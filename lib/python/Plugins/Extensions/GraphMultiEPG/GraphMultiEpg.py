from skin import parseColor, parseFont, parseSize
from Components.config import config, ConfigClock, ConfigInteger, ConfigSubsection, ConfigYesNo, ConfigSelection, ConfigSelectionNumber
from Components.Pixmap import Pixmap
from Components.Button import Button
from Components.ActionMap import HelpableActionMap
from Components.HTMLComponent import HTMLComponent
from Components.GUIComponent import GUIComponent
from Components.EpgList import Rect
from Components.Sources.Event import Event
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.TimerList import TimerList
from Components.Renderer.Picon import getPiconName
from Components.Sources.ServiceEvent import ServiceEvent
import Screens.InfoBar
from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Screens.EventView import EventViewEPGSelect
from Screens.TimeDateInput import TimeDateInput
from Screens.TimerEntry import TimerEntry
from Screens.EpgSelection import EPGSelection
from Screens.TimerEdit import TimerSanityConflict, TimerEditList
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT
from ServiceReference import ServiceReference, isPlayableForCur
from Tools.LoadPixmap import LoadPixmap
from Tools.Alternatives import CompareWithAlternatives
from Tools import Notifications
from enigma import eEPGCache, eListbox, gFont, eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER,\
	RT_VALIGN_CENTER, RT_WRAP, BT_SCALE, BT_KEEP_ASPECT_RATIO, eSize, eRect, eTimer, getBestPlayableServiceReference, loadPNG
from GraphMultiEpgSetup import GraphMultiEpgSetup
from time import localtime, time, strftime
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor
from Tools.BoundFunction import boundFunction

MAX_TIMELINES = 6

config.misc.graph_mepg = ConfigSubsection()
config.misc.graph_mepg.prev_time = ConfigClock(default = time())
config.misc.graph_mepg.prev_time_period = ConfigInteger(default = 120, limits = (60, 300))
config.misc.graph_mepg.ev_fontsize = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 8, wraparound = True)
config.misc.graph_mepg.items_per_page = ConfigSelectionNumber(min = 3, max = 40, stepwidth = 1, default = 6, wraparound = True)
config.misc.graph_mepg.items_per_page_listscreen = ConfigSelectionNumber(min = 3, max = 60, stepwidth = 1, default = 12, wraparound = True)
config.misc.graph_mepg.default_mode = ConfigYesNo(default = False)
config.misc.graph_mepg.overjump = ConfigYesNo(default = True)
config.misc.graph_mepg.center_timeline = ConfigYesNo(default = False)
config.misc.graph_mepg.servicetitle_mode = ConfigSelection(default = "picon+servicename", choices = [
	("servicename", _("Service name")),
	("picon", _("Picon")),
	("picon+servicename", _("Picon and service name")) ])
config.misc.graph_mepg.roundTo = ConfigSelection(default = "900", choices = [("900", _("%d minutes") % 15), ("1800", _("%d minutes") % 30), ("3600", _("%d minutes") % 60)])
config.misc.graph_mepg.OKButton = ConfigSelection(default = "info", choices = [("info", _("Show detailed event info")), ("zap", _("Zap to selected channel"))])
possibleAlignmentChoices = [
	( str(RT_HALIGN_LEFT   | RT_VALIGN_CENTER          ) , _("left")),
	( str(RT_HALIGN_CENTER | RT_VALIGN_CENTER          ) , _("centered")),
	( str(RT_HALIGN_RIGHT  | RT_VALIGN_CENTER          ) , _("right")),
	( str(RT_HALIGN_LEFT   | RT_VALIGN_CENTER | RT_WRAP) , _("left, wrapped")),
	( str(RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_WRAP) , _("centered, wrapped")),
	( str(RT_HALIGN_RIGHT  | RT_VALIGN_CENTER | RT_WRAP) , _("right, wrapped"))]
config.misc.graph_mepg.event_alignment = ConfigSelection(default = possibleAlignmentChoices[0][0], choices = possibleAlignmentChoices)
config.misc.graph_mepg.servicename_alignment = ConfigSelection(default = possibleAlignmentChoices[0][0], choices = possibleAlignmentChoices)
config.misc.graph_mepg.extension_menu = ConfigYesNo(default = False)
config.misc.graph_mepg.silent_bouquet_change = ConfigYesNo(default = True)

listscreen = config.misc.graph_mepg.default_mode.value

class EPGList(HTMLComponent, GUIComponent):
	def __init__(self, selChangedCB = None, timer = None, time_epoch = 120, overjump_empty = True):
		GUIComponent.__init__(self)
		self.cur_event = None
		self.cur_service = None
		self.offs = 0
		self.timer = timer
		self.last_time = time()
		self.onSelChanged = [ ]
		if selChangedCB is not None:
			self.onSelChanged.append(selChangedCB)
		self.l = eListboxPythonMultiContent()
		self.l.setBuildFunc(self.buildEntry)
		self.setOverjump_Empty(overjump_empty)
		self.epgcache = eEPGCache.getInstance()
		self.clocks = [ LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_add.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_pre.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_prepost.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_post.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/zapclock_add.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/zapclock_pre.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/zapclock.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/zapclock_prepost.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/zapclock_post.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/zaprecclock_add.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/zaprecclock_pre.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/zaprecclock.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/zaprecclock_prepost.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/zaprecclock_post.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/repepgclock_add.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/repepgclock_pre.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/repepgclock.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/repepgclock_prepost.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/repepgclock_post.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/repzapclock_add.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/repzapclock_pre.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/repzapclock.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/repzapclock_prepost.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/repzapclock_post.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/repzaprecclock_add.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/repzaprecclock_pre.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/repzaprecclock.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/repzaprecclock_prepost.png')),
				LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/repzaprecclock_post.png')) ]
		self.time_base = None
		self.time_epoch = time_epoch
		self.list = None
		self.select_rect = None
		self.event_rect = None
		self.service_rect = None
		self.picon_size = None
		self.currentlyPlaying = None
		self.showPicon = False
		self.showServiceTitle = True
		self.nowEvPix = None
		self.othEvPix = None
		self.selEvPix = None
		self.recEvPix = None
		self.curSerPix = None

		self.foreColor = 0xffffff
		self.foreColorSelected = 0xffc000
		self.borderColor = 0x464445
		self.backColor = 0x595959
		self.backColorSelected = 0x808080
		self.foreColorService = 0xffffff
		self.foreColorServiceSelected = 0xffffff
		self.backColorService = 0x000000
		self.backColorServiceSelected = 0x508050
		self.borderColorService = 0x000000
		self.foreColorNow = 0xffffff
		self.backColorNow = 0x505080
		self.foreColorRec = 0xffffff
		self.backColorRec = 0x805050
		self.serviceFont = gFont("Regular", 20)
		self.entryFontName = "Regular"
		self.entryFontSize = 18

		self.listHeight = None
		self.listWidth = None
		self.serviceBorderWidth = 1
		self.serviceNamePadding = 0
		self.eventBorderWidth = 1
		self.eventNamePadding = 0

	def applySkin(self, desktop, screen):
		def EntryForegroundColor(value):
			self.foreColor = parseColor(value).argb()
		def EntryForegroundColorSelected(value):
			self.foreColorSelected = parseColor(value).argb()
		def EntryBackgroundColor(value):
			self.backColor = parseColor(value).argb()
		def EntryBackgroundColorSelected(value):
			self.backColorSelected = parseColor(value).argb()
		def EntryBorderColor(value):
			self.borderColor = parseColor(value).argb()
		def EntryFont(value):
			font = parseFont(value, ((1,1),(1,1)) )
			self.entryFontName = font.family
			self.entryFontSize = font.pointSize
		def ServiceForegroundColor(value):
			self.foreColorService = parseColor(value).argb()
		def ServiceNameForegroundColor(value):
			self.foreColorService = parseColor(value).argb()
		def ServiceForegroundColorSelected(value):
			self.foreColorServiceSelected = parseColor(value).argb()
		def ServiceBackgroundColor(value):
			self.backColorService = parseColor(value).argb()
		def ServiceNameBackgroundColor(value):
			self.backColorService = parseColor(value).argb()
		def ServiceBackgroundColorSelected(value):
			self.backColorServiceSelected = parseColor(value).argb()
		def ServiceBackgroundColorRecording(value):
			self.backColorRec = parseColor(value).argb()
		def ServiceNameBackgroundColor(value):
			self.backColorRec = parseColor(value).argb()
		def ServiceForegroundColorRecording(value):
			self.foreColorRec = parseColor(value).argb()
		def ServiceBorderColor(value):
			self.borderColorService = parseColor(value).argb()
		def ServiceFont(value):
			self.serviceFont = parseFont(value, ((1,1),(1,1)) )
		def EntryBackgroundColorNow(value):
			self.backColorNow = parseColor(value).argb()
		def EntryForegroundColorNow(value):
			self.foreColorNow = parseColor(value).argb()
		def ServiceBorderWidth(value):
			self.serviceBorderWidth = int(value)
		def ServiceNamePadding(value):
			self.serviceNamePadding = int(value)
		def EventBorderWidth(value):
			self.eventBorderWidth = int(value)
		def EventNamePadding(value):
			self.eventNamePadding = int(value)
		for (attrib, value) in list(self.skinAttributes):
			try:
				locals().get(attrib)(value)
				self.skinAttributes.remove((attrib, value))
			except:
				pass
		self.l.setFont(0, self.serviceFont)
		self.setEventFontsize()
		rc = GUIComponent.applySkin(self, desktop, screen)
		# now we know our size and can safely set items per page
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.setItemsPerPage()
		return rc

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
		self.fillMultiEPG(None) # refill

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
				if CompareWithAlternatives(self.list[x][0], serviceref.toString()):
					return x
		return None

	def moveToService(self, serviceref):
		newIdx = self.getIndexFromService(serviceref)
		if newIdx is None:
			newIdx = 0
		self.setCurrentIndex(newIdx)

	def setCurrentIndex(self, index):
		if self.instance:
			self.instance.moveSelectionTo(index)

	def moveTo(self, dir):
		if self.instance:
			self.instance.moveSelection(dir)

	def moveToFromEPG(self, dir, epg):
		self.moveTo(dir==1 and eListbox.moveDown or eListbox.moveUp)
		if self.cur_service:
			epg.setService(ServiceReference(self.cur_service[0]))

	def getCurrent(self):
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
		now = time()
		if old_service and self.cur_event is not None:
			events = old_service[2]
			cur_event = events[self.cur_event] #(event_id, event_title, begin_time, duration)
			if self.last_time < cur_event[2] or cur_event[2]+cur_event[3] < self.last_time:
				self.last_time = cur_event[2]
		if now > self.last_time:
			self.last_time = now
		if cur_service:
			self.cur_event = None
			events = cur_service[2]
			if events and len(events):
				self.cur_event = idx = 0
				for event in events: #iterate all events
					if event[2] <= self.last_time and event[2]+event[3] > self.last_time:
						self.cur_event = idx
						break
					idx += 1
		self.selEntry(0)

	def selectionChanged(self):
		for x in self.onSelChanged:
			if x is not None:
				x()

	GUI_WIDGET = eListbox

	def setItemsPerPage(self):
		global listscreen
		if self.listHeight > 0:
			if listscreen:
				itemHeight = self.listHeight / config.misc.graph_mepg.items_per_page_listscreen.getValue()
			else:
				itemHeight = self.listHeight / config.misc.graph_mepg.items_per_page.getValue()
		else:
			itemHeight = 54 # some default (270/5)
		if listscreen:
			self.instance.resize(eSize(self.listWidth, itemHeight * config.misc.graph_mepg.items_per_page_listscreen.getValue()))
		else:
			self.instance.resize(eSize(self.listWidth, itemHeight * config.misc.graph_mepg.items_per_page.getValue()))
		self.l.setItemHeight(itemHeight)

		self.nowEvPix = loadPNG(resolveFilename(SCOPE_CURRENT_SKIN, 'epg/CurrentEvent.png'))
		self.othEvPix = loadPNG(resolveFilename(SCOPE_CURRENT_SKIN, 'epg/OtherEvent.png'))
		self.selEvPix = loadPNG(resolveFilename(SCOPE_CURRENT_SKIN, 'epg/SelectedEvent.png'))
		self.recEvPix = loadPNG(resolveFilename(SCOPE_CURRENT_SKIN, 'epg/RecordingEvent.png'))
		self.curSerPix = loadPNG(resolveFilename(SCOPE_CURRENT_SKIN, 'epg/CurrentService.png'))

	def setEventFontsize(self):
		self.l.setFont(1, gFont(self.entryFontName, self.entryFontSize + config.misc.graph_mepg.ev_fontsize.getValue()))

	def postWidgetCreate(self, instance):
		instance.setWrapAround(True)
		instance.selectionChanged.get().append(self.serviceChanged)
		instance.setContent(self.l)
		self.l.setSelectionClip(eRect(0, 0, 0, 0), False)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.serviceChanged)
		instance.setContent(None)

	def recalcEntrySize(self):
		esize = self.l.getItemSize()
		width = esize.width()
		height = esize.height()
		if self.showServiceTitle:
			w = width / 10 * 2;
		else:     # if self.showPicon:    # this must be set if showServiceTitle is None
			w = 2 * height - 2 * self.serviceBorderWidth  # FIXME: could do better...
		self.service_rect = Rect(0, 0, w, height)
		self.event_rect = Rect(w, 0, width - w, height)
		piconHeight = height - 2 * self.serviceBorderWidth
		piconWidth = 2 * piconHeight  # FIXME: could do better...
		if piconWidth > w - 2 * self.serviceBorderWidth:
			piconWidth = w - 2 * self.serviceBorderWidth
		self.picon_size = eSize(piconWidth, piconHeight)

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

	def buildEntry(self, service, service_name, events, picon):
		r1 = self.service_rect
		r2 = self.event_rect
		selected = self.cur_service[0] == service

		# Picon and Service name
		if CompareWithAlternatives(service, self.currentlyPlaying and self.currentlyPlaying.toString()):
			serviceForeColor = self.foreColorServiceSelected
			serviceBackColor = self.backColorServiceSelected
			bgpng = self.curSerPix or self.nowEvPix
			currentservice = True
		else:
			serviceForeColor = self.foreColorService
			serviceBackColor = self.backColorService
			bgpng = self.othEvPix
			currentservice = False

		res = [ None ]
		if bgpng is not None:    # bacground for service rect
			res.append(MultiContentEntryPixmapAlphaTest(
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
					backcolor = serviceBackColor, backcolor_sel = serviceBackColor))

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
				res.append(MultiContentEntryPixmapAlphaTest(
					pos = (r1.x + self.serviceBorderWidth, r1.y + self.serviceBorderWidth),
					size = (piconWidth, piconHeight),
					png = displayPicon,
					backcolor = None, backcolor_sel = None, flags = BT_SCALE | BT_KEEP_ASPECT_RATIO))
			elif not self.showServiceTitle:
				# no picon so show servicename anyway in picon space
				namefont = 1
				namefontflag = int(config.misc.graph_mepg.servicename_alignment.value)
				namewidth = piconWidth
				piconWidth = 0
		else:
			piconWidth = 0

		if self.showServiceTitle: # we have more space so reset parms
			namefont = 0
			namefontflag = int(config.misc.graph_mepg.servicename_alignment.value)
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
				backcolor = None, backcolor_sel = None))

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
				rec = self.timer.isInTimer(ev[0], stime, duration, service)

				# event box background
				foreColorSelected = foreColor = self.foreColor
				if stime <= now and now < stime + duration:
					backColor = self.backColorNow
					if isPlayableForCur(ServiceReference(service).ref):
						foreColor = self.foreColorNow
						foreColorSelected = self.foreColorSelected
				else:
					backColor = self.backColor

				if selected and self.select_rect.x == xpos + left and self.selEvPix:
					bgpng = self.selEvPix
					backColorSel = None
				elif rec is not None and rec[1][-1] in (2, 12, 17, 27):
					bgpng = self.recEvPix
					foreColor = self.foreColorRec
					backColor = self.backColorRec
				elif stime <= now and now < stime + duration:
					bgpng = self.nowEvPix
				elif currentservice:
					bgpng = self.curSerPix or self.othEvPix
					backColor = self.backColorServiceSelected
				else:
					bgpng = self.othEvPix

				if bgpng is not None:
					res.append(MultiContentEntryPixmapAlphaTest(
						pos = (left + xpos + self.eventBorderWidth, top + self.eventBorderWidth),
						size = (ewidth - 2 * self.eventBorderWidth, height - 2 * self.eventBorderWidth),
						png = bgpng,
						flags = BT_SCALE))
				else:
					res.append(MultiContentEntryText(
						pos = (left + xpos, top), size = (ewidth, height),
						font = 1, flags = int(config.misc.graph_mepg.event_alignment.value),
						text = "", color = None, color_sel = None,
						backcolor = backColor, backcolor_sel = backColorSel))

				# event text
				evX = left + xpos + self.eventBorderWidth + self.eventNamePadding
				evY = top + self.eventBorderWidth
				evW = ewidth - 2 * (self.eventBorderWidth + self.eventNamePadding)
				evH = height - 2 * self.eventBorderWidth
				if evW > 0:
					res.append(MultiContentEntryText(
						pos = (evX, evY),
						size = (evW, evH),
						font = 1,
						flags = int(config.misc.graph_mepg.event_alignment.value),
						text = ev[1],
						color = foreColor,
						color_sel = foreColorSelected))
				# recording icons
				if rec is not None:
					for i in range(len(rec[1])):
						if ewidth < (i + 1) * 22:
							break
						res.append(MultiContentEntryPixmapAlphaTest(
							pos = (left + xpos + ewidth - (i + 1) * 22, top + height - 22), size = (21, 21),
							png = self.clocks[rec[1][len(rec[1]) - 1 - i]]))

		else:
			if selected and self.selEvPix:
				res.append(MultiContentEntryPixmapAlphaTest(
					pos = (r2.x + self.eventBorderWidth, r2.y + self.eventBorderWidth),
					size = (r2.w - 2 * self.eventBorderWidth, r2.h - 2 * self.eventBorderWidth),
					png = self.selEvPix,
					flags = BT_SCALE))
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
					self.fillMultiEPG(None) # refill
					return True
			elif dir == -1: #prev
				if valid_event and self.cur_event - 1 >= 0:
					self.cur_event -= 1
				elif self.offs > 0:
					self.offs -= 1
					self.fillMultiEPG(None) # refill
					return True
			elif dir == +2: #next page
				self.offs += 1
				self.fillMultiEPG(None) # refill
				return True
			elif dir == -2: #prev
				if self.offs > 0:
					self.offs -= 1
					self.fillMultiEPG(None) # refill
					return True
			elif dir == +3: #next day
				self.offs += 60 * 24 / self.time_epoch
				self.fillMultiEPG(None) # refill
				return True
			elif dir == -3: #prev day
				self.offs -= 60 * 24 / self.time_epoch
				if self.offs < 0:
					self.offs = 0;
				self.fillMultiEPG(None) # refill
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

	def fillMultiEPG(self, services, stime = None):
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

class TimelineText(HTMLComponent, GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setSelectionClip(eRect(0, 0, 0, 0))
		self.l.setItemHeight(25);
		self.foreColor = 0xffc000
		self.backColor = 0x000000
		self.time_base = 0
		self.time_epoch = 0
		self.font = gFont("Regular", 20)

	GUI_WIDGET = eListbox

	def applySkin(self, desktop, screen):
		def foregroundColor(value):
			self.foreColor = parseColor(value).argb()
		def backgroundColor(value):
			self.backColor = parseColor(value).argb()
		def font(value):
			self.font = parseFont(value,  ((1, 1), (1, 1)) )
		for (attrib, value) in list(self.skinAttributes):
			try:
				locals().get(attrib)(value)
				self.skinAttributes.remove((attrib, value))
			except:
				pass
		self.l.setFont(0, self.font)
		return GUIComponent.applySkin(self, desktop, screen)

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)

	def setDateFormat(self, value):
		if "servicename" in value:
			self.datefmt = _("%A %d %B")
		elif "picon" in value:
			self.datefmt = _("%d-%m")

	def setEntries(self, l, timeline_now, time_lines, force):
		event_rect = l.getEventRect()
		time_epoch = l.getTimeEpoch()
		time_base = l.getTimeBase()

		if event_rect is None or time_epoch is None or time_base is None:
			return

		eventLeft = event_rect.left()
		res = [ None ]

		# Note: event_rect and service_rect are relative to the timeline_text position
		#       while the time lines are relative to the GraphEPG screen position!
		if self.time_base != time_base or self.time_epoch != time_epoch or force:
			service_rect = l.getServiceRect()
			itemHeight = self.l.getItemSize().height()
			time_steps = 60 if time_epoch > 180 else 30
			num_lines = time_epoch / time_steps
			timeStepsCalc = time_steps * 60
			incWidth = event_rect.width() / num_lines
			if int(config.misc.graph_mepg.center_timeline.value):
				tlMove = incWidth / 2
				tlFlags = RT_HALIGN_CENTER | RT_VALIGN_CENTER
			else:
				tlMove = 0
				tlFlags = RT_HALIGN_LEFT | RT_VALIGN_CENTER

				res.append( MultiContentEntryText(
					pos = (0, 0),
					size = (service_rect.width(), itemHeight),
					font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER,
					text = strftime(self.datefmt, localtime(time_base)),
					color = self.foreColor, color_sel = self.foreColor,
					backcolor = self.backColor, backcolor_sel = self.backColor) )

			xpos = 0 # eventLeft
			for x in range(0, num_lines):
				res.append( MultiContentEntryText(
					pos = (service_rect.width() + xpos-tlMove, 0),
					size = (incWidth, itemHeight),
					font = 0, flags = tlFlags,
					text = strftime("%H:%M", localtime( time_base + x*timeStepsCalc )),
					color = self.foreColor, color_sel = self.foreColor,
					backcolor = self.backColor, backcolor_sel = self.backColor) )
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

class GraphMultiEPG(Screen, HelpableScreen):
	EMPTY = 0
	ADD_TIMER = 1
	REMOVE_TIMER = 2

	ZAP = 1

	def __init__(self, session, services, zapFunc=None, bouquetChangeCB=None, bouquetname=""):
		Screen.__init__(self, session)
		self.bouquetChangeCB = bouquetChangeCB
		now = time() - config.epg.histminutes.getValue() * 60
		self.ask_time = now - now % int(config.misc.graph_mepg.roundTo.getValue())
		self["key_red"] = Button("")
		self["key_green"] = Button("")

		global listscreen
		if listscreen:
			self["key_yellow"] = Button(_("Normal mode"))
			self.skinName="GraphMultiEPGList"
		else:
			self["key_yellow"] = Button(_("List mode"))

		self["key_blue"] = Button(_("Goto"))

		self.key_green_choice = self.EMPTY
		self.key_red_choice = self.EMPTY
		self["timeline_text"] = TimelineText()
		self["Service"] = ServiceEvent()
		self["Event"] = Event()
		self.time_lines = [ ]
		for x in range(0, MAX_TIMELINES):
			pm = Pixmap()
			self.time_lines.append(pm)
			self["timeline%d"%(x)] = pm
		self["timeline_now"] = Pixmap()
		self.services = services
		self.zapFunc = zapFunc
		if bouquetname != "":
			Screen.setTitle(self, bouquetname)

		self["list"] = EPGList( selChangedCB = self.onSelectionChanged,
					timer = self.session.nav.RecordTimer,
					time_epoch = config.misc.graph_mepg.prev_time_period.value,
					overjump_empty = config.misc.graph_mepg.overjump.value)

		HelpableScreen.__init__(self)
		self["okactions"] = HelpableActionMap(self, "OkCancelActions",
			{
				"cancel": (self.closeScreen,   _("Exit EPG")),
				"ok":	  (self.eventSelected, _("Zap to selected channel, or show detailed event info (depends on configuration)"))
			}, -1)
		self["okactions"].csel = self
		self["epgactions"] = HelpableActionMap(self, "EPGSelectActions",
			{
				"timerAdd":    (self.timerAdd,       _("Add/remove change timer for current event")),
				"info":        (self.infoKeyPressed, _("Show detailed event info")),
				"red":         (self.zapTo,          _("Zap to selected channel")),
				"yellow":      (self.swapMode,       _("Switch between normal mode and list mode")),
				"blue":        (self.enterDateTime,  _("Goto specific date/time")),
				"menu":	       (self.furtherOptions, _("Further Options")),
				"nextBouquet": (self.nextBouquet,    _("Show bouquet selection menu")),
				"prevBouquet": (self.prevBouquet,    _("Show bouquet selection menu")),
				"nextService": (self.nextPressed,    _("Goto next page of events")),
				"prevService": (self.prevPressed,    _("Goto previous page of events")),
				"preview":     (self.preview,        _("Preview selected channel")),
				"nextDay":     (self.nextDay,        _("Goto next day of events")),
				"prevDay":     (self.prevDay,        _("Goto previous day of events"))
			}, -1)
		self["epgactions"].csel = self

		self["inputactions"] = HelpableActionMap(self, "InputActions",
			{
				"left":  (self.leftPressed,  _("Go to previous event")),
				"right": (self.rightPressed, _("Go to next event")),
				"1":     (self.key1,         _("Set time window to 1 hour")),
				"2":     (self.key2,         _("Set time window to 2 hours")),
				"3":     (self.key3,         _("Set time window to 3 hours")),
				"4":     (self.key4,         _("Set time window to 4 hours")),
				"5":     (self.key5,         _("Set time window to 5 hours")),
				"6":     (self.key6,         _("Set time window to 6 hours")),
				"7":     (self.prevPage,     _("Go to previous page of service")),
				"9":     (self.nextPage,     _("Go to next page of service")),
				"8":     (self.toTop,        _("Go to first service")),
				"0":     (self.toEnd,        _("Go to last service"))
			}, -1)
		self["inputactions"].csel = self

		self.updateTimelineTimer = eTimer()
		self.updateTimelineTimer.callback.append(self.moveTimeLines)
		self.updateTimelineTimer.start(60 * 1000)
		self.onLayoutFinish.append(self.onCreate)
		self.previousref = self.session.nav.getCurrentlyPlayingServiceOrGroup()

	def prevPage(self):
		self["list"].moveTo(eListbox.pageUp)

	def nextPage(self):
		self["list"].moveTo(eListbox.pageDown)

	def toTop(self):
		self["list"].moveTo(eListbox.moveTop)

	def toEnd(self):
		self["list"].moveTo(eListbox.moveEnd)

	def prevPressed(self):
		self.updEvent(-2)

	def nextPressed(self):
		self.updEvent(+2)

	def leftPressed(self):
		self.updEvent(-1)

	def rightPressed(self):
		self.updEvent(+1)

	def prevDay(self):
		self.updEvent(-3)

	def nextDay(self):
		self.updEvent(+3)

	def updEvent(self, dir, visible = True):
		ret = self["list"].selEntry(dir, visible)
		if ret:
			self.moveTimeLines(True)

	def updEpoch(self, mins):
		self["list"].setEpoch(mins)
		config.misc.graph_mepg.prev_time_period.value = mins
		self.moveTimeLines()

	def key1(self):
		self.updEpoch(60)

	def key2(self):
		self.updEpoch(120)

	def key3(self):
		self.updEpoch(180)

	def key4(self):
		self.updEpoch(240)

	def key5(self):
		self.updEpoch(300)

	def key6(self):
		self.updEpoch(360)

	def nextBouquet(self):
		if self.bouquetChangeCB:
			self.bouquetChangeCB(1, self)

	def prevBouquet(self):
		if self.bouquetChangeCB:
			self.bouquetChangeCB(-1, self)

	def enterDateTime(self):
		t = localtime(time())
		config.misc.graph_mepg.prev_time.value = [t.tm_hour, t.tm_min]
		self.session.openWithCallback(self.onDateTimeInputClosed, TimeDateInput, config.misc.graph_mepg.prev_time)

	def onDateTimeInputClosed(self, ret):
		if len(ret) > 1:
			if ret[0]:
				now = time() - config.epg.histminutes.getValue() * 60
				self.ask_time = ret[1] if ret[1] >= now else now
				self.ask_time = self.ask_time - self.ask_time % int(config.misc.graph_mepg.roundTo.getValue())
				l = self["list"]
				l.resetOffset()
				l.fillMultiEPG(None, self.ask_time)
				self.moveTimeLines(True)

	def showSetup(self):
		self.session.openWithCallback(self.onSetupClose, GraphMultiEpgSetup)

	def onSetupClose(self, ignore = -1):
		l = self["list"]
		l.setItemsPerPage()
		l.setEventFontsize()
		l.setEpoch(config.misc.graph_mepg.prev_time_period.value)
		l.setOverjump_Empty(config.misc.graph_mepg.overjump.value)
		l.setShowServiceMode(config.misc.graph_mepg.servicetitle_mode.value)
		now = time() - config.epg.histminutes.getValue() * 60
		self.ask_time = now - now % int(config.misc.graph_mepg.roundTo.getValue())
		self["timeline_text"].setDateFormat(config.misc.graph_mepg.servicetitle_mode.value)
		l.fillMultiEPG(None, self.ask_time)
		self.moveTimeLines(True)

	def closeScreen(self):
		self.zapFunc(None, zapback = True)
		config.misc.graph_mepg.save()
		self.close(False)

	def furtherOptions(self):
		menu = []
		text = _("Select action")
		event = self["list"].getCurrent()[0]
		if event:
			menu = [(p.name, boundFunction(self.runPlugin, p)) for p in plugins.getPlugins(where = PluginDescriptor.WHERE_EVENTINFO) \
				if 'selectedevent' in p.__call__.func_code.co_varnames]
			if menu:
				text += _(": %s") % event.getEventName()
		menu.append((_("Timer Overview"), self.openTimerOverview))
		menu.append((_("Setup menu"), self.showSetup))
		if len(menu) == 1:
			menu and menu[0][1]()
		elif len(menu) > 1:
			def boxAction(choice):
				if choice:
					choice[1]()
			self.session.openWithCallback(boxAction, ChoiceBox, title=text, list=menu)

	def runPlugin(self, plugin):
		event = self["list"].getCurrent()
		plugin(session=self.session, selectedevent=event)

	def openTimerOverview(self):
		self.session.open(TimerEditList)

	def infoKeyPressed(self):
		cur = self["list"].getCurrent()
		event = cur[0]
		service = cur[1]
		if event is not None:
			self.session.open(EventViewEPGSelect, event, service, self.eventViewCallback, self.openSingleServiceEPG, self.openMultiServiceEPG, self.openSimilarList)

	def openSimilarList(self, eventid, refstr):
		self.session.open(EPGSelection, refstr, None, eventid)

	def openSingleServiceEPG(self):
		ref = self["list"].getCurrent()[1].ref.toString()
		if ref:
			self.session.openWithCallback(self.doRefresh, EPGSelection, ref, self.zapFunc, serviceChangeCB=self["list"].moveToFromEPG)

	def openMultiServiceEPG(self):
		if self.services:
			self.session.openWithCallback(self.doRefresh, EPGSelection, self.services, self.zapFunc, None, self.bouquetChangeCB)

	def setServices(self, services):
		self.services = services
		self.onCreate()

	def doRefresh(self, answer):
		serviceref = Screens.InfoBar.InfoBar.instance.servicelist.getCurrentSelection()
		l = self["list"]
		l.moveToService(serviceref)
		l.setCurrentlyPlaying(serviceref)
		self.moveTimeLines()

	def onCreate(self):
		serviceref = Screens.InfoBar.InfoBar.instance.servicelist.getCurrentSelection()
		l = self["list"]
		l.setShowServiceMode(config.misc.graph_mepg.servicetitle_mode.value)
		self["timeline_text"].setDateFormat(config.misc.graph_mepg.servicetitle_mode.value)
		l.fillMultiEPG(self.services, self.ask_time)
		l.moveToService(serviceref)
		l.setCurrentlyPlaying(serviceref)
		self.moveTimeLines()

	def eventViewCallback(self, setEvent, setService, val):
		l = self["list"]
		old = l.getCurrent()
		self.updEvent(val, False)
		cur = l.getCurrent()
		if cur[0] is None and cur[1].ref != old[1].ref:
			self.eventViewCallback(setEvent, setService, val)
		else:
			setService(cur[1])
			setEvent(cur[0])

	def preview(self):
		ref = self["list"].getCurrent()[1]
		if ref:
			self.zapFunc(ref.ref, preview = True)
			self["list"].setCurrentlyPlaying(ref.ref)
			self["list"].l.invalidate()

	def zapTo(self):
		if self.zapFunc and self.key_red_choice == self.ZAP:
			ref = self["list"].getCurrent()[1]
			if ref:
				from Components.ServiceEventTracker import InfoBarCount
				preview = InfoBarCount > 1
				self.zapFunc(ref.ref, preview)
				if self.previousref and self.previousref == ref.ref and not preview:
					config.misc.graph_mepg.save()
					self.close(True)
				self.previousref = ref.ref
				self["list"].setCurrentlyPlaying(ref.ref)
				self["list"].l.invalidate()

	def swapMode(self):
		global listscreen
		listscreen = not listscreen
		self.close(None)

	def eventSelected(self):
		if config.misc.graph_mepg.OKButton.value == "info":
			self.infoKeyPressed()
		else:
			self.zapTo()

	def removeTimer(self, timer):
		timer.afterEvent = AFTEREVENT.NONE
		self.session.nav.RecordTimer.removeEntry(timer)
		self["key_green"].setText(_("Add timer"))
		self.key_green_choice = self.ADD_TIMER

	def disableTimer(self, timer, state, repeat=False, record=False):
		if repeat:
			if record:
				title_text = _("Repeating event currently recording.\nWhat do you want to do?")
				menu = [(_("Stop current event but not coming events"), "stoponlycurrent"),(_("Stop current event and disable coming events"), "stopall")]
				if not timer.disabled:
					menu.append((_("Don't stop current event but disable coming events"), "stoponlycoming"))
			else:
				title_text = _("Attention, this is repeated timer!\nWhat do you want to do?")
				menu = [(_("Disable current event but not coming events"), "nextonlystop"),(_("Disable timer"), "simplestop")]
			self.session.openWithCallback(boundFunction(self.runningEventCallback, timer, state), ChoiceBox, title=title_text, list=menu)
		elif timer.state == state:
			timer.disable()
			self.session.nav.RecordTimer.timeChanged(timer)
			self["key_green"].setText(_("Add timer"))
			self.key_green_choice = self.ADD_TIMER

	def runningEventCallback(self, t, state, result):
		if result is not None and t.state == state:
			findNextRunningEvent = True
			findEventNext = False
			if result[1] == "nextonlystop":
				findEventNext = True
				t.disable()
				self.session.nav.RecordTimer.timeChanged(t)
				t.processRepeated(findNextEvent=True)
				t.enable()
			if result[1] in ("stoponlycurrent", "stopall"):
				findNextRunningEvent = False
				t.enable()
				t.processRepeated(findRunningEvent=False)
				self.session.nav.RecordTimer.doActivate(t)
			if result[1] in ("stoponlycoming", "stopall", "simplestop"):
				findNextRunningEvent = True
				t.disable()
			self.session.nav.RecordTimer.timeChanged(t)
			t.findRunningEvent = findNextRunningEvent
			t.findNextEvent = findEventNext
			if result[1] in ("stoponlycurrent", "stopall", "simplestop", "nextonlystop"):
				self["key_green"].setText(_("Add timer"))
				self.key_green_choice = self.ADD_TIMER

	def timerAdd(self):
		cur = self["list"].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		isRecordEvent = isRepeat = firstNextRepeatEvent = isRunning = False
		eventid = event.getEventId()
		begin = event.getBeginTime()
		end = begin + event.getDuration()
		refstr = ':'.join(serviceref.ref.toString().split(':')[:11])
		for timer in self.session.nav.RecordTimer.timer_list:
			needed_ref = ':'.join(timer.service_ref.ref.toString().split(':')[:11]) == refstr
			if needed_ref and timer.eit == eventid and (begin < timer.begin <= end or timer.begin <= begin <= timer.end):
				isRecordEvent = True
				break
			elif needed_ref and timer.repeated and self.session.nav.RecordTimer.isInRepeatTimer(timer, event):
				isRecordEvent = True
				break
		if isRecordEvent:
			isRepeat = timer.repeated
			prev_state = timer.state
			isRunning = prev_state in (1, 2)
			title_text = isRepeat and _("Attention, this is repeated timer!\n") or ""
			firstNextRepeatEvent = isRepeat and (begin < timer.begin <= end or timer.begin <= begin <= timer.end) and not timer.justplay 
			menu = [(_("Delete timer"), "delete"),(_("Edit timer"), "edit")]
			buttons = ["red", "green"]
			if not isRunning:
				if firstNextRepeatEvent and timer.isFindRunningEvent() and not timer.isFindNextEvent():
					menu.append((_("Options disable timer"), "disablerepeat"))
				else:
					menu.append((_("Disable timer"), "disable"))
				buttons.append("yellow")
			elif prev_state == 2 and firstNextRepeatEvent:
				menu.append((_("Options disable timer"), "disablerepeatrunning"))
				buttons.append("yellow")
			menu.append((_("Timer Overview"), "timereditlist"))
			def timerAction(choice):
				if choice is not None:
					if choice[1] == "delete":
						self.removeTimer(timer)
					elif choice[1] == "edit":
						self.session.open(TimerEntry, timer)
					elif choice[1] == "disable":
						self.disableTimer(timer, prev_state)
					elif choice[1] == "timereditlist":
						self.session.open(TimerEditList)
					elif choice[1] == "disablerepeatrunning":
						self.disableTimer(timer, prev_state, repeat=True, record=True)
					elif choice[1] == "disablerepeat":
						self.disableTimer(timer, prev_state, repeat=True)
			self.session.openWithCallback(timerAction, ChoiceBox, title=title_text + _("Select action for timer '%s'.") % timer.name, list=menu, keys=buttons)
		else:
			newEntry = RecordTimerEntry(serviceref, checkOldTimers = True, *parseEvent(event))
			self.session.openWithCallback(self.finishedTimerAdd, TimerEntry, newEntry)

	def finishedTimerAdd(self, answer):
		print "finished add"
		if answer[0]:
			entry = answer[1]
			simulTimerList = self.session.nav.RecordTimer.record(entry)
			if simulTimerList is not None:
				for x in simulTimerList:
					if x.setAutoincreaseEnd(entry):
						self.session.nav.RecordTimer.timeChanged(x)
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList is not None:
					if not entry.repeated and not config.recording.margin_before.value and not config.recording.margin_after.value and len(simulTimerList) > 1:
						change_time = False
						conflict_begin = simulTimerList[1].begin
						conflict_end = simulTimerList[1].end
						if conflict_begin == entry.end:
							entry.end -= 30
							change_time = True
						elif entry.begin == conflict_end:
							entry.begin += 30
							change_time = True
						if change_time:
							simulTimerList = self.session.nav.RecordTimer.record(entry)
					if simulTimerList is not None:
						self.session.openWithCallback(self.finishSanityCorrection, TimerSanityConflict, simulTimerList)
						return
			cur = self["list"].getCurrent()
			event = cur and cur[0]
			if event:
				begin = event.getBeginTime()
				end = begin + event.getDuration()
				if begin < entry.begin <= end or entry.begin <= begin <= entry.end:
					self["key_green"].setText(_("Change timer"))
					self.key_green_choice = self.REMOVE_TIMER
		else:
			self["key_green"].setText(_("Add timer"))
			self.key_green_choice = self.ADD_TIMER
			print "Timeredit aborted"

	def finishSanityCorrection(self, answer):
		self.finishedTimerAdd(answer)

	def onSelectionChanged(self):
		cur = self["list"].getCurrent()
		event = cur[0]
		self["Event"].newEvent(event)

		if cur[1] is None or cur[1].getServiceName() == "":
			if self.key_green_choice != self.EMPTY:
				self["key_green"].setText("")
				self.key_green_choice = self.EMPTY
			if self.key_red_choice != self.EMPTY:
				self["key_red"].setText("")
				self.key_red_choice = self.EMPTY
			return

		servicerefref = cur[1].ref
		self["Service"].newService(servicerefref)

		if self.key_red_choice != self.ZAP:
			self["key_red"].setText(_("Zap"))
			self.key_red_choice = self.ZAP

		if not event:
			if self.key_green_choice != self.EMPTY:
				self["key_green"].setText("")
				self.key_green_choice = self.EMPTY
			return

		eventid = event.getEventId()
		begin = event.getBeginTime()
		end = begin + event.getDuration()
		refstr = ':'.join(servicerefref.toString().split(':')[:11])
		isRecordEvent = False
		for timer in self.session.nav.RecordTimer.timer_list:
			needed_ref = ':'.join(timer.service_ref.ref.toString().split(':')[:11]) == refstr
			if needed_ref and (timer.eit == eventid and (begin < timer.begin <= end or timer.begin <= begin <= timer.end) or timer.repeated and self.session.nav.RecordTimer.isInRepeatTimer(timer, event)):
				isRecordEvent = True
				break
		if isRecordEvent and self.key_green_choice != self.REMOVE_TIMER:
			self["key_green"].setText(_("Change timer"))
			self.key_green_choice = self.REMOVE_TIMER
		elif not isRecordEvent and self.key_green_choice != self.ADD_TIMER:
			self["key_green"].setText(_("Add timer"))
			self.key_green_choice = self.ADD_TIMER

	def moveTimeLines(self, force=False):
		self.updateTimelineTimer.start((60 - (int(time()) % 60)) * 1000)	#keep syncronised
		self["timeline_text"].setEntries(self["list"], self["timeline_now"], self.time_lines, force)
		self["list"].l.invalidate() # not needed when the zPosition in the skin is correct! ?????
