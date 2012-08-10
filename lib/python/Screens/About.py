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
from Screens.SoftwareUpdate import SoftwareUpdateChanges
from enigma import eTimer

from Plugins.SystemPlugins.WirelessLan.Wlan import iWlan, iStatus, getWlanConfigName
from Components.Pixmap import MultiPixmap
from Components.Network import iNetwork

from Tools.DreamboxHardware import getFPVersion
from os import path, popen

class About(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Image Information"))
		self.populate()

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "TimerEditActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				'log': self.showAboutReleaseNotes,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown
			})

	def populate(self):
		self["lab1"] = StaticText(_("Virtuosso Image Xtreme"))
		self["lab2"] = StaticText(_("By Team ViX"))
		if config.misc.boxtype.value == 'vuuno':
			self["lab3"] = StaticText(_("Support at") + " www.vuplus-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Uno")
			AboutText = _("Hardware:") + " Vu+ Uno\n"
		elif config.misc.boxtype.value == 'vuultimo':
			self["lab3"] = StaticText(_("Support at") + " www.vuplus-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Ultimo")
			AboutText = _("Hardware:") + " Vu+ Ultimo\n"
		elif config.misc.boxtype.value == 'vusolo':
			self["lab3"] = StaticText(_("Support at") + " www.vuplus-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Solo")
			AboutText = _("Hardware:") + " Vu+ Solo\n"
		elif config.misc.boxtype.value == 'vuduo':
			self["lab3"] = StaticText(_("Support at") + " www.vuplus-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Duo")
			AboutText = _("Hardware:") + " Vu+ Duo\n"
		elif config.misc.boxtype.value == 'et5x00':
			self["lab3"] = StaticText(_("Support at") + " www.xtrend-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Xtrend ET5x00 Series")
			AboutText = _("Hardware:") + "  Xtrend ET5x00 Series\n"
		elif config.misc.boxtype.value == 'et6x00':
			self["lab3"] = StaticText(_("Support at") + " www.xtrend-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Xtrend ET6x00 Series")
			AboutText = _("Hardware:") + "  Xtrend ET6x00 Series\n"
		elif config.misc.boxtype.value == 'et9x00':
			self["lab3"] = StaticText(_("Support at") + " www.xtrend-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Xtrend ET9x00 Series")
			AboutText = _("Hardware:") + " Xtrend ET9x00 Series\n"
		elif config.misc.boxtype.value == 'odin':
			self["lab3"] = StaticText(_("Support at") + " www.odin-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Odin")
			AboutText = _("Hardware:") + " Odin\n"
		else:
			self["lab3"] = StaticText(_("Support at") + " www.world-of-satellite.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " " + config.misc.boxtype.value)
			AboutText = _("Hardware:") + " " + config.misc.boxtype.value + "\n"

		self["KernelVersion"] = StaticText(_("Kernel:") + " " + about.getKernelVersionString())
		AboutText += _("Kernel:") + " " + about.getKernelVersionString() + "\n"
		self["DriversVersion"] = StaticText(_("Drivers:") + " " + about.getDriversString())
		AboutText += _("Drivers:") + " " + about.getDriversString() + "\n"
		self["ImageType"] = StaticText(_("Image:") + " " + about.getImageTypeString())
		AboutText += _("Image:") + " " + about.getImageTypeString() + "\n"
		self["ImageVersion"] = StaticText(_("Version:") + " " + about.getImageVersionString())
		AboutText += _("Version:") + " " + about.getImageVersionString() + "\n"
		self["BuildVersion"] = StaticText(_("Build:") + " " + about.getBuildVersionString())
		AboutText += _("Build:") + " " + about.getBuildVersionString() + "\n"
		self["EnigmaVersion"] = StaticText(_("Last Update:") + " " + about.getLastUpdateString())
		AboutText += _("Last Update:") + " " + about.getLastUpdateString() + "\n\n"

		fp_version = getFPVersion()
		if fp_version is None:
			fp_version = ""
		elif fp_version != 0:
			fp_version = _("Frontprocessor version: %d") % fp_version
			AboutText += fp_version + "\n"
		self["FPVersion"] = StaticText(fp_version)

		self["TranslationHeader"] = StaticText(_("Translation:"))
		AboutText += _("Translation:") + "\n"

		# don't remove the string out of the _(), or it can't be "translated" anymore.
		# TRANSLATORS: Add here whatever should be shown in the "translator" about screen, up to 6 lines (use \n for newline)
		info = _("TRANSLATOR_INFO")

		if info == _("TRANSLATOR_INFO"):
			info = ""

		infolines = _("").split("\n")
		infomap = {}
		for x in infolines:
			l = x.split(': ')
			if len(l) != 2:
				continue
			(type, value) = l
			infomap[type] = value

		translator_name = infomap.get("Language-Team", "none")
		if translator_name == "none":
			translator_name = infomap.get("Last-Translator", "")

		self["TranslatorName"] = StaticText(translator_name)
		AboutText += translator_name + "\n\n"

		self["TranslationInfo"] = StaticText(info)
		AboutText += info

		self["AboutScrollLabel"] = ScrollLabel(AboutText)

	def showAboutReleaseNotes(self):
		self.session.open(ViewGitLog)

	def createSummary(self):
		return AboutSummary

class Devices(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Device Information"))
		self["TunerHeader"] = StaticText(_("Detected NIMs:"))
		self["HDDHeader"] = StaticText(_("Detected Devices:"))
		self["MountsHeader"] = StaticText(_("Network Servers:"))
		self["nims"] = StaticText()
		self["hdd"] = StaticText()
		self["mounts"] = StaticText()
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
		self["nims"].setText(scanning)
		self["hdd"].setText(scanning)
		self['mounts'].setText(scanning)
		self.activityTimer.start(10)

	def populate2(self):
		self.activityTimer.stop()
		self.Console = Console()
		niminfo = ""
		nims = nimmanager.nimList()
		for count in range(len(nims)):
			if niminfo:
				niminfo += "\n"
			niminfo += nims[count]
		self["nims"].setText(niminfo)

		hddlist = harddiskmanager.HDDList()
		hddinfo = ""
		if hddlist:
			for count in range(len(hddlist)):
				if hddinfo:
					hddinfo += "\n"
				hdd = hddlist[count][1]
				if int(hdd.free()) > 1024:
					hddinfo += "%s (%s, %d GB %s)" % (hdd.model(), hdd.capacity(), hdd.free()/1024, _("free"))
				else:
					hddinfo += "%s (%s, %d MB %s)" % (hdd.model(), hdd.capacity(), hdd.free(), _("free"))
		else:
			hddinfo = _("none")
		self["hdd"].setText(hddinfo)

		self.mountinfo = ""
		f = open('/proc/mounts', 'r')
		for line in f.readlines():
			self.parts = line.strip().split()
			if self.parts[0] and (self.parts[0].startswith('192') or self.parts[0].startswith('//192')):
				self.Console.ePopen("df -mh " + self.parts[1] + " | grep -v '^Filesystem'", self.Stage1Complete)
			else:
				self["mounts"].setText(_('none'))
		f.close()

	def Stage1Complete(self,result, retval, extra_args = None):
		mount = str(result).replace('\n','')
		mount = mount.split()
		ipaddress = mount[0]
		mounttotal = mount[1]
		mountfree = mount[3]
		if self.mountinfo:
			self.mountinfo += "\n"
		self.mountinfo += "%s (%sB, %sB %s)" % (ipaddress, mounttotal, mountfree, _("free"))
		self["mounts"].setText(self.mountinfo)

	def createSummary(self):
		return AboutSummary

class SystemMemoryInfo(Screen):
	skin = """
	<screen name="SystemMemoryInfo" position="center,center" size="560,400" >
		<widget source="lab1" render="Label" position="30,133" size="458,25" font="Boldit;24" transparent="0" zPosition="2" />
		<widget source="lab2" render="Label" position="30,158" size="458,25" font="Italic;19" transparent="0" zPosition="2" />
		<widget name="AboutScrollLabel" position="30,225" size="458,325" font="Regular;20" transparent="0" zPosition="1" scrollbarMode="showOnDemand"/>
	</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Memory Information"))
		self.skinName = ["SystemMemoryInfo", "About"]
		self["lab1"] = StaticText(_("Virtuosso Image Xtreme"))
		self["lab2"] = StaticText(_("By Team ViX"))
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

	def createSummary(self):
		return AboutSummary

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

		self["key_red"] = StaticText(_("Close"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.close,
				"ok": self.close,
			})
		self.resetList()
		self.updateStatusbar()
		self.timer = eTimer()
		self.timer.timeout.get().append(self.resetList)
		self.onShown.append(lambda: self.timer.start(8000))
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

	def createSummary(self):
		return AboutSummary

class AboutSummary(Screen):
	skin = """
	<screen name="AboutSummary" position="0,0" size="132,64">
		<widget source="selected" render="Label" position="0,0" size="124,32" font="Regular;16" />
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
		if about.getImageTypeString() == 'Release':
			self["selected"] = StaticText("ViX:" + about.getImageVersionString() + ' (R)')
		elif about.getImageTypeString() == 'Experimental':
			self["selected"] = StaticText("ViX:" + about.getImageVersionString() + ' (B)')
		if config.misc.boxtype.value == 'vuuno':
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Uno")
		elif config.misc.boxtype.value == 'vuultimo':
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Ultimo")
		elif config.misc.boxtype.value == 'vusolo':
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Solo")
		elif config.misc.boxtype.value == 'vuduo':
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Duo")
		elif config.misc.boxtype.value == 'et5x00':
			self["BoxType"] = StaticText(_("Hardware:") + " Xtrend ET5x00 Series")
		elif config.misc.boxtype.value == 'et6x00':
			self["BoxType"] = StaticText(_("Hardware:") + " Xtrend ET6x00 Series")
		elif config.misc.boxtype.value == 'et9x00':
			self["BoxType"] = StaticText(_("Hardware:") + " Xtrend ET9x00 Series")
		elif config.misc.boxtype.value == 'odin':
			self["BoxType"] = StaticText(_("Hardware:") + " Odin")
		else:
			self["BoxType"] = StaticText(_("Hardware:") + " " + config.misc.boxtype.value)
		self["KernelVersion"] = StaticText(_("Kernel:") + " " + about.getKernelVersionString())
		self["ImageType"] = StaticText(_("Image:") + " " + about.getImageTypeString())
		self["ImageVersion"] = StaticText(_("Version:") + " " + about.getImageVersionString() + "   " + _("Build:") + " " + about.getBuildVersionString())
		self["EnigmaVersion"] = StaticText(_("Last Update:") + " " + about.getLastUpdateString())

class ViewGitLog(Screen):
	def __init__(self, session, args = None):
		self.skin = """
			<screen position="center,center" size="720,540" >
				<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
				<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
				<widget name="key_red" position="0,2" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
				<widget name="key_yellow" position="280,2" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
				<widget name="text" position="0,50" size="720,500" font="Regular;21" />
			</screen>"""
		Screen.__init__(self, session)
		self.skinName = "SoftwareUpdateChanges"
		self.setTitle(_("OE Changes"))
		if path.exists('/tmp/oe-git.log'):
			remove('/tmp/oe-git.log')
		if path.exists('/tmp/e2-git.log'):
			remove('/tmp/e2-git.log')
		self.logtype = 'oe'
		self["text"] = ScrollLabel()
		self['title_summary'] = StaticText()
		self['text_summary'] = StaticText()
		self["key_red"] = Button(_("Close"))
		self["key_green"] = Button(_("OK"))
		self["key_yellow"] = Button(_("Show E2 Log"))
		self["myactions"] = ActionMap(['ColorActions', 'OkCancelActions', 'DirectionActions'],
		{
			'cancel': self.closeRecursive,
			'green': self.closeRecursive,
			"red": self.closeRecursive,
			"yellow": self.changelogtype,
			"left": self.pageUp,
			"right": self.pageDown,
			"down": self.pageDown,
			"up": self.pageUp
		},-1)
		self.onLayoutFinish.append(self.getlog)

	def changelogtype(self):
		if self.logtype == 'oe':
			self["key_yellow"].setText(_("Show E2 Log"))
			self.setTitle(_("OE Changes"))
			self.logtype = 'e2'
		else:
			self["key_yellow"].setText(_("Show OE Log"))
			self.setTitle(_("Enimga2 Changes"))
			self.logtype = 'oe'
		self.getlog()

	def pageUp(self):
		self["text"].pageUp()

	def pageDown(self):
		self["text"].pageDown()

	def getlog(self):
		fd = open('/etc/' + self.logtype + '-git.log', 'r')
		releasenotes = fd.read()
		fd.close()
		releasenotes = releasenotes.replace('\nopenvix: build',"\n\nopenvix: build")
		self["text"].setText(releasenotes)
		summarytext = releasenotes.split(':\n')
		try:
			self['title_summary'].setText(summarytext[0]+':')
			self['text_summary'].setText(summarytext[1])
		except:
			self['title_summary'].setText("")
			self['text_summary'].setText("")

	def unattendedupdate(self):
		self.close((_("Unattended upgrade without GUI and reboot system"), "cold"))

	def closeRecursive(self):
		self.close((_("Cancel"), ""))

