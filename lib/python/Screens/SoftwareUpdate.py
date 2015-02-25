from boxbranding import getImageVersion, getImageBuild, getImageDistro, getMachineBrand, getMachineName, getMachineBuild
from os import rename, path, remove
from gettext import dgettext
import urllib

from enigma import eTimer, eDVBDB

import Components.Task
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
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

class SoftwareUpdateChanges(Screen):
	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		self.setTitle(_("OE Changes"))
		if path.exists('/tmp/oe-git.log'):
			remove('/tmp/oe-git.log')
		if path.exists('/tmp/e2-git.log'):
			remove('/tmp/e2-git.log')
		self.logtype = 'oe'
		self["text"] = ScrollLabel()
		self['title_summary'] = StaticText()
		self['text_summary'] = StaticText()
		self["key_red"] = Button(_("Close"))
		self["key_green"] = Button(_("Update"))
		self["key_yellow"] = Button(_("Show E2 Log"))
		self["myactions"] = ActionMap(['ColorActions', 'OkCancelActions', 'DirectionActions'],
		{
			'cancel': self.closeRecursive,
			"red": self.closeRecursive,
			"green": self.unattendedupdate,
			"yellow": self.changelogtype,
			"left": self.pageUp,
			"right": self.pageDown,
			"down": self.pageDown,
			"up": self.pageUp
		},-1)
		self.onLayoutFinish.append(self.getlog)

	def changelogtype(self):
		if self.logtype == 'oe':
			self["key_yellow"].setText(_("Show OE Log"))
			self.setTitle(_("Enigma2 Changes"))
			self.logtype = 'e2'
		else:
			self["key_yellow"].setText(_("Show E2 Log"))
			self.setTitle(_("OE Changes"))
			self.logtype = 'oe'
		self.getlog()

	def pageUp(self):
		self["text"].pageUp()

	def pageDown(self):
		self["text"].pageDown()

	def getlog(self):
		global ocram
		try:
			sourcefile = 'http://www.openvix.co.uk/feeds/%s/%s/%s-git.log' % (getImageDistro(), getImageVersion(), self.logtype)
			sourcefile,headers = urllib.urlretrieve(sourcefile)
			rename(sourcefile,'/tmp/' + self.logtype + '-git.log')
			fd = open('/tmp/' + self.logtype + '-git.log', 'r')
			releasenotes = fd.read()
			fd.close()
		except:
			releasenotes = '404 Not Found'
		if '404 Not Found' not in releasenotes:
			releasenotes = releasenotes.replace('[openvix] Zeus Release.', 'openvix: build 000')
			releasenotes = releasenotes.replace('\nopenvix: build',"\n\nopenvix: build")
			releasenotes = releasenotes.split('\n\n')
			ver = -1
			releasever = ""
			viewrelease = ""
			while not releasever.isdigit():
				ver += 1
				releasever = releasenotes[int(ver)].split('\n')
				releasever = releasever[0].split(' ')
				if len(releasever) > 2:
					releasever = releasever[2].replace(':',"")
				else:
					releasever = releasever[0].replace(':',"")
			if self.logtype == 'oe':
				if int(getImageBuild()) == 1:
					imagever = int(getImageBuild())-1
				else:
					imagever = int(getImageBuild())
			else:
				imagever = int(getImageBuild())+905
			while int(releasever) > int(imagever):
				if ocram:
					viewrelease += releasenotes[int(ver)]+'\n'+ocram+'\n'
					ocram = ""
				else:
					viewrelease += releasenotes[int(ver)]+'\n\n'
				ver += 1
				releasever = releasenotes[int(ver)].split('\n')
				releasever = releasever[0].split(' ')
				releasever = releasever[2].replace(':',"")
			if not viewrelease and ocram:
				viewrelease = ocram
				ocram = ""
			self["text"].setText(viewrelease)
			summarytext = viewrelease.split(':\n')
			try:
				self['title_summary'].setText(summarytext[0]+':')
				self['text_summary'].setText(summarytext[1])
			except:
				self['title_summary'].setText("")
				self['text_summary'].setText(viewrelease)
		else:
			self['title_summary'].setText("")
			self['text_summary'].setText(_("Error downloading change log."))
			self['text'].setText(_("Error downloading change log."))

	def unattendedupdate(self):
		self.close((_("Unattended upgrade without GUI and reboot system"), "cold"))

	def closeRecursive(self):
		self.close(("menu", "menu"))

class UpdatePlugin(Screen):
	def __init__(self, session, *args):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Software Update"))

		self.sliderPackages = { "dreambox-dvb-modules": 1, "enigma2": 2, "tuxbox-image-info": 3 }

		self.setTitle(_("Software update"))
		
		self.slider = Slider(0, 4)
		self["slider"] = self.slider
		self.activityslider = Slider(0, 100)
		self["activityslider"] = self.activityslider
		self.status = StaticText(_("Please wait..."))
		self["status"] = self.status
		self.package = StaticText(_("Package list update"))
		self["package"] = self.package
		self.oktext = _("Press OK on your remote control to continue.")

		status_msgs = {'stable': _('Feeds status:   Stable'), 'unstable': _('Feeds status:   Unstable'), 'updating': _('Feeds status:   Updating'), 'unknown': _('No connection')}
		self['tl_off'] = Pixmap()
		self['tl_red'] = Pixmap()
		self['tl_yellow'] = Pixmap()
		self['tl_green'] = Pixmap()
		self.feedsStatus()
		self['feedStatusMSG'] = Label(status_msgs[self.trafficLight])
		
		self.channellist_only = 0
		self.channellist_name = ''
		self.SettingsBackupDone = False
		self.ImageBackupDone = False
		self.autobackuprunning = False

		self.packages = 0
		self.error = 0
		self.processed_packages = []
		self.total_packages = None
		self.checkNetworkState()

	def feedsStatus(self):
		from urllib import urlopen
		import socket
		self['tl_red'].hide()
		self['tl_yellow'].hide()
		self['tl_green'].hide()
		currentTimeoutDefault = socket.getdefaulttimeout()
		socket.setdefaulttimeout(3)
		try:
			d = urlopen("http://openvix.co.uk/TrafficLightState.php")
			self.trafficLight = d.read()
			if self.trafficLight == 'unstable':
				self['tl_off'].hide()
				self['tl_red'].show()
			elif self.trafficLight == 'updating':
				self['tl_off'].hide()
				self['tl_yellow'].show()
			elif self.trafficLight == 'stable':
				self['tl_off'].hide()
				self['tl_green'].show()
			else:
				self.trafficLight = 'unknown'
				self['tl_off'].show()
		except:
			self.trafficLight = 'unknown'
			self['tl_off'].show()
		socket.setdefaulttimeout(currentTimeoutDefault)
		
	def checkNetworkState(self):
		cmd1 = "opkg update"
		self.CheckConsole = Console()
		self.CheckConsole.ePopen(cmd1, self.checkNetworkStateFinished)

	def checkNetworkStateFinished(self, result, retval,extra_args=None):
		if 'bad address' in result:
			self.session.openWithCallback(self.close, MessageBox, _("Your %s %s is not connected to the internet, please check your network settings and try again.") % (getMachineBrand(), getMachineName()), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif ('wget returned 1' or 'wget returned 255' or '404 Not Found') in result:
			self.session.openWithCallback(self.close, MessageBox, _("Sorry feeds are down for maintenance, please try again later. If this issue persists please check openvix.co.uk or world-of-satellite.com."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif 'Collected errors' in result:
			self.session.openWithCallback(self.close, MessageBox, _("A background update check is in progress, please wait a few minutes and try again."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			self.startCheck()

	def startCheck(self):
		self.activity = 0
		self.activityTimer = eTimer()
		self.activityTimer.callback.append(self.doActivityTimer)

		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)

		self.updating = False

		self["actions"] = ActionMap(["WizardActions"],
		{
			"ok": self.exit,
			"back": self.exit
		}, -1)

		self.updating = True
		self.activityTimer.start(100, False)
		self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)

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
				self.session.openWithCallback(
					self.modificationCallback,
					MessageBox,
					_("A configuration file (%s) has been modified since it was installed.\nDo you want to keep your modifications?") % param
				)
		elif event == IpkgComponent.EVENT_ERROR:
			self.error += 1
		elif event == IpkgComponent.EVENT_DONE:
			if self.updating:
				self.updating = False
				self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE_LIST)
			elif self.ipkg.currentCommand == IpkgComponent.CMD_UPGRADE_LIST:
				from urllib import urlopen
				import socket
				currentTimeoutDefault = socket.getdefaulttimeout()
				socket.setdefaulttimeout(3)
				status = urlopen('http://www.openvix.co.uk/feeds/status').read()
				if '404 Not Found' in status:
					status = '1'
				config.softwareupdate.updateisunstable.setValue(status)
				socket.setdefaulttimeout(currentTimeoutDefault)
				self.total_packages = None
				if config.softwareupdate.updateisunstable.value == '1' and config.softwareupdate.updatebeta.value:
					self.total_packages = len(self.ipkg.getFetchedList())
					message = _("The current update may be unstable") + "\n" + _("Are you sure you want to update your %s %s ?") % (getMachineBrand(), getMachineName()) + "\n(" + (ngettext("%s updated package available", "%s updated packages available", self.total_packages) % self.total_packages) + ")"
				elif config.softwareupdate.updateisunstable.value == '0':
					self.total_packages = len(self.ipkg.getFetchedList())
					message = _("Do you want to update your %s %s ?") % (getMachineBrand(), getMachineName()) + "\n(" + (ngettext("%s updated package available", "%s updated packages available", self.total_packages) % self.total_packages) + ")"
				if self.total_packages:
					global ocram
					for package_tmp in self.ipkg.getFetchedList():
						if package_tmp[0].startswith('enigma2-plugin-picons-tv-ocram'):
							ocram = ocram + '[ocram-picons] ' + package_tmp[0].split('enigma2-plugin-picons-tv-ocram.')[1] + 'updated ' + package_tmp[2] + '\n'
						elif package_tmp[0].startswith('enigma2-plugin-settings-ocram'):
							ocram = ocram + '[ocram-settings] ' + package_tmp[0].split('enigma2-plugin-picons-tv-ocram.')[1] + 'updated ' + package_tmp[2] + '\n'
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
					upgrademessage = self.session.openWithCallback(self.startActualUpgrade, ChoiceBox, title=message, list=choices, skin_name = "SoftwareUpdateChoices", var=self.trafficLight)
					upgrademessage.setTitle(_('Software update'))
				else:
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
					error = _("No updates available. Please try again later.")
				if self.updating:
					error = _("Update failed. Your %s %s does not have a working internet connection.") % (getMachineBrand(), getMachineName())
				self.status.setText(_("Error") +  " - " + error)
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
			upgrademessage = self.session.openWithCallback(self.startActualUpgrade, ChoiceBox, title=message, list=choices, skin_name = "SoftwareUpdateChoices", var=self.trafficLight)
			upgrademessage.setTitle(_('Software update'))
		elif answer[1] == "changes":
			self.session.openWithCallback(self.startActualUpgrade,SoftwareUpdateChanges)
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
