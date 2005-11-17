from PerServiceDisplay import *
from time import strftime
from time import localtime

from enigma import iServiceInformationPtr, eServiceEventPtr

class EventInfo(PerServiceDisplay):
	Now = 0
	Next = 1
	Now_Duration = 2
	Next_Duration = 3
	Now_StartTime = 4
	Next_StartTime = 5
	
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
				ev = info.getEvent(self.now_or_next & 1)
				if ev is not None:
					if (self.Now_Duration <= self.now_or_next <= self.Next_Duration):
						self.setText("%d min" % (ev.getDuration() / 60))
					if (self.Now_StartTime <= self.now_or_next <= self.Next_StartTime):
						self.setText(strftime("%H:%M", localtime(ev.getBeginTime())))
					if (self.Now <= self.now_or_next <= self.Next):
						self.setText(ev.getEventName())

	def stopEvent(self):
		self.setText(
			(_("waiting for event data..."), "", "--:--",  "--:--", "--:--", "--:--")[self.now_or_next]);

