import xml.sax
from Tools.Directories import crawlDirectory, resolveFilename, SCOPE_CONFIG, SCOPE_SKIN
from Components.NimManager import nimmanager
from Components.Ipkg import IpkgComponent
from enigma import eConsoleAppContainer
import os

class InfoHandlerParseError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class InfoHandler(xml.sax.ContentHandler):
	def __init__(self, prerequisiteMet, directory):
		self.attributes = {}
		self.directory = directory
		self.list = []
		self.globalprerequisites = {}
		self.prerequisites = {}
		self.elements = []
		self.validFileTypes = ["skin", "config", "services", "favourites", "package"]
		self.prerequisitesMet = prerequisiteMet
	
				
	def printError(self, error):
		print "Error in defaults xml files:", error
		raise InfoHandlerParseError, error
    
	def startElement(self, name, attrs):
		print name, ":", attrs.items()
		self.elements.append(name)
		if name in ["hardware", "bcastsystem", "satellite"]:
			if not attrs.has_key("type"):
					self.printError(str(name) + " tag with no type attribute")
			if self.elements[-3] == "default":
				prerequisites = self.globalprerequisites
			else:
				prerequisites = self.prerequisites
			if not prerequisites.has_key(name):
				prerequisites[name] = []
			prerequisites[name].append(str(attrs["type"]))
		if name == "files":
			if attrs.has_key("type"):
				if attrs["type"] == "directories":
					self.attributes["filestype"] = "directories"
				# TODO add a compressed archive type
		if name == "file":
			self.prerequisites = {}
			if not attrs.has_key("type"):
				self.printError("file tag with no type attribute")
			else:
				if not attrs.has_key("name"):
					self.printError("file tag with no name attribute")
				else:	
					if not attrs.has_key("directory"):
						directory = self.directory
					type = attrs["type"]
					if not type in self.validFileTypes:
						self.printError("file tag with invalid type attribute")
					else:
						self.filetype = type
						self.fileattrs = attrs
	def endElement(self, name):
		print "end", name
		print "self.elements:", self.elements
		self.elements.pop()
		if name == "file":
			print "prerequisites:", self.prerequisites
			if len(self.prerequisites) == 0 or self.prerequisitesMet(self.prerequisites):
				if not self.attributes.has_key(self.filetype):
					self.attributes[self.filetype] = []
				if self.fileattrs.has_key("directory"):
					directory = str(self.fileattrs["directory"])
					if len(directory) < 1 or directory[0] != "/":
						directory = self.directory + directory
				else:
					directory = self.directory
				self.attributes[self.filetype].append({ "name": str(self.fileattrs["name"]), "directory": directory })
    
		if name == "default":
			self.list.append({"attributes": self.attributes, 'prerequisites': self.globalprerequisites})
			self.attributes = {}
			self.globalprerequisites = {}
    
	def characters(self, data):
		if self.elements[-1] == "author":
			self.attributes["author"] = str(data)
		if self.elements[-1] == "name":
			self.attributes["name"] = str(data)
		print "characters", data
		
class DreamInfoHandler:
	STATUS_WORKING = 0
	STATUS_DONE = 1
	STATUS_ERROR = 2
	STATUS_INIT = 4
	
	def __init__(self, statusCallback):
		self.directory = "/"
		
		self.console = eConsoleAppContainer()
		self.console.appClosed.get().append(self.installNext)
		
		self.statusCallback = statusCallback
		self.setStatus(self.STATUS_INIT)
				
		self.packageslist = []
	
	def readInfo(self, directory, file):
		print "Reading .info file", file
		handler = InfoHandler(self.prerequisiteMet, directory)
		try:
			xml.sax.parse(file, handler)
			for entry in handler.list:
				self.packageslist.append((entry,file)) 
		except InfoHandlerParseError:
			print "file", file, "ignored due to errors in the file"
		print handler.list
        
	# prerequisites = True: give only packages matching the prerequisites
	def fillPackagesList(self, prerequisites = True):
		self.packageslist = []
		packages = crawlDirectory(self.directory, ".*\.info$")
		for package in packages:
			self.readInfo(package[0] + "/", package[0] + "/" + package[1])
			
		if prerequisites:
			for package in self.packageslist[:]:
				if not self.prerequisiteMet(package[0]["prerequisites"]):
					self.packageslist.remove(package)
		return packages
			
	def prerequisiteMet(self, prerequisites):
		# TODO: we need to implement a hardware detection here...
		print "prerequisites:", prerequisites
		met = True
		if prerequisites.has_key("bcastsystem"):
			for bcastsystem in prerequisites["bcastsystem"]:
				if nimmanager.hasNimType(bcastsystem):
					return True
			return False
		if prerequisites.has_key("hardware"):
			for hardware in prerequisites["hardware"]:
				# TODO: hardware detection
				met = True
		return True
			
	def installPackage(self, index):
		print "installing package with index", index, "and name", self.packageslist[index][0]["attributes"]["name"]
		
		attributes = self.packageslist[index][0]["attributes"]
		self.installingAttributes = attributes
		self.attributeNames = ["skin", "config", "favourites", "package", "services"]
		self.currentAttributeIndex = 0
		self.currentIndex = -1
		self.installNext()
		
	def setStatus(self, status):
		self.status = status
		self.statusCallback(self.status, None)
						
	def installNext(self, *args, **kwargs):
		self.currentIndex += 1
		attributes = self.installingAttributes
		
		if self.currentAttributeIndex >= len(self.attributeNames): # end reached
			self.setStatus(self.STATUS_DONE)
			return
		
		self.setStatus(self.STATUS_WORKING)		
		
		currentAttribute = self.attributeNames[self.currentAttributeIndex]
		
		print "installing", currentAttribute, "with index", self.currentIndex
		
		if attributes.has_key(currentAttribute):
			if self.currentIndex >= len(attributes[currentAttribute]): # all jobs done for current attribute
				self.currentIndex = -1
				self.currentAttributeIndex += 1
				self.installNext()
				return
		else: # nothing to install here
			self.currentAttributeIndex += 1
			self.installNext()
			return
			
		if currentAttribute == "skin":
			skin = attributes["skin"][self.currentIndex]
			self.installSkin(skin["directory"], skin["name"])
		elif currentAttribute == "config":
			if self.currentIndex == 0:
				from Components.config import configfile
				configfile.save()
			config = attributes["config"][self.currentIndex]
			self.mergeConfig(config["directory"], config["name"])
		elif currentAttribute == "favourites":
			favourite = attributes["favourites"][self.currentIndex]
			self.installFavourites(favourite["directory"], favourite["name"])
		elif currentAttribute == "package":
			package = attributes["package"][self.currentIndex]
			self.installIPK(package["directory"], package["name"])
		elif currentAttribute == "services":
			service = attributes["services"][self.currentIndex]
			self.mergeServices(service["directory"], service["name"])
				
	def readfile(self, filename):
		if not os.path.isfile(filename):
			return []
		fd = open(filename)
		lines = fd.readlines()
		fd.close()
		return lines
			
	def mergeConfig(self, directory, name, merge = True):
		print "merging config:", directory, " - ", name

		newconfig = self.readfile(directory + name)
		newconfig.sort()
		print newconfig
		
		if merge:
			oldconfig = self.readfile(resolveFilename(SCOPE_CONFIG) + "settings")
			oldconfig.sort()
			print oldconfig
		else:
			oldconfig = []
		
		# merge with duplicate removal through dictionary
		mergeddict = {}
		for list in oldconfig, newconfig:
			for entry in list:
				splitentry = entry.split("=")
				if len(splitentry) != 2: # wrong entry
					continue
				mergeddict[splitentry[0]] = splitentry[1].strip()
		
		print "new:"
		fd = open(resolveFilename(SCOPE_CONFIG) + "settings", "w")
		for entry in mergeddict.keys():
			print entry + "=" + mergeddict[entry]
			fd.write(entry + "=" + mergeddict[entry] + '\n')
		fd.close()
		self.installNext()
		#configfile.load()
		
		
	def installIPK(self, directory, name):
		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)
		self.ipkg.startCmd(IpkgComponent.CMD_INSTALL, {'package': directory + name})
		
	def ipkgCallback(self, event, param):
		print "ipkgCallback"
		if event == IpkgComponent.EVENT_DONE:
			self.installNext()
		elif event == IpkgComponent.EVENT_ERROR:
			self.installNext()
	
	def installSkin(self, directory, name):
		print "installing skin:", directory, " - ", name
		print "cp -a %s %s" % (directory, resolveFilename(SCOPE_SKIN))
		if self.console.execute("cp -a %s %s" % (directory, resolveFilename(SCOPE_SKIN))):
			print "execute failed"
			self.installNext()

	def readServices(self, filename):
		newservicesfile = self.readfile(filename)
		
		transponders = []
		services = []
		status = 0 # 0 = start, 1 = transponders, 2 = services
		count = 0
		while count < len(newservicesfile):
			if status == 0:
				if newservicesfile[count].strip() == "transponders":
					status = 1
			elif status == 1: # reading transponders
				if newservicesfile[count].strip() == "end": # finished reading transponders
					pass
				elif newservicesfile[count].strip() == "services": # start of services section
					status = 2
				else:
					transponders.append(''.join(newservicesfile[count:count + 3]))
					count += 2
			elif status == 2: # reading services
				if newservicesfile[count].strip() == "end": # finished reading file
					break
				else:
					services.append(''.join(newservicesfile[count:count + 3]))
					count += 2
			count += 1
		return (transponders, services)
	
	def mergeServices(self, directory, name, merge = False):
		print "merging services:", directory, " - ", name
		
		newtransponders, newservices = self.readServices(directory + name)
		if merge:
			oldtransponders, oldservices = self.readServices(resolveFilename(SCOPE_CONFIG) + "lamedb")
		else:
			oldtransponders, oldservices = [], []
		
		fp = open(resolveFilename(SCOPE_CONFIG) + "lamedb", "w")
		fp.write("eDVB services /3/\n")
		
		fp.write("transponders\n")
		for transponderlist in oldtransponders, newtransponders:
			for transponder in transponderlist:
				fp.write(transponder)
		fp.write("end\n")
		
		fp.write("services\n")
		for serviceslist in oldservices, newservices:
			for service in serviceslist:
				fp.write(service)
		fp.write("end\n")
		
		fp.close()
		self.installNext()

	def installFavourites(self, directory, name):
		print "installing favourites:", directory, " - ", name

		if self.console.execute("cp %s %s" % ((directory + name), resolveFilename(SCOPE_CONFIG))):
			print "execute failed"
			self.installNext()
