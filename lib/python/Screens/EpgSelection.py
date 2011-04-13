from Screen import Screen
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Components.Button import Button
from Components.config import config, ConfigClock, NoSave, ConfigSelection, getConfigListEntry, ConfigText, ConfigDateTime, ConfigSubList, ConfigYesNo
from Components.ConfigList import ConfigListScreen
from Components.EpgList import EPGList, EPG_TYPE_SINGLE, EPG_TYPE_SIMILAR, EPG_TYPE_MULTI, EPG_TYPE_ENHANCED, EPG_TYPE_INFOBAR
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.Event import Event
from Components.SystemInfo import SystemInfo
from Components.TimerSanityCheck import TimerSanityCheck
from Components.UsageConfig import preferredTimerPath, defaultMoviePath
from Screens.MovieSelection import getPreferredTagEditor
from Screens.TimerEdit import TimerSanityConflict
from Screens.EventView import EventViewSimple
from Screens.MessageBox import MessageBox
from Tools.Directories import pathExists, resolveFilename, SCOPE_CURRENT_SKIN, SCOPE_LANGUAGE, SCOPE_PLUGINS
from Tools.LoadPixmap import LoadPixmap
from TimeDateInput import TimeDateInput
from enigma import eServiceReference, getDesktop, eEPGCache, eTimer, eServiceCenter
from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT
from TimerEntry import TimerEntry
from ServiceReference import ServiceReference
from time import time, strftime, localtime, mktime
from datetime import datetime

mepg_config_initialized = False

config.misc.EPGSort = ConfigSelection(default="Time", choices = [
				("Time", _("Time")),
				("AZ", _("Alphanumeric"))
				])

class EPGSelection(Screen):
	sz_w = getDesktop(0).size().width()
	if sz_w == 1280:
		skin = """
			<screen name="QuickEPG" position="0,505" size="1280,215" title="QuickEPG" backgroundColor="transparent" flags="wfNoBorder">
				<ePixmap alphatest="off" pixmap="/usr/lib/enigma2/python/Plugins/VIX/VIXMainMenu/hd.png" position="0,0" size="1280,220" zPosition="0"/>
				<widget source="Service" render="Picon" position="60,75" size="100,60" transparent="1" zPosition="2" alphatest="blend">
					<convert type="ChannelSelectionExtraInfo">Reference</convert>
				</widget>
				<widget source="Service" render="Label" position="0,42" size="1280,36" font="Regular;26" valign="top" halign="center" noWrap="1" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" zPosition="2" >
					<convert type="ServiceName">Name</convert>
				</widget>
				<widget name="list" position="340,80" size="640,54" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" itemHeight="27" zPosition="2"/>
				<ePixmap pixmap="ViX_HD/buttons/red.png" position="260,160" size="25,25" alphatest="blend" />
				<widget name="key_red" position="300,164" zPosition="1" size="130,20" font="Regular; 20" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" />
				<ePixmap pixmap="ViX_HD/buttons/green.png" position="450,160" size="25,25" alphatest="blend" />
				<widget name="key_green" position="490,164" zPosition="1" size="130,20" font="Regular; 20" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" />
				<ePixmap pixmap="ViX_HD/buttons/yellow.png" position="640,160" size="25,25" alphatest="blend" />
				<widget name="key_yellow" position="680,164" zPosition="1" size="130,20" font="Regular; 20" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" />
				<ePixmap pixmap="ViX_HD/buttons/blue.png" position="830,160" size="25,25" alphatest="blend" />
				<widget name="key_blue" position="870,164" zPosition="1" size="150,20" font="Regular; 20" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" />
			</screen>"""
	else:
		skin = """
			<screen name="QuickEPG" position="0,325" size="720,276" title="QuickEPG" backgroundColor="transparent" flags="wfNoBorder" >
				<ePixmap alphatest="off" pixmap="Magic/infobar/infobar.png" position="0,0" size="720,156" zPosition="1"/>
				<eLabel backgroundColor="#41080808" position="0,156" size="720,110" zPosition="2"/>
				<widget borderColor="#0f0f0f" borderWidth="1" backgroundColor="#16000000" font="Enigma;24" foregroundColor="#00f0f0f0" halign="left" noWrap="1" position="88,120" render="Label" size="68,28" source="global.CurrentTime" transparent="1" zPosition="3">
					<convert type="ClockToText">Default</convert>
				</widget>		
				<widget borderColor="#0f0f0f" borderWidth="1" backgroundColor="#16000000" font="Enigma;16" noWrap="1" position="54,100" render="Label" size="220,22" source="global.CurrentTime" transparent="1" valign="bottom" zPosition="3">
					<convert type="ClockToText">Date</convert>
				</widget>
				<widget source="Service" render="Picon" position="50,150" size="100,60" transparent="1" zPosition="4" alphatest="blend">
					<convert type="ChannelSelectionExtraInfo">Reference</convert>
				</widget>
				<widget source="Service" render="Label" borderColor="#0f0f0f" borderWidth="1" backgroundColor="#16000000" font="Enigma;24" foregroundColor="#00f0f0f0" halign="center" position="160,120" size="400,28" transparent="1" valign="bottom" zPosition="3" >
					<convert type="ServiceName">Name</convert>
				</widget>
				<widget name="list" position="160,160" size="500,45" backgroundColor="#41080808" foregroundColor="#cccccc" transparent="1" itemHeight="22" zPosition="4"/>
				<ePixmap pixmap="ViX_HD/buttons/red.png" position="80,210" size="25,25" alphatest="blend" zPosition="4" />
				<widget name="key_red" position="110,213" size="100,20" font="Regular; 17" halign="left" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" zPosition="4" />
				<ePixmap pixmap="ViX_HD/buttons/green.png" position="210,210" size="25,25" alphatest="blend" zPosition="4" />
				<widget name="key_green" position="240,213" size="100,20" font="Regular; 17" halign="left" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" zPosition="4" />
				<ePixmap pixmap="ViX_HD/buttons/yellow.png" position="340,210" size="25,25" alphatest="blend" zPosition="4" />
				<widget name="key_yellow" position="370,213" size="100,20" font="Regular; 17" halign="left" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" zPosition="4" />
				<ePixmap pixmap="ViX_HD/buttons/blue.png" position="470,210" size="25,25" alphatest="blend" zPosition="4" />
				<widget name="key_blue" position="500,213" size="150,20" font="Regular; 17" halign="left" backgroundColor="#101214" foregroundColor="#cccccc" transparent="1" zPosition="4" />
			</screen>"""

	EMPTY = 0
	ADD_TIMER = 1
	REMOVE_TIMER = 2
	
	ZAP = 1

	def __init__(self, session, service, zapFunc=None, eventid=None, bouquetChangeCB=None, serviceChangeCB=None, EPGtype=False):
		Screen.__init__(self, session)
		print 'EPGtype',EPGtype
		self.bouquetChangeCB = bouquetChangeCB
		self.serviceChangeCB = serviceChangeCB
		self.ask_time = -1 #now
		self.closeRecursive = False
		self.saved_title = None
		self["Service"] = ServiceEvent()
		self["Event"] = Event()
		if isinstance(service, str) and eventid != None:
			self.type = EPG_TYPE_SIMILAR
			self["key_yellow"] = Button()
			self["key_blue"] = Button()
			self["key_red"] = Button()
			self.currentService=service
			self.eventid = eventid
			self.zapFunc = None
		elif isinstance(service, list):
			if EPGtype == "graph":
				self.type = EPG_TYPE_MULTI
				self["key_yellow"] = Button(_("Prev"))
				self["key_blue"] = Button(_("Next"))
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
				self.services = service
				self.zapFunc = zapFunc
			else:
				self.skinName = "EPGSelectionMulti"
				self.type = EPG_TYPE_MULTI
				self["key_yellow"] = Button(_("Prev"))
				self["key_blue"] = Button(_("Next"))
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
				self.services = service
				self.zapFunc = zapFunc

		elif isinstance(service, eServiceReference) or isinstance(service, str):
			self.type = EPG_TYPE_SINGLE
			self.currentService=ServiceReference(service)
			self.zapFunc = None
		else:
			if EPGtype:
				self.type = EPG_TYPE_INFOBAR
				self.skinName = "QuickEPG"
			else:
				self.type = EPG_TYPE_ENHANCED
			self.list = []
			self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
			self.currentService=self.session.nav.getCurrentlyPlayingServiceReference()
			self.zapFunc = None

		self["key_red"] = Button(_("IMDb Search"))
		self["key_yellow"] = Button(_("EPG Search"))
		self["key_blue"] = Button(_("Add AutoTimer"))
		self["key_green"] = Button(_("Add timer"))
		self.key_green_choice = self.ADD_TIMER
		self.key_red_choice = self.EMPTY
		self["list"] = EPGList(type = self.type, selChangedCB = self.onSelectionChanged, timer = session.nav.RecordTimer)

		if self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			self["actions"] = ActionMap(["OkCancelActions", "InfobarInstantRecord", "EPGSelectActions", "ChannelSelectBaseActions", "ColorActions", "DirectionActions", "MenuActions", "HelpActions"], 
			{
				"ok": self.ZapTo, 
				"cancel": self.closing,
				"nextBouquet": self.nextBouquet,
				"prevBouquet": self.prevBouquet,
				"nextService": self.nextService,
				"prevService": self.prevService,
	#			"prevBouquet": self.openServiceList,
				"red": self.redButtonPressed,
				"timerAdd": self.timerAdd,
				"yellow": self.yellowButtonPressed,
				"blue": self.blueButtonPressed,
				"info": self.infoKeyPressed,
				"instantRecord": self.Record,
				},-2)
			self["actions2"] = NumberActionMap(["NumberActions"],
			{
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal,
			}, -1)
			self["MenuActions"] = HelpableActionMap(self, "MenuActions",
				{
					"menu": (self.createSetup, _("Open Context Menu"))
				}
			)
			self.onLayoutFinish.append(self.onCreate)
			self.servicelist = service
			self.servicelist_orig_zap = self.servicelist.zap 
			self.servicelist.zap = self.servicelist_overwrite_zap
			self.servicelist["actions"] = ActionMap(["OkCancelActions"],
				{
					"cancel": self.cancelChannelSelection,
					"ok": self.servicelist.channelSelected,
				})
			# temp. vars, needed when pressing cancel in ChannelSelection
			self.curSelectedRef = None
			self.curSelectedBouquet = None
			# needed, because if we won't zap, we have to go back to the current bouquet and service
			self.curRef = ServiceReference(self.servicelist.getCurrentSelection())
			self.curBouquet = self.servicelist.getRoot()
			self.startRef = ServiceReference(self.servicelist.getCurrentSelection())
			self.startBouquet = self.servicelist.getRoot()
			self.onClose.append(self.__onClose)
		else:
			self["actions"] = ActionMap(["EPGSelectActions", "OkCancelActions"],
			{
				"cancel": self.closeScreen,
				"ok": self.eventSelected,
				"red": self.redButtonPressed,
				"timerAdd": self.timerAdd,
				"yellow": self.yellowButtonPressed,
				"blue": self.blueButtonPressed,
				"info": self.infoKeyPressed,
				"input_date_time": self.enterDateTime,
				"nextBouquet": self.nextBouquet, # just used in multi epg yet
				"prevBouquet": self.prevBouquet, # just used in multi epg yet
				"nextService": self.nextService, # just used in single epg yet
				"prevService": self.prevService, # just used in single epg yet
			})
			self["MenuActions"] = HelpableActionMap(self, "MenuActions",
				{
					"menu": (self.createSetup, _("Open Context Menu"))
				}
			)
			self["actions"].csel = self
			self.onLayoutFinish.append(self.onCreate)

	def createSetup(self):
		self.session.openWithCallback(self.onSetupClose, EPGSelectionSetup)

	def onSetupClose(self):
		if config.misc.EPGSort.value == "Time":
			self.sort_type = 0
		else:
			self.sort_type = 1
		l = self["list"]
		l.sortSingleEPG(self.sort_type)

	def onCreate(self):
		#try:
			#from Plugins.Extensions.IMDb.plugin import IMDB, IMDBEPGSelection
		#except ImportError:
			#self.session.open(MessageBox, _("The IMDb plugin is not installed!\nPlease install it."), type = MessageBox.TYPE_INFO,timeout = 10 )
		l = self["list"]
		l.recalcEntrySize()
		if self.type == EPG_TYPE_MULTI:
			l.fillMultiEPG(self.services, self.ask_time)
			l.moveToService(self.session.nav.getCurrentlyPlayingServiceReference())
		elif self.type == EPG_TYPE_SINGLE:
			service = self.currentService
			self["Service"].newService(service.ref)
			if self.saved_title is None:
				self.saved_title = self.instance.getTitle()
			title = self.saved_title + ' - ' + service.getServiceName()
			self.instance.setTitle(title)
			l.fillSingleEPG(service)
		elif self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			service = ServiceReference(self.servicelist.getCurrentSelection())
			self["Service"].newService(service.ref)
			if self.saved_title is None:
				self.saved_title = self.instance.getTitle()
			title = self.saved_title + ' - ' + service.getServiceName()
			self.instance.setTitle(title)
			l.fillSingleEPG(service)
		else:
			l.fillSimilarList(self.currentService, self.eventid)
		if self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_ENHANCED:
			if config.misc.EPGSort.value == "Time":
				self.sort_type = 0
			else:
				self.sort_type = 1
			l.sortSingleEPG(self.sort_type)

	def nextBouquet(self):
		if self.type != EPG_TYPE_ENHANCED and self.bouquetChangeCB:
			self.bouquetChangeCB(1, self)
		elif self.type == EPG_TYPE_ENHANCED and config.usage.multibouquet.value:
			self.servicelist.nextBouquet()
			self.onCreate()

	def prevBouquet(self):
		if self.type != EPG_TYPE_ENHANCED and self.bouquetChangeCB:
			self.bouquetChangeCB(-1, self)
		elif self.type == EPG_TYPE_ENHANCED and config.usage.multibouquet.value:
			self.servicelist.prevBouquet()
			self.onCreate()

	def nextService(self):
		if self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
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
			else:
				self.nextService()
		else:
			if self.serviceChangeCB:
				self.serviceChangeCB(1, self)

	def prevService(self):
		if self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
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
			else:
				self.prevService()
		else:
			if self.serviceChangeCB:
				self.serviceChangeCB(-1, self)

	def enterDateTime(self):
		if self.type == EPG_TYPE_MULTI:
			global mepg_config_initialized
			if not mepg_config_initialized:
				config.misc.prev_mepg_time=ConfigClock(default = time())
				mepg_config_initialized = True
			self.session.openWithCallback(self.onDateTimeInputClosed, TimeDateInput, config.misc.prev_mepg_time )

	def onDateTimeInputClosed(self, ret):
		if len(ret) > 1:
			if ret[0]:
				self.ask_time=ret[1]
				self["list"].fillMultiEPG(self.services, ret[1])

	def closing(self):
		if self.oldService:
			self.session.nav.playService(self.oldService)
		self.setServicelistSelection(self.curBouquet, self.curRef.ref)
		self.close(self.closeRecursive)

	def closeScreen(self):
		self.close(self.closeRecursive)

	def infoKeyPressed(self):
		cur = self["list"].getCurrent()
		event = cur[0]
		service = cur[1]
		if event is not None:
			if self.type != EPG_TYPE_SIMILAR:
				self.session.open(EventViewSimple, event, service, self.eventViewCallback, self.openSimilarList)
			else:
				self.session.open(EventViewSimple, event, service, self.eventViewCallback)

	def openSimilarList(self, eventid, refstr):
		self.session.open(EPGSelection, refstr, None, eventid)

	def setServices(self, services):
		self.services = services
		self.onCreate()

	def setService(self, service):
		self.currentService = service
		self.onCreate()

	def eventViewCallback(self, setEvent, setService, val):
		l = self["list"]
		old = l.getCurrent()
		if val == -1:
			self.moveUp()
		elif val == +1:
			self.moveDown()
		cur = l.getCurrent()
		if self.type == EPG_TYPE_MULTI and cur[0] is None and cur[1].ref != old[1].ref:
			self.eventViewCallback(setEvent, setService, val)
		else:
			setService(cur[1])
			setEvent(cur[0])

	def eventSelected(self):
		self.infoKeyPressed()

	def setSortDescription(self):
		if config.misc.EPGSort.value == "Time":
			self.sort_type = 1
		else:
			self.sort_type = 0
		print 'SORT',config.misc.EPGSort.value
		self["list"].sortSingleEPG(self.sort_type)

	def redButtonPressed(self):
		if self.type == EPG_TYPE_MULTI:
			if self.zapFunc and self.key_red_choice == self.ZAP:
				lst = self["list"]
				count = lst.getCurrentChangeCount()
				if count == 0:
					self.closeRecursive = True
					ref = lst.getCurrent()[1]
					self.zapFunc(ref.ref)
		elif self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			try:
				from Plugins.Extensions.IMDb.plugin import IMDB, IMDBEPGSelection
				try:
					cur = self["list"].getCurrent()
					event = cur[0]
					name = event.getEventName()
				except:
					name = ''
				self.session.open(IMDB, name, False)
			except ImportError:
				self.session.open(MessageBox, _("The IMDb plugin is not installed!\nPlease install it."), type = MessageBox.TYPE_INFO,timeout = 10 )

	def yellowButtonPressed(self):
		if self.type == EPG_TYPE_MULTI:
			self["list"].updateMultiEPG(-1)
		elif self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			try:
				from Plugins.Extensions.EPGSearch.EPGSearch import EPGSearch
				try:
					cur = self["list"].getCurrent()
					event = cur[0]
					name = event.getEventName()
				except:
					name = ''
				self.session.open(EPGSearch, name, False)
			except ImportError:
				self.session.open(MessageBox, _("The EPGSearch plugin is not installed!\nPlease install it."), type = MessageBox.TYPE_INFO,timeout = 10 )

	def blueButtonPressed(self):
		if self.type == EPG_TYPE_MULTI:
			self["list"].updateMultiEPG(1)
		elif self.type == EPG_TYPE_SINGLE or self.type == EPG_TYPE_ENHANCED or self.type == EPG_TYPE_INFOBAR:
			try:
				from Plugins.Extensions.AutoTimer.AutoTimerEditor import addAutotimerFromEvent
				cur = self["list"].getCurrent()
				event = cur[0]
				if not event: return
				serviceref = cur[1]
				addAutotimerFromEvent(self.session, evt = event, service = serviceref)
			except ImportError:
				self.session.open(MessageBox, _("The AutoTimer plugin is not installed!\nPlease install it."), type = MessageBox.TYPE_INFO,timeout = 10 )

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
			newEntry = RecordTimerEntry(serviceref, checkOldTimers = True, dirname = preferredTimerPath(), *parseEvent(event))
			self.session.openWithCallback(self.finishedAdd, TimerEntry, newEntry)

	def finishedAdd(self, answer):
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
		self.finishedAdd(answer)

	def Record(self):
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
			self.session.openWithCallback(self.finishedAdd, RecordSetup, newEntry)

	def moveUp(self):
		self["list"].moveUp()

	def moveDown(self):
		self["list"].moveDown()
	
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
			days = [ _("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun") ]
			datestr = ""
			if event is not None:
				now = time()
				beg = event.getBeginTime()
				nowTime = localtime(now)
				begTime = localtime(beg)
				if nowTime[2] != begTime[2]:
					datestr = '%s %d.%d.'%(days[begTime[6]], begTime[2], begTime[1])
				else:
					datestr = '%s %d.%d.'%(_("Today"), begTime[2], begTime[1])
			self["date"].setText(datestr)
			if cur[1] is None:
				self["Service"].newService(None)
			else:
				self["Service"].newService(cur[1].ref)

		if cur[1] is None or cur[1].getServiceName() == "":
			if self.key_green_choice != self.EMPTY:
				self["key_green"].setText("")
				self.key_green_choice = self.EMPTY
			if self.key_red_choice != self.EMPTY:
				self["key_red"].setText("")
				self.key_red_choice = self.EMPTY
			return
		elif self.key_red_choice != self.ZAP and  self.type == EPG_TYPE_MULTI:
				self["key_red"].setText("Zap")
				self.key_red_choice = self.ZAP

		if event is None:
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

	def isPlayable(self):
		# check if service is playable
		current = ServiceReference(self.servicelist.getCurrentSelection())
		return not (current.ref.flags & (eServiceReference.isMarker|eServiceReference.isDirectory))

	def setServicelistSelection(self, bouquet, service):
		# we need to select the old service with bouquet
		if self.servicelist.getRoot() != bouquet: #already in correct bouquet?
			self.servicelist.clearPath()
			self.servicelist.enterPath(self.servicelist.bouquet_root)
			self.servicelist.enterPath(bouquet)
		self.servicelist.setCurrentSelection(service) #select the service in servicelist

	def ZapTo(self):
		currch = self.session.nav.getCurrentlyPlayingServiceReference()
		currch = currch.toString()
		switchto = ServiceReference(self.servicelist.getCurrentSelection())
		switchto = str(switchto)
#		print 'switchto',switchto
#		print 'Current Playing',currch
#		print 'self.oldService',str(self.oldService)
		
		if not switchto == currch:
#			print 'match1'
			self.servicelist_orig_zap()
		else:
#			print 'match2'
			self.close()

	#def CheckItNow(self):
		#self.CheckForEPG.stop()
		#self.onCreate()

	def keyNumberGlobal(self, number):
		from Screens.InfoBarGenerics import NumberZap
		self.session.openWithCallback(self.numberEntered, NumberZap, number)

	def numberEntered(self, retval):
		if retval > 0:
			self.zapToNumber(retval)

	def searchNumberHelper(self, serviceHandler, num, bouquet):
		servicelist = serviceHandler.list(bouquet)
		if not servicelist is None:
			while num:
				serviceIterator = servicelist.getNext()
				if not serviceIterator.valid(): #check end of list
					break
				playable = not (serviceIterator.flags & (eServiceReference.isMarker|eServiceReference.isDirectory))
				if playable:
					num -= 1;
			if not num: #found service with searched number ?
				return serviceIterator, 0
		return None, num

	def zapToNumber(self, number):
		bouquet = self.servicelist.bouquet_root
		service = None
		serviceHandler = eServiceCenter.getInstance()
		bouquetlist = serviceHandler.list(bouquet)
		if not bouquetlist is None:
			while number:
				bouquet = bouquetlist.getNext()
				if not bouquet.valid(): #check end of list
					break
				if bouquet.flags & eServiceReference.isDirectory:
					service, number = self.searchNumberHelper(serviceHandler, number, bouquet)
		if not service is None:
			self.setServicelistSelection(bouquet, service)
		self.onCreate()

	# ChannelSelection Support
	def prepareChannelSelectionDisplay(self):
		# save current ref and bouquet ( for cancel )
		self.curSelectedRef = eServiceReference(self.servicelist.getCurrentSelection().toString())
		self.curSelectedBouquet = self.servicelist.getRoot()

	def cancelChannelSelection(self):
		# select service and bouquet selected before started ChannelSelection
		if self.servicelist.revertMode is None:
			ref = self.curSelectedRef
			bouquet = self.curSelectedBouquet
			if ref.valid() and bouquet.valid():
				# select bouquet and ref in servicelist
				self.setServicelistSelection(bouquet, ref)
		# close ChannelSelection
		self.servicelist.revertMode = None
		self.servicelist.asciiOff()
		self.servicelist.close(None)

		# clean up
		self.curSelectedRef = None
		self.curSelectedBouquet = None
		# display VZ data
		self.servicelist_overwrite_zap()

	#def switchChannelDown(self):
		#self.prepareChannelSelectionDisplay()
		#self.servicelist.moveDown()
		## show ChannelSelection
		#self.session.execDialog(self.servicelist)

	#def switchChannelUp(self):
		#self.prepareChannelSelectionDisplay()
		#self.servicelist.moveUp()
		## show ChannelSelection
		#self.session.execDialog(self.servicelist)

	def showFavourites(self):
		self.prepareChannelSelectionDisplay()
		self.servicelist.showFavourites()
		# show ChannelSelection
		self.session.execDialog(self.servicelist)

	def openServiceList(self):
		self.prepareChannelSelectionDisplay()
		# show ChannelSelection
		self.session.execDialog(self.servicelist)

	def servicelist_overwrite_zap(self):
		# we do not really want to zap to the service, just display data for VZ
		self.currentPiP = ""
		if self.isPlayable():
			self.onCreate()

	def __onClose(self):
		# reverse changes of ChannelSelection 
		self.servicelist.zap = self.servicelist_orig_zap
		self.servicelist["actions"] = ActionMap(["OkCancelActions", "TvRadioActions"],
			{
				"cancel": self.servicelist.cancel,
				"ok": self.servicelist.channelSelected,
				"keyRadio": self.servicelist.setModeRadio,
				"keyTV": self.servicelist.setModeTv,
			})

class RecordSetup(TimerEntry):
	def __init__(self, session, timer):
		Screen.__init__(self, session)
		self.timer = timer
		self.entryDate = None
		self.entryService = None
		self.createConfig()
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = session)
		self.createSetup("config")

	def createConfig(self):
			justplay = self.timer.justplay
			afterevent = {
				AFTEREVENT.NONE: "nothing",
				AFTEREVENT.DEEPSTANDBY: "deepstandby",
				AFTEREVENT.STANDBY: "standby",
				AFTEREVENT.AUTO: "auto"
				}[self.timer.afterEvent]

			weekday_table = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
			# calculate default values
			day = []
			weekday = 0
			for x in (0, 1, 2, 3, 4, 5, 6):
				day.append(0)
			if self.timer.repeated: # repeated
				type = "repeated"
				if (self.timer.repeated == 31): # Mon-Fri
					repeated = "weekdays"
				elif (self.timer.repeated == 127): # daily
					repeated = "daily"
				else:
					flags = self.timer.repeated
					repeated = "user"
					count = 0
					for x in (0, 1, 2, 3, 4, 5, 6):
						if flags == 1: # weekly
							print "Set to weekday " + str(x)
							weekday = x
						if flags & 1 == 1: # set user defined flags
							day[x] = 1
							count += 1
						else:
							day[x] = 0
						flags = flags >> 1
					if count == 1:
						repeated = "weekly"
			else: # once
				type = "once"
				repeated = None
				weekday = (int(strftime("%w", localtime(self.timer.begin))) - 1) % 7
				day[weekday] = 1

			self.timerentry_justplay = ConfigSelection(choices = [("zap", _("zap")), ("record", _("record"))], default = {0: "record", 1: "zap"}[justplay])
			if SystemInfo["DeepstandbySupport"]:
				shutdownString = _("go to deep standby")
			else:
				shutdownString = _("shut down")
			self.timerentry_afterevent = ConfigSelection(choices = [("nothing", _("do nothing")), ("standby", _("go to standby")), ("deepstandby", shutdownString), ("auto", _("auto"))], default = afterevent)
			self.timerentry_type = ConfigSelection(choices = [("once",_("once")), ("repeated", _("repeated"))], default = type)
			self.timerentry_name = ConfigText(default = self.timer.name, visible_width = 50, fixed_size = False)
			self.timerentry_description = ConfigText(default = self.timer.description, visible_width = 50, fixed_size = False)
			self.timerentry_tags = self.timer.tags[:]
			self.timerentry_tagsset = ConfigSelection(choices = [not self.timerentry_tags and "None" or " ".join(self.timerentry_tags)])
			self.timerentry_repeated = ConfigSelection(default = repeated, choices = [("daily", _("daily")), ("weekly", _("weekly")), ("weekdays", _("Mon-Fri")), ("user", _("user defined"))])
			self.timerentry_date = ConfigDateTime(default = self.timer.begin, formatstring = _("%d.%B %Y"), increment = 86400)
			self.timerentry_starttime = ConfigClock(default = self.timer.begin)
			self.timerentry_endtime = ConfigClock(default = self.timer.end)
			self.timerentry_showendtime = ConfigSelection(default = ((self.timer.end - self.timer.begin) > 4), choices = [(True, _("yes")), (False, _("no"))])

			default = self.timer.dirname or defaultMoviePath()
			tmp = config.movielist.videodirs.value
			if default not in tmp:
				tmp.append(default)
			self.timerentry_dirname = ConfigSelection(default = default, choices = tmp)
			self.timerentry_repeatedbegindate = ConfigDateTime(default = self.timer.repeatedbegindate, formatstring = _("%d.%B %Y"), increment = 86400)
			self.timerentry_weekday = ConfigSelection(default = weekday_table[weekday], choices = [("mon",_("Monday")), ("tue", _("Tuesday")), ("wed",_("Wednesday")), ("thu", _("Thursday")), ("fri", _("Friday")), ("sat", _("Saturday")), ("sun", _("Sunday"))])
			self.timerentry_day = ConfigSubList()
			for x in (0, 1, 2, 3, 4, 5, 6):
				self.timerentry_day.append(ConfigYesNo(default = day[x]))

			# FIXME some service-chooser needed here
			servicename = "N/A"
			try: # no current service available?
				servicename = str(self.timer.service_ref.getServiceName())
			except:
				pass
			self.timerentry_service_ref = self.timer.service_ref
			self.timerentry_service = ConfigSelection([servicename])

	def createSetup(self, widget):
		self.list = []
		self.list.append(getConfigListEntry(_("Name"), self.timerentry_name))
		self.list.append(getConfigListEntry(_("Description"), self.timerentry_description))
		self.timerJustplayEntry = getConfigListEntry(_("Timer Type"), self.timerentry_justplay)
		self.list.append(self.timerJustplayEntry)
		self.timerTypeEntry = getConfigListEntry(_("Repeat Type"), self.timerentry_type)
		self.list.append(self.timerTypeEntry)

		if self.timerentry_type.value == "once":
			self.frequencyEntry = None
		else: # repeated
			self.frequencyEntry = getConfigListEntry(_("Repeats"), self.timerentry_repeated)
			self.list.append(self.frequencyEntry)
			self.repeatedbegindateEntry = getConfigListEntry(_("Starting on"), self.timerentry_repeatedbegindate)
			self.list.append(self.repeatedbegindateEntry)
			if self.timerentry_repeated.value == "daily":
				pass
			if self.timerentry_repeated.value == "weekdays":
				pass
			if self.timerentry_repeated.value == "weekly":
				self.list.append(getConfigListEntry(_("Weekday"), self.timerentry_weekday))
			if self.timerentry_repeated.value == "user":
				self.list.append(getConfigListEntry(_("Monday"), self.timerentry_day[0]))
				self.list.append(getConfigListEntry(_("Tuesday"), self.timerentry_day[1]))
				self.list.append(getConfigListEntry(_("Wednesday"), self.timerentry_day[2]))
				self.list.append(getConfigListEntry(_("Thursday"), self.timerentry_day[3]))
				self.list.append(getConfigListEntry(_("Friday"), self.timerentry_day[4]))
				self.list.append(getConfigListEntry(_("Saturday"), self.timerentry_day[5]))
				self.list.append(getConfigListEntry(_("Sunday"), self.timerentry_day[6]))

		self.entryDate = getConfigListEntry(_("Date"), self.timerentry_date)
		if self.timerentry_type.value == "once":
			self.list.append(self.entryDate)
		
		self.entryStartTime = getConfigListEntry(_("StartTime"), self.timerentry_starttime)
		self.list.append(self.entryStartTime)
		
		self.entryShowEndTime = getConfigListEntry(_("Set End Time"), self.timerentry_showendtime)
		if self.timerentry_justplay.value == "zap":
			self.list.append(self.entryShowEndTime)
		self.entryEndTime = getConfigListEntry(_("EndTime"), self.timerentry_endtime)
		if self.timerentry_justplay.value != "zap" or self.timerentry_showendtime.value:
			self.list.append(self.entryEndTime)

		self.channelEntry = getConfigListEntry(_("Channel"), self.timerentry_service)
		self.list.append(self.channelEntry)

		self.dirname = getConfigListEntry(_("Location"), self.timerentry_dirname)
		self.tagsSet = getConfigListEntry(_("Tags"), self.timerentry_tagsset)
		if self.timerentry_justplay.value != "zap":
			if config.usage.setup_level.index >= 2: # expert+
				self.list.append(self.dirname)
			if getPreferredTagEditor():
				self.list.append(self.tagsSet)
			self.list.append(getConfigListEntry(_("After event"), self.timerentry_afterevent))

		self.keyGo()

	def finishedChannelSelection(self, *args):
		if args:
			self.timerentry_service_ref = ServiceReference(args[0])
			self.timerentry_service.setCurrentText(self.timerentry_service_ref.getServiceName())
			self["config"].invalidate(self.channelEntry)
			
	def getTimestamp(self, date, mytime):
		d = localtime(date)
		dt = datetime(d.tm_year, d.tm_mon, d.tm_mday, mytime[0], mytime[1])
		return int(mktime(dt.timetuple()))

	def getBeginEnd(self):
		date = self.timerentry_date.value
		endtime = self.timerentry_endtime.value
		starttime = self.timerentry_starttime.value
		begin = self.getTimestamp(date, starttime)
		end = self.getTimestamp(date, endtime)
		# if the endtime is less than the starttime, add 1 day.
		if end < begin:
			end += 86400
		return begin, end

	def selectChannelSelector(self, *args):
		self.session.openWithCallback(
				self.finishedChannelSelectionCorrection,
				ChannelSelection.SimpleChannelSelection,
				_("Select channel to record from")
			)

	def finishedChannelSelectionCorrection(self, *args):
		if args:
			self.finishedChannelSelection(*args)
			self.keyGo()

	def keyGo(self, result = None):
		self.timer.name = self.timerentry_name.value
		self.timer.description = self.timerentry_description.value
		self.timer.justplay = self.timerentry_justplay.value == "zap"
		if self.timerentry_justplay.value == "zap":
			if not self.timerentry_showendtime.value:
				self.timerentry_endtime.value = self.timerentry_starttime.value
		self.timer.resetRepeated()
		self.timer.afterEvent = {
			"auto": AFTEREVENT.AUTO
			}[self.timerentry_afterevent.value]
		self.timer.service_ref = self.timerentry_service_ref
		self.timer.tags = self.timerentry_tags

		if self.timer.dirname or self.timerentry_dirname.value != defaultMoviePath():
			self.timer.dirname = self.timerentry_dirname.value
			config.movielist.last_timer_videodir.value = self.timer.dirname
			config.movielist.last_timer_videodir.save()

		if self.timerentry_type.value == "once":
			self.timer.begin, self.timer.end = self.getBeginEnd()

		if self.timer.eit is not None:
			event = eEPGCache.getInstance().lookupEventId(self.timer.service_ref.ref, self.timer.eit)
			if event:
				n = event.getNumOfLinkageServices()
				if n > 1:
					tlist = []
					ref = self.session.nav.getCurrentlyPlayingServiceReference()
					parent = self.timer.service_ref.ref
					selection = 0
					for x in range(n):
						i = event.getLinkageService(parent, x)
						if i.toString() == ref.toString():
							selection = x
						tlist.append((i.getName(), i))
					self.session.openWithCallback(self.subserviceSelected, ChoiceBox, title=_("Please select a subservice to record..."), list = tlist, selection = selection)
					return
				elif n > 0:
					parent = self.timer.service_ref.ref
					self.timer.service_ref = ServiceReference(event.getLinkageService(parent, 0))
		self.saveTimer()
		self.close((True, self.timer))

	def subserviceSelected(self, service):
		if not service is None:
			self.timer.service_ref = ServiceReference(service[1])
		self.saveTimer()
		self.close((True, self.timer))

	def saveTimer(self):
		self.session.nav.RecordTimer.saveTimer()
				
class EPGSelectionSetup(ConfigListScreen, Screen):
	skin = """
		<screen name="EPGSelectionSetup" position="center,center" size="500,285" title="EPG Setup">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" position="10,45" size="480,250" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.skin = EPGSelectionSetup.skin
		self.skinName = "EPGSelectionSetup"
		self["title"] = Label(_("EPG Setup"))
		self.onChangedEntry = [ ]

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		self.createSetup()
		
		self["actions"] = ActionMap(["SetupActions"],
		{
		  "cancel": self.keyCancel,
		  "save": self.keySave,
		}, -2)
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("OK"))

	def createSetup(self):
		self.editListEntry = None
		self.list = []
		self.list.append(getConfigListEntry(_("Sort List by"), config.misc.EPGSort))
		self["config"].list = self.list
		self["config"].setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def keySave(self):
		for x in self["config"].list:
			x[1].save()
		self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()
