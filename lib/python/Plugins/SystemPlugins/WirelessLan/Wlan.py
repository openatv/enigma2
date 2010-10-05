from Components.config import config, ConfigYesNo, NoSave, ConfigSubsection, ConfigText, ConfigSelection, ConfigPassword
from Components.Console import Console

from os import system
from string import maketrans, strip
import sys
import types
from re import compile as re_compile, search as re_search
from pythonwifi.iwlibs import getNICnames, Wireless, Iwfreq, getWNICnames
from pythonwifi import flags as wififlags

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
config.plugins.wlan.encryption.enabled = NoSave(ConfigYesNo(default = True))
config.plugins.wlan.encryption.type = NoSave(ConfigSelection(list, default = "WPA/WPA2"))
config.plugins.wlan.encryption.wepkeytype = NoSave(ConfigSelection(weplist, default = "ASCII"))
config.plugins.wlan.encryption.psk = NoSave(ConfigPassword(default = "mysecurewlan", fixed_size = False))

class Wlan:
	def __init__(self, iface):
		a = ''; b = ''
		for i in range(0, 255):
			a = a + chr(i)
			if i < 32 or i > 127:
				b = b + ' '
			else:
				b = b + chr(i)
		
		self.iface = iface
		self.wlaniface = {}
		self.WlanConsole = Console()
		self.asciitrans = maketrans(a, b)

	def stopWlanConsole(self):
		if self.WlanConsole is not None:
			print "killing self.WlanConsole"
			self.WlanConsole = None
			del self.WlanConsole
			
	def getDataForInterface(self, callback = None):
		#get ip out of ip addr, as avahi sometimes overrides it in ifconfig.
		print "self.iface im getDataForInterface",self.iface
		if len(self.WlanConsole.appContainers) == 0:
			self.WlanConsole = Console()
			cmd = "iwconfig " + self.iface
			self.WlanConsole.ePopen(cmd, self.iwconfigFinished, callback)

	def iwconfigFinished(self, result, retval, extra_args):
		print "self.iface im iwconfigFinished",self.iface
		callback = extra_args
		data = { 'essid': False, 'frequency': False, 'acesspoint': False, 'bitrate': False, 'encryption': False, 'quality': False, 'signal': False }
		
		for line in result.splitlines():
			line = line.strip()
			if "ESSID" in line:
				if "off/any" in line:
					ssid = _("No Connection")
				else:
					if "Nickname" in line:
						tmpssid=(line[line.index('ESSID')+7:line.index('"  Nickname')])
						if tmpssid == '':
							ssid = _("Hidden networkname")
						elif tmpssid ==' ':
							ssid = _("Hidden networkname")
						else:
							ssid = tmpssid
					else:
						tmpssid=(line[line.index('ESSID')+7:len(line)-1])
						if tmpssid == '':
							ssid = _("Hidden networkname")
						elif tmpssid ==' ':
							ssid = _("Hidden networkname")
						else:
							ssid = tmpssid						

				if ssid is not None:
					data['essid'] = ssid
			if 'Frequency' in line:
				frequency = line[line.index('Frequency')+10 :line.index(' GHz')]
				if frequency is not None:
					data['frequency'] = frequency
			if "Access Point" in line:
				ap=line[line.index('Access Point')+14:len(line)-1]
				if ap is not None:
					data['acesspoint'] = ap
			if "Bit Rate" in line:
				br = line[line.index('Bit Rate')+9 :line.index(' Mb/s')]
				if br is not None:
					data['bitrate'] = br
			if 'Encryption key' in line:
				if ":off" in line:
				    enc = _("Disabled")
				else:
				    enc = line[line.index('Encryption key')+15 :line.index('   Security')]
				if enc is not None:
					data['encryption'] = _("Enabled")
			if 'Quality' in line:
				if "/100" in line:
					qual = line[line.index('Quality')+8:line.index('/100')]
				else:
					qual = line[line.index('Quality')+8:line.index('Sig')]
				if qual is not None:
					data['quality'] = qual
			if 'Signal level' in line:
				signal = line[line.index('Signal level')+13 :line.index(' dBm')]
				if signal is not None:
					data['signal'] = signal

		self.wlaniface[self.iface] = data
		
		if len(self.WlanConsole.appContainers) == 0:
			print "self.wlaniface after loading:", self.wlaniface
			self.WlanConsole = None
			if callback is not None:
				callback(True,self.wlaniface)

	def getAdapterAttribute(self, attribute):
		if self.wlaniface.has_key(self.iface):
			print "self.wlaniface.has_key",self.iface
			if self.wlaniface[self.iface].has_key(attribute):
				return self.wlaniface[self.iface][attribute]
		return None
		
	def asciify(self, str):
		return str.translate(self.asciitrans)

	
	def getWirelessInterfaces(self):
		device = re_compile('[a-z]{2,}[0-9]*:')
		ifnames = []

		fp = open('/proc/net/wireless', 'r')
		for line in fp:
			try:
				# append matching pattern, without the trailing colon
				ifnames.append(device.search(line).group()[:-1])
			except AttributeError:
				pass
		return ifnames

	
	def getNetworkList(self):
		system("ifconfig "+self.iface+" up")
		ifobj = Wireless(self.iface) # a Wireless NIC Object
		
		#Association mappings
		#stats, quality, discard, missed_beacon = ifobj.getStatistics()
		#snr = quality.signallevel - quality.noiselevel

		try:
			scanresults = ifobj.scan()
		except:
			scanresults = None
			print "[Wlan.py] No Wireless Networks could be found"
		
		if scanresults is not None:
			aps = {}
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
					print element
					if 'SignalStrength' in element:
						signal = element[element.index('SignalStrength')+15:element.index(',L')]					
					if 'LinkQuality' in element:
						quality = element[element.index('LinkQuality')+12:len(element)]				

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
				#print "GOT APS ENTRY:",aps[bssid]
				index = index + 1
			return aps

		
	def getStatus(self):
		ifobj = Wireless(self.iface)
		fq = Iwfreq()
		try:
			self.channel = str(fq.getChannel(str(ifobj.getFrequency()[0:-3])))
		except:
			self.channel = 0
		status = {
				  'BSSID': str(ifobj.getAPaddr()), #ifobj.getStatistics()
				  'ESSID': str(ifobj.getEssid()),
				  'quality': "%s/%s" % (ifobj.getStatistics()[1].quality,ifobj.getQualityMax().quality),
				  'signal': str(ifobj.getStatistics()[1].siglevel-0x100) + " dBm",
				  'bitrate': str(ifobj.getBitrate()),
				  'channel': str(self.channel),
				  #'channel': str(fq.getChannel(str(ifobj.getFrequency()[0:-3]))),
		}
		
		for (key, item) in status.items():
			if item is "None" or item is "":
					status[key] = _("N/A")
				
		return status


class wpaSupplicant:
	def __init__(self):
		pass
	
		
	def writeConfig(self):	
			
			essid = config.plugins.wlan.essid.value
			hiddenessid = config.plugins.wlan.hiddenessid.value
			encrypted = config.plugins.wlan.encryption.enabled.value
			encryption = config.plugins.wlan.encryption.type.value
			wepkeytype = config.plugins.wlan.encryption.wepkeytype.value
			psk = config.plugins.wlan.encryption.psk.value
			fp = file('/etc/wpa_supplicant.conf', 'w')
			fp.write('#WPA Supplicant Configuration by enigma2\n')
			fp.write('ctrl_interface=/var/run/wpa_supplicant\n')
			fp.write('eapol_version=1\n')
			fp.write('fast_reauth=1\n')	
			if essid == 'hidden...':
				fp.write('ap_scan=2\n')
			else:
				fp.write('ap_scan=1\n')
			fp.write('network={\n')
			if essid == 'hidden...':
				fp.write('\tssid="'+hiddenessid+'"\n')
			else:
				fp.write('\tssid="'+essid+'"\n')
			fp.write('\tscan_ssid=0\n')			
			if encrypted:
				if encryption == 'WPA' or encryption == 'WPA2' or encryption == 'WPA/WPA2' :
					fp.write('\tkey_mgmt=WPA-PSK\n')
					
					if encryption == 'WPA':
						fp.write('\tproto=WPA\n')
						fp.write('\tpairwise=TKIP\n')
						fp.write('\tgroup=TKIP\n')
					elif encryption == 'WPA2':
						fp.write('\tproto=WPA RSN\n')
						fp.write('\tpairwise=CCMP TKIP\n')
						fp.write('\tgroup=CCMP TKIP\n')						
					else:
						fp.write('\tproto=WPA WPA2\n')
						fp.write('\tpairwise=CCMP\n')
						fp.write('\tgroup=TKIP\n')					
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
			system("cat /etc/wpa_supplicant.conf")
		
	def loadConfig(self):
		try:
			#parse the wpasupplicant configfile
			fp = file('/etc/wpa_supplicant.conf', 'r')
			supplicant = fp.readlines()
			fp.close()
			ap_scan = False
			essid = None

			for s in supplicant:
				split = s.strip().split('=',1)
				if split[0] == 'ap_scan':
					print "[Wlan.py] Got Hidden SSID Scan  Value "+split[1]
					if split[1] == '2':
						ap_scan = True
					else:
						ap_scan = False
						
				elif split[0] == 'ssid':
					print "[Wlan.py] Got SSID "+split[1][1:-1]
					essid = split[1][1:-1]
					
				elif split[0] == 'proto':
					config.plugins.wlan.encryption.enabled.value = True
					if split[1] == "WPA" :
						mode = 'WPA'
					if split[1] == "WPA WPA2" :
						mode = 'WPA/WPA2'
					if split[1] == "WPA RSN" :
						mode = 'WPA2'
					config.plugins.wlan.encryption.type.value = mode
					print "[Wlan.py] Got Encryption: "+mode
					
				#currently unused !
				#elif split[0] == 'key_mgmt':
				#	print "split[1]",split[1]
				#	if split[1] == "WPA-PSK" :
				#		config.plugins.wlan.encryption.enabled.value = True
				#		config.plugins.wlan.encryption.type.value = "WPA/WPA2"
				#	print "[Wlan.py] Got Encryption: "+ config.plugins.wlan.encryption.type.value
					
				elif split[0] == 'wep_key0':
					config.plugins.wlan.encryption.enabled.value = True
					config.plugins.wlan.encryption.type.value = 'WEP'
					if split[1].startswith('"') and split[1].endswith('"'):
						config.plugins.wlan.encryption.wepkeytype.value = 'ASCII'
						config.plugins.wlan.encryption.psk.value = split[1][1:-1]
					else:
						config.plugins.wlan.encryption.wepkeytype.value = 'HEX'
						config.plugins.wlan.encryption.psk.value = split[1]						
					
				elif split[0] == 'psk':
					config.plugins.wlan.encryption.psk.value = split[1][1:-1]
				else:
					pass
				
			if ap_scan is True:
				config.plugins.wlan.hiddenessid.value = essid
				config.plugins.wlan.essid.value = 'hidden...'
			else:
				config.plugins.wlan.hiddenessid.value = essid
				config.plugins.wlan.essid.value = essid
			wsconfig = {
					'hiddenessid': config.plugins.wlan.hiddenessid.value,
					'ssid': config.plugins.wlan.essid.value,
					'encryption': config.plugins.wlan.encryption.enabled.value,
					'encryption_type': config.plugins.wlan.encryption.type.value,
					'encryption_wepkeytype': config.plugins.wlan.encryption.wepkeytype.value,
					'key': config.plugins.wlan.encryption.psk.value,
				}
		
			for (key, item) in wsconfig.items():
				if item is "None" or item is "":
					if key == 'hiddenessid':
						wsconfig['hiddenessid'] = "home"
					if key == 'ssid':
						wsconfig['ssid'] = "home"
					if key == 'encryption':
						wsconfig['encryption'] = True				
					if key == 'encryption':
						wsconfig['encryption_type'] = "WPA/WPA2"
					if key == 'encryption':
						wsconfig['encryption_wepkeytype'] = "ASCII"
					if key == 'encryption':
						wsconfig['key'] = "mysecurewlan"

		except:
			print "[Wlan.py] Error parsing /etc/wpa_supplicant.conf"
			wsconfig = {
					'hiddenessid': "home",
					'ssid': "home",
					'encryption': True,
					'encryption_type': "WPA/WPA2",
					'encryption_wepkeytype': "ASCII",
					'key': "mysecurewlan",
				}
		print "[Wlan.py] WS-CONFIG-->",wsconfig
		return wsconfig

	
	def restart(self, iface):
		system("start-stop-daemon -K -x /usr/sbin/wpa_supplicant")
		system("start-stop-daemon -S -x /usr/sbin/wpa_supplicant -- -B -i"+iface+" -c/etc/wpa_supplicant.conf")

class Status:
	def __init__(self):
		self.wlaniface = {}
		self.backupwlaniface = {}
		self.WlanConsole = Console()

	def stopWlanConsole(self):
		if self.WlanConsole is not None:
			print "killing self.WlanConsole"
			self.WlanConsole = None
			
	def getDataForInterface(self, iface, callback = None):
		self.WlanConsole = Console()
		cmd = "iwconfig " + iface
		self.WlanConsole.ePopen(cmd, self.iwconfigFinished, [iface, callback])

	def iwconfigFinished(self, result, retval, extra_args):
		(iface, callback) = extra_args
		data = { 'essid': False, 'frequency': False, 'acesspoint': False, 'bitrate': False, 'encryption': False, 'quality': False, 'signal': False }
		for line in result.splitlines():
			line = line.strip()
			if "ESSID" in line:
				if "off/any" in line:
					ssid = _("No Connection")
				else:
					if "Nickname" in line:
						tmpssid=(line[line.index('ESSID')+7:line.index('"  Nickname')])
						if tmpssid == '':
							ssid = _("Hidden networkname")
						elif tmpssid ==' ':
							ssid = _("Hidden networkname")
						else:
							ssid = tmpssid
					else:
						tmpssid=(line[line.index('ESSID')+7:len(line)-1])
						if tmpssid == '':
							ssid = _("Hidden networkname")
						elif tmpssid ==' ':
							ssid = _("Hidden networkname")
						else:
							ssid = tmpssid						
				if ssid is not None:
					data['essid'] = ssid
			if 'Frequency' in line:
				frequency = line[line.index('Frequency')+10 :line.index(' GHz')]
				if frequency is not None:
					data['frequency'] = frequency
			if "Access Point" in line:
				ap=line[line.index('Access Point')+14:len(line)]
				if ap is not None:
					data['acesspoint'] = ap
					if ap == "Not-Associated":
						data['essid'] = _("No Connection")
			if "Bit Rate" in line:
				if "kb" in line:
					br = line[line.index('Bit Rate')+9 :line.index(' kb/s')]
					if br == '0':
						br = _("Unsupported")
					else:
						br += " Mb/s"
				else:
					br = line[line.index('Bit Rate')+9 :line.index(' Mb/s')] + " Mb/s"
				if br is not None:
					data['bitrate'] = br
			if 'Encryption key' in line:
				if ":off" in line:
					if data['acesspoint'] is not "Not-Associated":
						enc = _("Unsupported")
					else:
						enc = _("Disabled")
				else:
					enc = line[line.index('Encryption key')+15 :line.index('   Security')]
					if enc is not None:
						enc = _("Enabled")
				if enc is not None:
					data['encryption'] = enc
			if 'Quality' in line:
				if "/100" in line:
					#qual = line[line.index('Quality')+8:line.index('/100')]
					qual = line[line.index('Quality')+8:line.index('  Signal')]
				else:
					qual = line[line.index('Quality')+8:line.index('Sig')]
				if qual is not None:
					data['quality'] = qual
			if 'Signal level' in line:
				if "dBm" in line:
					signal = line[line.index('Signal level')+13 :line.index(' dBm')]
					signal += " dBm"
				elif "/100" in line:
					if "Noise" in line:
						signal = line[line.index('Signal level')+13:line.index('  Noise')]
					else:
						signal = line[line.index('Signal level')+13:len(line)]
				else:
					if "Noise" in line:
						signal = line[line.index('Signal level')+13:line.index('  Noise')]
					else:
						signal = line[line.index('Signal level')+13:len(line)]						
				if signal is not None:
					data['signal'] = signal

		self.wlaniface[iface] = data
		self.backupwlaniface = self.wlaniface
		
		if self.WlanConsole is not None:
			if len(self.WlanConsole.appContainers) == 0:
				print "self.wlaniface after loading:", self.wlaniface
				if callback is not None:
					callback(True,self.wlaniface)

	def getAdapterAttribute(self, iface, attribute):
		self.iface = iface
		if self.wlaniface.has_key(self.iface):
			if self.wlaniface[self.iface].has_key(attribute):
				return self.wlaniface[self.iface][attribute]
		return None
	
iStatus = Status()
