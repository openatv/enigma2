from time import localtime, time, strftime

from enigma import eEPGCache, eListbox, eListboxPythonMultiContent, loadPNG, gFont, getDesktop, eRect, eSize, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, BT_SCALE, BT_KEEP_ASPECT_RATIO

from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend, MultiContentEntryPixmapAlphaTest
from Components.Renderer.Picon import getPiconName
from skin import parseColor, parseFont
from Tools.Alternatives import CompareWithAlternatives
from Tools.LoadPixmap import LoadPixmap
from Components.config import config
from ServiceReference import ServiceReference
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN


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

class EPGList(HTMLComponent, GUIComponent):
	def __init__(self, type = EPG_TYPE_SINGLE, selChangedCB = None, timer = None, time_epoch = 120, overjump_empty = False, graphic=False):
		self.cur_event = None
		self.cur_service = None
		self.offs = 0
		self.time_base = None
		self.time_epoch = time_epoch
		self.select_rect = None
		self.event_rect = None
		self.service_rect = None
		self.currentlyPlaying = None
		self.showPicon = False
		self.showServiceTitle = True
		self.screenwidth = getDesktop(0).size().width()

		self.overjump_empty = overjump_empty
		self.timer = timer
		self.onSelChanged = [ ]
		if selChangedCB is not None:
			self.onSelChanged.append(selChangedCB)
		GUIComponent.__init__(self)
		self.type = type
		self.graphic = graphic
		self.l = eListboxPythonMultiContent()

		if type == EPG_TYPE_SINGLE or type == EPG_TYPE_ENHANCED or type == EPG_TYPE_INFOBAR:
			self.l.setBuildFunc(self.buildSingleEntry)
		elif type == EPG_TYPE_MULTI:
			self.l.setBuildFunc(self.buildMultiEntry)
		elif type == EPG_TYPE_GRAPH or type == EPG_TYPE_INFOBARGRAPH:
			self.l.setBuildFunc(self.buildGraphEntry)
		else:
			assert(type == EPG_TYPE_SIMILAR)
			self.l.setBuildFunc(self.buildSimilarEntry)
		self.epgcache = eEPGCache.getInstance()

		self.clocks = [ LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_add.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_pre.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_prepost.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_post.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_add.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_pre.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_zap.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_prepost.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_post.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_add.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_pre.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_zaprec.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_prepost.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_post.png'))]

		self.selclocks = [ LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_add.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_selpre.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_selprepost.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_selpost.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_add.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_selpre.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_zap.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_selprepost.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_selpost.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_add.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_selpre.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_zaprec.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_selprepost.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_selpost.png'))]

		self.autotimericon = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_autotimer.png'))

		self.nowEvPix = None
		self.nowSelEvPix = None
		self.othEvPix = None
		self.selEvPix = None
		self.othServPix = None
		self.nowServPix = None
		self.recEvPix = None
		self.recSelEvPix = None
		self.recordingEvPix= None
		self.zapEvPix = None
		self.zapSelEvPix = None

		self.borderTopPix = None
		self.borderBottomPix = None
		self.borderLeftPix = None
		self.borderRightPix = None
		self.borderSelectedTopPix = None
		self.borderSelectedLeftPix = None
		self.borderSelectedBottomPix = None
		self.borderSelectedRightPix = None
		self.InfoPix = None
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
			self.eventFontSizeGraph = 18
			self.eventFontSizeSingle = 22
			self.eventFontSizeMulti = 22
			self.serviceFontSizeInfobar = 20
			self.eventFontSizeInfobar = 22

		self.listHeight = None
		self.listWidth = None
		self.serviceBorderWidth = 1
		self.serviceNamePadding = 3
		self.eventBorderWidth = 1
		self.eventNamePadding = 3
		self.eventNameAlign = 'left'
		self.eventNameWrap = 'yes'
		self.NumberOfRows = None

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "ServiceFontGraphical":
					font = parseFont(value, ((1,1),(1,1)) )
					self.serviceFontNameGraph = font.family
					self.serviceFontSizeGraph = font.pointSize
				elif attrib == "EntryFontGraphical":
					font = parseFont(value, ((1,1),(1,1)) )
					self.eventFontNameGraph = font.family
					self.eventFontSize = font.pointSize
				elif attrib == "EntryFontAlignment":
					self.eventNameAlign = value
				elif attrib == "EntryFontWrap":
					self.eventNameWrap = value
				elif attrib == "EventFontSingle":
					font = parseFont(value, ((1,1),(1,1)) )
					self.eventFontNameSingle = font.family
					self.eventFontSizeSingle = font.pointSize
				elif attrib == "EventFontInfobar":
					font = parseFont(value, ((1,1),(1,1)) )
					self.eventFontNameInfobar = font.family
					self.eventFontSizeInfobar = font.pointSize
				elif attrib == "ServiceFontInfobar":
					font = parseFont(value, ((1,1),(1,1)) )
					self.serviceFontNameInfobar = font.family
					self.serviceFontSizeInfobar = font.pointSize

				elif attrib == "ServiceForegroundColor":
					self.foreColorService = parseColor(value).argb()
				elif attrib == "ServiceForegroundColorNow":
					self.foreColorServiceNow = parseColor(value).argb()
				elif attrib == "ServiceBackgroundColor":
					self.backColorService = parseColor(value).argb()
				elif attrib == "ServiceBackgroundColorNow":
					self.backColorServiceNow = parseColor(value).argb()

				elif attrib == "EntryForegroundColor":
					self.foreColor = parseColor(value).argb()
				elif attrib == "EntryForegroundColorSelected":
					self.foreColorSelected = parseColor(value).argb()
				elif attrib == "EntryBackgroundColor":
					self.backColor = parseColor(value).argb()
				elif attrib == "EntryBackgroundColorSelected":
					self.backColorSelected = parseColor(value).argb()
				elif attrib == "EntryBackgroundColorNow":
					self.backColorNow = parseColor(value).argb()
				elif attrib == "EntryBackgroundColorNowSelected":
					self.backColorNowSelected = parseColor(value).argb()
				elif attrib == "EntryForegroundColorNow":
					self.foreColorNow = parseColor(value).argb()
				elif attrib == "EntryForegroundColorNowSelected":
					self.foreColorNowSelected = parseColor(value).argb()

				elif attrib == "ServiceBorderColor":
					self.borderColorService = parseColor(value).argb()
				elif attrib == "ServiceBorderWidth":
					self.serviceBorderWidth = int(value)
				elif attrib == "ServiceNamePadding":
					self.serviceNamePadding = int(value)
				elif attrib == "EntryBorderColor":
					self.borderColor = parseColor(value).argb()
				elif attrib == "EventBorderWidth":
					self.eventBorderWidth = int(value)
				elif attrib == "EventNamePadding":
					self.eventNamePadding = int(value)

				elif attrib == "RecordForegroundColor":
					self.foreColorRecord = parseColor(value).argb()
				elif attrib == "RecordForegroundColorSelected":
					self.foreColorRecordSelected = parseColor(value).argb()
				elif attrib == "RecordBackgroundColor":
					self.backColorRecord = parseColor(value).argb()
				elif attrib == "RecordBackgroundColorSelected":
					self.backColorRecordSelected = parseColor(value).argb()
				elif attrib == "ZapForegroundColor":
					self.foreColorZap = parseColor(value).argb()
				elif attrib == "ZapBackgroundColor":
					self.backColorZap = parseColor(value).argb()
				elif attrib == "ZapForegroundColorSelected":
					self.foreColorZapSelected = parseColor(value).argb()
				elif attrib == "ZapBackgroundColorSelected":
					self.backColorZapSelected = parseColor(value).argb()
				elif attrib == "NumberOfRows":
					self.NumberOfRows = int(value)
				else:
					attribs.append((attrib,value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.setItemsPerPage()
		return rc

	def getCurrentChangeCount(self):
		if self.type == EPG_TYPE_MULTI and self.l.getCurrentSelection() is not None:
			return self.l.getCurrentSelection()[0]
		return 0

	def isSelectable(self, service, service_name, events, picon):
		return (events and len(events) and True) or False

	def setShowServiceMode(self, value):
		self.showServiceTitle = "servicename" in value
		self.showPicon = "picon" in value
		self.recalcEntrySize()
		self.selEntry(0) #Select entry again so that the clipping region gets updated if needed

	def setOverjump_Empty(self, overjump_empty):
		if overjump_empty:
			self.l.setSelectableFunc(self.isSelectable)
		else:
			self.l.setSelectableFunc(None)

	def setEpoch(self, epoch):
		self.offs = 0
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
				if str(self.list[x][0]).startswith('1:'): # check for Graphical EPG
					if CompareWithAlternatives(self.list[x][0], serviceref.toString()):
						return x
				elif str(self.list[x][1]).startswith('1:'): # check for Multi EPG
					if CompareWithAlternatives(self.list[x][1], serviceref.toString()):
						return x
				else:
					return None
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

	def setCurrentIndex(self, index):
		if self.instance is not None:
			self.instance.moveSelectionTo(index)

	def moveTo(self, dir):
		if self.instance is not None:
			self.instance.moveSelection(dir)

	def getCurrent(self):
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			if self.cur_service is None:
				return None, None
			old_service = self.cur_service  #(service, service_name, events, picon)
			events = self.cur_service[2]
			refstr = self.cur_service[0]
			try:
				if self.cur_event is None or not events or (self.cur_event and events and self.cur_event > len(events)-1):
					return None, ServiceReference(refstr)
				event = events[self.cur_event] #(event_id, event_title, begin_time, duration)
				eventid = event[0]
				service = ServiceReference(refstr)
				event = self.getEventFromId(service, eventid) # get full event info
				return event, service
			except:
				return None, ServiceReference(refstr)
		else:
			idx = 0
			if self.type == EPG_TYPE_MULTI:
				idx += 1
			tmp = self.l.getCurrentSelection()
			if tmp is None:
				return None, None
			eventid = tmp[idx+1]
			service = ServiceReference(tmp[idx])
			event = self.getEventFromId(service, eventid)
			return event, service

	def connectSelectionChanged(func):
		if not self.onSelChanged.count(func):
			self.onSelChanged.append(func)

	def disconnectSelectionChanged(func):
		self.onSelChanged.remove(func)

	def serviceChanged(self):
		cur_sel = self.l.getCurrentSelection()
		if cur_sel:
			self.findBestEvent()

	def findBestEvent(self):
		old_service = self.cur_service  #(service, service_name, events, picon)
		cur_service = self.cur_service = self.l.getCurrentSelection()
		time_base = self.getTimeBase()
		last_time = time()
		if old_service and self.cur_event is not None:
			try:
				events = old_service[2]
				cur_event = events[self.cur_event] #(event_id, event_title, begin_time, duration)
				last_time = cur_event[2]
			except:
				pass
		if cur_service:
			self.cur_event = 0
			events = cur_service[2]
			best = None
			if events and len(events):
				best_diff = 0
				idx = 0
				for event in events: #iterate all events
					ev_time = event[2]
					ev_end_time = event[2] + event[3]
					if ev_time < time_base:
						ev_time = time_base
					diff = abs(ev_time - last_time)
					if best is None or (diff < best_diff):
						best = idx
						best_diff = diff
					if ev_end_time < time():
						best = idx+1
					if best is not None and ev_time > last_time and ev_end_time > time():
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
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			if self.type == EPG_TYPE_GRAPH:
				if self.listHeight > 0:
					itemHeight = self.listHeight / config.epgselection.graph_itemsperpage.value
				else:
					itemHeight = 54 # some default (270/5)
				if config.epgselection.graph_heightswitch.value:
					if ((self.listHeight / config.epgselection.graph_itemsperpage.value) / 3) >= 27:
						tmp_itemHeight = ((self.listHeight / config.epgselection.graph_itemsperpage.value) / 3)
					elif ((self.listHeight / config.epgselection.graph_itemsperpage.value) / 2) >= 27:
						tmp_itemHeight = ((self.listHeight / config.epgselection.graph_itemsperpage.value) / 2)
					else:
						tmp_itemHeight = 27
					if tmp_itemHeight < itemHeight:
						itemHeight = tmp_itemHeight
					else:
						if ((self.listHeight / config.epgselection.graph_itemsperpage.value) * 3) <= 45:
							itemHeight = ((self.listHeight / config.epgselection.graph_itemsperpage.value) * 3)
						elif ((self.listHeight / config.epgselection.graph_itemsperpage.value) * 2) <= 45:
							itemHeight = ((self.listHeight / config.epgselection.graph_itemsperpage.value) * 2)
						else:
							itemHeight = 45
			elif self.type == EPG_TYPE_INFOBARGRAPH:
				if self.listHeight > 0:
					itemHeight = self.listHeight / config.epgselection.infobar_itemsperpage.value
				else:
					itemHeight = 54 # some default (270/5)
			if self.NumberOfRows:
				itemHeight = self.listHeight / self.NumberOfRows
			self.l.setItemHeight(itemHeight)
			self.instance.resize(eSize(self.listWidth, self.listHeight / itemHeight * itemHeight))
			self.listHeight = self.instance.size().height()
			self.listWidth = self.instance.size().width()
			self.itemHeight = itemHeight

		elif self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_SIMILAR:
			if self.listHeight > 0:
				itemHeight = self.listHeight / config.epgselection.enhanced_itemsperpage.value
			else:
				itemHeight = 32
			if itemHeight < 15:
				itemHeight = 15
			self.l.setItemHeight(itemHeight)
			self.instance.resize(eSize(self.listWidth, self.listHeight / itemHeight * itemHeight))
			self.listHeight = self.instance.size().height()
			self.listWidth = self.instance.size().width()
			self.itemHeight = itemHeight
		elif self.type == EPG_TYPE_MULTI:
			if self.listHeight > 0:
				itemHeight = self.listHeight / config.epgselection.multi_itemsperpage.value
			else:
				itemHeight = 32
			if itemHeight < 25:
				itemHeight = 25
			self.l.setItemHeight(itemHeight)
			self.instance.resize(eSize(self.listWidth, self.listHeight / itemHeight * itemHeight))
			self.listHeight = self.instance.size().height()
			self.listWidth = self.instance.size().width()
			self.itemHeight = itemHeight
		elif self.type == EPG_TYPE_INFOBAR:
			if self.listHeight > 0:
				itemHeight = self.listHeight / config.epgselection.infobar_itemsperpage.value
			else:
				itemHeight = 32
			if itemHeight < 25:
				itemHeight = 20
			self.l.setItemHeight(int(itemHeight))
			self.instance.resize(eSize(self.listWidth, self.listHeight / itemHeight * itemHeight))
			self.listHeight = self.instance.size().height()
			self.listWidth = self.instance.size().width()
			self.itemHeight = itemHeight

	def setServiceFontsize(self):
		if self.type == EPG_TYPE_GRAPH:
			self.l.setFont(0, gFont(self.serviceFontNameGraph, self.serviceFontSizeGraph + config.epgselection.graph_servfs.value))
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			self.l.setFont(0, gFont(self.serviceFontNameInfobar, self.serviceFontSizeInfobar + config.epgselection.infobar_servfs.value))

	def setEventFontsize(self):
		if self.type == EPG_TYPE_GRAPH:
			self.l.setFont(1, gFont(self.eventFontNameGraph, self.eventFontSizeGraph + config.epgselection.graph_eventfs.value))
		elif self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_SIMILAR:
			self.l.setFont(0, gFont(self.eventFontNameSingle, self.eventFontSizeSingle + config.epgselection.enhanced_eventfs.value))
		elif self.type == EPG_TYPE_MULTI:
			self.l.setFont(0, gFont(self.eventFontNameMulti, self.eventFontSizeMulti + config.epgselection.multi_eventfs.value))
			self.l.setFont(1, gFont(self.eventFontNameMulti, self.eventFontSizeMulti - 4 + config.epgselection.multi_eventfs.value))
		elif self.type == EPG_TYPE_INFOBAR:
			self.l.setFont(0, gFont(self.eventFontNameInfobar, self.eventFontSizeInfobar + config.epgselection.infobar_eventfs.value))
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			self.l.setFont(1, gFont(self.eventFontNameInfobar, self.eventFontSizeInfobar + config.epgselection.infobar_eventfs.value))

	def postWidgetCreate(self, instance):
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self.setOverjump_Empty(self.overjump_empty)
			instance.setWrapAround(True)
			instance.selectionChanged.get().append(self.serviceChanged)
			instance.setContent(self.l)
			self.l.setSelectionClip(eRect(0,0,0,0), False)
			self.setServiceFontsize()
			self.setEventFontsize()
		else:
			instance.setWrapAround(False)
			instance.selectionChanged.get().append(self.selectionChanged)
			instance.setContent(self.l)
			self.setEventFontsize()

	def preWidgetRemove(self, instance):
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
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
			xpos = 0
			w = width / 10 * 3
			self.service_rect = Rect(xpos, 0, w-10, height)
			xpos += w
			w = width / 10 * 2
			self.start_end_rect = Rect(xpos, 0, w-10, height)
			self.progress_rect = Rect(xpos, 4, w-10, height-8)
			xpos += w
			w = width / 10 * 4.6
			self.descr_rect = Rect(xpos, 0, w, height)
		elif self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			servicew = 0
			piconw = 0
			if self.type == EPG_TYPE_GRAPH:
				if self.showServiceTitle:
					servicew = config.epgselection.graph_servicewidth.value
				if self.showPicon:
					piconw = config.epgselection.graph_piconwidth.value
			elif self.type == EPG_TYPE_INFOBARGRAPH:
				if self.showServiceTitle:
					servicew = config.epgselection.infobar_servicewidth.value
				if self.showPicon:
					piconw = config.epgselection.infobar_piconwidth.value
			w = (piconw + servicew)
			self.service_rect = Rect(0, 0, w, height)
			self.event_rect = Rect(w, 0, width - w, height)
			piconHeight = height - 2 * self.serviceBorderWidth
			piconWidth = piconw
			if piconWidth > w - 2 * self.serviceBorderWidth:
				piconWidth = w - 2 * self.serviceBorderWidth
			self.picon_size = eSize(piconWidth, piconHeight)
		else:
			self.weekday_rect = Rect(0, 0, float(width * 10) / 100, height)
			self.datetime_rect = Rect(self.weekday_rect.width(), 0, float(width * 25) / 100, height)
			self.descr_rect = Rect(self.datetime_rect.left() + self.datetime_rect.width(), 0, float(width * 62) / 100, height)

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
		xpos, width = self.calcEntryPosAndWidthHelper(ev_start, ev_duration, time_base, time_base + time_epoch * 60, event_rect.width())
		return xpos + event_rect.left(), width

	def getPixmapForEntry(self, service, eventId, beginTime, duration):
		if not beginTime:
			return None
		rec = self.timer.isInTimer(eventId, beginTime, duration, service)
		if rec is not None:
			self.wasEntryAutoTimer = rec[2]
			return rec[1]
		else:
			self.wasEntryAutoTimer = False
			return None

	def buildSingleEntry(self, service, eventId, beginTime, duration, EventName):
		clock_types = self.getPixmapForEntry(service, eventId, beginTime, duration)
		r1 = self.weekday_rect
		r2 = self.datetime_rect
		r3 = self.descr_rect
		t = localtime(beginTime)
		res = [
			None, # no private data needed
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _(strftime("%a", t))),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, r2.w, r1.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, strftime("%e/%m, %-H:%M", t))
		]
		if clock_types:
			if self.wasEntryAutoTimer and clock_types in (2,7,12):
				if self.screenwidth and self.screenwidth == 1920:
					res.extend((
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x+r3.w-25, (r3.h/2-13), 25, 25, self.clocks[clock_types]),
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x+r3.w-52, (r3.h/2-13), 25, 25, self.autotimericon),
						(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w-52, r3.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, EventName)
						))
				else:
					res.extend((
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x+r3.w-21, (r3.h/2-11), 21, 21, self.clocks[clock_types]),
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x+r3.w-42, (r3.h/2-11), 21, 21, self.autotimericon),
						(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w-42, r3.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, EventName)
						))
			else:
				if self.screenwidth and self.screenwidth == 1920:
					res.extend((
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x+r3.w-25, (r3.h/2-13), 25, 25, self.clocks[clock_types]),
						(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w-25, r3.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, EventName)
						))
				else:
					res.extend((
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x+r3.w-21, (r3.h/2-11), 21, 21, self.clocks[clock_types]),
						(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w-21, r3.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, EventName)
						))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, EventName))
		return res

	def buildSimilarEntry(self, service, eventId, beginTime, service_name, duration):
		clock_types = self.getPixmapForEntry(service, eventId, beginTime, duration)
		r1 = self.weekday_rect
		r2 = self.datetime_rect
		r3 = self.descr_rect
		t = localtime(beginTime)
		res = [
			None,  # no private data needed
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _(strftime("%a", t))),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, r2.w, r1.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, strftime("%e/%m, %-H:%M", t))
		]
		if clock_types:
			if self.wasEntryAutoTimer and clock_types in (2,7,12):
				if self.screenwidth and self.screenwidth == 1920:
					res.extend((
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x+r3.w-25, (r3.h/2-13), 25, 25, self.clocks[clock_types]),
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x+r3.w-52, (r3.h/2-13), 25, 25, self.autotimericon),
						(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w-52, r3.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, service_name)
					))
				else:
					res.extend((
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x+r3.w-21, (r3.h/2-11), 21, 21, self.clocks[clock_types]),
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x+r3.w-42, (r3.h/2-11), 21, 21, self.autotimericon),
						(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w-42, r3.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, service_name)
					))
			else:
				if self.screenwidth and self.screenwidth == 1920:
					res.extend((
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x+r3.w-25, (r3.h/2-13), 25, 25, self.clocks[clock_types]),
						(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w-25, r3.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, service_name)
					))
				else:
					res.extend((
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.x+r3.w-21, (r3.h/2-11), 21, 21, self.clocks[clock_types]),
						(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w-21, r3.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, service_name)
					))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, service_name))
		return res

	def buildMultiEntry(self, changecount, service, eventId, beginTime, duration, EventName, nowTime, service_name):
		r1 = self.service_rect
		r2 = self.progress_rect
		r3 = self.descr_rect
		r4 = self.start_end_rect
		res = [None, (eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, service_name)] # no private data needed
		if beginTime is not None:
			clock_types = self.getPixmapForEntry(service, eventId, beginTime, duration)
			if nowTime < beginTime:
				begin = localtime(beginTime)
				end = localtime(beginTime+duration)
				res.extend((
					(eListboxPythonMultiContent.TYPE_TEXT, r4.x, r4.y, r4.w, r4.h, 1, RT_HALIGN_CENTER|RT_VALIGN_CENTER, "%02d.%02d - %02d.%02d"%(begin[3],begin[4],end[3],end[4])),
					(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, 80, r3.h, 1, RT_HALIGN_RIGHT|RT_VALIGN_CENTER, _("%d min") % (duration / 60))
				))
			else:
				percent = (nowTime - beginTime) * 100 / duration
				prefix = "+"
				remaining = ((beginTime+duration) - int(time())) / 60
				if remaining <= 0:
					prefix = ""
				res.extend((
					(eListboxPythonMultiContent.TYPE_PROGRESS, r2.x, r2.y, r2.w, r2.h, percent),
					(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, 80, r3.h, 1, RT_HALIGN_RIGHT|RT_VALIGN_CENTER, _("%s%d min") % (prefix, remaining))
				))
			if clock_types:
				if clock_types in (1,6,11):
					pos = r3.x+r3.w
				else:
					pos = r3.x+r3.w-10
				if self.wasEntryAutoTimer and clock_types in (2,7,12):
					if self.screenwidth and self.screenwidth == 1920:
						res.extend((
							(eListboxPythonMultiContent.TYPE_TEXT, r3.x + 90, r3.y, r3.w-131, r3.h, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, EventName),
							(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, pos, (r3.h/2-13), 25, 25, self.clocks[clock_types]),
							(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, pos-26, (r3.h/2-13), 25, 25, self.autotimericon)
						))
					else:
						res.extend((
							(eListboxPythonMultiContent.TYPE_TEXT, r3.x + 90, r3.y, r3.w-131, r3.h, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, EventName),
							(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, pos, (r3.h/2-11), 21, 21, self.clocks[clock_types]),
							(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, pos-22, (r3.h/2-11), 21, 21, self.autotimericon)
						))
				else:
					if self.screenwidth and self.screenwidth == 1920:
						res.extend((
							(eListboxPythonMultiContent.TYPE_TEXT, r3.x + 90, r3.y, r3.w-110, r3.h, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, EventName),
							(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, pos, (r3.h/2-13), 25, 25, self.clocks[clock_types])
						))
					else:
						res.extend((
							(eListboxPythonMultiContent.TYPE_TEXT, r3.x + 90, r3.y, r3.w-110, r3.h, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, EventName),
							(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, pos, (r3.h/2-11), 21, 21, self.clocks[clock_types])
						))
			else:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x + 90, r3.y, r3.w-100, r3.h, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, EventName))
		return res

	def buildGraphEntry(self, service, service_name, events, picon):
		r1 = self.service_rect
		r2 = self.event_rect
		left = r2.x
		top = r2.y
		width = r2.w
		height = r2.h
		selected = self.cur_service[0] == service
		res = [ None ]

		borderTopPix = None
		borderLeftPix = None
		borderBottomPix = None
		borderRightPix = None

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
					pos = (r1.x + self.serviceBorderWidth, r1.y + self.serviceBorderWidth),
					size = (r1.w - 2 * self.serviceBorderWidth, r1.h - 2 * self.serviceBorderWidth),
					png = bgpng,
					flags = BT_SCALE))
		else:
			res.append(MultiContentEntryText(
					pos  = (r1.x, r1.y),
					size = (r1.w, r1.h),
					font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER,
					text = "",
					color = serviceForeColor, color_sel = serviceForeColor,
					backcolor = serviceBackColor, backcolor_sel = serviceBackColor,
					border_width = self.serviceBorderWidth, border_color = self.borderColorService))

		displayPicon = None
		if self.showPicon:
			if picon is None: # go find picon and cache its location
				picon = getPiconName(service)
				curIdx = self.l.getCurrentSelectionIndex()
				self.list[curIdx] = (service, service_name, events, picon)
			piconWidth = self.picon_size.width()
			piconHeight = self.picon_size.height()
			if picon != "":
				displayPicon = loadPNG(picon)
			if displayPicon is not None:
				res.append(MultiContentEntryPixmapAlphaBlend(
					pos = (r1.x + self.serviceBorderWidth, r1.y + self.serviceBorderWidth),
					size = (piconWidth, piconHeight),
					png = displayPicon,
					backcolor = None, backcolor_sel = None, flags = BT_SCALE | BT_KEEP_ASPECT_RATIO))
			elif not self.showServiceTitle:
				# no picon so show servicename anyway in picon space
				namefont = 1
				namefontflag = RT_HALIGN_LEFT | RT_VALIGN_CENTER | RT_WRAP
				namewidth = piconWidth
				piconWidth = 0
			else:
				piconWidth = 0
		else:
			piconWidth = 0

		if self.showServiceTitle: # we have more space so reset parms
			namefont = 0
			namefontflag = RT_HALIGN_LEFT | RT_VALIGN_CENTER
			namewidth = r1.w - piconWidth

		if self.showServiceTitle or displayPicon is None:
			res.append(MultiContentEntryText(
				pos = (r1.x + piconWidth + self.serviceBorderWidth + self.serviceNamePadding,
					r1.y + self.serviceBorderWidth),
				size = (namewidth - 2 * (self.serviceBorderWidth + self.serviceNamePadding),
					r1.h - 2 * self.serviceBorderWidth),
				font = namefont, flags = namefontflag,
				text = service_name,
				color = serviceForeColor, color_sel = serviceForeColor,
				backcolor = serviceBackColor, backcolor_sel = serviceBackColor))

		# Service Borders
		if self.borderTopPix is not None and self.graphic:
			res.append(MultiContentEntryPixmapAlphaTest(
					pos = (r1.x, r1.y),
					size = (r1.w, self.serviceBorderWidth),
					png = self.borderTopPix,
					flags = BT_SCALE))
			res.append(MultiContentEntryPixmapAlphaTest(
					pos = (r2.x, r2.y),
					size = (r2.w, self.eventBorderWidth),
					png = self.borderTopPix,
					flags = BT_SCALE))
		if self.borderBottomPix is not None and self.graphic:
			res.append(MultiContentEntryPixmapAlphaTest(
					pos = (r1.x, r1.h-self.serviceBorderWidth),
					size = (r1.w, self.serviceBorderWidth),
					png = self.borderBottomPix,
					flags = BT_SCALE))
			res.append(MultiContentEntryPixmapAlphaTest(
					pos = (r2.x, r2.h-self.eventBorderWidth),
					size = (r2.w, self.eventBorderWidth),
					png = self.borderBottomPix,
					flags = BT_SCALE))
		if self.borderLeftPix is not None and self.graphic:
			res.append(MultiContentEntryPixmapAlphaTest(
					pos = (r1.x, r1.y),
					size = (self.serviceBorderWidth, r1.h),
					png = self.borderLeftPix,
					flags = BT_SCALE))
			res.append(MultiContentEntryPixmapAlphaTest(
					pos = (r2.x, r2.y),
					size = (self.eventBorderWidth, r2.h),
					png = self.borderLeftPix,
					flags = BT_SCALE))
		if self.borderRightPix is not None and self.graphic:
			res.append(MultiContentEntryPixmapAlphaTest(
					pos = (r1.w-self.serviceBorderWidth, r1.x),
					size = (self.serviceBorderWidth, r1.h),
					png = self.borderRightPix,
					flags = BT_SCALE))
			res.append(MultiContentEntryPixmapAlphaTest(
					pos = (r2.x + r2.w-self.eventBorderWidth, r2.y),
					size = (self.eventBorderWidth, r2.h),
					png = self.borderRightPix,
					flags = BT_SCALE))

		if self.graphic:
			if not selected and self.othEvPix:
				res.append(MultiContentEntryPixmapAlphaTest(
					pos = (r2.x + self.eventBorderWidth, r2.y + self.eventBorderWidth),
					size = (r2.w - 2 * self.eventBorderWidth, r2.h - 2 * self.eventBorderWidth),
					png = self.othEvPix,
					flags = BT_SCALE))
			elif selected and self.selEvPix:
				res.append(MultiContentEntryPixmapAlphaTest(
					pos = (r2.x + self.eventBorderWidth, r2.y + self.eventBorderWidth),
					size = (r2.w - 2 * self.eventBorderWidth, r2.h - 2 * self.eventBorderWidth),
					png = self.selEvPix,
					flags = BT_SCALE))
		else:
			res.append(MultiContentEntryText(
				pos = (left, top), size = (width, height),
				font = 1, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				text = "", color = None, color_sel = None,
				backcolor = self.backColor, backcolor_sel = self.backColorSelected,
				border_width = self.eventBorderWidth, border_color = self.borderColor))

		# Events for service
		if events:
			start = self.time_base + self.offs * self.time_epoch * 60
			end = start + self.time_epoch * 60

			now = time()
			for ev in events:  #(event_id, event_title, begin_time, duration)
				stime = ev[2]
				duration = ev[3]
				xpos, ewidth = self.calcEntryPosAndWidthHelper(stime, duration, start, end, width)
				clock_types = self.getPixmapForEntry(service, ev[0], stime, duration)
				if self.eventNameAlign.lower() == 'left':
					if self.eventNameWrap.lower() == 'yes':
						alignnment = RT_HALIGN_LEFT | RT_VALIGN_CENTER | RT_WRAP
					else:
						alignnment = RT_HALIGN_LEFT | RT_VALIGN_CENTER
				else:
					if self.eventNameWrap.lower() == 'yes':
						alignnment = RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_WRAP
					else:
						alignnment = RT_HALIGN_CENTER | RT_VALIGN_CENTER

				if stime <= now < (stime + duration):
					if clock_types is not None and clock_types == 2:
						foreColor = self.foreColorRecord
						backColor = self.backColorRecord
						foreColorSel = self.foreColorRecordSelected
						backColorSel = self.backColorRecordSelected
					else:
						foreColor = self.foreColorNow
						backColor = self.backColorNow
						foreColorSel = self.foreColorNowSelected
						backColorSel = self.backColorNowSelected
				else:
					foreColor = self.foreColor
					backColor = self.backColor
					foreColorSel = self.foreColorSelected
					backColorSel = self.backColorSelected
					if clock_types is not None and clock_types == 2:
						foreColor = self.foreColorRecord
						backColor = self.backColorRecord
						foreColorSel = self.foreColorRecordSelected
						backColorSel = self.backColorRecordSelected
					elif clock_types is not None and clock_types == 7:
						foreColor = self.foreColorZap
						backColor = self.backColorZap
						foreColorSel = self.foreColorZapSelected
						backColorSel = self.backColorZapSelected

				if selected and self.select_rect.x == xpos + left:
					if clock_types is not None:
						clocks = self.selclocks[clock_types]
					borderTopPix = self.borderSelectedTopPix
					borderLeftPix = self.borderSelectedLeftPix
					borderBottomPix = self.borderSelectedBottomPix
					borderRightPix = self.borderSelectedRightPix
					infoPix = self.selInfoPix
					if clock_types is not None and clock_types == 2:
						bgpng = self.recSelEvPix
					elif stime <= now < (stime + duration):
						bgpng = self.nowSelEvPix
					else:
						bgpng = self.selEvPix
				else:
					if clock_types is not None:
						clocks = self.clocks[clock_types]
					borderTopPix = self.borderTopPix
					borderLeftPix = self.borderLeftPix
					borderBottomPix = self.borderBottomPix
					borderRightPix = self.borderRightPix
					infoPix = self.InfoPix
					if stime <= now < (stime + duration):
						if clock_types is not None and clock_types == 2:
							bgpng = self.recordingEvPix
						else:
							bgpng = self.nowEvPix
					else:
						bgpng = self.othEvPix
						if clock_types is not None and clock_types == 2:
							bgpng = self.recEvPix
						elif clock_types is not None and clock_types == 7:
							bgpng = self.zapEvPix

				# event box background
				if bgpng is not None and self.graphic:
					backColor = None
					backColorSel = None
					res.append(MultiContentEntryPixmapAlphaTest(
						pos = (left + xpos + self.eventBorderWidth, top + self.eventBorderWidth),
						size = (ewidth - 2 * self.eventBorderWidth, height - 2 * self.eventBorderWidth),
						png = bgpng,
						flags = BT_SCALE))
				else:
					res.append(MultiContentEntryText(
						pos = (left + xpos, top), size = (ewidth, height),
						font = 1, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER,
						text = "", color = None, color_sel = None,
						backcolor = backColor, backcolor_sel = backColorSel,
						border_width = self.eventBorderWidth, border_color = self.borderColor))

				# event text
				evX = left + xpos + self.eventBorderWidth + self.eventNamePadding
				evY = top + self.eventBorderWidth
				evW = ewidth - 2 * (self.eventBorderWidth + self.eventNamePadding)
				evH = height - 2 * self.eventBorderWidth
				if self.type == EPG_TYPE_GRAPH:
					infowidth = config.epgselection.graph_infowidth.value
				elif self.type == EPG_TYPE_INFOBARGRAPH:
					infowidth = config.epgselection.infobar_infowidth.value
				if evW < infowidth and infoPix is not None:
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos = (evX, evY), size = (evW, evH),
						png = infoPix))
				else:
					res.append(MultiContentEntryText(
						pos = (evX, evY), size = (evW, evH),
						font = 1, flags = alignnment,
						text = ev[1],
						color = foreColor, color_sel = foreColorSel,
						backcolor = backColor, backcolor_sel = backColorSel))

				# event box borders
				if borderTopPix is not None and self.graphic:
					res.append(MultiContentEntryPixmapAlphaTest(
							pos = (left + xpos, top),
							size = (ewidth, self.eventBorderWidth),
							png = borderTopPix,
							flags = BT_SCALE))
				if borderBottomPix is not None and self.graphic:
					res.append(MultiContentEntryPixmapAlphaTest(
							pos = (left + xpos, height-self.eventBorderWidth),
							size = (ewidth, self.eventBorderWidth),
							png = borderBottomPix,
							flags = BT_SCALE))
				if borderLeftPix is not None and self.graphic:
					res.append(MultiContentEntryPixmapAlphaTest(
							pos = (left + xpos, top),
							size = (self.eventBorderWidth, height),
							png = borderLeftPix,
							flags = BT_SCALE))
				if borderRightPix is not None and self.graphic:
					res.append(MultiContentEntryPixmapAlphaTest(
							pos = (left + xpos + ewidth-self.eventBorderWidth, top),
							size = (self.eventBorderWidth, height),
							png = borderRightPix,
							flags = BT_SCALE))

				# recording icons
				if clock_types is not None and ewidth > 23:
					if clock_types in (1,6,11):
						if self.screenwidth and self.screenwidth == 1920:
							pos = (left+xpos+ewidth-17, top+height-28)
						else:
							pos = (left+xpos+ewidth-13, top+height-22)
					elif clock_types in (5,10,15):
						if self.screenwidth and self.screenwidth == 1920:
							pos = (left+xpos-2, top+height-28)
						else:
							pos = (left+xpos-8, top+height-23)
					else:
						if self.screenwidth and self.screenwidth == 1920:
							pos = (left+xpos+ewidth-29, top+height-28)
						else:
							pos = (left+xpos+ewidth-23, top+height-22)
					if self.screenwidth and self.screenwidth == 1920:
						res.append(MultiContentEntryPixmapAlphaBlend(
							pos = pos, size = (25, 25),
							png = clocks))
					else:
						res.append(MultiContentEntryPixmapAlphaBlend(
							pos = pos, size = (21, 21),
							png = clocks))
					if self.wasEntryAutoTimer and clock_types in (2,7,12):
						if self.screenwidth and self.screenwidth == 1920:
							res.append(MultiContentEntryPixmapAlphaBlend(
								pos = (pos[0]-29,pos[1]), size = (25, 25),
								png = self.autotimericon))
						else:
							res.append(MultiContentEntryPixmapAlphaBlend(
								pos = (pos[0]-22,pos[1]), size = (21, 21),
								png = self.autotimericon))
		return res

	def getSelectionPosition(self,serviceref):
		if self.type == EPG_TYPE_GRAPH:
			indx = int(self.getIndexFromService(serviceref))
			selx = self.select_rect.x+self.select_rect.w
			while indx+1 > config.epgselection.graph_itemsperpage.value:
				indx = indx - config.epgselection.graph_itemsperpage.value
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			indx = int(self.getIndexFromService(serviceref))
			selx = self.select_rect.x+self.select_rect.w
			while indx+1 > config.epgselection.infobar_itemsperpage.value:
				indx = indx - config.epgselection.infobar_itemsperpage.value
		elif self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_SIMILAR:
			indx = int(self.l.getCurrentSelectionIndex())
			selx = self.listWidth
			while indx+1 > config.epgselection.enhanced_itemsperpage.value:
				indx = indx - config.epgselection.enhanced_itemsperpage.value
		elif self.type == EPG_TYPE_MULTI:
			indx = int(self.l.getCurrentSelectionIndex())
			selx = self.listWidth
			while indx+1 > config.epgselection.multi_itemsperpage.value:
				indx = indx - config.epgselection.multi_itemsperpage.value
		elif self.type == EPG_TYPE_INFOBAR:
			indx = int(self.l.getCurrentSelectionIndex())
			selx = self.listWidth
			while indx+1 > config.epgselection.infobar_itemsperpage.value:
				indx = indx - config.epgselection.infobar_itemsperpage.value
		pos = self.instance.position().y()
		sely = int(pos)+(int(self.itemHeight)*int(indx))
		temp = int(self.instance.position().y())+int(self.listHeight)
		if int(sely) >= temp:
			sely = int(sely) - int(self.listHeight)
		return int(selx), int(sely)

	def selEntry(self, dir, visible = True):
		cur_service = self.cur_service    #(service, service_name, events, picon)
		self.recalcEntrySize()
		valid_event = self.cur_event is not None
		if cur_service:
			update = True
			entries = cur_service[2]
			if dir == 0: #current
				update = False
			elif dir == +1: #next
				if valid_event and self.cur_event + 1 < len(entries):
					self.cur_event += 1
				else:
					self.offs += 1
					self.fillGraphEPG(None) # refill
					return True
			elif dir == -1: #prev
				if valid_event and self.cur_event - 1 >= 0:
					self.cur_event -= 1
				elif self.offs > 0:
					self.offs -= 1
					self.fillGraphEPG(None) # refill
					return True
				elif self.time_base > time():
					self.time_base -= self.time_epoch * 60
					self.fillGraphEPG(None) # refill
					return True
			elif dir == +2: #next page
				self.offs += 1
				self.fillGraphEPG(None) # refill
				return True
			elif dir == -2: #prev
				if self.offs > 0:
					self.offs -= 1
					self.fillGraphEPG(None) # refill
					return True
			elif dir == +24:
				self.time_base += 86400
				self.fillGraphEPG(None, self.time_base) # refill
				return True
			elif dir == -24:
				now = time() - int(config.epg.histminutes.value) * 60
				if self.type == EPG_TYPE_GRAPH:
					if (self.time_base - 86400) >= now - now % (int(config.epgselection.graph_roundto.value) * 60):
						self.time_base -= 86400
						self.fillGraphEPG(None, self.time_base) # refill
						return True
				elif self.type == EPG_TYPE_INFOBARGRAPH:
					if (self.time_base - 86400) >= now - now % (int(config.epgselection.infobar_roundto.value) * 60):
						self.time_base -= 86400
						self.fillGraphEPG(None, self.time_base) # refill
						return True

		if cur_service and valid_event and (self.cur_event+1 <= len(entries)):
			entry = entries[self.cur_event] #(event_id, event_title, begin_time, duration)
			time_base = self.time_base + self.offs * self.time_epoch * 60
			xpos, width = self.calcEntryPosAndWidth(self.event_rect, time_base, self.time_epoch, entry[2], entry[3])
			self.select_rect = Rect(xpos ,0, width, self.event_rect.height)
			self.l.setSelectionClip(eRect(xpos, 0, width, self.event_rect.h), visible and update)
		else:
			self.select_rect = self.event_rect
			self.l.setSelectionClip(eRect(self.event_rect.x, self.event_rect.y, self.event_rect.w, self.event_rect.h), False)
		self.selectionChanged()
		return False

	def queryEPG(self, list, buildFunc=None):
		if self.epgcache is not None:
			if buildFunc is not None:
				return self.epgcache.lookupEvent(list, buildFunc)
			else:
				return self.epgcache.lookupEvent(list)
		return [ ]

	def fillSimilarList(self, refstr, event_id):
		# search similar broadcastings
		t = time()
		if event_id is None:
			return
		self.list = self.epgcache.search(('RIBND', 1024, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, refstr, event_id))
		if self.list and len(self.list):
			self.list.sort(key=lambda x: x[2])
		self.l.setList(self.list)
		self.selectionChanged()

	def fillSingleEPG(self, service):
		t = time()
		epg_time = t - config.epg.histminutes.value*60
		test = [ 'RIBDT', (service.ref.toString(), 0, epg_time, -1) ]
		self.list = self.queryEPG(test)
		self.l.setList(self.list)
		if t != epg_time:
			idx = 0
			for x in self.list:
				idx += 1
				if t < x[2]+x[3]:
					break
			self.instance.moveSelectionTo(idx-1)
		self.selectionChanged()

	def fillMultiEPG(self, services, stime=None):
		test = [ (service.ref.toString(), 0, stime) for service in services ]
		test.insert(0, 'X0RIBDTCn')
		self.list = self.queryEPG(test)
		self.l.setList(self.list)
		self.selectionChanged()

	def updateMultiEPG(self, direction):
		test = [ x[3] and (x[1], direction, x[3]) or (x[1], direction, 0) for x in self.list ]
		test.insert(0, 'XRIBDTCn')
		epg_data = self.queryEPG(test)
		cnt = 0
		for x in epg_data:
			changecount = self.list[cnt][0] + direction
			if changecount >= 0:
				if x[2] is not None:
					self.list[cnt] = (changecount, x[0], x[1], x[2], x[3], x[4], x[5], x[6])
			cnt+=1
		self.l.setList(self.list)
		self.selectionChanged()

	def fillGraphEPG(self, services, stime = None):
		if (self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH) and not self.graphicsloaded:
			if self.graphic:
				self.nowEvPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/CurrentEvent.png'))
				self.nowSelEvPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/SelectedCurrentEvent.png'))
				self.othEvPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/OtherEvent.png'))
				self.selEvPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/SelectedEvent.png'))
				self.othServPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/OtherService.png'))
				self.nowServPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/CurrentService.png'))
				self.recEvPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/RecordEvent.png'))
				self.recSelEvPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/SelectedRecordEvent.png'))
				self.recordingEvPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/RecordingEvent.png'))
				self.zapEvPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/ZapEvent.png'))
				self.zapSelEvPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/SelectedZapEvent.png'))

				self.borderTopPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/BorderTop.png'))
				self.borderBottomPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/BorderBottom.png'))
				self.borderLeftPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/BorderLeft.png'))
				self.borderRightPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/BorderRight.png'))
				self.borderSelectedTopPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/SelectedBorderTop.png'))
				self.borderSelectedBottomPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/SelectedBorderBottom.png'))
				self.borderSelectedLeftPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/SelectedBorderLeft.png'))
				self.borderSelectedRightPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/SelectedBorderRight.png'))

			self.InfoPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/information.png'))
			self.selInfoPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/SelectedInformation.png'))

			self.graphicsloaded = True

		if stime is not None:
			self.time_base = int(stime)
		if services is None:
			time_base = self.time_base + self.offs * self.time_epoch * 60
			test = [ (service[0], 0, time_base, self.time_epoch) for service in self.list ]
			serviceList = self.list
			piconIdx = 3
		else:
			self.cur_event = None
			self.cur_service = None
			test = [ (service.ref.toString(), 0, self.time_base, self.time_epoch) for service in services ]
			serviceList = services
			piconIdx = 0

		test.insert(0, 'XRnITBD') #return record, service ref, service name, event id, event title, begin time, duration
		epg_data = self.queryEPG(test)
		self.list = [ ]
		tmp_list = None
		service = ""
		sname = ""

		serviceIdx = 0
		for x in epg_data:
			if service != x[0]:
				if tmp_list is not None:
					picon = None if piconIdx == 0 else serviceList[serviceIdx][piconIdx]
					self.list.append((service, sname, tmp_list[0][0] is not None and tmp_list or None, picon))
					serviceIdx += 1
				service = x[0]
				sname = x[1]
				tmp_list = [ ]
			tmp_list.append((x[2], x[3], x[4], x[5])) #(event_id, event_title, begin_time, duration)
		if tmp_list and len(tmp_list):
			picon = None if piconIdx == 0 else serviceList[serviceIdx][piconIdx]
			self.list.append((service, sname, tmp_list[0][0] is not None and tmp_list or None, picon))
			serviceIdx += 1

		self.l.setList(self.list)
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

	def getEventRect(self):
		rc = self.event_rect
		return Rect( rc.left() + (self.instance and self.instance.position().x() or 0), rc.top(), rc.width(), rc.height() )

	def getServiceRect(self):
		rc = self.service_rect
		return Rect( rc.left() + (self.instance and self.instance.position().x() or 0), rc.top(), rc.width(), rc.height() )

	def getTimeEpoch(self):
		return self.time_epoch

	def getTimeBase(self):
		try:
			return int(self.time_base) + (int(self.offs) * int(self.time_epoch) * 60)
		except:
			return self.time_base

	def resetOffset(self):
		self.offs = 0

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

class TimelineText(HTMLComponent, GUIComponent):
	def __init__(self, type = EPG_TYPE_GRAPH, graphic=False):
		GUIComponent.__init__(self)
		self.type = type
		self.graphic = graphic
		self.l = eListboxPythonMultiContent()
		self.l.setSelectionClip(eRect(0,0,0,0))
		self.itemHeight = 30
		self.TlDate = None
		self.TlTime = None
		self.foreColor = 0xffc000
		self.borderColor = 0x000000
		self.backColor = 0x000000
		self.borderWidth = 1
		self.time_base = 0
		self.time_epoch = 0
		self.timelineFontName = "Regular"
		self.timelineFontSize = 20
		self.timelineAlign = 'left'
		self.datefmt = ""

	GUI_WIDGET = eListbox

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "foregroundColor":
					self.foreColor = parseColor(value).argb()
				elif attrib == "borderColor":
					self.borderColor = parseColor(value).argb()
				elif attrib == "backgroundColor":
					self.backColor = parseColor(value).argb()
				elif attrib == "font":
					self.l.setFont(0, parseFont(value,  ((1,1),(1,1)) ))
				elif attrib == "borderWidth":
					self.borderWidth = int(value)
				elif attrib == "TimelineFont":
					font = parseFont(value, ((1,1),(1,1)) )
					self.timelineFontName = font.family
					self.timelineFontSize = font.pointSize
				elif attrib == "TimelineAlignment":
					self.timelineAlign = value
				elif attrib == "itemHeight":
					self.itemHeight = int(value)
				else:
					attribs.append((attrib,value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.l.setItemHeight(self.itemHeight)
		if self.graphic:
			self.TlDate = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/TimeLineDate.png'))
			self.TlTime = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/TimeLineTime.png'))
		return rc

	def setTimeLineFontsize(self):
		if self.type == EPG_TYPE_GRAPH:
			self.l.setFont(0, gFont(self.timelineFontName, self.timelineFontSize + config.epgselection.graph_timelinefs.value))
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			self.l.setFont(0, gFont(self.timelineFontName, self.timelineFontSize + config.epgselection.infobar_timelinefs.value))

	def postWidgetCreate(self, instance):
		self.setTimeLineFontsize()
		instance.setContent(self.l)

	def setEntries(self, l, timeline_now, time_lines, force):
		event_rect = l.getEventRect()
		time_epoch = l.getTimeEpoch()
		time_base = l.getTimeBase()

		if self.timelineAlign.lower() == 'right':
			alignnment = RT_HALIGN_RIGHT | RT_VALIGN_TOP
		else:
			alignnment = RT_HALIGN_LEFT | RT_VALIGN_TOP

		if event_rect is None or time_epoch is None or time_base is None:
			return

		eventLeft = event_rect.left()

		res = [ None ]

		# Note: event_rect and service_rect are relative to the timeline_text position
		# while the time lines are relative to the GraphEPG screen position!
		if self.time_base != time_base or self.time_epoch != time_epoch or force:
			service_rect = l.getServiceRect()
			time_steps = 60 if time_epoch > 180 else 30
			num_lines = time_epoch / time_steps
			incWidth = event_rect.width() / num_lines
			timeStepsCalc = time_steps * 60

			nowTime = localtime(time())
			begTime = localtime(time_base)
			ServiceWidth = service_rect.width()
			if nowTime[2] != begTime[2]:
				if ServiceWidth > 179:
					datestr = strftime("%A %d %B", localtime(time_base))
				elif ServiceWidth > 139:
					datestr = strftime("%a %d %B", localtime(time_base))
				elif ServiceWidth > 129:
					datestr = strftime("%a %d %b", localtime(time_base))
				elif ServiceWidth > 119:
					datestr = strftime("%a %d", localtime(time_base))
				elif ServiceWidth > 109:
					datestr = strftime("%A", localtime(time_base))
				else:
					datestr = strftime("%a", localtime(time_base))
			else:
				datestr = '%s'%(_("Today"))

			foreColor = self.foreColor
			backColor = self.backColor
			bgpng = self.TlDate
			if bgpng is not None and self.graphic:
				backColor = None
				backColorSel = None
				res.append(MultiContentEntryPixmapAlphaTest(
					pos = (0, 0),
					size = (service_rect.width(), self.listHeight),
					png = bgpng,
					flags = BT_SCALE))
			else:
				res.append( MultiContentEntryText(
					pos = (0, 0),
					size = (service_rect.width(), self.listHeight),
					color = foreColor,
					backcolor = backColor,
					border_width = self.borderWidth, border_color = self.borderColor))

			res.append(MultiContentEntryText(
				pos = (5, 0),
				size = (service_rect.width()-15, self.listHeight),
				font = 0, flags = alignnment,
				text = _(datestr),
				color = foreColor,
				backcolor = backColor))

			bgpng = self.TlTime
			xpos = 0 # eventLeft
			if bgpng is not None and self.graphic:
				backColor = None
				backColorSel = None
				res.append(MultiContentEntryPixmapAlphaTest(
					pos = (service_rect.width(), 0),
					size = (event_rect.width(), self.listHeight),
					png = bgpng,
					flags = BT_SCALE))
			else:
				res.append( MultiContentEntryText(
					pos = (service_rect.width(), 0),
					size = (event_rect.width(), self.listHeight),
					color = foreColor,
					backcolor = backColor,
					border_width = self.borderWidth, border_color = self.borderColor))

			for x in range(0, num_lines):
				ttime = localtime(time_base + (x*timeStepsCalc))
				if (self.type == EPG_TYPE_GRAPH and config.epgselection.graph_timeline24h.value) or (self.type == EPG_TYPE_INFOBARGRAPH and config.epgselection.infobar_timeline24h.value):
					timetext = strftime("%H:%M", localtime(time_base + x*timeStepsCalc))
				else:
					if int(strftime("%H",ttime)) > 12:
						timetext = strftime("%-I:%M",ttime) + _('pm')
					else:
						timetext = strftime("%-I:%M",ttime) + _('am')
				res.append(MultiContentEntryText(
					pos = (service_rect.width() + xpos, 0),
					size = (incWidth, self.listHeight),
					font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP,
					text = timetext,
					color = foreColor,
					backcolor = backColor))
				line = time_lines[x]
				old_pos = line.position
				line.setPosition(xpos + eventLeft, old_pos[1])
				line.visible = True
				xpos += incWidth
			for x in range(num_lines, MAX_TIMELINES):
				time_lines[x].visible = False
			self.l.setList([res])
			self.time_base = time_base
			self.time_epoch = time_epoch

		now = time()
		if time_base <= now < (time_base + time_epoch * 60):
			xpos = int((((now - time_base) * event_rect.width()) / (time_epoch * 60)) - (timeline_now.instance.size().width() / 2))
			old_pos = timeline_now.position
			new_pos = (xpos + eventLeft, old_pos[1])
			if old_pos != new_pos:
				timeline_now.setPosition(new_pos[0], new_pos[1])
			timeline_now.visible = True
		else:
			timeline_now.visible = False

class EPGBouquetList(HTMLComponent, GUIComponent):
	def __init__(self, graphic=False):
		GUIComponent.__init__(self)
		self.graphic = graphic
		self.l = eListboxPythonMultiContent()
		self.l.setBuildFunc(self.buildEntry)

		self.onSelChanged = [ ]

		self.foreColor = 0xffffff
		self.foreColorSelected = 0xffffff
		self.backColor = 0x2D455E
		self.backColorSelected = 0xd69600

		self.borderColor = 0xC0C0C0
		self.BorderWidth = 1

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
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "font":
					font = parseFont(value, ((1,1),(1,1)) )
					self.bouquetFontName = font.family
					self.bouquetFontSize = font.pointSize
				elif attrib == "foregroundColor":
					self.foreColor = parseColor(value).argb()
				elif attrib == "backgroundColor":
					self.backColor = parseColor(value).argb()
				elif attrib == "foregroundColorSelected":
					self.foreColorSelected = parseColor(value).argb()
				elif attrib == "backgroundColorSelected":
					self.backColorSelected = parseColor(value).argb()
				elif attrib == "borderColor":
					self.borderColor = parseColor(value).argb()
				elif attrib == "borderWidth":
					self.BorderWidth = int(value)
				elif attrib == "itemHeight":
					self.itemHeight = int(value)
				else:
					attribs.append((attrib,value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.l.setItemHeight(self.itemHeight)
		return rc

	GUI_WIDGET = eListbox

	def getCurrentBouquet(self):
		return self.l.getCurrentSelection()[0]

	def getCurrentBouquetService(self):
		return self.l.getCurrentSelection()[1]

	def setCurrentBouquet(self, CurrentBouquetService):
		self.CurrentBouquetService = CurrentBouquetService

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
		self.setBouquetFontsize()

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
		return Rect( rc.left() + (self.instance and self.instance.position().x() or 0), rc.top(), rc.width(), rc.height() )

	def buildEntry(self, name, func):
		r1 = self.bouquet_rect
		left = r1.x
		top = r1.y
		# width = (len(name)+5)*8
		width = r1.w
		height = r1.h
		selected = self.CurrentBouquetService == func

		if self.bouquetNameAlign.lower() == 'left':
			if self.bouquetNameWrap.lower() == 'yes':
				alignnment = RT_HALIGN_LEFT | RT_VALIGN_CENTER | RT_WRAP
			else:
				alignnment = RT_HALIGN_LEFT | RT_VALIGN_CENTER
		else:
			if self.bouquetNameWrap.lower() == 'yes':
				alignnment = RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_WRAP
			else:
				alignnment = RT_HALIGN_CENTER | RT_VALIGN_CENTER

		res = [ None ]

		if selected:
			if self.graphic:
				borderTopPix = self.borderSelectedTopPix
				borderLeftPix = self.borderSelectedLeftPix
				borderBottomPix = self.borderSelectedBottomPix
				borderRightPix = self.borderSelectedRightPix
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
				borderTopPix = self.borderTopPix
				borderLeftPix = self.borderLeftPix
				borderBottomPix = self.borderBottomPix
				borderRightPix = self.borderRightPix
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
				pos = (left + self.BorderWidth, top + self.BorderWidth),
				size = (width - 2 * self.BorderWidth, height - 2 * self.BorderWidth),
				png = bgpng,
				flags = BT_SCALE))
		else:
			res.append(MultiContentEntryText(
				pos = (left , top), size = (width, height),
				font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				text = "", color = None, color_sel = None,
				backcolor = backColor, backcolor_sel = backColorSel,
				border_width = self.BorderWidth, border_color = self.borderColor))

		evX = left + self.BorderWidth + self.bouquetNamePadding
		evY = top + self.BorderWidth
		evW = width - 2 * (self.BorderWidth + self.bouquetNamePadding)
		evH = height - 2 * self.BorderWidth

		res.append(MultiContentEntryText(
			pos = (evX, evY), size = (evW, evH),
			font = 0, flags = alignnment,
			text = name,
			color = foreColor, color_sel = foreColorSel,
			backcolor = backColor, backcolor_sel = backColorSel))

		# Borders
		if self.graphic:
			if borderTopPix is not None:
				res.append(MultiContentEntryPixmapAlphaTest(
						pos = (left, r1.y),
						size = (r1.w, self.BorderWidth),
						png = borderTopPix,
						flags = BT_SCALE))
			if borderBottomPix is not None:
				res.append(MultiContentEntryPixmapAlphaTest(
						pos = (left, r1.h-self.BorderWidth),
						size = (r1.w, self.BorderWidth),
						png = borderBottomPix,
						flags = BT_SCALE))
			if borderLeftPix is not None:
				res.append(MultiContentEntryPixmapAlphaTest(
						pos = (left, r1.y),
						size = (self.BorderWidth, r1.h),
						png = borderLeftPix,
						flags = BT_SCALE))
			if borderRightPix is not None:
				res.append(MultiContentEntryPixmapAlphaTest(
						pos = (r1.w-self.BorderWidth, left),
						size = (self.BorderWidth, r1.h),
						png = borderRightPix,
						flags = BT_SCALE))

		return res

	def fillBouquetList(self, bouquets):
		if self.graphic and not self.graphicsloaded:
			self.othPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/OtherEvent.png'))
			self.selPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/SelectedCurrentEvent.png'))

			self.borderTopPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/BorderTop.png'))
			self.borderBottomPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/BorderLeft.png'))
			self.borderLeftPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/BorderBottom.png'))
			self.borderRightPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/BorderRight.png'))
			self.borderSelectedTopPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/SelectedBorderTop.png'))
			self.borderSelectedLeftPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/SelectedBorderLeft.png'))
			self.borderSelectedBottomPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/SelectedBorderBottom.png'))
			self.borderSelectedRightPix = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'epg/SelectedBorderRight.png'))

			self.graphicsloaded = True
		self.bouquetslist = bouquets
		self.l.setList(self.bouquetslist)
		self.selectionChanged()
		self.CurrentBouquetService = self.getCurrentBouquetService()
