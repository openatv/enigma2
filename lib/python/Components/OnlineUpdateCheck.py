from time import time
from boxbranding import getImageVersion

from enigma import eTimer

import Components.Task
from Components.Ipkg import IpkgComponent
from Components.config import config


def OnlineUpdateCheck(session=None, **kwargs):
	global onlineupdatecheckpoller
	onlineupdatecheckpoller = OnlineUpdateCheckPoller()
	onlineupdatecheckpoller.start()

class OnlineUpdateCheckPoller:
	def __init__(self):
		# Init Timer
		self.timer = eTimer()
		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)

	def start(self):
		if self.onlineupdate_check not in self.timer.callback:
			self.timer.callback.append(self.onlineupdate_check)

		if time() > 1262304000:
			self.timer.startLongTimer(0)
		else:
			self.timer.startLongTimer(120)

	def stop(self):
		if self.version_check in self.timer.callback:
			self.timer.callback.remove(self.onlineupdate_check)
		self.timer.stop()

	def onlineupdate_check(self):
		if config.softwareupdate.check.getValue():
			Components.Task.job_manager.AddJob(self.createCheckJob())
		self.timer.startLongTimer(config.softwareupdate.checktimer.getValue() * 3600)

	def createCheckJob(self):
		job = Components.Task.Job(_("OnlineVersionCheck"))
		task = Components.Task.PythonTask(job, _("Checking for Updates..."))
		task.work = self.JobStart
		task.weighting = 1
		return job

	def JobStart(self):
		self.updating = True
		self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)

	def ipkgCallback(self, event, param):
		if event == IpkgComponent.EVENT_DONE:
			if self.updating:
				self.updating = False
				self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE_LIST)
			elif self.ipkg.currentCommand == IpkgComponent.CMD_UPGRADE_LIST:
				self.total_packages = len(self.ipkg.getFetchedList())
				print ('[OnlineVersionCheck] %s Updates available' % self.total_packages)
				if self.total_packages:
					from urllib import urlopen
					import socket
					currentTimeoutDefault = socket.getdefaulttimeout()
					socket.setdefaulttimeout(3)
					config.softwareupdate.updatefound.setValue(True)
					try:
						#config.softwareupdate.updateisunstable.setValue(urlopen("http://enigma2.world-of-satellite.com/feeds/" + getImageVersion() + "/status").read())
						config.softwareupdate.updateisunstable.setValue(urlopen("http://enigma2.world-of-satellite.com/feeds/3.0/status").read())
					except:
						config.softwareupdate.updateisunstable.setValue(1)
					socket.setdefaulttimeout(currentTimeoutDefault)
				else:
					config.softwareupdate.updatefound.setValue(False)
			else:
				config.softwareupdate.updatefound.setValue(False)
		pass

class VersionCheck:
	def __init__(self):
		pass

	def getStableUpdateAvailable(self):
		if config.softwareupdate.updatefound.getValue() and config.softwareupdate.check.getValue():
			if config.softwareupdate.updateisunstable.getValue() == '0':
# 				print '[OnlineVersionCheck] New Release updates found'
				return True
			else:
# 				print '[OnlineVersionCheck] skipping as beta is not wanted'
				return False
		else:
			return False

	def getUnstableUpdateAvailable(self):
		if config.softwareupdate.updatefound.getValue() and config.softwareupdate.check.getValue():
			if config.softwareupdate.updateisunstable.getValue() == '1' and config.softwareupdate.updatebeta.getValue():
# 				print '[OnlineVersionCheck] New Experimental updates found'
				return True
			else:
# 				print '[OnlineVersionCheck] skipping as beta is not wanted'
				return False
		else:
			return False

versioncheck = VersionCheck()
