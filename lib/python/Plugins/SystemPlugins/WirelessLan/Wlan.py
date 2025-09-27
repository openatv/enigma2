from re import compile
from os.path import exists
from wifi.scan import Cell

from Components.config import ConfigPassword, ConfigSelection, ConfigSubsection, ConfigText, ConfigYesNo, NoSave, config
from Components.Console import Console
from Components.Network import iNetwork
from Tools.Directories import fileReadLines, fileWriteLines

MODULE_NAME = __name__.split(".")[-1]
MODE_LIST = ["WPA/WPA2", "WPA2", "WPA", "WEP", "Unencrypted"]
WEP_LIST = ["ASCII", "HEX"]

config.plugins.wlan = ConfigSubsection()
config.plugins.wlan.essid = NoSave(ConfigText(default="", fixed_size=False))
config.plugins.wlan.hiddenessid = NoSave(ConfigYesNo(default=False))
config.plugins.wlan.encryption = NoSave(ConfigSelection(MODE_LIST, default="WPA/WPA2"))
config.plugins.wlan.wepkeytype = NoSave(ConfigSelection(WEP_LIST, default="ASCII"))
config.plugins.wlan.psk = NoSave(ConfigPassword(default="", fixed_size=False))


def getWlanConfigName(iface):
	driver = iNetwork.detectWlanModule(iface)
	if driver == "brcm-wl":
		return "/etc/wl.conf.%s" % iface
	return "/etc/wpa_supplicant.%s.conf" % iface


class Wlan:
	def __init__(self, iface=None):
		self.iface = iface
		self.oldInterfaceState = None
		a = ""
		b = ""
		for i in range(0, 255):
			a += chr(i)
			b += " " if i < 32 or i > 127 else chr(i)
		self.asciiTrans = str.maketrans(a, b)

	def asciify(self, str):
		return str.translate(self.asciiTrans)

	def getWirelessInterfaces(self):
		device = compile("[a-z]{2,}[0-9]*:")
		ifNames = []
		lines = fileReadLines("/proc/net/wireless", default=[], source=MODULE_NAME)
		for line in lines:
			try:
				ifNames.append(device.search(line).group()[:-1])
			except AttributeError:
				pass
		return ifNames

	def setInterface(self, iface=None):
		self.iface = iface

	def getInterface(self):
		return self.iface

	def getNetworkList(self):
		if self.oldInterfaceState is None:
			self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")
		if self.oldInterfaceState is False:
			if iNetwork.getAdapterAttribute(self.iface, "up") is False:
				iNetwork.setAdapterAttribute(self.iface, "up", True)
				Console().ePopen(["/sbin/ifconfig", "/sbin/ifconfig", self.iface, "up"])
				driver = iNetwork.detectWlanModule(self.iface)
				if driver == "brcm-wl":
					Console().ePopen(["/usr/bin/wl", "/usr/bin/wl", "up"])
		try:
			scanResults = list(Cell.all(self.iface, 5))
			print("[Wlan] Scan results = '%s'." % scanResults)
		except Exception:
			scanResults = None
			print("[Wlan] No wireless networks could be found.")
		aps = {}
		if scanResults:
			for i in range(len(scanResults)):
				bssid = scanResults[i].ssid
				aps[bssid] = {
					"active": True,
					"bssid": scanResults[i].ssid,
					"essid": scanResults[i].ssid,
					"channel": scanResults[i].channel,
					"encrypted": scanResults[i].encrypted,
					"encryption_type": scanResults[i].encryption_type if scanResults[i].encrypted else "none",
					"iface": self.iface,
					"maxrate": scanResults[i].bitrates,
					"mode": scanResults[i].mode,
					"quality": scanResults[i].quality,
					"signal": scanResults[i].signal,
					"frequency": scanResults[i].frequency,
					"frequency_norm": scanResults[i].frequency_norm,
					"address": scanResults[i].address,
					"noise": scanResults[i].noise,
					"pairwise_ciphers": scanResults[i].pairwise_ciphers,
					"authentication_suites": scanResults[i].authentication_suites,
				}
		return aps

	def stopGetNetworkList(self):
		if self.oldInterfaceState is not None:
			if self.oldInterfaceState is False:
				iNetwork.setAdapterAttribute(self.iface, "up", False)
				Console().ePopen(["/sbin/ifconfig", "/sbin/ifconfig", self.iface, "down"])
				driver = iNetwork.detectWlanModule(self.iface)
				if driver == "brcm-wl":
					Console().ePopen(["/usr/bin/wl", "/usr/bin/wl", "down"])
				self.oldInterfaceState = None
				self.iface = None


iWlan = Wlan()


class brcmWLConfig:
	def __init__(self):
		pass

	def writeConfig(self, iface):
		essid = config.plugins.wlan.essid.value
		hiddenessid = config.plugins.wlan.hiddenessid.value  # noqa F841
		encryption = config.plugins.wlan.encryption.value
		wepkeytype = config.plugins.wlan.wepkeytype.value  # noqa F841
		psk = config.plugins.wlan.psk.value
		contents = ["ssid=%s\n" % essid]
		if encryption in ("WPA", "WPA2", "WPA/WPA2", "WEP"):
			if encryption == "WPA/WPA2":
				encryption = "WPA2"
			contents.append("method=%s" % encryption.lower())
			if encryption.lower() == "unencrypted":
				contents.append("method=None")
			contents.append("key=%s" % psk)
		fileWriteLines(getWlanConfigName(iface), lines=contents, source=MODULE_NAME)

	def loadConfig(self, iface):
		config.plugins.wlan.hiddenessid.value = False
		config.plugins.wlan.wepkeytype.value = "ASCII"
		config.plugins.wlan.essid.value = ""
		config.plugins.wlan.encryption.value = "WPA2"
		config.plugins.wlan.psk.value = ""
		configFile = getWlanConfigName(iface)
		if exists(configFile):
			print("[Wlan] Parsing config file '%s'." % configFile)
			lines = fileReadLines(configFile, default=[], source=MODULE_NAME)
			for line in lines:
				try:
					(key, value) = line.strip().split("=", 1)
				except ValueError:
					continue
				if key == "ssid":
					config.plugins.wlan.essid.value = value.strip()
				if key == "method":
					method = value.strip()
					if method == "None":
						method = "Unencrypted"
					else:
						method = method.upper()
					config.plugins.wlan.encryption.value = method
				elif key == "key":
					config.plugins.wlan.psk.value = value.strip()
				else:
					continue
		wsconf = {
			"hiddenessid": config.plugins.wlan.hiddenessid.value,
			"ssid": config.plugins.wlan.essid.value,
			"encryption": config.plugins.wlan.encryption.value,
			"wepkeytype": config.plugins.wlan.wepkeytype.value,
			"key": config.plugins.wlan.psk.value,
		}
		return wsconf


class wpaSupplicant:
	def __init__(self):
		pass

	def writeBcmWifiConfig(self, iface, essid, encryption, psk):
		contents = ["ssid=%s" % essid]
		contents.append("method=%s" % encryption)
		contents.append("key=%s" % psk)
		print("[Wlan] writeBcmWifiConfig DEBUG: Content:\n%s" % "\n".join(contents))
		fileWriteLines(getWlanConfigName(iface), lines=contents, source=MODULE_NAME)

	def loadBcmWifiConfig(self, iface):
		wsconf = {}
		wsconf["ssid"] = ""
		wsconf["hiddenessid"] = False  # Not used.
		wsconf["encryption"] = "WPA2"
		wsconf["wepkeytype"] = "ASCII"  # Not used.
		wsconf["key"] = ""
		configFile = getWlanConfigName(iface)
		lines = fileReadLines(configFile, default=None, source=MODULE_NAME)
		if lines is None:
			print("[Wlan] Error: Unable to parse '%s'!" % configFile)
			wsconfig = {  # noqa F841
				"hiddenessid": False,
				"ssid": "",
				"encryption": "WPA2",
				"wepkeytype": "ASCII",
				"key": "",
			}
		else:
			for line in lines:
				try:
					(key, value) = line.strip().split("=", 1)
				except ValueError:
					continue
				if key == "ssid":
					wsconf["ssid"] = value.strip()
				if key == "method":
					wsconf["encryption"] = value.strip()
				elif key == "key":
					wsconf["key"] = value.strip()
				else:
					continue
		for (key, value) in wsconf.items():
			print("[Wlan] DEBUG: Entry wsconf [%s] = '%s'." % (key, value))
		return wsconf

	def writeConfig(self, iface):
		essid = config.plugins.wlan.essid.value
		hiddenessid = config.plugins.wlan.hiddenessid.value
		encryption = config.plugins.wlan.encryption.value
		wepkeytype = config.plugins.wlan.wepkeytype.value
		psk = config.plugins.wlan.psk.value
		contents = ["#WPA Supplicant Configuration by enigma2"]
		contents.append("ctrl_interface=/var/run/wpa_supplicant")
		contents.append("eapol_version=1")
		contents.append("fast_reauth=1")
		contents.append("ap_scan=1")
		contents.append("network={")
		contents.append("\tssid=\"%s\"" % essid)
		if hiddenessid:
			contents.append("\tscan_ssid=1")
		else:
			contents.append("\tscan_ssid=0")
		if encryption in ("WPA", "WPA2", "WPA/WPA2"):
			contents.append("\tkey_mgmt=WPA-PSK")
			if encryption == "WPA":
				contents.append("\tproto=WPA")
				contents.append("\tpairwise=TKIP")
				contents.append("\tgroup=TKIP")
			elif encryption == "WPA2":
				contents.append("\tproto=RSN")
				contents.append("\tpairwise=CCMP")
				contents.append("\tgroup=CCMP")
			else:
				contents.append("\tproto=WPA RSN")
				contents.append("\tpairwise=CCMP TKIP")
				contents.append("\tgroup=CCMP TKIP")
			contents.append("\tpsk=\"%s\"" % psk)
		elif encryption == "WEP":
			contents.append("\tkey_mgmt=NONE")
			if wepkeytype == "ASCII":
				contents.append("\twep_key0=\"%s\"" % psk)
			else:
				contents.append("\twep_key0=%s" % psk)
		else:
			contents.append("\tkey_mgmt=NONE")
		contents.append("}")
		fileWriteLines(getWlanConfigName(iface), lines=contents, source=MODULE_NAME)

	def loadConfig(self, iface):
		configFile = getWlanConfigName(iface)
		if not exists(configFile):
			configFile = "/etc/wpa_supplicant.conf"
		lines = fileReadLines(configFile, default=None, source=MODULE_NAME)
		if lines is None:
			print("[Wlan] Error: Unable to parse '%s'!" % configFile)
			wsconfig = {
				"hiddenessid": False,
				"ssid": "",
				"encryption": "WPA2",
				"wepkeytype": "ASCII",
				"key": "",
			}
		else:
			essid = None  # noqa F841
			encryption = "Unencrypted"
			for line in lines:
				split = line.strip().split("=", 1)
				if split[0] == "scan_ssid":
					config.plugins.wlan.hiddenessid.value = split[1] == "1"
				elif split[0] == "ssid":
					config.plugins.wlan.essid.value = split[1][1:-1]
				elif split[0] == "proto":
					if split[1] == "WPA":
						mode = "WPA"
					if split[1] == "RSN":
						mode = "WPA2"
					if split[1] in ("WPA RSN", "WPA WPA2"):
						mode = "WPA/WPA2"
					encryption = mode
				elif split[0] == "wep_key0":
					encryption = "WEP"
					if split[1].startswith("\"") and split[1].endswith("\""):
						config.plugins.wlan.wepkeytype.value = "ASCII"
						config.plugins.wlan.psk.value = split[1][1:-1]
					else:
						config.plugins.wlan.wepkeytype.value = "HEX"
						config.plugins.wlan.psk.value = split[1]
				elif split[0] == "psk":
					config.plugins.wlan.psk.value = split[1][1:-1]
				else:
					pass
			config.plugins.wlan.encryption.value = encryption
			wsconfig = {
				"hiddenessid": config.plugins.wlan.hiddenessid.value,
				"ssid": config.plugins.wlan.essid.value,
				"encryption": config.plugins.wlan.encryption.value,
				"wepkeytype": config.plugins.wlan.wepkeytype.value,
				"key": config.plugins.wlan.psk.value,
			}
			for (key, item) in list(wsconfig.items()):
				if item == "None" or item == "":
					if key == "hiddenessid":
						wsconfig["hiddenessid"] = False
					if key == "ssid":
						wsconfig["ssid"] = ""
					if key == "encryption":
						wsconfig["encryption"] = "WPA2"
					if key == "wepkeytype":
						wsconfig["wepkeytype"] = "ASCII"
					if key == "key":
						wsconfig["key"] = ""
		return wsconfig


class Status:
	def __init__(self):
		self.wlanIface = {}
		self.backupWlanIface = {}
		self.statusCallback = None
		self.wlanConsole = Console()

	def stopWlanConsole(self):
		if self.wlanConsole is not None:
			print("[Wlan] Killing self.wlanConsole.")
			self.wlanConsole.killAll()
			self.wlanConsole = None

	def getDataForInterface(self, iface, callback=None):
		self.wlanConsole = Console()
		if callback is not None:
			self.statusCallback = callback
		self.wlanConsole.ePopen(["/sbin/iwconfig", "/sbin/iwconfig", iface], self.iwconfigFinished, iface)

	def iwconfigFinished(self, result, retVal, extraArgs):
		iface = extraArgs
		ssid = "off"
		data = {
			"essid": False,
			"frequency": False,
			"accesspoint": False,
			"bitrate": False,
			"encryption": False,
			"quality": False,
			"signal": False,
			"channel": False,
			"encryption_type": False,
			"frequency_norm": False
		}
		for line in result.splitlines():
			line = line.strip()
			if "ESSID" in line:
				if "off/any" in line:
					ssid = "off"
				else:
					if "Nickname" in line:
						ssid = (line[line.index("ESSID") + 7:line.index("\"  Nickname")])
					else:
						ssid = (line[line.index("ESSID") + 7:len(line) - 1])
				if ssid != "off":
					data["essid"] = ssid
			if "Access Point" in line:
				if "Sensitivity" in line:
					ap = line[line.index("Access Point") + 14:line.index("   Sensitivity")]
				else:
					ap = line[line.index("Access Point") + 14:len(line)]
				if ap is not None:
					data["accesspoint"] = ap
			if "Frequency" in line:
				frequency = line[line.index("Frequency") + 10:line.index(" GHz")]
				if frequency is not None:
					data["frequency"] = frequency
			if "Bit Rate" in line:
				if "kb" in line:
					br = line[line.index("Bit Rate") + 9:line.index(" kb/s")]
				elif "Gb" in line:
					br = line[line.index("Bit Rate") + 9:line.index(" Gb/s")]
				else:
					br = line[line.index("Bit Rate") + 9:line.index(" Mb/s")]
				if br is not None:
					data["bitrate"] = br
			if "Encryption key" in line:
				if ":off" in line:
					enc = "off"
				elif "Security" in line:
					enc = line[line.index("Encryption key") + 15:line.index("   Security")]
					if enc:
						enc = "on"
				else:
					enc = line[line.index("Encryption key") + 15:len(line)]
					if enc:
						enc = "on"
				if enc:
					data["encryption"] = enc
			if "Quality" in line:
				if "/100" in line:
					qual = line[line.index("Quality") + 8:line.index("  Signal")]
				else:
					qual = line[line.index("Quality") + 8:line.index("Sig")]
				if qual:
					data["quality"] = qual
			if "Signal level" in line:
				if "dBm" in line:
					signal = line[line.index("Signal level") + 13:line.index(" dBm")] + " dBm"
				elif "/100" in line:
					if "Noise" in line:
						signal = line[line.index("Signal level") + 13:line.index("  Noise")]
					else:
						signal = line[line.index("Signal level") + 13:len(line)]
				else:
					if "Noise" in line:
						signal = line[line.index("Signal level") + 13:line.index("  Noise")]
					else:
						signal = line[line.index("Signal level") + 13:len(line)]
				if signal:
					data["signal"] = signal
		if ssid is not None and ssid != "off" and ssid != "":
			try:
				scanResults = list(Cell.all(iface, 5))
				print("[Wlan] Scan results = '%s'." % scanResults)
			except Exception:
				scanResults = None
				print("[Wlan] No wireless networks could be found.")
			aps = {}
			if scanResults:
				for i in range(len(scanResults)):
					bssid = scanResults[i].ssid
					aps[bssid] = {
						"active": True,
						"bssid": scanResults[i].ssid,
						"essid": scanResults[i].ssid,
						"channel": scanResults[i].channel,
						"encrypted": scanResults[i].encrypted,
						"encryption_type": scanResults[i].encryption_type if scanResults[i].encrypted else "none",
						"iface": iface,
						"maxrate": scanResults[i].bitrates,
						"mode": scanResults[i].mode,
						"quality": scanResults[i].quality,
						"signal": scanResults[i].signal,
						"frequency": scanResults[i].frequency,
						"frequency_norm": scanResults[i].frequency_norm,
						"address": scanResults[i].address,
						"noise": scanResults[i].noise,
						"pairwise_ciphers": scanResults[i].pairwise_ciphers,
						"authentication_suites": scanResults[i].authentication_suites,
					}
				# data["bitrate"] = aps[ssid]["maxrate"]
				data["encryption"] = aps[ssid]["encrypted"]
				data["quality"] = aps[ssid]["quality"]
				data["signal"] = aps[ssid]["signal"]
				data["channel"] = aps[ssid]["channel"]
				data["encryption_type"] = aps[ssid]["encryption_type"]
				# data["frequency"] = aps[ssid]["frequency"]
				data["frequency_norm"] = aps[ssid]["frequency_norm"]
		self.wlanIface[iface] = data
		self.backupWlanIface = self.wlanIface
		if self.wlanConsole is not None:
			if not self.wlanConsole.appContainers:
				print("[Wlan] self.wlanIface after loading: '%s'." % str(self.wlanIface))
				if self.statusCallback is not None:
					self.statusCallback(True, self.wlanIface)
					self.statusCallback = None

	def getAdapterAttribute(self, iface, attribute):
		self.iface = iface
		if self.iface in self.wlanIface:
			if attribute in self.wlanIface[self.iface]:
				return self.wlanIface[self.iface][attribute]
		return None


iStatus = Status()
