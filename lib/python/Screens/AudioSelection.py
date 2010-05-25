from Screen import Screen
from Components.ServiceEventTracker import ServiceEventTracker
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.config import config, ConfigSubsection, getConfigListEntry, ConfigNothing, ConfigSelection, ConfigOnOff
from Components.MultiContent import MultiContentEntryText
from Components.Sources.List import List
from Components.Sources.Boolean import Boolean
from Components.SystemInfo import SystemInfo

from enigma import iPlayableService

from Tools.ISO639 import LanguageCodes
from Tools.BoundFunction import boundFunction
FOCUS_CONFIG, FOCUS_STREAMS = range(2)

class AudioSelection(Screen, ConfigListScreen):
	def __init__(self, session, infobar=None):
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
        
		self["actions"] = ActionMap(["ColorActions", "SetupActions", "DirectionActions"],
		{
			"red": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"blue": self.keyBlue,
			"ok": self.keyOk,
			"cancel": self.cancel,
			"up": self.keyUp,
			"down": self.keyDown,
		}, -3)

		self.settings = ConfigSubsection()
		choicelist = [("audio",_("audio tracks")), ("subtitles",_("Subtitles"))]
		self.settings.menupage = ConfigSelection(choices = choicelist)
		self.settings.menupage.addNotifier(self.fillList)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __layoutFinished(self):
		self["config"].instance.setSelectionEnable(False)
		self.focus = FOCUS_STREAMS

	def fillList(self, arg=None):
		streams = []
		conflist = []
		selectedidx = 0
		
		service = self.session.nav.getCurrentService()
		self.audioTracks = audio = service and service.audioTracks()
		n = audio and audio.getNumberOfTracks() or 0
		
		if self.settings.menupage.getValue() == "audio":
			self.setTitle(_("Select audio track"))
			if SystemInfo["CanDownmixAC3"]:
				print "config.av.downmix_ac3.value=", config.av.downmix_ac3.value
				self.settings.downmix = ConfigOnOff(default=config.av.downmix_ac3.value)
				self.settings.downmix.addNotifier(self.changeAC3Downmix, initial_call = False)
				conflist.append(getConfigListEntry(_("AC3 downmix"), self.settings.downmix))
				self["key_red"] = Boolean(True)

			if n > 0:
				self.audioChannel = service.audioChannel()
				print "self.audioChannel.getCurrentChannel()", self.audioChannel.getCurrentChannel()
				choicelist = [("0",_("left")), ("1",_("stereo")), ("2", _("right"))]
				self.settings.channelmode = ConfigSelection(choices = choicelist, default = str(self.audioChannel.getCurrentChannel()))
				self.settings.channelmode.addNotifier(self.changeMode, initial_call = False)
				conflist.append(getConfigListEntry(_("Channel"), self.settings.channelmode))
				self["key_green"] = Boolean(True)
				
				selectedAudio = self.audioTracks.getCurrentTrack()
				print "selectedAudio:", selectedAudio

				for x in range(n):
					number = str(x)
					i = audio.getTrackInfo(x)
					languages = i.getLanguage().split('/')
					description = i.getDescription() or _("<unknown>")
					selected = ""
					language = ""

					if selectedAudio == x:
						selected = _("Running")
						selectedidx = x

					cnt = 0
					for lang in languages:
						if cnt:
							language += ' / '
						if LanguageCodes.has_key(lang):
							language += LanguageCodes[lang][0]
						elif lang == "und":
							_("<unknown>")
						else:
							language += lang
						cnt += 1

					streams.append((x, "", number, description, language, selected))

				#if hasattr(self, "runPlugin"):
					#class PluginCaller:
						#def __init__(self, fnc, *args):
							#self.fnc = fnc
							#self.args = args
						#def __call__(self, *args, **kwargs):
							#self.fnc(*self.args)

					#Plugins = [ (p.name, PluginCaller(self.runPlugin, p)) for p in plugins.getPlugins(where = PluginDescriptor.WHERE_AUDIOMENU) ]

					#for p in Plugins:
						#selection += 1
						#flist.append((p[0], "CALLFUNC", p[1]))
						#if availableKeys:
							#usedKeys.append(availableKeys[0])
							#del availableKeys[0]
						#else:
							#usedKeys.append("")
			else:
				streams = [(None, "", "", _("none"), "")]

		elif self.settings.menupage.getValue() == "subtitles":
			self.setTitle(_("Subtitle selection"))
			
			self.settings.dummy = ConfigNothing()
			conflist.append(getConfigListEntry("", self.settings.dummy))
			conflist.append(getConfigListEntry("", self.settings.dummy))

			if self.subtitlesEnabled():
				sel = self.infobar.selected_subtitle
			else:
				sel = None

			idx = 0
			
			subtitlelist = self.getSubtitleList()
			
			if len(subtitlelist):
				for x in subtitlelist:
					number = str(x[1])
					description = "?"
					language = _("<unknown>")
					selected = ""

					if sel and x[:4] == sel[:4]:
						selected = _("Running")
						selectedidx = idx
					
					if x[4] != "und":
						if LanguageCodes.has_key(x[4]):
							language = LanguageCodes[x[4]][0]
						else:
							language = x[4]

					if x[0] == 0:
						description = "DVB"
						number = "%x" % (x[1])

					elif x[0] == 1:
						description = "TTX"
						number = "%x%02x" % (x[3],x[2])
					
					elif x[0] == 2:
						types = (" UTF-8 text "," SSA / AAS "," .SRT file ")
						description = types[x[2]]

					streams.append((x, "", number, description, language, selected))
					idx += 1
			
			else:
				streams = [(None, "", "", _("none"), "")]

		conflist.append(getConfigListEntry(_("Menu"), self.settings.menupage))
		self["config"].list = conflist
		self["config"].l.setList(conflist)

		self["streams"].list = streams
		self["streams"].setIndex(selectedidx)

	def __updatedInfo(self):
		self.fillList()

	def getSubtitleList(self):
		s = self.infobar and self.infobar.getCurrentServiceSubtitle()
		l = s and s.getSubtitleList() or [ ]
		return l

	def subtitlesEnabled(self):
		return self.infobar.subtitles_enabled

	def enableSubtitle(self, subtitles):
		print "[enableSubtitle]", subtitles
		if self.infobar.selected_subtitle != subtitles:
			self.infobar.subtitles_enabled = False
			self.infobar.selected_subtitle = subtitles
			if subtitles:
				self.infobar.subtitles_enabled = True

	def changeAC3Downmix(self, downmix):
		print "changeAC3Downmix config.av.downmix_ac3.value=", config.av.downmix_ac3.value, downmix.getValue()
		if downmix.getValue() == True:
			config.av.downmix_ac3.value = True
		else:
			config.av.downmix_ac3.value = False
		config.av.downmix_ac3.save()

	def changeMode(self, mode):
		print "changeMode", mode, mode.getValue()
		if mode is not None:
			self.audioChannel.selectChannel(int(mode.getValue()))

	def changeAudio(self, audio):
		print "changeAudio", audio, "self.session.nav.getCurrentService().audioTracks().getNumberOfTracks():", self.session.nav.getCurrentService().audioTracks().getNumberOfTracks()
		track = int(audio)
		if isinstance(track, int):
			if self.session.nav.getCurrentService().audioTracks().getNumberOfTracks() > track:
				self.audioTracks.selectTrack(track)

	def keyLeft(self):
		if self.focus == FOCUS_CONFIG:
			ConfigListScreen.keyLeft(self)
		elif self.focus == FOCUS_STREAMS:
			self["streams"].setIndex(0)

	def keyRight(self):
		if self.focus == FOCUS_CONFIG:
			ConfigListScreen.keyRight(self)
		elif self.focus == FOCUS_STREAMS and self["streams"].count():
			self["streams"].setIndex(self["streams"].count()-1)

	def keyRed(self):
		self.colorkey(0)

	def keyGreen(self):
		self.colorkey(1)

	def keyYellow(self):
		self.colorkey(2)
	
	def keyBlue(self):
		pass
		
	def colorkey(self, idx):
		self["config"].setCurrentIndex(idx)
		ConfigListScreen.keyRight(self)

	def keyUp(self):
		print "[keyUp]", self["streams"].getIndex()
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
		print "[keyDown]", self["config"].getCurrentIndex(), len(self["config"].getList())-1
		if self.focus == FOCUS_CONFIG:
			if self["config"].getCurrentIndex() < len(self["config"].getList())-1:
				self["config"].instance.moveSelection(self["config"].instance.moveDown)
			else:
				self["config"].instance.setSelectionEnable(False)
				self["streams"].style = "default"
				self.focus = FOCUS_STREAMS
		elif self.focus == FOCUS_STREAMS:
			self["streams"].selectNext()

	def keyOk(self):
		print "[keyok]", self["streams"].list, self["streams"].getCurrent()
		if self.focus == FOCUS_STREAMS and self["streams"].list:
			cur = self["streams"].getCurrent()
			if self.settings.menupage.getValue() == "audio" and cur[0] is not None:
				self.changeAudio(cur[2])
				self.__updatedInfo()
			if self.settings.menupage.getValue() == "subtitles" and cur[0] is not None:
				if self.infobar.selected_subtitle == cur[0]:
					self.enableSubtitle(None)
					selectedidx = self["streams"].getIndex()
					self.__updatedInfo()
					self["streams"].setIndex(selectedidx)
				else:
					self.enableSubtitle(cur[0])
					self.__updatedInfo()
		#self.close()
		elif self.focus == FOCUS_CONFIG:
			self.keyRight()

	def cancel(self):
		self.close()
