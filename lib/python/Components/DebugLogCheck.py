import Components.Task
from config import config
from Tools.Directories import pathExists
from twisted.internet import reactor, threads, task
from time import localtime, time, strftime
from enigma import eTimer
from os import path, remove
from glob import glob

_session = None

def AutoDebugLogCheck(session=None, **kwargs):
	global debuglogcheckpoller
	debuglogcheckpoller = DebugLogCheckPoller()
	debuglogcheckpoller.start()

class DebugLogCheckPoller:
	"""Automatically Poll SoftCam"""
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
		now = int(time())
		if config.crash.enabledebug.value:
			filename = ""
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
			filename = ""
			for filename in glob('/home/root/*.log') :
				remove(filename)
		self.timer.startLongTimer(43200) #twice a day
