from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Harddisk import harddiskmanager			#global harddiskmanager
from Components.MenuList import MenuList
from Components.Label import Label
from Screens.MessageBox import MessageBox

class HarddiskSetup(Screen):
	def __init__(self, session, hdd):
		Screen.__init__(self, session)
		self.hdd = hdd
		
		self["model"] = Label("Model: " + hdd.model())
		self["capacity"] = Label("Capacity: " + hdd.capacity())
		self["bus"] = Label("Bus: " + hdd.bus())
		self["initialize"] = Label("Initialize")

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.close,
			"cancel": self.close
		})
		
		self["shortcuts"] = ActionMap(["ShortcutActions"],
		{
			"red": self.hddInitialize
		})

	def hddInitialize(self):
		print "this will start the initialize now!"
		self.hdd.initialize()

class HarddiskSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		if harddiskmanager.HDDCount() == 0:
			tlist = []
			tlist.append(("no HDD found", 0))
			self["hddlist"] = MenuList(tlist)
		else:			
			self["hddlist"] = MenuList(harddiskmanager.HDDList())
		
		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.okbuttonClick ,
			"cancel": self.close
		})

	def okbuttonClick(self):
		selection = self["hddlist"].getCurrent()
		if selection[1] != 0:
			self.session.open(HarddiskSetup, selection[1])
