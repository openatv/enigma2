# Copyright (c) 2025 jbleyel

# This code may be used commercially. Attribution must be given to the original author.
# Licensed under GPLv2.


from glob import glob
from os import listdir, mkdir, rmdir, unlink
from os.path import exists, ismount, join, realpath
from shutil import which
from string import ascii_letters, digits

from Components.Task import ConditionTask, Job, LoggingTask, ReturncodePostcondition
from Tools.Conversions import scaleNumber
from Tools.Directories import fileReadLine, fileReadLines, fileWriteLines

MODULE_NAME = __name__.split(".")[-1]
EXPANDER_MOUNT = ".FlashExpander"


class StorageDevice():
	def __init__(self, deviceData):
		self.deviceData = {key: value for key, value in deviceData.items()}
		for key, value in self.deviceData.items():
			setattr(self, key, value)

		self.mount_path = None
		self.mount_device = None
		self.dev_path = self.devicePoint
		self.disk_path = self.dev_path

	def getLabelLimit(self, fstype):
		if "ntfs" in fstype:
			return 32
		elif "exfat" == fstype:
			return 15
		elif "ext" in fstype:
			return 16
		else:
			return 11

	def normalizeLabel(self, label, limit):
		label = label.replace(" ", "_")
		return "".join([ch for ch in label if ch in (ascii_letters + digits + "_")])[:limit]

	def findMount(self):
		if self.mount_path is None:
			return self.mountDevice()
		return self.mount_path

	def mountDevice(self):
		for parts in getProcMountsNew():
			if realpath(parts[0]).startswith(self.devicePoint):
				self.mount_device = parts[0]
				self.mount_path = parts[1]
				return parts[1]

	def createWipeJob(self, options=None):
		options = options or {}
		uuids = options.get("uuids") or {}
		debug = options.get("debug")

		job = Job(_("Initializing storage device..."))

		UnmountTask(job, self, debug)

		UnmountSwapTask(job, self, debug)

		task = LoggingTask(job, _("Removing partition table"))
		task.setTool('parted')
		alignment = "min" if self.size < (1024 ** 3) else "opt"  # 1GB -> "min" else "opt"
		parttype = "gpt" if self.size > (2 * (1024 ** 3)) else "msdos"  # 2GB -> "gpt" else "msdos"
		task.args += ['-a', alignment, '-s', self.disk_path, 'mklabel', parttype]
		task.weighting = 1

		if uuids:
			task = UUIDTask(job, uuids, debug)
			task.weighting = 1
		return job

	def createFormatJob(self, options):
		debug = options.get("debug")
		fsType = options.get("fsType", "ext4")
		label = options.get("label")
		label = self.normalizeLabel(label, self.getLabelLimit(fsType))
		job = Job(_("Formatting storage device..."))
		UnmountTask(job, self, debug)
		UnmountSwapTask(job, self, debug)
		task = MkfsTask(job, debug)
		task.setTool(f"mkfs.{fsType}")
		if label:
			if fsType in ("vfat", "fat"):
				task.args += ["-n", label]
			else:
				task.args += ["-L", label]
		if fsType == "ntfs":
			task.setTool("mkntfs")
			task.args += ["-Q", "-F"]
			if label:
				task.args += ["-L", label]
		if fsType == "swap":
			task.setTool("mkswap")
		elif fsType.startswith("ext"):
			big_o_options = ["dir_index"]
			if self.size > 250000 * 1024 * 1024:
				# No more than 256k i-nodes (prevent problems with fsck memory requirements)
				task.args += ["-T", "largefile", "-N", "262144"]
				big_o_options.append("sparse_super")
			elif self.size > (16 * (1024 ** 3)):
				# Between 16GB and 250GB: 1 i-node per megabyte
				task.args += ["-T", "largefile"]
				big_o_options.append("sparse_super")
			elif self.size > (2 * (1024 ** 3)):
				# Over 2GB: 32 i-nodes per megabyte
				task.args += ["-T", "largefile", "-N", str(int((self.size / 1024 / 1024) * 32))]
			if self.UUID and self.fsType and self.fsType == fsType:
				task.args += ["-U", self.UUID]
			task.args += ["-E", "discard", "-F", "-m0", "-O ^metadata_csum", "-O", ",".join(big_o_options)]
		task.args.append(self.devicePoint)
		if self.fstabMountPoint and self.UUID:
			task = UUIDTask(job, {self.devicePoint.replace("/dev/", ""): self.UUID}, debug)
			task.weighting = 1
		task = MountTask(job, self, debug=debug)
		task.weighting = 3
		return job

	def createInitializeJob(self, options=None):
		options = options or {}
		debug = options.get("debug")
		partitions = options.get("partitions") or []
		uuids = options.get("uuids") or {}
		fsTypes = options.get("fsTypes") or {}
		partitionType = options.get("partitionType")
		mountDevice = options.get("mountDevice")

		job = Job(_("Initializing storage device..."))
		if debug:
			print(f"[StorageDevice] createInitializeJob size: {scaleNumber(self.size, format="%.2f")}")
			print(f"[StorageDevice] createInitializeJob partitions: {partitions} uuids: {uuids}")

		UnmountTask(job, self, debug)

		UnmountSwapTask(job, self, debug)

		task = LoggingTask(job, _("Removing partition table"))
		task.setTool('parted')
		alignment = "min" if self.size < (1024 ** 3) else "opt"  # 1GB -> "min" else "opt"
		task.args += ['-a', alignment, '-s', self.disk_path, 'mklabel', partitionType]
		task.weighting = 1

		task = LoggingTask(job, _("Rereading partition table"))
		task.weighting = 1
		task.setTool('hdparm')
		task.args.append('-z')
		task.args.append(self.disk_path)

		task = ConditionTask(job, _("Waiting for partition"), timeoutCount=5)
		task.check = lambda: not [x for x in glob(f"{self.devicePoint}*") if x != self.devicePoint]
		task.weighting = 1

		task = LoggingTask(job, _("Creating partition"))
		task.weighting = 5
		task.setTool('parted')
		alignment = "min" if self.size < (1024 ** 3) else "opt"  # 1GB -> "min" else "opt"
		# parttype = "gpt" if self.size > (2 * (1024 ** 3)) else "msdos"  # 2GB -> "gpt" else "msdos"
		task.args += ['-a', alignment, '-s', self.disk_path, 'mklabel', partitionType]
		start = 0
		for partition in partitions:
			fsType = partition.get("fsType", "ext4")
			size = partition.get("size", 100)
			end = min(start + size, 100)
			if fsType == "swap":
				task.args += ["mkpart", "primary", "linux-swap", f"{start}%", f"{end}%"]
			else:
				task.args += ["mkpart", "primary", f"{start}%", f"{end}%"]
			start += size

		task = ConditionTask(job, _("Waiting for partition"))
		task.check = lambda: [x for x in glob(f"{self.devicePoint}*") if x != self.devicePoint]
		task.weighting = 1

		for index, partition in enumerate(partitions):
			fsType = partition.get("fsType", "ext4")
			label = partition.get("label", f"DISK_{index + 1}")
			label = self.normalizeLabel(label, self.getLabelLimit(fsType))
			device = f"{self.devicePoint}p{index + 1}" if "mmcblk" in self.devicePoint else f"{self.devicePoint}{index + 1}"
			uuid = uuids.get(device)
			oldFsType = fsTypes.get(device)
			task = MkfsTask(job, debug)
			if fsType == "swap":
				task.setTool("mkswap")
			else:
				task.setTool(f"mkfs.{fsType}")
				if label:
					if fsType in ("vfat", "fat"):
						task.args += ["-n", label]
					else:
						task.args += ["-L", label]
				if fsType == "ntfs":
					task.setTool("mkntfs")
					task.args += ["-Q", "-F"]
					if label:
						task.args += ["-L", label]
				elif fsType.startswith("ext"):
					big_o_options = ["dir_index"]
					if self.size > 250000 * 1024 * 1024:
						# No more than 256k i-nodes (prevent problems with fsck memory requirements)
						task.args += ["-T", "largefile", "-N", "262144"]
						big_o_options.append("sparse_super")
					elif self.size > (16 * (1024 ** 3)):
						# Between 16GB and 250GB: 1 i-node per megabyte
						task.args += ["-T", "largefile"]
						big_o_options.append("sparse_super")
					elif self.size > (2 * (1024 ** 3)):
						# Over 2GB: 32 i-nodes per megabyte
						task.args += ["-T", "largefile", "-N", str(int((self.size / 1024 / 1024) * 32))]
					if uuid and oldFsType and oldFsType == fsType:
						task.args += ["-U", uuid]
					task.args += ["-E", "discard", "-F", "-m0", "-O ^metadata_csum", "-O", ",".join(big_o_options)]
			task.args.append(device)

		if uuids:
			task = UUIDTask(job, uuids, debug)
			task.weighting = 1
		task = MountTask(job, self, mountDevice=mountDevice, debug=debug)
		task.weighting = 3
		return job

	def createExt4ConversionJob(self, options=None):
		options = options or {}
		debug = options.get("debug")
		job = Job(_("Converting ext3 to ext4..."))

		if self.findMount():
			UnmountTask(job, self, debug)
		task = LoggingTask(job, "fsck")
		task.setTool('fsck.ext3')
		task.args.append('-p')
		task.args.append(self.devicePoint)
		task = LoggingTask(job, "tune2fs")
		task.setTool('tune2fs')
		task.args.append('-O')
		task.args.append('extents,uninit_bg,dir_index')
		task.args.append('-o')
		task.args.append('journal_data_writeback')
		task.args.append(self.devicePoint)
		task = LoggingTask(job, "fsck")
		task.setTool('fsck.ext4')
		task.postconditions = []  # ignore result, it will always "fail"
		task.args.append('-f')
		task.args.append('-p')
		task.args.append('-D')
		task.args.append(self.devicePoint)

		if self.fstabMountPoint and self.UUID:
			task = UUIDTask(job, {self.devicePoint.replace("/dev/", ""): self.UUID}, debug)
			task.weighting = 1

		task = MountTask(job, self, debug=debug)
		task.weighting = 3
		return job

	def createCheckJob(self, options=None):
		return FileSystemCheckJob(self)

	def createTrimJob(self, options=None):
		options = options or {}
		debug = options.get("debug")
		job = Job(_("Trim File System..."))
		task = LoggingTask(job, "fstrim")
		task.setTool("fstrim")
		task.args += ["-v"]
		task.args.append(self.devicePoint)
		task = MountTask(job, self, debug=debug)
		task.weighting = 3
		return job


class FileSystemCheckJob(Job):
	def __init__(self, storageDevice):
		Job.__init__(self, _("Checking file system..."))
		self.storageDevice = storageDevice
		self.mounts = []
		self.nomountFile = join("/dev", f"nomount.{storageDevice.disk}")
		self.ownsMountBlock = False
		self.state_changed.append(self.releaseMountBlock)
		FileSystemCheckUnmountTask(self)
		self.checkTask = FileSystemCheckTask(self)
		self.mountTask = FileSystemCheckMountTask(self)

	def getMounts(self):
		device = realpath(self.storageDevice.devicePoint)
		return [x for x in getProcMountsNew(strict=True) if realpath(x[0]) == device]

	def releaseMountBlock(self):
		# Job failures also include missing tools, prepare exceptions and cancellation.
		if self.ownsMountBlock and self.status in (self.FAILED, self.FINISHED):
			try:
				unlink(self.nomountFile)
			except FileNotFoundError:
				self.ownsMountBlock = False
			except OSError as err:
				print(f"[Storage] Unable to remove '{self.nomountFile}': {err}")
			else:
				self.ownsMountBlock = False


class FileSystemCheckUnmountTask(LoggingTask):
	def __init__(self, job):
		LoggingTask.__init__(self, job, _("Unmount"))
		self.setTool(which("umount") or "/bin/umount")

	def checkPreconditions(self, immediate=False):
		problems = LoggingTask.checkPreconditions(self, immediate)
		if not immediate:
			# Check all required tools before taking the storage offline.
			problems += self.job.checkTask.checkPreconditions() + self.job.mountTask.checkPreconditions()
		return problems

	def prepare(self):
		self.job.mounts = self.job.getMounts()
		if len(self.job.mounts) > 1:
			raise OSError(_("This device has multiple mount points. Unmount them before checking the file system."))
		if self.job.mounts and self.job.mounts[0][1] == "/":
			raise OSError(_("The running system's file system cannot be checked."))
		# Do not overwrite or remove a mount block owned by another operation.
		with open(self.job.nomountFile, "xb"):
			self.job.ownsMountBlock = True
		if self.job.mounts:
			# A busy filesystem must remain mounted; never use force or lazy unmount.
			self.args.append(self.job.mounts[0][1])
		else:
			self.cmd = None
			self.returncode = 0


class FileSystemCheckTask(LoggingTask):
	def __init__(self, job):
		LoggingTask.__init__(self, job, "fsck")
		fsType = job.storageDevice.fsType
		tool = "ntfsfix" if fsType == "ntfs" else f"fsck.{fsType}"
		self.setTool(which(tool) or join("/sbin", tool))
		if fsType != "ntfs":
			self.args += ["-p"] if fsType == "exfat" else ["-f", "-p"]
		self.args.append(job.storageDevice.devicePoint)
		self.postconditions = [FileSystemCheckCondition()]

	def prepare(self):
		# Recheck after unmount, including unexpected mounts created in the meantime.
		if self.job.getMounts():
			raise OSError(_("The device is still mounted. Stop recordings and time shift before checking the file system."))


class FileSystemCheckCondition(ReturncodePostcondition):
	def check(self, task):
		# e2fsck status 1 means repaired; status 2 requests a reboot, not a remount.
		return task.returncode == 0 or (task.job.storageDevice.fsType in ("ext2", "ext3", "ext4") and task.returncode == 1)

	def getErrorMessage(self, task):
		if task.job.storageDevice.fsType in ("ext2", "ext3", "ext4") and task.returncode in (2, 3):
			return _("The file system was repaired. Restart the receiver before using this device.")
		return ReturncodePostcondition.getErrorMessage(self, task)


class FileSystemCheckMountTask(LoggingTask):
	def __init__(self, job):
		LoggingTask.__init__(self, job, _("Mount"))
		self.setTool(which("mount") or "/bin/mount")
		self.weighting = 3

	def prepare(self):
		# Restore only this device's previous mount, including its read-only state.
		if self.job.mounts:
			device, mountPoint = self.job.mounts[0][:2]
			mountOptions = self.job.mounts[0][3]
			if any(x[1] == mountPoint for x in getProcMountsNew(strict=True)):
				raise OSError(_("The previous mount point is already in use."))
			if not exists(mountPoint):
				mkdir(mountPoint)
			self.args += ["-o", mountOptions, device, mountPoint]
		else:
			self.cmd = None
			self.returncode = 0


class UUIDTask(ConditionTask):
	def __init__(self, job, uuids, debug):
		ConditionTask.__init__(self, job, _("UUID"), 1)
		self.uuids = uuids
		self.debug = debug

	def check(self):
		fstab = fileReadLines("/etc/fstab", default=[], source=MODULE_NAME)
		knownDevices = fileReadLines("/etc/udev/known_devices", default=[], source=MODULE_NAME)
		saveFstab = False
		saveknownDevices = False
		for device, olduuid in self.uuids.items():
			newuuid = fileReadLine(f"/dev/uuid/{device}", default=None, source=MODULE_NAME)
			if newuuid and newuuid != olduuid:
				for i, line in enumerate(fstab):
					if line.find(f"UUID={olduuid}") != -1:
						fstab[i] = line.replace(f"UUID={olduuid}", f"UUID={newuuid}")
						if self.debug:
							print(f"[UUIDTask] fstab UUID changed from {olduuid} to {newuuid}")
						saveFstab = True
						break
				for i, line in enumerate(knownDevices):
					if line.startswith(olduuid):
						knownDevices[i] = line.replace(f"{olduuid}", f"{newuuid}")
						if self.debug:
							print(f"[UUIDTask] known_devices UUID changed from {olduuid} to {newuuid}")
						saveknownDevices = True
						break
			if not newuuid:
				for i, line in enumerate(fstab):
					if line.find(f"UUID={olduuid}") != -1:
						fstab[i] = ""
						if self.debug:
							print(f"[UUIDTask] fstab UUID {olduuid} removed")
						saveFstab = True
						break
				for i, line in enumerate(knownDevices):
					if line.startswith(olduuid):
						knownDevices[i] = ""
						if self.debug:
							print(f"[UUIDTask] known_devices UUID {olduuid} removed")
						saveknownDevices = True
						break
		if saveFstab:
			fileWriteLines("/etc/fstab", fstab, source=MODULE_NAME)
		if saveknownDevices:
			knownDevices = [x for x in knownDevices if x]
			fileWriteLines("/etc/udev/known_devices", knownDevices, source=MODULE_NAME)
		for line in fstab:
			if EXPANDER_MOUNT not in line and "/media/" in line:
				parts = line.split()
				if not exists(parts[1]):
					mkdir(parts[1], 0o755)

		return True


class UnmountTask(LoggingTask):
	def __init__(self, job, storageDevice, debug):
		self.debug = debug
		LoggingTask.__init__(self, job, _("Unmount"))
		self.storageDevice = storageDevice
		self.nomoutFile = f"/dev/nomount.{self.storageDevice.disk}"
		self.mountpoints = []

	def prepare(self):
		try:
			open(self.nomoutFile, "wb").close()
		except Exception as e:
			print(f"[{self.__class__.__name__}] ERROR: Failed to create /dev/nomount file:{e}")
		self.setTool('umount')
		self.args.append('-f')
		self.args.append('-l')
		for parts in getProcMountsNew():
			if parts[0].startswith(self.storageDevice.devicePoint):
				self.args.append(parts[0])
				self.mountpoints.append(parts[0])
		if not self.mountpoints:
			print(f"[{self.__class__.__name__}] No mountpoints found?")
			self.cmd = 'true'
			self.args = [self.cmd]
		else:
			self.postconditions.append(ReturncodePostcondition())

	def afterRun(self):
		if self.debug:
			print(f"[{self.__class__.__name__}] DEBUG Output:\n")
			print(self.log)


class UnmountSwapTask(LoggingTask):
	def __init__(self, job, storageDevice, debug):
		self.debug = debug
		LoggingTask.__init__(self, job, _("Unmount"))
		self.storageDevice = storageDevice
		self.mountpoints = []

	def prepare(self):
		self.setTool('swapoff')
		swaps = fileReadLines("/proc/swaps", default=[])
		swaps = [x for x in swaps if x.startswith(f"/dev/{self.storageDevice.disk}")]
		for line in swaps:
			parts = line.split()
			self.args.append(parts[0])
		if not swaps:
			if self.debug:
				print(f"[{self.__class__.__name__}] No mountpoints found!")
			self.cmd = 'true'
			self.args = [self.cmd]

	def afterRun(self):
		if self.debug:
			print(f"[{self.__class__.__name__}] DEBUG Output:\n")
			print(self.log)


class MountTask(LoggingTask):
	def __init__(self, job, storageDevice, mountDevice="", debug=False):
		self.debug = debug
		LoggingTask.__init__(self, job, _("Mount"))
		self.storageDevice = storageDevice
		self.mountDevice = mountDevice
		self.nomoutFile = f"/dev/nomount.{self.storageDevice.disk}"

	def prepare(self):
		try:
			unlink(self.nomoutFile)
		except Exception as e:
			print(f"[{self.__class__.__name__}] ERROR: Failed to remove /dev/nomount file: {e}")

		if self.mountDevice:
			part = "p1" if "mmcblk" in self.storageDevice.disk else "1"
			mountPoint = f"/media/{self.storageDevice.disk}{part}"
			devicePoint = f"/dev/{self.storageDevice.disk}{part}"
			if not exists(mountPoint):
				mkdir(mountPoint, 0o755)
			self.setCmdline(f"mount -t auto {devicePoint} {mountPoint}")
		else:
			self.setCmdline("mount -a")

	def afterRun(self):
		if self.debug:
			print(f"[{self.__class__.__name__}] DEBUG Output:\n")
			print(self.log)


class MkfsTask(LoggingTask):
	def __init__(self, job, debug):
		self.debug = debug
		LoggingTask.__init__(self, job, _("Creating file system"))

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
				print(f"[{self.__class__.__name__}] Error: {err}!")
			return  # Don't log the progress.
		self.log.append(data)

	def afterRun(self):
		if self.debug:
			print(f"[{self.__class__.__name__}] DEBUG Output:\n")
			print(self.log)


def getProcMountsNew(strict=False):
	lines = fileReadLines("/proc/mounts", default=None if strict else [])
	if strict and not lines:
		raise OSError(_("Unable to read the list of mounted file systems."))
	result = []
	for line in [x for x in lines if x and (strict or x.startswith("/dev/"))]:
		# Replace encoded space (\040) and newline (\012) characters with actual space and newline
		parts = [x.replace("\\040", " ").replace("\\011", "\t").replace("\\012", "\n").replace("\\134", "\\") for x in line.split()]
		if strict and len(parts) < 4:
			raise OSError(_("Unable to read the list of mounted file systems."))
		result.append(parts)
	return result


def cleanMediaDirs():
	mounts = getProcMountsNew()
	mounts = [x[1] for x in mounts if x[1].startswith("/media/")]
	try:
		directories = listdir("/media")
	except OSError as err:
		print(f"[Storage] Error {err.errno}: Unable to list '/media'!  ({err.strerror})")
		return
	for directory in directories:
		if directory not in ("audiocd", "autofs", "hdd", "net"):
			mediaDirectory = join("/media/", directory)
			if mediaDirectory not in mounts and not ismount(mediaDirectory):
				print(f"[Storage] remove directory {mediaDirectory} because of unmount")
				try:
					rmdir(mediaDirectory)
				except OSError as err:
					print(f"[Storage] Error {err.errno}: Failed delete '{mediaDirectory}'!  ({err.strerror})")
