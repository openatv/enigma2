from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Sources.Source import ObsoleteSource
from Components.Harddisk import Harddisk
from Components.NimManager import nimmanager
from Components.About import about

from Tools.DreamboxHardware import getFPVersion

class About(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["EnigmaVersion"] = StaticText("Enigma: " + about.getEnigmaVersionString())
		self["ImageVersion"] = StaticText("Image: " + about.getImageVersionString())

		self["TunerHeader"] = StaticText(_("Detected NIMs:"))

		fp_version = getFPVersion()
		if fp_version is None:
			fp_version = ""
		else:
			fp_version = _("Frontprocessor version: %d") % fp_version

		self["FPVersion"] = StaticText(fp_version)

		nims = nimmanager.nimList()
		for count in range(4):
			if count < len(nims):
				self["Tuner" + str(count)] = StaticText(nims[count])
			else:
				self["Tuner" + str(count)] = StaticText("")

		self["HDDHeader"] = StaticText(_("Detected HDD:"))
		hdd = Harddisk(0)
		if hdd.model() != "":
			self["hddA"] = StaticText(_("%s\n(%s, %d MB free)") % (hdd.model(), hdd.capacity(),hdd.free()))
		else:			
			self["hddA"] = StaticText(_("none"))

		self["actions"] = ActionMap(["SetupActions"], 
			{
				"cancel": self.close,
				"ok": self.close,
			})
