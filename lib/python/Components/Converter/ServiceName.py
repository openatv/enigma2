# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from Components.config import config
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceReference, eEPGCache, eServiceCenter
from Components.Element import cached
from ServiceReference import resolveAlternate, ServiceReference
from Tools.Directories import fileExists
from Tools.Transponder import ConvertToHumanReadable
from Components.NimManager import nimmanager
from Components.Converter.ChannelNumbers import channelnumbers
import Screens.InfoBar

class ServiceName(Converter, object):
	NAME = 0
	NAME_ONLY = 1
	NAME_EVENT = 2
	PROVIDER = 3
	REFERENCE = 4
	EDITREFERENCE = 5
	TRANSPONDER = 6

	def __init__(self, type):
		Converter.__init__(self, type)
		self.epgQuery = eEPGCache.getInstance().lookupEventTime
		self.mode = ""
		if ';' in type:
			type, self.mode = type.split(';')
		if type == "Provider":
			self.type = self.PROVIDER
		elif type == "Reference":
			self.type = self.REFERENCE
		elif type == "EditReference":
			self.type = self.EDITREFERENCE
		elif type == "NameOnly":
			self.type = self.NAME_ONLY
		elif type == "NameAndEvent":
			self.type = self.NAME_EVENT
		elif type == "TransponderInfo":
			self.type = self.TRANSPONDER
		else:
			self.type = self.NAME

	@cached
	def getText(self):
		service = self.source.service
		info = None
		if isinstance(service, eServiceReference):
			info = self.source.info
		elif isinstance(service, iPlayableServicePtr):
			info = service and service.info()
			service = None

		if not info:
			return ""

		if self.type == self.NAME or self.type == self.NAME_ONLY or self.type == self.NAME_EVENT:
			name = service and info.getName(service)
			if name is None:
				name = info.getName()
			name = name.replace('\xc2\x86', '').replace('\xc2\x87', '')
			if self.type == self.NAME_EVENT:
				act_event = info and info.getEvent(0)
				if not act_event and info:
					refstr = info.getInfoString(iServiceInformation.sServiceref)
					act_event = self.epgQuery(eServiceReference(refstr), -1, 0)
				if act_event is None:
					return "%s - " % name
				else:
					return "%s - %s" % (name, act_event.getEventName())
			elif self.type != self.NAME_ONLY and config.usage.show_infobar_channel_number.value and hasattr(self.source, "serviceref") and self.source.serviceref and '0:0:0:0:0:0:0:0:0' not in self.source.serviceref.toString():
				numservice = self.source.serviceref
				num = numservice and numservice.getChannelNum() or None
				if num is not None:
					return str(num) + '   ' + name
				else:
					return name
			else:
				return name
		elif self.type == self.PROVIDER:
			return info.getInfoString(iServiceInformation.sProvider)
		elif self.type == self.REFERENCE or self.type == self.EDITREFERENCE and hasattr(self.source, "editmode") and self.source.editmode:
			if not service:
				refstr = info.getInfoString(iServiceInformation.sServiceref)
				path = refstr and eServiceReference(refstr).getPath()
				if path and fileExists("%s.meta" % path):
					fd = open("%s.meta" % path, "r")
					refstr = fd.readline().strip()
					fd.close()
				return refstr
			nref = resolveAlternate(service)
			if nref:
				service = nref
			return service.toString()
		elif self.type == self.TRANSPONDER:
			if service:
				nref = resolveAlternate(service)
				if nref:
					service = nref
					info = eServiceCenter.getInstance().info(service)
				transponder_info = info.getInfoObject(service, iServiceInformation.sTransponderData)
			else:
				transponder_info = info.getInfoObject(iServiceInformation.sTransponderData)
			if "InRootOnly" in self.mode and not self.rootBouquet():
				return ""
			if "NoRoot" in self.mode and self.rootBouquet():
				return ""
			if transponder_info:
				self.t_info = ConvertToHumanReadable(transponder_info)
				if self.system() == None: # catch driver bug
					return ""
				if "DVB-T" in self.system():
					return	self.dvb_t()
				elif "DVB-C" in self.system():
					return self.dvb_c()
				return 	self.dvb_s()
			if service:
				result = service.toString()
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
		return "%s %s %s %s %s %s %s" % (self.orb_pos(), self.system(), self.freq(), self.polar(), self.s_rate(), self.fec(), self.mod())
	def dvb_t(self):
		return "%s %s %s/%s" % (self.system(), self.ch_number(), self.freq(), self.bandwidth())
	def dvb_c(self):
		return "%s %s %s %s %s" % (self.system(), self.freq(), self.s_rate(), self.fec(), self.mod())
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
