from PerServiceDisplay import *

from enigma import iServiceInformationPtr, eServiceEventPtr

class EventInfo(PerServiceDisplay):
	Now = 0
	Next = 1
	Now_Duration = 2
	Next_Duration = 3
	
	def __init__(self, navcore, now_or_next):
		# listen to evUpdatedEventInfo and evStopService
		# note that evStopService will be called once to establish a known state
		self.now_or_next = now_or_next
		PerServiceDisplay.__init__(self, navcore, 
			{ 
				pNavigation.evUpdatedEventInfo: self.ourEvent, 
				pNavigation.evStopService: self.stopEvent 
			})

	def ourEvent(self):
		info = iServiceInformationPtr()
		service = self.navcore.getCurrentService()
		
		if service != None:
			info = service.info()
			if info is not None: 
				ev = eServiceEventPtr()
				if info.getEvent(ev, self.now_or_next & 1) == 0:
					if self.now_or_next & 2:
						self.setText("%d min" % (ev.m_duration / 60))
					else:
						self.setText(ev.m_event_name)
		print "new event info in EventInfo! yeah!"

	def stopEvent(self):
		self.setText(
			("waiting for event data...", "", "--:--",  "--:--")[self.now_or_next]);

