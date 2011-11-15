import Components.Task
from config import config
from enigma import eTimer
from os import path, remove
from glob import glob

_session = None

def AutoDebugLogCheck(session=None, **kwargs):
	global debuglogcheckpoller
	debuglogcheckpoller = DebugLogCheckPoller()
	debuglogcheckpoller.start()

class DebugLogCheckPoller:
	"""Automatically Poll DebugLogCheck"""
	def __init__(self):
		# Init Timer
		self.timer = eTimer()

	def start(self):
		if self.debug_check not in self.timer.callback:
			self.timer.callback.append(self.debug_check)
		self.timer.startLongTimer(0)

	def stop(self):
		if self.version_check in self.timer.callback:
			self.timer.callback.remove(self.debug_check)
		self.timer.stop()

	def debug_check(self):
		print '[DebugLogCheck] Poll Started'
		Components.Task.job_manager.AddJob(self.createCheckJob())

	def createCheckJob(self):
		job = Components.Task.Job(_("DebugLogCheck"))
		task = Components.Task.PythonTask(job, _("Checking Log Size..."))
		task.work = self.JobStart
		task.weighting = 1
		return job

	def JobStart(self):
		filename = ""
		if config.crash.enabledebug.value:
			for filename in glob(config.crash.debug_path.value + '*.log'):
				if path.getsize(filename) > (config.crash.debugloglimit.value * 1024 * 1024):
					fh = open(filename, 'rb+')
					fh.seek(-(config.crash.debugloglimit.value * 1024 * 1024), 2)
					data = fh.read()
					fh.seek(0) # rewind
					fh.write(data)
					fh.truncate()
					fh.close()
		elif not config.crash.enabledebug.value:
			for filename in glob(config.crash.debug_path.value + '*.log'):
				remove(filename)
		self.timer.startLongTimer(43200) #twice a day
