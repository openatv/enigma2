# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceReference
from ServiceReference import resolveAlternate
from Components.Element import cached

class ServiceName(Converter, object):
	NAME = 0
	PROVIDER = 1
	REFERENCE = 2
	EDITREFERENCE = 3
	NUMBER = 4

	def __init__(self, type):
		Converter.__init__(self, type)

		if type == "Provider":
			self.type = self.PROVIDER
		elif type == "Reference":
			self.type = self.REFERENCE
		elif type == "EditReference":
			self.type = self.EDITREFERENCE
		elif type == "Number":
			self.type = self.NUMBER
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
		elif self.type == self.NUMBER:
			if not ref:
				ref = eServiceReference(info.getInfoString(iServiceInformation.sServiceref))
			num = ref and ref.getChannelNum() or None
			if num is None:
				num = '---'
			else:
				num = str(num)
			return num

	text = property(getText)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart,):
			Converter.changed(self, what)
