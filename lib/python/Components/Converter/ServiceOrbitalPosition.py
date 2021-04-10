# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceCenter
from ServiceReference import resolveAlternate

from Components.Element import cached

class ServiceOrbitalPosition(Converter, object):
	FULL = 0
	SHORT = 1

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "Short":
			self.type = self.SHORT
		else:
			self.type = self.FULL

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
			transponder_info = info.getInfoObject(ref, iServiceInformation.sTransponderData)
		else:
			transponder_info = info.getInfoObject(iServiceInformation.sTransponderData)

		if transponder_info:
			tunerType = transponder_info["tuner_type"]
			if tunerType == "DVB-S":
				pos = int(transponder_info["orbital_position"])
				direction = 'E'
				if pos > 1800:
					pos = 3600 - pos
					direction = 'W'
				if self.type == self.SHORT:
					return "%d.%d%s" % (pos / 10, pos % 10, direction)
				else:
					return "%d.%d° %s" % (pos / 10, pos % 10, direction)
			return tunerType
		if ref:
			refString = ref.toString().lower()
			if "%3a//" in refString:
				return _("Stream")
			if refString.startswith("1:134:"):
				return _("Alternative")
		return ""

	text = property(getText)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in [iPlayableService.evStart]:
			Converter.changed(self, what)
