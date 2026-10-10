from os import stat
from urllib.parse import urlsplit
from xml.etree.ElementTree import ParseError, fromstring
from enigma import eEnv, eServiceCenter, eServiceReference, eTimer, iPlayableService, iServiceInformation
from Components.ServiceEventTracker import ServiceEventTracker
from Tools.Directories import SCOPE_CONFIG, resolveFilename


class HybridService:
	"""Keep broadcast identities while playing explicitly mapped Internet services.

	Only the main InfoBar owns this helper. Recordings, PiP and scan results are
	unchanged. Portal applications still use the installed Red Button handler.
	"""

	MAX_XML_SIZE = 262144

	def __init__(self, infoBar):
		self.infoBar = infoBar
		self.paths = (eEnv.resolve("${datadir}/enigma2/hybridservices.xml"), resolveFilename(SCOPE_CONFIG, "hybridservices.xml"))
		self.files = {}
		self.services = {}
		self.reference = None
		self.openedPortal = None
		self.timer = eTimer()
		self.timer.callback.append(self.openApplication)
		self.eventTracker = ServiceEventTracker(screen=infoBar, eventmap={
			iPlayableService.evStart: self.serviceStarted,
			iPlayableService.evEnd: self.serviceStopped,
			iPlayableService.evHBBTVInfo: self.applicationDetected
		})
		infoBar.session.nav.playServiceExtensions.append(self.playService)
		infoBar.onClose.append(self.close)

	@staticmethod
	def serviceKey(ref):
		# Namespace also separates satellite, terrestrial and cable services with
		# otherwise identical triplets. Ignore SD/HD type changes and cached names.
		if ref and ref.type == 1 and not ref.flags & eServiceReference.isGroup and not ref.getPath():
			return tuple(ref.getUnsignedData(x) for x in (4, 3, 2, 1))
		return None

	@classmethod
	def parseServices(cls, data):
		if len(data) > cls.MAX_XML_SIZE or b"<!DOCTYPE" in data.upper():
			raise ValueError("Invalid hybrid services XML")
		root = fromstring(data)
		if root.tag != "hybridservices" or root.get("version") != "1":
			raise ValueError("Unsupported hybrid services XML version")
		services = {}
		for entry in root.findall("service"):
			key = tuple(int(entry.attrib[x], 16) for x in ("namespace", "onid", "tsid", "sid"))
			if not 0 <= key[0] <= 0xFFFFFFFF or any(not 0 <= x <= 0xFFFF for x in key[1:]):
				raise ValueError("Invalid DVB service identity")
			mode = entry.get("mode")
			url = entry.get("url", "").strip()
			if mode not in ("stream", "hbbtv", "disabled"):
				raise ValueError("Invalid hybrid service mode")
			if mode == "stream":
				address = urlsplit(url)
				if address.scheme not in ("http", "https") or not address.hostname or address.username or address.password or any(ord(x) < 32 for x in url):
					raise ValueError("Only HTTP(S) stream URLs without credentials are supported")
			elif url:
				raise ValueError("Portal URLs must come from the broadcast AIT")
			services[key] = (mode, url)
		return services

	def loadServices(self):
		changed = False
		for path in self.paths:
			try:
				status = stat(path)
				stamp = (status.st_mtime_ns, status.st_size)
			except OSError:
				stamp = None
			previous = self.files.get(path)
			if previous is not None and previous[0] == stamp:
				continue
			entries = {}
			if stamp is not None:
				try:
					with open(path, "rb") as source:
						entries = self.parseServices(source.read(self.MAX_XML_SIZE + 1))
				except (OSError, ParseError, KeyError, ValueError) as error:
					print(f"[HybridService] Cannot load '{path}': {error}")
					entries = previous[1] if previous else {}
			self.files[path] = (stamp, entries)
			changed = True
		if changed:
			self.services = {}
			for path in self.paths:
				self.services.update(self.files[path][1])

	def playService(self, navigation, ref, event, infoBar):
		navigation.hybridPlaybackService = None
		if infoBar is not self.infoBar:
			return ref
		self.loadServices()
		entry = self.services.get(self.serviceKey(ref))
		if entry and entry[0] == "stream":
			target = eServiceReference(4097, 0, entry[1])
			for index in range(8):
				target.setData(index, ref.getData(index))
			info = eServiceCenter.getInstance().info(ref)
			if info:
				target.setName(info.getName(ref))
			navigation.hybridPlaybackService = target
			navigation.currentlyPlayingServiceReference = target
			print(f"[HybridService] Playing mapped Internet service {self.serviceKey(ref)}.")
			return target
		return ref

	def serviceStarted(self):
		self.timer.stop()
		ref = self.infoBar.session.nav.getCurrentlyPlayingServiceOrGroup()
		key = self.serviceKey(ref)
		if key != self.reference:
			self.openedPortal = None
		self.reference = key

	def serviceStopped(self):
		self.timer.stop()

	def applicationDetected(self):
		self.loadServices()
		entry = self.services.get(self.reference)
		if entry and entry[0] == "hbbtv" and self.openedPortal != self.reference:
			# Leave the native AIT callback before opening a screen. Also allow the
			# installed HbbTV plugin to register its Red Button handler at startup.
			self.timer.start(1500, True)

	def openApplication(self):
		bar = self.infoBar
		self.loadServices()
		entry = self.services.get(self.reference)
		ref = bar.session.nav.getCurrentlyPlayingServiceOrGroup()
		if not entry or entry[0] != "hbbtv" or self.reference != self.serviceKey(ref) or bar.session.current_dialog is not bar or ServiceEventTracker.getActiveInfoBar() is not bar:
			return
		service = bar.session.nav.getCurrentService()
		info = service and service.info()
		# An explicitly mapped portal may broadcast a placeholder WITH audio/video.
		# The current service's AUTOSTART AIT, not missing PIDs, authorizes the URL.
		if not info or not info.getInfoString(iServiceInformation.sHBBTVUrl):
			return
		self.openedPortal = self.reference
		if bar.onHBBTVActivation:
			print(f"[HybridService] Opening broadcast HbbTV portal {self.reference}.")
			try:
				bar.activateRedButton()
			except Exception as error:
				print(f"[HybridService] Cannot start HbbTV: {error}")
				bar.session.showError(_("Unable to start the HbbTV application."))
		else:
			bar.session.showInfo(_("This channel requires an HbbTV plugin. Please install a compatible HbbTV plugin."), timeout=8)

	def close(self):
		self.timer.stop()
		self.infoBar.session.nav.playServiceExtensions.remove(self.playService)
