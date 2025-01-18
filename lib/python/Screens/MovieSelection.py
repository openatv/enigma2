from pickle import dump, load
from os import W_OK, access, listdir, mkdir, rename, rmdir, stat
from os.path import abspath, exists, isdir, isfile, join, normpath, pardir, realpath, split, splitext
from time import time

from enigma import eRCInput, eServiceCenter, eServiceReference, eServiceReferenceFS, eTimer, eSize, iPlayableService, iServiceInformation, getPrevAsciiCode, pNavigation

import NavigationInstance
from RecordTimer import AFTEREVENT, RecordTimerEntry
from Components.ActionMap import ActionMap, HelpableActionMap, NumberActionMap
from Components.config import ConfigLocations, ConfigSelection, ConfigSelectionNumber, ConfigSet, ConfigSubsection, ConfigText, ConfigYesNo, config
from Components.DiskInfo import DiskInfo
from Components.Harddisk import harddiskmanager
from Components.MenuList import MenuList
from Components.MovieList import AUDIO_EXTENSIONS, DVD_EXTENSIONS, IMAGE_EXTENSIONS, MovieList, resetMoviePlayState
from Components.Pixmap import MultiPixmap, Pixmap
from Components.Label import Label
from Components.PluginComponent import plugins
from Components.ServiceEventTracker import InfoBarBase, ServiceEventTracker
from Components.UsageConfig import preferredTimerPath
from Components.Sources.Boolean import Boolean
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
import Screens.InfoBar
from Screens.LocationBox import MovieLocationBox
from Screens.MessageBox import MessageBox
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.TagEditor import TagEditor
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.BoundFunction import boundFunction
from Tools.CopyFiles import copyFiles, deleteFiles, moveFiles
from Tools.Directories import SCOPE_HDD, isPluginInstalled, resolveFilename
from Tools.NumericalTextInput import NumericalTextInput
from Tools.Trashcan import TRASHCAN, TrashInfo, cleanAll, createTrashcan, getTrashcan

config.movielist = ConfigSubsection()
config.movielist.curentlyplayingservice = ConfigText()
config.movielist.show_live_tv_in_movielist = ConfigYesNo(default=True)
config.movielist.fontsize = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
config.movielist.itemsperpage = ConfigSelectionNumber(default=20, stepwidth=1, min=3, max=30, wraparound=True)
config.movielist.useslim = ConfigYesNo(default=False)
config.movielist.useextlist = ConfigSelection(default="0", choices={"0": _("No"), "1": _("ServiceName"), "2": _("ServicePicon")})
config.movielist.eventinfo_delay = ConfigSelectionNumber(50, 1000, 50, default=100)
config.movielist.last_videodir = ConfigText(default=resolveFilename(SCOPE_HDD))
config.movielist.last_timer_videodir = ConfigText(default=resolveFilename(SCOPE_HDD))
config.movielist.videodirs = ConfigLocations(default=[resolveFilename(SCOPE_HDD)])
config.movielist.last_selected_tags = ConfigSet([], default=[])
config.movielist.play_audio_internal = ConfigYesNo(default=True)
config.movielist.settings_per_directory = ConfigYesNo(default=False)
config.movielist.root = ConfigSelection(default="/media", choices=["/", "/media", "/media/hdd", "/media/hdd/movie", "/media/usb", "/media/usb/movie"])
config.movielist.hide_extensions = ConfigYesNo(default=False)
config.movielist.stop_service = ConfigYesNo(default=True)
config.movielist.show_underscores = ConfigYesNo(default=False)

userDefinedButtons = None
last_selected_dest = []

# This kludge is needed because ConfigSelection only takes numbers and someone appears to be fascinated by "enums".
#
l_moviesort = [
	(MovieList.SORT_GROUPWISE, _("default"), "02/01 & A-Z"),
	(MovieList.SORT_RECORDED, _("by date"), "03/02/01"),
	(MovieList.SORT_ALPHANUMERIC, _("alphabetic"), "A-Z"),
	(MovieList.SORT_ALPHANUMERIC_FLAT, _("flat alphabetic"), "A-Z Flat"),
	(MovieList.SHUFFLE, _("shuffle"), "?"),
	(MovieList.SORT_RECORDED_REVERSE, _("reverse by date"), "01/02/03"),
	(MovieList.SORT_ALPHANUMERIC_REVERSE, _("alphabetic reverse"), "Z-A"),
	(MovieList.SORT_ALPHANUMERIC_FLAT_REVERSE, _("flat alphabetic reverse"), "Z-A Flat"),
	(MovieList.SORT_ALPHA_DATE_OLDEST_FIRST, _("alpha then oldest"), "A1 A2 Z1"),
	(MovieList.SORT_ALPHAREV_DATE_NEWEST_FIRST, _("alpharev then newest"), "Z1 A2 A1")]

config.movielist.moviesort = ConfigSelection(default=MovieList.SORT_GROUPWISE, choices=l_moviesort)

l_desc = [
	(MovieList.SHOW_DESCRIPTION, _("Yes")),
	(MovieList.HIDE_DESCRIPTION, _("No"))
]

config.movielist.description = ConfigSelection(default=MovieList.SHOW_DESCRIPTION, choices=l_desc)


def defaultMoviePath():
	result = config.usage.default_path.value
	if not isdir(result):
		from Tools import Directories
		return Directories.defaultRecordingLocation(config.usage.default_path.value)
	return result


def setPreferredTagEditor(tageditor):  # Wrapper function for old plugins.
	return


def getPreferredTagEditor():  # Wrapper function for old plugins.
	return None


def isTrashFolder(ref):
	if not config.usage.movielist_trashcan.value or not ref.flags & eServiceReference.mustDescent:
		return False
	return realpath(ref.getPath()).endswith(TRASHCAN) or realpath(ref.getPath()).endswith(f"{TRASHCAN}/")


def isInTrashFolder(ref):
	if not config.usage.movielist_trashcan.value or not ref.flags & eServiceReference.mustDescent:
		return False
	path = realpath(ref.getPath())
	return path.startswith(getTrashcan(path))


def isSimpleFile(item):
	if not item:
		return False
	if not item[0] or not item[1]:
		return False
	return (item[0].flags & eServiceReference.mustDescent) == 0


def isFolder(item):
	if not item:
		return False
	if not item[0] or not item[1]:
		return False
	return (item[0].flags & eServiceReference.mustDescent) != 0


def canMove(item):
	if not item:
		return False
	if not item[0] or not item[1]:
		return False
	return True


canDelete = canMove
canCopy = canMove
canRename = canMove


def createMoveList(serviceref, dest):
	src = normpath(serviceref.getPath())  # normpath is to remove the trailing "/" from directories.
	srcPath, srcName = split(src)
	if normpath(srcPath) == dest:  # Move file to itself is allowed, so we have to check it.
		raise Exception("Refusing to move to the same directory")
	moveList = [(src, join(dest, srcName))]  # Make a list of items to move.
	if not serviceref.flags & eServiceReference.mustDescent:  # Real movie, add extra files.
		srcBase = splitext(src)[0]
		baseName = split(srcBase)[1]
		eitName = f"{srcBase}.eit"
		if exists(eitName):
			moveList.append((eitName, join(dest, f"{baseName}.eit")))
		baseName = split(src)[1]
		for ext in ("%s.ap", "%s.cuts", "%s.meta", "%s.sc"):
			candidate = ext % src
			if exists(candidate):
				moveList.append((candidate, join(dest, ext % baseName)))
	return moveList


def moveServiceFiles(serviceref, dest, name=None, allowCopy=True):
	moveList = createMoveList(serviceref, dest)
	try:
		# print("[MovieSelection] Moving in background.")
		moveList.reverse()  # Start with the smaller files, do the big one later.
		if name is None:
			name = split(moveList[-1][0])[1]
		moveFiles(moveList, name)
	except OSError as err:
		print(f"[MovieSelection] Error {err.errno}: Failed move!  ({err.strerror})")
		raise  # Throw exception.


def copyServiceFiles(serviceref, dest, name=None):
	moveList = createMoveList(serviceref, dest)  # Current should be "ref" type, dest a simple path string.
	try:
		# print("[MovieSelection] Copying in background.")
		moveList.reverse()  # Start with the smaller files, do the big one later.
		if name is None:
			name = split(moveList[-1][0])[1]
		copyFiles(moveList, name)
	except OSError as err:
		print(f"[MovieSelection] Error {err.errno}: Failed copy!  ({err.strerror})")
		raise  # Throw exception.


# Appends possible destinations to the bookmarks object. Appends tuples
# in the form (description, path) to it.
#
def buildMovieLocationList(bookmarks):
	inlist = []
	for d in config.movielist.videodirs.value:
		d = normpath(d)
		bookmarks.append((d, d))
		inlist.append(d)
	for p in harddiskmanager.getMountedPartitions():
		d = normpath(p.mountpoint)
		if d in inlist:  # Improve shortcuts to mount points.
			try:
				bookmarks[bookmarks.index((d, d))] = (p.tabbedDescription(), d)
			except Exception:
				pass  # When already listed as some "friendly" name.
		else:
			bookmarks.append((p.tabbedDescription(), d))
		inlist.append(d)
	for d in last_selected_dest:
		if d not in inlist:
			bookmarks.append((d, d))


class SelectionEventInfo:
	def __init__(self):
		self["Service"] = ServiceEvent()
		self.list.connectSelChanged(self.__selectionChanged)
		self.timer = eTimer()
		self.timer.callback.append(self.updateEventInfo)
		self.onShown.append(self.__selectionChanged)

	def __selectionChanged(self):
		if self.execing and self.settings["description"] == MovieList.SHOW_DESCRIPTION:
			self.timer.start(int(config.movielist.eventinfo_delay.value), True)

	def updateEventInfo(self):
		serviceref = self.getCurrent()
		self["Service"].newService(serviceref)


class MovieSelection(Screen, SelectionEventInfo, InfoBarBase, ProtectedScreen):
	# SUSPEND_PAUSES actually means "please call my pauseService()".

	def __init__(self, session, selectedmovie=None, timeshiftEnabled=False):
		Screen.__init__(self, session, enableHelp=True)
		if config.movielist.useslim.value:
			self.skinName = ["MovieSelectionSlim", "MovieSelection"]
		else:
			self.skinName = "MovieSelection"
		if config.ParentalControl.configured.value:
			ProtectedScreen.__init__(self)
		if not timeshiftEnabled:
			InfoBarBase.__init__(self)  # For ServiceEventTracker.
		ProtectedScreen.__init__(self)
		self.protectContextMenu = True
		self.initUserDefinedActions()
		self.tags = {}
		if selectedmovie:
			self.selected_tags = config.movielist.last_selected_tags.value
		else:
			self.selected_tags = None
		self.selected_tags_ele = None
		self.nextInBackground = None
		self.movemode = False
		self.bouquet_mark_edit = False
		self.feedbackTimer = None
		self.pathselectEnabled = False
		self.numericalTextInput = NumericalTextInput(mapping=NumericalTextInput.MAP_SEARCH_UPCASE)
		self["chosenletter"] = Label("")
		self["chosenletter"].visible = False
		self["waitingtext"] = Label(_("Please wait... Loading list..."))
		self.LivePlayTimer = eTimer()
		self.LivePlayTimer.timeout.get().append(self.LivePlay)
		self.filePlayingTimer = eTimer()
		self.filePlayingTimer.timeout.get().append(self.FilePlaying)
		self.playingInForeground = None
		self["DescriptionBorder"] = Pixmap()  # Create optional description border and hide immediately.
		self["DescriptionBorder"].hide()
		if not isdir(config.movielist.last_videodir.value):
			config.movielist.last_videodir.value = defaultMoviePath()
			config.movielist.last_videodir.save()
		self.setCurrentRef(config.movielist.last_videodir.value)
		self.settings = {
			"moviesort": config.movielist.moviesort.value,
			"description": config.movielist.description.value,
			"movieoff": config.usage.on_movie_eof.value
		}
		self.movieOff = self.settings["movieoff"]
		self["list"] = MovieList(None, sort_type=self.settings["moviesort"], descr_state=self.settings["description"])
		self.list = self["list"]
		self.selectedmovie = selectedmovie
		self.playGoTo = None  # 1: Preview next item, -1: Preview previous item.
		self.setTitle(_("Movie selection"))
		SelectionEventInfo.__init__(self)
		self["key_red"] = StaticText()
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self._updateButtonTexts()
		self["movie_off"] = MultiPixmap()
		self["movie_off"].hide()
		self["movie_sort"] = MultiPixmap()
		self["movie_sort"].hide()
		self["freeDiskSpace"] = self.diskinfo = DiskInfo(config.movielist.last_videodir.value, DiskInfo.FREE, update=False)
		self["TrashcanSize"] = self.trashinfo = TrashInfo(config.movielist.last_videodir.value)
		self["InfobarActions"] = HelpableActionMap(self, ["InfobarActions"], {
			"showMovies": (self.doPathSelect, _("Select the movie path")),
			"showRadio": (self.btn_radio, boundFunction(self.getinitUserDefinedActionsDescription, "btn_radio")),
			"showTv": (self.btn_tv, boundFunction(self.getinitUserDefinedActionsDescription, "btn_tv"))
		}, prio=0)
		self["NumberActions"] = NumberActionMap(["NumberActions", "InputAsciiActions"], {
			"gotAsciiCode": self.keyAsciiCode,
			"0": self.keyNumberGlobal,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal
		}, prio=0)
		self["playbackActions"] = HelpableActionMap(self, ["MoviePlayerActions"], {
			"leavePlayer": (self.playbackStop, _("Stop")),
			"moveNext": (self.playNext, _("Play next")),
			"movePrev": (self.playPrev, _("Play previous")),
			"channelUp": (self.moveToFirstOrFirstFile, _("Go to first movie or top of list")),
			"channelDown": (self.moveToLastOrFirstFile, _("Go to first movie or last item"))
		}, prio=0)
		self["MovieSelectionActions"] = HelpableActionMap(self, ["MovieSelectionActions"], {
			"contextMenu": (self.doContext, _("Menu")),
			"showEventInfo": (self.showEventInformation, _("Show event details")),
			"showText": (self.btn_text, boundFunction(self.getinitUserDefinedActionsDescription, "btn_text"))
		}, prio=0)
		if isPluginInstalled("SubsSupport"):
			self["SubtitleActions"] = HelpableActionMap(self, ["MovieSelectionActions"], {
				"subtitle": (self.openSubsSupport, _("Open external subtitle management screen"))
			}, prio=0)
		self["ColorActions"] = HelpableActionMap(self, ["ColorActions"], {
			"red": (self.btn_red, boundFunction(self.getinitUserDefinedActionsDescription, "btn_red")),
			"green": (self.btn_green, boundFunction(self.getinitUserDefinedActionsDescription, "btn_green")),
			"yellow": (self.btn_yellow, boundFunction(self.getinitUserDefinedActionsDescription, "btn_yellow")),
			"blue": (self.btn_blue, boundFunction(self.getinitUserDefinedActionsDescription, "btn_blue")),
			"redlong": (self.btn_redlong, boundFunction(self.getinitUserDefinedActionsDescription, "btn_redlong")),
			"greenlong": (self.btn_greenlong, boundFunction(self.getinitUserDefinedActionsDescription, "btn_greenlong")),
			"yellowlong": (self.btn_yellowlong, boundFunction(self.getinitUserDefinedActionsDescription, "btn_yellowlong")),
			"bluelong": (self.btn_bluelong, boundFunction(self.getinitUserDefinedActionsDescription, "btn_bluelong"))
		}, prio=0)
		self["FunctionKeyActions"] = HelpableActionMap(self, ["FunctionKeyActions"], {
			"f1": (self.btn_F1, boundFunction(self.getinitUserDefinedActionsDescription, "btn_F1")),
			"f2": (self.btn_F2, boundFunction(self.getinitUserDefinedActionsDescription, "btn_F2")),
			"f3": (self.btn_F3, boundFunction(self.getinitUserDefinedActionsDescription, "btn_F3"))
		}, prio=0)
		self["OkCancelActions"] = HelpableActionMap(self, ["OkCancelActions"], {
			"cancel": (self.abort, _("Exit movie list")),
			"ok": (self.itemSelected, _("Select movie"))
		}, prio=0)
		self["DirectionActions"] = HelpableActionMap(self, ["DirectionActions"], {
			"up": (self.keyUp, _("Go up the list")),
			"down": (self.keyDown, _("Go down the list"))
		}, prio=-2)
		tPreview = _("Preview")
		tFwd = f"{_("skip forward")} ({tPreview})"
		tBack = f"{_("skip backward")} ({tPreview})"
		sfwd = lambda: self.seekRelative(1, config.seek.selfdefined_46.value * 90000)
		ssfwd = lambda: self.seekRelative(1, config.seek.selfdefined_79.value * 90000)
		sback = lambda: self.seekRelative(-1, config.seek.selfdefined_46.value * 90000)
		ssback = lambda: self.seekRelative(-1, config.seek.selfdefined_79.value * 90000)
		self["SeekActions"] = HelpableActionMap(self, ["MovielistSeekActions"], {
			"playpauseService": (self.preview, _("Preview")),
			"seekFwd": (sfwd, tFwd),
			"seekFwdManual": (ssfwd, tFwd),
			"seekBack": (sback, tBack),
			"seekBackManual": (ssback, tBack)
		}, prio=5)
		self.onShown.append(self.onFirstTimeShown)
		self.onLayoutFinish.append(self.saveListsize)
		self.list.connectSelChanged(self.updateButtons)
		self.onClose.append(self.__onClose)
		NavigationInstance.instance.RecordTimer.on_state_change.append(self.list.updateRecordings)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			# iPlayableService.evSeekableStatusChanged: self.__seekableStatusChanged,
			iPlayableService.evStart: self.__serviceStarted,
			iPlayableService.evEOF: self.__evEOF,
			# iPlayableService.evSOF: self.__evSOF,
		})
		self.onExecBegin.append(self.asciiOff if config.misc.remotecontrol_text_support.value else self.asciiOn)

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and config.ParentalControl.config_sections.movie_list.value

	def asciiOn(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmAscii)

	def asciiOff(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)

	def initUserDefinedActions(self):
		global userDefinedButtons, userDefinedActions, config
		if userDefinedButtons is None:
			userDefinedActions = {
				"delete": _("Delete"),
				"move": _("Move"),
				"copy": _("Copy"),
				"reset": _("Reset"),
				"tags": _("Tags"),
				"addbookmark": _("Add Bookmark"),
				"bookmarks": _("Bookmarks"),
				"rename": _("Rename"),
				"gohome": _("Home"),
				"sort": _("Sort"),
				"sortby": _("Sort by"),
				"sortdefault": _("Sort by default"),
				"preview": _("Preview"),
				"movieoff": _("On end of movie"),
				"movieoff_menu": _("On end of movie (as menu)")
			}
			for plugin in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST):
				userDefinedActions[f"@{plugin.name}"] = plugin.description
			locations = []
			buildMovieLocationList(locations)
			for d, p in locations:
				if p and p.startswith("/"):
					userDefinedActions[p] = f"{_("Goto")}: {d}"
			config.movielist.btn_red = ConfigSelection(default="delete", choices=userDefinedActions)
			config.movielist.btn_green = ConfigSelection(default="move", choices=userDefinedActions)
			config.movielist.btn_yellow = ConfigSelection(default="bookmarks", choices=userDefinedActions)
			config.movielist.btn_blue = ConfigSelection(default="sort", choices=userDefinedActions)
			config.movielist.btn_redlong = ConfigSelection(default="rename", choices=userDefinedActions)
			config.movielist.btn_greenlong = ConfigSelection(default="copy", choices=userDefinedActions)
			config.movielist.btn_yellowlong = ConfigSelection(default="tags", choices=userDefinedActions)
			config.movielist.btn_bluelong = ConfigSelection(default="sortdefault", choices=userDefinedActions)
			config.movielist.btn_radio = ConfigSelection(default="tags", choices=userDefinedActions)
			config.movielist.btn_tv = ConfigSelection(default="gohome", choices=userDefinedActions)
			config.movielist.btn_text = ConfigSelection(default="movieoff", choices=userDefinedActions)
			config.movielist.btn_F1 = ConfigSelection(default="movieoff_menu", choices=userDefinedActions)
			config.movielist.btn_F2 = ConfigSelection(default="preview", choices=userDefinedActions)
			config.movielist.btn_F3 = ConfigSelection(default="/media", choices=userDefinedActions)
		userDefinedButtons = {
			"red": config.movielist.btn_red,
			"green": config.movielist.btn_green,
			"yellow": config.movielist.btn_yellow,
			"blue": config.movielist.btn_blue,
			"redlong": config.movielist.btn_redlong,
			"greenlong": config.movielist.btn_greenlong,
			"yellowlong": config.movielist.btn_yellowlong,
			"bluelong": config.movielist.btn_bluelong,
			"Radio": config.movielist.btn_radio,
			"TV": config.movielist.btn_tv,
			"Text": config.movielist.btn_text,
			"F1": config.movielist.btn_F1,
			"F2": config.movielist.btn_F2,
			"F3": config.movielist.btn_F3
		}

	def getinitUserDefinedActionsDescription(self, key):
		return _(userDefinedActions.get(eval(f"config.movielist.{key}.value"), _("Not Defined")))

	def _callButton(self, name):
		if name.startswith("@"):
			item = self.getCurrentSelection()
			if isSimpleFile(item):
				name = name[1:]
				for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST):
					if name == p.name:
						p(self.session, item[0])
		elif name.startswith("/"):
			self.gotFilename(name)
		else:
			try:
				a = getattr(self, f"do_{name}")
			except Exception:  # Undefined action.
				return
			a()

	def btn_red(self):
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_red.value)

	def btn_green(self):
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_green.value)

	def btn_yellow(self):
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_yellow.value)

	def btn_blue(self):
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_blue.value)

	def btn_redlong(self):
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_redlong.value)

	def btn_greenlong(self):
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_greenlong.value)

	def btn_yellowlong(self):
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_yellowlong.value)

	def btn_bluelong(self):
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_bluelong.value)

	def btn_radio(self):
		self._callButton(config.movielist.btn_radio.value)

	def btn_tv(self):
		self._callButton(config.movielist.btn_tv.value)

	def btn_text(self):
		self._callButton(config.movielist.btn_text.value)

	def btn_F1(self):
		self._callButton(config.movielist.btn_F1.value)

	def btn_F2(self):
		self._callButton(config.movielist.btn_F2.value)

	def btn_F3(self):
		self._callButton(config.movielist.btn_F3.value)

	def keyUp(self):
		if self["list"].getCurrentIndex() < 1:
			self["list"].moveToLast()
		else:
			self["list"].moveUp()

	def keyDown(self):
		if self["list"].getCurrentIndex() == len(self["list"]) - 1:
			self["list"].moveToFirst()
		else:
			self["list"].moveDown()

	def moveToFirstOrFirstFile(self):
		if self.list.getCurrentIndex() <= self.list.firstFileEntry:  # Selection above or on first movie.
			if self.list.getCurrentIndex() < 1:
				self.list.moveToLast()
			else:
				self.list.moveToFirst()
		else:
			self.list.moveToFirstMovie()

	def moveToLastOrFirstFile(self):
		if self.list.getCurrentIndex() >= self.list.firstFileEntry or self.list.firstFileEntry == len(self.list):  # Selection below or on first movie or no files.
			if self.list.getCurrentIndex() == len(self.list) - 1:
				self.list.moveToFirst()
			else:
				self.list.moveToLast()
		else:
			self.list.moveToFirstMovie()

	def keyNumberGlobal(self, number):
		charstr = self.numericalTextInput.getKey(number)
		if len(charstr) == 1:
			self.list.moveToChar(charstr[0], self["chosenletter"])

	def keyAsciiCode(self):
		charstr = chr(getPrevAsciiCode())
		if len(charstr) == 1:
			self.list.moveToString(charstr[0], self["chosenletter"])

	def isItemPlayable(self, index):
		item = self.list.getItem(index)
		if item:
			path = item.getPath()
			if not item.flags & eServiceReference.mustDescent:
				ext = splitext(path)[1].lower()
				if ext in IMAGE_EXTENSIONS:
					return False
				else:
					return True
		return False

	def goToPlayingService(self):
		service = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if service:
			path = service.getPath()
			if path:
				path = split(normpath(path))[0]
				if not path.endswith("/"):
					path += "/"
				self.gotFilename(path, selItem=service)
				return True
		return False

	def playNext(self):
		if self.list.playInBackground:
			if self.list.moveTo(self.list.playInBackground):
				if self.isItemPlayable(self.list.getCurrentIndex() + 1):
					self.list.moveDown()
					self.callLater(self.preview)
			else:
				self.playGoTo = 1
				self.goToPlayingService()
		else:
			self.preview()

	def playPrev(self):
		if self.list.playInBackground:
			if self.list.moveTo(self.list.playInBackground):
				if self.isItemPlayable(self.list.getCurrentIndex() - 1):
					self.list.moveUp()
					self.callLater(self.preview)
			else:
				self.playGoTo = -1
				self.goToPlayingService()
		else:
			current = self.getCurrent()
			if current is not None:
				if self["list"].getCurrentIndex() > 0:
					path = current.getPath()
					path = abspath(join(path, pardir))
					path = abspath(join(path, pardir))
					self.gotFilename(path)

	def __onClose(self):
		try:
			NavigationInstance.instance.RecordTimer.on_state_change.remove(self.list.updateRecordings)
		except Exception as err:
			print(f"[MovieSelection] Error: Failed to unsubscribe '{str(err)}'!")

	def createSummary(self):
		return MovieSelectionSummary

	def updateDescription(self):
		if self.settings["description"] == MovieList.SHOW_DESCRIPTION:
			self["DescriptionBorder"].show()
			self["list"].instance.resize(eSize(self.listWidth, self.listHeight - self["DescriptionBorder"].instance.size().height()))
		else:
			self["Service"].newService(None)
			self["DescriptionBorder"].hide()
			self["list"].instance.resize(eSize(self.listWidth, self.listHeight))

	def pauseService(self):  # Called when pressing Power button (go to standby).
		self.playbackStop()
		self.session.nav.stopService()

	def unPauseService(self):  # When returning from standby. It might have been a while, so reload the list.
		self.reloadList()

	def can_move(self, item):
		return canMove(item) if item else False

	def can_delete(self, item):
		try:
			if not item:
				return False
			return canDelete(item) or isTrashFolder(item[0])
		except Exception:
			return False

	def can_default(self, item):  # Returns whether item is a regular file.
		return isSimpleFile(item)

	def can_sort(self, item):
		return True

	def can_preview(self, item):
		return isSimpleFile(item)

	def _updateButtonTexts(self):
		for button in ("red", "green", "yellow", "blue"):
			self[f"key_{button}"].setText(userDefinedActions[userDefinedButtons[button].value])

	def updateButtons(self):
		item = self.getCurrentSelection()
		for button in ("red", "green", "yellow", "blue"):
			action = userDefinedButtons[button].value
			if action.startswith("@"):
				check = self.can_default
			elif action.startswith("/"):
				check = self.can_gohome
			else:
				try:
					check = getattr(self, f"can_{action}")
				except Exception:
					check = self.can_default
			self[f"key_{button}"].setText(userDefinedActions[userDefinedButtons[button].value] if check(item) else "")

	def showEventInformation(self):
		from Screens.EventView import EventViewSimple
		from ServiceReference import ServiceReference
		evt = self["list"].getCurrentEvent()
		if evt:
			self.session.open(EventViewSimple, evt, ServiceReference(self.getCurrent()))

	def saveListsize(self):
		listsize = self["list"].instance.size()
		self.listWidth = listsize.width()
		self.listHeight = listsize.height()
		self.updateDescription()

	def FilePlaying(self):
		if self.session.nav.getCurrentlyPlayingServiceReference() and ":0:/" in self.session.nav.getCurrentlyPlayingServiceReference().toString():
			self.list.playInForeground = self.session.nav.getCurrentlyPlayingServiceReference()
		else:
			self.list.playInForeground = None
		self.filePlayingTimer.stop()

	def onFirstTimeShown(self):
		self.filePlayingTimer.start(100)
		self.onShown.remove(self.onFirstTimeShown)  # Just once, not after returning etc.
		self.show()
		self.reloadList(self.selectedmovie, home=True)
		del self.selectedmovie
		if config.movielist.show_live_tv_in_movielist.value:
			self.LivePlayTimer.start(100)

	def hidewaitingtext(self):
		self.hidewaitingTimer.stop()
		self["waitingtext"].hide()

	def LivePlay(self):
		if self.session.nav.getCurrentlyPlayingServiceReference():
			if ":0:/" not in self.session.nav.getCurrentlyPlayingServiceReference().toString():
				config.movielist.curentlyplayingservice.setValue(self.session.nav.getCurrentlyPlayingServiceReference().toString())
		checkplaying = self.session.nav.getCurrentlyPlayingServiceReference()
		if checkplaying:
			checkplaying = checkplaying.toString()
		if checkplaying is None or (config.movielist.curentlyplayingservice.value != checkplaying and ":0:/" not in self.session.nav.getCurrentlyPlayingServiceReference().toString()):
			self.session.nav.playService(eServiceReference(config.movielist.curentlyplayingservice.value))
		self.LivePlayTimer.stop()

	def getCurrent(self):  # Returns selected serviceref (may be None).
		return self["list"].getCurrent()

	def getCurrentSelection(self):  # Returns None or (serviceref, info, begin, len).
		return self["list"].l.getCurrentSelection()

	def playAsDVD(self, path):
		try:
			from Screens import DVD
			if path.endswith("VIDEO_TS/"):  # Strip away VIDEO_TS/ part.
				path = split(path.rstrip("/"))[0]
			self.session.open(DVD.DVDPlayer, dvd_filelist=[path])
			return True
		except Exception as err:
			print(f"[MovieSelection] Error: DVD Player not installed!  ({str(err)})")

	def __serviceStarted(self):
		if not self.list.playInBackground or not self.list.playInForeground:
			return
		ref = self.session.nav.getCurrentService()
		cue = ref.cueSheet()
		if not cue:
			return
		cue.setCutListEnable(2)  # Disable writing the stop position.
		cuts = cue.getCutList()  # Find "resume" position.
		if not cuts:
			return
		for (pts, what) in cuts:
			if what == 3:
				last = pts
				break
		else:  # No resume, jump to start of program (first marker).
			last = cuts[0][0]
		self.doSeekTo = last
		self.callLater(self.doSeek)

	def doSeek(self, pts=None):
		if pts is None:
			pts = self.doSeekTo
		seekable = self.getSeek()
		if seekable is None:
			return
		seekable.seekTo(pts)

	def getSeek(self):
		service = self.session.nav.getCurrentService()
		if service is None:
			return None
		seek = service.seek()
		if seek is None or not seek.isCurrentlySeekable():
			return None
		return seek

	def callLater(self, function):
		self.previewTimer = eTimer()
		self.previewTimer.callback.append(function)
		self.previewTimer.start(10, True)

	def __evEOF(self):
		playInBackground = self.list.playInBackground
		playInForeground = self.list.playInForeground
		if not playInBackground:  # TODO: What if playInForeground = True?
			print("[MovieSelection] Not playing anything in background.")
			return
		if not playInForeground:
			print("[MovieSelection] Not playing anything in foreground.")
			return
		current = self.getCurrent()
		self.session.nav.stopService()
		self.list.playInBackground = None
		self.list.playInForeground = None
		if config.movielist.play_audio_internal.value:
			index = self.list.findService(playInBackground)
			if index is None:
				return  # Not found?
			nextItem = self.list.getItem(index + 1)
			if not nextItem:
				return
			path = nextItem.getPath()
			ext = splitext(path)[1].lower()
			print(f"[MovieSelection] Next up '{path}'.")
			if ext in AUDIO_EXTENSIONS:
				self.nextInBackground = next
				self.callLater(self.preview)
				self["list"].moveToIndex(index + 1)
		if config.movielist.show_live_tv_in_movielist.value:
			self.LivePlayTimer.start(100)

	def preview(self):
		current = self.getCurrent()
		if current is not None:
			path = current.getPath()
			if current.flags & eServiceReference.mustDescent:
				self.gotFilename(path)
			else:
				Screens.InfoBar.InfoBar.instance.checkTimeshiftRunning(self.previewCheckTimeshiftCallback)

	def startPreview(self):
		if self.nextInBackground is not None:
			current = self.nextInBackground
			self.nextInBackground = None
		else:
			current = self.getCurrent()
		playInBackground = self.list.playInBackground
		playInForeground = self.list.playInForeground
		if playInBackground:
			self.list.playInBackground = None
			from Screens.InfoBar import MoviePlayer
			MoviePlayerInstance = MoviePlayer.instance
			if MoviePlayerInstance is not None:
				from Screens.InfoBarGenerics import setResumePoint
				setResumePoint(MoviePlayer.instance.session)
			self.session.nav.stopService()
			if playInBackground != current:
				self.callLater(self.preview)  # Come back to play the new one.
		elif playInForeground:
			self.playingInForeground = playInForeground
			self.list.playInForeground = None
			from Screens.InfoBar import MoviePlayer
			MoviePlayerInstance = MoviePlayer.instance
			if MoviePlayerInstance is not None:
				from Screens.InfoBarGenerics import setResumePoint
				setResumePoint(MoviePlayer.instance.session)
			self.session.nav.stopService()
			if playInForeground != current:
				self.callLater(self.preview)
		else:
			self.list.playInBackground = current
			if current.type == 4116:  # Check if MerlinMusicPlayer is installed and merlinmp3player.so is running so we need the right id to play now the mp3-file.
				path = current.getPath()
				service = eServiceReference(4097, 0, path)
				self.session.nav.playService(service)
			else:
				self.session.nav.playService(current)

	def previewCheckTimeshiftCallback(self, answer):
		if answer:
			self.startPreview()

	def seekRelative(self, direction, amount):
		if self.list.playInBackground or self.list.playInForeground:
			seekable = self.getSeek()
			if seekable is None:
				return
			seekable.seekRelative(direction, amount)

	def playbackStop(self):
		if self.list.playInBackground:
			self.list.playInBackground = None
			from Screens.InfoBar import MoviePlayer
			MoviePlayerInstance = MoviePlayer.instance
			if MoviePlayerInstance is not None:
				from Screens.InfoBarGenerics import setResumePoint
				setResumePoint(MoviePlayer.instance.session)
			self.session.nav.stopService()
			if config.movielist.show_live_tv_in_movielist.value:
				self.LivePlayTimer.start(100)
			self.filePlayingTimer.start(100)
			return
		elif self.list.playInForeground:
			from Screens.InfoBar import MoviePlayer
			MoviePlayerInstance = MoviePlayer.instance
			if MoviePlayerInstance is not None:
				from Screens.InfoBarGenerics import setResumePoint
				setResumePoint(MoviePlayer.instance.session)
				MoviePlayerInstance.close()
			self.session.nav.stopService()
			if config.movielist.show_live_tv_in_movielist.value:
				self.LivePlayTimer.start(100)
			self.filePlayingTimer.start(100)

	def itemSelected(self, answer=True):
		current = self.getCurrent()
		if current is not None:
			path = current.getPath()
			if current.flags & eServiceReference.mustDescent:
				if path.endswith("VIDEO_TS/") or exists(join(path, "VIDEO_TS.IFO")):  # Force a DVD extention.
					Screens.InfoBar.InfoBar.instance.checkTimeshiftRunning(boundFunction(self.itemSelectedCheckTimeshiftCallback, ".iso", path))
					return
				self.gotFilename(path)
			else:
				ext = splitext(path)[1].lower()
				if config.movielist.play_audio_internal.value and (ext in AUDIO_EXTENSIONS):
					self.preview()
					return
				if self.list.playInBackground:
					self.session.nav.stopService()  # Stop preview, come back later.
					self.list.playInBackground = None
					self.callLater(self.itemSelected)
					return
				if ext in IMAGE_EXTENSIONS:
					try:
						from Plugins.Extensions.PicturePlayer import ui
						filelist = []  # Build the list for the PicturePlayer UI.
						index = 0
						for item in self.list.list:
							p = item[0].getPath()
							if p == path:
								index = len(filelist)
							if splitext(p)[1].lower() in IMAGE_EXTENSIONS:
								filelist.append(((p, False), None))
						self.session.open(ui.Pic_Full_View, filelist, index, path)
					except Exception as err:
						print(f"[MovieSelection] Error: Cannot display!  ({str(err)})")
					return
				Screens.InfoBar.InfoBar.instance.checkTimeshiftRunning(boundFunction(self.itemSelectedCheckTimeshiftCallback, ext, path))

	def itemSelectedCheckTimeshiftCallback(self, ext, path, answer):
		if answer:
			if ext in DVD_EXTENSIONS and self.playAsDVD(path):
				return
			self.movieSelected()

	def movieSelected(self):  # Note: DVDBurn overrides this method, hence the itemSelected indirection.
		current = self.getCurrent()
		if current is not None:
			self.saveconfig()
			self.close(current)

	def doContext(self):
		current = self.getCurrent() or None
		self.session.openWithCallback(self.doneContext, MovieContextMenu, self, current)

	def doneContext(self, action):
		if action is not None:
			action()

	def saveLocalSettings(self):
		try:
			path = join(config.movielist.last_videodir.value, ".e2settings.pkl")
			with open(path, "wb") as fd:
				dump(self.settings, fd)
		except OSError as err:
			print(f"[MovieSelection] Error {err.errno}: Failed to save settings to '{path}'!  ({err.strerror})")
		# Also set config items, in case the user has a read-only disk.
		config.movielist.moviesort.value = self.settings["moviesort"]
		config.movielist.description.value = self.settings["description"]
		config.usage.on_movie_eof.value = self.settings["movieoff"]
		# Save moviesort and movieeof values for using by hotkeys.
		# config.movielist.moviesort.save()
		config.usage.on_movie_eof.save()

	def loadLocalSettings(self):
		"Load settings, called when entering a directory"
		if config.movielist.settings_per_directory.value:
			try:
				path = join(config.movielist.last_videodir.value, ".e2settings.pkl")
				with open(path, "rb") as fd:
					updates = load(fd)
				self.applyConfigSettings(updates)
			except OSError as err:  # Ignore fail to open errors.
				updates = {
					"moviesort": config.movielist.moviesort.default,
					"description": config.movielist.description.default,
					"movieoff": config.usage.on_movie_eof.default
				}
				self.applyConfigSettings(updates)
			except Exception as err:
				print(f"[MovieSelection] Error: Failed to load settings from '{path}'!  ({str(err)})")
		else:
			updates = {
				"moviesort": config.movielist.moviesort.value,
				"description": config.movielist.description.value,
				"movieoff": config.usage.on_movie_eof.value
				}
			self.applyConfigSettings(updates)

	def applyConfigSettings(self, updates):
		needUpdate = ("description" in updates) and (updates["description"] != self.settings["description"])
		self.settings.update(updates)
		if needUpdate:
			self["list"].setDescriptionState(self.settings["description"])
			self.updateDescription()
		if self.settings["moviesort"] != self["list"].sort_type:
			self["list"].setSortType(int(self.settings["moviesort"]))
			needUpdate = True
		if self.settings["movieoff"] != self.movieOff:
			self.movieOff = self.settings["movieoff"]
			needUpdate = True
		config.movielist.moviesort.value = self.settings["moviesort"]
		config.movielist.description.value = self.settings["description"]
		config.usage.on_movie_eof.value = self.settings["movieoff"]
		return needUpdate

	def sortBy(self, newType):
		print(f"[MovieSelection] Sort by '{newType}'.")
		self.settings["moviesort"] = newType
		self.saveLocalSettings()
		self.setSortType(newType)
		self.reloadList()

	def showDescription(self, newType):
		self.settings["description"] = newType
		self.saveLocalSettings()
		self.setDescriptionState(newType)
		self.updateDescription()

	def abort(self):
		global playlist
		del playlist[:]
		if self.list.playInBackground:
			self.list.playInBackground = None
			self.session.nav.stopService()
			self.callLater(self.abort)
			return
		if self.playingInForeground:
			self.list.playInForeground = self.playingInForeground
			self.session.nav.stopService()
			self.close(self.playingInForeground)
			return
		self.saveconfig()
		self.close(None)

	def saveconfig(self):
		config.movielist.last_selected_tags.value = self.selected_tags if self.selected_tags else []

	def configure(self):
		self.session.openWithCallback(self.configureDone, MovieSelectionSetup)

	def configureDone(self, result):
		if result is True:
			self.applyConfigSettings({
				"moviesort": config.movielist.moviesort.value,
				"description": config.movielist.description.value,
				"movieoff": config.usage.on_movie_eof.value
			})
			self.saveLocalSettings()
			self._updateButtonTexts()
			self["list"].setItemsPerPage()
			self["list"].setFontsize()
			self.reloadList()
			self.updateDescription()

	def can_sortby(self, item):
		return True

	def do_sortby(self):
		self.selectSortby()

	def selectSortby(self):
		menu = []
		used = 0
		for index, x in enumerate(l_moviesort):
			if int(x[0]) == int(config.movielist.moviesort.value):
				used = index
			menu.append((_(x[1]), x[0], str(index)))
		self.session.openWithCallback(self.sortbyMenuCallback, ChoiceBox, title=_("Sort list:"), list=menu, selection=used)

	def getPixmapSortIndex(self, which):
		index = int(which)
		if index == MovieList.SORT_ALPHA_DATE_OLDEST_FIRST:
			index = MovieList.SORT_ALPHANUMERIC
		elif index == MovieList.SORT_ALPHAREV_DATE_NEWEST_FIRST:
			index = MovieList.SORT_ALPHANUMERIC_REVERSE
		return index - 1

	def sortbyMenuCallback(self, choice):
		if choice is None:
			return
		self.sortBy(int(choice[1]))
		self["movie_sort"].setPixmapNum(self.getPixmapSortIndex(choice[1]))

	def getTagDescription(self, tag):  # TODO: Access the tag database.
		return tag

	def updateTags(self):  # Get a list of tags available in this list.
		self.tags = self["list"].tags

	def setDescriptionState(self, val):
		self["list"].setDescriptionState(val)

	def setSortType(self, type):
		self["list"].setSortType(type)

	def setCurrentRef(self, path):
		self.current_ref = eServiceReference(eServiceReference.idFile, eServiceReference.noFlags, eServiceReferenceFS.directory)
		self.current_ref.setPath(path)
		self.current_ref.setName("16384:jpg 16384:png 16384:gif 16384:bmp")  # Magic: This sets extra things to show.

	def reloadList(self, sel=None, home=False):
		self.reload_sel = sel
		self.reload_home = home
		self["waitingtext"].visible = True
		self.pathselectEnabled = False
		self.callLater(self.reloadWithDelay)

	def reloadWithDelay(self):
		if not isdir(config.movielist.last_videodir.value):
			path = defaultMoviePath()
			config.movielist.last_videodir.value = path
			config.movielist.last_videodir.save()
			self.setCurrentRef(path)
			self["freeDiskSpace"].path = path
			self["TrashcanSize"].update(path)
		else:
			self["TrashcanSize"].update(config.movielist.last_videodir.value)
		if self.reload_sel is None:
			self.reload_sel = self.getCurrent()
		if config.usage.movielist_trashcan.value and access(config.movielist.last_videodir.value, W_OK):
			trash = createTrashcan(config.movielist.last_videodir.value)
		self.loadLocalSettings()
		self["list"].reload(self.current_ref, self.selected_tags)
		self.updateTags()
		title = ""
		if config.usage.setup_level.index >= 2:  # Expert+.
			title += config.movielist.last_videodir.value
		if self.selected_tags:
			title += " - {",".join(self.selected_tags)}"
		self.setTitle(title)
		self.displayMovieOffStatus()
		self.displaySortStatus()
		if not (self.reload_sel and self["list"].moveTo(self.reload_sel)) and self.reload_home:
			self["list"].moveToFirstMovie()
		self["freeDiskSpace"].update()
		self["waitingtext"].visible = False
		self.createPlaylist()
		if self.playGoTo and self.isItemPlayable(self.list.getCurrentIndex() + 1):
			if self.playGoTo > 0:
				self.list.moveDown()
			else:
				self.list.moveUp()
			self.playGoTo = None
			self.callLater(self.preview)
		self.callLater(self.enablePathSelect)

	def enablePathSelect(self):
		self.pathselectEnabled = True

	def doPathSelect(self):
		if self.pathselectEnabled:
			self.session.openWithCallback(self.gotFilename, MovieLocationBox, _("Please select the movie path..."), config.movielist.last_videodir.value)

	def gotFilename(self, res, selItem=None):
		if not res:
			return
		res = join(res, "")  # The service reference must end with "/".
		currentDir = config.movielist.last_videodir.value
		if res != currentDir:
			if isdir(res):
				config.movielist.last_videodir.value = res
				config.movielist.last_videodir.save()
				self.loadLocalSettings()
				self.setCurrentRef(res)
				self["freeDiskSpace"].path = res
				self["TrashcanSize"].update(res)
				if selItem:
					self.reloadList(home=True, sel=selItem)
				else:
					ref = eServiceReference(eServiceReference.idFile, eServiceReference.noFlags, eServiceReferenceFS.directory)
					ref.setPath(currentDir)
					self.reloadList(home=True, sel=ref)
			else:
				self.session.open(MessageBox, _("Directory %s does not exist.") % res, type=MessageBox.TYPE_ERROR, timeout=5, windowTitle=self.getTitle())

	def showAll(self):
		self.selected_tags_ele = None
		self.selected_tags = None
		self.saveconfig()
		self.reloadList(home=True)

	def showTagsN(self, tagele):
		if not self.tags:
			self.showTagWarning()
		elif not tagele or (self.selected_tags and tagele.value in self.selected_tags) or tagele.value not in self.tags:
			self.showTagsMenu(tagele)
		else:
			self.selected_tags_ele = tagele
			self.selected_tags = self.tags[tagele.value]
			self.reloadList(home=True)

	def showTagsFirst(self):
		self.showTagsN(config.movielist.first_tags)

	def showTagsSecond(self):
		self.showTagsN(config.movielist.second_tags)

	def can_tags(self, item):
		return self.tags

	def do_tags(self):
		self.showTagsN(None)

	def tagChosen(self, tag):
		if tag is not None:
			if tag[1] is None:  # All.
				self.showAll()
				return
			self.selected_tags = self.tags[tag[0]]  # TODO: Some error checking maybe, don't wanna crash on KeyError.
			if self.selected_tags_ele:
				self.selected_tags_ele.value = tag[0]
				self.selected_tags_ele.save()
			self.saveconfig()
			self.reloadList(home=True)

	def showTagsMenu(self, tagele):
		self.selected_tags_ele = tagele
		lst = [(_("show all tags"), None)] + [(tag, self.getTagDescription(tag)) for tag in sorted(self.tags)]
		self.session.openWithCallback(self.tagChosen, ChoiceBox, title=_("Please select tag to filter..."), list=lst, skin_name="MovieListTags")

	def showTagWarning(self):
		self.session.open(MessageBox, _("No tags are set on these movies."), MessageBox.TYPE_ERROR, windowTitle=self.getTitle())

	def selectMovieLocation(self, title, callback):
		bookmarks = [(f"({_("Other")}...)", None)]
		buildMovieLocationList(bookmarks)
		self.onMovieSelected = callback
		self.movieSelectTitle = title
		self.session.openWithCallback(self.gotMovieLocation, ChoiceBox, title=title, list=bookmarks)

	def gotMovieLocation(self, choice):
		if not choice:  # Canceled.
			self.onMovieSelected(None)
			del self.onMovieSelected
			return
		if isinstance(choice, tuple):
			if choice[1] is None:  # Display full browser, which returns string.
				self.session.openWithCallback(self.gotMovieLocation, MovieLocationBox, self.movieSelectTitle, config.movielist.last_videodir.value)
				return
			choice = choice[1]
		choice = normpath(choice)
		self.rememberMovieLocation(choice)
		self.onMovieSelected(choice)
		del self.onMovieSelected

	def rememberMovieLocation(self, where):
		if where in last_selected_dest:
			last_selected_dest.remove(where)
		last_selected_dest.insert(0, where)
		if len(last_selected_dest) > 5:
			del last_selected_dest[-1]

	def can_bookmarks(self, item):
		return True

	def do_bookmarks(self):
		self.selectMovieLocation(title=_("Please select the movie path..."), callback=self.gotFilename)

	def can_addbookmark(self, item):
		return True

	def exist_bookmark(self):
		path = config.movielist.last_videodir.value
		if path in config.movielist.videodirs.value:
			return True
		return False

	def do_addbookmark(self):
		path = config.movielist.last_videodir.value
		if path in config.movielist.videodirs.value:
			if len(path) > 40:
				path = f"...{path[-40:]}"
			self.session.openWithCallback(self.removeBookmark, MessageBox, _("Do you really want to remove your bookmark for '%s'?") % path, windowTitle=self.getTitle())
		else:
			config.movielist.videodirs.value += [path]
			config.movielist.videodirs.save()

	def removeBookmark(self, yes):
		if not yes:
			return
		path = config.movielist.last_videodir.value
		bookmarks = config.movielist.videodirs.value
		bookmarks.remove(path)
		config.movielist.videodirs.value = bookmarks
		config.movielist.videodirs.save()

	def can_createdir(self, item):
		return True

	def do_createdir(self):
		self.session.openWithCallback(self.createDirCallback, VirtualKeyBoard, title=_("Please enter a name for the new directory:"), text="")

	def createDirCallback(self, name):
		if not name:
			return
		msg = None
		try:
			path = join(config.movielist.last_videodir.value, name)
			mkdir(path)
			path = join(path, "")
			ref = eServiceReference(eServiceReference.idFile, eServiceReference.noFlags, eServiceReferenceFS.directory)
			ref.setPath(path)
			self.reloadList(sel=ref)
		except OSError as err:
			print(f"[MovieSelection] Error {err.errno}: {err.strerror}!")
			if err.errno == 17:
				msg = _("Error: The path '%s' already exists!") % name
			else:
				msg = f"{_("Error")}\n{str(err)}"
		except Exception as err:
			print("[MovieSelection] Unexpected error: '{str(err)}'!")
			msg = f"{_("Error")}\n{str(err)}"
		if msg:
			self.session.open(MessageBox, msg, type=MessageBox.TYPE_ERROR, timeout=5, windowTitle=self.getTitle())

	def do_tageditor(self):
		item = self.getCurrentSelection()
		if not isFolder(item):
			self.session.openWithCallback(self.tageditorCallback, TagEditor, service=item[0])

	def tageditorCallback(self, tags):
		return

	def do_rename(self):
		item = self.getCurrentSelection()
		if not canMove(item):
			return
		self.extension = ""
		if isFolder(item):
			p = split(item[0].getPath())
			if not p[1]:  # If path ends in "/", p is blank.
				p = split(p[0])
			name = p[1]
		else:
			info = item[1]
			name = info.getName(item[0])
			full_name = split(item[0].getPath())[1]
			if full_name == name:  # Split extensions for files without metafile.
				name, self.extension = splitext(name)
		self.session.openWithCallback(self.renameCallback, VirtualKeyBoard,
			title=_("Rename"),
			text=name)

	def do_decode(self):
		from ServiceReference import ServiceReference
		item = self.getCurrentSelection()
		info = item[1]
		serviceref = ServiceReference(None, reftype=eServiceReference.idDVB, path=item[0].getPath())
		name = f"{info.getName(item[0])} - decoded"
		description = info.getInfoString(item[0], iServiceInformation.sDescription)
		begin = int(time())
		recording = RecordTimerEntry(serviceref, begin, begin + 3600, name, description, 0, dirname=preferredTimerPath())
		recording.dontSave = True
		recording.autoincrease = True
		recording.setAutoincreaseEnd()
		self.session.nav.RecordTimer.record(recording, ignoreTSC=True)

	def renameCallback(self, name):
		if not name:
			return
		name = name.strip()
		item = self.getCurrentSelection()
		if item and item[0]:
			try:
				path = item[0].getPath().rstrip("/")
				meta = f"{path}.meta"
				if isfile(meta):
					metafile = open(meta, "r+")
					sid = metafile.readline()
					oldtitle = metafile.readline()
					rest = metafile.read()
					metafile.seek(0)
					metafile.write(f"{sid}{name}\n{rest}")
					metafile.truncate()
					metafile.close()
					index = self.list.getCurrentIndex()
					info = self.list.list[index]
					if hasattr(info[3], "txt"):
						info[3].txt = name
					else:
						self.list.invalidateCurrentItem()
					return
				pathname, filename = split(path)
				newpath = join(pathname, name)
				msg = None
				print(f"[MovieSelection] Rename '{path}' to '{newpath}'.")
				rename(path, newpath)
				ref = eServiceReference(eServiceReference.idFile, eServiceReference.noFlags, eServiceReferenceFS.directory)
				ref.setPath(newpath)
				self.reloadList(sel=ref)
			except OSError as err:
				print(f"[MovieSelection] Error {err.errno}: {err.strerror}!")
				if err.errno == 17:
					msg = _("Error: The path '%s' already exists!") % name
				else:
					msg = f"{_("Error")}\n{str(err)}"
			except Exception as err:
				import traceback
				print("[MovieSelection] Unexpected error: {str(err)}")
				traceback.print_exc()
				msg = f"{_("Error")}\n{str(err)}"
			if msg:
				self.session.open(MessageBox, msg, type=MessageBox.TYPE_ERROR, timeout=5, windowTitle=self.getTitle())

	def do_reset(self):
		current = self.getCurrent()
		if current:
			resetMoviePlayState(f"{current.getPath()}.cuts", current)
			self["list"].invalidateCurrentItem()  # Trigger repaint.

	def do_move(self):
		item = self.getCurrentSelection()
		if canMove(item):
			current = item[0]
			info = item[1]
			if info is None:  # Special case.
				return
			name = info and info.getName(current) or _("this recording")
			path = normpath(current.getPath())
			# Show a more limited list of destinations, no point in showing mount points.
			title = f"{_("Select destination for:")} {name}"
			bookmarks = [(f"({_("Other")}...)", None)]
			inlist = []
			try:  # Sub directories.
				base = split(path)[0]
				for fn in listdir(base):
					if not fn.startswith("."):  # Skip hidden things.
						d = join(base, fn)
						if isdir(d) and (d not in inlist):
							bookmarks.append((fn, d))
							inlist.append(d)
			except Exception as err:
				print(f"[MovieSelection] Error: {str(err)}!")
			for d in last_selected_dest:  # Last favorites.
				if d not in inlist:
					bookmarks.append((d, d))
			for d in config.movielist.videodirs.value:  # Other favorites.
				d = normpath(d)
				bookmarks.append((d, d))
				inlist.append(d)
			for p in harddiskmanager.getMountedPartitions():
				d = normpath(p.mountpoint)
				if d not in inlist:
					bookmarks.append((p.description, d))
					inlist.append(d)
			self.onMovieSelected = self.gotMoveMovieDest
			self.movieSelectTitle = title
			self.session.openWithCallback(self.gotMovieLocation, ChoiceBox, title=title, list=bookmarks)

	def gotMoveMovieDest(self, choice):
		if not choice:
			return
		dest = normpath(choice)
		try:
			item = self.getCurrentSelection()
			current = item[0]
			if item[1] is None:
				name = None
			else:
				name = item[1].getName(current)
			moveServiceFiles(current, dest, name)
			self["list"].removeService(current)
		except Exception as e:
			self.session.open(MessageBox, str(e), MessageBox.TYPE_ERROR, windowTitle=self.getTitle())

	def do_copy(self):
		item = self.getCurrentSelection()
		if canCopy(item):
			current = item[0]
			info = item[1]
			if info is None:  # Special case.
				return
			name = info and info.getName(current) or _("this recording")
			self.selectMovieLocation(title=f"{_("Select copy destination for:")} {name}", callback=self.gotCopyMovieDest)

	def gotCopyMovieDest(self, choice):
		if not choice:
			return
		dest = normpath(choice)
		try:
			item = self.getCurrentSelection()
			current = item[0]
			name = None if item[1] is None else item[1].getName(current)
			copyServiceFiles(current, dest, name)
		except Exception as err:
			self.session.open(MessageBox, str(err), MessageBox.TYPE_ERROR, windowTitle=self.getTitle())

	def stopTimer(self, timer):
		if timer.isRunning():
			if timer.repeated:
				timer.enable()
				timer.processRepeated(findRunningEvent=False)
				self.session.nav.RecordTimer.doActivate(timer)
			else:
				timer.afterEvent = AFTEREVENT.NONE
				NavigationInstance.instance.RecordTimer.removeEntry(timer)

	def onTimerChoice(self, choice):
		if isinstance(choice, tuple) and choice[1]:
			choice, timer = choice[1]
			if not choice:  # Cancel.
				return
			if "s" in choice:
				self.stopTimer(timer)
			if "d" in choice:
				self.delete(True)

	def do_delete(self):
		self.delete()

	def delete(self, *args):
		if args and (not args[0]):  # Canceled by user (passing any arg means it's a dialog return).
			return
		item = self.getCurrentSelection()
		current = item[0]
		info = item[1]
		cur_path = realpath(current.getPath())
		if not exists(cur_path):  # File does not exist.
			return
		st = stat(cur_path)
		name = info and info.getName(current) or _("this recording")
		are_you_sure = ""
		pathtest = info and info.getName(current)
		if not pathtest:
			return
		if item and isTrashFolder(item[0]):  # Red button to empty trashcan.
			self.purgeAll()
			return
		if current.flags & eServiceReference.mustDescent:
			files = 0
			subdirs = 0
			if TRASHCAN not in cur_path and config.usage.movielist_trashcan.value:
				if isFolder(item):
					are_you_sure = _("Do you really want to move to trashcan ?")
				else:
					args = True
				if args:
					trash = createTrashcan(cur_path)
					if trash:
						moveServiceFiles(current, trash, name, allowCopy=True)
						self["list"].removeService(current)
						self.showActionFeedback(_("Deleted") + " " + name)
						return
					else:
						msg = _("Cannot move to trash can") + "\n"
						are_you_sure = _("Do you really want to delete %s ?") % name
				for fn in listdir(cur_path):
					if (fn != ".") and (fn != ".."):
						ffn = join(cur_path, fn)
						if isdir(ffn):
							subdirs += 1
						else:
							files += 1
				if files or subdirs:
					folder_filename = split(split(name)[0])[1]
					self.session.openWithCallback(self.delete, MessageBox, _("'%s' contains %d file(s) and %d sub-directories.\n") % (folder_filename, files, subdirs) + are_you_sure, windowTitle=self.getTitle())
					return
				else:
					self.session.openWithCallback(self.delete, MessageBox, are_you_sure, windowTitle=self.getTitle())
					return
			else:
				if TRASHCAN in cur_path:
					are_you_sure = _("Do you really want to permanently remove from trash can ?")
				else:
					are_you_sure = _("Do you really want to delete ?")
				if args:
					try:
						msg = ""
						deleteFiles(cur_path, name)
						self["list"].removeService(current)
						self.showActionFeedback(f"{_("Deleted")} {name}")
						return
					except Exception as err:
						print(f"[MovieSelection] Error: Weird error moving to trash!  ({str(err)})")
						msg = f"{_("Cannot delete file")}\n{str(err)}\n"
						return
				for fn in listdir(cur_path):
					if (fn != ".") and (fn != ".."):
						ffn = join(cur_path, fn)
						if isdir(ffn):
							subdirs += 1
						else:
							files += 1
				if files or subdirs:
					folder_filename = split(split(name)[0])[1]
					self.session.openWithCallback(self.delete, MessageBox, _("'%s' contains %d file(s) and %d sub-directories.\n") % (folder_filename, files, subdirs) + are_you_sure, windowTitle=self.getTitle())
				else:
					try:
						rmdir(cur_path)
					except OSError as err:
						print(f"[MovieSelection] Error {err.errno}: Failed delete '{cur_path}'!  ({err.strerror})")
						self.session.open(MessageBox, f"{_("Delete failed!")}\n{str(err)}", MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
					else:
						self["list"].removeService(current)
						self.showActionFeedback(f"{_("Deleted")} {name}")
		else:
			if not args:
				rec_filename = split(current.getPath())[1]
				if rec_filename.endswith(".ts"):
					rec_filename = rec_filename[:-3]
				elif rec_filename.endswith(".stream"):
					rec_filename = rec_filename[:-7]
				for timer in NavigationInstance.instance.RecordTimer.timer_list:
					if timer.isRunning() and not timer.justplay and rec_filename in timer.Filename:
						choices = [
							(_("Cancel"), None),
							(_("Stop recording"), ("s", timer)),
							(_("Stop recording and delete"), ("sd", timer))
						]
						self.session.openWithCallback(self.onTimerChoice, ChoiceBox, title=f"{_("Recording in progress!")}\n{name}", list=choices)
						return
				if time() - st.st_mtime < 5 and not args:
					are_you_sure = _("Do you really want to delete ?")
					self.session.openWithCallback(self.delete, MessageBox, _("File appears to be busy.\n") + are_you_sure, windowTitle=self.getTitle())
					return
			if TRASHCAN not in cur_path and config.usage.movielist_trashcan.value:
				trash = createTrashcan(cur_path)
				if trash:
					moveServiceFiles(current, trash, name, allowCopy=True)
					self["list"].removeService(current)
					from Screens.InfoBarGenerics import delResumePoint
					delResumePoint(current)  # Files were moved to .Trash, okay.
					self.showActionFeedback(f"{_("Deleted")} {name}")
					return
				else:
					msg = f"{_("Cannot move to trash can")}\n"
					are_you_sure = _("Do you really want to delete %s ?") % name
			else:
				if TRASHCAN in cur_path:
					are_you_sure = _("Do you really want to permanently remove '%s' from trash can ?") % name
				else:
					are_you_sure = _("Do you really want to delete %s ?") % name
				msg = ""
			self.session.openWithCallback(self.deleteConfirmed, MessageBox, msg + are_you_sure, windowTitle=self.getTitle())

	def deleteConfirmed(self, confirmed):
		if not confirmed:
			return
		item = self.getCurrentSelection()
		if item is None:
			return  # Huh?
		current = item[0]
		info = item[1]
		name = info and info.getName(current) or _("this recording")
		serviceHandler = eServiceCenter.getInstance()
		offline = serviceHandler.offlineOperations(current)
		try:
			if offline is None:
				from enigma import eBackgroundFileEraser
				eBackgroundFileEraser.getInstance().erase(realpath(current.getPath()))
			else:
				if offline.deleteFromDisk(0):
					raise Exception("Offline delete failed")
			self["list"].removeService(current)
			from Screens.InfoBarGenerics import delResumePoint
			delResumePoint(current)
			self.showActionFeedback(f"{_("Deleted")} {name}")
		except Exception as err:
			self.session.open(MessageBox, f"{_("Delete failed!")}\n{name}\n{str(err)}", MessageBox.TYPE_ERROR, windowTitle=self.getTitle())

	def purgeAll(self):
		recordings = self.session.nav.getRecordings(False, pNavigation.isRealRecording)
		next_rec_time = -1
		if not recordings:
			next_rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
		if recordings or (next_rec_time > 0 and (next_rec_time - time()) < 120):
			msg = f"\n{_("Recording(s) are in progress or coming up in few seconds!")}"
		else:
			msg = ""
		self.session.openWithCallback(self.purgeConfirmed, MessageBox, _("Permanently delete all recordings in the trash can?") + msg, windowTitle=self.getTitle())

	def purgeConfirmed(self, confirmed):
		if not confirmed:
			return
		item = self.getCurrentSelection()
		current = item[0]
		cleanAll(split(current.getPath())[0])

	def showNetworkMounts(self):
		try:
			from Plugins.SystemPlugins.NetworkBrowser.plugin import MountManagerMain
			MountManagerMain(self.session)
		except ImportError:
			pass

	def showDeviceMounts(self):
		from Screens.DeviceManager import DeviceManager
		self.session.open(DeviceManager)

	def showActionFeedback(self, text):
		if self.feedbackTimer is None:
			self.feedbackTimer = eTimer()
			self.feedbackTimer.callback.append(self.hideActionFeedback)
		else:
			self.feedbackTimer.stop()
		self.feedbackTimer.start(3000, 1)
		self.diskinfo.setText(text)

	def hideActionFeedback(self):
		self.diskinfo.update()
		current = self.getCurrent()
		if current is not None:
			self.trashinfo.update(current.getPath())

	def can_gohome(self, item):
		return True

	def do_gohome(self):
		self.gotFilename(defaultMoviePath())

	def do_sortdefault(self):
		print(f"[MovieSelection] Sort '{config.movielist.moviesort.value}'.")
		config.movielist.moviesort.load()
		print(f"[MovieSelection] Sort '{config.movielist.moviesort.value}'.")
		self.sortBy(int(config.movielist.moviesort.value))

	def do_sort(self):
		index = 0
		for index, item in enumerate(l_moviesort):
			if int(item[0]) == int(config.movielist.moviesort.value):
				break
		if index >= len(l_moviesort) - 1:
			index = 0
		else:
			index += 1
		sorttext = l_moviesort[index][2]  # Descriptions in native languages too long.
		if config.movielist.btn_red.value == "sort":
			self["key_red"].setText(sorttext)
		if config.movielist.btn_green.value == "sort":
			self["key_green"].setText(sorttext)
		if config.movielist.btn_yellow.value == "sort":
			self["key_yellow"].setText(sorttext)
		if config.movielist.btn_blue.value == "sort":
			self["key_blue"].setText(sorttext)
		self.sorttimer = eTimer()
		self.sorttimer.callback.append(self._updateButtonTexts)
		self.sorttimer.start(3000, True)  # Time for displaying sorting type just applied.
		self.sortBy(int(l_moviesort[index][0]))
		self["movie_sort"].setPixmapNum(self.getPixmapSortIndex(l_moviesort[index][0]))

	def do_preview(self):
		self.preview()

	def displaySortStatus(self):
		self["movie_sort"].setPixmapNum(self.getPixmapSortIndex(config.movielist.moviesort.value))
		self["movie_sort"].show()

	def can_movieoff(self, item):
		return True

	def do_movieoff(self):
		self.setNextMovieOffStatus()
		self.displayMovieOffStatus()

	def displayMovieOffStatus(self):
		self["movie_off"].setPixmapNum(config.usage.on_movie_eof.getIndex())
		self["movie_off"].show()

	def setNextMovieOffStatus(self):
		config.usage.on_movie_eof.selectNext()
		self.settings["movieoff"] = config.usage.on_movie_eof.value
		self.saveLocalSettings()

	def can_movieoff_menu(self, item):
		return True

	def do_movieoff_menu(self):
		current_movie_eof = config.usage.on_movie_eof.value
		menu = []
		for x in config.usage.on_movie_eof.choices:
			config.usage.on_movie_eof.value = x
			menu.append((config.usage.on_movie_eof.getText(), x))
		config.usage.on_movie_eof.value = current_movie_eof
		used = config.usage.on_movie_eof.getIndex()
		self.session.openWithCallback(self.movieoffMenuCallback, ChoiceBox, title=_("On end of movie"), list=menu, selection=used)

	def movieoffMenuCallback(self, choice):
		if choice is None:
			return
		self.settings["movieoff"] = choice[1]
		self.saveLocalSettings()
		self.displayMovieOffStatus()

	def createPlaylist(self):
		global playlist
		items = playlist
		del items[:]
		for index, item in enumerate(self["list"]):
			if item:
				item = item[0]
				path = item.getPath()
				if not item.flags & eServiceReference.mustDescent:
					ext = splitext(path)[1].lower()
					if ext in IMAGE_EXTENSIONS:
						continue
					else:
						items.append(item)

	def openSubsSupport(self):
		item = self.getCurrentSelection()
		if item and item[0] and item[1] and not item[0].flags & eServiceReference.mustDescent:
			info = item[1]
			name = info and info.getName(item[0])
			path = item[0].getPath()
			if name:
				try:  # The import must be done here, otherwise enigma will not start.
					from Plugins.Extensions.SubsSupport.subtitles import SubsSearch, E2SubsSeeker, initSubsSettings
					settings = initSubsSettings().search
					self.session.open(SubsSearch, E2SubsSeeker(self.session, settings), settings, filepath=path, searchTitles=[name], standAlone=True)
				except Exception as err:
					print(f"[MovieSelection] Error: Start SubsSupport plugin failed!  ({str(err)})")


class MovieSelectionSummary(Screen):
	# Kludgy component to display current selection on LCD. Should use
	# parent.Service as source for everything, but that seems to have a
	# performance impact as the MovieSelection goes through hoops to prevent
	# this when the info is not selected.
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["name"] = StaticText("")
		self.onShow.append(self.__onShow)
		self.onHide.append(self.__onHide)

	def __onShow(self):
		self.parent.list.connectSelChanged(self.selectionChanged)
		self.selectionChanged()

	def __onHide(self):
		self.parent.list.disconnectSelChanged(self.selectionChanged)

	def selectionChanged(self):
		item = self.parent.getCurrentSelection()
		if item and item[0]:
			data = item[3]
			if (data is not None) and (data != -1):
				name = data.txt
			elif not item[1]:
				name = ".."  # special case, one up.
			else:
				name = item[1].getName(item[0])
			if item[0].flags & eServiceReference.mustDescent:
				if len(name) > 12:
					name = split(normpath(name))[1]
				name = f"> {name}"
			self["name"].text = name
		else:
			self["name"].text = ""


class MovieContextMenu(Screen, ProtectedScreen):  # Contract: On OK returns a callable object (e.g. delete).
	def __init__(self, session, csel, service):
		self.csel = csel
		Screen.__init__(self, session)
		ProtectedScreen.__init__(self)
		self.skinName = "Setup"
		self.setTitle(_("Movie List Settings"))
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)
		self["footnote"] = Label("")
		self["description"] = Label("")
		self["status"] = StaticText()
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "NumberActions", "MenuActions"], {
			"red": self.cancelClick,
			"green": self.okbuttonClick,
			"ok": self.okbuttonClick,
			"cancel": self.cancelClick
		})
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		menu = [
			(_("Settings") + "...", csel.configure),
			(_("Device mounts") + "...", csel.showDeviceMounts),
			(_("Network mounts") + "...", csel.showNetworkMounts),
			(_("Create Directory"), csel.do_createdir),
			(_("Sort by") + "...", csel.selectSortby)
		]
		if csel.exist_bookmark():
			menu.append((_("Remove Bookmark"), csel.do_addbookmark))
		else:
			menu.append((_("Add Bookmark"), csel.do_addbookmark))
		if service:
			if service.flags & eServiceReference.mustDescent:
				if isTrashFolder(service):
					menu.append((_("Permanently remove all deleted items"), csel.purgeAll))
				else:
					menu.append((_("Delete"), csel.do_delete))
					menu.append((_("Move"), csel.do_move))
					menu.append((_("Copy"), csel.do_copy))
					menu.append((_("Rename"), csel.do_rename))
			else:
				menu.append((_("Delete"), csel.do_delete))
				menu.append((_("Move"), csel.do_move))
				menu.append((_("Copy"), csel.do_copy))
				menu.append((_("Reset playback position"), csel.do_reset))
				menu.append((_("Rename"), csel.do_rename))
				menu.append((_("Start offline decode"), csel.do_decode))
				if isfile(f"{service.getPath().rstrip("/")}.meta"):
					menu.append((_("Edit Tags"), csel.do_tageditor))
				# Plugins expect a valid selection, so only include them if we selected a non-directory.
				menu.extend([(p.description, boundFunction(p, session, service)) for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST)])
		self["config"] = MenuList(menu)

	def isProtected(self):
		return self.csel.protectContextMenu and config.ParentalControl.setuppinactive.value and config.ParentalControl.config_sections.context_menus.value

	def pinEntered(self, answer):
		if answer:
			self.csel.protectContextMenu = False
		ProtectedScreen.pinEntered(self, answer)

	def createSummary(self):
		return MovieContextMenuSummary

	def okbuttonClick(self):
		self.close(self["config"].getCurrent()[1])

	def cancelClick(self):
		self.close(None)


class MovieContextMenuSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["selected"] = StaticText("")
		self.onShow.append(self.__onShow)
		self.onHide.append(self.__onHide)

	def __onShow(self):
		self.parent["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def __onHide(self):
		self.parent["config"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		item = self.parent["config"].getCurrent()
		self["selected"].text = item[0]


class MovieSelectionSetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, setup="MovieSelection")

	def keySave(self):
		self.saveAll()
		self.close(True)

	def closeConfigList(self, closeParameters=()):
		Setup.closeConfigList(self, (False,))


playlist = []
