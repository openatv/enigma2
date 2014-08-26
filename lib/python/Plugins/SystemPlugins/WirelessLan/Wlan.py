from os import system, path as os_path
from string import maketrans, strip

from Components.config import config, ConfigYesNo, NoSave, ConfigSubsection, ConfigText, ConfigSelection, ConfigPassword
from Components.Console import Console
from Components.Network import iNetwork
from pythonwifi.iwlibs import Wireless, Iwstats, getWNICnames
from pythonwifi import flags as wififlags


list = ["Unencrypted", "WEP", "WPA", "WPA/WPA2", "WPA2"]

weplist = ["ASCII", "HEX"]

config.plugins.wlan = ConfigSubsection()
config.plugins.wlan.essid = NoSave(ConfigText(default = "", fixed_size = False))
config.plugins.wlan.hiddenessid = NoSave(ConfigYesNo(default = False))
config.plugins.wlan.encryption = NoSave(ConfigSelection(list, default = "WPA2"))
config.plugins.wlan.wepkeytype = NoSave(ConfigSelection(weplist, default = "ASCII"))
config.plugins.wlan.psk = NoSave(ConfigPassword(default = "", fixed_size = False))


def getWlanConfigName(iface):
	return '/etc/wpa_supplicant.' + iface + '.conf'

class Wlan:
	def __init__(self, iface = None):
		self.iface = iface
		self.oldInterfaceState = None

		a = ''; b = ''
		for i in range(0, 255):
			a += chr(i)
			if i < 32 or i > 127:
				b += ' '
			else:
				b += chr(i)

		self.asciitrans = maketrans(a, b)

	def asciify(self, str):
		return str.translate(self.asciitrans)

	def getWirelessInterfaces(self):
		return getWNICnames()

	def setInterface(self, iface = None):
		self.iface = iface

	def getInterface(self):
		return self.iface

	def getNetworkList(self):
		if self.oldInterfaceState is None:
			self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")
		if self.oldInterfaceState is False:
			if iNetwork.getAdapterAttribute(self.iface, "up") is False:
				iNetwork.setAdapterAttribute(self.iface, "up", True)
				system("ifconfig "+self.iface+" up")

		ifobj = Wireless(self.iface) # a Wireless NIC Object

		try:
			scanresults = ifobj.scan()
		except:
			scanresults = None
			print "[Wlan.py] No wireless networks could be found"
		aps = {}
		if scanresults is not None:
			(num_channels, frequencies) = ifobj.getChannelInfo()
			index = 1
			for result in scanresults:
				bssid = result.bssid

				if result.encode.flags & wififlags.IW_ENCODE_DISABLED > 0:
					encryption = False
				elif result.encode.flags & wififlags.IW_ENCODE_NOKEY > 0:
					encryption = True
				else:
					encryption = None

				signal = str(result.quality.siglevel-0x100) + " dBm"
				quality = "%s/%s" % (result.quality.quality,ifobj.getQualityMax().quality)

				extra = []
				for element in result.custom:
					element = element.encode()
					extra.append( strip(self.asciify(element)) )
				for element in extra:
					if 'SignalStrength' in element:
						signal = element[element.index('SignalStrength')+15:element.index(',L')]
					if 'LinkQuality' in element:
						quality = element[element.index('LinkQuality')+12:len(element)]

				# noinspection PyProtectedMember
				aps[bssid] = {
					'active' : True,
					'bssid': result.bssid,
					'channel': frequencies.index(ifobj._formatFrequency(result.frequency.getFrequency())) + 1,
					'encrypted': encryption,
					'essid': strip(self.asciify(result.essid)),
					'iface': self.iface,
					'maxrate' : ifobj._formatBitrate(result.rate[-1][-1]),
					'noise' : '',#result.quality.nlevel-0x100,
					'quality' : str(quality),
					'signal' : str(signal),
					'custom' : extra,
				}

				index += 1
		return aps

	def stopGetNetworkList(self):
		if self.oldInterfaceState is not None:
			if self.oldInterfaceState is False:
				iNetwork.setAdapterAttribute(self.iface, "up", False)
				system("ifconfig "+self.iface+" down")
				self.oldInterfaceState = None
				self.iface = None

iWlan = Wlan()

class wpaSupplicant:
	def __init__(self):
		pass

	def writeConfig(self, iface):
		essid = config.plugins.wlan.essid.value
		hiddenessid = config.plugins.wlan.hiddenessid.value
		encryption = config.plugins.wlan.encryption.value
		wepkeytype = config.plugins.wlan.wepkeytype.value
		psk = config.plugins.wlan.psk.value
		fp = file(getWlanConfigName(iface), 'w')
		fp.write('#WPA Supplicant Configuration by enigma2\n')
		fp.write('ctrl_interface=/var/run/wpa_supplicant\n')
		fp.write('eapol_version=1\n')
		fp.write('fast_reauth=1\n')
		fp.write('ap_scan=1\n')
		fp.write('network={\n')
		fp.write('\tssid="'+essid+'"\n')
		if hiddenessid:
			fp.write('\tscan_ssid=1\n')
		else:
			fp.write('\tscan_ssid=0\n')
		if encryption in ('WPA', 'WPA2', 'WPA/WPA2'):
			fp.write('\tkey_mgmt=WPA-PSK\n')
			if encryption == 'WPA':
				fp.write('\tproto=WPA\n')
				fp.write('\tpairwise=TKIP\n')
				fp.write('\tgroup=TKIP\n')
			elif encryption == 'WPA2':
				fp.write('\tproto=RSN\n')
				fp.write('\tpairwise=CCMP\n')
				fp.write('\tgroup=CCMP\n')
			else:
				fp.write('\tproto=WPA RSN\n')
				fp.write('\tpairwise=CCMP TKIP\n')
				fp.write('\tgroup=CCMP TKIP\n')
			fp.write('\tpsk="'+psk+'"\n')
		elif encryption == 'WEP':
			fp.write('\tkey_mgmt=NONE\n')
			if wepkeytype == 'ASCII':
				fp.write('\twep_key0="'+psk+'"\n')
			else:
				fp.write('\twep_key0='+psk+'\n')
		else:
			fp.write('\tkey_mgmt=NONE\n')
		fp.write('}')
		fp.write('\n')
		fp.close()
		#system('cat ' + getWlanConfigName(iface))

	def loadConfig(self,iface):
		configfile = getWlanConfigName(iface)
		if not os_path.exists(configfile):
			configfile = '/etc/wpa_supplicant.conf'
		try:
			#parse the wpasupplicant configfile
			print "[Wlan.py] parsing configfile: ",configfile
			fp = file(configfile, 'r')
			supplicant = fp.readlines()
			fp.close()
			essid = None
			encryption = "Unencrypted"

			for s in supplicant:
				split = s.strip().split('=',1)
				if split[0] == 'scan_ssid':
					if split[1] == '1':
						config.plugins.wlan.hiddenessid.value = True
					else:
						config.plugins.wlan.hiddenessid.value = False

				elif split[0] == 'ssid':
					essid = split[1][1:-1]
					config.plugins.wlan.essid.value = essid

				elif split[0] == 'proto':
					if split[1] == 'WPA' :
						mode = 'WPA'
					if split[1] == 'RSN':
						mode = 'WPA2'
					if split[1] in ('WPA RSN', 'WPA WPA2'):
						mode = 'WPA/WPA2'
					encryption = mode

				elif split[0] == 'wep_key0':
					encryption = 'WEP'
					if split[1].startswith('"') and split[1].endswith('"'):
						config.plugins.wlan.wepkeytype.value = 'ASCII'
						config.plugins.wlan.psk.value = split[1][1:-1]
					else:
						config.plugins.wlan.wepkeytype.value = 'HEX'
						config.plugins.wlan.psk.value = split[1]

				elif split[0] == 'psk':
					config.plugins.wlan.psk.value = split[1][1:-1]
				else:
					pass

			config.plugins.wlan.encryption.value = encryption

			wsconfig = {
					'hiddenessid': config.plugins.wlan.hiddenessid.value,
					'ssid': config.plugins.wlan.essid.value,
					'encryption': config.plugins.wlan.encryption.value,
					'wepkeytype': config.plugins.wlan.wepkeytype.value,
					'key': config.plugins.wlan.psk.value,
				}

			for (key, item) in wsconfig.items():
				if item is "None" or item is "":
					if key == 'hiddenessid':
						wsconfig['hiddenessid'] = False
					if key == 'ssid':
						wsconfig['ssid'] = ""
					if key == 'encryption':
						wsconfig['encryption'] = "WPA2"
					if key == 'wepkeytype':
						wsconfig['wepkeytype'] = "ASCII"
					if key == 'key':
						wsconfig['key'] = ""
		except:
			print "[Wlan.py] Error parsing ",configfile
			wsconfig = {
					'hiddenessid': False,
					'ssid': "",
					'encryption': "WPA2",
					'wepkeytype': "ASCII",
					'key': "",
				}
		#print "[Wlan.py] WS-CONFIG-->",wsconfig
		return wsconfig


class Status:
	def __init__(self):
		self.wlaniface = {}
		self.backupwlaniface = {}
		self.statusCallback = None
		self.WlanConsole = Console()

	def stopWlanConsole(self):
		if self.WlanConsole is not None:
			print "[iStatus] killing self.WlanConsole"
			self.WlanConsole.killAll()
			self.WlanConsole = None

	def collectDataForInterface(self, iface):
		w = Wireless(iface)
		wsconfig = { }

		simpleConfigs = (
			("essid",       w.getEssid,      "off"),
			("frequency",   w.getFrequency,  ""),
			("accesspoint", w.getAPaddr,     "Not-Associated"),
			("bitrate",     w.getBitrate,    "0"),
			("encryption",  w.getEncryption, "off"),
		)

		for name, func, default in simpleConfigs:
			try:
				wsconfig[name] = func()
			except:
				wsconfig[name] = default
		try:
			wsconfig["quality"] = str(Iwstats("wlan0").qual.quality) + "/" + str(w.getQualityMax().quality)
		except:
			wsconfig["quality"] = ""
		try:
			wsconfig["signal"] = str(w.getQualityAvg().siglevel-128) + " dBm"
		except:
			wsconfig["signal"] = ""

		return wsconfig

	def getDataForInterface(self, iface, callback = None):
		wsconfig = self.collectDataForInterface(iface)
		self.wlaniface[iface] = wsconfig
		self.backupwlaniface = self.wlaniface
		if callback is not None:
			callback(True, self.wlaniface)
		return self.wlaniface

	def getAdapterAttribute(self, iface, attribute):
		self.iface = iface
		if self.iface in self.wlaniface:
			if attribute in self.wlaniface[self.iface]:
				return self.wlaniface[self.iface][attribute]
		return None

iStatus = Status()
