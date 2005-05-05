from PerServiceDisplay import *
from enigma import pNavigation

class ServiceName(PerServiceDisplay):
	def __init__(self, navcore):
		PerServiceDisplay.__init__(self, navcore,
			{
				pNavigation.evNewService: self.newService,
				pNavigation.evStopService: self.stopEvent
			})

	def newService(self):
		info = iServiceInformationPtr()
		service = self.navcore.getCurrentService(service)
		
		if service != None:
			if not service.info(info):
				self.setText("no name known, but it should be here :)")
	
	def stopEvent(self):
			self.setText("");

