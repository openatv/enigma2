from Components.HTMLComponent import *
from Components.GUIComponent import *
from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from ServiceReference import ServiceReference
from enigma import eListboxPythonMultiContent, eListbox, gFont

RT_HALIGN_LEFT = 0

def ServiceInfoListEntry(a, b):
	res = [ ]

	#PyObject *px, *py, *pwidth, *pheight, *pfnt, *pstring, *pflags;
	res.append((0, 0, 200, 30, 0, RT_HALIGN_LEFT, ""))
	res.append((0, 0, 150, 25, 0, RT_HALIGN_LEFT, a))
	res.append((170, 0, 150, 25, 0, RT_HALIGN_LEFT, b))

	return res

class ServiceInfoList(HTMLComponent, GUIComponent):
	def __init__(self, source):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.list = source
		self.l.setList(self.list)
		self.l.setFont(0, gFont("Arial", 23))

	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
		self.instance.setItemHeight(25)

	def GUIdelete(self):
		self.instance.setContent(None)
		self.instance = None

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
			tlist.append(ServiceInfoListEntry(item[0]+":", value))		

		self["infolist"] = ServiceInfoList(tlist)
