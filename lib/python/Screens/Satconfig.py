from Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigList
from Components.config import *
from Components.MenuList import MenuList
from Components.NimManager import nimmanager

class NimSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["nimlist"] = MenuList(nimmanager.nimList())

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.okbuttonClick ,
			"cancel": self.close
		})

	def okbuttonClick(self):
		#selection = self["hddlist"].getCurrent()
		#self.session.open(HarddiskSetup, selection[1])
		pass
