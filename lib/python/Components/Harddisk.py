from os import system, listdir, statvfs, popen, makedirs

from Tools.Directories import SCOPE_HDD, resolveFilename
from Tools.CList import CList

from SystemInfo import SystemInfo

def tryOpen(filename):
	try:
		procFile = open(filename)
	except IOError:
		return ""
	return procFile

def num2prochdx(num):
	return "/proc/ide/hd" + ("a","b","c","d","e","f","g","h","i")[num] + "/"

class Harddisk:
	def __init__(self, index):
		self.index = index

		host = (self.index & 2) >> 1
		bus = 0
		target = (self.index & 1)

		self.prochdx = num2prochdx(index)
		self.devidex = "/dev/ide/host%d/bus%d/target%d/lun0/" % (host, bus, target)

	def getIndex(self):
		return self.index

	def bus(self):
		ret = ""

		if self.index & 2:
			ret = "External (CF) - "
		else:
			ret = "Internal - "
		
		if self.index & 1:
			return ret + "Slave"
		else:
			return ret + "Master"

	def diskSize(self):
		procfile = tryOpen(self.prochdx + "capacity")

		if procfile == "":
			return 0

		line = procfile.readline()
		procfile.close()

		try:
			cap = int(line)
		except:
			return 0

		return cap / 1000 * 512 / 1000

	def capacity(self):
		cap = self.diskSize()
		if cap == 0:
			return ""
		
		return "%d.%03d GB" % (cap/1024, cap%1024)

	def model(self):
		procfile = tryOpen(self.prochdx + "model")

		if procfile == "":
			return ""

		line = procfile.readline()
		procfile.close()

		return line.strip()

	def free(self):
		procfile = tryOpen("/proc/mounts")
		
		if procfile == "":
			return -1

		free = -1
		while 1:
			line = procfile.readline()
			if line == "":
				break
			if line.startswith(self.devidex):
				parts = line.strip().split(" ")
				try:
					stat = statvfs(parts[1])
				except OSError:
					continue
				free = stat.f_bfree/1000 * stat.f_bsize/1000
				break
		procfile.close()
		return free		

	def numPartitions(self):
		try:
			idedir = listdir(self.devidex)
		except OSError:
			return -1
		numPart = -1
		for filename in idedir:
			if filename.startswith("disc"):
				numPart += 1
			if filename.startswith("part"):
				numPart += 1
		return numPart

	def unmount(self):
		procfile = tryOpen("/proc/mounts")

		if procfile == "":
			return -1

		cmd = "/bin/umount"

		for line in procfile:
			if line.startswith(self.devidex):
				parts = line.split()
				cmd = ' '.join([cmd, parts[1]])

		procfile.close()

		res = system(cmd)
		return (res >> 8)

	def createPartition(self):
		cmd = "/sbin/sfdisk -f " + self.devidex + "disc"
		sfdisk = popen(cmd, "w")
		sfdisk.write("0,\n;\n;\n;\ny\n")
		sfdisk.close()
		return 0

	def mkfs(self):
		cmd = "/sbin/mkfs.ext3 "
		if self.diskSize() > 4 * 1024:
			cmd += "-T largefile "
		cmd += "-m0 " + self.devidex + "part1"
		res = system(cmd)
		return (res >> 8)

	def mount(self):
		cmd = "/bin/mount -t ext3 " + self.devidex + "part1"
		res = system(cmd)
		return (res >> 8)

	def createMovieFolder(self):
		try:
			makedirs(resolveFilename(SCOPE_HDD))
		except OSError:
			return -1
		return 0

	def fsck(self):
		# We autocorrect any failures
		# TODO: we could check if the fs is actually ext3
		cmd = "/sbin/fsck.ext3 -f -p " + self.devidex + "part1"
		res = system(cmd)
		return (res >> 8)

	errorList = [ _("Everything is fine"), _("Creating partition failed"), _("Mkfs failed"), _("Mount failed"), _("Create movie folder failed"), _("Fsck failed"), _("Please Reboot"), _("Filesystem contains uncorrectable errors"), _("Unmount failed")]

	def initialize(self):
		self.unmount()

		if self.createPartition() != 0:
			return -1

		if self.mkfs() != 0:
			return -2

		if self.mount() != 0:
			return -3

		#only create a movie folder on the internal hdd
		if not self.index & 2 and self.createMovieFolder() != 0:
			return -4
		
		return 0

	def check(self):
		self.unmount()

		res = self.fsck()
		if res & 2 == 2:
			return -6

		if res & 4 == 4:
			return -7

		if res != 0 and res != 1:
			# A sum containing 1 will also include a failure
			return -5

		if self.mount() != 0:
			return -3

		return 0

def existHDD(num):
	mediafile = tryOpen(num2prochdx(num) + "media")

	if mediafile == "":
		return False

	line = mediafile.readline()
	mediafile.close()

	if line.startswith("disk"):
		return True

	return False

class Partition:
	def __init__(self, mountpoint, description = "", force_mounted = False):
		self.mountpoint = mountpoint
		self.description = description
		self.force_mounted = force_mounted
		self.is_hotplug = force_mounted # so far; this might change.

	def stat(self):
		return statvfs(self.mountpoint)

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

	def mounted(self):
		# THANK YOU PYTHON FOR STRIPPING AWAY f_fsid.
		# TODO: can os.path.ismount be used?
		if self.force_mounted:
			return True
		procfile = tryOpen("/proc/mounts")
		for n in procfile.readlines():
			if n.split(' ')[1] == self.mountpoint:
				return True
		return False

class HarddiskManager:
	def __init__(self):
		hddNum = 0
		self.hdd = [ ]
		
		self.partitions = [ ]
		
		self.on_partition_list_change = CList()
		
		for hddNum in range(8):
			if existHDD(hddNum):
				hdd = Harddisk(hddNum)
				self.hdd.append(hdd)

		self.enumerateBlockDevices()

		SystemInfo["Harddisc"] = len(self.hdd) > 0

		# currently, this is just an enumeration of what's possible,
		# this probably has to be changed to support automount stuff.
		# still, if stuff is mounted into the correct mountpoints by
		# external tools, everything is fine (until somebody inserts 
		# a second usb stick.)
		p = [
					("/media/hdd", _("Harddisk")), 
					("/media/card", _("Card")), 
					("/media/cf", _("Compact Flash")),
					("/media/mmc1", _("MMC Card")),
					("/media/net", _("Network Mount")),
					("/media/ram", _("Ram Disk")),
					("/media/usb", _("USB Stick")),
					("/", _("Internal Flash"))
				]
		
		for x in p:
			self.partitions.append(Partition(mountpoint = x[0], description = x[1]))

	def enumerateBlockDevices(self):
		print "enumerating block devices..."
		import os
		for blockdev in os.listdir("/sys/block"):
			devpath = "/sys/block/" + blockdev
			error = False
			removable = False
			blacklisted = False
			is_cdrom = False
			partitions = []
			try:
				removable = bool(int(open(devpath + "/removable").read()))
				dev = int(open(devpath + "/dev").read().split(':')[0])
				if dev in [7, 31]: # loop, mtdblock
					blacklisted = True
				if blockdev[0:2] == 'sr':
					is_cdrom = True
				if blockdev[0:2] == 'hd':
					try:
						media = open("/proc/ide/%s/media" % blockdev).read()
						if media.find("cdrom") != -1:
							is_cdrom = True
					except IOError:
						error = True
				# check for partitions
				if not is_cdrom:
					for partition in os.listdir(devpath):
						if partition[0:len(blockdev)] != blockdev:
							continue
						partitions.append(partition)
			except IOError:
				error = True
			print "found block device '%s':" % blockdev, 
			if error:
				print "error querying properties"
			elif blacklisted:
				print "blacklisted"
			else:
				print "ok, removable=%s, cdrom=%s, partitions=%s" % (removable, is_cdrom, partitions)
				self.addHotplugPartition(blockdev, blockdev)
				for part in partitions:
					self.addHotplugPartition(part, part)

	def getAutofsMountpoint(self, device):
		return "/autofs/%s/" % (device)

	def addHotplugPartition(self, device, description):
		p = Partition(mountpoint = self.getAutofsMountpoint(device), description = description, force_mounted = True)
		self.partitions.append(p)
		self.on_partition_list_change("add", p)

	def removeHotplugPartition(self, device):
		mountpoint = self.getAutofsMountpoint(device)
		for x in self.partitions[:]:
			if x.mountpoint == mountpoint:
				self.partitions.remove(x)
				self.on_partition_list_change("remove", x)

	def HDDCount(self):
		return len(self.hdd)

	def HDDList(self):
		list = [ ]
		for hd in self.hdd:
			hdd = hd.model() + " (" 
			hdd += hd.bus()
			cap = hd.capacity()	
			if cap != "":
				hdd += ", " + cap
			hdd += ")"
			list.append((hdd, hd))

		return list

	def getMountedPartitions(self, onlyhotplug = False):
		return [x for x in self.partitions if (x.is_hotplug or not onlyhotplug) and x.mounted()]

harddiskmanager = HarddiskManager()
