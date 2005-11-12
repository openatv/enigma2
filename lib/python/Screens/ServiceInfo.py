from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList

class ServiceInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.close,
			"cancel": self.close
		}, -1)
	
		Labels = ("Name", "Provider", "VideoPID", "AudioPID",
							"PCRPID", "PMTPID", "TXTPID", "Videoformat",
							"TSID", "ONID", "SID", "Namespace")
	
		tlist = [ ]

		for item in Labels:
			tlist.append((item + ":",0))
		
		self["infolist"] = MenuList(tlist)
