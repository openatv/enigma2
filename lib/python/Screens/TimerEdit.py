from Screen import Screen
from Components.TimerList import TimerList, TimerEntryComponent
from Components.ActionMap import ActionMap
from Components.TimeInput import TimeInput
from Components.Label import Label
from Components.Button import Button
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
		self.session.nav.RecordTimer.on_state_change.append(self.onStateChange)

	def fillTimerList(self):
		del self.list[:]
		
		for timer in self.session.nav.RecordTimer.timer_list:
			self.list.append(TimerEntryComponent(timer, processed=False))
		
		for timer in self.session.nav.RecordTimer.processed_timers:
			self.list.append(TimerEntryComponent(timer, processed=True))

	def openEdit(self):
		self.session.openWithCallback(self.finishedEdit, TimerEntry, self["timerlist"].getCurrent()[0])
		#self.session.open(TimerEdit, self["timerlist"].getCurrent()[0])
		
	def removeTimer(self):
		list = self["timerlist"]
		currentIndex = list.getCurrentIndex()
		list.moveDown()
		if list.getCurrentIndex() == currentIndex:
			currentIndex -= 1
			list.moveToIndex(currentIndex)
		self.session.nav.RecordTimer.removeEntry(list.getCurrent()[0])
		self.refill()
	
	def refill(self):
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
		print "finished edit"
		if answer[0]:
			print "Edited timer"
			self.session.nav.RecordTimer.timeChanged(answer[1])
			self.fillTimerList()
		else:
			print "Timeredit aborted"

	def finishedAdd(self, answer):
		print "finished add"
		if answer[0]:
			entry = answer[1]
			self.session.nav.RecordTimer.record(entry)
			self.fillTimerList()
		else:
			print "Timeredit aborted"		

	def leave(self):
		self.session.nav.RecordTimer.saveTimer()
		self.session.nav.RecordTimer.on_state_change.remove(self.onStateChange)
		self.close()

	def onStateChange(self, entry):
		self.refill()
