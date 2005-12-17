from Screen import Screen
from Components.TimerList import TimerList, TimerEntryComponent
from Components.ActionMap import ActionMap
from Components.TimeInput import TimeInput
from Components.Label import Label
from Components.Button import Button
from Components.TextInput import TextInput
from TimerEntry import TimerEntry
from RecordTimer import RecordTimerEntry, parseEvent
from time import *
from ServiceReference import ServiceReference
from Components.config import *

class TimerEditList(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		list = [ ]
		self.list = list
		self.fillTimerList()

		self["timerlist"] = TimerList(list)
		
		self["key_red"] = Button(_("Delete"))
		self["key_green"] = Button(_("Add"))
		self["key_yellow"] = Button("")
		self["key_blue"] = Button("")

		self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions"], 
			{
				"ok": self.openEdit,
				"cancel": self.leave,
				"red": self.removeTimer,
				"green": self.addCurrentTimer
			})

	def fillTimerList(self):
		del self.list[:]
		
		for timer in self.session.nav.RecordTimer.timer_list:
			self.list.append(TimerEntryComponent(timer, 0))
		
		for timer in self.session.nav.RecordTimer.processed_timers:
			self.list.append(TimerEntryComponent(timer, 1))

	def openEdit(self):
		self.session.openWithCallback(self.finishedEdit, TimerEntry, self["timerlist"].getCurrent()[0])
		#self.session.open(TimerEdit, self["timerlist"].getCurrent()[0])
		
	def removeTimer(self):
		# FIXME doesn't work...
		self.session.nav.RecordTimer.removeEntry(self["timerlist"].getCurrent()[0])
		self.fillTimerList()
		self["timerlist"].invalidate()
	
	def addCurrentTimer(self):
		event = None
		service = self.session.nav.getCurrentService()
		if service is not None:
			info = service.info()
			if info is not None:
				event = info.getEvent(0)

		# FIXME only works if already playing a service
		serviceref = ServiceReference(self.session.nav.getCurrentlyPlayingServiceReference())
		
		if event is None:	
			data = (int(time()), int(time() + 60), "unknown event", "", None)
		else:
			data = parseEvent(event)

		self.addTimer(RecordTimerEntry(serviceref, *data))
		
	def addTimer(self, timer):
		self.session.openWithCallback(self.finishedAdd, TimerEntry, timer)
		
	def finishedEdit(self, answer):
		if (answer[0]):
			print "Edited timer"
			self.session.nav.RecordTimer.timeChanged(answer[1])
			self.fillTimerList()
		else:
			print "Timeredit aborted"
			
	def finishedAdd(self, answer):
		if (answer[0]):
			self.session.nav.RecordTimer.record(answer[1])
			self.fillTimerList()
		else:
			print "Timeredit aborted"		

	def leave(self):
		self.session.nav.RecordTimer.saveTimer()
		self.close()
