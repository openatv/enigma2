# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceCenter
from Components.Element import cached
from ServiceReference import resolveAlternate,  ServiceReference
from Tools.Transponder import ConvertToHumanReadable, getChannelNumber
from Components.NimManager import nimmanager
import Screens.InfoBar

class TransponderInfo(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = type.split(";")

	@cached
	def getText(self):
		service = self.source.service
		if isinstance(service, iPlayableServicePtr):
			info = service and service.info()
			ref = None
		else: # reference
			info = service and self.source.info
			ref = service
		if not info:
			return ""
		if ref:
			nref = resolveAlternate(ref)
			if nref:
				ref = nref
				info = eServiceCenter.getInstance().info(ref)
			transponderraw = info.getInfoObject(ref, iServiceInformation.sTransponderData)
		else:
			transponderraw = info.getInfoObject(iServiceInformation.sTransponderData)
		if "InRootOnly" in self.type and not self.rootBouquet():
			return ""
		if "NoRoot" in self.type and self.rootBouquet():
			return ""
		if transponderraw:
			transponderdata = ConvertToHumanReadable(transponderraw)
			if not transponderdata["system"]:
				transponderdata["system"] = transponderraw.get("tuner_type", "None")
			if not transponderdata["system"]:
				return ""
			if "DVB-T" in transponderdata["system"]:
				return "%s %s %d MHz %s" % (transponderdata["system"], transponderdata["channel"], transponderdata["frequency"]/1000000 + 0.5 , transponderdata["bandwidth"])
			elif "DVB-C" in transponderdata["system"]:
				return "%s %d MHz %d %s %s" % (transponderdata["system"], transponderdata["frequency"]/1000 + 0.5, transponderdata["symbol_rate"]/1000 + 0.5, transponderdata["fec_inner"], \
					transponderdata["modulation"])
			return "%s %d %s %d %s %s %s" % (transponderdata["system"], transponderdata["frequency"]/1000 + 0.5, transponderdata["polarization_abbreviation"], transponderdata["symbol_rate"]/1000 + 0.5, \
				transponderdata["fec_inner"], transponderdata["modulation"], transponderdata["detailed_satpos" in self.type and "orbital_position" or "orb_pos"])
		if ref:
			result = ref.toString()
		else:
			result = info.getInfoString(iServiceInformation.sServiceref)
		if "%3a//" in result:
			return _("Stream") + " " + result.rsplit("%3a//", 1)[1].split("/")[0]
		return ""

	text = property(getText)

	def rootBouquet(self):
		servicelist = Screens.InfoBar.InfoBar.instance.servicelist
		epg_bouquet = servicelist and servicelist.getRoot()
		if ServiceReference(epg_bouquet).getServiceName():
			return False
		return True

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart,):
			Converter.changed(self, what)
