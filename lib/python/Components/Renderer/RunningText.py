################################################################################
#    RunningText.py - Running Text Renderer for Enigma2
#    Version: 1.5 (04.04.2012 23:40)
#    Copyright (C) 2010-2012 vlamo <vlamodev@gmail.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
################################################################################

################################################################################
# Several changes made by Dr.Best <dr.best@dreambox-tools.info> (07-18-2013)
# - I got rid of eCanvas, instead I took a widget as a parent and scroll the label directly into the widget (this saves performance (about 30%)).
# - New property: mShown --> this fixes the bug that this renderer keeps running in background when its not shown.
# - This renderer can be used in OLED display with dmm oe2.0 images.
# - Due to changing to eWidget in combination with eLabel transparent flag is possible (still cpu killer!).
# - Fixed left / right scrolling , fixed nowrap-mode.
# Take a look at the discussion: http://board.dreambox-tools.info/showthread.php?6050-Erweiterung-Running-Text-render.
################################################################################

from enigma import RT_HALIGN_BLOCK, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_BOTTOM, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, eLabel, ePoint, eSize, eTimer, eWidget, gFont

from skin import parseBoolean, parseColor, parseFont
from Components.Renderer.Renderer import Renderer


class RunningText(Renderer):
	GUI_WIDGET = eWidget

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
		self.textFlags = 0  # RT_WRAP
		self.textText = ""
		self.soffset = (0, 0)
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
		self.mStepTimeout = 50  # Step timeout: 1 step per 50 milliseconds (speed: 20 pixel per second).
		self.direction = self.LEFT
		self.mLoopTimeout = 0
		self.mOneShot = 0
		self.mRepeat = 0
		self.mPageDelay = 0
		self.mPageLength = 0
		self.mShown = 0
		self.lineHeight = 0  # For text height auto correction on dmm-enigma2.

	def postWidgetCreate(self, instance):
		for (attribute, value) in self.skinAttributes:
			if attribute == "size":
				xPos, yPos = value.split(",")
				self.W, self.H = int(xPos), int(yPos)
		self.instance.move(ePoint(0, 0))
		self.instance.resize(eSize(self.W, self.H))
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
				self.moveLabel(self.P, self.Y)
			else:  # if self.direction in (self.TOP, self.BOTTOM):
				self.moveLabel(self.X, self.P)
			timeout = self.mStepTimeout
			if (self.mStop is not None) and (self.mStop + abs(self.mStep) > self.P >= self.mStop):
				if (self.runningType == self.RUNNING) and (self.mOneShot > 0):
					if (self.mRepeat > 0) and (self.mCount - 1 <= 0):
						return
					timeout = self.mOneShot
				elif (self.runningType == self.SWIMMING) and (self.mPageLength > 0) and (self.mPageDelay > 0):
					if (self.direction == self.TOP) and (self.mStep < 0):
						self.mStop -= self.mPageLength
						if self.mStop < self.A:
							self.mStop = self.B
						timeout = self.mPageDelay
					elif (self.direction == self.BOTTOM) and (self.mStep > 0):
						self.mStop += self.mPageLength
						if self.mStop > self.B:
							self.mStop = self.A
						timeout = self.mPageDelay
		else:
			if self.mRepeat > 0:
				self.mCount -= 1
				if self.mCount == 0:
					return
			timeout = self.mLoopTimeout
			if self.runningType == self.RUNNING:
				self.P = self.B + abs(self.mStep) if self.P < self.A else self.A - abs(self.mStep)
			else:
				self.mStep = -self.mStep
		self.P += self.mStep
		self.mTimer.start(timeout, True)

	def moveLabel(self, xPos, yPos):
		self.scrollText.move(ePoint(xPos - self.soffset[0], yPos - self.soffset[1]))

	def applySkin(self, desktop, screen):
		def retValue(setting, limit, default, minimum=False):  # minimum is not used
			try:
				value = min(limit, int(setting)) if minimum else max(limit, int(setting))
			except Exception:
				value = default
			return value

		def setWrapFlag(attribute, value):
			if (attribute.lower() == "wrap" and not parseBoolean("wrap", value)) or (attribute.lower() == "nowrap" and parseBoolean("nowrap", value)):
				self.textFlags &= ~RT_WRAP
			else:
				self.textFlags |= RT_WRAP

		self.horizontalAlignment = eLabel.alignLeft
		verticalAlignment = eLabel.alignTop
		if self.skinAttributes:
			attributes = []
			for (attribute, value) in self.skinAttributes:
				match attribute:
					case "borderColor" | "shadowColor":  # Fake for openpli-enigma2.
						self.scrollText.setShadowColor(parseColor(value))
					case "borderWidth":  # Fake for openpli-enigma2.
						self.soffset = (-int(value), -int(value))
					case "font":
						self.textFont = parseFont(value, screen.scale)
					case "foregroundColor":
						self.scrollText.setForegroundColor(parseColor(value))
					case "halign" | "horizontalAlignment":
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
									setWrapFlag(option, setting or "1")
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
										case "pagedelay":
											self.mPageDelay = retValue(setting, 0, self.mPageDelay)
										case "pagelength":
											self.mPageLength = retValue(setting, 0, self.mPageLength)
										case "pause":
											self.mLoopTimeout = retValue(setting, 0, self.mLoopTimeout)
										case "repeat":
											self.mRepeat = retValue(setting, 0, self.mRepeat)
										case "startdelay":
											self.mStartDelay = retValue(setting, 0, self.mStartDelay)
										case "startpoint":
											self.mStartPoint = int(setting)
										case "step":
											self.mStep = retValue(setting, 1, self.mStep)
										case "steptime":
											self.mStepTimeout = retValue(setting, 25, self.mStepTimeout)
					case "shadowOffset":
						xPos, yPos = value.split(",")
						self.soffset = (int(xPos), int(yPos))
						self.scrollText.setShadowOffset(ePoint(self.soffset))
					case "valign" | "verticalAlignment":
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
					case "wrap":
						setWrapFlag(attribute, value)
					case _:
						attributes.append((attribute, value))
						match attribute:
							case "backgroundColor":
								self.scrollText.setBackgroundColor(parseColor(value))
							case "transparent":
								self.scrollText.setTransparent(int(value))
			self.skinAttributes = attributes
		result = Renderer.applySkin(self, desktop, screen)
		if self.mOneShot:
			self.mOneShot = max(self.mStepTimeout, self.mOneShot)
		if self.mLoopTimeout:
			self.mLoopTimeout = max(self.mStepTimeout, self.mLoopTimeout)
		if self.mPageDelay:
			self.mPageDelay = max(self.mStepTimeout, self.mPageDelay)
		self.scrollText.setFont(self.textFont)
		if not (self.textFlags & RT_WRAP):
			self.scrollText.setWrap(0)
		self.scrollText.setVAlign(verticalAlignment)
		self.scrollText.setHAlign(self.horizontalAlignment)
		self.scrollText.move(ePoint(0, 0))
		self.scrollText.resize(eSize(self.W, self.H))
		if self.direction in (self.TOP, self.BOTTOM):  # Test for auto correction text height.
			from enigma import fontRenderClass
			fontLineHeight = int(fontRenderClass.getInstance().getLineHeight(self.textFont) or self.textFont.pointSize / 6 + self.textFont.pointSize)
			self.scrollText.setText("WQq")
			if fontLineHeight > self.scrollText.calculateSize().height():
				self.lineHeight = fontLineHeight
			self.scrollText.setText("")
		return result

	def doSuspend(self, suspended):
		self.mShown = 1 - suspended
		self.changed((self.CHANGED_CLEAR,) if suspended else (self.CHANGED_DEFAULT,))

	def connect(self, source):
		Renderer.connect(self, source)

	def changed(self, what):
		if self.mTimer is not None:
			self.mTimer.stop()
		if what[0] == self.CHANGED_CLEAR:
			self.textText = ""
			if self.instance:
				self.scrollText.setText("")
		else:
			if self.mShown:
				self.textText = self.source.text or ""
				if self.instance and not self.calcMoving():
					self.scrollText.resize(eSize(self.W, self.H))
					self.moveLabel(self.X, self.Y)

	def calcMoving(self):
		self.X = 0
		self.Y = 0
		if not (self.textFlags & RT_WRAP):
			self.textText = self.textText.replace("\xe0\x8a", " ").replace(chr(0x8A), " ").replace("\n", " ").replace("\r", " ")
		self.scrollText.setText(self.textText)
		if self.textText == "" or self.runningType == self.NONE or self.scrollText is None:
			return False
		if self.direction in (self.LEFT, self.RIGHT) or not (self.textFlags & RT_WRAP):
			self.scrollText.resize(eSize(self.textFont.pointSize * len(self.textText), self.H))  # Stupid workaround, have no better idea right now.
		textSize = self.scrollText.calculateSize()
		textWidth = textSize.width()
		textHeight = textSize.height()
		if self.direction in (self.LEFT, self.RIGHT) or not (self.textFlags & RT_WRAP):
			textWidth += 10
		self.mStop = None
		if self.lineHeight and self.direction in (self.TOP, self.BOTTOM):  # Text height correction if necessary.
			textHeight = max(textHeight, (textHeight + self.lineHeight - 1) / self.lineHeight * self.lineHeight)
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
								self.mStop = self.P = max(self.A, min(self.W, self.mStartPoint))
							else:
								self.mStop = self.P = max(self.A, min(self.B, self.mStartPoint - textWidth + self.soffset[0]))
					case self.SWIMMING:
						if textWidth < self.W:
							self.A = self.X + 1  # Incomprehensible indent "+ 1"?
							self.B = self.W - textWidth - 1  # Incomprehensible indent "- 1"?
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
						else:
							if textWidth == self.W:
								textWidth += max(2, textWidth / 20)
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
					case _:
						return False
			case self.TOP | self.BOTTOM:
				if not self.mAlways and textHeight <= self.H:
					return False
				if self.runningType == self.RUNNING:
					self.A = self.Y - textHeight - self.soffset[1] - abs(self.mStep)
					self.B = self.H - self.soffset[1] + abs(self.mStep)
					if self.direction == self.TOP:
						self.mStep = -abs(self.mStep)
						self.mStop = self.Y
						self.P = self.B
					else:
						self.mStep = abs(self.mStep)
						self.mStop = self.B - textHeight + self.soffset[1] - self.mStep
						self.P = self.A
					if self.mStartPoint is not None:
						if self.direction == self.TOP:
							self.mStop = self.P = max(self.A, min(self.H, self.mStartPoint))
						else:
							self.mStop = self.P = max(self.A, min(self.B, self.mStartPoint - textHeight + self.soffset[1]))
				elif self.runningType == self.SWIMMING:
					if textHeight < self.H:
						self.A = self.Y
						self.B = self.H - textHeight
						if self.direction == self.TOP:
							self.P = self.B
							self.mStep = -abs(self.mStep)
						else:
							self.P = self.A
							self.mStep = abs(self.mStep)
					else:
						if textHeight == self.H:
							textHeight += max(2, textHeight / 40)
						self.A = self.H - textHeight
						self.B = self.Y
						if self.direction == self.TOP:
							self.P = self.B
							self.mStep = -abs(self.mStep)
							self.mStop = self.B
						else:
							self.P = self.A
							self.mStep = abs(self.mStep)
							self.mStop = self.A
				else:
					return False
			case _:
				return False
		self.xW = max(self.W, textWidth)
		self.xH = max(self.H, textHeight)
		self.scrollText.resize(eSize(self.xW, self.xH))
		if self.mStartDelay:
			if self.direction in (self.LEFT, self.RIGHT):
				self.moveLabel(self.P, self.Y)
			else:  # if self.direction in (self.TOP, self.BOTTOM):
				self.moveLabel(self.X, self.P)
		self.mCount = self.mRepeat
		self.mTimer.start(self.mStartDelay, True)
		return True
