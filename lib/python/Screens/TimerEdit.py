from Screen import Screen
from Components.TimerList import TimerList, TimerEntryComponent
from Components.ActionMap import ActionMap
from Components.TimeInput import TimeInput
from Components.Label import Label
from Components.Button import Button
from Components.TextInput import TextInput
from TimerEntry import TimerEntry
from RecordTimer import RecordTimerEntry
from time import *
from ServiceReference import ServiceReference

class TimerEdit(Screen):
	def __init__(self, session, entry):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.apply,
				"cancel": self.close
			})
		
		self["shortcuts"] = ActionMap(["ShortcutActions"],
			{
				"red": self.beginFocus,
				"yellow": self.endFocus,
				"green": self.descFocus
			})
		
		self.entry = entry
		# begin, end, description, service
		self["begin"] = TimeInput()
		self["end"] = TimeInput()
		
		self["lbegin"] = Label("Begin")
		self["lend"] = Label("End")
		
		self["description"] = TextInput()
		self["apply"] = Button("Apply")
		self["service"] = Button()
		
		self["description"].setText(entry.description);
	
	def beginFocus(self):
		self.setFocus(self["begin"])
	
	def endFocus(self):
		self.setFocus(self["end"])
	
	def descFocus(self):
		self.setFocus(self["description"])
	
	def apply(self):
		print "applied!"
	
class TimerEditList(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		list = [ ]
		for timer in session.nav.RecordTimer.timer_list:
			list.append(TimerEntryComponent(timer, 0))
		
		for timer in session.nav.RecordTimer.processed_timers:
			list.append(TimerEntryComponent(timer, 1))
		
		self["timerlist"] = TimerList(list)
		
		self["key_red"] = Button("Delete")
		self["key_green"] = Button("Add")
		self["key_yellow"] = Button("")
		self["key_blue"] = Button("")

		self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions"], 
			{
				"ok": self.openEdit,
				"cancel": self.close,
				"red": self.removeTimer,
				"green": self.addTimer
			})

	def openEdit(self):
		self.session.open(TimerEntry, self["timerlist"].getCurrent()[0])
		#self.session.open(TimerEdit, self["timerlist"].getCurrent()[0])
		
	def removeTimer(self):
		self.session.nav.RecordTimer.removeEntry(self["timerlist"].getCurrent()[0])
	
	def addTimer(self):
		begin = time()
		end = time() + 60
		
		epg = None
		try:
			service = self.session.nav.getCurrentService()
			info = service.info()
			ev = info.getEvent(0)
			epg = ev
		except:
			pass
		
		if (epg == None):
			description = "unknown event"
		else:
			description = ev.getEventName()
			# FIXME we need a timestamp here:
			begin = ev.getBeginTime()
			
			print begin
			print ev.getDuration()
			end = begin + ev.getDuration()


		# FIXME only works if already playing a service
		serviceref = ServiceReference(self.session.nav.getCurrentlyPlayingServiceReference())
		
		newEntry = RecordTimerEntry(begin, end, serviceref, epg, description)
		self.session.open(TimerEntry, newEntry)
		
