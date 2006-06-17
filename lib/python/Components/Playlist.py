from ServiceReference import ServiceReference

class PlaylistIO:	
	def __init__(self):
		self.list = []
	
	# returns a list of services or None if filename is not a valid playlist
	def open(self, filename):
		return None
	
	OK = 0
	FILEEXISTS = 1
	WRITEERROR = 2
	ERROR = 3
	UNSUPPORTED_FILES_IN_PLAYLIST = 4
	
	def save(self, filename = None):
		return self.ERROR
		
	def clear(self):
		del self.list[:]
		
	def addService(self, service):
		self.list.append(service)
		
		
class PlaylistIOInternal(PlaylistIO):
	def __init__(self):
		PlaylistIO.__init__(self)
	
	def open(self, filename):
		self.clear()
		try:
			file = open(filename, "r")
		except IOError:
			return None
		while True:
			entry = file.readline().strip()
			if entry == "":
				break
			self.addService(ServiceReference(entry))
		file.close()
		return self.list
		
	def save(self, filename = None):
		print "Writing playlist into file", filename
		file = open(filename, "w")
		for x in self.list:
			file.write(str(x) + "\n")
		file.close()
		
		return self.OK