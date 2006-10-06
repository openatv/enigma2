from Screen import Screen
from Components.config import *
from Components.ActionMap import ActionMap, NumberActionMap
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.Button import Button
from Components.Label import Label
from Components.Pixmap import Pixmap
import time
import datetime

class TimeDateInput(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["oktext"] = Label(_("OK"))
		self["canceltext"] = Label(_("Cancel"))
		self["ok"] = Pixmap()
		self["cancel"] = Pixmap()

		self.createConfig()

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.keySelect,
			"save": self.keyGo,
			"cancel": self.keyCancel,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.createSetup(self["config"])

	def createConfig(self):
		nowtime = time.time()
		self.timeinput_date = ConfigDateTime(default = nowtime, formatstring = (_("%d.%B %Y"), 86400))
#		self.timeinput_time = ConfigSequence(default = [int(time.strftime("%H", time.localtime(nowtime))), int(time.strftime("%M", time.localtime(nowtime)))]
		assert False, "fixme"

	def createSetup(self, configlist):
		self.list = []
		self.list.append(getConfigListEntry(_("Date"), config.timeinput.date))
		self.list.append(getConfigListEntry(_("Time"), config.timeinput.time))
		configlist.list = self.list
		configlist.l.setList(self.list)

	def keyRightCallback(self, configPath):
		currentConfigPath = self["config"].getCurrent()[1].parent.getConfigPath()
		# check if we are still on the same config entry
		if (currentConfigPath == configPath):
			self.keyRight()

	def keySelect(self):
		self.keyGo()

	def getTimestamp(self, date, mytime):
		d = time.localtime(date)
		dt = datetime.datetime(d.tm_year, d.tm_mon, d.tm_mday, mytime[0], mytime[1])
		return int(mktime(dt.timetuple()))

	def keyGo(self):
		time = self.getTimestamp(config.timeinput.date.value, config.timeinput.time.value)
		self.close((True, time))

	def keyCancel(self):
		self.close((False,))
