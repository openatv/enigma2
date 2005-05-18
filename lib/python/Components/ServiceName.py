from PerServiceDisplay import *

from enigma import pNavigation, iServiceInformationPtr

class ServiceName(PerServiceDisplay):
	def __init__(self, navcore):
		PerServiceDisplay.__init__(self, navcore,
			{
				pNavigation.evNewService: self.newService,
				pNavigation.evStopService: self.stopEvent
			})

	def newService(self):
		info = iServiceInformationPtr()
		service = self.navcore.getCurrentService()
		
		if service != None:
			if not service.info(info):
				self.setText(info.getName())
	
	def stopEvent(self):
			self.setText("");

