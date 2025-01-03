from os import W_OK, access, listdir, makedirs, stat, system
from os.path import exists, isdir, join
from re import search

from Components.ActionMap import HelpableActionMap
from Components.config import ConfigSelection, ConfigSubsection, ConfigText, config
from Components.Console import Console
from Components.Harddisk import harddiskmanager
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import BoxInfo
from Screens.HarddiskSetup import HarddiskSelection
from Screens.LocationBox import DEFAULT_INHIBIT_DEVICES
from Screens.MessageBox import MessageBox
from Screens.Setup import Setup
from Screens.Standby import QUIT_REBOOT, TryQuitMainloop
from Tools.Directories import fileReadLine, fileReadLines, fileWriteLines

MODULE_NAME = __name__.split(".")[-1]

EXPANDER_MOUNT = ".FlashExpander"
EXPANDER_DIRECTORY = "/usr"

ACTION_SELECT = 0
ACTION_CREATE = 1
ACTION_ACTIVATE = 2
ACTION_DEACTIVATE = 3
ACTION_DELETE = 4

FSTAB_FILE_SYSTEM = 0
FSTAB_DIRECTORY = 1
FSTAB_TYPE = 2
FSTAB_OPTIONS = 3
FSTAB_DUMP = 4
FSTAB_FSCK_ORDER = 5
MAX_FSTAB = 6

MOUNT_DEVICE = 0
MOUNT_MOUNTPOINT = 1
MOUNT_FILESYSTEM = 2
MOUNT_OPTIONS = 3
MOUNT_DUMP = 4
MOUNT_FSCK_ORDER = 5
MAX_MOUNT = 6

config.flashExpander = ConfigSubsection()
config.flashExpander.location = ConfigSelection(default=None, choices=[(None, _("<Flash expander inactive>"))])
config.flashExpander.device = ConfigText(default="")


class FlashExpander(Setup):
	def __init__(self, session):
		def getGreenHelpText():
			return {
				ACTION_SELECT: _("Select a device to use as the flash expander"),
				ACTION_CREATE: _("Create the flash expander in the selected device"),
				ACTION_ACTIVATE: _("Activate the flash expander, save all changed settings and exit"),
				ACTION_DEACTIVATE: _("Deactivate the flash expander in the selected device"),
				ACTION_DELETE: _("Delete the flash expander in the selected device"),
			}.get(self.green, _("Help text uninitialized"))

		Setup.__init__(self, session=session, setup="FlashExpander")
		self["key_yellow"] = StaticText(_("Format Disk"))
		self["fullUIActions"] = HelpableActionMap(self, ["CancelSaveActions"], {
			"cancel": (self.keyCancel, _("Cancel any changed settings and exit")),
			"close": (self.closeRecursive, _("Cancel any changed settings and exit all menus")),
			# "save": (self.keySave, _("Save all changed settings and exit"))
		}, prio=0, description=_("Common Setup Actions"))  # Override the ConfigList "fullUIActions" action map so that we can control the GREEN button here.
		self["actions"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyGreen, getGreenHelpText),
			"yellow": (self.keyFormat, _("Format Disk"))
		}, prio=-1, description=_("Flash Expander Actions"))
		choiceList = [config.flashExpander.location.getSelectionList()[0]]
		if config.flashExpander.location.saved_value:
			choiceList.append((config.flashExpander.location.saved_value, config.flashExpander.location.saved_value))
			value = config.flashExpander.location.saved_value
		else:
			value = None
		config.flashExpander.location.setSelectionList(default=value, choices=choiceList)
		config.flashExpander.location.value = value
		self.console = Console()
		self.status = None
		self.active = None
		self.deviceData = {}
		self.mountData = None
		self.green = ACTION_SELECT
		self.onClose.append(self.__onClose)

	def __onClose(self):
		harddiskmanager.on_partition_list_change.remove(self.partitionListChanged)

	def partitionListChanged(self, action, device):
		self.readDevices()

	def layoutFinished(self):
		Setup.layoutFinished(self)
		self.readDevices()
		harddiskmanager.on_partition_list_change.append(self.partitionListChanged)

	def selectionChanged(self):
		Setup.selectionChanged(self)
		self.updateStatus()

	def changedEntry(self):
		Setup.changedEntry(self)
		self.updateStatus()

	def keyCancel(self):
		config.flashExpander.location.setSelectionList(default=None, choices=[config.flashExpander.location.getSelectionList()[0]])
		config.flashExpander.location.value = None
		config.flashExpander.device.value = ""
		Setup.keyCancel(self)

	def closeRecursive(self):
		config.flashExpander.location.setSelectionList(default=None, choices=[config.flashExpander.location.getSelectionList()[0]])
		config.flashExpander.location.value = None
		config.flashExpander.device.value = ""
		Setup.closeRecursive(self)

	def updateStatus(self, footnote=None):
		def fstabCheck():
			found = False
			fstab = fileReadLines("/etc/fstab", default=[], source=MODULE_NAME)
			for line in fstab:
				if line.startswith("#") or line.strip() == "":
					continue
				if EXPANDER_DIRECTORY in line:
					found = True
					break
			print("[FlashExpander] fstabCheck DEBUG: Flash expander fstab entry%s found." % ("" if found else " not"))
			return found

		def mountCheck():
			found = False
			mounts = fileReadLines("/proc/mounts", default=[], source=MODULE_NAME)
			for index, line in enumerate(mounts, start=1):
				if line.startswith("#") or line.strip() == "":
					continue
				data = line.split()
				if data[MOUNT_MOUNTPOINT] == EXPANDER_DIRECTORY:
					found = True
					break
			print("[FlashExpander] mountCheck DEBUG: Flash expander mount entry%s found." % ("" if found else " not"))
			return found

		self.status = footnote
		self.active = mountCheck()
		if not footnote:
			enabled = _("Enabled") if fstabCheck() else _("Disabled")
			activeMsg = _("Active") if self.active else _("Inactive")
			footnote = _("FlashExpander on boot is '%s'.  FlashExpander status is '%s'.") % (enabled, activeMsg)
		self.setFootnote(footnote)
		if config.flashExpander.device.value:
			if isdir(join("/%s/%s" % (EXPANDER_MOUNT, EXPANDER_MOUNT), "bin")):
				self.green = ACTION_DEACTIVATE if self.active else ACTION_DELETE
			else:
				self.green = ACTION_CREATE
		else:
			self.green = ACTION_SELECT
		self["key_green"].setText({
			ACTION_SELECT: _("Select Device"),
			ACTION_CREATE: _("Create Expander"),
			ACTION_ACTIVATE: _("Activate Expander"),
			ACTION_DEACTIVATE: _("Deactivate Expander"),
			ACTION_DELETE: _("Delete Expander")
		}.get(self.green, _("Invalid")))

	def keySelect(self):
		if self.getCurrentItem() == config.flashExpander.location:
			self.showDeviceSelection()
		else:
			Setup.keySelect(self)

	def keySelectCallback(self, deviceId):
		def getPathMountData(path):
			mounts = fileReadLines("/proc/mounts", [], source=MODULE_NAME)
			print(f"[FlashExpander] getPathMountData DEBUG: path={path}.")
			for mount in mounts:
				data = mount.split()
				if data[MOUNT_DEVICE] == path:
					status = stat(data[MOUNT_MOUNTPOINT])
					return (data[MOUNT_MOUNTPOINT], status, data)
			return None

		if deviceId:
			print(f"[FlashExpander] keySelectCallback DEBUG: deviceId={deviceId}.")
			config.flashExpander.device.value = deviceId
			locations = config.flashExpander.location.getSelectionList()
			path = self.deviceData[deviceId][0]
			self.mountData = getPathMountData(path)
			if self.mountData:
				mountPoint = self.mountData[0]
				mountStat = self.mountData[1]
				print("[FlashExpander] keySelectCallback DEBUG: mountData=%s." % str(self.mountData))
				if not isdir(mountPoint):
					footnote = _("Directory '%s' does not exist!") % mountPoint
				elif mountStat.st_dev in DEFAULT_INHIBIT_DEVICES:
					footnote = _("Flash directory '%s' not allowed!") % mountPoint
				elif not access(mountPoint, W_OK):
					footnote = _("Directory '%s' not writable!") % mountPoint
	#			elif fstype and not fstype.startswith("ext"):
	#				footnote = _("File system type '%s' not permitted!") % fstype
				else:
					footnote = None
			else:
				footnote = _("No valid mount for '%s' found!") % path
			print("[FlashExpander] keySelectCallback DEBUG: footnote=%s" % footnote)
			if not footnote:
				if (path, path) not in locations:
					locations.append((path, path))
					config.flashExpander.location.setSelectionList(default=None, choices=locations)
					config.flashExpander.location.value = path
					self["config"].invalidateCurrent()
				config.flashExpander.device.value = deviceId
			self.updateStatus(footnote)

	def showDeviceSelection(self):
		def readDevicesCallback():
			choiceList = [
				(_("Cancel"), "")
			]
			for deviceID, deviceData in self.deviceData.items():
				choiceList.append((f"{deviceData[1]} ({deviceData[0]})", deviceID))
			if self.active:
				message = _("Please select the device where the flash expander '/usr' directory should disabled.")
			else:
				message = _("Please select the device where the flash expander '/usr' directory should created.")

			self.session.openWithCallback(self.keySelectCallback, MessageBox, text=message, list=choiceList, windowTitle=self.getTitle())

		self.readDevices(readDevicesCallback)

	def keyGreen(self):
		def activateCallback(output, retVal, extraArgs):
			def mountCallback(output, retVal, extraArgs):
				system("sync")
				if isdir(join(f"/{EXPANDER_MOUNT}/{EXPANDER_MOUNT}", "bin")):
					config.flashExpander.device.save()
					config.flashExpander.location.save()
					Setup.keySave(self)
				else:
					self.session.open(MessageBox, _("Error: mount not successful!"), MessageBox.TYPE_ERROR, windowTitle=self.getTitle())

			self.messageBox.close(retVal == 0)
			if retVal:
				self.session.open(MessageBox, _("Error: The copy was unsuccessful!"), MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
				self.updateStatus()
			else:
				self.fstabUpdate(True)
				makedirs("/%s" % EXPANDER_MOUNT, mode=0o755, exist_ok=True)
				self.console.ePopen(["/bin/busybox", "mount", "-a"], callback=mountCallback)

		def deactivateCallback(answer):
			if answer:
				self.fstabUpdate(False)
				config.flashExpander.location.setSelectionList(default=None, choices=[config.flashExpander.location.getSelectionList()[0]])
				config.flashExpander.location.value = None
				config.flashExpander.device.value = ""
				config.flashExpander.device.save()
				for notifier in self.onSave:
					notifier()
				self.saveAll()
				self.session.open(TryQuitMainloop, retvalue=QUIT_REBOOT)
				self.close()

		def copyFlashdata():
			makedirs(usrDirectory, exist_ok=True)
			self.console.ePopen(["/bin/busybox", "cp", "-af", f"{EXPANDER_DIRECTORY}/.", usrDirectory], callback=activateCallback)
			self.messageBox = self.session.open(MessageBox, "%s\n\n%s" % (usrDirectory, _("Please wait, flash memory is being copied to this flash expander. This could take a number of minutes to complete.")), MessageBox.TYPE_INFO, enable_input=False, windowTitle=self.getTitle())

		def deleteCallback(answer):
			def deleteMessageCallback(output, retVal, extraArgs):
				self.messageBox.close(retVal == 0)
				if retVal:
					self.session.open(MessageBox, _("Error: The delete was unsuccessful!"), MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
				self.updateStatus()

			if answer:
				self.console.ePopen(["/bin/busybox", "rm", "-r", usrDirectory], callback=deleteMessageCallback)
				self.messageBox = self.session.open(MessageBox, "%s\n\n%s" % (usrDirectory, _("Please wait, copy of flash memory is being deleted. This could take a few minutes to complete.")), MessageBox.TYPE_INFO, enable_input=False, windowTitle=self.getTitle())

		if config.flashExpander.device.value:
			if not self.mountData:  # Reselect the device
				self.showDeviceSelection()
				return

			usrDirectory = join(self.mountData[0], EXPANDER_MOUNT)
			if exists(usrDirectory):
				if self.active:
					self.session.openWithCallback(deactivateCallback, MessageBox, "%s\n\n%s" % (usrDirectory, _("Do you want to deactivate this flash expander?")), MessageBox.TYPE_YESNO, default=False, windowTitle=self.getTitle())
				else:
					self.session.openWithCallback(deleteCallback, MessageBox, "%s\n\n%s" % (usrDirectory, _("Do you want to delete this flash expander directory?")), MessageBox.TYPE_YESNO, default=False, windowTitle=self.getTitle())
			else:
				copyFlashdata()
		else:
			self.showDeviceSelection()

	def keyFormat(self):
		def formatCallback():
			harddiskmanager.enumerateBlockDevices()
			self.readDevices()
		self.session.openWithCallback(formatCallback, HarddiskSelection)

	def fstabUpdate(self, expand):
		# Also look for the mount point in case the disk is mounted in a way not currently detected.
		mountDevice = config.flashExpander.device.value
		if not mountDevice:  # DEBUG!
			return
		flashExpanderToken = f"UUID={mountDevice}"
		fstab = []
		fstabnew = []
		fstab = fileReadLines("/etc/fstab", default=fstab, source=MODULE_NAME)
		for line in fstab:
			if EXPANDER_MOUNT in line:
				continue
			fstabnew.append(line)
		print("[FlashExpander] fstabUpdate DEBUG: Starting fstab:\n%s" % "\n".join(fstab))
		if expand:
			mountData = self.mountData[2]
			line = " ".join((flashExpanderToken, f"/{EXPANDER_MOUNT}", mountData[MOUNT_FILESYSTEM], "defaults", "0", "0"))
			fstabnew.append(line)
			fstabnew.append(f"/{EXPANDER_MOUNT}/{EXPANDER_MOUNT} {EXPANDER_DIRECTORY} none  bind 0 0")
		fstabnew.append("")
		fileWriteLines("/etc/fstab", "\n".join(fstabnew), source=MODULE_NAME)
		print("[FlashExpander] fstabUpdate DEBUG: Ending fstab:\n%s" % "\n".join(fstabnew))

	def readDevices(self, callback=None):
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

		print("[FlashExpander] DEBUG: uuids -> ", uuids)

		for (name, hdd) in harddiskmanager.HDDList():
			print("[FlashExpander] DEBUG: HDDList", hdd.device, hdd.dev_path)
			uuid, device = uuids.get(hdd.device, (None, None))
			if uuid:
				self.deviceData[uuid] = (device, name)

		print("[FlashExpander] DEBUG: self.deviceData", self.deviceData)
		self.updateStatus()
		if callback and callable(callback):
			callback()
