from Components.HTMLComponent import *
from Components.GUIComponent import *
from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from ServiceReference import ServiceReference
from enigma import eListboxPythonMultiContent, eListbox, gFont, iServiceInformation

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
		self.l.setFont(0, gFont("Regular", 23))

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
		
		service = session.nav.getCurrentService()
		if service is not None:
			self.info = service.info()
		else:
			self.info = None

		if self.session.nav.getCurrentlyPlayingServiceReference() is not None:
			name = ServiceReference(self.session.nav.getCurrentlyPlayingServiceReference()).getServiceName()
		else:
			name = "N/A"
		Labels = ( ("Name",  name),
				   ("Provider", self.getValue(iServiceInformation.sProvider)),
				   ("VideoPID", self.getValue(iServiceInformation.sVideoPID)),
				   ("AudioPID", self.getValue(iServiceInformation.sAudioPID)),
				   ("PCRPID", self.getValue(iServiceInformation.sPCRPID)),
				   ("PMTPID", self.getValue(iServiceInformation.sPMTPID)),
				   ("TXTPID", self.getValue(iServiceInformation.sTXTPID)),
				   ("Videoformat", self.getValue(iServiceInformation.sAspect)),
				   ("TSID", self.getValue(iServiceInformation.sTSID)),
				   ("ONID", self.getValue(iServiceInformation.sONID)),
				   ("SID", self.getValue(iServiceInformation.sSID)),
				   ("Namespace", self.getValue(iServiceInformation.sNamespace)))
	
		tlist = [ ]

		for item in Labels:
			value = item[1]
			tlist.append(ServiceInfoListEntry(item[0]+":", value))		

		self["infolist"] = ServiceInfoList(tlist)

	def getValue(self, what):
		if self.info is None:
			return ""
		
		v = self.info.getInfo(what)
		if v == -2:
			v = self.info.getInfoString(what)
		elif v != -1:
			if what in [iServiceInformation.sVideoPID, 
					iServiceInformation.sAudioPID, iServiceInformation.sPCRPID, iServiceInformation.sPMTPID, 
					iServiceInformation.sTXTPID, iServiceInformation.sTSID, iServiceInformation.sONID,
					iServiceInformation.sSID]:
				v = "0x%04x (%dd)" % (v, v)
			elif what in [iServiceInformation.sNamespace]:
				v = "0x%08x" % (v)
			else:
				v = str(v)
		else:
			v = "N/A"

		return v
