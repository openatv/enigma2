from os.path import basename, normpath

from enigma import eServiceReference, iServiceInformation

from Components.Converter.Converter import Converter
from Components.Element import ElementError, cached
from ServiceReference import ServiceReference


class MovieInfo(Converter):
	MOVIE_SHORT_DESCRIPTION = 0  # Meta description when available, otherwise the .eit short description.
	MOVIE_META_DESCRIPTION = 1  # Just the meta description when available.
	MOVIE_REC_SERVICE_NAME = 2  # Name of the recording service.
	MOVIE_REC_SERVICE_REF = 3  # Reference of the recording service.
	MOVIE_REC_FILESIZE = 4  # File size of the recording.
	MOVIE_NAME = 5  # Recording name or directory name.
	MOVIE_FULL_DESCRIPTION = 6  # Full description of the movie.

	def __init__(self, tokens):
		self.type = {
			"FileSize": self.MOVIE_REC_FILESIZE,
			"FullDescription": self.MOVIE_FULL_DESCRIPTION,
			"MetaDescription": self.MOVIE_META_DESCRIPTION,
			"Name": self.MOVIE_NAME,
			"RecordServiceName": self.MOVIE_REC_SERVICE_NAME,
			"RecordServiceRef": self.MOVIE_REC_SERVICE_REF,
			"Reference": self.MOVIE_REC_SERVICE_REF,
			"ShortDescription": self.MOVIE_SHORT_DESCRIPTION
		}.get(tokens)
		if self.type is None:
			raise ElementError(f"'{tokens}' is not <ShortDescription|MetaDescription|FullDescription|RecordServiceName|FileSize> for MovieInfo converter")
		Converter.__init__(self, tokens)

	@cached
	def getText(self):
		def formatDescription(description, extended):
			if description[:20] == extended[:20]:
				result = extended
			elif description and extended:
				result = f"{description}\n{extended}"
			else:
				result = f"{description}{extended}"
			return result

		text = ""
		service = self.source.service
		info = self.source.info
		event = self.source.event
		if info and service:
			isDirectory = (service.flags & eServiceReference.flagDirectory) == eServiceReference.flagDirectory
			match self.type:
				case self.MOVIE_FULL_DESCRIPTION:
					shortDesc = formatDescription(event.getShortDescription(), event.getExtendedDescription()) if event else ""
					if not shortDesc:
						shortDesc = info.getInfoString(service, iServiceInformation.sDescription)
						extendedDesc = info.getInfoString(service, iServiceInformation.sExtendedDescription)
						if shortDesc or extendedDesc:
							shortDesc = formatDescription(shortDesc, extendedDesc)
					text = shortDesc or service.getPath()
				case self.MOVIE_META_DESCRIPTION:
					text = ((event and (event.getExtendedDescription() or event.getShortDescription()))
						or info.getInfoString(service, iServiceInformation.sDescription)
						or service.getPath())
				case self.MOVIE_NAME:
					text = basename(normpath(service.getPath())) if isDirectory else event and event.getEventName() or info and info.getName(service)
				case self.MOVIE_REC_FILESIZE:
					if isDirectory:
						text = _("Directory")
					else:
						fileSize = info.getInfoObject(service, iServiceInformation.sFileSize)
						if fileSize is not None:
							if fileSize >= 100000 * 1024 * 1024:
								text = _("%.0f GB") % (fileSize / (1024.0 * 1024.0 * 1024.0))
							elif fileSize >= 100000 * 1024:
								text = _("%.2f GB") % (fileSize / (1024.0 * 1024.0 * 1024.0))
							else:
								text = _("%.0f MB") % (fileSize / (1024.0 * 1024.0))
				case self.MOVIE_REC_SERVICE_NAME:
					text = ServiceReference(info.getInfoString(service, iServiceInformation.sServiceref)).getServiceName()
				case self.MOVIE_REC_SERVICE_REF:
					text = str(ServiceReference(info.getInfoString(service, iServiceInformation.sServiceref)))
				case self.MOVIE_SHORT_DESCRIPTION:
					if isDirectory:  # Short description for a directory is the full path.
						text = service.getPath()
					else:
						text = (info.getInfoString(service, iServiceInformation.sDescription)
							or (event and event.getShortDescription())
							or service.getPath())
		return text

	text = property(getText)
