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
		
		cap = hdd.capacity() / 1000 * 512 / 1000
		capstr = "Capacity: %d.%03d GB" % (cap / 1000, cap % 1000)

		self["model"] = Label("Model: " + hdd.model())
		self["capacity"] = Label(capstr)

		idx = hdd.getIndex()
		
		if idx & 1:
			busstr = "Slave"
		else:	
			busstr = "Master"
		
		self["bus"] = Label("Bus: " + busstr)
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
		if self.hdd.getIndex() == 2:		#CF
			print "not a good idea!"
			self.session.open(MessageBox, "not a good idea - this will kill our rootfs!")
		else:	
			pass
			#self.hdd.initialize()

class HarddiskSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["hddlist"] = MenuList(harddiskmanager.HDDList())
		
		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.okbuttonClick ,
			"cancel": self.close
		})

	def okbuttonClick(self):
		selection = self["hddlist"].getCurrent()
		self.session.open(HarddiskSetup, selection[1])
		print "ok"
		pass
