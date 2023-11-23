from tarfile import TarError, TarFile

from enigma import eDVBDB

from Components.ActionMap import HelpableActionMap
from Components.ConfigList import ConfigListScreen
from Components.config import ConfigBoolean, ConfigIP, ConfigSelection, ConfigSubsection, ConfigYesNo, config
from Components.Network import iNetwork
from Components.Opkg import OpkgComponent
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen

config.misc.installwizard = ConfigSubsection()
config.misc.installwizard.hasnetwork = ConfigBoolean(default=False)
config.misc.installwizard.ipkgloaded = ConfigBoolean(default=False)
config.misc.installwizard.channellistdownloaded = ConfigBoolean(default=False)


class InstallWizard(Screen, ConfigListScreen):
	STATE_UPDATE = 0
	STATE_CHANNELLIST = 1
	STATE_SOFTCAM = 2

	def __init__(self, session, args=None):
		def checkNetworkCallback(data):
			if data < 3:
				config.misc.installwizard.hasnetwork.value = True
			self.createMenu()

		def checkNetworkLinkCallback(retVal):
			if retVal:
				iNetwork.checkNetworkState(checkNetworkCallback)
			else:
				self.createMenu()

		Screen.__init__(self, session)
		ConfigListScreen.__init__(self, [])
		self.mode = args
		match args:
			case self.STATE_UPDATE:
				config.misc.installwizard.hasnetwork.value = False
				config.misc.installwizard.ipkgloaded.value = False
				self.enabled = ConfigSelection(default=0, choices={0: " "})
				self.configUpdate = ConfigSelection(default=0, choices={0: "Press OK to install"})
				isFound = False
				for adapter in [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getAdapterList()]:
					if adapter[1] in ("eth0", "eth1"):
						if iNetwork.getAdapterAttribute(adapter[1], "up"):
							self.ipConfigEntry = ConfigIP(default=iNetwork.getAdapterAttribute(adapter[1], "ip"))
							iNetwork.checkNetworkState(checkNetworkCallback)
							isFound = True
						else:
							iNetwork.restartNetwork(checkNetworkLinkCallback)
						break
				if isFound is False:
					self.createMenu()
			case self.STATE_CHANNELLIST:
				self.enabled = ConfigYesNo(default=True)
				self.channellist_type = ConfigSelection(default="default", choices={
					"default": _("Default Astra (13e-19e)"),
					"none": _("None")
				})
				self.createMenu()
			# case self.STATE_SOFTCAM:
			# 	self.enabled = ConfigYesNo(default=True)
			# 	self.softcamType = ConfigSelection(default="cccam", choices={
			# 		"cccam": f"{_('Default')} (CCcam)",
			# 		"scam": "Scam"
			# 	})
			# 	self.createMenu()

	def createMenu(self):
		if hasattr(self, "mode"):
			self.configList = []
			match self.mode:
				case self.STATE_UPDATE:
					if config.misc.installwizard.hasnetwork.value:
						self.configList.append((_("Your Internet connection is working (IP: %s)") % (self.ipConfigEntry.getText()), self.enabled))
						self.configList.append((_("There are pending tasks:"), self.configUpdate))
					else:
						self.configList.append((_("Your receiver does not have an Internet connection"), self.enabled))
				case self.STATE_CHANNELLIST:
					# self.configList.append((_("Install channel list"), self.enabled))
					# if self.enabled.value:
					self.configList.append((_("Channel list type"), self.channellist_type))
				# case self.STATE_SOFTCAM:
				# 	self.configList.append((_("Install softcam"), self.enabled))
				# 	if self.enabled.value:
				# 		self.configList.append((_("Softcam type"), self.softcamType))
			self["config"].setList(self.configList)

	def keyLeft(self):
		if self.mode:
			ConfigListScreen.keyLeft(self)
			self.createMenu()

	def keyRight(self):
		if self.mode:
			ConfigListScreen.keyRight(self)
			self.createMenu()

	def run(self):
		if self.mode == self.STATE_UPDATE and config.misc.installwizard.hasnetwork.value:
			self.session.open(InstallWizardSmallBox)
		if self.mode == self.STATE_CHANNELLIST and self.enabled.value and self.channellist_type.value == "default":
			config.misc.installwizard.channellistdownloaded.value = True
			try:
				with TarFile.open("/etc/defaultsat.tar.gz") as tar:
					tar.extractall("/etc/enigma2")
			except TarError:
				pass
			eDVBDB.getInstance().reloadServicelist()
			eDVBDB.getInstance().reloadBouquets()


class InstallWizardSmallBox(Screen, HelpableScreen):
	skin = """
	<screen name="InstallWizardSmallBox" position="center,center" size="520,185" resolution="1280,720">
		<widget source="Title" render="Label" position="65,8" size="520,0" font="Regular;22" transparent="1"/>
		<widget source="status" render="Label" position="75,10" size="435,55" font="Regular;22" transparent="1"/>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setTitle(_("Small Box Preparation"))
		self["actions"] = HelpableActionMap(self, ["SelectCancelActions"], {
			"cancel": (self.close, _("Close the screen")),
			"select": (self.close, _("Close the screen"))
		}, prio=0, description=_("Small Box Preparation Actions"))
		self["actions"].setEnabled(False)
		self["status"] = StaticText(_("Updating package list."))
		self.opkgComponent = OpkgComponent()
		self.opkgComponent.addCallback(self.opkgCallback)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.opkgComponent.runCommand(self.opkgComponent.CMD_REFRESH_INSTALL, {"arguments": ["packagegroup-openatv-small"]})

	def opkgCallback(self, event, parameter):
		# print(f"[InstallWizard] opkgCallback DEBUG: event='{self.opkgComponent.getEventText(event)}', parameter='{parameter}'.")
		match event:
			case self.opkgComponent.EVENT_REFRESH_DONE:
				self["status"].setText(_("Installing package."))
			case self.opkgComponent.EVENT_ERROR:
				self["status"].setText(_("Package installation failed."))
				self["actions"].setEnabled(True)
			case self.opkgComponent.EVENT_INSTALL:
				self["status"].setText(f"{_('Installing')}: '{parameter}'.")
			case self.opkgComponent.EVENT_DOWNLOAD:
				self["status"].setText(f"{_('Downloading')}: '{parameter}'.")
			case self.opkgComponent.EVENT_CONFIGURING:
				self["status"].setText(f"{_('Configuring')}: '{parameter}'.")
			case self.opkgComponent.EVENT_DONE:
				config.misc.installwizard.ipkgloaded.value = True
				self.opkgComponent.removeCallback(self.opkgCallback)
				self.close()
