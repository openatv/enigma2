from Screen import Screen
from LocationBox import LocationBox
import ChannelSelection
from ServiceReference import ServiceReference
from Components.config import config, ConfigSelection, ConfigText, ConfigSubList, ConfigDateTime, ConfigClock, ConfigYesNo, getConfigListEntry
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigListScreen
from Components.MenuList import MenuList
from Components.Button import Button
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.ChoiceBox import ChoiceBox
from RecordTimer import AFTEREVENT
from enigma import eEPGCache
import time
import datetime

class TimerEntry(Screen, ConfigListScreen):
	def __init__(self, session, timer):
		Screen.__init__(self, session)
		self.timer = timer
		
		self.entryStartDate = None
		self.entryEndDate = None
		self.entryService = None
		
		self["oktext"] = Label(_("OK"))
		self["canceltext"] = Label(_("Cancel"))
		self["locationtext"] = Label(_("Choose Location"))
		self["ok"] = Pixmap()
		self["cancel"] = Pixmap()
		self["location"] = Pixmap()

		self.createConfig()

		self["actions"] = NumberActionMap(["SetupActions", "ColorActions"],
		{
			"ok": self.keySelect,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"yellow": self.selectPath,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = session)
		self.createSetup("config")

		self.onLayoutFinish.append(self.handleLocation)

	def handleLocation(self):
		if config.usage.setup_level.index < 2: # -expert
			self["locationtext"].hide()
			self["location"].hide()

	def createConfig(self):
			justplay = self.timer.justplay
				
			afterevent = { AFTEREVENT.NONE: "nothing", AFTEREVENT.DEEPSTANDBY: "deepstandby", AFTEREVENT.STANDBY: "standby"}[self.timer.afterEvent]
			
			weekday_table = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

			# calculate default values
			day = []
			weekday = 0
			for x in range(0,7):
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
					for x in range(0, 7):
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
				weekday = (int(time.strftime("%w", time.localtime(self.timer.begin))) - 1) % 7
				day[weekday] = 1
			
			self.timerentry_justplay = ConfigSelection(choices = [("zap", _("zap")), ("record", _("record"))], default = {0: "record", 1: "zap"}[justplay])
			self.timerentry_afterevent = ConfigSelection(choices = [("nothing", _("do nothing")), ("standby", _("go to standby")), ("deepstandby", _("go to deep standby"))], default = afterevent)
			self.timerentry_type = ConfigSelection(choices = [("once",_("once")), ("repeated", _("repeated"))], default = type)
			self.timerentry_name = ConfigText(default = self.timer.name, visible_width = 50, fixed_size = False)
			self.timerentry_description = ConfigText(default = self.timer.description, visible_width = 50, fixed_size = False)

			self.timerentry_repeated = ConfigSelection(default = repeated, choices = [("daily", _("daily")), ("weekly", _("weekly")), ("weekdays", _("Mon-Fri")), ("user", _("user defined"))])

			self.timerentry_startdate = ConfigDateTime(default = self.timer.begin, formatstring = _("%d.%B %Y"), increment = 86400)
			self.timerentry_starttime = ConfigClock(default = self.timer.begin)

			self.timerentry_enddate = ConfigDateTime(default = self.timer.end, formatstring =  _("%d.%B %Y"), increment = 86400)
			self.timerentry_endtime = ConfigClock(default = self.timer.end)

			self.timerentry_dirname = ConfigSelection(choices = [self.timer.dirname or "/hdd/movie/"])

			self.timerentry_repeatedbegindate = ConfigDateTime(default = self.timer.repeatedbegindate, formatstring = _("%d.%B %Y"), increment = 86400)

			self.timerentry_weekday = ConfigSelection(default = weekday_table[weekday], choices = [("mon",_("Monday")), ("tue", _("Tuesday")), ("wed",_("Wednesday")), ("thu", _("Thursday")), ("fri", _("Friday")), ("sat", _("Saturday")), ("sun", _("Sunday"))])

			self.timerentry_day = ConfigSubList()
			for x in range(0,7):
				self.timerentry_day.append(ConfigYesNo(default = day[x]))

			# FIXME some service-chooser needed here
			servicename = "N/A"
			try: # no current service available?
				servicename = str(self.timer.service_ref.getServiceName())
			except:
				pass
			self.timerentry_service_ref = self.timer.service_ref
			self.timerentry_service = ConfigSelection([servicename])
			
			self.timerentry_startdate.addNotifier(self.checkDate)
			self.timerentry_enddate.addNotifier(self.checkDate)

	def checkDate(self, configElement):
		if configElement is self.timerentry_startdate:
			if self.timerentry_enddate.value < self.timerentry_startdate.value:
				self.timerentry_enddate.value = self.timerentry_startdate.value
				self["config"].invalidate(self.entryEndDate)
		if configElement is self.timerentry_enddate:
			if (self.timerentry_enddate.value < self.timerentry_startdate.value):
				self.timerentry_startdate.value = self.timerentry_enddate.value
				self["config"].invalidate(self.entryStartDate)

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
			self.frequencyEntry = getConfigListEntry(_("Frequency"), self.timerentry_repeated)
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

			#self.list.append(getConfigListEntry("StartDate", self.timerentry_startdate))
#		self.list.append(getConfigListEntry("Weekday", self.timerentry_weekday))

		self.entryStartDate = getConfigListEntry(_("Start"), self.timerentry_startdate)
		if self.timerentry_type.value == "once":
			self.list.append(self.entryStartDate)
			self.list.append(getConfigListEntry(" ", self.timerentry_starttime))
		else:
			self.list.append(getConfigListEntry(_("StartTime"), self.timerentry_starttime))

		self.entryEndDate = getConfigListEntry(_("End"), self.timerentry_enddate)
		if self.timerentry_type.value == "once":
			if self.timerentry_justplay.value != "zap":
				self.list.append(self.entryEndDate)
				self.list.append(getConfigListEntry(" ", self.timerentry_endtime))
		else:
			if self.timerentry_justplay.value != "zap":
				self.list.append(getConfigListEntry(_("EndTime"), self.timerentry_endtime))

		if self.timerentry_justplay.value != "zap":
			if config.usage.setup_level.index >= 2: # expert+
				self.list.append(getConfigListEntry(_("Location"), self.timerentry_dirname))
			self.list.append(getConfigListEntry(_("After event"), self.timerentry_afterevent))

		self.channelEntry = getConfigListEntry(_("Channel"), self.timerentry_service)
		self.list.append(self.channelEntry)

		self[widget].list = self.list
		self[widget].l.setList(self.list)

	def newConfig(self):
		print "newConfig", self["config"].getCurrent()
		if self["config"].getCurrent() == self.timerTypeEntry:
			self.createSetup("config")
		if self["config"].getCurrent() == self.timerJustplayEntry:
			self.createSetup("config")
		if self["config"].getCurrent() == self.frequencyEntry:
			self.createSetup("config")

	def keyLeft(self):
		if self["config"].getCurrent() is self.channelEntry:
			self.keySelect()
		else:
			ConfigListScreen.keyLeft(self)
			self.newConfig()

	def keyRight(self):
		if self["config"].getCurrent() is self.channelEntry:
			self.keySelect()
		else:
			ConfigListScreen.keyRight(self)
			self.newConfig()
		
	def keySelect(self):
		if self["config"].getCurrent() == self.channelEntry:
			self.session.openWithCallback(self.finishedChannelSelection, ChannelSelection.SimpleChannelSelection, _("Select channel to record from"))
		else:
			self.keyGo()

	def finishedChannelSelection(self, *args):
		if len(args):
			self.timerentry_service_ref = ServiceReference(args[0])
			self.timerentry_service.setCurrentText(self.timerentry_service_ref.getServiceName())
			self["config"].invalidate(self.channelEntry)

	def getTimestamp(self, date, mytime):
		d = time.localtime(date)
		dt = datetime.datetime(d.tm_year, d.tm_mon, d.tm_mday, mytime[0], mytime[1])
		return int(time.mktime(dt.timetuple()))

	def buildRepeatedBegin(self, rep_time, start_time):
		d = time.localtime(rep_time)
		dt = datetime.datetime(d.tm_year, d.tm_mon, d.tm_mday, start_time[0], start_time[1])
		return int(time.mktime(dt.timetuple()))

	def getBeginEnd(self):
		enddate = self.timerentry_enddate.value
		endtime = self.timerentry_endtime.value
		
		startdate = self.timerentry_startdate.value
		starttime = self.timerentry_starttime.value
		
		begin = self.getTimestamp(startdate, starttime)
		end = self.getTimestamp(enddate, endtime)
		
		# because of the dateChecks, startdate can't be < enddate.
		# however, the endtime can be less than the starttime.
		# in this case, add 1 day.
		if end < begin:
			end += 86400
		return begin, end

	def keyGo(self):
		self.timer.name = self.timerentry_name.value
		self.timer.description = self.timerentry_description.value
		self.timer.justplay = self.timerentry_justplay.value == "zap"
		self.timer.resetRepeated()
		self.timer.afterEvent = {"nothing": AFTEREVENT.NONE, "deepstandby": AFTEREVENT.DEEPSTANDBY, "standby": AFTEREVENT.STANDBY}[self.timerentry_afterevent.value]
		self.timer.service_ref = self.timerentry_service_ref

		# TODO: fix that thing with none (this might as well just be ignored)
		if self.timerentry_dirname.value == "/hdd/movie/":
			self.timer.dirname = None
		else:
			self.timer.dirname = self.timerentry_dirname.value

		if self.timerentry_type.value == "once":
			self.timer.begin, self.timer.end = self.getBeginEnd()
		if self.timerentry_type.value == "repeated":
			if self.timerentry_repeated.value == "daily":
				for x in range(0,7):
					self.timer.setRepeated(x)

			if self.timerentry_repeated.value == "weekly":
				self.timer.setRepeated(self.timerentry_weekday.index)
				
			if self.timerentry_repeated.value == "weekdays":
				for x in range(0,5):
					self.timer.setRepeated(x)
				
			if self.timerentry_repeated.value == "user":
				for x in range(0,7):
					if self.timerentry_day[x].value:
						self.timer.setRepeated(x)

			self.timer.repeatedbegindate = self.buildRepeatedBegin(self.timerentry_repeatedbegindate.value, self.timerentry_starttime.value)
			self.timer.begin = self.getTimestamp(time.time(), self.timerentry_starttime.value)
			self.timer.end = self.getTimestamp(time.time(), self.timerentry_endtime.value)
			
			# when a timer end is set before the start, add 1 day
			if self.timer.end < self.timer.begin:
				self.timer.end += 86400

		if self.timer.eit is not None:
			event = eEPGCache.getInstance().lookupEventId(self.timer.service_ref.ref, self.timer.eit)
			if event is not None:
				n = event.getNumOfLinkageServices()
				if n > 0:
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

		self.saveTimer()
		self.close((True, self.timer))

	def subserviceSelected(self, service):
		if not service is None:
			self.timer.service_ref = ServiceReference(service[1])
		self.saveTimer()
		self.close((True, self.timer))

	def saveTimer(self):
		self.session.nav.RecordTimer.saveTimer()

	def keyCancel(self):
		self.close((False,))

	def selectPath(self):
		if config.usage.setup_level.index < 2: #-expert
			return
		self.session.openWithCallback(
			self.pathSelected,
			LocationBox,
			text = _("Choose target folder"),
			filename = "",
			currDir = None, # TODO: fix FileList to correctly determine mountpoint
			minFree = 100
		)

	def pathSelected(self, res):
		if res is not None:
			self.timerentry_dirname.choices.append(res)
			self.timerentry_dirname.description[res] = res
			self.timerentry_dirname.value = res

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

	def deleteEntry(self):
		cur = self["loglist"].getCurrent()
		if cur is None:
			return 
		self.log_entries.remove(cur[1])
		self.fillLogList()
		self["loglist"].l.setList(self.list)
		self.updateText()

	def fillLogList(self):
		self.list = [ ]
		for x in self.log_entries:
			self.list.append((str(time.strftime("%Y-%m-%d %H-%M", time.localtime(x[0])) + " - " + x[2]), x))
	
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
		if len(self.list) > 0:
			self["logentry"].setText(str(self["loglist"].getCurrent()[1][2]))
		else:
			self["logentry"].setText("")
