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

	def hdindex(self):
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
			hdd = hd.model() + " (" 
			if hd.index & 1:
				hdd += "slave"
			else:	
				hdd += "master"
			if cap > 0:
				hdd += ", %d,%d GB" % (cap/1024, cap%1024)
			hdd += ")"

			list.append((hdd, hd))
		return list
