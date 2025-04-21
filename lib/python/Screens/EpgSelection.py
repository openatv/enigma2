from time import localtime, mktime, strftime, time

from enigma import ePoint, eServiceCenter, eServiceReference, eTimer

from RecordTimer import AFTEREVENT, RecordTimerEntry, parseEvent
from ServiceReference import ServiceReference
from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import ConfigClock, config, configfile
from Components.EpgList import EPG_TYPE_ENHANCED, EPG_TYPE_GRAPH, EPG_TYPE_INFOBAR, EPG_TYPE_INFOBARGRAPH, EPG_TYPE_MULTI, EPG_TYPE_SIMILAR, EPG_TYPE_SINGLE, EPG_TYPE_VERTICAL, EPGBouquetList, EPGList, MAX_TIMELINES, TimelineText
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.Sources.Event import Event
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.StaticText import StaticText
from Components.UsageConfig import preferredTimerPath
from Screens.ChoiceBox import ChoiceBox
from Screens.DateTimeInput import EPGJumpTime
from Screens.EventView import EventViewEPGSelect, EventViewSimple
from Screens.MessageBox import MessageBox
from Screens.PictureInPicture import PictureInPicture
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.TimerEdit import TimerSanityConflict
from Screens.TimerEntry import InstantRecordTimerEntry, TimerEntry


try:  # PiPServiceRelation installed?
	from Plugins.SystemPlugins.PiPServiceRelation.plugin import getRelationDict
	plugin_PiPServiceRelation_installed = True
except:
	plugin_PiPServiceRelation_installed = False

mepg_config_initialized = False

epgTypes = {
	"single": EPG_TYPE_SINGLE,
	"infobar": EPG_TYPE_INFOBAR,
	"enhanced": EPG_TYPE_ENHANCED,
	"graph": EPG_TYPE_GRAPH,
	"infobargraph": EPG_TYPE_INFOBARGRAPH,
	"multi": EPG_TYPE_MULTI,
	"vertical": EPG_TYPE_VERTICAL,
	"similar": EPG_TYPE_SIMILAR
}


class EPGSelection(Screen):
	catchupPlayerFunc = None
	EMPTY = 0
	ADD_TIMER = 1
	REMOVE_TIMER = 2
	ZAP = 1

	def __init__(self, session, service=None, zapFunc=None, eventid=None, bouquetChangeCB=None, serviceChangeCB=None, EPGtype=None, StartBouquet=None, StartRef=None, bouquets=None):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("EPG Selection"))
		self.zapFunc = zapFunc
		self.serviceChangeCB = serviceChangeCB
		self.bouquets = bouquets
		graphic = ((config.epgselection.infobar_type_mode.value == "graphics" and "infobargraph" == EPGtype)
			or (config.epgselection.graph_type_mode.value == "graphics" and "graph" == EPGtype))
		if EPGtype is None and eventid is None and isinstance(service, eServiceReference):
			self.type = EPG_TYPE_SINGLE
		else:
			self.type = epgTypes.get(EPGtype, EPG_TYPE_SIMILAR)
		if not self.type == EPG_TYPE_SINGLE:
			self.StartBouquet = StartBouquet
			self.StartRef = StartRef
			self.servicelist = None
		self.ChoiceBoxDialog = None
		self.ask_time = -1
		self.closeRecursive = False
		self.eventviewDialog = None
		self.eventviewWasShown = False
		self.currch = None
		self.Oldpipshown = False
		if self.session.pipshown:
			self.Oldpipshown = True
		self.session.pipshown = False
		self.onClose.append(self.restorePiP)
		self.cureventindex = None
		if plugin_PiPServiceRelation_installed:
			self.pipServiceRelation = getRelationDict()
		else:
			self.pipServiceRelation = {}
		self.zapnumberstarted = False
		self.NumberZapTimer = eTimer()
		self.NumberZapTimer.callback.append(self.dozumberzap)
		self.NumberZapField = None
		self.CurrBouquet = None
		self.CurrService = None
		self["Service"] = ServiceEvent()
		self["Event"] = Event()
		self["lab1"] = Label(_("Please wait while gathering data..."))
		self.key_green_choice = self.EMPTY
		self["key_menu"] = StaticText(_("MENU"))
		self["key_info"] = StaticText(_("INFO"))
		self["key_text"] = StaticText(_("TEXT"))
		self["key_epg"] = StaticText(_("EPG"))
		if self.type == EPG_TYPE_VERTICAL:
			self.StartBouquet = StartBouquet
			self.StartRef = StartRef
			self.servicelist = service
			self.bouquetlist_active = False
			self.firststart = True
			self.lastEventTime = (time(), time() + 3600)
			self.lastMinus = 0
			self.activeList = 1
			self.myServices = []
			self.list = []
		else:
			self.activeList = ""
			self["number"] = Label()
			self["number"].hide()
		if self.type in [EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH, EPG_TYPE_VERTICAL]:
			self.RefreshColouredKeys()
		else:
			self["key_red"] = StaticText(_("IMDb Search"))
			self["key_green"] = StaticText(_("Add Timer"))
			self["key_yellow"] = StaticText(_("EPG Search"))
			self["key_blue"] = StaticText(_("Add AutoTimer"))
		epgCursoractions = {
			"up": (self.moveUp, _("Goto previous channel")),
			"down": (self.moveDown, _("Goto next channel"))
		}
		if self.type == EPG_TYPE_INFOBAR:
			epgCursoractions["left"] = (self.prevService, _("Goto previous channel"))
			epgCursoractions["right"] = (self.nextService, _("Goto next channel"))
		elif self.type in [EPG_TYPE_ENHANCED, EPG_TYPE_SINGLE]:
			epgCursoractions["left"] = (self.prevPage, _("Move up a page"))
			epgCursoractions["right"] = (self.nextPage, _("Move down a page"))
		elif self.type in [EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH, EPG_TYPE_MULTI, EPG_TYPE_VERTICAL]:
			epgCursoractions["left"] = (self.leftPressed, _("Goto previous event"))
			epgCursoractions["right"] = (self.rightPressed, _("Goto next event"))
			self["bouquetcursoractions"] = HelpableActionMap(self, ["DirectionActions"], {
				"left": (self.moveBouquetPageUp, _("Goto previous event")),
				"right": (self.moveBouquetPageDown, _("Goto next event")),
				"up": (self.moveBouquetUp, _("Goto previous channel")),
				"down": (self.moveBouquetDown, _("Goto next channel"))
			}, prio=-1, description=_("EPG Navigation Actions"))
			self["bouquetcursoractions"].csel = self
			self["bouquetcursoractions"].setEnabled(False)
		else:
			epgCursoractions = None
		if epgCursoractions:
			self["epgcursoractions"] = HelpableActionMap(self, ["DirectionActions"], epgCursoractions, prio=-1, description=_("EPG Navigation Actions"))
			self["epgcursoractions"].csel = self
		epgActions = {
			"menu": (self.createSetup, _("Setup menu")),
			"info": (self.Info, _("Show detailed event info")),
			"infolong": (self.InfoLong, _("Show single EPG for current channel"))
		}

		self["epgcatchupactions"] = HelpableActionMap(self, "EPGCatchUpActions", {
			"play": (self.playCatchup, _("Play catch up service archive")),
		}, prio=-2, description=_("Catch Up Player Actions"))
		self["epgcatchupactions"].setEnabled(callable(self.catchupPlayerFunc))

		if self.type == EPG_TYPE_SINGLE:
			epgActions["epg"] = (self.Info, _("Show detailed event info"))
			del epgActions["infolong"]
			epgActions["nextService"] = (self.nextService, _("Goto next channel"))
			epgActions["prevService"] = (self.prevService, _("Goto previous channel"))
		elif self.type != EPG_TYPE_SIMILAR:
			epgActions["epg"] = (self.epgButtonPressed, _("Show single EPG for current channel"))
			epgActions["input_date_time"] = (self.enterDateTime, _("Goto specific date/time"))
			if self.type != EPG_TYPE_INFOBAR and self.type != EPG_TYPE_ENHANCED:
				epgActions["tv"] = (self.Bouquetlist, _("Toggle between bouquet/EPG lists"))
				if self.type != EPG_TYPE_MULTI:
					epgActions["tvlong"] = (self.togglePIG, _("Toggle Picture in Graphics"))
			epgActions["nextBouquet"] = (self.nextBouquet, _("Goto next bouquet"))
			epgActions["prevBouquet"] = (self.prevBouquet, _("Goto previous bouquet"))
			epgActions["prevService"] = (self.nextPage, _("Move down a page"))
			epgActions["nextService"] = (self.prevPage, _("Move up a page"))
			if self.type == EPG_TYPE_ENHANCED:
				epgActions["nextService"] = (self.nextService, _("Goto next channel"))
				epgActions["prevService"] = (self.prevService, _("Goto previous channel"))
			if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
				if config.epgselection.graph_channelbtn.value == "bouquet":
					epgActions["nextService"] = epgActions["nextBouquet"]
					epgActions["prevService"] = epgActions["prevBouquet"]
				elif config.epgselection.graph_channelbtn.value != "page":
					epgActions["nextService"] = (self.nextService, _("Jump forward 24 hours"))
					epgActions["prevService"] = (self.prevService, _("Jump back 24 hours"))
			if self.type == EPG_TYPE_VERTICAL:
				epgActions["info"] = (self.Info, _("Show detailed event info (setup in menu)"))
				epgActions["infolong"] = (self.Info, _("Show single EPG for current channel (setup in menu)"))
				epgActions["nextService"] = (self.nextPage, _("Jump to next page or all up (setup in menu)"))
				epgActions["prevService"] = (self.prevPage, _("Jump to previous page or all down (setup in menu)"))
		self["epgactions"] = HelpableActionMap(self, ["EPGSelectActions"], epgActions, prio=-1, description=_("EPG Navigation Actions"))
		self["epgactions"].csel = self
		self["dialogactions"] = HelpableActionMap(self, ["WizardActions"], {
			"back": (self.closeChoiceBoxDialog, _("Close dialog")),
		}, prio=-1)
		self["dialogactions"].csel = self
		self["dialogactions"].setEnabled(False)
		self["okactions"] = HelpableActionMap(self, ["OkCancelActions"], {
			"cancel": (self.closeScreen, _("Exit EPG")),
			"OK": (self.OK, _("Zap to channel (setup in menu)")),
			"OKLong": (self.OKLong, _("Zap to channel and close (setup in menu)"))
		}, prio=-1, description=_("EPG Actions"))
		self["okactions"].csel = self
		self["coloractions"] = HelpableActionMap(self, ["ColorActions"], {
			"red": (self.redButtonPressed, _("IMDb search for current event")),
			"redlong": (self.redButtonPressedLong, _("Sort EPG List")),
			"green": (self.greenButtonPressed, _("Add/Remove a timer for the current event")),
			"greenlong": (self.greenButtonPressedLong, _("Show Timer List")),
			"yellow": (self.yellowButtonPressed, _("Search for similar events")),
			"blue": (self.blueButtonPressed, _("Add an AutoTimer for the current event")),
			"bluelong": (self.blueButtonPressedLong, _("Show AutoTimer List"))
		}, -1, description=_("EPG Actions"))
		self["coloractions"].csel = self
		self["recordingactions"] = HelpableActionMap(self, ["InfobarInstantRecord"], {
			"ShortRecord": (self.recButtonPressed, _("Add a RecordTimer for current event")),
			"LongRecord": (self.recButtonPressedLong, _("Add a ZapTimer for current event"))
		}, prio=-1, description=_("Record Actions"))
		self["recordingactions"].csel = self
		if self.type == EPG_TYPE_SIMILAR:
			self.currentService = service
			self.eventid = eventid
		elif self.type == EPG_TYPE_SINGLE:
			self.currentService = ServiceReference(service)
		elif self.type == EPG_TYPE_INFOBAR or self.type == EPG_TYPE_ENHANCED:
			if self.type == EPG_TYPE_INFOBAR:
				self.skinName = "QuickEPG"
			self["input_actions"] = HelpableNumberActionMap(self, ["NumberActions"], {
				"0": (self.keyNumberGlobal, _("Enter number to jump to channel")),
				"1": (self.keyNumberGlobal, _("Enter number to jump to channel")),
				"2": (self.keyNumberGlobal, _("Enter number to jump to channel")),
				"3": (self.keyNumberGlobal, _("Enter number to jump to channel")),
				"4": (self.keyNumberGlobal, _("Enter number to jump to channel")),
				"5": (self.keyNumberGlobal, _("Enter number to jump to channel")),
				"6": (self.keyNumberGlobal, _("Enter number to jump to channel")),
				"7": (self.keyNumberGlobal, _("Enter number to jump to channel")),
				"8": (self.keyNumberGlobal, _("Enter number to jump to channel")),
				"9": (self.keyNumberGlobal, _("Enter number to jump to channel"))
			}, prio=-1, description=_("EPG Channel/Service Selection"))
			self["input_actions"].csel = self
			self.list = []
			self.servicelist = service
			self.currentService = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		elif self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			if self.type == EPG_TYPE_GRAPH:
				if not config.epgselection.graph_pig.value:
					self.skinName = "GraphicalEPG"
				else:
					self.skinName = "GraphicalEPGPIG"
				now = time() - int(config.epgselection.graph_histminutes.value) * 60
				self.ask_time = now - now % (int(config.epgselection.graph_roundto.value) * 60)
				if "primetime" in config.epgselection.graph_startmode.value:
					basetime = localtime(self.ask_time)
					basetime = (basetime[0], basetime[1], basetime[2], int(config.epgselection.graph_primetimehour.value), int(config.epgselection.graph_primetimemins.value), 0, basetime[6], basetime[7], basetime[8])
					self.ask_time = mktime(basetime)
					if self.ask_time + 3600 < time():
						self.ask_time += 86400
			elif self.type == EPG_TYPE_INFOBARGRAPH:
				self.skinName = "GraphicalInfoBarEPG"
				now = time() - int(config.epgselection.infobar_histminutes.value) * 60
				self.ask_time = now - now % (int(config.epgselection.infobar_roundto.value) * 60)
			self.closeRecursive = False
			self.bouquetlist_active = False
			self["bouquetlist"] = EPGBouquetList(graphic=graphic)
			self["bouquetlist"].hide()
			self["timeline_text"] = TimelineText(type=self.type, graphic=graphic)
			self["Event"] = Event()
			self["primetime"] = Label(_("PRIMETIME"))
			self["change_bouquet"] = Label(_("CHANGE BOUQUET"))
			self["jump"] = Label(_("JUMP 24 HOURS"))
			self["page"] = Label(_("PAGE UP/DOWN"))
			self.time_lines = []
			for x in list(range(0, MAX_TIMELINES)):
				pm = Pixmap()
				self.time_lines.append(pm)
				self[f"timeline{x}"] = pm
			self["timeline_now"] = Pixmap()
			self.updateTimelineTimer = eTimer()
			self.updateTimelineTimer.callback.append(self.moveTimeLines)
			self.updateTimelineTimer.start(60000)
			self["bouquetokactions"] = HelpableActionMap(self, ["OkCancelActions"], {
				"cancel": (self.BouquetlistHide, _("Close bouquet list.")),
				"OK": (self.BouquetOK, _("Change to bouquet")),
			}, prio=-1, description=_("EPG Bouquet Actions"))
			self["bouquetokactions"].csel = self
			self["bouquetokactions"].setEnabled(False)
			self["input_actions"] = HelpableNumberActionMap(self, ["NumberActions"], {
				"1": (self.keyNumberGlobal, _("Reduce time scale")),
				"2": (self.keyNumberGlobal, _("Page up")),
				"3": (self.keyNumberGlobal, _("Increase time scale")),
				"4": (self.keyNumberGlobal, _("Page left")),
				"5": (self.keyNumberGlobal, _("Jump to current time")),
				"6": (self.keyNumberGlobal, _("Page right")),
				"7": (self.keyNumberGlobal, _("No of items switch (increase or reduced)")),
				"8": (self.keyNumberGlobal, _("Page down")),
				"9": (self.keyNumberGlobal, _("Jump to prime time")),
				"0": (self.keyNumberGlobal, _("Move to home of list"))
			}, prio=-1, description=_("EPG Display Actions"))
			self["input_actions"].csel = self
		elif self.type == EPG_TYPE_MULTI:
			self.skinName = "EPGSelectionMulti"
			self["bouquetlist"] = EPGBouquetList(graphic=graphic)
			self["bouquetlist"].hide()
			self["now_button"] = Pixmap()
			self["next_button"] = Pixmap()
			self["more_button"] = Pixmap()
			self["now_button_sel"] = Pixmap()
			self["next_button_sel"] = Pixmap()
			self["more_button_sel"] = Pixmap()
			self["now_text"] = Label()
			self["next_text"] = Label()
			self["more_text"] = Label()
			self["date"] = Label()
			self.bouquetlist_active = False
			self["bouquetokactions"] = HelpableActionMap(self, ["OkCancelActions"], {
				"OK": (self.BouquetOK, _("Change to bouquet")),
			}, prio=-1)
			self["bouquetokactions"].csel = self
			self["bouquetokactions"].setEnabled(False)
		elif self.type == EPG_TYPE_VERTICAL:
			if config.epgselection.vertical_pig.value:
				self.Fields = 4
				self.skinName = "EPGverticalPIG"
			else:
				self.Fields = 6
				self.skinName = "EPGvertical"
			self["bouquetlist"] = EPGBouquetList(graphic=graphic)
			self["bouquetlist"].hide()
			self["list"] = MenuList([])
			self["piconCh1"] = ServiceEvent()
			self["piconCh2"] = ServiceEvent()
			self["piconCh3"] = ServiceEvent()
			self["piconCh4"] = ServiceEvent()
			self["piconCh5"] = ServiceEvent()
			self["currCh1"] = Label(" ")
			self["currCh2"] = Label(" ")
			self["currCh3"] = Label(" ")
			self["currCh4"] = Label(" ")
			self["currCh5"] = Label(" ")
			self["Active1"] = Label(" ")
			self["Active2"] = Label(" ")
			self["Active3"] = Label(" ")
			self["Active4"] = Label(" ")
			self["Active5"] = Label(" ")
			self["list1"] = EPGList(type=EPG_TYPE_VERTICAL, selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer)
			self["list2"] = EPGList(type=EPG_TYPE_VERTICAL, selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer)
			self["list3"] = EPGList(type=EPG_TYPE_VERTICAL, selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer)
			self["list4"] = EPGList(type=EPG_TYPE_VERTICAL, selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer)
			self["list5"] = EPGList(type=EPG_TYPE_VERTICAL, selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer)
			self["bouquetokactions"] = HelpableActionMap(self, ["OkCancelActions"], {
				"cancel": (self.BouquetlistHide, _("Close bouquet list")),
				"OK": (self.BouquetOK, _("Change to bouquet")),
			}, prio=-1)
			self["bouquetokactions"].csel = self
			self["bouquetokactions"].setEnabled(False)
			self["input_actions"] = HelpableNumberActionMap(self, ["NumberActions"], {
				"1": (self.keyNumberGlobal, _("Goto first channel")),
				"2": (self.keyNumberGlobal, _("All events up")),
				"3": (self.keyNumberGlobal, _("Goto last channel")),
				"4": (self.keyNumberGlobal, _("Previous channel page")),
				"0": (self.keyNumberGlobal, _("Goto current channel and now")),
				"6": (self.keyNumberGlobal, _("Next channel page")),
				"7": (self.keyNumberGlobal, _("Goto now")),
				"8": (self.keyNumberGlobal, _("All events down")),
				"9": (self.keyNumberGlobal, _("Goto Prime Time")),
				"5": (self.keyNumberGlobal, _("Set Base Time"))
			}, prio=-1, description=_("EPG Other Actions"))
		if self.type == EPG_TYPE_GRAPH:
			time_epoch = int(config.epgselection.graph_prevtimeperiod.value)
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			time_epoch = int(config.epgselection.infobar_prevtimeperiod.value)
		else:
			time_epoch = None
		if self.type != EPG_TYPE_VERTICAL:
			self["list"] = EPGList(type=self.type, selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer, time_epoch=time_epoch, overjump_empty=config.epgselection.overjump.value, graphic=graphic)
		self.onLayoutFinish.append(self.LayoutFinish)
		self.refreshTimer = eTimer()
		self.refreshTimer.timeout.get().append(self.refreshlist)

	def createSetup(self):
		def createSetupCallback(test=None):
			if closeType:
				self.close(closeType)

		self.closeEventViewDialog()
		key, closeType = {
			EPG_TYPE_SINGLE: ("EPGSingle", None),
			EPG_TYPE_MULTI: ("EPGMulti", None),
			EPG_TYPE_ENHANCED: ("EPGEnhanced", None),
			EPG_TYPE_INFOBAR: ("EPGInfobar", "reopeninfobar"),
			EPG_TYPE_GRAPH: ("EPGGraphical", "reopengraph"),
			EPG_TYPE_INFOBARGRAPH: ("EPGInfobarGraphical", "reopeninfobargraph"),
			EPG_TYPE_VERTICAL: ("EPGVertical", "reopenvertical")
		}.get(self.type, (None, None))
		if key:
			self.session.openWithCallback(createSetupCallback, Setup, key)

	def setupKeyPlayButtonDisplay(self, stime, service):
		ena = self["list"].detectCatchupAvailable(stime, service)
		self["epgcatchupactions"].setEnabled(ena)

	def playCatchup(self):
		event, service = self["list"].getCurrent()[:2]
		stime = event and event.getBeginTime()
		service = service and service.ref
		if self["list"].detectCatchupAvailable(stime, service):
			self.catchupPlayerFunc(event, service)

	def togglePIG(self):
		if self.type == EPG_TYPE_VERTICAL:
			config.epgselection.vertical_pig.value = not config.epgselection.vertical_pig.value
			config.epgselection.vertical_pig.save()
			closeType = "reopenvertical"
		else:
			config.epgselection.graph_pig.value = not config.epgselection.graph_pig.value
			config.epgselection.graph_pig.save()
			closeType = "reopengraph"
		configfile.save()
		self.close(closeType)

	def getBouquetServices(self, bouquet):
		services = []
		from Screens.InfoBar import InfoBar
		if InfoBar.instance.servicelist.isSubservices(bouquet):
			return [ServiceReference(ref) for ref in InfoBar.instance.servicelist.getSubservices()]
		servicelist = eServiceCenter.getInstance().list(bouquet)
		if servicelist is not None:
			while True:
				service = servicelist.getNext()
				if not service.valid():  # Check if end of list.
					break
				if service.flags & (eServiceReference.isDirectory | eServiceReference.isMarker):  # Ignore non-playable services.
					continue
				services.append(ServiceReference(service))
		return services

	def LayoutFinish(self):
		self.createTimer = eTimer()
		self.createTimer.start(500, True)
		self["lab1"].show()
		self.onCreate()

	def onCreate(self):
		title = None
		self.BouquetRoot = False
		serviceref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if self.type != EPG_TYPE_VERTICAL:
			self["list"].recalcEntrySize()
		if self.type == EPG_TYPE_VERTICAL:
			self.ask_time = -1
			self.lastEventTime = (time(), time() + 3600)
			self.BouquetRoot = False
			if self.StartBouquet.toString().startswith("1:7:0"):
				self.BouquetRoot = True
			self.services = self.getBouquetServices(self.StartBouquet)
			self["bouquetlist"].recalcEntrySize()
			self["bouquetlist"].fillBouquetList(self.bouquets)
			self["bouquetlist"].moveToService(self.StartBouquet)
			self["bouquetlist"].setCurrentBouquet(self.StartBouquet)
			self.setTitle(self["bouquetlist"].getCurrentBouquet())
			self["list"].setList(self.getChannels())
			if self.servicelist:
				service = ServiceReference(self.servicelist.getCurrentSelection())
				info = service and service.info()
				nameROH = info and info.getName(service.ref).replace("\xc2\x86", "").replace("\xc2\x87", "")
			else:
				service = self.session.nav.getCurrentService()
				info = service and service.info()
				nameROH = info and info.getName().replace("\xc2\x86", "").replace("\xc2\x87", "")
			if (nameROH is not None) and "channel1" not in config.epgselection.vertical_startmode.value:
				idx = 0
				for channel in self.myServices:
					idx += 1
					if channel[1] == nameROH:
						break
				page = idx // (self.Fields - 1)
				row = idx % (self.Fields - 1)
				if row:
					self.activeList = row
				else:
					page -= 1
					self.activeList = self.Fields - 1
				self["list"].moveToIndex(0)
				for i in list(range(0, page)):
					self["list"].pageDown()
			else:
				self["list"].moveToIndex(0)
			self["Service"].newService(service.ref)
			if self.firststart and "primetime" in config.epgselection.vertical_startmode.value:
				self.gotoPrimetime()
			else:
				self.updateVerticalEPG()
			self.firststart = False
		elif self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH or self.type == EPG_TYPE_MULTI:
			if self.StartBouquet.toString().startswith("1:7:0"):
				self.BouquetRoot = True
			self.services = self.getBouquetServices(self.StartBouquet)
			self["bouquetlist"].recalcEntrySize()
			self["bouquetlist"].fillBouquetList(self.bouquets)
			self["bouquetlist"].moveToService(self.StartBouquet)
			self["bouquetlist"].setCurrentBouquet(self.StartBouquet)
			self.setTitle(self["bouquetlist"].getCurrentBouquet())
			if self.type == EPG_TYPE_MULTI:
				self["list"].fillMultiEPG(self.services, self.ask_time)
			else:
				self["list"].fillGraphEPG(self.services, self.ask_time, current_service=serviceref)
			self["list"].setCurrentlyPlaying(serviceref)
			self["list"].moveToService(serviceref)
			if self.type != EPG_TYPE_MULTI:
				self["list"].fillGraphEPG(None, self.ask_time, True)
			if self.type == EPG_TYPE_GRAPH:
				self["list"].setShowServiceMode(config.epgselection.graph_servicetitle_mode.value)
				self.moveTimeLines()
				if "channel1" in config.epgselection.graph_startmode.value:
					self["list"].instance.moveSelectionTo(0)
			elif self.type == EPG_TYPE_INFOBARGRAPH:
				self["list"].setShowServiceMode(config.epgselection.infobar_servicetitle_mode.value)
				self.moveTimeLines()
		elif self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			if self.type == EPG_TYPE_SINGLE:
				service = self.currentService
			elif self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
				service = ServiceReference(self.servicelist.getCurrentSelection())
				title = ServiceReference(self.servicelist.getRoot()).getServiceName()
			self["Service"].newService(service.ref)
			if title:
				title = f"{title} - {service.getServiceName()}"
			else:
				title = service.getServiceName()
			self.setTitle(title)
			self["list"].fillSingleEPG(service)
			self["list"].sortSingleEPG(int(config.epgselection.sort.value))
		else:
			self["list"].fillSimilarList(self.currentService, self.eventid)
		self["lab1"].hide()

	def refreshlist(self):
		self.refreshTimer.stop()
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self.ask_time = self["list"].getTimeBase()
			self["list"].fillGraphEPG(None, self.ask_time)
			self.moveTimeLines()
		elif self.type == EPG_TYPE_MULTI:
			curr = self["list"].getCurrentChangeCount()
			self["list"].fillMultiEPG(self.services, self.ask_time)
			for i in list(range(curr)):
				self["list"].updateMultiEPG(1)
		elif self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			try:
				if self.type == EPG_TYPE_SINGLE:
					service = self.currentService
				elif self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
					service = ServiceReference(self.servicelist.getCurrentSelection())
				if not self.cureventindex:
					index = self["list"].getCurrentIndex()
				else:
					index = self.cureventindex
					self.cureventindex = None
				self["list"].fillSingleEPG(service)
				self["list"].sortSingleEPG(int(config.epgselection.sort.value))
				self["list"].setCurrentIndex(index)
			except:
				pass
		elif self.type == EPG_TYPE_VERTICAL:
			curr = self[f"list{self.activeList}"].getSelectedEventId()
			currPrg = self.myServices[self.getActivePrg()]
			l = self[f"list{self.activeList}"]
			l.recalcEntrySize()
			service = ServiceReference(currPrg[0])
			stime = None
			if self.ask_time > time():
				stime = self.ask_time
			l.fillSingleEPG(service, stime)
			self[f"list{self.activeList}"].moveToEventId(curr)

	def moveUp(self):
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self["list"].moveUp()
			self.moveTimeLines(True)
			return
		if self.type == EPG_TYPE_VERTICAL and config.epgselection.vertical_updownbtn.value:
			if self.getEventTime(self.activeList)[0] is None:
				return
			self.saveLastEventTime()
			idx = self[f"list{self.activeList}"].getCurrentIndex()
			if not idx:
				tmp = self.lastEventTime
				self.setMinus24h(True, 6)
				self.lastEventTime = tmp
				self.gotoLasttime()
			elif config.epgselection.vertical_updownbtn.value:
				if not idx % config.epgselection.vertical_itemsperpage.value:
					self.syncUp(idx)
		self[f"list{self.activeList}"].moveTo(self[f"list{self.activeList}"].instance.moveUp)
		if self.type == EPG_TYPE_VERTICAL:
			self.saveLastEventTime()

	def moveDown(self):
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self["list"].moveDown()
			self.moveTimeLines(True)
			return
		if self.type == EPG_TYPE_VERTICAL and config.epgselection.vertical_updownbtn.value:
			idx = self[f"list{self.activeList}"].getCurrentIndex()
			if not (idx + 1) % config.epgselection.vertical_itemsperpage.value:
				self.syncDown(idx + 1)
		self[f"list{self.activeList}"].moveTo(self[f"list{self.activeList}"].instance.moveDown)
		if self.type == EPG_TYPE_VERTICAL:
			self.saveLastEventTime()

	def updEvent(self, dir, visible=True):
		ret = self["list"].selEntry(dir, visible)
		if ret:
			self.moveTimeLines(True)
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self.moveTimeLines(True)

	def nextPage(self, numberkey=False, reverse=False):
		if self.type == EPG_TYPE_VERTICAL:
			if not numberkey and "scroll" in config.epgselection.vertical_channelbtn.value:
				if config.epgselection.vertical_channelbtn_invert.value:
					self.allDown()
				else:
					self.allUp()
			elif not numberkey and "24" in config.epgselection.vertical_channelbtn.value:
				if config.epgselection.vertical_channelbtn_invert.value:
					self.setPlus24h()
				else:
					self.setMinus24h()
			else:
				if not numberkey:
					if not reverse and config.epgselection.vertical_channelbtn_invert.value:
						self.prevPage(reverse=True)
						return
				if len(self.list) <= self["list"].getSelectionIndex() + self.Fields - 1:
					self.gotoFirst()
				else:
					self["list"].pageDown()
					self.activeList = 1
					self.updateVerticalEPG()
				self.gotoLasttime()
		elif self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self["list"].nextPage()
		else:
			self["list"].moveTo(self["list"].instance.pageDown)

	def prevPage(self, numberkey=False, reverse=False):
		if self.type == EPG_TYPE_VERTICAL:
			if not numberkey and "scroll" in config.epgselection.vertical_channelbtn.value:
				if config.epgselection.vertical_channelbtn_invert.value:
					self.allUp()
				else:
					self.allDown()
			elif not numberkey and "24" in config.epgselection.vertical_channelbtn.value:
				if config.epgselection.vertical_channelbtn_invert.value:
					self.setMinus24h()
				else:
					self.setPlus24h()
			else:
				if not numberkey:
					if not reverse and config.epgselection.vertical_channelbtn_invert.value:
						self.nextPage(reverse=True)
						return
				if not self["list"].getSelectionIndex():
					self.gotoLast()
				else:
					self["list"].pageUp()
					self.activeList = (self.Fields - 1)
					self.updateVerticalEPG()
				self.gotoLasttime()
		elif self.type in (EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH) and self["list"].listFirstServiceIndex != 0:  # Workaround for https://github.com/openatv/enigma2/issues/3006#issuecomment-1751998017.
			self["list"].prevPage()
		else:
			self["list"].moveTo(self["list"].instance.pageUp)

	def toTop(self):
		if self.type in (EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH):  # Dirty workaround for #3006. (Pressing '0' no longer goes to first channel in bouquet.)
			self.BouquetOK()
		else:
			self["list"].moveTo(self["list"].instance.moveTop)

	def toEnd(self):
		self["list"].moveTo(self["list"].instance.moveEnd)

	def leftPressed(self):
		if self.type == EPG_TYPE_VERTICAL:
			first = not self["list"].getSelectionIndex() and self.activeList == 1
			if self.activeList > 1 and not first:
				self.activeList -= 1
				self.displayActiveEPG()
			else:
				if first:
					self.gotoLast()
				else:
					self["list"].pageUp()
					self.activeList = (self.Fields - 1)
					self.updateVerticalEPG()
				self.gotoLasttime()
			self.onSelectionChanged()
		elif self.type == EPG_TYPE_MULTI:
			self["list"].updateMultiEPG(-1)
		else:
			self.updEvent(-1)

	def rightPressed(self):
		if self.type == EPG_TYPE_VERTICAL:
			end = len(self.list) == self["list"].getSelectionIndex() + self.activeList
			if self.activeList < (self.Fields - 1) and not end:
				self.activeList += 1
				self.displayActiveEPG()
			else:
				if end:
					self.gotoFirst()
				else:
					self["list"].pageDown()
					self.activeList = 1
					self.updateVerticalEPG()
				self.gotoLasttime()
			self.onSelectionChanged()
		elif self.type == EPG_TYPE_MULTI:
			self["list"].updateMultiEPG(1)
		else:
			self.updEvent(+1)

	def Bouquetlist(self):
		if not self.bouquetlist_active:
			self.BouquetlistShow()
		else:
			self.BouquetlistHide()

	def BouquetlistShow(self):
		self.curindex = self["bouquetlist"].l.getCurrentSelectionIndex()
		self["epgcursoractions"].setEnabled(False)
		self["okactions"].setEnabled(False)
		self["bouquetlist"].show()
		self["bouquetokactions"].setEnabled(True)
		self["bouquetcursoractions"].setEnabled(True)
		self.bouquetlist_active = True

	def BouquetlistHide(self, cancel=True):
		self["bouquetokactions"].setEnabled(False)
		self["bouquetcursoractions"].setEnabled(False)
		self["bouquetlist"].hide()
		if cancel:
			self["bouquetlist"].setCurrentIndex(self.curindex)
		self["okactions"].setEnabled(True)
		self["epgcursoractions"].setEnabled(True)
		self.bouquetlist_active = False

	def getCurrentBouquet(self):
		if self.BouquetRoot:
			return self.StartBouquet
		elif "bouquetlist" in self:
			cur = self["bouquetlist"].l.getCurrentSelection()
			return cur and cur[1]
		else:
			return self.servicelist.getRoot()

	def BouquetOK(self):
		self.BouquetRoot = False
		self.services = self.getBouquetServices(self.getCurrentBouquet())
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			if self.type == EPG_TYPE_GRAPH:
				now = time() - int(config.epgselection.graph_histminutes.value) * 60
				self.ask_time = now - now % (int(config.epgselection.graph_roundto.value) * 60)
				if "primetime" in config.epgselection.graph_startmode.value:
					basetime = localtime(self.ask_time)
					basetime = (basetime[0], basetime[1], basetime[2], int(config.epgselection.graph_primetimehour.value), int(config.epgselection.graph_primetimemins.value), 0, basetime[6], basetime[7], basetime[8])
					self.ask_time = mktime(basetime)
					if self.ask_time + 3600 < time():
						self.ask_time += 86400
			elif self.type == EPG_TYPE_INFOBARGRAPH:
				now = time() - int(config.epgselection.infobar_histminutes.value) * 60
				self.ask_time = now - now % (int(config.epgselection.infobar_roundto.value) * 60)
			self["list"].resetOffset()
			self["list"].fillGraphEPG(self.services, self.ask_time)
			self.moveTimeLines(True)
		elif self.type == EPG_TYPE_MULTI:
			self["list"].fillMultiEPG(self.services, self.ask_time)
		if self.type == EPG_TYPE_VERTICAL:
			self["list"].setList(self.getChannels())
			self.gotoFirst()
		else:
			self["list"].instance.moveSelectionTo(0)
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self["list"].fillGraphEPG(None, self.ask_time, True)
			serviceref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if serviceref:
				self["list"].moveToService(serviceref)
		self.setTitle(self["bouquetlist"].getCurrentBouquet())
		self.BouquetlistHide(False)

	def moveBouquetUp(self):
		self["bouquetlist"].moveTo(self["bouquetlist"].instance.moveUp)
		self["bouquetlist"].fillBouquetList(self.bouquets)

	def moveBouquetDown(self):
		self["bouquetlist"].moveTo(self["bouquetlist"].instance.moveDown)
		self["bouquetlist"].fillBouquetList(self.bouquets)

	def moveBouquetPageUp(self):
		self["bouquetlist"].moveTo(self["bouquetlist"].instance.pageUp)
		self["bouquetlist"].fillBouquetList(self.bouquets)

	def moveBouquetPageDown(self):
		self["bouquetlist"].moveTo(self["bouquetlist"].instance.pageDown)
		self["bouquetlist"].fillBouquetList(self.bouquets)

	def nextBouquet(self):
		if self.type == EPG_TYPE_MULTI or self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH or self.type == EPG_TYPE_VERTICAL:
			self.moveBouquetDown()
			self.BouquetOK()
		elif (self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR) and config.usage.multibouquet.value:
			self.CurrBouquet = self.servicelist.getCurrentSelection()
			self.CurrService = self.servicelist.getRoot()
			self.servicelist.nextBouquet()
			self.onCreate()

	def prevBouquet(self):
		if self.type == EPG_TYPE_MULTI or self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH or self.type == EPG_TYPE_VERTICAL:
			self.moveBouquetUp()
			self.BouquetOK()
		elif (self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR) and config.usage.multibouquet.value:
			self.CurrBouquet = self.servicelist.getCurrentSelection()
			self.CurrService = self.servicelist.getRoot()
			self.servicelist.prevBouquet()
			self.onCreate()

	def nextService(self):
		if self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			self.CurrBouquet = self.servicelist.getCurrentSelection()
			self.CurrService = self.servicelist.getRoot()
			self["list"].instance.moveSelectionTo(0)
			if self.servicelist.inBouquet():
				prev = self.servicelist.getCurrentSelection()
				if prev:
					prev = prev.toString()
					while True:
						if config.usage.quickzap_bouquet_change.value and self.servicelist.atEnd():
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
				if not self["list"].getCurrent()[1] and config.epgselection.overjump.value:
					self.nextService()
			else:
				self.nextService()
		elif self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self.updEvent(+24)
		elif self.serviceChangeCB:
			self.serviceChangeCB(1, self)

	def prevService(self):
		if self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			self.CurrBouquet = self.servicelist.getCurrentSelection()
			self.CurrService = self.servicelist.getRoot()
			self["list"].instance.moveSelectionTo(0)
			if self.servicelist.inBouquet():
				prev = self.servicelist.getCurrentSelection()
				if prev:
					prev = prev.toString()
					while True:
						if config.usage.quickzap_bouquet_change.value:
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
				if not self["list"].getCurrent()[1] and config.epgselection.overjump.value:
					self.prevService()
			else:
				self.prevService()
		elif self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self.updEvent(-24)
		elif self.serviceChangeCB:
			self.serviceChangeCB(-1, self)

	def enterDateTime(self):
		def enterDateTimeCallback(result):
			if len(result) > 1 and result[0]:
				jumpTime = result[1]
				if self.type == EPG_TYPE_MULTI:
					self["list"].fillMultiEPG(self.services, jumpTime)
				elif self.type in (EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH):
					if self.type == EPG_TYPE_GRAPH:
						jumpTime -= jumpTime % (int(config.epgselection.graph_roundto.value) * 60)
					else:
						jumpTime -= jumpTime % (int(config.epgselection.infobar_roundto.value) * 60)
					epgList = self["list"]
					epgList.resetOffset()
					epgList.fillGraphEPG(None, jumpTime)
					self.moveTimeLines(True)
				elif self.type == EPG_TYPE_VERTICAL:
					if jumpTime > time():
						self.updateVerticalEPG()
					else:
						jumpTime = -1
				self.ask_time = jumpTime
			if self.eventviewDialog and self.type in (EPG_TYPE_INFOBAR, EPG_TYPE_INFOBARGRAPH):
				self.infoKeyPressed(True)

		if self.type == EPG_TYPE_GRAPH:
			self.session.openWithCallback(enterDateTimeCallback, EPGJumpTime, config.epgselection.graph_prevtime, config.epg.histminutes.value)
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			self.session.openWithCallback(enterDateTimeCallback, EPGJumpTime, config.epgselection.infobar_prevtime, config.epg.histminutes.value)
		elif self.type == EPG_TYPE_MULTI:
			global mepg_config_initialized
			if not mepg_config_initialized:
				config.misc.prev_mepg_time = ConfigClock(default=time())
				mepg_config_initialized = True
			self.session.openWithCallback(enterDateTimeCallback, EPGJumpTime, config.misc.prev_mepg_time, 0)
		elif self.type == EPG_TYPE_VERTICAL:
			self.session.openWithCallback(enterDateTimeCallback, EPGJumpTime, config.epgselection.vertical_prevtime, config.epg.histminutes.value)

	def infoKeyPressed(self, eventviewopen=False):
		cur = self[f"list{self.activeList}"].getCurrent()
		event = cur[0]
		service = cur[1]
		if event is not None and not self.eventviewDialog and not eventviewopen:
			if self.type != EPG_TYPE_SIMILAR:
				if self.type == EPG_TYPE_INFOBARGRAPH:
					self.eventviewDialog = self.session.instantiateDialog(EventViewSimple, event, service, skin="InfoBarEventView")
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
					self.eventviewDialog = self.session.instantiateDialog(EventViewSimple, event, service, skin="InfoBarEventView")
					self.eventviewDialog.show()

	def redButtonPressed(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
				if config.epgselection.graph_red.value == "24plus":
					self.nextService()
				if config.epgselection.graph_red.value == "24minus":
					self.prevService()
				if config.epgselection.graph_red.value == "timer":
					self.RecordTimerQuestion(True)
				if config.epgselection.graph_red.value == "imdb" or config.epgselection.graph_red.value is None:
					self.openIMDb()
				if config.epgselection.graph_red.value == "tmdb":
					self.openTMDB()
				if config.epgselection.graph_red.value == "autotimer":
					self.addAutoTimer()
				if config.epgselection.graph_red.value == "bouquetlist":
					self.Bouquetlist()
				if config.epgselection.graph_red.value == "epgsearch":
					self.openEPGSearch()
				if config.epgselection.graph_red.value == "showmovies":
					self.showMovieSelection()
				if config.epgselection.graph_red.value == "record":
					self.RecordTimerQuestion()
				if config.epgselection.graph_red.value == "gotodatetime":
					self.enterDateTime()
				if config.epgselection.graph_red.value == "nextpage" and self.type == EPG_TYPE_GRAPH:
					self.nextPage()
				if config.epgselection.graph_red.value == "prevpage" and self.type == EPG_TYPE_GRAPH:
					self.prevPage()
				if config.epgselection.graph_red.value == "nextbouquet" and self.type == EPG_TYPE_GRAPH:
					self.nextBouquet()
				if config.epgselection.graph_red.value == "prevbouquet" and self.type == EPG_TYPE_GRAPH:
					self.prevBouquet()
			elif self.type == EPG_TYPE_VERTICAL:
				if config.epgselection.vertical_red.value == "24plus":
					self.setPlus24h()
				if config.epgselection.vertical_red.value == "24minus":
					self.setMinus24h()
				if config.epgselection.vertical_red.value == "timer":
					self.RecordTimerQuestion(True)
				if config.epgselection.vertical_red.value == "imdb" or config.epgselection.vertical_red.value is None:
					self.openIMDb()
				if config.epgselection.vertical_red.value == "tmdb":
					self.openTMDB()
				if config.epgselection.vertical_red.value == "autotimer":
					self.addAutoTimer()
				if config.epgselection.vertical_red.value == "bouquetlist":
					self.Bouquetlist()
				if config.epgselection.vertical_red.value == "epgsearch":
					self.openEPGSearch()
				if config.epgselection.vertical_red.value == "showmovies":
					self.showMovieSelection()
				if config.epgselection.vertical_red.value == "record":
					self.RecordTimerQuestion()
				if config.epgselection.vertical_red.value == "gotoprimetime":
					self.gotoPrimetime()
				if config.epgselection.vertical_red.value == "setbasetime":
					self.setBasetime()
				if config.epgselection.vertical_red.value == "gotodatetime":
					self.enterDateTime()
			else:
				self.openIMDb()

	def redButtonPressedLong(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance.LongButtonPressed:
			self.sortEpg()

	def greenButtonPressed(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
				if config.epgselection.graph_green.value == "24plus":
					self.nextService()
				if config.epgselection.graph_green.value == "24minus":
					self.prevService()
				if config.epgselection.graph_green.value == "timer" or config.epgselection.graph_green.value is None:
					self.RecordTimerQuestion(True)
				if config.epgselection.graph_green.value == "imdb":
					self.openIMDb()
				if config.epgselection.graph_green.value == "tmdb":
					self.openTMDB()
				if config.epgselection.graph_green.value == "autotimer":
					self.addAutoTimer()
				if config.epgselection.graph_green.value == "bouquetlist":
					self.Bouquetlist()
				if config.epgselection.graph_green.value == "epgsearch":
					self.openEPGSearch()
				if config.epgselection.graph_green.value == "showmovies":
					self.showMovieSelection()
				if config.epgselection.graph_green.value == "record":
					self.RecordTimerQuestion()
				if config.epgselection.graph_green.value == "gotodatetime":
					self.enterDateTime()
				if config.epgselection.graph_green.value == "nextpage" and self.type == EPG_TYPE_GRAPH:
					self.nextPage()
				if config.epgselection.graph_green.value == "prevpage" and self.type == EPG_TYPE_GRAPH:
					self.prevPage()
				if config.epgselection.graph_green.value == "nextbouquet" and self.type == EPG_TYPE_GRAPH:
					self.nextBouquet()
				if config.epgselection.graph_green.value == "prevbouquet" and self.type == EPG_TYPE_GRAPH:
					self.prevBouquet()
			elif self.type == EPG_TYPE_VERTICAL:
				if config.epgselection.vertical_green.value == "24plus":
					self.setPlus24h()
				if config.epgselection.vertical_green.value == "24minus":
					self.setMinus24h()
				if config.epgselection.vertical_green.value == "timer":
					self.RecordTimerQuestion(True)
				if config.epgselection.vertical_green.value == "imdb" or config.epgselection.vertical_green.value is None:
					self.openIMDb()
				if config.epgselection.vertical_green.value == "tmdb":
					self.openTMDB()
				if config.epgselection.vertical_green.value == "autotimer":
					self.addAutoTimer()
				if config.epgselection.vertical_green.value == "bouquetlist":
					self.Bouquetlist()
				if config.epgselection.vertical_green.value == "epgsearch":
					self.openEPGSearch()
				if config.epgselection.vertical_green.value == "showmovies":
					self.showMovieSelection()
				if config.epgselection.vertical_green.value == "record":
					self.RecordTimerQuestion()
				if config.epgselection.vertical_green.value == "gotoprimetime":
					self.gotoPrimetime()
				if config.epgselection.vertical_green.value == "setbasetime":
					self.setBasetime()
				if config.epgselection.vertical_green.value == "gotodatetime":
					self.enterDateTime()
			else:
				self.RecordTimerQuestion(True)

	def greenButtonPressedLong(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance.LongButtonPressed:
			self.showTimerList()

	def yellowButtonPressed(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
				if config.epgselection.graph_yellow.value == "24plus":
					self.nextService()
				if config.epgselection.graph_yellow.value == "24minus":
					self.prevService()
				if config.epgselection.graph_yellow.value == "timer":
					self.RecordTimerQuestion(True)
				if config.epgselection.graph_yellow.value == "imdb":
					self.openIMDb()
				if config.epgselection.graph_yellow.value == "tmdb":
					self.openTMDB()
				if config.epgselection.graph_yellow.value == "autotimer":
					self.addAutoTimer()
				if config.epgselection.graph_yellow.value == "bouquetlist":
					self.Bouquetlist()
				if config.epgselection.graph_yellow.value == "epgsearch" or config.epgselection.graph_yellow.value is None:
					self.openEPGSearch()
				if config.epgselection.graph_yellow.value == "showmovies":
					self.showMovieSelection()
				if config.epgselection.graph_yellow.value == "record":
					self.RecordTimerQuestion()
				if config.epgselection.graph_yellow.value == "gotodatetime":
					self.enterDateTime()
				if config.epgselection.graph_yellow.value == "nextpage" and self.type == EPG_TYPE_GRAPH:
					self.nextPage()
				if config.epgselection.graph_yellow.value == "prevpage" and self.type == EPG_TYPE_GRAPH:
					self.prevPage()
				if config.epgselection.graph_yellow.value == "nextbouquet" and self.type == EPG_TYPE_GRAPH:
					self.nextBouquet()
				if config.epgselection.graph_yellow.value == "prevbouquet" and self.type == EPG_TYPE_GRAPH:
					self.prevBouquet()
			elif self.type == EPG_TYPE_VERTICAL:
				if config.epgselection.vertical_yellow.value == "24plus":
					self.setPlus24h()
				if config.epgselection.vertical_yellow.value == "24minus":
					self.setMinus24h()
				if config.epgselection.vertical_yellow.value == "timer":
					self.RecordTimerQuestion(True)
				if config.epgselection.vertical_yellow.value == "imdb" or config.epgselection.vertical_yellow.value is None:
					self.openIMDb()
				if config.epgselection.vertical_yellow.value == "tmdb":
					self.openTMDB()
				if config.epgselection.vertical_yellow.value == "autotimer":
					self.addAutoTimer()
				if config.epgselection.vertical_yellow.value == "bouquetlist":
					self.Bouquetlist()
				if config.epgselection.vertical_yellow.value == "epgsearch":
					self.openEPGSearch()
				if config.epgselection.vertical_yellow.value == "showmovies":
					self.showMovieSelection()
				if config.epgselection.vertical_yellow.value == "record":
					self.RecordTimerQuestion()
				if config.epgselection.vertical_yellow.value == "gotoprimetime":
					self.gotoPrimetime()
				if config.epgselection.vertical_yellow.value == "setbasetime":
					self.setBasetime()
				if config.epgselection.vertical_yellow.value == "gotodatetime":
					self.enterDateTime()
			else:
				self.openEPGSearch()

	def blueButtonPressed(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
				if config.epgselection.graph_blue.value == "24plus":
					self.nextService()
				if config.epgselection.graph_blue.value == "24minus":
					self.prevService()
				if config.epgselection.graph_blue.value == "timer":
					self.RecordTimerQuestion(True)
				if config.epgselection.graph_blue.value == "imdb":
					self.openIMDb()
				if config.epgselection.graph_blue.value == "tmdb":
					self.openTMDB()
				if config.epgselection.graph_blue.value == "autotimer" or config.epgselection.graph_blue.value is None:
					self.addAutoTimer()
				if config.epgselection.graph_blue.value == "bouquetlist":
					self.Bouquetlist()
				if config.epgselection.graph_blue.value == "epgsearch":
					self.openEPGSearch()
				if config.epgselection.graph_blue.value == "showmovies":
					self.showMovieSelection()
				if config.epgselection.graph_blue.value == "record":
					self.RecordTimerQuestion()
				if config.epgselection.graph_blue.value == "gotodatetime":
					self.enterDateTime()
				if config.epgselection.graph_blue.value == "nextpage" and self.type == EPG_TYPE_GRAPH:
					self.nextPage()
				if config.epgselection.graph_blue.value == "prevpage" and self.type == EPG_TYPE_GRAPH:
					self.prevPage()
				if config.epgselection.graph_blue.value == "nextbouquet" and self.type == EPG_TYPE_GRAPH:
					self.nextBouquet()
				if config.epgselection.graph_blue.value == "prevbouquet" and self.type == EPG_TYPE_GRAPH:
					self.prevBouquet()
			elif self.type == EPG_TYPE_VERTICAL:
				if config.epgselection.vertical_blue.value == "24plus":
					self.setPlus24h()
				if config.epgselection.vertical_blue.value == "24minus":
					self.setMinus24h()
				if config.epgselection.vertical_blue.value == "timer":
					self.RecordTimerQuestion(True)
				if config.epgselection.vertical_blue.value == "imdb" or config.epgselection.vertical_blue.value is None:
					self.openIMDb()
				if config.epgselection.vertical_blue.value == "tmdb":
					self.openTMDB()
				if config.epgselection.vertical_blue.value == "autotimer":
					self.addAutoTimer()
				if config.epgselection.vertical_blue.value == "bouquetlist":
					self.Bouquetlist()
				if config.epgselection.vertical_blue.value == "epgsearch":
					self.openEPGSearch()
				if config.epgselection.vertical_blue.value == "showmovies":
					self.showMovieSelection()
				if config.epgselection.vertical_blue.value == "record":
					self.RecordTimerQuestion()
				if config.epgselection.vertical_blue.value == "gotoprimetime":
					self.gotoPrimetime()
				if config.epgselection.vertical_blue.value == "setbasetime":
					self.setBasetime()
				if config.epgselection.vertical_blue.value == "gotodatetime":
					self.enterDateTime()
			else:
				self.addAutoTimer()

	def blueButtonPressedLong(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance.LongButtonPressed:
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
		l = self[f"list{self.activeList}"]
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
		if self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			if config.epgselection.sort.value == "0":
				config.epgselection.sort.setValue("1")
			else:
				config.epgselection.sort.setValue("0")
			config.epgselection.sort.save()
			configfile.save()
			self["list"].sortSingleEPG(int(config.epgselection.sort.value))

	def OpenSingleEPG(self):
		cur = self[f"list{self.activeList}"].getCurrent()
		if cur[0] is not None:
			event = cur[0]
			serviceref = cur[1].ref
			if serviceref is not None:
				self.session.open(SingleEPG, serviceref)

	def openIMDb(self):
		try:
			from Plugins.Extensions.IMDb.plugin import IMDB
			try:
				cur = self[f"list{self.activeList}"].getCurrent()
				event = cur[0]
				name = event.getEventName()
			except:
				name = ""
			self.session.open(IMDB, name, False)
		except ImportError:
			self.session.open(MessageBox, _("The IMDb plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def openTMDB(self):
		try:
			from Plugins.Extensions.tmdb.tmdb import tmdbScreen
			try:
				cur = self[f"list{self.activeList}"].getCurrent()
				event = cur[0]
				name = event.getEventName()
			except:
				name = ""
			self.session.open(tmdbScreen, name)
		except ImportError:
			self.session.open(MessageBox, _("The TMDB plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def openEPGSearch(self):
		try:
			from Plugins.Extensions.EPGSearch.EPGSearch import EPGSearch
			try:
				cur = self[f"list{self.activeList}"].getCurrent()
				event = cur[0]
				name = event.getEventName()
			except:
				name = ""
			self.session.open(EPGSearch, name, False)
		except ImportError:
			self.session.open(MessageBox, _("The EPGSearch plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def addAutoTimer(self):
		try:
			from Plugins.Extensions.AutoTimer.AutoTimerEditor import addAutotimerFromEvent
			cur = self[f"list{self.activeList}"].getCurrent()
			event = cur[0]
			if not event:
				return
			serviceref = cur[1]
			addAutotimerFromEvent(self.session, evt=event, service=serviceref)
			self.refreshTimer.start(3000)
		except ImportError:
			self.session.open(MessageBox, _("The AutoTimer plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def addAutoTimerSilent(self):
		try:
			from Plugins.Extensions.AutoTimer.AutoTimerEditor import addAutotimerFromEventSilent
			cur = self[f"list{self.activeList}"].getCurrent()
			event = cur[0]
			if not event:
				return
			serviceref = cur[1]
			addAutotimerFromEventSilent(self.session, evt=event, service=serviceref)
			self.refreshTimer.start(3000)
		except ImportError:
			self.session.open(MessageBox, _("The AutoTimer plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def showTimerList(self):
		from Screens.Timers import RecordTimerOverview
		self.session.open(RecordTimerOverview)

	def showMovieSelection(self):
		from Screens.InfoBar import InfoBar
		InfoBar.instance.showMovies()

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
				self.session.open(MessageBox, _("Your config file is not well-formed:\n%s") % str(se), type=MessageBox.TYPE_ERROR, timeout=10)
				return

			if autopoller is not None:
				autopoller.stop()
			from Plugins.Extensions.AutoTimer.AutoTimerOverview import AutoTimerOverview
			self.session.openWithCallback(self.editCallback, AutoTimerOverview, autotimer)
		except ImportError:
			self.session.open(MessageBox, _("The AutoTimer plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def editCallback(self, session):
		global autopoller
		global autotimer
		if session is not None:
			autotimer.writeXml()
			autotimer.parseEPG()
		if config.plugins.autotimer.autopoll.value:
			if autopoller is None:
				from Plugins.Extensions.AutoTimer.AutoPoller import AutoPoller
				autopoller = AutoPoller()
			autopoller.start()
		else:
			autopoller = None
			autotimer = None

	def timerAdd(self):
		self.RecordTimerQuestion(True)

	def editTimer(self, timer):
		self.session.open(TimerEntry, timer)

	def removeTimer(self, timer):
		self.closeChoiceBoxDialog()
		timer.afterEvent = AFTEREVENT.NONE
		self.session.nav.RecordTimer.removeEntry(timer)
		self.setTimerButtonText(_("Add Timer"))
		self.key_green_choice = self.ADD_TIMER
		self.refreshlist()

	def disableTimer(self, timer):
		self.closeChoiceBoxDialog()
		timer.disable()
		self.session.nav.RecordTimer.timeChanged(timer)
		self.setTimerButtonText(_("Add Timer"))
		self.key_green_choice = self.ADD_TIMER
		self.refreshlist()

	def enableTimer(self, timer):
		self.closeChoiceBoxDialog()
		timer.enable()
		self.session.nav.RecordTimer.timeChanged(timer)
		self.setTimerButtonText(_("Add Timer"))
		self.key_green_choice = self.ADD_TIMER
		self.refreshlist()

	def RecordTimerQuestion(self, manual=False):
		cur = self[f"list{self.activeList}"].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		serviceRefStr = serviceref.ref.toCompareString()
		title = None
		foundtimer = self.getRecordEvent(serviceRefStr, event)
		if foundtimer:
			timer = foundtimer
			if timer.isRunning():
				cb_func1 = lambda ret: self.removeTimer(timer)
				cb_func2 = lambda ret: self.editTimer(timer)
				menu = [
					(_("Delete Timer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb_func1),
					(_("Edit Timer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb_func2)
				]
			else:
				cb_func1 = lambda ret: self.removeTimer(timer)
				cb_func2 = lambda ret: self.editTimer(timer)
				cb_func3 = lambda ret: self.disableTimer(timer)
				cb_func4 = lambda ret: self.enableTimer(timer)
				menu = [
					(_("Delete Timer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb_func1),
					(_("Edit Timer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb_func2)
				]
				if timer.disabled:
					menu.append((_("Enable timer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb_func4))
				else:
					menu.append((_("Disable timer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb_func3))
			title = _("Select action for timer %s:") % event.getEventName()
		else:
			if not manual:
				cb_func1 = lambda ret: self.doRecordTimer(True)
				menu = [
					(_("Add RecordTimer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb_func1),
					(_("Add ZapTimer"), "CALLFUNC", self.ChoiceBoxCB, self.doZapTimer),
					(_("Add Zap+RecordTimer"), "CALLFUNC", self.ChoiceBoxCB, self.doZapRecordTimer),
					(_("Add AutoTimer"), "CALLFUNC", self.ChoiceBoxCB, self.addAutoTimerSilent)
				]
				title = f"{event.getEventName()}?"
			else:
				newEntry = RecordTimerEntry(serviceref, checkOldTimers=True, dirname=preferredTimerPath(), *parseEvent(event))
				self.session.openWithCallback(self.finishedAdd, TimerEntry, newEntry)

		if title:
			self.ChoiceBoxDialog = self.session.instantiateDialog(ChoiceBox, text=title, choiceList=menu, buttonList=["red", "green", "yellow", "blue"], skinName="RecordTimerQuestion")
			serviceRef = eServiceReference(str(self[f"list{self.activeList}"].getCurrent()[1]))
			pos = self[f"list{self.activeList}"].getSelectionPosition(serviceRef, self.activeList)
			posX = max(self.instance.position().x() + pos[0] - self.ChoiceBoxDialog.instance.size().width(), 0)
			posY = self.instance.position().y() + pos[1]
			posY += self[f"list{self.activeList}"].itemHeight - 2
			if posY + self.ChoiceBoxDialog.instance.size().height() > 720:
				posY -= self[f"list{self.activeList}"].itemHeight - 4 + self.ChoiceBoxDialog.instance.size().height()
			self.ChoiceBoxDialog.instance.move(ePoint(int(posX), int(posY)))
			self.showChoiceBoxDialog()

	def recButtonPressed(self):
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			self.RecordTimerQuestion()

	def recButtonPressedLong(self):
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance.LongButtonPressed:
			self.doZapTimer()

	def RemoveChoiceBoxCB(self, choice):
		self.closeChoiceBoxDialog()
		if choice:
			choice(self)

	def ChoiceBoxCB(self, choice):
		self.closeChoiceBoxDialog()
		if choice:
			try:
				choice()
			except:
				choice

	def showChoiceBoxDialog(self):
		self["okactions"].setEnabled(False)
		if "epgcursoractions" in self:
			self["epgcursoractions"].setEnabled(False)
		if "coloractions" in self:
			self["coloractions"].setEnabled(False)
		if "colouractions" in self:
			self["colouractions"].setEnabled(False)
		self["recordingactions"].setEnabled(False)
		self["epgactions"].setEnabled(False)
		self["dialogactions"].setEnabled(True)
		self["epgcatchupactions"].setEnabled(False)
		self.ChoiceBoxDialog.instantiateActionMap(True)
		self.ChoiceBoxDialog.show()
		if "input_actions" in self:
			self["input_actions"].setEnabled(False)

	def closeChoiceBoxDialog(self):
		self["dialogactions"].setEnabled(False)
		if self.ChoiceBoxDialog:
			self.ChoiceBoxDialog.instantiateActionMap(False)
			self.session.deleteDialog(self.ChoiceBoxDialog)
		self["okactions"].setEnabled(True)
		if "epgcursoractions" in self:
			self["epgcursoractions"].setEnabled(True)
		if "coloractions" in self:
			self["coloractions"].setEnabled(True)
		if "colouractions" in self:
			self["colouractions"].setEnabled(True)
		self["recordingactions"].setEnabled(True)
		self["epgactions"].setEnabled(True)
		if "input_actions" in self:
			self["input_actions"].setEnabled(True)

	def doRecordTimer(self, rec=False):
		if not rec and "Plugins.Extensions.EPGSearch.EPGSearch.EPGSearch" in repr(self):
			self.RecordTimerQuestion()
		else:
			self.doInstantTimer(0, 0)

	def doZapTimer(self):
		self.doInstantTimer(1, 0)

	def doZapRecordTimer(self):
		self.doInstantTimer(0, 1)

	def doInstantTimer(self, zap, zaprecord):
		cur = self[f"list{self.activeList}"].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		newEntry = RecordTimerEntry(serviceref, checkOldTimers=True, dirname=preferredTimerPath(), *parseEvent(event, isZapTimer=zap), justplay=zap)
		self.InstantRecordDialog = self.session.instantiateDialog(InstantRecordTimerEntry, newEntry, zap, zaprecord)
		retval = [True, self.InstantRecordDialog.retval()]
		self.session.deleteDialogWithCallback(self.finishedAdd, self.InstantRecordDialog, retval)

	def finishedAdd(self, answer):
		if isinstance(answer, bool) and answer:  # Special case for close recursive.
			self.close(True)
			return
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
			self.setTimerButtonText(_("Change Timer"))
			self.key_green_choice = self.REMOVE_TIMER
		else:
			self.setTimerButtonText(_("Add Timer"))
			self.key_green_choice = self.ADD_TIMER
		self.refreshlist()

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def OK(self):
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			if self.zapnumberstarted:
				self.dozumberzap()
			else:
				if self.type == EPG_TYPE_VERTICAL and "Channel" in config.epgselection.vertical_ok.value:
					self.infoKeyPressed()
				elif ((self.type == EPG_TYPE_GRAPH and config.epgselection.graph_ok.value == "Zap") or (self.type == EPG_TYPE_ENHANCED and config.epgselection.enhanced_ok.value == "Zap") or
				((self.type == EPG_TYPE_INFOBAR or self.type == EPG_TYPE_INFOBARGRAPH) and config.epgselection.infobar_ok.value == "Zap") or
				(self.type == EPG_TYPE_MULTI and config.epgselection.multi_ok.value == "Zap") or (self.type == EPG_TYPE_VERTICAL and config.epgselection.vertical_ok.value == "Zap")):
					self.zapTo()
				elif ((self.type == EPG_TYPE_GRAPH and config.epgselection.graph_ok.value == "Zap + Exit") or (self.type == EPG_TYPE_ENHANCED and config.epgselection.enhanced_ok.value == "Zap + Exit") or
				((self.type == EPG_TYPE_INFOBAR or self.type == EPG_TYPE_INFOBARGRAPH) and config.epgselection.infobar_ok.value == "Zap + Exit") or
				(self.type == EPG_TYPE_MULTI and config.epgselection.multi_ok.value == "Zap + Exit") or (self.type == EPG_TYPE_VERTICAL and config.epgselection.vertical_ok.value == "Zap + Exit")):
					self.zap()

	def OKLong(self):
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance.LongButtonPressed:
			if self.zapnumberstarted:
				self.dozumberzap()
			else:
				if self.type == EPG_TYPE_VERTICAL and "Channel" in config.epgselection.vertical_oklong.value:
					self.infoKeyPressed()
				elif ((self.type == EPG_TYPE_GRAPH and config.epgselection.graph_oklong.value == "Zap") or (self.type == EPG_TYPE_ENHANCED and config.epgselection.enhanced_oklong.value == "Zap") or
				((self.type == EPG_TYPE_INFOBAR or self.type == EPG_TYPE_INFOBARGRAPH) and config.epgselection.infobar_oklong.value == "Zap") or
				(self.type == EPG_TYPE_MULTI and config.epgselection.multi_oklong.value == "Zap") or (self.type == EPG_TYPE_VERTICAL and config.epgselection.vertical_oklong.value == "Zap")):
					self.zapTo()
				elif ((self.type == EPG_TYPE_GRAPH and config.epgselection.graph_oklong.value == "Zap + Exit") or (self.type == EPG_TYPE_ENHANCED and config.epgselection.enhanced_oklong.value == "Zap + Exit") or
				((self.type == EPG_TYPE_INFOBAR or self.type == EPG_TYPE_INFOBARGRAPH) and config.epgselection.infobar_oklong.value == "Zap + Exit") or
				(self.type == EPG_TYPE_MULTI and config.epgselection.multi_oklong.value == "Zap + Exit") or (self.type == EPG_TYPE_VERTICAL and config.epgselection.vertical_oklong.value == "Zap + Exit")):
					self.zap()

	def epgButtonPressed(self):
		self.OpenSingleEPG()

	def Info(self):
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			if (self.type == EPG_TYPE_GRAPH and config.epgselection.graph_info.value == "Channel Info") or (self.type == EPG_TYPE_VERTICAL and config.epgselection.vertical_info.value == "Channel Info"):
				self.infoKeyPressed()
			elif (self.type == EPG_TYPE_GRAPH and config.epgselection.graph_info.value == "Single EPG") or (self.type == EPG_TYPE_VERTICAL and config.epgselection.vertical_info.value == "Single EPG"):
				self.OpenSingleEPG()
			else:
				self.infoKeyPressed()

	def InfoLong(self):
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance.LongButtonPressed:
			if (self.type == EPG_TYPE_GRAPH and config.epgselection.graph_infolong.value == "Channel Info") or (self.type == EPG_TYPE_VERTICAL and config.epgselection.vertical_infolong.value == "Channel Info"):
				self.infoKeyPressed()
			elif (self.type == EPG_TYPE_GRAPH and config.epgselection.graph_infolong.value == "Single EPG") or (self.type == EPG_TYPE_VERTICAL and config.epgselection.vertical_infolong.value == "Single EPG"):
				self.OpenSingleEPG()
			else:
				self.OpenSingleEPG()

	def applyButtonState(self, state):
		if state == 0:
			self["now_button"].hide()
			self["now_button_sel"].hide()
			self["next_button"].hide()
			self["next_button_sel"].hide()
			self["more_button"].hide()
			self["more_button_sel"].hide()
			self["now_text"].hide()
			self["next_text"].hide()
			self["more_text"].hide()
			self["key_red"].setText("")
		else:
			if state == 1:
				self["now_button_sel"].show()
				self["now_button"].hide()
			else:
				self["now_button"].show()
				self["now_button_sel"].hide()
			if state == 2:
				self["next_button_sel"].show()
				self["next_button"].hide()
			else:
				self["next_button"].show()
				self["next_button_sel"].hide()
			if state == 3:
				self["more_button_sel"].show()
				self["more_button"].hide()
			else:
				self["more_button"].show()
				self["more_button_sel"].hide()

	def getRecordEvent(self, serviceRefStr, event):
		recordEvent = None
		eventID = event.getEventId()
		for timer in [x for x in self.session.nav.RecordTimer.timer_list + self.session.nav.RecordTimer.processed_timers if x.eit == eventID]:
			if timer.service_ref.ref.toCompareString() == serviceRefStr:
				recordEvent = timer
				break
		else:
			if self.session.nav.isRecordTimerImageStandard:
				isInTimer = self.session.nav.RecordTimer.isInTimer(eventID, event.getBeginTime(), event.getDuration(), serviceRefStr, True)
				if isInTimer and isInTimer[1] in (2, 7, 12):
					recordEvent = isInTimer[3]
		return recordEvent

	def onSelectionChanged(self):
		if self.type != EPG_TYPE_VERTICAL:
			self.activeList = ""
		cur = self[f"list{self.activeList}"].getCurrent()
		event = cur[0]
		self["Event"].newEvent(event)
		if cur[1] is None:
			self["Service"].newService(None)
		else:
			self["Service"].newService(cur[1].ref)
		if self.type == EPG_TYPE_MULTI:
			count = self["list"].getCurrentChangeCount()
			if self.ask_time != -1:
				self.applyButtonState(0)
			elif count > 1:
				self.applyButtonState(3)
			elif count > 0:
				self.applyButtonState(2)
			else:
				self.applyButtonState(1)
			datestr = ""
			if event is not None:
				now = time()
				beg = event.getBeginTime()
				nowTime = localtime(now)
				begTime = localtime(beg)
				if nowTime[2] != begTime[2]:
					datestr = strftime(config.usage.date.dayshort.value, begTime)
				else:
					datestr = _("Today")
			self["date"].setText(datestr)
		if cur[1] is None or cur[1].getServiceName() == "":
			if self.key_green_choice != self.EMPTY:
				self.setTimerButtonText("")
				self.key_green_choice = self.EMPTY
			return
		if event is None:
			if self.key_green_choice != self.EMPTY:
				self.setTimerButtonText("")
				self.key_green_choice = self.EMPTY
			return
		serviceref = cur[1]
		serviceRefStr = serviceref.ref.toCompareString()
		isRecordEvent = self.getRecordEvent(serviceRefStr, event)
		if isRecordEvent and self.key_green_choice != self.REMOVE_TIMER:
			self.setTimerButtonText(_("Change Timer"))
			self.key_green_choice = self.REMOVE_TIMER
		elif not isRecordEvent and self.key_green_choice != self.ADD_TIMER:
			self.setTimerButtonText(_("Add Timer"))
			self.key_green_choice = self.ADD_TIMER
		if self.eventviewDialog and (self.type == EPG_TYPE_INFOBAR or self.type == EPG_TYPE_INFOBARGRAPH):
			self.infoKeyPressed(True)
		if callable(self.catchupPlayerFunc):
			self.setupKeyPlayButtonDisplay(event.getBeginTime(), serviceref)

	def moveTimeLines(self, force=False):
		self.updateTimelineTimer.start((60 - int(time()) % 60) * 1000)
		self["timeline_text"].setEntries(self["list"], self["timeline_now"], self.time_lines, force)
		self["list"].l.invalidate()

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

	def closeScreen(self, NOCLOSE=False):
		if self.type == EPG_TYPE_SINGLE:
			self.close()
			return  # Stop and do not continue.
		if hasattr(self, "servicelist") and self.servicelist:
			selected_ref = str(ServiceReference(self.servicelist.getCurrentSelection()))
			current_ref = str(ServiceReference(self.session.nav.getCurrentlyPlayingServiceOrGroup()))
			if selected_ref != current_ref:
				self.servicelist.restoreRoot()
				self.servicelist.setCurrentSelection(self.session.nav.getCurrentlyPlayingServiceOrGroup())
		if self.session.nav.getCurrentlyPlayingServiceOrGroup() and self.StartRef and self.session.nav.getCurrentlyPlayingServiceOrGroup().toString() != self.StartRef.toString():
			if self.zapFunc and self.StartRef and self.StartBouquet:
				if ((self.type == EPG_TYPE_GRAPH and config.epgselection.graph_preview_mode.value) or
					(self.type == EPG_TYPE_MULTI and config.epgselection.multi_preview_mode.value) or
					(self.type in (EPG_TYPE_INFOBAR, EPG_TYPE_INFOBARGRAPH) and config.epgselection.infobar_preview_mode.value in ("1", "2")) or
					(self.type == EPG_TYPE_ENHANCED and config.epgselection.enhanced_preview_mode.value) or
					(self.type == EPG_TYPE_VERTICAL and config.epgselection.vertical_preview_mode.value)):
					if "0:0:0:0:0:0:0:0:0" not in self.StartRef.toString():
						self.zapFunc(None, zapback=True)
				elif "0:0:0:0:0:0:0:0:0" in self.StartRef.toString():
					self.session.nav.playService(self.StartRef)
				else:
					self.zapFunc(None, False)
		self.closeEventViewDialog()
		if self.type == EPG_TYPE_VERTICAL and NOCLOSE:
			return
		self.close(True)

	def restorePiP(self):
		if self.session.pipshown:
			self.Oldpipshown = False
			self.session.pipshown = False
			del self.session.pip
		if self.Oldpipshown:
			self.session.pipshown = True

	def zap(self):
		if self.session.nav.getCurrentlyPlayingServiceOrGroup() and "0:0:0:0:0:0:0:0:0" in self.session.nav.getCurrentlyPlayingServiceOrGroup().toString():
			return
		if self.zapFunc:
			self.zapSelectedService()
			self.closeEventViewDialog()
			self.close(True)
		else:
			self.closeEventViewDialog()
			self.close()

	def zapSelectedService(self, prev=False):
		currservice = self.session.nav.getCurrentlyPlayingServiceReference() and str(self.session.nav.getCurrentlyPlayingServiceReference().toString()) or None
		if self.session.pipshown:
			self.prevch = self.session.pip.getCurrentService() and str(self.session.pip.getCurrentService().toString()) or None
		else:
			self.prevch = self.session.nav.getCurrentlyPlayingServiceReference() and str(self.session.nav.getCurrentlyPlayingServiceReference().toString()) or None
		lst = self[f"list{self.activeList}"]
		count = lst.getCurrentChangeCount()
		if count == 0:
			ref = lst.getCurrent()[1]
			if ref is None and self.type == EPG_TYPE_VERTICAL and self.myServices[0][0]:
				ref = ServiceReference(self.myServices[self["list"].getSelectionIndex() + self.activeList - 1][0])
			if ref is not None:
				if (self.type == EPG_TYPE_INFOBAR or self.type == EPG_TYPE_INFOBARGRAPH) and config.epgselection.infobar_preview_mode.value == "2":
					if not prev:
						if self.session.pipshown:
							self.session.pipshown = False
							del self.session.pip
						self.zapFunc(ref.ref, bouquet=self.getCurrentBouquet(), preview=False)
						return
					if not self.session.pipshown:
						self.session.pip = self.session.instantiateDialog(PictureInPicture)
						self.session.pip.show()
						self.session.pipshown = True
					n_service = self.pipServiceRelation.get(str(ref.ref), None)
					if n_service is not None:
						service = eServiceReference(n_service)
					else:
						service = ref.ref
					if self.currch == service.toString():
						if self.session.pipshown:
							self.session.pipshown = False
							del self.session.pip
						self.zapFunc(ref.ref, bouquet=self.getCurrentBouquet(), preview=False)
						return
					if self.prevch != service.toString() and currservice != service.toString():
						self.session.pip.playService(service)
						self.currch = self.session.pip.getCurrentService() and str(self.session.pip.getCurrentService().toString())
				else:
					self.zapFunc(ref.ref, bouquet=self.getCurrentBouquet(), preview=prev)
					self.currch = self.session.nav.getCurrentlyPlayingServiceReference() and str(self.session.nav.getCurrentlyPlayingServiceReference().toString())
				self[f"list{self.activeList}"].setCurrentlyPlaying(self.session.nav.getCurrentlyPlayingServiceOrGroup())

	def zapTo(self):
		if self.session.nav.getCurrentlyPlayingServiceOrGroup() and "0:0:0:0:0:0:0:0:0" in self.session.nav.getCurrentlyPlayingServiceOrGroup().toString():
			# from Screens.InfoBarGenerics import setResumePoint
			# setResumePoint(self.session)
			return
		if self.zapFunc:
			self.zapSelectedService(True)
			self.refreshTimer.start(2000)
		if not self.currch or self.currch == self.prevch:
			if self.zapFunc:
				self.zapFunc(None, False)
				self.closeEventViewDialog()
				self.close("close")
			else:
				self.closeEventViewDialog()
				self.close()

	def keyNumberGlobal(self, number):
		if self.createTimer.isActive():
			return
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			if self.type == EPG_TYPE_GRAPH:
				now = time() - int(config.epgselection.graph_histminutes.value) * 60
				prevtimeperiod = config.epgselection.graph_prevtimeperiod
				roundto = config.epgselection.graph_roundto
				primetimehour = config.epgselection.graph_primetimehour
				primetimemins = config.epgselection.graph_primetimemins
			else:
				now = time() - int(config.epgselection.infobar_histminutes.value) * 60
				prevtimeperiod = config.epgselection.infobar_prevtimeperiod
				roundto = config.epgselection.infobar_roundto
				primetimehour = config.epgselection.infobar_primetimehour
				primetimemins = config.epgselection.infobar_primetimemins
			if number == 1:
				timeperiod = int(prevtimeperiod.value)
				if timeperiod > 60:
					timeperiod -= 60
					self["list"].setEpoch(timeperiod)
					prevtimeperiod.setValue(timeperiod)
					self.moveTimeLines()
			elif number == 2:
				self.prevPage()
			elif number == 3:
				timeperiod = int(prevtimeperiod.value)
				if timeperiod < 300:
					timeperiod += 60
					self["list"].setEpoch(timeperiod)
					prevtimeperiod.setValue(timeperiod)
					self.moveTimeLines()
			elif number == 4:
				self.updEvent(-2)
			elif number == 5:
				self.ask_time = now - now % (int(roundto.value) * 60)
				self["list"].resetOffset()
				self["list"].fillGraphEPG(None, self.ask_time, True)
				self.moveTimeLines(True)
			elif number == 6:
				self.updEvent(+2)
			elif number == 7 and self.type == EPG_TYPE_GRAPH:
				if config.epgselection.graph_heightswitch.value:
					config.epgselection.graph_heightswitch.setValue(False)
				else:
					config.epgselection.graph_heightswitch.setValue(True)
				self["list"].setItemsPerPage()
				self["list"].fillGraphEPG(None)
				self.moveTimeLines()
			elif number == 8:
				self.nextPage()
			elif number == 9:
				basetime = localtime(self["list"].getTimeBase())
				basetime = (basetime[0], basetime[1], basetime[2], int(primetimehour.value), int(primetimemins.value), 0, basetime[6], basetime[7], basetime[8])
				self.ask_time = mktime(basetime)
				if self.ask_time + 3600 < time():
					self.ask_time += 86400
				self["list"].resetOffset()
				self["list"].fillGraphEPG(None, self.ask_time)
				self.moveTimeLines(True)
			elif number == 0:
				self.toTop()
				self.ask_time = now - now % (int(roundto.value) * 60)
				self["list"].resetOffset()
				self["list"].fillGraphEPG(None, self.ask_time, True)
				self.moveTimeLines()
		elif self.type == EPG_TYPE_VERTICAL:
			if number == 1:
				self.gotoFirst()
			elif number == 2:
				self.allUp()
			elif number == 3:
				self.gotoLast()
			elif number == 4:
				self.prevPage(True)
			elif number == 0:
				if self.zapFunc:
					self.closeScreen(True)
				self.onCreate()
			elif number == 6:
				self.nextPage(True)
			elif number == 7:
				self.gotoNow()
			elif number == 8:
				self.allDown()
			elif number == 9:
				self.gotoPrimetime()
			elif number == 5:
				self.setBasetime()
		else:
			self.zapnumberstarted = True
			self.NumberZapTimer.start(5000, True)
			if not self.NumberZapField:
				self.NumberZapField = f"{number}"
			else:
				self.NumberZapField = f"{self.NumberZapField}{number}"
			self.handleServiceName()
			self["number"].setText(f"{self.zaptoservicename}\n{self.NumberZapField}")
			self["number"].show()
			if len(self.NumberZapField) >= 4:
				self.dozumberzap()

	def dozumberzap(self):
		self.zapnumberstarted = False
		self.numberEntered(self.service, self.bouquet)

	def handleServiceName(self):
		if self.searchNumber:
			self.service, self.bouquet = self.searchNumber(int(self.NumberZapField))
			self.zaptoservicename = ServiceReference(self.service).getServiceName()

	def numberEntered(self, service=None, bouquet=None):
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
		if config.usage.multibouquet.value:
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
							if config.usage.alternative_number_mode.value:
								break
						bouquet = bouquetlist.getNext()
		return service, bouquet

	def zapToNumber(self, service, bouquet):
		self["number"].hide()
		self.NumberZapField = None
		self.CurrBouquet = bouquet
		self.CurrService = service
		if service is not None:
			self.setServicelistSelection(bouquet, service)
		self.onCreate()

	def RefreshColouredKeys(self):
		buttonOptions = {
			"24plus": _("+24 Hours"),
			"24minus": _("-24 Hours"),
			"timer": _("Add Timer"),
			"imdb": _("IMDb Search"),
			"tmdb": _("TMDB Search"),
			"autotimer": _("Add AutoTimer"),
			"bouquetlist": _("Bouquet List"),
			"epgsearch": _("EPG Search"),
			"showmovies": _("Recordings"),
			"record": _("Record"),
			"gotodatetime": _("Goto Date/Time"),
			"nextpage": _("Next Page"),
			"prevpage": _("Previous Page"),
			"nextbouquet": _("Next Bouquet"),
			"prevbouquet": _("Previous Bouquet"),
			"gotoprimetime": _("Goto Prime Time"),
			"setbasetime": _("Set Base Time")
		}
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			self["key_red"] = StaticText(buttonOptions.get(config.epgselection.graph_red.value, "imdb"))
			self["key_green"] = StaticText(buttonOptions.get(config.epgselection.graph_green.value, "timer"))
			self["key_yellow"] = StaticText(buttonOptions.get(config.epgselection.graph_yellow.value, "epgsearch"))
			self["key_blue"] = StaticText(buttonOptions.get(config.epgselection.graph_blue.value, "autotimer"))
		elif self.type == EPG_TYPE_VERTICAL:
			self["key_red"] = StaticText(buttonOptions.get(config.epgselection.vertical_red.value, "imdb"))
			self["key_green"] = StaticText(buttonOptions.get(config.epgselection.vertical_green.value, "timer"))
			self["key_yellow"] = StaticText(buttonOptions.get(config.epgselection.vertical_yellow.value, "epgsearch"))
			self["key_blue"] = StaticText(buttonOptions.get(config.epgselection.vertical_blue.value, "autotimer"))

	def setTimerButtonText(self, text=None):
		if text is None:
			text = _("Add Timer")
		if self.type == EPG_TYPE_GRAPH or self.type == EPG_TYPE_INFOBARGRAPH:
			if config.epgselection.graph_red.value == "timer":
				self["key_red"].setText(text)
			if config.epgselection.graph_green.value == "timer":
				self["key_green"].setText(text)
			if config.epgselection.graph_yellow.value == "timer":
				self["key_yellow"].setText(text)
			if config.epgselection.graph_blue.value == "timer":
				self["key_blue"].setText(text)
		elif self.type == EPG_TYPE_VERTICAL:
			if config.epgselection.vertical_red.value == "timer":
				self["key_red"].setText(text)
			if config.epgselection.vertical_green.value == "timer":
				self["key_green"].setText(text)
			if config.epgselection.vertical_yellow.value == "timer":
				self["key_yellow"].setText(text)
			if config.epgselection.vertical_blue.value == "timer":
				self["key_blue"].setText(text)
		else:
			self["key_green"].setText(text)

	def getChannels(self):
		self.list = []
		self.myServices = []
		idx = 0
		for service in self.services:
			idx = idx + 1
			info = service.info()
			servicename = info.getName(service.ref).replace("\xc2\x86", "").replace("\xc2\x87", "")
			self.list.append(f"{idx}. {servicename}")
			self.myServices.append((service.ref.toString(), servicename))
		if not idx:
			self.list.append("")
			self.myServices.append(("", ""))
		return self.list

	def updateVerticalEPG(self, force=False):
		self.displayActiveEPG()
		stime = None
		now = time()
		if force or self.ask_time >= now - config.epg.histminutes.value * 60:
			stime = self.ask_time
		prgIndex = self["list"].getSelectionIndex()
		CurrentPrg = self.myServices[prgIndex]
		x = len(self.list) - 1
		if x >= 0 and CurrentPrg[0]:
			self["list1"].show()
			self["currCh1"].setText(str(CurrentPrg[1]))
			l = self["list1"]
			l.recalcEntrySize()
			myService = ServiceReference(CurrentPrg[0])
			self["piconCh1"].newService(myService.ref)
			l.fillSingleEPG(myService, stime)
		else:
			self["Active1"].hide()
			self["piconCh1"].newService(None)
			self["currCh1"].setText(" ")
			self["list1"].hide()
		prgIndex = prgIndex + 1
		if prgIndex < (x + 1):
			self["list2"].show()
			CurrentPrg = self.myServices[prgIndex]
			self["currCh2"].setText(str(CurrentPrg[1]))
			l = self["list2"]
			l.recalcEntrySize()
			myService = ServiceReference(CurrentPrg[0])
			self["piconCh2"].newService(myService.ref)
			l.fillSingleEPG(myService, stime)
		else:
			self["piconCh2"].newService(None)
			self["currCh2"].setText(" ")
			self["list2"].hide()
		prgIndex = prgIndex + 1
		if prgIndex < (x + 1):
			self["list3"].show()
			CurrentPrg = self.myServices[prgIndex]
			self["currCh3"].setText(str(CurrentPrg[1]))
			l = self["list3"]
			l.recalcEntrySize()
			myService = ServiceReference(CurrentPrg[0])
			self["piconCh3"].newService(myService.ref)
			l.fillSingleEPG(myService, stime)
		else:
			self["piconCh3"].newService(None)
			self["currCh3"].setText(" ")
			self["list3"].hide()
		if self.Fields == 6:
			prgIndex = prgIndex + 1
			if prgIndex < (x + 1):
				self["list4"].show()
				CurrentPrg = self.myServices[prgIndex]
				self["currCh4"].setText(str(CurrentPrg[1]))
				l = self["list4"]
				l.recalcEntrySize()
				myService = ServiceReference(CurrentPrg[0])
				self["piconCh4"].newService(myService.ref)
				l.fillSingleEPG(myService, stime)
			else:
				self["piconCh4"].newService(None)
				self["currCh4"].setText(" ")
				self["piconCh4"].newService(None)
				self["list4"].hide()
			prgIndex = prgIndex + 1
			if prgIndex < (x + 1):
				self["list5"].show()
				CurrentPrg = self.myServices[prgIndex]
				self["currCh5"].setText(str(CurrentPrg[1]))
				l = self["list5"]
				l.recalcEntrySize()
				myService = ServiceReference(CurrentPrg[0])
				self["piconCh5"].newService(myService.ref)
				l.fillSingleEPG(myService, stime)
			else:
				self["piconCh5"].newService(None)
				self["currCh5"].setText(" ")
				self["list5"].hide()
		else:
			self["currCh4"].setText(" ")
			self["list4"].hide()
			self["Active4"].hide()
			self["currCh5"].setText(" ")
			self["list5"].hide()
			self["Active5"].hide()

	def displayActiveEPG(self):
		marker = config.epgselection.vertical_eventmarker.value
		for _list in list(range(1, self.Fields)):
			if _list == self.activeList:
				self[f"list{_list}"].selectionEnabled(True)
				self[f"Active{_list}"].show()
			else:
				self[f"Active{_list}"].hide()
				self[f"list{_list}"].selectionEnabled(marker)

	def getActivePrg(self):
		return self["list"].getSelectionIndex() + (self.activeList - 1)

	def allUp(self):
		if self.getEventTime(self.activeList)[0] is None:
			return
		idx = self[f"list{self.activeList}"].getCurrentIndex()
		if not idx:
			tmp = self.lastEventTime
			self.setMinus24h(True, 6)
			self.lastEventTime = tmp
			self.gotoLasttime()
		for _list in list(range(1, self.Fields)):
			self[f"list{_list}"].moveTo(self[f"list{_list}"].instance.pageUp)
		self.syncUp(idx)
		self.saveLastEventTime()

	def syncUp(self, idx):
		idx = self[f"list{self.activeList}"].getCurrentIndex()
		curTime = self.getEventTime(self.activeList)[0]
		for _list in list(range(1, self.Fields)):
			if _list == self.activeList:
				continue
			for x in list(range(0, int(idx / config.epgselection.vertical_itemsperpage.value))):
				evTime = self.getEventTime(_list)[0]
				if curTime is None or evTime is None or curTime <= evTime:
					self[f"list{_list}"].moveTo(self[f"list{_list}"].instance.pageUp)
				evTime = self.getEventTime(_list)[0]
				if curTime is None or evTime is None or curTime >= evTime:
					break

	def syncDown(self, idx):
		curTime = self.getEventTime(self.activeList)[0]
		for _list in list(range(1, self.Fields)):
			if _list == self.activeList:
				continue
			for x in list(range(0, int(idx / config.epgselection.vertical_itemsperpage.value))):
				evTime = self.getEventTime(_list)[0]
				if curTime is None or evTime is None or curTime >= evTime:
					self[f"list{_list}"].moveTo(self[f"list{_list}"].instance.pageDown)
				evTime = self.getEventTime(_list)[0]
				if curTime is None or evTime is None or curTime <= evTime:
					break

	def allDown(self):
		if self.getEventTime(self.activeList)[0] is None:
			return
		for _list in list(range(1, self.Fields)):
			self[f"list{_list}"].moveTo(self[f"list{_list}"].instance.pageDown)
		idx = self[f"list{self.activeList}"].getCurrentIndex()
		self.syncDown(idx)
		self.saveLastEventTime()

	def gotoNow(self):
		self.ask_time = time()
		self.updateVerticalEPG()
		self.saveLastEventTime()

	def gotoFirst(self):
		self["list"].moveToIndex(0)
		self.activeList = 1
		self.updateVerticalEPG()

	def gotoLast(self):
		idx = len(self.list)
		page = idx // (self.Fields - 1)
		row = idx % (self.Fields - 1)
		if row:
			self.activeList = row
		else:
			page -= 1
			self.activeList = self.Fields - 1
		self["list"].moveToIndex(0)
		for i in list(range(0, page)):
			self["list"].pageDown()
		self.updateVerticalEPG()

	def setPrimetime(self, stime):
		if stime is None:
			stime = time()
		t = localtime(stime)
		primetime = mktime((t[0], t[1], t[2], config.epgselection.vertical_primetimehour.value, config.epgselection.vertical_primetimemins.value, 0, t[6], t[7], t[8]))
		return primetime

	def findMaxEventTime(self, stime):
		curr = self[f"list{self.activeList}"].getSelectedEventId()
		self[f"list{self.activeList}"].moveTo(self[f"list{self.activeList}"].instance.moveEnd)
		maxtime = self.getEventTime(self.activeList)[0]
		self[f"list{self.activeList}"].moveToEventId(curr)
		return maxtime is not None and maxtime >= stime

	def findMinEventTime(self, stime):
		curr = self[f"list{self.activeList}"].getSelectedEventId()
		self[f"list{self.activeList}"].moveTo(self[f"list{self.activeList}"].instance.moveTop)
		mintime = self.getEventTime(self.activeList)[0]
		self[f"list{self.activeList}"].moveToEventId(curr)
		return mintime is not None and mintime <= stime

	def isInTimeRange(self, stime):
		return self.findMaxEventTime(stime) and self.findMinEventTime(stime)

	def setPlus24h(self):
		oneDay = 24 * 3600
		ev_begin, ev_end = self.getEventTime(self.activeList)

		if ev_begin is not None:
			if self.findMaxEventTime(ev_begin + oneDay):
				primetime = self.setPrimetime(ev_begin)
				if primetime >= ev_begin and primetime < ev_end:
					self.ask_time = primetime + oneDay
				else:
					self.ask_time = ev_begin + oneDay
				self.updateVerticalEPG()
			else:
				self[f"list{self.activeList}"].moveTo(self[f"list{self.activeList}"].instance.moveEnd)
			self.saveLastEventTime()

	def setMinus24h(self, force=False, daypart=1):
		now = time()
		oneDay = 24 * 3600 // daypart
		if not self.lastMinus:
			self.lastMinus = oneDay
		ev_begin, ev_end = self.getEventTime(self.activeList)
		if ev_begin is not None:
			if ev_begin - oneDay < now:
				self.ask_time = -1
			else:
				if self[f"list{self.activeList}"].getCurrentIndex() and not force and self.findMinEventTime(ev_begin - oneDay):
					self.lastEventTime = ev_begin - oneDay, ev_end - oneDay
					self.gotoLasttime()
					return
				else:
					pt = 0
					if self.ask_time == ev_begin - self.lastMinus:
						self.lastMinus += self.lastMinus
					else:
						primetime = self.setPrimetime(ev_begin)
						if primetime >= ev_begin and primetime < ev_end:
							self.ask_time = pt = primetime - oneDay
						self.lastMinus = oneDay
					if not pt:
						self.ask_time = ev_begin - self.lastMinus
			self.updateVerticalEPG()
			self.saveLastEventTime()

	def setBasetime(self):
		ev_begin, ev_end = self.getEventTime(self.activeList)
		if ev_begin is not None:
			self.ask_time = ev_begin
			self.updateVerticalEPG()

	def gotoPrimetime(self):
		idx = 0
		now = time()
		oneDay = 24 * 3600
		if self.firststart:
			self.ask_time = self.setPrimetime(now)
			self[f"list{self.activeList}"].moveTo(self[f"list{self.activeList}"].instance.moveTop)
			ev_begin = self.getEventTime(self.activeList)[0]
			if ev_begin is not None and ev_begin > self.ask_time:
				self.ask_time += oneDay
			self.updateVerticalEPG()
			self.saveLastEventTime()
			return
		ev_begin, ev_end = self.getEventTime(self.activeList)
		if ev_begin is None:
			return
		for _list in list(range(1, self.Fields)):
			idx += self[f"list{_list}"].getCurrentIndex()
		primetime = self.setPrimetime(ev_begin)
		onlyPT = False  # Key press prime-time always sync.
		gotoNow = False  # False -> -24h List expanded, True -> got to current event and sync. (onlyPT must set to False!)
		rPM = self.isInTimeRange(primetime - oneDay)
		rPT = self.isInTimeRange(primetime)
		rPP = self.isInTimeRange(primetime + oneDay)
		if rPM or rPT or rPP:
			if onlyPT or idx or not (primetime >= ev_begin and primetime < ev_end):  # Not sync or not prime-time.
				if rPT:
					self.ask_time = primetime
				elif rPP:
					self.ask_time = primetime + oneDay
				elif rPM:
					self.ask_time = primetime - oneDay
				self.updateVerticalEPG(True)
			else:
				if gotoNow:
					self.gotoNow()
					return
				else:
					self[f"list{self.activeList}"].moveTo(self[f"list{self.activeList}"].instance.moveTop)
					self.setMinus24h(True, 6)
					for _list in list(range(1, self.Fields)):
						self[f"list{_list}"].moveTo(self[f"list{_list}"].instance.moveEnd)
						cnt = self[f"list{_list}"].getCurrentIndex()
						self[f"list{_list}"].moveTo(self[f"list{_list}"].instance.moveTop)
						self.findPrimetime(cnt, _list, primetime)
			self.saveLastEventTime()

	def gotoLasttime(self, _list=0):
		if _list:
			self[f"list{_list}"].moveTo(self[f"list{_list}"].instance.moveEnd)
			cnt = self[f"list{_list}"].getCurrentIndex()
			self[f"list{_list}"].moveTo(self[f"list{_list}"].instance.moveTop)
			self.findLasttime(cnt, _list)
		else:
			for _list in list(range(1, self.Fields)):
				self[f"list{_list}"].moveTo(self[f"list{_list}"].instance.moveEnd)
				cnt = self[f"list{_list}"].getCurrentIndex()
				self[f"list{_list}"].moveTo(self[f"list{_list}"].instance.moveTop)
				self.findLasttime(cnt, _list)

	def findLasttime(self, cnt, _list, idx=0):
		last_begin, last_end = self.lastEventTime
		for events in list(range(0, idx)):
			self[f"list{_list}"].moveTo(self[f"list{_list}"].instance.moveDown)
		for events in list(range(idx, cnt)):
			ev_begin, ev_end = self.getEventTime(_list)
			if ev_begin is not None:
				if (ev_begin <= last_begin and ev_end > last_begin) or (ev_end >= last_end):
					break
				self[f"list{_list}"].moveTo(self[f"list{_list}"].instance.moveDown)
			else:
				break

	def findPrimetime(self, cnt, _list, primetime):
		for events in list(range(0, cnt)):
			ev_begin, ev_end = self.getEventTime(_list)
			if ev_begin is not None:
				if (primetime >= ev_begin and primetime < ev_end):
					break
				self[f"list{_list}"].moveTo(self[f"list{_list}"].instance.moveDown)
			else:
				break

	def saveLastEventTime(self, _list=0):
		if not _list:
			_list = self.activeList
		now = time()
		last = self.lastEventTime
		self.lastEventTime = self.getEventTime(_list)
		if self.lastEventTime[0] is None and last[0] is not None:
			self.lastEventTime = last
		elif last[0] is None:
			self.lastEventTime = (now, now + 3600)

	def getEventTime(self, _list):
		tmp = self[f"list{_list}"].l.getCurrentSelection()
		if tmp is None:
			return None, None
		return tmp[2], tmp[2] + tmp[3]  # Event begin, event end.


class SingleEPG(EPGSelection):
	def __init__(self, session, service, EPGtype="single"):
		EPGSelection.__init__(self, session, service=service, EPGtype=EPGtype)
		self.skinName = "EPGSelection"
