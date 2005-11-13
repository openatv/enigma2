from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from enigma import eServiceEventPtr
from ServiceReference import ServiceReference

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
				"nextEvent": self.nextEvent
			})
		self.setEvent(Event)
		self.setService(Ref)

	def prevEvent(self):
		if self.cbFunc is not None:
			self.cbFunc(self.setEvent, -1)

	def nextEvent(self):
		if self.cbFunc is not None:
			self.cbFunc(self.setEvent, +1)

	def setService(self, service):
		self.currentService=service
		name = self.currentService.getServiceName()
		if name is not None:
			self["channel"].setText(name)
		else:
			self["channel"].setText("unknown service")

	def setEvent(self, event):
#		FIXME .. how to set eWindow titlebar?
#		self.instance.setTitle(event.getEventName())
		text = event.getShortDescription()
		if len(text) > 0:
			text = text + '\n\n'
		text = text + event.getExtendedDescription()
		self["epg_description"].setText(text)
		self["datetime"].setText(event.getBeginTimeString())
		self["duration"].setText("%d min"%(event.getDuration()/60))

	def pageUp(self):
		self["epg_description"].pageUp()
	
	def pageDown(self):
		self["epg_description"].pageDown()
