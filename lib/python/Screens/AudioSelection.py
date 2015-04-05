from enigma import iPlayableService, eTimer

from Screen import Screen
from Screens.Setup import getConfigMenuItem, Setup
from Components.ServiceEventTracker import ServiceEventTracker
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, getConfigListEntry, ConfigNothing, ConfigSelection, ConfigOnOff
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Components.Sources.Boolean import Boolean
from Components.SystemInfo import SystemInfo
from Components.VolumeControl import VolumeControl
from Tools.ISO639 import LanguageCodes

FOCUS_CONFIG, FOCUS_STREAMS = range(2)
[PAGE_AUDIO, PAGE_SUBTITLES] = ["audio", "subtitles"]


class AudioSelection(Screen, ConfigListScreen):
	def __init__(self, session, infobar=None, page=PAGE_AUDIO):
		Screen.__init__(self, session)

		self["streams"] = List([], enableWrapAround=True)
		self["key_red"] = Boolean(False)
		self["key_green"] = Boolean(False)
		self["key_yellow"] = Boolean(True)
		self["key_blue"] = Boolean(False)
		self["key_left"] = Pixmap()
		self["key_right"] = Pixmap()
		self["switchdescription"] = Label(_("Switch between Audio-, Subtitlepage"))
		self["summary_description"] = StaticText("")

		ConfigListScreen.__init__(self, [])
		self.infobar = infobar or self.session.infobar

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evUpdatedInfo: self.__updatedInfo
			})
		self.cached_subtitle_checked = False
		self.__selected_subtitle = None

		self["actions"] = NumberActionMap(["ColorActions", "OkCancelActions", "DirectionActions", "MenuActions", "InfobarAudioSelectionActions", "InfobarSubtitleSelectionActions"],
		{
			"red": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"subtitleSelection": self.keyAudioSubtitle,
			"audioSelection": self.keyAudioSubtitle,
			"blue": self.keyBlue,
			"ok": self.keyOk,
			"cancel": self.cancel,
			"up": self.keyUp,
			"down": self.keyDown,
			"volumeUp": self.volumeUp,
			"volumeDown": self.volumeDown,
			"volumeMute": self.volumeMute,
			"menu": self.openAutoLanguageSetup,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
		}, -2)

		self.settings = ConfigSubsection()
		choicelist = [(PAGE_AUDIO,""), (PAGE_SUBTITLES,"")]
		self.settings.menupage = ConfigSelection(choices = choicelist, default=page)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __layoutFinished(self):
		self["config"].instance.setSelectionEnable(False)
		self.focus = FOCUS_STREAMS
		self.settings.menupage.addNotifier(self.fillList)

	def fillList(self, arg=None):
		streams = []
		conflist = []
		selectedidx = 0

		self["key_red"].setBoolean(False)
		self["key_green"].setBoolean(False)
		self["key_yellow"].setBoolean(False)
		self["key_blue"].setBoolean(False)

		service = self.session.nav.getCurrentService()
		self.audioTracks = audio = service and service.audioTracks()
		n = audio and audio.getNumberOfTracks() or 0

		subtitlelist = self.getSubtitleList()

		if self.settings.menupage.value == PAGE_AUDIO:
			self.setTitle(_("Select audio track"))
			service = self.session.nav.getCurrentService()
			self.audioTracks = audio = service and service.audioTracks()
			n = audio and audio.getNumberOfTracks() or 0
			if SystemInfo["CanDownmixAC3"]:
				self.settings.downmix_ac3 = ConfigOnOff(default=config.av.downmix_ac3.value)
				self.settings.downmix_ac3.addNotifier(self.changeAC3Downmix, initial_call = False)
				conflist.append(getConfigListEntry(_("Digital downmix"), self.settings.downmix_ac3, None))

			if SystemInfo["CanDownmixAAC"]:
				self.settings.downmix_aac = ConfigOnOff(default=config.av.downmix_aac.value)
				self.settings.downmix_aac.addNotifier(self.changeAACDownmix, initial_call = False)
				conflist.append(getConfigListEntry(_("AAC downmix"), self.settings.downmix_aac, None))

			if SystemInfo["CanAACTranscode"]:
				choice_list = [("off", _("off")), ("ac3", _("AC3")), ("dts", _("DTS"))]
				self.settings.transcodeaac = ConfigSelection(choices = choice_list, default = "off")
				self.settings.transcodeaac.addNotifier(self.setAACTranscode, initial_call = False)
				conflist.append(getConfigListEntry(_("AAC transcoding"), self.settings.transcodeaac, None))

			if SystemInfo["CanPcmMultichannel"]:
				self.settings.pcm_multichannel = ConfigOnOff(default=config.av.pcm_multichannel.value)
				self.settings.pcm_multichannel.addNotifier(self.changePCMMultichannel, initial_call = False)
				conflist.append(getConfigListEntry(_("PCM Multichannel"), self.settings.pcm_multichannel, None))

			if n > 0:
				self.audioChannel = service.audioChannel()
				if self.audioChannel:
					choicelist = [("0",_("left")), ("1",_("stereo")), ("2", _("right"))]
					self.settings.channelmode = ConfigSelection(choices = choicelist, default = str(self.audioChannel.getCurrentChannel()))
					self.settings.channelmode.addNotifier(self.changeMode, initial_call = False)
					conflist.append(getConfigListEntry(_("Channel"), self.settings.channelmode, None))
				selectedAudio = self.audioTracks.getCurrentTrack()
				for x in range(n):
					number = str(x + 1)
					i = audio.getTrackInfo(x)
					languages = i.getLanguage().split('/')
					description = i.getDescription() or ""
					selected = ""
					language = ""

					if selectedAudio == x:
						selected = "X"
						selectedidx = x

					cnt = 0
					for lang in languages:
						if cnt:
							language += ' / '
						if LanguageCodes.has_key(lang):
							language += _(LanguageCodes[lang][0])
						else:
							language += lang
						cnt += 1

					streams.append((x, "", number, description, language, selected))

			else:
				conflist.append(('',))

			if SystemInfo["Can3DSurround"]:
				choice_list = [("none", _("off")), ("hdmi", _("HDMI")), ("spdif", _("SPDIF")), ("dac", _("DAC"))]
				self.settings.surround_3d = ConfigSelection(choices = choice_list, default = config.av.surround_3d.value)
				self.settings.surround_3d.addNotifier(self.change3DSurround, initial_call = False)
				conflist.append(getConfigListEntry(_("3D Surround"), self.settings.surround_3d, None))

			if SystemInfo["Can3DSpeaker"] and config.av.surround_3d.value != "none":
				choice_list = [("center", _("center")), ("wide", _("wide")), ("extrawide", _("extra wide"))]
				self.settings.surround_3d_speaker = ConfigSelection(choices = choice_list, default = config.av.surround_3d_speaker.value)
				self.settings.surround_3d_speaker.addNotifier(self.change3DSurroundSpeaker, initial_call = False)
				conflist.append(getConfigListEntry(_("3D Surround Speaker Position"), self.settings.surround_3d_speaker, None))

			if SystemInfo["CanAutoVolume"]:
				choice_list = [("none", _("off")), ("hdmi", _("HDMI")), ("spdif", _("SPDIF")), ("dac", _("DAC"))]
				self.settings.autovolume = ConfigSelection(choices = choice_list, default = config.av.autovolume.value)
				self.settings.autovolume.addNotifier(self.changeAutoVolume, initial_call = False)
				conflist.append(getConfigListEntry(_("Auto Volume Level"), self.settings.autovolume, None))

			if SystemInfo["Canedidchecking"]:
				choice_list = [("00000001", _("on")), ("00000000", _("off"))]
				self.settings.bypass_edid_checking = ConfigSelection(choices = choice_list, default = config.av.bypass_edid_checking.value)
				self.settings.bypass_edid_checking.addNotifier(self.changeEDIDChecking, initial_call = False)
				conflist.append(getConfigListEntry(_("Bypass HDMI EDID Check"), self.settings.bypass_edid_checking, None))

			from Components.PluginComponent import plugins
			from Plugins.Plugin import PluginDescriptor

			if hasattr(self.infobar, "runPlugin"):
				class PluginCaller:
					def __init__(self, fnc, *args):
						self.fnc = fnc
						self.args = args
					def __call__(self, *args, **kwargs):
						self.fnc(*self.args)

				Plugins = [ (p.name, PluginCaller(self.infobar.runPlugin, p)) for p in plugins.getPlugins(where = PluginDescriptor.WHERE_AUDIOMENU) ]
				if len(Plugins):
					for x in Plugins:
						if x[0] != 'AudioEffect': # always make AudioEffect Blue button.
							conflist.append(getConfigListEntry(x[0], ConfigNothing(),x[1]))

		elif self.settings.menupage.value == PAGE_SUBTITLES:

			self.setTitle(_("Subtitle selection"))

			idx = 0

			for x in subtitlelist:
				number = str(x[1])
				description = "?"
				language = ""
				selected = ""

				if self.selectedSubtitle and x[:4] == self.selectedSubtitle[:4]:
					selected = "X"
					selectedidx = idx

				try:
					if x[4] != "und":
						if LanguageCodes.has_key(x[4]):
							language = _(LanguageCodes[x[4]][0])
						else:
							language = x[4]
				except:
					language = ""

				if x[0] == 0:
					description = "DVB"
					number = "%x" % (x[1])

				elif x[0] == 1:
					description = "teletext"
					number = "%x%02x" %(x[3] and x[3] or 8, x[2])

				elif x[0] == 2:
					types = ("unknown", "embedded", "SSA file", "ASS file",
							"SRT file", "VOB file", "PGS file")
					try:
						description = types[x[2]]
					except:
						description = _("unknown") + ": %s" % x[2]
					number = str(int(number) + 1)

				streams.append((x, "", number, description, language, selected))
				idx += 1

			if self.infobar.selected_subtitle and self.infobar.selected_subtitle != (0,0,0,0)  and not ".DVDPlayer'>" in `self.infobar`:
				conflist.append(getConfigListEntry(_("Subtitle Quickmenu"), ConfigNothing(), None))

		if len(conflist) > 0 and conflist[0][0]:
			self["key_red"].setBoolean(True)
		if len(conflist) > 1 and conflist[1][0]:
			self["key_green"].setBoolean(True)
		if len(conflist) > 2 and conflist[2][0]:
			self["key_yellow"].setBoolean(True)
		if len(conflist) > 3 and conflist[3][0]:
			self["key_blue"].setBoolean(True)

		self["config"].list = conflist
		self["config"].l.setList(conflist)

		self["streams"].list = streams
		self["streams"].setIndex(selectedidx)

	def __updatedInfo(self):
		self.fillList()

	def getSubtitleList(self):
		service = self.session.nav.getCurrentService()
		subtitle = service and service.subtitle()
		subtitlelist = subtitle and subtitle.getSubtitleList()
		self.selectedSubtitle = None
		if self.subtitlesEnabled():
			self.selectedSubtitle = self.infobar.selected_subtitle
			if self.selectedSubtitle and self.selectedSubtitle[:4] == (0,0,0,0):
				self.selectedSubtitle = None
			elif self.selectedSubtitle and not self.selectedSubtitle[:4] in (x[:4] for x in subtitlelist):
				subtitlelist.append(self.selectedSubtitle)
		return subtitlelist

	def subtitlesEnabled(self):
		try:
			return self.infobar.subtitle_window.shown
		except:
			return False

	def enableSubtitle(self, subtitle):
		if self.infobar.selected_subtitle != subtitle:
			self.infobar.enableSubtitle(subtitle)

	def change3DSurround(self, surround_3d):
		if surround_3d.value:
			config.av.surround_3d.value = surround_3d.value
		config.av.surround_3d.save()
		self.fillList()

	def change3DSurroundSpeaker(self, surround_3d_speaker):
		if surround_3d_speaker.value:
			config.av.surround_3d_speaker.value = surround_3d_speaker.value
		config.av.surround_3d_speaker.save()

	def changeAutoVolume(self, autovolume):
		if autovolume.value:
			config.av.autovolume.value = autovolume.value
		config.av.autovolume.save()

	def changeEDIDChecking(self, edidchecking):
		if edidchecking.value:
			config.av.bypass_edid_checking.value = edidchecking.value
		config.av.bypass_edid_checking.save()

	def changeAC3Downmix(self, downmix):
		if downmix.value:
			config.av.downmix_ac3.setValue(True)
			if SystemInfo["supportPcmMultichannel"]:
				config.av.pcm_multichannel.setValue(False)
		else:
			config.av.downmix_ac3.setValue(False)
		config.av.downmix_ac3.save()
		if SystemInfo["supportPcmMultichannel"]:
			config.av.pcm_multichannel.save()
		self.fillList()

	def changePCMMultichannel(self, multichan):
		if multichan.value:
			config.av.pcm_multichannel.setValue(True)
		else:
			config.av.pcm_multichannel.setValue(False)
		config.av.pcm_multichannel.save()
		self.fillList()

	def changeAACDownmix(self, downmix):
		if downmix.value:
			config.av.downmix_aac.setValue(True)
		else:
			config.av.downmix_aac.setValue(False)
		config.av.downmix_aac.save()

	def setAACTranscode(self, transcode):
		config.av.transcodeaac.setValue(transcode)
		config.av.transcodeaac.save()

	def changeMode(self, mode):
		if mode is not None and self.audioChannel:
			self.audioChannel.selectChannel(int(mode.value))

	def changeAudio(self, audio):
		track = int(audio)
		if isinstance(track, int):
			if self.session.nav.getCurrentService().audioTracks().getNumberOfTracks() > track:
				self.audioTracks.selectTrack(track)

	def keyLeft(self):
		if self.focus == FOCUS_CONFIG:
			ConfigListScreen.keyLeft(self)
		elif self.focus == FOCUS_STREAMS:
			self.keyAudioSubtitle()

	def keyRight(self, config = False):
		if config or self.focus == FOCUS_CONFIG:
			if self.settings.menupage.value == PAGE_AUDIO and self["config"].getCurrent()[2]:
				self["config"].getCurrent()[2]()
			elif self.settings.menupage.value == PAGE_SUBTITLES and self.infobar.selected_subtitle and self.infobar.selected_subtitle != (0,0,0,0):
				self.session.open(QuickSubtitlesConfigMenu, self.infobar)
			else:
				ConfigListScreen.keyRight(self)

		if self.focus == FOCUS_STREAMS and config == False:
			self.keyAudioSubtitle()

	def keyRed(self):
		if self["key_red"].getBoolean():
			self.colorkey(0)
		else:
			return 0

	def keyGreen(self):
		if self["key_green"].getBoolean():
			self.colorkey(1)
		else:
			return 0

	def keyYellow(self):
		if self["key_yellow"].getBoolean():
			self.colorkey(2)
		else:
			return 0

	def keyBlue(self):
		if self["key_blue"].getBoolean():
			self.colorkey(3)
		else:
			return 0

	def keyAudioSubtitle(self):
		if self.settings.menupage.value == PAGE_AUDIO:
			self.settings.menupage.setValue('subtitles')
		else:
			self.settings.menupage.setValue('audio')

	def colorkey(self, idx):
		self["config"].setCurrentIndex(idx)
		self.keyRight(True)

	def keyUp(self):
		if self.focus == FOCUS_CONFIG:
			self["config"].instance.moveSelection(self["config"].instance.moveUp)
		elif self.focus == FOCUS_STREAMS:
			if self["streams"].getIndex() == 0:
				self["switchdescription"].hide()
				self["key_left"].hide()
				self["key_right"].hide()
				self["config"].instance.setSelectionEnable(True)
				self["streams"].style = "notselected"
				self["config"].setCurrentIndex(len(self["config"].getList())-1)
				self.focus = FOCUS_CONFIG
			else:
				self["streams"].selectPrevious()

	def keyDown(self):
		if self.focus == FOCUS_CONFIG:
			if self["config"].getCurrentIndex() < len(self["config"].getList())-1:
				self["config"].instance.moveSelection(self["config"].instance.moveDown)
			else:
				self["switchdescription"].show()
				self["key_left"].show()
				self["key_right"].show()
				self["config"].instance.setSelectionEnable(False)
				self["streams"].style = "default"
				self.focus = FOCUS_STREAMS
		elif self.focus == FOCUS_STREAMS:
			self["streams"].selectNext()

	def volumeUp(self):
		VolumeControl.instance and VolumeControl.instance.volUp()

	def volumeDown(self):
		VolumeControl.instance and VolumeControl.instance.volDown()

	def volumeMute(self):
		VolumeControl.instance and VolumeControl.instance.volMute()

	def keyNumberGlobal(self, number):
		if number <= len(self["streams"].list):
			self["streams"].setIndex(number-1)
			self.keyOk()

	def keyOk(self):
		if self.focus == FOCUS_STREAMS and self["streams"].list:
			cur = self["streams"].getCurrent()
			if self.settings.menupage.value == PAGE_AUDIO and cur[0] is not None:
				self.changeAudio(cur[0])
				self.__updatedInfo()
			if self.settings.menupage.value == PAGE_SUBTITLES and cur[0] is not None:
				if self.infobar.selected_subtitle and self.infobar.selected_subtitle[:4] == cur[0][:4]:
					self.enableSubtitle(None)
					selectedidx = self["streams"].getIndex()
					self.__updatedInfo()
					self["streams"].setIndex(selectedidx)
				else:
					self.enableSubtitle(cur[0][:5])
					self.__updatedInfo()
			self.close(0)
		elif self.focus == FOCUS_CONFIG:
			self.keyRight()

	def openAutoLanguageSetup(self):
		self.session.open(Setup, "autolanguagesetup")

	def cancel(self):
		self.close(0)

class SubtitleSelection(AudioSelection):
	def __init__(self, session, infobar=None):
		AudioSelection.__init__(self, session, infobar, page=PAGE_SUBTITLES)
		self.skinName = ["AudioSelection"]

class QuickSubtitlesConfigMenu(ConfigListScreen, Screen):
	def __init__(self, session, infobar):
		Screen.__init__(self, session)
		self.infobar = infobar or self.session.infobar

		self.wait = eTimer()
		self.wait.timeout.get().append(self.resyncSubtitles)

		self["videofps"] = Label("")

		sub = self.infobar.selected_subtitle
		if sub[0] == 0:  # dvb
			menu = [
				getConfigMenuItem("config.subtitles.dvb_subtitles_yellow"),
				getConfigMenuItem("config.subtitles.dvb_subtitles_centered"),
				getConfigMenuItem("config.subtitles.dvb_subtitles_backtrans"),
				getConfigMenuItem("config.subtitles.dvb_subtitles_original_position"),
				getConfigMenuItem("config.subtitles.subtitle_position"),
				getConfigMenuItem("config.subtitles.subtitle_bad_timing_delay"),
				getConfigMenuItem("config.subtitles.subtitle_noPTSrecordingdelay"),
			]
		elif sub[0] == 1: # teletext
			menu = [
				getConfigMenuItem("config.subtitles.ttx_subtitle_colors"),
				getConfigMenuItem("config.subtitles.ttx_subtitle_original_position"),
				getConfigMenuItem("config.subtitles.subtitle_fontsize"),
				getConfigMenuItem("config.subtitles.subtitle_position"),
				getConfigMenuItem("config.subtitles.subtitle_rewrap"),
				getConfigMenuItem("config.subtitles.subtitle_borderwidth"),
				getConfigMenuItem("config.subtitles.subtitle_alignment"),
				getConfigMenuItem("config.subtitles.subtitle_bad_timing_delay"),
				getConfigMenuItem("config.subtitles.subtitle_noPTSrecordingdelay"),
			]
		else: 		# pango
			menu = [
				getConfigMenuItem("config.subtitles.pango_subtitles_delay"),
				getConfigMenuItem("config.subtitles.pango_subtitle_colors"),
				getConfigMenuItem("config.subtitles.subtitle_fontsize"),
				getConfigMenuItem("config.subtitles.subtitle_position"),
				getConfigMenuItem("config.subtitles.subtitle_alignment"),
				getConfigMenuItem("config.subtitles.subtitle_rewrap"),
				getConfigMenuItem("config.subtitles.pango_subtitle_removehi"),
				getConfigMenuItem("config.subtitles.subtitle_borderwidth"),
				getConfigMenuItem("config.subtitles.pango_subtitles_fps"),
			]
			self["videofps"].setText(_("Video: %s fps") % (self.getFps().rstrip(".000")))

		ConfigListScreen.__init__(self, menu, self.session, on_change = self.changedEntry)

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"cancel": self.cancel,
			"ok": self.ok,
		},-2)

	def changedEntry(self):
		if self["config"].getCurrent() in [getConfigMenuItem("config.subtitles.pango_subtitles_delay"),getConfigMenuItem("config.subtitles.pango_subtitles_fps")]:
			self.wait.start(500, True)

	def resyncSubtitles(self):
		self.infobar.setSeekState(self.infobar.SEEK_STATE_PAUSE)
		self.infobar.setSeekState(self.infobar.SEEK_STATE_PLAY)

	def getFps(self):
		from enigma import iServiceInformation
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if not info:
			return ""
		fps = info.getInfo(iServiceInformation.sFrameRate)
		if fps > 0:
			return "%6.3f" % (fps/1000.)
		return ""

	def cancel(self):
		self.close()

	def ok(self):
		config.subtitles.save()
		self.close()
