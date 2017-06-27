from Screen import Screen
from Screens.SoftwareUpdate import UpdatePlugin
from Screens.GitCommitInfo import CommitInfo
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Sources.StaticText import StaticText
from Components.Harddisk import Harddisk
from Components.NimManager import nimmanager
from Components.About import about
from Components.ScrollLabel import ScrollLabel
from Components.Console import Console
from Components.config import config
from enigma import eTimer, getEnigmaVersionString, getDesktop
from boxbranding import getMachineBrand, getMachineName, getImageVersion, getImageType, getImageBuild, getDriverDate, getImageDevBuild
from Components.Pixmap import MultiPixmap
from Components.Network import iNetwork
from Tools.StbHardware import getFPVersion
from os import path
from re import search
import skin

class About(Screen):
	def __init__(self, session, menu_path=""):
		Screen.__init__(self, session)
		screentitle = _("About")
		self.menu_path = menu_path
		if config.usage.show_menupath.value == 'large':
			self.menu_path += screentitle
			title = self.menu_path
			self["menu_path_compressed"] = StaticText("")
			self.menu_path += ' / '
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			condtext = ""
			if self.menu_path and not self.menu_path.endswith(' / '):
				condtext = self.menu_path + " >"
			elif self.menu_path:
				condtext = self.menu_path[:-3] + " >"
			self["menu_path_compressed"] = StaticText(condtext)
			self.menu_path += screentitle + ' / '
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)
		self.skinName = "AboutOE"
		self.populate()

		self["key_red"] = Button(_("Close"))
		self["key_green"] = Button(_("Translations"))
		self["key_yellow"] = Button(_("Software update"))
		self["key_blue"] = Button(_("Release notes"))
		self["actions"] = ActionMap(["SetupActions", "ColorActions", "TimerEditActions", "DirectionActions"],
									{
										"cancel": self.close,
										"ok": self.close,
										"up": self["AboutScrollLabel"].pageUp,
										"down": self["AboutScrollLabel"].pageDown,
										"red": self.close,
										"green": self.showTranslationInfo,
										"yellow": self.showUpdatePlugin,
										"blue": self.showAboutReleaseNotes,
									})

	def populate(self):
		self["lab1"] = StaticText(_("Virtuosso Image Xtreme"))
		self["lab2"] = StaticText(_("By Team ViX"))
		model = None
		AboutText = ""
		self["lab3"] = StaticText(_("Support at") + " www.world-of-satellite.com")

		AboutText += _("Model:\t%s %s\n") % (getMachineBrand(), getMachineName())

		if about.getChipSetString() != _("unavailable"):
			if about.getIsBroadcom():
				AboutText += _("Chipset:\tBCM%s\n") % about.getChipSetString().upper()
			else:
				AboutText += _("Chipset:\t%s\n") % about.getChipSetString().upper()

		AboutText += _("CPU:\t%s %s %s\n") % (about.getCPUArch(), about.getCPUSpeedString(), about.getCpuCoresString())
		imageSubBuild = ""
		if getImageType() != 'release':
			imageSubBuild = ".%s" % getImageDevBuild()
		AboutText += _("Image:\t%s.%s%s (%s)\n") % (getImageVersion(), getImageBuild(), imageSubBuild, getImageType().title())
		skinWidth = getDesktop(0).size().width()
		skinHeight = getDesktop(0).size().height()

		string = getDriverDate()
		year = string[0:4]
		month = string[4:6]
		day = string[6:8]
		driversdate = '-'.join((year, month, day))
		AboutText += _("Drivers:\t%s\n") % driversdate
		AboutText += _("Kernel:\t%s\n") % about.getKernelVersionString()
		AboutText += _("GStreamer:\t%s\n") % about.getGStreamerVersionString().replace("GStreamer ","")
		AboutText += _("Python:\t%s\n") % about.getPythonVersionString()
		AboutText += _("Installed:\t%s\n") % about.getFlashDateString()
		AboutText += _("Last update:\t%s\n") % getEnigmaVersionString()
		AboutText += _("E2 (re)starts:\t%s\n") % config.misc.startCounter.value
		AboutText += _("Skin:\t%s") % config.skin.primary_skin.value[0:-9] + _("  (%s x %s)") % (skinWidth, skinHeight) + "\n"

		tempinfo = ""
		if path.exists('/proc/stb/sensors/temp0/value'):
			f = open('/proc/stb/sensors/temp0/value', 'r')
			tempinfo = f.read()
			f.close()
		elif path.exists('/proc/stb/fp/temp_sensor'):
			f = open('/proc/stb/fp/temp_sensor', 'r')
			tempinfo = f.read()
			f.close()
		elif path.exists('/proc/stb/sensors/temp/value'):
			f = open('/proc/stb/sensors/temp/value', 'r')
			tempinfo = f.read()
			f.close()
		if tempinfo and int(tempinfo.replace('\n', '')) > 0:
			mark = str('\xc2\xb0')
			AboutText += _("System temp:\t%s") % tempinfo.replace('\n', '').replace(' ','') + mark + "C\n"

		tempinfo = ""
		if path.exists('/proc/stb/fp/temp_sensor_avs'):
			f = open('/proc/stb/fp/temp_sensor_avs', 'r')
			tempinfo = f.read()
			f.close()
		if tempinfo and int(tempinfo.replace('\n', '')) > 0:
			mark = str('\xc2\xb0')
			AboutText += _("Processor temp:\t%s") % tempinfo.replace('\n', '').replace(' ','') + mark + "C\n"
		AboutLcdText = AboutText.replace('\t', ' ')

		fp_version = getFPVersion()
		if fp_version is None:
			fp_version = ""
		elif fp_version != 0:
			fp_version = _("FP version:\t%s") % fp_version
			AboutText += fp_version + "\n"

		bootloader = ""
		if path.exists('/sys/firmware/devicetree/base/bolt/tag'):
				f = open('/sys/firmware/devicetree/base/bolt/tag', 'r')
				bootloader = f.readline().replace('\x00', '').replace('\n', '')
				f.close()
				AboutText += _("Bootloader:\t%s\n") % (bootloader)

		self["AboutScrollLabel"] = ScrollLabel(AboutText)

	def showTranslationInfo(self):
		self.session.open(TranslationInfo, self.menu_path)

	def showUpdatePlugin(self):
		self.session.open(UpdatePlugin, self.menu_path)

	def showAboutReleaseNotes(self):
		self.session.open(CommitInfo, self.menu_path)

	def createSummary(self):
		return AboutSummary

class Devices(Screen):
	def __init__(self, session, menu_path = ""):
		Screen.__init__(self, session)
		screentitle = _("Devices")
		if config.usage.show_menupath.value == 'large':
			menu_path += screentitle
			title = menu_path
			self["menu_path_compressed"] = StaticText("")
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			self["menu_path_compressed"] = StaticText(menu_path + " >" if not menu_path.endswith(' / ') else menu_path[:-3] + " >" or "")
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)
		self["TunerHeader"] = StaticText(_("Detected tuners:"))
		self["HDDHeader"] = StaticText(_("Detected devices:"))
		self["MountsHeader"] = StaticText(_("Network servers:"))
		self["nims"] = StaticText()
		for count in (0, 1, 2, 3):
			self["Tuner" + str(count)] = StaticText("")
		self["hdd"] = StaticText()
		self["mounts"] = StaticText()
		self.list = []
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.populate2)
		self["key_red"] = Button(_("Close"))
		self["actions"] = ActionMap(["SetupActions", "ColorActions", "TimerEditActions"],
									{
										"cancel": self.close,
										"ok": self.close,
										"red": self.close,
									})
		self.onLayoutFinish.append(self.populate)

	def populate(self):
		self.mountinfo = ''
		self["actions"].setEnabled(False)
		scanning = _("Please wait while scanning for devices...")
		self["nims"].setText(scanning)
		for count in (0, 1, 2, 3):
			self["Tuner" + str(count)].setText(scanning)
		self["hdd"].setText(scanning)
		self['mounts'].setText(scanning)
		self.activityTimer.start(1)

	def populate2(self):
		self.activityTimer.stop()
		self.Console = Console()
		niminfo = ""
		nims = nimmanager.nimListCompressed()
		for count in range(len(nims)):
			if niminfo:
				niminfo += "\n"
			niminfo += nims[count]
		self["nims"].setText(niminfo)

		nims = nimmanager.nimList()
		if len(nims) <= 4 :
			for count in (0, 1, 2, 3):
				if count < len(nims):
					self["Tuner" + str(count)].setText(nims[count])
				else:
					self["Tuner" + str(count)].setText("")
		else:
			desc_list = []
			count = 0
			cur_idx = -1
			while count < len(nims):
				data = nims[count].split(":")
				idx = data[0].strip('Tuner').strip()
				desc = data[1].strip()
				if desc_list and desc_list[cur_idx]['desc'] == desc:
					desc_list[cur_idx]['end'] = idx
				else:
					desc_list.append({'desc' : desc, 'start' : idx, 'end' : idx})
					cur_idx += 1
				count += 1

			for count in (0, 1, 2, 3):
				if count < len(desc_list):
					if desc_list[count]['start'] == desc_list[count]['end']:
						text = "Tuner %s: %s" % (desc_list[count]['start'], desc_list[count]['desc'])
					else:
						text = "Tuner %s-%s: %s" % (desc_list[count]['start'], desc_list[count]['end'], desc_list[count]['desc'])
				else:
					text = ""

				self["Tuner" + str(count)].setText(text)

		self.list = []
		list2 = []
		f = open('/proc/partitions', 'r')
		for line in f.readlines():
			parts = line.strip().split()
			if not parts:
				continue
			device = parts[3]
			if not search('sd[a-z][1-9]', device):
				continue
			if device in list2:
				continue

			mount = '/dev/' + device
			f = open('/proc/mounts', 'r')
			for line in f.readlines():
				if device in line:
					parts = line.strip().split()
					mount = str(parts[1])
					break
			f.close()

			if not mount.startswith('/dev/'):
				size = Harddisk(device).diskSize()
				free = Harddisk(device).free()

				if ((float(size) / 1024) / 1024) >= 1:
					sizeline = _("Size: ") + str(round(((float(size) / 1024) / 1024), 2)) + _("TB")
				elif (size / 1024) >= 1:
					sizeline = _("Size: ") + str(round((float(size) / 1024), 2)) + _("GB")
				elif size >= 1:
					sizeline = _("Size: ") + str(size) + _("MB")
				else:
					sizeline = _("Size: ") + _("unavailable")

				if ((float(free) / 1024) / 1024) >= 1:
					freeline = _("Free: ") + str(round(((float(free) / 1024) / 1024), 2)) + _("TB")
				elif (free / 1024) >= 1:
					freeline = _("Free: ") + str(round((float(free) / 1024), 2)) + _("GB")
				elif free >= 1:
					freeline = _("Free: ") + str(free) + _("MB")
				else:
					freeline = _("Free: ") + _("full")
				self.list.append(mount + '\t' + sizeline + ' \t' + freeline)
			else:
				self.list.append(mount + '\t' + _('Not mounted'))

			list2.append(device)
		self.list = '\n'.join(self.list)
		self["hdd"].setText(self.list)

		self.Console.ePopen("df -mh | grep -v '^Filesystem'", self.Stage1Complete)

	def Stage1Complete(self, result, retval, extra_args=None):
		result = result.replace('\n                        ', ' ').split('\n')
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
			self["mounts"].setText(self.mountinfo)
		else:
			self["mounts"].setText(_('none'))
		self["actions"].setEnabled(True)

	def createSummary(self):
		return AboutSummary


class SystemMemoryInfo(Screen):
	def __init__(self, session, menu_path = ""):
		Screen.__init__(self, session)
		screentitle = _("Memory")
		if config.usage.show_menupath.value == 'large':
			menu_path += screentitle
			title = menu_path
			self["menu_path_compressed"] = StaticText("")
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			self["menu_path_compressed"] = StaticText(menu_path + " >" if not menu_path.endswith(' / ') else menu_path[:-3] + " >" or "")
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)
		self.skinName = ["SystemMemoryInfo", "About"]
		self["lab1"] = StaticText(_("Virtuosso Image Xtreme"))
		self["lab2"] = StaticText(_("By Team ViX"))
		self["lab3"] = StaticText(_("Support at") + " www.world-of-satellite.com")
		self["AboutScrollLabel"] = ScrollLabel()

		self["key_red"] = Button(_("Close"))
		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
									{
										"cancel": self.close,
										"ok": self.close,
										"red": self.close,
									})

		out_lines = file("/proc/meminfo").readlines()
		self.AboutText = _("RAM") + '\n\n'
		RamTotal = "-"
		RamFree = "-"
		for lidx in range(len(out_lines) - 1):
			tstLine = out_lines[lidx].split()
			if "MemTotal:" in tstLine:
				MemTotal = out_lines[lidx].split()
				self.AboutText += _("Total memory:") + "\t" + MemTotal[1] + "\n"
			if "MemFree:" in tstLine:
				MemFree = out_lines[lidx].split()
				self.AboutText += _("Free memory:") + "\t" + MemFree[1] + "\n"
			if "Buffers:" in tstLine:
				Buffers = out_lines[lidx].split()
				self.AboutText += _("Buffers:") + "\t" + Buffers[1] + "\n"
			if "Cached:" in tstLine:
				Cached = out_lines[lidx].split()
				self.AboutText += _("Cached:") + "\t" + Cached[1] + "\n"
			if "SwapTotal:" in tstLine:
				SwapTotal = out_lines[lidx].split()
				self.AboutText += _("Total swap:") + "\t" + SwapTotal[1] + "\n"
			if "SwapFree:" in tstLine:
				SwapFree = out_lines[lidx].split()
				self.AboutText += _("Free swap:") + "\t" + SwapFree[1] + "\n\n"

		self["actions"].setEnabled(False)
		self.Console = Console()
		self.Console.ePopen("df -mh / | grep -v '^Filesystem'", self.Stage1Complete)

	def Stage1Complete(self, result, retval, extra_args=None):
		flash = str(result).replace('\n', '')
		flash = flash.split()
		RamTotal = flash[1]
		RamFree = flash[3]

		self.AboutText += _("FLASH") + '\n\n'
		self.AboutText += _("Total:") + "\t" + RamTotal + "\n"
		self.AboutText += _("Free:") + "\t" + RamFree + "\n\n"

		self["AboutScrollLabel"].setText(self.AboutText)
		self["actions"].setEnabled(True)

	def createSummary(self):
		return AboutSummary


class SystemNetworkInfo(Screen):
	def __init__(self, session, menu_path = ""):
		Screen.__init__(self, session)
		screentitle = _("Network")
		if config.usage.show_menupath.value == 'large':
			menu_path += screentitle
			title = menu_path
			self["menu_path_compressed"] = StaticText("")
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			self["menu_path_compressed"] = StaticText(menu_path + " >" if not menu_path.endswith(' / ') else menu_path[:-3] + " >" or "")
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)
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
		self["statuspic"].setPixmapNum(1)
		self["statuspic"].show()
		self["devicepic"] = MultiPixmap()

		self["AboutScrollLabel"] = ScrollLabel()

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

		self["key_red"] = StaticText(_("Close"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"],
									{
										"cancel": self.close,
										"ok": self.close,
										"up": self["AboutScrollLabel"].pageUp,
										"down": self["AboutScrollLabel"].pageDown
									})
		self.onLayoutFinish.append(self.updateStatusbar)

	def createscreen(self):
		self.AboutText = ""
		self.iface = "eth0"
		eth0 = about.getIfConfig('eth0')
		if eth0.has_key('addr'):
			self.AboutText += _("IP:") + "\t" + eth0['addr'] + "\n"
			if eth0.has_key('netmask'):
				self.AboutText += _("Netmask:") + "\t" + eth0['netmask'] + "\n"
			if eth0.has_key('hwaddr'):
				self.AboutText += _("MAC:") + "\t" + eth0['hwaddr'] + "\n"
			self.iface = 'eth0'

		eth1 = about.getIfConfig('eth1')
		if eth1.has_key('addr'):
			self.AboutText += _("IP:") + "\t" + eth1['addr'] + "\n"
			if eth1.has_key('netmask'):
				self.AboutText += _("Netmask:") + "\t" + eth1['netmask'] + "\n"
			if eth1.has_key('hwaddr'):
				self.AboutText += _("MAC:") + "\t" + eth1['hwaddr'] + "\n"
			self.iface = 'eth1'

		ra0 = about.getIfConfig('ra0')
		if ra0.has_key('addr'):
			self.AboutText += _("IP:") + "\t" + ra0['addr'] + "\n"
			if ra0.has_key('netmask'):
				self.AboutText += _("Netmask:") + "\t" + ra0['netmask'] + "\n"
			if ra0.has_key('hwaddr'):
				self.AboutText += _("MAC:") + "\t" + ra0['hwaddr'] + "\n"
			self.iface = 'ra0'

		wlan0 = about.getIfConfig('wlan0')
		if wlan0.has_key('addr'):
			self.AboutText += _("IP:") + "\t" + wlan0['addr'] + "\n"
			if wlan0.has_key('netmask'):
				self.AboutText += _("Netmask:") + "\t" + wlan0['netmask'] + "\n"
			if wlan0.has_key('hwaddr'):
				self.AboutText += _("MAC:") + "\t" + wlan0['hwaddr'] + "\n"
			self.iface = 'wlan0'

		wlan3 = about.getIfConfig('wlan3')
		if wlan3.has_key('addr'):
			self.AboutText += _("IP:") + "\t" + wlan3['addr'] + "\n"
			if wlan3.has_key('netmask'):
				self.AboutText += _("Netmask:") + "\t" + wlan3['netmask'] + "\n"
			if wlan3.has_key('hwaddr'):
				self.AboutText += _("MAC:") + "\t" + wlan3['hwaddr'] + "\n"
			self.iface = 'wlan3'

		rx_bytes, tx_bytes = about.getIfTransferredData(self.iface)
		self.AboutText += "\n" + _("Bytes received:") + "\t" + rx_bytes + "\n"
		self.AboutText += _("Bytes sent:") + "\t" + tx_bytes + "\n"

		self.console = Console()
		self.console.ePopen('ethtool %s' % self.iface, self.SpeedFinished)

	def SpeedFinished(self, result, retval, extra_args):
		result_tmp = result.split('\n')
		for line in result_tmp:
			if 'Speed:' in line:
				speed = line.split(': ')[1][:-4]
				self.AboutText += _("Speed:") + "\t" + speed + _('Mb/s')

		hostname = file('/proc/sys/kernel/hostname').read()
		self.AboutText += "\n" + _("Hostname:") + "\t" + hostname + "\n"
		self["AboutScrollLabel"].setText(self.AboutText)

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
					if self.iface == 'wlan0' or self.iface == 'wlan3' or self.iface == 'ra0':
						if status[self.iface]["essid"] == "off":
							essid = _("No connection")
						else:
							essid = status[self.iface]["essid"]
						if status[self.iface]["accesspoint"] == "Not-Associated":
							accesspoint = _("Not-Associated")
							essid = _("No connection")
						else:
							accesspoint = status[self.iface]["accesspoint"]
						if self.has_key("BSSID"):
							self.AboutText += _('Accesspoint:') + '\t' + accesspoint + '\n'
						if self.has_key("ESSID"):
							self.AboutText += _('SSID:') + '\t' + essid + '\n'

						quality = status[self.iface]["quality"]
						if self.has_key("quality"):
							self.AboutText += _('Link quality:') + '\t' + quality + '\n'

						if status[self.iface]["bitrate"] == '0':
							bitrate = _("Unsupported")
						else:
							bitrate = str(status[self.iface]["bitrate"]) + " Mb/s"
						if self.has_key("bitrate"):
							self.AboutText += _('Bitrate:') + '\t' + bitrate + '\n'

						signal = status[self.iface]["signal"]
						if self.has_key("signal"):
							self.AboutText += _('Signal strength:') + '\t' + signal + '\n'

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
							self["statuspic"].setPixmapNum(1)
							self["statuspic"].show()
						else:
							self.LinkState = True
							iNetwork.checkNetworkState(self.checkNetworkCB)
						self["AboutScrollLabel"].setText(self.AboutText)

	def exit(self):
		self.close(True)

	def updateStatusbar(self):
		self["IFtext"].setText(_("Network:"))
		self["IF"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		self["Statustext"].setText(_("Link:"))
		if iNetwork.isWirelessInterface(self.iface):
			self["devicepic"].setPixmapNum(1)
			try:
				self.iStatus.getDataForInterface(self.iface, self.getInfoCB)
			except:
				self["statuspic"].setPixmapNum(1)
				self["statuspic"].show()
		else:
			iNetwork.getLinkState(self.iface, self.dataAvail)
			self["devicepic"].setPixmapNum(0)
		self["devicepic"].show()

	def dataAvail(self, data):
		self.LinkState = None
		for line in data.splitlines():
			line = line.strip()
			if 'Link detected:' in line:
				if "yes" in line:
					self.LinkState = True
				else:
					self.LinkState = False
		if self.LinkState:
			iNetwork.checkNetworkState(self.checkNetworkCB)
		else:
			self["statuspic"].setPixmapNum(1)
			self["statuspic"].show()

	def checkNetworkCB(self, data):
		try:
			if iNetwork.getAdapterAttribute(self.iface, "up") is True:
				if self.LinkState is True:
					if data <= 2:
						self["statuspic"].setPixmapNum(0)
					else:
						self["statuspic"].setPixmapNum(1)
				else:
					self["statuspic"].setPixmapNum(1)
			else:
				self["statuspic"].setPixmapNum(1)
			self["statuspic"].show()
		except:
			pass

	def createSummary(self):
		return AboutSummary


class AboutSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["selected"] = StaticText("ViX:" + getImageVersion())

		AboutText = _("Model: %s %s\n") % (getMachineBrand(), getMachineName())

		if path.exists('/proc/stb/info/chipset'):
			chipset = open('/proc/stb/info/chipset', 'r').read()
			AboutText += _("Chipset: BCM%s") % chipset.replace('\n', '') + "\n"

		AboutText += _("Version: %s") % getImageVersion() + "\n"
		AboutText += _("Build: %s") % getImageBuild() + "\n"
		AboutText += _("Kernel: %s") % about.getKernelVersionString() + "\n"

		string = getDriverDate()
		year = string[0:4]
		month = string[4:6]
		day = string[6:8]
		driversdate = '-'.join((year, month, day))
		AboutText += _("Drivers: %s") % driversdate + "\n"
		AboutText += _("Last update: %s") % getEnigmaVersionString() + "\n\n"

		tempinfo = ""
		if path.exists('/proc/stb/sensors/temp0/value'):
			tempinfo = open('/proc/stb/sensors/temp0/value', 'r').read()
		elif path.exists('/proc/stb/fp/temp_sensor'):
			tempinfo = open('/proc/stb/fp/temp_sensor', 'r').read()
		if tempinfo and int(tempinfo.replace('\n', '')) > 0:
			mark = str('\xc2\xb0')
			AboutText += _("System temperature: %s") % tempinfo.replace('\n', '') + mark + "C\n\n"

		self["AboutText"] = StaticText(AboutText)

class TranslationInfo(Screen):
	def __init__(self, session, menu_path=""):
		Screen.__init__(self, session)
		screentitle = _("Translations")
		if config.usage.show_menupath.value == 'large':
			menu_path += screentitle
			title = menu_path
			self["menu_path_compressed"] = StaticText("")
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			self["menu_path_compressed"] = StaticText(menu_path + " >" if not menu_path.endswith(' / ') else menu_path[:-3] + " >" or "")
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)
		# don't remove the string out of the _(), or it can't be "translated" anymore.

		# TRANSLATORS: Add here whatever should be shown in the "translator" about screen, up to 6 lines (use \n for newline)
		info = _("TRANSLATOR_INFO")

		if info == "TRANSLATOR_INFO":
			info = ""

		infolines = _("").split("\n")
		infomap = {}
		for x in infolines:
			l = x.split(': ')
			if len(l) != 2:
				continue
			(type, value) = l
			infomap[type] = value
		print infomap

		self["key_red"] = Button(_("Close"))
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
