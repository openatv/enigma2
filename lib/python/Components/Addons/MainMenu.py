from Components.Addons.GUIAddon import GUIAddon

from enigma import eListbox, eListboxPythonMultiContent, gFont, RT_BLEND, RT_HALIGN_LEFT, RT_VALIGN_CENTER, getDesktop, eSize

from skin import applySkinFactor, parseFont, parseColor, parseScale

from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend
from Components.Label import Label


class MainMenu(GUIAddon):
	def __init__(self):
		GUIAddon.__init__(self)
		self.itemHeight = 36
		self.itemWidth = 36
		self.l = eListboxPythonMultiContent()  # noqa: E741
		self.l.setBuildFunc(self.buildEntry)
		self.l.setItemHeight(self.itemHeight)
		self.l.setItemWidth(self.itemWidth)
		self.orientation = eListbox.orVertical
		self.font = gFont("Regular", applySkinFactor(22))
		self.iconSize = 0
		self.foregroundColor = 0xffffff
		self.foregroundColorSelected = 0xffffff
		self.backgroundColor = 0x000000
		self.textRenderer = Label("")
		self.longestMenuTextWidth = 0
		self.minWidth = 100
		self.maxWidth = 700

	def onContainerShown(self):
		self.textRenderer.GUIcreate(self.relatedScreen.instance)
		self.source.onListUpdated.append(self.constructMenu)
		self.constructMenu()

	GUI_WIDGET = eListbox

	def getDesktopWith(self):
		return getDesktop(0).size().width()

	def _calcTextWidth(self, text, font=None, size=None):
		if size:
			self.textRenderer.instance.resize(size)
		if font:
			self.textRenderer.instance.setFont(font)
		self.textRenderer.text = text
		return self.textRenderer.instance.calculateSize().width()

	def buildEntry(self, *args):
		item_text = args[0]
		menupng = args[5] if len(args) >= 6 else None
		xPos = 17
		yPos = 5

		res = [None]

		if self.iconSize > 0 and menupng:
			res.append(MultiContentEntryPixmapAlphaBlend(
						pos=(xPos, yPos),
						size=(self.iconSize, self.iconSize),
						png=menupng))
			xPos += self.iconSize + 10
		textWidth = self.longestMenuTextWidth if self.maxWidth >= (self.longestMenuTextWidth + self.iconSize + 40 + 10) else self.maxWidth - self.iconSize - 40 - 10
		res.append(MultiContentEntryText(
				pos=(xPos, 0),
				size=(textWidth, self.itemHeight),
				font=0, flags=RT_BLEND | RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				text=item_text,
				color=self.foregroundColor, color_sel=self.foregroundColorSelected,
				backcolor=None, backcolor_sel=None))

		return res

	def moveSelection(self, index):
		if self.instance is not None:
			self.instance.moveSelectionTo(index)

	def selectionChanged(self):
		if self.instance and hasattr(self, "source"):
			self.source.setIndex(self.instance.getCurrentIndex())  # relay selection changed to underlaying list
			self.source.setConnectedGuiElement(self)

	def setMinWidth(self, value):
		self.minWidth = parseScale(value)

	def setMaxWidth(self, value):
		self.maxWidth = parseScale(value)

	def setIconSize(self, value):
		self.iconSize = parseScale(value)

	def setForegroundColor(self, value):
		self.foregroundColor = parseColor(value).argb()

	def setForegroundColorSelected(self, value):
		self.foregroundColorSelected = parseColor(value).argb()

	def setBackgroundColor(self, value):
		self.backgroundColor = parseColor(value).argb()

	def setItemWidth(self, value):
		self.itemWidth = parseScale(value)
		self.l.setItemWidth(self.itemWidth)

	def setItemHeight(self, value):
		self.itemHeight = parseScale(value)
		self.l.setItemHeight(self.itemHeight)

	def postWidgetCreate(self, instance):
		instance.selectionChanged.get().append(self.selectionChanged)
		instance.setSelectionEnable(True)
		instance.setContent(self.l)
		instance.allowNativeKeys(True)

	def constructMenu(self):
		for x in self.source.list:
			textWidth = self._calcTextWidth(x[0], font=self.font, size=eSize(self.getDesktopWith() // 3, 0))
			if textWidth > self.longestMenuTextWidth:
				self.longestMenuTextWidth = textWidth
		curSize = self.instance.size()
		destWidth = self.iconSize + 20 * 2 + 10
		destWidth += self.longestMenuTextWidth
		if destWidth > self.maxWidth:
			destWidth = self.maxWidth
		if destWidth > self.minWidth:
			self.instance.resize(eSize(destWidth, curSize.height()))
			self.relatedScreen.screenContentChanged()
		self.l.setList(self.source.list)

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes[:]:
			if attrib == "font":
				self.font = parseFont(value, parent.scale)
			elif attrib == "foregroundColor":
				self.foregroundColor = parseColor(value).argb()
			elif attrib == "foregroundColorSelected":
				self.foregroundColorSelected = parseColor(value).argb()
			elif attrib == "backgroundColor":
				self.backgroundColor = parseColor(value).argb()
			elif attrib == "iconSize":
				self.iconSize = parseScale(value)
			elif attrib == "minWidth":
				self.minWidth = parseScale(value)
			elif attrib == "maxWidth":
				self.maxWidth = parseScale(value)
			elif attrib == "itemWidth":
				self.itemWidth = parseScale(value)
			elif attrib == "itemHeight":
				self.itemHeight = parseScale(value)
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		self.l.setFont(0, self.font)
		self.l.setItemHeight(self.itemHeight)
		self.l.setItemWidth(self.itemWidth)

		return GUIAddon.applySkin(self, desktop, parent)
