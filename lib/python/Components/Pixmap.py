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
			skin_path_prefix = getattr(screen, "skin_path", path)
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

		self.clearPath()

		self.moveTimer = eTimer()
		self.moveTimer.callback.append(self.doMove)

	def bresMove(self, x, y):
		if self.steep:
			x, y = y, x

		try:
			Pixmap.move(self, x, y)
		except: # moving not possible... widget not there any more... stop moving
			self.stopMoving()

	def getBresPos(self):
		x, y = self.getPosition()
		return (y, x) if self.steep else (x, y)

	def bresSetup(self, x1, y1):
		# The x and y coords are flipped if needed to
		# keep the calculations in the octants where
		# abs(x1 - x0) <= abs(y1 - y0)

		x0, y0 = self.getPosition()
		dx, dy = abs(x1 - x0), abs(y1 - y0)

		self.steep = dy > dx
		if self.steep:
			dx, dy = dy, dx
			x0, y0 = y0, x0
			x1, y1 = y1, x1
		self.dx, self.dy = dx, dy

		self.inc = 1 if x0 < x1 else -1
		self.ystep = 1 if y0 < y1 else -1

		self.err = dx / 2

	def bresStep(self, tox):
		# The intermediate points aren't needed, so just
		# calculate the "y" change, residual error
		# and final coordinates

		x, y = self.getBresPos()
		xsteps = abs(tox - x)
		self.err -= self.dy * xsteps
		if self.err < 0:
			ysteps = -self.err / self.dx
			y += self.ystep * ysteps
			self.err += self.dx * ysteps
		self.bresMove(tox, y)

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
				self.bresSetup(*self.path[self.currDest][0:2])
				self.time = self.path[self.currDest][2]
				self.stepX = self.inc * (self.dx / self.time)
				self.stepXRem = self.dx % self.time
				self.moving = True
				self.moveTimer.start(100)
			except:  # moving not possible... widget not there any more... stop moving
				self.stopMoving()

	def stopMoving(self):
		self.moving = False
		self.moveTimer.stop()

	def doMove(self):
		try:
			tox = self.getBresPos()[0] + self.stepX
			if self.stepXRem > 0:
				tox += self.inc
				self.stepXRem -= 1

			self.bresStep(tox)
		except:  # moving not possible... widget not there any more... stop moving
			self.stopMoving()

		self.time -= 1

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

	def move(self, x, y = None):
		self.stopMoving()
		try:
			Pixmap.move(self, x, y)
		except:  # moving not possible... widget not there any more... stop moving
			pass

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
						pngfile = resolveFilename(SCOPE_ACTIVE_SKIN, p, path_prefix=skin_path_prefix)
						if fileExists(resolveFilename(SCOPE_SKIN_IMAGE, p, path_prefix=skin_path_prefix)):
							pngfile = resolveFilename(SCOPE_SKIN_IMAGE, p, path_prefix=skin_path_prefix)
						elif fileExists(resolveFilename(SCOPE_ACTIVE_LCDSKIN, p, path_prefix=skin_path_prefix)):
							pngfile = resolveFilename(SCOPE_ACTIVE_LCDSKIN, p, path_prefix=skin_path_prefix)
						if path.exists(pngfile):
							self.pixmaps.append(loadPixmap(pngfile, desktop))
					if not pixmap:
						pixmap = resolveFilename(SCOPE_ACTIVE_SKIN, pixmaps[0], path_prefix=skin_path_prefix)
						if fileExists(resolveFilename(SCOPE_SKIN_IMAGE, pixmaps[0], path_prefix=skin_path_prefix)):
							pixmap = resolveFilename(SCOPE_SKIN_IMAGE, pixmaps[0], path_prefix=skin_path_prefix)
						elif fileExists(resolveFilename(SCOPE_ACTIVE_LCDSKIN, pixmaps[0], path_prefix=skin_path_prefix)):
							pixmap = resolveFilename(SCOPE_ACTIVE_LCDSKIN, pixmaps[0], path_prefix=skin_path_prefix)
				elif attrib == "pixmap":
					pixmap = resolveFilename(SCOPE_ACTIVE_SKIN, value, path_prefix=skin_path_prefix)
					if fileExists(resolveFilename(SCOPE_SKIN_IMAGE, value, path_prefix=skin_path_prefix)):
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
				print "setPixmapNum(%d) failed! defined pixmaps:" % x, self.pixmaps
