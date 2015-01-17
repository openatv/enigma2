from os import path, listdir, stat
from re import match

from boxbranding import getBoxType, getMachineBrand, getMachineName, getImageVersion, getImageBuild, getDriverDate
from enigma import eTimer, getEnigmaVersionString, gFont, eActionMap, eListbox
from Components.About import about
from Components.ActionMap import ActionMap
from Components.Harddisk import Partition, harddiskmanager, getProcMounts, getPartitionNames
from Components.Label import Label
from Components.Network import iNetwork
from Components.NimManager import nimmanager
from Components.Pixmap import MultiPixmap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.config import config, ConfigInteger
from Screen import Screen
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
from Tools.LoadPixmap import LoadPixmap
from Tools.StbHardware import getFPVersion
from keyids import KEYIDS


class AboutBase(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self.list = []
		self["list"] = List(self.list)

		self.setBindings()

		self["actions"] = ActionMap(
			["SetupActions", "ColorActions"],
			{
				"cancel": self.close,
				"ok": self.close,
			})

	@staticmethod
	def sizeStr(size, unknown=_("unavailable")):
		if float(size) / 2 ** 20 >= 1:
			return str(round(float(size) / 2 ** 20, 2)) + _("TB")
		if (float(size) / 2 ** 10) >= 1:
			return str(round(float(size) / 2 ** 10, 2)) + _("GB")
		if size >= 1:
			return str(size) + _("MB")
		return unknown

	ENT_HEADING = 0
	ENT_INFOLABEL = 1
	ENT_INFO = 2
	ENT_HEADINFOLABEL = 3
	ENT_HEADINFO = 4
	ENT_GW = 5
	ENT_GWDEST = 6
	ENT_IFTYPE = 7
	ENT_INETLABEL = 8
	ENT_ICONINFO = 9
	NENT = 10

	@staticmethod
	def makeEmptyEntry():
		l = [''] * AboutBase.NENT
		l[AboutBase.ENT_ICONINFO] = None
		return tuple(l)

	@staticmethod
	def makeHeadingEntry(heading):
		l = list(AboutBase.makeEmptyEntry())
		l[AboutBase.ENT_HEADING] = heading
		return tuple(l)

	@staticmethod
	def makeInfoEntry(label, info):
		l = list(AboutBase.makeEmptyEntry())
		l[AboutBase.ENT_INFOLABEL:AboutBase.ENT_INFO + 1] = label, info
		return tuple(l)

	@staticmethod
	def makeHeadingInfoEntry(label, info):
		l = list(AboutBase.makeEmptyEntry())
		l[AboutBase.ENT_HEADINFOLABEL:AboutBase.ENT_HEADINFO + 1] = label, info
		return tuple(l)

	def setBindings(self):
		actionMap = eActionMap.getInstance()
		actionMap.unbindNativeKey("ListboxActions", eListbox.moveUp)
		actionMap.unbindNativeKey("ListboxActions", eListbox.moveDown)
		actionMap.bindKey("keymap.xml", "generic", KEYIDS["KEY_UP"], 5, "ListboxActions", "pageUp")
		actionMap.bindKey("keymap.xml", "generic", KEYIDS["KEY_DOWN"], 5, "ListboxActions", "pageDown")
		self.onClose.append(self.restoreBindings)

	def restoreBindings(self):
		# After setBindings(), both KEY_UP and KEY_LEFT are bound to
		# pageUp, and KEY_DOWN, KEY_RIGHT are bound to pageDown,
		# so all four are unbound by the unbindNativeKey()s here
		# and all must be rebound to their defaults

		actionMap = eActionMap.getInstance()
		actionMap.unbindNativeKey("ListboxActions", eListbox.pageUp)
		actionMap.unbindNativeKey("ListboxActions", eListbox.pageDown)
		actionMap.bindKey("keymap.xml", "generic", KEYIDS["KEY_UP"], 5, "ListboxActions", "moveUp")
		actionMap.bindKey("keymap.xml", "generic", KEYIDS["KEY_DOWN"], 5, "ListboxActions", "moveDown")
		actionMap.bindKey("keymap.xml", "generic", KEYIDS["KEY_LEFT"], 5, "ListboxActions", "pageUp")
		actionMap.bindKey("keymap.xml", "generic", KEYIDS["KEY_RIGHT"], 5, "ListboxActions", "pageDown")


class About(AboutBase):
	def __init__(self, session):
		AboutBase.__init__(self, session)

		scanning = _("Wait please while loading information...")
		self.list.append(self.makeHeadingEntry(scanning))
		self["list"].updateList(self.list)

		about.getBootLoaderVersion(self.populate)

	def populate(self, bootLoaderInfo):
		self.list = []

		self.list.append(self.makeHeadingInfoEntry(_("Model:"), "%s %s" % (getMachineBrand(), getMachineName())))

		self.list.append(self.makeEmptyEntry())

		if path.exists('/proc/stb/info/chipset'):
			self.list.append(self.makeInfoEntry(_("Chipset:"), "BCM%s" % about.getChipSetString()))

		self.list.append(self.makeInfoEntry(_("CPU:"), about.getCPUString()))
		self.list.append(self.makeInfoEntry(_("CPU Speed:"), about.getCPUSpeedString()))
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

		self.list.append(self.makeInfoEntry(_("GStreamer:"), about.getGStreamerVersionString()))

		self["list"].updateList(self.list)

class Devices(AboutBase):

	ENT_HEADING = 0
	ENT_INFOLABEL = 1
	ENT_INFO = 2
	ENT_HEADINFOLABEL = 3
	ENT_HEADINFO = 4
	ENT_HDDNAME = 5
	ENT_HDDTYPE = 6
	ENT_HDDSIZE = 7
	ENT_FSNAME = 8
	ENT_FSTYPE = 9
	ENT_FSSIZE = 10
	ENT_FSFREE = 11
	ENT_FSWIDE = 12
	ENT_FSWIDENET = 13
	NENT = 14

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
		l[Devices.ENT_INFOLABEL:Devices.ENT_INFO + 1] = label, info
		return tuple(l)

	@staticmethod
	def makeHeadingInfoEntry(label, info):
		l = list(Devices.makeEmptyEntry())
		l[Devices.ENT_HEADINFOLABEL:Devices.ENT_HEADINFO + 1] = label, info
		return tuple(l)

	@staticmethod
	def makeHDDEntry(name, kind, size):
		l = list(Devices.makeEmptyEntry())
		l[Devices.ENT_HDDNAME:Devices.ENT_HDDSIZE + 1] = name, kind, size
		return tuple(l)

	@staticmethod
	def makeFilesystemEntry(name, kind, size, free):
		l = list(Devices.makeEmptyEntry())
		l[Devices.ENT_FSNAME:Devices.ENT_FSFREE + 1] = name, kind, size, free
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
	fsNameMap = {
				"fuseblk": "NTFS", "hfs": "HFS", "hfsplus": "HFS+",
				"iso9660": "ISO9660", "msdos": "FAT",
				"ubifs": "UBIFS", "udf": "UDF", "vfat": "FAT",
	}

	def __init__(self, session):
		AboutBase.__init__(self, session)

		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.populate2)
		self.populate()

	def mountInfo(self, name, mountpoint, kind, twoLines=False, indent=''):
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
				mounttotal /= 10 ** 6
			mountfree = part.free()
			if mountfree is None:
				mountfree = -1
			else:
				mountfree /= 10 ** 6
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
					self.makeFilesystemEntry(None, kind, sizeinfo, freeinfo)
				)
			else:
				return (self.makeFilesystemEntry(name, kind, sizeinfo, freeinfo),)
		else:
			return (self.makeInfoEntry(name, ''),)

	def populate(self):
		scanning = _("Please wait while scanning for devices...")
		self.list.append(self.makeHeadingEntry(scanning))
		self["list"].updateList(self.list)
		self.activityTimer.start(10, True)

	def populate2(self):

		self.list = []

		self.list.append(self.makeHeadingInfoEntry(_("Model:"), "%s %s" % (getMachineBrand(), getMachineName())))

		self.list.append(self.makeEmptyEntry())

		self.list.append(self.makeHeadingEntry(_("Detected Tuners:")))

		nims = nimmanager.nimList()
		for count in range(min(len(nims), 4)):
			self.list.append(self.makeInfoEntry(*nims[count].split(": ")))

		self.list.append(self.makeEmptyEntry())
		self.list.append(self.makeHeadingEntry(_("Detected HDDs and Volumes:")))

		partitions = getPartitionNames()
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
			for part in [p for p in partitions if p.startswith(hdd.device)]:
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
		for mount in [m for m in mounts if match(Devices.FSTABIPMATCH, m[0])]:
			self.mountinfo += self.mountInfo(mount[0], mount[1], mount[2].upper(), twoLines=True)

		try:
			for mountname in listdir('/media/autofs'):
				mountpoint = path.join('/media/autofs', mountname)
				self.mountinfo += self.mountInfo(mountpoint, mountpoint, 'AUTOFS', twoLines=True)
		except Exception, e:
			print "[Devices] find autofs mounts:", e

		try:
			for mountname in listdir('/media/upnp'):
				mountpoint = path.join('/media/upnp', mountname)
				if path.isdir(mountpoint) and not mountname.startswith('.'):
					self.mountinfo.append(self.makeWideNetworkEntry(mountpoint))
					self.mountinfo.append(self.makeFilesystemEntry(None, 'DLNA', None, None))
		except Exception, e:
			print "[Devices] find DLNA mounts:", e

		if not self.mountinfo:
			self.mountinfo.append(self.makeWideFilesystemEntry(_('none')))

		self.list += self.mountinfo
		self["list"].updateList(self.list)

class SystemMemoryInfo(AboutBase):
	def __init__(self, session):
		AboutBase.__init__(self, session)

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
			FlashTotal = self.sizeStr(part.total() / 10 ** 6, _("unavailable"))
			FlashFree = self.sizeStr(part.free() / 10 ** 6, _("full"))

		self.list.append(self.makeEmptyEntry())
		self.list.append(self.makeHeadingEntry(_("FLASH")))
		self.list.append(self.makeInfoEntry(_("Total:"), FlashTotal))
		self.list.append(self.makeInfoEntry(_("Free:"), FlashFree))

		self["list"].updateList(self.list)

config.misc.interface_info_poll = ConfigInteger(default=5, limits=(1, 3600))
config.misc.internet_info_poll = ConfigInteger(default=20, limits=(10, 3600))

class SystemNetworkInfo(AboutBase):

	@staticmethod
	def makeNetworkHeadEntry(label, info, statusLabel, icon):
		l = list(AboutBase.makeEmptyEntry())
		l[SystemNetworkInfo.ENT_HEADINFOLABEL] = label
		l[SystemNetworkInfo.ENT_IFTYPE] = info
		l[SystemNetworkInfo.ENT_INETLABEL] = statusLabel
		l[SystemNetworkInfo.ENT_ICONINFO] = icon
		return tuple(l)

	@staticmethod
	def makeGwInfoEntry(label, gw, dest):
		l = list(AboutBase.makeEmptyEntry())
		l[1] = label
		l[SystemNetworkInfo.ENT_GW:SystemNetworkInfo.ENT_GWDEST + 1] = gw, dest
		return tuple(l)

	@staticmethod
	def getPixmaps(pixmapNames):
		pixmaps = []
		for name in pixmapNames:
			try:
				pixmaps.append(LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, name)))
			except Exception, e:
				pixmaps.append(None)
				print "[SystemNetworkInfo]", e
		return tuple(pixmaps)

	class DisplayList:
		def __init__(self, screenList):
			self.screenList = screenList
			self.list = []
			self.pos = 0
			self.changed = set()

		def reset(self):
			self.pos = 0

		def add(self, data):
			if self.pos < len(self.list):
				if self.list[self.pos] != data:
					self.list[self.pos] = data
					self.changed.add(self.pos)
			else:
				self.list.append(data)
				self.changed.add(self.pos)
			self.pos += 1

		def update(self, row, data):
			if row <= len(self.list) and self.list[row] != data:
				self.list[row] = data
				self.changed.add(row)

		def updateScreen(self):
			if len(self.changed) <= len(self.list) / 4 and len(self.list) == len(self.screenList.list):
				for row in self.changed:
					self.screenList.modifyEntry(row, self.list[row])
			else:
				self.screenList.updateList(self.list)
			self.changed.clear()

		def nextPos(self):
			return self.pos

	def __init__(self, session):
		AboutBase.__init__(self, session)

		self["hostname"] = Label()
		self["inetstatus"] = MultiPixmap()

		self.list = self.DisplayList(self["list"])

		self.linkIcons = self.getPixmaps(("buttons/button_green_off.png", "buttons/button_green.png"))

		# self.config controls whether the items
		# "BSSID", "ESSID", "quality", "signal",
		# "bitrate", "enc" appear or not

		self.config = frozenset(("BSSID", "ESSID", "quality", "signal", "bitrate", "enc"))

		self.currIface = None
		self.iStatus = None
		self.allGateways = {}
		self.allTransferredData = {}
		self.linkState = {}
		self.iNetState = False

		self.ifacePollTime = config.misc.interface_info_poll.value * 1000
		self.inetPollTime = config.misc.internet_info_poll.value * 1000

		self.ifacePollTimer = eTimer()
		self.ifacePollTimer.timeout.get().append(self.updateLinks)
		self.inetPollTimer = eTimer()
		self.inetPollTimer.timeout.get().append(self.updateInternetStatus)

		self.updateLinks()
		self.updateInternetStatus()

		self.ifacePollTimer.start(self.ifacePollTime)
		self.inetPollTimer.start(self.inetPollTime)

	def updateLinks(self):
		self.allGateways = about.getGateways()
		self.allTransferredData = about.getAllIfTransferredData()

		anyLinkUp = any(self.linkState)

		self.list.reset()

		hostname = file('/proc/sys/kernel/hostname').read().strip()

		self["hostname"].setText(hostname)
		self["inetstatus"].setPixmapNum(self.iNetState)

		for ifaceName in [ifn for ifn in iNetwork.getInstalledAdapters() if ifn != 'lo']:
			self.addIfList(ifaceName)

		if anyLinkUp != any(self.linkState):
			self.updateInternetStatus(restart=True)

		self.list.updateScreen()

	def updateInternetStatus(self, restart=False):
		if (iNetwork.PingConsole is None or len(iNetwork.PingConsole.appContainers) == 0):
			iNetwork.checkNetworkState(self.checkNetworkCB)
		if(restart):
			self.inetPollTimer.start(self.inetPollTime)

	def addIfList(self, ifaceName):
		prevLinkState = ifaceName in self.linkState and self.linkState[ifaceName]
		self.linkState[ifaceName] = False

		iface = about.getIfConfig(ifaceName)
		if 'addr' in iface:
			self.linkState[ifaceName] = self.getLinkState(ifaceName, iface)
			self.list.add(self.makeNetworkHeadEntry(_("Network:"), iNetwork.getFriendlyAdapterName(ifaceName), _("Link:"), self.linkIcons[self.linkState[ifaceName]]))

			self.list.add(self.makeInfoEntry(_("IP:"), str(iface['addr'])))
			if 'netmask' in iface:
				self.list.add(self.makeInfoEntry(_("Netmask:"), str(iface['netmask'])))
			if 'brdaddr' in iface:
				self.list.add(self.makeInfoEntry(_("Broadcast:"), iface['brdaddr']))
			if 'hwaddr' in iface:
				self.list.add(self.makeInfoEntry(_("MAC:"), iface['hwaddr']))
			gateways = self.allGateways.get(ifaceName)
			if gateways:
				if len(gateways) == 1:
					gatewayLabel = _("Gateway:")
				elif len(gateways) > 1:
					gatewayLabel = _("Gateways")
					self.list.add(self.makeGwInfoEntry('', _("Gateway"), _("Destination")))
				for gw in gateways:
					if gw["destination"] == "0.0.0.0":
						gw["destination"] = "default"
					self.list.add(self.makeGwInfoEntry(gatewayLabel, gw["gateway"], gw["destination"]))
				gatewayLabel = None
			transferredData = self.allTransferredData.get(ifaceName)
			if transferredData:
				self.list.add(self.makeInfoEntry(_("Bytes in / out:"), ' / '.join([str(s) for s in transferredData])))

			self.loadWanIfStatusModule(ifaceName)

			if iNetwork.isWirelessInterface(ifaceName):
				self.addWirelessInfo(ifaceName)

	def loadWanIfStatusModule(self, ifaceName):
		if 'iStatus' not in globals() and iNetwork.isWirelessInterface(ifaceName):
			try:
				from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus

				self.iStatus = iStatus
			except:
				pass
			self.onClose.append(self.cleanup)

	def getLinkState(self, ifaceName, iface):
		return 'flags' in iface \
			and 'up' in iface['flags'] \
			and iface['flags']['up'] \
			and 'running' in iface['flags'] \
			and iface['flags']['running']

	def cleanup(self):
		self.ifacePollTimer.stop()
		self.inetPollTimer.stop()
		iNetwork.stopPingConsole()

	def addWirelessInfo(self, ifaceName):
		status = self.iStatus.getDataForInterface(ifaceName)
		if status:
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
				self.list.add(self.makeInfoEntry(_("Accesspoint:"), accesspoint))
			if "ESSID" in self.config:
				self.list.add(self.makeInfoEntry(_("SSID:"), essid))

			if "quality" in self.config:
				quality = status[ifaceName]["quality"]
				self.list.add(self.makeInfoEntry(_('Link Quality:'), quality.replace('/', ' / ')))

			if "bitrate" in self.config:
				if status[ifaceName]["bitrate"] == '0':
					bitrate = _("Unsupported")
				else:
					bitrate = str(status[ifaceName]["bitrate"])
				self.list.add(self.makeInfoEntry(_('Bitrate:'), str(bitrate)))

			if "signal" in self.config:
				signal = status[ifaceName]["signal"]
				self.list.add(self.makeInfoEntry(_('Signal Strength:'), str(signal)))

			if "enc" in self.config:
				if status[ifaceName]["encryption"] == "off":
					if accesspoint == "Not-Associated":
						encryption = _("Disabled")
					else:
						encryption = _("Unsupported")
				else:
					encryption = _("Enabled")
				self.list.add(self.makeInfoEntry(_('Encryption:'), str(encryption)))
			self.linkState[ifaceName] = status[ifaceName]["essid"] != "off" and status[ifaceName]["accesspoint"] not in [False, "Not-Associated"]
		else:
			self.linkState[ifaceName] = False

	def exit(self):
		self.close()

	def checkNetworkCB(self, data):
		self.iNetState = data <= 2
		self["inetstatus"].setPixmapNum(self.iNetState)

	def createSummary(self):
		return AboutSummary


class AboutSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["selected"] = StaticText("About")
