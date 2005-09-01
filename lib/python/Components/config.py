class configFile:
	def __init__(self):
		pass

	def openFile(self):
		try:
			self.file = open("config")
		except IOError:
			self.file = ""

	def getKey(self, key, dataType):
		self.openFile()			#good idea? (open every time we need it?) else we have to seek
		while 1:
			line = self.file.readline()
			if line == "":
				break
			if line.startswith(key):
				x = line.find("=")
				if x > -1:
					self.file.close()
					return dataType(line[x + 1:])

		self.file.close()
		return ""

class configBoolean:
	def __init__(self, parent):
		self.parent = parent
		
	def checkValues(self):
		if self.parent.value < 0:
			self.parent.value = 0	

		if(self.parent.value >= (len(self.parent.vals) - 1)):
			self.parent.value = len(self.parent.vals) - 1

	def cancel(self):
		self.parent.reload()

	def save(self):
		print "save bool"

	def handleKey(self, key):
		if key == 1:
			self.parent.value = self.parent.value - 1
		if key == 2:
			self.parent.value = self.parent.value + 1
		
		self.checkValues()			

		self.parent.change()	

	def __call__(self):			#needed by configlist
		self.checkValues()			
		return ("text", self.parent.vals[self.parent.value])

class configValue:
	def __init__(self, obj):
		self.obj = obj
		
	def __str__(self):
		return self.obj

class Config:
	def __init__(self):
		pass

	def saveLine(self, file, element):
		#FIXME can handle INTs only
		line = element.configPath + "=" + str(element.value) + "\n"
		file.write(line)

	def save(self):
		fileHandle = open("config", "w")
		
		for groupElement in self.__dict__.items():
			for element in groupElement[1].__dict__.items():
				self.saveLine(fileHandle, element[1])
		
		fileHandle.close()		
		
		while 1:
			pass	
		
config = Config();
configfile = configFile()

class ConfigSlider:
	def __init__(self, parent):
		self.parent = parent

	def cancel(self):
		self.parent.reload()

	def save(self):
		print "slider - save"

	def checkValues(self):
		if self.parent.value < 0:
			self.parent.value = 0	

		if self.parent.value > 10:
			self.parent.value = 10	

	def handleKey(self, key):
		if key == 1:
			self.parent.value = self.parent.value - 1
		if key == 2:
			self.parent.value = self.parent.value + 1
					
		self.checkValues()	
		self.parent.change()	

	def __call__(self):			#needed by configlist
		self.checkValues()	
		return ("slider", self.parent.value * 10)

class ConfigSubsection:
	def __init__(self):
		pass

class configElement:
	def dataType(self, control):
		if control == ConfigSlider:
			return int;
		elif control == configBoolean:
			return int;
		else: 
			return ""	

	def loadData(self):
		try:
			value = configfile.getKey(self.configPath, self.dataType(self.controlType))
		except:		
			value = ""

		if value == "":
			print "value not found - using default"
			self.value = self.defaultValue
		else:
			self.value = value
			print "value ok"

	def __init__(self, configPath, control, defaultValue, vals):
		self.configPath = configPath
		self.defaultValue = defaultValue
		self.controlType = control
		self.vals = vals
		self.notifierList = [ ]
		self.loadData()		
	def addNotifier(self, notifier):
		self.notifierList.append(notifier);
		notifier(self);
	def change(self):
		for notifier in self.notifierList:
			notifier(self)
	def reload(self):
		self.loadData()
