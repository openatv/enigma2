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
			print("[NetworkTime] Error %d: Unable to synchronize the time!\n%s" % (retVal, data.strip()))
		nowTime = time()
		if nowTime > 10000:
			timeSource = config.misc.SyncTimeUsing.value
			print("[NetworkTime] Setting time to '%s' (%s) from '%s'." % (ctime(nowTime), str(nowTime), config.misc.SyncTimeUsing.toDisplayString(timeSource)))
			setRTCtime(nowTime)
			eDVBLocalTimeHandler.getInstance().setUseDVBTime(timeSource == "0")
			eEPGCache.getInstance().timeUpdated()
			self.timer.startLongTimer(config.misc.useNTPminutes.value * 60)
		else:
			print("[NetworkTime] System time not yet available.")
			self.timer.startLongTimer(10)


ntpSyncPoller = NTPSyncPoller()
