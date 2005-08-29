import os

def tryOpen(filename):
	try:
		procFile = open(filename)
	except IOError:
		return ""
	return procFile

class Harddisk:
	def __init__(self, index):
		self.index = index

		host = self.index / 4
		bus = (self.index & 2)
		target = (self.index & 1)

		#perhaps this is easier?
		self.prochdx = "/proc/ide/hd" + ("a","b","c","d","e","f","g","h")[index] + "/"
		self.devidex = "/dev/ide/host" + str(host) + "/bus" + str(bus) + "/target" + str(target) + "/lun0/"

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

		return line

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
