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

	def syncTimeUsingChanged(self, configElement):
		print("[NetworkTime] Time reference changed to '%s'." % configElement.toDisplayString(configElement.value))
		eDVBLocalTimeHandler.getInstance().setUseDVBTime(configElement.value == "0")
		eEPGCache.getInstance().timeUpdated()
		self.timer.startLongTimer(0)

	def ntpServerChanged(self, configElement):
		print("[NetworkTime] Time server changed to '%s'." % configElement.value)
		self.timeCheck()

	def useNTPminutesChanged(self, configElement):
		print("[NetworkTime] Time sync period changed to '%s'." % configElement.toDisplayString(configElement.value))
		self.timeCheck()

	def startTimer(self):
		if self.timeCheck not in self.timer.callback:
			self.timer.callback.append(self.timeCheck)
			config.misc.SyncTimeUsing.addNotifier(self.syncTimeUsingChanged, initial_call=False, immediate_feedback=False)
			config.misc.NTPserver.addNotifier(self.ntpServerChanged, initial_call=False, immediate_feedback=False)
			config.misc.useNTPminutes.addNotifier(self.useNTPminutesChanged, initial_call=False, immediate_feedback=False)
		self.timer.startLongTimer(0)

	def stopTimer(self):
		if self.timeCheck in self.timer.callback:
			self.timer.callback.remove(self.timeCheck)
		self.timer.stop()

	def timeCheck(self):
		if config.misc.SyncTimeUsing.value == "1":
			print("[NetworkTime] Updating time via NTP.")
			self.Console.ePopen(["/usr/sbin/ntpd", "/usr/sbin/ntpd", "-nq", "-p", config.misc.NTPserver.value], self.updateSchedule)
		else:
			self.updateSchedule()

	def updateSchedule(self, data=None, retVal=None, extraArgs=None):
		if retVal and data:
			print("[NetworkTime] Error %d: /usr/sbin/ntpd was unable to synchronize the time!\n%s" % (retVal, data.strip()))
		nowTime = time()
		if nowTime > 10000:
			print("[NetworkTime] Setting time to '%s' (%s)." % (ctime(nowTime), str(nowTime)))
			setRTCtime(nowTime)
			eDVBLocalTimeHandler.getInstance().setUseDVBTime(config.misc.SyncTimeUsing.value == "0")
			eEPGCache.getInstance().timeUpdated()
			self.timer.startLongTimer(int(config.misc.useNTPminutes.value) * 60)
		else:
			print("[NetworkTime] System time not yet available.")
			self.timer.startLongTimer(10)


ntpSyncPoller = NTPSyncPoller()
