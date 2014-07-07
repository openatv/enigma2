from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Harddisk import Harddisk, Partition, harddiskmanager, getProcMounts
from Components.NimManager import nimmanager
from Components.About import about
from Components.config import config
from Components.ScrollLabel import ScrollLabel
from Components.Label import Label
from Components.Sources.List import List
from enigma import eTimer, getEnigmaVersionString, gFont
from boxbranding import getBoxType, getMachineBrand, getMachineName, getImageVersion, getImageBuild, getDriverDate

from Components.Pixmap import MultiPixmap
from Components.Network import iNetwork

from Tools.StbHardware import getFPVersion
from os import path, listdir, stat
from re import match

class AboutBase(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self.list = []
		self["list"] = List(self.list)

	@staticmethod
	def sizeStr(size, unknown=_("unavailable")):
		if float(size) / 2**20 >= 1:
			return str(round(float(size) / 2**20, 2)) + _("TB")
		if (float(size) / 2**10) >= 1:
			return str(round(float(size) / 2**10, 2)) + _("GB")
		if size >= 1:
			return str(size) + _("MB")
		return  unknown

	ENT_HEADING=0
	ENT_INFOLABEL=1
	ENT_INFO=2
	ENT_HEADINFOLABEL=3
	ENT_HEADINFO=4
	NENT=5

	@staticmethod
	def makeEmptyEntry():
		return ('',) * AboutBase.NENT

	@staticmethod
	def makeHeadingEntry(heading):
		l = [''] * AboutBase.NENT
		l[AboutBase.ENT_HEADING] = heading
		return tuple(l)

	@staticmethod
	def makeInfoEntry(label, info):
		l = [''] * AboutBase.NENT
		l[AboutBase.ENT_INFOLABEL:AboutBase.ENT_INFO+1] = label, info
		return tuple(l)

	@staticmethod
	def makeHeadingInfoEntry(label, info):
		l = [''] * AboutBase.NENT
		l[AboutBase.ENT_HEADINFOLABEL:AboutBase.ENT_HEADINFO+1] = label, info
		return tuple(l)

class About(AboutBase):
	def __init__(self, session):
		AboutBase.__init__(self, session)

		self.list.append(self.makeHeadingInfoEntry(_("Model:"), "%s %s" % (getMachineBrand(), getMachineName())))

		self.list.append(self.makeEmptyEntry())

		if path.exists('/proc/stb/info/chipset'):
			self.list.append(self.makeInfoEntry(_("Chipset:"), "BCM%s" % about.getChipSetString()))

		self.list.append(self.makeInfoEntry(_("CPU:"), about.getCPUString()))
		self.list.append(self.makeInfoEntry(_("Cores:"), str(about.getCpuCoresString())))

		string = getDriverDate()
		year = string[0:4]
		month = string[4:6]
		day = string[6:8]
		driversdate = '-'.join((year, month, day))
		self.list.append(self.makeInfoEntry(_("Drivers:"), driversdate))
		self.list.append(self.makeInfoEntry(_("Image:"), about.getImageVersionString()))
		self.list.append(self.makeInfoEntry(_("Kernel:"), about.getKernelVersionString()))
		self.list.append(self.makeInfoEntry(_("Oe-Core:"), about.getEnigmaVersionString()))

		fp_version = getFPVersion()
		if fp_version is not None:
			self.list.append(self.makeInfoEntry(_("Front Panel:"), "%d" % fp_version))

		self.list.append(self.makeEmptyEntry())
		self.list.append(self.makeInfoEntry(_("Last Upgrade:"), about.getLastUpdateString()))
		self.list.append(self.makeEmptyEntry())
		self.list.append(self.makeInfoEntry(_("WWW:"), about.getImageUrlString()))

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
			self.list.append(self.makeInfoEntry(_("System temperature:"), tempinfo.replace('\n', '') + mark + "C"))

		self["list"].updateList(self.list)

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.close,
				"ok": self.close,
			})

class Devices(AboutBase):

	ENT_HEADING=0
	ENT_INFOLABEL=1
	ENT_INFO=2
	ENT_HEADINFOLABEL=3
	ENT_HEADINFO=4
	ENT_HDDNAME=5
	ENT_HDDTYPE=6
	ENT_HDDSIZE=7
	ENT_FSNAME=8
	ENT_FSTYPE=9
	ENT_FSSIZE=10
	ENT_FSFREE=11
	ENT_FSWIDE=12
	ENT_FSWIDENET=13
	NENT=14

	@staticmethod
	def makeEmptyEntry():
		return ('',) * Devices.NENT

	@staticmethod
	def makeHeadingEntry(heading):
		l = [''] * Devices.NENT
		l[Devices.ENT_HEADING] = heading
		return tuple(l)

	@staticmethod
	def makeInfoEntry(label, info):
		l = [''] * Devices.NENT
		l[Devices.ENT_INFOLABEL:Devices.ENT_INFO+1] = label, info
		return tuple(l)

	@staticmethod
	def makeHeadingInfoEntry(label, info):
		l = [''] * Devices.NENT
		l[Devices.ENT_HEADINFOLABEL:Devices.ENT_HEADINFO+1] = label, info
		return tuple(l)

	@staticmethod
	def makeHDDEntry(name, type, size):
		l = [''] * Devices.NENT
		l[Devices.ENT_HDDNAME:Devices.ENT_HDDSIZE+1] = name, type, size
		return tuple(l)

	@staticmethod
	def makeFilesystemEntry(name, type, size, free):
		l = [''] * Devices.NENT
		l[Devices.ENT_FSNAME:Devices.ENT_FSFREE+1] = name, type, size, free
		return tuple(l)

	@staticmethod
	def makeWideFilesystemEntry(name):
		l = [''] * 14
		l[Devices.ENT_FSWIDE] = name
		return tuple(l)

	@staticmethod
	def makeWideNetworkEntry(name):
		l = [''] * 14
		l[Devices.ENT_FSWIDENET] = name
		return tuple(l)

	FSTABIPMATCH = "(//)?\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/"

       # Mapping fuseblk is a hack that only works if NTFS
       # is the only FUSE file system loaded.

	fsNameMap = { "fuseblk": "NTFS", "hfs": "HFS", "hfsplus": "HFS+",
			"iso9660": "ISO9660", "msdos" : "FAT",
			"ubifs": "UBIFS", "udf": "UDF", "vfat": "FAT",
		 }

	def __init__(self, session):
		AboutBase.__init__(self, session)

		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.populate2)
		self.populate()

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.close,
				"ok": self.close,
			})

	def mountInfo(self, name, mountpoint, type, twoLines=False, indent=''):
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
			sizeinfo = "%s%s" % (
					_("Size: "),
					self.sizeStr(mounttotal, _("unavailable"))
				)
			freeinfo = "%s%s" % (
					_("Free: "),
					self.sizeStr(mountfree, _("full"))
				)
			if twoLines:
				return (
					self.makeWideNetworkEntry(name),
					self.makeFilesystemEntry(None, type, sizeinfo, freeinfo)
				)
			else:
				return (self.makeFilesystemEntry(name, type, sizeinfo, freeinfo),)
		else:
			return (self.makeInfoEntry(name, ''),)

	def populate(self):
		scanning = _("Wait please while scanning for devices...")
		self.list.append(self.makeHeadingEntry(scanning))
		self["list"].updateList(self.list)
		self.activityTimer.start(10)

	def populate2(self):
		self.activityTimer.stop()

		self.list = []

		self.list.append(self.makeHeadingInfoEntry(_("Model:"), "%s %s" % (getMachineBrand(), getMachineName())))

		self.list.append(self.makeEmptyEntry())

		self.list.append(self.makeHeadingEntry(_("Detected NIMs"+":")))

		nims = nimmanager.nimList()
		for count in range(min(len(nims), 4)):
			self.list.append(self.makeInfoEntry(*nims[count].split(": ")))

		self.list.append(self.makeEmptyEntry())
		self.list.append(self.makeHeadingEntry(_("Detected HDDs and Volumes"+":")))

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
			self.mountinfo.append(self.makeHDDEntry(hdd.dev_path, hdd.model(), self.sizeStr(hdd.diskSize())))
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
					self.mountinfo += self.mountInfo(mount[0], mount[1], fsType)
				else:
					self.mountinfo.append(self.makeInfoEntry(part, _('Not mounted')))
		if not self.mountinfo:
			self.mountinfo.append(self.makeHDDEntry(_('none'), '', ''))

		self.list += self.mountinfo

		self.mountinfo = []
		self.list.append(self.makeEmptyEntry())
		self.list.append(self.makeHeadingEntry(_("Network Servers:")))
		for mount in [m for m in mounts
				if match(Devices.FSTABIPMATCH, m[0])]:
			self.mountinfo += self.mountInfo(mount[0], mount[1], mount[2].upper(), twoLines=True)

		for mountname in listdir('/media/autofs'):
			mountpoint = path.join('/media/autofs', mountname)
			self.mountinfo += self.mountInfo(mountpoint, mountpoint, 'AUTOFS', twoLines=True)
		for mountname in listdir('/media/upnp'):
			mountpoint = path.join('/media/upnp', mountname)
			if path.isdir(mountpoint) and not mountname.startswith('.'):
				self.mountinfo.append(self.makeWideNetworkEntry(mountpoint))
				self.mountinfo.append(self.makeFilesystemEntry(None, 'DLNA', None, None))

		if not self.mountinfo:
			self.mountinfo.append(self.makeWideFilesystemEntry(_('none')))

		self.list += self.mountinfo
		self["list"].updateList(self.list)

class SystemMemoryInfo(AboutBase):
	def __init__(self, session):
		AboutBase.__init__(self, session)

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"cancel": self.close,
			"ok": self.close,
		})

		out_lines = file("/proc/meminfo").readlines()
		self.list.append(self.makeHeadingEntry(_("RAM")))
		for lidx in range(len(out_lines) - 1):
			tstLine = out_lines[lidx].split()
			if "MemTotal:" in tstLine:
				MemTotal = out_lines[lidx].split()
				self.list.append(self.makeInfoEntry(_("Total Memory:"), MemTotal[1]))
			if "MemFree:" in tstLine:
				MemFree = out_lines[lidx].split()
				self.list.append(self.makeInfoEntry(_("Free Memory:"), MemFree[1]))
			if "Buffers:" in tstLine:
				Buffers = out_lines[lidx].split()
				self.list.append(self.makeInfoEntry(_("Buffers:"), Buffers[1]))
			if "Cached:" in tstLine:
				Cached = out_lines[lidx].split()
				self.list.append(self.makeInfoEntry(_("Cached:"), Cached[1]))
			if "SwapTotal:" in tstLine:
				SwapTotal = out_lines[lidx].split()
				self.list.append(self.makeInfoEntry(_("Total Swap:"), SwapTotal[1]))
			if "SwapFree:" in tstLine:
				SwapFree = out_lines[lidx].split()
				self.list.append(self.makeInfoEntry(_("Free Swap:"), SwapFree[1]))

		FlashTotal = "-"
		FlashFree = "-"
		mounts = getProcMounts()
		if mounts:
			part = Partition(mounts[0][1])
			FlashTotal = self.sizeStr(part.total() / 10**6, _("unavailable"))
			FlashFree = self.sizeStr(part.free() / 10**6, _("full"))

		self.list.append(self.makeEmptyEntry())
		self.list.append(self.makeHeadingEntry(_("FLASH")))
		self.list.append(self.makeInfoEntry(_("Total:"), FlashTotal))
		self.list.append(self.makeInfoEntry(_("Free:"), FlashFree))

		self["list"].updateList(self.list)

class SystemNetworkInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

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
