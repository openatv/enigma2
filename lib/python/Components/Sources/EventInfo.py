from Components.PerServiceDisplay import PerServiceBase
from Tools.Event import Event
from enigma import iPlayableService
from Source import Source

from time import time

class EventInfo(PerServiceBase, Source, object):
	NOW = 0
	NEXT = 1
	
	def __init__(self, navcore, now_or_next):
		Source.__init__(self)
		PerServiceBase.__init__(self, navcore, 
			{ 
				iPlayableService.evStart: self.gotEvent,
				iPlayableService.evUpdatedEventInfo: self.gotEvent,
				iPlayableService.evEnd: self.gotEvent
			}, with_event=True)
		
		self.now_or_next = now_or_next
		
	def getEvent(self):
		if self.cache is None:
			service = self.navcore.getCurrentService()
			info = service and service.info()
			self.cache = (True, info and info.getEvent(self.now_or_next)) # we always store a tuple for negative caching
		
		return self.cache[1]

	event = property(getEvent)

	def gotEvent(self, what):
		if what in [iPlayableService.evStart, iPlayableService.evEnd]:
			self.changed((self.CHANGED_CLEAR,))
		else:
			self.changed((self.CHANGED_ALL,))
