from datetime import datetime
from glob import glob
from hashlib import md5
from os import mkdir, rename, rmdir, stat
from os.path import basename, exists, isdir, isfile, ismount, join as pathjoin
from struct import pack
from tempfile import mkdtemp

# NOTE: This module must not import from SystemInfo.py as this module is
# used to populate BoxInfo / SystemInfo and will create a boot loop!
#
from Components.Console import Console
from Tools.Directories import copyfile, fileReadLine, fileReadLines

MODULE_NAME = __name__.split(".")[-1]

MOUNT = "/bin/mount"
UMOUNT = "/bin/umount"
REMOVE = "/bin/rm"
PREFIX = "MultiBoot_"
COMMAND_FILE = "cmdline.txt"
DUAL_BOOT_FILE = "/dev/block/by-name/flag"
STARTUP_FILE = "STARTUP"
STARTUP_ONCE = "STARTUP_ONCE"
STARTUP_TEMPLATE = "STARTUP_*"
STARTUP_ANDROID = "STARTUP_ANDROID"
STARTUP_ANDROID_LINUXSE = "STARTUP_ANDROID_LINUXSE"
STARTUP_RECOVERY = "STARTUP_RECOVERY"
STARTUP_BOXMODE = "BOXMODE"  # This is known as bootCode in this code.


# STARTUP
# STARTUP_LINUX_1_BOXMODE_1
# boot emmcflash0.linuxkernel 'root=/dev/mmcblk0p3 rootsubdir=linuxrootfs1 kernel=/dev/mmcblk0p2 rw rootwait h7_4.boxmode=1'
# STARTUP_LINUX_2_BOXMODE_1
# boot emmcflash0.linuxkernel2 'root=/dev/mmcblk0p8 rootsubdir=linuxrootfs2 kernel=/dev/mmcblk0p4 rw rootwait h7_4.boxmode=1'
# STARTUP_LINUX_3_BOXMODE_1
# boot emmcflash0.linuxkernel3 'root=/dev/mmcblk0p8 rootsubdir=linuxrootfs3 kernel=/dev/mmcblk0p5 rw rootwait h7_4.boxmode=1'
# STARTUP_LINUX_4_BOXMODE_1
# boot emmcflash0.linuxkernel4 'root=/dev/mmcblk0p8 rootsubdir=linuxrootfs4 kernel=/dev/mmcblk0p6 rw rootwait h7_4.boxmode=1'
# STARTUP_LINUX_1_BOXMODE_12
# boot emmcflash0.linuxkernel 'brcm_cma=520M@248M brcm_cma=192M@768M root=/dev/mmcblk0p3 rootsubdir=linuxrootfs1 kernel=/dev/mmcblk0p2 rw rootwait h7_4.boxmode=12'
# STARTUP_LINUX_2_BOXMODE_12
# boot emmcflash0.linuxkernel2 'brcm_cma=520M@248M brcm_cma=192M@768M root=/dev/mmcblk0p8 rootsubdir=linuxrootfs2 kernel=/dev/mmcblk0p4 rw rootwait h7_4.boxmode=12'
# STARTUP_LINUX_3_BOXMODE_12
# boot emmcflash0.linuxkernel3 'brcm_cma=520M@248M brcm_cma=192M@768M root=/dev/mmcblk0p8 rootsubdir=linuxrootfs3 kernel=/dev/mmcblk0p5 rw rootwait h7_4.boxmode=12'
# STARTUP_LINUX_4_BOXMODE_12
# boot emmcflash0.linuxkernel4 'brcm_cma=520M@248M brcm_cma=192M@768M root=/dev/mmcblk0p8 rootsubdir=linuxrootfs4 kernel=/dev/mmcblk0p6 rw rootwait h7_4.boxmode=12'
#
# STARTUP
# STARTUP_1
# boot emmcflash0.kernel1: 'root=/dev/mmcblk0p5 rootwait rw rootflags=data=journal libata.force=1:3.0G,2:3.0G,3:3.0G coherent_poll=2M vmalloc=525m bmem=529m@491m bmem=608m@2464m'
# STARTUP_2
# boot emmcflash0.kernel2: 'root=/dev/mmcblk0p7 rootwait rw rootflags=data=journal libata.force=1:3.0G,2:3.0G,3:3.0G coherent_poll=2M vmalloc=525m bmem=529m@491m bmem=608m@2464m'
# STARTUP_3
# boot emmcflash0.kernel3: 'root=/dev/mmcblk0p9 rootwait rw rootflags=data=journal libata.force=1:3.0G,2:3.0G,3:3.0G coherent_poll=2M vmalloc=525m bmem=529m@491m bmem=608m@2464m'
#
# STARTUP (sfx6008)
# boot internalflash0.linuxkernel1 'ubi.mtd=12 root=ubi0:ubifs rootsubdir=linuxrootfs1 rootfstype=ubifs kernel=/dev/mtd10 userdataroot=/dev/mtd12 userdatasubdir=userdata1 mtdparts=hinand:1M(boot),1M(bootargs),1M(bootoptions),1M(baseparam),1M(pqparam),1M(logo),1M(deviceinfo),1M(softwareinfo),1M(loaderdb),16M(loader),6M(linuxkernel1),6M(linuxkernel2),-(userdata)'
#
# /sys/firmware/devicetree/base/chosen/bootargs
# console=ttyAMA0,115200 ubi.mtd=12 root=ubi0:ubifs rootsubdir=linuxrootfs1 rootfstype=ubifs kernel=/dev/mtd10 userdataroot=/dev/mtd12 userdatasubdir=userdata1 mtdparts=hinand:1M(boot),1M(bootargs),1M(bootoptions),1M(baseparam),1M(pqparam),1M(logo),1M(deviceinfo),1M(softwareinfo),1M(loaderdb),16M(loader),6M(linuxkernel1),6M(linuxkernel2),-(userdata) mem=512M mmz=ddr,0,0,160M vmalloc=500M MACHINEBUILD=sfx6008 OEM=octagon MODEL=sfx6008
#
# root=/dev/mmcblk0p3 rootsubdir=linuxrootfs1 kernel=/dev/mmcblk0p2 rw rootwait h7_4.boxmode=1
#
class MultiBootClass():
	def __init__(self):
		print("[MultiBoot] MultiBoot is initializing.")
		self.bootArgs = fileReadLine("/sys/firmware/devicetree/base/chosen/bootargs", default="", source=MODULE_NAME)
		self.loadMultiBoot()

	def loadMultiBoot(self):
		self.bootDevice, self.startupCmdLine = self.loadBootDevice()
		self.bootSlots, self.bootSlotsKeys = self.loadBootSlots()
		self.bootSlot, self.bootCode = self.loadCurrentSlotAndBootCodes()

	def loadBootDevice(self):
		for device in ("/dev/block/by-name/bootoptions", "/dev/mmcblk0p1", "/dev/mmcblk1p1", "/dev/mmcblk0p3", "/dev/mmcblk0p4", "/dev/mtdblock2"):
			bootDevice = None
			startupCmdLine = None
			if exists(device):
				tempDir = mkdtemp(prefix=PREFIX)
				Console().ePopen([MOUNT, MOUNT, device, tempDir])
				cmdFile = pathjoin(tempDir, COMMAND_FILE)
				startupFile = pathjoin(tempDir, STARTUP_FILE)
				if isfile(cmdFile) or isfile(startupFile):
					file = cmdFile if isfile(cmdFile) else startupFile
					startupCmdLine = " ".join(x.strip() for x in fileReadLines(file, default=[], source=MODULE_NAME) if x.strip())
					bootDevice = device
				Console().ePopen([UMOUNT, UMOUNT, tempDir])
				rmdir(tempDir)
			if bootDevice:
				print("[MultiBoot] Startup device identified as '%s'." % device)
			if startupCmdLine:
				print("[MultiBoot] Startup command line '%s'." % startupCmdLine)
				break
		return bootDevice, startupCmdLine

	def getParam(self, line, param):
		return line.replace("userdataroot", "rootuserdata").rsplit("%s=" % param, 1)[1].split(" ", 1)[0]

	def loadBootSlots(self):
		def saveKernel(bootSlots, slotCode, kernel):
			value = bootSlots[slotCode].get("kernel")
			if value is None:
				bootSlots[slotCode]["kernel"] = kernel
			elif value != kernel:
				print("[MultiBoot] Error: Inconsistent kernels found for slot '%s'!  ('%s' != '%s')" % (slotCode, value, kernel))

		bootSlots = {}
		bootSlotsKeys = []
		if self.bootDevice:
			tempDir = mkdtemp(prefix=PREFIX)
			Console().ePopen([MOUNT, MOUNT, self.bootDevice, tempDir])
			for path in sorted(glob(pathjoin(tempDir, STARTUP_TEMPLATE))):
				if "DISABLE" in path:
					# print("[MultiBoot] getBootSlots DEBUG: Skipping path='%s'." % path)
					continue
				file = basename(path)
				if file == STARTUP_ANDROID:
					bootCode = ""
					slotCode = "A"
				elif file == STARTUP_ANDROID_LINUXSE:
					bootCode = ""
					slotCode = "L"
				elif file == STARTUP_RECOVERY:
					bootCode = ""
					slotCode = "R"
				elif STARTUP_BOXMODE in file:
					parts = file.rsplit("_", 3)
					bootCode = parts[3]
					slotCode = parts[1]
				else:
					bootCode = ""
					slotCode = file.rsplit("_", 1)[1]
				# print("[MultiBoot] getBootSlots DEBUG: Path='%s', File='%s', SlotCode='%s'." % (path, file, slotCode))
				if slotCode:
					line = " ".join(x.strip() for x in fileReadLines(path, default=[], source=MODULE_NAME) if x.strip())
					if "root=" in line:
						# print("[MultiBoot] getBootSlots DEBUG: 'root=' found.")
						device = self.getParam(line, "root")
						if exists(device) or device == "ubi0:ubifs":
							if slotCode not in bootSlots:
								bootSlots[slotCode] = {}
							# print("[MultiBoot] getBootSlots DEBUG: Root dictionary entry '%s' created." % slotCode)
							value = bootSlots[slotCode].get("device")
							if value is None:
								bootSlots[slotCode]["device"] = device
							elif value != device:
								print("[MultiBoot] Error: Inconsistent root devices found for slot '%s'!  ('%s' != '%s')" % (slotCode, value, device))
							value = bootSlots[slotCode].get("bootCodes")
							if value is None:
								bootSlots[slotCode]["bootCodes"] = [bootCode]
							else:
								bootSlots[slotCode]["bootCodes"].append(bootCode)
							value = bootSlots[slotCode].get("startupfile")
							if value is None:
								bootSlots[slotCode]["startupfile"] = {}
							bootSlots[slotCode]["startupfile"][bootCode] = file
							value = bootSlots[slotCode].get("cmdline")
							if value is None:
								bootSlots[slotCode]["cmdline"] = {}
							bootSlots[slotCode]["cmdline"][bootCode] = line
							if "ubi.mtd=" in line:
								bootSlots[slotCode]["ubi"] = True
							if "rootsubdir" in line:
								bootSlots[slotCode]["kernel"] = self.getParam(line, "kernel")
								bootSlots[slotCode]["rootsubdir"] = self.getParam(line, "rootsubdir")
							elif "sda" in line:
								saveKernel(bootSlots, slotCode, "/dev/sda%s" % line.split("sda", 1)[1].split(" ", 1)[0])
							else:
								parts = device.split("p")
								saveKernel(bootSlots, slotCode, "%sp%s" % (parts[0], int(parts[1]) - 1))
					elif "bootcmd=" in line or " recovery " in line:
						# print("[MultiBoot] getBootSlots DEBUG: 'bootcmd=' or ' recovery 'text found.")
						if slotCode not in bootSlots:
							bootSlots[slotCode] = {}
						# print("[MultiBoot] getBootSlots DEBUG: Bootcmd/Recovery dictionary entry '%s' created." % slotCode)
						value = bootSlots[slotCode].get("bootCodes")
						if value is None:
							bootSlots[slotCode]["bootCodes"] = [bootCode]
						else:
							bootSlots[slotCode]["bootCodes"].append(bootCode)
						value = bootSlots[slotCode].get("startupfile")
						if value is None:
							bootSlots[slotCode]["startupfile"] = {}
						bootSlots[slotCode]["startupfile"][bootCode] = file
						value = bootSlots[slotCode].get("cmdline")
						if value is None:
							bootSlots[slotCode]["cmdline"] = {}
						bootSlots[slotCode]["cmdline"][bootCode] = line
					else:
						print("[MultiBoot] Error: Slot can't be identified.  (%s)" % line)
				else:
					print("[MultiBoot] Error: Slot code can not be determined from '%s'!" % file)
			Console().ePopen([UMOUNT, UMOUNT, tempDir])
			rmdir(tempDir)
			bootSlotsKeys = sorted(bootSlots.keys())
			# for slotCode in bootSlotsKeys:
			# 	print("[MultiBoot] getBootSlots DEBUG: Boot slot '%s': %s" % (slotCode, bootSlots[slotCode]))
		return bootSlots, bootSlotsKeys

	def loadCurrentSlotAndBootCodes(self):
		if self.bootSlots and self.bootSlotsKeys:
			for slotCode in self.bootSlotsKeys:
				cmdLines = self.bootSlots[slotCode]["cmdline"]
				bootCodes = sorted(self.bootSlots[slotCode]["cmdline"].keys())
				for bootCode in bootCodes:
					if cmdLines[bootCode] == self.startupCmdLine:
						# print("[MultiBoot] getCurrentSlotAndBootCodes DEBUG: Slot code='%s', bootCode='%s'." % (slotCode, bootCode))
						return slotCode, bootCode
		return None, ""

	def canMultiBoot(self):
		return self.bootSlots != {}

	def getBootDevice(self):
		return self.bootDevice

	def getBootSlots(self):
		return self.bootSlots

	def getCurrentSlotAndBootCodes(self):
		return self.bootSlot, self.bootCode

	def getCurrentSlotCode(self):
		return self.bootSlot

	def getCurrentBootMode(self):
		return self.bootCode

	def hasRecovery(self):
		return "R" in self.bootSlots

	def getBootCodeDescription(self, bootCode=None):
		bootCodeDescriptions = {
			"": _("Normal: No boot modes required."),
			"1": _("Mode 1: Supports Kodi but PiP may not work"),
			"12": _("Mode 12: Supports PiP but Kodi may not work")
		}
		if bootCode is None:
			return bootCodeDescriptions
		return bootCodeDescriptions.get(bootCode, "")

	def getStartupFile(self, slotCode=None):
		slotCode = slotCode if slotCode in self.bootSlots else self.bootSlot
		return self.bootSlots[slotCode]["startupfile"][self.bootCode]

	def hasRootSubdir(self, slotCode=None):
		slotCode = slotCode if slotCode in self.bootSlots else self.bootSlot
		return "rootsubdir" in self.bootSlots[slotCode]

	def getSlotImageList(self, callback):
		self.imageList = {}
		if self.bootSlots:
			self.callback = callback
			self.tempDir = mkdtemp(prefix=PREFIX)
			self.slotCodes = self.bootSlotsKeys[:]
			self.findSlot()
		else:
			callback(self.imageList)

	def findSlot(self):  # Part of getSlotImageList().
		if self.slotCodes:
			self.slotCode = self.slotCodes.pop(0)
			hasMultiBootMTD = self.bootSlots[self.slotCode].get("ubi", False)
			self.imageList[self.slotCode] = {
				"ubi": hasMultiBootMTD,
				"bootCodes": self.bootSlots[self.slotCode].get("bootCodes", [""])
			}
			if self.slotCode == "A":
				# print("[MultiBoot] Slot '%s': Found an Android slot." % self.slotCode)
				self.imageList[self.slotCode]["imagename"] = _("Android")
				self.imageList[self.slotCode]["status"] = "android"
				self.findSlot()
			elif self.slotCode == "L":
				# print("[MultiBoot] Slot '%s': Found an Android Linux SE slot." % self.slotCode)
				self.imageList[self.slotCode]["imagename"] = _("Android Linux SE")
				self.imageList[self.slotCode]["status"] = "androidlinuxse"
				self.findSlot()
			elif self.slotCode == "R":
				# print("[MultiBoot] Slot '%s': Found a Recovery slot." % self.slotCode)
				self.imageList[self.slotCode]["imagename"] = _("Recovery")
				self.imageList[self.slotCode]["status"] = "recovery"
				self.findSlot()
			elif self.bootSlots[self.slotCode].get("device"):
				self.device = self.bootSlots[self.slotCode]["device"]
				# print("[MultiBoot] DEBUG: Analyzing slot='%s' (%s)." % (self.slotCode, self.device))
				if hasMultiBootMTD:
					Console().ePopen([MOUNT, MOUNT, "-t", "ubifs", self.device, self.tempDir], self.analyzeSlot)
				else:
					Console().ePopen([MOUNT, MOUNT, self.device, self.tempDir], self.analyzeSlot)
			else:
				# print("[MultiBoot] Slot '%s': Found an unexpected/ill-defined slot." % self.slotCode)
				self.imageList[self.slotCode]["imagename"] = _("Unknown")
				self.imageList[self.slotCode]["status"] = "unknown"
				self.findSlot()
		else:
			rmdir(self.tempDir)
			# for slotCode in sorted(self.imageList.keys()):
			# 	print("[MultiBoot] findSlot DEBUG: Image slot '%s': %s" % (slotCode, self.imageList[slotCode]))
			self.callback(self.imageList)

	def analyzeSlot(self, data, retVal, extraArgs):  # Part of getSlotImageList().
		if retVal:
			# print("[MultiBoot] analyzeSlot Error %d: Unable to mount slot '%s' (%s)!" % (retVal, self.slotCode, self.device))
			self.imageList[self.slotCode]["imagename"] = _("Inaccessible")
			self.imageList[self.slotCode]["status"] = "unknown"
		else:
			rootDir = self.bootSlots[self.slotCode].get("rootsubdir")
			imageDir = pathjoin(self.tempDir, rootDir) if rootDir else self.tempDir
			infoFile = pathjoin(imageDir, "usr/lib/enigma.info")
			if isfile(infoFile):
				# print("[MultiBoot] Slot '%s' (%s%s): Found an enigma information file." % (self.slotCode, self.device, " - %s" % rootDir if rootDir else ""))
				info = self.readSlotInfo(infoFile)
				compileDate = str(info.get("compiledate"))
				revision = info.get("imgrevision")
				if info.get("distro") == "openvix":
					revision = ".%03d" % revision if revision else ""
				else:
					revision = " %s" % revision
				revision = "" if revision.strip() == compileDate else revision
				compileDate = "%s-%s-%s" % (compileDate[0:4], compileDate[4:6], compileDate[6:8])
				self.imageList[self.slotCode]["imagename"] = "%s %s%s (%s)" % (info.get("displaydistro", info.get("distro")), info.get("imgversion"), revision, compileDate)
				self.imageList[self.slotCode]["status"] = "active"
			elif isfile(pathjoin(imageDir, "usr/bin/enigma2")):
				# print("[MultiBoot] Slot '%s' (%s%s): Found an enigma2 binary file." % (self.slotCode, self.device, " - %s" % rootDir if rootDir else ""))
				info = self.deriveSlotInfo(imageDir)
				compileDate = str(info.get("compiledate"))
				compileDate = "%s-%s-%s" % (compileDate[0:4], compileDate[4:6], compileDate[6:8])
				self.imageList[self.slotCode]["imagename"] = "%s %s (%s)" % (info.get("displaydistro", info.get("distro")), info.get("imgversion"), compileDate)
				self.imageList[self.slotCode]["status"] = "active"
			else:
				# print("[MultiBoot] Slot '%s' (%s%s): Found no enigma files." % (self.slotCode, self.device, " - %s" % rootDir if rootDir else ""))
				self.imageList[self.slotCode]["imagename"] = _("Empty")
				self.imageList[self.slotCode]["status"] = "empty"
		if ismount(self.tempDir):
			Console().ePopen([UMOUNT, UMOUNT, self.tempDir], self.finishSlot)
		else:
			self.findSlot()

	def finishSlot(self, data, retVal, extraArgs):  # Part of getSlotImageList().
		if retVal:
			print("[MultiBoot] finishSlot Error %d: Unable to unmount slot '%s' (%s)!" % (retVal, self.slotCode, self.device))
		else:
			self.findSlot()

	def readSlotInfo(self, path):  # Part of analyzeSlot() within getSlotImageList().
		info = {}
		lines = fileReadLines(path, source=MODULE_NAME)
		if lines:
			if self.checkChecksum(lines):
				print("[MultiBoot] WARNING: Enigma information file found but checksum is incorrect!")
			for line in lines:
				if line.startswith("#") or line.strip() == "":
					continue
				if "=" in line:
					item, value = [x.strip() for x in line.split("=", 1)]
					if item:
						info[item] = self.processValue(value)
		lines = fileReadLines(path.replace(".info", ".conf"), source=MODULE_NAME)
		if lines:
			for line in lines:
				if line.startswith("#") or line.strip() == "":
					continue
				if "=" in line:
					item, value = [x.strip() for x in line.split("=", 1)]
					if item:
						if item in info:
							print("[MultiBoot] Note: Enigma information value '%s' with value '%s' being overridden to '%s'." % (item, info[item], value))
						info[item] = self.processValue(value)
		return info

	def checkChecksum(self, lines):  # Part of readSlotInfo() within analyzeSlot() within getSlotImageList().
		value = "Undefined!"
		data = []
		for line in lines:
			if line.startswith("checksum"):
				item, value = [x.strip() for x in line.split("=", 1)]
			else:
				data.append(line)
		data.append("")
		result = md5(bytearray("\n".join(data), "UTF-8", errors="ignore")).hexdigest()
		return value != result

	def processValue(self, value):  # Part of readSlotInfo() within analyzeSlot() within getSlotImageList().
		valueTest = value.upper() if value else ""
		if value is None:
			pass
		elif value.startswith("\"") or value.startswith("'") and value.endswith(value[0]):
			value = value[1:-1]
		elif value.startswith("(") and value.endswith(")"):
			data = []
			for item in [x.strip() for x in value[1:-1].split(",")]:
				data.append(self.processValue(item))
			value = tuple(data)
		elif value.startswith("[") and value.endswith("]"):
			data = []
			for item in [x.strip() for x in value[1:-1].split(",")]:
				data.append(self.processValue(item))
			value = list(data)
		elif valueTest == "NONE":
			value = None
		elif valueTest in ("FALSE", "NO", "OFF", "DISABLED"):
			value = False
		elif valueTest in ("TRUE", "YES", "ON", "ENABLED"):
			value = True
		elif value.isdigit() or (value[0:1] == "-" and value[1:].isdigit()):
			value = int(value)
		elif valueTest.startswith("0X"):
			try:
				value = int(value, 16)
			except ValueError:
				pass
		elif valueTest.startswith("0O"):
			try:
				value = int(value, 8)
			except ValueError:
				pass
		elif valueTest.startswith("0B"):
			try:
				value = int(value, 2)
			except ValueError:
				pass
		else:
			try:
				value = float(value)
			except ValueError:
				pass
		return value

	def deriveSlotInfo(self, path):  # Part of analyzeSlot() within getSlotImageList().
		info = {}
		try:
			date = datetime.fromtimestamp(stat(pathjoin(path, "var/lib/opkg/status")).st_mtime).strftime("%Y%m%d")
			if date.startswith("1970"):
				date = datetime.fromtimestamp(stat(pathjoin(path, "usr/share/bootlogo.mvi")).st_mtime).strftime("%Y%m%d")
			date = max(date, datetime.fromtimestamp(stat(pathjoin(path, "usr/bin/enigma2")).st_mtime).strftime("%Y%m%d"))
		except OSError as err:
			date = "00000000"
		info["compiledate"] = date
		lines = fileReadLines(pathjoin(path, "etc/issue"), source=MODULE_NAME)
		if lines:
			data = lines[-2].strip()[:-6].split()
			info["distro"] = " ".join(data[:-1])
			info["displaydistro"] = {
				"beyonwiz": "Beyonwiz",
				"blackhole": "Black Hole",
				"egami": "EGAMI",
				"openatv": "openATV",
				"openbh": "OpenBH",
				"opendroid": "OpenDroid",
				"openeight": "OpenEight",
				"openhdf": "OpenHDF",
				"opennfr": "OpenNFR",
				"openpli": "OpenPLi",
				"openspa": "OpenSpa",
				"openvision": "Open Vision",
				"openvix": "OpenViX",
				"sif": "Sif",
				"teamblue": "teamBlue",
				"vti": "VTi"
			}.get(info["distro"].lower(), info["distro"].capitalize())
			info["imgversion"] = data[-1]
		else:
			info["distro"] = "Enigma2"
			info["displaydistro"] = "Enigma2"
			info["imgversion"] = "???"
		return info

	def activateSlot(self, slotCode, bootCode, callback):
		self.slotCode = slotCode
		self.bootCode = bootCode
		self.callback = callback
		self.tempDir = mkdtemp(prefix=PREFIX)
		Console().ePopen([MOUNT, MOUNT, self.bootDevice, self.tempDir], self.bootDeviceMounted)

	def bootDeviceMounted(self, data, retVal, extraArgs):  # Part of activateSlot().
		if retVal:
			print("[MultiBoot] bootDeviceMounted Error %d: Unable to mount boot device '%s'!" % (retVal, self.bootDevice))
			self.callback(1)
		else:
			bootSlot = self.bootSlots[self.slotCode]
			startup = bootSlot["startupfile"][self.bootCode]
			target = STARTUP_ONCE if startup == STARTUP_RECOVERY else STARTUP_FILE
			copyfile(pathjoin(self.tempDir, startup), pathjoin(self.tempDir, target))
			if exists(DUAL_BOOT_FILE):
				slot = self.slotCode if self.slotCode.isdecimal() else "0"
				with open(DUAL_BOOT_FILE, "wb") as fd:
					fd.write(pack("B", int(slot)))
			# print("[MultiBoot] DEBUG: Installing '%s' as '%s'." % (startup, target))
			Console().ePopen([UMOUNT, UMOUNT, self.tempDir], self.bootDeviceUnmounted)

	def bootDeviceUnmounted(self, data, retVal, extraArgs):  # Part of activateSlot().
		if retVal:
			print("[MultiBoot] bootDeviceUnmounted Error %d: Unable to mount boot device '%s'!" % (retVal, self.bootDevice))
			self.callback(2)
		else:
			rmdir(self.tempDir)
			self.callback(0)

	def emptySlot(self, slotCode, callback):
		self.manageSlot(slotCode, callback, self.hideSlot)

	def restoreSlot(self, slotCode, callback):
		self.manageSlot(slotCode, callback, self.revealSlot)

	def manageSlot(self, slotCode, callback, method):  # Part of emptySlot() and restoreSlot().
		if self.bootSlots:
			self.slotCode = slotCode
			self.callback = callback
			self.device = self.bootSlots[self.slotCode]["device"]
			self.tempDir = mkdtemp(prefix=PREFIX)
			if self.bootSlots[self.slotCode].get("ubi", False):
				Console().ePopen([MOUNT, MOUNT, "-t", "ubifs", self.device, self.tempDir], method)
			else:
				Console().ePopen([MOUNT, MOUNT, self.device, self.tempDir], method)
		else:
			self.callback(1)

	def hideSlot(self, data, retVal, extraArgs):  # Part of emptySlot().
		if retVal:
			print("[MultiBoot] hideSlot Error %d: Unable to mount slot '%s' (%s)!" % (retVal, self.slotCode, self.device))
			self.callback(2)
		else:
			rootDir = self.bootSlots[self.slotCode].get("rootsubdir")
			imageDir = pathjoin(self.tempDir, rootDir) if rootDir else self.tempDir
			if self.bootSlots[self.slotCode].get("ubi", False):
				try:
					if isfile(pathjoin(imageDir, "usr/bin/enigma2")):
						Console().ePopen([REMOVE, REMOVE, "-rf", imageDir])
					mkdir(imageDir)
				except OSError as err:
					print("[MultiBoot] hideSlot Error %d: Unable to wipe all files in slot '%s' (%s)!  (%s)" % (err.errno, self.slotCode, self.device, err.strerror))
			else:
				enigmaFile = ""  # This is in case the first pathjoin fails.
				try:
					enigmaFile = pathjoin(imageDir, "usr/bin/enigma2")
					if isfile(enigmaFile):
						rename(enigmaFile, "%sx.bin" % enigmaFile)
					enigmaFile = pathjoin(imageDir, "usr/lib/enigma.info")
					if isfile(enigmaFile):
						rename(enigmaFile, "%sx" % enigmaFile)
					enigmaFile = pathjoin(imageDir, "etc")
					if isdir(enigmaFile):
						rename(enigmaFile, "%sx" % enigmaFile)
				except OSError as err:
					print("[MultiBoot] hideSlot Error %d: Unable to hide item '%s' in slot '%s' (%s)!  (%s)" % (err.errno, enigmaFile, self.slotCode, self.device, err.strerror))
			Console().ePopen([UMOUNT, UMOUNT, self.tempDir], self.cleanUpSlot)

	def revealSlot(self, data, retVal, extraArgs):  # Part of restoreSlot().
		if retVal:
			print("[MultiBoot] revealSlot Error %d: Unable to mount slot '%s' (%s)!" % (retVal, self.slotCode, self.device))
			self.callback(2)
		else:
			rootDir = self.bootSlots[self.slotCode].get("rootsubdir")
			imageDir = pathjoin(self.tempDir, rootDir) if rootDir else self.tempDir
			enigmaFile = ""  # This is in case the first pathjoin fails.
			try:
				enigmaFile = pathjoin(imageDir, "usr/bin/enigma2")
				hiddenFile = "%sx.bin" % enigmaFile
				if isfile(hiddenFile):
					rename(hiddenFile, enigmaFile)
				enigmaFile = pathjoin(imageDir, "usr/lib/enigma.info")
				hiddenFile = "%sx" % enigmaFile
				if isfile(hiddenFile):
					rename(hiddenFile, enigmaFile)
				enigmaFile = pathjoin(imageDir, "etc")
				hiddenFile = "%sx" % enigmaFile
				if isdir(hiddenFile):
					rename(hiddenFile, enigmaFile)
			except OSError as err:
				print("[MultiBoot] revealSlot Error %d: Unable to reveal item '%s' in slot '%s' (%s)!  (%s)" % (err.errno, enigmaFile, self.slotCode, self.device, err.strerror))
			Console().ePopen([UMOUNT, UMOUNT, self.tempDir], self.cleanUpSlot)

	def cleanUpSlot(self, data, retVal, extraArgs):  # Part of emptySlot() and restoreSlot().
		if retVal:
			print("[MultiBoot] emptySlotCleanUp Error %d: Unable to unmount slot '%s' (%s)!" % (retVal, self.slotCode, self.device))
			self.callback(3)
		else:
			rmdir(self.tempDir)
			self.callback(0)


MultiBoot = MultiBootClass()
