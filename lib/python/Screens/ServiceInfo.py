from Components.HTMLComponent import *
from Components.GUIComponent import *
from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from ServiceReference import ServiceReference
from enigma import eListboxPythonMultiContent, eListbox, gFont, iServiceInformation

RT_HALIGN_LEFT = 0

TYPE_TEXT = 0
TYPE_VALUE_HEX = 1
TYPE_VALUE_DEC = 2
TYPE_VALUE_HEX_DEC = 3
TYPE_SLIDER = 4

def ServiceInfoListEntry(a, b, valueType=TYPE_TEXT, param=4):
	res = [ ]

	#PyObject *type, *px, *py, *pwidth, *pheight, *pfnt, *pstring, *pflags;
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 0, 200, 30, 0, RT_HALIGN_LEFT, ""))
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 0, 150, 25, 0, RT_HALIGN_LEFT, a))
	print "b:", b
	if type(b) is not str:
		if valueType == TYPE_VALUE_HEX:
			b = ("0x%0" + str(param) + "x") % b
		elif valueType == TYPE_VALUE_DEC:
			b = str(b)
		elif valueType == TYPE_VALUE_HEX_DEC:
			b = ("0x%0" + str(param) + "x (%dd)") % (b, b)
		else:
			b = str(b)		
	
	
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 170, 0, 350, 25, 0, RT_HALIGN_LEFT, b))

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
		
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"ok": self.close,
			"cancel": self.close,
			"red": self.information,
			"green": self.pids,
			"yellow": self.transponder
		}, -1)
		
		service = session.nav.getCurrentService()
		if service is not None:
			self.info = service.info()
			self.feinfo = service.frontendStatusInfo()
			if self.feinfo:
				print self.feinfo.getFrontendData(False)
		else:
			self.info = None

		self["red"] = Label("Serviceinfo")
		self["green"] = Label("PIDs")
		self["yellow"] = Label("Transponder")
		self["blue"] = Label("")
	
		tlist = [ ]

		self["infolist"] = ServiceInfoList(tlist)
		self.onShown.append(self.information)

	def information(self):
		if self.session.nav.getCurrentlyPlayingServiceReference() is not None:
			name = ServiceReference(self.session.nav.getCurrentlyPlayingServiceReference()).getServiceName()
		else:
			name = "N/A"
		Labels = ( ("Name",  name, TYPE_TEXT),
				   ("Provider", self.getServiceInfoValue(iServiceInformation.sProvider), TYPE_TEXT),
				   ("Videoformat", self.getServiceInfoValue(iServiceInformation.sAspect), TYPE_TEXT),
				   ("Namespace", self.getServiceInfoValue(iServiceInformation.sNamespace), TYPE_VALUE_HEX, 8))
		self.fillList(Labels)
	
	def pids(self):
		Labels = ( ("VideoPID", self.getServiceInfoValue(iServiceInformation.sVideoPID), TYPE_VALUE_HEX_DEC, 4),
				   ("AudioPID", self.getServiceInfoValue(iServiceInformation.sAudioPID), TYPE_VALUE_HEX_DEC, 4),
				   ("PCRPID", self.getServiceInfoValue(iServiceInformation.sPCRPID), TYPE_VALUE_HEX_DEC, 4),
				   ("PMTPID", self.getServiceInfoValue(iServiceInformation.sPMTPID), TYPE_VALUE_HEX_DEC, 4),
				   ("TXTPID", self.getServiceInfoValue(iServiceInformation.sTXTPID), TYPE_VALUE_HEX_DEC, 4),
				   ("TSID", self.getServiceInfoValue(iServiceInformation.sTSID), TYPE_VALUE_HEX_DEC, 4),
				   ("ONID", self.getServiceInfoValue(iServiceInformation.sONID), TYPE_VALUE_HEX_DEC, 4),
				   ("SID", self.getServiceInfoValue(iServiceInformation.sSID), TYPE_VALUE_HEX_DEC, 4))
		self.fillList(Labels)
	
	def transponder(self):
		Labels = ( ("Frequency", "11823", TYPE_TEXT),
				   ("Polarity", "H", TYPE_TEXT))
		self.fillList(Labels)
	
	def fillList(self, Labels):
		tlist = [ ]

		for item in Labels:
			print item
			value = item[1]
			if len(item) < 4:
				tlist.append(ServiceInfoListEntry(item[0]+":", value, item[2]))
			else:
				tlist.append(ServiceInfoListEntry(item[0]+":", value, item[2], item[3]))

		self["infolist"].l.setList(tlist)

	def getServiceInfoValue(self, what):
		if self.info is None:
			return ""
		
		v = self.info.getInfo(what)
		if v == -2:
			v = self.info.getInfoString(what)
		elif v == -1:
			v = "N/A"

		return v
