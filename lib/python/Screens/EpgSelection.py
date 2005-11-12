from Screen import Screen
from Components.Button import Button
from Components.EpgList import EPGList
from Components.ActionMap import ActionMap
from Screens.EventView import EventView
from enigma import eServiceReference, eServiceEventPtr
from Screens.FixedMenu import FixedMenu

import xml.dom.minidom

class EPGSelection(Screen):
	def __init__(self, session, root):
		Screen.__init__(self, session)

		self["list"] = EPGList()

		class ChannelActionMap(ActionMap):
			def action(self, contexts, action):
					ActionMap.action(self, contexts, action)

		self["actions"] = ChannelActionMap(["EPGSelectActions", "OkCancelActions"], 
			{
				"cancel": self.close,
				"ok": self.eventSelected,
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
		self.session.open(EventView, event, self.eventViewCallback)
	
	def setRoot(self, root):
		self["list"].setRoot(root)

	def moveUp(self):
		self["list"].moveUp()

	def moveDown(self):
		self["list"].moveDown()
