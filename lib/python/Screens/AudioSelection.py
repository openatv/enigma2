from Screen import Screen
from Screens.Setup import getConfigMenuItem, Setup
from Components.ServiceEventTracker import ServiceEventTracker
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigListScreen
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.config import config, ConfigSubsection, getConfigListEntry, ConfigNothing, ConfigSelection, ConfigOnOff
from Components.Label import Label
from Components.MultiContent import MultiContentEntryText
from Components.Sources.List import List
from Components.Sources.Boolean import Boolean
from Components.SystemInfo import SystemInfo


from enigma import iPlayableService, eTimer

from Tools.ISO639 import LanguageCodes
from Tools.BoundFunction import boundFunction
FOCUS_CONFIG, FOCUS_STREAMS = range(2)
[PAGE_AUDIO, PAGE_SUBTITLES] = ["audio", "subtitles"]

class AudioSelection(Screen, ConfigListScreen):
	def __init__(self, session, infobar=None, page=PAGE_AUDIO):
		Screen.__init__(self, session)

		self["streams"] = List([])
		self["key_red"] = Boolean(False)
		self["key_green"] = Boolean(False)
		self["key_yellow"] = Boolean(True)
		self["key_blue"] = Boolean(False)
		
		ConfigListScreen.__init__(self, [])
		self.infobar = infobar or self.session.infobar

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evUpdatedInfo: self.__updatedInfo
			})
		self.cached_subtitle_checked = False
		self.__selected_subtitle = None

		self["actions"] = NumberActionMap(["ColorActions", "SetupActions", "DirectionActions", "MenuActions"],
		{
			"red": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"blue": self.keyBlue,
			"ok": self.keyOk,
			"cancel": self.cancel,
			"up": self.keyUp,
			"down": self.keyDown,
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

		self["key_blue"].setBoolean(False)

		service = self.session.nav.getCurrentService()
		self.audioTracks = audio = service and service.audioTracks()
		n = audio and audio.getNumberOfTracks() or 0
		
		subtitlelist = self.getSubtitleList()

		if self.settings.menupage.getValue() == PAGE_AUDIO:
			self.setTitle(_("Select audio track"))
			service = self.session.nav.getCurrentService()
			self.audioTracks = audio = service and service.audioTracks()
			n = audio and audio.getNumberOfTracks() or 0
			if SystemInfo["CanDownmixAC3"]:
				self.settings.downmix = ConfigOnOff(default=config.av.downmix_ac3.value)
				self.settings.downmix.addNotifier(self.changeAC3Downmix, initial_call = False)
				conflist.append(getConfigListEntry(_("AC3/DTS downmix"), self.settings.downmix))
				self["key_red"].setBoolean(True)

			if n > 0:
				self.audioChannel = service.audioChannel()
				if self.audioChannel:
					choicelist = [("0",_("left")), ("1",_("stereo")), ("2", _("right"))]
					self.settings.channelmode = ConfigSelection(choices = choicelist, default = str(self.audioChannel.getCurrentChannel()))
					self.settings.channelmode.addNotifier(self.changeMode, initial_call = False)
					conflist.append(getConfigListEntry(_("Channel"), self.settings.channelmode))
					self["key_green"].setBoolean(True)
				else:
					conflist.append(('',))
					self["key_green"].setBoolean(False)
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
							language += LanguageCodes[lang][0]
						elif lang == "und":
							""
						else:
							language += lang
						cnt += 1

					streams.append((x, "", number, description, language, selected))

			else:
				streams = []
				conflist.append(('',))
				self["key_green"].setBoolean(False)

			if subtitlelist:
				self["key_yellow"].setBoolean(True)
				conflist.append(getConfigListEntry(_("To subtitle selection"), self.settings.menupage))
			else:
				self["key_yellow"].setBoolean(False)
				conflist.append(('',))

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
					self["key_blue"].setBoolean(True)
					conflist.append(getConfigListEntry(Plugins[0][0], ConfigNothing()))
					self.plugincallfunc = Plugins[0][1]
				if len(Plugins) > 1:
					print "plugin(s) installed but not displayed in the dialog box:", Plugins[1:]

		elif self.settings.menupage.getValue() == PAGE_SUBTITLES:
	
			self.setTitle(_("Subtitle selection"))
			conflist.append(('',))
			conflist.append(('',))
			self["key_red"].setBoolean(False)
			self["key_green"].setBoolean(False)

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
							language = LanguageCodes[x[4]][0]
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

			conflist.append(getConfigListEntry(_("To audio selection"), self.settings.menupage))

			if self.infobar.selected_subtitle and self.infobar.selected_subtitle != (0,0,0,0)  and not ".DVDPlayer'>" in `self.infobar`:
				self["key_blue"].setBoolean(True)
				conflist.append(getConfigListEntry(_("Subtitle Quickmenu"), ConfigNothing()))

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
			if self.selectedSubtitle == (0,0,0,0):
				self.selectedSubtitle = None
			elif self.selectedSubtitle and not self.selectedSubtitle[:4] in (x[:4] for x in subtitlelist):
				subtitlelist.append(self.selectedSubtitle)
		return subtitlelist

	def subtitlesEnabled(self):
		try:
			return self.infobar.subtitles_enabled
		except: 
			return False

	def enableSubtitle(self, subtitles):
		if self.infobar.selected_subtitle != subtitles:
			self.infobar.subtitles_enabled = False
			self.infobar.selected_subtitle = subtitles
			if subtitles:
				self.infobar.subtitles_enabled = True
				self.infobar.selected_subtitle = subtitles

	def changeAC3Downmix(self, downmix):
		if downmix.getValue() == True:
			config.av.downmix_ac3.value = True
		else:
			config.av.downmix_ac3.value = False
		config.av.downmix_ac3.save()

	def changeMode(self, mode):
		if mode is not None and self.audioChannel:
			self.audioChannel.selectChannel(int(mode.getValue()))

	def changeAudio(self, audio):
		track = int(audio)
		if isinstance(track, int):
			if self.session.nav.getCurrentService().audioTracks().getNumberOfTracks() > track:
				self.audioTracks.selectTrack(track)

	def keyLeft(self):
		if self.focus == FOCUS_CONFIG:
			ConfigListScreen.keyLeft(self)
		elif self.focus == FOCUS_STREAMS:
			self["streams"].setIndex(0)

	def keyRight(self, config = False):
		if config or self.focus == FOCUS_CONFIG:
			if self["config"].getCurrentIndex() < 3:
				ConfigListScreen.keyRight(self)
			elif self["config"].getCurrentIndex() == 3:
				if self.settings.menupage.getValue() == PAGE_AUDIO and hasattr(self, "plugincallfunc"):
					self.plugincallfunc()
				elif self.settings.menupage.getValue() == PAGE_SUBTITLES and self.infobar.selected_subtitle and self.infobar.selected_subtitle != (0,0,0,0):
					self.session.open(QuickSubtitlesConfigMenu, self.infobar)
		if self.focus == FOCUS_STREAMS and self["streams"].count() and config == False:
			self["streams"].setIndex(self["streams"].count()-1)

	def keyRed(self):
		if self["key_red"].getBoolean():
			self.colorkey(0)

	def keyGreen(self):
		if self["key_green"].getBoolean():
			self.colorkey(1)

	def keyYellow(self):
		if self["key_yellow"].getBoolean():
			self.colorkey(2)

	def keyBlue(self):
		if self["key_blue"].getBoolean():
			self.colorkey(3)

	def colorkey(self, idx):
		self["config"].setCurrentIndex(idx)
		self.keyRight(True)

	def keyUp(self):
		if self.focus == FOCUS_CONFIG:
			self["config"].instance.moveSelection(self["config"].instance.moveUp)
		elif self.focus == FOCUS_STREAMS:
			if self["streams"].getIndex() == 0:
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
				self["config"].instance.setSelectionEnable(False)
				self["streams"].style = "default"
				self.focus = FOCUS_STREAMS
		elif self.focus == FOCUS_STREAMS:
			self["streams"].selectNext()

	def keyNumberGlobal(self, number):
		if number <= len(self["streams"].list):
			self["streams"].setIndex(number-1)
			self.keyOk()

	def keyOk(self):
		if self.focus == FOCUS_STREAMS and self["streams"].list:
			cur = self["streams"].getCurrent()
			if self.settings.menupage.getValue() == PAGE_AUDIO and cur[0] is not None:
				self.changeAudio(cur[0])
				self.__updatedInfo()
			if self.settings.menupage.getValue() == PAGE_SUBTITLES and cur[0] is not None:
				if self.infobar.selected_subtitle == cur[0][:4]:
					self.enableSubtitle(None)
					selectedidx = self["streams"].getIndex()
					self.__updatedInfo()
					self["streams"].setIndex(selectedidx)
				else:
					self.enableSubtitle(cur[0][:4])
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
	skin = """
	<screen position="50,50" size="480,255" title="Subtitle settings" backgroundColor="#7f000000" flags="wfNoBorder">
		<widget name="config" position="5,5" size="470,225" font="Regular;18" zPosition="1" transparent="1" selectionPixmap="PLi-HD/buttons/sel.png" valign="center" />
		<widget name="videofps" position="5,230" size="470,20" backgroundColor="secondBG" transparent="1" zPosition="1" font="Regular;16" valign="center" halign="left" foregroundColor="blue"/>
	</screen>"""

	def __init__(self, session, infobar):
		Screen.__init__(self, session)
		self.skin = QuickSubtitlesConfigMenu.skin
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
				getConfigMenuItem("config.subtitles.pango_subtitles_yellow"),
				getConfigMenuItem("config.subtitles.subtitle_fontsize"),
				getConfigMenuItem("config.subtitles.subtitle_position"),
				getConfigMenuItem("config.subtitles.subtitle_alignment"),
				getConfigMenuItem("config.subtitles.subtitle_rewrap"),
				getConfigMenuItem("config.subtitles.subtitle_borderwidth"),
				getConfigMenuItem("config.subtitles.pango_subtitles_fps"),
			]
			self["videofps"].setText(_("Video: %s fps") % (self.getFps().rstrip(".000")))

		ConfigListScreen.__init__(self, menu, self.session, on_change = self.changedEntry)

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"cancel": self.finish,
			"ok": self.finish,
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

	def finish(self):
		self.close()
