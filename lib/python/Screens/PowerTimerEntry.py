from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Components.config import ConfigSelection, ConfigSubList, ConfigDateTime, ConfigClock, ConfigYesNo, ConfigInteger, getConfigListEntry
from Components.ActionMap import NumberActionMap, HelpableNumberActionMap
from Components.ConfigList import ConfigListScreen
from Components.MenuList import MenuList
from Components.Button import Button
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.SystemInfo import SystemInfo
from Components.Sources.Boolean import Boolean
from PowerTimer import AFTEREVENT, TIMERTYPE
from boxbranding import getMachineBrand, getMachineName
from time import localtime, mktime, time, strftime
from datetime import datetime

class TimerEntry(Screen, ConfigListScreen, HelpableScreen):
	def __init__(self, session, timer):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.timer = timer

		self.entryDate = None
		self.entryService = None

		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		self["description"] = Label("")
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("OK"))
		self["key_yellow"] = Label()
		self["key_blue"] = Label()

		self.createConfig()

		self["actions"] = HelpableNumberActionMap(self, ["SetupActions", "GlobalActions", "PiPSetupActions"], {
			"ok": (self.keySelect, _("Save the timer and exit")),
			"save": (self.keyGo, "Save the timer and exit"),
			"cancel": (self.keyCancel, "Cancel creation of the timer and exit"),
			"volumeUp": (self.incrementStart, _("Increment start time")),
			"volumeDown": (self.decrementStart, _("Decrement start time")),
			"size+": (self.incrementEnd, _("Increment end time")),
			"size-": (self.decrementEnd, _("Decrement end time"))
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session)
		self.setTitle(_("PowerManager entry"))
		self.createSetup("config")
		if self.selectionChanged not in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		if self["config"].getCurrent():
			if len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2]:
				self["description"].setText(self["config"].getCurrent()[2])

	def createConfig(self):
		afterevent = {
			AFTEREVENT.NONE: "nothing",
			AFTEREVENT.WAKEUPTOSTANDBY: "wakeuptostandby",
			AFTEREVENT.STANDBY: "standby",
			AFTEREVENT.DEEPSTANDBY: "deepstandby"
		}[self.timer.afterEvent]

		timertype = {
			TIMERTYPE.WAKEUP: "wakeup",
			TIMERTYPE.WAKEUPTOSTANDBY: "wakeuptostandby",
			TIMERTYPE.AUTOSTANDBY: "autostandby",
			TIMERTYPE.AUTODEEPSTANDBY: "autodeepstandby",
			TIMERTYPE.STANDBY: "standby",
			TIMERTYPE.DEEPSTANDBY: "deepstandby",
			TIMERTYPE.REBOOT: "reboot",
			TIMERTYPE.RESTART: "restart"
		}[self.timer.timerType]

		weekday_table = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

		# calculate default values
		day = []
		weekday = 0
		for x in (0, 1, 2, 3, 4, 5, 6):
			day.append(0)
		if self.timer.repeated:  # repeated
			type = "repeated"
			if self.timer.repeated == 31:  # Mon-Fri
				repeated = "weekdays"
			elif self.timer.repeated == 127:  # daily
				repeated = "daily"
			else:
				flags = self.timer.repeated
				repeated = "user"
				count = 0
				for x in (0, 1, 2, 3, 4, 5, 6):
					if flags == 1:  # weekly
						print "Set to weekday " + str(x)
						weekday = x
					if flags & 1 == 1:  # set user defined flags
						day[x] = 1
						count += 1
					else:
						day[x] = 0
					flags >>= 1
				if count == 1:
					repeated = "weekly"
		else:  # once
			type = "once"
			repeated = None
			weekday = int(strftime("%u", localtime(self.timer.begin))) - 1
			day[weekday] = 1

		autosleepinstandbyonly = self.timer.autosleepinstandbyonly
		autosleepdelay = self.timer.autosleepdelay
		autosleeprepeat = self.timer.autosleeprepeat

		if SystemInfo["DeepstandbySupport"]:
			shutdownString = _("go to deep standby")
		else:
			shutdownString = _("shut down")
		self.timerentry_timertype = ConfigSelection(choices=[("wakeup", _("wakeup")), ("wakeuptostandby", _("wakeup to standby")), ("autostandby", _("auto standby")), ("autodeepstandby", _("auto deepstandby")), ("standby", _("go to standby")), ("deepstandby", shutdownString), ("reboot", _("reboot system")), ("restart", _("restart GUI"))], default=timertype)
		self.timerentry_afterevent = ConfigSelection(choices=[("nothing", _("do nothing")), ("wakeuptostandby", _("wakeup to standby")), ("standby", _("go to standby")), ("deepstandby", shutdownString), ("nothing", _("do nothing"))], default=afterevent)
		self.timerentry_type = ConfigSelection(choices=[("once", _("once")), ("repeated", _("repeated"))], default=type)

		self.timerentry_repeated = ConfigSelection(default=repeated, choices=[("daily", _("daily")), ("weekly", _("weekly")), ("weekdays", _("Mon-Fri")), ("user", _("user defined"))])
		self.timerrntry_autosleepdelay = ConfigInteger(default=autosleepdelay, limits=(10, 300))
		self.timerentry_autosleeprepeat = ConfigSelection(choices=[("once", _("once")), ("repeated", _("repeated"))], default=autosleeprepeat)
		self.timerrntry_autosleepinstandbyonly = ConfigSelection(choices=[("yes", _("Yes")), ("no", _("No"))], default=autosleepinstandbyonly)

		self.timerentry_date = ConfigDateTime(default=self.timer.begin, formatstring=_("%a %d %b %Y"), increment=86400)
		self.timerentry_starttime = ConfigClock(default=self.timer.begin)
		self.timerentry_endtime = ConfigClock(default=self.timer.end)
		self.timerentry_showendtime = ConfigSelection(default=(((self.timer.end - self.timer.begin) / 60) > 1), choices=[(True, _("yes")), (False, _("no"))])

		self.timerentry_repeatedbegindate = ConfigDateTime(default=self.timer.repeatedbegindate, formatstring=_("%a %d %b %Y"), increment=86400)

		self.timerentry_weekday = ConfigSelection(default=weekday_table[weekday], choices=[("mon", _("Monday")), ("tue", _("Tuesday")), ("wed", _("Wednesday")), ("thu", _("Thursday")), ("fri", _("Friday")), ("sat", _("Saturday")), ("sun", _("Sunday"))])

		self.timerentry_day = ConfigSubList()
		for x in (0, 1, 2, 3, 4, 5, 6):
			self.timerentry_day.append(ConfigYesNo(default=day[x]))

	def createSetup(self, widget):
		self.list = []
		self.timerType = getConfigListEntry(_("Timer type"), self.timerentry_timertype, _("Select the action that the timer will perform. \"Auto\" actions will be done when your %s %s is idle.") % (getMachineBrand(), getMachineName()))
		self.list.append(self.timerType)

		if self.timerentry_timertype.value == "autostandby" or self.timerentry_timertype.value == "autodeepstandby":
			if self.timerentry_timertype.value == "autodeepstandby":
				self.list.append(getConfigListEntry(_("Auto deep standby timers only active when in standby."), self.timerrntry_autosleepinstandbyonly, _("If enabled, the timer will only be active when your %s %s is in standby mode.") % (getMachineBrand(), getMachineName())))
			self.list.append(getConfigListEntry(_("Sleep delay"), self.timerrntry_autosleepdelay, _("\"Auto\" timers will try to shut down your %s %s when the remote control hasn't been used for longer than this time. In minutes.") % (getMachineBrand(), getMachineName())))
			self.list.append(getConfigListEntry(_("Repeat type"), self.timerentry_autosleeprepeat, _("A repeating timer or just once?")))
			self.timerTypeEntry = getConfigListEntry(_("Repeat type"), self.timerentry_type, _("A repeating timer or just once?"))
			self.entryShowEndTime = getConfigListEntry(_("Set end time"), self.timerentry_showendtime, _("Allow the timer to perform a later completion action. Otherwise the \"After event\" action is performed immediately after the \"Timer type\" action."))
			self.frequencyEntry = getConfigListEntry(_("Repeats"), self.timerentry_repeated, _("The type of repetition required: daily, weekly on a specified day, on weekdays (Mon-Fri), or regularly on specified days."))
		else:
			self.timerTypeEntry = getConfigListEntry(_("Repeat type"), self.timerentry_type, _("A repeating timer or just once?"))
			self.list.append(self.timerTypeEntry)

			if self.timerentry_type.value == "once":
				self.frequencyEntry = None
			else:  # repeated
				self.frequencyEntry = getConfigListEntry(_("Repeats"), self.timerentry_repeated, _("The type of repetition required: daily, weekly on a specified day, on weekdays (Mon-Fri), or regularly on specified days"))
				self.list.append(self.frequencyEntry)
				self.repeatedbegindateEntry = getConfigListEntry(_("Starting on"), self.timerentry_repeatedbegindate, _("The timer becomes active (but doesn't necessarily run) on this date."))
				self.list.append(self.repeatedbegindateEntry)
				if self.timerentry_repeated.value == "daily":
					pass
				if self.timerentry_repeated.value == "weekdays":
					pass
				if self.timerentry_repeated.value == "weekly":
					self.list.append(getConfigListEntry(_("Weekday"), self.timerentry_weekday, _("The day of the week the timer runs.")))

				if self.timerentry_repeated.value == "user":
					self.list.append(getConfigListEntry(_("Monday"), self.timerentry_day[0], _("Enable/disable the timer on Mondays.")))
					self.list.append(getConfigListEntry(_("Tuesday"), self.timerentry_day[1], _("Enable/disable the timer on Tuesdays.")))
					self.list.append(getConfigListEntry(_("Wednesday"), self.timerentry_day[2], _("Enable/disable the timer on Wednesdays.")))
					self.list.append(getConfigListEntry(_("Thursday"), self.timerentry_day[3], _("Enable/disable the timer on Thursdays.")))
					self.list.append(getConfigListEntry(_("Friday"), self.timerentry_day[4], _("Enable/disable the timer on Fridays.")))
					self.list.append(getConfigListEntry(_("Saturday"), self.timerentry_day[5], _("Enable/disable the timer on Saturdays.")))
					self.list.append(getConfigListEntry(_("Sunday"), self.timerentry_day[6], _("Enable/disable the timer on Sundays.")))

			self.entryDate = getConfigListEntry(_("Date"), self.timerentry_date, _("The date the timer performs the action in \"Timer type\"."))
			if self.timerentry_type.value == "once":
				self.list.append(self.entryDate)

			self.entryStartTime = getConfigListEntry(_("Start time"), self.timerentry_starttime, _("The time the timer performs the action in \"Timer type\"."))
			self.list.append(self.entryStartTime)

			self.entryShowEndTime = getConfigListEntry(_("Set end time"), self.timerentry_showendtime, _("Allow the timer to perform a later completion action. Otherwise the \"After event\" action is performed immediately after the \"Timer type\" action."))
			self.list.append(self.entryShowEndTime)
			self.entryEndTime = getConfigListEntry(_("End time"), self.timerentry_endtime, _("Time when the timer completes and the \"After event\" action is taken. If the end time is earlier than the start time of the timer, the completion action takes place at that time on the following day."))
			if self.timerentry_showendtime.value:
				self.list.append(self.entryEndTime)

			self.list.append(getConfigListEntry(_("After event"), self.timerentry_afterevent, _("Action taken on the completion of the timer.")))

		self[widget].list = self.list
		self[widget].l.setList(self.list)

	def newConfig(self):
		if self["config"].getCurrent() in (self.timerType, self.timerTypeEntry, self.frequencyEntry, self.entryShowEndTime):
			self.createSetup("config")

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def keySelect(self):
		cur = self["config"].getCurrent()
		self.keyGo()

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

	def keyGo(self, result=None):
		if not self.timerentry_showendtime.value:
			self.timerentry_endtime.value = self.timerentry_starttime.value

		self.timer.resetRepeated()
		self.timer.timerType = {
			"wakeup": TIMERTYPE.WAKEUP,
			"wakeuptostandby": TIMERTYPE.WAKEUPTOSTANDBY,
			"autostandby": TIMERTYPE.AUTOSTANDBY,
			"autodeepstandby": TIMERTYPE.AUTODEEPSTANDBY,
			"standby": TIMERTYPE.STANDBY,
			"deepstandby": TIMERTYPE.DEEPSTANDBY,
			"reboot": TIMERTYPE.REBOOT,
			"restart": TIMERTYPE.RESTART
		}[self.timerentry_timertype.value]
		self.timer.afterEvent = {
			"nothing": AFTEREVENT.NONE,
			"wakeuptostandby": AFTEREVENT.WAKEUPTOSTANDBY,
			"standby": AFTEREVENT.STANDBY,
			"deepstandby": AFTEREVENT.DEEPSTANDBY
		}[self.timerentry_afterevent.value]

		if self.timerentry_type.value == "once":
			self.timer.begin, self.timer.end = self.getBeginEnd()

		if self.timerentry_timertype.value == "autostandby" or self.timerentry_timertype.value == "autodeepstandby":
			self.timer.begin = int(time()) + 10
			self.timer.end = self.timer.begin
			self.timer.autosleepinstandbyonly = self.timerrntry_autosleepinstandbyonly.value
			self.timer.autosleepdelay = self.timerrntry_autosleepdelay.value
			self.timer.autosleeprepeat = self.timerentry_autosleeprepeat.value
		if self.timerentry_type.value == "repeated":
			if self.timerentry_repeated.value == "daily":
				for x in (0, 1, 2, 3, 4, 5, 6):
					self.timer.setRepeated(x)

			if self.timerentry_repeated.value == "weekly":
				self.timer.setRepeated(self.timerentry_weekday.index)

			if self.timerentry_repeated.value == "weekdays":
				for x in (0, 1, 2, 3, 4):
					self.timer.setRepeated(x)

			if self.timerentry_repeated.value == "user":
				for x in (0, 1, 2, 3, 4, 5, 6):
					if self.timerentry_day[x].value:
						self.timer.setRepeated(x)

			self.timer.repeatedbegindate = self.getTimestamp(self.timerentry_repeatedbegindate.value, self.timerentry_starttime.value)
			if self.timer.repeated:
				self.timer.begin = self.getTimestamp(self.timerentry_repeatedbegindate.value, self.timerentry_starttime.value)
				self.timer.end = self.getTimestamp(self.timerentry_repeatedbegindate.value, self.timerentry_endtime.value)
			else:
				self.timer.begin = self.getTimestamp(time.time(), self.timerentry_starttime.value)
				self.timer.end = self.getTimestamp(time.time(), self.timerentry_endtime.value)

			# when a timer end is set before the start, add 1 day
			if self.timer.end < self.timer.begin:
				self.timer.end += 86400

		self.timer.origbegin = self.timer.begin
		self.timer.origend = self.timer.end

		self.saveTimer()
		self.close((True, self.timer))

	def incrementStart(self):
		self.timerentry_starttime.increment()
		self["config"].invalidate(self.entryStartTime)
		if self.timerentry_type.value == "once" and self.timerentry_starttime.value == [0, 0]:
			self.timerentry_date.value += 86400
			self["config"].invalidate(self.entryDate)

	def decrementStart(self):
		self.timerentry_starttime.decrement()
		self["config"].invalidate(self.entryStartTime)
		if self.timerentry_type.value == "once" and self.timerentry_starttime.value == [23, 59]:
			self.timerentry_date.value -= 86400
			self["config"].invalidate(self.entryDate)

	def incrementEnd(self):
		if self.entryEndTime is not None:
			self.timerentry_endtime.increment()
			self["config"].invalidate(self.entryEndTime)

	def decrementEnd(self):
		if self.entryEndTime is not None:
			self.timerentry_endtime.decrement()
			self["config"].invalidate(self.entryEndTime)

	def saveTimer(self):
		self.session.nav.PowerTimer.saveTimer()

	def keyCancel(self):
		self.close((False,))

class TimerLog(Screen):
	def __init__(self, session, timer):
		Screen.__init__(self, session)
		self.skinName = "TimerLog"
		self.timer = timer
		self.log_entries = self.timer.log_entries[:]

		self.fillLogList()

		self["loglist"] = MenuList(self.list)
		self["logentry"] = Label()

		self["key_red"] = Button(_("Delete entry"))
		self["key_green"] = Button()
		self["key_yellow"] = Button("")
		self["key_blue"] = Button(_("Clear log"))

		self.onShown.append(self.updateText)

		self["actions"] = NumberActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {
			"ok": self.keyClose,
			"cancel": self.keyClose,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right,
			"red": self.deleteEntry,
			"blue": self.clearLog
		}, -1)
		self.setTitle(_("PowerManager log"))

	def deleteEntry(self):
		cur = self["loglist"].getCurrent()
		if cur is None:
			return
		self.log_entries.remove(cur[1])
		self.fillLogList()
		self["loglist"].l.setList(self.list)
		self.updateText()

	def fillLogList(self):
		self.list = [(str(strftime("%a %d %b %Y %H:%M", localtime(x[0])) + " - " + x[2]), x) for x in self.log_entries]

	def clearLog(self):
		self.log_entries = []
		self.fillLogList()
		self["loglist"].l.setList(self.list)
		self.updateText()

	def keyClose(self):
		if self.timer.log_entries != self.log_entries:
			self.timer.log_entries = self.log_entries
			self.session.nav.PowerTimer.saveTimer()
			self.close((True, self.timer))
		else:
			self.close((False,))

	def up(self):
		self["loglist"].instance.moveSelection(self["loglist"].instance.moveUp)
		self.updateText()

	def down(self):
		self["loglist"].instance.moveSelection(self["loglist"].instance.moveDown)
		self.updateText()

	def left(self):
		self["loglist"].instance.moveSelection(self["loglist"].instance.pageUp)
		self.updateText()

	def right(self):
		self["loglist"].instance.moveSelection(self["loglist"].instance.pageDown)
		self.updateText()

	def updateText(self):
		if self.list:
			self["logentry"].setText(str(self["loglist"].getCurrent()[1][2]))
		else:
			self["logentry"].setText("")
