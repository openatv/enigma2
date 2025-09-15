from Components.Addons.GUIAddon import GUIAddon

from enigma import eListbox, eListboxPythonMultiContent, BT_ALIGN_CENTER, BT_VALIGN_CENTER, RT_BLEND, gFont, eSize, getDesktop, RT_HALIGN_CENTER, RT_VALIGN_CENTER

from skin import parseScale, applySkinFactor, parseFont, parseColor

from Components.MultiContent import MultiContentEntryPixmapAlphaBlend, MultiContentEntryText
from Components.Sources.List import List
from Components.Label import Label

from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap


class Pager(GUIAddon):
	def __init__(self):
		GUIAddon.__init__(self)
		self.foreColor = None
		self.l = eListboxPythonMultiContent()  # noqa: E741
		self.l.setBuildFunc(self.buildEntry)
		self.l.setItemHeight(25)  # 25 is the height of the default images. For other images set the height in the skin.
		self.l.setItemWidth(25)  # 25 is the width of the default images. For other images set the width in the skin.
		self.spacing = applySkinFactor(5)
		self.font = gFont("Regular", 16)
		self.picDotPage = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/dot.png"))
		self.picDotCurPage = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/dotfull.png"))
		self.picShevronLeft = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/shevronleft.png"))
		self.picShevronRight = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/shevronright.png"))
		self.picShevronUp = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/shevronup.png"))
		self.picShevronDown = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/shevrondown.png"))
		self.showIcons = "showAll"  # can be "showAll", "onlyFirst", "onlyLast"
		self.orientations = {"orHorizontal": eListbox.orHorizontal, "orVertical": eListbox.orVertical}
		self.orientation = eListbox.orHorizontal
		self.maxPages = 10
		self.currentPageStyle = "bubbletext"  # possible is bubbletext and graphic
		self.textRenderer = Label("")
		self.bubbletextCornerRadius = 12
		self.bubbletextBkColor = 0x02444444
		self.bubbletextPadding = 10

	def onContainerShown(self):
		# disable listboxes default scrollbars
		if hasattr(self.source, "instance") and hasattr(self.source.instance, "setScrollbarMode"):
			self.source.instance.setScrollbarMode(eListbox.showNever)

		onSelectionChanged = x if (x := getattr(self.source, "onSelectionChanged", None)) is not None else getattr(self.source, "onSelChanged", None)

		if (isinstance(onSelectionChanged, list) or isinstance(onSelectionChanged, List)) and self.initPager not in onSelectionChanged:
			onSelectionChanged.append(self.initPager)
		self.textRenderer.GUIcreate(self.relatedScreen.instance)
		self.initPager()

	GUI_WIDGET = eListbox

	def onSourceVisibleChanged(self, visible):
		if visible:
			self.show()
		else:
			self.hide()

	def buildEntry(self, currentPage, pageCount):
		width = self.l.getItemSize().width()
		height = self.l.getItemSize().height()
		xPos = width
		yPos = height

		if self.picDotPage:
			pixdSize = self.picDotPage.size()
			pixdWidth = pixdSize.width()
			pixdHeight = pixdSize.height()
			widthDots = pixdWidth + (pixdWidth + self.spacing) * pageCount
			heightDots = pixdHeight + (pixdHeight + self.spacing) * pageCount
			xPos = (width - widthDots) / 2 - pixdWidth / 2 if self.showIcons == "showAll" else 0
			yPos = (height - heightDots) / 2 - pixdHeight / 2 if self.showIcons == "showAll" else 0
		res = [None]
		if self.showIcons == "showAll" and pageCount > 0 and self.maxPages > 0 and pageCount > self.maxPages:
			widthDots = pixdWidth + (pixdWidth + self.spacing) * (2 if currentPage > 0 and currentPage < pageCount else 1)
			xPos = (width - widthDots) / 2 - pixdWidth / 2
			yPos = (height - heightDots) / 2 - pixdHeight / 2
			if self.orientation == eListbox.orHorizontal:
				if currentPage > 0:
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos=(xPos, 0),
						size=(pixdWidth, pixdHeight),
						png=self.picShevronLeft,
						backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
					xPos += pixdWidth + self.spacing
				if self.currentPageStyle == "bubbletext":
					textBubble = f"{currentPage + 1} / {pageCount + 1}"
					textWidth = self._calcTextWidth(textBubble, font=self.font, size=eSize(self.getDesktopWith() // 3, 0))
					res.append(MultiContentEntryText(
						pos=(xPos, 0),
						size=(textWidth + self.bubbletextPadding * 2, height),
						font=0, flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER,
						text=" ",
						cornerRadius=self.bubbletextCornerRadius,
						backcolor=self.bubbletextBkColor, backcolor_sel=self.bubbletextBkColor))
					res.append(MultiContentEntryText(
							pos=(xPos + self.bubbletextPadding - 1, 0), size=(textWidth + 2, height),
							font=0, flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_BLEND,
							text=textBubble, color=self.foreColor, color_sel=self.foreColor,
							textBWidth=1, textBColor=0x010101))
					xPos += textWidth + self.bubbletextPadding * 2 + self.spacing
				else:
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos=(xPos, 0),
						size=(pixdWidth, pixdHeight),
						png=self.picDotCurPage,
						backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
					xPos += pixdWidth + self.spacing
				if currentPage < pageCount:
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos=(xPos, 0),
						size=(pixdWidth, pixdHeight),
						png=self.picShevronRight,
						backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
			else:
				if currentPage > 0:
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos=(0, yPos),
						size=(pixdWidth, pixdHeight),
						png=self.picShevronLeft,
						backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
					yPos += pixdHeight + self.spacing
				res.append(MultiContentEntryPixmapAlphaBlend(
					pos=(0, yPos),
					size=(pixdWidth, pixdHeight),
					png=self.picDotCurPage,
					backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
				yPos += pixdHeight + self.spacing
				if currentPage < pageCount:
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos=(0, yPos),
						size=(pixdWidth, pixdHeight),
						png=self.picShevronRight,
						backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
		elif pageCount > (0 if self.showIcons == "showAll" else -1):
			pages = list(range(pageCount + 1))
			# add option to show just first or last icon
			if self.showIcons == "onlyFirst":
				pages = [pages[0]]
			elif self.showIcons == "onlyLast":
				pages = [pages[-1]]
			for x in pages:
				if self.picDotPage and self.picDotCurPage:
					if self.orientation == eListbox.orHorizontal:
						res.append(
							MultiContentEntryPixmapAlphaBlend(
								pos=(xPos, 0),
								size=(pixdWidth, pixdHeight),
								png=self.picDotCurPage if x == currentPage else self.picDotPage,
								backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
						xPos += pixdWidth + self.spacing
					else:
						res.append(
							MultiContentEntryPixmapAlphaBlend(
								pos=(0, yPos),
								size=(pixdWidth, pixdHeight),
								png=self.picDotCurPage if x == currentPage else self.picDotPage,
								backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER | BT_VALIGN_CENTER))
						yPos += pixdHeight + self.spacing

		return res

	def selChange(self, currentPage, pagesCount):
		lList = []
		lList.append((currentPage, pagesCount))
		self.l.setList(lList)

	def postWidgetCreate(self, instance):
		instance.setSelectionEnable(False)
		instance.setContent(self.l)
		instance.allowNativeKeys(False)

	def getSourceOrientation(self):
		if isinstance(self.source, List):  # Components.Sources.List
			origSource = self.source.connectedGuiElement or self.source.master.master
		else:
			origSource = self.source
		if hasattr(origSource, "instance") and hasattr(origSource.instance, "getOrientation"):
			return origSource.instance.getOrientation()
		return eListbox.orVertical

	def getCurrentIndex(self):
		if hasattr(self.source, "index"):
			return self.source.index
		if hasattr(self.source, "currentIndex"):
			return self.source.currentIndex
		return self.source.l.getCurrentSelectionIndex()

	def getSourceSize(self):
		if isinstance(self.source, List):  # Components.Sources.List
			return self.source.connectedGuiElement and self.source.connectedGuiElement.instance.size() or self.source.master.master.instance.size()
		return self.source.instance.size()

	def getListCount(self):
		if hasattr(self.source, 'listCount'):
			return self.source.listCount
		elif hasattr(self.source, 'list'):
			return len(self.source.list)
		elif hasattr(self.source, 'l') and hasattr(self.source.l, 'getListSize'):
			return self.source.l.getListSize()
		elif hasattr(self.source, "totalItemsCount"):
			return self.source.totalItemsCount
		return 0

	def getListItemSize(self):
		if isinstance(self.source, List):  # Components.Sources.List
			origSource = self.source.connectedGuiElement or self.source.master.master
		else:
			origSource = self.source
		if hasattr(origSource, 'content'):
			return origSource.content.getItemSize()

		return origSource.l.getItemSize()

	def initPager(self):
		if self.source.__class__.__name__ == "ScrollLabel":
			currentPageIndex = self.source.curPos // self.source.pageHeight
			if not ((self.source.TotalTextHeight - self.source.curPos) % self.source.pageHeight):
				currentPageIndex += 1
			pagesCount = -(-self.source.TotalTextHeight // self.source.pageHeight) - 1
			self.selChange(currentPageIndex, pagesCount)
		else:
			lOrientation = self.getSourceOrientation()
			if lOrientation == eListbox.orVertical or lOrientation == eListbox.orGrid:
				listControledlSize = self.getSourceSize().height()
			else:
				listControledlSize = self.getSourceSize().width()

			if listControledlSize > 0:
				currentIndex = self.getCurrentIndex()
				listCount = self.getListCount()
				if lOrientation == eListbox.orVertical:
					itemControlledSizeParam = self.getListItemSize().height()
				elif lOrientation == eListbox.orGrid:
					itemControlledSizeParam = self.getListItemSize().height()
				else:
					itemControlledSizeParam = self.getListItemSize().width()
				items_per_page = listControledlSize // itemControlledSizeParam
				if items_per_page > 0:
					currentPageIndex = currentIndex // items_per_page
					pagesCount = -(listCount // -items_per_page) - 1
					self.selChange(currentPageIndex, pagesCount)

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes[:]:
			if attrib == "picPage":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picDotPage = pic
			elif attrib == "picPageCurrent":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picDotCurPage = pic
			elif attrib == "picL":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picShevronLeft = pic
			elif attrib == "picR":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picShevronRight = pic
			elif attrib == "picU":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picShevronUp = pic
			elif attrib == "picD":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picShevronDown = pic
			elif attrib == "itemHeight":
				self.l.setItemHeight(parseScale(value))
			elif attrib == "itemWidth":
				self.l.setItemWidth(parseScale(value))
			elif attrib == "spacing":
				self.spacing = parseScale(value)
			elif attrib == "showIcons":
				self.showIcons = value
			elif attrib == "maxPages":
				self.maxPages = int(value)
			elif attrib == "currentPageStyle":
				self.currentPageStyle = value
			elif attrib == "bubbletextFont":
				self.font = parseFont(value, parent.scale)
			elif attrib == "bubbletextPadding":
				self.bubbletextPadding = parseScale(value)
			elif attrib == "foregroundColor":
				self.foreColor = parseColor(value).argb()
			elif attrib == "bubbletextBackgroundColor":
				self.bubbletextBkColor = parseColor(value).argb()
			elif attrib == "orientation":
				self.orientation = self.orientations.get(value, self.orientations["orHorizontal"])
				if self.orientation == eListbox.orHorizontal:
					self.instance.setOrientation(eListbox.orVertical)
					self.l.setOrientation(eListbox.orVertical)
				else:
					self.instance.setOrientation(eListbox.orHorizontal)
					self.l.setOrientation(eListbox.orHorizontal)
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
