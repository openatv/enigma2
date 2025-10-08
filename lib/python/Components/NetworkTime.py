from time import ctime, time

from enigma import eTimer, eDVBLocalTimeHandler, eEPGCache

from Components.config import config
from Components.Console import Console
from Tools.StbHardware import setRTCtime


class NTPSyncPoller:
	"""Automatically Poll NTP"""

	def __init__(self):
		self.timer = eTimer()
		self.Console = Console()
		self.onTimeUpdated = []
		self.previousTime = time()

	def startTimer(self):
		if self.timeCheck not in self.timer.callback:
			self.timer.callback.append(self.timeCheck)
		self.timer.startLongTimer(0)

	def stopTimer(self):
		if self.timeCheck in self.timer.callback:
			self.timer.callback.remove(self.timeCheck)
		self.timer.stop()

	def timeCheck(self):
		if config.misc.SyncTimeUsing.value == "1":
			self.Console.ePopen(["/usr/sbin/ntpd", "/usr/sbin/ntpd", "-nq", "-p", config.misc.NTPserver.value], self.updateSchedule)
		else:
			self.updateSchedule()

	def updateSchedule(self, data=None, retVal=None, extraArgs=None):
		if retVal and data:
			print(f"[NetworkTime] Error {retVal}: Unable to synchronize the time!\n{data.strip()}")
		nowTime = time()
		if nowTime > 10000:
			timeSource = config.misc.SyncTimeUsing.value
			print(f"[NetworkTime] Setting time to '{ctime(nowTime)}' ({str(nowTime)}) from '{config.misc.SyncTimeUsing.toDisplayString(timeSource)}'.")
			setRTCtime(nowTime)
			eDVBLocalTimeHandler.getInstance().setUseDVBTime(timeSource == "0")
			eEPGCache.getInstance().timeUpdated()
			self.timer.startLongTimer(config.misc.useNTPminutes.value * 60)
			if abs(time() - self.previousTime) > 60:
				for func in self.onTimeUpdated:
					if callable(func):
						func()
		else:
			print("[NetworkTime] System time not yet available.")
			self.timer.startLongTimer(10)

	def addTimeUpdatedCallback(self, func):
		if func not in self.onTimeUpdated:
			self.onTimeUpdated.append(func)

	def removeTimeUpdatedCallback(self, func):
		if func in self.onTimeUpdated:
			self.onTimeUpdated.remove(func)


ntpSyncPoller = NTPSyncPoller()
ntpsyncpoller = ntpSyncPoller  # This is used by some plugins like ABM
