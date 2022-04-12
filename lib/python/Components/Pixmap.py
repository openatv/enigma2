from enigma import ePixmap, eTimer
from os.path import isfile

from skin import domScreens, loadPixmap
from Components.ConditionalWidget import ConditionalWidget
from Components.GUIComponent import GUIComponent
from Tools.Directories import SCOPE_LCDSKIN, SCOPE_GUISKIN, fileExists, resolveFilename


class Pixmap(GUIComponent):
	GUI_WIDGET = ePixmap

	def __init__(self):
		GUIComponent.__init__(self)
		self.xOffset = 0
		self.yOffset = 0

	def getSize(self):
		size = self.instance.size()
		return size.width(), size.height()

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = []
			for (attrib, value) in self.skinAttributes:
				if attrib == "offset":
					self.xOffset, self.yOffset = map(int, value.split(","))
				else:
					attribs.append((attrib, value))
			self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop, screen)

	def move(self, x, y=None):
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
	def __init__(self, withTimer=True):
		ConditionalWidget.__init__(self)
		Pixmap.__init__(self)


class MovingPixmap(Pixmap):
	def __init__(self):
		Pixmap.__init__(self)
		self.moving = False
		self.x = 0  # Get actual value after skin applied.
		self.y = 0  # Get actual value after skin applied.
		self.clearPath()
		self.moveTimer = eTimer()
		self.moveTimer.callback.append(self.doMove)
		self.callback = None

	def applySkin(self, desktop, screen):
		ret = Pixmap.applySkin(self, desktop, screen)
		self.x, self.y = self.getPosition()
		return ret

	def clearPath(self, repeated=False):
		if self.moving:
			self.moving = False
			self.moveTimer.stop()
		self.path = []
		self.currDest = 0
		self.repeated = repeated

	def addMovePoint(self, x, y, time=20):
		self.path.append((x, y, time))

	def moveTo(self, x, y, time=20):
		self.clearPath()
		self.addMovePoint(x, y, time)

	def startMoving(self, callback=None):
		if callable(callback):
			self.callback = callback
		if not self.moving:
			try:
				self.time = self.path[self.currDest][2]
				self.x, self.y = self.getPosition()
				self.stepX = (self.path[self.currDest][0] - self.x) / float(self.time)
				self.stepY = (self.path[self.currDest][1] - self.y) / float(self.time)
				self.moving = True
				self.moveTimer.start(100)
			except Exception:  # Moving not possible.  Widget not there yet/any more.  Stop moving.
				self.stopMoving()

	def stopMoving(self):
		self.moving = False
		self.moveTimer.stop()
		if self.callback:
			self.callback()

	def doMove(self):
		self.time -= 1
		if self.time == 0:
			self.x, self.y = self.path[self.currDest][0:2]
		else:
			self.x += self.stepX
			self.y += self.stepY
		try:
			self.move(int(self.x), int(self.y))
		except Exception:  # Moving not possible.  Widget not there any more.  Stop moving.
			self.stopMoving()
		if self.time == 0:
			self.currDest += 1
			self.moveTimer.stop()
			self.moving = False
			if self.currDest >= len(self.path):  # End of path.
				if self.repeated:
					self.currDest = 0
					self.moving = False
					self.startMoving()
				elif self.callback:
					self.callback()
			else:
				self.moving = False
				self.startMoving()


class MultiPixmap(Pixmap):
	def __init__(self):
		Pixmap.__init__(self)
		self.pixmaps = []

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			myScreen, path = domScreens.get(screen.__class__.__name__, (None, None))
			skinPathPrefix = getattr(screen, "skin_path", path)
			pixmap = None
			attribs = []
			for (attrib, value) in self.skinAttributes:
				if attrib == "pixmaps":
					pixmaps = value.split(",")
					for pix in pixmaps:
						if fileExists(resolveFilename(SCOPE_GUISKIN, pix, path_prefix=skinPathPrefix)):
							pngfile = resolveFilename(SCOPE_GUISKIN, pix, path_prefix=skinPathPrefix)
						elif fileExists(resolveFilename(SCOPE_LCDSKIN, pix, path_prefix=skinPathPrefix)):
							pngfile = resolveFilename(SCOPE_LCDSKIN, pix, path_prefix=skinPathPrefix)
						else:
							pngfile = ""
						if pngfile and isfile(pngfile):
							self.pixmaps.append(loadPixmap(pngfile, desktop))
					if not pixmap:
						if fileExists(resolveFilename(SCOPE_GUISKIN, pixmaps[0], path_prefix=skinPathPrefix)):
							pixmap = resolveFilename(SCOPE_GUISKIN, pixmaps[0], path_prefix=skinPathPrefix)
						elif fileExists(resolveFilename(SCOPE_LCDSKIN, pixmaps[0], path_prefix=skinPathPrefix)):
							pixmap = resolveFilename(SCOPE_LCDSKIN, pixmaps[0], path_prefix=skinPathPrefix)
				elif attrib == "pixmap":
					if fileExists(resolveFilename(SCOPE_GUISKIN, value, path_prefix=skinPathPrefix)):
						pixmap = resolveFilename(SCOPE_GUISKIN, value, path_prefix=skinPathPrefix)
					elif fileExists(resolveFilename(SCOPE_LCDSKIN, value, path_prefix=skinPathPrefix)):
						pixmap = resolveFilename(SCOPE_LCDSKIN, value, path_prefix=skinPathPrefix)
				else:
					attribs.append((attrib, value))
			if pixmap:
				attribs.append(("pixmap", pixmap))
			self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop, screen)

	def setPixmapNum(self, index):
		if self.instance:
			if len(self.pixmaps) > index:
				self.instance.setPixmap(self.pixmaps[index])
			else:
				print("[Pixmap] setPixmapNum(%d) failed!  Defined pixmaps: %s." % (index, str(self.pixmaps)))
