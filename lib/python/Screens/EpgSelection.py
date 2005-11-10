from Screen import Screen
from Components.Button import Button
from Components.EpgList import EPGList
from Components.ActionMap import ActionMap

from enigma import eServiceReference

from Screens.FixedMenu import FixedMenu

import xml.dom.minidom

class EPGSelection(Screen):
	def __init__(self, session, root):
		Screen.__init__(self, session)

		self["list"] = EPGList()
#		self["list"].setRoot(root)

		class ChannelActionMap(ActionMap):
			def action(self, contexts, action):
					ActionMap.action(self, contexts, action)

		self["actions"] = ChannelActionMap(["ChannelSelectActions", "OkCancelActions"], 
			{
				"cancel": self.close,
				"ok": self.eventSelected,
			})
		self["actions"].csel = self
		setRoot(root)

	def eventSelected(self):
		ref = self["list"].getCurrent()
# open eventdetail view... not finished yet
		self.close()
	
	def setRoot(self, root):
		self["list"].setRoot(root)

	def moveUp(self):
		self["list"].moveUp()

	def moveDown(self):
		self["list"].moveDown()
