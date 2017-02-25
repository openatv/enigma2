from boxbranding import getImageVersion, getImageBuild, getImageDevBuild, getImageType, getImageDistro, getMachineBrand, getMachineName, getMachineBuild
from os import path
from gettext import dgettext

from enigma import eTimer, eDVBDB

import Components.Task
from Components.OnlineUpdateCheck import feedsstatuscheck, kernelMismatch, statusMessage
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.GitCommitInfo import CommitInfo, gitcommitinfo
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.config import config
from Components.Console import Console
from Components.Ipkg import IpkgComponent
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.Slider import Slider

ocram = ''

class SoftwareUpdateChanges(CommitInfo):
	def __init__(self, session, menu_path=""):
		CommitInfo.__init__(self, session, menu_path=menu_path)

		self["actions"] = ActionMap(["SetupActions", "DirectionActions"],
		{
			'cancel': self.closeRecursive,
			"red": self.closeRecursive,
			"up": self["AboutScrollLabel"].pageUp,
			"down": self["AboutScrollLabel"].pageDown,
			"left": self.left,
			"right": self.right
		},-1)

		self["key_red"] = Button(_("Close"))

	def readGithubCommitLogs(self):
		self.updateScreenTitle(gitcommitinfo.getScreenTitle())
		self["AboutScrollLabel"].setText(gitcommitinfo.readGithubCommitLogsSoftwareUpdate())


class UpdatePlugin(Screen, ProtectedScreen):
	def __init__(self, session, *args):
		Screen.__init__(self, session)
		ProtectedScreen.__init__(self)
		screentitle = _("Software Update")
		self.menu_path = args[0]
		if config.usage.show_menupath.value == 'large':
			self.menu_path += screentitle
			self.title = self.menu_path
			self.menu_path_compressed = ""
			self.menu_path += ' / '
		elif config.usage.show_menupath.value == 'small':
			self.title = screentitle
			condtext = ""
			if self.menu_path and not self.menu_path.endswith(' / '):
				condtext = self.menu_path + " >"
			elif self.menu_path:
				condtext = self.menu_path[:-3] + " >"
			self.menu_path_compressed = condtext
			self.menu_path += screentitle + ' / '
		else:
			self.title = screentitle
			self.menu_path_compressed = ""
		self["menu_path_compressed"] = StaticText(self.menu_path_compressed)
		Screen.setTitle(self, self.title)

		self["actions"] = ActionMap(["WizardActions"],
		{
			"ok": self.exit,
			"back": self.exit
		}, -1)
		self['actions'].csel = self
		self["actions"].setEnabled(False)

		self.sliderPackages = { "dreambox-dvb-modules": 1, "enigma2": 2, "tuxbox-image-info": 3 }
		self.slider = Slider(0, 4)
		self["slider"] = self.slider
		self.activityslider = Slider(0, 100)
		self["activityslider"] = self.activityslider
		self.status = StaticText(_("Please wait..."))
		self["status"] = self.status
		self.package = StaticText(_("Package list update"))
		self["package"] = self.package
		self.oktext = _("Press OK on your remote control to continue.")

		self['tl_off'] = Pixmap()
		self['tl_red'] = Pixmap()
		self['tl_yellow'] = Pixmap()
		self['tl_green'] = Pixmap()
		self['feedStatusMSG'] = Label()

		self.channellist_only = 0
		self.channellist_name = ''
		self.SettingsBackupDone = False
		self.ImageBackupDone = False
		self.autobackuprunning = False
		self.updating = False

		self.packages = 0
		self.error = 0
		self.processed_packages = []
		self.total_packages = None
		self.onFirstExecBegin.append(self.checkNetworkState)

	def checkNetworkState(self):
		self['tl_red'].hide()
		self['tl_yellow'].hide()
		self['tl_green'].hide()
		self['tl_off'].hide()
		self.trafficLight = feedsstatuscheck.getFeedsBool()
		if self.trafficLight in feedsstatuscheck.feed_status_msgs:
			status_text = feedsstatuscheck.feed_status_msgs[self.trafficLight]
		else:
			status_text = _('Feeds status: Unexpected')
		if self.trafficLight:
			self['feedStatusMSG'].setText(status_text)
		if self.trafficLight == 'stable':
			self['tl_green'].show()
		elif self.trafficLight == 'unstable':
			self['tl_red'].show()
		elif self.trafficLight == 'updating':
			self['tl_yellow'].show()
		else:
			self['tl_off'].show()
		if kernelMismatch():
			self.session.openWithCallback(self.close, MessageBox, _("The Linux kernel has changed, an update is not permitted. \nInstall latest image using USB stick or Image Manager."), type=MessageBox.TYPE_INFO, timeout=30, close_on_any_key=True)
			return
		if (getImageType() != 'release' and self.trafficLight != 'unknown') or (getImageType() == 'release' and self.trafficLight not in ('stable', 'unstable')):
			self.session.openWithCallback(self.close, MessageBox, feedsstatuscheck.getFeedsErrorMessage(), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			if getImageType() != 'release' or (config.softwareupdate.updateisunstable.value == '1' and config.softwareupdate.updatebeta.value) or config.softwareupdate.updateisunstable.value == '0':
				message = statusMessage()
				if message:
					message += "\nDo you want to continue?"
					self.session.openWithCallback(self.statusMessageCallback, MessageBox, message, type=MessageBox.TYPE_YESNO, default=False)
				else:
					self.startCheck()
			else:
				self.session.openWithCallback(self.close, MessageBox, _("Sorry the feeds seem to be in an unstable state, if you wish to use them please enable 'Allow unstable (experimental) updates' in \"Software update settings\"."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)

	def statusMessageCallback(self, answer):
		if answer:
			self.startCheck()
		else:
			self.close()

	def startCheck(self):
		self.updating = True
		self.activity = 0
		self.activityTimer = eTimer()
		self.activityTimer.callback.append(self.doActivityTimer)

		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)

		self.activityTimer.start(100, False)
		self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)

# We've just manually checked for an update, so note this time as the last
# check time, then update the next autocheck time too.
#
		from time import time
		config.softwareupdate.updatelastcheck.setValue(int(time()))
		config.softwareupdate.updatelastcheck.save()
		from Components.OnlineUpdateCheck import onlineupdatecheckpoller
		onlineupdatecheckpoller.start()

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and\
			(not config.ParentalControl.config_sections.main_menu.value and not config.ParentalControl.config_sections.configuration.value  or hasattr(self.session, 'infobar') and self.session.infobar is None) and\
			config.ParentalControl.config_sections.software_update.value

	def doActivityTimer(self):
		self.activity += 1
		if self.activity == 100:
			self.activity = 0
		self.activityslider.setValue(self.activity)

	def showUpdateCompletedMessage(self):
		self.setEndMessage(ngettext("Update completed, %d package was installed.", "Update completed, %d packages were installed.", self.packages) % self.packages)

	def ipkgCallback(self, event, param):
		if event == IpkgComponent.EVENT_DOWNLOAD:
			self.status.setText(_("Downloading"))
		elif event == IpkgComponent.EVENT_UPGRADE:
			if self.sliderPackages.has_key(param):
				self.slider.setValue(self.sliderPackages[param])
			self.package.setText(param)
			self.status.setText(_("Upgrading") + ": %s/%s" % (self.packages, self.total_packages))
			if not param in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == IpkgComponent.EVENT_INSTALL:
			self.package.setText(param)
			self.status.setText(_("Installing"))
			if not param in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == IpkgComponent.EVENT_REMOVE:
			self.package.setText(param)
			self.status.setText(_("Removing"))
			if not param in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == IpkgComponent.EVENT_CONFIGURING:
			self.package.setText(param)
			self.status.setText(_("Configuring"))
		elif event == IpkgComponent.EVENT_MODIFIED:
			if config.plugins.softwaremanager.overwriteConfigFiles.value in ("N", "Y"):
				self.ipkg.write(True and config.plugins.softwaremanager.overwriteConfigFiles.value)
			else:
				self["actions"].setEnabled(True)
				self.session.openWithCallback(
					self.modificationCallback,
					MessageBox,
					_("A configuration file (%s) has been modified since it was installed.\nDo you want to keep your modifications?") % param
				)
		elif event == IpkgComponent.EVENT_ERROR:
			self.error += 1
			self.updating = False
		elif event == IpkgComponent.EVENT_DONE:
			if self.updating:
				self.updating = False
				self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE_LIST)
			elif self.ipkg.currentCommand == IpkgComponent.CMD_UPGRADE_LIST:
				self.total_packages = None
				if getImageType() != 'release' or (config.softwareupdate.updateisunstable.value == '1' and config.softwareupdate.updatebeta.value):
					self.total_packages = len(self.ipkg.getFetchedList())
					message = _("The current update may be unstable") + "\n" + _("Are you sure you want to update your %s %s ?") % (getMachineBrand(), getMachineName()) + "\n(" + (ngettext("%s updated package available", "%s updated packages available", self.total_packages) % self.total_packages) + ")"
				elif config.softwareupdate.updateisunstable.value == '0':
					self.total_packages = len(self.ipkg.getFetchedList())
					message = _("Do you want to update your %s %s ?") % (getMachineBrand(), getMachineName()) + "\n(" + (ngettext("%s updated package available", "%s updated packages available", self.total_packages) % self.total_packages) + ")"
				if self.total_packages > 150:
					message += " " + _("Reflash recommended!")
				if self.total_packages:
					global ocram
					ocram = ''
					for package_tmp in self.ipkg.getFetchedList():
						if package_tmp[0].startswith('enigma2-plugin-picons-snp'):
							ocram = ocram + '[ocram-picons] ' + package_tmp[0].split('enigma2-plugin-picons-snp-')[1].replace('.',' ') + ' updated ' + package_tmp[2].replace('--',' ') + '\n'
						elif package_tmp[0].startswith('enigma2-plugin-picons-srp'):
							ocram = ocram + '[ocram-picons] ' + package_tmp[0].split('enigma2-plugin-picons-srp-')[1].replace('.',' ') + ' updated ' + package_tmp[2].replace('--',' ') + '\n'
					config.softwareupdate.updatefound.setValue(True)
					choices = [(_("View the changes"), "changes"),
						(_("Upgrade and reboot system"), "cold")]
					if path.exists("/usr/lib/enigma2/python/Plugins/SystemPlugins/ViX/BackupManager.pyo"):
						if not config.softwareupdate.autosettingsbackup.value and config.backupmanager.backuplocation.value:
							choices.append((_("Perform a settings backup,") + '\n\t' + _("making a backup before updating") + '\n\t' +_("is strongly advised."), "backup"))
						if not config.softwareupdate.autoimagebackup.value and config.imagemanager.backuplocation.value:
							choices.append((_("Perform a full image backup"), "imagebackup"))
					choices.append((_("Update channel list only"), "channels"))
					choices.append((_("Cancel"), ""))
					self["actions"].setEnabled(True)
					upgrademessage = self.session.openWithCallback(self.startActualUpgrade, ChoiceBox, title=message, list=choices, skin_name = "SoftwareUpdateChoices", var=self.trafficLight, menu_path=self.menu_path_compressed)
					upgrademessage.setTitle(self.title)
				else:
					self["actions"].setEnabled(True)
					upgrademessage = self.session.openWithCallback(self.close, MessageBox, _("Nothing to upgrade"), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
					upgrademessage.setTitle(_('Software update'))
			elif self.channellist_only > 0:
				if self.channellist_only == 1:
					self.setEndMessage(_("Could not find installed channel list."))
				elif self.channellist_only == 2:
					self.slider.setValue(2)
					self.ipkg.startCmd(IpkgComponent.CMD_REMOVE, {'package': self.channellist_name})
					self.channellist_only += 1
				elif self.channellist_only == 3:
					self.slider.setValue(3)
					self.ipkg.startCmd(IpkgComponent.CMD_INSTALL, {'package': self.channellist_name})
					self.channellist_only += 1
				elif self.channellist_only == 4:
					self.showUpdateCompletedMessage()
					eDVBDB.getInstance().reloadBouquets()
					eDVBDB.getInstance().reloadServicelist()
			elif self.error == 0:
				self.showUpdateCompletedMessage()
			else:
				self.activityTimer.stop()
				self.activityslider.setValue(0)
				error = _("Your %s %s might be unusable now. Please consult the manual for further assistance before rebooting your %s %s.") % (getMachineBrand(), getMachineName(), getMachineBrand(), getMachineName())
				if self.packages == 0:
					if self.error != 0:
						error = _("Problem retrieving update list.\nIf this issue persists please check/report on forum")
					else:
						error = _("A background update check is in progress,\nplease wait a few minutes and try again.")
				if self.updating:
					error = _("Update failed. Your %s %s does not have a working internet connection.") % (getMachineBrand(), getMachineName())
				self.status.setText(_("Error") +  " - " + error)
				self["actions"].setEnabled(True)
		elif event == IpkgComponent.EVENT_LISTITEM:
			if 'enigma2-plugin-settings-' in param[0] and self.channellist_only > 0:
				self.channellist_name = param[0]
				self.channellist_only = 2
		#print event, "-", param
		pass

	def setEndMessage(self, txt):
		self.slider.setValue(4)
		self.activityTimer.stop()
		self.activityslider.setValue(0)
		self.package.setText(txt)
		self.status.setText(self.oktext)

	def startActualUpgrade(self, answer):
		if not answer or not answer[1]:
			self.close()
			return

		if answer[1] == "menu":
			if config.softwareupdate.updateisunstable.value == '1':
				message = _("The current update may be unstable") + "\n" + _("Are you sure you want to update your %s %s ?") % (getMachineBrand(), getMachineName()) + "\n(%s " % self.total_packages + _("Packages") + ")"
			elif config.softwareupdate.updateisunstable.value == '0':
				message = _("Do you want to update your %s %s ?") % (getMachineBrand(), getMachineName()) + "\n(%s " % self.total_packages + _("Packages") + ")"
			choices = [(_("View the changes"), "changes"),
				(_("Upgrade and reboot system"), "cold")]
			if not self.SettingsBackupDone and not config.softwareupdate.autosettingsbackup.value and config.backupmanager.backuplocation.value:
				choices.append((_("Perform a settings backup, making a backup before updating is strongly advised."), "backup"))
			if not self.ImageBackupDone and not config.softwareupdate.autoimagebackup.value and config.imagemanager.backuplocation.value:
				choices.append((_("Perform a full image backup"), "imagebackup"))
			choices.append((_("Update channel list only"), "channels"))
			choices.append((_("Cancel"), ""))
			self["actions"].setEnabled(True)
			upgrademessage = self.session.openWithCallback(self.startActualUpgrade, ChoiceBox, title=message, list=choices, skin_name="SoftwareUpdateChoices", var=self.trafficLight, menu_path=self.menu_path_compressed)
			upgrademessage.setTitle(self.title)
		elif answer[1] == "changes":
			self.session.openWithCallback(self.startActualUpgrade,SoftwareUpdateChanges, self.menu_path)
		elif answer[1] == "backup":
			self.doSettingsBackup()
		elif answer[1] == "imagebackup":
			self.doImageBackup()
		elif answer[1] == "channels":
			self.channellist_only = 1
			self.slider.setValue(1)
			self.ipkg.startCmd(IpkgComponent.CMD_LIST, args = {'installed_only': True})
		elif answer[1] == "cold":
			if (config.softwareupdate.autosettingsbackup.value and config.backupmanager.backuplocation.value) or (config.softwareupdate.autoimagebackup.value and config.imagemanager.backuplocation.value):
				self.doAutoBackup()
			else:
				self.session.open(TryQuitMainloop,retvalue=42)
				self.close()

	def modificationCallback(self, res):
		self.ipkg.write(res and "N" or "Y")

	def doSettingsBackup(self):
		backup = None
		from Plugins.SystemPlugins.ViX.BackupManager import BackupFiles
		self.BackupFiles = BackupFiles(self.session, True)
		Components.Task.job_manager.AddJob(self.BackupFiles.createBackupJob())
		Components.Task.job_manager.in_background = False
		for job in Components.Task.job_manager.getPendingJobs():
			if job.name == dgettext('vix', 'Backup Manager'):
				break
		self.showJobView(job)

	def doImageBackup(self):
		backup = None
		from Plugins.SystemPlugins.ViX.ImageManager import ImageBackup
		self.ImageBackup = ImageBackup(self.session, True)
		Components.Task.job_manager.AddJob(self.ImageBackup.createBackupJob())
		Components.Task.job_manager.in_background = False
		for job in Components.Task.job_manager.getPendingJobs():
			if job.name == dgettext('vix', 'Image Manager'):
				break
		self.showJobView(job)

	def doAutoBackup(self, val = False):
		self.autobackuprunning = True
		if config.softwareupdate.autosettingsbackup.value and config.backupmanager.backuplocation.value and not self.SettingsBackupDone:
			self.doSettingsBackup()
		elif config.softwareupdate.autoimagebackup.value and config.imagemanager.backuplocation.value and not self.ImageBackupDone:
			self.doImageBackup()
		else:
			self.session.open(TryQuitMainloop,retvalue=42)
			self.close()

	def showJobView(self, job):
		if job.name == dgettext('vix', 'Image Manager'):
			self.ImageBackupDone = True
		elif job.name == dgettext('vix', 'Backup Manager'):
			self.SettingsBackupDone = True
		from Screens.TaskView import JobView
		Components.Task.job_manager.in_background = False
		if not self.autobackuprunning:
			self.session.openWithCallback(self.startActualUpgrade(("menu", "menu")), JobView, job,  cancelable = False, backgroundable = False, afterEventChangeable = False, afterEvent="close")
		else:
			self.session.openWithCallback(self.doAutoBackup, JobView, job,  cancelable = False, backgroundable = False, afterEventChangeable = False, afterEvent="close")

	def exit(self):
		if not self.ipkg.isRunning():
			if self.packages != 0 and self.error == 0 and self.channellist_only == 0:
				self.session.openWithCallback(self.exitAnswer, MessageBox, _("Upgrade finished.") +" "+_("Do you want to reboot your %s %s") % (getMachineBrand(), getMachineName()))
			else:
				self.close()
		else:
			if not self.updating:
				self.close()

	def exitAnswer(self, result):
		if result is not None and result:
			self.session.open(TryQuitMainloop, retvalue=2)
		self.close()
