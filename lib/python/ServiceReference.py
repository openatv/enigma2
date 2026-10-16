from enigma import eServiceReference, eServiceReferenceDVB, eServiceCenter, getBestPlayableServiceReference
from Components.config import config, configfile
import NavigationInstance


class ServiceReference(eServiceReference):
	def __init__(self, ref, reftype=eServiceReference.idInvalid, flags=0, path=''):
		if reftype != eServiceReference.idInvalid:
			self.ref = eServiceReference(reftype, flags, path)
		elif not isinstance(ref, eServiceReference):
			self.ref = eServiceReference(ref or "")
		else:
			self.ref = ref
		self.serviceHandler = eServiceCenter.getInstance()

	def __str__(self):
		return self.ref.toString()

	def getServiceName(self):
		info = self.info()
		return info and info.getName(self.ref) or ""

	def info(self):
		return self.serviceHandler.info(self.ref)

	def list(self):
		return self.serviceHandler.list(self.ref)

	def getType(self):
		return self.ref.type

	def getPath(self):
		return self.ref.getPath()

	def getFlags(self):
		return self.ref.flags

	def isRecordable(self):
		ref = self.ref
		return ref.flags & eServiceReference.isGroup or (ref.type == eServiceReference.idDVB or ref.type == eServiceReference.idDVB + 0x100 or ref.type == eServiceReference.idServiceDAB or ref.type == 0x2000 or ref.type == 0x1001)

	def toString(self):
		return self.ref.toString()


def getStreamRelayRef(sref):
	try:
		if "http" in sref:
			icamport = config.misc.softcam_streamrelay_port.value
			icamip = ".".join("%d" % d for d in config.misc.softcam_streamrelay_url.value)
			icam = f"http%3a//{icamip}%3a{icamport}/"
			if icam in sref:
				return sref.split(icam)[1].split(":")[0].replace("%3a", ":"), True
	except Exception:
		pass
	return sref, False


def getPlayingref(ref):
	playingref = None
	if NavigationInstance.instance:
		playingref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
		if playingref:
			from Screens.InfoBarGenerics import streamrelay  # needs here to prevent cycle import
			if streamrelay.checkService(playingref):
				playingref.setAlternativeUrl(playingref.toString(), True)
	if not playingref:
		playingref = eServiceReference()
	return playingref


def isPlayableForCur(ref):
	info = eServiceCenter.getInstance().info(ref)
	return info and info.isPlayable(ref, getPlayingref(ref))


def resolveAlternate(ref):
	nref = None
	if ref.flags & eServiceReference.isGroup:
		nref = getBestPlayableServiceReference(ref, getPlayingref(ref))
		if not nref:
			nref = getBestPlayableServiceReference(ref, eServiceReference(), True)
	return nref


def makeServiceQueryStr(serviceTypes):
	return ' || '.join(['(type == %d)' % x for x in serviceTypes])


def isRadioServiceReference(ref):
	"""Return whether *ref* belongs in Enigma2's existing radio mode."""
	if not isinstance(ref, eServiceReference):
		ref = eServiceReference(ref or "")
	return bool(ref.valid() and (ref.type == eServiceReference.idServiceDAB or ref.getUnsignedData(0) in (
		eServiceReferenceDVB.dRadio,
		eServiceReferenceDVB.dRadioAvc,
	)))


# type 1 = digital television service
# type 4 = nvod reference service (NYI)
# type 17 = MPEG-2 HD digital television service
# type 22 = advanced codec SD digital television
# type 24 = advanced codec SD NVOD reference service (NYI)
# type 25 = advanced codec HD digital television
# type 27 = advanced codec HD NVOD reference service (NYI)
# type 2 = digital radio sound service
# type 10 = advanced codec digital radio sound service
# type 31 = High Efficiency Video Coding digital television
# type 32 = High Efficiency Video Coding digital television

# Generate an eServiceRef query path containing
# '(type == serviceTypes[0]) || (type == serviceTypes[1]) || ...'


service_types_tv_ref = eServiceReference(eServiceReference.idDVB, eServiceReference.flagDirectory, eServiceReferenceDVB.dTv)

service_types_tv_ref.setPath(makeServiceQueryStr((
	eServiceReferenceDVB.dTv,
	eServiceReferenceDVB.mpeg2HdTv,
	eServiceReferenceDVB.avcSdTv,
	eServiceReferenceDVB.avcHdTv,
	eServiceReferenceDVB.nvecTv,
	eServiceReferenceDVB.nvecTv20,
	eServiceReferenceDVB.user134,
	eServiceReferenceDVB.user195,
)))

service_types_radio_ref = eServiceReference(eServiceReference.idDVB, eServiceReference.flagDirectory, eServiceReferenceDVB.dRadio)
service_types_radio_ref.setPath(makeServiceQueryStr((
	eServiceReferenceDVB.dRadio,
	eServiceReferenceDVB.dRadioAvc,
)))


def serviceRefAppendPath(sref, path):
	nsref = eServiceReference(sref)
	nsref.setPath(nsref.getPath() + path)
	return nsref


def getPanicService():
	"""Resolve the saved service in today's bouquets; only migrate numbers once."""
	reference = config.usage.panicsref.value
	wanted = eServiceReference(reference) if reference else None
	if wanted is not None and not wanted.valid():
		return None, None
	radio = wanted is not None and isRadioServiceReference(wanted)
	mode = "radio" if radio else "tv"
	serviceTypes = service_types_radio_ref if radio else service_types_tv_ref
	if config.usage.multibouquet.value:
		root = eServiceReference(serviceTypes)
		root.setPath(f'FROM BOUQUET "bouquets.{mode}" ORDER BY bouquet')
	else:
		root = serviceRefAppendPath(serviceTypes, f' FROM BOUQUET "userbouquet.favourites.{mode}" ORDER BY bouquet')
	serviceHandler = eServiceCenter.getInstance()
	visited = set()

	def findService(bouquet, path):
		key = bouquet.toString()
		if key in visited:
			return None, None
		visited.add(key)
		services = serviceHandler.list(bouquet)
		if services is not None:
			service = services.getNext()
			while service.valid():
				if service.flags & eServiceReference.isDirectory and not service.flags & eServiceReference.isGroup:
					found, foundPath = findService(service, path + [service])
					if found is not None:
						return found, foundPath
				elif not service.flags & eServiceReference.isMarker:
					matches = service == wanted if wanted is not None else service.getChannelNum() == config.usage.panicchannel.value
					if matches:
						return service, path
				service = services.getNext()
		return None, None

	service, path = findService(root, [root])
	if service is None and wanted is not None:
		# A service removed from a bouquet can still exist in the service database.
		root = serviceRefAppendPath(serviceTypes, " ORDER BY name")
		service, path = findService(root, [root])
	if service is not None and not reference:
		config.usage.panicsref.value = service.toString()
		config.usage.panicsref.save()
		configfile.save()
	return service, path


def hdmiInServiceRef():
	return eServiceReference(eServiceReference.idServiceHDMIIn, eServiceReference.noFlags, eServiceReferenceDVB.dTv)
