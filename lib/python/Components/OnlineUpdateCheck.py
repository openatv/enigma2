import Components.Task
from config import config
from Tools.Directories import pathExists, resolveFilename, SCOPE_SYSETC
from twisted.internet import reactor, threads, task
from time import localtime, time, strftime
from enigma import eTimer
from os import rename, remove

class VersionCheck:
	def __init__(self):
		pass

	def getImageUpdateAvailable(self):
		now = int(time())
		if config.usage.infobar_onlineupdatelastcheck.value != 0:
			lastchecked = (now - config.usage.infobar_onlineupdatelastcheck.value)
			CheckTime = (config.usage.infobar_onlinechecktimer.value * 3600) - lastchecked
		else:
			lastchecked = 0
			CheckTime = 0
		NextCheckTime = now + CheckTime
		if config.usage.infobar_onlinechecktimer.value > 0 and CheckTime <= 0:
			print '[OnlineVersionCheck] Online check started'
			Components.Task.job_manager.AddJob(self.createCheckJob())
			if config.usage.infobar_onlineupdatefound.value:
				print '[OnlineVersionCheck] New online version found'
				print "[OnlineVersionCheck] Next check allowed at", strftime("%c", localtime(NextCheckTime)), strftime("(now=%c)", localtime(now)), strftime("(Last Check=%c)", localtime(config.usage.infobar_onlineupdatelastcheck.value))
				return True
			else:
				print '[OnlineVersionCheck] No New online version found'
				print "[OnlineVersionCheck] Next check allowed at", strftime("%c", localtime(NextCheckTime)), strftime("(now=%c)", localtime(now)), strftime("(Last Check=%c)", localtime(config.usage.infobar_onlineupdatelastcheck.value))
				return False
		else:
			print "[OnlineVersionCheck] Next check allowed at", strftime("%c", localtime(NextCheckTime)), strftime("(now=%c)", localtime(now)), strftime("(Last Check=%c)", localtime(config.usage.infobar_onlineupdatelastcheck.value))
			return False

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
		config.usage.infobar_onlineupdatelastcheck.setValue(int(time()))

versioncheck = VersionCheck()
