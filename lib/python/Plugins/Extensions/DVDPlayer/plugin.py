import os
from os import path as os_path, remove as os_remove, listdir as os_listdir, system
from enigma import eTimer, iPlayableService, iServiceInformation, eServiceReference, iServiceKeys, getDesktop
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.HelpMenu import HelpableScreen
from Screens.InfoBarGenerics import InfoBarSeek, InfoBarPVRState, InfoBarCueSheetSupport, InfoBarShowHide, InfoBarNotifications, InfoBarAudioSelection, InfoBarSubtitleSupport, InfoBarSimpleEventView
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.FileList import FileList
from Components.MenuList import MenuList
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from Components.config import config
from Tools.Directories import pathExists, fileExists
from Components.Harddisk import harddiskmanager

lastpath = ""

detected_DVD = None

class FileBrowser(Screen):

	def __init__(self, session, dvd_filelist = [ ]):
		Screen.__init__(self, session)

		# for the skin: first try FileBrowser_DVDPlayer, then FileBrowser, this allows individual skinning
		self.skinName = ["FileBrowser_DVDPlayer", "FileBrowser" ]

		self.dvd_filelist = dvd_filelist
		if len(dvd_filelist):
			self["filelist"] = MenuList(self.dvd_filelist)
		else:
			global lastpath
			if lastpath is not None:
				currDir = lastpath + "/"
			else:
				currDir = "/media/dvd/"
			if not pathExists(currDir):
				currDir = "/media/"
			if lastpath == "":  # 'None' is magic to start at the list of mountpoints
				currDir = None

			inhibitDirs = ["/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/proc", "/sbin", "/share", "/sys", "/tmp", "/usr", "/var"]
			self.filelist = FileList(currDir, matchingPattern = "(?i)^.*\.(iso|img)", useServiceRef = True)
			self["filelist"] = self.filelist

		self["FilelistActions"] = ActionMap(["SetupActions"],
			{
				"save": self.ok,
				"ok": self.ok,
				"cancel": self.exit
			})
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("DVD File Browser"))

	def ok(self):
		if len(self.dvd_filelist):
			print "OK " + self["filelist"].getCurrent()
			self.close(self["filelist"].getCurrent())
		else:
			global lastpath
			filename = self["filelist"].getFilename()
			if filename is not None:
				if filename.upper().endswith("VIDEO_TS/"):
					print "dvd structure found, trying to open..."
					dvdpath = filename[0:-9]
					lastpath = (dvdpath.rstrip("/").rsplit("/",1))[0]
					print "lastpath video_ts/=", lastpath
					self.close(dvdpath)
					return
			if self["filelist"].canDescent(): # isDir
				self["filelist"].descent()
				pathname = self["filelist"].getCurrentDirectory() or ""
				if fileExists(pathname+"VIDEO_TS.IFO"):
					print "dvd structure found, trying to open..."
					lastpath = (pathname.rstrip("/").rsplit("/",1))[0]
					print "lastpath video_ts.ifo=", lastpath
					self.close(pathname)
				if fileExists(pathname+"VIDEO_TS/VIDEO_TS.IFO"):
					print "dvd structure found, trying to open..."
					lastpath = (pathname.rstrip("/").rsplit("/",1))[0]
					print "lastpath video_ts.ifo=", lastpath
					pathname += "VIDEO_TS"
					self.close(pathname)
			else:
				lastpath = filename[0:filename.rfind("/")]
				print "lastpath directory=", lastpath
				self.close(filename)

	def exit(self):
		self.close(None)

class DVDSummary(Screen):
	skin = (
	"""<screen name="DVDSummary" position="0,0" size="132,64" id="1">
		<widget source="session.CurrentService" render="Label" position="5,4" size="120,28" font="Regular;12" transparent="1" >
			<convert type="ServiceName">Name</convert>
		</widget>
		<widget name="DVDPlayer" position="5,30" size="66,16" font="Regular;11" transparent="1" />
		<widget name="Chapter" position="72,30" size="54,16" font="Regular;12" transparent="1" halign="right" />
		<widget source="session.CurrentService" render="Label" position="66,46" size="60,18" font="Regular;16" transparent="1" halign="right" >
			<convert type="ServicePosition">Position</convert>
		</widget>
		<widget source="session.CurrentService" render="Progress" position="6,46" size="60,18" borderWidth="1" >
			<convert type="ServicePosition">Position</convert>
		</widget>
	</screen>""",
	"""<screen name="DVDSummary" position="0,0" size="96,64" id="2">
		<widget source="session.CurrentService" render="Label" position="0,0" size="96,25" font="Regular;12" transparent="1" >
			<convert type="ServiceName">Name</convert>
		</widget>
		<widget name="DVDPlayer" position="0,26" size="96,12" font="Regular;10" transparent="1" />
		<widget name="Chapter" position="0,40" size="66,12" font="Regular;10" transparent="1" halign="left" />
		<widget source="session.CurrentService" render="Label" position="66,40" size="30,12" font="Regular;10" transparent="1" halign="right" >
			<convert type="ServicePosition">Position</convert>
		</widget>
		<widget source="session.CurrentService" render="Progress" position="0,52" size="96,12" borderWidth="1" >
			<convert type="ServicePosition">Position</convert>
		</widget>
	</screen>""")

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent)

		self["DVDPlayer"] = Label("DVD Player")
		self["Title"] = Label("")
		self["Time"] = Label("")
		self["Chapter"] = Label("")

	def updateChapter(self, chapter):
		self["Chapter"].setText(chapter)

	def setTitle(self, title):
		self["Title"].setText(title)

class DVDOverlay(Screen):
	def __init__(self, session, args = None):
		desktop_size = getDesktop(0).size()
		DVDOverlay.skin = """<screen name="DVDOverlay" position="0,0" size="%d,%d" flags="wfNoBorder" zPosition="-1" backgroundColor="transparent" />""" %(desktop_size.width(), desktop_size.height())
		Screen.__init__(self, session)

class ChapterZap(Screen):
	skin = """
	<screen name="ChapterZap" position="235,255" size="250,60" title="Chapter" >
		<widget name="chapter" position="35,15" size="110,25" font="Regular;23" />
		<widget name="number" position="145,15" size="80,25" halign="right" font="Regular;23" />
	</screen>"""
	
	def quit(self):
		self.Timer.stop()
		self.close(0)

	def keyOK(self):
		self.Timer.stop()
		self.close(int(self["number"].getText()))

	def keyNumberGlobal(self, number):
		self.Timer.start(3000, True)		#reset timer
		self.field = self.field + str(number)
		self["number"].setText(self.field)
		if len(self.field) >= 4:
			self.keyOK()

	def __init__(self, session, number):
		Screen.__init__(self, session)
		self.field = str(number)

		self["chapter"] = Label(_("Chapter:"))

		self["number"] = Label(self.field)

		self["actions"] = NumberActionMap( [ "SetupActions" ],
			{
				"cancel": self.quit,
				"ok": self.keyOK,
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
			})

		self.Timer = eTimer()
		self.Timer.callback.append(self.keyOK)
		self.Timer.start(3000, True)

class DVDPlayer(Screen, InfoBarBase, InfoBarNotifications, InfoBarSeek, InfoBarPVRState, InfoBarShowHide, HelpableScreen, InfoBarCueSheetSupport, InfoBarAudioSelection, InfoBarSubtitleSupport, InfoBarSimpleEventView):
	ALLOW_SUSPEND = Screen.SUSPEND_PAUSES
	ENABLE_RESUME_SUPPORT = True
	
	skin = """
	<screen name="DVDPlayer" flags="wfNoBorder" position="0,380" size="720,160" title="InfoBar" backgroundColor="transparent" >
		<!-- Background -->
		<ePixmap position="0,0" zPosition="-2" size="720,160" pixmap="skin_default/info-bg_mp.png" alphatest="off" />
		<ePixmap position="29,40" zPosition="0" size="665,104" pixmap="skin_default/screws_mp.png" alphatest="on" transparent="1" />
		<!-- colorbuttons -->
		<ePixmap position="48,70" zPosition="0" size="108,13" pixmap="skin_default/icons/mp_buttons.png" alphatest="on" />
		<!-- Servicename -->
		<ePixmap pixmap="skin_default/icons/icon_event.png" position="207,78" zPosition="1" size="15,10" alphatest="on" />
		<widget source="session.CurrentService" render="Label" position="230,73" size="300,22" font="Regular;20" backgroundColor="#263c59" shadowColor="#1d354c" shadowOffset="-1,-1" transparent="1" noWrap="1">
			<convert type="ServiceName">Name</convert>
		</widget>
		<!-- Chapter info -->
		<widget name="chapterLabel" position="230,96" size="360,22" font="Regular;20" foregroundColor="#c3c3c9" backgroundColor="#263c59" transparent="1" />
		<!-- Audio track info -->
		<ePixmap pixmap="skin_default/icons/icon_dolby.png" position="540,60" zPosition="1" size="26,16" alphatest="on"/>
		<widget name="audioLabel" position="570,60" size="130,22" font="Regular;18" backgroundColor="#263c59" shadowColor="#1d354c" shadowOffset="-1,-1" transparent="1" />
		<!-- Subtitle track info -->
		<widget source="session.CurrentService" render="Pixmap" pixmap="skin_default/icons/icon_txt.png" position="540,83" zPosition="1" size="26,16" alphatest="on" >
			<convert type="ServiceInfo">HasTelext</convert>
			<convert type="ConditionalShowHide" />
		</widget>
		<widget name="subtitleLabel" position="570,83" size="130,22" font="Regular;18" backgroundColor="#263c59" shadowColor="#1d354c" shadowOffset="-1,-1" transparent="1" />
		<!-- Angle info -->
		<widget name="anglePix" pixmap="skin_default/icons/icon_view.png" position="540,106" size="26,16" alphatest="on" />
		<widget name="angleLabel" position="570,106" size="130,22" font="Regular;18" backgroundColor="#263c59" shadowColor="#1d354c" shadowOffset="-1,-1" transparent="1" />
		<!-- Elapsed time -->
		<widget source="session.CurrentService" render="Label" position="205,129" size="100,20" font="Regular;18" halign="center" valign="center" backgroundColor="#06224f" shadowColor="#1d354c" shadowOffset="-1,-1" transparent="1" >
			<convert type="ServicePosition">Position,ShowHours</convert>
		</widget>
		<!-- Progressbar (movie position)-->
		<widget source="session.CurrentService" render="PositionGauge" position="300,133" size="270,10" zPosition="2" pointer="skin_default/position_pointer.png:540,0" transparent="1" >
			<convert type="ServicePosition">Gauge</convert>
		</widget>
		<!-- Remaining time -->
		<widget source="session.CurrentService" render="Label" position="576,129" size="100,20" font="Regular;18" halign="center" valign="center" backgroundColor="#06224f" shadowColor="#1d354c" shadowOffset="-1,-1" transparent="1" >
			<convert type="ServicePosition">Remaining,Negate,ShowHours</convert>
		</widget>
	</screen>"""

	def save_infobar_seek_config(self):
		self.saved_config_speeds_forward = config.seek.speeds_forward.value
		self.saved_config_speeds_backward = config.seek.speeds_backward.value
		self.saved_config_enter_forward = config.seek.enter_forward.value
		self.saved_config_enter_backward = config.seek.enter_backward.value
		self.saved_config_seek_on_pause = config.seek.on_pause.value
		self.saved_config_seek_speeds_slowmotion = config.seek.speeds_slowmotion.value

	def change_infobar_seek_config(self):
		config.seek.speeds_forward.setValue([2, 4, 8, 16, 32, 64])
		config.seek.speeds_backward.setValue([8, 16, 32, 64])
		config.seek.speeds_slowmotion.setValue([ ])
		config.seek.enter_forward.setValue("2")
		config.seek.enter_backward.setValue("2")
		config.seek.on_pause.setValue("play")

	def restore_infobar_seek_config(self):
		config.seek.speeds_forward.setValue(self.saved_config_speeds_forward)
		config.seek.speeds_backward.setValue(self.saved_config_speeds_backward)
		config.seek.speeds_slowmotion.setValue(self.saved_config_seek_speeds_slowmotion)
		config.seek.enter_forward.setValue(self.saved_config_enter_forward)
		config.seek.enter_backward.setValue(self.saved_config_enter_backward)
		config.seek.on_pause.setValue(self.saved_config_seek_on_pause)

	def __init__(self, session, dvd_device = None, dvd_filelist = [ ], args = None):
		Screen.__init__(self, session)
		InfoBarBase.__init__(self)
		InfoBarNotifications.__init__(self)
		InfoBarCueSheetSupport.__init__(self, actionmap = "MediaPlayerCueSheetActions")
		InfoBarShowHide.__init__(self)
		InfoBarAudioSelection.__init__(self)
		InfoBarSubtitleSupport.__init__(self)
		HelpableScreen.__init__(self)
		self.save_infobar_seek_config()
		self.change_infobar_seek_config()
		InfoBarSeek.__init__(self)
		InfoBarPVRState.__init__(self)
		self.dvdScreen = self.session.instantiateDialog(DVDOverlay)

		self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()
		self["audioLabel"] = Label("n/a")
		self["subtitleLabel"] = Label("")
		self["angleLabel"] = Label("")
		self["chapterLabel"] = Label("")
		self["anglePix"] = Pixmap()
		self["anglePix"].hide()
		self.last_audioTuple = None
		self.last_subtitleTuple = None
		self.last_angleTuple = None
		self.totalChapters = 0
		self.currentChapter = 0
		self.totalTitles = 0
		self.currentTitle = 0

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evStopped: self.__serviceStopped,
				iPlayableService.evUser: self.__timeUpdated,
				iPlayableService.evUser+1: self.__statePlay,
				iPlayableService.evUser+2: self.__statePause,
				iPlayableService.evUser+3: self.__osdFFwdInfoAvail,
				iPlayableService.evUser+4: self.__osdFBwdInfoAvail,
				iPlayableService.evUser+5: self.__osdStringAvail,
				iPlayableService.evUser+6: self.__osdAudioInfoAvail,
				iPlayableService.evUser+7: self.__osdSubtitleInfoAvail,
				iPlayableService.evUser+8: self.__chapterUpdated,
				iPlayableService.evUser+9: self.__titleUpdated,
				iPlayableService.evUser+11: self.__menuOpened,
				iPlayableService.evUser+12: self.__menuClosed,
				iPlayableService.evUser+13: self.__osdAngleInfoAvail
			})

		self["DVDPlayerDirectionActions"] = ActionMap(["DirectionActions"],
			{
				#MENU KEY DOWN ACTIONS
				"left": self.keyLeft,
				"right": self.keyRight,
				"up": self.keyUp,
				"down": self.keyDown,

				#MENU KEY REPEATED ACTIONS
				"leftRepeated": self.doNothing,
				"rightRepeated": self.doNothing,
				"upRepeated": self.doNothing,
				"downRepeated": self.doNothing,

				#MENU KEY UP ACTIONS
				"leftUp": self.doNothing,
				"rightUp": self.doNothing,
				"upUp": self.doNothing,
				"downUp": self.doNothing,
			})

		self["OkCancelActions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.keyOk,
				"cancel": self.keyCancel,
			})

		self["DVDPlayerPlaybackActions"] = HelpableActionMap(self, "DVDPlayerActions",
			{
				#PLAYER ACTIONS
				"dvdMenu": (self.enterDVDMenu, _("show DVD main menu")),
				"toggleInfo": (self.toggleInfo, _("toggle time, chapter, audio, subtitle info")),
				"nextChapter": (self.nextChapter, _("forward to the next chapter")),
				"prevChapter": (self.prevChapter, _("rewind to the previous chapter")),
				"nextTitle": (self.nextTitle, _("jump forward to the next title")),
				"prevTitle": (self.prevTitle, _("jump back to the previous title")),
				"tv": (self.askLeavePlayer, _("exit DVD player or return to file browser")),
				"dvdAudioMenu": (self.enterDVDAudioMenu, _("(show optional DVD audio menu)")),
				"AudioSelection": (self.enterAudioSelection, _("Select audio track")),
				"nextAudioTrack": (self.nextAudioTrack, _("switch to the next audio track")),
				"nextSubtitleTrack": (self.nextSubtitleTrack, _("switch to the next subtitle language")),
				"nextAngle": (self.nextAngle, _("switch to the next angle")),
				"seekBeginning": self.seekBeginning,
			}, -2)
			
		self["NumberActions"] = NumberActionMap( [ "NumberActions"],
			{
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal,
				"0": self.keyNumberGlobal,
			})

		self.onClose.append(self.__onClose)

		try:
			from Plugins.SystemPlugins.Hotplug.plugin import hotplugNotifier
			hotplugNotifier.append(self.hotplugCB)
		except:
			pass
		
		self.autoplay = dvd_device or dvd_filelist

		if dvd_device:
			self.physicalDVD = True
		else:
			self.scanHotplug()

		self.dvd_filelist = dvd_filelist
		self.onFirstExecBegin.append(self.opened)
		self.service = None
		self.in_menu = False

	def keyNumberGlobal(self, number):
		print "You pressed number " + str(number)
		self.session.openWithCallback(self.numberEntered, ChapterZap, number)

	def numberEntered(self, retval):
#		print self.servicelist
		if retval > 0:
			self.zapToNumber(retval)

	def getServiceInterface(self, iface):
		service = self.service
		if service:
			attr = getattr(service, iface, None)
			if callable(attr):
				return attr()
		return None

	def __serviceStopped(self):
		self.dvdScreen.hide()
		subs = self.getServiceInterface("subtitle")
		if subs:
			subs.disableSubtitles(self.session.current_dialog.instance)

	def serviceStarted(self): #override InfoBarShowHide function
		self.dvdScreen.show()

	def doEofInternal(self, playing):
		if self.in_menu:
			self.hide()

	def __menuOpened(self):
		self.hide()
		self.in_menu = True
		self["NumberActions"].setEnabled(False)

	def __menuClosed(self):
		self.show()
		self.in_menu = False
		self["NumberActions"].setEnabled(True)

	def setChapterLabel(self):
		chapterLCD = "Menu"
		chapterOSD = "DVD Menu"
		if self.currentTitle > 0:
			chapterLCD = "%s %d" % (_("Chap."), self.currentChapter)
			chapterOSD = "DVD %s %d/%d" % (_("Chapter"), self.currentChapter, self.totalChapters)
			chapterOSD += " (%s %d/%d)" % (_("Title"), self.currentTitle, self.totalTitles)
		self["chapterLabel"].setText(chapterOSD)
		try:
			self.session.summary.updateChapter(chapterLCD)
		except:
			pass

	def doNothing(self):
		pass

	def toggleInfo(self):
		if not self.in_menu:
			self.toggleShow()
			print "toggleInfo"

	def __timeUpdated(self):
		print "timeUpdated"

	def __statePlay(self):
		print "statePlay"

	def __statePause(self):
		print "statePause"

	def __osdFFwdInfoAvail(self):
		self.setChapterLabel()
		print "FFwdInfoAvail"

	def __osdFBwdInfoAvail(self):
		self.setChapterLabel()
		print "FBwdInfoAvail"

	def __osdStringAvail(self):
		print "StringAvail"

	def __osdAudioInfoAvail(self):
		info = self.getServiceInterface("info")
		audioTuple = info and info.getInfoObject(iServiceInformation.sUser+6)
		print "AudioInfoAvail ", repr(audioTuple)
		if audioTuple:
			#audioString = "%d: %s (%s)" % (audioTuple[0],audioTuple[1],audioTuple[2])
			audioString = "%s (%s)" % (audioTuple[1],audioTuple[2])
			self["audioLabel"].setText(audioString)
			if audioTuple != self.last_audioTuple and not self.in_menu:
				self.doShow()
		self.last_audioTuple = audioTuple

	def __osdSubtitleInfoAvail(self):
		info = self.getServiceInterface("info")
		subtitleTuple = info and info.getInfoObject(iServiceInformation.sUser+7)
		print "SubtitleInfoAvail ", repr(subtitleTuple)
		if subtitleTuple:
			subtitleString = ""
			if subtitleTuple[0] is not 0:
				#subtitleString = "%d: %s" % (subtitleTuple[0],subtitleTuple[1])
				subtitleString = "%s" % subtitleTuple[1]
			self["subtitleLabel"].setText(subtitleString)
			if subtitleTuple != self.last_subtitleTuple and not self.in_menu:
				self.doShow()
		self.last_subtitleTuple = subtitleTuple
	
	def __osdAngleInfoAvail(self):
		info = self.getServiceInterface("info")
		angleTuple = info and info.getInfoObject(iServiceInformation.sUser+8)
		print "AngleInfoAvail ", repr(angleTuple)
		if angleTuple:
			angleString = ""
			if angleTuple[1] > 1:
				angleString = "%d / %d" % (angleTuple[0],angleTuple[1])
				self["anglePix"].show()
			else:
				self["anglePix"].hide()
			self["angleLabel"].setText(angleString)
			if angleTuple != self.last_angleTuple and not self.in_menu:
				self.doShow()
		self.last_angleTuple = angleTuple

	def __chapterUpdated(self):
		info = self.getServiceInterface("info")
		if info:
			self.currentChapter = info.getInfo(iServiceInformation.sCurrentChapter)
			self.totalChapters = info.getInfo(iServiceInformation.sTotalChapters)
			self.setChapterLabel()
			print "__chapterUpdated: %d/%d" % (self.currentChapter, self.totalChapters)

	def __titleUpdated(self):
		info = self.getServiceInterface("info")
		if info:
			self.currentTitle = info.getInfo(iServiceInformation.sCurrentTitle)
			self.totalTitles = info.getInfo(iServiceInformation.sTotalTitles)
			self.setChapterLabel()
			print "__titleUpdated: %d/%d" % (self.currentTitle, self.totalTitles)
			if not self.in_menu:
				self.doShow()
		
	def askLeavePlayer(self):
		if self.autoplay:
			self.exitCB((None,"exit"))
			return
		choices = [(_("Exit"), "exit"), (_("Continue playing"), "play")]
		if True or not self.physicalDVD:
			choices.insert(1,(_("Return to file browser"), "browser"))
		if self.physicalDVD:
			cur = self.session.nav.getCurrentlyPlayingServiceReference()
			if cur and not cur.toString().endswith(harddiskmanager.getAutofsMountpoint(harddiskmanager.getCD())):
			    choices.insert(0,(_("Play DVD"), "playPhysical" ))
		self.session.openWithCallback(self.exitCB, ChoiceBox, title=_("Leave DVD Player?"), list = choices)

	def sendKey(self, key):
		keys = self.getServiceInterface("keys")
		if keys:
			keys.keyPressed(key)
		return keys

	def enterAudioSelection(self):
		self.audioSelection()

	def nextAudioTrack(self):
		self.sendKey(iServiceKeys.keyUser)

	def nextSubtitleTrack(self):
		self.sendKey(iServiceKeys.keyUser+1)

	def enterDVDAudioMenu(self):
		self.sendKey(iServiceKeys.keyUser+2)

	def nextChapter(self):
		self.sendKey(iServiceKeys.keyUser+3)

	def prevChapter(self):
		self.sendKey(iServiceKeys.keyUser+4)

	def nextTitle(self):
		self.sendKey(iServiceKeys.keyUser+5)

	def prevTitle(self):
		self.sendKey(iServiceKeys.keyUser+6)

	def enterDVDMenu(self):
		self.sendKey(iServiceKeys.keyUser+7)
	
	def nextAngle(self):
		self.sendKey(iServiceKeys.keyUser+8)

	def seekBeginning(self):
		if self.service:
			seekable = self.getSeek()
			if seekable:
				seekable.seekTo(0)

	def zapToNumber(self, number):
		if self.service:
			seekable = self.getSeek()
			if seekable:
				print "seek to chapter %d" % number
				seekable.seekChapter(number)

#	MENU ACTIONS
	def keyRight(self):
		self.sendKey(iServiceKeys.keyRight)

	def keyLeft(self):
		self.sendKey(iServiceKeys.keyLeft)

	def keyUp(self):
		self.sendKey(iServiceKeys.keyUp)

	def keyDown(self):
		self.sendKey(iServiceKeys.keyDown)

	def keyOk(self):
		if self.sendKey(iServiceKeys.keyOk) and not self.in_menu:
			self.toggleInfo()

	def keyCancel(self):
		self.askLeavePlayer()

	def opened(self):
		if self.autoplay and self.dvd_filelist:
			# opened via autoplay
			self.FileBrowserClosed(self.dvd_filelist[0])
		elif self.autoplay and self.physicalDVD:
			self.playPhysicalCB(True)
		elif self.physicalDVD:
			# opened from menu with dvd in drive
			self.session.openWithCallback(self.playPhysicalCB, MessageBox, text=_("Do you want to play DVD in drive?"), timeout=5 )
		else:
			# opened from menu without dvd in drive
			self.session.openWithCallback(self.FileBrowserClosed, FileBrowser, self.dvd_filelist)

	def playPhysicalCB(self, answer):
		if answer == True:
			harddiskmanager.setDVDSpeed(harddiskmanager.getCD(), 1)
			self.FileBrowserClosed(harddiskmanager.getAutofsMountpoint(harddiskmanager.getCD()))
		else:
			self.session.openWithCallback(self.FileBrowserClosed, FileBrowser)

	def FileBrowserClosed(self, val):
		curref = self.session.nav.getCurrentlyPlayingServiceReference()
		print "FileBrowserClosed", val
		if val is None:
			self.askLeavePlayer()
		else:
			newref = eServiceReference(4369, 0, val)
			print "play", newref.toString()
			if curref is None or curref != newref:
				if newref.toString().endswith("/VIDEO_TS") or newref.toString().endswith("/"):
					names = newref.toString().rsplit("/",3)
					if names[2].startswith("Disk ") or names[2].startswith("DVD "):
						name = str(names[1]) + " - " + str(names[2])
					else:
						name = names[2]
					print "setting name to: ", self.service
					newref.setName(str(name))
				self.session.nav.playService(newref)
				self.service = self.session.nav.getCurrentService()
				print "self.service", self.service
				print "cur_dlg", self.session.current_dialog
				subs = self.getServiceInterface("subtitle")
				if subs:
					subs.enableSubtitles(self.dvdScreen.instance, None)

	def exitCB(self, answer):
		if answer is not None:
			if answer[1] == "exit":
				if self.service:
					self.service = None
				self.close()
			if answer[1] == "browser":
				#TODO check here if a paused dvd playback is already running... then re-start it...
				#else
				if self.service:
					self.service = None
				self.session.openWithCallback(self.FileBrowserClosed, FileBrowser)
			if answer[1] == "playPhysical":
				if self.service:
					self.service = None
				self.playPhysicalCB(True)
			else:
				pass

	def __onClose(self):
		self.restore_infobar_seek_config()
		self.session.nav.playService(self.oldService)
		try:
			from Plugins.SystemPlugins.Hotplug.plugin import hotplugNotifier
			hotplugNotifier.remove(self.hotplugCB)
		except:
			pass

	def playLastCB(self, answer): # overwrite infobar cuesheet function
		print "playLastCB", answer, self.resume_point
		if self.service:
			if answer == True:
				seekable = self.getSeek()
				if seekable:
					seekable.seekTo(self.resume_point)
			pause = self.service.pause()
			pause.unpause()
		self.hideAfterResume()

	def showAfterCuesheetOperation(self):
		if not self.in_menu:
			self.show()

	def createSummary(self):
		return DVDSummary

#override some InfoBarSeek functions
	def doEof(self):
		self.setSeekState(self.SEEK_STATE_PLAY)

	def calcRemainingTime(self):
		return 0

	def hotplugCB(self, dev, media_state):
		print "[hotplugCB]", dev, media_state
		if dev == harddiskmanager.getCD():
			if media_state == "1":
				self.scanHotplug()
			else:
				self.physicalDVD = False

	def scanHotplug(self):
		devicepath = harddiskmanager.getAutofsMountpoint(harddiskmanager.getCD())
		if pathExists(devicepath):
			from Components.Scanner import scanDevice
			res = scanDevice(devicepath)
			list = [ (r.description, r, res[r], self.session) for r in res ]
			if list:
				(desc, scanner, files, session) = list[0]
				for file in files:
					print file
					if file.mimetype == "video/x-dvd":
						print "physical dvd found:", devicepath
						self.physicalDVD = True
						return
		self.physicalDVD = False

def main(session, **kwargs):
	session.open(DVDPlayer)
	
def play(session, **kwargs):
	from Screens import DVD
	session.open(DVD.DVDPlayer, dvd_device=harddiskmanager.getAutofsMountpoint(harddiskmanager.getCD()))	
	
def onPartitionChange(action, partition):
	print "[@] onPartitionChange", action, partition
	if partition != harddiskmanager.getCD():
		global detected_DVD
		if action == 'remove':
			print "[@] DVD removed"
			detected_DVD = False
		elif action == 'add':
			print "[@] DVD Inserted"
			detected_DVD = None	

def menu(menuid, **kwargs):
	if menuid == "mainmenu":
		global detected_DVD
		if config.usage.show_dvdplayer.value:
			return [(_("DVD Player"), main, "dvd_player", 46)]
		elif detected_DVD is None:
			cd = harddiskmanager.getCD()
			if cd and os.path.exists(os.path.join(harddiskmanager.getAutofsMountpoint(harddiskmanager.getCD()), "VIDEO_TS")):
				detected_DVD = True
			else:
				detected_DVD = False
			if onPartitionChange not in harddiskmanager.on_partition_list_change:
				harddiskmanager.on_partition_list_change.append(onPartitionChange)
		if detected_DVD:
			return [(_("DVD Player"), play, "dvd_player", 46)]
	return []

from Plugins.Plugin import PluginDescriptor

def filescan_open(list, session, **kwargs):
	if len(list) == 1 and list[0].mimetype == "video/x-dvd":
		splitted = list[0].path.split('/')
		if len(splitted) > 2:
			if splitted[1] == 'media' and (splitted[2].startswith('sr') or splitted[2] == 'dvd'):
				session.open(DVDPlayer, dvd_device="/dev/%s" %(splitted[2]))
				return
	else:
		dvd_filelist = []
		for x in list:
			if x.mimetype == "video/x-dvd-iso":
				dvd_filelist.append(x.path)
			if x.mimetype == "video/x-dvd":
				dvd_filelist.append(x.path.rsplit('/',1)[0])
		session.open(DVDPlayer, dvd_filelist=dvd_filelist)

def filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath

	# Overwrite checkFile to only detect local
	class LocalScanner(Scanner):
		def checkFile(self, file):
			return fileExists(file.path)

	return [
		LocalScanner(mimetypes = ["video/x-dvd","video/x-dvd-iso"],
			paths_to_scan =
				[
					ScanPath(path = "video_ts", with_subdirs = False),
					ScanPath(path = "VIDEO_TS", with_subdirs = False),
					ScanPath(path = "", with_subdirs = False),
				],
			name = "DVD",
			description = _("Play DVD"),
			openfnc = filescan_open,
		)]		

def Plugins(**kwargs):
	return [PluginDescriptor(name = "DVDPlayer", description = "Play DVDs", where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc = menu),
		PluginDescriptor(where = PluginDescriptor.WHERE_FILESCAN, needsRestart = False, fnc = filescan)]
