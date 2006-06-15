from Components.PerServiceDisplay import PerServiceBase
from Tools.Event import Event
from enigma import iPlayableService
from Source import Source

class EventInfo(PerServiceBase, Source):
	NOW = 0
	NEXT = 1
	
	def __init__(self, navcore, now_or_next):
		self.changed = Event()
		PerServiceBase.__init__(self, navcore, 
			{ 
				iPlayableService.evUpdatedEventInfo: self.ourEvent, 
				iPlayableService.evEnd: self.stopEvent 
			})
		
		self.event = None
		self.now_or_next = now_or_next
		
	def ourEvent(self):
		service = self.navcore.getCurrentService()
		info = service and service.info()
		self.event = info and info.getEvent(self.now_or_next)
		self.changed()

	def stopEvent(self):
		self.event = None
		self.changed()
