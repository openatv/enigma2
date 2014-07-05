from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Harddisk import Harddisk, Partition, harddiskmanager, getProcMounts
from Components.NimManager import nimmanager
from Components.About import about
from Components.config import config
from Components.ScrollLabel import ScrollLabel
from Components.Console import Console
from Components.Label import Label
from enigma import eTimer, getEnigmaVersionString
from boxbranding import getBoxType, getMachineBrand, getMachineName, getImageVersion, getImageBuild, getDriverDate

from Components.Pixmap import MultiPixmap
from Components.Network import iNetwork

from Tools.StbHardware import getFPVersion
from os import path, listdir, stat
from re import match

def sizeStr(size, unknown=_("unavailable")):
	if float(size) / 2**20 >= 1:
		return str(round(float(size) / 2**20, 2)) + _("TB")
	if (float(size) / 2**10) >= 1:
		return str(round(float(size) / 2**10, 2)) + _("GB")
	if size >= 1:
		return str(size) + _("MB")
	return  unknown

class About(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		AboutText = _("Model:\t%s %s\n") % (getMachineBrand(), getMachineName())

		if path.exists('/proc/stb/info/chipset'):
			AboutText += _("Chipset:\tBCM%s") % about.getChipSetString() + "\n"

		AboutText += _("CPU:\t%s") % about.getCPUString() + "\n"
		AboutText += _("Cores:\t%s") % about.getCpuCoresString() + "\n"

		string = getDriverDate()
		year = string[0:4]
		month = string[4:6]
		day = string[6:8]
		driversdate = '-'.join((year, month, day))
		AboutText += _("Drivers:\t%s") % driversdate + "\n"
		AboutText += _("Image:\t%s") % about.getImageVersionString() + "\n"
		AboutText += _("Kernel: \t%s") % about.getKernelVersionString() + "\n"
		AboutText += _("Oe-Core:\t%s") % about.getEnigmaVersionString() + "\n"

		fp_version = getFPVersion()
		if fp_version is None:
			fp_version = ""
		else:
			fp_version = _("Front Panel:\t%d") % fp_version
			AboutText += fp_version + "\n\n"

		AboutText += _("Last Upgrade:\t%s") % about.getLastUpdateString() + "\n\n"
		AboutText += _("WWW:\t%s") % about.getImageUrlString()

		tempinfo = ""
		if path.exists('/proc/stb/sensors/temp0/value'):
			f = open('/proc/stb/sensors/temp0/value', 'r')
			tempinfo = f.read()
			f.close()
		elif path.exists('/proc/stb/fp/temp_sensor'):
			f = open('/proc/stb/fp/temp_sensor', 'r')
			tempinfo = f.read()
			f.close()
		if tempinfo and int(tempinfo.replace('\n', '')) > 0:
			mark = str('\xc2\xb0')
			AboutText += _("System temperature: %s") % tempinfo.replace('\n', '') + mark + "C\n\n"

		nims = nimmanager.nimList()
		for count in range(len(nims)):
			if count < 4:
				self["Tuner" + str(count)] = StaticText(nims[count])
			else:
				self["Tuner" + str(count)] = StaticText("")

		self["AboutScrollLabel"] = ScrollLabel(AboutText)

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown,
				"left": self["AboutScrollLabel"].pageUp,
				"right": self["AboutScrollLabel"].pageDown,
			})

class Devices(Screen):

	FSTABIPMATCH = "(//)?\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/"

       # Mapping fuseblk is a hack that only works if NTFS
       # is the only FUSE file system loaded.

	fsNameMap = { "fuseblk": "NTFS", "hfs": "HFS", "hfsplus": "HFS+",
			"iso9660": "ISO9660", "msdos" : "FAT",
			"ubifs": "UBIFS", "udf": "UDF", "vfat": "FAT",
		 }

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Device Information"))
		self.skinName = ["SystemDevicesInfo", "About"]

		self.AboutText = ""
		self["AboutScrollLabel"] = ScrollLabel(self.AboutText)
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.populate2)
		self.populate()

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown,
				"left": self["AboutScrollLabel"].pageUp,
				"right": self["AboutScrollLabel"].pageDown,
			})

	def mountInfo(self, name, mountpoint, type, mountsep='\t', indent=''):
		if path.isdir(mountpoint):
			# Handle autofs "ghost" entries
			try:
				stat(mountpoint)
			except:
				return ""
			part = Partition(mountpoint)
			mounttotal = part.total()
			if mounttotal is None:
				mounttotal = -1
			else:
				mounttotal /= 10**6
			mountfree =  part.free()
			if mountfree is None:
				mountfree = -1
			else:
				mountfree /= 10**6
			return "%s%s%s%s%s\t%s%s\t%s" % (
					indent,
					name,
					mountsep,
					_("Size: "),
					sizeStr(mounttotal, _("unavailable")),
					_("Free: "),
					sizeStr(mountfree, _("full")),
					type
				)
		else:
			return ""

	def populate(self):
		scanning = _("Wait please while scanning for devices...")
		self["AboutScrollLabel"].setText(scanning)
		self.activityTimer.start(10)

	def populate2(self):
		self.activityTimer.stop()

		self.AboutText = _("Model:\t%s %s\n") % (getMachineBrand(), getMachineName())
		self.AboutText += "\n" + _("Detected NIMs:")

		nims = nimmanager.nimList()
		for count in range(len(nims)):
			if count < 4:
				self["Tuner" + str(count)] = StaticText(nims[count])
			else:
				self["Tuner" + str(count)] = StaticText("")
			self.AboutText +=  "\n" + nims[count]

		self.AboutText += "\n\n" + _("Detected HDDs and Volumes:")

		partitions = []
		f = open('/proc/partitions', 'r')
		for line in f.readlines():
			parts = line.strip().split()
			if not parts:
				continue
			device = parts[3]
			if device in partitions or not device[-1].isdigit():
				continue
			partitions.append(device)
		partitions.sort()

		mounts = getProcMounts()

		mountIndex = {}
		for m in mounts:
			x = m[0]
			if x.startswith('/dev/'):
				x = x[5:]
			mountIndex[x] = m

		self.mountinfo = []
		for hddtup in harddiskmanager.HDDList():
			hdd = hddtup[1]
			self.mountinfo.append("%s\t%s %s" % (hdd.device, hdd.model(), sizeStr(hdd.diskSize())))
			for part in [p for p in partitions
					if p.startswith(hdd.device)]:
				if part in mountIndex:
					mount = mountIndex[part]

					fs = mount[2]
					if fs:
						fs = fs.upper()
					else:
						fs = "Unknown"
					fsType = mount[2]
					if fsType in Devices.fsNameMap:
						fsType = Devices.fsNameMap[fsType]
					self.mountinfo.append(self.mountInfo(mount[0], mount[1], fsType, indent="    "))
				else:
					self.mountinfo.append("    " + part + '\t' + _('Not mounted'))
		if not self.mountinfo:
			self.mountinfo.append(_('none'))

		self.AboutText += '\n' + '\n'.join(self.mountinfo)

		self.AboutText += "\n\n" + _("Network Servers:")
		self.mountinfo = []
		for mount in [m for m in mounts
				if match(Devices.FSTABIPMATCH, m[0])]:
			self.mountinfo.append(self.mountInfo(mount[0], mount[1], mount[2].upper(), mountsep='\n\t'))

		for mountname in listdir('/media/autofs'):
			mountpoint = path.join('/media/autofs', mountname)
			self.mountinfo.append(self.mountInfo(mountpoint, mountpoint, 'AUTOFS', mountsep='\n\t'))
		for mountname in listdir('/media/upnp'):
			mountpoint = path.join('/media/upnp', mountname)
			if path.isdir(mountpoint) and not mountname.startswith('.'):
				self.mountinfo.append(mountpoint + '\t\t' + 'DLNA')

		if not self.mountinfo:
			self.mountinfo.append(_('none'))

		self.AboutText += '\n' + '\n'.join(self.mountinfo)
		self["AboutScrollLabel"].setText(self.AboutText)

class SystemMemoryInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Memory Information"))
		#self.skinName = ["SystemMemoryInfo", "About"]
		self.skinName = ["About"]

		self["AboutScrollLabel"] = ScrollLabel()

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"cancel": self.close,
			"ok": self.close,
		})

		out_lines = file("/proc/meminfo").readlines()
		self.AboutText = _("RAM") + '\n\n'
		RamTotal = "-"
		RamFree = "-"
		for lidx in range(len(out_lines) - 1):
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

	def Stage1Complete(self, result, retval, extra_args=None):
		flash = str(result).replace('\n', '')
		flash = flash.split()
		RamTotal = flash[1]
		RamFree = flash[3]

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
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Network Information"))
		self.skinName = ["SystemNetworkInfo", "About"]

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
				"down": self["AboutScrollLabel"].pageDown,
				"left": self["AboutScrollLabel"].pageUp,
				"right": self["AboutScrollLabel"].pageDown,
			})

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

		rx_bytes, tx_bytes = about.getIfTransferredData(self.iface)
		self.AboutText += "\n" + _("Bytes received:") + "\t" + rx_bytes + "\n"
		self.AboutText += _("Bytes sent:") + "\t" + tx_bytes + "\n"

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
							self["statuspic"].setPixmapNum(1)
							self["statuspic"].show()
						else:
							self.LinkState = True
							iNetwork.checkNetworkState(self.checkNetworkCB)
						self["AboutScrollLabel"].setText(self.AboutText)

	def exit(self):
		self.timer.stop()
		self.close(True)

	def updateStatusbar(self):
		self["IFtext"].setText(_("Network:"))
		self["IF"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		self["Statustext"].setText(_("Link:"))
		if iNetwork.isWirelessInterface(self.iface):
			try:
				self.iStatus.getDataForInterface(self.iface, self.getInfoCB)
			except:
				self["statuspic"].setPixmapNum(1)
				self["statuspic"].show()
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
					self["statuspic"].show()
				else:
					self["statuspic"].setPixmapNum(1)
					self["statuspic"].show()
			else:
				self["statuspic"].setPixmapNum(1)
				self["statuspic"].show()
		except:
			try:
				self["statuspic"].setPixmapNum(0)
			except:
				print "KeyError: statuspic"

	def createSummary(self):
		return AboutSummary


class AboutSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
		self["selected"] = StaticText("About")

