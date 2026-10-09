from enigma import iPlayableService

from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached


class VAudioInfo(Poll, Converter):
	GET_AUDIO_ICON = 0
	GET_AUDIO_CODEC = 1

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		Poll.__init__(self)
		self.poll_interval = 1000
		self.poll_enabled = True
		self.lang_strings = ("ger", "german", "deu")
		self.codecs = {
			"01_dolbydigitalplus": ("ac3+", "digital+", "digitalplus",),
			"02_dolbydigital": ("ac3", "dolbydigital",),
			"03_mp3": ("mp3",),
			"04_wma": ("wma",),
			"05_flac": ("flac",),
			"06_mpeg": ("mpeg",),
			"07_lpcm": ("lpcm",),
			"08_dts-hd": ("dts-hd",),
			"09_dts": ("dts",),
			"10_pcm": ("pcm",),
			"11_aac": ("aac",),
			"12_he-aac": ("he-aac",),
			"13_truehd": ("truehd",),
			"14_aacplus": ("aac+",),
			"15_ipcm": ("ipcm",),
			"16_wma-pro": ("wma pro",),
			"17_vorbis": ("vorbis",),
			"18_opus": ("opus",),
			"19_amr": ("amr",),
			"20_mp2": ("mp2",),
		}
		self.codec_info = {
			"dolbydigitalplus": ("51", "20", "71"),
			"dolbydigital": ("51", "20", "71"),
			"wma": ("8", "9"),
		}
		self.type, self.interesting_events = {
			"AudioCodec": (self.GET_AUDIO_CODEC, (iPlayableService.evUpdatedInfo,)),
			"AudioIcon": (self.GET_AUDIO_ICON, (iPlayableService.evUpdatedInfo,)),
		}[tokens]

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
			Converter.changed(self, what)

	def get_short(self, audioName):
		result = audioName
		for returnCodec, codecs in sorted(self.codecs.items()):
			if any(x in audioName for x in codecs):
				result = returnCodec.split("_")[1]
				extension = next((x for x in self.codec_info.get(result, ()) if x in audioName), "")
				result = f"{result}{extension}"
				break
		return result

	def getAudio(self):
		result = False
		audio = self.source.service.audioTracks()
		if audio:
			self.current_track = audio.getCurrentTrack()
			self.number_of_tracks = audio.getNumberOfTracks()
			if self.number_of_tracks > 0 and self.current_track > -1:
				self.audio_info = audio.getTrackInfo(self.current_track)
				result = True
		return result

	def getAudioCodec(self, info):
		result = _("unknown")
		if self.getAudio():
			languages = self.getLanguage()
			description = self.audio_info.getDescription() or ""
			if description.split(" ")[0] in languages:
				result = languages
			else:
				if description.lower() in languages.lower():
					languages = ""
				result = f"{description} {languages}"
		return result

	def getAudioIcon(self, info):
		return self.get_short(self.getAudioCodec(info).translate(str.maketrans("", "", " .")).lower())

	def getLanguage(self):
		languages = self.audio_info.getLanguage()
		if any(x in languages for x in self.lang_strings):
			languages = "Deutsch"
		return languages.replace("und ", "")

	@cached
	def getText(self):
		text = _("Invalid type")
		service = self.source.service
		info = service and service.info()
		if info:
			match self.type:
				case self.GET_AUDIO_CODEC:
					text = self.getAudioCodec(info)
				case self.GET_AUDIO_ICON:
					text = self.getAudioIcon(info)
		return text

	text = property(getText)
