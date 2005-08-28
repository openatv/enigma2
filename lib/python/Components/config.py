#  temp stuff :)
class configBoolean:
	def __init__(self, parent):
		self.parent = parent
		self.val = parent.value
		self.vals = parent.vals
			
	def handleKey(self, key):
		if key == 1:
			self.val = self.val - 1
		if key == 2:
			self.val = self.val + 1
			
		if self.val < 0:
			self.val = 0	

#		if self.val > 1:
#			self.val = 1	
	
	def __call__(self):			#needed by configlist
	
		print len(self.vals)
		print self.val
			
		if(self.val > (len(self.vals) - 1)):
			self.val = len(self.vals) - 1
	
		return ("text",self.vals[self.val])

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
		self.val = parent.value
	def handleKey(self, key):
		if key == 1:
			self.val = self.val - 1
		if key == 2:
			self.val = self.val + 1
			
		if self.val < 0:
			self.val = 0	

		if self.val > 10:
			self.val = 10	
	def __call__(self):			#needed by configlist
		return ("slider", self.val * 10)

class ConfigSubsection:
	def __init__(self):
		pass

class configElement:
	def __init__(self, configPath, control, defaultValue, vals):
		self.configPath = configPath
#		self.value = 0	#read from registry else use default
		self.value = defaultValue	#read from registry else use default
		self.controlType = control
		self.vals = vals
		self.notifierList = [ ]
	def addNotifier(self, notifier):
		self.notifierList.append(notifier);
		notifier(self);
