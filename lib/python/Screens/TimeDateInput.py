from Screen import Screen
from Components.config import ConfigClock, ConfigDateTime, ClockTime, getConfigListEntry, KEY_PAGEUP, KEY_PAGEDOWN, KEY_LEFT, KEY_RIGHT, KEY_PREV, KEY_NEXT

from Components.ActionMap import ActionMap, NumberActionMap
from Components.ConfigList import ConfigListScreen
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.Sources.StaticText import StaticText
import time
import datetime

class TimeDateInputBase(ConfigListScreen, Screen):
	TIME_MASK = 1
	DATE_MASK = 2

	def __init__(self, session):
		Screen.__init__(self, session)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()

		self.timeinput_time = None
		self.timeinput_date = None
		self.save_mask = 0

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.keySelect,
			"save": self.keyGo,
			"cancel": self.keyCancel,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list)

	def keySelect(self):
		self.keyGo()

	def keyGo(self):
		time = self.getTimestamp(self.timeinput_date.value, self.timeinput_time.value)
		if self.save_mask & self.TIME_MASK:
			self.timeinput_time.save()
		if self.save_mask & self.DATE_MASK:
			self.timeinput_date.save()
		self.close((True, time))

	def keyCancel(self):
		if self.save_mask & self.TIME_MASK:
			self.timeinput_time.cancel()
		if self.save_mask & self.DATE_MASK:
			self.timeinput_date.cancel()
		self.close((False,))

	# Change the setup summary title if setTitle is changed on the screen

	def setTitle(self, title):
		Screen.setTitle(self, title)
		if hasattr(self, "setup_title"):
			self.setup_title = title
		if hasattr(self, "summaries"):
			for summary in self.summaries:
				if "SetupTitle" in summary:
					summary["SetupTitle"].text = title

class TimeDateInput(TimeDateInputBase):
	def __init__(self, session, config_time=None, config_date=None):
		super(TimeDateInput, self).__init__(session)

		self.createConfig(config_date, config_time)

		self.createSetup(self["config"])

	def createConfig(self, conf_date, conf_time):
		self.save_mask = 0
		if conf_time:
			self.save_mask |= self.TIME_MASK
		else:
			conf_time = ConfigClock(default = time.time())
		if conf_date:
			self.save_mask |= self.DATE_MASK
		else:
			conf_date = ConfigDateTime(default = time.time(), formatstring = _("%A %d %B %Y"), increment = 86400)
		self.timeinput_date = conf_date
		self.timeinput_time = conf_time

	def createSetup(self, configlist):
		self.list = [
			getConfigListEntry(_("Date"), self.timeinput_date),
			getConfigListEntry(_("Time"), self.timeinput_time)
		]
		configlist.list = self.list
		configlist.l.setList(self.list)

	def getTimestamp(self, date, mytime):
		d = time.localtime(date)
		dt = datetime.datetime(d.tm_year, d.tm_mon, d.tm_mday, mytime[0], mytime[1])
		return int(time.mktime(dt.timetuple()))

class TimeDateDurationInput(TimeDateInputBase):
	DURATION_MASK = 4

	def __init__(self, session, config_time=None, config_date=None, config_duration=None, desc_time=None, desc_date=None, desc_duration=None, show_entries=None, skin_name=None):
		if not skin_name:
			skin_name = []

		if show_entries is None:
			show_entries = self.TIME_MASK | self.DATE_MASK | self.DURATION_MASK
		assert show_entries != 0, "TimeDateDurationInput must have at least one input field"

		self.desc_time = desc_time
		self.desc_date = desc_date
		self.desc_duration = desc_duration

		self.show_entries = show_entries

		super(TimeDateDurationInput, self).__init__(session)

		if isinstance(self.skinName, str):
			self.skinName = [self.skinName]
		self.skinName.append("TimeDateInput")

		if isinstance(skin_name, str):
			skin_name = [skin_name]
		if skin_name:
			self.skinName = skin_name + self.skinName

		self["description"] = Label()

		self.createConfig(config_date, config_time, config_duration)
		self.createSetup(self["config"])

		# Disabled until consensus can be reached about which
		# buttons to use

		# self["increment1"] = ActionMap(["TimeDateDurationInput"], {
		# 	"volumeDown": self.keyPrev,
		# 	"volumeUp": self.keyNext,
		# 	"rewind": self.keyPrev,
		# 	"fastforward": self.keyNext,
		# 	"previous": self.keyPrev,
		# 	"next": self.keyNext,
		# }, -2)

	def createConfig(self, conf_date, conf_time, conf_duration):
		self.save_mask = 0
		if self.show_entries & self.TIME_MASK:
			if conf_time:
				self.save_mask |= self.TIME_MASK
			else:
				conf_time = ConfigDateTime(default=time.time(), formatstring=_("%H:%M"), increment=60 * 60, increment1=60)
		else:
			conf_time = None
		if self.show_entries & self.DATE_MASK:
			if conf_date:
				self.save_mask |= self.DATE_MASK
			else:
				conf_date = ConfigDateTime(default = time.time(), formatstring = _("%A %d %B %Y"), increment = 86400)
		else:
			conf_date = None
		if self.show_entries & self.DURATION_MASK:
			if conf_duration:
				self.save_mask |= self.DURATION_MASK
			else:
				conf_duration = ConfigDuration(default=time.time(), formatstring=_("%j days %H:%M"), increment=24 * 60 * 60)
		else:
			conf_duration = None
		self.timeinput_time = conf_time
		self.timeinput_date = conf_date
		self.timeinput_duration = conf_duration

	def createSetup(self, configlist):
		self.list = [
			getConfigListEntry(_("Date"), self.timeinput_date, self.desc_date),
			getConfigListEntry(_("Time"), self.timeinput_time, self.desc_time),
			getConfigListEntry(_("Duration"), self.timeinput_duration, self.desc_duration),
		]
		self.timeinput_time.select_callback = self._timeSelectCallback
		for entry in self.list:
			entry[1].addNotifier(self.timeUpdate)
		configlist.list = self.list
		configlist.l.setList(self.list)

	def _timeSelectCallback(self, conf, selected):
		for entry in self.list:
			c = entry[1]
			c.allow_invalid = selected

	def timeUpdate(self, conf):
		for entry in self.list:
			c = entry[1]
			if c is not conf and c.value != conf.value:
				c.value = conf.value
				self["config"].invalidate(entry)

	def getTimestamp(self, date, mytime):
		return self.list[0][1]

	def keyGo(self):
		if self.save_mask & self.DURATION_MASK:
			self.timeinput_duration.save()
		super(TimeDateDurationInput, self).keyGo()

	def keyCancel(self):
		if self.save_mask & self.DURATION_MASK:
			self.timeinput_duration.cancel()
		super(TimeDateDurationInput, self).keyCancel()

	# Disabled until consensus can be reached about which
	# buttons to use

	# def keyPrev(self):
	# 	self["config"].handleKey(KEY_PREV)

	# def keyNext(self):
	# 	self["config"].handleKey(KEY_NEXT)

	# def keyPageDown(self):
	# 	self["config"].handleKey(KEY_PAGEDOWN)

	# def keyPageUp(self):
	# 	self["config"].handleKey(KEY_PAGEUP)
