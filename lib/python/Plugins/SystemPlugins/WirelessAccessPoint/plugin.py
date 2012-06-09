from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen, ConfigList
from Components.config import config, ConfigSubsection, getConfigListEntry, ConfigSelection, ConfigIP, ConfigInteger
from Components.config import ConfigText, ConfigYesNo, NoSave, ConfigPassword, ConfigNothing, ConfigSequence
from Components.ActionMap import ActionMap
from Screens.MessageBox import MessageBox
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import fileExists
from math import pow as math_pow
from Components.Network import iNetwork
from Components.PluginComponent import plugins
from Components.Console import Console
from os import path as os_path, system as os_system, listdir
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from enigma import eTimer
import wirelessap

debug_msg_on = False
def printDebugMsg(msg):
	global debug_msg_on
	if debug_msg_on:
		print "[Wireless Access Point] ", msg

class fixedValue:
	def __init__(self, value = ""):
		self.value = value

apModeConfig = ConfigSubsection()
apModeConfig.useap = ConfigYesNo(default = False)
apModeConfig.setupmode = ConfigSelection(default = "simple", choices = [ ("simple", "Simple"), ("advanced", "Advanced") ] )
#apModeConfig.wirelessdevice = fixedValue(value = "")
apModeConfig.branch = fixedValue(value = "br0")
apModeConfig.driver = fixedValue(value = "nl80211")
apModeConfig.wirelessmode = ConfigSelection(default = "g", choices = [ ("b", "802.11b"), ("a", "802.11a"), ("g", "802.11g") ] )
apModeConfig.channel = ConfigInteger(default = 1, limits = (1,13) )
apModeConfig.ssid = ConfigText(default = "Input SSID", visible_width = 50, fixed_size = False)
apModeConfig.beacon = ConfigInteger(default = 100, limits = (15,65535))
apModeConfig.rts_threshold = ConfigInteger(default = 2347, limits = (0,2347) )
apModeConfig.fragm_threshold = ConfigInteger(default = 2346, limits = (256,2346) )
apModeConfig.preamble = ConfigSelection(default = "0", choices = [ ("0", "Long"), ("1", "Short") ] )
apModeConfig.ignore_broadcast_ssid = ConfigSelection(default = "0", choices = [ ("0", _("disabled")), ("1", _("enabled")) ])

apModeConfig.encrypt = ConfigYesNo(default = False)
apModeConfig.method = ConfigSelection(default = "0", choices = [
	("0", _("WEP")), ("1", _("WPA")), ("2", _("WPA2")),("3", _("WPA/WPA2"))])
apModeConfig.wep = ConfigYesNo(default = False)
#apModeConfig.wep_default_key = ConfigSelection(default = "0", choices = [ ("0", "0"), ("1", "1"), ("2", "2"), ("3", "3") ] )
apModeConfig.wep_default_key = fixedValue(value = "0")
apModeConfig.wepType = ConfigSelection(default = "64", choices = [
	("64", _("Enable 64 bit (Input 10 hex keys)")), ("128", _("Enable 128 bit (Input 26 hex keys)"))])
apModeConfig.wep_key0 = ConfigPassword(default = "", visible_width = 50, fixed_size = False)
apModeConfig.wpa = ConfigSelection(default = "0", choices = [
	("0", _("not set")), ("1", _("WPA")), ("2", _("WPA2")),("3", _("WPA/WPA2"))])
apModeConfig.wpa_passphrase = ConfigPassword(default = "", visible_width = 50, fixed_size = False)
apModeConfig.wpagrouprekey = ConfigInteger(default = 600, limits = (0,3600))
apModeConfig.wpa_key_mgmt = fixedValue(value = "WPA-PSK")
apModeConfig.wpa_pairwise = fixedValue(value = "TKIP CCMP")
apModeConfig.rsn_pairwise = fixedValue(value = "CCMP")

apModeConfig.usedhcp = ConfigYesNo(default=True)
apModeConfig.address = ConfigIP(default = [0,0,0,0])
apModeConfig.netmask = ConfigIP(default = [255,0,0,0])
apModeConfig.gateway = ConfigIP(default = [0,0,0,0])

class WirelessAccessPoint(Screen,ConfigListScreen):
	skin = """
		<screen position="center,center" size="590,450" title="Wireless Access Point" >
		<ePixmap pixmap="skin_default/buttons/red.png" position="20,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="160,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="300,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="440,0" size="140,40" alphatest="on" />

		<widget source="key_red" render="Label" position="20,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="160,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_yellow" render="Label" position="300,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#a08500" transparent="1" />
		<widget source="key_blue" render="Label" position="440,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#18188b" transparent="1" />

		<widget name="config" zPosition="2" position="10,70" size="580,270" scrollbarMode="showOnDemand" transparent="1" />
		<widget source="current_settings" render="Label" position="10,340" size="570,20" font="Regular;19" halign="center" valign="center" transparent="1" />
		<widget source="IPAddress_text" render="Label" position="130,370" size="190,21" font="Regular;19" transparent="1" />
		<widget source="Netmask_text" render="Label" position="130,395" size="190,21" font="Regular;19" transparent="1" />
		<widget source="Gateway_text" render="Label" position="130,420" size="190,21" font="Regular;19" transparent="1" />
		<widget source="IPAddress" render="Label" position="340,370" size="240,21" font="Regular;19" transparent="1" />
		<widget source="Netmask" render="Label" position="340,395" size="240,21" font="Regular;19" transparent="1" />
		<widget source="Gateway" render="Label" position="340,420" size="240,21" font="Regular;19" transparent="1" />
		</screen>"""

	def __init__(self,session):
		Screen.__init__(self,session)
		self.session = session
		self["shortcuts"] = ActionMap(["ShortcutActions", "SetupActions" ],
		{
			"ok": self.doConfigMsg,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"green": self.doConfigMsg,
		}, -2)
		self.list = []
		ConfigListScreen.__init__(self, self.list,session = self.session)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Ok"))
		self["key_yellow"] = StaticText(_(" "))
		self["key_blue"] = StaticText(_(" "))
		self["current_settings"] = StaticText(_("Current settings (interface : br0)"))
		self["IPAddress_text"] = StaticText(_("IP Address"))
		self["Netmask_text"] = StaticText(_("Netmask"))
		self["Gateway_text"] = StaticText(_("Gateway"))
		self["IPAddress"] = StaticText(_("N/A"))
		self["Netmask"] = StaticText(_("N/A"))
		self["Gateway"] = StaticText(_("N/A"))
		self.wirelessAP = wirelessap.wirelessAP()
		self.checkRunHostapd()
		self.checkWirelessDevices()
		self.makeConfigList()
		self.loadInterfacesConfig()
		self.loadHostapConfig()
		self.setupCurrentEncryption()
		self.createConfigEntry()
		self.createConfig()
		self.onClose.append(self.__onClose)
		self.onLayoutFinish.append(self.checkwlanDeviceList)
		self.onLayoutFinish.append(self.currentNetworkSettings)
		self.checkwlanDeviceListTimer = eTimer()
		self.checkwlanDeviceListTimer.callback.append(self.WirelessDeviceNotDetectedMsg)

	def checkwlanDeviceList(self):
		if len(self.wlanDeviceList) == 0:
			self.checkwlanDeviceListTimer.start(100,True)

	def WirelessDeviceNotDetectedMsg(self):
		self.session.openWithCallback(self.close ,MessageBox, _("Wireless Lan Device is not detected."), MessageBox.TYPE_ERROR)

	def currentNetworkSettings(self):
		self["IPAddress"].setText(self.formatAddr(iNetwork.getAdapterAttribute("br0", "ip")))
		self["Netmask"].setText(self.formatAddr(iNetwork.getAdapterAttribute("br0", "netmask")))
		self["Gateway"].setText(self.formatAddr(iNetwork.getAdapterAttribute("br0", "gateway")))

	def formatAddr(self, address = [0,0,0,0]):
		if address is None:
			return "N/A"
		return "%d:%d:%d:%d"%(address[0],address[1],address[2],address[3])

	def checkRunHostapd(self):
		global apModeConfig
		if fileExists("/var/run/hostapd", 0):
			apModeConfig.useap.value = True

	def makeConfigList(self):
		global apModeConfig
		self.hostapdConfigList = {}
		self.hostapdConfigList["interface"] = apModeConfig.wirelessdevice
		self.hostapdConfigList["bridge"] = apModeConfig.branch # "br0"
		self.hostapdConfigList["driver"] = apModeConfig.driver # "nl80211"
		self.hostapdConfigList["hw_mode"] = apModeConfig.wirelessmode
		self.hostapdConfigList["channel"] = apModeConfig.channel
		self.hostapdConfigList["ssid"] = apModeConfig.ssid
		self.hostapdConfigList["beacon_int"] = apModeConfig.beacon
		self.hostapdConfigList["rts_threshold"] = apModeConfig.rts_threshold
		self.hostapdConfigList["fragm_threshold"] = apModeConfig.fragm_threshold
		self.hostapdConfigList["preamble"] = apModeConfig.preamble
#		self.hostapdConfigList["macaddr_acl"] = "" # fix to add Access Control List Editer
#		self.hostapdConfigList["accept_mac_file"] = "" # fix to add Access Control List Editer
#		self.hostapdConfigList["deny_mac_file"] = "" # fix to add Access Control List Editer
		self.hostapdConfigList["ignore_broadcast_ssid"] = apModeConfig.ignore_broadcast_ssid
#		self.hostapdConfigList["wmm_enabled"] = ""
#		self.hostapdConfigList["ieee80211n"] = ""
#		self.hostapdConfigList["ht_capab"] = ""
		self.hostapdConfigList["wep_default_key"] = apModeConfig.wep_default_key
		self.hostapdConfigList["wep_key0"] = apModeConfig.wep_key0
		self.hostapdConfigList["wpa"] = apModeConfig.wpa
		self.hostapdConfigList["wpa_passphrase"] = apModeConfig.wpa_passphrase
		self.hostapdConfigList["wpa_key_mgmt"] = apModeConfig.wpa_key_mgmt # "WPA-PSK"
		self.hostapdConfigList["wpa_pairwise"] = apModeConfig.wpa_pairwise # "TKIP CCMP"
		self.hostapdConfigList["rsn_pairwise"] = apModeConfig.rsn_pairwise # "CCMP"
		self.hostapdConfigList["wpa_group_rekey"] = apModeConfig.wpagrouprekey

	def loadInterfacesConfig(self):
		global apModeConfig
		try:
			fp = file('/etc/network/interfaces', 'r')
			datas = fp.readlines()
			fp.close()
		except:
			printDebugMsg("interfaces - file open failed")
		# check br0 configuration
		current_iface = ""
		ifaceConf = {}
		try:
			for line in datas:
				split = line.strip().split(' ')
				if (split[0] == "iface"):
					current_iface = split[1]
					if (current_iface == "br0") and (len(split) == 4 and split[3] == "dhcp"):
						apModeConfig.usedhcp.value = True
					else:
						apModeConfig.usedhcp.value = False
				if (current_iface == "br0" or current_iface == "eth0"):
					if (split[0] == "address"):
						apModeConfig.address.value = map(int, split[1].split('.'))
					if (split[0] == "netmask"):
						apModeConfig.netmask.value = map(int, split[1].split('.'))
					if (split[0] == "gateway"):
						apModeConfig.gateway.value = map(int, split[1].split('.'))
		except:
			printDebugMsg("configuration parsing error! - /etc/network/interfaces")

	def loadHostapConfig(self):
		hostapdConf = { }
		ret = self.wirelessAP.loadHostapConfig(hostapdConf)
		if ret != 0:
			printDebugMsg("configuration opening failed!!")
			return
		for (key,value) in hostapdConf.items():
			if key == "config.wep":
				apModeConfig.wep.value = int(value)
			elif key in ["channel", "beacon_int", "rts_threshold", "fragm_threshold", "wpa_group_rekey"]:
				self.hostapdConfigList[key].value = int(value)
			elif key in self.hostapdConfigList.keys():
				self.hostapdConfigList[key].value = value
			if key == "channel" and int(value) not in range(14):
				self.hostapdConfigList[key].value = 1

#		for key in self.hostapdConfigList.keys():
#			printDebugMsg("[cofigList] key : %s, value : %s"%(key, str(self.hostapdConfigList[key].value)) )

	def setupCurrentEncryption(self):
		if apModeConfig.wpa.value is not "0" and apModeConfig.wpa_passphrase.value: # (1,WPA), (2,WPA2), (3,WPA/WPA2)
			apModeConfig.encrypt.value = True
			apModeConfig.method.value = apModeConfig.wpa.value
		elif apModeConfig.wep.value and apModeConfig.wep_key0.value:
			apModeConfig.encrypt.value = True
			apModeConfig.method.value = "0"
			if len(apModeConfig.wep_key0.value) > 10:
				apModeConfig.wepType.value = "128"
		else:
			apModeConfig.encrypt.value = False

	def createConfigEntry(self):
		global apModeConfig
#hostap settings
		self.useApEntry = getConfigListEntry(_("Use AP Mode"), apModeConfig.useap)
		self.setupModeEntry = getConfigListEntry(_("Setup Mode"), apModeConfig.setupmode)
		self.wirelessDeviceEntry = getConfigListEntry(_("AP Device"), apModeConfig.wirelessdevice)
		self.wirelessModeEntry = getConfigListEntry(_("AP Mode"), apModeConfig.wirelessmode)
		self.channelEntry = getConfigListEntry(_("Channel (1~13)"), apModeConfig.channel)
		self.ssidEntry = getConfigListEntry(_("SSID (1~32 Characters)"), apModeConfig.ssid)
		self.beaconEntry = getConfigListEntry(_("Beacon (15~65535)"), apModeConfig.beacon)
		self.rtsThresholdEntry = getConfigListEntry(_("RTS Threshold (0~2347)"), apModeConfig.rts_threshold)
		self.fragmThresholdEntry = getConfigListEntry(_("FRAGM Threshold (256~2346)"), apModeConfig.fragm_threshold)
		self.prambleEntry = getConfigListEntry(_("Preamble"), apModeConfig.preamble)
		self.ignoreBroadcastSsid = getConfigListEntry(_("Ignore Broadcast SSID"), apModeConfig.ignore_broadcast_ssid)
# hostap encryption
		self.encryptEntry = getConfigListEntry(_("Encrypt"), apModeConfig.encrypt)
		self.methodEntry = getConfigListEntry(_("Method"), apModeConfig.method)
		self.wepKeyTypeEntry = getConfigListEntry(_("KeyType"), apModeConfig.wepType)
		self.wepKey0Entry = getConfigListEntry(_("WEP Key (HEX)"), apModeConfig.wep_key0)
		self.wpaKeyEntry = getConfigListEntry(_("KEY (8~63 Characters)"), apModeConfig.wpa_passphrase)
		self.groupRekeyEntry = getConfigListEntry(_("Group Rekey Interval"), apModeConfig.wpagrouprekey)
# interface settings
		self.usedhcpEntry = getConfigListEntry(_("Use DHCP"), apModeConfig.usedhcp)
		self.ipEntry = getConfigListEntry(_("IP Address"), apModeConfig.address)
		self.netmaskEntry = getConfigListEntry(_("NetMask"), apModeConfig.netmask)
		self.gatewayEntry = getConfigListEntry(_("Gateway"), apModeConfig.gateway)

	def createConfig(self):
		global apModeConfig
		self.configList = []
		self.configList.append( self.useApEntry )
		if apModeConfig.useap.value is True:
			self.configList.append( self.setupModeEntry )
			self.configList.append( self.wirelessDeviceEntry )
			self.configList.append( self.wirelessModeEntry )
			self.configList.append( self.channelEntry )
			self.configList.append( self.ssidEntry )
			if apModeConfig.setupmode.value  is "advanced":
				self.configList.append( self.beaconEntry )
				self.configList.append( self.rtsThresholdEntry )
				self.configList.append( self.fragmThresholdEntry )
				self.configList.append( self.prambleEntry )
				self.configList.append( self.ignoreBroadcastSsid )
			self.configList.append( self.encryptEntry )
			if apModeConfig.encrypt.value is True:
				self.configList.append( self.methodEntry )
				if apModeConfig.method.value is "0": # wep
					self.configList.append( self.wepKeyTypeEntry )
					self.configList.append( self.wepKey0Entry )
				else:
					self.configList.append( self.wpaKeyEntry )
					if apModeConfig.setupmode.value  is "advanced":
						self.configList.append( self.groupRekeyEntry )
## 		set network interfaces
			self.configList.append( self.usedhcpEntry )
			if apModeConfig.usedhcp.value is False:
				self.configList.append( self.ipEntry )
				self.configList.append( self.netmaskEntry )
				self.configList.append( self.gatewayEntry )
		self["config"].list = self.configList
		self["config"].l.setList(self.configList)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def newConfig(self):
		if self["config"].getCurrent() in [ self.encryptEntry, self.methodEntry, self.useApEntry, self.usedhcpEntry, self.setupModeEntry]:
			self.createConfig()

	def doConfigMsg(self):
		try:
			self.session.openWithCallback(self.doConfig, MessageBox, (_("Are you sure you want to setup your AP?\n\n") ) )
		except:
			printDebugMsg("doConfig failed")

	def doConfig(self, ret = False):
		global apModeConfig
		if ret is not True:
			return
		if apModeConfig.useap.value is True and apModeConfig.encrypt.value is True:
			if not self.checkEncrypKey():
				return
		if not self.checkConfig():
			return
		self.configStartMsg = self.session.openWithCallback(self.ConfigFinishedMsg, MessageBox, _("Please wait for AP Configuration....\n") , type = MessageBox.TYPE_INFO, enable_input = False)
		if apModeConfig.useap.value is True:
			self.networkRestart( nextFunc = self.makeConf )
		else:
			self.networkRestart( nextFunc = self.removeConf )

	def checkEncrypKey(self):
		if apModeConfig.method.value == "0":
			if self.checkWep(apModeConfig.wep_key0.value) is False:
				self.session.open(MessageBox, _("Invalid WEP key\n\n"), type = MessageBox.TYPE_ERROR, timeout = 10 )
			else:
				return True
		else:
			if not len(apModeConfig.wpa_passphrase.value) in range(8,65):
				self.session.open(MessageBox, _("Invalid WPA key\n\n"), type = MessageBox.TYPE_ERROR, timeout = 10)
			else:
				return True
		return False

	def checkWep(self,  key):
		length = len(key)
		if length == 0:
			return False
		elif apModeConfig.wepType.value == "64" and length == 10:
			return True
		elif apModeConfig.wepType.value == "128" and length == 26:
			return True
		else:
			return False

	def checkConfig(self):
		# ssid Check
		if len(apModeConfig.ssid.value) == 0 or len(apModeConfig.ssid.value) > 32:
			self.session.open(MessageBox, _("Invalid SSID\n"), type = MessageBox.TYPE_ERROR, timeout = 10)
			return False;
		elif apModeConfig.channel.value not in range(1,14):
			self.session.open(MessageBox, _("Invalid channel\n"), type = MessageBox.TYPE_ERROR, timeout = 10)
			return False;
		elif apModeConfig.beacon.value < 15 or apModeConfig.beacon.value > 65535:
			self.session.open(MessageBox, _("Invalid beacon\n"), type = MessageBox.TYPE_ERROR, timeout = 10)
			return False;
		elif apModeConfig.rts_threshold.value < 0 or apModeConfig.rts_threshold.value > 2347:
			self.session.open(MessageBox, _("Invalid RTS Threshold\n"), type = MessageBox.TYPE_ERROR, timeout = 10)
			return False;
		elif apModeConfig.fragm_threshold.value < 256 or apModeConfig.fragm_threshold.value > 2346:
			self.session.open(MessageBox, _("Invalid Fragm Threshold\n"), type = MessageBox.TYPE_ERROR, timeout = 10)
			return False;
		elif apModeConfig.wpagrouprekey.value < 0 or apModeConfig.wpagrouprekey.value > 3600:
			self.session.open(MessageBox, _("Invalid wpagrouprekey\n"), type = MessageBox.TYPE_ERROR, timeout = 10)
			return False;
		return True;

	def networkRestart(self, nextFunc = None ):
		self.networkRestart_stop( nextFunc = nextFunc )

	def networkRestart_stop(self, nextFunc = None ):
		printDebugMsg("networkRestart_stop")
		self.msgPlugins(False)
		self.commands = [] # stop current network
		self.networkRestartConsole = Console()
		self.commands.append("/etc/init.d/avahi-daemon stop")
		for iface in iNetwork.getAdapterList():
			if iface != 'eth0' or not iNetwork.onRemoteRootFS():
				self.commands.append("ifdown " + iface)
				self.commands.append("ip addr flush dev " + iface)
		self.commands.append("/etc/init.d/hostapd stop")
		self.commands.append("/etc/init.d/networking stop")
		self.commands.append("killall -9 udhcpc")
		self.commands.append("rm /var/run/udhcpc*")
		self.networkRestartConsole.eBatch(self.commands, nextFunc, debug = True)

	def makeConf(self,extra_args):
		printDebugMsg("makeConf")
		self.writeNetworkInterfaces()
		result = self.writeHostapdConfig()
		if result == -1:
			self.configStartMsg.close(False)
			return
		self.setIpForward(1)
		self.networkRestart_start()

	def removeConf(self,extra_args):
		printDebugMsg("removeConf")
		if fileExists("/etc/hostapd.conf", 0):
			os_system("mv /etc/hostapd.conf /etc/hostapd.conf.linuxap.back")
		fp = file("/etc/network/interfaces", 'w')
		fp.write("# automatically generated by AP Setup Plugin\n# do NOT change manually!\n\n")
		fp.write("auto lo\n")
		fp.write("iface lo inet loopback\n\n")
		# eth0 setup
		fp.write("auto eth0\n")
		if apModeConfig.usedhcp.value is True:
			fp.write("iface eth0 inet dhcp\n")
		else:
			fp.write("iface eth0 inet static\n")
			fp.write("	address %d.%d.%d.%d\n" % tuple(apModeConfig.address.value) )
			fp.write("	netmask %d.%d.%d.%d\n" % tuple(apModeConfig.netmask.value) )
			fp.write("	gateway %d.%d.%d.%d\n" % tuple(apModeConfig.gateway.value) )
		fp.close()
		self.setIpForward(0)
		self.networkRestart_start()

	def networkRestart_start(self):
		printDebugMsg("networkRestart_start")
		self.restartConsole = Console()
		self.commands = []
		self.commands.append("/etc/init.d/networking start")
		self.commands.append("/etc/init.d/avahi-daemon start")
		self.commands.append("/etc/init.d/hostapd start")
		self.restartConsole.eBatch(self.commands, self.networkRestartFinished, debug=True)

	def networkRestartFinished(self, data):
		printDebugMsg("networkRestartFinished")
		iNetwork.removeAdapterAttribute('br0',"ip")
		iNetwork.removeAdapterAttribute('br0',"netmask")
		iNetwork.removeAdapterAttribute('br0',"gateway")
		iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data is True and self.configStartMsg is not None:
			self.configStartMsg.close(True)

	def ConfigFinishedMsg(self, ret):
		if ret is True:
			self.session.openWithCallback(self.ConfigFinishedMsgCallback ,MessageBox, _("Configuration your AP is finished"), type = MessageBox.TYPE_INFO, timeout = 5, default = False)
		else:
			self.session.openWithCallback(self.close ,MessageBox, _("Invalid model or Image."), MessageBox.TYPE_ERROR)

	def ConfigFinishedMsgCallback(self,data):
		self.close()

	def msgPlugins(self,reason = False):
		for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKCONFIG_READ):
				p(reason=reason)

	def writeNetworkInterfaces(self):
		global apModeConfig
		fp = file("/etc/network/interfaces", 'w')
		fp.write("# automatically generated by AP Setup Plugin\n# do NOT change manually!\n\n")
		fp.write("auto lo\n")
		fp.write("iface lo inet loopback\n\n")
		# eth0 setup
		fp.write("auto eth0\n")
		fp.write("iface eth0 inet manual\n")
		fp.write("	up ip link set $IFACE up\n")
		fp.write("	down ip link set $IFACE down\n\n")
		# Wireless device setup
		fp.write("auto %s\n" % apModeConfig.wirelessdevice.value)
		fp.write("iface %s inet manual\n" % apModeConfig.wirelessdevice.value)
		fp.write("	up ip link set $IFACE up\n")
		fp.write("	down ip link set $IFACE down\n")
		# branch setup
		fp.write("auto br0\n")
		if apModeConfig.usedhcp.value is True:
			fp.write("iface br0 inet dhcp\n")
		else:
			fp.write("iface br0 inet static\n")
			fp.write("	address %d.%d.%d.%d\n" % tuple(apModeConfig.address.value) )
			fp.write("	netmask %d.%d.%d.%d\n" % tuple(apModeConfig.netmask.value) )
			fp.write("	gateway %d.%d.%d.%d\n" % tuple(apModeConfig.gateway.value) )
		fp.write("	pre-up brctl addbr br0\n")
		fp.write("	pre-up brctl addif br0 eth0\n")
#		fp.write("	pre-up brctl addif br0 wlan0\n") // runned by hostpad
		fp.write("	post-down brctl delif br0 eth0\n")
#		fp.write("	post-down brctl delif br0 wlan0\n") // runned by hostpad
		fp.write("	post-down brctl delbr br0\n\n")
		fp.write("\n")
		fp.close()

	def writeHostapdConfig(self): #c++
		global apModeConfig
		configDict = {}
		for key in self.hostapdConfigList.keys():
			configDict[key] = str(self.hostapdConfigList[key].value)
		configDict["config.encrypt"] = str(int(apModeConfig.encrypt.value))
		configDict["config.method"] = apModeConfig.method.value
		ret = self.wirelessAP.writeHostapdConfig(configDict)
		if(ret != 0):
			return -1
		return 0

	def setIpForward(self, setValue = 0):
		ipForwardFilePath = "/proc/sys/net/ipv4/ip_forward"
		if not fileExists(ipForwardFilePath):
			return -1
		printDebugMsg("set %s to %d" % (ipForwardFilePath, setValue))
		f = open(ipForwardFilePath, "w")
		f.write("%d" % setValue)
		f.close()
		sysctlPath = "/etc/sysctl.conf"
		sysctlLines = []
		if fileExists(sysctlPath):
			fp = file(sysctlPath, "r")
			sysctlLines = fp.readlines()
			fp.close()
		sysctlList = {}
		for line in sysctlLines:
			line = line.strip()
			(key,value) = line.split("=")
			key=key.strip()
			value=value.strip()
			sysctlList[key] = value
		sysctlList["net.ipv4.ip_forward"] = str(setValue)
		fp = file(sysctlPath, "w")
		for (key,value) in sysctlList.items():
			fp.write("%s=%s\n"%(key,value))
		fp.close()
		return 0

	def checkWirelessDevices(self):
		global apModeConfig
		self.wlanDeviceList = []
		wlanIfaces =[]
		for x in iNetwork.getInstalledAdapters():
			if x.startswith('eth') or x.startswith('br') or x.startswith('mon'):
				continue
			wlanIfaces.append(x)
			description=self.getAdapterDescription(x)
			if description == "Unknown network adapter":
				self.wlanDeviceList.append((x, x))
			else:
				self.wlanDeviceList.append(( x, description + " (%s)"%x ))
		apModeConfig.wirelessdevice = ConfigSelection( choices = self.wlanDeviceList )

	def getAdapterDescription(self, iface):
		classdir = "/sys/class/net/" + iface + "/device/"
		driverdir = "/sys/class/net/" + iface + "/device/driver/"
		if os_path.exists(classdir):
			files = listdir(classdir)
			if 'driver' in files:
				if os_path.realpath(driverdir).endswith('rtw_usb_drv'):
					return _("Realtek")+ " " + _("WLAN adapter.")
				elif os_path.realpath(driverdir).endswith('ath_pci'):
					return _("Atheros")+ " " + _("WLAN adapter.")
				elif os_path.realpath(driverdir).endswith('zd1211b'):
					return _("Zydas")+ " " + _("WLAN adapter.")
				elif os_path.realpath(driverdir).endswith('rt73'):
					return _("Ralink")+ " " + _("WLAN adapter.")
				elif os_path.realpath(driverdir).endswith('rt73usb'):
					return _("Ralink")+ " " + _("WLAN adapter.")
				else:
					return str(os_path.basename(os_path.realpath(driverdir))) + " " + _("WLAN adapter")
			else:
				return _("Unknown network adapter")
		else:
			return _("Unknown network adapter")

	def __onClose(self):
		for x in self["config"].list:
			x[1].cancel()
		apModeConfig.wpa.value = "0"
		apModeConfig.wep.value = False

	def keyCancel(self):
		self.close()

def main(session, **kwargs):
	session.open(WirelessAccessPoint)

def Plugins(**kwargs):
	return [PluginDescriptor(name=_("Wireless Access Point"), description="Using a Wireless module as access point.", where = PluginDescriptor.WHERE_PLUGINMENU, needsRestart = True, fnc=main)]

