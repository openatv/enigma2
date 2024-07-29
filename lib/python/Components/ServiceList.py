from enigma import eListboxServiceContent, eListbox, eServiceCenter, eServiceReference, gFont, eRect, eSize

from Components.config import config, ConfigYesNo, ConfigSelection, ConfigSubsection
from Components.GUIComponent import GUIComponent
from Components.Renderer.Picon import getPiconName
from skin import parseColor, parseFont
from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap
from Tools.TextBoundary import getTextBoundarySize


def InitServiceListSettings():
	config.channelSelection = ConfigSubsection()
	config.channelSelection.showNumber = ConfigYesNo(default=True)
	config.channelSelection.showPicon = ConfigYesNo(default=False)
	config.channelSelection.showServiceTypeIcon = ConfigYesNo(default=False)
	config.channelSelection.showCryptoIcon = ConfigYesNo(default=False)
	config.channelSelection.recordIndicatorMode = ConfigSelection(default=2, choices=[
		(0, _("None")),
		(1, _("Record Icon")),
		(2, _("Colored Text"))
	])
	config.channelSelection.piconRatio = ConfigSelection(default=167, choices=[
		(167, _("XPicon, ZZZPicon")),
		(235, _("ZZPicon")),
		(250, _("ZPicon"))
	])
	choiceList = [("", _("Legacy mode"))]
	config.channelSelection.screenStyle = ConfigSelection(default="", choices=choiceList)
	config.channelSelection.widgetStyle = ConfigSelection(default="", choices=choiceList)


def refreshServiceList(configElement=None):
	from Screens.InfoBar import InfoBar
	InfoBarInstance = InfoBar.instance
	if InfoBarInstance is not None:
		servicelist = InfoBarInstance.servicelist
		if servicelist:
			servicelist.setMode()


class ServiceList(GUIComponent):
	MODE_NORMAL = 0
	MODE_FAVOURITES = 1
	MODE_ALL = 2

	def __init__(self, serviceList):
		self.serviceList = serviceList
		GUIComponent.__init__(self)
		self.l = eListboxServiceContent()

		pic = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/folder.png"))
		pic and self.l.setPixmap(self.l.picFolder, pic)

		pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/marker.png"))
		pic and self.l.setPixmap(self.l.picMarker, pic)

		pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/ico_dvb-s.png"))
		pic and self.l.setPixmap(self.l.picDVB_S, pic)

		pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/ico_dvb-c.png"))
		pic and self.l.setPixmap(self.l.picDVB_C, pic)

		pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/ico_dvb-t.png"))
		pic and self.l.setPixmap(self.l.picDVB_T, pic)

		pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/ico_stream.png"))
		pic and self.l.setPixmap(self.l.picStream, pic)

		pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/ico_service_group.png"))
		pic and self.l.setPixmap(self.l.picServiceGroup, pic)

		pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/icon_crypt.png"))
		pic and self.l.setPixmap(self.l.picCrypto, pic)

		pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/record.png"))
		pic and self.l.setPixmap(self.l.picRecord, pic)

		self.root = None
		self.mode = self.MODE_NORMAL
		self.listHeight = 0
		self.listWidth = 0
		self.ServiceNumberFontName = "Regular"
		self.ServiceNumberFontSize = 20
		self.ServiceNameFontName = "Regular"
		self.ServiceNameFontSize = 22
		self.ServiceInfoFontName = "Regular"
		self.ServiceInfoFontSize = 18
		self.progressInfoFontName = "Regular"
		self.progressInfoFontSize = -1
		self.progressBarWidth = 52
		self.fieldMargins = 10
		self.itemsDistances = 8
		self.listMarginRight = 25  # scrollbar is fixed 20 + 5 Extra marge
		self.listMarginLeft = 5

		self.onSelectionChanged = []

	def applySkin(self, desktop, parent):
		def foregroundColorMarked(value):
			self.l.setColor(eListboxServiceContent.markedForeground, parseColor(value))

		def foregroundColorMarkedSelected(value):
			self.l.setColor(eListboxServiceContent.markedForegroundSelected, parseColor(value))

		def backgroundColorMarked(value):
			self.l.setColor(eListboxServiceContent.markedBackground, parseColor(value))

		def backgroundColorMarkedSelected(value):
			self.l.setColor(eListboxServiceContent.markedBackgroundSelected, parseColor(value))

		def foregroundColorServiceNotAvail(value):
			self.l.setColor(eListboxServiceContent.serviceNotAvail, parseColor(value))

		def foregroundColorEvent(value):
			self.l.setColor(eListboxServiceContent.eventForeground, parseColor(value))

		def colorServiceDescription(value):
			self.l.setColor(eListboxServiceContent.serviceDescriptionColor, parseColor(value))

		def foregroundColorEventSelected(value):
			self.l.setColor(eListboxServiceContent.eventForegroundSelected, parseColor(value))

		def colorServiceDescriptionSelected(value):
			self.l.setColor(eListboxServiceContent.serviceDescriptionColorSelected, parseColor(value))

		def foregroundColorEventborder(value):
			self.l.setColor(eListboxServiceContent.eventborderForeground, parseColor(value))

		def foregroundColorEventborderSelected(value):
			self.l.setColor(eListboxServiceContent.eventborderForegroundSelected, parseColor(value))

		def colorEventProgressbar(value):
			self.l.setColor(eListboxServiceContent.serviceEventProgressbarColor, parseColor(value))

		def colorEventProgressbarSelected(value):
			self.l.setColor(eListboxServiceContent.serviceEventProgressbarColorSelected, parseColor(value))

		def colorEventProgressbarBorder(value):
			self.l.setColor(eListboxServiceContent.serviceEventProgressbarBorderColor, parseColor(value))

		def colorEventProgressbarBorderSelected(value):
			self.l.setColor(eListboxServiceContent.serviceEventProgressbarBorderColorSelected, parseColor(value))

		def colorServiceRecorded(value):
			self.l.setColor(eListboxServiceContent.serviceRecorded, parseColor(value))

		def colorServicePseudoRecorded(value):
			self.l.setColor(eListboxServiceContent.servicePseudoRecorded, parseColor(value))

		def colorServiceStreamed(value):
			self.l.setColor(eListboxServiceContent.serviceStreamed, parseColor(value))

		def colorFallbackItem(value):
			self.l.setColor(eListboxServiceContent.serviceItemFallback, parseColor(value))

		def colorServiceSelectedFallback(value):
			self.l.setColor(eListboxServiceContent.serviceSelectedFallback, parseColor(value))

		def colorServiceDescriptionFallback(value):
			self.l.setColor(eListboxServiceContent.eventForegroundFallback, parseColor(value))

		def colorServiceDescriptionSelectedFallback(value):
			self.l.setColor(eListboxServiceContent.eventForegroundSelectedFallback, parseColor(value))

		def colorServiceRecording(value):
			self.l.setColor(eListboxServiceContent.serviceRecordingColor, parseColor(value))

		def colorServiceWithAdvertisment(value):
			self.l.setColor(eListboxServiceContent.serviceAdvertismentColor, parseColor(value))

		def picServiceEventProgressbar(value):
			pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
			pic and self.l.setPixmap(self.l.picServiceEventProgressbar, pic)

		def serviceItemHeight(value):
			self.ItemHeight = int(value)

		def serviceNameFont(value):
			font = parseFont(value, ((1, 1), (1, 1)))
			self.ServiceNameFontName = font.family
			self.ServiceNameFontSize = font.pointSize

		def serviceInfoFont(value):
			font = parseFont(value, ((1, 1), (1, 1)))
			self.ServiceInfoFontName = font.family
			self.ServiceInfoFontSize = font.pointSize

		def serviceNumberFont(value):
			font = parseFont(value, ((1, 1), (1, 1)))
			self.ServiceNumberFontName = font.family
			self.ServiceNumberFontSize = font.pointSize

		def progressInfoFont(value):
			font = parseFont(value, ((1, 1), (1, 1)))
			self.progressInfoFontName = font.family
			self.progressInfoFontSize = font.pointSize

		def progressbarHeight(value):
			self.l.setProgressbarHeight(int(value))

		def progressbarBorderWidth(value):
			self.l.setProgressbarBorderWidth(int(value))

		def progressBarWidth(value):
			self.progressBarWidth = int(value)

		def fieldMargins(value):
			self.fieldMargins = int(value)

		def listMarginRight(value):
			self.listMarginRight = int(value)

		def listMarginLeft(value):
			self.listMarginLeft = int(value)

		def nonplayableMargins(value):
			self.l.setNonplayableMargins(int(value))

		def itemsDistances(value):
			self.itemsDistances = int(value)
			self.l.setItemsDistances(self.itemsDistances)
		if self.skinAttributes is not None:
			for (attrib, value) in list(self.skinAttributes):
				try:
					locals().get(attrib)(value)
					self.skinAttributes.remove((attrib, value))
				except:
					pass
		rc = GUIComponent.applySkin(self, desktop, parent)
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.setItemsPerPage()
		self.setFontsize()
		return rc

	def connectSelChanged(self, fnc):
		if fnc not in self.onSelectionChanged:
			self.onSelectionChanged.append(fnc)

	def disconnectSelChanged(self, fnc):
		if fnc in self.onSelectionChanged:
			self.onSelectionChanged.remove(fnc)

	def selectionChanged(self):
		for x in self.onSelectionChanged:
			x()

	def setCurrent(self, ref, adjust=True):
		if self.l.setCurrent(ref):
			return None
		from Components.ServiceEventTracker import InfoBarCount
		if adjust and config.usage.multibouquet.value and InfoBarCount == 1 and ref and ref.type != 8192:
			print("[servicelist] search for service in userbouquets")
			isRadio = ref.toString().startswith("1:0:2:") or ref.toString().startswith("1:0:A:")
			if self.serviceList:
				revert_mode = config.servicelist.lastmode.value
				revert_root = self.getRoot()
				if not isRadio:
					self.serviceList.setModeTv()
					revert_tv_root = self.getRoot()
					bouquets = self.serviceList.getBouquetList()
					for bouquet in bouquets:
						self.serviceList.enterUserbouquet(bouquet[1])
						if self.l.setCurrent(ref):
							config.servicelist.lastmode.save()
							self.serviceList.saveChannel(ref)
							return True
					self.serviceList.enterUserbouquet(revert_tv_root)
				else:
					self.serviceList.setModeRadio()
					revert_radio_root = self.getRoot()
					bouquets = self.serviceList.getBouquetList()
					for bouquet in bouquets:
						self.serviceList.enterUserbouquet(bouquet[1])
						if self.l.setCurrent(ref):
							config.servicelist.lastmode.save()
							self.serviceList.saveChannel(ref)
							return True
					self.serviceList.enterUserbouquet(revert_radio_root)
				print("[servicelist] service not found in any userbouquets")
				if revert_mode == "tv":
					self.serviceList.setModeTv()
				elif revert_mode == "radio":
					self.serviceList.setModeRadio()
				self.serviceList.enterUserbouquet(revert_root)
		return False

	def getCurrent(self):
		r = eServiceReference()
		self.l.getCurrent(r)
		return r

	def getPrev(self):
		r = eServiceReference()
		self.l.getPrev(r)
		return r

	def getNext(self):
		r = eServiceReference()
		self.l.getNext(r)
		return r

	def getList(self):
		return self.l.getList()

	def atBegin(self):
		return self.instance.atBegin()

	def atEnd(self):
		return self.instance.atEnd()

	def moveToChar(self, char):
		# TODO fill with life
		print("Next char: ")
		index = self.l.getNextBeginningWithChar(char)
		indexup = self.l.getNextBeginningWithChar(char.upper())
		if indexup != 0:
			if index > indexup or index == 0:
				index = indexup

		self.instance.moveSelectionTo(index)
		print("Moving to character %s" % str(char))

	def moveToNextMarker(self):
		idx = self.l.getNextMarkerPos()
		self.instance.moveSelectionTo(idx)

	def moveToPrevMarker(self):
		idx = self.l.getPrevMarkerPos()
		self.instance.moveSelectionTo(idx)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	GUI_WIDGET = eListbox

	def setItemsPerPage(self):
		if self.listHeight > 0:
			itemHeight = self.listHeight // (config.usage.serviceitems_per_page_twolines.value if config.usage.servicelist_twolines.value else config.usage.serviceitems_per_page.value)
		else:
			itemHeight = 28
		self.ItemHeight = itemHeight
		self.l.setItemHeight(itemHeight)
		if self.listHeight:
			self.instance.resize(eSize(self.listWidth, self.listHeight // itemHeight * itemHeight))

	def setFontsize(self):
		self.ServiceNumberFont = gFont(self.ServiceNumberFontName, self.ServiceNumberFontSize + config.usage.servicenum_fontsize.value)
		self.ServiceNameFont = gFont(self.ServiceNameFontName, self.ServiceNameFontSize + config.usage.servicename_fontsize.value)
		self.ServiceInfoFont = gFont(self.ServiceInfoFontName, self.ServiceInfoFontSize + config.usage.serviceinfo_fontsize.value)
		if self.progressInfoFontSize == -1:  # font in skin not defined
			self.ProgressInfoFont = gFont(self.ServiceInfoFontName, self.ServiceInfoFontSize + config.usage.progressinfo_fontsize.value)
		else:
			self.ProgressInfoFont = gFont(self.progressInfoFontName, self.progressInfoFontSize + config.usage.progressinfo_fontsize.value)

		self.l.setElementFont(self.l.celServiceName, self.ServiceNameFont)
		self.l.setElementFont(self.l.celServiceNumber, self.ServiceNumberFont)
		self.l.setElementFont(self.l.celServiceInfo, self.ServiceInfoFont)

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
		self.setFontsize()
		self.setMode(self.mode)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

	def getRoot(self):
		return self.root

	def getRootServices(self):
		serviceHandler = eServiceCenter.getInstance()
		list = serviceHandler.list(self.root)
		dest = []
		if list is not None:
			while True:
				s = list.getNext()
				if s.valid():
					dest.append(s.toString())
				else:
					break
		return dest

	def setPlayableIgnoreService(self, ref):
		self.l.setIgnoreService(ref)

	def setRoot(self, root, justSet=False):
		self.root = root
		self.l.setRoot(root, justSet)
		if not justSet:
			self.l.sort()
		self.selectionChanged()

	def resetRoot(self):
		index = self.instance.getCurrentIndex()
		self.l.setRoot(self.root, False)
		self.l.sort()
		self.instance.moveSelectionTo(index)

	def removeCurrent(self):
		self.l.removeCurrent()

	def addService(self, service, beforeCurrent=False):
		self.l.addService(service, beforeCurrent)

	def fillFinished(self):
		self.l.FillFinished()

	def finishFill(self):
		self.l.FillFinished()
		self.l.sort()


# stuff for multiple marks (edit mode / later multiepg)


	def clearMarks(self):
		self.l.initMarked()

	def isMarked(self, ref):
		return self.l.isMarked(ref)

	def isVertical(self):
		return True

	def addMarked(self, ref):
		self.l.addMarked(ref)

	def removeMarked(self, ref):
		self.l.removeMarked(ref)

	def getMarked(self):
		i = self.l
		i.markedQueryStart()
		ref = eServiceReference()
		marked = []
		while i.markedQueryNext(ref) == 0:
			marked.append(ref.toString())
			ref = eServiceReference()
		return marked

#just for movemode.. only one marked entry..
	def setCurrentMarked(self, state):
		self.l.setCurrentMarked(state)

	def setMode(self, mode):
		if mode == self.MODE_ALL:  # Mode all is not supported in legacy mode
			self.mode = self.MODE_NORMAL
		self.setItemsPerPage()
		self.l.setItemHeight(self.ItemHeight)
		self.l.setVisualMode(eListboxServiceContent.visModeComplex)
		self.l.setServicePiconDownsize(int(config.usage.servicelist_picon_downsize.value))
		self.l.setServicePiconRatio(int(config.usage.servicelist_picon_ratio.value))

		twoLines = config.usage.servicelist_twolines.value
		self.l.setShowTwoLines(twoLines)

		if config.usage.service_icon_enable.value:
			self.l.setGetPiconNameFunc(getPiconName)
		else:
			self.l.setGetPiconNameFunc(None)

		rowWidth = self.instance.size().width() - self.listMarginRight

		if mode != self.MODE_FAVOURITES or not config.usage.show_channel_numbers_in_servicelist.value:
			channelNumberWidth = 0
			channelNumberSpace = self.listMarginLeft
		else:
			channelNumberWidth = config.usage.alternative_number_mode.value and getTextBoundarySize(self.instance, self.ServiceNumberFont, self.instance.size(), "0" * int(config.usage.maxchannelnumlen.value)).width() or getTextBoundarySize(self.instance, self.ServiceNumberFont, self.instance.size(), "00000").width()
			channelNumberSpace = self.fieldMargins + self.listMarginLeft

		numberHeight = self.ItemHeight // 2 if twoLines and config.usage.servicelist_servicenumber_valign.value == "1" else self.ItemHeight
		self.l.setElementPosition(self.l.celServiceNumber, eRect(self.listMarginLeft, 0, channelNumberWidth, numberHeight))

		#progress view modes for two lines
		#  0 - single, centered
		# 10 - single, upper line
		#  1 - dual, bar upper line, value lower line
		#  2 - dual, value upper line, bar lower line
		# 11 - dual, bar and value upper line
		# 12 - dual, value and bar upper line
		if twoLines:
			viewMode, viewType = (config.usage.servicelist_eventprogress_valign.value + config.usage.servicelist_eventprogress_view_mode.value).split('_')
			viewMode = int(viewMode)
		else:
			viewType = config.usage.show_event_progress_in_servicelist.value
			viewMode = 0

		self.l.setProgressViewMode(viewMode)

		minuteUnit = _("min")
		self.l.setProgressUnit(minuteUnit if "mins" in viewType else "%")

		progressHeight = self.ItemHeight // 2 if viewMode else self.ItemHeight
		progressTextWidth = getTextBoundarySize(self.instance, self.ProgressInfoFont, self.instance.size(), "+000 %s" % minuteUnit).width() if "mins" in viewType else getTextBoundarySize(self.instance, self.ProgressInfoFont, self.instance.size(), "100 %").width()
		self.l.setProgressTextWidth(progressTextWidth)

		if "bar" in viewType:
			if viewMode and viewMode < 10:
				progressWidth = max(self.progressBarWidth, progressTextWidth)
			elif viewMode > 10:
				progressWidth = self.progressBarWidth + progressTextWidth + self.itemsDistances
			else:
				progressWidth = self.progressBarWidth
		else:
			progressWidth = progressTextWidth

		if "left" in viewType:
			self.l.setElementPosition(self.l.celServiceEventProgressbar, eRect(channelNumberWidth + channelNumberSpace, 0, progressWidth, progressHeight))
			self.l.setElementPosition(self.l.celServiceName, eRect(channelNumberWidth + channelNumberSpace + progressWidth + self.fieldMargins, 0, rowWidth - (channelNumberWidth + channelNumberSpace + progressWidth + self.fieldMargins), self.ItemHeight))
		elif "right" in viewType:
			self.l.setElementPosition(self.l.celServiceEventProgressbar, eRect(rowWidth - progressWidth, 0, progressWidth, progressHeight))
			self.l.setElementPosition(self.l.celServiceName, eRect(channelNumberWidth + channelNumberSpace, 0, rowWidth - (channelNumberWidth + channelNumberSpace + progressWidth + self.fieldMargins), self.ItemHeight))
		else:
			self.l.setElementPosition(self.l.celServiceEventProgressbar, eRect(0, 0, 0, 0))
			self.l.setElementPosition(self.l.celServiceName, eRect(channelNumberWidth + channelNumberSpace, 0, rowWidth - (channelNumberWidth + channelNumberSpace), self.ItemHeight))
		if "perc" in viewType or "mins" in viewType:
			self.l.setElementFont(self.l.celServiceEventProgressbar, self.ProgressInfoFont)

		self.l.setElementFont(self.l.celServiceName, self.ServiceNameFont)
		self.l.setElementFont(self.l.celServiceNumber, self.ServiceNumberFont)
		self.l.setElementFont(self.l.celServiceInfo, self.ServiceInfoFont)

		self.l.setHideNumberMarker(config.usage.hide_number_markers.value)
		self.l.setServiceTypeIconMode(int(config.usage.servicetype_icon_mode.value))
		self.l.setCryptoIconMode(int(config.usage.crypto_icon_mode.value))
		self.l.setRecordIndicatorMode(int(config.usage.record_indicator_mode.value))
		self.l.setColumnWidth(-1 if twoLines else int(config.usage.servicelist_column.value))

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)

	def setHideNumberMarker(self, value):
		self.l.setHideNumberMarker(value)

	def sort(self):
		self.l.sort()

	# Navigation Actions
	def goTop(self):
		self.instance.goTop()

	def goPageUp(self):
		self.instance.goPageUp()

	def goLineUp(self):
		self.instance.goLineUp()

	def goFirst(self):
		self.instance.goFirst()

	def goLeft(self):
		self.instance.goLeft()

	def goRight(self):
		self.instance.goRight()

	def goLast(self):
		self.instance.goLast()

	def goLineDown(self):
		self.instance.goLineDown()

	def goPageDown(self):
		self.instance.goPageDown()

	def goBottom(self):
		self.instance.goBottom()

	# Old method names. This methods should be found and removed from all code.
	#
	def moveUp(self):
		self.instance.goLineUp()

	def moveDown(self):
		self.instance.goLineDown()

	def moveTop(self):
		self.instance.goTop()

	def moveEnd(self):
		self.instance.goBottom()


class ServiceListLegacy(ServiceList):
	pass
