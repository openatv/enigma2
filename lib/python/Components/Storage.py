#Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License
#
#Copyright (c) 2025 jbleyel

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#1. Non-Commercial Use: You may not use the Software or any derivative works
#   for commercial purposes without obtaining explicit permission from the
#   copyright holder.
#2. Share Alike: If you distribute or publicly perform the Software or any
#   derivative works, you must do so under the same license terms, and you
#   must make the source code of any derivative works available to the
#   public.
#3. Attribution: You must give appropriate credit to the original author(s)
#   of the Software by including a prominent notice in your derivative works.
#THE SOFTWARE IS PROVIDED "AS IS," WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL
#THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR
#OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE,
#ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#OTHER DEALINGS IN THE SOFTWARE.
#
#For more details about the CC BY-NC-SA 4.0 License, please visit:
#https://creativecommons.org/licenses/by-nc-sa/4.0/


from glob import glob
from os import listdir, mkdir, rmdir, unlink
from os.path import exists, ismount, join, realpath


from Components.Task import Job, LoggingTask, ConditionTask, ReturncodePostcondition
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

		job = Job(_("Initializing storage device..."))

		UnmountTask(job, self)

		UnmountSwapTask(job, self)

		task = LoggingTask(job, _("Removing partition table"))
		task.setTool('parted')
		alignment = "min" if self.size < (1024 ** 3) else "opt"  # 1GB -> "min" else "opt"
		parttype = "gpt" if self.size > (2 * (1024 ** 3)) else "msdos"  # 2GB -> "gpt" else "msdos"
		task.args += ['-a', alignment, '-s', self.disk_path, 'mklabel', parttype]
		task.weighting = 1

		if uuids:
			task = UUIDTask(job, uuids)
			task.weighting = 1
		return job

	def createFormatJob(self, options):
		fsType = options.get("fsType", "ext4")
		label = options.get("label")
		label.replace(" ", "_")
		job = Job(_("Formatting storage device..."))
		UnmountTask(job, self)
		UnmountSwapTask(job, self)
		task = MkfsTask(job, _("Creating file system"))
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
			task = UUIDTask(job, {self.devicePoint.replace("/dev/", ""): self.UUID})
			task.weighting = 1
		task = MountTask(job, self)
		task.weighting = 3
		return job

	def createInitializeJob(self, options=None):
		options = options or {}
		partitions = options.get("partitions") or []
		uuids = options.get("uuids") or {}
		fsTypes = options.get("fsTypes") or {}
		partitionType = options.get("partitionType")
		mountDevice = options.get("mountDevice")

		job = Job(_("Initializing storage device..."))
		print(f"[StorageDevice] createInitializeJob size: {scaleNumber(self.size, format="%.2f")}")
		print(f"[StorageDevice] createInitializeJob partitions: {partitions} uuids: {uuids}")

		UnmountTask(job, self)

		UnmountSwapTask(job, self)

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
		#parttype = "gpt" if self.size > (2 * (1024 ** 3)) else "msdos"  # 2GB -> "gpt" else "msdos"
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
			label.replace(" ", "_")
			device = f"{self.devicePoint}p{index + 1}" if "mmcblk" in self.devicePoint else f"{self.devicePoint}{index + 1}"
			uuid = uuids.get(device)
			oldFsType = fsTypes.get(device)
			task = MkfsTask(job, _("Creating file system"))
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
			task = UUIDTask(job, uuids)
			task.weighting = 1
		task = MountTask(job, self, mountDevice=mountDevice)
		task.weighting = 3
		return job

	def createExt4ConversionJob(self, options=None):
		job = Job(_("Converting ext3 to ext4..."))

		if self.findMount():
			UnmountTask(job, self)
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
			task = UUIDTask(job, {self.devicePoint.replace("/dev/", ""): self.UUID})
			task.weighting = 1

		task = MountTask(job, self)
		task.weighting = 3
		return job

	def createCheckJob(self, options=None):
		job = Job(_("Checking file system..."))
		if self.findMount():
			UnmountTask(job, self)
		task = LoggingTask(job, "fsck")
		if self.fsType == "ntfs":
			task.setTool("ntfsfix")
		else:
			task.setTool(f"fsck.{self.fsType}")
			if self.fsType == "exfat":
				task.args += ["-p"]
			else:
				task.args += ["-f", "-p"]
		task.args.append(self.devicePoint)
		task = MountTask(job, self)
		task.weighting = 3
		return job


class UUIDTask(ConditionTask):
	def __init__(self, job, uuids):
		ConditionTask.__init__(self, job, _("UUID"), 1)
		self.uuids = uuids

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
						print(f"[UUIDTask] fstab UUID changed from {olduuid} to {newuuid}")
						saveFstab = True
						break
				for i, line in enumerate(knownDevices):
					if line.startswith(olduuid):
						knownDevices[i] = line.replace(f"{olduuid}", f"{newuuid}")
						print(f"[UUIDTask] known_devices UUID changed from {olduuid} to {newuuid}")
						saveknownDevices = True
						break
			if not newuuid:
				for i, line in enumerate(fstab):
					if line.find(f"UUID={olduuid}") != -1:
						fstab[i] = ""
						print(f"[UUIDTask] fstab UUID {olduuid} removed")
						saveFstab = True
						break
				for i, line in enumerate(knownDevices):
					if line.startswith(olduuid):
						knownDevices[i] = ""
						print(f"[UUIDTask] known_devices UUID {olduuid} removed")
						saveknownDevices = True
						break
		if saveFstab:
			fileWriteLines("/etc/fstab", fstab, source=MODULE_NAME)
		if saveknownDevices:
			knownDevices = [x for x in knownDevices if x]
			fileWriteLines("/etc/udev/known_devices", knownDevices, source=MODULE_NAME)
		return True


class UnmountTask(LoggingTask):
	def __init__(self, job, storageDevice):
		LoggingTask.__init__(self, job, _("Unmount"))
		self.storageDevice = storageDevice
		self.nomoutFile = f"/dev/nomount.{self.storageDevice.disk}"
		self.mountpoints = []

	def prepare(self):
		try:
			open(self.nomoutFile, "wb").close()
		except Exception as e:
			print("[UnmountTask] ERROR: Failed to create /dev/nomount file:", e)
		self.setTool('umount')
		self.args.append('-f')
		self.args.append('-l')
		for parts in getProcMountsNew():
			if parts[0].startswith(self.storageDevice.devicePoint):
				self.args.append(parts[0])
				self.mountpoints.append(parts[0])
		if not self.mountpoints:
			print("[UnmountTask] No mountpoints found?")
			self.cmd = 'true'
			self.args = [self.cmd]
		else:
			self.postconditions.append(ReturncodePostcondition())


class UnmountSwapTask(LoggingTask):
	def __init__(self, job, storageDevice):
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
			print("[UnmountSwapTask] No mountpoints found?")
			self.cmd = 'true'
			self.args = [self.cmd]


class MountTask(LoggingTask):
	def __init__(self, job, storageDevice, mountDevice=""):
		LoggingTask.__init__(self, job, _("Mount"))
		self.storageDevice = storageDevice
		self.mountDevice = mountDevice
		self.nomoutFile = f"/dev/nomount.{self.storageDevice.disk}"

	def prepare(self):
		try:
			unlink(self.nomoutFile)
		except Exception as e:
			print("[MountTask] ERROR: Failed to remove /dev/nomount file:", e)

		if self.mountDevice:
			part = "p1" if "mmcblk" in self.storageDevice.disk else "1"
			mountPoint = f"/media/{self.storageDevice.disk}{part}"
			devicePoint = f"/dev/{self.storageDevice.disk}{part}"
			if not exists(mountPoint):
				mkdir(mountPoint, 0o755)
			self.setCmdline(f"mount -t auto {devicePoint} {mountPoint}")
		else:
			self.setCmdline("mount -a")


class MkfsTask(LoggingTask):
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
				print(f"[MkfsTask] MkfsTask - [Mkfs] Error: {err}!")
			return  # Don't log the progress.
		self.log.append(data)


def getProcMountsNew():
	lines = fileReadLines("/proc/mounts", default=[])
	result = []
	for line in [x for x in lines if x and x.startswith("/dev/")]:
		# Replace encoded space (\040) and newline (\012) characters with actual space and newline
		result.append([s.replace("\\040", " ").replace("\\012", "\n") for s in line.strip(" \n").split(" ")])
	return result


def cleanMediaDirs():
	mounts = getProcMountsNew()
	mounts = [x[1] for x in mounts if x[1].startswith("/media/")]
	for directory in listdir("/media"):
		if directory not in ("autofs", "hdd"):
			mediaDirectory = join("/media/", directory)
			if mediaDirectory not in mounts and not ismount(mediaDirectory):
				print(f"[Storage] remove directory {mediaDirectory} because of unmount")
				try:
					rmdir(mediaDirectory)
				except OSError as err:
					print(f"[Storage] Error {err.errno}: Failed delete '{mediaDirectory}'!  ({err.strerror})")
