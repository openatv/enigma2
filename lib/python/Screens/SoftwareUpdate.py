from boxbranding import getImageVersion, getImageBuild, getMachineBrand, getMachineName, getBoxType

from enigma import eTimer, eDVBDB

from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.TextBox import TextBox
from Components.ActionMap import ActionMap
from Components.config import config
from Components.Console import Console
from Components.Ipkg import IpkgComponent
from Components.Sources.StaticText import StaticText
from Components.Slider import Slider
from Tools.BoundFunction import boundFunction

class SoftwareUpdateChangeView(TextBox):
	skin = """<screen name="SoftwareUpdateChangeView" backgroundColor="background" position="40,112" size="1200,550" title="Changes">
			<widget font="Console;18" name="text" position="8,4" size="1184,540"/>
		</screen>"""

class UpdatePlugin(Screen):
	def __init__(self, session, *args):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Software update"))

		self.setTitle(_("Software update"))
		self.slider = Slider(0, 100)
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

	def checkNetworkStateFinished(self, result, retval, extra_args=None):
		if 'bad address' in result:
			self.session.openWithCallback(self.close, MessageBox, _("Your %s %s is not connected to the Internet, please check your network settings and try again.") % (getMachineBrand(), getMachineName()), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif ('wget returned 1' or 'wget returned 255' or '404 Not Found') in result:
			self.session.openWithCallback(self.close, MessageBox, _("Can not retrieve data from feed server. Check your Internet connection and try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
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
		self.onClose.append(self.__close)

		self.updating = False

		self["actions"] = ActionMap(["WizardActions"], {
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
			self.package.setText(param.rpartition("/")[2].rstrip("."))
		elif event == IpkgComponent.EVENT_UPGRADE:
			self.slider.setValue(100 * self.packages / self.total_packages)
			self.package.setText(param)
			self.status.setText(_("Upgrading") + ": %s/%s" % (self.packages, self.total_packages))
			if param not in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == IpkgComponent.EVENT_INSTALL:
			self.package.setText(param)
			self.status.setText(_("Installing"))
			if param not in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == IpkgComponent.EVENT_REMOVE:
			self.package.setText(param)
			self.status.setText(_("Removing"))
			if param not in self.processed_packages:
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
				self.total_packages = None
				self.total_packages = len(self.ipkg.getFetchedList())
				message = _("Do you want to update your %s %s ?") % (getMachineBrand(), getMachineName()) + "\n(" + (ngettext("%s updated package available", "%s updated packages available", self.total_packages) % self.total_packages) + ")"
				if self.total_packages:
					config.softwareupdate.updatefound.setValue(True)
					choices = [
						(_("View the changes"), "showlist"),
						(_("Update and ask to reboot"), "hot"),
						# (_("Upgrade and reboot system"), "cold")
					]
					choices.append((_("Cancel"), ""))
					upgrademessage = self.session.openWithCallback(self.startActualUpgrade, ChoiceBox, title=message, list=choices, skin_name="SoftwareUpdateChoices")
					upgrademessage.setTitle(_('Software update'))
				else:
					upgrademessage = self.session.openWithCallback(self.close, MessageBox, _("Nothing to upgrade"), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
					upgrademessage.setTitle(_('Software update'))
			elif self.channellist_only > 0:
				if self.channellist_only == 1:
					self.setEndMessage(_("Could not find installed channel list."))
				elif self.channellist_only == 2:
					self.slider.setValue(33)
					self.ipkg.startCmd(IpkgComponent.CMD_REMOVE, {'package': self.channellist_name})
					self.channellist_only += 1
				elif self.channellist_only == 3:
					self.slider.setValue(66)
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
					error = _("Update failed. Your %s %s does not have a working Internet connection.") % (getMachineBrand(), getMachineName())
				self.status.setText(_("Error") + " - " + error)
		elif event == IpkgComponent.EVENT_LISTITEM:
			if 'enigma2-plugin-settings-' in param[0] and self.channellist_only > 0:
				self.channellist_name = param[0]
				self.channellist_only = 2
		#print event, "-", param
		pass

	def setEndMessage(self, txt):
		self.slider.setValue(100)
		self.activityTimer.stop()
		self.activityslider.setValue(0)
		self.package.setText(txt)
		self.status.setText(self.oktext)

	def startActualUpgrade(self, answer):
		if not answer or not answer[1]:
			self.close()
			return

		if answer[1] == "menu":
			message = _("Do you want to update your %s %s ?") % (getMachineBrand(), getMachineName()) + "\n(%s " % self.total_packages + _("Packages") + ")"
			choices = [
				(_("View the changes"), "showlist"),
				(_("Update and ask to reboot"), "hot"),
				# (_("Upgrade and reboot system"), "cold")
			]
			choices.append((_("Cancel"), ""))
			upgrademessage = self.session.openWithCallback(self.startActualUpgrade, ChoiceBox, title=message, list=choices, skin_name="SoftwareUpdateChoices")
			upgrademessage.setTitle(_('Software update'))
		elif answer[1] == "showlist":
			format = "%-38.38s %-32.32s %-32.32s\n"
			text = format % ("Package name", "Current version", "New version")
			spaces = "-" * 50
			text += format % (spaces, spaces, spaces)
			for i in sorted(self.ipkg.getFetchedList(), key=lambda d: d[0]):
				text += format % (i[0], i[1], i[2])
			self.session.openWithCallback(boundFunction(self.ipkgCallback, IpkgComponent.EVENT_DONE, None), SoftwareUpdateChangeView, text)
		elif answer[1] == "cold":
			self.session.open(TryQuitMainloop, retvalue=42)
			self.close()
		else:
			self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE, args={'test_only': False})

	def modificationCallback(self, res):
		self.ipkg.write(res and "N" or "Y")

	def exit(self):
		if not self.ipkg.isRunning():
			if self.packages != 0 and self.error == 0 and self.channellist_only == 0:
				self.session.openWithCallback(self.exitAnswer, MessageBox, _("Upgrade finished.") + " " + _("Do you want to reboot your %s %s") % (getMachineBrand(), getMachineName()))
			else:
				self.close()
		else:
			if not self.updating:
				self.close()

	def exitAnswer(self, result):
		if result is not None and result:
			self.session.open(TryQuitMainloop, retvalue=2)
		self.close()

	def __close(self):
		self.ipkg.removeCallback(self.ipkgCallback)
