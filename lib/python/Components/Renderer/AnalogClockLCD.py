# original code is from openmips gb Team: [OMaClockLcd] Renderer #
# Thx to arn354 #

import math
from Renderer import Renderer
from skin import parseColor
from enigma import eCanvas, eSize, gRGB, eRect
from Components.VariableText import VariableText
from Components.config import config

class AnalogClockLCD(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.fColor = gRGB(255, 255, 255, 0)
		self.fColors = gRGB(255, 0, 0, 0)
		self.fColorm = gRGB(255, 0, 0, 0)
		self.fColorh = gRGB(255, 255, 255, 0)
		self.bColor = gRGB(0, 0, 0, 255)
		self.forend = -1
		self.linewidth = 1
                self.positionheight = 1
                self.positionwidth = 1
                self.linesize = 1
                
	GUI_WIDGET = eCanvas

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, what,) in self.skinAttributes:
			if (attrib == 'hColor'):
				self.fColorh = parseColor(what)
			elif (attrib == 'mColor'):
				self.fColorm = parseColor(what)
			elif (attrib == 'sColor'):
				self.fColors = parseColor(what)
			elif (attrib == 'linewidth'):
				self.linewidth = int(what)
			elif (attrib == 'positionheight'):
				self.positionheight = int(what)
			elif (attrib == 'positionwidth'):
				self.positionwidth = int(what)
			elif (attrib == 'linesize'):
				self.linesize = int(what)
			else:
				attribs.append((attrib, what))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def calc(self, w, r, m, m1):
		a = (w * 6)
		z = (math.pi / 180)
		x = int(round((r * math.sin((a * z)))))
		y = int(round((r * math.cos((a * z)))))
		return ((m + x),(m1 - y))

	def hand(self,opt):
		width = self.positionwidth
		height = self.positionheight
		r = (width / 2)
		r1 = (height / 2)
		l = self.linesize  
		if opt == 'sec':
			l = self.linesize  
			self.fColor = self.fColors
		elif opt == 'min':
			l = self.linesize 
			self.fColor = self.fColorm
		else:
			self.fColor = self.fColorh
		(endX, endY,) = self.calc(self.forend, l, r, r1)
		self.line_draw(r, r1, endX, endY)

	def line_draw(self, x0, y0, x1, y1):
		steep = (abs((y1 - y0)) > abs((x1 - x0)))
		if steep:
			x0,y0 = y0,x0
			x1,y1 = y1,x1
		if (x0 > x1):
			x0,x1 = x1,x0
			y0,y1 = y1,y0
		if (y0 < y1):
			ystep = 1
		else:
			ystep = -1
		deltax = (x1 - x0)
		deltay = abs((y1 - y0))
		error = (-deltax / 2)
		y = y0
		for x in range(x0, (x1 + 1)):
			if steep:
				self.instance.fillRect(eRect(y, x, self.linewidth, self.linewidth), self.fColor)
			else:
				self.instance.fillRect(eRect(x, y, self.linewidth, self.linewidth), self.fColor)
			error = (error + deltay)
			if (error > 0):
				y = (y + ystep)
				error = (error - deltax)

	def changed(self, what):
		opt = (self.source.text).split(',')
		try:
			sopt = int(opt[0])
			if len(opt) < 2:
				opt.append('')
		except Exception, e:
			return

		if (what[0] == self.CHANGED_CLEAR):
			pass
		elif self.instance:
			self.instance.show()
			if (self.forend != sopt):
				self.forend = sopt
				self.instance.clear(self.bColor)
				self.hand(opt[1])

	def parseSize(self, str):
		(x, y,) = str.split(',')
		return eSize(int(x), int(y))

	def postWidgetCreate(self, instance):
		for (attrib, value,) in self.skinAttributes:
			if ((attrib == 'size') and self.instance.setSize(self.parseSize(value))):
				pass
		self.instance.clear(self.bColor)
