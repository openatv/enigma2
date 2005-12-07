from ConditionalWidget import *

from enigma import *

class Pixmap(Widget):
	def __init__(self):
		Widget.__init__(self)

	def getePixmap(self, parent):
		#pixmap = ePixmap(parent)
		#pixmap.setPixmapFromFile(self.filename)
		return ePixmap(parent)
	
	def createWidget(self, parent):
		return self.getePixmap(parent)

	def removeWidget(self, w):
		pass

	def move(self, x, y):
		self.instance.move(ePoint(int(x), int(y)))

class PixmapConditional(ConditionalWidget, Pixmap):
	def __init__(self, withTimer = True):
		ConditionalWidget.__init__(self)
		Pixmap.__init__(self)

class MovingPixmap(Pixmap):
	def __init__(self):
		Pixmap.__init__(self)
		
		self.moving = False
		
		# TODO: get real values
		self.x = 0.0
		self.y = 0.0
		
		self.moveTimer = eTimer()
		self.moveTimer.timeout.get().append(self.doMove)
		
	def moveTo(self, x, y, time = 20):
		self.time = time
		self.destX = x
		self.destY = y
		self.stepX = (self.destX - self.x) / float(time)
		self.stepY = (self.destY - self.y) / float(time)
		
	def startMoving(self):
		if not self.moving:
			self.moving = True
			self.moveTimer.start(10)
		
	def doMove(self):
		self.x += self.stepX
		self.y += self.stepY
		self.time -= 1
		self.move(int(self.x), int(self.y))
		if (self.time == 0):
			self.moveTimer.stop()
			self.moving = False