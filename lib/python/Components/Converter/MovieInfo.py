from Components.Converter.Converter import Converter
from Components.Element import cached
from enigma import iServiceInformation
from ServiceReference import ServiceReference

class MovieInfo(Converter, object):
	MOVIE_SHORT_DESCRIPTION = 0 # meta description when available.. when not .eit short description
	MOVIE_META_DESCRIPTION = 1 # just meta description when available
	MOVIE_REC_SERVICE_NAME = 2 # name of recording service

	def __init__(self, type):
		if type == "ShortDescription":
			self.type = self.MOVIE_SHORT_DESCRIPTION
		elif type == "MetaDescription":
			self.type = self.MOVIE_META_DESCRIPTION
		elif type == "RecordServiceName":
			self.type = self.MOVIE_REC_SERVICE_NAME
		else:
			raise str("'%s' is not <ShortDescription|MetaDescription|RecordServiceName> for MovieInfo converter" % type)
		Converter.__init__(self, type)

	@cached
	def getText(self):
		service = self.source.service
		info = self.source.info
		if info and service:
			if self.type == self.MOVIE_SHORT_DESCRIPTION:
				event = self.source.event
				if event:
					descr = info.getInfoString(service, iServiceInformation.sDescription)
					if descr == "":
						return event.getShortDescription()
					else:
						return descr
			elif self.type == self.MOVIE_META_DESCRIPTION:
				return info.getInfoString(service, iServiceInformation.sDescription)
			elif self.type == self.MOVIE_REC_SERVICE_NAME:
				rec_ref_str = info.getInfoString(service, iServiceInformation.sServiceref)
				return ServiceReference(rec_ref_str).getServiceName()
		return ""

	text = property(getText)
