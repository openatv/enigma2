from os import path as os_path, remove as os_remove, listdir as os_listdir, system
from time import strftime
from enigma import eTimer, iPlayableService, eServiceCenter, iServiceInformation, eServiceReference, iServiceKeys
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.InputBox import InputBox
from Screens.HelpMenu import HelpableScreen
from Screens.InfoBarGenerics import InfoBarSeek, InfoBarPVRState, InfoBarCueSheetSupport, InfoBarShowHide, InfoBarNotifications
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Components.Label import Label
from Components.FileList import FileList
from Components.ServiceEventTracker import ServiceEventTracker
from Components.config import config
from Components.ProgressBar import ProgressBar
from ServiceReference import ServiceReference
from Tools.Directories import pathExists, fileExists

import random
import servicedvd # load c++ part of dvd player plugin

class FileBrowser(Screen):
	skin = """
	<screen name="FileBrowser" position="100,100" size="520,376" title="DVD File Browser" >
		<widget name="filelist" position="0,0" size="520,376" scrollbarMode="showOnDemand" />
	</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		currDir = "/media/dvd/"
		if not pathExists(currDir):
			currDir = "/"
		#else:
			#print system("mount "+currDir)
		self.filelist = FileList(currDir, matchingPattern = "(?i)^.*\.(iso)", useServiceRef = True)
		self["filelist"] = self.filelist

		self["FilelistActions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.ok,
				"cancel": self.exit
			})

	def ok(self):
		if self["filelist"].getFilename().upper().endswith("VIDEO_TS/"):
			print "dvd structure found, trying to open..."
			self.close(self["filelist"].getFilename()[0:-9])
		
		elif self["filelist"].canDescent(): # isDir
			self["filelist"].descent()
			
		else:
			self.close(self["filelist"].getFilename())
			
	def exit(self):
		self.close(None)
		
class DVDSummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget source="session.CurrentService" render="Label" position="5,4" size="120,28" font="Regular;12" transparent="1" >
			<convert type="ServiceName">Name</convert>
		</widget>
		<widget name="DVDPlayer" position="5,30" size="66,16" font="Regular;12" transparent="1" />
		<widget name="Chapter" position="72,30" size="54,16" font="Regular;12" transparent="1" halign="right" />
		<widget source="session.CurrentService" render="Label" position="66,46" size="60,18" font="Regular;16" transparent="1" halign="right" >
			<convert type="ServicePosition">Position</convert>
		</widget>
		<widget source="session.CurrentService" render="Progress" position="6,46" size="60,18" borderWidth="1" >
			<convert type="ServicePosition">Position</convert>
		</widget>
	</screen>"""

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
	skin = """<screen name="DVDOverlay" position="0,0" size="720,576" flags="wfNoBorder" zPosition="-1" backgroundColor="transparent" />"""
	def __init__(self, session, args = None):
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

class DVDPlayer(Screen, InfoBarNotifications, InfoBarSeek, InfoBarCueSheetSupport, InfoBarPVRState, InfoBarShowHide, HelpableScreen):
	ALLOW_SUSPEND = True
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
		<ePixmap pixmap="skin_default/icons/icon_dolby.png" position="540,73" zPosition="1" size="26,16" alphatest="on"/>
		<widget name="audioLabel" position="570,73" size="130,22" font="Regular;18" backgroundColor="#263c59" shadowColor="#1d354c" shadowOffset="-1,-1" transparent="1" />
		<!-- Subtitle track info -->
		<widget source="session.CurrentService" render="Pixmap" pixmap="skin_default/icons/icon_txt.png" position="540,96" zPosition="1" size="26,16" alphatest="on" >
			<convert type="ServiceInfo">HasTelext</convert>
			<convert type="ConditionalShowHide" />
		</widget>
		<widget name="subtitleLabel" position="570,96" size="130,22" font="Regular;18" backgroundColor="#263c59" shadowColor="#1d354c" shadowOffset="-1,-1" transparent="1" />
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
		self.saved_config_seek_stepwise_minspeed = config.seek.stepwise_minspeed.value
		self.saved_config_seek_stepwise_repeat = config.seek.stepwise_repeat.value
		self.saved_config_seek_on_pause = config.seek.on_pause.value
		self.saved_config_seek_speeds_slowmotion = config.seek.speeds_slowmotion.value

	def change_infobar_seek_config(self):
		config.seek.speeds_forward.value = [2, 4, 8, 16, 32, 64]
		config.seek.speeds_backward.value = [8, 16, 32, 64]
		config.seek.speeds_slowmotion.value = [ ]
		config.seek.enter_forward.value = "2"
		config.seek.enter_backward.value = "2"
		config.seek.stepwise_minspeed.value = "Never"
		config.seek.stepwise_repeat.value = "3"
		config.seek.on_pause.value = "play"

	def restore_infobar_seek_config(self):
		config.seek.speeds_forward.value = self.saved_config_speeds_forward
		config.seek.speeds_backward.value = self.saved_config_speeds_backward
		config.seek.speeds_slowmotion.value = self.saved_config_seek_speeds_slowmotion
		config.seek.enter_forward.value = self.saved_config_enter_forward
		config.seek.enter_backward.value = self.saved_config_enter_backward
		config.seek.stepwise_minspeed.value = self.saved_config_seek_stepwise_minspeed
		config.seek.stepwise_repeat.value = self.saved_config_seek_stepwise_repeat
		config.seek.on_pause.value = self.saved_config_seek_on_pause

	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		InfoBarNotifications.__init__(self)
		InfoBarCueSheetSupport.__init__(self, actionmap = "MediaPlayerCueSheetActions")
		InfoBarShowHide.__init__(self)
		HelpableScreen.__init__(self)
		self.save_infobar_seek_config()
		self.change_infobar_seek_config()
		InfoBarSeek.__init__(self)
		InfoBarPVRState.__init__(self)
		self.dvdScreen = self.session.instantiateDialog(DVDOverlay)

		self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()
		self["audioLabel"] = Label("1")
		self["subtitleLabel"] = Label("")
		self["chapterLabel"] = Label("")
		self.totalChapters = 0
		self.currentChapter = 0
		self.totalTitles = 0
		self.currentTitle = 0

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
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
				#iPlayableService.evUser+10: self.__initializeDVDinfo,
				iPlayableService.evUser+11: self.__menuOpened,
				iPlayableService.evUser+12: self.__menuClosed
			})

		self["DVDPlayerDirectionActions"] = HelpableActionMap(self, "DirectionActions",
			{
				#MENU KEY DOWN ACTIONS
				"left": (self.keyLeft, _("DVD left key")),
				"right": (self.keyRight, _("DVD right key")),
				"up": (self.keyUp, _("DVD up key")),
				"down": (self.keyDown, _("DVD down key")),

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
			}, -2)

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
				"ok": (self.keyOk, _("DVD ENTER key")),
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
				"nextAudioTrack": (self.nextAudioTrack, _("switch to the next audio track")),
				"nextSubtitleTrack": (self.nextSubtitleTrack, _("switch to the next subtitle language")),
				"seekBeginning": (self.seekBeginning, _("Jump to video title 1 (play movie from start)")),
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
		self.onFirstExecBegin.append(self.showFileBrowser)
		self.service = None
		self.in_menu = False
		
	def keyNumberGlobal(self, number):
		print "You pressed number " + str(number)
		self.session.openWithCallback(self.numberEntered, ChapterZap, number)

	def numberEntered(self, retval):
#		print self.servicelist
		if retval > 0:
			self.zapToNumber(retval)

	def serviceStarted(self): #override InfoBarShowHide function
		pass

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
		audioString = self.service.info().getInfoString(iPlayableService.evUser+6)
		print "AudioInfoAvail "+audioString
		self["audioLabel"].setText(audioString)
		self.doShow()

	def __osdSubtitleInfoAvail(self):
		subtitleString = self.service.info().getInfoString(iPlayableService.evUser+7)
		print "SubtitleInfoAvail "+subtitleString
		self["subtitleLabel"].setText(subtitleString)
		self.doShow()

	def __chapterUpdated(self):
		self.currentChapter = self.service.info().getInfo(iPlayableService.evUser+8)
		self.totalChapters = self.service.info().getInfo(iPlayableService.evUser+80)
		self.setChapterLabel()
		print "__chapterUpdated: %d/%d" % (self.currentChapter, self.totalChapters)

	def __titleUpdated(self):
		self.currentTitle = self.service.info().getInfo(iPlayableService.evUser+9)
		self.totalTitles = self.service.info().getInfo(iPlayableService.evUser+90)
		self.setChapterLabel()
		print "__titleUpdated: %d/%d" % (self.currentTitle, self.totalTitles)
		self.doShow()
		
	#def __initializeDVDinfo(self):
		#self.__osdAudioInfoAvail()
		#self.__osdSubtitleInfoAvail()

	def askLeavePlayer(self):
		self.session.openWithCallback(self.exitCB, ChoiceBox, title=_("Leave DVD Player?"), list=[(_("Exit"), "exit"), (_("Return to file browser"), "browser"), (_("Continue playing"), "play")])

	def nextAudioTrack(self):
		if self.service:
			self.service.keys().keyPressed(iServiceKeys.keyUser)

	def nextSubtitleTrack(self):
		if self.service:
			self.service.keys().keyPressed(iServiceKeys.keyUser+1)

	def enterDVDAudioMenu(self):
		if self.service:
			self.service.keys().keyPressed(iServiceKeys.keyUser+2)

	def nextChapter(self):
		if self.service:
			self.service.keys().keyPressed(iServiceKeys.keyUser+3)

	def prevChapter(self):
		if self.service:
			self.service.keys().keyPressed(iServiceKeys.keyUser+4)

	def nextTitle(self):
		if self.service:
			self.service.keys().keyPressed(iServiceKeys.keyUser+5)

	def prevTitle(self):
		if self.service:
			self.service.keys().keyPressed(iServiceKeys.keyUser+6)

	def enterDVDMenu(self):
		if self.service:
			self.service.keys().keyPressed(iServiceKeys.keyUser+7)
			
	def seekBeginning(self):
		if self.service:
			seekable = self.getSeek()
			if seekable is not None:
				seekable.seekTo(0)
				
	def zapToNumber(self, number):
		if self.service:
			seekable = self.getSeek()
			if seekable is not None:
				print "seek to chapter %d" % number
				seekable.seekChapter(number)

#	MENU ACTIONS
	def keyRight(self):
		if self.service:
			self.service.keys().keyPressed(iServiceKeys.keyRight)

	def keyLeft(self):
		if self.service:
			self.service.keys().keyPressed(iServiceKeys.keyLeft)

	def keyUp(self):
		if self.service:
			self.service.keys().keyPressed(iServiceKeys.keyUp)

	def keyDown(self):
		if self.service:
			self.service.keys().keyPressed(iServiceKeys.keyDown)

	def keyOk(self):
		if self.service:
			self.service.keys().keyPressed(iServiceKeys.keyOk)

	def keyCancel(self):
		self.askLeavePlayer()

	def showFileBrowser(self):
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
				self.session.nav.playService(newref)
				self.service = self.session.nav.getCurrentService()
				print "self.service", self.service
				print "cur_dlg", self.session.current_dialog
				self.dvdScreen.show()
				self.service.subtitle().enableSubtitles(self.dvdScreen.instance, None)

	def exitCB(self, answer):
		if answer is not None:
			if answer[1] == "exit":
				if self.service:
					self.dvdScreen.hide()
					self.service.subtitle().disableSubtitles(self.session.current_dialog.instance)
					self.service = None
				self.close()
			if answer[1] == "browser":
				#TODO check here if a paused dvd playback is already running... then re-start it...
				#else
				self.showFileBrowser()
			else:
				pass

	def __onClose(self):
		self.restore_infobar_seek_config()
		self.session.nav.playService(self.oldService)

	def showAfterCuesheetOperation(self):
		self.show()

	def createSummary(self):
		print "DVDCreateSummary"
		return DVDSummary

def main(session, **kwargs):
	session.open(DVDPlayer)

def menu(menuid, **kwargs):
	if menuid == "mainmenu":
		return [(_("DVD Player"), main, "dvd_player", 46)]
	return []

from Plugins.Plugin import PluginDescriptor
def Plugins(**kwargs):
	return [PluginDescriptor(name = "DVDPlayer", description = "Play DVDs", where = PluginDescriptor.WHERE_MENU, fnc = menu)]
