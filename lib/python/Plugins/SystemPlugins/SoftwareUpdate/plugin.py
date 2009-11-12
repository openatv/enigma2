from Components.ActionMap import ActionMap, NumberActionMap
from Components.GUIComponent import GUIComponent
from Components.Input import Input
from Components.Ipkg import IpkgComponent
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList
from Components.Slider import Slider
from Plugins.Plugin import PluginDescriptor
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from enigma import eTimer, quitMainloop, RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, eListbox, gFont
from os import popen

class UpdatePlugin(Screen):
	skin = """
		<screen name="UpdatePlugin" position="center,center" size="550,200" title="Software update" >
			<widget name="activityslider" position="0,0" size="550,5"  />
			<widget name="slider" position="0,150" size="550,30"  />
			<widget source="package" render="Label" position="10,30" size="540,20" font="Regular;18" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="status" render="Label" position="10,60" size="540,45" font="Regular;20" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
		</screen>"""
		
	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		
		self.sliderPackages = { "dreambox-dvb-modules": 1, "enigma2": 2, "tuxbox-image-info": 3 }
		
		self.slider = Slider(0, 4)
		self["slider"] = self.slider
		self.activityslider = Slider(0, 100)
		self["activityslider"] = self.activityslider
		self.status = StaticText(_("Upgrading Dreambox... Please wait"))
		self["status"] = self.status
		self.package = StaticText()
		self["package"] = self.package
		
		self.packages = 0
		self.error = 0
		
		self.activity = 0
		self.activityTimer = eTimer()
		self.activityTimer.callback.append(self.doActivityTimer)

		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)

		self["actions"] = ActionMap(["WizardActions"],
		{
			"ok": self.exit,
			"back": self.exit
		}, -1)

		self.firsttime = True
		self.onShown.append(self.confirmUpdate)

	def confirmUpdate(self):
		if self.firsttime:
			self.firsttime = False
			self.session.openWithCallback(self.confirmationResult, MessageBox, _("Do you want to upgrade?"))

	def confirmationResult(self, result):
		if not result:
			self.close()
		else:
			self.activityTimer.start(100, False)
			self.updating = True
			self.package.setText(_("Package list update"))
			self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)

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
			self.status.setText(_("Upgrading"))
			self.packages += 1
		elif event == IpkgComponent.EVENT_INSTALL:
			self.package.setText(param)
			self.status.setText(_("Installing"))
			self.packages += 1
		elif event == IpkgComponent.EVENT_CONFIGURING:
			self.package.setText(param)
			self.status.setText(_("Configuring"))
		elif event == IpkgComponent.EVENT_MODIFIED:
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
				self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE, args = {'test_only': False})
			elif self.error == 0:
				self.slider.setValue(4)
				
				self.activityTimer.stop()
				self.activityslider.setValue(0)
				
				self.package.setText("")
				self.status.setText(_("Done - Installed or upgraded %d packages") % self.packages)
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

	def modificationCallback(self, res):
		self.ipkg.write(res and "N" or "Y")

	def exit(self):
		if not self.ipkg.isRunning():
			if self.packages != 0 and self.error == 0:
				self.session.openWithCallback(self.exitAnswer, MessageBox, _("Upgrade finished. Do you want to reboot your Dreambox?"))
			else:
				self.close()
			
	def exitAnswer(self, result):
		if result is not None and result:
			quitMainloop(2)
		self.close()

def UpgradeMain(session, **kwargs):
	session.open(UpdatePlugin)

def Plugins(**kwargs):
	return PluginDescriptor(name="Softwareupdate", description=_("Updates your receiver's software"), icon="update.png", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=UpgradeMain)
