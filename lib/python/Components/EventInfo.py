from PerServiceDisplay import *
from time import strftime
from time import localtime, time

from enigma import iServiceInformationPtr, eServiceEventPtr

class EventInfo(PerServiceDisplay):
	Now = 0
	Next = 1
	Now_Duration = 2
	Next_Duration = 3
	Now_StartTime = 4
	Next_StartTime = 5
	Now_Remaining = 6
	
	def __init__(self, navcore, now_or_next):
		# listen to evUpdatedEventInfo and evEnd
		# note that evEnd will be called once to establish a known state
		self.now_or_next = now_or_next
		PerServiceDisplay.__init__(self, navcore, 
			{ 
				iPlayableService.evUpdatedEventInfo: self.ourEvent, 
				iPlayableService.evEnd: self.stopEvent 
			})
		
		if now_or_next in [self.Now_Remaining]:
			self.enablePolling()

	def ourEvent(self):
		info = iServiceInformationPtr()
		service = self.navcore.getCurrentService()
		
		if service != None:
			info = service.info()
			if info is not None: 
				ev = info.getEvent(self.now_or_next & 1)
				if ev is not None:
					self.update(ev)

	def update(self, ev):
		if self.now_or_next == self.Now_Remaining and ev.getBeginTime() <= time() <= (ev.getBeginTime() + ev.getDuration()):
			self.setText("+%d min" % ((ev.getBeginTime() + ev.getDuration() - time()) / 60))
		elif self.now_or_next in [self.Now_Duration, self.Next_Duration, self.Now_Remaining]:
			self.setText("%d min" % (ev.getDuration() / 60))
		elif self.now_or_next in [self.Now_StartTime, self.Next_StartTime]:
			self.setText(strftime("%H:%M", localtime(ev.getBeginTime())))
		elif self.now_or_next in [self.Now, self.Next]:
			self.setText(ev.getEventName())		

	def stopEvent(self):
		self.setText(
			("", "", "",  "", "--:--", "--:--", "")[self.now_or_next]);

	def poll(self):
		self.ourEvent()

class EventInfoProgress(PerServiceDisplayProgress, EventInfo):
	def __init__(self, navcore, now_or_next):
		self.now_or_next = now_or_next
		PerServiceDisplayProgress.__init__(self, navcore, 
			{ 
				iPlayableService.evUpdatedEventInfo: self.ourEvent, 
				iPlayableService.evEnd: self.stopEvent 
			})

	def update(self, ev):
		self.g.setRange(0, ev.getDuration())
		progress = int(time() - ev.getBeginTime())

		self.setValue(progress)
		
	def stopEvent(self):
		self.setValue(0)
