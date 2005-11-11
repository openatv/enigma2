from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from enigma import eWidget, eServiceEventPtr, eLabel

class EventView(Screen):
	def __init__(self, session, Event, callback):
		Screen.__init__(self, session)

		self.cbFunc = callback
		print self.cbFunc

		self["epg_description"] = Label()
		self["datetime"] = Label()
		self["channel"] = Label()
		self["scrollbar"] = ProgressBar()
		self["duration"] = Label()

		self["actions"] = ActionMap(["OkCancelActions", "EventViewActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"scrollUp": self.scrollUp,
				"scrollDown": self.scrollDown,
				"prevEvent": self.prevEvent,
				"nextEvent": self.nextEvent
			})
		self.setEvent(Event)

	def prevEvent(self):
		if self.cbFunc is not None:
			self.cbFunc(self.setEvent, -1)

	def nextEvent(self):
		if self.cbFunc is not None:
			self.cbFunc(self.setEvent, +1)

	def setEvent(self, event):
		text = event.getShortDescription()
		if len(text) > 0:
			text = text + '\n\n'
		text = text + event.getExtendedDescription()
		self["epg_description"].setText(text)
		self["datetime"].setText(event.getBeginTimeString())
		self["channel"].setText("Unknown Service")
		self["duration"].setText("%d min"%(event.getDuration()/60))

	def scrollUp(self):
		print "scrollUp"

	def scrollDown(self):
		print "scrollDown"
