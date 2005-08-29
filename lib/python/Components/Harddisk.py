

def tryOpen(filename):
	try:
		procFile = open(filename)
	except IOError:
		return ""
	return procFile

class Harddisk:
	def __init__(self, index):
		self.index = index
		#perhaps this is easier?
		self.prochdx = "/proc/ide/hd" + ("a","b","c","d","e","f","g","h")[index] + "/"
		
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
		pass
		
	