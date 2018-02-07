from Components.Converter.Converter import Converter
from Components.Element import cached, ElementError
from enigma import iServiceInformation, eServiceReference
from ServiceReference import ServiceReference
from Tools.UnitConversions import UnitScaler

class MovieInfo(Converter, object):
	MOVIE_SHORT_DESCRIPTION = 0  # meta description when available.. when not .eit short description
	MOVIE_META_DESCRIPTION = 1  # just meta description when available
	MOVIE_REC_SERVICE_NAME = 2  # name of recording service
	MOVIE_REC_SERVICE_REF = 3  # referance of recording service
	MOVIE_REC_FILESIZE = 4  # filesize of recording
	MOVIE_FULL_DESCRIPTION = 5  # combination of short and long description when available

	KEYWORDS = {
		# Arguments...
		"FileSize": ("type", MOVIE_REC_FILESIZE),
		"FullDescription": ("type", MOVIE_FULL_DESCRIPTION),
		"MetaDescription": ("type", MOVIE_META_DESCRIPTION),
		"RecordServiceName": ("type", MOVIE_REC_SERVICE_NAME),
		"RecordServiceRef": ("type", MOVIE_REC_SERVICE_REF),
		"ShortDescription": ("type", MOVIE_SHORT_DESCRIPTION),
		# Options...
		"Separated": ("separator", "\n\n"),
		"NotSeparated": ("separator", "\n"),
		"Trimmed": ("trim", True),
		"NotTrimmed": ("trim", False)
	}

	def __init__(self, type):
		self.type = None
		self.separator = "\n"
		self.trim = False

		parse = ","
		type.replace(";", parse)  # Some builds use ";" as a separator, most use ",".
		args = [arg.strip() for arg in type.split(parse)]
		for arg in args:
			name, value = self.KEYWORDS.get(arg, ("Error", None))
			if name == "Error":
				print "[MovieInfo] ERROR: Unexpected / Invalid argument token '%s'!" % arg
			else:
				setattr(self, name, value)
		if ((name == "Error") or (type is None)):
			print "[MovieInfo] Valid arguments are: ShortDescription|MetaDescription|FullDescription|RecordServiceName|RecordServiceRef|FileSize."
			print "[MovieInfo] Valid options for descriptions are: Separated|NotSeparated|Trimmed|NotTrimmed."
		Converter.__init__(self, type)

	def trimText(self, text):
		if self.trim:
			return str(text).strip()
		else:
			return str(text)

	def formatDescription(self, description, extended):
		description = self.trimText(description)
		extended = self.trimText(extended)
		if description[0:20] == extended[0:20]:
			return extended
		if description and extended:
			description += self.separator
		return description + extended

	@cached
	def getText(self):
		service = self.source.service
		info = self.source.info
		event = self.source.event
		if info and service:
			if self.type == self.MOVIE_SHORT_DESCRIPTION:
				if (service.flags & eServiceReference.flagDirectory) == eServiceReference.flagDirectory:
					# Short description for Directory is the full path
					return service.getPath()
				return (
					info.getInfoString(service, iServiceInformation.sDescription)
					or (event and self.trimText(event.getShortDescription()))
					or service.getPath()
				)
			elif self.type == self.MOVIE_META_DESCRIPTION:
				return (
					(event and (self.trimText(event.getExtendedDescription()) or self.trimText(event.getShortDescription())))
					or info.getInfoString(service, iServiceInformation.sDescription)
					or service.getPath()
				)
			elif self.type == self.MOVIE_FULL_DESCRIPTION:
				return (
					(event and self.formatDescription(event.getShortDescription(), event.getExtendedDescription()))
					or info.getInfoString(service, iServiceInformation.sDescription)
					or service.getPath()
				)

			elif self.type == self.MOVIE_REC_SERVICE_NAME:
				rec_ref_str = info.getInfoString(service, iServiceInformation.sServiceref)
				return ServiceReference(rec_ref_str).getServiceName()
			elif self.type == self.MOVIE_REC_SERVICE_REF:
				rec_ref_str = info.getInfoString(service, iServiceInformation.sServiceref)
				return str(ServiceReference(rec_ref_str))
			elif self.type == self.MOVIE_REC_FILESIZE:
				if (service.flags & eServiceReference.flagDirectory) == eServiceReference.flagDirectory:
					return _("Directory")
				filesize = info.getFileSize(service)
				if filesize:
					return _("%s %sB") % UnitScaler()(filesize)
		return ""

	text = property(getText)
