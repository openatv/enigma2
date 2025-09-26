import math

from Screens.Screen import Screen
from Components.config import config
from Components.Sources.CanvasSource import CanvasSource
from Components.ActionMap import NumberActionMap
from Components.SystemInfo import BoxInfo
from Tools.Directories import fileExists
from enigma import gFont, getDesktop, gMainDC, eSize, RT_HALIGN_RIGHT, RT_WRAP


def RGB(r, g, b):
	return (r << 16) | (g << 8) | b


class OverscanTestScreen(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Overscan Test"))

		self.skin = """<screen position="fill">
				<ePixmap pixmap="%s" position="0,0" size="%s,%s" zPosition="2" scale="1" alphatest="on"/>
			</screen>""" % (getDesktop(0).size().height() == 1080 and ("overscan.png", 1920, 1080) or ("overscan.png", 1280, 720))

		self["actions"] = NumberActionMap(["InputActions", "OkCancelActions"],
		{
			"1": self.keyNumber,
			"2": self.keyNumber,
			"3": self.keyNumber,
			"4": self.keyNumber,
			"5": self.keyNumber,
			"7": self.keyNumber,
			"8": self.keyNumber,
			"9": self.keyNumber,
			"ok": self.ok,
			"cancel": self.cancel
		})

	def ok(self):
		self.close(True)

	def cancel(self):
		self.close(False)

	def keyNumber(self, key):
		self.close(key)


class FullHDTestScreen(OverscanTestScreen):
	skin = """
		<screen position="fill">
			<ePixmap pixmap="testscreen.png" position="0,0" size="1920,1080" zPosition="2" alphatest="on"/>
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("FullHD Test"))

		self.xres, self.yres = getDesktop(0).size().width(), getDesktop(0).size().height()

		if (self.xres, self.yres) != (1920, 1080):
			gMainDC.getInstance().setResolution(1920, 1080)
			getDesktop(0).resize(eSize(1920, 1080))
			self.onClose.append(self.__close)

		self["actions"] = NumberActionMap(["InputActions", "OkCancelActions"],
		{
			"1": self.keyNumber,
			"2": self.keyNumber,
			"3": self.keyNumber,
			"4": self.keyNumber,
			"5": self.keyNumber,
			"6": self.keyNumber,
			"8": self.keyNumber,
			"9": self.keyNumber,
			"ok": self.ok,
			"cancel": self.cancel
		})

	def __close(self):
		gMainDC.getInstance().setResolution(self.xres, self.yres)
		getDesktop(0).resize(eSize(self.xres, self.yres))


class FullUHDTestScreen(OverscanTestScreen):
	skin = """<screen position="0,0" size="0,0"/>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("UHD Test"))
		self.oldref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.session.nav.stopService()
		#Console().ePopen("/usr/bin/showiframe %s" % resolveFilename(SCOPE_PLUGINS, "SystemPlugins/VideoTune/testbeeld-4k.mvi"))
		self.hide()
		self.onClose.append(self.__close)

		self["actions"] = NumberActionMap(["InputActions", "OkCancelActions"],
		{
			"1": self.keyNumber,
			"2": self.keyNumber,
			"3": self.keyNumber,
			"4": self.keyNumber,
			"5": self.keyNumber,
			"6": self.keyNumber,
			"7": self.keyNumber,
			"8": self.keyNumber,
			"9": self.keyNumber,
			"ok": self.ok,
			"cancel": self.cancel
		})

	def __close(self):
		self.session.nav.playService(self.oldref)


class VideoFinetune(Screen):
	skin = """
		<screen position="fill">
			<widget source="Canvas" render="Canvas" position="fill" zPosition="2"/>
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("VideoFinetune"))

		port = config.av.videoport.value  # noqa F841
		self.hasUHD = False
		#self.hasUHD = port and config.av.videomode[port].value.startswith("2160")

		self["Canvas"] = CanvasSource()

		self.basic_colors = [RGB(255, 255, 255), RGB(255, 255, 0), RGB(0, 255, 255), RGB(0, 255, 0), RGB(255, 0, 255), RGB(255, 0, 0), RGB(0, 0, 255), RGB(0, 0, 0)]
		self.fontsize = getDesktop(0).size().height() == 1080 and 30 or 20

		if fileExists("/proc/stb/fb/dst_left"):
			self.left = open("/proc/stb/fb/dst_left").read()
			self.width = open("/proc/stb/fb/dst_width").read()
			self.top = open("/proc/stb/fb/dst_top").read()
			self.height = open("/proc/stb/fb/dst_height").read()
			if self.left != "00000000" or self.top != "00000000" or self.width != "000002d0" or self.height != "0000000240":
				open("/proc/stb/fb/dst_left", "w").write("00000000")
				open("/proc/stb/fb/dst_width", "w").write("000002d0")
				open("/proc/stb/fb/dst_top", "w").write("00000000")
				open("/proc/stb/fb/dst_height", "w").write("0000000240")
				self.onClose.append(self.__close)

		self["actions"] = NumberActionMap(["InputActions", "OkCancelActions"],
		{
			"1": self.keyNumber,
			"2": self.keyNumber,
			"3": self.keyNumber,
			"4": self.keyNumber,
			"5": self.keyNumber,
			"6": self.keyNumber,
			"7": self.keyNumber,
			"8": self.keyNumber,
			"9": self.keyNumber,
			"ok": self.callNext,
			"cancel": self.close,
		})
		self.testpic_brightness()

	def __close(self):
		open("/proc/stb/fb/dst_left", "w").write(self.left)
		open("/proc/stb/fb/dst_width", "w").write(self.width)
		open("/proc/stb/fb/dst_top", "w").write(self.top)
		open("/proc/stb/fb/dst_height", "w").write(self.height)

	def keyNumber(self, key):
		(self.testpic_brightness, self.testpic_contrast, self.testpic_colors, self.testpic_filter, self.testpic_gamma, self.testpic_overscan, self.testpic_fullhd, self.testpic_uhd, self.testpic_pixels)[key - 1]()

	def callNext(self):
		if self.next:
			self.next()

	def bbox(self, x, y, width, height, col, xx, yy):
		c = self["Canvas"]
		c.fill(x, y, xx, yy, col)
		c.fill(x + width - xx, y, xx, yy, col)
		c.fill(x, y + height - yy, xx, yy, col)
		c.fill(x + width - xx, y + height - yy, xx, yy, col)

	def testpic_brightness(self):
		self.next = self.testpic_contrast
		self.show()

		c = self["Canvas"]

		xres, yres = getDesktop(0).size().width(), getDesktop(0).size().height()

		bbw, bbh = xres // 192, yres // 192  # noqa F841
		c.fill(0, 0, xres, yres, RGB(0, 0, 0))

		for i in list(range(15)):
			col = i * 116 // 14
			height = yres // 3
			eh = height // 8
			offset = yres // 6 + eh * i
			x = xres * 2 // 3
			width = yres // 6

			c.fill(x, offset, width, eh, RGB(col, col, col))
			if col == 0 or col == 16 or col == 116:
				c.fill(x, offset, width, 2, RGB(255, 255, 255))
			if i < 2:
				c.writeText(x + width, offset, width, eh, RGB(255, 255, 255), RGB(0, 0, 0), gFont("Regular", self.fontsize), "%d." % (i + 1))

		c.writeText(xres // 10, yres // 6 - self.fontsize * 3, xres * 3 // 5, 40, RGB(128, 255, 255), RGB(0, 0, 0), gFont("Regular", self.fontsize * 2),
			_("Brightness"))
		c.writeText(xres // 10, yres // 6, xres // 2, yres * 4 // 6, RGB(255, 255, 255), RGB(0, 0, 0), gFont("Regular", self.fontsize),
			_("If your TV has a brightness or contrast enhancement, disable it. If there is something called \"dynamic\", "
				"set it to standard. Adjust the backlight level to a value suiting your taste. "
				"Turn down contrast on your TV as much as possible.\nThen turn the brightness setting as "
				"low as possible, but make sure that the two lowermost shades of gray stay distinguishable.\n"
				"Do not care about the bright shades now. They will be set up in the next step.\n"
				"If you are happy with the result, press OK."),
				RT_WRAP)

		c.flush()

	def testpic_contrast(self):
		self.next = self.testpic_colors
		self.show()

		c = self["Canvas"]

		xres, yres = getDesktop(0).size().width(), getDesktop(0).size().height()

		bbw, bbh = xres // 192, yres // 192  # noqa F841
		c.fill(0, 0, xres, yres, RGB(0, 0, 0))

		bbw = xres // 192  # noqa F841
		bbh = yres // 192  # noqa F841
		c.fill(0, 0, xres, yres, RGB(255, 255, 255))

		for i in list(range(15)):
			col = 185 + i * 5
			height = yres // 3
			eh = height // 8
			offset = yres // 6 + eh * i
			x = xres * 2 // 3
			width = yres // 6

			c.fill(x, offset, width, eh, RGB(col, col, col))
			if col == 185 or col == 235 or col == 255:
				c.fill(x, offset, width, 2, RGB(0, 0, 0))
			if i >= 13:
				c.writeText(x + width, offset, width, eh, RGB(0, 0, 0), RGB(255, 255, 255), gFont("Regular", self.fontsize), "%d." % (i - 13 + 1))

		c.writeText(xres // 10, yres // 6 - self.fontsize * 3, xres * 3 // 5, 40, RGB(128, 0, 0), RGB(255, 255, 255), gFont("Regular", self.fontsize * 2),
			_("Contrast"))
		c.writeText(xres // 10, yres // 6, xres // 2, yres * 4 // 6, RGB(0, 0, 0), RGB(255, 255, 255), gFont("Regular", self.fontsize),
			_("Now, use the contrast setting to turn up the brightness of the background as much as possible, "
				"but make sure that you can still see the difference between the two brightest levels of shades."
				"If you have done that, press OK."),
				RT_WRAP)

		c.flush()

	def testpic_colors(self):
		self.next = self.testpic_filter
		self.show()

		c = self["Canvas"]

		xres, yres = getDesktop(0).size().width(), getDesktop(0).size().height()

		bbw = xres // 192
		bbh = yres // 192
		c.fill(0, 0, xres, yres, RGB(255, 255, 255))

		for i in list(range(33)):
			col = i * 255 // 32
			width = xres - xres // 5
			ew = width // 33
			offset = xres // 10 + ew * i
			y = yres * 2 // 3
			height = yres // 20
			o = yres // 60

			if i < 16:
				c1 = 0xFF
				c2 = 0xFF - (0xFF * i // 16)
			else:
				c1 = 0xFF - (0xFF * (i - 16) // 16)
				c2 = 0

			c.fill(offset, y, ew, height, RGB(c1, c2, c2))
			c.fill(offset, y + (height + o) * 1, ew, height, RGB(c2, c1, c2))
			c.fill(offset, y + (height + o) * 2, ew, height, RGB(c2, c2, c1))
			c.fill(offset, y + (height + o) * 3, ew, height, RGB(col, col, col))

			if i == 0:
				self.bbox(offset, y, ew, height, RGB(0, 0, 0), bbw, bbh)
				self.bbox(offset, y + (height + o) * 1, ew, height, RGB(0, 0, 0), bbw, bbh)
				self.bbox(offset, y + (height + o) * 2, ew, height, RGB(0, 0, 0), bbw, bbh)

			for i in list(range(8)):
				height = yres // 3
				eh = height // 8
				offset = yres // 6 + eh * i
				x = xres * 2 // 3
				width = yres // 6

				c.fill(x, offset, width, eh, self.basic_colors[i])
				if i == 0:
					self.bbox(x, offset, width, eh, RGB(0, 0, 0), bbw, bbh)

		c.writeText(xres // 10, yres // 6 - self.fontsize * 3, xres * 3 // 5, 40, RGB(128, 0, 0), RGB(255, 255, 255), gFont("Regular", self.fontsize * 2),
			_("Color"))
		c.writeText(xres // 10, yres // 6, xres // 2, yres * 4 // 6, RGB(0, 0, 0), RGB(255, 255, 255), gFont("Regular", self.fontsize),
			_("Adjust the color settings so that all the color shades are distinguishable, but appear as saturated as possible. "
				"If you are happy with the result, press OK to close the video fine-tuning, or use the number keys to select other test screens."),
				RT_WRAP)

		c.flush()

	def testpic_filter(self):
		self.next = self.testpic_gamma
		self.show()

		c = self["Canvas"]

		xres, yres = getDesktop(0).size().width(), getDesktop(0).size().height()

		c.fill(0, 0, xres, yres, RGB(64, 64, 64))

		width = xres - xres // 5
		offset = xres // 10
		yb = yres * 2 // 3
		height = yres // 20
		o = yres // 60
		border = xres // 60

		g1 = 255
		g2 = 128

		c.fill(offset - border, yb - border, border * 2 + width, border * 2 + (height * 3 + o * 2), RGB(g1, g1, g1))

		for x in list(range(0, width, 2)):
			c.fill(offset + x, yb, 1, height, RGB(g2, g2, g2))

		for x in list(range(0, width, 4)):
			c.fill(offset + x, yb + (o + height), 2, height, RGB(g2, g2, g2))

		for x in list(range(0, width, 8)):
			c.fill(offset + x, yb + (o + height) * 2, 4, height, RGB(g2, g2, g2))

		c.flush()

	def testpic_gamma(self):
		self.next = self.testpic_overscan
		self.show()

		c = self["Canvas"]

		xres, yres = getDesktop(0).size().width(), getDesktop(0).size().height()

		c.fill(0, 0, xres, yres, RGB(0, 0, 0))

		width = xres - xres // 5
		offset_x = xres // 10

		height = yres - yres // 5
		offset_y = yres // 10

		for y in list(range(0, height, 4)):
			c.fill(offset_x, offset_y + y, width // 2, 2, RGB(255, 255, 255))

		posY = 0
		fnt = gFont("Regular", height // 14)
		for i in list(range(1, 15)):
			y = i * height // 14
			h = y - posY
			gamma = 0.6 + i * 0.2
			col = int(math.pow(.5, 1.0 / gamma) * 256.0)
			c.fill(offset_x + width // 2, offset_y + posY, width // 2, h, RGB(col, col, col))

			c.writeText(offset_x + width // 2, offset_y + posY, width // 2, h, RGB(0, 0, 0), RGB(col, col, col), fnt, "%1.2f" % gamma, RT_WRAP | RT_HALIGN_RIGHT)
			posY = y

		c.flush()

	def testpic_overscan(self):
		self.next = BoxInfo.getItem("HasFullHDSkinSupport") and self.testpic_fullhd or self.testpic_pixels
		self.hide()
		self.session.openWithCallback(self.testpicCallback, OverscanTestScreen)

	def testpic_fullhd(self):
		if BoxInfo.getItem("HasFullHDSkinSupport"):
			self.next = self.hasUHD and self.testpic_uhd or self.testpic_pixels
			self.hide()
			self.session.openWithCallback(self.testpicCallback, FullHDTestScreen)
		else:
			self.testpic_pixels()

	def testpic_uhd(self):
		if self.hasUHD:
			self.next = self.testpic_pixels
			self.hide()
			self.session.openWithCallback(self.testpicCallback, FullUHDTestScreen)
		else:
			self.testpic_pixels()

	def testpic_pixels(self):
		self.next = self.testpic_brightness
		self.hide()
		self.session.openWithCallback(self.testpicCallback, PixelsTestScreen)

	def testpicCallback(self, key):
		if key:
			if key is True:
				self.next()
			else:
				self.keyNumber(key)
		else:
			self.close()


class PixelsTestScreen(Screen):
	skin = """
		<screen position="fill">
			<widget source="Canvas" render="Canvas" position="fill" zPosition="2"/>
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Pixel Test"))

		self["Canvas"] = CanvasSource()
		self.fontsize = getDesktop(0).size().height() == 1080 and 30 or 20
		self.xres, self.yres = getDesktop(0).size().width(), getDesktop(0).size().height()

		self["actions"] = NumberActionMap(["InputActions", "OkCancelActions", "ColorActions"],
		{
			"1": self.keyNumber,
			"2": self.keyNumber,
			"3": self.keyNumber,
			"4": self.keyNumber,
			"5": self.keyNumber,
			"6": self.keyNumber,
			"7": self.keyNumber,
			"8": self.keyNumber,
			"red": self.togglered,
			"green": self.togglegreen,
			"yellow": self.intro,
			"blue": self.toggleblue,
			"ok": self.ok,
			"cancel": self.cancel,
			"left": self.left,
			"right": self.right,
		})
		self.intro()

	def intro(self):
		c = self["Canvas"]
		c.fill(0, 0, self.xres, self.yres, RGB(0, 0, 0))
		c.writeText(self.xres // 10, self.yres // 6 - self.fontsize * 3, self.xres * 3 // 5, 40, RGB(255, 128, 255), RGB(0, 0, 0), gFont("Regular", self.fontsize * 2),
			_("Pixels\n"))
		c.writeText(self.xres // 10, self.yres // 6, self.xres // 2, self.yres * 4 // 6, RGB(255, 255, 255), RGB(0, 0, 0), gFont("Regular", self.fontsize),
			_("Can be used to test defect pixels on TV screen.\n\n"
			"Available color test screens:\n\n"
			"red\ngreen\nblue\nwhite\nblack\ncyan\nmagenta\nyellow\n\n"
			"Screens change with left/right buttons or use red, green, blue to toggle.\n"
			"Yellow for returning back to this intro"),
			RT_WRAP)
		c.flush()
		self.color = 8

	def left(self):
		self.setArea((7, 2, 4, 0, 8, 3, 5, 1, 6)[self.color])

	def right(self):
		self.setArea((3, 7, 1, 5, 2, 6, 8, 0, 4)[self.color])

	def togglered(self):
		self.setArea(self.color ^ 4)

	def togglegreen(self):
		self.setArea(self.color ^ 2)

	def toggleblue(self):
		self.setArea(self.color ^ 1)

	def setArea(self, color):
		if color == 8:
			self.intro()
		else:
			self.color = color & 7
			self.show()
			c = self["Canvas"]
			c.fill(0, 0, self.xres, self.yres, RGB(color & 4 and 255, color & 2 and 255, color & 1 and 255))
			c.flush()

	def ok(self):
		self.close(True)

	def cancel(self):
		self.close(False)

	def keyNumber(self, key):
		self.close(key)
