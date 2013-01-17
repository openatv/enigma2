from Components.Console import Console
from config import config
from enigma import eTimer, eDVBLocalTimeHandler
from Tools.StbHardware import setRTCtime
from time import time

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
		if self.ntp_sync not in self.timer.callback:
			self.timer.callback.append(self.ntp_sync)
		self.timer.startLongTimer(0)

	def stop(self):
		if self.version_check in self.timer.callback:
			self.timer.callback.remove(self.ntp_sync)
		self.timer.stop()

	def ntp_sync(self):
		if config.misc.SyncTimeUsing.getValue() == "1":
			print '[NTP]: Updating'
			self.Console.ePopen('/usr/bin/ntpdate -s -u ' + config.misc.NTPserver.getValue(), self.update_schedule)

	def update_schedule(self, result = None, retval = None, extra_args = None):
		nowTime = time()
		print '[NTP]: setting E2 time:',nowTime
		setRTCtime(nowTime)
		eDVBLocalTimeHandler.getInstance().setUseDVBTime(False)
		self.timer.startLongTimer(int(config.misc.useNTPminutes.getValue()) * 60)
