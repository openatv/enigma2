from ServiceReference import ServiceReference
import os

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
	
class PlaylistIOM3U(PlaylistIO):
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
			if entry[0] != "#":
				# TODO: use e2 facilities to create a service ref from file
				if entry[0] == "/":
					self.addService(ServiceReference("4097:0:0:0:0:0:0:0:0:0:" + entry))
				else:
					self.addService(ServiceReference("4097:0:0:0:0:0:0:0:0:0:" + os.path.dirname(filename) + "/" + entry))
		file.close()
		return self.list
		
	def save(self, filename = None):
		return self.ERROR
	
class PlaylistIOPLS(PlaylistIO):
	def __init__(self):
		PlaylistIO.__init__(self)
	
	def open(self, filename):
		self.clear()
		try:
			file = open(filename, "r")
		except IOError:
			return None
		entry = file.readline().strip()
		if entry == "[playlist]": # extended pls
			while True:
				entry = file.readline().strip()
				if entry == "":
					break
				if entry[0:4] == "File":
					pos = entry.find('=') + 1
					newentry = entry[pos:]
					# TODO: use e2 facilities to create a service ref from file
					if newentry[0] == "/":
						self.addService(ServiceReference("4097:0:0:0:0:0:0:0:0:0:" + newentry))
					else:
						self.addService(ServiceReference("4097:0:0:0:0:0:0:0:0:0:" + os.path.dirname(filename) + "/" + newentry))
		else:
			playlist = PlaylistIOM3U()
			return playlist.open(filename)
		file.close()
		return self.list
		
	def save(self, filename = None):
		return self.ERROR