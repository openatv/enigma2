from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from enigma import eServiceEventPtr
from ServiceReference import ServiceReference
from RecordTimer import RecordTimerEntry, parseEvent
from TimerEntry import TimerEntry

class EventView(Screen):
	def __init__(self, session, Event, Ref, callback=None):
		Screen.__init__(self, session)
		self.cbFunc = callback
		self.currentService=None
		self["epg_description"] = ScrollLabel()
		self["datetime"] = Label()
		self["channel"] = Label()
		self["duration"] = Label()
		self["actions"] = ActionMap(["OkCancelActions", "EventViewActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"pageUp": self.pageUp,
				"pageDown": self.pageDown,
				"prevEvent": self.prevEvent,
				"nextEvent": self.nextEvent,
				"timerAdd": self.timerAdd
			})
		self.setEvent(Event)
		self.setService(Ref)

	def prevEvent(self):
		if self.cbFunc is not None:
			self.cbFunc(self.setEvent, -1)

	def nextEvent(self):
		if self.cbFunc is not None:
			self.cbFunc(self.setEvent, +1)
			
	def timerAdd(self):
		newEntry = RecordTimerEntry(self.currentService, *parseEvent(self.event))
		self.session.openWithCallback(self.timerEditFinished, TimerEntry, newEntry)

	def timerEditFinished(self, answer):
		if (answer[0]):
			self.session.nav.RecordTimer.record(answer[1])
		else:
			print "Timeredit aborted"	

	def setService(self, service):
		self.currentService=service
		name = self.currentService.getServiceName()
		if name is not None:
			self["channel"].setText(name)
		else:
			self["channel"].setText(_("unknown service"))

	def setEvent(self, event):
		self.event = event
		text = event.getEventName()
		short = event.getShortDescription()
		ext = event.getExtendedDescription()
		if len(short) > 0 and short != text:
			text = text + '\n\n' + short
		if len(ext) > 0:
			if len(text) > 0:
				text = text + '\n\n'
			text = text + ext
		self.session.currentDialog.instance.setTitle(event.getEventName())
		self["epg_description"].setText(text)
		self["datetime"].setText(event.getBeginTimeString())
		self["duration"].setText(_("%d min")%(event.getDuration()/60))

	def pageUp(self):
		self["epg_description"].pageUp()
	
	def pageDown(self):
		self["epg_description"].pageDown()
