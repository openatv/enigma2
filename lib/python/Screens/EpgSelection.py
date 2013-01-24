from Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Components.ActionMap import NumberActionMap, HelpableActionMap, HelpableNumberActionMap
from Components.Button import Button
from Components.config import config, configfile, ConfigClock
from Components.EpgList import EPGList, TimelineText, EPG_TYPE_SINGLE, EPG_TYPE_SIMILAR, EPG_TYPE_MULTI, EPG_TYPE_ENHANCED, EPG_TYPE_INFOBAR, EPG_TYPE_GRAPH, MAX_TIMELINES
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.Event import Event
from Components.UsageConfig import preferredTimerPath
from Screens.TimerEdit import TimerSanityConflict
from Screens.EventView import EventViewEPGSelect
from Screens.MessageBox import MessageBox
from Screens.PictureInPicture import PictureInPicture
from Screens.Setup import Setup
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from TimeDateInput import TimeDateInput
from enigma import eServiceReference, eTimer, eServiceCenter
from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT
from TimerEntry import TimerEntry, InstantRecordTimerEntry
from ServiceReference import ServiceReference
from time import localtime, time, strftime, mktime
mepg_config_initialized = False
# PiPServiceRelation installed?
try:
	from Plugins.SystemPlugins.PiPServiceRelation.plugin import getRelationDict
	plugin_PiPServiceRelation_installed = True
except:
	plugin_PiPServiceRelation_installed = False

class EPGSelection(Screen, HelpableScreen):
	EMPTY = 0
	ADD_TIMER = 1
	REMOVE_TIMER = 2
	ZAP = 1

	def __init__(self, session, service, zapFunc = None, eventid = None, bouquetChangeCB = None, serviceChangeCB = None, EPGtype = None, StartBouquet = None, StartRef = None, bouquetname = ''):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.longbuttonpressed = False
		self.zapFunc = zapFunc
		self.bouquetChangeCB = bouquetChangeCB
		self.serviceChangeCB = serviceChangeCB
		if EPGtype == 'single':
			self.type = EPG_TYPE_SINGLE
		elif EPGtype == 'infobar':
			self.type = EPG_TYPE_INFOBAR
		elif EPGtype == 'enhanced':
			self.type = EPG_TYPE_ENHANCED
		elif EPGtype == 'graph':
			self.type = EPG_TYPE_GRAPH
		elif EPGtype == 'multi':
			self.type = EPG_TYPE_MULTI
		else:
			self.type = EPG_TYPE_SIMILAR
		self.StartBouquet = StartBouquet
		self.StartRef = StartRef
		self.bouquetname = bouquetname
		self.ask_time = -1
		self.closeRecursive = False
		self.currch = None
		self['Service'] = ServiceEvent()
		self['Event'] = Event()
		self.key_green_choice = self.EMPTY
		self['key_red'] = Button(_('IMDb Search'))
		self['key_green'] = Button(_('Add Timer'))
		self['key_yellow'] = Button(_('EPG Search'))
		self['key_blue'] = Button(_('Add AutoTimer'))
		self['okactions'] = HelpableActionMap(self, 'OkCancelActions',
			{
				'cancel': (self.closeScreen, _('Exit EPG')),
				'OK': (self.OK, _('Zap to channel (setup in menu)')),
				'OKLong': (self.OKLong, _('Zap to channel and close (setup in menu)'))
			}, -1)
		self['okactions'].csel = self
		self['colouractions'] = HelpableActionMap(self, 'ColorActions', 
			{
				'red': (self.redButtonPressed, _('IMDB search for current event')),
				'redlong': (self.redlongButtonPressed, _('Sort EPG List')),
				'green': (self.greenButtonPressed, _('Add/Remove timer for current event')),
				'yellow': (self.yellowButtonPressed, _('Search for similar events')),
				'greenlong': (self.showTimerList, _('Show Timer List')),
				'blue': (self.blueButtonPressed, _('Add a auto timer for current event')),
				'bluelong': (self.bluelongButtonPressed, _('Show AutoTimer List'))
			}, -1)
		self['colouractions'].csel = self
		self['recordingactions'] = HelpableActionMap(self, 'InfobarInstantRecord', 
			{
				'ShortRecord': (self.doRecordTimer, _('Add a record timer for current event')),
				'LongRecord': (self.doZapTimer, _('Add a zap timer for current event'))
			}, -1)
		self['recordingactions'].csel = self
		if self.type == EPG_TYPE_SIMILAR:
			self.currentService = service
			self.eventid = eventid
			self['epgactions'] = HelpableActionMap(self, 'EPGSelectActions', 
				{
					'info': (self.Info, _('Show detailed event info')),
					'infolong': (self.InfoLong, _('Show single epg for current channel')),
					'menu': (self.createSetup, _('Setup menu'))
				}, -1)
			self['epgactions'].csel = self
		elif self.type == EPG_TYPE_SINGLE:
			self.currentService = ServiceReference(service)
			self['epgactions'] = HelpableActionMap(self, 'EPGSelectActions', 
				{
					'info': (self.Info, _('Show detailed event info')),
					'epg': (self.Info, _('Show detailed event info')),
					'menu': (self.createSetup, _('Setup menu'))
				}, -1)
			self['epgactions'].csel = self
			self['cursoractions'] = HelpableActionMap(self, 'DirectionActions', 
				{
					'left': (self.prevPage, _('Move up a page')),
					'right': (self.nextPage, _('Move down a page')),
					'up': (self.moveUp, _('Goto previous channel')),
					'down': (self.moveDown, _('Goto next channel'))
				}, -1)
			self['cursoractions'].csel = self
		elif self.type == EPG_TYPE_INFOBAR or self.type == EPG_TYPE_ENHANCED:
			if self.type == EPG_TYPE_INFOBAR:
				self.skinName = 'QuickEPG'
				self.session.pipshown = False
				if plugin_PiPServiceRelation_installed:
					self.pipServiceRelation = getRelationDict()
				else:
					self.pipServiceRelation = {}
				self['epgactions'] = HelpableActionMap(self, 'EPGSelectActions', 
					{
						'nextBouquet': (self.nextBouquet, _('Goto next bouquet')),
						'prevBouquet': (self.prevBouquet, _('Goto previous bouquet')),
						'nextService': (self.nextPage, _('Move down a page')),
						'prevService': (self.prevPage, _('Move up a page')),
						'input_date_time': (self.enterDateTime, _('Goto specific data/time')),
						'info': (self.Info, _('Show detailed event info')),
						'infolong': (self.InfoLong, _('Show single epg for current channel')),
						'menu': (self.createSetup, _('Setup menu'))
					}, -1)
				self['epgactions'].csel = self
				self['cursoractions'] = HelpableActionMap(self, 'DirectionActions', 
					{
						'left': (self.prevService, _('Goto previous channel')),
						'right': (self.nextService, _('Goto next channel')),
						'up': (self.moveUp, _('Goto previous channel')),
						'down': (self.moveDown, _('Goto next channel'))
					}, -1)
				self['cursoractions'].csel = self
			elif self.type == EPG_TYPE_ENHANCED:
				self['epgactions'] = HelpableActionMap(self, 'EPGSelectActions', 
					{
						'nextBouquet': (self.nextBouquet, _('Goto next bouquet')),
						'prevBouquet': (self.prevBouquet, _('Goto previous bouquet')),
						'nextService': (self.nextService, _('Goto next channel')),
						'prevService': (self.prevService, _('Goto previous channel')),
						'input_date_time': (self.enterDateTime, _('Goto specific data/time')),
						'info': (self.Info, _('Show detailed event info')),
						'infolong': (self.InfoLong, _('Show single epg for current channel')),
						'menu': (self.createSetup, _('Setup menu'))
					}, -1)
				self['epgactions'].csel = self
				self['cursoractions'] = HelpableActionMap(self, 'DirectionActions', 
					{
						'left': (self.prevPage, _('Move up a page')),
						'right': (self.nextPage, _('Move down a page')),
						'up': (self.moveUp, _('Goto previous channel')),
						'down': (self.moveDown, _('Goto next channel'))
					}, -1)
				self['cursoractions'].csel = self
			self['inputactions'] = HelpableNumberActionMap(self, 'NumberActions', 
				{
					'1': (self.keyNumberGlobal, _('enter number to jump to channel.')),
					'2': (self.keyNumberGlobal, _('enter number to jump to channel.')),
					'3': (self.keyNumberGlobal, _('enter number to jump to channel.')),
					'4': (self.keyNumberGlobal, _('enter number to jump to channel.')),
					'5': (self.keyNumberGlobal, _('enter number to jump to channel.')),
					'6': (self.keyNumberGlobal, _('enter number to jump to channel.')),
					'7': (self.keyNumberGlobal, _('enter number to jump to channel.')),
					'8': (self.keyNumberGlobal, _('enter number to jump to channel.')),
					'9': (self.keyNumberGlobal, _('enter number to jump to channel.'))
				}, -1)
			self['inputactions'].csel = self
			self.list = []
			self.servicelist = service
			self.currentService = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		elif self.type == EPG_TYPE_GRAPH:
			if not config.epgselection.pictureingraphics.getValue():
				self.skinName = 'GraphicalEPG'
			else:
				self.skinName = 'GraphicalEPGPIG'
			now = time() - int(config.epg.histminutes.getValue()) * 60
			self.ask_time = self.ask_time = now - now % (int(config.epgselection.roundTo.getValue()) * 60)
			self.closeRecursive = False
			self['lab1'] = Label(_('Wait please while gathering data...'))
			self['timeline_text'] = TimelineText()
			self['Event'] = Event()
			self['primetime'] = Label(_('PRIMETIME'))
			self['change_bouquet'] = Label(_('CHANGE BOUQUET'))
			self['jump'] = Label(_('JUMP 24 HOURS'))
			self['page'] = Label(_('PAGE UP/DOWN'))
			self.time_lines = []
			for x in range(0, MAX_TIMELINES):
				pm = Pixmap()
				self.time_lines.append(pm)
				self['timeline%d' % x] = pm

			self['timeline_now'] = Pixmap()
			self.services = service
			self.curBouquet = bouquetChangeCB
			self.updateTimelineTimer = eTimer()
			self.updateTimelineTimer.callback.append(self.moveTimeLines)
			self.updateTimelineTimer.start(60000)
			self['epgactions'] = HelpableActionMap(self, 'EPGSelectActions', 
				{
					'nextService': (self.nextService, _('Jump forward 24 hours')),
					'prevService': (self.prevService, _('Jump back 24 hours')),
					'nextBouquet': (self.nextBouquet, _('Goto next bouquet')),
					'prevBouquet': (self.prevBouquet, _('Goto previous bouquet')),
					'input_date_time': (self.enterDateTime, _('Goto specific data/time')),
					'info': (self.Info, _('Show detailed event info')),
					'infolong': (self.InfoLong, _('Show single epg for current channel')),
					'tv': (self.togglePIG, _('Toggle Picture In Graphics')),
					'menu': (self.createSetup, _('Setup menu'))
				}, -1)
			self['epgactions'].csel = self
			self['cursoractions'] = HelpableActionMap(self, 'DirectionActions', 
				{
					'left': (self.leftPressed, _('Goto previous event')),
					'right': (self.rightPressed, _('Goto next event')),
					'up': (self.moveUp, _('Goto previous channel')),
					'down': (self.moveDown, _('Goto next channel'))
				}, -1)
			self['cursoractions'].csel = self
			self['input_actions'] = HelpableNumberActionMap(self, 'NumberActions', 
				{
					'1': (self.keyNumberGlobal, _('Reduce time scale')),
					'2': (self.keyNumberGlobal, _('Page up')),
					'3': (self.keyNumberGlobal, _('Increase time scale')),
					'4': (self.keyNumberGlobal, _('page left')),
					'5': (self.keyNumberGlobal, _('Jump to current time')),
					'6': (self.keyNumberGlobal, _('Page right')),
					'7': (self.keyNumberGlobal, _('No of items switch (increase or reduced)')),
					'8': (self.keyNumberGlobal, _('Page down')),
					'9': (self.keyNumberGlobal, _('Jump to prime time')),
					'0': (self.keyNumberGlobal, _('Move to home of list'))
				}, -1)
			self['input_actions'].csel = self
		elif self.type == EPG_TYPE_MULTI:
			self.skinName = 'EPGSelectionMulti'
			self['now_button'] = Pixmap()
			self['next_button'] = Pixmap()
			self['more_button'] = Pixmap()
			self['now_button_sel'] = Pixmap()
			self['next_button_sel'] = Pixmap()
			self['more_button_sel'] = Pixmap()
			self['now_text'] = Label()
			self['next_text'] = Label()
			self['more_text'] = Label()
			self['date'] = Label()
			self.services = service
			self.curBouquet = bouquetChangeCB
			self['epgactions'] = HelpableActionMap(self, 'EPGSelectActions', 
				{
					'nextService': (self.nextPage, _('Move down a page')),
					'prevService': (self.prevPage, _('Move up a page')),
					'nextBouquet': (self.nextBouquet, _('Goto next bouquet')),
					'prevBouquet': (self.prevBouquet, _('Goto previous bouquet')),
					'input_date_time': (self.enterDateTime, _('Goto specific data/time')),
					'info': (self.Info, _('Show detailed event info')),
					'infolong': (self.InfoLong, _('Show single epg for current channel')),
					'menu': (self.createSetup, _('Setup menu'))
				}, -1)
			self['epgactions'].csel = self
			self['cursoractions'] = HelpableActionMap(self, 'DirectionActions', 
				{
					'left': (self.leftPressed, _('Move up a page')),
					'right': (self.rightPressed, _('Move down a page')),
					'up': (self.moveUp, _('Goto previous channel')),
					'down': (self.moveDown, _('Goto next channel'))
				}, -1)
			self['cursoractions'].csel = self
		self['list'] = EPGList(type=self.type, selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer, time_epoch=config.epgselection.prev_time_period.getValue(), overjump_empty=config.epgselection.overjump.getValue())
		self.refreshTimer = eTimer()
		self.refreshTimer.timeout.get().append(self.refreshData)
		self.listTimer = eTimer()
		self.listTimer.timeout.get().append(self.hidewaitingtext)
		self.onLayoutFinish.append(self.onCreate)

	def createSetup(self):
		key = None
		if self.type == EPG_TYPE_SINGLE:
			key = 'epgsingle'
		elif self.type == EPG_TYPE_MULTI:
			key = 'epgmulti'
		elif self.type == EPG_TYPE_ENHANCED:
			key = 'epgenhanced'
		elif self.type == EPG_TYPE_INFOBAR:
			key = 'epginfobar'
		elif self.type == EPG_TYPE_GRAPH:
			key = 'epggraphical'
		if key:
			self.session.openWithCallback(self.onSetupClose, Setup, key)

	def onSetupClose(self, test = None):
		l = self['list']
		l.setItemsPerPage()
		l.setEventFontsize()
		if self.type == EPG_TYPE_GRAPH:
			l.setServiceFontsize()
			self['timeline_text'].setTimeLineFontsize()
			l.setEpoch(config.epgselection.prev_time_period.getValue())
			l.setOverjump_Empty(config.epgselection.overjump.getValue())
			l.setShowServiceMode(config.epgselection.servicetitle_mode.getValue())
			now = time() - int(config.epg.histminutes.getValue()) * 60
			self.ask_time = now - now % (int(config.epgselection.roundTo.getValue()) * 60)
			l.fillGraphEPG(None, self.ask_time)
			self.moveTimeLines()
			self.close('reopen')
		else:
			l.recalcEntrySize()
			l.sortSingleEPG(int(config.epgselection.sort.getValue()))

	def togglePIG(self):
		if not config.epgselection.pictureingraphics.getValue():
			config.epgselection.pictureingraphics.setValue(True)
		else:
			config.epgselection.pictureingraphics.setValue(False)
		config.epgselection.pictureingraphics.save()
		configfile.save()
		self.close('reopen')

	def hidewaitingtext(self):
		self.listTimer.stop()
		self['lab1'].hide()

	def onCreate(self):
		serviceref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		l = self['list']
		l.recalcEntrySize()
		if self.type == EPG_TYPE_GRAPH:
			l.fillGraphEPG(self.services, self.ask_time)
			l.moveToService(serviceref)
			l.setCurrentlyPlaying(serviceref)
			l.setShowServiceMode(config.epgselection.servicetitle_mode.getValue())
			self.moveTimeLines()
			if config.epgselection.channel1.getValue():
				l.instance.moveSelectionTo(0)
			self.setTitle(self.bouquetname)
			self.listTimer.start(10)
		elif self.type == EPG_TYPE_MULTI:
			l.fillMultiEPG(self.services, self.ask_time)
			l.moveToService(serviceref)
			l.setCurrentlyPlaying(serviceref)
			self.setTitle(self.bouquetname)
		elif self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			if self.type == EPG_TYPE_SINGLE:
				service = self.currentService
				title = ServiceReference(self.StartBouquet).getServiceName()
			elif self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
				service = ServiceReference(self.servicelist.getCurrentSelection())
				title = ServiceReference(self.servicelist.getRoot()).getServiceName()
			self['Service'].newService(service.ref)
			title = title + ' - ' + service.getServiceName()
			self.setTitle(title)
			l.fillSingleEPG(service)
			l.sortSingleEPG(int(config.epgselection.sort.getValue()))
		else:
			l.fillSimilarList(self.currentService, self.eventid)

	def moveUp(self):
		self['list'].moveTo(self['list'].instance.moveUp)

	def moveDown(self):
		self['list'].moveTo(self['list'].instance.moveDown)

	def updEvent(self, dir, visible = True):
		ret = self['list'].selEntry(dir, visible)
		print 'RET:',ret
		if ret:
			self.moveTimeLines(True)

	def nextPage(self):
		self['list'].moveTo(self['list'].instance.pageDown)

	def prevPage(self):
		self['list'].moveTo(self['list'].instance.pageUp)

	def toTop(self):
		self['list'].moveTo(self['list'].instance.moveTop)

	def toEnd(self):
		self['list'].moveTo(self['list'].instance.moveEnd)

	def leftPressed(self):
		if self.type == EPG_TYPE_MULTI:
			self['list'].updateMultiEPG(-1)
		else:
			self.updEvent(-1)

	def rightPressed(self):
		if self.type == EPG_TYPE_MULTI:
			self['list'].updateMultiEPG(1)
		else:
			self.updEvent(+1)

	def nextBouquet(self):
		if (self.type == EPG_TYPE_MULTI or self.type == EPG_TYPE_GRAPH) and self.bouquetChangeCB:
			if self.type == EPG_TYPE_MULTI and not config.epgselection.showbouquet_multi.getValue() or self.type == EPG_TYPE_GRAPH and not config.epgselection.showbouquet_vixepg.getValue():
				self['list'].instance.moveSelectionTo(0)
				self.bouquetChangeCB(1, self)
				if self.type == EPG_TYPE_GRAPH:
					now = time() - int(config.epg.histminutes.getValue()) * 60
					self.ask_time = self.ask_time = now - now % (int(config.epgselection.roundTo.getValue()) * 60)
					self['list'].resetOffset()
					self['list'].fillGraphEPG(self.services, self.ask_time)
					self.moveTimeLines(True)
				elif self.type == EPG_TYPE_MULTI:
					self['list'].fillMultiEPG(self.services, self.ask_time)
			else:
				self.close(False)
		elif (self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR) and config.usage.multibouquet.getValue():
			self.servicelist.nextBouquet()
			self.onCreate()

	def prevBouquet(self):
		if (self.type == EPG_TYPE_MULTI or self.type == EPG_TYPE_GRAPH) and self.bouquetChangeCB:
			if self.type == EPG_TYPE_MULTI and not config.epgselection.showbouquet_multi.getValue() or self.type == EPG_TYPE_GRAPH and not config.epgselection.showbouquet_vixepg.getValue():
				self['list'].instance.moveSelectionTo(0)
				self.bouquetChangeCB(-1, self)
				if self.type == EPG_TYPE_GRAPH:
					now = time() - int(config.epg.histminutes.getValue()) * 60
					self.ask_time = self.ask_time = now - now % (int(config.epgselection.roundTo.getValue()) * 60)
					self['list'].resetOffset()
					self['list'].fillGraphEPG(self.services, self.ask_time)
					self.moveTimeLines(True)
				elif self.type == EPG_TYPE_MULTI:
					self['list'].fillMultiEPG(self.services, self.ask_time)
			else:
				self.close(False)
		elif (self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR) and config.usage.multibouquet.getValue():
			self.servicelist.prevBouquet()
			self.onCreate()

	def nextService(self):
		if self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			self['list'].instance.moveSelectionTo(0)
			if self.servicelist.inBouquet():
				prev = self.servicelist.getCurrentSelection()
				if prev:
					prev = prev.toString()
					while True:
						if config.usage.quickzap_bouquet_change.getValue() and self.servicelist.atEnd():
							self.servicelist.nextBouquet()
						else:
							self.servicelist.moveDown()
						cur = self.servicelist.getCurrentSelection()
						if not cur or (not (cur.flags & 64)) or cur.toString() == prev:
							break
			else:
				self.servicelist.moveDown()
			if self.isPlayable():
				self.onCreate()
				if not self['list'].getCurrent()[1] and config.epgselection.overjump.getValue():
					self.nextService()
			else:
				self.nextService()
		elif self.type == EPG_TYPE_GRAPH:
			timeperiod = config.epgselection.prev_time_period.getValue()
			if timeperiod == 60:
				for i in range(24):
					self.updEvent(+2)
			if timeperiod == 120:
				for i in range(12):
					self.updEvent(+2)
			if timeperiod == 180:
				for i in range(8):
					self.updEvent(+2)
			if timeperiod == 240:
				for i in range(6):
					self.updEvent(+2)
			if timeperiod == 300:
				for i in range(4):
					self.updEvent(+2)
		elif self.serviceChangeCB:
			self.serviceChangeCB(1, self)

	def prevService(self):
		if self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			self['list'].instance.moveSelectionTo(0)
			if self.servicelist.inBouquet():
				prev = self.servicelist.getCurrentSelection()
				if prev:
					prev = prev.toString()
					while True:
						if config.usage.quickzap_bouquet_change.getValue():
							if self.servicelist.atBegin():
								self.servicelist.prevBouquet()
						self.servicelist.moveUp()
						cur = self.servicelist.getCurrentSelection()
						if not cur or (not (cur.flags & 64)) or cur.toString() == prev:
							break
			else:
				self.servicelist.moveUp()
			if self.isPlayable():
				self.onCreate()
				if not self['list'].getCurrent()[1] and config.epgselection.overjump.getValue():
					self.prevService()
			else:
				self.prevService()
		elif self.type == EPG_TYPE_GRAPH:
			coolhilf = config.epgselection.prev_time_period.getValue()
			if coolhilf == 60:
				for i in range(24):
					self.updEvent(-2)
			if coolhilf == 120:
				for i in range(12):
					self.updEvent(-2)
			if coolhilf == 180:
				for i in range(8):
					self.updEvent(-2)
			if coolhilf == 240:
				for i in range(6):
					self.updEvent(-2)
			if coolhilf == 300:
				for i in range(4):
					self.updEvent(-2)
		elif self.serviceChangeCB:
			self.serviceChangeCB(-1, self)

	def enterDateTime(self):
		global mepg_config_initialized
		if self.type == EPG_TYPE_MULTI:
			if not mepg_config_initialized:
				config.misc.prev_mepg_time = ConfigClock(default=time())
				mepg_config_initialized = True
			self.session.openWithCallback(self.onDateTimeInputClosed, TimeDateInput, config.epgselection.prev_time)
		elif self.type == EPG_TYPE_GRAPH:
			self.session.openWithCallback(self.onDateTimeInputClosed, TimeDateInput, config.epgselection.prev_time)

	def onDateTimeInputClosed(self, ret):
		if len(ret) > 1:
			if ret[0]:
				if self.type == EPG_TYPE_MULTI:
					self.ask_time = ret[1]
					self['list'].fillMultiEPG(self.services, ret[1])
				elif self.type == EPG_TYPE_GRAPH:
					now = time() - int(config.epg.histminutes.getValue()) * 60
					self.ask_time = self.ask_time - self.ask_time % (int(config.epgselection.roundTo.getValue()) * 60)
					l = self['list']
					l.resetOffset()
					l.fillGraphEPG(None, self.ask_time)
					self.moveTimeLines(True)

	def closeScreen(self):
		if self.session.nav.getCurrentlyPlayingServiceOrGroup() and self.StartRef and self.session.nav.getCurrentlyPlayingServiceOrGroup().toString() != self.StartRef.toString():
			if self.zapFunc and (self.type == 5 and config.epgselection.preview_mode_vixepg.getValue() or self.type == 4 and (config.epgselection.preview_mode_infobar.getValue() == '1' or config.epgselection.preview_mode_infobar.getValue() == '2') or self.type == 3 and config.epgselection.preview_mode_enhanced.getValue() or self.type != 5 and self.type != 4 and self.type != 3 and config.epgselection.preview_mode.getValue()) and self.StartRef and self.StartBouquet:
				if self.StartRef.toString().find('0:0:0:0:0:0:0:0:0') == -1:
					self.zapFunc(None, zapback = True)
				if self.session.pipshown:
					self.session.pipshown = False
					del self.session.pip
					self.setServicelistSelection(self.StartBouquet, self.StartRef)
				else:
					self.session.nav.playService(self.StartRef)
		self.close(True)

	def infoKeyPressed(self):
		cur = self['list'].getCurrent()
		event = cur[0]
		service = cur[1]
		if event is not None:
			if self.type != EPG_TYPE_SIMILAR:
				self.session.open(EventViewEPGSelect, event, service, self.eventViewCallback, None, None, self.openSimilarList)

	def redButtonPressed(self):
		if not self.longbuttonpressed:
			self.openIMDb()
		else:
			self.longbuttonpressed = False

	def redlongButtonPressed(self):
		self.longbuttonpressed = True
		self.sortEpg()

	def greenButtonPressed(self):
		if not self.longbuttonpressed:
			self.timerAdd()
		else:
			self.longbuttonpressed = False

	def greenlongButtonPressed(self):
		self.longbuttonpressed = True
		self.showAutoTimerList()

	def yellowButtonPressed(self):
		if not self.longbuttonpressed:
			self.openEPGSearch()
		else:
			self.longbuttonpressed = False

	def blueButtonPressed(self):
		if not self.longbuttonpressed:
			self.addAutoTimer()
		else:
			self.longbuttonpressed = False

	def bluelongButtonPressed(self):
		self.longbuttonpressed = True
		self.showAutoTimerList()

	def openSimilarList(self, eventid, refstr):
		self.session.open(EPGSelection, refstr, None, eventid)

	def setServices(self, services):
		self.services = services
		self.onCreate()

	def setService(self, service):
		self.currentService = service
		self.onCreate()

	def eventViewCallback(self, setEvent, setService, val):
		l = self['list']
		old = l.getCurrent()
		if self.type == EPG_TYPE_GRAPH:
			self.updEvent(val, False)
		elif val == -1:
			self.moveUp()
		elif val == +1:
			self.moveDown()
		cur = l.getCurrent()
		if (self.type == EPG_TYPE_MULTI or self.type == EPG_TYPE_GRAPH) and cur[0] is None and cur[1].ref != old[1].ref:
			self.eventViewCallback(setEvent, setService, val)
		else:
			setService(cur[1])
			setEvent(cur[0])

	def eventSelected(self):
		self.infoKeyPressed()

	def sortEpg(self):
		if self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_ENHANCED:
			if config.epgselection.sort.getValue() == '0':
				config.epgselection.sort.setValue('1')
			else:
				config.epgselection.sort.setValue('0')
			config.epgselection.sort.save()
			configfile.save()
			self['list'].sortSingleEPG(int(config.epgselection.sort.getValue()))

	def OpenSingleEPG(self):
		cur = self['list'].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		refstr = serviceref.ref.toString()
		if event is not None:
			self.session.open(SingleEPG, refstr)

	def openIMDb(self):
		try:
			from Plugins.Extensions.IMDb.plugin import IMDB, IMDBEPGSelection
			try:
				cur = self['list'].getCurrent()
				event = cur[0]
				name = event.getEventName()
			except:
				name = ''

			self.session.open(IMDB, name, False)
		except ImportError:
			self.session.open(MessageBox, _('The IMDb plugin is not installed!\nPlease install it.'), type=MessageBox.TYPE_INFO, timeout=10)

	def openEPGSearch(self):
		try:
			from Plugins.Extensions.EPGSearch.EPGSearch import EPGSearch
			try:
				cur = self['list'].getCurrent()
				event = cur[0]
				name = event.getEventName()
			except:
				name = ''

			self.session.open(EPGSearch, name, False)
		except ImportError:
			self.session.open(MessageBox, _('The EPGSearch plugin is not installed!\nPlease install it.'), type=MessageBox.TYPE_INFO, timeout=10)

	def addAutoTimer(self):
		try:
			from Plugins.Extensions.AutoTimer.AutoTimerEditor import addAutotimerFromEvent
			cur = self['list'].getCurrent()
			event = cur[0]
			if not event:
				return
			serviceref = cur[1]
			addAutotimerFromEvent(self.session, evt=event, service=serviceref)
		except ImportError:
			self.session.open(MessageBox, _('The AutoTimer plugin is not installed!\nPlease install it.'), type=MessageBox.TYPE_INFO, timeout=10)

	def showTimerList(self):
		from Screens.TimerEdit import TimerEditList
		self.session.open(TimerEditList)

	def showAutoTimerList(self):
		global autopoller
		global autotimer
		try:
			from Plugins.Extensions.AutoTimer.plugin import main, autostart
			from Plugins.Extensions.AutoTimer.AutoTimer import AutoTimer
			from Plugins.Extensions.AutoTimer.AutoPoller import AutoPoller
			autopoller = AutoPoller()
			autotimer = AutoTimer()
			try:
				autotimer.readXml()
			except SyntaxError as se:
				self.session.open(MessageBox, _('Your config file is not well-formed:\n%s') % str(se), type=MessageBox.TYPE_ERROR, timeout=10)
				return

			if autopoller is not None:
				autopoller.stop()
			from Plugins.Extensions.AutoTimer.AutoTimerOverview import AutoTimerOverview
			self.session.openWithCallback(self.editCallback, AutoTimerOverview, autotimer)
		except ImportError:
			self.session.open(MessageBox, _('The AutoTimer plugin is not installed!\nPlease install it.'), type=MessageBox.TYPE_INFO, timeout=10)

	def editCallback(self, session):
		global autopoller
		global autotimer
		if session is not None:
			autotimer.writeXml()
			autotimer.parseEPG()
		if config.plugins.autotimer.autopoll.getValue():
			if autopoller is None:
				from Plugins.Extensions.AutoTimer.AutoPoller import AutoPoller
				autopoller = AutoPoller()
			autopoller.start()
		else:
			autopoller = None
			autotimer = None

	def removeTimer(self, timer):
		timer.afterEvent = AFTEREVENT.NONE
		self.session.nav.RecordTimer.removeEntry(timer)
		self['key_green'].setText(_('Add Timer'))
		self.key_green_choice = self.ADD_TIMER

	def timerAdd(self):
		cur = self['list'].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				cb_func = lambda ret: not ret or self.removeTimer(timer)
				self.session.openWithCallback(cb_func, MessageBox, _('Do you really want to delete %s?') % event.getEventName())
				break
		else:
			newEntry = RecordTimerEntry(serviceref, checkOldTimers=True, dirname=preferredTimerPath(), *parseEvent(event))
			self.session.openWithCallback(self.finishedAdd, TimerEntry, newEntry)

	def finishedAdd(self, answer):
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
			self['key_green'].setText(_('Remove timer'))
			self.key_green_choice = self.REMOVE_TIMER
		else:
			self['key_green'].setText(_('Add Timer'))
			self.key_green_choice = self.ADD_TIMER

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def doRecordTimer(self):
		zap = 0
		cur = self['list'].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				cb_func = lambda ret: not ret or self.removeTimer(timer)
				self.session.openWithCallback(cb_func, MessageBox, _('Do you really want to delete %s?') % event.getEventName())
				break
		else:
			newEntry = RecordTimerEntry(serviceref, checkOldTimers=True, *parseEvent(event))
			self.session.openWithCallback(self.finishedAdd, InstantRecordTimerEntry, newEntry, zap)

	def doZapTimer(self):
		zap = 1
		cur = self['list'].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				cb_func = lambda ret: not ret or self.removeTimer(timer)
				self.session.openWithCallback(cb_func, MessageBox, _('Do you really want to delete %s?') % event.getEventName())
				break
		else:
			newEntry = RecordTimerEntry(serviceref, checkOldTimers=True, *parseEvent(event))
			self.session.openWithCallback(self.finishedAdd, InstantRecordTimerEntry, newEntry, zap)

	def OK(self):
		if config.epgselection.OK_vixepg.getValue() == 'Zap' or config.epgselection.OK_enhanced.getValue() == 'Zap' or config.epgselection.OK_infobar.getValue() == 'Zap' or config.epgselection.OK_multi.getValue() == 'Zap':
			self.zapTo()
		if config.epgselection.OK_vixepg.getValue() == 'Zap + Exit' or config.epgselection.OK_enhanced.getValue() == 'Zap + Exit' or config.epgselection.OK_infobar.getValue() == 'Zap + Exit':
			self.zap()

	def OKLong(self):
		if config.epgselection.OKLong_vixepg.getValue() == 'Zap' or config.epgselection.OKLong_enhanced.getValue() == 'Zap' or config.epgselection.OKLong_infobar.getValue() == 'Zap':
			self.zapTo()
		if self.type == EPG_TYPE_GRAPH:
			serviceref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			self['list'].setCurrentlyPlaying(serviceref)
			self['list'].fillGraphEPG(None, self.ask_time)
			self.moveTimeLines(True)
		if config.epgselection.OKLong_vixepg.getValue() == 'Zap + Exit' or config.epgselection.OKLong_enhanced.getValue() == 'Zap + Exit' or config.epgselection.OKLong_infobar.getValue() == 'Zap + Exit' or config.epgselection.OKLong_multi.getValue() == 'Zap + Exit':
			self.zap()

	def Info(self):
		if config.epgselection.Info.getValue() == 'Channel Info':
			self.infoKeyPressed()
		if config.epgselection.Info.getValue() == 'Single EPG':
			self.OpenSingleEPG()

	def InfoLong(self):
		if config.epgselection.InfoLong.getValue() == 'Channel Info':
			self.infoKeyPressed()
		if config.epgselection.InfoLong.getValue() == 'Single EPG':
			self.OpenSingleEPG()

	def applyButtonState(self, state):
		if state == 0:
			self['now_button'].hide()
			self['now_button_sel'].hide()
			self['next_button'].hide()
			self['next_button_sel'].hide()
			self['more_button'].hide()
			self['more_button_sel'].hide()
			self['now_text'].hide()
			self['next_text'].hide()
			self['more_text'].hide()
			self['key_red'].setText('')
		else:
			if state == 1:
				self['now_button_sel'].show()
				self['now_button'].hide()
			else:
				self['now_button'].show()
				self['now_button_sel'].hide()
			if state == 2:
				self['next_button_sel'].show()
				self['next_button'].hide()
			else:
				self['next_button'].show()
				self['next_button_sel'].hide()
			if state == 3:
				self['more_button_sel'].show()
				self['more_button'].hide()
			else:
				self['more_button'].show()
				self['more_button_sel'].hide()

	def onSelectionChanged(self):
		cur = self['list'].getCurrent()
		event = cur[0]
		self['Event'].newEvent(event)
		if cur[1] is None:
			self['Service'].newService(None)
		else:
			self['Service'].newService(cur[1].ref)
		if self.type == EPG_TYPE_MULTI:
			count = self['list'].getCurrentChangeCount()
			if self.ask_time != -1:
				self.applyButtonState(0)
			elif count > 1:
				self.applyButtonState(3)
			elif count > 0:
				self.applyButtonState(2)
			else:
				self.applyButtonState(1)
			datestr = ''
			if event is not None:
				now = time()
				beg = event.getBeginTime()
				nowTime = localtime(now)
				begTime = localtime(beg)
				if nowTime[2] != begTime[2]:
					datestr = strftime(_('%A %e %b'), begTime)
				else:
					datestr = '%s' % _('Today')
			self['date'].setText(datestr)
		if cur[1] is None or cur[1].getServiceName() == '':
			if self.key_green_choice != self.EMPTY:
				self['key_green'].setText('')
				self.key_green_choice = self.EMPTY
			return
		if event is None:
			if self.key_green_choice != self.EMPTY:
				self['key_green'].setText('')
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
			self['key_green'].setText(_('Remove timer'))
			self.key_green_choice = self.REMOVE_TIMER
		elif not isRecordEvent and self.key_green_choice != self.ADD_TIMER:
			self['key_green'].setText(_('Add Timer'))
			self.key_green_choice = self.ADD_TIMER

	def moveTimeLines(self, force = False):
		self.updateTimelineTimer.start((60 - int(time()) % 60) * 1000)
		self['timeline_text'].setEntries(self['list'], self['timeline_now'], self.time_lines, force)
		self['list'].l.invalidate()

	def refreshData(self, force = False):
		self.refreshTimer.stop()
		if self.type == EPG_TYPE_GRAPH:
			self['list'].fillGraphEPG(None, self.ask_time)
		elif self.type == EPG_TYPE_MULTI:
			self['list'].fillMultiEPG(self.services, self.ask_time)
		elif self.type == EPG_TYPE_SINGLE:
			service = self.currentService
			self['list'].fillSingleEPG(service)
		elif self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			service = ServiceReference(self.servicelist.getCurrentSelection())
			self['list'].fillSingleEPG(service)

	def isPlayable(self):
		current = ServiceReference(self.servicelist.getCurrentSelection())
		return not current.ref.flags & (eServiceReference.isMarker | eServiceReference.isDirectory)

	def setServicelistSelection(self, bouquet, service):
		if self.servicelist.getRoot() != bouquet:
			self.servicelist.clearPath()
			self.servicelist.enterPath(self.servicelist.bouquet_root)
			self.servicelist.enterPath(bouquet)
		self.servicelist.setCurrentSelection(service)

	def zap(self):
		self.zapSelectedService()
		self.close(True)

	def zapSelectedService(self, prev=False):
		if self.session.pipshown:
			self.prevch = str(self.session.pip.getCurrentService().toString())
		else:
			self.prevch = str(self.session.nav.getCurrentlyPlayingServiceReference().toString())
		lst = self["list"]
		count = lst.getCurrentChangeCount()
		if count == 0:
			ref = lst.getCurrent()[1]
			if ref is not None:
				if self.type == EPG_TYPE_INFOBAR and config.epgselection.preview_mode_infobar.getValue() == '2':
					if not self.session.pipshown:
						self.session.pip = self.session.instantiateDialog(PictureInPicture)
						self.session.pip.show()
						self.session.pipshown = True
					n_service = self.pipServiceRelation.get(str(ref.ref), None)
					if n_service is not None:
						service = eServiceReference(n_service)
					else:
						service = ref.ref
					if self.session.pipshown and self.currch == service.toString():
						self.session.pipshown = False
						del self.session.pip
						self.zapFunc(ref.ref, preview = False)
						return
					self.session.pip.playService(service)
					self.currch = str(self.session.pip.getCurrentService().toString())
				else:
					self.zapFunc(ref.ref, preview = prev)
					self.currch = str(self.session.nav.getCurrentlyPlayingServiceReference().toString())

	def zapTo(self):
		if self.session.nav.getCurrentlyPlayingServiceOrGroup().toString().find('0:0:0:0:0:0:0:0:0') != -1:
			from Screens.InfoBarGenerics import setResumePoint
			setResumePoint(self.session)
		if self.zapFunc:
			self.zapSelectedService(True)
			self.refreshTimer.start(10000)
		if self.currch == self.prevch:
			self.close('close')

	def keyNumberGlobal(self, number):
		if self.type == EPG_TYPE_GRAPH:
			if number == 1:
				hilf = config.epgselection.prev_time_period.getValue()
				if hilf > 60:
					hilf = hilf - 60
					self['list'].setEpoch(hilf)
					config.epgselection.prev_time_period.setValue(hilf)
					self.moveTimeLines()
			elif number == 2:
				self.prevPage()
			elif number == 3:
				hilf = config.epgselection.prev_time_period.getValue()
				if hilf < 300:
					hilf = hilf + 60
					self['list'].setEpoch(hilf)
					config.epgselection.prev_time_period.setValue(hilf)
					self.moveTimeLines()
			elif number == 4:
				self.updEvent(-2)
			elif number == 5:
				now = time() - int(config.epg.histminutes.getValue()) * 60
				self.ask_time = now - now % (int(config.epgselection.roundTo.getValue()) * 60)
				self['list'].resetOffset()
				self['list'].fillGraphEPG(None, self.ask_time)
				self.moveTimeLines(True)
			elif number == 6:
				self.updEvent(+2)
			elif number == 7:
				if config.epgselection.heightswitch.getValue():
					config.epgselection.heightswitch.setValue(False)
				else:
					config.epgselection.heightswitch.setValue(True)
				self['list'].setItemsPerPage()
				self['list'].fillGraphEPG(None)
				self.moveTimeLines()
			elif number == 8:
				self.nextPage()
			elif number == 9:
				basetime = localtime(self['list'].getTimeBase())
				basetime = (basetime[0], basetime[1], basetime[2], int(config.epgselection.primetimehour.getValue()), int(config.epgselection.primetimemins.getValue()), 0, basetime[6], basetime[7], basetime[8])
				self.ask_time = mktime(basetime)
				if self.ask_time + 3600 < time():
					self.ask_time = self.ask_time + 86400
				self['list'].resetOffset()
				self['list'].fillGraphEPG(None, self.ask_time)
				self.moveTimeLines(True)
			elif number == 0:
				self.toTop()
				now = time() - int(config.epg.histminutes.getValue()) * 60
				self.ask_time = now - now % (int(config.epgselection.roundTo.getValue()) * 60)
				self['list'].resetOffset()
				self['list'].fillGraphEPG(None, self.ask_time)
				self.moveTimeLines()
		else:
			from Screens.InfoBarGenerics import NumberZap
			self.session.openWithCallback(self.numberEntered, NumberZap, number, self.searchNumber)

	def numberEntered(self, service = None, bouquet = None):
		if service is not None:
			self.zapToNumber(service, bouquet)

	def searchNumberHelper(self, serviceHandler, num, bouquet):
		servicelist = serviceHandler.list(bouquet)
		if servicelist is not None:
			serviceIterator = servicelist.getNext()
			while serviceIterator.valid():
				if num == serviceIterator.getChannelNum():
					return serviceIterator
				serviceIterator = servicelist.getNext()
		return None

	def searchNumber(self, number):
		bouquet = self.servicelist.getRoot()
		service = None
		serviceHandler = eServiceCenter.getInstance()
		service = self.searchNumberHelper(serviceHandler, number, bouquet)
		if config.usage.multibouquet.getValue():
			service = self.searchNumberHelper(serviceHandler, number, bouquet)
			if service is None:
				bouquet = self.servicelist.bouquet_root
				bouquetlist = serviceHandler.list(bouquet)
				if bouquetlist is not None:
					bouquet = bouquetlist.getNext()
					while bouquet.valid():
						if bouquet.flags & eServiceReference.isDirectory:
							service = self.searchNumberHelper(serviceHandler, number, bouquet)
							if service is not None:
								playable = not service.flags & (eServiceReference.isMarker | eServiceReference.isDirectory) or service.flags & eServiceReference.isNumberedMarker
								if not playable:
									service = None
								break
							if config.usage.alternative_number_mode.getValue():
								break
						bouquet = bouquetlist.getNext()
		return (service, bouquet)

	def zapToNumber(self, service, bouquet):
		if service is not None:
			self.setServicelistSelection(bouquet, service)
		self.onCreate()


class SingleEPG(EPGSelection):
	def __init__(self, session, service, zapFunc = None, bouquetChangeCB = None, serviceChangeCB = None):
		EPGSelection.__init__(self, session, service, zapFunc, bouquetChangeCB, serviceChangeCB)
		self.skinName = 'EPGSelection'
