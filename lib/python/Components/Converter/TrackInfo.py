from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Converter.Poll import Poll
from Tools.ISO639 import LanguageCodes
from Tools.Directories import isPluginInstalled


class TrackInfo(Poll, Converter):
	AUDIO = 0
	SUBTITLE = 1
	AUDIO_CODEC = 2
	AUDIO_LANG = 3
	SUBTITLE_TYPE = 4
	SUBTITLE_LANG = 5

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.poll_interval = 1500
		self.poll_enabled = True

		if type == "Audio":
			self.type = self.AUDIO
		elif type == "Subtitle":
			self.type = self.SUBTITLE
		elif type == "AudioCodec":
			self.type = self.AUDIO_CODEC
		elif type == "AudioLang":
			self.type = self.AUDIO_LANG
		elif type == "SubtitleType":
			self.type = self.AUDIO_LANG
		elif type == "SubtitleLang":
			self.type = self.AUDIO_LANG
		else:
			self.type = self.AUDIO

	@cached
	def getText(self):
		service = self.source.service
		if self.type == self.AUDIO or self.type == self.AUDIO_CODEC or self.type == self.AUDIO_LANG:
			audio = service and service.audioTracks()
			if audio:
				try:
					selectedAudio = audio.getCurrentTrack()
					i = audio.getTrackInfo(selectedAudio)
					languages = i.getLanguage().split('/')
					description = i.getDescription().replace(" audio", "") or ""
					cnt = 0
					language = ''
					for lang in languages:
						if cnt:
							language += ' / '
						if lang in LanguageCodes:
							language += _(LanguageCodes[lang][0])
						else:
							language += lang
						cnt += 1
					if language == '':
						language = _("Unknown")
					if self.type == self.AUDIO:
						return description + ' | ' + language
					elif self.type == self.AUDIO_CODEC:
						return description
					else:
						return language
				except:
					pass
			return ""
		elif self.type == self.SUBTITLE or self.type == self.SUBTITLE_TYPE or self.type == self.SUBTITLE_LANG:
			subtitle = service and service.subtitle()
			selectedSubtitle = None
			enabled = False
			import Screens.InfoBar
			######## MoviePlayer
			movieplayer = Screens.InfoBar.MoviePlayer.instance
			if movieplayer:
				selectedSubtitle = movieplayer.selected_subtitle
				enabled = movieplayer.subtitle_window.shown
			else:
				selectedSubtitle = None
				enabled = False
			######## Infobar
			if not selectedSubtitle:
				InfoBar = Screens.InfoBar.InfoBar.instance
				if InfoBar:
					selectedSubtitle = InfoBar.selected_subtitle
					enabled = InfoBar.subtitle_window.shown
				else:
					selectedSubtitle = None
					enabled = False
			######### for kodi & subssupport
			if not selectedSubtitle:
				try:
					from Plugins.Extensions.Kodi.plugin import KodiVideoPlayer
					kodi = KodiVideoPlayer.instance
				except:
					kodi = None
				if kodi and isPluginInstalled("SubsSupport"):
					if kodi.embeddedEnabled:
						selectedSubtitle = kodi.selected_subtitle
						enabled = kodi.subtitle_window.shown
					else:
						selectedSubtitle = kodi.getSubsPath()
						if selectedSubtitle:
							if self.type == self.SUBTITLE:
								return _("External") + " | " + selectedSubtitle
							elif self.type == self.SUBTITLE_TYPE:
								return _("External")
							else:
								return selectedSubtitle
			##############################
			if selectedSubtitle and enabled:
				subtitlelist = subtitle and subtitle.getSubtitleList()
				for x in subtitlelist:

					if x[:4] == selectedSubtitle[:4]:
						language = _("Unknown")
						try:
							if x[4] != "und":
								if x[4] in LanguageCodes:
									language = _(LanguageCodes[x[4]][0])
								else:
									language = x[4]
						except:
							pass

						if selectedSubtitle[0] == 0:
							description = "DVB"

						elif selectedSubtitle[0] == 1:
							description = _("teletext")

						elif selectedSubtitle[0] == 2:
							types = (_("unknown"), _("embedded"), _("SSA file"), _("ASS file"),
								_("SRT file"), _("VOB file"), _("PGS file"))
							try:
								description = types[x[2]]
							except:
								description = _("unknown") + ": %s" % x[2]
						if self.type == self.SUBTITLE:
							return description + ' | ' + language
						elif self.type == self.SUBTITLE_TYPE:
							return description
						else:
							return language
			return _("None")

	text = property(getText)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] == self.type:
			Converter.changed(self, what)
