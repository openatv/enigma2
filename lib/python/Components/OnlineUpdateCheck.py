import Components.Task
from Components.Ipkg import IpkgComponent
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
	def __init__(self):
		# Init Timer
		self.timer = eTimer()
		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)

	def start(self):
		now = int(time())
		if self.onlineupdate_check not in self.timer.callback:
			self.timer.callback.append(self.onlineupdate_check)
		if config.usage.infobar_onlinechecktimer.value > 0:
			print "[OnlineVersionCheck] Schedule Enabled at ", strftime("%c", localtime(now))
			if now > 1262304000:
				self.timer.startLongTimer(0)
			else:
				print "[OnlineVersionCheck] Time not yet set, delaying", strftime("%c", localtime(now))
				self.timer.startLongTimer(120)

	def stop(self):
		if self.version_check in self.timer.callback:
			self.timer.callback.remove(self.onlineupdate_check)
		self.timer.stop()

	def onlineupdate_check(self):
		now = int(time())
		if config.usage.infobar_onlinechecktimer.value > 0:
			print '[OnlineVersionCheck] Online check started', strftime("(now=%c)", localtime(now))
			Components.Task.job_manager.AddJob(self.createCheckJob())
		else:
			print '[OnlineVersionCheck] Online check skiped', strftime("(now=%c)", localtime(now))

	def createCheckJob(self):
		job = Components.Task.Job(_("OnlineVersionCheck"))

		task = Components.Task.PythonTask(job, _("Checking for Updates..."))
		task.work = self.JobStart
		task.weighting = 1

		return job

	def JobStart(self):
		self.updating = True
		self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)
		now = int(time())
		nextcheck = now + (int(config.usage.infobar_onlinechecktimer.value )* 3600)
		print "[OnlineVersionCheck] Next check at:", strftime("%c", localtime(int(nextcheck))), strftime("(%c)", localtime(now))
		self.timer.startLongTimer(config.usage.infobar_onlinechecktimer.value * 3600)

	def ipkgCallback(self, event, param):
		if event == IpkgComponent.EVENT_DONE:
			if self.updating:
				self.updating = False
				self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE_LIST)
			elif self.ipkg.currentCommand == IpkgComponent.CMD_UPGRADE_LIST:
				self.total_packages = len(self.ipkg.getFetchedList())
				print ('[OnlineVersionCheck] %s Updates available' % self.total_packages)
				if self.total_packages:
					config.usage.infobar_onlineupdatefound.setValue(True)
				else:
					config.usage.infobar_onlineupdatefound.setValue(False)
			else:
				config.usage.infobar_onlineupdatefound.setValue(False)
		pass

class VersionCheck:
	def __init__(self):
		pass

	def getImageUpdateAvailable(self):
		if config.usage.infobar_onlineupdatefound.value:
			print '[OnlineVersionCheck] New online version found'
			return True
		else:
			return False

versioncheck = VersionCheck()
