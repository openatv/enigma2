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
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 0, 200, 25, 0, RT_HALIGN_LEFT, a))
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
	
	
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 220, 0, 350, 25, 0, RT_HALIGN_LEFT, b))

	return res

class ServiceInfoList(HTMLComponent, GUIComponent):
	def __init__(self, source):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.list = source
		self.l.setList(self.list)
		self.l.setFont(0, gFont("Regular", 23))

	GUI_WIDGET = eListbox
	
	def postWidgetCreate(self, instance):
		self.instance.setContent(self.l)
		self.instance.setItemHeight(25)

class ServiceInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"ok": self.close,
			"cancel": self.close,
			"red": self.information,
			"green": self.pids,
			"yellow": self.transponder,
			"blue": self.tuner
		}, -1)
		
		service = session.nav.getCurrentService()
		if service is not None:
			self.info = service.info()
			self.feinfo = service.frontendInfo()
			print self.info.getInfoObject(iServiceInformation.sCAIDs);
		else:
			self.info = None


		self["red"] = Label("Serviceinfo")
		self["green"] = Label("PIDs")
		self["yellow"] = Label("Transponder")
		self["blue"] = Label("Tuner status")
	
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
	
	def showFrontendData(self, real):
		frontendData = self.feinfo and self.feinfo.getFrontendData(real)
		Labels = self.getFEData(frontendData)
		self.fillList(Labels)
	
	def transponder(self):
		self.showFrontendData(True)
		
	def tuner(self):
		self.showFrontendData(False)
		
	def getFEData(self, frontendData):
		if frontendData is None:
			return []
		if frontendData["tuner_type"] == "DVB-S":
			return ( ("NIM", ['A', 'B', 'C', 'D'][frontendData["tuner_number"]], TYPE_TEXT),
					   ("Type", frontendData["system"], TYPE_TEXT),
					   ("Modulation", frontendData["modulation"], TYPE_TEXT),
					   ("Orbital position", frontendData["orbital_position"], TYPE_VALUE_DEC),
					   ("Frequency", frontendData["frequency"], TYPE_VALUE_DEC),
					   ("Symbolrate", frontendData["symbol_rate"], TYPE_VALUE_DEC),
					   ("Polarization", frontendData["polarization"], TYPE_TEXT),
					   ("Inversion", frontendData["inversion"], TYPE_TEXT),
					   ("FEC inner", frontendData["fec_inner"], TYPE_TEXT),
				   		)
		elif frontendData["tuner_type"] == "DVB-C":
			return ( ("NIM", ['A', 'B', 'C', 'D'][frontendData["tuner_number"]], TYPE_TEXT),
					   ("Type", frontendData["tuner_type"], TYPE_TEXT),
					   ("Frequency", frontendData["frequency"], TYPE_VALUE_DEC),
					   ("Symbolrate", frontendData["symbol_rate"], TYPE_VALUE_DEC),
					   ("Modulation", frontendData["modulation"], TYPE_TEXT),
					   ("Inversion", frontendData["inversion"], TYPE_TEXT),
					   ("FEC inner", frontendData["fec_inner"], TYPE_TEXT),
				   		)
		elif frontendData["tuner_type"] == "DVB-T":
			return ( ("NIM", ['A', 'B', 'C', 'D'][frontendData["tuner_number"]], TYPE_TEXT),
					   ("Type", frontendData["tuner_type"], TYPE_TEXT),
					   ("Frequency", frontendData["frequency"], TYPE_VALUE_DEC),
					   ("Inversion", frontendData["inversion"], TYPE_TEXT),
					   ("Bandwidth", frontendData["bandwidth"], TYPE_VALUE_DEC),
					   ("CodeRateLP", frontendData["code_rate_lp"], TYPE_TEXT),
					   ("CodeRateHP", frontendData["code_rate_hp"], TYPE_TEXT),
					   ("Constellation", frontendData["constellation"], TYPE_TEXT),
					   ("Transmission Mode", frontendData["transmission_mode"], TYPE_TEXT),
					   ("Guard Interval", frontendData["guard_interval"], TYPE_TEXT),
					   ("Hierarchy Inform.", frontendData["hierarchy_information"], TYPE_TEXT),
				   		)
		
	def fillList(self, Labels):
		tlist = [ ]

		for item in Labels:
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
