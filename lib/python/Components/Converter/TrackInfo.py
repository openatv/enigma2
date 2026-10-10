from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached
from Tools.Directories import isPluginInstalled
from Tools.ISO639 import LanguageCodes


class TrackInfo(Poll, Converter):
	AUDIO = 0
	SUBTITLE = 1
	AUDIO_CODEC = 2
	AUDIO_LANG = 3
	SUBTITLE_TYPE = 4
	SUBTITLE_LANG = 5

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		Poll.__init__(self)
		self.poll_interval = 1500
		self.poll_enabled = True
		self.type = {
			"Audio": self.AUDIO,
			"AudioCodec": self.AUDIO_CODEC,
			"AudioLang": self.AUDIO_LANG,
			"Subtitle": self.SUBTITLE,
			"SubtitleLang": self.SUBTITLE_LANG,
			"SubtitleType": self.SUBTITLE_TYPE
		}.get(tokens, self.AUDIO)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] == self.type:
			Converter.changed(self, what)

	@cached
	def getText(self):
		text = ""
		service = self.source.service
		match self.type:
			case self.AUDIO | self.AUDIO_CODEC | self.AUDIO_LANG:
				audio = service and service.audioTracks()
				if audio:
					try:
						trackInfo = audio.getTrackInfo(audio.getCurrentTrack())
						description = trackInfo.getDescription().replace(" audio", "") or ""
						language = " / ".join(_(LanguageCodes[x][0]) if x in LanguageCodes else x for x in trackInfo.getLanguage().split("/")) or _("Unknown")
						match self.type:
							case self.AUDIO:
								text = f"{description} | {language}"
							case self.AUDIO_CODEC:
								text = description
							case _:
								text = language
					except Exception:
						pass
			case self.SUBTITLE | self.SUBTITLE_LANG | self.SUBTITLE_TYPE:
				from Screens.InfoBar import InfoBar, MoviePlayer  # Prevent circular import.
				text = _("None")
				subtitle = service and service.subtitle()
				selectedSubtitle = None
				externalSubtitle = None
				enabled = False
				for player in (MoviePlayer.instance, InfoBar.instance):
					if player and not selectedSubtitle:
						selectedSubtitle = player.selected_subtitle
						enabled = player.subtitle_window.shown
				if not selectedSubtitle:  # For Kodi and SubsSupport.
					try:
						from Plugins.Extensions.Kodi.plugin import KodiVideoPlayer
						kodi = KodiVideoPlayer.instance
					except ImportError:
						kodi = None
					if kodi and isPluginInstalled("SubsSupport"):
						if kodi.embeddedEnabled:
							selectedSubtitle = kodi.selected_subtitle
							enabled = kodi.subtitle_window.shown
						else:
							externalSubtitle = kodi.getSubsPath()
				if externalSubtitle:
					match self.type:
						case self.SUBTITLE:
							text = f"{_('External')} | {externalSubtitle}"
						case self.SUBTITLE_TYPE:
							text = _("External")
						case _:
							text = externalSubtitle
				elif selectedSubtitle and enabled:
					for subtitleEntry in (subtitle and subtitle.getSubtitleList()) or ():
						if subtitleEntry[:4] == selectedSubtitle[:4]:
							language = _("Unknown")
							try:
								if subtitleEntry[4] != "und":
									language = _(LanguageCodes[subtitleEntry[4]][0]) if subtitleEntry[4] in LanguageCodes else subtitleEntry[4]
							except Exception:
								pass
							match selectedSubtitle[0]:
								case 0:
									description = "DVB"
								case 1:
									description = _("teletext")
								case 2:
									types = (_("unknown"), _("embedded"), _("SSA file"), _("ASS file"), _("SRT file"), _("VOB file"), _("PGS file"), "WebVTT")
									try:
										description = types[subtitleEntry[2]]
									except Exception:
										description = f"{_('unknown')}: {subtitleEntry[2]}"
								case 3:
									description = "PGS"
								case _:
									description = _("unknown")
							match self.type:
								case self.SUBTITLE:
									text = f"{description} | {language}"
								case self.SUBTITLE_TYPE:
									text = description
								case _:
									text = language
							break
		return text

	text = property(getText)
