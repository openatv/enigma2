from enigma import eLabel, eListbox, eListboxPythonMultiContent, eSize, getDesktop, gFont, BT_ALIGN_CENTER, BT_VALIGN_CENTER, RT_VALIGN_CENTER, RT_HALIGN_LEFT
from skin import applySkinFactor, parseColor, parseFont, parseScale
from Components.Addons.GUIAddon import GUIAddon
from Components.Label import Label
from Components.MultiContent import MultiContentEntryPixmapAlphaBlend
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
		self.alignment = "left"
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
		l_list = []
		l_list.append((sequence,))
		self.l.setList(l_list)

	def buildEntry(self, sequence):
		res = [None]
		if len(sequence) == 0:
			return res
		width = self.instance.size().width()
		height = self.instance.size().height()
		xPos = width if self.alignment == "right" else 0
		yPos = 0
		sectorWidth = width // len(sequence)
		minSectorWidth = width // 4

		pic = None
		pixd_width = 0

		for x, val in sequence.items():
			textColor = self.foreColor
			if x in self.colors:
				textColor = parseColor(self.colors[x]).argb()
			if x in self.pixmaps:
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, self.pixmaps[x]))
				if pic:
					pixd_size = pic.size()
					pixd_width = pixd_size.width()
					pic_x_pos = (xPos - pixd_width) if self.alignment == "right" else xPos
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos=(pic_x_pos, yPos),
						size=(pixd_width, height),
						png=pic,
						backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
					if self.alignment == "right":
						xPos -= pixd_width + self.spacingPixmapText
					else:
						xPos += pixd_width + self.spacingPixmapText
			if hasattr(val, "text"):
				buttonText = val.text
			else:
				buttonText = ""

			if buttonText:
				textWidth = self._calcTextWidth(buttonText, font=self.font, size=eSize(self.getDesktopWith() // 3, 0))
			else:
				textWidth = 0
			if self.layoutStyle != "fluid":
				if textWidth < (minSectorWidth - self.spacingButtons - self.spacingPixmapText - pixd_width):
					textWidth = minSectorWidth - self.spacingButtons - self.spacingPixmapText - pixd_width
			if buttonText:
				if textColor is not None:
					res.append((eListboxPythonMultiContent.TYPE_TEXT, xPos, yPos, textWidth, height - 2, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, buttonText, textColor))
				else:
					res.append((eListboxPythonMultiContent.TYPE_TEXT, xPos, yPos, textWidth, height - 2, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, buttonText))
				xPos += textWidth + self.spacingButtons
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
				self.pixmaps = dict(item.split(':') for item in value.split(','))
			elif attrib == "spacingButtons":
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
				self.font = parseFont(value, ((1, 1), (1, 1)))
			elif attrib == "foregroundColor":
				self.foreColor = parseColor(value).argb()
			elif attrib == "textColors":
				self.colors = dict(item.split(':') for item in value.split(','))
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
