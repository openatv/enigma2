from enigma import eTimer
from Screens.Screen import Screen
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Pixmap import Pixmap,MultiPixmap
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList
from Components.config import config, getConfigListEntry, ConfigYesNo, NoSave, ConfigSubsection, ConfigText, ConfigSelection, ConfigPassword
from Components.ConfigList import ConfigListScreen
from Components.Network import Network, iNetwork
from Components.Console import Console
from Plugins.Plugin import PluginDescriptor
from os import system, path as os_path, listdir
from Wlan import Wlan, WlanList, wpaSupplicant
from Wlan import Status, iStatus

plugin_path = "/usr/lib/enigma2/python/Plugins/SystemPlugins/WirelessLan"

list = []
list.append("WEP")
list.append("WPA")
list.append("WPA2")
list.append("WPA/WPA2")

weplist = []
weplist.append("ASCII")
weplist.append("HEX")

config.plugins.wlan = ConfigSubsection()
config.plugins.wlan.essid = NoSave(ConfigText(default = "home", fixed_size = False))
config.plugins.wlan.hiddenessid = NoSave(ConfigText(default = "home", fixed_size = False))

config.plugins.wlan.encryption = ConfigSubsection()
config.plugins.wlan.encryption.enabled = NoSave(ConfigYesNo(default = False))
config.plugins.wlan.encryption.type = NoSave(ConfigSelection(list, default = "WPA/WPA2" ))
config.plugins.wlan.encryption.wepkeytype = NoSave(ConfigSelection(weplist, default = "ASCII"))
config.plugins.wlan.encryption.psk = NoSave(ConfigPassword(default = "mysecurewlan", fixed_size = False))


class WlanStatus(Screen):
	skin = """
	<screen position="center,center" size="560,400" title="Wireless Network State" >
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />

		<widget source="LabelBSSID" render="Label" position="10,60" size="250,25" valign="left" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
		<widget source="LabelESSID" render="Label" position="10,100" size="250,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
		<widget source="LabelQuality" render="Label" position="10,140" size="250,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
		<widget source="LabelSignal" render="Label" position="10,180" size="250,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
		<widget source="LabelBitrate" render="Label" position="10,220" size="250,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
		<widget source="LabelEnc" render="Label" position="10,260" size="250,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
		
		<widget source="BSSID" render="Label" position="320,60" size="180,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
		<widget source="ESSID" render="Label" position="320,100" size="180,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
		<widget source="quality" render="Label" position="320,140" size="180,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
		<widget source="signal" render="Label" position="320,180" size="180,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
		<widget source="bitrate" render="Label" position="320,220" size="180,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
		<widget source="enc" render="Label" position="320,260" size="180,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />

		<ePixmap pixmap="skin_default/div-h.png" position="0,350" zPosition="1" size="560,2" />		
		<widget source="IFtext" render="Label" position="10,355" size="120,21" zPosition="10" font="Regular;20" halign="left" backgroundColor="#25062748" transparent="1" />
		<widget source="IF" render="Label" position="120,355" size="400,21" zPosition="10" font="Regular;20" halign="left" backgroundColor="#25062748" transparent="1" />
		<widget source="Statustext" render="Label" position="10,375" size="115,21" zPosition="10" font="Regular;20" halign="left" backgroundColor="#25062748" transparent="1"/>
		<widget name="statuspic" pixmaps="skin_default/buttons/button_green.png,skin_default/buttons/button_green_off.png" position="130,380" zPosition="10" size="15,16" transparent="1" alphatest="on"/>
	</screen>
	"""
	
	def __init__(self, session, iface):
		Screen.__init__(self, session)
		self.session = session
		self.iface = iface
		self.skin = WlanStatus.skin
				    
		self["LabelBSSID"] = StaticText(_('Accesspoint:'))
		self["LabelESSID"] = StaticText(_('SSID:'))
		self["LabelQuality"] = StaticText(_('Link Quality:'))
		self["LabelSignal"] = StaticText(_('Signal Strength:'))
		self["LabelBitrate"] = StaticText(_('Bitrate:'))
		self["LabelEnc"] = StaticText(_('Encryption:'))
			
		self["BSSID"] = StaticText()
		self["ESSID"] = StaticText()
		self["quality"] = StaticText()
		self["signal"] = StaticText()
		self["bitrate"] = StaticText()
		self["enc"] = StaticText()

		self["IFtext"] = StaticText()
		self["IF"] = StaticText()
		self["Statustext"] = StaticText()
		self["statuspic"] = MultiPixmap()
		self["statuspic"].hide()
		self["key_red"] = StaticText(_("Close"))

		self.resetList()
		self.updateStatusbar()
		
		self["actions"] = NumberActionMap(["WizardActions", "InputActions", "EPGSelectActions", "ShortcutActions"],
		{
			"ok": self.exit,
			"back": self.exit,
			"red": self.exit,
		}, -1)
		self.timer = eTimer()
		self.timer.timeout.get().append(self.resetList) 
		self.onShown.append(lambda: self.timer.start(5000))
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.cleanup)

	def cleanup(self):
		iStatus.stopWlanConsole()
		
	def layoutFinished(self):
		self.setTitle(_("Wireless Network State"))
		
	def resetList(self):
		print "self.iface im resetlist",self.iface
		iStatus.getDataForInterface(self.iface,self.getInfoCB)
		
	def getInfoCB(self,data,status):
		if data is not None:
			if data is True:
				if status is not None:
					self["BSSID"].setText(status[self.iface]["acesspoint"])
					self["ESSID"].setText(status[self.iface]["essid"])
					self["quality"].setText(status[self.iface]["quality"]+"%")
					self["signal"].setText(status[self.iface]["signal"])
					self["bitrate"].setText(status[self.iface]["bitrate"])
					self["enc"].setText(status[self.iface]["encryption"])
					self.updateStatusLink(status)

	def exit(self):
		self.timer.stop()
		self.close()	

	def updateStatusbar(self):
		print "self.iface im updateStatusbar",self.iface
		self["BSSID"].setText(_("Please wait..."))
		self["ESSID"].setText(_("Please wait..."))
		self["quality"].setText(_("Please wait..."))
		self["signal"].setText(_("Please wait..."))
		self["bitrate"].setText(_("Please wait..."))
		self["enc"].setText(_("Please wait..."))
		self["IFtext"].setText(_("Network:"))
		self["IF"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		self["Statustext"].setText(_("Link:"))

	def updateStatusLink(self,status):
		if status is not None:
			if status[self.iface]["acesspoint"] == "No Connection" or status[self.iface]["acesspoint"] == "Not-Associated" or status[self.iface]["acesspoint"] == False:
				self["statuspic"].setPixmapNum(1)
			else:
				self["statuspic"].setPixmapNum(0)
			self["statuspic"].show()		

class WlanScan(Screen):
	skin = """
	<screen position="center,center" size="560,400" title="Choose a Wireless Network" >
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		<widget name="list" position="5,50" size="550,280" scrollbarMode="showOnDemand" />
		<ePixmap pixmap="skin_default/div-h.png" position="0,340" zPosition="1" size="560,2" />		
		<widget source="info" render="Label" position="0,350" size="560,50" font="Regular;24" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
	</screen>
	"""

	def __init__(self, session, iface):
		Screen.__init__(self, session)
		self.session = session
		self.iface = iface
		self.skin = WlanScan.skin
		self.skin_path = plugin_path
		self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")
		
		self["info"] = StaticText()
		
		self.list = []	
		self["list"] = WlanList(self.session, self.iface)
		
		self.setInfo()

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Connect"))
		self["key_yellow"] = StaticText(_("Refresh"))
			
		self["actions"] = NumberActionMap(["WizardActions", "InputActions", "EPGSelectActions"],
		{
			"ok": self.select,
			"back": self.cancel,
		}, -1)
		
		self["shortcuts"] = ActionMap(["ShortcutActions"],
		{
		 	"red": self.cancel,
			"green": self.select,
			"yellow": self.rescan,
		})
		self.onLayoutFinish.append(self.layoutFinished)
		
	def layoutFinished(self):
		self.setTitle(_("Choose a wireless network"))
	
	def select(self):
		cur = self["list"].getCurrent()
		#print "CURRENT",cur
		if cur is not None:
			if cur[1] is not None:
				essid = cur[0]
				if essid == '':
					essid = cur[1]
				encrypted = cur[2]
				self.close(essid,self["list"].getList())
			else:
				self.close(None,None)
		else:
			self.close(None,None)
	
	def WlanSetupClosed(self, *ret):
		if ret[0] == 2:
			self.close(None)
	
	def rescan(self):
		self["list"].reload()
		self.setInfo()
	
	def cancel(self):
		if self.oldInterfaceState is False:
			iNetwork.deactivateInterface(self.iface,self.deactivateInterfaceCB)
		else:
			self.close(None)

	def deactivateInterfaceCB(self,data):
		if data is not None:
			if data is True:
				iNetwork.getInterfaces(self.cancelCB)
	
	def cancelCB(self,data):			
		if data is not None:
			if data is True:
				self.close(None)

	def setInfo(self):
		length = self["list"].getLength()
		
		if length == 0:
			self["info"].setText(_("No wireless networks found! Please refresh."))
		elif length == 1:
			self["info"].setText(_("1 wireless network found!"))
		else:
			self["info"].setText(str(length)+_(" wireless networks found!"))	


def WlanStatusScreenMain(session, iface):
	session.open(WlanStatus, iface)


def callFunction(iface):
	
	w = Wlan(iface)
	i = w.getWirelessInterfaces()
	if i:
		if iface in i:
			return WlanStatusScreenMain
	
	return None


def configStrings(iface):
	driver = iNetwork.detectWlanModule()
	print "WLAN-MODULE",driver
	if driver == 'ralink':
		return "	pre-up /usr/sbin/wpa_supplicant -i"+iface+" -c/etc/wpa_supplicant.conf -B -Dralink\n	post-down wpa_cli terminate"
	if driver == 'madwifi':
		if config.plugins.wlan.essid.value == "hidden...":
			if ' ' in config.plugins.wlan.hiddenessid.value:
				return '	pre-up iwconfig '+iface+' essid "'+config.plugins.wlan.hiddenessid.value+'"\n	pre-up /usr/sbin/wpa_supplicant -i'+iface+' -c/etc/wpa_supplicant.conf -B -dd -Dmadwifi\n	post-down wpa_cli terminate'
			else:
				return '	pre-up iwconfig '+iface+' essid '+config.plugins.wlan.hiddenessid.value+'\n	pre-up /usr/sbin/wpa_supplicant -i'+iface+' -c/etc/wpa_supplicant.conf -B -dd -Dmadwifi\n	post-down wpa_cli terminate'
		else:
			if ' ' in config.plugins.wlan.essid.value:
				return '	pre-up iwconfig '+iface+' essid "'+config.plugins.wlan.essid.value+'"\n	pre-up /usr/sbin/wpa_supplicant -i'+iface+' -c/etc/wpa_supplicant.conf -B -dd -Dmadwifi\n	post-down wpa_cli terminate'
			else:
				return '	pre-up iwconfig '+iface+' essid '+config.plugins.wlan.essid.value+'\n	pre-up /usr/sbin/wpa_supplicant -i'+iface+' -c/etc/wpa_supplicant.conf -B -dd -Dmadwifi\n	post-down wpa_cli terminate'
	if driver == 'zydas':
		return "	pre-up /usr/sbin/wpa_supplicant -i"+iface+" -c/etc/wpa_supplicant.conf -B -dd -Dzydas\n	post-down wpa_cli terminate"

def Plugins(**kwargs):
	return PluginDescriptor(name=_("Wireless LAN"), description=_("Connect to a Wireless Network"), where = PluginDescriptor.WHERE_NETWORKSETUP, fnc={"ifaceSupported": callFunction, "configStrings": configStrings, "WlanPluginEntry": lambda x: "Wireless Network Configuartion..."})
	