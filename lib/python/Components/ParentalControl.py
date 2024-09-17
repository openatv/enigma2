from time import time

from enigma import eDVBDB, eServiceCenter, eServiceReference, eTimer, iServiceInformation

from ServiceReference import ServiceReference
from Components.config import ConfigInteger, ConfigPIN, ConfigSelection, ConfigSubList, ConfigSubsection, ConfigYesNo, config
from Components.ServiceList import refreshServiceList
from Screens.InputBox import PinInput
from Screens.MessageBox import MessageBox
from Tools.BoundFunction import boundFunction
from Tools.Directories import SCOPE_CONFIG, fileReadLines, fileWriteLines, resolveFilename
from Tools.Notifications import AddNotificationParentalControl, AddPopup, RemovePopup

MODULE_NAME = __name__.split(".")[-1]

TYPE_SERVICE = "SERVICE"
TYPE_BOUQUETSERVICE = "BOUQUETSERVICE"
TYPE_BOUQUET = "BOUQUET"
LIST_BLACKLIST = "blacklist"

config.ParentalControl = ConfigSubsection()
config.ParentalControl.storeservicepin = ConfigSelection(default="never", choices=[
	("never", _("Never")),
	("5", _("%d Minutes") % 5),
	("30", _("%d Minutes") % 30),
	("60", _("%d Minutes") % 60),
	("standby", _("Until standby/restart"))
])
config.ParentalControl.configured = ConfigYesNo(default=False)
config.ParentalControl.setuppinactive = ConfigYesNo(default=False)
config.ParentalControl.retries = ConfigSubsection()
config.ParentalControl.retries.servicepin = ConfigSubsection()
config.ParentalControl.retries.servicepin.tries = ConfigInteger(default=3)
config.ParentalControl.retries.servicepin.time = ConfigInteger(default=3)
config.ParentalControl.servicepin = ConfigSubList()
config.ParentalControl.servicepin.append(ConfigPIN(default=0))
config.ParentalControl.age = ConfigSelection(default=18, choices=[(0, _("No age block"))] + [(x, "%d+" % x) for x in range(3, 19)])
config.ParentalControl.hideBlacklist = ConfigYesNo(default=False)
config.ParentalControl.config_sections = ConfigSubsection()
config.ParentalControl.config_sections.main_menu = ConfigYesNo(default=False)
config.ParentalControl.config_sections.configuration = ConfigYesNo(default=False)
config.ParentalControl.config_sections.timer_menu = ConfigYesNo(default=False)
config.ParentalControl.config_sections.plugin_browser = ConfigYesNo(default=False)
config.ParentalControl.config_sections.standby_menu = ConfigYesNo(default=False)
config.ParentalControl.config_sections.movie_list = ConfigYesNo(default=False)
config.ParentalControl.config_sections.context_menus = ConfigYesNo(default=False)
# config.ParentalControl.config_sections.infopanel = ConfigYesNo(default=False)
config.ParentalControl.config_sections.quickmenu = ConfigYesNo(default=False)
config.ParentalControl.config_sections.software_update = ConfigYesNo(default=False)
# Added for backwards compatibility with some 3rd party plugins that depend on this configuration.
config.ParentalControl.servicepinactive = config.ParentalControl.configured
config.ParentalControl.setuppin = config.ParentalControl.servicepin[0]
config.ParentalControl.retries.setuppin = config.ParentalControl.retries.servicepin
config.ParentalControl.type = ConfigSelection(default="blacklist", choices=[(LIST_BLACKLIST, _("Blacklist"))])


class ParentalControl:
	def __init__(self):
		# Do not call open on __init__, because bouquets are not ready at that moment!
		self.filesOpened = False
		self.PinDlg = None
		# This is the timer that is used to see, if the time for caching the PIN is over. Of course we could
		# also work without a timer and compare the times every time we call isServicePlayable. But this might
		# probably slow down zapping, that's why I decided to use a timer.
		self.sessionPinTimer = eTimer()
		self.sessionPinTimer.callback.append(self.resetSessionPin)
		self.getConfigValues()

	def __getattr__(self, name):  # This method is called if we lack a property. I'm lazy, so I load the files when someone "hits" this code.
		if name in ("blacklist", "whitelist"):
			if not self.filesOpened:
				self.open()
				return getattr(self, name)
		raise AttributeError(name)

	# This method is used to call all functions that need a service as Parameter.
	# It takes either a Service-Reference or a Bouquet-Reference and passes either
	# the service or all services contained in the bouquet to the method given. That
	# way all other functions do not need to distinguish between service and bouquet.
	#
	def serviceMethodWrapper(self, service, method, *args):
		if "FROM BOUQUET" in service:
			method(service, TYPE_BOUQUET, *args)
			servicelist = self.readServicesFromBouquet(service, "C")
			for ref in servicelist:
				sRef = str(ref[0])
				method(sRef, TYPE_BOUQUETSERVICE, *args)
		else:
			ref = ServiceReference(service)
			sRef = str(ref)
			method(sRef, TYPE_SERVICE, *args)

	def isServicePlayable(self, ref, callback, session=None):
		self.session = session
		if not config.ParentalControl.servicepinactive.value:
			return True
		# Check if configuration has already been read or if the significant values have changed.
		# If true:, read the configuration.
		if self.storeServicePin != config.ParentalControl.storeservicepin.value:
			self.getConfigValues()
		service = ref.toCompareString()
		info = eServiceCenter.getInstance().info(ref)
		age = 0
		if service.startswith("1:") and service.rsplit(":", 1)[1].startswith("/"):
			refstr = info and info.getInfoString(ref, iServiceInformation.sServiceref)
			service = refstr and eServiceReference(refstr).toCompareString()
		elif config.ParentalControl.age.value:
			event = info and info.getEvent(ref)
			rating = event and event.getParentalData()
			age = rating and rating.getRating()
			age = age and age <= 15 and age + 3 or 0
		if (age and age >= config.ParentalControl.age.value) or service and service in self.blacklist:
			if self.sessionPinCached:  # Check if the session PIN is cached.
				return True
			self.callback = callback
			title = "FROM BOUQUET \"userbouquet." in service and _("This bouquet is protected by a parental control PIN!") or _("This service is protected by a parental control PIN!")
			if session:
				RemovePopup("Parental control")
				if self.PinDlg:
					self.PinDlg.close()
				self.PinDlg = session.openWithCallback(boundFunction(self.servicePinEntered, ref), PinInput, triesEntry=config.ParentalControl.retries.servicepin, pinList=self.getPinList(), service=ServiceReference(ref).getServiceName(), title=title, windowTitle=_("Parental Control"), simple=False)
			else:
				AddNotificationParentalControl(boundFunction(self.servicePinEntered, ref), PinInput, triesEntry=config.ParentalControl.retries.servicepin, pinList=self.getPinList(), service=ServiceReference(ref).getServiceName(), title=title, windowTitle=_("Parental Control"))
			return False
		else:
			return True

	def protectService(self, service):
		if service not in self.blacklist:
			self.serviceMethodWrapper(service, self.addServiceToList, self.blacklist)
			if config.ParentalControl.hideBlacklist.value and not self.sessionPinCached:
				eDVBDB.getInstance().addFlag(eServiceReference(service), 2)

	def unProtectService(self, service):
		if service in self.blacklist:
			self.serviceMethodWrapper(service, self.removeServiceFromList, self.blacklist)

	def getProtectionLevel(self, service):
		return service not in self.blacklist and -1 or 0

	def getConfigValues(self):  # Read all values from the configuration.
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
			iSeconds = int(iMinutes * 60)
			self.pinIntervalSeconds = iSeconds

	def standbyCounterCallback(self, configElement):
		self.resetSessionPin()

	def resetSessionPin(self):  # Reset the session PIN, stop the timer.
		self.sessionPinCached = False
		self.hideBlacklist()

	def getCurrentTimeStamp(self):
		return time()

	def getPinList(self):
		return [x.value for x in config.ParentalControl.servicepin]

	def setSessionPinCached(self):
		if self.checkSessionPin is True:
			self.sessionPinCached = True
		if self.checkPinInterval is True:
			self.sessionPinCached = True
			self.sessionPinTimer.startLongTimer(self.pinIntervalSeconds)

	def servicePinEntered(self, service, result=None):
		if result is not None and result:
			self.setSessionPinCached()
			self.hideBlacklist()
			self.callback(ref=service)
		else:  # This is the new function of caching canceling of service PIN.
			if result is not None:
				messageText = _("The PIN code entered is incorrect!")
				if self.session:
					self.session.open(MessageBox, messageText, MessageBox.TYPE_INFO, timeout=3)
				else:
					AddPopup(messageText, MessageBox.TYPE_ERROR, timeout=3)

	# Replaces saveWhiteList and saveBlackList. (I don't like
	# to have two functions with identical code.)
	#
	def saveListToFile(self, sWhichList, vList):
		lines = []
		for sService, sType in vList.items():
			# Only Services that are selected directly and bouquets are saved. Services that are added by a
			# bouquet are not saved. This is the reason for the change in self.whitelist and self.blacklist.
			if TYPE_SERVICE in sType or TYPE_BOUQUET in sType:
				lines.append(str(sService))
		if lines:
			lines.append("")
		fileWriteLines(resolveFilename(SCOPE_CONFIG, sWhichList), "\n".join(lines), source=MODULE_NAME)

	# Replaces openWhiteList and openBlackList. (I don't like
	# to have two functions with identical code.)
	#
	def openListFromFile(self, sWhichList):
		result = {}
		lines = fileReadLines(resolveFilename(SCOPE_CONFIG, sWhichList), default=[], source=MODULE_NAME)
		for line in lines:
			self.serviceMethodWrapper(line.strip(), self.addServiceToList, result)
		return result

	# Replaces addWhitelistService and addBlacklistService. The lists are not only lists of service references
	# any more, they are named lists with the service as key and an array of types as value:
	#
	def addServiceToList(self, service, type, vList):
		if service in vList:
			if type not in vList[service]:
				vList[service].append(type)
		else:
			vList[service] = [type]

	def removeServiceFromList(self, service, type, vList):  # Replaces deleteWhitelistService and deleteBlacklistService.
		if service in vList:
			if type in vList[service]:
				vList[service].remove(type)
			if not vList[service]:
				del vList[service]

	def readServicesFromBouquet(self, sBouquetSelection, formatstring):  # This method gives back a list of services for a given bouquet.
		serviceHandler = eServiceCenter.getInstance()
		root = eServiceReference(sBouquetSelection)
		serviceList = serviceHandler.list(root)
		if serviceList is not None:
			return serviceList.getContent("CN", True)  # (ServiceCompareString, Name)

	def save(self):
		if self.filesOpened:
			self.saveListToFile(LIST_BLACKLIST, self.blacklist)

	def open(self):
		self.blacklist = self.openListFromFile(LIST_BLACKLIST)
		self.hideBlacklist()
		if not self.filesOpened:  # Reset PIN cache on standby. Use StandbyCounter-Config-Callback.
			config.misc.standbyCounter.addNotifier(self.standbyCounterCallback, initial_call=False)
			self.filesOpened = True
			refreshServiceList()

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


parentalControl = ParentalControl()
