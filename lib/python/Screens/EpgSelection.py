from time import localtime, mktime, strftime, time

from enigma import ePoint, eServiceCenter, eServiceReference, eTimer

from Components.ActionMap import ActionMap, HelpableActionMap, HelpableNumberActionMap
from Components.EpgConfig import EPGSettings
from Components.EpgList import EPGBouquetList, EPGListGrid, EPGListMulti, EPGListSingle, EPGListVertical, EPG_TYPE_ENHANCED, EPG_TYPE_GRAPH, EPG_TYPE_INFOBAR, EPG_TYPE_INFOBARGRAPH, EPG_TYPE_MULTI, EPG_TYPE_SIMILAR, EPG_TYPE_SINGLE, EPG_TYPE_VERTICAL, MAX_TIMELINES, TimelineText
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.Sources.Event import Event
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.StaticText import StaticText
from Components.UsageConfig import preferredTimerPath
from Components.config import ConfigClock, config, configfile
from RecordTimer import AFTEREVENT, RecordTimerEntry, parseEvent
from Screens.ChoiceBox import ChoiceBox
from Screens.DateTimeInput import EPGJumpTime
from Screens.EventView import getEventViewInstance, showEventViewCallback
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.TimerEdit import TimerSanityConflict
from Screens.TimerEntry import InstantRecordTimerEntry, TimerEntry
from ServiceReference import ServiceReference
from skin import parameters
from Tools.Alternatives import CompareWithAlternatives
from Tools.FallbackTimer import FallbackTimerList

try:  # PiPServiceRelation installed?
	from Plugins.SystemPlugins.PiPServiceRelation.plugin import getRelationDict
except ImportError:
	getRelationDict = None


autopoller = None
autotimer = None


class EPGSelectionBase(Screen):
	# Shared constants used for the green button / timer state tracking.
	catchupPlayerFunc = None
	EMPTY = 0
	ADD_TIMER = 1
	REMOVE_TIMER = 2
	ZAP = 1

	def __init__(self, session, epgConfig, startBouquet=None, startRef=None, bouquets=None):
		Screen.__init__(self, session, enableHelp=True)

		# epgConfig is the config subsection for this EPG type, e.g. config.epgselection.grid
		self.epgConfig = epgConfig
		from Screens.InfoBar import InfoBar
		servicelist = InfoBar.instance.servicelist if InfoBar.instance else None
		if startBouquet is None and servicelist:
			startBouquet = servicelist.getRoot()
		self.bouquets = bouquets or self.getDefaultBouquets(servicelist, startBouquet)
		# Enhanced, infobar and vertical EPG keep the channel list in sync (as in the old EPGSelection).
		self.servicelist = servicelist if self.type in (EPG_TYPE_ENHANCED, EPG_TYPE_INFOBAR, EPG_TYPE_VERTICAL) else None
		self.startBouquet = startBouquet
		self.startRef = startRef

		self.closeRecursive = False
		self.eventviewDialog = None
		self.eventviewWasShown = False
		self.pipServiceRelation = getRelationDict() if getRelationDict else {}
		self.ChoiceBoxDialog = None
		# key_green_choice tracks current timer state for the green button label.
		self.key_green_choice = self.EMPTY

		# PiP state saved/restored around EPG open/close.
		self.Oldpipshown = bool(self.session.pipshown)
		self.session.pipshown = False
		self.onClose.append(self.restorePiP)

		# Number zap state for the inline channel number entry.
		self.zapnumberstarted = False
		self.NumberZapTimer = eTimer()
		self.NumberZapTimer.callback.append(self.dozumberzap)
		self.NumberZapField = None

		self["Service"] = ServiceEvent()
		self["Event"] = Event()
		self["lab1"] = Label(_("Please wait while gathering data..."))
		self["lab1"].hide()

		# Button label widgets, concrete classes may override text via _updateButtonText.
		self["key_red"] = StaticText(_("IMDb Search"))
		self["key_green"] = StaticText(_("Add Timer"))
		self["key_yellow"] = StaticText(_("EPG Search"))
		self["key_blue"] = StaticText(_("Add AutoTimer"))
		self["key_menu"] = StaticText(_("MENU"))
		self["key_info"] = StaticText(_("INFO"))
		self["key_text"] = StaticText(_("TEXT"))
		self["key_epg"] = StaticText(_("EPG"))
		self["key_play"] = StaticText("")

		helpDescription = _("EPG Actions")

		self["okactions"] = HelpableActionMap(self, "OkCancelActions", {
			"cancel": (self.closeScreen, _("Exit EPG")),
			"OK": self.helpKeyAction("ok"),
			"OKLong": self.helpKeyAction("oklong"),
		}, prio=-1, description=helpDescription)

		self["colouractions"] = HelpableActionMap(self, "ColorActions", {
			"red": self.helpKeyAction("red"),
			"redlong": self.helpKeyAction("redlong"),
			"green": self.helpKeyAction("green"),
			"greenlong": self.helpKeyAction("greenlong"),
			"yellow": self.helpKeyAction("yellow"),
			"yellowlong": self.helpKeyAction("yellowlong"),
			"blue": self.helpKeyAction("blue"),
			"bluelong": self.helpKeyAction("bluelong"),
		}, prio=-1, description=helpDescription)

		self["recordingactions"] = HelpableActionMap(self, "InfobarInstantRecord", {
			"ShortRecord": self.helpKeyAction("rec"),
			"LongRecord": self.helpKeyAction("reclong"),
		}, prio=-1, description=helpDescription)

		# Base epgactions map; concrete classes add their own entries.
		self["epgactions"] = HelpableActionMap(self, "EPGSelectActions", {}, prio=-1)
		self["epgcursoractions"] = HelpableActionMap(self, "DirectionActions", {
			"up": (self.moveUp, _("Goto previous channel")),
			"down": (self.moveDown, _("Goto next channel")),
		}, prio=-1, description=_("EPG Navigation Actions"))

		self["epgcatchupactions"] = HelpableActionMap(self, "EPGCatchUpActions", {
			"play": (self.playCatchup, _("Play catch up service archive")),
		}, prio=-2, description=_("Catch Up Player Actions"))
		self["epgcatchupactions"].setEnabled(callable(self.catchupPlayerFunc))

		# dialogactions is enabled while ChoiceBoxDialog is open (disables other maps).
		self["dialogactions"] = HelpableActionMap(self, "WizardActions", {
			"back": (self.closeChoiceBoxDialog, _("Close dialog")),
		}, prio=-1)
		self["dialogactions"].setEnabled(False)

		self._updateButtonText()

		self.refreshTimer = eTimer()
		self.refreshTimer.timeout.get().append(self.refreshlist)
		self.onClose.append(self.stopTimers)

		# Defer actual list population until the screen layout is complete.
		self.onLayoutFinish.append(self.onCreate)

	def addEpgActions(self, actions, mapName="epgactions", context="EPGSelectActions"):
		for action, response in actions.items():
			self[mapName].addAction(self, context, action, response)

	def addCursorActions(self, actions):
		self.addEpgActions(actions, "epgcursoractions", "DirectionActions")

	def getDefaultBouquets(self, servicelist, startBouquet):
		bouquets = servicelist.getBouquetList() if servicelist else None
		if not bouquets and startBouquet:
			bouquets = [(ServiceReference(startBouquet).getServiceName(), startBouquet)]
		return bouquets or []


	def moveUp(self):
		self[f"list{self.activeList}"].moveTo(self[f"list{self.activeList}"].instance.moveUp)

	def moveDown(self):
		self[f"list{self.activeList}"].moveTo(self[f"list{self.activeList}"].instance.moveDown)

	def nextPage(self):
		self[f"list{self.activeList}"].moveTo(self[f"list{self.activeList}"].instance.pageDown)

	def prevPage(self):
		self[f"list{self.activeList}"].moveTo(self[f"list{self.activeList}"].instance.pageUp)

	def toTop(self):
		self[f"list{self.activeList}"].moveTo(self[f"list{self.activeList}"].instance.moveTop)

	def toEnd(self):
		self[f"list{self.activeList}"].moveTo(self[f"list{self.activeList}"].instance.moveEnd)


	def openEventView(self):
		event, service = self[f"list{self.activeList}"].getCurrent()[:2]
		if self.eventviewDialog:
			self.closeEventViewDialog()
		elif event is not None:
			if self.type == EPG_TYPE_INFOBARGRAPH:
				self.eventviewDialog = getEventViewInstance(self.session, event, service, skinName="InfoBarEventView")
				self.eventviewDialog.show()
			else:
				showEventViewCallback(None, self.session, False, event, service,
										callback=self.eventViewCallback,
										similarEPGCB=self.openSimilarList)

	def updateEventViewDialog(self, event, service):
		# Keep the infobar event view overlay in sync with the selection.
		if self.eventviewDialog and event is not None and self.type in (EPG_TYPE_INFOBAR, EPG_TYPE_INFOBARGRAPH):
			self.closeEventViewDialog()
			self.eventviewDialog = getEventViewInstance(self.session, event, service, skinName="InfoBarEventView")
			self.eventviewDialog.show()

	def openSimilarList(self, eventId, refstr):
		self.session.open(EPGSelection, refstr, None, eventId)

	def eventViewCallback(self, setEvent, setService, val):
		# Called by EventView when user navigates prev/next event.
		# Concrete classes override this for type-specific list navigation.
		if val == -1:
			self.moveUp()
		elif val == +1:
			self.moveDown()
		event, service = self[f"list{self.activeList}"].getCurrent()[:2]
		setService(service)
		setEvent(event)

	def closeEventViewDialog(self):
		if self.eventviewDialog:
			self.eventviewDialog.hide()
			del self.eventviewDialog
			self.eventviewDialog = None


	def sortEPG(self):
		self.closeEventViewDialog()


	def enterDateTime(self):
		def callback(result):
			if len(result) > 1 and result[0]:
				self._onDateTimeEntered(result[1])

		if self.type == EPG_TYPE_GRAPH:
			self.session.openWithCallback(callback, EPGJumpTime,
											config.epgselection.grid.prevtime,
											config.epg.histminutes.value)
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			self.session.openWithCallback(callback, EPGJumpTime,
											config.epgselection.infobar.prevtime,
											config.epg.histminutes.value)
		elif self.type == EPG_TYPE_MULTI:
			# Multi-EPG keeps its own shared time config.
			global mepg_config_initialized
			if not mepg_config_initialized:
				config.misc.prev_mepg_time = ConfigClock(default=time())
				mepg_config_initialized = True
			self.session.openWithCallback(callback, EPGJumpTime,
											config.misc.prev_mepg_time, 0)
		elif self.type == EPG_TYPE_VERTICAL:
			self.session.openWithCallback(callback, EPGJumpTime,
											config.epgselection.vertical.prevtime,
											config.epg.histminutes.value)

	def _onDateTimeEntered(self, jumpTime):
		# Override in concrete classes that support time jumping.
		pass


	def showMovies(self):
		from Screens.InfoBar import InfoBar
		InfoBar.instance.showMovies()


	def openSingleEPG(self):
		# Opens the single EPG for the selected service.
		event, service = self[f"list{self.activeList}"].getCurrent()[:2]
		if service is not None:
			self.session.open(EPGSelection, service.ref)


	def openIMDb(self):
		self.closeEventViewDialog()
		try:
			from Plugins.Extensions.IMDb.plugin import IMDB
		except ImportError:
			self.session.open(MessageBox, _("The IMDb plugin is not installed!\nPlease install it."),
								type=MessageBox.TYPE_INFO, timeout=10)
			return
		event = self[f"list{self.activeList}"].getCurrent()[0]
		if event is not None:
			self.session.open(IMDB, event.getEventName(), False)

	def openTMDb(self):
		self.closeEventViewDialog()
		try:
			from Plugins.Extensions.tmdb.tmdb import tmdbScreen
		except ImportError:
			self.session.open(MessageBox, _("The TMDB plugin is not installed!\nPlease install it."),
								type=MessageBox.TYPE_INFO, timeout=10)
			return
		event = self[f"list{self.activeList}"].getCurrent()[0]
		if event is not None:
			self.session.open(tmdbScreen, event.getEventName())

	def openEPGSearch(self):
		self.closeEventViewDialog()
		try:
			from Plugins.Extensions.EPGSearch.EPGSearch import EPGSearch
		except ImportError:
			self.session.open(MessageBox, _("The EPGSearch plugin is not installed!\nPlease install it."),
								type=MessageBox.TYPE_INFO, timeout=10)
			return
		event = self[f"list{self.activeList}"].getCurrent()[0]
		if event is not None:
			self.session.open(EPGSearch, event.getEventName(), False)

	def addEditAutoTimer(self):
		self.closeEventViewDialog()
		event, service = self[f"list{self.activeList}"].getCurrent()[:2]
		if event is None:
			return
		timer = self.session.nav.RecordTimer.getTimerForEvent(service, event)
		if timer is not None and hasattr(timer, 'autoTimerId') and timer.autoTimerId:
			self._editAutoTimer(timer)
		else:
			self.addAutoTimer()

	def addAutoTimer(self):
		self.closeEventViewDialog()
		try:
			from Plugins.Extensions.AutoTimer.AutoTimerEditor import addAutotimerFromEvent
		except ImportError:
			self.session.open(MessageBox, _("The AutoTimer plugin is not installed!\nPlease install it."),
								type=MessageBox.TYPE_INFO, timeout=10)
			return
		event, service = self[f"list{self.activeList}"].getCurrent()[:2]
		if event is None:
			return
		addAutotimerFromEvent(self.session, evt=event, service=service)
		self.refreshTimer.start(3000)

	def _editAutoTimer(self, timer):
		try:
			from Plugins.Extensions.AutoTimer.AutoTimerEditor import editAutotimerFromTimer
		except ImportError:
			self.session.open(MessageBox, _("The AutoTimer plugin is not installed!\nPlease install it."),
								type=MessageBox.TYPE_INFO, timeout=10)
			return
		editAutotimerFromTimer(self.session, timer)
		self.refreshTimer.start(3000)

	def addAutoTimerSilent(self):
		# Used by the RecordTimerQuestion menu as a quick add-without-editing action.
		try:
			from Plugins.Extensions.AutoTimer.AutoTimerEditor import addAutotimerFromEventSilent
		except ImportError:
			self.session.open(MessageBox, _("The AutoTimer plugin is not installed!\nPlease install it."),
								type=MessageBox.TYPE_INFO, timeout=10)
			return
		event, service = self[f"list{self.activeList}"].getCurrent()[:2]
		if event is None:
			return
		addAutotimerFromEventSilent(self.session, evt=event, service=service)
		self.refreshTimer.start(3000)


	def setupKeyPlayButtonDisplay(self, stime, service):
		if hasattr(self[f"list{self.activeList}"], "detectCatchupAvailable"):
			enabled = self[f"list{self.activeList}"].detectCatchupAvailable(stime, service)
			if "epgcatchupactions" in self:
				self["epgcatchupactions"].setEnabled(enabled and callable(self.catchupPlayerFunc))
			self["key_play"].setText(_("PLAY") if enabled and callable(self.catchupPlayerFunc) else "")

	def playCatchup(self):
		if not callable(self.catchupPlayerFunc):
			return
		event, service = self[f"list{self.activeList}"].getCurrent()[:2]
		stime = event and event.getBeginTime()
		service = service and service.ref
		if hasattr(self[f"list{self.activeList}"], "detectCatchupAvailable"):
			if self[f"list{self.activeList}"].detectCatchupAvailable(stime, service):
				self.catchupPlayerFunc(event, service)


	def createMenu(self):
		self.closeEventViewDialog()
		from Screens.Setup import Setup
		from Components.EpgList import EPG_TYPE_ENHANCED, EPG_TYPE_GRAPH, EPG_TYPE_INFOBAR, EPG_TYPE_INFOBARGRAPH, EPG_TYPE_MULTI, EPG_TYPE_SINGLE, EPG_TYPE_VERTICAL
		_SETUP_KEYS = {
			EPG_TYPE_SINGLE: ("EPGSingle", None),
			EPG_TYPE_MULTI: ("EPGMulti", None),
			EPG_TYPE_ENHANCED: ("EPGEnhanced", None),
			EPG_TYPE_INFOBAR: ("EPGInfobar", "reopeninfobar"),
			EPG_TYPE_GRAPH: ("EPGGraphical", "reopengraph"),
			EPG_TYPE_INFOBARGRAPH: ("EPGInfobarGraphical", "reopeninfobargraph"),
			EPG_TYPE_VERTICAL: ("EPGVertical", "reopenvertical"),
		}
		key, closeType = _SETUP_KEYS.get(self.type, (None, None))
		if not key:
			return

		def _setupDone(test=None):
			if closeType:
				self.close(closeType)
			else:
				self._updateButtonText()
				self.key_green_choice = self.EMPTY  # Force the timer label update.
				self.onSelectionChanged()

		self.session.openWithCallback(_setupDone, Setup, key)


	def openTimerList(self):
		self.closeEventViewDialog()
		from Screens.Timers import RecordTimerOverview
		self.session.open(RecordTimerOverview)

	def openAutoTimerList(self):
		self.closeEventViewDialog()
		global autopoller, autotimer
		try:
			from Plugins.Extensions.AutoTimer.AutoTimer import AutoTimer
			from Plugins.Extensions.AutoTimer.AutoPoller import AutoPoller
			autopoller = AutoPoller()
			autotimer = AutoTimer()
			try:
				autotimer.readXml()
			except SyntaxError as se:
				self.session.open(MessageBox,
									_("Your config file is not well-formed:\n%s") % str(se),
									type=MessageBox.TYPE_ERROR, timeout=10)
				return
			if autopoller is not None:
				autopoller.stop()
			from Plugins.Extensions.AutoTimer.AutoTimerOverview import AutoTimerOverview
			self.session.openWithCallback(self.editCallback, AutoTimerOverview, autotimer)
		except ImportError:
			self.session.open(MessageBox, _("The AutoTimer plugin is not installed!\nPlease install it."),
								type=MessageBox.TYPE_INFO, timeout=10)

	def editCallback(self, session):
		global autopoller, autotimer
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


	def addEditTimer(self):
		# Primary "add timer" action: opens RecordTimerQuestion in manual (edit) mode
		# so the user sees the full timer entry screen.
		self.RecordTimerQuestion(manual=True)

	def addEditTimerMenu(self):
		# Shows a quick-choice menu (add / zap / zap+rec / autotimer).
		self.RecordTimerQuestion(manual=False)

	def addEditZapTimerSilent(self):
		# Creates a zap timer without opening the full timer entry screen.
		self.doInstantTimer(zap=1, zaprecord=0)

	def editTimer(self, timer):
		# FallbackTimerList handles external (e.g. satellite) timers.
		prevExternal = timer.external
		self.session.open(TimerEntry, timer)
		if prevExternal and not timer.external:
			def fallbackInitDone():
				fallbackTimer.removeTimer(timer, self.refreshlist)
			fallbackTimer = FallbackTimerList(self, fallbackInitDone)
		elif timer.external:
			def fallbackInitDone():
				fallbackTimer.editTimer(timer, self.refreshlist)
			fallbackTimer = FallbackTimerList(self, fallbackInitDone)

	def removeTimer(self, timer):
		self.closeChoiceBoxDialog()
		timer.afterEvent = AFTEREVENT.NONE
		if timer.external:
			def fallbackInitDone():
				fallbackTimer.removeTimer(timer, self.refreshlist)
			fallbackTimer = FallbackTimerList(self, fallbackInitDone)
		else:
			self.session.nav.RecordTimer.removeEntry(timer)
		self.setTimerButtonText(_("Add Timer"))
		self.key_green_choice = self.ADD_TIMER
		self.refreshlist()

	def disableTimer(self, timer):
		self.closeChoiceBoxDialog()
		if timer.external:
			def fallbackInitDone():
				fallbackTimer.toggleTimer(timer, self.refreshlist)
			fallbackTimer = FallbackTimerList(self, fallbackInitDone)
		else:
			timer.disable()
			self.session.nav.RecordTimer.timeChanged(timer)
		self.setTimerButtonText(_("Add Timer"))
		self.key_green_choice = self.ADD_TIMER
		self.refreshlist()

	def enableTimer(self, timer):
		self.closeChoiceBoxDialog()
		if timer.external:
			def fallbackInitDone():
				fallbackTimer.toggleTimer(timer, self.refreshlist)
			fallbackTimer = FallbackTimerList(self, fallbackInitDone)
		else:
			timer.enable()
			self.session.nav.RecordTimer.timeChanged(timer)
		self.setTimerButtonText(_("Add Timer"))
		self.key_green_choice = self.ADD_TIMER
		self.refreshlist()

	def RecordTimerQuestion(self, manual=False):
		event, service = self[f"list{self.activeList}"].getCurrent()[:2]
		if event is None:
			return
		serviceRefStr = service.ref.toCompareString()
		title = None
		foundtimer = self.getRecordEvent(serviceRefStr, event)
		if foundtimer:
			timer = foundtimer
			if timer.isRunning():
				cb1 = lambda ret: self.removeTimer(timer)  # noqa: E731
				cb2 = lambda ret: self.editTimer(timer)  # noqa: E731
				menu = [
					(_("Delete Timer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb1),
					(_("Edit Timer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb2),
				]
			else:
				cb1 = lambda ret: self.removeTimer(timer)  # noqa: E731
				cb2 = lambda ret: self.editTimer(timer)  # noqa: E731
				cb3 = lambda ret: self.disableTimer(timer)  # noqa: E731
				cb4 = lambda ret: self.enableTimer(timer)  # noqa: E731
				menu = [
					(_("Delete Timer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb1),
					(_("Edit Timer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb2),
				]
				if timer.disabled:
					menu.append((_("Enable timer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb4))
				else:
					menu.append((_("Disable timer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb3))
			title = _("Select action for timer %s:") % event.getEventName()
		else:
			if not manual:
				cb1 = lambda ret: self.doRecordTimer(True)  # noqa: E731
				menu = [
					(_("Add RecordTimer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb1),
					(_("Add ZapTimer"), "CALLFUNC", self.ChoiceBoxCB, self.doZapTimer),
					(_("Add Zap+RecordTimer"), "CALLFUNC", self.ChoiceBoxCB, self.doZapRecordTimer),
					(_("Add AutoTimer"), "CALLFUNC", self.ChoiceBoxCB, self.addAutoTimerSilent),
				]
				title = "%s?" % event.getEventName()
			else:
				newEntry = RecordTimerEntry(service, checkOldTimers=True,
											dirname=preferredTimerPath(),
											*parseEvent(event))
				self.session.openWithCallback(self.finishedAdd, TimerEntry, newEntry)
		if title:
			self.ChoiceBoxDialog = self.session.instantiateDialog(
				ChoiceBox, text=title, choiceList=menu,
				buttonList=["red", "green", "yellow", "blue"],
				skinName="RecordTimerQuestion")
			pos = self[f"list{self.activeList}"].getSelectionPosition()
			posX = max(self.instance.position().x() + pos[0] - self.ChoiceBoxDialog.instance.size().width(), 0)
			posY = self.instance.position().y() + pos[1]
			posY += self[f"list{self.activeList}"].itemHeight - 2
			if posY + self.ChoiceBoxDialog.instance.size().height() > 720:
				posY -= self[f"list{self.activeList}"].itemHeight - 4 + self.ChoiceBoxDialog.instance.size().height()
			self.ChoiceBoxDialog.instance.move(ePoint(int(posX), int(posY)))
			self.showChoiceBoxDialog()

	def RemoveChoiceBoxCB(self, choice):
		self.closeChoiceBoxDialog()
		if choice:
			choice(self)

	def ChoiceBoxCB(self, choice):
		self.closeChoiceBoxDialog()
		if choice:
			try:
				choice()
			except Exception:
				pass

	def doRecordTimer(self, rec=False):
		self.doInstantTimer(0, 0)

	def doZapTimer(self):
		self.doInstantTimer(1, 0)

	def doZapRecordTimer(self):
		self.doInstantTimer(0, 1)

	def doInstantTimer(self, zap, zaprecord):
		event, service = self[f"list{self.activeList}"].getCurrent()[:2]
		if event is None:
			return
		newEntry = RecordTimerEntry(service, checkOldTimers=True,
									dirname=preferredTimerPath(),
									*parseEvent(event, isZapTimer=zap), justplay=zap)
		self.InstantRecordDialog = self.session.instantiateDialog(
			InstantRecordTimerEntry, newEntry, zap, zaprecord)
		retval = [True, self.InstantRecordDialog.retval()]
		self.session.deleteDialogWithCallback(self.finishedAdd, self.InstantRecordDialog, retval)

	def finishedAdd(self, answer):
		if isinstance(answer, bool) and answer:
			self.close(True)
			return
		if answer[0]:
			entry = answer[1]
			if entry.external:
				def fallbackInitDone():
					fallbackTimer.addTimer(entry, self.refreshlist)
				fallbackTimer = FallbackTimerList(self, fallbackInitDone)
			else:
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList is not None:
					# Try to auto-resolve simple conflicts by trimming margins.
					for x in simulTimerList:
						if x.setAutoincreaseEnd(entry):
							self.session.nav.RecordTimer.timeChanged(x)
					simulTimerList = self.session.nav.RecordTimer.record(entry)
					if simulTimerList is not None:
						if (not entry.repeated
								and not config.recording.margin_before.value
								and not config.recording.margin_after.value
								and len(simulTimerList) > 1):
							conflict_begin = simulTimerList[1].begin
							conflict_end = simulTimerList[1].end
							if conflict_begin == entry.end:
								entry.end -= 30
								simulTimerList = self.session.nav.RecordTimer.record(entry)
							elif entry.begin == conflict_end:
								entry.begin += 30
								simulTimerList = self.session.nav.RecordTimer.record(entry)
						if simulTimerList is not None:
							self.session.openWithCallback(
								self.finishSanityCorrection, TimerSanityConflict, simulTimerList)
			self.setTimerButtonText(_("Change Timer"))
			self.key_green_choice = self.REMOVE_TIMER
		else:
			self.setTimerButtonText(_("Add Timer"))
			self.key_green_choice = self.ADD_TIMER
		self.refreshlist()

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def getRecordEvent(self, serviceRefStr, event):
		# Checks both active and processed timers; also queries the record timer
		# image for standard isInTimer logic.
		recordEvent = None
		eventID = event.getEventId()
		for timer in self.session.nav.RecordTimer.timer_list + self.session.nav.RecordTimer.processed_timers:
			if timer.eit == eventID and timer.service_ref.ref.toCompareString() == serviceRefStr:
				recordEvent = timer
				break
		else:
			if self.session.nav.isRecordTimerImageStandard:
				isInTimer = self.session.nav.RecordTimer.isInTimer(
					eventID, event.getBeginTime(), event.getDuration(), serviceRefStr, True)
				if isInTimer and isInTimer[1] in (2, 7, 12):
					recordEvent = isInTimer[3]
		return recordEvent


	def showChoiceBoxDialog(self):
		self["okactions"].setEnabled(False)
		if "epgcursoractions" in self:
			self["epgcursoractions"].setEnabled(False)
		if "colouractions" in self:
			self["colouractions"].setEnabled(False)
		if "coloractions" in self:
			self["coloractions"].setEnabled(False)
		self["recordingactions"].setEnabled(False)
		self["epgactions"].setEnabled(False)
		self["dialogactions"].setEnabled(True)
		if "epgcatchupactions" in self:
			self["epgcatchupactions"].setEnabled(False)
		if "input_actions" in self:
			self["input_actions"].setEnabled(False)
		self.ChoiceBoxDialog.instantiateActionMap(True)
		self.ChoiceBoxDialog.show()

	def closeChoiceBoxDialog(self):
		self["dialogactions"].setEnabled(False)
		if self.ChoiceBoxDialog:
			self.ChoiceBoxDialog.instantiateActionMap(False)
			self.session.deleteDialog(self.ChoiceBoxDialog)
			self.ChoiceBoxDialog = None
		self["okactions"].setEnabled(True)
		if "epgcursoractions" in self:
			self["epgcursoractions"].setEnabled(True)
		if "colouractions" in self:
			self["colouractions"].setEnabled(True)
		if "coloractions" in self:
			self["coloractions"].setEnabled(True)
		self["recordingactions"].setEnabled(True)
		self["epgactions"].setEnabled(True)
		if "epgcatchupactions" in self and callable(self.catchupPlayerFunc):
			self["epgcatchupactions"].setEnabled(True)
		if "input_actions" in self:
			self["input_actions"].setEnabled(True)


	def onSelectionChanged(self):
		event, service = self[f"list{self.activeList}"].getCurrent()[:2]
		self["Event"].newEvent(event)
		self["Service"].newService(service.ref if service else None)
		self.updateEventViewDialog(event, service)

		if service is None or service.getServiceName() == "":
			if self.key_green_choice != self.EMPTY:
				self.setTimerButtonText("")
				self.key_green_choice = self.EMPTY
			return
		if event is None or event.getBeginTime() + event.getDuration() < time():
			if self.key_green_choice != self.EMPTY:
				self.setTimerButtonText("")
				self.key_green_choice = self.EMPTY
			return

		serviceRefStr = service.ref.toCompareString()
		isRecordEvent = self.getRecordEvent(serviceRefStr, event)
		if isRecordEvent and self.key_green_choice != self.REMOVE_TIMER:
			self.setTimerButtonText(_("Change Timer"))
			self.key_green_choice = self.REMOVE_TIMER
		elif not isRecordEvent and self.key_green_choice != self.ADD_TIMER:
			self.setTimerButtonText(_("Add Timer"))
			self.key_green_choice = self.ADD_TIMER

		if "epgcatchupactions" in self and callable(self.catchupPlayerFunc):
			self.setupKeyPlayButtonDisplay(event.getBeginTime(), service)


	def _dispatchEpgAction(self, action):
		# Core action table shared by all EPG types.
		common = {
			"addEditTimer": self.addEditTimer,
			"addEditTimerMenu": self.addEditTimerMenu,
			"addEditZapTimerSilent": self.addEditZapTimerSilent,
			"openIMDb": self.openIMDb,
			"openTMDb": self.openTMDb,
			"addEditAutoTimer": self.addAutoTimer,
			"openEPGSearch": self.openEPGSearch,
			"showMovies": self.showMovies,
			"sortEPG": self.sortEPG,
			"openTimerList": self.openTimerList,
			"openAutoTimerList": self.openAutoTimerList,
			"openEventView": self.openEventView,
			"openSingleEPG": self.openSingleEPG,
		}
		# Navigation actions that not every EPG type supports.
		common.update({x: getattr(self, x) for x in ("prevPage", "nextPage", "prevBouquet", "nextBouquet", "toggleBouquetList", "enterDateTime", "gotoPrimetime", "setBasetime") if hasattr(self, x)})
		# Graph and infobargraph treat channelup/down as 24-hour jumps.
		if self.type in (EPG_TYPE_GRAPH, EPG_TYPE_INFOBARGRAPH):
			dispatch = dict(common, forward24Hours=lambda: self.updEvent(+24), back24Hours=lambda: self.updEvent(-24))
		elif self.type == EPG_TYPE_VERTICAL:
			dispatch = dict(common, forward24Hours=self.setPlus24h, back24Hours=self.setMinus24h)
		else:
			dispatch = common
		func = dispatch.get(action)
		if func:
			func()


	def closeScreen(self, NOCLOSE=False):
		if self.type == EPG_TYPE_SINGLE:
			self.close()
			return
		if hasattr(self, "servicelist") and self.servicelist:
			selected_ref = str(ServiceReference(self.servicelist.getCurrentSelection()))
			current_ref = str(ServiceReference(
				self.session.nav.getCurrentlyPlayingServiceOrGroup()))
			if selected_ref != current_ref:
				self.servicelist.restoreRoot()
				self.servicelist.setCurrentSelection(
					self.session.nav.getCurrentlyPlayingServiceOrGroup())
		current = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if current and self.startRef and current.toString() != self.startRef.toString():
			if self.zapFunc and self.startRef and self.startBouquet:
				# Preview mode: restore the original service on exit.
				preview = (
					(self.type == EPG_TYPE_GRAPH and config.epgselection.grid.preview_mode.value) or
					(self.type == EPG_TYPE_MULTI and config.epgselection.multi.preview_mode.value) or
					(self.type in (EPG_TYPE_INFOBAR, EPG_TYPE_INFOBARGRAPH) and
						config.epgselection.infobar.preview_mode.value in ("1", "2")) or
					(self.type == EPG_TYPE_ENHANCED and config.epgselection.single.preview_mode.value) or
					(self.type == EPG_TYPE_VERTICAL and config.epgselection.vertical.preview_mode.value)
				)
				if preview:
					if "0:0:0:0:0:0:0:0:0" not in self.startRef.toString():
						self.zapFunc(None, zapback=True)
				elif "0:0:0:0:0:0:0:0:0" in self.startRef.toString():
					self.session.nav.playService(self.startRef)
				else:
					self.zapFunc(None, False)
		self.closeEventViewDialog()
		if self.type == EPG_TYPE_VERTICAL and NOCLOSE:
			return
		self.close(True)

	def stopTimers(self):
		self.refreshTimer.stop()
		self.NumberZapTimer.stop()

	def restorePiP(self):
		# Restores the PiP state that was saved at EPG open time.
		if self.session.pipshown:
			self.Oldpipshown = False
			self.session.pipshown = False
			del self.session.pip
		if self.Oldpipshown and hasattr(self.session, "pip"):
			self.session.pipshown = True

	def zap(self):
		# Zap to the currently selected service and close the EPG.
		if (self.session.nav.getCurrentlyPlayingServiceOrGroup()
				and "0:0:0:0:0:0:0:0:0" in
				self.session.nav.getCurrentlyPlayingServiceOrGroup().toString()):
			return
		if self.zapFunc:
			self.zapSelectedService()
			self.closeEventViewDialog()
			self.close(True)
		else:
			self.closeEventViewDialog()
			self.close()

	def zapTo(self):
		# Preview zap: zaps the service but stays in the EPG (for preview mode).
		# If the same service is selected twice, exits the EPG.
		if (self.session.nav.getCurrentlyPlayingServiceOrGroup()
				and "0:0:0:0:0:0:0:0:0" in
				self.session.nav.getCurrentlyPlayingServiceOrGroup().toString()):
			return
		if self.zapFunc:
			self.zapSelectedService(prev=True)
			self.refreshTimer.start(2000)
		if not self.currch or self.currch == self.prevch:
			if self.zapFunc:
				self.zapFunc(None, False)
				self.closeEventViewDialog()
				self.close("close")
			else:
				self.closeEventViewDialog()
				self.close()

	def zapSelectedService(self, prev=False):
		playing = self.session.nav.getCurrentlyPlayingServiceReference()
		currservice = playing.toString() if playing else None
		if self.session.pipshown:
			pipService = self.session.pip.getCurrentService()
			self.prevch = pipService.toString() if pipService else None
		else:
			self.prevch = currservice
		epgList = self[f"list{self.activeList}"]
		if hasattr(epgList, "getCurrentChangeCount") and epgList.getCurrentChangeCount():
			return
		service = epgList.getCurrent()[1]
		if service is None and self.type == EPG_TYPE_VERTICAL and self.myServices:
			service = ServiceReference(self.myServices[self["list"].getSelectionIndex() + self.activeList - 1][0])
		if service is None:
			return
		if self.type in (EPG_TYPE_INFOBAR, EPG_TYPE_INFOBARGRAPH) and config.epgselection.infobar.preview_mode.value == "2":
			if not prev:
				self.closePiP()
				self.zapFunc(service.ref, bouquet=self.getCurrentBouquet(), preview=False)
				return
			if not self.previewInPiP(service, currservice):
				return
		else:
			self.zapFunc(service.ref, bouquet=self.getCurrentBouquet(), preview=prev)
			playing = self.session.nav.getCurrentlyPlayingServiceReference()
			self.currch = playing.toString() if playing else None
		if hasattr(epgList, "setCurrentlyPlaying"):
			epgList.setCurrentlyPlaying(self.session.nav.getCurrentlyPlayingServiceOrGroup())

	def previewInPiP(self, service, currservice):
		# Infobar preview mode 2: preview in PiP, zap when the PiP service is selected again.
		# Returns False when it zapped instead of previewing.
		if not self.session.pipshown:
			from Screens.PictureInPicture import PictureInPicture
			self.session.pip = self.session.instantiateDialog(PictureInPicture)
			self.session.pip.show()
			self.session.pipshown = True
		pipRef = self.pipServiceRelation.get(str(service.ref))
		pipRef = eServiceReference(pipRef) if pipRef else service.ref
		if self.currch == pipRef.toString():
			self.closePiP()
			self.zapFunc(service.ref, bouquet=self.getCurrentBouquet(), preview=False)
			return False
		if self.prevch != pipRef.toString() and currservice != pipRef.toString():
			self.session.pip.playService(pipRef)
			pipService = self.session.pip.getCurrentService()
			self.currch = pipService.toString() if pipService else None
		return True

	def closePiP(self):
		if self.session.pipshown:
			self.session.pipshown = False
			del self.session.pip


	def setTimerButtonText(self, text):
		# Update every color button that is configured to add/edit timers.
		for color in ("red", "green", "yellow", "blue"):
			if self._cfg.btn(color) == "addEditTimer":
				self[f"key_{color}"].setText(text)


	def OK(self):
		from Screens.InfoBar import InfoBar
		if InfoBar.instance.LongButtonPressed:
			return
		if self.zapnumberstarted:
			self.dozumberzap()
			return
		action = self._cfg.ok
		if action == "openEventView":
			self.openEventView()
		elif action == "zap":
			self.zapTo()
		elif action == "zapExit":
			self.zap()

	def OKLong(self):
		from Screens.InfoBar import InfoBar
		if not InfoBar.instance.LongButtonPressed:
			return
		if self.zapnumberstarted:
			self.dozumberzap()
			return
		action = self._cfg.oklong
		if action == "openEventView":
			self.openEventView()
		elif action == "zap":
			self.zapTo()
		elif action == "zapExit":
			self.zap()


	def Info(self):
		from Screens.InfoBar import InfoBar
		if InfoBar.instance.LongButtonPressed:
			return
		if self._cfg.info == "openSingleEPG":
			self.openSingleEPG()
		else:
			self.openEventView()

	def InfoLong(self):
		from Screens.InfoBar import InfoBar
		if not InfoBar.instance.LongButtonPressed:
			return
		if self._cfg.infolong == "openEventView":
			self.openEventView()
		else:
			self.openSingleEPG()

	def epgButtonPressed(self):
		from Screens.InfoBar import InfoBar
		if not InfoBar.instance.LongButtonPressed:
			self.epgButtonAction(self._cfg.epg)

	def epgButtonPressedLong(self):
		from Screens.InfoBar import InfoBar
		if InfoBar.instance.LongButtonPressed:
			self.epgButtonAction(self._cfg.epglong)

	def epgButtonAction(self, action):
		# A single EPG of the single EPG makes no sense, show the event info instead (as in the old EPGSelection).
		if action == "openEventView" or (action == "openSingleEPG" and self.type == EPG_TYPE_SINGLE):
			self.openEventView()
		elif action == "openSingleEPG":
			self.openSingleEPG()


	def keyNumberGlobal(self, number):
		# Starts or continues a number-zap sequence.
		self.zapnumberstarted = True
		self.NumberZapTimer.start(5000, True)
		if not self.NumberZapField:
			self["number"].setText(str(number))
			self["number"].show()
			self.NumberZapField = str(number)
		else:
			self.NumberZapField += str(number)
			self["number"].setText(self.NumberZapField)
			if len(self.NumberZapField) >= 4:
				self.dozumberzap()

	def dozumberzap(self):
		self.zapnumberstarted = False
		self.NumberZapTimer.stop()
		number = self.NumberZapField
		self.NumberZapField = None
		if "number" in self:
			self["number"].hide()
		if number is None:
			return
		# Search bouquets for a service matching the entered number.
		service, bouquet = self._getServiceByNumber(int(number))
		if service is not None:
			self.numberEntered(service, bouquet)

	def _getServiceByNumber(self, number):
		# Returns (service, bouquet) for the given channel number.
		# Searches all bouquets; uses alternative_number_mode if configured.
		if not self.bouquets:
			return None, None
		if config.usage.alternative_number_mode.value:
			services = self._getBouquetServices(self.getCurrentBouquet())
			for service in services:
				if service.ref.getChannelNum() == number:
					return service, self.getCurrentBouquet()
		else:
			for bouquet in self.bouquets:
				services = self._getBouquetServices(bouquet[1])
				for service in services:
					if service.ref.getChannelNum() == number:
						return service, bouquet[1]
		return None, None


	def togglePIG(self):
		if self.type == EPG_TYPE_VERTICAL:
			config.epgselection.vertical.pig.value = not config.epgselection.vertical.pig.value
			config.epgselection.vertical.pig.save()
			self.close("reopenvertical")
		else:
			config.epgselection.grid.pig.value = not config.epgselection.grid.pig.value
			config.epgselection.grid.pig.save()
			self.close("reopengraph")
		configfile.save()


	def refreshlist(self):
		self.refreshTimer.stop()

	def onCreate(self):
		pass

	def moveToService(self, service):
		self[f"list{self.activeList}"].moveToService(service)


	def setService(self, service):
		self.currentService = service
		self.onCreate()

	def setServices(self, services):
		self.services = services
		self.onCreate()

	def setServicelistSelection(self, bouquet, service):
		if self.servicelist:
			if self.servicelist.getRoot() != bouquet:
				self.servicelist.clearPath()
				self.servicelist.enterPath(self.servicelist.bouquet_root)
				self.servicelist.enterPath(bouquet)
			self.servicelist.setCurrentSelection(service)

	def isPlayable(self):
		# Returns True if the currently selected service in the servicelist is
		# a real playable service (not a marker or directory entry).
		current = ServiceReference(self.servicelist.getCurrentSelection())
		return not current.ref.flags & (eServiceReference.isMarker | eServiceReference.isDirectory)

	def applyButtonState(self, state):
		if state == 0:
			for key in ("now_button", "now_button_sel", "next_button", "next_button_sel",
						"more_button", "more_button_sel", "now_text", "next_text", "more_text"):
				if key in self:
					self[key].hide()
			if "key_red" in self:
				self["key_red"].setText("")
		else:
			for btn, sel in (("now_button", 1), ("next_button", 2), ("more_button", 3)):
				btn_sel = btn + "_sel"
				if btn in self and btn_sel in self:
					if state == sel:
						self[btn_sel].show()
						self[btn].hide()
					else:
						self[btn].show()
						self[btn_sel].hide()


mepg_config_initialized = False


class EPGServiceZap:
	def __init__(self, zapFunc):
		# Store the service that was playing when the EPG was opened so we can
		# restore it on close when in preview mode.
		# Single underscore so that concrete subclasses can access it without
		# Python name-mangling issues (double underscore would bind to EPGServiceZap).
		self._originalPlayingService = (
			self.session.nav.getCurrentlyPlayingServiceOrGroup() or eServiceReference())
		self.prevch = None
		self.currch = None
		self.zapFunc = zapFunc

class EPGServiceNumberSelection:
	def __init__(self):
		self["number"] = Label()
		self["number"].hide()
		helpMsg = _("Enter number to jump to channel")
		self["numberactions"] = HelpableNumberActionMap(self, "NumberActions",
			dict([(str(i), (self.keyNumberGlobal, helpMsg)) for i in range(0, 10)]),
			prio=-1, description=_("EPG Channel/Service Selection"))


	def numberEntered(self, service, bouquet):
		self.setBouquet(bouquet)
		if isinstance(self, EPGServiceBrowse):
			self.setCurrentService(service)
			self.serviceChanged()
		else:
			self.bouquetChanged()
			self.moveToService(service)


class EPGBouquetSelection:
	# Class-level variables shared across all EPG instances (same session).
	lastBouquet = None
	lastService = None
	lastPlaying = None

	def __init__(self, graphic):
		self.services = []
		self.selectedBouquetIndex = -1

		self["bouquetlist"] = EPGBouquetList(graphic)
		self["bouquetlist"].hide()
		self.bouquetlistActive = False

		self["bouquetokactions"] = ActionMap(["OkCancelActions"], {
			"cancel": self.__cancel,
			"OK": self.__OK,
		}, -1)
		self["bouquetokactions"].setEnabled(False)

		self["bouquetcursoractions"] = ActionMap(["DirectionActions"], {
			"left": self.moveBouquetPageUp,
			"right": self.moveBouquetPageDown,
			"up": self.moveBouquetUp,
			"down": self.moveBouquetDown,
		}, -1)
		self["bouquetcursoractions"].setEnabled(False)

		self.onClose.append(self.__onClose)

		# browse_mode "lastepgservice": restore the last EPG position on reopen.
		browseMode = getattr(self.epgConfig, "browse_mode", None)
		self.restoreLastService = browseMode is not None and browseMode.value == "lastepgservice"
		if self.restoreLastService:
			if (EPGBouquetSelection.lastPlaying and self.startRef
					and EPGBouquetSelection.lastBouquet
					and EPGBouquetSelection.lastPlaying == self.startRef):
				self.startBouquet = EPGBouquetSelection.lastBouquet
				self.startRef = EPGBouquetSelection.lastService
			EPGBouquetSelection.lastPlaying = self.session.nav.getCurrentlyPlayingServiceOrGroup()

	def __onClose(self):
		EPGSelectionBase.onSelectionChanged(self)
		if self.restoreLastService:
			EPGBouquetSelection.lastBouquet = self.getCurrentBouquet()
			if isinstance(self, EPGServiceBrowse):
				EPGBouquetSelection.lastService = self.getCurrentService()
			else:
				EPGBouquetSelection.lastService = self[f"list{self.activeList}"].getCurrent()[1]

	def getStartService(self):
		# Service to select when opening the EPG, see browse_mode.
		if self.restoreLastService and self.startRef:
			return self.startRef
		return self.session.nav.getCurrentlyPlayingServiceOrGroup()

	def selectFirstService(self):
		return getattr(self.epgConfig, "browse_mode", None) is not None and self.epgConfig.browse_mode.value == "firstservice"

	def _getBouquetServices(self, bouquet):
		if bouquet is None:
			return []
		from Screens.InfoBar import InfoBar
		if InfoBar.instance and InfoBar.instance.servicelist.isSubservices(bouquet):
			return [ServiceReference(ref) for ref in InfoBar.instance.servicelist.getSubservices()]
		servicelist = eServiceCenter.getInstance().list(bouquet)
		if servicelist is not None:
			services = []
			while True:
				service = servicelist.getNext()
				if not service.valid():
					break
				if service.flags & (eServiceReference.isDirectory | eServiceReference.isMarker):
					continue
				services.append(ServiceReference(service))
			return services
		return []

	getBouquetServices = _getBouquetServices

	def _populateBouquetList(self):
		self["bouquetlist"].recalcEntrySize()
		self["bouquetlist"].fillBouquetList(self.bouquets)
		self.setBouquet(self.startBouquet)

	def toggleBouquetList(self):
		if not self["bouquetlist"].skinAttributes:
			return
		if not self.bouquetlistActive:
			self.bouquetListShow()
		else:
			self.__cancel()

	def __OK(self):
		self.bouquetListHide()
		self.setBouquetIndex(self["bouquetlist"].instance.getCurrentIndex())
		self.bouquetChanged()

	def __cancel(self):
		self.bouquetListHide()
		self["bouquetlist"].setCurrentIndex(self.selectedBouquetIndex)

	def bouquetListShow(self):
		if "epgcursoractions" in self:
			self["epgcursoractions"].setEnabled(False)
		self["okactions"].setEnabled(False)
		self["bouquetlist"].setCurrentIndex(self.selectedBouquetIndex)
		self["bouquetlist"].show()
		self["bouquetokactions"].setEnabled(True)
		self["bouquetcursoractions"].setEnabled(True)
		self.bouquetlistActive = True

	def bouquetListHide(self):
		self["bouquetokactions"].setEnabled(False)
		self["bouquetcursoractions"].setEnabled(False)
		self["bouquetlist"].hide()
		self["okactions"].setEnabled(True)
		if "epgcursoractions" in self:
			self["epgcursoractions"].setEnabled(True)
		self.bouquetlistActive = False

	def moveBouquetUp(self):
		self["bouquetlist"].moveTo(self["bouquetlist"].instance.moveUp)

	def moveBouquetDown(self):
		self["bouquetlist"].moveTo(self["bouquetlist"].instance.moveDown)

	def moveBouquetPageUp(self):
		self["bouquetlist"].moveTo(self["bouquetlist"].instance.pageUp)

	def moveBouquetPageDown(self):
		self["bouquetlist"].moveTo(self["bouquetlist"].instance.pageDown)

	def getCurrentBouquet(self):
		if self.bouquets and self.selectedBouquetIndex >= 0:
			return self.bouquets[self.selectedBouquetIndex][1]
		return None

	def getCurrentBouquetName(self):
		if self.bouquets and self.selectedBouquetIndex >= 0:
			return self.bouquets[self.selectedBouquetIndex][0]
		return ""

	def nextBouquet(self):
		self.setBouquetIndex(self.selectedBouquetIndex + 1)
		self.bouquetChanged()

	def prevBouquet(self):
		self.setBouquetIndex(self.selectedBouquetIndex - 1)
		self.bouquetChanged()

	def setBouquetIndex(self, index):
		if not self.bouquets:
			return
		self.selectedBouquetIndex = index % len(self.bouquets)
		self.services = self._getBouquetServices(self.getCurrentBouquet())
		self.selectedServiceIndex = 0 if self.services else -1

	def setBouquet(self, bouquetRef):
		self.selectedBouquetIndex = 0
		if bouquetRef is not None:
			for i, bouquet in enumerate(self.bouquets):
				if bouquet[1] == bouquetRef:
					self.selectedBouquetIndex = i
					break
			else:  # The start bouquet (e.g. all services or a provider) is not in the bouquet list.
				self.bouquets = [(ServiceReference(bouquetRef).getServiceName(), bouquetRef)] + self.bouquets
				self["bouquetlist"].fillBouquetList(self.bouquets)
		self["bouquetlist"].setCurrentIndex(self.selectedBouquetIndex)
		self.services = self._getBouquetServices(bouquetRef)
		self.selectedServiceIndex = 0 if self.services else -1

	def getServiceByNumber(self, number):
		if config.usage.alternative_number_mode.value:
			for service in self.services:
				if service.ref.getChannelNum() == number:
					return service, self.getCurrentBouquet()
		else:
			for bouquet in self.bouquets:
				services = self._getBouquetServices(bouquet[1])
				for service in services:
					if service.ref.getChannelNum() == number:
						return service, bouquet[1]
		return None, None


class EPGServiceBrowse(EPGBouquetSelection):
	def __init__(self):
		# graphic=False: single/enhanced/infobar don't use the graphical bouquet list.
		EPGBouquetSelection.__init__(self, False)
		self.selectedServiceIndex = -1
		self.currentService = None

	def _populateBouquetList(self):
		EPGBouquetSelection._populateBouquetList(self)
		if not self.services:
			return
		self.setCurrentService(self.startRef)

	def setCurrentService(self, serviceRef):
		if serviceRef is None:
			self.selectedServiceIndex = 0
			return
		refstr = serviceRef.toString()
		for i, service in enumerate(self.services):
			if CompareWithAlternatives(service.ref.toString(), refstr):
				self.selectedServiceIndex = i
				return

	def bouquetChanged(self):
		self.serviceChanged()

	def getCurrentService(self):
		if self.selectedServiceIndex >= 0:
			return self.services[self.selectedServiceIndex]
		return eServiceReference()

	def nextService(self):
		self.moveService(+1)

	def prevService(self):
		self.moveService(-1)

	def moveService(self, direction):
		# Skips services without EPG data when "Skip empty services" is enabled.
		for x in range(max(len(self.services), 1)):
			self.selectedServiceIndex += direction
			if not 0 <= self.selectedServiceIndex < len(self.services):
				if config.usage.quickzap_bouquet_change.value and self.bouquets:
					self.selectedBouquetIndex = (self.selectedBouquetIndex + direction) % len(self.bouquets)
					self.services = self._getBouquetServices(self.getCurrentBouquet())
				self.selectedServiceIndex = (0 if direction > 0 else len(self.services) - 1) if self.services else -1
			self.serviceChanged()
			if not config.epgselection.overjump.value or self["list"].getCurrent()[1]:
				break
		service = self.getCurrentService()
		if self.servicelist and isinstance(service, ServiceReference):
			self.setServicelistSelection(self.getCurrentBouquet(), service.ref)


class EPGStandardButtons:

	def setActionButtonText(self, actionName, buttonText):
		if actionName == "addEditTimer":
			self["key_green"].setText(buttonText)
		elif actionName == "addEditAutoTimer":
			self["key_blue"].setText(buttonText)

	# --- Button wrapper methods, called at press time, read config then. ---

	def _btn_red(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		if not InfoBar.instance.LongButtonPressed:
			self._dispatchEpgAction(self._cfg.btn("red"))

	def _btn_redlong(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		if InfoBar.instance.LongButtonPressed:
			self._dispatchEpgAction(self._cfg.btn("red", long=True))

	def _btn_green(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		if not InfoBar.instance.LongButtonPressed:
			self._dispatchEpgAction(self._cfg.btn("green"))

	def _btn_greenlong(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		if InfoBar.instance.LongButtonPressed:
			self._dispatchEpgAction(self._cfg.btn("green", long=True))

	def _btn_yellow(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		if not InfoBar.instance.LongButtonPressed:
			self._dispatchEpgAction(self._cfg.btn("yellow"))

	def _btn_yellowlong(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		if InfoBar.instance.LongButtonPressed:
			self._dispatchEpgAction(self._cfg.btn("yellow", long=True))

	def _btn_blue(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		if not InfoBar.instance.LongButtonPressed:
			self._dispatchEpgAction(self._cfg.btn("blue"))

	def _btn_bluelong(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		if InfoBar.instance.LongButtonPressed:
			self._dispatchEpgAction(self._cfg.btn("blue", long=True))

	def _btn_rec(self):
		# rec/reclong are special: no closeEventViewDialog since the timer dialog
		# positions relative to the selection, and closing eventview first would
		# shift the list position.
		from Screens.InfoBar import InfoBar
		if not InfoBar.instance.LongButtonPressed:
			self._dispatchEpgAction(self._cfg.rec)

	def _btn_reclong(self):
		from Screens.InfoBar import InfoBar
		if InfoBar.instance.LongButtonPressed:
			self._dispatchEpgAction(self._cfg.reclong)

	def helpKeyAction(self, actionName):
		from Components.EpgConfig import okActions, recActions, infoActions, verticalActions
		_labels = {action_id: label for action_id, label, *_
					in verticalActions + okActions + recActions + infoActions}

		_color = {"red": "red", "redlong": "red",
					"green": "green", "greenlong": "green",
					"yellow": "yellow", "yellowlong": "yellow",
					"blue": "blue", "bluelong": "blue"}

		if actionName in _color:
			action_id = self._cfg.btn(_color[actionName], long=actionName.endswith("long"))
			help_text = _labels.get(action_id) or _("Do nothing")
		elif actionName == "rec":
			help_text = _labels.get(self._cfg.rec) or _("Do nothing")
		elif actionName == "reclong":
			help_text = _labels.get(self._cfg.reclong) or _("Do nothing")
		else:
			help_text = {
				"ok": _("Zap to channel (setup in menu)"),
				"oklong": _("Zap to channel and close (setup in menu)"),
				"epg": _("Show single EPG for current channel"),
				"epglong": "",
				"info": _("Show detailed event info (setup in menu)"),
				"infolong": _("Show single EPG for current channel (setup in menu)"),
			}.get(actionName, "")

		fn_map = {
			"red": self._btn_red, "redlong": self._btn_redlong,
			"green": self._btn_green, "greenlong": self._btn_greenlong,
			"yellow": self._btn_yellow, "yellowlong": self._btn_yellowlong,
			"blue": self._btn_blue, "bluelong": self._btn_bluelong,
			"ok": self.OK, "oklong": self.OKLong,
			"rec": self._btn_rec, "reclong": self._btn_reclong,
			"epg": self.epgButtonPressed, "epglong": self.epgButtonPressedLong,
			"info": self.Info, "infolong": self.InfoLong,
		}
		return (fn_map.get(actionName, lambda: None), help_text)

	def _updateButtonText(self):
		# Show the label of the configured action on each color button.
		from Components.EpgConfig import verticalActions  # All color button actions.
		labels = {x[0]: x[1] for x in verticalActions}
		labels[""] = ""
		for color in ("red", "green", "yellow", "blue"):
			self[f"key_{color}"].setText(labels.get(self._cfg.btn(color), ""))


class EPGSelectionGrid(EPGSelectionBase, EPGBouquetSelection, EPGServiceZap, EPGStandardButtons):
	"""Graphical grid EPG screen (EPG_TYPE_GRAPH and the infobar EPG_TYPE_INFOBARGRAPH)."""

	def __init__(self, session, zapFunc=None, startBouquet=None,
					startRef=None, bouquets=None, graphic=False, epgType=EPG_TYPE_GRAPH):
		self.type = epgType
		self._cfg = EPGSettings(epgType)
		self.activeList = ""
		epgConfig = config.epgselection.infobar if epgType == EPG_TYPE_INFOBARGRAPH else config.epgselection.grid

		# Initial start time aligned to roundto boundary.
		now = time() - epgConfig.histminutes.value * 60
		self.ask_time = now - now % (epgConfig.roundto.value * 60)

		EPGSelectionBase.__init__(self, session, epgConfig, startBouquet, startRef, bouquets)
		if epgType == EPG_TYPE_INFOBARGRAPH:
			self.skinName = "GraphicalInfoBarEPG"
		else:
			self.skinName = "GraphicalEPGPIG" if epgConfig.pig.value else "GraphicalEPG"
		EPGServiceZap.__init__(self, zapFunc)
		# graphic=True: graphical bouquet list (channel logos alongside names).
		EPGBouquetSelection.__init__(self, graphic)

		self["list"] = EPGListGrid(session, epgConfig, epgType, self.onSelectionChanged,
									graphic=graphic,
									overjump_empty=config.epgselection.overjump.value,
									time_epoch=epgConfig.prevtimeperiod.value)

		# Opt-in: skins can request Label widgets instead of Pixmap for the
		# timeline graphics, e.g. to apply icon-font glyphs.
		graphicControl = Label if parameters.get("EPGNativeControls", 0) else Pixmap

		# Timeline text widget labels the time axis above the event grid.
		self["timeline_text"] = TimelineText(epgType=epgType, graphic=graphic)
		self["primetime"] = Label(_("PRIMETIME"))
		self["change_bouquet"] = Label(_("CHANGE BOUQUET"))
		self["jump"] = Label(_("JUMP 24 HOURS"))
		self["page"] = Label(_("PAGE UP/DOWN"))
		self["timeline_now"] = graphicControl()

		# Pixmap slots for vertical "now" and interval tick markers.
		self.time_lines = []
		for i in range(MAX_TIMELINES):
			pm = graphicControl()
			self.time_lines.append(pm)
			self[f"timeline{i}"] = pm

		# Re-fire moveTimeLines every minute to slide the "now" marker.
		self.updateTimelineTimer = eTimer()
		self.updateTimelineTimer.callback.append(self.moveTimeLines)
		self.updateTimelineTimer.start(60000)
		self.onClose.append(self.updateTimelineTimer.stop)

		# Number keys 0-9 drive graph navigation (epoch, time-jump, primetime).
		# No channel-number zap in graph mode.
		numberActions = {
			"1": (lambda: self._numberKeyPressed(1), _("Reduce time scale")),
			"2": (lambda: self._numberKeyPressed(2), _("Page up")),
			"3": (lambda: self._numberKeyPressed(3), _("Increase time scale")),
			"4": (lambda: self._numberKeyPressed(4), _("Page left")),
			"5": (lambda: self._numberKeyPressed(5), _("Jump to current time")),
			"6": (lambda: self._numberKeyPressed(6), _("Page right")),
			"8": (lambda: self._numberKeyPressed(8), _("Page down")),
			"9": (lambda: self._numberKeyPressed(9), _("Jump to prime time")),
			"0": (lambda: self._numberKeyPressed(0), _("Goto first channel")),
		}
		if epgType == EPG_TYPE_GRAPH:
			numberActions["7"] = (lambda: self._numberKeyPressed(7), _("No of items switch (increase or reduced)"))
		self["input_actions"] = HelpableNumberActionMap(self, "NumberActions", numberActions, prio=-1, description=_("EPG Navigation Actions"))

		self.addEpgActions({
			"info": (self.Info, _("Show detailed event info")),
			"infolong": (self.InfoLong, _("Show single EPG for current channel")),
			"menu": (self.createMenu, _("Setup menu")),
			"nextBouquet": (self.nextBouquet, _("Goto next bouquet")),
			"prevBouquet": (self.prevBouquet, _("Goto previous bouquet")),
			"input_date_time": (self.enterDateTime, _("Goto specific date/time")),
			"nextService": (self.nextService, _("CHANNEL+ button (setup in menu)")),
			"prevService": (self.prevService, _("CHANNEL- button (setup in menu)")),
			"epg": (self.epgButtonPressed, _("Show single EPG for current channel")),
			"epglong": (self.epgButtonPressedLong, _("EPG button long (setup in menu)")),
			"tv": (self.toggleBouquetList, _("Toggle between bouquet/EPG lists")),
			"tvlong": (self.togglePIG, _("Toggle Picture in Graphics")),
		})
		self.addCursorActions({
			"left": (self.leftPressed, _("Goto previous event")),
			"right": (self.rightPressed, _("Goto next event")),
		})


	def onCreate(self):
		if self.type == EPG_TYPE_GRAPH and "primetime" in self.epgConfig.startmode.value:
			pt = self.epgConfig.primetime.value
			now = time() - self.epgConfig.histminutes.value * 60
			base = localtime(now - now % (self.epgConfig.roundto.value * 60))
			self.ask_time = mktime((base[0], base[1], base[2], pt[0], pt[1], 0,
									base[6], base[7], base[8]))
			if self.ask_time + 3600 < time():
				self.ask_time += 86400

		self._populateBouquetList()
		self["list"].recalcEntrySize()
		serviceref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self["list"].fillGraphEPG(self.services, self.ask_time)
		self["list"].setCurrentlyPlaying(serviceref)
		self["list"].moveToService(self.getStartService())
		self["list"].fillGraphEPG(None, self.ask_time, True)
		self["list"].setShowServiceMode(self.epgConfig.servicetitle_mode.value)
		if (self.type == EPG_TYPE_GRAPH and "channel1" in self.epgConfig.startmode.value) or self.selectFirstService():
			self["list"].instance.moveSelectionTo(0)
		self.moveTimeLines(True)
		self.onSelectionChanged()

	def refreshlist(self):
		self.ask_time = self["list"].getTimeBase()
		self["list"].fillGraphEPG(None, self.ask_time)
		self.moveTimeLines()
		self.onSelectionChanged()


	def moveTimeLines(self, force=False):
		self.updateTimelineTimer.start((60 - int(time()) % 60) * 1000)
		self["timeline_text"].setEntries(self["list"], self["timeline_now"],
											self.time_lines, force)
		self["list"].l.invalidate()


	def moveUp(self):
		self["list"].moveUp()
		self.moveTimeLines(True)

	def moveDown(self):
		self["list"].moveDown()
		self.moveTimeLines(True)

	def nextPage(self):
		self["list"].nextPage()

	def prevPage(self):
		if self["list"].listFirstServiceIndex != 0:
			# The list scrolls the services itself, page up only when not at the top.
			self["list"].prevPage()
		else:
			self["list"].moveTo(self["list"].instance.pageUp)

	def updEvent(self, direction, visible=True):
		if self["list"].selEntry(direction, visible):
			self.moveTimeLines(True)


	def nextBouquet(self):
		self._moveBouquetAndFill(+1)

	def prevBouquet(self):
		self._moveBouquetAndFill(-1)

	def _moveBouquetAndFill(self, direction):
		n = len(self.bouquets)
		if not n:
			return
		self.selectedBouquetIndex = (self.selectedBouquetIndex + direction) % n
		self.services = self._getBouquetServices(self.getCurrentBouquet())
		cfg = self.epgConfig
		now = time() - cfg.histminutes.value * 60
		self.ask_time = now - now % (cfg.roundto.value * 60)
		if self.type == EPG_TYPE_GRAPH and "primetime" in cfg.startmode.value:
			pt = cfg.primetime.value
			base = localtime(self.ask_time)
			self.ask_time = mktime((base[0], base[1], base[2], pt[0], pt[1], 0,
									base[6], base[7], base[8]))
			if self.ask_time + 3600 < time():
				self.ask_time += 86400
		self["list"].resetOffset()
		self["list"].fillGraphEPG(self.services, self.ask_time)
		serviceref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self["list"].fillGraphEPG(None, self.ask_time, True)
		self["list"].moveToService(serviceref)
		name = self.getCurrentBouquetName()
		self.setTitle(name)
		self.moveTimeLines(True)


	def _onDateTimeEntered(self, jumpTime):
		cfg = self.epgConfig
		jumpTime -= jumpTime % (cfg.roundto.value * 60)
		self["list"].resetOffset()
		self["list"].fillGraphEPG(None, jumpTime)
		self.moveTimeLines(True)
		self.ask_time = jumpTime


	def _numberKeyPressed(self, number):
		cfg = self.epgConfig
		now = time() - cfg.histminutes.value * 60

		if number == 1:
			period = int(cfg.prevtimeperiod.value)
			if period > 60:
				period -= 60
				self["list"].setEpoch(period)
				cfg.prevtimeperiod.setValue(period)
				self.moveTimeLines()

		elif number == 2:
			self.prevPage()

		elif number == 3:
			period = int(cfg.prevtimeperiod.value)
			if period < 300:
				period += 60
				self["list"].setEpoch(period)
				cfg.prevtimeperiod.setValue(period)
				self.moveTimeLines()

		elif number == 4:
			self.updEvent(-2)

		elif number == 5:
			self.ask_time = now - now % (cfg.roundto.value * 60)
			self["list"].resetOffset()
			self["list"].fillGraphEPG(None, self.ask_time, True)
			self.moveTimeLines(True)

		elif number == 6:
			self.updEvent(+2)

		elif number == 7 and self.type == EPG_TYPE_GRAPH:
			# Toggle compact/expanded row height.
			cfg.heightswitch.setValue(not cfg.heightswitch.value)
			self["list"].setItemsPerPage()
			self["list"].fillGraphEPG(None)
			self.moveTimeLines()

		elif number == 8:
			self.nextPage()

		elif number == 9:
			pt = cfg.primetime.value
			base = localtime(self["list"].getTimeBase())
			self.ask_time = mktime((base[0], base[1], base[2], pt[0], pt[1], 0,
									base[6], base[7], base[8]))
			if self.ask_time + 3600 < time():
				self.ask_time += 86400
			self["list"].resetOffset()
			self["list"].fillGraphEPG(None, self.ask_time)
			self.moveTimeLines(True)

		elif number == 0:
			self.ask_time = now - now % (cfg.roundto.value * 60)
			self["list"].instance.moveSelectionTo(0)
			self["list"].resetOffset()
			self["list"].fillGraphEPG(None, self.ask_time, True)
			self.moveTimeLines()


	def sortEPG(self):
		pass

	def leftPressed(self):
		self.updEvent(-1)

	def rightPressed(self):
		self.updEvent(+1)

	def nextService(self):
		self.channelButton(config.epgselection.grid.btn_channelup.value)

	def prevService(self):
		self.channelButton(config.epgselection.grid.btn_channeldown.value)

	def channelButton(self, action):
		func = {
			"forward24Hours": lambda: self.updEvent(+24),
			"back24Hours": lambda: self.updEvent(-24),
			"nextPage": self.nextPage,
			"prevPage": self.prevPage,
			"nextBouquet": self.nextBouquet,
			"prevBouquet": self.prevBouquet,
		}.get(action)
		if func:
			func()

	def bouquetChanged(self):
		self._moveBouquetAndFill(0)


class EPGSelectionInfobarGrid(EPGSelectionGrid):
	"""Infobar graphical grid EPG screen (EPG_TYPE_INFOBARGRAPH)."""

	def __init__(self, session, zapFunc=None, startBouquet=None, startRef=None, bouquets=None, graphic=False):
		EPGSelectionGrid.__init__(self, session, zapFunc, startBouquet, startRef, bouquets, graphic, EPG_TYPE_INFOBARGRAPH)


class EPGSelectionMulti(EPGSelectionBase, EPGServiceNumberSelection,
						EPGBouquetSelection, EPGServiceZap, EPGStandardButtons):
	"""Multi-service EPG screen (EPG_TYPE_MULTI)."""

	def __init__(self, session, zapFunc=None, startBouquet=None,
					startRef=None, bouquets=None):
		self.type = EPG_TYPE_MULTI
		self._cfg = EPGSettings(EPG_TYPE_MULTI)
		self.activeList = ""
		self.ask_time = -1

		EPGSelectionBase.__init__(self, session, config.epgselection.multi,
									startBouquet, startRef, bouquets)
		self.skinName = "EPGSelectionMulti"
		EPGServiceZap.__init__(self, zapFunc)
		# EPGBouquetSelection uses graphic=True for the visual bouquet list.
		EPGBouquetSelection.__init__(self, True)
		EPGServiceNumberSelection.__init__(self)

		self["list"] = EPGListMulti(session, config.epgselection.multi,
									self.onSelectionChanged)
		graphicControl = Label if parameters.get("EPGNativeControls", 0) else Pixmap
		for key in ("now_button", "next_button", "more_button",
					"now_button_sel", "next_button_sel", "more_button_sel"):
			self[key] = graphicControl()
		for key in ("now_text", "next_text", "more_text", "date"):
			self[key] = Label()

		self.addEpgActions({
			"info": (self.Info, _("Show detailed event info")),
			"infolong": (self.InfoLong, _("Show single EPG for current channel")),
			"menu": (self.createMenu, _("Setup menu")),
			"nextBouquet": (self.nextBouquet, _("Goto next bouquet")),
			"prevBouquet": (self.prevBouquet, _("Goto previous bouquet")),
			"nextService": (self.prevPage, _("Page up")),
			"prevService": (self.nextPage, _("Page down")),
			"input_date_time": (self.enterDateTime, _("Goto specific date/time")),
			"epg": (self.epgButtonPressed, _("Show single EPG for current channel")),
			"epglong": (self.epgButtonPressedLong, _("EPG button long (setup in menu)")),
			"tv": (self.toggleBouquetList, _("Toggle between bouquet/EPG lists")),
		})
		self.addCursorActions({
			"left": (self.leftPressed, _("Goto previous event")),
			"right": (self.rightPressed, _("Goto next event")),
		})


	def onCreate(self):
		self._populateBouquetList()
		self.setTitle(self.getCurrentBouquetName())
		self._fillList()
		self.onSelectionChanged()

	def onSelectionChanged(self):
		count = self["list"].getCurrentChangeCount()
		if self.ask_time != -1:
			self.applyButtonState(0)
		elif count > 1:
			self.applyButtonState(3)
		elif count > 0:
			self.applyButtonState(2)
		else:
			self.applyButtonState(1)
		event = self["list"].getCurrent()[0]
		datestr = ""
		if event is not None:
			begTime = localtime(event.getBeginTime())
			datestr = _("Today") if localtime()[2] == begTime[2] else strftime(config.usage.date.dayshort.value, begTime)
		self["date"].setText(datestr)
		EPGSelectionBase.onSelectionChanged(self)

	def _fillList(self):
		self["list"].recalcEntrySize()
		self["list"].fillMultiEPG(self.services, self.ask_time)
		if self.selectFirstService():
			self["list"].setCurrentIndex(0)
		else:
			self["list"].moveToService(self.getStartService())

	def refreshlist(self):
		curr = self["list"].getCurrentChangeCount()
		self["list"].fillMultiEPG(self.services, self.ask_time)
		for _ in range(curr):
			self["list"].updateMultiEPG(1)
		self.onSelectionChanged()


	def bouquetChanged(self):
		bouquet = self.getCurrentBouquet()
		if bouquet:
			self.services = self._getBouquetServices(bouquet)
			self.setTitle(self.getCurrentBouquetName())
			self["list"].fillMultiEPG(self.services, self.ask_time)


	def leftPressed(self):
		self["list"].updateMultiEPG(-1)

	def rightPressed(self):
		self["list"].updateMultiEPG(1)

	def _onDateTimeEntered(self, jumpTime):
		self.ask_time = jumpTime
		self["list"].fillMultiEPG(self.services, jumpTime)
class EPGSelectionSimilar(EPGSelectionBase, EPGServiceZap, EPGStandardButtons):
	"""Similar-events EPG screen (EPG_TYPE_SIMILAR)."""

	def __init__(self, session, service, eventid, zapFunc=None):
		self.type = EPG_TYPE_SIMILAR
		self._cfg = EPGSettings(EPG_TYPE_SIMILAR)
		self.activeList = ""

		# Convert str/eServiceReference to ServiceReference.
		if isinstance(service, str):
			self.currentService = ServiceReference(service)
		elif hasattr(service, "ref"):
			self.currentService = service
		else:
			self.currentService = ServiceReference(service)
		self.eventid = eventid

		# No bouquets for similar EPG, pass empty/None values.
		EPGSelectionBase.__init__(self, session, config.epgselection.single, None, None, None)
		self.skinName = "EPGSelection"
		EPGServiceZap.__init__(self, zapFunc)

		self["list"] = EPGListSingle(session, config.epgselection.single,
										EPG_TYPE_SIMILAR, self.onSelectionChanged)

		self.addEpgActions({
			"info": (self.Info, _("Show detailed event info")),
			"infolong": (self.InfoLong, _("Show detailed event info")),
			"menu": (self.createMenu, _("Setup menu")),
		})

	def onCreate(self):
		self.setTitle(_("EPG Selection"))
		self["list"].fillSimilarList(self.currentService.toString(), self.eventid)
		self.onSelectionChanged()

	def refreshlist(self):
		self["list"].fillSimilarList(self.currentService.toString(), self.eventid)
		self.onSelectionChanged()

	def getCurrentBouquet(self):
		return self.startBouquet
class EPGSelectionSingle(EPGSelectionBase, EPGServiceNumberSelection,
							EPGServiceBrowse, EPGServiceZap, EPGStandardButtons):
	"""Single-channel EPG screen (EPG_TYPE_SINGLE / EPG_TYPE_ENHANCED)."""

	def __init__(self, session, zapFunc=None, startBouquet=None,
					startRef=None, bouquets=None, epgType=EPG_TYPE_SINGLE, serviceChangeCB=None):
		self.serviceChangeCB = serviceChangeCB
		# Must be set before EPGSelectionBase.__init__: helpKeyAction() reads self._cfg.
		self.type = epgType
		self._cfg = EPGSettings(epgType)
		self.activeList = ""  # not vertical

		epgConfig = config.epgselection.infobar if epgType == EPG_TYPE_INFOBAR else config.epgselection.single
		EPGSelectionBase.__init__(self, session, epgConfig, startBouquet, startRef, bouquets)
		self.skinName = "QuickEPG" if epgType == EPG_TYPE_INFOBAR else "EPGSelection"
		# The zap mixin needs self.session.nav (available after Screen.__init__).
		EPGServiceZap.__init__(self, zapFunc)
		# The browse/bouquet mixin needs self.epgConfig and self.startRef.
		EPGServiceBrowse.__init__(self)
		# Number key action map.
		EPGServiceNumberSelection.__init__(self)

		# onSelectionChanged (from base) updates Event/Service widgets + green button.
		self["list"] = EPGListSingle(session, epgConfig, epgType, self.onSelectionChanged)
		self.createActions()

	def createActions(self):
		self.addEpgActions({
			"epg": (self.epgButtonPressed, _("Show detailed event info") if self.type == EPG_TYPE_SINGLE else _("Show single EPG for current channel")),
			"epglong": (self.epgButtonPressedLong, _("EPG button long (setup in menu)")),
			"info": (self.Info, _("Show detailed event info")),
			"menu": (self.createMenu, _("Setup menu")),
			"nextService": (self.nextService, _("Goto next channel")),
			"prevService": (self.prevService, _("Goto previous channel")),
		})
		if self.type == EPG_TYPE_ENHANCED:
			self.addEpgActions({
				"infolong": (self.InfoLong, _("Show single EPG for current channel")),
				"nextBouquet": (self.nextBouquet, _("Goto next bouquet")),
				"prevBouquet": (self.prevBouquet, _("Goto previous bouquet")),
				"input_date_time": (self.enterDateTime, _("Goto specific date/time")),
			})
		self.addCursorActions({
			"left": (self.prevPage, _("Page up")),
			"right": (self.nextPage, _("Page down")),
		})


	def onCreate(self):
		self.setTitle(_("EPG Selection"))
		self._populateBouquetList()
		self._fillList(self.startRef)
		self.onSelectionChanged()
		self.startRefreshTimer()


	def _fillList(self, serviceRef=None):
		sref = serviceRef or self._originalPlayingService
		if sref is None:
			return
		if not hasattr(sref, "ref"):
			sref = ServiceReference(sref)
		self.currentService = sref  # Old attribute, used by plugins like SeriesPlugin.
		name = sref.getServiceName()
		self.setTitle(name if self.type == EPG_TYPE_SINGLE else f"{self.getCurrentBouquetName()} - {name}")
		self["list"].fillSingleEPG(sref)
		self["list"].sortSingleEPG(int(config.epgselection.sort.value))

	def refreshlist(self):
		if self.currentService:
			index = self["list"].getCurrentIndex()
			self["list"].fillSingleEPG(self.currentService)
			self["list"].sortSingleEPG(int(config.epgselection.sort.value))
			self["list"].setCurrentIndex(index)
		self.onSelectionChanged()
		self.startRefreshTimer()

	def sortEPG(self):
		self.closeEventViewDialog()
		config.epgselection.sort.value = "1" if config.epgselection.sort.value == "0" else "0"
		config.epgselection.sort.save()
		configfile.save()
		self["list"].sortSingleEPG(int(config.epgselection.sort.value))


	def serviceChanged(self):
		service = self.getCurrentService()
		if service:
			self._fillList(service)

	def moveToService(self, service):
		self._fillList(service)


	def nextService(self):
		if self.type == EPG_TYPE_SINGLE and self.serviceChangeCB:
			self.serviceChangeCB(1, self)
		else:
			EPGServiceBrowse.nextService(self)

	def prevService(self):
		if self.type == EPG_TYPE_SINGLE and self.serviceChangeCB:
			self.serviceChangeCB(-1, self)
		else:
			EPGServiceBrowse.prevService(self)

	def setService(self, service):
		self.setCurrentService(service)
		self._fillList(service)
		self.onSelectionChanged()


	def startRefreshTimer(self):
		if hasattr(config.epg, "pollinterval"):
			self.refreshTimer.start(config.epg.pollinterval.value * 60 * 1000, True)
class EPGSelectionInfobarSingle(EPGSelectionSingle):
	"""Infobar single-channel EPG overlay (EPG_TYPE_INFOBAR text mode)."""

	def __init__(self, session, zapFunc=None, startBouquet=None, startRef=None, bouquets=None):
		EPGSelectionSingle.__init__(self, session, zapFunc, startBouquet, startRef, bouquets, EPG_TYPE_INFOBAR)

	def createActions(self):
		self.addEpgActions({
			"info": (self.Info, _("Show detailed event info")),
			"infolong": (self.InfoLong, _("Show single EPG for current channel")),
			"menu": (self.createMenu, _("Setup menu")),
			"nextBouquet": (self.nextBouquet, _("Goto next bouquet")),
			"prevBouquet": (self.prevBouquet, _("Goto previous bouquet")),
			"input_date_time": (self.enterDateTime, _("Goto specific date/time")),
			"nextService": (self.prevPage, _("Page up")),
			"prevService": (self.nextPage, _("Page down")),
			"epg": (self.epgButtonPressed, _("Show single EPG for current channel")),
			"epglong": (self.epgButtonPressedLong, _("EPG button long (setup in menu)")),
		})
		self.addCursorActions({
			"left": (self.prevService, _("Goto previous channel")),
			"right": (self.nextService, _("Goto next channel")),
		})


class EPGSelectionVertical(EPGSelectionBase, EPGBouquetSelection,
							EPGServiceZap, EPGStandardButtons):
	"""Vertical multi-column EPG screen (EPG_TYPE_VERTICAL)."""

	def __init__(self, session, zapFunc=None, startBouquet=None,
					startRef=None, bouquets=None):
		self.type = EPG_TYPE_VERTICAL
		self._cfg = EPGSettings(EPG_TYPE_VERTICAL)
		# Fields=4 with PIG (3 visible channels), Fields=6 without (5 channels).
		self.Fields = 4 if config.epgselection.vertical.pig.value else 6
		self.activeList = 1  # column that has focus (1 … Fields-1)

		EPGSelectionBase.__init__(self, session, config.epgselection.vertical,
									startBouquet, startRef, bouquets)
		EPGServiceZap.__init__(self, zapFunc)
		EPGBouquetSelection.__init__(self, False)

		self.skinName = "EPGverticalPIG" if self.Fields == 4 else "EPGvertical"

		# Channel-position navigator (hidden from user; drives which services are
		# shown in each column).
		self["list"] = MenuList([])

		# Per-column picon, label, active-marker and EPG list widgets.
		for n in range(1, 6):
			self[f"piconCh{n}"] = ServiceEvent()
			self[f"currCh{n}"] = Label(" ")
			self[f"Active{n}"] = Label(" ")
			self[f"list{n}"] = EPGListVertical(session, config.epgselection.vertical,
												self.onSelectionChanged)

		self.myServices = []
		self.list = []
		self.ask_time = -1
		self.lastEventTime = (time(), time() + 3600)
		self.lastMinus = 0
		self.firststart = True

		from Components.ActionMap import HelpableNumberActionMap
		self["input_actions"] = HelpableNumberActionMap(self, "NumberActions", {
			"1": (lambda: self._numberKeyPressed(1), _("Goto first channel")),
			"2": (lambda: self._numberKeyPressed(2), _("All events up")),
			"3": (lambda: self._numberKeyPressed(3), _("Goto last channel")),
			"4": (lambda: self._numberKeyPressed(4), _("Previous channel page")),
			"0": (lambda: self._numberKeyPressed(0), _("Goto current channel and now")),
			"6": (lambda: self._numberKeyPressed(6), _("Next channel page")),
			"7": (lambda: self._numberKeyPressed(7), _("Goto now")),
			"8": (lambda: self._numberKeyPressed(8), _("All events down")),
			"9": (lambda: self._numberKeyPressed(9), _("Jump to prime time")),
			"5": (lambda: self._numberKeyPressed(5), _("Set Base Time")),
		}, prio=-1, description=_("EPG Navigation Actions"))

		self.addEpgActions({
			"info": (self.Info, _("Show detailed event info")),
			"infolong": (self.InfoLong, _("Show single EPG for current channel")),
			"menu": (self.createMenu, _("Setup menu")),
			"nextBouquet": (self.nextBouquet, _("Goto next bouquet")),
			"prevBouquet": (self.prevBouquet, _("Goto previous bouquet")),
			"input_date_time": (self.enterDateTime, _("Goto specific date/time")),
			"nextService": (self.nextPage, _("CHANNEL+ button (setup in menu)")),
			"prevService": (self.prevPage, _("CHANNEL- button (setup in menu)")),
			"epg": (self.epgButtonPressed, _("Show single EPG for current channel")),
			"epglong": (self.epgButtonPressedLong, _("EPG button long (setup in menu)")),
			"tv": (self.toggleBouquetList, _("Toggle between bouquet/EPG lists")),
			"tvlong": (self.togglePIG, _("Toggle Picture in Graphics")),
		})
		self.addCursorActions({
			"left": (self.leftPressed, _("Goto previous channel")),
			"right": (self.rightPressed, _("Goto next channel")),
		})


	def onCreate(self):
		self.ask_time = -1
		self.lastEventTime = (time(), time() + 3600)
		self._populateBouquetList()
		self["bouquetlist"].recalcEntrySize()
		self["bouquetlist"].fillBouquetList(self.bouquets)
		self["bouquetlist"].moveToService(self.startBouquet)
		self["bouquetlist"].setCurrentBouquet(self.startBouquet)
		self.setTitle(self.getCurrentBouquetName())
		self["list"].setList(self.getChannels())

		# Try to position on the currently playing channel.
		serviceref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		info = serviceref and serviceref.info()
		nameROH = info and info.getName().replace("\xc2\x86", "").replace("\xc2\x87", "")
		if nameROH and "channel1" not in config.epgselection.vertical.startmode.value:
			idx = 0
			for ch in self.myServices:
				idx += 1
				if ch[1] == nameROH:
					break
			page = idx // (self.Fields - 1)
			row = idx % (self.Fields - 1)
			if row:
				self.activeList = row
			else:
				page -= 1
				self.activeList = self.Fields - 1
			self["list"].moveToIndex(0)
			for _ in range(page):
				self["list"].pageDown()
		else:
			self["list"].moveToIndex(0)

		self["Service"].newService(serviceref)
		if self.firststart and "primetime" in config.epgselection.vertical.startmode.value:
			self.gotoPrimetime()
		else:
			self.updateVerticalEPG()
		self.firststart = False

	def refreshlist(self):
		curr = self[f"list{self.activeList}"].getSelectedEventId()
		svc = self.myServices[self["list"].getSelectionIndex() + self.activeList - 1][0] if self.myServices else None
		self.updateVerticalEPG()
		if curr and svc:
			self[f"list{self.activeList}"].moveToEventId(curr)
		self.onSelectionChanged()


	def moveUp(self):
		if config.epgselection.vertical.updownbtn.value:
			if self.getEventTime(self.activeList)[0] is None:
				return
			self.saveLastEventTime()
			idx = self[f"list{self.activeList}"].getCurrentIndex()
			if not idx:
				tmp = self.lastEventTime
				self.setMinus24h(True, 6)
				self.lastEventTime = tmp
				self.gotoLasttime()
			elif not idx % config.epgselection.vertical.itemsperpage.value:
				self.syncUp(idx)
		self[f"list{self.activeList}"].moveTo(
			self[f"list{self.activeList}"].instance.moveUp)
		self.saveLastEventTime()

	def moveDown(self):
		if config.epgselection.vertical.updownbtn.value:
			idx = self[f"list{self.activeList}"].getCurrentIndex()
			if not (idx + 1) % config.epgselection.vertical.itemsperpage.value:
				self.syncDown(idx + 1)
		self[f"list{self.activeList}"].moveTo(
			self[f"list{self.activeList}"].instance.moveDown)
		self.saveLastEventTime()

	def nextPage(self, numberkey=False, reverse=False):
		if not numberkey and "scroll" in config.epgselection.vertical.channelbtn.value:
			if config.epgselection.vertical.channelbtn_invert.value:
				self.allDown()
			else:
				self.allUp()
		elif not numberkey and "24" in config.epgselection.vertical.channelbtn.value:
			if config.epgselection.vertical.channelbtn_invert.value:
				self.setPlus24h()
			else:
				self.setMinus24h()
		else:
			if not numberkey and not reverse and config.epgselection.vertical.channelbtn_invert.value:
				self.prevPage(reverse=True)
				return
			if len(self.list) <= self["list"].getSelectionIndex() + self.Fields - 1:
				self.gotoFirst()
			else:
				self["list"].pageDown()
				self.activeList = 1
				self.updateVerticalEPG()
			self.gotoLasttime()

	def prevPage(self, numberkey=False, reverse=False):
		if not numberkey and "scroll" in config.epgselection.vertical.channelbtn.value:
			if config.epgselection.vertical.channelbtn_invert.value:
				self.allUp()
			else:
				self.allDown()
		elif not numberkey and "24" in config.epgselection.vertical.channelbtn.value:
			if config.epgselection.vertical.channelbtn_invert.value:
				self.setMinus24h()
			else:
				self.setPlus24h()
		else:
			if not numberkey and not reverse and config.epgselection.vertical.channelbtn_invert.value:
				self.nextPage(reverse=True)
				return
			if self["list"].getSelectionIndex() == 0:
				self.gotoLast()
			else:
				self["list"].pageUp()
				self.activeList = self.Fields - 1
				self.updateVerticalEPG()
			self.gotoLasttime()

	def leftPressed(self):
		first = not self["list"].getSelectionIndex() and self.activeList == 1
		if self.activeList > 1 and not first:
			self.activeList -= 1
			self.displayActiveEPG()
		else:
			if first:
				self.gotoLast()
			else:
				self["list"].pageUp()
				self.activeList = self.Fields - 1
				self.updateVerticalEPG()
			self.gotoLasttime()
		self.onSelectionChanged()

	def rightPressed(self):
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


	def nextBouquet(self):
		self._moveBouquetAndFill(+1)

	def prevBouquet(self):
		self._moveBouquetAndFill(-1)

	def bouquetChanged(self):
		self._moveBouquetAndFill(0)

	def _moveBouquetAndFill(self, direction):
		n = len(self.bouquets)
		if not n:
			return
		self.selectedBouquetIndex = (self.selectedBouquetIndex + direction) % n
		self.services = self._getBouquetServices(self.getCurrentBouquet())
		self["list"].setList(self.getChannels())
		self.gotoFirst()
		self.setTitle(self.getCurrentBouquetName())


	def _onDateTimeEntered(self, jumpTime):
		if jumpTime > time():
			self.ask_time = jumpTime
			self.updateVerticalEPG()
		else:
			self.ask_time = -1


	def _numberKeyPressed(self, number):
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


	def getChannels(self):
		self.list = []
		self.myServices = []
		idx = 0
		for service in self.services:
			idx += 1
			info = service.info()
			name = info.getName(service.ref).replace("\xc2\x86", "").replace("\xc2\x87", "")
			self.list.append(f"{idx}. {name}")
			self.myServices.append((service.ref.toString(), name))
		if not idx:
			self.list.append("")
			self.myServices.append(("", ""))
		return self.list

	def getActivePrg(self):
		return self["list"].getSelectionIndex() + (self.activeList - 1)


	def updateVerticalEPG(self, force=False):
		self.displayActiveEPG()
		stime = None
		now = time()
		if force or self.ask_time >= now - config.epg.histminutes.value * 60:
			stime = self.ask_time
		prgIndex = self["list"].getSelectionIndex()
		x = len(self.list) - 1

		for col in range(1, self.Fields):
			lkey = f"list{col}"
			pkkey = f"piconCh{col}"
			chkey = f"currCh{col}"
			if prgIndex < (x + 1) and self.myServices[prgIndex][0]:
				self[lkey].show()
				self[chkey].setText(str(self.myServices[prgIndex][1]))
				self[lkey].recalcEntrySize()
				svc = ServiceReference(self.myServices[prgIndex][0])
				self[pkkey].newService(svc.ref)
				self[lkey].fillVerticalEPG(svc, stime)
			else:
				if col > self.Fields - 1 or (col >= 4 and self.Fields < 6):
					self[f"Active{col}"].hide()
				self[pkkey].newService(None)
				self[chkey].setText(" ")
				self[lkey].hide()
			prgIndex += 1

	def displayActiveEPG(self):
		marker = config.epgselection.vertical.eventmarker.value
		for n in range(1, self.Fields):
			if n == self.activeList:
				self[f"list{n}"].selectionEnabled(True)
				self[f"Active{n}"].show()
			else:
				self[f"Active{n}"].hide()
				self[f"list{n}"].selectionEnabled(marker)


	def allUp(self):
		if self.getEventTime(self.activeList)[0] is None:
			return
		idx = self[f"list{self.activeList}"].getCurrentIndex()
		if not idx:
			tmp = self.lastEventTime
			self.setMinus24h(True, 6)
			self.lastEventTime = tmp
			self.gotoLasttime()
		for n in range(1, self.Fields):
			self[f"list{n}"].moveTo(self[f"list{n}"].instance.pageUp)
		self.syncUp(idx)
		self.saveLastEventTime()

	def allDown(self):
		if self.getEventTime(self.activeList)[0] is None:
			return
		for n in range(1, self.Fields):
			self[f"list{n}"].moveTo(self[f"list{n}"].instance.pageDown)
		idx = self[f"list{self.activeList}"].getCurrentIndex()
		self.syncDown(idx)
		self.saveLastEventTime()

	def syncUp(self, idx):
		idx = self[f"list{self.activeList}"].getCurrentIndex()
		curTime = self.getEventTime(self.activeList)[0]
		pages = int(idx / config.epgselection.vertical.itemsperpage.value)
		for n in range(1, self.Fields):
			if n == self.activeList:
				continue
			for _ in range(pages):
				evTime = self.getEventTime(n)[0]
				if curTime is None or evTime is None or curTime <= evTime:
					self[f"list{n}"].moveTo(self[f"list{n}"].instance.pageUp)
				evTime = self.getEventTime(n)[0]
				if curTime is None or evTime is None or curTime >= evTime:
					break

	def syncDown(self, idx):
		curTime = self.getEventTime(self.activeList)[0]
		pages = int(idx / config.epgselection.vertical.itemsperpage.value)
		for n in range(1, self.Fields):
			if n == self.activeList:
				continue
			for _ in range(pages):
				evTime = self.getEventTime(n)[0]
				if curTime is None or evTime is None or curTime >= evTime:
					self[f"list{n}"].moveTo(self[f"list{n}"].instance.pageDown)
				evTime = self.getEventTime(n)[0]
				if curTime is None or evTime is None or curTime <= evTime:
					break


	def getEventTime(self, n):
		tmp = self[f"list{n}"].l.getCurrentSelection()
		if tmp is None:
			return None, None
		return tmp[2], tmp[2] + tmp[3]

	def saveLastEventTime(self, n=0):
		if not n:
			n = self.activeList
		now = time()
		last = self.lastEventTime
		self.lastEventTime = self.getEventTime(n)
		if self.lastEventTime[0] is None and last[0] is not None:
			self.lastEventTime = last
		elif last[0] is None:
			self.lastEventTime = (now, now + 3600)

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
		for _ in range(page):
			self["list"].pageDown()
		self.updateVerticalEPG()

	def setPrimetime(self, stime):
		if stime is None:
			stime = time()
		t = localtime(stime)
		vpt = config.epgselection.vertical.primetime.value
		return mktime((t[0], t[1], t[2], vpt[0], vpt[1], 0, t[6], t[7], t[8]))

	def setPlus24h(self):
		oneDay = 24 * 3600
		ev_begin, ev_end = self.getEventTime(self.activeList)
		if ev_begin is not None:
			if self.findMaxEventTime(ev_begin + oneDay):
				primetime = self.setPrimetime(ev_begin)
				if ev_begin <= primetime < ev_end:
					self.ask_time = primetime + oneDay
				else:
					self.ask_time = ev_begin + oneDay
				self.updateVerticalEPG()
			else:
				self[f"list{self.activeList}"].moveTo(
					self[f"list{self.activeList}"].instance.moveEnd)
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
				if (self[f"list{self.activeList}"].getCurrentIndex()
						and not force
						and self.findMinEventTime(ev_begin - oneDay)):
					self.lastEventTime = ev_begin - oneDay, ev_end - oneDay
					self.gotoLasttime()
					return
				else:
					pt = 0
					if self.ask_time == ev_begin - self.lastMinus:
						self.lastMinus += self.lastMinus
					else:
						primetime = self.setPrimetime(ev_begin)
						if ev_begin <= primetime < ev_end:
							self.ask_time = pt = primetime - oneDay
						self.lastMinus = oneDay
					if not pt:
						self.ask_time = ev_begin - self.lastMinus
			self.updateVerticalEPG()
			self.saveLastEventTime()

	def setBasetime(self):
		ev_begin, _ = self.getEventTime(self.activeList)
		if ev_begin is not None:
			self.ask_time = ev_begin
			self.updateVerticalEPG()

	def gotoPrimetime(self):
		now = time()
		oneDay = 24 * 3600
		if self.firststart:
			self.ask_time = self.setPrimetime(now)
			self[f"list{self.activeList}"].moveTo(
				self[f"list{self.activeList}"].instance.moveTop)
			ev_begin = self.getEventTime(self.activeList)[0]
			if ev_begin is not None and ev_begin > self.ask_time:
				self.ask_time += oneDay
			self.updateVerticalEPG()
			self.saveLastEventTime()
			return
		ev_begin, ev_end = self.getEventTime(self.activeList)
		if ev_begin is None:
			return
		primetime = self.setPrimetime(ev_begin)
		rPM = self.isInTimeRange(primetime - oneDay)
		rPT = self.isInTimeRange(primetime)
		rPP = self.isInTimeRange(primetime + oneDay)
		if rPM or rPT or rPP:
			idx = sum(self[f"list{n}"].getCurrentIndex() for n in range(1, self.Fields))
			if idx or not (ev_begin <= primetime < ev_end):
				if rPT:
					self.ask_time = primetime
				elif rPP:
					self.ask_time = primetime + oneDay
				elif rPM:
					self.ask_time = primetime - oneDay
				self.updateVerticalEPG(True)
			else:
				self[f"list{self.activeList}"].moveTo(
					self[f"list{self.activeList}"].instance.moveTop)
				self.setMinus24h(True, 6)
				for n in range(1, self.Fields):
					self[f"list{n}"].moveTo(self[f"list{n}"].instance.moveEnd)
					cnt = self[f"list{n}"].getCurrentIndex()
					self[f"list{n}"].moveTo(self[f"list{n}"].instance.moveTop)
					self.findPrimetime(cnt, n, primetime)
			self.saveLastEventTime()

	def gotoLasttime(self, n=0):
		if n:
			self[f"list{n}"].moveTo(self[f"list{n}"].instance.moveEnd)
			cnt = self[f"list{n}"].getCurrentIndex()
			self[f"list{n}"].moveTo(self[f"list{n}"].instance.moveTop)
			self.findLasttime(cnt, n)
		else:
			for n in range(1, self.Fields):
				self[f"list{n}"].moveTo(self[f"list{n}"].instance.moveEnd)
				cnt = self[f"list{n}"].getCurrentIndex()
				self[f"list{n}"].moveTo(self[f"list{n}"].instance.moveTop)
				self.findLasttime(cnt, n)

	def findLasttime(self, cnt, n, idx=0):
		last_begin, last_end = self.lastEventTime
		for _ in range(idx):
			self[f"list{n}"].moveTo(self[f"list{n}"].instance.moveDown)
		for _ in range(idx, cnt):
			ev_begin, ev_end = self.getEventTime(n)
			if ev_begin is not None:
				if (ev_begin <= last_begin < ev_end) or ev_end >= last_end:
					break
				self[f"list{n}"].moveTo(self[f"list{n}"].instance.moveDown)
			else:
				break

	def findPrimetime(self, cnt, n, primetime):
		for _ in range(cnt):
			ev_begin, ev_end = self.getEventTime(n)
			if ev_begin is not None:
				if ev_begin <= primetime < ev_end:
					break
				self[f"list{n}"].moveTo(self[f"list{n}"].instance.moveDown)
			else:
				break

	def findMaxEventTime(self, stime):
		curr = self[f"list{self.activeList}"].getSelectedEventId()
		self[f"list{self.activeList}"].moveTo(
			self[f"list{self.activeList}"].instance.moveEnd)
		maxtime = self.getEventTime(self.activeList)[0]
		self[f"list{self.activeList}"].moveToEventId(curr)
		return maxtime is not None and maxtime >= stime

	def findMinEventTime(self, stime):
		curr = self[f"list{self.activeList}"].getSelectedEventId()
		self[f"list{self.activeList}"].moveTo(
			self[f"list{self.activeList}"].instance.moveTop)
		mintime = self.getEventTime(self.activeList)[0]
		self[f"list{self.activeList}"].moveToEventId(curr)
		return mintime is not None and mintime <= stime

	def isInTimeRange(self, stime):
		return self.findMaxEventTime(stime) and self.findMinEventTime(stime)


	def sortEPG(self):
		pass
_EPG_TYPE_STR = {
	"single": EPG_TYPE_SINGLE,
	"enhanced": EPG_TYPE_ENHANCED,
	"infobar": EPG_TYPE_INFOBAR,
	"graph": EPG_TYPE_GRAPH,
	"infobargraph": EPG_TYPE_INFOBARGRAPH,
	"multi": EPG_TYPE_MULTI,
	"vertical": EPG_TYPE_VERTICAL,
	"similar": EPG_TYPE_SIMILAR,
}


def createEPGSelection(session, service=None, zapFunc=None, eventid=None,
						bouquetChangeCB=None, serviceChangeCB=None, EPGtype=None,
						StartBouquet=None, StartRef=None, bouquets=None):
	"""Returns the EPG screen matching the old EPGSelection arguments."""
	if EPGtype is None and eventid is None and isinstance(service, eServiceReference):
		epgType = EPG_TYPE_SINGLE
	else:
		epgType = _EPG_TYPE_STR.get(EPGtype, EPG_TYPE_SIMILAR)
	if StartRef is None and isinstance(service, eServiceReference):
		StartRef = service
	if epgType == EPG_TYPE_SIMILAR:
		return EPGSelectionSimilar(session, service, eventid, zapFunc)
	if epgType in (EPG_TYPE_SINGLE, EPG_TYPE_ENHANCED):
		return EPGSelectionSingle(session, zapFunc, StartBouquet, StartRef, bouquets, epgType, serviceChangeCB)
	if epgType == EPG_TYPE_INFOBAR:
		return EPGSelectionInfobarSingle(session, zapFunc, StartBouquet, StartRef, bouquets)
	if epgType == EPG_TYPE_GRAPH:
		return EPGSelectionGrid(session, zapFunc, StartBouquet, StartRef, bouquets, config.epgselection.grid.type_mode.value == "graphics")
	if epgType == EPG_TYPE_INFOBARGRAPH:
		return EPGSelectionInfobarGrid(session, zapFunc, StartBouquet, StartRef, bouquets, config.epgselection.infobar.type_mode.value == "graphics")
	if epgType == EPG_TYPE_MULTI:
		return EPGSelectionMulti(session, zapFunc, StartBouquet, StartRef, bouquets)
	return EPGSelectionVertical(session, zapFunc, StartBouquet, StartRef, bouquets)


class EPGSelectionMeta(type):
	# Plugins like Partnerbox2 patch methods on EPGSelection; apply them to all EPG screens.
	# __init__ and the compat overrides are not forwarded, their signatures differ.
	def __init__(cls, name, bases, namespace):
		super().__init__(name, bases, namespace)
		type.__setattr__(cls, "compatNames", frozenset(namespace))

	def __setattr__(cls, name, value):
		forward = cls is EPGSelection and not name.startswith("__") and name not in cls.compatNames
		type.__setattr__(cls, name, value)
		if forward:
			type.__setattr__(EPGSelectionBase, name, value)


class EPGSelection(EPGSelectionSingle, metaclass=EPGSelectionMeta):
	"""Old EPGSelection API for plugins.

	Calling EPGSelection returns the EPG screen matching the arguments.
	Subclasses like AutoTimer or EPGSearch get a single or similar EPG.
	"""

	activeList = ""  # EPGSearch does not call __init__.
	_cfg = EPGSettings(EPG_TYPE_SIMILAR)  # Default button actions for EPGSearch.

	def __new__(cls, session, *args, **kwargs):
		if cls is EPGSelection:
			return createEPGSelection(session, *args, **kwargs)
		return EPGSelectionSingle.__new__(cls)

	def __init__(self, session, service=None, zapFunc=None, eventid=None, bouquetChangeCB=None, serviceChangeCB=None, EPGtype=None, StartBouquet=None, StartRef=None, bouquets=None):
		if isinstance(service, str):
			service = eServiceReference(service)
		elif not isinstance(service, eServiceReference):
			service = None
		EPGSelectionSingle.__init__(self, session, zapFunc, StartBouquet, StartRef or service, bouquets, EPG_TYPE_SINGLE, serviceChangeCB)
		if EPGtype == "similar" or (EPGtype is None and eventid is not None):
			self.type = EPG_TYPE_SIMILAR
			self.currentService = ServiceReference(service)
			self.eventid = eventid
			self["list"] = EPGListSingle(session, config.epgselection.single, EPG_TYPE_SIMILAR, self.onSelectionChanged)

	def onCreate(self):
		if self.type == EPG_TYPE_SIMILAR:
			EPGSelectionSimilar.onCreate(self)
		else:
			EPGSelectionSingle.onCreate(self)

	def refreshlist(self):
		if self.type == EPG_TYPE_SIMILAR:
			EPGSelectionSimilar.refreshlist(self)
		else:
			EPGSelectionSingle.refreshlist(self)

	def Info(self):
		from Screens.InfoBar import InfoBar
		if not InfoBar.instance.LongButtonPressed:
			self.infoKeyPressed()

	def infoKeyPressed(self, eventviewopen=False):
		self.openEventView()

	def eventSelected(self):
		self.infoKeyPressed()

	def timerAdd(self):
		self.RecordTimerQuestion(True)

	def OpenSingleEPG(self):
		self.openSingleEPG()

	# Old method names used by plugins (e.g. EPGSearch, PrimeTimeManager).
	redButtonPressed = EPGStandardButtons._btn_red
	redButtonPressedLong = EPGStandardButtons._btn_redlong
	greenButtonPressed = EPGStandardButtons._btn_green
	greenButtonPressedLong = EPGStandardButtons._btn_greenlong
	yellowButtonPressed = EPGStandardButtons._btn_yellow
	blueButtonPressed = EPGStandardButtons._btn_blue
	blueButtonPressedLong = EPGStandardButtons._btn_bluelong
	recButtonPressed = EPGStandardButtons._btn_rec
	recButtonPressedLong = EPGStandardButtons._btn_reclong

	def sortEpg(self):
		self.sortEPG()

	def showTimerList(self):
		self.openTimerList()

	def showAutoTimerList(self):
		self.openAutoTimerList()

	def showMovieSelection(self):
		self.showMovies()

	def openTMDB(self):
		self.openTMDb()

	def createSetup(self):
		self.createMenu()
