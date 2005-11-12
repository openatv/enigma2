from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from ServiceReference import ServiceReference

class ServiceInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.close,
			"cancel": self.close
		}, -1)
	
		Labels = ( ("Name",  "ServiceReference(self.session.nav.getCurrentlyPlayingServiceReference()).getServiceName()"),
				   ("Provider", ),
				   ("VideoPID",""),
				   ("AudioPID",""),
				   ("PCRPID",""),
				   ("PMTPID",""),
				   ("TXTPID",""),
				   ("Videoformat",""),
				   ("TSID",""),
				   ("ONID",""),
				   ("SID",""),
				   ("Namespace",""))
	
		tlist = [ ]

		for item in Labels:
			try:
				value = str(eval(item[1]))
			except:
				value = "N/A"
			tlist.append((item[0] + ": " + value,0))
		
		self["infolist"] = MenuList(tlist)
