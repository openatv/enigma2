from enigma import eServiceReference, eServiceCenter, getBestPlayableServiceReference
import NavigationInstance

class ServiceReference(eServiceReference):
	def __init__(self, ref, reftype = eServiceReference.idInvalid, flags = 0, path = ''):
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
		return ref.flags & eServiceReference.isGroup or (ref.type == eServiceReference.idDVB or ref.type == eServiceReference.idDVB + 0x100 or ref.type == 0x2000 or ref.type == 0x1001)

def getPlayingref(ref):
	playingref = None
	if NavigationInstance.instance:
		playingref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
	if not playingref:
		playingref = eServiceReference()
	return playingref

def isPlayableForCur(ref):
	info = eServiceCenter.getInstance().info(ref)
	return not not (info and info.isPlayable(ref, getPlayingref(ref)))

def resolveAlternate(ref):
	nref = None
	if ref.flags & eServiceReference.isGroup:
		nref = getBestPlayableServiceReference(ref, getPlayingref(ref))
		if not nref:
			nref = getBestPlayableServiceReference(ref,
			 eServiceReference(), True)
	return nref
