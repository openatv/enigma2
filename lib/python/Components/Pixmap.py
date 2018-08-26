from ConditionalWidget import ConditionalWidget
from GUIComponent import GUIComponent

from enigma import ePixmap, eTimer

from Tools.Directories import resolveFilename, fileExists, SCOPE_SKIN_IMAGE, SCOPE_ACTIVE_SKIN, SCOPE_ACTIVE_LCDSKIN
from os import path
from skin import loadPixmap

class Pixmap(GUIComponent):
	GUI_WIDGET = ePixmap

	def __init__(self):
		GUIComponent.__init__(self)
		self.xOffset, self.yOffset = 0, 0

	def getSize(self):
		s = self.instance.size()
		return s.width(), s.height()

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			pixmap = None
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "offset":
					self.xOffset, self.yOffset = map(int, value.split(','))
				else:
					attribs.append((attrib,value))
			self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop, screen)


	def move(self, x, y = None):
		if y is None:
			y = x.y()
			x = x.x()
		GUIComponent.move(self, x - self.xOffset, y - self.yOffset)

	def setPosition(self, x, y):
		self.move(x, y)

	def getPosition(self):
		x, y = GUIComponent.getPosition(self)
		return x + self.xOffset, y + self.yOffset

	def setOffset(self, x, y):
		oldx, oldy = self.getPosition()
		self.xOffset, self.yOffset = x, y
		self.move(oldx, oldy)

	def getOffset(self):
		return self.xOffset, self.yOffset

class PixmapConditional(ConditionalWidget, Pixmap):
	def __init__(self, withTimer = True):
		ConditionalWidget.__init__(self)
		Pixmap.__init__(self)

class MovingPixmap(Pixmap):
	def __init__(self):
		Pixmap.__init__(self)

		self.moving = False

		# get actual values after skin applied
		self.x = 0
		self.y = 0

		self.clearPath()

		self.moveTimer = eTimer()
		self.moveTimer.callback.append(self.doMove)

	def applySkin(self, desktop, screen):
		ret = Pixmap.applySkin(self, desktop, screen)
		self.x, self.y = self.getPosition()
		return ret

	def clearPath(self, repeated = False):
		if self.moving:
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
			try:
				self.time = self.path[self.currDest][2]
				self.x, self.y = self.getPosition()
				self.stepX = (self.path[self.currDest][0] - self.x) / float(self.time)
				self.stepY = (self.path[self.currDest][1] - self.y) / float(self.time)

				self.moving = True
				self.moveTimer.start(100)
			except:  # moving not possible... widget not there yet/any more... stop moving
				self.stopMoving()

	def stopMoving(self):
		self.moving = False
		self.moveTimer.stop()

	def doMove(self):
		self.time -= 1
		if self.time == 0:
			self.x, self.y = self.path[self.currDest][0:2]
		else:
			self.x += self.stepX
			self.y += self.stepY
		try:
			self.move(int(self.x), int(self.y))
		except:  # moving not possible... widget not there any more... stop moving
			self.stopMoving()

		if self.time == 0:
			self.currDest += 1
			self.moveTimer.stop()
			self.moving = False
			if self.currDest >= len(self.path): # end of path
				if self.repeated:
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
			skin_path_prefix = getattr(screen, "skin_path", None)
			pixmap = None
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "pixmaps":
					pixmaps = value.split(',')
					for p in pixmaps:
						pngfile = ""
						if fileExists(resolveFilename(SCOPE_ACTIVE_SKIN, p, path_prefix=skin_path_prefix)):
							pngfile = resolveFilename(SCOPE_ACTIVE_SKIN, p, path_prefix=skin_path_prefix)
						elif fileExists(resolveFilename(SCOPE_SKIN_IMAGE, p, path_prefix=skin_path_prefix)):
							pngfile = resolveFilename(SCOPE_SKIN_IMAGE, p, path_prefix=skin_path_prefix)
						elif fileExists(resolveFilename(SCOPE_ACTIVE_LCDSKIN, p, path_prefix=skin_path_prefix)):
							pngfile = resolveFilename(SCOPE_ACTIVE_LCDSKIN, p, path_prefix=skin_path_prefix)
						if path.exists(pngfile):
							self.pixmaps.append(loadPixmap(pngfile, desktop))
					if not pixmap:
						if fileExists(resolveFilename(SCOPE_ACTIVE_SKIN, pixmaps[0], path_prefix=skin_path_prefix)):
							pixmap = resolveFilename(SCOPE_ACTIVE_SKIN, pixmaps[0], path_prefix=skin_path_prefix)
						elif fileExists(resolveFilename(SCOPE_SKIN_IMAGE, pixmaps[0], path_prefix=skin_path_prefix)):
							pixmap = resolveFilename(SCOPE_SKIN_IMAGE, pixmaps[0], path_prefix=skin_path_prefix)
						elif fileExists(resolveFilename(SCOPE_ACTIVE_LCDSKIN, pixmaps[0], path_prefix=skin_path_prefix)):
							pixmap = resolveFilename(SCOPE_ACTIVE_LCDSKIN, pixmaps[0], path_prefix=skin_path_prefix)
				elif attrib == "pixmap":
					if fileExists(resolveFilename(SCOPE_ACTIVE_SKIN, value, path_prefix=skin_path_prefix)):
						pixmap = resolveFilename(SCOPE_ACTIVE_SKIN, value, path_prefix=skin_path_prefix)
					elif fileExists(resolveFilename(SCOPE_SKIN_IMAGE, value, path_prefix=skin_path_prefix)):
						pixmap = resolveFilename(SCOPE_SKIN_IMAGE, value, path_prefix=skin_path_prefix)
					elif fileExists(resolveFilename(SCOPE_ACTIVE_LCDSKIN, value, path_prefix=skin_path_prefix)):
						pixmap = resolveFilename(SCOPE_ACTIVE_LCDSKIN, value, path_prefix=skin_path_prefix)
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
				print "[Pixmap] setPixmapNum(%d) failed! defined pixmaps:" % x, self.pixmaps
