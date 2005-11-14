from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Harddisk import Harddisk
from Components.NimManager import nimmanager
from Components.MenuList import MenuList

class About(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["text"] = Label("Enigma v2.0b")

		self["tuner"] = Label("Detected NIMs:")
		
		nims = nimmanager.nimList()
		count = 0
		for i in nims:
			self["tuner" + str(count)] = Label(i[0])
			count += 1

		self["hdd"] = Label("Detected HDD:")
		hdd = Harddisk(0)
		if hdd.model() != "":
			self["hddA"] = Label("%s (%s, %d MB free)" % (hdd.model(), hdd.capacity(),hdd.free()))
		else:			
			self["hddA"] = Label("none")

		self["actions"] = ActionMap(["SetupActions"], 
			{
				"cancel": self.close,
				"ok": self.close,
			})
	