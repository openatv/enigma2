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
from Screens.HelpMenu import HelpableScreen
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


# lib/python/Screens/EpgSelectionBase.py
#
# New file (2026). Based on OpenViX Screens/EpgSelectionBase.py,
# adapted for openATV while preserving ATV functionality.
#
# Key differences from OpenViX:
#   - Button actions are user-configurable via EPGSettings (EpgConfig.py),
#     not hardcoded in EPGStandardButtons like in OpenViX.
#   - Timer dialogs use ATV ChoiceBox + RecordTimerQuestion (with FallbackTimerList
#     support for external timers). OpenViX uses PopupChoiceBox + addTimerFromEvent.
#   - EPGServiceZap.closeScreen keeps ATV per-type preview_mode and zapFunc/PiP logic.
#     OpenViX's cleaner version using self.epgConfig.preview_mode is included as comment.
#   - getBouquetServices includes ATV InfoBar subservice check (not in OpenViX).
#   - Number channel zap uses ATV NumberZapTimer inline approach.
#     OpenViX EPGServiceNumberSelectionPopup class is included for reference, commented.
#   - openEventView uses ATV showEventViewCallback; OpenViX uses EventViewEPGSelect.
#
# Concrete classes (EpgSelectionSingle.py etc.) must:
#   1. Set self._cfg = EPGSettings(EPG_TYPE_xxx) BEFORE calling EPGSelectionBase.__init__
#   2. Set self.type = EPG_TYPE_xxx (used by _dispatchEpgAction, closeScreen, etc.)
#   3. Set self.activeList appropriately ("" for all non-vertical, 1-5 for vertical)


# OpenViX uses these helpers from TimerEntry; ATV uses RecordTimerQuestion instead.
# from Screens.TimerEntry import addTimerFromEvent, addTimerFromEventSilent

# OpenViX uses PopupChoiceBox for timer action menus; ATV uses ChoiceBox.
# from Screens.ChoiceBox import PopupChoiceBox

# OpenViX opens EventViewEPGSelect directly; ATV calls showEventViewCallback.
# from Screens.EventView import EventViewEPGSelect

# OpenViX checks isPluginInstalled("tmdb") at init time to decide the red button label.
# ATV checks the import directly when the action is triggered.
# from Tools.Directories import isPluginInstalled

autopoller = None
autotimer = None


# ---------------------------------------------------------------------------
# Action ID lists — describe the available user-configurable button actions.
# These are consumed by EpgConfig.py to build ConfigSelection choices and by
# EPGSettings to resolve the configured action name to a method name.
# Format: (action_id, label) or (action_id, label, help_text)
# Taken from OpenViX; ATV-only entries are marked.
# ---------------------------------------------------------------------------

epgActions = [
    ("", _("Do nothing")),
    ("openIMDb", _("IMDb Search"), _("IMDb search for current event")),
    ("openTMDb", _("TMDb Search"), _("TMDb search for current event")),
    ("sortEPG", _("Sort"), _("Sort the EPG list")),
    ("addEditTimer", _("Add Timer"), _("Add/Edit/Remove timer for current event")),
    ("openTimerList", _("Show Timer List"), _("Show timer list")),
    ("openEPGSearch", _("EPG Search"), _("Search for similar events")),
    ("addEditAutoTimer", _("Add AutoTimer"), _("Add/Edit autotimer for current event")),
    ("openAutoTimerList", _("AutoTimer List"), _("Show autotimer list")),
    ("forward24Hours", _("+24 hours"), _("Go forward 24 hours")),
    ("back24Hours", _("-24 hours"), _("Go back 24 hours")),
    ("openEventView", _("Event Info"), _("Show detailed event info")),
    ("openSingleEPG", _("Single EPG"), _("Show single channel EPG")),
    ("showMovies", _("Recordings"), _("Show recorded movies")),
]

okActions = [
    ("zap", _("Zap")),
    ("zapExit", _("Zap + Exit")),
    ("openEventView", _("Event Info"), _("Show detailed event info")),
]

# ATV RecordTimerQuestion shows a menu; these IDs select the action within it.
recActions = [
    ("addEditTimerMenu", _("Timer Menu"), _("Add a record timer or an autotimer")),
    ("addEditTimer", _("Add Timer"), _("Add and edit a record timer")),
    ("addEditZapTimerSilent", _("Create Zap Timer"), _("Add a zap timer silently")),
    ("addEditAutoTimer", _("Add AutoTimer"), _("Add an autotimer")),
]

infoActions = [
    ("", _("Do nothing")),
    ("openEventView", _("Event Info"), _("Show detailed event info")),
    ("openSingleEPG", _("Single EPG"), _("Show single channel EPG")),
    # OpenViX also supports switchToSingleEPG, switchToGridEPG, switchToMultiEPG here.
    # Those require EPGSelection factory routing that ATV does differently.
    # ("switchToSingleEPG", _("Switch to Single EPG")),
    # ("switchToGridEPG", _("Switch to Grid EPG")),
    # ("switchToMultiEPG", _("Switch to Multi EPG")),
]

# These are used by grid/infobargraph for channelup/down key config.
channelUpActions = [
    ("forward24Hours", _("+24 hours"), _("Go forward 24 hours")),
    ("prevPage", _("Page up")),
]

channelDownActions = [
    ("back24Hours", _("-24 hours"), _("Go back 24 hours")),
    ("nextPage", _("Page down")),
]


class EPGSelectionBase(Screen, HelpableScreen):
    # Shared constants used for the green button / timer state tracking.
    catchupPlayerFunc = None
    EMPTY = 0
    ADD_TIMER = 1
    REMOVE_TIMER = 2
    ZAP = 1

    def __init__(self, session, epgConfig, startBouquet=None, startRef=None, bouquets=None):
        Screen.__init__(self, session)
        HelpableScreen.__init__(self)

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

        # ATV-specific: PiP state saved/restored around EPG open/close.
        self.Oldpipshown = bool(self.session.pipshown)
        self.session.pipshown = False
        self.onClose.append(self.restorePiP)

        # ATV-specific: number-zap state for inline channel number entry.
        self.zapnumberstarted = False
        self.NumberZapTimer = eTimer()
        self.NumberZapTimer.callback.append(self.dozumberzap)
        self.NumberZapField = None

        self["Service"] = ServiceEvent()
        self["Event"] = Event()
        self["lab1"] = Label(_("Please wait while gathering EPG data..."))
        self["lab1"].hide()

        # Button label widgets — concrete classes may override text via _updateButtonText.
        self["key_red"] = StaticText(_("IMDb Search"))
        self["key_green"] = StaticText(_("Add Timer"))
        self["key_yellow"] = StaticText(_("EPG Search"))
        self["key_blue"] = StaticText(_("Add AutoTimer"))
        self["key_menu"] = StaticText(_("MENU"))
        self["key_info"] = StaticText(_("INFO"))
        self["key_text"] = StaticText(_("TEXT"))
        self["key_epg"] = StaticText(_("EPG"))
        self["key_play"] = StaticText("")

        helpDescription = _("EPG Commands")

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
            "up": (self.moveUp, _("Go to previous channel")),
            "down": (self.moveDown, _("Go to next channel")),
        }, prio=-1, description=_("EPG navigation commands"))

        self["epgcatchupactions"] = HelpableActionMap(self, "EPGCatchUpActions", {
            "play": (self.playCatchup, _("Play catch-up archive")),
        }, prio=-2, description=_("Catch-up player commands"))
        self["epgcatchupactions"].setEnabled(callable(self.catchupPlayerFunc))

        # dialogactions is enabled while ChoiceBoxDialog is open (disables other maps).
        self["dialogactions"] = HelpableActionMap(self, "WizardActions", {
            "back": (self.closeChoiceBoxDialog, _("Close dialog")),
        }, prio=-1)
        self["dialogactions"].setEnabled(False)

        self._updateButtonText()

        self.refreshTimer = eTimer()
        self.refreshTimer.timeout.get().append(self.refreshlist)

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

    # ------------------------------------------------------------------
    # Navigation — delegate to the list widget. Concrete classes extend
    # these where type-specific behaviour is needed (e.g. vertical EPG).
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Event view
    # ------------------------------------------------------------------

    def openEventView(self):
        # ATV approach: showEventViewCallback handles the dialog lifecycle.
        # OpenViX uses: self.session.open(EventViewEPGSelect, event, service, ...)
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

    # ------------------------------------------------------------------
    # Sorting — base is a no-op; concrete classes implement per-type sort.
    # ------------------------------------------------------------------

    def sortEPG(self):
        self.closeEventViewDialog()

    # ------------------------------------------------------------------
    # Date/time jump — ATV version using EPGJumpTime per type.
    # OpenViX uses a single TimeDateInput for all types.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Movies / recordings
    # ------------------------------------------------------------------

    def showMovies(self):
        # ATV: delegate to InfoBar.showMovies().
        # OpenViX: same, but named showMovies (ATV name is showMovieSelection in old code).
        from Screens.InfoBar import InfoBar
        InfoBar.instance.showMovies()

    # ------------------------------------------------------------------
    # Single EPG / type switching
    # ------------------------------------------------------------------

    def openSingleEPG(self):
        # ATV-specific: opens EPGSelection in single mode for the current service.
        event, service = self[f"list{self.activeList}"].getCurrent()[:2]
        if service is not None:
            self.session.open(EPGSelection, service.ref)

    # OpenViX has switchToSingleEPG / switchToGridEPG / switchToMultiEPG which close
    # the current EPG and reopen it in a different mode via the EPGSelection factory.
    # ATV routes EPG type switches differently (through EPGSelection.__init__ EPGtype param).
    # def switchToSingleEPG(self):
    #     from Screens.EpgSelectionSingle import EPGSelectionSingle
    #     event, service = self[f"list{self.activeList}"].getCurrent()[:2]
    #     if service is not None:
    #         self.close("open", EPGSelectionSingle, self.getCurrentBouquet(), service, self.bouquets, ...)
    # def switchToGridEPG(self): ...
    # def switchToMultiEPG(self): ...

    # ------------------------------------------------------------------
    # Plugin actions — IMDb, TMDb, EPGSearch, AutoTimer
    # ATV checks imports at call time; OpenViX uses isPluginInstalled at init.
    # ------------------------------------------------------------------

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
            self.session.open(MessageBox, _("The TMDb plugin is not installed!\nPlease install it."),
                              type=MessageBox.TYPE_INFO, timeout=10)
            return
        event = self[f"list{self.activeList}"].getCurrent()[0]
        if event is not None:
            self.session.open(tmdbScreen, event.getEventName(), 2)

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
        # OpenViX: checks timer.autoTimerId to decide add vs edit.
        # ATV: addAutoTimer handles both cases internally.
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
        # OpenViX public name: editAutoTimer. ATV keeps it private to avoid
        # confusion with the similarly named editTimer (record timer).
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

    # ------------------------------------------------------------------
    # Catch-up / replay
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Setup menu — opens per-type Setup page. Ported from EPGSelectionNEW.py.
    # Graph/infobar types close with a "reopen" key so the screen rebuilds.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Timer list / autotimer list
    # ------------------------------------------------------------------

    def openTimerList(self):
        # ATV: uses RecordTimerOverview. OpenViX: uses TimerEditList.
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
                                  _("Your AutoTimer config file is not well-formed:\n%s") % str(se),
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

    # ------------------------------------------------------------------
    # Timer add / edit / remove — ATV approach using RecordTimerQuestion.
    # OpenViX uses addTimerFromEvent / PopupChoiceBox which are not in ATV.
    # ------------------------------------------------------------------

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
        # ATV-specific: FallbackTimerList handles external (e.g. satellite) timers.
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
        # ATV-specific: FallbackTimerList support for external timers.
        # OpenViX version (no external timer handling):
        #   timer.disable()
        #   self.session.nav.RecordTimer.timeChanged(timer)
        #   self.setActionButtonText("addEditTimer", _("Add Timer"))
        #   self.refreshList()
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
        # ATV-specific: combines add/edit/remove timer in one dialog.
        # OpenViX splits this into addEditTimer (via addTimerFromEvent) and
        # addEditTimerMenu (via PopupChoiceBox with three static choices).
        # ATV version also handles FallbackTimerList for external timers.
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
                    menu.append((_("Enable Timer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb4))
                else:
                    menu.append((_("Disable Timer"), "CALLFUNC", self.RemoveChoiceBoxCB, cb3))
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
        # image for standard isInTimer logic (ATV-specific for multi-image setups).
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

    # ------------------------------------------------------------------
    # ChoiceBox dialog management — enables/disables competing action maps
    # while the timer-choice dialog is visible.
    # OpenViX uses a different mechanism (PopupChoiceBox with callbacks).
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Selection changed — updates Event/Service sources and green button.
    # ATV version tracks timer state (key_green_choice) and handles multi-EPG
    # progress display. OpenViX version is simpler.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Configurable button action dispatch — central dispatcher used by all
    # color/rec button handlers. Action names match EPGSettings property names
    # and the method names defined on this class.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Close / zap / exit — ATV version kept active (complex PiP + zapFunc
    # + per-type preview_mode logic). OpenViX version included for reference.
    # ------------------------------------------------------------------

    def closeScreen(self, NOCLOSE=False):
        # ATV: restore original service when in preview mode, using per-type config.
        # OpenViX EPGServiceZap.closeScreen() is simpler: uses self.epgConfig.preview_mode.value
        # and restores self.__originalPlayingService. That approach is included in EPGServiceZap.
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

    def restorePiP(self):
        # ATV-specific: restores PiP state that was saved at EPG open time.
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
        # If the same service is selected twice, exits the EPG (matches ATV behaviour).
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

    # ------------------------------------------------------------------
    # Green button text — keeps display in sync with current timer state.
    # OpenViX calls this setActionButtonText("addEditTimer", text);
    # ATV uses setTimerButtonText for brevity.
    # ------------------------------------------------------------------

    def setTimerButtonText(self, text):
        # Update every color button that is configured to add/edit timers.
        for color in ("red", "green", "yellow", "blue"):
            if self._cfg.btn(color) == "addEditTimer":
                self[f"key_{color}"].setText(text)

    # ------------------------------------------------------------------
    # OK / OKLong — dispatch based on EPGSettings config.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Info / EPG buttons — configurable via EPGSettings.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Number zap — ATV inline approach (number field displayed in the EPG).
    # OpenViX EPGServiceNumberSelectionPopup class below is an alternative.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # PiP toggle — ATV-specific (not in OpenViX).
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Refresh — concrete classes implement for their specific data source.
    # ------------------------------------------------------------------

    def refreshlist(self):
        self.refreshTimer.stop()

    def onCreate(self):
        pass

    def moveToService(self, service):
        self[f"list{self.activeList}"].moveToService(service)

    # ------------------------------------------------------------------
    # Public API — called from ChannelSelection, InfoBarGenerics, EventView.
    # ATV: same as old EPGSelection. OpenViX: same names, same semantics.
    # ------------------------------------------------------------------

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
        # Manages the now/next/more button visibility for multi-EPG mode.
        # state 0: hide all; state 1: now selected; 2: next selected; 3: more selected.
        # ATV-specific skin widgets — OpenViX uses a different button layout.
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


# ===========================================================================
# EPGServiceZap — handles zap/preview/closeScreen when zapFunc is available.
# Taken from OpenViX. ATV closeScreen is on EPGSelectionBase; the OpenViX
# version of closeScreen (which lives here) is included as comment for reference.
# ===========================================================================

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

    def zapExit(self):
        # Zap to the selected service and exit the EPG immediately.
        self.zapSelectedService()
        self.closeEventViewDialog()
        self.close()

    def zap(self):
        # Preview zap: same service a second time = exit; first time = stay.
        currentService = self.session.nav.getCurrentlyPlayingServiceOrGroup()
        if currentService and currentService.isPlayback():
            from Screens.InfoBarGenerics import setResumePoint
            setResumePoint(self.session)
        self.zapSelectedService(True)
        self.refreshTimer.start(1)
        if not self.currch or self.currch == self.prevch:
            self.zapFunc(None, False)
            self.closeEventViewDialog()
            self.close()

    # OpenViX EPGServiceZap.closeScreen() — simpler than ATV but requires
    # self.epgConfig.preview_mode.value (our subsection config has this).
    # ATV uses EPGSelectionBase.closeScreen() instead (handles per-type config
    # and zapFunc/PiP logic). Left here for reference.
    #
    # def closeScreen(self):
    #     currentService = self.session.nav.getCurrentlyPlayingServiceOrGroup()
    #     if currentService and currentService.toString() != self._originalPlayingService.toString():
    #         if self.epgConfig.preview_mode.value:
    #             if self._originalPlayingService.isPlayback():
    #                 from Screens.InfoBar import MoviePlayer
    #                 if MoviePlayer.instance:
    #                     MoviePlayer.instance.forceNextResume()
    #             self.session.nav.playService(self._originalPlayingService)
    #         else:
    #             from Screens.InfoBar import MoviePlayer
    #             MoviePlayer.ensureClosed(currentService)
    #             self.zapFunc(None, False)
    #     self.closeEventViewDialog()
    #     self.close()

    def zapSelectedService(self, prev=False):
        self.prevch = (self.session.nav.getCurrentlyPlayingServiceReference()
                       and self.session.nav.getCurrentlyPlayingServiceReference().toString()
                       or None)
        selectedService = self["list"].getCurrent()[1]
        if selectedService is not None:
            self.zapFunc(selectedService.ref, bouquet=self.getCurrentBouquet(), preview=prev)
            self.currch = (self.session.nav.getCurrentlyPlayingServiceReference()
                           and self.session.nav.getCurrentlyPlayingServiceReference().toString())


# ===========================================================================
# EPGServiceNumberSelectionPopup — OpenViX popup dialog for number zap.
# NOT used by default (ATV uses inline NumberZapTimer approach in EPGSelectionBase).
# Included here as a reference / alternative implementation.
# To use: call self.popupDialog = self.session.instantiateDialog(
#     EPGServiceNumberSelectionPopup, self.getServiceByNumber, closed, number)
# ===========================================================================

class EPGServiceNumberSelectionPopup(Screen):
    # OpenViX popup that shows the entered number and matching service name.
    # ATV equivalent: inline self["number"] label + NumberZapTimer in EPGSelectionBase.
    def __init__(self, session, getServiceByNumber, callback, number):
        Screen.__init__(self, session)
        self.skinName = "EPGServiceNumberSelection"
        self.getServiceByNumber = getServiceByNumber
        self.callback = callback

        helpDescription = _("EPG Commands")
        helpMsg = _("Enter a number to jump to a service/channel")
        self["actions"] = HelpableNumberActionMap(self, "NumberActions",
            dict([(str(i), (self.keyNumber, helpMsg)) for i in range(0, 10)]),
            prio=-1, description=helpDescription)
        self["cancelaction"] = HelpableActionMap(self, "OkCancelActions", {
            "cancel": (self.__cancel, _("Exit channel selection")),
            "OK": (self.__OK, _("Select EPG channel")),
        }, prio=-1, description=helpDescription)

        self["number"] = Label()
        self["service"] = ServiceEvent()
        self["service"].newService(None)

        self.timer = eTimer()
        self.timer.callback.append(self.__OK)
        self.number = ""
        self.keyNumber(number)

    def show(self):
        self["actions"].execBegin()
        self["cancelaction"].execBegin()
        Screen.show(self)

    def hide(self):
        self["actions"].execEnd()
        self["cancelaction"].execEnd()
        Screen.hide(self)

    def keyNumber(self, number):
        if config.misc.zapkey_delay.value > 0:
            self.timer.start(1000 * config.misc.zapkey_delay.value, True)
        self.number += str(number)
        service, bouquet = self.getServiceByNumber(int(self.number))
        self["number"].setText(self.number)
        self["service"].newService(service)
        if len(self.number) >= 4:
            self.__OK()

    def __OK(self):
        self.callback(int(self.number))

    def __cancel(self):
        self.callback(None)


# ===========================================================================
# EPGServiceNumberSelection — mixin that adds number-key channel jumping.
# OpenViX version uses EPGServiceNumberSelectionPopup (above).
# Concrete classes can use this mixin alongside the ATV inline approach.
# ===========================================================================

class EPGServiceNumberSelection:
    def __init__(self):
        self["number"] = Label()
        self["number"].hide()
        helpMsg = _("Enter a number to jump to a service/channel")
        self["numberactions"] = HelpableNumberActionMap(self, "NumberActions",
            dict([(str(i), (self.keyNumberGlobal, helpMsg)) for i in range(0, 10)]),
            prio=-1, description=_("Service/Channel number zap commands"))

    # OpenViX EPGServiceNumberSelection uses EPGServiceNumberSelectionPopup:
    # def keyNumberGlobal(self, number):
    #     def closed(number):
    #         if self.popupDialog:
    #             self.popupDialog.doClose()
    #         self.closePopupDialog()
    #         if number is not None:
    #             service, bouquet = self.getServiceByNumber(number)
    #             if service is not None:
    #                 self.startRef = service
    #                 self.startBouquet = bouquet
    #                 self.setBouquet(bouquet)
    #                 self.bouquetChanged()
    #                 self.moveToService(service)
    #     self.popupDialog = self.session.instantiateDialog(
    #         EPGServiceNumberSelectionPopup, self.getServiceByNumber, closed, number)
    #     self.showPopupDialog()
    #
    # ATV uses keyNumberGlobal from EPGSelectionBase (inline NumberZapTimer).
    # That method is already defined there; this mixin just registers the action map.

    def numberEntered(self, service, bouquet):
        self.setBouquet(bouquet)
        if isinstance(self, EPGServiceBrowse):
            self.setCurrentService(service)
            self.serviceChanged()
        else:
            self.bouquetChanged()
            self.moveToService(service)


# ===========================================================================
# EPGBouquetSelection — mixin for bouquets with a visual bouquet list widget.
# Taken from OpenViX with ATV adaptations:
#   - getBouquetServices: ATV version checks InfoBar subservices.
#   - browse_mode "lastepgservice": remembers last bouquet/service across EPG opens.
# ===========================================================================

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
        # ATV: also returns subservices when the bouquet is a subservice list.
        # OpenViX: only uses eServiceCenter.
        # OpenViX version:
        #   servicelist = eServiceCenter.getInstance().list(bouquet)
        #   if servicelist:
        #       return [s for s in servicelist.getContent("R", True)
        #               if not (s.flags & (eServiceReference.isDirectory | eServiceReference.isMarker))]
        #   return []
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

    # Keep OpenViX name as alias so concrete classes can call either.
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


# ===========================================================================
# EPGServiceBrowse — extends EPGBouquetSelection with per-service navigation.
# Used by single/enhanced/infobar EPG types.
# Taken from OpenViX without changes.
# ===========================================================================

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


# ===========================================================================
# EPGStandardButtons — provides helpKeyAction() and button label management.
#
# ATV approach: all button actions are user-configurable via EPGSettings (self._cfg).
#   helpKeyAction() returns wrapper methods that call _dispatchEpgAction at press time.
#
# OpenViX approach: actions are hardcoded in helpKeyAction() — red=IMDb/TMDb,
#   green=addEditTimer, rec=addEditTimerMenu, reclong=addEditZapTimerSilent.
#   That hardcoded version is included as comment below for reference.
# ===========================================================================

class EPGStandardButtons:

    def setActionButtonText(self, actionName, buttonText):
        # Updates button label for the two state-tracking buttons.
        # OpenViX: same implementation.
        if actionName == "addEditTimer":
            self["key_green"].setText(buttonText)
        elif actionName == "addEditAutoTimer":
            self["key_blue"].setText(buttonText)

    # --- Button wrapper methods — called at press time, read config then. ---

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
        # Returns a (function, help_text) tuple for use in HelpableActionMap.
        # help_text is resolved dynamically from the currently configured action,
        # matching the OpenViX UserDefinedButtons approach.
        from Components.EpgConfig import epgActions, okActions, recActions, infoActions
        _labels = {action_id: label for action_id, label, *_
                   in epgActions + okActions + recActions + infoActions}

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
                "ok": _("Zap to channel/service"),
                "oklong": _("Zap to channel/service and close"),
                "epg": _("Show single EPG for current channel"),
                "epglong": "",
                "info": _("Show event info (setup in menu)"),
                "infolong": _("Show single EPG (setup in menu)"),
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
        from Components.EpgConfig import epgActions
        labels = {x[0]: x[1] for x in epgActions}
        labels[""] = ""
        for color in ("red", "green", "yellow", "blue"):
            self[f"key_{color}"].setText(labels.get(self._cfg.btn(color), ""))
# ===========================================================================
# EPGGridNavigation — left/right and CH+/CH- handling shared by both grid EPGs.
# ===========================================================================

class EPGGridNavigation:
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


# lib/python/Screens/EpgSelectionGrid.py
#
# New file (2026). Concrete EPG screen for graphical grid mode.
#
# Handles EPG_TYPE_GRAPH.
# Features not in single/multi: graphical timeline, epoch zoom (keys 1/3),
# primetime jump (key 9), height-switch (key 7), 24h-jump (keys 4/6).
# Number keys 0-9 drive graph navigation — no channel-number zap here.


class EPGSelectionGrid(EPGSelectionBase, EPGBouquetSelection,
                       EPGServiceZap, EPGStandardButtons, EPGGridNavigation):
    """Graphical grid EPG screen (EPG_TYPE_GRAPH)."""

    def __init__(self, session, zapFunc=None, startBouquet=None,
                 startRef=None, bouquets=None, graphic=False):
        self.type = EPG_TYPE_GRAPH
        self._cfg = EPGSettings(EPG_TYPE_GRAPH)
        self.activeList = ""

        # Initial start time aligned to roundto boundary.
        now = time() - config.epgselection.grid.histminutes.value * 60
        self.ask_time = now - now % (config.epgselection.grid.roundto.value * 60)

        EPGSelectionBase.__init__(self, session, config.epgselection.grid,
                                  startBouquet, startRef, bouquets)
        self.skinName = "GraphicalEPGPIG" if config.epgselection.grid.pig.value else "GraphicalEPG"
        EPGServiceZap.__init__(self, zapFunc)
        # graphic=True: graphical bouquet list (channel logos alongside names).
        EPGBouquetSelection.__init__(self, graphic)

        self["list"] = EPGListGrid(session, config.epgselection.grid,
                                   EPG_TYPE_GRAPH, self.onSelectionChanged,
                                   graphic=graphic,
                                   overjump_empty=config.epgselection.overjump.value,
                                   time_epoch=config.epgselection.grid.prevtimeperiod.value)

        # Opt-in: skins can request Label widgets instead of Pixmap for the
        # timeline graphics, e.g. to apply icon-font glyphs.
        graphicControl = Label if parameters.get("EPGNativeControls", 0) else Pixmap

        # Timeline text widget labels the time axis above the event grid.
        self["timeline_text"] = TimelineText(epgType=EPG_TYPE_GRAPH, graphic=graphic)
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
        from enigma import eTimer as _eTimer
        self.updateTimelineTimer = _eTimer()
        self.updateTimelineTimer.callback.append(self.moveTimeLines)
        self.updateTimelineTimer.start(60000)

        # Number keys 0-9 drive graph navigation (epoch, time-jump, primetime).
        # No channel-number zap in graph mode.
        from Components.ActionMap import HelpableNumberActionMap
        self["input_actions"] = HelpableNumberActionMap(self, "NumberActions", {
            "1": (lambda: self._numberKeyPressed(1), _("Reduce time scale")),
            "2": (lambda: self._numberKeyPressed(2), _("Page up")),
            "3": (lambda: self._numberKeyPressed(3), _("Increase time scale")),
            "4": (lambda: self._numberKeyPressed(4), _("Step left")),
            "5": (lambda: self._numberKeyPressed(5), _("Jump to current time")),
            "6": (lambda: self._numberKeyPressed(6), _("Step right")),
            "7": (lambda: self._numberKeyPressed(7), _("Height switch")),
            "8": (lambda: self._numberKeyPressed(8), _("Page down")),
            "9": (lambda: self._numberKeyPressed(9), _("Jump to prime time")),
            "0": (lambda: self._numberKeyPressed(0), _("Go to first channel")),
        }, prio=-1, description=_("Graph EPG navigation"))

        self.addEpgActions({
            "info": (self.Info, _("Event info")),
            "infolong": (self.InfoLong, _("Single EPG")),
            "menu": (self.createMenu, _("Menu")),
            "nextBouquet": (self.nextBouquet, _("Next bouquet")),
            "prevBouquet": (self.prevBouquet, _("Previous bouquet")),
            "input_date_time": (self.enterDateTime, _("Jump to date/time")),
            "nextService": (self.nextService, _("CHANNEL+ button (setup in menu)")),
            "prevService": (self.prevService, _("CHANNEL- button (setup in menu)")),
            "epg": (self.epgButtonPressed, _("Single EPG")),
            "epglong": (self.epgButtonPressedLong, _("EPG button long (setup in menu)")),
            "tv": (self.toggleBouquetList, _("Toggle bouquet list")),
            "tvlong": (self.togglePIG, _("Toggle picture in graphics")),
        })
        self.addCursorActions({
            "left": (self.leftPressed, _("Go to previous event")),
            "right": (self.rightPressed, _("Go to next event")),
        })

    # ------------------------------------------------------------------
    # onCreate — called from onLayoutFinish after layout is ready.
    # ------------------------------------------------------------------

    def onCreate(self):
        if "primetime" in config.epgselection.grid.startmode.value:
            pt = config.epgselection.grid.primetime.value
            now = time() - config.epgselection.grid.histminutes.value * 60
            base = localtime(now - now % (config.epgselection.grid.roundto.value * 60))
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
        self["list"].setShowServiceMode(config.epgselection.grid.servicetitle_mode.value)
        if "channel1" in config.epgselection.grid.startmode.value or self.selectFirstService():
            self["list"].instance.moveSelectionTo(0)
        self.moveTimeLines(True)
        self.onSelectionChanged()

    def refreshlist(self):
        self.ask_time = self["list"].getTimeBase()
        self["list"].fillGraphEPG(None, self.ask_time)
        self.moveTimeLines()
        self.onSelectionChanged()

    # ------------------------------------------------------------------
    # Timeline — updates every minute and on any navigation change.
    # ------------------------------------------------------------------

    def moveTimeLines(self, force=False):
        self.updateTimelineTimer.start((60 - int(time()) % 60) * 1000)
        self["timeline_text"].setEntries(self["list"], self["timeline_now"],
                                         self.time_lines, force)
        self["list"].l.invalidate()

    # ------------------------------------------------------------------
    # Navigation overrides for graph mode (left/right = time; up/down = channel).
    # ------------------------------------------------------------------

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
            # Workaround: ATV scrolls the service list; prevPage only when not at top.
            self["list"].prevPage()
        else:
            self["list"].moveTo(self["list"].instance.pageUp)

    def updEvent(self, direction, visible=True):
        if self["list"].selEntry(direction, visible):
            self.moveTimeLines(True)

    # ------------------------------------------------------------------
    # Bouquet navigation.
    # ------------------------------------------------------------------

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
        cfg = config.epgselection.grid
        now = time() - cfg.histminutes.value * 60
        self.ask_time = now - now % (cfg.roundto.value * 60)
        if "primetime" in cfg.startmode.value:
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

    # ------------------------------------------------------------------
    # Date/time jump — graph-specific rounding and refill.
    # ------------------------------------------------------------------

    def _onDateTimeEntered(self, jumpTime):
        cfg = config.epgselection.grid
        jumpTime -= jumpTime % (cfg.roundto.value * 60)
        self["list"].resetOffset()
        self["list"].fillGraphEPG(None, jumpTime)
        self.moveTimeLines(True)
        self.ask_time = jumpTime

    # ------------------------------------------------------------------
    # Number-key shortcuts.
    # ------------------------------------------------------------------

    def _numberKeyPressed(self, number):
        cfg = config.epgselection.grid
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

        elif number == 7:
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

    # ------------------------------------------------------------------
    # Sort is not applicable to grid EPG.
    # ------------------------------------------------------------------

    def sortEPG(self):
        pass
# lib/python/Screens/EpgSelectionInfobarGrid.py
#
# New file (2026). Concrete EPG screen for infobar graphical grid mode.
#
# Handles EPG_TYPE_INFOBARGRAPH.
# Similar to EpgSelectionGrid but uses config.epgselection.infobar and skinName
# "QuickGraphEPG". No height-switch (key 7 is unused) — that is GRAPH-only.


class EPGSelectionInfobarGrid(EPGSelectionBase, EPGBouquetSelection,
                               EPGServiceZap, EPGStandardButtons, EPGGridNavigation):
    """Infobar graphical grid EPG screen (EPG_TYPE_INFOBARGRAPH)."""

    def __init__(self, session, zapFunc=None, startBouquet=None,
                 startRef=None, bouquets=None, graphic=False):
        self.type = EPG_TYPE_INFOBARGRAPH
        self._cfg = EPGSettings(EPG_TYPE_INFOBARGRAPH)
        self.activeList = ""

        now = time() - config.epgselection.infobar.histminutes.value * 60
        self.ask_time = now - now % (config.epgselection.infobar.roundto.value * 60)

        EPGSelectionBase.__init__(self, session, config.epgselection.infobar,
                                  startBouquet, startRef, bouquets)
        self.skinName = "GraphicalInfoBarEPG"
        EPGServiceZap.__init__(self, zapFunc)
        EPGBouquetSelection.__init__(self, graphic)

        self["list"] = EPGListGrid(session, config.epgselection.infobar,
                                   EPG_TYPE_INFOBARGRAPH, self.onSelectionChanged,
                                   graphic=graphic,
                                   overjump_empty=config.epgselection.overjump.value,
                                   time_epoch=config.epgselection.infobar.prevtimeperiod.value)

        # Opt-in: skins can request Label widgets instead of Pixmap for the
        # timeline graphics, e.g. to apply icon-font glyphs.
        graphicControl = Label if parameters.get("EPGNativeControls", 0) else Pixmap

        self["timeline_text"] = TimelineText(epgType=EPG_TYPE_INFOBARGRAPH, graphic=graphic)
        self["primetime"] = Label(_("PRIMETIME"))
        self["change_bouquet"] = Label(_("CHANGE BOUQUET"))
        self["jump"] = Label(_("JUMP 24 HOURS"))
        self["page"] = Label(_("PAGE UP/DOWN"))
        self["timeline_now"] = graphicControl()

        self.time_lines = []
        for i in range(MAX_TIMELINES):
            pm = graphicControl()
            self.time_lines.append(pm)
            self[f"timeline{i}"] = pm

        from enigma import eTimer as _eTimer
        self.updateTimelineTimer = _eTimer()
        self.updateTimelineTimer.callback.append(self.moveTimeLines)
        self.updateTimelineTimer.start(60000)

        from Components.ActionMap import HelpableNumberActionMap
        self["input_actions"] = HelpableNumberActionMap(self, "NumberActions", {
            "1": (lambda: self._numberKeyPressed(1), _("Reduce time scale")),
            "2": (lambda: self._numberKeyPressed(2), _("Page up")),
            "3": (lambda: self._numberKeyPressed(3), _("Increase time scale")),
            "4": (lambda: self._numberKeyPressed(4), _("Step left")),
            "5": (lambda: self._numberKeyPressed(5), _("Jump to current time")),
            "6": (lambda: self._numberKeyPressed(6), _("Step right")),
            "8": (lambda: self._numberKeyPressed(8), _("Page down")),
            "9": (lambda: self._numberKeyPressed(9), _("Jump to prime time")),
            "0": (lambda: self._numberKeyPressed(0), _("Go to first channel")),
        }, prio=-1, description=_("Infobar graph EPG navigation"))

        self.addEpgActions({
            "info": (self.Info, _("Event info")),
            "infolong": (self.InfoLong, _("Single EPG")),
            "menu": (self.createMenu, _("Menu")),
            "nextBouquet": (self.nextBouquet, _("Next bouquet")),
            "prevBouquet": (self.prevBouquet, _("Previous bouquet")),
            "input_date_time": (self.enterDateTime, _("Jump to date/time")),
            "nextService": (self.nextService, _("CHANNEL+ button (setup in menu)")),
            "prevService": (self.prevService, _("CHANNEL- button (setup in menu)")),
            "epg": (self.epgButtonPressed, _("Single EPG")),
            "epglong": (self.epgButtonPressedLong, _("EPG button long (setup in menu)")),
            "tv": (self.toggleBouquetList, _("Toggle bouquet list")),
            "tvlong": (self.togglePIG, _("Toggle picture in graphics")),
        })
        self.addCursorActions({
            "left": (self.leftPressed, _("Go to previous event")),
            "right": (self.rightPressed, _("Go to next event")),
        })

    def onCreate(self):
        self._populateBouquetList()
        self["list"].recalcEntrySize()
        serviceref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
        self["list"].fillGraphEPG(self.services, self.ask_time)
        self["list"].setCurrentlyPlaying(serviceref)
        self["list"].moveToService(self.getStartService())
        self["list"].fillGraphEPG(None, self.ask_time, True)
        self["list"].setShowServiceMode(config.epgselection.infobar.servicetitle_mode.value)
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
        self["list"].prevPage()

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
        cfg = config.epgselection.infobar
        now = time() - cfg.histminutes.value * 60
        self.ask_time = now - now % (cfg.roundto.value * 60)
        self["list"].resetOffset()
        self["list"].fillGraphEPG(self.services, self.ask_time)
        serviceref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
        self["list"].fillGraphEPG(None, self.ask_time, True)
        self["list"].moveToService(serviceref)
        name = self.getCurrentBouquetName()
        self.setTitle(name)
        self.moveTimeLines(True)

    def _onDateTimeEntered(self, jumpTime):
        cfg = config.epgselection.infobar
        jumpTime -= jumpTime % (cfg.roundto.value * 60)
        self["list"].resetOffset()
        self["list"].fillGraphEPG(None, jumpTime)
        self.moveTimeLines(True)
        self.ask_time = jumpTime

    def _numberKeyPressed(self, number):
        cfg = config.epgselection.infobar
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
# lib/python/Screens/EpgSelectionInfobarSingle.py
#
# New file (2026). Concrete EPG screen for infobar single-channel mode.
#
# Handles EPG_TYPE_INFOBAR.
# Like EpgSelectionSingle but attached to the infobar overlay.
# Uses config.epgselection.infobar subsection for list config.


class EPGSelectionInfobarSingle(EPGSelectionBase, EPGServiceNumberSelection,
                                EPGServiceBrowse, EPGServiceZap, EPGStandardButtons):
    """Infobar single-channel EPG overlay (EPG_TYPE_INFOBAR text mode)."""

    def __init__(self, session, zapFunc=None, startBouquet=None,
                 startRef=None, bouquets=None):
        self.type = EPG_TYPE_INFOBAR
        self._cfg = EPGSettings(EPG_TYPE_INFOBAR)
        self.activeList = ""

        EPGSelectionBase.__init__(self, session, config.epgselection.infobar,
                                  startBouquet, startRef, bouquets)
        self.skinName = "QuickEPG"
        EPGServiceZap.__init__(self, zapFunc)
        EPGServiceBrowse.__init__(self)
        EPGServiceNumberSelection.__init__(self)

        self["list"] = EPGListSingle(session, config.epgselection.infobar,
                                     EPG_TYPE_INFOBAR, self.onSelectionChanged)

        self.addEpgActions({
            "info": (self.Info, _("Event info")),
            "infolong": (self.InfoLong, _("Single EPG")),
            "menu": (self.createMenu, _("Menu")),
            "nextBouquet": (self.nextBouquet, _("Next bouquet")),
            "prevBouquet": (self.prevBouquet, _("Previous bouquet")),
            "input_date_time": (self.enterDateTime, _("Jump to date/time")),
            "nextService": (self.prevPage, _("Page up")),
            "prevService": (self.nextPage, _("Page down")),
            "epg": (self.epgButtonPressed, _("Single EPG")),
            "epglong": (self.epgButtonPressedLong, _("EPG button long (setup in menu)")),
        })
        self.addCursorActions({
            "left": (self.prevService, _("Go to previous channel")),
            "right": (self.nextService, _("Go to next channel")),
        })

    def onCreate(self):
        self.setTitle(_("Infobar EPG"))
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

    def startRefreshTimer(self):
        if hasattr(config.epg, "pollinterval"):
            self.refreshTimer.start(config.epg.pollinterval.value * 60 * 1000, True)
# lib/python/Screens/EpgSelectionMulti.py
#
# New file (2026). Concrete EPG screen for multi-service mode.
#
# Handles EPG_TYPE_MULTI: shows one row per service with current + next event.
# Uses EPGListMulti for the list widget and EPGBouquetSelection for bouquet browsing.


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
            "info": (self.Info, _("Event info")),
            "infolong": (self.InfoLong, _("Single EPG")),
            "menu": (self.createMenu, _("Menu")),
            "nextBouquet": (self.nextBouquet, _("Next bouquet")),
            "prevBouquet": (self.prevBouquet, _("Previous bouquet")),
            "nextService": (self.prevPage, _("Page up")),
            "prevService": (self.nextPage, _("Page down")),
            "input_date_time": (self.enterDateTime, _("Jump to date/time")),
            "epg": (self.epgButtonPressed, _("Single EPG")),
            "epglong": (self.epgButtonPressedLong, _("EPG button long (setup in menu)")),
            "tv": (self.toggleBouquetList, _("Toggle bouquet list")),
        })
        self.addCursorActions({
            "left": (self.leftPressed, _("Go to previous event")),
            "right": (self.rightPressed, _("Go to next event")),
        })

    # ------------------------------------------------------------------
    # onCreate — populate list from start bouquet.
    # ------------------------------------------------------------------

    def onCreate(self):
        self.setTitle(_("Multi Channel EPG"))
        self._populateBouquetList()
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

    # ------------------------------------------------------------------
    # Bouquet change — reload services from the new bouquet and refill.
    # ------------------------------------------------------------------

    def bouquetChanged(self):
        bouquet = self.getCurrentBouquet()
        if bouquet:
            self.services = self._getBouquetServices(bouquet)
            self.setTitle(self.getCurrentBouquetName())
            self["list"].fillMultiEPG(self.services, self.ask_time)

    # ------------------------------------------------------------------
    # Multi-EPG has next/prev for events in time (not just services).
    # ------------------------------------------------------------------

    def leftPressed(self):
        self["list"].updateMultiEPG(-1)

    def rightPressed(self):
        self["list"].updateMultiEPG(1)

    def _onDateTimeEntered(self, jumpTime):
        self.ask_time = jumpTime
        self["list"].fillMultiEPG(self.services, jumpTime)
# lib/python/Screens/EpgSelectionSimilar.py
#
# New file (2026). Similar-events EPG screen.
#
# Handles EPG_TYPE_SIMILAR: shows all broadcasts that match a given event name.
# Opened from EventView with (service_ref_str, eventid).
# No bouquet browsing; navigation is within the similar-events result set.


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

        # No bouquets for similar EPG — pass empty/None values.
        EPGSelectionBase.__init__(self, session, config.epgselection.single, None, None, None)
        self.skinName = "EPGSelection"
        EPGServiceZap.__init__(self, zapFunc)

        self["list"] = EPGListSingle(session, config.epgselection.single,
                                     EPG_TYPE_SIMILAR, self.onSelectionChanged)

        self.addEpgActions({
            "info": (self.Info, _("Event info")),
            "infolong": (self.InfoLong, _("Event info")),
            "menu": (self.createMenu, _("Menu")),
        })

    def onCreate(self):
        self.setTitle(_("Similar EPG"))
        self["list"].fillSimilarList(self.currentService.toString(), self.eventid)
        self.onSelectionChanged()

    def refreshlist(self):
        self["list"].fillSimilarList(self.currentService.toString(), self.eventid)
        self.onSelectionChanged()

    def getCurrentBouquet(self):
        return self.startBouquet
# lib/python/Screens/EpgSelectionSingle.py
#
# New file (2026). Concrete EPG screen for single-channel and enhanced modes.
#
# Handles EPG_TYPE_SINGLE and EPG_TYPE_ENHANCED.
# The two modes share the same screen; epgType selects title and list config.
#
# Initialisation order matters:
#   1. Set self.type / self._cfg / self.activeList (needed by EPGSelectionBase.__init__)
#   2. Call EPGSelectionBase.__init__ (calls Screen.__init__, sets self.session + self.epgConfig)
#   3. Call EPGServiceZap.__init__ (needs self.session.nav)
#   4. Call EPGServiceBrowse.__init__ (needs self.epgConfig, self.startRef)
#   5. Call EPGServiceNumberSelection.__init__ (adds action maps)
#   6. Add the list widget (selChangedCB = self.onSelectionChanged from base)


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

        # Step 2: base screen init — calls Screen.__init__, sets self.epgConfig,
        #         self.startBouquet, self.startRef, self.bouquets, action maps.
        EPGSelectionBase.__init__(self, session, config.epgselection.single,
                                  startBouquet, startRef, bouquets)
        self.skinName = "EPGSelection"
        # Step 3: zap mixin needs self.session.nav (available after Screen.__init__).
        EPGServiceZap.__init__(self, zapFunc)
        # Step 4: browse/bouquet mixin needs self.epgConfig and self.startRef.
        EPGServiceBrowse.__init__(self)
        # Step 5: number-key action map.
        EPGServiceNumberSelection.__init__(self)

        # onSelectionChanged (from base) updates Event/Service widgets + green button.
        self["list"] = EPGListSingle(session, config.epgselection.single,
                                     epgType, self.onSelectionChanged)

        # Add type-specific extra actions on top of the base epgactions map.
        self.addEpgActions({
            "epg": (self.epgButtonPressed, _("Event info") if epgType == EPG_TYPE_SINGLE else _("Single EPG")),
            "epglong": (self.epgButtonPressedLong, _("EPG button long (setup in menu)")),
            "info": (self.Info, _("Event info")),
            "menu": (self.createMenu, _("Menu")),
            "nextService": (self.nextService, _("Go to next channel")),
            "prevService": (self.prevService, _("Go to previous channel")),
        })
        if epgType == EPG_TYPE_ENHANCED:
            self.addEpgActions({
                "infolong": (self.InfoLong, _("Single EPG")),
                "nextBouquet": (self.nextBouquet, _("Next bouquet")),
                "prevBouquet": (self.prevBouquet, _("Previous bouquet")),
                "input_date_time": (self.enterDateTime, _("Jump to date/time")),
            })
        self.addCursorActions({
            "left": (self.prevPage, _("Page up")),
            "right": (self.nextPage, _("Page down")),
        })

    # ------------------------------------------------------------------
    # onCreate — called from onLayoutFinish after screen layout is applied.
    # ------------------------------------------------------------------

    def onCreate(self):
        if self.type == EPG_TYPE_ENHANCED:
            self.setTitle(_("Enhanced EPG"))
        else:
            self.setTitle(_("Single Channel EPG"))
        self._populateBouquetList()
        self._fillList(self.startRef)
        self.onSelectionChanged()
        self.startRefreshTimer()

    # ------------------------------------------------------------------
    # List population helpers.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Service navigation — called by EPGServiceBrowse when bouquet changes.
    # ------------------------------------------------------------------

    def serviceChanged(self):
        service = self.getCurrentService()
        if service:
            self._fillList(service)

    def moveToService(self, service):
        self._fillList(service)

    # ------------------------------------------------------------------
    # Sort toggle — ATV-specific; not in OpenViX (no sortSingleEPG there).
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # CH+/CH- in single EPG moves the calling channel list (serviceChangeCB).
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Auto-refresh — restarts the poll timer after each fill.
    # ------------------------------------------------------------------

    def startRefreshTimer(self):
        if hasattr(config.epg, "pollinterval"):
            self.refreshTimer.start(config.epg.pollinterval.value * 60 * 1000, True)
# lib/python/Screens/EpgSelectionVertical.py
#
# New file (2026). Concrete EPG screen for vertical multi-column mode.
#
# Handles EPG_TYPE_VERTICAL (ATV-specific, no OpenViX equivalent).
# Layout: a hidden MenuList tracks channel position; 3 or 5 visible EPGListVertical
# columns (list1–list5) each show one channel's schedule.  The number of visible
# columns is controlled by the PIG setting: PIG=on → 3 channels (Fields=4),
# PIG=off → 5 channels (Fields=6).
#
# activeList is 1–(Fields-1) — the column that currently has focus.


class EPGSelectionVertical(EPGSelectionBase, EPGBouquetSelection,
                           EPGServiceZap, EPGStandardButtons):
    """Vertical multi-column EPG screen (EPG_TYPE_VERTICAL, ATV-specific)."""

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
            "5": (lambda: self._numberKeyPressed(5), _("Set base time")),
        }, prio=-1, description=_("Vertical EPG navigation"))

        self.addEpgActions({
            "info": (self.Info, _("Event info")),
            "infolong": (self.InfoLong, _("Single EPG")),
            "menu": (self.createMenu, _("Menu")),
            "nextBouquet": (self.nextBouquet, _("Next bouquet")),
            "prevBouquet": (self.prevBouquet, _("Previous bouquet")),
            "input_date_time": (self.enterDateTime, _("Jump to date/time")),
            "nextService": (self.nextPage, _("CHANNEL+ button (setup in menu)")),
            "prevService": (self.prevPage, _("CHANNEL- button (setup in menu)")),
            "epg": (self.epgButtonPressed, _("Single EPG")),
            "epglong": (self.epgButtonPressedLong, _("EPG button long (setup in menu)")),
            "tv": (self.toggleBouquetList, _("Toggle bouquet list")),
            "tvlong": (self.togglePIG, _("Toggle picture in graphics")),
        })
        self.addCursorActions({
            "left": (self.leftPressed, _("Go to previous channel")),
            "right": (self.rightPressed, _("Go to next channel")),
        })

    # ------------------------------------------------------------------
    # onCreate — populate from start bouquet then fill columns.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Overridden onSelectionChanged — uses the active column instead of self["list"].
    # ------------------------------------------------------------------

    def onSelectionChanged(self):
        cur = self[f"list{self.activeList}"].getCurrent()
        event = cur[0] if cur else None
        service = cur[1] if cur else None
        self["Event"].newEvent(event)
        self["Service"].newService(service.ref if service else None)
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

    # ------------------------------------------------------------------
    # Navigation — overrides the base class methods for vertical EPG.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Bouquet navigation.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Date/time jump.
    # ------------------------------------------------------------------

    def _onDateTimeEntered(self, jumpTime):
        if jumpTime > time():
            self.ask_time = jumpTime
            self.updateVerticalEPG()
        else:
            self.ask_time = -1

    # ------------------------------------------------------------------
    # Number-key shortcuts.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Channel list helpers.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Column update — fills each visible column from myServices.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Sync helpers — keep all columns aligned when scrolling.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Time helpers.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Sort is not applicable to vertical EPG.
    # ------------------------------------------------------------------

    def sortEPG(self):
        pass
# lib/python/Screens/EpgSelectionRouter.py
#
# New file (2026). Factory/router for the new split EPG screen classes.
#
# EPGSelection() keeps the old constructor signature and returns the matching
# concrete screen, so existing session.open(EPGSelection, ...) callers keep working.


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
