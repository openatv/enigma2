class configFile:
	def __init__(self):
		self.changed = 0
		self.configElements = { }
		try:
			self.file = open("config")
		except IOError:
			print "cannot open config file"
			return 
		
		while 1:
			line = self.file.readline()
			if line == "":
				break
			
			if line.startswith("#"):		#skip comments
				continue	
				
			self.addElement(line)
		self.file.close()

	def addElement(self, line):
		x = line.find("=")
		if x > -1:
			self.configElements[line[:x]] = line[x + 1:]
	
	def getKey(self, key):
		return self.configElements[key]

	def setKey(self, key, value):
		self.changed = 1
		self.configElements[key] = value

	def save(self):
		if self.changed == 0:		#no changes, so no write to disk needed
			return
			
		fileHandle = open("config", "w")
		
		for x in self.configElements:
			wstr = x + "=" + self.configElements[x]
			
			if wstr[len(wstr) - 1] != '\n':
				wstr = wstr + "\n"

			fileHandle.write(wstr)

		fileHandle.close()		

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
		self.parent.save()

	def handleKey(self, key):
		if key == config.prevElement:
			self.parent.value = self.parent.value - 1
		if key == config.nextElement:
			self.parent.value = self.parent.value + 1
		
		self.checkValues()			

		self.parent.change()	

	def __call__(self):			#needed by configlist
		self.checkValues()			
		return ("text", self.parent.vals[self.parent.value])
		
class configSequence:
	def __init__(self, parent):
		self.parent = parent
		
	def checkValues(self):
		pass
#		if self.parent.value < 0:
#			self.parent.value = 0	
#
#		if(self.parent.value >= (len(self.parent.vals) - 1)):
#			self.parent.value = len(self.parent.vals) - 1
#
	def cancel(self):
		self.parent.reload()

	def save(self):
		self.parent.save()

	def handleKey(self, key):
		if key == config.prevElement:
			self.parent.value = self.parent.value - 1
		if key == config.nextElement:
			self.parent.value = self.parent.value + 1
		
		self.checkValues()			

		self.parent.change()	

	def __call__(self):			#needed by configlist
		value = ""
		for i in self.parent.value:
			if value != "":
				value += self.parent.vals
			value += str(i)
		return ("text", value)

class configValue:
	def __init__(self, obj):
		self.obj = obj
		
	def __str__(self):
		return self.obj

class Config:
	def __init__(self):
		self.choseElement = 0
		self.prevElement = 1
		self.nextElement = 2
						
config = Config();
configfile = configFile()

class ConfigSlider:
	def __init__(self, parent):
		self.parent = parent

	def cancel(self):
		self.parent.reload()

	def save(self):
		self.parent.save()

	def checkValues(self):
		if self.parent.value < 0:
			self.parent.value = 0	

		if self.parent.value > 10:
			self.parent.value = 10	

	def handleKey(self, key):
		if key == config.prevElement:
			self.parent.value = self.parent.value - 1
		if key == config.nextElement:
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
	def datafromFile(self, control, data):
		if control == ConfigSlider:
			return int(data);
		elif control == configBoolean:
			return int(data);
		elif control == configSequence:
			list = [ ]
			part = data.split(self.vals)
			for x in part:
				list.append(int(x))
			return list
		else: 
			return ""	

	def datatoFile(self, control, data):
		if control == ConfigSlider:
			return str(data);
		elif control == configBoolean:
			return str(data);
		elif control == configSequence:
			value = ""
			for i in data:
				if value !="":
					value += self.vals
				value += str(i)
			return value
		else: 
			return ""	

	def loadData(self):
		try:
			value = self.datafromFile(self.controlType, configfile.getKey(self.configPath))
		except:		
			value = ""

		if value == "":
			print "value not found - using default"
			self.value = self.defaultValue
			self.save()		#add missing value to dict
		else:
			self.value = value

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
	def save(self):
		configfile.setKey(self.configPath, self.datatoFile(self.controlType,self.value))
