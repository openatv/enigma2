from ConditionalWidget import ConditionalWidget
from GUIComponent import GUIComponent

from enigma import ePixmap, eTimer

class Pixmap(GUIComponent):
	GUI_WIDGET = ePixmap

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
		
		self.clearPath()
		
		self.moveTimer = eTimer()
		self.moveTimer.callback.append(self.doMove)
		
	def clearPath(self, repeated = False):
		if (self.moving):
			self.moving = False
			self.moveTimer.stop()
			
		self.path = []
		self.currDest = 0
		self.repeated = repeated
		
	def addMovePoint(self, x, y, time = 20):
		self.path.append((x, y, time))
	
	def moveTo(self, x, y, time = 20):
		self.clearPath()
		self.addMovePoint(x, y, time)
		
	def startMoving(self):
		if not self.moving:
			self.time = self.path[self.currDest][2]
			self.stepX = (self.path[self.currDest][0] - self.x) / float(self.time)
			self.stepY = (self.path[self.currDest][1] - self.y) / float(self.time)

			self.moving = True
			self.moveTimer.start(100)
			
	def stopMoving(self):
		self.moving = False
		self.moveTimer.stop()
		
	def doMove(self):
		self.x += self.stepX
		self.y += self.stepY
		self.time -= 1
		try:
			self.move(int(self.x), int(self.y))
		except: # moving not possible... widget not there any more... stop moving
			self.stopMoving()
			
		if (self.time == 0):
			self.currDest += 1
			self.moveTimer.stop()
			self.moving = False
			if (self.currDest >= len(self.path)): # end of path
				if (self.repeated):
					self.currDest = 0
					self.moving = False
					self.startMoving()
			else:
				self.moving = False
				self.startMoving()
