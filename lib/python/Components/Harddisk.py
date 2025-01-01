from glob import glob
from os import access, listdir, lstat, major, minor, mkdir, popen, remove, rmdir, stat as osstat, statvfs, system, unlink, walk
from os.path import abspath, dirname, exists, isfile, islink, ismount, join, realpath
from re import search, sub
from time import sleep, time

from enigma import getDeviceDB, eTimer

from Components.SystemInfo import BoxInfo
import Components.Task
from Components.Console import Console
from Tools.Directories import fileReadLines, fileReadLine, fileWriteLines
from Tools.CList import CList
from Tools.HardwareInfo import HardwareInfo

MODEL = BoxInfo.getItem("model")


def readFile(filename):
	with open(filename) as fd:
		data = fd.read().strip()
	return data

## Unused
#def getextdevices(ext):
#	cmd = f"blkid -t TYPE={ext} -o device"
#	extdevices = popen(cmd).read().replace("\n", ",").rstrip(",")
#	return None if extdevices == "" else [x.strip() for x in extdevices.split(",")]


def getProcMountsNew():
	lines = fileReadLines("/proc/mounts", default=[])
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
		for d in dirnames:
			dp = join(dirpath, d)
	return total_bytes


def Freespace(dev):
	try:
		statdev = statvfs(dev)
		space = (statdev.f_bavail * statdev.f_frsize) / 1024
	except OSError:
		space = 0
	return space


DEVTYPE_UDEV = 0
DEVTYPE_DEVFS = 1


class Harddisk:
	def __init__(self, device, removable=False):
		self.device = device
		if access("/dev/.udev", 0) or access("/run/udev/data", 0):
			self.type = DEVTYPE_UDEV
		elif access("/dev/.devfsd", 0):
			self.type = DEVTYPE_DEVFS
		else:
			print("[Harddisk] Unable to determine structure of '/dev'!")
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
		if self.type == DEVTYPE_UDEV:
			self.dev_path = join("/dev", self.device)
			self.disk_path = self.dev_path
		elif self.type == DEVTYPE_DEVFS:
			tmp = readFile(self.sysfsPath("dev")).split(":")
			s_major = int(tmp[0])
			s_minor = int(tmp[1])
			for disc in listdir("/dev/discs"):  # IanSav: Is this path correct?  Linux uses disk not disc!
				dev_path = realpath(join("/dev/discs", disc))
				disk_path = join(dev_path, "disc")
				try:
					rdev = osstat(disk_path).st_rdev
				except OSError:
					continue
				if s_major == major(rdev) and s_minor == minor(rdev):
					self.dev_path = dev_path
					self.disk_path = disk_path
					break
		print(f"[Harddisk] New Harddisk '{self.device}' -> '{self.dev_path}' -> '{self.disk_path}'.")
		if not removable:
			self.startIdle()

	def __lt__(self, ob):
		return self.device < ob.device

	def partitionPath(self, n):
		if self.type == DEVTYPE_UDEV:
			if self.dev_path.startswith("/dev/mmcblk"):
				return f"{self.dev_path}p{n}"
			else:
				return f"{self.dev_path}{n}"
		elif self.type == DEVTYPE_DEVFS:
			return join(self.dev_path, "part{n}")

	def sysfsPath(self, filename):
		return join("/sys/block/", self.device, filename)

	def stop(self):
		if self.timer:
			self.timer.stop()
			self.timer.callback.remove(self.runIdle)

	def bus(self):
		ret = _("External")
		if self.type == DEVTYPE_UDEV:  # SD/MMC(F1 specific).
			card = "sdhci" in self.phys_path
			type_name = " (SD/MMC)"
		elif self.type == DEVTYPE_DEVFS:  # CF(7025 specific).
			card = self.device[:2] == "hd" and "host0" not in self.dev_path
			type_name = " (CF)"
		hw_type = HardwareInfo().get_device_name()
		if hw_type == "elite" or hw_type == "premium" or hw_type == "premium+" or hw_type == "ultra":
			internal = "ide" in self.phys_path
		else:
			internal = ("pci" in self.phys_path or "ahci" in self.phys_path)
		if MODEL == "sf8008":
			internal = ("usb1/1-1/1-1.1/1-1.1:1.0" in self.phys_path) or ("usb1/1-1/1-1.4/1-1.4:1.0" in self.phys_path)
		if card:
			ret += type_name
		elif internal:
			ret = _("Internal")
		return ret

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
			if self.device[:2] == "hd":
				return readFile(join("/proc/ide", self.device, "model"))
			elif self.device[:2] == "sd":
				vendor = readFile(join(self.phys_path, "vendor"))
				model = readFile(join(self.phys_path, "model"))
				return f"{vendor}({model})"
			elif self.device.startswith("mmcblk"):
				return readFile(self.sysfsPath("device/name"))
			else:
				raise Exception("no hdX or sdX or mmcX")
		except Exception as err:
			# print(f"[Harddisk] Error {err.errno}: Failed to get model!  ({err.strerror})")
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
		if self.type == DEVTYPE_UDEV:
			try:
				devdir = listdir("/dev")
			except OSError:
				return -1
			for filename in devdir:
				if filename.startswith(self.device):
					numPart += 1
		elif self.type == DEVTYPE_DEVFS:
			try:
				idedir = listdir(self.dev_path)
			except OSError:
				return -1
			for filename in idedir:
				if filename.startswith("disc"):
					numPart += 1
				if filename.startswith("part"):
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

	def createPartition(self):  # No longer supported, use createInitializeJob instead!
		return 1

	def mkfs(self):  # No longer supported, use createInitializeJob instead!
		return 1

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
		if self.type == DEVTYPE_UDEV:
			res = system(f"hdparm -z {self.disk_path}")  # We can let udev do the job, re-read the partition table.
			sleep(3)  # Give udev some time to make the mount, which it will do asynchronously.
		return res >> 8

	def fsck(self):  # No longer supported, use createCheckJob instead!
		return 1

	def killPartitionTable(self):
		zero = 512 * b"\0"
		h = open(self.dev_path, "wb")
		for i in list(range(9)):  # Delete first 9 sectors, which will likely kill the first partition too.
			h.write(zero)
		h.close()

	def killPartition(self, n):
		zero = 512 * b"\0"
		part = self.partitionPath(n)
		h = open(part, "wb")
		for i in list(range(3)):
			h.write(zero)
		h.close()

	def createInitializeJob(self):
		job = Components.Task.Job(_("Initializing storage device..."))
		size = self.diskSize()
		print(f"[Harddisk] Storage size {size} MB.")
		task = UnmountTask(job, self)
		task = Components.Task.PythonTask(job, _("Removing partition table"))
		task.work = self.killPartitionTable
		task.weighting = 1
		task = Components.Task.LoggingTask(job, _("Rereading partition table"))
		task.weighting = 1
		task.setTool("hdparm")
		task.args.append("-z")
		task.args.append(self.disk_path)
		task = Components.Task.ConditionTask(job, _("Waiting for partition"), timeoutCount=20)
		task.check = lambda: not exists(self.partitionPath("1"))
		task.weighting = 1
		task = Components.Task.LoggingTask(job, _("Creating partition"))
		task.weighting = 5
		task.setTool("parted")
		alignment = "min" if size < 1024 else "opt"  # On very small devices, align to block only, prefer optimal alignment for performance.
		parttype = "gpt" if size > 2097151 else "msdos"
		task.args += ["-a", alignment, "-s", self.disk_path, "mklabel", parttype, "mkpart", "primary", "0%", "100%"]
		task = Components.Task.ConditionTask(job, _("Waiting for partition"))
		task.check = lambda: exists(self.partitionPath("1"))
		task.weighting = 1
		task = UnmountTask(job, self)
		task = MkfsTask(job, _("Creating file system"))
		big_o_options = ["dir_index"]
		task.setTool("mkfs.ext4")
		if size > 250000:
			task.args += ["-T", "largefile", "-N", "262144"]  # No more than 256k i-nodes (prevent problems with fsck memory requirements).
			big_o_options.append("sparse_super")
		elif size > 16384:
			task.args += ["-T", "largefile"]  # Between 16GB and 250GB: 1 i-node per megabyte.
			big_o_options.append("sparse_super")
		elif size > 2048:
			task.args += ["-T", "largefile", "-N", str(int(size * 32))]  # Over 2GB: 32 i-nodes per megabyte.
		task.args += ["-F", "-F", "-m0", "-O ^metadata_csum", "-O", ",".join(big_o_options), self.partitionPath("1")]
		task = MountTask(job, self)
		task.weighting = 3
		task = Components.Task.ConditionTask(job, _("Waiting for mount"), timeoutCount=20)
		task.check = self.mountDevice
		task.weighting = 1
		return job

	def initialize(self):  # No longer supported!
		return -5

	def check(self):  # No longer supported!
		return -5

	def createCheckJob(self):
		job = Components.Task.Job(_("Checking file system..."))
		if self.findMount():
			UnmountTask(job, self)  # Create unmount task if it was not mounted.
			dev = self.mount_device
		else:
			dev = self.partitionPath("1")  # Otherwise, assume there is one partition.
		task = Components.Task.LoggingTask(job, "fsck")
		task.setTool("fsck.ext3")
		task.args.append("-f")
		task.args.append("-p")
		task.args.append(dev)
		MountTask(job, self)
		task = Components.Task.ConditionTask(job, _("Waiting for mount"))
		task.check = self.mountDevice
		return job

	def createExt4ConversionJob(self):
		job = Components.Task.Job(_("Converting ext3 to ext4..."))
		if not exists("/sbin/tune2fs"):
			addInstallTask(job, "e2fsprogs-tune2fs")
		if self.findMount():
			UnmountTask(job, self)  # Create unmount task if it was not mounted.
			dev = self.mount_device
		else:
			dev = self.partitionPath("1")  # Otherwise, assume there is one partition.
		task = Components.Task.LoggingTask(job, "fsck")
		task.setTool("fsck.ext3")
		task.args.append("-p")
		task.args.append(dev)
		task = Components.Task.LoggingTask(job, "tune2fs")
		task.setTool("tune2fs")
		task.args.append("-O")
		task.args.append("extents,uninit_bg,dir_index")
		task.args.append("-o")
		task.args.append("journal_data_writeback")
		task.args.append(dev)
		task = Components.Task.LoggingTask(job, "fsck")
		task.setTool("fsck.ext4")
		task.postconditions = []  # Ignore result, it will always "fail".
		task.args.append("-f")
		task.args.append("-p")
		task.args.append("-D")
		task.args.append(dev)
		MountTask(job, self)
		task = Components.Task.ConditionTask(job, _("Waiting for mount"))
		task.check = self.mountDevice
		return job

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
				l = fd.read()
			data = l.split(None, 5)
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
		t = time()
		idle_time = t - self.last_access
		stats = self.readStats()
		l = sum(stats)
		if l != self.last_stat and l >= 0:  # Access.
			self.last_stat = l
			self.last_access = t
			idle_time = 0
			self.is_sleeping = False
		if idle_time >= self.max_idle_time and not self.is_sleeping:
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


def addInstallTask(job, package):
	task = Components.Task.LoggingTask(job, "update packages")
	task.setTool("opkg")
	task.args.append("update")
	task = Components.Task.LoggingTask(job, f"Install {package}")
	task.setTool("opkg")
	task.args.append("install")
	task.args.append(package)


class HarddiskManager:
	def __init__(self):
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

	def getBlockDevInfo(self, blockdev):
		devpath = join("/sys/block", blockdev)
		error = False
		removable = False
		BLACKLIST = []
		if BoxInfo.getItem("mtdrootfs").startswith("mmcblk0p"):
			BLACKLIST = ["mmcblk0"]
		elif BoxInfo.getItem("mtdrootfs").startswith("mmcblk1p"):
			BLACKLIST = ["mmcblk1"]
		blacklisted = False
		if blockdev[:7] in BLACKLIST:
			blacklisted = True
		if blockdev.startswith("mmcblk") and (search(r"mmcblk\dboot", blockdev) or search(r"mmcblk\drpmb", blockdev)) or blockdev == "ram":
			blacklisted = True
		is_cdrom = False
		partitions = []
		try:
			if exists(join(devpath, "removable")):
				removable = bool(int(readFile(join(devpath, "removable"))))
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
				device = eventData["DEVNAME"].replace("/dev/", "")
				shortDevice = device[:7] if device.startswith("mmcblk") else sub(r"[\d]", "", device)
				removable = fileReadLine(f"/sys/block/{shortDevice}/removable")
				eventData["SORT"] = 0 if ("pci" in eventData["DEVPATH"] or "ahci" in eventData["DEVPATH"]) and removable == "0" else 1
				devices.append(eventData)
				remove(fileName)

		if devices:
			devices.sort(key=lambda x: (x["SORT"], x["ID_PART_ENTRY_SIZE"]))
			mounts = getProcMountsNew()
			devmounts = [x[0] for x in mounts]
			mounts = [x[1] for x in mounts if x[1].startswith("/media/")]
			possibleMountPoints = [f"/media/{x}" for x in ("usb8", "usb7", "usb6", "usb5", "usb4", "usb3", "usb2", "usb", "hdd") if f"/media/{x}" not in mounts]

			for device in devices:
				if device["DEVNAME"] not in devmounts or "/media/hdd" in possibleMountPoints:
					device["MOUNT"] = possibleMountPoints.pop()

			knownDevices = fileReadLines("/etc/udev/known_devices", default=[])
			newFstab = fileReadLines("/etc/fstab")
			commands = []
			for device in devices:
				ID_FS_UUID = device.get("ID_FS_UUID")
				DEVNAME = device.get("DEVNAME")
				if [x for x in newFstab if DEVNAME in x]:
					print(f"[Harddisk] Add hotplug device: {DEVNAME} ignored because device is already in fstab")
					continue
				if [x for x in newFstab if ID_FS_UUID in x]:
					print(f"[Harddisk] Add hotplug device: {DEVNAME} ignored because uuid is already in fstab")
					continue
				mountPoint = device.get("MOUNT")
				if mountPoint:
					commands.append(f"/bin/umount -lf {DEVNAME.replace("/dev/", "/media/")}")
					ID_FS_TYPE = "auto"  # eventData.get("ID_FS_TYPE")
					knownDevices.append(f"{ID_FS_UUID}:{mountPoint}")
					newFstab.append(f"UUID={ID_FS_UUID} {mountPoint} {ID_FS_TYPE} defaults 0 0")
					if not exists(mountPoint):
						mkdir(mountPoint, 0o755)
					print(f"[Harddisk] Add hotplug device: {DEVNAME} mount: {mountPoint} to fstab")
				else:
					print(f"[Harddisk] Warning! hotplug device: {DEVNAME} has no mountPoint")

			if commands:
				#def enumerateHotPlugDevicesCallback(*args, **kwargs):
				#	callback()
				fileWriteLines("/etc/fstab", newFstab)
				commands.append("/bin/mount -a")
				#self.console.eBatch(cmds=commands, callback=enumerateHotPlugDevicesCallback) # eBatch is not working correctly here this needs to be fixed
				#return
				for command in commands:
					self.console.ePopen(command)
		callback()

	def enumerateBlockDevices(self):
		print("[Harddisk] Enumerating block devices.")
		for blockdev in listdir("/sys/block"):
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

	def addHotplugPartition(self, device, physdev=None):
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
		hw_type = HardwareInfo().get_device_name()
		if hw_type == "elite" or hw_type == "premium" or hw_type == "premium+" or hw_type == "ultra":
			if device[0:3] == "hda":
				blacklisted = True
		if not blacklisted and medium_found:
			description = self.getUserfriendlyDeviceName(device, physdev)
			p = Partition(mountpoint=self.getMountpoint(device), description=description, force_mounted=True, device=device)
			self.partitions.append(p)
			if p.mountpoint:  # Plugins won't expect unmounted devices
				self.on_partition_list_change("add", p)
			# see if this is a harddrive
			l = len(device)
			if l and (not device[l - 1].isdigit() or (device.startswith("mmcblk") and not search(r"mmcblk\dp\d+", device))):
				if device not in [hdd.device for hdd in self.hdd]:
					self.hdd.append(Harddisk(device, removable))
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
			self.on_partition_list_change("add", p)
			BoxInfo.setItem("Harddisk", False)
		return error, blacklisted, removable, is_cdrom, partitions, medium_found

	def removeHotplugPartition(self, device):
		for x in self.partitions[:]:
			if x.device == device:
				self.partitions.remove(x)
				if x.mountpoint:  # Plugins won't expect unmounted devices.
					self.on_partition_list_change("remove", x)
		l = len(device)
		if l and (not device[l - 1].isdigit() or (device.startswith("mmcblk") and not search(r"mmcblk\dp\d+", device))):
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
		return [x for x in parts if not x.device or x.device in devs]  # Return all devices which are not removed due to being a whole disk when a partition exists.

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
		dev, part = self.splitDeviceName(dev)
		description = _("External Storage %s") % dev
		try:
			fileName = "name" if "mmc" in dev else "model"
			description = readFile(f"/sys{phys}/{fileName}")
		except OSError as err:
			print(f"[Harddisk] Error {err.errno}: Couldn't read model!  ({err.strerror})")
		for physdevprefix, pdescription in list(getDeviceDB().items()):
			if phys.startswith(physdevprefix):
				description = pdescription
		if part and part != 1:  # Not whole disk and not partition 1.
			description += _(" (Partition %d)") % part
		return description

	def addMountedPartition(self, device, desc):
		device = join(device, "")
		for x in self.partitions:
			if x.mountpoint == device:
				return  # Already mounted.
		newpartion = Partition(mountpoint=device, description=desc)
		self.partitions.append(newpartion)
		self.on_partition_list_change("add", newpartion)

	def removeMountedPartition(self, mountpoint):
		mountpoint = join(mountpoint, "")
		for x in self.partitions[:]:
			if x.mountpoint == mountpoint:
				self.partitions.remove(x)
				self.on_partition_list_change("remove", x)

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


class UnmountTask(Components.Task.LoggingTask):
	def __init__(self, job, hdd):
		Components.Task.LoggingTask.__init__(self, job, _("Unmount"))
		self.hdd = hdd
		self.mountpoints = []

	def prepare(self):
		try:
			dev = self.hdd.disk_path.split("/")[-1]
			open(f"/dev/nomount.{dev}", "wb").close()
		except OSError as err:
			print(f"[Harddisk] Error {err.errno}: Failed to create '/dev/nomount' file!  ({err.strerror})")
		self.setTool("umount")
		self.args.append("-f")
		for dev in self.hdd.enumMountDevices():
			self.args.append(dev)
			self.postconditions.append(Components.Task.ReturncodePostcondition())
			self.mountpoints.append(dev)
		if not self.mountpoints:
			print("[Harddisk] UnmountTask: No mount points found?")
			self.cmd = "true"
			self.args = [self.cmd]

	def afterRun(self):
		for path in self.mountpoints:
			try:
				rmdir(path)
			except OSError as err:
				print(f"[Harddisk] Error {err.errno}: Failed to remove path '{path}'!  ({err.strerror})")


class MountTask(Components.Task.LoggingTask):
	def __init__(self, job, hdd):
		Components.Task.LoggingTask.__init__(self, job, _("Mount"))
		self.hdd = hdd

	def prepare(self):
		try:
			dev = self.hdd.disk_path.split("/")[-1]
			unlink(f"/dev/nomount.{dev}")
		except OSError as err:
			print(f"[Harddisk] Error {err.errno}: Failed to remove '/dev/nomount' file!  ({err.strerror})")
		if self.hdd.mount_device is None:  # Try mounting through fstab first.
			dev = self.hdd.partitionPath("1")
		else:
			dev = self.hdd.mount_device  # If previously mounted, use the same spot.
		with open("/etc/fstab") as fd:
			lines = fd.readlines()
		for line in lines:
			parts = line.strip().split(" ")
			fspath = realpath(parts[0])
			if realpath(fspath) == dev:
				self.setCmdline(f"mount -t auto {fspath}")
				self.postconditions.append(Components.Task.ReturncodePostcondition())
				return
		if self.hdd.type == DEVTYPE_UDEV:  # The device is not in fstab.
			self.setCmdline(f"sleep 2; hdparm -z {self.hdd.disk_path}")  # We can let udev do the job, re-read the partition table. Sorry for the sleep 2 hack.
			self.postconditions.append(Components.Task.ReturncodePostcondition())


class MkfsTask(Components.Task.LoggingTask):
	def prepare(self):
		self.fsck_state = None

	def processOutput(self, data):
		if isinstance(data, bytes):
			data = data.decode()
		if "Writing inode tables:" in data or "Die Superblöcke" in data:
			self.fsck_state = "inode"
		elif self.fsck_state == "inode" and "/" in data:
			try:
				d = data.strip(" \x08\r\n").split("/", 1)
				if "\x08" in d[1]:
					d[1] = d[1].split("\x08", 1)[0]
				self.setProgress(80 * int(d[0]) // int(d[1]))
			except Exception as err:
				print(f"[Harddisk] MkfsTask - [Mkfs] Error: {err}!")
			return  # Don't log the progress.
		self.log.append(data)


harddiskmanager = HarddiskManager()
