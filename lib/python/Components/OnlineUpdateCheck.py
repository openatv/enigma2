import Components.Task
from config import config
from Tools.Directories import pathExists, resolveFilename, SCOPE_SYSETC
from twisted.internet import reactor, threads, task
from time import localtime, time, strftime
from enigma import eTimer
from os import rename, remove

def OnlineUpdateCheck(session=None, **kwargs):
	global onlineupdatecheckpoller
	onlineupdatecheckpoller = OnlineUpdateCheckPoller()
	onlineupdatecheckpoller.start()

class OnlineUpdateCheckPoller:
	"""Automatically Poll SoftCam"""
	def __init__(self):
		# Init Timer
		self.timer = eTimer()

	def start(self):
		print '[OnlineVersionCheck] Poll Started'
		if self.onlineupdate_check not in self.timer.callback:
			self.timer.callback.append(self.onlineupdate_check)
		self.timer.startLongTimer(0)

	def stop(self):
		if self.version_check in self.timer.callback:
			self.timer.callback.remove(self.onlineupdate_check)
		self.timer.stop()

	def onlineupdate_check(self):
		print '[OnlineVersionCheck] Online check started'
		Components.Task.job_manager.AddJob(self.createCheckJob())

	def createCheckJob(self):
		job = Components.Task.Job(_("OnlineVersionCheck"))

		task = Components.Task.PythonTask(job, _("Downloading file..."))
		task.work = self.JobStart
		task.weighting = 1

		task = Components.Task.ConditionTask(job, _("Downloading file..."), timeoutCount=20)
		task.check = lambda: pathExists('/tmp/online-image-version')
		task.weighting = 1

		task = Components.Task.PythonTask(job, _("Checking Version..."))
		task.work = self.CheckVersion
		task.weighting = 1

		return job

	def JobStart(self):
		now = int(time())
		if pathExists('/tmp/online-image-version'):
			remove('/tmp/online-image-version')
		file = open(resolveFilename(SCOPE_SYSETC, 'image-version'), 'r')
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
		if fileurl.find('release') != -1:
			print '[OnlineVersionCheck] Downloading RELEASE online version file.'
			sourcefile='http://enigma2.world-of-satellite.com/feeds/release/' + box_type + '/image-version'
		else:
			print '[OnlineVersionCheck] Downloading BETA online version file.'
			sourcefile='http://enigma2.world-of-satellite.com/feeds/ghtudh66383/' + box_type + '/image-version'
		sourcefile,headers = urllib.urlretrieve(sourcefile)
		rename(sourcefile,'/tmp/online-image-version')

		nextcheck = now + (int(config.usage.infobar_onlinechecktimer.value )* 3600)
		print 'NEXT CHECK',nextcheck
		print "[OnlineVersionCheck] Next check at:", strftime("%c", localtime(int(nextcheck))), strftime("(now=%c)", localtime(now))
		self.timer.startLongTimer(config.usage.infobar_onlinechecktimer.value * 3600)


	def CheckVersion(self):
		onlineversion = ""
		currentversion = ""
		print '[OnlineVersionCheck] parsing online version file.'
		file = open(resolveFilename(SCOPE_SYSETC, 'image-version'), 'r')
		lines = file.readlines()
		for x in lines:
			splitted = x.split('=')
			if splitted[0] == "date":
				currentversion = splitted[1].replace('\n','')
		file.close()
		file = open('/tmp/online-image-version', 'r')
		lines = file.readlines()
		for x in lines:
			splitted = x.split('=')
			if splitted[0] == "date":
				onlineversion = splitted[1].replace('\n','')
		file.close()
		if onlineversion > currentversion:
			config.usage.infobar_onlineupdatefound.setValue(True)
		else:
			config.usage.infobar_onlineupdatefound.setValue(False)
		if pathExists('/tmp/online-image-version'):
			remove('/tmp/online-image-version')


class VersionCheck:
	def __init__(self):
		pass

	def getImageUpdateAvailable(self):
		if config.usage.infobar_onlineupdatefound.value:
			print '[OnlineVersionCheck] New online version found'
			return True
		else:
			print '[OnlineVersionCheck] No New online version found'
			return False

versioncheck = VersionCheck()
