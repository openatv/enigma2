import Components.Task
from config import config
from Tools.Directories import pathExists
from twisted.internet import reactor, threads, task
from time import localtime, time, strftime
from enigma import eTimer
from os import rename, remove

def AutoVersionCheck(session=None, **kwargs):
	global versioncheckpoller
	print "[OnlineVersionCheck] AutoStart Enabled"
	versioncheckpoller = VersionCheckPoller()
	versioncheckpoller.start()

class VersionCheckPoller:
	"""Automatically Poll SoftCam"""
	def __init__(self):
		# Init Timer
		self.timer = eTimer()

	def start(self, initial = True):
		if self.version_check not in self.timer.callback:
			self.timer.callback.append(self.version_check)
		self.timer.startLongTimer(60)

	def stop(self):
		if self.version_check in self.timer.callback:
			self.timer.callback.remove(self.version_check)
		self.timer.stop()

	def version_check(self):
		now = int(time())
		print "[OnlineVersionCheck] Poll occured at", strftime("%c", localtime(now))
		name = _("OnlineCheck")
		job = Components.Task.Job(name)
		task = CheckTask(job, name)
		Components.Task.job_manager.AddJob(job)
		self.timer.startLongTimer(int(config.usage.infobar_onlinecheck.value) * 3600)

class CheckTask(Components.Task.PythonTask):
	def work(self):
		if pathExists('/tmp/online-image-version'):
			remove('/tmp/online-image-version')

		file = open('/etc/image-version', 'r')
		lines = file.readlines()
		file.close()
		for x in lines:
			splitted = x.split('=')
			if splitted[0] == "box_type":
				box_type = splitted[1].replace('\n','') # 0 = release, 1 = experimental
			elif splitted[0] == "version":
				version = splitted[1].replace('\n','')
				version = version.split('.')
				version = version[0] + '.' + version[1]

		import urllib
		fd = open('/etc/opkg/all-feed.conf', 'r')
		fileurl = fd.read()
		fd.close()
		if fileurl.find('experimental') != -1:
			sourcefile='http://enigma2.world-of-satellite.com/feeds/release/' + box_type + '/image-version'
		else:
			sourcefile='http://enigma2.world-of-satellite.com/feeds/ghtudh66383/' + box_type + '/image-version'
		sourcefile,headers = urllib.urlretrieve(sourcefile)
		rename(sourcefile,'/tmp/online-image-version')
