from os import mkdir, remove
from os.path import exists, isfile

from enigma import eHotplugSocket, getDeviceDB, eTimer

from Components.config import config
from Components.Console import Console
from Components.Harddisk import harddiskmanager
from Components.Storage import EXPANDER_MOUNT, cleanMediaDirs
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import ModalMessageBox
from Tools.Directories import fileReadLines, fileWriteLines
from Tools.Conversions import scaleNumber

# globals
hotplugNotifier = []
audiocd = False


def AudiocdAdded():
	global audiocd
	return audiocd


def autostart(reason, **kwargs):
	if reason == 0:
		print("[Hotplug] Starting hotplug handler.")
		cleanMediaDirs()  # Initial cleanup
		eHotplugSocket.getInstance().dataReceived.get().append(hotPlugManager.processRawData)


class HotPlugManager:
	def __init__(self):
		self.addTimer = eTimer()
		self.addTimer.callback.append(self.processAddDevice)
		self.removeTimer = eTimer()
		self.removeTimer.callback.append(self.processRemoveDevice)
		self.deviceData = []
		self.addedDevice = []
		self.callMount = False
		self.debug = False

		def debugStorageChanged(configElement):
			self.debug = configElement.value
		config.crash.debugStorage.addNotifier(debugStorageChanged)

	def processRawData(self, raw):
		eventData = {}
		if "\n" in raw:
			data = raw.rstrip("\0\n").split("\n")
			eventData["mode"] = 1
		else:
			data = raw.split("\0")[:-1]
			eventData["mode"] = 0
		for values in data:
			if "=" in values:
				variable, value = values.split("=", 1)
				eventData[variable] = value
		if data and eventData:
			self.processHotplugData(eventData)

	def processAddDevice(self):
		self.addTimer.stop()
		if self.deviceData:
			eventData = self.deviceData.pop()
			DEVPATH = eventData.get("DEVPATH")
			DEVNAME = eventData.get("DEVNAME")
			ID_MODEL = eventData.get("ID_MODEL")
			if eventData["DEVTYPE"] == "disk":
				harddiskmanager.addHotplugPartition(DEVNAME, DEVPATH, ID_MODEL)
				self.addTimer.start(100)
				return

			ID_FS_TYPE = "auto"  # eventData.get("ID_FS_TYPE")
			# ID_BUS = eventData.get("ID_BUS")
			ID_FS_UUID = eventData.get("ID_FS_UUID")
			ID_PART_ENTRY_SIZE = int(eventData.get("ID_PART_ENTRY_SIZE", 0))
			notFound = True
			mounts = [(x[0], x[1].replace("\\040", " ")) for x in (line.split() for line in fileReadLines("/proc/mounts", default=[])) if len(x) > 1]
			mountPoints = [x[1] for x in mounts]
			fstabEntries = [x for x in (line.split() for line in fileReadLines("/etc/fstab", default=[])) if len(x) > 1 and not x[0].startswith("#")]
			usedMountPoints = mountPoints + [x[1] for x in fstabEntries]
			mountPoint = "/media/usb"
			mountPointDevice = DEVNAME.replace("/dev/", "/media/")
			mountPointHdd = None if "/media/hdd" in usedMountPoints else "/media/hdd"
			knownDevices = fileReadLines("/etc/udev/known_devices", default=[])
			knownDevice = ""
			nr = 1
			while mountPoint in usedMountPoints:
				nr += 1
				mountPoint = f"/media/usb{nr}"

			for device, point in mounts:
				if device == DEVNAME and point != mountPointDevice:
					print(f"[Hotplug] device '{DEVNAME}' found in mounts -> {point}")
					notFound = False
					break

			if notFound and knownDevices:
				for device in knownDevices:
					deviceData = device.split(":")
					if len(deviceData) == 2 and deviceData[0] == ID_FS_UUID:
						if self.debug:
							print("[Hotplug] UUID found in known_devices")
						knownDevice = deviceData[1]
						notFound = knownDevice != "None"  # Ignore this device
						break

			if notFound and ID_FS_UUID:
				fstabDevice = [x[1] for x in fstabEntries if x[0] == f"UUID={ID_FS_UUID}" and EXPANDER_MOUNT not in x[1]]
				if fstabDevice and fstabDevice[0] not in mountPoints:  # Check if device is already in fstab and if the mountpoint not used
					if not exists(fstabDevice[0]):
						mkdir(fstabDevice[0], 0o755)
					self.callMount = True
					notFound = False

			if notFound and mountPointHdd and ID_FS_UUID:  # If device is the first and /media/hdd not mounted
				knownDevices.append(f"{ID_FS_UUID}:{mountPointHdd}")
				fileWriteLines("/etc/udev/known_devices", knownDevices)
				fstab = fileReadLines("/etc/fstab", default=[])
				newFstab = [x for x in fstab if f"UUID={ID_FS_UUID}" not in x]
				newFstab.append(f"UUID={ID_FS_UUID} {mountPointHdd} {ID_FS_TYPE} defaults 0 0")
				fileWriteLines("/etc/fstab", newFstab)
				if not exists(mountPointHdd):
					mkdir(mountPointHdd, 0o755)
				self.callMount = True
				notFound = False

			if notFound:
				description = ""
				for physdevprefix, pdescription in list(getDeviceDB().items()):
					if DEVPATH.startswith(physdevprefix):
						description = f"\n{_(pdescription)}"

				text = f"{_('A new storage device has been connected:')}\n{ID_MODEL} - ({scaleNumber(ID_PART_ENTRY_SIZE * 512, format='%.1f')})\n{description}"

				def newDeviceCallback(answer):
					if answer:
						knownDevice = None
						fstab = fileReadLines("/etc/fstab", default=[])
						if answer in (2, 3) and not exists(mountPoint):
							mkdir(mountPoint, 0o755)
						if answer == 4 and not exists(mountPointHdd):
							mkdir(mountPointHdd, 0o755)
						if answer == 1:
							knownDevice = "None"
						elif answer == 2:
							Console().ePopen(f"/bin/mount -t {ID_FS_TYPE} {DEVNAME} {mountPoint}")
						elif answer == 3:
							knownDevice = mountPoint
							newFstab = [x for x in fstab if f"UUID={ID_FS_UUID}" not in x]
							newFstab.append(f"UUID={ID_FS_UUID} {mountPoint} {ID_FS_TYPE} defaults 0 0")
							fileWriteLines("/etc/fstab", newFstab)
							self.callMount = True
						elif answer == 4:
							knownDevice = mountPointHdd
							newFstab = [x for x in fstab if f"UUID={ID_FS_UUID}" not in x]
							newFstab.append(f"UUID={ID_FS_UUID} {mountPointHdd} {ID_FS_TYPE} defaults 0 0")
							fileWriteLines("/etc/fstab", newFstab)
							self.callMount = True
						elif answer == 5:
							knownDevice = mountPointDevice
							newFstab = [x for x in fstab if f"UUID={ID_FS_UUID}" not in x]
							newFstab.append(f"UUID={ID_FS_UUID} {mountPointDevice} {ID_FS_TYPE} defaults 0 0")
							fileWriteLines("/etc/fstab", newFstab)
							self.callMount = True
						if knownDevice:
							knownEntry = f"{ID_FS_UUID}:{knownDevice}"
							for index, device in enumerate(knownDevices):
								if device.startswith(f"{ID_FS_UUID}:"):
									knownDevices[index] = knownEntry
									break
							else:
								knownDevices.append(knownEntry)
							fileWriteLines("/etc/udev/known_devices", knownDevices)
					self.addedDevice.append((DEVNAME, DEVPATH, ID_MODEL))
					self.addTimer.start(1000)

				default = 3
				choiceList = [
					(_("Do nothing"), 0),
					(_("Permanently ignore this device"), 1),
					(_("Temporarily mount as %s") % mountPoint, 2),
					(_("Permanently mount as %s") % mountPoint, 3)
				]
				if mountPointHdd:
					default = 4
					choiceList.append(
						(_("Permanently mount as %s") % mountPointHdd, 4),
					)
				choiceList.append(
					(_("Permanently mount as %s") % mountPointDevice, 5),
				)
				ModalMessageBox.instance.showMessageBox(text=text, list=choiceList, default=default, windowTitle=_("New Storage Device"), callback=newDeviceCallback)
			else:
				self.addedDevice.append((DEVNAME, DEVPATH, ID_MODEL))
				self.addTimer.start(1000)
		elif self.addedDevice:
			if self.callMount:
				self.callMount = False
				Console().ePopen("/bin/mount -a")  # Without a callback this blocks, so the mount point is ready below.
			addedDevice = self.addedDevice
			self.addedDevice = []
			for device, physicalDevicePath, model in addedDevice:
				harddiskmanager.addHotplugPartition(device, physicalDevicePath, model=model)

	def processRemoveDevice(self):
		self.removeTimer.stop()
		cleanMediaDirs()

	def processHotplugData(self, eventData):
		mode = eventData.get("mode")
		if self.debug:
			print("[Hotplug] DEBUG: ", eventData)
		action = eventData.get("ACTION")
		if mode == 1 and eventData.get("MODE", "") != "CD":
			if action == "dab-sdr-add":
				device = eventData.get("DEVPATH", "").split("/")[-1]
				for callback in hotplugNotifier[:]:
					try:
						callback(device, action)
					except AttributeError:
						hotplugNotifier.remove(callback)
			elif action == "add":
				self.addTimer.stop()
				ID_TYPE = eventData.get("ID_TYPE")
				DEVTYPE = eventData.get("DEVTYPE")
				if ID_TYPE == "disk" and DEVTYPE in ("partition", "disk"):
					self.deviceData.append(eventData)
					self.addTimer.start(1000)

			elif action == "remove":
				ID_TYPE = eventData.get("ID_TYPE")
				DEVTYPE = eventData.get("DEVTYPE")
				# ID_FS_UUID = eventData.get("ID_FS_UUID")
				if ID_TYPE == "disk" and DEVTYPE in ("partition", "disk"):
					device = eventData.get("DEVNAME")
					harddiskmanager.removeHotplugPartition(device)
					self.removeTimer.stop()
					self.removeTimer.start(2000)
			elif action == "ifup":
				interface = eventData.get("INTERFACE")  # noqa F841
			elif action == "ifdown":
				interface = eventData.get("INTERFACE")  # noqa F841
			elif action == "online":
				state = eventData.get("STATE")  # noqa F841

		else:
			device = eventData.get("DEVPATH", "").split("/")[-1]
			physicalDevicePath = eventData.get("PHYSDEVPATH")
			mediaState = eventData.get("X_E2_MEDIA_STATUS")
			global audiocd

			if action == "add":
				error, blacklisted, removable, is_cdrom, partitions, medium_found = harddiskmanager.addHotplugPartition(device, physicalDevicePath)
			elif action == "remove":
				harddiskmanager.removeHotplugPartition(device)
			elif action == "audiocdadd":
				audiocd = True
				mediaState = "audiocd"
				error, blacklisted, removable, is_cdrom, partitions, medium_found = harddiskmanager.addHotplugAudiocd(device, physicalDevicePath)
				print("[Hotplug] Adding AudioCD.")
			elif action == "audiocdremove":
				audiocd = False
				file = []
				# Removing the invalid playlist.e2pls If its still the audio cd's list
				# Default setting is to save last playlist on closing Mediaplayer.
				# If audio cd is removed after Mediaplayer was closed,
				# the playlist remains in if no other media was played.
				if isfile("/etc/enigma2/playlist.e2pls"):
					with open("/etc/enigma2/playlist.e2pls") as f:
						file = f.readline().strip()
				if file and ".cda" in file:
					try:
						remove("/etc/enigma2/playlist.e2pls")
					except OSError:
						pass
				harddiskmanager.removeHotplugPartition(device)
				print("[Hotplug] Removing AudioCD.")
			elif mediaState is not None:
				if mediaState == "1":
					harddiskmanager.removeHotplugPartition(device)
					harddiskmanager.addHotplugPartition(device, physicalDevicePath)
				elif mediaState == "0":
					harddiskmanager.removeHotplugPartition(device)

			for callback in hotplugNotifier:
				try:
					callback(device, action or mediaState)
				except AttributeError:
					hotplugNotifier.remove(callback)


hotPlugManager = HotPlugManager()


def Plugins(**kwargs):
	return PluginDescriptor(name="Hotplug", description="Hotplug handler.", where=PluginDescriptor.WHERE_AUTOSTART, needsRestart=True, fnc=autostart)
