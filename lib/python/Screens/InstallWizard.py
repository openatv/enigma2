from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.config import config, ConfigSubsection, ConfigBoolean, getConfigListEntry, ConfigSelection, ConfigYesNo, ConfigIP
from Components.Network import iNetwork
from Components.Ipkg import IpkgComponent
from enigma import eDVBDB
import os
config.misc.installwizard = ConfigSubsection()
config.misc.installwizard.hasnetwork = ConfigBoolean(default = False)
config.misc.installwizard.ipkgloaded = ConfigBoolean(default = False)
config.misc.installwizard.channellistdownloaded = ConfigBoolean(default = False)
config.misc.installwizard.softcamdownloaded = ConfigBoolean(default = False)


class InstallWizard(Screen, ConfigListScreen):

	STATE_UPDATE = 0
	STATE_CHOISE_CHANNELLIST = 1
 	STATE_CHOISE_SOFTCAM = 2

	def __init__(self, session, args = None):
		Screen.__init__(self, session)

		self.index = args
		self.list = []
		ConfigListScreen.__init__(self, self.list)

		if self.index == self.STATE_UPDATE:
			config.misc.installwizard.hasnetwork.value = False
			config.misc.installwizard.ipkgloaded.value = False
			modes = {0: " "}
			self.enabled = ConfigSelection(choices = modes, default = 0)
			self.adapters = [(iNetwork.getFriendlyAdapterName(x),x) for x in iNetwork.getAdapterList()]
			is_found = False
			for x in self.adapters:
				if x[1] == 'eth0' or x[1] == 'eth1':
					if iNetwork.getAdapterAttribute(x[1], 'up'):
						self.ipConfigEntry = ConfigIP(default = iNetwork.getAdapterAttribute(x[1], "ip"))
						iNetwork.checkNetworkState(self.checkNetworkCB)
						if_found = True
					else:
						iNetwork.restartNetwork(self.checkNetworkLinkCB)
					break
			if is_found is False:
				self.createMenu()
		elif self.index == self.STATE_CHOISE_CHANNELLIST:
			self.enabled = ConfigYesNo(default = True)
			modes = {"e2-astra-hispasat-iplus": "Open+ default(Astra-Hispasat)", "e2-astra-comunitarias-iplus": "Astra Comunitarias", "e2-astra-hotbird-hispasat-iplus": "Astra Hotbird Hispasat", "e2-motor-iplus": "All-Motor", "e2-cuatro-sat-19-13-28-23e-iplus": "Cuatro SAT" }
			self.channellist_type = ConfigSelection(choices = modes, default = "e2-astra-hispasat-iplus")
			self.createMenu()
 		elif self.index == self.STATE_CHOISE_SOFTCAM:
 			self.enabled = ConfigYesNo(default = True)
 			modes = {"oscam": _("default") + " (oscam)", "CCcam": "sbox"}
 			self.softcam_type = ConfigSelection(choices = modes, default = "oscam")
 			self.createMenu()

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
		if self.index == self.STATE_UPDATE:
			if config.misc.installwizard.hasnetwork.value:
				self.list.append(getConfigListEntry(_("Your internet connection is working (ip: %s)") % (self.ipConfigEntry.getText()), self.enabled))
			else:
				self.list.append(getConfigListEntry(_("Your receiver does not have an internet connection"), self.enabled))
		elif self.index == self.STATE_CHOISE_CHANNELLIST:
			self.list.append(getConfigListEntry(_("Install channel list"), self.enabled))
			if self.enabled.value:
				self.list.append(getConfigListEntry(_("Channel list type"), self.channellist_type))
 		elif self.index == self.STATE_CHOISE_SOFTCAM:
 			self.list.append(getConfigListEntry(_("Install softcam"), self.enabled))
 			if self.enabled.value:
 				self.list.append(getConfigListEntry(_("Softcam type"), self.softcam_type))
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
		if self.index == self.STATE_UPDATE:
			if config.misc.installwizard.hasnetwork.value:
			        # Check if feed is active                                                                                                                  
			        if not os.path.isfile("/etc/opkg/lbappstore.conf"):                                                                                        
			                with open ('/etc/opkg/lbappstore.conf', 'a') as f: 
			                        f.write ("src/gz lbutils http://appstore.linux-box.es/files" + '\n')
			                        f.close()
			                	                      
				self.session.open(InstallWizardIpkgUpdater, self.index, _('Please wait (updating packages)'), IpkgComponent.CMD_UPDATE)
		elif self.index == self.STATE_CHOISE_CHANNELLIST and self.enabled.value:
			self.session.open(InstallWizardIpkgUpdater, self.index, _('Please wait (downloading channel list)'), IpkgComponent.CMD_INSTALL, {'package': 'enigma2-plugin-settings-sorys-' + self.channellist_type.value})
 		elif self.index == self.STATE_CHOISE_SOFTCAM and self.enabled.value:
 			self.session.open(InstallWizardIpkgUpdater, self.index, _('Please wait (downloading softcam)'), IpkgComponent.CMD_INSTALL, {'package': 'enigma2-plugin-lbcam-' + self.softcam_type.value})
		return


class InstallWizardIpkgUpdater(Screen):
	def __init__(self, session, index, info, cmd, pkg = None):
		Screen.__init__(self, session)

		self["statusbar"] = StaticText(info)

		self.pkg = pkg
		self.index = index
		self.state = 0

		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)

		if self.index == InstallWizard.STATE_CHOISE_CHANNELLIST:
			self.ipkg.startCmd(cmd, {'package': 'enigma2-plugin-settings-*'})
		elif self.index == InstallWizard.STATE_CHOISE_SOFTCAM:                                                                   
                        self.ipkg.startCmd(cmd, {'package': 'enigma2-plugin-lbcam-*'})
		else:
			self.ipkg.startCmd(cmd, pkg)

	def ipkgCallback(self, event, param):
		if event == IpkgComponent.EVENT_DONE:
			if self.index == InstallWizard.STATE_UPDATE:
				config.misc.installwizard.ipkgloaded.value = True
			elif self.index == InstallWizard.STATE_CHOISE_CHANNELLIST:
				if self.state == 0:
					self.ipkg.startCmd(IpkgComponent.CMD_INSTALL, self.pkg)
					self.state = 1
					return
				else:
					config.misc.installwizard.channellistdownloaded.value = True
					eDVBDB.getInstance().reloadBouquets()
					eDVBDB.getInstance().reloadServicelist()
			elif self.index == InstallWizard.STATE_CHOISE_SOFTCAM:  
			        if self.state == 0:                                                       
                        	        self.ipkg.startCmd(IpkgComponent.CMD_INSTALL, self.pkg)                                            
                        	        self.state = 1                                                                                     
                        	        return
                                else:
                                        config.misc.installwizard.softcamdownloaded.value = True                                                        
			self.close()
