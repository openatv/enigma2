#
# Running Text Renderer for Enigma2 (RunningText.py)
# Coded by vlamo (c) 2010
#
# Version: 1.4 (02.04.2011 17:15)
# Support: http://dream.altmaster.net/
#

from enigma import eCanvas, ePoint, eRect, eSize, gRGB

from skin import parseColor
from Components.Renderer.RunningText import Direction, HAlign, RunningTextBase, ScrollType

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


def RGB(r, g, b):
	return (r << 16) | (g << 8) | b


class VRunningText(RunningTextBase):
	GUI_WIDGET = eCanvas

	def __init__(self):
		RunningTextBase.__init__(self)
		self.fcolor = gRGB(RGB(255, 255, 255))
		self.bcolor = gRGB(RGB(0, 0, 0))
		self.scolor = None
		self.mStepTimeout = 5000

	def applySkin(self, desktop, screen):
		result = RunningTextBase.applySkin(self, desktop, screen)
		self.textLabel.move(ePoint(self.W, self.H))
		self.textLabel.resize(eSize(self.W, self.H))
		return result

	def postWidgetCreate(self, instance):
		RunningTextBase.postWidgetCreate(self, instance)
		instance.setSize(eSize(self.W, self.H))

	def changed(self, what):
		if self.mTimer is not None:
			self.mTimer.stop()
		if what[0] == self.CHANGED_CLEAR:
			self.txtext = ""
			if self.instance:
				#self.instance.fillRect( eRect(0, 0, self.W, self.H), self.bcolor )
				self.instance.clear(self.bcolor)
		else:
			self.txtext = self.source.text or ""
			if self.instance and not self.calcMoving():
				self.moveText(self.X, self.Y)

	def applySkinAttribute(self, attrib, value):
		handled = True
		match attrib:
			case "backgroundColor":
				self.bcolor = parseColor(value)
			case "foregroundColor":
				self.fcolor = parseColor(value)
			case "shadowColor":
				self.scolor = parseColor(value)
			case "shadowOffset":
				x, y = value.split(",")
				self.soffset = (int(x), int(y))
			case _:
				handled = False
		return handled

	def moveText(self, X, Y):
		#self.instance.fillRect( eRect(0, 0, self.W, self.H), self.bcolor )
		self.instance.clear(self.bcolor)

		#if not self.scolor is None:
		#	self.instance.writeText( eRect(X-self.soffset[0], Y-self.soffset[1], self.W-self.soffset[0], self.H-self.soffset[1]), self.scolor, self.bcolor, self.txfont, self.txtext, self.txtflags )
		#self.instance.writeText( eRect(X, Y, self.W, self.H), self.fcolor, self.bcolor, self.txfont, self.txtext, self.txtflags )
		fcolor = self.scolor if self.scolor is not None else self.fcolor
		self.instance.writeText(eRect(X - self.soffset[0], Y - self.soffset[1], self.W, self.H), fcolor, self.bcolor, self.txfont, self.txtext, self.txtflags)
		if self.scolor is not None:
			self.instance.writeText(eRect(X, Y, self.W, self.H), self.fcolor, self.scolor, self.txfont, self.txtext, self.txtflags)

	def calcMoving(self):
		if self.txtext == "" or self.type == ScrollType.NONE or self.textLabel is None:
			return False
		self.textLabel.setText(self.txtext)
		text_size = self.textLabel.calculateSize()
		text_width = text_size.width()
		text_height = text_size.height()

		match self.direction:
			case Direction.LEFT | Direction.RIGHT:
				match self.type:
					case ScrollType.RUNNING:
						if not self.mAlways and text_width <= self.W:
							return False

						self.A = self.X - text_width - self.soffset[0] - abs(self.mStep)
						self.B = self.W - self.soffset[0] + abs(self.mStep)
						if self.direction == Direction.LEFT:		# direction == LEFT:
							self.mStep = -abs(self.mStep)
							self.mStop = self.X
							self.P = self.B
						else:					# direction == RIGHT (arabic):
							self.mStep = abs(self.mStep)
							self.mStop = self.B - text_width + self.soffset[0] - self.mStep
							self.P = self.A

						if self.mStartPoint is not None:
							if self.direction == Direction.LEFT:
								#self.P = min(self.B, max(self.A, self.mStartPoint))
								self.mStop = self.P = max(self.A, min(self.W, self.mStartPoint))
							else:
								self.mStop = self.P = max(self.A, min(self.B, self.mStartPoint - text_width + self.soffset[0]))

					case ScrollType.SWIMMING:
						if not self.mAlways and text_width <= self.W:
							return False
						if text_width < self.W:
							match self.halign:
								case HAlign.LEFT:
									self.A = self.X + 1
									self.B = self.W - text_width - 1
									self.P = self.A
									self.mStep = abs(self.mStep)
								case HAlign.RIGHT:
									self.A = self.X + 1
									self.B = self.W - text_width - 1
									self.P = self.B
									self.mStep = -abs(self.mStep)
								case _:  # HAlign.CENTER or HAlign.BLOCK
									self.A = self.X + 1
									self.B = self.W - text_width - 1
									self.P = int(self.B / 2)
									self.mStep = (self.direction == Direction.RIGHT) and abs(self.mStep) or -abs(self.mStep)
						elif text_width > self.W:
							match self.halign:
								case HAlign.LEFT:
									self.A = self.W - text_width
									self.B = self.X
									self.P = self.B
									self.mStep = -abs(self.mStep)
								case HAlign.RIGHT:
									self.A = self.W - text_width
									self.B = self.X
									self.P = self.A
									self.mStep = abs(self.mStep)
								case _:  # HAlign.CENTER or HAlign.BLOCK
									self.A = self.W - text_width
									self.B = self.X
									self.P = int(self.A / 2)
									self.mStep = (self.direction == Direction.RIGHT) and abs(self.mStep) or -abs(self.mStep)
						else:  # if text_width == self.W
							return False
					case _:  # ScrollType.NONE
						return False
			case Direction.TOP | Direction.BOTTOM:
				match self.type:
					case ScrollType.RUNNING:
						if not self.mAlways and text_height <= self.H:
							return False

						self.A = self.Y - text_height - self.soffset[1] - abs(self.mStep) - 9
						self.B = self.H - self.soffset[1] + abs(self.mStep)
						if self.direction == Direction.TOP:		# direction == TOP:
							self.mStep = -abs(self.mStep)
							self.mStop = self.Y
							self.P = self.B
						else:					# direction == BOTTOM (arabic):
							self.mStep = abs(self.mStep)
							self.mStop = self.B - text_height + self.soffset[1] - self.mStep - 9
							self.P = self.A

						if self.mStartPoint is not None:
							if self.direction == Direction.TOP:
								self.mStop = self.P = max(self.A, min(self.H, self.mStartPoint))
							else:
								self.mStop = self.P = max(self.A, min(self.B, self.mStartPoint - text_height + self.soffset[1] - 9))

					case ScrollType.SWIMMING:
						if not self.mAlways and text_height <= self.H:
							return False
						if text_height < self.H:
							if self.direction == Direction.TOP:  # direction == TOP
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
							if self.direction == Direction.TOP:  # direction == TOP
								self.A = self.H - text_height - 8  # " - 8" added by vlamo (25.12.2010 17:59)
								self.B = self.Y
								self.P = self.B
								self.mStep = -abs(self.mStep)
							else:				# direction == BOTTOM (arabic)
								self.A = self.H - text_height - 8  # " - 8" added by vlamo (25.12.2010 17:59)
								self.B = self.Y
								self.P = self.A
								self.mStep = abs(self.mStep)
						else:  # if text_height == self.H
							return False
					case _:  # ScrollType.NONE
						return False
			case _:
				return False

		if self.mStartDelay:
			self.moveToPosition()
		self.mCount = self.mRepeat
		self.mTimer.start(self.mStartDelay, True)
		return True

	def movingLoop(self):
		if self.A <= self.P <= self.B:
			self.moveToPosition()
			if (self.type == ScrollType.RUNNING) and (self.mOneShot > 0) and (self.mStop + abs(self.mStep) > self.P >= self.mStop):
				if (self.mRepeat > 0) and (self.mCount - 1 == 0):
					return
				timeout = self.mOneShot
			else:
				timeout = self.mStepTimeout
		else:
			if self.mRepeat > 0:
				self.mCount -= 1
				if self.mCount == 0:
					self.moveText(0, 0)
					return
				elif (self.mCount > 0) and (self.type == ScrollType.RUNNING):
					self.moveText(0, 0)
					timeout = self.mLoopTimeout
					self.P = 1
					self.mTimer.start(self.mStartDelay, True)
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
