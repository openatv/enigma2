from Components.config import config, ConfigClock, ConfigDateTime
from datetime import datetime
from Screens.Setup import Setup
from time import localtime, mktime, time

class TimeDateInput(Setup):
	def __init__(self, session, configTime=None, default=0):
		self.configTime = configTime
		self.default = default
		self.createConfig()
		Setup.__init__(self, session, "TimeDateInput")
		self["key_green"].setText(_("OK"))

	def createConfig(self):
		if self.configTime:
			if isinstance(self.configTime, ConfigClock):
				self.timeInputTime = self.configTime
			else:  # New init with timestamp same as return
				self.timeInputTime = ConfigClock(self.configTime)
				self.configTime = None
		else:  # Now
			self.timeInputTime = ConfigClock(time())

		t = mktime(self.timeInputTime.time)
		self.timeInputDate = ConfigDateTime(default=t, formatstring=config.usage.date.full.value, increment=86400)

	def keyPageDown(self):
		sel = self["config"].getCurrent()
		if sel and sel[1] == self.timeInputTime:
			self.timeInputTime.decrement()
			self["config"].invalidateCurrent()

	def keyPageUp(self):
		sel = self["config"].getCurrent()
		if sel and sel[1] == self.timeInputTime:
			self.timeInputTime.increment()
			self["config"].invalidateCurrent()

	def keyCancel(self):
		# if self.configTime:
			# if self.default:
				# self.configTime = ConfigClock(self.default)
			# self.configTime.cancel()

		if self.default:
			self.close((False, self.default))
		else:
			self.close((False,))

	def keySave(self, result=None):
		# if self.configTime:
			# self.configTime = ConfigClock(self.getTimestamp())
			# self.configTime.save()
		self.close((True, self.getTimestamp()))

	def formatItemDescription(self, item, itemDescription):
		return itemDescription

	def getTimestamp(self):
		return self.getTimeStamp(self.timeInputDate.value, self.timeInputTime.value)

	def getTimeStamp(self, date, time):  # Note: The "date" can be a float() or an int() while "time" is a two item list.
		localDate = localtime(date)
		return int(mktime(datetime(localDate.tm_year, localDate.tm_mon, localDate.tm_mday, time[0], time[1]).timetuple()))
