from PerServiceDisplay import *

#from enigma import iPlayableService, iServiceInformationPtr
from enigma import *

class ServiceName(PerServiceDisplay):
	def __init__(self, navcore):
		PerServiceDisplay.__init__(self, navcore,
			{
				iPlayableService.evStart: self.newService,
				iPlayableService.evEnd: self.stopEvent
			})
		self.newService()

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

