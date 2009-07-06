from Components.Converter.Converter import Converter
from Components.Element import cached, ElementError
from enigma import iServiceInformation
from ServiceReference import ServiceReference

class MovieInfo(Converter, object):
	MOVIE_SHORT_DESCRIPTION = 0 # meta description when available.. when not .eit short description
	MOVIE_META_DESCRIPTION = 1 # just meta description when available
	MOVIE_REC_SERVICE_NAME = 2 # name of recording service
	MOVIE_REC_FILESIZE = 3 # filesize of recording

	def __init__(self, type):
		if type == "ShortDescription":
			self.type = self.MOVIE_SHORT_DESCRIPTION
		elif type == "MetaDescription":
			self.type = self.MOVIE_META_DESCRIPTION
		elif type == "RecordServiceName":
			self.type = self.MOVIE_REC_SERVICE_NAME
		elif type == "FileSize":
			self.type = self.MOVIE_REC_FILESIZE
		else:
			raise ElementError("'%s' is not <ShortDescription|MetaDescription|RecordServiceName|FileSize> for MovieInfo converter" % type)
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
			elif self.type == self.MOVIE_REC_FILESIZE:
				filesize = info.getInfoObject(service, iServiceInformation.sFileSize)
				if filesize is not None:
					return "%d MB" % (filesize / (1024*1024))
		return ""

	text = property(getText)
