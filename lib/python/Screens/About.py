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

from Components.Network import iNetwork

from Tools.StbHardware import getFPVersion
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
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
	ENT_ICONINFO1=5
	ENT_GW=6
	ENT_GWDEST=7
	ENT_IFTYPE=8
	NENT=9

	@staticmethod
	def makeEmptyEntry():
		l = [''] * AboutBase.NENT
		l[AboutBase.ENT_ICONINFO1] = None
		return tuple(l)

	@staticmethod
	def makeHeadingEntry(heading):
		l = list(AboutBase.makeEmptyEntry())
		l[AboutBase.ENT_HEADING] = heading
		return tuple(l)

	@staticmethod
	def makeInfoEntry(label, info):
		l = list(AboutBase.makeEmptyEntry())
		l[AboutBase.ENT_INFOLABEL:AboutBase.ENT_INFO+1] = label, info
		return tuple(l)

	@staticmethod
	def makeHeadingInfoEntry(label, info):
		l = list(AboutBase.makeEmptyEntry())
		l[AboutBase.ENT_HEADINFOLABEL:AboutBase.ENT_HEADINFO+1] = label, info
		return tuple(l)

class About(AboutBase):
	def __init__(self, session):
		AboutBase.__init__(self, session)

		scanning = _("Wait please while loading information...")
		self.list.append(self.makeHeadingEntry(scanning))
		self["list"].updateList(self.list)

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.close,
				"ok": self.close,
			})

		about.getBootLoaderVersion(self.populate)

	def populate(self, bootLoaderInfo):
		self.list = []

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
		self.list.append(self.makeInfoEntry(_("Bootloader:"), bootLoaderInfo))

		fp_version = getFPVersion()
		if fp_version is not None:
			self.list.append(self.makeInfoEntry(_("Front Panel:"), "%d" % fp_version))

		self.list.append(self.makeEmptyEntry())
		self.list.append(self.makeInfoEntry(_("Last Upgrade:"), about.getLastUpdateString()))
		self.list.append(self.makeEmptyEntry())
		self.list.append(self.makeInfoEntry(_("WWW:"), about.getImageUrlString()))

		tempinfo = ""
		if path.exists('/proc/stb/sensors/temp0/value'):
			tempinfo = file('/proc/stb/sensors/temp0/value').read()
		elif path.exists('/proc/stb/fp/temp_sensor'):
			tempinfo = file('/proc/stb/fp/temp_sensor').read()
		if tempinfo and int(tempinfo.replace('\n', '')) > 0:
			mark = str('\xc2\xb0')
			self.list.append(self.makeInfoEntry(_("System temperature:"), tempinfo.replace('\n', '') + mark + "C"))

		self["list"].updateList(self.list)

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
		l = list(Devices.makeEmptyEntry())
		l[Devices.ENT_HEADING] = heading
		return tuple(l)

	@staticmethod
	def makeInfoEntry(label, info):
		l = list(Devices.makeEmptyEntry())
		l[Devices.ENT_INFOLABEL:Devices.ENT_INFO+1] = label, info
		return tuple(l)

	@staticmethod
	def makeHeadingInfoEntry(label, info):
		l = list(Devices.makeEmptyEntry())
		l[Devices.ENT_HEADINFOLABEL:Devices.ENT_HEADINFO+1] = label, info
		return tuple(l)

	@staticmethod
	def makeHDDEntry(name, type, size):
		l = list(Devices.makeEmptyEntry())
		l[Devices.ENT_HDDNAME:Devices.ENT_HDDSIZE+1] = name, type, size
		return tuple(l)

	@staticmethod
	def makeFilesystemEntry(name, type, size, free):
		l = list(Devices.makeEmptyEntry())
		l[Devices.ENT_FSNAME:Devices.ENT_FSFREE+1] = name, type, size, free
		return tuple(l)

	@staticmethod
	def makeWideFilesystemEntry(name):
		l = list(Devices.makeEmptyEntry())
		l[Devices.ENT_FSWIDE] = name
		return tuple(l)

	@staticmethod
	def makeWideNetworkEntry(name):
		l = list(Devices.makeEmptyEntry())
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

class SystemNetworkInfo(AboutBase):

	@staticmethod
	def makeNetworkHeadEntry(label, info, icon):
		l = list(AboutBase.makeEmptyEntry())
		l[SystemNetworkInfo.ENT_HEADINFOLABEL] = label
		l[SystemNetworkInfo.ENT_IFTYPE] = info
		l[SystemNetworkInfo.ENT_ICONINFO1] = icon
		return tuple(l)

	@staticmethod
	def makeGwInfoEntry(label, gw, dest):
		l = list(AboutBase.makeEmptyEntry())
		l[1] = label
		l[SystemNetworkInfo.ENT_GW:SystemNetworkInfo.ENT_GWDEST+1] = gw, dest
		return tuple(l)

	@staticmethod
	def getPixmap(pixmap):
		try:
			return LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, pixmap))
		except Exception, e:
			print "[SystemNetworkInfo]", e
		return None

	def __init__(self, session):
		Screen.__init__(self, session)

		self.list = []
		self["list"] = List(self.list)

		self.linkIcons = (self.getPixmap("buttons/button_green_off.png"), self.getPixmap("buttons/button_green.png"))

		# self.config controls whether the items
		# "BSSID", "ESSID", "quality", "signal",
		# "bitrate", "enc" appear or not

		self.config = frozenset(("BSSID", "ESSID", "quality",
					"signal", "bitrate", "enc"))

		self.updateLocs = {}

		self.currIfaceace = None
		self.iStatus = None
		self.allGateways = {}
		self.allTransferredData = {}

		self.ifScan = []

		self.createscreen()

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"cancel": self.close,
			"ok": self.close,
		})

	def createscreen(self):
		self.allGateways = about.getGateways()
		self.allTransferredData = about.getAllIfTransferredData()

		self.ifScan = [ifn for ifn in iNetwork.getInstalledAdapters()
					if ifn != 'lo']

		self.list = []

		hostname = file('/proc/sys/kernel/hostname').read().strip()
		self.list.append(self.makeHeadingInfoEntry(_("Hostname:"), hostname))

		self.createIfList()

	def createIfList(self):
		if self.ifScan:
			self.currIface = self.ifScan.pop(0)
		else:
			self["list"].updateList(self.list)
			self.currIface = None
			return

		ifaceName = self.currIface

		iface = about.getIfConfig(ifaceName)
		if iface.has_key('addr'):
			self.list.append(self.makeEmptyEntry())

			netHeadLabels = (_("Network:"), iNetwork.getFriendlyAdapterName(ifaceName))
			self.list.append(self.makeNetworkHeadEntry(*netHeadLabels + (self.linkIcons[int(False)],)))
			if ifaceName not in self.updateLocs:
				self.updateLocs[ifaceName] = {}
			self.updateLocs[ifaceName]["linkIcon"] = {"loc": len(self.list)-1, "labels": netHeadLabels}

			self.list.append(self.makeInfoEntry(_("IP:"), str(iface['addr'])))
			if iface.has_key('netmask'):
				self.list.append(self.makeInfoEntry(_("Netmask:"), str(iface['netmask'])))
			if 'brdaddr' in iface:
				self.list.append(self.makeInfoEntry(_("Broadcast:"), iface['brdaddr']))
			if iface.has_key('hwaddr'):
				self.list.append(self.makeInfoEntry(_("MAC:"), iface['hwaddr']))
			gateways = self.allGateways.get(ifaceName)
			if gateways:
				if len(gateways) == 1:
					gatewayLabel = _("Gateway:")
				elif len(gateways) > 1:
					gatewayLabel = _("Gateways:")
					self.list.append(self.makeGwInfoEntry('', _("Gateway"), _("Destination")))
				for gw in gateways:
					if gw["destination"] == "0.0.0.0":
						gw["destination"] = "default"
					self.list.append(self.makeGwInfoEntry(gatewayLabel, gw["gateway"], gw["destination"]))
				gatewayLabel = None
			transferredData = self.allTransferredData.get(ifaceName)
			if transferredData:
				self.list.append(self.makeInfoEntry(_("Bytes received:"), str(transferredData[0])))
				self.list.append(self.makeInfoEntry(_("Bytes sent:"), str(transferredData[1])))

			self.loadWanIfStatusModule(ifaceName)

			if iNetwork.isWirelessInterface(ifaceName):
				try:
					self.iStatus.getDataForInterface(self.currIface, self.getInfoCB)
				except:
					self.setLinkIcon(False)
					self.createIfList()
			else:
				iNetwork.getLinkState(self.currIface, self.getLinkStateCB)
		else:
			self.createIfList()

	def loadWanIfStatusModule(self, ifaceName):
		if 'iStatus' not in globals() and iNetwork.isWirelessInterface(ifaceName):
			try:
				from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus

				self.iStatus = iStatus
			except:
				pass
			self.onClose.append(self.cleanup)

	def cleanup(self):
		if self.iStatus:
			self.iStatus.stopWlanConsole()

	def getInfoCB(self, data, status):
		self.LinkState = None
		ifaceName = self.currIface
		if data and status is not None and iNetwork.isWirelessInterface(ifaceName):
			if status[ifaceName]["essid"] == "off":
				essid = _("No Connection")
			else:
				essid = status[ifaceName]["essid"]
			if status[ifaceName]["accesspoint"] == "Not-Associated":
				accesspoint = _("Not-Associated")
				essid = _("No Connection")
			else:
				accesspoint = status[ifaceName]["accesspoint"]
			if "BSSID" in self.config:
				self.list.append(self.makeInfoEntry(_("Accesspoint:"), accesspoint))
			if "ESSID" in self.config:
				self.list.append(self.makeInfoEntry(_("SSID:"), essid))

			if "quality" in self.config:
				quality = status[ifaceName]["quality"]
				self.list.append(self.makeInfoEntry(_('Link Quality:'), str(quality)))

			if "bitrate" in self.config:
				if status[ifaceName]["bitrate"] == '0':
					bitrate = _("Unsupported")
				else:
					bitrate = str(status[ifaceName]["bitrate"])
				self.list.append(self.makeInfoEntry(_('Bitrate:'), str(bitrate)))

			if "signal" in self.config:
				signal = status[ifaceName]["signal"]
				self.list.append(self.makeInfoEntry(_('Signal Strength:'), str(signal)))

			if "enc" in self.config:
				if status[ifaceName]["encryption"] == "off":
					if accesspoint == "Not-Associated":
						encryption = _("Disabled")
					else:
						encryption = _("Unsupported")
				else:
					encryption = _("Enabled")
				self.list.append(self.makeInfoEntry(_('Encryption:'), str(encryption)))

			if status[ifaceName]["essid"] == "off" or status[ifaceName]["accesspoint"] in [False, "Not-Associated"]:
				self.LinkState = False
				self.setLinkIcon(False)
				self.createIfList()
			else:
				self.LinkState = True
				iNetwork.checkNetworkState(self.checkNetworkCB)

	def exit(self):
		self.close()

	def getLinkStateCB(self, data):
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
			self.setLinkIcon(False)
			self.createIfList()

	def checkNetworkCB(self, data):
		try:
			if iNetwork.getAdapterAttribute(self.currIface, "up") is True:
				if self.LinkState is True:
					if data <= 2:
						self.setLinkIcon(True)
					else:
						self.setLinkIcon(False)
				else:
					self.setLinkIcon(False)
			else:
				self.setLinkIcon(False)
		except:
			self.setLinkIcon(False)
		self.createIfList()

	def setLinkIcon(self, on):
		loc = self.updateLocs[self.currIface]["linkIcon"]["loc"]
		labels = self.updateLocs[self.currIface]["linkIcon"]["labels"]
		self.list[loc] = self.makeNetworkHeadEntry(labels[0], labels[1], self.linkIcons[int(on)])

	def createSummary(self):
		return AboutSummary


class AboutSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
		self["selected"] = StaticText("About")
