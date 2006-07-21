from Screens.Screen import Screen
from enigma import ePoint, eSize, eServiceCenter
from Components.VideoWindow import VideoWindow
from Components.config import config, configElement, configSequence, configsequencearg

class PictureInPicture(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["video"] = VideoWindow()
		self.currentService = None
		config.av.pip = configElement("config.av.pip", configSequence, [-1, -1, -1, -1], configsequencearg.get("POSITION", (719, 567, 720, 568)))
		self.onLayoutFinish.append(self.LayoutFinished)

	def LayoutFinished(self):
		self.onLayoutFinish.remove(self.LayoutFinished)
		x = config.av.pip.value[0]
		y = config.av.pip.value[1]
		w = config.av.pip.value[2]
		h = config.av.pip.value[3]
		if x != -1 and y != -1 and w != -1 and h != -1:
			self.move(x, y)
			self.resize(w, h)

	def move(self, x, y):
		config.av.pip.value[0] = x
		config.av.pip.value[1] = y
		config.av.pip.save()
		self.instance.move(ePoint(x, y))
		
	def resize(self, w, h):
		config.av.pip.value[2] = w
		config.av.pip.value[3] = h
		config.av.pip.save()
		self.instance.resize(eSize(*(w, h)))
		self["video"].instance.resize(eSize(*(w, h)))
		
	def getPosition(self):
		return ((self.instance.position().x(), self.instance.position().y()))
		
	def getSize(self):
		return (self.instance.size().width(), self.instance.size().height())
		
	def playService(self, service):
		self.pipservice = eServiceCenter.getInstance().play(service)
		if self.pipservice and not self.pipservice.setTarget(1):
			self.pipservice.start()
			self.currentService = service
			return True
		else:
			self.pipservice = None
			return False
		
	def getCurrentService(self):
		return self.currentService
	
