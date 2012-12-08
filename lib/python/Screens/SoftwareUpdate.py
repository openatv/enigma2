from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Components.About import about
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.config import config
from Components.Console import Console
from Components.Ipkg import IpkgComponent
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.Slider import Slider
import Components.Task
from enigma import eTimer, eDVBDB
from os import rename, path, remove

class SoftwareUpdateChanges(Screen):
	def __init__(self, session, args = None):
		self.skin = """
			<screen position="center,center" size="720,540" >
				<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
				<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
				<widget name="key_red" position="0,2" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
				<widget name="key_green" position="140,2" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
				<widget name="text" position="0,50" size="720,500" font="Regular;21" />
			</screen>"""
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
			self["key_yellow"].setText(_("Show E2 Log"))
			self.setTitle(_("OE Changes"))
			self.logtype = 'e2'
		else:
			self["key_yellow"].setText(_("Show OE Log"))
			self.setTitle(_("Enimga2 Changes"))
			self.logtype = 'oe'
		self.getlog()

	def pageUp(self):
		self["text"].pageUp()

	def pageDown(self):
		self["text"].pageDown()

	def getlog(self):
		if not path.exists('/tmp/' + self.logtype + '-git.log'):
			import urllib
			sourcefile = 'http://enigma2.world-of-satellite.com/feeds/' + about.getImageVersionString() + '/' + self.logtype + '-git.log'
			sourcefile,headers = urllib.urlretrieve(sourcefile)
			rename(sourcefile,'/tmp/' + self.logtype + '-git.log')
		fd = open('/tmp/' + self.logtype + '-git.log', 'r')
		releasenotes = fd.read()
		fd.close()
		releasenotes = releasenotes.replace('\nopenvix: build',"\n\nopenvix: build")
		releasenotes = releasenotes.split('\n\n')
		ver=0
		releasever = releasenotes[int(ver)].split('\n')
		releasever = releasever[0].split(' ')
		releasever = releasever[2].replace(':',"")
		viewrelease=""
		while int(releasever) > int(about.getBuildVersionString()):
			viewrelease += releasenotes[int(ver)]+'\n\n'
			ver += 1
			releasever = releasenotes[int(ver)].split('\n')
			releasever = releasever[0].split(' ')
			releasever = releasever[2].replace(':',"")
		self["text"].setText(viewrelease)
		summarytext = viewrelease.split(':\n')
		try:
			self['title_summary'].setText(summarytext[0]+':')
			self['text_summary'].setText(summarytext[1])
		except:
			self['title_summary'].setText("")
			self['text_summary'].setText("")

	def unattendedupdate(self):
		self.close((_("Unattended upgrade without GUI and reboot system"), "cold"))

	def closeRecursive(self):
		self.close(("menu", "menu"))

class UpdatePlugin(Screen):
	skin = """
		<screen name="UpdatePlugin" position="center,center" size="550,300">
			<widget name="activityslider" position="0,0" size="550,5"  />
			<widget name="slider" position="0,150" size="550,30"  />
			<widget source="package" render="Label" position="10,30" size="540,20" font="Regular;18" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="status" render="Label" position="10,180" size="540,100" font="Regular;20" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
		</screen>"""

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

	def checkNetworkState(self):
		cmd1 = "opkg update"
		self.CheckConsole = Console()
		self.CheckConsole.ePopen(cmd1, self.checkNetworkStateFinished)

	def checkNetworkStateFinished(self, result, retval,extra_args=None):
		if result.find('wget returned 1') != -1 or result.find('wget returned 255') != -1 or result.find('404 Not Found') != -1:
			self.session.openWithCallback(self.close, MessageBox, _("Sorry feeds are down for maintenance, please try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif result.find('bad address') != -1:
			self.session.openWithCallback(self.close, MessageBox, _("Your STB_BOX is not connected to the internet, please check your network settings and try again."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif result.find('Collected errors') != -1:
			self.session.openWithCallback(self.close, MessageBox, _("A background update check is is progress, please wait a few minutes and try again."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
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
			if config.plugins.softwaremanager.overwriteConfigFiles.getValue() in ("N", "Y"):
				self.ipkg.write(True and config.plugins.softwaremanager.overwriteConfigFiles.getValue())
			else:
				self.session.openWithCallback(
					self.modificationCallback,
					MessageBox,
					_("A configuration file (%s) has been modified since it was installed.\nDo you want to keep your modifications?") % (param)
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
				try:
					config.softwareupdate.updateisunstable.setValue(urlopen("http://enigma2.world-of-satellite.com/feeds/" + about.getImageVersionString() + "/status").read())
				except:
					config.softwareupdate.updateisunstable.setValue(1)
				socket.setdefaulttimeout(currentTimeoutDefault)
				self.total_packages = None
				if config.softwareupdate.updateisunstable.getValue() == '1' and config.softwareupdate.updatebeta.getValue():
					self.total_packages = len(self.ipkg.getFetchedList())
					message = _("The current update maybe unstable") + "\n" + _("Are you sure you want to update your STB_BOX?") + "\n(" + (ngettext("%s updated package available", "%s updated packages available", self.total_packages) % self.total_packages) + ")"
				elif config.softwareupdate.updateisunstable.getValue() == '0':
					self.total_packages = len(self.ipkg.getFetchedList())
					message = _("Do you want to update your STB_BOX?") + "\n(" + (ngettext("%s updated package available", "%s updated packages available", self.total_packages) % self.total_packages) + ")"
				if self.total_packages:
					config.softwareupdate.updatefound.setValue(True)
					choices = [(_("View the changes"), "changes"),
						(_("Upgrade and reboot system"), "cold")]
					if path.exists("/usr/lib/enigma2/python/Plugins/SystemPlugins/ViX/BackupManager.pyo"):
						if not config.softwareupdate.autosettingsbackup.getValue():
							choices.append((_("Perform a setting backup,") + '\n\t' + _("making a backup before updating") + '\n\t' +_("is strongly advised."), "backup"))
						if not config.softwareupdate.autoimagebackup.getValue():
							choices.append((_("Perform a full image backup"), "imagebackup"))
					choices.append((_("Update channel list only"), "channels"))
					choices.append((_("Cancel"), ""))
					upgrademessage = self.session.openWithCallback(self.startActualUpgrade, ChoiceBox, title=message, list=choices, skin_name = "SoftwareUpdateChoices")
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
				error = _("Your STB_BOX might be unusable now. Please consult the manual for further assistance before rebooting your STB_BOX.")
				if self.packages == 0:
					error = _("No updates available. Please try again later.")
				if self.updating:
					error = _("Update failed. Your STB_BOX does not have a working internet connection.")
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
			if config.softwareupdate.updateisunstable.getValue() == '1':
				message = _("The current update maybe unstable") + "\n" + _("Are you sure you want to update your STB_BOX?") + "\n(%s " % self.total_packages + _("Packages") + ")"
			elif config.softwareupdate.updateisunstable.getValue() == '0':
				message = _("Do you want to update your STB_BOX?") + "\n(%s " % self.total_packages + _("Packages") + ")"
			choices = [(_("View the changes"), "changes"),
				(_("Upgrade and reboot system"), "cold")]
			if not self.SettingsBackupDone and not config.softwareupdate.autosettingsbackup.getValue():
				choices.append((_("Perform a setting backup, making a backup before updating is strongly advised."), "backup"))
			if not self.ImageBackupDone and not config.softwareupdate.autoimagebackup.getValue():
				choices.append((_("Perform a full image backup"), "imagebackup"))
			choices.append((_("Update channel list only"), "channels"))
			choices.append((_("Cancel"), ""))
			upgrademessage = self.session.openWithCallback(self.startActualUpgrade, ChoiceBox, title=message, list=choices)
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
			if config.softwareupdate.autosettingsbackup.getValue() or config.softwareupdate.autoimagebackup.getValue():
				self.doAutoBackup()
			else:
				self.session.open(TryQuitMainloop,retvalue=42)
				self.close()

	def modificationCallback(self, res):
		self.ipkg.write(res and "N" or "Y")

	def doSettingsBackup(self):
		backup = None
		from Plugins.SystemPlugins.ViX.BackupManager import BackupFiles
		self.BackupFiles = BackupFiles(self.session)
		Components.Task.job_manager.AddJob(self.BackupFiles.createBackupJob())
		Components.Task.job_manager.in_background = False
		for job in Components.Task.job_manager.getPendingJobs():
			if job.name.startswith(_("Backup Manager")):
				backup = job
		if backup:
			self.showJobView(backup)

	def doImageBackup(self):
		backup = None
		from Plugins.SystemPlugins.ViX.ImageManager import ImageBackup
		self.ImageBackup = ImageBackup(self.session)
		Components.Task.job_manager.AddJob(self.ImageBackup.createBackupJob())
		Components.Task.job_manager.in_background = False
		for job in Components.Task.job_manager.getPendingJobs():
			if job.name.startswith(_("Image Manager")):
				backup = job
		if backup:
			self.showJobView(backup)

	def doAutoBackup(self, val = False):
		self.autobackuprunning = True
		if config.softwareupdate.autosettingsbackup.getValue() and not self.SettingsBackupDone:
			self.doSettingsBackup()
		elif config.softwareupdate.autoimagebackup.getValue() and not self.ImageBackupDone:
			self.doImageBackup()
		else:
			self.session.open(TryQuitMainloop,retvalue=42)
			self.close()

	def showJobView(self, job):
		if job.name.startswith(_("Image Manager")):
			self.ImageBackupDone = True
		elif job.name.startswith(_("Backup Manager")):
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
				self.session.openWithCallback(self.exitAnswer, MessageBox, _("Upgrade finished.") +" "+_("Do you want to reboot your STB_BOX?"))
			else:
				self.close()
		else:
			if not self.updating:
				self.close()

	def exitAnswer(self, result):
		if result is not None and result:
			self.session.open(TryQuitMainloop, retvalue=2)
		self.close()
