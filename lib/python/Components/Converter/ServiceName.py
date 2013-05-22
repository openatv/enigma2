# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from Components.config import config
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr
from Components.Element import cached
from ServiceReference import resolveAlternate

class ServiceName(Converter, object):
	NAME = 0
	NAME_ONLY = 2
	PROVIDER = 3
	REFERENCE = 4
	EDITREFERENCE = 4

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "Provider":
			self.type = self.PROVIDER
		elif type == "Reference":
			self.type = self.REFERENCE
		elif type == "EditReference":
			self.type = self.EDITREFERENCE
		elif type == "NameOnly":
			self.type = self.NAME_ONLY
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
		if self.type == self.NAME or self.type == self.NAME_ONLY:
			if self.type != self.NAME_ONLY and config.usage.show_infobar_channel_number.getValue() and hasattr(self.source, "serviceref") and self.source.serviceref.toString().find('0:0:0:0:0:0:0:0:0') == -1:
				name = ref and info.getName(ref)
				numservice = self.source.serviceref
				num = numservice and numservice.getChannelNum() or None
				if name is None:
					name = info.getName()
				if num is not None:
					return str(num) + '   ' + name.replace('\xc2\x86', '').replace('\xc2\x87', '')
				else:
					return name.replace('\xc2\x86', '').replace('\xc2\x87', '')
			else:
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

	text = property(getText)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart,):
			Converter.changed(self, what)
