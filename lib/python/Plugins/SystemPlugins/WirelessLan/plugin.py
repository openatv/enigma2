from enigma import eTimer, eEnv
from Screens.Screen import Screen
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Pixmap import Pixmap,MultiPixmap
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Components.MenuList import MenuList
from Components.config import config, getConfigListEntry, ConfigYesNo, NoSave, ConfigSubsection, ConfigText, ConfigSelection, ConfigPassword
from Components.ConfigList import ConfigListScreen
from Components.Network import iNetwork
from Components.Console import Console
from Plugins.Plugin import PluginDescriptor
from os import system, path as os_path, listdir
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_SKIN_IMAGE
from Tools.LoadPixmap import LoadPixmap
from Wlan import iWlan, wpaSupplicant, iStatus, getWlanConfigName
from time import time
from os import system
from re import escape as re_escape

plugin_path = eEnv.resolve("${libdir}/enigma2/python/Plugins/SystemPlugins/WirelessLan")


list = []
list.append("Unencrypted")
list.append("WEP")
list.append("WPA")
list.append("WPA/WPA2")
list.append("WPA2")

weplist = []
weplist.append("ASCII")
weplist.append("HEX")

config.plugins.wlan = ConfigSubsection()
config.plugins.wlan.essid = NoSave(ConfigText(default = "", fixed_size = False))
config.plugins.wlan.hiddenessid = NoSave(ConfigYesNo(default = False))
config.plugins.wlan.encryption = NoSave(ConfigSelection(list, default = "WPA2"))
config.plugins.wlan.wepkeytype = NoSave(ConfigSelection(weplist, default = "ASCII"))
config.plugins.wlan.psk = NoSave(ConfigPassword(default = "", fixed_size = False))



class WlanStatus(Screen):
	skin = """
		<screen name="WlanStatus" position="center,center" size="560,400" title="Wireless network status" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />

			<widget source="LabelBSSID" render="Label" position="10,60" size="200,25" valign="left" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelESSID" render="Label" position="10,100" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelQuality" render="Label" position="10,140" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelSignal" render="Label" position="10,180" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelBitrate" render="Label" position="10,220" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelEnc" render="Label" position="10,260" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="BSSID" render="Label" position="220,60" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="ESSID" render="Label" position="220,100" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="quality" render="Label" position="220,140" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="signal" render="Label" position="220,180" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="bitrate" render="Label" position="220,220" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="enc" render="Label" position="220,260" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />

			<ePixmap pixmap="skin_default/div-h.png" position="0,350" zPosition="1" size="560,2" />
			<widget source="IFtext" render="Label" position="10,355" size="120,21" zPosition="10" font="Regular;20" halign="left" backgroundColor="#25062748" transparent="1" />
			<widget source="IF" render="Label" position="120,355" size="400,21" zPosition="10" font="Regular;20" halign="left" backgroundColor="#25062748" transparent="1" />
			<widget source="Statustext" render="Label" position="10,375" size="115,21" zPosition="10" font="Regular;20" halign="left" backgroundColor="#25062748" transparent="1"/>
			<widget name="statuspic" pixmaps="skin_default/buttons/button_green.png,skin_default/buttons/button_green_off.png" position="130,380" zPosition="10" size="15,16" transparent="1" alphatest="on"/>
		</screen>"""

	def __init__(self, session, iface):
		Screen.__init__(self, session)
		self.session = session
		self.iface = iface

		self["LabelBSSID"] = StaticText(_('Accesspoint:'))
		self["LabelESSID"] = StaticText(_('SSID:'))
		self["LabelQuality"] = StaticText(_('Link quality:'))
		self["LabelSignal"] = StaticText(_('Signal strength:'))
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
		self.onShown.append(lambda: self.timer.start(8000))
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.cleanup)

	def cleanup(self):
		iStatus.stopWlanConsole()

	def layoutFinished(self):
		self.setTitle(_("Wireless network state"))

	def resetList(self):
		iStatus.getDataForInterface(self.iface,self.getInfoCB)

	def getInfoCB(self,data,status):
		if data is not None:
			if data is True:
				if status is not None:
					if status[self.iface]["essid"] == "off":
						essid = _("No Connection")
					else:
						essid = status[self.iface]["essid"]
					if status[self.iface]["accesspoint"] == "Not-Associated":
						accesspoint = _("Not associated")
						essid = _("No Connection")
					else:
						accesspoint = status[self.iface]["accesspoint"]
					if self.has_key("BSSID"):
						self["BSSID"].setText(accesspoint)
					if self.has_key("ESSID"):
						self["ESSID"].setText(essid)

					quality = status[self.iface]["quality"]
					if self.has_key("quality"):
						self["quality"].setText(quality)

					if status[self.iface]["bitrate"] == '0':
						bitrate = _("Unsupported")
					else:
						bitrate = str(status[self.iface]["bitrate"]) + " Mb/s"
					if self.has_key("bitrate"):
						self["bitrate"].setText(bitrate)

					signal = status[self.iface]["signal"]
					if self.has_key("signal"):
						self["signal"].setText(signal)

					if status[self.iface]["encryption"] == "off":
						if accesspoint == "Not-Associated":
							encryption = _("Disabled")
						else:
							encryption = _("off or wpa2 on")
					else:
						encryption = _("Enabled")
					if self.has_key("enc"):
						self["enc"].setText(encryption)
					self.updateStatusLink(status)

	def exit(self):
		self.timer.stop()
		self.close(True)

	def updateStatusbar(self):
		wait_txt = _("Please wait...")
		self["BSSID"].setText(wait_txt)
		self["ESSID"].setText(wait_txt)
		self["quality"].setText(wait_txt)
		self["signal"].setText(wait_txt)
		self["bitrate"].setText(wait_txt)
		self["enc"].setText(wait_txt)
		self["IFtext"].setText(_("Network:"))
		self["IF"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		self["Statustext"].setText(_("Link:"))

	def updateStatusLink(self,status):
		if status is not None:
			if status[self.iface]["essid"] == "off" or status[self.iface]["accesspoint"] == "Not-Associated" or status[self.iface]["accesspoint"] == False:
				self["statuspic"].setPixmapNum(1)
			else:
				self["statuspic"].setPixmapNum(0)
			self["statuspic"].show()


class WlanScan(Screen):
	skin = """
		<screen name="WlanScan" position="center,center" size="560,400" title="Select a wireless network" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="list" render="Listbox" position="5,40" size="550,300" scrollbarMode="showOnDemand">
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (0, 0), size = (550, 30), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the essid
							MultiContentEntryText(pos = (0, 30), size = (175, 20), font=1, flags = RT_HALIGN_LEFT, text = 5), # index 5 is the interface
							MultiContentEntryText(pos = (175, 30), size = (175, 20), font=1, flags = RT_HALIGN_LEFT, text = 4), # index 0 is the encryption
							MultiContentEntryText(pos = (350, 0), size = (200, 20), font=1, flags = RT_HALIGN_LEFT, text = 2), # index 0 is the signal
							MultiContentEntryText(pos = (350, 30), size = (200, 20), font=1, flags = RT_HALIGN_LEFT, text = 3), # index 0 is the maxrate
							MultiContentEntryPixmapAlphaTest(pos = (0, 52), size = (550, 2), png = 6), # index 6 is the div pixmap
						],
					"fonts": [gFont("Regular", 28),gFont("Regular", 18)],
					"itemHeight": 54
					}
				</convert>
			</widget>
			<ePixmap pixmap="skin_default/div-h.png" position="0,340" zPosition="1" size="560,2" />
			<widget source="info" render="Label" position="0,350" size="560,50" font="Regular;24" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
		</screen>"""

	def __init__(self, session, iface):
		Screen.__init__(self, session)
		self.session = session
		self.iface = iface
		self.skin_path = plugin_path
		self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")
		self.APList = None
		self.newAPList = None
		self.WlanList = None
		self.cleanList = None
		self.oldlist = {}
		self.listLength = None
		self.divpng = LoadPixmap(path=resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/div-h.png"))

		self.rescanTimer = eTimer()
		self.rescanTimer.callback.append(self.rescanTimerFired)

		self["info"] = StaticText()

		self.list = []
		self["list"] = List(self.list)

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Connect"))
		self["key_yellow"] = StaticText()

		self["actions"] = NumberActionMap(["WizardActions", "InputActions", "EPGSelectActions"],
		{
			"ok": self.select,
			"back": self.cancel,
		}, -1)

		self["shortcuts"] = ActionMap(["ShortcutActions"],
		{
			"red": self.cancel,
			"green": self.select,
		})
		iWlan.setInterface(self.iface)
		self.w = iWlan.getInterface()
		self.onLayoutFinish.append(self.layoutFinished)
		self.getAccessPoints(refresh = False)

	def layoutFinished(self):
		self.setTitle(_("Select a wireless network"))

	def select(self):
		cur = self["list"].getCurrent()
		if cur is not None:
			iWlan.stopGetNetworkList()
			self.rescanTimer.stop()
			del self.rescanTimer
			if cur[0] is not None:
				self.close(cur[0])
			else:
				self.close(None)
		else:
			iWlan.stopGetNetworkList()
			self.rescanTimer.stop()
			del self.rescanTimer
			self.close(None)

	def cancel(self):
		iWlan.stopGetNetworkList()
		self.rescanTimer.stop()
		del self.rescanTimer
		self.close(None)

	def rescanTimerFired(self):
		self.rescanTimer.stop()
		self.updateAPList()

	def buildEntryComponent(self, essid, bssid, encrypted, iface, maxrate, signal):
		encryption = encrypted and _("Yes") or _("No")
		return((essid, bssid, _("Signal: ") + str(signal), _("Max. bitrate: ") + str(maxrate), _("Encrypted: ") + encryption, _("Interface: ") + str(iface), self.divpng))

	def updateAPList(self):
		newList = []
		newList = self.getAccessPoints(refresh = True)
		self.newAPList = []
		tmpList = []
		newListIndex = None
		currentListEntry = None
		currentListIndex = None

		for ap in self.oldlist.keys():
			data = self.oldlist[ap]['data']
			if data is not None:
				tmpList.append(data)

		if len(tmpList):
			for entry in tmpList:
				self.newAPList.append(self.buildEntryComponent( entry[0], entry[1], entry[2], entry[3], entry[4], entry[5] ))

			currentListEntry = self["list"].getCurrent()
			if currentListEntry is not None:
				idx = 0
				for entry in self.newAPList:
					if entry[0] == currentListEntry[0]:
						newListIndex = idx
					idx +=1
			self['list'].setList(self.newAPList)
			if newListIndex is not None:
				self["list"].setIndex(newListIndex)
			self["list"].updateList(self.newAPList)
			self.listLength = len(self.newAPList)
			self.buildWlanList()
			self.setInfo()

	def getAccessPoints(self, refresh = False):
		self.APList = []
		self.cleanList = []
		aps = iWlan.getNetworkList()
		if aps is not None:
			print "[WirelessLan.py] got Accespoints!"
			tmpList = []
			compList = []
			for ap in aps:
				a = aps[ap]
				if a['active']:
					tmpList.append( (a['essid'], a['bssid']) )
					compList.append( (a['essid'], a['bssid'], a['encrypted'], a['iface'], a['maxrate'], a['signal']) )

			for entry in tmpList:
				if entry[0] == "":
					for compentry in compList:
						if compentry[1] == entry[1]:
							compList.remove(compentry)
			for entry in compList:
				self.cleanList.append( ( entry[0], entry[1], entry[2], entry[3], entry[4], entry[5] ) )
				if not self.oldlist.has_key(entry[0]):
					self.oldlist[entry[0]] = { 'data': entry }
				else:
					self.oldlist[entry[0]]['data'] = entry

		for entry in self.cleanList:
			self.APList.append(self.buildEntryComponent( entry[0], entry[1], entry[2], entry[3], entry[4], entry[5] ))

		if refresh is False:
			self['list'].setList(self.APList)
		self.listLength = len(self.APList)
		self.setInfo()
		self.rescanTimer.start(5000)
		return self.cleanList

	def setInfo(self):
		length = self.getLength()
		if length == 0:
			self["info"].setText(_("No wireless networks found! Searching..."))
		else:
			self["info"].setText(ngettext("%d wireless network found!", "%d wireless networks found!", length) % length)

	def buildWlanList(self):
		self.WlanList = []
		for entry in self['list'].list:
			self.WlanList.append( (entry[0], entry[0]) )

	def getLength(self):
		return self.listLength

	def getWlanList(self):
		if self.WlanList is None:
			self.buildWlanList()
		return self.WlanList


def WlanStatusScreenMain(session, iface):
	session.open(WlanStatus, iface)

def callFunction(iface):
	iWlan.setInterface(iface)
	i = iWlan.getWirelessInterfaces()
	if iface in i or iNetwork.isWirelessInterface(iface):
		return WlanStatusScreenMain
	return None

def configStrings(iface):
	driver = iNetwork.detectWlanModule(iface)
	ret = ""
	if driver == 'madwifi' and config.plugins.wlan.hiddenessid.value:
		ret += "\tpre-up iwconfig " + iface + " essid \"" + re_escape(config.plugins.wlan.essid.value) + "\" || true\n"
	ret += "\tpre-up wpa_supplicant -i" + iface + " -c" + getWlanConfigName(iface) + " -B -dd -D" + driver + " || true\n"
	ret += "\tpre-down wpa_cli -i" + iface + " terminate || true\n"
	return ret

def Plugins(**kwargs):
	return PluginDescriptor(name=_("Wireless LAN"), description=_("Connect to a wireless network"), where = PluginDescriptor.WHERE_NETWORKSETUP, needsRestart = False, fnc={"ifaceSupported": callFunction, "configStrings": configStrings, "WlanPluginEntry": lambda x: _("Wireless network configuration...")})
