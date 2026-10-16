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
# several changes made by Dr.Best <dr.best@dreambox-tools.info> (07-18-2013)
# - I got rid of eCanvas, instead I took a widget as a parent and scroll the label directly into the widget (this saves performance (about 30%))
# - new property: mShown --> this fixes the bug that this renderer keeps running in background when its not shown
# - this renderer can be used in OLED display with dmm oe2.0 images
# - due to changing to eWidget in combination with eLabel transparent flag is possible (still cpu killer!)
# - fixed left / right scrolling , fixed nowrap-mode
# take a look at the discussion: http://board.dreambox-tools.info/showthread.php?6050-Erweiterung-Running-Text-render
################################################################################

from enigma import RT_HALIGN_BLOCK, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_BOTTOM, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, eLabel, ePoint, eSize, eTimer, eWidget, fontRenderClass, gFont

from skin import parseColor, parseFont
from Components.Renderer.Renderer import Renderer


class ScrollType:
	NONE = 0
	RUNNING = 1
	SWIMMING = 2
	AUTO = 3


class Direction:
	LEFT = 0
	RIGHT = 1
	TOP = 2
	BOTTOM = 3


class HAlign:
	# Known bug: self.halign holds eLabel values (alignCenter = 1, alignRight = 2), so RIGHT and CENTER are swapped in calcMoving.
	LEFT = 0
	RIGHT = 1
	CENTER = 2
	BLOCK = 3


# Old globals, kept for compatibility.
NONE = ScrollType.NONE
RUNNING = ScrollType.RUNNING
SWIMMING = ScrollType.SWIMMING
AUTO = ScrollType.AUTO
LEFT = Direction.LEFT
RIGHT = Direction.RIGHT
TOP = Direction.TOP
BOTTOM = Direction.BOTTOM
CENTER = HAlign.CENTER
BLOCK = HAlign.BLOCK


class RunningTextBase(Renderer):  # Shared code of RunningText and VRunningText.
	def __init__(self):
		Renderer.__init__(self)
		self.type = ScrollType.NONE
		self.direction = Direction.LEFT
		self.halign = eLabel.alignLeft
		self.txfont = gFont("Regular", 14)
		self.soffset = (0, 0)
		self.txtflags = 0
		self.txtext = ""
		self.textLabel = self.mTimer = self.mStartPoint = None
		self.X = self.Y = self.W = self.H = self.mStartDelay = 0
		self.mAlways = 1  # Always move the text.
		self.mStep = 1  # Pixels per step.
		self.mStepTimeout = 50  # Milliseconds per step.
		self.mLoopTimeout = self.mOneShot = self.mRepeat = 0
		self.mPageDelay = self.mPageLength = 0

	def applySkin(self, desktop, screen):
		valign = eLabel.alignTop
		if self.skinAttributes:
			attribs = []
			for (attrib, value) in self.skinAttributes:
				match attrib:
					case "font":
						self.txfont = parseFont(value, screen.scale)
					case "halign" if value in ("left", "center", "right", "block"):
						self.halign = {"left": eLabel.alignLeft, "center": eLabel.alignCenter, "right": eLabel.alignRight, "block": eLabel.alignBlock}[value]
						self.txtflags |= {"left": RT_HALIGN_LEFT, "center": RT_HALIGN_CENTER, "right": RT_HALIGN_RIGHT, "block": RT_HALIGN_BLOCK}[value]
					case "noWrap":
						self.setWrapFlag(attrib, value)
					case "options":
						self.parseOptions(value)
					case "valign" if value in ("top", "center", "bottom"):
						valign = {"top": eLabel.alignTop, "center": eLabel.alignCenter, "bottom": eLabel.alignBottom}[value]
						self.txtflags |= {"top": RT_VALIGN_TOP, "center": RT_VALIGN_CENTER, "bottom": RT_VALIGN_BOTTOM}[value]
					case _:
						if not self.applySkinAttribute(attrib, value):
							attribs.append((attrib, value))
			self.skinAttributes = attribs
		result = Renderer.applySkin(self, desktop, screen)
		if self.mOneShot:
			self.mOneShot = max(self.mStepTimeout, self.mOneShot)
		if self.mLoopTimeout:
			self.mLoopTimeout = max(self.mStepTimeout, self.mLoopTimeout)
		if self.mPageDelay:
			self.mPageDelay = max(self.mStepTimeout, self.mPageDelay)
		self.textLabel.setFont(self.txfont)
		if not (self.txtflags & RT_WRAP):
			self.textLabel.setWrap(0)
		self.textLabel.setVAlign(valign)
		self.textLabel.setHAlign(self.halign)
		return result

	def postWidgetCreate(self, instance):
		for (attrib, value) in self.skinAttributes:
			if attrib == "size":
				x, y = value.split(",")
				self.W, self.H = int(x), int(y)
		self.textLabel = eLabel(instance)
		self.mTimer = eTimer()
		self.mTimer.callback.append(self.movingLoop)

	def preWidgetRemove(self, instance):
		self.mTimer.stop()
		self.mTimer.callback.remove(self.movingLoop)
		self.mTimer = None
		self.textLabel = None

	def doSuspend(self, suspended):
		self.changed((self.CHANGED_CLEAR if suspended else self.CHANGED_DEFAULT,))

	def applySkinAttribute(self, attrib, value):  # Return True if the attribute is handled and must not be passed to the widget.
		return False

	def parseOptions(self, value):
		def retValue(val, limit, default):
			try:
				result = max(limit, int(val))
			except ValueError:
				result = default
			return result

		for option in value.split(","):
			opt, val = (x.strip() for x in option.split("=", 1)) if "=" in option else (option.strip(), "")
			match opt:
				case "always" if val:
					self.mAlways = retValue(val, 0, self.mAlways)
				case "direction" if val in ("left", "right", "top", "bottom"):
					self.direction = {"left": Direction.LEFT, "right": Direction.RIGHT, "top": Direction.TOP, "bottom": Direction.BOTTOM}[val]
				case "movetype" if val in ("none", "running", "swimming"):
					self.type = {"none": ScrollType.NONE, "running": ScrollType.RUNNING, "swimming": ScrollType.SWIMMING}[val]
				case "nowrap" | "wrap":
					self.setWrapFlag(opt, val)
				case "oneshot" if val:
					self.mOneShot = retValue(val, 0, self.mOneShot)
				case "pagedelay" if val:
					self.mPageDelay = retValue(val, 0, self.mPageDelay)
				case "pagelength" if val:
					self.mPageLength = retValue(val, 0, self.mPageLength)
				case "pause" if val:
					self.mLoopTimeout = retValue(val, 0, self.mLoopTimeout)
				case "repeat" if val:
					self.mRepeat = retValue(val, 0, self.mRepeat)
				case "startdelay" if val:
					self.mStartDelay = retValue(val, 0, self.mStartDelay)
				case "startpoint" if val:
					self.mStartPoint = int(val)
				case "step" if val:
					self.mStep = retValue(val, 1, self.mStep)
				case "steptime" if val:
					self.mStepTimeout = retValue(val, 25, self.mStepTimeout)

	def setWrapFlag(self, attrib, value):
		if (attrib.lower() == "wrap" and value == "0") or (attrib.lower() == "nowrap" and value != "0"):
			self.txtflags &= ~RT_WRAP
		else:
			self.txtflags |= RT_WRAP

	def moveToPosition(self):
		if self.direction in (Direction.LEFT, Direction.RIGHT):
			self.moveText(self.P, self.Y)
		else:  # Direction.TOP or Direction.BOTTOM
			self.moveText(self.X, self.P)


class RunningText(RunningTextBase):
	GUI_WIDGET = eWidget

	def __init__(self):
		RunningTextBase.__init__(self)
		self.lineHeight = 0  # For text height auto correction on dmm-enigma2.
		self.mShown = 0

	def applySkin(self, desktop, screen):
		result = RunningTextBase.applySkin(self, desktop, screen)
		self.textLabel.move(ePoint(0, 0))
		self.textLabel.resize(eSize(self.W, self.H))
		if self.direction in (Direction.TOP, Direction.BOTTOM):  # Auto correction of the text height.
			flh = int(fontRenderClass.getInstance().getLineHeight(self.txfont) or self.txfont.pointSize / 6 + self.txfont.pointSize)
			self.textLabel.setText("WQq")
			if flh > self.textLabel.calculateSize().height():
				self.lineHeight = flh
			self.textLabel.setText("")
		return result

	def postWidgetCreate(self, instance):
		RunningTextBase.postWidgetCreate(self, instance)
		instance.move(ePoint(0, 0))
		instance.resize(eSize(self.W, self.H))

	def changed(self, what):
		if self.mTimer is not None:
			self.mTimer.stop()
		if what[0] == self.CHANGED_CLEAR:
			self.txtext = ""
			if self.instance:
				self.textLabel.setText("")
		else:
			if self.mShown:
				self.txtext = self.source.text or ""
				if self.instance and not self.calcMoving():
					self.textLabel.resize(eSize(self.W, self.H))
					self.moveText(self.X, self.Y)

	def doSuspend(self, suspended):
		self.mShown = 1 - suspended
		RunningTextBase.doSuspend(self, suspended)

	def applySkinAttribute(self, attrib, value):
		handled = True
		match attrib:
			case "backgroundColor":
				self.textLabel.setBackgroundColor(parseColor(value))
				handled = False  # The widget needs it too.
			case "borderColor" | "shadowColor":  # Fake for openpli-enigma2.
				self.textLabel.setShadowColor(parseColor(value))
			case "borderWidth":  # Fake for openpli-enigma2.
				self.soffset = (-int(value), -int(value))
			case "foregroundColor":
				self.textLabel.setForegroundColor(parseColor(value))
			case "shadowOffset":
				x, y = value.split(",")
				self.soffset = (int(x), int(y))
				self.textLabel.setShadowOffset(ePoint(self.soffset))
			case "transparent":
				self.textLabel.setTransparent(int(value))
				handled = False  # The widget needs it too.
			case _:
				handled = False
		return handled

	def moveText(self, X, Y):
		self.textLabel.move(ePoint(X - self.soffset[0], Y - self.soffset[1]))

	def calcMoving(self):
		self.X = self.Y = 0
		if not (self.txtflags & RT_WRAP):
			self.txtext = self.txtext.replace("\xe0\x8a", " ").replace(chr(0x8A), " ").replace("\n", " ").replace("\r", " ")

		self.textLabel.setText(self.txtext)

		if self.txtext == "" or \
			self.type == ScrollType.NONE or \
			self.textLabel is None:
			return False

		if self.direction in (Direction.LEFT, Direction.RIGHT) or not (self.txtflags & RT_WRAP):
			self.textLabel.resize(eSize(self.txfont.pointSize * len(self.txtext), self.H))  # stupid workaround, have no better idea right now...

		text_size = self.textLabel.calculateSize()
		text_width = text_size.width()
		text_height = text_size.height()

		if self.direction in (Direction.LEFT, Direction.RIGHT) or not (self.txtflags & RT_WRAP):
			text_width += 10

		self.mStop = None
		# text height correction if necessary:
		if self.lineHeight and self.direction in (Direction.TOP, Direction.BOTTOM):
			text_height = max(text_height, (text_height + self.lineHeight - 1) / self.lineHeight * self.lineHeight)

		match self.direction:
			case Direction.LEFT | Direction.RIGHT:
				if not self.mAlways and text_width <= self.W:
					return False
				match self.type:
					case ScrollType.RUNNING:
						self.A = self.X - text_width - self.soffset[0] - abs(self.mStep)
						self.B = self.W - self.soffset[0] + abs(self.mStep)
						if self.direction == Direction.LEFT:
							self.mStep = -abs(self.mStep)
							self.mStop = self.X
							self.P = self.B
						else:
							self.mStep = abs(self.mStep)
							self.mStop = self.B - text_width + self.soffset[0] - self.mStep
							self.P = self.A
						if self.mStartPoint is not None:
							if self.direction == Direction.LEFT:
								self.mStop = self.P = max(self.A, min(self.W, self.mStartPoint))
							else:
								self.mStop = self.P = max(self.A, min(self.B, self.mStartPoint - text_width + self.soffset[0]))
					case ScrollType.SWIMMING:
						if text_width < self.W:
							self.A = self.X + 1			# incomprehensible indent "+ 1" ???
							self.B = self.W - text_width - 1  # incomprehensible indent "- 1" ???
							match self.halign:
								case HAlign.LEFT:
									self.P = self.A
									self.mStep = abs(self.mStep)
								case HAlign.RIGHT:
									self.P = self.B
									self.mStep = -abs(self.mStep)
								case _:  # HAlign.CENTER or HAlign.BLOCK
									self.P = int(self.B / 2)
									self.mStep = (self.direction == Direction.RIGHT) and abs(self.mStep) or -abs(self.mStep)
						else:
							if text_width == self.W:
								text_width += max(2, text_width / 20)
							self.A = self.W - text_width
							self.B = self.X
							match self.halign:
								case HAlign.LEFT:
									self.P = self.B
									self.mStep = -abs(self.mStep)
								case HAlign.RIGHT:
									self.P = self.A
									self.mStep = abs(self.mStep)
								case _:  # HAlign.CENTER or HAlign.BLOCK
									self.P = int(self.A / 2)
									self.mStep = (self.direction == Direction.RIGHT) and abs(self.mStep) or -abs(self.mStep)
					case _:
						return False
			case Direction.TOP | Direction.BOTTOM:
				if not self.mAlways and text_height <= self.H:
					return False
				match self.type:
					case ScrollType.RUNNING:
						self.A = self.Y - text_height - self.soffset[1] - abs(self.mStep)
						self.B = self.H - self.soffset[1] + abs(self.mStep)
						if self.direction == Direction.TOP:
							self.mStep = -abs(self.mStep)
							self.mStop = self.Y
							self.P = self.B
						else:
							self.mStep = abs(self.mStep)
							self.mStop = self.B - text_height + self.soffset[1] - self.mStep
							self.P = self.A
						if self.mStartPoint is not None:
							if self.direction == Direction.TOP:
								self.mStop = self.P = max(self.A, min(self.H, self.mStartPoint))
							else:
								self.mStop = self.P = max(self.A, min(self.B, self.mStartPoint - text_height + self.soffset[1]))
					case ScrollType.SWIMMING:
						if text_height < self.H:
							self.A = self.Y
							self.B = self.H - text_height
							if self.direction == Direction.TOP:
								self.P = self.B
								self.mStep = -abs(self.mStep)
							else:
								self.P = self.A
								self.mStep = abs(self.mStep)
						else:
							if text_height == self.H:
								text_height += max(2, text_height / 40)
							self.A = self.H - text_height
							self.B = self.Y
							if self.direction == Direction.TOP:
								self.P = self.B
								self.mStep = -abs(self.mStep)
								self.mStop = self.B
							else:
								self.P = self.A
								self.mStep = abs(self.mStep)
								self.mStop = self.A
					case _:
						return False
			case _:
				return False

		self.xW = max(self.W, text_width)
		self.xH = max(self.H, text_height)

		self.textLabel.resize(eSize(self.xW, self.xH))

		if self.mStartDelay:
			self.moveToPosition()

		self.mCount = self.mRepeat
		self.mTimer.start(self.mStartDelay, True)
		return True

	def movingLoop(self):
		if self.A <= self.P <= self.B:
			self.moveToPosition()
			timeout = self.mStepTimeout
			if (self.mStop is not None) and (self.mStop + abs(self.mStep) > self.P >= self.mStop):
				match self.type:
					case ScrollType.RUNNING if self.mOneShot > 0:
						if (self.mRepeat > 0) and (self.mCount - 1 <= 0):
							return
						timeout = self.mOneShot
					case ScrollType.SWIMMING if self.mPageLength > 0 and self.mPageDelay > 0:
						match self.direction:
							case Direction.TOP if self.mStep < 0:
								self.mStop -= self.mPageLength
								if self.mStop < self.A:
									self.mStop = self.B
								timeout = self.mPageDelay
							case Direction.BOTTOM if self.mStep > 0:
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
			if self.type == ScrollType.RUNNING:
				if self.P < self.A:
					self.P = self.B + abs(self.mStep)
				else:
					self.P = self.A - abs(self.mStep)
			else:
				self.mStep = -self.mStep

		self.P += self.mStep
		self.mTimer.start(timeout, True)
