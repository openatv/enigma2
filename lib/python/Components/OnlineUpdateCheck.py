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

	# The onlineupdatecheckpoller will be created (see below) after
	# OnlineUpdateCheckPoller is set-up, which is will be before we can ever
	# run.
	onlineupdatecheckpoller.start()

class SuspendableMessageBox(MessageBox):
		ALLOW_SUSPEND = True

class OnlineUpdateCheckPoller:
	def __init__(self):
		# Init Timer
		self.timer = eTimer()
		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)

	# Class variables
	MIN_INITIAL_DELAY = 40 * 60; # Wait at least 40 mins
	checktimer_Notifier_Added = False

	# Add optional args to start(), as it is now a callback from addNotifier
	# so will have one when called from there.
	def start(self, *args, **kwargs):
		if self.onlineupdate_check not in self.timer.callback:
			self.timer.callback.append(self.onlineupdate_check)

		# This will get start re-run on any change to the interval setting
		# so the next-timer will be suitably updated...
		# ...but only add one of them!!!
		if not self.checktimer_Notifier_Added:
			config.softwareupdate.checktimer.addNotifier(self.start, initial_call = False, immediate_feedback = False)
			self.checktimer_Notifier_Added = True
			minimum_delay = self.MIN_INITIAL_DELAY
		else: # we been here before, so this is *not* start-up
			minimum_delay = 60 # 1 minute

		last_run = config.softwareupdate.updatelastcheck.getValue()
		gap = config.softwareupdate.checktimer.value*3600
		delay = last_run + gap - int(time())

		# Set-up the minimum delay, which is greater on the first boot-time pass.
		# Also check that we aren't setting a delay that is more than the
		# configured frequency of checks, which caters for mis-/un-set system
		# clocks.
		if delay < minimum_delay:
			delay = minimum_delay
		if delay > gap:
			delay = gap
		self.timer.startLongTimer(delay)
		when = time() + delay

	def stop(self):
		if self.version_check in self.timer.callback:
			self.timer.callback.remove(self.onlineupdate_check)
		self.timer.stop()

	def onlineupdate_check(self):
		if config.softwareupdate.check.value:
			Components.Task.job_manager.AddJob(self.createCheckJob())
		self.timer.startLongTimer(int(config.softwareupdate.checktimer.value) * 3600)

		# Record the time of this latest check
		config.softwareupdate.updatelastcheck.setValue(int(time()))
		config.softwareupdate.updatelastcheck.save()

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
						Notifications.AddNotificationWithCallback(self.updateNotificationAnswer, SuspendableMessageBox, _("Online update available.\nInstall now?"))
				else:
					config.softwareupdate.updatefound.setValue(False)
			else:
				config.softwareupdate.updatefound.setValue(False)

	def updateNotificationAnswer(self, answer):
		if answer:
			Notifications.AddNotification(UpdatePlugin)

# Create a callable instance...
onlineupdatecheckpoller = OnlineUpdateCheckPoller()

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
