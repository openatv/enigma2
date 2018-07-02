import skin
from time import localtime, time, strftime

from enigma import eEPGCache, eListbox, eListboxPythonMultiContent, loadPNG, gFont, getDesktop, eRect, eSize, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, BT_SCALE, BT_KEEP_ASPECT_RATIO

from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend, MultiContentEntryPixmapAlphaTest
from Components.Renderer.Picon import getPiconName
from skin import parseFont
from Tools.Alternatives import CompareWithAlternatives
from Tools.LoadPixmap import LoadPixmap
from Components.config import config
from ServiceReference import ServiceReference
from Tools.ExtraAttributes import applyExtraSkinAttributes
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
from Tools.TextBoundary import getTextBoundarySize

EPG_TYPE_SINGLE = 0
EPG_TYPE_MULTI = 1
EPG_TYPE_SIMILAR = 2
EPG_TYPE_ENHANCED = 3
EPG_TYPE_INFOBAR = 4
EPG_TYPE_GRAPH = 5
EPG_TYPE_INFOBARGRAPH = 7

MAX_TIMELINES = 6

class Rect:
	def __init__(self, x, y, width, height):
		self.x = x
		self.y = y
		self.w = width
		self.h = height

	# silly, but backward compatible
	def left(self):
		return self.x

	def top(self):
		return self.y

	def height(self):
		return self.h

	def width(self):
		return self.w

def _loadPixmaps(names):
	pixmaps = []
	for name in names:
		try:
			pixmaps.append(LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, name)))
		except Exception, e:
			print "[EPGList]", e
			pixmaps.append(None)
	return pixmaps

def _loadPixmap(name):
	return _loadPixmaps((name,))[0]

def _loadPixmapsToAttrs(obj, map):
	attrNames = map.keys()
	pixmaps = _loadPixmaps(map.values())
	for (attr, pixmap) in zip(attrNames, pixmaps):
		setattr(obj, attr, pixmap)

def _makeBorder(rect, borderWidth, pixmaps):
	size = (
		(rect.w, borderWidth),					   # T/B
		(borderWidth, rect.h))					   # L/R
	pos = (
		(rect.x, rect.y), (rect.x, rect.y + rect.h - borderWidth),  # T/B
		(rect.x, rect.y), (rect.x + rect.w - borderWidth, 0))	   # L/R
	bdr = []
	for i in range(4):  # T, B, L, R
		if pixmaps and i < len(pixmaps) and pixmaps[i]:
			bdr.append(MultiContentEntryPixmapAlphaTest(
				pos=pos[i],
				size=size[i / 2],
				png=pixmaps[i],
				flags=BT_SCALE))
	return bdr

def _rectToPosSize(rect, tbBorderWidth=0, lrBorderWidth=None):
	if lrBorderWidth is None:
		lrBorderWidth = tbBorderWidth
	return {
		"pos": (rect.x + lrBorderWidth, rect.y + tbBorderWidth),
		"size": (
			max(0, rect.w - lrBorderWidth * 2),
			max(0, rect.h - tbBorderWidth * 2))
	}

class EPGList(HTMLComponent, GUIComponent):

	# Map skin attributes to class attribute names; font skin attributes
	# map to two class attributes each, font name and font size.

	attribMap = {
		# Plain strs
		"EntryFontAlignment": ("str", "eventNameAlign"),
		"EntryFontWrap": ("str", "eventNameWrap"),
		# Plain ints
		"NumberOfRows": ("int", "numberOfRows"),
		"EventBorderWidth": ("int", "eventBorderWidth"),
		"EventNamePadding": ("int", "eventNamePadding"),
		"ServiceBorderWidth": ("int", "serviceBorderWidth"),
		"ServiceNamePadding": ("int", "serviceNamePadding"),
		"ServiceNumberPadding": ("int", "serviceNumberPadding"),
		# Fonts
		"ServiceFontGraphical": ("font", "serviceFontNameGraph", "serviceFontSizeGraph"),
		"EntryFontGraphical": ("font", "eventFontNameGraph", "eventFontSizeGraph"),
		"EventFontSingle": ("font", "eventFontNameSingle", "eventFontSizeSingle"),
		"EventFontInfobar": ("font", "eventFontNameInfobar", "eventFontSizeInfobar"),
		"ServiceFontInfobar": ("font", "serviceFontNameInfobar", "serviceFontSizeInfobar"),
		# Colors
		"ServiceForegroundColor": ("color", "foreColorService"),
		"ServiceForegroundColorNow": ("color", "foreColorServiceNow"),
		"ServiceBackgroundColor": ("color", "backColorService"),
		"ServiceBackgroundColorNow": ("color", "backColorServiceNow"),

		"EntryForegroundColor": ("color", "foreColor"),
		"EntryForegroundColorSelected": ("color", "foreColorSelected"),
		"EntryForegroundColorNow": ("color", "foreColorNow"),
		"EntryForegroundColorNowSelected": ("color", "foreColorNowSelected"),
		"EntryBackgroundColor": ("color", "backColor"),
		"EntryBackgroundColorSelected": ("color", "backColorSelected"),
		"EntryBackgroundColorNow": ("color", "backColorNow"),
		"EntryBackgroundColorNowSelected": ("color", "backColorNowSelected"),
		"ServiceBorderColor": ("color", "borderColorService"),
		"EntryBorderColor": ("color", "borderColor"),
		"RecordForegroundColor": ("color", "foreColorRecord"),
		"RecordForegroundColorSelected": ("color", "foreColorRecordSelected"),
		"RecordBackgroundColor": ("color", "backColorRecord"),
		"RecordBackgroundColorSelected": ("color", "backColorRecordSelected"),
		"ZapForegroundColor": ("color", "foreColorZap"),
		"ZapBackgroundColor": ("color", "backColorZap"),
		"ZapForegroundColorSelected": ("color", "foreColorZapSelected"),
		"ZapBackgroundColorSelected": ("color", "backColorZapSelected"),
	}

	def __init__(self, type=EPG_TYPE_SINGLE, selChangedCB=None, timer=None, time_epoch=120, overjump_empty=False, graphic=False):
		self.cur_event = None
		self.cur_service = None
		self.service_set = False
		self.time_base = None
		self.time_epoch = time_epoch
		self.select_rect = None
		self.event_rect = None
		self.service_rect = None
		self.currentlyPlaying = None
		self.showPicon = False
		self.showServiceTitle = True
		self.showServiceNumber = False
		self.screenwidth = getDesktop(0).size().width()
		self.ref_event = None

		self.overjump_empty = overjump_empty
		self.timer = timer
		self.onSelChanged = []
		if selChangedCB is not None:
			self.onSelChanged.append(selChangedCB)
		GUIComponent.__init__(self)
		self.type = type
		self.graphic = graphic
		self.l = eListboxPythonMultiContent()

		if type in (EPG_TYPE_SINGLE, EPG_TYPE_ENHANCED, EPG_TYPE_INFOBAR):
			self.l.setBuildFunc(self.buildSingleEntry)
		elif type == EPG_TYPE_MULTI:
			self.l.setBuildFunc(self.buildMultiEntry)
		elif type in (EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH):
			self.l.setBuildFunc(self.buildGraphEntry)
		else:
			assert(type == EPG_TYPE_SIMILAR)
			self.l.setBuildFunc(self.buildSimilarEntry)
		self.epgcache = eEPGCache.getInstance()

		self.clocks = _loadPixmaps((
			'icons/epgclock_add.png',
			'icons/epgclock_pre.png',
			'icons/epgclock.png',
			'icons/epgclock_prepost.png',
			'icons/epgclock_post.png',
			'icons/epgclock_add.png',
			'icons/epgclock_pre.png',
			'icons/epgclock_zap.png',
			'icons/epgclock_prepost.png',
			'icons/epgclock_post.png',
			'icons/epgclock_add.png',
			'icons/epgclock_pre.png',
			'icons/epgclock_zaprec.png',
			'icons/epgclock_prepost.png',
			'icons/epgclock_post.png'
		))

		self.selclocks = _loadPixmaps((
			'icons/epgclock_add.png',
			'icons/epgclock_selpre.png',
			'icons/epgclock.png',
			'icons/epgclock_selprepost.png',
			'icons/epgclock_selpost.png',
			'icons/epgclock_add.png',
			'icons/epgclock_selpre.png',
			'icons/epgclock_zap.png',
			'icons/epgclock_selprepost.png',
			'icons/epgclock_selpost.png',
			'icons/epgclock_add.png',
			'icons/epgclock_selpre.png',
			'icons/epgclock_zaprec.png',
			'icons/epgclock_selprepost.png',
			'icons/epgclock_selpost.png'
		))

		self.autotimericon = _loadPixmap('icons/epgclock_autotimer.png')
		self.icetvicon = _loadPixmap('icons/epgclock_icetv.png')

		self.nowEvPix = None
		self.nowSelEvPix = None
		self.othEvPix = None
		self.selEvPix = None
		self.othServPix = None
		self.nowServPix = None
		self.recEvPix = None
		self.recSelEvPix = None
		self.zapEvPix = None
		self.zapSelEvPix = None

		self.borderPixmaps = None
		self.borderSelectedPixmaps = None
		self.infoPix = None
		self.selInfoPix = None
		self.graphicsloaded = False

		self.borderColor = 0xC0C0C0
		self.borderColorService = 0xC0C0C0

		self.foreColor = 0xffffff
		self.foreColorSelected = 0xffffff
		self.backColor = 0x2D455E
		self.backColorSelected = 0xd69600
		self.foreColorService = 0xffffff
		self.backColorService = 0x2D455E
		self.foreColorNow = 0xffffff
		self.foreColorNowSelected = 0xffffff
		self.backColorNow = 0x00825F
		self.backColorNowSelected = 0xd69600
		self.foreColorServiceNow = 0xffffff
		self.backColorServiceNow = 0x00825F

		self.foreColorRecord = 0xffffff
		self.backColorRecord = 0xd13333
		self.foreColorRecordSelected = 0xffffff
		self.backColorRecordSelected = 0x9e2626
		self.foreColorZap = 0xffffff
		self.backColorZap = 0x669466
		self.foreColorZapSelected = 0xffffff
		self.backColorZapSelected = 0x436143

		self.serviceFontNameGraph = "Regular"
		self.eventFontNameGraph = "Regular"
		self.eventFontNameSingle = "Regular"
		self.eventFontNameMulti = "Regular"
		self.serviceFontNameInfobar = "Regular"
		self.eventFontNameInfobar = "Regular"

		if self.screenwidth and self.screenwidth == 1920:
			self.serviceFontSizeGraph = 28
			self.eventFontSizeGraph = 28
			self.eventFontSizeSingle = 28
			self.eventFontSizeMulti = 28
			self.serviceFontSizeInfobar = 28
			self.eventFontSizeInfobar = 28
		else:
			self.serviceFontSizeGraph = 20
			self.eventFontSizeGraph = 20
			self.eventFontSizeSingle = 20
			self.eventFontSizeMulti = 20
			self.serviceFontSizeInfobar = 20
			self.eventFontSizeInfobar = 20

		self.origListHeight = self.listHeight = None
		self.origListWidth = self.listWidth = None
		self.serviceBorderWidth = 1
		self.serviceNamePadding = 3
		self.serviceNumberPadding = 9
		self.eventBorderWidth = 1
		self.eventNamePadding = 3
		self.numberOfRows = None

	# Keep old selfs.offs attribute as a do-nothing property.

	def __getOffs(self):
		return 0

	def __setOffs(self, offs):
		pass

	offs = property(__getOffs, __setOffs)

	def applySkin(self, desktop, screen):
		self.skinAttributes = applyExtraSkinAttributes(self, self.skinAttributes, self.attribMap)
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.origListHeight = self.listHeight = self.instance.size().height()
		self.origListWidth = self.listWidth = self.instance.size().width()
		self.setItemsPerPage()
		self.setFontsize()
		return rc

	def getCurrentChangeCount(self):
		if self.type == EPG_TYPE_MULTI and self.l.getCurrentSelection() is not None:
			return self.l.getCurrentSelection()[0]
		return 0

	def isSelectable(self, service, service_name, events, picon, channel):
		return (events and len(events) and True) or False

	def setShowServiceMode(self, value):
		self.showServiceNumber = "servicenumber" in value
		self.showServiceTitle = "servicename" in value
		self.showPicon = "picon" in value
		self.recalcEntrySize()
		self.selEntry(0)  # Select entry again so that the clipping region gets updated if needed

	def setOverjump_Empty(self, overjump_empty):
		if overjump_empty:
			self.l.setSelectableFunc(self.isSelectable)
		else:
			self.l.setSelectableFunc(None)

	def setEpoch(self, epoch):
		self.time_epoch = epoch
		self.fillGraphEPG(None)

	def setCurrentlyPlaying(self, serviceref):
		self.currentlyPlaying = serviceref

	def getEventFromId(self, service, eventid):
		event = None
		if self.epgcache is not None and eventid is not None:
			event = self.epgcache.lookupEventId(service.ref, eventid)
		return event

	def getIndexFromService(self, serviceref):
		if serviceref is not None:
			for x in range(len(self.list)):
				if str(self.list[x][0]).startswith('1:'):  # check for Graphical EPG
					if CompareWithAlternatives(self.list[x][0], serviceref.toString()):
						return x
				elif str(self.list[x][1]).startswith('1:'):  # check for Multi EPG
					if CompareWithAlternatives(self.list[x][1], serviceref.toString()):
						return x
		return None

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def moveToService(self, serviceref):
		if not serviceref:
			return
		newIdx = self.getIndexFromService(serviceref)
		if newIdx is None:
			newIdx = 0
		self.setCurrentIndex(newIdx)
		self.service_set = True
		if self.type in (EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH):
			self.findBestEvent()

	def setCurrentIndex(self, index):
		if self.instance is not None:
			self.instance.moveSelectionTo(index)

	def moveTo(self, dir):
		if self.instance is not None:
			self.instance.moveSelection(dir)

	def getCurrent(self):
		if self.type in (EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH):
			if self.cur_service is None:
				return None, None
			(refstr, service_name, events, picon, channel) = self.cur_service
			if self.cur_event is None or not events or (self.cur_event and events and self.cur_event > len(events) - 1):
				return None, ServiceReference(refstr)
			event = events[self.cur_event]  # (event_id, event_title, begin_time, duration)
			eventid = event[0]
			service = ServiceReference(refstr)
			event = self.getEventFromId(service, eventid)  # get full event info
			return event, service
		else:
			idx = 0
			if self.type == EPG_TYPE_MULTI:
				idx += 1
			tmp = self.l.getCurrentSelection()
			if tmp is None:
				return None, None
			eventid = tmp[idx + 1]
			service = ServiceReference(tmp[idx])
			event = self.getEventFromId(service, eventid)
			return event, service

	def connectSelectionChanged(self, func):
		if not self.onSelChanged.count(func):
			self.onSelChanged.append(func)

	def disconnectSelectionChanged(self, func):
		self.onSelChanged.remove(func)

	def serviceChanged(self):
		cur_sel = self.l.getCurrentSelection()
		if cur_sel:
			self.findBestEvent()

	# clip a time to those visible in the EPG, and round to minutes by truncation
	def clipRoundTimeToVisible(self, time):
		time_base = self.getTimeBase()
		ev_min = time_base
		ev_max = time_base + self.time_epoch * 60
		return max(ev_min, min(ev_max, time - (time % 60)))

	def findBestEvent(self):
		if not self.service_set:
			return
		old_service = self.cur_service  # (service, service_name, events, picon, channel)
		cur_service = self.cur_service = self.l.getCurrentSelection()
		if self.ref_event is not None:
			# Use the visible portion of the reference event time range, at least a minute and up to 10% of the whole EPG visible time range
			last_time = self.clipRoundTimeToVisible(self.ref_event[2])
			last_end_time = self.clipRoundTimeToVisible(self.ref_event[2] + self.ref_event[3])
			last_end_time = max(last_time + 60, min(last_end_time, self.clipRoundTimeToVisible(last_time + self.time_epoch * 60 / 10)))
		else:
			last_time = time()
			last_time = last_end_time = last_time - (last_time % 60)
		if cur_service:
			self.cur_event = 0
			events = cur_service[2]
			best = None
			if events and len(events):
				best_diff = 0
				idx = 0
				for event in events:  # iterate all events
					ev_time = self.clipRoundTimeToVisible(event[2])
					ev_end_time = self.clipRoundTimeToVisible(event[2] + event[3])
					if not old_service and ev_time <= last_time < ev_end_time:
						best = idx
						break
					# If there's a reference event look for the largest overlap with its range, otherwise look for the event containing current time or is the closest to it
					if self.ref_event is not None:
						diff = min(ev_end_time, last_end_time) - max(ev_time, last_time)
						better = diff > best_diff
					else:
						diff = 0 if ev_time <= last_time < ev_end_time else min(abs(ev_time - last_time), abs(ev_end_time - last_time))
						better = diff < best_diff
					if best is None or better:
						best = idx
						best_diff = diff
					if best is not None and ev_time > last_end_time:
						break
					idx += 1
			self.cur_event = best
		self.selEntry(0)

	def selectionChanged(self):
		for x in self.onSelChanged:
			if x is not None:
				x()

	GUI_WIDGET = eListbox

	def setItemsPerPage(self):
		if self.type in (EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH):
			if self.type == EPG_TYPE_GRAPH:
				if self.origListHeight > 0:
					itemHeight = self.origListHeight / config.epgselection.graph_itemsperpage.value
				else:
					itemHeight = 54  # some default (270/5)
				if config.epgselection.graph_heightswitch.value:
					if ((self.origListHeight / config.epgselection.graph_itemsperpage.value) / 3) >= 27:
						tmp_itemHeight = ((self.origListHeight / config.epgselection.graph_itemsperpage.value) / 3)
					elif ((self.origListHeight / config.epgselection.graph_itemsperpage.value) / 2) >= 27:
						tmp_itemHeight = ((self.origListHeight / config.epgselection.graph_itemsperpage.value) / 2)
					else:
						tmp_itemHeight = 27
					if tmp_itemHeight < itemHeight:
						itemHeight = tmp_itemHeight
					else:
						if ((self.origListHeight / config.epgselection.graph_itemsperpage.value) * 3) <= 45:
							itemHeight = ((self.origListHeight / config.epgselection.graph_itemsperpage.value) * 3)
						elif ((self.origListHeight / config.epgselection.graph_itemsperpage.value) * 2) <= 45:
							itemHeight = ((self.origListHeight / config.epgselection.graph_itemsperpage.value) * 2)
						else:
							itemHeight = 45
				if self.numberOfRows:
					config.epgselection.graph_itemsperpage.default = self.numberOfRows
			elif self.type == EPG_TYPE_INFOBARGRAPH:
				if self.numberOfRows:
					config.epgselection.infobar_itemsperpage.default = self.numberOfRows
				if self.origListHeight > 0:
					itemHeight = self.origListHeight / config.epgselection.infobar_itemsperpage.value
				else:
					itemHeight = 54  # some default (270/5)
			self.l.setItemHeight(itemHeight)
			self.instance.resize(eSize(self.listWidth, self.origListHeight / itemHeight * itemHeight))
			self.listHeight = self.instance.size().height()
			self.listWidth = self.instance.size().width()
			self.itemHeight = itemHeight

		elif self.type in (EPG_TYPE_ENHANCED, EPG_TYPE_SINGLE, EPG_TYPE_SIMILAR):
			if self.numberOfRows:
				config.epgselection.enhanced_itemsperpage.default = self.numberOfRows
			if self.listHeight > 0:
				itemHeight = self.listHeight / config.epgselection.enhanced_itemsperpage.value
			else:
				itemHeight = 32
			if itemHeight < 20:
				itemHeight = 20
			self.l.setItemHeight(itemHeight)
			self.instance.resize(eSize(self.listWidth, self.listHeight / itemHeight * itemHeight))
			self.listHeight = self.instance.size().height()
			self.listWidth = self.instance.size().width()
			self.itemHeight = itemHeight
		elif self.type == EPG_TYPE_MULTI:
			if self.numberOfRows:
				config.epgselection.multi_itemsperpage.default = self.numberOfRows
			if self.listHeight > 0:
				itemHeight = self.listHeight / config.epgselection.multi_itemsperpage.value
			else:
				itemHeight = 32
			if itemHeight < 20:
				itemHeight = 20
			self.l.setItemHeight(itemHeight)
			self.instance.resize(eSize(self.listWidth, self.listHeight / itemHeight * itemHeight))
			self.listHeight = self.instance.size().height()
			self.listWidth = self.instance.size().width()
			self.itemHeight = itemHeight
		elif self.type == EPG_TYPE_INFOBAR:
			if self.numberOfRows:
				config.epgselection.infobar_itemsperpage.default = self.numberOfRows
			if self.listHeight > 0:
				itemHeight = self.listHeight / config.epgselection.infobar_itemsperpage.value
			else:
				itemHeight = 32
			if itemHeight < 20:
				itemHeight = 20
			self.l.setItemHeight(int(itemHeight))
			self.instance.resize(eSize(self.listWidth, self.listHeight / itemHeight * itemHeight))
			self.listHeight = self.instance.size().height()
			self.listWidth = self.instance.size().width()
			self.itemHeight = itemHeight

	def setFontsize(self):
		if self.type == EPG_TYPE_GRAPH:
			self.l.setFont(0, gFont(self.serviceFontNameGraph, self.serviceFontSizeGraph + config.epgselection.graph_servfs.value))
			self.l.setFont(1, gFont(self.eventFontNameGraph, self.eventFontSizeGraph + config.epgselection.graph_eventfs.value))
		elif self.type in (EPG_TYPE_ENHANCED, EPG_TYPE_SINGLE, EPG_TYPE_SIMILAR):
			self.l.setFont(0, gFont(self.eventFontNameSingle, self.eventFontSizeSingle + config.epgselection.enhanced_eventfs.value))
		elif self.type == EPG_TYPE_MULTI:
			self.l.setFont(0, gFont(self.eventFontNameMulti, self.eventFontSizeMulti + config.epgselection.multi_eventfs.value))
			self.l.setFont(1, gFont(self.eventFontNameMulti, self.eventFontSizeMulti - 4 + config.epgselection.multi_eventfs.value))
		elif self.type == EPG_TYPE_INFOBAR:
			self.l.setFont(0, gFont(self.eventFontNameInfobar, self.eventFontSizeInfobar + config.epgselection.infobar_eventfs.value))
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			self.l.setFont(0, gFont(self.serviceFontNameInfobar, self.serviceFontSizeInfobar + config.epgselection.infobar_servfs.value))
			self.l.setFont(1, gFont(self.eventFontNameInfobar, self.eventFontSizeInfobar + config.epgselection.infobar_eventfs.value))

	def postWidgetCreate(self, instance):
		if self.type in (EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH):
			self.setOverjump_Empty(self.overjump_empty)
			instance.setWrapAround(True)
			instance.selectionChanged.get().append(self.serviceChanged)
			instance.setContent(self.l)
			self.l.setSelectionClip(eRect(0, 0, 0, 0), False)
		else:
			instance.setWrapAround(self.type == EPG_TYPE_ENHANCED)
			instance.selectionChanged.get().append(self.selectionChanged)
			instance.setContent(self.l)

	def preWidgetRemove(self, instance):
		if self.type in (EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH):
			instance.selectionChanged.get().remove(self.serviceChanged)
			instance.setContent(None)
		else:
			instance.selectionChanged.get().remove(self.selectionChanged)
			instance.setContent(None)

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)

	def recalcEntrySize(self):
		esize = self.l.getItemSize()
		width = esize.width()
		height = esize.height()
		if self.type == EPG_TYPE_MULTI:
			fontSize = self.eventFontSizeMulti + config.epgselection.multi_eventfs.value
			servScale, timeScale, durScale, wideScale = skin.parameters.get("EPGMultiColumnScales", (6.5, 6.0, 4.5, 1.5))
			# servW = int((fontSize + 4) * servScale)  # Service font is 4 px larger
			servW = int(fontSize * servScale)
			timeW = int(fontSize * timeScale)
			durW = int(fontSize * durScale)
			left, servWidth, sepWidth, timeWidth, progHeight, breakWidth, durWidth, gapWidth = skin.parameters.get("EPGMultiColumnSpecs", (0, servW, 10, timeW, height - 12, 10, durW, 10))
			if config.usage.time.wide.value:
				timeWidth = int(timeWidth * wideScale)
			self.service_rect = Rect(left, 0, servWidth, height)
			left += servWidth + sepWidth
			self.start_end_rect = Rect(left, 0, timeWidth, height)
			progTop = int((height - progHeight) / 2)
			self.progress_rect = Rect(left, progTop, timeWidth, progHeight)
			left += timeWidth + breakWidth
			self.duration_rect = Rect(left, 0, durWidth, height)
			left += durWidth + gapWidth
			self.descr_rect = Rect(left, 0, width - left, height)
		elif self.type in (EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH):
			servicew = 0
			piconw = 0
			channelw = 0
			if self.type == EPG_TYPE_GRAPH:
				if self.showServiceTitle:
					servicew = config.epgselection.graph_servicewidth.value
				if self.showPicon:
					piconw = config.epgselection.graph_piconwidth.value
				if self.showServiceNumber:
					font = gFont(self.serviceFontNameGraph, self.serviceFontSizeGraph + config.epgselection.graph_servfs.value)
					channelw = getTextBoundarySize(self.instance, font, self.instance.size(), "0000" ).width()
			elif self.type == EPG_TYPE_INFOBARGRAPH:
				if self.showServiceTitle:
					servicew = config.epgselection.infobar_servicewidth.value
				if self.showPicon:
					piconw = config.epgselection.infobar_piconwidth.value
				if self.showServiceNumber:
					font = gFont(self.serviceFontNameGraph, self.serviceFontSizeGraph + config.epgselection.infobar_servfs.value)
					channelw = getTextBoundarySize(self.instance, font, self.instance.size(), "0000" ).width()
			w = (channelw + piconw + servicew)
			self.service_rect = Rect(0, 0, w, height)
			self.event_rect = Rect(w, 0, width - w, height)
			piconHeight = height - 2 * self.serviceBorderWidth
			piconWidth = piconw
			if piconWidth > w - 2 * self.serviceBorderWidth:
				piconWidth = w - 2 * self.serviceBorderWidth
			self.picon_size = eSize(piconWidth, piconHeight)
		else:
			fontSize = self.eventFontSizeSingle + config.epgselection.enhanced_eventfs.value
			dateScale, timesScale, wideScale = skin.parameters.get("EPGSingleColumnScales", (5.7, 6.0, 1.5))
			dateW = int(fontSize * dateScale)
			timesW = int(fontSize * timesScale)
			left, dateWidth, sepWidth, timesWidth, breakWidth = skin.parameters.get("EPGSingleColumnSpecs", (0, dateW, 5, timesW, 20))
			if config.usage.time.wide.value:
				timesWidth = int(timesWidth * wideScale)
			self.weekday_rect = Rect(left, 0, dateWidth, height)
			left += dateWidth + sepWidth
			self.datetime_rect = Rect(left, 0, timesWidth, height)
			left += timesWidth + breakWidth
			self.descr_rect = Rect(left, 0, width - left, height)
			self.showend = True  # This is not an unused variable. It is a flag used by EPGSearch plugin

	def calcEntryPosAndWidthHelper(self, stime, duration, start, end, width):
		xpos = (stime - start) * width / (end - start)
		ewidth = (stime + duration - start) * width / (end - start)
		ewidth -= xpos
		if xpos < 0:
			ewidth += xpos
			xpos = 0
		if (xpos + ewidth) > width:
			ewidth = width - xpos
		return xpos, ewidth

	def calcEntryPosAndWidth(self, event_rect, time_base, time_epoch, ev_start, ev_duration):
		xpos, width = self.calcEntryPosAndWidthHelper(ev_start, ev_duration, time_base, time_base + time_epoch * 60, event_rect.w)
		return xpos + event_rect.x, width

	def getPixmapForEntry(self, service, eventId, beginTime, duration):
		if not beginTime:
			return None
		rec = self.timer.isInTimer(eventId, beginTime, duration, service)
		if rec is not None:
			self.wasEntryAutoTimer = bool(rec[2] & 1)
			self.wasEntryIceTV = bool(rec[2] & 2)
			return rec[1]
		else:
			self.wasEntryAutoTimer = False
			self.wasEntryIceTV = False
			return None

	def buildSingleEntry(self, service, eventId, beginTime, duration, EventName):
		clock_types = self.getPixmapForEntry(service, eventId, beginTime, duration)
		r1 = self.weekday_rect
		r2 = self.datetime_rect
		r3 = self.descr_rect
		split = int(r2.w * 0.55)
		t = localtime(beginTime)
		et = localtime(beginTime + duration)
		res = [
			None,  # no private data needed
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, strftime(config.usage.date.dayshort.value, t)),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, split, r2.h, 0, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, strftime(config.usage.time.short.value + " -", t)),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x + split, r2.y, r2.w - split, r2.h, 0, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, strftime(config.usage.time.short.value, et))
		]
		if clock_types:
			if (self.wasEntryAutoTimer or self.wasEntryIceTV) and clock_types in (2, 7, 12):
				if self.screenwidth and self.screenwidth == 1920:
					iconOffset = 25
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - iconOffset, (r3.h / 2 - 13), 25, 25, self.clocks[clock_types]))
					if self.wasEntryAutoTimer:
						iconOffset += 27
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - iconOffset, (r3.h / 2 - 13), 25, 25, self.autotimericon))
					if self.wasEntryIceTV:
						iconOffset += 27
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - iconOffset, (r3.h / 2 - 13), 25, 25, self.icetvicon))
					res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w - 52, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, EventName))
				else:
					iconOffset = 21
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - iconOffset, (r3.h / 2 - 11), 21, 21, self.clocks[clock_types]))
					if self.wasEntryAutoTimer:
						iconOffset += 21
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - iconOffset, (r3.h / 2 - 11), 21, 21, self.autotimericon))
					if self.wasEntryIceTV:
						iconOffset += 21
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - iconOffset, (r3.h / 2 - 11), 21, 21, self.icetvicon))
					res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w - iconOffset, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, EventName))
			else:
				if self.screenwidth and self.screenwidth == 1920:
					res.extend((
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - 25, (r3.h / 2 - 13), 25, 25, self.clocks[clock_types]),
						(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w - 25, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, EventName)
					))
				else:
					res.extend((
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - 21, (r3.h / 2 - 11), 21, 21, self.clocks[clock_types]),
						(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w - 21, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, EventName)
					))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, EventName))
		return res

	def buildSimilarEntry(self, service, eventId, beginTime, service_name, duration):
		clock_types = self.getPixmapForEntry(service, eventId, beginTime, duration)
		r1 = self.weekday_rect
		r2 = self.datetime_rect
		r3 = self.descr_rect
		split = int(r2.w * 0.55)
		t = localtime(beginTime)
		et = localtime(beginTime + duration)
		res = [
			None,  # no private data needed
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, strftime(config.usage.date.dayshort.value, t)),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, split, r2.h, 0, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, strftime(config.usage.time.short.value + " -", t)),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x + split, r2.y, r2.w - split, r2.h, 0, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, strftime(config.usage.time.short.value, et))
		]
		if clock_types:
			if (self.wasEntryAutoTimer or self.wasEntryIceTV) and clock_types in (2, 7, 12):
				if self.screenwidth and self.screenwidth == 1920:
					iconOffset = 25
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - iconOffset, (r3.h / 2 - 13), 25, 25, self.clocks[clock_types]))
					if self.wasEntryAutoTimer:
						iconOffset += 27
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - iconOffset, (r3.h / 2 - 13), 25, 25, self.autotimericon))
					if self.wasEntryIceTV:
						iconOffset += 27
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - iconOffset, (r3.h / 2 - 13), 25, 25, self.icetvicon))
					res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w - iconOffset, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, service_name))
				else:
					iconOffset = 21
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - iconOffset, (r3.h / 2 - 11), 21, 21, self.clocks[clock_types]))
					if self.wasEntryAutoTimer:
						iconOffset += 21
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - iconOffset, (r3.h / 2 - 11), 21, 21, self.autotimericon))
					if self.wasEntryIceTV:
						iconOffset += 21
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - iconOffset, (r3.h / 2 - 11), 21, 21, self.icetvicon))
					res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w - iconOffset, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, service_name))
			else:
				if self.screenwidth and self.screenwidth == 1920:
					res.extend((
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - 25, (r3.h / 2 - 13), 25, 25, self.clocks[clock_types]),
						(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w - 25, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, service_name)
					))
				else:
					res.extend((
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x + r3.w - 21, (r3.h / 2 - 11), 21, 21, self.clocks[clock_types]),
						(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w - 21, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, service_name)
					))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, service_name))
		return res

	def buildMultiEntry(self, changecount, service, eventId, beginTime, duration, EventName, nowTime, service_name):
		r1 = self.service_rect
		r2 = self.start_end_rect
		r3 = self.progress_rect
		r4 = self.duration_rect
		r5 = self.descr_rect
		res = [
			None,  # no private data needed
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, service_name)
		]
		if beginTime is not None:
			fontSize = self.eventFontSizeMulti + config.epgselection.multi_eventfs.value
			if nowTime < beginTime:
				begin = localtime(beginTime)
				end = localtime(beginTime + duration)
				split = int(r2.w * 0.55)
				res.extend((
					(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, split, r2.h, 0, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, strftime(config.usage.time.short.value + " - ", begin)),
					(eListboxPythonMultiContent.TYPE_TEXT, r2.x + split, r2.y, r2.w - split, r2.h, 0, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, strftime(config.usage.time.short.value, end))
				))
				remaining = duration / 60
				prefix = ""
			else:
				percent = (nowTime - beginTime) * 100 / duration
				remaining = ((beginTime + duration) - int(time())) / 60
				if remaining <= 0:
					prefix = ""
				else:
					prefix = "+"
				res.append((eListboxPythonMultiContent.TYPE_PROGRESS, r3.x, r3.y, r3.w, r3.h, percent))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r4.x, r4.y, r4.w, r4.h, 0, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, _("%s%d Min") % (prefix, remaining)))
			width = r5.w
			clock_types = self.getPixmapForEntry(service, eventId, beginTime, duration)
			if clock_types:
				clk_sz = 25 if self.screenwidth and self.screenwidth == 1920 else 21
				width -= clk_sz / 2 if clock_types in (1, 6, 11) else clk_sz
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r5.x + width, (r5.h - clk_sz) / 2, clk_sz, clk_sz, self.clocks[clock_types]))
				if (self.wasEntryAutoTimer or self.wasEntryIceTV) and clock_types in (2, 7, 12):
					width -= clk_sz + 1
					if self.wasEntryAutoTimer:
						icon = self.autotimericon
					else:
						icon = self.icetvicon
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r5.x + width, (r5.h - clk_sz) / 2, clk_sz, clk_sz, icon))
				width -= 5
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r5.x, r5.y, width, r5.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, EventName))
		return res

	def buildGraphEntry(self, service, service_name, events, picon, channel):
		r1 = self.service_rect
		r2 = self.event_rect
		left = r2.x
		top = r2.y
		width = r2.w
		height = r2.h
		selected = (self.cur_service is not None) and (self.cur_service[0] == service)
		res = [None]

		borderPixmaps = None

		# Picon and Service name
		serviceForeColor = self.foreColorService
		serviceBackColor = self.backColorService
		bgpng = self.othServPix
		if CompareWithAlternatives(service, self.currentlyPlaying and self.currentlyPlaying.toString()):
			serviceForeColor = self.foreColorServiceNow
			serviceBackColor = self.backColorServiceNow
			bgpng = self.nowServPix

		if bgpng is not None and self.graphic:
			serviceBackColor = None
			res.append(MultiContentEntryPixmapAlphaBlend(
				png=bgpng,
				flags=BT_SCALE,
				**_rectToPosSize(r1, self.serviceBorderWidth)))
		else:
			res.append(MultiContentEntryText(
				pos=(r1.x, r1.y),
				size=(r1.w, r1.h),
				font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				text="",
				color=serviceForeColor, color_sel=serviceForeColor,
				backcolor=serviceBackColor, backcolor_sel=serviceBackColor,
				border_width=self.serviceBorderWidth, border_color=self.borderColorService))

		displayPicon = None
		if self.showPicon:
			if picon is None:  # go find picon and cache its location
				picon = getPiconName(service)
				curIdx = self.l.getCurrentSelectionIndex()
				self.list[curIdx] = (service, service_name, events, picon, channel)
			piconWidth = self.picon_size.width()
			piconHeight = self.picon_size.height()
			if picon != "":
				displayPicon = loadPNG(picon)
			if displayPicon is not None:
				res.append(MultiContentEntryPixmapAlphaBlend(
					pos=(r1.x + self.serviceBorderWidth, r1.y + self.serviceBorderWidth),
					size=(piconWidth, piconHeight),
					png=displayPicon,
					backcolor=None, backcolor_sel=None, flags=BT_SCALE | BT_KEEP_ASPECT_RATIO))
			elif not self.showServiceTitle:
				# no picon so show servicename anyway in picon space
				namefont = 1
				namefontflag = int(config.epgselection.graph_servicename_alignment.value)
				namewidth = piconWidth
			else:
				piconWidth = 0
		else:
			piconWidth = 0

		channelWidth = 0
		if self.showServiceNumber:
			if not isinstance(channel, int):
				channel = self.getChannelNumber(channel)
			
			if channel:
				namefont = 0
				namefontflag = int(config.epgselection.graph_servicenumber_alignment.value)
				font = gFont(self.serviceFontNameGraph, self.serviceFontSizeGraph + config.epgselection.graph_servfs.value)
				channelWidth = getTextBoundarySize(self.instance, font, self.instance.size(), (channel < 10000)  and "0000" or str(channel) ).width()
				res.append(MultiContentEntryText(
					pos = (r1.x + self.serviceNamePadding + piconWidth + self.serviceNamePadding, r1.y + self.serviceBorderWidth),
					size = (channelWidth, r1.h - 2 * self.serviceBorderWidth),
					font = namefont, flags = namefontflag,
					text = str(channel),
					color = serviceForeColor, color_sel = serviceForeColor,
					backcolor = serviceBackColor, backcolor_sel = serviceBackColor))

		if self.showServiceTitle:  # we have more space so reset parms
			namefont = 0
			namefontflag = int(config.epgselection.graph_servicename_alignment.value)
			namewidth = r1.w - channelWidth - piconWidth

		if self.showServiceTitle or displayPicon is None:
			res.append(MultiContentEntryText(
				pos = (r1.x + self.serviceNamePadding + piconWidth + self.serviceNamePadding + channelWidth + self.serviceNumberPadding,
					r1.y + self.serviceBorderWidth),
				size = (namewidth - 3 * (self.serviceBorderWidth + self.serviceNamePadding),
					r1.h - 2 * self.serviceBorderWidth),
				font = namefont, flags = namefontflag,
				text = service_name,
				color = serviceForeColor, color_sel = serviceForeColor,
				backcolor = serviceBackColor, backcolor_sel = serviceBackColor))

		# Service Borders
		if self.graphic:
			res += _makeBorder(r1, self.serviceBorderWidth, self.borderPixmaps)
			res += _makeBorder(r2, self.eventBorderWidth, self.borderPixmaps)

		if self.graphic:
			if selected and not events and self.selEvPix:
				res.append(MultiContentEntryPixmapAlphaTest(
					png=self.selEvPix,
					flags=BT_SCALE,
					**_rectToPosSize(r2, self.eventBorderWidth)))
			elif self.othEvPix:
				res.append(MultiContentEntryPixmapAlphaTest(
					png=self.othEvPix,
					flags=BT_SCALE,
					**_rectToPosSize(r2, self.eventBorderWidth)))
		else:
			res.append(MultiContentEntryText(
				pos=(left, top), size=(width, height),
				font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				text="", color=None, color_sel=None,
				backcolor=self.backColor, backcolor_sel=self.backColorSelected,
				border_width=self.eventBorderWidth, border_color=self.borderColor))

		# Events for service
		if events:
			start = self.getTimeBase()
			end = start + self.time_epoch * 60

			now = time()
			for ev in events:  # (event_id, event_title, begin_time, duration)
				stime = ev[2]
				duration = ev[3]
				xpos, ewidth = self.calcEntryPosAndWidthHelper(stime, duration, start, end, width)
				evRect = Rect(left + xpos, top, ewidth, height)
				clock_types = self.getPixmapForEntry(service, ev[0], stime, duration)

				foreColor = self.foreColor
				backColor = self.backColor
				foreColorSel = self.foreColorSelected
				backColorSel = self.backColorSelected
				if clock_types is not None and clock_types in (2, 12):
					foreColor = self.foreColorRecord
					backColor = self.backColorRecord
					foreColorSel = self.foreColorRecordSelected
					backColorSel = self.backColorRecordSelected
				elif clock_types is not None and clock_types == 7:
					foreColor = self.foreColorZap
					backColor = self.backColorZap
					foreColorSel = self.foreColorZapSelected
					backColorSel = self.backColorZapSelected
				elif stime <= now < (stime + duration) and config.epgselection.graph_highlight_current_events.value:
					foreColor = self.foreColorNow
					backColor = self.backColorNow
					foreColorSel = self.foreColorNowSelected
					backColorSel = self.backColorNowSelected

				if selected and self.select_rect.x == xpos + left:
					if clock_types is not None:
						clocks = self.selclocks[clock_types]
					borderPixmaps = self.borderSelectedPixmaps
					infoPix = self.selInfoPix
					bgpng = self.selEvPix
					if clock_types is not None and clock_types in (2, 12):
						bgpng = self.recSelEvPix
					elif clock_types is not None and clock_types == 7:
						bgpng = self.zapSelEvPix
					elif stime <= now < (stime + duration) and config.epgselection.graph_highlight_current_events.value:
						bgpng = self.nowSelEvPix
				else:
					if clock_types is not None:
						clocks = self.clocks[clock_types]
					borderPixmaps = self.borderPixmaps
					infoPix = self.infoPix
					bgpng = self.othEvPix
					if clock_types is not None and clock_types in (2, 12):
						bgpng = self.recEvPix
					elif clock_types is not None and clock_types == 7:
						bgpng = self.zapEvPix
					elif stime <= now < (stime + duration) and config.epgselection.graph_highlight_current_events.value:
						bgpng = self.nowEvPix

				# event box background
				if bgpng is not None and self.graphic:
					backColor = None
					backColorSel = None
					res.append(MultiContentEntryPixmapAlphaTest(
						png=bgpng,
						flags=BT_SCALE,
						**_rectToPosSize(evRect, self.eventBorderWidth)))
				else:
					res.append(MultiContentEntryText(
						font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
						text="", color=None, color_sel=None,
						backcolor=backColor, backcolor_sel=backColorSel,
						border_width=self.eventBorderWidth, border_color=self.borderColor,
						**_rectToPosSize(evRect, 0)))

				# event text
				evSizePos = _rectToPosSize(evRect, self.eventBorderWidth, self.eventBorderWidth + self.eventNamePadding)

				if self.type == EPG_TYPE_GRAPH:
					infowidth = config.epgselection.graph_infowidth.value
				elif self.type == EPG_TYPE_INFOBARGRAPH:
					infowidth = config.epgselection.infobar_infowidth.value
				if evSizePos["size"][0] < infowidth and infoPix is not None:
					res.append(MultiContentEntryPixmapAlphaBlend(
						png=infoPix,
						**evSizePos))
				else:
					res.append(MultiContentEntryText(
						font=1, flags=int(config.epgselection.graph_event_alignment.value),
						text=ev[1],
						color=foreColor, color_sel=foreColorSel,
						backcolor=backColor, backcolor_sel=backColorSel,
						**evSizePos))

				# event box borders
				res += _makeBorder(evRect, self.eventBorderWidth, borderPixmaps)

				# recording icons
				if clock_types is not None and ewidth > 23 and config.epgselection.graph_rec_icon_height.value != "hide":
					if config.epgselection.graph_rec_icon_height.value == "middle":
						RecIconHDheight = top+(height/2)-11
						RecIconFHDheight = top+(height/2)-13
					elif config.epgselection.graph_rec_icon_height.value == "top":
						RecIconHDheight = top+3
						RecIconFHDheight = top+3
					else:
						RecIconHDheight = top+height-22
						RecIconFHDheight = top+height-26
					if clock_types in (1, 6, 11):
						if self.screenwidth and self.screenwidth == 1920:
							pos = (left+xpos+ewidth-15, RecIconFHDheight)
						else:
							pos = (left+xpos+ewidth-13, RecIconHDheight)
					elif clock_types in (5, 10, 15):
						if self.screenwidth and self.screenwidth == 1920:
							pos = (left+xpos-26, RecIconFHDheight)
						else:
							pos = (left+xpos-22, RecIconHDheight)
					else:
						if self.screenwidth and self.screenwidth == 1920:
							pos = (left+xpos+ewidth-26, RecIconFHDheight)
						else:
							pos = (left+xpos+ewidth-22, RecIconHDheight)
					if self.screenwidth and self.screenwidth == 1920:
						res.append(MultiContentEntryPixmapAlphaBlend(
							pos=pos, size=(25, 25),
							png=clocks))
					else:
						res.append(MultiContentEntryPixmapAlphaBlend(
							pos=pos, size=(21, 21),
							png=clocks))
					if (self.wasEntryAutoTimer or self.wasEntryIceTV) and clock_types in (2, 7, 12):
						if self.screenwidth and self.screenwidth == 1920:
							iconOffset = 0
							if self.wasEntryAutoTimer:
								iconOffset += 29
								res.append(MultiContentEntryPixmapAlphaBlend(
									pos=(pos[0] - iconOffset, pos[1]), size=(25, 25),
									png=self.autotimericon))
							if self.wasEntryIceTV:
								iconOffset += 29
								res.append(MultiContentEntryPixmapAlphaBlend(
									pos=(pos[0] - iconOffset, pos[1]), size=(25, 25),
									png=self.icetvicon))
						else:
							iconOffset = 0
							if self.wasEntryAutoTimer:
								iconOffset += 22
								res.append(MultiContentEntryPixmapAlphaBlend(
									pos=(pos[0] - iconOffset, pos[1]), size=(21, 21),
									png=self.autotimericon))
							if self.wasEntryIceTV:
								iconOffset += 22
								res.append(MultiContentEntryPixmapAlphaBlend(
									pos=(pos[0] - iconOffset, pos[1]), size=(21, 21),
									png=self.icetvicon))
		return res

	def getSelectionPosition(self, serviceref):
		if self.type == EPG_TYPE_GRAPH:
			indx = self.getIndexFromService(serviceref) or 0
			selx = self.select_rect.x + self.select_rect.w
			while indx + 1 > config.epgselection.graph_itemsperpage.value:
				indx = indx - config.epgselection.graph_itemsperpage.value
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			indx = self.getIndexFromService(serviceref) or 0
			selx = self.select_rect.x + self.select_rect.w
			while indx + 1 > config.epgselection.infobar_itemsperpage.value:
				indx = indx - config.epgselection.infobar_itemsperpage.value
		elif self.type in (EPG_TYPE_ENHANCED, EPG_TYPE_SINGLE, EPG_TYPE_SIMILAR):
			indx = self.l.getCurrentSelectionIndex()
			selx = self.listWidth
			while indx + 1 > config.epgselection.enhanced_itemsperpage.value:
				indx = indx - config.epgselection.enhanced_itemsperpage.value
		elif self.type == EPG_TYPE_MULTI:
			indx = self.l.getCurrentSelectionIndex()
			selx = self.listWidth
			while indx + 1 > config.epgselection.multi_itemsperpage.value:
				indx = indx - config.epgselection.multi_itemsperpage.value
		elif self.type == EPG_TYPE_INFOBAR:
			indx = self.l.getCurrentSelectionIndex()
			selx = self.listWidth
			while indx + 1 > config.epgselection.infobar_itemsperpage.value:
				indx = indx - config.epgselection.infobar_itemsperpage.value
		pos = self.instance.position().y()
		sely = int(pos) + (int(self.itemHeight) * int(indx))
		temp = int(self.instance.position().y()) + int(self.listHeight)
		if int(sely) >= temp:
			sely = int(sely) - int(self.listHeight)
		return int(selx), int(sely)

	def selEntry(self, dir, visible=True):

		def newBaseTime(newBase):
			now = time() - int(config.epg.histminutes.value) * 60
			roundTo = int(config.epgselection.infobar_roundto.value) if self.type == EPG_TYPE_INFOBARGRAPH else int(config.epgselection.graph_roundto.value)
			return int(max(newBase, now - now % (roundTo * 60)))

		if not self.service_set:
			return
		cur_service = self.cur_service  # (service, service_name, events, picon, channel)
		self.recalcEntrySize()
		valid_event = self.cur_event is not None
		if cur_service:
			update = True
			check_ref_event = False
			entries = cur_service[2]
			if dir == 0:  # current
				update = False
			elif dir == +1:  # next
				if valid_event and self.cur_event + 1 < len(entries):
					self.cur_event += 1
					check_ref_event = True
				else:
					self.time_base += self.time_epoch * 60
					self.fillGraphEPG(None)  # refill
					return True
			elif dir == -1:  # prev
				if valid_event and self.cur_event - 1 >= 0:
					self.cur_event -= 1
					check_ref_event = True
				else:
					newBase = newBaseTime(self.time_base - self.time_epoch * 60)
					if newBase != self.time_base:
						self.time_base = newBase
						self.fillGraphEPG(None)  # refill
						return True
			elif dir == +2:  # next page
				self.time_base += self.time_epoch * 60
				self.fillGraphEPG(None)  # refill
				return True
			elif dir == -2:  # prev page
				newBase = newBaseTime(self.time_base - self.time_epoch * 60)
				if newBase != self.time_base:
					self.time_base = newBase
					self.fillGraphEPG(None)  # refill
					return True
			elif dir == +24:
				self.time_base += 86400
				self.fillGraphEPG(None)  # refill
				return True
			elif dir == -24:
				newBase = newBaseTime(self.time_base - 86400)
				if newBase != self.time_base:
					self.time_base = newBase
					self.fillGraphEPG(None)  # refill
					return True

		if cur_service and valid_event and self.cur_event < len(entries):
			entry = entries[self.cur_event]  # (event_id, event_title, begin_time, duration)
			time_base = self.getTimeBase()
			xpos, width = self.calcEntryPosAndWidth(self.event_rect, time_base, self.time_epoch, entry[2], entry[3])
			self.select_rect = Rect(xpos, 0, width, self.event_rect.h)
			clipUpdate = visible and update
			# if the current event doesn't contain current time, keep it as a reference for findBestEvent()
			if check_ref_event:
				self.ref_event = None if entry[2] <= time() < entry[2] + entry[3] else entry
		else:
			self.select_rect = self.event_rect
			clipUpdate = False
		self.l.setSelectionClip(eRect(self.select_rect.x, self.select_rect.y, self.select_rect.w, self.select_rect.h), clipUpdate)
		self.selectionChanged()
		return False

	def queryEPG(self, list, buildFunc=None):
		if self.epgcache is not None:
			if buildFunc is not None:
				return self.epgcache.lookupEvent(list, buildFunc)
			else:
				return self.epgcache.lookupEvent(list)
		return []

	def fillSimilarList(self, refstr, event_id):
		# search similar broadcastings
		t = time()
		if event_id is None:
			return
		self.list = self.epgcache.search(('RIBND', 1024, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, refstr, event_id))
		if self.list and len(self.list):
			self.list.sort(key=lambda x: x[2])
		self.l.setList(self.list)
		self.recalcEntrySize()
		self.selectionChanged()

	def fillSingleEPG(self, service):
		t = time()
		epg_time = t - config.epg.histminutes.value * 60
		test = ['RIBDT', (service.ref.toString(), 0, epg_time, -1)]
		self.list = self.queryEPG(test)
		# Add explicit gaps if data isn't available.
		for i in range(len(self.list) - 1, 0, -1):
			this_beg = self.list[i][2]
			prev_end = self.list[i-1][2] + self.list[i-1][3]
			if prev_end + 5 * 60 < this_beg:
				self.list.insert(i, (self.list[i][0], None, prev_end, this_beg - prev_end, None))
		self.l.setList(self.list)
		self.recalcEntrySize()
		if t != epg_time:
			idx = 0
			for x in self.list:
				idx += 1
				if t < x[2] + x[3]:
					break
			self.instance.moveSelectionTo(idx - 1)
		self.selectionChanged()

	def fillMultiEPG(self, services, stime=None):
		test = [(service.ref.toString(), 0, stime) for service in services]
		test.insert(0, 'X0RIBDTCn')
		self.list = self.queryEPG(test)
		self.l.setList(self.list)
		self.recalcEntrySize()
		self.selectionChanged()

	def updateMultiEPG(self, direction):
		test = [x[3] and (x[1], direction, x[3]) or (x[1], direction, 0) for x in self.list]
		test.insert(0, 'XRIBDTCn')
		epg_data = self.queryEPG(test)
		cnt = 0
		for x in epg_data:
			changecount = self.list[cnt][0] + direction
			if changecount >= 0:
				if x[2] is not None:
					self.list[cnt] = (changecount, x[0], x[1], x[2], x[3], x[4], x[5], x[6])
			cnt += 1
		self.l.setList(self.list)
		self.recalcEntrySize()
		self.selectionChanged()

	def getCurrentCursorLocation(self):
		return self.time_base

	def fillGraphEPG(self, services, stime=None):
		if (self.type in (EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH)) and not self.graphicsloaded:
			if self.graphic:
				_loadPixmapsToAttrs(self, {
					"nowEvPix": 'epg/CurrentEvent.png',
					"nowSelEvPix": 'epg/SelectedCurrentEvent.png',
					"othEvPix": 'epg/OtherEvent.png',
					"selEvPix": 'epg/SelectedEvent.png',
					"othServPix": 'epg/OtherService.png',
					"nowServPix": 'epg/CurrentService.png',
					"recEvPix": 'epg/RecordEvent.png',
					"recSelEvPix": 'epg/SelectedRecordEvent.png',
					"zapEvPix": 'epg/ZapEvent.png',
					"zapSelEvPix": 'epg/SelectedZapEvent.png',
				})
				self.borderPixmaps = _loadPixmaps((
					'epg/BorderTop.png',
					'epg/BorderBottom.png',
					'epg/BorderLeft.png',
					'epg/BorderRight.png',
				))
				self.borderSelectedPixmaps = _loadPixmaps((
					'epg/SelectedBorderTop.png',
					'epg/SelectedBorderBottom.png',
					'epg/SelectedBorderLeft.png',
					'epg/SelectedBorderRight.png',
				))

			_loadPixmapsToAttrs(self, {
				"infoPix": 'epg/information.png',
				"selInfoPix": 'epg/SelectedInformation.png',
			})

			self.graphicsloaded = True

		if stime is not None:
			self.time_base = int(stime)
		if services is None:
			time_base = self.getTimeBase()
			test = [(service[0], 0, time_base, self.time_epoch) for service in self.list]
			serviceList = self.list
			piconIdx = 3
			channelIdx = 4
		else:
			self.cur_event = None
			self.cur_service = None
			test = [(service.ref.toString(), 0, self.time_base, self.time_epoch) for service in services]
			serviceList = services
			piconIdx = 0
			channelIdx = None

		test.insert(0, 'XRnITBD')  # return record, service ref, service name, event id, event title, begin time, duration
		epg_data = self.queryEPG(test)
		self.list = []
		tmp_list = None
		service = ""
		sname = ""

		serviceIdx = 0
		for x in epg_data:
			if service != x[0]:
				if tmp_list is not None:
					picon = None if piconIdx == 0 else serviceList[serviceIdx][piconIdx]
					# We pass the serviceref if we don't have the channel number yet, so it can be grabbed
					channel = serviceList[serviceIdx] if (channelIdx == None) else serviceList[serviceIdx][channelIdx] 
					self.list.append((service, sname, tmp_list[0][0] is not None and tmp_list or None, picon, channel))
					serviceIdx += 1
				service = x[0]
				sname = x[1]
				tmp_list = []
			tmp_list.append((x[2], x[3], x[4], x[5]))  # (event_id, event_title, begin_time, duration)
		if tmp_list and len(tmp_list):
			picon = None if piconIdx == 0 else serviceList[serviceIdx][piconIdx]
			channel = serviceList[serviceIdx] if (channelIdx == None) else serviceList[serviceIdx][channelIdx]
			self.list.append((service, sname, tmp_list[0][0] is not None and tmp_list or None, picon, channel))
			serviceIdx += 1

		self.l.setList(self.list)
		self.recalcEntrySize()
		self.findBestEvent()

	def sortSingleEPG(self, type):
		list = self.list
		if list:
			event_id = self.getSelectedEventId()
			if type == 1:
				list.sort(key=lambda x: (x[4] and x[4].lower(), x[2]))
			else:
				assert(type == 0)
				list.sort(key=lambda x: x[2])
			self.l.invalidate()
			self.moveToEventId(event_id)

	def getChannelNumber(self,service):
		if hasattr(service, "ref") and service.ref and '0:0:0:0:0:0:0:0:0' not in service.ref.toString(): 
			numservice = service.ref
			num = numservice and numservice.getChannelNum() or None
			if num is not None:
				return num
		return None

	def getEventRect(self):
		rc = self.event_rect
		return Rect(rc.x + (self.instance and self.instance.position().x() or 0), rc.y, rc.w, rc.h)

	def getServiceRect(self):
		rc = self.service_rect
		return Rect(rc.x + (self.instance and self.instance.position().x() or 0), rc.y, rc.w, rc.h)

	def getTimeEpoch(self):
		return self.time_epoch

	def getTimeBase(self):
		return self.time_base

	# self.offs no longer does anything

	def resetOffset(self):
		pass

	def getSelectedEventId(self):
		x = self.l.getCurrentSelection()
		return x and x[1]

	def moveToEventId(self, eventId):
		if not eventId:
			return
		index = 0
		for x in self.list:
			if x[1] == eventId:
				self.instance.moveSelectionTo(index)
				break
			index += 1

	def moveToTime(self, time):
		cur_sel = self.l.getCurrentSelection()
		if not cur_sel or not self.epgcache:
			return
		service = ServiceReference(cur_sel[0])
		event = self.epgcache.lookupEventTime(service.ref, time)
		if event:
			self.moveToEventId(event.getEventId())

class TimelineText(HTMLComponent, GUIComponent):

	attribMap = {
		# Plain strs
		"TimelineAlignment": ("str", "timelineAlign"),
		"TimelineTicksOn": ("str", "ticksOn"),
		"TimelineTickAlignment": ("str", "tickAlignment"),
		# Plain ints
		"itemHeight": ("int", "itemHeight"),
		"borderWidth": ("int", "borderWidth"),
		"TimelineTextPadding": ("int", "textPadding"),
		# Fonts
		"TimelineFont": ("font", "timelineFontName", "timelineFontSize"),
		# Colors
		"foregroundColor": ("color", "foreColor"),
		"borderColor": ("color", "borderColor"),
		"backgroundColor": ("color", "backColor"),
	}

	def __init__(self, type=EPG_TYPE_GRAPH, graphic=False):
		GUIComponent.__init__(self)
		self.type = type
		self.graphic = graphic
		self.l = eListboxPythonMultiContent()
		self.l.setSelectionClip(eRect(0, 0, 0, 0))
		self.itemHeight = 30
		self.tlDate = None
		self.tlTime = None
		self.foreColor = 0xffc000
		self.borderColor = 0x000000
		self.backColor = 0x000000
		self.time_base = 0
		self.time_epoch = 0
		self.timelineFontName = "Regular"
		self.timelineFontSize = 20
		self.borderWidth = 1
		self.ticksOn = "yes"
		self.tickAlignment = "right"
		self.textPadding = 2
		self.datefmt = ""

	GUI_WIDGET = eListbox

	def applySkin(self, desktop, screen):
		self.skinAttributes = applyExtraSkinAttributes(self, self.skinAttributes, self.attribMap)
		if self.skinAttributes is not None:
			attribs = []
			for (attrib, value) in self.skinAttributes:
				if attrib == "font":
					self.l.setFont(0, parseFont(value, ((1, 1), (1, 1))))
				else:
					attribs.append((attrib, value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.l.setItemHeight(self.itemHeight)
		if self.graphic:
			_loadPixmapsToAttrs(self, {
				"TlDate": 'epg/TimeLineDate.png',
				"TlTime": 'epg/TimeLineTime.png',
			})
		self.ticksOn = self.ticksOn.lower()
		self.tickAlignment = self.tickAlignment.lower()
		self.setTimeLineFontsize()
		return rc

	def setTimeLineFontsize(self):
		if self.type == EPG_TYPE_GRAPH:
			self.l.setFont(0, gFont(self.timelineFontName, self.timelineFontSize + config.epgselection.graph_timelinefs.value))
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			self.l.setFont(0, gFont(self.timelineFontName, self.timelineFontSize + config.epgselection.infobar_timelinefs.value))

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)

	def setEntries(self, l, timeline_now, time_lines, force):
		event_rect = l.getEventRect()
		time_epoch = l.getTimeEpoch()
		time_base = l.getTimeBase()

		if event_rect is None or time_epoch is None or time_base is None:
			return

		eventLeft = event_rect.x

		res = [None]

		# Note: event_rect and service_rect are relative to the timeline_text position
		# while the time lines are relative to the GraphEPG screen position!
		if self.time_base != time_base or self.time_epoch != time_epoch or force:
			service_rect = l.getServiceRect()
			time_steps = 60 if time_epoch > 180 else 30
			num_lines = (time_epoch + time_steps / 2) / time_steps
			incWidth = float(event_rect.w) * time_steps / time_epoch
			timeStepsCalc = time_steps * 60

			nowTime = localtime(time())
			begTime = localtime(time_base)
			serviceWidth = service_rect.w
			if nowTime.tm_year == begTime.tm_year and nowTime.tm_yday == begTime.tm_yday:
				datestr = _("Today")
			else:
				if serviceWidth > 179:
					datestr = strftime(config.usage.date.daylong.value, begTime)
				elif serviceWidth > 129:
					datestr = strftime(config.usage.date.dayshort.value, begTime)
				elif serviceWidth > 79:
					datestr = strftime(config.usage.date.daysmall.value, begTime)
				else:
					datestr = strftime("%a", begTime)

			foreColor = self.foreColor
			backColor = self.backColor
			bgpng = self.tlDate
			if bgpng is not None and self.graphic:
				backColor = None
				backColorSel = None
				res.append(MultiContentEntryPixmapAlphaTest(
					pos=(0, 0),
					size=(service_rect.w, self.listHeight),
					png=bgpng,
					flags=BT_SCALE))
			else:
				res.append(MultiContentEntryText(
					pos=(0, 0),
					size=(service_rect.w, self.listHeight),
					color=foreColor,
					backcolor=backColor,
					border_width=self.borderWidth, border_color = self.borderColor))

			res.append(MultiContentEntryText(
				pos=(5, 0),
				size=(service_rect.w - 15, self.listHeight),
				font=0, flags=int(config.epgselection.graph_timelinedate_alignment.value),
				text=datestr,
				color=foreColor,
				backcolor=backColor))

			bgpng = self.tlTime
			if bgpng is not None and self.graphic:
				backColor = None
				backColorSel = None
				res.append(MultiContentEntryPixmapAlphaTest(
					pos=(service_rect.w, 0),
					size=(event_rect.w, self.listHeight),
					png=bgpng,
					flags=BT_SCALE))
			else:
				res.append(MultiContentEntryText(
					pos=(service_rect.w, 0),
					size=(event_rect.w, self.listHeight),
					color=foreColor,
					backcolor=backColor,
					border_width=self.borderWidth, border_color = self.borderColor))

			# An estimate of textHeight is the best we can do, and it's not really critical
			textHeight = self.timelineFontSize + 2
			textScreenY = self.position[1]
			for x in range(0, num_lines):
				line = time_lines[x]
				xpos = round(x * incWidth)
				textOffset = self.textPadding
				if self.ticksOn == "yes":
					tickWidth, tickHeight = line.getSize()
					tickScreenY = line.position[1]
					if self.tickAlignment == "left":
						tickXOffset = -tickWidth
					elif self.tickAlignment == "center":
						tickXOffset = -tickWidth / 2
					else:
						tickXOffset = 0
					line.setPosition(xpos + eventLeft + tickXOffset, tickScreenY)
					line.visible = True
					# If the tick and text overlap in y, nudge the text over by the
					# amount of the line to the left of the nominal x position
					if min(textScreenY + textHeight, tickScreenY + tickHeight) - max(textScreenY, tickScreenY) > 0:
						textOffset += tickWidth + tickXOffset
				else:
					line.visible = False
				ttime = localtime(time_base + (x * timeStepsCalc))
				if config.usage.time.enabled.value:
					timetext = strftime(config.usage.time.short.value, ttime)
				else:
					if (self.type == EPG_TYPE_GRAPH and config.epgselection.graph_timeline24h.value) or (self.type == EPG_TYPE_INFOBARGRAPH and config.epgselection.infobar_timeline24h.value):
						timetext = strftime("%H:%M", ttime)
					else:
						if int(strftime("%H", ttime)) > 12:
							timetext = strftime("%-I:%M", ttime) + _('pm')
						else:
							timetext = strftime("%-I:%M", ttime) + _('am')
				res.append(MultiContentEntryText(
					pos=(service_rect.width() + xpos + textOffset, 0),
					size=(incWidth, self.listHeight),
					font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
					text=timetext,
					color=foreColor,
					backcolor=backColor))
			for x in range(num_lines, MAX_TIMELINES):
				time_lines[x].visible = False
			self.l.setList([res])
			self.time_base = time_base
			self.time_epoch = time_epoch

		now = time()
		if time_base <= now < (time_base + time_epoch * 60):
			xpos = int((((now - time_base) * event_rect.w) / (time_epoch * 60)) - (timeline_now.getSize()[0] / 2))
			old_pos = timeline_now.position
			new_pos = (xpos + eventLeft, old_pos[1])
			if old_pos != new_pos:
				timeline_now.setPosition(new_pos[0], new_pos[1])
			timeline_now.visible = True
		else:
			timeline_now.visible = False

class EPGBouquetList(HTMLComponent, GUIComponent):

	attribMap = {
		# Plain ints
		"borderWidth": ("int", "borderWidth"),
		"itemHeight": ("int", "itemHeight"),
		# Fonts
		"font": ("font", "bouquetFontName", "bouquetFontSize"),
		# Colors
		"foregroundColor": ("color", "foreColor"),
		"backgroundColor": ("color", "backColor"),
		"foregroundColorSelected": ("color", "foreColorSelected"),
		"backgroundColorSelected": ("color", "backColorSelected"),
		"borderColor": ("color", "borderColor"),
	}

	def __init__(self, graphic=False):
		GUIComponent.__init__(self)
		self.graphic = graphic
		self.l = eListboxPythonMultiContent()
		self.l.setBuildFunc(self.buildEntry)

		self.onSelChanged = []

		self.foreColor = 0xffffff
		self.foreColorSelected = 0xffffff
		self.backColor = 0x2D455E
		self.backColorSelected = 0xd69600

		self.borderColor = 0xC0C0C0
		self.borderWidth = 1

		self.othPix = None
		self.selPix = None
		self.graphicsloaded = False

		self.bouquetFontName = "Regular"
		self.bouquetFontSize = 20

		self.itemHeight = 31
		self.listHeight = None
		self.listWidth = None

		self.bouquetNamePadding = 3
		self.bouquetNameAlign = 'left'
		self.bouquetNameWrap = 'no'

	def applySkin(self, desktop, screen):
		self.skinAttributes = applyExtraSkinAttributes(self, self.skinAttributes, self.attribMap)
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.l.setItemHeight(self.itemHeight)
		self.setBouquetFontsize()
		return rc

	GUI_WIDGET = eListbox

	def getCurrentBouquet(self):
		return self.l.getCurrentSelection()[0]

	def getCurrentBouquetService(self):
		return self.l.getCurrentSelection()[1]

	def setCurrentBouquet(self, currentBouquetService):
		self.currentBouquetService = currentBouquetService

	def selectionChanged(self):
		for x in self.onSelChanged:
			if x is not None:
				x()

	def getIndexFromService(self, serviceref):
		if serviceref is not None:
			for x in range(len(self.bouquetslist)):
				if CompareWithAlternatives(self.bouquetslist[x][1].toString(), serviceref.toString()):
					return x
		return None

	def moveToService(self, serviceref):
		newIdx = self.getIndexFromService(serviceref)
		if newIdx is None:
			newIdx = 0
		self.setCurrentIndex(newIdx)

	def setCurrentIndex(self, index):
		if self.instance is not None:
			self.instance.moveSelectionTo(index)

	def moveTo(self, dir):
		if self.instance is not None:
			self.instance.moveSelection(dir)

	def setBouquetFontsize(self):
		self.l.setFont(0, gFont(self.bouquetFontName, self.bouquetFontSize))

	def postWidgetCreate(self, instance):
		self.l.setSelectableFunc(True)
		instance.setWrapAround(True)
		instance.selectionChanged.get().append(self.selectionChanged)
		instance.setContent(self.l)
		# self.l.setSelectionClip(eRect(0,0,0,0), False)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().append(self.selectionChanged)
		instance.setContent(None)

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)

	def recalcEntrySize(self):
		esize = self.l.getItemSize()
		width = esize.width()
		height = esize.height()
		self.bouquet_rect = Rect(0, 0, width, height)

	def getBouquetRect(self):
		rc = self.bouquet_rect
		return Rect(rc.x + (self.instance and self.instance.position().x() or 0), rc.y, rc.w, rc.h)

	def buildEntry(self, name, func):
		r1 = self.bouquet_rect
		selected = self.currentBouquetService == func

		if self.bouquetNameAlign.lower() == 'left':
			if self.bouquetNameWrap.lower() == 'yes':
				alignment = RT_HALIGN_LEFT | RT_VALIGN_CENTER | RT_WRAP
			else:
				alignment = RT_HALIGN_LEFT | RT_VALIGN_CENTER
		else:
			if self.bouquetNameWrap.lower() == 'yes':
				alignment = RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_WRAP
			else:
				alignment = RT_HALIGN_CENTER | RT_VALIGN_CENTER

		res = [None]

		borderPixmaps = None

		if selected:
			if self.graphic:
				borderPixmaps = self.borderSelectedPixmaps
			foreColor = self.foreColor
			backColor = self.backColor
			foreColorSel = self.foreColorSelected
			backColorSel = self.backColorSelected
			bgpng = self.selPix
			if bgpng is not None and self.graphic:
				backColor = None
				backColorSel = None
		else:
			if self.graphic:
				borderPixmaps = self.borderPixmaps
			backColor = self.backColor
			foreColor = self.foreColor
			foreColorSel = self.foreColorSelected
			backColorSel = self.backColorSelected
			bgpng = self.othPix
			if bgpng is not None and self.graphic:
				backColor = None
				backColorSel = None

		# box background
		if bgpng is not None and self.graphic:
			res.append(MultiContentEntryPixmapAlphaTest(
				png=bgpng,
				flags=BT_SCALE,
				**_rectToPosSize(r1, self.borderWidth)))
		else:
			res.append(MultiContentEntryText(
				font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				text="", color=None, color_sel=None,
				backcolor=backColor, backcolor_sel=backColorSel,
				border_width=self.borderWidth, border_color=self.borderColor,
				**_rectToPosSize(r1, 0)))

		res.append(MultiContentEntryText(
			font=0, flags=alignment,
			text=name,
			color=foreColor, color_sel=foreColorSel,
			backcolor=backColor, backcolor_sel=backColorSel,
			**_rectToPosSize(r1, self.borderWidth, self.borderWidth + self.bouquetNamePadding)))

		# Borders
		if self.graphic:
			res += _makeBorder(r1, self.borderWidth, borderPixmaps)

		return res

	def fillBouquetList(self, bouquets):
		if self.graphic and not self.graphicsloaded:
			_loadPixmapsToAttrs(self, {
				"othPix": 'epg/OtherEvent.png',
				"selPix": 'epg/SelectedCurrentEvent.png',
			})
			self.borderPixmaps = _loadPixmaps((
				'epg/BorderTop.png',
				'epg/BorderBottom.png',
				'epg/BorderLeft.png',
				'epg/BorderRight.png',
			))
			self.borderSelectedPixmaps = _loadPixmaps((
				'epg/SelectedBorderTop.png',
				'epg/SelectedBorderBottom.png',
				'epg/SelectedBorderLeft.png',
				'epg/SelectedBorderRight.png',
			))

			self.graphicsloaded = True
		self.bouquetslist = bouquets
		self.l.setList(self.bouquetslist)
		self.recalcEntrySize()
		self.selectionChanged()
		self.currentBouquetService = self.getCurrentBouquetService()
