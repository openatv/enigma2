from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from Components.AVSwitch import AVSwitch
from Components.config import config
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest

from enigma import eEPGCache, eListbox, eListboxPythonMultiContent, ePicLoad, gFont, eRect, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_WRAP

from Tools.LoadPixmap import LoadPixmap

from time import localtime, time
from ServiceReference import ServiceReference
from Tools.Directories import pathExists, resolveFilename, SCOPE_CURRENT_SKIN
from os import listdir, path

EPG_TYPE_SINGLE = 0
EPG_TYPE_MULTI = 1
EPG_TYPE_SIMILAR = 2
EPG_TYPE_ENHANCED = 3
EPG_TYPE_INFOBAR = 4
EPG_TYPE_GRAPH = 5

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
	searchPiconPaths = ['/usr/share/enigma2/picon/','/picon/']
	for f in listdir("/media"):
		if pathExists("/media/" + f + '/picon/'):
			searchPiconPaths.append('/media/' + f + '/picon/')
	if path.exists("/media/net"):
		for f in listdir("/media/net"):
			if pathExists("/media/net/" + f + '/picon/'):
				searchPiconPaths.append('/media/net/' + f + '/picon/')
	def __init__(self, type=EPG_TYPE_SINGLE, selChangedCB=None, timer = None, time_epoch = 120, overjump_empty=False):
		self.days = (_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun"))
		self.cur_event = None
		self.cur_service = None
		self.offs = 0
		self.curr_refcool = None	
		self.coolheight = 54
		self.time_base = None
		self.time_epoch = time_epoch
		self.event_rect = None

		self.timer = timer
		self.onSelChanged = [ ]
		if selChangedCB is not None:
			self.onSelChanged.append(selChangedCB)
		GUIComponent.__init__(self)
		self.type=type
		self.l = eListboxPythonMultiContent()
		self.l.setFont(0, gFont("Regular", 22))
		self.l.setFont(1, gFont("Regular", 16))
		if type == EPG_TYPE_SINGLE:
			self.l.setBuildFunc(self.buildSingleEntry)
		elif type == EPG_TYPE_ENHANCED:
			self.l.setBuildFunc(self.buildSingleEntry)
		elif type == EPG_TYPE_INFOBAR:
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
		if type == EPG_TYPE_GRAPH:
			self.setOverjump_Empty(overjump_empty)
		self.nowForeColor = 0xffffff
		self.nowForeColorSelected = 0x000000
		self.foreColor = 0xffffff
		self.foreColorSelected = 0x000000
		self.borderColor = 0xC0C0C0
		self.backColor = 0x2D455E
		self.backColorSelected = 0xC0C0C0
		self.nowBackColor = 0x00825F
		self.nowBackColorSelected = 0x4800FF
		self.foreColorService = 0xffffff
		self.backColorService = 0x000000
		self.picload = ePicLoad()
		self.frameBufferScale = AVSwitch().getFramebufferScale()


	def applySkin(self, desktop, screen):
		if self.type == EPG_TYPE_GRAPH:
			if self.skinAttributes is not None:
				attribs = [ ]
				for (attrib, value) in self.skinAttributes:
					if attrib == "EntryForegroundColor":
						self.foreColor = parseColor(value).argb()
					elif attrib == "EntryForegroundColorSelected":
						self.foreColorSelected = parseColor(value).argb()
					elif attrib == "EntryNowForegroundColorSelected":
						self.nowForeColorSelected = parseColor(value).argb()
					elif attrib == "EntryNowForegroundColor":
						self.nowForeColor = parseColor(value).argb()
					elif attrib == "EntryBorderColor":
						self.borderColor = parseColor(value).argb()
					elif attrib == "EntryBackgroundColor":
						self.backColor = parseColor(value).argb()
					elif attrib == "EntryNowBackgroundColor":
						self.nowBackColor = parseColor(value).argb()
					elif attrib == "EntryBackgroundColorSelected":
						self.backColorSelected = parseColor(value).argb()
					elif attrib == "EntryNowBackgroundColorSelected":
						self.nowBackColorSelected = parseColor(value).argb()
					elif attrib == "ServiceNameForegroundColor":
						self.foreColorService = parseColor(value).argb()
					elif attrib == "ServiceNameBackgroundColor":
						self.backColorService = parseColor(value).argb()
					else:
						attribs.append((attrib,value))
				self.skinAttributes = attribs
			rc = GUIComponent.applySkin(self, desktop, screen)
			self.setItemsPerPage()
			return rc
		else:
			rc = GUIComponent.applySkin(self, desktop, screen)
			return rc


	def isSelectable(self, service, sname, event_list):
		return (event_list and len(event_list) and True) or False

	def setOverjump_Empty(self, overjump_empty):
		if overjump_empty:
			self.l.setSelectableFunc(self.isSelectable)
		
	def setEpoch(self, epoch):
		self.offs = 0
		self.time_epoch = epoch
		self.fillGraphEPG(None)

	def setEpoch2(self, epoch):
		self.offs = 0
		self.time_epoch = epoch

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

	def getCurrentChangeCount(self):
		if self.type == EPG_TYPE_MULTI and self.l.getCurrentSelection() is not None:
			return self.l.getCurrentSelection()[0]
		return 0

	def getCurrent(self):
		if self.type == EPG_TYPE_GRAPH:
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
		else:
			idx=0
			if self.type == EPG_TYPE_MULTI:
				idx += 1

			tmp = self.l.getCurrentSelection()
			if tmp is None:
				return ( None, None )
			eventid = tmp[idx+1]
			service = ServiceReference(tmp[idx])
			event = self.getEventFromId(service, eventid)
			return ( event, service )

	def moveUp(self):
		self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)

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
#		ItemHeight = None
		config.GraphEPG.item_hight.value = self.instance.size().height()
		if not config.GraphEPG.coolswitch.value == "14-16":
			self.l.setItemHeight(config.GraphEPG.item_hight.value / config.GraphEPG.items_per_page.value)
			self.coolheight = (config.GraphEPG.item_hight.value / config.GraphEPG.items_per_page.value)
		if ((config.GraphEPG.item_hight.value / config.GraphEPG.items_per_page.value) / 3) > 27:
			config.GraphEPG.item_hight16.value = ((config.GraphEPG.item_hight.value / config.GraphEPG.items_per_page.value) / 3)
		elif ((config.GraphEPG.item_hight.value / config.GraphEPG.items_per_page.value) / 2) > 27:
			config.GraphEPG.item_hight16.value = ((config.GraphEPG.item_hight.value / config.GraphEPG.items_per_page.value) / 2)
		else:
			config.GraphEPG.item_hight16.value = 27
		if config.GraphEPG.coolswitch.value == "14-16":
			self.coolheight = config.GraphEPG.item_hight16.value
			self.l.setItemHeight(config.GraphEPG.item_hight16.value)

	def setServiceFontsize(self):
		self.l.setFont(0, gFont("Regular", config.GraphEPG.Left_Fontsize.value))

	def setEventFontsize(self):
		self.l.setFont(1, gFont("Regular", config.GraphEPG.Fontsize.value))

	def postWidgetCreate(self, instance):
		if self.type == EPG_TYPE_GRAPH:
			instance.setWrapAround(True)
			instance.selectionChanged.get().append(self.serviceChanged)
			instance.setContent(self.l)
			self.l.setSelectionClip(eRect(0,0,0,0), False)
			self.setServiceFontsize()
			self.setEventFontsize()
		else:
			instance.setWrapAround(True)
			instance.selectionChanged.get().append(self.selectionChanged)
			instance.setContent(self.l)

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

		if self.type == EPG_TYPE_SINGLE:
			self.weekday_rect = Rect(0, 0, width/20*2-10, height)
			self.datetime_rect = Rect(width/20*2, 0, width/20*5-15, height)
			self.descr_rect = Rect(width/20*7, 0, width/20*13, height)
		elif self.type == EPG_TYPE_ENHANCED:
			self.weekday_rect = Rect(0, 0, width/20*2-10, height)
			self.datetime_rect = Rect(width/20*2, 0, width/20*5-15, height)
			self.descr_rect = Rect(width/20*7, 0, width/20*13, height)
		elif self.type == EPG_TYPE_INFOBAR:
			self.weekday_rect = Rect(0, 0, width/20*2-10, height)
			self.datetime_rect = Rect(width/20*2, 0, width/20*5-15, height)
			self.descr_rect = Rect(width/20*7, 0, width/20*13, height)
		elif self.type == EPG_TYPE_MULTI:
			xpos = 0;
			w = width/10*3;
			self.service_rect = Rect(xpos, 0, w-10, height)
			xpos += w;
			w = width/10*2;
			self.start_end_rect = Rect(xpos, 0, w-10, height)
			self.progress_rect = Rect(xpos, 4, w-10, height-8)
			xpos += w
			w = width/10*5;
			self.descr_rect = Rect(xpos, 0, width, height)
		elif self.type == EPG_TYPE_GRAPH:
			global ItemHeight
			#esize = self.l.getItemSize()
			#width = esize.width()
			#height = esize.height()
			xpos = 0;
			if config.GraphEPG.UsePicon.value:
				w = config.GraphEPG.left8.value;
				ItemHeight = height;
			elif not config.GraphEPG.UsePicon.value:
				w = config.GraphEPG.left16.value;
				ItemHeight = height;
			self.service_rect = Rect(xpos, 0, w, height)
			xpos += w;
			w = width - xpos;
			self.event_rect = Rect(xpos, 0, w, height)
		else: # EPG_TYPE_SIMILAR
			self.weekday_rect = Rect(0, 0, width/20*2-10, height)
			self.datetime_rect = Rect(width/20*2, 0, width/20*5-15, height)
			self.service_rect = Rect(width/20*7, 0, width/20*13, height)

	def calcEntryPosAndWidthHelper(self, stime, duration, start, end, width):
		xpos = (stime - start) * width / (end - start)
		ewidth = (stime + duration - start) * width / (end - start) + 1
		ewidth -= xpos;
		if xpos < 0:
			ewidth += xpos;
			xpos = 0;
		if (xpos+ewidth) > width:
			ewidth = width - xpos
		return xpos, ewidth

	def calcEntryPosAndWidth(self, event_rect, time_base, time_epoch, ev_start, ev_duration):
		xpos, width = self.calcEntryPosAndWidthHelper(ev_start, ev_duration, time_base, time_base + time_epoch * 60, event_rect.width())
		return xpos+event_rect.left(), width

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
		rec=beginTime and (self.timer.isInTimer(eventId, beginTime, duration, service))
		if rec:
			clock_pic = self.getClockPixmap(service, beginTime, duration, eventId)
		else:
			clock_pic = None
		return (clock_pic, rec)

	def buildSingleEntry(self, service, eventId, beginTime, duration, EventName):
		(clock_pic, rec) = self.getPixmapForEntry(service, eventId, beginTime, duration)
		r1=self.weekday_rect
		r2=self.datetime_rect
		r3=self.descr_rect
		t = localtime(beginTime)
		res = [
			None, # no private data needed
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_RIGHT, self.days[t[6]]),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, r2.w, r1.h, 0, RT_HALIGN_RIGHT, "%2d.%02d, %02d:%02d"%(t[2],t[1],t[3],t[4]))
		]
		if rec:
			res.extend((
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, r3.x, r3.y, 21, 21, clock_pic),
				(eListboxPythonMultiContent.TYPE_TEXT, r3.x + 25, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT, EventName)
			))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT, EventName))
		return res

	def buildSimilarEntry(self, service, eventId, beginTime, service_name, duration):
		(clock_pic, rec) = self.getPixmapForEntry(service, eventId, beginTime, duration)
		r1=self.weekday_rect
		r2=self.datetime_rect
		r3=self.service_rect
		t = localtime(beginTime)
		res = [
			None,  # no private data needed
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h, 0, RT_HALIGN_RIGHT, self.days[t[6]]),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, r2.w, r1.h, 0, RT_HALIGN_RIGHT, "%2d.%02d, %02d:%02d"%(t[2],t[1],t[3],t[4]))
		]
		if rec:
			res.extend((
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, r3.x, r3.y, 21, 21, clock_pic),
				(eListboxPythonMultiContent.TYPE_TEXT, r3.x + 25, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT, service_name)
			))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w, r3.h, 0, RT_HALIGN_LEFT, service_name))
		return res

	def buildMultiEntry(self, changecount, service, eventId, beginTime, duration, EventName, nowTime, service_name):
		(clock_pic, rec) = self.getPixmapForEntry(service, eventId, beginTime, duration)
		r1=self.service_rect
		r2=self.progress_rect
		r3=self.descr_rect
		r4=self.start_end_rect
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
#				print "begin", begin
#				print "end", end
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

	def buildGraphEntry(self, service, service_name, events):
		if service == self.cur_service[0]:
			piconbkcolor = 0xB5B5B5
		else:
			piconbkcolor = 0x909090
		r1=self.service_rect
		r2=self.event_rect
		foreColor = self.foreColor
		foreColorSelected = self.foreColorSelected
		backColor = self.backColor
		backColorSelected = self.backColorSelected
		borderColor = self.borderColor
		backColorService = self.backColorService
		backColorOrig = self.backColor # normale Eventsfarbe
#		VIXEPGEvent = 1
		if self.curr_refcool.toString() == service:
#			backColor = 0x516b96
#			backColorOrig = 0x516b96
			backColorService = 0x516b96
		res = [ None ]
		picon = self.findPicon(service, service_name)

		if picon is None:
			res.append(MultiContentEntryText(
			pos = (r1.left(),r1.top()),
			size = (r1.width(), r1.height()),
				font = 0, flags = RT_HALIGN_CENTER | RT_VALIGN_CENTER,
			text = service_name,
				color = self.foreColorService,
				border_width = 1, border_color = borderColor,
				backcolor = backColorService, backcolor_sel = backColorService)) #backcolor_sel= Event left select

		else:
			piconHeight = r1.height()-2
			piconWidth = r1.width()-2
			self.picload.setPara((piconWidth, piconHeight, self.frameBufferScale[0], self.frameBufferScale[1], 1, 1, "#FF000000"))
			self.picload.startDecode(picon, piconWidth, piconHeight, False)
			res.append(MultiContentEntryPixmapAlphaTest(
				pos = (r1.left(),r1.top()),
				size = (r1.width(), r1.height()),
				png = self.picload.getData(),
				backcolor = piconbkcolor,
				backcolor_sel = 0))

		if events:
			start = self.time_base+self.offs*self.time_epoch*60
			end = start + self.time_epoch * 60
			left = r2.left()
			top = r2.top()
			width = r2.width()
			height = r2.height()
			coolflags = RT_HALIGN_LEFT | RT_VALIGN_CENTER
			thepraefix = " "

			if self.coolheight > 30:
				coolflags = RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_WRAP
				thepraefix = ""
#				if service == self.cur_service[0]:
#					backColorSelected = self.backColorSelected
			now = int(time())
			for ev in events:  #(event_id, event_title, begin_time, duration)
				rec=ev[2] and self.timer.isInTimer(ev[0], ev[2], ev[3], service)
				xpos, ewidth = self.calcEntryPosAndWidthHelper(ev[2], ev[3], start, end, width)

				if self.curr_refcool.toString() == service:
					backColorOrig = 0x516b96

				if ev[2] <= now and (ev[2] + ev[3]) > now:
					foreColor = self.nowForeColor
					foreColorSelected = self.nowForeColorSelected
					backColor = self.nowBackColor
#						backColorSelected = self.backColorSelected # Event Selected
				else:
					backColor = backColorOrig 
#						backColorSelected = self.backColorSelected

					foreColor = self.foreColor
					foreColorSelected = self.foreColorSelected

				if rec:
					cooltyp = self.GraphEPGRecRed(service, ev[2], ev[3], ev[0])
					if cooltyp == "record":
						backColor = 0xcf5353 
						backColorSelected = 0xf7664b
					elif cooltyp == "justplay":						
						backColor = 0x669466
						backColorSelected = 0x61a161
#					elif cooltyp == "nichts" and cooltyp != "record":						
#						backColor = 0xB6FF00
#						backColorSelected = 0xC0FF23
					else:
						backColor = backColorOrig 
						backColorSelected = self.backColorSelected

				res.append(MultiContentEntryText(
					pos = (left+xpos, top), size = (ewidth, height),
					font = 1, flags = coolflags,
					text = thepraefix + ev[1], color = foreColor, color_sel = foreColorSelected,
					backcolor = backColor, backcolor_sel = backColorSelected, border_width = 1, border_color = borderColor)) # Color select Event

		else:
			left = r2.left()
			top = r2.top()
			width = r2.width()
			height = r2.height()
			res.append(MultiContentEntryText(			
				pos = (left, top), size = (width, height),
				font = 1, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				text = " ", color = foreColor, color_sel = foreColorSelected,
				border_width = 1, backcolor_sel = backColorSelected, border_color = borderColor))
		return res

	def findPicon(self, service = None, serviceName = None):
		if config.GraphEPG.UsePicon.value:
			service_refstr = None
			serviceName_ref = None
			if service is not None:
				serviceName_ref = ServiceReference(service).getServiceName()	#get true servicename
				serviceName_ref = serviceName_ref.replace('\xc2\x87', '').replace('\xc2\x86', '').decode("utf-8").encode("latin1")
				pos = service.rfind(':')
				if pos != -1:
					service_refstr = service[:pos].rstrip(':').replace(':','_')
				for path in self.searchPiconPaths:
					pngname = path + service_refstr + ".png"
					if pathExists(pngname):
						print"picon found"
						return pngname

	def selEntry(self, dir, visible=True):
		cur_service = self.cur_service #(service, service_name, events)
		self.recalcEntrySize()
		valid_event = self.cur_event is not None
		if cur_service:
			update = True
			entries = cur_service[2]
			if dir == 0: #current
				update = False
			elif dir == +1: #next
				if valid_event and self.cur_event+1 < len(entries):
					self.cur_event+=1
				else:
					self.offs += 1
					self.fillGraphEPG(None) # refill
					return True
			elif dir == -1: #prev
				if valid_event and self.cur_event-1 >= 0:
					self.cur_event-=1
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

		self.l.setSelectionClip(eRect(self.service_rect.left(), self.service_rect.top(), self.service_rect.width(), self.service_rect.height()), False) # left Picon select
		if cur_service and valid_event:
			entry = entries[self.cur_event] #(event_id, event_title, begin_time, duration)
			time_base = self.time_base+self.offs*self.time_epoch*60
			xpos, width = self.calcEntryPosAndWidth(self.event_rect, time_base, self.time_epoch, entry[2], entry[3])
			self.l.setSelectionClip(eRect(xpos, 0, width, self.event_rect.height()), visible and update)
		else:
			self.l.setSelectionClip(eRect(self.event_rect.left(), self.event_rect.top(), self.event_rect.width(), self.event_rect.height()), False)
		self.selectionChanged()
		return False

	def queryEPG(self, list, buildFunc=None):
		if self.epgcache is not None:
			if buildFunc is not None:
				return self.epgcache.lookupEvent(list, buildFunc)
			else:
				return self.epgcache.lookupEvent(list)
		return [ ]

	def fillMultiEPG(self, services, stime=-1):
		#t = time()
		test = [ (service.ref.toString(), 0, stime) for service in services ]
		test.insert(0, 'X0RIBDTCn')
		self.list = self.queryEPG(test)
		self.l.setList(self.list)
		#print time() - t
		self.selectionChanged()

	def updateMultiEPG(self, direction):
		#t = time()
		test = [ x[3] and (x[1], direction, x[3]) or (x[1], direction, 0) for x in self.list ]
		test.insert(0, 'XRIBDTCn')
		tmp = self.queryEPG(test)
		cnt=0
		for x in tmp:
			changecount = self.list[cnt][0] + direction
			if changecount >= 0:
				if x[2] is not None:
					self.list[cnt]=(changecount, x[0], x[1], x[2], x[3], x[4], x[5], x[6])
			cnt+=1
		self.l.setList(self.list)
		#print time() - t
		self.selectionChanged()

	def fillSingleEPG(self, service):
		#t = time()
		test = [ 'RIBDT', (service.ref.toString(), 0, -1, -1) ]
		self.list = self.queryEPG(test)
		self.l.setList(self.list)
		#print time() - t
		self.selectionChanged()

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

	def fillGraphEPG(self, services, stime=-1):
		if services is None:
			time_base = self.time_base+self.offs*self.time_epoch*60
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

	def getSelectedEventId(self):
		x = self.l.getCurrentSelection()
		return x and x[1]

	def moveToService(self,serviceref):
		if not serviceref:
			return
		index = 0
		refstr = serviceref.toString()
		for x in self.list:
			if x[0] == refstr:
				self.instance.moveSelectionTo(index)
				break
			index += 1
			
	def moveToEventId(self, eventId):
		if not eventId:
			return
		index = 0
		for x in self.list:
			if x[1] == eventId:
				self.instance.moveSelectionTo(index)
				break
			index += 1

	def fillSimilarList(self, refstr, event_id):
		t = time()
	 # search similar broadcastings
		if event_id is None:
			return
		l = self.epgcache.search(('RIBND', 1024, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, refstr, event_id))
		if l and len(l):
			l.sort(key=lambda x: x[2])
		self.l.setList(l)
		self.selectionChanged()
		print time() - t

	def getEventRect(self):
		rc = self.event_rect
		return Rect( rc.left() + (self.instance and self.instance.position().x() or 0), rc.top(), rc.width(), rc.height() )

	def getTimeEpoch(self):
		return self.time_epoch

	def getTimeBase(self):
		return self.time_base + (self.offs * self.time_epoch * 60)

	def resetOffset(self):
		self.offs = 0

	def GraphEPGRecRed(self, refstr, beginTime, duration, eventId):
#		for x in self.timer.timer_list:
#			if x.service_ref.ref.toString() == refstr:
#				if x.eit == eventId:
#					if x.justplay:
#						return "justplay"
#					else:
#						return "record"
#		return "nichts"
		pre_clock = 1
		post_clock = 2
		clock_type = 0
		endTime = beginTime + duration
		for x in self.timer.timer_list:
			if x.service_ref.ref.toString() == refstr:
				if x.eit == eventId:
					return "record"
				beg = x.begin
				end = x.end
				if beginTime > beg and beginTime < end and endTime > end:
					clock_type |= pre_clock
				elif beginTime < beg and endTime > beg and endTime < end:
					clock_type |= post_clock
		if clock_type == 0:
			return "record"
		elif clock_type == pre_clock:
			return "nichts"
		elif clock_type == post_clock:
			return "nichts"
		else:
			return "nichts"
