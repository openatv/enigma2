import Components.Task
from Components.Console import Console
from config import config
from enigma import eTimer

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
		if config.misc.SyncTimeUsing.value == "1":
			Components.Task.job_manager.AddJob(self.createCheckJob())
		self.timer.startLongTimer(int(config.misc.useNTPminutes.value) * 60)

	def createCheckJob(self):
		print '[NTPSync] Poll Started'
		job = Components.Task.Job(_("NTPSync"))
		task = Components.Task.PythonTask(job, _("Checking Time..."))
		task.work = self.JobStart
		task.weighting = 1
		return job

	def JobStart(self):
		self.Console.ePopen('/usr/bin/ntpdate -s -u pool.ntp.org')
