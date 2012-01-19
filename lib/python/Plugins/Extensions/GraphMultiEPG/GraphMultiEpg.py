from skin import parseColor, parseFont
from Components.config import config, ConfigClock, ConfigInteger, ConfigSubsection, ConfigBoolean
from Components.Pixmap import Pixmap
from Components.Button import Button
from Components.ActionMap import ActionMap
from Components.HTMLComponent import HTMLComponent
from Components.GUIComponent import GUIComponent
from Components.EpgList import Rect
from Components.Sources.Event import Event
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.TimerList import TimerList
from Screens.Screen import Screen
from Screens.EventView import EventViewSimple
from Screens.TimeDateInput import TimeDateInput
from Screens.TimerEntry import TimerEntry
from Screens.EpgSelection import EPGSelection
from Screens.TimerEdit import TimerSanityConflict
from Screens.MessageBox import MessageBox
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT
from ServiceReference import ServiceReference
from Tools.LoadPixmap import LoadPixmap
from enigma import eEPGCache, eListbox, gFont, eListboxPythonMultiContent, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_WRAP, eRect, eTimer
from GraphMultiEpgSetup import GraphMultiEpgSetup

from time import localtime, time, strftime

MAX_TIMELINES = 6

class EPGList(HTMLComponent, GUIComponent):
	def __init__(self, selChangedCB = None, timer = None, time_epoch = 120, overjump_empty = True):
		GUIComponent.__init__(self)
		self.cur_event = None
		self.cur_service = None
		self.offs = 0
		self.timer = timer
		self.onSelChanged = [ ]
		if selChangedCB is not None:
			self.onSelChanged.append(selChangedCB)
		self.l = eListboxPythonMultiContent()
		self.l.setBuildFunc(self.buildEntry)
		self.setOverjump_Empty(overjump_empty)
		self.epgcache = eEPGCache.getInstance()
		self.clock_pixmap = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock.png'))
		self.clock_add_pixmap = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_add.png'))
		self.clock_pre_pixmap = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_pre.png'))
		self.clock_post_pixmap = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_post.png'))
		self.clock_prepost_pixmap = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_prepost.png'))
		self.time_base = None
		self.time_epoch = time_epoch
		self.list = None
		self.event_rect = None
		self.currentlyPlaying = None

		self.foreColor = 0xffffff
		self.foreColorSelected = 0xffc000
		self.borderColor = 0x464445
		self.backColor = 0x595959
		self.backColorSelected = 0x808080
		self.foreColorService = 0xffffff
		self.foreColorServiceSelected = 0x000000
		self.backColorService = 0x000000
		self.backColorServiceSelected = 0xffffff
		self.borderColorService = 0x000000
		self.foreColorNow = 0xffc000
		self.backColorNow = 0x508050

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "EntryForegroundColor":
					self.foreColor = parseColor(value).argb()
				elif attrib == "EntryForegroundColorSelected":
					self.foreColorSelected = parseColor(value).argb()
				elif attrib == "EntryBackgroundColor":
					self.backColor = parseColor(value).argb()
				elif attrib == "EntryBackgroundColorSelected":
					self.backColorSelected = parseColor(value).argb()
				elif attrib == "EntryBorderColor":
					self.borderColor = parseColor(value).argb()
				elif attrib == "ServiceForegroundColor" or attrib == "ServiceNameForegroundColor":
					self.foreColorService = parseColor(value).argb()
				elif attrib == "ServiceForegroundColorSelected":
					self.foreColorServiceSelected = parseColor(value).argb()
				elif attrib == "ServiceBackgroundColor" or attrib == "ServiceNameBackgroundColor":
					self.backColorService = parseColor(value).argb()
				elif attrib == "ServiceBackgroundColorSelected":
					self.backColorServiceSelected = parseColor(value).argb()
				elif attrib == "ServiceBorderColor":
					self.borderColorService = parseColor(value).argb()
				elif attrib == "EntryBackgroundColorNow":
					self.backColorNow = parseColor(value).argb()
				elif attrib == "EntryForegroundColorNow":
					self.foreColorNow = parseColor(value).argb()
				else:
					attribs.append((attrib,value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		# now we know our size and can savely set items per page
		self.setItemsPerPage()
		return rc

	def isSelectable(self, service, sname, event_list):
		return (event_list and len(event_list) and True) or False

	def setOverjump_Empty(self, overjump_empty):
		if overjump_empty:
			self.l.setSelectableFunc(self.isSelectable)

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

	def moveToService(self,serviceref):
		if serviceref is not None:
			for x in range(len(self.list)):
				if self.list[x][0] == serviceref.toString():
					self.instance.moveSelectionTo(x)
					break
	
	def getIndexFromService(self, serviceref):
		if serviceref is not None:
			for x in range(len(self.list)):
				if self.list[x][0] == serviceref.toString():
					return x
		
	def setCurrentIndex(self, index):
		if self.instance is not None:
			self.instance.moveSelectionTo(index)
	
	def getCurrent(self):
		if self.cur_service is None:
			return ( None, None )
		old_service = self.cur_service  #(service, service_name, events)
		events = self.cur_service[2]
		refstr = self.cur_service[0]
		if self.cur_event is None or not events or not len(events):
			return ( None, ServiceReference(refstr) )
		event = events[self.cur_event] #(event_id, event_title, begin_time, duration)
		eventid = event[0]
		service = ServiceReference(refstr)
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
		old_service = self.cur_service  #(service, service_name, events)
		cur_service = self.cur_service = self.l.getCurrentSelection()
		last_time = 0;
		time_base = self.getTimeBase()
		if old_service and self.cur_event is not None:
			events = old_service[2]
			cur_event = events[self.cur_event] #(event_id, event_title, begin_time, duration)
			last_time = cur_event[2]
			if last_time < time_base:
				last_time = time_base
		if cur_service:
			self.cur_event = 0
			events = cur_service[2]
			if events and len(events):
				if last_time:
					best_diff = 0
					best = len(events) #set invalid
					idx = 0
					for event in events: #iterate all events
						ev_time = event[2]
						if ev_time < time_base:
							ev_time = time_base
						diff = abs(ev_time-last_time)
						if (best == len(events)) or (diff < best_diff):
							best = idx
							best_diff = diff
						idx += 1
					if best != len(events):
						self.cur_event = best
			else:
				self.cur_event = None
		self.selEntry(0)

	def selectionChanged(self):
		for x in self.onSelChanged:
			if x is not None:
				x()
#				try:
#					x()
#				except: # FIXME!!!
#					print "FIXME in EPGList.selectionChanged"
#					pass

	GUI_WIDGET = eListbox

	def setItemsPerPage(self):
		h = self.instance.size().height()
		if h > 0:
			self.l.setItemHeight(h / config.misc.graph_mepg.items_per_page.value)
		else:
			self.l.setItemHeight(54) # some default (270/5)

	def setEventFontsize(self):
		self.l.setFont(1, gFont("Regular", config.misc.graph_mepg.ev_fontsize.value))

	def postWidgetCreate(self, instance):
		instance.setWrapAround(True)
		instance.selectionChanged.get().append(self.serviceChanged)
		instance.setContent(self.l)
		self.l.setSelectionClip(eRect(0, 0, 0, 0), False)
		self.l.setFont(0, gFont("Regular", 20))
		self.setEventFontsize()

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.serviceChanged)
		instance.setContent(None)

	def recalcEntrySize(self):
		esize = self.l.getItemSize()
		width = esize.width()
		height = esize.height()
		xpos = 0;
		w = width / 10 * 2;
		self.service_rect = Rect(xpos, 0, w, height)
		xpos += w;
		w = width / 10 * 8;
		self.event_rect = Rect(xpos, 0, w, height)

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
		return xpos+event_rect.left(), width

	def buildEntry(self, service, service_name, events):
		r1 = self.service_rect
		r2 = self.event_rect
		nowPlaying = self.currentlyPlaying.toString()
		serviceForeColor = self.foreColorService
		serviceBackColor = self.backColorService
		if nowPlaying is not None and nowPlaying == service:
			serviceForeColor = self.foreColorServiceSelected
			serviceBackColor = self.backColorServiceSelected

		res = [ None, MultiContentEntryText(
						pos = (r1.x, r1.y),
						size = (r1.w, r1.h),
						font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER,
						text = service_name,
						color = serviceForeColor, color_sel = serviceForeColor,
						backcolor = serviceBackColor, backcolor_sel = serviceBackColor,
						border_width = 1, border_color = self.borderColorService) ]

		if events:
			start = self.time_base+self.offs*self.time_epoch * 60
			end = start + self.time_epoch * 60
			left = r2.x
			top = r2.y
			width = r2.w
			height = r2.h

			now = time()
			for ev in events:  #(event_id, event_title, begin_time, duration)
				stime = ev[2]
				duration = ev[3]
				rec = stime and self.timer.isInTimer(ev[0], stime, duration, service)
				xpos, ewidth = self.calcEntryPosAndWidthHelper(stime, duration, start, end, width)
				if stime <= now and now < stime + duration:
					backColor = self.backColorNow
					foreColor = self.foreColorNow
				else:
					backColor = self.backColor
					foreColor = self.foreColor

				res.append(MultiContentEntryText(
					pos = (left + xpos, top), size = (ewidth, height),
					font = 1, flags = RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_WRAP,
					text = ev[1],
					color = foreColor, color_sel = self.foreColorSelected,
					backcolor = backColor, backcolor_sel = self.backColorSelected,
					border_width = 1, border_color = self.borderColor))
				if rec and ewidth > 23:
					res.append(MultiContentEntryPixmapAlphaTest(
						pos = (left + xpos + ewidth - 22, top + height - 22), size = (21, 21),
						png = self.getClockPixmap(service, stime, duration, ev[0]),
						backcolor = backColor, backcolor_sel = self.backColorSelected))
		return res

	def selEntry(self, dir, visible = True):
		cur_service = self.cur_service    #(service, service_name, events)
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
		if cur_service and valid_event:
			entry = entries[self.cur_event] #(event_id, event_title, begin_time, duration)
			time_base = self.time_base + self.offs*self.time_epoch * 60
			xpos, width = self.calcEntryPosAndWidth(self.event_rect, time_base, self.time_epoch, entry[2], entry[3])
			self.l.setSelectionClip(eRect(xpos, 0, width, self.event_rect.h), visible and update)
		else:
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

	def fillMultiEPG(self, services, stime = -1):
		if services is None:
			time_base = self.time_base + self.offs * self.time_epoch * 60
			test = [ (service[0], 0, time_base, self.time_epoch) for service in self.list ]
		else:
			self.cur_event = None
			self.cur_service = None
			self.time_base = int(stime)
			test = [ (service.ref.toString(), 0, self.time_base, self.time_epoch) for service in services ]
		test.insert(0, 'XRnITBD')
		epg_data = self.queryEPG(test)
		self.list = [ ]
		tmp_list = None
		service = ""
		sname = ""
		for x in epg_data:
			if service != x[0]:
				if tmp_list is not None:
					self.list.append((service, sname, tmp_list[0][0] is not None and tmp_list or None))
				service = x[0]
				sname = x[1]
				tmp_list = [ ]
			tmp_list.append((x[2], x[3], x[4], x[5]))
		if tmp_list and len(tmp_list):
			self.list.append((service, sname, tmp_list[0][0] is not None and tmp_list or None))

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

class TimelineText(HTMLComponent, GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setSelectionClip(eRect(0, 0, 0, 0))
		self.l.setItemHeight(25);
		self.foreColor = 0xffc000
		self.borderColor = 0x000000
		self.backColor = 0x000000
		self.borderWidth = 1

	GUI_WIDGET = eListbox

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if   attrib == "foregroundColor":
					self.foreColor = parseColor(value).argb()
				elif attrib == "borderColor":
					self.borderColor = parseColor(value).argb()
				elif attrib == "backgroundColor":
					self.backColor = parseColor(value).argb()
				elif attrib == "font":
					self.l.setFont(0, parseFont(value,  ((1, 1), (1, 1)) ))
				elif attrib == "borderWidth":
					self.borderWidth = int(value)
				else:
					attribs.append((attrib,value))
			self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop, screen)

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		self.l.setFont(0, gFont("Regular", 20))

	def setEntries(self, l, timeline_now, time_lines):
		service_rect = l.getServiceRect()
		event_rect = l.getEventRect()
		time_epoch = l.getTimeEpoch()
		time_base = l.getTimeBase()
		itemHeight = self.l.getItemSize().height()

		if event_rect is None or time_epoch is None or time_base is None:
			return
		time_steps = 60 if time_epoch > 180 else 30

		num_lines = time_epoch / time_steps
		incWidth = event_rect.width() / num_lines
		eventLeft = event_rect.left()
		timeStepsCalc = time_steps * 60

		res = [ None ]

		# Note: event_rect and service_rect are relative to the timeline_text position
		#       while the time lines are relative to the GraphEPG screen position!
		res.append( MultiContentEntryText(
						pos = (0, 0),
						size = (service_rect.width(), itemHeight),
						font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER,
						text = strftime("%A %d %B", localtime(time_base)),
						color = self.foreColor, color_sel = self.foreColor,
						backcolor = self.backColor, backcolor_sel = self.backColor,
						border_width = self.borderWidth, border_color = self.borderColor))

		xpos = 0 # eventLeft
		for x in range(0, num_lines):
			res.append( MultiContentEntryText(
				pos = (service_rect.width() + xpos, 0),
				size = (incWidth, itemHeight),
				font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER,
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
		self.l.setList([res])

config.misc.graph_mepg = ConfigSubsection()
config.misc.graph_mepg.prev_time = ConfigClock(default = time())
config.misc.graph_mepg.prev_time_period = ConfigInteger(default = 120, limits = (60, 300))
config.misc.graph_mepg.ev_fontsize = ConfigInteger(default = 14, limits = (10, 25))
config.misc.graph_mepg.items_per_page = ConfigInteger(default = 5, limits = (3, 10))
config.misc.graph_mepg.overjump = ConfigBoolean(default = True)

class GraphMultiEPG(Screen):
	EMPTY = 0
	ADD_TIMER = 1
	REMOVE_TIMER = 2
	
	ZAP = 1

	def __init__(self, session, services, zapFunc=None, bouquetChangeCB=None, bouquetname=""):
		Screen.__init__(self, session)
		self.bouquetChangeCB = bouquetChangeCB
		now = time()
		self.ask_time = now - now % 900
		self.closeRecursive = False
		self["key_red"] = Button("")
		self["key_green"] = Button("")
		self["key_blue"] = Button(_("Setup"))

		self.key_green_choice = self.EMPTY
		self.key_red_choice = self.EMPTY
		self["timeline_text"] = TimelineText()
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

		self["actions"] = ActionMap(["EPGSelectActions", "OkCancelActions"],
			{
				"cancel": self.closeScreen,
				"ok": self.eventSelected,
				"timerAdd": self.timerAdd,
				"info": self.infoKeyPressed,
				"red": self.zapTo,
				"blue": self.showSetup,
				"input_date_time": self.enterDateTime,
				"nextBouquet": self.nextBouquet,
				"prevBouquet": self.prevBouquet,
				"nextService": self.nextPressed,
				"prevService": self.prevPressed,
			})
		self["actions"].csel = self

		self["input_actions"] = ActionMap(["InputActions"],
			{
				"left": self.leftPressed,
				"right": self.rightPressed,
				"1": self.key1,
				"2": self.key2,
				"3": self.key3,
				"4": self.key4,
				"5": self.key5,
			},-1)

		self.updateTimelineTimer = eTimer()
		self.updateTimelineTimer.callback.append(self.moveTimeLines)
		self.updateTimelineTimer.start(60 * 1000)
		self.onLayoutFinish.append(self.onCreate)

	def prevPressed(self):
		self.updEvent(-2)

	def nextPressed(self):
		self.updEvent(+2)

	def leftPressed(self):
		self.updEvent(-1)

	def rightPressed(self):
		self.updEvent(+1)

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
				self.ask_time = ret[1] - ret[1] % 900
				l = self["list"]
				l.resetOffset()
				l.fillMultiEPG(self.services, self.ask_time)
				self.moveTimeLines(True)

	def showSetup(self):
		self.session.openWithCallback(self.onSetupClose, GraphMultiEpgSetup)

	def onSetupClose(self, ignore = -1):
		l = self["list"]
		l.setItemsPerPage()
		l.setEventFontsize()
		l.setEpoch(config.misc.graph_mepg.prev_time_period.value)
		l.setOverjump_Empty(config.misc.graph_mepg.overjump.value)
		self.moveTimeLines()
		
	def closeScreen(self):
		config.misc.graph_mepg.save()
		self.close(self.closeRecursive)

	def infoKeyPressed(self):
		cur = self["list"].getCurrent()
		event = cur[0]
		service = cur[1]
		if event is not None:
			self.session.open(EventViewSimple, event, service, self.eventViewCallback, self.openSimilarList)

	def openSimilarList(self, eventid, refstr):
		self.session.open(EPGSelection, refstr, None, eventid)

	def setServices(self, services):
		self.services = services
		self.onCreate()

	def onCreate(self):
		serviceref = self.session.nav.getCurrentlyPlayingServiceReference()
		l = self["list"]
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

	def zapTo(self):
		if self.zapFunc and self.key_red_choice == self.ZAP:
			self.closeRecursive = True
			ref = self["list"].getCurrent()[1]
			if ref:
				self.zapFunc(ref.ref)
				self["list"].setCurrentlyPlaying(ref.ref)
				self["list"].l.invalidate()

	def eventSelected(self):
		self.infoKeyPressed()

	def removeTimer(self, timer):
		timer.afterEvent = AFTEREVENT.NONE
		self.session.nav.RecordTimer.removeEntry(timer)
		self["key_green"].setText(_("Add timer"))
		self.key_green_choice = self.ADD_TIMER
	
	def timerAdd(self):
		cur = self["list"].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				cb_func = lambda ret : not ret or self.removeTimer(timer)
				self.session.openWithCallback(cb_func, MessageBox, _("Do you really want to delete %s?") % event.getEventName())
				break
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
					self.session.openWithCallback(self.finishSanityCorrection, TimerSanityConflict, simulTimerList)
			self["key_green"].setText(_("Remove timer"))
			self.key_green_choice = self.REMOVE_TIMER
		else:
			self["key_green"].setText(_("Add timer"))
			self.key_green_choice = self.ADD_TIMER
			print "Timeredit aborted"
	
	def finishSanityCorrection(self, answer):
		self.finishedTimerAdd(answer)

	def onSelectionChanged(self):
		cur = self["list"].getCurrent()
		if cur is None:
			if self.key_green_choice != self.EMPTY:
				self["key_green"].setText("")
				self.key_green_choice = self.EMPTY
			if self.key_red_choice != self.EMPTY:
				self["key_red"].setText("")
				self.key_red_choice = self.EMPTY
			return
		
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
		elif self.key_red_choice != self.ZAP:
				self["key_red"].setText("Zap")
				self.key_red_choice = self.ZAP
			
		if not event:
			if self.key_green_choice != self.EMPTY:
				self["key_green"].setText("")
				self.key_green_choice = self.EMPTY
			return
		
		serviceref = cur[1]
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		isRecordEvent = False
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				isRecordEvent = True
				break
		if isRecordEvent and self.key_green_choice != self.REMOVE_TIMER:
			self["key_green"].setText(_("Remove timer"))
			self.key_green_choice = self.REMOVE_TIMER
		elif not isRecordEvent and self.key_green_choice != self.ADD_TIMER:
			self["key_green"].setText(_("Add timer"))
			self.key_green_choice = self.ADD_TIMER
	
	def moveTimeLines(self, force=False):
		self.updateTimelineTimer.start((60 - (int(time()) % 60)) * 1000)	#keep syncronised
		self["list"].l.invalidate() # not needed when the zPosition in the skin is correct! ?????
		self["timeline_text"].setEntries(self["list"], self["timeline_now"], self.time_lines)
