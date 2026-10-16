# original code is from openmips gb Team: [OMaClockLcd] Renderer #
# Thx to arn354 #

from math import cos, pi, sin

from enigma import eCanvas, eRect, eSize, gRGB

from skin import parseColor
from Components.Renderer.Renderer import Renderer


class AnalogClockLCD(Renderer):
	GUI_WIDGET = eCanvas

	def __init__(self):
		Renderer.__init__(self)
		self.fColor = gRGB(255, 255, 255, 0)
		self.bColor = gRGB(0, 0, 0, 255)
		self.forend = -1
		self.linewidth = 1
		self.positionheight = 1
		self.positionwidth = 1
		self.linesize = 10

	def applySkin(self, desktop, parent):  # HINT: clock center = position="(x + linesize / 2), (y + linesize / 2)"
		attribs = []
		for attrib, what in self.skinAttributes:
			match attrib:
				case "bColor":  # hand backgroundColor
					self.bColor = parseColor(what)
				case "fColor" | "hColor" | "mColor" | "sColor":  # hand foregroundColor (compatible to old attribs 'h/m/sColor')
					self.fColor = parseColor(what)
				case "linesize":  # hand length
					self.linesize = int(what)
				case "linewidth":  # hand thickness
					self.linewidth = int(what)
				case "positionheight":  # oval dial height, typically >= 2 * linesize
					self.positionheight = int(what)
				case "positionwidth":  # oval dial width, typically >= 2 * linesize
					self.positionwidth = int(what)
				case _:
					attribs.append((attrib, what))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def postWidgetCreate(self, instance):
		for attrib, value in self.skinAttributes:
			if attrib == "size":
				self.instance.setSize(self.parseSize(value))
		self.instance.clear(self.bColor)

	def changed(self, what):
		opt = self.source.text.split(",")
		if isinstance(opt[0], (str, int, float)):
			sopt = int(opt[0])
			if len(opt) < 2:
				opt.append("")
			if self.instance and what[0] != self.CHANGED_CLEAR:
				self.instance.show()
				if self.forend != sopt:
					self.forend = sopt
					self.instance.clear(self.bColor)
					self.hand()

	def calc(self, w, r, m, m1):
		a, z = w * 6, pi / 180
		x = int(round(r * sin(a * z)))
		y = int(round(r * cos(a * z)))
		return m + x, m1 - y

	def hand(self):
		width = self.positionwidth
		height = self.positionheight
		r, r1 = width / 2, height / 2
		x, y = self.calc(self.forend, self.linesize, r, r1)
		self.line_draw(r, r1, x, y)

	def line_draw(self, x0, y0, x1, y1):
		steep = abs(y1 - y0) > abs(x1 - x0)
		if steep:
			x0, y0 = y0, x0
			x1, y1 = y1, x1
		if x0 > x1:
			x0, x1 = x1, x0
			y0, y1 = y1, y0
		ystep = 1 if y0 < y1 else -1
		deltax = x1 - x0
		deltay = abs(y1 - y0)
		error = -deltax / 2
		y = int(y0)
		for x in range(int(x0), (int(x1) + 1)):
			a, b = (y, x) if steep else (x, y)
			self.instance.fillRect(eRect(a, b, self.linewidth, self.linewidth), self.fColor)
			error = error + deltay
			if error > 0:
				y = y + ystep
				error = error - deltax

	def parseSize(self, str):
		x, y = str.split(",")
		return eSize(int(x), int(y))
