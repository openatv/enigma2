import Components.Task
from Components.Console import Console
from config import config
from time import localtime, time, strftime
from enigma import eTimer
from os import path, remove

_session = None

def AutoNTPSync(session=None, **kwargs):
	global ntpsyncpoller
	ntpsyncpoller = NTPSyncPoller()
	ntpsyncpoller.start()

class NTPSyncPoller:
	"""Automatically Poll SoftCam"""
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
		print '[NTPSync] Poll Started'
		now = int(time())
		if not config.misc.useNTP.value:
			self.Console.ePopen('/usr/bin/ntpdate -s -u pool.ntp.org')
		self.timer.startLongTimer(int(config.misc.useNTPminutes.value) * 60)
