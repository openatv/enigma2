# -*- coding: utf-8 -*-
#
# Running Text Renderer for Enigma2 (RunningText.py)
# Coded by vlamo (c) 2010
#
# Version: 1.4 (02.04.2011 17:15)
# Support: http://dream.altmaster.net/
#

from Renderer import Renderer

from enigma import eCanvas, eRect, gRGB, eLabel, eTimer, fontRenderClass, ePoint, eSize, gFont
from enigma import RT_WRAP, RT_HALIGN_LEFT, RT_HALIGN_CENTER, RT_HALIGN_RIGHT, RT_HALIGN_BLOCK, RT_VALIGN_TOP, RT_VALIGN_CENTER, RT_VALIGN_BOTTOM
from skin import parseColor, parseFont

# scroll type:
NONE     = 0
RUNNING  = 1
SWIMMING = 2
AUTO     = 3
# direction:
LEFT     = 0
RIGHT    = 1
TOP      = 2
BOTTOM   = 3
# halign:
#LEFT     = 0
#RIGHT    = 1
CENTER   = 2
BLOCK    = 3

def RGB(r,g,b):
	return (r<<16)|(g<<8)|b

class VRunningText(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.type     = NONE
		self.txfont   = gFont("Regular", 14)
		self.fcolor   = gRGB(RGB(255,255,255))
		self.bcolor   = gRGB(RGB(0,0,0))
		self.scolor   = None
		self.soffset  = (0,0)
		self.txtflags = 0 #RT_WRAP
		self.txtext   = ""
		self.test_label = self.mTimer = self.mStartPoint = None
		self.X = self.Y = self.W = self.H = self.mStartDelay = 0
		self.mAlways = 1	# always move text
		self.mStep = 1		# moving step: 1 pixel per 1 time
		self.mStepTimeout = 5000	# step timeout: 1 step per 50 milliseconds ( speed: 20 pixel per second )
		self.direction = LEFT
		self.mLoopTimeout = self.mOneShot = 0
		self.mRepeat = 0

	GUI_WIDGET = eCanvas

	def postWidgetCreate(self, instance):
		for (attrib, value) in self.skinAttributes:
			if attrib == "size":
				x, y = value.split(',')
				self.W, self.H = int(x), int(y)

		self.instance.setSize( eSize(self.W,self.H) )
		self.test_label = eLabel(instance)
		self.mTimer = eTimer()
		self.mTimer.callback.append(self.movingLoop)

	def preWidgetRemove(self, instance):
		self.mTimer.stop()
		self.mTimer.callback.remove(self.movingLoop)
		self.mTimer = None
		self.test_label = None

	def applySkin(self, desktop, screen):
		def retValue(val, limit, default, Min=False):
			try:
				if Min:
					x = min(limit, int(val))
				else:
					x = max(limit, int(val))
			except:
					x = default
			return x

		self.halign = valign = eLabel.alignLeft
		if self.skinAttributes:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "font":
					self.txfont = parseFont(value, ((1,1),(1,1)))
				elif attrib == "foregroundColor":
					self.fcolor = parseColor(value)
				elif attrib == "backgroundColor":
					self.bcolor = parseColor(value)
				elif attrib == "shadowColor":
					self.scolor = parseColor(value)
				elif attrib == "shadowOffset":
					x, y = value.split(',')
					self.soffset = (int(x),int(y))
				elif attrib == "valign" and value in ("top","center","bottom"):
					valign = { "top": eLabel.alignTop, "center": eLabel.alignCenter, "bottom": eLabel.alignBottom }[value]
					self.txtflags |= { "top": RT_VALIGN_TOP, "center": RT_VALIGN_CENTER, "bottom": RT_VALIGN_BOTTOM }[value]
				elif attrib == "halign" and value in ("left","center","right","block"):
					self.halign = { "left": eLabel.alignLeft, "center": eLabel.alignCenter, "right": eLabel.alignRight, "block": eLabel.alignBlock }[value]
					self.txtflags |= { "left": RT_HALIGN_LEFT, "center": RT_HALIGN_CENTER, "right": RT_HALIGN_RIGHT, "block": RT_HALIGN_BLOCK }[value]
				elif attrib == "noWrap":
					if value == "0":
						self.txtflags |= RT_WRAP
					else:
						self.txtflags &= ~RT_WRAP
				elif attrib == "options":
					options = value.split(',')
					for opt in options:
						val = ''
						pos = opt.find('=')
						if pos != -1:
							val = opt[pos+1:].strip()
							opt = opt[:pos].strip()
						if opt == "wrap":
							if val == "0":
								self.txtflags &= ~RT_WRAP
							else:
								self.txtflags |= RT_WRAP
						elif opt == "nowrap":
							if val == "0":
								self.txtflags |= RT_WRAP
							else:
								self.txtflags &= ~RT_WRAP
						elif opt == "movetype" and val in ("none","running","swimming"):
							self.type = {"none": NONE, "running": RUNNING, "swimming": SWIMMING}[val]
						elif opt =="direction" and val in ("left","right","top","bottom"):
							self.direction = { "left": LEFT, "right": RIGHT, "top": TOP, "bottom": BOTTOM }[val]
						elif opt == "step" and val:
							#retValue(val, limit, default, Min=False)
							self.mStep = retValue(val, 1, self.mStep)
						elif opt == "steptime" and val:
							self.mStepTimeout = retValue(val, 25, self.mStepTimeout)
						elif opt == "startdelay" and val:
							self.mStartDelay = retValue(val, 0, self.mStartDelay)
						elif opt == "pause" and val:
							self.mLoopTimeout = retValue(val, 0, self.mLoopTimeout)
						elif opt == "oneshot" and val:
							self.mOneShot = retValue(val, 0, self.mOneShot)
						elif opt =="repeat" and val:
							self.mRepeat = retValue(val, 0, self.mRepeat)
						elif opt =="always" and val:
							self.mAlways = retValue(val, 0, self.mAlways)
						elif opt =="startpoint" and val:
							self.mStartPoint = int(val)
				else:
					attribs.append((attrib,value))
			self.skinAttributes = attribs
		ret = Renderer.applySkin(self, desktop, screen)
		#if self.type == RUNNING and self.direction in (LEFT,RIGHT):
		#	self.halign = eLabel.alignLeft
		#	self.txtflags = RT_HALIGN_LEFT | (self.txtflags & RT_WRAP)
		if self.mOneShot: self.mOneShot = max(self.mStepTimeout, self.mOneShot)
		if self.mLoopTimeout: self.mLoopTimeout = max(self.mStepTimeout, self.mLoopTimeout)
		
		self.test_label.setFont(self.txfont)
		#self.test_label.setForegroundColor(self.fcolor)
		#self.test_label.setBackgroundColor(self.bcolor)
		#if not self.scolor is None:
		#	self.test_label.setShadowColor(self.scolor)
		#	self.test_label.setShadowOffset(ePoint(self.soffset[0], self.soffset[1]))
		if not (self.txtflags & RT_WRAP):
			self.test_label.setNoWrap(1)
		self.test_label.setVAlign(valign)
		self.test_label.setHAlign(self.halign)
		self.test_label.move( ePoint(self.W,self.H) )
		self.test_label.resize( eSize(self.W,self.H) )
		#self.test_label.hide()
		#self.changed((self.CHANGED_DEFAULT,))
		return ret

	def doSuspend(self, suspended):
		if suspended:
			self.changed((self.CHANGED_CLEAR,))
		else:
			self.changed((self.CHANGED_DEFAULT,))

	def connect(self, source):
		Renderer.connect(self, source)
		#self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		if not self.mTimer is None: self.mTimer.stop()
		if what[0] == self.CHANGED_CLEAR:
			self.txtext = ""
			if self.instance:
				#self.instance.fillRect( eRect(0, 0, self.W, self.H), self.bcolor )
				self.instance.clear(self.bcolor)
		else:
			self.txtext = self.source.text or ""
			if self.instance:
				if not self.calcMoving():
					self.drawText(self.X, self.Y)

	def drawText(self, X, Y):
		#self.instance.fillRect( eRect(0, 0, self.W, self.H), self.bcolor )
		self.instance.clear(self.bcolor)
		
		#if not self.scolor is None:
		#	self.instance.writeText( eRect(X-self.soffset[0], Y-self.soffset[1], self.W-self.soffset[0], self.H-self.soffset[1]), self.scolor, self.bcolor, self.txfont, self.txtext, self.txtflags )
		#self.instance.writeText( eRect(X, Y, self.W, self.H), self.fcolor, self.bcolor, self.txfont, self.txtext, self.txtflags )
		if not self.scolor is None:
			fcolor = self.scolor
		else:
			fcolor = self.fcolor
		self.instance.writeText( eRect(X-self.soffset[0], Y-self.soffset[1], self.W, self.H), fcolor, self.bcolor, self.txfont, self.txtext, self.txtflags )
		if not self.scolor is None:
			self.instance.writeText( eRect(X, Y, self.W, self.H), self.fcolor, self.scolor, self.txfont, self.txtext, self.txtflags )

	def calcMoving(self):
		if self.txtext == "": return False
		if self.type == NONE: return False
		if self.test_label is None: return False
		self.test_label.setText(self.txtext)
		text_size = self.test_label.calculateSize()
		text_width = text_size.width()
		text_height = text_size.height()

#		self.type =		0 - NONE; 1 - RUNNING; 2 - SWIMMING; 3 - AUTO(???)
#		self.direction =	0 - LEFT; 1 - RIGHT;   2 - TOP;      3 - BOTTOM
#		self.halign =		0 - LEFT; 1 - RIGHT;   2 -CENTER;    3 - BLOCK

		if self.direction in (LEFT,RIGHT):
			if self.type == RUNNING:		# scroll_type == RUNNING
				if not self.mAlways and text_width <= self.W:
					return False
				
				self.A = self.X - text_width - self.soffset[0] - abs(self.mStep)
				self.B = self.W - self.soffset[0] + abs(self.mStep)
				if self.direction == LEFT:		# direction == LEFT:
					self.mStep = -abs(self.mStep)
					self.mStop = self.X
					self.P = self.B
				else:					# direction == RIGHT (arabic):
					self.mStep = abs(self.mStep)
					self.mStop = self.B - text_width + self.soffset[0] - self.mStep
					self.P = self.A
				
				if not self.mStartPoint is None:
					if self.direction == LEFT:
						#self.P = min(self.B, max(self.A, self.mStartPoint))
						self.mStop = self.P = max(self.A, min(self.W, self.mStartPoint))
					else:
						self.mStop = self.P = max(self.A, min(self.B, self.mStartPoint - text_width + self.soffset[0]))
			
			elif self.type == SWIMMING:	# scroll_type == SWIMMING
				if not self.mAlways and text_width <= self.W: return False
				if text_width < self.W:
					if self.halign == LEFT:
						self.A = self.X + 1
						self.B = self.W - text_width - 1
						self.P = self.A
						self.mStep = abs(self.mStep)
					elif self.halign == RIGHT:
						self.A = self.X + 1
						self.B = self.W - text_width - 1
						self.P = self.B
						self.mStep = -abs(self.mStep)
					else: # self.halign == CENTER or self.halign == BLOCK:
						self.A = self.X + 1
						self.B = self.W - text_width - 1
						self.P = int(self.B / 2)
						self.mStep = (self.direction == RIGHT) and abs(self.mStep) or -abs(self.mStep)
				elif text_width > self.W:
					if self.halign == LEFT:
						self.A = self.W - text_width
						self.B = self.X
						self.P = self.B
						self.mStep = -abs(self.mStep)
					elif self.halign == RIGHT:
						self.A = self.W - text_width
						self.B = self.X
						self.P = self.A
						self.mStep = abs(self.mStep)
					else: # self.halign == CENTER or self.halign == BLOCK:
						self.A = self.W - text_width
						self.B = self.X
						self.P = int(self.A / 2)
						self.mStep = (self.direction == RIGHT) and abs(self.mStep) or -abs(self.mStep)
				else:	# if text_width == self.W
					return False
			else:					# scroll_type == NONE
				return False
		elif self.direction in (TOP,BOTTOM):
			if self.type == RUNNING:		# scroll_type == RUNNING
				if not self.mAlways and text_height <= self.H:
					return False
				
				self.A = self.Y - text_height - self.soffset[1] - abs(self.mStep) - 9
				self.B = self.H - self.soffset[1] + abs(self.mStep)
				if self.direction == TOP:		# direction == TOP:
					self.mStep = -abs(self.mStep)
					self.mStop = self.Y
					self.P = self.B
				else:					# direction == BOTTOM (arabic):
					self.mStep = abs(self.mStep)
					self.mStop = self.B - text_height + self.soffset[1] - self.mStep - 9
					self.P = self.A
				
				if not self.mStartPoint is None:
					if self.direction == TOP:
						self.mStop = self.P = max(self.A, min(self.H, self.mStartPoint))
					else:
						self.mStop = self.P = max(self.A, min(self.B, self.mStartPoint - text_height + self.soffset[1] - 9))
			
			elif self.type == SWIMMING:	# scroll_type == SWIMMING
				if not self.mAlways and text_height <= self.H: return False
				if text_height < self.H:
					if self.direction == TOP:	# direction == TOP
						self.A = self.Y
						self.B = self.H - text_height
						self.P = self.B
						self.mStep = -abs(self.mStep)
					else:				# direction == BOTTOM (arabic)
						self.A = self.Y
						self.B = self.H - text_height
						self.P = self.A
						self.mStep = abs(self.mStep)
				elif text_height > self.H:
					if self.direction == TOP:	# direction == TOP
						self.A = self.H - text_height - 8	# " - 8" added by vlamo (25.12.2010 17:59)
						self.B = self.Y
						self.P = self.B
						self.mStep = -abs(self.mStep)
					else:				# direction == BOTTOM (arabic)
						self.A = self.H - text_height - 8	# " - 8" added by vlamo (25.12.2010 17:59)
						self.B = self.Y
						self.P = self.A
						self.mStep = abs(self.mStep)
				else:	# if text_height == self.H
					return False
			else:					# scroll_type == NONE
				return False
		else:
			return False

		if self.mStartDelay:
			if self.direction in (LEFT,RIGHT):
				self.drawText(self.P, self.Y)
			else: # if self.direction in (TOP,BOTTOM)
				self.drawText(self.X, self.P)
		self.mCount = self.mRepeat
		self.mTimer.start(self.mStartDelay,True)
		return True

	def movingLoop(self):
		if self.A <= self.P <= self.B:
			if self.direction in (LEFT,RIGHT):
				self.drawText(self.P, self.Y)
			else: # if self.direction in (TOP,BOTTOM)
				self.drawText(self.X, self.P)
			if (self.type == RUNNING) and (self.mOneShot > 0) and (self.mStop+abs(self.mStep) > self.P >= self.mStop):
				if (self.mRepeat > 0) and (self.mCount-1 == 0): return
				timeout = self.mOneShot
			else:
				timeout = self.mStepTimeout
		else:
			if self.mRepeat > 0:
				self.mCount -= 1
				if self.mCount == 0: 
					self.drawText(0, 0)
					return
				elif (self.mCount > 0) and (self.type == RUNNING):
					self.drawText(0, 0)
					timeout = self.mLoopTimeout
					self.P = 1
					self.mTimer.start(self.mStartDelay,True)
					return
			timeout = self.mLoopTimeout
			if self.type == RUNNING:
				if self.P < self.A:
					self.P = self.B + abs(self.mStep)
				else:
					self.P = self.A - abs(self.mStep)
			else:
				self.mStep = -self.mStep
		
		self.P += self.mStep
		self.mTimer.start(timeout,True)


