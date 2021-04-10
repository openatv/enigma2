#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from Plugins.Plugin import PluginDescriptor

# Components
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigYesNo, ConfigText, ConfigDirectory, ConfigSelection, ConfigSet, NoSave, ConfigNothing, ConfigLocations, ConfigSelectionNumber
from Components.Label import Label
from Components.FileTransfer import FileTransferJob, ALL_MOVIE_EXTENSIONS
from Components.Task import job_manager
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Sources.Boolean import Boolean
from Components.Sources.List import List
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent

# Screens
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.Console import Console
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.LocationBox import LocationBox
from Screens.HelpMenu import HelpableScreen
from Screens.TaskList import TaskListScreen
from Screens.MovieSelection import defaultMoviePath
from Screens.InfoBar import InfoBar
from Screens.VirtualKeyBoard import VirtualKeyBoard

# Tools
from Tools.BoundFunction import boundFunction
from Tools.UnitConversions import UnitScaler, UnitMultipliers
from Tools import Notifications

# Various
from enigma import eConsoleAppContainer, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, eTimer

import os
import stat
import string
import re

# System mods
from InputBox import InputBox
from FileList import FileList, MultiFileSelectList, EXTENSIONS

# Addons
from addons.key_actions import key_actions, stat_info
from addons.type_utils import vEditor

MOVIEEXTENSIONS = {"cuts": "movieparts", "meta": "movieparts", "ap": "movieparts", "sc": "movieparts", "eit": "movieparts"}

def _make_filter(media_type):
	return "(?i)^.*\.(" + '|'.join(sorted((ext for ext, type in EXTENSIONS.iteritems() if type == media_type))) + ")$"

def _make_rec_filter():
	return "(?i)^.*\.(" + '|'.join(sorted(["ts"] + [ext == "eit" and ext or "ts." + ext  for ext in MOVIEEXTENSIONS.iterkeys()])) + ")$"

movie = _make_filter("movie")
music = _make_filter("music")
pictures = _make_filter("picture")
records = _make_rec_filter()

dmnapi_py = "/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/addons/dmnapi.py"
##################################

pname = _("File Commander")
pdesc = _("manage local Files")

config.plugins.filecommander = ConfigSubsection()
config.plugins.filecommander.savedir_left = ConfigYesNo(default=False)
config.plugins.filecommander.savedir_right = ConfigYesNo(default=False)
config.plugins.filecommander.add_mainmenu_entry = ConfigYesNo(default=False)
config.plugins.filecommander.add_extensionmenu_entry = ConfigYesNo(default=False)
config.plugins.filecommander.editposition_lineend = ConfigYesNo(default=False)
config.plugins.filecommander.path_default = ConfigDirectory(default="")
config.plugins.filecommander.path_left = ConfigText(default="")
config.plugins.filecommander.path_right = ConfigText(default="")
config.plugins.filecommander.my_extension = ConfigText(default="", visible_width=15, fixed_size=False)
config.plugins.filecommander.extension = ConfigSelection(default="^.*", choices=[("^.*", _("without")), ("myfilter", _("My Extension")), (records, _("Records")), (movie, _("Movie")), (music, _("Music")), (pictures, _("Pictures"))])
config.plugins.filecommander.change_navbutton = ConfigSelection(default="no", choices=[("no", _("No")), ("always", _("Channel button always changes sides")), ("yes", _("Yes"))])
config.plugins.filecommander.input_length = ConfigInteger(default=40, limits=(1, 100))
config.plugins.filecommander.diashow = ConfigInteger(default=5000, limits=(1000, 10000))
config.plugins.filecommander.script_messagelen = ConfigSelectionNumber(default=3, stepwidth=1, min=1, max=10, wraparound=True)
config.plugins.filecommander.script_priority_nice = ConfigSelectionNumber(default=0, stepwidth=1, min=0, max=19, wraparound=True)
config.plugins.filecommander.script_priority_ionice = ConfigSelectionNumber(default=0, stepwidth=3, min=0, max=3, wraparound=True)
config.plugins.filecommander.unknown_extension_as_text = ConfigYesNo(default=False)
config.plugins.filecommander.sortDirs = ConfigSelection(default="0.0", choices=[
				("0.0", _("Name")),
				("0.1", _("Name reverse")),
				("1.0", _("Date")),
				("1.1", _("Date reverse"))])
choicelist = [
				("0.0", _("Name")),
				("0.1", _("Name reverse")),
				("1.0", _("Date")),
				("1.1", _("Date reverse")),
				("2.0", _("Size")), 
				("2.1", _("Size reverse"))]
config.plugins.filecommander.sortFiles_left = ConfigSelection(default="1.1", choices=choicelist)
config.plugins.filecommander.sortFiles_right = ConfigSelection(default="1.1", choices=choicelist)
config.plugins.filecommander.firstDirs = ConfigYesNo(default=True)
config.plugins.filecommander.path_left_selected = ConfigYesNo(default=True)
config.plugins.filecommander.showTaskCompleted_message = ConfigYesNo(default=True)
config.plugins.filecommander.showScriptCompleted_message = ConfigYesNo(default=True)
config.plugins.filecommander.hashes = ConfigSet(key_actions.hashes.keys(), default=["MD5"])
config.plugins.filecommander.bookmarks = ConfigLocations()
config.plugins.filecommander.fake_entry = NoSave(ConfigNothing())

tmpLeft = '%s,%s' %(config.plugins.filecommander.sortDirs.value, config.plugins.filecommander.sortFiles_left.value)
tmpRight = '%s,%s' %(config.plugins.filecommander.sortDirs.value, config.plugins.filecommander.sortFiles_right.value)
config.plugins.filecommander.sortingLeft_tmp = NoSave(ConfigText(default=tmpLeft))
config.plugins.filecommander.sortingRight_tmp = NoSave(ConfigText(default=tmpRight))
config.plugins.filecommander.path_left_tmp = NoSave(ConfigText(default=config.plugins.filecommander.path_left.value))
config.plugins.filecommander.path_right_tmp = NoSave(ConfigText(default=config.plugins.filecommander.path_right.value))

# ####################
# ## Config Screen ###
# ####################
class FileCommanderConfigScreen(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "filecommander", plugin="Extensions/FileCommander")

	def keyOK(self):
		if self["config"].getCurrent()[1] is config.plugins.filecommander.path_default:
			self.session.openWithCallback(self.pathSelected, LocationBox, text=_("Default Folder"), currDir=config.plugins.filecommander.path_default.getValue(), minFree=100)
		else:
			Setup.keyOK(self)

	def pathSelected(self, res):
		if res is not None:
			config.plugins.filecommander.path_default.value = res

def formatSortingTyp(sortDirs, sortFiles):
	sortDirs, reverseDirs = [int(x) for x in sortDirs.split('.')]
	sortFiles, reverseFiles = [int(x) for x in sortFiles.split('.')]
	sD = ('n','d','s')[sortDirs] #name, date, size
	sF = ('n','d','s')[sortFiles]
	rD = ('+','-')[reverseDirs] #normal, reverse
	rF = ('+','-')[reverseFiles]
	return '[D]%s%s[F]%s%s' %(sD,rD,sF,rF)

###################
# ## Main Screen ###
###################

glob_running = False

class FileCommanderScreen(Screen, HelpableScreen, key_actions):
	skin = """
		<screen position="40,80" size="1200,600" title="" >
			<widget name="list_left_head1" position="10,10" size="570,40" font="Regular;18" foregroundColor="#00fff000"/>
			<widget source="list_left_head2" render="Listbox" position="10,50" size="570,20" foregroundColor="#00fff000" selectionDisabled="1" transparent="1" >
				<convert type="TemplatedMultiContent">
					{"template": [
						MultiContentEntryText(pos = (0, 0), size = (115, 20), font = 0, flags = RT_HALIGN_LEFT, text = 1), # index 1 is a symbolic mode
						MultiContentEntryText(pos = (130, 0), size = (90, 20), font = 0, flags = RT_HALIGN_RIGHT, text = 11), # index 11 is the scaled size
						MultiContentEntryText(pos = (235, 0), size = (260, 20), font = 0, flags = RT_HALIGN_LEFT, text = 13), # index 13 is the modification time
						],
						"fonts": [gFont("Regular", 18)],
						"itemHeight": 20,
						"selectionEnabled": False
					}
				</convert>
			</widget>
			<widget name="list_right_head1" position="595,10" size="570,40" font="Regular;18" foregroundColor="#00fff000"/>
			<widget source="list_right_head2" render="Listbox" position="595,50" size="570,20" foregroundColor="#00fff000" selectionDisabled="1" transparent="1" >
				<convert type="TemplatedMultiContent">
					{"template": [
						MultiContentEntryText(pos = (0, 0), size = (115, 20), font = 0, flags = RT_HALIGN_LEFT, text = 1), # index 1 is a symbolic mode
						MultiContentEntryText(pos = (130, 0), size = (90, 20), font = 0, flags = RT_HALIGN_RIGHT, text = 11), # index 11 is the scaled size
						MultiContentEntryText(pos = (235, 0), size = (260, 20), font = 0, flags = RT_HALIGN_LEFT, text = 13), # index 13 is the modification time
						],
						"fonts": [gFont("Regular", 18)],
						"itemHeight": 20,
						"selectionEnabled": False
					}
				</convert>
			</widget>
			<widget name="list_left" position="10,85" size="570,460" scrollbarMode="showOnDemand"/>
			<widget name="list_right" position="595,85" size="570,460" scrollbarMode="showOnDemand"/>
			<widget name="sort_left" position="10,550" size="570,15" halign="center" font="Regular;15" foregroundColor="#00fff000"/>
			<widget name="sort_right" position="595,550" size="570,15" halign="center" font="Regular;15" foregroundColor="#00fff000"/>
			<widget name="key_red" position="100,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_green" position="395,570" size="260,25"  transparent="1" font="Regular;20"/>
			<widget name="key_yellow" position="690,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_blue" position="985,570" size="260,25" transparent="1" font="Regular;20"/>
			<ePixmap position="70,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_red.png" transparent="1" alphatest="on"/>
			<ePixmap position="365,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_green.png" transparent="1" alphatest="on"/>
			<ePixmap position="660,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_yellow.png" transparent="1" alphatest="on"/>
			<ePixmap position="955,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_blue.png" transparent="1" alphatest="on"/>
		</screen>"""

	def __init__(self, session, path_left=None):
		# path_left == "" means device list, whereas path_left == None means saved or default value
		if path_left is None:
			if config.plugins.filecommander.savedir_left.value and config.plugins.filecommander.path_left.value and os.path.isdir(config.plugins.filecommander.path_left.value):
				path_left = config.plugins.filecommander.path_left.value
			elif config.plugins.filecommander.path_default.value and os.path.isdir(config.plugins.filecommander.path_default.value):
				path_left = config.plugins.filecommander.path_default.value

		if config.plugins.filecommander.savedir_right.value and config.plugins.filecommander.path_right.value and os.path.isdir(config.plugins.filecommander.path_right.value):
			path_right = config.plugins.filecommander.path_right.value
		elif config.plugins.filecommander.path_default.value and os.path.isdir(config.plugins.filecommander.path_default.value):
			path_right = config.plugins.filecommander.path_default.value
		else:
			path_right = None

		if path_left and os.path.isdir(path_left) and path_left[-1] != "/":
			path_left += "/"

		if path_right and os.path.isdir(path_right) and path_right[-1] != "/":
			path_right += "/"

		if path_left == "":
			path_left = None
		if path_right == "":
			path_right = None

		self.session = session
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)

		# set filter
		filter = self.fileFilter()

		# disable actions
		self.disableActions_Timer = eTimer()

		self.jobs = 0
		self.jobs_old = 0

		self.updateDirs = set()
		self.containers = []

		# set current folder
		self["list_left_head1"] = Label(path_left)
		self["list_left_head2"] = List()
		self["list_right_head1"] = Label(path_right)
		self["list_right_head2"] = List()

		# set sorting
		sortDirs = config.plugins.filecommander.sortDirs.value
		sortFilesLeft = config.plugins.filecommander.sortFiles_left.value
		sortFilesRight = config.plugins.filecommander.sortFiles_right.value
		firstDirs = config.plugins.filecommander.firstDirs.value

		self["list_left"] = FileList(path_left, matchingPattern=filter, sortDirs=sortDirs, sortFiles=sortFilesLeft, firstDirs=firstDirs)
		self["list_right"] = FileList(path_right, matchingPattern=filter, sortDirs=sortDirs, sortFiles=sortFilesRight, firstDirs=firstDirs)

		sortLeft = formatSortingTyp(sortDirs,sortFilesLeft)
		sortRight = formatSortingTyp(sortDirs,sortFilesRight)
		self["sort_left"] = Label(sortLeft)
		self["sort_right"] = Label(sortRight)

		self["key_red"] = Label(_("Delete"))
		self["key_green"] = Label(_("Move"))
		self["key_yellow"] = Label(_("Copy"))
		self["key_blue"] = Label(_("Rename"))
		self["VKeyIcon"] = Boolean(False)

		self["actions"] = HelpableActionMap(self, ["ChannelSelectBaseActions", "WizardActions", "FileNavigateActions", "MenuActions", "NumberActions", "ColorActions", "InfobarActions", "InfobarTeletextActions", "InfobarSubtitleSelectionActions"], {
			"ok": (self.ok, _("Play/view/edit/install/extract/run file or enter directory")),
			"back": (self.exit, _("Leave File Commander")),
			"menu": (self.goContext, _("Open settings/actions menu")),
			"nextMarker": (self.listRight, _("Activate right-hand file list as source")),
			"prevMarker": (self.listLeft, _("Activate left-hand file list as source")),
			"nextBouquet": (self.listRightB, _("Activate right-hand file list as source")),
			"prevBouquet": (self.listLeftB, _("Activate left-hand file list as source")),
			"1": (self.gomakeDir, _("Create directory/folder")),
			"2": (self.gomakeSym, _("Create user-named symbolic link")),
			"3": (self.gofileStatInfo, _("File/Directory Status Information")),
			"4": (self.call_change_mode, _("Change execute permissions (755/644)")),
			"5": (self.goDefaultfolder, _("Go to bookmarked folder")),
			"6": (self.run_file, self.help_run_file),
			"7": (self.run_ffprobe, self.help_run_ffprobe),
			# "8": (self.run_mediainfo, self.help_run_mediainfo),
			"9": (self.run_hashes, _("Calculate file checksums")),
			"startTeletext": (self.file_viewer, _("View or edit file (if size < 1MB)")),
			"info": (self.openTasklist, _("Show task list")),
			"directoryUp": (self.goParentfolder, _("Go to parent directory")),
			"up": (self.goUp, _("Move up list")),
			"down": (self.goDown, _("Move down list")),
			"left": (self.goLeftB, _("Page up list")),
			"right": (self.goRightB, _("Page down list")),
			"red": (self.goRed, _("Delete file or directory (and all its contents)")),
			"green": (self.goGreen, _("Move file/directory to target directory")),
			"yellow": (self.goYellow, _("Copy file/directory to target directory")),
			"blue": (self.goBlue, _("Rename file/directory")),
			"0": (self.doRefresh, _("Refresh screen")),
			"showMovies": (self.listSelect, _("Enter multi-file selection mode")),
			"subtitleSelection": self.downloadSubtitles,  # Unimplemented
			"redlong": (self.goRedLong, _("Sorting left files by name, date or size")),
			"greenlong": (self.goGreenLong, _("Reverse left file sorting")),
			"yellowlong": (self.goYellowLong, _("Reverse right file sorting")),
			"bluelong": (self.goBlueLong, _("Sorting right files by name, date or size")),
		}, -1)

		global glob_running
		glob_running = True

		if config.plugins.filecommander.path_left_selected:
			self.onLayoutFinish.append(self.listLeft)
		else:
			self.onLayoutFinish.append(self.listRight)

		self.checkJobs_Timer = eTimer()
		self.checkJobs_Timer.callback.append(self.checkJobs_TimerCB)
		#self.onLayoutFinish.append(self.onLayout)
		self.onLayoutFinish.append(self.checkJobs_TimerCB)

	def onLayout(self):
		if self.jobs_old:
			self.checkJobs_Timer.startLongTimer(5)

		if config.plugins.filecommander.extension.value == "^.*":
			filtered = ""
		else:
			filtered = "(*)"

		if self.jobs or self.jobs_old:
			jobs = _("(1 job)") if (self.jobs+self.jobs_old) == 1 else _("(%d jobs)") % (self.jobs+self.jobs_old)
		else:
			jobs = ""
		self.setTitle(pname + " " + filtered + " " + jobs)

	def checkJobs_TimerCB(self):
		self.jobs_old = 0
		for job in job_manager.getPendingJobs():
			if (job.name.startswith(_('copy file')) or job.name.startswith(_('copy folder')) or job.name.startswith(_('move file')) or job.name.startswith(_('move folder'))or job.name.startswith(_('Run script'))):
				self.jobs_old += 1
		self.jobs_old -= self.jobs
		self.onLayout()

	def viewable_file(self):
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		if (filename is None) or (sourceDir is None):
			return None
		longname = sourceDir + filename
		try:
			xfile = os.stat(longname)
			if (xfile.st_size < 1000000):
				return longname
		except:
			pass
		return None

	def file_viewer(self):
		if self.disableActions_Timer.isActive():
			return
		longname = self.viewable_file()
		if longname is not None:
			self.session.open(vEditor, longname)
			self.onFileActionCB(True)

	def exit(self):
		if self.disableActions_Timer.isActive():
			return
		if self["list_left"].getCurrentDirectory() and config.plugins.filecommander.savedir_left.value:
			config.plugins.filecommander.path_left.value = self["list_left"].getCurrentDirectory()
			config.plugins.filecommander.path_left.save()
		else:
			config.plugins.filecommander.path_left.value = config.plugins.filecommander.path_default.value

		if self["list_right"].getCurrentDirectory() and config.plugins.filecommander.savedir_right.value:
			config.plugins.filecommander.path_right.value = self["list_right"].getCurrentDirectory()
			config.plugins.filecommander.path_right.save()
		else:
			config.plugins.filecommander.path_right.value = config.plugins.filecommander.path_default.value

		global glob_running
		glob_running = False

		self.close(self.session, True)

	def ok(self):
		if self.disableActions_Timer.isActive():
			return
		if self.SOURCELIST.canDescent():  # isDir
			self.SOURCELIST.descent()
			self.updateHead()
		else:
			self.onFileAction(self.SOURCELIST, self.TARGETLIST)
			# self.updateHead()
			self.doRefresh()

	def goContext(self):
		if self.disableActions_Timer.isActive():
			return
		dummy_to_translate_in_skin = _("File Commander menu")
		buttons = ("menu", "info") + tuple(string.digits) + ("red", "green", "yellow", "blue")

		# Map the listed button actions to their help texts and
		# build a list of the contexts used by the selected buttons
		actionMap = self["actions"]
		actions = {}
		haveContext = set()
		contexts = []
		for contextEntry in (ce for ce in self.helpList if ce[0] is actionMap):
			for actionEntry in contextEntry[2]:
				button = actionEntry[0]
				text = actionEntry[1]
				if button in buttons and text is not None:
					context = contextEntry[1]
					if context not in haveContext:
						contexts.append(context)
						haveContext.add(context)
					actions[button] = _("Settings...") if button == "menu" else text

		# Create the menu list with the buttons in the order of
		# the "buttons" tuple
		menu = [(button, actions[button]) for button in buttons if button in actions]
		menu += [
			("bullet", self.help_uninstall_file, "uninstall+file"),
			("bullet", self.help_uninstall_ffprobe, "uninstall+ffprobe"),
			# ("bullet", self.help_uninstall_mediainfo, "uninstall+mediainfo"),
		]

		dirname = self.SOURCELIST.getFilename()
		if dirname and dirname.endswith("/"):
			menu += [("bullet", dirname in config.plugins.filecommander.bookmarks.value
								and _("Remove selected folder from bookmarks")
								or	_("Add selected folder to bookmarks"), "bookmark+selected")]
		dirname = self.SOURCELIST.getCurrentDirectory()
		if dirname:
			menu += [("bullet", dirname in config.plugins.filecommander.bookmarks.value
								and _("Remove current folder from bookmarks")
								or	_("Add current folder to bookmarks"), "bookmark+current")]

		self.session.openWithCallback(self.goContextCB, FileCommanderContextMenu, contexts, menu)

	def goContextCB(self, action):
		if action:
			if action == "menu":
				self.goMenu()
			elif action == "uninstall+file":
				self.uninstall_file()
			elif action == "uninstall+ffprobe":
				self.uninstall_ffprobe()
			elif action == "uninstall+mediainfo":
				self.uninstall_mediainfo()
			elif action.startswith("bookmark"):
				self.goBookmark(action.endswith("current"))
			else:
				actions = self["actions"].actions
				if action in actions:
					actions[action]()

	def goMenu(self):
		self.oldFilterSettings = self.filterSettings()
		self.session.openWithCallback(self.goRestart, FileCommanderConfigScreen)

	def goBookmark(self, current):
		dirname = current and self.SOURCELIST.getCurrentDirectory() or self.SOURCELIST.getFilename()
		bookmarks = config.plugins.filecommander.bookmarks.value
		if dirname in bookmarks:
			bookmarks.remove(dirname)
		else:
			bookmarks.insert(0, dirname)
			order = config.misc.pluginlist.fc_bookmarks_order.value
			if dirname not in order:
				order = dirname + "," + order
				config.misc.pluginlist.fc_bookmarks_order.value = order
				config.misc.pluginlist.fc_bookmarks_order.save()
		config.plugins.filecommander.bookmarks.value = bookmarks
		config.plugins.filecommander.bookmarks.save()

	def goDefaultfolder(self):
		if self.disableActions_Timer.isActive():
			return
		bookmarks = config.plugins.filecommander.bookmarks.value
		if not bookmarks:
			if config.plugins.filecommander.path_default.value:
				bookmarks.append(config.plugins.filecommander.path_default.value)
			bookmarks.append('/home/root/')
			bookmarks.append(defaultMoviePath())
			config.plugins.filecommander.bookmarks.value = bookmarks
			config.plugins.filecommander.bookmarks.save()
		bookmarks = [(x, x) for x in bookmarks]
		bookmarks.append((_("Storage devices"), None))
		self.session.openWithCallback(self.locationCB, ChoiceBox, title=_("Select a path"), list=bookmarks, reorderConfig="fc_bookmarks_order")

	def locationCB(self, answer):
		if answer:
			self.SOURCELIST.changeDir(answer[1])
			self.updateHead()

	def goParentfolder(self):
		if self.disableActions_Timer.isActive():
			return
		if self.SOURCELIST.getParentDirectory() != False:
			self.SOURCELIST.changeDir(self.SOURCELIST.getParentDirectory())
			self.updateHead()

	def goRestart(self, *answer):
		if hasattr(self, "oldFilterSettings"):
			if self.oldFilterSettings != self.filterSettings():
				filter = self.fileFilter()
				self["list_left"].matchingPattern = re.compile(filter)
				self["list_right"].matchingPattern = re.compile(filter)
				self.onLayout()
			del self.oldFilterSettings

		sortDirs = config.plugins.filecommander.sortDirs.value
		sortFilesLeft = config.plugins.filecommander.sortFiles_left.value
		sortFilesRight = config.plugins.filecommander.sortFiles_right.value

		self["list_left"].setSortBy(sortDirs, True)
		self["list_right"].setSortBy(sortDirs, True)
		self["list_left"].setSortBy(sortFilesLeft)
		self["list_right"].setSortBy(sortFilesRight)

		self.doRefresh()

	def goLeftB(self):
		if self.disableActions_Timer.isActive():
			return
		if config.plugins.filecommander.change_navbutton.value == 'yes':
			self.listLeft()
		else:
			self.goLeft()

	def goRightB(self):
		if self.disableActions_Timer.isActive():
			return
		if config.plugins.filecommander.change_navbutton.value == 'yes':
			self.listRight()
		else:
			self.goRight()

	def goLeft(self):
		self.SOURCELIST.pageUp()
		self.updateHead()

	def goRight(self):
		self.SOURCELIST.pageDown()
		self.updateHead()

	def goUp(self):
		if self.disableActions_Timer.isActive():
			return
		self.SOURCELIST.up()
		self.updateHead()

	def goDown(self):
		if self.disableActions_Timer.isActive():
			return
		self.SOURCELIST.down()
		self.updateHead()

# ## Multiselect ###
	def listSelect(self):
		if not self.SOURCELIST.getCurrentDirectory() or self.disableActions_Timer.isActive():
			return
		selectedid = self.SOURCELIST.getSelectionID()
		config.plugins.filecommander.path_left_tmp.value = self["list_left"].getCurrentDirectory() or ""
		config.plugins.filecommander.path_right_tmp.value = self["list_right"].getCurrentDirectory() or ""
		config.plugins.filecommander.sortingLeft_tmp.value = self["list_left"].getSortBy()
		config.plugins.filecommander.sortingRight_tmp.value = self["list_right"].getSortBy()
		if self.SOURCELIST == self["list_left"]:
			leftactive = True
		else:
			leftactive = False

		self.session.openWithCallback(self.doRefreshDir, FileCommanderScreenFileSelect, leftactive, selectedid)
		self.updateHead()

	def openTasklist(self):
		if self.disableActions_Timer.isActive():
			return
		self.tasklist = []
		for job in job_manager.getPendingJobs():
			#self.tasklist.append((job, job.name, job.getStatustext(), int(100 * job.progress / float(job.end)), str(100 * job.progress / float(job.end)) + "%"))
			progress = job.getProgress()
			self.tasklist.append((job,job.name,job.getStatustext(),progress,str(progress) + " %"))
		self.session.open(TaskListScreen, self.tasklist)

	def addJob(self, job, updateDirs):
		self.jobs += 1
		self.onLayout()
		self.updateDirs.update(updateDirs)
		if isinstance(job, list):
			container = eConsoleAppContainer()
			container.appClosed.append(self.finishedCB)
			self.containers.append(container)
			retval = container.execute("rm", "rm", "-rf", *job)
			if retval:
				self.finishedCB(retval)
		else:
			job_manager.AddJob(job, onSuccess=self.finishedCB)

	def failCB(self, job, task, problems):
		task.setProgress(100)
		from Screens.Standby import inStandby
		message = job.name + "\n" + _("Error") + ': %s' % (problems[0].getErrorMessage(task))
		messageboxtyp = MessageBox.TYPE_ERROR
		timeout = 0
		if InfoBar.instance and not inStandby:
			InfoBar.instance.openInfoBarMessage(message, messageboxtyp, timeout)
		else:
			Notifications.AddNotification(MessageBox, message, type=messageboxtyp, timeout=timeout)
		if hasattr(self, "jobs"):
			self.finishedCB(None)
		return False

	def finishedCB(self, arg):
		if hasattr(self, "jobs"):
			self.jobs -= 1
			self.onLayout()
			if (self["list_left"].getCurrentDirectory() in self.updateDirs or
				self["list_right"].getCurrentDirectory() in self.updateDirs):
				self.doRefresh()
			if not self.jobs:
				self.updateDirs.clear()
				del self.containers[:]
		if not glob_running and config.plugins.filecommander.showTaskCompleted_message.value:
			for job in job_manager.getPendingJobs():
				if (job.name.startswith(_('copy file')) or job.name.startswith(_('copy folder')) or job.name.startswith(_('move file')) or job.name.startswith(_('move folder'))or job.name.startswith(_('Run script'))):
					return
			from Screens.Standby import inStandby
			message = _("File Commander - all Task's are completed!")
			messageboxtyp = MessageBox.TYPE_INFO
			timeout = 30
			if InfoBar.instance and not inStandby:
				InfoBar.instance.openInfoBarMessage(message, messageboxtyp, timeout)
			else:
				Notifications.AddNotification(MessageBox, message, type=messageboxtyp, timeout=timeout)

	def setSort(self, list, setDirs=False):
		sortDirs, sortFiles = list.getSortBy().split(',')
		if setDirs:
			sort, reverse = [int(x) for x in sortDirs.split('.')]
			sort += 1
			if sort > 1:
				sort = 0
		else:
			sort, reverse = [int(x) for x in sortFiles.split('.')]
			sort += 1
			if sort > 2:
				sort = 0
		return '%d.%d' %(sort, reverse)

	def setReverse(self, list, setDirs=False):
		sortDirs, sortFiles = list.getSortBy().split(',')
		if setDirs:
			sort, reverse = [int(x) for x in sortDirs.split('.')]
		else:
			sort, reverse = [int(x) for x in sortFiles.split('.')]
		reverse += 1
		if reverse > 1:
			reverse = 0
		return '%d.%d' %(sort, reverse)

# ## sorting files left ###
	def goRedLong(self):
		if self.disableActions_Timer.isActive():
			return
		self["list_left"].setSortBy(self.setSort(self["list_left"]))
		self.doRefresh()

# ## reverse sorting files left ###
	def goGreenLong(self):
		if self.disableActions_Timer.isActive():
			return
		self["list_left"].setSortBy(self.setReverse(self["list_left"]))
		self.doRefresh()

# ## reverse sorting files right ###
	def goYellowLong(self):
		if self.disableActions_Timer.isActive():
			return
		self["list_right"].setSortBy(self.setReverse(self["list_right"]))
		self.doRefresh()

# ## sorting files right ###
	def goBlueLong(self):
		if self.disableActions_Timer.isActive():
			return
		self["list_right"].setSortBy(self.setSort(self["list_right"]))
		self.doRefresh()

# ## copy ###
	def goYellow(self):
		if InfoBar.instance and InfoBar.instance.LongButtonPressed or self.disableActions_Timer.isActive():
			return
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		targetDir = self.TARGETLIST.getCurrentDirectory()
		if (filename is None) or (sourceDir is None) or (targetDir is None) or not self.SOURCELIST.getSelectionID():
			return
		warntxt = ""
		if sourceDir not in filename:
			if os.path.exists(targetDir + filename):
				warntxt = _(" - file exist! Overwrite")
			copytext = _("Copy file") + warntxt
		else:
			if os.path.exists(targetDir + filename.split('/')[-2]):
				warntxt = _(" - folder exist! Overwrite")
			copytext = _("Copy folder") + warntxt
		self.session.openWithCallback(self.doCopy, ChoiceBox, title=copytext + "?\n%s\n%s\n%s\n%s\n%s" % (filename, _("from dir"), sourceDir, _("to dir"), targetDir), list=[(_("Yes"), True), (_("No"), False)])

	def doCopy(self, result):
		if result is not None:
			if result[1]:
				filename = self.SOURCELIST.getFilename()
				sourceDir = self.SOURCELIST.getCurrentDirectory()
				targetDir = self.TARGETLIST.getCurrentDirectory()
				updateDirs = [targetDir]
				dst_file = targetDir
				if dst_file.endswith("/") and dst_file != "/":
					targetDir = dst_file[:-1]
				if sourceDir not in filename:
					self.addJob(FileTransferJob(sourceDir + filename, targetDir, False, True, "%s : %s" % (_("copy file"), sourceDir + filename)), updateDirs)
				else:
					self.addJob(FileTransferJob(filename, targetDir, True, True, "%s : %s" % (_("copy folder"), filename)), updateDirs)

# ## delete ###
	def goRed(self):
		if InfoBar.instance and InfoBar.instance.LongButtonPressed or self.disableActions_Timer.isActive():
			return
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		if (filename is None) or (sourceDir is None) or not self.SOURCELIST.getSelectionID():
			return
		if sourceDir not in filename:
			deltext = _("Delete file")
		else:
			deltext = _("Delete folder")
		self.session.openWithCallback(self.doDelete, ChoiceBox, title=deltext + "?\n%s\n%s\n%s" % (filename, _("from dir"), sourceDir), list=[(_("Yes"), True), (_("No"), False)])

	def doDelete(self, result):
		if result is not None:
			if result[1]:
				filename = self.SOURCELIST.getFilename()
				sourceDir = self.SOURCELIST.getCurrentDirectory()
				if sourceDir is None:
					return
				if sourceDir not in filename:
					os.remove(sourceDir + filename)
					self.doRefresh()
				else:
					self.addJob([filename], [sourceDir])

# ## move ###
	def goGreen(self):
		if InfoBar.instance and InfoBar.instance.LongButtonPressed or self.disableActions_Timer.isActive():
			return
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		targetDir = self.TARGETLIST.getCurrentDirectory()
		if (filename is None) or (sourceDir is None) or (targetDir is None) or not self.SOURCELIST.getSelectionID():
			return
		warntxt = ""
		if sourceDir not in filename:
			if os.path.exists(targetDir + filename):
				warntxt = _(" - file exist! Overwrite")
			movetext = _("Move file") + warntxt
		else:
			if os.path.exists(targetDir + filename.split('/')[-2]):
				warntxt = _(" - folder exist! Overwrite")
			movetext = _("Move folder") + warntxt
		self.session.openWithCallback(self.doMove, ChoiceBox, title=movetext + "?\n%s\n%s\n%s\n%s\n%s" % (filename, _("from dir"), sourceDir, _("to dir"), targetDir), list=[(_("Yes"), True), (_("No"), False)])

	def doMove(self, result):
		if result is not None:
			if result[1]:
				filename = self.SOURCELIST.getFilename()
				sourceDir = self.SOURCELIST.getCurrentDirectory()
				targetDir = self.TARGETLIST.getCurrentDirectory()
				if (filename is None) or (sourceDir is None) or (targetDir is None):
					return
				updateDirs = [sourceDir, targetDir]
				dst_file = targetDir
				if dst_file.endswith("/") and dst_file != "/":
					targetDir = dst_file[:-1]
				if sourceDir not in filename:
					self.addJob(FileTransferJob(sourceDir + filename, targetDir, False, False, "%s : %s" % (_("move file"), sourceDir + filename)), updateDirs)
				else:
					self.addJob(FileTransferJob(filename, targetDir, True, False, "%s : %s" % (_("move folder"), filename)), updateDirs)

# ## rename ###
	def goBlue(self):
		if InfoBar.instance and InfoBar.instance.LongButtonPressed or self.disableActions_Timer.isActive():
			return
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		if (filename is None) or (sourceDir is None) or not self.SOURCELIST.getSelectionID():
			return
		filename = os.path.basename(os.path.normpath(filename))
		if not filename:
			self.session.open(MessageBox, _("It's not possible to rename the filesystem root."), type=MessageBox.TYPE_ERROR)
			return
		fname = _("Please enter the new file name")
		if sourceDir in filename:
			fname = _("Please enter the new directory name")
		#length = config.plugins.filecommander.input_length.value
		#self.session.openWithCallback(self.doRename, InputBox, text=filename, visible_width=length, overwrite=False, firstpos_end=True, allmarked=False, title=_("Please enter file/folder name"), windowTitle=_("Rename file"))
		# overwrite : False = insert mode (not overwrite) when InputBox is created
		# firstpos_end : True = cursor at end of text on InputBox creation - False = cursor at start of text on InputBox creation
		# visible_width : if this width is smaller than the skin width, the text will be scrolled if it is too long
		# allmarked : text all selected at InputBox creation or not
		self.session.openWithCallback(self.doRename, VirtualKeyBoard, title=fname, text=filename)

	def doRename(self, newname):
		if newname:
			filename = self.SOURCELIST.getFilename()
			sourceDir = self.SOURCELIST.getCurrentDirectory()
			if (filename is None) or (sourceDir is None) or newname == filename:
				return
			try:
				if sourceDir not in filename:
					os.rename(sourceDir + filename, sourceDir + newname)
					movie, ext = os.path.splitext(filename)
					newmovie, newext = os.path.splitext(newname)
					if ext in ALL_MOVIE_EXTENSIONS and newext in ALL_MOVIE_EXTENSIONS:
						for ext in MOVIEEXTENSIONS:
							try:
								if ext == "eit":
									os.rename(sourceDir + movie + ".eit", sourceDir + newmovie + ".eit")
								else:
									os.rename(sourceDir + filename + "." + ext, sourceDir + newname + "." + ext)
							except:
								pass
				else:
					os.rename(filename, sourceDir + newname)
			except OSError as oe:
				self.session.open(MessageBox, _("Error renaming %s to %s:\n%s") % (filename, newname, oe.strerror), type=MessageBox.TYPE_ERROR)
			self.doRefresh()

	def doRenameCB(self):
		self.doRefresh()

# ## symlink by name ###
	def gomakeSym(self):
		if self.disableActions_Timer.isActive():
			return
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		targetDir = self.TARGETLIST.getCurrentDirectory()
		if targetDir is None or filename is None or not self.SOURCELIST.getSelectionID():
			return
		if filename.startswith("/"):
			if filename == "/":
				filename = "root"
			else:
				filename = os.path.basename(os.path.normpath(filename))
		elif sourceDir is None:
			return
		#self.session.openWithCallback(self.doMakesym, InputBox, text=filename, title=_("Please enter name of the new symlink"), windowTitle=_("New symlink"))
		self.session.openWithCallback(self.doMakesym, VirtualKeyBoard, title=_("Please enter name of the new symlink"), text=filename)

	def doMakesym(self, newname):
		if newname:
			oldname = self.SOURCELIST.getFilename()
			sourceDir = self.SOURCELIST.getCurrentDirectory()
			targetDir = self.TARGETLIST.getCurrentDirectory()
			if targetDir is None or oldname is None:
				return
			if oldname.startswith("/"):
				oldpath = oldname
			elif sourceDir is not None:
				oldpath = os.path.join(sourceDir, oldname)
			else:
				return
			newpath = os.path.join(targetDir, newname)
			try:
				os.symlink(oldpath, newpath)
			except OSError as oe:
				self.session.open(MessageBox, _("Error linking %s to %s:\n%s") % (oldpath, newpath, oe.strerror), type=MessageBox.TYPE_ERROR)
			self.doRefresh()

# ## File/directory information
	def gofileStatInfo(self):
		if self.disableActions_Timer.isActive():
			return
		self.session.open(FileCommanderFileStatInfo, self.SOURCELIST)

# ## symlink by folder ###
	def gomakeSymlink(self):
		if self.disableActions_Timer.isActive():
			return
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		targetDir = self.TARGETLIST.getCurrentDirectory()
		if (filename is None) or (sourceDir is None) or (targetDir is None):
			return
		if sourceDir not in filename:
			movetext = _("Create symlink to file")
		else:
			movetext = _("Symlink to ")
		testfile = filename[:-1]
		if (filename is None) or (sourceDir is None):
			return
		if path.islink(testfile):
			return
		self.session.openWithCallback(self.domakeSymlink, ChoiceBox, title=movetext + " %s in %s" % (filename, targetDir), list=[(_("Yes"), True), (_("No"), False)])

	def domakeSymlink(self, result):
		if result is not None:
			if result[1]:
				filename = self.SOURCELIST.getFilename()
				sourceDir = self.SOURCELIST.getCurrentDirectory()
				targetDir = self.TARGETLIST.getCurrentDirectory()
				if (filename is None) or (sourceDir is None) or (targetDir is None):
					return
				if sourceDir in filename:
					self.session.openWithCallback(self.doRenameCB, Console, title=_("create symlink ..."), cmdlist=(("ln", "-s", filename, targetDir),))

# ## new folder ###
	def gomakeDir(self):
		if self.disableActions_Timer.isActive():
			return
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		if (filename is None) or (sourceDir is None):
			return
		#self.session.openWithCallback(self.doMakedir, InputBox, text="", title=_("Please enter name of the new directory"), windowTitle=_("New folder"))
		self.session.openWithCallback(self.doMakedir, VirtualKeyBoard, title=_("Please enter name of the new directory"), text=_('New folder'))

	def doMakedir(self, newname):
		if newname:
			sourceDir = self.SOURCELIST.getCurrentDirectory()
			if sourceDir is None:
				return
			# self.session.openWithCallback(self.doMakedirCB, Console, title = _("create folder"), cmdlist=["mkdir \"" + sourceDir + newname + "\""])
			try:
				os.mkdir(sourceDir + newname)
			except OSError as oe:
				self.session.open(MessageBox, _("Error creating directory %s:\n%s") % (sourceDir + newname, oe.strerror), type=MessageBox.TYPE_ERROR)
			self.doRefresh()

	def doMakedirCB(self):
		self.doRefresh()

# ## download subtitles ###
	def downloadSubtitles(self):
		if self.disableActions_Timer.isActive():
			return
		testFileName = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		if (testFileName is None) or (sourceDir is None):
			return
		subFile = sourceDir + testFileName
		if (testFileName.endswith(".mpg")) or (testFileName.endswith(".mpeg")) or (testFileName.endswith(".mkv")) or (testFileName.endswith(".m2ts")) or (testFileName.endswith(".vob")) or (testFileName.endswith(".mod")) or (testFileName.endswith(".avi")) or (testFileName.endswith(".mp4")) or (testFileName.endswith(".divx")) or (testFileName.endswith(".mkv")) or (testFileName.endswith(".wmv")) or (testFileName.endswith(".mov")) or (testFileName.endswith(".flv")) or (testFileName.endswith(".3gp")):
			print "[FileCommander] Downloading subtitle for: ", subFile
			# For Future USE

	def subCallback(self, answer=False):
		self.doRefresh()

# ## basic functions ###
	def updateHead(self):
		for side in ("list_left", "list_right"):
			dir = self[side].getCurrentDirectory()
			if dir is not None:
				file = self[side].getFilename() or ''
				if file.startswith(dir):
					pathname = file # subfolder
				elif not dir.startswith(file):
					pathname = dir + file # filepath
				else:
					pathname = dir # parent folder
				self[side + "_head1"].text = pathname
				self[side + "_head2"].updateList(self.statInfo(self[side]))
			else:
				self[side + "_head1"].text = ""
				self[side + "_head2"].updateList(())
		self["VKeyIcon"].boolean = self.viewable_file() is not None

	def doRefreshDir(self, jobs, updateDirs):
		if jobs:
			for job in jobs:
				self.addJob(job, updateDirs)
		self["list_left"].changeDir(config.plugins.filecommander.path_left_tmp.value or None)
		self["list_right"].changeDir(config.plugins.filecommander.path_right_tmp.value or None)
		if self.SOURCELIST == self["list_left"]:
			self["list_left"].selectionEnabled(1)
			self["list_right"].selectionEnabled(0)
		else:
			self["list_left"].selectionEnabled(0)
			self["list_right"].selectionEnabled(1)
		self.updateHead()

	def doRefresh(self):
		if self.disableActions_Timer.isActive():
			return
		sortDirsLeft, sortFilesLeft = self["list_left"].getSortBy().split(',')
		sortDirsRight, sortFilesRight = self["list_right"].getSortBy().split(',')
		sortLeft = formatSortingTyp(sortDirsLeft, sortFilesLeft)
		sortRight = formatSortingTyp(sortDirsRight, sortFilesRight)
		self["sort_left"].setText(sortLeft)
		self["sort_right"].setText(sortRight)

		self.SOURCELIST.refresh()
		self.TARGETLIST.refresh()
		self.updateHead()

	def listRightB(self):
		if self.disableActions_Timer.isActive():
			return
		if config.plugins.filecommander.change_navbutton.value == 'yes':
			self.goLeft()
		elif config.plugins.filecommander.change_navbutton.value == 'always' and self.SOURCELIST == self["list_right"]:
			self.listLeft()
		else:
			self.listRight()

	def listLeftB(self):
		if self.disableActions_Timer.isActive():
			return
		if config.plugins.filecommander.change_navbutton.value == 'yes':
			self.goRight()
		elif config.plugins.filecommander.change_navbutton.value == 'always' and self.SOURCELIST == self["list_left"]:
			self.listRight()
		else:
			self.listLeft()

	def listRight(self):
		if self.disableActions_Timer.isActive():
			return
		self["list_left"].selectionEnabled(0)
		self["list_right"].selectionEnabled(1)
		self.SOURCELIST = self["list_right"]
		self.TARGETLIST = self["list_left"]
		self.updateHead()

	def listLeft(self):
		if self.disableActions_Timer.isActive():
			return
		self["list_left"].selectionEnabled(1)
		self["list_right"].selectionEnabled(0)
		self.SOURCELIST = self["list_left"]
		self.TARGETLIST = self["list_right"]
		self.updateHead()

	def call_change_mode(self):
		if self.disableActions_Timer.isActive():
			return
		self.change_mod(self.SOURCELIST)

# 	def call_onFileAction(self):
# 		self.onFileAction(self.SOURCELIST, self.TARGETLIST)

class FileCommanderContextMenu(Screen):
	skin = """
		<screen name="FileCommanderContextMenu" position="center,center" size="560,570" title="File Commander context menu" backgroundColor="background">
			<widget name="menu" position="fill" itemHeight="30" foregroundColor="white" backgroundColor="background" transparent="0" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, contexts, list):
		Screen.__init__(self, session)
		self.setTitle(_("File Commander context menu"))
		actions = {
			"ok": self.goOk,
			"cancel": self.goCancel,
		}
		menu = []
		if ["OkCancelActions"] not in contexts:
			contexts = ["OkCancelActions"] + contexts

		for item in list:
			button = item[0]
			text = item[1]
			if callable(text):
				text = text()
			if text:
				action = item[2] if len(item) > 2 else button
				if button and button not in ("expandable", "expanded", "verticalline", "bullet"):
					actions[button] = boundFunction(self.close, button)
				menu.append(ChoiceEntryComponent(button, (text, action)))

		self["actions"] = ActionMap(contexts, actions)
		self["menu"] = ChoiceList(menu)

	def goOk(self):
		self.close(self["menu"].getCurrent()[0][1])

	def goCancel(self):
		self.close(False)

#####################
# ## Select Screen ###
#####################
class FileCommanderScreenFileSelect(Screen, HelpableScreen, key_actions):
	skin = """
		<screen position="40,80" size="1200,600" title="" >
			<widget name="list_left_head1" position="10,10" size="570,40" font="Regular;18" foregroundColor="#00fff000"/>
			<widget source="list_left_head2" render="Listbox" position="10,50" size="570,20" foregroundColor="#00fff000" selectionDisabled="1" transparent="1" >
				<convert type="TemplatedMultiContent">
					{"template": [
						MultiContentEntryText(pos = (0, 0), size = (115, 20), font = 0, flags = RT_HALIGN_LEFT, text = 1), # index 1 is a symbolic mode
						MultiContentEntryText(pos = (130, 0), size = (90, 20), font = 0, flags = RT_HALIGN_RIGHT, text = 11), # index 11 is the scaled size
						MultiContentEntryText(pos = (235, 0), size = (260, 20), font = 0, flags = RT_HALIGN_LEFT, text = 13), # index 13 is the modification time
						],
						"fonts": [gFont("Regular", 18)],
						"itemHeight": 20,
						"selectionEnabled": False
					}
				</convert>
			</widget>
			<widget name="list_right_head1" position="595,10" size="570,40" font="Regular;18" foregroundColor="#00fff000"/>
			<widget source="list_right_head2" render="Listbox" position="595,50" size="570,20" foregroundColor="#00fff000" selectionDisabled="1" transparent="1" >
				<convert type="TemplatedMultiContent">
					{"template": [
						MultiContentEntryText(pos = (0, 0), size = (115, 20), font = 0, flags = RT_HALIGN_LEFT, text = 1), # index 1 is a symbolic mode
						MultiContentEntryText(pos = (130, 0), size = (90, 20), font = 0, flags = RT_HALIGN_RIGHT, text = 11), # index 11 is the scaled size
						MultiContentEntryText(pos = (235, 0), size = (260, 20), font = 0, flags = RT_HALIGN_LEFT, text = 13), # index 13 is the modification time
						],
						"fonts": [gFont("Regular", 18)],
						"itemHeight": 20,
						"selectionEnabled": False
					}
				</convert>
			</widget>
			<widget name="list_left" position="10,85" size="570,460" scrollbarMode="showOnDemand"/>
			<widget name="list_right" position="595,85" size="570,460" scrollbarMode="showOnDemand"/>
			<widget name="sort_left" position="10,550" size="570,15" halign="center" font="Regular;15" foregroundColor="#00fff000"/>
			<widget name="sort_right" position="595,550" size="570,15" halign="center" font="Regular;15" foregroundColor="#00fff000"/>
			<widget name="key_red" position="100,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_green" position="395,570" size="260,25"  transparent="1" font="Regular;20"/>
			<widget name="key_yellow" position="690,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_blue" position="985,570" size="260,25" transparent="1" font="Regular;20"/>
			<ePixmap position="70,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_red.png" transparent="1" alphatest="on"/>
			<ePixmap position="365,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_green.png" transparent="1" alphatest="on"/>
			<ePixmap position="660,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_yellow.png" transparent="1" alphatest="on"/>
			<ePixmap position="955,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_blue.png" transparent="1" alphatest="on"/>
		</screen>"""

	def __init__(self, session, leftactive, selectedid):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)

		self.selectedFiles = []
		self.selectedid = selectedid

		path_left = config.plugins.filecommander.path_left_tmp.value or None
		path_right = config.plugins.filecommander.path_right_tmp.value or None

		# set sorting
		sortDirsLeft, sortFilesLeft = config.plugins.filecommander.sortingLeft_tmp.value.split(',')
		sortDirsRight, sortFilesRight = config.plugins.filecommander.sortingRight_tmp.value.split(',')
		firstDirs = config.plugins.filecommander.firstDirs.value

		sortLeft = formatSortingTyp(sortDirsLeft,sortFilesLeft)
		sortRight = formatSortingTyp(sortDirsRight,sortFilesRight)
		self["sort_left"] = Label(sortLeft)
		self["sort_right"] = Label(sortRight)

		# set filter
		filter = self.fileFilter()

		# set current folder
		self["list_left_head1"] = Label(path_left)
		self["list_left_head2"] = List()
		self["list_right_head1"] = Label(path_right)
		self["list_right_head2"] = List()

		if leftactive:
			self["list_left"] = MultiFileSelectList(self.selectedFiles, path_left, matchingPattern=filter, sortDirs=sortDirsLeft, sortFiles=sortFilesLeft, firstDirs=firstDirs)
			self["list_right"] = FileList(path_right, matchingPattern=filter, sortDirs=sortDirsRight, sortFiles=sortFilesRight, firstDirs=firstDirs)
			self.SOURCELIST = self["list_left"]
			self.TARGETLIST = self["list_right"]
			self.onLayoutFinish.append(self.listLeft)
		else:
			self["list_left"] = FileList(path_left, matchingPattern=filter, sortDirs=sortDirsLeft, sortFiles=sortFilesLeft, firstDirs=firstDirs)
			self["list_right"] = MultiFileSelectList(self.selectedFiles, path_right, matchingPattern=filter, sortDirs=sortDirsRight, sortFiles=sortFilesRight, firstDirs=firstDirs)
			self.SOURCELIST = self["list_right"]
			self.TARGETLIST = self["list_left"]
			self.onLayoutFinish.append(self.listRight)

		self["key_red"] = Label(_("Delete"))
		self["key_green"] = Label(_("Move"))
		self["key_yellow"] = Label(_("Copy"))
		self["key_blue"] = Label(_("Skip selection"))

		self["actions"] = HelpableActionMap(self, ["ChannelSelectBaseActions", "WizardActions", "FileNavigateActions", "MenuActions", "NumberActions", "ColorActions", "InfobarActions"], {
			"ok": (self.ok, _("Select (source list) or enter directory (target list)")),
			"back": (self.exit, _("Leave multi-select mode")),
			"nextMarker": (self.listRight, _("Activate right-hand file list as multi-select source")),
			"prevMarker": (self.listLeft, _("Activate left-hand file list as multi-select source")),
			"nextBouquet": (self.listRightB, _("Activate right-hand file list as multi-select source")),
			"prevBouquet": (self.listLeftB, _("Activate left-hand file list as multi-select source")),
			"info": (self.openTasklist, _("Show task list")),
			"directoryUp": (self.goParentfolder, _("Go to parent directory")),
			"up": (self.goUp, _("Move up list")),
			"down": (self.goDown, _("Move down list")),
			"left": (self.goLeftB, _("Page up list")),
			"right": (self.goRightB, _("Page down list")),
			"red": (self.goRed, _("Delete the selected files or directories")),
			"green": (self.goGreen, _("Move files/directories to target directory")),
			"yellow": (self.goYellow, _("Copy files/directories to target directory")),
			"blue": (self.goBlue, _("Leave multi-select mode")),
			"0": (self.doRefresh, _("Refresh screen")),
			"showMovies": (self.ok, _("Select")),
		}, -1)
		self.onLayoutFinish.append(self.onLayout)

	def onLayout(self):
		if config.plugins.filecommander.extension.value == "^.*":
			filtered = ""
		else:
			filtered = "(*)"
		self.setTitle(pname + " " + filtered + " " + _("(Selectmode)"))
		self.SOURCELIST.moveToIndex(self.selectedid)
		self.updateHead()

	def changeSelectionState(self):
		if self.ACTIVELIST == self.SOURCELIST:
			self.ACTIVELIST.changeSelectionState()
			self.selectedFiles = self.ACTIVELIST.getSelectedList()
			print "[FileCommander] selectedFiles:", self.selectedFiles
			self.goDown()

	def exit(self, jobs=None, updateDirs=None):
		config.plugins.filecommander.path_left_tmp.value = self["list_left"].getCurrentDirectory() or ""
		config.plugins.filecommander.path_right_tmp.value = self["list_right"].getCurrentDirectory() or ""
		self.close(jobs, updateDirs)

	def ok(self):
		if self.ACTIVELIST == self.SOURCELIST:
			self.changeSelectionState()
		else:
			if self.ACTIVELIST.canDescent():  # isDir
				self.ACTIVELIST.descent()
			self.updateHead()

	def goParentfolder(self):
		if self.ACTIVELIST == self.SOURCELIST:
			return
		if self.ACTIVELIST.getParentDirectory() != False:
			self.ACTIVELIST.changeDir(self.ACTIVELIST.getParentDirectory())
			self.updateHead()

	def goLeftB(self):
		if config.plugins.filecommander.change_navbutton.value == 'yes':
			self.listLeft()
		else:
			self.goLeft()

	def goRightB(self):
		if config.plugins.filecommander.change_navbutton.value == 'yes':
			self.listRight()
		else:
			self.goRight()

	def goLeft(self):
		self.ACTIVELIST.pageUp()
		self.updateHead()

	def goRight(self):
		self.ACTIVELIST.pageDown()
		self.updateHead()

	def goUp(self):
		self.ACTIVELIST.up()
		self.updateHead()

	def goDown(self):
		self.ACTIVELIST.down()
		self.updateHead()

	def openTasklist(self):
		self.tasklist = []
		for job in job_manager.getPendingJobs():
			#self.tasklist.append((job, job.name, job.getStatustext(), int(100 * job.progress / float(job.end)), str(100 * job.progress / float(job.end)) + "%"))
			progress = job.getProgress()
			self.tasklist.append((job,job.name,job.getStatustext(),progress,str(progress) + " %"))
		self.session.open(TaskListScreen, self.tasklist)

# ## delete select ###
	def goRed(self):
		if not len(self.selectedFiles):
			return
		sourceDir = self.SOURCELIST.getCurrentDirectory()

		cnt = 0
		filename = ""
		self.delete_dirs = []
		self.delete_files = []
		self.delete_updateDirs = [self.SOURCELIST.getCurrentDirectory()]
		for file in self.selectedFiles:
			print 'delete: %s' %file
			if not cnt:
				filename += '%s' %file
			elif cnt < 5:
				filename += ', %s' %file
			elif cnt < 6:
				filename += ', ...'
			cnt += 1
			if os.path.isdir(file):
				self.delete_dirs.append(file)
			else:
				self.delete_files.append(file)
		if cnt > 1:
			deltext = _("Delete %d elements") %len(self.selectedFiles)
		else:
			deltext = _("Delete 1 element")
		self.session.openWithCallback(self.doDelete, ChoiceBox, title=deltext + "?\n%s\n%s\n%s" % (filename, _("from dir"), sourceDir), list=[(_("Yes"), True), (_("No"), False)])

	def doDelete(self, result):
		if result is not None:
			if result[1]:
				for file in self.delete_files:
					print 'delete:', file
					os.remove(file)
				self.exit([self.delete_dirs], self.delete_updateDirs)

# ## move select ###
	def goGreen(self):
		targetDir = self.TARGETLIST.getCurrentDirectory()
		if targetDir is None or not len(self.selectedFiles):
			return
		sourceDir = self.SOURCELIST.getCurrentDirectory()

		cnt = 0
		warncnt = 0
		warntxt = ""
		filename = ""
		self.cleanList()
		self.move_updateDirs = [targetDir, self.SOURCELIST.getCurrentDirectory()]
		self.move_jobs = []
		for file in self.selectedFiles:
			if not cnt:
				filename += '%s' %file
			elif cnt < 3:
				filename += ', %s' %file
			elif cnt < 4:
				filename += ', ...'
			cnt += 1
			if os.path.exists(targetDir + '/' + file.rstrip('/').split('/')[-1]):
				warncnt += 1
				if warncnt > 1:
					warntxt = _(" - %d elements exist! Overwrite") %warncnt
				else:
					warntxt = _(" - 1 element exist! Overwrite")
			dst_file = targetDir
			if dst_file.endswith("/") and dst_file != "/":
				targetDir = dst_file[:-1]
			self.move_jobs.append(FileTransferJob(file, targetDir, False, False, "%s : %s" % (_("move file"), file)))
		if cnt > 1:
			movetext = (_("Move %d elements") %len(self.selectedFiles)) + warntxt
		else:
			movetext = _("Move 1 element") + warntxt
		self.session.openWithCallback(self.doMove, ChoiceBox, title=movetext + "?\n%s\n%s\n%s\n%s\n%s" % (filename, _("from dir"), sourceDir, _("to dir"), targetDir), list=[(_("Yes"), True), (_("No"), False)])

	def doMove(self, result):
		if result is not None:
			if result[1]:
				self.exit(self.move_jobs, self.move_updateDirs)

# ## copy select ###
	def goYellow(self):
		targetDir = self.TARGETLIST.getCurrentDirectory()
		if targetDir is None or not len(self.selectedFiles):
			return
		sourceDir = self.SOURCELIST.getCurrentDirectory()

		cnt = 0
		warncnt = 0
		warntxt = ""
		filename = ""
		self.cleanList()
		self.copy_updateDirs = [targetDir]
		self.copy_jobs = []
		for file in self.selectedFiles:
			if not cnt:
				filename += '%s' %file
			elif cnt < 3:
				filename += ', %s' %file
			elif cnt < 4:
				filename += ', ...'
			cnt += 1
			if os.path.exists(targetDir + '/' + file.rstrip('/').split('/')[-1]):
				warncnt += 1
				if warncnt > 1:
					warntxt = _(" - %d elements exist! Overwrite") %warncnt
				else:
					warntxt = _(" - 1 element exist! Overwrite")
			dst_file = targetDir
			if dst_file.endswith("/") and dst_file != "/":
				targetDir = dst_file[:-1]
			if file.endswith("/"):
				self.copy_jobs.append(FileTransferJob(file, targetDir, True, True, "%s : %s" % (_("copy folder"), file)))
			else:
				self.copy_jobs.append(FileTransferJob(file, targetDir, False, True, "%s : %s" % (_("copy file"), file)))
		if cnt > 1:
			copytext = (_("Copy %d elements") %len(self.selectedFiles)) + warntxt
		else:
			copytext = _("Copy 1 element") + warntxt
		self.session.openWithCallback(self.doCopy, ChoiceBox, title=copytext + "?\n%s\n%s\n%s\n%s\n%s" % (filename, _("from dir"), sourceDir, _("to dir"), targetDir), list=[(_("Yes"), True), (_("No"), False)])

	def doCopy(self, result):
		if result is not None:
			if result[1]:
				self.exit(self.copy_jobs, self.copy_updateDirs)

	def goBlue(self):
		self.exit()

# ## basic functions ###
	def updateHead(self):
		for side in ("list_left", "list_right"):
			dir = self[side].getCurrentDirectory()
			if dir is not None:
				file = self[side].getFilename() or ''
				if file.startswith(dir):
					pathname = file # subfolder
				elif not dir.startswith(file):
					pathname = dir + file # filepath
				else:
					pathname = dir # parent folder
				self[side + "_head1"].text = pathname
				self[side + "_head2"].updateList(self.statInfo(self[side]))
			else:
				self[side + "_head1"].text = ""
				self[side + "_head2"].updateList(())

	def doRefresh(self):
		print "[FileCommander] selectedFiles:", self.selectedFiles
		self.SOURCELIST.refresh()
		self.TARGETLIST.refresh()
		self.updateHead()

	def listRightB(self):
		if config.plugins.filecommander.change_navbutton.value == 'yes':
			self.goLeft()
		elif config.plugins.filecommander.change_navbutton.value == 'always' and self.ACTIVELIST == self["list_right"]:
			self.listLeft()
		else:
			self.listRight()

	def listLeftB(self):
		if config.plugins.filecommander.change_navbutton.value == 'yes':
			self.goRight()
		elif config.plugins.filecommander.change_navbutton.value == 'always' and self.ACTIVELIST == self["list_left"]:
			self.listRight()
		else:
			self.listLeft()

	def listRight(self):
		self["list_left"].selectionEnabled(0)
		self["list_right"].selectionEnabled(1)
		self.ACTIVELIST = self["list_right"]
		self.updateHead()

	def listLeft(self):
		self["list_left"].selectionEnabled(1)
		self["list_right"].selectionEnabled(0)
		self.ACTIVELIST = self["list_left"]
		self.updateHead()

	# remove movieparts if the movie is present
	def cleanList(self):
		for file in self.selectedFiles[:]:
			movie, extension = os.path.splitext(file)
			if extension[1:] in MOVIEEXTENSIONS:
				if extension == ".eit":
					extension = ".ts"
					movie += extension
				else:
					extension = os.path.splitext(movie)[1]
				if extension in ALL_MOVIE_EXTENSIONS and movie in self.selectedFiles:
					self.selectedFiles.remove(file)

class FileCommanderFileStatInfo(Screen, stat_info):
	skin = """
		<screen name="FileCommanderFileStatInfo" backgroundColor="un44000000" position="center,center" size="545,345" title="File/Directory Status Information">
			<widget name="filename" position="10,0" size="525,46" font="Regular;20"/>
			<widget source="list" render="Listbox" position="10,60" size="525,275" scrollbarMode="showOnDemand" selectionDisabled="1" transparent="1" >
				<convert type="TemplatedMultiContent">
					{"template": [
						# 0   100 200 300 400 500
						# |   |   |   |   |   |
						# 00000000 1111111111111
						MultiContentEntryText(pos = (0, 0), size = (200, 25), font = 0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is a label
						MultiContentEntryText(pos = (225, 0), size = (300, 25), font = 0, flags = RT_HALIGN_LEFT, text = 1), # index 1 is the information
						],
						"fonts": [gFont("Regular", 20)],
						"itemHeight": 25,
						"selectionEnabled": False
					}
				</convert>
			</widget>
		</screen>
	"""

	SIZESCALER = UnitScaler(scaleTable=UnitMultipliers.Jedec, maxNumLen=3, decimals=1)

	def __init__(self, session, source):
		Screen.__init__(self, session)
		stat_info.__init__(self)

		self.list = []

		self["list"] = List(self.list)
		self["filename"] = Label()
		self["link_sep"] = Label()
		self["link_label"] = Label()
		self["link_value"] = Label()

		self["link_sep"].hide()

		self["actions"] = ActionMap(
			["SetupActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"up": self.pageUp,
				"down": self.pageDown,
			}, prio=-1)

		self.setTitle(_("File/Directory Status Information"))
		self.source = source

		self.onShown.append(self.fillList)

	def pageUp(self):
		if "list" in self:
			self["list"].pageUp()

	def pageDown(self):
		if "list" in self:
			self["list"].pageDown()

	def fillList(self):
		filename = self.source.getFilename()
		sourceDir = self.source.getCurrentDirectory()

		if filename is None:
			self.session.open(MessageBox, _("It is not possible to get the file status of <List of Storage Devices>"), type=MessageBox.TYPE_ERROR)
			self.close()
			return

		if filename.endswith("/"):
			filepath = os.path.normpath(filename)
			if filepath == '/':
				filename = '/'
			else:
				filename = os.path.normpath(filename)
		else:
			filepath = os.path.join(sourceDir, filename)

		filename = os.path.basename(os.path.normpath(filename))
		self["filename"].text = filename
		self.list = []

		try:
			st = os.lstat(filepath)
		except OSError as oe:
			self.session.open(MessageBox, _("%s: %s") % (filepath, oe.strerror), type=MessageBox.TYPE_ERROR)
			self.close()
			return

		mode = st.st_mode
		perms = stat.S_IMODE(mode)
		self.list.append((_("Type:"), self.filetypeStr(mode)))
		self.list.append((_("Owner:"), "%s (%d)" % (self.username(st.st_uid), st.st_uid)))
		self.list.append((_("Group:"), "%s (%d)" % (self.groupname(st.st_gid), st.st_gid)))
		self.list.append((_("Permissions:"), _("%s (%04o)") % (self.fileModeStr(perms), perms)))
		if not (stat.S_ISCHR(mode) or stat.S_ISBLK(mode)):
			self.list.append((_("Size:"), "%s (%sB)" % ("{:n}".format(st.st_size), ' '.join(self.SIZESCALER.scale(st.st_size)))))
		self.list.append((_("Modified:"), self.formatTime(st.st_mtime)))
		self.list.append((_("Accessed:"), self.formatTime(st.st_atime)))
		self.list.append((_("Metadata changed:"), self.formatTime(st.st_ctime)))
		self.list.append((_("Links:"), "%d" % st.st_nlink))
		self.list.append((_("Inode:"), "%d" % st.st_ino))
		self.list.append((_("On device:"), "%d, %d" % ((st.st_dev >> 8) & 0xff, st.st_dev & 0xff)))

		self["list"].updateList(self.list)

		if stat.S_ISLNK(mode):
			self["link_sep"].show()
			self["link_label"].text = _("Link target:")
			try:
				self["link_value"].text = os.readlink(filepath)
			except OSError as oe:
				self["link_value"].text = _("Can't read link contents: %s") % oe.strerror
		else:
			self["link_sep"].hide()
			self["link_label"].text = ""
			self["link_value"].text = ""

# #####################
# ## Start routines ###
# #####################
def filescan_open(list, session, **kwargs):
	path = "/".join(list[0].path.split("/")[:-1]) + "/"
	session.open(FileCommanderScreen, path_left=path)

def start_from_filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	return \
		Scanner(
			mimetypes=None,
			paths_to_scan=[
				ScanPath(path="", with_subdirs=False),
			],
			name=pname,
			description=_("Open with File Commander"),
			openfnc=filescan_open,
		)

def start_from_mainmenu(menuid, **kwargs):
	# starting from main menu
	if menuid == "mainmenu":
		return [(pname, start_from_pluginmenu, "filecommand", 1)]
	return []

def start_from_pluginmenu(session, **kwargs):
	session.openWithCallback(exit, FileCommanderScreen)

def exit(session, result):
	if not result:
		session.openWithCallback(exit, FileCommanderScreen)

def Plugins(path, **kwargs):
	desc_mainmenu = PluginDescriptor(name=pname, description=pdesc, where=PluginDescriptor.WHERE_MENU, fnc=start_from_mainmenu)
	desc_pluginmenu = PluginDescriptor(name=pname, description=pdesc,  where=PluginDescriptor.WHERE_PLUGINMENU, icon="FileCommander.png", fnc=start_from_pluginmenu)
	desc_extensionmenu = PluginDescriptor(name=pname, description=pdesc, where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=start_from_pluginmenu)
	desc_filescan = PluginDescriptor(name=pname, where=PluginDescriptor.WHERE_FILESCAN, fnc=start_from_filescan)
	list = []
	list.append(desc_pluginmenu)
####
# 	buggy
# 	list.append(desc_filescan)
####
	if config.plugins.filecommander.add_extensionmenu_entry.value:
		list.append(desc_extensionmenu)
	if config.plugins.filecommander.add_mainmenu_entry.value:
		list.append(desc_mainmenu)
	return list
