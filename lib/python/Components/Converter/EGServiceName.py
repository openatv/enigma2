# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr
from enigma import eServiceCenter, eServiceReference, iServiceInformation

from Components.Element import cached

class EGServiceName(Converter, object):
	NAME = 0
	PROVIDER = 1
	REFERENCE = 2
	SERVICENUMBER = 3

	def __init__(self, type):
		Converter.__init__(self, type)
		self.getLists()

		if type == "Provider":
			self.type = self.PROVIDER
		elif type == "Reference":
			self.type = self.REFERENCE
		elif type == "ServiceNumber":
			self.type = self.SERVICENUMBER
		else:
			self.type = self.NAME

	@cached
	def getService(self):
		return self.source.service
	
	def getServiceInfoValue(self, info, what, ref=None):
		v = ref and info.getInfo(ref, what) or info.getInfo(what)
		if v != iServiceInformation.resIsString:
			return "N/A"
		return ref and info.getInfoString(ref, what) or info.getInfoString(what)

	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return ""

		name = info.getName().replace('\xc2\x86', '').replace('\xc2\x87', '')
		number = self.getServiceNumber(name, info.getInfoString(iServiceInformation.sServiceref))

		if isinstance(service, iPlayableServicePtr):
			info = service and service.info()
			ref = None
		else: # reference
			info = service and self.source.info
			ref = service
		if info is None:
			return ""
		if ref:
			transponder_info = info.getInfoObject(ref, iServiceInformation.sTransponderData)
		else:
			transponder_info = info.getInfoObject(iServiceInformation.sTransponderData)
			
		transponderData = info.getInfoObject(iServiceInformation.sTransponderData)
		orbital = ""
		info = service and service.info()
		
		try:
			if transponderData is not None:
				if transponderData.has_key("tuner_type"):
					if (transponderData["tuner_type"] == "DVB-S") or (transponderData["tuner_type"] == "DVB-S2"):
						orbital = transponderData["orbital_position"]
						orbital = int(orbital)
						if orbital > 1800:
							orbital = str((float(3600 - orbital))/10.0) + "\xc2\xb0 W"
						else:
							orbital = str((float(orbital))/10.0) + "\xc2\xb0 E"
					elif (transponderData["tuner_type"] == "DVB-T") or (transponderData["tuner_type"] == "DVB-T2"):
					  orbital = "DVB-T"
					elif (transponderData["tuner_type"] == "DVB-C"):
					  orbital = "DVB-C"
                except:
                    orbital = "NONE"
				
		if self.type == self.NAME:
			name = ref and info.getName(ref)
			if name is None:
				name = ((info.getName() + " (") + orbital + ")")
			return name.replace('\xc2\x86', '').replace('\xc2\x87', '')
		elif self.type == self.PROVIDER:
			return self.getServiceInfoValue(info, iServiceInformation.sProvider, ref)
		elif self.type == self.REFERENCE:
			return self.getServiceInfoValue(info, iServiceInformation.sServiceref, ref)
		elif self.type == self.SERVICENUMBER:
			return number


	text = property(getText)
	service = property(getService)

	def changed(self, what):
		Converter.changed(self, what)
			
	def getListFromRef(self, ref):
		list = []
		
		serviceHandler = eServiceCenter.getInstance()
		services = serviceHandler.list(ref)
		bouquets = services and services.getContent("SN", True)
		
		for bouquet in bouquets:
			services = serviceHandler.list(eServiceReference(bouquet[0]))
			channels = services and services.getContent("SN", True)
			for channel in channels:
				if not channel[0].startswith("1:64:"): # Ignore marker
					list.append(channel[1].replace('\xc2\x86', '').replace('\xc2\x87', ''))
		
		return list

	def getLists(self):
		self.tv_list = self.getListFromRef(eServiceReference('1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 195) || (type == 25) FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
		self.radio_list = self.getListFromRef(eServiceReference('1:7:2:0:0:0:0:0:0:0:(type == 2) FROM BOUQUET "bouquets.radio" ORDER BY bouquet'))


	def getServiceNumber(self, name, ref):
		list = []
		if ref.startswith("1:0:2"):
			list = self.radio_list
		elif ref.startswith("1:0:1"):
			list = self.tv_list
		number = ""
		if name in list:
			for idx in range(1, len(list)):
				if name == list[idx-1]:
					number = str(idx)
					break
		return number

