from Components.Console import Console
from config import config
from enigma import eTimer, eDVBLocalTimeHandler, eEPGCache
from Tools.StbHardware import setRTCtime
from time import time, ctime

# _session = None
#
def AutoNTPSync(session=None, **kwargs):
	global ntpsyncpoller
	ntpsyncpoller = NTPSyncPoller()
	ntpsyncpoller.start()

class NTPSyncPoller:
	"""Automatically Poll NTP"""
	def __init__(self):
		# Init Timer
		self.timer = eTimer()
		self.Console = Console()

	def start(self):
		if self.timecheck not in self.timer.callback:
			self.timer.callback.append(self.timecheck)
		self.timer.startLongTimer(0)

	def stop(self):
		if self.timecheck in self.timer.callback:
			self.timer.callback.remove(self.timecheck)
		self.timer.stop()

	def timecheck(self):
		if config.misc.SyncTimeUsing.value == "1":
			print '[NTP]: Updating'
			self.Console.ePopen('/usr/bin/ntpdate-sync', self.update_schedule)
		else:
			self.update_schedule()

	def update_schedule(self, result = None, retval = None, extra_args = None):
		nowTime = time()
		nowTimereal = ctime(nowTime)
		if nowTime > 10000:
			print '[NTP]: setting E2 unixtime:',nowTime
			print '[NTP]: setting E2 realtime:',nowTimereal
			setRTCtime(nowTime)
			if config.misc.SyncTimeUsing.value == "1":
				eDVBLocalTimeHandler.getInstance().setUseDVBTime(False)
			else:
				eDVBLocalTimeHandler.getInstance().setUseDVBTime(True)
			eEPGCache.getInstance().timeUpdated()
			self.timer.startLongTimer(int(config.misc.useNTPminutes.value) * 60)
		else:
			print 'NO TIME SET'
			self.timer.startLongTimer(10)
