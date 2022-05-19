from re import compile
from os import path as os_path
from wifi.scan import Cell

from Components.config import config, ConfigYesNo, NoSave, ConfigSubsection, ConfigText, ConfigSelection, ConfigPassword
from Components.Console import Console
from Components.Network import iNetwork


modelist = ["WPA/WPA2", "WPA2", "WPA", "WEP", "Unencrypted"]

weplist = ["ASCII", "HEX"]

config.plugins.wlan = ConfigSubsection()
config.plugins.wlan.essid = NoSave(ConfigText(default="", fixed_size=False))
config.plugins.wlan.hiddenessid = NoSave(ConfigYesNo(default=False))
config.plugins.wlan.encryption = NoSave(ConfigSelection(modelist, default="WPA/WPA2"))
config.plugins.wlan.wepkeytype = NoSave(ConfigSelection(weplist, default="ASCII"))
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
		for i in list(range(0, 255)):
			a += chr(i)
			if i < 32 or i > 127:
				b += " "
			else:
				b += chr(i)
		self.asciitrans = str.maketrans(a, b)

	def asciify(self, str):
		return str.translate(self.asciitrans)

	def getWirelessInterfaces(self):
		device = compile("[a-z]{2,}[0-9]*:")
		ifnames = []

		fp = open("/proc/net/wireless", "r")
		for line in fp:
			try:
				ifnames.append(device.search(line).group()[:-1])
			except AttributeError:
				pass

		return ifnames

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
			scanresults = list(Cell.all(self.iface, 5))
			print("[Wlan] Scan results = %s" % scanresults)
		except:
			scanresults = None
			print("[Wlan] No wireless networks could be found")
		aps = {}
		if scanresults:
			for i in range(len(scanresults)):
				bssid = scanresults[i].ssid
				aps[bssid] = {
					"active": True,
					"bssid": scanresults[i].ssid,
					"essid": scanresults[i].ssid,
					"channel": scanresults[i].channel,
					"encrypted": scanresults[i].encrypted,
					"encryption_type": scanresults[i].encryption_type if scanresults[i].encrypted else "none",
					"iface": self.iface,
					"maxrate": scanresults[i].bitrates,
					"mode": scanresults[i].mode,
					"quality": scanresults[i].quality,
					"signal": scanresults[i].signal,
					"frequency": scanresults[i].frequency,
					"frequency_norm": scanresults[i].frequency_norm,
					"address": scanresults[i].address,
					"noise": scanresults[i].noise,
					"pairwise_ciphers": scanresults[i].pairwise_ciphers,
					"authentication_suites": scanresults[i].authentication_suites,
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
		hiddenessid = config.plugins.wlan.hiddenessid.value
		encryption = config.plugins.wlan.encryption.value
		wepkeytype = config.plugins.wlan.wepkeytype.value
		psk = config.plugins.wlan.psk.value

		fp = open(getWlanConfigName(iface), "w")

		fp.write("ssid=%s\n" % essid)
		if encryption in ("WPA", "WPA2", "WPA/WPA2", "WEP"):
			if encryption == "WPA/WPA2":
				encryption = "WPA2"
			fp.write("method=%s\n" % encryption.lower())
		if encryption.lower() == "unencrypted":
			fp.write("method=None\n")
		fp.write("key=%s\n" % psk)
		fp.close()

	def loadConfig(self, iface):
		config.plugins.wlan.hiddenessid.value = False
		config.plugins.wlan.wepkeytype.value = "ASCII"
		config.plugins.wlan.essid.value = ""
		config.plugins.wlan.encryption.value = "WPA2"
		config.plugins.wlan.psk.value = ""
		configfile = getWlanConfigName(iface)

		if os_path.exists(configfile):
			print("[Wlan] parsing configfile: %s" % configfile)
			fd = open(configfile, "r")
			lines = fd.readlines()
			fd.close()
			for line in lines:
				try:
					(key, value) = line.strip().split("=", 1)
				except:
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
		contents = ""
		contents += "ssid=" + essid + "\n"
		contents += "method=" + encryption + "\n"
		contents += "key=" + psk + "\n"
		print("[Wlan] Content = \n%s" % contents)

		fd = open(getWlanConfigName(iface), "w")
		fd.write(contents)
		fd.close()

	def loadBcmWifiConfig(self, iface):
		wsconf = {}
		wsconf["ssid"] = ""
		wsconf["hiddenessid"] = False # not used
		wsconf["encryption"] = "WPA2"
		wsconf["wepkeytype"] = "ASCII" # not used
		wsconf["key"] = ""

		configfile = getWlanConfigName(iface)

		try:
			fd = open(configfile, "r")
			lines = fd.readlines()
			fd.close()

			for line in lines:
				try:
					(key, value) = line.strip().split("=", 1)
				except:
					continue

				if key == "ssid":
					wsconf["ssid"] = value.strip()
				if key == "method":
					wsconf["encryption"] = value.strip()
				elif key == "key":
					wsconf["key"] = value.strip()
				else:
					continue
		except:
			print("[Wlan] Error parsing %s" % configfile)
			wsconfig = {
					"hiddenessid": False,
					"ssid": "",
					"encryption": "WPA2",
					"wepkeytype": "ASCII",
					"key": "",
				}

		for (k, v) in list(wsconf.items()):
			print("[Wlan] wsconf [%s] %s" % (k, v))

		return wsconf

	def writeConfig(self, iface):
		essid = config.plugins.wlan.essid.value
		hiddenessid = config.plugins.wlan.hiddenessid.value
		encryption = config.plugins.wlan.encryption.value
		wepkeytype = config.plugins.wlan.wepkeytype.value
		psk = config.plugins.wlan.psk.value

		fp = open(getWlanConfigName(iface), "w")
		fp.write("#WPA Supplicant Configuration by enigma2\n")
		fp.write("ctrl_interface=/var/run/wpa_supplicant\n")
		fp.write("eapol_version=1\n")
		fp.write("fast_reauth=1\n")
		fp.write("ap_scan=1\n")
		fp.write("network={\n")
		fp.write("\tssid=\"%s\"\n" % essid)
		if hiddenessid:
			fp.write("\tscan_ssid=1\n")
		else:
			fp.write("\tscan_ssid=0\n")
		if encryption in ("WPA", "WPA2", "WPA/WPA2"):
			fp.write("\tkey_mgmt=WPA-PSK\n")
			if encryption == "WPA":
				fp.write("\tproto=WPA\n")
				fp.write("\tpairwise=TKIP\n")
				fp.write("\tgroup=TKIP\n")
			elif encryption == "WPA2":
				fp.write("\tproto=RSN\n")
				fp.write("\tpairwise=CCMP\n")
				fp.write("\tgroup=CCMP\n")
			else:
				fp.write("\tproto=WPA RSN\n")
				fp.write("\tpairwise=CCMP TKIP\n")
				fp.write("\tgroup=CCMP TKIP\n")
			fp.write("\tpsk=\"%s\"\n" % psk)
		elif encryption == "WEP":
			fp.write("\tkey_mgmt=NONE\n")
			if wepkeytype == "ASCII":
				fp.write("\twep_key0=\"%s\"\n" % psk)
			else:
				fp.write("\twep_key0=%s\n" % psk)
		else:
			fp.write("\tkey_mgmt=NONE\n")
		fp.write("}\n")
		fp.close()


	def loadConfig(self, iface):
		configfile = getWlanConfigName(iface)
		if not os_path.exists(configfile):
			configfile = "/etc/wpa_supplicant.conf"
		try:
			#parse the wpasupplicant configfile
			print("[Wlan] parsing configfile: %s" % configfile)
			fp = open(configfile, "r")
			supplicant = fp.readlines()
			fp.close()
			essid = None
			encryption = "Unencrypted"

			for s in supplicant:
				split = s.strip().split("=", 1)
				if split[0] == "scan_ssid":
					if split[1] == "1":
						config.plugins.wlan.hiddenessid.value = True
					else:
						config.plugins.wlan.hiddenessid.value = False

				elif split[0] == "ssid":
					essid = split[1][1:-1]
					config.plugins.wlan.essid.value = essid

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
		except Exception as ex:
			print("[Wlan] Error parsing %s / %s" % (configfile, str(ex)))
			wsconfig = {
					"hiddenessid": False,
					"ssid": "",
					"encryption": "WPA2",
					"wepkeytype": "ASCII",
					"key": "",
				}
		return wsconfig


class Status:
	def __init__(self):
		self.wlaniface = {}
		self.backupwlaniface = {}
		self.statusCallback = None
		self.WlanConsole = Console()

	def stopWlanConsole(self):
		if self.WlanConsole is not None:
			print("[Wlan] killing self.WlanConsole")
			self.WlanConsole.killAll()
			self.WlanConsole = None

	def getDataForInterface(self, iface, callback=None):
		self.WlanConsole = Console()
		cmd = ["/sbin/iwconfig", "/sbin/iwconfig", iface]
		if callback is not None:
			self.statusCallback = callback
		self.WlanConsole.ePopen(cmd, self.iwconfigFinished, iface)

	def iwconfigFinished(self, result, retval, extra_args):
		iface = extra_args
		ssid = "off"
		data = {"essid": False, "frequency": False, "accesspoint": False, "bitrate": False, "encryption": False, "quality": False, "signal": False, "channel": False, "encryption_type": False, "frequency": False, "frequency_norm": False}
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
					enc = line[line.index('Encryption key') + 15:line.index('   Security')]
					if enc:
						enc = "on"
				else:
					enc = line[line.index('Encryption key') + 15:len(line)]
					if enc:
						enc = "on"
				if enc:
					data['encryption'] = enc
			if 'Quality' in line:
				if "/100" in line:
					qual = line[line.index('Quality') + 8:line.index('  Signal')]
				else:
					qual = line[line.index('Quality') + 8:line.index('Sig')]
				if qual:
					data['quality'] = qual
			if 'Signal level' in line:
				if "dBm" in line:
					signal = line[line.index('Signal level') + 13:line.index(' dBm')] + " dBm"
				elif "/100" in line:
					if "Noise" in line:
						signal = line[line.index('Signal level') + 13:line.index('  Noise')]
					else:
						signal = line[line.index('Signal level') + 13:len(line)]
				else:
					if "Noise" in line:
						signal = line[line.index('Signal level') + 13:line.index('  Noise')]
					else:
						signal = line[line.index('Signal level') + 13:len(line)]
				if signal:
					data['signal'] = signal

		if ssid != None and ssid != "off" and ssid != "":
			try:
				scanresults = list(Cell.all(iface, 5))
				print("[Wlan] Scan results = %s" % scanresults)
			except:
				scanresults = None
				print("[Wlan] No wireless networks could be found")
			aps = {}
			if scanresults:
				for i in range(len(scanresults)):
					bssid = scanresults[i].ssid
					aps[bssid] = {
						"active": True,
						"bssid": scanresults[i].ssid,
						"essid": scanresults[i].ssid,
						"channel": scanresults[i].channel,
						"encrypted": scanresults[i].encrypted,
						"encryption_type": scanresults[i].encryption_type if scanresults[i].encrypted else "none",
						"iface": iface,
						"maxrate": scanresults[i].bitrates,
						"mode": scanresults[i].mode,
						"quality": scanresults[i].quality,
						"signal": scanresults[i].signal,
						"frequency": scanresults[i].frequency,
						"frequency_norm": scanresults[i].frequency_norm,
						"address": scanresults[i].address,
						"noise": scanresults[i].noise,
						"pairwise_ciphers": scanresults[i].pairwise_ciphers,
						"authentication_suites": scanresults[i].authentication_suites,
					}
				#data["bitrate"] = aps[ssid]["maxrate"]
				data["encryption"] = aps[ssid]["encrypted"]
				data["quality"] = aps[ssid]["quality"]
				data["signal"] = aps[ssid]["signal"]
				data["channel"] = aps[ssid]["channel"]
				data["encryption_type"] = aps[ssid]["encryption_type"]
				#data["frequency"] = aps[ssid]["frequency"]
				data["frequency_norm"] = aps[ssid]["frequency_norm"]

		self.wlaniface[iface] = data
		self.backupwlaniface = self.wlaniface

		if self.WlanConsole is not None:
			if not self.WlanConsole.appContainers:
				print("[Wlan] self.wlaniface after loading:%s" % str(self.wlaniface))
				if self.statusCallback is not None:
						self.statusCallback(True, self.wlaniface)
						self.statusCallback = None

	def getAdapterAttribute(self, iface, attribute):
		self.iface = iface
		if self.iface in self.wlaniface:
			if attribute in self.wlaniface[self.iface]:
				return self.wlaniface[self.iface][attribute]
		return None


iStatus = Status()
