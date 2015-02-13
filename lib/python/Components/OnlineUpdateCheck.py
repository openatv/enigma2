from time import time
from boxbranding import getImageVersion

from enigma import eTimer

import Components.Task
from Components.Ipkg import IpkgComponent
from Components.config import config
from Tools import Notifications
from Screens.MessageBox import MessageBox
from Screens.SoftwareUpdate import UpdatePlugin

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

		if time() > 1262304000:  # Fri, 01 Jan 2010 00:00:00 GMT
			self.timer.startLongTimer(30)
		else:
			self.timer.startLongTimer(10 * 60)

	def stop(self):
		if self.version_check in self.timer.callback:
			self.timer.callback.remove(self.onlineupdate_check)
		self.timer.stop()

	def onlineupdate_check(self):
		if config.softwareupdate.check.value:
			Components.Task.job_manager.AddJob(self.createCheckJob())
		self.timer.startLongTimer(int(config.softwareupdate.checktimer.value) * 3600)

	def createCheckJob(self):
		job = Components.Task.Job(_("OnlineVersionCheck"))
		task = Components.Task.PythonTask(job, _("Checking for updates..."))
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
				print ('[OnlineVersionCheck] %s updates available' % self.total_packages)
				if self.total_packages:
					config.softwareupdate.updatefound.setValue(True)
					if not versioncheck.user_notified:
						versioncheck.user_notified = True
						Notifications.AddNotificationWithCallback(self.updateNotificationAnswer, MessageBox, _("Online update available.\nInstall now?"))
				else:
					config.softwareupdate.updatefound.setValue(False)
			else:
				config.softwareupdate.updatefound.setValue(False)

	def updateNotificationAnswer(self, answer):
		if answer:
			Notifications.AddNotification(UpdatePlugin)

class VersionCheck:
	def __init__(self):
		self.user_notified = False

	def getStableUpdateAvailable(self):
		if config.softwareupdate.updatefound.value and config.softwareupdate.check.value:
			if config.softwareupdate.updateisunstable.value == 0:
				# print '[OnlineVersionCheck] New Release updates found'
				return True
			else:
				# print '[OnlineVersionCheck] skipping as beta is not wanted'
				return False
		else:
			return False

	def getUnstableUpdateAvailable(self):
		if config.softwareupdate.updatefound.value and config.softwareupdate.check.value:
			if config.softwareupdate.updateisunstable.value == 1 and config.softwareupdate.updatebeta.value:
				# print '[OnlineVersionCheck] New Experimental updates found'
				return True
			else:
				# print '[OnlineVersionCheck] skipping as beta is not wanted'
				return False
		else:
			return False

versioncheck = VersionCheck()
