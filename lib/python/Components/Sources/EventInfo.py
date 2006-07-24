from Components.PerServiceDisplay import PerServiceBase
from Tools.Event import Event
from enigma import iPlayableService
from Source import Source

class EventInfo(PerServiceBase, Source, object):
	NOW = 0
	NEXT = 1
	
	def __init__(self, navcore, now_or_next):
		Source.__init__(self)
		PerServiceBase.__init__(self, navcore, 
			{ 
				iPlayableService.evStart: self.changed,
				iPlayableService.evUpdatedEventInfo: self.changed,
				iPlayableService.evEnd: self.changed
			})
		
		self.now_or_next = now_or_next
		
	def getEvent(self):
		service = self.navcore.getCurrentService()
		info = service and service.info()
		return info and info.getEvent(self.now_or_next)

	event = property(getEvent)
