import os
from enigma import eTimer, iPlayableService, iServiceInformation, eServiceReference, iServiceKeys, getDesktop
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.HelpMenu import HelpableScreen
from Screens.InfoBarGenerics import InfoBarSeek, InfoBarPVRState, InfoBarCueSheetSupport, InfoBarShowHide, InfoBarNotifications, InfoBarAudioSelection, InfoBarSubtitleSupport
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from Components.config import config
from Tools.Directories import pathExists, fileExists
from Components.Harddisk import harddiskmanager

lastpath = ""

class DVDSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent)
		self["Title"] = Label("")
		self["Time"] = Label("")
		self["Chapter"] = Label("")

	def updateChapter(self, chapter):
		self["Chapter"].setText(chapter)

	def setTitle(self, title):
		self["Title"].setText(title)

class DVDOverlay(Screen):
	def __init__(self, session, args = None, height = None):
		desktop_size = getDesktop(0).size()
		w = desktop_size.width()
		h = desktop_size.height()
		if height is not None:
			h = height
		DVDOverlay.skin = """<screen name="DVDOverlay" position="0,0" size="%d,%d" flags="wfNoBorder" zPosition="-1" backgroundColor="transparent" />""" %(w, h)
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
		self.close(self.field and int(self.field))

	def keyNumberGlobal(self, number):
		self.Timer.start(3000, True)
		self.field = self.field + str(number)
		self["number"].setText(self.field)
		if len(self.field) >= 4:
			self.keyOK()

	def __init__(self, session):
		Screen.__init__(self, session)
		self.field = ""

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

class DVDPlayer(Screen, InfoBarBase, InfoBarNotifications, InfoBarSeek, InfoBarPVRState, InfoBarShowHide, HelpableScreen, InfoBarCueSheetSupport, InfoBarAudioSelection, InfoBarSubtitleSupport):
	ALLOW_SUSPEND = Screen.SUSPEND_PAUSES
	ENABLE_RESUME_SUPPORT = True

	skin = """
	<screen name="DVDPlayer" flags="wfNoBorder" position="0,380" size="720,160" title="Info bar" backgroundColor="transparent" >
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

		self.oldService = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.dvdScreen = None
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
				iPlayableService.evEnd: self.__serviceStopped,
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
			}, -2)

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

		self["DVDPlayerColorActions"] = HelpableActionMap(self, "ColorActions",
			{
				"blue": (self.chapterZap, _("jump to chapter by number")),
			}, -2)

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
		if fileExists("/proc/stb/fb/dst_left"):
			self.left = open("/proc/stb/fb/dst_left", "r").read()
			self.width = open("/proc/stb/fb/dst_width", "r").read()
			self.top = open("/proc/stb/fb/dst_top", "r").read()
			self.height = open("/proc/stb/fb/dst_height", "r").read()
			if self.left != "00000000" or self.top != "00000000" or self.width != "000002d0" or self.height != "0000000240":
				open("/proc/stb/fb/dst_left", "w").write("00000000")
				open("/proc/stb/fb/dst_width", "w").write("000002d0")
				open("/proc/stb/fb/dst_top", "w").write("00000000")
				open("/proc/stb/fb/dst_height", "w").write("0000000240")
				self.onClose.append(self.__restoreOSDSize)

	def save_infobar_seek_config(self):
		self.saved_config_speeds_forward = config.seek.speeds_forward.value
		self.saved_config_speeds_backward = config.seek.speeds_backward.value
		self.saved_config_enter_forward = config.seek.enter_forward.value
		self.saved_config_enter_backward = config.seek.enter_backward.value
		self.saved_config_seek_on_pause = config.seek.on_pause.value
		self.saved_config_seek_speeds_slowmotion = config.seek.speeds_slowmotion.value

	def change_infobar_seek_config(self):
		config.seek.speeds_forward.value = [2, 4, 6, 8, 16, 32, 64]
		config.seek.speeds_backward.value = [2, 4, 6, 8, 16, 32, 64]
		config.seek.speeds_slowmotion.value = [ 2, 3, 4, 6 ]
		config.seek.enter_forward.value = "2"
		config.seek.enter_backward.value = "2"
		config.seek.on_pause.value = "play"

	def restore_infobar_seek_config(self):
		config.seek.speeds_forward.value = self.saved_config_speeds_forward
		config.seek.speeds_backward.value = self.saved_config_speeds_backward
		config.seek.speeds_slowmotion.value = self.saved_config_seek_speeds_slowmotion
		config.seek.enter_forward.value = self.saved_config_enter_forward
		config.seek.enter_backward.value = self.saved_config_enter_backward
		config.seek.on_pause.value = self.saved_config_seek_on_pause

	def __restoreOSDSize(self):
		open("/proc/stb/fb/dst_left", "w").write(self.left)
		open("/proc/stb/fb/dst_width", "w").write(self.width)
		open("/proc/stb/fb/dst_top", "w").write(self.top)
		open("/proc/stb/fb/dst_height", "w").write(self.height)

	def chapterZap(self):
		if not self.in_menu:
			self.session.openWithCallback(self.numberEntered, ChapterZap)

	def numberEntered(self, retval):
		if retval:
			self.zapToNumber(retval)

	def getServiceInterface(self, iface):
		service = self.service
		if service:
			attr = getattr(service, iface, None)
			if callable(attr):
				return attr()
		return None

	def __serviceStopped(self):
		if self.in_menu:
			self.in_menu = False
		self.dvdScreen and self.dvdScreen.hide()
		subs = self.getServiceInterface("subtitle")
		if subs:
			subs.disableSubtitles(self.session.current_dialog.instance)

	def serviceStarted(self): #override InfoBarShowHide function
		self.dvdScreen and self.dvdScreen.show()

	def doEofInternal(self, playing):
		if self.in_menu:
			self.hide()

	def __menuOpened(self):
		self.hide()
		self.in_menu = True

	def __menuClosed(self):
		self.show()
		self.in_menu = False

	def setChapterLabel(self):
		chapterLCD = _("Menu")
		chapterOSD = _("DVD Menu")
		if self.currentTitle > 0:
			chapterLCD = "%s %d" % (_("Chap."), self.currentChapter)
			chapterOSD = "DVD %s %d/%d" % (_("Chapter"), self.currentChapter, self.totalChapters)
			chapterOSD += " (%s %d/%d)" % (_("Title"), self.currentTitle, self.totalTitles)
		self["chapterLabel"].setText(chapterOSD)
		try:
			self.session.summary and self.session.summary.updateChapter(chapterLCD)
		except:
			pass

	def doNothing(self):
		pass

	def toggleInfo(self):
		if not self.in_menu:
			self.toggleShow()
			print "[DVD] toggleInfo"

	def __timeUpdated(self):
		print "[DVD] timeUpdated"

	def __statePlay(self):
		print "[DVD] statePlay"

	def __statePause(self):
		print "[DVD] statePause"

	def __osdFFwdInfoAvail(self):
		self.setChapterLabel()
		print "[DVD] FFwdInfoAvail"

	def __osdFBwdInfoAvail(self):
		self.setChapterLabel()
		print "[DVD] FBwdInfoAvail"

	def __osdStringAvail(self):
		print "[DVD] StringAvail"

	def __osdAudioInfoAvail(self):
		info = self.getServiceInterface("info")
		audioTuple = info and info.getInfoObject(iServiceInformation.sUser+6)
		print "[DVD] AudioInfoAvail ", repr(audioTuple)
		if audioTuple:
			audioString = "%d: %s (%s)" % (audioTuple[0],audioTuple[1],audioTuple[2])
			self["audioLabel"].setText(audioString)
			if audioTuple != self.last_audioTuple and not self.in_menu:
				self.doShow()
		self.last_audioTuple = audioTuple

	def __osdSubtitleInfoAvail(self):
		info = self.getServiceInterface("info")
		subtitleTuple = info and info.getInfoObject(iServiceInformation.sUser+7)
		print "[DVD] SubtitleInfoAvail ", repr(subtitleTuple)
		if subtitleTuple:
			subtitleString = ""
			if subtitleTuple[0] is not 0:
				subtitleString = "%d: %s" % (subtitleTuple[0],subtitleTuple[1])
			self["subtitleLabel"].setText(subtitleString)
			if subtitleTuple != self.last_subtitleTuple and not self.in_menu:
				self.doShow()
		self.last_subtitleTuple = subtitleTuple

	def __osdAngleInfoAvail(self):
		info = self.getServiceInterface("info")
		angleTuple = info and info.getInfoObject(iServiceInformation.sUser+8)
		print "[DVD] AngleInfoAvail ", repr(angleTuple)
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
			print "[DVD] __chapterUpdated: %d/%d" % (self.currentChapter, self.totalChapters)

	def __titleUpdated(self):
		info = self.getServiceInterface("info")
		if info:
			self.currentTitle = info.getInfo(iServiceInformation.sCurrentTitle)
			self.totalTitles = info.getInfo(iServiceInformation.sTotalTitles)
			self.setChapterLabel()
			print "[DVD] __titleUpdated: %d/%d" % (self.currentTitle, self.totalTitles)
			if not self.in_menu:
				self.doShow()

	def askLeavePlayer(self):
		if self.autoplay:
			self.exitCB((None, "exit"))
			return
		choices = [(_("Exit"), "exit"), (_("Continue playing"), "play")]
		if self.physicalDVD:
			cur = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if cur and not cur.toString().endswith(harddiskmanager.getAutofsMountpoint(harddiskmanager.getCD())):
				choices.insert(0,(_("Play DVD"), "playPhysical"))
		self.session.openWithCallback(self.exitCB, ChoiceBox, title=_("Leave DVD player?"), list = choices)

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

	def resumeDvd(self):
		self.sendKey(iServiceKeys.keyUser+21)

	def seekBeginning(self):
		if self.service:
			seekable = self.getSeek()
			if seekable:
				seekable.seekTo(0)

	def zapToNumber(self, number):
		if self.service:
			seekable = self.getSeek()
			if seekable:
				print "[DVD] seek to chapter %d" % number
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
			print "[DVD] keyOk"
			self.toggleInfo()
			if not self.in_menu:
				self.toggleShow()

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

	def playPhysicalCB(self, answer):
		if answer == True:
			harddiskmanager.setDVDSpeed(harddiskmanager.getCD(), 1)
			self.FileBrowserClosed(harddiskmanager.getAutofsMountpoint(harddiskmanager.getCD()))

	def FileBrowserClosed(self, val):
		curref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		print "[DVD] FileBrowserClosed", val
		if val is None:
			self.askLeavePlayer()
		else:
			isopathname = "/VIDEO_TS.ISO"
			if os.path.exists(val + isopathname):
				val += isopathname
			newref = eServiceReference(4369, 0, val)
			print "[DVD] play", newref.toString()
			if curref is None or curref != newref:
				self.service = None
				if newref.toString().endswith("/VIDEO_TS") or newref.toString().endswith("/"):
					names = newref.toString().rsplit("/",3)
					if names[2].startswith("Disk ") or names[2].startswith("DVD "):
						name = str(names[1]) + " - " + str(names[2])
					else:
						name = names[2]
					newref.setName(str(name))

#				Construct a path for the IFO header assuming it exists
				ifofilename = val
				if not ifofilename.upper().endswith("/VIDEO_TS"):
					ifofilename += "/VIDEO_TS"
				files = [("/VIDEO_TS.IFO", 0x100), ("/VTS_01_0.IFO", 0x100), ("/VTS_01_0.IFO", 0x200)] # ( filename, offset )
				for name in files:
					(status, isNTSC, isLowResolution) = self.readVideoAtributes(ifofilename, name)
					if status:
						break
				height = getDesktop(0).size().height()
				print "[DVD] height:", height
				if isNTSC:
					height = height * 576 / 480
					print "[DVD] NTSC height:", height
				if isLowResolution:
					height *= 2
					print "[DVD] LowResolution:", height
				if self.dvdScreen is None:
					self.dvdScreen = self.session.instantiateDialog(DVDOverlay, height=height)
				self.session.nav.playService(newref)
				self.service = self.session.nav.getCurrentService()
				print "[DVD] cur_dlg", self.session.current_dialog
				subs = self.getServiceInterface("subtitle")
				if subs and self.dvdScreen:
					subs.enableSubtitles(self.dvdScreen.instance, None)

	def readVideoAtributes(self, isofilename, checked_file):
		(name, offset) = checked_file
		isofilename += name

		print "[DVD] file", name

		status = False
		isNTSC = False
		isLowResolution = False

		ifofile = None
		try:
#			Try to read the IFO header to determine PAL/NTSC format and the resolution
			ifofile = open(isofilename, "r")
			ifofile.seek(offset)
			video_attr_high = ord(ifofile.read(1))
			if video_attr_high != 0:
				status = True
			video_attr_low = ord(ifofile.read(1))
			print "[DVD] %s: video_attr_high = %x" % ( name, video_attr_high ), "video_attr_low = %x" % ( video_attr_low )
			isNTSC = (video_attr_high & 0x10 == 0)
			isLowResolution = (video_attr_low & 0x18 == 0x18)
		except:
#			If the service is an .iso or .img file we assume it is PAL
#			Sorry we cannot open image files here.
			print "[DVD] Cannot read file or is ISO/IMG"
		finally:
			if ifofile is not None:
				ifofile.close()
		return status, isNTSC, isLowResolution

	def exitCB(self, answer):
		if answer is not None:
			if answer[1] == "exit":
				if self.service:
					self.service = None
				self.close()
			elif answer[1] == "playPhysical":
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
		print "[DVD] playLastCB", answer, self.resume_point
		if self.service:
			if answer == True:
				self.resumeDvd()
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
		print "[DVD] hotplugCB", dev, media_state
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
					if file.mimetype == "video/x-dvd":
						print "[DVD] physical dvd found:", devicepath
						self.physicalDVD = True
						return
		self.physicalDVD = False
