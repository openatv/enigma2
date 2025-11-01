from re import escape as re_escape

from enigma import eTimer

from Screens.Screen import Screen
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Pixmap import MultiPixmap
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Components.config import config, ConfigYesNo, NoSave, ConfigSubsection, ConfigText, ConfigSelection, ConfigPassword
from Components.Network import iNetwork
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap
from .Wlan import iWlan, iStatus, getWlanConfigName


liste = ["Unencrypted", "WEP", "WPA", "WPA/WPA2", "WPA2"]

weplist = ["ASCII", "HEX"]

config.plugins.wlan = ConfigSubsection()
config.plugins.wlan.essid = NoSave(ConfigText(default="", fixed_size=False))
config.plugins.wlan.hiddenessid = NoSave(ConfigYesNo(default=False))
config.plugins.wlan.encryption = NoSave(ConfigSelection(liste, default="WPA2"))
config.plugins.wlan.wepkeytype = NoSave(ConfigSelection(weplist, default="ASCII"))
config.plugins.wlan.psk = NoSave(ConfigPassword(default="", fixed_size=False))


class WlanStatus(Screen):
	skin = """
		<screen name="WlanStatus" position="center,center" size="560,430" title="Wireless network status" resolution="1280,720">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />

			<widget source="LabelBSSID" render="Label" position="10,60" size="200,25" valign="left" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelESSID" render="Label" position="10,90" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelQuality" render="Label" position="10,120" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelChannel" render="Label" position="10,150" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelFrequency" render="Label" position="10,180" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelFrequencyNorm" render="Label" position="10,210" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelSignal" render="Label" position="10,240" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelBitrate" render="Label" position="10,270" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelEnc" render="Label" position="10,300" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelEncType" render="Label" position="10,330" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />

			<widget source="BSSID" render="Label" position="220,60" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="ESSID" render="Label" position="220,90" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="quality" render="Label" position="220,120" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="channel" render="Label" position="220,150" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="frequency" render="Label" position="220,180" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="frequency_norm" render="Label" position="220,210" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="signal" render="Label" position="220,240" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="bitrate" render="Label" position="220,270" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="enc" render="Label" position="220,300" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="encryption_type" render="Label" position="220,330" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />

			<ePixmap pixmap="skin_default/div-h.png" position="0,370" zPosition="1" size="560,2" />
			<widget source="IFtext" render="Label" position="10,375" size="120,21" zPosition="10" font="Regular;20" halign="left" backgroundColor="#25062748" transparent="1" />
			<widget source="IF" render="Label" position="120,375" size="400,21" zPosition="10" font="Regular;20" halign="left" backgroundColor="#25062748" transparent="1" />
			<widget source="Statustext" render="Label" position="10,395" size="115,21" zPosition="10" font="Regular;20" halign="left" backgroundColor="#25062748" transparent="1"/>
			<widget name="statuspic" pixmaps="skin_default/buttons/button_green.png,skin_default/buttons/button_green_off.png" position="130,400" zPosition="10" size="15,16" transparent="1" alphatest="on"/>
		</screen>"""

	def __init__(self, session, iface):
		Screen.__init__(self, session)
		self.iface = iface

		self["LabelBSSID"] = StaticText(_("Access point") + ":")
		self["LabelESSID"] = StaticText(_("SSID") + ":")
		self["LabelQuality"] = StaticText(_("Link quality:"))
		self["LabelSignal"] = StaticText(_("Signal strength") + ":")
		self["LabelBitrate"] = StaticText(_("Bitrate") + ":")
		self["LabelEnc"] = StaticText(_("Encryption") + ":")

		self["LabelChannel"] = StaticText(_("Channel") + ":")
		self["LabelEncType"] = StaticText(_("Encryption Type:"))
		self["LabelFrequency"] = StaticText(_("Frequency") + ":")
		self["LabelFrequencyNorm"] = StaticText(_("Frequency Norm:"))

		self["BSSID"] = StaticText()
		self["ESSID"] = StaticText()
		self["quality"] = StaticText()
		self["signal"] = StaticText()
		self["bitrate"] = StaticText()
		self["enc"] = StaticText()

		self["channel"] = StaticText()
		self["encryption_type"] = StaticText()
		self["frequency"] = StaticText()
		self["frequency_norm"] = StaticText()

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
		self.onShown.append(lambda: self.timer.start(16000))
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.cleanup)

	def cleanup(self):
		iStatus.stopWlanConsole()

	def layoutFinished(self):
		self.setTitle(_("Wireless network state"))

	def resetList(self):
		iStatus.getDataForInterface(self.iface, self.getInfoCB)

	def getInfoCB(self, data, status):
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
					if "BSSID" in self:
						self["BSSID"].setText(accesspoint)
					if "ESSID" in self:
						self["ESSID"].setText(essid)

					quality = status[self.iface]["quality"]
					if "quality" in self:
						self["quality"].setText(quality)

					if status[self.iface]["bitrate"] == '0':
						bitrate = _("Unsupported")
					else:
						bitrate = str(status[self.iface]["bitrate"])
					if "bitrate" in self:
						self["bitrate"].setText(bitrate)

					signal = str(status[self.iface]["signal"]) + " dBm"
					if "signal" in self:
						self["signal"].setText(signal)

					if status[self.iface]["encryption"] == "off":
						if accesspoint == "Not-Associated":
							encryption = _("Disabled")
						else:
							encryption = _("off or wpa2 on")
					else:
						encryption = _("Enabled")
					if "enc" in self:
						self["enc"].setText(encryption)

					channel = str(status[self.iface]["channel"])
					if "channel" in self:
						self["channel"].setText(channel)

					encryption_type = status[self.iface]["encryption_type"]
					if "encryption_type" in self:
						self["encryption_type"].setText(encryption_type)

					frequency = status[self.iface]["frequency"]
					if "frequency" in self:
						self["frequency"].setText(frequency)

					frequency_norm = status[self.iface]["frequency_norm"]
					if "frequency_norm" in self:
						self["frequency_norm"].setText(frequency_norm)

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
		self["channel"].setText(wait_txt)
		self["encryption_type"].setText(wait_txt)
		self["frequency"].setText(wait_txt)
		self["frequency_norm"].setText(wait_txt)
		self["IFtext"].setText(_("Network:"))
		self["IF"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		self["Statustext"].setText(_("Link:"))

	def updateStatusLink(self, status):
		if status is not None:
			if status[self.iface]["essid"] == "off" or status[self.iface]["accesspoint"] == "Not-Associated" or status[self.iface]["accesspoint"] is False:
				self["statuspic"].setPixmapNum(1)
			else:
				self["statuspic"].setPixmapNum(0)
			self["statuspic"].show()


class WlanScan(Screen):
	skin = """
		<screen name="WlanScan" position="center,center" size="560,400" title="Select a wireless network" resolution="1280,720">
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
							MultiContentEntryText(pos = (245, 0), size = (200, 20), font=1, flags = RT_HALIGN_LEFT, text = 6), # index 6 is the frequency_norm
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
		self.iface = iface
		self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")
		self.APList = None
		self.newAPList = None
		self.WlanList = None
		self.cleanList = None
		self.oldlist = {}
		self.listLength = None
		self.divpng = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))

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
		self.getAccessPoints(refresh=False)

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

	def buildEntryComponent(self, essid, bssid, encrypted, iface, maxrate, signal, frequency_norm):
		encryption = encrypted and _("Yes") or _("No")
		maxrate = maxrate[-1] if isinstance(maxrate, list) else maxrate
		return essid, bssid, _("Signal: ") + str(signal) + " dB", _("Max. bitrate: ") + str(maxrate), _("Encrypted: ") + encryption, _("Interface: ") + str(iface), frequency_norm, self.divpng

	def updateAPList(self):
		newList = self.getAccessPoints(refresh=True)  # noqa F841
		self.newAPList = []
		tmpList = []
		newListIndex = None
		currentListEntry = None
		currentListIndex = None  # noqa F841

		for ap in list(self.oldlist.keys()):
			data = self.oldlist[ap]['data']
			if data is not None:
				tmpList.append(data)

		if len(tmpList):
			for entry in tmpList:
				self.newAPList.append(self.buildEntryComponent(entry[0], entry[1], entry[2], entry[3], entry[4], entry[5], entry[6]))

			currentListEntry = self["list"].getCurrent()
			if currentListEntry is not None:
				idx = 0
				for entry in self.newAPList:
					if entry[0] == currentListEntry[0]:
						newListIndex = idx
					idx += 1
			self['list'].setList(self.newAPList)
			if newListIndex is not None:
				self["list"].setIndex(newListIndex)
			self["list"].updateList(self.newAPList)
			self.listLength = len(self.newAPList)
			self.buildWlanList()
			self.setInfo()

	def getAccessPoints(self, refresh=False):
		self.APList = []
		self.cleanList = []
		aps = iWlan.getNetworkList()
		if aps is not None:
			print("[WirelessLan.py] got Accespoints!")
			tmpList = []
			compList = []
			for ap in aps:
				a = aps[ap]
				if a['active']:
					tmpList.append((a['essid'], a['bssid']))
					compList.append((a['essid'], a['bssid'], a['encrypted'], a['iface'], a['maxrate'], a['signal'], a['frequency_norm']))

			for entry in tmpList:
				if entry[0] == "":
					for compentry in compList:
						if compentry[1] == entry[1]:
							compList.remove(compentry)
			for entry in compList:
				self.cleanList.append((entry[0], entry[1], entry[2], entry[3], entry[4], entry[5], entry[6]))
				if entry[0] not in self.oldlist:
					self.oldlist[entry[0]] = {'data': entry}
				else:
					self.oldlist[entry[0]]['data'] = entry

		for entry in self.cleanList:
			self.APList.append(self.buildEntryComponent(entry[0], entry[1], entry[2], entry[3], entry[4], entry[5], entry[6]))

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
			self.WlanList.append((entry[0], entry[0]))

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
	if driver == "brcm-wl":
		encryption = config.plugins.wlan.encryption.value
		if encryption == "WPA/WPA2":
			encryption = "WPA2"
		encryption = encryption.lower()
		if encryption == "unencrypted":
			encryption = "None"
		ret += '\tpre-up wl-config.sh -m ' + encryption + ' -k ' + config.plugins.wlan.psk.value + ' -s \"' + config.plugins.wlan.essid.value + '\" || true\n'
		ret += '\tpost-down wl-down.sh || true\n'
		return ret
	if driver == 'madwifi' and config.plugins.wlan.hiddenessid.value:
		ret += "\tpre-up iwconfig " + iface + " essid \"" + re_escape(config.plugins.wlan.essid.value) + "\" || true\n"
	ret += "\tpre-up wpa_supplicant -i" + iface + " -c" + getWlanConfigName(iface) + " -B -dd -D" + driver + " || true\n"
	if config.plugins.wlan.hiddenessid.value is True:
		ret += "\tpre-up iwconfig " + iface + " essid \"" + re_escape(config.plugins.wlan.essid.value) + "\" || true\n"
	ret += "\tpre-down wpa_cli -i" + iface + " terminate || true\n"
	return ret


def Plugins(**kwargs):
	return PluginDescriptor(name=_("Wireless LAN"), description=_("Connect to a wireless network"), where=PluginDescriptor.WHERE_NETWORKSETUP, needsRestart=False, fnc={"ifaceSupported": callFunction, "configStrings": configStrings, "WlanPluginEntry": lambda x: _("Wireless network configuration...")})
