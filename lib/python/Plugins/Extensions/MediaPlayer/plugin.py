from os import path as os_path, remove as os_remove, listdir as os_listdir
from time import strftime
from enigma import eTimer, iPlayableService, eServiceCenter, iServiceInformation
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox
from Components.ActionMap import NumberActionMap, HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.FileList import FileList
from Components.MediaPlayer import PlayList
from Tools.Directories import resolveFilename, SCOPE_CONFIG, SCOPE_PLAYLIST, SCOPE_SKIN_IMAGE
from Components.ServicePosition import ServicePositionGauge
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Playlist import PlaylistIOInternal, PlaylistIOM3U, PlaylistIOPLS
from Screens.InfoBarGenerics import InfoBarSeek, InfoBarAudioSelection, InfoBarCueSheetSupport, InfoBarNotifications
from ServiceReference import ServiceReference
from Screens.ChoiceBox import ChoiceBox
from Screens.HelpMenu import HelpableScreen
import random

class MyPlayList(PlayList):
	def __init__(self):
		PlayList.__init__(self)

	def PlayListShuffle(self):
		random.shuffle(self.list)
		self.l.setList(self.list)
		self.currPlaying = -1
		self.oldCurrPlaying = -1

class MediaPlayer(Screen, InfoBarSeek, InfoBarAudioSelection, InfoBarCueSheetSupport, InfoBarNotifications, HelpableScreen):
	ALLOW_SUSPEND = True
	ENABLE_RESUME_SUPPORT = True

	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		InfoBarAudioSelection.__init__(self)
		InfoBarCueSheetSupport.__init__(self, actionmap = "MediaPlayerCueSheetActions")
		InfoBarNotifications.__init__(self)
		HelpableScreen.__init__(self)
		self.summary = None
		self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()

		self.playlistparsers = {}
		self.addPlaylistParser(PlaylistIOM3U, "m3u")
		self.addPlaylistParser(PlaylistIOPLS, "pls")
		self.addPlaylistParser(PlaylistIOInternal, "e2pls")

		# 'None' is magic to start at the list of mountpoints
		self.filelist = FileList(None, matchingPattern = "(?i)^.*\.(mp3|ogg|ts|wav|wave|m3u|pls|e2pls|mpg|vob)", useServiceRef = True)
		self["filelist"] = self.filelist

		self.playlist = MyPlayList()
		#self.playlist = PlayList()
		self.is_closing = False
		self.delname = ""
		self["playlist"] = self.playlist

		self["PositionGauge"] = ServicePositionGauge(self.session.nav)

		self["currenttext"] = Label("")

		self["artisttext"] = Label(_("Artist:"))
		self["artist"] = Label("")
		self["titletext"] = Label(_("Title:"))
		self["title"] = Label("")
		self["albumtext"] = Label(_("Album:"))
		self["album"] = Label("")
		self["yeartext"] = Label(_("Year:"))
		self["year"] = Label("")
		self["genretext"] = Label(_("Genre:"))
		self["genre"] = Label("")
		self["coverArt"] = Pixmap()

		self.seek_target = None

		class MoviePlayerActionMap(NumberActionMap):
			def __init__(self, player, contexts = [ ], actions = { }, prio=0):
				NumberActionMap.__init__(self, contexts, actions, prio)
				self.player = player

			def action(self, contexts, action):
				self.player.show()
				return NumberActionMap.action(self, contexts, action)


		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions", 
			{
				"ok": (self.ok, _("add file to playlist")),
				"cancel": (self.exit, _("exit mediaplayer")),
			}, -2)

		self["MediaPlayerActions"] = HelpableActionMap(self, "MediaPlayerActions", 
			{
				"play": (self.playEntry, _("play entry")),
				"pause": (self.pauseEntry, _("pause")),
				"stop": (self.stopEntry, _("stop entry")),
				"previous": (self.previousEntry, _("play previous playlist entry")),
				"next": (self.nextEntry, _("play next playlist entry")),
				"menu": (self.showMenu, _("menu")),
				"skipListbegin": (self.skip_listbegin, _("jump to listbegin")),
				"skipListend": (self.skip_listend, _("jump to listend")),
				"prevBouquet": (self.switchToPlayList, _("switch to playlist")),
				"nextBouquet": (self.switchToFileList, _("switch to filelist")),
				"delete": (self.deletePlaylistEntry, _("delete playlist entry")),
				"shift_stop": (self.clear_playlist, _("clear playlist")),
				"shift_record": (self.playlist.PlayListShuffle, _("shuffle playlist")),
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

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				#iPlayableService.evStart: self.__serviceStarted,
				#iPlayableService.evSeekableStatusChanged: InfoBarSeek.__seekableStatusChanged,

				iPlayableService.evEOF: self.__evEOF,
			})

		self.onClose.append(self.delMPTimer)
		self.onClose.append(self.__onClose)

		self.righttimer = False
		self.rightKeyTimer = eTimer()
		self.rightKeyTimer.timeout.get().append(self.rightTimerFire)

		self.lefttimer = False
		self.leftKeyTimer = eTimer()
		self.leftKeyTimer.timeout.get().append(self.leftTimerFire)

		self.infoTimer = eTimer()
		self.infoTimer.timeout.get().append(self.infoTimerFire)
		self.infoTimer.start(500)

		self.currList = "filelist"

		self.coverArtFileName = ""

		self.playlistIOInternal = PlaylistIOInternal()
		list = self.playlistIOInternal.open(resolveFilename(SCOPE_CONFIG, "playlist.e2pls"))
		if list:
			for x in list:
				self.playlist.addFile(x.ref)
			self.playlist.updateList()

	def doNothing(self):
		pass

	def createSummary(self):
		return MediaPlayerLCDScreen

	def exit(self):
		self.session.openWithCallback(self.exitCB, MessageBox, _("Do you really want to exit?"), timeout=5)

	def exitCB(self, answer):
		if answer == True:
			self.playlistIOInternal.clear()
			for x in self.playlist.list:
				self.playlistIOInternal.addService(ServiceReference(x[0]))
			self.playlistIOInternal.save(resolveFilename(SCOPE_CONFIG, "playlist.e2pls"))
			self.close()

	def checkSkipShowHideLock(self):
		self.updatedSeekState()

	def __evEOF(self):
		self.nextEntry()

	def __onClose(self):
		self.session.nav.playService(self.oldService)

	def delMPTimer(self):
		del self.rightKeyTimer
		del self.leftKeyTimer
		del self.infoTimer

	def infoTimerFire(self):
		currPlay = self.session.nav.getCurrentService()
		if currPlay is not None:
			stitle = currPlay.info().getInfoString(iServiceInformation.sTitle)
			if stitle == "":
				stitle = currPlay.info().getName().split('/')[-1]

			self.updateMusicInformation( artist = currPlay.info().getInfoString(iServiceInformation.sArtist),
										 title = stitle,
										 album = currPlay.info().getInfoString(iServiceInformation.sAlbum),
										 genre = currPlay.info().getInfoString(iServiceInformation.sGenre),
										 clear = True)
			self.updateCoverArtPixmap( currPlay.info().getName() )
		else:
			self.updateMusicInformation()
			self.updateCoverArtPixmap( "" )

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

	def updateCoverArtPixmap(self, currentServiceName):
		filename = currentServiceName
		# The "getName" usually adds something like "MP3 File:" infront of filename
		# Get rid of this...by finding the first "/"
		# FIXME: this should be fixed in the servicemp3.cpp handler
		filename = filename[filename.find("/"):]
		path = os_path.dirname(filename)
		pngname = path + "/" + "folder.png"
		if not os_path.exists(pngname):
			pngname = resolveFilename(SCOPE_SKIN_IMAGE, "no_coverArt.png")
		if self.coverArtFileName != pngname:
			self.coverArtFileName = pngname
			self["coverArt"].instance.setPixmapFromFile(self.coverArtFileName)

	def leftDown(self):
		self.lefttimer = True
		self.leftKeyTimer.start(1000)

	def rightDown(self):
		self.righttimer = True
		self.rightKeyTimer.start(1000)

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
		self.show()

	def showAfterCuesheetOperation(self):
		self.show()

	def hideAfterResume(self):
		self.hide()

	# FIXME: maybe this code can be optimized 
	def updateCurrentInfo(self):
		text = ""
		if self.currList == "filelist":
			idx = self.filelist.getSelectionIndex()
			r = self.filelist.list[idx]
			text = r[1][7]
			if r[0][1] == True:
				if len(text) < 2:
					text += " "
				if text[:2] != "..":
					text = "/" + text
			self.summaries.setText(text,1)

			idx += 1
			if idx < len(self.filelist.list):
				r = self.filelist.list[idx]
				text = r[1][7]
				if r[0][1] == True:
					text = "/" + text
				self.summaries.setText(text,3)
			else:
				self.summaries.setText(" ",3)

			idx += 1
			if idx < len(self.filelist.list):
				r = self.filelist.list[idx]
				text = r[1][7]
				if r[0][1] == True:
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
				self["currenttext"].setText(os_path.basename(text))

		if self.currList == "playlist":
			t = self.playlist.getSelection()
			if t is None:
				return
			#display current selected entry on LCD
			text = t.getPath()
			text = text.split('/')[-1]
			self.summaries.setText(text,1)
			self["currenttext"].setText(text)
			idx = self.playlist.getSelectionIndex()
			idx += 1
			if idx < len(self.playlist):
				currref = self.playlist.getServiceRefList()[idx]
				text = currref.getPath()
				text = text.split('/')[-1]
				self.summaries.setText(text,3)
			else:
				self.summaries.setText(" ",3)

			idx += 1
			if idx < len(self.playlist):
				currref = self.playlist.getServiceRefList()[idx]
				text = currref.getPath()
				text = text.split('/')[-1]
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
			selection = self["playlist"].getSelection()
			self.changeEntry(self.playlist.getSelectionIndex())

	def showMenu(self):
		menu = []
		if self.currList == "filelist":
			if self.filelist.canDescent():
				menu.append((_("add directory to playlist"), "copydir"))
			else:
				menu.append((_("add files to playlist"), "copyfiles"))
			menu.append((_("switch to playlist"), "playlist"))
		else:
			menu.append((_("switch to filelist"), "filelist"))

			menu.append((_("shuffle playlist"), "shuffle"))

			menu.append((_("delete"), "delete"))
			menu.append((_("clear playlist"), "clear"))
		menu.append((_("hide player"), "hide"));
		menu.append((_("save playlist"), "saveplaylist"));
		menu.append((_("load playlist"), "loadplaylist"));
		menu.append((_("delete saved playlist"), "deleteplaylist"));
		self.session.openWithCallback(self.menuCallback, ChoiceBox, title="", list=menu)

	def menuCallback(self, choice):
		if choice is None:
			return

		if choice[1] == "copydir":
			self.copyDirectory(self.filelist.getSelection()[0])
		elif choice[1] == "copyfiles":
			self.stopEntry()
			self.playlist.clear()
			self.copyDirectory(os_path.dirname(self.filelist.getSelection()[0].getPath()) + "/", recursive = False)
			self.playServiceRefEntry(self.filelist.getServiceRef())
		elif choice[1] == "playlist":
			self.switchToPlayList()
		elif choice[1] == "filelist":
			self.switchToFileList()
		elif choice[1] == "delete":
			if self.playlist.getSelectionIndex() == self.playlist.getCurrentIndex():
				self.stopEntry()
			self.deleteEntry()
		elif choice[1] == "clear":
			self.stopEntry()
			self.playlist.clear()
			self.switchToFileList()
		elif choice[1] == "hide":
			self.hide()
		elif choice[1] == "saveplaylist":
			self.save_playlist()
		elif choice[1] == "loadplaylist":
			self.load_playlist()
		elif choice[1] == "deleteplaylist":
			self.delete_saved_playlist()
		elif choice[1] == "shuffle":
			self.playlist.PlayListShuffle()


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
		self.session.openWithCallback(self.save_playlist2,InputBox, title=_("Please enter filename (empty = use current date)"),windowTitle = _("Save Playlist"))

	def save_playlist2(self, name):
		if name is not None:
			name = name.strip()
			if name == "":
				name = strftime("%y%m%d_%H%M%S")
			name += ".e2pls"
			self.playlistIOInternal.clear()
			for x in self.playlist.list:
				self.playlistIOInternal.addService(ServiceReference(x[0]))
			self.playlistIOInternal.save(resolveFilename(SCOPE_PLAYLIST) + name)

	def load_playlist(self):
		listpath = []
		playlistdir = resolveFilename(SCOPE_PLAYLIST)
		try:
			for i in os_listdir(playlistdir):
				listpath.append((i,playlistdir + i))
		except IOError,e:
			print "Error while scanning subdirs ",e
		self.session.openWithCallback(self.PlaylistSelected, ChoiceBox, title=_("Please select a playlist..."), list = listpath)

	def PlaylistSelected(self,path):
		if path is not None:
			self.clear_playlist()
			self.playlistIOInternal = PlaylistIOInternal()
			list = self.playlistIOInternal.open(path[1])
			if list:
				for x in list:
					self.playlist.addFile(x.ref)
				self.playlist.updateList()

	def delete_saved_playlist(self):
		listpath = []
		playlistdir = resolveFilename(SCOPE_PLAYLIST)
		try:
			for i in os_listdir(playlistdir):
				listpath.append((i,playlistdir + i))
		except IOError,e:
			print "Error while scanning subdirs ",e
		self.session.openWithCallback(self.DeletePlaylistSelected, ChoiceBox, title=_("Please select a playlist to delete..."), list = listpath)

	def DeletePlaylistSelected(self,path):
		if path is not None:
			self.delname = path[1]
			self.session.openWithCallback(self.deleteConfirmed, MessageBox, _("Do you really want to delete %s?") % (path[1]))

	def deleteConfirmed(self, confirmed):
		if confirmed:
			os_remove(self.delname)

	def clear_playlist(self):
		self.stopEntry()
		self.playlist.clear()
		self.switchToFileList()

	def copyDirectory(self, directory, recursive = True):
		print "copyDirectory", directory
		filelist = FileList(directory, useServiceRef = True, isTop = True)

		for x in filelist.getFileList():
			if x[0][1] == True: #isDir
				if recursive:
					self.copyDirectory(x[0][0])
			else:
				self.playlist.addFile(x[0][0])
		self.playlist.updateList()

	def copyFile(self):
		if self.filelist.getServiceRef().type == 4098: # playlist
			ServiceRef = self.filelist.getServiceRef()
			extension = ServiceRef.getPath()[ServiceRef.getPath().rfind('.') + 1:]
			print "extension:", extension
			if self.playlistparsers.has_key(extension):
				playlist = self.playlistparsers[extension]()
				list = playlist.open(ServiceRef.getPath())
				for x in list:
					self.playlist.addFile(x.ref)
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

	def previousEntry(self):
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

	def playEntry(self):
		if len(self.playlist.getServiceRefList()):
			currref = self.playlist.getServiceRefList()[self.playlist.getCurrentIndex()]
			if self.session.nav.getCurrentlyPlayingServiceReference() is None or currref != self.session.nav.getCurrentlyPlayingServiceReference():
				self.session.nav.playService(self.playlist.getServiceRefList()[self.playlist.getCurrentIndex()])
				info = eServiceCenter.getInstance().info(currref)
				description = info and info.getInfoString(currref, iServiceInformation.sDescription) or ""
				self["title"].setText(description)
				# display just playing musik on LCD
				idx = self.playlist.getCurrentIndex()
				currref = self.playlist.getServiceRefList()[idx]
				text = currref.getPath()
				text = text.split('/')[-1]
				text = ">"+text
				ext = text[-3:].lower()

				# FIXME: the information if the service contains video (and we should hide our window) should com from the service instead 
				if ext not in ["mp3", "wav", "ogg"]:
					self.hide()
				self.summaries.setText(text,1)

				# get the next two entries
				idx += 1
				if idx < len(self.playlist):
					currref = self.playlist.getServiceRefList()[idx]
					text = currref.getPath()
					text = text.split('/')[-1]
					self.summaries.setText(text,3)
				else:
					self.summaries.setText(" ",3)

				idx += 1
				if idx < len(self.playlist):
					currref = self.playlist.getServiceRefList()[idx]
					text = currref.getPath()
					text = text.split('/')[-1]
					self.summaries.setText(text,4)
				else:
					self.summaries.setText(" ",4)
			else:
				idx = self.playlist.getCurrentIndex()
				currref = self.playlist.getServiceRefList()[idx]
				text = currref.getPath()
				ext = text[-3:].lower()
				if ext not in ["mp3", "wav", "ogg"]:
					self.hide()
			self.unPauseService()

	def updatedSeekState(self):
		if self.seekstate == self.SEEK_STATE_PAUSE:
			self.playlist.pauseFile()
		elif self.seekstate == self.SEEK_STATE_PLAY:
			self.playlist.playFile()
		elif self.seekstate in ( self.SEEK_STATE_FF_2X,
								 self.SEEK_STATE_FF_4X,
								 self.SEEK_STATE_FF_8X,
								 self.SEEK_STATE_FF_16X,
								 self.SEEK_STATE_FF_32X,
								 self.SEEK_STATE_FF_48X,
								 self.SEEK_STATE_FF_64X,
								 self.SEEK_STATE_FF_128X):
			self.playlist.forwardFile()
		elif self.seekstate in ( self.SEEK_STATE_BACK_8X,
								 self.SEEK_STATE_BACK_16X,
								 self.SEEK_STATE_BACK_32X,
								 self.SEEK_STATE_BACK_48X,
								 self.SEEK_STATE_BACK_64X,
								 self.SEEK_STATE_BACK_128X):
			self.playlist.rewindFile()

	def pauseEntry(self):
		self.pauseService()
		self.show()

	def stopEntry(self):
		self.playlist.stopFile()
		self.session.nav.playService(None)
		self.updateMusicInformation(clear=True)
		self.show()

	def unPauseService(self):
		self.setSeekState(self.SEEK_STATE_PLAY)


class MediaPlayerLCDScreen(Screen):
	skin = """
	<screen position="0,0" size="132,64" title="LCD Text">
		<widget name="text1" position="4,0" size="132,35" font="Regular;16"/>
		<widget name="text3" position="4,36" size="132,14" font="Regular;10"/>
		<widget name="text4" position="4,49" size="132,14" font="Regular;10"/>
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session)
		self["text1"] = Label("Mediaplayer")
		self["text3"] = Label("")
		self["text4"] = Label("")

	def setText(self, text, line):
		print "lcd set text:", text, line
		if len(text) > 10:
			if text[-4:] == ".mp3":
				text = text[:-4]
		textleer = "    "
		text = text + textleer*10
		if line == 1:
			self["text1"].setText(text)
		elif line == 3:
			self["text3"].setText(text)
		elif line == 4:
			self["text4"].setText(text)

def main(session, **kwargs):
        session.open(MediaPlayer)

def menu(menuid, **kwargs):
	if menuid == "mainmenu":
		return [(_("Media player"), main)]
	return []

def filescan_open(list, session, **kwargs):
	from enigma import eServiceReference

	mp = session.open(MediaPlayer)

	mp.switchToPlayList()
	for file in list:
		ref = eServiceReference(4097, 0, file)
		mp.playlist.addFile(ref)

	# TODO: rather play first than last file?
	mp.playServiceRefEntry(ref)
	mp.playlist.updateList()

def filescan(**kwargs):
	# we expect not to be called if the MediaScanner plugin is not available,
	# thus we don't catch an ImportError exception here
	from Plugins.Extensions.MediaScanner.plugin import Scanner, ScanPath
	return [
		Scanner(mimetypes = ["video/mpeg"],
			paths_to_scan =
				[
					ScanPath(path = "", with_subdirs = False),
				],
			name = "Movie",
			description = "View Movies...",
			openfnc = filescan_open,
		),
		Scanner(mimetypes = ["audio/mpeg", "audio/x-wav", "application/ogg"],
			paths_to_scan =
				[
					ScanPath(path = "", with_subdirs = False),
				],
			name = "Music",
			description = "Play Music...",
			openfnc = filescan_open,
		)
	]

from Plugins.Plugin import PluginDescriptor
def Plugins(**kwargs):
	return [
		PluginDescriptor(name = "MediaPlayer", description = "Play back media files", where = PluginDescriptor.WHERE_SETUP, fnc = menu),
		PluginDescriptor(name = "MediaPlayer", where = PluginDescriptor.WHERE_FILESCAN, fnc = filescan)
	]
