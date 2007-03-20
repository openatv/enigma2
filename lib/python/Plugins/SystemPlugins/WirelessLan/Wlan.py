from enigma import eListboxPythonMultiContent, eListbox, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER

from Components.MultiContent import MultiContentEntryText
from Components.GUIComponent import GUIComponent
from Components.HTMLComponent import HTMLComponent
from Components.config import config, ConfigYesNo, ConfigIP, NoSave, ConfigSubsection, ConfigMAC, ConfigEnableDisable, ConfigText, ConfigSelection

from pythonwifi import iwlibs

import os, string


list = []
list.append(_("WEP"))
list.append(_("WPA"))
list.append(_("WPA2"))

config.plugins.wlan = ConfigSubsection()
config.plugins.wlan.essid = NoSave(ConfigText(default = "home", fixed_size = False))

config.plugins.wlan.encryption = ConfigSubsection()
config.plugins.wlan.encryption.enabled = NoSave(ConfigYesNo(default = False))
config.plugins.wlan.encryption.type = NoSave(ConfigSelection(list, default = _("WPA")))
config.plugins.wlan.encryption.psk = NoSave(ConfigText(default = "mysecurewlan", fixed_size = False))

class Wlan:
	def __init__(self):
		a = ''; b = ''
		
		for i in range(0, 255):
		    a = a + chr(i)
		    if i < 32 or i > 127:
			b = b + ' '
		    else:
			b = b + chr(i)
		
		self.asciitrans = string.maketrans(a, b)

	def asciify(self, str):
		return str.translate(self.asciitrans)
	
	def getWirelessInterfaces(self):
		iwifaces = None
		try:
			iwifaces = iwlibs.getNICnames()
		except:
			iwifaces = None
			"[Wlan.py] No Wireless Networkcards could be found"
		
		return iwifaces
	
	def getNetworkList(self, iface):

		ifobj = iwlibs.Wireless(iface) # a Wireless NIC Object
		
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
					extra.append( string.strip(self.asciify(element)) )
		
				aps[bssid] = {
					'active' : True,
					'bssid': result.bssid,
					'channel': result.frequency.getChannel(result.frequency.getFrequency(), result.range),
					'encrypted': encryption,
					'essid': string.strip(self.asciify(result.essid)),
					'iface': iface,
					'maxrate' : result.rate[-1],
					'noise' : result.quality.getNoiselevel(),
					'quality' : result.quality.quality,
					'signal' : result.quality.getSignallevel(),
					'custom' : extra,
				}
				
			return aps
				

class WlanList(HTMLComponent, GUIComponent):
	
	def __init__(self, session, iface = 'wlan0'):
		
		GUIComponent.__init__(self)
		self.w = Wlan()
		self.iface = iface
		
		self.l = None
		self.l = eListboxPythonMultiContent()
		
		self.l.setFont(0, gFont("Regular", 32))
		self.l.setFont(1, gFont("Regular", 18))
		self.l.setFont(2, gFont("Regular", 16))
		self.l.setBuildFunc(self.buildWlanListEntry)		
				
		self.reload()
	
	def buildWlanListEntry(self, essid, bssid, encrypted, iface, maxrate):                                                                                                 
		
		res = [ (essid, encrypted, iface) ]
		e = encrypted and _("Yes") or _("No")
		res.append( MultiContentEntryText(pos=(0, 0), size=(570, 35), font=0, flags=RT_HALIGN_LEFT, text=essid) )
		res.append( MultiContentEntryText(pos=(0, 40), size=(180, 20), font=1, flags=RT_HALIGN_LEFT, text=_("Max. Bitrate: ")+maxrate) )
		res.append( MultiContentEntryText(pos=(190, 40), size=(180, 20), font=1, flags=RT_HALIGN_CENTER, text=_("Encrypted: ")+e) )
		res.append( MultiContentEntryText(pos=(380, 40), size=(190, 20), font=1, flags=RT_HALIGN_RIGHT, text=_("Interface: ")+iface) )
		return res
			
	def reload(self):
		aps = self.w.getNetworkList(self.iface)
		list = []
		if aps is not None:
			print "[Wlan.py] got Accespoints!"
			for ap in aps:
				a = aps[ap]
				if a['active']:
					list.append((a['essid'], a['bssid'], a['encrypted'], a['iface'], a['maxrate']))
		
		self.l.setList([])
		self.l.setList(list)
		 	
	GUI_WIDGET = eListbox

	def getCurrent(self):
		return self.l.getCurrentSelection()
	
	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.setItemHeight(60)


class wpaSupplicant:
	def __init__(self):
		pass
		
	def writeConfig(self):	
			
			essid = config.plugins.wlan.essid.value
			encrypted = config.plugins.wlan.encryption.enabled.value
			encryption = config.plugins.wlan.encryption.type.value
			psk = config.plugins.wlan.encryption.psk.value

		
			fp = file('/etc/wpa_supplicant.conf', 'w')
			fp.write('#WPA Supplicant Configuration by enigma2\n\n')
			fp.write('ctrl_interface=/var/run/wpa_supplicant\n')
			fp.write('ctrl_interface_group=0\n')
			fp.write('network={\n')
			fp.write('\tssid="'+essid+'"\n')
			fp.write('\tscan_ssid=1\n')
			
			if encrypted:
							
				if encryption == 'WPA' or encryption == 'WPA2':
					fp.write('\tkey_mgmt=WPA-PSK\n')
					
					if encryption == 'WPA':
						fp.write('\tproto=WPA\n')
						fp.write('\tpairwise=TKIP\n')
					else:
						fp.write('\tproto=WPA RSN\n')
						fp.write('\tpairwise=CCMP TKIP\n')
					
					fp.write('\tpsk="'+psk+'"\n')
				
				elif encryption == 'WEP':
					fp.write('\tkey_mgmt=NONE\n')
					fp.write('\twep_key0="'+psk+'"\n')
			
			fp.write('}')	
			fp.close()
					
			
	def loadConfig(self):

		try:
			#parse the wpasupplicant configfile
			fp = file('/etc/wpa_supplicant.conf', 'r')
			supplicant = fp.readlines()
			fp.close()
			
			for s in supplicant:
			
				split = s.strip().split('=')
				if split[0] == 'ssid':
					print "[Wlan.py] Got SSID "+split[1][1:-1]
					config.plugins.wlan.essid.value = split[1][1:-1]
					
				elif split[0] == 'proto':
					config.plugins.wlan.encryption.enabled.value = True
					if split[1] == "WPA RSN" : split[1] = 'WPA2'
					config.plugins.wlan.encryption.type.value = split[1]
					print "[Wlan.py] Got Encryption "+split[1]
				
				elif split[0] == 'psk':
					config.plugins.wlan.encryption.psk.value = split[1][1:-1]
					print "[Wlan.py] Got PSK "+split[1][1:-1]
				else:
					pass
				
		except:
			print "[Wlan.py] Error parsing /etc/wpa_supplicant.conf"
	
	def restart(self, iface):
		import os
		os.system("start-stop-daemon -K -x /usr/sbin/wpa_supplicant")
		os.system("start-stop-daemon -S -x /usr/sbin/wpa_supplicant -- -B -i"+iface+" -c/etc/wpa_supplicant.conf")
