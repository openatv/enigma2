from os import system
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigBoolean, getConfigListEntry, ConfigSelection, ConfigYesNo, ConfigIP
from Components.Network import iNetwork
from Components.Opkg import OpkgComponent
from Components.Sources.StaticText import StaticText
from enigma import eDVBDB

config.misc.installwizard = ConfigSubsection()
config.misc.installwizard.hasnetwork = ConfigBoolean(default=False)
config.misc.installwizard.ipkgloaded = ConfigBoolean(default=False)
config.misc.installwizard.channellistdownloaded = ConfigBoolean(default=False)


class InstallWizard(Screen, ConfigListScreen):

	STATE_UPDATE = 0
	STATE_CHOISE_CHANNELLIST = 1

	def __init__(self, session, args=None):
		Screen.__init__(self, session)

		self.index = args
		self.list = []
		ConfigListScreen.__init__(self, self.list)

		if self.index == self.STATE_UPDATE:
			config.misc.installwizard.hasnetwork.value = False
			config.misc.installwizard.ipkgloaded.value = False
			modes = {0: " "}
			self.enabled = ConfigSelection(choices=modes, default=0)
			modes = {0: "Press OK to install"}
			self.cfgupdate = ConfigSelection(choices=modes, default=0)
			self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getAdapterList()]
			is_found = False
			for x in self.adapters:
				if x[1] in ("eth0", "eth1"):
					if iNetwork.getAdapterAttribute(x[1], "up"):
						self.ipConfigEntry = ConfigIP(default=iNetwork.getAdapterAttribute(x[1], "ip"))
						iNetwork.checkNetworkState(self.checkNetworkCB)
						is_found = True
					else:
						iNetwork.restartNetwork(self.checkNetworkLinkCB)
					break
			if is_found is False:
				self.createMenu()
		elif self.index == self.STATE_CHOISE_CHANNELLIST:
			self.enabled = ConfigYesNo(default=True)
			modes = {"default": _("default Astra (13e-19e)"), "none": _("none")}
			self.channellist_type = ConfigSelection(choices=modes, default="default")
			self.createMenu()
# 		elif self.index == self.STATE_CHOISE_SOFTCAM:
# 			self.enabled = ConfigYesNo(default = True)
# 			modes = {"cccam": _("default") + " (CCcam)", "scam": "scam"}
# 			self.softcam_type = ConfigSelection(choices = modes, default = "cccam")
# 			self.createMenu()

	def checkNetworkCB(self, data):
		if data < 3:
			config.misc.installwizard.hasnetwork.value = True
		self.createMenu()

	def checkNetworkLinkCB(self, retval):
		if retval:
			iNetwork.checkNetworkState(self.checkNetworkCB)
		else:
			self.createMenu()

	def createMenu(self):
		try:
			test = self.index
		except Exception:
			return
		self.list = []
		if self.index == self.STATE_UPDATE:
			if config.misc.installwizard.hasnetwork.value:
				self.list.append(getConfigListEntry(_("Your Internet connection is working (ip: %s)") % (self.ipConfigEntry.getText()), self.enabled))
				self.list.append(getConfigListEntry(_("There are pending tasks:"), self.cfgupdate))
			else:
				self.list.append(getConfigListEntry(_("Your receiver does not have an Internet connection"), self.enabled))
		elif self.index == self.STATE_CHOISE_CHANNELLIST:
#			self.list.append(getConfigListEntry(_("Install channel list"), self.enabled))
#			if self.enabled.value:
			self.list.append(getConfigListEntry(_("Channel list type"), self.channellist_type))
# 		elif self.index == self.STATE_CHOISE_SOFTCAM:
# 			self.list.append(getConfigListEntry(_("Install softcam"), self.enabled))
# 			if self.enabled.value:
# 				self.list.append(getConfigListEntry(_("Softcam type"), self.softcam_type))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keyLeft(self):
		if self.index == 0:
			return
		ConfigListScreen.keyLeft(self)
		self.createMenu()

	def keyRight(self):
		if self.index == 0:
			return
		ConfigListScreen.keyRight(self)
		self.createMenu()

	def run(self):
		if self.index == self.STATE_UPDATE and config.misc.installwizard.hasnetwork.value:
			self.session.open(InstallWizardSmallBox)
		if self.index == self.STATE_CHOISE_CHANNELLIST and self.enabled.value and self.channellist_type.value == "default":
			config.misc.installwizard.channellistdownloaded.value = True
			system("tar -xzf /etc/defaultsat.tar.gz -C /etc/enigma2")
			eDVBDB.getInstance().reloadServicelist()
			eDVBDB.getInstance().reloadBouquets()


class InstallWizardSmallBox(Screen):
	skin = """
	<screen name="InstallWizardSmallBox" position="center,center" size="520,185" resolution="1280,720">
		<widget source="Title" render="Label" position="65,8" size="520,0" font="Regular;22" transparent="1"/>
		<widget source="statusbar" render="Label" position="75,10" size="435,55" font="Regular;22" transparent="1"/>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Small Box Preparation"))
		self["statusbar"] = StaticText(_("Update package list please wait..."))
		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"cancel": self.close,
			"red": self.close,
			"green": self.close,
			"ok": self.close
		})

		self["actions"].setEnabled(False)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.opkg.startCmd(OpkgComponent.CMD_UPDATE)

	def opkgCallback(self, event, parameter):
		print("InstallWizard opkgCallback event:%s parameter:%s" % (event, parameter))
		if event == OpkgComponent.EVENT_ERROR:
			self["statusbar"].setText(_("Package installation failed"))
			self["actions"].setEnabled(True)
		elif event == OpkgComponent.EVENT_INSTALL:
			self["statusbar"].setText("%s: '%s'.\n" % (_("Installing"), parameter))
		elif event == OpkgComponent.EVENT_DOWNLOAD:
			self["statusbar"].setText("%s: '%s'.\n" % (_("Downloading"), parameter))
		elif event == OpkgComponent.EVENT_CONFIGURING:
			self["statusbar"].setText("%s: '%s'.\n" % (_("Configuring"), parameter))
		elif event == OpkgComponent.EVENT_DONE:
			if self.opkg.currentCommand == OpkgComponent.CMD_UPDATE:
				self["statusbar"].setText(_("Installing Please wait..."))
				self.opkg.startCmd(OpkgComponent.CMD_INSTALL, {"package": "packagegroup-openatv-small"})
			else:
				config.misc.installwizard.ipkgloaded.value = True
				self.opkg.removeCallback(self.opkgCallback)
				self.close()
