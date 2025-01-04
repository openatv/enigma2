from os import listdir, makedirs, stat, statvfs
from os.path import join, isdir
from re import search
from shlex import split

from enigma import eTimer

from Components.AVSwitch import avSwitch
from Components.config import ConfigBoolean, config, configfile
from Components.Console import Console
from Components.Harddisk import harddiskmanager
from Components.Storage import EXPANDER_MOUNT
from Components.SystemInfo import BoxInfo
from Components.Pixmap import Pixmap
from Screens.FlashExpander import MOUNT_DEVICE, MOUNT_MOUNTPOINT, MOUNT_FILESYSTEM
from Screens.HarddiskSetup import HarddiskSelection
from Screens.HelpMenu import ShowRemoteControl
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop, QUIT_RESTART
from Screens.VideoWizard import VideoWizard
from Screens.Wizard import wizardManager, Wizard
from Tools.Directories import fileReadLine, fileReadLines, fileWriteLines

MODULE_NAME = __name__.split(".")[-1]

config.misc.firstrun = ConfigBoolean(default=True)
config.misc.videowizardenabled = ConfigBoolean(default=True)
config.misc.wizardLanguageEnabled = ConfigBoolean(default=True)


class StartWizard(Wizard, ShowRemoteControl):
	def __init__(self, session, silent=True, showSteps=False, neededTag=None):
		self.xmlfile = ["startwizard.xml"]
		Wizard.__init__(self, session, showSteps=False)
		ShowRemoteControl.__init__(self)
		self.deviceData = {}
		self.mountData = None
		self.swapDevice = None
		self.swapDeviceIndex = -1
		self.console = Console()
		flashSize = statvfs('/')
		flashSize = (flashSize.f_frsize * flashSize.f_blocks) // 2 ** 20
		self.smallFlashSize = BoxInfo.getItem("SmallFlash") and flashSize < 130
		self.swapExists = "/dev/" in "".join(fileReadLines("/proc/swaps", default=[], source=MODULE_NAME))
		self["wizard"] = Pixmap()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self.setTitle(_("Start Wizard"))

	def markDone(self):
		# Setup remote control, all STBs have same settings except dm8000 which uses a different setting.
		config.misc.rcused.value = 0 if BoxInfo.getItem("machinebuild") == 'dm8000' else 1
		config.misc.rcused.save()
		config.misc.firstrun.value = False
		config.misc.firstrun.save()
		configfile.save()

	def createSwapFileFlashExpander(self, callback):
		def messageBoxCallback(*res):
			if callback and callable(callback):
				callback()

		def creataSwapFileCallback(result=None, retVal=None, extraArgs=None):
			fstab = fileReadLines("/etc/fstab", default=[], source=MODULE_NAME)
			print("[FlashExpander] fstabUpdate DEBUG: Begin fstab:\n%s" % "\n".join(fstab))
			fstabNew = [line for line in fstab if "swap" not in line]
			fstabNew.append("%s swap swap defaults 0 0" % fileName)
			fstabNew.append("")
			fileWriteLines("/etc/fstab", "\n".join(fstabNew), source=MODULE_NAME)
			print("[FlashExpander] fstabUpdate DEBUG: Ending fstab:\n%s" % "\n".join(fstabNew))
			messageBox.close()

		print("[StartWizard] DEBUG createSwapFileFlashExpander")
		messageBox = self.session.openWithCallback(messageBoxCallback, MessageBox, _("Please wait, swap is is being created. This could take a few minutes to complete."), MessageBox.TYPE_INFO, enable_input=False, windowTitle=_("Create swap"))
		fileName = join("/.FlashExpander", "swapfile")
		commands = []
		commands.append("/bin/dd if=/dev/zero of='%s' bs=1024 count=131072 2>/dev/null" % fileName)  # Use 128 MB because creation of bigger swap is very slow.
		commands.append("/bin/chmod 600 '%s'" % fileName)
		commands.append("/sbin/mkswap '%s'" % fileName)
		commands.append("/sbin/swapon '%s'" % fileName)
		self.console.eBatch(commands, creataSwapFileCallback, debug=True)

	def createSwapFile(self, callback):
		def getPathMountData(path):
			mounts = fileReadLines("/proc/mounts", [], source=MODULE_NAME)
			print("[StartWizard] getPathMountData DEBUG: path=%s." % path)
			for mount in mounts:
				data = mount.split()
				if data[MOUNT_DEVICE] == path:
					status = stat(data[MOUNT_MOUNTPOINT])
					return (data[MOUNT_MOUNTPOINT], status, data)
			return None

		def creataSwapFileCallback(result=None, retVal=None, extraArgs=None):
			if callback and callable(callback):
				callback()

		print("[StartWizard] DEBUG createSwapFile: %s" % self.swapDevice)
		fileName = "/.swap/swapfile"
		path = self.deviceData[self.swapDevice][0]
		self.mountData = getPathMountData(path)
		if self.mountData:
			fstab = fileReadLines("/etc/fstab", default=[], source=MODULE_NAME)
			print("[StartWizard] fstabUpdate DEBUG: Starting fstab:\n%s" % "\n".join(fstab))
			fstabNew = [line for line in fstab if "swap" not in line]
			mountData = self.mountData[2]
			line = " ".join(("UUID=%s" % self.swapDevice, "/.swap", mountData[MOUNT_FILESYSTEM], "defaults", "0", "0"))
			fstabNew.append(line)
			fstabNew.append("%s swap swap defaults 0 0" % fileName)
			fstabNew.append("")
			fileWriteLines("/etc/fstab", "\n".join(fstabNew), source=MODULE_NAME)
			print("[StartWizard] fstabUpdate DEBUG: Ending fstab:\n%s" % "\n".join(fstabNew))
			makedirs("/.swap", mode=0o755, exist_ok=True)
			commands = []
			commands.append("/bin/mount -a")
			commands.append("/bin/dd if=/dev/zero of='%s' bs=1024 count=131072 2>/dev/null" % fileName)  # Use 128 MB because creation of bigger swap is very slow.
			commands.append("/bin/chmod 600 '%s'" % fileName)
			commands.append("/sbin/mkswap '%s'" % fileName)
			commands.append("/sbin/swapon '%s'" % fileName)
			self.console.eBatch(commands, creataSwapFileCallback, debug=True)
		else:
			self.session.open(MessageBox, _("No valid mount for '%s' found!") % path, type=MessageBox.TYPE_ERROR)

	def swapDeviceList(self):  # Called by startwizard.xml.
		choiceList = []
		for deviceID, deviceData in self.deviceData.items():
			choiceList.append(("%s (%s)" % (deviceData[1], deviceData[0]), deviceID))
		# DEBUG
		print("[StartWizard] DEBUG swapDeviceList: %s" % str(choiceList))

		if len(choiceList) == 0:
			choiceList.append((_("No valid device detected - Press OK"), "."))
		return choiceList

	def swapDeviceSelectionMade(self, index):  # Called by startwizard.xml.
		print("[StartWizard] swapDeviceSelectionMade DEBUG: index='%s'." % index)
		self.swapDeviceIndex = index

	def swapDeviceSelectionMoved(self):  # Called by startwizard.xml.
		print("[StartWizard] DEBUG swapDeviceSelectionMoved: %s" % self.selection)
		self.swapDevice = self.selection

	def readSwapDevices(self, callback=None):
		black = BoxInfo.getItem("mtdblack")
		self.deviceData = {}
		uuids = {}
		for fileName in listdir("/dev/uuid"):
			if black not in fileName:
				m = search(r"(?P<A>mmcblk\d)p1$|(?P<B>sd\w)1$", fileName)
				if m:
					disk = m.group("A") or m.group("B")
					if disk:
						uuids[disk] = (fileReadLine(join("/dev/uuid", fileName)), f"/dev/{fileName}")

		print("[StartWizard] DEBUG readSwapDevices uuids", uuids)

		for (name, hdd) in harddiskmanager.HDDList():
			uuid, device = uuids.get(hdd.device, (None, None))
			if uuid:
				self.deviceData[uuid] = (device, name)

		print("[StartWizard] DEBUG readSwapDevicesCallback: %s" % str(self.deviceData))
		if callback and callable(callback):
			callback()

	def getFreeMemory(self):
		memInfo = fileReadLines("/proc/meminfo", source=MODULE_NAME)
		return int([line for line in memInfo if "MemFree" in line][0].split(":")[1].strip().split(maxsplit=1)[0]) // 1024

	def isFlashExpanderActive(self):
		return isdir(join("/%s/%s" % (EXPANDER_MOUNT, EXPANDER_MOUNT), "bin"))

	def hasPartitions(self):
		partitions = fileReadLines("/proc/partitions", source=MODULE_NAME)
		count = 0
		black = BoxInfo.getItem("mtdblack")
		for line in partitions:
			parts = line.strip().split()
			if parts:
				device = parts[3]
				if not device.startswith(black) and (search(r"^sd[a-z][1-9][\d]*$", device) or search(r"^mmcblk[\d]p[\d]*$", device)):
					count += 1
		return count > 1

	def keyYellow(self):
		if self.wizard[self.currStep]["name"] == "swap":
			if not self.isFlashExpanderActive():
				def formatCallback():
					harddiskmanager.enumerateBlockDevices()
					self.updateValues()
				self.session.openWithCallback(formatCallback, HarddiskSelection)
		else:
			Wizard.keyYellow(self)


class WizardLanguage(Wizard, ShowRemoteControl):
	def __init__(self, session, silent=True, showSteps=False, neededTag=None):
		self.xmlfile = ["wizardlanguage.xml"]
		Wizard.__init__(self, session, showSteps=False)
		ShowRemoteControl.__init__(self)
		self.skinName = ["WizardLanguage", "StartWizard"]
		self.oldLanguage = config.osd.language.value
		self.mode = "720p"
		self.modeList = [(mode[0], mode[0]) for mode in avSwitch.getModeList("HDMI")]
		self["wizard"] = Pixmap()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self.setTitle(_("Start Wizard"))
		self.resolutionTimer = eTimer()
		self.resolutionTimer.callback.append(self.resolutionTimeout)
		# preferred = avSwitch.readPreferredModes(saveMode=True)
		preferred = ["720p"]  # Use only 720p because some TV sends wrong edid info
		available = avSwitch.readAvailableModes()
		preferred = list(set(preferred) & set(available))

		if preferred:
			if "2160p50" in preferred:
				self.mode = "2160p"
			elif "2160p30" in preferred:
				self.mode = "2160p30"
			elif "1080p" in preferred:
				self.mode = "1080p"

		self.setMode()

		if not preferred:
			ports = [port for port in avSwitch.getPortList() if avSwitch.isPortUsed(port)]
			if len(ports) > 1:
				self.resolutionTimer.start(20000)
				print("[WizardLanguage] DEBUG start resolutionTimer")

	def setMode(self):
		print("[WizardLanguage] DEBUG setMode %s" % self.mode)
		if self.mode in ("720p", "1080p") and not BoxInfo.getItem("AmlogicFamily"):
			rate = "multi"
		else:
			rate = self.getVideoRate()
		avSwitch.setMode(port="HDMI", mode=self.mode, rate=rate)

	def getVideoRate(self):
		def sortKey(name):
			return {
				"multi": 1,
				"auto": 2
			}.get(name[0], 3)

		rates = []
		for modes in avSwitch.getModeList("HDMI"):
			if modes[0] == self.mode:
				for rate in modes[1]:
					if rate == "auto" and not BoxInfo.getItem("have24hz"):
						continue
					rates.append((rate, rate))
		rates.sort(key=sortKey)
		return rates[0][0]

	def resolutionTimeout(self):
		if self.mode == "720p":
			self.mode = "576i"
		if self.mode == "576i":
			self.mode = "480i"
			self.resolutionTimer.stop()
		self.setMode()

	def saveWizardChanges(self):
		self.resolutionTimer.stop()
		config.misc.wizardLanguageEnabled.value = 0
		config.misc.wizardLanguageEnabled.save()
		configfile.save()
		if config.osd.language.value != self.oldLanguage:
			self.session.open(TryQuitMainloop, QUIT_RESTART)
		self.close()


# StartEnigma.py#L528ff - RestoreSettings
if config.misc.firstrun.value:
	wizardManager.registerWizard(WizardLanguage, config.misc.wizardLanguageEnabled.value, priority=0)
wizardManager.registerWizard(VideoWizard, config.misc.videowizardenabled.value, priority=1)
#wizardManager.registerWizard(LocaleWizard, config.misc.languageselected.value, priority=2)
# FrontprocessorUpgrade FPUpgrade priority = 8
# FrontprocessorUpgrade SystemMessage priority = 9
wizardManager.registerWizard(StartWizard, config.misc.firstrun.value, priority=30)
# StartWizard calls InstallWizard
# NetworkWizard priority = 25
