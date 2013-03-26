from Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.Button import Button
from Components.config import config, configfile, ConfigClock
from Components.EpgList import EPGList, EPGBouquetList, TimelineText, EPG_TYPE_SINGLE, EPG_TYPE_SIMILAR, EPG_TYPE_MULTI, EPG_TYPE_ENHANCED, EPG_TYPE_INFOBAR, EPG_TYPE_INFOBARGRAPH, EPG_TYPE_GRAPH, MAX_TIMELINES
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.Event import Event
from Components.UsageConfig import preferredTimerPath
from Screens.TimerEdit import TimerSanityConflict
from Screens.EventView import EventViewEPGSelect, EventViewSimple
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.PictureInPicture import PictureInPicture
from Screens.Setup import Setup
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
from TimeDateInput import TimeDateInput
from enigma import eServiceReference, eTimer, eServiceCenter, ePoint
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

	def __init__(self, session, service = None, zapFunc = None, eventid = None, bouquetChangeCB=None, serviceChangeCB = None, EPGtype = None, StartBouquet = None, StartRef = None, bouquets=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.zapFunc = zapFunc
		self.serviceChangeCB = serviceChangeCB
		self.bouquets = bouquets
		graphic = False
		if EPGtype == 'single':
			self.type = EPG_TYPE_SINGLE
		elif EPGtype == 'infobar':
			self.type = EPG_TYPE_INFOBAR
		elif EPGtype == 'enhanced':
			self.type = EPG_TYPE_ENHANCED
		elif EPGtype == 'graph':
			self.type = EPG_TYPE_GRAPH
			if config.epgselection.graph_type_mode.getValue() == "graphics":
				graphic = True
		elif EPGtype == 'infobargraph':
			self.type = EPG_TYPE_INFOBARGRAPH
			if config.epgselection.infobar_type_mode.getValue() == "graphics":
				graphic = True
		elif EPGtype == 'multi':
			self.type = EPG_TYPE_MULTI
		else:
			self.type = EPG_TYPE_SIMILAR
		if not self.type == EPG_TYPE_SINGLE:
			self.StartBouquet = StartBouquet
			self.StartRef = StartRef
			self.servicelist = None
		self.longbuttonpressed = False
		self.ChoiceBoxDialog = None
		self.ask_time = -1
		self.closeRecursive = False
		self.eventviewDialog = None
		self.eventviewWasShown = False
		self.currch = None
		self.session.pipshown = False
		if plugin_PiPServiceRelation_installed:
			self.pipServiceRelation = getRelationDict()
		else:
			self.pipServiceRelation = {}
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
		self['dialogactions'] = HelpableActionMap(self, 'OkCancelActions',
			{
				'cancel': (self.closeChoiceBoxDialog, _('Exit EPG')),
			}, -1)
		self['dialogactions'].csel = self
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
				'ShortRecord': (self.RecordTimerQuestion, _('Add a record timer for current event')),
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
			self['epgcursoractions'] = HelpableActionMap(self, 'DirectionActions', 
				{
					'left': (self.prevPage, _('Move up a page')),
					'right': (self.nextPage, _('Move down a page')),
					'up': (self.moveUp, _('Goto previous channel')),
					'down': (self.moveDown, _('Goto next channel'))
				}, -1)
			self['epgcursoractions'].csel = self
		elif self.type == EPG_TYPE_INFOBAR or self.type == EPG_TYPE_ENHANCED:
			if self.type == EPG_TYPE_INFOBAR:
				self.skinName = 'QuickEPG'
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
				self['epgcursoractions'] = HelpableActionMap(self, 'DirectionActions', 
					{
						'left': (self.prevService, _('Goto previous channel')),
						'right': (self.nextService, _('Goto next channel')),
						'up': (self.moveUp, _('Goto previous channel')),
						'down': (self.moveDown, _('Goto next channel'))
					}, -1)
				self['epgcursoractions'].csel = self
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
				self['epgcursoractions'] = HelpableActionMap(self, 'DirectionActions', 
					{
						'left': (self.prevPage, _('Move up a page')),
						'right': (self.nextPage, _('Move down a page')),
						'up': (self.moveUp, _('Goto previous channel')),
						'down': (self.moveDown, _('Goto next channel'))
					}, -1)
				self['epgcursoractions'].csel = self
			self['input_actions'] = HelpableNumberActionMap(self, 'NumberActions', 
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
			self['input_actions'].csel = self
			self.list = []
			self.servicelist = service
			self.currentService = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		elif self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			if self.type == EPG_TYPE_GRAPH:
				if not config.epgselection.graph_pig.getValue():
					self.skinName = 'GraphicalEPG'
				else:
					self.skinName = 'GraphicalEPGPIG'
			elif self.type == EPG_TYPE_INFOBARGRAPH:
				self.skinName = 'GraphicalInfoBarEPG'
			now = time() - int(config.epg.histminutes.getValue()) * 60
			if self.type == EPG_TYPE_GRAPH:
				self.ask_time = self.ask_time = now - now % (int(config.epgselection.graph_roundto.getValue()) * 60)
			elif self.type == EPG_TYPE_INFOBARGRAPH:
				self.ask_time = self.ask_time = now - now % (int(config.epgselection.infobar_roundto.getValue()) * 60)
			self.closeRecursive = False
			self.bouquetlist_active = False
			self['lab1'] = Label(_('Wait please while gathering data...'))
			self['bouquetlist'] = EPGBouquetList(graphic=graphic)
			self['bouquetlist'].hide()
			self['timeline_text'] = TimelineText(type=self.type,graphic=graphic)
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
			self.updateTimelineTimer = eTimer()
			self.updateTimelineTimer.callback.append(self.moveTimeLines)
			self.updateTimelineTimer.start(60000)
			self['bouquetcursoractions'] = HelpableActionMap(self, 'DirectionActions', 
				{
					'left': (self.leftPressed, _('Goto previous event')),
					'right': (self.rightPressed, _('Goto next event')),
					'up': (self.moveBouquetUp, _('Goto previous channel')),
					'down': (self.moveBouquetDown, _('Goto next channel'))
				}, -1)
			self['bouquetcursoractions'].csel = self
			self["bouquetcursoractions"].setEnabled(False)
			self['bouquetokactions'] = HelpableActionMap(self, 'OkCancelActions',
				{
					'cancel': (self.closeScreen, _('Exit EPG')),
					'OK': (self.BouquetOK, _('Zap to channel (setup in menu)')),
				}, -1)
			self['bouquetokactions'].csel = self
			self["bouquetokactions"].setEnabled(False)

			self['epgactions'] = HelpableActionMap(self, 'EPGSelectActions', 
				{
					'nextService': (self.nextService, _('Jump forward 24 hours')),
					'prevService': (self.prevService, _('Jump back 24 hours')),
					'nextBouquet': (self.nextBouquet, _('Goto next bouquet')),
					'prevBouquet': (self.prevBouquet, _('Goto previous bouquet')),
					'input_date_time': (self.enterDateTime, _('Goto specific data/time')),
					'info': (self.Info, _('Show detailed event info')),
					'infolong': (self.InfoLong, _('Show single epg for current channel')),
					'tv': (self.Bouquetlist, _('Toggle between bouquet/epg lists')),
					'tvlong': (self.togglePIG, _('Toggle Picture In Graphics')),
					'menu': (self.createSetup, _('Setup menu'))
				}, -1)
			self['epgactions'].csel = self
			self['epgcursoractions'] = HelpableActionMap(self, 'DirectionActions', 
				{
					'left': (self.leftPressed, _('Goto previous event')),
					'right': (self.rightPressed, _('Goto next event')),
					'up': (self.moveUp, _('Goto previous channel')),
					'down': (self.moveDown, _('Goto next channel'))
				}, -1)
			self['epgcursoractions'].csel = self

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

			self["bouquetcursoractions"].setEnabled(False)
			self["epgcursoractions"].setEnabled(True)
		elif self.type == EPG_TYPE_MULTI:
			self.skinName = 'EPGSelectionMulti'
			self['bouquetlist'] = EPGBouquetList(graphic=graphic)
			self['bouquetlist'].hide()
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
			self.bouquetlist_active = False
			self['bouquetcursoractions'] = HelpableActionMap(self, 'DirectionActions', 
				{
					'left': (self.leftPressed, _('Goto previous event')),
					'right': (self.rightPressed, _('Goto next event')),
					'up': (self.moveBouquetUp, _('Goto previous channel')),
					'down': (self.moveBouquetDown, _('Goto next channel'))
				}, -1)
			self['bouquetcursoractions'].csel = self
			self["bouquetcursoractions"].setEnabled(False)
			self['bouquetokactions'] = HelpableActionMap(self, 'OkCancelActions',
				{
					'cancel': (self.closeScreen, _('Exit EPG')),
					'OK': (self.BouquetOK, _('Zap to channel (setup in menu)')),
				}, -1)
			self['bouquetokactions'].csel = self
			self["bouquetokactions"].setEnabled(False)

			self['epgactions'] = HelpableActionMap(self, 'EPGSelectActions', 
				{
					'nextService': (self.nextPage, _('Move down a page')),
					'prevService': (self.prevPage, _('Move up a page')),
					'nextBouquet': (self.nextBouquet, _('Goto next bouquet')),
					'prevBouquet': (self.prevBouquet, _('Goto previous bouquet')),
					'input_date_time': (self.enterDateTime, _('Goto specific data/time')),
					'info': (self.Info, _('Show detailed event info')),
					'infolong': (self.InfoLong, _('Show single epg for current channel')),
					'tv': (self.Bouquetlist, _('Toggle between bouquet/epg lists')),
					'menu': (self.createSetup, _('Setup menu'))
				}, -1)
			self['epgactions'].csel = self
			self['epgcursoractions'] = HelpableActionMap(self, 'DirectionActions', 
				{
					'left': (self.leftPressed, _('Goto previous event')),
					'right': (self.rightPressed, _('Goto next event')),
					'up': (self.moveUp, _('Goto previous channel')),
					'down': (self.moveDown, _('Goto next channel'))
				}, -1)
			self['epgcursoractions'].csel = self

		if self.type == EPG_TYPE_GRAPH:
			time_epoch=config.epgselection.graph_prevtimeperiod.getValue()
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			time_epoch=config.epgselection.infobar_prevtimeperiod.getValue()
		else:
			time_epoch=None
		self['list'] = EPGList(type=self.type, selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer, time_epoch=time_epoch, overjump_empty=config.epgselection.overjump.getValue(), graphic=graphic)
		self.refreshTimer = eTimer()
		self.refreshTimer.timeout.get().append(self.refreshData)
		self.listTimer = eTimer()
		self.listTimer.timeout.get().append(self.hidewaitingtext)
		self.onLayoutFinish.append(self.onCreate)

	def createSetup(self):
		self.closeEventViewDialog()
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
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			key = 'epginfobargraphical'
		if key:
			self.session.openWithCallback(self.onSetupClose, Setup, key)

	def onSetupClose(self, test = None):
		l = self['list']
		l.setItemsPerPage()
		l.setEventFontsize()
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			l.setServiceFontsize()
			self['timeline_text'].setTimeLineFontsize()
			now = time() - int(config.epg.histminutes.getValue()) * 60
			l.setOverjump_Empty(config.epgselection.overjump.getValue())
			if self.type == EPG_TYPE_GRAPH:
				l.setEpoch(config.epgselection.graph_prevtimeperiod.getValue())
				l.setShowServiceMode(config.epgselection.graph_servicetitle_mode.getValue())
				self.ask_time = now - now % (int(config.epgselection.graph_roundto.getValue()) * 60)
			elif self.type == EPG_TYPE_INFOBARGRAPH:
				l.setEpoch(config.epgselection.infobar_prevtimeperiod.getValue())
				l.setShowServiceMode(config.epgselection.infobar_servicetitle_mode.getValue())
				self.ask_time = now - now % (int(config.epgselection.infobar_roundto.getValue()) * 60)
			l.fillGraphEPG(None, self.ask_time)
			self.moveTimeLines()
			if self.type == EPG_TYPE_GRAPH:
				self.close('reopengraph')
			elif self.type == EPG_TYPE_INFOBARGRAPH:
				self.close('reopeninfobargraph')
		else:
			l.recalcEntrySize()
			if self.type == EPG_TYPE_INFOBAR:
				l.sortSingleEPG(int(config.epgselection.sort.getValue()))
				self.close('reopeninfobar')

	def togglePIG(self):
		if not config.epgselection.graph_pig.getValue():
			config.epgselection.graph_pig.setValue(True)
		else:
			config.epgselection.graph_pig.setValue(False)
		config.epgselection.graph_pig.save()
		configfile.save()
		self.close('reopengraph')

	def hidewaitingtext(self):
		self.listTimer.stop()
		self['lab1'].hide()

	def getBouquetServices(self, bouquet):
		services = []
		servicelist = eServiceCenter.getInstance().list(bouquet)
		if not servicelist is None:
			while True:
				service = servicelist.getNext()
				if not service.valid(): #check if end of list
					break
				if service.flags & (eServiceReference.isDirectory | eServiceReference.isMarker): #ignore non playable services
					continue
				services.append(ServiceReference(service))
		return services

	def onCreate(self):
		serviceref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		title = None
		l = self['list']
		l.recalcEntrySize()
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self['bouquetlist'].recalcEntrySize()
			self['bouquetlist'].fillBouquetList(self.bouquets)
			self['bouquetlist'].moveToService(self.StartBouquet)
			self['bouquetlist'].fillBouquetList(self.bouquets)
			self.services = self.getBouquetServices(self.StartBouquet)
			l.fillGraphEPG(self.services, self.ask_time)
			l.moveToService(serviceref)
			l.setCurrentlyPlaying(serviceref)
			self.setTitle(self['bouquetlist'].getCurrentBouquet())
			if self.type == EPG_TYPE_GRAPH:
				l.setShowServiceMode(config.epgselection.graph_servicetitle_mode.getValue())
				self.moveTimeLines()
				if config.epgselection.graph_channel1.getValue():
					l.instance.moveSelectionTo(0)
			elif self.type == EPG_TYPE_INFOBARGRAPH:
				l.setShowServiceMode(config.epgselection.infobar_servicetitle_mode.getValue())
				self.moveTimeLines()
			self.listTimer.start(10)
		elif self.type == EPG_TYPE_MULTI:
			self['bouquetlist'].recalcEntrySize()
			self['bouquetlist'].fillBouquetList(self.bouquets)
			self['bouquetlist'].moveToService(self.StartBouquet)
			self['bouquetlist'].fillBouquetList(self.bouquets)
			self.services = self.getBouquetServices(self.StartBouquet)
			l.fillMultiEPG(self.services, self.ask_time)
			l.moveToService(serviceref)
			l.setCurrentlyPlaying(serviceref)
			self.setTitle(self['bouquetlist'].getCurrentBouquet())
		elif self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			if self.type == EPG_TYPE_SINGLE:
				service = self.currentService
			elif self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
				service = ServiceReference(self.servicelist.getCurrentSelection())
				title = ServiceReference(self.servicelist.getRoot()).getServiceName()
			self['Service'].newService(service.ref)
			if title:
				title = title + ' - ' + service.getServiceName()
			else: 
				title = service.getServiceName()
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


	def Bouquetlist(self):
		if not self.bouquetlist_active:
			self.BouquetlistShow()
		else:
			self.BouquetlistHide()

	def BouquetlistShow(self):
		self['bouquetlist'].show()
		self["bouquetokactions"].setEnabled(True)
		self["okactions"].setEnabled(False)
		self["bouquetcursoractions"].setEnabled(True)
		self["epgcursoractions"].setEnabled(False)
		self.bouquetlist_active = True

	def BouquetlistHide(self):
		self['bouquetlist'].hide()
		self["bouquetokactions"].setEnabled(False)
		self["okactions"].setEnabled(True)
		self["bouquetcursoractions"].setEnabled(False)
		self["epgcursoractions"].setEnabled(True)
		self.bouquetlist_active = False

	def getCurrentBouquet(self):
		if self.has_key('bouquetlist'):
			cur = self["bouquetlist"].l.getCurrentSelection()
			return cur and cur[1]
		else:
			return self.servicelist.getRoot()

	def BouquetOK(self):
		self.BouquetlistHide()
		now = time() - int(config.epg.histminutes.getValue()) * 60
		self.services = self.getBouquetServices(self.getCurrentBouquet())
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			if self.type == EPG_TYPE_GRAPH:
				self.ask_time = self.ask_time = now - now % (int(config.epgselection.graph_roundto.getValue()) * 60)
			elif self.type == EPG_TYPE_INFOBARGRAPH:
				self.ask_time = self.ask_time = now - now % (int(config.epgselection.infobar_roundto.getValue()) * 60)
			self['list'].resetOffset()
			self['list'].fillGraphEPG(self.services, self.ask_time)
			self.moveTimeLines(True)
		elif self.type == EPG_TYPE_MULTI:
			self['list'].fillMultiEPG(self.services, self.ask_time)
		self['list'].instance.moveSelectionTo(0)
		self.setTitle(self['bouquetlist'].getCurrentBouquet())

	def moveBouquetUp(self):
		self['bouquetlist'].moveTo(self['bouquetlist'].instance.moveUp)
		self['bouquetlist'].fillBouquetList(self.bouquets)

	def moveBouquetDown(self):
		self['bouquetlist'].moveTo(self['bouquetlist'].instance.moveDown)
		self['bouquetlist'].fillBouquetList(self.bouquets)

	def nextBouquet(self):
		if self.type == EPG_TYPE_MULTI or self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self.moveBouquetDown()
			self.BouquetOK()
		elif (self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR) and config.usage.multibouquet.getValue():
			self.servicelist.nextBouquet()
			self.onCreate()

	def prevBouquet(self):
		if self.type == EPG_TYPE_MULTI or self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self.moveBouquetUp()
			self.BouquetOK()
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
		elif self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			if self.type == EPG_TYPE_GRAPH:
				timeperiod = config.epgselection.graph_prevtimeperiod.getValue()
			elif self.type == EPG_TYPE_INFOBARGRAPH:
				timeperiod = config.epgselection.infobar_prevtimeperiod.getValue()
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
		elif self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			if self.type == EPG_TYPE_GRAPH:
				timeperiod = config.epgselection.graph_prevtimeperiod.getValue()
			elif self.type == EPG_TYPE_INFOBARGRAPH:
				timeperiod = config.epgselection.infobar_prevtimeperiod.getValue()
			if timeperiod == 60:
				for i in range(24):
					self.updEvent(-2)
			if timeperiod == 120:
				for i in range(12):
					self.updEvent(-2)
			if timeperiod == 180:
				for i in range(8):
					self.updEvent(-2)
			if timeperiod == 240:
				for i in range(6):
					self.updEvent(-2)
			if timeperiod == 300:
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
			self.session.openWithCallback(self.onDateTimeInputClosed, TimeDateInput, config.misc.prev_mepg_time)
		elif self.type == EPG_TYPE_GRAPH:
			self.session.openWithCallback(self.onDateTimeInputClosed, TimeDateInput, config.epgselection.graph_prevtime)
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			self.session.openWithCallback(self.onDateTimeInputClosed, TimeDateInput, config.epgselection.infobar_prevtime)

	def onDateTimeInputClosed(self, ret):
		if len(ret) > 1:
			if ret[0]:
				if self.type == EPG_TYPE_MULTI:
					self.ask_time = ret[1]
					self['list'].fillMultiEPG(self.services, ret[1])
				elif self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
					now = time() - int(config.epg.histminutes.getValue()) * 60
					if self.type == EPG_TYPE_GRAPH:
						self.ask_time = self.ask_time - self.ask_time % (int(config.epgselection.graph_roundto.getValue()) * 60)
					elif self.type == EPG_TYPE_INFOBARGRAPH:
						self.ask_time = self.ask_time - self.ask_time % (int(config.epgselection.infobar_roundto.getValue()) * 60)
					l = self['list']
					l.resetOffset()
					l.fillGraphEPG(None, self.ask_time)
					self.moveTimeLines(True)
		if self.eventviewDialog and (self.type == EPG_TYPE_INFOBAR or self.type == EPG_TYPE_INFOBARGRAPH):
			self.infoKeyPressed(True)

	def closeScreen(self):
		if self.type == EPG_TYPE_SINGLE:
			self.close()
			return # stop and do not continue.
		if self.session.nav.getCurrentlyPlayingServiceOrGroup() and self.StartRef and self.session.nav.getCurrentlyPlayingServiceOrGroup().toString() != self.StartRef.toString():
			if self.zapFunc and ((self.type == EPG_TYPE_GRAPH and config.epgselection.graph_preview_mode.getValue()) or (self.type == EPG_TYPE_MULTI and config.epgselection.multi_preview_mode.getValue()) or ((self.type == EPG_TYPE_INFOBAR or self.type == EPG_TYPE_INFOBARGRAPH) and (config.epgselection.infobar_preview_mode.getValue() == '1' or config.epgselection.infobar_preview_mode.getValue() == '2')) or (self.type == EPG_TYPE_ENHANCED and config.epgselection.enhanced_preview_mode.getValue())) and self.StartRef and self.StartBouquet:
				if self.StartRef.toString().find('0:0:0:0:0:0:0:0:0') == -1:
					self.zapFunc(None, zapback = True)
			elif self.StartRef.toString().find('0:0:0:0:0:0:0:0:0') != -1:
				self.session.nav.playService(self.StartRef)
		if self.session.pipshown:
			self.session.pipshown = False
			del self.session.pip
		self.closeEventViewDialog()
		self.close(True)

	def infoKeyPressed(self, eventviewopen=False):
		cur = self['list'].getCurrent()
		event = cur[0]
		service = cur[1]
		if event is not None and not self.eventviewDialog and not eventviewopen:
			if self.type != EPG_TYPE_SIMILAR:
				if self.type == EPG_TYPE_INFOBARGRAPH:
					self.eventviewDialog = self.session.instantiateDialog(EventViewSimple,event, service, skin='InfoBarEventView')
					self.eventviewDialog.show()
				else:
					self.session.open(EventViewEPGSelect, event, service, callback=self.eventViewCallback, similarEPGCB=self.openSimilarList)
		elif self.eventviewDialog and not eventviewopen:
			self.eventviewDialog.hide()
			del self.eventviewDialog
			self.eventviewDialog = None
		elif event is not None and self.eventviewDialog and eventviewopen:
			if self.type != EPG_TYPE_SIMILAR:
				if self.type == EPG_TYPE_INFOBAR or self.type == EPG_TYPE_INFOBARGRAPH:
					self.eventviewDialog.hide()
					self.eventviewDialog = self.session.instantiateDialog(EventViewSimple,event, service, skin='InfoBarEventView')
					self.eventviewDialog.show()

	def redButtonPressed(self):
		self.closeEventViewDialog()
		if not self.longbuttonpressed:
			self.openIMDb()
		else:
			self.longbuttonpressed = False

	def redlongButtonPressed(self):
		self.closeEventViewDialog()
		self.longbuttonpressed = True
		self.sortEpg()

	def greenButtonPressed(self):
		self.closeEventViewDialog()
		if not self.longbuttonpressed:
			self.timerAdd()
		else:
			self.longbuttonpressed = False

	def greenlongButtonPressed(self):
		self.closeEventViewDialog()
		self.longbuttonpressed = True
		self.showAutoTimerList()

	def yellowButtonPressed(self):
		self.closeEventViewDialog()
		if not self.longbuttonpressed:
			self.openEPGSearch()
		else:
			self.longbuttonpressed = False

	def blueButtonPressed(self):
		self.closeEventViewDialog()
		if not self.longbuttonpressed:
			self.addAutoTimer()
		else:
			self.longbuttonpressed = False

	def bluelongButtonPressed(self):
		self.closeEventViewDialog()
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
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self.updEvent(val, False)
		elif val == -1:
			self.moveUp()
		elif val == +1:
			self.moveDown()
		cur = l.getCurrent()
		if (self.type == EPG_TYPE_MULTI or self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH) and cur[0] is None and cur[1].ref != old[1].ref:
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
		serviceref = cur[1].ref
		if serviceref is not None:
			self.session.open(SingleEPG, serviceref)

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
			self.refreshTimer.start(3000)
		except ImportError:
			self.session.open(MessageBox, _('The AutoTimer plugin is not installed!\nPlease install it.'), type=MessageBox.TYPE_INFO, timeout=10)

	def addAutoTimerSilent(self):
		try:
			from Plugins.Extensions.AutoTimer.AutoTimerEditor import addAutotimerFromEventSilent
			cur = self['list'].getCurrent()
			event = cur[0]
			if not event:
				return
			serviceref = cur[1]
			addAutotimerFromEventSilent(self.session, evt=event, service=serviceref)
			self.refreshTimer.start(3000)
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
				cb_func = lambda ret: self.removeTimer(timer)
				menu = [(_("Yes"), 'CALLFUNC', cb_func), (_("No"), 'CALLFUNC', self.ChoiceBoxCB, self.ChoiceBoxNull)]
				self.ChoiceBoxDialog = self.session.instantiateDialog(ChoiceBox, title=_('Do you really want to remove the timer for %s?') % event.getEventName(), list=menu)
				self.showChoiceBoxDialog()
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
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self['list'].fillGraphEPG(None, self.ask_time)
			self.moveTimeLines()

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def removeTimer(self, timer):
		print 'removeTimer'
		timer.afterEvent = AFTEREVENT.NONE
		self.session.nav.RecordTimer.removeEntry(timer)
		self['key_green'].setText(_('Add Timer'))
		self.key_green_choice = self.ADD_TIMER
		self.closeChoiceBoxDialog()
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self['list'].fillGraphEPG(None, self.ask_time)
			self.moveTimeLines()

	def RecordTimerQuestion(self):
		timerfound = False
		cur = self['list'].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				cb_func = lambda ret: self.removeTimer(timer)
				menu = [(_("Yes"), 'CALLFUNC', cb_func), (_("No"), 'CALLFUNC', self.ChoiceBoxCB, self.ChoiceBoxNull)]
				self.ChoiceBoxDialog = self.session.instantiateDialog(ChoiceBox, title=_('Do you really want to remove the timer for %s?') % event.getEventName(), list=menu)
				self.showChoiceBoxDialog()
				break
		else:
			menu = [(_("Record once"), 'CALLFUNC', self.ChoiceBoxCB, self.doRecordTimer), (_("Add AutoTimer"), 'CALLFUNC', self.ChoiceBoxCB, self.addAutoTimerSilent)]
			self.ChoiceBoxDialog = self.session.instantiateDialog(ChoiceBox, title="%s?" % event.getEventName(), list=menu, skin_name="RecordTimerQuestion")
			serviceref = eServiceReference(str(self['list'].getCurrent()[1]))
			posy = self['list'].getSelectionPosition(serviceref)
			self.ChoiceBoxDialog.instance.move(ePoint(posy[0]-self.ChoiceBoxDialog.instance.size().width(),self.instance.position().y()+posy[1]))
			self.showChoiceBoxDialog()

	def ChoiceBoxNull(self):
		return

	def ChoiceBoxCB(self, choice):
		if choice[3]:
			try:
				choice[3]()
			except:
				choice[3]
		self.closeChoiceBoxDialog()

	def showChoiceBoxDialog(self):
		self['dialogactions'].execBegin()
		self.ChoiceBoxDialog.show()
		self.ChoiceBoxDialog['actions'].execBegin()
		self['okactions'].execEnd()
		self['epgcursoractions'].execEnd()
		self['colouractions'].execEnd()
		self['recordingactions'].execEnd()
		self['epgactions'].execEnd()
		if self.has_key('input_actions'):
			self['input_actions'].execEnd()

	def closeChoiceBoxDialog(self):
		self['dialogactions'].execEnd()
		if self.ChoiceBoxDialog:
			self.ChoiceBoxDialog['actions'].execEnd()
			self.session.deleteDialog(self.ChoiceBoxDialog)
		self['okactions'].execBegin()
		self['epgcursoractions'].execBegin()
		self['colouractions'].execBegin()
		self['recordingactions'].execBegin()
		self['epgactions'].execBegin()
		if self.has_key('input_actions'):
			self['input_actions'].execBegin()

	def doRecordTimer(self):
		self.doInstantTimer(0)

	def doZapTimer(self):
		self.doInstantTimer(1)

	def doInstantTimer(self, zap):
		cur = self['list'].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		newEntry = RecordTimerEntry(serviceref, checkOldTimers=True, *parseEvent(event))
		self.InstantRecordDialog = self.session.instantiateDialog(InstantRecordTimerEntry, newEntry, zap)
		retval = [True, self.InstantRecordDialog.retval()]
		self.session.deleteDialogWithCallback(self.finishedAdd, self.InstantRecordDialog, retval)

	def OK(self):
		if config.epgselection.graph_ok.getValue() == 'Zap' or config.epgselection.enhanced_ok.getValue() == 'Zap' or config.epgselection.infobar_ok.getValue() == 'Zap' or config.epgselection.multi_ok.getValue() == 'Zap':
			self.zapTo()
		if config.epgselection.graph_ok.getValue() == 'Zap + Exit' or config.epgselection.enhanced_ok.getValue() == 'Zap + Exit' or config.epgselection.infobar_ok.getValue() == 'Zap + Exit' or config.epgselection.multi_ok.getValue() == 'Zap + Exit':
			self.zap()

	def OKLong(self):
		if config.epgselection.graph_oklong.getValue() == 'Zap' or config.epgselection.enhanced_oklong.getValue() == 'Zap' or config.epgselection.infobar_oklong.getValue() == 'Zap' or config.epgselection.multi_oklong.getValue() == 'Zap':
			self.zapTo()
		if config.epgselection.graph_oklong.getValue() == 'Zap + Exit' or config.epgselection.enhanced_oklong.getValue() == 'Zap + Exit' or config.epgselection.infobar_oklong.getValue() == 'Zap + Exit' or config.epgselection.multi_oklong.getValue() == 'Zap + Exit':
			self.zap()

	def Info(self):
		if (self.type == EPG_TYPE_GRAPH and config.epgselection.graph_info.getValue() == 'Channel Info'):
			self.infoKeyPressed()
		elif (self.type == EPG_TYPE_GRAPH and config.epgselection.graph_info.getValue() == 'Single EPG'):
			self.OpenSingleEPG()
		else:
			self.infoKeyPressed()

	def InfoLong(self):
		if self.type == EPG_TYPE_GRAPH and config.epgselection.graph_infolong.getValue() == 'Channel Info':
			self.infoKeyPressed()
		elif self.type == EPG_TYPE_GRAPH and config.epgselection.graph_infolong.getValue() == 'Single EPG':
			self.OpenSingleEPG()
		else:
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
		if self.eventviewDialog and (self.type == EPG_TYPE_INFOBAR or self.type == EPG_TYPE_INFOBARGRAPH):
			self.infoKeyPressed(True)

	def moveTimeLines(self, force = False):
		self.updateTimelineTimer.start((60 - int(time()) % 60) * 1000)
		self['timeline_text'].setEntries(self['list'], self['timeline_now'], self.time_lines, force)
		self['list'].l.invalidate()

	def refreshData(self, force = False):
		self.refreshTimer.stop()
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
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
		if self.servicelist:
			if self.servicelist.getRoot() != bouquet:
				self.servicelist.clearPath()
				self.servicelist.enterPath(self.servicelist.bouquet_root)
				self.servicelist.enterPath(bouquet)
			self.servicelist.setCurrentSelection(service)

	def closeEventViewDialog(self):
		if self.eventviewDialog:
			self.eventviewDialog.hide()
			del self.eventviewDialog
			self.eventviewDialog = None

	def zap(self):
		if self.zapFunc:
			self.zapSelectedService()
			self.closeEventViewDialog()
			self.close(True)
		else:
			self.closeEventViewDialog()
			self.close()

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
				if (self.type == EPG_TYPE_INFOBAR or self.type == EPG_TYPE_INFOBARGRAPH) and config.epgselection.infobar_preview_mode.getValue() == '2':
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
						self.zapFunc(ref.ref, bouquet = self.getCurrentBouquet(), preview = False)
						return
					self.session.pip.playService(service)
					self.currch = str(self.session.pip.getCurrentService().toString())
				else:
					self.zapFunc(ref.ref, bouquet = self.getCurrentBouquet(), preview = prev)
					self.currch = str(self.session.nav.getCurrentlyPlayingServiceReference().toString())
				self['list'].setCurrentlyPlaying(self.session.nav.getCurrentlyPlayingServiceOrGroup())

	def zapTo(self):
		if self.session.nav.getCurrentlyPlayingServiceOrGroup().toString().find('0:0:0:0:0:0:0:0:0') != -1:
			from Screens.InfoBarGenerics import setResumePoint
			setResumePoint(self.session)
		if self.zapFunc:
			self.zapSelectedService(True)
			self.refreshTimer.start(2000)
		if not self.currch or self.currch == self.prevch:
			if self.zapFunc:
				self.zapFunc(None, False)
				self.closeEventViewDialog()
				self.close('close')
			else:
				self.closeEventViewDialog()
				self.close()

	def keyNumberGlobal(self, number):
		if self.type == EPG_TYPE_GRAPH:
			if number == 1:
				timeperiod = config.epgselection.graph_prevtimeperiod.getValue()
				if timeperiod > 60:
					timeperiod = timeperiod - 60
					self['list'].setEpoch(timeperiod)
					config.epgselection.graph_prevtimeperiod.setValue(timeperiod)
					self.moveTimeLines()
			elif number == 2:
				self.prevPage()
			elif number == 3:
				timeperiod = config.epgselection.graph_prevtimeperiod.getValue()
				if timeperiod < 300:
					timeperiod = timeperiod + 60
					self['list'].setEpoch(timeperiod)
					config.epgselection.graph_prevtimeperiod.setValue(timeperiod)
					self.moveTimeLines()
			elif number == 4:
				self.updEvent(-2)
			elif number == 5:
				now = time() - int(config.epg.histminutes.getValue()) * 60
				self.ask_time = now - now % (int(config.epgselection.graph_roundto.getValue()) * 60)
				self['list'].resetOffset()
				self['list'].fillGraphEPG(None, self.ask_time)
				self.moveTimeLines(True)
			elif number == 6:
				self.updEvent(+2)
			elif number == 7:
				if config.epgselection.graph_heightswitch.getValue():
					config.epgselection.graph_heightswitch.setValue(False)
				else:
					config.epgselection.graph_heightswitch.setValue(True)
				self['list'].setItemsPerPage()
				self['list'].fillGraphEPG(None)
				self.moveTimeLines()
			elif number == 8:
				self.nextPage()
			elif number == 9:
				basetime = localtime(self['list'].getTimeBase())
				basetime = (basetime[0], basetime[1], basetime[2], int(config.epgselection.graph_primetimehour.getValue()), int(config.epgselection.graph_primetimemins.getValue()), 0, basetime[6], basetime[7], basetime[8])
				self.ask_time = mktime(basetime)
				if self.ask_time + 3600 < time():
					self.ask_time = self.ask_time + 86400
				self['list'].resetOffset()
				self['list'].fillGraphEPG(None, self.ask_time)
				self.moveTimeLines(True)
			elif number == 0:
				self.toTop()
				now = time() - int(config.epg.histminutes.getValue()) * 60
				self.ask_time = now - now % (int(config.epgselection.graph_roundto.getValue()) * 60)
				self['list'].resetOffset()
				self['list'].fillGraphEPG(None, self.ask_time)
				self.moveTimeLines()
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			if number == 1:
				timeperiod = config.epgselection.infobar_prevtimeperiod.getValue()
				if timeperiod > 60:
					timeperiod = timeperiod - 60
					self['list'].setEpoch(timeperiod)
					config.epgselection.infobar_prevtimeperiod.setValue(timeperiod)
					self.moveTimeLines()
			elif number == 2:
				self.prevPage()
			elif number == 3:
				timeperiod = config.epgselection.infobar_prevtimeperiod.getValue()
				if timeperiod < 300:
					timeperiod = timeperiod + 60
					self['list'].setEpoch(timeperiod)
					config.epgselection.infobar_prevtimeperiod.setValue(timeperiod)
					self.moveTimeLines()
			elif number == 4:
				self.updEvent(-2)
			elif number == 5:
				now = time() - int(config.epg.histminutes.getValue()) * 60
				self.ask_time = now - now % (int(config.epgselection.infobar_roundto.getValue()) * 60)
				self['list'].resetOffset()
				self['list'].fillGraphEPG(None, self.ask_time)
				self.moveTimeLines(True)
			elif number == 6:
				self.updEvent(+2)
			elif number == 8:
				self.nextPage()
			elif number == 9:
				basetime = localtime(self['list'].getTimeBase())
				basetime = (basetime[0], basetime[1], basetime[2], int(config.epgselection.infobar_primetimehour.getValue()), int(config.epgselection.infobar_primetimemins.getValue()), 0, basetime[6], basetime[7], basetime[8])
				self.ask_time = mktime(basetime)
				if self.ask_time + 3600 < time():
					self.ask_time = self.ask_time + 86400
				self['list'].resetOffset()
				self['list'].fillGraphEPG(None, self.ask_time)
				self.moveTimeLines(True)
			elif number == 0:
				self.toTop()
				now = time() - int(config.epg.histminutes.getValue()) * 60
				self.ask_time = now - now % (int(config.epgselection.infobar_roundto.getValue()) * 60)
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
	def __init__(self, session, service, EPGtype="single"):
		EPGSelection.__init__(self, session, service, EPGtype)
		self.skinName = 'EPGSelection'
