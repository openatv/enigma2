from Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox
from Screens.Standby import *
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.HelpMenu import HelpableScreen
from Components.Console import Console
from Components.Network import iNetwork
from Components.Sources.StaticText import StaticText
from Components.Sources.Boolean import Boolean
from Components.Sources.List import List
from Components.Label import Label,MultiColorLabel
from Components.ScrollLabel import ScrollLabel
from Components.Pixmap import Pixmap,MultiPixmap
from Components.MenuList import MenuList
from Components.config import config, ConfigYesNo, ConfigIP, NoSave, ConfigText, ConfigPassword, ConfigSelection, getConfigListEntry, ConfigNothing, ConfigNumber
from Components.ConfigList import ConfigListScreen
from Components.PluginComponent import plugins
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap
from Plugins.Plugin import PluginDescriptor
from enigma import eTimer, ePoint, eSize, RT_HALIGN_LEFT, eListboxPythonMultiContent, gFont
from os import remove, symlink, unlink, rename, chmod
from shutil import move
from re import compile as re_compile, search as re_search
import time

class NetworkAdapterSelection(Screen,HelpableScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		
		self.wlan_errortext = _("No working wireless network adapter found.\nPlease verify that you have attached a compatible WLAN device and your network is configured correctly.")
		self.lan_errortext = _("No working local network adapter found.\nPlease verify that you have attached a network cable and your network is configured correctly.")
		self.oktext = _("Press OK on your remote control to continue.")
		self.edittext = _("Press OK to edit the settings.")
		self.defaulttext = _("Press yellow to set this interface as default interface.")
		self.restartLanRef = None
		
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["introduction"] = StaticText(self.edittext)
		
		self.adapters = [(iNetwork.getFriendlyAdapterName(x),x) for x in iNetwork.getAdapterList()]
		
		if not self.adapters:
			self.onFirstExecBegin.append(self.NetworkFallback)
			
		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
			"cancel": (self.close, _("exit network interface list")),
			"ok": (self.okbuttonClick, _("select interface")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
			"red": (self.close, _("exit network interface list")),
			"green": (self.okbuttonClick, _("select interface")),
			"blue": (self.openNetworkWizard, _("Use the Networkwizard to configure selected network adapter")),
			})
		
		self["DefaultInterfaceAction"] = HelpableActionMap(self, "ColorActions",
			{
			"yellow": (self.setDefaultInterface, [_("Set interface as default Interface"),_("* Only available if more than one interface is active.")] ),
			})

		self.list = []
		self["list"] = List(self.list)
		self.updateList()

		if len(self.adapters) == 1:
			self.onFirstExecBegin.append(self.okbuttonClick)
		self.onClose.append(self.cleanup)

	def buildInterfaceList(self,iface,name,default,active ):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/div-h.png"))
		defaultpng = None
		activepng = None
		description = None
		interfacepng = None

		if iface in iNetwork.lan_interfaces:
			if active is True:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/network_wired-active.png"))
			elif active is False:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/network_wired-inactive.png"))
			else:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/network_wired.png"))
		elif iface in iNetwork.wlan_interfaces:
			if active is True:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/network_wireless-active.png"))
			elif active is False:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/network_wireless-inactive.png"))
			else:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/network_wireless.png"))

		num_configured_if = len(iNetwork.getConfiguredAdapters())
		if num_configured_if >= 2:
			if default is True:
				defaultpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/buttons/button_blue.png"))
			elif default is False:
				defaultpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/buttons/button_blue_off.png"))
		if active is True:
			activepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/lock_on.png"))
		elif active is False:
			activepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/lock_error.png"))
		
		description = iNetwork.getFriendlyAdapterDescription(iface)

		return((iface, name, description, interfacepng, defaultpng, activepng, divpng))	

	def updateList(self):
		self.list = []
		default_gw = None
		num_configured_if = len(iNetwork.getConfiguredAdapters())
		if num_configured_if >= 2:
			self["key_yellow"].setText(_("Default"))
			self["introduction"].setText(self.defaulttext)
			self["DefaultInterfaceAction"].setEnabled(True)
		else:
			self["key_yellow"].setText("")
			self["introduction"].setText(self.edittext)
			self["DefaultInterfaceAction"].setEnabled(False)

		if num_configured_if < 2 and fileExists("/etc/default_gw"):
			unlink("/etc/default_gw")
			
		if fileExists("/etc/default_gw"):
			fp = file('/etc/default_gw', 'r')
			result = fp.read()
			fp.close()
			default_gw = result
					
		if len(self.adapters) == 0: # no interface available => display only eth0
			self.list.append(self.buildInterfaceList("eth0",iNetwork.getFriendlyAdapterName('eth0'),True,True ))
		else:
			for x in self.adapters:
				if x[1] == default_gw:
					default_int = True
				else:
					default_int = False
				if iNetwork.getAdapterAttribute(x[1], 'up') is True:
					active_int = True
				else:
					active_int = False
				self.list.append(self.buildInterfaceList(x[1],_(x[0]),default_int,active_int ))
		
		if fileExists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
			self["key_blue"].setText(_("NetworkWizard"))
		self["list"].setList(self.list)

	def setDefaultInterface(self):
		selection = self["list"].getCurrent()
		num_if = len(self.list)
		old_default_gw = None
		num_configured_if = len(iNetwork.getConfiguredAdapters())
		if fileExists("/etc/default_gw"):
			fp = open('/etc/default_gw', 'r')
			old_default_gw = fp.read()
			fp.close()
		if num_configured_if > 1 and (not old_default_gw or old_default_gw != selection[0]):
			fp = open('/etc/default_gw', 'w+')
			fp.write(selection[0])
			fp.close()
			self.restartLan()
		elif old_default_gw and num_configured_if < 2:
			unlink("/etc/default_gw")
			self.restartLan()

	def okbuttonClick(self):
		selection = self["list"].getCurrent()
		if selection is not None:
			self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetupConfiguration, selection[0])

	def AdapterSetupClosed(self, *ret):
		if len(self.adapters) == 1:
			self.close()
		else:
			self.updateList()

	def NetworkFallback(self):
		if 'wlan0' in iNetwork.configuredNetworkAdapters:
			self.session.openWithCallback(self.ErrorMessageClosed, MessageBox, self.wlan_errortext, type = MessageBox.TYPE_INFO,timeout = 10)
		if 'ath0' in iNetwork.configuredNetworkAdapters:
			self.session.openWithCallback(self.ErrorMessageClosed, MessageBox, self.wlan_errortext, type = MessageBox.TYPE_INFO,timeout = 10)
		else:
			self.session.openWithCallback(self.ErrorMessageClosed, MessageBox, self.lan_errortext, type = MessageBox.TYPE_INFO,timeout = 10)

	def ErrorMessageClosed(self, *ret):
		if 'wlan0' in iNetwork.configuredNetworkAdapters:
			self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetupConfiguration, 'wlan0')
		elif 'ath0' in iNetwork.configuredNetworkAdapters:
			self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetupConfiguration, 'ath0')
		else:
			self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetupConfiguration, 'eth0')

	def cleanup(self):
		iNetwork.stopLinkStateConsole()
		iNetwork.stopRestartConsole()
		iNetwork.stopGetInterfacesConsole()

	def restartLan(self):
		iNetwork.restartNetwork(self.restartLanDataAvail)
		self.restartLanRef = self.session.openWithCallback(self.restartfinishedCB, MessageBox, _("Please wait while we configure your network..."), type = MessageBox.TYPE_INFO, enable_input = False)
			
	def restartLanDataAvail(self, data):
		if data is True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data is True:
			self.restartLanRef.close(True)

	def restartfinishedCB(self,data):
		if data is True:
			self.updateList()
			self.session.open(MessageBox, _("Finished configuring your network"), type = MessageBox.TYPE_INFO, timeout = 10, default = False)

	def openNetworkWizard(self):
		if fileExists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
			try:
				from Plugins.SystemPlugins.NetworkWizard.NetworkWizard import NetworkWizard
			except ImportError:
				self.session.open(MessageBox, _("The NetworkWizard extension is not installed!\nPlease install it."), type = MessageBox.TYPE_INFO,timeout = 10 )
			else:
				selection = self["list"].getCurrent()
				if selection is not None:
					self.session.openWithCallback(self.AdapterSetupClosed, NetworkWizard, selection[0])


class NameserverSetup(Screen, ConfigListScreen, HelpableScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.backupNameserverList = iNetwork.getNameserverList()[:]
		print "backup-list:", self.backupNameserverList
		
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Add"))
		self["key_yellow"] = StaticText(_("Delete"))

		self["introduction"] = StaticText(_("Press OK to activate the settings."))
		self.createConfig()

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
			"cancel": (self.cancel, _("exit nameserver configuration")),
			"ok": (self.ok, _("activate current configuration")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
			"red": (self.cancel, _("exit nameserver configuration")),
			"green": (self.add, _("add a nameserver entry")),
			"yellow": (self.remove, _("remove a nameserver entry")),
			})

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.ok,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.createSetup()
		
	def createConfig(self):
		self.nameservers = iNetwork.getNameserverList()
		self.nameserverEntries = [ NoSave(ConfigIP(default=nameserver)) for nameserver in self.nameservers]

	def createSetup(self):
		self.list = []

		i = 1
		for x in self.nameserverEntries:
			self.list.append(getConfigListEntry(_("Nameserver %d") % (i), x))
			i += 1

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def ok(self):
		iNetwork.clearNameservers()
		for nameserver in self.nameserverEntries:
			iNetwork.addNameserver(nameserver.value)
		iNetwork.writeNameserverConfig()
		self.close()

	def run(self):
		self.ok()

	def cancel(self):
		iNetwork.clearNameservers()
		print "backup-list:", self.backupNameserverList
		for nameserver in self.backupNameserverList:
			iNetwork.addNameserver(nameserver)
		self.close()

	def add(self):
		iNetwork.addNameserver([0,0,0,0])
		self.createConfig()
		self.createSetup()

	def remove(self):
		print "currentIndex:", self["config"].getCurrentIndex()
		index = self["config"].getCurrentIndex()
		if index < len(self.nameservers):
			iNetwork.removeNameserver(self.nameservers[index])
			self.createConfig()
			self.createSetup()


class AdapterSetup(Screen, ConfigListScreen, HelpableScreen):
	def __init__(self, session, networkinfo, essid=None, aplist=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.session = session
		if isinstance(networkinfo, (list, tuple)):
			self.iface = networkinfo[0]
			self.essid = networkinfo[1]
			self.aplist = networkinfo[2]
		else:
			self.iface = networkinfo
			self.essid = essid
			self.aplist = aplist
		self.extended = None
		self.applyConfigRef = None
		self.finished_cb = None
		self.oktext = _("Press OK on your remote control to continue.")
		self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")

		self.createConfig()

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
			"cancel": (self.keyCancel, _("exit network adapter configuration")),
			"ok": (self.keySave, _("activate network adapter configuration")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
			"red": (self.keyCancel, _("exit network adapter configuration")),
			"blue": (self.KeyBlue, _("open nameserver configuration")),
			})

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.keySave,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list,session = self.session)
		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.cleanup)

		self["DNS1text"] = StaticText(_("Primary DNS"))
		self["DNS2text"] = StaticText(_("Secondary DNS"))
		self["DNS1"] = StaticText()
		self["DNS2"] = StaticText()
		self["introduction"] = StaticText(_("Current settings:"))

		self["IPtext"] = StaticText(_("IP Address"))
		self["Netmasktext"] = StaticText(_("Netmask"))
		self["Gatewaytext"] = StaticText(_("Gateway"))

		self["IP"] = StaticText()
		self["Mask"] = StaticText()
		self["Gateway"] = StaticText()

		self["Adaptertext"] = StaticText(_("Network:"))
		self["Adapter"] = StaticText()
		self["introduction2"] = StaticText(_("Press OK to activate the settings."))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_blue"] = StaticText(_("Edit DNS"))

		self["VKeyIcon"] = Boolean(False)
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		
	def layoutFinished(self):
		self["DNS1"].setText(self.primaryDNS.getText())
		self["DNS2"].setText(self.secondaryDNS.getText())
		if self.ipConfigEntry.getText() is not None:
			if self.ipConfigEntry.getText() == "0.0.0.0":
				self["IP"].setText(_("N/A"))
			else:	
				self["IP"].setText(self.ipConfigEntry.getText())
		else:
			self["IP"].setText(_("N/A"))
		if self.netmaskConfigEntry.getText() is not None:
			if self.netmaskConfigEntry.getText() == "0.0.0.0":
					self["Mask"].setText(_("N/A"))
			else:	
				self["Mask"].setText(self.netmaskConfigEntry.getText())
		else:
			self["IP"].setText(_("N/A"))			
		if iNetwork.getAdapterAttribute(self.iface, "gateway"):
			if self.gatewayConfigEntry.getText() == "0.0.0.0":
				self["Gatewaytext"].setText(_("Gateway"))
				self["Gateway"].setText(_("N/A"))
			else:
				self["Gatewaytext"].setText(_("Gateway"))
				self["Gateway"].setText(self.gatewayConfigEntry.getText())
		else:
			self["Gateway"].setText("")
			self["Gatewaytext"].setText("")
		self["Adapter"].setText(iNetwork.getFriendlyAdapterName(self.iface))

	def createConfig(self):
		self.InterfaceEntry = None
		self.dhcpEntry = None
		self.gatewayEntry = None
		self.hiddenSSID = None
		self.wlanSSID = None
		self.encryptionEnabled = None
		self.encryptionKey = None
		self.encryptionType = None
		self.nwlist = None
		self.encryptionlist = None
		self.weplist = None
		self.wsconfig = None
		self.default = None

		if self.iface in iNetwork.wlan_interfaces:
			from Plugins.SystemPlugins.WirelessLan.Wlan import wpaSupplicant,Wlan
			self.w = Wlan(self.iface)
			self.ws = wpaSupplicant()
			self.encryptionlist = []
			self.encryptionlist.append(("WEP", _("WEP")))
			self.encryptionlist.append(("WPA", _("WPA")))
			self.encryptionlist.append(("WPA2", _("WPA2")))
			self.encryptionlist.append(("WPA/WPA2", _("WPA or WPA2")))
			self.weplist = []
			self.weplist.append("ASCII")
			self.weplist.append("HEX")
			if self.aplist is not None:
				self.nwlist = self.aplist
				self.nwlist.sort(key = lambda x: x[0])
			else:
				self.nwlist = []
				self.aps = None
				try:
					self.aps = self.w.getNetworkList()
					if self.aps is not None:
						for ap in self.aps:
							a = self.aps[ap]
							if a['active']:
								if a['essid'] != '':
									self.nwlist.append((a['essid'],a['essid']))
					self.nwlist.sort(key = lambda x: x[0])
				except:
					self.nwlist.append(("No Networks found",_("No Networks found")))

			self.wsconfig = self.ws.loadConfig()
			if self.essid is not None: # ssid from wlan scan
				self.default = self.essid
			else:
				self.default = self.wsconfig['ssid']

			if "hidden..." not in self.nwlist:
				self.nwlist.append(("hidden...",_("enter hidden network SSID")))
			if self.default not in self.nwlist:
				self.nwlist.append((self.default,self.default))
			config.plugins.wlan.essid = NoSave(ConfigSelection(self.nwlist, default = self.default ))
			config.plugins.wlan.hiddenessid = NoSave(ConfigText(default = self.wsconfig['hiddenessid'], visible_width = 50, fixed_size = False))

			config.plugins.wlan.encryption.enabled = NoSave(ConfigYesNo(default = self.wsconfig['encryption'] ))
			config.plugins.wlan.encryption.type = NoSave(ConfigSelection(self.encryptionlist, default = self.wsconfig['encryption_type'] ))
			config.plugins.wlan.encryption.wepkeytype = NoSave(ConfigSelection(self.weplist, default = self.wsconfig['encryption_wepkeytype'] ))
			config.plugins.wlan.encryption.psk = NoSave(ConfigPassword(default = self.wsconfig['key'], visible_width = 50, fixed_size = False))

		self.activateInterfaceEntry = NoSave(ConfigYesNo(default=iNetwork.getAdapterAttribute(self.iface, "up") or False))
		self.dhcpConfigEntry = NoSave(ConfigYesNo(default=iNetwork.getAdapterAttribute(self.iface, "dhcp") or False))
		self.ipConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "ip")) or [0,0,0,0])
		self.netmaskConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "netmask") or [255,0,0,0]))
		if iNetwork.getAdapterAttribute(self.iface, "gateway"):
			self.dhcpdefault=True
		else:
			self.dhcpdefault=False
		self.hasGatewayConfigEntry = NoSave(ConfigYesNo(default=self.dhcpdefault or False))
		self.gatewayConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "gateway") or [0,0,0,0]))
		nameserver = (iNetwork.getNameserverList() + [[0,0,0,0]] * 2)[0:2]
		self.primaryDNS = NoSave(ConfigIP(default=nameserver[0]))
		self.secondaryDNS = NoSave(ConfigIP(default=nameserver[1]))

	def createSetup(self):
		self.list = []
		self.InterfaceEntry = getConfigListEntry(_("Use Interface"), self.activateInterfaceEntry)

		self.list.append(self.InterfaceEntry)
		if self.activateInterfaceEntry.value:
			self.dhcpEntry = getConfigListEntry(_("Use DHCP"), self.dhcpConfigEntry)
			self.list.append(self.dhcpEntry)
			if not self.dhcpConfigEntry.value:
				self.list.append(getConfigListEntry(_('IP Address'), self.ipConfigEntry))
				self.list.append(getConfigListEntry(_('Netmask'), self.netmaskConfigEntry))
				self.gatewayEntry = getConfigListEntry(_('Use a gateway'), self.hasGatewayConfigEntry)
				self.list.append(self.gatewayEntry)
				if self.hasGatewayConfigEntry.value:
					self.list.append(getConfigListEntry(_('Gateway'), self.gatewayConfigEntry))

			self.extended = None
			for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKSETUP):
				callFnc = p.__call__["ifaceSupported"](self.iface)
				if callFnc is not None:
					if p.__call__.has_key("WlanPluginEntry"): # internally used only for WLAN Plugin
						self.extended = callFnc
						if p.__call__.has_key("configStrings"):
							self.configStrings = p.__call__["configStrings"]
						else:
							self.configStrings = None
						if config.plugins.wlan.essid.value == 'hidden...':
							self.wlanSSID = getConfigListEntry(_("Network SSID"), config.plugins.wlan.essid)
							self.list.append(self.wlanSSID)
							self.hiddenSSID = getConfigListEntry(_("Hidden network SSID"), config.plugins.wlan.hiddenessid)
							self.list.append(self.hiddenSSID)
						else:
							self.wlanSSID = getConfigListEntry(_("Network SSID"), config.plugins.wlan.essid)
							self.list.append(self.wlanSSID)
						self.encryptionEnabled = getConfigListEntry(_("Encryption"), config.plugins.wlan.encryption.enabled)
						self.list.append(self.encryptionEnabled)
						
						if config.plugins.wlan.encryption.enabled.value:
							self.encryptionType = getConfigListEntry(_("Encryption Type"), config.plugins.wlan.encryption.type)
							self.list.append(self.encryptionType)
							if config.plugins.wlan.encryption.type.value == 'WEP':
								self.list.append(getConfigListEntry(_("Encryption Keytype"), config.plugins.wlan.encryption.wepkeytype))
								self.encryptionKey = getConfigListEntry(_("Encryption Key"), config.plugins.wlan.encryption.psk)
								self.list.append(self.encryptionKey)
							else:
								self.encryptionKey = getConfigListEntry(_("Encryption Key"), config.plugins.wlan.encryption.psk)
								self.list.append(self.encryptionKey)

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def KeyBlue(self):
		self.session.openWithCallback(self.NameserverSetupClosed, NameserverSetup)

	def newConfig(self):
		if self["config"].getCurrent() == self.InterfaceEntry:
			self.createSetup()
		if self["config"].getCurrent() == self.dhcpEntry:
			self.createSetup()
		if self["config"].getCurrent() == self.gatewayEntry:
			self.createSetup()
		if self.iface in iNetwork.wlan_interfaces:
			if self["config"].getCurrent() == self.wlanSSID:
				self.createSetup()
			if self["config"].getCurrent() == self.encryptionEnabled:
				self.createSetup()
			if self["config"].getCurrent() == self.encryptionType:
				self.createSetup()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()
	
	def keySave(self):
		self.hideInputHelp()
		if self["config"].isChanged():
			self.session.openWithCallback(self.keySaveConfirm, MessageBox, (_("Are you sure you want to activate this network configuration?\n\n") + self.oktext ) )
		else:
			if self.finished_cb:
				self.finished_cb()
			else:
				self.close('cancel')

	def keySaveConfirm(self, ret = False):
		if (ret == True):		
			num_configured_if = len(iNetwork.getConfiguredAdapters())
			if num_configured_if >= 1:
				if num_configured_if == 1 and self.iface in iNetwork.getConfiguredAdapters():
					self.applyConfig(True)
				else:
					self.session.openWithCallback(self.secondIfaceFoundCB, MessageBox, _("A second configured interface has been found.\n\nDo you want to disable the second network interface?"), default = True)
			else:
				self.applyConfig(True)
		else:
			self.keyCancel()		

	def secondIfaceFoundCB(self,data):
		if data is False:
			self.applyConfig(True)
		else:
			configuredInterfaces = iNetwork.getConfiguredAdapters()
			for interface in configuredInterfaces:
				if interface == self.iface:
					continue
				iNetwork.setAdapterAttribute(interface, "up", False)
				iNetwork.deactivateInterface(interface)
				self.applyConfig(True)

	def applyConfig(self, ret = False):
		if (ret == True):
			iNetwork.setAdapterAttribute(self.iface, "up", self.activateInterfaceEntry.value)
			iNetwork.setAdapterAttribute(self.iface, "dhcp", self.dhcpConfigEntry.value)
			iNetwork.setAdapterAttribute(self.iface, "ip", self.ipConfigEntry.value)
			iNetwork.setAdapterAttribute(self.iface, "netmask", self.netmaskConfigEntry.value)
			if self.hasGatewayConfigEntry.value:
				iNetwork.setAdapterAttribute(self.iface, "gateway", self.gatewayConfigEntry.value)
			else:
				iNetwork.removeAdapterAttribute(self.iface, "gateway")
			if self.extended is not None and self.configStrings is not None:
				iNetwork.setAdapterAttribute(self.iface, "configStrings", self.configStrings(self.iface))
				self.ws.writeConfig()
			if self.activateInterfaceEntry.value is False:
				iNetwork.deactivateInterface(self.iface)
			iNetwork.writeNetworkConfig()
			iNetwork.restartNetwork(self.applyConfigDataAvail)
			self.applyConfigRef = self.session.openWithCallback(self.applyConfigfinishedCB, MessageBox, _("Please wait for activation of your network configuration..."), type = MessageBox.TYPE_INFO, enable_input = False)
		else:
			self.keyCancel()

	def applyConfigDataAvail(self, data):
		if data is True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data is True:
			self.applyConfigRef.close(True)

	def applyConfigfinishedCB(self,data):
		if data is True:
			if self.finished_cb:
				self.session.openWithCallback(lambda x : self.finished_cb(), MessageBox, _("Your network configuration has been activated."), type = MessageBox.TYPE_INFO, timeout = 10)
			else:
				self.session.openWithCallback(self.ConfigfinishedCB, MessageBox, _("Your network configuration has been activated."), type = MessageBox.TYPE_INFO, timeout = 10)

	def ConfigfinishedCB(self,data):
		if data is not None:
			if data is True:
				self.close('ok')

	def keyCancelConfirm(self, result):
		if not result:
			return
		if self.oldInterfaceState is False:
			iNetwork.deactivateInterface(self.iface,self.keyCancelCB)
		else:
			self.close('cancel')

	def keyCancel(self):
		self.hideInputHelp()
		if self["config"].isChanged():
			self.session.openWithCallback(self.keyCancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close('cancel')

	def keyCancelCB(self,data):
		if data is not None:
			if data is True:
				self.close('cancel')

	def runAsync(self, finished_cb):
		self.finished_cb = finished_cb
		self.keySave()

	def NameserverSetupClosed(self, *ret):
		iNetwork.loadNameserverConfig()
		nameserver = (iNetwork.getNameserverList() + [[0,0,0,0]] * 2)[0:2]
		self.primaryDNS = NoSave(ConfigIP(default=nameserver[0]))
		self.secondaryDNS = NoSave(ConfigIP(default=nameserver[1]))
		self.createSetup()
		self.layoutFinished()

	def cleanup(self):
		iNetwork.stopLinkStateConsole()
		
	def hideInputHelp(self):
		current = self["config"].getCurrent()
		if current == self.hiddenSSID and config.plugins.wlan.essid.value == 'hidden...':
			if current[1].help_window.instance is not None:
				current[1].help_window.instance.hide()
		elif current == self.encryptionKey and config.plugins.wlan.encryption.enabled.value:
			if current[1].help_window.instance is not None:
				current[1].help_window.instance.hide()


class AdapterSetupConfiguration(Screen, HelpableScreen):
	def __init__(self, session,iface):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.session = session
		self.iface = iface
		self.restartLanRef = None
		self.LinkState = None
		self.mainmenu = self.genMainMenu()
		self["menulist"] = MenuList(self.mainmenu)
		self["key_red"] = StaticText(_("Close"))
		self["description"] = StaticText()
		self["IFtext"] = StaticText()
		self["IF"] = StaticText()
		self["Statustext"] = StaticText()
		self["statuspic"] = MultiPixmap()
		self["statuspic"].hide()
		
		self.oktext = _("Press OK on your remote control to continue.")
		self.reboottext = _("Your Dreambox will restart after pressing OK on your remote control.")
		self.errortext = _("No working wireless network interface found.\n Please verify that you have attached a compatible WLAN device or enable your local network interface.")	
		
		self["WizardActions"] = HelpableActionMap(self, "DirectionActions",
			{
			"up": (self.up, _("move up to previous entry")),
			"down": (self.down, _("move down to next entry")),
			"left": (self.left, _("move up to first entry")),
			"right": (self.right, _("move down to last entry")),
			})
		
		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
			"cancel": (self.close, _("exit networkadapter setup menu")),
			"ok": (self.ok, _("select menu entry")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
			"red": (self.close, _("exit networkadapter setup menu")),	
			})

		self["actions"] = NumberActionMap(["WizardActions", "DirectionActions" ,"ShortcutActions"],
		{
			"ok": self.ok,
			"back": self.close,
			"up": self.up,
			"down": self.down,
			"red": self.close,
			"left": self.left,
			"right": self.right,
		}, -2)
		
		self.updateStatusbar()
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.cleanup)

	def ok(self):
		self.cleanup()
		if self["menulist"].getCurrent()[1] == 'edit':
			if self.iface in iNetwork.wlan_interfaces:
				try:
					from Plugins.SystemPlugins.WirelessLan.plugin import WlanScan
					from pythonwifi.iwlibs import Wireless
				except ImportError:
					self.session.open(MessageBox, _("The wireless LAN plugin is not installed!\nPlease install it."), type = MessageBox.TYPE_INFO,timeout = 10 )
				else:
					ifobj = Wireless(self.iface) # a Wireless NIC Object
					try:
						self.wlanresponse = ifobj.getAPaddr()
					except IOError:
						self.wlanresponse = ifobj.getStatistics()
					if self.wlanresponse:
						if self.wlanresponse[0] not in (19,95): # 19 = 'No such device', 95 = 'Operation not supported'
							self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup,self.iface)
						else:
							# Display Wlan not available Message
							self.showErrorMessage()
					else:
						# Display Wlan not available Message
						self.showErrorMessage()
			else:
				self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup,self.iface)
		if self["menulist"].getCurrent()[1] == 'test':
			self.session.open(NetworkAdapterTest,self.iface)
		if self["menulist"].getCurrent()[1] == 'dns':
			self.session.open(NameserverSetup)
		if self["menulist"].getCurrent()[1] == 'scanwlan':
			try:
				from Plugins.SystemPlugins.WirelessLan.plugin import WlanScan
				from pythonwifi.iwlibs import Wireless
			except ImportError:
				self.session.open(MessageBox, _("The wireless LAN plugin is not installed!\nPlease install it."), type = MessageBox.TYPE_INFO,timeout = 10 )
			else:
				ifobj = Wireless(self.iface) # a Wireless NIC Object
				try:
					self.wlanresponse = ifobj.getAPaddr()
				except IOError:
					self.wlanresponse = ifobj.getStatistics()
				if self.wlanresponse:
					if self.wlanresponse[0] not in (19,95): # 19 = 'No such device', 95 = 'Operation not supported'
						self.session.openWithCallback(self.WlanScanClosed, WlanScan, self.iface)
					else:
						# Display Wlan not available Message
						self.showErrorMessage()
				else:
					# Display Wlan not available Message
					self.showErrorMessage()
		if self["menulist"].getCurrent()[1] == 'wlanstatus':
			try:
				from Plugins.SystemPlugins.WirelessLan.plugin import WlanStatus
				from pythonwifi.iwlibs import Wireless
			except ImportError:
				self.session.open(MessageBox, _("The wireless LAN plugin is not installed!\nPlease install it."), type = MessageBox.TYPE_INFO,timeout = 10 )
			else:	
				ifobj = Wireless(self.iface) # a Wireless NIC Object
				try:
					self.wlanresponse = ifobj.getAPaddr()
				except IOError:
					self.wlanresponse = ifobj.getStatistics()
				if self.wlanresponse:
					if self.wlanresponse[0] not in (19,95): # 19 = 'No such device', 95 = 'Operation not supported'
						self.session.openWithCallback(self.WlanStatusClosed, WlanStatus,self.iface)
					else:
						# Display Wlan not available Message
						self.showErrorMessage()
				else:
					# Display Wlan not available Message
					self.showErrorMessage()
		if self["menulist"].getCurrent()[1] == 'lanrestart':
			self.session.openWithCallback(self.restartLan, MessageBox, (_("Are you sure you want to restart your network interfaces?\n\n") + self.oktext ) )
		if self["menulist"].getCurrent()[1] == 'openwizard':
			from Plugins.SystemPlugins.NetworkWizard.NetworkWizard import NetworkWizard
			self.session.openWithCallback(self.AdapterSetupClosed, NetworkWizard, self.iface)
		if self["menulist"].getCurrent()[1][0] == 'extendedSetup':
			self.extended = self["menulist"].getCurrent()[1][2]
			self.extended(self.session, self.iface)
	
	def up(self):
		self["menulist"].up()
		self.loadDescription()

	def down(self):
		self["menulist"].down()
		self.loadDescription()

	def left(self):
		self["menulist"].pageUp()
		self.loadDescription()

	def right(self):
		self["menulist"].pageDown()
		self.loadDescription()

	def layoutFinished(self):
		idx = 0
		self["menulist"].moveToIndex(idx)
		self.loadDescription()

	def loadDescription(self):
		if self["menulist"].getCurrent()[1] == 'edit':
			self["description"].setText(_("Edit the network configuration of your Dreambox.\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'test':
			self["description"].setText(_("Test the network configuration of your Dreambox.\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'dns':
			self["description"].setText(_("Edit the Nameserver configuration of your Dreambox.\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'scanwlan':
			self["description"].setText(_("Scan your network for wireless access points and connect to them using your selected wireless device.\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'wlanstatus':
			self["description"].setText(_("Shows the state of your wireless LAN connection.\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'lanrestart':
			self["description"].setText(_("Restart your network connection and interfaces.\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'openwizard':
			self["description"].setText(_("Use the Networkwizard to configure your Network\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1][0] == 'extendedSetup':
			self["description"].setText(_(self["menulist"].getCurrent()[1][1]) + self.oktext )
		
	def updateStatusbar(self, data = None):
		self.mainmenu = self.genMainMenu()
		self["menulist"].l.setList(self.mainmenu)
		self["IFtext"].setText(_("Network:"))
		self["IF"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		self["Statustext"].setText(_("Link:"))
		
		if self.iface in iNetwork.wlan_interfaces:
			try:
				from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
			except:
				self["statuspic"].setPixmapNum(1)
				self["statuspic"].show()
			else:
				iStatus.getDataForInterface(self.iface,self.getInfoCB)
		else:
			iNetwork.getLinkState(self.iface,self.dataAvail)

	def doNothing(self):
		pass

	def genMainMenu(self):
		menu = []
		menu.append((_("Adapter settings"), "edit"))
		menu.append((_("Nameserver settings"), "dns"))
		menu.append((_("Network test"), "test"))
		menu.append((_("Restart network"), "lanrestart"))

		self.extended = None
		self.extendedSetup = None		
		for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKSETUP):
			callFnc = p.__call__["ifaceSupported"](self.iface)
			if callFnc is not None:
				self.extended = callFnc
				if p.__call__.has_key("WlanPluginEntry"): # internally used only for WLAN Plugin
					menu.append((_("Scan Wireless Networks"), "scanwlan"))
					if iNetwork.getAdapterAttribute(self.iface, "up"):
						menu.append((_("Show WLAN Status"), "wlanstatus"))
				else:
					if p.__call__.has_key("menuEntryName"):
						menuEntryName = p.__call__["menuEntryName"](self.iface)
					else:
						menuEntryName = _('Extended Setup...')
					if p.__call__.has_key("menuEntryDescription"):
						menuEntryDescription = p.__call__["menuEntryDescription"](self.iface)
					else:
						menuEntryDescription = _('Extended Networksetup Plugin...')
					self.extendedSetup = ('extendedSetup',menuEntryDescription, self.extended)
					menu.append((menuEntryName,self.extendedSetup))					
			
		if fileExists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
			menu.append((_("NetworkWizard"), "openwizard"))

		return menu

	def AdapterSetupClosed(self, *ret):
		if ret is not None and len(ret):
			if ret[0] == 'ok' and (self.iface in iNetwork.wlan_interfaces) and iNetwork.getAdapterAttribute(self.iface, "up") is True:
				try:
					from Plugins.SystemPlugins.WirelessLan.plugin import WlanStatus
					from pythonwifi.iwlibs import Wireless
				except ImportError:
					self.session.open(MessageBox, _("The wireless LAN plugin is not installed!\nPlease install it."), type = MessageBox.TYPE_INFO,timeout = 10 )
				else:	
					ifobj = Wireless(self.iface) # a Wireless NIC Object
					try:
						self.wlanresponse = ifobj.getAPaddr()
					except IOError:
						self.wlanresponse = ifobj.getStatistics()
					if self.wlanresponse:
						if self.wlanresponse[0] not in (19,95): # 19 = 'No such device', 95 = 'Operation not supported'
							self.session.openWithCallback(self.WlanStatusClosed, WlanStatus,self.iface)
						else:
							# Display Wlan not available Message
							self.showErrorMessage()
					else:
						# Display Wlan not available Message
						self.showErrorMessage()
			else:
				self.updateStatusbar()
		else:
			self.updateStatusbar()

	def WlanStatusClosed(self, *ret):
		if ret is not None and len(ret):
			from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
			iStatus.stopWlanConsole()
			self.updateStatusbar()

	def WlanScanClosed(self,*ret):
		if ret[0] is not None:
			self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, self.iface,ret[0],ret[1])
		else:
			from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
			iStatus.stopWlanConsole()
			self.updateStatusbar()
			
	def restartLan(self, ret = False):
		if (ret == True):
			iNetwork.restartNetwork(self.restartLanDataAvail)
			self.restartLanRef = self.session.openWithCallback(self.restartfinishedCB, MessageBox, _("Please wait while your network is restarting..."), type = MessageBox.TYPE_INFO, enable_input = False)
			
	def restartLanDataAvail(self, data):
		if data is True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data is True:
			self.restartLanRef.close(True)

	def restartfinishedCB(self,data):
		if data is True:
			self.updateStatusbar()
			self.session.open(MessageBox, _("Finished restarting your network"), type = MessageBox.TYPE_INFO, timeout = 10, default = False)

	def dataAvail(self,data):
		self.LinkState = None
		for line in data.splitlines():
			line = line.strip()
			if 'Link detected:' in line:
				if "yes" in line:
					self.LinkState = True
				else:
					self.LinkState = False
		if self.LinkState == True:
			iNetwork.checkNetworkState(self.checkNetworkCB)
		else:
			self["statuspic"].setPixmapNum(1)
			self["statuspic"].show()			

	def showErrorMessage(self):
		self.session.open(MessageBox, self.errortext, type = MessageBox.TYPE_INFO,timeout = 10 )
		
	def cleanup(self):
		iNetwork.stopLinkStateConsole()
		iNetwork.stopDeactivateInterfaceConsole()
		iNetwork.stopPingConsole()
		try:
			from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
		except ImportError:
			pass
		else:
			iStatus.stopWlanConsole()

	def getInfoCB(self,data,status):
		self.LinkState = None
		if data is not None:
			if data is True:
				if status is not None:
					if status[self.iface]["acesspoint"] == "No Connection" or status[self.iface]["acesspoint"] == "Not-Associated" or status[self.iface]["acesspoint"] == False:
						self.LinkState = False
						self["statuspic"].setPixmapNum(1)
						self["statuspic"].show()
					else:
						self.LinkState = True
						iNetwork.checkNetworkState(self.checkNetworkCB)

	def checkNetworkCB(self,data):
		if iNetwork.getAdapterAttribute(self.iface, "up") is True:
			if self.LinkState is True:
				if data <= 2:
					self["statuspic"].setPixmapNum(0)
				else:
					self["statuspic"].setPixmapNum(1)
				self["statuspic"].show()	
			else:
				self["statuspic"].setPixmapNum(1)
				self["statuspic"].show()
		else:
			self["statuspic"].setPixmapNum(1)
			self["statuspic"].show()


class NetworkAdapterTest(Screen):	
	def __init__(self, session,iface):
		Screen.__init__(self, session)
		self.iface = iface
		self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")
		self.setLabels()
		self.onClose.append(self.cleanup)
		self.onHide.append(self.cleanup)
		
		self["updown_actions"] = NumberActionMap(["WizardActions", "DirectionActions" ,"ShortcutActions"],
		{
			"ok": self.KeyOK,
			"blue": self.KeyOK,
			"up": lambda: self.updownhandler('up'),
			"down": lambda: self.updownhandler('down'),
		
		}, -2)
		
		self["shortcuts"] = ActionMap(["ShortcutActions","WizardActions"],
		{
			"red": self.cancel,
			"back": self.cancel,
		}, -2)
		self["infoshortcuts"] = ActionMap(["ShortcutActions","WizardActions"],
		{
			"red": self.closeInfo,
			"back": self.closeInfo,
		}, -2)
		self["shortcutsgreen"] = ActionMap(["ShortcutActions"],
		{
			"green": self.KeyGreen,
		}, -2)
		self["shortcutsgreen_restart"] = ActionMap(["ShortcutActions"],
		{
			"green": self.KeyGreenRestart,
		}, -2)
		self["shortcutsyellow"] = ActionMap(["ShortcutActions"],
		{
			"yellow": self.KeyYellow,
		}, -2)
		
		self["shortcutsgreen_restart"].setEnabled(False)
		self["updown_actions"].setEnabled(False)
		self["infoshortcuts"].setEnabled(False)
		self.onClose.append(self.delTimer)	
		self.onLayoutFinish.append(self.layoutFinished)
		self.steptimer = False
		self.nextstep = 0
		self.activebutton = 0
		self.nextStepTimer = eTimer()
		self.nextStepTimer.callback.append(self.nextStepTimerFire)

	def cancel(self):
		if self.oldInterfaceState is False:
			iNetwork.setAdapterAttribute(self.iface, "up", self.oldInterfaceState)
			iNetwork.deactivateInterface(self.iface)
		self.close()

	def closeInfo(self):
		self["shortcuts"].setEnabled(True)		
		self["infoshortcuts"].setEnabled(False)
		self["InfoText"].hide()
		self["InfoTextBorder"].hide()
		self["key_red"].setText(_("Close"))

	def delTimer(self):
		del self.steptimer
		del self.nextStepTimer

	def nextStepTimerFire(self):
		self.nextStepTimer.stop()
		self.steptimer = False
		self.runTest()

	def updownhandler(self,direction):
		if direction == 'up':
			if self.activebutton >=2:
				self.activebutton -= 1
			else:
				self.activebutton = 6
			self.setActiveButton(self.activebutton)
		if direction == 'down':
			if self.activebutton <=5:
				self.activebutton += 1
			else:
				self.activebutton = 1
			self.setActiveButton(self.activebutton)

	def setActiveButton(self,button):
		if button == 1:
			self["EditSettingsButton"].setPixmapNum(0)
			self["EditSettings_Text"].setForegroundColorNum(0)
			self["NetworkInfo"].setPixmapNum(0)
			self["NetworkInfo_Text"].setForegroundColorNum(1)
			self["AdapterInfo"].setPixmapNum(1) 		  # active
			self["AdapterInfo_Text"].setForegroundColorNum(2) # active
		if button == 2:
			self["AdapterInfo_Text"].setForegroundColorNum(1)
			self["AdapterInfo"].setPixmapNum(0)
			self["DhcpInfo"].setPixmapNum(0)
			self["DhcpInfo_Text"].setForegroundColorNum(1)
			self["NetworkInfo"].setPixmapNum(1) 		  # active
			self["NetworkInfo_Text"].setForegroundColorNum(2) # active
		if button == 3:
			self["NetworkInfo"].setPixmapNum(0)
			self["NetworkInfo_Text"].setForegroundColorNum(1)
			self["IPInfo"].setPixmapNum(0)
			self["IPInfo_Text"].setForegroundColorNum(1)
			self["DhcpInfo"].setPixmapNum(1) 		  # active
			self["DhcpInfo_Text"].setForegroundColorNum(2) 	  # active
		if button == 4:
			self["DhcpInfo"].setPixmapNum(0)
			self["DhcpInfo_Text"].setForegroundColorNum(1)
			self["DNSInfo"].setPixmapNum(0)
			self["DNSInfo_Text"].setForegroundColorNum(1)
			self["IPInfo"].setPixmapNum(1)			# active
			self["IPInfo_Text"].setForegroundColorNum(2)	# active		
		if button == 5:
			self["IPInfo"].setPixmapNum(0)
			self["IPInfo_Text"].setForegroundColorNum(1)
			self["EditSettingsButton"].setPixmapNum(0)
			self["EditSettings_Text"].setForegroundColorNum(0)
			self["DNSInfo"].setPixmapNum(1)			# active
			self["DNSInfo_Text"].setForegroundColorNum(2)	# active
		if button == 6:
			self["DNSInfo"].setPixmapNum(0)
			self["DNSInfo_Text"].setForegroundColorNum(1)
			self["EditSettingsButton"].setPixmapNum(1) 	   # active
			self["EditSettings_Text"].setForegroundColorNum(2) # active
			self["AdapterInfo"].setPixmapNum(0)
			self["AdapterInfo_Text"].setForegroundColorNum(1)
			
	def runTest(self):
		next = self.nextstep
		if next == 0:
			self.doStep1()
		elif next == 1:
			self.doStep2()
		elif next == 2:
			self.doStep3()
		elif next == 3:
			self.doStep4()
		elif next == 4:
			self.doStep5()
		elif next == 5:
			self.doStep6()
		self.nextstep += 1

	def doStep1(self):
		self.steptimer = True
		self.nextStepTimer.start(300)
		self["key_yellow"].setText(_("Stop test"))

	def doStep2(self):
		self["Adapter"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		self["Adapter"].setForegroundColorNum(2)
		self["Adaptertext"].setForegroundColorNum(1)
		self["AdapterInfo_Text"].setForegroundColorNum(1)
		self["AdapterInfo_OK"].show()
		self.steptimer = True
		self.nextStepTimer.start(300)

	def doStep3(self):
		self["Networktext"].setForegroundColorNum(1)
		self["Network"].setText(_("Please wait..."))
		self.getLinkState(self.iface)
		self["NetworkInfo_Text"].setForegroundColorNum(1)
		self.steptimer = True
		self.nextStepTimer.start(1000)

	def doStep4(self):
		self["Dhcptext"].setForegroundColorNum(1)
		if iNetwork.getAdapterAttribute(self.iface, 'dhcp') is True:
			self["Dhcp"].setForegroundColorNum(2)
			self["Dhcp"].setText(_("enabled"))
			self["DhcpInfo_Check"].setPixmapNum(0)
		else:
			self["Dhcp"].setForegroundColorNum(1)
			self["Dhcp"].setText(_("disabled"))
			self["DhcpInfo_Check"].setPixmapNum(1)
		self["DhcpInfo_Check"].show()
		self["DhcpInfo_Text"].setForegroundColorNum(1)
		self.steptimer = True
		self.nextStepTimer.start(1000)

	def doStep5(self):
		self["IPtext"].setForegroundColorNum(1)
		self["IP"].setText(_("Please wait..."))
		iNetwork.checkNetworkState(self.NetworkStatedataAvail)

	def doStep6(self):
		self.steptimer = False
		self.nextStepTimer.stop()
		self["DNStext"].setForegroundColorNum(1)
		self["DNS"].setText(_("Please wait..."))
		iNetwork.checkDNSLookup(self.DNSLookupdataAvail)

	def KeyGreen(self):
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsyellow"].setEnabled(True)
		self["updown_actions"].setEnabled(False)
		self["key_yellow"].setText("")
		self["key_green"].setText("")
		self.steptimer = True
		self.nextStepTimer.start(1000)

	def KeyGreenRestart(self):
		self.nextstep = 0
		self.layoutFinished()
		self["Adapter"].setText((""))
		self["Network"].setText((""))
		self["Dhcp"].setText((""))
		self["IP"].setText((""))
		self["DNS"].setText((""))
		self["AdapterInfo_Text"].setForegroundColorNum(0)
		self["NetworkInfo_Text"].setForegroundColorNum(0)
		self["DhcpInfo_Text"].setForegroundColorNum(0)
		self["IPInfo_Text"].setForegroundColorNum(0)
		self["DNSInfo_Text"].setForegroundColorNum(0)
		self["shortcutsgreen_restart"].setEnabled(False)
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsyellow"].setEnabled(True)
		self["updown_actions"].setEnabled(False)
		self["key_yellow"].setText("")
		self["key_green"].setText("")
		self.steptimer = True
		self.nextStepTimer.start(1000)

	def KeyOK(self):
		self["infoshortcuts"].setEnabled(True)
		self["shortcuts"].setEnabled(False)
		if self.activebutton == 1: # Adapter Check
			self["InfoText"].setText(_("This test detects your configured LAN-Adapter."))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 2: #LAN Check
			self["InfoText"].setText(_("This test checks whether a network cable is connected to your LAN-Adapter.\nIf you get a \"disconnected\" message:\n- verify that a network cable is attached\n- verify that the cable is not broken"))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 3: #DHCP Check
			self["InfoText"].setText(_("This test checks whether your LAN Adapter is set up for automatic IP Address configuration with DHCP.\nIf you get a \"disabled\" message:\n - then your LAN Adapter is configured for manual IP Setup\n- verify thay you have entered correct IP informations in the AdapterSetup dialog.\nIf you get an \"enabeld\" message:\n-verify that you have a configured and working DHCP Server in your network."))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 4: # IP Check
			self["InfoText"].setText(_("This test checks whether a valid IP Address is found for your LAN Adapter.\nIf you get a \"unconfirmed\" message:\n- no valid IP Address was found\n- please check your DHCP, cabling and adapter setup"))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 5: # DNS Check
			self["InfoText"].setText(_("This test checks for configured Nameservers.\nIf you get a \"unconfirmed\" message:\n- please check your DHCP, cabling and Adapter setup\n- if you configured your Nameservers manually please verify your entries in the \"Nameserver\" Configuration"))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 6: # Edit Settings
			self.session.open(AdapterSetup,self.iface)

	def KeyYellow(self):
		self.nextstep = 0
		self["shortcutsgreen_restart"].setEnabled(True)
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsyellow"].setEnabled(False)
		self["key_green"].setText(_("Restart test"))
		self["key_yellow"].setText("")
		self.steptimer = False
		self.nextStepTimer.stop()

	def layoutFinished(self):
		self.setTitle(_("Network test: ") + iNetwork.getFriendlyAdapterName(self.iface) )
		self["shortcutsyellow"].setEnabled(False)
		self["AdapterInfo_OK"].hide()
		self["NetworkInfo_Check"].hide()
		self["DhcpInfo_Check"].hide()
		self["IPInfo_Check"].hide()
		self["DNSInfo_Check"].hide()
		self["EditSettings_Text"].hide()
		self["EditSettingsButton"].hide()
		self["InfoText"].hide()
		self["InfoTextBorder"].hide()
		self["key_yellow"].setText("")

	def setLabels(self):
		self["Adaptertext"] = MultiColorLabel(_("LAN Adapter"))
		self["Adapter"] = MultiColorLabel()
		self["AdapterInfo"] = MultiPixmap()
		self["AdapterInfo_Text"] = MultiColorLabel(_("Show Info"))
		self["AdapterInfo_OK"] = Pixmap()
		
		if self.iface in iNetwork.wlan_interfaces:
			self["Networktext"] = MultiColorLabel(_("Wireless Network"))
		else:
			self["Networktext"] = MultiColorLabel(_("Local Network"))
		
		self["Network"] = MultiColorLabel()
		self["NetworkInfo"] = MultiPixmap()
		self["NetworkInfo_Text"] = MultiColorLabel(_("Show Info"))
		self["NetworkInfo_Check"] = MultiPixmap()
		
		self["Dhcptext"] = MultiColorLabel(_("DHCP"))
		self["Dhcp"] = MultiColorLabel()
		self["DhcpInfo"] = MultiPixmap()
		self["DhcpInfo_Text"] = MultiColorLabel(_("Show Info"))
		self["DhcpInfo_Check"] = MultiPixmap()
		
		self["IPtext"] = MultiColorLabel(_("IP Address"))
		self["IP"] = MultiColorLabel()
		self["IPInfo"] = MultiPixmap()
		self["IPInfo_Text"] = MultiColorLabel(_("Show Info"))
		self["IPInfo_Check"] = MultiPixmap()
		
		self["DNStext"] = MultiColorLabel(_("Nameserver"))
		self["DNS"] = MultiColorLabel()
		self["DNSInfo"] = MultiPixmap()
		self["DNSInfo_Text"] = MultiColorLabel(_("Show Info"))
		self["DNSInfo_Check"] = MultiPixmap()
		
		self["EditSettings_Text"] = MultiColorLabel(_("Edit settings"))
		self["EditSettingsButton"] = MultiPixmap()
		
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Start test"))
		self["key_yellow"] = StaticText(_("Stop test"))
		
		self["InfoTextBorder"] = Pixmap()
		self["InfoText"] = Label()

	def getLinkState(self,iface):
		if iface in iNetwork.wlan_interfaces:
			try:
				from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
			except:
					self["Network"].setForegroundColorNum(1)
					self["Network"].setText(_("disconnected"))
					self["NetworkInfo_Check"].setPixmapNum(1)
					self["NetworkInfo_Check"].show()
			else:
				iStatus.getDataForInterface(self.iface,self.getInfoCB)
		else:
			iNetwork.getLinkState(iface,self.LinkStatedataAvail)

	def LinkStatedataAvail(self,data):
		self.output = data.strip()
		if "Link detected: yes" in data:
			self["Network"].setForegroundColorNum(2)
			self["Network"].setText(_("connected"))
			self["NetworkInfo_Check"].setPixmapNum(0)
		elif "No data available" in data:
			self["Network"].setForegroundColorNum(2)
			self["Network"].setText(_("unknown"))
			self["NetworkInfo_Check"].setPixmapNum(0)
		else:
			self["Network"].setForegroundColorNum(1)
			self["Network"].setText(_("disconnected"))
			self["NetworkInfo_Check"].setPixmapNum(1)
		self["NetworkInfo_Check"].show()

	def NetworkStatedataAvail(self,data):
		if data <= 2:
			self["IP"].setForegroundColorNum(2)
			self["IP"].setText(_("confirmed"))
			self["IPInfo_Check"].setPixmapNum(0)
		else:
			self["IP"].setForegroundColorNum(1)
			self["IP"].setText(_("unconfirmed"))
			self["IPInfo_Check"].setPixmapNum(1)
		self["IPInfo_Check"].show()
		self["IPInfo_Text"].setForegroundColorNum(1)		
		self.steptimer = True
		self.nextStepTimer.start(300)		
		
	def DNSLookupdataAvail(self,data):
		if data <= 2:
			self["DNS"].setForegroundColorNum(2)
			self["DNS"].setText(_("confirmed"))
			self["DNSInfo_Check"].setPixmapNum(0)
		else:
			self["DNS"].setForegroundColorNum(1)
			self["DNS"].setText(_("unconfirmed"))
			self["DNSInfo_Check"].setPixmapNum(1)
		self["DNSInfo_Check"].show()
		self["DNSInfo_Text"].setForegroundColorNum(1)
		self["EditSettings_Text"].show()
		self["EditSettingsButton"].setPixmapNum(1)
		self["EditSettings_Text"].setForegroundColorNum(2) # active
		self["EditSettingsButton"].show()
		self["key_yellow"].setText("")
		self["key_green"].setText(_("Restart test"))
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsgreen_restart"].setEnabled(True)
		self["shortcutsyellow"].setEnabled(False)
		self["updown_actions"].setEnabled(True)
		self.activebutton = 6

	def getInfoCB(self,data,status):
		if data is not None:
			if data is True:
				if status is not None:
					if status[self.iface]["acesspoint"] == "No Connection" or status[self.iface]["acesspoint"] == "Not-Associated" or status[self.iface]["acesspoint"] == False:
						self["Network"].setForegroundColorNum(1)
						self["Network"].setText(_("disconnected"))
						self["NetworkInfo_Check"].setPixmapNum(1)
						self["NetworkInfo_Check"].show()
					else:
						self["Network"].setForegroundColorNum(2)
						self["Network"].setText(_("connected"))
						self["NetworkInfo_Check"].setPixmapNum(0)
						self["NetworkInfo_Check"].show()
						
	def cleanup(self):
		iNetwork.stopLinkStateConsole()
		iNetwork.stopDNSConsole()
		try:
			from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
		except ImportError:
			pass
		else:
			iStatus.stopWlanConsole()

class NetworkFtp(Screen):
	skin = """
		<screen position="center,center" size="340,310" title="Ftp Setup">
			<widget name="lab1" position="20,30" size="300,80" font="Regular;20" valign="center" transparent="1"/>
			<widget name="lab2" position="20,150" size="150,30" font="Regular;20" valign="center" transparent="1"/>
			<widget name="labstop" position="170,150" size="100,30" font="Regular;20" valign="center"  halign="center" backgroundColor="red"/>
			<widget name="labrun" position="170,150" size="100,30" zPosition="1" font="Regular;20" valign="center"  halign="center" backgroundColor="green"/>
			<ePixmap pixmap="skin_default/buttons/red.png" position="20,260" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="180,260" size="140,40" alphatest="on" />
			<widget name="key_red" position="20,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="180,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("FTP Setup"))
		self['lab1'] = Label(_("Ftpd service type: Vsftpd server"))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_red'] = Label(_("Enable"))
		self['key_green'] = Label(_("Disable"))
		self.my_ftp_active = False
		self.Console = Console()
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'red': self.FtpStart, 'green': self.FtpStop})
		self.onLayoutFinish.append(self.updateFtp)

	def FtpStart(self):
		if self.my_ftp_active == False:
			if fileExists('/etc/inetd.conf'):
				inme = open('/etc/inetd.conf', 'r')
				out = open('/etc/inetd.tmp', 'w')
				for line in inme.readlines():
					if line.find('vsftpd') != -1:
						line = line.replace('#', '')
					out.write(line)
				out.close()
				inme.close()
			if fileExists('/etc/inetd.tmp'):
				move('/etc/inetd.tmp', '/etc/inetd.conf')
				self.Console.ePopen('killall -HUP inetd')
				self.Console.ePopen('ps')
				mybox = self.session.open(MessageBox, _("Ftp service Enabled."), MessageBox.TYPE_INFO)
				mybox.setTitle(_("Info"))
				self.updateFtp()

	def FtpStop(self):
		if self.my_ftp_active == True:
			if fileExists('/etc/inetd.conf'):
				inme = open('/etc/inetd.conf', 'r')
				out = open('/etc/inetd.tmp', 'w')
				for line in inme.readlines():
					if line.find('vsftpd') != -1:
						line = '#' + line
					out.write(line)
				out.close()
				inme.close()
			if fileExists('/etc/inetd.tmp'):
				move('/etc/inetd.tmp', '/etc/inetd.conf')
				self.Console.ePopen('killall -HUP inetd')
				self.Console.ePopen('ps')
				mybox = self.session.open(MessageBox, _("Ftp service Disabled."), MessageBox.TYPE_INFO)
				mybox.setTitle(_("Info"))
				self.updateFtp()

	def updateFtp(self):
		self['labrun'].hide()
		self['labstop'].hide()
		self.my_ftp_active = False
		if fileExists('/etc/inetd.conf'):
			f = open('/etc/inetd.conf', 'r')
			for line in f.readlines():
				parts = line.strip().split()
				if parts[0] == 'ftp':
					self.my_ftp_active = True
					continue
			f.close()
		if self.my_ftp_active == True:
			self['labstop'].hide()
			self['labrun'].show()
		else:
			self['labstop'].show()
			self['labrun'].hide()

class NetworkNfs(Screen):
	skin = """
		<screen position="center,center" size="420,310" title="NFS Setup">
			<widget name="lab1" position="20,50" size="200,30" font="Regular;20" valign="center" transparent="0"/>
			<widget name="labactive" position="220,50" size="150,30" font="Regular;20" valign="center" transparent="0"/>
			<widget name="lab2" position="20,100" size="200,30" font="Regular;20" valign="center" transparent="0"/>
			<widget name="labstop" position="220,100" size="100,30" font="Regular;20" valign="center"  halign="center" backgroundColor="red"/>
			<widget name="labrun" position="220,100" size="100,30" zPosition="1" font="Regular;20" valign="center"  halign="center" backgroundColor="green"/>
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,260" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,260" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,260" size="140,40" alphatest="on" />
			<widget name="key_red" position="0,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="140,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="key_yellow" position="280,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("NFS Setup"))
		self['lab1'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Disabled")))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_red'] = Label(_("Start"))
		self['key_green'] = Label(_("Stop"))
		self['key_yellow'] = Label(_("Autostart"))
		self.Console = Console()
		self.my_nfs_active = False
		self.my_nfs_run = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'red': self.NfsStart, 'green': self.NfsStop, 'yellow': self.Nfsset})
		self.onLayoutFinish.append(self.updateNfs)

	def NfsStart(self):
		if self.my_nfs_run == False:
			self.Console.ePopen('/etc/init.d/nfsserver start')
			time.sleep(3)
			self.updateNfs()
		if self.my_nfs_run == True:
			self.Console.ePopen('/etc/init.d/nfsserver restart')
			time.sleep(3)
			self.updateNfs()

	def NfsStop(self):
		if self.my_nfs_run == True:
			self.Console.ePopen('/etc/init.d/nfsserver stop')
			time.sleep(3)
			self.updateNfs()

	def Nfsset(self):
		if fileExists('/etc/rc0.d/K20nfsserver'):
			unlink('/etc/rc0.d/K20nfsserver')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/nfsserver', '/etc/rc0.d/K20nfsserver')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc1.d/K20nfsserver'):
			unlink('/etc/rc1.d/K20nfsserver')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/nfsserver', '/etc/rc1.d/K20nfsserver')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc2.d/S20nfsserver'):
			unlink('/etc/rc2.d/S20nfsserver')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/nfsserver', '/etc/rc2.d/S20nfsserver')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc3.d/S20nfsserver'):
			unlink('/etc/rc3.d/S20nfsserver')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/nfsserver', '/etc/rc3.d/S20nfsserver')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc4.d/S20nfsserver'):
			unlink('/etc/rc4.d/S20nfsserver')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/nfsserver', '/etc/rc4.d/S20nfsserver')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc5.d/S20nfsserver'):
			unlink('/etc/rc5.d/S20nfsserver')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/nfsserver', '/etc/rc5.d/S20nfsserver')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc6.d/K20nfsserver'):
			unlink('/etc/rc6.d/K20nfsserver')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/nfsserver', '/etc/rc6.d/K20nfsserver')
			mymess = _("Autostart Enabled.")

		mybox = self.session.open(MessageBox, mymess, MessageBox.TYPE_INFO)
		mybox.setTitle(_("Info"))
		self.updateNfs()

	def updateNfs(self):
		import process
		p = process.ProcessList()
		nfs_process = str(p.named('nfsd')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].setText(_("Disabled"))
		self.my_nfs_active = False
		self.my_nfs_run = False
		if fileExists('/etc/rc3.d/S20nfsserver'):
			self['labactive'].setText(_("Enabled"))
			self['labactive'].show()
			self.my_nfs_active = True
		if nfs_process:
			self.my_nfs_run = True
		if self.my_nfs_run == True:
			self['labstop'].hide()
			self['labrun'].show()
			self['key_red'].setText(_("Restart"))
		else:
			self['labstop'].show()
			self['labrun'].hide()
			self['key_red'].setText(_("Start"))

class NetworkOpenvpn(Screen):
	skin = """
		<screen position="center,center" size="560,310" title="OpenVpn Setup">
			<widget name="lab1" position="20,90" size="150,30" font="Regular;20" valign="center" transparent="0"/>
			<widget name="labactive" position="180,90" size="250,30" font="Regular;20" valign="center" transparent="0"/>
			<widget name="lab2" position="20,160" size="150,30" font="Regular;20" valign="center" transparent="0"/>
			<widget name="labstop" position="180,160" size="100,30" font="Regular;20" valign="center" halign="center" backgroundColor="red"/>
			<widget name="labrun" position="180,160" size="100,30" zPosition="1" font="Regular;20" valign="center"  halign="center" backgroundColor="green"/>
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,260" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,260" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,260" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,260" size="140,40" alphatest="on" />
			<widget name="key_red" position="0,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="140,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="key_yellow" position="280,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget name="key_blue" position="420,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("OpenVpn Setup"))
		self['lab1'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Disabled")))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_red'] = Label(_("Start"))
		self['key_green'] = Label(_("Stop"))
		self['key_yellow'] = Label(_("Autostart"))
		self['key_blue'] = Label(_("Show Log"))
		self.Console = Console()
		self.my_vpn_active = False
		self.my_vpn_run = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'red': self.VpnStart, 'green': self.VpnStop, 'yellow': self.activateVpn, 'blue': self.Vpnshowlog})
		self.onLayoutFinish.append(self.updateVpn)

	def Vpnshowlog(self):
		self.session.open(NetworkVpnLog)

	def VpnStart(self):
		if self.my_vpn_run == False:
			self.Console.ePopen('/etc/init.d/openvpn start')
			time.sleep(3)
			self.updateVpn()
		elif self.my_vpn_run == True:
			self.Console.ePopen('/etc/init.d/openvpn restart')
			time.sleep(3)
			self.updateVpn()

	def VpnStop(self):
		if self.my_vpn_run == True:
			self.Console.ePopen('/etc/init.d/openvpn stop')
			time.sleep(3)
			self.updatemy_Vpn()

	def activateVpn(self):
		if fileExists('/etc/rc0.d/K20openvpn'):
			unlink('/etc/rc0.d/K20openvpn')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/openvpn', '/etc/rc0.d/K20openvpn')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc1.d/K20openvpn'):
			unlink('/etc/rc1.d/K20openvpn')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/openvpn', '/etc/rc1.d/K20openvpn')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc2.d/S20openvpn'):
			unlink('/etc/rc2.d/S20openvpn')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/openvpn', '/etc/rc2.d/S20openvpn')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc3.d/S20openvpn'):
			unlink('/etc/rc3.d/S20openvpn')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/openvpn', '/etc/rc3.d/S20openvpn')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc4.d/S20openvpn'):
			unlink('/etc/rc4.d/S20openvpn')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/openvpn', '/etc/rc4.d/S20openvpn')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc5.d/S20openvpn'):
			unlink('/etc/rc5.d/S20openvpn')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/openvpn', '/etc/rc5.d/S20openvpn')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc6.d/K20openvpn'):
			unlink('/etc/rc6.d/K20openvpn')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/openvpn', '/etc/rc6.d/K20openvpn')
			mymess = _("Autostart Enabled.")

		mybox = self.session.open(MessageBox, mymess, MessageBox.TYPE_INFO)
		mybox.setTitle(_("Info"))
		self.updateVpn()

	def updateVpn(self):
		import process
		p = process.ProcessList()
		openvpn_process = str(p.named('openvpn')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].setText(_("Disabled"))
		self.my_Vpn_active = False
		self.my_vpn_run = False
		if fileExists('/etc/rc3.d/S20openvpn'):
			self['labactive'].setText(_("Enabled"))
			self['labactive'].show()
			self.my_Vpn_active = True
		if openvpn_process:
			self.my_vpn_run = True
		if self.my_vpn_run == True:
			self['labstop'].hide()
			self['labrun'].show()
			self['key_red'].setText(_("Restart"))
		else:
			self['labstop'].show()
			self['labrun'].hide()
			self['key_red'].setText(_("Start"))

class NetworkVpnLog(Screen):
	skin = """
		<screen position="80,100" size="560,400" title="OpenVpn Log">
				<widget name="infotext" position="10,10" size="540,380" font="Regular;18" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("OpenVpn Log"))
		self['infotext'] = ScrollLabel('')
		self.Console = Console()
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'up': self['infotext'].pageUp, 'down': self['infotext'].pageDown})
		strview = ''
		self.Console.ePopen('tail /etc/openvpn/openvpn.log > /etc/openvpn/tmp.log')
		time.sleep(1)
		if fileExists('/etc/openvpn/tmp.log'):
			f = open('/etc/openvpn/tmp.log', 'r')
			for line in f.readlines():
				strview += line
			f.close()
			remove('/etc/openvpn/tmp.log')
		self['infotext'].setText(strview)



class NetworkSamba(Screen):
	skin = """
		<screen position="center,center" size="560,310" title="Samba Setup">
			<widget name="lab1" position="20,90" size="150,30" font="Regular;20" valign="center" transparent="0"/>
			<widget name="labactive" position="180,90" size="250,30" font="Regular;20" valign="center" transparent="0"/>
			<widget name="lab2" position="20,160" size="150,30" font="Regular;20" valign="center" transparent="0"/>
			<widget name="labstop" position="180,160" size="100,30" font="Regular;20" valign="center" halign="center" backgroundColor="red"/>
			<widget name="labrun" position="180,160" size="100,30" zPosition="1" font="Regular;20" valign="center"  halign="center" backgroundColor="green"/>
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,260" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,260" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,260" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,260" size="140,40" alphatest="on" />
			<widget name="key_red" position="0,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="140,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="key_yellow" position="280,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget name="key_blue" position="420,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Samba Setup"))
		self['lab1'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Disabled")))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_red'] = Label(_("Start"))
		self['key_green'] = Label(_("Stop"))
		self['key_yellow'] = Label(_("Autostart"))
		self['key_blue'] = Label(_("Show Log"))
		self.Console = Console()
		self.my_Samba_active = False
		self.my_Samba_run = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'red': self.SambaStart, 'green': self.SambaStop, 'yellow': self.activateSamba, 'blue': self.Sambashowlog})
		self.onLayoutFinish.append(self.updateSamba)

	def Sambashowlog(self):
		self.session.open(NetworkSambaLog)

	def SambaStart(self):
		if self.my_Samba_run == False:
			self.Console.ePopen('/etc/init.d/samba start')
			time.sleep(3)
			self.updateSamba()
		elif self.my_Samba_run == True:
			self.Console.ePopen('/etc/init.d/samba restart')
			time.sleep(3)
			self.updateSamba()

	def SambaStop(self):
		if self.my_Samba_run == True:
			self.Console.ePopen('/etc/init.d/samba stop')
			time.sleep(3)
			self.updateSamba()

	def activateSamba(self):
		if fileExists('/etc/rc0.d/K20samba'):
			unlink('/etc/rc0.d/K20samba')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/samba', '/etc/rc0.d/K20samba')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc1.d/K20samba'):
			unlink('/etc/rc1.d/K20samba')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/samba', '/etc/rc1.d/K20samba')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc2.d/S20samba'):
			unlink('/etc/rc2.d/S20samba')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/samba', '/etc/rc2.d/S20samba')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc3.d/S20samba'):
			unlink('/etc/rc3.d/S20samba')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/samba', '/etc/rc3.d/S20samba')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc4.d/S20samba'):
			unlink('/etc/rc4.d/S20samba')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/samba', '/etc/rc4.d/S20samba')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc5.d/S20samba'):
			unlink('/etc/rc5.d/S20samba')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/samba', '/etc/rc5.d/S20samba')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc6.d/K20samba'):
			unlink('/etc/rc6.d/K20samba')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/samba', '/etc/rc6.d/K20samba')
			mymess = _("Autostart Enabled.")

		mybox = self.session.open(MessageBox, mymess, MessageBox.TYPE_INFO)
		mybox.setTitle(_("Info"))
		self.updateSamba()

	def updateSamba(self):
		self.Console.ePopen('ps > /tmp/Samba.tmp')
		time.sleep(1)
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].setText(_("Disabled"))
		self.my_Samba_active = False
		self.my_Samba_run = False
		if fileExists('/etc/rc3.d/S20samba'):
			self['labactive'].setText(_("Enabled"))
			self['labactive'].show()
			self.my_Samba_active = True
		if fileExists('/tmp/Samba.tmp'):
			f = open('/tmp/Samba.tmp', 'r')
			for line in f.readlines():
				if line.find('smbd') >= 0:
					#self['labstop'].hide()
					#self['labactive'].show()
					#self['labrun'].show()
					#self['key_red'].setText(_("Restart"))
					self.my_Samba_run = True
					continue
				#else:
					#self['labstop'].show()
					#self['labactive'].show()
					#self['labrun'].hide()
					#self['key_red'].setText(_("Start"))
			f.close()
			remove('/tmp/Samba.tmp')
		if self.my_Samba_run == True:
			print 'SMBD TRUE'
			self['labstop'].hide()
			self['labactive'].show()
			self['labrun'].show()
			self['key_red'].setText(_("Restart"))
		else:
			print 'SMBD FALSE'
			self['labrun'].hide()
			self['labstop'].show()
			self['labactive'].show()
			self['key_red'].setText(_("Start"))

class NetworkSambaLog(Screen):
	skin = """
		<screen position="80,100" size="560,400" title="Samba Log">
				<widget name="infotext" position="10,10" size="540,380" font="Regular;18" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("OpenVpn Log"))
		self['infotext'] = ScrollLabel('')
		self.Console = Console()
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'up': self['infotext'].pageUp, 'down': self['infotext'].pageDown})
		strview = ''
		self.Console.ePopen('tail /tmp/smb.log > /tmp/tmp.log')
		time.sleep(1)
		if fileExists('/tmp/tmp.log'):
			f = open('//tmp/tmp.log', 'r')
			for line in f.readlines():
				strview += line
			f.close()
			remove('/tmp/tmp.log')
		self['infotext'].setText(strview)

class NetworkTelnet(Screen):
	skin = """
		<screen position="center,center" size="340,310" title="Telnet Setup">
			<widget name="lab1" position="20,30" size="300,80" font="Regular;20" valign="center" transparent="1"/>
			<widget name="lab2" position="20,150" size="150,30" font="Regular;20" valign="center" transparent="1"/>
			<widget name="labstop" position="170,150" size="100,30" font="Regular;20" valign="center"  halign="center" backgroundColor="red"/>
			<widget name="labrun" position="170,150" size="100,30" zPosition="1" font="Regular;20" valign="center"  halign="center" backgroundColor="green"/>
			<ePixmap pixmap="skin_default/buttons/red.png" position="20,260" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="180,260" size="140,40" alphatest="on" />
			<widget name="key_red" position="20,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="180,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Telnet Setup"))
		self['lab1'] = Label(_("You can disable Telnet Server and use ssh to login to your Vu+."))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_red'] = Label(_("Enable"))
		self['key_green'] = Label(_("Disable"))
		self.Console = Console()
		self.my_telnet_active = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'red': self.TelnetStart, 'green': self.TelnetStop})
		self.onLayoutFinish.append(self.updateTelnet)

	def TelnetStart(self):
		if self.my_telnet_active == False:
			if fileExists('/etc/inetd.conf'):
				inme = open('/etc/inetd.conf', 'r')
				out = open('/etc/inetd.tmp', 'w')
				for line in inme.readlines():
					if line.find('telnetd') != -1:
						line = line.replace('#', '')
					out.write(line)
				out.close()
				inme.close()
			if fileExists('/etc/inetd.tmp'):
				move('/etc/inetd.tmp', '/etc/inetd.conf')
				self.Console.ePopen('killall -HUP inetd')
				self.Console.ePopen('ps')
				mybox = self.session.open(MessageBox, _("Telnet service Enabled."), MessageBox.TYPE_INFO)
				mybox.setTitle(_("Info"))
				self.updateTelnet()

	def TelnetStop(self):
		if self.my_telnet_active == True:
			if fileExists('/etc/inetd.conf'):
				inme = open('/etc/inetd.conf', 'r')
				out = open('/etc/inetd.tmp', 'w')
				for line in inme.readlines():
					if line.find('telnetd') != -1:
						line = '#' + line
					out.write(line)
				out.close()
				inme.close()
			if fileExists('/etc/inetd.tmp'):
				move('/etc/inetd.tmp', '/etc/inetd.conf')
				self.Console.ePopen('killall -HUP inetd')
				self.Console.ePopen('ps')
				mybox = self.session.open(MessageBox, _("Telnet service Disabled."), MessageBox.TYPE_INFO)
				mybox.setTitle(_("Info"))
				self.updateTelnet()

	def updateTelnet(self):
		self['labrun'].hide()
		self['labstop'].hide()
		self.my_telnet_active = False
		if fileExists('/etc/inetd.conf'):
			f = open('/etc/inetd.conf', 'r')
			for line in f.readlines():
				parts = line.strip().split()
				if parts[0] == 'telnet':
					self.my_telnet_active = True
					continue
			f.close()
		if self.my_telnet_active == True:
			self['labstop'].hide()
			self['labrun'].show()
		else:
			self['labstop'].show()
			self['labrun'].hide()

class NetworkInadyn(Screen):
	skin = """
		<screen position="center,center" size="590,410" title="Inadyn Manager">
			<widget name="autostart" position="10,0" size="100,24" font="Regular;20" valign="center" transparent="0" />
			<widget name="labdisabled" position="110,0" size="100,24" font="Regular;20" valign="center" halign="center" backgroundColor="red" zPosition="1" />
			<widget name="labactive" position="110,0" size="100,24" font="Regular;20" valign="center" halign="center" backgroundColor="green" zPosition="2" />
			<widget name="status" position="240,0" size="150,24" font="Regular;20" valign="center" transparent="0" />
			<widget name="labstop" position="390,0" size="100,24" font="Regular;20" valign="center" halign="center" backgroundColor="red" zPosition="1" />
			<widget name="labrun" position="390,0" size="100,24" font="Regular;20" valign="center" halign="center" backgroundColor="green" zPosition="2"/>
			<widget name="time" position="10,50" size="230,30" font="Regular;20" valign="center" transparent="1"/>
			<widget name="labtime" position="240,50" size="100,30" font="Regular;20" valign="center" backgroundColor="#4D5375"/>
			<widget name="username" position="10,100" size="150,30" font="Regular;20" valign="center" transparent="1"/>
			<widget name="labuser" position="160,100" size="310,30" font="Regular;20" valign="center" backgroundColor="#4D5375"/>
			<widget name="password" position="10,150" size="150,30" font="Regular;20" valign="center" transparent="1"/>
			<widget name="labpass" position="160,150" size="310,30" font="Regular;20" valign="center" backgroundColor="#4D5375"/>
			<widget name="alias" position="10,200" size="150,30" font="Regular;20" valign="center" transparent="1"/>
			<widget name="labalias" position="160,200" size="310,30" font="Regular;20" valign="center" backgroundColor="#4D5375"/>
			<widget name="sinactive" position="10,250" zPosition="1" pixmap="skin_default/icons/lock_off.png" size="32,32"  alphatest="on" />
			<widget name="sactive" position="10,250" zPosition="2" pixmap="skin_default/icons/lock_on.png" size="32,32"  alphatest="on" />
			<widget name="system" position="50,250" size="100,30" font="Regular;20" valign="center" transparent="1"/>
			<widget name="labsys" position="160,250" size="310,30" font="Regular;20" valign="center" backgroundColor="#4D5375"/>
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,360" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="150,360" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="300,360" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="450,360" size="140,40" alphatest="on" />
			<widget name="key_red" position="0,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="150,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="key_yellow" position="300,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget name="key_blue" position="450,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Inadyn Manager"))
		self['autostart'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Active")))
		self['labdisabled'] = Label(_(_("Disabled")))
		self['status'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['time'] = Label(_('Time Update in Minutes:'))
		self['labtime'] = Label()
		self['username'] = Label(_('Username:'))
		self['labuser'] = Label()
		self['password'] = Label(_('Password:'))
		self['labpass'] = Label()
		self['alias'] = Label(_('Alias:'))
		self['labalias'] = Label()
		self['sactive'] = Pixmap()
		self['sinactive'] = Pixmap()
		self['system'] = Label(_('System:'))
		self['labsys'] = Label()
		self['key_red'] = Label(_('Setup'))
		self['key_green'] = Label(_('Show Log'))
		self['key_yellow'] = Label(_("Start"))
		self['key_blue'] = Label(_("Autostart"))
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.setupin, 'back': self.close, 'red': self.setupin, 'green': self.inaLog, 'yellow': self.InadynStart, 'blue': self.autostart})
		self.Console = Console()
		self.onLayoutFinish.append(self.updateIna)

	def InadynStart(self):
		if self.my_inadyn_run == False:
			self.Console.ePopen('/etc/init.d/inadyn-daemon start')
			time.sleep(3)
			self.updateIna()
		elif self.my_inadyn_run == True:
			self.Console.ePopen('/etc/init.d/inadyn-daemon stop')
			time.sleep(3)
			self.updateIna()

	def autostart(self):
		if fileExists('/etc/rc0.d/K20inadyn-daemon'):
			unlink('/etc/rc0.d/K20inadyn-daemon')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/inadyn-daemon', '/etc/rc0.d/K20inadyn-daemon')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc1.d/K20inadyn-daemon'):
			unlink('/etc/rc1.d/K20inadyn-daemon')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/inadyn-daemon', '/etc/rc1.d/K20inadyn-daemon')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc2.d/S20inadyn-daemon'):
			unlink('/etc/rc2.d/S20inadyn-daemon')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/inadyn-daemon', '/etc/rc2.d/S20inadyn-daemon')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc3.d/S20inadyn-daemon'):
			unlink('/etc/rc3.d/S20inadyn-daemon')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/inadyn-daemon', '/etc/rc3.d/S20inadyn-daemon')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc4.d/S20inadyn-daemon'):
			unlink('/etc/rc4.d/S20inadyn-daemon')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/inadyn-daemon', '/etc/rc4.d/S20inadyn-daemon')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc5.d/S20inadyn-daemon'):
			unlink('/etc/rc5.d/S20inadyn-daemon')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/inadyn-daemon', '/etc/rc5.d/S20inadyn-daemon')
			mymess = _("Autostart Enabled.")

		if fileExists('/etc/rc6.d/K20inadyn-daemon'):
			unlink('/etc/rc6.d/K20inadyn-daemon')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/inadyn-daemon', '/etc/rc6.d/K20inadyn-daemon')
			mymess = _("Autostart Enabled.")

		mybox = self.session.open(MessageBox, mymess, MessageBox.TYPE_INFO, timeout = 10)
		mybox.setTitle(_("Info"))
		self.updateIna()

	def updateIna(self):
		import process
		p = process.ProcessList()
		inadyn_process = str(p.named('inadyn')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].hide()
		self['labdisabled'].hide()
		self['sactive'].hide()
		self.my_inadyn_active = False
		self.my_inadyn_run = False
		if fileExists('/etc/rc3.d/S20inadyn-daemon'):
			self['labdisabled'].hide()
			self['labactive'].show()
			self.my_inadyn_active = True
		else:
			self['labactive'].hide()
			self['labdisabled'].show()
		if inadyn_process:
			self.my_inadyn_run = True
		if self.my_inadyn_run == True:
			self['labstop'].hide()
			self['labrun'].show()
			self['key_yellow'].setText(_("Stop"))
		else:
			self['labstop'].show()
			self['labrun'].hide()
			self['key_yellow'].setText(_("Start"))

		#self.my_nabina_state = False
		if fileExists('/etc/inadyn.conf'):
			f = open('/etc/inadyn.conf', 'r')
			for line in f.readlines():
				line = line.strip()
				if line.startswith('username '):
					line = line[9:]
					self['labuser'].setText(line)
				elif line.startswith('password '):
					line = line[9:]
					self['labpass'].setText(line)
				elif line.startswith('alias '):
					line = line[6:]
					self['labalias'].setText(line)
				elif line.startswith('update_period_sec '):
					line = line[18:]
					line = (int(line) / 60)
					self['labtime'].setText(str(line))
				elif line.startswith('dyndns_system ') or line.startswith('#dyndns_system '):
					print 'DYNDNS',line
					if line.startswith('#'):
						line = line[15:]
						self['sactive'].hide()
					else:
						line = line[14:]
						self['sactive'].show()
					self['labsys'].setText(line)
			f.close()

	def setupin(self):
		self.session.openWithCallback(self.updateIna, NetworkInadynSetup)

	def inaLog(self):
		self.session.open(NetworkInadynLog)



class NetworkInadynSetup(Screen, ConfigListScreen):
	skin = """
		<screen name="InadynSetup" position="center,center" size="440,350" title="Inadyn Setup">
			<widget name="config" position="10,10" size="420,240" scrollbarMode="showOnDemand" />
			<widget name="HelpWindow" pixmap="skin_default/vkey_icon.png" position="170,300" zPosition="1" size="440,350" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="130,310" size="140,40" alphatest="on" />
			<widget name="key_red" position="130,310" size="140,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<ePixmap pixmap="skin_default/buttons/key_text.png" position="300,313" zPosition="4" size="35,25" alphatest="on" transparent="1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		Screen.setTitle(self, _("Inadyn Setup"))
		self['key_red'] = Label(_('Save'))
		self['actions'] = ActionMap(['WizardActions', 'ColorActions', 'VirtualKeyboardActions'], {'red': self.saveIna, 'back': self.close, 'showVirtualKeyboard': self.KeyText})
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self.updateList()

	def updateList(self):
		self.ina_user = NoSave(ConfigText(fixed_size=False))
		self.ina_pass = NoSave(ConfigText(fixed_size=False))
		self.ina_alias = NoSave(ConfigText(fixed_size=False))
		self.ina_period = NoSave(ConfigNumber())
		self.ina_sysactive = NoSave(ConfigYesNo(default='False'))
		self.ina_system = NoSave(ConfigSelection(default = "dyndns@dyndns.org", choices = [("dyndns@dyndns.org", "dyndns@dyndns.org"), ("statdns@dyndns.org", "statdns@dyndns.org"), ("custom@dyndns.org", "custom@dyndns.org")]))

		if fileExists('/etc/inadyn.conf'):
			f = open('/etc/inadyn.conf', 'r')
			for line in f.readlines():
				line = line.strip()
				if line.startswith('username '):
					line = line[9:]
					self.ina_user.value = line
					ina_user1 = getConfigListEntry('Username', self.ina_user)
					self.list.append(ina_user1)
				elif line.startswith('password '):
					line = line[9:]
					self.ina_pass.value = line
					ina_pass1 = getConfigListEntry('Password', self.ina_pass)
					self.list.append(ina_pass1)
				elif line.startswith('alias '):
					line = line[6:]
					self.ina_alias.value = line
					ina_alias1 = getConfigListEntry('Alias', self.ina_alias)
					self.list.append(ina_alias1)
				elif line.startswith('update_period_sec '):
					line = line[18:]
					line = (int(line) / 60)
					self.ina_period.value = line
					ina_period1 = getConfigListEntry('Time Update in Minutes', self.ina_period)
					self.list.append(ina_period1)
				elif line.startswith('dyndns_system ') or line.startswith('#dyndns_system '):
					if not line.startswith('#'):
						self.ina_sysactive.value = True
					else:
						self.ina_sysactive.value = False
					ina_sysactive1 = getConfigListEntry('Set System', self.ina_sysactive)
					self.list.append(ina_sysactive1)
				elif line.startswith('dyndns_system ') or line.startswith('#dyndns_system '):
					if line.startswith('#'):
						line = line[15:]
					else:
						line = line[14:]
					self.ina_system.value = line
					ina_system1 = getConfigListEntry('System ', self.ina_system)
					self.list.append(ina_system1)

			f.close()
		self['config'].list = self.list
		self['config'].l.setList(self.list)

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def KeyText(self):
		sel = self['config'].getCurrent()
		if sel:
			self.vkvar = sel[0]
			if self.vkvar == "Username" or self.vkvar == "Password" or self.vkvar == "Alias" or self.vkvar == "System":
				from Screens.VirtualKeyBoard import VirtualKeyBoard
				self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title = self["config"].getCurrent()[0], text = self["config"].getCurrent()[1].getValue())

	def VirtualKeyBoardCallback(self, callback = None):
		if callback is not None and len(callback):
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidate(self["config"].getCurrent())

	def saveIna(self):
		if fileExists('/etc/inadyn.conf'):
			inme = open('/etc/inadyn.conf', 'r')
			out = open('/etc/inadyn.conf.tmp', 'w')
			for line in inme.readlines():
				line = line.replace('\n', '')
				if line.startswith('username '):
					line = ('username ' + self.ina_user.value.strip())
				elif line.startswith('password '):
					line = ('password ' + self.ina_pass.value.strip())
				elif line.startswith('alias '):
					line = ('alias ' + self.ina_alias.value.strip())
				elif line.startswith('update_period_sec '):
					strview = (self.ina_period.value * 60)
					strview = str(strview)
					line = ('update_period_sec ' + strview)
				elif line.startswith('dyndns_system ') or line.startswith('#dyndns_system '):
					if self.ina_sysactive.value == True:
						line = ('dyndns_system ' + self.ina_system.value.strip())
					else:
						line = ('#dyndns_system ' + self.ina_system.value.strip())
				out.write((line + '\n'))
			out.close()
			inme.close()
		else:
			self.session.open(MessageBox, 'Sorry Inadyn Config is Missing', MessageBox.TYPE_INFO)
			self.close()
		if fileExists('/etc/inadyn.conf.tmp'):
			rename('/etc/inadyn.conf.tmp', '/etc/inadyn.conf')
		self.myStop()

	def myStop(self):
		self.close()

class NetworkInadynLog(Screen):
	skin = """
		<screen name="InadynLog" position="center,center" size="590,410" title="Inadyn Log">
			<widget name="infotext" position="10,10" size="590,410" font="Console;16" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Inadyn Log"))
		self['infotext'] = ScrollLabel('')
		self['actions'] = ActionMap(['WizardActions', 'DirectionActions', 'ColorActions'], {'ok': self.close,
		 'back': self.close,
		 'up': self['infotext'].pageUp,
		 'down': self['infotext'].pageDown})
		strview = ''
		if fileExists('/var/log/inadyn.log'):
			f = open('/var/log/inadyn.log', 'r')
			for line in f.readlines():
				strview += line
			f.close()
		self['infotext'].setText(strview)

