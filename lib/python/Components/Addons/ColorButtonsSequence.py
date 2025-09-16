from Components.Addons.GUIAddon import GUIAddon

from enigma import eListbox, eListboxPythonMultiContent, BT_ALIGN_CENTER, RT_VALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_CENTER, RT_BLEND, BT_SCALE, eSize, getDesktop, gFont

from skin import parseScale, parseColor, parseFont, applySkinFactor

from Components.MultiContent import MultiContentEntryPixmapAlphaBlend, MultiContentEntryText
from Components.Label import Label

from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap


class ColorButtonsSequence(GUIAddon):
	def __init__(self):
		GUIAddon.__init__(self)
		self.foreColor = None
		self.font = gFont("Regular", 18)
		self.l = eListboxPythonMultiContent()  # noqa: E741
		self.l.setBuildFunc(self.buildEntry)
		self.l.setItemHeight(35)
		self.l.setItemWidth(35)
		self.spacingButtons = applySkinFactor(40)
		self.spacingPixmapText = applySkinFactor(10)
		self.layoutStyle = "fixed"
		self.colorIndicatorStyle = "pixmap"
		self.orientations = {"orHorizontal": eListbox.orHorizontal, "orVertical": eListbox.orVertical}
		self.orientation = eListbox.orHorizontal
		self.renderType = "ImageTextRight"  # Currently supported are ImageTextRight, ImageTextOver and ColorTextOver
		self.alignment = "left"
		self.cornerRadius = 0
		self.pixmaps = {}
		self.colors = {}
		self.textRenderer = Label("")

	def onContainerShown(self):
		for x, val in self.sources.items():
			if self.constructColorButtonSequence not in val.onChanged:
				val.onChanged.append(self.constructColorButtonSequence)
		self.textRenderer.GUIcreate(self.relatedScreen.instance)
		self.l.setItemHeight(self.instance.size().height())
		self.l.setItemWidth(self.instance.size().width())
		self.constructColorButtonSequence()

	GUI_WIDGET = eListbox

	def updateAddon(self, sequence):
		lList = []
		lList.append((sequence,))
		self.l.setList(lList)

	def buildEntry(self, sequence):
		res = [None]
		if len(sequence) == 0:
			return res
		width = self.instance.size().width()
		height = self.instance.size().height()
		xPos = width if self.alignment == "right" else 0
		yPos = 0
		minSectorWidth = width // 4

		pic = None
		pixdWidth = 0

		for x, val in sequence.items():
			textColor = self.foreColor
			buttonBgColor = self.foreColor

			if x in self.colors:
				if self.renderType == "ImageTextRight":
					textColor = parseColor(self.colors[x]).argb()
				else:
					buttonBgColor = parseColor(self.colors[x]).argb()

			if self.renderType != "ImageTextOver" and x in self.pixmaps:
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, self.pixmaps[x]))
				if pic:
					pixdSize = pic.size()
					pixdWidth = pixdSize.width()
					picXPos = (xPos - pixdWidth) if self.alignment == "right" else xPos
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos=(picXPos, yPos),
						size=(pixdWidth, height),
						png=pic,
						backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
					if self.alignment == "right":
						xPos -= pixdWidth + self.spacingPixmapText
					else:
						xPos += pixdWidth + self.spacingPixmapText
			if hasattr(val, "text"):
				buttonText = val.text
			else:
				buttonText = ""

			if buttonText:
				textWidth = self._calcTextWidth(buttonText, font=self.font, size=eSize(self.getDesktopWith() // 3, 0))
			else:
				textWidth = 0
			if self.layoutStyle != "fluid":
				if textWidth < (minSectorWidth - self.spacingButtons - (self.spacingPixmapText if pic else 0) - pixdWidth):
					textWidth = minSectorWidth - self.spacingButtons - (self.spacingPixmapText if pic else 0) - pixdWidth
			if buttonText:
				textFlags = RT_HALIGN_LEFT | RT_VALIGN_CENTER
				textPaddings = 0
				backColor = None
				if self.renderType in ["ColorTextOver", "ImageTextOver"]:
					textFlags = RT_HALIGN_CENTER | RT_VALIGN_CENTER
					textPaddings = self.spacingPixmapText
					backColor = buttonBgColor

				if self.renderType == "ImageTextOver":
					textFlags = textFlags | RT_BLEND
					if x in self.pixmaps:
						pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, self.pixmaps[x]))
						if pic:
							res.append(MultiContentEntryPixmapAlphaBlend(
								pos=(xPos, yPos),
								size=(textWidth + textPaddings * 2, height),
								png=pic,
								backcolor=0x000000, backcolor_sel=None, flags=BT_SCALE, cornerRadius=self.cornerRadius))
						res.append(MultiContentEntryText(
							pos=(xPos + textPaddings, yPos), size=(textWidth, height - 2),
							font=0, flags=textFlags,
							text=buttonText, color=textColor, color_sel=textColor))
				else:
					res.append(MultiContentEntryText(
						pos=(xPos, yPos), size=(textWidth + textPaddings * 2, height - 2),
						font=0, flags=textFlags,
						text=buttonText, color=textColor, color_sel=textColor, backcolor=backColor, cornerRadius=self.cornerRadius))

				xPos += textWidth + textPaddings * 2 + self.spacingButtons
			if xPos > width and self.layoutStyle != "fluid":
				self.layoutStyle = "fluid"
				return self.buildEntry(sequence)

		return res

	def postWidgetCreate(self, instance):
		instance.setSelectionEnable(False)
		instance.setContent(self.l)
		instance.allowNativeKeys(False)

	def constructColorButtonSequence(self):
		sequence = {}
		for x, val in self.sources.items():
			if hasattr(val, "text") and val.text:
				sequence[x] = val

		self.updateAddon(sequence)

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes[:]:
			if attrib == "pixmaps":
				self.pixmaps = {k: v for k, v in (item.split(':') for item in value.split(','))}
			elif attrib == "spacing":
				self.spacingButtons = parseScale(value)
			elif attrib == "spacingPixmapText":
				self.spacingPixmapText = parseScale(value)
			elif attrib == "layoutStyle":
				self.layoutStyle = value
			elif attrib == "alignment":
				self.alignment = value
			elif attrib == "orientation":
				self.orientation = self.orientations.get(value, self.orientations["orHorizontal"])
				if self.orientation == eListbox.orHorizontal:
					self.instance.setOrientation(eListbox.orVertical)
					self.l.setOrientation(eListbox.orVertical)
				else:
					self.instance.setOrientation(eListbox.orHorizontal)
					self.l.setOrientation(eListbox.orHorizontal)
			elif attrib == "font":
				self.font = parseFont(value, parent.scale)
			elif attrib == "foregroundColor":
				self.foreColor = parseColor(value).argb()
			elif attrib == "textColors":
				self.colors = {k: v for k, v in (item.split(':') for item in value.split(','))}
			elif attrib == "buttonCornerRadius":
				self.cornerRadius = parseScale(value)
			elif attrib == "renderType":
				self.renderType = value
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		self.l.setFont(0, self.font)
		return GUIAddon.applySkin(self, desktop, parent)

	def _calcTextWidth(self, text, font=None, size=None):
		if size:
			self.textRenderer.instance.resize(size)
		if font:
			self.textRenderer.instance.setFont(font)
		self.textRenderer.text = text
		return self.textRenderer.instance.calculateSize().width()

	def getDesktopWith(self):
		return getDesktop(0).size().width()
