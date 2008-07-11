from Screens.Screen import Screen
from Components.Sources.CanvasSource import CanvasSource
from Components.ActionMap import ActionMap
from enigma import gFont
from enigma import RT_HALIGN_RIGHT, RT_WRAP

def RGB(r,g,b):
	return (r<<16)|(g<<8)|b

class VideoFinetune(Screen):
	skin = """
		<screen position="0,0" size="720,576">
			<widget source="Canvas" render="Canvas" position="0,0" size="720,576" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["Canvas"] = CanvasSource()

		self.basic_colors = [RGB(255, 255, 255), RGB(255, 255, 0), RGB(0, 255, 255), RGB(0, 255, 0), RGB(255, 0, 255), RGB(255, 0, 0), RGB(0, 0, 255), RGB(0, 0, 0)]

		self["actions"] = ActionMap(["InputActions", "OkCancelActions"],
		{
			"1": self.testpic_brightness,
			"2": self.testpic_contrast,
#			"3": self.testpic_colors,
			"3": self.testpic_filter,
			"4": self.testpic_gamma,
			"5": self.testpic_fubk,
			"ok": self.callNext,
			"cancel": self.close,
		})
		self.testpic_brightness()

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
		c = self["Canvas"]

		xres, yres = 720, 576

		bbw, bbh = xres / 192, yres / 192
		c.fill(0, 0, xres, yres, RGB(0,0,0))

#		for i in range(8):
#			col = (7-i) * 255 / 7
#			width = xres - xres/5
#			ew = width / 15
#			offset = xres/10 + ew * i
#			y = yres * 2 / 3
#			height = yres / 6
#
#			c.fill(offset, y, ew, height, RGB(col, col, col))
#
#			if col == 0 or col == 16 or col == 116:
#				self.bbox(offset, y, ew, height, RGB(255,255,255), bbw, bbh)

		for i in range(15):
			col = i * 116 / 14
			height = yres / 3
			eh = height / 8
			offset = yres/6 + eh * i
			x = xres * 2 / 3
			width = yres / 6

			c.fill(x, offset, width, eh, RGB(col, col, col))
			if col == 0 or col == 16 or col == 116:
				c.fill(x, offset, width, 2, RGB(255, 255, 255))
#			if col == 0 or col == 36:
#				self.bbox(x, offset, width, eh, RGB(255,255,255), bbw, bbh)
			if i < 2:
				c.writeText(x + width, offset, width, eh, RGB(255, 255, 255), RGB(0,0,0), gFont("Regular", 20), "%d." % (i+1))

		c.writeText(xres / 10, yres / 6 - 40, xres * 3 / 5, 40, RGB(128,255,255), RGB(0,0,0), gFont("Regular", 40), 
			_("Brightness"))
		c.writeText(xres / 10, yres / 6, xres * 4 / 7, yres / 6, RGB(255,255,255), RGB(0,0,0), gFont("Regular", 20),
			_("If your TV has a brightness or contrast enhancement, disable it. If there is something called \"dynamic\", "
				"set it to standard. Adjust the backlight level to a value suiting your taste. "
				"Turn down contrast on your TV as much as possible.\nThen turn the brightness setting as "
				"low as possible, but make sure that the two lowermost shades of gray stay distinguishable.\n"
				"Do not care about the bright shades now. They will be set up in the next step.\n"
				"If you are happy with the result, press OK."),
				RT_WRAP)

		c.flush()

	def testpic_contrast(self):
#		self.next = self.testpic_colors
		self.next = self.close

		c = self["Canvas"]

		xres, yres = 720, 576

		bbw, bbh = xres / 192, yres / 192
		c.fill(0, 0, xres, yres, RGB(0,0,0))

		bbw = xres / 192
		bbh = yres / 192
		c.fill(0, 0, xres, yres, RGB(255,255,255))

#		for i in range(15):
#			col = 185 + i * 5
#			width = xres - xres/5
#			ew = width / 15
#			offset = xres/10 + ew * i
#			y = yres * 2 / 3
#			height = yres / 6
#
#			c.fill(offset, y, ew, height, RGB(col, col, col))
#
#			if col == 185 or col == 235 or col == 255:
#				self.bbox(offset, y, ew, height, RGB(0,0,0), bbw, bbh)

		for i in range(15):
#			col = (7-i) * 255 / 7
			col = 185 + i * 5
			height = yres / 3
			eh = height / 8
			offset = yres/6 + eh * i
			x = xres * 2 / 3
			width = yres / 6

			c.fill(x, offset, width, eh, RGB(col, col, col))
#			if col == 0 or col == 36:
#				self.bbox(x, offset, width, eh, RGB(255,255,255), bbw, bbh);
#			if col == 255:
#				self.bbox(x, offset, width, eh, RGB(0,0,0), bbw, bbh);
			if col == 185 or col == 235 or col == 255:
				c.fill(x, offset, width, 2, RGB(0,0,0)) 
			if i >= 13:
				c.writeText(x + width, offset, width, eh, RGB(0, 0, 0), RGB(255, 255, 255), gFont("Regular", 20), "%d." % (i-13+1))

		c.writeText(xres / 10, yres / 6 - 40, xres * 3 / 5, 40, RGB(128,0,0), RGB(255,255,255), gFont("Regular", 40), 
			_("Contrast"))
		c.writeText(xres / 10, yres / 6, xres / 2, yres / 6, RGB(0,0,0), RGB(255,255,255), gFont("Regular", 20),
			_("Now, use the contrast setting to turn up the brightness of the background as much as possible, "
				"but make sure that you can still see the difference between the two brightest levels of shades."
				"If you have done that, press OK."),
				RT_WRAP)

		c.flush()

	def testpic_colors(self):
		self.next = self.close

		c = self["Canvas"]

		xres, yres = 720, 576

		bbw = xres / 192
		bbh = yres / 192
		c.fill(0, 0, xres, yres, RGB(255,255,255))

		for i in range(33):
			col = i * 255 / 32;
			width = xres - xres/5;
			ew = width / 33;
			offset = xres/10 + ew * i;
			y = yres * 2 / 3;
			height = yres / 20;
			o = yres / 60;

			if i < 16:
				c1 = 0xFF;
				c2 = 0xFF - (0xFF * i / 16);
			else:
				c1 = 0xFF - (0xFF * (i - 16) / 16);
				c2 = 0;

			c.fill(offset, y, ew, height, RGB(c1, c2, c2))
			c.fill(offset, y + (height + o) * 1, ew, height, RGB(c2, c1, c2))
			c.fill(offset, y + (height + o) * 2, ew, height, RGB(c2, c2, c1))
			c.fill(offset, y + (height + o) * 3, ew, height, RGB(col, col, col))

			if i == 0:
				self.bbox(offset, y, ew, height, RGB(0,0,0), bbw, bbh);
				self.bbox(offset, y + (height + o) * 1, ew, height, RGB(0,0,0), bbw, bbh);
				self.bbox(offset, y + (height + o) * 2, ew, height, RGB(0,0,0), bbw, bbh);

			for i in range(8):
				height = yres / 3;
				eh = height / 8;
				offset = yres/6 + eh * i;
				x = xres * 2 / 3;
				width = yres / 6;

				c.fill(x, offset, width, eh, self.basic_colors[i])
				if i == 0:
					self.bbox(x, offset, width, eh, RGB(0,0,0), bbw, bbh)

		c.writeText(xres / 10, yres / 6 - 40, xres * 3 / 5, 40, RGB(128,0,0), RGB(255,255,255), gFont("Regular", 40), 
			("Color"))
		c.writeText(xres / 10, yres / 6, xres / 2, yres / 6, RGB(0,0,0), RGB(255,255,255), gFont("Regular", 20),
			_("Adjust the color settings so that all the color shades are distinguishable, but appear as saturated as possible. "
				"If you are happy with the result, press OK to close the video fine-tuning, or use the number keys to select other test screens."),
				RT_WRAP)

		c.flush()

	def testpic_filter(self):
		c = self["Canvas"]

		xres, yres = 720, 576

		c.fill(0, 0, xres, yres, RGB(64, 64, 64))

		width = xres - xres/5
		offset = xres/10
		yb = yres * 2 / 3
		height = yres / 20
		o = yres / 60
		border = xres / 60

		g1 = 255
		g2 = 128

		c.fill(offset - border, yb - border, border * 2 + width, border * 2 + (height * 3 + o * 2), RGB(g1, g1, g1))

		for x in xrange(0, width, 2):
			c.fill(offset + x, yb, 1, height, RGB(g2,g2,g2))

		for x in xrange(0, width, 4):
			c.fill(offset + x, yb + (o + height), 2, height, RGB(g2,g2,g2))

		for x in xrange(0, width, 8):
			c.fill(offset + x, yb + (o + height) * 2, 4, height, RGB(g2,g2,g2))

		c.flush()

	def testpic_gamma(self):
		self.next = None

		c = self["Canvas"]

		xres, yres = 720, 576

		c.fill(0, 0, xres, yres, RGB(0, 0, 0))

		width = xres - xres/5
		offset_x = xres/10

		height = yres - yres/5
		offset_y = yres/10

		for y in xrange(0, height, 4):
			c.fill(offset_x, offset_y + y, width/2, 2, RGB(255,255,255))

		l = 0
		fnt = gFont("Regular", height / 14)
		import math
		for i in xrange(1, 15):
			y = i * height / 14
			h = y - l
			gamma = 0.6 + i * 0.2
			col = int(math.pow(.5, 1.0/gamma) * 256.0)
			c.fill(offset_x + width/2, offset_y + l, width/2, h, RGB(col,col,col))

			c.writeText(offset_x + width/2, offset_y + l, width/2, h, RGB(0,0,0), RGB(col,col,col), fnt, "%1.2f" % gamma, RT_WRAP|RT_HALIGN_RIGHT)
			l = y

		c.flush()

	def testpic_fubk(self):
		self.next = None

		# TODO:
		# this test currently only works for 4:3 aspect.
		# also it's hardcoded to 720,576
		c = self["Canvas"]

		xres, yres = 720, 576

		c.fill(0, 0, xres, yres, RGB(128, 128, 128))

		for x in xrange(6, xres, 44):
			c.fill(x, 0, 3, yres, RGB(255,255,255))

		for y in xrange(34, yres, 44):
			c.fill(0, y, xres, 3, RGB(255,255,255))

		for i in range(8):
			c.fill(140+i*55, 80, 55, 80, self.basic_colors[i])
			g = i * 255 / 7
			c.fill(140+i*55, 160, 55, 80, RGB(g,g,g))

		x = 0
		phase = 0

		while x < 440:
			freq = (440 - x) / 44 + 1
			if phase:
				col = RGB(255,255,255)
			else:
				col = RGB(0,0,0)
			c.fill(140+x, 320, freq, 160, col)
			x += freq
			phase = not phase

		c.flush()

