from Plugins.Plugin import PluginDescriptor

import os
from enigma import gFont, eTimer, eConsoleAppContainer, ePicLoad, getDesktop, eServiceReference, iPlayableService, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER

from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.InfoBarGenerics import InfoBarNotifications

from Components.Button import Button
from Components.Label import Label
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.ActionMap import NumberActionMap, ActionMap
from Components.config import config, ConfigSelection, getConfigListEntry, ConfigText, ConfigDirectory, ConfigYesNo, ConfigSelection
from Components.FileList import FileList, FileEntryComponent
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap, MovingPixmap
from Components.AVSwitch import AVSwitch
from Components.ServiceEventTracker import ServiceEventTracker
from Components.MultiContent import MultiContentEntryText

from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS

EXTENSIONS = {
	".m4a" : "music",
	".mp2" : "music",
	".mp3" : "music",
	".wav" : "music",
	".ogg" : "music",
	".flac": "music",
	".ts"  : "movie",
	".avi" : "movie",
	".divx": "movie",
	".m4v" : "movie",
	".mpg" : "movie",
	".mpeg": "movie",
	".mkv" : "movie",
	".mp4" : "movie",
	".mov" : "movie",
	".m2ts": "movie",
	".wmv" : "movie",
	".jpg" : "picture",
	".jpeg": "picture",
	".png" : "picture",
	".bmp" : "picture",
	".m3u" : "stream",
	".m3u8": "stream",
}

DLNA_CONFIG_SLIDESHOW       = 10000
DLNA_CONFIG_DEVICE_REFRESH  = 10000
DLNA_CONFIG_ROOT_DIR        = '/media/upnp/'
DLNA_CONFIG_CLIENT_CONFNAME = "/etc/djmount.conf"


class DLNAFileList(FileList):
	def __init__(self, directory):
		self.rootDir = directory
		inhibitDirs = ["/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sbin", "/sys", "/usr", "/var"]
		matchingPattern = "(?i)^.*\.(m4a|mp2|mp3|wav|ogg|flac|ts|avi|divx|m4v|mpg|mpeg|mkv|mp4|mov|m2ts|jpg|jpeg|png|bmp)"
		FileList.__init__(self, directory=directory, matchingPattern=matchingPattern, showDirectories=True, showFiles=True, inhibitMounts=[], inhibitDirs=inhibitDirs, isTop=True)

	def changeTop(self):
		parent = ""
		directoryItem = self.rootDir[:-1].split('/')
		directoryItem.pop()
		for di in directoryItem:
			parent += di+'/'
		self.changeDir(self.rootDir, select=parent)

	def changeParent(self):
		i, parent, grandParent = 0, "", ""
		currentDir = self.getCurrentDirectory()
		if currentDir == self.rootDir:
			return False
		directoryItem = currentDir[:-1].split('/')
		directoryItem.pop()
		for di in directoryItem:
			parent += di+'/'
		if len(directoryItem) > 0:
			directoryItem.pop()
		for di in directoryItem:
			grandParent += di+'/'
		if parent == grandParent:
			return False
		self.changeDir(parent, select=grandParent)
		return True

	def getFileType(self):
		try:
			selectedFileName = self.getSelection()[0]
			splitedFileName  = os.path.splitext(selectedFileName)
			return EXTENSIONS[splitedFileName[1]]
		except: pass
		return 'unknown'

class DLNAFileBrowser(Screen):
	skin = 	"""
		<screen name="DLNAFileBrowser" position="center,center" size="600,350" title="File Browser">
			<ePixmap pixmap="skin_default/buttons/red.png" position="5,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="155,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="305,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="455,0" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="5,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="155,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_yellow" render="Label" position="305,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_blue" render="Label" position="455,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="#ffffff" transparent="1" />

			<widget name="directory" position="10,45" size="600,40" valign="center" font="Regular;20" />
			<widget name="filelist" position="0,100" zPosition="1" size="560,250" scrollbarMode="showOnDemand"/>
		</screen>
		<!--
		<screen name="DLNAFileBrowser" position="center,90" size="1000,580" title="File Browser">
			<ePixmap pixmap="skin_default/buttons/red.png" position="55,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="305,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="555,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="805,0" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="55,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="305,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_yellow" render="Label" position="555,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_blue" render="Label" position="805,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="#ffffff" transparent="1" />

			<widget name="directory" position="10,60" size="980,22" valign="center" font="Regular;22" />
			<widget name="filelist" position="0,100" zPosition="1" size="1000,480" scrollbarMode="showOnDemand"/>
		</screen>
		-->
		"""
	def __init__(self, session, directory):
		self.session = session
		Screen.__init__(self, session)
		
		self["actions"]  = ActionMap(["WizardActions", "DirectionActions", "ColorActions", "EPGSelectActions"], {
			"back"  : self.keyCancel,
			"left"  : self.keyLeft,
			"right" : self.keyRight,
			"up"    : self.keyUp,
			"down"  : self.keyDown,
			"ok"    : self.keyOK,
			"green" : self.keyGreen,
			"red"   : self.keyCancel,
			"yellow": self.keyYellow,
			"blue"  : self.keyBlue
		}, -1)

		self["directory"]  = Label()
		self["key_red"]    = StaticText(_("Show Device"))
		self["key_green"]  = StaticText(_(" "))
		self["key_yellow"] = StaticText(_("Up"))
		self["key_blue"]   = StaticText(_("Top"))
		self["filelist"]   = DLNAFileList(directory)

		self.onLayoutFinish.append(self.layoutFinished)

		self.showCB = {
			'movie'   : self.showMovie,
			'music'   : self.showMusic,
			'picture' : self.showPicture,
			'stream'  : self.showStream,
			'unknown' : self.showUnknown,
		}

	def layoutFinished(self):
		self.updateDirectory()

	def keyCancel(self):
		self.close()

	def keyBlue(self):
		self["filelist"].changeTop()
		self.updateDirectory()

	def keyGreen(self):
		print "not implements!!"

	def keyYellow(self):
		self["filelist"].changeParent()
		self.updateDirectory()

	def keyUp(self):
		self["filelist"].up()
		self.updateDirectory()

	def keyDown(self):
		self["filelist"].down()
		self.updateDirectory()

	def keyLeft(self):
		self["filelist"].pageUp()
		self.updateDirectory()

	def keyRight(self):
		self["filelist"].pageDown()
		self.updateDirectory()

	def keyOK(self):
		try:
			if self["filelist"].canDescent():
				self["filelist"].descent()
				self.updateDirectory()
				return
		except:	return
		fileType = self["filelist"].getFileType()
		self.showCB[fileType]()

	def updateDirectory(self):
		directory = self["filelist"].getSelection()[0]
		if directory is None or directory.strip() == '':
			directory = "Empty Directory!!"
		self["directory"].setText(directory)

	def showMovie(self):
		from Plugins.Extensions.MediaPlayer.plugin import MediaPlayer
		self.beforeService = self.session.nav.getCurrentlyPlayingServiceReference()
		path = self["filelist"].getCurrentDirectory() + self["filelist"].getFilename()
		mp = self.session.open(MediaPlayer)
		mp.callback = self.cbShowMovie
		mp.playlist.clear()
		mp.savePlaylistOnExit = False
		mp.playlist.addFile(eServiceReference(4097, 0, path))
		mp.changeEntry(0)
		mp.switchToPlayList()
		
	def showPicture(self):
		self.session.openWithCallback(self.cbShowPicture, 
					      DLNAImageViewer, 
					      self["filelist"].getFileList(), 
					      self["filelist"].getSelectionIndex(), 
					      self["filelist"].getCurrentDirectory())

	def showMusic(self):
		self.showMovie()

	def showStream(self):
		path = self["filelist"].getCurrentDirectory() + self["filelist"].getFilename()
		self.beforeService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.openWithCallback(self.cbShowMovie, 
					      DLNAStreamPlayer, 
					      eServiceReference(4097, 0, path), 
					      self.beforeService)

	def showUnknown(self):
		message = "Can't play selected file. It is unknown file extension."
		self.session.open(MessageBox, message, type=MessageBox.TYPE_INFO)

	def cbShowMovie(self, data=None):
		if self.beforeService is not None:
			self.session.nav.playService(self.beforeService)
			self.beforeService = None

	def cbShowPicture(self, idx=0):
		if idx > 0: self["filelist"].moveToIndex(idx)

class DLNAStreamPlayer(Screen, InfoBarNotifications):
	skin = 	"""
		<screen name="DLNAStreamPlayer" flags="wfNoBorder" position="center,620" size="455,53" title="DLNAStreamPlayer" backgroundColor="transparent">
			<ePixmap pixmap="skin_default/mp_wb_background.png" position="0,0" zPosition="-1" size="455,53" />
			<ePixmap pixmap="skin_default/icons/mp_wb_buttons.png" position="40,23" size="30,13" alphatest="on" />

			<widget source="session.CurrentService" render="PositionGauge" position="80,25" size="220,10" zPosition="2" pointer="skin_default/position_pointer.png:540,0" transparent="1" foregroundColor="#20224f">
				<convert type="ServicePosition">Gauge</convert>
			</widget>
			
			<widget source="session.CurrentService" render="Label" position="310,20" size="50,20" font="Regular;18" halign="center" valign="center" backgroundColor="#4e5a74" transparent="1" >
				<convert type="ServicePosition">Position</convert>
			</widget>
			<widget name="sidebar" position="362,20" size="10,20" font="Regular;18" halign="center" valign="center" backgroundColor="#4e5a74" transparent="1" />
			<widget source="session.CurrentService" render="Label" position="374,20" size="50,20" font="Regular;18" halign="center" valign="center" backgroundColor="#4e5a74" transparent="1" > 
				<convert type="ServicePosition">Length</convert>
			</widget>
		</screen>
		"""
	PLAYER_IDLE	= 0
	PLAYER_PLAYING 	= 1
	PLAYER_PAUSED 	= 2

	def __init__(self, session, service, lastservice):
		Screen.__init__(self, session)
		InfoBarNotifications.__init__(self)

		self.session     = session
		self.service     = service
		self.lastservice = lastservice
		self["actions"] = ActionMap(["OkCancelActions", "InfobarSeekActions", "MediaPlayerActions", "MovieSelectionActions"], {
			"ok": self.doInfoAction,
			"cancel": self.doExit,
			"stop": self.doExit,
			"playpauseService": self.playpauseService,
		}, -2)
		self["sidebar"] = Label(_("/"))

		self.__event_tracker = ServiceEventTracker(screen = self, eventmap = {
			iPlayableService.evSeekableStatusChanged: self.__seekableStatusChanged,
			iPlayableService.evStart: self.__serviceStarted,
			iPlayableService.evEOF: self.__evEOF,
		})

		self.hidetimer = eTimer()
		self.hidetimer.timeout.get().append(self.doInfoAction)

		self.state = self.PLAYER_PLAYING
		self.lastseekstate = self.PLAYER_PLAYING
		self.__seekableStatusChanged()
	
		self.onClose.append(self.__onClose)
		self.doPlay()

	def __onClose(self):
		self.session.nav.stopService()

	def __seekableStatusChanged(self):
		service = self.session.nav.getCurrentService()
		if service is not None:
			seek = service.seek()
			if seek is None or not seek.isCurrentlySeekable():
				self.setSeekState(self.PLAYER_PLAYING)

	def __serviceStarted(self):
		self.state = self.PLAYER_PLAYING
		self.__seekableStatusChanged()

	def __evEOF(self):
		self.doExit()

	def __setHideTimer(self):
		self.hidetimer.start(5000)

	def doExit(self):
		list = ((_("Yes"), "y"), (_("No"), "n"),)
		self.session.openWithCallback(self.cbDoExit, ChoiceBox, title=_("Stop playing this movie?"), list = list)

	def cbDoExit(self, answer):
		answer = answer and answer[1]
		if answer == "y":
			self.close()

	def setSeekState(self, wantstate):
		service = self.session.nav.getCurrentService()
		if service is None:
			print "No Service found"
			return

		pauseable = service.pause()
		if pauseable is not None:
			if wantstate == self.PLAYER_PAUSED:
				pauseable.pause()
				self.state = self.PLAYER_PAUSED
				if not self.shown:
					self.hidetimer.stop()
					self.show()
			elif wantstate == self.PLAYER_PLAYING:
				pauseable.unpause()
				self.state = self.PLAYER_PLAYING
				if self.shown:
					self.__setHideTimer()
		else:
			self.state = self.PLAYER_PLAYING

	def doInfoAction(self):
		if self.shown:
			self.hidetimer.stop()
			self.hide()
		else:
			self.show()
			if self.state == self.PLAYER_PLAYING:
				self.__setHideTimer()

	def doPlay(self):
		if self.state == self.PLAYER_PAUSED:
			if self.shown:
				self.__setHideTimer()	
		self.state = self.PLAYER_PLAYING
		self.session.nav.playService(self.service)
		if self.shown:
			self.__setHideTimer()

	def playpauseService(self):
		if self.state == self.PLAYER_PLAYING:
			self.setSeekState(self.PLAYER_PAUSED)
		elif self.state == self.PLAYER_PAUSED:
			self.setSeekState(self.PLAYER_PLAYING)

class DLNAImageViewer(Screen):
	s, w, h = 30, getDesktop(0).size().width(), getDesktop(0).size().height()
	skin = """
		<screen position="0,0" size="%d,%d" flags="wfNoBorder">
			<eLabel position="0,0" zPosition="0" size="%d,%d" backgroundColor="#00000000" />
			<widget name="image" position="%d,%d" size="%d,%d" zPosition="1" alphatest="on" />
			<widget name="status" position="%d,%d" size="20,20" zPosition="2" pixmap="skin_default/icons/record.png" alphatest="on" />
			<widget name="icon" position="%d,%d" size="20,20" zPosition="2" pixmap="skin_default/icons/ico_mp_play.png"  alphatest="on" />
			<widget source="message" render="Label" position="%d,%d" size="%d,25" font="Regular;20" halign="left" foregroundColor="#0038FF48" zPosition="2" noWrap="1" transparent="1" />
		</screen>
		""" % (w, h, w, h, s, s, w-(s*2), h-(s*2), s+5, s+2, s+25, s+2, s+45, s, w-(s*2)-50)

	def __init__(self, session, fileList, index, path):
		Screen.__init__(self, session)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MovieSelectionActions"], {
			"cancel": self.keyCancel,
			"left"  : self.keyLeft,
			"right" : self.keyRight,
			"blue"  : self.keyBlue,
			"yellow": self.keyYellow,
		}, -1)

		self["icon"]    = Pixmap()
		self["image"]   = Pixmap()
		self["status"]  = Pixmap()
		self["message"] = StaticText(_("Please wait, Loading image."))

		self.fileList     = []
		self.currentImage = []

		self.lsatIndex      = index
		self.fileListLen    = 0
		self.currentIndex   = 0
		self.directoryCount = 0

		self.displayNow = True

		self.makeFileList(fileList, path)

		self.pictureLoad = ePicLoad()
		self.pictureLoad.PictureData.get().append(self.finishDecode)

		self.slideShowTimer = eTimer()
		self.slideShowTimer.callback.append(self.cbSlideShow)

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		if self.fileListLen >= 0:
			self.setPictureLoadPara()

	def keyLeft(self):
		self.currentImage = []
		self.currentIndex = self.lsatIndex
		self.currentIndex -= 1
		if self.currentIndex < 0:
			self.currentIndex = self.fileListLen
		self.startDecode()
		self.displayNow = True

	def keyRight(self):
		self.displayNow = True
		self.showPicture()

	def keyYellow(self):
		if self.fileListLen < 0:
			return
		from Plugins.Extensions.PicturePlayer.plugin import Pic_Exif
		self.session.open(Pic_Exif, self.pictureLoad.getInfo(self.fileList[self.lsatIndex]))

	def keyBlue(self):
		if self.slideShowTimer.isActive():
			self.slideShowTimer.stop()
			self["icon"].hide()
		else:
			global DLNA_CONFIG_SLIDESHOW
			self.slideShowTimer.start(DLNA_CONFIG_SLIDESHOW)
			self["icon"].show()
			self.keyRight()

	def keyCancel(self):
		del self.pictureLoad
		self.close(self.lsatIndex + self.directoryCount)

	def setPictureLoadPara(self):
		sc = AVSwitch().getFramebufferScale()
		self.pictureLoad.setPara([self["image"].instance.size().width(), 
					  self["image"].instance.size().height(), 
					  sc[0],
					  sc[1],
					  0,
					  int(config.pic.resize.value),
					  '#00000000'])
		self["icon"].hide()
		if config.pic.infoline.value == False:
			self["message"].setText("")
		self.startDecode()

	def makeFileList(self, fileList, path):
		for x in fileList:
			l = len(fileList[0])
			if l == 3:
				if x[0][1] == False:
					self.fileList.append(path + x[0][0])
				else:	self.directoryCount += 1
			elif l == 2:
				if x[0][1] == False:
					self.fileList.append(x[0][0])
				else:	self.directoryCount += 1
			else:	self.fileList.append(x[4])
		
		self.currentIndex = self.lsatIndex - self.directoryCount
		if self.currentIndex < 0:
			self.currentIndex = 0
		self.fileListLen = len(self.fileList) - 1

	def showPicture(self):
		if self.displayNow and len(self.currentImage):
			self.displayNow = False
			self["message"].setText(self.currentImage[0])
			self.lsatIndex = self.currentImage[1]
			self["image"].instance.setPixmap(self.currentImage[2].__deref__())
			self.currentImage = []

			self.currentIndex += 1
			if self.currentIndex > self.fileListLen:
				self.currentIndex = 0
			self.startDecode()

	def finishDecode(self, picInfo=""):
		self["status"].hide()
		ptr = self.pictureLoad.getData()
		if ptr != None:
			text = ""
			try:
				text = picInfo.split('\n',1)
				text = "(" + str(self.currentIndex+1) + "/" + str(self.fileListLen+1) + ") " + text[0].split('/')[-1]
			except:
				pass
			self.currentImage = []
			self.currentImage.append(text)
			self.currentImage.append(self.currentIndex)
			self.currentImage.append(ptr)
			self.showPicture()

	def startDecode(self):
		self.pictureLoad.startDecode(self.fileList[self.currentIndex])
		self["status"].show()

	def cbSlideShow(self):
		print "slide to next Picture index=" + str(self.lsatIndex)
		if config.pic.loop.value==False and self.lsatIndex == self.fileListLen:
			self.PlayPause()
		self.displayNow = True
		self.showPicture()

class TaskManager:
	def __init__(self):
		self.taskIdx = 0
		self.taskList = []
		self.gTaskInstance = None
		self.occurError = False
		self.cbSetStatusCB = None

	def append(self, command, cbDataFunc, cbCloseFunc):
		self.taskList.append([command+'\n', cbDataFunc, cbCloseFunc])

	def dump(self):
		print "############### TASK ###############"
		print "Current Task Index :", self.taskIdx
		print "Current Task Instance :", self.gTaskInstance
		print "Occur Error :", self.occurError
		print "Task List:\n", self.taskList
		print "####################################"

	def error(self):
		print "[DLNAClient Plugin] Info >> set task error!!"
		self.occurError = True

	def reset(self):
		self.taskIdx = 0
		self.gTaskInstance = None
		self.occurError = False

	def clean(self):
		self.reset()
		self.taskList = []
		self.cbSetStatusCB = None
		print "clear task!!"

	def index(self):
		self.taskIdx

	def setStatusCB(self, cbfunc):
		self.cbSetStatusCB = cbfunc
		
	def next(self):
		if self.taskIdx >= len(self.taskList) or self.occurError:
			print "[DLNAClient Plugin] Info >> can't run task!!"
			return False
		command     = self.taskList[self.taskIdx][0]
		cbDataFunc  = self.taskList[self.taskIdx][1]
		cbCloseFunc = self.taskList[self.taskIdx][2]

		self.gTaskInstance = eConsoleAppContainer()
		if cbDataFunc is not None:
			self.gTaskInstance.dataAvail.append(cbDataFunc)
		if cbCloseFunc is not None:
			self.gTaskInstance.appClosed.append(cbCloseFunc)
		if self.cbSetStatusCB is not None:
			self.cbSetStatusCB(self.taskIdx)

		print "[DLNAClient Plugin] Info >> prepared command : %s"%(command)
		self.gTaskInstance.execute(command)
		self.taskIdx += 1
		return True

class DLNAClientConfig(ConfigListScreen, Screen):
	skin=   """
		<screen position="center,center" size="600,350" title="Mini DLNA Runcher">
			<ePixmap pixmap="skin_default/buttons/red.png" position="5,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="155,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="305,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="455,0" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="5,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="155,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_yellow" render="Label" position="305,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_blue" render="Label" position="455,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="#ffffff" transparent="1" />

			<widget name="config" position="0,50" size="600,200" scrollbarMode="showOnDemand" />
		</screen>
		"""
	def __init__(self, session): 
                self.session = session
		Screen.__init__(self, session)

		self.menulist  = []
		self.oldConfig = {}
		ConfigListScreen.__init__(self, self.menulist)

		global DLNA_CONFIG_CLIENT_CONFNAME
		self.configFileName = DLNA_CONFIG_CLIENT_CONFNAME
		self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "WizardActions", "ColorActions", "SetupActions", ], {
			"red"    : self.keyExit,
			"green"  : self.keyOK,
			"cancel" : self.keyExit,
			"ok"     : self.keyOK,
                }, -2)
		self["key_red"]     = StaticText(_("Exit"))
		self["key_green"]   = StaticText(_("Save"))
		self["key_yellow"]  = StaticText(_(" "))
		self["key_blue"]    = StaticText(_(" "))

		self.makeMenuList()

	def keyExit(self):
		self.close(None, None, None)

	def keyOK(self):
		self.writeConfigFile()
		#self.close(self.menuItemRefresh.value, self.menuItemRootDir.value)
		self.close(self.menuItemRefresh.value, None, self.menuItemSlideshow.value)

	def makeMenuList(self):
		self.readConfigFile()
		#self.menuItemRootDir   = ConfigText(default=self.oldConfig.get('rootdir'))
		self.menuItemRefresh   = ConfigSelection(default=self.oldConfig.get('refresh'), choices = [("5", _("5")), ("10", _("10")), ("15", _("15"))])
		self.menuItemSlideshow = ConfigSelection(default=self.oldConfig.get('slideshow'), choices = [("5", _("5")), ("10", _("10")), ("15", _("15")), ("20", _("20"))])

		#self.menuEntryRootDir   = getConfigListEntry(_("Mount Point"), self.menuItemRootDir)
		self.menuEntryRefresh   = getConfigListEntry(_("DeviceList Refresh Interval"), self.menuItemRefresh)
		self.menuEntrySlideshow = getConfigListEntry(_("Slideshow Interval"), self.menuItemSlideshow)
		self.resetMenuList()

	def resetMenuList(self):
		self.menulist = []
		#self.menulist.append(self.menuEntryRootDir)
		self.menulist.append(self.menuEntryRefresh)
		self.menulist.append(self.menuEntrySlideshow)
		self["config"].list = self.menulist
		self["config"].l.setList(self.menulist)

	def writeConfigFile(self):
		def configDataAppend(origin, key, value):
			if key.strip() != '' and value.strip() != '':
				origin += "%s=%s\n" % (key,value)
			return origin
		configString = ""
		#configString = configDataAppend(configString, "rootdir", self.menuItemRootDir.value)
		configString = configDataAppend(configString, "refresh", self.menuItemRefresh.value)
		configString = configDataAppend(configString, "slideshow", self.menuItemSlideshow.value)
		print configString
		confFile = file(self.configFileName, 'w')
		confFile.write(configString)
		confFile.close()

	def readConfigFile(self):
		def setDefault(key, default):
			try:
				value = self.oldConfig.get(key)
				if value == None or value.strip() == '':
					self.oldConfig[key] = default
			except: self.oldConfig[key] = default

		self.oldConfig = {}
		if not os.path.exists(self.configFileName):
			#setDefault('rootdir', '/media/upnp/')
			setDefault('refresh', '10')
			setDefault('slideshow', '10')
			return
		for line in file(self.configFileName).readlines():
			line = line.strip()
			if line == '' or line[0] == '#':
				continue
			try:
				i   = line.find('=')
				k,v = line[:i],line[i+1:]
				self.oldConfig[k] = v
			except : pass

		#setDefault('rootdir', '/media/upnp/')
		setDefault('refresh', '10')
		setDefault('slideshow', '10')
		print "Current Config : ", self.oldConfig


class DLNADeviceBrowser(Screen):
	skin = 	"""
		<screen name="DLNADeviceBrowser" position="center,center" size="600,350" title="Device Browser">
			<ePixmap pixmap="skin_default/buttons/red.png" position="5,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="155,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="305,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="455,0" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="5,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="155,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_yellow" render="Label" position="305,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_blue" render="Label" position="455,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="#ffffff" transparent="1" />

			<widget name="devicelist" position="0,50" size="600,300" backgroundColor="#000000" zPosition="10" scrollbarMode="showOnDemand" />
	        </screen>
		"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self["actions"]  = ActionMap(["OkCancelActions", "ShortcutActions", "WizardActions", "ColorActions", "SetupActions", "NumberActions", "MenuActions"], {
			"ok"    : self.keyOK,
			"cancel": self.keyCancel,
			"red"   : self.keyCancel,
			"green" : self.keyGreen,
			"yellow": self.keyYellow,
			"blue"  : self.keyBlue,
		}, -1)

		global DLNA_CONFIG_CLIENT_CONFNAME
		self.configFileName = DLNA_CONFIG_CLIENT_CONFNAME
		self["key_red"]    = StaticText(_("Exit"))
		self["key_green"]  = StaticText(_("Start"))
		self["key_yellow"] = StaticText(_("Setting"))
		self["key_blue"]   = StaticText(_("Reload Device"))

		#self["devicelist"] = MenuList(self.setListOnView())
		self["devicelist"] = MenuList([])
		self.onLayoutFinish.append(self.layoutFinished)

		self.initConfig()
		self.taskManager = TaskManager()

		self.toggleGreenButtonTimer = eTimer()
		self.toggleGreenButtonTimer.timeout.get().append(self.cbToggleGreenButton)

		self.deviceListRefreshTimer = eTimer()
		self.deviceListRefreshTimer.timeout.get().append(self.cbDeviceListRefresh)
		global DLNA_CONFIG_DEVICE_REFRESH
		self.deviceListRefreshTimer.start(DLNA_CONFIG_DEVICE_REFRESH)

	def layoutFinished(self):
		if not os.path.exists('/media/upnp'):
			os.system('mkdir -p /media/upnp')
		self.updateGUI()
		if self["key_green"].getText() == 'Start':
			global DLNA_CONFIG_DEVICE_REFRESH
			self.deviceListRefreshTimer.start(DLNA_CONFIG_DEVICE_REFRESH)

	def keyYellow(self):
		self.deviceListRefreshTimer.stop()
		self.session.openWithCallback(self.cbConfigClose, DLNAClientConfig)

	def keyGreen(self):
		global DLNA_CONFIG_ROOT_DIR
		if self["key_green"].getText() == 'Stop':
			cmd = 'fusermount -u %s'%(DLNA_CONFIG_ROOT_DIR)
			self.taskManager.append(cmd, self.cbPrintAvail, self.cbPrintClose)
			cmd = 'modprobe -r fuse'
			self.taskManager.append(cmd, self.cbPrintAvail, self.cbStopDone)
			#cmd = 'killall -9 djmount'
			#self.taskManager.append(cmd, self.cbPrintAvail, self.cbTasksDone)
			self["devicelist"].setList([])
		else:
			cmd = 'modprobe fuse'
			self.taskManager.append(cmd, self.cbPrintAvail, self.cbPrintClose)
			cmd = 'djmount -o allow_other -o iocharset=utf8 %s'%(DLNA_CONFIG_ROOT_DIR)
			self.taskManager.append(cmd, self.cbPrintAvail, self.cbStartDone)
		self.taskManager.next()

	def keyCancel(self):
		self.close()

	def keyOK(self):
		global DLNA_CONFIG_ROOT_DIR
		selectedFullPaht = '%s%s/'%(DLNA_CONFIG_ROOT_DIR, self["devicelist"].getCurrent()[1])
		self.session.openWithCallback(self.cbDeviceListRefresh, DLNAFileBrowser, selectedFullPaht)
		self.deviceListRefreshTimer.stop()

	def keyBlue(self):
		print "updated device list!!"
		self["devicelist"].setList(self.setListOnView())

	def initConfig(self):
		global DLNA_CONFIG_ROOT_DIR
		global DLNA_CONFIG_SLIDESHOW
		global DLNA_CONFIG_DEVICE_REFRESH
		if not os.path.exists(self.configFileName):
			DLNA_CONFIG_ROOT_DIR = '/media/upnp/'
			DLNA_CONFIG_DEVICE_REFRESH = 10000
			DLNA_CONFIG_SLIDESHOW = 10000
			print "config : [%s][%d][%d]"%(DLNA_CONFIG_ROOT_DIR, DLNA_CONFIG_SLIDESHOW, DLNA_CONFIG_DEVICE_REFRESH)
			return
		for line in file(self.configFileName).readlines():
			line = line.strip()
			if line == '' or line[0] == '#':
				continue
			try:
				i   = line.find('=')
				k,v = line[:i],line[i+1:]
				if k == 'rootdir':	DLNA_CONFIG_ROOT_DIR = v
				elif k == 'refresh':	DLNA_CONFIG_DEVICE_REFRESH = int(v)*1000
				elif k == 'slideshow':	DLNA_CONFIG_SLIDESHOW = int(v)*1000
			except : pass
		print "config : [%s][%d][%d]"%(DLNA_CONFIG_ROOT_DIR, DLNA_CONFIG_SLIDESHOW, DLNA_CONFIG_DEVICE_REFRESH)

	def isRunning(self):
		ps_str = os.popen('cat /etc/mtab | grep djmount').read()
		if ps_str.strip() != '':
			return True
		return False

	def updateGUI(self):
		green_btm_str = 'Start'
		if self.isRunning():
			green_btm_str = 'Stop'
		self["key_green"].setText(green_btm_str)
		self.keyBlue()

	def cbConfigClose(self, refresh, rootdir, slideshow):
		global DLNA_CONFIG_ROOT_DIR
		global DLNA_CONFIG_SLIDESHOW
		global DLNA_CONFIG_DEVICE_REFRESH
		try:
			if refresh is not None:
				newRefresh = int(refresh)*1000
				if DLNA_CONFIG_DEVICE_REFRESH != newRefresh:
					DLNA_CONFIG_DEVICE_REFRESH = newRefresh
		except: pass
		try:
			if rootdir is not None:
				if DLNA_CONFIG_ROOT_DIR != rootdir:
					DLNA_CONFIG_ROOT_DIR = rootdir
					print "need restart!!!"
		except: pass
		try:
			if slideshow is not None:
				newSlideshow = int(slideshow)*1000
				if DLNA_CONFIG_SLIDESHOW != newSlideshow:
					DLNA_CONFIG_SLIDESHOW = newSlideshow
		except: pass
		self.deviceListRefreshTimer.start(DLNA_CONFIG_DEVICE_REFRESH)
		print "config : [%s][%d][%d]"%(DLNA_CONFIG_ROOT_DIR, DLNA_CONFIG_SLIDESHOW, DLNA_CONFIG_DEVICE_REFRESH)

	def cbPrintAvail(self, data):
		print data

	def cbPrintClose(self, ret):
		self.taskManager.next()

	def cbStopDone(self, ret):
		self.taskManager.clean()
		self.toggleGreenButtonTimer.start(1000)
		self.deviceListRefreshTimer.stop()

	def cbStartDone(self, ret):
		global DLNA_CONFIG_DEVICE_REFRESH
		self.taskManager.clean()
		self.toggleGreenButtonTimer.start(1000)
		self.deviceListRefreshTimer.start(DLNA_CONFIG_DEVICE_REFRESH)

	def cbToggleGreenButton(self):
		self.toggleGreenButtonTimer.stop()
		self.updateGUI()

	def cbDeviceListRefresh(self):
		global DLNA_CONFIG_DEVICE_REFRESH
		self.deviceListRefreshTimer.start(DLNA_CONFIG_DEVICE_REFRESH)
		self.keyBlue()

	def setListOnView(slelf):
		global DLNA_CONFIG_ROOT_DIR
		items,rootdir = [],DLNA_CONFIG_ROOT_DIR
		deviceList = [ name for name in os.listdir(rootdir) if os.path.isdir(os.path.join(rootdir, name)) ]
		deviceList.sort()
		for d in deviceList:
			if d[0] in ('.', '_'): continue
			items.append((d,d))
		return items

def main(session, **kwargs):
	session.open(DLNADeviceBrowser)
                                                           
def Plugins(**kwargs):
	return PluginDescriptor(name=_("DLNA/uPnP Browser"), description="This is dlna/upnp client using djmount.", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
