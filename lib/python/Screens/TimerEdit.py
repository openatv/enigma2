from Screen import Screen
from Components.TimerList import TimerList, TimerEntry
from Components.ActionMap import ActionMap
from Components.TimeInput import TimeInput
from Components.Label import Label
from Components.Button import Button
from Components.TextInput import TextInput

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
			list.append(TimerEntry(timer, 0))
		
		for timer in session.nav.RecordTimer.processed_timers:
			list.append(TimerEntry(timer, 1))
		
		self["timerlist"] = TimerList(list)

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
#				"ok": self.openEdit,
				"cancel": self.close
			})

	def openEdit(self):
		self.session.open(TimerEdit, self["timerlist"].getCurrent()[0])
