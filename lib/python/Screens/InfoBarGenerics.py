from bisect import insort
from datetime import datetime
from inspect import getfullargspec
from itertools import groupby
from os import listdir
from os.path import exists, isfile, ismount, realpath, splitext
from pickle import HIGHEST_PROTOCOL, dump, load
from re import match
from socket import AF_UNIX, SOCK_STREAM, socket
from sys import maxsize
from time import localtime, strftime, time

from enigma import eActionMap, eAVControl, eDBoxLCD, eDVBDB, eDVBServicePMTHandler, eDVBVolumecontrol, eEPGCache, eServiceCenter, eServiceReference, eTimer, getBsodCounter, getDesktop, iPlayableService, iServiceInformation, quitMainloop, resetBsodCounter

from keyids import KEYFLAGS, KEYIDNAMES, KEYIDS
from RecordTimer import AFTEREVENT, RecordTimer, RecordTimerEntry, findSafeRecordPath, parseEvent
from ServiceReference import ServiceReference, getStreamRelayRef, hdmiInServiceRef, isPlayableForCur
from Components.ActionMap import ActionMap, HelpableActionMap, HelpableNumberActionMap
from Components.AVSwitch import avSwitch
from Components.config import ConfigBoolean, ConfigClock, ConfigSelection, config, configfile
from Components.Harddisk import findMountPoint, harddiskmanager
from Components.Input import Input
from Components.Label import Label
from Components.MovieList import AUDIO_EXTENSIONS, DVD_EXTENSIONS, MOVIE_EXTENSIONS
from Components.Pixmap import MovingPixmap, MultiPixmap
from Components.PluginComponent import plugins
from Components.ScrollLabel import ScrollLabel
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Components.Task import job_manager
from Components.TimerList import TimerList  # Deprecated!
from Components.Timeshift import InfoBarTimeshift
from Components.UsageConfig import defaultMoviePath, preferredInstantRecordPath, preferredTimerPath
from Components.VolumeControl import VolumeControl
from Components.Sources.Boolean import Boolean
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.ChannelSelection import BouquetSelector, ChannelSelection, EpgBouquetSelector, PiPZapSelection, SilentBouquetSelector, service_types_tv, service_types_radio
from Screens.ChoiceBox import ChoiceBox
from Screens.DateTimeInput import InstantRecordingEndTime
from Screens.Dish import Dish
from Screens.EpgSelection import EPGSelection
from Screens.EventView import EventViewEPGSelect, EventViewSimple
from Screens.InputBox import InputBox
from Screens.Menu import Menu, findMenu
from Screens.MessageBox import MessageBox
from Screens.MinuteInput import MinuteInput
from Screens.PictureInPicture import PictureInPicture
from Screens.PiPSetup import PiPSetup
from Screens.PVRState import PVRState, TimeshiftState
from Screens.SubtitleDisplay import SubtitleDisplay
from Screens.RdsDisplay import RassInteractive, RdsInfoDisplay
from Screens.Screen import Screen
from Screens.ScreenSaver import ScreenSaver
from Screens.Setup import Setup
import Screens.Standby
from Screens.Standby import Standby, TryQuitMainloop
from Screens.Timers import RecordTimerEdit, RecordTimerOverview
from Screens.UnhandledKey import UnhandledKey
from Tools import Notifications
from Tools.BoundFunction import boundFunction
from Tools.Directories import SCOPE_CONFIG, SCOPE_SKINS, fileReadLines, fileWriteLines, isPluginInstalled, pathExists, resolveFilename

MODULE_NAME = __name__.split(".")[-1]

AUDIO = False
seek_withjumps_muted = False
jump_pts_adder = 0
jump_last_pts = None
jump_last_pos = None
keyPressCallback = []


def isStandardInfoBar(self):
	return self.__class__.__name__ == "InfoBar"


def isMoviePlayerInfoBar(self):
	return self.__class__.__name__ == "MoviePlayer"


def setResumePoint(session):
	global resumePointCache, resumePointCacheLast
	service = session.nav.getCurrentService()
	ref = session.nav.getCurrentlyPlayingServiceOrGroup()
	if (service is not None) and (ref is not None):  # and (ref.type != 1):
		# Ref type 1 has its own memory.
		seek = service.seek()
		if seek:
			pos = seek.getPlayPosition()
			if not pos[0]:
				key = ref.toString()
				lru = int(time())
				l = seek.getLength()
				if l:
					l = l[1]
				else:
					l = None
				resumePointCache[key] = [lru, pos[1], l]
				for k, v in list(resumePointCache.items()):
					if v[0] < lru:
						candidate = k
						filepath = realpath(candidate.split(":")[-1])
						mountpoint = findMountPoint(filepath)
						if ismount(mountpoint) and not exists(filepath):
							del resumePointCache[candidate]
				saveResumePoints()


def delResumePoint(ref):
	global resumePointCache, resumePointCacheLast
	try:
		del resumePointCache[ref.toString()]
	except KeyError:
		pass
	saveResumePoints()


def getResumePoint(session):
	global resumePointCache
	ref = session.nav.getCurrentlyPlayingServiceOrGroup()
	if (ref is not None) and (ref.type != 1):
		try:
			entry = resumePointCache[ref.toString()]
			entry[0] = int(time())  # Update LRU timestamp.
			return entry[1]
		except KeyError:
			return None


def saveResumePoints():
	global resumePointCache, resumePointCacheLast
	try:
		f = open("/etc/enigma2/resumepoints.pkl", "wb")
		dump(resumePointCache, f, HIGHEST_PROTOCOL)
		f.close()
	except Exception as ex:
		print("[InfoBarGenerics] Failed to write resumepoints:", ex)
	resumePointCacheLast = int(time())


def loadResumePoints():
	try:
		file = open("/etc/enigma2/resumepoints.pkl", "rb")
		PickleFile = load(file)
		file.close()
		return PickleFile
	except Exception as ex:
		print("[InfoBarGenerics] Failed to load resumepoints:", ex)
		return {}


def updateresumePointCache():
	global resumePointCache
	resumePointCache = loadResumePoints()


def ToggleVideo():
	mode = open("/proc/stb/video/policy").read()[:-1]
	print("[InfoBarGenerics] toggle videomode:", mode)
	if mode == "letterbox":
		f = open("/proc/stb/video/policy", "w")
		f.write("panscan")
		f.close()
	elif mode == "panscan":
		f = open("/proc/stb/video/policy", "w")
		f.write("letterbox")
		f.close()
	else:
		# If current policy is not PanScan or Letterbox, set to PanScan.
		f = open("/proc/stb/video/policy", "w")
		f.write("panscan")
		f.close()


resumePointCache = loadResumePoints()
resumePointCacheLast = int(time())


class InfoBarUnhandledKey:
	def __init__(self):
		self.unhandledKey = self.session.instantiateDialog(UnhandledKey)
		eActionMap.getInstance().bindAction("", -maxsize - 1, self.processKeyA)  # Highest priority.
		eActionMap.getInstance().bindAction("", maxsize, self.processKeyB)  # Lowest priority.
		self.checkUnusedTimer = eTimer()
		self.checkUnusedTimer.callback.append(self.isUnhandledKey)
		self.flagBitmap = 0b0010
		self.prevBitmap = 0b0000
		self.sibIgnoreKeys = (
			KEYIDS["KEY_VOLUMEDOWN"],  # 114.
			KEYIDS["KEY_VOLUMEUP"],  # 115.
			KEYIDS["KEY_INFO"],  # 358.
			KEYIDS["KEY_OK"],  # 352.
			KEYIDS["KEY_UP"],  # 103.
			KEYIDS["KEY_DOWN"],  # 108.
			KEYIDS["KEY_CHANNELUP"],  # 402.
			KEYIDS["KEY_CHANNELDOWN"],  # 403.
			KEYIDS["KEY_NEXT"],  #407.
			KEYIDS["KEY_PREVIOUS"]  # 412.
		)

	# Flags:
	# 	0 = Make.
	# 	1 = Break.
	# 	2 = Repeat.
	# 	3 = Long.
	# 	4 = ASCII.
	def processKeyA(self, key, flag):  # This function is called on every key press!
		print(f"[InfoBarGenerics] Key '{KEYIDNAMES.get(key, _('Unknown'))}' (0x{key:X} - {key}) {KEYFLAGS.get(flag, _('Unknown'))}.")
		for callback in keyPressCallback:
			callback()
		if self.closeSecondInfoBar(key) and self.secondInfoBarScreen and self.secondInfoBarScreen.shown:
			self.secondInfoBarScreen.hide()
			self.secondInfoBarWasShown = False
		if flag != 4:
			if flag == 0:
				self.unhandledKey.hide()
			if self.flagBitmap & 0b0010:  # The button is repeating.
				self.flagBitmap = 0b0000
				self.prevBitmap = 0b0000
			self.flagBitmap |= (1 << flag)
			if flag == 1:
				self.checkUnusedTimer.start(0, True)
		return 0

	def processKeyB(self, key, flag):  # This function is only called when no other action has handled this key.
		if flag != 4:
			self.prevBitmap |= (1 << flag)

	def closeSecondInfoBar(self, key):
		return key >= 12 and key not in self.sibIgnoreKeys

	def isUnhandledKey(self):
		if self.flagBitmap == self.prevBitmap:
			self.unhandledKey.show()

	def showUnhandledKey(self):
		self.unhandledKey.show()


class InfoBarLongKeyDetection:
	def __init__(self):
		eActionMap.getInstance().bindAction("", -maxsize - 2, self.detection)  # Highest priority.
		self.LongButtonPressed = False

	def detection(self, key, flag):  # This function is called on every key press!
		if flag == 3:
			self.LongButtonPressed = True
		elif flag == 0:
			self.LongButtonPressed = False


class InfoBarMenu:
	"""Handles the main menu actions, for example, to open the mainmenu (Main Menu) menu."""

	def __init__(self):
		self["MenuActions"] = HelpableActionMap(self, ["InfoBarMenuActions"], {  # "MenuActions" is also used by EMC.
			"showMenu": (self.showMainMenu, _("Open Main Menu")),
			"showSetup": (self.showSetupMenu, _("Open Setup")),
			"showNetworkSetup": (self.showNetworkMenu, _("Open Network Settings")),
			"showSystemSetup": (self.showSystemMenu, _("Open Usage and GUI Settings")),
			"showHDMIRecord": (self.showHDMIRecordSetup, _("Open HDMIRecord Settings")),
			"showRFmod": (self.showRFSetup, _("Open RFmod Settings")),
			"toggleAspectRatio": (self.toggleAspectRatio, _("Cycle through the available aspect ratios")),
			# I think the global subtitle, zoom, audio, timer, quick menu options should be here as well!
			# Maybe also the HDMI option.
		}, prio=0, description=_("Menu Actions"))
		self.session.infobar = None

	def showMenuCallback(self, *val):
		self.session.infobar = None

	def showMainMenu(self):
		menu = findMenu("mainmenu")
		if menu is not None:
			# This is so we can access the currently active InfoBar from screens opened
			# from within the menu at the moment. Used from the SubserviceSelection
			# class latter in this module.
			self.session.infobar = self
			self.session.openWithCallback(self.showMenuCallback, Menu, menu)

	def showSetupMenu(self):
		menu = findMenu("setup")
		if menu is not None:
			self.session.openWithCallback(self.showMenuCallback, Menu, menu)

	def showNetworkMenu(self):
		menu = findMenu("network")
		if menu is not None:
			self.session.openWithCallback(self.showMenuCallback, Menu, menu)

	def showSystemMenu(self):
		menu = findMenu("system")
		if menu is not None:
			self.session.openWithCallback(self.showMenuCallback, Menu, menu)

	def showHDMIRecordSetup(self):
		if BoxInfo.getItem("HDMIin"):
			self.session.openWithCallback(self.showMenuCallback, Setup, "HDMIRecord")

	def showRFSetup(self):
		if BoxInfo.getItem("RfModulator"):
			self.session.openWithCallback(self.showMenuCallback, Setup, "RFmod")

	def toggleAspectRatio(self):
		aspectRatios = config.av.aspect.getSelectionList()
		index = (config.av.aspect.getIndex() + 1) % len(aspectRatios)
		config.av.aspect.value = aspectRatios[index][0]
		config.av.aspect.save()
		self.session.open(MessageBox, _("Aspect ratio set to '%s'.") % aspectRatios[index][1], MessageBox.TYPE_INFO, timeout=3, closeOnAnyKey=True, windowTitle=_("Aspect Ratio"))


class InfoBarStreamRelay:
	FILENAME = "/etc/enigma2/whitelist_streamrelay"

	def __init__(self):
		self.reload()

	def reload(self):
		data = fileReadLines(self.FILENAME, default=[], source=self.__class__.__name__)
		self.__services = self.__sanitizeData(data)

	def __sanitizeData(self, data: list):
		return list(set([match(r"([0-9A-F]+:){10}", line.strip()).group(0) for line in data if line and match(r"^(?:[0-9A-F]+:){10}", line.strip())]))

	def check(self, nav, service):
		return (service or nav.getCurrentlyPlayingServiceReference()) and service.toCompareString() in self.__services

	def write(self):
		fileWriteLines(self.FILENAME, self.__services, source=self.__class__.__name__)

	def toggle(self, nav, service):
		if isinstance(service, list):
			serviceList = service
			serviceList = [service.toCompareString() for service in serviceList]
			self.__services = list(set(serviceList + self.__services))
			self.write()
		else:
			service = service or nav.getCurrentlyPlayingServiceReference()
			if service:
				servicestring = service.toCompareString()
				if servicestring in self.__services:
					self.__services.remove(servicestring)
				else:
					self.__services.append(servicestring)
					if nav.getCurrentlyPlayingServiceReference() and nav.getCurrentlyPlayingServiceReference() == service:
						nav.restartService()
				self.write()

	def __getData(self):
		return self.__services

	def __setData(self, value):
		self.__services = value
		self.write()

	data = property(__getData, __setData)

	def streamrelayChecker(self, playref):
		playrefstring = playref.toCompareString()
		if "%3a//" not in playrefstring and playrefstring in self.__services:
			url = f'http://{".".join("%d" % d for d in config.misc.softcam_streamrelay_url.value)}:{config.misc.softcam_streamrelay_port.value}/'
			if "127.0.0.1" in url:
				playrefmod = ":".join([("%x" % (int(x[1], 16) + 1)).upper() if x[0] == 6 else x[1] for x in enumerate(playrefstring.split(":"))])
			else:
				playrefmod = playrefstring
			playref = eServiceReference("%s%s%s:%s" % (playrefmod, url.replace(":", "%3a"), playrefstring.replace(":", "%3a"), ServiceReference(playref).getServiceName()))
			print(f"[{self.__class__.__name__}] Play service {playref.toCompareString()} via streamrelay")
			playref.setAlternativeUrl(playrefstring, True)
			return playref, True
		return playref, False

	def checkService(self, service):
		return service and service.toCompareString() in self.__services


streamrelay = InfoBarStreamRelay()


class InfoBarAutoCam:
	FILENAME = "/etc/enigma2/autocam"

	def __init__(self):
		self.currentCam = BoxInfo.getItem("CurrentSoftcam")
		self.defaultCam = config.misc.autocamDefault.value or self.currentCam
		self.reload()

	def reload(self):
		self.autoCam = {}
		items = fileReadLines(self.FILENAME, default=[], source=self.__class__.__name__)
		items = [item for item in items if item and "=" in item]
		for item in items:
			itemValues = item.split("=")
			self.autoCam[itemValues[0]] = itemValues[1]

	def write(self):
		items = []
		for key in self.autoCam.keys():
			items.append(f"{key}={self.autoCam[key]}")
		fileWriteLines(self.FILENAME, lines=items, source=self.__class__.__name__)

	def getData(self):
		return self.autoCam

	def setData(self, value):
		self.autoCam = value
		self.write()

	data = property(getData, setData)

	def getCam(self, service):
		return self.autoCam.get(service.toCompareString(), None)

	def checkCrypt(self, service):
		refstring = service.toCompareString()
		if refstring.startswith("1:") and "%" not in refstring:
			try:
				info = eServiceCenter.getInstance().info(service)
				return info.isCrypted()
			except Exception:
				pass
		return False

	def selectCam(self, nav, service, cam):
		service = service or nav.getCurrentlyPlayingServiceReference()
		if service:
			servicestring = service.toCompareString()
			if cam == "None":
				if servicestring in self.autoCam:
					del self.autoCam[servicestring]
			else:
				self.autoCam[servicestring] = cam
			self.write()

	def selectCams(self, services, cam):
		for service in services:
			servicestring = service.toCompareString()
			if cam == "None":
				if servicestring in self.autoCam:
					del self.autoCam[servicestring]
			else:
				self.autoCam[servicestring] = cam
		self.write()

	def autoCamChecker(self, nav, service):
		info = service.info()
		playrefstring = info.getInfoString(iServiceInformation.sServiceref)
		if playrefstring.startswith("1:"):
			isStreamRelay = False
			if "%" in playrefstring:
				playrefstring, isStreamRelay = getStreamRelayRef(playrefstring)
			if "%" not in playrefstring and (isStreamRelay or info and info.getInfo(iServiceInformation.sIsCrypted) == 1):
				cam = self.autoCam.get(playrefstring, self.defaultCam)
				if self.currentCam != cam:
					if nav.getRecordings(False):
						print("[InfoBarGenerics] InfoBarAutoCam: Switch of Softcam not possible due to an active recording.")
						return
					self.switchCam(cam)
					self.currentCam = cam
					BoxInfo.setMutableItem("CurrentSoftcam", cam)

	def switchCam(self, new):
		deamonSocket = socket(AF_UNIX, SOCK_STREAM)
		deamonSocket.connect("/tmp/deamon.socket")
		deamonSocket.send(f"SWITCH_SOFTCAM,{new}".encode())
		deamonSocket.close()


autocam = InfoBarAutoCam()


class TimerSelection(Screen):
	def __init__(self, session, list):
		Screen.__init__(self, session)
		self.setTitle(_("Timer selection"))
		self.list = list
		self["timerlist"] = TimerList(self.list)
		self["actions"] = HelpableActionMap(self, ["OkCancelActions"], {
			"ok": (self.keySelected, _("Select the currently highlighted timer")),
			"cancel": (self.keyClose, _("Close the screen"))
		}, -1, description=_("Timer Selection Actions"))

	def keySelected(self):
		self.close(self["timerlist"].getCurrentIndex())

	def keyClose(self):
		self.close(None)


class InfoBarDish:
	def __init__(self):
		self.dishDialog = self.session.instantiateDialog(Dish)
		self.dishDialog.setAnimationMode(0)


class InfoBarScreenSaver:
	def __init__(self):
		self.screenSaverTimer = eTimer()
		self.screenSaverTimer.callback.append(self.screenSaverTimeout)
		self.screenSaver = self.session.instantiateDialog(ScreenSaver)
		self.onExecBegin.append(self.__onExecBegin)
		self.onExecEnd.append(self.__onExecEnd)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __onExecBegin(self):
		self.screenSaverTimerStart()

	def __onExecEnd(self):
		if self.screenSaver.shown:
			self.screenSaver.hide()
			eActionMap.getInstance().unbindAction("", self.screenSaverKeyPress)
		self.screenSaverTimer.stop()

	def __layoutFinished(self):
		self.screenSaver.hide()

	def screenSaverTimerStart(self):
		startTimer = config.usage.screenSaverStartTimer.value
		flag = self.seekstate[0]
		if not flag:
			ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if ref and not (hasattr(self.session, "pipshown") and self.session.pipshown):
				ref = ref.toString().split(":")
				flag = ref[2] == "2" or ref[2] == "A" or splitext(ref[10])[1].lower() in AUDIO_EXTENSIONS
		if startTimer and flag:
			self.screenSaverTimer.startLongTimer(startTimer)
		else:
			self.screenSaverTimer.stop()

	def screenSaverTimeout(self):
		if self.execing and not Screens.Standby.inStandby and not Screens.Standby.inTryQuitMainloop:
			self.hide()
			if hasattr(self, "pvrStateDialog"):
				try:
					self.pvrStateDialog.hide()
				except Exception:
					pass
			self.screenSaver.show()
			eActionMap.getInstance().bindAction("", -maxsize - 3, self.screenSaverKeyPress)

	def screenSaverKeyPress(self, key, flag):
		if flag:
			self.screenSaver.hide()
			self.show()
			self.screenSaverTimerStart()
			eActionMap.getInstance().unbindAction("", self.screenSaverKeyPress)


class HideVBILine(Screen):
	skin = """<screen position="0,0" size="%s,%s" backgroundColor="#000000" flags="wfNoBorder" />""" % (getDesktop(0).size().width(), getDesktop(0).size().height() / 360)

	def __init__(self, session):
		Screen.__init__(self, session)


class SecondInfoBar(Screen):
	ADD_TIMER = 0
	REMOVE_TIMER = 1

	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		self.skinName = "SecondInfoBarECM" if config.usage.show_second_infobar.value == "3" else "SecondInfoBar"
		self["epg_description"] = ScrollLabel()
		self["FullDescription"] = ScrollLabel()
		self["channel"] = Label()
		self["key_red"] = StaticText()
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["SecondInfoBar"] = HelpableActionMap(self, ["2ndInfobarActions"], {
			"pageUp": (self.pageUp, _("Switch EPG Page Up")),
			"pageDown": (self.pageDown, _("Switch EPG Page Down")),
			"prevPage": (self.pageUp, _("Switch EPG Page Up")),
			"nextPage": (self.pageDown, _("Switch EPG Page Down")),
			"prevEvent": (self.prevEvent, _("Switch to previous EPG Event")),
			"nextEvent": (self.nextEvent, _("Switch to next EPG Event")),
			"timerAdd": (self.timerAdd, _("Add Timer")),
			"openSimilarList": (self.openSimilarList, _("Open Similar List Channel List")),
		}, prio=-1, description=_("2nd InfoBar Actions"))
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evUpdatedEventInfo: self.getEvent,
			iPlayableService.evUpdateTags: self.getEvent
		})
		self.onShow.append(self.__Show)
		self.onHide.append(self.__Hide)

	def pageUp(self):
		self["epg_description"].pageUp()
		self["FullDescription"].pageUp()

	def pageDown(self):
		self["epg_description"].pageDown()
		self["FullDescription"].pageDown()

	def __Show(self):
		if config.plisettings.ColouredButtons.value:
			self["key_yellow"].setText(_("Search"))
		self["key_red"].setText(_("Similar"))
		self["key_blue"].setText(_("Extensions"))
		self["SecondInfoBar"].doBind()
		self.getEvent()

	def __Hide(self):
		if self["SecondInfoBar"].bound:
			self["SecondInfoBar"].doUnbind()

	def getEvent(self):
		self["epg_description"].setText("")
		self["FullDescription"].setText("")
		self["channel"].setText("")
		ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.getNowNext()
		epglist = self.epglist
		if not epglist:
			self.is_now_next = False
			epg = eEPGCache.getInstance()
			ptr = ref and ref.valid() and epg.lookupEventTime(ref, -1)
			if ptr:
				epglist.append(ptr)
				ptr = epg.lookupEventTime(ref, ptr.getBeginTime(), +1)
				if ptr:
					epglist.append(ptr)
		else:
			self.is_now_next = True
		if epglist:
			Event = self.epglist[0]
			Ref = ServiceReference(ref)
			callback = self.eventViewCallback
			self.cbFunc = callback
			self.currentService = Ref
			self.isRecording = (not Ref.ref.flags & eServiceReference.isGroup) and Ref.ref.getPath()
			self.event = Event
			self.key_green_choice = self.ADD_TIMER
			if self.isRecording:
				self["key_green"].setText("")
			else:
				self["key_green"].setText(_("Add Timer"))
			self.setEvent(self.event)

	def getNowNext(self):
		epglist = []
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		ptr = info and info.getEvent(0)
		if ptr:
			epglist.append(ptr)
		ptr = info and info.getEvent(1)
		if ptr:
			epglist.append(ptr)
		self.epglist = epglist

	def eventViewCallback(self, setEvent, setService, val):  # Used for Now/Next display.
		epglist = self.epglist
		if len(epglist) > 1:
			tmp = epglist[0]
			epglist[0] = epglist[1]
			epglist[1] = tmp
			setEvent(epglist[0])

	def prevEvent(self):
		if self.cbFunc is not None:
			self.cbFunc(self.setEvent, self.setService, -1)

	def nextEvent(self):
		if self.cbFunc is not None:
			self.cbFunc(self.setEvent, self.setService, +1)

	def removeTimer(self, timer):
		timer.afterEvent = AFTEREVENT.NONE
		self.session.nav.RecordTimer.removeEntry(timer)
		self["key_green"].setText(_("Add Timer"))
		self.key_green_choice = self.ADD_TIMER

	def timerAdd(self):
		self.hide()
		self.secondInfoBarWasShown = False
		if self.isRecording:
			return
		event = self.event
		serviceref = self.currentService
		if event is None:
			return
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				cb_func = lambda ret: not ret or self.removeTimer(timer)
				self.session.openWithCallback(cb_func, MessageBox, _("Do you really want to delete '%s'?") % event.getEventName())
				break
		else:
			newEntry = RecordTimerEntry(self.currentService, afterEvent=AFTEREVENT.AUTO, justplay=False, always_zap=False, checkOldTimers=True, dirname=preferredTimerPath(), *parseEvent(self.event))
			self.session.openWithCallback(self.finishedAdd, RecordTimerEdit, newEntry)

	def finishedAdd(self, answer):
		# print("finished add")
		if not isinstance(answer, bool) and answer[0]:
			entry = answer[1]
			simulTimerList = self.session.nav.RecordTimer.record(entry)
			if simulTimerList is not None:
				for x in simulTimerList:
					if x.setAutoincreaseEnd(entry):
						self.session.nav.RecordTimer.timeChanged(x)
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList is not None:
					if not entry.repeated and not config.recording.margin_before.value and not config.recording.margin_after.value and len(simulTimerList) > 1:
						change_time = False
						conflict_begin = simulTimerList[1].begin
						conflict_end = simulTimerList[1].end
						if conflict_begin == entry.end:
							entry.end -= 30
							change_time = True
						elif entry.begin == conflict_end:
							entry.begin += 30
							change_time = True
						if change_time:
							simulTimerList = self.session.nav.RecordTimer.record(entry)
					if simulTimerList is not None:
						self.session.openWithCallback(self.finishSanityCorrection, TimerSanityConflict, simulTimerList)
			self["key_green"].setText(_("Remove timer"))
			self.key_green_choice = self.REMOVE_TIMER
		else:
			self["key_green"].setText(_("Add Timer"))
			self.key_green_choice = self.ADD_TIMER
			# print("Timeredit aborted")

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def setService(self, service):
		self.currentService = service
		if self.isRecording:
			self["channel"].setText(_("Recording"))
		else:
			name = self.currentService.getServiceName()
			if name is not None:
				self["channel"].setText(name)
			else:
				self["channel"].setText(_("Unknown Service"))

	def sort_func(self, x, y):
		if x[1] < y[1]:
			return -1
		elif x[1] == y[1]:
			return 0
		else:
			return 1

	def setEvent(self, event):
		if event is None:
			return
		self.event = event
		try:
			name = event.getEventName()
			self["channel"].setText(name)
		except Exception:
			pass
		description = event.getShortDescription()
		extended = event.getExtendedDescription()
		if description and extended:
			description += "\n"
		elif description and not extended:
			extended = description
		if description == extended:
			text = description
		else:
			text = description + extended
		self.setTitle(event.getEventName())
		self["epg_description"].setText(text)
		self["FullDescription"].setText(extended)
		serviceref = self.currentService
		eventid = self.event.getEventId()
		refstr = serviceref.ref.toString()
		isRecordEvent = False
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				isRecordEvent = True
				break
		if isRecordEvent and self.key_green_choice != self.REMOVE_TIMER:
			self["key_green"].setText(_("Remove timer"))
			self.key_green_choice = self.REMOVE_TIMER
		elif not isRecordEvent and self.key_green_choice != self.ADD_TIMER:
			self["key_green"].setText(_("Add Timer"))
			self.key_green_choice = self.ADD_TIMER

	def openSimilarList(self):
		id = self.event and self.event.getEventId()
		refstr = str(self.currentService)
		if id is not None:
			self.hide()
			self.secondInfoBarWasShown = False
			self.session.open(EPGSelection, refstr, None, id)


class InfoBarShowHide(InfoBarScreenSaver):
	""" InfoBar show/hide control, accepts toggleShow and hide actions, might start
	fancy animations. """
	STATE_HIDDEN = 0
	STATE_HIDING = 1
	STATE_SHOWING = 2
	STATE_SHOWN = 3
	FLAG_CENTER_DVB_SUBS = 2048
	skipToggleShow = False

	def __init__(self):
		self["ShowHideActions"] = HelpableActionMap(self, ["InfobarShowHideActions"],
			{
			"LongOKPressed": (self.toggleShowLong, _("Cycle through the InfoBars")),
			"toggleShow": (self.OkPressed, _("Cycle through the InfoBars")),
			"hide": (self.keyHide, _("Hide the InfoBar")),
		}, prio=1, description=_("Show/Hide Actions"))  # Lower priority to make it possible to override OK and Cancel.
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evStart: self.serviceStarted
		})
		InfoBarScreenSaver.__init__(self)
		self.__state = self.STATE_SHOWN
		self.__locked = 0
		self.autocamTimer = eTimer()
		self.autocamTimer.timeout.get().append(self.checkAutocam)
		self.autocamTimer_active = 0
		self.DimmingTimer = eTimer()
		self.DimmingTimer.callback.append(self.doDimming)
		self.hideTimer = eTimer()
		self.hideTimer.callback.append(self.doTimerHide)
		self.hideTimer.start(5000, True)
		self.onShow.append(self.__onShow)
		self.onHide.append(self.__onHide)
		self.hideVBILineScreen = self.session.instantiateDialog(HideVBILine)
		self.hideVBILineScreen.show()
		self.onShowHideNotifiers = []
		self.standardInfoBar = False
		self.lastSecondInfoBar = 0
		self.lastResetAlpha = True
		self.secondInfoBarScreen = ""
		if isStandardInfoBar(self):
			self.SwitchSecondInfoBarScreen()
		self.onLayoutFinish.append(self.__layoutFinished)
		self.onExecBegin.append(self.__onExecBegin)
		for plugin in plugins.getPlugins(PluginDescriptor.WHERE_INFOBARLOADED):
			plugin(reason=1, session=self.session, instance=self, typeInfoBar=self.__class__.__name__)
		self.onClose.append(self.__onClose)

	def __onClose(self):
		for plugin in plugins.getPlugins(PluginDescriptor.WHERE_INFOBARLOADED):
			plugin(reason=0, session=self.session, instance=self, typeInfoBar=self.__class__.__name__)

	def __onExecBegin(self):
		self.showHideVBI()

	def __layoutFinished(self):
		if self.secondInfoBarScreen:
			self.secondInfoBarScreen.hide()
			self.standardInfoBar = True
		self.secondInfoBarWasShown = False
		self.EventViewIsShown = False
		self.hideVBILineScreen.hide()
		try:
			if self.pvrStateDialog:
				pass
		except Exception:
			self.pvrStateDialog = None

	def OkPressed(self):
		if config.usage.okbutton_mode.value == "0":
			self.toggleShow()
		elif config.usage.okbutton_mode.value == "1":
			try:
				self.openServiceList()
			except Exception:
				self.toggleShow()

	def SwitchSecondInfoBarScreen(self):
		if self.lastSecondInfoBar == int(config.usage.show_second_infobar.value):
			return
		self.secondInfoBarScreen = self.session.instantiateDialog(SecondInfoBar)
		self.lastSecondInfoBar = int(config.usage.show_second_infobar.value)

	def LongOKPressed(self):
		if isinstance(self, InfoBarEPG):
			if config.plisettings.InfoBarEpg_mode.value == "1":
				self.openInfoBarEPG()

	def __onShow(self):
		self.__state = self.STATE_SHOWN
		for x in self.onShowHideNotifiers:
			x(True)
		self.startHideTimer()

	def doDimming(self):
		if config.usage.show_infobar_do_dimming.value:
			self.dimmed = self.dimmed - 1
		else:
			self.dimmed = 0
		self.DimmingTimer.stop()
		self.doHide()

	def unDimming(self):
		self.unDimmingTimer.stop()
		self.doWriteAlpha(config.av.osd_alpha.value)

	def doWriteAlpha(self, value):
		if exists("/proc/stb/video/alpha"):
			f = open("/proc/stb/video/alpha", "w")
			f.write("%i" % (value))
			f.close()
			if value == config.av.osd_alpha.value:
				self.lastResetAlpha = True
			else:
				self.lastResetAlpha = False

	def __onHide(self):
		self.__state = self.STATE_HIDDEN
		self.resetAlpha()
		for x in self.onShowHideNotifiers:
			x(False)

	def resetAlpha(self):
		if config.usage.show_infobar_do_dimming.value and self.lastResetAlpha is False:
			self.unDimmingTimer = eTimer()
			self.unDimmingTimer.callback.append(self.unDimming)
			self.unDimmingTimer.start(300, True)

	def keyHide(self, SHOW=True):
		if self.__state == self.STATE_HIDDEN:
			ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if ref:
				ref = ref.toString()
			else:
				ref = " "
			if SHOW and config.plisettings.InfoBarEpg_mode.value == "2" and not ref[1:].startswith(":0:0:0:0:0:0:0:0:0:"):
				self.openInfoBarEPG()
			else:
				self.hide()
				if self.secondInfoBarScreen and self.secondInfoBarScreen.shown:
					self.secondInfoBarScreen.hide()
					self.secondInfoBarWasShown = False
			if SHOW:
				if self.session.pipshown and "popup" in config.usage.pip_hideOnExit.value:
					if config.usage.pip_hideOnExit.value == "popup":
						self.session.openWithCallback(self.hidePipOnExitCallback, MessageBox, _("Disable Picture in Picture"), simple=True)
					else:
						self.hidePipOnExitCallback(True)
		else:
			self.hide()
			if hasattr(self, "pvrStateDialog"):
				try:
					self.pvrStateDialog.hide()
				except Exception:
					pass

	def hidePipOnExitCallback(self, answer):
		if answer:
			self.showPiP()

	def connectShowHideNotifier(self, fnc):
		if fnc not in self.onShowHideNotifiers:
			self.onShowHideNotifiers.append(fnc)

	def disconnectShowHideNotifier(self, fnc):
		if fnc in self.onShowHideNotifiers:
			self.onShowHideNotifiers.remove(fnc)

	def serviceStarted(self):
		if self.execing:
			if self.autocamTimer_active == 1:
				self.autocamTimer.stop()
			self.autocamTimer.start(1000)
			self.autocamTimer_active = 1
			if config.usage.show_infobar_on_zap.value:
				self.doShow()
		self.showHideVBI()

	def startHideTimer(self):
		if self.__state == self.STATE_SHOWN and not self.__locked:
			self.hideTimer.stop()
			idx = config.usage.infobar_timeout.index
			if idx:
				self.hideTimer.start(idx * 1000, True)
		elif (self.secondInfoBarScreen and self.secondInfoBarScreen.shown) or ((not config.usage.show_second_infobar.value or isMoviePlayerInfoBar(self)) and self.EventViewIsShown):
			self.hideTimer.stop()
			idx = config.usage.second_infobar_timeout.index
			if idx:
				self.hideTimer.start(idx * 1000, True)
		elif hasattr(self, "pvrStateDialog"):
			self.hideTimer.stop()
			# idx = config.usage.infobar_timeout.index
			# if idx:
			# 	self.hideTimer.start(idx*1000, True)
		self.skipToggleShow = False

	def doShow(self):
		self.show()
		self.hideTimer.stop()
		self.DimmingTimer.stop()
		self.doWriteAlpha(config.av.osd_alpha.value)
		self.startHideTimer()

	def doTimerHide(self):
		self.hideTimer.stop()
		self.DimmingTimer.start(300, True)
		self.dimmed = config.usage.show_infobar_dimming_speed.value
		self.skipToggleShow = False

	def doHide(self):
		if self.__state != self.STATE_HIDDEN:
			if self.dimmed > 0:
				self.doWriteAlpha((config.av.osd_alpha.value * self.dimmed / config.usage.show_infobar_dimming_speed.value))
				self.DimmingTimer.start(5, True)
			else:
				self.DimmingTimer.stop()
				self.hide()
		elif self.__state == self.STATE_HIDDEN and self.secondInfoBarScreen and self.secondInfoBarScreen.shown:
			if self.dimmed > 0:
				self.doWriteAlpha((config.av.osd_alpha.value * self.dimmed / config.usage.show_infobar_dimming_speed.value))
				self.DimmingTimer.start(5, True)
			else:
				self.DimmingTimer.stop()
				self.secondInfoBarScreen.hide()
				self.secondInfoBarWasShown = False
				self.resetAlpha()
		elif self.__state == self.STATE_HIDDEN and self.EventViewIsShown:
			try:
				self.eventView.close()
			except Exception:
				pass
			self.EventViewIsShown = False
		# elif hasattr(self, "pvrStateDialog"):
		# 	if self.dimmed > 0:
		# 		self.doWriteAlpha((config.av.osd_alpha.value*self.dimmed/config.usage.show_infobar_dimming_speed.value))
		# 		self.DimmingTimer.start(5, True)
		# 	else:
		# 		self.DimmingTimer.stop()
		# 		try:
		# 			self.pvrStateDialog.hide()
		# 		except Exception:
		# 			pass

	def toggleShow(self):
		if self.skipToggleShow:
			self.skipToggleShow = False
			return
		if not hasattr(self, "LongButtonPressed"):
			self.LongButtonPressed = False
		if not self.LongButtonPressed:
			if self.__state == self.STATE_HIDDEN:
				if not self.secondInfoBarWasShown or (config.usage.show_second_infobar.value == "1" and not self.EventViewIsShown):
					self.show()
				if self.secondInfoBarScreen:
					self.secondInfoBarScreen.hide()
				self.secondInfoBarWasShown = False
				self.EventViewIsShown = False
			elif self.secondInfoBarScreen and (config.usage.show_second_infobar.value == "2" or config.usage.show_second_infobar.value == "3") and not self.secondInfoBarScreen.shown:
				self.SwitchSecondInfoBarScreen()
				self.hide()
				self.secondInfoBarScreen.show()
				self.secondInfoBarWasShown = True
				self.startHideTimer()
			elif (config.usage.show_second_infobar.value == "1" or isMoviePlayerInfoBar(self)) and not self.EventViewIsShown:
				self.hide()
				try:
					self.openEventView()
				except Exception:
					pass
				self.EventViewIsShown = True
				self.hideTimer.stop()
			elif isMoviePlayerInfoBar(self) and not self.EventViewIsShown and config.usage.show_second_infobar.value:
				self.hide()
				self.openEventView(True)
				self.EventViewIsShown = True
				self.startHideTimer()
			else:
				self.hide()
				if self.secondInfoBarScreen and self.secondInfoBarScreen.shown:
					self.secondInfoBarScreen.hide()
				elif self.EventViewIsShown:
					try:
						self.eventView.close()
					except Exception:
						pass
					self.EventViewIsShown = False

	def toggleShowLong(self):
		try:
			if self.LongButtonPressed:
				if isinstance(self, InfoBarEPG):
					if config.plisettings.InfoBarEpg_mode.value == "1":
						self.openInfoBarEPG()
		except Exception as e:
			print("[InfoBarGenerics] 'toggleShowLong' failed:", e)

	def lockShow(self):
		try:
			self.__locked += 1
		except Exception:
			self.__locked = 0
		if self.execing:
			self.show()
			self.hideTimer.stop()
			self.skipToggleShow = False

	def unlockShow(self):
		if config.usage.show_infobar_do_dimming.value and self.lastResetAlpha is False:
			self.doWriteAlpha(config.av.osd_alpha.value)
		try:
			self.__locked -= 1
		except Exception:
			self.__locked = 0
		if self.__locked < 0:
			self.__locked = 0
		if self.execing:
			self.startHideTimer()

	def openEventView(self, simple=False):
		try:
			if self.servicelist is None:
				return
		except Exception:
			simple = True
		ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.getNowNext()
		epglist = self.epglist
		if not epglist:
			self.is_now_next = False
			epg = eEPGCache.getInstance()
			ptr = ref and ref.valid() and epg.lookupEventTime(ref, -1)
			if ptr:
				epglist.append(ptr)
				ptr = epg.lookupEventTime(ref, ptr.getBeginTime(), +1)
				if ptr:
					epglist.append(ptr)
		else:
			self.is_now_next = True
		if epglist:
			if not simple:
				self.eventView = self.session.openWithCallback(self.closed, EventViewEPGSelect, epglist[0], ServiceReference(ref), self.eventViewCallback, self.openSingleServiceEPG, self.openMultiServiceEPG, self.openSimilarList)
				self.dlg_stack.append(self.eventView)
			else:
				self.eventView = self.session.openWithCallback(self.closed, EventViewSimple, epglist[0], ServiceReference(ref))
				self.dlg_stack = None

	def getNowNext(self):
		epglist = []
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		ptr = info and info.getEvent(0)
		if ptr:
			epglist.append(ptr)
		ptr = info and info.getEvent(1)
		if ptr:
			epglist.append(ptr)
		self.epglist = epglist

	def closed(self, ret=False):
		if not self.dlg_stack:
			return
		closedScreen = self.dlg_stack.pop()
		if self.eventView and closedScreen == self.eventView:
			self.eventView = None
		if ret is True or ret == "close":
			dlgs = len(self.dlg_stack)
			if dlgs > 0:
				self.dlg_stack[dlgs - 1].close(dlgs > 1)
		self.reopen(ret)

	def eventViewCallback(self, setEvent, setService, val):  # Used for Now/Next display.
		epglist = self.epglist
		if len(epglist) > 1:
			tmp = epglist[0]
			epglist[0] = epglist[1]
			epglist[1] = tmp
			setEvent(epglist[0])

	def checkHideVBI(self):
		service = self.session.nav.getCurrentlyPlayingServiceReference()
		servicepath = service and service.getPath()
		if servicepath and servicepath.startswith("/"):
			if service.toString().startswith("1:"):
				info = eServiceCenter.getInstance().info(service)
				service = info and info.getInfoString(service, iServiceInformation.sServiceref)
				FLAG_HIDE_VBI = 512
				return service and eDVBDB.getInstance().getFlag(eServiceReference(service)) & FLAG_HIDE_VBI and True
			else:
				return ".hidevbi." in servicepath.lower()
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		return info and info.getInfo(iServiceInformation.sHideVBI) == 1

	def showHideVBI(self):
		if self.checkHideVBI():
			self.hideVBILineScreen.show()
		else:
			self.hideVBILineScreen.hide()

	def checkStreamrelay(self, service=None):
		return streamrelay.check(self.session.nav, service)

	def checkCrypt(self, service=None):
		return autocam.checkCrypt(service)

	def checkAutocam(self):
		self.autocamTimer.stop()
		self.autocamTimer_active = 0
		if config.misc.autocamEnabled.value:
			service = self.session.nav.getCurrentService()
			if service:
				autocam.autoCamChecker(self.session.nav, service)


class BufferIndicator(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["status"] = Label()
		self.mayShow = False
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evBuffering: self.bufferChanged,
			iPlayableService.evStart: self.__evStart,
			iPlayableService.evGstreamerPlayStarted: self.__evGstreamerPlayStarted,
		})

	def bufferChanged(self):
		if self.mayShow:
			service = self.session.nav.getCurrentService()
			info = service and service.info()
			if info:
				value = info.getInfo(iServiceInformation.sBuffer)
				if value and value != 100:
					self["status"].setText(_("Buffering %d%%") % value)
					if not self.shown:
						self.show()

	def __evStart(self):
		self.mayShow = True
		self.hide()

	def __evGstreamerPlayStarted(self):
		self.mayShow = False
		self.hide()


class InfoBarBuffer():
	def __init__(self):
		self.bufferScreen = self.session.instantiateDialog(BufferIndicator)
		self.bufferScreen.hide()


class NumberZap(Screen):
	def __init__(self, session, number, searchNumberFunction=None):
		Screen.__init__(self, session)
		if config.usage.numzappicon.value:
			self.onLayoutFinish.append(self.showPicon)
			self.skinName = ["NumberZapPicon", "NumberZapWithName"]
		self.onChangedEntry = []
		self.numberString = str(number)
		self.field = str(number)
		self.searchNumber = searchNumberFunction
		self.startBouquet = None
		self["channel"] = Label(_("Channel") + ":")
		self["channel_summary"] = StaticText(_("Channel") + ":")
		self["number"] = Label(self.numberString)
		self["servicenumber"] = Label(self.numberString)
		self["number_summary"] = StaticText(self.numberString)
		self["servicename"] = Label()
		self["service_summary"] = StaticText("")
		self["Service"] = ServiceEvent()
		self.handleServiceName()
		self["service_summary"].setText(self["servicename"].getText())
		self["actions"] = HelpableNumberActionMap(self, ["OkCancelActions", "NumberActions", "ColorActions"], {
			"cancel": (self.quit, _("Cancel the selection")),
			"ok": (self.keyOK, _("Select/Zap to the selected service")),
			"blue": (self.keyBlue, _("Toggle service name display")),
			"1": (self.keyNumberGlobal, _("Digit entry for service selection")),
			"2": (self.keyNumberGlobal, _("Digit entry for service selection")),
			"3": (self.keyNumberGlobal, _("Digit entry for service selection")),
			"4": (self.keyNumberGlobal, _("Digit entry for service selection")),
			"5": (self.keyNumberGlobal, _("Digit entry for service selection")),
			"6": (self.keyNumberGlobal, _("Digit entry for service selection")),
			"7": (self.keyNumberGlobal, _("Digit entry for service selection")),
			"8": (self.keyNumberGlobal, _("Digit entry for service selection")),
			"9": (self.keyNumberGlobal, _("Digit entry for service selection")),
			"0": (self.keyNumberGlobal, _("Digit entry for service selection"))
		}, prio=0, description=_("Service Selection Actions"))
		self.Timer = eTimer()
		self.Timer.callback.append(self.keyOK)
		if config.usage.numberZapDigits.value == 1:
			self.Timer.start(100, True)
		elif config.usage.numberZapTimeouts.value != "off":
			if config.usage.numberZapTimeouts.value == "default":
				self.Timer.start(3000, True)
			else:
				self.Timer.start(config.usage.numberZapTimeoutFirst.value, True)

	def quit(self):
		self.Timer.stop()
		self.close()

	def keyOK(self):
		self.Timer.stop()
		self.close(self.service, self.bouquet)

	def handleServiceName(self):
		if self.searchNumber:
			self.service, self.bouquet = self.searchNumber(int(self["number"].getText()), recursive=True)
			self["servicename"].setText(ServiceReference(self.service).getServiceName())
			if not self.startBouquet:
				self.startBouquet = self.bouquet

	def keyBlue(self):
		self.Timer.start(3000, True)
		if self.searchNumber:
			if self.startBouquet == self.bouquet:
				self.service, self.bouquet = self.searchNumber(int(self["number"].getText()), firstBouquetOnly=True)
			else:
				self.service, self.bouquet = self.searchNumber(int(self["number"].getText()))
			self["servicename"].setText(ServiceReference(self.service).getServiceName())

	def keyNumberGlobal(self, number):
		if config.usage.numberZapTimeouts.value != "off":
			if config.usage.numberZapTimeouts.value == "default":
				self.Timer.start(1000, True)
			else:
				self.Timer.start(config.usage.numberZapTimeoutOther.value, True)
		self.numberString += str(number)
		self["number"].setText(self.numberString)
		self["servicenumber"].setText(self.numberString)
		self["number_summary"].setText(self.numberString)
		self.field = self.numberString
		self.handleServiceName()
		self["service_summary"].setText(self["servicename"].getText())
		if config.usage.numzappicon.value:
			self.showPicon()
		if len(self.numberString) >= config.usage.numberZapDigits.value:
			if self.Timer.isActive():
				self.Timer.stop()
			self.Timer.start(100, True)

	def showPicon(self):
		self["Service"].newService(self.service)


class InfoBarNumberZap:
	""" Handles an initial number for NumberZapping """

	def __init__(self):
		def digitHelp():
			return _("Digit entry for service selection")

		self["NumberActions"] = HelpableNumberActionMap(self, ["NumberActions"], {
			"1": (self.keyNumberGlobal, digitHelp()),
			"2": (self.keyNumberGlobal, digitHelp()),
			"3": (self.keyNumberGlobal, digitHelp()),
			"4": (self.keyNumberGlobal, digitHelp()),
			"5": (self.keyNumberGlobal, digitHelp()),
			"6": (self.keyNumberGlobal, digitHelp()),
			"7": (self.keyNumberGlobal, digitHelp()),
			"8": (self.keyNumberGlobal, digitHelp()),
			"9": (self.keyNumberGlobal, digitHelp()),
			"0": (self.keyNumberGlobal, digitHelp())
		}, prio=0, description=_("Service Selection Actions"))

	def keyNumberGlobal(self, number):
		if "PTSSeekPointer" in self.pvrStateDialog and self.timeshiftEnabled() and self.isSeekable():
			InfoBarTimeshiftState._mayShow(self)
			self.pvrStateDialog["PTSSeekPointer"].setPosition((self.pvrStateDialog["PTSSeekBack"].instance.size().width() - 4) / 2, self.pvrStateDialog["PTSSeekPointer"].position[1])
			if self.seekstate != self.SEEK_STATE_PLAY:
				self.setSeekState(self.SEEK_STATE_PLAY)
			self.ptsSeekPointerOK()
			return
		seekable = self.getSeek()
		if seekable:
			length = seekable.getLength() or (None, 0)
			if length[1] > 0:
				key = int(number)
				time = (-config.seek.selfdefined_13.value, False, config.seek.selfdefined_13.value,
					-config.seek.selfdefined_46.value, False, config.seek.selfdefined_46.value,
					-config.seek.selfdefined_79.value, False, config.seek.selfdefined_79.value)[key - 1]

				time = time * 90000
				seekable.seekRelative(time < 0 and -1 or 1, abs(time))
				return
		if self.pts_blockZap_timer.isActive():
			return
		# if self.save_current_timeshift and self.timeshiftEnabled():
		# 	InfoBarTimeshift.saveTimeshiftActions(self)
		# 	return
		if number == 0:
			if isinstance(self, InfoBarPiP) and self.pipHandles0Action():
				self.pipDoHandle0Action()
			elif self.servicelist.history and self.servicelist.isSubservices():
				self.servicelist.setHistoryPath()
			elif len(self.servicelist.history) > 1 or config.usage.panicbutton.value:
				self.checkTimeshiftRunning(self.recallPrevService)
		else:
			if "TimeshiftActions" in self and self.timeshiftEnabled():
				ts = self.getTimeshift()
				if ts and ts.isTimeshiftActive():
					return
			self.session.openWithCallback(self.numberEntered, NumberZap, number, self.searchNumber)

	def recallPrevService(self, reply):
		if reply:
			if config.usage.panicbutton.value:
				if self.session.pipshown:
					del self.session.pip
					self.session.pipshown = False
				self.servicelist.history_tv = []
				self.servicelist.history_radio = []
				self.servicelist.history = self.servicelist.history_tv
				self.servicelist.history_pos = 0
				self.servicelist2.history_tv = []
				self.servicelist2.history_radio = []
				self.servicelist2.history = self.servicelist.history_tv
				self.servicelist2.history_pos = 0
				if config.usage.multibouquet.value:
					bqrootstr = "1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"bouquets.tv\" ORDER BY bouquet"
				else:
					self.service_types = service_types_tv
					bqrootstr = "%s FROM BOUQUET \"userbouquet.favourites.tv\" ORDER BY bouquet" % self.service_types
				serviceHandler = eServiceCenter.getInstance()
				rootbouquet = eServiceReference(bqrootstr)
				bouquet = eServiceReference(bqrootstr)
				bouquetlist = serviceHandler.list(bouquet)
				if bouquetlist is not None:
					while True:
						bouquet = bouquetlist.getNext()
						if bouquet.flags & eServiceReference.isDirectory:
							self.servicelist.clearPath()
							self.servicelist.setRoot(bouquet)
							servicelist = serviceHandler.list(bouquet)
							if servicelist is not None:
								serviceIterator = servicelist.getNext()
								while serviceIterator.valid():
									service, bouquet2 = self.searchNumber(config.usage.panicchannel.value)
									if service == serviceIterator:
										break
									serviceIterator = servicelist.getNext()
								if serviceIterator.valid() and service == serviceIterator:
									break
					self.servicelist.enterPath(rootbouquet)
					self.servicelist.enterPath(bouquet)
					self.servicelist.saveRoot()
					self.servicelist2.enterPath(rootbouquet)
					self.servicelist2.enterPath(bouquet)
					self.servicelist2.saveRoot()
				self.selectAndStartService(service, bouquet)
			else:
				self.servicelist.recallPrevService()

	def numberEntered(self, service=None, bouquet=None):
		if service:
			self.selectAndStartService(service, bouquet)

	def searchNumberHelperRecursive(self, serviceHandler, num, bouquet):
		# print("searchNumberHelperRecursive %s" % bouquet.toString())
		servicelist = serviceHandler.list(bouquet)
		if servicelist:
			serviceIterator = servicelist.getNext()
			while serviceIterator.valid():
				if num == serviceIterator.getChannelNum():
					return (serviceIterator, "%s;" % bouquet.toString())
				if serviceIterator.flags & eServiceReference.isDirectory:
					result = self.searchNumberHelperRecursive(serviceHandler, num, serviceIterator)
					if result[0]:
						return (result[0], "%s;%s" % (bouquet.toString(), result[1]))
				serviceIterator = servicelist.getNext()
		return (None, None)

	def searchNumberHelper(self, serviceHandler, num, bouquet):
		servicelist = serviceHandler.list(bouquet)
		if servicelist:
			serviceIterator = servicelist.getNext()
			while serviceIterator.valid():
				if num == serviceIterator.getChannelNum():
					return serviceIterator
				serviceIterator = servicelist.getNext()
		return None

	def searchNumber(self, number, firstBouquetOnly=False, bouquet=None, recursive=False):
		servicepath = None
		bouquet = bouquet or self.servicelist.getRoot()
		service = None
		serviceHandler = eServiceCenter.getInstance()
		if not firstBouquetOnly:
			service = self.searchNumberHelper(serviceHandler, number, bouquet)
		if config.usage.multibouquet.value and not service:
			bouquet = self.servicelist.bouquet_root
			bouquetlist = serviceHandler.list(bouquet)
			if bouquetlist:
				bouquet = bouquetlist.getNext()
				while bouquet.valid():
					if bouquet.flags & eServiceReference.isDirectory:
						if recursive:
							service, servicepath = self.searchNumberHelperRecursive(serviceHandler, number, bouquet)
						else:
							service = self.searchNumberHelper(serviceHandler, number, bouquet)
						if service:
							playable = not (service.flags & (eServiceReference.isMarker | eServiceReference.isDirectory)) or (service.flags & eServiceReference.isNumberedMarker)
							if not playable:
								service = None
							break
						if config.usage.alternative_number_mode.value or firstBouquetOnly:
							break
					bouquet = bouquetlist.getNext()
		if servicepath:
			return service, "%s;%s" % (self.servicelist.bouquet_root.toString(), servicepath)
		else:
			return service, bouquet

	def selectAndStartService(self, service, bouquet):
		if service:
			if isinstance(bouquet, str):
				self.servicelist.lastroot.value = bouquet
				self.servicelist.restoreRoot()
			elif self.servicelist.getRoot() != bouquet:  # Already in correct bouquet?
				self.servicelist.clearPath()
				if self.servicelist.bouquet_root != bouquet:
					self.servicelist.enterPath(self.servicelist.bouquet_root)
				self.servicelist.enterPath(bouquet)
			self.servicelist.setCurrentSelection(service)  # Select the service in the service list.
			self.servicelist.zap(enable_pipzap=True)
			self.servicelist.correctChannelNumber()
			self.servicelist.startRoot = None

	def zapToNumber(self, number):
		service, bouquet = self.searchNumber(number)
		self.selectAndStartService(service, bouquet)


config.misc.initialchannelselection = ConfigBoolean(default=True)


class InfoBarChannelSelection:
	"""ChannelSelection - handles the channelSelection dialog and the initial
	channelChange actions which open the channelSelection dialog."""

	def __init__(self):
		def serviceZapHelp(direction):
			match direction:
				case "previous":
					helpText = _("Zap to previous service in the current bouquet")
				case "next":
					helpText = _("Zap to next service in the current bouquet")
			return helpText

		def serviceListHelp(direction):
			match direction:
				case "up":
					helpText = _("Open service list and select previous channel")
				case "down":
					helpText = _("Open service list and select next channel")
			return helpText

		def pipListHelp(direction):
			match direction:
				case "up":
					helpText = _("Open service list and select previous channel for PiP")
				case "down":
					helpText = _("Open service list and select next channel for PiP")
			return helpText

		# Instantiate forever.
		self.servicelist = self.session.instantiateDialog(ChannelSelection)
		self.servicelist2 = self.session.instantiateDialog(PiPZapSelection)
		self.tscallback = None
		if config.misc.initialchannelselection.value:
			self.onShown.append(self.firstRun)
		self["ChannelSelectActions"] = HelpableActionMap(self, "InfobarChannelSelection", {
			"switchChannelUp": (self.UpPressed, serviceListHelp("up")),
			"switchChannelDown": (self.DownPressed, serviceListHelp("down")),
			"switchChannelUpLong": (self.switchChannelUp, pipListHelp("up")),
			"switchChannelDownLong": (self.switchChannelDown, pipListHelp("down")),
			"zapUp": (self.zapUp, _("Zap to previous service")),
			"zapDown": (self.zapDown, _("Zap to next service")),
			"historyBack": (self.historyBack, _("Zap to previous service in the history")),
			"historyNext": (self.historyNext, _("Zap to next service in the history")),
			"openServiceList": (self.openServiceList, _("Open Services / Reception selection")),
			"openSatellites": (self.openSatellites, _("Open Satellites selection")),
			"openBouquets": (self.openBouquets, _("Open Bouquet selection")),
			"LeftPressed": (self.LeftPressed, serviceZapHelp("previous")),
			"RightPressed": (self.RightPressed, serviceZapHelp("next")),
			"ChannelPlusPressed": (self.ChannelPlusPressed, serviceZapHelp("next")),
			"ChannelMinusPressed": (self.ChannelMinusPressed, serviceZapHelp("previous")),
			"ChannelPlusPressedLong": (self.ChannelPlusPressed, serviceZapHelp("next")),
			"ChannelMinusPressedLong": (self.ChannelMinusPressed, serviceZapHelp("previous"))
		}, prio=0, description=_("Service Selection Actions"))

	def firstRun(self):
		self.onShown.remove(self.firstRun)
		config.misc.initialchannelselection.value = False
		config.misc.initialchannelselection.save()
		self.openServiceList()

	def LeftPressed(self):
		if config.plisettings.InfoBarEpg_mode.value == "3":
			self.openInfoBarEPG()
		else:
			self.zapUp()

	def RightPressed(self):
		if config.plisettings.InfoBarEpg_mode.value == "3":
			self.openInfoBarEPG()
		else:
			self.zapDown()

	def UpPressed(self):
		if config.usage.updownbutton_mode.value == "0":
			self.zapDown()
		elif config.usage.updownbutton_mode.value == "1":
			self.switchChannelUp()

	def DownPressed(self):
		if config.usage.updownbutton_mode.value == "0":
			self.zapUp()
		elif config.usage.updownbutton_mode.value == "1":
			self.switchChannelDown()

	def ChannelPlusPressed(self):
		if config.usage.channelbutton_mode.value == "0":
			self.zapDown()
		elif config.usage.channelbutton_mode.value == "1" or config.usage.channelbutton_mode.value == "3":
			self.openServiceList()
		elif config.usage.channelbutton_mode.value == "2":
			self.serviceListType = "Norm"
			self.servicelist.showFavourites()
			self.openServiceList()

	def ChannelMinusPressed(self):
		if config.usage.channelbutton_mode.value == "0":
			self.zapUp()
		elif config.usage.channelbutton_mode.value == "1" or config.usage.channelbutton_mode.value == "3":
			self.openServiceList()
		elif config.usage.channelbutton_mode.value == "2":
			self.serviceListType = "Norm"
			self.servicelist.showFavourites()
			self.openServiceList()

	def showTvChannelList(self, zap=False):
		self.servicelist.setModeTv()
		if zap:
			self.servicelist.zap()
		if config.usage.show_servicelist.value:
			self.openServiceList()

	def showRadioChannelList(self, zap=False):
		self.servicelist.setModeRadio()
		if zap:
			self.servicelist.zap()
		if config.usage.show_servicelist.value:
			self.openServiceList()

	def historyBack(self):
		if config.usage.historymode.value == "0":
			self.servicelist.historyBack()
		else:
			self.servicelist.historyZap(-1)

	def historyNext(self):
		if config.usage.historymode.value == "0":
			self.servicelist.historyNext()
		else:
			self.servicelist.historyZap(+1)

	def switchChannelUp(self):
		if not self.secondInfoBarScreen or not self.secondInfoBarScreen.shown:
			self.keyHide(False)
			if not self.LongButtonPressed or BoxInfo.getItem("NumVideoDecoders", 1) <= 1:
				if not config.usage.show_bouquetalways.value:
					if "keep" not in config.usage.servicelist_cursor_behavior.value:
						self.servicelist.moveUp()
					self.openServiceList()
				else:
					self.servicelist.showFavourites()
					self.openServiceList()
			elif self.LongButtonPressed:
				if not config.usage.show_bouquetalways.value:
					if "keep" not in config.usage.servicelist_cursor_behavior.value:
						self.servicelist2.moveUp()
					self.openServiceListPiP()
				else:
					self.servicelist2.showFavourites()
					self.openServiceListPiP()

	def switchChannelDown(self):
		if not self.secondInfoBarScreen or not self.secondInfoBarScreen.shown:
			self.keyHide(False)
			if not self.LongButtonPressed or BoxInfo.getItem("NumVideoDecoders", 1) <= 1:
				if not config.usage.show_bouquetalways.value:
					if "keep" not in config.usage.servicelist_cursor_behavior.value:
						self.servicelist.moveDown()
					self.openServiceList()
				else:
					self.servicelist.showFavourites()
					self.openServiceList()
			elif self.LongButtonPressed:
				if not config.usage.show_bouquetalways.value:
					if "keep" not in config.usage.servicelist_cursor_behavior.value:
						self.servicelist2.moveDown()
					self.openServiceListPiP()
				else:
					self.servicelist2.showFavourites()
					self.openServiceListPiP()

	def openServiceList(self):
		if config.skin.autorefresh.value:
			self.servicelist.servicelist.reloadSkin()
		self.session.execDialog(self.servicelist)

	def openServiceListPiP(self):
		self.session.execDialog(self.servicelist2)

	def openSatellites(self):
		self.servicelist.showSatellites()
		self.openServiceList()

	def openBouquets(self):
		self.servicelist.showFavourites()
		self.openServiceList()

	def openSubservices(self):
		self.servicelist.enterSubservices()
		self.openServiceList()

	def zapUp(self):
		if not self.LongButtonPressed or BoxInfo.getItem("NumVideoDecoders", 1) <= 1:
			if self.pts_blockZap_timer.isActive():
				return
			self["SeekActionsPTS"].setEnabled(False)
			if self.servicelist.inBouquet():
				prev = self.servicelist.getCurrentSelection()
				if prev:
					isIPTV = "://" in prev.getPath()  # Workaround: Ignore IPTV channel streaming.
					prev = prev.toString()
					while True:
						if config.usage.quickzap_bouquet_change.value and self.servicelist.atBegin():
							self.servicelist.prevBouquet()
							self.servicelist.moveEnd()
						else:
							self.servicelist.moveUp()
						cur = self.servicelist.getCurrentSelection()
						if cur:
							if self.servicelist.dopipzap:
								isPlayable = isIPTV or self.session.pip.isPlayableForPipService(cur)
							else:
								isPlayable = isIPTV or isPlayableForCur(cur)
						if cur and (cur.toString() == prev or isPlayable):
							break
			else:
				self.servicelist.moveUp()
			self.servicelist.zap(enable_pipzap=True)
		elif self.LongButtonPressed:
			if not hasattr(self.session, "pip") and not self.session.pipshown:
				self.session.open(MessageBox, _("Please open Picture in Picture first"), MessageBox.TYPE_ERROR)
				return
			from Screens.ChannelSelection import ChannelSelection
			ChannelSelectionInstance = ChannelSelection.instance
			ChannelSelectionInstance.dopipzap = True
			if self.servicelist2.inBouquet():
				prev = self.servicelist2.getCurrentSelection()
				if prev:
					isIPTV = "://" in prev.getPath()  # Workaround: Ignore IPTV channel streaming.
					prev = prev.toString()
					while True:
						if config.usage.quickzap_bouquet_change.value and self.servicelist2.atBegin():
							self.servicelist2.prevBouquet()
							self.servicelist2.moveEnd()
						else:
							self.servicelist2.moveUp()
						cur = self.servicelist2.getCurrentSelection()
						if cur:
							if ChannelSelectionInstance.dopipzap:
								isPlayable = isIPTV or self.session.pip.isPlayableForPipService(cur)
							else:
								isPlayable = isIPTV or isPlayableForCur(cur)
						if cur and (cur.toString() == prev or isPlayable):
							break
			else:
				self.servicelist2.moveUp()
			self.servicelist2.zap(enable_pipzap=True)
			ChannelSelectionInstance.dopipzap = False
		if self.timeshiftEnabled() and self.isSeekable():
			self["SeekActionsPTS"].setEnabled(True)

	def zapDown(self):
		if not self.LongButtonPressed or BoxInfo.getItem("NumVideoDecoders", 1) <= 1:
			if self.pts_blockZap_timer.isActive():
				return
			self["SeekActionsPTS"].setEnabled(False)
			if self.servicelist.inBouquet():
				prev = self.servicelist.getCurrentSelection()
				if prev:
					isIPTV = "://" in prev.getPath()  # Workaround: Ignore IPTV channel streaming.
					prev = prev.toString()
					while True:
						if config.usage.quickzap_bouquet_change.value and self.servicelist.atEnd():
							self.servicelist.nextBouquet()
							self.servicelist.moveTop()
						else:
							self.servicelist.moveDown()
						cur = self.servicelist.getCurrentSelection()
						if cur:
							if self.servicelist.dopipzap:
								isPlayable = isIPTV or self.session.pip.isPlayableForPipService(cur)
							else:
								isPlayable = isIPTV or isPlayableForCur(cur)
						if cur and (cur.toString() == prev or isPlayable):
							break
			else:
				self.servicelist.moveDown()
			self.servicelist.zap(enable_pipzap=True)
		elif self.LongButtonPressed:
			if not hasattr(self.session, "pip") and not self.session.pipshown:
				self.session.open(MessageBox, _("Please open Picture in Picture first"), MessageBox.TYPE_ERROR)
				return
			from Screens.ChannelSelection import ChannelSelection
			ChannelSelectionInstance = ChannelSelection.instance
			ChannelSelectionInstance.dopipzap = True
			if self.servicelist2.inBouquet():
				prev = self.servicelist2.getCurrentSelection()
				if prev:
					isIPTV = "://" in prev.getPath()  # Workaround: Ignore IPTV channel streaming.
					prev = prev.toString()
					while True:
						if config.usage.quickzap_bouquet_change.value and self.servicelist2.atEnd():
							self.servicelist2.nextBouquet()
							self.servicelist2.moveTop()
						else:
							self.servicelist2.moveDown()
						cur = self.servicelist2.getCurrentSelection()
						if cur:
							if ChannelSelectionInstance.dopipzap:
								isPlayable = isIPTV or self.session.pip.isPlayableForPipService(cur)
							else:
								isPlayable = isIPTV or isPlayableForCur(cur)
						if cur and (cur.toString() == prev or isPlayable):
							break
			else:
				self.servicelist2.moveDown()
			self.servicelist2.zap(enable_pipzap=True)
			ChannelSelectionInstance.dopipzap = False
		if self.timeshiftEnabled() and self.isSeekable():
			self["SeekActionsPTS"].setEnabled(True)

	def volumeUp(self):  # Called from ButtonSetup
		VolumeControl.instance.keyVolumeUp()

	def volumeDown(self):  # Called from ButtonSetup
		VolumeControl.instance.keyVolumeDown()


class InfoBarSimpleEventView:
	""" Opens the Eventview for now/next """

	def __init__(self):
		self["EventViewActions"] = HelpableActionMap(self, "InfobarEPGActions", {
			"showEventInfo": (self.openEventView, _("Open event information")),
			"InfoPressed": (self.openEventView, _("Open event information")),
			"showInfobarOrEpgWhenInfobarAlreadyVisible": self.showEventInfoWhenNotVisible,
		}, prio=0, description=_("Event View Actions"))

	def openEventView(self, simple=False):
		if self.servicelist is None:
			return
		ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.getNowNext()
		epglist = self.epglist
		if not epglist:
			self.is_now_next = False
			epg = eEPGCache.getInstance()
			ptr = ref and ref.valid() and epg.lookupEventTime(ref, -1)
			if ptr:
				epglist.append(ptr)
				ptr = epg.lookupEventTime(ref, ptr.getBeginTime(), +1)
				if ptr:
					epglist.append(ptr)
		else:
			self.is_now_next = True
		if epglist:
			if not simple:
				self.eventView = self.session.openWithCallback(self.closed, EventViewEPGSelect, epglist[0], ServiceReference(ref), self.eventViewCallback, self.openSingleServiceEPG, self.openMultiServiceEPG, self.openSimilarList)
			else:
				self.eventView = self.session.openWithCallback(self.closed, EventViewSimple, epglist[0], ServiceReference(ref))
			self.dlg_stack.append(self.eventView)

	def eventViewCallback(self, setEvent, setService, val):  # Used for Now/Next display.
		epglist = self.epglist
		if len(epglist) > 1:
			tmp = epglist[0]
			epglist[0] = epglist[1]
			epglist[1] = tmp
			setEvent(epglist[0])

	def showEventInfoWhenNotVisible(self):
		if self.shown:
			self.openEventView()
		else:
			self.toggleShow()
			return 1


class SimpleServicelist:
	def __init__(self, services):
		self.services = services
		self.length = len(services)
		self.current = 0

	def selectService(self, service):
		if not self.length:
			self.current = -1
			return False
		else:
			self.current = 0
			while self.services[self.current].ref != service:
				self.current += 1
				if self.current >= self.length:
					return False
		return True

	def nextService(self):
		if not self.length:
			return
		if self.current + 1 < self.length:
			self.current += 1
		else:
			self.current = 0

	def prevService(self):
		if not self.length:
			return
		if self.current - 1 > -1:
			self.current -= 1
		else:
			self.current = self.length - 1

	def currentService(self):
		if not self.length or self.current >= self.length:
			return None
		return self.services[self.current]


class InfoBarEPG:
	""" EPG - Opens an EPG list when the showEPGList action fires """

	def __init__(self):
		self.is_now_next = False
		self.dlg_stack = []
		self.bouquetSel = None
		self.eventView = None
		self.isInfo = None
		self.epglist = []
		self.defaultGuideType = self.getDefaultGuidetype()
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evUpdatedEventInfo: self.__evEventInfoChanged,
			iPlayableService.evUpdateTags: self.__evEventInfoChanged
		})
		self["EPGActions"] = HelpableActionMap(self, "InfobarEPGActions", {
			"IPressed": (self.IPressed, _("Open event information")),
			"InfoPressed": (self.InfoPressed, _("Open event information")),
			"showEventInfoPlugin": (self.showEventInfoPlugins, _("List available EPG functions")),
			"EPGPressed": (self.EPGPressed, _("Open EPG")),
			"showEventGuidePlugin": (self.showEventGuidePlugins, _("List available EPG functions")),
			"showInfobarOrEpgWhenInfobarAlreadyVisible": self.showEventInfoWhenNotVisible,
		}, prio=0, description=_("EPG Actions"))

	def getEPGPluginList(self):
		pluginlist = [(p.name, boundFunction(self.runPlugin, p)) for p in plugins.getPlugins(where=PluginDescriptor.WHERE_EVENTINFO)]
		if pluginlist:
			pluginlist.append((_("Event Info"), self.openEventView))
			pluginlist.append((_("Graphical EPG"), self.openGraphEPG))
			pluginlist.append((_("Vertical EPG"), self.openVerticalEPG))
			pluginlist.append((_("InfoBar EPG"), self.openInfoBarEPG))
			pluginlist.append((_("Multi EPG"), self.openMultiServiceEPG))
			pluginlist.append((_("Open EPG for current service"), self.openSingleServiceEPG))
		return pluginlist

	def showEventInfoPlugins(self):
		if isMoviePlayerInfoBar(self):
			self.openEventView()
		else:
			pluginlist = self.getEPGPluginList()
			if pluginlist:
				self.session.openWithCallback(self.EventInfoPluginChosen, ChoiceBox, title=_("Please choose an extension..."), list=pluginlist, skin_name="EPGExtensionsList")
			else:
				self.openSingleServiceEPG()

	def getDefaultGuidetype(self):
		pluginlist = self.getEPGPluginList()
		config.usage.defaultGuideType = ConfigSelection(default="None", choices=pluginlist)
		for plugin in pluginlist:
			if plugin[0] == config.usage.defaultGuideType.value:
				return plugin[1]
		return None

	def showEventGuidePlugins(self):
		if isMoviePlayerInfoBar(self):
			self.openEventView()
		else:
			pluginlist = self.getEPGPluginList()
			if pluginlist:
				pluginlist.append((_("Select default EPG type..."), self.SelectDefaultGuidePlugin))
				self.session.openWithCallback(self.EventGuidePluginChosen, ChoiceBox, title=_("Please choose an extension..."), list=pluginlist, skin_name="EPGExtensionsList")
			else:
				self.openSingleServiceEPG()

	def SelectDefaultGuidePlugin(self):
		self.session.openWithCallback(self.DefaultGuidePluginChosen, ChoiceBox, title=_("Please select a default EPG type..."), list=self.getEPGPluginList(), skin_name="EPGExtensionsList")

	def DefaultGuidePluginChosen(self, answer):
		if answer is not None:
			self.defaultGuideType = answer[1]
			config.usage.defaultGuideType.value = answer[0]
			config.usage.defaultGuideType.save()

	def EventGuidePluginChosen(self, answer):
		if answer is not None:
			answer[1]()

	def runPlugin(self, plugin):
		plugin(session=self.session, servicelist=self.servicelist)

	def EventInfoPluginChosen(self, answer):
		if answer is not None:
			answer[1]()

	def InfoPressed(self):
		if isStandardInfoBar(self) or isMoviePlayerInfoBar(self):
			if config.plisettings.PLIINFO_mode.value == "eventview":
				self.openEventView()
			elif config.plisettings.PLIINFO_mode.value == "epgpress":
				self.EPGPressed()
			elif config.plisettings.PLIINFO_mode.value == "single":
				self.openSingleServiceEPG()
			else:
				if config.plisettings.PLIINFO_mode.value != "infobar":
					self.EPGPressed()

	def IPressed(self):
		if isStandardInfoBar(self) or isMoviePlayerInfoBar(self):
			self.openEventView()

	def EPGPressed(self):
		if isStandardInfoBar(self) or isMoviePlayerInfoBar(self):
			if config.plisettings.PLIEPG_mode.value == "pliepg":
				self.openGraphEPG()
			elif config.plisettings.PLIEPG_mode.value == "multi":
				self.openMultiServiceEPG()
			elif config.plisettings.PLIEPG_mode.value == "single":
				self.openSingleServiceEPG()
			elif config.plisettings.PLIEPG_mode.value == "vertical":
				self.openVerticalEPG()
			# elif config.plisettings.PLIEPG_mode.value == "merlinepgcenter":
			# 	self.openMerlinEPGCenter()
			elif config.plisettings.PLIEPG_mode.value == "eventview":
				self.openEventView()
			else:
				self.openSingleServiceEPG()

	def showEventInfoWhenNotVisible(self):
		if self.shown:
			self.openEventView()
		else:
			self.toggleShow()
			return 1

	def zapToService(self, service, bouquet=None, preview=False, zapback=False):
		if self.servicelist.startServiceRef is None:
			self.servicelist.startServiceRef = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.servicelist.currentServiceRef = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if service is not None:
			if self.servicelist.getRoot() != bouquet:  # Already in correct bouquet?
				self.servicelist.clearPath()
				if self.servicelist.bouquet_root != bouquet:
					self.servicelist.enterPath(self.servicelist.bouquet_root)
				self.servicelist.enterPath(bouquet)
			self.servicelist.setCurrentSelection(service)  # Select the service in the service list.
		if not zapback or preview:
			self.servicelist.zap(preview_zap=preview)
		if (self.servicelist.dopipzap or zapback) and not preview:
			self.servicelist.zapBack()
		if not preview:
			self.servicelist.startServiceRef = None
			self.servicelist.startRoot = None

	def getBouquetServices(self, bouquet):
		services = []
		servicelist = eServiceCenter.getInstance().list(bouquet)
		if servicelist is not None:
			while True:
				service = servicelist.getNext()
				if not service.valid():  # Check if end of list.
					break
				if service.flags & (eServiceReference.isDirectory | eServiceReference.isMarker):  # Ignore non playable services.
					continue
				services.append(ServiceReference(service))
		return services

	def openBouquetEPG(self, bouquet=None, bouquets=None):
		if bouquet:
			self.StartBouquet = bouquet
		elif bouquets and not self.servicelist.isSubservices():
			root = self.servicelist.getRoot()
			if root.toString().startswith((service_types_tv, service_types_radio)):  # Current service not found in any bouquet so add all services
				bouquets.insert(0, (self.servicelist.getServiceName(root), root))
		self.dlg_stack.append(self.session.openWithCallback(self.closed, EPGSelection, None, zapFunc=self.zapToService, EPGtype=self.EPGtype, StartBouquet=self.StartBouquet, StartRef=self.StartRef, bouquets=bouquets))

	def closed(self, ret=False):
		if not self.dlg_stack:
			return
		closedScreen = self.dlg_stack.pop()
		if self.bouquetSel and closedScreen == self.bouquetSel:
			self.bouquetSel = None
		elif self.eventView and closedScreen == self.eventView:
			self.eventView = None
		if ret is True or ret == "close":
			dlgs = len(self.dlg_stack)
			if dlgs > 0:
				self.dlg_stack[dlgs - 1].close(dlgs > 1)
		self.reopen(ret)

	def MultiServiceEPG(self):
		bouquets = self.servicelist.getBouquetList()
		if bouquets is None:
			cnt = 0
		else:
			cnt = len(bouquets)
		if (self.EPGtype == "multi" and config.epgselection.multi_showbouquet.value) or (self.EPGtype == "graph" and config.epgselection.graph_showbouquet.value):
			if cnt > 1:  # Show bouquet list.
				self.bouquetSel = self.session.openWithCallback(self.closed, EpgBouquetSelector, bouquets, self.openBouquetEPG, enableWrapAround=True)
				self.dlg_stack.append(self.bouquetSel)
			elif cnt == 1:
				self.openBouquetEPG(bouquets=bouquets)
		else:
			self.openBouquetEPG(bouquets=bouquets)

	def openMultiServiceEPG(self):
		if self.servicelist is None:
			return
		self.EPGtype = "multi"
		self.StartBouquet = self.servicelist.getRoot()
		if isMoviePlayerInfoBar(self):
			self.StartRef = self.lastservice
		else:
			self.StartRef = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.MultiServiceEPG()

	def openGraphEPG(self, reopen=False):
		if self.servicelist is None:
			return
		self.EPGtype = "graph"
		if not reopen:
			self.StartBouquet = self.servicelist.getRoot()
			self.StartRef = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.MultiServiceEPG()

	def openSingleServiceEPG(self, reopen=False):
		if self.servicelist is None:
			return
		self.EPGtype = "enhanced"
		self.SingleServiceEPG()

	def openVerticalEPG(self, reopen=False):
		if self.servicelist is None:
			return
		if not reopen:
			self.StartBouquet = self.servicelist.getRoot()
			self.StartRef = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.EPGtype = "vertical"
		self.VerticalEPG()

	def VerticalEPG(self):
		# self.StartBouquet = self.servicelist.getRoot()
		# self.StartRef = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		bouquets = self.servicelist.getBouquetList()
		self.dlg_stack.append(self.session.openWithCallback(self.closed, EPGSelection, self.servicelist, zapFunc=self.zapToService, EPGtype=self.EPGtype, StartBouquet=self.StartBouquet, StartRef=self.StartRef, bouquets=bouquets))

	def openInfoBarEPG(self, reopen=False):
		if self.servicelist is None:
			return
		if not reopen:
			self.StartBouquet = self.servicelist.getRoot()
			self.StartRef = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if config.epgselection.infobar_type_mode.value == "single":
			self.EPGtype = "infobar"
			self.SingleServiceEPG()
		else:
			self.EPGtype = "infobargraph"
			self.MultiServiceEPG()

	def SingleServiceEPG(self):
		self.StartBouquet = self.servicelist.getRoot()
		self.StartRef = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if isMoviePlayerInfoBar(self):
			ref = self.lastservice
		else:
			ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if ref:
			services = self.getBouquetServices(self.StartBouquet)
			self.serviceSel = SimpleServicelist(services)
			if self.serviceSel.selectService(ref):
				self.session.openWithCallback(self.SingleServiceEPGClosed, EPGSelection, self.servicelist, zapFunc=self.zapToService, serviceChangeCB=self.changeServiceCB, EPGtype=self.EPGtype, StartBouquet=self.StartBouquet, StartRef=self.StartRef)
			else:
				self.session.openWithCallback(self.SingleServiceEPGClosed, EPGSelection, ref)

	def changeServiceCB(self, direction, epg):
		if self.serviceSel:
			if direction > 0:
				self.serviceSel.nextService()
			else:
				self.serviceSel.prevService()
			epg.setService(self.serviceSel.currentService())

	def SingleServiceEPGClosed(self, ret=False):
		self.serviceSel = None
		self.reopen(ret)

	def reopen(self, answer):
		if answer == "reopengraph":
			self.openGraphEPG(True)
		elif answer == "reopenvertical":
			self.openVerticalEPG(True)
		elif answer == "reopeninfobargraph" or answer == "reopeninfobar":
			self.openInfoBarEPG(True)
		elif answer == "close" and isMoviePlayerInfoBar(self):
			self.lastservice = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			self.close()

	def openMerlinEPGCenter(self):
		if self.servicelist is None:
			return
		if isPluginInstalled("MerlinEPGCenter"):
			for plugin in plugins.getPlugins([PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_EVENTINFO]):
				if plugin.name == _("Merlin EPG Center"):
					self.runPlugin(plugin)
					break
		else:
			self.session.open(MessageBox, _("The Merlin EPG Center plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def openSimilarList(self, eventid, refstr):
		self.session.open(EPGSelection, refstr, eventid=eventid)

	def getNowNext(self):
		epglist = []
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		ptr = info and info.getEvent(0)
		if ptr and ptr.getEventName() != "":
			epglist.append(ptr)
		ptr = info and info.getEvent(1)
		if ptr and ptr.getEventName() != "":
			epglist.append(ptr)
		self.epglist = epglist

	def __evEventInfoChanged(self):
		self.isInfo = True
		if self.is_now_next and len(self.dlg_stack) == 1:
			self.getNowNext()
			if self.eventView and self.epglist:
				self.eventView.setEvent(self.epglist[0])

	def openEventView(self, simple=False):
		if self.servicelist is None:
			return
		ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.getNowNext()
		epglist = self.epglist
		if not epglist:
			self.is_now_next = False
			epg = eEPGCache.getInstance()
			ptr = ref and ref.valid() and epg.lookupEventTime(ref, -1)
			if ptr:
				epglist.append(ptr)
				ptr = epg.lookupEventTime(ref, ptr.getBeginTime(), +1)
				if ptr:
					epglist.append(ptr)
		else:
			self.is_now_next = True
		if epglist:
			if not simple:
				self.eventView = self.session.openWithCallback(self.closed, EventViewEPGSelect, epglist[0], ServiceReference(ref), self.eventViewCallback, self.openSingleServiceEPG, self.openMultiServiceEPG, self.openSimilarList)
			else:
				self.eventView = self.session.openWithCallback(self.closed, EventViewSimple, epglist[0], ServiceReference(ref))
			self.dlg_stack.append(self.eventView)

	def eventViewCallback(self, setEvent, setService, val):  # Used for Now/Next display.
		epglist = self.epglist
		if len(epglist) > 1:
			tmp = epglist[0]
			epglist[0] = epglist[1]
			epglist[1] = tmp
			setEvent(epglist[0])


class InfoBarRdsDecoder:
	"""provides RDS and Rass support/display"""

	def __init__(self):
		self.rds_display = self.session.instantiateDialog(RdsInfoDisplay)
		self.session.instantiateSummaryDialog(self.rds_display)
		self.rds_display.setAnimationMode(0)
		self.rass_interactive = None
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evEnd: self.__serviceStopped,
			iPlayableService.evUpdatedRassSlidePic: self.RassSlidePicChanged
		})
		self["RdsActions"] = HelpableActionMap(self, ["InfobarRdsActions"], {
			"startRassInteractive": (self.startRassInteractive, _("Start RDS interactive"))
		}, prio=-1, description=_("RDS Actions"))
		self["RdsActions"].setEnabled(False)
		self.onLayoutFinish.append(self.rds_display.show)
		self.rds_display.onRassInteractivePossibilityChanged.append(self.RassInteractivePossibilityChanged)

	def RassInteractivePossibilityChanged(self, state):
		self["RdsActions"].setEnabled(state)

	def RassSlidePicChanged(self):
		if not self.rass_interactive:
			service = self.session.nav.getCurrentService()
			decoder = service and service.rdsDecoder()
			if decoder:
				decoder.showRassSlidePicture()

	def __serviceStopped(self):
		if self.rass_interactive is not None:
			rass_interactive = self.rass_interactive
			self.rass_interactive = None
			rass_interactive.close()

	def startRassInteractive(self):
		self.rds_display.hide()
		self.rass_interactive = self.session.openWithCallback(self.RassInteractiveClosed, RassInteractive)

	def RassInteractiveClosed(self, *val):
		if self.rass_interactive is not None:
			self.rass_interactive = None
			self.RassSlidePicChanged()
		self.rds_display.show()


class Seekbar(Screen):
	def __init__(self, session, fwd):
		Screen.__init__(self, session)
		self.setTitle(_("Seek"))
		self.fwd = fwd
		self.percent = 0.0
		self.length = None
		service = session.nav.getCurrentService()
		if service:
			self.seek = service.seek()
			if self.seek:
				self.length = self.seek.getLength()
				position = self.seek.getPlayPosition()
				if self.length and position and int(self.length[1]) > 0:
					if int(position[1]) > 0:
						self.percent = float(position[1]) * 100.0 / float(self.length[1])
				else:
					self.close()
		self["cursor"] = MovingPixmap()
		self["time"] = Label()
		self["actions"] = HelpableActionMap(self, ["WizardActions", "DirectionActions"], {
			"back": (self.exit, _("Cancel the selection")),
			"ok": (self.keyOK, _("Seek forward long")),
			"left": (self.keyLeft, _("Seek back short")),
			"right": (self.keyRight, _("Seek forward  short"))
		}, prio=-1, description=_("Seek Actions"))
		self.cursorTimer = eTimer()
		self.cursorTimer.callback.append(self.updateCursor)
		self.cursorTimer.start(200, False)

	def updateCursor(self):
		if self.length:
			screenwidth = getDesktop(0).size().width()
			if screenwidth and screenwidth == 1920:
				x = 218 + int(4.05 * self.percent)
				self["cursor"].moveTo(x, 23, 1)
			else:
				x = 145 + int(2.7 * self.percent)
				self["cursor"].moveTo(x, 15, 1)
			self["cursor"].startMoving()
			pts = int(float(self.length[1]) / 100.0 * self.percent)
			self["time"].setText("%d:%02d" % ((pts / 60 / 90000), ((pts / 90000) % 60)))

	def exit(self):
		self.cursorTimer.stop()
		self.close()

	def keyOK(self):
		if self.length:
			self.seek.seekTo(int(float(self.length[1]) / 100.0 * self.percent))
			self.exit()

	def keyLeft(self):
		self.percent -= float(config.seek.sensibility.value) / 10.0
		if self.percent < 0.0:
			self.percent = 0.0

	def keyRight(self):
		self.percent += float(config.seek.sensibility.value) / 10.0
		if self.percent > 100.0:
			self.percent = 100.0

	def keyNumberGlobal(self, number):
		sel = self["config"].getCurrent()[1]
		if sel == self.positionEntry:
			self.percent = float(number) * 10.0
		else:
			ConfigListScreen.keyNumberGlobal(self, number)


class InfoBarSeek:
	"""handles actions like seeking, pause"""

	SEEK_STATE_PLAY = (0, 0, 0, ">")
	SEEK_STATE_PAUSE = (1, 0, 0, "||")
	SEEK_STATE_EOF = (1, 0, 0, "END")

	def __init__(self, actionmap="InfobarSeekActions"):
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evSeekableStatusChanged: self.__seekableStatusChanged,
			iPlayableService.evStart: self.__serviceStarted,
			iPlayableService.evEOF: self.__evEOF,
			iPlayableService.evSOF: self.__evSOF,
		})
		self.fast_winding_hint_message_showed = False

		class InfoBarSeekActionMap(HelpableActionMap):
			def __init__(self, screen, *args, **kwargs):
				HelpableActionMap.__init__(self, screen, *args, **kwargs)
				self.screen = screen

			def action(self, contexts, action):
				# print("action:", action)
				if action[:5] == "seek:":
					time = int(action[5:])
					self.screen.doSeekRelative(time * 90000)
					return 1
				elif action[:8] == "seekdef:":
					key = int(action[8:])
					time = (-config.seek.selfdefined_13.value, False, config.seek.selfdefined_13.value,
						-config.seek.selfdefined_46.value, False, config.seek.selfdefined_46.value,
						-config.seek.selfdefined_79.value, False, config.seek.selfdefined_79.value)[key - 1]
					self.screen.doSeekRelative(time * 90000)
					return 1
				else:
					return HelpableActionMap.action(self, contexts, action)

		self["SeekActions"] = InfoBarSeekActionMap(self, actionmap, {
			"playpauseService": (self.playpauseService, _("Pause/Continue playback")),
			"pauseService": (self.pauseService, _("Pause playback")),
			"pauseServiceYellow": (self.pauseServiceYellow, _("Pause playback")),
			"unPauseService": (self.unPauseService, _("Continue playback")),
			"okButton": (self.okButton, _("Continue playback")),
			"seekFwd": (self.seekFwd, _("Seek forward")),
			"seekFwdManual": (self.seekFwdManual, _("Seek forward (enter time)")),
			"seekBack": (self.seekBack, _("Seek backward")),
			"seekBackManual": (self.seekBackManual, _("Seek backward (enter time)")),
			"SeekbarFwd": self.seekFwdSeekbar,
			"SeekbarBack": self.seekBackSeekbar
		}, prio=-1, description=_("Seek Actions"))  # Give them a little more priority to win over the color buttons.
		self["SeekActions"].setEnabled(False)
		self["SeekActionsPTS"] = InfoBarSeekActionMap(self, "InfobarSeekActionsPTS", {
			"playpauseService": (self.playpauseService, _("Pause/Continue playback")),
			"pauseService": (self.pauseService, _("Pause playback")),
			"pauseServiceYellow": (self.pauseServiceYellow, _("Pause playback")),
			"unPauseService": (self.unPauseService, _("Continue playback")),
			"seekFwd": (self.seekFwd, _("Skip forward")),
			"seekFwdManual": (self.seekFwdManual, _("Skip forward (enter time)")),
			"seekBack": (self.seekBack, _("Skip backward")),
			"seekBackManual": (self.seekBackManual, _("Skip backward (enter time)"))
		}, prio=-1, description=_("Seek Actions"))  # Give them a little more priority to win over the color buttons.
		self["SeekActionsPTS"].setEnabled(False)
		self.activity = 0
		self.activityTimer = eTimer()
		self.activityTimer.callback.append(self.doActivityTimer)
		self.seekstate = self.SEEK_STATE_PLAY
		self.lastseekstate = self.SEEK_STATE_PLAY
		self.seekAction = 0
		self.LastseekAction = False
		self.onPlayStateChanged = []
		self.lockedBecauseOfSkipping = False
		self.__seekableStatusChanged()

	def makeStateForward(self, n):
		return 0, n, 0, ">> %dx" % n

	def makeStateBackward(self, n):
		return 0, -n, 0, "<< %dx" % n

	def makeStateSlowMotion(self, n):
		return 0, 0, n, "/%d" % n

	def isStateForward(self, state):
		return state[1] > 1

	def isStateBackward(self, state):
		return state[1] < 0

	def isStateSlowMotion(self, state):
		return state[1] == 0 and state[2] > 1

	def getHigher(self, n, lst):
		for x in lst:
			if x > n:
				return x
		return False

	def getLower(self, n, lst):
		lst = lst[:]
		lst.reverse()
		for x in lst:
			if x < n:
				return x
		return False

	def showAfterSeek(self):
		if isinstance(self, InfoBarShowHide):
			self.doShow()

	def up(self):
		pass

	def down(self):
		pass

	def getSeek(self):
		service = self.session.nav.getCurrentService()
		if service is None:
			return None
		seek = service.seek()
		if seek is None or not seek.isCurrentlySeekable():
			return None
		return seek

	def isSeekable(self):
		if self.getSeek() is None or (isStandardInfoBar(self) and not self.timeshiftEnabled()):
			return False
		return True

	def __seekableStatusChanged(self):
		if isStandardInfoBar(self) and self.timeshiftEnabled():
			pass
		elif not self.isSeekable():
			BoxInfo.setMutableItem("SeekStatePlay", False)
			if exists("/proc/stb/lcd/symbol_hdd"):
				f = open("/proc/stb/lcd/symbol_hdd", "w")
				f.write("0")
				f.close()
			if exists("/proc/stb/lcd/symbol_hddprogress"):
				f = open("/proc/stb/lcd/symbol_hddprogress", "w")
				f.write("0")
				f.close()
			# print("not seekable, return to play")
			self["SeekActions"].setEnabled(False)
			self.setSeekState(self.SEEK_STATE_PLAY)
		else:
			# print("seekable")
			self["SeekActions"].setEnabled(True)
			self.activityTimer.start(int(config.seek.withjumps_repeat_ms.getValue()), False)
			for c in self.onPlayStateChanged:
				c(self.seekstate)
		global seek_withjumps_muted
		if seek_withjumps_muted and eDVBVolumecontrol.getInstance().isMuted(True):
			print("[InfoBarGenerics] STILL MUTED AFTER FFWD/FBACK !!!!!!!! so we unMute")
			seek_withjumps_muted = False
			eDVBVolumecontrol.getInstance().volumeUnMute()

	def doActivityTimer(self):
		if self.isSeekable():
			self.activity += 16
			hdd = 1
			if self.activity >= 100:
				self.activity = 0
			BoxInfo.setMutableItem("SeekStatePlay", True)
			if exists("/proc/stb/lcd/symbol_hdd"):
				if config.lcd.hdd.value:
					file = open("/proc/stb/lcd/symbol_hdd", "w")
					file.write("%d" % int(hdd))
					file.close()
			if exists("/proc/stb/lcd/symbol_hddprogress"):
				if config.lcd.hdd.value:
					file = open("/proc/stb/lcd/symbol_hddprogress", "w")
					file.write("%d" % int(self.activity))
					file.close()
		else:
			self.activityTimer.stop()
			self.activity = 0
			hdd = 0
			self.seekAction = 0
		BoxInfo.setMutableItem("SeekStatePlay", True)
		if exists("/proc/stb/lcd/symbol_hdd"):
			if config.lcd.hdd.value:
				file = open("/proc/stb/lcd/symbol_hdd", "w")
				file.write("%d" % int(hdd))
				file.close()
		if exists("/proc/stb/lcd/symbol_hddprogress"):
			if config.lcd.hdd.value:
				file = open("/proc/stb/lcd/symbol_hddprogress", "w")
				file.write("%d" % int(self.activity))
				file.close()
		if self.LastseekAction:
			self.DoSeekAction()

	def __serviceStarted(self):
		self.fast_winding_hint_message_showed = False
		self.setSeekState(self.SEEK_STATE_PLAY)
		self.__seekableStatusChanged()

	def setSeekState(self, state):
		service = self.session.nav.getCurrentService()
		if service is None:
			return False
		if not self.isSeekable():
			if state not in (self.SEEK_STATE_PLAY, self.SEEK_STATE_PAUSE):
				state = self.SEEK_STATE_PLAY
		pauseable = service.pause()
		if pauseable is None:
			# print("not pauseable.")
			state = self.SEEK_STATE_PLAY
		self.seekstate = state
		if pauseable is not None:
			if self.seekstate[0] and self.seekstate[3] == "||":
				# print("resolved to PAUSE")
				self.activityTimer.stop()
				pauseable.pause()
			elif self.seekstate[0] and self.seekstate[3] == "END":
				# print("resolved to STOP")
				self.activityTimer.stop()
			elif self.seekstate[1]:
				if not pauseable.setFastForward(self.seekstate[1]):
					pass
					# print("resolved to FAST FORWARD")
				else:
					self.seekstate = self.SEEK_STATE_PLAY
					# print("FAST FORWARD not possible: resolved to PLAY")
			elif self.seekstate[2]:
				if not pauseable.setSlowMotion(self.seekstate[2]):
					pass
					# print("resolved to SLOW MOTION")
				else:
					self.seekstate = self.SEEK_STATE_PAUSE
					# print("SLOW MOTION not possible: resolved to PAUSE")
			else:
				# print("resolved to PLAY")
				self.activityTimer.start(int(config.seek.withjumps_repeat_ms.getValue()), False)
				pauseable.unpause()
		for c in self.onPlayStateChanged:
			c(self.seekstate)
		self.checkSkipShowHideLock()
		if hasattr(self, "screenSaverTimerStart"):
			self.screenSaverTimerStart()
		return True

	def okButton(self):
		if self.seekstate == self.SEEK_STATE_PLAY:
			return 0
		elif self.seekstate == self.SEEK_STATE_PAUSE:
			self.pauseService()
		else:
			self.unPauseService()

	def playpauseService(self):
		if self.seekAction != 0:
			self.seekAction = 0
			self.doPause(False)
			global seek_withjumps_muted
			seek_withjumps_muted = False
			return
		if self.seekstate == self.SEEK_STATE_PLAY:
			self.pauseService()
		else:
			if self.seekstate == self.SEEK_STATE_PAUSE:
				if config.seek.on_pause.value == "play":
					self.unPauseService()
				elif config.seek.on_pause.value == "step":
					self.doSeekRelative(1)
				elif config.seek.on_pause.value == "last":
					self.setSeekState(self.lastseekstate)
					self.lastseekstate = self.SEEK_STATE_PLAY
			else:
				self.unPauseService()

	def pauseService(self):
		BoxInfo.setMutableItem("StatePlayPause", True)
		if self.seekstate != self.SEEK_STATE_EOF:
			self.lastseekstate = self.seekstate
		self.setSeekState(self.SEEK_STATE_PAUSE)

	def pauseServiceYellow(self):
		# if config.plugins.infopanel_yellowkey.list.value == "0":
		self.audioSelection()
		# elif config.plugins.infopanel_yellowkey.list.value == "2":
		# 	ToggleVideo()
		# else:
		# 	self.playpauseService()

	def unPauseService(self):
		BoxInfo.setMutableItem("StatePlayPause", False)
		if self.seekstate == self.SEEK_STATE_PLAY:
			if self.seekAction != 0:
				self.playpauseService()
			# return 0  # If 'return 0', plays time shift again from the beginning.
			return
		self.doPause(False)
		self.setSeekState(self.SEEK_STATE_PLAY)
		if config.usage.show_infobar_on_skip.value and not config.usage.show_infobar_locked_on_pause.value:
			self.showAfterSeek()
		self.skipToggleShow = True  # Skip 'break' action (toggleShow) after 'make' action (unPauseService).

	def doPause(self, pause):
		if pause:
			if not eDVBVolumecontrol.getInstance().isMuted(True):
				eDVBVolumecontrol.getInstance().volumeMute()
		else:
			if eDVBVolumecontrol.getInstance().isMuted(True):
				eDVBVolumecontrol.getInstance().volumeUnMute()

	def doSeek(self, pts):
		seekable = self.getSeek()
		if seekable is None:
			return
		seekable.seekTo(pts)

	def doSeekRelativeAvoidStall(self, pts):
		global jump_pts_adder
		global jump_last_pts
		global jump_last_pos
		seekable = self.getSeek()
		# When config.seek.withjumps, avoid that jumps smaller than the time between I-frames result in hanging, by increasing pts when stalled.
		if seekable and config.seek.withjumps_avoid_zero.getValue():
			position = seekable.getPlayPosition()
			if jump_last_pos and jump_last_pts:
				if (abs(position[1] - jump_last_pos[1]) < 100 * 90) and (pts == jump_last_pts):  # Stalled?
					jump_pts_adder += pts
					jump_last_pts = pts
					pts += jump_pts_adder
				else:
					jump_pts_adder = 0
					jump_last_pts = pts
			else:
				jump_last_pts = pts
			jump_last_pos = position
		self.doSeekRelative(pts)

	def doSeekRelative(self, pts):
		try:
			if "<class 'Screens.InfoBar.InfoBar'>" in repr(self):
				if InfoBarTimeshift.timeshiftEnabled(self):
					length = InfoBarTimeshift.ptsGetLength(self)
					position = InfoBarTimeshift.ptsGetPosition(self)
					if length is None or position is None:
						return
					if position + pts >= length:
						InfoBarTimeshift.evEOF(self, position + pts - length)
						self.showAfterSeek()
						return
					elif position + pts < 0:
						InfoBarTimeshift.evSOF(self, position + pts)
						self.showAfterSeek()
						return
		except Exception:
			from sys import exc_info
			print(f"[InfoBarGenerics] InfoBarSeek: Error in 'def doSeekRelative' {exc_info()[:2]}!")
		seekable = self.getSeek()
		if seekable is None or int(seekable.getLength()[1]) < 1:
			return
		prevstate = self.seekstate
		if self.seekstate == self.SEEK_STATE_EOF:
			if prevstate == self.SEEK_STATE_PAUSE:
				self.setSeekState(self.SEEK_STATE_PAUSE)
			else:
				self.setSeekState(self.SEEK_STATE_PLAY)
		seekable.seekRelative(pts < 0 and -1 or 1, abs(pts))
		if (abs(pts) > 100 or not config.usage.show_infobar_locked_on_pause.value) and config.usage.show_infobar_on_skip.value:
			self.showAfterSeek()

	def DoSeekAction(self):
		if self.seekAction > int(config.seek.withjumps_after_ff_speed.getValue()):
			self.doSeekRelativeAvoidStall(self.seekAction * int(config.seek.withjumps_forwards_ms.getValue()) * 90)
		elif self.seekAction < 0:
			self.doSeekRelativeAvoidStall(self.seekAction * int(config.seek.withjumps_backwards_ms.getValue()) * 90)
		for c in self.onPlayStateChanged:
			if self.seekAction > int(config.seek.withjumps_after_ff_speed.getValue()):  # Forward.
				c((0, self.seekAction, 0, ">> %dx" % self.seekAction))
			elif self.seekAction < 0:  # Backward.
				c((0, self.seekAction, 0, "<< %dx" % abs(self.seekAction)))
		if self.seekAction == 0:
			self.LastseekAction = False
			self.doPause(False)
			global seek_withjumps_muted
			seek_withjumps_muted = False
			self.setSeekState(self.SEEK_STATE_PLAY)

	def isServiceTypeTS(self):
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		isTS = False
		if ref is not None:
			servincetype = ServiceReference(ref).getType()
			if servincetype == 1:
				isTS = True
		return isTS

	def seekFwd(self):
		if config.seek.withjumps.value and not self.isServiceTypeTS():
			self.seekFwd_new()
		else:
			self.seekFwd_old()

	def seekBack(self):
		if config.seek.withjumps.value and not self.isServiceTypeTS():
			self.seekBack_new()
		else:
			self.seekBack_old()

	def seekFwd_new(self):
		self.LastseekAction = True
		self.doPause(True)
		global seek_withjumps_muted
		seek_withjumps_muted = True
		if self.seekAction >= 0:
			self.seekAction = self.getHigher(abs(self.seekAction), config.seek.speeds_forward.value) or config.seek.speeds_forward.value[-1]
		else:
			self.seekAction = -self.getLower(abs(self.seekAction), config.seek.speeds_backward.value)
		if (self.seekAction > 1) and (self.seekAction <= int(config.seek.withjumps_after_ff_speed.getValue())):  # Use fast forward for the configured speeds.
			self.setSeekState(self.makeStateForward(self.seekAction))
		elif self.seekAction > int(config.seek.withjumps_after_ff_speed.getValue()):  # We first need to go the play state, to stop fast forward.
			self.setSeekState(self.SEEK_STATE_PLAY)

	def seekBack_new(self):
		self.LastseekAction = True
		self.doPause(True)
		global seek_withjumps_muted
		seek_withjumps_muted = True
		if self.seekAction <= 0:
			self.seekAction = -self.getHigher(abs(self.seekAction), config.seek.speeds_backward.value) or -config.seek.speeds_backward.value[-1]
		else:
			self.seekAction = self.getLower(abs(self.seekAction), config.seek.speeds_forward.value)
		if (self.seekAction > 1) and (self.seekAction <= int(config.seek.withjumps_after_ff_speed.getValue())):  # Use fast forward for the configured forwards speeds.
			self.setSeekState(self.makeStateForward(self.seekAction))

	def seekFwd_old(self):
		seek = self.getSeek()
		if seek and not (seek.isCurrentlySeekable() & 2):
			if not self.fast_winding_hint_message_showed and (seek.isCurrentlySeekable() & 1):
				self.session.open(MessageBox, _("No fast winding possible yet.. but you can use the number buttons to skip forward/backward!"), MessageBox.TYPE_INFO, timeout=10)
				self.fast_winding_hint_message_showed = True
				return
			return 0  # Treat as unhandled action.
		if self.seekstate == self.SEEK_STATE_PLAY:
			self.setSeekState(self.makeStateForward(int(config.seek.enter_forward.value)))
		elif self.seekstate == self.SEEK_STATE_PAUSE:
			if len(config.seek.speeds_slowmotion.value):
				self.setSeekState(self.makeStateSlowMotion(config.seek.speeds_slowmotion.value[-1]))
			else:
				self.setSeekState(self.makeStateForward(int(config.seek.enter_forward.value)))
		elif self.seekstate == self.SEEK_STATE_EOF:
			pass
		elif self.isStateForward(self.seekstate):
			speed = self.seekstate[1]
			if self.seekstate[2]:
				speed /= self.seekstate[2]
			speed = self.getHigher(speed, config.seek.speeds_forward.value) or config.seek.speeds_forward.value[-1]
			self.setSeekState(self.makeStateForward(speed))
		elif self.isStateBackward(self.seekstate):
			speed = -self.seekstate[1]
			if self.seekstate[2]:
				speed /= self.seekstate[2]
			speed = self.getLower(speed, config.seek.speeds_backward.value)
			if speed:
				self.setSeekState(self.makeStateBackward(speed))
			else:
				self.setSeekState(self.SEEK_STATE_PLAY)
		elif self.isStateSlowMotion(self.seekstate):
			speed = self.getLower(self.seekstate[2], config.seek.speeds_slowmotion.value) or config.seek.speeds_slowmotion.value[0]
			self.setSeekState(self.makeStateSlowMotion(speed))

	def seekBack_old(self):
		seek = self.getSeek()
		if seek and not (seek.isCurrentlySeekable() & 2):
			if not self.fast_winding_hint_message_showed and (seek.isCurrentlySeekable() & 1):
				self.session.open(MessageBox, _("No fast winding possible yet.. but you can use the number buttons to skip forward/backward!"), MessageBox.TYPE_INFO, timeout=10)
				self.fast_winding_hint_message_showed = True
				return
			return 0  # Treat as unhandled action.
		seekstate = self.seekstate
		if seekstate == self.SEEK_STATE_PLAY:
			self.setSeekState(self.makeStateBackward(int(config.seek.enter_backward.value)))
		elif seekstate == self.SEEK_STATE_EOF:
			self.setSeekState(self.makeStateBackward(int(config.seek.enter_backward.value)))
			self.doSeekRelative(-6)
		elif seekstate == self.SEEK_STATE_PAUSE:
			self.doSeekRelative(-1)
		elif self.isStateForward(seekstate):
			speed = seekstate[1]
			if seekstate[2]:
				speed /= seekstate[2]
			speed = self.getLower(speed, config.seek.speeds_forward.value)
			if speed:
				self.setSeekState(self.makeStateForward(speed))
			else:
				self.setSeekState(self.SEEK_STATE_PLAY)
		elif self.isStateBackward(seekstate):
			speed = -seekstate[1]
			if seekstate[2]:
				speed /= seekstate[2]
			speed = self.getHigher(speed, config.seek.speeds_backward.value) or config.seek.speeds_backward.value[-1]
			self.setSeekState(self.makeStateBackward(speed))
		elif self.isStateSlowMotion(seekstate):
			speed = self.getHigher(seekstate[2], config.seek.speeds_slowmotion.value)
			if speed:
				self.setSeekState(self.makeStateSlowMotion(speed))
			else:
				self.setSeekState(self.SEEK_STATE_PAUSE)
		self.pts_lastseekspeed = self.seekstate[1]

	def seekFwdManual(self, fwd=True):
		if config.seek.baractivation.value == "leftright":
			self.session.open(Seekbar, fwd)
		else:
			self.session.openWithCallback(self.fwdSeekTo, MinuteInput)

	def seekBackManual(self, fwd=False):
		if config.seek.baractivation.value == "leftright":
			self.session.open(Seekbar, fwd)
		else:
			self.session.openWithCallback(self.rwdSeekTo, MinuteInput)

	def seekFwdVod(self, fwd=True):
		seekable = self.getSeek()
		if seekable is None:
			return
		else:
			if config.seek.baractivation.value == "leftright":
				self.session.open(Seekbar, fwd)
			else:
				self.session.openWithCallback(self.fwdSeekTo, MinuteInput)

	def seekFwdSeekbar(self, fwd=True):
		if not config.seek.baractivation.value == "leftright":
			self.session.open(Seekbar, fwd)
		else:
			self.session.openWithCallback(self.fwdSeekTo, MinuteInput)

	def fwdSeekTo(self, minutes):
		self.doSeekRelative(minutes * 60 * 90000)

	def seekBackSeekbar(self, fwd=False):
		if not config.seek.baractivation.value == "leftright":
			self.session.open(Seekbar, fwd)
		else:
			self.session.openWithCallback(self.rwdSeekTo, MinuteInput)

	def rwdSeekTo(self, minutes):
		# print("rwdSeekTo")
		self.doSeekRelative(-minutes * 60 * 90000)

	def checkSkipShowHideLock(self):
		if self.seekstate == self.SEEK_STATE_PLAY or self.seekstate == self.SEEK_STATE_EOF:
			self.lockedBecauseOfSkipping = False
			self.unlockShow()
		elif self.seekstate == self.SEEK_STATE_PAUSE and not config.usage.show_infobar_locked_on_pause.value:
			if config.usage.show_infobar_on_skip.value:
				self.lockedBecauseOfSkipping = False
				self.unlockShow()
				self.showAfterSeek()
		else:
			wantlock = self.seekstate != self.SEEK_STATE_PLAY
			if config.usage.show_infobar_on_skip.value:
				if self.lockedBecauseOfSkipping and not wantlock:
					self.unlockShow()
					self.lockedBecauseOfSkipping = False

				if wantlock and not self.lockedBecauseOfSkipping:
					self.lockShow()
					self.lockedBecauseOfSkipping = True

	def calcRemainingTime(self):
		seekable = self.getSeek()
		if seekable is not None:
			len = seekable.getLength()
			try:
				tmp = self.cueGetEndCutPosition()
				if tmp:
					len = (False, tmp)
			except Exception:
				pass
			pos = seekable.getPlayPosition()
			speednom = self.seekstate[1] or 1
			speedden = self.seekstate[2] or 1
			if not len[0] and not pos[0]:
				if len[1] <= pos[1]:
					return 0
				time = (len[1] - pos[1]) * speedden // (90 * speednom)
				return time
		return False

	def __evEOF(self):
		if self.seekstate == self.SEEK_STATE_EOF:
			return
		global seek_withjumps_muted
		if seek_withjumps_muted and eDVBVolumecontrol.getInstance().isMuted():
			print("[InfoBarGenerics] STILL MUTED AFTER FFWD/FBACK !!!!!!!! so we unMute")
			seek_withjumps_muted = False
			eDVBVolumecontrol.getInstance().volumeUnMute()
		# If we are seeking forward, we try to end up ~1s before the end, and pause there.
		seekstate = self.seekstate
		if self.seekstate != self.SEEK_STATE_PAUSE:
			self.setSeekState(self.SEEK_STATE_EOF)
		if seekstate not in (self.SEEK_STATE_PLAY, self.SEEK_STATE_PAUSE):  # If we are seeking.
			seekable = self.getSeek()
			if seekable is not None:
				seekable.seekTo(-1)
				self.doEofInternal(True)
		if seekstate == self.SEEK_STATE_PLAY:  # Regular EOF.
			self.doEofInternal(True)
		else:
			self.doEofInternal(False)

	def doEofInternal(self, playing):
		pass  # Defined in subclasses.

	def __evSOF(self):
		self.setSeekState(self.SEEK_STATE_PLAY)
		self.doSeek(0)


class InfoBarPVRState:
	def __init__(self, screen=PVRState, force_show=False):
		self.onChangedEntry = []
		self.onPlayStateChanged.append(self.__playStateChanged)
		self.pvrStateDialog = self.session.instantiateDialog(screen)
		self.pvrStateDialog.setAnimationMode(0)
		self.onShow.append(self._mayShow)
		self.onHide.append(self.pvrStateDialog.hide)
		self.force_show = force_show

	def createSummary(self):
		return InfoBarMoviePlayerSummary

	def _mayShow(self):
		if "state" in self and not config.usage.movieplayer_pvrstate.value:
			self["state"].setText("")
			self["statusicon"].setPixmapNum(6)
			self["speed"].setText("")
		if self.shown and self.seekstate != self.SEEK_STATE_EOF and not config.usage.movieplayer_pvrstate.value:
			self.DimmingTimer.stop()
			self.doWriteAlpha(config.av.osd_alpha.value)
			self.pvrStateDialog.show()
			self.startHideTimer()

	def __playStateChanged(self, state):
		playstateString = state[3]
		state_summary = playstateString
		if "statusicon" in self.pvrStateDialog:
			self.pvrStateDialog["state"].setText(playstateString)
			if playstateString == ">":
				self.pvrStateDialog["statusicon"].setPixmapNum(0)
				self.pvrStateDialog["speed"].setText("")
				speed_summary = self.pvrStateDialog["speed"].text
				statusicon_summary = 0
				if "state" in self and config.usage.movieplayer_pvrstate.value:
					self["state"].setText(playstateString)
					self["statusicon"].setPixmapNum(0)
					self["speed"].setText("")
			elif playstateString == "||":
				self.pvrStateDialog["statusicon"].setPixmapNum(1)
				self.pvrStateDialog["speed"].setText("")
				speed_summary = self.pvrStateDialog["speed"].text
				statusicon_summary = 1
				if "state" in self and config.usage.movieplayer_pvrstate.value:
					self["state"].setText(playstateString)
					self["statusicon"].setPixmapNum(1)
					self["speed"].setText("")
			elif playstateString == "END":
				self.pvrStateDialog["statusicon"].setPixmapNum(2)
				self.pvrStateDialog["speed"].setText("")
				speed_summary = self.pvrStateDialog["speed"].text
				statusicon_summary = 2
				if "state" in self and config.usage.movieplayer_pvrstate.value:
					self["state"].setText(playstateString)
					self["statusicon"].setPixmapNum(2)
					self["speed"].setText("")
			elif playstateString.startswith(">>"):
				speed = state[3].split()
				self.pvrStateDialog["statusicon"].setPixmapNum(3)
				self.pvrStateDialog["speed"].setText(speed[1])
				speed_summary = self.pvrStateDialog["speed"].text
				statusicon_summary = 3
				if "state" in self and config.usage.movieplayer_pvrstate.value:
					self["state"].setText(playstateString)
					self["statusicon"].setPixmapNum(3)
					self["speed"].setText(speed[1])
			elif playstateString.startswith("<<"):
				speed = state[3].split()
				self.pvrStateDialog["statusicon"].setPixmapNum(4)
				self.pvrStateDialog["speed"].setText(speed[1])
				speed_summary = self.pvrStateDialog["speed"].text
				statusicon_summary = 4
				if "state" in self and config.usage.movieplayer_pvrstate.value:
					self["state"].setText(playstateString)
					self["statusicon"].setPixmapNum(4)
					self["speed"].setText(speed[1])
			elif playstateString.startswith("/"):
				self.pvrStateDialog["statusicon"].setPixmapNum(5)
				self.pvrStateDialog["speed"].setText(playstateString)
				speed_summary = self.pvrStateDialog["speed"].text
				statusicon_summary = 5
				if "state" in self and config.usage.movieplayer_pvrstate.value:
					self["state"].setText(playstateString)
					self["statusicon"].setPixmapNum(5)
					self["speed"].setText(playstateString)
			for cb in self.onChangedEntry:
				cb(state_summary, speed_summary, statusicon_summary)
		# If we return into "PLAY" state, ensure that the dialog gets hidden if there will be no InfoBar displayed.
		if not config.usage.show_infobar_on_skip.value and self.seekstate == self.SEEK_STATE_PLAY and not self.force_show:
			self.pvrStateDialog.hide()
		else:
			self._mayShow()


class InfoBarTimeshiftState(InfoBarPVRState):
	def __init__(self):
		InfoBarPVRState.__init__(self, screen=TimeshiftState, force_show=True)
		self.onPlayStateChanged.append(self.__timeshiftEventName)
		self.onHide.append(self.__hideTimeshiftState)

	def _mayShow(self):
		if self.shown and self.timeshiftEnabled() and self.isSeekable():
			InfoBarTimeshift.ptsSeekPointerSetCurrentPos(self)
			if config.timeshift.showInfoBar.value:
				self["TimeshiftSeekPointerActions"].setEnabled(True)
			self.pvrStateDialog.show()
		if not self.isSeekable():
			self.startHideTimer()

	def __hideTimeshiftState(self):
		self["TimeshiftSeekPointerActions"].setEnabled(False)
		self.pvrStateDialog.hide()

	def __timeshiftEventName(self, state):
		if self.timeshiftEnabled() and exists("%spts_livebuffer_%s.meta" % (config.timeshift.path.value, self.pts_currplaying)):
			readmetafile = open("%spts_livebuffer_%s.meta" % (config.timeshift.path.value, self.pts_currplaying))
			servicerefname = readmetafile.readline()[0:-1]
			eventname = readmetafile.readline()[0:-1]
			readmetafile.close()
			self.pvrStateDialog["eventname"].setText(eventname)
		else:
			self.pvrStateDialog["eventname"].setText("")


class InfoBarShowMovies:
	# I don't really like this class.
	# It calls a not further specified "movie list" on up/down/movieList,
	# so this is not more than an action map.
	def __init__(self):
		self["MovieListActions"] = HelpableActionMap(self, "InfobarMovieListActions", {
			"movieList": (self.showMovies, _("Open Movie Selection")),
			"up": (self.up, _("Open Movie Selection")),
			"down": (self.down, _("Open Movie Selection"))
		}, prio=0, description=_("Movie Selection Actions"))


class ExtensionsList(ChoiceBox):
	def __init__(self, session, extensions):
		colorKeys = {
			"red": 1,
			"green": 2,
			"yellow": 3,
			"blue": 4
		}
		extensionListAll = []
		for extension in extensions:
			if extension[0] == 0:  # EXTENSION_SINGLE
				if extension[1][2]():
					extensionListAll.append((extension[1][0](), extension[1], extension[2], colorKeys.get(extension[2], 0)))
			else:
				for subExtension in extension[1]():
					if subExtension[0][2]():
						extensionListAll.append((subExtension[0][0](), subExtension[0], subExtension[1], colorKeys.get(subExtension[1], 0)))

		if config.usage.sortExtensionslist.value == "alpha":
			extensionListAll.sort(key=lambda x: (x[3], x[0]))
		else:
			extensionListAll.sort(key=lambda x: x[3])

		allkeys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
		extensionList = []
		extensionKeys = []

		for extension in extensionListAll:
			key = extension[2]
			if not key and allkeys:
				key = allkeys.pop(0)
			extensionKeys.append(key or "")
			extensionList.append((extension[0], extension[1]))

		reorderConfig = "extensionOrder" if config.usage.sortExtensionslist.value == "user" else ""
		ChoiceBox.__init__(self, session, title=_("Please choose an extension..."), list=extensionList, keys=extensionKeys, reorderConfig=reorderConfig, skin_name="ExtensionsList")


class InfoBarExtensions:
	EXTENSION_SINGLE = 0
	EXTENSION_LIST = 1

	def __init__(self):
		self.list = []
		if config.plisettings.ColouredButtons.value:
			self["InstantExtensionsActions"] = HelpableActionMap(self, "InfobarExtensions", {
				"extensions": (self.bluekey_ex, _("Open Extensions")),
				"quickmenu": (self.bluekey_qm, _("Open QuickMenu")),
				"showPluginBrowser": (self.showPluginBrowser, _("Open Plugin Browser")),
				"showEventInfo": (self.SelectopenEventView, _("Open event information")),
				"openTimerList": (self.showTimerList, _("Open RecordTimer Overview")),
				"openAutoTimerList": (self.showAutoTimerList, _("Open AutoTimer OverView")),
				"openEPGSearch": (self.showEPGSearch, _("Search EPG for current event")),
				"openIMDB": (self.showIMDB, _("Search IMDb for information about current event")),
				"showMediaPlayer": (self.showMediaPlayer, _("Open Media Player")),
				"openDreamPlex": (self.showDreamPlex, _("Open DreamPlex"))
			}, prio=1, description=_("Extension Actions"))  # Lower priority.
		else:
			self["InstantExtensionsActions"] = HelpableActionMap(self, "InfobarExtensions", {
				"extensions": (self.bluekey_ex, _("Open Extensions")),
				"quickmenu": (self.bluekey_qm, _("Open QuickMenu")),
				"showPluginBrowser": (self.showPluginBrowser, _("Open Plugin Browser")),
				"showEventInfo": (self.SelectopenEventView, _("Open event information")),
				"showMediaPlayer": (self.showMediaPlayer, _("Open Media Player")),
				"showDreamPlex": (self.showDreamPlex, _("Open DreamPlex"))
			}, prio=1, description=_("Extension Actions"))  # Lower priority.
		self.addExtension((lambda: _("Manually import from fallback tuner"), self.importChannels, lambda: config.usage.remote_fallback_extension_menu.value and config.usage.remote_fallback_import.value))
		self.addExtension(extension=self.getLogManager, type=InfoBarExtensions.EXTENSION_LIST)
		self.addExtension(extension=self.getOsd3DSetup, type=InfoBarExtensions.EXTENSION_LIST)
		self.addExtension(extension=self.getCCcamInfo, type=InfoBarExtensions.EXTENSION_LIST)
		self.addExtension(extension=self.getOScamInfo, type=InfoBarExtensions.EXTENSION_LIST)
		self.addExtension(extension=self.getSoftcamSetup, type=InfoBarExtensions.EXTENSION_LIST)
		if config.usage.show_restart_network_extensionslist.getValue() is True:
			self.addExtension(extension=self.getRestartNetwork, type=InfoBarExtensions.EXTENSION_LIST)
		for p in plugins.getPlugins(PluginDescriptor.WHERE_EXTENSIONSINGLE):
			p(self)

	def bluekey_qm(self):
		if config.workaround.blueswitch.value:
			self.showExtensionSelection()
		else:
			self.quickmenuStart()

	def bluekey_ex(self):
		if config.workaround.blueswitch.value:
			self.quickmenuStart()
		else:
			self.showExtensionSelection()

	def quickmenuStart(self):
		try:
			if self.session.pipshown:
				self.showExtensionSelection()
				return
		except Exception:
			print("[INFOBARGENERICS] QuickMenu: error pipshow, starting Quick Menu")
		from Screens.QuickMenu import QuickMenu
		self.session.open(QuickMenu)

	def importChannels(self):
		from Components.ImportChannels import ImportChannels
		ImportChannels()

	def SelectopenEventView(self):
		try:
			self.openEventView()
		except Exception:
			pass

	def getLMname(self):
		return _("Log Manager")

	def getLogManager(self):
		if config.logmanager.showinextensions.value:
			return [((boundFunction(self.getLMname), boundFunction(self.openLogManager), lambda: True), None)]
		else:
			return []

	def getSoftcamSetupname(self):
		return _("Softcam Settings")

	def getSoftcamSetup(self):
		return [((boundFunction(self.getSoftcamSetupname), boundFunction(self.openSoftcamSetup), lambda: True), None)] if BoxInfo.getItem("SoftCam") else []

	def getRestartNetworkname(self):
		return _("Restart Network")

	def getRestartNetwork(self):
		return [((boundFunction(self.getRestartNetworkname), boundFunction(self.openRestartNetwork), lambda: True), None)]

	def get3DSetupname(self):
		return _("OSD 3D Settings")

	def getOsd3DSetup(self):
		if config.osd.show3dextensions.value:
			return [((boundFunction(self.get3DSetupname), boundFunction(self.open3DSetup), lambda: True), None)]
		else:
			return []

	def getCCname(self):
		return _("CCcam Info")

	def getCCcamInfo(self):
		if pathExists("/usr/bin/"):
			softcams = listdir("/usr/bin/")
		for softcam in softcams:
			if softcam.lower().startswith("cccam") and config.softcam.showInExtensions.value:
				return [((boundFunction(self.getCCname), boundFunction(self.openCCcamInfo), lambda: True), None)] or []
		else:
			return []

	def getOSname(self):
		return _("OSCam Info")

	def getOScamInfo(self):
		if pathExists("/usr/bin/"):
			softcams = listdir("/usr/bin/")
		for softcam in softcams:
			if softcam.lower().startswith("oscam") and config.softcam.showInExtensions.value:
				return [((boundFunction(self.getOSname), boundFunction(self.openOScamInfo), lambda: True), None)] or []
		else:
			return []

	def addExtension(self, extension, key=None, type=EXTENSION_SINGLE):
		self.list.append((type, extension, key))

	def showExtensionSelection(self):
		self.session.openWithCallback(self.extensionCallback, ExtensionsList, self.list)

	def extensionCallback(self, answer):
		if answer is not None:
			answer[1][1]()

	def showPluginBrowser(self):
		from Screens.PluginBrowser import PluginBrowser
		self.session.open(PluginBrowser)

	def openCCcamInfo(self):
		from Screens.CCcamInfo import CCcamInfoMain
		self.session.open(CCcamInfoMain)

	def openOScamInfo(self):
		from Screens.OScamInfo import OSCamInfo
		self.session.open(OSCamInfo)

	def showTimerList(self):
		self.session.open(RecordTimerOverview)

	def openLogManager(self):
		from Screens.LogManager import LogManager
		self.session.open(LogManager)

	def open3DSetup(self):
		from Screens.Setup import Setup
		self.session.open(Setup, "OSD3D")

	def openSoftcamSetup(self):
		from Screens.SoftcamSetup import SoftcamSetup
		self.session.open(SoftcamSetup)

	def openRestartNetwork(self):
		try:
			from Screens.RestartNetwork import RestartNetwork
			self.session.open(RestartNetwork)
		except Exception:
			print("[INFOBARGENERICS] failed to restart network")

	def showAutoTimerList(self):
		if isPluginInstalled("AutoTimer"):
			from Plugins.Extensions.AutoTimer.plugin import main, autostart
			from Plugins.Extensions.AutoTimer.AutoTimer import AutoTimer
			from Plugins.Extensions.AutoTimer.AutoPoller import AutoPoller
			self.autopoller = AutoPoller()
			self.autotimer = AutoTimer()
			try:
				self.autotimer.readXml()
			except SyntaxError as se:
				self.session.open(
					MessageBox,
					_("Your config file is not well-formed:\n%s") % (str(se)),
					type=MessageBox.TYPE_ERROR,
					timeout=10
				)
				return
			# Do not run in background while editing, this might screw things up.
			if self.autopoller is not None:
				self.autopoller.stop()
			from Plugins.Extensions.AutoTimer.AutoTimerOverview import AutoTimerOverview
			self.session.openWithCallback(
				self.editCallback,
				AutoTimerOverview,
				self.autotimer
			)
		else:
			self.session.open(MessageBox, _("The AutoTimer plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def editCallback(self, session):
		# XXX: Canceling of GUI (Overview) won't affect config values which might have been changed - is this intended?
		# Don't parse EPG if editing was canceled.
		if session is not None:
			self.autotimer.writeXml()  # Save XML.
			self.autotimer.parseEPG()  # Poll EPGCache.
		if config.plugins.autotimer.autopoll.value:  # Start autopoller again if wanted.
			if self.autopoller is None:
				from Plugins.Extensions.AutoTimer.AutoPoller import AutoPoller
				self.autopoller = AutoPoller()
			self.autopoller.start()
		else:  # Remove instance if not running in background.
			self.autopoller = None
			self.autotimer = None

	def showEPGSearch(self):
		from Plugins.Extensions.EPGSearch.EPGSearch import EPGSearch
		s = self.session.nav.getCurrentService()
		if s:
			info = s.info()
			event = info.getEvent(0)  # 0 = Now, 1 = Next.
			if event:
				name = event.getEventName() or ""
			else:
				name = self.session.nav.getCurrentlyPlayingServiceOrGroup().toString()
				name = name.split("/")
				name = name[-1]
				name = name.replace(".", " ")
				name = name.split("-")
				name = name[0]
				if name.endswith(" "):
					name = name[:-1]
			if name:
				self.session.open(EPGSearch, name, False)
			else:
				self.session.open(EPGSearch)
		else:
			self.session.open(EPGSearch)

	def showIMDB(self):
		if isPluginInstalled("IMDb"):
			from Plugins.Extensions.IMDb.plugin import IMDB
			s = self.session.nav.getCurrentService()
			if s:
				info = s.info()
				event = info.getEvent(0)  # 0 = Now, 1 = Next.
				name = event and event.getEventName() or ""
				self.session.open(IMDB, name)
		else:
			self.session.open(MessageBox, _("The IMDb plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def showMediaPlayer(self):
		if isinstance(self, InfoBarExtensions):
			if isinstance(self, InfoBar):
				try:  # If it is not installed.
					from Plugins.Extensions.MediaPlayer.plugin import MediaPlayer
					self.session.open(MediaPlayer)
					no_plugin = False
				except Exception as e:
					self.session.open(MessageBox, _("The MediaPlayer plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def showDreamPlex(self):
		if isPluginInstalled("DreamPlex"):
			from Plugins.Extensions.DreamPlex.plugin import DPS_MainMenu
			self.session.open(DPS_MainMenu)
		else:
			self.session.open(MessageBox, _("The DreamPlex plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)


# Depends on InfoBarExtensions
#
class InfoBarPlugins:
	def __init__(self):
		self.addExtension(extension=self.getPluginList, type=InfoBarExtensions.EXTENSION_LIST)

	def getPluginName(self, name):
		return name

	def getPluginList(self):
		l = []
		for p in plugins.getPlugins(where=PluginDescriptor.WHERE_EXTENSIONSMENU):
			args = getfullargspec(p.__call__)[0]  # FIME: This is a performance issue and should be replaced.
			if len(args) == 1 or len(args) == 2 and isinstance(self, InfoBarChannelSelection):
				l.append(((boundFunction(self.getPluginName, p.name), boundFunction(self.runPlugin, p), lambda: True), None, p.name))
		l.sort(key=lambda e: e[2])  # Sort by name.
		return l

	def runPlugin(self, plugin):
		if isinstance(self, InfoBarChannelSelection):
			plugin(session=self.session, servicelist=self.servicelist)
		else:
			try:
				plugin(session=self.session)
			except Exception as err:
				print("[InfoBarGenerics] Error: ", err)


class InfoBarJobman:
	def __init__(self):
		self.addExtension(extension=self.getJobList, type=InfoBarExtensions.EXTENSION_LIST)

	def getJobList(self):
		return [((boundFunction(self.getJobName, job), boundFunction(self.showJobView, job), lambda: True), None) for job in job_manager.getPendingJobs()] if config.usage.jobtaksextensions.value else []

	def getJobName(self, job):
		return "%s: %s (%d%%)" % (job.getStatustext(), job.name, int(100 * job.progress / float(job.end)))

	def showJobView(self, job):
		from Screens.TaskView import JobView
		job_manager.in_background = False
		self.session.openWithCallback(self.JobViewCB, JobView, job)

	def JobViewCB(self, in_background):
		job_manager.in_background = in_background


# Depends on InfoBarExtensions
#
class InfoBarPiP:
	def __init__(self):
		def pipHelp():
			if self.servicelist and self.servicelist.dopipzap:
				helpText = _("Disable Picture in Picture")
			if self.session.pipshown:
				helpText = _("Zap focus to Picture in Picture")
			else:
				helpText = _("Activate Picture in Picture")
			return helpText

		try:
			self.session.pipshown
		except Exception:
			self.session.pipshown = False
		self.lastPiPService = None
		if BoxInfo.getItem("PIPAvailable") and isinstance(self, InfoBarEPG):
			self["PiPActions"] = HelpableActionMap(self, "InfobarPiPActions", {
				"activatePiP": (self.activePiP, pipHelp),
			}, prio=0, description=_("Picture in Picture Actions"))
			if self.allowPiP:
				self.addExtension((self.getShowHideName, self.showPiP, lambda: True), "blue")
				self.addExtension((self.getMoveName, self.movePiP, self.pipShown), "green")
				self.addExtension((self.getSwapName, self.swapPiP, lambda: self.pipShown() and isStandardInfoBar(self)), "yellow")
				self.addExtension((self.getTogglePipzapName, self.togglePipzap, self.pipShown), "red")
			else:
				self.addExtension((self.getShowHideName, self.showPiP, self.pipShown), "blue")
				self.addExtension((self.getMoveName, self.movePiP, self.pipShown), "green")
		self.lastPiPServiceTimeoutTimer = eTimer()
		self.lastPiPServiceTimeoutTimer.callback.append(self.clearLastPiPService)

	def pipShown(self):
		return self.session.pipshown

	def pipHandles0Action(self):
		return self.pipShown() and config.usage.pip_zero_button.value != "standard"

	def getShowHideName(self):
		return _("Disable Picture in Picture") if self.session.pipshown else _("Activate Picture in Picture")

	def getSwapName(self):
		return _("Swap services")

	def getMoveName(self):
		return _("Picture in Picture Settings")

	def getTogglePipzapName(self):
		serviceList = self.servicelist
		return _("Zap focus to main screen") if serviceList and serviceList.dopipzap else _("Zap focus to Picture in Picture")

	def togglePipzap(self):
		if not self.session.pipshown:
			self.showPiP()
		slist = self.servicelist
		if slist and self.session.pipshown:
			slist.togglePipzap()
			if slist.dopipzap:
				currentServicePath = slist.getCurrentServicePath()
				self.servicelist.setCurrentServicePath(self.session.pip.servicePath, doZap=False)
				self.session.pip.servicePath = currentServicePath

	def showPiP(self):
		self.lastPiPServiceTimeoutTimer.stop()
		slist = self.servicelist
		if self.session.pipshown:
			if slist and slist.dopipzap:
				self.togglePipzap()
			if self.session.pipshown:
				lastPiPServiceTimeout = int(config.usage.pip_last_service_timeout.value)
				if lastPiPServiceTimeout >= 0:
					self.lastPiPService = self.session.pip.getCurrentServiceReference()
					if lastPiPServiceTimeout:
						self.lastPiPServiceTimeoutTimer.startLongTimer(lastPiPServiceTimeout)
				del self.session.pip
				if BoxInfo.getItem("LCDMiniTV") and config.lcd.modepip.value >= 1:
					print("[InfoBarGenerics] [LCDMiniTV] disable PiP")
					eDBoxLCD.getInstance().setLCDMode(config.lcd.modeminitv.value)
				self.session.pipshown = False
			if hasattr(self, "screenSaverTimerStart"):
				self.screenSaverTimerStart()
		else:
			service = self.session.nav.getCurrentService()
			info = service and service.info()
			if info:
				xres = str(info.getInfo(iServiceInformation.sVideoWidth))
			if info and int(xres) <= 720 or BoxInfo.getItem("model") != "blackbox7405":
				self.session.pip = self.session.instantiateDialog(PictureInPicture)
				self.session.pip.setAnimationMode(0)
				self.session.pip.show()
				if isStandardInfoBar(self):
					newservice = self.lastPiPService or self.session.nav.getCurrentlyPlayingServiceReference() or self.servicelist.getCurrentSelection()
				else:
					newservice = self.lastPiPService or self.servicelist.getCurrentSelection()
				if self.session.pip.playService(newservice):
					self.session.pipshown = True
					self.session.pip.servicePath = self.servicelist.getCurrentServicePath()
					if BoxInfo.getItem("LCDMiniTVPiP") and config.lcd.modepip.value >= 1:
						print("[InfoBarGenerics] [LCDMiniTV] enable PiP")
						eDBoxLCD.getInstance().setLCDMode(config.lcd.modepip.value, True)
				else:
					newservice = self.session.nav.getCurrentlyPlayingServiceReference() or self.servicelist.servicelist.getCurrent()
					if self.session.pip.playService(newservice):
						self.session.pipshown = True
						self.session.pip.servicePath = self.servicelist.getCurrentServicePath()
						if BoxInfo.getItem("LCDMiniTVPiP") and config.lcd.modepip.value >= 1:
							print("[InfoBarGenerics] [LCDMiniTV] enable PiP")
							eDBoxLCD.getInstance().setLCDMode(config.lcd.modepip.value, True)
					else:
						self.lastPiPService = None
						self.session.pipshown = False
						del self.session.pip
			elif info:
				self.session.open(MessageBox, _("Your %s %s does not support PiP HD") % getBoxDisplayName(), type=MessageBox.TYPE_INFO, timeout=5)
			else:
				self.session.open(MessageBox, _("No active channel found."), type=MessageBox.TYPE_INFO, timeout=5)
		if self.session.pipshown and hasattr(self, "screenSaverTimer"):
			self.screenSaverTimer.stop()

	def clearLastPiPService(self):
		self.lastPiPService = None

	def activePiP(self):
		if self.servicelist and self.servicelist.dopipzap or not self.session.pipshown:
			self.showPiP()
		else:
			self.togglePipzap()

	def swapPiP(self):
		if self.pipShown():
			swapservice = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			pipref = self.session.pip.getCurrentService()
			if swapservice and pipref and pipref.toString() != swapservice.toString():
				currentServicePath = self.servicelist.getCurrentServicePath()
				currentBouquet = self.servicelist and self.servicelist.getRoot()
				self.servicelist.setCurrentServicePath(self.session.pip.servicePath, doZap=False)
				self.session.pip.playService(swapservice)
				self.session.nav.stopService()  # Stop portal.
				self.session.nav.playService(pipref, checkParentalControl=False, adjust=False)
				self.session.pip.servicePath = currentServicePath
				self.session.pip.servicePath[1] = currentBouquet
				if self.servicelist.dopipzap:
					# This unfortunately won't work with subservices.
					self.servicelist.setCurrentSelection(self.session.pip.getCurrentService())

	def movePiP(self):
		if self.pipShown():
			self.session.open(PiPSetup, pip=self.session.pip)

	def pipDoHandle0Action(self):
		match config.usage.pip_zero_button.value:
			case "swap":
				self.swapPiP()
			case "swapstop":
				self.swapPiP()
				self.showPiP()
			case "stop":
				self.showPiP()


class InfoBarQuickMenu:
	def __init__(self):
		def quickMenuHelp():
			return _("Open Extensions") if config.workaround.blueswitch.value else _("Open QuickMenu")

		self["QuickMenuActions"] = HelpableActionMap(self, "InfoBarQuickMenu", {
			"quickmenu": (self.quickMenu, quickMenuHelp()),
		}, prio=0, description=_("QuickMenu Actions"))

	def quickMenu(self):
		def quickMenuStart():
			try:
				if self.session.pipshown:
					self.showExtensionSelection()
					return
			except Exception:
				print("[InfoBarGenerics] QuickMenu: Error pipshow, starting Quick Menu!")
			from Screens.QuickMenu import QuickMenu  # This is here to avoid a cyclic import.
			self.session.open(QuickMenu)

		if config.workaround.blueswitch.value:
			self.showExtensionSelection()
		else:
			quickmenuStart()


class InfoBarInstantRecord:
	"""Instant Record - Handles the instantRecord action in order to start/stop instant recordings."""

	def __init__(self):
		self["InstantRecordActions"] = HelpableActionMap(self, "InfobarInstantRecord", {
			"instantRecord": (self.instantRecord, _("Start an instant recording")),
		}, prio=0, description=_("Instant Recording Actions"))
		self.SelectedInstantServiceRef = None
		if isStandardInfoBar(self):
			self.recording = []
		else:
			from Screens.InfoBar import InfoBar
			InfoBarInstance = InfoBar.instance
			if InfoBarInstance:
				self.recording = InfoBarInstance.recording
		self.saveTimeshiftEventPopupActive = False

	def stopCurrentRecording(self, entry=-1):
		if entry is not None and entry != -1:
			self.session.nav.RecordTimer.removeEntry(self.recording[entry])
			self.recording.remove(self.recording[entry])

	def getProgramInfoAndEvent(self, info, name):
		info["serviceref"] = hasattr(self, "SelectedInstantServiceRef") and self.SelectedInstantServiceRef or self.session.nav.getCurrentlyPlayingServiceOrGroup()
		# Try to get event information.
		event = None
		try:
			epg = eEPGCache.getInstance()
			event = epg.lookupEventTime(info["serviceref"], -1, 0)
			if event is None:
				if hasattr(self, "SelectedInstantServiceRef") and self.SelectedInstantServiceRef:
					service_info = eServiceCenter.getInstance().info(self.SelectedInstantServiceRef)
					event = service_info and service_info.getEvent(self.SelectedInstantServiceRef)
				else:
					service = self.session.nav.getCurrentService()
					event = service and service.info().getEvent(0)
		except Exception:
			pass
		info["event"] = event
		info["name"] = name
		info["description"] = ""
		info["eventid"] = None
		if event is not None:
			curEvent = parseEvent(event)
			info["name"] = curEvent[2]
			info["description"] = curEvent[3]
			info["eventid"] = curEvent[4]
			info["end"] = curEvent[1]

	def startInstantRecording(self, limitEvent=False):
		begin = int(time())
		end = begin + 3600  # Dummy.
		name = "instant record"
		info = {}
		self.getProgramInfoAndEvent(info, name)
		serviceref = info["serviceref"]
		event = info["event"]
		if event is not None:
			if limitEvent:
				end = info["end"]
		else:
			if limitEvent:
				self.session.open(MessageBox, _("No event information found, recording default is 24 hours."), MessageBox.TYPE_INFO)
		if isinstance(serviceref, eServiceReference):
			serviceref = ServiceReference(serviceref)
		if not limitEvent:
			end = begin + (60 * 60 * 24)  # 24 hours.
		recording = RecordTimerEntry(serviceref, begin, end, info["name"], info["description"], info["eventid"], afterEvent=AFTEREVENT.AUTO, justplay=False, always_zap=False, dirname=preferredInstantRecordPath())
		recording.marginBefore = 0
		recording.dontSave = True
		recording.eventBegin = recording.begin
		if not limitEvent:
			recording.marginAfter = 0
			recording.eventEnd = recording.end
		if event is None or limitEvent is False:
			recording.autoincrease = True
			recording.setAutoincreaseEnd()
		simulTimerList = self.session.nav.RecordTimer.record(recording)
		if simulTimerList is None:  # No conflict.
			recording.autoincrease = False
			self.recording.append(recording)
		else:
			if len(simulTimerList) > 1:  # With other recording.
				name = simulTimerList[1].name
				name_date = " ".join((name, strftime("%F %T", localtime(simulTimerList[1].begin))))
				# print(f"[InfoBarGenerics] InstantTimer conflicts with {name_date}!")
				recording.autoincrease = True  # Start with max available length, then increment.
				if recording.setAutoincreaseEnd():
					self.session.nav.RecordTimer.record(recording)
					self.recording.append(recording)
					self.session.open(MessageBox, _("Record time limited due to conflicting timer:%s") % f"\n\t'{name_date}'", MessageBox.TYPE_INFO)
				else:
					self.session.open(MessageBox, _("Could not record due to conflicting timer:%s") % f"\n\t'{name}'", MessageBox.TYPE_INFO)
			else:
				self.session.open(MessageBox, _("Could not record due to invalid service:%s") % f"\n\t'{serviceref}'", MessageBox.TYPE_INFO)
			recording.autoincrease = False

	def startRecordingCurrentEvent(self):
		self.startInstantRecording(True)

	def isInstantRecordRunning(self):
		# print("[InfoBarGenerics] self.recording: {self.recording}")
		if self.recording:
			for x in self.recording:
				if x.isRunning():
					return True
		return False

	def recordQuestionCallback(self, answer):
		# print("[InfoBarGenerics] recordQuestionCallback")
		# print("[InfoBarGenerics] pre: {self.recording}")
		if answer is None or answer[1] == "no":
			self.saveTimeshiftEventPopupActive = False
			return
		items = []
		recording = self.recording[:]
		for x in recording:
			if x not in self.session.nav.RecordTimer.timer_list:
				self.recording.remove(x)
			elif x.dontSave and x.isRunning():
				items.append((x, False))
		if answer[1] == "changeduration":
			if len(self.recording) == 1:
				self.changeDuration(0)
			else:
				self.session.openWithCallback(self.changeDuration, TimerSelection, items)
		elif answer[1] == "changeendtime":
			if len(self.recording) == 1:
				self.changeEndtime(0)
			else:
				self.session.openWithCallback(self.changeEndtime, TimerSelection, items)
		elif answer[1] == "timer":
			self.session.open(RecordTimerOverview)
		elif answer[1] == "stop":
			self.session.openWithCallback(self.stopCurrentRecording, TimerSelection, items)
		elif answer[1] in ("indefinitely", "manualduration", "manualendtime", "event"):
			if len(items) >= 2 and BoxInfo.getItem("ChipsetString") in ("meson-6", "meson-64"):
				Notifications.AddNotification(MessageBox, _("Sorry it is only possible to record 2 channels at once!"), MessageBox.TYPE_ERROR, timeout=5)
				return
			self.startInstantRecording(limitEvent=answer[1] in ("event", "manualendtime") or False)
			if answer[1] == "manualduration":
				self.changeDuration(len(self.recording) - 1)
			elif answer[1] == "manualendtime":
				self.changeEndtime(len(self.recording) - 1)
		elif answer[1] == "savetimeshift":
			if self.isSeekable() and self.pts_eventcount != self.pts_currplaying:
				InfoBarTimeshift.SaveTimeshift(self, timeshiftfile="pts_livebuffer_%s" % self.pts_currplaying)
			else:
				Notifications.AddNotification(MessageBox, _("Time shift will get saved at end of event."), MessageBox.TYPE_INFO, timeout=5)
				self.save_current_timeshift = True
				config.timeshift.isRecording.value = True
		elif answer[1] == "savetimeshiftEvent":
			InfoBarTimeshift.saveTimeshiftEventPopup(self)
		elif answer[1].startswith("pts_livebuffer") is True:
			InfoBarTimeshift.SaveTimeshift(self, timeshiftfile=answer[1])
		if answer[1] != "savetimeshiftEvent":
			self.saveTimeshiftEventPopupActive = False

	def changeEndtime(self, entry):
		def changeEndtimeCallback(result):
			if len(result) > 1 and result[0]:
				print(f"[InfoBarGenerics] Instant recording due to stop at {strftime('%F %T', localtime(result[1]))}.")
				if recordingEntry.end != result[1]:
					recordingEntry.autoincrease = False
				recordingEntry.end = result[1]
				recordingEntry.eventEnd = recordingEntry.end
				recordingEntry.marginAfter = 0  # Why is this being done?
				self.session.nav.RecordTimer.timeChanged(recordingEntry)

		if entry is not None and entry >= 0:
			recordingEntry = self.recording[entry]
			self.session.openWithCallback(changeEndtimeCallback, InstantRecordingEndTime, recordingEntry.eventEnd)

	def changeDuration(self, entry):
		def changeDurationCallback(value):
			entry = self.recording[self.selectedEntry]
			if value is not None:
				value = int(value.replace(" ", "") or "0")
				if value:
					entry.autoincrease = False
				print(f"[InfoBarGenerics] Instant recording due to stop after {value} minutes.")
				entry.end = int(time()) + 60 * value
				entry.eventEnd = entry.end
				entry.marginAfter = 0
				self.session.nav.RecordTimer.timeChanged(entry)

		if entry is not None and entry >= 0:
			self.selectedEntry = entry
			self.session.openWithCallback(changeDurationCallback, InputBox, title=_("For how many minutes do you want to record?"), text="5  ", maxSize=True, type=Input.NUMBER)

	def isTimerRecordRunning(self):
		identical = timers = 0
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.isRunning() and not timer.justplay:
				timers += 1
				if self.recording:
					for x in self.recording:
						if x.isRunning() and x == timer:
							identical += 1
		return timers > identical

	def instantRecord(self, serviceRef=None):
		self.SelectedInstantServiceRef = serviceRef
		pirr = preferredInstantRecordPath()
		if not findSafeRecordPath(pirr) and not findSafeRecordPath(defaultMoviePath()):
			if not pirr:
				pirr = ""
			self.session.open(MessageBox, "%s\n\n%s" % (_("Path '%s' missing!") % pirr, _("No HDD found or HDD not initialized!")), MessageBox.TYPE_ERROR)
			return
		if isStandardInfoBar(self):
			commonRecord = [
				(_("Add recording (Stop after current event)"), "event"),
				(_("Add recording (Indefinitely - 24 hours)"), "indefinitely"),
				(_("Add recording (Enter recording duration)"), "manualduration"),
				(_("Add recording (Enter recording end time)"), "manualendtime")
			]
			commonTimeshift = [
				(_("Time shift save recording (Stop after current event)"), "savetimeshift"),
				(_("Time shift save recording (Select event)"), "savetimeshiftEvent")
			]
		else:
			commonRecord = []
			commonTimeshift = []
		if self.isInstantRecordRunning():
			title = _("A recording is currently running.\nWhat do you want to do?")
			choiceList = [
				(_("Stop recording"), "stop")
			] + commonRecord + [
				(_("Change recording (Duration)"), "changeduration"),
				(_("Change recording (End time)"), "changeendtime")
			]
			if self.isTimerRecordRunning():
				choiceList.append((_("Stop timer recording"), "timer"))
		else:
			title = _("Start instant recording?")
			choiceList = commonRecord
			if self.isTimerRecordRunning():
				choiceList.append((_("Stop timer recording"), "timer"))
		if isStandardInfoBar(self) and self.timeshiftEnabled():
			choiceList.extend(commonTimeshift)
		if isStandardInfoBar(self):
			choiceList.append((_("Do not record"), "no"))
		if choiceList:
			self.session.openWithCallback(self.recordQuestionCallback, ChoiceBox, title=title, list=choiceList)


class InfoBarAudioSelection:
	def __init__(self):
		self["AudioSelectionAction"] = HelpableActionMap(self, "InfobarAudioSelectionActions", {
			"audioSelection": (self.audioSelection, _("Open Audio options")),
			"yellow_key": (self.yellow_key, _("Open Audio options")),
			"audioSelectionLong": (self.audioDownmixToggle, _("Toggle Dolby Digital down mix")),
		}, prio=0, description=_("Audio Actions"))

	def yellow_key(self):
		from Screens.AudioSelection import AudioSelection
		self.session.openWithCallback(self.audioSelected, AudioSelection, infobar=self)
		# if not hasattr(self, "LongButtonPressed"):
		# 	self.LongButtonPressed = False
		# global AUDIO
		# if not self.LongButtonPressed:
		# 	if config.plugins.infopanel_yellowkey.list.value == "0":
		# 		from Screens.AudioSelection import AudioSelection
		# 		self.session.openWithCallback(self.audioSelected, AudioSelection, infobar=self)
		# 	elif config.plugins.infopanel_yellowkey.list.value == "2":
		# 		AUDIO = True
		# 		ToggleVideo()
		# 	elif config.plugins.infopanel_yellowkey.list.value == "3":
		# 		self.startTeletext()
		# 	else:
		# 		try:
		# 			self.startTimeshift()
		# 		except Exception:
		# 			pass
		# else:
		# 	if config.plugins.infopanel_yellowkey.listLong.value == "0":
		# 		from Screens.AudioSelection import AudioSelection
		# 		self.session.openWithCallback(self.audioSelected, AudioSelection, infobar=self)
		# 	elif config.plugins.infopanel_yellowkey.listLong.value == "2":
		# 		AUDIO = True
		# 		ToggleVideo()
		# 	elif config.plugins.infopanel_yellowkey.listLong.value == "3":
		# 		self.startTeletext()
		# 	else:
		# 		try:
		# 			self.startTimeshift()
		# 		except Exception:
		# 			pass

	def audioSelection(self):
		from Screens.AudioSelection import AudioSelection
		self.session.openWithCallback(self.audioSelected, AudioSelection, infobar=self)

	def audioSelected(self, ret=None):
		print("[InfoBarGenerics] [infobar::audioSelected]", ret)

	def audioDownmixToggle(self, popup=True):
		if BoxInfo.getItem("CanDownmixAC3"):
			if config.av.downmix_ac3.value:
				config.av.downmix_ac3.setValue(False)
				status = "disabled"
				message = _("disabled")
			else:
				config.av.downmix_ac3.setValue(True)
				status = "enabled"
				message = _("enabled")
			print(f"[InfoBarGenerics] InfoBarAudioSelection: Dolby Digital down mix is now {status}.")
			if popup:
				Notifications.AddPopup(text=_("Dolby Digital downmix is now") + " " + message, type=MessageBox.TYPE_INFO, timeout=5, id="DDdownmixToggle")

	def audioDownmixOn(self):
		if not config.av.downmix_ac3.value:
			self.audioDownmixToggle(False)

	def audioDownmixOff(self):
		if config.av.downmix_ac3.value:
			self.audioDownmixToggle(False)


# Subservice processing.
#
instanceInfoBarSubserviceSelection = None


class InfoBarSubserviceSelection:
	def __init__(self):
		def subservicesHelp():
			fallback = _("Open RecordTimer Overview") if config.usage.subservice.value in (0, 2) else _("Open Plugin Browser")
			return _("Open Subservices selection") if self.countSubservices() else fallback

		global instanceInfoBarSubserviceSelection
		instanceInfoBarSubserviceSelection = self
		self.subservicesGroups = self.loadSubservicesGroups()
		self["SubserviceSelectionAction"] = HelpableActionMap(self, "InfobarSubserviceSelectionActions", {
			"selectSubservices": (self.keySelectSubservice, subservicesHelp())
		}, prio=0, description=_("Subservice Actions"))

	def loadSubservicesGroups(self):
		subservicesGroups = []
		groupedServicesFile = resolveFilename(SCOPE_CONFIG, "groupedservices")
		if not isfile(groupedServicesFile):
			groupedServicesFile = resolveFilename(SCOPE_SKINS, "groupedservices")
			if not isfile(groupedServicesFile):
				groupedServicesFile = None
				print("[InfoBarGenerics] InfoBarSubserviceSelection: No 'groupedservices' file found so no subservices available.")
		if groupedServicesFile:
			subservicesGroups = [list(g) for k, g in groupby([line.split("#")[0].strip() for line in fileReadLines(groupedServicesFile, [], source=MODULE_NAME)], lambda x: not x) if not k]
			count = len(subservicesGroups)
			print(f"[InfoBarGenerics] InfoBarSubserviceSelection: {count} subservice group{'' if count == 1 else 's'} loaded from '{groupedServicesFile}'.")
		return subservicesGroups

	def getSubserviceGroups(self):
		return self.subservicesGroups

	def countSubservices(self):
		result = 0
		serviceReference = self.session.nav.getCurrentlyPlayingServiceReference() and self.session.nav.getCurrentlyPlayingServiceReference().toCompareString()
		if serviceReference:
			if "%3a" in serviceReference:
				serviceReference = self.session.nav.getCurrentlyPlayingServiceReference().toString()
			subservices = self.getActiveSubservicesForCurrentService(serviceReference)
			if subservices and len(subservices) > 1 and serviceReference in subservices:
				result = subservices
		return result

	def hasActiveSubservicesForCurrentService(self, serviceReference):
		if serviceReference and "%3a" not in serviceReference:
			serviceReference = ":".join(serviceReference.split(":")[:11])
		match config.usage.showInfoBarSubservices.value:
			case 1:
				subservices = self.getActiveSubservicesForCurrentService(serviceReference)
			case 2:
				subservices = self.getPossibleSubservicesForCurrentService(serviceReference)
			case _:
				subservices = None
		return bool(subservices and len(subservices) > 1)

	def getActiveSubservicesForCurrentService(self, serviceReference):
		transmissionPaused = [
			"Sendepause"  # This is for German TV.
		]
		activeSubservices = []
		if config.usage.showInfoBarSubservices.value and serviceReference:
			possibleSubservices = self.getPossibleSubservicesForCurrentService(serviceReference)
			epgCache = eEPGCache.getInstance()
			for subservice in possibleSubservices:
				events = epgCache.lookupEvent(["T", (subservice, 0, -1)])
				if events and len(events) == 1:
					title = events[0][0]
					if title and not any([x for x in transmissionPaused if x in title]):
						activeSubservices.append(subservice)
				elif config.usage.showInfoBarSubservices.value == 2:
					activeSubservices.append(subservice)
		return activeSubservices

	def getPossibleSubservicesForCurrentService(self, serviceReference):
		possibleSubservices = []
		if serviceReference and self.subservicesGroups:
			possibleSubserviceGroups = [x for x in self.subservicesGroups if serviceReference in x]
			if possibleSubserviceGroups:
				possibleSubservices = possibleSubserviceGroups[0]  # If the service is in multiple groups should we return more options?
		return possibleSubservices

	def hotkeySubserviceSelection(self):  # Used in ButtonSetup
		self.keySelectSubservice(noSubservice=False)

	def keySelectSubservice(self, noSubservice=True):
		if config.usage.subservice.value > 1:
			if self.countSubservices():
				self.servicelist.enterSubservices()
				self.session.execDialog(self.servicelist)
				noSubservice = False
		if noSubservice:
			if config.usage.subservice.value in (0, 2):
				self.session.open(RecordTimerOverview)
			else:
				from Screens.PluginBrowser import PluginBrowser
				self.session.open(PluginBrowser)


from Components.Sources.HbbtvApplication import HbbtvApplication
gHbbtvApplication = HbbtvApplication()


class InfoBarRedButton:
	def __init__(self):
		self["RedButtonActions"] = HelpableActionMap(self, "InfobarRedButtonActions", {
			"activateRedButton": (self.activateRedButton, _("RED button / HbbTV")),
		}, prio=0, description=_("Red/HbbTV Button Actions"))
		self["HbbtvApplication"] = gHbbtvApplication
		self.onHBBTVActivation = []
		self.onRedButtonActivation = []
		self.onReadyForAIT = []
		self.__et = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evHBBTVInfo: self.detectedHbbtvApplication,
			iPlayableService.evUpdatedInfo: self.updateInfomation
		})

	def updateAIT(self, orgId=0):
		for x in self.onReadyForAIT:
			try:
				x(orgId)
			except Exception as ErrMsg:
				print("[InfoBarGenerics] updateAIT error", ErrMsg)
				# self.onReadyForAIT.remove(x)

	def updateInfomation(self):
		try:
			self["HbbtvApplication"].setApplicationName("")
			self.updateAIT()
		except Exception as ErrMsg:
			pass

	def detectedHbbtvApplication(self):
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		try:
			for x in info.getInfoObject(iServiceInformation.sHBBTVUrl):
				print("[InfoBarGenerics] HbbtvApplication:", x)
				if x[0] in (-1, 1):
					self.updateAIT(x[3])
					self["HbbtvApplication"].setApplicationName(x[1])
					break
		except Exception as ErrMsg:
			pass

	def activateRedButton(self):
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if info and info.getInfoString(iServiceInformation.sHBBTVUrl) != "":
			for x in self.onHBBTVActivation:
				x()
		# TODO: Other red button services.
		# elif False:
		# for x in self.onRedButtonActivation:
		# x()


class InfoBarTimerButton:
	def __init__(self):
		self["TimerButtonActions"] = HelpableActionMap(self, "InfobarTimerButtonActions", {
			"timerSelection": (self.timerSelection, _("Open RecordTimer Overview")),
		}, prio=0, description=_("Timer Actions"))

	def timerSelection(self):
		self.session.open(RecordTimerOverview)


class InfoBarAspectSelection:
	STATE_HIDDEN = 0
	STATE_ASPECT = 1
	STATE_RESOLUTION = 2

	def __init__(self):
		self["AspectSelectionAction"] = HelpableActionMap(self, "InfobarAspectSelectionActions", {
			"aspectSelection": (self.ExGreen_toggleGreen, _("Open Aspect Ratio Settings")),
		}, prio=0, description=_("Aspect Ratio Actions"))
		self.__ExGreen_state = self.STATE_HIDDEN

	def ExGreen_doAspect(self):
		print("[InfoBarGenerics] do self.STATE_ASPECT")
		self.__ExGreen_state = self.STATE_ASPECT
		self.aspectSelection()

	def ExGreen_doResolution(self):
		print("[InfoBarGenerics] do self.STATE_RESOLUTION")
		self.__ExGreen_state = self.STATE_RESOLUTION
		self.resolutionSelection()

	def ExGreen_doHide(self):
		print("[InfoBarGenerics] do self.STATE_HIDDEN")
		self.__ExGreen_state = self.STATE_HIDDEN

	def ExGreen_toggleGreen(self, arg=""):
		print("[InfoBarGenerics] toggleGreen:", self.__ExGreen_state)
		if self.__ExGreen_state == self.STATE_HIDDEN:
			print("[InfoBarGenerics] self.STATE_HIDDEN")
			self.ExGreen_doAspect()
		elif self.__ExGreen_state == self.STATE_ASPECT:
			print("[InfoBarGenerics] self.STATE_ASPECT")
			self.ExGreen_doResolution()
		elif self.__ExGreen_state == self.STATE_RESOLUTION:
			print("[InfoBarGenerics] self.STATE_RESOLUTION")
			self.ExGreen_doHide()

	def aspectSelection(self):
		selection = 0
		if BoxInfo.getItem("AmlogicFamily"):
			aspectList = [
				(_("Resolution"), "resolution"),
				("--", ""),
				(_("Normal"), "0"),
				(_("Full Stretch"), "1"),
				("4:3", "2"),
				("16:9", "3"),
				(_("Non-Linear"), "4"),
				(_("Normal No ScaleUp"), "5"),
				(_("4:3 Ignore"), "6"),
				(_("4:3 Letterbox"), "7"),
				(_("4:3 PanScan"), "8"),
				(_("4:3 Combined"), "9"),
				(_("16:9 Ignore"), "10"),
				(_("16:9 Letterbox"), "11"),
				(_("16:9 PanScan"), "12"),
				(_("16:9 Combined"), "13")
			]
		else:
			aspectSwitchList = []
			if config.av.aspectswitch.enabled.value:
				for aspect in range(5):
					aspectSwitchList.append((avSwitch.ASPECT_SWITCH_MSG[aspect], str(aspect + 100)))
				aspectSwitchList.append(("--", ""))
			aspectList = [
				(_("Resolution"), "resolution"),
				("--", "")
			] + aspectSwitchList + [
				(_("4:3 Letterbox"), "0"),
				(_("4:3 PanScan"), "1"),
				(_("16:9"), "2"),
				(_("16:9 Always"), "3"),
				(_("16:10 Letterbox"), "4"),
				(_("16:10 PanScan"), "5"),
				(_("16:9 Letterbox"), "6")
			]
		keys = ["green", "", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
		aspect = avSwitch.getAspectRatioSetting()
		selection = 0
		for item in range(len(aspectList)):
			if aspectList[item][1] == aspect:
				selection = item
				break
		self.session.openWithCallback(self.aspectSelected, ChoiceBox, text=_("Please select an aspect ratio..."), list=aspectList, keys=keys, selection=selection)

	def aspectSelected(self, aspect):
		if aspect is not None:
			if isinstance(aspect[1], str):
				if aspect[1] == "":
					self.ExGreen_doHide()
				elif aspect[1] == "resolution":
					self.ExGreen_toggleGreen()
				else:
					avSwitch.setAspectRatio(int(aspect[1]))
					self.ExGreen_doHide()
		else:
			self.ExGreen_doHide()


class InfoBarResolutionSelection:
	def __init__(self):
		pass

	def resolutionSelection(self):
		avControl = eAVControl.getInstance()
		fps = float(avControl.getFrameRate(50000)) / 1000.0
		yRes = avControl.getResolutionY(0)
		xRes = avControl.getResolutionX(0)
		resList = []
		resList.append((_("Exit"), "exit"))
		resList.append((_("Auto(not available)"), "auto"))
		resList.append((_("Video") + ": %dx%d@%gHz" % (xRes, yRes, fps), ""))
		resList.append(("--", ""))
		# Do we need a new sorting with this way here or should we disable some choices?
		videoModes = avSwitch.readPreferredModes(readOnly=True)
		videoModes = [x.replace("pal ", "").replace("ntsc ", "") for x in videoModes]  # Do we need this?
		for videoMode in videoModes:
			video = videoMode
			if videoMode.endswith("23"):
				video = "%s.976" % videoMode
			if videoMode[-1].isdigit():
				video = "%sHz" % videoMode
			resList.append((video, videoMode))
		videoMode = avControl.getVideoMode("Unknown")
		keys = ["green", "yellow", "blue", "", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
		selection = 0
		for index, item in enumerate(resList):
			if item[1] == videoMode:
				selection = index
				break
		print("[InfoBarGenerics] Current video mode is %s." % videoMode)
		self.session.openWithCallback(self.resolutionSelected, ChoiceBox, text=_("Please select a resolution..."), list=resList, keys=keys, selection=selection)

	def resolutionSelected(self, videoMode):
		if videoMode is not None:
			if isinstance(videoMode[1], str):
				if videoMode[1] == "exit" or videoMode[1] == "" or videoMode[1] == "auto":
					self.ExGreen_toggleGreen()
				if videoMode[1] != "auto":
					avSwitch.setVideoModeDirect(videoMode[1])
					self.ExGreen_doHide()
		else:
			self.ExGreen_doHide()


class InfoBarVmodeButton:
	def __init__(self):
		self["VmodeButtonActions"] = HelpableActionMap(self, "InfobarVmodeButtonActions", {
			"vmodeSelection": (self.vmodeSelection, _("LetterBox zoom")),
		}, prio=0, description=_("Zoom Actions"))

	def vmodeSelection(self):
		self.session.open(VideoMode)


class VideoMode(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["videomode"] = Label()
		self["actions"] = HelpableNumberActionMap(self, ["InfobarVmodeButtonActions"], {
			"vmodeSelection": (self.selectVMode, _("LetterBox zoom")),
		}, prio=0, description=_("Zoom Actions"))
		self.Timer = eTimer()
		self.Timer.callback.append(self.quit)
		self.selectVMode()

	def selectVMode(self):
		policy = config.av.policy_43
		if hasattr(config.av, "policy_169") and self.isWideScreen():
			policy = config.av.policy_169
		idx = policy.choices.index(policy.value)
		idx = (idx + 1) % len(policy.choices)
		policy.value = policy.choices[idx]
		self["videomode"].setText(policy.value)
		self.Timer.start(1000, True)

	def isWideScreen(self):
		from Components.Converter.ServiceInfo import WIDESCREEN
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		return info.getInfo(iServiceInformation.sAspect) in WIDESCREEN

	def quit(self):
		self.Timer.stop()
		self.close()


class InfoBarAdditionalInfo:
	def __init__(self):
		self["RecordingPossible"] = Boolean(fixed=harddiskmanager.HDDCount() > 0)
		self["TimeshiftPossible"] = self["RecordingPossible"]
		self["ExtensionsAvailable"] = Boolean(fixed=1)
		# TODO: These properties should be queried from the input device keymap.
		self["ShowTimeshiftOnYellow"] = Boolean(fixed=0)
		self["ShowAudioOnYellow"] = Boolean(fixed=0)
		self["ShowRecordOnRed"] = Boolean(fixed=0)


class InfoBarNotifications:
	def __init__(self):
		self.onExecBegin.append(self.checkNotifications)
		Notifications.notificationAdded.append(self.checkNotificationsIfExecing)
		self.onClose.append(self.__removeNotification)

	def __removeNotification(self):
		Notifications.notificationAdded.remove(self.checkNotificationsIfExecing)

	def checkNotificationsIfExecing(self):
		if self.execing:
			self.checkNotifications()

	def checkNotifications(self):
		notifications = Notifications.notifications
		if notifications:
			n = notifications[0]
			del notifications[0]
			cb = n[0]
			if "onSessionOpenCallback" in n[3]:
				n[3]["onSessionOpenCallback"]()
				del n[3]["onSessionOpenCallback"]
			if cb:
				dlg = self.session.openWithCallback(cb, n[1], *n[2], **n[3])
			elif not Notifications.current_notifications and n[4] == "ZapError":
				if "timeout" in n[3]:
					del n[3]["timeout"]
				n[3]["enable_input"] = False
				dlg = self.session.instantiateDialog(n[1], *n[2], **n[3])
				self.hide()
				dlg.show()
				self.notificationDialog = dlg
				eActionMap.getInstance().bindAction("", -maxsize - 4, self.keypressNotification)
			else:
				dlg = self.session.open(n[1], *n[2], **n[3])
			# Remember that this notification is currently active.
			d = (n[4], dlg)
			Notifications.current_notifications.append(d)
			dlg.onClose.append(boundFunction(self.__notificationClosed, d))

	def closeNotificationInstantiateDialog(self):
		if hasattr(self, "notificationDialog"):
			self.session.deleteDialog(self.notificationDialog)
			del self.notificationDialog
			eActionMap.getInstance().unbindAction("", self.keypressNotification)

	def keypressNotification(self, key, flag):
		if flag:
			self.closeNotificationInstantiateDialog()

	def __notificationClosed(self, d):
		Notifications.current_notifications.remove(d)


class InfoBarServiceNotifications:
	def __init__(self):
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evEnd: self.serviceHasEnded
			})

	def serviceHasEnded(self):
		# print("service end!")
		try:
			self.setSeekState(self.SEEK_STATE_PLAY)
		except Exception:
			pass


class InfoBarCueSheetSupport:
	CUT_TYPE_IN = 0
	CUT_TYPE_OUT = 1
	CUT_TYPE_MARK = 2
	CUT_TYPE_LAST = 3

	ENABLE_RESUME_SUPPORT = False

	def __init__(self, actionmap="InfobarCueSheetActions"):
		self["CueSheetActions"] = HelpableActionMap(self, actionmap, {
			"jumpPreviousMark": (self.jumpPreviousMark, _("Jump to previous marked position")),
			"jumpNextMark": (self.jumpNextMark, _("Jump to next marked position")),
			"toggleMark": (self.toggleMark, _("Toggle a cut mark at the current position"))
		}, prio=1, description=_("Marker Actions"))
		self.cut_list = []
		self.is_closing = False
		self.resumeTimer = eTimer()
		self.resumeTimer.callback.append(self.triggerResumeLogic)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evStart: self.__serviceStarted,
			iPlayableService.evCuesheetChanged: self.downloadCuesheet,
		})

	def __serviceStarted(self):
		self.resumeTimer.stop()
		self.resumeTimer.start(config.av.passthrough_fix_long.value + 1000, True)

	def triggerResumeLogic(self):
		if self.is_closing:
			return
		# print("[InfoBarGenerics] InfoBarCueSheetSupport: New service started, trying to download cuts.")
		self.downloadCuesheet()
		self.resume_point = None
		if self.ENABLE_RESUME_SUPPORT:
			for (pts, what) in self.cut_list:
				if what == self.CUT_TYPE_LAST:
					last = pts
					break
			else:
				last = getResumePoint(self.session)
			if last is None:
				return
			# Only resume if at least 10 seconds ahead, or <10 seconds before the end.
			seekable = self.__getSeekable()
			if seekable is None:
				return  # Should not happen?
			length = seekable.getLength() or (None, 0)
			# print(f"[InfoBarGenerics] InfoBarCueSheetSupport: Length returned is {length}.")
			# Hmm, this implies we don't resume if the length is unknown.
			if (last > 900000) and (not length[1] or (last < length[1] - 900000)):
				self.resume_point = last
				l = last // 90000
				if "ask" in config.usage.on_movie_start.value or not length[1]:
					Notifications.AddNotificationWithCallback(self.playLastCB, MessageBox, _("Do you want to resume this playback?") + "\n" + (_("Resume position at %s") % ("%d:%02d:%02d" % (l / 3600, l % 3600 / 60, l % 60))), timeout=30, default="yes" in config.usage.on_movie_start.value)
				elif config.usage.on_movie_start.value == "resume":
					Notifications.AddNotificationWithCallback(self.playLastCB, MessageBox, _("Resuming playback"), timeout=2, type=MessageBox.TYPE_INFO)

	def playLastCB(self, answer):
		if answer is True and self.resume_point:
			self.doSeek(self.resume_point)
		self.hideAfterResume()

	def hideAfterResume(self):
		if isinstance(self, InfoBarShowHide):
			self.hide()

	def __getSeekable(self):
		service = self.session.nav.getCurrentService()
		if service is None:
			return None
		return service.seek()

	def cueGetCurrentPosition(self):
		seek = self.__getSeekable()
		if seek is None:
			return None
		r = seek.getPlayPosition()
		if r[0]:
			return None
		return int(r[1])

	def cueGetEndCutPosition(self):
		ret = False
		isin = True
		for cp in self.cut_list:
			if cp[1] == self.CUT_TYPE_OUT:
				if isin:
					isin = False
					ret = cp[0]
			elif cp[1] == self.CUT_TYPE_IN:
				isin = True
		return ret

	def jumpPreviousNextMark(self, cmp, start=False):
		current_pos = self.cueGetCurrentPosition()
		if current_pos is None:
			return False
		mark = self.getNearestCutPoint(current_pos, cmp=cmp, start=start)
		if mark is not None:
			pts = mark[0]
		else:
			return False
		self.doSeek(pts)
		return True

	def jumpPreviousMark(self):
		# We add 5 seconds, so if the play position is <5s after
		# the mark, the mark before will be used.
		self.jumpPreviousNextMark(lambda x: -x - 5 * 90000, start=True)

	def jumpNextMark(self):
		if not self.jumpPreviousNextMark(lambda x: x - 90000):
			self.doSeek(-1)

	def getNearestCutPoint(self, pts, cmp=abs, start=False):
		# Can be optimized.
		beforecut = True
		nearest = None
		bestdiff = -1
		instate = True
		if start:
			bestdiff = cmp(0 - pts)
			if bestdiff >= 0:
				nearest = [0, False]
		for cp in self.cut_list:
			if beforecut and cp[1] in (self.CUT_TYPE_IN, self.CUT_TYPE_OUT):
				beforecut = False
				if cp[1] == self.CUT_TYPE_IN:  # Start is here, disregard previous marks.
					diff = cmp(cp[0] - pts)
					if start and diff >= 0:
						nearest = cp
						bestdiff = diff
					else:
						nearest = None
						bestdiff = -1
			if cp[1] == self.CUT_TYPE_IN:
				instate = True
			elif cp[1] == self.CUT_TYPE_OUT:
				instate = False
			elif cp[1] in (self.CUT_TYPE_MARK, self.CUT_TYPE_LAST):
				diff = cmp(cp[0] - pts)
				if instate and diff >= 0 and (nearest is None or bestdiff > diff):
					nearest = cp
					bestdiff = diff
		return nearest

	def toggleMark(self, onlyremove=False, onlyadd=False, tolerance=5 * 90000, onlyreturn=False):
		current_pos = self.cueGetCurrentPosition()
		if current_pos is None:
			# print("[InfoBarGenerics] InfoBarCueSheetSupport: Can't seek to current position.")
			return
		nearest_cutpoint = self.getNearestCutPoint(current_pos)
		if nearest_cutpoint is not None and abs(nearest_cutpoint[0] - current_pos) < tolerance:
			if onlyreturn:
				return nearest_cutpoint
			if not onlyadd:
				self.removeMark(nearest_cutpoint)
		elif not onlyremove and not onlyreturn:
			self.addMark((current_pos, self.CUT_TYPE_MARK))
		if onlyreturn:
			return None

	def addMark(self, point):
		insort(self.cut_list, point)
		self.uploadCuesheet()
		self.showAfterCuesheetOperation()

	def removeMark(self, point):
		self.cut_list.remove(point)
		self.uploadCuesheet()
		self.showAfterCuesheetOperation()

	def showAfterCuesheetOperation(self):
		if isinstance(self, InfoBarShowHide):
			self.doShow()

	def __getCuesheet(self):
		service = self.session.nav.getCurrentService()
		return None if service is None else service.cueSheet()

	def uploadCuesheet(self):
		cueSheet = self.__getCuesheet()
		# if cueSheet is None:
		# 	# print("[InfoBarGenerics] InfoBarCueSheetSupport: Upload failed, there is no cue sheet interface.")
		# 	return
		# cueSheet.setCutList(self.cut_list)
		return None if cueSheet is None else cueSheet.setCutList(self.cut_list)

	def downloadCuesheet(self):
		cueSheet = self.__getCuesheet()
		# if cueSheet is None:
		# 	# print("[InfoBarGenerics] InfoBarCueSheetSupport: Download failed, there is no cue sheet interface.")
		# 	self.cut_list = []
		# else:
		# 	self.cut_list = cueSheet.getCutList()
		self.cut_list = [] if cueSheet is None else cueSheet.getCutList()


class InfoBarSummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget source="global.CurrentTime" render="Label" position="62,46" size="82,18" font="Regular;16" >
			<convert type="ClockToText">WithSeconds</convert>
		</widget>
		<widget source="session.RecordState" render="FixedLabel" text=" " position="62,46" size="82,18" zPosition="1" >
			<convert type="ConfigEntryTest">config.usage.blinking_display_clock_during_recording,True,CheckSourceBoolean</convert>
			<convert type="ConditionalShowHide">Blink</convert>
		</widget>
		<widget source="session.CurrentService" render="Label" position="6,4" size="120,42" font="Regular;18" >
			<convert type="ServiceName">Name</convert>
		</widget>
		<widget source="session.Event_Now" render="Progress" position="6,46" size="46,18" borderWidth="1" >
			<convert type="EventTime">Progress</convert>
		</widget>
	</screen>"""

# For picon:  (path="piconlcd" will use LCD picons)
# 		<widget source="session.CurrentService" render="Picon" position="6,0" size="120,64" path="piconlcd" >
# 			<convert type="ServiceName">Reference</convert>
# 		</widget>


class InfoBarSummarySupport:
	def __init__(self):
		pass

	def createSummary(self):
		return InfoBarSummary


class InfoBarMoviePlayerSummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget source="global.CurrentTime" render="Label" position="62,46" size="64,18" font="Regular;16" halign="right" >
			<convert type="ClockToText">WithSeconds</convert>
		</widget>
		<widget source="session.RecordState" render="FixedLabel" text=" " position="62,46" size="64,18" zPosition="1" >
			<convert type="ConfigEntryTest">config.usage.blinking_display_clock_during_recording,True,CheckSourceBoolean</convert>
			<convert type="ConditionalShowHide">Blink</convert>
		</widget>
		<widget source="session.CurrentService" render="Label" position="6,4" size="120,42" font="Regular;18" >
			<convert type="ServiceName">Name</convert>
		</widget>
		<widget source="session.CurrentService" render="Progress" position="6,46" size="56,18" borderWidth="1" >
			<convert type="ServicePosition">Position</convert>
		</widget>
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["state_summary"] = StaticText("")
		self["speed_summary"] = StaticText("")
		self["statusicon_summary"] = MultiPixmap()
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self, state_summary, speed_summary, statusicon_summary):
		self["state_summary"].setText(state_summary)
		self["speed_summary"].setText(speed_summary)
		self["statusicon_summary"].setPixmapNum(int(statusicon_summary))


class InfoBarMoviePlayerSummarySupport:
	def __init__(self):
		pass

	def createSummary(self):
		return InfoBarMoviePlayerSummary


class InfoBarTeletextPlugin:
	def __init__(self):
		self.teletext_plugin = None
		for p in plugins.getPlugins(PluginDescriptor.WHERE_TELETEXT):
			self.teletext_plugin = p
		if self.teletext_plugin is not None:
			self["TeletextActions"] = HelpableActionMap(self, "InfobarTeletextActions", {
				"startTeletext": (self.startTeletext, _("View Teletext"))
			}, prio=0, description=_("Teletext Actions"))
		else:
			print("[InfoBarGenerics] no teletext plugin found!")

	def startTeletext(self):
		self.teletext_plugin and self.teletext_plugin(session=self.session, service=self.session.nav.getCurrentService())


class InfoBarSubtitleSupport:
	def __init__(self):
		object.__init__(self)
		self["SubtitleSelectionAction"] = HelpableActionMap(self, "InfobarSubtitleSelectionActions", {
			"subtitleSelection": (self.subtitleSelection, _("Open Subtitle options")),
		}, prio=0, description=_("Subtitle Actions"))
		self.selected_subtitle = None
		if isStandardInfoBar(self):
			self.subtitle_window = self.session.instantiateDialog(SubtitleDisplay)
			self.subtitle_window.setAnimationMode(0)
		else:
			from Screens.InfoBar import InfoBar
			self.subtitle_window = InfoBar.instance.subtitle_window
		self.subtitle_window.hide()
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evStart: self.__serviceChanged,
			iPlayableService.evEnd: self.__serviceChanged,
			iPlayableService.evUpdatedInfo: self.__updatedInfo
		})

	def getCurrentServiceSubtitle(self):
		service = self.session.nav.getCurrentService()
		return service and service.subtitle()

	def subtitleSelection(self):
		service = self.session.nav.getCurrentService()
		subtitle = service and service.subtitle()
		subtitlelist = subtitle and subtitle.getSubtitleList()
		if self.selected_subtitle or subtitlelist and len(subtitlelist) > 0:
			from Screens.AudioSelection import SubtitleSelection
			self.session.open(SubtitleSelection, self)
		else:
			return 0

	def doCenterDVBSubs(self):
		service = self.session.nav.getCurrentlyPlayingServiceReference()
		servicepath = service and service.getPath()
		if servicepath and servicepath.startswith("/"):
			if service.toString().startswith("1:"):
				info = eServiceCenter.getInstance().info(service)
				service = info and info.getInfoString(service, iServiceInformation.sServiceref)
				config.subtitles.dvb_subtitles_centered.value = service and eDVBDB.getInstance().getFlag(eServiceReference(service)) & self.FLAG_CENTER_DVB_SUBS and True
				return
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		config.subtitles.dvb_subtitles_centered.value = info and info.getInfo(iServiceInformation.sCenterDVBSubs) and True

	def subtitleQuickMenu(self):
		service = self.session.nav.getCurrentService()
		subtitle = service and service.subtitle()
		subtitlelist = subtitle and subtitle.getSubtitleList()
		if self.selected_subtitle and self.selected_subtitle != (0, 0, 0, 0):
			from Screens.AudioSelection import QuickSubtitlesConfigMenu
			self.session.open(QuickSubtitlesConfigMenu, self)
		else:
			self.subtitleSelection()

	def __serviceChanged(self):
		if self.selected_subtitle:
			self.selected_subtitle = None
			self.subtitle_window.hide()

	def __updatedInfo(self):
		if not self.selected_subtitle:
			subtitle = self.getCurrentServiceSubtitle()
			cachedsubtitle = subtitle.getCachedSubtitle()
			if cachedsubtitle:
				self.enableSubtitle(cachedsubtitle)
				self.doCenterDVBSubs()

	def enableSubtitle(self, selectedSubtitle):
		subtitle = self.getCurrentServiceSubtitle()
		self.selected_subtitle = selectedSubtitle
		if subtitle and self.selected_subtitle:
			subtitle.enableSubtitles(self.subtitle_window.instance, self.selected_subtitle)
			self.subtitle_window.show()
			self.doCenterDVBSubs()
		else:
			if subtitle:
				subtitle.disableSubtitles(self.subtitle_window.instance)
			self.subtitle_window.hide()

	def restartSubtitle(self):
		if self.selected_subtitle:
			self.enableSubtitle(self.selected_subtitle)


class InfoBarServiceErrorPopupSupport:
	def __init__(self):
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evTuneFailed: self.__tuneFailed,
			iPlayableService.evTunedIn: self.__serviceStarted,
			iPlayableService.evStart: self.__serviceStarted
		})
		self.__serviceStarted()

	def __serviceStarted(self):
		self.closeNotificationInstantiateDialog()
		self.last_error = None
		Notifications.RemovePopup(id="ZapError")

	def __tuneFailed(self):
		if not config.usage.hide_zap_errors.value or not config.usage.remote_fallback_enabled.value:
			service = self.session.nav.getCurrentService()
			info = service and service.info()
			error = info and info.getInfo(iServiceInformation.sDVBState)
			if not config.usage.remote_fallback_enabled.value and (error == eDVBServicePMTHandler.eventMisconfiguration or error == eDVBServicePMTHandler.eventNoResources):
				self.session.nav.currentlyPlayingServiceReference = None
				self.session.nav.currentlyPlayingServiceOrGroup = None
			if error == self.last_error:
				error = None
			else:
				self.last_error = error
			error = {
				eDVBServicePMTHandler.eventNoResources: _("No free tuner!"),
				eDVBServicePMTHandler.eventTuneFailed: _("Tune failed!"),
				eDVBServicePMTHandler.eventNoPAT: _("No data on transponder!\n(Timeout reading PAT)"),
				eDVBServicePMTHandler.eventNoPATEntry: _("Service not found!\n(SID not found in PAT)"),
				eDVBServicePMTHandler.eventNoPMT: _("Service invalid!\n(Timeout reading PMT)"),
				eDVBServicePMTHandler.eventNewProgramInfo: None,
				eDVBServicePMTHandler.eventTuned: None,
				eDVBServicePMTHandler.eventSOF: None,
				eDVBServicePMTHandler.eventEOF: None,
				eDVBServicePMTHandler.eventMisconfiguration: _("Service unavailable!\nCheck tuner configuration!"),
			}.get(error)  # This returns None when the key not exist in the dictionary.
			if error and not config.usage.hide_zap_errors.value:
				self.closeNotificationInstantiateDialog()
				if hasattr(self, "dishDialog") and not self.dishDialog.dishState():
					Notifications.AddPopup(text=error, type=MessageBox.TYPE_ERROR, timeout=5, id="ZapError")


class InfoBarZoom:
	def __init__(self):
		self.zoomrate = 0
		self.zoomin = 1
		self["ZoomActions"] = HelpableActionMap(self, "InfobarZoomActions", {
			"ZoomInOut": (self.ZoomInOut, _("Zoom In/Out TV")),
			"ZoomOff": (self.ZoomOff, _("Zoom Off")),
		}, prio=2, description=_("Zoom Actions"))

	def ZoomInOut(self):
		zoomval = 0
		if self.zoomrate > 3:
			self.zoomin = 0
		elif self.zoomrate < -9:
			self.zoomin = 1
		if self.zoomin == 1:
			self.zoomrate += 1
		else:
			self.zoomrate -= 1
		if self.zoomrate < 0:
			zoomval = abs(self.zoomrate) + 10
		else:
			zoomval = self.zoomrate
		# print("zoomRate:", self.zoomrate)
		# print("zoomval:", zoomval)
		file = open("/proc/stb/vmpeg/0/zoomrate", "w")
		file.write("%d" % int(zoomval))
		file.close()

	def ZoomOff(self):
		self.zoomrate = 0
		self.zoomin = 1
		f = open("/proc/stb/vmpeg/0/zoomrate", "w")
		f.write(str(0))
		f.close()


class InfoBarHdmi:
	def __init__(self):
		self.hdmi_enabled = False
		self.hdmi_enabled_full = False
		self.hdmi_enabled_pip = False
		if BoxInfo.getItem("HDMIin"):
			if not self.hdmi_enabled_full:
				self.addExtension((self.getHDMIInFullScreen, self.HDMIInFull, lambda: True))
			if BoxInfo.getItem("HDMIinPiP") and not self.hdmi_enabled_pip:
				self.addExtension((self.getHDMIInPiPScreen, self.HDMIInPiP, lambda: True))
		self["HDMIActions"] = HelpableActionMap(self, "InfobarHDMIActions", {
			"HDMIin": (self.HDMIIn, _("Switch to HDMI in mode")),
			"HDMIinLong": (self.HDMIInLong, _("Switch to HDMI in mode")),
		}, prio=2, description=_("HDMI-IN Actions"))

	def HDMIInLong(self):
		if self.LongButtonPressed:
			if not hasattr(self.session, "pip") and not self.session.pipshown:
				self.session.pip = self.session.instantiateDialog(PictureInPicture)
				self.session.pip.playService(hdmiInServiceRef())
				self.session.pip.show()
				self.session.pipshown = True
				self.session.pip.servicePath = self.servicelist.getCurrentServicePath()
			elif BoxInfo.getItem("HDMIinPiP"):
				curref = self.session.pip.getCurrentService()
				if curref and curref.type != eServiceReference.idServiceHDMIIn:
					self.session.pip.playService(hdmiInServiceRef())
					self.session.pip.servicePath = self.servicelist.getCurrentServicePath()
				else:
					self.session.pipshown = False
					del self.session.pip

	def HDMIIn(self):
		if not self.LongButtonPressed:
			slist = self.servicelist
			curref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if curref and curref.type != eServiceReference.idServiceHDMIIn:
				self.session.nav.playService(hdmiInServiceRef())
			else:
				self.session.nav.playService(slist.servicelist.getCurrent())

	def getHDMIInFullScreen(self):
		return _("Turn on HDMI-IN Full screen mode") if not self.hdmi_enabled_full else _("Turn off HDMI-IN Full screen mode")

	def getHDMIInPiPScreen(self):
		return _("Turn on HDMI-IN PiP mode") if not self.hdmi_enabled_pip else _("Turn off HDMI-IN PiP mode")

	def HDMIInPiP(self):
		if not hasattr(self.session, "pip") and not self.session.pipshown:
			self.hdmi_enabled_pip = True
			self.session.pip = self.session.instantiateDialog(PictureInPicture)
			self.session.pip.playService(hdmiInServiceRef())
			self.session.pip.show()
			self.session.pipshown = True
			self.session.pip.servicePath = self.servicelist.getCurrentServicePath()
		else:
			curref = self.session.pip.getCurrentService()
			if curref and curref.type != eServiceReference.idServiceHDMIIn:
				self.hdmi_enabled_pip = True
				self.session.pip.playService(hdmiInServiceRef())
				self.session.pip.servicePath = self.servicelist.getCurrentServicePath()
			else:
				self.hdmi_enabled_pip = False
				self.session.pipshown = False
				del self.session.pip

	def HDMIInFull(self):
		slist = self.servicelist
		curref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if curref and curref.type != eServiceReference.idServiceHDMIIn:
			self.hdmi_enabled_full = True
			self.session.nav.playService(hdmiInServiceRef())
		else:
			self.hdmi_enabled_full = False
			self.session.nav.playService(slist.servicelist.getCurrent())


class InfoBarSleepTimer:
	def __init__(self):
		global keyPressCallback
		self.sleepStartTime = 0
		self.sleepTimer = eTimer()
		self.sleepTimer.callback.append(self.sleepTimerTimeout)
		self.energyStartTime = 0
		self.energyTimer = eTimer()
		self.energyTimer.callback.append(self.energyTimerTimeout)
		keyPressCallback.append(self.resetEnergyTimer)

	def sleepTimerState(self):
		return self.getTimerRemaining(self.sleepTimer, self.sleepStartTime)

	def energyTimerState(self):
		return self.getTimerRemaining(self.energyTimer, self.energyStartTime)

	def getTimerRemaining(self, timer, startTime):
		if timer.isActive():
			return (startTime - int(time()))
		return 0

	def setSleepTimer(self, sleepTime, showMessage=True):
		self.sleepStartTime = self.setTimer(sleepTime, self.sleepStartTime, self.sleepTimer, _("Sleep timer"), showMessage=showMessage)

	def setEnergyTimer(self, energyTime, showMessage=True):
		self.energyStartTime = self.setTimer(energyTime, self.energyStartTime, self.energyTimer, _("Energy timer"), showMessage=showMessage)

	def resetEnergyTimer(self):
		if str(config.usage.energyTimer.value) == config.usage.energyTimer.savedValue:  # Don't change energy timer while it is being edited.
			self.energyStartTime = self.setTimer(config.usage.energyTimer.value, self.energyStartTime, self.energyTimer, _("Energy timer"), showMessage=False)

	def setTimer(self, delay, previous, timer, name, showMessage):
		minutes = delay // 60
		if delay:
			message = "%s\n%s %s" % (_("%s has been activated.") % name, _("Delay:"), _("%d minutes") % minutes)
			timer.startLongTimer(delay)
			delay = int(time()) + delay
		else:
			message = _("%s has been disabled.") % name
			timer.stop()
			delay = 0
		if showMessage and delay != previous:
			print("[InfoBarGenerics] InfoBarSleepTimer: %s set to %d minutes." % (name, minutes))
			Notifications.AddPopup(message, type=MessageBox.TYPE_INFO, timeout=5)
		return delay

	def sleepTimerTimeout(self):
		action = config.usage.sleepTimerAction.value
		brand, model, timeout = self.timerTimeout(action, self.setSleepTimer, _("Sleep Timer"))
		if brand:
			if not Screens.Standby.inStandby:
				optionList = [
					(_("Yes"), True),
					(_("No"), False),
					(_("Extend"), "extend")
				]
				state = _("Standby") if action == "standby" else _("Deep Standby")
				message = _("The sleep timer wants to set the %s %s to %s.\n\nDo that now or extend the timer?") % (brand, model, state)
				self.session.openWithCallback(self.sleepTimerTimeoutCallback, MessageBox, message, timeout=timeout, list=optionList, default=True, windowTitle=_("Sleep Timer"))  # , simple=True
			else:
				self.timerStandby(action)

	def sleepTimerTimeoutCallback(self, answer):
		if answer == "extend":
			from Screens.SleepTimer import SleepTimer
			self.session.open(SleepTimer)
		elif answer:
			self.timerStandby(config.usage.sleepTimerAction.value)
		else:
			self.setSleepTimer(0, showMessage=False)

	def energyTimerTimeout(self):
		action = config.usage.energyTimerAction.value
		brand, model, timeout = self.timerTimeout(action, self.setEnergyTimer, _("Energy Timer"))
		if brand:
			if not Screens.Standby.inStandby:
				state = _("Standby") if action == "standby" else _("Deep Standby")
				message = _("The energy timer wants to set the %s %s to %s.\n\nPress OK to continue using the %s %s.") % (brand, model, state, brand, model)
				self.session.openWithCallback(self.energyTimerTimeoutCallback, MessageBox, message, type=MessageBox.TYPE_WARNING, timeout=timeout, default=True, timeoutDefault=False, windowTitle=_("Energy Timer"))  # , simple=True
			else:
				self.timerStandby(action)

	def energyTimerTimeoutCallback(self, answer):
		if answer:
			self.setEnergyTimer(0, showMessage=False)
		else:
			self.timerStandby(config.usage.energyTimerAction.value)

	def timerTimeout(self, action, timerMethod, name):
		brand = BoxInfo.getItem("displaybrand")
		model = BoxInfo.getItem("displaymodel")
		timeout = int(config.usage.shutdown_msgbox_timeout.value)
		if action != "standby":
			isRecordTime = abs(self.session.nav.RecordTimer.getNextRecordingTime() - time()) <= 900 or self.session.nav.RecordTimer.getStillRecording() or abs(self.session.nav.RecordTimer.getNextZapTime() - time()) <= 900
			isScheduler = abs(self.session.nav.Scheduler.getNextPowerManagerTime() - time()) <= 900 or self.session.nav.Scheduler.isProcessing(exceptTimer=0)
			if isRecordTime or isScheduler:
				timerMethod(1800, showMessage=False)  # 1800 = 30 minutes.
				if not Screens.Standby.inStandby:
					message = _("A recording, recording timer or scheduled task is running or will begin within 15 minutes. %s extended to 30 minutes. Your %s %s will go to Deep Standby after the recording or scheduled task.\n\nGo to Deep Standby now?") % (name, brand, model)
					self.session.openWithCallback(boundFunction(self.timerStandby, action), MessageBox, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True, windowTitle=name)
				return None, None, None
		return brand, model, timeout

	def timerStandby(self, action, answer=None):
		if action == "standby" or answer:
			if not Screens.Standby.inStandby:
				print("[InfoBarGenerics] InfoBarSleepTimer: Going to Standby.")
				self.session.open(Screens.Standby.Standby)
		elif answer is None:
			if not Screens.Standby.inStandby:
				if not Screens.Standby.inTryQuitMainloop:
					print("[InfoBarGenerics] InfoBarSleepTimer: Going to Deep Standby.")
					self.session.open(Screens.Standby.TryQuitMainloop, 1)
			else:
				print("[InfoBarGenerics] InfoBarSleepTimer: Going to Deep Standby.")
				quitMainloop(1)


# ########################################################################################
# For displayed power or record timer messages in foreground and for callback execution. #
# ########################################################################################
#
class InfoBarOpenOnTopHelper:
	def __init__(self):
		pass

	def openInfoBarMessage(self, message, messageboxtyp, timeout=-1):
		try:
			self.session.open(MessageBox, message, messageboxtyp, timeout=timeout)
		except Exception as e:
			print("[InfoBarOpenMessage] Exception:", e)

	def openInfoBarMessageWithCallback(self, callback, message, messageboxtyp, timeout=-1, default=True):
		try:
			self.session.openWithCallback(callback, MessageBox, message, messageboxtyp, timeout=timeout, default=default)
		except Exception as e:
			print("[InfoBarGenerics] [openInfoBarMessageWithCallback] Exception:", e)

	def openInfoBarSession(self, session, option=None):
		try:
			if option is None:
				self.session.open(session)
			else:
				self.session.open(session, option)
		except Exception as e:
			print("[InfoBarGenerics] [openInfoBarSession] Exception:", e)


# ################################################################
# Handle bsod (python crashes) and show information after crash. #
# ################################################################
#
class InfoBarHandleBsod:
	def __init__(self):
		self.lastBsod = 0
		self.infoBsodIsShown = False
		self.lastestBsodWarning = False
		self.checkBsodTimer = eTimer()
		self.checkBsodTimer.callback.append(self.checkBsodCallback)
		self.checkBsodTimer.start(1000, True)
		config.crash.bsodpython_ready.setValue(True)

	def checkBsodCallback(self):
		self.checkBsodTimer.start(1000, True)
		if Screens.Standby.inStandby or self.infoBsodIsShown:
			return
		bsodcnt = getBsodCounter()
		if config.crash.bsodpython.value and self.lastBsod < bsodcnt:
			maxbs = int(config.crash.bsodmax.value) or 100
			writelog = bsodcnt == 1 or not bsodcnt > int(config.crash.bsodhide.value) or bsodcnt >= maxbs
			txt = _("Your Receiver has a Software problem detected. Since the last reboot it has occurred %d times.\n") % bsodcnt
			txt += _("(Attention: There will be a restart after %d crashes.)") % maxbs
			if writelog:
				txt += "\n" + "-" * 80 + "\n"
				txt += _("A crash log was %s created in '%s'") % ((_("not"), "")[int(writelog)], config.crash.debug_path.value)
			# if not writelog:
			# 	txt += "\n" + "-"*80 + "\n"
			# 	txt += _("(It is set that '%s' crash logs are displayed and written.\nInfo: It will always write the first, last but one and lastest crash log.)") % str(int(config.crash.bsodhide.value) or _("Never"))
			if bsodcnt >= maxbs:
				txt += "\n" + "-" * 80 + "\n"
				txt += _("Warning: This is the last crash before an automatic restart is performed.\n")
				txt += _("Should the crash counter be reset to prevent a restart?")
				self.lastestBsodWarning = True
			try:
				self.session.openWithCallback(self.infoBsodCallback, MessageBox, txt, type=MessageBox.TYPE_YESNO if self.lastestBsodWarning else MessageBox.TYPE_ERROR, default=False, close_on_any_key=not self.lastestBsodWarning, typeIcon=MessageBox.TYPE_ERROR)
				self.infoBsodIsShown = True
			except Exception as e:
				# print("[InfoBarHandleBsod] Exception:", e)
				self.checkBsodTimer.stop()
				self.checkBsodTimer.start(5000, True)
				self.infoBsodCallback(False)
				raise
		self.lastBsod = bsodcnt

	def infoBsodCallback(self, ret):
		if ret and self.lastestBsodWarning:
			resetBsodCounter()
		self.infoBsodIsShown = False
		self.lastestBsodWarning = False
