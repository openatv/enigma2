import xml.sax
from Tools.Directories import crawlDirectory, resolveFilename, SCOPE_CONFIG, SCOPE_SKIN, copyfile, copytree
from Components.NimManager import nimmanager
from Components.Ipkg import IpkgComponent
from Components.config import config, configfile
from Tools.HardwareInfo import HardwareInfo
from enigma import eConsoleAppContainer, eDVBDB
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
		self.data = ""

	def printError(self, error):
		raise InfoHandlerParseError, error

	def startElement(self, name, attrs):
		self.elements.append(name)

		if name in ("hardware", "bcastsystem", "satellite", "tag", "flag"):
			if not attrs.has_key("type"):
					self.printError(str(name) + " tag with no type attribute")
			if self.elements[-3] in ("default", "package"):
				prerequisites = self.globalprerequisites
			else:
				prerequisites = self.prerequisites
			if not prerequisites.has_key(name):
				prerequisites[name] = []
			prerequisites[name].append(str(attrs["type"]))

		if name == "info":
			self.foundTranslation = None
			self.data = ""

		if name == "files":
			if attrs.has_key("type"):
				if attrs["type"] == "directories":
					self.attributes["filestype"] = "directories"
				elif attrs["type"] == "package":
					self.attributes["filestype"] = "package"

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

		if name == "package":
			if attrs.has_key("details"):
				self.attributes["details"] = str(attrs["details"])
			if attrs.has_key("name"):
				self.attributes["name"] = str(attrs["name"])
			if attrs.has_key("packagename"):
				self.attributes["packagename"] = str(attrs["packagename"])
			if attrs.has_key("packagetype"):
				self.attributes["packagetype"] = str(attrs["packagetype"])
			if attrs.has_key("needsRestart"):
				self.attributes["needsRestart"] = str(attrs["needsRestart"])
			if attrs.has_key("shortdescription"):
				self.attributes["shortdescription"] = str(attrs["shortdescription"])

		if name == "screenshot":
			if attrs.has_key("src"):
				self.attributes["screenshot"] = str(attrs["src"])

	def endElement(self, name):
		self.elements.pop()
		if name == "file":
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

		if name in ( "default", "package" ):
			self.list.append({"attributes": self.attributes, 'prerequisites': self.globalprerequisites})
			self.attributes = {}
			self.globalprerequisites = {}

	def characters(self, data):
		if self.elements[-1] == "author":
			self.attributes["author"] = str(data)
		if self.elements[-1] == "name":
			self.attributes["name"] = str(data)
		if self.elements[-1] == "packagename":
			self.attributes["packagename"] = str(data)
		if self.elements[-1] == "needsRestart":
			self.attributes["needsRestart"] = str(data)
		if self.elements[-1] == "shortdescription":
			self.attributes["shortdescription"] = str(data)
		if self.elements[-1] == "description":
			self.data += data.strip()
			self.attributes["description"] = str(self.data)


class PackageInfoHandler:
	STATUS_WORKING = 0
	STATUS_DONE = 1
	STATUS_ERROR = 2
	STATUS_INIT = 4

	def __init__(self, statusCallback, blocking = False, neededTag = None, neededFlag = None):
		self.directory = "/"

		self.neededTag = neededTag
		self.neededFlag = neededFlag

		# caution: blocking should only be used, if further execution in enigma2 depends on the outcome of
		# the installer!
		self.blocking = blocking

		self.currentlyInstallingMetaIndex = None

		self.console = eConsoleAppContainer()
		self.console.appClosed.append(self.installNext)
		self.reloadFavourites = False

		self.statusCallback = statusCallback
		self.setStatus(self.STATUS_INIT)

		self.packageslist = []
		self.packagesIndexlist = []
		self.packageDetails = []

	def readInfo(self, directory, file):
		handler = InfoHandler(self.prerequisiteMet, directory)
		try:
			xml.sax.parse(file, handler)
			for entry in handler.list:
				self.packageslist.append((entry,file))
		except InfoHandlerParseError:
			pass

	def readIndex(self, directory, file):
		handler = InfoHandler(self.prerequisiteMet, directory)
		try:
			xml.sax.parse(file, handler)
			for entry in handler.list:
				self.packagesIndexlist.append((entry,file))
		except InfoHandlerParseError:
			pass

	def readDetails(self, directory, file):
		self.packageDetails = []
		handler = InfoHandler(self.prerequisiteMet, directory)
		try:
			xml.sax.parse(file, handler)
			for entry in handler.list:
				self.packageDetails.append((entry,file))
		except InfoHandlerParseError:
			pass

	def fillPackagesList(self, prerequisites = True):
		self.packageslist = []
		packages = []
		if not isinstance(self.directory, list):
			self.directory = [self.directory]

		for directory in self.directory:
			packages += crawlDirectory(directory, ".*\.info$")

		for package in packages:
			self.readInfo(package[0] + "/", package[0] + "/" + package[1])

		if prerequisites:
			for package in self.packageslist[:]:
				if not self.prerequisiteMet(package[0]["prerequisites"]):
					self.packageslist.remove(package)
		return self.packageslist

	def fillPackagesIndexList(self, prerequisites = True):
		self.packagesIndexlist = []
		indexfileList = []

		if not isinstance(self.directory, list):
			self.directory = [self.directory]

		for indexfile in os.listdir(self.directory[0]):
			if indexfile.startswith("index-"):
				if indexfile.endswith(".xml"):
					if indexfile[-7:-6] == "_":
						continue
					indexfileList.append(indexfile)
		if len(indexfileList):
			for file in indexfileList:
				neededFile = self.directory[0] + "/" + file
				if os.path.isfile(neededFile):
					self.readIndex(self.directory[0] + "/" , neededFile)

		if prerequisites:
			for package in self.packagesIndexlist[:]:
				if not self.prerequisiteMet(package[0]["prerequisites"]):
					self.packagesIndexlist.remove(package)
		return self.packagesIndexlist

	def fillPackageDetails(self, details = None):
		self.packageDetails = []
		detailsfile = details
		if not isinstance(self.directory, list):
			self.directory = [self.directory]
		self.readDetails(self.directory[0] + "/", self.directory[0] + "/" + detailsfile)
		return self.packageDetails

	def prerequisiteMet(self, prerequisites):
		met = True
		if self.neededTag is None:
			if prerequisites.has_key("tag"):
				return False
		elif self.neededTag == 'ALL_TAGS':
				return True
		else:
			if prerequisites.has_key("tag"):
				if not self.neededTag in prerequisites["tag"]:
					return False
			else:
				return False

		if self.neededFlag is None:
			if prerequisites.has_key("flag"):
				return False
		else:
			if prerequisites.has_key("flag"):
				if not self.neededFlag in prerequisites["flag"]:
					return False
			else:
				return True

		if prerequisites.has_key("satellite"):
			for sat in prerequisites["satellite"]:
				if int(sat) not in nimmanager.getConfiguredSats():
					return False
		if prerequisites.has_key("bcastsystem"):
			has_system = False
			for bcastsystem in prerequisites["bcastsystem"]:
				if nimmanager.hasNimType(bcastsystem):
					has_system = True
			if not has_system:
				return False
		if prerequisites.has_key("hardware"):
			hardware_found = False
			for hardware in prerequisites["hardware"]:
				if hardware == HardwareInfo().device_name:
					hardware_found = True
			if not hardware_found:
				return False
		return True

	def installPackages(self, indexes):
		if len(indexes) == 0:
			self.setStatus(self.STATUS_DONE)
			return
		self.installIndexes = indexes
		self.currentlyInstallingMetaIndex = 0
		self.installPackage(self.installIndexes[self.currentlyInstallingMetaIndex])

	def installPackage(self, index):
		if len(self.packageslist) <= index:
			return

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
		if self.reloadFavourites:
			self.reloadFavourites = False
			db = eDVBDB.getInstance().reloadBouquets()

		self.currentIndex += 1
		attributes = self.installingAttributes

		if self.currentAttributeIndex >= len(self.attributeNames):
			if self.currentlyInstallingMetaIndex is None or self.currentlyInstallingMetaIndex >= len(self.installIndexes) - 1:
				self.setStatus(self.STATUS_DONE)
				return
			else:
				self.currentlyInstallingMetaIndex += 1
				self.currentAttributeIndex = 0
				self.installPackage(self.installIndexes[self.currentlyInstallingMetaIndex])
				return

		self.setStatus(self.STATUS_WORKING)

		currentAttribute = self.attributeNames[self.currentAttributeIndex]

		if attributes.has_key(currentAttribute):
			if self.currentIndex >= len(attributes[currentAttribute]):
				self.currentIndex = -1
				self.currentAttributeIndex += 1
				self.installNext()
				return
		else:
			self.currentIndex = -1
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
		if os.path.isfile(directory + name):
			config.loadFromFile(directory + name, base_file=False)
			configfile.save()
		self.installNext()

	def installIPK(self, directory, name):
		if self.blocking:
			os.system("opkg install " + directory + name)
			self.installNext()
		else:
			self.ipkg = IpkgComponent()
			self.ipkg.addCallback(self.ipkgCallback)
			self.ipkg.startCmd(IpkgComponent.CMD_INSTALL, {'package': directory + name})

	def ipkgCallback(self, event, param):
		if event == IpkgComponent.EVENT_DONE:
			self.installNext()
		elif event == IpkgComponent.EVENT_ERROR:
			self.installNext()

	def installSkin(self, directory, name):
		if self.blocking:
			copytree(directory, resolveFilename(SCOPE_SKIN))
			self.installNext()
		else:
			if self.console.execute("cp -a %s %s" % (directory, resolveFilename(SCOPE_SKIN))):
				self.installNext()

	def mergeServices(self, directory, name, merge = False):
		if os.path.isfile(directory + name):
			db = eDVBDB.getInstance()
			db.reloadServicelist()
			db.loadServicelist(directory + name)
			db.saveServicelist()
		self.installNext()

	def installFavourites(self, directory, name):
		self.reloadFavourites = True

		if self.blocking:
			copyfile(directory + name, resolveFilename(SCOPE_CONFIG))
			self.installNext()
		else:
			if self.console.execute("cp %s %s" % ((directory + name), resolveFilename(SCOPE_CONFIG))):
				self.installNext()
