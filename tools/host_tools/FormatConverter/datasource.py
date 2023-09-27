from input import inputChoices


class datasource:
	def __init__(self):
		self.clear()

	def setDatasources(self, datasources):
		self.datasources = datasources

	def getCapabilities(self):
		return []

	def getName(self):
		return "N/A"

	def getStatus(self):
		text = str(len(self.transponderlist.keys())) + " Satellites" + "\n"
		return text

	def printAll(self):
		for sat in self.transponderlist.keys():
			print("***********")
			print("sat:", sat, self.satnames[sat])
			for transponder in self.transponderlist[sat]:
				print(transponder)

	def clear(self):
		self.transponderlist = {}
		self.satnames = {}

	def read(self):
		pass

	def write(self):
		pass

	def addSat(self, satname, satpos):
		if satpos not in self.transponderlist:
			self.transponderlist[satpos] = []
			self.satnames[satpos] = satname

	def addTransponder(self, satpos, transponder):
		if len(transponder.keys()) >= 6:
			self.transponderlist[satpos].append(transponder)


class genericdatasource(datasource):
	def __init__(self):
		datasource.__init__(self)
		self.source = self.destination = None

	def getName(self):
		return "Generic Datasource"

	def getCapabilities(self):
		return [("copy data from one source to another", self.copy), ("merge data from one source into another", self.merge)]

	def copy(self):
		self.copymerge(action="copy")

	def merge(self):
		self.copymerge(action="merge")

	def copymerge(self, action="copy"):
		choice = -1
		while choice is not None:
			choice = inputChoices(["select source", "select destination", "copy now!"])
			if choice == 0:
				print("\nselect source:")
				self.source = self.selectDatasource()
			elif choice == 1:
				print("\nselect destination")
				self.destination = self.selectDatasource()
			elif choice == 2:
				self.docopymerge(action)

	def docopymerge(self, action="copy"):
		if self.source is None:
			print("select a source first!")
		elif self.destination is None:
			print("select a destination first!")
		else:
			if action == "copy":
				print("copying ", end=' ')
			elif action == "merge":
				print("merging ", end=' ')
			print("from %s to %s" % (self.source.getName(), self.destination.getName()))
			countsat = 0
			counttransponder = 0
			if action == "copy":
				self.destination.clear()
			for satpos in self.source.transponderlist.keys():
				countsat += 1
				self.destination.addSat(self.source.satnames[satpos], satpos)
				for transponder in self.source.transponderlist[satpos]:
					counttransponder += 1
					self.destination.addTransponder(satpos, transponder)
			print("copied %d sats with %d transponders" % (countsat, counttransponder))

	def selectDatasource(self):
		list = []
		sources = []
		for source in self.datasources:
			if source != self:
				list.append(source.getName() + (" (%d sats)" % len(source.transponderlist.keys())))
				sources.append(source)
		choice = inputChoices(list)
		if choice is None:
			return None
		return sources[choice]
