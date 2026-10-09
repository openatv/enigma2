from enigma import iPlayableService

from Components.Converter.Converter import Converter
from Components.Element import cached


class VServiceInfo(Converter):
	AUDIOTRACKS_AVAILABLE = 1
	SUBTITLES_AVAILABLE = 2

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.type, self.interesting_events = {
			"AudioTracksAvailable": (self.AUDIOTRACKS_AVAILABLE, (iPlayableService.evUpdatedInfo,)),
			"SubtitlesAvailable": (self.SUBTITLES_AVAILABLE, (iPlayableService.evUpdatedInfo,)),
		}[tokens]

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
			Converter.changed(self, what)

	@cached
	def getBoolean(self):
		result = False
		service = self.source.service
		info = service and service.info()
		if info:
			match self.type:
				case self.AUDIOTRACKS_AVAILABLE:
					audio = service.audioTracks()
					result = bool(audio and audio.getNumberOfTracks() > 1)
				case self.SUBTITLES_AVAILABLE:
					subtitle = service and service.subtitle()
					result = bool(subtitle and subtitle.getSubtitleList())
				case _:
					result = None
		return result

	boolean = property(getBoolean)

	def getServiceInfoString(self, info, what, convert=lambda x: f"{int(x)}"):
		value = info.getInfo(what)
		match value:
			case -1:
				result = "N/A"
			case -2:
				result = info.getInfoString(what)
			case _:
				result = convert(value)
		return result

	@cached
	def getText(self):  # FIXME What's this ?
		service = self.source.service
		info = service and service.info()
		return None if info else ""

	text = property(getText)

	@cached
	def getValue(self):  # FIXME What's this ?
		service = self.source.service
		info = service and service.info()
		return None if info else -1

	value = property(getValue)
