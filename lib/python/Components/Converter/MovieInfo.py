from os.path import basename, normpath
from enigma import iServiceInformation, eServiceReference

from Components.Converter.Converter import Converter
from Components.Element import cached, ElementError
from ServiceReference import ServiceReference


class MovieInfo(Converter):
	MOVIE_SHORT_DESCRIPTION = 0  # meta description when available.. when not .eit short description
	MOVIE_META_DESCRIPTION = 1  # just meta description when available
	MOVIE_REC_SERVICE_NAME = 2  # name of recording service
	MOVIE_REC_SERVICE_REF = 3  # referance of recording service
	MOVIE_REC_FILESIZE = 4  # filesize of recording
	MOVIE_NAME = 5  # recording name or directory name
	MOVIE_FULL_DESCRIPTION = 6  # full description of the movie

	def __init__(self, type):
		if type == "ShortDescription":
			self.type = self.MOVIE_SHORT_DESCRIPTION
		elif type == "MetaDescription":
			self.type = self.MOVIE_META_DESCRIPTION
		elif type == "FullDescription":
			self.type = self.MOVIE_FULL_DESCRIPTION
		elif type == "RecordServiceName":
			self.type = self.MOVIE_REC_SERVICE_NAME
		elif type == "FileSize":
			self.type = self.MOVIE_REC_FILESIZE
		elif type in ("RecordServiceRef", "Reference"):
			self.type = self.MOVIE_REC_SERVICE_REF
		elif type == "Name":
			self.type = self.MOVIE_NAME
		else:
			raise ElementError("'%s' is not <ShortDescription|MetaDescription|FullDescription|RecordServiceName|FileSize> for MovieInfo converter" % type)
		Converter.__init__(self, type)

	@cached
	def getText(self):

		def formatDescription(description, extended):
			if description[:20] == extended[:20]:
				return extended
			if description and extended:
				description = f"{description}\n"
			return f"{description}{extended}"

		service = self.source.service
		info = self.source.info
		event = self.source.event
		if info and service:
			isDirectory = (service.flags & eServiceReference.flagDirectory) == eServiceReference.flagDirectory
			if self.type == self.MOVIE_SHORT_DESCRIPTION:
				if isDirectory:
					# Short description for Directory is the full path
					return service.getPath()
				return (info.getInfoString(service, iServiceInformation.sDescription)
						or (event and event.getShortDescription())
						or service.getPath())
			elif self.type == self.MOVIE_META_DESCRIPTION:
				return ((event and (event.getExtendedDescription() or event.getShortDescription()))
						or info.getInfoString(service, iServiceInformation.sDescription)
						or service.getPath())
			elif self.type == self.MOVIE_FULL_DESCRIPTION:
				shortDesc = ""
				if event:
					shortDesc = formatDescription(event.getShortDescription(), event.getExtendedDescription())
				if not shortDesc:
					shortDesc = info.getInfoString(service, iServiceInformation.sDescription) or service.getPath()
				return shortDesc
			elif self.type == self.MOVIE_REC_SERVICE_NAME:
				rec_ref_str = info.getInfoString(service, iServiceInformation.sServiceref)
				return ServiceReference(rec_ref_str).getServiceName()
			elif self.type == self.MOVIE_NAME:
				if isDirectory:
					return basename(normpath(service.getPath()))
				return event and event.getEventName() or info and info.getName(service)
			elif self.type == self.MOVIE_REC_SERVICE_REF:
				rec_ref_str = info.getInfoString(service, iServiceInformation.sServiceref)
				return str(ServiceReference(rec_ref_str))
			elif self.type == self.MOVIE_REC_FILESIZE:
				if isDirectory:
					return _("Directory")
				filesize = info.getInfoObject(service, iServiceInformation.sFileSize)
				if filesize is not None:
					if filesize >= 100000 * 1024 * 1024:
						return _("%.0f GB") % (filesize / (1024.0 * 1024.0 * 1024.0))
					elif filesize >= 100000 * 1024:
						return _("%.2f GB") % (filesize / (1024.0 * 1024.0 * 1024.0))
					else:
						return _("%.0f MB") % (filesize / (1024.0 * 1024.0))
		return ""

	text = property(getText)
