from ConditionalWidget import ConditionalWidget
from GUIComponent import GUIComponent

from enigma import ePixmap, eTimer

from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from os import path
from skin import loadPixmap

class Pixmap(GUIComponent):
	GUI_WIDGET = ePixmap

	def getSize(self):
		s = self.instance.size()
		return (s.width(), s.height())

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

class MultiPixmap(Pixmap):
	def __init__(self):
		Pixmap.__init__(self)
		self.pixmaps = []

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			skin_path_prefix = getattr(screen, "skin_path", path)
			pixmap = None
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "pixmaps":
					pixmaps = value.split(',')
					for p in pixmaps:
						self.pixmaps.append(loadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, p, path_prefix=skin_path_prefix), desktop) )
					if not pixmap:
						pixmap = resolveFilename(SCOPE_CURRENT_SKIN, pixmaps[0], path_prefix=skin_path_prefix)
				elif attrib == "pixmap":
					pixmap = resolveFilename(SCOPE_CURRENT_SKIN, value, path_prefix=skin_path_prefix)
				else:
					attribs.append((attrib,value))
			if pixmap:
				attribs.append(("pixmap", pixmap))
			self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop, screen)

	def setPixmapNum(self, x):
		if self.instance:
			if len(self.pixmaps) > x:
				self.instance.setPixmap(self.pixmaps[x])
			else:
				print "setPixmapNum(%d) failed! defined pixmaps:" %(x), self.pixmaps
