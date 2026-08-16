from os import listdir, makedirs, stat, statvfs
from os.path import join, isdir
from re import search

from enigma import eTimer

from Components.AVSwitch import avSwitch
from Components.config import ConfigBoolean, config, configfile
from Components.Console import Console
from Components.Harddisk import harddiskmanager
from Components.NetworkManager import networkManager
from Components.Storage import EXPANDER_MOUNT
from Components.SystemInfo import BoxInfo
from Components.Pixmap import Pixmap
from Screens.FlashExpander import MOUNT_DEVICE, MOUNT_MOUNTPOINT, MOUNT_FILESYSTEM
from Screens.HarddiskSetup import HarddiskSelection
from Screens.HelpMenu import ShowRemoteControl
from Screens.MessageBox import MessageBox
from Screens.NetworkSetup import NetworkAdapterSetup, NetworkWiFiAddFlow
from Screens.Standby import TryQuitMainloop, QUIT_RESTART
from Screens.WizardVideo import WizardVideo
from Screens.Wizard import wizardManager, Wizard
from Tools.Directories import fileReadLine, fileReadLines, fileWriteLines

MODULE_NAME = __name__.split(".")[-1]

config.misc.firstrun = ConfigBoolean(default=True)
config.misc.videowizardenabled = ConfigBoolean(default=True)
config.misc.wizardLanguageEnabled = ConfigBoolean(default=True)


class WizardStart(Wizard, ShowRemoteControl):

	def __init__(self, session, silent=True, showSteps=False, neededTag=None):
		self.xmlfile = ["startwizard.xml"]
		Wizard.__init__(self, session, showSteps=False)
		ShowRemoteControl.__init__(self)
		self.skinName.insert(0, "StartWizard")
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
		self.nwSelectedIface = None
		self.nwIpFound = ""
		self.nwPollTimer = None
		self.nwPollCount = 0
		self.nwSubFlowActive = False
		self.nwPollIntervalMs = 1500
		self.nwPollMaxAttempts = 12  # 18 s total

	def markDone(self):
		# All boxes use the same remote control setting except the dm8000, which needs its own.
		config.misc.rcused.value = 0 if BoxInfo.getItem("machinebuild") == 'dm8000' else 1
		config.misc.rcused.save()
		config.misc.firstrun.value = False
		config.misc.firstrun.save()
		configfile.save()

	def createSwapFileFlashExpander(self, callback):
		def messageBoxCallback(*res):
			if callback and callable(callback):
				callback()

		def isSwapActive(path):
			swaps = fileReadLines("/proc/swaps", default=[], source=MODULE_NAME)
			for line in swaps[1:]:
				parts = line.split()
				if parts and parts[0] == path:
					return True
			return False

		def creataSwapFileCallback(result=None, retVal=None, extraArgs=None):
			print(f"[FlashExpander] createSwapFile callback DEBUG: retVal={retVal}, result={result}")
			if retVal not in (0, None) and not isSwapActive(fileName):
				if messageBox:
					messageBox.close()
				self.session.open(MessageBox, _("Creating or activating the swap file failed.\n\n%s") % (result or ""), type=MessageBox.TYPE_ERROR)
				return
			fstab = fileReadLines("/etc/fstab", default=[], source=MODULE_NAME)
			print("[FlashExpander] fstabUpdate DEBUG: Begin fstab:\n%s" % "\n".join(fstab))
			fstabNew = [line for line in fstab if "swap" not in line]
			fstabNew.append(f"{fileName} swap swap defaults 0 0")
			fstabNew.append("")
			fileWriteLines("/etc/fstab", "\n".join(fstabNew), source=MODULE_NAME)
			print("[FlashExpander] fstabUpdate DEBUG: Ending fstab:\n%s" % "\n".join(fstabNew))
			messageBox.close()

		print("[WizardStart] DEBUG createSwapFileFlashExpander")
		messageBox = self.session.openWithCallback(messageBoxCallback, MessageBox, _("Please wait, swap is being created. This could take a few minutes to complete."), MessageBox.TYPE_INFO, enable_input=False, windowTitle=_("Create swap"))
		fileName = join("/.FlashExpander", "swapfile")
		commands = []
		commands.append(f"/bin/dd if=/dev/zero of='{fileName}' bs=1024 count=131072 2>/dev/null")  # Use 128 MB because creation of bigger swap is very slow.
		commands.append(f"/bin/chmod 600 '{fileName}'")
		commands.append(f"/sbin/mkswap '{fileName}'")
		commands.append(f"/sbin/swapon '{fileName}'")
		self.console.eBatch(commands, creataSwapFileCallback, debug=True)

	def createSwapFile(self, callback):
		def getPathMountData(path):
			mounts = fileReadLines("/proc/mounts", [], source=MODULE_NAME)
			print(f"[WizardStart] getPathMountData DEBUG: path={path}.")
			for mount in mounts:
				data = mount.split()
				if data[MOUNT_DEVICE] == path:
					status = stat(data[MOUNT_MOUNTPOINT])
					return (data[MOUNT_MOUNTPOINT], status, data)
			return None

		def isSwapActive(path):
			swaps = fileReadLines("/proc/swaps", default=[], source=MODULE_NAME)
			for line in swaps[1:]:
				parts = line.split()
				if parts and parts[0] == path:
					return True
			return False

		def creataSwapFileCallback(result=None, retVal=None, extraArgs=None):
			print(f"[WizardStart] createSwapFile callback DEBUG: retVal={retVal}, result={result}")
			if retVal not in (0, None) and not isSwapActive(fileName):
				self.session.open(MessageBox, _("Creating or activating the swap file failed.\n\n%s") % (result or ""), type=MessageBox.TYPE_ERROR)
				return
			if callback and callable(callback):
				callback()

		print(f"[WizardStart] DEBUG createSwapFile: {self.swapDevice}")
		fileName = "/.swap/swapfile"
		path = self.deviceData[self.swapDevice][0]
		self.mountData = getPathMountData(path)
		if self.mountData:
			fstab = fileReadLines("/etc/fstab", default=[], source=MODULE_NAME)
			print("[WizardStart] fstabUpdate DEBUG: Starting fstab:\n%s" % "\n".join(fstab))
			fstabNew = [line for line in fstab if "swap" not in line]
			mountData = self.mountData[2]
			line = " ".join((f"UUID={self.swapDevice}", "/.swap", mountData[MOUNT_FILESYSTEM], "defaults", "0", "0"))
			fstabNew.append(line)
			fstabNew.append(f"{fileName} swap swap defaults 0 0")
			fstabNew.append("")
			fileWriteLines("/etc/fstab", "\n".join(fstabNew), source=MODULE_NAME)
			print("[WizardStart] fstabUpdate DEBUG: Ending fstab:\n%s" % "\n".join(fstabNew))
			makedirs("/.swap", mode=0o755, exist_ok=True)
			if isSwapActive(fileName):
				print("[WizardStart] DEBUG: Swap already active, skipping swapon.")
				if callback and callable(callback):
					callback()
				return
			commands = []
			commands.append("/bin/mount -a")
			commands.append(f"/bin/dd if=/dev/zero of='{fileName}' bs=1024 count=131072 2>/dev/null")  # Use 128 MB because creation of bigger swap is very slow.
			commands.append(f"/bin/chmod 600 '{fileName}'")
			commands.append(f"/sbin/mkswap '{fileName}'")
			commands.append(f"/sbin/swapon '{fileName}'")
			self.console.eBatch(commands, creataSwapFileCallback, debug=True)
		else:
			self.session.open(MessageBox, _("No valid mount for '%s' found!") % path, type=MessageBox.TYPE_ERROR)

	def swapDeviceList(self):  # Called by startwizard.xml.
		choiceList = []
		for deviceID, deviceData in self.deviceData.items():
			choiceList.append((f"{deviceData[1]} ({deviceData[0]})", deviceID))
		print(f"[WizardStart] DEBUG swapDeviceList: {str(choiceList)}")

		if len(choiceList) == 0:
			choiceList.append((_("No valid device detected - Press OK"), "."))
		return choiceList

	def swapDeviceSelectionMade(self, index):  # Called by startwizard.xml.
		print(f"[WizardStart] swapDeviceSelectionMade DEBUG: index='{index}'.")
		self.swapDeviceIndex = index

	def swapDeviceSelectionMoved(self):  # Called by startwizard.xml.
		print(f"[WizardStart] DEBUG swapDeviceSelectionMoved: {self.selection}")
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

		print("[WizardStart] DEBUG readSwapDevices uuids", uuids)

		for (name, hdd) in harddiskmanager.HDDList():
			uuid, device = uuids.get(hdd.device, (None, None))
			if uuid:
				self.deviceData[uuid] = (device, name)

		print(f"[WizardStart] DEBUG readSwapDevicesCallback: {str(self.deviceData)}")
		if callback and callable(callback):
			callback()

	def getFreeMemory(self):
		memInfo = fileReadLines("/proc/meminfo", source=MODULE_NAME)
		return int([line for line in memInfo if "MemFree" in line][0].split(":")[1].strip().split(maxsplit=1)[0]) // 1024

	def isFlashExpanderActive(self):
		return isdir(join(f"/{EXPANDER_MOUNT}/{EXPANDER_MOUNT}", "bin"))

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

	# ------------------------------------------------------------------
	# Network setup steps.
	#
	# nwifaceselect (adapter list) → nwconfig (NetworkAdapterSetup) → either:
	#   - LAN: poll for an IP, then skip past nwstatus straight to nwdns
	#   - WLAN, activated on save: Wi-Fi scan + connection setup, then land on
	#     nwstatus to show the result (Continue → nwdns, or Configure another
	#     interface → back to nwifaceselect)
	#   - WLAN, not activated on save: straight back to nwifaceselect
	# ------------------------------------------------------------------

	def nwListInterfaces(self):
		result = []
		for interface, adapter in networkManager.adapters.items():
			result.append((f"{_("Wi-Fi") if adapter.isWiFi else _("LAN")}  ({interface})  –  {networkManager.getFriendlyAdapterDescription(interface)}", interface))
		result.append((_("Skip network setup"), "skip"))
		return result

	def nwIfaceSelected(self, value):
		self.nwSelectedIface = None if value == "skip" else value

	def nwIfaceMoved(self):  # Called on every cursor move in startwizard.xml's interface list; no-op here, subclasses may override.
		pass

	def nwAdvanceFromSelect(self):
		self.currStep = self.getStepWithID("network" if self.nwSelectedIface is None else "nwconfig")
		self.afterAsyncCode()

	def nwOpenSetup(self):
		def nwPollIp():
			def ip4Str(addr):
				joined = ".".join(str(x) for x in addr)
				return "" if joined == "0.0.0.0" else joined

			adapter = networkManager.adapters.get(self.nwSelectedIface)
			if adapter is not None:
				# Check the IP via netInfo's link state, not a raw address lookup - a stale
				# address can survive on a down interface and would look "connected" too
				# early. Same check as NetworkWiFiActivator.checkIp().
				networkManager.applyNetinfo()
				netInfo = adapter.netInfo
				ip = ip4Str(netInfo.ip)
				if netInfo.link and ip:
					self.nwIpFound = ip
					self.nwDone()
					return
			self.nwPollCount += 1
			if self.nwPollCount >= self.nwPollMaxAttempts:
				self.nwDone()
				return
			self.nwPollTimer.start(self.nwPollIntervalMs, True)

		def nwStartIpPoll():
			self.nwPollCount = 0
			self.nwIpFound = ""
			if self.nwPollTimer:
				self.nwPollTimer.stop()
			self.nwPollTimer = eTimer()
			self.nwPollTimer.callback.append(nwPollIp)
			# Check immediately instead of waiting a full interval first – activateInterface()
			# already waited for ifup/DHCP, so the IP is often already there.
			nwPollIp()

		def nwWifiFlowDone(ip=""):
			# NetworkWiFi already ran NetworkWiFiActivator (ifup + wpa_supplicant
			# + IP poll) and reports the result here, so there is nothing left to activate
			# or poll for. Show the result on the status step, same as the LAN path.
			print(f"[WizardStart] nwWifiFlowDone called, ip={ip}")
			self.nwSubFlowActive = False
			self.nwIpFound = ip
			self.nwShowStatusStep()

		def nwAdapterSetupDone(saved=False):
			# NetworkAdapterSetup.keySave() closes with (False, True); keyCancel()
			# closes with no args, so "saved" is only truthy after an actual save.
			print(f"[WizardStart] nwAdapterSetupDone: saved={saved!r}")
			# NetworkAdapterSetup.keySave() already called networkManager.save(),
			# which now applies whatever the adapter needs (ifup/ifdown, or a
			# full restart) itself based on what actually changed.
			if adapter.isWiFi:
				if saved and adapter.adapterEnabled:
					# The adapter was just activated – jump straight into the Wi-Fi
					# scan/connect flow instead of leaving the user stuck with an
					# enabled adapter and no SSID configured. Each screen in this
					# chain (scan → connection setup → activator) opens itself from
					# within the previous one's close callback, and Session.close()
					# briefly restores this Wizard as the current dialog in between
					# (see the comment in StartEnigma.Session.close()) – long enough
					# to re-fire onShown/updateValues() on the "nwconfig" step and
					# reopen NetworkAdapterSetup, which looks like an infinite loop.
					# nwSubFlowActive blocks that spurious re-entry until the whole
					# Wi-Fi flow really is done.
					self.nwSubFlowActive = True
					NetworkWiFiAddFlow.start(self.session, adapter=adapter, callback=nwWifiFlowDone)
				else:
					self.nwBackToList()
			else:
				nwStartIpPoll()

		if self.nwSubFlowActive:
			print("[WizardStart] nwOpenSetup: Spurious re-entry while Wi-Fi sub-flow is active -> ignored!")
			return

		try:
			adapter = networkManager.adapters.get(self.nwSelectedIface) if self.nwSelectedIface else None
			if adapter is None:
				self.nwDone()
				return
			self.session.openWithCallback(nwAdapterSetupDone, NetworkAdapterSetup, adapter)
			print("[WizardStart] nwOpenSetup: openWithCallback returned, updateValues_in_onShown=%s" % (self.updateValues in self.onShown))
		except Exception as err:
			print(f"[WizardStart] nwOpenSetup: EXCEPTION {err} -> nwDone")
			self.nwDone()

	def nwBackToList(self):
		self.nwSubFlowActive = False
		if self.nwPollTimer:
			self.nwPollTimer.stop()
			self.nwPollTimer = None
		# getStepWithID()/findStepByName() returns the enumerate() index (0-based),
		# one less than the step's real 1-based key in self.wizard – every other
		# caller in this framework (nwDone() below, afterAsyncCode()) adds this
		# same +1 to compensate. Omitting it here landed on the *previous* step
		# (nwconfig) instead of nwifaceselect, which re-ran nwOpenSetup() and
		# reopened NetworkAdapterSetup – looked like an infinite loop.
		self.currStep = self.getStepWithID("nwifaceselect") + 1
		self.updateValues()

	def nwShowStatusStep(self):
		self.nwSubFlowActive = False
		if self.nwPollTimer:
			self.nwPollTimer.stop()
			self.nwPollTimer = None
		# See the +1 note in nwBackToList() above – same off-by-one compensation.
		self.currStep = self.getStepWithID("nwstatus") + 1
		self.updateValues()

	def nwDone(self):
		self.nwSubFlowActive = False
		if self.nwPollTimer:
			self.nwPollTimer.stop()
			self.nwPollTimer = None
		self.currStep = self.getStepWithID("nwstatus") + 1
		self.updateValues()

	def nwShowStatus(self):
		if self.nwPollTimer:
			self.nwPollTimer.stop()
			self.nwPollTimer = None
		if self.nwIpFound:
			self["text"].setText(_("Network connected successfully.\n\nInterface: %s\nIP address: %s") % (self.nwSelectedIface or "", self.nwIpFound))
		else:
			self["text"].setText(_("No IP address was received.\n\nThe network connection could not be established."))


class WizardLanguage(Wizard, ShowRemoteControl):
	def __init__(self, session, silent=True, showSteps=False, neededTag=None):
		self.xmlfile = ["wizardlanguage.xml"]
		Wizard.__init__(self, session, showSteps=False)
		ShowRemoteControl.__init__(self)
		self.skinName = ["WizardLanguage", "WizardStart", "StartWizard"]
		self.oldLanguage = config.osd.language.value
		self.mode = "720p"
		self.modeList = [(mode[0], mode[0]) for mode in avSwitch.getModeList("HDMI")]
		self["wizard"] = Pixmap()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self.setTitle(_("Start Wizard"))
		self.resolutionTimer = eTimer()
		self.resolutionTimer.callback.append(self.resolutionTimeout)
		preferred = ["720p"]  # Only offer 720p - some TVs report broken EDID info, so auto-detection isn't reliable.
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
		print(f"[WizardLanguage] DEBUG setMode {self.mode}")
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


# See RestoreSettings in StartEnigma.py (around line 528) for how these wizards get run.
if config.misc.firstrun.value:
	wizardManager.registerWizard(WizardLanguage, config.misc.wizardLanguageEnabled.value, priority=0)
wizardManager.registerWizard(WizardVideo, config.misc.videowizardenabled.value, priority=1)
# wizardManager.registerWizard(LocaleWizard, config.misc.languageselected.value, priority=2)
# Priorities 8, 9, 25 are taken by wizards defined elsewhere (FPUpgrade, SystemMessage,
# NetworkWizard) - keep new priorities here clear of those.
wizardManager.registerWizard(WizardStart, config.misc.firstrun.value, priority=30)
# WizardStart itself chains into WizardInstall once its steps are done.
