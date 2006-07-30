from Components.PerServiceDisplay import PerServiceBase
from enigma import iPlayableService
from Source import Source

from time import time

class CurrentService(PerServiceBase, Source):
	def __init__(self, navcore):
		Source.__init__(self)
		PerServiceBase.__init__(self, navcore, 
			{ 
				iPlayableService.evStart: self.serviceEvent,
				iPlayableService.evEnd: self.serviceEvent,
				# FIXME: we should check 'interesting_events'
				# which is not always provided.
				iPlayableService.evUpdatedInfo: self.serviceEvent,
				iPlayableService.evUpdatedEventInfo: self.serviceEvent,
				iPlayableService.evCuesheetChanged: self.serviceEvent
			}, with_event=True)
		self.navcore = navcore

	def serviceEvent(self, event):
		self.changed((self.CHANGED_SPECIFIC, event))

	def getCurrentService(self):
		if self.cache is None:
			self.cache = self.navcore.getCurrentService()
		return self.cache

	service = property(getCurrentService)
