from time import time

from Components.ActionMap import HelpableActionMap
from Components.config import ConfigDateTime, config
from Screens.Setup import Setup


class DateTime(Setup):
	def __init__(self, session, setupSection, default, smallStep=60):
		self.dateTime = ConfigDateTime(default, f"{config.usage.date.daylong.value}  {config.usage.time.short.value}", increment=smallStep)
		Setup.__init__(self, session, setupSection)
		self.skinName.insert(0, "SetupDateTime")
		self["prevNextActions"] = HelpableActionMap(self, ["PreviousNextActions"], {  # This is for users who do not use PREV/NEXT as first/last.
			"previous": (self.keyFirst, _("Jump back one hour") if self.bigStep == 3600 else _("Jump back one day")),
			"next": (self.keyLast, _("Jump forward one hour") if self.bigStep == 3600 else _("Jump forward one day"))
		}, prio=0, description=_("Date Time Input Actions"))

	def changedEntry(self):  # This overrides the same class in Setup.py.
		current = self["config"].getCurrent()
		if current and current[1] == self.dateTime:
			if self.dateTime.value < self.minLimit:
				self.dateTime.value = self.minLimit
			elif self.dateTime.value > self.maxLimit:
				self.dateTime.value = self.maxLimit
			self["config"].invalidateCurrent()
		Setup.changedEntry(self)

	def keyFirst(self):  # This overrides the same class in ConfigList.py as part of Setup.py.
		current = self["config"].getCurrent()
		if current and current[1] == self.dateTime:
			self.dateTime.value -= self.bigStep
			if self.dateTime.value < self.minLimit:
				self.dateTime.value = self.minLimit
			self["config"].invalidateCurrent()

	def keyLast(self):  # This overrides the same class in ConfigList.py as part of Setup.py.
		current = self["config"].getCurrent()
		if current and current[1] == self.dateTime:
			self.dateTime.value += self.bigStep
			if self.dateTime.value > self.maxLimit:
				self.dateTime.value = self.maxLimit
			self["config"].invalidateCurrent()

	def keySave(self):  # This overrides the same class in ConfigList.py as part of Setup.py.
		self.close((True, self.dateTime.value))

	def keyCancel(self):  # This overrides the same class in ConfigList.py as part of Setup.py.
		self.close((False,))

	def closeRecursive(self):  # This overrides the same class in ConfigList.py as part of Setup.py.
		self.close((True,))


class EPGJumpTime(DateTime):
	def __init__(self, session, configElement, historyBuffer):
		self.minLimit = int(time()) - (historyBuffer * 60)  # Now - EPG history buffer length.
		self.maxLimit = int(time()) + 2419200  # Now + 4 weeks.
		self.smallStep = 3600  # 1 Hour.
		self.bigStep = 86400  # 1 Day.
		DateTime.__init__(self, session, "EPGJumpTime", default=int(time()), smallStep=self.smallStep)
		self.setTitle(_("EPG Jump"))
		self["key_green"].setText(_("Jump"))

	def createSetup(self):  # This overrides the same class in Setup.py.
		configList = [
			(_("Jump time"), self.dateTime, _("Select the time to which the EPG should be positioned. Press LEFT/RIGHT to decrease/increase the time by an hour. Press PREV/NEXT to decrease/increase the time by a day."))
		]
		self["config"].setList(configList)


class InstantRecordingEndTime(DateTime):
	def __init__(self, session, endTime):
		self.minLimit = int(time()) + 60  # Now + 1 minute.
		self.maxLimit = int(time()) + 86400  # Now + 1 day.
		self.smallStep = 60  # 1 Minute.
		self.bigStep = 3600  # 1 Hour.
		DateTime.__init__(self, session, "InstantRecordingEndTime", default=endTime, smallStep=self.smallStep)
		self.setTitle(_("Instant Recording End Time"))
		self["key_green"].setText(_("Set Time"))

	def createSetup(self):  # This overrides the same class in Setup.py.
		configList = [
			(_("End time"), self.dateTime, _("Select the time when this instant recording timer should end. Press LEFT/RIGHT to decrease/increase the time by a minute. Press PREV/NEXT to decrease/increase the time by an hour."))
		]
		self["config"].setList(configList)
