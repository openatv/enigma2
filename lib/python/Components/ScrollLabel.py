from enigma import eLabel, eListbox, ePoint, eSize, eSlider, eWidget, fontRenderClass

from skin import applyAllAttributes, parseBoolean, parseHorizontalAlignment, parseScrollbarMode, parseScrollbarScroll, scrollLabelStyle
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
		scrollLabelDefaults = (
			("scrollbarBorderWidth", eListbox.DefaultScrollBarBorderWidth),
			("scrollbarMode", eListbox.showOnDemand),
			("scrollbarOffset", eListbox.DefaultScrollBarOffset),
			("scrollbarScroll", eListbox.DefaultScrollBarScroll),
			("scrollbarWidth", eListbox.DefaultScrollBarWidth)
		)
		for attribute, default in scrollLabelDefaults:
			if attribute not in scrollLabelStyle:
				scrollLabelStyle[attribute] = default
		splitMargin = 0
		splitPosition = None
		splitSeparated = False
		sliderBorderWidth = scrollLabelStyle["scrollbarBorderWidth"]
		sliderMode = scrollLabelStyle["scrollbarMode"]
		sliderScroll = scrollLabelStyle["scrollbarScroll"]
		sliderOffset = scrollLabelStyle["scrollbarOffset"]
		sliderWidth = scrollLabelStyle["scrollbarWidth"]
		if self.skinAttributes:
			sliderProperties = (
				"scrollbarBorderColor",
				"scrollbarBorderWidth",
				"scrollbarBackgroundColor",
				"scrollbarForegroundColor",
				"scrollbarBackgroundPixmap",
				"scrollbarForegroundPixmap"
			)
			leftLabelAttributes = []
			rightLabelAttributes = []
			sliderAttributes = []
			leftAlign = "left"
			rightAlign = "left"
			for attribute, value in self.skinAttributes:
				if attribute in sliderProperties:
					sliderAttributes.append((attribute, value))
				else:
					try:
						if attribute == "leftColumnAlignment":
							leftAlign = parseHorizontalAlignment(value)  # The parser is used to check if the value is valid, an exception is raised if it isn't!
						elif attribute == "rightColumnAlignment":
							rightAlign = parseHorizontalAlignment(value)  # The parser is used to check if the value is valid, an exception is raised if it isn't!
							self.split = True
						elif attribute == "split":
							self.split = parseBoolean("split", value)
						elif attribute in ("splitCharacter", "divideChar", "dividechar"):
							self.splitCharacter = value
							self.split = True
						elif attribute == "splitMargin":
							splitMargin = int(value)
						elif attribute in ("splitPosition", "colPosition", "colposition"):
							splitPosition = int(value)
							self.split = True
						elif attribute == "splitSeparated":
							splitSeparated = parseBoolean("splitSeparated", value)
							self.split = True
						elif attribute == "splitTrim":
							self.splitTrim = parseBoolean("splitTrim", value)
						elif attribute == "scrollbarBorderWidth":
							sliderBorderWidth = int(value)
						elif attribute == "scrollbarMode":
							sliderMode = parseScrollbarMode(value)
						elif attribute == "scrollbarScroll":
							sliderScroll = parseScrollbarScroll(value)
						elif attribute == "scrollbarOffset":
							sliderOffset = int(value)
						elif attribute == "scrollbarWidth":
							sliderWidth = int(value)
						else:
							leftLabelAttributes.append((attribute, value))
							rightLabelAttributes.append((attribute, value))
					except ValueError:
						print("[ScrollLabel] Error: The attribute '%s' integer value '%s' is invalid!" % (attribute, value))
			if self.split:
				for attribute, value in leftLabelAttributes[:]:
					if attribute == "noWrap":  # Remove "noWrap" attribute so it can be set later.
						leftLabelAttributes.remove((attribute, value))
						break
				for attribute, value in rightLabelAttributes[:]:
					if attribute == "noWrap":  # Remove "noWrap" attribute so it can be set later.
						rightLabelAttributes.remove((attribute, value))
						break
				if not splitSeparated:
					leftAlign = "left"  # If columns are used and not separated then left column needs to be "left" aligned to avoid overlapping text.
					rightLabelAttributes.append(("transparent", "1"))  # Also, the right column needs to be transparent to allow for left column text overflow.
				leftLabelAttributes.extend([("horizontalAlignment", leftAlign), ("noWrap", "1")])  # Set "noWrap" to keep lines synchronized.
				rightLabelAttributes.extend([("horizontalAlignment", rightAlign), ("noWrap", "1")])  # Set "noWrap" to keep lines synchronized.
			applyAllAttributes(self.leftText, desktop, leftLabelAttributes, parent.scale)
			applyAllAttributes(self.rightText, desktop, rightLabelAttributes, parent.scale)
			applyAllAttributes(self.slider, desktop, sliderAttributes, parent.scale)
			retVal = True
		else:
			retVal = False
		lineHeight = int(fontRenderClass.getInstance().getLineHeight(self.leftText.getFont()) or 25)  # Assume a random line height if nothing is visible.
		self.pageWidth = self.leftText.size().width()
		self.pageHeight = (self.leftText.size().height() // lineHeight) * lineHeight
		self.instance.move(self.leftText.position())
		self.instance.resize(eSize(self.pageWidth, self.pageHeight))
		self.sliderWidth = sliderOffset + sliderWidth
		if splitPosition and sliderMode != eListbox.showNever:  # Check that there is space for the scrollbar in the split.
			if abs(splitPosition) < self.sliderWidth:
				splitPosition = None
			elif abs(self.pageWidth - splitPosition) < self.sliderWidth:
				splitPosition = None
		splitPosition = self.pageWidth // 2 if splitPosition is None else splitPosition
		self.leftWidth = (splitPosition - splitMargin) if splitSeparated else self.pageWidth
		self.rightColX = splitPosition + splitMargin
		self.rightWidth = self.pageWidth - splitPosition - splitMargin
		self.leftText.move(ePoint(0, 0))
		self.rightText.move(ePoint(self.rightColX, 0))
		self.slider.move(ePoint(0 if sliderMode in (eListbox.showLeftOnDemand, eListbox.showLeftAlways) else (self.pageWidth - sliderWidth), 0))
		self.slider.resize(eSize(sliderWidth, self.pageHeight))
		self.slider.setOrientation(eSlider.orVertical)
		self.slider.setRange(0, 1000)
		self.slider.setBorderWidth(sliderBorderWidth)
		self.sliderMode = sliderMode
		self.sliderScroll = lineHeight if sliderScroll else self.pageHeight
		self.setText(self.msgText)
		return retVal

	def getText(self):
		return self.msgText

	def setText(self, text, showBottom=False):
		self.msgText = text
		text = text.rstrip()
		if self.pageHeight:
			if self.split:
				leftText = []
				rightText = []
				for line in text.split("\n"):
					line = line.split(self.splitCharacter, 1)
					leftText.append(line[0])
					rightText.append("" if len(line) < 2 else (line[1].lstrip() if self.splitTrim else line[1]))
				self.leftText.setText("\n".join(leftText))
				self.rightText.setText("\n".join(rightText))
			else:
				self.leftText.setText(text)
			self.totalTextHeight = self.leftText.calculateSize().height()
			leftWidth = self.leftWidth
			rightWidth = self.rightWidth
			if self.isSliderVisible():
				self.slider.show()
				if self.sliderMode in (eListbox.showLeftAlways, eListbox.showLeftAlways):
					self.leftColX = self.sliderWidth
					leftWidth = self.leftWidth - self.sliderWidth
				else:
					rightWidth = self.rightWidth - self.sliderWidth
			else:
				self.slider.hide()
			self.leftText.resize(eSize(leftWidth, self.totalTextHeight))
			self.rightText.resize(eSize(rightWidth, self.totalTextHeight))
			if showBottom:
				self.moveBottom()
			else:
				self.setPosition(0)

	text = property(getText, setText)

	def appendText(self, text, showBottom=True):
		self.setText("%s%s" % (self.msgText, text), showBottom)

	def isSliderVisible(self):
		return self.sliderMode in (eListbox.showAlways, eListbox.showLeftAlways) or (self.sliderMode in (eListbox.showOnDemand, eListbox.showLeftOnDemand) and self.totalTextHeight > self.pageHeight)

	def setPosition(self, pos):
		self.currentPosition = max(0, min(pos, self.totalTextHeight - self.pageHeight))
		if self.isSliderVisible():
			self.updateScrollbar()
		self.leftText.move(ePoint(self.leftColX, -self.currentPosition))
		self.rightText.move(ePoint(self.rightColX, -self.currentPosition))

	def moveTop(self):
		if self.totalTextHeight > self.pageHeight:
			self.setPosition(0)

	def homePage(self):  # Deprecated navigation (no use found).
		return self.moveTop()

	def pageUp(self):
		if self.totalTextHeight > self.pageHeight:
			self.setPosition(self.currentPosition - self.pageHeight)

	def moveUp(self):
		if self.totalTextHeight > self.pageHeight:
			self.setPosition(self.currentPosition - self.sliderScroll)

	def moveDown(self):
		if self.totalTextHeight > self.pageHeight:
			self.setPosition(self.currentPosition + self.sliderScroll)

	def pageDown(self):
		if self.totalTextHeight > self.pageHeight:
			self.setPosition(self.currentPosition + self.pageHeight)

	def moveBottom(self):
		if self.totalTextHeight > self.pageHeight:
			self.setPosition(self.totalTextHeight - self.pageHeight)

	def endPage(self):  # Deprecated navigation (no use found).
		return self.moveBottom()

	def lastPage(self):  # Deprecated navigation (only minimal use).
		return self.moveBottom()

	def updateScrollbar(self):
		visible = min(max(1000 * self.pageHeight // self.totalTextHeight, 4), 1000)
		start = (1000 - visible) * self.currentPosition // ((self.totalTextHeight - self.pageHeight) or 1)
		self.slider.setStartEnd(start, start + visible)

	def isAtLastPage(self):
		return self.totalTextHeight <= self.pageHeight or self.currentPosition == self.totalTextHeight - self.pageHeight
