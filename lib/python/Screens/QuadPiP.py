from Screens.Screen import Screen
from enigma import ePoint, eSize, eServiceCenter, getBestPlayableServiceReference, eServiceReference
from Components.VideoWindow import VideoWindow
from Components.config import config, ConfigPosition

class QuadPiP(Screen):
	def __init__(self, session, decoderIdx = 1, pos = None):
		Screen.__init__(self, session)
		self["video"] = VideoWindow(decoderIdx, 720, 576)
		self.currentService = None
		self.onLayoutFinish.append(self.LayoutFinished)
		self.decoderIdx = decoderIdx
		self.pos = pos
		self.skinName = "PictureInPicture"

	def LayoutFinished(self):
		#self["video"].instance.setAdjustPosition(False)
		self.onLayoutFinish.remove(self.LayoutFinished)
		x = self.pos[0]
		y = self.pos[1]
		w = self.pos[2]
		h = self.pos[3]

		if x != -1 and y != -1 and w != -1 and h != -1:
			self.move(x, y)
			self.resize(w, h)

	def move(self, x, y):
		self.instance.move(ePoint(x, y))

	def resize(self, w, h):
		self.instance.resize(eSize(*(w, h)))
		self["video"].instance.resize(eSize(*(w, h)))

	def getPosition(self):
		return ((self.instance.position().x(), self.instance.position().y()))

	def getSize(self):
		return (self.instance.size().width(), self.instance.size().height())

	def playService(self, service, playAudio):
		print "  ---PLAY-->   ",service,playAudio
		if service and (service.flags & eServiceReference.isGroup):
			ref = getBestPlayableServiceReference(service, eServiceReference())
		else:
			ref = service
		if ref:
			self.pipservice = eServiceCenter.getInstance().play(ref)
			if self.pipservice and not self.pipservice.setTarget(self.decoderIdx):
				self.setQpipMode(True, playAudio)
				self.pipservice.start()
				self.currentService = service
				return True
			else:
				self.pipservice = None
		return False

	def setQpipMode(self, pipMode, playAudio):
		if self.pipservice:
			print "   ---->   index, mode, audio ---> ",self.decoderIdx, pipMode, playAudio
			self.pipservice.setQpipMode(pipMode, playAudio)

	def getCurrentService(self):
		return self.currentService

