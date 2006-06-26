from Components.PerServiceDisplay import PerServiceBase
from enigma import iPlayableService
from Source import Source

class CurrentService(PerServiceBase, Source):
	def __init__(self, navcore):
		Source.__init__(self)
		PerServiceBase.__init__(self, navcore, 
			{ 
				iPlayableService.evStart: self.changed,
				iPlayableService.evEnd: self.changed,
				# FIXME: we should check 'interesting_events'
				# which is not always provided.
				iPlayableService.evUpdatedInfo: self.changed,
				iPlayableService.evUpdatedEventInfo: self.changed
			})
		self.navcore = navcore

	def getCurrentService(self):
		return self.navcore.getCurrentService()

	service = property(getCurrentService)
