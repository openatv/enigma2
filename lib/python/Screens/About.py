from Screen import Screen
from Components.config import config
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Harddisk import harddiskmanager
from Components.NimManager import nimmanager
from Components.About import about
from Components.ScrollLabel import ScrollLabel
from Components.Button import Button
from Components.config import config

from Components.Pixmap import MultiPixmap
from Components.Network import iNetwork

from Components.Label import Label
from Components.ProgressBar import ProgressBar

from Tools.StbHardware import getFPVersion

from boxbranding import getBoxType
boxtype = getBoxType()

from enigma import eTimer, eLabel

from Components.HTMLComponent import HTMLComponent
from Components.GUIComponent import GUIComponent
import skin


class About(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		hddsplit, = skin.parameters.get("AboutHddSplit", (0,))

		#AboutHddSplit = 0
		#try:
		#	hddsplit = skin.parameters.get("AboutHddSplit",(0))[0]
		#except:
		#	hddsplit = AboutHddSplit

		if boxtype == 'gb800solo':
			BoxName = "GigaBlue HD 800SOLO"
		elif boxtype == 'gb800se':
			BoxName = "GigaBlue HD 800SE"
		elif boxtype == 'gb800ue':
			BoxName = "GigaBlue HD 800UE"
		elif boxtype == 'gbquad':
			BoxName = "GigaBlue HD Quad"
		elif boxtype == 'gbquadplus':
			BoxName = "GigaBlue HD Quadplus"
		elif boxtype == 'gb800seplus':
			BoxName = "GigaBlue HD 800SEplus"
		elif boxtype == 'gb800ueplus':
			BoxName = "GigaBlue HD 800UEplus"
		elif boxtype == 'gbipbox':
			BoxName = "GigaBlue IP Box"
		elif boxtype == 'gbultra':
			BoxName = "GigaBlue HD Ultra"
		elif boxtype == 'gbultraue':
			BoxName = "GigaBlue HD Ultra UE"
		elif boxtype == 'gbultrase':
			BoxName = "GigaBlue HD Ultra SE"
		elif boxtype == 'gbx1':
			BoxName = "GigaBlue X1"
		elif boxtype == 'gbx3':
			BoxName = "GigaBlue X3"
		elif boxtype == 'spycat':
			BoxName = "XCORE Spycat"
		elif boxtype == 'quadbox2400':
			BoxName = "AX Quadbox HD2400"
		else:
			BoxName = about.getHardwareTypeString()

		ImageType = about.getImageTypeString()
		self["ImageType"] = StaticText(ImageType)

		AboutHeader = ImageType + " - " + BoxName
		self["AboutHeader"] = StaticText(AboutHeader)

		AboutText = AboutHeader + "\n"

		#AboutText += _("Hardware: ") + about.getHardwareTypeString() + "\n"
		#AboutText += _("CPU: ") + about.getCPUInfoString() + "\n"
		#AboutText += _("Installed: ") + about.getFlashDateString() + "\n"
		#AboutText += _("Image: ") + about.getImageTypeString() + "\n"

		CPUinfo = _("CPU: ") + about.getCPUInfoString() + "\n"
		self["CPUinfo"] = StaticText(CPUinfo)
		AboutText += CPUinfo + "\n"

		CPUspeed = _("Speed: ") + about.getCPUSpeedString() + "\n"
		self["CPUspeed"] = StaticText(CPUspeed)
		AboutText += CPUspeed + "\n"

		ChipsetInfo = _("Chipset: ") + about.getChipSetString() + "\n"
		self["ChipsetInfo"] = StaticText(ChipsetInfo)
		AboutText += ChipsetInfo + "\n"

		KernelVersion = _("Kernel version: ") + about.getKernelVersionString() + "\n"
		self["KernelVersion"] = StaticText(KernelVersion)
		AboutText += KernelVersion + "\n"

		EnigmaVersion = _("GUI Build: ") + about.getEnigmaVersionString()
		self["EnigmaVersion"] = StaticText(EnigmaVersion)
		AboutText += EnigmaVersion + "\n"
		AboutText += _("Enigma (re)starts: %d\n") % config.misc.startCounter.value
		
		EnigmaSkin = _("Skin: ") + config.skin.primary_skin.value[0:-9]
		self["EnigmaSkin"] = StaticText(EnigmaSkin)
		AboutText += EnigmaSkin + "\n"

		GStreamerVersion = _("GStreamer: ") + about.getGStreamerVersionString().replace("GStreamer","")
		self["GStreamerVersion"] = StaticText(GStreamerVersion)
		AboutText += GStreamerVersion + "\n"

		FlashDate = _("Flashed: ") + about.getFlashDateString()
		self["FlashDate"] = StaticText(FlashDate)
		AboutText += FlashDate + "\n"

		ImageVersion = _("Last upgrade: ") + about.getImageVersionString()
		self["ImageVersion"] = StaticText(ImageVersion)
		AboutText += ImageVersion + "\n"

		AboutText += _("DVB drivers: ") + about.getDriverInstalledDate() + "\n"

		AboutText += _("Python version: ") + about.getPythonVersionString() + "\n"

		fp_version = getFPVersion()
		if fp_version is None:
			fp_version = ""
		else:
			fp_version = _("Frontprocessor version: %d") % fp_version
			AboutText += fp_version + "\n"

		self["FPVersion"] = StaticText(fp_version)

		self["TunerHeader"] = StaticText(_("Detected NIMs:"))
		AboutText += "\n" + _("Detected NIMs:") + "\n"

		nims = nimmanager.nimList()
		for count in range(len(nims)):
			if count < 4:
				self["Tuner" + str(count)] = StaticText(nims[count])
			else:
				self["Tuner" + str(count)] = StaticText("")
			AboutText += nims[count] + "\n"

		self["HDDHeader"] = StaticText(_("Detected HDD:"))
		AboutText += "\n" + _("Detected HDD:") + "\n"

		hddlist = harddiskmanager.HDDList()
		hddinfo = ""
		if hddlist:
			formatstring = hddsplit and "%s:%s, %.1f %sB %s" or "%s\n(%s, %.1f %sB %s)"
			for count in range(len(hddlist)):
				if hddinfo:
					hddinfo += "\n"
				hdd = hddlist[count][1]
				if int(hdd.free()) > 1024:
					hddinfo += formatstring % (hdd.model(), hdd.capacity(), hdd.free()/1024, "G", _("free"))
				else:
					hddinfo += formatstring % (hdd.model(), hdd.capacity(), hdd.free()/1024, "M", _("free"))
		else:
			hddinfo = _("none")
		self["hddA"] = StaticText(hddinfo)
		AboutText += hddinfo
		self["AboutScrollLabel"] = ScrollLabel(AboutText)
		self["key_green"] = Button(_("Translations"))
		self["key_red"] = Button(_("Latest Commits"))
		self["key_blue"] = Button(_("Memory Info"))

		self["actions"] = ActionMap(["ColorActions", "SetupActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"red": self.showCommits,
				"green": self.showTranslationInfo,
				"blue": self.showMemoryInfo,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown
			})

	def showTranslationInfo(self):
		self.session.open(TranslationInfo)

	def showCommits(self):
		self.session.open(CommitInfo)

	def showMemoryInfo(self):
		self.session.open(MemoryInfo)

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

		self["key_red"] = Button(_("Cancel"))
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

class CommitInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["CommitInfo", "About"]
		self["AboutScrollLabel"] = ScrollLabel(_("Please wait"))

		self["actions"] = ActionMap(["SetupActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown,
				"left": self.left,
				"right": self.right,
				"deleteBackward": self.left,
				"deleteForward": self.right
			})

		self["key_red"] = Button(_("Cancel"))

		self.project = 0
		self.projects = [
			#("organisation",  "repository",           "readable name",                "branch"),
			("openmips",      "stbgui",               "openMips Enigma2",             "master"),
			("openmips",      "skin-pax",             "openMips Skin GigaBlue Pax",   "master"),
			("oe-alliance",   "oe-alliance-core",     "OE Alliance Core",             "2.3"),
			("oe-alliance",   "oe-alliance-plugins",  "OE Alliance Plugins",          "2.3"),
			("oe-alliance",   "enigma2-plugins",      "OE Alliance Enigma2 Plugins",  "2.3")
		]
		self.cachedProjects = {}
		self.Timer = eTimer()
		self.Timer.callback.append(self.readGithubCommitLogs)
		self.Timer.start(50, True)

	def readGithubCommitLogs(self):
		url = 'https://api.github.com/repos/%s/%s/commits?sha=%s' % (self.projects[self.project][0], self.projects[self.project][1], self.projects[self.project][3])
		# print "[About] url: ", url
		commitlog = ""
		from datetime import datetime
		from json import loads
		from urllib2 import urlopen
		try:
			commitlog += 80 * '-' + '\n'
			commitlog += self.projects[self.project][2] + ' - ' + self.projects[self.project][1] + ' - branch:' + self.projects[self.project][3] + '\n'
			commitlog += 'URL: https://github.com/' + self.projects[self.project][0] + '/' + self.projects[self.project][1] + '/tree/' + self.projects[self.project][3] + '\n'
			commitlog += 80 * '-' + '\n'
			for c in loads(urlopen(url, timeout=5).read()):
				creator = c['commit']['author']['name']
				title = c['commit']['message']
				date = datetime.strptime(c['commit']['committer']['date'], '%Y-%m-%dT%H:%M:%SZ').strftime('%x %X')
				if title.startswith ("Merge "):
					pass
				else:
					commitlog += date + ' ' + creator + '\n' + title + 2 * '\n'
			commitlog = commitlog.encode('utf-8')
			self.cachedProjects[self.projects[self.project][2]] = commitlog
		except:
			commitlog += _("Currently the commit log cannot be retrieved - please try later again")
		self["AboutScrollLabel"].setText(commitlog)

	def updateCommitLogs(self):
		if self.cachedProjects.has_key(self.projects[self.project][2]):
			self["AboutScrollLabel"].setText(self.cachedProjects[self.projects[self.project][2]])
		else:
			self["AboutScrollLabel"].setText(_("Please wait"))
			self.Timer.start(50, True)

	def left(self):
		self.project = self.project == 0 and len(self.projects) - 1 or self.project - 1
		self.updateCommitLogs()

	def right(self):
		self.project = self.project != len(self.projects) - 1 and self.project + 1 or 0
		self.updateCommitLogs()

class MemoryInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.close,
				"ok": self.getMemoryInfo,
				"green": self.getMemoryInfo,
				"blue": self.clearMemory,
			})

		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Refresh"))
		self["key_blue"] = Label(_("Clear"))

		self['lmemtext'] = Label()
		self['lmemvalue'] = Label()
		self['rmemtext'] = Label()
		self['rmemvalue'] = Label()

		self['pfree'] = Label()
		self['pused'] = Label()
		self["slide"] = ProgressBar()
		self["slide"].setValue(100)

		self["params"] = MemoryInfoSkinParams()

		self['info'] = Label(_("This info is for developers only.\nIt is not important for a normal user.\nPlease - do not panic on any displayed suspicious information!"))

		self.setTitle(_("Memory Info"))
		self.onLayoutFinish.append(self.getMemoryInfo)

	def getMemoryInfo(self):
		try:
			ltext = rtext = ""
			lvalue = rvalue = ""
			mem = 1
			free = 0
			i = 0
			for line in open('/proc/meminfo','r'):
				( name, size, units ) = line.strip().split()
				if "MemTotal" in name:
					mem = int(size)
				if "MemFree" in name:
					free = int(size)
				if i < self["params"].rows_in_column:
					ltext += "".join((name,"\n"))
					lvalue += "".join((size," ",units,"\n"))
				else:
					rtext += "".join((name,"\n"))
					rvalue += "".join((size," ",units,"\n"))
				i += 1
			self['lmemtext'].setText(ltext)
			self['lmemvalue'].setText(lvalue)
			self['rmemtext'].setText(rtext)
			self['rmemvalue'].setText(rvalue)

			self["slide"].setValue(int(100.0*(mem-free)/mem+0.25))
			self['pfree'].setText("%.1f %s" % (100.*free/mem,'%'))
			self['pused'].setText("%.1f %s" % (100.*(mem-free)/mem,'%'))

		except Exception, e:
			print "[About] getMemoryInfo FAIL:", e

	def clearMemory(self):
		from os import system
		system("sync")
		system("echo 3 > /proc/sys/vm/drop_caches")
		self.getMemoryInfo()

class MemoryInfoSkinParams(HTMLComponent, GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.rows_in_column = 25

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "rowsincolumn":
					self.rows_in_column = int(value)
			self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop, screen)

	GUI_WIDGET = eLabel


class SystemNetworkInfo(Screen):
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

		self.iface = None
		self.createscreen()
		self.iStatus = None

		if iNetwork.isWirelessInterface(self.iface):
			try:
				from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
				self.iStatus = iStatus
			except:
				pass
			self.resetList()
			self.onClose.append(self.cleanup)
		self.updateStatusbar()

		self["key_red"] = StaticText(_("Close"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown
			})

	def createscreen(self):
		self.AboutText = ""
		self.iface = "eth0"
		eth0 = about.getIfConfig('eth0')
		if eth0.has_key('addr'):
			if eth0.has_key('ifname'):
				self.AboutText += _('Interface:\t/dev/' + eth0['ifname'] + "\n")
			self.AboutText += _("IP:") + "\t" + eth0['addr'] + "\n"
			if eth0.has_key('netmask'):
				self.AboutText += _("Netmask:") + "\t" + eth0['netmask'] + "\n"
			if eth0.has_key('brdaddr'):
				self.AboutText += _('Broadcast:\t' + eth0['brdaddr'] + "\n")
			if eth0.has_key('hwaddr'):
				self.AboutText += _("MAC:") + "\t" + eth0['hwaddr'] + "\n"
			self.iface = 'eth0'

		eth1 = about.getIfConfig('eth1')
		if eth1.has_key('addr'):
			if eth1.has_key('ifname'):
				self.AboutText += _('Interface:\t/dev/' + eth1['ifname'] + "\n")
			self.AboutText += _("IP:") + "\t" + eth1['addr'] + "\n"
			if eth1.has_key('netmask'):
				self.AboutText += _("Netmask:") + "\t" + eth1['netmask'] + "\n"
			if eth1.has_key('brdaddr'):
				self.AboutText += _('Broadcast:\t' + eth1['brdaddr'] + "\n")
			if eth1.has_key('hwaddr'):
				self.AboutText += _("MAC:") + "\t" + eth1['hwaddr'] + "\n"
			self.iface = 'eth1'
		
		ra0 = about.getIfConfig('ra0')
		if ra0.has_key('addr'):
			if ra0.has_key('ifname'):
				self.AboutText += _('Interface:\t/dev/' + ra0['ifname'] + "\n")
			self.AboutText += _("IP:") + "\t" + ra0['addr'] + "\n"
			if ra0.has_key('netmask'):
				self.AboutText += _("Netmask:") + "\t" + ra0['netmask'] + "\n"
			if ra0.has_key('brdaddr'):
				self.AboutText += _('Broadcast:\t' + ra0['brdaddr'] + "\n")
			if ra0.has_key('hwaddr'):
				self.AboutText += _("MAC:") + "\t" + ra0['hwaddr'] + "\n"
			self.iface = 'ra0'

		wlan0 = about.getIfConfig('wlan0')
		if wlan0.has_key('addr'):
			if wlan0.has_key('ifname'):
				self.AboutText += _('Interface:\t/dev/' + wlan0['ifname'] + "\n")
			self.AboutText += _("IP:") + "\t" + wlan0['addr'] + "\n"
			if wlan0.has_key('netmask'):
				self.AboutText += _("Netmask:") + "\t" + wlan0['netmask'] + "\n"
			if wlan0.has_key('brdaddr'):
				self.AboutText += _('Broadcast:\t' + wlan0['brdaddr'] + "\n")	
			if wlan0.has_key('hwaddr'):
				self.AboutText += _("MAC:") + "\t" + wlan0['hwaddr'] + "\n"
			self.iface = 'wlan0'

		rx_bytes, tx_bytes = about.getIfTransferredData(self.iface)
		self.AboutText += "\n" + _("Bytes received:") + "\t" + rx_bytes + '  (~'  + str(int(rx_bytes)/1024/1024)  + ' MB)'  + "\n"
		self.AboutText += _("Bytes sent:") + "\t" + tx_bytes + '  (~'  + str(int(tx_bytes)/1024/1024)+ ' MB)'  + "\n"

		hostname = file('/proc/sys/kernel/hostname').read()
		self.AboutText += "\n" + _("Hostname:") + "\t" + hostname + "\n"
		self["AboutScrollLabel"] = ScrollLabel(self.AboutText)

	def cleanup(self):
		if self.iStatus:
			self.iStatus.stopWlanConsole()

	def resetList(self):
		if self.iStatus:
			self.iStatus.getDataForInterface(self.iface, self.getInfoCB)

	def getInfoCB(self, data, status):
		self.LinkState = None
		if data is not None:
			if data is True:
				if status is not None:
					if self.iface == 'wlan0' or self.iface == 'ra0':
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
							self.AboutText += _('Accesspoint:') + '\t' + accesspoint + '\n'
						if self.has_key("ESSID"):
							self.AboutText += _('SSID:') + '\t' + essid + '\n'

						quality = status[self.iface]["quality"]
						if self.has_key("quality"):
							self.AboutText += _('Link Quality:') + '\t' + quality + '\n'

						if status[self.iface]["bitrate"] == '0':
							bitrate = _("Unsupported")
						else:
							bitrate = str(status[self.iface]["bitrate"]) + " Mb/s"
						if self.has_key("bitrate"):
							self.AboutText += _('Bitrate:') + '\t' + bitrate + '\n'

						signal = status[self.iface]["signal"]
						if self.has_key("signal"):
							self.AboutText += _('Signal Strength:') + '\t' + signal + '\n'

						if status[self.iface]["encryption"] == "off":
							if accesspoint == "Not-Associated":
								encryption = _("Disabled")
							else:
								encryption = _("Unsupported")
						else:
							encryption = _("Enabled")
						if self.has_key("enc"):
							self.AboutText += _('Encryption:') + '\t' + encryption + '\n'

						if status[self.iface]["essid"] == "off" or status[self.iface]["accesspoint"] == "Not-Associated" or status[self.iface]["accesspoint"] is False:
							self.LinkState = False
						else:
							self.LinkState = True
						self["AboutScrollLabel"].setText(self.AboutText)

	def exit(self):
		self.close(True)

	def updateStatusbar(self):
		self["IFtext"].setText(_("Network:"))
		self["IF"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		if iNetwork.isWirelessInterface(self.iface):
			try:
				self.iStatus.getDataForInterface(self.iface, self.getInfoCB)
			except:
				pass
		else:
			iNetwork.getLinkState(self.iface, self.dataAvail)

	def dataAvail(self, data):
		self.LinkState = None
		for line in data.splitlines():
			line = line.strip()
			if 'Link detected:' in line:
				if "yes" in line:
					self.LinkState = True
				else:
					self.LinkState = False
