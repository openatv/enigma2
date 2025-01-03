from datetime import datetime
from glob import glob
from hashlib import md5
from os import listdir, mkdir, rename, rmdir, stat
from os.path import basename, exists, isdir, isfile, ismount, join as pathjoin
from struct import calcsize, pack, unpack, error
from tempfile import mkdtemp

# NOTE: This module must not import from SystemInfo.py as this module is
# used to populate BoxInfo / SystemInfo and will create a boot loop!
#
from Components.Console import Console
from Tools.Directories import SCOPE_CONFIG, copyfile, fileHas, fileReadLine, fileReadLines, resolveFilename

MODULE_NAME = __name__.split(".")[-1]

MOUNT = "/bin/mount"
UMOUNT = "/bin/umount"
REMOVE = "/bin/rm"
PREFIX = "MultiBoot_"
COMMAND_FILE = "cmdline.txt"
DUAL_BOOT_FILE = "/dev/block/by-name/flag"
DREAM_BOOT_FILE = "/data/bootconfig.txt"
STARTUP_FILE = "STARTUP"
STARTUP_ONCE = "STARTUP_ONCE"
STARTUP_TEMPLATE = "STARTUP_*"
STARTUP_ANDROID = "STARTUP_ANDROID"
STARTUP_ANDROID_LINUXSE = "STARTUP_ANDROID_LINUXSE"
STARTUP_RECOVERY = "STARTUP_RECOVERY"
STARTUP_BOXMODE = "BOXMODE"  # This is known as bootCode in this code.
BOOT_DEVICE_LIST = ("/dev/mmcblk0p1", "/dev/mmcblk1p1", "/dev/mmcblk0p3", "/dev/mmcblk0p4", "/dev/mtdblock2", "/dev/block/by-name/bootoptions")
BOOT_DEVICE_LIST_VUPLUS = ("/dev/mmcblk0p4", "/dev/mmcblk0p7", "/dev/mmcblk0p9")  # Kexec kernel Vu+ MultiBoot.


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
		lines = []
		lines = fileReadLines(resolveFilename(SCOPE_CONFIG, "settings"), default=lines, source=MODULE_NAME)
		self.debugMode = "config.crash.debugMultiBoot=True" in lines
		self.bootArgs = fileReadLine("/sys/firmware/devicetree/base/chosen/bootargs", default="", source=MODULE_NAME)
		self.console = Console()
		self.loadMultiBoot()

	def loadMultiBoot(self):
		self.bootDevice, self.startupCmdLine = self.loadBootDevice()
		self.bootSlots, self.bootSlotsKeys = self.loadBootSlots()
		if exists(DUAL_BOOT_FILE):
			try:
				with open(DUAL_BOOT_FILE, "rb") as fd:
					structFormat = "B"
					flag = fd.read(calcsize(structFormat))
					slot = unpack(structFormat, flag)
					self.bootSlot = str(slot[0])
					self.bootCode = ""
			except OSError as err:
				print(f"MultiBoot] Error {err.errno}: Unable to read dual boot file '{DUAL_BOOT_FILE}'!  ({err.strerror})")
				self.bootSlot = None
				self.bootCode = ""
			except error as err:
				print(f"MultiBoot] Unable to interpret dual boot file '{DUAL_BOOT_FILE}' data!  ({err})")
		else:
			self.bootSlot, self.bootCode = self.loadCurrentSlotAndBootCodes()
		if exists(DREAM_BOOT_FILE):
			with open(DREAM_BOOT_FILE, "r") as fd:
				lines = fd.readlines()
				for line in lines:
					if line.startswith("default="):
						self.bootSlot = str(int(line.strip().split("=")[1]) + 1)

	def loadBootDevice(self):
		bootDeviceList = BOOT_DEVICE_LIST_VUPLUS if fileHas("/proc/cmdline", "kexec=1") else BOOT_DEVICE_LIST
		for device in bootDeviceList:
			bootDevice = None
			startupCmdLine = None
			if exists(device):
				tempDir = mkdtemp(prefix=PREFIX)
				self.console.ePopen([MOUNT, MOUNT, device, tempDir])
				cmdFile = pathjoin(tempDir, COMMAND_FILE)
				startupFile = pathjoin(tempDir, STARTUP_FILE)
				if isfile(cmdFile) or isfile(startupFile):
					file = cmdFile if isfile(cmdFile) else startupFile
					startupCmdLine = " ".join(x.strip() for x in fileReadLines(file, default=[], source=MODULE_NAME) if x.strip())
					bootDevice = device
				self.console.ePopen([UMOUNT, UMOUNT, tempDir])
				rmdir(tempDir)
			if bootDevice:
				print(f"[MultiBoot] Startup device identified as '{device}'.")
			if startupCmdLine:
				print(f"[MultiBoot] Startup command line '{startupCmdLine}'.")
				break
		return bootDevice, startupCmdLine

	def loadBootSlots(self):
		def saveKernel(bootSlots, slotCode, kernel):
			value = bootSlots[slotCode].get("kernel")
			if value is None:
				bootSlots[slotCode]["kernel"] = kernel
			elif value != kernel:
				print(f"[MultiBoot] Error: Inconsistent kernels found for slot '{slotCode}'!  ('{value}' != '{kernel}')")

		bootSlots = {}
		bootSlotsKeys = []
		if self.bootDevice:
			tempDir = mkdtemp(prefix=PREFIX)
			self.console.ePopen([MOUNT, MOUNT, self.bootDevice, tempDir])
			for path in sorted(glob(pathjoin(tempDir, STARTUP_TEMPLATE))):
				file = basename(path)
				if "DISABLE" in file:
					if self.debugMode:
						print(f"[MultiBoot] Skipping disabled boot file '{file}'.")
					continue
				elif file == STARTUP_ANDROID:
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
				if self.debugMode:
					print(f"[MultiBoot] Processing boot file '{file}' as slot code '{slotCode if slotCode else ""}', boot mode '{bootCode if bootCode else ""}'.")
				if slotCode:
					line = " ".join(x.strip() for x in fileReadLines(path, default=[], source=MODULE_NAME) if x.strip())
					if "root=" in line:
						# print("[MultiBoot] loadBootSlots DEBUG: 'root=' found.")
						device = self.getParam(line, "root")
						if "UUID=" in device:
							uuidDevice = self.getUUIDtoDevice(device)
							# print(f"[MultiBoot] loadBootSlots DEBUG: 'UUID=' found for device '{uuidDevice}'.")
							if uuidDevice:
								device = uuidDevice
						if exists(device) or device == "ubi0:ubifs":
							if slotCode not in bootSlots:
								bootSlots[slotCode] = {}
								# print(f"[MultiBoot] Root dictionary entry in slot '{slotCode}' created.")
							value = bootSlots[slotCode].get("device")
							if value is None:
								bootSlots[slotCode]["device"] = device
							elif value != device:
								print(f"[MultiBoot] Error: Inconsistent root devices found for slot '{slotCode}'!  ('{value}' != '{device}')")
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
							if "UUID=" in line:
								bootSlots[slotCode]["uuid"] = True
							if "rescuemode" in line:
								bootSlots[slotCode]["rootsubdir"] = "rescue"
							bootDevice = [x for x in ("sda", "sdb", "sdc", "sdd") if x in line]
							if "rootsubdir" in line:
								bootSlots[slotCode]["kernel"] = self.getParam(line, "kernel")
								bootSlots[slotCode]["rootsubdir"] = self.getParam(line, "rootsubdir")
							elif bootDevice:
								device = bootDevice[0]
								saveKernel(bootSlots, slotCode, f"/dev/{device}{line.split(device, 1)[1].split(" ", 1)[0]}")
							else:
								parts = device.split("p")
								saveKernel(bootSlots, slotCode, f"{parts[0]}p{int(parts[1]) - 1}")
					elif "bootcmd=" in line or " recovery " in line:
						# print("[MultiBoot] loadBootSlots DEBUG: 'bootcmd=' or ' recovery ' text found.")
						if slotCode not in bootSlots:
							bootSlots[slotCode] = {}
							# print(f"[MultiBoot] Boot Command/Recovery dictionary entry in slot '{slotCode}' created.")
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
						print(f"[MultiBoot] Error: Slot can't be identified.  ({line})")
				else:
					print(f"[MultiBoot] Error: Slot code can not be determined from '{file}'!")
			self.console.ePopen([UMOUNT, UMOUNT, tempDir])
			rmdir(tempDir)
			bootSlotsKeys = sorted(bootSlots.keys())
			if self.debugMode:
				for slotCode in bootSlotsKeys:
					# print(f"[MultiBoot] loadBootSlots DEBUG: Boot slot '{slotCode}': {bootSlots[slotCode]}")
					print(f"[MultiBoot] Slot '{slotCode}':")
					modes = bootSlots[slotCode].get("bootCodes")
					if modes and modes != [""]:
						print(f"[MultiBoot]     Boot modes: '{"', '".join(modes)}'.")
					startupFile = bootSlots[slotCode].get("startupfile")
					if startupFile:
						if isinstance(startupFile, dict):
							if "" in startupFile:
								print(f"[MultiBoot]     Startup file: '{startupFile[""]}'.")
							else:
								print("[MultiBoot]     Startup files:")
								for key in sorted(startupFile.keys()):
									print(f"[MultiBoot]         Mode '{key}': '{startupFile[key]}'.")
						else:
							print(f"[MultiBoot]     Startup file: '{startupFile}'.")
					commandLine = bootSlots[slotCode].get("cmdline")
					if commandLine:
						if isinstance(commandLine, dict):
							if "" in startupFile:
								print(f"[MultiBoot]     Command line: '{startupFile[""]}'.")
							else:
								print("[MultiBoot]     Command lines:")
								for key in sorted(commandLine.keys()):
									print(f"[MultiBoot]         Mode '{key}': '{commandLine[key]}'.")
						else:
							print(f"[MultiBoot]     Command line: '{startupFile}'.")
					print(f"[MultiBoot]     Kernel device: '{bootSlots[slotCode].get("kernel", "Unknown")}'.")
					print(f"[MultiBoot]     Root device: '{bootSlots[slotCode].get("device", "Unknown")}'.")
					print(f"[MultiBoot]     Root directory: '{bootSlots[slotCode].get("rootsubdir", "Unknown")}'.")
					print(f"[MultiBoot]     UBI device: '{"Yes" if bootSlots[slotCode].get("ubi", False) else "No"}'.")
					print(f"[MultiBoot]     UUID device: '{"Yes" if bootSlots[slotCode].get("uuid", False) else "No"}'.")
				print(f"[MultiBoot] {len(bootSlots)} boot slots detected.")
		return bootSlots, bootSlotsKeys

	def getParam(self, line, param):
		return line.replace("userdataroot", "rootuserdata").rsplit(f"{param}=", 1)[1].split(" ", 1)[0]

	def getUUIDtoDevice(self, UUID):  # Returns None on failure.
		if UUID.startswith("UUID="):  # Remove the "UUID=" from startup files that have it.
			UUID = UUID[5:]
		for fileName in listdir("/dev/uuid"):
			if fileReadLine(pathjoin("/dev/uuid", fileName)) == UUID:
				return f"/dev/{fileName}"
		return None

	def loadCurrentSlotAndBootCodes(self):
		if self.bootSlots and self.bootSlotsKeys:
			for slotCode in self.bootSlotsKeys:
				cmdLines = self.bootSlots[slotCode]["cmdline"]
				bootCodes = sorted(self.bootSlots[slotCode]["cmdline"].keys())
				for bootCode in bootCodes:
					if cmdLines[bootCode] == self.startupCmdLine:
						if self.debugMode:
							print(f"[MultiBoot] Startup slot code is '{slotCode}' and boot mode is '{bootCode if bootCode else ""}'.")
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
		if slotCode is None:
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
				"bootCodes": self.bootSlots[self.slotCode].get("bootCodes", [""]),
				"device": self.bootSlots[self.slotCode].get("device", _("Unknown")),
				"devicelog": self.bootSlots[self.slotCode].get("device", "Unknown"),
				"root": self.bootSlots[self.slotCode].get("rootsubdir", _("Not required")),
				"rootlog": self.bootSlots[self.slotCode].get("rootsubdir", "Not required")
			}
			if self.slotCode == "A":
				self.imageList[self.slotCode]["detection"] = "Found an Android slot"
				self.imageList[self.slotCode]["imagename"] = _("Android")
				self.imageList[self.slotCode]["imagelogname"] = "Android"
				self.imageList[self.slotCode]["status"] = "android"
				self.findSlot()
			elif self.slotCode == "L":
				self.imageList[self.slotCode]["detection"] = "Found an Android Linux SE slot"
				self.imageList[self.slotCode]["imagename"] = _("Android Linux SE")
				self.imageList[self.slotCode]["imagelogname"] = "Android Linux SE"
				self.imageList[self.slotCode]["status"] = "androidlinuxse"
				self.findSlot()
			elif self.slotCode == "R" and fileHas("/proc/cmdline", "kexec=1"):
				self.imageList[self.slotCode]["detection"] = "Found a Root Image slot"
				self.imageList[self.slotCode]["imagename"] = _("Root Image")
				self.imageList[self.slotCode]["imagelogname"] = "Root Image"
				self.imageList[self.slotCode]["status"] = "rootimage"
				self.findSlot()
			elif self.slotCode == "R":
				self.imageList[self.slotCode]["detection"] = "Found a Recovery slot"
				self.imageList[self.slotCode]["imagename"] = _("Recovery")
				self.imageList[self.slotCode]["imagelogname"] = "Recovery"
				self.imageList[self.slotCode]["status"] = "recovery"
				self.findSlot()
			elif self.bootSlots[self.slotCode].get("device"):
				self.device = self.bootSlots[self.slotCode]["device"]
				# print(f"[MultiBoot] DEBUG: Analyzing slot='{self.slotCode}' ({self.device}).")
				if hasMultiBootMTD:
					self.console.ePopen([MOUNT, MOUNT, "-t", "ubifs", self.device, self.tempDir], self.analyzeSlot)
				else:
					self.console.ePopen([MOUNT, MOUNT, self.device, self.tempDir], self.analyzeSlot)
			else:
				self.imageList[self.slotCode]["detection"] = "Found an unexpected/ill-defined slot"
				self.imageList[self.slotCode]["imagename"] = _("Unknown")
				self.imageList[self.slotCode]["imagelogname"] = "Unknown"
				self.imageList[self.slotCode]["status"] = "unknown"
				self.findSlot()
		else:
			rmdir(self.tempDir)
			if self.debugMode:
				for slotCode in sorted(self.imageList.keys()):
					# print(f"[MultiBoot] findSlot DEBUG: Image slot '{slotCode}': {self.imageList[slotCode]}")
					print(f"[MultiBoot] Slot '{slotCode}' content: '{self.imageList[slotCode].get("imagelogname", "Unknown")}'.")
					print(f"[MultiBoot]     Device: '{self.imageList[slotCode].get("devicelog", "Unknown")}'.")
					print(f"[MultiBoot]     Root: '{self.imageList[slotCode].get("rootlog", "Unknown")}'.")
					print(f"[MultiBoot]     Detection: '{self.imageList[slotCode].get("detection", "Unknown")}'.")
					print(f"[MultiBoot]     Status: '{self.imageList[slotCode].get("status", "Unknown").capitalize()}'.")
					modes = self.imageList[slotCode].get("bootCodes")
					if modes and modes != [""]:
						print(f"[MultiBoot]     Boot modes: '{"', '".join(modes)}'.")
					print(f"[MultiBoot]     UBI device: '{"Yes" if self.imageList[slotCode].get("ubi", False) else "No"}'.")
					print(f"[MultiBoot]     UUID device: '{"Yes" if self.imageList[slotCode].get("uuid", False) else "No"}'.")
				print(f"[MultiBoot] {len(self.imageList)} boot slots detected.")
			self.callback(self.imageList)

	def analyzeSlot(self, data, retVal, extraArgs):  # Part of getSlotImageList().
		if retVal:
			self.imageList[self.slotCode]["detection"] = f"Error {retVal}: Unable to mount slot '{self.slotCode}' ({self.device}) for analysis"
			self.imageList[self.slotCode]["imagename"] = _("Inaccessible")
			self.imageList[self.slotCode]["imagelogname"] = "Inaccessible"
			self.imageList[self.slotCode]["status"] = "unknown"
		else:
			rootDir = self.bootSlots[self.slotCode].get("rootsubdir")
			imageDir = pathjoin(self.tempDir, rootDir) if rootDir else self.tempDir
			infoFile = pathjoin(imageDir, "usr/lib/enigma.info")
			infoFile1 = pathjoin(imageDir, "etc/image-version")
			if isfile(infoFile):
				info = self.readSlotInfo(infoFile)
				compileDate = str(info.get("compiledate"))
				revision = info.get("imgrevision")
				revision = ".%03d" % revision if info.get("distro") == "openvix" and isinstance(revision, int) else f" {revision}"
				revision = "" if revision.strip() == compileDate else revision
				compileDate = f"{compileDate[0:4]}-{compileDate[4:6]}-{compileDate[6:8]}"
				self.imageList[self.slotCode]["detection"] = "Found an enigma information file"
				self.imageList[self.slotCode]["imagename"] = f"{info.get("displaydistro", info.get("distro"))} {info.get("imgversion")}{revision} ({compileDate})"
				self.imageList[self.slotCode]["imagelogname"] = f"{info.get("displaydistro", info.get("distro"))} {info.get("imgversion")}{revision} ({compileDate})"
				self.imageList[self.slotCode]["status"] = "active"
			elif isfile(infoFile1):
				info = self.readSlotInfo(infoFile1)
				compileDate = self.getCompiledate(imageDir)
				compileDate = f"{compileDate[0:4]}-{compileDate[4:6]}-{compileDate[6:8]}"
				version = str(info.get("version"))
				if "." not in version and "-" not in version and version.isdigit():
					version = f"{int(version[0:2])}.{int(version[3:5])}"
				self.imageList[self.slotCode]["detection"] = "Found an image version file"
				creator = info.get("creator")
				if creator is not None:
					self.imageList[self.slotCode]["imagename"] = f"{creator.split()[0]} {version} ({compileDate})"
					self.imageList[self.slotCode]["imagelogname"] = f"{creator.split()[0]} {version} ({compileDate})"
				else:
					self.imageList[self.slotCode]["imagename"] = f"Unknown Creator {version} ({compileDate})"
					self.imageList[self.slotCode]["imagelogname"] = f"Unknown Creator {version} ({compileDate})"
				self.imageList[self.slotCode]["status"] = "active"
			elif isfile(pathjoin(imageDir, "usr/bin/enigma2")):
				info = self.deriveSlotInfo(imageDir)
				compileDate = str(info.get("compiledate"))
				compileDate = f"{compileDate[0:4]}-{compileDate[4:6]}-{compileDate[6:8]}"
				self.imageList[self.slotCode]["detection"] = "Found an enigma2 binary file"
				self.imageList[self.slotCode]["imagename"] = f"{info.get("displaydistro", info.get("distro"))} {info.get("imgversion")} ({compileDate})"
				self.imageList[self.slotCode]["imagelogname"] = f"{info.get("displaydistro", info.get("distro"))} {info.get("imgversion")} ({compileDate})"
				self.imageList[self.slotCode]["status"] = "active"
			else:
				self.imageList[self.slotCode]["detection"] = "Found no enigma files"
				self.imageList[self.slotCode]["imagename"] = _("Empty")
				self.imageList[self.slotCode]["imagelogname"] = "Empty"
				self.imageList[self.slotCode]["status"] = "empty"
		if ismount(self.tempDir):
			self.console.ePopen([UMOUNT, UMOUNT, self.tempDir], self.finishSlot)
		else:
			self.findSlot()

	def finishSlot(self, data, retVal, extraArgs):  # Part of getSlotImageList().
		if retVal:
			print(f"[MultiBoot] finishSlot Error {retVal}: Unable to unmount slot '{self.slotCode}' (self.device)!")
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
					item, value = (x.strip() for x in line.split("=", 1))
					if item:
						info[item] = self.processValue(value)
		lines = fileReadLines(path.replace(".info", ".conf"), source=MODULE_NAME)
		if lines:
			for line in lines:
				if line.startswith("#") or line.strip() == "":
					continue
				if "=" in line:
					item, value = (x.strip() for x in line.split("=", 1))
					if item:
						if item in info:
							print(f"[MultiBoot] Note: Enigma information value '{item}' with value '{info[item]}' being overridden to '{value}'.")
						info[item] = self.processValue(value)
		return info

	def checkChecksum(self, lines):  # Part of readSlotInfo() within analyzeSlot() within getSlotImageList().
		value = "Undefined!"
		data = []
		for line in lines:
			if line.startswith("checksum"):
				item, value = (x.strip() for x in line.split("=", 1))
			else:
				data.append(line)
		data.append("")
		result = md5(bytearray("\n".join(data), "UTF-8", errors="ignore")).hexdigest()  # NOSONAR
		return value != result

	def processValue(self, value):  # Part of readSlotInfo() within analyzeSlot() within getSlotImageList().
		valueTest = value.upper() if value else ""
		if value is None:
			pass
		elif (value.startswith("\"") or value.startswith("'")) and value.endswith(value[0]):
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
		elif value.isdigit() or (value[0:1] in ("-", "+") and value[1:].isdigit()):
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

	def getCompiledate(self, path):
		statusfile = "var/lib/opkg/status"
		if exists(pathjoin(path, "var/lib/dpkg/status")):
			statusfile = "var/lib/dpkg/status"
		try:
			date = datetime.fromtimestamp(stat(pathjoin(path, statusfile)).st_mtime).strftime("%Y%m%d")
			if date.startswith("1970"):
				date = datetime.fromtimestamp(stat(pathjoin(path, "usr/share/bootlogo.mvi")).st_mtime).strftime("%Y%m%d")
			date = max(date, datetime.fromtimestamp(stat(pathjoin(path, "usr/bin/enigma2")).st_mtime).strftime("%Y%m%d"))
		except OSError as err:
			date = "00000000"
		return date

	def deriveSlotInfo(self, path):  # Part of analyzeSlot() within getSlotImageList().
		info = {}
		info["compiledate"] = self.getCompiledate(path)
		lines = fileReadLines(pathjoin(path, "etc/issue"), source=MODULE_NAME)
		if lines and "vuplus" not in lines[0] and len(lines) >= 2:
			data = lines[-2].strip()[:-6].split()
			info["distro"] = " ".join(data[:-1])
			info["displaydistro"] = {
				"beyonwiz": "Beyonwiz",
				"blackhole": "Black Hole",
				"egami": "EGAMI",
				"openatv": "OpenATV",
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
		self.console.ePopen([MOUNT, MOUNT, self.bootDevice, self.tempDir], self.bootDeviceMounted)

	def bootDeviceMounted(self, data, retVal, extraArgs):  # Part of activateSlot().
		if retVal:
			print(f"[MultiBoot] bootDeviceMounted Error {retVal}: Unable to mount boot device '{self.bootDevice}'!")
			self.callback(1)
		else:
			bootSlot = self.bootSlots[self.slotCode]
			startup = bootSlot["startupfile"][self.bootCode]
			if (fileHas("/proc/cmdline", "kexec=1") or self.bootSlots[self.slotCode].get("rootsubdir") == "rescue") and startup == STARTUP_RECOVERY:
				target = STARTUP_FILE
			else:
				target = STARTUP_ONCE if startup == STARTUP_RECOVERY else STARTUP_FILE
			if exists(DREAM_BOOT_FILE) and startup == STARTUP_RECOVERY:
				pass
			else:
				copyfile(pathjoin(self.tempDir, startup), pathjoin(self.tempDir, target))
			if exists(DUAL_BOOT_FILE):
				slot = self.slotCode if self.slotCode.isdecimal() else "0"
				with open(DUAL_BOOT_FILE, "wb") as fd:
					fd.write(pack("B", int(slot)))
			if exists(DREAM_BOOT_FILE):
				if self.slotCode == "R":
					cmd_count = 0
					with open(DREAM_BOOT_FILE, "r") as fd:
						lines = fd.readlines()
						for line in lines:
							if line.startswith("cmd="):
								cmd_count += 1
					self.slotCode = str(cmd_count)
				slot = int(self.slotCode) - 1
				with open(DREAM_BOOT_FILE, "r+") as fd:
					lines = fd.readlines()
					fd.seek(0)
					for line in lines:
						if line.startswith("default="):
							line = f"default={slot}\n"
						fd.write(line)
					fd.truncate()
			if self.debugMode:
				print(f"[MultiBoot] Installing '{startup}' as '{target}'.")
			self.console.ePopen([UMOUNT, UMOUNT, self.tempDir], self.bootDeviceUnmounted)

	def bootDeviceUnmounted(self, data, retVal, extraArgs):  # Part of activateSlot().
		if retVal:
			print(f"[MultiBoot] bootDeviceUnmounted Error {retVal}: Unable to mount boot device '{self.bootDevice}'!")
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
				self.console.ePopen([MOUNT, MOUNT, "-t", "ubifs", self.device, self.tempDir], method)
			else:
				self.console.ePopen([MOUNT, MOUNT, self.device, self.tempDir], method)
		else:
			self.callback(1)

	def hideSlot(self, data, retVal, extraArgs):  # Part of emptySlot().
		if retVal:
			print(f"[MultiBoot] hideSlot Error {retVal}: Unable to mount slot '{self.slotCode}' ({self.device})!")
			self.callback(2)
		else:
			rootDir = self.bootSlots[self.slotCode].get("rootsubdir")
			imageDir = pathjoin(self.tempDir, rootDir) if rootDir else self.tempDir
			if self.bootSlots[self.slotCode].get("ubi", False) or fileHas("/proc/cmdline", "kexec=1"):
				try:
					if isfile(pathjoin(imageDir, "usr/bin/enigma2")):
						self.console.ePopen([REMOVE, REMOVE, "-rf", imageDir])
					mkdir(imageDir)
				except OSError as err:
					print(f"[MultiBoot] hideSlot Error {err.errno}: Unable to wipe all files in slot '{self.slotCode}' ({self.device})!  ({err.strerror})")
			else:
				enigmaFile = ""  # This is in case the first pathjoin fails.
				try:
					enigmaFile = pathjoin(imageDir, "usr/bin/enigma2")
					if isfile(enigmaFile):
						rename(enigmaFile, f"{enigmaFile}x.bin")
					enigmaFile = pathjoin(imageDir, "usr/lib/enigma.info")
					if isfile(enigmaFile):
						rename(enigmaFile, f"{enigmaFile}x")
					enigmaFile = pathjoin(imageDir, "etc")
					if isdir(enigmaFile):
						rename(enigmaFile, f"{enigmaFile}x")
				except OSError as err:
					print(f"[MultiBoot] hideSlot Error {err.errno}: Unable to hide item '{enigmaFile}' in slot '{self.slotCode}' ({self.device})!  ({err.strerror})")
			self.console.ePopen([UMOUNT, UMOUNT, self.tempDir], self.cleanUpSlot)

	def revealSlot(self, data, retVal, extraArgs):  # Part of restoreSlot().
		if retVal:
			print(f"[MultiBoot] revealSlot Error {retVal}: Unable to mount slot '{self.slotCode}' ({self.device})!")
			self.callback(2)
		else:
			rootDir = self.bootSlots[self.slotCode].get("rootsubdir")
			imageDir = pathjoin(self.tempDir, rootDir) if rootDir else self.tempDir
			enigmaFile = ""  # This is in case the first pathjoin fails.
			try:
				enigmaFile = pathjoin(imageDir, "usr/bin/enigma2")
				hiddenFile = f"{enigmaFile}x.bin"
				if isfile(hiddenFile):
					rename(hiddenFile, enigmaFile)
				enigmaFile = pathjoin(imageDir, "usr/lib/enigma.info")
				hiddenFile = f"{enigmaFile}x"
				if isfile(hiddenFile):
					rename(hiddenFile, enigmaFile)
				enigmaFile = pathjoin(imageDir, "etc")
				hiddenFile = f"{enigmaFile}x"
				if isdir(hiddenFile):
					rename(hiddenFile, enigmaFile)
			except OSError as err:
				print(f"[MultiBoot] revealSlot Error {err.errno}: Unable to reveal item '{enigmaFile}' in slot '{self.slotCode}' ({self.device})!  ({err.strerror})")
			self.console.ePopen([UMOUNT, UMOUNT, self.tempDir], self.cleanUpSlot)

	def cleanUpSlot(self, data, retVal, extraArgs):  # Part of emptySlot() and restoreSlot().
		if retVal:
			print(f"[MultiBoot] emptySlotCleanUp Error {retVal}: Unable to unmount slot '{self.slotCode}' ({self.device})!")
			self.callback(3)
		else:
			rmdir(self.tempDir)
			self.callback(0)


MultiBoot = MultiBootClass()
