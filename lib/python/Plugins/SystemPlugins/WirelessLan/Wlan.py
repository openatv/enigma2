from enigma import eListboxPythonMultiContent, eListbox, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER
from Components.MultiContent import MultiContentEntryText
from Components.GUIComponent import GUIComponent
from Components.HTMLComponent import HTMLComponent
from Components.config import config, ConfigYesNo, NoSave, ConfigSubsection, ConfigText, ConfigSelection, ConfigPassword
from Components.Console import Console

from os import system
from string import maketrans, strip
import sys
import types
from re import compile as re_compile, search as re_search
from iwlibs import getNICnames, Wireless, Iwfreq

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
		#print "result im iwconfigFinished",result
		
		for line in result.splitlines():
			#print "line",line
			line = line.strip()
			if "ESSID" in line:
				if "off/any" in line:
					ssid = _("No Connection")
				else:
					tmpssid=(line[line.index('ESSID')+7:len(line)-1])
					if tmpssid == '':
						ssid = _("Hidden networkname")
					elif tmpssid ==' ':
						ssid = _("Hidden networkname")
					else:
					    ssid = tmpssid
				#print "SSID->",ssid
				if ssid is not None:
					data['essid'] = ssid
			if 'Frequency' in line:
				frequency = line[line.index('Frequency')+10 :line.index(' GHz')]
				#print "Frequency",frequency   
				if frequency is not None:
					data['frequency'] = frequency
			if "Access Point" in line:
				ap=line[line.index('Access Point')+14:len(line)-1]
				#print "AP",ap
				if ap is not None:
					data['acesspoint'] = ap
			if "Bit Rate" in line:
				br = line[line.index('Bit Rate')+9 :line.index(' Mb/s')]
				#print "Bitrate",br
				if br is not None:
					data['bitrate'] = br
			if 'Encryption key' in line:
				if ":off" in line:
				    enc = _("Disabled")
				else:
				    enc = line[line.index('Encryption key')+15 :line.index('   Security')]
				#print "Encryption key",enc 
				if enc is not None:
					data['encryption'] = _("Enabled")
			if 'Quality' in line:
				if "/100" in line:
					qual = line[line.index('Quality')+8:line.index('/100')]
				else:
					qual = line[line.index('Quality')+8:line.index('Sig')]
				#print "Quality",qual
				if qual is not None:
					data['quality'] = qual
			if 'Signal level' in line:
				signal = line[line.index('Signal level')+14 :line.index(' dBm')]
				#print "Signal level",signal		
				if signal is not None:
					data['signal'] = signal

		self.wlaniface[self.iface] = data
		
		if len(self.WlanConsole.appContainers) == 0:
			print "self.wlaniface after loading:", self.wlaniface
			self.WlanConsole = None
			if callback is not None:
				callback(True,self.wlaniface)

	def getAdapterAttribute(self, attribute):
		print "im getAdapterAttribute"
		if self.wlaniface.has_key(self.iface):
			print "self.wlaniface.has_key",self.iface
			if self.wlaniface[self.iface].has_key(attribute):
				return self.wlaniface[self.iface][attribute]
		return None
		
	def asciify(self, str):
		return str.translate(self.asciitrans)

	
	def getWirelessInterfaces(self):
		iwifaces = None
		try:
			iwifaces = getNICnames()
		except:
			print "[Wlan.py] No Wireless Networkcards could be found"
		
		return iwifaces

	
	def getNetworkList(self):
		system("ifconfig "+self.iface+" up")
		ifobj = Wireless(self.iface) # a Wireless NIC Object
		
		#Association mappings
		stats, quality, discard, missed_beacon = ifobj.getStatistics()
		snr = quality.signallevel - quality.noiselevel

		try:
			scanresults = ifobj.scan()
		except:
			scanresults = None
			print "[Wlan.py] No Wireless Networks could be found"
		
		if scanresults is not None:
			aps = {}
			for result in scanresults:
			
				bssid = result.bssid
		
				encryption = map(lambda x: hex(ord(x)), result.encode)
		
				if encryption[-1] == "0x8":
					encryption = True
				else:
					encryption = False
		
				extra = []
				for element in result.custom:
					element = element.encode()
					extra.append( strip(self.asciify(element)) )
				
				if result.quality.sl is 0 and len(extra) > 0:
					begin = extra[0].find('SignalStrength=')+15
									
					done = False
					end = begin+1
					
					while not done:
						if extra[0][begin:end].isdigit():
							end += 1
						else:
							done = True
							end -= 1
					
					signal = extra[0][begin:end]
					#print "[Wlan.py] signal is:" + str(signal)

				else:
					signal = str(result.quality.sl)
				
				aps[bssid] = {
					'active' : True,
					'bssid': result.bssid,
					'channel': result.frequency.getChannel(result.frequency.getFrequency()),
					'encrypted': encryption,
					'essid': strip(self.asciify(result.essid)),
					'iface': self.iface,
					'maxrate' : result.rate[-1],
					'noise' : result.quality.getNoiselevel(),
					'quality' : str(result.quality.quality),
					'signal' : signal,
					'custom' : extra,
				}
				print aps[bssid]
			return aps

		
	def getStatus(self):
		ifobj = Wireless(self.iface)
		fq = Iwfreq()
		try:
			self.channel = str(fq.getChannel(str(ifobj.getFrequency()[0:-3])))
		except:
			self.channel = 0
		#print ifobj.getStatistics()
		status = {
				  'BSSID': str(ifobj.getAPaddr()),
				  'ESSID': str(ifobj.getEssid()),
				  'quality': str(ifobj.getStatistics()[1].quality),
				  'signal': str(ifobj.getStatistics()[1].sl),
				  'bitrate': str(ifobj.getBitrate()),
				  'channel': str(self.channel),
				  #'channel': str(fq.getChannel(str(ifobj.getFrequency()[0:-3]))),
		}
		
		for (key, item) in status.items():
			if item is "None" or item is "":
					status[key] = _("N/A")
				
		return status



class WlanList(HTMLComponent, GUIComponent):
	def __init__(self, session, iface):
		
		GUIComponent.__init__(self)
		self.w = Wlan(iface)
		self.iface = iface
		
		self.length = 0
		self.aplist = None
		self.list = None
		self.oldlist = None
		self.l = None
		self.l = eListboxPythonMultiContent()
		
		self.l.setFont(0, gFont("Regular", 32))
		self.l.setFont(1, gFont("Regular", 18))
		self.l.setFont(2, gFont("Regular", 16))
		self.l.setBuildFunc(self.buildWlanListEntry)		
				
		self.reload()
	
	def buildWlanListEntry(self, essid, bssid, encrypted, iface, maxrate, signal):                                                                                                 
		
		res = [ (essid, encrypted, iface) ]
		
		if essid == "":
			essid = bssid
		
		e = encrypted and _("Yes") or _("No")
		res.append( MultiContentEntryText(pos=(0, 0), size=(470, 35), font=0, flags=RT_HALIGN_LEFT, text=essid) )
		res.append( MultiContentEntryText(pos=(425, 0), size=(60, 20), font=1, flags=RT_HALIGN_LEFT, text=_("Signal: ")))
		res.append( MultiContentEntryText(pos=(480, 0), size=(70, 35), font=0, flags=RT_HALIGN_RIGHT, text="%s" %signal))
		res.append( MultiContentEntryText(pos=(0, 40), size=(180, 20), font=1, flags=RT_HALIGN_LEFT, text=_("Max. Bitrate: %s") %maxrate ))
		res.append( MultiContentEntryText(pos=(190, 40), size=(180, 20), font=1, flags=RT_HALIGN_CENTER, text=_("Encrypted: %s") %e ))
		res.append( MultiContentEntryText(pos=(345, 40), size=(190, 20), font=1, flags=RT_HALIGN_RIGHT, text=_("Interface: %s") %iface ))
		return res
		
			
	def reload(self):
		aps = self.w.getNetworkList()

		self.list = []
		self.aplist = []
		if aps is not None:
			print "[Wlan.py] got Accespoints!"
			for ap in aps:
				a = aps[ap]
				if a['active']:
					if a['essid'] != '':
					#	a['essid'] = a['bssid']
						self.list.append( (a['essid'], a['bssid'], a['encrypted'], a['iface'], a['maxrate'], a['signal']) )
					#self.aplist.append( a['essid'])
		if self.oldlist is not None:
			for entry in self.oldlist:
				if entry not in self.list:
					self.list.append(entry)
		
		if len(self.list):
			for entry in self.list:
				self.aplist.append( entry[0])
		self.length = len(self.list)
		self.oldlist = self.list
		self.l.setList([])
		self.l.setList(self.list)
		 	
	GUI_WIDGET = eListbox


	def getCurrent(self):
		return self.l.getCurrentSelection()
	
	
	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.setItemHeight(60)
	
	
	def getLength(self):
		return self.length
	
	def getList(self):
		return self.aplist


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
					print "split[1]",split[1]
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
					print "[Wlan.py] Got Encryption: WEP - keytype is: "+config.plugins.wlan.encryption.wepkeytype.value
					print "[Wlan.py] Got Encryption: WEP - key0 is: "+config.plugins.wlan.encryption.psk.value
					
				elif split[0] == 'psk':
					config.plugins.wlan.encryption.psk.value = split[1][1:-1]
					print "[Wlan.py] Got PSK: "+split[1][1:-1]
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
					tmpssid=(line[line.index('ESSID')+7:len(line)-1])
					if tmpssid == '':
						ssid = _("Hidden networkname")
					elif tmpssid ==' ':
						ssid = _("Hidden networkname")
					else:
					    ssid = tmpssid
				#print "SSID->",ssid
				if ssid is not None:
					data['essid'] = ssid
			if 'Frequency' in line:
				frequency = line[line.index('Frequency')+10 :line.index(' GHz')]
				#print "Frequency",frequency   
				if frequency is not None:
					data['frequency'] = frequency
			if "Access Point" in line:
				ap=line[line.index('Access Point')+14:len(line)]
				#print "AP",ap
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
				#print "Bitrate",br
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
				#print "Encryption key",enc 
				if enc is not None:
					data['encryption'] = enc
			if 'Quality' in line:
				if "/100" in line:
					qual = line[line.index('Quality')+8:line.index('/100')]
				else:
					qual = line[line.index('Quality')+8:line.index('Sig')]
				#print "Quality",qual
				if qual is not None:
					data['quality'] = qual
			if 'Signal level' in line:
				if "dBm" in line:
					signal = line[line.index('Signal level')+14 :line.index(' dBm')]
					signal += " dBm"
				elif "/100" in line:
					signal = line[line.index('Signal level')+13:line.index('/100  Noise')]
					signal += "%"
				else:
					signal = line[line.index('Signal level')+13:line.index('  Noise')]
					signal += "%"
				#print "Signal level",signal		
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
		print "im getAdapterAttribute"
		self.iface = iface
		if self.wlaniface.has_key(self.iface):
			print "self.wlaniface.has_key",self.iface
			if self.wlaniface[self.iface].has_key(attribute):
				return self.wlaniface[self.iface][attribute]
		return None
	
iStatus = Status()