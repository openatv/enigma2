# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceCenter
from Components.Element import cached
from ServiceReference import resolveAlternate,  ServiceReference
from Tools.Transponder import ConvertToHumanReadable
from Components.NimManager import nimmanager
from Components.Converter.ChannelNumbers import channelnumbers
import Screens.InfoBar

class ServiceName(Converter, object):
	NAME = 0
	PROVIDER = 1
	REFERENCE = 2
	EDITREFERENCE = 3
	TRANSPONDER = 4

	def __init__(self, type):
		Converter.__init__(self, type)

		self.mode = ""
		if ';' in type:
			type, self.mode = type.split(';')

		if type == "Provider":
			self.type = self.PROVIDER
		elif type == "Reference":
			self.type = self.REFERENCE
		elif type == "EditReference":
			self.type = self.EDITREFERENCE
		elif type == "TransponderInfo":
			self.type = self.TRANSPONDER
		else:
			self.type = self.NAME

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
		if self.type == self.NAME:
			name = ref and info.getName(ref)
			if name is None:
				name = info.getName()
			return name.replace('\xc2\x86', '').replace('\xc2\x87', '')
		elif self.type == self.PROVIDER:
			return info.getInfoString(iServiceInformation.sProvider)
		elif self.type == self.REFERENCE or self.type == self.EDITREFERENCE and hasattr(self.source, "editmode") and self.source.editmode:
			if not ref:
				return info.getInfoString(iServiceInformation.sServiceref)
			nref = resolveAlternate(ref)
			if nref:
				ref = nref
			return ref.toString()
		elif self.type == self.TRANSPONDER:
			if ref:
				nref = resolveAlternate(ref)
				if nref:
					ref = nref
					info = eServiceCenter.getInstance().info(ref)
				transponder_info = info.getInfoObject(ref, iServiceInformation.sTransponderData)
			else:
				transponder_info = info.getInfoObject(iServiceInformation.sTransponderData)
			if "InRootOnly" in self.mode and not self.rootBouquet():
				return ""
			if "NoRoot" in self.mode and self.rootBouquet():
				return ""
			if transponder_info:
				self.t_info = ConvertToHumanReadable(transponder_info)
				if "DVB-T" in self.system():
					return	self.dvb_t()
				elif "DVB-C" in self.system():
					return self.dvb_c()
				return 	self.dvb_s()
			if ref:
				result = ref.toString()
			else:
				result = info.getInfoString(iServiceInformation.sServiceref)
			if "%3a//" in result:
				return result.rsplit("%3a//", 1)[1].split("/")[0]
			return ""

	text = property(getText)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart,):
			Converter.changed(self, what)

	def dvb_s(self):
		return "%s %d %s %d %s %s %s" % (self.system(), self.freq()/1000, self.polar(), self.s_rate()/1000, self.fec(), self.mod(), self.orb_pos())
	def dvb_t(self):
		return "%s %s %d/%s" % (self.system(), self.ch_number(), self.freq()/1000000 + 0.5 , self.bandwidth())
	def dvb_c(self):
		return "%s %d %s %d %s %s" % (self.system(), self.freq()/1000, _("MHz"), self.s_rate()/1000, self.fec(), self.mod())
	def system(self):
		return self.t_info["system"]
	def freq(self):
		return self.t_info["frequency"]
	def bandwidth(self):
		return self.t_info["bandwidth"]
	def s_rate(self):
		return self.t_info["symbol_rate"]
	def mod(self):
		return self.t_info["modulation"]
	def polar(self):
		return self.t_info["polarization_abbreviation"]
	def orb_pos(self):
		op = self.t_info["orbital_position"]
		if '(' in op:
			op = op.split('(')[1]
			return "%s°%s" % (op[:-2],op[-2:-1])
		op = op.split(' ')[0]
		return "%s°%s" % (op[:-1],op[-1:])
	def fec(self):
		return self.t_info["fec_inner"]
	def ch_number(self):
		for n in nimmanager.nim_slots:
			if n.isCompatible("DVB-T"):
				channel = channelnumbers.getChannelNumber(self.freq(), n.slot)
				if channel:
					return _("CH") + "%s" % channel
		return ""

	def rootBouquet(self):
		servicelist = Screens.InfoBar.InfoBar.instance.servicelist
		epg_bouquet = servicelist and servicelist.getRoot()
		if ServiceReference(epg_bouquet).getServiceName():
			return False
		return True