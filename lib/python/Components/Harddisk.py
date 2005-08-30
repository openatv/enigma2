import os

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

	def index(self):
		return self.index

	def capacity(self):
		procfile = tryOpen(self.prochdx + "capacity")
		
		if procfile == "":
			return -1

		line = procfile.readline()
		procfile.close()
		
		try:
			cap = int(line)
		except:
			return -1
		
		return cap	
						
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
		os.system(cmd)

	def createPartition(self):
		cmd = "/sbin/sfdisk -f " + self.devidex + "disc"
		sfdisk = os.popen(cmd, "w")
		sfdisk.write("0,\n;\n;\n;\ny\n")
		sfdisk.close()
		return 0

	def mkfs(self):
		cmd = "/sbin/mkfs.ext3 -T largefile -m0 " + self.devidex + "part1"
		res = os.system(cmd)
		return (res >> 8)

	def mount(self):
		cmd = "/bin/mount -t ext3 " + self.devidex + "part1 /hdd"
		res = os.system(cmd)
		return (res >> 8)

	def createMovieFolder(self):
		res = os.system("mkdir /hdd/movie")
		return (res >> 8)
		
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

class HarddiskManager:
	def __init__(self):
		hddNum = 0
		self.hdd = [ ]
		while 1:
			if existHDD(hddNum) == 1:
				self.hdd.append(Harddisk(hddNum))
			hddNum += 1
			
			if hddNum > 8:
				break

	def HDDList(self):
		list = [ ]
		for hd in self.hdd:
			cap = hd.capacity() / 1000 * 512 / 1000
			print cap
			hdd = hd.model() + " (" 
			if hd.index & 1:
				hdd += "slave"
			else:	
				hdd += "master"
			if cap > 0:
				hdd += ", %d.%03d GB" % (cap/1024, cap%1024)
			hdd += ")"

			print hdd
			
#			if hd.index == 0:
#				if hd.initialize() == 0:
#					print "hdd status ok"
#				else:
#					print "hdd status ok"

			list.append((hdd, hd))
		return list


harddiskmanager = HarddiskManager()


