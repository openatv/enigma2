from enigma import eLabel, eListbox, ePoint, eSize, eSlider, eWidget

from skin import applyAllAttributes, parseBoolean, parseGradient, parseInteger, parseRadius, parseScrollbarMode, parseScrollbarScroll, scrollLabelStyle
from Components.GUIComponent import GUIComponent


class ScrollLabel(GUIComponent):
	def __init__(self, text=""):
		GUIComponent.__init__(self)
		self.msgText = text
		self.instance = None
		self.leftText = None
		self.rightText = None
		self.slider = None
		self.split = False
		self.splitCharacter = "|"
		self.splitTrim = False
		self.lineWrap = True
		self.lineHeight = 0
		self.pageWidth = 0
		self.pageHeight = 0
		self.totalTextHeight = 0
		self.currentPosition = 0
		self.leftColX = 0
		self.rightColX = 0

	def GUIcreate(self, parent):
		self.instance = eWidget(parent)
		self.leftText = eLabel(self.instance)
		self.rightText = eLabel(self.instance)
		self.slider = eSlider(self.instance)
		self.slider.setIsScrollbar()

	def GUIdelete(self):
		self.leftText = None
		self.rightText = None
		self.slider = None
		self.instance = None

	def applySkin(self, desktop, parent):
		splitMargin = 0
		splitPosition = 0
		splitSeparated = False
		sliderBorderWidth = scrollLabelStyle.get("scrollbarBorderWidth", eListbox.DefaultScrollBarBorderWidth)
		sliderMode = scrollLabelStyle.get("scrollbarMode", eListbox.showOnDemand)
		sliderScroll = scrollLabelStyle.get("scrollbarScroll", eListbox.DefaultScrollBarScroll)
		sliderOffset = scrollLabelStyle.get("scrollbarOffset", eListbox.DefaultScrollBarOffset)
		sliderWidth = scrollLabelStyle.get("scrollbarWidth", eListbox.DefaultScrollBarWidth)
		scrollbarRadius = scrollLabelStyle.get("scrollbarRadius", None)
		scrollbarGradient = None
		lineWrap = True
		if self.skinAttributes:
			sliderProperties = (
				"scrollbarBorderColor",
				"scrollbarBorderWidth",
				"scrollbarBackgroundColor",
				"scrollbarForegroundColor",
				"scrollbarBackgroundPixmap",
				"scrollbarForegroundPixmap"
			)
			widgetAttributes = []
			leftLabelAttributes = [("transparent", "1")]
			rightLabelAttributes = [("transparent", "1")]
			sliderAttributes = [("transparent", "1")]
			leftAlign = "left"
			rightAlign = "left"
			for attribute, value in self.skinAttributes:
				if attribute in sliderProperties:
					sliderAttributes.append((attribute, value))
				else:
					if attribute == "backgroundColor":
						widgetAttributes.append((attribute, value))
						if "scrollbarBackgroundColor" not in [x[0] for x in sliderAttributes]:
							sliderAttributes.append(("scrollbarBackgroundColor", value))
						continue
					if attribute == "transparent":
						widgetAttributes.append((attribute, value))
						continue
					if attribute in ("leftColumnAlignment", "leftColAlign"):
						leftAlign = value
					elif attribute in ("rightColumnAlignment", "rightColAlign"):
						rightAlign = value
						self.split = True
					elif attribute == "split":
						self.split = parseBoolean("split", value)
					elif attribute in ("splitCharacter", "divideChar", "dividechar"):
						self.splitCharacter = value
						self.split = True
					elif attribute == "splitMargin":
						splitMargin = parseInteger(value)
					elif attribute in ("splitPosition", "colPosition", "colposition"):
						splitPosition = parseInteger(value)
						self.split = True
					elif attribute == "splitSeparated":
						splitSeparated = parseBoolean("splitSeparated", value)
						self.split = True
					elif attribute == "splitTrim":
						self.splitTrim = parseBoolean("splitTrim", value)
					elif attribute == "scrollbarBorderWidth":
						sliderBorderWidth = parseInteger(value, eListbox.DefaultScrollBarBorderWidth)
					elif attribute == "scrollbarMode":
						sliderMode = parseScrollbarMode(value)
					elif attribute == "scrollbarScroll":
						sliderScroll = parseScrollbarScroll(value)
					elif attribute == "scrollbarOffset":
						sliderOffset = parseInteger(value, eListbox.DefaultScrollBarOffset)
					elif attribute == "scrollbarWidth":
						sliderWidth = parseInteger(value, eListbox.DefaultScrollBarWidth)
					elif attribute == "scrollbarRadius":
						scrollbarRadius = parseRadius(value)
					elif attribute == "scrollbarGradient":
						scrollbarGradient = parseGradient(value)
					else:
						leftLabelAttributes.append((attribute, value))
						rightLabelAttributes.append((attribute, value))
						if attribute == "noWrap" and value in ("1", "enable", "enabled", "on", "true", "yes"):
							lineWrap = False
						if attribute == "wrap" and value not in ("1", "enable", "enabled", "on", "true", "yes"):
							lineWrap = False
			if self.split:
				if not splitSeparated:
					leftAlign = "left"  # If columns are used and not separated then left column needs to be "left" aligned to avoid overlapping text.
				leftLabelAttributes.append(("horizontalAlignment", leftAlign))
				rightLabelAttributes.append(("horizontalAlignment", rightAlign))
			applyAllAttributes(self.instance, desktop, widgetAttributes, parent.scale)
			applyAllAttributes(self.leftText, desktop, leftLabelAttributes, parent.scale)
			applyAllAttributes(self.rightText, desktop, rightLabelAttributes, parent.scale)
			applyAllAttributes(self.slider, desktop, sliderAttributes, parent.scale)
			retVal = True
		else:
			retVal = False
		self.lineWrap = lineWrap
		self.lineHeight = eLabel.calculateTextSize(self.leftText.getFont(), "Abcdefgh", eSize(10000, 10000), True).height()
		self.pageWidth = self.leftText.size().width()
		self.pageHeight = (self.leftText.size().height() // self.lineHeight) * self.lineHeight
		self.instance.move(self.leftText.position())
		self.instance.resize(eSize(self.pageWidth, self.pageHeight))
		self.sliderWidth = sliderOffset + sliderWidth
		if self.split and sliderMode != eListbox.showNever:  # Check that there is space for the scrollbar in the split.
			if abs(splitPosition) < self.sliderWidth:
				splitPosition = None
			elif abs(self.pageWidth - splitPosition) < self.sliderWidth:
				splitPosition = None
		splitPosition = self.pageWidth // 2 if splitPosition is None else splitPosition
		self.leftWidth = (splitPosition - splitMargin) if splitSeparated else self.pageWidth
		self.rightColX = splitPosition + splitMargin
		self.rightWidth = self.pageWidth - splitPosition - splitMargin
		self.splitSeparated = splitSeparated
		self.leftText.move(ePoint(0, 0))
		self.rightText.move(ePoint(self.rightColX, 0))
		self.slider.move(ePoint(0 if sliderMode in (eListbox.showLeftOnDemand, eListbox.showLeftAlways) else (self.pageWidth - sliderWidth), 0))
		self.slider.resize(eSize(sliderWidth, self.pageHeight))
		self.slider.setOrientation(eSlider.orVertical)
		self.slider.setRange(0, 1000)
		self.slider.setBorderWidth(sliderBorderWidth)
		if scrollbarRadius:
			self.slider.setCornerRadius(*scrollbarRadius)
		if scrollbarGradient:
			scrollbarGradient = scrollbarGradient + (True,)  # Add fullColor.
			self.slider.setForegroundGradient(*scrollbarGradient)
		self.sliderMode = sliderMode
		self.sliderScroll = self.lineHeight if sliderScroll else self.pageHeight
		self.setText(self.msgText)
		return retVal

	def getForegroundColor(self):
		return self.leftText.getForegroundColor().argb()

	def getText(self):
		return self.msgText

	def setText(self, text, showBottom=False):
		def buildText(text, leftWidth, rightWidth):
			if self.split:  # Two column mode.
				leftText = []
				rightText = []
				font = self.leftText.getFont()
				for line in text.split("\n"):
					line = line.split(self.splitCharacter, 1)
					if len(line) > 1:
						line[1] = line[1].lstrip() if self.splitTrim else line[1]
					else:
						line.append("")
					if self.lineWrap:  # We are going to be wrapping long lines so we need to synchronize the columns.
						leftHeight = eLabel.calculateTextSize(font, line[0], eSize(leftWidth, 10000), False).height() if line[0] else self.lineHeight
						rightHeight = eLabel.calculateTextSize(font, line[1], eSize(rightWidth, 10000), False).height() if line[1] else self.lineHeight
						blankLines = "\n" * (max(leftHeight // self.lineHeight, rightHeight // self.lineHeight) - 1)
						if blankLines and leftHeight > rightHeight:
							leftText.append(line[0])
							rightText.append(f"{line[1]}{blankLines}")
						elif blankLines and leftHeight < rightHeight:
							leftText.append(f"{line[0]}{blankLines}")
							rightText.append(line[1])
						else:
							leftText.append(line[0])
							rightText.append(line[1])
					else:
						leftText.append(line[0])
						rightText.append(line[1])
				leftText = "\n".join(leftText)
				rightText = "\n".join(rightText)
			else:  # One column mode.
				leftText = text
				rightText = ""
			return leftText, rightText

		self.msgText = text
		if self.pageHeight:  # This stops the text being processed if applySkin has not yet been run.
			text = text.rstrip() if self.splitTrim else text
			leftWidth = self.leftWidth
			rightWidth = self.rightWidth
			leftText, rightText = buildText(text, leftWidth, rightWidth)
			font = self.leftText.getFont()
			self.totalTextHeight = eLabel.calculateTextSize(font, leftText, eSize(leftWidth, 10000), not self.lineWrap).height()
			if self.isSliderVisible():
				leftWidth -= self.sliderWidth
				rightWidth -= self.sliderWidth
				leftText, rightText = buildText(text, leftWidth, rightWidth)
				self.totalTextHeight = eLabel.calculateTextSize(font, leftText, eSize(leftWidth, 10000), not self.lineWrap).height()
				if self.sliderMode in (eListbox.showLeftAlways, eListbox.showLeftOnDemand):
					self.leftColX = self.sliderWidth
				else:
					self.leftColX = 0
					leftWidth = self.leftWidth if self.splitSeparated else self.leftWidth - self.sliderWidth
				self.slider.show()
			else:
				self.leftColX = 0
				self.slider.hide()
			self.leftText.resize(eSize(leftWidth, self.totalTextHeight))
			self.rightText.resize(eSize(rightWidth, self.totalTextHeight))
			self.leftText.setText(leftText)
			self.rightText.setText(rightText)
			self.setPos(self.totalTextHeight - self.pageHeight if showBottom else 0)

	text = property(getText, setText)

	def appendText(self, text, showBottom=True):
		self.setText(f"{self.msgText}{text}", showBottom)

	def isSliderVisible(self):
		return self.sliderMode in (eListbox.showAlways, eListbox.showLeftAlways) or (self.sliderMode in (eListbox.showOnDemand, eListbox.showLeftOnDemand) and self.totalTextHeight > self.pageHeight)

	def isNavigationNeeded(self):
		return self.totalTextHeight > self.pageHeight

	def isAtLastPage(self):
		return self.totalTextHeight <= self.pageHeight or self.currentPosition == self.totalTextHeight - self.pageHeight

	def setPos(self, pos):
		self.currentPosition = max(0, min(pos, self.totalTextHeight - self.pageHeight))
		if self.isSliderVisible():
			visible = min(max(1000 * self.pageHeight // self.totalTextHeight, 4), 1000)
			start = (1000 - visible) * self.currentPosition // ((self.totalTextHeight - self.pageHeight) or 1)
			self.slider.setStartEnd(start, start + visible)
		self.leftText.move(ePoint(self.leftColX, -self.currentPosition))
		self.rightText.move(ePoint(self.rightColX, -self.currentPosition))

	def goTop(self):
		if self.totalTextHeight > self.pageHeight:
			self.setPos(0)

	def goPageUp(self):
		if self.totalTextHeight > self.pageHeight:
			self.setPos(self.currentPosition - self.pageHeight)

	def goLineUp(self):
		if self.totalTextHeight > self.pageHeight:
			self.setPos(self.currentPosition - self.sliderScroll)

	def goLineDown(self):
		if self.totalTextHeight > self.pageHeight:
			self.setPos(self.currentPosition + self.sliderScroll)

	def goPageDown(self):
		if self.totalTextHeight > self.pageHeight:
			self.setPos(self.currentPosition + self.pageHeight)

	def goBottom(self):
		if self.totalTextHeight > self.pageHeight:
			self.setPos(self.totalTextHeight - self.pageHeight)

	# Old navigation method names.
	#
	def moveTop(self):
		self.goTop()

	def homePage(self):  # Deprecated navigation (no use found).
		return self.goTop()

	def pageUp(self):
		self.goPageUp()

	def moveUp(self):
		self.goLineUp()

	def moveDown(self):
		self.goLineDown()

	def pageDown(self):
		self.goPageDown()

	def moveBottom(self):
		self.goBottom()

	def endPage(self):  # Deprecated navigation (no use found).
		return self.goBottom()

	def lastPage(self):  # Deprecated navigation (only minimal use).
		return self.goBottom()
