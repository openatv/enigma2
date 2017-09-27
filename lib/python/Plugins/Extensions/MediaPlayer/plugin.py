import os
import time
import random
from boxbranding import getMachineBrand, getMachineName

from enigma import iPlayableService, eTimer, eServiceCenter, iServiceInformation, ePicLoad, eServiceReference

from ServiceReference import ServiceReference
from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox
from Screens.ChoiceBox import ChoiceBox
from Screens.InfoBar import InfoBar, setAudioTrack
from Screens.InfoBarGenerics import InfoBarSeek, InfoBarScreenSaver, InfoBarAudioSelection, InfoBarAspectSelection, InfoBarCueSheetSupport, InfoBarNotifications, InfoBarSubtitleSupport, InfoBarResolutionSelection
from Components.ActionMap import NumberActionMap, HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap,MultiPixmap
from Components.FileList import FileList
from Components.MediaPlayer import PlayList
from Components.MovieList import AUDIO_EXTENSIONS
from Components.ServicePosition import ServicePositionGauge
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from Components.Playlist import PlaylistIOInternal, PlaylistIOM3U, PlaylistIOPLS
from Components.AVSwitch import AVSwitch
from Components.Harddisk import harddiskmanager
from Components.config import config
from Tools.Directories import fileExists, resolveFilename, SCOPE_CONFIG, SCOPE_PLAYLIST, SCOPE_ACTIVE_SKIN
from Tools.BoundFunction import boundFunction
from settings import MediaPlayerSettings, Load_defaults


class MyPlayList(PlayList):
	def __init__(self):
		PlayList.__init__(self)

	def PlayListShuffle(self):
		random.shuffle(self.list)
		self.l.setList(self.list)
		self.currPlaying = -1
		self.oldCurrPlaying = -1

class MediaPixmap(Pixmap):
	def __init__(self):
		Pixmap.__init__(self)
		self.coverArtFileName = ""
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.paintCoverArtPixmapCB)
		self.coverFileNames = ["folder.png", "folder.jpg"]

	def applySkin(self, desktop, screen):
		from Tools.LoadPixmap import LoadPixmap
		noCoverFile = None
		if self.skinAttributes is not None:
			for (attrib, value) in self.skinAttributes:
				if attrib == "pixmap":
					noCoverFile = value
					break
		if noCoverFile is None:
			noCoverFile = resolveFilename(SCOPE_ACTIVE_SKIN, "no_coverArt.png")
		self.noCoverPixmap = LoadPixmap(noCoverFile)
		return Pixmap.applySkin(self, desktop, screen)

	def onShow(self):
		Pixmap.onShow(self)
		sc = AVSwitch().getFramebufferScale()
		#0=Width 1=Height 2=Aspect 3=use_cache 4=resize_type 5=Background(#AARRGGBB)
		self.picload.setPara((self.instance.size().width(), self.instance.size().height(), sc[0], sc[1], False, 1, "#00000000"))

	def paintCoverArtPixmapCB(self, picInfo=None):
		ptr = self.picload.getData()
		if ptr is not None:
			self.instance.setPixmap(ptr.__deref__())

	def updateCoverArt(self, path):
		while not path.endswith("/"):
			path = path[:-1]
		new_coverArtFileName = None
		for filename in self.coverFileNames:
			if fileExists(path + filename):
				new_coverArtFileName = path + filename
		if self.coverArtFileName != new_coverArtFileName:
			self.coverArtFileName = new_coverArtFileName
			if new_coverArtFileName:
				self.picload.startDecode(self.coverArtFileName)
			else:
				self.showDefaultCover()

	def showDefaultCover(self):
		self.instance.setPixmap(self.noCoverPixmap)

	def embeddedCoverArt(self):
		print "[embeddedCoverArt] found"
		self.coverArtFileName = "/tmp/.id3coverart"
		self.picload.startDecode(self.coverArtFileName)

class MediaPlayerInfoBar(Screen):

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "MoviePlayer"

class MediaPlayer(Screen, InfoBarBase, InfoBarScreenSaver, InfoBarSeek, InfoBarAudioSelection, InfoBarAspectSelection, InfoBarCueSheetSupport, InfoBarNotifications, InfoBarSubtitleSupport, HelpableScreen, InfoBarResolutionSelection):
	ALLOW_SUSPEND = True
	ENABLE_RESUME_SUPPORT = True
	FLAG_CENTER_DVB_SUBS = 2048

	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		InfoBarAudioSelection.__init__(self)
		InfoBarAspectSelection.__init__(self)
		InfoBarCueSheetSupport.__init__(self, actionmap = "MediaPlayerCueSheetActions")
		InfoBarNotifications.__init__(self)
		InfoBarBase.__init__(self)
		InfoBarScreenSaver.__init__(self)
		InfoBarSubtitleSupport.__init__(self)
		HelpableScreen.__init__(self)
		InfoBarResolutionSelection.__init__(self)
		self.summary = None
		self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()

		self.playlistparsers = {}
		self.addPlaylistParser(PlaylistIOM3U, "m3u")
		self.addPlaylistParser(PlaylistIOPLS, "pls")
		self.addPlaylistParser(PlaylistIOInternal, "e2pls")

		# 'None' is magic to start at the list of mountpoints
		try:
			defaultDir = config.mediaplayer.defaultDir.value
		except:
			Load_defaults()
			defaultDir = config.mediaplayer.defaultDir.value
		self.filelist = FileList(defaultDir, matchingPattern = "(?i)^.*\.(mp2|mp3|ogg|ts|trp|mts|m2ts|wav|wave|m3u|pls|e2pls|mpg|vob|avi|divx|m4v|mkv|mp4|m4a|dat|flac|flv|mov|dts|3gp|3g2|asf|wmv|wma|webm)", useServiceRef = True, additionalExtensions = "4098:m3u 4098:e2pls 4098:pls")
		self["filelist"] = self.filelist

		self.playlist = MyPlayList()
		self.is_closing = False
		self.hiding = False
		self.delname = ""
		self.playlistname = ""
		self["playlist"] = self.playlist

		self["PositionGauge"] = ServicePositionGauge(self.session.nav)

		self["currenttext"] = Label("")

		self["artisttext"] = Label(_("Artist")+':')
		self["artist"] = Label("")
		self["titletext"] = Label(_("Title")+':')
		self["title"] = Label("")
		self["albumtext"] = Label(_("Album")+':')
		self["album"] = Label("")
		self["yeartext"] = Label(_("Year")+':')
		self["year"] = Label("")
		self["genretext"] = Label(_("Genre")+':')
		self["genre"] = Label("")
		self["coverArt"] = MediaPixmap()
		self["repeat"] = MultiPixmap()

		self.seek_target = None

		try:
			from Plugins.SystemPlugins.Hotplug.plugin import hotplugNotifier
			hotplugNotifier.append(self.hotplugCB)
		except Exception, ex:
			print "[MediaPlayer] No hotplug support", ex

		class MoviePlayerActionMap(NumberActionMap):
			def __init__(self, player, contexts=None, actions=None, prio=0):
				if not contexts: contexts = []
				if not actions: actions = {}
				NumberActionMap.__init__(self, contexts, actions, prio)
				self.player = player

			def action(self, contexts, action):
				self.player.show()
				return NumberActionMap.action(self, contexts, action)

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
				"ok": (self.ok, _("Add file to playlist")),
				"cancel": (self.exit, _("Exit mediaplayer")),
			}, -2)

		self["MediaPlayerActions"] = HelpableActionMap(self, "MediaPlayerActions",
			{
				"play": (self.xplayEntry, _("Play entry")),
				"pause": (self.pauseEntry, _("Pause")),
				"stop": (self.stopEntry, _("Stop entry")),
				"previous": (self.previousMarkOrEntry, _("Play from previous mark or playlist entry")),
				"next": (self.nextMarkOrEntry, _("Play from next mark or playlist entry")),
				"menu": (self.showMenu, _("Menu")),
				"skipListbegin": (self.skip_listbegin, _("Jump to beginning of list")),
				"skipListend": (self.skip_listend, _("Jump to end of list")),
				"prevBouquet": (self.switchLists, _("Switch between filelist/playlist")),
				"nextBouquet": (self.switchLists, _("Switch between filelist/playlist")),
				"delete": (self.deletePlaylistEntry, _("Delete playlist entry")),
				"shift_stop": (self.clear_playlist, _("Clear playlist")),
				"shift_record": (self.playlist.PlayListShuffle, _("Shuffle playlist")),
				"subtitles": (self.subtitleSelection, _("Subtitle selection")),
			}, -2)

		self["InfobarEPGActions"] = HelpableActionMap(self, "InfobarEPGActions",
			{
				"showEventInfo": (self.showEventInformation, _("show event details")),
			})

		self["actions"] = MoviePlayerActionMap(self, ["DirectionActions"],
		{
			"right": self.rightDown,
			"rightRepeated": self.doNothing,
			"rightUp": self.rightUp,
			"left": self.leftDown,
			"leftRepeated": self.doNothing,
			"leftUp": self.leftUp,

			"up": self.up,
			"upRepeated": self.up,
			"upUp": self.doNothing,
			"down": self.down,
			"downRepeated": self.down,
			"downUp": self.doNothing,
		}, -2)

		InfoBarSeek.__init__(self, actionmap = "MediaPlayerSeekActions")

		self.mediaPlayerInfoBar = self.session.instantiateDialog(MediaPlayerInfoBar)

		self.onClose.append(self.delMPTimer)
		self.onClose.append(self.__onClose)
		self.onShow.append(self.timerHideMediaPlayerInfoBar)

		self.righttimer = False
		self.rightKeyTimer = eTimer()
		self.rightKeyTimer.callback.append(self.rightTimerFire)

		self.lefttimer = False
		self.leftKeyTimer = eTimer()
		self.leftKeyTimer.callback.append(self.leftTimerFire)

		self.hideMediaPlayerInfoBar = eTimer()
		self.hideMediaPlayerInfoBar.callback.append(self.timerHideMediaPlayerInfoBar)

		self.currList = "filelist"
		self.isAudioCD = False
		self.ext = None
		self.AudioCD_albuminfo = {}
		self.cdAudioTrackFiles = []
		self.onShown.append(self.applySettings)

		self.playlistIOInternal = PlaylistIOInternal()
		list = self.playlistIOInternal.open(resolveFilename(SCOPE_CONFIG, "playlist.e2pls"))
		if list:
			for x in list:
				self.playlist.addFile(x.ref)
			self.playlist.updateList()

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evStart: self.__evStart,
				iPlayableService.evUpdatedInfo: self.__evUpdatedInfo,
				iPlayableService.evUser+10: self.__evAudioDecodeError,
				iPlayableService.evUser+11: self.__evVideoDecodeError,
				iPlayableService.evUser+12: self.__evPluginError,
				# we dont need that anymore, but keep it for the next two weeks
				# let us see, if user reports any problems
				iPlayableService.evUser+13: self["coverArt"].embeddedCoverArt,
				iPlayableService.evUser+13: self.__embeddedCoverArt
			})

	def hideAndInfoBar(self):
		self.hide()
		self.hiding = True
		self.mediaPlayerInfoBar.show()
		if config.mediaplayer.alwaysHideInfoBar.value or self.ext not in AUDIO_EXTENSIONS and not self.isAudioCD:
			self.hideMediaPlayerInfoBar.start(5000, True)

	def timerHideMediaPlayerInfoBar(self):
		self.hideMediaPlayerInfoBar.stop()
		self.mediaPlayerInfoBar.hide()

	def doNothing(self):
		pass

	def createSummary(self):
		return MediaPlayerLCDScreen

	def exit(self):
		if self.mediaPlayerInfoBar.shown:
			self.timerHideMediaPlayerInfoBar()
		else:
			self.session.openWithCallback(self.exitCallback, MessageBox, _("Exit media player?"), simple = not self.shown)

	def exitCallback(self, answer):
		if answer:
			self.playlistIOInternal.clear()
			for x in self.playlist.list:
				self.playlistIOInternal.addService(ServiceReference(x[0]))
			if self.savePlaylistOnExit:
				try:
					self.playlistIOInternal.save(resolveFilename(SCOPE_CONFIG, "playlist.e2pls"))
				except IOError:
					print "couldn't save playlist.e2pls"
			if config.mediaplayer.saveDirOnExit.value:
				config.mediaplayer.defaultDir.setValue(self.filelist.getCurrentDirectory())
				config.mediaplayer.defaultDir.save()
			try:
				from Plugins.SystemPlugins.Hotplug.plugin import hotplugNotifier
				hotplugNotifier.remove(self.hotplugCB)
			except:
				pass
			del self["coverArt"].picload
			self.close()

	def checkSkipShowHideLock(self):
		self.updatedSeekState()

	def doEofInternal(self, playing):
		if playing:
			self.nextEntry()
		else:
			self.show()

	def __onClose(self):
		self.mediaPlayerInfoBar.doClose()
		self.session.nav.playService(self.oldService)

	def __evStart(self):
		self.switchAudioTimer = eTimer()
		self.switchAudioTimer.callback.append(self.switchAudio)
		self.switchAudioTimer.start(750, True)    # 750 is a safe-value

	def __evUpdatedInfo(self):
		currPlay = self.session.nav.getCurrentService()
		sTagTrackNumber = currPlay.info().getInfo(iServiceInformation.sTagTrackNumber)
		sTagTrackCount = currPlay.info().getInfo(iServiceInformation.sTagTrackCount)
		sTagTitle = currPlay.info().getInfoString(iServiceInformation.sTagTitle)
		if sTagTrackNumber or sTagTrackCount or sTagTitle:
			print "[__evUpdatedInfo] title %d of %d (%s)" % (sTagTrackNumber, sTagTrackCount, sTagTitle)
		self.readTitleInformation()

	def __evAudioDecodeError(self):
		currPlay = self.session.nav.getCurrentService()
		sTagAudioCodec = currPlay.info().getInfoString(iServiceInformation.sTagAudioCodec)
		print "[__evAudioDecodeError] audio-codec %s can't be decoded by hardware" % sTagAudioCodec
		self.session.open(MessageBox, _("This %s %s cannot decode %s streams!") % (getMachineBrand(), getMachineName(), sTagAudioCodec), type = MessageBox.TYPE_INFO,timeout = 20 )

	def __evVideoDecodeError(self):
		currPlay = self.session.nav.getCurrentService()
		sTagVideoCodec = currPlay.info().getInfoString(iServiceInformation.sTagVideoCodec)
		print "[__evVideoDecodeError] video-codec %s can't be decoded by hardware" % sTagVideoCodec
		self.session.open(MessageBox, _("This %s %s cannot decode %s streams!") % (getMachineBrand(), getMachineName(), sTagVideoCodec), type = MessageBox.TYPE_INFO,timeout = 20 )

	def __evPluginError(self):
		currPlay = self.session.nav.getCurrentService()
		message = currPlay.info().getInfoString(iServiceInformation.sUser+12)
		print "[__evPluginError]" , message
		self.session.open(MessageBox, message, type = MessageBox.TYPE_INFO,timeout = 20 )

	def __embeddedCoverArt(self):
		self.embeddedCoverArtTimer = eTimer()
		self.embeddedCoverArtTimer.callback.append(self.showEmbeddedCoverArt)
		self.embeddedCoverArtTimer.start(500, True)

	def showEmbeddedCoverArt(self):
		self["coverArt"].embeddedCoverArt()

	def delMPTimer(self):
		del self.rightKeyTimer
		del self.leftKeyTimer

	def switchAudio(self):
		service = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if service:
			# we go this way for other extensions as own records(they switch over pmt in c)
			path = service.getPath()
			ext = os.path.splitext(path)[1].lower()
			exts = [".mkv", ".avi", ".divx", ".mp4"]      # we need more extensions here ?
			if ext.lower() in exts:
				service = self.session.nav.getCurrentService()
				if service:
					setAudioTrack(service)

	def readTitleInformation(self):
		currPlay = self.session.nav.getCurrentService()
		if currPlay is not None:
			sTitle = currPlay.info().getInfoString(iServiceInformation.sTagTitle)
			sAlbum = currPlay.info().getInfoString(iServiceInformation.sTagAlbum)
			sGenre = currPlay.info().getInfoString(iServiceInformation.sTagGenre)
			sArtist = currPlay.info().getInfoString(iServiceInformation.sTagArtist)
			sYear = currPlay.info().getInfoString(iServiceInformation.sTagDate)

			if sTitle == "":
				if not self.isAudioCD:
					sTitle = currPlay.info().getName().split('/')[-1]
				else:
					sTitle = self.playlist.getServiceRefList()[self.playlist.getCurrentIndex()].getName()

			if self.AudioCD_albuminfo:
				if sAlbum == "" and "title" in self.AudioCD_albuminfo:
					sAlbum = self.AudioCD_albuminfo["title"]
				if sGenre == "" and "genre" in self.AudioCD_albuminfo:
					sGenre = self.AudioCD_albuminfo["genre"]
				if sArtist == "" and "artist" in self.AudioCD_albuminfo:
					sArtist = self.AudioCD_albuminfo["artist"]
				if "year" in self.AudioCD_albuminfo:
					sYear = self.AudioCD_albuminfo["year"]

			self.updateMusicInformation( sArtist, sTitle, sAlbum, sYear, sGenre, clear = True )
		else:
			self.updateMusicInformation()

	def updateMusicInformation(self, artist = "", title = "", album = "", year = "", genre = "", clear = False):
		self.updateSingleMusicInformation("artist", artist, clear)
		self.updateSingleMusicInformation("title", title, clear)
		self.updateSingleMusicInformation("album", album, clear)
		self.updateSingleMusicInformation("year", year, clear)
		self.updateSingleMusicInformation("genre", genre, clear)

	def updateSingleMusicInformation(self, name, info, clear):
		if info != "" or clear:
			if self[name].getText() != info:
				self[name].setText(info)
				if info != "":
					if name == "artist":
						self.summaries.setText(info,1)
					elif name == "title":
						idx = self.playlist.getCurrentIndex()
						currref = self.playlist.getServiceRefList()[idx]
						if info != self.getIdentifier(currref):
							self.summaries.setText(info,3)
					elif name == "album":
						self.summaries.setText(info,4)

	def leftDown(self):
		if self.hiding:
			self.show()
			self.hiding = False
		else:
			if self.currList == "playlist":
				if self.playlist.getSelectionIndex() > 0:
					self.playlist.pageUp()
				else:
					self.lefttimer = True
					self.leftKeyTimer.start(1000)
			else:
				self.filelist.pageUp()

	def rightDown(self):
		if self.hiding:
			self.show()
			self.hiding = False
		else:
			if self.currList == "filelist":
				if (self.filelist.getSelectionIndex() + 1) < len(self.filelist.list):
					self.filelist.pageDown()
				else:
					self.righttimer = True
					self.rightKeyTimer.start(1000)
			else:
				self.playlist.pageDown()

	def leftUp(self):
		if self.lefttimer:
			self.leftKeyTimer.stop()
			self.lefttimer = False
			self[self.currList].pageUp()
			self.updateCurrentInfo()

	def rightUp(self):
		if self.righttimer:
			self.rightKeyTimer.stop()
			self.righttimer = False
			self[self.currList].pageDown()
			self.updateCurrentInfo()

	def leftTimerFire(self):
		self.leftKeyTimer.stop()
		self.lefttimer = False
		self.switchToFileList()

	def rightTimerFire(self):
		self.rightKeyTimer.stop()
		self.righttimer = False
		self.switchToPlayList()

	def switchLists(self):
		if self.currList == "filelist":
			self.switchToPlayList()
			return
		self.switchToFileList()

	def switchToFileList(self):
		self.currList = "filelist"
		self.filelist.selectionEnabled(1)
		self.playlist.selectionEnabled(0)
		self.updateCurrentInfo()

	def switchToPlayList(self):
		if len(self.playlist) != 0:
			self.currList = "playlist"
			self.filelist.selectionEnabled(0)
			self.playlist.selectionEnabled(1)
			self.updateCurrentInfo()

	def up(self):
		self[self.currList].up()
		self.updateCurrentInfo()

	def down(self):
		self[self.currList].down()
		self.updateCurrentInfo()

	def showAfterSeek(self):
		if not self.shown:
			self.hideAndInfoBar()

	def showAfterCuesheetOperation(self):
		self.show()

	def hideAfterResume(self):
		self.hideAndInfoBar()

	def getIdentifier(self, ref):
		if self.isAudioCD:
			return ref.getName()
		else:
			text = ref.getPath()
			return text.split('/')[-1]

	# FIXME: maybe this code can be optimized
	def updateCurrentInfo(self):
		text = ""
		if self.currList == "filelist":
			idx = self.filelist.getSelectionIndex()
			r = self.filelist.list[idx]
			text = r[1][7]
			if r[0][1]:
				if len(text) < 2:
					text += " "
				if text[:2] != "..":
					text = "/" + text
			self.summaries.setText(text,1)

			idx += 1
			if idx < len(self.filelist.list):
				r = self.filelist.list[idx]
				text = r[1][7]
				if r[0][1]:
					text = "/" + text
				self.summaries.setText(text,3)
			else:
				self.summaries.setText(" ",3)

			idx += 1
			if idx < len(self.filelist.list):
				r = self.filelist.list[idx]
				text = r[1][7]
				if r[0][1]:
					text = "/" + text
				self.summaries.setText(text,4)
			else:
				self.summaries.setText(" ",4)

			text = ""
			if not self.filelist.canDescent():
				r = self.filelist.getServiceRef()
				if r is None:
					return
				text = r.getPath()
				self["currenttext"].setText(os.path.basename(text))

		if self.currList == "playlist":
			t = self.playlist.getSelection()
			if t is None:
				return
			#display current selected entry on LCD
			text = self.getIdentifier(t)
			self.summaries.setText(text,1)
			self["currenttext"].setText(text)
			idx = self.playlist.getSelectionIndex()
			idx += 1
			if idx < len(self.playlist):
				currref = self.playlist.getServiceRefList()[idx]
				text = self.getIdentifier(currref)
				self.summaries.setText(text,3)
			else:
				self.summaries.setText(" ",3)

			idx += 1
			if idx < len(self.playlist):
				currref = self.playlist.getServiceRefList()[idx]
				text = self.getIdentifier(currref)
				self.summaries.setText(text,4)
			else:
				self.summaries.setText(" ",4)

	def ok(self):
		if self.currList == "filelist":
			if self.filelist.canDescent():
				self.filelist.descent()
				self.updateCurrentInfo()
			else:
				self.copyFile()

		if self.currList == "playlist":
			if self.playlist.getCurrentIndex() == self.playlist.getSelectionIndex() and not self.playlist.isStopped():
				if self.shown:
					if self.seekstate == self.SEEK_STATE_PAUSE or self.isStateForward(self.seekstate) or self.isStateBackward(self.seekstate):
						self.pauseEntry()
					else:
						self.hideAndInfoBar()
				elif self.mediaPlayerInfoBar.shown:
					self.mediaPlayerInfoBar.hide()
					self.hideMediaPlayerInfoBar.stop()
					if self.ext in AUDIO_EXTENSIONS or self.isAudioCD:
						self.show()
				else:
					self.mediaPlayerInfoBar.show()
			else:
				self.changeEntry(self.playlist.getSelectionIndex())

	def showMenu(self):
		menulist = []
		if len(self.cdAudioTrackFiles):
			menulist.insert(0,(_("Play audio-CD..."), "audiocd"))
		if self.currList == "filelist":
			if self.filelist.canDescent():
				menulist.append((_("Add directory to playlist"), "copydir"))
			else:
				menulist.append((_("Add files to playlist"), "copyfiles"))
			menulist.append((_("Switch to playlist"), "playlist"))
			if config.usage.setup_level.index >= 1: # intermediate+
				menulist.append((_("Delete file"), "deletefile"))
		else:
			menulist.append((_("Switch to filelist"), "filelist"))
			menulist.append((_("Clear playlist"), "clear"))
			menulist.append((_("Delete entry"), "deleteentry"))
			if config.usage.setup_level.index >= 1: # intermediate+
				menulist.append((_("Shuffle playlist"), "shuffle"))
		menulist.append((_("Hide player"), "hide"))
		menulist.append((_("Load playlist"), "loadplaylist"))
		if config.usage.setup_level.index >= 1: # intermediate+
			menulist.append((_("Save playlist"), "saveplaylist"))
			menulist.append((_("Delete saved playlist"), "deleteplaylist"))
			menulist.append((_("Edit settings"), "settings"))
		self.timerHideMediaPlayerInfoBar()
		self.session.openWithCallback(self.menuCallback, ChoiceBox, title="", list=menulist)

	def menuCallback(self, choice):
		self.show()
		if choice is None:
			return

		if choice[1] == "copydir":
			self.copyDirectory(self.filelist.getSelection()[0])
		elif choice[1] == "copyfiles":
			self.copyDirectory(os.path.dirname(self.filelist.getSelection()[0].getPath()) + "/", recursive = False)
		elif choice[1] == "playlist":
			self.switchToPlayList()
		elif choice[1] == "filelist":
			self.switchToFileList()
		elif choice[1] == "deleteentry":
			if self.playlist.getSelectionIndex() == self.playlist.getCurrentIndex():
				self.stopEntry()
			self.deleteEntry()
		elif choice[1] == "clear":
			self.clear_playlist()
		elif choice[1] == "hide":
			self.hideAndInfoBar()
		elif choice[1] == "saveplaylist":
			self.save_playlist()
		elif choice[1] == "loadplaylist":
			self.load_playlist()
		elif choice[1] == "deleteplaylist":
			self.delete_saved_playlist()
		elif choice[1] == "shuffle":
			self.playlist.PlayListShuffle()
		elif choice[1] == "deletefile":
			self.deleteFile()
		elif choice[1] == "settings":
			self.session.openWithCallback(self.applySettings, MediaPlayerSettings, self)
		elif choice[1] == "audiocd":
			self.playAudioCD()

	def playAudioCD(self):
		from enigma import eServiceReference
		if len(self.cdAudioTrackFiles):
			self.playlist.clear()
			self.savePlaylistOnExit = False
			self.isAudioCD = True
			for x in self.cdAudioTrackFiles:
				ref = eServiceReference(4097, 0, x)
				self.playlist.addFile(ref)
			try:
				from Plugins.Extensions.CDInfo.plugin import Query
				cdinfo = Query(self)
				cdinfo.scan()
			except ImportError:
				pass # we can live without CDInfo
			self.changeEntry(0)
			self.switchToPlayList()

	def applySettings(self):
		self.savePlaylistOnExit = config.mediaplayer.savePlaylistOnExit.value
		if config.mediaplayer.repeat.value:
			self["repeat"].setPixmapNum(1)
		else:
			self["repeat"].setPixmapNum(0)

	def showEventInformation(self):
		from Screens.EventView import EventViewSimple
		from ServiceReference import ServiceReference
		evt = self[self.currList].getCurrentEvent()
		if evt:
			self.session.open(EventViewSimple, evt, ServiceReference(self.getCurrent()))

	# also works on filelist (?)
	def getCurrent(self):
		return self["playlist"].getCurrent()

	def deletePlaylistEntry(self):
		if self.currList == "playlist":
			if self.playlist.getSelectionIndex() == self.playlist.getCurrentIndex():
				self.stopEntry()
			self.deleteEntry()

	def skip_listbegin(self):
		if self.currList == "filelist":
			self.filelist.moveToIndex(0)
		else:
			self.playlist.moveToIndex(0)
		self.updateCurrentInfo()

	def skip_listend(self):
		if self.currList == "filelist":
			idx = len(self.filelist.list)
			self.filelist.moveToIndex(idx - 1)
		else:
			self.playlist.moveToIndex(len(self.playlist)-1)
		self.updateCurrentInfo()

	def save_playlist(self):
		self.session.openWithCallback(self.save_playlist2,InputBox, title=_("Please enter filename (empty = use current date)"),windowTitle = _("Save playlist"), text=self.playlistname)

	def save_playlist2(self, name):
		if name is not None:
			name = name.strip()
			if name == "":
				name = time.strftime("%y%m%d_%H%M%S")
			self.playlistname = name
			name += ".e2pls"
			self.playlistIOInternal.clear()
			for x in self.playlist.list:
				self.playlistIOInternal.addService(ServiceReference(x[0]))
			self.playlistIOInternal.save(resolveFilename(SCOPE_PLAYLIST) + name)

	def load_playlist(self):
		listpath = []
		playlistdir = resolveFilename(SCOPE_PLAYLIST)
		try:
			for i in os.listdir(playlistdir):
				listpath.append((i,playlistdir + i))
		except IOError,e:
			print "Error while scanning subdirs ",e
		if config.mediaplayer.sortPlaylists.value:
			listpath.sort()
		self.session.openWithCallback(self.PlaylistSelected, ChoiceBox, title=_("Please select a playlist..."), list = listpath)

	def PlaylistSelected(self,path):
		if path is not None:
			self.playlistname = path[0].rsplit('.',1)[-2]
			self.clear_playlist()
			extension = path[0].rsplit('.',1)[-1]
			if self.playlistparsers.has_key(extension):
				playlist = self.playlistparsers[extension]()
				list = playlist.open(path[1])
				for x in list:
					self.playlist.addFile(x.ref)
			self.playlist.updateList()

	def delete_saved_playlist(self):
		listpath = []
		playlistdir = resolveFilename(SCOPE_PLAYLIST)
		try:
			for i in os.listdir(playlistdir):
				listpath.append((i,playlistdir + i))
		except IOError,e:
			print "Error while scanning subdirs ",e
		if config.mediaplayer.sortPlaylists.value:
			listpath.sort()
		self.session.openWithCallback(self.DeletePlaylistSelected, ChoiceBox, title=_("Please select a playlist to delete..."), list = listpath)

	def DeletePlaylistSelected(self,path):
		if path is not None:
			self.delname = path[1]
			self.session.openWithCallback(self.deleteConfirmed, MessageBox, _("Do you really want to delete %s?") % (path[1]))

	def deleteConfirmed(self, confirmed):
		if confirmed:
			try:
				os.remove(self.delname)
			except OSError,e:
				print "delete failed:", e
				self.session.open(MessageBox, _("Delete failed!"), MessageBox.TYPE_ERROR)

	def clear_playlist(self):
		self.isAudioCD = False
		self.stopEntry()
		self.playlist.clear()
		self.switchToFileList()

	def copyDirectory(self, directory, recursive = True):
		print "copyDirectory", directory
		if directory == '/':
			print "refusing to operate on /"
			return
		filelist = FileList(directory, useServiceRef = True, showMountpoints = False, isTop = True)

		for x in filelist.getFileList():
			if x[0][1]: #isDir
				if recursive:
					if x[0][0] != directory:
						self.copyDirectory(x[0][0])
			# check if MerlinMusicPlayer is installed and merlinmp3player.so is running
			# so we need the right id to play now the mp3-file
			elif filelist.getServiceRef() and filelist.getServiceRef().type == 4116:
				inst = x[0][0]
				if isinstance(inst, eServiceReference):
					path = inst.getPath()
					service = eServiceReference(4097, 0, path)
					self.playlist.addFile(service)
			elif filelist.getServiceRef() and filelist.getServiceRef().type == 4097:
				self.playlist.addFile(x[0][0])
		self.playlist.updateList()

	def deleteFile(self):
		if self.currList == "filelist":
			self.service = self.filelist.getServiceRef()
		else:
			self.service = self.playlist.getSelection()
		if self.service is None:
			return
		if self.service.type != 4098 and self.session.nav.getCurrentlyPlayingServiceReference() is not None:
			if self.service == self.session.nav.getCurrentlyPlayingServiceReference():
				self.stopEntry()

		serviceHandler = eServiceCenter.getInstance()
		offline = serviceHandler.offlineOperations(self.service)
		info = serviceHandler.info(self.service)
		name = info and info.getName(self.service)
		result = False
		if offline is not None:
			# simulate first
			if not offline.deleteFromDisk(1):
				result = True
		if result:
			self.session.openWithCallback(self.deleteConfirmed_offline, MessageBox, _("Do you really want to delete %s?") % name)
		else:
			self.session.openWithCallback(self.close, MessageBox, _("You cannot delete this!"), MessageBox.TYPE_ERROR)

	def deleteConfirmed_offline(self, confirmed):
		if confirmed:
			serviceHandler = eServiceCenter.getInstance()
			offline = serviceHandler.offlineOperations(self.service)
			result = False
			if offline is not None:
				# really delete!
				if not offline.deleteFromDisk(0):
					result = True
			if not result:
				self.session.open(MessageBox, _("Delete failed!"), MessageBox.TYPE_ERROR)
			else:
				self.removeListEntry()

	def removeListEntry(self):
		currdir = self.filelist.getCurrentDirectory()
		self.filelist.changeDir(currdir)
		deleteend = False
		while not deleteend:
			index = 0
			deleteend = True
			if len(self.playlist) > 0:
				for x in self.playlist.list:
					if self.service == x[0]:
						self.playlist.deleteFile(index)
						deleteend = False
						break
					index += 1
		self.playlist.updateList()
		if self.currList == "playlist":
			if len(self.playlist) == 0:
				self.switchToFileList()

	def copyFile(self):
		if self.filelist.getServiceRef().type == 4098: # playlist
			ServiceRef = self.filelist.getServiceRef()
			extension = ServiceRef.getPath()[ServiceRef.getPath().rfind('.') + 1:]
			if self.playlistparsers.has_key(extension):
				playlist = self.playlistparsers[extension]()
				list = playlist.open(ServiceRef.getPath())
				for x in list:
					self.playlist.addFile(x.ref)
			self.playlist.updateList()
		# check if MerlinMusicPlayer is installed and merlinmp3player.so is running
		# so we need the right id to play now the mp3-file
		elif self.filelist.getServiceRef().type == 4116:
				if self.filelist.getSelection() is not None:
					inst = self.filelist.getSelection()[0]
					if isinstance(inst, eServiceReference):
						path = inst.getPath()
						service = eServiceReference(4097, 0, path)
						self.playlist.addFile(service)
						self.playlist.updateList()
						if len(self.playlist) == 1:
							self.changeEntry(0)
		else:
			self.playlist.addFile(self.filelist.getServiceRef())
			self.playlist.updateList()
			if len(self.playlist) == 1:
				self.changeEntry(0)

	def addPlaylistParser(self, parser, extension):
		self.playlistparsers[extension] = parser

	def nextEntry(self):
		next = self.playlist.getCurrentIndex() + 1
		if next < len(self.playlist):
			self.changeEntry(next)
		elif ( len(self.playlist) > 0 ) and ( config.mediaplayer.repeat.value == True ):
			self.stopEntry()
			self.changeEntry(0)
		elif len(self.playlist) > 0:
			self.stopEntry()

	def nextMarkOrEntry(self):
		if not self.jumpPreviousNextMark(lambda x: x):
			next = self.playlist.getCurrentIndex() + 1
			if next < len(self.playlist):
				self.changeEntry(next)
			else:
				self.doSeek(-1)

	def previousMarkOrEntry(self):
		if not self.jumpPreviousNextMark(lambda x: -x-5*90000, start=True):
			next = self.playlist.getCurrentIndex() - 1
			if next >= 0:
				self.changeEntry(next)

	def deleteEntry(self):
		self.playlist.deleteFile(self.playlist.getSelectionIndex())
		self.playlist.updateList()
		if len(self.playlist) == 0:
			self.switchToFileList()

	def changeEntry(self, index):
		self.playlist.setCurrentPlaying(index)
		self.playEntry()

	def playServiceRefEntry(self, serviceref):
		serviceRefList = self.playlist.getServiceRefList()
		for count in range(len(serviceRefList)):
			if serviceRefList[count] == serviceref:
				self.changeEntry(count)
				break

	def xplayEntry(self):
		if self.currList == "playlist":
			self.pauseEntry()
		else:
			self.stopEntry()
			self.playlist.clear()
			self.isAudioCD = False
			sel = self.filelist.getSelection()
			if sel:
				if sel[1]: # can descent
					# add directory to playlist
					self.copyDirectory(sel[0])
				else:
					# add files to playlist
					self.copyDirectory(os.path.dirname(sel[0].getPath()) + "/", recursive = False)
			if len(self.playlist) > 0:
				self.changeEntry(0)

	def playEntry(self, coverreload=True):
		if len(self.playlist.getServiceRefList()):
			needsInfoUpdate = False
			currref = self.playlist.getServiceRefList()[self.playlist.getCurrentIndex()]
			if self.session.nav.getCurrentlyPlayingServiceReference() is None or currref != self.session.nav.getCurrentlyPlayingServiceReference() or self.playlist.isStopped():
				self.session.nav.playService(self.playlist.getServiceRefList()[self.playlist.getCurrentIndex()])
				info = eServiceCenter.getInstance().info(currref)
				description = info and info.getInfoString(currref, iServiceInformation.sDescription) or ""
				self["title"].setText(description)
				# display just playing musik on LCD
				idx = self.playlist.getCurrentIndex()
				currref = self.playlist.getServiceRefList()[idx]
				text = self.getIdentifier(currref)
				self.ext = os.path.splitext(text)[1].lower()
				text = ">"+text
				# FIXME: the information if the service contains video (and we should hide our window) should com from the service instead
				if self.ext not in AUDIO_EXTENSIONS and not self.isAudioCD:
					self.hideAndInfoBar()
				else:
					needsInfoUpdate = True
				self.summaries.setText(text,1)

				# get the next two entries
				idx += 1
				if idx < len(self.playlist):
					currref = self.playlist.getServiceRefList()[idx]
					text = self.getIdentifier(currref)
					self.summaries.setText(text,3)
				else:
					self.summaries.setText(" ",3)

				idx += 1
				if idx < len(self.playlist):
					currref = self.playlist.getServiceRefList()[idx]
					text = self.getIdentifier(currref)
					self.summaries.setText(text,4)
				else:
					self.summaries.setText(" ",4)
			else:
				idx = self.playlist.getCurrentIndex()
				currref = self.playlist.getServiceRefList()[idx]
				text = currref.getPath()
				ext = os.path.splitext(text)[1].lower()
				if self.ext not in AUDIO_EXTENSIONS and not self.isAudioCD:
					self.hideAndInfoBar()
				else:
					needsInfoUpdate = True

			self.unPauseService()
			if needsInfoUpdate and coverreload:
				path = self.playlist.getServiceRefList()[self.playlist.getCurrentIndex()].getPath()
				self["coverArt"].updateCoverArt(path)
			else:
				if coverreload:
					self["coverArt"].showDefaultCover()
			self.readTitleInformation()

	def updatedSeekState(self):
		if self.seekstate == self.SEEK_STATE_PAUSE:
			self.playlist.pauseFile()
		elif self.seekstate == self.SEEK_STATE_PLAY:
			self.playlist.playFile()
		elif self.isStateForward(self.seekstate):
			self.playlist.forwardFile()
		elif self.isStateBackward(self.seekstate):
			self.playlist.rewindFile()

	def pauseEntry(self):
		if self.shown:
			if self.currList == "playlist":
				if self.seekstate == self.SEEK_STATE_PAUSE:
					if self.playlist.getCurrentIndex() != self.playlist.getSelectionIndex():
						self.changeEntry(self.playlist.getSelectionIndex())
					else:
						if self.ext in AUDIO_EXTENSIONS or self.isAudioCD:
							# do not try to reload cover ! Cover is showing if exists.
							# we dont need that, if the same file will continue to play
							# otherwise showing embedded covers are gone !!!
							self.playEntry(False)
						else:
							self.playEntry()
				elif self.seekstate == self.SEEK_STATE_PLAY:
					if self.playlist.getCurrentIndex() != self.playlist.getSelectionIndex():
						self.changeEntry(self.playlist.getSelectionIndex())
					else:
						if not self.playlist.isStopped():
							if self.ext in AUDIO_EXTENSIONS or self.isAudioCD:
								self.pauseService()
							else:
								self.hideAndInfoBar()
						else:
							self.changeEntry(self.playlist.getSelectionIndex())
				elif self.isStateForward(self.seekstate) or self.isStateBackward(self.seekstate):
					self.playEntry()
		else:
			if self.currList == "playlist" and self.seekstate == self.SEEK_STATE_PAUSE:
				self.playEntry()
			elif self.isStateForward(self.seekstate) or self.isStateBackward(self.seekstate):
				self.playEntry()
			else:
				self.pauseService()
				if self.seekstate == self.SEEK_STATE_PAUSE:
					self.show()

	def stopEntry(self):
		self.playlist.stopFile()
		self.session.nav.playService(None)
		self.updateMusicInformation(clear=True)
		self.show()

	def unPauseService(self):
		self.setSeekState(self.SEEK_STATE_PLAY)

	def subtitleSelection(self):
		from Screens.AudioSelection import SubtitleSelection
		self.session.open(SubtitleSelection, self)

	def hotplugCB(self, dev, media_state):
		if media_state == "audiocd" or media_state == "audiocdadd":
			self.cdAudioTrackFiles = []
			if os.path.isfile('/media/audiocd/cdplaylist.cdpls'):
				list = open("/media/audiocd/cdplaylist.cdpls")
				if list:
					self.isAudioCD = True
					for x in list:
						xnon = x.replace("\n", "")
						self.cdAudioTrackFiles.append(xnon)
					self.playAudioCD()
			else:
				self.cdAudioTrackFiles = []
				if self.isAudioCD:
					self.clear_playlist()
		else:
			self.cdAudioTrackFiles = []
			if self.isAudioCD:
				self.clear_playlist()

class MediaPlayerLCDScreen(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session)
		self["text1"] = Label("Media player")
		self["text3"] = Label("")
		self["text4"] = Label("")

	def setText(self, text, line):
		if len(text) > 10:
			if text[-4:] == ".mp3":
				text = text[:-4]
		textleer = "    "
		text += textleer * 10
		if line == 1:
			self["text1"].setText(text)
		elif line == 3:
			self["text3"].setText(text)
		elif line == 4:
			self["text4"].setText(text)

def mainCheckTimeshiftCallback(session, answer):
	if answer:
		session.open(MediaPlayer)

def main(session, **kwargs):
	InfoBar.instance.checkTimeshiftRunning(boundFunction(mainCheckTimeshiftCallback, session))

def menu(menuid, **kwargs):
	try:
		if menuid == "mainmenu" and config.mediaplayer.onMainMenu.value:
			return [(_("Media player"), main, "media_player", 45)]
	except:
		pass
	return []

def filescan_open(list, session, **kwargs):
	from enigma import eServiceReference

	mp = session.open(MediaPlayer)
	mp.playlist.clear()
	mp.savePlaylistOnExit = False

	for file in list:
		if file.mimetype == "video/MP2T":
			stype = 1
		else:
			stype = 4097
		ref = eServiceReference(stype, 0, file.path)
		mp.playlist.addFile(ref)

	mp.changeEntry(0)
	mp.switchToPlayList()

def audioCD_open(list, session, **kwargs):
	from enigma import eServiceReference
	if os.path.isfile('/media/audiocd/cdplaylist.cdpls'):
		list = open("/media/audiocd/cdplaylist.cdpls")
	else:
		# to do : adding msgbox to inform user about failure of opening audiocd.
		return False
	mp = session.open(MediaPlayer)
	if list:
		mp.isAudioCD = True
		for x in list:
			xnon = x.replace("\n", "")
			mp.cdAudioTrackFiles.append(xnon)
		mp.playAudioCD()
	else:
		# to do : adding msgbox to inform user about failure of opening audiocd.
		return False

def audioCD_open_mn(session, **kwargs):
	from enigma import eServiceReference
	if os.path.isfile('/media/audiocd/cdplaylist.cdpls'):
		list = open("/media/audiocd/cdplaylist.cdpls")
	else:
		# to do : adding msgbox to inform user about failure of opening audiocd.
		return False
	mp = session.open(MediaPlayer)
	if list:
		mp.isAudioCD = True
		for x in list:
			xnon = x.replace("\n", "")
			mp.cdAudioTrackFiles.append(xnon)
		mp.playAudioCD()
	else:
		# to do : adding msgbox to inform user about failure of opening audiocd.
		return False

def movielist_open(list, session, **kwargs):
	if not list:
		# sanity
		return
	from enigma import eServiceReference
	from Screens.InfoBar import InfoBar
	f = list[0]
	if f.mimetype == "video/MP2T":
		stype = 1
	else:
		stype = 4097
	if InfoBar.instance:
		path = os.path.split(f.path)[0]
		if not path.endswith('/'):
			path += '/'
		config.movielist.last_videodir.value = path
		InfoBar.instance.showMovies(eServiceReference(stype, 0, f.path))

def audiocdscan(menuid, **kwargs):
	try:
		from Plugins.SystemPlugins.Hotplug.plugin import AudiocdAdded
	except Exception, e:
		print "[Mediaplayer.plugin] no hotplug support",e
		return []
	if menuid == "mainmenu" and AudiocdAdded() and os.path.isfile('/media/audiocd/cdplaylist.cdpls'):
		return [(_("Play audio-CD..."), audioCD_open_mn, "play_cd", 45)]
	else:
		return []

def filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	return [
		Scanner(mimetypes = ["video/mpeg", "video/MP2T", "video/x-msvideo", "video/mkv"],
			paths_to_scan =
				[
					ScanPath(path = "", with_subdirs = False),
					ScanPath(path = "PRIVATE/AVCHD/BDMV/STREAM", with_subdirs = False),
				],
			name = "Movie",
			description = _("Watch movies..."),
			openfnc = movielist_open,
		),
		Scanner(mimetypes = ["video/x-vcd"],
			paths_to_scan =
				[
					ScanPath(path = "mpegav", with_subdirs = False),
					ScanPath(path = "MPEGAV", with_subdirs = False),
				],
			name = "Video CD",
			description = _("View video CD..."),
			openfnc = filescan_open,
		),
		Scanner(mimetypes = ["audio/mpeg", "audio/x-wav", "application/ogg", "audio/x-flac"],
			paths_to_scan =
				[
					ScanPath(path = "", with_subdirs = False),
				],
			name = "Music",
			description = _("Play music..."),
			openfnc = filescan_open,
		),
		Scanner(mimetypes = ["audio/x-cda"],
			paths_to_scan =
				[
					ScanPath(path = "", with_subdirs = False),
				],
			name = "Audio-CD",
			description = _("Play audio-CD..."),
			openfnc = audioCD_open,
		),
		]

from Plugins.Plugin import PluginDescriptor
def Plugins(**kwargs):
	return [
		PluginDescriptor(name = _("Media player"), description = _("Play back media files"), where = PluginDescriptor.WHERE_PLUGINMENU, icon="MediaPlayer.png", needsRestart = False, fnc = main),
		#PluginDescriptor(name = _("Media player"), where = PluginDescriptor.WHERE_FILESCAN, needsRestart = False, fnc = filescan),
		PluginDescriptor(name = _("Media player"), where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc = audiocdscan),
		PluginDescriptor(name = _("Media player"), description = _("Play back media files"), where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc = menu)
	]
