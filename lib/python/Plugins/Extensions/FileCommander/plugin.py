from errno import EEXIST
from grp import getgrgid
from json import loads
from os import R_OK, X_OK, access, chmod, environ, listdir, lstat, mkdir, readlink, remove, rename, rmdir, stat, symlink
from os.path import basename, dirname, exists, getsize, isdir, isfile, islink, join, lexists, normpath, splitext
from pwd import getpwuid
from puremagic import PureError, from_file as fromfile
from re import compile
from string import digits
from stat import S_IFBLK, S_IFCHR, S_IFDIR, S_IFIFO, S_IFLNK, S_IFMT, S_IFREG, S_IFSOCK, S_IMODE, S_ISBLK, S_ISCHR, S_ISLNK, filemode
from tempfile import gettempdir, mkdtemp
from time import localtime, strftime
from twisted.internet.threads import deferToThread

from enigma import eConsoleAppContainer, ePicLoad, ePoint, eServiceReference, eSize, eTimer

from Components.ActionMap import ActionMap, HelpableActionMap, HelpableNumberActionMap
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.config import config, ConfigYesNo, ConfigText, ConfigDirectory, ConfigSelection, ConfigLocations, ConfigSelectionNumber, ConfigSubsection
from Components.Console import Console as console
from Components.FileList import AUDIO_EXTENSIONS, DVD_EXTENSIONS, EXTENSIONS, FILE_PATH, FILE_IS_DIR, FileList, IMAGE_EXTENSIONS, MOVIE_EXTENSIONS, RECORDING_EXTENSIONS
from Components.Harddisk import harddiskmanager
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.PluginComponent import plugins
from Components.ScrollLabel import ScrollLabel
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.Task import Condition, Job, job_manager as JobManager, Task
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.Console import Console
from Screens.DVD import DVDPlayer
from Screens.InfoBar import InfoBar
from Screens.LocationBox import LocationBox
from Screens.MessageBox import MessageBox
from Screens.MovieSelection import defaultMoviePath
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.TaskList import TaskListScreen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.BoundFunction import boundFunction
from Tools.Conversions import NumberScaler
from Tools.Directories import SCOPE_PLUGINS, copyFile, fileReadLines, fileWriteLines, resolveFilename
from Tools.Notifications import AddNotification, AddPopup
from Tools.NumericalTextInput import NumericalTextInput

MODULE_NAME = __name__.split(".")[-1]

PROGRAM_NAME = _("File Commander")
PROGRAM_DESCRIPTION = _("Manage and explore directories and files.")
PROGRAM_VERSION = f"{_("Version")} 4.12"

STORAGE_DEVICES_NAME = f"<{_("List of Storage Devices")}>"
PROTECTED_DIRECTORIES = ("/", "/bin/", "/boot/", "/dev/", "/etc/", "/home/", "/lib/", "/proc/", "/run/", "/sbin/", "/share/", "/sys/", "/tmp/", "/usr/", "/var/")

HASH_CHECK_SIZE = 134217728
MAX_EDIT_SIZE = 1048576
MAX_HEXVIEW_SIZE = 262144
BLOCK_CHUNK_SIZE = 4096
FILE_CHUNK_SIZE = 16384
FILES_TO_LIST = 7

ARCHIVE_FILES = frozenset([x for x, y in EXTENSIONS.items() if y in ("7z", "bz2", "gz", "ipk", "rar", "tar", "xz", "zip")])
MEDIA_FILES = frozenset([x for x, y in EXTENSIONS.items() if y in ("music", "picture", "movie")])
TEXT_FILES = frozenset([x for x, y in EXTENSIONS.items() if y in ("cfg", "html", "log", "lst", "playlist", "py", "sh", "txt", "xml")])

config.plugins.FileCommander = ConfigSubsection()
config.plugins.FileCommander.addToMainMenu = ConfigYesNo(default=False)
config.plugins.FileCommander.addToExtensionMenu = ConfigYesNo(default=False)
config.plugins.FileCommander.useQuickSelect = ConfigYesNo(default=False)
config.plugins.FileCommander.defaultPathLeft = ConfigDirectory(default="")
config.plugins.FileCommander.defaultPathRight = ConfigDirectory(default="")
config.plugins.FileCommander.savePathLeft = ConfigYesNo(default=True)
config.plugins.FileCommander.savePathRight = ConfigYesNo(default=True)
config.plugins.FileCommander.pathLeft = ConfigText(default="")
config.plugins.FileCommander.pathRight = ConfigText(default="")
config.plugins.FileCommander.defaultSide = ConfigSelection(default="Left", choices=[
	("Left", _("Left column")),
	("Right", _("Right column")),
	("Last", _("Last used column"))
])
config.plugins.FileCommander.leftActive = ConfigYesNo(default=True)
config.plugins.FileCommander.directoriesFirst = ConfigYesNo(default=True)
config.plugins.FileCommander.showCurrentDirectory = ConfigYesNo(default=False)
choiceList = [
	("0.0", _("Name ascending")),
	("0.1", _("Name descending")),
	("1.0", _("Date ascending")),
	("1.1", _("Date descending"))
]
config.plugins.FileCommander.sortDirectoriesLeft = ConfigSelection(default="0.0", choices=choiceList)
config.plugins.FileCommander.sortDirectoriesRight = ConfigSelection(default="0.0", choices=choiceList)
choiceList = choiceList + [
	("2.0", _("Size ascending")),
	("2.1", _("Size descending"))
]
config.plugins.FileCommander.sortFilesLeft = ConfigSelection(default="0.0", choices=choiceList)
config.plugins.FileCommander.sortFilesRight = ConfigSelection(default="0.0", choices=choiceList)
default = ["/home/root/", defaultMoviePath()]
if config.plugins.FileCommander.defaultPathLeft.value and config.plugins.FileCommander.defaultPathLeft.value not in default:
	default.append(config.plugins.FileCommander.defaultPathLeft.value)
if config.plugins.FileCommander.defaultPathRight.value and config.plugins.FileCommander.defaultPathRight.value not in default:
	default.append(config.plugins.FileCommander.defaultPathRight.value)
config.plugins.FileCommander.bookmarks = ConfigLocations(default=default)
config.plugins.FileCommander.myExtensions = ConfigText(default="", visible_width=15, fixed_size=False)
config.plugins.FileCommander.extension = ConfigSelection(default="^.*$", choices=[
	("^.*$", _("All files")),
	("myfilter", _("My extensions")),
	(f"(?i)^.*({"|".join(sorted(["\\.ts"] + [x == "\\.eit" and x or f"\\.ts\\.{x}" for x in RECORDING_EXTENSIONS]))})$", _("Recordings")),
	(f"(?i)^.*({"|".join(sorted((f"\\{ext}" for ext, fileType in EXTENSIONS.items() if fileType == "movie")))})$", _("Movies")),
	(f"(?i)^.*({"|".join(sorted((f"\\{ext}" for ext, fileType in EXTENSIONS.items() if fileType == "music")))})$", _("Music")),
	(f"(?i)^.*({"|".join(sorted((f"\\{ext}" for ext, fileType in EXTENSIONS.items() if fileType == "picture")))})$", _("Pictures"))
])
config.plugins.FileCommander.useViewerForUnknown = ConfigYesNo(default=False)
config.plugins.FileCommander.editLineEnd = ConfigYesNo(default=False)
config.plugins.FileCommander.slideshowDelay = ConfigSelection(default=5, choices=[(x, ngettext("%d Second", "%d Seconds", x) % x) for x in range(1, 61)])
config.plugins.FileCommander.slideshowLoop = ConfigYesNo(default=True)
config.plugins.FileCommander.displayStatusTimeout = ConfigSelection(default=3, choices=[(x, ngettext("%d Second", "%d Seconds", x) % x) for x in range(1, 61)])
config.plugins.FileCommander.scriptMessageLength = ConfigSelectionNumber(default=3, stepwidth=1, min=1, max=10, wraparound=True)
config.plugins.FileCommander.scriptPriorityNice = ConfigSelectionNumber(default=0, stepwidth=1, min=0, max=19, wraparound=True)
config.plugins.FileCommander.scriptPriorityIONice = ConfigSelectionNumber(default=0, stepwidth=3, min=0, max=3, wraparound=True)
config.plugins.FileCommander.showTaskCompletedMessage = ConfigYesNo(default=True)
config.plugins.FileCommander.showScriptCompletedMessage = ConfigYesNo(default=True)
config.plugins.FileCommander.completeMessageTimeout = ConfigSelection(default=10, choices=[(x, ngettext("%d Second", "%d Seconds", x) % x) for x in range(1, 61)])
config.plugins.FileCommander.splitJobTasks = ConfigYesNo(default=False)
config.plugins.FileCommander.legacyNavigation = ConfigYesNo(default=True)
config.plugins.FileCommander.autoMultiSelection = ConfigYesNo(default=True)
running = None


class StatInfo:
	@staticmethod
	def username(uid):
		try:
			pwent = getpwuid(uid)
			return pwent.pw_name
		except KeyError:
			return _("Unknown user: %d") % uid

	@staticmethod
	def groupname(gid):
		try:
			grent = getgrgid(gid)
			return grent.gr_name
		except KeyError:
			return _("Unknown group: %d") % gid

	@staticmethod
	def formatTime(time):
		return strftime(f"{config.usage.date.daylong.value} {config.usage.time.long.value}", localtime(time))

	@staticmethod
	def isPackageInstalled(prog):
		path = environ.get("PATH")
		if "/" in prog or not path:
			return access(prog, X_OK)
		for directory in path.split(":"):
			if access(join(directory, prog), X_OK):
				return True
		return False


class FileCommander(Screen, NumericalTextInput, StatInfo):
	skin = """
	<screen name="FileCommander" title="File Commander" position="center,center" size="1200,600" resolution="1280,720">
		<widget source="headleft" render="Listbox" position="0,0" size="590,75" foregroundColor="#00fff000" selection="0">
			<templates>
				<template name="Default" fonts="Regular;20" itemHeight="75">
					<mode name="default">
						<text index="PathName" position="0,0" size="590,50" font="0" horizontalAlignment="left" verticalAlignment="center" wrap="true" />
						<text index="ModeSymbolic" position="0,50" size="120,25" font="0" horizontalAlignment="left" verticalAlignment="center" />
						<text index="SizeScaled" position="130,50" size="130,25" font="0" horizontalAlignment="right" verticalAlignment="center" />
						<text index="TimeModified" position="330,50" size="260,25" font="0" horizontalAlignment="right" verticalAlignment="center" />
					</mode>
				</template>
			</templates>
		</widget>
		<widget name="listleft" position="0,80" size="590,450" />
		<widget name="sortleft" position="0,530" size="590,20" font="Regular;17" foregroundColor="#00fff000" halign="center" />
		<widget source="headright" render="Listbox" position="610,0" size="590,75" foregroundColor="#00fff000" selection="0">
			<templates>
				<template name="Default" fonts="Regular;20" itemHeight="75">
					<mode name="default">
						<text index="PathName" position="0,0" size="590,50" font="0" horizontalAlignment="left" verticalAlignment="center" wrap="true" />
						<text index="ModeSymbolic" position="0,50" size="120,25" font="0" horizontalAlignment="left" verticalAlignment="center" />
						<text index="SizeScaled" position="130,50" size="130,25" font="0" horizontalAlignment="right" verticalAlignment="center" />
						<text index="TimeModified" position="330,50" size="260,25" font="0" horizontalAlignment="right" verticalAlignment="center" />
					</mode>
				</template>
			</templates>
		</widget>
		<widget name="listright" position="610,80" size="590,450" />
		<widget name="sortright" position="610,530" size="590,20" font="Regular;17" foregroundColor="#00fff000" halign="center" />
		<widget name="quickselect" position="0,80" size="590,450" font="Regular;100" foregroundColor="#00fff000" halign="center" transparent="1" valign="center" zPosition="+1" />
		<widget name="status" position="0,515" size="1200,35" font="Regular;25" backgroundColor="#00fff000" borderColor="#00000000" borderWidth="2" foregroundColor="#00ffffff" halign="center" valign="center" zPosition="+1" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="380,e-40" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="570,e-40" size="180,40" backgroundColor="key_blue" conditional="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_menu" render="Label" position="e-260,e-40" size="80,40" backgroundColor="key_back" conditional="key_menu" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_info" render="Label" position="e-170,e-40" size="80,40" backgroundColor="key_back" conditional="key_info" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	OPTIONAL_PACKAGES = {
		"ffmpeg": "ffmpeg",
		"ffprobe": "ffmpeg",
		"mediainfo": "mediainfo"
	}

	def __init__(self, session, pathLeft="", pathRight="", leftActive=None):
		Screen.__init__(self, session, enableHelp=True)
		NumericalTextInput.__init__(self, handleTimeout=False, mode="SearchUpper")
		StatInfo.__init__(self)
		self.multiSelect = None
		self.baseTitle = self.getTitle()
		if not self.baseTitle:
			self.baseTitle = PROGRAM_NAME
			self.setTitle(PROGRAM_NAME)
		if pathLeft and exists(pathLeft):
			config.plugins.FileCommander.pathLeft.value = pathLeft
		if pathRight and exists(pathRight):
			config.plugins.FileCommander.pathRight.value = pathRight
		if leftActive is None:
			leftActive = config.plugins.FileCommander.defaultSide.value == "Left" or (config.plugins.FileCommander.defaultSide.value == "Last" and config.plugins.FileCommander.leftActive.value)
		self.leftActive = leftActive
		fileFilter = self.buildFileFilter()
		self.sortDirectoriesLeft = config.plugins.FileCommander.sortDirectoriesLeft.value
		self.sortDirectoriesRight = config.plugins.FileCommander.sortDirectoriesRight.value
		self.sortFilesLeft = config.plugins.FileCommander.sortFilesLeft.value
		self.sortFilesRight = config.plugins.FileCommander.sortFilesRight.value
		directoriesFirst = config.plugins.FileCommander.directoriesFirst.value
		showCurrentDirectory = config.plugins.FileCommander.showCurrentDirectory.value
		indexNames = {
			"ModeOctal": 0,
			"ModeSymbolic": 1,
			"ModeBoth": 2,
			"Inode": 3,
			"DeviceNumber": 4,
			"Links": 5,
			"UserID": 6,
			"UserName": 7,
			"GroupID": 8,
			"GroupName": 9,
			"SizeFormatted": 10,
			"SizeScaled": 11,
			"SizeBoth": 12,
			"TimeModified": 13,
			"TimeAccessed": 14,
			"TimeCreated": 15,
			"SortOrder": 16,
			"PathName": 17,
			"DirectoryName": 18,
			"FileName": 19,
			"SizeSi": 20,
			"SizeFormattedSi": 21,
			"SizeTec": 22,
			"SizeFormattedTec": 23,
			"CurrentDirectory": 24,
			"CurrentParentDirectory": 25,
			"DirectorySpecial": 26
		}
		self["headleft"] = List(indexNames=indexNames)
		self["listleft"] = FileList("", matchingPattern=fileFilter, sortDirs=self.sortDirectoriesLeft, sortFiles=self.sortFilesLeft, firstDirs=directoriesFirst, showCurrentDirectory=showCurrentDirectory)
		self["listleft"].onSelectionChanged.append(self.selectionChanged)
		self["sortleft"] = Label()
		self["headright"] = List(indexNames=indexNames)
		self["listright"] = FileList("", matchingPattern=fileFilter, sortDirs=self.sortDirectoriesRight, sortFiles=self.sortFilesRight, firstDirs=directoriesFirst, showCurrentDirectory=showCurrentDirectory)
		self["listright"].onSelectionChanged.append(self.selectionChanged)
		self["sortright"] = Label()
		self["quickselect"] = Label()
		self["quickselect"].visible = False
		self["status"] = Label()
		self["status"].visible = False
		self["key_red"] = StaticText()
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["key_menu"] = StaticText(_("MENU"))
		self["key_info"] = StaticText(_("INFO"))
		self["key_text"] = StaticText(_("TEXT"))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "FileCommanderActions", "InfoActions", "ColorActions"], {
			"cancel": (self.keyExit, _("Exit File Commander")),
			"ok": (self.keyOk, _("Enter a directory or process a file (play/view/edit/install/extract/run)")),
			"menu": (self.keyMenu, _("Open context menu (contains settings menu)")),
			"info": (self.keyTaskList, _("Show the task list")),
			"redlong": (self.keySortDirectories, _("Select temporary directory sort order for the current column")),
			"greenlong": (self.keySortFiles, _("Select temporary file sort order for the current column")),
			"yellowlong": (self.keyParent, _("Go to parent directory of the current column")),
			"bluelong": (self.keyRefresh, _("Refresh screen"))
			# "redlong": (self.keySortLeft, _("Sort left column files by name, date or size")),
			# "greenlong": (self.keySortLeftReverse, _("Invert left file sort order")),
			# "yellowlong": (self.keySortRightReverse, _("Invert right file sort order")),
			# "bluelong": (self.keySortRight, _("Sort right column files by name, date or size")),
		}, prio=0, description=_("File Commander Actions"))
		self["navigationActions"] = HelpableActionMap(self, ["NavigationActions"], {
			"top": (self.keyGoTop, _("Move to first line / screen")),
			"pageUp": (self.keyGoPageUp, _("Move up a screen")),
			"up": (self.keyGoLineUp, _("Move up a line")),
			"first": (self.keyGoLeftColumn, _("Switch to the left column")),
			"left": (self.keyGoLeftColumn, _("Switch to the left column")),
			"right": (self.keyGoRightColumn, _("Switch to the right column")),
			"last": (self.keyGoRightColumn, _("Switch to the right column")),
			"down": (self.keyGoLineDown, _("Move down a line")),
			"pageDown": (self.keyGoPageDown, _("Move down a screen")),
			"bottom": (self.keyGoBottom, _("Move to last line / screen"))
		}, prio=0, description=_("File Commander Navigation Actions"))
		self["navigationActions"].setEnabled(not config.plugins.FileCommander.legacyNavigation.value)
		self["legacyNavigationActions"] = HelpableActionMap(self, ["FileCommanderActions", "NavigationActions"], {
			"top": (self.keyGoTop, _("Move to first line / screen")),
			"pageUp": (self.keyToggleColumn, _("Switch to the other column")),
			"up": (self.keyGoLineUp, _("Move up a line")),
			"left": (self.keyGoPageUp, _("Move up a screen")),
			"right": (self.keyGoPageDown, _("Move down a screen")),
			"down": (self.keyGoLineDown, _("Move down a line")),
			"pageDown": (self.keyToggleColumn, _("Switch to the other column")),
			"bottom": (self.keyGoBottom, _("Move to last line / screen")),
			"panelLeft": (self.keyGoLeftColumn, _("Switch to the left column")),
			"panelRight": (self.keyGoRightColumn, _("Switch to the right column"))
		}, prio=0, description=_("File Commander Navigation Actions"))
		self["legacyNavigationActions"].setEnabled(config.plugins.FileCommander.legacyNavigation.value)
		self["multiSelectAction"] = HelpableActionMap(self, ["FileCommanderActions"], {
			"multi": (self.keyMultiSelect, _("Toggle multi-selection mode"))
		}, prio=0, description=_("File Commander Actions"))
		self["selectionActions"] = HelpableActionMap(self, ["FileCommanderActions", "NavigationActions"], {
			"toggle": (self.keyToggleAll, _("Toggle selections")),
			"first": (self.keyDeselectAll, _("Deselect all lines")),
			"last": (self.keySelectAll, _("Select all lines"))
		}, prio=0, description=_("File Commander Selection Actions"))
		self["selectionActions"].setEnabled(self.multiSelect)
		self["textEditViewAction"] = HelpableActionMap(self, ["FileCommanderActions"], {
			"text": (self.keyViewEdit, _("View or edit files less than 1MB in size"))
		}, prio=0, description=_("File Commander Actions"))
		self["deleteAction"] = HelpableActionMap(self, ["ColorActions"], {
			"red": (self.keyDelete, _("Delete directory or file"))
		}, prio=0, description=_("File Commander Actions"))
		self["copyMoveActions"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyMove, _("Move directory/file to target directory")),
			"yellow": (self.keyCopy, _("Copy directory/file to target directory"))
		}, prio=0, description=_("File Commander Actions"))
		self["renameAction"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.keyRename, _("Rename directory/file"))
		}, prio=0, description=_("File Commander Actions"))
		self["alwaysNumberActions"] = HelpableActionMap(self, ["NumberActions"], {
			"5": (self.keySelectBookmark, _("Select a directory from the bookmarks")),
			"8": (self.keyRefresh, _("Refresh screen"))
			# "0": (self.keySelect, _("Toggle the selection"))
			# "0": (self.keyJobTaskTesting, _("Debug code for job and task testing"))
		}, prio=0, description=_("File Commander Actions"))
		self["alwaysNumberActions"].setEnabled(not config.plugins.FileCommander.useQuickSelect.value)
		self["notStorageNumberAction"] = HelpableActionMap(self, ["NumberActions"], {
			"1": (self.keyMakeDirectory, _("Create a directory"))
		}, prio=0, description=_("File Commander Actions"))
		self["notStorageNumberAction"].setEnabled(not config.plugins.FileCommander.useQuickSelect.value)
		self["directoryFileNumberActions"] = HelpableActionMap(self, ["NumberActions"], {
			"2": (self.keyMakeSymlink, _("Create a symbolic link")),
			"3": (self.keyInformation, _("Directory/File status information"))
		}, prio=0, description=_("File Commander Actions"))
		self["directoryFileNumberActions"].setEnabled(not config.plugins.FileCommander.useQuickSelect.value)
		self["fileOnlyNumberActions"] = HelpableActionMap(self, ["NumberActions"], {
			"4": (self.keyChangeMode, _("Change execute permissions (755/644)")),
			"6": (self.keyMediaInfo, self.keyMediaInfoHelp),
			"7": (self.keyFFprobe, self.keyFFprobeHelp),
			"9": (self.keyHashes, _("Calculate file hashes/checksums"))
		}, prio=0, description=_("File Commander Actions"))
		self["fileOnlyNumberActions"].setEnabled(not config.plugins.FileCommander.useQuickSelect.value)
		smsMsg = _("SMS style QuickSelect entry selection")
		self["quickSelectActions"] = HelpableNumberActionMap(self, "NumberActions", {  # Action used by QuickSelect.
			"1": (self.keyNumberGlobal, smsMsg),
			"2": (self.keyNumberGlobal, smsMsg),
			"3": (self.keyNumberGlobal, smsMsg),
			"4": (self.keyNumberGlobal, smsMsg),
			"5": (self.keyNumberGlobal, smsMsg),
			"6": (self.keyNumberGlobal, smsMsg),
			"7": (self.keyNumberGlobal, smsMsg),
			"8": (self.keyNumberGlobal, smsMsg),
			"9": (self.keyNumberGlobal, smsMsg),
			"0": (self.keyNumberGlobal, smsMsg)
		}, prio=0, description=_("QuickSelect Actions"))
		self["quickSelectActions"].setEnabled(config.plugins.FileCommander.useQuickSelect.value)
		self.quickSelectTimer = eTimer()  # Initialize QuickSelect timer.
		self.quickSelectTimer.callback.append(self.quickSelectTimeout)
		self.quickSelectTimerType = 0
		self.quickSelect = ""
		self.quickSelectPos = -1
		self.displayStatusTimer = eTimer()  # Initialize status display timer.
		self.displayStatusTimer.callback.append(self.displayStatusTimeout)
		self.enabledMenuActionMaps = []
		global running
		running = True
		self.onLayoutFinish.append(self.layoutFinished)

	def buildFileFilter(self):
		if config.plugins.FileCommander.extension.value == "myfilter":
			return compile(r"^.*\.(%s)" % "|".join([x.strip() for x in config.plugins.FileCommander.myExtensions.value.split(",")]))
		return compile(config.plugins.FileCommander.extension.value)

	def selectionChanged(self):
		self.updateHeading(self.sourceColumn)
		self.updateButtons()

	def layoutFinished(self):
		def getInitPath(path):
			directory = None  # None means the device list.
			select = None
			if not path.startswith("/"):  # This should be a selection on device list.
				select = f"/{path}"
			elif path.endswith("/") and isdir(path):
				directory = normpath(path)
			elif isfile(path) or isdir(path):
				select = path if isfile(path) else join(path, "")
				directory = dirname(path)
			else:
				directory = dirname(normpath(path))  # Try parent, probably file is removed.
				if not isdir(directory):
					directory = dirname(directory)  # Try one more parent, for dir is removed.
					if not isdir(directory):
						directory = None
			return (directory, select)

		self["headleft"].enableAutoNavigation(False)  # Override listbox navigation.
		self["headright"].enableAutoNavigation(False)  # Override listbox navigation.
		self["listleft"].enableAutoNavigation(False)  # Override listbox navigation.
		self["listright"].enableAutoNavigation(False)  # Override listbox navigation.
		if self.leftActive:
			self.keyGoLeftColumn()
		else:
			self.keyGoRightColumn()
		self["listleft"].changeDir(*getInitPath(config.plugins.FileCommander.pathLeft.value))
		self["listright"].changeDir(*getInitPath(config.plugins.FileCommander.pathRight.value))
		self.updateHeading(self.targetColumn)
		self.updateSort()

	def updateTitle(self):
		if self.multiSelect:
			def dirSize(directory):
				totalSize = getsize(directory)
				for item in listdir(directory):
					path = join(directory, item)
					if isfile(path):
						totalSize += getsize(path)
					elif isdir(path):
						totalSize += dirSize(path)
				return totalSize

			selectedItemCount = 0
			selectedItemsSize = 0
			for selectedItems in self.multiSelect.getSelectedItems():
				selectedItemCount += 1
				if isfile(selectedItems):
					selectedItemsSize += getsize(selectedItems)
				elif isdir(selectedItems):
					selectedItemsSize += dirSize(selectedItems)
			selected = f"  -  {selectedItemCount} Selected  -  {NumberScaler().scale(selectedItemsSize, style="Si", maxNumLen=3, decimals=3)}"
			self.setTitle(f"{PROGRAM_NAME}{selected}")
		else:
			filtered = "" if config.plugins.FileCommander.extension.value == config.plugins.FileCommander.extension.default else "  (*)"
			self.setTitle(f"{PROGRAM_NAME}{filtered}")

	def updateHeading(self, column):
		def buildHeadingData(column):  # Numbers in trailing comments are the template text indexes.
			sort = column.getSortBy().split(",")
			sortDirs, reverseDirs = (int(x) for x in sort[0].split("."))
			sortFiles, reverseFiles = (int(x) for x in sort[1].split("."))
			sortText = f"[D]{('n', 'd', 's')[sortDirs]}{('+', '-')[reverseDirs]}[F]{('n', 'd', 's')[sortFiles]}{('+', '-')[reverseFiles]}"  # (name|date|size)(normal|reverse)
			path = column.getPath()
			currentDirectory = column.getCurrentDirectory()
			currentDirectory = normpath(currentDirectory) if currentDirectory else ""
			splitCurrentParent = _("Current: %s\nParent: %s") % (currentDirectory, dirname(currentDirectory)) if column.getIsSpecialFolder() else path  # 25
			if path:
				path = normpath(path)
				try:
					pathStat = lstat(path)
					symbolicMode = filemode(pathStat.st_mode)
					octalMode = f"{S_IMODE(pathStat.st_mode):04o}"
					modes = (
						octalMode,  # 0
						symbolicMode,  # 1
						f"{octalMode} ({symbolicMode})"  # 2
					)
					size = pathStat.st_size
					formattedSize = f"{size:,}"
					scaledSizes = [NumberScaler().scale(size, style=x, maxNumLen=3, decimals=3) for x in (None, "Si", "Iec")]
					if S_ISCHR(pathStat.st_mode) or S_ISBLK(pathStat.st_mode):
						sizes = ("", "", "")
					else:
						sizes = (
							formattedSize,  # 10
							scaledSizes[0],  # 11
							f"{formattedSize} ({scaledSizes[0]})"  # 12
						)
					data = modes + (
						f"{pathStat.st_ino}",  # 3
						f"{(pathStat.st_dev >> 8) & 0xff}, {pathStat.st_dev & 0xff}",  # 4
						f"{pathStat.st_nlink}",  # 5
						f"{pathStat.st_uid}",  # 6
						self.username(pathStat.st_uid),  # 7
						f"{pathStat.st_gid}",  # 8
						self.groupname(pathStat.st_gid)  # 9
					) + sizes + (
						self.formatTime(pathStat.st_mtime),  # 13
						self.formatTime(pathStat.st_atime),  # 14
						self.formatTime(pathStat.st_ctime),  # 15
						sortText,  # 16
						path,  # 17
						dirname(path),  # 18
						basename(path),  # 19
						scaledSizes[1],  # 20
						f"{formattedSize} ({scaledSizes[1]})",  # 21
						scaledSizes[2],  # 22
						f"{formattedSize} ({scaledSizes[2]})",  # 23
						currentDirectory,  # 24
						splitCurrentParent,  # 25
						currentDirectory if column.getIsSpecialFolder() else f"{currentDirectory}/\u2026/{basename(path)}"  # 26
					)
				except OSError:
					data = ("", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", sortText, path, dirname(path), basename(path), "", "", "", "", currentDirectory, splitCurrentParent, currentDirectory)
			else:
				data = ("", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", sortText, STORAGE_DEVICES_NAME, STORAGE_DEVICES_NAME, STORAGE_DEVICES_NAME, "", "", "", "", currentDirectory, "", currentDirectory)
			return [data]

		self.updateTitle()
		headColumn = self["headleft"] if column == self["listleft"] else self["headright"]
		headColumn.updateList(buildHeadingData(column))

	def updateSort(self):
		def formatSort(columnSort):
			sortDirs, sortFiles = columnSort.split(",")
			sortDirs, reverseDirs = (int(x) for x in sortDirs.split("."))
			sortFiles, reverseFiles = (int(x) for x in sortFiles.split("."))
			sD = (_("name"), _("date"), _("size"))[sortDirs]  # name, date, size
			sF = (_("name"), _("date"), _("size"))[sortFiles]
			rD = ("\u25B2", "\u25BC")[reverseDirs]  # normal, reverse
			rF = ("\u25B2", "\u25BC")[reverseFiles]
			return _("Sort: Directories by %s %s; Files by %s %s.") % (sD, rD, sF, rF)

		self["sortleft"].setText(formatSort(self["listleft"].getSortBy()))
		self["sortright"].setText(formatSort(self["listright"].getSortBy()))

	def updateButtons(self):
		isFileOrFolder = self.sourceColumn.getCurrentDirectory() and self.sourceColumn.getPath() and not self.sourceColumn.getIsSpecialFolder()
		if isFileOrFolder:
			self["key_red"].setText(_("Delete"))
			self["deleteAction"].setEnabled(True)
		else:
			self["key_red"].setText("")
			self["deleteAction"].setEnabled(False)
		if isFileOrFolder and self.targetColumn.getCurrentDirectory() and self.targetColumn.getCurrentDirectory() != self.sourceColumn.getCurrentDirectory():
			self["key_green"].setText(_("Move"))
			self["key_yellow"].setText(_("Copy"))
			self["copyMoveActions"].setEnabled(True)
		else:
			self["key_green"].setText("")
			self["key_yellow"].setText("")
			self["copyMoveActions"].setEnabled(False)
		if isFileOrFolder and self.sourceColumn.multiSelect is False:
			self["key_blue"].setText(_("Rename"))
			self["renameAction"].setEnabled(True)
		else:
			self["key_blue"].setText("")
			self["renameAction"].setEnabled(False)
		if isFileOrFolder and isfile(self.sourceColumn.getPath()) and getsize(self.sourceColumn.getPath()) < MAX_EDIT_SIZE:  # Should we check that this is not a known binary file?
			self["key_text"].setText(_("TEXT"))
			self["textEditViewAction"].setEnabled(True)
		else:
			self["key_text"].setText("")
			self["textEditViewAction"].setEnabled(False)
		directoryFileNumberActions = isFileOrFolder
		notStorageNumberAction = self.sourceColumn.getCurrentDirectory()
		fileOnlyNumberActions = isFileOrFolder and not self.sourceColumn.getIsDir()
		self["multiSelectAction"].setEnabled(self.sourceColumn.getCurrentDirectory())
		self["selectionActions"].setEnabled(self.multiSelect)
		self["directoryFileNumberActions"].setEnabled(directoryFileNumberActions)
		self["notStorageNumberAction"].setEnabled(not config.plugins.FileCommander.useQuickSelect.value and notStorageNumberAction)
		self["fileOnlyNumberActions"].setEnabled(not config.plugins.FileCommander.useQuickSelect.value and fileOnlyNumberActions)
		self.enabledMenuActionMaps = []
		if directoryFileNumberActions:
			self.enabledMenuActionMaps.append("directoryFileNumberActions")
		if notStorageNumberAction:
			self.enabledMenuActionMaps.append("notStorageNumberAction")
		if fileOnlyNumberActions:
			self.enabledMenuActionMaps.append("fileOnlyNumberActions")

	def keyNumberGlobal(self, digit):
		self.quickSelectTimer.stop()
		if self.lastKey != digit:  # Is this a different digit?
			self.nextKey()  # Reset lastKey again so NumericalTextInput triggers its key change.
			self.selectByStart()
			self.quickSelectPos += 1
		char = self.getKey(digit)  # Get char and append to text.
		self.quickSelect = f"{self.quickSelect[:self.quickSelectPos]}{str(char)}"
		self["quickselect"].setText(self.quickSelect)
		self["quickselect"].instance.resize(eSize(self.sourceColumn.instance.size().width(), self.sourceColumn.instance.size().height()))
		self["quickselect"].instance.move(ePoint(self.sourceColumn.instance.position().x(), self.sourceColumn.instance.position().y()))
		self["quickselect"].visible = True
		self.quickSelectTimerType = 0
		self.quickSelectTimer.start(1000, True)  # Allow 1 second to select the desired character for the QuickSelect text.

	def quickSelectTimeout(self, force=False):
		if not force and self.quickSelectTimerType == 0:
			self.selectByStart()
			self.quickSelectTimerType = 1
			self.quickSelectTimer.start(1500, True)  # Allow 1.5 seconds before reseting the QuickSelect text.
		else:  # Timeout QuickSelect
			self.quickSelectTimer.stop()
			self.quickSelect = ""
			self.quickSelectPos = -1
		self.lastKey = -1  # Finalize current character.

	def selectByStart(self):  # Try to select what was typed so far.
		currentDir = self.sourceColumn.getCurrentDirectory()
		if currentDir and self.quickSelect:  # Don't try to select if there is no directory or QuickSelect text.
			self["quickselect"].visible = False
			self["quickselect"].setText("")
			pattern = join(currentDir, self.quickSelect).lower()
			files = self.sourceColumn.getFileList()  # Files returned by getFileList() are absolute paths.
			for index, file in enumerate(files):
				if file[0][0] and file[0][0].lower().startswith(pattern):  # Select first file starting with case insensitive QuickSelect text.
					self.sourceColumn.setCurrentIndex(index)
					break

	def displayStatus(self, message, timeout=config.plugins.FileCommander.displayStatusTimeout.value):
		self["status"].setText(message)
		self["status"].visible = True
		self.displayStatusTimer.startLongTimer(timeout)

	def displayStatusTimeout(self):
		self.displayStatusTimer.stop()
		self["status"].visible = False

	def displayPopUp(self, message, messageType, timeout=config.plugins.FileCommander.completeMessageTimeout.value):
		if config.plugins.FileCommander.showTaskCompletedMessage.value:
			if InfoBar and InfoBar.instance:
				InfoBar.instance.openInfoBarMessage(message, messageType, timeout=timeout)
			else:
				AddPopup(message, messageType, timeout=timeout)  # , id="FileCommander"

	def keyChangeMode(self):
		def changeModeCallback(answer):
			if answer:
				try:
					chmod(path, answer)
				except OSError as err:
					self.session.open(MessageBox, _("Error %d: Unable to set access mode on '%s'!  (%s)") % (err.errno, path, err.strerror), MessageBox.TYPE_ERROR, windowTitle=self.baseTitle)
				self.sourceColumn.refresh()

		path = self.sourceColumn.getPath()
		if self.checkStillExists(path):
			choiceList = [
				(_("Cancel"), 0),
				(_("Reset executable mode (644)"), 0o0644),
				(_("Set executable mode (755)"), 0o0755)
			]
			self.session.openWithCallback(changeModeCallback, MessageBox, text=(_("Do you want change '%s' access mode?") % path), list=choiceList, windowTitle=self.baseTitle)

	def keyCopy(self):
		def checkRelatedCopy():
			if relatedFiles:
				msg = [_("The following files are related to '%s':") % path]
				for file in relatedFiles[2:]:
					if file == path:
						continue
					msg.append(f"- '{basename(file)}'")
				choiceList = [
					(_("Cancel"), ""),
					(_("Copy all related files"), "ALL"),
					(_("Copy only highlighted file"), "CURRENT")
				]
				self.session.openWithCallback(processCopy, MessageBox, "\n".join(msg), list=choiceList, default=2, windowTitle=windowTitle)
			else:
				processCopy("CURRENT")

		def processCopy(answer):
			def processCallback(result):
				if result:
					if config.plugins.FileCommander.splitJobTasks.value:
						for srcPath in srcPaths:
							jobTitle = f"{_('Copy')}: {basename(normpath(srcPath))}"
							JobManager.AddJob(FileCopyTask([srcPath], directory, jobTitle), onSuccess=successCallback, onFail=failCallback)
					else:
						JobManager.AddJob(FileCopyTask(srcPaths, directory, _("File Commander Copy")), onSuccess=successCallback, onFail=failCallback)
					self.displayStatus(_("Copy job queued."))
					if answer == "MULTI":
						self.sourceColumn.clearAllSelections()
					if config.plugins.FileCommander.autoMultiSelection.value and self.multiSelect == self.sourceColumn:
						self.keyMultiSelect()

			if answer:
				if answer == "ALL":
					srcPaths = relatedFiles[2:]
				elif answer == "MULTI":
					srcPaths = selectedItems
				else:
					srcPaths = [path]
				names = [basename(normpath(x)) for x in srcPaths]
				count = len(names)
				if count > FILES_TO_LIST:
					names = names[:FILES_TO_LIST]
					names.append("...")
				if count == 1:
					msg = [_("Copy the directory/file '%s'?") % names[0]]
				else:
					msg = [_("Copy these %d directories/files?") % count]
					for name in names:
						msg.append(f"- '{name}'")
				directory = self.targetColumn.getCurrentDirectory()
				targetNames = [x for x in names if exists(join(directory, x))]
				count = len(targetNames)
				if count > FILES_TO_LIST:
					targetNames = targetNames[:FILES_TO_LIST]
					targetNames.append("...")
				if count:
					msg.append("")
					if count == 1:
						msg.append(_("NOTE: The directory/file '%s' exists and will be overwritten!") % targetNames[0])
					else:
						msg.append(_("NOTE: These %d directories/files exist and will be overwritten!") % count)
						for targetName in targetNames:
							msg.append(f"- '{targetName}'")
				self.session.openWithCallback(processCallback, MessageBox, "\n".join(msg), windowTitle=windowTitle)

		def successCallback(job):
			print(f"[FileCommander] Job '{job.name}' finished.")
			if "status" in self:
				self.displayStatus(_("Copy job completed."))
				newPath = basename(normpath(path))
				if isdir(newPath):
					newPath = join(newPath, "")
				self.targetColumn.refresh(join(self.targetColumn.getCurrentDirectory(), newPath))
			else:
				self.displayPopUp(f"{windowTitle}: {_('Copy job completed.')}", MessageBox.TYPE_INFO)

		def failCallback(job, task, problems):
			problem = "\n".join([x.getErrorMessage(task) for x in problems])
			print(f"[FileCommander] Job '{job.name}', task '{task.name}' failed.\n{problem}")
			if "status" in self:
				self.displayStatus(_("Copy job failed!"))
				newPath = basename(normpath(path))
				if isdir(newPath):
					newPath = join(newPath, "")
				self.targetColumn.refresh(join(self.targetColumn.getCurrentDirectory(), newPath))
			else:
				self.displayPopUp(f"{windowTitle}: {_('Copy job failed!')}", MessageBox.TYPE_ERROR)

		windowTitle = f"{self.baseTitle} - {_('Copy')}"
		path = self.sourceColumn.getPath()
		if self.checkStillExists(path):
			if self.multiSelect == self.sourceColumn:
				selectedItems = self.sourceColumn.getSelectedItems()
				if selectedItems:
					processCopy("MULTI")
				else:
					relatedFiles = self.getRelatedFiles(path)
					checkRelatedCopy()
			else:
				relatedFiles = self.getRelatedFiles(path)
				checkRelatedCopy()

	def keyDelete(self):
		def checkRelatedDelete():
			if relatedFiles:
				msg = [_("The following files are related to '%s':") % path]
				for file in relatedFiles[2:]:
					if file == path:
						continue
					msg.append(f"- '{basename(file)}'")
				choiceList = [
					(_("Cancel"), ""),
					(_("Delete all related files"), "ALL"),
					(_("Delete only highlighted file"), "CURRENT")
				]
				self.session.openWithCallback(processDelete, MessageBox, "\n".join(msg), list=choiceList, default=2, windowTitle=windowTitle)
			else:
				processDelete("CURRENT")

		def processDelete(answer):
			def processCallback(result):
				if result:
					if config.plugins.FileCommander.splitJobTasks.value:
						for srcPath in srcPaths:
							jobTitle = f"{_('Delete')}: {basename(normpath(srcPath))}"
							JobManager.AddJob(FileDeleteTask([srcPath], jobTitle), onSuccess=successCallback, onFail=failCallback)
					else:
						JobManager.AddJob(FileDeleteTask(srcPaths, _("File Commander Delete")), onSuccess=successCallback, onFail=failCallback)
					self.displayStatus(_("Delete job queued."))
					if answer == "MULTI":
						self.sourceColumn.clearAllSelections()
					if config.plugins.FileCommander.autoMultiSelection.value and self.multiSelect == self.sourceColumn:
						self.keyMultiSelect()

			if answer:
				if answer == "ALL":
					srcPaths = relatedFiles[2:]
				elif answer == "MULTI":
					srcPaths = selectedItems
				else:
					srcPaths = [path]
				names = [basename(normpath(x)) for x in srcPaths]
				count = len(names)
				if count > FILES_TO_LIST:
					names = names[:FILES_TO_LIST]
					names.append("...")
				if count == 1:
					msg = [_("Delete the directory/file '%s'?") % names[0]]
				else:
					msg = [_("Delete these %d directories/files?") % count]
					for name in names:
						msg.append(f"- '{name}'")
				self.session.openWithCallback(processCallback, MessageBox, "\n".join(msg), windowTitle=windowTitle)

		def successCallback(job):
			print(f"[FileCommander] Job '{job.name}' finished.")
			if "status" in self:
				self.displayStatus(_("Delete job completed."))
				self.sourceColumn.refresh()
			else:
				self.displayPopUp(f"{windowTitle}: {_('Delete job completed.')}", MessageBox.TYPE_INFO)

		def failCallback(job, task, problems):
			problem = "\n".join([x.getErrorMessage(task) for x in problems])
			print(f"[FileCommander] Job '{job.name}', task '{task.name}' failed.\n{problem}")
			if "status" in self:
				self.displayStatus(_("Delete job failed!"))
				self.sourceColumn.refresh()
			else:
				self.displayPopUp(f"{windowTitle}: {_('Delete job failed!')}", MessageBox.TYPE_ERROR)

		windowTitle = f"{self.baseTitle} - {_('Delete')}"
		path = self.sourceColumn.getPath()
		if self.checkStillExists(path):
			if path in PROTECTED_DIRECTORIES:
				self.session.open(MessageBox, _("Error: The root file system and system directories can't be deleted!"), MessageBox.TYPE_ERROR, windowTitle=windowTitle)
				return
			if self.multiSelect == self.sourceColumn:
				selectedItems = self.sourceColumn.getSelectedItems()
				if selectedItems:
					processDelete("MULTI")
				else:
					relatedFiles = self.getRelatedFiles(path)
					checkRelatedDelete()
			else:
				relatedFiles = self.getRelatedFiles(path)
				checkRelatedDelete()

	def keyDeselectAll(self):
		self.sourceColumn.clearAllSelections()

	def keyExit(self):
		def getSavePath(fileList):
			if not fileList.getCurrentDirectory():  # Device list
				return fileList.getPath()[1:] if fileList.getPath() else ""  # We save the path for selection only without the first /.
			elif fileList.getIsSpecialFolder():
				return fileList.getCurrentDirectory()
			elif fileList.getPath():
				return normpath(fileList.getPath())
		if config.plugins.FileCommander.savePathLeft.value:
			config.plugins.FileCommander.pathLeft.value = getSavePath(self["listleft"])
		else:
			config.plugins.FileCommander.pathLeft.value = config.plugins.FileCommander.defaultPathLeft.value
		if config.plugins.FileCommander.savePathRight.value:
			config.plugins.FileCommander.pathRight.value = getSavePath(self["listright"])
		else:
			config.plugins.FileCommander.pathRight.value = config.plugins.FileCommander.defaultPathRight.value
		config.plugins.FileCommander.leftActive.value = self.leftActive
		config.plugins.FileCommander.pathLeft.save()
		config.plugins.FileCommander.pathRight.save()
		config.plugins.FileCommander.leftActive.save()
		global running
		running = False
		self.close(self.session, True)

	def keyFFprobe(self):
		self.shortcutAction("ffprobe")

	def keyFFprobeHelp(self):
		return self.shortcutHelp("ffprobe")

	def keyGoTop(self):
		self.sourceColumn.goTop()

	def keyGoPageUp(self):
		self.sourceColumn.goPageUp()

	def keyGoLineUp(self):
		self.sourceColumn.goLineUp()

	def keyToggleColumn(self):
		if self.leftActive:
			self.keyGoRightColumn()
		else:
			self.keyGoLeftColumn()

	def keyGoLeftColumn(self):
		self.leftActive = True
		self.sourceColumn = self["listleft"]
		self.targetColumn = self["listright"]
		self.goColumn()

	def keyGoRightColumn(self):
		self.leftActive = False
		self.sourceColumn = self["listright"]
		self.targetColumn = self["listleft"]
		self.goColumn()

	def goColumn(self):
		self.sourceColumn.selectionEnabled(True)
		self.targetColumn.selectionEnabled(False)
		self.updateHeading(self.sourceColumn)
		self.updateButtons()

	def keyGoLineDown(self):
		self.sourceColumn.goLineDown()

	def keyGoPageDown(self):
		self.sourceColumn.goPageDown()

	def keyGoBottom(self):
		self.sourceColumn.goBottom()

	def keyHashes(self, path=None):
		if path is None:
			path = self.sourceColumn.getPath()
		if isfile(path) or islink(path):
			if lstat(path).st_size < HASH_CHECK_SIZE:
				import hashlib
				data = {}
				data["Screen"] = "FileCommanderHashes"
				data["Title"] = _("File Commander Hashes / Checksums")
				data["Description"] = _("File Commander Hash / Checksum Actions")
				textList = [f"{_('File')}:|{path}"]
				textList.append("")
				with open(path, "rb") as fd:
					hashData = {}
					hashItems = ["BLAKE2B", "BLAKE2S", "MD5", "SHA1", "SHA3_224", "SHA3_256", "SHA3_384", "SHA3_512", "SHA224", "SHA256", "SHA384", "SHA512"]
					for algorithm in hashItems:
						hashData[algorithm] = getattr(hashlib, algorithm.lower())()
					while fileBuffer := fd.read(FILE_CHUNK_SIZE):
						for algorithm in hashItems:
							hashData[algorithm].update(fileBuffer)
					for algorithm in hashItems:
						textList.append(f"{algorithm}:|{hashData[algorithm].hexdigest()}")
				data["Data"] = textList
				self.session.open(FileCommanderData, data)
			else:
				self.fileTooBig()

	def keyInformation(self, path=None):
		if path is None:
			path = self.sourceColumn.getPath()
		if self.checkStillExists(path):
			self.session.open(FileCommanderInformation, path, self.targetColumn)

	def keyJobTaskTesting(self):
		def successCallback(job):
			print(f"[FileCommander] Job '{job.name}' finished.")
			if "status" in self:
				self.displayStatus(_("Test job completed."))
			else:
				self.displayPopUp(f"{windowTitle}: {_('Test job completed.')}", MessageBox.TYPE_INFO)

		def failCallback(job, task, problems):
			task.setProgress(100)
			problem = "\n".join([x.getErrorMessage(task) for x in problems])
			print(f"[FileCommander] Job '{job.name}', task '{task.name}' failed.\n{problem}")
			if "status" in self:
				self.displayStatus(_("Test job failed!"))
			else:
				self.displayPopUp(f"{windowTitle}: {_('Test job failed!')}", MessageBox.TYPE_ERROR)

		windowTitle = f"{self.baseTitle} - {_('Test')}"
		job = Job(_("Sleep test"))
		task = Task(job, _("Sleep test"))
		task.postconditions.append(TaskPostConditions())
		task.processStdout = taskProcessStdout
		task.processStderr = taskProcessStderr
		task.setCmdline("/bin/sleep 20 ; ls -l /")
		JobManager.AddJob(job, onSuccess=successCallback, onFail=failCallback)

	def keyMakeDirectory(self):
		def makeDirectoryCallback(newName):
			if newName:
				sourceDirectory = self.sourceColumn.getCurrentDirectory()
				if sourceDirectory:
					newDirectory = join(sourceDirectory, newName, "")
					try:
						mkdir(newDirectory)
					except OSError as err:
						self.session.open(MessageBox, _("Error %d: Unable to create directory '%s'!  (%s)") % (err.errno, newDirectory, err.strerror), MessageBox.TYPE_ERROR, windowTitle=self.baseTitle)
					self.sourceColumn.refresh(newDirectory)

		if self.sourceColumn.getCurrentDirectory():
			self.session.openWithCallback(makeDirectoryCallback, VirtualKeyBoard, title=_("Please enter a name for the new directory:"), text=_("NewDirectory"))

	def keyMakeSymlink(self):
		def makeSymlinkCallback(newName):
			if newName:
				oldPath = path
				newPath = join(self.targetColumn.getCurrentDirectory(), newName)
				try:
					symlink(oldPath, newPath)
				except OSError as err:
					self.session.open(MessageBox, _("Error %d: Unable to link '%s' as '%s'!  (%s)") % (err.errno, oldPath, newPath, err.strerror), MessageBox.TYPE_ERROR, windowTitle=self.baseTitle)
				if isdir(path):
					newPath = join(newPath, "")
				self.targetColumn.refresh(newPath)

		path = self.sourceColumn.getPath()
		if self.checkStillExists(path):
			oldName = basename(normpath(path))
			self.session.openWithCallback(makeSymlinkCallback, VirtualKeyBoard, title=_("Please enter name of the new symbolic link:"), text=oldName)

	def keyManageBookmarks(self, current):
		bookmarks = config.plugins.FileCommander.bookmarks.value
		order = eval(config.misc.pluginlist.fcBookmarksOrder.value)
		directory = current and self.sourceColumn.getCurrentDirectory() or self.sourceColumn.getPath()
		if directory in bookmarks:
			bookmarks.remove(directory)
			if directory in order:
				order.remove(directory)
			self.displayStatus(_("Bookmark removed."))
		else:
			bookmarks.insert(0, directory)
			if directory not in order:
				order.insert(0, directory)
			self.displayStatus(_("Bookmark added."))
		config.plugins.FileCommander.bookmarks.value = bookmarks
		config.plugins.FileCommander.bookmarks.save()
		config.misc.pluginlist.fcBookmarksOrder.value = str(order)
		config.misc.pluginlist.fcBookmarksOrder.save()

	def keyMediaInfo(self):
		self.shortcutAction("mediainfo")

	def keyMediaInfoHelp(self):
		return self.shortcutHelp("mediainfo")

	def keyMenu(self):
		def keyMenuCallback(action):
			if action:
				if action == "menu":
					self.keySettings()
				elif action == "info":
					self.keyTaskList()
				elif action == "selectAll":
					self.sourceColumn.setAllSelections()
				elif action == "deselectAll":
					self.sourceColumn.clearAllSelections()
				elif action == "toggleAll":
					self.sourceColumn.toggleAllSelections()
				elif action.startswith("bookmark+"):
					self.keyManageBookmarks(action.endswith("current"))
				else:
					actions = self["alwaysNumberActions"].actions
					if action in actions:
						actions[action]()
					actions = self["notStorageNumberAction"].actions
					if action in actions:
						actions[action]()
					actions = self["directoryFileNumberActions"].actions
					if action in actions:
						actions[action]()
					actions = self["fileOnlyNumberActions"].actions
					if action in actions:
						actions[action]()

		path = self.sourceColumn.getPath()
		if self.checkStillExists(path):
			buttons = tuple(digits)  # + ("red", "green", "yellow", "blue")
			# Map the listed button actions to their help texts and build a list of the contexts used by the selected buttons.
			actionMaps = [self["alwaysNumberActions"]]
			for enabledActionmaps in self.enabledMenuActionMaps:
				actionMaps.append(self[enabledActionmaps])
			actions = {}
			haveContext = set()
			haveContext.add("MenuActions")
			haveContext.add("InfoActions")
			contexts = ["MenuActions", "InfoActions"]
			for actionMap in actionMaps:
				for contextEntry in (x for x in self.helpList if x[0] is actionMap):
					for actionEntry in contextEntry[2]:
						button = actionEntry[0]
						text = actionEntry[1]
						if button in buttons and text:
							context = contextEntry[1]
							if context not in haveContext:
								contexts.append(context)
								haveContext.add(context)
							actions[button] = text if isinstance(text, str) else text()
			# Create the menu list with the buttons in the order of the "buttons" tuple.
			menu = [
				("menu", _("File Commander settings")),
				("info", _("Show task list"))
			] + [(button, actions[button]) for button in buttons if button in actions]
			directory = self.sourceColumn.getCurrentDirectory()
			if directory:
				menu.append(("bullet", _("Remove current directory from bookmarks") if directory in config.plugins.FileCommander.bookmarks.value else _("Add current directory to bookmarks"), "bookmark+current"))
			if path and path != directory and isdir(path):
				menu.append(("bullet", _("Remove highlighted directory from bookmarks") if path in config.plugins.FileCommander.bookmarks.value else _("Add highlighted directory to bookmarks"), "bookmark+selected"))
			if self.sourceColumn.multiSelect:
				menu.append(("bullet", _("Select all"), "selectAll"))
				menu.append(("bullet", _("Deselect all"), "deselectAll"))
				menu.append(("bullet", _("Toggle selections"), "toggleAll"))
			self.session.openWithCallback(keyMenuCallback, FileCommanderContextMenu, contexts, menu, directory, path)

	def keyMove(self):
		def checkRelatedMove():
			if relatedFiles:
				msg = [_("The following files are related to '%s':") % path]
				for file in relatedFiles[2:]:
					if file == path:
						continue
					msg.append(f"- '{basename(file)}'")
				choiceList = [
					(_("Cancel"), ""),
					(_("Move all related files"), "ALL"),
					(_("Move only highlighted file"), "CURRENT")
				]
				self.session.openWithCallback(processMove, MessageBox, "\n".join(msg), list=choiceList, windowTitle=windowTitle)
			else:
				processMove("CURRENT")

		def processMove(answer):
			def processCallback(result):
				if result:
					if config.plugins.FileCommander.splitJobTasks.value:
						for srcPath in srcPaths:
							jobTitle = f"{_('Move')}: {basename(normpath(srcPath))}"
							JobManager.AddJob(FileMoveTask([srcPath], directory, jobTitle), onSuccess=successCallback, onFail=failCallback)
					else:
						JobManager.AddJob(FileMoveTask(srcPaths, directory, _("File Commander Move")), onSuccess=successCallback, onFail=failCallback)
					self.displayStatus(_("Move job queued."))
					if answer == "MULTI":
						self.sourceColumn.clearAllSelections()
					if config.plugins.FileCommander.autoMultiSelection.value and self.multiSelect == self.sourceColumn:
						self.keyMultiSelect()

			if answer:
				if answer == "ALL":
					srcPaths = relatedFiles[2:]
				elif answer == "MULTI":
					srcPaths = selectedItems
				else:
					srcPaths = [path]
				names = [basename(normpath(x)) for x in srcPaths]
				count = len(names)
				if count > FILES_TO_LIST:
					names = names[:FILES_TO_LIST]
					names.append("...")
				if count == 1:
					msg = [_("Move the directory/file '%s'?") % names[0]]
				else:
					msg = [_("Move these directories/files?")]
					for name in names:
						msg.append(f"- '{name}'")
				targetNames = [x for x in names if exists(join(directory, x))]
				count = len(targetNames)
				if count > FILES_TO_LIST:
					targetNames = targetNames[:FILES_TO_LIST]
					targetNames.append("...")
				if count:
					msg.append("")
					if count == 1:
						msg.append(_("NOTE: The directory/file '%s' exists and will be overwritten!") % targetNames[0])
					else:
						msg.append(_("NOTE: These %d directories/files exist and will be overwritten!") % count)
						for targetName in targetNames:
							msg.append(f"- '{targetName}'")
				self.session.openWithCallback(processCallback, MessageBox, "\n".join(msg), windowTitle=windowTitle)

		def successCallback(job):
			print(f"[FileCommander] Job '{job.name}' finished.")
			if "status" in self:
				self.displayStatus(_("Move job completed."))
				self.sourceColumn.refresh()
				self.targetColumn.refresh(join(self.targetColumn.getCurrentDirectory(), basename(normpath(path))))
				# if startIndex < self.sourceColumn.count():
				# 	self.sourceColumn.setCurrentIndex(startIndex)
				# else:
				# 	self.sourceColumn.goBottom()
			else:
				self.displayPopUp(f"{windowTitle}: {_('Move job completed.')}", MessageBox.TYPE_INFO)

		def failCallback(job, task, problems):
			problem = "\n".join([x.getErrorMessage(task) for x in problems])
			print(f"[FileCommander] Job '{job.name}', task '{task.name}' failed.\n{problem}")
			if "status" in self:
				self.displayStatus(_("Move job failed!"))
				self.sourceColumn.refresh()
				self.targetColumn.refresh(join(self.targetColumn.getCurrentDirectory(), basename(normpath(path))))
			else:
				self.displayPopUp(f"{windowTitle}: {_('Move job failed!')}", MessageBox.TYPE_ERROR)

		windowTitle = f"{self.baseTitle} - {_('Move')}"
		path = self.sourceColumn.getPath()
		if self.checkStillExists(path):
			# startIndex = self.sourceColumn.getCurrentIndex()
			if path in PROTECTED_DIRECTORIES:
				self.session.open(MessageBox, _("Error: The root file system and system directories can't be moved!"), MessageBox.TYPE_ERROR, windowTitle=windowTitle)
				return
			directory = self.targetColumn.getCurrentDirectory()
			if self.multiSelect == self.sourceColumn:
				selectedItems = self.sourceColumn.getSelectedItems()
				if selectedItems:
					processMove("MULTI")
				else:
					relatedFiles = self.getRelatedFiles(path)
					checkRelatedMove()
			else:
				relatedFiles = self.getRelatedFiles(path)
				checkRelatedMove()

	def keyMultiSelect(self):
		if self.multiSelect is None:
			self.multiSelect = self["listleft"] if self.leftActive else self["listright"]
			self.sourceColumn.setMultiSelectMode()
			self.targetColumn.setSingleSelectMode()
		else:
			self.multiSelect.setSingleSelectMode()
			self.multiSelect.clearAllSelections()  # Clearing the selection list should be removed when multi selection across directories is enabled.
			self.multiSelect = None
		self.updateTitle()
		self.updateButtons()

	def keyOk(self):
		def archiveCallback(answer):
			if answer:
				path = self.sourceColumn.getPath()
				if answer == "VIEW":
					self.session.open(FileCommanderArchiveView, path)
				elif answer == "EXTRACT":
					self.session.open(FileCommanderArchiveExtract, path, self.targetColumn)
				elif answer == "INSTALL":
					self.session.open(FileCommanderArchiveInstall, path, self.targetColumn)

		def imageCallback(index=0):
			self.sourceColumn.setCurrentIndex(index)

		def musicCallback(answer):
			if answer:
				from Plugins.Extensions.MediaPlayer.plugin import MediaPlayer
				path = self.sourceColumn.getPath()
				mediaPlayer = self.session.open(MediaPlayer)
				mediaPlayer.playlist.clear()
				mediaPlayer.savePlaylistOnExit = False
				fileList = self.sourceColumn.getFileList() if answer == "LIST" else [self.sourceColumn.getCurrent()]
				elements = len(fileList[0])
				currentIndex = 0
				index = 0
				for fileData in fileList:
					audioPath = fileData[0][FILE_PATH] if elements > 1 else fileData[4]
					extension = splitext(audioPath)[1].lower() if audioPath and not fileData[0][FILE_IS_DIR] else None
					if extension and extension in AUDIO_EXTENSIONS:
						mediaPlayer.playlist.addFile(eServiceReference(4097, 0, audioPath))
						if audioPath.endswith(basename(path)):
							currentIndex = index
						index += 1
				mediaPlayer.changeEntry(currentIndex)
				mediaPlayer.switchToPlayList()

		def mviCallback(answer=None):
			def processImage(data, retVal, extraArgs):
				def cleanUp(index):
					if not filePreExists:
						remove(imagePath)

				# print(f"[FileCommander] processImage DEBUG: Return value is {retVal}\n{data}.")
				answer, path, imagePath, filePreExists = extraArgs
				if retVal == 0:
					if not filePreExists:
						chmod(imagePath, 0o644)
					if "SHOW" in answer:
						if "SAVE" in answer or "TARGET" in answer:
							self.session.open(FileCommanderImageViewer, imagePath, 0, None, basename(imagePath))
						else:
							self.session.openWithCallback(cleanUp, FileCommanderImageViewer, imagePath, 0, None, basename(imagePath))

			if answer:
				path = self.sourceColumn.getPath()
				imagePath = join(self.targetColumn.getCurrentDirectory() if "TARGET" in answer else gettempdir(), f"{splitext(basename(path))[0]}.jpg")
				filePreExists = exists(imagePath)
				console().ePopen(["/usr/bin/ffmpeg", "/usr/bin/ffmpeg", "-y", "-hide_banner", "-f", "mpegvideo", "-i", path, "-frames:v", "1", "-r", "1/1", imagePath], processImage, (answer, path, imagePath, filePreExists))

		def scriptCallback(answer):
			def successCallback(job):
				if running and config.plugins.FileCommander.showTaskCompletedMessage.value:
					from Screens.Standby import inStandby
					message = _("File Commander - All tasks are complete.")
					if InfoBar.instance and not inStandby:
						InfoBar.instance.openInfoBarMessage(message, MessageBox.TYPE_INFO, timeout=config.plugins.FileCommander.completeMessageTimeout.value)
					else:
						AddNotification(MessageBox, message, MessageBox.TYPE_INFO, timeout=config.plugins.FileCommander.completeMessageTimeout.value)

			def failCallback(job, task, problems):
				task.setProgress(100)
				from Screens.Standby import inStandby
				message = f"{job.name}\n{_('Error')}: {problems[0].getErrorMessage(task)}"
				if InfoBar.instance and not inStandby:
					InfoBar.instance.openInfoBarMessage(message, MessageBox.TYPE_ERROR, timeout=0)
				else:
					AddNotification(MessageBox, message, MessageBox.TYPE_ERROR, timeout=0, windowTitle=self.baseTitle)
				return False

			if answer:
				if answer in ("YES", "PAR", "YES_BG", "PAR_BG"):
					if not access(path, R_OK):
						self.session.open(MessageBox, _("Error: Script '%s' must have read permission to be able to run!") % path, MessageBox.TYPE_ERROR, close_on_any_key=True, windowTitle=self.baseTitle)
						return
					nice = config.plugins.FileCommander.scriptPriorityNice.value or ""
					ionice = config.plugins.FileCommander.scriptPriorityIONice.value or ""
					if nice:
						nice = f"/bin/nice -n {nice} "
					if ionice:
						ionice = f"/bin/ionice -c {ionice} "
					priority = f"{nice}{ionice}"
					if path.endswith(".sh"):
						if access(path, X_OK):
							cmdline = f"{priority}{path}"
						else:
							cmdline = f"{priority}/bin/sh {path}"
					else:
						cmdline = f"{priority}/usr/bin/python {path}"
					if "PAR" in answer:
						cmdline = f"{cmdline} '{parameter}'"
				elif answer == "VIEW":
					try:
						yfile = stat(path)
					except OSError as err:
						self.session.open(MessageBox, f"{path}: {err.strerror}", MessageBox.TYPE_ERROR, windowTitle=self.baseTitle)
						return
					if path:
						if yfile.st_size < MAX_EDIT_SIZE:
							self.session.open(FileCommanderTextEditor, path)
						else:
							self.session.open(FileCommanderFileViewer, path, isText=self.isFileText(path), initialView="T")
				if answer != "VIEW":
					if answer.endswith("_BG"):
						global taskSTDOut, taskSTDErr
						taskSTDOut = []
						taskSTDErr = []
						if "PAR" in answer:
							name = f"{priority}{path} {parameter}"
						else:
							name = f"{priority}{path}"
						job = Job(f"{_('Run script')} ('{name}')")
						task = Task(job, name)
						task.postconditions.append(TaskPostConditions())
						task.processStdout = taskProcessStdout
						task.processStderr = taskProcessStderr
						task.setCmdline(cmdline)
						JobManager.AddJob(job, onSuccess=successCallback, onFail=failCallback)
						self.updateTitle()
					else:
						self.session.open(Console, cmdlist=(cmdline,))

		def selectionCallback(answer):
			if answer:
				if answer == "CURRENT":
					self.sourceColumn.toggleSelection()
				else:
					startIndex = self.sourceColumn.getCurrentIndex()
					for index in range(self.sourceColumn.count()):
						self.sourceColumn.setCurrentIndex(index)
						if self.sourceColumn.getPath() in relatedFiles[1:]:
							if answer == "SELECTALL":
								self.sourceColumn.setSelection()
							elif answer == "DESELECTALL":
								self.sourceColumn.clearSelection()
							else:
								self.sourceColumn.toggleSelection()
							if [x.strip() for x in self.sourceColumn.getSortBy().split(",")][1].startswith("0"):
								startIndex = index
					self.sourceColumn.setCurrentIndex(startIndex)
				if self.sourceColumn.getCurrentIndex() < self.sourceColumn.count() - 1:
					self.keyGoLineDown()
				print(f"[FileCommander] selectedItems {self.sourceColumn.getSelectedItems()}.")

		path = self.sourceColumn.getPath()
		if self.checkStillExists(path):
			if self.multiSelect == self.sourceColumn:
				if path:
					selectedItems = self.sourceColumn.getSelectedItems()
					relatedFiles = self.getRelatedFiles(path)
					if relatedFiles:
						msg = [_("The following files are related to '%s':") % path]
						for file in relatedFiles[2:]:
							if file == path:
								continue
							msg.append(f"- '{basename(file)}'")
						choiceList = [
							(_("Cancel the selection"), ""),
							(_("Toggle all related files"), "TOGGLEALL")
						]
						if path in selectedItems:
							choiceList.extend((
								(_("Deselect all related files"), "DESELECTALL"),
								(_("Deselect only highlighted file"), "CURRENT")
							))
						else:
							choiceList.extend((
								(_("Select all related files"), "SELECTALL"),
								(_("Select only highlighted file"), "CURRENT")
							))
						self.session.openWithCallback(selectionCallback, MessageBox, "\n".join(msg), list=choiceList, default=3, windowTitle=self.baseTitle)
					else:
						selectionCallback("CURRENT")
				else:
					InfoBar.instance.showUnhandledKey()
			else:
				if self.sourceColumn.canDescend():
					self.sourceColumn.descend()
				else:
					# print(f"[FileCommander] keyOk DEBUG: path='{path}', dir='{self.sourceColumn.getCurrentDirectory()}', file='{basename(path)}'.")
					if not path:
						return
					fileType = splitext(path)[1].lower()
					try:
						magicType = fromfile(path)
					except (PureError, ValueError) as err:
						magicType = None
						print(f"[FileCommander] Error: Unable to identify file via magic fingerprint!  ({err})")
					except OSError as err:
						self.session.open(MessageBox, _("Error %d: File '%s' cannot be opened!  (%s)") % (err.errno, basename(path), err.strerror), MessageBox.TYPE_ERROR, windowTitle=self.baseTitle)
						return
					except Exception as err:
						self.session.open(MessageBox, _("Error: File '%s' cannot be opened!  (%s)") % (basename(path), str(err)), MessageBox.TYPE_ERROR, windowTitle=self.baseTitle)
						return
					if fileType and magicType and fileType != magicType:
						# print(f"[FileCommander] DEBUG: File identified as extension='{fileType}', magic='{magicType}'.")
						if fileType == ".ipk" and magicType == ".lib":
							magicType = ".ipk"
						if fileType == ".py" and magicType == ".wsgi":
							magicType = ".py"
						if fileType == ".mvi" and magicType == ".mpg":
							magicType = ".mvi"
						fileType = magicType
					if fileType == ".mvi" and not exists("/usr/bin/ffmpeg"):  # Disable .mvi viewer if ffmpeg is not available!
						self.session.open(MessageBox, _("FFmpeg is not installed so '.mvi' file actions are not available!"), MessageBox.TYPE_ERROR, windowTitle=self.baseTitle)
						fileType = None
					if fileType in ARCHIVE_FILES:
						if fileType == ".ipk":
							viewMsg = _("View the package contents")
							extractMsg = _("Extract the package contents")
							promptMsg = _("What would you like to do with the package file:")
						else:
							viewMsg = _("View the archive contents")
							extractMsg = _("Extract the archive contents")
							promptMsg = _("What would you like to do with the archive file:")
						choiceList = [
							(_("Cancel"), ""),
							(viewMsg, "VIEW"),
							(extractMsg, "EXTRACT")
						]
						if fileType == ".ipk":
							choiceList.append((_("Install the package"), "INSTALL"))
						self.session.openWithCallback(archiveCallback, MessageBox, text=f"{promptMsg}\n\n{path}", list=choiceList, windowTitle=self.baseTitle)
					elif fileType == ".ts":
						if InfoBar and InfoBar.instance:
							InfoBar.instance.lastservice = self.session.nav.getCurrentlyPlayingServiceOrGroup()
							InfoBar.instance.movieSelected(eServiceReference(eServiceReference.idDVB, eServiceReference.noFlags, path), fromMovieSelection=False)
					elif fileType in MOVIE_EXTENSIONS:
						if InfoBar and InfoBar.instance:
							InfoBar.instance.lastservice = self.session.nav.getCurrentlyPlayingServiceOrGroup()
							InfoBar.instance.movieSelected(eServiceReference(eServiceReference.idServiceMP3, eServiceReference.noFlags, path), fromMovieSelection=False)
					elif fileType in DVD_EXTENSIONS:
						self.session.open(DVDPlayer, dvd_filelist=[path])
					elif fileType in AUDIO_EXTENSIONS:
						choiceList = [
							(_("Cancel"), ""),
							(_("Play the audio file"), "SINGLE"),
							(_("Play all audio files in the directory"), "LIST")
						]
						self.session.openWithCallback(musicCallback, MessageBox, text=f"{_("What would you like to do with the audio file:")}\n\n{path}", list=choiceList, windowTitle=self.baseTitle)
					elif fileType in IMAGE_EXTENSIONS:
						self.session.openWithCallback(imageCallback, FileCommanderImageViewer, self.sourceColumn.getFileList(), self.sourceColumn.getCurrentIndex(), self.sourceColumn.getCurrentDirectory(), basename(path))  # DEBUG: path is not needed!
					elif fileType in (".sh", ".py", ".pyc"):
						choiceList = [
							(_("Cancel"), ""),
							(_("View or edit this %s script") % (_("shell") if path.endswith(".sh") else _("Python")), "VIEW"),
							(_("Run script"), "YES"),
							(_("Run script in background"), "YES_BG")
						]
						parameter = self.targetColumn.getPath() or ""
						msg = ""
						if parameter:
							choiceList.append((_("Run script with optional parameter"), "PAR"))
							choiceList.append((_("Run script with optional parameter in background"), "PAR_BG"))
							msg = f"\n\n{_('Optional parameter')}: {parameter}"
						self.session.openWithCallback(scriptCallback, MessageBox, text=f"{_("What would you like to do with the script file:")}\n\n{path}{msg}", list=choiceList, windowTitle=self.baseTitle)
					elif fileType == ".mvi":
						filename = f"{splitext(basename(path))[0]}.jpg"
						choiceList = [
							(_("Cancel"), ""),
							(_("Show image"), "SHOW"),
							(_("Save image as '%s'") % join(gettempdir(), filename), "SAVE"),
							(_("Show image and save as '%s'") % join(gettempdir(), filename), "SAVESHOW")
						]
						target = self.targetColumn.getCurrentDirectory()
						if target:
							target = join(target, filename)
							choiceList.append((_("Save image as '%s'") % target, "SAVETARGET"))
							choiceList.append((_("Show image and save as '%s'") % target, "SAVESHOWTARGET"))
						self.session.openWithCallback(mviCallback, MessageBox, f"{_("What would you like to do with the background image file:")}\n\n{path}", list=choiceList, windowTitle=self.baseTitle)
					elif fileType in TEXT_FILES or config.plugins.FileCommander.useViewerForUnknown.value:
						self.keyViewEdit(path)
					else:
						self.session.open(MessageBox, _("There are no actions available to process '%s'!") % path, MessageBox.TYPE_ERROR, close_on_any_key=True, windowTitle=self.baseTitle)

	def keyParent(self):
		parent = self.sourceColumn.getCurrentDirectory()
		parent = dirname(normpath(parent)) if parent else None
		self.sourceColumn.changeDir(parent, self.sourceColumn.getCurrentDirectory())

	def keyRefresh(self):
		self.sourceColumn.refresh()
		self.targetColumn.refresh()

	def keyRename(self):
		def processRename(answer):
			if answer:
				msg = _("Please enter the new file name:") if isfile(path) else _("Please enter the new directory name:")
				if answer == "ALL":
					self.session.openWithCallback(renameAllCallback, VirtualKeyBoard, title=msg, text=basename(normpath(relatedFiles[0])))
				else:
					self.session.openWithCallback(renameSelectedCallback, VirtualKeyBoard, title=msg, text=basename(normpath(path)))

		def renameAllCallback(newName):
			if newName:
				directory = dirname(normpath(path))
				baseLen = len(relatedFiles[0])
				for file in relatedFiles[2:]:
					try:
						rename(file, join(directory, f"{newName}{file[baseLen:]}"))
					except OSError as err:
						self.session.open(MessageBox, _("Error %d: Unable to rename related file '%s' to '%s'!  (%s)") % (err.errno, path, newName, err.strerror), MessageBox.TYPE_ERROR, windowTitle=windowTitle)
				self.sourceColumn.refresh(join(directory, f"{newName}{relatedFiles[2][baseLen:]}"))

		def renameSelectedCallback(newName):
			if newName:
				newPath = join(dirname(normpath(path)), newName)
				try:
					rename(normpath(path), newPath)
				except OSError as err:
					self.session.open(MessageBox, _("Error %d: Unable to rename directory/file '%s' to '%s'!  (%s)") % (err.errno, path, newName, err.strerror), MessageBox.TYPE_ERROR, windowTitle=windowTitle)
				if isdir(newPath):
					newPath = join(newPath, "")
				self.sourceColumn.refresh(newPath)

		windowTitle = f"{self.baseTitle} - {_('Rename')}"
		path = self.sourceColumn.getPath()
		if self.checkStillExists(path):
			if path in PROTECTED_DIRECTORIES:
				self.session.open(MessageBox, _("Error: The root file system and system directories can't be renamed!"), MessageBox.TYPE_ERROR, windowTitle=windowTitle)
				return
			relatedFiles = self.getRelatedFiles(path)
			if relatedFiles:
				msg = [_("The following files are related to '%s':") % path]
				for file in relatedFiles[2:]:
					if file == path:
						continue
					msg.append(f"- '{basename(file)}'")
				choiceList = [
					(_("Cancel"), ""),
					(_("Rename all related files"), "ALL"),
					(_("Rename only highlighted file"), "CURRENT")
				]
				self.session.openWithCallback(processRename, MessageBox, "\n".join(msg), list=choiceList, default=2, windowTitle=windowTitle)
			else:
				processRename("CURRENT")

	def keySelectAll(self):
		self.sourceColumn.setAllSelections()

	def keySelectBookmark(self):
		def selectBookmarkCallback(answer):
			if answer:
				self.sourceColumn.changeDir(answer[1])

		bookmarks = [(x, x) for x in config.plugins.FileCommander.bookmarks.value]
		bookmarks.insert(0, (_("Storage Devices"), None))
		order = eval(config.misc.pluginlist.fcBookmarksOrder.value)
		if order and _("Storage Devices") in order:
			order.remove(_("Storage Devices"))
		order.insert(0, _("Storage Devices"))
		config.misc.pluginlist.fcBookmarksOrder.value = str(order)
		config.misc.pluginlist.fcBookmarksOrder.save()
		self.session.openWithCallback(selectBookmarkCallback, ChoiceBox, title=_("Select Bookmark"), list=bookmarks, reorderConfig="fcBookmarksOrder")

	def keySettings(self):
		def settingsCallback(*answer):
			fileFilter = self.buildFileFilter()
			if fileFilter != self.oldFileFilter:
				self["listleft"].matchingPattern = fileFilter
				self["listright"].matchingPattern = fileFilter
				self.updateTitle()
			del self.oldFileFilter
			self["listleft"].setSortBy(f"{config.plugins.FileCommander.sortDirectoriesLeft.value},{config.plugins.FileCommander.sortFilesLeft.value}")
			self["listright"].setSortBy(f"{config.plugins.FileCommander.sortDirectoriesRight.value},{config.plugins.FileCommander.sortFilesRight.value}")
			self["alwaysNumberActions"].setEnabled(not config.plugins.FileCommander.useQuickSelect.value)
			self["notStorageNumberAction"].setEnabled(not config.plugins.FileCommander.useQuickSelect.value)
			self["directoryFileNumberActions"].setEnabled(not config.plugins.FileCommander.useQuickSelect.value)
			self["fileOnlyNumberActions"].setEnabled(not config.plugins.FileCommander.useQuickSelect.value)
			self["quickSelectActions"].setEnabled(config.plugins.FileCommander.useQuickSelect.value)
			self["navigationActions"].setEnabled(not config.plugins.FileCommander.legacyNavigation.value)
			self["legacyNavigationActions"].setEnabled(config.plugins.FileCommander.legacyNavigation.value)
			self.updateSort()
			self.keyRefresh()

		self.oldFileFilter = self.buildFileFilter()
		self.session.openWithCallback(settingsCallback, FileCommanderSetup)

	def keySortDirectories(self):
		def sortDirectoriesCallback(answer):
			if answer:
				sort = self.sourceColumn.getSortBy().split(",")
				sort[0] = answer
				self.sourceColumn.setSortBy(",".join(sort))
				self.sourceColumn.refresh()
				self.updateHeading(self.sourceColumn)
				self.updateSort()

		msg = _("Select the directory sort order for the left column:") if self.leftActive else _("Select the directory sort order for the right column:")
		choiceList = [
			(_("Cancel"), ""),
			(_("Name ascending"), "0.0"),
			(_("Name descending"), "0.1"),
			(_("Date ascending"), "1.0"),
			(_("Date descending"), "1.1")
		]
		self.session.openWithCallback(sortDirectoriesCallback, MessageBox, text=msg, list=choiceList, windowTitle=self.baseTitle)

	def keySortFiles(self):
		def sortFilesCallback(answer):
			if answer:
				sort = self.sourceColumn.getSortBy().split(",")
				sort[1] = answer
				self.sourceColumn.setSortBy(",".join(sort))
				self.sourceColumn.refresh()
				self.updateHeading(self.sourceColumn)
				self.updateSort()

		column = "left" if self.leftActive else "right"
		choiceList = [
			(_("Cancel"), ""),
			(_("Name ascending"), "0.0"),
			(_("Name descending"), "0.1"),
			(_("Date ascending"), "1.0"),
			(_("Date descending"), "1.1"),
			(_("Size ascending"), "2.0"),
			(_("Size descending"), "2.1")
		]
		self.session.openWithCallback(sortFilesCallback, MessageBox, text=(_("Select the file sort order for the %s column:") % column), list=choiceList, windowTitle=self.baseTitle)

	def keyTaskList(self):
		self.taskList = []
		for job in JobManager.getPendingJobs():
			progress = job.getProgress()
			self.taskList.append((job, job.name, job.getStatustext(), progress, f"{progress} %%"))
		self.session.open(TaskListScreen, self.taskList)

	def keyToggleAll(self):
		self.sourceColumn.toggleAllSelections()

	def keyViewEdit(self, path=None):
		if path is None:
			path = self.sourceColumn.getPath()
		if self.checkStillExists(path):
			if self.isFileText(path):
				if stat(path).st_size < MAX_EDIT_SIZE:
					modTime = stat(path).st_mtime
					self.session.open(FileCommanderTextEditor, path)
					if modTime != stat(path).st_mtime:
						self.sourceColumn.refresh()
				else:
					self.fileTooBig()
			else:
				if stat(path).st_size < MAX_HEXVIEW_SIZE:
					self.session.open(FileCommanderFileViewer, path, isText=False, initialView="H")
				else:
					self.fileTooBig()

	def shortcutAction(self, program):
		def shortcutInstallCallback(answer):
			if answer:
				self.session.openWithCallback(shortcutInstalledCallback, Console, title=f"{self.baseTitle} - {_('Console')}", cmdlist=(("/usr/bin/opkg", "update"), ("/usr/bin/opkg", "install", self.package)))

		def shortcutInstalledCallback():
			self.shortcutAction(program)

		if self.isPackageInstalled(program):
			path = self.sourceColumn.getPath()
			if self.checkStillExists(path):
				if path is None:
					self.session.open(MessageBox, _("Error: It is not possible to run '%s' on '%s'!") % (program, STORAGE_DEVICES_NAME), MessageBox.TYPE_ERROR, windowTitle=self.baseTitle)
					return
				path = normpath(path)
				if isdir(path):
					self.session.open(MessageBox, _("Error: You can't run '%s' on a directory!") % program, MessageBox.TYPE_ERROR, close_on_any_key=True, windowTitle=self.baseTitle)
				else:
					fileType = splitext(path.lower())[1]
					if fileType in MEDIA_FILES:
						self.session.open(FileCommanderMediaInfo, path, program=program)
					else:
						self.session.open(MessageBox, _("Error: You can't run '%s' on '%s'!") % (program, basename(path)), MessageBox.TYPE_ERROR, close_on_any_key=True, windowTitle=self.baseTitle)
		else:
			package = self.OPTIONAL_PACKAGES.get(program)
			if package:
				self.package = package
				self.session.openWithCallback(shortcutInstallCallback, MessageBox, _("Program '%s' needs to be installed to perform this action. Do you want to install the '%s' package to install the program?") % (program, package), MessageBox.TYPE_YESNO, default=True, windowTitle=self.baseTitle)
			else:
				self.session.open(MessageBox, _("Error: Program '%s' not installed and the package containing this program is unknown!") % program, MessageBox.TYPE_ERROR, close_on_any_key=True, windowTitle=self.baseTitle)

	def shortcutHelp(self, program):
		if self.isPackageInstalled(program):
			helpMsg = _("Run '%s' command") % program
		elif program in self.OPTIONAL_PACKAGES:
			helpMsg = _("Install '%s' command") % program
		else:
			helpMsg = _("Command '%s' is unknown") % program
		return helpMsg

	def getRelatedFiles(self, path):
		# print(f"[FileCommander] DEBUG: Supplied path '{path}'.")
		relatedFiles = []
		base, extension = splitext(path)
		if extension == ".eit":  # We have a ".eit" extension so we need to identify the movie type.
			if isfile(f"{base}.ts"):  # For speed see if this is a normal recording ".ts" file.
				extension = ".ts"
			else:  # Try all other movie extensions see if there is a related movie file match.
				for extension in MOVIE_EXTENSIONS:
					if isfile(f"{base}{extension}"):
						break
				else:
					extension = None
		elif extension in RECORDING_EXTENSIONS:
			base, extension = splitext(base)
		if extension in MOVIE_EXTENSIONS:
			base = splitext(base)[0]
			relatedFiles.append(base)
			relatedFiles.append(f"{base}{extension}")
			relatedExtensions = (".eit", ".jpg", ".log", ".txt", extension, f"{extension}.ap", f"{extension}.cuts", f"{extension}.meta", f"{extension}.sc")
			for extension in relatedExtensions:
				related = f"{base}{extension}"
				if isfile(related):
					relatedFiles.append(related)
			if len(relatedFiles) < 4:  # The file is a movie related file but has no related files.
				relatedFiles = ""
			# 	print("[FileCommander] DEBUG: No related files.")
			# else:
			# 	print(f"[FileCommander] DEBUG: Base path '{base}'.")
			# 	for file in relatedFiles[1:]:
			# 		print(f"[FileCommander] DEBUG:     Related file: '{file}'.")
		return relatedFiles

	def checkStillExists(self, path):
		if path and not lexists(path):
			self.displayStatus(_("The directory/file no longer exists."))
			self.sourceColumn.refresh()
			return False
		return True

	def fileTooBig(self):
		self.session.open(MessageBox, _("This function is not available as processing of large files may take too long to run on this hardware."), MessageBox.TYPE_WARNING, timeout=5, close_on_any_key=True, windowTitle=self.baseTitle)

	def isFileText(self, path):
		text = True
		try:
			with open(path, encoding="UTF-8", errors="strict") as fd:
				fd.read(BLOCK_CHUNK_SIZE)
		except Exception:
			text = False
		return text

	# def keySortLeft(self):  # Sorting files left.
	# 	self["listleft"].setSortBy(self.setSort(self["listleft"]))
	# 	self["listleft"].refresh()

	# def keySortLeftReverse(self):  # Reverse sorting files left.
	# 	self["listleft"].setSortBy(self.setReverse(self["listleft"]))
	# 	self["listleft"].refresh()

	# def keySortRight(self):  # Sorting files right.
	# 	self["listright"].setSortBy(self.setSort(self["listright"]))
	# 	self["listright"].refresh()

	# def keySortRightReverse(self):  # Reverse sorting files right.
	# 	self["listright"].setSortBy(self.setReverse(self["listright"]))
	# 	self["listright"].refresh()

	# def setSort(self, column, setDirs=False):
	# 	sortDirs, sortFiles = column.getSortBy().split(",")
	# 	# if setDirs:
	# 	# 	sort, reverse = [int(x) for x in sortDirs.split(".")]
	# 	# 	sort += 1
	# 	# 	if sort > 1:
	# 	# 		sort = 0
	# 	# else:
	# 	sort, reverse = [int(x) for x in sortFiles.split(".")]
	# 	sort += 1
	# 	if sort > 2:
	# 		sort = 0
	# 	return f"{sort}.{reverse}"

	# def setReverse(self, column, setDirs=False):
	# 	sortDirs, sortFiles = column.getSortBy().split(",")
	# 	# if setDirs:
	# 	# 	sort, reverse = [int(x) for x in sortDirs.split(".")]
	# 	# else:
	# 	sort, reverse = [int(x) for x in sortFiles.split(".")]
	# 	reverse += 1
	# 	if reverse > 1:
	# 		reverse = 0
	# 	return f"{sort}.{reverse}"


class FileCommanderContextMenu(Screen):
	skin = """
	<screen name="FileCommanderContextMenu" title="File Commander Context Menu" position="center,center" size="560,545" resolution="1280,720">
		<widget name="menu" position="0,0" size="560,385" itemHeight="35" />
		<widget name="description" position="0,395" size="560,100" font="Regular;20" valign="center" />
		<widget source="key_menu" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_menu" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, contexts, menuList, directory, path):
		Screen.__init__(self, session)
		if not self.getTitle():
			self.setTitle(_("File Commander Context Menu"))
		if "OkCancelActions" not in contexts:
			contexts = ["OkCancelActions"] + contexts
		actions = {
			"cancel": self.keyCancel,
			"ok": self.keyOk
		}
		menu = []
		for item in menuList:
			button = item[0]
			text = item[1]
			if callable(text):
				text = text()
			if text:
				action = item[2] if len(item) > 2 else button
				if button and button not in ("expandable", "expanded", "verticalline", "bullet"):
					actions[button] = boundFunction(self.close, button)
				menu.append(ChoiceEntryComponent(button, (text, action)))
		self["actions"] = ActionMap(contexts, actions, prio=0)
		self["key_menu"] = StaticText(_("MENU"))
		self["menu"] = ChoiceList(menu)
		description = [f"{_("Current directory")}: {directory}"]
		if path != directory:
			description.append(f"{_("Highlighted item")}: {path}")
		self["description"] = Label("\n".join(description))

	def keyCancel(self):
		self.close(False)

	def keyOk(self):
		self.close(self["menu"].getCurrent()[0][1])


class FileCommanderSetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "FileCommander", plugin="Extensions/FileCommander")

	def keySelect(self):
		if self.getCurrentItem() in (config.plugins.FileCommander.defaultPathLeft, config.plugins.FileCommander.defaultPathRight):
			currDir = self.getCurrentItem().value if self.getCurrentItem().value else None
			self.session.openWithCallback(boundFunction(self.keySelectCallback, self.getCurrentItem()), LocationBox, text=_("Select default File Commander directory:"), currDir=currDir, minFree=100)
		else:
			Setup.keySelect(self)

	def keySelectCallback(self, configItem, path):
		if path:
			configItem.value = path


class FileCommanderData(Screen):
	skin = """
	<screen name="FileCommanderData" title="File Commander Data" position="center,center" size="1000,500" resolution="1280,720">
		<widget name="data" position="0,0" size="1000,450" conditional="data" font="Regular;20" splitPosition="300" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="380,e-40" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="570,e-40" size="180,40" backgroundColor="key_blue" conditional="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_menu" render="Label" position="e-260,e-40" size="80,40" backgroundColor="key_back" conditional="key_menu" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_info" render="Label" position="e-170,e-40" size="80,40" backgroundColor="key_back" conditional="key_info" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, data):
		Screen.__init__(self, session, enableHelp=True)
		self.skinName = ["FileCommanderData"]
		if not isinstance(data, dict):
			print("[FileCommander] Error: FileCommanderData screen requires a formatting dictionary!")
			self.session.open(MessageBox, _("Error: FileCommanderData screen requires a formatting dictionary!"), MessageBox.TYPE_ERROR, windowTitle=_("File Commander Data"))
			self.close()
		item = data.get("Screen")
		if item:
			self.skinName.insert(0, item)
		item = data.get("Title")
		if item:
			self.setTitle(item)
		self["data"] = ScrollLabel("\n".join(data.get("Data")))
		self["key_red"] = StaticText(_("Close"))
		item = data.get("Description", _("File Commander Data Actions"))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"cancel": (self.close, _("Close this screen")),
			"ok": (self.close, _("Close this screen")),
			"red": (self.close, _("Close this screen"))
		}, prio=0, description=item)
		self["navigationActions"] = HelpableActionMap(self, ["NavigationActions"], {
			"top": (self["data"].goTop, _("Move to first line / screen")),
			"pageUp": (self["data"].goPageUp, _("Move up a screen")),
			"up": (self["data"].goLineUp, _("Move up a line")),
			# "left": (self["data"].goPageUp, _("Move up a screen")),
			# "right": (self["data"].goPageDown, _("Move down a screen")),
			"down": (self["data"].goLineDown, _("Move down a line")),
			"pageDown": (self["data"].goPageDown, _("Move down a screen")),
			"bottom": (self["data"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=item)
		self["navigationActions"].setEnabled(self["data"].isNavigationNeeded())

	def processArguments(self, directory, arguments, display, finished):
		def dataAvail(data):
			if isinstance(data, bytes):
				data = data.decode()
			self.textBuffer = f"{self.textBuffer}{data}"
			if callable(display):
				display(self.textBuffer)

		def appClosed(retVal):
			del self.container.dataAvail[:]
			del self.container.appClosed[:]
			del self.container
			if callable(display):
				display(self.textBuffer)
			if callable(finished):
				finished(retVal)

		self.container = eConsoleAppContainer()
		if directory:
			self.container.setCWD(directory)
		self.container.dataAvail.append(dataAvail)
		self.container.appClosed.append(appClosed)
		self.container.execute(*arguments)


class FileCommanderArchiveBase(FileCommanderData):
	def __init__(self, session, path, target=None):
		data = {}
		data["Screen"] = "FileCommanderArchive"
		data["Title"] = _("File Commander Archive")
		data["Description"] = _("File Commander Archive Actions")
		self.path = normpath(path)
		self.extension = splitext(self.path)[1][1:].lower()
		if self.path[-8:].lower() == ".tar.bz2" or self.path[-7:].lower() in (".tar.gz", ".tar.xz"):
			self.extension = "tar"
		self.target = target
		data["Data"] = [_("Please wait while the data is extracted...")]
		FileCommanderData.__init__(self, session, data)


class FileCommanderArchiveExtract(FileCommanderArchiveBase):
	def __init__(self, session, path, target=None):
		FileCommanderArchiveBase.__init__(self, session, path, target)
		self.callLater(self.extractArchive)

	def extractArchive(self):
		currentDir = join(dirname(self.path), "")
		tempDir = join(gettempdir(), "")
		choices = [
			(_("Cancel extraction"), ""),
			(_("Current directory (%s)") % currentDir, currentDir),
			(_("Default movie location (%s)") % config.usage.default_path.value, config.usage.default_path.value),
			(_("Temp directory (%s)") % tempDir, tempDir),
			(_("Select a directory"), "\0")
		]
		if self.target and self.target.getCurrentDirectory():
			targetDir = self.target.getCurrentDirectory()
			choices.insert(2, (_("Other panel directory (%s)") % targetDir, targetDir))
		self.session.openWithCallback(self.extractArchiveCallback, MessageBox, _("To where would you like to extract '%s'?") % self.path, MessageBox.TYPE_YESNO, list=choices, default=0, windowTitle=self.getTitle())

	def extractArchiveCallback(self, target):
		if target == "\0":
			minFree = 100  # Get the size of the archive?
			self.session.openWithCallback(self.extractArchiveCallback, LocationBox, text=_("Select a location into which to extract '%s':") % self.path, currDir=dirname(self.path), minFree=minFree)
		elif target:
			self.textBuffer = f"- {self.path}:\n- \n"
			if self.extension == "tar":
				def displayData(data):
					self["data"].setText(data)

				self.processArguments(target, ["/bin/busybox", "tar", "-xvf", self.path], displayData, self.updateActionMap)
			elif self.extension == "ipk":
				def displayData(data):
					self["data"].setText(data)

				def processControl(retVal):
					path = join(target, "control.tar.gz")
					if isfile(path):
						self.textBuffer = f"{self.textBuffer}{_("Control files:")}\n"
						self.processArguments(target, ["/bin/busybox", "tar", "-xvf", path], displayData, processArchive)

				def processArchive(retVal):
					for file in ("data.tar.gz", "data.tar.xz"):
						path = join(target, file)
						if isfile(path):
							self.textBuffer = f"{self.textBuffer}\n{_("Package files:")}\n"
							self.processArguments(target, ["/bin/busybox", "tar", "-xvf", path], displayData, processCleanup)
							break

				def processCleanup(retVal):
					for file in ("debian-binary", "control.tar.gz", "data.tar.gz", "data.tar.xz"):
						path = join(target, file)
						if isfile(path):
							try:
								remove(path)
							except OSError:
								pass
					self["navigationActions"].setEnabled(self["data"].isNavigationNeeded())

				target = join(target, splitext(basename(self.path))[0])
				try:
					mkdir(target)
				except OSError as err:
					if err.errno != EEXIST:
						self["data"].setText(_("Error %d: Unable to create package directory '%s'!  (%s)") % (err.errno, target, err.strerror))
						print("[FileCommander] Error %d: Unable to create package directory '%s'!  (%s)" % (err.errno, target, err.strerror))
						return
				self.processArguments(target, ["/usr/bin/ar", "/usr/bin/ar", "x", self.path], None, processControl)
			elif self.extension == "rar":
				def displayData(data):
					self["data"].setText(data)

				self.processArguments(target, ["/usr/bin/unrar", "/usr/bin/unrar", "x", "-y", self.path], displayData, self.updateActionMap)
			else:
				def displayData(data):
					self["data"].setText("\n".join([x[2:] for x in [x for x in data.split("\n") if x.startswith("- ")]]))

				self.processArguments(target, ["/usr/bin/7za", "/usr/bin/7za", "x", "-ba", "-bb1", "-bd", "-y", self.path], displayData, self.updateActionMap)
		else:
			self.close()

	def updateActionMap(self, retVal=None):
		self["navigationActions"].setEnabled(self["data"].isNavigationNeeded())
		if self.target:
			self.target.refresh()


class FileCommanderArchiveInstall(FileCommanderArchiveBase):
	def __init__(self, session, path, target=None):
		FileCommanderArchiveBase.__init__(self, session, path, target)
		self.callLater(self.installArchive)

	def installArchive(self):
		def displayData(data):
			self["data"].setText(data)
			self["data"].goBottom()

		def processInstall(retVal):
			self.processArguments(None, ["/usr/bin/opkg", "/usr/bin/opkg", "install", self.path], displayData, processPlugin)

		def processPlugin(retVal):
			self.textBuffer = f"{self.textBuffer}\n{_("Installation finished.")}\n"
			displayData(self.textBuffer)
			self["navigationActions"].setEnabled(self["data"].isNavigationNeeded())
			if basename(self.path).startswith("enigma2-plugin-"):
				plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))

		self.textBuffer = f"{self.path}:\n\n"
		self.processArguments(None, ["/usr/bin/opkg", "/usr/bin/opkg", "update"], displayData, processInstall)


class FileCommanderArchiveView(FileCommanderArchiveBase):
	def __init__(self, session, path):
		FileCommanderArchiveBase.__init__(self, session, path, target=None)
		self.callLater(self.viewArchive)

	def viewArchive(self):
		self.textBuffer = f"{' ' * 53}{self.path}:\n{' ' * 53}\n"
		if self.extension == "tar":
			def displayData(data):
				self["data"].setText(data)

			self.processArguments(None, ["/bin/busybox", "tar", "-tf", self.path], displayData, self.updateActionMap)
		elif self.extension == "ipk":
			def displayData(data):
				self["data"].setText(data)

			def processControl(retVal):
				path = join(tempDir, "control.tar.gz")
				if isfile(path):
					self.textBuffer = f"{self.textBuffer}{_("Control files:")}\n"
					self.processArguments(tempDir, ["/bin/busybox", "tar", "-tf", path], displayData, processArchive)

			def processArchive(retVal):
				for file in ("data.tar.bz2", "data.tar.gz", "data.tar.xz"):
					path = join(tempDir, file)
					if isfile(path):
						self.textBuffer = f"{self.textBuffer}\n{_("Package files:")}\n"
						self.processArguments(tempDir, ["/bin/busybox", "tar", "-tf", path], displayData, processCleanup)
						break

			def processCleanup(retVal):
				for file in ("debian-binary", "control.tar.gz", "data.tar.bz2", "data.tar.gz", "data.tar.xz"):
					path = join(tempDir, file)
					if isfile(path):
						try:
							remove(path)
						except OSError:
							pass
				try:
					rmdir(tempDir)
				except OSError:
					pass
				self.updateActionMap()

			tempDir = mkdtemp()
			self.processArguments(tempDir, ["/usr/bin/ar", "/usr/bin/ar", "x", self.path], None, processControl)
		elif self.extension == "rar":
			def displayData(data):
				self["data"].setText(data)

			self.processArguments(None, ["/usr/bin/unrar", "/usr/bin/unrar", "lb", self.path], displayData, self.updateActionMap)
		else:
			def displayData(data):
				self["data"].setText("\n".join([x[53:] for x in [x for x in data.split("\n") if x]]))

			self.processArguments(None, ["/usr/bin/7za", "/usr/bin/7za", "l", "-ba", self.path], displayData, self.updateActionMap)

	def updateActionMap(self, retVal=None):
		self["navigationActions"].setEnabled(self["data"].isNavigationNeeded())


class FileCommanderFileViewer(Screen):
	skin = """
	<screen name="FileCommanderFileViewer" title="File Commander File Viewer" position="40,80" size="1200,610" resolution="1280,720">
		<widget name="path" position="0,0" size="1030,50" font="Regular;20" foregroundColor="#00fff000" valign="center" />
		<widget name="data" position="0,60" size="1200,500" font="Console;20" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="380,e-40" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="570,e-40" size="180,40" backgroundColor="key_blue" conditional="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, path, isText=False, initialView="H"):
		Screen.__init__(self, session, enableHelp=True)
		self.skinName = ["FileCommanderFileViewer"]
		if not self.getTitle():
			self.setTitle(_("File Commander File Viewer"))
		self.path = normpath(path)
		self.isText = isText
		self["path"] = Label(self.path)
		self["data"] = ScrollLabel()
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"cancel": (self.close, _("Exit viewer")),
			"ok": (self.close, _("Exit viewer")),
			"red": (self.close, _("Exit viewer")),
			"top": (self["data"].goTop, _("Move to first line / screen")),
			"pageUp": (self["data"].goPageUp, _("Move up a screen")),
			"up": (self["data"].goLineUp, _("Move up a line")),
			"down": (self["data"].goLineDown, _("Move down a line")),
			"pageDown": (self["data"].goPageDown, _("Move down a screen")),
			"bottom": (self["data"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("File Commander File Viewer Actions"))
		self["hexAction"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyHex, _("Display file as hexadecimal"))
		}, prio=0, description=_("File Commander File Viewer Actions"))
		self["octAction"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyOct, _("Display file as octal"))
		}, prio=0, description=_("File Commander File Viewer Actions"))
		self["textAction"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.keyText, _("Display file as text"))
		}, prio=0, description=_("File Commander File Viewer Actions"))
		if initialView[0].upper() == "H":
			self.keyHex()
		elif initialView[0].upper() == "O":
			self.keyOct()
		elif initialView[0].upper() == "T":
			self.keyText()

	def keyHex(self):
		deferToThread(self.readHex)
		self["data"].setText(_("Please wait while the file is read and processed..."))
		self["key_green"].setText("")
		self["key_yellow"].setText(_("Octal"))
		self["key_blue"].setText(_("Text") if self.isText else "")
		self["hexAction"].setEnabled(False)
		self["octAction"].setEnabled(True)
		self["textAction"].setEnabled(self.isText)

	def readHex(self):
		data = []
		try:
			with open(self.path, "rb") as fd:
				fileBuffer = fd.read(MAX_HEXVIEW_SIZE)
				for position, rowData in [(x, fileBuffer[x:x + 16]) for x in range(0, len(fileBuffer), 16)]:
					hexChars = " ".join([f"{x:02X}" for x in rowData])
					textChars = " ".join([chr(x) if 0x20 <= x < 0x7F else "?" for x in rowData])
					count = len(rowData)
					while count < 16:
						hexChars = f"{hexChars}   "
						count += 1
					data.append(f"{position:06X}: {hexChars}  -  {textChars}")
		except OSError as err:
			data = [_("Error %d: Unable to read '%s'!  (%s)") % (err.errno, self.path, err.strerror)]
		self["data"].setText("\n".join(data))

	def keyOct(self):
		deferToThread(self.readOct)
		self["key_green"].setText(_("Hexadecimal"))
		self["key_yellow"].setText("")
		self["key_blue"].setText(_("Text") if self.isText else "")
		self["hexAction"].setEnabled(True)
		self["octAction"].setEnabled(False)
		self["textAction"].setEnabled(self.isText)

	def readOct(self):
		data = []
		try:
			with open(self.path, "rb") as fd:
				fileBuffer = fd.read(MAX_HEXVIEW_SIZE)
				for position, rowData in [(x, fileBuffer[x:x + 8]) for x in range(0, len(fileBuffer), 8)]:
					octChars = " ".join([f"{x:03o}" for x in rowData])
					textChars = " ".join([chr(x) if 0x20 <= x < 0x7F else "?" for x in rowData])
					count = len(rowData)
					while count < 8:
						octChars = f"{octChars}    "
						count += 1
					data.append(f"{position:08o}: {octChars}  -  {textChars}")
		except OSError as err:
			data = [_("Error %d: Unable to read '%s'!  (%s)") % (err.errno, self.path, err.strerror)]
		self["data"].setText("\n".join(data))

	def keyText(self):
		data = []
		try:
			with open(self.path) as fd:
				data = fd.read(MAX_EDIT_SIZE).splitlines()
		except OSError as err:
			data = [_("Error %d: Unable to read '%s'!  (%s)") % (err.errno, self.path, err.strerror)]
		self["data"].setText("\n".join(data))
		if stat(self.path).st_size < MAX_HEXVIEW_SIZE:
			self["key_green"].setText(_("Hexadecimal"))
			self["key_yellow"].setText(_("Octal"))
			self["key_blue"].setText("")
			self["hexAction"].setEnabled(True)
			self["octAction"].setEnabled(True)
			self["textAction"].setEnabled(False)


class FileCommanderImageViewer(Screen):
	skin = """
	<screen name="FileCommanderImageViewer" title="File Commander Image Viewer" position="fill" flags="wfNoBorder" resolution="1280,720">
		<eLabel position="fill" backgroundColor="#00000000" />
		<widget name="image" position="0,0" size="1280,720" alphatest="on" zPosition="+1" />
		<widget source="message" render="Label" position="10,685" size="1210,25" borderColor="#00000000" borderWidth="2" font="Regular;20" foregroundColor="#0038FF48" noWrap="1" transparent="1" valign="bottom" zPosition="+2" />
		<widget name="status" position="1220,690" size="20,20" pixmap="icons/record.png" alphatest="blend" scale="1" zPosition="+2" />
		<widget name="icon" position="1250,690" size="20,20" pixmap="icons/ico_mp_play.png" alphatest="blend" scale="1" zPosition="+2" />
		<widget name="infolabels" position="10,10" size="250,600" borderColor="#00000000" borderWidth="2" font="Regular;20" foregroundColor="#0038FF48" halign="right" transparent="1" zPosition="+3" />
		<widget name="infodata" position="270,10" size="1000,600" borderColor="#00000000" borderWidth="2" font="Regular;20" foregroundColor="#0038FF48" halign="left" transparent="1" zPosition="+3" />
	</screen>"""
	exifDesc = [
		_("Filename"),
		_("EXIF-Version"),
		_("Make"),
		_("Camera"),
		_("Date / Time"),
		_("Width / Height"),
		_("Flash used"),
		_("Orientation"),
		_("User comments"),
		_("Metering mode"),
		_("Exposure program"),
		_("Light source"),
		_("Compressed bits/pixel"),
		_("ISO speed rating"),
		_("X-Resolution"),
		_("Y-Resolution"),
		_("Resolution unit"),
		_("Brightness"),
		_("Exposure time"),
		_("Exposure bias"),
		_("Distance"),
		_("CCD-Width"),
		_("Aperture F number")
	]

	def __init__(self, session, fileList, index, path, filename):  # DEBUG: path is not needed!
		Screen.__init__(self, session, mandatoryWidgets=["infolabels"], enableHelp=True)
		self.skinName = ["FileCommanderImageViewer"]
		if not self.getTitle():
			self.setTitle(_("File Commander Image Viewer"))
		self.startIndex = index
		self.lastIndex = index
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "InfoActions", "ColorActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Exit image viewer")),
			"ok": (self.keyToggleOverlay, _("Toggle display of the image status overlay")),
			"info": (self.keyToggleInformation, _("Toggle display of image information")),
			"red": (self.keyCancel, _("Exit image viewer")),
			"green": (self.keyToggleInformation, _("Toggle display of image information")),
			"yellow": (self.keySlideshow, _("Start/stop slide show")),
			"up": (self.keyFirstImage, _("Show first image")),
			"first": (self.keyFirstImage, _("Show first image")),
			"left": (self.keyPreviousImage, _("Show previous image")),
			"right": (self.keyNextImage, _("Show next image")),
			"last": (self.keyLastImage, _("Show last image")),
			"down": (self.keyLastImage, _("Show last image"))
		}, prio=0, description=_("File Commander Image Viewer Actions"))
		self["image"] = Pixmap()
		self["icon"] = Pixmap()
		self["status"] = Pixmap()
		self["message"] = StaticText(_("Please wait, loading image..."))
		self["infolabels"] = Label()
		text = ":\n".join(self.exifDesc)
		self.infoLabelsText = f"{text}:"
		self["infodata"] = Label()
		self.currentIndex = 0
		self.fileList = [fileList] if isinstance(fileList, str) else self.makeFileList(fileList, filename)
		self.fileListLen = len(self.fileList) - 1
		self.displayedImage = ()
		self.currentImage = ()
		self.displayNow = True
		self.displayOverlay = True
		self.displayInformation = False
		self.slideshowTimer = eTimer()
		self.slideshowTimer.callback.append(self.slideshowCallback)
		self.imageLoad = ePicLoad()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		if self.fileListLen >= 0:
			self.imageLoad.PictureData.get().append(self.finishDecode)
			self.imageLoad.setPara([self["image"].instance.size().width(), self["image"].instance.size().height(), 1, 1, 0, 1, "#00000000"])
			self["icon"].hide()
			self["message"].setText("")
			self["infolabels"].setText("")
			self["infodata"].setText("")
			self.startDecode()

	def makeFileList(self, fileList, filename):
		elements = len(fileList[0])
		imageList = []
		index = 0
		for fileData in fileList:
			imagePath = fileData[0][FILE_PATH] if elements > 1 else fileData[4]
			extension = splitext(imagePath)[1].lower() if imagePath and not fileData[0][FILE_IS_DIR] else None
			if extension and extension in IMAGE_EXTENSIONS:
				imageList.append(imagePath)
				if basename(imagePath) == filename:
					self.currentIndex = index
				index += 1
		return imageList

	def slideshowCallback(self):
		if not config.plugins.FileCommander.slideshowLoop.value and self.lastIndex == self.fileListLen:
			self["icon"].hide()
			return
		self.displayNow = True
		self.showPicture()

	def startDecode(self):
		if self.fileList:
			self.imageLoad.startDecode(self.fileList[self.currentIndex])
			if self.displayOverlay:
				self["status"].show()

	def finishDecode(self, picInfo=""):
		if self.displayOverlay:
			self["status"].hide()
		data = self.imageLoad.getData()
		if data:
			try:
				text = picInfo.split("\n", 1)[0].split("/")[-1]
				text = f"({self.currentIndex + 1} / {self.fileListLen + 1})  {text}"
			except Exception:
				text = f"({self.currentIndex + 1} / {self.fileListLen + 1})"
			exifList = self.imageLoad.getInfo(self.fileList[self.currentIndex])
			information = []
			for index in range(len(exifList)):
				information.append(f"{exifList[index]}")
			self.currentImage = (text, self.currentIndex, data, "\n".join(information))
			self.showPicture()

	def showPicture(self):
		if self.displayNow and self.currentImage:
			self.displayNow = False
			self["message"].setText(self.currentImage[0] if self.displayOverlay else "")
			self.lastIndex = self.currentImage[1]
			self["image"].instance.setPixmap(self.currentImage[2].__deref__())
			self["infolabels"].setText(self.infoLabelsText if self.displayInformation else "")
			self["infodata"].setText(self.currentImage[3] if self.displayInformation else "")
			self.displayedImage = self.currentImage[:]
			self.currentImage = ()
			self.currentIndex += 1
			if self.currentIndex > self.fileListLen:
				self.currentIndex = 0
			self.startDecode()

	def keyCancel(self):
		self.slideshowTimer.stop()
		del self.imageLoad
		self.close(self.startIndex)

	def keyToggleOverlay(self):
		self.displayOverlay = not self.displayOverlay
		if self.displayOverlay:
			self["message"].setText(self.displayedImage[0])
			if self.slideshowTimer.isActive():
				self["icon"].show()
		else:
			self["message"].setText("")
			self["icon"].hide()

	def keyToggleInformation(self):
		self.displayInformation = not self.displayInformation
		if self.displayInformation:
			self["infolabels"].setText(self.infoLabelsText)
			self["infodata"].setText(self.displayedImage[3])
		else:
			self["infolabels"].setText("")
			self["infodata"].setText("")

	def keySlideshow(self):
		if self.slideshowTimer.isActive():
			self.slideshowTimer.stop()
			if self.displayOverlay:
				self["icon"].hide()
		else:
			self.slideshowTimer.start(config.plugins.FileCommander.slideshowDelay.value * 1000)
			if self.displayOverlay:
				self["icon"].show()
			self.keyNextImage()

	def keyFirstImage(self):
		self.currentImage = ()
		self.currentIndex = 0
		self.startDecode()
		self.displayNow = True

	def keyPreviousImage(self):
		self.currentImage = ()
		self.currentIndex = self.lastIndex
		self.currentIndex -= 1
		if self.currentIndex < 0:
			self.currentIndex = self.fileListLen
		self.startDecode()
		self.displayNow = True

	def keyNextImage(self):
		self.displayNow = True
		self.showPicture()

	def keyLastImage(self):
		self.currentImage = ()
		self.currentIndex = self.fileListLen
		self.startDecode()
		self.displayNow = True


class FileCommanderInformation(FileCommanderData, StatInfo):
	def __init__(self, session, path, target):
		def displayDirectorySize(retVal):
			if directorySizeIndex:
				treeSize = None
				try:
					treeSize = int([x for x in self.textBuffer.split("\n") if x][-1].split("\t")[0]) if self.textBuffer else None
				except:
					pass
				if treeSize:
					info[directorySizeIndex] = f"{_("Tree size")}:|{treeSize:,}   ({numberScaler.scale(treeSize, style="Si", maxNumLen=3, decimals=3)})   ({NumberScaler().scale(treeSize, style="Iec", maxNumLen=3, decimals=3)})"
				else:
					del info[directorySizeIndex]
				self["data"].setText("\n".join(info))

		def displayFileInfo(retVal):
			fileType = self.textBuffer.split(" ", 1)[1] if self.textBuffer else None
			if fileType:
				info[3] = f"{_("Content")}:|{fileType.strip()}"
			else:
				del info[3]
			self["data"].setText("\n".join(info))

		data = {}
		data["Screen"] = "FileCommanderInformation"
		data["Title"] = _("File Commander Directory/File Information")
		data["Description"] = _("File Commander Information Actions")
		data["Data"] = []
		FileCommanderData.__init__(self, session, data)
		StatInfo.__init__(self)
		numberScaler = NumberScaler()
		self.path = normpath(path)
		self.target = target
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["detailAction"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyDetails, _("Display more information about this file"))
		}, prio=0, description=_("Directory/File Status Actions"))
		self["detailAction2"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyDetails2, _("Display more information about this file"))
		}, prio=0, description=_("Directory/File Status Actions"))
		extension = splitext(self.path)[1].lower()
		if extension in MEDIA_FILES:
			if self.isPackageInstalled("mediainfo"):
				self["key_green"].setText(_("MediaInfo"))
				self["detailAction"].setEnabled(True)
			if self.isPackageInstalled("ffmpeg"):
				self["key_yellow"].setText(_("FFmpeg Probe"))
				self["detailAction2"].setEnabled(True)
		elif extension in TEXT_FILES:
			self["key_green"].setText(_("View File"))
			self["detailAction"].setEnabled(True)
		elif extension in ARCHIVE_FILES:
			self["key_green"].setText(_("Unpack File"))
			self["detailAction"].setEnabled(True)
		else:
			self["key_green"].setText("")
			self["detailAction"].setEnabled(False)
		info = [f"{_("Directory") if isdir(self.path) else _("File")}:|{self.path}"]
		info.append("")
		directorySizeIndex = None
		try:
			status = lstat(self.path)
			mode = status.st_mode
			fileType = {
				S_IFSOCK: _("Socket"),
				S_IFLNK: _("Symbolic link"),
				S_IFREG: _("Regular file"),
				S_IFBLK: _("Block device"),
				S_IFDIR: _("Directory"),
				S_IFCHR: _("Character device"),
				S_IFIFO: _("FIFO"),
			}.get(S_IFMT(mode), _("Unknown"))
			info.append(f"{_("Type")}:|{fileType}")
			if isfile(self.path):
				info.append(f"{_("Content")}:|{_("Calculating...")}")
			if S_ISLNK(mode):
				try:
					link = readlink(self.path)
				except OSError as err:
					link = _("Error %d: %s") % (err.errno, err.strerror)
				info.append(f"{_("Link target")}:|{link}")
			info.append(f"{_("Owner")}:|{self.username(status.st_uid)} ({status.st_uid})")
			info.append(f"{_("Group")}:|{self.groupname(status.st_gid)} ({status.st_gid})")
			permissions = S_IMODE(mode)
			info.append(f"{_("Permissions")}:|{filemode(mode)} ({permissions:04o})")
			if not (S_ISCHR(mode) or S_ISBLK(mode)):
				info.append(f"{_("Size")}:|{status.st_size:,}   ({numberScaler.scale(status.st_size, style="Si", maxNumLen=3, decimals=3)})   ({numberScaler.scale(status.st_size, style="Iec", maxNumLen=3, decimals=3)})")
			if isdir(self.path):
				info.append(f"{_("Tree size")}:|{_("Calculating...")}")
				directorySizeIndex = len(info) - 1
			info.append(f"{_("Modified")}:|{self.formatTime(status.st_mtime)}")
			info.append(f"{_("Accessed")}:|{self.formatTime(status.st_atime)}")
			info.append(f"{_("Changed")}:|{self.formatTime(status.st_ctime)}")
			info.append(f"{_("Links")}:|{status.st_nlink}")
			info.append(f"{_("Inode")}:|{status.st_ino}")
			info.append(f"{_("Device number")}:|{(status.st_dev >> 8) & 0xff}, {status.st_dev & 0xff}")
			self.textBuffer = ""
			if isfile(path) and status.st_size > 0:
				self.processArguments(None, ["/usr/bin/file", "/usr/bin/file", self.path], None, displayFileInfo)
			elif isdir(path) and directorySizeIndex:
				self.processArguments(None, ["/bin/busybox", "du", "-H", "-b", "-l", "-d", "0", self.path], None, displayDirectorySize)
			self["data"].setText("\n".join(info))
			self["navigationActions"].setEnabled(self["data"].isNavigationNeeded())
		except OSError as err:
			self.session.open(MessageBox, _("Error %s: Unable to get information for '%s'!  (%s)") % (err.errno, self.path, err.strerror), MessageBox.TYPE_ERROR, windowTitle=data["Title"])
			self.close()

	def keyDetails(self):
		extension = splitext(self.path)[1].lower()
		if extension in MEDIA_FILES:
			self.session.open(FileCommanderMediaInfo, self.path)
		elif extension in TEXT_FILES:
			text = True
			try:
				with open(self.path, encoding="UTF-8", errors="strict") as fd:
					fd.read(BLOCK_CHUNK_SIZE)
			except Exception:
				text = False
			self.session.open(FileCommanderFileViewer, self.path, isText=text, initialView="T" if text else "H")
		elif extension in ARCHIVE_FILES:
			self.session.open(FileCommanderArchiveView, self.path, self.target)

	def keyDetails2(self):
		self.session.open(FileCommanderMediaInfo, self.path, program="ffprobe")


class FileCommanderMediaInfo(FileCommanderData):
	def __init__(self, session, path, program="mediainfo"):
		data = {}
		data["Screen"] = "FileCommanderMediaInfo"
		data["Title"] = _("File Commander Media Information")
		data["Description"] = _("File Commander Media Information Actions")
		data["Data"] = []
		FileCommanderData.__init__(self, session, data)
		self.path = normpath(path)
		self.jsonData = ""
		self.program = program
		self.callLater(self.viewMediaInfo)

	def viewMediaInfo(self):
		def displayJson(retVal):
			info = [f"{_("File")}:|{self.path}"]
			try:
				info.append("")
				jsonData = loads(self.textBuffer)
				for index, track in enumerate(jsonData["media"]["track"]):
					info.append(f"Track-{index + 1}:")
					info.extend([f"{x}:|{y}" for x, y in track.items()])
			except Exception as err:
				print(f"[FileCommander] Error: Unable to parse the mediainfo json data!  ({err})")
			self["data"].setText("\n".join(info))
			self["navigationActions"].setEnabled(self["data"].isNavigationNeeded())

		def displayFFprobe(retVal):
			info = [f"{_("File")}:|{self.path}"]
			info.append("")
			info.extend(self.textBuffer.split("\n"))
			self["data"].setText("\n".join(info))
			self["navigationActions"].setEnabled(self["data"].isNavigationNeeded())

		self.textBuffer = ""
		if self.program == "mediainfo":
			self.processArguments(None, ["/usr/bin/mediainfo", "/usr/bin/mediainfo", "--Output=JSON", self.path], None, displayJson)
		else:
			self.processArguments(None, ["/usr/bin/ffprobe", "/usr/bin/ffprobe", "-hide_banner", self.path], None, displayFFprobe)


class FileCommanderTextEditor(Screen):
	skin = """
	<screen name="FileCommanderTextEditor" title="File Commander Text Editor" position="40,80" size="1200,610" resolution="1280,720">
		<widget name="path" position="0,0" size="1030,50" font="Regular;20" foregroundColor="#00fff000" valign="center" />
		<widget name="location" position="1050,12" size="150,25" font="Regular;20" foregroundColor="#00fff000" halign="right" valign="center" />
		<widget name="data" position="0,60" size="1200,500" font="Console;20" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="380,e-40" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="570,e-40" size="180,40" backgroundColor="key_blue" conditional="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, path):
		Screen.__init__(self, session, enableHelp=True)
		self.skinName = ["FileCommanderTextEditor"]
		if not self.getTitle():
			self.setTitle(_("File Commander Text Editor"))
		self.path = normpath(path)
		self.data = []
		self["path"] = Label(self.path)
		self["location"] = Label()
		self["data"] = MenuList(self.data)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Delete Line"))
		self["key_blue"] = StaticText(_("Insert Line"))
		self["key_text"] = StaticText(_("TEXT"))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions", "FileCommanderActions"], {
			"cancel": (self.keyCancel, _("Exit editor and discard any changes")),
			"ok": (self.keyEdit, _("Edit current line")),
			"red": (self.keyCancel, _("Exit editor and discard any changes")),
			"green": (self.keySave, _("Exit editor and save any changes")),
			"yellow": (self.keyDelete, _("Delete current line")),
			"blue": (self.keyInsert, _("Insert line before current line")),
			"greenlong": (self.keyDeleteEmptyLines, _("Delete empty and white space only lines")),
			"yellowlong": (self.keyDeleteDuplicateLines, _("Delete all duplicated lines")),
			"bluelong": (self.keyDuplicateCurrentLine, _("Duplicate the current line")),
			"text": (self.keySortTextMenu, _("Open file sort menu")),
			"top": (self["data"].goTop, _("Move to first line / screen")),
			"pageUp": (self["data"].goPageUp, _("Move up a screen")),
			"up": (self["data"].goLineUp, _("Move up a line")),
			"down": (self["data"].goLineDown, _("Move down a line")),
			"pageDown": (self["data"].goPageDown, _("Move down a screen")),
			"bottom": (self["data"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("File Commander Text Editor Actions"))
		self["moveUpAction"] = HelpableActionMap(self, ["NavigationActions"], {
			"first": (self.keyMoveLineUp, _("Move the current line up")),
		}, prio=0, description=_("File Commander Text Editor Actions"))
		self["moveDownAction"] = HelpableActionMap(self, ["NavigationActions"], {
			"last": (self.keyMoveLineDown, _("Move the current line down")),
		}, prio=0, description=_("File Commander Text Editor Actions"))
		self.isChanged = False
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["data"].enableAutoNavigation(False)  # Override listbox navigation.
		self.data = fileReadLines(self.path, default=[], source=MODULE_NAME)
		self["data"].setList(self.data)
		self["data"].onSelectionChanged.append(self.updateStatus)
		self.updateStatus()

	def updateStatus(self):
		count = self["data"].count()
		index = self["data"].getCurrentIndex()
		if count:
			self["location"].setText(_("Line %d / %d") % (index + 1, count))
		else:
			self["location"].setText(_("Empty file"))
		self["moveUpAction"].setEnabled(index > 0)
		self["moveDownAction"].setEnabled(index < count - 1)

	def keyCancel(self):
		def keyCancelCallback(answer):
			if answer:
				self.close()

		if self.isChanged:
			self.session.openWithCallback(keyCancelCallback, MessageBox, _("The file '%s' has been changed. Do you want to discard the changes?") % self.path, MessageBox.TYPE_YESNO, default=False, windowTitle=self.getTitle())
		else:
			self.close()

	def keyDelete(self):
		if self.data:
			del self.data[self["data"].getCurrentIndex()]
			self["data"].setList(self.data)
			self.isChanged = True

	def keyDeleteDuplicateLines(self):
		length = len(self.data)
		unique = []
		for line in self.data:
			if line not in unique:
				unique.append(line)
		self.data = unique
		self["data"].setList(unique)
		if len(self.data) != length:
			self.isChanged = True

	def keyDeleteEmptyLines(self):
		length = len(self.data)
		# self.data = [x for x in self.data if x]
		self.data = [x for x in self.data if x.strip()]
		self["data"].setList(self.data)
		if len(self.data) != length:
			self.isChanged = True

	def keyDuplicateCurrentLine(self):
		self.data.insert(self["data"].getCurrentIndex(), self["data"].getCurrent())
		self["data"].setList(self.data)
		self.isChanged = True

	def keyEdit(self):
		def keyEditCallback(line):
			if line is not None:
				# Find and restore TABs from a special single character.  This could also be helpful for NEWLINE as well.
				# line = line.replace("<TAB>", "\t") # Find and restore TABs.  This could also be helpful for NEWLINE as well.
				self.data[self["data"].getCurrentIndex()] = line
				self["data"].setList(self.data)
				self.isChanged = True

		line = self["data"].getCurrent()
		# Find and replace TABs with a special single character.  This could also be helpful for NEWLINE as well.
		# line = line.replace("\t", "<TAB>") # Find and replace TABs.  This could also be helpful for NEWLINE as well.
		currPos = None if config.plugins.FileCommander.editLineEnd.value is True else 0
		self.session.openWithCallback(keyEditCallback, VirtualKeyBoard, title=f"{_("Original")}: {line}", text=line, currPos=currPos, allMarked=False, windowTitle=self.getTitle())

	def keyInsert(self):
		self.data.insert(self["data"].getCurrentIndex(), "")
		self["data"].setList(self.data)
		self.isChanged = True

	def keyMoveLineUp(self):
		self.moveLine(-1)

	def keyMoveLineDown(self):
		self.moveLine(+1)

	def moveLine(self, direction):
		index = self["data"].getCurrentIndex() + direction
		self.data.insert(index, self.data.pop(index - direction))
		self["data"].setList(self.data)
		self["data"].setCurrentIndex(index)
		self.isChanged = True

	def keySave(self):
		def keySaveCallback(answer):
			if answer:
				if isfile(self.path):
					copyFile(self.path, f"{self.path}.bak")
				if fileWriteLines(self.path, "\n".join(self.data), source=MODULE_NAME) == 0:
					self.session.open(MessageBox, _("Error: There was a problem writing '%s'!") % self.path, MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
			self.close()

		if self.isChanged:
			msg = [_("The file '%s' has been changed. Do you want to save it?") % self.path]
			msg.append("")
			msg.append(_("WARNING:"))
			msg.append(_("The authors are NOT RESPONSIBLE for DATA LOSS OR DAMAGE!"))
			self.session.openWithCallback(keySaveCallback, MessageBox, "\n".join(msg), MessageBox.TYPE_YESNO, windowTitle=self.getTitle())
		else:
			self.close()

	def keySortTextMenu(self):
		def keySortTextMenuCallback(answer):
			if answer:
				if answer == "SORTA":
					self.data.sort()
				elif answer == "SORTD":
					self.data.sort(reverse=True)
				self["data"].setList(self.data)
				self.isChanged = True

		choiceList = [
			(_("Ascending"), "SORTA"),
			(_("Descending"), "SORTD")
		]
		self.session.openWithCallback(keySortTextMenuCallback, MessageBox, _("Select the sort order for the file lines:"), list=choiceList, default=0, windowTitle=self.getTitle())


class FileCopyTask(Job):
	def __init__(self, srcPaths, dstPath, title):
		Job.__init__(self, title)
		count = len(srcPaths)
		for index, srcPath in enumerate(srcPaths):
			taskName = _("Directory/File %d of %d" % (index + 1, count))
			FileTransferTask(self, taskName, srcPath, dstPath, FileTransferTask.JOB_COPY)


class FileMoveTask(Job):
	def __init__(self, srcPaths, dstPath, title):
		Job.__init__(self, title)
		count = len(srcPaths)
		for index, srcPath in enumerate(srcPaths):
			taskName = _("Directory/File %d of %d" % (index + 1, count))
			FileTransferTask(self, taskName, srcPath, dstPath, FileTransferTask.JOB_MOVE)


class FileDeleteTask(Job):
	def __init__(self, srcPaths, title):
		Job.__init__(self, title)
		count = len(srcPaths)
		for index, srcPath in enumerate(srcPaths):
			taskName = _("Directory/File %d of %d" % (index + 1, count))
			if isfile(srcPath) or islink(srcPath):
				FileTransferTask(self, taskName, srcPath, dirname(normpath(srcPath)), FileTransferTask.JOB_DELETE)
			else:
				FileTransferTask(self, taskName, srcPath, dirname(normpath(srcPath)), FileTransferTask.JOB_DELETE_TREE)


class FileTestTask(Job):
	def __init__(self, job, srcPaths, dstPath, title):
		Job.__init__(self, title)
		count = len(srcPaths)
		for index, srcPath in enumerate(srcPaths):
			taskName = _("File %d of %d" % (index + 1, count))
			FileTransferTask(self, taskName, srcPath, dstPath, FileTransferTask.JOB_TEST)


class FileTransferTask(Task):
	JOB_COPY = 0
	JOB_MOVE = 1
	JOB_DELETE = 2
	JOB_DELETE_TREE = 3
	JOB_TEST = 4
	JOB_NAMES = [
		_("copy"),
		_("move"),
		_("delete"),
		_("tree delete"),
		_("text")
	]

	def __init__(self, job, taskName, srcPath, dstPath, jobType):
		Task.__init__(self, job, taskName)
		if lexists(srcPath) and exists(dstPath):
			self.srcPath = srcPath
			self.dstPath = dstPath
			target = join(dstPath, "") if isdir(srcPath) else join(dstPath, basename(normpath(srcPath)))
			if jobType == self.JOB_COPY:
				cmdLine = ("cp", "-pr", srcPath, target)
			elif jobType == self.JOB_MOVE:
				cmdLine = ("mv", "-f", srcPath, target)
			elif jobType == self.JOB_DELETE:
				cmdLine = ("rm", "-f", srcPath)
			elif jobType == self.JOB_DELETE_TREE:
				cmdLine = ("rm", "-fr", srcPath)
			elif jobType == self.JOB_TEST:
				cmdLine = ("sleep", "100")
			else:
				print(f"[Directories] FileTransferTask Error: Unknown job type '{jobType}' specified!")
				cmdLine = None
			self.mountPoints = [normpath(x.mountpoint) for x in harddiskmanager.getMountedPartitions()]
			self.initialSize = self.dirSize(target) if isdir(target) else 0
			if isfile(srcPath):
				self.dstPath = target
			if cmdLine:
				self.postconditions.append(TaskPostConditions())
				self.processStdout = taskProcessStdout
				self.processStderr = taskProcessStderr
				# print(f"[Directories] FileTransferTask DEBUG: Command line '/bin/busybox {' '.join(cmdLine)}'.")
				self.setCommandline("/bin/busybox", cmdLine)
				# self.nice = 0
				self.ionice = 8
				self.progressTimer = eTimer()
				self.progressTimer.callback.append(self.progressUpdate)

	def progressUpdate(self):
		if exists(self.dstPath):
			dstSize = float((self.dirSize(self.dstPath) - self.initialSize) if isdir(self.dstPath) else getsize(self.dstPath))
			self.setProgress(dstSize / self.srcSize * 100.0)
		else:
			self.setProgress(100)
		self.progressTimer.start(self.updateTime, True)

	def prepare(self):
		self.srcSize = float(self.dirSize(self.srcPath) if isdir(self.srcPath) else lstat(self.srcPath).st_size)
		self.updateTime = max(1000, int(self.srcSize * 0.000001 * 0.5))  # Based on 20Mb/s transfer rate.
		self.progressTimer.start(self.updateTime, True)

	def afterRun(self):
		if hasattr(self, "progressTimer"):
			self.progressTimer.stop()
		self.setProgress(100)

	def finish(self, aborted=False):
		self.afterRun()
		notMet = []
		if aborted:
			AddNotification(MessageBox, _("File transfer was canceled by user!"), MessageBox.TYPE_INFO)
		else:
			for postCondition in self.postconditions:
				if not postCondition.check(self):
					notMet.append(postCondition)
		self.cleanup(notMet)
		self.callback(self, notMet)

	def dirSize(self, directory):
		totalSize = getsize(directory)
		for item in listdir(directory):
			path = join(directory, item)
			if path in ("/dev", "/proc", "/run", "/sys") or path in self.mountPoints or islink(path):  # Don't analyze system directories, mount points or links.
				continue
			if isfile(path):
				totalSize += getsize(path)
			elif isdir(path):
				totalSize += self.dirSize(path)
		return totalSize


taskSTDOut = []
taskSTDErr = []


class TaskPostConditions(Condition):
	def __init__(self):
		Condition.__init__(self)
		self.errorMessage = ""

	def check(self, task):
		global taskSTDOut, taskSTDErr
		result = False
		self.errorMessage = ""
		if config.plugins.FileCommander.showScriptCompletedMessage.value:
			message = []
			if task.returncode != 0:
				message.append(_("Task '%s' ended with error number %d!") % (task.name, task.returncode))
				# messageType = MessageBox.TYPE_ERROR
			if taskSTDErr:
				message.append(_("Task '%s' ended with an error message!") % task.name)
				# messageType = MessageBox.TYPE_ERROR
			if task.returncode == 0 and not taskSTDErr:
				message.append(_("Task '%s' ended successfully.") % task.name)
				# messageType = MessageBox.TYPE_INFO
				result = True
			if message:
				message.append("")
			lines = config.plugins.FileCommander.scriptMessageLength.value * -1
			if taskSTDOut:
				message.append(_("Output text:"))
				message.extend(taskSTDOut[lines:])
			if taskSTDErr:
				message.append(_("Error text:"))
				message.extend(taskSTDErr[lines:])
			if message:
				self.errorMessage = "\n".join(message)
				print(f"[FileCommander] Task output:\n{message}")
				# self.showMessage("\n".join(message), messageType)
		taskSTDOut = []
		taskSTDErr = []
		return result

	def showMessage(self, message, messageType, timeout=config.plugins.FileCommander.completeMessageTimeout.value):
		if not running:
			from Screens.Standby import inStandby
			if InfoBar.instance and not inStandby:
				InfoBar.instance.openInfoBarMessage(message, messageType, timeout=timeout)
			else:
				AddNotification(MessageBox, message, messageType, timeout=timeout)

	def getErrorMessage(self, task):
		return self.errorMessage


def taskProcessStdout(data):
	global taskSTDOut
	data = data.decode()
	for line in data.split("\n"):
		if line:
			taskSTDOut.append(line)
	while len(taskSTDOut) > 10:
		taskSTDOut.pop(0)


def taskProcessStderr(data):
	global taskSTDErr
	data = data.decode()
	for line in data.split("\n"):
		if line:
			taskSTDErr.append(line)
	while len(taskSTDErr) > 10:
		taskSTDErr.pop(0)


conversionDone = False


# Start Routines
#
def convertSettings():
	global conversionDone
	if conversionDone:
		return
	attributes = (
		("add_extensionmenu_entry", "addToExtensionMenu"),
		("add_mainmenu_entry", "addToMainMenu"),
		("bookmarks", "bookmarks"),
		("calculate_directorysize", None),
		("change_navbutton", None),
		("diashow", None),
		("editposition_lineend", "editLineEnd"),
		("extension", "extension"),
		("firstDirs", "directoriesFirst"),
		("hashes", None),
		("input_length", None),
		("my_extension", "myExtensions"),
		("path_default", "defaultPathLeft"),
		("pathDefault", "defaultPathLeft"),
		("path_left", None),
		("path_right", None),
		("savedir_left", "savePathLeft"),
		("savedir_right", "savePathRight"),
		("script_messagelen", "scriptMessageLength"),
		("script_priority_ionice", "scriptPriorityIONice"),
		("script_priority_nice", "scriptPriorityNice"),
		("showScriptCompleted_message", "showScriptCompletedMessage"),
		("showTaskCompleted_message", "showTaskCompletedMessage"),
		("sortDirs", "sortDirectories"),
		("sortFiles_left", "sortFilesLeft"),
		("sortFiles_right", "sortFilesRight"),
		("unknown_extension_as_text", "useViewerForUnknown")
	)
	config.plugins.filecommander = ConfigSubsection()
	for old, new in attributes:
		setattr(config.plugins.filecommander, old, ConfigText(default=""))
		value = getattr(config.plugins.filecommander, old).value
		if value and new:
			if value == "True":
				value = True
			if value == "False":
				value = False
			if old == "bookmarks":
				value = [x for x in value[2:-2].split("', '")]
			getattr(config.plugins.FileCommander, new).value = value
		getattr(config.plugins.filecommander, old).value = ""
	config.plugins.filecommander.save()
	config.plugins.FileCommander.save()
	conversionDone = True


def filescanOpen(list, session, **kwargs):
	path = "/".join(list[0].path.split("/")[:-1]) + "/"
	session.open(FileCommander, pathLeft=path)


def startFromFilescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	return Scanner(
		mimetypes=None,
		paths_to_scan=[
			ScanPath(path="", with_subdirs=False),
		],
		name=PROGRAM_NAME,
		description=_("Open with File Commander"),
		openfnc=filescanOpen,
	)


def startFromMainMenu(menuid, **kwargs):
	if menuid == "mainmenu":  # Starting from main menu.
		convertSettings()
		return [(PROGRAM_NAME, startFromPluginMenu, "filecommand", 1)]
	return []


def startFromPluginMenu(session, **kwargs):
	convertSettings()
	session.openWithCallback(exit, FileCommander)


def exit(session, result):
	if not result:
		session.openWithCallback(exit, FileCommander)


def Plugins(path, **kwargs):
	plugin = [
		PluginDescriptor(name=PROGRAM_NAME, description=f"{PROGRAM_DESCRIPTION} ({PROGRAM_VERSION})", where=PluginDescriptor.WHERE_PLUGINMENU, icon="FileCommander.png", fnc=startFromPluginMenu),
		# PluginDescriptor(name=PROGRAM_NAME, where=PluginDescriptor.WHERE_FILESCAN, fnc=startFromFilescan)  # Buggy!!!
	]
	if config.plugins.FileCommander.addToExtensionMenu.value:
		plugin.append(PluginDescriptor(name=PROGRAM_NAME, description=PROGRAM_DESCRIPTION, where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=startFromPluginMenu))
	if config.plugins.FileCommander.addToMainMenu.value:
		plugin.append(PluginDescriptor(name=PROGRAM_NAME, description=PROGRAM_DESCRIPTION, where=PluginDescriptor.WHERE_MENU, fnc=startFromMainMenu))
	return plugin
