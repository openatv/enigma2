from Screen import Screen
from Components.Button import Button
from Components.EpgList import EPGList
from Components.ActionMap import ActionMap
from Screens.EventView import EventView
from enigma import eServiceReference, eServiceEventPtr
from Screens.FixedMenu import FixedMenu
from RecordTimer import RecordTimerEntry, parseEvent
from TimerEdit import TimerEditList
from TimerEntry import TimerEntry
from ServiceReference import ServiceReference

import xml.dom.minidom

class EPGSelection(Screen):
	def __init__(self, session, root):
		Screen.__init__(self, session)

		self["list"] = EPGList()

		class ChannelActionMap(ActionMap):
			def action(self, contexts, action):
					ActionMap.action(self, contexts, action)
					
		self["key_red"] = Button("")
		self["key_green"] = Button(_("Add timer"))
		self["key_yellow"] = Button("")
		self["key_blue"] = Button("")

		self["actions"] = ChannelActionMap(["EPGSelectActions", "OkCancelActions"], 
			{
				"cancel": self.close,
				"ok": self.eventSelected,
				"timerAdd": self.timerAdd
			})
		self["actions"].csel = self
		self.setRoot(root)

	def eventViewCallback(self, setEvent, val):
		if val == -1:
			self.moveUp()
			setEvent(self["list"].getCurrent())
		elif val == +1:
			self.moveDown()
			setEvent(self["list"].getCurrent())

	def eventSelected(self):
		event = self["list"].getCurrent()
		self.session.open(EventView, event, self.currentService, self.eventViewCallback)
	
	def timerAdd(self):
		event = self["list"].getCurrent()
		
		if event is None:
			return
		
		newEntry = RecordTimerEntry(self.currentService, *parseEvent(event))
		self.session.openWithCallback(self.timerEditFinished, TimerEntry, newEntry)
	
	def timerEditFinished(self, answer):
		if (answer[0]):
			self.session.nav.RecordTimer.record(answer[1])
		else:
			print "Timeredit aborted"	

	def setRoot(self, root):
		self.currentService=ServiceReference(root)
		self["list"].setRoot(root)

	def moveUp(self):
		self["list"].moveUp()

	def moveDown(self):
		self["list"].moveDown()
