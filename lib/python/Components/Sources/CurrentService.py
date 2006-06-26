from Components.PerServiceDisplay import PerServiceBase
from enigma import iPlayableService
from Source import Source

class CurrentService(PerServiceBase, Source):
	def __init__(self, navcore):
		Source.__init__(self)
		PerServiceBase.__init__(self, navcore, 
			{ 
				iPlayableService.evStart: self.changed,
				iPlayableService.evEnd: self.changed 
			})
		self.navcore = navcore

	def getCurrentService(self):
		service = self.navcore.getCurrentService()
		return service

	def stopEvent(self):
		self.changed()

	service = property(getCurrentService)
