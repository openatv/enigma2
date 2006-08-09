from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService
from Components.Element import cached

class ServiceName(Converter, object):
	NAME = 0
	PROVIDER = 1

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "Provider":
			self.type = self.PROVIDER
		else:
			self.type = self.NAME

	def getServiceInfoValue(self, info, what):
		v = info.getInfo(what)
		if v != -2:
			return "N/A"
		return info.getInfoString(what)

	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if info is None:
			return ""
		
		if self.type == self.NAME:
			return info.getName()
		elif self.type == self.PROVIDER:
			return self.getServiceInfoValue(info, iServiceInformation.sProvider)

	text = property(getText)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in [iPlayableService.evStart]:
			Converter.changed(self, what)
