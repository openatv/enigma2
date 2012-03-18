from Components.config import config, ConfigSubsection, ConfigSelection, ConfigPIN, ConfigText, ConfigYesNo, ConfigSubList, ConfigInteger
#from Screens.ChannelSelection import service_types_tv
from Screens.InputBox import PinInput
from Screens.MessageBox import MessageBox
from Tools.BoundFunction import boundFunction
from ServiceReference import ServiceReference
from Tools import Notifications
from Tools.Directories import resolveFilename, SCOPE_CONFIG
from Tools.Notifications import AddPopup
from enigma import eTimer
import time

TYPE_SERVICE = "SERVICE"
TYPE_BOUQUETSERVICE = "BOUQUETSERVICE"
TYPE_BOUQUET = "BOUQUET"
LIST_BLACKLIST = "blacklist"
LIST_WHITELIST = "whitelist"

IMG_WHITESERVICE = LIST_WHITELIST + "-" + TYPE_SERVICE
IMG_WHITEBOUQUET = LIST_WHITELIST + "-" + TYPE_BOUQUET
IMG_BLACKSERVICE = LIST_BLACKLIST + "-" + TYPE_SERVICE
IMG_BLACKBOUQUET = LIST_BLACKLIST + "-" + TYPE_BOUQUET

def InitParentalControl():
	global parentalControl
	parentalControl = ParentalControl()
	config.ParentalControl = ConfigSubsection()
	config.ParentalControl.configured = ConfigYesNo(default = False)
	config.ParentalControl.mode = ConfigSelection(default = "simple", choices = [("simple", _("simple")), ("complex", _("complex"))])
	config.ParentalControl.storeservicepin = ConfigSelection(default = "never", choices = [("never", _("never")), ("5", _("%d minutes") % 5), ("30", _("%d minutes") % 30), ("60", _("%d minutes") % 60), ("standby", _("until standby/restart"))])
	config.ParentalControl.servicepinactive = ConfigYesNo(default = False)
	config.ParentalControl.setuppinactive = ConfigYesNo(default = False)
	config.ParentalControl.type = ConfigSelection(default = "blacklist", choices = [(LIST_WHITELIST, _("whitelist")), (LIST_BLACKLIST, _("blacklist"))])
	config.ParentalControl.setuppin = ConfigPIN(default = -1)
	
	config.ParentalControl.retries = ConfigSubsection()
	config.ParentalControl.retries.setuppin = ConfigSubsection()
	config.ParentalControl.retries.setuppin.tries = ConfigInteger(default = 3)
	config.ParentalControl.retries.setuppin.time = ConfigInteger(default = 3)	
	config.ParentalControl.retries.servicepin = ConfigSubsection()
	config.ParentalControl.retries.servicepin.tries = ConfigInteger(default = 3)
	config.ParentalControl.retries.servicepin.time = ConfigInteger(default = 3)

	config.ParentalControl.servicepin = ConfigSubList()

	for i in (0, 1, 2):
		config.ParentalControl.servicepin.append(ConfigPIN(default = -1))
		#config.ParentalControl.servicepin.append(configElement("config.ParentalControl.servicepin.level" + str(i), configSequence, "0000", configSequenceArg().get("PINCODE", (4, ""))))

class ParentalControl:
	def __init__(self):
		#Do not call open on init, because bouquets are not ready at that moment 
		self.filesOpened = False
		self.serviceLevel = {}
		#Instead: Use Flags to see, if we already initialized config and called open
		self.configInitialized = False
		#This is the timer that is used to see, if the time for caching the pin is over
		#Of course we could also work without a timer and compare the times every
		#time we call isServicePlayable. But this might probably slow down zapping, 
		#That's why I decided to use a timer
		self.sessionPinTimer = eTimer()
		self.sessionPinTimer.callback.append(self.resetSessionPin)
	
	def serviceMethodWrapper(self, service, method, *args):
		#This method is used to call all functions that need a service as Parameter: 
		#It takes either a Service- Reference or a Bouquet- Reference and passes 
		#Either the service or all services contained in the bouquet to the method given
		#That way all other functions do not need to distinguish between service and bouquet. 
		if "FROM BOUQUET" in service:
			method( service , TYPE_BOUQUET , *args )
			servicelist = self.readServicesFromBouquet(service,"C")
			for ref in servicelist:
				sRef = str(ref[0])
				method( sRef , TYPE_BOUQUETSERVICE , *args )
		else:
			ref = ServiceReference(service)
			sRef = str(ref)
			method( sRef , TYPE_SERVICE , *args )
	
	def setServiceLevel(self, service, type, level):
		self.serviceLevel[service] = level

	def isServicePlayable(self, ref, callback):
		if not config.ParentalControl.configured.value or not config.ParentalControl.servicepinactive.value:
			return True
		#Check if configuration has already been read or if the significant values have changed.
		#If true: read the configuration 
		if self.configInitialized == False or self.storeServicePin != config.ParentalControl.storeservicepin.value:
			self.getConfigValues()
		service = ref.toCompareString()
		if (config.ParentalControl.type.value == LIST_WHITELIST and not self.whitelist.has_key(service)) or (config.ParentalControl.type.value == LIST_BLACKLIST and self.blacklist.has_key(service)):
			#Check if the session pin is cached
			if self.sessionPinCached == True:
				return True
			self.callback = callback
			#Someone started to implement different levels of protection. Seems they were never completed
			#I did not throw out this code, although it is of no use at the moment
			levelNeeded = 0
			if self.serviceLevel.has_key(service):
				levelNeeded = self.serviceLevel[service]
			pinList = self.getPinList()[:levelNeeded + 1]
			Notifications.AddNotificationWithCallback(boundFunction(self.servicePinEntered, ref), PinInput, triesEntry = config.ParentalControl.retries.servicepin, pinList = pinList, service = ServiceReference(ref).getServiceName(), title = _("this service is protected by a parental control pin"), windowTitle = _("Parental control"))
			return False
		else:
			return True
		
	def protectService(self, service):
		if config.ParentalControl.type.value == LIST_WHITELIST:
			if self.whitelist.has_key(service):
				self.serviceMethodWrapper(service, self.removeServiceFromList, self.whitelist)
				#self.deleteWhitelistService(service)
		else: # blacklist
			if not self.blacklist.has_key(service):
				self.serviceMethodWrapper(service, self.addServiceToList, self.blacklist)
				#self.addBlacklistService(service)
		#print "whitelist:", self.whitelist
		#print "blacklist:", self.blacklist

	def unProtectService(self, service):
		#print "unprotect"
		#print "config.ParentalControl.type.value:", config.ParentalControl.type.value
		if config.ParentalControl.type.value == LIST_WHITELIST:
			if not self.whitelist.has_key(service):
				self.serviceMethodWrapper(service, self.addServiceToList, self.whitelist)
				#self.addWhitelistService(service)
		else: # blacklist
			if self.blacklist.has_key(service):
				self.serviceMethodWrapper(service, self.removeServiceFromList, self.blacklist)
				#self.deleteBlacklistService(service)
		#print "whitelist:", self.whitelist
		#print "blacklist:", self.blacklist

	def getProtectionLevel(self, service):
		if (config.ParentalControl.type.value == LIST_WHITELIST and not self.whitelist.has_key(service)) or (config.ParentalControl.type.value == LIST_BLACKLIST and self.blacklist.has_key(service)):
			if self.serviceLevel.has_key(service):
				return self.serviceLevel[service]
			else:
				return 0
		else:
			return -1

	def getProtectionType(self, service):
		#New method used in ParentalControlList: This method does not only return
		#if a service is protected or not, it also returns, why (whitelist or blacklist, service or bouquet)
		sImage = ""
		if (config.ParentalControl.type.value == LIST_WHITELIST):
			if self.whitelist.has_key(service):
				if TYPE_SERVICE in self.whitelist[service]:
					sImage = IMG_WHITESERVICE
				else:
					sImage = IMG_WHITEBOUQUET
		elif (config.ParentalControl.type.value == LIST_BLACKLIST):
			if self.blacklist.has_key(service):
				if TYPE_SERVICE in self.blacklist[service]:
					sImage = IMG_BLACKSERVICE
				else:
					sImage = IMG_BLACKBOUQUET
		bLocked = self.getProtectionLevel(service) != -1
		return (bLocked,sImage)
	
	def getConfigValues(self):	
		#Read all values from configuration 
		self.checkPinInterval = False
		self.checkPinIntervalCancel = False
		self.checkSessionPin = False
		
		self.sessionPinCached = False
		self.pinIntervalSeconds = 0
		self.pinIntervalSecondsCancel = 0

		self.storeServicePin = config.ParentalControl.storeservicepin.value
		
		if self.storeServicePin == "never":
			pass
		elif self.storeServicePin == "standby":
			self.checkSessionPin = True
		else:
			self.checkPinInterval = True
			iMinutes = float(self.storeServicePin)
			iSeconds = iMinutes*60
			self.pinIntervalSeconds = iSeconds
	
		self.configInitialized = True
		# Reset PIN cache on standby: Use StandbyCounter- Config- Callback
		config.misc.standbyCounter.addNotifier(self.standbyCounterCallback, initial_call = False)

	def standbyCounterCallback(self, configElement):
		self.resetSessionPin()
		
	def resetSessionPin(self):
		#Reset the session pin, stop the timer
		self.sessionPinCached = False
		self.sessionPinTimer.stop()

	def getCurrentTimeStamp(self):
		return time.time()

	def getPinList(self):
		return [ x.value for x in config.ParentalControl.servicepin ]
		
	def servicePinEntered(self, service, result):

		if result is not None and result:
			#This is the new function of caching the service pin
			#save last session and time of last entered pin...
			if self.checkSessionPin == True:
				self.sessionPinCached = True
			if self.checkPinInterval == True:
				self.sessionPinCached = True
				self.sessionPinTimer.start(self.pinIntervalSeconds*1000,1)
			self.callback(ref = service)
		else:
			#This is the new function of caching cancelling of service pin
			if result is not None:
				AddPopup(_("The pin code you entered is wrong."), MessageBox.TYPE_ERROR, timeout = 3)
			
	def saveListToFile(self,sWhichList,vList):
		#Replaces saveWhiteList and saveBlackList: 
		#I don't like to have two functions with identical code...
		file = open(resolveFilename(SCOPE_CONFIG, sWhichList), 'w')
		for sService,sType in vList.iteritems():
			#Only Services that are selected directly and Bouqets are saved. 
			#Services that are added by a bouquet are not saved. 
			#This is the reason for the change in self.whitelist and self.blacklist
			if TYPE_SERVICE in sType or TYPE_BOUQUET in sType:
				file.write(str(sService) + "\n")
		file.close()

	def openListFromFile(self,sWhichList):
		#Replaces openWhiteList and openBlackList: 
		#I don't like to have two functions with identical code...
		result = {}
		try:
			for x in open(resolveFilename(SCOPE_CONFIG, sWhichList ), 'r'):
				sPlain = x.strip()
				self.serviceMethodWrapper(sPlain, self.addServiceToList, result)
		except:
			pass
		return result
	
	def addServiceToList(self, service, type, vList):
		#Replaces addWhitelistService and addBlacklistService
		#The lists are not only lists of service references any more. 
		#They are named lists with the service as key and an array of types as value:
		if vList.has_key(service):
			if not type in vList[service]:
				vList[service].append(type)
		else:
			vList[service] = [type]
	
	def removeServiceFromList(self, service, type, vList):
		#Replaces deleteWhitelistService and deleteBlacklistService
		if vList.has_key(service):
			if type in vList[service]:
				vList[service].remove(type)
			if not vList[service]:
				del vList[service]
		if self.serviceLevel.has_key(service):
			self.serviceLevel.remove(service)
		
	def readServicesFromBouquet(self,sBouquetSelection,formatstring):
		#This method gives back a list of services for a given bouquet
		from enigma import eServiceCenter, eServiceReference
		from Screens.ChannelSelection import service_types_tv
		serviceHandler = eServiceCenter.getInstance()
		refstr = sBouquetSelection
		root = eServiceReference(refstr)
		list = serviceHandler.list(root)
		if list is not None:
			services = list.getContent("CN", True) #(servicecomparestring, name)
			return services
		
	def save(self):
		self.saveListToFile(LIST_BLACKLIST, self.blacklist)
		self.saveListToFile(LIST_WHITELIST, self.whitelist)
		
	def open(self):
		self.blacklist = self.openListFromFile(LIST_BLACKLIST)
		self.whitelist = self.openListFromFile(LIST_WHITELIST)
		self.filesOpened = True

	def __getattr__(self, name):
		# This method is called if we lack a property. I'm lazy, so
		# I load the files when someone 'hits' this code
		if name in ('blacklist', 'whitelist'):
			if not self.filesOpened:
				self.open()
				return getattr(self, name)
		raise AttributeError, name
			

