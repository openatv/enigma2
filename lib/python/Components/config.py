#  temp stuff :)
class configBoolean:
	def __init__(self, reg):
		self.reg = reg
		self.val = 0
	
	def toggle(self):
		self.val += 1
		self.val %= 3
	
	def __str__(self):
		return ("NO", "YES", "MAYBE")[self.val]

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
			
	def __str__(self):			#needed by configlist
		return ("0", "10", "20", "30", "40", "50", "60", "70", "80", "90", "100")[self.val]

class ConfigSubsection:
	def __init__(self):
		pass

class configElement:
	def __init__(self, configPath, control, defaultValue):
		self.configPath = configPath
		self.value = 0	#read from registry else use default
		self.controlType = control
		self.notifierList = [ ]
	def addNotifier(self, notifier):
		self.notifierList.append(notifier);
		notifier(self);
