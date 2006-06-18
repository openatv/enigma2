from enigma import eTimer, iPlayableService, eServiceCenter, iServiceInformation, eSize
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.Label import Label
from Components.Input import Input
from Components.GUIComponent import *
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.FileList import FileEntryComponent, FileList
from Components.MediaPlayer import PlayList, PlaylistEntryComponent
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, SCOPE_MEDIA, SCOPE_CONFIG
from Components.ServicePosition import ServicePositionGauge
from Screens.ChoiceBox import ChoiceBox
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Playlist import PlaylistIOInternal, PlaylistIOM3U, PlaylistIOPLS
from Screens.InfoBarGenerics import InfoBarSeek
from ServiceReference import ServiceReference
from Screens.ChoiceBox import ChoiceBox

import os

class MediaPlayer(Screen, InfoBarSeek):
	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()

		self.playlistparsers = {}
		self.addPlaylistParser(PlaylistIOM3U, "m3u")
		self.addPlaylistParser(PlaylistIOPLS, "pls")
		self.addPlaylistParser(PlaylistIOInternal, "e2pls")

		self.filelist = FileList(resolveFilename(SCOPE_MEDIA), matchingPattern = "^.*\.(mp3|ogg|ts|wav|wave|m3u|pls|e2pls)", useServiceRef = True)
		self["filelist"] = self.filelist

		self.playlist = PlayList()
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
		
		#self["text"] = Input("1234", maxSize=True, type=Input.NUMBER)

		class MoviePlayerActionMap(NumberActionMap):
			def __init__(self, player, contexts = [ ], actions = { }, prio=0):
				NumberActionMap.__init__(self, contexts, actions, prio)
				self.player = player

			def action(self, contexts, action):
				self.player.show()
				return NumberActionMap.action(self, contexts, action)

		self["actions"] = MoviePlayerActionMap(self, ["OkCancelActions", "DirectionActions", "NumberActions", "MediaPlayerSeekActions"],
		{
			"ok": self.ok,
			"cancel": self.exit,
			
			"right": self.rightDown,
			"rightRepeated": self.doNothing,
			"rightUp": self.rightUp,
			"left": self.leftDown,
			"leftRepeated": self.doNothing,
			"leftUp": self.leftUp,
			
			"up": self.up,
			"upRepeated": self.up,
			"down": self.down,
			"downRepeated": self.down,
			
			"play": self.playEntry,
			"pause": self.pauseEntry,
			"stop": self.stopEntry,
			
			"previous": self.previousEntry,
			"next": self.nextEntry,
			
			"menu": self.showMenu,
			
            "1": self.keyNumberGlobal,
            "2": self.keyNumberGlobal,
            "3": self.keyNumberGlobal,
            "4": self.keyNumberGlobal,
            "5": self.keyNumberGlobal,
            "6": self.keyNumberGlobal,
            "7": self.keyNumberGlobal,
            "8": self.keyNumberGlobal,
            "9": self.keyNumberGlobal,
            "0": self.keyNumberGlobal
        }, -2)

		InfoBarSeek.__init__(self)

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				#iPlayableService.evStart: self.__serviceStarted,
				#iPlayableService.evSeekableStatusChanged: InfoBarSeek.__seekableStatusChanged,

				iPlayableService.evEOF: self.__evEOF,
#				iPlayableService.evSOF: self.__evSOF,
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
		
		self.playlistIOInternal = PlaylistIOInternal()
		list = self.playlistIOInternal.open(resolveFilename(SCOPE_CONFIG, "playlist.e2pls"))
		if list:
			for x in list:
				self.playlist.addFile(x.ref)
			self.playlist.updateList()		
		
	def doNothing(self):
		pass
	
	def exit(self):
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
			self.updateMusicInformation( artist = currPlay.info().getInfoString(iServiceInformation.sArtist),
										 title = currPlay.info().getInfoString(iServiceInformation.sTitle),
										 album = currPlay.info().getInfoString(iServiceInformation.sAlbum),
										 genre = currPlay.info().getInfoString(iServiceInformation.sGenre),
										 clear = True)
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

	def fwdTimerFire(self):
		self.fwdKeyTimer.stop()
		self.fwdtimer = False
		self.nextEntry()
	
	def rwdTimerFire(self):
		self.rwdKeyTimer.stop()
		self.rwdtimer = False
		self.previousEntry()
        
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
    
   	def rightUp(self):
		if self.righttimer:
			self.rightKeyTimer.stop()
			self.righttimer = False
			self[self.currList].pageDown()
			
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

	def updateCurrentInfo(self):
		text = ""
		if self.currList == "filelist":
			if not self.filelist.canDescent():
				text = self.filelist.getServiceRef().getPath()
		if self.currList == "playlist":
			text = self.playlist.getSelection().getPath()
		
		self["currenttext"].setText(os.path.basename(text))
    
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

	def keyNumberGlobal(self, number):
		pass
	
	def showMenu(self):
		menu = []
		if self.currList == "filelist":
			menu.append((_("switch to playlist"), "playlist"))
			if self.filelist.canDescent():
				menu.append((_("add directory to playlist"), "copydir"))
			else:
				menu.append((_("add file to playlist"), "copy"))
		else:
			menu.append((_("switch to filelist"), "filelist"))
			menu.append((_("delete"), "delete"))
			menu.append((_("clear playlist"), "clear"))
		menu.append((_("hide player"), "hide"));
		self.session.openWithCallback(self.menuCallback, ChoiceBox, title="", list=menu)
		
	def menuCallback(self, choice):
		if choice is None:
			return
		
		if choice[1] == "copydir":
			self.copyDirectory(self.filelist.getSelection()[0])
		elif choice[1] == "copy":
			self.copyFile()
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

	def copyDirectory(self, directory):
		filelist = FileList(directory, useServiceRef = True, isTop = True)
		
		for x in filelist.getFileList():
			if x[0][1] == True: #isDir
				self.copyDirectory(x[0][0])
			else:
				self.playlist.addFile(x[0][0])
		self.playlist.updateList()
	
	ADDPLAYLIST = 0
	REPLACEPLAYLIST = 1
	
	def copyFile(self):
		if self.filelist.getServiceRef().type == 4098: # playlist
			list = []
			list.append((_("Add files to playlist"), (self.ADDPLAYLIST, self.filelist.getServiceRef())))
			list.append((_("Replace current playlist"), (self.REPLACEPLAYLIST, self.filelist.getServiceRef())))
			self.session.openWithCallback(self.playlistCallback, ChoiceBox, title=_("You selected a playlist"), list = list)
		else:
			self.playlist.addFile(self.filelist.getServiceRef())
			self.playlist.updateList()
			if len(self.playlist) == 1:
				self.changeEntry(0)

	def addPlaylistParser(self, parser, extension):
		self.playlistparsers[extension] = parser

	def playlistCallback(self, answer):
		if answer is not None:
			extension = answer[1][1].getPath()[answer[1][1].getPath().rfind('.') + 1:]
			print "extension:", extension
			if self.playlistparsers.has_key(extension):
				playlist = self.playlistparsers[extension]()
				if answer[1][0] == self.REPLACEPLAYLIST:
					self.stopEntry()
					self.playlist.clear()
					self.switchToFileList()
				if answer[1][0] == self.REPLACEPLAYLIST or answer[1][0] == self.ADDPLAYLIST:
					list = playlist.open(answer[1][1].getPath())
					for x in list:
						self.playlist.addFile(x.ref)
				

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
	
	def playEntry(self):
		if len(self.playlist.getServiceRefList()):
			currref = self.playlist.getServiceRefList()[self.playlist.getCurrentIndex()]
			if self.session.nav.getCurrentlyPlayingServiceReference() is None or currref != self.session.nav.getCurrentlyPlayingServiceReference():
				self.session.nav.playService(self.playlist.getServiceRefList()[self.playlist.getCurrentIndex()])
				info = eServiceCenter.getInstance().info(currref)
				description = info and info.getInfoString(currref, iServiceInformation.sDescription) or ""
				self["title"].setText(description)
			self.unPauseService()
				
	def updatedSeekState(self):
		if self.seekstate == self.SEEK_STATE_PAUSE:
			self.playlist.pauseFile()
		elif self.seekstate == self.SEEK_STATE_PLAY:
			self.playlist.playFile()
		elif self.seekstate in ( self.SEEK_STATE_FF_2X,
								 self.SEEK_STATE_FF_4X,
								 self.SEEK_STATE_FF_8X,
								 self.SEEK_STATE_FF_32X,
								 self.SEEK_STATE_FF_64X,
								 self.SEEK_STATE_FF_128X):
			self.playlist.forwardFile()
		elif self.seekstate in ( self.SEEK_STATE_BACK_16X,
								 self.SEEK_STATE_BACK_32X,
								 self.SEEK_STATE_BACK_64X,
								 self.SEEK_STATE_BACK_128X,):
			self.playlist.rewindFile()
	
	def pauseEntry(self):
		self.pauseService()
		
	def stopEntry(self):
		self.playlist.stopFile()
		self.session.nav.playService(None)
		self.updateMusicInformation(clear=True)

	def unPauseService(self):
		self.setSeekState(self.SEEK_STATE_PLAY)


    
