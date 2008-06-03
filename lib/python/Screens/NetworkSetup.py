from Screen import Screen
from Components.ActionMap import ActionMap,NumberActionMap
from Screens.MessageBox import MessageBox
from Screens.Standby import *
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry
from Components.Network import iNetwork
from Tools.Directories import resolveFilename, SCOPE_SKIN_IMAGE
from Components.Label import Label
from Components.Pixmap import Pixmap
from Tools.LoadPixmap import LoadPixmap
from Components.MenuList import MenuList
from Components.config import config, ConfigYesNo, ConfigIP, NoSave, ConfigNothing, ConfigSubsection, ConfigText, ConfigSelection, getConfigListEntry
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor
from enigma import eTimer, eConsoleAppContainer,gRGB
import time, os, re
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

Black = "#000000"
Grey = "#8c8c93"
Green = "1cff1c"
nextstep = None
activebutton = None

def getColor(str):
	return gRGB(int(str[1:], 0x10))

class NetworkAdapterSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		iNetwork.getInterfaces()
		self.wlan_errortext = _("No working wireless networkadapter found.\nPlease verify that you have attached a compatible WLAN USB Stick and your Network is configured correctly.")
		self.lan_errortext = _("No working local networkadapter found.\nPlease verify that you have attached a network cable and your Network is configured correctly.")
		self.adapters = [(iNetwork.getFriendlyAdapterName(x),x) for x in iNetwork.getAdapterList()]
		if len(self.adapters) == 0:
			self.onFirstExecBegin.append(self.NetworkFallback)
			
		self["adapterlist"] = MenuList(self.adapters)
		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.okbuttonClick,
			"cancel": self.close
		})

		if len(self.adapters) == 1:
			self.onFirstExecBegin.append(self.okbuttonClick)

	def okbuttonClick(self):
		selection = self["adapterlist"].getCurrent()
		if selection is not None:
			self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetupConfiguration, selection[1])
	
	def AdapterSetupClosed(self, *ret):
		self.close()

	def NetworkFallback(self):
		if iNetwork.configuredInterfaces.has_key('wlan0') is True:
			self.session.openWithCallback(self.ErrorMessageClosed, MessageBox, self.wlan_errortext, type = MessageBox.TYPE_INFO,timeout = 10)
		else:
			self.session.openWithCallback(self.ErrorMessageClosed, MessageBox, self.lan_errortext, type = MessageBox.TYPE_INFO,timeout = 10)

	def ErrorMessageClosed(self, *ret):
		if iNetwork.configuredInterfaces.has_key('wlan0') is True:
			self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetupConfiguration, 'wlan0')
		else:
			self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetupConfiguration, 'eth0')
			
class NameserverSetup(Screen, ConfigListScreen):

	def __init__(self, session):
		Screen.__init__(self, session)
		iNetwork.getInterfaces()
		self.backupNameserverList = iNetwork.getNameserverList()[:]
		print "backup-list:", self.backupNameserverList

		self["ButtonGreentext"] = Label(_("Add"))
		self["ButtonYellowtext"] = Label(_("Delete"))
		self["ButtonRedtext"] = Label(_("Close"))		
		self.createConfig()

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"ok": self.ok,
			"cancel": self.cancel,
			"red": self.cancel,
			"green": self.add,
			"yellow": self.remove
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.createSetup()

	def createConfig(self):
		self.nameservers = iNetwork.getNameserverList()
		self.nameserverEntries = []

		for nameserver in self.nameservers:
			self.nameserverEntries.append(NoSave(ConfigIP(default=nameserver)))

	def createSetup(self):
		self.list = []

		for i in range(len(self.nameserverEntries)):
			self.list.append(getConfigListEntry(_("Nameserver %d") % (i + 1), self.nameserverEntries[i]))

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def ok(self):
		iNetwork.clearNameservers()
		for nameserver in self.nameserverEntries:
			iNetwork.addNameserver(nameserver.value)
		iNetwork.writeNameserverConfig()
		self.close()

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


class AdapterSetup(Screen, ConfigListScreen):
	def __init__(self, session, iface):
		Screen.__init__(self, session)
		self.session = session
		iNetwork.getInterfaces()
		## FIXME , workaround against current wizzard not able to send arguments
		if iface == 0:
			self.iface = "eth0"
		elif iface == 1:
			self.iface = "wlan0"
		else:
			self.iface = iface

		if self.iface == 'wlan0':
			from Plugins.SystemPlugins.WirelessLan.Wlan import wpaSupplicant,Wlan
			self.ws = wpaSupplicant()
			list = []
			list.append(_("WEP"))
			list.append(_("WPA"))
			list.append(_("WPA2"))
			if iNetwork.getAdapterAttribute('wlan0', 'up') is True:
				try:
					self.w = Wlan('wlan0')
					aps = self.w.getNetworkList()
					nwlist = []
					if aps is not None:
						print "[Wlan.py] got Accespoints!"
						for ap in aps:
							a = aps[ap]
							if a['active']:
								if a['essid'] == "":
									a['essid'] = a['bssid']
								nwlist.append( a['essid'])
					nwlist.sort(key = lambda x: x[0])
				except:
					nwlist = []
					nwlist.append("No Networks found")
					
			if nwlist is None:
				nwlist = []
				nwlist.append("No Networks found")				

			config.plugins.wlan.essid = NoSave(ConfigSelection(nwlist, default = nwlist[0]))			
			config.plugins.wlan.encryption.enabled = NoSave(ConfigYesNo(default = False))
			config.plugins.wlan.encryption.type = NoSave(ConfigSelection(list, default = _("WPA")))
			config.plugins.wlan.encryption.psk = NoSave(ConfigText(default = "mysecurewlan", fixed_size = False))
			self.ws.loadConfig()

		self.dhcpConfigEntry = NoSave(ConfigYesNo(default=iNetwork.getAdapterAttribute(self.iface, "dhcp") or False))
		self.hasGatewayConfigEntry = NoSave(ConfigYesNo(default=True))
		self.ipConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "ip")) or [0,0,0,0])
		self.netmaskConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "netmask") or [255,0,0,0]))
		self.gatewayConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "gateway") or [0,0,0,0]))
		nameserver = (iNetwork.getNameserverList() + [[0,0,0,0]] * 2)[0:2]
		self.primaryDNS = NoSave(ConfigIP(default=nameserver[0]))
		self.secondaryDNS = NoSave(ConfigIP(default=nameserver[1]))

		self["actions"] = ActionMap(["SetupActions","ShortcutActions"],
		{
			"ok": self.ok,
			"cancel": self.cancel,
			"red": self.cancel,
			"blue": self.KeyBlue,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)
		
		self["DNS1text"] = Label(_("Primary DNS"))
		self["DNS2text"] = Label(_("Secondary DNS"))
		self["DNS1"] = Label()
		self["DNS2"] = Label()
		
		self["introduction"] = Label(_("Current settings:"))
		
		self["IPtext"] = Label(_("IP Address"))
		self["Netmasktext"] = Label(_("Netmask"))
		self["Gatewaytext"] = Label(_("Gateway"))
		
		self["IP"] = Label()
		self["Mask"] = Label()
		self["Gateway"] = Label()
		
		self["BottomBG"] = Pixmap()
		self["Adaptertext"] = Label(_("Network:"))
		self["Adapter"] = Label()
		self["introduction2"] = Label(_("Press OK to activate the settings."))
		self["ButtonRed"] = Pixmap()
		self["ButtonRedtext"] = Label(_("Close"))
		self["ButtonBlue"] = Pixmap()
		self["ButtonBluetext"] = Label(_("Edit DNS"))

	def layoutFinished(self):
		self["DNS1"].setText(self.primaryDNS.getText())
		self["DNS2"].setText(self.secondaryDNS.getText())
		print "self.ipConfigEntry.getText()--->>>",self.ipConfigEntry.getText()
		if self.ipConfigEntry.getText() is not None:
			self["IP"].setText(self.ipConfigEntry.getText())
		else:
			self["IP"].setText([0,0,0,0])
		self["Mask"].setText(self.netmaskConfigEntry.getText())
		self["Gateway"].setText(self.gatewayConfigEntry.getText())		
		self["Adapter"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		
	def createSetup(self):
		self.list = []

		self.dhcpEntry = getConfigListEntry(_("Use DHCP"), self.dhcpConfigEntry)
		self.list.append(self.dhcpEntry)
		if not self.dhcpConfigEntry.value:
			self.list.append(getConfigListEntry(_('IP Address'), self.ipConfigEntry))
			self.list.append(getConfigListEntry(_('Netmask'), self.netmaskConfigEntry))
			self.list.append(getConfigListEntry(_('Use a gateway'), self.hasGatewayConfigEntry))
			if self.hasGatewayConfigEntry.value:
				self.list.append(getConfigListEntry(_('Gateway'), self.gatewayConfigEntry))

		self.extended = None
		self.extendedSetup = None
		for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKSETUP):
			callFnc = p.__call__["ifaceSupported"](self.iface)
			if callFnc is not None:
				self.extended = callFnc
				print p.__call__
				if p.__call__.has_key("configStrings"):
					self.configStrings = p.__call__["configStrings"]
				else:
					self.configStrings = None

				self.list.append(getConfigListEntry(_("Network SSID"), config.plugins.wlan.essid))
				self.encryptionEnabled = getConfigListEntry(_("Encryption"), config.plugins.wlan.encryption.enabled)
				self.list.append(self.encryptionEnabled)
		
				if config.plugins.wlan.encryption.enabled.value:
					self.list.append(getConfigListEntry(_("Encryption Type"), config.plugins.wlan.encryption.type))
					self.list.append(getConfigListEntry(_("Encryption Key"), config.plugins.wlan.encryption.psk))


		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def KeyBlue(self):
		self.session.open(NameserverSetup)

	def newConfig(self):
		print self["config"].getCurrent()
		if self["config"].getCurrent() == self.dhcpEntry:
			self.createSetup()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def ok(self):
		selection = self["config"].getCurrent()
		if selection == self.extendedSetup:
			self.extended(self.session, self.iface)
		else:
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
			
			iNetwork.deactivateNetworkConfig()
			iNetwork.writeNetworkConfig()
			iNetwork.activateNetworkConfig()
			self.close()

	def cancel(self):
		iNetwork.getInterfaces()
		self.close()

	def run(self):
		self.ok()


class AdapterSetupConfiguration(Screen):
	
	def __init__(self, session,iface):
		Screen.__init__(self, session)
		self.iface = iface
		self.session = session
		self.mainmenu = self.genMainMenu()
		self["menulist"] = MenuList(self.mainmenu)
		self["description"] = Label()
		self["IFtext"] = Label()
		self["IF"] = Label()
		self["BottomBG"] = Label()
		self["Statustext"] = Label()
		self["statuspic_active"] = Pixmap()
		self["statuspic_active"].hide()
		self["statuspic_inactive"] = Pixmap()
		self["statuspic_inactive"].hide()
		self["BottomBG"] = Pixmap()
		self["ButtonRed"] = Pixmap()
		self["ButtonRedtext"] = Label(_("Close"))

		self.oktext = _("Press OK on your remote control to continue.")
		self.reboottext = _("Your Dreambox will restart after pressing OK on your remote control.")
		self.errortext = _("No working wireless interface found.\n Please verify that you have attached a compatible WLAN USB Stick or enable you local network interface.")	
		
		self["actions"] = NumberActionMap(["WizardActions","ShortcutActions"],
		{
			"ok": self.ok,
			"back": self.close,
			"up": self.up,
			"down": self.down,
			"red": self.close,
			"left": self.left,
			"right": self.right,			
		}, -2)

		iNetwork.getInterfaces()
		self.onLayoutFinish.append(self.layoutFinished)
		self.updateStatusbar()

	def ok(self):
		if self["menulist"].getCurrent()[1] == 'edit':
			if self.iface == 'wlan0':
				from Plugins.SystemPlugins.WirelessLan.iwlibs import Wireless
				ifobj = Wireless(self.iface) # a Wireless NIC Object
				self.wlanresponse = ifobj.getStatistics()
				if self.wlanresponse[0] != 19: # Wlan Interface found.
					self.session.open(AdapterSetup,self.iface)
				else:
					# Display Wlan not available Message
					self.showErrorMessage()
			else:
				self.session.open(AdapterSetup,self.iface)
		if self["menulist"].getCurrent()[1] == 'test':
			self.session.open(NetworkAdapterTest,self.iface)
		if self["menulist"].getCurrent()[1] == 'dns':
			self.session.open(NameserverSetup)
		if self["menulist"].getCurrent()[1] == 'scanwlan':
			from Plugins.SystemPlugins.WirelessLan.iwlibs import Wireless
			ifobj = Wireless(self.iface) # a Wireless NIC Object
			self.wlanresponse = ifobj.getStatistics()
			if self.wlanresponse[0] != 19:
				from Plugins.SystemPlugins.WirelessLan.plugin import WlanScan
				self.session.open(WlanScan,self.iface)
			else:
				# Display Wlan not available Message
				self.showErrorMessage()
		if self["menulist"].getCurrent()[1] == 'wlanstatus':
			from Plugins.SystemPlugins.WirelessLan.iwlibs import Wireless
			ifobj = Wireless(self.iface) # a Wireless NIC Object
			self.wlanresponse = ifobj.getStatistics()
			if self.wlanresponse[0] != 19:
				from Plugins.SystemPlugins.WirelessLan.plugin import WlanStatus
				self.session.open(WlanStatus,self.iface)
			else:
				# Display Wlan not available Message
				self.showErrorMessage()
		if self["menulist"].getCurrent()[1] == 'lanrestart':
			self.session.openWithCallback(self.restartLan, MessageBox, (_("Are you sure you want to restart your network interfaces?\n\n") + self.oktext ) )
		if self["menulist"].getCurrent()[1] == 'enablewlan':
			self.session.openWithCallback(self.enableWlan, MessageBox, _("Are you sure you want to enable WLAN support?\nConnect your Wlan USB Stick to your Dreambox and press OK.\n\n") )
		if self["menulist"].getCurrent()[1] == 'enablelan':
			self.session.openWithCallback(self.enableLan, MessageBox, (_("Are you sure you want to enable your local network?\n\n") + self.oktext ) )
		if self["menulist"].getCurrent()[1] == 'openwizard':
			from Plugins.SystemPlugins.NetworkWizard.NetworkWizard import NetworkWizard
			self.session.openWithCallback(self.AdapterSetupClosed, NetworkWizard)
	
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
		if self["menulist"].getCurrent()[1] == 'enablelan':
			self["description"].setText(_("Enable the local network of your Dreambox.\n\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'dns':
			self["description"].setText(_("Edit the Nameserver configuration of your Dreambox.\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'scanwlan':
			self["description"].setText(_("Scan your network for wireless Access Points and connect to them using your WLAN USB Stick\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'wlanstatus':
			self["description"].setText(_("Shows the state of your wireless LAN connection.\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'lanrestart':
			self["description"].setText(_("Restart your network connection and interfaces.\n" ) + self.oktext )
		if self["menulist"].getCurrent()[1] == 'enablewlan':
			self["description"].setText(_("Pressing OK enables the built in wireless LAN support of your Dreambox.\nWlan USB Sticks with Zydas ZD1211B and RAlink RT73 Chipset are supported.\nConnect your Wlan USB Stick to your Dreambox before pressing OK.\n\n" ) + self.reboottext )
		if self["menulist"].getCurrent()[1] == 'openwizard':
			self["description"].setText(_("Use the Networkwizard to configure your Network\n" ) + self.oktext )


	def updateStatusbar(self):
		self["IFtext"].setText(_("Network:"))
		self["IF"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		self["Statustext"].setText(_("Link:"))

		if self.iface == 'wlan0':
			try:
				from Plugins.SystemPlugins.WirelessLan.Wlan import Wlan, WlanList, wpaSupplicant
				w = Wlan(self.iface)
				stats = w.getStatus()
				if stats['BSSID'] == "00:00:00:00:00:00":
					self["statuspic_active"].hide()
					self["statuspic_inactive"].show()
				else:
					self["statuspic_active"].show()
					self["statuspic_inactive"].hide()
			except:
					self["statuspic_active"].hide()
					self["statuspic_inactive"].show()
		else:
			self.getLinkState(self.iface)
		
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
				menu.append((_("Scan Wireless Networks"), "scanwlan"))
				menu.append((_("Show WLAN Status"), "wlanstatus"))
				menu.append((_("Enable LAN"), "enablelan"))
			if callFnc is None and iNetwork.ifaces.has_key('wlan0') is False:
				menu.append((_("Enable WLAN"), "enablewlan"))
			if callFnc is None and iNetwork.ifaces.has_key('wlan0') is True:
				menu.append((_("Enable LAN"), "enablelan"))
				
		if os.path.exists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
			menu.append((_("NetworkWizard"), "openwizard"));
		return menu

	def AdapterSetupClosed(self, *ret):
		self.mainmenu = self.genMainMenu()
		self["menulist"].l.setList(self.mainmenu)
	
	def enableWlan(self, ret = False):
		if (ret == True):
			iNetwork.resetNetworkConfig('wlan')
			iNetwork.getInterfaces()
			if iNetwork.getAdapterAttribute('wlan0', 'up') is True:
				self.iface = 'wlan0'
				self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, 'wlan0')
			else:
				self.session.openWithCallback(self.restartDreambox, MessageBox, _("Your wireless LAN Adapter could not be startet.\nDo you want to reboot your Dreambox to apply the new configuration?\n"))

	
	def enableLan(self, ret = False):
		if (ret == True):
			iNetwork.resetNetworkConfig('lan')
			iNetwork.getInterfaces()
			if iNetwork.getAdapterAttribute('eth0', 'up') is True:
				self.iface = 'eth0'
				self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, 'eth0')
			else:
				self.session.openWithCallback(self.restartDreambox, MessageBox, _("Your local LAN Adapter could not be startet.\nDo you want to reboot your Dreambox to apply the new configuration?\n"))


	def restartLan(self, ret = False):
		if (ret == True):
			iNetwork.restartNetwork()

	def restartDreambox(self, ret = False):
		if (ret == True):
			TryQuitMainloop(self.session,2)


	def getLinkState(self,iface):
		iNetwork.getLinkState(iface,self.dataAvail)

	def dataAvail(self,data):
		self.output = data.strip()
		result = self.output.split('\n')
		pattern = re.compile("Link detected: yes")
		for item in result:
			if re.search(pattern, item):
				self["statuspic_active"].show()
				self["statuspic_inactive"].hide()
			else:
				self["statuspic_active"].hide()
				self["statuspic_inactive"].show()
	
	def showErrorMessage(self):
		self.session.open(MessageBox, self.errortext, type = MessageBox.TYPE_INFO,timeout = 10 )


class NetworkAdapterTest(Screen):	

	def __init__(self, session,iface):
		Screen.__init__(self, session)
		self.iface = iface
		iNetwork.getInterfaces()
		self.setLabels()
	
		self["updown_actions"] = NumberActionMap(["WizardActions","ShortcutActions"],
		{
			"ok": self.KeyOK,
			"blue": self.KeyOK,
			"up": lambda: self.updownhandler('up'),
			"down": lambda: self.updownhandler('down'),
	
		}, -2)

		self["shortcuts"] = ActionMap(["ShortcutActions","WizardActions"],
		{
			"red": self.close,
			"back": self.close,
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
		global nextstep
		nextstep = 0
		global activebutton
		activebutton = 0		
		self.nextStepTimer = eTimer()
		self.nextStepTimer.callback.append(self.nextStepTimerFire)

	def closeInfo(self):
		self["shortcuts"].setEnabled(True)		
		self["infoshortcuts"].setEnabled(False)
		self["InfoText"].hide()
		self["InfoTextBorder"].hide()
		self["ButtonRedtext"].setText(_("Close"))
		
	def delTimer(self):
		del self.steptimer
		del self.nextStepTimer

	def nextStepTimerFire(self):
		global nextstep
		self.nextstep= nextstep
		self.nextStepTimer.stop()
		self.steptimer = False
		self.runTest(self.nextstep)

	def updownhandler(self,direction):
		global activebutton
		if direction == 'up':
			if activebutton >=2:
				activebutton = activebutton -1
			self.setActiveButton(activebutton)
		if direction == 'down':
			if activebutton <=5:
				activebutton = activebutton +1
			self.setActiveButton(activebutton)

	def setActiveButton(self,button):
		if button == 1:
			self["NetworkInfo"].show()
			self["NetworkInfo_selected"].hide()
			self["AdapterInfo"].hide()
			self["AdapterInfo_selected"].show()
		if button == 2:
			self["AdapterInfo"].show()
			self["AdapterInfo_selected"].hide()
			self["DhcpInfo"].show()
			self["DhcpInfo_selected"].hide()
			self["NetworkInfo"].hide()
			self["NetworkInfo_selected"].show()		
		if button == 3:
			self["NetworkInfo"].show()
			self["NetworkInfo_selected"].hide()
			self["IPInfo"].show()
			self["IPInfo_selected"].hide()
			self["DhcpInfo"].hide()
			self["DhcpInfo_selected"].show()
		if button == 4:
			self["DhcpInfo"].show()
			self["DhcpInfo_selected"].hide()
			self["DNSInfo"].show()
			self["DNSInfo_selected"].hide()
			self["IPInfo"].hide()
			self["IPInfo_selected"].show()
		if button == 5:
			self["IPInfo"].show()
			self["IPInfo_selected"].hide()
			self["EditSettingsButton"].show()
			self["EditSettingsButton_selected"].hide()
			self["DNSInfo"].hide()
			self["DNSInfo_selected"].show()
		if button == 6:
			self["DNSInfo"].show()
			self["DNSInfo_selected"].hide()
			self["EditSettingsButton"].hide()
			self["EditSettingsButton_selected"].show()
			
	def runTest(self,next):
		global nextstep
		if next == 0:
			nextstep = next + 1
			self.doStep1()
		if next == 1:
			nextstep = next + 1
			self.doStep2()		
		if next == 2:
			nextstep = next + 1
			self.doStep3()
		if next == 3:
			nextstep = next + 1
			self.doStep4()
		if next == 4:
			nextstep = next + 1
			self.doStep5()
		if next == 5:
			nextstep = next + 1
			self.doStep6()			
		
	def doStep1(self):
		self.steptimer = True
		self.nextStepTimer.start(3000)

	def doStep2(self):
		self["Adapter"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		self["Adapter"].instance.setForegroundColor(getColor(Green))
		self["AdapterInfo_Text"].instance.setForegroundColor(getColor(Black))
		self["AdapterInfo_OK"].show()		
		self.steptimer = True
		self.nextStepTimer.start(3000)		

	def doStep3(self):
		self.getLinkState(self.iface)
		self["NetworkInfo_Text"].instance.setForegroundColor(getColor(Black))
		self.steptimer = True
		self.nextStepTimer.start(3000)			

	def doStep4(self):
		if iNetwork.getAdapterAttribute(self.iface, 'dhcp') is True:
			self["Dhcp"].instance.setForegroundColor(getColor(Green))
			self["Dhcp"].setText(_("enabled"))
			self["DhcpInfo_OK"].show()
			self["DhcpInfo_NOK"].hide()
		else:
			self["Dhcp"].instance.setForegroundColor(getColor(Grey))
			self["Dhcp"].setText(_("disabled"))		
			self["DhcpInfo_NOK"].show()
			self["DhcpInfo_OK"].hide()
		self["DhcpInfo_Text"].instance.setForegroundColor(getColor(Black))	
		self.steptimer = True
		self.nextStepTimer.start(3000)

	def doStep5(self):
		ret = iNetwork.checkNetworkState()
		if ret == True:
			self["IP"].instance.setForegroundColor(getColor(Green))
			self["IP"].setText(_("confirmed"))
			self["IPInfo_OK"].show()
			self["IPInfo_NOK"].hide()
		else:
			self["IP"].instance.setForegroundColor(getColor(Grey))
			self["IP"].setText(_("unconfirmed"))			
			self["IPInfo_NOK"].show()
			self["IPInfo_OK"].hide()
		self["IPInfo_Text"].instance.setForegroundColor(getColor(Black))	
		self.steptimer = True
		self.nextStepTimer.start(3000)

	def doStep6(self):
		self.steptimer = False
		self.nextStepTimer.stop()
		if len (iNetwork.getNameserverList()) != 0:
			self["DNS"].instance.setForegroundColor(getColor(Green))
			self["DNS"].setText(_("confirmed"))
			self["DNSInfo_OK"].show()
			self["DNSInfo_NOK"].hide()
		else:
			self["DNS"].instance.setForegroundColor(getColor(Grey))
			self["DNS"].setText(_("unconfirmed"))
			self["DNSInfo_NOK"].show()
			self["DNSInfo_OK"].hide()
			
		self["DNSInfo_Text"].instance.setForegroundColor(getColor(Black))
		self["EditSettings_Text"].show()
		self["EditSettingsButton_selected"].show()
		self["ButtonYellow_off"].show()
		self["ButtonYellow"].hide()
		self["ButtonGreentext"].setText(_("Restart test"))
		self["ButtonGreen"].show()		
		self["ButtonGreen_off"].hide()
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsgreen_restart"].setEnabled(True)
		self["shortcutsyellow"].setEnabled(False)
		self["updown_actions"].setEnabled(True)
		global activebutton
		activebutton = 6
		
	def KeyGreen(self):
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsyellow"].setEnabled(True)
		self["updown_actions"].setEnabled(False)
		self["ButtonYellow_off"].hide()
		self["ButtonYellow"].show()
		self["ButtonGreen"].hide()		
		self["ButtonGreen_off"].show()
		self.steptimer = True
		self.nextStepTimer.start(1000)

	def KeyGreenRestart(self):
		global nextstep
		nextstep = 0		
		self.layoutFinished()
		self["Adapter"].setText((""))
		self["Network"].setText((""))
		self["Dhcp"].setText((""))
		self["IP"].setText((""))
		self["DNS"].setText((""))
		self["AdapterInfo_Text"].instance.setForegroundColor(getColor(Grey))
		self["NetworkInfo_Text"].instance.setForegroundColor(getColor(Grey))
		self["DhcpInfo_Text"].instance.setForegroundColor(getColor(Grey))
		self["IPInfo_Text"].instance.setForegroundColor(getColor(Grey))
		self["DNSInfo_Text"].instance.setForegroundColor(getColor(Grey))
		self["shortcutsgreen_restart"].setEnabled(False)
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsyellow"].setEnabled(True)
		self["updown_actions"].setEnabled(False)
		self["ButtonYellow_off"].hide()
		self["ButtonYellow"].show()
		self["ButtonGreen"].hide()		
		self["ButtonGreen_off"].show()
		self.steptimer = True
		self.nextStepTimer.start(1000)
		
	def KeyOK(self):
		global activebutton
		self["infoshortcuts"].setEnabled(True)
		self["shortcuts"].setEnabled(False)
		if activebutton == 1: # Adapter Check
			self["InfoText"].setText(_("This test detects your configured LAN-Adapter."))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["ButtonRedtext"].setText(_("Back"))
		if activebutton == 2: #LAN Check
			self["InfoText"].setText(_("This test checks whether a network cable is connected to your LAN-Adapter.\nIf you get a \"disconnected\" message:\n- verify that a network cable is attached\n- verify that the cable is not broken"))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["ButtonRedtext"].setText(_("Back"))
		if activebutton == 3: #DHCP Check
			self["InfoText"].setText(_("This test checks whether your LAN Adapter is set up for automatic IP Address configuration with DHCP.\nIf you get a \"disabled\" message:\n - then your LAN Adapter is configured for manual IP Setup\n- verify thay you have entered correct IP informations in the AdapterSetup dialog.\nIf you get an \"enabeld\" message:\n-verify that you have a configured and working DHCP Server in your network."))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["ButtonRedtext"].setText(_("Back"))
		if activebutton == 4: # IP Check
			self["InfoText"].setText(_("This test checks whether a valid IP Address is found for your LAN Adapter.\nIf you get a \"unconfirmed\" message:\n- no valid IP Address was found\n- please check your DHCP, cabling and adapter setup"))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["ButtonRedtext"].setText(_("Back"))
		if activebutton == 5: # DNS Check
			self["InfoText"].setText(_("This test checks for configured Nameservers.\nIf you get a \"unconfirmed\" message:\n- please check your DHCP, cabling and Adapter setup\n- if you configured your Nameservers manually please verify your entries in the \"Nameserver\" Configuration"))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["ButtonRedtext"].setText(_("Back"))
		if activebutton == 6: # Edit Settings
			self.session.open(AdapterSetup,self.iface)

	def KeyYellow(self):
		global nextstep
		nextstep = 0
		self["shortcutsgreen_restart"].setEnabled(True)
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsyellow"].setEnabled(False)
		self["ButtonGreentext"].setText(_("Restart test"))
		self["ButtonYellow_off"].show()
		self["ButtonYellow"].hide()
		self["ButtonGreen"].show()		
		self["ButtonGreen_off"].hide()
		self.steptimer = False
		self.nextStepTimer.stop()
		
	def layoutFinished(self):
		self["shortcutsyellow"].setEnabled(False)
		self["AdapterInfo_selected"].hide()
		self["AdapterInfo_OK"].hide()
		
		self["NetworkInfo_selected"].hide()
		self["NetworkInfo_OK"].hide()
		self["NetworkInfo_NOK"].hide()
		
		self["DhcpInfo_selected"].hide()
		self["DhcpInfo_OK"].hide()
		self["DhcpInfo_NOK"].hide()
		
		self["IPInfo_selected"].hide()
		self["IPInfo_OK"].hide()
		self["IPInfo_NOK"].hide()
		
		self["DNSInfo_selected"].hide()
		self["DNSInfo_OK"].hide()
		self["DNSInfo_NOK"].hide()
		
		self["EditSettings_Text"].hide()
		self["EditSettingsButton"].hide()
		self["EditSettingsButton_selected"].hide()
		self["ButtonYellow"].hide()
		self["ButtonGreen_off"].hide()
		self["InfoText"].hide()
		self["InfoTextBorder"].hide()
		
	def setLabels(self):
		self["Adaptertext"] = Label(_("LAN Adapter"))
		self["Adapter"] = Label()
		self["AdapterInfo"] = Pixmap()
		self["AdapterInfo_selected"] = Pixmap()
		self["AdapterInfo_Text"] = Label(_("Show Info"))
		self["AdapterInfo_OK"] = Pixmap()
		
		if self.iface == 'wlan0':
			self["Networktext"] = Label(_("Wireless Network"))
		else:
			self["Networktext"] = Label(_("Local Network"))
		
		self["Network"] = Label()
		self["NetworkInfo"] = Pixmap()
		self["NetworkInfo_selected"] = Pixmap()
		self["NetworkInfo_Text"] = Label(_("Show Info"))
		self["NetworkInfo_OK"] = Pixmap()
		self["NetworkInfo_NOK"] = Pixmap()
		
		self["Dhcptext"] = Label(_("DHCP"))
		self["Dhcp"] = Label()
		self["DhcpInfo"] = Pixmap()
		self["DhcpInfo_selected"] = Pixmap()
		self["DhcpInfo_Text"] = Label(_("Show Info"))
		self["DhcpInfo_OK"] = Pixmap()
		self["DhcpInfo_NOK"] = Pixmap()
		
		self["IPtext"] = Label(_("IP Address"))
		self["IP"] = Label()
		self["IPInfo"] = Pixmap()
		self["IPInfo_selected"] = Pixmap()
		self["IPInfo_Text"] = Label(_("Show Info"))
		self["IPInfo_OK"] = Pixmap()
		self["IPInfo_NOK"] = Pixmap()
		
		self["DNStext"] = Label(_("Nameserver"))
		self["DNS"] = Label()
		self["DNSInfo"] = Pixmap()
		self["DNSInfo_selected"] = Pixmap()
		self["DNSInfo_Text"] = Label(_("Show Info"))
		self["DNSInfo_OK"] = Pixmap()
		self["DNSInfo_NOK"] = Pixmap()
		
		self["EditSettings_Text"] = Label(_("Edit settings"))		
		self["EditSettingsButton"] = Pixmap()
		self["EditSettingsButton_selected"] = Pixmap()
		
		self["ButtonRedtext"] = Label(_("Close"))
		self["ButtonRed"] = Pixmap()
		self["ButtonGreentext"] = Label(_("Start test"))
		self["ButtonGreen"] = Pixmap()
		self["ButtonGreen_off"] = Pixmap()
		self["ButtonYellowtext"] = Label(_("Stop test"))
		self["ButtonYellow"] = Pixmap()		
		self["ButtonYellow_off"] = Pixmap()
		
		self["InfoTextBorder"] = Pixmap()
		self["InfoText"] = Label()

	def getLinkState(self,iface):
		if iface == 'wlan0':
			try:
				from Plugins.SystemPlugins.WirelessLan.Wlan import Wlan
				w = Wlan(iface)
				stats = w.getStatus()
				if stats['BSSID'] == "00:00:00:00:00:00":
					self["Network"].instance.setForegroundColor(getColor(Grey))
					self["Network"].setText(_("disconnected"))
					self["NetworkInfo_OK"].hide()
					self["NetworkInfo_NOK"].show()
				else:
					self["Network"].instance.setForegroundColor(getColor(Green))
					self["Network"].setText(_("connected"))
					self["NetworkInfo_OK"].show()
					self["NetworkInfo_NOK"].hide()
			except:
					self["Network"].instance.setForegroundColor(getColor(Grey))
					self["Network"].setText(_("disconnected"))
					self["NetworkInfo_OK"].hide()
					self["NetworkInfo_NOK"].show()				
		else:
			iNetwork.getLinkState(iface,self.dataAvail)

	def dataAvail(self,data):
		self.output = data.strip()
		result = self.output.split('\n')
		pattern = re.compile("Link detected: yes")
		for item in result:
			if re.search(pattern, item):
				self["Network"].instance.setForegroundColor(getColor(Green))
				self["Network"].setText(_("connected"))
				self["NetworkInfo_OK"].show()
				self["NetworkInfo_NOK"].hide()
			else:
				self["Network"].instance.setForegroundColor(getColor(Grey))
				self["Network"].setText(_("disconnected"))
				self["NetworkInfo_OK"].hide()
				self["NetworkInfo_NOK"].show()


