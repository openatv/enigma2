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

def _loadPixmaps(names):
	pixmaps = [ ]
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

def _applySkinAttributes(obj, skinAttrs, attribMap, callerApplyMap = None):
	def applyStrAttrib(obj, objAttrs, value):
		setattr(obj, objAttrs[0], value)

	def applyIntAttrib(obj, objAttrs, value):
		setattr(obj, objAttrs[0], int(value))

	def applyFontAttrib(obj, objAttrs, value):
		font = parseFont(value, ((1,1),(1,1)) )
		setattr(obj, objAttrs[0], font.family)
		setattr(obj, objAttrs[1], font.pointSize)

	def applyColorAttrib(obj, objAttrs, value):
		setattr(obj, objAttrs[0], parseColor(value).argb())

	applyMap = {
		"str":		applyStrAttrib,
		"int":		applyIntAttrib,
		"font":		applyFontAttrib,
		"color":	applyColorAttrib,
	}

	# Callers can override/extend function map
	if callerApplyMap is not None:
		applyMap = dict(applyMap.items() + callerApplyMap.items())

	if skinAttrs is not None:
		attribs = [ ]
		for (attrib, value) in skinAttrs:
			if attrib in attribMap:
				mapEnt = attribMap[attrib]
				type = mapEnt[0]
				if type in applyMap:
					applyMap[type](obj, mapEnt[1:], value)
				else:
					print "[EPGList]", "Unknown type %s in attribute map for skin attribute %s" % (type, attrib)
			else:
				attribs.append((attrib,value))
		return attribs
	else:
		return None

def _makeBorder(rect, borderWidth, pixmaps):
	size = ((rect.w, borderWidth),					# T/B
		(borderWidth, rect.h))					# L/R
	pos  = ((rect.x, rect.y), (rect.x, rect.y+rect.h-borderWidth),	# T/B
		(rect.x, rect.y), (rect.x+rect.w-borderWidth, 0))	# L/R
	bdr = [ ]
	for i in range(4): # T, B, L, R
		if pixmaps and i < len(pixmaps) and pixmaps[i]:
			bdr.append(MultiContentEntryPixmapAlphaTest(
				pos = pos[i],
				size = size[i/2],
				png = pixmaps[i],
				flags = BT_SCALE))
	return bdr

def _rectToPosSize(rect, tbBorderWidth = 0, lrBorderWidth = None):
	if lrBorderWidth is None:
		lrBorderWidth = tbBorderWidth
	return {
		"pos":  (rect.x + lrBorderWidth, rect.y + tbBorderWidth),
		"size": (max(0, rect.w - lrBorderWidth * 2),
			 max(0, rect.h - tbBorderWidth * 2))
	}

class EPGList(HTMLComponent, GUIComponent):

	# Map skin attributes to class attribute names; font skin attributes
	# map to two class attributes each, font name and font size.

	attribMap = {
		# Plain strs
		"EntryFontAlignment":	("str", "eventNameAlign"),
		"EntryFontWrap":	("str", "eventNameWrap"),
		# Plain ints
		"NumberOfRows":		("int", "numberOfRows"),
		"EventBorderWidth":	("int", "eventBorderWidth"),
		"EventNamePadding":	("int", "eventNamePadding"),
		"ServiceBorderWidth":	("int", "serviceBorderWidth"),
		"ServiceNamePadding":	("int", "serviceNamePadding"),
		# Fonts
		"ServiceFontGraphical": ("font", "serviceFontNameGraph", "serviceFontSizeGraph"),
		"EntryFontGraphical":	("font", "eventFontNameGraph", "eventFontSizeGraph"),
		"EventFontSingle":	("font", "eventFontNameSingle", "eventFontSizeSingle"),
		"EventFontInfobar":	("font", "eventFontNameInfobar", "eventFontSizeInfobar"),
		"ServiceFontInfobar":	("font", "serviceFontNameInfobar", "serviceFontSizeInfobar"),
		# Colors
		"ServiceForegroundColor":	("color", "foreColorService"),
		"ServiceForegroundColorNow":	("color", "foreColorServiceNow"),
		"ServiceBackgroundColor":	("color", "backColorService"),
		"ServiceBackgroundColorNow":	("color", "backColorServiceNow"),

		"EntryForegroundColor":		("color", "foreColor"),
		"EntryForegroundColorSelected":	("color", "foreColorSelected"),
		"EntryBackgroundColor":		("color", "backColor"),
		"EntryBackgroundColorSelected":	("color", "backColorSelected"),
		"ServiceBorderColor":		("color", "borderColorService"),
		"EntryBorderColor":		("color", "borderColor"),
		"RecordForegroundColor":	("color", "foreColorRecord"),
		"RecordForegroundColorSelected":("color", "foreColorRecordSelected"),
		"RecordBackgroundColor":	("color", "backColorRecord"),
		"RecordBackgroundColorSelected":("color", "backColorRecordSelected"),
		"ZapForegroundColor":		("color", "foreColorZap"),
		"ZapBackgroundColor":		("color", "backColorZap"),
		"ZapForegroundColorSelected":	("color", "foreColorZapSelected"),
		"ZapBackgroundColorSelected":	("color", "backColorZapSelected"),
	}

	def __init__(self, type = EPG_TYPE_SINGLE, selChangedCB = None, timer = None, time_epoch = 120, overjump_empty = False, graphic=False):
		self.cur_event = None
		self.cur_service = None
		self.service_set = False
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
		self.numberOfRows = None

	def applySkin(self, desktop, screen):
		self.skinAttributes = _applySkinAttributes(self, self.skinAttributes, self.attribMap)
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.setItemsPerPage()
		self.setFontsize()
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
			(refstr, service_name, events, picon) = self.cur_service
			if self.cur_event is None or not events or (self.cur_event and events and self.cur_event > len(events)-1):
				return None, ServiceReference(refstr)
			event = events[self.cur_event] #(event_id, event_title, begin_time, duration)
			eventid = event[0]
			service = ServiceReference(refstr)
			event = self.getEventFromId(service, eventid) # get full event info
			return event, service
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

	def connectSelectionChanged(self, func):
		if not self.onSelChanged.count(func):
			self.onSelChanged.append(func)

	def disconnectSelectionChanged(self, func):
		self.onSelChanged.remove(func)

	def serviceChanged(self):
		cur_sel = self.l.getCurrentSelection()
		if cur_sel:
			self.findBestEvent()

	def findBestEvent(self):
		if not self.service_set:
			return
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
					if not old_service and ev_time <= last_time < ev_end_time:
						best = idx
						break
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
		if self.type in (EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH):
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
			if self.numberOfRows:
				itemHeight = self.listHeight / self.numberOfRows
			self.l.setItemHeight(itemHeight)
			self.instance.resize(eSize(self.listWidth, self.listHeight / itemHeight * itemHeight))
			self.listHeight = self.instance.size().height()
			self.listWidth = self.instance.size().width()
			self.itemHeight = itemHeight

		elif self.type in (EPG_TYPE_ENHANCED, EPG_TYPE_SINGLE, EPG_TYPE_SIMILAR):
			if self.listHeight > 0:
				itemHeight = self.listHeight / config.epgselection.enhanced_itemsperpage.value
			else:
				itemHeight = 32
			if itemHeight < 25:
				itemHeight = 25
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
			self.l.setSelectionClip(eRect(0,0,0,0), False)
		else:
			instance.setWrapAround(False)
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
		elif self.type in (EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH):
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
			self.weekday_rect = Rect(0, 0, float(width * 15) / 100, height)
			self.datetime_rect = Rect(self.weekday_rect.w, 0, float(width * 15) / 100, height)
			self.descr_rect = Rect(self.datetime_rect.x + self.datetime_rect.w, 0, float(width * 70) / 100, height)

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
		et = localtime(beginTime + duration)
		res = [
			None, # no private data needed
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, strftime("%a, %d %b", t)),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, r2.w, r1.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, "%s ~ %s" % (strftime("%H:%M", t), strftime("%H:%M", et)))
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
					png = bgpng,
					flags = BT_SCALE,
					**_rectToPosSize(r1, self.serviceBorderWidth)))
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
				font = namefont, flags = namefontflag,
				text = service_name,
				color = serviceForeColor, color_sel = serviceForeColor,
				backcolor = serviceBackColor, backcolor_sel = serviceBackColor,
				**_rectToPosSize(Rect(r1.x + piconWidth, r1.y, namewidth, r1.h), self.serviceBorderWidth, self.serviceBorderWidth + self.serviceNamePadding)))

		# Service Borders
		if self.graphic:
			res += _makeBorder(r1, self.serviceBorderWidth, self.borderPixmaps)
			res += _makeBorder(r2, self.eventBorderWidth, self.borderPixmaps)

		if self.graphic:
			if selected and not events and self.selEvPix:
				res.append(MultiContentEntryPixmapAlphaTest(
					png = self.selEvPix,
					flags = BT_SCALE,
					**_rectToPosSize(r2, self.eventBorderWidth)))
			elif self.othEvPix:
				res.append(MultiContentEntryPixmapAlphaTest(
					png = self.othEvPix,
					flags = BT_SCALE,
					**_rectToPosSize(r2, self.eventBorderWidth)))
		else:
			res.append(MultiContentEntryText(
				pos = (left, top), size = (width, height),
				font = 1, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				text = "", color = None, color_sel = None,
				backcolor = self.backColor, backcolor_sel = self.backColorSelected,
				border_width = self.eventBorderWidth, border_color = self.borderColor))

		# Events for service
		if events:
			start = self.getTimeBase()
			end = start + self.time_epoch * 60

			now = time()
			for ev in events:  #(event_id, event_title, begin_time, duration)
				stime = ev[2]
				duration = ev[3]
				xpos, ewidth = self.calcEntryPosAndWidthHelper(stime, duration, start, end, width)
				evRect = Rect(left + xpos, top, ewidth, height)
				clock_types = self.getPixmapForEntry(service, ev[0], stime, duration)
				if self.eventNameAlign.lower() == 'left':
					if self.eventNameWrap.lower() == 'yes':
						alignment = RT_HALIGN_LEFT | RT_VALIGN_TOP | RT_WRAP
					else:
						alignment = RT_HALIGN_LEFT | RT_VALIGN_TOP
				else:
					if self.eventNameWrap.lower() == 'yes':
						alignment = RT_HALIGN_CENTER | RT_VALIGN_TOP | RT_WRAP
					else:
						alignment = RT_HALIGN_CENTER | RT_VALIGN_TOP

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
				else:
					if clock_types is not None:
						clocks = self.clocks[clock_types]
					borderPixmaps = self.borderPixmaps
					infoPix = self.infoPix
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
						png = bgpng,
						flags = BT_SCALE,
						**_rectToPosSize(evRect, self.eventBorderWidth)))
				else:
					res.append(MultiContentEntryText(
						font = 1, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER,
						text = "", color = None, color_sel = None,
						backcolor = backColor, backcolor_sel = backColorSel,
						border_width = self.eventBorderWidth, border_color = self.borderColor,
						**_rectToPosSize(evRect, 0)))

				# event text
				evSizePos = _rectToPosSize(evRect, self.eventBorderWidth, self.eventBorderWidth + self.eventNamePadding)

				if self.type == EPG_TYPE_GRAPH:
					infowidth = config.epgselection.graph_infowidth.value
				elif self.type == EPG_TYPE_INFOBARGRAPH:
					infowidth = config.epgselection.infobar_infowidth.value
				if evSizePos["size"][0] < infowidth and infoPix is not None:
					res.append(MultiContentEntryPixmapAlphaBlend(
						png = infoPix,
						**evSizePos))
				else:
					res.append(MultiContentEntryText(
						font = 1, flags = alignment,
						text = ev[1],
						color = foreColor, color_sel = foreColorSel,
						backcolor = backColor, backcolor_sel = backColorSel,
						**evSizePos))

				# event box borders
				res += _makeBorder(evRect, self.eventBorderWidth, borderPixmaps)

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
		elif self.type in (EPG_TYPE_ENHANCED, EPG_TYPE_SINGLE, EPG_TYPE_SIMILAR):
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
		if not self.service_set:
			return
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
				elif self.time_base > time():
					self.time_base -= self.time_epoch * 60
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

		if cur_service and valid_event and self.cur_event < len(entries):
			entry = entries[self.cur_event] #(event_id, event_title, begin_time, duration)
			time_base = self.getTimeBase()
			xpos, width = self.calcEntryPosAndWidth(self.event_rect, time_base, self.time_epoch, entry[2], entry[3])
			self.select_rect = Rect(xpos, 0, width, self.event_rect.h)
			clipUpdate = visible and update
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
		if (self.type in (EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH)) and not self.graphicsloaded:
			if self.graphic:
				_loadPixmapsToAttrs(self, {
					"othEvPix":	'epg/OtherEvent.png',
					"selEvPix":	'epg/SelectedEvent.png',
					"othServPix":	'epg/OtherService.png',
					"nowServPix":	'epg/CurrentService.png',
					"recEvPix":	'epg/RecordEvent.png',
					"recSelEvPix":	'epg/SelectedRecordEvent.png',
					"zapEvPix":	'epg/ZapEvent.png',
					"zapSelEvPix":	'epg/SelectedZapEvent.png',
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
				"infoPix":	'epg/information.png',
				"selInfoPix":	'epg/SelectedInformation.png',
			})

			self.graphicsloaded = True

		if stime is not None:
			self.time_base = int(stime)
		if services is None:
			time_base = self.getTimeBase()
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
		return Rect( rc.x + (self.instance and self.instance.position().x() or 0), rc.y, rc.w, rc.h )

	def getServiceRect(self):
		rc = self.service_rect
		return Rect( rc.x + (self.instance and self.instance.position().x() or 0), rc.y, rc.w, rc.h )

	def getTimeEpoch(self):
		return self.time_epoch

	def getTimeBase(self):
		return self.time_base + self.offs * self.time_epoch * 60

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

	attribMap = {
		# Plain strs
		"TimelineAlignment":	("str", "timelineAlign"),
		"TimelineTicksOn":	("str", "ticksOn"),
		"TimelineTickAlignment":("str", "tickAlignment"),
		# Plain ints
		"itemHeight":		("int", "itemHeight"),
		"borderWidth":		("int", "borderWidth"),
		"TimelineTextPadding":	("int", "textPadding"),
		# Fonts
		"TimelineFont":		("font", "timelineFontName", "timelineFontSize"),
		# Colors
		"foregroundColor":	("color", "foreColor"),
		"borderColor":		("color", "borderColor"),
		"backgroundColor":	("color", "backColor"),
	}

	def __init__(self, type = EPG_TYPE_GRAPH, graphic=False):
		GUIComponent.__init__(self)
		self.type = type
		self.graphic = graphic
		self.l = eListboxPythonMultiContent()
		self.l.setSelectionClip(eRect(0,0,0,0))
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
		self.timelineAlign = 'left'
		self.borderWidth = 1
		self.ticksOn = "yes"
		self.tickAlignment = "right"
		self.textPadding = 2
		self.datefmt = ""

	GUI_WIDGET = eListbox

	def applySkin(self, desktop, screen):
		self.skinAttributes = _applySkinAttributes(self, self.skinAttributes, self.attribMap)
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "font":
					self.l.setFont(0, parseFont(value,  ((1,1),(1,1)) ))
				else:
					attribs.append((attrib,value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.l.setItemHeight(self.itemHeight)
		if self.graphic:
			_loadPixmapsToAttrs(self, {
				"TlDate":	'epg/TimeLineDate.png',
				"TlTime":	'epg/TimeLineTime.png',
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

		if self.timelineAlign.lower() == 'right':
			alignment = RT_HALIGN_RIGHT | RT_VALIGN_TOP
		else:
			alignment = RT_HALIGN_LEFT | RT_VALIGN_TOP

		if event_rect is None or time_epoch is None or time_base is None:
			return

		eventLeft = event_rect.x

		res = [ None ]

		# Note: event_rect and service_rect are relative to the timeline_text position
		# while the time lines are relative to the GraphEPG screen position!
		if self.time_base != time_base or self.time_epoch != time_epoch or force:
			service_rect = l.getServiceRect()
			time_steps = 60 if time_epoch > 180 else 30
			num_lines = time_epoch / time_steps
			incWidth = event_rect.w / num_lines
			timeStepsCalc = time_steps * 60

			nowTime = localtime(time())
			begTime = localtime(time_base)
			serviceWidth = service_rect.w
			if nowTime[2] != begTime[2]:
				if serviceWidth > 179:
					datestr = strftime("%A %d %B", localtime(time_base))
				elif serviceWidth > 139:
					datestr = strftime("%a %d %B", localtime(time_base))
				elif serviceWidth > 129:
					datestr = strftime("%a %d %b", localtime(time_base))
				elif serviceWidth > 119:
					datestr = strftime("%a %d", localtime(time_base))
				elif serviceWidth > 109:
					datestr = strftime("%A", localtime(time_base))
				else:
					datestr = strftime("%a", localtime(time_base))
			else:
				datestr = '%s'%(_("Today"))

			foreColor = self.foreColor
			backColor = self.backColor
			bgpng = self.tlDate
			if bgpng is not None and self.graphic:
				backColor = None
				backColorSel = None
				res.append(MultiContentEntryPixmapAlphaTest(
					pos = (0, 0),
					size = (service_rect.w, self.listHeight),
					png = bgpng,
					flags = BT_SCALE))
			else:
				res.append( MultiContentEntryText(
					pos = (0, 0),
					size = (service_rect.w, self.listHeight),
					color = foreColor,
					backcolor = backColor,
					border_width = self.borderWidth, border_color = self.borderColor))

			res.append(MultiContentEntryText(
				pos = (5, 0),
				size = (service_rect.w-15, self.listHeight),
				font = 0, flags = alignment,
				text = datestr,
				color = foreColor,
				backcolor = backColor))

			bgpng = self.tlTime
			xpos = 0 # eventLeft
			if bgpng is not None and self.graphic:
				backColor = None
				backColorSel = None
				res.append(MultiContentEntryPixmapAlphaTest(
					pos = (service_rect.w, 0),
					size = (event_rect.w, self.listHeight),
					png = bgpng,
					flags = BT_SCALE))
			else:
				res.append( MultiContentEntryText(
					pos = (service_rect.w, 0),
					size = (event_rect.w, self.listHeight),
					color = foreColor,
					backcolor = backColor,
					border_width = self.borderWidth, border_color = self.borderColor))

			# An estimate of textHeight is the best we can do, and it's not really critical
			textHeight = self.timelineFontSize + 2
			textScreenY = self.position[1]
			for x in range(0, num_lines):
				line = time_lines[x]
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
				ttime = localtime(time_base + (x*timeStepsCalc))
				if (self.type == EPG_TYPE_GRAPH and config.epgselection.graph_timeline24h.value) or (self.type == EPG_TYPE_INFOBARGRAPH and config.epgselection.infobar_timeline24h.value):
					timetext = strftime("%H:%M", localtime(time_base + x*timeStepsCalc))
				else:
					if int(strftime("%H",ttime)) > 12:
						timetext = strftime("%-I:%M",ttime) + _('pm')
					else:
						timetext = strftime("%-I:%M",ttime) + _('am')
				res.append(MultiContentEntryText(
					pos = (service_rect.width() + xpos + textOffset, 0),
					size = (incWidth, self.listHeight),
					font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP,
					text = timetext,
					color = foreColor,
					backcolor = backColor))
				xpos += incWidth
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
		"borderWidth":			("int", "borderWidth"),
		"itemHeight":			("int", "itemHeight"),
		# Fonts
		"font":				("font", "bouquetFontName", "bouquetFontSize"),
		# Colors
		"foregroundColor":		("color", "foreColor"),
		"backgroundColor":		("color", "backColor"),
		"foregroundColorSelected":	("color", "foreColorSelected"),
		"backgroundColorSelected":	("color", "backColorSelected"),
		"borderColor":			("color", "borderColor"),
	}

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
		self.skinAttributes = _applySkinAttributes(self, self.skinAttributes, self.attribMap)
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
		return Rect( rc.x + (self.instance and self.instance.position().x() or 0), rc.y, rc.w, rc.h )

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

		res = [ None ]

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
				png = bgpng,
				flags = BT_SCALE,
				**_rectToPosSize(r1, self.borderWidth)))
		else:
			res.append(MultiContentEntryText(
				font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				text = "", color = None, color_sel = None,
				backcolor = backColor, backcolor_sel = backColorSel,
				border_width = self.borderWidth, border_color = self.borderColor,
				**_rectToPosSize(r1, 0)))

		res.append(MultiContentEntryText(
			font = 0, flags = alignment,
			text = name,
			color = foreColor, color_sel = foreColorSel,
			backcolor = backColor, backcolor_sel = backColorSel,
			**_rectToPosSize(r1, self.borderWidth, self.borderWidth + self.bouquetNamePadding)))

		# Borders
		if self.graphic:
			res += _makeBorder(r1, self.borderWidth, borderPixmaps)

		return res

	def fillBouquetList(self, bouquets):
		if self.graphic and not self.graphicsloaded:
			_loadPixmapsToAttrs(self, {
				"othPix":		'epg/OtherEvent.png',
				"selPix":		'epg/SelectedCurrentEvent.png',
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
		self.selectionChanged()
		self.currentBouquetService = self.getCurrentBouquetService()
