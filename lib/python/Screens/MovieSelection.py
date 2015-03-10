import os
import time
import cPickle as pickle

from enigma import eServiceReference, eServiceCenter, eTimer, eSize, iPlayableService, iServiceInformation, getPrevAsciiCode, eRCInput

from Screen import Screen
from Components.Button import Button
from Components.ActionMap import HelpableActionMap, ActionMap, NumberActionMap
from Components.MenuList import MenuList
from Components.MovieList import MovieList, resetMoviePlayState, AUDIO_EXTENSIONS, DVD_EXTENSIONS, IMAGE_EXTENSIONS
from Components.DiskInfo import DiskInfo
from Tools.Trashcan import TrashInfo
from Components.Pixmap import Pixmap, MultiPixmap
from Components.Label import Label
from Components.PluginComponent import plugins
from Components.config import config, ConfigSubsection, ConfigText, ConfigInteger, ConfigLocations, ConfigSet, ConfigYesNo, ConfigSelection, getConfigListEntry, ConfigSelectionNumber
from Components.ConfigList import ConfigListScreen
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.StaticText import StaticText
import Components.Harddisk
from Components.UsageConfig import preferredTimerPath
from Components.Sources.Boolean import Boolean
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.LocationBox import MovieLocationBox
from Screens.HelpMenu import HelpableScreen
import Screens.InfoBar
from Tools import NumericalTextInput
from Tools.Directories import resolveFilename, SCOPE_HDD
from Tools.BoundFunction import boundFunction
import Tools.CopyFiles
import Tools.Trashcan
import NavigationInstance
import RecordTimer


config.movielist = ConfigSubsection()
config.movielist.curentlyplayingservice = ConfigText()
config.movielist.show_live_tv_in_movielist = ConfigYesNo(default=True)
config.movielist.fontsize = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
config.movielist.itemsperpage = ConfigSelectionNumber(default = 20, stepwidth = 1, min = 3, max = 30, wraparound = True)
config.movielist.useslim = ConfigYesNo(default=False)
config.movielist.useextlist = ConfigSelection(default='0', choices={'0': _('No'), '1': _('ServiceName'), '2': _('ServicePicon')})
config.movielist.eventinfo_delay = ConfigSelectionNumber(50, 1000, 50, default= 100)
config.movielist.moviesort = ConfigInteger(default=MovieList.SORT_GROUPWISE)
config.movielist.description = ConfigInteger(default=MovieList.SHOW_DESCRIPTION)
config.movielist.last_videodir = ConfigText(default=resolveFilename(SCOPE_HDD))
config.movielist.last_timer_videodir = ConfigText(default=resolveFilename(SCOPE_HDD))
config.movielist.videodirs = ConfigLocations(default=[resolveFilename(SCOPE_HDD)])
config.movielist.last_selected_tags = ConfigSet([], default=[])
config.movielist.play_audio_internal = ConfigYesNo(default=True)
config.movielist.settings_per_directory = ConfigYesNo(default=True)
config.movielist.root = ConfigSelection(default="/media", choices=["/","/media","/media/hdd","/media/hdd/movie"])
config.movielist.hide_extensions = ConfigYesNo(default=False)
config.movielist.stop_service = ConfigYesNo(default=True)

userDefinedButtons = None
last_selected_dest = []
preferredTagEditor = None

# this kludge is needed because ConfigSelection only takes numbers
# and someone appears to be fascinated by 'enums'.
l_moviesort = [
	(str(MovieList.SORT_GROUPWISE), _("default") , '02/01 & A-Z'),
	(str(MovieList.SORT_RECORDED), _("by date"), '03/02/01'),
	(str(MovieList.SORT_ALPHANUMERIC), _("alphabetic"), 'A-Z'),
	(str(MovieList.SORT_ALPHANUMERIC_FLAT), _("flat alphabetic"), 'A-Z Flat'),
	(str(MovieList.SHUFFLE), _("shuffle"), '?'),
	(str(MovieList.SORT_RECORDED_REVERSE), _("reverse by date"), '01/02/03'),
	(str(MovieList.SORT_ALPHANUMERIC_REVERSE), _("alphabetic reverse"), 'Z-A'),
	(str(MovieList.SORT_ALPHANUMERIC_FLAT_REVERSE), _("flat alphabetic reverse"), 'Z-A Flat'),
	(str(MovieList.SORT_ALPHA_DATE_OLDEST_FIRST), _("alpha then oldest"), 'A1 A2 Z1'),
	(str(MovieList.SORT_ALPHAREV_DATE_NEWEST_FIRST), _("alpharev then newest"),  'Z1 A2 A1')]

def defaultMoviePath():
	result = config.usage.default_path.value
	if not os.path.isdir(result):
		from Tools import Directories
		return Directories.defaultRecordingLocation(config.usage.default_path.value)
	return result

def setPreferredTagEditor(te):
	global preferredTagEditor
	if preferredTagEditor is None:
		preferredTagEditor = te
		print "Preferred tag editor changed to", preferredTagEditor
	else:
		print "Preferred tag editor already set to", preferredTagEditor, "ignoring", te

def getPreferredTagEditor():
	global preferredTagEditor
	return preferredTagEditor

def isTrashFolder(ref):
	if not config.usage.movielist_trashcan.value or not ref.flags & eServiceReference.mustDescent:
		return False
	return os.path.realpath(ref.getPath()).endswith('.Trash') or os.path.realpath(ref.getPath()).endswith('.Trash/')

def isInTrashFolder(ref):
	if not config.usage.movielist_trashcan.value or not ref.flags & eServiceReference.mustDescent:
		return False
	path = os.path.realpath(ref.getPath())
	return path.startswith(Tools.Trashcan.getTrashFolder(path))

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
	#normpath is to remove the trailing '/' from directories
	src = os.path.normpath(serviceref.getPath())
	srcPath, srcName = os.path.split(src)
	if os.path.normpath(srcPath) == dest:
		# move file to itself is allowed, so we have to check it
		raise Exception, "Refusing to move to the same directory"
	# Make a list of items to move
	moveList = [(src, os.path.join(dest, srcName))]
	if not serviceref.flags & eServiceReference.mustDescent:
		# Real movie, add extra files...
		srcBase = os.path.splitext(src)[0]
		baseName = os.path.split(srcBase)[1]
		eitName =  srcBase + '.eit'
		if os.path.exists(eitName):
			moveList.append((eitName, os.path.join(dest, baseName+'.eit')))
		baseName = os.path.split(src)[1]
		for ext in ('.ap', '.cuts', '.meta', '.sc'):
			candidate = src + ext
			if os.path.exists(candidate):
				moveList.append((candidate, os.path.join(dest, baseName+ext)))
	return moveList

def moveServiceFiles(serviceref, dest, name=None, allowCopy=True):
	moveList = createMoveList(serviceref, dest)
	# Try to "atomically" move these files
	movedList = []
	try:
		# print "[MovieSelection] Moving in background..."
		# start with the smaller files, do the big one later.
		moveList.reverse()
		if name is None:
			name = os.path.split(moveList[-1][0])[1]
		Tools.CopyFiles.moveFiles(moveList, name)
	except Exception, e:
		print "[MovieSelection] Failed move:", e
		# rethrow exception
		raise

def copyServiceFiles(serviceref, dest, name=None):
	# current should be 'ref' type, dest a simple path string
	moveList = createMoveList(serviceref, dest)
	# Try to "atomically" move these files
	movedList = []
	try:
		# print "[MovieSelection] Copying in background..."
		# start with the smaller files, do the big one later.
		moveList.reverse()
		if name is None:
			name = os.path.split(moveList[-1][0])[1]
		Tools.CopyFiles.copyFiles(moveList, name)
	except Exception, e:
		print "[MovieSelection] Failed copy:", e
		# rethrow exception
		raise

class MovieBrowserConfiguration(ConfigListScreen,Screen):
	def __init__(self, session, args = 0):
		Screen.__init__(self, session)
		self.session = session
		self.skinName = "Setup"
		self.setup_title = _("Movie List Setup")
		Screen.setTitle(self, _(self.setup_title))
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)
		self['footnote'] = Label("")
		self["description"] = Label("")

		self.onChangedEntry = [ ]
		cfg = ConfigSubsection()
		self.cfg = cfg
		cfg.moviesort = ConfigSelection(default=str(config.movielist.moviesort.value), choices = l_moviesort)
		cfg.description = ConfigYesNo(default=(config.movielist.description.value != MovieList.HIDE_DESCRIPTION))
		configList = [getConfigListEntry(_("Use trash can in movielist"), config.usage.movielist_trashcan, _("When enabled, deleted recordings are moved to the trash can, instead of being deleted immediately.")),
					  getConfigListEntry(_("Remove items from trash can after (days)"), config.usage.movielist_trashcan_days, _("Configure the number of days after which items are automatically removed from the trash can.")),
					  getConfigListEntry(_("Clean network trash cans"), config.usage.movielist_trashcan_network_clean, _("When enabled, network trash cans are probed for cleaning.")),
					  getConfigListEntry(_("Disk space to reserve for recordings (in GB)"), config.usage.movielist_trashcan_reserve, _("Configure the minimum amount of disk space to be available for recordings. When the amount of space drops below this value, deleted items will be removed from the trash can.")),
					  getConfigListEntry(_("Background delete option"), config.misc.erase_flags, _("Configure on which devices the background delete option should be used.")),
					  getConfigListEntry(_("Background delete speed"), config.misc.erase_speed, _("Configure the speed of the background deletion process. Lower speed will consume less hard disk drive performance.")),
					  getConfigListEntry(_("Fontsize"), config.movielist.fontsize, _("This allows you change the font size relative to skin size, so 1 increases by 1 point size, and -1 decreases by 1 point size")),
					  getConfigListEntry(_("Number of rows"), config.movielist.itemsperpage, _("Number of rows to display")), getConfigListEntry(_("Use slim screen"), config.movielist.useslim, _("Use the alternative screen")),
					  getConfigListEntry(_("Use extended List"), config.movielist.useextlist, _("Use the extended List")), getConfigListEntry(_("Update delay for Events in List"), config.movielist.eventinfo_delay, _("Update delay for Events in List. Scrolling in List is faster with higher delay, specialy on big Lists !")),
					  getConfigListEntry(_("Sort"), cfg.moviesort, _("Set the default sorting method.")), getConfigListEntry(_("Show extended description"), cfg.description, _("Show or hide the extended description, (skin dependent).")),
					  getConfigListEntry(_("Use individual settings for each directory"), config.movielist.settings_per_directory, _("When set each folder will show the previous state used, when off the default values will be shown.")),
					  getConfigListEntry(_("Behavior when a movie reaches the end"), config.usage.on_movie_eof, _("On reaching the end of a file during playback, you can choose the box's behavior.")),
					  getConfigListEntry(_("Stop service on return to movie list"), config.movielist.stop_service, _("Stop previous broadcasted service on return to movielist.")),
					  getConfigListEntry(_("Show status icons in movielist"), config.usage.show_icons_in_movielist, _("Shows the watched status of the movie."))]		
		if config.usage.show_icons_in_movielist.value:
			configList.append(getConfigListEntry(_("Show icon for new/unseen items"), config.usage.movielist_unseen, _("Shows the icons when new/unseen, else will not show an icon.")))
		configList.append(getConfigListEntry(_("Play audio in background"), config.movielist.play_audio_internal, _("Keeps MovieList open whilst playing audio files.")))
		configList.append(getConfigListEntry(_("Root directory"), config.movielist.root, _("Sets the root folder of movie list, to remove the '..' from benign shown in that folder.")))
		configList.append(getConfigListEntry(_("Hide known extensions"), config.movielist.hide_extensions, _("Allows you to hide the extensions of known file types.")))
		configList.append(getConfigListEntry(_("Show live tv when movie stopped"), config.movielist.show_live_tv_in_movielist, _("When set the PIG will return to live after a movie has stopped playing.")))
		for btn in (('red', _('Red')), ('green', _('Green')), ('yellow', _('Yellow')), ('blue', _('Blue')),('redlong', _('Red long')), ('greenlong', _('Green long')), ('yellowlong', _('Yellow long')), ('bluelong', _('Blue long')), ('TV', _('TV')), ('Radio', _('Radio')), ('Text', _('Text'))):
			configList.append(getConfigListEntry(_("Button") + " " + _(btn[1]), userDefinedButtons[btn[0]], _("Allows you to setup the button to do what you choose.")))
		ConfigListScreen.__init__(self, configList, session = self.session, on_change = self.changedEntry)
		self["config"].setList(configList)
		if config.usage.sort_settings.value:
			self["config"].list.sort()

		self["actions"] = ActionMap(["SetupActions", 'ColorActions'],
		{
			"red": self.cancel,
			"green": self.save,
			"save": self.save,
			"cancel": self.cancel,
			"ok": self.save,
		}, -2)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		self["description"].setText(self["config"].getCurrent()[2])

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent() and self["config"].getCurrent()[0] or ""

	def getCurrentValue(self):
		return self["config"].getCurrent() and str(self["config"].getCurrent()[1].getText()) or ""

	def getCurrentDescription(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2] or ""

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

	def save(self):
		self.saveAll()
		cfg = self.cfg
		config.movielist.moviesort.setValue(int(cfg.moviesort.value))
		if cfg.description.value:
			config.movielist.description.value = MovieList.SHOW_DESCRIPTION
		else:
			config.movielist.description.value = MovieList.HIDE_DESCRIPTION
		if not config.movielist.settings_per_directory.value:
			config.movielist.moviesort.save()
			config.movielist.description.save()
			config.movielist.useslim.save()
			config.usage.on_movie_eof.save()
		self.close(True)

	def cancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelCallback, MessageBox, _("Really close without saving settings?"))
		else:
			self.cancelCallback(True)

	def cancelCallback(self, answer):
		if answer:
			for x in self["config"].list:
				x[1].cancel()
			self.close(False)

class MovieContextMenuSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
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


class MovieContextMenu(Screen):
	# Contract: On OK returns a callable object (e.g. delete)
	def __init__(self, session, csel, service):
		Screen.__init__(self, session)
		self.skinName = "Setup"
		self.setup_title = _("Movie List Setup")
		Screen.setTitle(self, _(self.setup_title))
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)
		self['footnote'] = Label("")
		self["status"] = StaticText()

		self["actions"] = ActionMap(["OkCancelActions", 'ColorActions'],
			{
				"red": self.cancelClick,
				"green": self.okbuttonClick,
				"ok": self.okbuttonClick,
				"cancel": self.cancelClick
			})

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		menu = [(_("Settings") + "...", csel.configure),
				(_("Device mounts") + "...", csel.showDeviceMounts),
				(_("Network mounts") + "...", csel.showNetworkMounts),
				(_("Add bookmark"), csel.do_addbookmark),
				(_("Create directory"), csel.do_createdir),
				(_("Sort by") + "...", csel.selectSortby)]
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
				# Plugins expect a valid selection, so only include them if we selected a non-dir
				menu.extend([(p.description, boundFunction(p, session, service)) for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST)])

		self["config"] = MenuList(menu)

	def createSummary(self):
		return MovieContextMenuSummary

	def okbuttonClick(self):
		self.close(self["config"].getCurrent()[1])

	def cancelClick(self):
		self.close(None)

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

class MovieSelectionSummary(Screen):
	# Kludgy component to display current selection on LCD. Should use
	# parent.Service as source for everything, but that seems to have a
	# performance impact as the MovieSelection goes through hoops to prevent
	# this when the info is not selected
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
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
				# special case, one up
				name = ".."
			else:
				name = item[1].getName(item[0])
			if item[0].flags & eServiceReference.mustDescent:
				if len(name) > 12:
					name = os.path.split(os.path.normpath(name))[1]
				name = "> " + name
			self["name"].text = name
		else:
			self["name"].text = ""
			
from Screens.ParentalControlSetup import ProtectedScreen

class MovieSelection(Screen, HelpableScreen, SelectionEventInfo, InfoBarBase, ProtectedScreen):
	# SUSPEND_PAUSES actually means "please call my pauseService()"
	ALLOW_SUSPEND = Screen.SUSPEND_PAUSES

	def __init__(self, session, selectedmovie = None, timeshiftEnabled = False):
		Screen.__init__(self, session)
		if config.movielist.useslim.value:
			self.skinName = ["MovieSelectionSlim","MovieSelection"]
		else:
			self.skinName = "MovieSelection"
		HelpableScreen.__init__(self)
		if config.ParentalControl.configured.value:
			ProtectedScreen.__init__(self)
		if not timeshiftEnabled:
			InfoBarBase.__init__(self) # For ServiceEventTracker
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

		self.numericalTextInput = NumericalTextInput.NumericalTextInput(mapping=NumericalTextInput.MAP_SEARCH_UPCASE)
		self["chosenletter"] = Label("")
		self["chosenletter"].visible = False

		self["waitingtext"] = Label(_("Please wait... Loading list..."))

		self.LivePlayTimer = eTimer()
		self.LivePlayTimer.timeout.get().append(self.LivePlay)

		self.filePlayingTimer = eTimer()
		self.filePlayingTimer.timeout.get().append(self.FilePlaying)

		self.playingInForeground = None
		# create optional description border and hide immediately
		self["DescriptionBorder"] = Pixmap()
		self["DescriptionBorder"].hide()

		if not os.path.isdir(config.movielist.last_videodir.value):
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

		self.playGoTo = None #1 - preview next item / -1 - preview previous

		title = _("Movie selection")
		self.setTitle(title)

		# Need list for init
		SelectionEventInfo.__init__(self)

		self["key_red"] = Button("")
		self["key_green"] = Button("")
		self["key_yellow"] = Button("")
		self["key_blue"] = Button("")
		self._updateButtonTexts()

		self["movie_off"] = MultiPixmap()
		self["movie_off"].hide()

		self["movie_sort"] = MultiPixmap()
		self["movie_sort"].hide()

		self["freeDiskSpace"] = self.diskinfo = DiskInfo(config.movielist.last_videodir.value, DiskInfo.FREE, update=False)
		self["TrashcanSize"] = self.trashinfo = TrashInfo(config.movielist.last_videodir.value, TrashInfo.USED, update=False)

		self["InfobarActions"] = HelpableActionMap(self, "InfobarActions",
			{
				"showMovies": (self.doPathSelect, _("Select the movie path")),
				"showRadio": (self.btn_radio, "?"),
				"showTv": (self.btn_tv, _("Home")),
				"showText": (self.btn_text, _("On end of movie")),
			})

		self["NumberActions"] =  NumberActionMap(["NumberActions", "InputAsciiActions"],
			{
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
			})

		self["playbackActions"] = HelpableActionMap(self, "MoviePlayerActions",
			{
				"leavePlayer": (self.playbackStop, _("Stop")),
				"moveNext": (self.playNext, _("Play next")),
				"movePrev": (self.playPrev, _("Play previous")),
				"channelUp": (self.moveToFirstOrFirstFile, _("Go to first movie or top of list")),
				"channelDown": (self.moveToLastOrFirstFile, _("Go to first movie or last item")),
			})
		self["MovieSelectionActions"] = HelpableActionMap(self, "MovieSelectionActions",
			{
				"contextMenu": (self.doContext, _("Menu")),
				"showEventInfo": (self.showEventInformation, _("Show event details")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
				"red": (self.btn_red, _("Delete...")),
				"green": (self.btn_green, _("Move to other directory")),
				"yellow": (self.btn_yellow, _("Select the movie path")),
				"blue": (self.btn_blue, _("Change sort by...")),
				"redlong": (self.btn_redlong, _("Rename...")),
				"greenlong": (self.btn_greenlong, _("Copy to other directory")),
				"yellowlong": (self.btn_yellowlong, _("Select the movie path")),
				"bluelong": (self.btn_bluelong, _("Sort by default")),
			})
		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
				"cancel": (self.abort, _("Exit movie list")),
				"ok": (self.itemSelected, _("Select movie")),
			})
		self["DirectionActions"] = HelpableActionMap(self, "DirectionActions",
			{
				"up": (self.keyUp, _("Go up the list")),
				"down": (self.keyDown, _("Go down the list"))
			}, prio = -2)

		tPreview = _("Preview")
		tFwd = _("skip forward") + " (" + tPreview +")"
		tBack= _("skip backward") + " (" + tPreview +")"
		sfwd = lambda: self.seekRelative(1, config.seek.selfdefined_46.value * 90000)
		ssfwd = lambda: self.seekRelative(1, config.seek.selfdefined_79.value * 90000)
		sback = lambda: self.seekRelative(-1, config.seek.selfdefined_46.value * 90000)
		ssback = lambda: self.seekRelative(-1, config.seek.selfdefined_79.value * 90000)
		self["SeekActions"] = HelpableActionMap(self, "MovielistSeekActions",
			{
				"playpauseService": (self.preview, _("Preview")),
				"seekFwd": (sfwd, tFwd),
				"seekFwdManual": (ssfwd, tFwd),
				"seekBack": (sback, tBack),
				"seekBackManual": (ssback, tBack),
			}, prio=5)
		self.onShown.append(self.onFirstTimeShown)
		self.onLayoutFinish.append(self.saveListsize)
		self.list.connectSelChanged(self.updateButtons)
		self.onClose.append(self.__onClose)
		NavigationInstance.instance.RecordTimer.on_state_change.append(self.list.updateRecordings)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				#iPlayableService.evSeekableStatusChanged: self.__seekableStatusChanged,
				iPlayableService.evStart: self.__serviceStarted,
				iPlayableService.evEOF: self.__evEOF,
				#iPlayableService.evSOF: self.__evSOF,
			})
		if config.misc.remotecontrol_text_support.value:
			self.onExecBegin.append(self.asciiOff)
		else:
			self.onExecBegin.append(self.asciiOn)

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
				'delete': _("Delete"),
				'move': _("Move"),
				'copy': _("Copy"),
				'reset': _("Reset"),
				'tags': _("Tags"),
				'addbookmark': _("Add bookmark"),
				'bookmarks': _("Location"),
				'rename': _("Rename"),
				'gohome': _("Home"),
				'sort': _("Sort"),
				'sortby': _("Sort by"),
				'sortdefault': _("Sort by default"),
				'preview': _("Preview"),
				'movieoff': _("On end of movie"),
				'movieoff_menu': _("On end of movie (as menu)")
			}
			for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST):
				userDefinedActions['@' + p.name] = p.description
			config.movielist.btn_red = ConfigSelection(default='delete', choices=userDefinedActions)
			config.movielist.btn_green = ConfigSelection(default='move', choices=userDefinedActions)
			config.movielist.btn_yellow = ConfigSelection(default='bookmarks', choices=userDefinedActions)
			config.movielist.btn_blue = ConfigSelection(default='sort', choices=userDefinedActions)
			config.movielist.btn_redlong = ConfigSelection(default='rename', choices=userDefinedActions)
			config.movielist.btn_greenlong = ConfigSelection(default='copy', choices=userDefinedActions)
			config.movielist.btn_yellowlong = ConfigSelection(default='tags', choices=userDefinedActions)
			config.movielist.btn_bluelong = ConfigSelection(default='sortdefault', choices=userDefinedActions)
			config.movielist.btn_radio = ConfigSelection(default='tags', choices=userDefinedActions)
			config.movielist.btn_tv = ConfigSelection(default='gohome', choices=userDefinedActions)
			config.movielist.btn_text = ConfigSelection(default='movieoff', choices=userDefinedActions)
			userDefinedButtons ={
				'red': config.movielist.btn_red,
				'green': config.movielist.btn_green,
				'yellow': config.movielist.btn_yellow,
				'blue': config.movielist.btn_blue,
				'redlong': config.movielist.btn_redlong,
				'greenlong': config.movielist.btn_greenlong,
				'yellowlong': config.movielist.btn_yellowlong,
				'bluelong': config.movielist.btn_bluelong,
				'Radio': config.movielist.btn_radio,
				'TV': config.movielist.btn_tv,
				'Text': config.movielist.btn_text,
			}

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and config.ParentalControl.config_sections.movie_list.value

	def protectedClose_ParentalControl(self, res = None):
		self.close(None)

	def _callButton(self, name):
		if name.startswith('@'):
			item = self.getCurrentSelection()
			if isSimpleFile(item):
				name = name[1:]
				for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST):
					if name == p.name:
						p(self.session, item[0])
			return
		try:
			a = getattr(self, 'do_' + name)
		except Exception:
			# Undefined action
			return
		a()

	def btn_red(self):
		from InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_red.value)
	def btn_green(self):
		from InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_green.value)
	def btn_yellow(self):
		from InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_yellow.value)
	def btn_blue(self):
		from InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_blue.value)
	def btn_redlong(self):
		from InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_redlong.value)
	def btn_greenlong(self):
		from InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_greenlong.value)
	def btn_yellowlong(self):
		from InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_yellowlong.value)
	def btn_bluelong(self):
		from InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance.LongButtonPressed:
			self._callButton(config.movielist.btn_bluelong.value)
	def btn_radio(self):
		self._callButton(config.movielist.btn_radio.value)
	def btn_tv(self):
		self._callButton(config.movielist.btn_tv.value)
	def btn_text(self):
		self._callButton(config.movielist.btn_text.value)

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
		if self.list.getCurrentIndex() <= self.list.firstFileEntry: #selection above or on first movie
			if self.list.getCurrentIndex() < 1:
				self.list.moveToLast()
			else:
				self.list.moveToFirst()
		else:
			self.list.moveToFirstMovie()

	def moveToLastOrFirstFile(self):
		if self.list.getCurrentIndex() >= self.list.firstFileEntry or self.list.firstFileEntry == len(self.list): #selection below or on first movie or no files
			if self.list.getCurrentIndex() == len(self.list) - 1:
				self.list.moveToFirst()
			else:
				self.list.moveToLast()
		else:
			self.list.moveToFirstMovie()

	def keyNumberGlobal(self, number):
		unichar = self.numericalTextInput.getKey(number)
		charstr = unichar.encode("utf-8")
		if len(charstr) == 1:
			self.list.moveToChar(charstr[0], self["chosenletter"])

	def keyAsciiCode(self):
		unichar = unichr(getPrevAsciiCode())
		charstr = unichar.encode("utf-8")
		if len(charstr) == 1:
			self.list.moveToString(charstr[0], self["chosenletter"])

	def isItemPlayable(self, index):
		item = self.list.getItem(index)
		if item:
			path = item.getPath()
			if not item.flags & eServiceReference.mustDescent:
				ext = os.path.splitext(path)[1].lower()
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
				path = os.path.split(os.path.normpath(path))[0]
				if not path.endswith('/'):
					path += '/'
				self.gotFilename(path, selItem = service)
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
					path = os.path.abspath(os.path.join(path, os.path.pardir))
					path = os.path.abspath(os.path.join(path, os.path.pardir))
					self.gotFilename(path)

	def __onClose(self):
		try:
			NavigationInstance.instance.RecordTimer.on_state_change.remove(self.list.updateRecordings)
		except Exception, e:
			print "[ML] failed to unsubscribe:", e
			pass

	def createSummary(self):
		return MovieSelectionSummary

	def updateDescription(self):
		if self.settings["description"] == MovieList.SHOW_DESCRIPTION:
			self["DescriptionBorder"].show()
			self["list"].instance.resize(eSize(self.listWidth, self.listHeight-self["DescriptionBorder"].instance.size().height()))
		else:
			self["Service"].newService(None)
			self["DescriptionBorder"].hide()
			self["list"].instance.resize(eSize(self.listWidth, self.listHeight))

	def pauseService(self):
		# Called when pressing Power button (go to standby)
		self.playbackStop()
		self.session.nav.stopService()

	def unPauseService(self):
		# When returning from standby. It might have been a while, so
		# reload the list.
		self.reloadList()

	def can_move(self, item):
		if not item:
			return False
		return canMove(item)

	def can_delete(self, item):
		try:
			if not item:
				return False
			return canDelete(item) or isTrashFolder(item[0])
		except:

			return False

	def can_default(self, item):
		# returns whether item is a regular file
		return isSimpleFile(item)

	def can_sort(self, item):
		return True

	def can_preview(self, item):
		return isSimpleFile(item)

	def _updateButtonTexts(self):
		for k in ('red', 'green', 'yellow', 'blue'):
			btn = userDefinedButtons[k]
			self['key_' + k].setText(userDefinedActions[btn.value])

	def updateButtons(self):
		item = self.getCurrentSelection()
		for name in ('red', 'green', 'yellow', 'blue'):
			action = userDefinedButtons[name].value
			if action.startswith('@'):
				check = self.can_default
			else:
				try:
					check = getattr(self, 'can_' + action)
				except:
					check = self.can_default
			gui = self["key_" + name]
			if check(item):
				gui.show()
			else:
				gui.hide()

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
		if self.session.nav.getCurrentlyPlayingServiceReference() and ':0:/' in self.session.nav.getCurrentlyPlayingServiceReference().toString():
			self.list.playInForeground = self.session.nav.getCurrentlyPlayingServiceReference()
		else:
			self.list.playInForeground = None
		self.filePlayingTimer.stop()

	def onFirstTimeShown(self):
		self.filePlayingTimer.start(100)
		self.onShown.remove(self.onFirstTimeShown) # Just once, not after returning etc.
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
			if ':0:/' not in self.session.nav.getCurrentlyPlayingServiceReference().toString():
				config.movielist.curentlyplayingservice.setValue(self.session.nav.getCurrentlyPlayingServiceReference().toString())
		checkplaying = self.session.nav.getCurrentlyPlayingServiceReference()
		if checkplaying:
			checkplaying = checkplaying.toString()
		if checkplaying is None or (config.movielist.curentlyplayingservice.value != checkplaying and ':0:/' not in self.session.nav.getCurrentlyPlayingServiceReference().toString()):
			self.session.nav.playService(eServiceReference(config.movielist.curentlyplayingservice.value))
		self.LivePlayTimer.stop()

	def getCurrent(self):
		# Returns selected serviceref (may be None)
		return self["list"].getCurrent()

	def getCurrentSelection(self):
		# Returns None or (serviceref, info, begin, len)
		return self["list"].l.getCurrentSelection()

	def playAsDVD(self, path):
		try:
			from Screens import DVD
			if path.endswith('VIDEO_TS/'):
				# strip away VIDEO_TS/ part
				path = os.path.split(path.rstrip('/'))[0]
			self.session.open(DVD.DVDPlayer, dvd_filelist=[path])
			return True
		except Exception, e:
			print "[ML] DVD Player not installed:", e

	def __serviceStarted(self):
		if not self.list.playInBackground or not self.list.playInForeground:
			return
		ref = self.session.nav.getCurrentService()
		cue = ref.cueSheet()
		if not cue:
			return
		# disable writing the stop position
		cue.setCutListEnable(2)
		# find "resume" position
		cuts = cue.getCutList()
		if not cuts:
			return
		for (pts, what) in cuts:
			if what == 3:
				last = pts
				break
		else:
			# no resume, jump to start of program (first marker)
			last = cuts[0][0]
		self.doSeekTo = last
		self.callLater(self.doSeek)

	def doSeek(self, pts = None):
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
		if not playInBackground:
			print "Not playing anything in background"
			return
		if not playInBackground:
			print "Not playing anything in foreground"
			return
		current = self.getCurrent()
		self.session.nav.stopService()
		self.list.playInBackground = None
		self.list.playInForeground = None
		if config.movielist.play_audio_internal.value:
			index = self.list.findService(playInBackground)
			if index is None:
				return # Not found?
			next = self.list.getItem(index + 1)
			if not next:
				return
			path = next.getPath()
			ext = os.path.splitext(path)[1].lower()
			print "Next up:", path
			if ext in AUDIO_EXTENSIONS:
				self.nextInBackground = next
				self.callLater(self.preview)
				self["list"].moveToIndex(index+1)

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
				# come back to play the new one
				self.callLater(self.preview)
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
			# check if MerlinMusicPlayer is installed and merlinmp3player.so is running
			# so we need the right id to play now the mp3-file
			if current.type == 4116:
				path = current.getPath()
				service = eServiceReference(4097, 0, path)
				self.session.nav.playService(service)
			else:
				self.session.nav.playService(current)

	def previewCheckTimeshiftCallback(self, answer):
		if answer:
			self.startPreview()

	def seekRelative(self, direction, amount):
		if self.list.playInBackground or self.list.playInBackground:
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

	def itemSelected(self, answer = True):
		current = self.getCurrent()
		if current is not None:
			path = current.getPath()
			if current.flags & eServiceReference.mustDescent:
				if path.endswith("VIDEO_TS/") or os.path.exists(os.path.join(path, 'VIDEO_TS.IFO')):
					#force a DVD extention
					Screens.InfoBar.InfoBar.instance.checkTimeshiftRunning(boundFunction(self.itemSelectedCheckTimeshiftCallback, ".iso", path))
					return
				self.gotFilename(path)
			else:
				ext = os.path.splitext(path)[1].lower()
				if config.movielist.play_audio_internal.value and (ext in AUDIO_EXTENSIONS):
					self.preview()
					return
				if self.list.playInBackground:
					# Stop preview, come back later
					self.session.nav.stopService()
					self.list.playInBackground = None
					self.callLater(self.itemSelected)
					return
				if ext in IMAGE_EXTENSIONS:
					try:
						from Plugins.Extensions.PicturePlayer import ui
						# Build the list for the PicturePlayer UI
						filelist = []
						index = 0
						for item in self.list.list:
							p = item[0].getPath()
							if p == path:
								index = len(filelist)
							if os.path.splitext(p)[1].lower() in IMAGE_EXTENSIONS:
								filelist.append(((p,False), None))
						self.session.open(ui.Pic_Full_View, filelist, index, path)
					except Exception, ex:
						print "[ML] Cannot display", str(ex)
					return
				Screens.InfoBar.InfoBar.instance.checkTimeshiftRunning(boundFunction(self.itemSelectedCheckTimeshiftCallback, ext, path))

	def itemSelectedCheckTimeshiftCallback(self, ext, path, answer):
		if answer:
			if ext in DVD_EXTENSIONS:
				if self.playAsDVD(path):
					return
			self.movieSelected()

	# Note: DVDBurn overrides this method, hence the itemSelected indirection.
	def movieSelected(self):
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
			path = os.path.join(config.movielist.last_videodir.value, ".e2settings.pkl")
			file = open(path, "wb")
			pickle.dump(self.settings, file)
			file.close()
		except Exception, e:
			print "Failed to save settings to %s: %s" % (path, e)
		# Also set config items, in case the user has a read-only disk
		config.movielist.moviesort.value = self.settings["moviesort"]
		config.movielist.description.value = self.settings["description"]
		config.usage.on_movie_eof.value = self.settings["movieoff"]
		# save moviesort and movieeof values for using by hotkeys
#		config.movielist.moviesort.save()
		config.usage.on_movie_eof.save()

	def loadLocalSettings(self):
		"""Load settings, called when entering a directory"""
		if config.movielist.settings_per_directory.value:
			try:
				path = os.path.join(config.movielist.last_videodir.value, ".e2settings.pkl")
				file = open(path, "rb")
				updates = pickle.load(file)
				file.close()
				self.applyConfigSettings(updates)
			except IOError, e:
				updates = {
					"moviesort": config.movielist.moviesort.default,
					"description": config.movielist.description.default,
					"movieoff": config.usage.on_movie_eof.default
				}
				self.applyConfigSettings(updates)
				pass # ignore fail to open errors
			except Exception, e:
				print "Failed to load settings from %s: %s" % (path, e)
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
		print 'SORTYBY:',newType
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
		from Screens.InfoBar import InfoBar
		infobar = InfoBar.instance
		if self.session.nav.getCurrentlyPlayingServiceReference():
			if not infobar.timeshiftEnabled() and ':0:/' not in self.session.nav.getCurrentlyPlayingServiceReference().toString():
				self.session.nav.stopService()
		self.close(None)

	def saveconfig(self):
		config.movielist.last_selected_tags.value = self.selected_tags

	def configure(self):
		self.session.openWithCallback(self.configureDone, MovieBrowserConfiguration)

	def configureDone(self, result):
		if result:
			self.applyConfigSettings({
			"moviesort": config.movielist.moviesort.value,
				"description": config.movielist.description.value,
				"movieoff": config.usage.on_movie_eof.value})
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
		index = 0
		used = 0
		for x in l_moviesort:
			if int(x[0]) == int(config.movielist.moviesort.value):
				used = index
			menu.append((_(x[1]), x[0], "%d" % index))
			index += 1
		self.session.openWithCallback(self.sortbyMenuCallback, ChoiceBox, title=_("Sort list:"), list=menu, selection = used)

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

	def getTagDescription(self, tag):
		# TODO: access the tag database
		return tag

	def updateTags(self):
		# get a list of tags available in this list
		self.tags = self["list"].tags

	def setDescriptionState(self, val):
		self["list"].setDescriptionState(val)

	def setSortType(self, type):
		self["list"].setSortType(type)

	def setCurrentRef(self, path):
		self.current_ref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + path)
		# Magic: this sets extra things to show
		self.current_ref.setName('16384:jpg 16384:png 16384:gif 16384:bmp')

	def reloadList(self, sel = None, home = False):
		self.reload_sel = sel
		self.reload_home = home
		self["waitingtext"].visible = True
		self.pathselectEnabled = False
		self.callLater(self.reloadWithDelay)

	def reloadWithDelay(self):
		if not os.path.isdir(config.movielist.last_videodir.value):
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
		if config.usage.movielist_trashcan.value and os.access(config.movielist.last_videodir.value, os.W_OK):
			trash = Tools.Trashcan.createTrashFolder(config.movielist.last_videodir.value)
		self.loadLocalSettings()
		self["list"].reload(self.current_ref, self.selected_tags)
		self.updateTags()
		title = ""
		if config.usage.setup_level.index >= 2: # expert+
			title += config.movielist.last_videodir.value
		if self.selected_tags is not None:
			title += " - " + ','.join(self.selected_tags)
		self.setTitle(title)
		self.displayMovieOffStatus()
		self.displaySortStatus()
		if not (self.reload_sel and self["list"].moveTo(self.reload_sel)):
			if self.reload_home:
				self["list"].moveToFirstMovie()
		self["freeDiskSpace"].update()
		self["waitingtext"].visible = False
		self.createPlaylist()
		if self.playGoTo:
			if self.isItemPlayable(self.list.getCurrentIndex() + 1):
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
			self.session.openWithCallback(
				self.gotFilename,
				MovieLocationBox,
				_("Please select the movie path..."),
				config.movielist.last_videodir.value
			)

	def gotFilename(self, res, selItem = None):
		if not res:
			return
		# serviceref must end with /
		if not res.endswith('/'):
			res += '/'
		currentDir = config.movielist.last_videodir.value
		if res != currentDir:
			if os.path.isdir(res):
				config.movielist.last_videodir.value = res
				config.movielist.last_videodir.save()
				self.loadLocalSettings()
				self.setCurrentRef(res)
				self["freeDiskSpace"].path = res
				self["TrashcanSize"].update(res)
				if selItem:
					self.reloadList(home = True, sel = selItem)
				else:
					self.reloadList(home = True, sel = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + currentDir))
			else:
				mbox=self.session.open(
					MessageBox,
					_("Directory %s does not exist.") % res,
					type = MessageBox.TYPE_ERROR,
					timeout = 5
					)
				mbox.setTitle(self.getTitle())

	def showAll(self):
		self.selected_tags_ele = None
		self.selected_tags = None
		self.saveconfig()
		self.reloadList(home = True)

	def showTagsN(self, tagele):
		if not self.tags:
			self.showTagWarning()
		elif not tagele or (self.selected_tags and tagele.value in self.selected_tags) or not tagele.value in self.tags:
			self.showTagsMenu(tagele)
		else:
			self.selected_tags_ele = tagele
			self.selected_tags = self.tags[tagele.value]
			self.reloadList(home = True)

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
			if tag[1] is None: # all
				self.showAll()
				return
			# TODO: Some error checking maybe, don't wanna crash on KeyError
			self.selected_tags = self.tags[tag[0]]
			if self.selected_tags_ele:
				self.selected_tags_ele.value = tag[0]
				self.selected_tags_ele.save()
			self.saveconfig()
			self.reloadList(home = True)

	def showTagsMenu(self, tagele):
		self.selected_tags_ele = tagele
		lst = [(_("show all tags"), None)] + [(tag, self.getTagDescription(tag)) for tag in sorted(self.tags)]
		self.session.openWithCallback(self.tagChosen, ChoiceBox, title=_("Please select tag to filter..."), list = lst, skin_name = "MovieListTags")

	def showTagWarning(self):
		mbox=self.session.open(MessageBox, _("No tags are set on these movies."), MessageBox.TYPE_ERROR)
		mbox.setTitle(self.getTitle())

	def selectMovieLocation(self, title, callback):
		bookmarks = [("("+_("Other")+"...)", None)]
		inlist = []
		for d in config.movielist.videodirs.value:
			d = os.path.normpath(d)
			bookmarks.append((d,d))
			inlist.append(d)
		for p in Components.Harddisk.harddiskmanager.getMountedPartitions():
			d = os.path.normpath(p.mountpoint)
			if d != '/':
				if d in inlist:
					# improve shortcuts to mountpoints
					try:
						bookmarks[bookmarks.index((d,d))] = (p.tabbedDescription(), d)
					except:
						pass
				else:
					bookmarks.append((p.tabbedDescription(), d))
				inlist.append(d)
		for d in last_selected_dest:
			if d not in inlist:
				bookmarks.append((d,d))
		self.onMovieSelected = callback
		self.movieSelectTitle = title
		self.session.openWithCallback(self.gotMovieLocation, ChoiceBox, title=title, list = bookmarks)

	def gotMovieLocation(self, choice):
		if not choice:
			# cancelled
			self.onMovieSelected(None)
			del self.onMovieSelected
			return
		if isinstance(choice, tuple):
			if choice[1] is None:
				# Display full browser, which returns string
				self.session.openWithCallback(
					self.gotMovieLocation,
					MovieLocationBox,
					self.movieSelectTitle,
					config.movielist.last_videodir.value
				)
				return
			choice = choice[1]
		choice = os.path.normpath(choice)
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
				path = '...' + path[-40:]
			mbox=self.session.openWithCallback(self.removeBookmark, MessageBox, _("Do you really want to remove your bookmark of %s?") % path)
			mbox.setTitle(self.getTitle())
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
		from Screens.VirtualKeyBoard import VirtualKeyBoard
		self.session.openWithCallback(self.createDirCallback, VirtualKeyBoard,
			title = _("Please enter name of the new directory"),
			text = "")
	def createDirCallback(self, name):
		if not name:
			return
		msg = None
		try:
			path = os.path.join(config.movielist.last_videodir.value, name)
			os.mkdir(path)
			if not path.endswith('/'):
				path += '/'
			self.reloadList(sel = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + path))
		except OSError, e:
			print "Error %s:" % e.errno, e
			if e.errno == 17:
				msg = _("The path %s already exists.") % name
			else:
				msg = _("Error") + '\n' + str(e)
		except Exception, e:
			print "[ML] Unexpected error:", e
			msg = _("Error") + '\n' + str(e)
		if msg:
			mbox=self.session.open(MessageBox, msg, type = MessageBox.TYPE_ERROR, timeout = 5)
			mbox.setTitle(self.getTitle())

	def do_rename(self):
		item = self.getCurrentSelection()
		if not canRename(item):
			return
		if isFolder(item):
			p = os.path.split(item[0].getPath())
			if not p[1]:
				# if path ends in '/', p is blank.
				p = os.path.split(p[0])
			name = p[1]
		else:
			info = item[1]
			name = info.getName(item[0])
		from Screens.VirtualKeyBoard import VirtualKeyBoard
		self.session.openWithCallback(self.renameCallback, VirtualKeyBoard,
			title = _("Rename"),
			text = name)

	def do_decode(self):
		from ServiceReference import ServiceReference
		item = self.getCurrentSelection()
		info = item[1]
		serviceref = ServiceReference(None, reftype = eServiceReference.idDVB, path = item[0].getPath())
		name = info.getName(item[0]) + ' - decoded'
		description = info.getInfoString(item[0], iServiceInformation.sDescription)
		recording = RecordTimer.RecordTimerEntry(serviceref, int(time.time()), int(time.time()) + 3600, name, description, 0, dirname = preferredTimerPath())
		recording.dontSave = True
		recording.autoincrease = True
		recording.setAutoincreaseEnd()
		self.session.nav.RecordTimer.record(recording, ignoreTSC = True)

	def renameCallback(self, name):
		if not name:
			return
		name = name.strip()
		item = self.getCurrentSelection()
		if item and item[0]:
			try:
				path = item[0].getPath().rstrip('/')
				meta = path + '.meta'
				if os.path.isfile(meta):
					metafile = open(meta, "r+")
					sid = metafile.readline()
					oldtitle = metafile.readline()
					rest = metafile.read()
					metafile.seek(0)
					metafile.write("%s%s\n%s" %(sid, name, rest))
					metafile.truncate()
					metafile.close()
					index = self.list.getCurrentIndex()
					info = self.list.list[index]
					if hasattr(info[3], 'txt'):
						info[3].txt = name
					else:
						self.list.invalidateCurrentItem()
					return
				pathname,filename = os.path.split(path)
				newpath = os.path.join(pathname, name)
				msg = None
				print "[ML] rename", path, "to", newpath
				os.rename(path, newpath)
				self.reloadList(sel = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + newpath))
			except OSError, e:
				print "Error %s:" % e.errno, e
				if e.errno == 17:
					msg = _("The path %s already exists.") % name
				else:
					msg = _("Error") + '\n' + str(e)
			except Exception, e:
				import traceback
				print "[ML] Unexpected error:", e
				traceback.print_exc()
				msg = _("Error") + '\n' + str(e)
			if msg:
				mbox=self.session.open(MessageBox, msg, type = MessageBox.TYPE_ERROR, timeout = 5)
				mbox.setTitle(self.getTitle())

	def do_reset(self):
		current = self.getCurrent()
		if current:
			resetMoviePlayState(current.getPath() + ".cuts", current)
			self["list"].invalidateCurrentItem() # trigger repaint

	def do_move(self):
		item = self.getCurrentSelection()
		if canMove(item):
			current = item[0]
			info = item[1]
			if info is None:
				# Special case
				return
			name = info and info.getName(current) or _("this recording")
			path = os.path.normpath(current.getPath())
			# show a more limited list of destinations, no point
			# in showing mountpoints.
			title = _("Select destination for:") + " " + name
			bookmarks = [("("+_("Other")+"...)", None)]
			inlist = []
			# Subdirs
			try:
				base = os.path.split(path)[0]
				for fn in os.listdir(base):
					if not fn.startswith('.'): # Skip hidden things
						d = os.path.join(base, fn)
						if os.path.isdir(d) and (d not in inlist):
							bookmarks.append((fn,d))
							inlist.append(d)
			except Exception, e :
				print "[MovieSelection]", e
			# Last favourites
			for d in last_selected_dest:
				if d not in inlist:
					bookmarks.append((d,d))
			# Other favourites
			for d in config.movielist.videodirs.value:
				d = os.path.normpath(d)
				bookmarks.append((d,d))
				inlist.append(d)
			for p in Components.Harddisk.harddiskmanager.getMountedPartitions():
				d = os.path.normpath(p.mountpoint)
				if d not in inlist:
					bookmarks.append((p.description, d))
					inlist.append(d)
			self.onMovieSelected = self.gotMoveMovieDest
			self.movieSelectTitle = title
			self.session.openWithCallback(self.gotMovieLocation, ChoiceBox, title=title, list=bookmarks)

	def gotMoveMovieDest(self, choice):
		if not choice:
			return
		dest = os.path.normpath(choice)
		try:
			item = self.getCurrentSelection()
			current = item[0]
			if item[1] is None:
				name = None
			else:
				name = item[1].getName(current)
			moveServiceFiles(current, dest, name)
			self["list"].removeService(current)
		except Exception, e:
			mbox=self.session.open(MessageBox, str(e), MessageBox.TYPE_ERROR)
			mbox.setTitle(self.getTitle())

	def do_copy(self):
		item = self.getCurrentSelection()
		if canCopy(item):
			current = item[0]
			info = item[1]
			if info is None:
				# Special case
				return
			name = info and info.getName(current) or _("this recording")
			self.selectMovieLocation(title=_("Select copy destination for:") + " " + name, callback=self.gotCopyMovieDest)

	def gotCopyMovieDest(self, choice):
		if not choice:
			return
		dest = os.path.normpath(choice)
		try:
			item = self.getCurrentSelection()
			current = item[0]
			if item[1] is None:
				name = None
			else:
				name = item[1].getName(current)
			copyServiceFiles(current, dest, name)
		except Exception, e:
			mbox=self.session.open(MessageBox, str(e), MessageBox.TYPE_ERROR)
			mbox.setTitle(self.getTitle())

	def stopTimer(self, timer):
		if timer.isRunning():
			if timer.repeated:
				timer.enable()
				timer.processRepeated(findRunningEvent = False)
				self.session.nav.RecordTimer.doActivate(timer)
			else:
				timer.afterEvent = RecordTimer.AFTEREVENT.NONE
				NavigationInstance.instance.RecordTimer.removeEntry(timer)

	def onTimerChoice(self, choice):
		if isinstance(choice, tuple) and choice[1]:
			choice, timer = choice[1]
			if not choice:
				# cancel
				return
			if "s" in choice:
				self.stopTimer(timer)
			if "d" in choice:
				self.delete(True)

	def do_delete(self):
		self.delete()

	def delete(self, *args):
		if args and (not args[0]):
			# cancelled by user (passing any arg means it's a dialog return)
			return
		item = self.getCurrentSelection()
		current = item[0]
		info = item[1]
		cur_path = os.path.realpath(current.getPath())
		if not os.path.exists(cur_path):
			# file does not exist.
			return
		st = os.stat(cur_path)
		name = info and info.getName(current) or _("this recording")
		are_you_sure = ""
		pathtest = info and info.getName(current)
		if not pathtest:
			return
		if item and isTrashFolder(item[0]):
			# Red button to empty trashcan...
			self.purgeAll()
			return
		if current.flags & eServiceReference.mustDescent:
			files = 0
			subdirs = 0
			if '.Trash' not in cur_path and config.usage.movielist_trashcan.value:
				if isFolder(item):
					are_you_sure = _("Do you really want to move to trashcan ?")
				else:
					args = True
				if args:
					trash = Tools.Trashcan.createTrashFolder(cur_path)
					if trash:
						moveServiceFiles(current, trash, name, allowCopy=True)
						self["list"].removeService(current)
						self.showActionFeedback(_("Deleted") + " " + name)
						return
					else:
						msg = _("Cannot move to trash can") + "\n"
						are_you_sure = _("Do you really want to delete %s ?") % name
				for fn in os.listdir(cur_path):
					if (fn != '.') and (fn != '..'):
						ffn = os.path.join(cur_path, fn)
						if os.path.isdir(ffn):
							subdirs += 1
						else:
							files += 1
				if files or subdirs:
					folder_filename = os.path.split(os.path.split(name)[0])[1]
					mbox=self.session.openWithCallback(self.delete, MessageBox, _("'%s' contains %d file(s) and %d sub-directories.\n") % (folder_filename,files,subdirs) + are_you_sure)
					mbox.setTitle(self.getTitle())
					return
			else:
				if '.Trash' in cur_path:
					are_you_sure = _("Do you really want to permanently remove from trash can ?")
				else:
					are_you_sure = _("Do you really want to delete ?")
				if args:
					try:
						msg = ''
						Tools.CopyFiles.deleteFiles(cur_path, name)
						self["list"].removeService(current)
						self.showActionFeedback(_("Deleted") + " " + name)
						return
					except Exception, e:
						print "[MovieSelection] Weird error moving to trash", e
						msg = _("Cannot delete file") + "\n" + str(e) + "\n"
						return
				for fn in os.listdir(cur_path):
					if (fn != '.') and (fn != '..'):
						ffn = os.path.join(cur_path, fn)
						if os.path.isdir(ffn):
							subdirs += 1
						else:
							files += 1
				if files or subdirs:
					folder_filename = os.path.split(os.path.split(name)[0])[1]
					mbox=self.session.openWithCallback(self.delete, MessageBox, _("'%s' contains %d file(s) and %d sub-directories.\n") % (folder_filename,files,subdirs) + are_you_sure)
					mbox.setTitle(self.getTitle())
					return
				else:
					try:
						os.rmdir(cur_path)
					except Exception, e:
						print "[MovieSelection] Failed delete", e
						self.session.open(MessageBox, _("Delete failed!") + "\n" + str(e), MessageBox.TYPE_ERROR)
					else:
						self["list"].removeService(current)
						self.showActionFeedback(_("Deleted") + " " + name)
		else:
			if not args:
				rec_filename = os.path.split(current.getPath())[1]
				if rec_filename.endswith(".ts"): rec_filename = rec_filename[:-3]
				for timer in NavigationInstance.instance.RecordTimer.timer_list:
					if timer.isRunning() and not timer.justplay and rec_filename in timer.Filename:
						choices = [
							(_("Cancel"), None),
							(_("Stop recording"), ("s", timer)),
							(_("Stop recording and delete"), ("sd", timer))]
						self.session.openWithCallback(self.onTimerChoice, ChoiceBox, title=_("Recording in progress") + ":\n%s" % name, list=choices)
						return
				if time.time() - st.st_mtime < 5:
					if not args:
						are_you_sure = _("Do you really want to delete ?")
						mbox=self.session.openWithCallback(self.delete, MessageBox, _("File appears to be busy.\n") + are_you_sure)
						mbox.setTitle(self.getTitle())
						return
			if '.Trash' not in cur_path and config.usage.movielist_trashcan.value:
				trash = Tools.Trashcan.createTrashFolder(cur_path)
				if trash:
					moveServiceFiles(current, trash, name, allowCopy=True)
					self["list"].removeService(current)
					# Files were moved to .Trash, ok.
					from Screens.InfoBarGenerics import delResumePoint
					delResumePoint(current)
					self.showActionFeedback(_("Deleted") + " " + name)
					return
				else:
					msg = _("Cannot move to trash can") + "\n"
					are_you_sure = _("Do you really want to delete %s ?") % name
			else:
				if '.Trash' in cur_path:
					are_you_sure = _("Do you really want to permamently remove '%s' from trash can ?") % name
				else:
					are_you_sure = _("Do you really want to delete %s ?") % name
				msg = ''
			mbox=self.session.openWithCallback(self.deleteConfirmed, MessageBox, msg + are_you_sure)
			mbox.setTitle(self.getTitle())

	def deleteConfirmed(self, confirmed):
		if not confirmed:
			return
		item = self.getCurrentSelection()
		if item is None:
			return # huh?
		current = item[0]
		info = item[1]
		name = info and info.getName(current) or _("this recording")
		serviceHandler = eServiceCenter.getInstance()
		offline = serviceHandler.offlineOperations(current)
		try:
			if offline is None:
				from enigma import eBackgroundFileEraser
				eBackgroundFileEraser.getInstance().erase(os.path.realpath(current.getPath()))
			else:
				if offline.deleteFromDisk(0):
					raise Exception, "Offline delete failed"
			self["list"].removeService(current)
			from Screens.InfoBarGenerics import delResumePoint
			delResumePoint(current)
			self.showActionFeedback(_("Deleted") + " " + name)
		except Exception, ex:
			mbox=self.session.open(MessageBox, _("Delete failed!") + "\n" + name + "\n" + str(ex), MessageBox.TYPE_ERROR)
			mbox.setTitle(self.getTitle())

	def purgeAll(self):
		recordings = self.session.nav.getRecordings()
		next_rec_time = -1
		if not recordings:
			next_rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
		if recordings or (next_rec_time > 0 and (next_rec_time - time.time()) < 120):
			msg = "\n" + _("Recording(s) are in progress or coming up in few seconds!")
		else:
			msg = ""
		mbox=self.session.openWithCallback(self.purgeConfirmed, MessageBox, _("Permanently delete all recordings in the trash can?") + msg)
		mbox.setTitle(self.getTitle())

	def purgeConfirmed(self, confirmed):
		if not confirmed:
			return
		item = self.getCurrentSelection()
		current = item[0]
		Tools.Trashcan.cleanAll(os.path.split(current.getPath())[0])

	def showNetworkMounts(self):
		import NetworkSetup
		self.session.open(NetworkSetup.NetworkMountsMenu)

	def showDeviceMounts(self):
		from Plugins.Extensions.Infopanel.MountManager import HddMount
		self.session.open(HddMount)

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
		print 'SORT:',config.movielist.moviesort.value
		config.movielist.moviesort.load()
		print 'SORT:',config.movielist.moviesort.value
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
		#descriptions in native languages too long...
		sorttext = l_moviesort[index][2]
		if config.movielist.btn_red.value == "sort": self['key_red'].setText(sorttext)
		if config.movielist.btn_green.value == "sort": self['key_green'].setText(sorttext)
		if config.movielist.btn_yellow.value == "sort": self['key_yellow'].setText(sorttext)
		if config.movielist.btn_blue.value == "sort": self['key_blue'].setText(sorttext)
		self.sorttimer = eTimer()
		self.sorttimer.callback.append(self._updateButtonTexts)
		self.sorttimer.start(3000, True) #time for displaying sorting type just applied
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
		self.session.openWithCallback(self.movieoffMenuCallback, ChoiceBox, title = _("On end of movie"), list = menu, selection = used)

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
					ext = os.path.splitext(path)[1].lower()
					if ext in IMAGE_EXTENSIONS:
						continue
					else:
						items.append(item)

playlist = []
