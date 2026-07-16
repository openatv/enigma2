################################################################################
#    VRunningText.py - Running Text Renderer for Enigma2
#    Version: 1.4 (02.04.2011 17:15)
#    Coded by vlamo (c) 2010
#    Support: http://dream.altmaster.net/
################################################################################

from enigma import RT_HALIGN_BLOCK, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_BOTTOM, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, eCanvas, eLabel, ePoint, eRect, eSize, eTimer, gFont, gRGB

from skin import parseColor, parseFont
from Components.Renderer.Renderer import Renderer


def RGB(r, g, b):
	return (r << 16) | (g << 8) | b


class VRunningText(Renderer):
	GUI_WIDGET = eCanvas

	# Scroll type:
	NONE = 0
	RUNNING = 1
	SWIMMING = 2
	AUTO = 3  # Not used
	# Direction:
	LEFT = 0
	RIGHT = 1
	TOP = 2
	BOTTOM = 3
	# Horizontal alignment:
	# LEFT = 0
	# RIGHT = 1
	CENTER = 2  # Not used
	BLOCK = 3  # Not used

	def __init__(self):
		Renderer.__init__(self)
		self.runningType = self.NONE
		self.textFont = gFont("Regular", 14)
		self.foregroundColor = gRGB(RGB(255, 255, 255))
		self.backgroundColor = gRGB(RGB(0, 0, 0))
		self.shadowColor = None
		self.soffset = (0, 0)
		self.textFlags = 0  # RT_WRAP
		self.textText = ""
		self.scrollText = None
		self.mTimer = None
		self.mStartPoint = None
		self.X = 0
		self.Y = 0
		self.W = 0
		self.H = 0
		self.mStartDelay = 0
		self.mAlways = 1  # Always move text.
		self.mStep = 1  # Moving step: 1 pixel per 1 time.
		self.mStepTimeout = 5000  # Step timeout: 1 step per 50 milliseconds (speed: 20 pixel per second).
		self.direction = self.LEFT
		self.mLoopTimeout = 0
		self.mOneShot = 0
		self.mRepeat = 0

	def postWidgetCreate(self, instance):
		for (attribute, value) in self.skinAttributes:
			if attribute == "size":
				xPos, yPos = value.split(",")
				self.W, self.H = int(xPos), int(yPos)
		self.instance.setSize(eSize(self.W, self.H))
		self.scrollText = eLabel(instance)
		self.mTimer = eTimer()
		self.mTimer.callback.append(self.movingLoop)

	def preWidgetRemove(self, instance):
		self.mTimer.stop()
		self.mTimer.callback.remove(self.movingLoop)
		self.mTimer = None
		self.scrollText = None

	def movingLoop(self):
		if self.A <= self.P <= self.B:
			if self.direction in (self.LEFT, self.RIGHT):
				self.drawText(self.P, self.Y)
			else:  # if self.direction in (self.TOP, self.BOTTOM):
				self.drawText(self.X, self.P)
			if (self.runningType == self.RUNNING) and (self.mOneShot > 0) and (self.mStop + abs(self.mStep) > self.P >= self.mStop):
				if (self.mRepeat > 0) and (self.mCount - 1 == 0):
					return
				timeout = self.mOneShot
			else:
				timeout = self.mStepTimeout
		else:
			if self.mRepeat > 0:
				self.mCount -= 1
				if self.mCount == 0:
					self.drawText(0, 0)
					return
				elif (self.mCount > 0) and (self.runningType == self.RUNNING):
					self.drawText(0, 0)
					timeout = self.mLoopTimeout
					self.P = 1
					self.mTimer.start(self.mStartDelay, True)
					return
			timeout = self.mLoopTimeout
			if self.runningType == self.RUNNING:
				self.P = self.B + abs(self.mStep) if self.P < self.A else self.A - abs(self.mStep)
			else:
				self.mStep = -self.mStep
		self.P += self.mStep
		self.mTimer.start(timeout, True)
	def drawText(self, xPos, yPos):
		# self.instance.fillRect(eRect(0, 0, self.W, self.H), self.backgroundColor)
		self.instance.clear(self.backgroundColor)
		# if self.shadowColor is not None:
		# 	self.instance.writeText(eRect(xPos - self.soffset[0], yPos - self.soffset[1], self.W - self.soffset[0], self.H - self.soffset[1]), self.shadowColor, self.backgroundColor, self.textFont, self.textText, self.textFlags)
		# self.instance.writeText(eRect(xPos, yPos, self.W, self.H), self.foregroundColor, self.backgroundColor, self.textFont, self.textText, self.textFlags)
		drawColor = self.shadowColor if self.shadowColor is not None else self.foregroundColor
		self.instance.writeText(eRect(xPos - self.soffset[0], yPos - self.soffset[1], self.W, self.H), drawColor, self.backgroundColor, self.textFont, self.textText, self.textFlags)
		if self.shadowColor is not None:
			self.instance.writeText(eRect(xPos, yPos, self.W, self.H), self.foregroundColor, self.shadowColor, self.textFont, self.textText, self.textFlags)

	def applySkin(self, desktop, screen):
		def retValue(setting, limit, default, minimum=False):
			try:
				value = min(limit, int(setting)) if minimum else max(limit, int(setting))
			except Exception:
				value = default
			return value

		def setWrapFlag(attribute, value):
			if (attribute.lower() == "wrap" and value == "0") or (attribute.lower() == "nowrap" and value != "0"):
				self.textFlags &= ~RT_WRAP
			else:
				self.textFlags |= RT_WRAP

		self.horizontalAlignment = eLabel.alignLeft
		verticalAlignment = eLabel.alignLeft
		if self.skinAttributes:
			attributes = []
			for (attribute, value) in self.skinAttributes:
				match attribute:
					case "backgroundColor":
						self.backgroundColor = parseColor(value)
					case "font":
						self.textFont = parseFont(value, screen.scale)
					case "foregroundColor":
						self.foregroundColor = parseColor(value)
					case "halign":
						if value in ("left", "center", "right", "block"):
							self.horizontalAlignment = {
								"left": eLabel.alignLeft,
								"center": eLabel.alignCenter,
								"right": eLabel.alignRight,
								"block": eLabel.alignBlock
							}[value]
							self.textFlags |= {
								"left": RT_HALIGN_LEFT,
								"center": RT_HALIGN_CENTER,
								"right": RT_HALIGN_RIGHT,
								"block": RT_HALIGN_BLOCK
							}[value]
					case "noWrap":
						setWrapFlag(attribute, value)
					case "options":
						for item in value.split(","):
							option, setting = (x.strip() for x in item.split("=", 1)) if "=" in item else (item.strip(), "")
							if option:
								if option in ("nowrap", "wrap"):
									setWrapFlag(option, setting)
								elif setting:
									match option:
										case "always":
											self.mAlways = retValue(setting, 0, self.mAlways)
										case "direction" if setting in ("left", "right", "top", "bottom"):
											self.direction = {
												"left": self.LEFT,
												"right": self.RIGHT,
												"top": self.TOP,
												"bottom": self.BOTTOM
											}[setting]
										case "movetype" if setting in ("none", "running", "swimming"):
											self.runningType = {
												"none": self.NONE,
												"running": self.RUNNING,
												"swimming": self.SWIMMING
											}[setting]
										case "oneshot":
											self.mOneShot = retValue(setting, 0, self.mOneShot)
										case "pause":
											self.mLoopTimeout = retValue(setting, 0, self.mLoopTimeout)
										case "repeat":
											self.mRepeat = retValue(setting, 0, self.mRepeat)
										case "startdelay":
											self.mStartDelay = retValue(setting, 0, self.mStartDelay)
										case "startpoint":
											self.mStartPoint = int(setting)
										case "step":
											# retValue(setting, limit, default, minimum=False)
											self.mStep = retValue(setting, 1, self.mStep)
										case "steptime":
											self.mStepTimeout = retValue(setting, 25, self.mStepTimeout)
					case "shadowColor":
						self.shadowColor = parseColor(value)
					case "shadowOffset":
						xPos, yPos = value.split(",")
						self.soffset = (int(xPos), int(yPos))
					case "valign":
						if value in ("top", "center", "bottom"):
							verticalAlignment = {
								"top": eLabel.alignTop,
								"center": eLabel.alignCenter,
								"bottom": eLabel.alignBottom
							}[value]
							self.textFlags |= {
								"top": RT_VALIGN_TOP,
								"center": RT_VALIGN_CENTER,
								"bottom": RT_VALIGN_BOTTOM
							}[value]
					case _:
						attributes.append((attribute, value))
			self.skinAttributes = attributes
		result = Renderer.applySkin(self, desktop, screen)
		# if self.runningType == self.RUNNING and self.direction in (self.LEFT, self.RIGHT):
		# 	self.horizontalAlignment = eLabel.alignLeft
		# 	self.textFlags = RT_HALIGN_LEFT | (self.textFlags & RT_WRAP)
		if self.mOneShot:
			self.mOneShot = max(self.mStepTimeout, self.mOneShot)
		if self.mLoopTimeout:
			self.mLoopTimeout = max(self.mStepTimeout, self.mLoopTimeout)
		self.scrollText.setFont(self.textFont)
		# self.scrollText.setForegroundColor(self.foregroundColor)
		# self.scrollText.setBackgroundColor(self.backgroundColor)
		# if self.shadowColor is not None:
		# 	self.scrollText.setShadowColor(self.shadowColor)
		# 	self.scrollText.setShadowOffset(ePoint(self.soffset[0], self.soffset[1]))
		if not (self.textFlags & RT_WRAP):
			self.scrollText.setWrap(0)
		self.scrollText.setVAlign(verticalAlignment)
		self.scrollText.setHAlign(self.horizontalAlignment)
		self.scrollText.move(ePoint(self.W, self.H))
		self.scrollText.resize(eSize(self.W, self.H))
		# self.scrollText.hide()
		# self.changed((self.CHANGED_DEFAULT,))
		return result

	def doSuspend(self, suspended):
		self.changed((self.CHANGED_CLEAR,) if suspended else (self.CHANGED_DEFAULT,))

	def connect(self, source):
		Renderer.connect(self, source)
		# self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		if self.mTimer is not None:
			self.mTimer.stop()
		if what[0] == self.CHANGED_CLEAR:
			self.textText = ""
			if self.instance:
				# self.instance.fillRect(eRect(0, 0, self.W, self.H), self.backgroundColor)
				self.instance.clear(self.backgroundColor)
		else:
			self.textText = self.source.text or ""
			if self.instance and not self.calcMoving():
				self.drawText(self.X, self.Y)

	def calcMoving(self):
		if self.textText == "" or self.runningType == self.NONE or self.scrollText is None:
			return False
		self.scrollText.setText(self.textText)
		textSize = self.scrollText.calculateSize()
		textWidth = textSize.width()
		textHeight = textSize.height()
		# self.runningType =         0 - NONE; 1 - RUNNING; 2 - SWIMMING; 3 - AUTO(???)
		# self.direction =           0 - LEFT; 1 - RIGHT;   2 - TOP;      3 - BOTTOM
		# self.horizontalAlignment = 0 - LEFT; 1 - RIGHT;   2 - CENTER;   3 - BLOCK
		match self.direction:
			case self.LEFT | self.RIGHT:
				if not self.mAlways and textWidth <= self.W:
					return False
				match self.runningType:
					case self.RUNNING:
						self.A = self.X - textWidth - self.soffset[0] - abs(self.mStep)
						self.B = self.W - self.soffset[0] + abs(self.mStep)
						if self.direction == self.LEFT:
							self.mStep = -abs(self.mStep)
							self.mStop = self.X
							self.P = self.B
						else:
							self.mStep = abs(self.mStep)
							self.mStop = self.B - textWidth + self.soffset[0] - self.mStep
							self.P = self.A
						if self.mStartPoint is not None:
							if self.direction == self.LEFT:
								# self.P = min(self.B, max(self.A, self.mStartPoint))
								self.mStop = self.P = max(self.A, min(self.W, self.mStartPoint))
							else:
								self.mStop = self.P = max(self.A, min(self.B, self.mStartPoint - textWidth + self.soffset[0]))
					case self.SWIMMING:
						if textWidth < self.W:
							self.A = self.X + 1
							self.B = self.W - textWidth - 1
							match self.horizontalAlignment:
								case self.LEFT:
									self.P = self.A
									self.mStep = abs(self.mStep)
								case self.RIGHT:
									self.P = self.B
									self.mStep = -abs(self.mStep)
								case _:  # self.CENTER | self.BLOCK:
									self.P = int(self.B / 2)
									self.mStep = (self.direction == self.RIGHT) and abs(self.mStep) or -abs(self.mStep)
						elif textWidth > self.W:
							self.A = self.W - textWidth
							self.B = self.X
							match self.horizontalAlignment:
								case self.LEFT:
									self.P = self.B
									self.mStep = -abs(self.mStep)
								case self.RIGHT:
									self.P = self.A
									self.mStep = abs(self.mStep)
								case _:  # self.CENTER | self.BLOCK:
									self.P = int(self.A / 2)
									self.mStep = (self.direction == self.RIGHT) and abs(self.mStep) or -abs(self.mStep)
						else:  # if textWidth == self.W
							return False
					case _:  # runningType == NONE
						return False
			case self.TOP | self.BOTTOM:
				if not self.mAlways and textHeight <= self.H:
					return False
				if self.runningType == self.RUNNING:
					self.A = self.Y - textHeight - self.soffset[1] - abs(self.mStep) - 9
					self.B = self.H - self.soffset[1] + abs(self.mStep)
					if self.direction == self.TOP:
						self.mStep = -abs(self.mStep)
						self.mStop = self.Y
						self.P = self.B
					else:
						self.mStep = abs(self.mStep)
						self.mStop = self.B - textHeight + self.soffset[1] - self.mStep - 9
						self.P = self.A
					if self.mStartPoint is not None:
						if self.direction == self.TOP:
							self.mStop = self.P = max(self.A, min(self.H, self.mStartPoint))
						else:
							self.mStop = self.P = max(self.A, min(self.B, self.mStartPoint - textHeight + self.soffset[1] - 9))
				elif self.runningType == self.SWIMMING:
					if textHeight < self.H:
						if self.direction == self.TOP:
							self.A = self.Y
							self.B = self.H - textHeight
							self.P = self.B
							self.mStep = -abs(self.mStep)
						else:
							self.A = self.Y
							self.B = self.H - textHeight
							self.P = self.A
							self.mStep = abs(self.mStep)
					elif textHeight > self.H:
						if self.direction == self.TOP:
							self.A = self.H - textHeight - 8  # " - 8" added by vlamo (25.12.2010 17:59)
							self.B = self.Y
							self.P = self.B
							self.mStep = -abs(self.mStep)
						else:
							self.A = self.H - textHeight - 8  # " - 8" added by vlamo (25.12.2010 17:59)
							self.B = self.Y
							self.P = self.A
							self.mStep = abs(self.mStep)
					else:  # if textHeight == self.H
						return False
				else:
					return False
			case _:
				return False
		if self.mStartDelay:
			if self.direction in (self.LEFT, self.RIGHT):
				self.drawText(self.P, self.Y)
			else:  # if self.direction in (self.TOP, self.BOTTOM):
				self.drawText(self.X, self.P)
		self.mCount = self.mRepeat
		self.mTimer.start(self.mStartDelay, True)
		return True

