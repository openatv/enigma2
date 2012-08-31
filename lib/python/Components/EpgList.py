from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from Components.config import config, ConfigSelectionNumber
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend, MultiContentEntryPixmapAlphaTest
from Components.Renderer.Picon import getPiconName

from skin import parseColor, parseFont
from enigma import eEPGCache, eListbox, eListboxPythonMultiContent, ePicLoad, gFont, eRect, eSize, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP

from Tools.Alternatives import CompareWithAlternatives
from Tools.LoadPixmap import LoadPixmap

from time import localtime, time, strftime
from ServiceReference import ServiceReference
from Tools.Directories import pathExists, resolveFilename, SCOPE_CURRENT_SKIN
from os import listdir, path

EPG_TYPE_SINGLE = 0
EPG_TYPE_MULTI = 1
EPG_TYPE_SIMILAR = 2
EPG_TYPE_ENHANCED = 3
EPG_TYPE_INFOBAR = 4
EPG_TYPE_GRAPH = 5

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
	def __init__(self, type = EPG_TYPE_SINGLE, selChangedCB = None, timer = None, time_epoch = 120, overjump_empty = False):
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
		self.picload = ePicLoad()

		self.overjump_empty = overjump_empty
		self.timer = timer
		self.onSelChanged = [ ]
		if selChangedCB is not None:
			self.onSelChanged.append(selChangedCB)
		GUIComponent.__init__(self)
		self.type = type
		self.l = eListboxPythonMultiContent()

		if type == EPG_TYPE_SINGLE or type == EPG_TYPE_ENHANCED or type == EPG_TYPE_INFOBAR:
			self.l.setBuildFunc(self.buildSingleEntry)
		elif type == EPG_TYPE_MULTI:
			self.l.setBuildFunc(self.buildMultiEntry)
		elif type == EPG_TYPE_GRAPH:
			self.l.setBuildFunc(self.buildGraphEntry)
		else:
			assert(type == EPG_TYPE_SIMILAR)
			self.l.setBuildFunc(self.buildSimilarEntry)
		self.epgcache = eEPGCache.getInstance()
		self.clock_pixmap = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock.png'))
		self.clock_add_pixmap = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_add.png'))
		self.clock_pre_pixmap = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_pre.png'))
		self.clock_post_pixmap = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_post.png'))
		self.clock_prepost_pixmap = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_prepost.png'))

		self.nowEvPix = None
		self.nowSelEvPix = None
		self.othEvPix = None
		self.selEvPix = None
		self.nowServPix = None
		self.recEvPix = None
		self.recSelEvPix = None
		self.zapEvPix = None
		self.zapSelEvPix = None

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
		self.serviceFontSizeGraph = 20
		self.eventFontNameGraph = "Regular"
		self.eventFontSizeGraph = 18
		self.eventFontNameSingle = "Regular"
		self.eventFontSizeSingle = 22
		self.eventFontNameMulti = "Regular"
		self.eventFontSizeMulti = 22
		self.eventFontNameInfobar = "Regular"
		self.eventFontSizeInfobar = 22

		self.listHeight = None
		self.listWidth = None
		self.serviceBorderWidth = 1
		self.serviceNamePadding = 3
		self.eventBorderWidth = 1
		self.eventNamePadding = 3
		self.eventNameAlign = 'left'

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "ServiceFont":
					font = parseFont(value, ((1,1),(1,1)) )
					self.serviceFontNameGraph = font.family
					self.serviceFontSizeGraph = font.pointSize
				elif attrib == "EntryFontGraphical":
					font = parseFont(value, ((1,1),(1,1)) )
					self.eventFontNameGraph = font.family
					self.eventFontSize = font.pointSize
				elif attrib == "EntryFontAlignment":
					self.eventNameAlign = value
				elif attrib == "EventFontSingle":
					font = parseFont(value, ((1,1),(1,1)) )
					self.eventFontNameSingle = font.family
					self.eventFontSizeSingle = font.pointSize
				elif attrib == "EventFontInfobar":
					font = parseFont(value, ((1,1),(1,1)) )
					self.eventFontNameInfobar = font.family
					self.eventFontSizeInfobar = font.pointSize

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

	def moveUp(self):
		self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)

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

	def getCurrent(self):
		if self.type == EPG_TYPE_GRAPH:
			if self.cur_service is None:
				return (None, None)
			old_service = self.cur_service  #(service, service_name, events, picon)
			events = self.cur_service[2]
			refstr = self.cur_service[0]
			if self.cur_event is None or not events or not len(events):
				return (None, ServiceReference(refstr))
			event = events[self.cur_event] #(event_id, event_title, begin_time, duration)
			eventid = event[0]
			service = ServiceReference(refstr)
			event = self.getEventFromId(service, eventid) # get full event info
			return (event, service)
		else:
			idx = 0
			if self.type == EPG_TYPE_MULTI:
				idx += 1
			tmp = self.l.getCurrentSelection()
			if tmp is None:
				return (None, None)
			eventid = tmp[idx+1]
			service = ServiceReference(tmp[idx])
			event = self.getEventFromId(service, eventid)
			return ( event, service )

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
			events = old_service[2]
			cur_event = events[self.cur_event] #(event_id, event_title, begin_time, duration)
			if cur_event[2] > last_time:
				last_time = cur_event[2]
		if cur_service:
			self.cur_event = 0
			events = cur_service[2]
			best = None
			if events and len(events):
				best_diff = 0
				idx = 0
				for event in events: #iterate all events
					ev_time = event[2]
					if ev_time < time_base:
						ev_time = time_base
					diff = abs(ev_time - last_time)
					if best is None or (diff < best_diff):
						best = idx
						best_diff = diff
					if best is not None and ev_time > last_time:
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
 		if self.type == EPG_TYPE_GRAPH:
			if self.listHeight > 0:
				itemHeight = self.listHeight / config.epgselection.itemsperpage_vixepg.getValue()
			else:
				itemHeight = 54 # some default (270/5)
			if config.epgselection.heightswitch.getValue():
				if ((self.listHeight / config.epgselection.itemsperpage_vixepg.getValue()) / 3) >= 27:
					tmp_itemHeight = ((self.listHeight / config.epgselection.itemsperpage_vixepg.getValue()) / 3)
				elif ((self.listHeight / config.epgselection.itemsperpage_vixepg.getValue()) / 2) >= 27:
					tmp_itemHeight = ((self.listHeight / config.epgselection.itemsperpage_vixepg.getValue()) / 2)
				else:
					tmp_itemHeight = 27
				if tmp_itemHeight < itemHeight:
					itemHeight = tmp_itemHeight
				else:
					if ((self.listHeight / config.epgselection.itemsperpage_vixepg.getValue()) * 3) <= 45:
						itemHeight = ((self.listHeight / config.epgselection.itemsperpage_vixepg.getValue()) * 3)
					elif ((self.listHeight / config.epgselection.itemsperpage_vixepg.getValue()) * 2) <= 45:
						itemHeight = ((self.listHeight / config.epgselection.itemsperpage_vixepg.getValue()) * 2)
					else:
						itemHeight = 45
			self.l.setItemHeight(itemHeight)
			self.instance.resize(eSize(self.listWidth, self.listHeight / itemHeight * itemHeight))

			self.picload.setPara((self.listWidth, itemHeight - 2 * self.eventBorderWidth, 0, 0, 1, 1, "#00000000"))
			self.picload.startDecode(resolveFilename(SCOPE_CURRENT_SKIN, 'epg/CurrentEvent.png'), 0, 0, False)
			self.nowEvPix = self.picload.getData()
			self.picload.startDecode(resolveFilename(SCOPE_CURRENT_SKIN, 'epg/SelectedCurrentEvent.png'), 0, 0, False)
			self.nowSelEvPix = self.picload.getData()

			self.picload.startDecode(resolveFilename(SCOPE_CURRENT_SKIN, 'epg/OtherEvent.png'), 0, 0, False)
			self.othEvPix = self.picload.getData()

			self.picload.startDecode(resolveFilename(SCOPE_CURRENT_SKIN, 'epg/SelectedEvent.png'), 0, 0, False)
			self.selEvPix = self.picload.getData()

			self.picload.startDecode(resolveFilename(SCOPE_CURRENT_SKIN, 'epg/CurrentService.png'), 0, 0, False)
			self.nowServPix = self.picload.getData()

			self.picload.startDecode(resolveFilename(SCOPE_CURRENT_SKIN, 'epg/RecordEvent.png'), 0, 0, False)
			self.recEvPix = self.picload.getData()
			self.picload.startDecode(resolveFilename(SCOPE_CURRENT_SKIN, 'epg/SelectedRecordEvent.png'), 0, 0, False)
			self.recSelEvPix = self.picload.getData()

			self.picload.startDecode(resolveFilename(SCOPE_CURRENT_SKIN, 'epg/ZapEvent.png'), 0, 0, False)
			self.zapEvPix = self.picload.getData()
			self.picload.startDecode(resolveFilename(SCOPE_CURRENT_SKIN, 'epg/SelectedZapEvent.png'), 0, 0, False)
			self.zapSelEvPix = self.picload.getData()

		elif self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_SIMILAR:
			if self.listHeight > 0:
				itemHeight = self.listHeight / config.epgselection.itemsperpage_enhanced.getValue()
			else:
				itemHeight = 32
			self.l.setItemHeight(itemHeight)
			self.instance.resize(eSize(self.listWidth, self.listHeight / itemHeight * itemHeight))
		elif self.type == EPG_TYPE_MULTI:
			if self.listHeight > 0:
				itemHeight = self.listHeight / config.epgselection.itemsperpage_multi.getValue()
			else:
				itemHeight = 32
			self.l.setItemHeight(itemHeight)
			self.instance.resize(eSize(self.listWidth, self.listHeight / itemHeight * itemHeight))
		elif self.type == EPG_TYPE_INFOBAR:
			if self.listHeight > 0:
				itemHeight = float(self.listHeight / config.epgselection.itemsperpage_infobar.getValue())
			else:
				itemHeight = 32
			self.l.setItemHeight(int(itemHeight))

	def setServiceFontsize(self):
		self.l.setFont(0, gFont(self.serviceFontNameGraph, self.serviceFontSizeGraph + config.epgselection.serv_fontsize_vixepg.getValue()))

	def setEventFontsize(self):
		if self.type == EPG_TYPE_GRAPH:
			self.l.setFont(1, gFont(self.eventFontNameGraph, self.eventFontSizeGraph + config.epgselection.ev_fontsize_vixepg.getValue()))
		elif self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_SIMILAR:
			self.l.setFont(0, gFont(self.eventFontNameSingle, self.eventFontSizeSingle + config.epgselection.ev_fontsize_enhanced.getValue()))
		elif self.type == EPG_TYPE_MULTI:
			self.l.setFont(0, gFont(self.eventFontNameMulti, self.eventFontSizeMulti + config.epgselection.ev_fontsize_multi.getValue()))
			self.l.setFont(1, gFont(self.eventFontNameMulti, self.eventFontSizeMulti - 4 + config.epgselection.ev_fontsize_multi.getValue()))
		elif self.type == EPG_TYPE_INFOBAR:
			self.l.setFont(0, gFont(self.eventFontNameInfobar, self.eventFontSizeInfobar + config.epgselection.ev_fontsize_infobar.getValue()))

	def postWidgetCreate(self, instance):
		if self.type == EPG_TYPE_GRAPH:
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
		if self.type == EPG_TYPE_GRAPH:
			instance.selectionChanged.get().remove(self.serviceChanged)
			instance.setContent(None)
		else:
			instance.selectionChanged.get().remove(self.selectionChanged)
			instance.setContent(None)

	def recalcEntrySize(self):
		esize = self.l.getItemSize()
		width = esize.width()
		height = esize.height()

		if self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_INFOBAR:
			if self.type == EPG_TYPE_INFOBAR:
				fontwdith = config.epgselection.ev_fontsize_infobar.getValue()
			else:
				fontwdith = config.epgselection.ev_fontsize_enhanced.getValue()
			self.weekday_rect = Rect(0, 0, float(width / 100) * (10 + (fontwdith / 2)) , height)
			self.datetime_rect = Rect(self.weekday_rect.width(), 0, float(width / 100) * (25 + fontwdith), height)
			self.descr_rect = Rect(self.datetime_rect.left() + self.datetime_rect.width(), 0, float(width / 100) * (70 + fontwdith), height)
		elif self.type == EPG_TYPE_MULTI:
			xpos = 0;
			w = width / 10 * 3;
			self.service_rect = Rect(xpos, 0, w-10, height)
			xpos += w;
			w = width / 10 * 2;
			self.start_end_rect = Rect(xpos, 0, w-10, height)
			self.progress_rect = Rect(xpos, 4, w-10, height-8)
			xpos += w
			w = width / 10 * 5;
			self.descr_rect = Rect(xpos, 0, width, height)
		elif self.type == EPG_TYPE_GRAPH:
			servicew = 0
			piconw = 0
			servicewtmp = width / 10 * 2
			config.epgselection.servicewidth = ConfigSelectionNumber(default = servicewtmp, stepwidth = 1, min = 70, max = 500, wraparound = True)
			piconwtmp = 2 * height - 2 * self.serviceBorderWidth  # FIXME: could do better...
			config.epgselection.piconwidth = ConfigSelectionNumber(default = piconwtmp, stepwidth = 1, min = 70, max = 500, wraparound = True)
			if self.showServiceTitle:
				servicew = config.epgselection.servicewidth.getValue()
			if self.showPicon:
				piconw = config.epgselection.piconwidth.getValue()
			w = (piconw + servicew)
			self.service_rect = Rect(0, 0, w, height)
			self.event_rect = Rect(w, 0, width - w, height)
			piconHeight = height - 2 * self.serviceBorderWidth
			piconWidth = piconw
			if piconWidth > w - 2 * self.serviceBorderWidth:
				piconWidth = w - 2 * self.serviceBorderWidth
			self.picon_size = eSize(piconWidth, piconHeight)
		else: # EPG_TYPE_SIMILAR
			fontwdith = config.epgselection.ev_fontsize_enhanced.getValue()
			self.weekday_rect = Rect(0, 0, float(width / 100) * (10 + (fontwdith / 2)) , height)
			self.datetime_rect = Rect(self.weekday_rect.width(), 0, float(width / 100) * (25 + fontwdith), height)
			self.service_rect = Rect(self.datetime_rect.left() + self.datetime_rect.width(), 0, float(width / 100) * (70 + fontwdith), height)

	def calcEntryPosAndWidthHelper(self, stime, duration, start, end, width):
		xpos = (stime - start) * width / (end - start)
		ewidth = (stime + duration - start) * width / (end - start)
		ewidth -= xpos;
		if xpos < 0:
			ewidth += xpos;
			xpos = 0;
		if (xpos + ewidth) > width:
			ewidth = width - xpos
		return xpos, ewidth

	def calcEntryPosAndWidth(self, event_rect, time_base, time_epoch, ev_start, ev_duration):
		xpos, width = self.calcEntryPosAndWidthHelper(ev_start, ev_duration, time_base, time_base + time_epoch * 60, event_rect.width())
		return xpos + event_rect.left(), width

	def buildSingleEntry(self, service, eventId, beginTime, duration, EventName):
		(clock_pic, rec) = self.getPixmapForEntry(service, eventId, beginTime, duration)
		r1 = self.weekday_rect
		r2 = self.datetime_rect
		r3 = self.descr_rect
		t = localtime(beginTime)

		res = [
			None, # no private data needed
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _(strftime("%a", t))),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, r2.w, r1.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, strftime("%e/%m, %-H:%M", t))
		]
		if rec:
			res.extend((
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, r3.x, r3.y, 21, 21, clock_pic),
				(eListboxPythonMultiContent.TYPE_TEXT, r3.x + 25, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, EventName)
			))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, EventName))
 		return res

	def buildSimilarEntry(self, service, eventId, beginTime, service_name, duration):
		(clock_pic, rec) = self.getPixmapForEntry(service, eventId, beginTime, duration)
		r1 = self.weekday_rect
		r2 = self.datetime_rect
		r3 = self.service_rect
		t = localtime(beginTime)
		res = [
			None,  # no private data needed
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _(strftime("%a", t))),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, r2.w, r1.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, strftime("%e/%m, %-H:%M", t))
		]
		if rec:
			res.extend((
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, r3.x, r3.y, 21, 21, clock_pic),
				(eListboxPythonMultiContent.TYPE_TEXT, r3.x + 25, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, service_name)
			))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, service_name))
		return res

	def buildMultiEntry(self, changecount, service, eventId, beginTime, duration, EventName, nowTime, service_name):
		(clock_pic, rec) = self.getPixmapForEntry(service, eventId, beginTime, duration)
		r1 = self.service_rect
		r2 = self.progress_rect
		r3 = self.descr_rect
		r4 = self.start_end_rect
		res = [ None ] # no private data needed
		if rec:
			res.extend((
				(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w-21, r1.h, 0, RT_HALIGN_LEFT, service_name),
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, r1.x+r1.w-16, r1.y, 21, 21, clock_pic)
			))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_LEFT, service_name))
		if beginTime is not None:
			if nowTime < beginTime:
				begin = localtime(beginTime)
				end = localtime(beginTime+duration)
				res.extend((
					(eListboxPythonMultiContent.TYPE_TEXT, r4.x, r4.y, r4.w, r4.h, 1, RT_HALIGN_CENTER|RT_VALIGN_CENTER, "%02d.%02d - %02d.%02d"%(begin[3],begin[4],end[3],end[4])),
					(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT, EventName)
				))
			else:
				percent = (nowTime - beginTime) * 100 / duration
				res.extend((
					(eListboxPythonMultiContent.TYPE_PROGRESS, r2.x, r2.y, r2.w, r2.h, percent),
					(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT, EventName)
				))
		return res

	def buildGraphEntry(self, service, service_name, events, picon):
		r1 = self.service_rect
		r2 = self.event_rect
		selected = self.cur_service[0] == service

		# Picon and Service name
		if CompareWithAlternatives(service, self.currentlyPlaying and self.currentlyPlaying.toString()):
			serviceForeColor = self.foreColorServiceNow
			serviceBackColor = self.backColorServiceNow
			bgpng = self.nowServPix
			if bgpng is not None and config.epgselection.graphics_mode.value == "graphics":    # bacground for service rect
				serviceBackColor = None
		else:
			serviceForeColor = self.foreColorService
			serviceBackColor = self.backColorService
			bgpng = self.othEvPix
			if bgpng is not None and config.epgselection.graphics_mode.value == "graphics":    # bacground for service rect
				serviceBackColor = None

		res = [ None ]
		if bgpng is not None and config.epgselection.graphics_mode.value == "graphics":    # bacground for service rect
			res.append(MultiContentEntryPixmapAlphaTest(
					pos = (r1.x + self.serviceBorderWidth, r1.y + self.serviceBorderWidth),
					size = (r1.w - 2 * self.serviceBorderWidth, r1.h - 2 * self.serviceBorderWidth),
					png = bgpng))
		else:
			res.append(MultiContentEntryText(
					pos  = (r1.x, r1.y),
					size = (r1.w, r1.h),
					font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER,
					text = "",
					color = serviceForeColor, color_sel = serviceForeColor,
					backcolor = serviceBackColor, backcolor_sel = serviceBackColor,
					border_width = self.serviceBorderWidth, border_color = self.borderColorService) )

		displayPicon = None
		if self.showPicon:
			if picon is None: # go find picon and cache its location
				picon = getPiconName(service)
				curIdx = self.l.getCurrentSelectionIndex()
				self.list[curIdx] = (service, service_name, events, picon)
			piconWidth = self.picon_size.width()
			piconHeight = self.picon_size.height()
			if picon != "":
				self.picload.setPara((piconWidth, piconHeight, 0, 0, 1, 1, "#00000000"))
				self.picload.startDecode(picon, 0, 0, False)
				displayPicon = self.picload.getData()
			if displayPicon is not None:
				res.append(MultiContentEntryPixmapAlphaTest(
					pos = (r1.x + self.serviceBorderWidth, r1.y + self.serviceBorderWidth),
					size = (piconWidth, piconHeight),
					png = displayPicon,
					backcolor = None, backcolor_sel = None) )
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

		# Events for service
		backColorSel = self.backColorSelected
		if events:
			start = self.time_base + self.offs * self.time_epoch * 60
			end = start + self.time_epoch * 60
			left = r2.x
			top = r2.y
			width = r2.w
			height = r2.h

			now = time()
			for ev in events:  #(event_id, event_title, begin_time, duration)
				stime = ev[2]
				duration = ev[3]
				xpos, ewidth = self.calcEntryPosAndWidthHelper(stime, duration, start, end, width)
				rec = stime and self.timer.isInTimer(ev[0], stime, duration, service)
				rectype = self.GraphEPGRecRed(service, ev[2], ev[3], ev[0])
				if self.eventNameAlign.lower() == 'left':
					alignnment = RT_HALIGN_LEFT | RT_VALIGN_CENTER | RT_WRAP
				else:
					alignnment = RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_WRAP

				if selected and self.select_rect.x == xpos + left:
					if stime <= now and now < (stime + duration):
						foreColor = self.foreColorNow
						backColor = self.backColorNow
						foreColorSel = self.foreColorNowSelected
						backColorSel = self.backColorNowSelected
						bgpng = self.nowSelEvPix
						if bgpng is not None and config.epgselection.graphics_mode.value == "graphics":
							backColor = None
							backColorSel = None
					else:
						foreColor = self.foreColor
						backColor = self.backColor
						foreColorSel = self.foreColorSelected
						backColorSel = self.backColorSelected
						bgpng = self.selEvPix
						if bgpng is not None and config.epgselection.graphics_mode.value == "graphics":
							backColor = None
							backColorSel = None
				elif stime <= now and now < (stime + duration):
					foreColor = self.foreColorNow
					backColor = self.backColorNow
					foreColorSel = self.foreColorNowSelected
					backColorSel = self.backColorNowSelected
					bgpng = self.nowEvPix
					if bgpng is not None and config.epgselection.graphics_mode.value == "graphics":
						backColor = None
						backColorSel = None
				else:
					backColor = self.backColor
					foreColor = self.foreColor
					foreColorSel = self.foreColorSelected
					backColorSel = self.backColorSelected
					bgpng = self.othEvPix
					if bgpng is not None and config.epgselection.graphics_mode.value == "graphics":
						backColor = None
						backColorSel = None

				if rec and selected and self.select_rect.x == xpos + left:
					if rectype == "record":
						foreColor = self.foreColorRecord
						backColor = self.backColorRecord
						foreColorSel = self.foreColorRecordSelected
						backColorSel = self.backColorRecordSelected
						bgpng = self.recSelEvPix
						if bgpng is not None and config.epgselection.graphics_mode.value == "graphics":
							backColor = None
							backColorSel = None
					elif rectype == "justplay":
						foreColor = self.foreColorZap
						backColor = self.backColorZap
						foreColorSel = self.foreColorZapSelected
						backColorSel = self.backColorZapSelected
						bgpng = self.zapSelEvPix
						if bgpng is not None and config.epgselection.graphics_mode.value == "graphics":
							backColor = None
							backColorSel = None
				elif rec:
					if rectype == "record":
						foreColor = self.foreColorRecord
						backColor = self.backColorRecord
						foreColorSel = self.foreColorRecordSelected
						backColorSel = self.backColorRecordSelected
						bgpng = self.recEvPix
						if bgpng is not None and config.epgselection.graphics_mode.value == "graphics":
							backColor = None
							backColorSel = None
					elif rectype == "justplay":
						foreColor = self.foreColorZap
						backColor = self.backColorZap
						foreColorSel = self.foreColorZapSelected
						backColorSel = self.backColorZapSelected
						bgpng = self.zapEvPix
						if bgpng is not None and config.epgselection.graphics_mode.value == "graphics":
							backColor = None
							backColorSel = None

				# event box background
				if bgpng is not None and config.epgselection.graphics_mode.value == "graphics":
					res.append(MultiContentEntryPixmapAlphaTest(
						pos = (left + xpos + self.eventBorderWidth, top + self.eventBorderWidth),
						size = (ewidth - 2 * self.eventBorderWidth, height - 2 * self.eventBorderWidth),
						png = bgpng))
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
				if evW > 0:
					res.append(MultiContentEntryText(
						pos = (evX, evY), size = (evW, evH),
						font = 1, flags = alignnment,
						text = ev[1],
						color = foreColor, color_sel = foreColorSel,
						backcolor = backColor, backcolor_sel = backColorSel))

				# recording icons
				if rec:
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos = (left+xpos+ewidth-22, top+height-22), size = (21, 21),
						png = self.getClockPixmap(service, stime, duration, ev[0]),
						backcolor_sel = backColorSel))
		else:
			# event box background
			if self.othEvPix is not None and config.epgselection.graphics_mode.value == "graphics":
				res.append(MultiContentEntryPixmapAlphaTest(
					pos = (r2.x + self.eventBorderWidth, r2.y + self.eventBorderWidth),
					size = (r2.w - 2 * self.eventBorderWidth, r2.h - 2 * self.eventBorderWidth),
					png = self.othEvPix))
			else:
				res.append(MultiContentEntryText(
					pos = (r2.x + self.eventBorderWidth, r2.y + self.eventBorderWidth),
					size = (r2.w - 2 * self.eventBorderWidth, r2.h - 2 * self.eventBorderWidth),
					font = 1, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER,
					text = "",
					color = self.foreColor, color_sel = self.foreColor,
					backcolor = self.backColor, backcolor_sel = self.backColorSelected,
					border_width = self.eventBorderWidth, border_color = self.borderColor))
		return res

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
			elif dir == +2: #next page
				self.offs += 1
				self.fillGraphEPG(None) # refill
				return True
			elif dir == -2: #prev
				if self.offs > 0:
					self.offs -= 1
					self.fillGraphEPG(None) # refill
					return True
		if cur_service and valid_event:
			entry = entries[self.cur_event] #(event_id, event_title, begin_time, duration)
			time_base = self.time_base + self.offs*self.time_epoch * 60
			xpos, width = self.calcEntryPosAndWidth(self.event_rect, time_base, self.time_epoch, entry[2], entry[3])
			self.select_rect = Rect(xpos ,0, width, self.event_rect.height)
			self.l.setSelectionClip(eRect(xpos, 0, width, self.event_rect.h), visible and update)
		else:
			self.select_rect = self.event_rect
			self.l.setSelectionClip(eRect(self.event_rect.x, self.event_rect.y, self.event_rect.w, self.event_rect.h), False)
		self.selectionChanged()
		return False

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
		print time() - t

	def fillSingleEPG(self, service):
		test = [ 'RIBDT', (service.ref.toString(), 0, -1, -1) ]
		self.list = [] if self.epgcache is None else self.epgcache.lookupEvent(test)
		self.l.setList(self.list)
		self.selectionChanged()

	def fillMultiEPG(self, services, stime=None):
		test = [ (service.ref.toString(), 0, stime) for service in services ]
		test.insert(0, 'X0RIBDTCn')
		self.list = [] if self.epgcache is None else self.epgcache.lookupEvent(test)
		self.l.setList(self.list)
		self.selectionChanged()

	def updateMultiEPG(self, direction):
		test = [ x[3] and (x[1], direction, x[3]) or (x[1], direction, 0) for x in self.list ]
		test.insert(0, 'XRIBDTCn')
		epg_data = [] if self.epgcache is None else self.epgcache.lookupEvent(test)
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
		epg_data = [] if self.epgcache is None else self.epgcache.lookupEvent(test)
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
		return self.time_base + (self.offs * self.time_epoch * 60)

	def resetOffset(self):
		self.offs = 0

	def getClockPixmap(self, refstr, beginTime, duration, eventId):
		pre_clock = 1
		post_clock = 2
		clock_type = 0
		endTime = beginTime + duration
		for x in self.timer.timer_list:
			if x.service_ref.ref.toString() == refstr:
				if x.eit == eventId:
					return self.clock_pixmap
				beg = x.begin
				end = x.end
				if beginTime > beg and beginTime < end and endTime > end:
					clock_type |= pre_clock
				elif beginTime < beg and endTime > beg and endTime < end:
					clock_type |= post_clock
		if clock_type == 0:
			return self.clock_add_pixmap
		elif clock_type == pre_clock:
			return self.clock_pre_pixmap
		elif clock_type == post_clock:
			return self.clock_post_pixmap
		else:
			return self.clock_prepost_pixmap

	def getPixmapForEntry(self, service, eventId, beginTime, duration):
		rec = beginTime and (self.timer.isInTimer(eventId, beginTime, duration, service))
		if rec:
			clock_pic = self.getClockPixmap(service, beginTime, duration, eventId)
		else:
			clock_pic = None
		return (clock_pic, rec)

	def GraphEPGRecRed(self, refstr, beginTime, duration, eventId):
		for x in self.timer.timer_list:
			if x.service_ref.ref.toString() == refstr:
				if x.eit == eventId:
					if x.justplay:
						return "justplay"
					else:
						return "record"
		return ""

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
	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setSelectionClip(eRect(0,0,0,0))
		self.l.setItemHeight(30);
		self.foreColor = 0xffc000
		self.borderColor = 0x000000
		self.backColor = 0x000000
		self.borderWidth = 1
		self.time_base = 0
		self.time_epoch = 0
		self.timelineFontName = "Regular"
		self.timelineFontSize = 20
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
				else:
					attribs.append((attrib,value))
			self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop, screen)

	def setTimeLineFontsize(self):
		self.l.setFont(0, gFont(self.timelineFontName, self.timelineFontSize + config.epgselection.tl_fontsize_vixepg.getValue()))

	def postWidgetCreate(self, instance):
		self.setTimeLineFontsize()
		instance.setContent(self.l)

	def setEntries(self, l, timeline_now, time_lines, force):
		event_rect = l.getEventRect()
		time_epoch = l.getTimeEpoch()
		time_base = l.getTimeBase()

		if event_rect is None or time_epoch is None or time_base is None:
			return

		eventLeft = event_rect.left()

		res = [ None ]

		# Note: event_rect and service_rect are relative to the timeline_text position
		# while the time lines are relative to the GraphEPG screen position!
		if self.time_base != time_base or self.time_epoch != time_epoch or force:
			service_rect = l.getServiceRect()
			itemHeight = self.l.getItemSize().height()
			time_steps = 60 if time_epoch > 180 else 30
			num_lines = time_epoch / time_steps
			incWidth = event_rect.width() / num_lines
			timeStepsCalc = time_steps * 60

			nowTime = localtime(time())
			begTime = localtime(time_base)
			self.ServiceWidth = service_rect.width()
			if nowTime[2] != begTime[2]:
				if self.ServiceWidth > 179:
					datestr = strftime("%A %d %B", localtime(time_base))
				elif self.ServiceWidth > 139:
					datestr = strftime("%a %d %B", localtime(time_base))
				elif self.ServiceWidth > 129:
					datestr = strftime("%a %d %b", localtime(time_base))
				elif self.ServiceWidth > 119:
					datestr = strftime("%a %d", localtime(time_base))
				elif self.ServiceWidth > 109:
					datestr = strftime("%A", localtime(time_base))
				else:
					datestr = strftime("%a", localtime(time_base))
			else:
				datestr = '%s'%(_("Today"))

			res.append( MultiContentEntryText(
				pos = (0, 0),
				size = (service_rect.width(), itemHeight),
				font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP,
				text = _(datestr),
				color = self.foreColor, color_sel = self.foreColor,
				backcolor = self.backColor, backcolor_sel = self.backColor,
				border_width = self.borderWidth, border_color = self.borderColor))

			xpos = 0 # eventLeft
			for x in range(0, num_lines):
				res.append( MultiContentEntryText(
					pos = (service_rect.width() + xpos, 0),
					size = (incWidth, itemHeight),
					font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP,
					text = strftime("%H:%M", localtime( time_base + x*timeStepsCalc )),
					color = self.foreColor, color_sel = self.foreColor,
					backcolor = self.backColor, backcolor_sel = self.backColor,
					border_width = self.borderWidth, border_color = self.borderColor) )
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
		if now >= time_base and now < (time_base + time_epoch * 60):
			xpos = int((((now - time_base) * event_rect.width()) / (time_epoch * 60)) - (timeline_now.instance.size().width() / 2))
			old_pos = timeline_now.position
			new_pos = (xpos + eventLeft, old_pos[1])
			if old_pos != new_pos:
				timeline_now.setPosition(new_pos[0], new_pos[1])
			timeline_now.visible = True
		else:
			timeline_now.visible = False
