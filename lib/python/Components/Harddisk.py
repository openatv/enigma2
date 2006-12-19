from os import system

from Tools.Directories import SCOPE_HDD, resolveFilename

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

		host = self.index / 4
		bus = (self.index & 2)
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

	def capacity(self):
		procfile = tryOpen(self.prochdx + "capacity")
		
		if procfile == "":
			return ""

		line = procfile.readline()
		procfile.close()
		
		try:
			cap = int(line)
		except:
			return ""
		
		cap = cap / 1000 * 512 / 1000
		
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
					stat = os.statvfs(parts[1])
				except OSError:
					continue
				free = stat.f_bfree/1000 * stat.f_bsize/1000
				break
		procfile.close()
		return free		

	def numPartitions(self):
		try:
			idedir = os.listdir(self.devidex)
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
		cmd = "/bin/umount " + self.devidex + "part*"
		res = system(cmd)
		return (res >> 8)

	def createPartition(self):
		cmd = "/sbin/sfdisk -f " + self.devidex + "disc"
		sfdisk = os.popen(cmd, "w")
		sfdisk.write("0,\n;\n;\n;\ny\n")
		sfdisk.close()
		return 0

	def mkfs(self):
		cmd = "/sbin/mkfs.ext3 -T largefile -m0 " + self.devidex + "part1"
		res = system(cmd)
		return (res >> 8)

	def mount(self):
		cmd = "/bin/mount -t ext3 " + self.devidex + "part1 /hdd"
		res = system(cmd)
		return (res >> 8)

	def createMovieFolder(self):
		res = system("mkdir " + resolveFilename(SCOPE_HDD))
		return (res >> 8)
		
	errorList = [ _("Everything is fine"), _("Creating partition failed"), _("Mkfs failed"), _("Mount failed"), _("Create movie folder failed"), _("Unmount failed")]

	def initialize(self):
		self.unmount()

		if self.createPartition() != 0:
			return -1

		if self.mkfs() != 0:
			return -2

		if self.mount() != 0:
			return -3

		if self.createMovieFolder() != 0:
			return -4
		
		return 0
		
def existHDD(num):
	mediafile = tryOpen(num2prochdx(num) + "media")

	if mediafile == "":
		return -1

	line = mediafile.readline()
	mediafile.close()
	
	if line.startswith("disk"):
		return 1
	
	return -1

class Partition:
	def __init__(self, mountpoint, description = ""):
		self.mountpoint = mountpoint
		self.description = description

	def stat(self):
		return os.statvfs(self.mountpoint)

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
		
		for hddNum in range(8):
			if existHDD(hddNum):
				hdd = Harddisk(hddNum)
				self.hdd.append(hdd)

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

	def getMountedPartitions(self):
		return [x for x in self.partitions if x.mounted()]

harddiskmanager = HarddiskManager()
