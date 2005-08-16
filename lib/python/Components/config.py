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

class config:
	def __init__(self):
		pass
	def Slider(self):		 # ok???
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
