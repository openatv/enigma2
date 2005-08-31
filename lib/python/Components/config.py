#  temp stuff :)
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
		print "save"

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

def configEntry(obj):
	# das hier ist ein zugriff auf die registry...
	if obj == "HKEY_LOCAL_ENIGMA/IMPORTANT/USER_ANNOYING_STUFF/SDTV/FLASHES/GREEN":
		return ("SDTV green flashes", configBoolean(obj))
	elif obj == "HKEY_LOCAL_ENIGMA/IMPORTANT/USER_ANNOYING_STUFF/HDTV/FLASHES/GREEN":
		return ("HDTV reen flashes", configBoolean(obj))
	else:
		return ("invalid", "")

class Config:
	def __init__(self):
		pass
		
config = Config();

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
	def __init__(self, configPath, control, defaultValue, vals):
		self.configPath = configPath
#		self.value = 0	#read from registry else use default
		self.value = defaultValue	#read from registry else use default
		self.defaultValue = defaultValue
		self.controlType = control
		self.vals = vals
		self.notifierList = [ ]
	def addNotifier(self, notifier):
		self.notifierList.append(notifier);
		notifier(self);
	def change(self):
		for notifier in self.notifierList:
			notifier(self)
	def reload(self):
		self.value = self.defaultValue	#HACK :-)
