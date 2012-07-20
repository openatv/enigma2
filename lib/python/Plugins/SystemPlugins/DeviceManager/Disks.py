import os
import re

class Disks():
	ptypes = {
	 "0": "Empty"             , "24":  "NEC DOS"        , "81":  "Minix / old Lin"     , "bf":  "Solaris",
	 "1": "FAT12"             , "39":  "Plan 9"         , "82":  "Linux swap / Solaris", "c1":  "DRDOS/sec (FAT)",
	 "2": "XENIX root"        , "3c":  "PartitionMagic" , "83":  "Linux"               , "c4":  "DRDOS/sec (FAT)",
	 "3": "XENIX usr"         , "40":  "Venix 80286"    , "84":  "OS/2 hidden C:"      , "c6":  "DRDOS/sec (FAT)",
	 "4": "FAT16 <32M"        , "41":  "PPC PReP Boot"  , "85":  "Linux extended"      , "c7":  "Syrinx",
	 "5": "Extended"          , "42":  "SFS"            , "86":  "NTFS volume set"     , "da":  "Non-FS data",
	 "6": "FAT16"             , "4d":  "QNX4.x"         , "87":  "NTFS volume set"     , "db":  "CP/M / CTOS",
	 "7": "HPFS/NTFS"         , "4e":  "QNX4.x 2nd part", "88":  "Linux plaintext"     , "de":  "Dell Utility",
	 "8": "AIX"               , "4f":  "QNX4.x 3rd part", "8e":  "Linux LVM"           , "df":  "BootIt",
	 "9": "AIX bootable"      , "50":  "OnTrack DM"     , "93":  "Amoeba"              , "e1":  "DOS access",
	 "a": "OS/2 Boot Manager" , "51":  "OnTrack DM6 Aux", "94":  "Amoeba BBT"          , "e3":  "DOS R/O",
	 "b": "W95 FAT32"         , "52":  "CP/M"           , "9f":  "BSD/OS"              , "e4":  "SpeedStor",
	 "c": "W95 FAT32 (LBA)"   , "53":  "OnTrack DM6 Aux", "a0":  "IBM Thinkpad hi"     , "eb":  "BeOS fs",
	 "e": "W95 FAT16 (LBA)"   , "54":  "OnTrackDM6"     , "a5":  "FreeBSD"             , "ee":  "GPT",
	 "f": "W95 Ext'd (LBA)"   , "55":  "EZ-Drive"       , "a6":  "OpenBSD"             , "ef":  "EFI",
	"10": "OPUS"              , "56":  "Golden Bow"     , "a7":  "NeXTSTEP"            , "f0":  "Linux/PA-RISC",
	"11": "Hidden FAT12"      , "5c":  "Priam Edisk"    , "a8":  "Darwin UFS"          , "f1":  "SpeedStor",
	"12": "Compaq diagnostic" , "61":  "SpeedStor"      , "a9":  "NetBSD"              , "f4":  "SpeedStor",
	"14": "Hidden FAT16"      , "63":  "GNU HURD"       , "ab":  "Darwin boot"         , "f2":  "DOS secondary",
	"16": "Hidden FAT16"      , "64":  "Novell Netware" , "af":  "HFS / HFS+"          , "fb":  "VMware VMFS",
	"17": "Hidden HPFS/NTFS"  , "65":  "Novell Netware" , "b7":  "BSDI fs"             , "fc":  "VMware VMKCORE",
	"18": "AST SmartSleep"    , "70":  "DiskSecure Mult", "b8":  "BSDI swap"           , "fd":  "Linux raid auto",
	"1b": "Hidden W95 FAT32"  , "75":  "PC/IX"          , "bb":  "Boot Wizard hidden"  , "fe":  "LANstep",
	"1c": "Hidden W95 FAT32"  , "80":  "Old Minix"      , "be":  "Solaris boot"        , "ff":  "BBT",
	"1e": "Hidden W95 FAT16" }

	def __init__(self):
		self.disks = []
		self.readDisks()
		self.readPartitions()

	def readDisks(self):
		partitions = open("/proc/partitions")
		for part in partitions:
			res = re.sub("\s+", " ", part).strip().split(" ")
			if res and len(res) == 4:
				if len(res[3]) == 3 and res[3][:2] == "sd":
					self.disks.append([ res[3],
										int(res[2]) * 1024,
										self.isRemovable(res[3]),
										self.getModel(res[3]),
										self.getVendor(res[3]),
										[ ] ])

	def readPartitions(self):
		partitions = open("/proc/partitions")
		for part in partitions:
			res = re.sub("\s+", " ", part).strip().split(" ")
			if res and len(res) == 4:
				if len(res[3]) > 3 and res[3][:2] == "sd":
					for i in self.disks:
						if i[0] == res[3][:3]:
							i[5].append([ res[3], int(res[2]) * 1024, self.getTypeName(res[3]), self.getType(res[3]) ])
							break

	def isRemovable(self, device):
		removable = open("/sys/block/%s/removable" % device, "r").read().strip()
		if removable == "1":
			return True
		return False

	# in this case device is full device with slice number... for example sda1
	def getTypeName(self, device):
		cmd = "/usr/sbin/sfdisk -c /dev/%s %s" % (device[:3], device[3:])
		fdisk = os.popen(cmd, "r")
		res = fdisk.read().strip()
		fdisk.close()
		if res in self.ptypes.keys():
			return self.ptypes[res]
		return res

	def getType(self, device):
		cmd = "/usr/sbin/sfdisk -c /dev/%s %s" % (device[:3], device[3:])
		fdisk = os.popen(cmd, "r")
		res = fdisk.read().strip()
		fdisk.close()
		return res

	def getModel(self, device):
		return open("/sys/block/%s/device/model" % device, "r").read().strip()

	def getVendor(self, device):
		return open("/sys/block/%s/device/vendor" % device, "r").read().strip()

	def isMounted(self, device):
		mounts = open("/proc/mounts")
		for mount in mounts:
			res = mount.split(" ")
			if res and len(res) > 1:
				if res[0][:8] == "/dev/%s" % device:
					mounts.close()
					return True
		mounts.close()
		return False

	def isMountedP(self, device, partition):
		mounts = open("/proc/mounts")
		for mount in mounts:
			res = mount.split(" ")
			if res and len(res) > 1:
				if res[0][:9] == "/dev/%s%s" % (device, partition):
					mounts.close()
					return True
		mounts.close()
		return False

	def getMountedP(self, device, partition):
		mounts = open("/proc/mounts")
		for mount in mounts:
			res = mount.split(" ")
			if res and len(res) > 1:
				if res[0] == "/dev/%s%d" % (device, partition):
					mounts.close()
					return res[1]
		mounts.close()
		return None

	def umount(self, device):
		mounts = open("/proc/mounts")
		for mount in mounts:
			res = mount.split(" ")
			if res and len(res) > 1:
				if res[0][:8] == "/dev/%s" % device:
					print "[DeviceManager] umount %s" % res[0]
					if os.system("umount -f %s" % res[0]) != 0:
						mounts.close()
						return False
		mounts.close()
		return True

	def umountP(self, device, partition):
		if os.system("umount -f /dev/%s%d" % (device, partition)) != 0:
			return False

		return True

	def mountP(self, device, partition, path):
		if os.system("mount /dev/%s%d %s" % (device, partition, path)) != 0:
			return False
		return True

	def mount(self, fdevice, path):
		if os.system("mount /dev/%s %s" % (fdevice, path)) != 0:
			return False
		return True

	# type:
	# 0 -> one partition
	# 1 -> two partition (2 x 50%)
	# 2 -> two partition (75% 25%)
	# 3 -> three partition (3 x 33%)
	# 4 -> four partition (4 x 25%)
	#
	# return value:
	# 0 -> ok
	# -1 -> umount failed
	# -2 -> sfdisk failed
	def fdisk(self, device, size, type, fstype=0):
		if self.isMounted(device):
			print "[DeviceManager] device is mounted... umount"
			if not self.umount(device):
				print "[DeviceManager] umount failed!"
				return -1

		if fstype == 0 or fstype == 1:
			ptype = "83"
		elif fstype == 2:
			ptype = "7"
		elif fstype == 3:
			ptype = "b"

		if type == 0:
			psize = (size / (1024*1024))
			if psize > 128000:
					# Start at sector 8 to better support 4k aligned disks
					print "[DeviceManager] Detected >128GB disk, using 4k alignment"
					flow = "8,+,%s\n;0,0\n;0,0\n;0,0\ny\n" % ptype
			else:
				flow = "0,+,%s\n;\n;\n;\ny\n" % ptype
		elif type == 1:
			psize = (size / (1024*1024)) / 2
			flow = "0,%d,%s\n+,+,%s\n;\n;\ny\n" % (psize, ptype, ptype)
		elif type == 2:
			psize = ((size / (1024*1024)) / 4) * 3
			flow = "0,%d,%s\n+,+,%s\n;\n;\ny\n" % (psize, ptype, ptype)
		elif type == 3:
			psize = (size / (1024*1024)) / 3
			flow = "0,%d,%s\n+,%d,%s\n+,+,%s\n;\ny\n" % (psize, ptype, psize, ptype, ptype)
		elif type == 4:
			psize = (size / (1024*1024)) / 4
			flow = "0,%d,%s\n+,%d,%s\n+,%d,%s\n+,+,%s\ny\n" % (psize, ptype, psize, ptype, psize, ptype, ptype)

		cmd = "%s -f -uM /dev/%s" % ("/usr/sbin/sfdisk", device)
		sfdisk = os.popen(cmd, "w")
		sfdisk.write(flow)
		if sfdisk.close():
			return -2

		# we need to call mdev just to be sure all devices are populated
		os.system("/sbin/mdev -s")
		return 0

	# return value:
	# 0 -> ok
	# -1 -> umount failed
	# -2 -> sfdisk failed
	def chkfs(self, device, partition, fstype=0):
		fdevice = "%s%d" % (device, partition)
		print "[DeviceManager] checking device %s" % fdevice
		if self.isMountedP(device, partition):
			oldmp = self.getMountedP(device, partition)
			print "[DeviceManager] partition is mounted... umount"
			if not self.umountP(device, partition):
				print "[DeviceManager] umount failed!"
				return -1
		else:
			oldmp = ""

		if self.isMountedP(device, partition):
				return -1

		if fstype == 0 or fstype == 1:
#			ret = os.system("/sbin/fsck /dev/%s" % fdevice)
			ret = os.system("/sbin/e2fsck.e2fsprogs -C 0 -f -p /dev/%s" % fdevice)
		elif fstype == 2:
			ret = os.system("/usr/bin/ntfsfix /dev/%s" % fdevice)
		elif fstype == 3:
			ret = os.system("/usr/sbin/dosfsck -a /dev/%s" % fdevice)

		if len(oldmp) > 0:
			self.mount(fdevice, oldmp)

		if ret == 0:
			return 0
		return -2;

	def mkfs(self, device, partition, fstype=0):
		dev = "%s%d" % (device, partition)
		size = 0
		partitions = open("/proc/partitions")
		for part in partitions:
			res = re.sub("\s+", " ", part).strip().split(" ")
			if res and len(res) == 4:
				if res[3] == dev:
					size = int(res[2])
					break

		if size == 0:
			return -1

		if self.isMountedP(device, partition):
			oldmp = self.getMountedP(device, partition)
			print "[DeviceManager] partition is mounted... umount"
			if not self.umountP(device, partition):
				print "[DeviceManager] umount failed!"
				return -2
		else:
			oldmp = ""

		if fstype == 0:
			cmd = "/sbin/mkfs.ext4 "
			psize = (size / (1024))
			if psize > 20000:
				version = open("/proc/version","r").read().split(' ', 4)[2].split('.',2)[:2]
				if (version[0] > 3) and (version[1] >= 2):
					# Linux version 3.2 supports bigalloc and -C option, use 256k blocks
					cmd += "-O bigalloc -C 262144 "
			cmd += "-m0 -O dir_index /dev/" + dev
		elif fstype == 1:
			cmd = "/sbin/mkfs.ext3 "
			psize = (size / (1024))
			if psize > 250000:
				# No more than 256k i-nodes (prevent problems with fsck memory requirements)
				cmd += "-T largefile -O sparse_super -N 262144 "
			elif psize > 16384:
				# between 16GB and 250GB: 1 i-node per megabyte
				cmd += "-T largefile -O sparse_super "
			elif psize > 2048:
				# Over 2GB: 32 i-nodes per megabyte
				cmd += "-T largefile -N %s " % str(psize * 32)
			cmd += "-m0 -O dir_index /dev/" + dev
		elif fstype == 2:
			cmd = "/sbin/mkfs.ntfs -f /dev/" + dev
		elif fstype == 3:
			cmd = "/usr/sbin/mkfs.vfat -F32 /dev/" + dev
		else:
			if len(oldmp) > 0:
				self.mount(dev, oldmp)
			return -3

		ret = os.system(cmd)

		if len(oldmp) > 0:
			self.mount(dev, oldmp)

		if ret == 0:
			return 0
		return -3;
