from Screen import Screen
import ChannelSelection
from ServiceReference import ServiceReference
from Components.config import *
from Components.ActionMap import ActionMap, NumberActionMap
from Components.ConfigList import ConfigList
from Components.MenuList import MenuList
from Components.Button import Button
from Components.NimManager import nimmanager
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from RecordTimer import AFTEREVENT
from enigma import eEPGCache
import time
import datetime

class TimerEntry(Screen):
	def __init__(self, session, timer):
		Screen.__init__(self, session)
		self.timer = timer
		
		self["oktext"] = Label(_("OK"))
		self["canceltext"] = Label(_("Cancel"))
		self["ok"] = Pixmap()
		self["cancel"] = Pixmap()

		self.createConfig()

		self["actions"] = NumberActionMap(["SetupActions", "TextEntryActions"],
		{
			"ok": self.keySelect,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"left": self.keyLeft,
			"right": self.keyRight,
			"delete": self.keyDelete,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, -1)

		self.list = []
		self["config"] = ConfigList(self.list)
		self.createSetup("config")

	def createConfig(self):
			config.timerentry = ConfigSubsection()
			
			if (self.timer.justplay):
				justplay = 0
			else:
				justplay = 1
				
			afterevent = { AFTEREVENT.NONE: 0, AFTEREVENT.DEEPSTANDBY: 1, AFTEREVENT.STANDBY: 2}[self.timer.afterEvent]

			# calculate default values
			day = []
			weekday = 0
			for x in range(0,7):
				day.append(1)
			if (self.timer.repeated != 0): # repeated
				type = 1 # repeated
				if (self.timer.repeated == 31): # Mon-Fri
					repeated = 2 # Mon - Fri
				elif (self.timer.repeated == 127): # daily
					repeated = 0 # daily
				else:
					flags = self.timer.repeated
					repeated = 3 # user defined
					count = 0
					for x in range(0, 7):
						if (flags == 1): # weekly
							print "Set to weekday " + str(x)
							weekday = x
						if (flags & 1 == 1): # set user defined flags
							day[x] = 0
							count += 1
						else:
							day[x] = 1
						flags = flags >> 1
					if (count == 1):
						repeated = 1 # weekly
			else: # once
				type = 0
				repeated = 0
				weekday = (int(strftime("%w", time.localtime(self.timer.begin))) - 1) % 7
				day[weekday] = 0
			
			config.timerentry.justplay = configElement_nonSave("config.timerentry.justplay", configSelection, justplay, (("zap", _("zap")), ("record", _("record"))))
			config.timerentry.afterevent = configElement_nonSave("config.timerentry.afterevent", configSelection, afterevent, (("nothing", _("do nothing")), ("deepstandby", _("go to deep standby"))))
			config.timerentry.type = configElement_nonSave("config.timerentry.type", configSelection, type, (_("once"), _("repeated")))
			config.timerentry.name = configElement_nonSave("config.timerentry.name", configText, self.timer.name, (configText.extendableSize, self.keyRightCallback))
			config.timerentry.description = configElement_nonSave("config.timerentry.description", configText, self.timer.description, (configText.extendableSize, self.keyRightCallback))

			config.timerentry.repeated = configElement_nonSave("config.timerentry.repeated", configSelection, repeated, (_("daily"), _("weekly"), _("Mon-Fri"), _("user defined")))

			config.timerentry.startdate = configElement_nonSave("config.timerentry.startdate", configDateTime, self.timer.begin, (_("%d.%B %Y"), 86400))
			config.timerentry.starttime = configElement_nonSave("config.timerentry.starttime", configSequence, [int(time.strftime("%H", time.localtime(self.timer.begin))), int(time.strftime("%M", time.localtime(self.timer.begin)))], configsequencearg.get("CLOCK"))

			config.timerentry.enddate = configElement_nonSave("config.timerentry.enddate", configDateTime, self.timer.end, (_("%d.%B %Y"), 86400))
			config.timerentry.endtime = configElement_nonSave("config.timerentry.endtime", configSequence, [int(time.strftime("%H", time.localtime(self.timer.end))), int(time.strftime("%M", time.localtime(self.timer.end)))], configsequencearg.get("CLOCK"))

			config.timerentry.weekday = configElement_nonSave("config.timerentry.weekday", configSelection, weekday, (_("Monday"), _("Tuesday"), _("Wednesday"), _("Thursday"), _("Friday"), _("Saturday"), _("Sunday")))

			config.timerentry.day = []
			for x in range(0,7):
				config.timerentry.day.append(configElement_nonSave("config.timerentry.day[" + str(x) + "]", configSelection, day[x], (_("yes"), _("no"))))


			# FIXME some service-chooser needed here
			servicename = "N/A"
			try: # no current service available?
				servicename = str(self.timer.service_ref.getServiceName())
			except:
				pass
			config.timerentry.service = configElement_nonSave("config.timerentry.service", configSelection, 0, ((servicename),))
			
			config.timerentry.startdate.addNotifier(self.checkDate)
			config.timerentry.enddate.addNotifier(self.checkDate)

	def checkDate(self, configElement):
		if (configElement.getConfigPath() == "config.timerentry.startdate"):
			if (config.timerentry.enddate.value < config.timerentry.startdate.value):
				config.timerentry.enddate.value = config.timerentry.startdate.value
				config.timerentry.enddate.change()
				try:
					self["config"].invalidate(config.timerentry.enddate)
				except: # FIXME: what could go wrong here?
					pass
		if (configElement.getConfigPath() == "config.timerentry.enddate"):
			if (config.timerentry.enddate.value < config.timerentry.startdate.value):
				config.timerentry.startdate.value = config.timerentry.enddate.value
				config.timerentry.startdate.change()
				try:
					self["config"].invalidate(config.timerentry.startdate)
				except: # FIXME: what could go wrong here?
					pass

	def createSetup(self, widget):
		self.list = []
		self.list.append(getConfigListEntry(_("Name"), config.timerentry.name))
		self.list.append(getConfigListEntry(_("Description"), config.timerentry.description))
		self.timerJustplayEntry = getConfigListEntry(_("Timer Type"), config.timerentry.justplay)
		self.list.append(self.timerJustplayEntry)
		self.timerTypeEntry = getConfigListEntry(_("Repeat Type"), config.timerentry.type)
		self.list.append(self.timerTypeEntry)

		if (config.timerentry.type.value == 0): # once
			self.frequencyEntry = None
		else: # repeated
			self.frequencyEntry = getConfigListEntry(_("Frequency"), config.timerentry.repeated)
			self.list.append(self.frequencyEntry)
			if (config.timerentry.repeated.value == 0): # daily
				pass
			if (config.timerentry.repeated.value == 2): # Mon-Fri
				pass
			if (config.timerentry.repeated.value == 1): # weekly
				self.list.append(getConfigListEntry(_("Weekday"), config.timerentry.weekday))

			if (config.timerentry.repeated.value == 3): # user defined
				self.list.append(getConfigListEntry(_("Monday"), config.timerentry.day[0]))
				self.list.append(getConfigListEntry(_("Tuesday"), config.timerentry.day[1]))
				self.list.append(getConfigListEntry(_("Wednesday"), config.timerentry.day[2]))
				self.list.append(getConfigListEntry(_("Thursday"), config.timerentry.day[3]))
				self.list.append(getConfigListEntry(_("Friday"), config.timerentry.day[4]))
				self.list.append(getConfigListEntry(_("Saturday"), config.timerentry.day[5]))
				self.list.append(getConfigListEntry(_("Sunday"), config.timerentry.day[6]))

			#self.list.append(getConfigListEntry("StartDate", config.timerentry.startdate))
#		self.list.append(getConfigListEntry("Weekday", config.timerentry.weekday))

		if (config.timerentry.type.value == 0): # once
			self.list.append(getConfigListEntry(_("Start"), config.timerentry.startdate))
			self.list.append(getConfigListEntry(" ", config.timerentry.starttime))
		else:
			self.list.append(getConfigListEntry(_("StartTime"), config.timerentry.starttime))
		if (config.timerentry.type.value == 0): # once
			if currentConfigSelectionElement(config.timerentry.justplay) != "zap":
				self.list.append(getConfigListEntry(_("End"), config.timerentry.enddate))
				self.list.append(getConfigListEntry(" ", config.timerentry.endtime))
		else:
			if currentConfigSelectionElement(config.timerentry.justplay) != "zap":
				self.list.append(getConfigListEntry(_("EndTime"), config.timerentry.endtime))

		if currentConfigSelectionElement(config.timerentry.justplay) != "zap":
			self.list.append(getConfigListEntry(_("After event"), config.timerentry.afterevent))

		self.channelEntry = getConfigListEntry(_("Channel"), config.timerentry.service)
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
		if self["config"].getCurrent() == self.channelEntry:
			self.keySelect()
		else:
			self["config"].handleKey(config.key["prevElement"])
			self.newConfig()

	def keyDelete(self):
		self["config"].handleKey(config.key["delete"])
			
	def keyRightCallback(self, configPath):
		currentConfigPath = self["config"].getCurrent()[1].parent.getConfigPath()
		# check if we are still on the same config entry
		if (currentConfigPath == configPath):
			self.keyRight()

	def keyRight(self):
		if self["config"].getCurrent() == self.channelEntry:
			self.keySelect()
		else:
			self["config"].handleKey(config.key["nextElement"])
			self.newConfig()
		
	def keySelect(self):
		if self["config"].getCurrent() == self.channelEntry:
			self.session.openWithCallback(self.finishedChannelSelection, ChannelSelection.SimpleChannelSelection, _("Select channel to record from"))
		else:
			self.keyGo()

	def finishedChannelSelection(self, *args):
		if len(args):
			self.timer.service_ref = ServiceReference(args[0])
			config.timerentry.service.vals = (str(self.timer.service_ref.getServiceName()),)
			self["config"].invalidate(config.timerentry.service)

	def keyNumberGlobal(self, number):
		print "You pressed number " + str(number)
		if (self["config"].getCurrent()[1].parent.enabled == True):
			self["config"].handleKey(config.key[str(number)])

	def getTimestamp(self, date, mytime):
		d = time.localtime(date)
		dt = datetime.datetime(d.tm_year, d.tm_mon, d.tm_mday, mytime[0], mytime[1])
		return int(mktime(dt.timetuple()))

	def getBeginEnd(self):
		enddate = config.timerentry.enddate.value
		endtime = config.timerentry.endtime.value
		
		startdate = config.timerentry.startdate.value
		starttime = config.timerentry.starttime.value
		
		begin = self.getTimestamp(startdate, starttime)
		end = self.getTimestamp(enddate, endtime)
		
		# because of the dateChecks, startdate can't be < enddate.
		# however, the endtime can be less than the starttime.
		# in this case, add 1 day.
		if end < begin:
			end += 86400
		return begin, end

	def keyGo(self):
		self.timer.name = config.timerentry.name.value
		self.timer.description = config.timerentry.description.value
		self.timer.justplay = (currentConfigSelectionElement(config.timerentry.justplay) == "zap")
		self.timer.resetRepeated()
		self.timer.afterEvent = { 0: AFTEREVENT.NONE, 1: AFTEREVENT.DEEPSTANDBY, 2: AFTEREVENT.STANDBY}[config.timerentry.afterevent.value]
		
		if (config.timerentry.type.value == 0): # once
			self.timer.begin, self.timer.end = self.getBeginEnd()
		if (config.timerentry.type.value == 1): # repeated
			if (config.timerentry.repeated.value == 0): # daily
				for x in range(0,7):
					self.timer.setRepeated(x)

			if (config.timerentry.repeated.value == 1): # weekly
				self.timer.setRepeated(config.timerentry.weekday.value)
				
			if (config.timerentry.repeated.value == 2): # Mon-Fri
				for x in range(0,5):
					self.timer.setRepeated(x)
				
			if (config.timerentry.repeated.value == 3): # user defined
				for x in range(0,7):
					if (config.timerentry.day[x].value == 0): self.timer.setRepeated(x)

			self.timer.begin = self.getTimestamp(time.time(), config.timerentry.starttime.value)
			self.timer.end = self.getTimestamp(time.time(), config.timerentry.endtime.value)
			
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
		self.close((True, self.timer))

	def subserviceSelected(self, service):
		if not service is None:
			self.timer.service_ref = ServiceReference(service[1])
		self.close((True, self.timer))

	def keyCancel(self):
		self.close((False,))
		
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
		self.log_entries.remove(self["loglist"].getCurrent()[1])
		self.fillLogList()
		self["loglist"].l.setList(self.list)
		self.updateText()

	def fillLogList(self):
		self.list = [ ]
		for x in self.log_entries:
			self.list.append((str(strftime("%Y-%m-%d %H-%M", localtime(x[0])) + " - " + x[2]), x))
	
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
