from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Sources.StaticText import StaticText
from Components.Harddisk import harddiskmanager
from Components.NimManager import nimmanager
from Components.About import about
from Components.config import config
from Components.ScrollLabel import ScrollLabel
from Components.Console import Console
from enigma import eTimer

from Plugins.SystemPlugins.WirelessLan.Wlan import iWlan, iStatus, getWlanConfigName
from Components.Pixmap import MultiPixmap
from Components.Network import iNetwork

from Tools.StbHardware import getFPVersion 
from os import path, popen

import socket
import fcntl
import struct

def getHwAddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
    return ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1]
    
def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])
    
class About(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		AboutText = _("Hardware: ") + about.getHardwareTypeString() + "\n"
		AboutText += _("Drivers: ") + about.getDriversVersionString() + "\n"
		AboutText += _("Image: ") + about.getImageTypeString() + "\n"
		AboutText += _("Kernel Version: ") + about.getKernelVersionString() + "\n"
		
		EnigmaVersion = "GUI: " + about.getEnigmaVersionString()
		self["EnigmaVersion"] = StaticText(EnigmaVersion)
		AboutText += EnigmaVersion + "\n"

		
		ImageVersion = _("Last Upgrade: ") + about.getImageVersionString()
		self["ImageVersion"] = StaticText(ImageVersion)
		AboutText += ImageVersion + "\n"

		fp_version = getFPVersion()
		if fp_version is None:
			fp_version = ""
		else:
			fp_version = _("Frontprocessor version: %d") % fp_version
			AboutText += fp_version + "\n"

		self["FPVersion"] = StaticText(fp_version)
		
		#try:
		#  AboutText += "\n" + _("MAC Address: ") + getHwAddr('eth0') + "\n"
		#  AboutText += _("IP Address: ") + get_ip_address('eth0') + "\n"
		#except:
		#  AboutText += "\n" + _("MAC Address: N/A") + "\n"
		#  AboutText += _("IP Address: N/A") + "\n"		  
		
		self["TunerHeader"] = StaticText(_("Detected NIMs:"))
		#AboutText += "\n" + _("Detected NIMs:") + "\n"

		nims = nimmanager.nimList()
		for count in range(len(nims)):
			if count < 4:
				self["Tuner" + str(count)] = StaticText(nims[count])
			else:
				self["Tuner" + str(count)] = StaticText("")
			#AboutText += nims[count] + "\n"

		self["HDDHeader"] = StaticText(_("Detected HDD:"))
		#AboutText += "\n" + _("Detected HDD:") + "\n"

		hddlist = harddiskmanager.HDDList()
		hddinfo = ""
		if hddlist:
			for count in range(len(hddlist)):
				if hddinfo:
					hddinfo += "\n"
				hdd = hddlist[count][1]
				if int(hdd.free()) > 1024:
					hddinfo += "%s\n(%s, %d GB %s)" % (hdd.model(), hdd.capacity(), hdd.free()/1024, _("free"))
				else:
					hddinfo += "%s\n(%s, %d MB %s)" % (hdd.model(), hdd.capacity(), hdd.free(), _("free"))
		else:
			hddinfo = _("none")
		self["hddA"] = StaticText(hddinfo)
		#AboutText += hddinfo
		self["AboutScrollLabel"] = ScrollLabel(AboutText)

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"], 
			{
				"cancel": self.close,
				"ok": self.close,
				"green": self.showTranslationInfo,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown
			})

	def showTranslationInfo(self):
		self.session.open(TranslationInfo)


class Devices(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Device Information"))
		self.skinName = ["SystemDevicesInfo", "About"]
		
		self.AboutText = ""
		self["AboutScrollLabel"] = ScrollLabel(self.AboutText)
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.populate2)
		self.populate()

		

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "TimerEditActions"],
			{
				"cancel": self.close,
				"ok": self.close,
			})

	def populate(self):
		scanning = _("Wait please while scanning for devices...")
		self["AboutScrollLabel"].setText(scanning)
		self.activityTimer.start(10)

	def populate2(self):
		self.activityTimer.stop()
		self.Console = Console()
		
		self.AboutText = _("Hardware: ") + about.getHardwareTypeString() + "\n"
		self.AboutText += "\n" + _("Detected NIMs:") + "\n"

		nims = nimmanager.nimList()
		for count in range(len(nims)):
			if count < 4:
				self["Tuner" + str(count)] = StaticText(nims[count])
			else:
				self["Tuner" + str(count)] = StaticText("")
			self.AboutText += nims[count] + "\n"

		self.AboutText += "\n" + _("Detected HDD:") + "\n"

		hddlist = harddiskmanager.HDDList()
		hddinfo = ""
		if hddlist:
			for count in range(len(hddlist)):
				if hddinfo:
					hddinfo += "\n"
				hdd = hddlist[count][1]
				if int(hdd.free()) > 1024:
					hddinfo += "%s\n(%s, %d GB %s)" % (hdd.model(), hdd.capacity(), hdd.free()/1024, _("free"))
				else:
					hddinfo += "%s\n(%s, %d MB %s)" % (hdd.model(), hdd.capacity(), hdd.free(), _("free"))
		else:
			hddinfo = _("none")
		self.AboutText += hddinfo + "\n"
		self.AboutText += "\n" + _("Network Servers:") + "\n"
		self.mountinfo = ""
		self.Console.ePopen("df -mh | grep -v '^Filesystem'", self.Stage1Complete)
		self.AboutText +=self.mountinfo
		self["AboutScrollLabel"].setText(self.AboutText)

	def Stage1Complete(self,result, retval, extra_args = None):
		result = result.replace('\n                        ',' ').split('\n')
		self.mountinfo = ""
		for line in result:
			self.parts = line.split()
			if line and self.parts[0] and (self.parts[0].startswith('192') or self.parts[0].startswith('//192')):
				line = line.split()
				ipaddress = line[0]
				mounttotal = line[1]
				mountfree = line[3]
				if self.mountinfo:
					self.mountinfo += "\n"
					self.mountinfo += "%s (%sB, %sB %s)" % (ipaddress, mounttotal, mountfree, _("free"))
		if self.mountinfo:
			self.mountinfo += "\n"
		else:
			self["mounts"].setText(_('none'))
		self.AboutText += self.mountinfo + "\n"


class SystemMemoryInfo(Screen):
	skin = """
	<screen name="SystemMemoryInfo" position="center,center" size="560,400" >
		<widget name="AboutScrollLabel" position="30,225" size="458,325" font="Regular;20" transparent="0" zPosition="1" scrollbarMode="showOnDemand"/>
	</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Memory Information"))
		self.skinName = ["SystemMemoryInfo", "About"]
		self["AboutScrollLabel"] = ScrollLabel()

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "TimerEditActions"],
			{
				"cancel": self.close,
				"ok": self.close,
			})

		out_lines = file("/proc/meminfo").readlines()
		self.AboutText = _("RAM") + '\n\n'
		RamTotal = "-"
		RamFree = "-"
		for lidx in range(len(out_lines)-1):
			tstLine = out_lines[lidx].split()
			if "MemTotal:" in tstLine:
				MemTotal = out_lines[lidx].split()
				self.AboutText += _("Total Memory:") + "\t" + MemTotal[1] + "\n"
			if "MemFree:" in tstLine:
				MemFree = out_lines[lidx].split()
				self.AboutText += _("Free Memory:") + "\t" + MemFree[1] + "\n"
			if "Buffers:" in tstLine:
				Buffers = out_lines[lidx].split()
				self.AboutText += _("Buffers:") + "\t" + Buffers[1] + "\n"
			if "Cached:" in tstLine:
				Cached = out_lines[lidx].split()
				self.AboutText += _("Cached:") + "\t" + Cached[1] + "\n"
			if "SwapTotal:" in tstLine:
				SwapTotal = out_lines[lidx].split()
				self.AboutText += _("Total Swap:") + "\t" + SwapTotal[1] + "\n"
			if "SwapFree:" in tstLine:
				SwapFree = out_lines[lidx].split()
				self.AboutText += _("Free Swap:") + "\t" + SwapFree[1] + "\n\n"

		self.Console = Console()
		self.Console.ePopen("df -mh / | grep -v '^Filesystem'", self.Stage1Complete)

	def Stage1Complete(self,result, retval, extra_args = None):
		flash = str(result).replace('\n','')
		flash = flash.split()
		RamTotal=flash[1]
		RamFree=flash[3]

		self.AboutText += _("FLASH") + '\n\n'
		self.AboutText += _("Total:") + "\t" + RamTotal + "\n"
		self.AboutText += _("Free:") + "\t" + RamFree + "\n\n"

		self["AboutScrollLabel"].setText(self.AboutText)

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.close,
				"ok": self.close,
			})



class SystemNetworkInfo(Screen):
	skin = """
		<screen name="SystemNetworkInfo" position="center,center" size="560,400" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="AboutScrollLabel" position="10,50" size="458,75" valign="left" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelBSSID" render="Label" position="10,130" size="200,25" valign="left" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelESSID" render="Label" position="10,160" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelQuality" render="Label" position="10,190" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelSignal" render="Label" position="10,220" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelBitrate" render="Label" position="10,250" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="LabelEnc" render="Label" position="10,280" size="200,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="BSSID" render="Label" position="161,130" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="ESSID" render="Label" position="161,160" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="quality" render="Label" position="161,190" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="signal" render="Label" position="161,220" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="bitrate" render="Label" position="161,250" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<widget source="enc" render="Label" position="161,280" size="330,25" valign="center" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,350" zPosition="1" size="560,2" />
			<widget source="IFtext" render="Label" position="10,355" size="120,21" zPosition="10" font="Regular;20" halign="left" transparent="1" />
			<widget source="IF" render="Label" position="120,355" size="400,21" zPosition="10" font="Regular;20" halign="left" transparent="1" />
			<widget source="Statustext" render="Label" position="10,375" size="115,21" zPosition="10" font="Regular;20" halign="left" transparent="1"/>
			<widget name="statuspic" pixmaps="skin_default/buttons/button_green.png,skin_default/buttons/button_green_off.png" position="120,380" zPosition="10" size="15,16" transparent="1" alphatest="on"/>
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Network Information"))
		self.skinName = ["SystemNetworkInfo", "WlanStatus"]
		self["LabelBSSID"] = StaticText()
		self["LabelESSID"] = StaticText()
		self["LabelQuality"] = StaticText()
		self["LabelSignal"] = StaticText()
		self["LabelBitrate"] = StaticText()
		self["LabelEnc"] = StaticText()
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

		self.iface = None
		self.createscreen()

		self.resetList()
		self.updateStatusbar()

		self["key_red"] = StaticText(_("Close"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown
			})
# 		self.timer = eTimer()
# 		self.timer.timeout.get().append(self.resetList)
# 		self.onShown.append(lambda: self.timer.start(500))
		self.onClose.append(self.cleanup)

	def createscreen(self):
		AboutText = ""
		self.iface = "eth0"
		eth0 = about.getIfConfig('eth0')
		if eth0.has_key('addr'):
			AboutText += _("IP:") + "\t" + eth0['addr'] + "\n"
			if eth0.has_key('netmask'):
				AboutText += _("Netmask:") + "\t" + eth0['netmask'] + "\n"
			if eth0.has_key('hwaddr'):
				AboutText += _("MAC:") + "\t" + eth0['hwaddr'] + "\n"
			self.iface = 'eth0'

		wlan0 = about.getIfConfig('wlan0')
		if wlan0.has_key('addr'):
			AboutText += _("IP:") + "\t" + wlan0['addr'] + "\n"
			if wlan0.has_key('netmask'):
				AboutText += _("Netmask:") + "\t" + wlan0['netmask'] + "\n"
			if wlan0.has_key('hwaddr'):
				AboutText += _("MAC:") + "\t" + wlan0['hwaddr'] + "\n"
			self.iface = 'wlan0'

			self["LabelBSSID"].setText(_('Accesspoint:'))
			self["LabelESSID"].setText(_('SSID:'))
			self["LabelQuality"].setText(_('Link Quality:'))
			self["LabelSignal"].setText(_('Signal Strength:'))
			self["LabelBitrate"].setText(_('Bitrate:'))
			self["LabelEnc"].setText(_('Encryption:'))

		hostname = file('/proc/sys/kernel/hostname').read()
		AboutText += "\n" + _("Hostname:") + "\t" + hostname + "\n"

		self["AboutScrollLabel"] = ScrollLabel(AboutText)


	def cleanup(self):
		iStatus.stopWlanConsole()

	def resetList(self):
		iStatus.getDataForInterface(self.iface,self.getInfoCB)

	def getInfoCB(self,data,status):
		self.LinkState = None
		if data is not None:
			if data is True:
				if status is not None:
					if self.iface == 'wlan0':
						if status[self.iface]["essid"] == "off":
							essid = _("No Connection")
						else:
							essid = status[self.iface]["essid"]
						if status[self.iface]["accesspoint"] == "Not-Associated":
							accesspoint = _("Not-Associated")
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
								encryption = _("Unsupported")
						else:
							encryption = _("Enabled")
						if self.has_key("enc"):
							self["enc"].setText(encryption)

						if status[self.iface]["essid"] == "off" or status[self.iface]["accesspoint"] == "Not-Associated" or status[self.iface]["accesspoint"] == False:
							self.LinkState = False
							self["statuspic"].setPixmapNum(1)
							self["statuspic"].show()
						else:
							self.LinkState = True
							iNetwork.checkNetworkState(self.checkNetworkCB)

	def exit(self):
		self.timer.stop()
		self.close(True)

	def updateStatusbar(self):
		self["IFtext"].setText(_("Network:"))
		self["IF"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		self["Statustext"].setText(_("Link:"))
		if self.iface == 'wlan0':
			wait_txt = _("Please wait...")
			self["BSSID"].setText(wait_txt)
			self["ESSID"].setText(wait_txt)
			self["quality"].setText(wait_txt)
			self["signal"].setText(wait_txt)
			self["bitrate"].setText(wait_txt)
			self["enc"].setText(wait_txt)

		if iNetwork.isWirelessInterface(self.iface):
			try:
				from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
			except:
				self["statuspic"].setPixmapNum(1)
				self["statuspic"].show()
			else:
				iStatus.getDataForInterface(self.iface,self.getInfoCB)
		else:
			iNetwork.getLinkState(self.iface,self.dataAvail)

	def dataAvail(self,data):
		self.LinkState = None
		for line in data.splitlines():
			line = line.strip()
			if 'Link detected:' in line:
				if "yes" in line:
					self.LinkState = True
				else:
					self.LinkState = False
		if self.LinkState == True:
			iNetwork.checkNetworkState(self.checkNetworkCB)
		else:
			self["statuspic"].setPixmapNum(1)
			self["statuspic"].show()

	def checkNetworkCB(self,data):
		try:
			if iNetwork.getAdapterAttribute(self.iface, "up") is True:
				if self.LinkState is True:
					if data <= 2:
						self["statuspic"].setPixmapNum(0)
					else:
						self["statuspic"].setPixmapNum(1)
					self["statuspic"].show()
				else:
					self["statuspic"].setPixmapNum(1)
					self["statuspic"].show()
			else:
				self["statuspic"].setPixmapNum(1)
				self["statuspic"].show()
		except:
			self["statuspic"].setPixmapNum(0)

	def createSummary(self):
		return AboutSummary

class AboutSummary(Screen):
	skin = """
	<screen name="AboutSummary" position="0,0" size="132,64">
		<widget source="selected" render="Label" position="0,0" size="124,32" font="Regular;16" />
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
		self["selected"] = StaticText("ViX:")

		self["BoxType"] = StaticText(_("Hardware: cccccc"))
		self["KernelVersion"] = StaticText(_("Kernel:") + " " + about.getKernelVersionString())
		self["ImageType"] = StaticText(_("Image:") + " " + about.getImageTypeString())
		self["ImageVersion"] = StaticText(_("Version:") + " " + about.getImageVersionString())
		self["EnigmaVersion"] = StaticText(_("Last Update:"))
		
class TranslationInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		# don't remove the string out of the _(), or it can't be "translated" anymore.

		# TRANSLATORS: Add here whatever should be shown in the "translator" about screen, up to 6 lines (use \n for newline)
		info = _("TRANSLATOR_INFO")

		if info == "TRANSLATOR_INFO":
			info = "(N/A)"

		infolines = _("").split("\n")
		infomap = {}
		for x in infolines:
			l = x.split(': ')
			if len(l) != 2:
				continue
			(type, value) = l
			infomap[type] = value
		print infomap

		self["TranslationInfo"] = StaticText(info)

		translator_name = infomap.get("Language-Team", "none")
		if translator_name == "none":
			translator_name = infomap.get("Last-Translator", "")

		self["TranslatorName"] = StaticText(translator_name)

		self["actions"] = ActionMap(["SetupActions"],
			{
				"cancel": self.close,
				"ok": self.close,
			})
