from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Harddisk import Harddisk

class About(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["text"] = Label("Enigma v2.0b")

		self["tuner"] = Label("Detected NIMs:")
		self["tunerA"] = Label("   Tuner A: Alps BSBE1 (DVB-S)")
		self["tunerB"] = Label("   Tuner B: Alps BSBE1 (DVB-S)")

		self["hdd"] = Label("Detected HDD:")
		hdd = Harddisk(0)
		#self["hddA"] = Label("%s (%s, %d MB free)" % (hdd.model(), hdd.capacity(),hdd.free()))
		self["hddA"] = Label("Seagate 398 GByte (323 GByte free)")

		self["actions"] = ActionMap(["SetupActions"], 
			{
				"cancel": self.close,
				"ok": self.close,
			})
	