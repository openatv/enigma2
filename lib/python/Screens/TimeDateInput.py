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
		self.timeinput_date = ConfigDateTime(default = nowtime, formatstring = _("%d.%B %Y"), increment = 86400)
		self.timeinput_time = ConfigClock(default = nowtime)

	def createSetup(self, configlist):
		self.list = []
		self.list.append(getConfigListEntry(_("Date"), self.timeinput_date))
		self.list.append(getConfigListEntry(_("Time"), self.timeinput_time))
		configlist.list = self.list
		configlist.l.setList(self.list)

	def keySelect(self):
		self.keyGo()

	def getTimestamp(self, date, mytime):
		d = time.localtime(date)
		dt = datetime.datetime(d.tm_year, d.tm_mon, d.tm_mday, mytime[0], mytime[1])
		return int(time.mktime(dt.timetuple()))

	def keyGo(self):
		time = self.getTimestamp(self.timeinput_date.value, self.timeinput_time.value)
		self.close((True, time))

	def keyCancel(self):
		self.close((False,))
