from enigma import iPlayableService
from Components.Converter.Converter import Converter
from Components.Element import cached
from Poll import Poll

class VAudioInfo(Poll, Converter, object):
	GET_AUDIO_ICON = 0
	GET_AUDIO_CODEC = 1

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.type = type
		self.poll_interval = 1000
		self.poll_enabled = True
		self.lang_strings = ("ger", "german", "deu")
		self.codecs = {    "01_dolbydigitalplus" : ("digital+", "digitalplus", "ac3+", "e-ac-3"),
				   "02_dolbydigital": ("ac3", "ac-3", "dolbydigital"),
				   "03_mp3": ("mp3", ),
				   "04_wma": ("wma", ),
				   "05_flac": ("flac", ),
				   "06_mpeg": ("mpeg", ),
				   "07_lpcm": ("lpcm", ),
				   "08_dts-hd": ("dts-hd", ),
				   "09_dts": ("dts", ),
				   "10_pcm": ("pcm", ),
				}
		self.codec_info = { "dolbydigitalplus" : ("51", "20", "71"),
				    "dolbydigital" : ("51", "20", "71"),
				    "wma" : ("8", "9"),
				  }
		self.type, self.interesting_events = {
				"AudioIcon": (self.GET_AUDIO_ICON, (iPlayableService.evUpdatedInfo,)),
				"AudioCodec": (self.GET_AUDIO_CODEC, (iPlayableService.evUpdatedInfo,)),
			}[type]

	def getAudio(self):
		service = self.source.service
		audio = service.audioTracks()
		if audio:
			self.current_track = audio.getCurrentTrack()
			self.number_of_tracks = audio.getNumberOfTracks()
			if self.number_of_tracks > 0 and self.current_track > -1:
				self.audio_info = audio.getTrackInfo(self.current_track)
				return True
		return False

	def getLanguage(self):
		languages = self.audio_info.getLanguage()
		for lang in self.lang_strings:
			if lang in languages:
				languages = "Deutsch"
				break
		languages = languages.replace("und ", "")
		return languages

	def getAudioCodec(self,info):
		description_str = _("unknown")
		if self.getAudio():
			languages = self.getLanguage()
			description = self.audio_info.getDescription();
			description_str = description.split(" ")
			if len(description_str) and description_str[0] in languages:
				return languages
			if description.lower() in languages.lower():
				languages = ""
			description_str = description + " " + languages
		return description_str

	def getAudioIcon(self,info):
		description_str = self.get_short(self.getAudioCodec(info).translate(None,' .').lower())
		return description_str

	def get_short(self, audioName):
		for return_codec, codecs in sorted(self.codecs.iteritems()):
			for codec in codecs:
				if codec in audioName:
					codec = return_codec.split('_')[1]
					if codec in self.codec_info:
						for ex_codec in self.codec_info[codec]:
							if ex_codec in audioName:
								codec += ex_codec
								break
					return codec
		return audioName

	@cached
	def getText(self):
		service = self.source.service
		if service:
			info = service and service.info()
			if info:
				if self.type == self.GET_AUDIO_CODEC:
					return self.getAudioCodec(info)
				if self.type == self.GET_AUDIO_ICON:
					return self.getAudioIcon(info)
		return _("invalid type")

	text = property(getText)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
			Converter.changed(self, what)
