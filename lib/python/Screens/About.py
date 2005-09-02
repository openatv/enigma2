from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Harddisk import Harddisk


class About(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["text"] = Label("Enigma v2.0a")

		self["tuner"] = Label("Detected NIMs:")
		self["tunerA"] = Label("   Tuner A: Fujitsu QST (DVB-S)")
		self["tunerB"] = Label("   Tuner B: Fujitsu QST (DVB-S)")

		self["hdd"] = Label("Detected HDD:")
		hdd = Harddisk(0)
		self["hddA"] = Label("%s (%s)" % (hdd.model(), hdd.capacity()))

		self["actions"] = ActionMap(["SetupActions"], 
			{
				"cancel": self.close,
				"ok": self.close,
			})
	