from Screen import Screen
from Components.config import *
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigList
from Components.NimManager import nimmanager
from Components.Label import Label
from time import *
from datetime import *
from math import log

class TimerEntry(Screen):
	def __init__(self, session, timer):
		Screen.__init__(self, session)
		self.timer = timer;

		self.createConfig()

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.keyGo,
			"cancel": self.keyCancel,
			"left": self.keyLeft,
			"right": self.keyRight,
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
			
			type = 0
			repeated = 0
			if (self.timer.repeated != 0):
				type = 1 # repeated
				if (self.timer.repeated == 31): # Mon-Fri
					repeated = 2 # Mon - Fri
				elif (self.timer.repeated == 127): # daily
					repeated = 0 # daily
				else:
					repeated = 3 # user-defined

			config.timerentry.type = configElement_nonSave("config.timerentry.type", configSelection, type, ("once", "repeated"))
			config.timerentry.description = configElement_nonSave("config.timerentry.description", configText, self.timer.description, (configText.extendableSize, self.keyRightCallback))

			config.timerentry.repeated = configElement_nonSave("config.timerentry.repeated", configSelection, repeated, ("daily", "weekly", "Mon-Fri", "user-defined"))

			config.timerentry.startdate = configElement_nonSave("config.timerentry.startdate", configDateTime, self.timer.begin, ("%d.%B %Y", 86400))
			config.timerentry.starttime = configElement_nonSave("config.timerentry.starttime", configSequence, [int(strftime("%H", localtime(self.timer.begin))), int(strftime("%M", localtime(self.timer.begin)))], configsequencearg.get("CLOCK"))

			config.timerentry.enddate = configElement_nonSave("config.timerentry.enddate", configDateTime, self.timer.end, ("%d.%B %Y", 86400))
			config.timerentry.endtime = configElement_nonSave("config.timerentry.endtime", configSequence, [int(strftime("%H", localtime(self.timer.end))), int(strftime("%M", localtime(self.timer.end)))], configsequencearg.get("CLOCK"))

			config.timerentry.weekday = configElement_nonSave("config.timerentry.weekday", configSelection, 0, ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"))

			config.timerentry.monday = configElement_nonSave("config.timerentry.monday", configSelection, 0, ("yes", "no"))
			config.timerentry.tuesday = configElement_nonSave("config.timerentry.tuesday", configSelection, 0, ("yes", "no"))
			config.timerentry.wednesday = configElement_nonSave("config.timerentry.wednesday", configSelection, 0, ("yes", "no"))
			config.timerentry.thursday = configElement_nonSave("config.timerentry.thursday", configSelection, 0, ("yes", "no"))
			config.timerentry.friday = configElement_nonSave("config.timerentry.friday", configSelection, 0, ("yes", "no"))
			config.timerentry.saturday = configElement_nonSave("config.timerentry.saturday", configSelection, 0, ("yes", "no"))
			config.timerentry.sunday = configElement_nonSave("config.timerentry.sunday", configSelection, 0, ("yes", "no"))

			# FIXME some service-chooser needed here
			config.timerentry.service = configElement_nonSave("config.timerentry.service", configSelection, 0, ((str(self.timer.service_ref.getServiceName())),))
			
			config.timerentry.startdate.addNotifier(self.checkDate)
			config.timerentry.enddate.addNotifier(self.checkDate)

	def checkDate(self, configElement):
		if (configElement.getConfigPath() == "config.timerentry.startdate"):
			if (config.timerentry.enddate.value < config.timerentry.startdate.value):
				config.timerentry.enddate.value = config.timerentry.startdate.value
				config.timerentry.enddate.change()
				self["config"].invalidate(config.timerentry.enddate)
		if (configElement.getConfigPath() == "config.timerentry.enddate"):
			if (config.timerentry.enddate.value < config.timerentry.startdate.value):
				config.timerentry.startdate.value = config.timerentry.enddate.value
				config.timerentry.startdate.change()
				self["config"].invalidate(config.timerentry.startdate)

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry("Description", config.timerentry.description))
		self.list.append(getConfigListEntry("TimerType", config.timerentry.type))

		if (config.timerentry.type.value == 0): # once
			pass
		else: # repeated
			self.list.append(getConfigListEntry("Frequency", config.timerentry.repeated))
			if (config.timerentry.repeated.value == 0): # daily
				pass
			if (config.timerentry.repeated.value == 2): # Mon-Fri
				pass
			if (config.timerentry.repeated.value == 1): # weekly
				self.list.append(getConfigListEntry("Weekday", config.timerentry.weekday))

			if (config.timerentry.repeated.value == 3): # user-defined
				self.list.append(getConfigListEntry("Monday", config.timerentry.monday))
				self.list.append(getConfigListEntry("Tuesday", config.timerentry.tuesday))
				self.list.append(getConfigListEntry("Wednesday", config.timerentry.wednesday))
				self.list.append(getConfigListEntry("Thursday", config.timerentry.thursday))
				self.list.append(getConfigListEntry("Friday", config.timerentry.friday))
				self.list.append(getConfigListEntry("Saturday", config.timerentry.saturday))
				self.list.append(getConfigListEntry("Sunday", config.timerentry.sunday))

			#self.list.append(getConfigListEntry("StartDate", config.timerentry.startdate))
#		self.list.append(getConfigListEntry("Weekday", config.timerentry.weekday))

		if (config.timerentry.type.value == 0): # once
			self.list.append(getConfigListEntry("StartDate", config.timerentry.startdate))
		self.list.append(getConfigListEntry("StartTime", config.timerentry.starttime))
		if (config.timerentry.type.value == 0): # once
			self.list.append(getConfigListEntry("EndDate", config.timerentry.enddate))
		self.list.append(getConfigListEntry("EndTime", config.timerentry.endtime))

		self.list.append(getConfigListEntry("Channel", config.timerentry.service))

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def newConfig(self):
		print self["config"].getCurrent()
		if self["config"].getCurrent()[0] == "TimerType":
			self.createSetup()
		if self["config"].getCurrent()[0] == "Frequency":
			self.createSetup()

	def keyLeft(self):
		self["config"].handleKey(config.key["prevElement"])
		self.newConfig()

	def keyRightCallback(self, configPath):
		currentConfigPath = self["config"].getCurrent()[1].parent.getConfigPath()
		# check if we are still on the same config entry
		if (currentConfigPath == configPath):
			self.keyRight()

	def keyRight(self):
		self["config"].handleKey(config.key["nextElement"])
		self.newConfig()

	def keyNumberGlobal(self, number):
		print "You pressed number " + str(number)
		if (self["config"].getCurrent()[1].parent.enabled == True):
			self["config"].handleKey(config.key[str(number)])

	def getTimestamp(self, date, time):
		d = localtime(date) # for gettin indexes 0(year), 1(month) and 2(day)
		dt = datetime(d.tm_year, d.tm_mon, d.tm_mday, time[0], time[1])
		print dt
		return int(mktime(dt.timetuple()))

	def keyGo(self):
		if (config.timerentry.type.value == 0): # once
			self.timer.begin = self.getTimestamp(config.timerentry.startdate.value, config.timerentry.starttime.value)
			self.timer.end = self.getTimestamp(config.timerentry.enddate.value, config.timerentry.endtime.value)
		if (config.timerentry.type.value == 1): # repeated
			if (config.timerentry.repeated.value == 0): # daily
				self.timer.setRepeated(0) # Mon
				self.timer.setRepeated(1) # Tue
				self.timer.setRepeated(2) # Wed
				self.timer.setRepeated(3) # Thu
				self.timer.setRepeated(4) # Fri
				self.timer.setRepeated(5) # Sat
				self.timer.setRepeated(6) # Sun

			if (config.timerentry.repeated.value == 1): # weekly
				self.timer.setRepeated(config.timerentry.weekday.value)
				
			if (config.timerentry.repeated.value == 2): # Mon-Fri
				self.timer.setRepeated(0) # Mon
				self.timer.setRepeated(1) # Tue
				self.timer.setRepeated(2) # Wed
				self.timer.setRepeated(3) # Thu
				self.timer.setRepeated(4) # Fri
				
			if (config.timerentry.repeated.value == 3): # user-defined
				if (config.timerentry.monday.value == 0): self.timer.setRepeated(0)
				if (config.timerentry.tuesday.value == 0): self.timer.setRepeated(1)
				if (config.timerentry.wednesday.value == 0): self.timer.setRepeated(2)
				if (config.timerentry.thursday.value == 0): self.timer.setRepeated(3)
				if (config.timerentry.friday.value == 0): self.timer.setRepeated(4)
				if (config.timerentry.saturday.value == 0): self.timer.setRepeated(5)
				if (config.timerentry.sunday.value == 0): self.timer.setRepeated(6)
				

		self.close((True, self.timer))

	def keyCancel(self):
		self.close((False,))
