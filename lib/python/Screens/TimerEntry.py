from Screen import Screen
import ChannelSelection
from ServiceReference import ServiceReference
from Components.config import config, ConfigSelection, ConfigText, ConfigSubList, ConfigDateTime, ConfigClock, ConfigYesNo, getConfigListEntry
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigListScreen
from Components.MenuList import MenuList
from Components.Button import Button
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.SystemInfo import SystemInfo
from Components.UsageConfig import defaultMoviePath
from Screens.MovieSelection import getPreferredTagEditor
from Screens.LocationBox import MovieLocationBox
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from RecordTimer import AFTEREVENT
from enigma import eEPGCache, eServiceReference
from time import localtime, mktime, time, strftime
from datetime import datetime

class TimerEntry(Screen, ConfigListScreen):
	def __init__(self, session, timer):
		Screen.__init__(self, session)
		self.timer = timer

		self.entryDate = None
		self.entryService = None

		self["oktext"] = Label(_("OK"))
		self["canceltext"] = Label(_("Cancel"))
		self["ok"] = Pixmap()
		self["cancel"] = Pixmap()

		self.createConfig()

		self["actions"] = NumberActionMap(["SetupActions", "GlobalActions", "PiPSetupActions"],
		{
			"ok": self.keySelect,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"volumeUp": self.incrementStart,
			"volumeDown": self.decrementStart,
			"size+": self.incrementEnd,
			"size-": self.decrementEnd
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = session)
		self.setTitle(_("Timer entry"))
		self.createSetup("config")

	def createConfig(self):
			justplay = self.timer.justplay

			afterevent = {
				AFTEREVENT.NONE: "nothing",
				AFTEREVENT.DEEPSTANDBY: "deepstandby",
				AFTEREVENT.STANDBY: "standby",
				AFTEREVENT.AUTO: "auto"
				}[self.timer.afterEvent]

			if self.timer.record_ecm and self.timer.descramble:
				recordingtype = "descrambled+ecm"
			elif self.timer.record_ecm:
				recordingtype = "scrambled+ecm"
			elif self.timer.descramble:
				recordingtype = "normal"

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
				weekday = int(strftime("%u", localtime(self.timer.begin))) - 1
				day[weekday] = 1

			self.timerentry_justplay = ConfigSelection(choices = [("zap", _("zap")), ("record", _("record"))], default = {0: "record", 1: "zap"}[justplay])
			if SystemInfo["DeepstandbySupport"]:
				shutdownString = _("go to deep standby")
			else:
				shutdownString = _("shut down")
			self.timerentry_afterevent = ConfigSelection(choices = [("nothing", _("do nothing")), ("standby", _("go to standby")), ("deepstandby", shutdownString), ("auto", _("auto"))], default = afterevent)
			self.timerentry_recordingtype = ConfigSelection(choices = [("normal", _("normal")), ("descrambled+ecm", _("descramble and record ecm")), ("scrambled+ecm", _("don't descramble, record ecm"))], default = recordingtype)
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
			self.list.append(getConfigListEntry(_("Recording type"), self.timerentry_recordingtype))

		self[widget].list = self.list
		self[widget].l.setList(self.list)

	def newConfig(self):
		print "newConfig", self["config"].getCurrent()
		if self["config"].getCurrent() in (self.timerTypeEntry, self.timerJustplayEntry, self.frequencyEntry, self.entryShowEndTime):
			self.createSetup("config")

	def keyLeft(self):
		if self["config"].getCurrent() in (self.channelEntry, self.tagsSet):
			self.keySelect()
		else:
			ConfigListScreen.keyLeft(self)
			self.newConfig()

	def keyRight(self):
		if self["config"].getCurrent() in (self.channelEntry, self.tagsSet):
			self.keySelect()
		else:
			ConfigListScreen.keyRight(self)
			self.newConfig()

	def keySelect(self):
		cur = self["config"].getCurrent()
		if cur == self.channelEntry:
			self.session.openWithCallback(
				self.finishedChannelSelection,
				ChannelSelection.SimpleChannelSelection,
				_("Select channel to record from")
			)
		elif config.usage.setup_level.index >= 2 and cur == self.dirname:
			self.session.openWithCallback(
				self.pathSelected,
				MovieLocationBox,
				_("Choose target folder"),
				self.timerentry_dirname.value,
				minFree = 100 # We require at least 100MB free space
			)
		elif getPreferredTagEditor() and cur == self.tagsSet:
			self.session.openWithCallback(
				self.tagEditFinished,
				getPreferredTagEditor(),
				self.timerentry_tags
			)
		else:
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
		if not self.timerentry_service_ref.isRecordable():
			self.session.openWithCallback(self.selectChannelSelector, MessageBox, _("You didn't select a channel to record from."), MessageBox.TYPE_ERROR)
			return
		self.timer.name = self.timerentry_name.value
		self.timer.description = self.timerentry_description.value
		self.timer.justplay = self.timerentry_justplay.value == "zap"
		if self.timerentry_justplay.value == "zap":
			if not self.timerentry_showendtime.value:
				self.timerentry_endtime.value = self.timerentry_starttime.value
		self.timer.resetRepeated()
		self.timer.afterEvent = {
			"nothing": AFTEREVENT.NONE,
			"deepstandby": AFTEREVENT.DEEPSTANDBY,
			"standby": AFTEREVENT.STANDBY,
			"auto": AFTEREVENT.AUTO
			}[self.timerentry_afterevent.value]
		self.timer.descramble = {
			"normal": True,
			"descrambled+ecm": True,
			"scrambled+ecm": False,
			}[self.timerentry_recordingtype.value]
		self.timer.record_ecm = {
			"normal": False,
			"descrambled+ecm": True,
			"scrambled+ecm": True,
			}[self.timerentry_recordingtype.value]
		self.timer.service_ref = self.timerentry_service_ref
		self.timer.tags = self.timerentry_tags

		if self.timer.dirname or self.timerentry_dirname.value != defaultMoviePath():
			self.timer.dirname = self.timerentry_dirname.value
			config.movielist.last_timer_videodir.value = self.timer.dirname
			config.movielist.last_timer_videodir.save()

		if self.timerentry_type.value == "once":
			self.timer.begin, self.timer.end = self.getBeginEnd()
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

	def incrementStart(self):
		self.timerentry_starttime.increment()
		self["config"].invalidate(self.entryStartTime)

	def decrementStart(self):
		self.timerentry_starttime.decrement()
		self["config"].invalidate(self.entryStartTime)

	def incrementEnd(self):
		if self.entryEndTime is not None:
			self.timerentry_endtime.increment()
			self["config"].invalidate(self.entryEndTime)

	def decrementEnd(self):
		if self.entryEndTime is not None:
			self.timerentry_endtime.decrement()
			self["config"].invalidate(self.entryEndTime)

	def subserviceSelected(self, service):
		if not service is None:
			self.timer.service_ref = ServiceReference(service[1])
		self.saveTimer()
		self.close((True, self.timer))

	def saveTimer(self):
		self.session.nav.RecordTimer.saveTimer()

	def keyCancel(self):
		self.close((False,))

	def pathSelected(self, res):
		if res is not None:
			if config.movielist.videodirs.value != self.timerentry_dirname.choices:
				self.timerentry_dirname.setChoices(config.movielist.videodirs.value, default=res)
			self.timerentry_dirname.value = res

	def tagEditFinished(self, ret):
		if ret is not None:
			self.timerentry_tags = ret
			self.timerentry_tagsset.setChoices([not ret and "None" or " ".join(ret)])
			self["config"].invalidate(self.tagsSet)

class TimerLog(Screen):
	def __init__(self, session, timer):
		Screen.__init__(self, session)
		self.timer = timer;
		self.log_entries = self.timer.log_entries[:]

		self.fillLogList()

		self["loglist"] = MenuList(self.list)
		self["logentry"] = Label()

		self["key_red"] = Button(_("Delete entry"))
		self["key_green"] = Button()
		self["key_yellow"] = Button("")
		self["key_blue"] = Button(_("Clear log"))

		self.onShown.append(self.updateText)

		self["actions"] = NumberActionMap(["OkCancelActions", "DirectionActions", "ColorActions"],
		{
			"ok": self.keyClose,
			"cancel": self.keyClose,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right,
			"red": self.deleteEntry,
			"blue": self.clearLog
		}, -1)
		self.setTitle(_("Timer log"))

	def deleteEntry(self):
		cur = self["loglist"].getCurrent()
		if cur is None:
			return 
		self.log_entries.remove(cur[1])
		self.fillLogList()
		self["loglist"].l.setList(self.list)
		self.updateText()

	def fillLogList(self):
		self.list = [(str(strftime("%Y-%m-%d %H-%M", localtime(x[0])) + " - " + x[2]), x) for x in self.log_entries]

	def clearLog(self):
		self.log_entries = []
		self.fillLogList()
		self["loglist"].l.setList(self.list)
		self.updateText()

	def keyClose(self):
		if self.timer.log_entries != self.log_entries:
			self.timer.log_entries = self.log_entries
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
