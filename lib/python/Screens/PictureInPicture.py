from Screens.Screen import Screen
from enigma import ePoint, eSize, eServiceCenter

from Components.VideoWindow import VideoWindow

class PictureInPicture(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["video"] = VideoWindow()
		self.currentService = None

	def move(self, x, y):
		print "moving pip to", str(x) + ":" + str(y)
		self.instance.move(ePoint(x, y))
		
	def resize(self, w, h):
		print "resizing pip to", str(w) + "x" + str(h)
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
	
