from PerServiceDisplay import *

#from enigma import pNavigation, iServiceInformationPtr
from enigma import *

class ServiceName(PerServiceDisplay):
	def __init__(self, navcore):
		PerServiceDisplay.__init__(self, navcore,
			{
				pNavigation.evNewService: self.newService,
				pNavigation.evStopService: self.stopEvent
			})

	def newService(self):
		service = self.navcore.getCurrentService()
		
		if service is not None:
			info = service.info()
			if info is not None:
				name = info.getName()
				self.setText(name)
				setLCD(name)
	
	def stopEvent(self):
			self.setText("");

