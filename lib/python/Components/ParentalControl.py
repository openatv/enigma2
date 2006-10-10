from Components.config import config, ConfigSubsection, ConfigSelection, ConfigPIN, ConfigYesNo, ConfigSubList
from Components.Input import Input
from Screens.InputBox import InputBox, PinInput
from Screens.MessageBox import MessageBox
from Tools.BoundFunction import boundFunction
from ServiceReference import ServiceReference
from Tools import Notifications
from Tools.Directories import resolveFilename, SCOPE_CONFIG

def InitParentalControl():
	config.ParentalControl = ConfigSubsection()
	config.ParentalControl.configured = ConfigYesNo(default = False)
	config.ParentalControl.mode = ConfigSelection(default = "simple", choices = [("simple", _("simple")), ("complex", _("complex"))])
	config.ParentalControl.storeservicepin = ConfigSelection(default = "never", choices = [("never", _("never")), ("5_minutes", _("5 minutes")), ("30_minutes", _("30 minutes")), ("60_minutes", _("60 minutes")), ("restart", _("until restart"))])
	config.ParentalControl.servicepinactive = ConfigYesNo(default = False)
	config.ParentalControl.setuppinactive = ConfigYesNo(default = False)
	config.ParentalControl.type = ConfigSelection(default = "blacklist", choices = [("whitelist", _("whitelist")), ("blacklist", _("blacklist"))])
	config.ParentalControl.setuppin = ConfigPIN(default = -1)
#	config.ParentalControl.configured = configElement("config.ParentalControl.configured", configSelection, 1, (("yes", _("yes")), ("no", _("no"))))
	#config.ParentalControl.mode = configElement("config.ParentalControl.mode", configSelection, 0, (("simple", _("simple")), ("complex", _("complex"))))
	#config.ParentalControl.storeservicepin = configElement("config.ParentalControl.storeservicepin", configSelection, 0, (("never", _("never")), ("5_minutes", _("5 minutes")), ("30_minutes", _("30 minutes")), ("60_minutes", _("60 minutes")), ("restart", _("until restart"))))
	#config.ParentalControl.servicepinactive = configElement("config.ParentalControl.servicepinactive", configSelection, 1, (("yes", _("yes")), ("no", _("no"))))
	#config.ParentalControl.setuppinactive = configElement("config.ParentalControl.setuppinactive", configSelection, 1, (("yes", _("yes")), ("no", _("no"))))
	#config.ParentalControl.type = configElement("config.ParentalControl.type", configSelection, 0, (("whitelist", _("whitelist")), ("blacklist", _("blacklist"))))
	#config.ParentalControl.setuppin = configElement("config.ParentalControl.setuppin", configSequence, "0000", configSequenceArg().get("PINCODE", (4, "")))

	config.ParentalControl.servicepin = ConfigSubList()

	for i in range(3):
		config.ParentalControl.servicepin.append(ConfigPIN(default = -1))
		#config.ParentalControl.servicepin.append(configElement("config.ParentalControl.servicepin.level" + str(i), configSequence, "0000", configSequenceArg().get("PINCODE", (4, ""))))

class ParentalControl:
	def __init__(self):
		self.open()
		self.serviceLevel = {}
		self.tries = 3
		
	def addWhitelistService(self, service):
		self.whitelist.append(service)
	
	def addBlacklistService(self, service):
		self.blacklist.append(service)

	def setServiceLevel(self, service, level):
		self.serviceLevel[service] = level

	def deleteWhitelistService(self, service):
		self.whitelist.remove(service)
		if self.serviceLevel.has_key(service):
			self.serviceLevel.remove(service)
	
	def deleteBlacklistService(self, service):
		self.blacklist.remove(service)
		if self.serviceLevel.has_key(service):
			self.serviceLevel.remove(service)
				
	def isServicePlayable(self, service, callback):
		if not config.ParentalControl.configured.value:
			return True
		print "whitelist:", self.whitelist
		print "blacklist:", self.blacklist
		print "config.ParentalControl.type.value:", config.ParentalControl.type.value
		print "not in whitelist:", (service not in self.whitelist)
		print "checking parental control for service:", service
		if (config.ParentalControl.type.value == "whitelist" and service not in self.whitelist) or (config.ParentalControl.type.value == "blacklist" and service in self.blacklist):
			self.callback = callback
			print "service:", ServiceReference(service).getServiceName()
			levelNeeded = 0
			if self.serviceLevel.has_key(service):
				levelNeeded = self.serviceLevel[service]
			pinList = self.getPinList()[:levelNeeded + 1]
			Notifications.AddNotificationWithCallback(boundFunction(self.servicePinEntered, service), PinInput, tries = self.tries, pinList = pinList, service = ServiceReference(service).getServiceName(), title = _("this service is protected by a parental control pin"), windowTitle = _("Parental control"))
			return False
		else:
			return True
		
	def protectService(self, service):
		print "protect"
		print "config.ParentalControl.type.value:", config.ParentalControl.type.value
		if config.ParentalControl.type.value == "whitelist":
			if service in self.whitelist:
				self.deleteWhitelistService(service)
		else: # blacklist
			if service not in self.blacklist:
				self.addBlacklistService(service)
		print "whitelist:", self.whitelist
		print "blacklist:", self.blacklist

				
	def unProtectService(self, service):
		print "unprotect"
		print "config.ParentalControl.type.value:", config.ParentalControl.type.value
		if config.ParentalControl.type.value == "whitelist":
			if service.toCompareString() not in self.whitelist:
				self.addWhitelistService(service)
		else: # blacklist
			if service.toCompareString() in self.blacklist:
				self.deleteBlacklistService(service)
		print "whitelist:", self.whitelist
		print "blacklist:", self.blacklist

	def getProtectionLevel(self, serviceref):
		service = serviceref.toCompareString()
		if (config.ParentalControl.type.value == "whitelist" and service not in self.whitelist) or (config.ParentalControl.type.value == "blacklist" and service in self.blacklist):
			if self.serviceLevel.has_key(service):
				return self.serviceLevel[service]
			else:
				return 0
		else:
			return -1
	
	def getPinList(self):
		pinList = []
		for x in config.ParentalControl.servicepin:
			pinList.append(x.value)
		return pinList
	
	def servicePinEntered(self, service, result):
#		levelNeeded = 0
		#if self.serviceLevel.has_key(service):
			#levelNeeded = self.serviceLevel[service]
#		
		#print "getPinList():", self.getPinList()
		#pinList = self.getPinList()[:levelNeeded + 1]
		#print "pinList:", pinList
#		
#		print "pin entered for service", service, "and pin was", pin
		#if pin is not None and int(pin) in pinList:
		if result[0] is not None and result[0]:
			print "pin ok, playing service"
			self.tries = 3
			self.callback(ref = ServiceReference(service).ref)
		else:
			self.tries = result[1]
			if result[0] is not None:
				Notifications.AddNotification(MessageBox,  _("The pin code you entered is wrong."), MessageBox.TYPE_ERROR)
			print "wrong pin entered"
			
	def saveWhitelist(self):
		file = open(resolveFilename(SCOPE_CONFIG, "whitelist"), 'w')
		for x in self.whitelist:
			file.write(x + "\n")
		file.close
	
	def openWhitelist(self):
		self.whitelist = []
		try:
			file = open(resolveFilename(SCOPE_CONFIG, "whitelist"), 'r')
			lines = file.readlines()
			for x in lines:
				self.whitelist.append(x.strip())
			file.close
		except:
			pass
		
	def saveBlacklist(self):
		file = open(resolveFilename(SCOPE_CONFIG, "blacklist"), 'w')
		for x in self.blacklist:
			file.write(x + "\n")
		file.close

	def openBlacklist(self):
		self.blacklist = []
		try:
			file = open(resolveFilename(SCOPE_CONFIG, "blacklist"), 'r')
			lines = file.readlines()
			for x in lines:
				self.blacklist.append(x.strip())
			file.close
		except:
			pass
		
	def save(self):
		self.saveBlacklist()
		self.saveWhitelist()
		
	def open(self):
		self.openBlacklist()
		self.openWhitelist()

parentalControl = ParentalControl()