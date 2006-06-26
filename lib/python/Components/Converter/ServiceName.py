from Components.Converter.Converter import Converter
from enigma import iServiceInformation

class ServiceName(Converter, object):
	NAME = 0
	PROVIDER = 1

	def __init__(self, type, *args, **kwargs):
		Converter.__init__(self)
		if type == "Provider":
			self.type = self.PROVIDER
		else:
			self.type = self.NAME

	def getServiceInfoValue(self, info, what):
		v = info.getInfo(what)
		if v != -2:
			return "N/A"
		return info.getInfoString(what)

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
