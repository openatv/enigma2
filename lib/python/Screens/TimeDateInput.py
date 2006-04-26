from Screen import Screen
from Components.config import *
from Components.ActionMap import ActionMap, NumberActionMap
from Components.ConfigList import ConfigList
from Components.Button import Button
from Components.Label import Label
from Components.Pixmap import Pixmap
import time
import datetime

class TimeDateInput(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

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
		self.createSetup(self["config"])

	def createConfig(self):
			config.timeinput = ConfigSubsection()
			nowtime = time.time()
			config.timeinput.date = configElement_nonSave("config.timeinput.date", configDateTime, nowtime, (_("%d.%B %Y"), 86400))
			config.timeinput.time = configElement_nonSave("config.timeinput.time", configSequence, [int(time.strftime("%H", time.localtime(nowtime))), int(time.strftime("%M", time.localtime(nowtime)))], configsequencearg.get("CLOCK"))

	def createSetup(self, configlist):
		self.list = []
		self.list.append(getConfigListEntry(_("Date"), config.timeinput.date))
		self.list.append(getConfigListEntry(_("Time"), config.timeinput.time))
		configlist.list = self.list
		configlist.l.setList(self.list)

	def keyLeft(self):
		self["config"].handleKey(config.key["prevElement"])

	def keyDelete(self):
		self["config"].handleKey(config.key["delete"])

	def keyRightCallback(self, configPath):
		currentConfigPath = self["config"].getCurrent()[1].parent.getConfigPath()
		# check if we are still on the same config entry
		if (currentConfigPath == configPath):
			self.keyRight()

	def keyRight(self):
		self["config"].handleKey(config.key["nextElement"])

	def keySelect(self):
		self.keyGo()

	def keyNumberGlobal(self, number):
		print "You pressed number " + str(number)
		if (self["config"].getCurrent()[1].parent.enabled == True):
			self["config"].handleKey(config.key[str(number)])

	def getTimestamp(self, date, mytime):
		d = time.localtime(date)
		dt = datetime.datetime(d.tm_year, d.tm_mon, d.tm_mday, mytime[0], mytime[1])
		return int(mktime(dt.timetuple()))

	def keyGo(self):
		time = self.getTimestamp(config.timeinput.date.value, config.timeinput.time.value)
		self.close((True, time))

	def keyCancel(self):
		self.close((False,))
