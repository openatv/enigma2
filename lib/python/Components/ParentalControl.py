from Components.config import config, ConfigSubsection, ConfigSelection, ConfigPIN, ConfigText, ConfigYesNo, ConfigSubList, ConfigInteger
from Components.ServiceList import refreshServiceList
#from Screens.ChannelSelection import service_types_tv
from Screens.InputBox import PinInput
from Screens.MessageBox import MessageBox
from Tools.BoundFunction import boundFunction
from ServiceReference import ServiceReference
from Tools import Notifications
from Tools.Directories import resolveFilename, SCOPE_CONFIG
from Tools.Notifications import AddPopup
from enigma import eTimer, eServiceCenter, iServiceInformation, eServiceReference, eDVBDB
import time

TYPE_SERVICE = "SERVICE"
TYPE_BOUQUETSERVICE = "BOUQUETSERVICE"
TYPE_BOUQUET = "BOUQUET"
LIST_BLACKLIST = "blacklist"

def InitParentalControl():
	config.ParentalControl = ConfigSubsection()
	config.ParentalControl.storeservicepin = ConfigSelection(default = "never", choices = [("never", _("never")), ("5", _("5 minutes")), ("30", _("30 minutes")), ("60", _("60 minutes")), ("standby", _("until standby/restart"))])
	config.ParentalControl.configured = ConfigYesNo(default = False)
	config.ParentalControl.setuppinactive = ConfigYesNo(default = False)
	config.ParentalControl.retries = ConfigSubsection()
	config.ParentalControl.retries.servicepin = ConfigSubsection()
	config.ParentalControl.retries.servicepin.tries = ConfigInteger(default = 3)
	config.ParentalControl.retries.servicepin.time = ConfigInteger(default = 3)
	config.ParentalControl.servicepin = ConfigSubList()
	config.ParentalControl.servicepin.append(ConfigPIN(default = 0))
	config.ParentalControl.age = ConfigSelection(default = "18", choices = [("0", _("No age block"))] + list((str(x), "%d+" % x) for x in range(3,19)))
	config.ParentalControl.hideBlacklist = ConfigYesNo(default = False)
	config.ParentalControl.config_sections = ConfigSubsection()
	config.ParentalControl.config_sections.main_menu = ConfigYesNo(default = False)
	config.ParentalControl.config_sections.configuration = ConfigYesNo(default = False)
	config.ParentalControl.config_sections.timer_menu = ConfigYesNo(default = False)
	config.ParentalControl.config_sections.plugin_browser = ConfigYesNo(default = False)
	config.ParentalControl.config_sections.standby_menu = ConfigYesNo(default = False)
	config.ParentalControl.config_sections.movie_list = ConfigYesNo(default = False)
	config.ParentalControl.config_sections.context_menus = ConfigYesNo(default = False)
	config.ParentalControl.config_sections.infopanel = ConfigYesNo(default = False)
	config.ParentalControl.config_sections.quickmenu = ConfigYesNo(default = False)

	#Added for backwards compatibility with some 3rd party plugins that depend on this config
	config.ParentalControl.servicepinactive = config.ParentalControl.configured
	config.ParentalControl.setuppin = config.ParentalControl.servicepin[0]
	config.ParentalControl.retries.setuppin = config.ParentalControl.retries.servicepin
	config.ParentalControl.type = ConfigSelection(default = "blacklist", choices = [(LIST_BLACKLIST, _("blacklist"))])

	global parentalControl
	parentalControl = ParentalControl()

class ParentalControl:
	def __init__(self):
		#Do not call open on init, because bouquets are not ready at that moment
		self.filesOpened = False
		self.PinDlg = None
		#This is the timer that is used to see, if the time for caching the pin is over
		#Of course we could also work without a timer and compare the times every
		#time we call isServicePlayable. But this might probably slow down zapping,
		#That's why I decided to use a timer
		self.sessionPinTimer = eTimer()
		self.sessionPinTimer.callback.append(self.resetSessionPin)
		self.getConfigValues()

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

	def isServicePlayable(self, ref, callback, session=None):
		self.session = session
		if not config.ParentalControl.servicepinactive.value:
			return True
		#Check if configuration has already been read or if the significant values have changed.
		#If true: read the configuration
		if self.storeServicePin != config.ParentalControl.storeservicepin.value:
			self.getConfigValues()
		service = ref.toCompareString()
		info = eServiceCenter.getInstance().info(ref)
		age = 0
		if service.startswith("1:") and service.rsplit(":", 1)[1].startswith("/"):
			refstr = info and info.getInfoString(ref, iServiceInformation.sServiceref)
			service = refstr and eServiceReference(refstr).toCompareString()
		elif int(config.ParentalControl.age.value):
			event = info and info.getEvent(ref)
			rating = event and event.getParentalData()
			age = rating and rating.getRating()
			age = age and age <= 15 and age + 3 or 0
		if (age and age >= int(config.ParentalControl.age.value)) or service and self.blacklist.has_key(service):
			#Check if the session pin is cached
			if self.sessionPinCached:
				return True
			self.callback = callback
			title = 'FROM BOUQUET "userbouquet.' in service and _("this bouquet is protected by a parental control pin") or _("this service is protected by a parental control pin")
			if session:
				Notifications.RemovePopup("Parental control")
				if self.PinDlg:
					self.PinDlg.close()
				self.PinDlg = session.openWithCallback(boundFunction(self.servicePinEntered, ref), PinInput, triesEntry=config.ParentalControl.retries.servicepin, pinList=self.getPinList(), service=ServiceReference(ref).getServiceName(), title=title, windowTitle=_("Parental control"), simple=False)
			else:
				Notifications.AddNotificationParentalControl(boundFunction(self.servicePinEntered, ref), PinInput, triesEntry=config.ParentalControl.retries.servicepin, pinList=self.getPinList(), service=ServiceReference(ref).getServiceName(), title=title, windowTitle=_("Parental control"))
			return False
		else:
			return True

	def protectService(self, service):
		if not self.blacklist.has_key(service):
			self.serviceMethodWrapper(service, self.addServiceToList, self.blacklist)
			if config.ParentalControl.hideBlacklist.value and not self.sessionPinCached:
				eDVBDB.getInstance().addFlag(eServiceReference(service), 2)

	def unProtectService(self, service):
		if self.blacklist.has_key(service):
			self.serviceMethodWrapper(service, self.removeServiceFromList, self.blacklist)

	def getProtectionLevel(self, service):
		return not self.blacklist.has_key(service) and -1 or 0

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
			iSeconds = int(iMinutes*60)
			self.pinIntervalSeconds = iSeconds

	def standbyCounterCallback(self, configElement):
		self.resetSessionPin()

	def resetSessionPin(self):
		#Reset the session pin, stop the timer
		self.sessionPinCached = False
		self.hideBlacklist()

	def getCurrentTimeStamp(self):
		return time.time()

	def getPinList(self):
		return [ x.value for x in config.ParentalControl.servicepin ]

	def setSessionPinCached(self):
		if self.checkSessionPin == True:
			self.sessionPinCached = True
		if self.checkPinInterval == True:
			self.sessionPinCached = True
			self.sessionPinTimer.startLongTimer(self.pinIntervalSeconds)

	def servicePinEntered(self, service, result=None):
		if result is not None and result:
			self.setSessionPinCached()
			self.hideBlacklist()
			self.callback(ref = service)
		else:
			#This is the new function of caching cancelling of service pin
			if result is not None:
				messageText = _("The pin code you entered is wrong.")
				if self.session:
					self.session.open(MessageBox, messageText, MessageBox.TYPE_INFO, timeout=3)
				else:
					AddPopup(messageText, MessageBox.TYPE_ERROR, timeout = 3)

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
			file =  open(resolveFilename(SCOPE_CONFIG, sWhichList ), 'r')
			for x in file:
				sPlain = x.strip()
				self.serviceMethodWrapper(sPlain, self.addServiceToList, result)
			file.close()
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

	def readServicesFromBouquet(self,sBouquetSelection,formatstring):
		#This method gives back a list of services for a given bouquet
		from enigma import eServiceCenter, eServiceReference

		serviceHandler = eServiceCenter.getInstance()
		refstr = sBouquetSelection
		root = eServiceReference(refstr)
		list = serviceHandler.list(root)
		if list is not None:
			services = list.getContent("CN", True) #(servicecomparestring, name)
			return services

	def save(self):
		self.saveListToFile(LIST_BLACKLIST, self.blacklist)

	def open(self):
		self.blacklist = self.openListFromFile(LIST_BLACKLIST)
		self.hideBlacklist()
		if not self.filesOpened:
			# Reset PIN cache on standby: Use StandbyCounter- Config- Callback
			config.misc.standbyCounter.addNotifier(self.standbyCounterCallback, initial_call = False)
			self.filesOpened = True

	def __getattr__(self, name):
		# This method is called if we lack a property. I'm lazy, so
		# I load the files when someone 'hits' this code
		if name in ('blacklist', 'whitelist'):
			if not self.filesOpened:
				self.open()
				return getattr(self, name)
		raise AttributeError, name

	def hideBlacklist(self):
		if self.blacklist:
			if config.ParentalControl.servicepinactive.value and config.ParentalControl.storeservicepin.value != "never" and config.ParentalControl.hideBlacklist.value and not self.sessionPinCached:
				for ref in self.blacklist:
					if TYPE_BOUQUET not in ref:
						eDVBDB.getInstance().addFlag(eServiceReference(ref), 2)
			else:
				for ref in self.blacklist:
					if TYPE_BOUQUET not in ref:
						eDVBDB.getInstance().removeFlag(eServiceReference(ref), 2)
			refreshServiceList()
