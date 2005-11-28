from Screen import Screen
import ChannelSelection
from ServiceReference import ServiceReference
from Components.config import *
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigList
from Components.NimManager import nimmanager
from Components.Label import Label
import time
import datetime

class TimerEntry(Screen):
	def __init__(self, session, timer):
		Screen.__init__(self, session)
		self.timer = timer;
		
		self["ok"] = Label("OK")
		self["cancel"] = Label("Cancel")

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
		self.createSetup()

	def createConfig(self):
			config.timerentry = ConfigSubsection()
			
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
					repeated = 3 # user-defined
					count = 0
					for x in range(0, 7):
						if (flags == 1): # weekly
							print "Set to weekday " + str(x)
							weekday = x
						if (flags & 1 == 1): # set user-defined flags
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
			
			config.timerentry.type = configElement_nonSave("config.timerentry.type", configSelection, type, (_("once"), _("repeated")))
			config.timerentry.description = configElement_nonSave("config.timerentry.description", configText, self.timer.description, (configText.extendableSize, self.keyRightCallback))

			config.timerentry.repeated = configElement_nonSave("config.timerentry.repeated", configSelection, repeated, (_("daily"), _("weekly"), _("Mon-Fri"), _("user-defined")))

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
				except:
					pass
		if (configElement.getConfigPath() == "config.timerentry.enddate"):
			if (config.timerentry.enddate.value < config.timerentry.startdate.value):
				config.timerentry.startdate.value = config.timerentry.enddate.value
				config.timerentry.startdate.change()
				try:
					self["config"].invalidate(config.timerentry.startdate)
				except:
					pass

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Description"), config.timerentry.description))
		self.list.append(getConfigListEntry(_("TimerType"), config.timerentry.type))

		if (config.timerentry.type.value == 0): # once
			pass
		else: # repeated
			self.list.append(getConfigListEntry(_("Frequency"), config.timerentry.repeated))
			if (config.timerentry.repeated.value == 0): # daily
				pass
			if (config.timerentry.repeated.value == 2): # Mon-Fri
				pass
			if (config.timerentry.repeated.value == 1): # weekly
				self.list.append(getConfigListEntry(_("Weekday"), config.timerentry.weekday))

			if (config.timerentry.repeated.value == 3): # user-defined
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
			self.list.append(getConfigListEntry("", config.timerentry.starttime))
		else:
			self.list.append(getConfigListEntry(_("StartTime"), config.timerentry.starttime))
		if (config.timerentry.type.value == 0): # once
			self.list.append(getConfigListEntry(_("End"), config.timerentry.enddate))
			self.list.append(getConfigListEntry("", config.timerentry.endtime))
		else:
			self.list.append(getConfigListEntry(_("EndTime"), config.timerentry.endtime))

		self.list.append(getConfigListEntry(_("Channel"), config.timerentry.service))

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def newConfig(self):
		print self["config"].getCurrent()
		if self["config"].getCurrent()[0] == _("TimerType"):
			self.createSetup()
		if self["config"].getCurrent()[0] == _("Frequency"):
			self.createSetup()

	def keyLeft(self):
		if self["config"].getCurrent()[0] == _("Channel"):
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
		if self["config"].getCurrent()[0] == _("Channel"):
			self.keySelect()
		else:
			self["config"].handleKey(config.key["nextElement"])
			self.newConfig()
		
	def keySelect(self):
		if self["config"].getCurrent()[0] == _("Channel"):
			self.session.openWithCallback(self.finishedChannelSelection, ChannelSelection.SimpleChannelSelection, _("Select channel to record from"))

	def finishedChannelSelection(self, args):
		self.timer.service_ref = ServiceReference(args)
		config.timerentry.service.vals = (str(self.timer.service_ref.getServiceName()),)
		self["config"].invalidate(config.timerentry.service)

	def keyNumberGlobal(self, number):
		print "You pressed number " + str(number)
		if (self["config"].getCurrent()[1].parent.enabled == True):
			self["config"].handleKey(config.key[str(number)])

	def getTimestamp(self, date, mytime):
		d = time.localtime(date)
		dt = datetime.datetime(d.tm_year, d.tm_mon, d.tm_mday, mytime[0], mytime[1])
		print dt
		return int(mktime(dt.timetuple()))

	def keyGo(self):
		self.timer.resetRepeated()
		
		if (config.timerentry.type.value == 0): # once
			self.timer.begin = self.getTimestamp(config.timerentry.startdate.value, config.timerentry.starttime.value)
			self.timer.end = self.getTimestamp(config.timerentry.enddate.value, config.timerentry.endtime.value)
		if (config.timerentry.type.value == 1): # repeated
			if (config.timerentry.repeated.value == 0): # daily
				for x in range(0,7):
					self.timer.setRepeated(x)

			if (config.timerentry.repeated.value == 1): # weekly
				self.timer.setRepeated(config.timerentry.weekday.value)
				
			if (config.timerentry.repeated.value == 2): # Mon-Fri
				for x in range(0,5):
					self.timer.setRepeated(x)
				
			if (config.timerentry.repeated.value == 3): # user-defined
				for x in range(0,7):
					if (config.timerentry.day[x].value == 0): self.timer.setRepeated(x)

			self.timer.begin = self.getTimestamp(time.time(), config.timerentry.starttime.value)
			self.timer.end = self.getTimestamp(time.time(), config.timerentry.endtime.value)				

		self.close((True, self.timer))

	def keyCancel(self):
		self.close((False,))
