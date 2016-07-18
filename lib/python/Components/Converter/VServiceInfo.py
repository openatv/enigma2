# -*- coding: utf-8 -*-

from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService
from Components.Element import cached

class VServiceInfo(Converter, object):

	AUDIOTRACKS_AVAILABLE = 1
	SUBTITLES_AVAILABLE = 2

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type, self.interesting_events = {
				"AudioTracksAvailable": (self.AUDIOTRACKS_AVAILABLE, (iPlayableService.evUpdatedInfo,)),
				"SubtitlesAvailable": (self.SUBTITLES_AVAILABLE, (iPlayableService.evUpdatedInfo,)),
			}[type]

	def getServiceInfoString(self, info, what, convert = lambda x: "%d" % x):
		v = info.getInfo(what)
		if v == -1:
			return "N/A"
		if v == -2:
			return info.getInfoString(what)
		return convert(v)

	@cached
	def getBoolean(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return False
		if self.type == self.AUDIOTRACKS_AVAILABLE:
			audio = service.audioTracks()
			if audio:
				if audio.getNumberOfTracks() > 1:
					return True
			return False
		elif self.type == self.SUBTITLES_AVAILABLE:
			subtitle = service and service.subtitle()
			if subtitle:
				subtitle_list = subtitle.getSubtitleList()
				if subtitle_list:
					if len(subtitle_list) > 0:
						return True
			return False

	boolean = property(getBoolean)
	
	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return ""

			text = property(getText)

	@cached
	def getValue(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return -1

	value = property(getValue)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
			Converter.changed(self, what)
