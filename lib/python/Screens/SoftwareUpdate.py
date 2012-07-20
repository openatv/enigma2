from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop 
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Ipkg import IpkgComponent
from Components.Sources.StaticText import StaticText
from Components.Slider import Slider
from enigma import eTimer

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

		self.packages = 0
		self.error = 0
		self.processed_packages = []
		self.total_packages = None

		self.updating = False
		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)
		self.onClose.append(self.__close)

		self["actions"] = ActionMap(["WizardActions"], 
		{
			"ok": self.exit,
			"back": self.exit
		}, -1)
		
		self.activity = 0 
		self.activityTimer = eTimer()
		self.activityTimer.callback.append(self.checkTraficLight)
		self.activityTimer.callback.append(self.doActivityTimer)
		self.activityTimer.start(100, True)

	def checkTraficLight(self):
	
		self.activityTimer.callback.remove(self.checkTraficLight)
		self.activityTimer.start(100, False)

		from urllib import urlopen
		import socket
		import os
		currentTimeoutDefault = socket.getdefaulttimeout()
		socket.setdefaulttimeout(3)
		message = ""
		picon = None
		default = True
		try:
			if os.path.isfile("/proc/stb/info/boxtype"):
				boxType = open("/proc/stb/info/boxtype").read().strip().lower()
			elif os.path.isfile("/proc/stb/info/vumodel"):
				boxType = "vu" + open("/proc/stb/info/vumodel").read().strip().lower()
			elif os.path.isfile("/proc/stb/info/model"):
				boxType = open("/proc/stb/info/model").read().strip().lower()
			# TODO: Use Twisted's URL fetcher, urlopen is evil. And it can
			# run in parallel to the package update.
			if boxType in urlopen("http://openpli.org/status").read():
				message = _("The current beta image could not be stable") + "\n" + _("For more information see www.openpli.org") + "\n"
				picon = MessageBox.TYPE_ERROR
				default = False
		except:
			message = _("The status of the current beta image could not be checked because www.openpli.org could not be reached for some reason") + "\n"
			picon = MessageBox.TYPE_ERROR
			default = False
		socket.setdefaulttimeout(currentTimeoutDefault)
		if default:
		        self.startActualUpdate(True)
		else:
			message += _("Do you want to update your Dreambox?")+"\n"+_("After pressing OK, please wait!")
			self.session.openWithCallback(self.startActualUpdate, MessageBox, message, default = default, picon = picon)

	def startActualUpdate(self,answer):
		if answer:
			self.updating = True
			self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)
		else:
			self.close()

	def doActivityTimer(self):
		self.activity += 1
		if self.activity == 100:
			self.activity = 0
		self.activityslider.setValue(self.activity)

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
					_("A configuration file (%s) was modified since Installation.\nDo you want to keep your version?") % (param)
				)
		elif event == IpkgComponent.EVENT_ERROR:
			self.error += 1
		elif event == IpkgComponent.EVENT_DONE:
			if self.updating:
				self.updating = False
				self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE_LIST)
			elif self.ipkg.currentCommand == IpkgComponent.CMD_UPGRADE_LIST:
				self.total_packages = len(self.ipkg.getFetchedList())
				if self.total_packages:
					message = _("Do you want to update your Dreambox?") + "\n(%s " % self.total_packages + _("Packages") + ")"
					choices = [(_("Unattended upgrade without GUI and reboot system"), "cold"),
						(_("Upgrade and ask to reboot"), "hot"),
						(_("Cancel"), "")]
					self.session.openWithCallback(self.startActualUpgrade, ChoiceBox, title=message, list=choices)
				else:
				        self.session.openWithCallback(self.close, MessageBox, _("Nothing to upgrade"), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
			elif self.error == 0:
				self.slider.setValue(4)
				self.activityTimer.stop()
				self.activityslider.setValue(0)
				self.package.setText(_("Done - Installed or upgraded %d packages") % self.packages)
				self.status.setText(self.oktext)
			else:
				self.activityTimer.stop()
				self.activityslider.setValue(0)
				error = _("your dreambox might be unusable now. Please consult the manual for further assistance before rebooting your dreambox.")
				if self.packages == 0:
					error = _("No packages were upgraded yet. So you can check your network and try again.")
				if self.updating:
					error = _("Your dreambox isn't connected to the internet properly. Please check it and try again.")
				self.status.setText(_("Error") +  " - " + error)
		#print event, "-", param
		pass

	def startActualUpgrade(self, answer):
		if not answer or not answer[1]:
			self.close()
			return
		if answer[1] == "cold":
			self.session.open(TryQuitMainloop,retvalue=42)
			self.close()
		else:
			self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE, args = {'test_only': False})

	def modificationCallback(self, res):
		self.ipkg.write(res and "N" or "Y")

	def exit(self):
		if not self.ipkg.isRunning():
			if self.packages != 0 and self.error == 0:
				self.session.openWithCallback(self.exitAnswer, MessageBox, _("Upgrade finished.") +" "+_("Do you want to reboot your Dreambox?"))
			else:
				self.close()
		else:
			if not self.updating:
				self.close()

	def exitAnswer(self, result):
		if result is not None and result:
			self.session.open(TryQuitMainloop,retvalue=2)
		self.close()

	def __close(self):
		self.ipkg.removeCallback(self.ipkgCallback)