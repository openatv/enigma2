from datetime import datetime
from os import stat, statvfs
from time import localtime, mktime, strftime, time

from enigma import BT_SCALE, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER, eEPGCache, eLabel, eListbox, eListboxPythonMultiContent, eSize, eTimer

from Scheduler import AFTEREVENT as SCHEDULER_AFTEREVENT, SchedulerEntry, TIMERTYPE as SCHEDULER_TYPE, functionTimer
from RecordTimer import AFTEREVENT as RECORD_AFTEREVENT, RecordTimerEntry, TIMERTYPE as RECORD_TIMERTYPE, parseEvent
from ServiceReference import ServiceReference
from skin import parseBoolean, parseFont, parseInteger
from timer import TimerEntry
from Components.ActionMap import HelpableActionMap
from Components.config import ConfigClock, ConfigDateTime, ConfigIP, ConfigSelection, ConfigSubDict, ConfigText, ConfigYesNo, config
from Components.GUIComponent import GUIComponent
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.SystemInfo import BoxInfo
from Components.TimerSanityCheck import TimerSanityCheck
from Components.UsageConfig import defaultMoviePath, preferredTimerPath
from Components.Sources.Event import Event
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.LocationBox import DEFAULT_INHIBIT_DEVICES, MovieLocationBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen, ScreenSummary
from Screens.Setup import Setup
from Screens.TagEditor import TagEditor
from Tools.Alternatives import GetWithAlternative
from Tools.BoundFunction import boundFunction
from Tools.Conversions import fuzzyDate, scaleNumber
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.FallbackTimer import FallbackTimerList, FallbackTimerDirs
from Tools.LoadPixmap import LoadPixmap

# Timer modes.
#
MODE_SCHEDULER = 0
MODE_ENERGY = 1
MODE_SLEEP = 2
MODE_RECORD = 3
MODE_CONFLICT = 4
#
# Timer mode data.
#
MODE_DATA = {  # Skin name, Screen title, ActionMap description
	MODE_SCHEDULER: ("SchedulerOverview", _("Scheduler Overview"), _("Scheduler Actions")),
	MODE_ENERGY: ("EnergyTimerOverview", _("EnergyTimer Overview"), _("EnergyTimer Actions")),
	MODE_SLEEP: ("SleepTimerOverview", _("SleepTimer Overview"), _("SleepTimer Actions")),
	MODE_RECORD: ("RecordTimerOverview", _("RecordTimer Overview"), _("RecordTimer Actions")),
	MODE_CONFLICT: ("ConflictTimerOverview", _("ConflictTimer Overview"), _("ConflictTimer Actions"))
}
#
# Timer mode data indexes.
#
MODE_DATA_SKIN = 0
MODE_DATA_TITLE = 1
MODE_DATA_ACTIONS = 2

DAYS_IN_WEEK = 7
DAY_LIST = [
	"Mon",
	"Tue",
	"Wed",
	"Thu",
	"Fri",
	"Sat",
	"Sun"
]
WEEKDAYS = [
	"Mon",
	"Tue",
	"Wed",
	"Thu",
	"Fri"
]
WEEKENDS = [
	"Sat",
	"Sun"
]
DAY_NAMES = [
	("Mon", _("Monday")),
	("Tue", _("Tuesday")),
	("Wed", _("Wednesday")),
	("Thu", _("Thursday")),
	("Fri", _("Friday")),
	("Sat", _("Saturday")),
	("Sun", _("Sunday"))
]
SHORT_DAY_NAMES = [
	("Mon", _("Mon")),
	("Tue", _("Tue")),
	("Wed", _("Wed")),
	("Thu", _("Thu")),
	("Fri", _("Fri")),
	("Sat", _("Sat")),
	("Sun", _("Sun"))
]
REPEAT_CHOICES = [
	("once", _("Once")),
	("repeated", _("Repeated"))
]
REPEAT_OPTIONS = [
	("weekly", _("Weekly")),
	("daily", _("Daily")),
	("weekdays", _("Mon-Fri")),
	("weekends", _("Sat-Sun")),
	("user", _("User defined"))
]
TIMER_STATES = {
	TimerEntry.StateWaiting: _("Waiting"),
	TimerEntry.StatePrepared: _("About to start"),
	TimerEntry.StateRunning: _("Running"),
	TimerEntry.StateEnded: _("Done"),
	TimerEntry.StateFailed: _("Failed"),
	TimerEntry.StateDisabled: _("Disabled")
}
DEEPSTANDBY_SUPPORT = BoxInfo.getItem("DeepstandbySupport")

SCHEDULER_TYPES = {
	SCHEDULER_TYPE.NONE: "nothing",
	SCHEDULER_TYPE.WAKEUP: "wakeup",
	SCHEDULER_TYPE.WAKEUPTOSTANDBY: "wakeuptostandby",
	SCHEDULER_TYPE.AUTOSTANDBY: "autostandby",
	SCHEDULER_TYPE.AUTODEEPSTANDBY: "autodeepstandby",
	SCHEDULER_TYPE.STANDBY: "standby",
	SCHEDULER_TYPE.DEEPSTANDBY: "deepstandby",
	SCHEDULER_TYPE.REBOOT: "reboot",
	SCHEDULER_TYPE.RESTART: "restart",
	SCHEDULER_TYPE.OTHER: "other"
}

SCHEDULER_VALUES = dict([(SCHEDULER_TYPES[x], x) for x in SCHEDULER_TYPES.keys()])
SCHEDULER_TYPE_NAMES = {
	SCHEDULER_TYPE.AUTODEEPSTANDBY: _("Auto deep standby") if DEEPSTANDBY_SUPPORT else _("Auto shut down"),
	SCHEDULER_TYPE.AUTOSTANDBY: _("Auto standby"),
	SCHEDULER_TYPE.DEEPSTANDBY: _("Deep standby") if DEEPSTANDBY_SUPPORT else _("Shut down"),
	SCHEDULER_TYPE.NONE: _("Do nothing"),
	SCHEDULER_TYPE.REBOOT: _("Reboot"),
	SCHEDULER_TYPE.RESTART: _("Restart GUI"),
	SCHEDULER_TYPE.STANDBY: _("Standby"),
	SCHEDULER_TYPE.WAKEUP: _("Wake up"),
	SCHEDULER_TYPE.WAKEUPTOSTANDBY: _("Wake up to standby")
}
SCHEDULER_AFTER_EVENTS = {
	SCHEDULER_AFTEREVENT.NONE: "nothing",
	SCHEDULER_AFTEREVENT.WAKEUPTOSTANDBY: "wakeuptostandby",
	SCHEDULER_AFTEREVENT.STANDBY: "standby",
	SCHEDULER_AFTEREVENT.DEEPSTANDBY: "deepstandby"
}
SCHEDULER_AFTER_VALUES = dict([(SCHEDULER_AFTER_EVENTS[x], x) for x in SCHEDULER_AFTER_EVENTS.keys()])
SCHEDULER_AFTER_EVENT_NAMES = {
	SCHEDULER_AFTEREVENT.NONE: _("Do nothing"),
	SCHEDULER_AFTEREVENT.WAKEUPTOSTANDBY: _("Wake up to standby"),
	SCHEDULER_AFTEREVENT.STANDBY: _("Go to standby"),
	SCHEDULER_AFTEREVENT.DEEPSTANDBY: _("Go to deep standby") if DEEPSTANDBY_SUPPORT else _("Shut down")
}

RECORDTIMER_TYPES = {
	RECORD_TIMERTYPE.RECORD: "record",
	RECORD_TIMERTYPE.ZAP: "zap",
	RECORD_TIMERTYPE.ZAP_RECORD: "zap+record"
}
RECORDTIMER_VALUES = dict([(RECORDTIMER_TYPES[x], x) for x in RECORDTIMER_TYPES.keys()])
RECORDTIMER_TYPE_NAMES = {
	RECORD_TIMERTYPE.RECORD: _("Record"),
	RECORD_TIMERTYPE.ZAP: _("Zap"),
	RECORD_TIMERTYPE.ZAP_RECORD: _("Zap and record")
}
RECORDTIMER_AFTER_EVENTS = {
	RECORD_AFTEREVENT.NONE: "nothing",
	RECORD_AFTEREVENT.STANDBY: "standby",
	RECORD_AFTEREVENT.DEEPSTANDBY: "deepstandby",
	RECORD_AFTEREVENT.AUTO: "auto"
}
RECORDTIMER_AFTER_VALUES = dict([(RECORDTIMER_AFTER_EVENTS[x], x) for x in RECORDTIMER_AFTER_EVENTS.keys()])
RECORDTIMER_AFTER_EVENT_NAMES = {
	RECORD_AFTEREVENT.AUTO: _("Auto"),
	RECORD_AFTEREVENT.DEEPSTANDBY: _("Go to deep standby") if DEEPSTANDBY_SUPPORT else _("Shut down"),
	RECORD_AFTEREVENT.NONE: _("Do nothing"),
	RECORD_AFTEREVENT.STANDBY: _("Go to standby")
}
UNKNOWN = _("Unknown!")

onRecordTimerCreate = []  # Hook for plugins to enhance the RecordTimer screen.
onRecordTimerSetup = []  # Hook for plugins to enhance the RecordTimer screen.
onRecordTimerSave = []  # Hook for plugins to enhance the RecordTimer screen.
onRecordTimerChannelChange = []  # Hook for plugins to enhance the RecordTimer screen.
onSchedulerCreate = []  # Hook for plugins to enhance the Scheduler screen.
onSchedulerSetup = []  # Hook for plugins to enhance the Scheduler screen.
onSchedulerSave = []  # Hook for plugins to enhance the Scheduler screen.


class TimerListBase(GUIComponent):
	GUI_WIDGET = eListbox

	def __init__(self, timerList):
		GUIComponent.__init__(self)
		self.timerList = timerList
		self.timerListWidget = eListboxPythonMultiContent()
		self.timerListWidget.setBuildFunc(self.buildTimerEntry)
		self.timerListWidget.setList(timerList)
		self.timerNameFont = parseFont("Regular;20")
		self.statusFont = parseFont("Regular;20")
		self.detailFont = parseFont("Regular;18")
		self.itemHeight = 50  # itemHeight must equal topHeight + bottomHeight + showSeparator (2 pixels)!
		self.topHeight = 24
		self.bottomHeight = 24
		self.showSeparator = True
		self.indent = 20
		self.iconMargin = 10
		self.statusOffset = 0
		self.satPosLeft = 200
		self.iconWait = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/timer_wait.png"))
		self.iconWidth = self.iconWait.size().width()  # It is intended that all icons have the same size but icons will now be scaled to fit.
		self.iconHeight = self.iconWait.size().height()
		self.iconRecording = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/timer_rec.png"))
		self.iconPrepared = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/timer_prep.png"))
		self.iconDone = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/timer_done.png"))
		self.iconRepeat = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/timer_rep.png"))
		self.iconOnce = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/timer_once.png"))
		self.iconZapped = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/timer_zap.png"))
		self.iconDisabled = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/timer_off.png"))
		self.iconFailed = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/timer_failed.png"))
		self.iconAutoTimer = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/timer_autotimer.png"))
		self.iconIceTVTimer = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/timer_icetv.png"))
		self.line = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "div-h.png"))

	def postWidgetCreate(self, instance):
		instance.setContent(self.timerListWidget)
		self.instance = instance

	def applySkin(self, desktop, parent):
		def bottomHeight(value):
			self.bottomHeight = parseInteger(value, 24)

		def detailFont(value):
			self.detailFont = parseFont(value, ((1, 1), (1, 1)))

		def iconMargin(value):
			self.iconMargin = parseInteger(value, 10)

		def itemHeight(value):
			self.itemHeight = parseInteger(value, 50)

		def indent(value):
			self.indent = parseInteger(value, 20)

		def satPosLeft(value):
			self.satPosLeft = parseInteger(value, 200)

		def showSeparator(value):
			self.showSeparator = parseBoolean("showseparator", value)

		def statusFont(value):
			self.statusFont = parseFont(value, ((1, 1), (1, 1)))

		def statusOffset(value):
			self.statusOffset = parseInteger(value, 0)

		def timerNameFont(value):
			self.timerNameFont = parseFont(value, ((1, 1), (1, 1)))

		def topHeight(value):
			self.topHeight = parseInteger(value, 24)

		for attrib, value in self.skinAttributes[:]:
			method = locals().get(attrib)
			if method and callable(method):
				method(value)
				self.skinAttributes.remove((attrib, value))
		self.timerListWidget.setItemHeight(self.itemHeight)
		self.timerListWidget.setFont(0, self.timerNameFont)
		self.timerListWidget.setFont(1, self.statusFont)
		self.timerListWidget.setFont(2, self.detailFont)
		return GUIComponent.applySkin(self, desktop, parent)

	def getList(self):
		return self.timerList

	def setList(self, timerList):
		self.timerList = timerList
		self.timerListWidget.setList(timerList)

	def count(self):
		return len(self.timerList)

	def getCurrent(self):
		current = self.timerListWidget.getCurrentSelection()
		return current and current[0]

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def setCurrentIndex(self, index):
		self.instance.moveSelectionTo(index)

	def entryRemoved(self, index):
		self.timerListWidget.entryRemoved(index)

	def invalidate(self):
		self.timerListWidget.invalidate()

	def enableAutoNavigation(self, enabled):
		if self.instance:
			self.instance.enableAutoNavigation(enabled)


# Widget item layout:
#
# <Repeat icon> <Name of timer>          <At end>
# <State icon>  <State>   <Start, End (Duration)>
#
class SchedulerList(TimerListBase):
	def __init__(self, timerList):
		TimerListBase.__init__(self, timerList)

	def buildTimerEntry(self, timer, processed):
		width = self.timerListWidget.getItemSize().width()
		height = self.timerListWidget.getItemSize().height()
		if timer.timerType in (SCHEDULER_TYPE.AUTOSTANDBY, SCHEDULER_TYPE.AUTODEEPSTANDBY):
			repeatIcon = self.iconOnce if timer.autosleeprepeat == "once" else self.iconRepeat
			topText = None
			bottomText = _("Delay: %s") % ngettext("%d Minute", "%d Minutes", timer.autosleepdelay) % timer.autosleepdelay
		else:
			repeatIcon = self.iconRepeat if timer.repeated else self.iconOnce
			topText = _("At end: %s") % SCHEDULER_AFTER_EVENT_NAMES.get(timer.afterEvent, UNKNOWN)
			begin = fuzzyDate(timer.begin)
			if timer.repeated:
				repeatedText = []
				flags = timer.repeated
				for dayName in DAY_LIST:
					if flags & 1 == 1:
						repeatedText.append(dayName)
					flags >>= 1
				if repeatedText == DAY_LIST:
					repeatedText = _("Everyday")
				elif repeatedText == WEEKDAYS:
					repeatedText = _("Weekdays")
				elif repeatedText == WEEKENDS:
					repeatedText = _("Weekends")
				else:
					repeatedText = ", ".join([dict(SHORT_DAY_NAMES).get(x) for x in repeatedText])
			else:
				repeatedText = begin[0]  # Date.
			duration = int((timer.end - timer.begin) / 60.0)
			bottomText = "%s %s ... %s  (%s)" % (repeatedText, begin[1], fuzzyDate(timer.end)[1], ngettext("%d Min", "%d Mins", duration) % duration)
		if processed:
			state = TIMER_STATES.get(TimerEntry.StateEnded)
			stateIcon = self.iconDone
		else:
			state = TIMER_STATES.get(timer.state, UNKNOWN)
			if timer.state == TimerEntry.StateWaiting:
				stateIcon = self.iconWait
			elif timer.state == TimerEntry.StatePrepared:
				stateIcon = self.iconPrepared
			elif timer.state == TimerEntry.StateRunning:
				stateIcon = self.iconZapped
			elif timer.state == TimerEntry.StateEnded:
				stateIcon = self.iconDone
			else:
				stateIcon = None
		if timer.disabled:
			state = TIMER_STATES.get(TimerEntry.StateDisabled, UNKNOWN)
			stateIcon = self.iconDisabled
		if timer.failed:
			state = TIMER_STATES.get(TimerEntry.StateFailed)
			stateIcon = self.iconFailed
		leftOffset = self.indent + self.iconWidth + self.iconMargin
		textWidth = width - leftOffset - self.indent
		halfWidth = textWidth // 2 - 5
		minorWidth = (textWidth - self.statusOffset) // 4 - 5
		majorWidth = textWidth - self.statusOffset - minorWidth - 10
		res = [None]
		if repeatIcon:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.indent, ((self.topHeight - self.iconHeight) // 2), self.iconWidth, self.iconHeight, repeatIcon, None, None, BT_SCALE))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, leftOffset, 0, halfWidth, self.topHeight, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, SCHEDULER_TYPE_NAMES.get(timer.timerType, UNKNOWN)))
		if topText:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, leftOffset + halfWidth + 10, 0, halfWidth, self.topHeight, 2, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, topText))
		if stateIcon:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.indent, self.topHeight + ((self.bottomHeight - self.iconHeight) // 2), self.iconWidth, self.iconHeight, stateIcon, None, None, BT_SCALE))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, leftOffset + self.statusOffset, self.topHeight, minorWidth, self.bottomHeight, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, state))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, leftOffset + self.statusOffset + minorWidth + 10, self.topHeight, majorWidth, self.bottomHeight, 2, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, bottomText))
		if self.showSeparator:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 0, height - 2, width, 2, self.line, None, None, BT_SCALE))
		return res


# Widget item layout:
#
# <Repeat icon> <Name of the timer>          <Service>
# <State icon> <State> <Orbital position> <Start, End>
#
class RecordTimerList(TimerListBase):
	def __init__(self, timerList):
		TimerListBase.__init__(self, timerList)

	def buildTimerEntry(self, timer, processed):
		width = self.timerListWidget.getItemSize().width()
		height = self.timerListWidget.getItemSize().height()
		repeatIcon = self.iconRepeat if timer.repeated else self.iconOnce
		if timer.isAutoTimer:
			repeatIcon = self.iconAutoTimer
		elif hasattr(timer, "ice_timer_id") and timer.ice_timer_id:
			repeatIcon = self.iconIceTVTimer
		serviceName = timer.service_ref.getServiceName()
		serviceNameWidth = eLabel.calculateTextSize(self.detailFont, serviceName, eSize(width, self.topHeight), False).width()
		# if 200 > width - serviceNameWidth - self.iconWidth - self.iconMargin:  # Limit the maximum size of the service name.
		# 	serviceNameWidth = width - 200 - self.iconWidth - self.iconMargin
		orbPos = self.getOrbitalPos(timer.service_ref, timer.state)
		orbPosWidth = eLabel.calculateTextSize(self.detailFont, orbPos, eSize(width, self.bottomHeight), False).width()
		begin = fuzzyDate(timer.begin)
		if timer.repeated:
			repeatedText = []
			flags = timer.repeated
			for dayName in DAY_LIST:
				if flags & 1 == 1:
					repeatedText.append(dayName)
				flags >>= 1
			if repeatedText == DAY_LIST:
				repeatedText = _("Everyday")
			elif repeatedText == WEEKDAYS:
				repeatedText = _("Weekdays")
			elif repeatedText == WEEKENDS:
				repeatedText = _("Weekends")
			else:
				repeatedText = ", ".join([dict(SHORT_DAY_NAMES).get(x) for x in repeatedText])
		else:
			repeatedText = begin[0]  # Date.
		# duration = int((timer.end - timer.begin) / 60.0)
		# durationText = ngettext("%d Min", "%d Mins", duration) % duration
		marginBefore = timer.marginBefore // 60
		eventDuration = (timer.eventEnd - timer.eventBegin) // 60
		marginAfter = timer.marginAfter // 60
		duration = marginBefore + eventDuration + marginAfter
		if marginBefore + marginAfter == 0:
			durationText = ngettext("%d Minute", "%d Minutes", duration) % eventDuration
		else:
			durationText = ngettext("%d + %d + %d Minute", "%d + %d + %d Minutes", duration) % (marginBefore, eventDuration, marginAfter)
		if timer.justplay:
			if timer.hasEndTime:
				text = "%s %s ... %s (%s, %s)" % (repeatedText, begin[1], fuzzyDate(timer.end)[1], _("ZAP"), durationText)
			else:
				# text = "%s %s (%s)" % (repeatedText, begin[1], _("ZAP as PiP") if timer.pipzap else _("ZAP"))
				text = "%s %s (%s)" % (repeatedText, begin[1], _("ZAP"))
		else:
			text = "%s %s ... %s  (%s)" % (repeatedText, begin[1], fuzzyDate(timer.end)[1], durationText)
		if not processed and (not timer.disabled or (timer.repeated and timer.isRunning() and not timer.justplay)):
			state = TIMER_STATES.get(timer.state, UNKNOWN)
			if timer.state == TimerEntry.StateWaiting:
				stateIcon = self.iconWait
			elif timer.state == TimerEntry.StatePrepared:
				stateIcon = self.iconPrepared
			elif timer.state == TimerEntry.StateRunning:
				stateIcon = self.iconZapped if timer.justplay else self.iconRecording
			elif timer.state == TimerEntry.StateEnded:
				stateIcon = self.iconDone
			else:
				stateIcon = None
		elif timer.disabled:
			state = TIMER_STATES.get(TimerEntry.StateDisabled, UNKNOWN)
			stateIcon = self.iconDisabled
		else:
			state = TIMER_STATES.get(TimerEntry.StateEnded)
			stateIcon = self.iconDone
		if timer.failed:
			state = TIMER_STATES.get(TimerEntry.StateFailed)
			stateIcon = self.iconFailed
		leftOffset = self.indent + self.iconWidth + self.iconMargin
		res = [None]
		if repeatIcon:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.indent, ((self.topHeight - self.iconHeight) // 2), self.iconWidth, self.iconHeight, repeatIcon, None, None, BT_SCALE))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, leftOffset, 0, width - leftOffset - serviceNameWidth - self.indent - 10, self.topHeight, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, timer.name))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, width - serviceNameWidth - self.indent, 0, serviceNameWidth, self.topHeight, 2, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, serviceName))
		if stateIcon:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.indent, self.topHeight + ((self.bottomHeight - self.iconHeight) // 2), self.iconWidth, self.iconHeight, stateIcon, None, None, BT_SCALE))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, leftOffset + self.statusOffset, self.topHeight, self.satPosLeft - leftOffset, self.bottomHeight, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, state))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, self.satPosLeft, self.topHeight, orbPosWidth, self.bottomHeight, 2, RT_HALIGN_LEFT | RT_VALIGN_CENTER, orbPos))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, self.satPosLeft + orbPosWidth + 10, self.topHeight, width - self.satPosLeft - orbPosWidth - self.indent - 10, self.bottomHeight, 2, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text))
		if self.showSeparator:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 0, height - 2, width, 2, self.line, None, None, BT_SCALE))
		return res

	def getOrbitalPos(self, ref, state):
		refStr = str(ref.sref) if hasattr(ref, "sref") else str(ref)
		refStr = refStr and GetWithAlternative(refStr)
		if "%3a//" in refStr:
			return _("Stream")
		op = int(refStr.split(":", 10)[6][:-4] or "0", 16)
		if op == 0xeeee:
			return _("DVB-T")
		if op == 0xffff:
			return _("DVB-C")
		if op > 1800:
			op = 3600 - op
			direction = "W"
		else:
			direction = "E"
		return ("%d.%d%s%s") % (op // 10, op % 10, "\u00B0", direction)


class TimerOverviewBase(Screen):
	def __init__(self, session, mode):
		Screen.__init__(self, session, enableHelp=True)
		self.skinName = [MODE_DATA[mode][MODE_DATA_SKIN], "TimerOverview", "TimerEditList"]  # TimerEditList is deprecated but kept for older skin compatibility.
		self.setTitle(MODE_DATA[mode][MODE_DATA_TITLE])
		self["key_info"] = StaticText("")
		self["key_red"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["description"] = Label("")
		self["actions"] = HelpableActionMap(self, ["TimerActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Close the screen")),
			"close": (self.keyClose, _("Close the screen and exit all menus")),
			"top": (self.keyGoTop, _("Move to first line / screen")),
			"pageUp": (self.keyGoPageUp, _("Move up a page / screen")),
			"up": (self.keyGoLineUp, _("Move up a line")),
			# "first": (self.keyTop, _("Move to first line / screen")),
			# "last": (self.keyBottom, _("Move to last line / screen")),
			"down": (self.keyGoLineDown, _("Move down a line")),
			"pageDown": (self.keyGoPageDown, _("Move down a page / screen")),
			"bottom": (self.keyGoBottom, _("Move to last line / screen"))
		}, prio=0, description=MODE_DATA[mode][MODE_DATA_ACTIONS])
		if mode == MODE_CONFLICT:
			self["key_blue"].setText(_("Ignore"))
			self["cancelActions"] = HelpableActionMap(self, ["TimerActions"], {
				"cleanup": (self.keyCancel, _("Cancel conflict resolution"))
			}, prio=0, description=MODE_DATA[mode][MODE_DATA_ACTIONS])
		else:
			self["key_green"] = StaticText(_("Add"))
			self["addActions"] = HelpableActionMap(self, ["TimerActions"], {
				"add": (self.addTimer, _("Add a new timer"))
			}, prio=0, description=MODE_DATA[mode][MODE_DATA_ACTIONS])
			self["cleanupActions"] = HelpableActionMap(self, ["TimerActions"], {
				"cleanup": (self.cleanupTimers, _("Clean up and remove all completed timers"))
			}, prio=-1, description=MODE_DATA[mode][MODE_DATA_ACTIONS])
			self["cleanupActions"].setEnabled(False)
		self["deleteActions"] = HelpableActionMap(self, ["TimerActions"], {
			"delete": (self.deleteTimer, _("Delete the currently selected timer"))
		}, prio=0, description=MODE_DATA[mode][MODE_DATA_ACTIONS])
		self["deleteActions"].setEnabled(False)
		self["editActions"] = HelpableActionMap(self, ["TimerActions"], {
			"edit": (self.editTimer, _("Edit the currently selected timer")),
			"log": (self.showTimerLog, _("Display log for the currently selected timer")),
		}, prio=0, description=MODE_DATA[mode][MODE_DATA_ACTIONS])
		self["editActions"].setEnabled(False)
		self["toggleActions"] = HelpableActionMap(self, ["TimerActions"], {
			"toggle": (self.toggleTimer, _("Toggle enable/disable of the currently selected timer"))
		}, prio=0, description=MODE_DATA[mode][MODE_DATA_ACTIONS])
		self["toggleActions"].setEnabled(False)
		self.onSelectionChanged = []
		self.loadTimerList()
		self.doChangeCallbackAppend()
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.doChangeCallbackRemove)

	def doChangeCallbackAppend(self):
		pass

	def doChangeCallbackRemove(self):
		pass

	def loadTimerList(self):
		pass

	def keyCancel(self):
		self.close()

	def keyClose(self):
		self.close(True)

	def onStateChange(self, entry):
		self.reloadTimerList()

	def reloadTimerList(self):
		length = self["timerlist"].count()
		self.loadTimerList()
		if length and length != self["timerlist"].count():
			self["timerlist"].entryRemoved(self["timerlist"].getCurrentIndex())
		else:
			self["timerlist"].invalidate()
		self.selectionChanged()

	def layoutFinished(self):
		self["timerlist"].enableAutoNavigation(False)
		self.selectionChanged()

	def selectionChanged(self):
		pass

	def addTimer(self):
		pass

	def cleanupTimers(self):
		self.session.openWithCallback(self.cleanupTimersCallback, MessageBox, _("Clean up and remove all completed timers?"), windowTitle=self.getTitle())

	def cleanupTimersCallback(self, answer):
		if answer:
			self.doCleanupTimers()
			self.reloadTimerList()

	def doCleanupTimers(self):
		pass

	def deleteTimer(self):
		pass

	def toggleTimer(self):
		pass

	def showTimerLog(self):
		timer = self["timerlist"].getCurrent()
		if timer:
			self.session.openWithCallback(self.editTimerCallback, TimerLog, timer)

	def keyGoTop(self):
		self["timerlist"].instance.goTop()
		self.selectionChanged()

	def keyGoPageUp(self):
		self["timerlist"].instance.goPageUp()
		self.selectionChanged()

	def keyGoLineUp(self):
		self["timerlist"].instance.goLineUp()
		self.selectionChanged()

	def keyGoLineDown(self):
		self["timerlist"].instance.goLineDown()
		self.selectionChanged()

	def keyGoPageDown(self):
		self["timerlist"].instance.goPageDown()
		self.selectionChanged()

	def keyGoBottom(self):
		self["timerlist"].instance.goBottom()
		self.selectionChanged()

	def createSummary(self):
		return TimerOverviewSummary


class TimerOverviewSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self["name"] = StaticText("")
		self["service"] = StaticText("")
		self["time"] = StaticText("")
		self["duration"] = StaticText("")
		self["state"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onSelectionChanged.append(self.selectionChanged)
		self.parent.selectionChanged()

	def removeWatcher(self):
		self.parent.onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self, name, service, time, duration, state):
		self["name"].setText(name)
		self["service"].setText(service)
		self["time"].setText(time)
		self["duration"].setText(duration)
		self["state"].setText(state)


class SchedulerOverview(TimerOverviewBase):
	def __init__(self, session):
		self["timerlist"] = SchedulerList([])
		TimerOverviewBase.__init__(self, session, mode=MODE_SCHEDULER)
		self.skinName.insert(0, "PowerTimerOverview")  # Fallback for old skins

	def doChangeCallbackAppend(self):
		self.session.nav.Scheduler.on_state_change.append(self.onStateChange)

	def doChangeCallbackRemove(self):
		self.session.nav.Scheduler.on_state_change.remove(self.onStateChange)

	def loadTimerList(self):
		def condition(element):
			return element[0].state == TimerEntry.StateEnded, element[0].begin

		timerList = []
		timerList.extend([(timer, False) for timer in self.session.nav.Scheduler.timer_list])
		timerList.extend([(timer, True) for timer in self.session.nav.Scheduler.processed_timers])
		if config.usage.timerlist_finished_timer_position.index:  # End of list.
			timerList.sort(key=condition)
		else:
			timerList.sort(key=lambda x: x[0].begin)
		self["timerlist"].setList(timerList)

	def selectionChanged(self):
		timer = self["timerlist"].getCurrent()
		if timer:
			# self["description"].setText(timer.description)
			self["description"].setText("")
			self["key_info"].setText(_("INFO"))
			self["editActions"].setEnabled(True)
			self["key_red"].setText(_("Delete"))
			self["deleteActions"].setEnabled(True)
			if timer.isRunning() and not timer.repeated:
				self["key_yellow"].setText("")
				self["toggleActions"].setEnabled(False)
			elif timer.disabled:
				self["key_yellow"].setText(_("Enable"))
				self["toggleActions"].setEnabled(True)
			else:
				self["key_yellow"].setText(_("Disable"))
				self["toggleActions"].setEnabled(True)
			time = "%s %s ... %s" % (fuzzyDate(timer.begin)[0], fuzzyDate(timer.begin)[1], fuzzyDate(timer.end)[1])
			duration = int((timer.end - timer.begin) / 60.0)
			for callback in self.onSelectionChanged:
				callback(SCHEDULER_TYPE_NAMES.get(timer.timerType, UNKNOWN), "", time, ngettext("%d Min", "%d Mins", duration) % duration, TIMER_STATES.get(timer.state, UNKNOWN))
		else:
			self["description"].setText("")
			self["key_info"].setText("")
			self["editActions"].setEnabled(False)
			self["key_red"].setText("")
			self["deleteActions"].setEnabled(False)
			self["key_yellow"].setText("")
			self["toggleActions"].setEnabled(False)
			for callback in self.onSelectionChanged:
				callback("", "", "", "", "")
		showCleanup = False
		for item in self["timerlist"].getList():
			if not item[0].disabled and item[1] is True:
				showCleanup = True
				break
		if showCleanup:
			self["key_blue"].setText(_("Cleanup"))
			self["cleanupActions"].setEnabled(True)
		else:
			self["key_blue"].setText("")
			self["cleanupActions"].setEnabled(False)

	def addTimer(self):
		now = int(time())
		begin = now + 60
		end = now + 120
		self.session.openWithCallback(self.addTimerCallback, SchedulerEdit, SchedulerEntry(begin, end, checkOldTimers=True))

	def addTimerCallback(self, result=(False,)):
		if isinstance(result, bool) and result:  # Special case for close recursive.
			self.close(True)
			return
		if result[0]:
			self.session.nav.Scheduler.record(result[1])
			self.loadTimerList()
			self.selectionChanged()

	def doCleanupTimers(self):
		self.session.nav.Scheduler.cleanup()

	def deleteTimer(self):
		if self["timerlist"].getCurrent():
			self.session.openWithCallback(self.deleteTimerCallback, MessageBox, _("Do you really want to delete this timer?"), default=False, windowTitle=self.getTitle())

	def deleteTimerCallback(self, answer):
		if answer:
			timer = self["timerlist"].getCurrent()
			if timer:
				timer.afterEvent = RECORD_AFTEREVENT.NONE
				self.session.nav.Scheduler.removeEntry(timer)
				self.reloadTimerList()

	def editTimer(self):
		timer = self["timerlist"].getCurrent()
		if timer:
			self.session.openWithCallback(self.editTimerCallback, SchedulerEdit, timer)

	def editTimerCallback(self, result):
		if isinstance(result, bool) and result:  # Special case for close recursive.
			self.close(True)
			return
		if result[0]:
			entry = result[1]
			self.session.nav.Scheduler.timeChanged(entry)
			print("[Timers] Scheduler updated.")
			self.reloadTimerList()
		else:
			print("[Timers] Scheduler not updated.")

	def toggleTimer(self):
		timer = self["timerlist"].getCurrent()
		if timer:
			if timer.disabled:
				print("[Timers] Try to enable Scheduler.")
				timer.enable()
			else:
				print("[Timers] Try to disable Scheduler.")
				if timer.isRunning():
					if timer.repeated:
						choiceList = (
							(_("Stop current event but not future events"), "stoponlycurrent"),
							(_("Stop current event and disable future events"), "stopall"),
							(_("Don't stop current event but disable future events"), "stoponlycoming")
						)
						self.session.openWithCallback(boundFunction(self.toggleTimerCallback, timer), ChoiceBox, title=_("Repeating event is currently active, what do you want to do?"), list=choiceList)
				else:
					timer.disable()
			self.session.nav.Scheduler.timeChanged(timer)
			self.reloadTimerList()

	def toggleTimerCallback(self, timer, choice):
		if choice is not None:
			if choice[1] in ("stoponlycurrent", "stopall"):
				timer.enable()
				timer.processRepeated(findRunningEvent=False)
				self.session.nav.Scheduler.doActivate(timer)
			if choice[1] in ("stoponlycoming", "stopall"):
				timer.disable()
			self.session.nav.Scheduler.timeChanged(timer)
			self.reloadTimerList()

	def cleanupTimers(self):
		self.session.openWithCallback(self.cleanupTimersCallback, MessageBox, _("Clean up (delete) all completed timers?"), windowTitle=self.getTitle())

	def cleanupTimersCallback(self, answer):
		if answer:
			self.session.nav.Scheduler.cleanup()
			self.reloadTimerList()

	# def refill(self):
	#	length = len(self.timerList)
	#	self.fillTimerList()
	#	if length and length != len(self.timerList):
	#		self["timerlist"].entryRemoved(self["timerlist"].getCurrentIndex())
	#	else:
	#		self["timerlist"].invalidate()


class RecordTimerOverview(TimerOverviewBase):
	def __init__(self, session):
		self["timerlist"] = RecordTimerList([])
		self.fallbackTimer = FallbackTimerList(self, self.fallbackRefresh)
		TimerOverviewBase.__init__(self, session, mode=MODE_RECORD)
		self["Event"] = Event()
		self["Service"] = ServiceEvent()

	def doChangeCallbackAppend(self):
		self.session.nav.RecordTimer.on_state_change.append(self.onStateChange)

	def doChangeCallbackRemove(self):
		self.session.nav.RecordTimer.on_state_change.remove(self.onStateChange)

	def fallbackRefresh(self):
		self.loadTimerList()
		self.selectionChanged()

	def loadTimerList(self):
		def condition(element):
			return element[0].state == TimerEntry.StateEnded, element[0].begin

		timerList = []
		if self.fallbackTimer.list:
			timerList.extend([(timer, False) for timer in self.fallbackTimer.list if timer.state != 3])
			timerList.extend([(timer, True) for timer in self.fallbackTimer.list if timer.state == 3])

		timerList.extend([(timer, False) for timer in self.session.nav.RecordTimer.timer_list])
		timerList.extend([(timer, True) for timer in self.session.nav.RecordTimer.processed_timers])
		if config.usage.timerlist_finished_timer_position.index:  # End of list.
			timerList.sort(key=condition)
		else:
			timerList.sort(key=lambda x: x[0].begin)
		self["timerlist"].setList(timerList)

	def getEventDescription(self, timer):
		description = timer.description
		event = eEPGCache.getInstance().lookupEventId(timer.service_ref.ref, timer.eit) if timer.eit else None
		if event:
			self["Event"].newEvent(event)
			shortDescription = event.getShortDescription()
			if shortDescription and description != shortDescription:
				if description and shortDescription:
					description = "%s %s\n\n%s: %s" % (_("Timer:"), description, _("EPG"), shortDescription)
				elif shortDescription:
					description = shortDescription
					timer.description = shortDescription
			extendDescription = event.getExtendedDescription()
			if extendDescription and description != extendDescription:
				description = "%s\n%s" % (description, extendDescription) if description else extendDescription
		return description

	def selectionChanged(self):
		timer = self["timerlist"].getCurrent()
		if timer:
			self["Service"].newService(timer.service_ref.ref)
			description = self.getEventDescription(timer)
			self["description"].setText(description)
			self["key_info"].setText(_("INFO"))
			self["editActions"].setEnabled(True)
			self["key_red"].setText(_("Stop") if timer.state == TimerEntry.StateRunning else _("Delete"))
			self["deleteActions"].setEnabled(True)
			stateRunning = timer.state in (TimerEntry.StatePrepared, TimerEntry.StateRunning)
			yellowText = ""
			if timer.disabled:
				if stateRunning and timer.repeated and not timer.justplay:
					yellowText = ""
				else:
					yellowText = _("Enable")
			elif stateRunning and (not timer.repeated or timer.state == TimerEntry.StatePrepared):
				yellowText = ""
			elif (not stateRunning or timer.repeated and timer.isRunning()) and not timer.disabled:
				yellowText = _("Disable")
			if not timer.disabled and not timer.repeated and timer.state == TimerEntry.StateEnded:
				yellowText = ""
			self["key_yellow"].setText(yellowText)
			self["toggleActions"].setEnabled(yellowText != "")
			time = "%s %s ... %s" % (fuzzyDate(timer.begin)[0], fuzzyDate(timer.begin)[1], fuzzyDate(timer.end)[1])
			duration = int((timer.end - timer.begin) / 60.0)
			for callback in self.onSelectionChanged:
				callback(timer.name, timer.service_ref.getServiceName(), time, ngettext("%d Min", "%d Mins", duration) % duration, TIMER_STATES.get(timer.state, UNKNOWN))
		else:
			self["description"].setText("")
			self["key_info"].setText("")
			self["editActions"].setEnabled(False)
			self["key_red"].setText("")
			self["deleteActions"].setEnabled(False)
			self["key_yellow"].setText("")
			self["toggleActions"].setEnabled(False)
			for callback in self.onSelectionChanged:
				callback("", "", "", "", "")
		showCleanup = False
		for item in self["timerlist"].getList():
			if not item[0].disabled and item[1] is True:
				showCleanup = True
				break
		if showCleanup:
			self["key_blue"].setText(_("Cleanup"))
			self["cleanupActions"].setEnabled(True)
		else:
			self["key_blue"].setText("")
			self["cleanupActions"].setEnabled(False)

	def addTimer(self):
		event = None
		service = self.session.nav.getCurrentService()
		if service:
			info = service.info()
			if info is not None:
				event = info.getEvent(0)
		# NOTE: Only works if already playing a service!
		serviceRef = ServiceReference(self.session.nav.getCurrentlyPlayingServiceOrGroup())
		now = int(time())
		data = parseEvent(event, description=False) if event else (now, now + 60, "", "", None)
		self.session.openWithCallback(self.addTimerCallback, RecordTimerEdit, RecordTimerEntry(serviceRef, checkOldTimers=True, dirname=preferredTimerPath(), fixDescription=True, *data))

	def addTimerCallback(self, result):
		if isinstance(result, bool) and result:  # Special case for close recursive.
			self.close(True)
			return
		if result[0]:
			entry = result[1]
			if entry.external:
				self.fallbackTimer.addTimer(entry, self.fallbackRefresh)
			else:
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList:
					for timer in simulTimerList:
						if timer.setAutoincreaseEnd(entry):
							self.session.nav.RecordTimer.timeChanged(timer)
					simulTimerList = self.session.nav.RecordTimer.record(entry)
					if simulTimerList:
						self.session.openWithCallback(self.addTimerCallback, ConflictTimerOverview, simulTimerList)
				self.loadTimerList()
				self.selectionChanged()

	def doCleanupTimers(self):
		self.session.nav.RecordTimer.cleanup()

	def deleteTimer(self):
		timer = self["timerlist"].getCurrent()
		if timer:
			message = _("Do you really want to stop and delete the timer '%s'?") if timer.state == TimerEntry.StateRunning else _("Do you really want to delete '%s'?")
			self.session.openWithCallback(self.deleteTimerCallback, MessageBox, message % timer.name, windowTitle=self.getTitle())

	def deleteTimerCallback(self, answer):
		if answer:
			timer = self["timerlist"].getCurrent()
			if timer:
				if timer.external:
					self.fallbackTimer.removeTimer(timer, self.reloadTimerList)
				else:
					timer.afterEvent = RECORD_AFTEREVENT.NONE
					self.session.nav.RecordTimer.removeEntry(timer)
					self.reloadTimerList()

	def editTimer(self):
		timer = self["timerlist"].getCurrent()
		if timer:
			self.session.openWithCallback(self.editTimerCallback, RecordTimerEdit, timer)

	def editTimerCallback(self, result):
		if isinstance(result, bool) and result:  # Special case for close recursive.
			self.close(True)
			return
		if result[0]:
			entry = result[1]
			if entry.external:
				self.fallbackTimer.editTimer(entry, self.reloadTimerList)
			else:
				timerSanityCheck = TimerSanityCheck(self.session.nav.RecordTimer.timer_list, entry)
				success = False
				if not timerSanityCheck.check():
					simulTimerList = timerSanityCheck.getSimulTimerList()
					if simulTimerList is not None:
						for simulTimer in simulTimerList:
							if simulTimer.setAutoincreaseEnd(entry):
								self.session.nav.RecordTimer.timeChanged(simulTimer)
						if not timerSanityCheck.check():
							simulTimerList = timerSanityCheck.getSimulTimerList()
							if simulTimerList is not None:
								self.session.openWithCallback(self.editTimerCallback, ConflictTimerOverview, timerSanityCheck.getSimulTimerList())
						else:
							success = True
				else:
					success = True
				if success:
					self.session.nav.RecordTimer.timeChanged(entry)
					print("[Timers] RecordTimer updated.")
				self.reloadTimerList()
		else:
			print("[Timers] RecordTimer not updated.")

	def toggleTimer(self):
		timerChanged = True
		timer = self["timerlist"].getCurrent()
		if timer:
			if timer.external:
				self.fallbackTimer.toggleTimer(timer, self.reloadTimerList)
			else:
				stateRunning = timer.state in (TimerEntry.StatePrepared, TimerEntry.StateRunning)
				if timer.disabled and timer.repeated and stateRunning and not timer.justplay:
					return
				if timer.disabled:
					print("[Timers] Try to enable RecordTimer.")
					timer.enable()
					timerSanityCheck = TimerSanityCheck(self.session.nav.RecordTimer.timer_list, timer)
					if not timerSanityCheck.check():
						timer.disable()
						print("[Timers] Sanity check failed.")
						simulTimerList = timerSanityCheck.getSimulTimerList()
						if simulTimerList is not None:
							self.session.openWithCallback(self.editTimerCallback, ConflictTimerOverview, simulTimerList)
							timerChanged = False
					else:
						print("[Timers] Sanity check passed.")
						if timerSanityCheck.doubleCheck():
							timer.disable()
				else:
					print("[Timers] Try to disable RecordTimer.")
					if stateRunning:
						if timer.isRunning() and timer.repeated:
							choiceList = (
								(_("Stop current event but not future events"), "stoponlycurrent"),
								(_("Stop current event and disable future events"), "stopall"),
								(_("Don't stop current event but disable future events"), "stoponlycoming")
							)
							self.session.openWithCallback(boundFunction(self.toggleTimerCallback, timer), ChoiceBox, title=_("Repeating event is currently recording, what do you want to do?"), list=choiceList)
							timerChanged = False
					else:
						timer.disable()
						timerChanged = False
				if timerChanged:
					self.session.nav.RecordTimer.timeChanged(timer)
				self.reloadTimerList()

	def toggleTimerCallback(self, timer, choice):
		if choice is not None and timer.isRunning():
			findNextRunningEvent = True
			if choice[1] == "stoponlycurrent" or choice[1] == "stopall":
				findNextRunningEvent = False
				timer.enable()
				timer.processRepeated(findRunningEvent=False)
				self.session.nav.RecordTimer.doActivate(timer)
			if choice[1] == "stoponlycoming" or choice[1] == "stopall":
				findNextRunningEvent = True
				timer.disable()
			self.session.nav.RecordTimer.timeChanged(timer)
			timer.findRunningEvent = findNextRunningEvent
			self.reloadTimerList()


class ConflictTimerOverview(TimerOverviewBase):
	def __init__(self, session, timers):
		self.timers = timers
		self["timerlist"] = RecordTimerList([])
		TimerOverviewBase.__init__(self, session, mode=MODE_CONFLICT)
		self["key_info"].setText(_("INFO"))
		self["deleteActions"].setEnabled(True)
		self["editActions"].setEnabled(True)
		self["Event"] = Event()
		self["Service"] = ServiceEvent()

	def doChangeCallbackAppend(self):
		self.session.nav.RecordTimer.on_state_change.append(self.onStateChange)

	def doChangeCallbackRemove(self):
		self.session.nav.RecordTimer.on_state_change.remove(self.onStateChange)

	def keyCancel(self):
		self.close((False, self.timers[0]))

	def loadTimerList(self):
		# for index, item in enumerate(self.session.nav.RecordTimer.timer_list):
		# 	print("[TimerSanityCheck] timer_list DEBUG 1: Entry %d: %s." % (index + 1, str(item)))
		# for index, item in enumerate(self.timers):
		# 	print("[TimerSanityCheck] timers     DEBUG 2: Entry %d: %s." % (index + 1, str(item)))
		timerList = []
		timerList.extend([(timer, False) for timer in self.timers])
		# timerList.sort(key=lambda x: x[0].begin)  # This was causing the timer order in simulTimerList to change and hide the *NEW* unsaved timer.
		self["timerlist"].setList(timerList)

	def selectionChanged(self):
		timer = self["timerlist"].getCurrent()
		if timer:
			self["description"].setText(timer.description)
			self["Service"].newService(timer.service_ref.ref)
			event = eEPGCache.getInstance().lookupEventId(timer.service_ref.ref, timer.eit) if timer.eit else None
			if event:
				self["Event"].newEvent(event)
			stateRunning = timer.state in (TimerEntry.StatePrepared, TimerEntry.StateRunning)
			if (not stateRunning or timer.repeated and timer.isRunning()) and not timer.disabled:
				self["key_yellow"].setText(_("Disable"))
				self["toggleActions"].setEnabled(True)
			self["key_red"].setText(_("Stop") if timer.state == TimerEntry.StateRunning else _("Delete"))
			time = "%s %s ... %s" % (fuzzyDate(timer.begin)[0], fuzzyDate(timer.begin)[1], fuzzyDate(timer.end)[1])
			duration = int((timer.end - timer.begin) / 60.0)
			for callback in self.onSelectionChanged:
				callback("", "", time, ngettext("%d Min", "%d Mins", duration) % duration, TIMER_STATES.get(timer.state, UNKNOWN))

	def deleteTimer(self):
		timer = self["timerlist"].getCurrent()
		if timer:
			message = _("Do you really want to stop and delete the timer '%s'?") if timer.state == TimerEntry.StateRunning else _("Do you really want to delete '%s'?")
			self.session.openWithCallback(self.deleteTimerCallback, MessageBox, message % timer.name, windowTitle=self.getTitle())

	def deleteTimerCallback(self, answer):
		if answer:
			index = self["timerlist"].getCurrentIndex()
			if index == 0:
				self.close((False, None))
			timer = self["timerlist"].getCurrent()
			if timer:
				timer.afterEvent = RECORD_AFTEREVENT.NONE
				self.session.nav.RecordTimer.removeEntry(timer)
		self.close((True, self.timers[0]))

	def editTimer(self):
		timer = self["timerlist"].getCurrent()
		if timer:
			self.session.openWithCallback(self.editTimerCallback, RecordTimerEdit, timer)

	def editTimerCallback(self, result):
		if result and len(result) > 1 and result[0]:
			if self["timerlist"].getCurrentIndex():
				self.session.nav.RecordTimer.timeChanged(result[1])
		self.close((True, self.timers[0]))

	def toggleTimer(self):
		timerChanged = True
		timer = self["timerlist"].getCurrent()
		if timer:
			stateRunning = timer.state in (TimerEntry.StatePrepared, TimerEntry.StateRunning)
			if timer.disabled and timer.repeated and stateRunning and not timer.justplay:
				return
			if not timer.disabled:
				if stateRunning:
					if timer.isRunning() and timer.repeated:
						choiceList = (
							(_("Stop current event but not future events"), "stoponlycurrent"),
							(_("Stop current event and disable future events"), "stopall"),
							(_("Don't stop current event but disable future events"), "stoponlycoming")
						)
						self.session.openWithCallback(boundFunction(self.toggleTimerCallback, timer), ChoiceBox, title=_("Repeating event is currently recording, what do you want to do?"), list=choiceList)
						timerChanged = False
				else:
					timer.disable()
					self.session.nav.RecordTimer.timeChanged(timer)
		self.close((True, self.timers[0]))

	def toggleTimerCallback(self, timer, choice):
		if choice is not None and timer.isRunning():
			findNextRunningEvent = True
			if choice[1] == "stoponlycurrent" or choice[1] == "stopall":
				findNextRunningEvent = False
				timer.enable()
				timer.processRepeated(findRunningEvent=False)
				self.session.nav.RecordTimer.doActivate(timer)
			if choice[1] == "stoponlycoming" or choice[1] == "stopall":
				findNextRunningEvent = True
				timer.disable()
			self.session.nav.RecordTimer.timeChanged(timer)
			timer.findRunningEvent = findNextRunningEvent
		self.close((True, self.timers[0]))

	# def isConflictResolved(self):
	# 	pass


class SchedulerEdit(Setup):
	def __init__(self, session, timer):
		self.timer = timer
		self.createConfig()
		Setup.__init__(self, session, "Scheduler")

	def createConfig(self):
		days = {}
		for day in DAY_LIST:
			days[day] = False
		if self.timer.repeated:  # Timer repeated.
			type = "repeated"
			weekday = "Mon"
			if self.timer.repeated == 31:  # Mon-Fri.
				repeated = "weekdays"
			elif self.timer.repeated == 127:  # Daily.
				repeated = "daily"
			else:
				flags = self.timer.repeated
				repeated = "user"
				count = 0
				for day in DAY_LIST:
					if flags == 1:  # Weekly.
						weekday = day
					if flags & 1 == 1:  # Set user defined days.
						days[day] = True
						count += 1
					else:
						days[day] = False
					flags >>= 1
				if count == 1:
					repeated = "weekly"
		else:  # Timer once.
			type = "once"
			repeated = None
			weekday = DAY_LIST[int(strftime("%u", localtime(self.timer.begin))) - 1]
			days[weekday] = True
		functionTimerItems = functionTimer.get()
		choices = [
			# (SCHEDULER_TYPES.get(SCHEDULER_TYPE.NONE), SCHEDULER_TYPE_NAMES.get(SCHEDULER_TYPE.NONE)),
			(SCHEDULER_TYPES.get(SCHEDULER_TYPE.WAKEUP), SCHEDULER_TYPE_NAMES.get(SCHEDULER_TYPE.WAKEUP)),
			(SCHEDULER_TYPES.get(SCHEDULER_TYPE.WAKEUPTOSTANDBY), SCHEDULER_TYPE_NAMES.get(SCHEDULER_TYPE.WAKEUPTOSTANDBY)),
			(SCHEDULER_TYPES.get(SCHEDULER_TYPE.AUTOSTANDBY), SCHEDULER_TYPE_NAMES.get(SCHEDULER_TYPE.AUTOSTANDBY)),
			(SCHEDULER_TYPES.get(SCHEDULER_TYPE.AUTODEEPSTANDBY), SCHEDULER_TYPE_NAMES.get(SCHEDULER_TYPE.AUTODEEPSTANDBY)),
			(SCHEDULER_TYPES.get(SCHEDULER_TYPE.STANDBY), SCHEDULER_TYPE_NAMES.get(SCHEDULER_TYPE.STANDBY)),
			(SCHEDULER_TYPES.get(SCHEDULER_TYPE.DEEPSTANDBY), SCHEDULER_TYPE_NAMES.get(SCHEDULER_TYPE.DEEPSTANDBY)),
			(SCHEDULER_TYPES.get(SCHEDULER_TYPE.REBOOT), SCHEDULER_TYPE_NAMES.get(SCHEDULER_TYPE.REBOOT)),
			(SCHEDULER_TYPES.get(SCHEDULER_TYPE.RESTART), SCHEDULER_TYPE_NAMES.get(SCHEDULER_TYPE.RESTART))
		] + [(x, functionTimerItems[x]['name']) for x in functionTimerItems]
		default = self.timer.function or SCHEDULER_TYPES.get(self.timer.timerType, "wakeup")
		self.timerType = ConfigSelection(default=default, choices=choices)
		self.timerActiveInStandby = ConfigSelection(default=self.timer.autosleepinstandbyonly, choices=[
			("yes", _("Only in standby")),
			("no", _("Standard (Always)")),
			("noquery", _("Without query"))
		])
		self.timerSleepDelay = ConfigSelection(default=self.timer.autosleepdelay, choices=[
			(1, _("%d Minute") % 1),
			(3, _("%d Minutes") % 3),
			(5, _("%d Minutes") % 5),
			(10, _("%d Minutes") % 10)
		] + [(x, _("%d Minutes") % x) for x in range(15, 301, 15)])
		self.timerRepeat = ConfigSelection(default=type, choices=REPEAT_CHOICES)
		self.timerAutoSleepRepeat = ConfigSelection(default=self.timer.autosleeprepeat, choices=REPEAT_CHOICES)
		self.timerSleepWindow = ConfigYesNo(default=self.timer.autosleepwindow)
		self.timerSleepStart = ConfigClock(default=self.timer.autosleepbegin)
		self.timerSleepEnd = ConfigClock(default=self.timer.autosleepend)
		self.timerShowExtended = ConfigYesNo(default=self.timer.nettraffic or self.timer.netip)
		self.timerNetTraffic = ConfigYesNo(default=self.timer.nettraffic)
		self.timerNetTrafficLimit = ConfigSelection(default=self.timer.trafficlimit, choices=[
			(10, "10"),
			(50, "50"),
			(100, "100"),
			(500, "500"),
			(1000, "1000")
		])
		self.timerNetIP = ConfigYesNo(default=self.timer.netip)
		timerIPAddress = [x.strip() for x in self.timer.ipadress.split(",")]
		self.timerNetIPCount = ConfigSelection(default=len(timerIPAddress), choices=[(x, str(x)) for x in range(1, 6)])
		self.timerIPAddress = []
		for i in range(5):
			ipAddress = timerIPAddress[i] if (len(timerIPAddress) > i and len(timerIPAddress[i].split(".")) == 4) else "0.0.0.0"
			self.timerIPAddress.append(ConfigIP(default=[int(x) for x in ipAddress.split(".")]))
		self.timerRepeatPeriod = ConfigSelection(default=repeated, choices=REPEAT_OPTIONS)
		self.timerRepeatStartDate = ConfigDateTime(default=self.timer.repeatedbegindate, formatstring=config.usage.date.daylong.value, increment=86400)
		self.timerWeekday = ConfigSelection(default=weekday, choices=DAY_NAMES)
		self.timerDay = {}
		for day in DAY_LIST:
			self.timerDay[day] = ConfigYesNo(default=days[day])
		self.timerStartTime = ConfigClock(default=self.timer.begin)
		self.timerSetEndTime = ConfigYesNo(default=(int((self.timer.end - self.timer.begin) / 60.0) > 4))
		self.timerEndTime = ConfigClock(default=self.timer.end)
		self.timerAfterEvent = ConfigSelection(default=SCHEDULER_AFTER_EVENTS.get(self.timer.afterEvent, "nothing"), choices=[
			(SCHEDULER_AFTER_EVENTS.get(SCHEDULER_AFTEREVENT.NONE), SCHEDULER_AFTER_EVENT_NAMES.get(SCHEDULER_AFTEREVENT.NONE)),
			(SCHEDULER_AFTER_EVENTS.get(SCHEDULER_AFTEREVENT.WAKEUPTOSTANDBY), SCHEDULER_AFTER_EVENT_NAMES.get(SCHEDULER_AFTEREVENT.WAKEUPTOSTANDBY)),
			(SCHEDULER_AFTER_EVENTS.get(SCHEDULER_AFTEREVENT.STANDBY), SCHEDULER_AFTER_EVENT_NAMES.get(SCHEDULER_AFTEREVENT.STANDBY)),
			(SCHEDULER_AFTER_EVENTS.get(SCHEDULER_AFTEREVENT.DEEPSTANDBY), SCHEDULER_AFTER_EVENT_NAMES.get(SCHEDULER_AFTEREVENT.DEEPSTANDBY))
		])
		for callback in onSchedulerCreate:
			callback(self)

	def createSetup(self):  # NOSONAR silence S2638
		Setup.createSetup(self)
		for callback in onSchedulerSetup:
			callback(self)

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, self.cancelMsg, default=False, type=MessageBox.TYPE_YESNO, windowTitle=self.getTitle())
		else:
			self.close((False,))

	def cancelConfirm(self, result):
		if not result:
			return
		for item in self["config"].list:
			if len(item) > 1:
				item[1].cancel()
		self.close((False,))

	def keySave(self, result=None):
		for callback in onSchedulerSave:
			callback(self)
		if not self.timerSetEndTime.value:
			self.timerEndTime.value = self.timerStartTime.value
		now = int(time())
		self.timer.resetRepeated()
		if self.timerType.value in functionTimer.get():
			self.timer.timerType = SCHEDULER_TYPE.OTHER
			self.timer.function = self.timerType.value
		else:
			self.timer.timerType = SCHEDULER_VALUES.get(self.timerType.value, SCHEDULER_TYPE.WAKEUP)
		self.timer.afterEvent = SCHEDULER_AFTER_VALUES.get(self.timerAfterEvent.value, SCHEDULER_TYPE.NONE)
		if self.timerRepeat.value == "once":
			date = self.timerRepeatStartDate.value
			startTime = self.timerStartTime.value
			begin = self.getTimeStamp(date, startTime)
			endTime = self.timerEndTime.value
			end = self.getTimeStamp(date, endTime)
			if end < begin:  # If end is less than start then add 1 day to the end time.
				end += 86400
			self.timer.begin = begin
			self.timer.end = end
		if self.timerType.value in ("autostandby", "autodeepstandby"):
			self.timer.begin = now + 10
			self.timer.end = self.timer.begin
			self.timer.autosleepinstandbyonly = self.timerActiveInStandby.value
			self.timer.autosleepdelay = self.timerSleepDelay.value
			self.timer.autosleeprepeat = self.timerAutoSleepRepeat.value
			if self.timerRepeat.value == "repeated":  # Ensure that the timer repeated is cleared if we have an "autosleeprepeat".
				self.timer.resetRepeated()
				self.timerRepeat.value = "once"  # Stop it being set again.
			self.timer.autosleepwindow = self.timerSleepWindow.value
			if self.timerSleepWindow.value:
				self.timer.autosleepbegin = self.getTimeStamp(now, self.timerSleepStart.value)
				self.timer.autosleepend = self.getTimeStamp(now, self.timerSleepEnd.value)
		if self.timerRepeat.value == "repeated":
			if self.timerRepeatPeriod.value == "daily":
				for day in (0, 1, 2, 3, 4, 5, 6):
					self.timer.setRepeated(day)
			elif self.timerRepeatPeriod.value == "weekly":
				self.timer.setRepeated(self.timerWeekday.index)
			elif self.timerRepeatPeriod.value == "weekdays":
				for day in (0, 1, 2, 3, 4):
					self.timer.setRepeated(day)
			elif self.timerRepeatPeriod.value == "weekends":
				for day in (5, 6):
					self.timer.setRepeated(day)
			elif self.timerRepeatPeriod.value == "user":
				for day in (0, 1, 2, 3, 4, 5, 6):
					if self.timerDay[DAY_LIST[day]].value:
						self.timer.setRepeated(day)
			self.timer.repeatedbegindate = self.getTimeStamp(self.timerRepeatStartDate.value, self.timerStartTime.value)
			if self.timer.repeated:
				self.timer.begin = self.getTimeStamp(self.timerRepeatStartDate.value, self.timerStartTime.value)
				self.timer.end = self.getTimeStamp(self.timerRepeatStartDate.value, self.timerEndTime.value)
			else:
				self.timer.begin = self.getTimeStamp(now, self.timerStartTime.value)
				self.timer.end = self.getTimeStamp(now, self.timerEndTime.value)
			if self.timer.end < self.timer.begin:  # If end is less than start then add 1 day to the end time.
				self.timer.end += 86400
		self.timer.nettraffic = self.timerNetTraffic.value
		self.timer.trafficlimit = self.timerNetTrafficLimit.value
		self.timer.netip = self.timerNetIP.value
		ipAdresses = []
		for i in range(self.timerNetIPCount.value):
			ipAdresses.append(".".join("%d" % d for d in self.timerIPAddress[i].value))
		self.timer.ipadress = ",".join(ipAdresses)

		self.session.nav.Scheduler.saveTimers()
		for notifier in self.onSave:
			notifier()
		self.close((True, self.timer))

	def getTimeStamp(self, date, time):  # Note: The "date" can be a float() or an int() while "time" is a two item list.
		localDate = localtime(date)
		return int(mktime(datetime(localDate.tm_year, localDate.tm_mon, localDate.tm_mday, time[0], time[1]).timetuple()))


class RecordTimerEdit(Setup):
	def __init__(self, session, timer):
		self.timer = timer
		self.newEntry = False  # TODO
		self.timer.service_ref_prev = self.timer.service_ref
		self.timer.begin_prev = self.timer.begin
		self.timer.end_prev = self.timer.end
		self.timer.external_prev = self.timer.external
		self.timer.dirname_prev = self.timer.dirname
		self.fallbackInfo = None
		self.initEndTime = True
		self.session = session  # We need session before createConfig
		self.createConfig()
		if self.timer.external:
			FallbackTimerDirs(self, self.fallbackResult)
		Setup.__init__(self, session, "RecordTimer")

	def fallbackResult(self, locations, default, tags):
		self.fallbackInfo = (locations, default, tags)
		if self.timer.dirname and self.timer.dirname not in locations:
			locations.append(self.timer.dirname)
		self.timerLocation.setChoices(choices=locations, default=self.timer.dirname)

	def createConfig(self):
		days = {}
		for day in DAY_LIST:
			days[day] = False
		if self.timer.repeated:  # Timer repeated.
			type = "repeated"
			weekday = "Mon"
			if self.timer.repeated == 31:  # Mon-Fri.
				repeated = "weekdays"
			elif self.timer.repeated == 127:  # Daily.
				repeated = "daily"
			else:
				flags = self.timer.repeated
				repeated = "user"
				count = 0
				for day in DAY_LIST:
					if flags == 1:  # Weekly.
						weekday = day
					if flags & 1 == 1:  # Set user defined days.
						days[day] = True
						count += 1
					else:
						days[day] = False
					flags >>= 1
				if count == 1:
					repeated = "weekly"
		else:  # Timer once.
			type = "once"
			repeated = None
			weekday = DAY_LIST[int(strftime("%u", localtime(self.timer.begin))) - 1]
			days[weekday] = True
		self.timerName = ConfigText(default=self.timer.name.replace("\x86", "").replace("\x87", ""), visible_width=50, fixed_size=False)
		self.timerDescription = ConfigText(default=self.timer.description.replace("\x8a", " ").replace("\n", " "), visible_width=50, fixed_size=False)
		self.timerType = ConfigSelection(default=RECORDTIMER_TYPES.get(self.timer.justplay + 2 * self.timer.always_zap, "record"), choices=[
			(RECORDTIMER_TYPES.get(RECORD_TIMERTYPE.RECORD), RECORDTIMER_TYPE_NAMES.get(RECORD_TIMERTYPE.RECORD)),
			(RECORDTIMER_TYPES.get(RECORD_TIMERTYPE.ZAP), RECORDTIMER_TYPE_NAMES.get(RECORD_TIMERTYPE.ZAP)),
			(RECORDTIMER_TYPES.get(RECORD_TIMERTYPE.ZAP_RECORD), RECORDTIMER_TYPE_NAMES.get(RECORD_TIMERTYPE.ZAP_RECORD))
		])
		self.timerRepeat = ConfigSelection(default=type, choices=REPEAT_CHOICES)
		self.timerRepeatPeriod = ConfigSelection(default=repeated, choices=REPEAT_OPTIONS)
		self.timerRepeatStartDate = ConfigDateTime(default=self.timer.repeatedbegindate, formatstring=config.usage.date.daylong.value, increment=86400)
		self.timerWeekday = ConfigSelection(default=weekday, choices=DAY_NAMES)
		self.timerDay = ConfigSubDict()
		for day in DAY_LIST:
			self.timerDay[day] = ConfigYesNo(default=days[day])
		self.timerRename = ConfigYesNo(default=self.timer.rename_repeat != 0)
		# self.timerStartDate = ConfigDateTime(default=self.timer.begin, formatstring=config.usage.date.daylong.value, increment=86400)
		self.timerStartDate = ConfigDateTime(default=self.timer.eventBegin, formatstring=config.usage.date.daylong.value, increment=86400)
		# self.timerStartTime = ConfigClock(default=self.timer.begin)
		self.timerStartTime = ConfigClock(default=self.timer.eventBegin)
		marginChoices = [(x, ngettext("%d Minute", "%d Minutes", x) % x) for x in range(121)]
		self.timerMarginBefore = ConfigSelection(default=self.timer.marginBefore // 60, choices=marginChoices)
		# print("[Timers] DEBUG: default=%d, value=%d, margin=%d." % (self.timerMarginBefore.value, self.timerMarginBefore.default, self.timer.marginBefore // 60))
		# self.timerHasEndTime = ConfigYesNo(default=self.timer.end > self.timer.begin + 3 and self.timer.justplay != 0)
		self.timerHasEndTime = ConfigYesNo(default=self.timer.hasEndTime)
		# self.timerEndTime = ConfigClock(default=self.timer.end)
		self.timerEndTime = ConfigClock(default=self.timer.eventEnd)
		self.timerMarginAfter = ConfigSelection(default=self.timer.marginAfter // 60, choices=marginChoices)
		serviceName = self.getServiceName(self.timer.service_ref)
		self.timerService = ConfigSelection([(serviceName, serviceName)])
		self.timerServiceReference = self.timer.service_ref
		if self.timer.record_ecm and self.timer.descramble:
			recordingType = "descrambled+ecm"
		elif self.timer.record_ecm:
			recordingType = "scrambled+ecm"
		elif self.timer.descramble:
			recordingType = "normal"
		self.timerRecordingType = ConfigSelection(default=recordingType, choices=[
			("normal", _("Normal")),
			("descrambled+ecm", _("Unscramble and record ECM")),
			("scrambled+ecm", _("Don't unscramble, record ECM"))
		])
		default, locations = self.getLocationInfo()
		if default not in locations:
			locations.append(default)
		self.timerLocation = ConfigSelection(default=default, choices=locations)

		self.tags = self.timer.tags[:]
		if not self.tags:  # If no tags found, make name of event default tag set.
			tagName = self.timer.name.strip()
			if tagName:
				tagName = "%s%s" % (tagName[0].upper(), tagName[1:].replace(" ", "_"))
				self.tags.append(tagName)
		self.timerTags = ConfigSelection(choices=[not self.tags and "None" or " ".join(self.tags)])
		self.timerAfterEvent = ConfigSelection(default=RECORDTIMER_AFTER_EVENTS.get(self.timer.afterEvent, "auto"), choices=[
			(RECORDTIMER_AFTER_EVENTS.get(RECORD_AFTEREVENT.NONE), RECORDTIMER_AFTER_EVENT_NAMES.get(RECORD_AFTEREVENT.NONE)),
			(RECORDTIMER_AFTER_EVENTS.get(RECORD_AFTEREVENT.STANDBY), RECORDTIMER_AFTER_EVENT_NAMES.get(RECORD_AFTEREVENT.STANDBY)),
			(RECORDTIMER_AFTER_EVENTS.get(RECORD_AFTEREVENT.DEEPSTANDBY), RECORDTIMER_AFTER_EVENT_NAMES.get(RECORD_AFTEREVENT.DEEPSTANDBY)),
			(RECORDTIMER_AFTER_EVENTS.get(RECORD_AFTEREVENT.AUTO), RECORDTIMER_AFTER_EVENT_NAMES.get(RECORD_AFTEREVENT.AUTO))
		])
		self.timerFallback = ConfigYesNo(default=self.timer.external_prev or self.newEntry and config.usage.remote_fallback_external_timer.value and config.usage.remote_fallback.value and config.usage.remote_fallback_external_timer_default.value)

		for callback in onRecordTimerCreate:
			callback(self)

	def createSetup(self):  # NOSONAR silence S2638
		Setup.createSetup(self)
		for callback in onRecordTimerSetup:
			callback(self)

	def changedEntry(self):
		Setup.changedEntry(self)
		current = self["config"].getCurrent()[1]
		if current == self.timerFallback:
			self.timer.external = self.timerFallback.value
			self.selectionChanged()  # Force getSpace()
		elif current == self.timerLocation and self.timerType.value != "zap":
			self.getSpace()
		elif current == self.timerType and self.timerType.value == "zap":
			if self.initEndTime:
				self.initEndTime = False
				self.timerHasEndTime.value = config.recording.zap_has_endtime.value
				self.timerMarginBefore.value = config.recording.zap_margin_before.value // 60
				self.timerMarginAfter.value = config.recording.zap_margin_after.value // 60
				Setup.createSetup(self)

	def selectionChanged(self):
		Setup.selectionChanged(self)
		if self.timerType.value != "zap":
			self.getSpace()  # TODO This will be called every time on selectionChanged and that's not good

	def keySelect(self):
		current = self["config"].getCurrent()[1]
		if current == self.timerLocation:
			self.getLocation()
		elif current == self.timerService:
			self.getChannels()
		elif current == self.timerTags:
			self.getTags()
		else:
			Setup.keySelect(self)

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, self.cancelMsg, default=False, type=MessageBox.TYPE_YESNO, windowTitle=self.getTitle())
		else:
			self.close((False,))

	def cancelConfirm(self, result):
		if not result:
			return
		for item in self["config"].list:
			if len(item) > 1:
				item[1].cancel()
		self.close((False,))

	def keySave(self, result=None):
		def keySaveCallback(answer):
			if answer:
				self.getChannels()
			else:
				self.close((False,))

		if not self.timerServiceReference.isRecordable():
			self.session.openWithCallback(keySaveCallback, MessageBox, "%s\n\n%s" % (_("Error: The selected service can't be recorded!"), _("Do you want to select another service?")), MessageBox.TYPE_YESNO, default=False, typeIcon=MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
			return
		for callback in onRecordTimerSave:
			callback(self)
		self.timer.name = self.timerName.value
		self.timer.description = self.timerDescription.value if self.timerDescription.default != self.timerDescription.value else self.timer.description
		self.timer.justplay = self.timerType.value == "zap"
		self.timer.always_zap = self.timerType.value == "zap+record"
		self.timer.rename_repeat = 1 if self.timerRename.value else 0
		if self.timerType.value == "zap" and not self.timerHasEndTime.value:
			self.timerAfterEvent.value = "nothing"
			self.timerMarginAfter.value = 0
		if self.timerEndTime.value == self.timerStartTime.value and self.timerAfterEvent.value != "nothing":
			self.timerAfterEvent.value = "nothing"
			self.session.open(MessageBox, _("Difference between timer begin and end must be equal or greater than %d minutes.\nEnd Action was disabled!") % 1, MessageBox.TYPE_INFO, timeout=30, windowTitle=self.getTitle())
		self.timer.resetRepeated()
		if self.timerRepeat.value == "once":
			startDate = self.timerStartDate.value
			# startTime = self.timerStartTime.value
			# begin = self.getTimeStamp(date, startTime)
			# endTime = self.timerEndTime.value
			# end = self.getTimeStamp(date, endTime)
			# if end < begin:  # If end is less than start then add 1 day to the end time.
			# 	end += 86400
			# if self.timerType.value == "zap":  # If this is a Zap timer and no end is set then set the duration to 1 second so time is shown in EPGs.
			# 	if not self.timerHasEndTime.value:
			# 		end = begin + 1
			# self.timer.begin = begin
			# self.timer.end = end
		elif self.timerRepeat.value == "repeated":
			if self.timerRepeatPeriod.value == "daily":
				for day in (0, 1, 2, 3, 4, 5, 6):
					self.timer.setRepeated(day)
			elif self.timerRepeatPeriod.value == "weekly":
				self.timer.setRepeated(self.timerWeekday.index)
			elif self.timerRepeatPeriod.value == "weekdays":
				for day in (0, 1, 2, 3, 4):
					self.timer.setRepeated(day)
			elif self.timerRepeatPeriod.value == "weekends":
				for day in (5, 6):
					self.timer.setRepeated(day)
			elif self.timerRepeatPeriod.value == "user":
				for day in (0, 1, 2, 3, 4, 5, 6):
					if self.timerDay[DAY_LIST[day]].value:
						self.timer.setRepeated(day)
			self.timer.repeatedbegindate = self.getTimeStamp(self.timerRepeatStartDate.value, self.timerStartTime.value) - self.timerMarginBefore.value * 60
			startDate = self.timerRepeatStartDate.value if self.timer.repeated else int(time())
			# self.timer.begin = self.getTimeStamp(startDate, self.timerStartTime.value)
			# self.timer.end = self.getTimeStamp(startDate, self.timerEndTime.value)
		marginBefore = self.timerMarginBefore.value * 60
		eventBegin = self.getTimeStamp(startDate, self.timerStartTime.value)
		startDate += 86400 if self.timerEndTime.value < self.timerStartTime.value else 0  # If endTime is less than startTime then add 1 day to the startDate.
		eventEnd = self.getTimeStamp(startDate, self.timerEndTime.value)
		if self.timerType.value == "zap" and not self.timerHasEndTime.value:
			eventEnd = eventBegin + 1
		marginAfter = self.timerMarginAfter.value * 60
		self.timer.begin = eventBegin - marginBefore
		self.timer.end = eventEnd + marginAfter
		self.timer.marginBefore = marginBefore
		self.timer.eventBegin = eventBegin
		self.timer.eventEnd = eventEnd
		self.timer.marginAfter = marginAfter
		self.timer.hasEndTime = self.timerHasEndTime.value
		self.timer.service_ref = self.timerServiceReference
		self.timer.descramble = {
			"normal": True,
			"descrambled+ecm": True,
			"scrambled+ecm": False,
		}[self.timerRecordingType.value]
		self.timer.record_ecm = {
			"normal": False,
			"descrambled+ecm": True,
			"scrambled+ecm": True,
		}[self.timerRecordingType.value]
		self.saveMovieDir()
		self.timer.tags = self.tags
		self.timer.afterEvent = RECORDTIMER_AFTER_VALUES[self.timerAfterEvent.value]
		if self.timer.eit is not None and not self.lookupEvent():
			return
		self.saveTimers()
		for notifier in self.onSave:
			notifier()
		self.close((True, self.timer))

	def getTimeStamp(self, date, time):  # Note: The "date" can be a float() or an int() while "time" is a two item list.
		localDate = localtime(date)
		return int(mktime(datetime(localDate.tm_year, localDate.tm_mon, localDate.tm_mday, time[0], time[1]).timetuple()))

	def subServiceCallback(self, subService):
		if subService is not None:
			self.timer.service_ref = ServiceReference(subService[1])
		self.saveTimers()
		for notifier in self.onSave:
			notifier()
		self.close((True, self.timer))

	# These functions have been separated from the main code so that they can be overridden in sub-classes.
	#
	def getTags(self):
		if not self.timer.external:  # TODO Fallback
			def getTagsCallback(result):
				if result is not None:
					self.tags = result
					self.timerTags.setChoices([not result and "None" or " ".join(result)])

			self.session.openWithCallback(getTagsCallback, TagEditor, tags=self.tags)

	def getChannels(self):
		if not self.timer.external:  # TODO Fallback
			def getChannelsCallback(*result):
				if result:
					self.timerServiceReference = ServiceReference(result[0])
					self.timerService.setCurrentText(self.timerServiceReference.getServiceName())
					for callback in onRecordTimerChannelChange:
						callback(self)

			from Screens.ChannelSelection import SimpleChannelSelection  # This must be here to avoid a boot loop!
			self.session.openWithCallback(getChannelsCallback, SimpleChannelSelection, _("Select the channel from which to record:"), currentBouquet=True)

	def saveMovieDir(self):
		if not self.timer.external:
			if self.timer.dirname or self.timerLocation.value != defaultMoviePath():
				self.timer.dirname = self.timerLocation.value
				config.movielist.last_timer_videodir.value = self.timer.dirname
				config.movielist.last_timer_videodir.save()

	def lookupEvent(self):
		event = eEPGCache.getInstance().lookupEventId(self.timer.service_ref.ref, self.timer.eit)
		if event:
			parent = self.timer.service_ref.ref
			linkServices = event.getNumOfLinkageServices()
			if linkServices > 1:
				subServiceList = []
				ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
				selection = 0
				for linkService in range(linkServices):
					service = event.getLinkageService(parent, linkService)
					if service.toString() == ref.toString():
						selection = linkService
					subServiceList.append((service.getName(), service))
				self.session.openWithCallback(self.subServiceCallback, ChoiceBox, title=_("Please select the sub-service to record:"), list=subServiceList, selection=selection)
				return False
			elif linkServices > 0:
				self.timer.service_ref = ServiceReference(event.getLinkageService(parent, 0))
		return True

	def saveTimers(self):
		if not self.timer.external:
			self.session.nav.RecordTimer.saveTimers()

	def getServiceName(self, service_ref):
		try:  # No current service available?  (FIXME: Some service-chooser needed here!)
			serviceName = service_ref.getServiceName()
		except Exception:
			serviceName = _("N/A")
		return serviceName

	def getLocationInfo(self):
		if not self.timer.external:
			default = self.timer.dirname or defaultMoviePath()
			locations = config.movielist.videodirs.value
			return (default, locations)
		elif self.fallbackInfo and len(self.fallbackInfo) > 1:
			return (self.fallbackInfo[1], self.fallbackInfo[0])
		elif self.timer.dirname:
			return (self.timer.dirname, [self.timer.dirname])
		else:
			return (defaultMoviePath(), [defaultMoviePath()])

	def getLocation(self):
		if not self.timer.external:  # TODO Fallback
			def getLocationCallback(result):
				if result:
					if config.movielist.videodirs.value != self.timerLocation.choices:
						self.timerLocation.setChoices(config.movielist.videodirs.value, default=result)
					self.timerLocation.value = result
				self.getSpace()

			self.session.openWithCallback(getLocationCallback, MovieLocationBox, _("Select the location in which to store the recording:"), self.timerLocation.value, minFree=100)  # We require at least 100MB free space.

	def getSpace(self):
		if not self.timer.external:
			if config.recording.timerviewshowfreespace.value:
				try:
					device = stat(self.timerLocation.value).st_dev
					if device in DEFAULT_INHIBIT_DEVICES:
						self.setFootnote(_("Warning: Recordings should not be stored on the Flash disk!"))
					else:
						status = statvfs(self.timerLocation.value)
						total = status.f_blocks * status.f_bsize
						free = status.f_bavail * status.f_bsize
						self.setFootnote(_("Space total %s, used %s, free %s (%0.f%%).") % (scaleNumber(total), scaleNumber(total - free), scaleNumber(free), 100.0 * free / total))
				except OSError as err:
					self.setFootnote(_("Error %d: Unable to check space!  (%s)") % (err.errno, err.strerror))
	#
	# Do not rename the methods above as they are designed to be overwritten in sub-classes.


class InstantRecordTimerEdit(RecordTimerEdit):
	def __init__(self, session, timer, zap=0, zaprecord=0):
		RecordTimerEdit.__init__(self, session, timer)
		self.timer.justplay = zap
		self.timer.always_zap = zaprecord
		self.keySave()

	def keySave(self, result=None):
		if self.timer.justplay:
			self.timer.begin += config.recording.zap_margin_before.value * 60
			self.timer.hasEndTime = config.recording.zap_has_endtime.value
			if not self.timer.hasEndTime:
				self.timer.end = self.timer.begin + 1
		self.timer.resetRepeated()
		self.session.nav.RecordTimer.saveTimers()

	def retval(self):
		return self.timer


class SleepTimer(Setup):
	def __init__(self, session, setupMode=True):
		from Screens.InfoBar import InfoBar
		if not InfoBar and not InfoBar.instance:
			self.close()
		self.infoBarInstance = InfoBar.instance
		self.setupMode = setupMode
		Setup.__init__(self, session=session, setup="SleepTimer")
		self.timer = eTimer()
		self.timer.callback.append(self.timeout)
		self.timer.start(250)
		self.onClose.append(self.clearTimer)

	def selectionChanged(self):  # This is from Setup.py but it does not clear the footnote which stops the footnote flashing on the screen.
		self["description"].text = self.getCurrentDescription() if self["config"] else _("There are no items currently available for this screen.")

	def keySave(self):
		sleepTimer = config.usage.sleepTimer.value
		if sleepTimer == -1:
			sleepTimer = 0  # Default sleep timer if the event end time can't be determined, default is the sleep timer is disabled.
			ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if ref:
				path = ref.getPath()
				if path:  # Movie
					service = self.session.nav.getCurrentService()
					seek = service and service.seek()
					if seek:
						length = seek.getLength()
						position = seek.getPlayPosition()
						if length and position:
							sleepTimer = length[1] - position[1]
							if sleepTimer > 0:
								sleepTimer = int(sleepTimer // 90000)
				else:  # Service
					epg = eEPGCache.getInstance()
					event = epg.lookupEventTime(ref, -1, 0)
					if event:
						sleepTimer = event.getBeginTime() + event.getDuration() - int(time())
				sleepTimer += (config.recording.margin_after.value * 60)
		self.infoBarInstance.setSleepTimer(sleepTimer)
		self.infoBarInstance.setEnergyTimer(config.usage.energyTimer.value)
		Setup.keySave(self)

	def timeout(self):
		sleepTimer = self.infoBarInstance.sleepTimerState()
		if sleepTimer > 60:
			sleepTimer //= 60
			sleepMsg = ngettext("SleepTimer: %d minute remains.", "SleepTimer: %d minutes remain.", sleepTimer) % sleepTimer
		elif sleepTimer:
			sleepMsg = ngettext("SleepTimer: %d second remains.", "SleepTimer: %d seconds remain.", sleepTimer) % sleepTimer
		else:
			sleepMsg = _("SleepTimer: Inactive.")
		energyTimer = self.infoBarInstance.energyTimerState()
		if energyTimer > 60:
			energyTimer //= 60
			energyMsg = ngettext("Energy Timer: %d minute remains.", "Energy Timer: %d minutes remain.", energyTimer) % energyTimer
		elif energyTimer:
			energyMsg = ngettext("Energy Timer: %d second remains.", "Energy Timer: %d seconds remain.", energyTimer) % energyTimer
		else:
			energyMsg = _("Energy Timer: Inactive.")
		self.setFootnote("%s   %s" % (sleepMsg, energyMsg))
		self.timer.start(250)

	def clearTimer(self):
		self.timer.stop()
		self.timer.callback.remove(self.timeout)


class SleepTimerButton(SleepTimer):
	def __init__(self, session):
		SleepTimer.__init__(self, session, setupMode=False)

	def keySelect(self):
		SleepTimer.keySave(self)


class TimerLog(Screen):
	skin = """
	<screen name="TimerLog" title="Timer Log" position="center,center" size="950,590" resolution="1280,720">
		<widget name="log" position="0,0" size="e,e-50" font="Regular;20" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="380,e-40" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="570,e-40" size="180,40" backgroundColor="key_blue" conditional="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, timer):
		Screen.__init__(self, session, mandatoryWidgets=["log"], enableHelp=True)
		self.timer = timer
		self["log"] = ScrollLabel()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText(_("Refresh"))
		self["key_blue"] = StaticText(_("Clear Log"))
		self["actions"] = HelpableActionMap(self, ["CancelSaveActions", "OkActions", "ColorActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Close the screen without saving any changes")),
			"save": (self.keySave, _("Save the log changes and exit")),
			"ok": (self.refreshLog, _("Refresh the screen")),
			"yellow": (self.refreshLog, _("Refresh the screen")),
			"blue": (self.keyClearLog, _("Clear the logs for this timer")),
			"top": (self["log"].moveTop, _("Move to first line / screen")),
			"pageUp": (self["log"].pageUp, _("Move up a screen")),
			"up": (self["log"].moveUp, _("Move up a line")),
			# "left": (self["log"].pageUp, _("Move up a screen")),
			# "right": (self["log"].pageDown, _("Move down a screen")),
			"down": (self["log"].moveDown, _("Move down a line")),
			"pageDown": (self["log"].pageDown, _("Move down a screen")),
			"bottom": (self["log"].moveBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Timer Log Actions"))
		self.refreshLog()

	def refreshLog(self):
		self.timerLog = self.timer.log_entries[:]
		self["log"].setText("\n".join(["%s: %s" % (strftime("%s %s" % (config.usage.date.long.value, config.usage.time.short.value), localtime(x[0])), x[2]) for x in self.timerLog]))
		self.refreshButtons()

	def refreshButtons(self):
		self["key_blue"].setText(_("Clear Log") if self.timerLog else "")
		self["key_green"].setText(_("Save") if self.timerLog != self.timer.log_entries else "")

	def keyCancel(self):
		self.close((False,))

	def keySave(self):
		if self.timerLog == self.timer.log_entries:
			self.close((False,))
		else:
			self.timer.log_entries = self.timerLog
			self.close((True, self.timer))

	def keyClearLog(self):
		self.timerLog = []
		self["log"].setText("")
		self.refreshButtons()

	def createSummary(self):
		return TimerLogSummary


class TimerLogSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self["logname"] = StaticText(parent.timer.name if hasattr(parent.timer, "name") else _("Scheduler log"))
