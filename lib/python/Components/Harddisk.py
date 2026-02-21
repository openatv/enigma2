from glob import glob
from os import listdir, lstat, mkdir, remove, statvfs, system, walk
from os.path import abspath, dirname, exists, isfile, islink, ismount, join, realpath
from re import search, sub
from time import sleep, time

from enigma import getDeviceDB, eTimer

from Components.SystemInfo import BoxInfo
from Components.Console import Console
from Tools.Directories import fileReadLines, fileReadLine, fileWriteLines
from Tools.CList import CList

MODEL = BoxInfo.getItem("model")
MODULE_NAME = __name__.split(".")[-1]


def checkFstabReservesMediaHDD(lines):
	for line in lines:
		line = (line or "").strip()
		if not line or line.startswith("#"):
			continue
		parts = line.split()
		if len(parts) < 3:
			continue
		spec, mnt, fstype = parts[0], parts[1], parts[2].lower()
		if mnt != "/media/hdd":
			continue
		if fstype in ("cifs", "nfs", "nfs4", "sshfs", "fuse.sshfs"):
			return True
		if spec.startswith("//") or (":/" in spec):
			return True
	return False

def readFile(filename):
	with open(filename) as fd:
		data = fd.read().strip()
	return data

# Unused!
# def getextdevices(ext):
# 	cmd = f"blkid -t TYPE={ext} -o device"
# 	extdevices = popen(cmd).read().replace("\n", ",").rstrip(",")
# 	return None if extdevices == "" else [x.strip() for x in extdevices.split(",")]


def getProcMountsNew():
	lines = fileReadLines("/proc/mounts", default=[], source=MODULE_NAME)
	result = []
	for line in [x for x in lines if x and x.startswith("/dev/")]:
		# Replace encoded space (\040) and newline (\012) characters with actual space and newline
		result.append([s.replace("\\040", " ").replace("\\012", "\n") for s in line.strip(" \n").split(" ")])
	return result


def getProcMounts():
	try:
		mounts = open("/proc/mounts")
		result = []
		tmp = [line.strip().split(" ") for line in mounts]
		mounts.close()
		for item in tmp:
			item[1] = item[1].replace("\\040", " ")  # Spaces are encoded as \040 in mounts.
			result.append(item)
		return result
	except OSError as err:
		print(f"[Harddisk] Error {err.errno}: Failed to open '/proc/mounts'!  ({err.strerror})")
		return []


def findMountPoint(path):
	"""Example: findMountPoint("/media/hdd/some/file") returns "/media/hdd\""""
	path = abspath(path)
	while not ismount(path):
		path = dirname(path)
	return path


def getFolderSize(path):
	if islink(path):
		return (lstat(path).st_size, 0)
	if isfile(path):
		st = lstat(path)
		return (st.st_size, st.st_blocks * 512)
	total_bytes = 0
	have = set()
	for dirpath, dirnames, filenames in walk(path):
		total_bytes += lstat(dirpath).st_blocks * 512
		for f in filenames:
			fp = join(dirpath, f)
			if islink(fp):
				continue
			st = lstat(fp)
			if st.st_ino in have:
				continue  # Skip hard links which were already counted.
			have.add(st.st_ino)
			total_bytes += st.st_blocks * 512
		# for d in dirnames:
		#	dp = join(dirpath, d)
	return total_bytes


def Freespace(dev):
	try:
		statdev = statvfs(dev)
		space = (statdev.f_bavail * statdev.f_frsize) / 1024
	except OSError:
		space = 0
	return space


class Harddisk:
	def __init__(self, device, removable=False, model=None):
		self.device = device
		self.type = 0  # TODO maybe no longer needed / DEVTYPE_UDEV
		self.max_idle_time = 0
		self.idle_running = False
		self.last_access = time()
		self.last_stat = 0
		self.timer = None
		self.is_sleeping = False
		self.dev_path = ""
		self.disk_path = ""
		self.mount_path = None
		self.mount_device = None
		self.phys_path = realpath(self.sysfsPath("device"))
		self.dev_path = join("/dev", self.device)
		self.disk_path = self.dev_path
		self.modelName = model
		print(f"[Harddisk] New Harddisk '{self.device}' -> '{self.dev_path}'.")
		if not removable:
			self.startIdle()

	def __lt__(self, ob):
		return self.device < ob.device

	def partitionPath(self, n):
		return join(self.dev_path, "part{n}")

	def sysfsPath(self, filename):
		return join("/sys/block/", self.device, filename)

	def stop(self):
		if self.timer:
			self.timer.stop()
			self.timer.callback.remove(self.runIdle)

	def bus(self):
		ret = _("External")
		internal = False
		if "sdhci" in self.phys_path:
			ret += " (SD/MMC)"
		elif MODEL == "sf8008":
			internal = ("usb1/1-1/1-1.1/1-1.1:1.0" in self.phys_path) or ("usb1/1-1/1-1.4/1-1.4:1.0" in self.phys_path)
		else:
			internal = ("pci" in self.phys_path or "ahci" in self.phys_path)
		return _("Internal") if internal else ret

	def diskSize(self):
		cap = 0
		try:
			line = readFile(self.sysfsPath("size"))
			cap = int(line)
		except Exception:
			dev = self.findMount()
			if dev:
				stat = statvfs(dev)
				cap = int(stat.f_blocks * stat.f_bsize)
				return cap // 1000 // 1000
			else:
				return cap
		return cap // 1000 * 512 // 1000

	def capacity(self):
		cap = self.diskSize()
		if cap == 0:
			return ""
		if cap < 1000:
			return _("%03d MB") % cap  # IanSav: Does this need to be translated?
		return _("%d.%03d GB") % (cap // 1000, cap % 1000)

	def model(self):
		try:
			if self.modelName:
				return self.modelName
			if self.device[:2] == "hd":
				return readFile(join("/proc/ide", self.device, "model"))
			elif self.device[:2] in ("sd", "sr"):
				vendor = readFile(join(self.phys_path, "vendor"))
				model = readFile(join(self.phys_path, "model"))
				return f"{vendor}  ({model})"
			elif self.device.startswith("mmcblk"):
				return readFile(self.sysfsPath("device/name"))
			else:
				raise Exception("No hdX, sdX, srX or mmcX")
		except Exception as err:
			print(f"[Harddisk] Error: Failed to get model for {self.device}!  ({err})")
			return "-?-"

	def free(self):
		dev = self.findMount()
		if dev:
			try:
				stat = statvfs(dev)
				return int((stat.f_bfree / 1000) * (stat.f_bsize / 1024))
			except Exception:
				pass
		return -1

	def numPartitions(self):
		numPart = -1
		try:
			devdir = listdir("/dev")
		except OSError:
			return -1
		for filename in devdir:
			if filename.startswith(self.device):
				numPart += 1
		return numPart

	def mountDevice(self):
		for parts in getProcMountsNew():
			if realpath(parts[0]).startswith(self.dev_path):
				self.mount_device = parts[0]
				self.mount_path = parts[1]
				return parts[1]

	def enumMountDevices(self):
		for parts in getProcMountsNew():
			if realpath(parts[0]).startswith(self.dev_path):
				yield parts[1]

	def findMount(self):
		if self.mount_path is None:
			return self.mountDevice()
		return self.mount_path

	def unmount(self):
		dev = self.mountDevice()
		if dev is None:  # Not mounted, return OK.
			return 0
		cmd = f"umount {dev}"
		print(f"[Harddisk] Command: '{cmd}'.")
		res = system(cmd)
		return res >> 8

	def mount(self):
		if self.mount_device is None:  # Try mounting through fstab first.
			dev = self.partitionPath("1")
		else:  # If previously mounted, use the same spot.
			dev = self.mount_device
		try:
			fstab = open("/etc/fstab")
			lines = fstab.readlines()
			fstab.close()
		except OSError:
			return -1
		for line in lines:
			parts = line.strip().split(" ")
			fspath = realpath(parts[0])
			if fspath == dev:
				print(f"[Harddisk] Mounting '{fspath}'.")
				cmd = f"mount -t auto {fspath}"
				res = system(cmd)
				return res >> 8

		res = -1  # Device is not in fstab.
		res = system(f"hdparm -z {self.disk_path}")  # We can let udev do the job, re-read the partition table.
		sleep(3)  # Give udev some time to make the mount, which it will do asynchronously.
		return res >> 8

	def getDeviceDir(self):
		return self.dev_path

	def getDeviceName(self):
		return self.disk_path

	# The HDD idle poll daemon.
	# As some hard drives have a buggy standby timer, we are doing this by hand here.
	# First, we disable the hardware timer. Then, we check every now and then if
	# any access has been made to the disc. If there has been no access over a
	# specified time, we set the HDD into standby.
	#
	def readStats(self):
		if exists(f"/sys/block/{self.device}/stat"):
			with open(f"/sys/block/{self.device}/stat") as fd:
				line = fd.read()
			data = line.split(None, 5)
			return int(data[0]), int(data[4])
		else:
			return -1, -1

	def startIdle(self):
		if self.bus() == _("External"):  # Disable HDD standby timer.
			Console().ePopen(("sdparm", "sdparm", "--set=SCT=0", self.disk_path))
		else:
			Console().ePopen(("hdparm", "hdparm", "-S0", self.disk_path))
		self.timer = eTimer()
		self.timer.callback.append(self.runIdle)
		self.idle_running = True
		self.hdd_timer = False
		try:
			configsettings = readFile("/etc/enigma2/settings")
			if "config.usage.hdd_timer" in configsettings:
				self.hdd_timer = True
		except Exception:
			self.hdd_timer = False
		self.setIdleTime(self.max_idle_time)  # Kick the idle polling loop.

	def runIdle(self):
		if not self.max_idle_time:
			return
		now = time()
		idleTime = now - self.last_access
		stats = self.readStats()
		sumStats = sum(stats)
		if sumStats != self.last_stat and sumStats >= 0:  # Access.
			self.last_stat = sumStats
			self.last_access = now
			idleTime = 0
			self.is_sleeping = False
		if idleTime >= self.max_idle_time and not self.is_sleeping:
			self.setSleep()
			self.is_sleeping = True

	def setSleep(self):
		if self.bus() == _("External"):
			Console().ePopen(("sdparm", "sdparm", "--flexible", "--readonly", "--command=stop", self.disk_path))
		else:
			Console().ePopen(("hdparm", "hdparm", "-y", self.disk_path))

	def setIdleTime(self, idle):
		self.max_idle_time = idle
		if self.idle_running:
			if not idle:
				self.timer.stop()
			else:
				self.timer.start(idle * 100, False)  # Poll 10 times per period.

	def isSleeping(self):
		return self.is_sleeping


# For backward compatibility, force_mounted actually means "hotplug".
#
class Partition:
	def __init__(self, mountpoint, device=None, description="", force_mounted=False):
		self.mountpoint = mountpoint
		self.description = description
		self.force_mounted = mountpoint and force_mounted
		self.is_hotplug = force_mounted  # So far; this might change.
		self.device = device

	def __str__(self):
		return f"Partition(mountpoint={self.mountpoint},description={self.description},device={self.device})"

	def stat(self):
		if self.mountpoint:
			return statvfs(self.mountpoint)
		else:
			raise OSError(f"Device {self.device} is not mounted")

	def free(self):
		try:
			s = self.stat()
			return s.f_bavail * s.f_bsize
		except OSError:
			return None

	def total(self):
		try:
			s = self.stat()
			return s.f_blocks * s.f_bsize
		except OSError:
			return None

	def tabbedDescription(self):
		if self.mountpoint.startswith("/media/net") or self.mountpoint.startswith("/media/autofs"):
			return self.description  # Network devices have a user defined name
		return f"{self.description}\t{self.mountpoint}"

	def mounted(self, mounts=None):
		return self.mountpoint and ismount(self.mountpoint)
#		if self.mountpoint:
#			if mounts is None:
#				mounts = getProcMountsNew()
#			for parts in mounts:
#				if self.mountpoint.startswith(parts[1]):  # Use startswith so a mount not ending with "/" is also detected.
#					return True
#		return False

	def fileSystem(self, mounts=None):
		if self.mountpoint:
			if mounts is None:
				mounts = getProcMountsNew()
			for fields in mounts:
				if self.mountpoint.endswith("/") and self.mountpoint != "/":
					if join(fields[1], "") == self.mountpoint:
						return fields[2]
				else:
					if fields[1] == self.mountpoint:
						return fields[2]
		return ""


class HarddiskManager:
	def __init__(self):
		self.debug = False
		self.hdd = []
		self.cd = ""
		self.partitions = []
		self.devices_scanned_on_init = []
		self.on_partition_list_change = CList()
		self.console = Console()
		self.enumerateHotPlugDevices(self.init)

	def init(self):
		self.enumerateBlockDevices()
		self.enumerateNetworkMounts()
		p = [("/", _("Internal flash"))]  # Find stuff not detected by the enumeration.
		self.partitions.extend([Partition(mountpoint=x[0], description=x[1]) for x in p])

	def debugPrint(self, text):
		if self.debug:
			print(f"[{MODULE_NAME}] DEBUG: {text}")

	def refreshMountPoints(self):
		# Remove old mounts
		self.debugPrint("refreshMountPoints")
		for partition in self.partitions:
			if partition.device and partition.mountpoint and partition.mountpoint != "/":
				newMountpoint = self.getMountpoint(partition.device)
				if partition.mountpoint != newMountpoint:
					self.debugPrint(f"remove mountpoint old: {partition.mountpoint} / new: {newMountpoint}")
					self.triggerAddRemovePartion("remove", partition=partition)
					partition.mountpoint = newMountpoint

		# Add new mount
		for partition in self.partitions:
			if partition.device and partition.mountpoint != "/":
				newMountpoint = self.getMountpoint(partition.device)
				self.debugPrint(f"add mountpoint old: {partition.mountpoint} / new: {newMountpoint}")
				if newMountpoint and partition.mountpoint != newMountpoint:
					partition.mountpoint = newMountpoint
					self.triggerAddRemovePartion("add", partition=partition)

	def refresh(self, disk):
		self.debugPrint(f"refresh {disk}")
		removeList = []
		appedList = []
		oldPartitions = []
		for partition in self.partitions:
			if partition.device and partition.device.startswith(disk) and partition.device != disk:
				oldPartitions.append(partition.device)

		if not exists(join("/sys/block/", disk)):
			removeList += oldPartitions
			removeList.append(disk)
		else:
			currentPartitions = []
			for line in fileReadLines("/proc/partitions", default=[], source=MODULE_NAME):
				parts = line.strip().split()
				if parts:
					device = parts[3]
					if device.startswith(disk) and device != disk:
						currentPartitions.append(device)

			for partition in oldPartitions:
				if partition not in currentPartitions:
					removeList.append(partition)

			for partition in currentPartitions:
				if partition not in oldPartitions:
					appedList.append(partition)

		for device in removeList:
			self.removeHotplugPartition(device)

		for device in appedList:
			self.addHotplugPartition(device)

	def getBlockDevInfo(self, blockdev):
		devpath = join("/sys/block", blockdev)
		error = False
		removable = False
		blacklisted = False
		is_cdrom = False
		partitions = []
		try:
			if exists(join(devpath, "removable")):
				removable = bool(int(readFile(join(devpath, "removable"))))  # TODO: This needs to be improved because some internal disks have removable = 1
			if exists(join(devpath, "dev")):
				dev = int(readFile(join(devpath, "dev")).split(":")[0])
			else:
				dev = None
			devlist = [1, 7, 31, 253, 254]  # This is ram, loop, mtdblock, romblock, ramzswap respectively.
			if dev in devlist:
				blacklisted = True
			if blockdev[0:2] == "sr":
				is_cdrom = True
			if blockdev[0:2] == "hd":
				try:
					media = readFile(f"/proc/ide/{blockdev}/media")
					if "cdrom" in media:
						is_cdrom = True
				except OSError:
					error = True
			if not is_cdrom and exists(devpath):  # Check for partitions.
				for partition in listdir(devpath):
					if partition[0:len(blockdev)] != blockdev:
						continue
					if dev == 179 and not search(r"mmcblk\dp\d+", partition):
						continue
					partitions.append(partition)
			else:
				self.cd = blockdev
		except OSError:
			error = True
		medium_found = True  # Check for medium.
		try:
			if exists(join("/dev", blockdev)):
				open(join("/dev", blockdev)).close()
		except OSError as err:
			if err.errno == 159:  # No medium present.
				medium_found = False
		return error, blacklisted, removable, is_cdrom, partitions, medium_found

	def enumerateHotPlugDevices(self, callback):
		def parseDeviceData(inputData):
			eventData = {}
			if "\n" in inputData:
				data = inputData[:-1].split("\n")
				eventData["mode"] = 1
			else:
				data = inputData.split("\0")[:-1]
				eventData["mode"] = 0
			for values in data:
				variable, value = values.split("=", 1)
				eventData[variable] = value
			return eventData

		print("[Harddisk] Enumerating hotplug devices.")
		fileNames = glob("/tmp/hotplug_dev_*")
		devices = []
		for fileName in fileNames:
			with open(fileName) as f:
				data = f.read()
				eventData = parseDeviceData(data)
				if eventData["DEVTYPE"] == "partition":  # Handle only partitions
					device = eventData["DEVNAME"].replace("/dev/", "")
					shortDevice = device[:7] if device.startswith("mmcblk") else sub(r"[\d]", "", device)
					removable = fileReadLine(f"/sys/block/{shortDevice}/removable", source=MODULE_NAME)
					internal = "pci" in eventData["DEVPATH"] or "ahci" in eventData["DEVPATH"] or "ata" in eventData["DEVPATH"]
					if internal and removable == "1":  # This is probably a driver bug
						for physdevprefix, pdescription in list(getDeviceDB().items()):
							if eventData["DEVPATH"].startswith(physdevprefix) and "SATA" in pdescription:
								removable = "0"  # Force removable to 0 if SATA
						if removable == "1":
							print("[Harddisk] Warning: internal and removable = 1!")
					eventData["SORT"] = 0 if internal or removable == "0" else 1
					devices.append(eventData)
				remove(fileName)

		if devices:
			devices.sort(key=lambda x: (x["SORT"], x["ID_PART_ENTRY_SIZE"]))
			mounts = getProcMountsNew()
			devmounts = [x[0] for x in mounts]
			mounts = [x[1] for x in mounts if x[1].startswith("/media/")]
			newFstab = fileReadLines("/etc/fstab", default=[], source=MODULE_NAME)
			fstabReservesMediaHDD = checkFstabReservesMediaHDD(newFstab)
			possibleMountPoints = [f"/media/{x}" for x in ("usb8", "usb7", "usb6", "usb5", "usb4", "usb3", "usb2", "usb", "hdd") if f"/media/{x}" not in mounts and not (x == "hdd" and fstabReservesMediaHDD)]

			for device in devices:
				if device["DEVNAME"] not in devmounts or "/media/hdd" in possibleMountPoints:
					device["MOUNT"] = possibleMountPoints.pop()

			knownDevices = fileReadLines("/etc/udev/known_devices", default=[], source=MODULE_NAME)
			commands = []
			for device in devices:
				ID_FS_UUID = device.get("ID_FS_UUID")
				DEVNAME = device.get("DEVNAME")
				if [x for x in newFstab if DEVNAME in x]:
					print(f"[Harddisk] Hotplug device '{DEVNAME}' ignored because device is already in '/etc/fstab'.")
					continue
				if [x for x in newFstab if ID_FS_UUID in x]:
					print(f"[Harddisk] Hotplug device '{DEVNAME}' ignored because UUID is already in '/etc/fstab'.")
					continue
				mountPoint = device.get("MOUNT")
				if mountPoint == "/media/hdd" and fstabReservesMediaHDD:
					print(f"[Harddisk] Skip auto fstab entry for '{DEVNAME}' as '/media/hdd' is reserved in '/etc/fstab'.")
					continue
				if mountPoint:
					commands.append(["/bin/umount", "/bin/umount", "-lf", DEVNAME.replace("/dev/", "/media/")])
					ID_FS_TYPE = "auto"  # eventData.get("ID_FS_TYPE")
					knownDevices.append(f"{ID_FS_UUID}:{mountPoint}")
					newFstab.append(f"UUID={ID_FS_UUID} {mountPoint} {ID_FS_TYPE} defaults 0 0")
					if not exists(mountPoint):
						mkdir(mountPoint, 0o755)
					print(f"[Harddisk] Add hotplug device '{DEVNAME}' mounted as '{mountPoint}' to '/etc/fstab'.")
				else:
					print(f"[Harddisk] Warning: Hotplug device '{DEVNAME}' has no mount point!")

			if commands:
				# def enumerateHotPlugDevicesCallback(*args, **kwargs):
				# 	callback()
				fileWriteLines("/etc/fstab", newFstab, source=MODULE_NAME)
				commands.append(["/bin/mount", "/bin/mount", "-a"])
				# self.console.eBatch(cmds=commands, callback=enumerateHotPlugDevicesCallback) # eBatch is not working correctly here this needs to be fixed
				# return
				for command in commands:
					self.console.ePopen(command)
		callback()

	def enumerateBlockDevices(self):
		print("[Harddisk] Enumerating block devices.")
		black = BoxInfo.getItem("mtdblack")
		for blockdev in listdir("/sys/block"):
			if blockdev.startswith(("ram", "rom", "loop", "zram", "md0", black)):
				continue
			# print(f"[Harddisk] Enumerating block device '{blockdev}'.")
			error, blacklisted, removable, is_cdrom, partitions, medium_found = self.addHotplugPartition(blockdev)
			if not error and not blacklisted and medium_found:
				for part in partitions:
					self.addHotplugPartition(part)
				self.devices_scanned_on_init.append((blockdev, removable, is_cdrom, medium_found))

	def enumerateNetworkMounts(self, refresh=False):
		print("[Harddisk] Enumerating network mounts.")
		for mount in ("net", "autofs"):
			netMounts = (exists(join("/media", mount)) and listdir(join("/media", mount))) or []
			for netMount in netMounts:
				path = join("/media", mount, netMount, "")
				if ismount(path):
					partition = Partition(mountpoint=path, description=netMount)
					if str(partition) not in [str(x) for x in self.partitions]:
						print(f"[Harddisk] New network mount '{mount}' -> '{path}'.")
						if refresh:
							self.addMountedPartition(device=path, desc=netMount)
						else:
							self.partitions.append(partition)
		if ismount("/media/hdd") and "/media/hdd/" not in [x.mountpoint for x in self.partitions]:
			print("[Harddisk] New network mount being used as HDD replacement -> '/media/hdd/'.")
			if refresh:
				self.addMountedPartition(device="/media/hdd/", desc="/media/hdd/")
			else:
				self.partitions.append(Partition(mountpoint="/media/hdd/", description="/media/hdd"))

	def getAutofsMountpoint(self, device):
		r = self.getMountpoint(device)
		if r is None:
			return join("/media", device)
		return r

	def getMountpoint(self, device):
		dev = join("/dev", device)
		for item in getProcMountsNew():
			if item[0] == dev:
				return join(item[1], "")
		return None

	def triggerAddRemovePartion(self, action, partition):
		self.debugPrint(f"{action} partition {partition.device} -> {partition.mountpoint}")
		self.on_partition_list_change(action, partition)

	def addHotplugPartition(self, device, physdev=None, model=None):
		device = device.replace("/dev/", "")
		self.debugPrint(f"addHotplugPartition {device}")
		# device -> the device name, without /dev.
		# physdev -> the physical device path, which we (might) use to determine the user friendly name.
		if not physdev:
			dev, part = self.splitDeviceName(device)
			try:
				physdev = realpath(f"/sys/block/{dev}/device")[4:]
			except OSError as err:
				physdev = dev
				print(f"[Harddisk] Error {err.errno}: Couldn't determine blockdev or physdev for device '{device}'!  ({err.strerror})")
		error, blacklisted, removable, is_cdrom, partitions, medium_found = self.getBlockDevInfo(self.splitDeviceName(device)[0])
		if not blacklisted and medium_found:
			description = self.getUserfriendlyDeviceName(device, physdev)
			p = Partition(mountpoint=self.getMountpoint(device), description=description, force_mounted=True, device=device)
			self.partitions.append(p)
			if p.mountpoint:  # Plugins won't expect unmounted devices
				self.triggerAddRemovePartion("add", p)
			# see if this is a harddrive
			if not search(r"mmcblk\dp\d+|sd\w\d+", device):
				if device not in [hdd.device for hdd in self.hdd]:
					self.hdd.append(Harddisk(device, removable, model))
					self.hdd.sort()
				BoxInfo.setItem("Harddisk", True)
		return error, blacklisted, removable, is_cdrom, partitions, medium_found

	def addHotplugAudiocd(self, device, physdev=None):
		# device -> the device name, without /dev.
		# physdev -> the physical device path, which we (might) use to determine the user friendly name.
		if not physdev:
			dev, part = self.splitDeviceName(device)
			try:
				physdev = realpath(f"/sys/block/{dev}/device")[4:]
			except OSError as err:
				physdev = dev
				print(f"[Harddisk] Error {err.errno}: Couldn't determine blockdev or physdev for device '{device}'!  ({err.strerror})")
		error, blacklisted, removable, is_cdrom, partitions, medium_found = self.getBlockDevInfo(device)
		if not blacklisted and medium_found:
			description = self.getUserfriendlyDeviceName(device, physdev)
			p = Partition(mountpoint="/media/audiocd", description=description, force_mounted=True, device=device)
			self.partitions.append(p)
			self.triggerAddRemovePartion("add", p)
			BoxInfo.setItem("Harddisk", False)
		return error, blacklisted, removable, is_cdrom, partitions, medium_found

	def removeHotplugPartition(self, device):
		device = device.replace("/dev/", "")
		self.debugPrint(f"removeHotplugPartition {device}")
		for x in self.partitions[:]:
			if x.device == device:
				self.partitions.remove(x)
				if x.mountpoint:  # Plugins won't expect unmounted devices.
					self.triggerAddRemovePartion("remove", x)
		if not search(r"mmcblk\dp\d+|sd\w\d+", device):
			for hdd in self.hdd:
				if hdd.device == device:
					hdd.stop()
					self.hdd.remove(hdd)
					break
			BoxInfo.setItem("Harddisk", len(self.hdd) > 0)

	def HDDCount(self):
		return len(self.hdd)

	def HDDList(self):
		list = []
		for hd in self.hdd:
			hdd = f"{hd.model()} - {hd.bus()}"
			cap = hd.capacity()
			if cap != "":
				hdd += f" ({cap})"
			list.append((hdd, hd))
		return list

	def getCD(self):
		return self.cd

	def getMountedPartitions(self, onlyhotplug=False, mounts=None):
		if mounts is None:
			mounts = getProcMountsNew()
		parts = [x for x in self.partitions if (x.is_hotplug or not onlyhotplug) and (x.force_mounted or x.mounted(mounts))]
		devs = set([x.device for x in parts])
		for devname in devs.copy():
			if not devname:
				continue
			dev, part = self.splitDeviceName(devname)
			if part and dev in devs:  # If this is a partition and we still have the whole disk, remove the whole disk.
				devs.remove(dev)
		return [x for x in parts if (not x.device or x.device in devs) and x.mountpoint]  # Return all devices which are not removed due to being a whole disk when a partition exists.

	def splitDeviceName(self, devname):
		if search(r"^mmcblk\d(?:p\d+$|$)", devname):
			m = search(r"(?P<dev>mmcblk\d)p(?P<part>\d+)$", devname)
			if m:
				return m.group("dev"), m.group("part") and int(m.group("part")) or 0
			else:
				return devname, 0
		else:
			# This works for: sdaX, hdaX, sr0 (which is in fact dev="sr0", part=""). It doesn't work for other names like mtdblock3, but they are blacklisted anyway.
			dev = devname[:3]
			part = devname[3:]
			for p in part:
				if not p.isdigit():
					return devname, 0
			return dev, part and int(part) or 0

	def getUserfriendlyDeviceName(self, dev, phys):
		device, part = self.splitDeviceName(dev)
		description = _("External Storage %s") % device
		try:
			fileName = "name" if "mmc" in device else "model"
			fileName = f"/sys{phys}/{fileName}"
			if exists(fileName):
				description = readFile(fileName)
		except OSError as err:
			print(f"[Harddisk] Error {err.errno}: Couldn't read model!  ({err.strerror})")
		hwdescription = ""
		for physdevprefix, pdescription in list(getDeviceDB().items()):
			if phys.startswith(physdevprefix):
				hwdescription = _(pdescription)

		label = fileReadLine(f"/dev/label/{dev}", default="", source=MODULE_NAME)
		if label:
			description += f" ({label})"
		else:
			if part and part != 1:  # Not whole disk and not partition 1.
				description += _(" (Partition %d)") % part

		if hwdescription:
			return f"{hwdescription}: {description}"
		else:
			return description

	def addMountedPartition(self, device, desc):
		device = join(device, "")
		for x in self.partitions:
			if x.mountpoint == device:
				return  # Already mounted.
		newpartion = Partition(mountpoint=device, description=desc)
		self.partitions.append(newpartion)
		self.triggerAddRemovePartion("add", newpartion)

	def removeMountedPartition(self, mountpoint):
		mountpoint = join(mountpoint, "")
		for x in self.partitions[:]:
			if x.mountpoint == mountpoint:
				self.partitions.remove(x)
				self.triggerAddRemovePartion("remove", x)

	def setDVDSpeed(self, device, speed=0):
		ioctl_flag = int(0x5322)
		if not device.startswith("/"):
			device = join("/dev", device)
		try:
			from fcntl import ioctl
			cd = open(device)
			ioctl(cd.fileno(), ioctl_flag, speed)
			cd.close()
		except OSError as err:
			print(f"[Harddisk] Error {err.errno}: Failed to set '{device}' speed to {speed}!  ({err.strerror})")


harddiskmanager = HarddiskManager()
