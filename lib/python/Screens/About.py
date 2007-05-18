from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Harddisk import Harddisk
from Components.NimManager import nimmanager
from Components.MenuList import MenuList
from Components.About import about

from Tools.DreamboxHardware import getFPVersion

class About(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["text"] = Label("Enigma v" + about.getVersionString())

		self["tuner"] = Label(_("Detected NIMs:"))

		fp_version = getFPVersion()
		if fp_version is None:
			fp_version = ""
		else:
			fp_version = _("Frontprocessor version: %d") % fp_version
		
		self["fpVersion"] = Label(fp_version)
		
		nims = nimmanager.nimList()
		for count in range(4):
			if count < len(nims):
				self["tuner" + str(count)] = Label(nims[count])
			else:
				self["tuner" + str(count)] = Label("")

		self["hdd"] = Label(_("Detected HDD:"))
		hdd = Harddisk(0)
		if hdd.model() != "":
			self["hddA"] = Label(_("%s\n(%s, %d MB free)") % (hdd.model(), hdd.capacity(),hdd.free()))
		else:			
			self["hddA"] = Label(_("none"))

		self["actions"] = ActionMap(["SetupActions"], 
			{
				"cancel": self.close,
				"ok": self.close,
			})
