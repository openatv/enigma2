from os.path import isfile

from enigma import eLabel, ePixmap, eTimer

from skin import domScreens, parseColor, parsePixmap
from Components.ConditionalWidget import ConditionalWidget
from Components.GUIComponent import GUIComponent
from Tools.Directories import SCOPE_LCDSKIN, SCOPE_GUISKIN, fileExists, resolveFilename


class Pixmap(GUIComponent):
	GUI_WIDGET = ePixmap

	def __init__(self):
		GUIComponent.__init__(self)
		self.xOffset = 0
		self.yOffset = 0
		self.pixmap = None

	def getSize(self):
		size = self.instance.size()
		return size.width(), size.height()

	def setPixmap(self, pixmap):
		self.pixmap = pixmap
		self.instance.setPixmap(pixmap)

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
		self.iconGlyphs = None
		self.iconColors = []
		self.iconFont = None

	def createWidget(self, parent):
		# Widget-local opt-in: embedded plugin skins can still use their PNGs.
		attributes = dict(self.skinAttributes or ())
		self.iconGlyphs = None
		self.iconColors = []
		self.iconFont = attributes.get("iconFont")
		if attributes.get("iconFont") and attributes.get("iconGlyphs"):
			try:
				codepoints = [int(value.strip(), 0) for value in attributes["iconGlyphs"].split(",")]
				if any(not 0 < value <= 0x10FFFF or 0xD800 <= value <= 0xDFFF for value in codepoints):
					raise ValueError("Invalid Unicode codepoint")
				self.iconGlyphs = [chr(value) for value in codepoints]
			except ValueError as error:
				print(f"[MultiPixmap] Invalid iconGlyphs, using pixmaps: {error}")
		return eLabel(parent) if self.iconGlyphs is not None else Pixmap.createWidget(self, parent)

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attributes = dict(self.skinAttributes)
			self.skinAttributes = [(name, value) for name, value in self.skinAttributes if name not in ("iconFont", "iconGlyphs", "iconColors")]
			if self.iconGlyphs is not None:
				self.skinAttributes = [(name, value) for name, value in self.skinAttributes if name not in ("pixmap", "pixmaps", "scale", "font")]
				self.skinAttributes.append(("font", self.iconFont))
				if "iconColors" in attributes:
					self.iconColors = [parseColor(value.strip()) for value in attributes["iconColors"].split(",") if value.strip()]
					if len(self.iconColors) != len(self.iconGlyphs):
						print("[MultiPixmap] iconColors must provide one color per glyph; using the widget foreground color")
						self.iconColors = []
				return GUIComponent.applySkin(self, desktop, screen)
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
							self.pixmaps.append(parsePixmap(pngfile, desktop))
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
		if self.iconGlyphs is not None:
			if self.instance and 0 <= index < len(self.iconGlyphs):
				self.instance.setText(self.iconGlyphs[index])
				if index < len(self.iconColors):
					self.instance.setForegroundColor(self.iconColors[index])
			return
		if self.instance and self.pixmaps:
			if len(self.pixmaps) > index:
				self.instance.setPixmap(self.pixmaps[index])
			else:
				print(f"[Pixmap] setPixmapNum({index}) failed!  Defined pixmaps: {str(self.pixmaps)}.")
