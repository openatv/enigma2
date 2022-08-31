import os
from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.config import config, ConfigSubsection, ConfigBoolean, getConfigListEntry, ConfigSelection, ConfigYesNo, ConfigIP
from Components.Network import iNetwork
from Components.Opkg import OpkgComponent
from enigma import eDVBDB

config.misc.installwizard = ConfigSubsection()
config.misc.installwizard.hasnetwork = ConfigBoolean(default=False)
config.misc.installwizard.ipkgloaded = ConfigBoolean(default=False)
config.misc.installwizard.channellistdownloaded = ConfigBoolean(default=False)


class InstallWizard(Screen, ConfigListScreen):

	STATE_UPDATE = 0
	STATE_CHOISE_CHANNELLIST = 1
# 	STATE_CHOISE_SOFTCAM = 2

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
			self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getAdapterList()]
			is_found = False
			for x in self.adapters:
				if x[1] == 'eth0' or x[1] == 'eth1':
					if iNetwork.getAdapterAttribute(x[1], 'up'):
						self.ipConfigEntry = ConfigIP(default=iNetwork.getAdapterAttribute(x[1], "ip"))
						iNetwork.checkNetworkState(self.checkNetworkCB)
						if_found = True
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
		except:
			return
		self.list = []
		#if self.index == self.STATE_UPDATE:
		#	if config.misc.installwizard.hasnetwork.value:
		#		self.list.append(getConfigListEntry(_("Your Internet connection is working (ip: %s)") % (self.ipConfigEntry.getText()), self.enabled))
		#	else:
		#self.list.append(getConfigListEntry(_("Your receiver does not have an Internet connection"), self.enabled))
		if self.index == self.STATE_CHOISE_CHANNELLIST:
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
		if self.index == self.STATE_CHOISE_CHANNELLIST and self.enabled.value and self.channellist_type.value == "default":
			config.misc.installwizard.channellistdownloaded.value = True
			os.system("tar -xzf /etc/defaultsat.tar.gz -C /etc/enigma2")
			eDVBDB.getInstance().reloadServicelist()
			eDVBDB.getInstance().reloadBouquets()
		return
