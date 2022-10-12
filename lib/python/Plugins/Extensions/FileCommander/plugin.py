from errno import EEXIST
from grp import getgrgid
from mimetypes import guess_type
from os import R_OK, X_OK, access, chmod, environ, lstat, mkdir, readlink, remove, rename, rmdir, sep, stat as osstat, statvfs, symlink
from os.path import basename, dirname, exists, isfile, isdir, islink, join as pathjoin, normpath, splitext
from pathlib import Path
from pwd import getpwuid
from puremagic import PureError, from_file as fromfile, magic_file as magicfile
from re import compile, search
from string import digits
from sys import maxsize
import stat
from tempfile import gettempdir, mkdtemp
from time import localtime, strftime

from enigma import eActionMap, eConsoleAppContainer, ePicLoad, eServiceReference, eTimer, getDesktop

from Components.ActionMap import ActionMap, HelpableActionMap
from Components.AVSwitch import AVSwitch
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.config import config, ConfigInteger, ConfigYesNo, ConfigText, ConfigDirectory, ConfigSelection, ConfigSet, NoSave, ConfigNothing, ConfigLocations, ConfigSelectionNumber, ConfigSubsection
from Components.Console import Console as console
from Components.FileList import AUDIO_EXTENSIONS, DVD_EXTENSIONS, EXTENSIONS, FILE_PATH, FILE_IS_DIR, FileList, FileListMultiSelect, IMAGE_EXTENSIONS, MOVIE_EXTENSIONS
from Components.FileTransfer import FileTransferJob
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.PluginComponent import plugins
from Components.Scanner import openFile
from Components.ScrollLabel import ScrollLabel
from Components.Sources.Boolean import Boolean
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.Task import Condition, Job, job_manager, Task
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.Console import Console
from Screens.DVD import DVDPlayer
from Screens.HelpMenu import HelpableScreen
from Screens.InfoBar import InfoBar, MoviePlayer
from Screens.LocationBox import LocationBox
from Screens.MessageBox import MessageBox
from Screens.MovieSelection import defaultMoviePath
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.TaskList import TaskListScreen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.Directories import SCOPE_PLUGINS, copyFile, fileReadLines, fileWriteLines, resolveFilename, shellquote
from Tools.BoundFunction import boundFunction
from Tools.UnitConversions import UnitScaler, UnitMultipliers
import Tools.Notifications

MODULE_NAME = __name__.split(".")[-1]

PNAME = _("File Commander")
PDESC = _("Manage and explore files and directories.")
PVERS = "%s%s" % (_("Version"), "3.00")

ALL_MOVIE_EXTENSIONS = MOVIE_EXTENSIONS.union((".ts",))
RECORDING_EXTENSIONS = frozenset((".ap", ".cuts", ".eit", ".meta", ".sc"))
TEXT_EXTENSIONS = frozenset((".bak", ".cfg", ".conf", ".html", ".log", ".lst", ".meta", ".py", ".srt", ".txt", ".xml"))
ARCHIVE_FILES = frozenset([x for x, y in EXTENSIONS.items() if y in ("7z", "bz2", "gz", "ipk", "rar", "tar", "xz", "zip")])
MEDIA_FILES = frozenset([x for x, y in EXTENSIONS.items() if y in ("music", "picture", "movie")])
TEXT_FILES = frozenset([x for x, y in EXTENSIONS.items() if y in ("cfg", "html", "log", "lst", "py", "sh", "txt", "xml")])

config.plugins.filecommander = ConfigSubsection()
config.plugins.filecommander.add_mainmenu_entry = ConfigYesNo(default=False)
config.plugins.filecommander.add_extensionmenu_entry = ConfigYesNo(default=False)
config.plugins.filecommander.savedir_left = ConfigYesNo(default=False)
config.plugins.filecommander.savedir_right = ConfigYesNo(default=False)
config.plugins.filecommander.editposition_lineend = ConfigYesNo(default=False)
config.plugins.filecommander.pathDefault = ConfigDirectory(default="")
config.plugins.filecommander.pathLeft = ConfigText(default="")
config.plugins.filecommander.pathRight = ConfigText(default="")
config.plugins.filecommander.my_extension = ConfigText(default="", visible_width=15, fixed_size=False)
config.plugins.filecommander.extension = ConfigSelection(default="^.*", choices=[
	("^.*", _("Without")),
	("myfilter", _("My extension")),
	("(?i)^.*(%s)$" % "|".join(sorted([".ts"] + [x == ".eit" and x or ".ts.%s" % x for x in RECORDING_EXTENSIONS])), _("Recordings")),
	("(?i)^.*(%s)$" % "|".join(sorted((ext for ext, type in EXTENSIONS.items() if type == "movie"))), _("Movies")),
	("(?i)^.*(%s)$" % "|".join(sorted((ext for ext, type in EXTENSIONS.items() if type == "music"))), _("Music")),
	("(?i)^.*(%s)$" % "|".join(sorted((ext for ext, type in EXTENSIONS.items() if type == "picture"))), _("Pictures"))
])
config.plugins.filecommander.change_navbutton = ConfigSelection(default="no", choices=[
	("no", _("No")),
	("always", _("Channel button always changes sides")),
	("yes", _("Yes"))
])
config.plugins.filecommander.input_length = ConfigInteger(default=40, limits=(1, 100))
config.plugins.filecommander.diashow = ConfigInteger(default=5000, limits=(1000, 10000))
config.plugins.filecommander.slideshowDelay = ConfigSelection(default=5, choices=[(x, ngettext("%d Second", "%d Second", x) % x) for x in range(1, 61)])
config.plugins.filecommander.slideshowLoop = ConfigYesNo(default=True)
config.plugins.filecommander.script_messagelen = ConfigSelectionNumber(default=3, stepwidth=1, min=1, max=10, wraparound=True)
config.plugins.filecommander.script_priority_nice = ConfigSelectionNumber(default=0, stepwidth=1, min=0, max=19, wraparound=True)
config.plugins.filecommander.script_priority_ionice = ConfigSelectionNumber(default=0, stepwidth=3, min=0, max=3, wraparound=True)
config.plugins.filecommander.unknown_extension_as_text = ConfigYesNo(default=False)
config.plugins.filecommander.sortDirs = ConfigSelection(default="0.0", choices=[
	("0.0", _("Name")),
	("0.1", _("Name reverse")),
	("1.0", _("Date")),
	("1.1", _("Date reverse"))
])
choicelist = [
	("0.0", _("Name")),
	("0.1", _("Name reverse")),
	("1.0", _("Date")),
	("1.1", _("Date reverse")),
	("2.0", _("Size")),
	("2.1", _("Size reverse"))
]
config.plugins.filecommander.sortFiles_left = ConfigSelection(default="1.1", choices=choicelist)
config.plugins.filecommander.sortFiles_right = ConfigSelection(default="1.1", choices=choicelist)
config.plugins.filecommander.firstDirs = ConfigYesNo(default=True)
config.plugins.filecommander.pathLeft_selected = ConfigYesNo(default=True)
config.plugins.filecommander.showTaskCompleted_message = ConfigYesNo(default=True)
config.plugins.filecommander.showScriptCompleted_message = ConfigYesNo(default=True)
CHECKSUM_HASHES = {
	"MD5": "md5sum",
	"SHA1": "sha1sum",
	"SHA3": "sha3sum",
	"SHA256": "sha256sum",
	"SHA512": "sha512sum",
}
config.plugins.filecommander.hashes = ConfigSet(list(CHECKSUM_HASHES.keys()), default=["MD5"])
config.plugins.filecommander.bookmarks = ConfigLocations(default=None)
config.plugins.filecommander.fake_entry = NoSave(ConfigNothing())
defaultSort = "%s,%s" % (config.plugins.filecommander.sortDirs.value, config.plugins.filecommander.sortFiles_left.value)
config.plugins.filecommander.sortingLeft_tmp = NoSave(ConfigText(default=defaultSort))
defaultSort = "%s,%s" % (config.plugins.filecommander.sortDirs.value, config.plugins.filecommander.sortFiles_right.value)
config.plugins.filecommander.sortingRight_tmp = NoSave(ConfigText(default=defaultSort))
config.plugins.filecommander.pathLeft_tmp = NoSave(ConfigText(default=config.plugins.filecommander.pathLeft.value))
config.plugins.filecommander.pathRight_tmp = NoSave(ConfigText(default=config.plugins.filecommander.pathRight.value))
config.plugins.filecommander.calculate_directorysize = ConfigYesNo(default=False)


class StatInfo:
	SIZESCALER = UnitScaler(scaleTable=UnitMultipliers.Jedec, maxNumLen=3, decimals=1)

	@staticmethod
	def fileTypeStr(mode):
		return {
			stat.S_IFSOCK: _("Socket"),
			stat.S_IFLNK: _("Symbolic link"),
			stat.S_IFREG: _("Regular file"),
			stat.S_IFBLK: _("Block device"),
			stat.S_IFDIR: _("Directory"),
			stat.S_IFCHR: _("Character device"),
			stat.S_IFIFO: _("FIFO"),
		}.get(stat.S_IFMT(mode), _("Unknown"))

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
		return strftime("%s %s" % (config.usage.date.daylong.value, config.usage.time.long.value), localtime(time))


class FileCommanderBase(Screen, HelpableScreen, StatInfo):
	skin = ["""
	<screen name="FileCommander" title="File Commander" position="40,80" size="1200,600" resolution="1280,720">
		<widget name="list_left_head1" position="0,0" size="590,50" font="Regular;20" foregroundColor="#00fff000" valign="center" />
		<widget source="list_left_head2" render="Listbox" position="0,50" size="590,25" foregroundColor="#00fff000" selection="0">
			<convert type="TemplatedMultiContent">
				{
				"template":
					[
					MultiContentEntryText(pos=(%d, 0), size=(%d, %d), font=0, flags= RT_HALIGN_LEFT, text=1),  # Index 1 is a symbolic mode.
					MultiContentEntryText(pos=(%d, 0), size=(%d, %d), font=0, flags= RT_HALIGN_RIGHT, text=11),  # Index 11 is the scaled size.
					MultiContentEntryText(pos=(%d, 0), size=(%d, %d), font=0, flags= RT_HALIGN_RIGHT, text=13),  # Index 13 is the modification time.
					],
				"fonts": [parseFont("Regular;%d")],
				"itemHeight": %d,
				"selectionEnabled": False
				}
			</convert>
		</widget>
		<widget name="list_right_head1" position="610,0" size="590,50" font="Regular;20" foregroundColor="#00fff000" valign="center" />
		<widget source="list_right_head2" render="Listbox" position="610,50" size="590,25" foregroundColor="#00fff000" selection="0">
			<convert type="TemplatedMultiContent">
				{
				"template":
					[
					MultiContentEntryText(pos=(%d, 0), size=(%d, %d), font=0, flags= RT_HALIGN_LEFT, text=1),  # Index 1 is a symbolic mode.
					MultiContentEntryText(pos=(%d, 0), size=(%d, %d), font=0, flags= RT_HALIGN_RIGHT, text=11),  # Index 11 is the scaled size.
					MultiContentEntryText(pos=(%d, 0), size=(%d, %d), font=0, flags= RT_HALIGN_RIGHT, text=13),  # Index 13 is the modification time.
					],
				"fonts": [parseFont("Regular;%d")],
				"itemHeight": %d,
				"selectionEnabled": False
				}
			</convert>
		</widget>
		<widget name="list_left" position="0,80" size="590,450" />
		<widget name="list_right" position="610,80" size="590,450" />
		<widget name="sort_left" position="0,530" size="590,20" font="Regular;17" foregroundColor="#00fff000" halign="center" />
		<widget name="sort_right" position="610,530" size="590,20" font="Regular;17" foregroundColor="#00fff000" halign="center" />
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
		<widget source="key_menu" render="Label" position="e-350,e-40" size="80,40" backgroundColor="key_back" conditional="key_menu" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_info" render="Label" position="e-260,e-40" size="80,40" backgroundColor="key_back" conditional="key_info" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_text" render="Label" position="e-170,e-40" size="80,40" backgroundColor="key_back" conditional="key_text" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>""",
		0, 120, 25,
		130, 130, 25,
		330, 260, 25,
		20,
		25,
		0, 120, 25,
		130, 130, 25,
		330, 260, 25,
		20,
		25
	]

	PROG_PACKAGES = {
		"file": "file",
		"ffprobe": "ffmpeg",
		# "mediainfo": "mediainfo",
	}

	def __init__(self, session):
		Screen.__init__(self, session, mandatoryWidgets=["Test"])
		HelpableScreen.__init__(self)
		StatInfo.__init__(self)
		self.multiselect = False
		self.calculate_directorysize = False
		self.skinName = ["FileCommander", "FileCommanderScreen", "FileCommanderScreenFileSelect"]
		self["key_menu"] = StaticText(_("MENU"))
		self["key_info"] = StaticText(_("INFO"))
		self["key_text"] = StaticText(_("TEXT"))
		self["key_red"] = StaticText(_("Delete"))
		self["key_green"] = StaticText(_("Move"))
		self["key_yellow"] = StaticText(_("Copy"))
		self["key_blue"] = StaticText("")
		self["baseactions"] = HelpableActionMap(self, ["DirectionActions", "OkCancelActions", "InfoActions", "MenuActions"], {
			"up": (self.goUp, _("Move up list")),
			"down": (self.goDown, _("Move down list")),
			"left": (self.goLeftB, _("Page up list")),
			"right": (self.goRightB, _("Page down list")),
			"info": (self.openTasklist, _("Show task list")),
			# "directoryUp": (self.goParentfolder, _("Go to parent directory")), # TODO define a key
		}, prio=-1, description=_("File Commander Actions"))

		# Can warning if image information is not available.
		# self.session.open(MessageBox, _("The ImageViewer component of FileCommander requires the PicturePlayer extension. Install PicturePlayer to enable this feature."), MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
		self.updateHeadLeft_Timer = eTimer()
		self.updateHeadRight_Timer = eTimer()
		self.updateHeadLeft_Timer.callback.append(self.updateHeadLeft)
		self.updateHeadRight_Timer.callback.append(self.updateHeadRight)

	def calculate_directorysizeChanged(self, configElement):
		self.calculate_directorysize = configElement.value

	@staticmethod
	def fileFilter():
		if config.plugins.filecommander.extension.value == "myfilter":
			return "^.*\.%s" % config.plugins.filecommander.my_extension.value
		else:
			return config.plugins.filecommander.extension.value

	def layoutFinished(self):
		self["list_left"].onSelectionChanged.append(self.selectionChangedLeft)
		self["list_right"].onSelectionChanged.append(self.selectionChangedRight)

	def goParentfolder(self):
		if self.multiselect and self.ACTIVELIST == self.SOURCELIST:
			return
		if self.ACTIVELIST.getParentDirectory() != False:
			self.ACTIVELIST.changeDir(self.ACTIVELIST.getParentDirectory())

	def selectionChangedLeft(self):
		self.updateHeadLeft_Timer.stop()
		self.updateHeadLeft_Timer.start(500)

	def selectionChangedRight(self):
		self.updateHeadRight_Timer.stop()
		self.updateHeadRight_Timer.start(500)

	def updateHeadLeft(self):
		self.updateHeadLeft_Timer.stop()
		self.updateHeadLeftRight("list_left")

	def updateHeadRight(self):
		self.updateHeadRight_Timer.stop()
		self.updateHeadLeftRight("list_right")

	def updateHeadLeftRight(self, side):
		print("[FileCommander] DEBUG updateHead %s" % side)
		pathname = self[side].getPath()
		calculate_directorysize = not self.multiselect and self.calculate_directorysize and pathname and isdir(pathname)
		self["%s_head1" % side].text = pathname
		self["%s_head2" % side].updateList(self.statInfo(self[side], calculate_directorysize) if pathname else ())
		self.updateButtons()

	def updateButtons(self):  # this will be overwritten in child class
		pass

	def goUp(self):
		self.ACTIVELIST.up()

	def goDown(self):
		self.ACTIVELIST.down()

	def goLeft(self):
		self.ACTIVELIST.pageUp()

	def goRight(self):
		self.ACTIVELIST.pageDown()

	def goLeftB(self):
		if config.plugins.filecommander.change_navbutton.value == "yes":
			self.listLeft()
		else:
			self.goLeft()

	def goRightB(self):
		if config.plugins.filecommander.change_navbutton.value == "yes":
			self.listRight()
		else:
			self.goRight()

	def listRightB(self):
		if config.plugins.filecommander.change_navbutton.value == "yes":
			self.goLeft()
		elif config.plugins.filecommander.change_navbutton.value == "always" and self.ACTIVELIST == self["list_right"]:
			self.listLeft()
		else:
			self.listRight()

	def listLeftB(self):
		if config.plugins.filecommander.change_navbutton.value == "yes":
			self.goRight()
		elif config.plugins.filecommander.change_navbutton.value == "always" and self.ACTIVELIST == self["list_left"]:
			self.listRight()
		else:
			self.listLeft()

	def listLeft(self):
		self["list_left"].selectionEnabled(1)
		self["list_right"].selectionEnabled(0)
		self.ACTIVELIST = self["list_left"]
		if self.multiselect:
			return
		self.SOURCELIST = self["list_left"]
		self.TARGETLIST = self["list_right"]

	def listRight(self):
		self["list_left"].selectionEnabled(0)
		self["list_right"].selectionEnabled(1)
		self.ACTIVELIST = self["list_right"]
		if self.multiselect:
			return
		self.SOURCELIST = self["list_right"]
		self.TARGETLIST = self["list_left"]

	def get_dirSize(self, folder: str) -> int:
		return sum(p.stat().st_size for p in (f for f in Path(folder).rglob("*") if f.is_file()))

	def openTasklist(self):
		self.tasklist = []
		for job in job_manager.getPendingJobs():
			# self.tasklist.append((job, job.name, job.getStatustext(), int(100 * job.progress / float(job.end)), str(100 * job.progress / float(job.end)) + "%"))
			progress = job.getProgress()
			self.tasklist.append((job, job.name, job.getStatustext(), progress, str(progress) + " %"))
		self.session.open(TaskListScreen, self.tasklist)

	def statInfo(self, dirsource, dirsize=False):
		pathname = dirsource.getPath()
		if pathname and dirsource.getSelectionIndex():
			pathname = normpath(pathname)
			try:
				st = lstat(pathname)
			except OSError:
				return ()
		else:
			return ()

		# Numbers in trailing comments are the template text indexes
		symbolicmode = stat.filemode(st.st_mode)
		octalmode = "%04o" % stat.S_IMODE(st.st_mode)
		modes = (
			octalmode,  # 0
			symbolicmode,  # 1
			_("%s (%s)") % (octalmode, symbolicmode)  # 2
		)

		if stat.S_ISCHR(st.st_mode) or stat.S_ISBLK(st.st_mode):
			sizes = ("", "", "")
		else:
			sz = st.st_size
			if dirsize and isdir(pathname):
				sz = self.get_dirSize(folder=pathname)
			bytesize = "%s" % "{:n}".format(sz)
			scaledsize = " ".join(self.SIZESCALER.scale(sz)) + "B"
			sizes = (
				bytesize,  # 10
				_("%s") % scaledsize,  # 11
				_("%s (%s") % (bytesize, scaledsize)  # 12
			)

		return [modes + (
			"%d" % st.st_ino,  # 3
			"%d, %d" % ((st.st_dev >> 8) & 0xff, st.st_dev & 0xff),   # 4
			"%d" % st.st_nlink,  # 5
			"%d" % st.st_uid,  # 6
			"%s" % self.username(st.st_uid),  # 7
			"%d" % st.st_gid,  # 8
			"%s" % self.groupname(st.st_gid)  # 9
		) + sizes + (
			self.formatTime(st.st_mtime),  # 13
			self.formatTime(st.st_atime),  # 14
			self.formatTime(st.st_ctime)  # 15
		)]


class FileCommander(FileCommanderBase):
	def __init__(self, session, pathLeft=None):
		FileCommanderBase.__init__(self, session)
		# pathLeft == "" means device list, whereas pathLeft == None means saved or default value
		if pathLeft is None:
			if config.plugins.filecommander.savedir_left.value and config.plugins.filecommander.pathLeft.value and isdir(config.plugins.filecommander.pathLeft.value):
				pathLeft = config.plugins.filecommander.pathLeft.value
			elif config.plugins.filecommander.pathDefault.value and isdir(config.plugins.filecommander.pathDefault.value):
				pathLeft = config.plugins.filecommander.pathDefault.value
		if config.plugins.filecommander.savedir_right.value and config.plugins.filecommander.pathRight.value and isdir(config.plugins.filecommander.pathRight.value):
			pathRight = config.plugins.filecommander.pathRight.value
		elif config.plugins.filecommander.pathDefault.value and isdir(config.plugins.filecommander.pathDefault.value):
			pathRight = config.plugins.filecommander.pathDefault.value
		else:
			pathRight = None
		if pathLeft and isdir(pathLeft) and pathLeft[-1] != "/":
			pathLeft += "/"
		if pathRight and isdir(pathRight) and pathRight[-1] != "/":
			pathRight += "/"
		if pathLeft == "":
			pathLeft = None
		if pathRight == "":
			pathRight = None
		filefilter = self.fileFilter()  # Set filter.
		self.jobs = 0
		self.jobs_old = 0
		self.updateDirs = set()
		self.containers = []
		self["list_left_head1"] = Label(pathLeft)  # Set current folder.
		self["list_left_head2"] = List()
		self["list_right_head1"] = Label(pathRight)
		self["list_right_head2"] = List()
		sortDirs = config.plugins.filecommander.sortDirs.value  # Set sorting.
		sortFilesLeft = config.plugins.filecommander.sortFiles_left.value
		sortFilesRight = config.plugins.filecommander.sortFiles_right.value
		firstDirs = config.plugins.filecommander.firstDirs.value
		self["list_left"] = FileList(pathLeft, matchingPattern=filefilter, sortDirs=sortDirs, sortFiles=sortFilesLeft, firstDirs=firstDirs)
		self["list_right"] = FileList(pathRight, matchingPattern=filefilter, sortDirs=sortDirs, sortFiles=sortFilesRight, firstDirs=firstDirs)
		sortLeft = formatSortingTyp(sortDirs, sortFilesLeft)
		sortRight = formatSortingTyp(sortDirs, sortFilesRight)
		self["sort_left"] = Label(sortLeft)
		self["sort_right"] = Label(sortRight)
		self["key_blue"].setText(_("Rename"))
		self["VKeyIcon"] = Boolean(False)
		self["actions"] = HelpableActionMap(self, ["DirectionActions", "OkCancelActions", "InfoActions", "MenuActions", "NumberActions", "ColorActions", "InfobarActions", "InfobarTeletextActions", "InfobarSubtitleSelectionActions"], {
			"ok": (self.ok, _("Play/view/edit/install/extract/run file or enter directory")),
			"cancel": (self.exit, _("Leave File Commander")),
			"menu": (self.goContext, _("Open settings/actions menu")),
			"moveDown": (self.listRight, _("Activate right-hand file list as source")),
			"moveUp": (self.listLeft, _("Activate left-hand file list as source")),
			"chplus": (self.listRightB, _("Activate right-hand file list as source")),
			"chminus": (self.listLeftB, _("Activate left-hand file list as source")),
			"1": (self.gomakeDir, _("Create directory/folder")),
			"2": (self.gomakeSym, _("Create user-named symbolic link")),
			"3": (self.gofileStatInfo, _("File/Directory Status Information")),
			"4": (self.call_change_mode, _("Change execute permissions (755/644)")),
			"5": (self.goDefaultfolder, _("Go to bookmarked folder")),
			"6": (self.run_file, self.help_run_file),
			"7": (self.run_ffprobe, self.help_run_ffprobe),
			"8": (self.run_dirsize, self.help_run_dirsize),
			# "8": (self.run_mediainfo, self.help_run_mediainfo),
			"9": (self.run_hashes, _("Calculate file checksums")),
			"startTeletext": (self.file_viewer, _("View or edit file (if size < 1MB)")),
			"0": (self.doRefresh, _("Refresh screen")),
			"showMovies": (self.listSelect, _("Enter multi-file selection mode")),
			"subtitleSelection": self.downloadSubtitles,  # Unimplemented
			"redlong": (self.goRedLong, _("Sorting left files by name, date or size")),
			"greenlong": (self.goGreenLong, _("Reverse left file sorting")),
			"yellowlong": (self.goYellowLong, _("Reverse right file sorting")),
			"bluelong": (self.goBlueLong, _("Sorting right files by name, date or size")),
		}, prio=-1, description=_("File Commander Actions"))
		self["ColorActions"] = HelpableActionMap(self, ["ColorActions"], {
			"red": (self.goRed, _("Delete file or directory (and all its contents)")),
			"green": (self.goGreen, _("Move file/directory to target directory")),
			"yellow": (self.goYellow, _("Copy file/directory to target directory")),
			"blue": (self.goBlue, _("Rename file/directory")),
		}, prio=-1, description=_("File Commander Actions"))
		self.running = True
		self.checkJobs_Timer = eTimer()
		self.checkJobs_Timer.callback.append(self.checkJobs_TimerCB)
		# self.onLayoutFinish.append(self.onLayout)
		config.plugins.filecommander.calculate_directorysize.addNotifier(self.calculate_directorysizeChanged)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		FileCommanderBase.layoutFinished(self)
		self["list_left"].instance.enableAutoNavigation(False)
		self["list_right"].instance.enableAutoNavigation(False)
		if config.plugins.filecommander.pathLeft_selected:
			self.listLeft()
		else:
			self.listRight()
		self.checkJobs_TimerCB()

	@staticmethod
	def filterSettings():
		return(config.plugins.filecommander.extension.value, config.plugins.filecommander.my_extension.value)

	def run_hashes(self):
		if not config.plugins.filecommander.hashes.value:
			self.session.open(MessageBox, _("No hash calculations configured"), type=MessageBox.TYPE_ERROR, close_on_any_key=True)
			return
		progs = tuple((h, CHECKSUM_HASHES[h]) for h in config.plugins.filecommander.hashes.value if h in CHECKSUM_HASHES and self.have_program(CHECKSUM_HASHES[h]))
		if not progs:
			self.session.open(MessageBox, _("None of the hash programs for the hashes %s are available") % "".join(config.plugins.filecommander.hashes.value), type=MessageBox.TYPE_ERROR, close_on_any_key=True)
			return
		filename = self.SOURCELIST.getPath()
		if filename is None:
			self.session.open(MessageBox, _("It is not possible to calculate hashes on <List of Storage Devices>"), type=MessageBox.TYPE_ERROR)
			return
		filename = normpath(filename)
		if isdir(filename):
			self.session.open(MessageBox, _("The hash of a directory can't be calculated."), type=MessageBox.TYPE_ERROR, close_on_any_key=True)
			return
		toRun = []
		for prog in progs:
			toRun += [("echo", "-n", prog[0] + ": "), (prog[1], filename)]
		self.session.open(Console, cmdlist=toRun)

	def progConsoleCB(self):
		if hasattr(self, "_progConsole") and "text" in self._progConsole:
			self._progConsole["text"].setPos(0)
			self._progConsole["text"].updateScrollbar()

	def doOpkgCB(self, ans):
		if ans and hasattr(self, "_opkgArgs"):
			self.session.open(Console, cmdlist=((("opkg",) + self._opkgArgs),))
			del self._opkgArgs

	def run_prog(self, prog, args=None):
		if not self.have_program(prog):
			pkg = self.PROG_PACKAGES.get(prog)
			if pkg:
				self._opkgArgs = ("install", pkg)
				self.session.openWithCallback(self.doOpkgCB, MessageBox, _("Program '%s' needs to be installed to run this action.\nInstall the '%s' package to install the program?") % (prog, pkg), type=MessageBox.TYPE_YESNO, default=True)
			else:
				self.session.open(MessageBox, _("Program '%s' not installed.\nThe package containing this program isn't known.") % prog, type=MessageBox.TYPE_ERROR, close_on_any_key=True)
			return
		filename = self.SOURCELIST.getPath()
		if filename is None:
			self.session.open(MessageBox, _("It is not possible to run '%s' on <List of Storage Devices>") % prog, type=MessageBox.TYPE_ERROR)
			return
		filename = normpath(filename)
		if isdir(filename):
			if prog != "file":
				self.session.open(MessageBox, _("You can't usefully run '%s' on a directory.") % prog, type=MessageBox.TYPE_ERROR, close_on_any_key=True)
				return
			filename = basename(filename) or "/"
			filetype = "directory"
		else:
			__, filetype = splitext(filename.lower())
		if prog == "file" or filetype == ".ts" or filetype in RECORDING_EXTENSIONS:
			if args is None:
				args = ()
			elif not isinstance(args, (tuple, list)):
				args = (args,)
			toRun = (prog,) + tuple(args) + (filename,)
			self._progConsole = self.session.open(Console, cmdlist=(toRun,), finishedCallback=self.progConsoleCB)
		else:
			self.session.open(MessageBox, _("You can't usefully run '%s' on '%s'.") % (prog, basename(filename)), type=MessageBox.TYPE_ERROR, close_on_any_key=True)

	@staticmethod
	def have_program(prog):
		path = environ.get("PATH")
		if "/" in prog or not path:
			return access(prog, X_OK)
		for directory in path.split(":"):
			if access(pathjoin(directory, prog), X_OK):
				return True
		return False

	def help_run_prog(self, prog):
		if self.have_program(prog):
			return _("Run '%s' command") % prog
		else:
			if prog in self.PROG_PACKAGES:
				return _("Install '%s' and enable this operation") % prog
			else:
				return _("'%s' not installed and no known package") % prog

	def help_run_dirsize(self):
		return _("Show Directory size")

	def run_dirsize(self):
		directory = self.SOURCELIST.getPath()
		if directory:
			directory = normpath(directory)
			if isdir(directory):
				cmd = "du -h -d 0 \"%s\"" % directory
				self._progConsole = self.session.open(Console, cmdlist=(cmd,), finishedCallback=self.progConsoleCB)

	def help_run_mediainfo(self):
		return self.help_run_prog("mediainfo")

	def run_mediainfo(self):
		self.run_prog("mediainfo")

	def help_run_ffprobe(self):
		return self.help_run_prog("ffprobe")

	def run_ffprobe(self):
		self.run_prog("ffprobe", "-hide_banner")

	def run_file(self):
		self.run_prog("file")

	def help_run_file(self):
		return self.help_run_prog("file")

	def onLayout(self):
		if self.jobs_old:
			self.checkJobs_Timer.startLongTimer(5)
		filtered = "" if config.plugins.filecommander.extension.value == "^.*" else "(*)"
		if self.jobs or self.jobs_old:
			jobs = self.jobs + self.jobs_old
			jobs = ngettext("(%d job)", "(%d jobs)", jobs) % jobs
		else:
			jobs = ""
		self.setTitle("%s %s %s" % (PNAME, filtered, jobs))

	def checkJobs_TimerCB(self):
		self.jobs_old = 0
		for job in job_manager.getPendingJobs():
			if (job.name.startswith(_("Copy file")) or job.name.startswith(_("Copy folder")) or job.name.startswith(_("move file")) or job.name.startswith(_("move folder")) or job.name.startswith(_("Run script"))):
				self.jobs_old += 1
		self.jobs_old -= self.jobs
		self.onLayout()

	def viewable_file(self):
		filename = self.SOURCELIST.getPath()
		if filename:
			try:
				xfile = osstat(filename)
				if (xfile.st_size < 1000000):
					return filename
			except OSError:
				pass
		return None

	def file_viewer(self):
		longname = self.viewable_file()
		if longname:
			self.session.open(FileCommanderEditor, longname)
			self.onFileActionCB(True)

	def onFileActionCB(self, result=None):
		self.SOURCELIST.refresh()
		self.TARGETLIST.refresh()

	def exit(self):
		if self["list_left"].getCurrentDirectory() and config.plugins.filecommander.savedir_left.value:
			config.plugins.filecommander.pathLeft.value = self["list_left"].getCurrentDirectory()
			config.plugins.filecommander.pathLeft.save()
		else:
			config.plugins.filecommander.pathLeft.value = config.plugins.filecommander.pathDefault.value
		if self["list_right"].getCurrentDirectory() and config.plugins.filecommander.savedir_right.value:
			config.plugins.filecommander.pathRight.value = self["list_right"].getCurrentDirectory()
			config.plugins.filecommander.pathRight.save()
		else:
			config.plugins.filecommander.pathRight.value = config.plugins.filecommander.pathDefault.value
		self.running = False
		self.close(self.session, True)

	def ok(self):
		if self.SOURCELIST.canDescent():  # isDir
			self.SOURCELIST.descent()
		else:
			self.onFileAction(self.SOURCELIST, self.TARGETLIST)

	def onFileAction(self, dirsource, dirtarget):
		try:
			fileType = fromfile(dirsource.getPath())
			print("[FileCommander] DEBUG: File extension identified as '%s'." % fileType)
			fileType = magicfile(dirsource.getPath())
			print("[FileCommander] DEBUG: File type identified as '%s'." % fileType)
		except PureError as err:
			print("[FileCommander] Error: Unable to identify file content!  (%s)" % err)
		longname = dirsource.getPath()
		filename = basename(longname)
		sourceDir = dirsource.getCurrentDirectory()
		lowerfilename = filename.lower()
		filetype = splitext(filename)[1].lower()
		if search("\.r\d+$", filetype):
			filetype = ".rar"
		print("[FileCommander] onFileAction DEBUG: %s %s %s" % (filename, sourceDir, lowerfilename))
		if not isfile(longname):
			self.session.open(MessageBox, _("File not found: %s") % longname, type=MessageBox.TYPE_ERROR)
			return
		if filetype in ARCHIVE_FILES:
			self.session.openWithCallback(self.onFileActionCB, FileCommanderArchive, longname, dirtarget.getCurrentDirectory())
		elif filetype == ".ts":
			fileRef = eServiceReference(eServiceReference.idDVB, eServiceReference.noFlags, longname)
			self.session.open(FileCommanderMoviePlayer, fileRef)
		elif filetype in MOVIE_EXTENSIONS:
			fileRef = eServiceReference(eServiceReference.idServiceMP3, eServiceReference.noFlags, longname)
			self.session.open(FileCommanderMoviePlayer, fileRef)
		elif filetype in DVD_EXTENSIONS:
			self.session.open(DVDPlayer, dvd_filelist=[longname])
		elif filetype in AUDIO_EXTENSIONS:
			self.play_music(self.SOURCELIST)
		elif filetype in IMAGE_EXTENSIONS:
			if self.SOURCELIST.getCurrentIndex() != 0:
				self.session.openWithCallback(
					self.cbShowPicture,
					FileCommanderImageViewer,
					self.SOURCELIST.getFileList(),
					self.SOURCELIST.getCurrentIndex(),
					self.SOURCELIST.getCurrentDirectory(),  # DEBUG: path is not needed!
					filename
				)
		elif filetype in (".sh", ".py", ".pyc"):
			self.run_script(longname, self.TARGETLIST.getPath())
		elif filetype == ".mvi":
			self.file_name = longname
			self.tmp_file = "/tmp/grab_%s_mvi.png" % filename[:-4]
			choice = [(_("No"), "no"),
					(_("Show as Picture (press any key to close)"), "show")]
			savetext = ""
			stat = statvfs("/tmp/")
			if stat.f_bavail * stat.f_bsize > 1000000:
				choice.append((_("Show as Picture and save as file ('%s')") % self.tmp_file, "save"))
				savetext = _(" or save additional the picture to a file")
			self.session.openWithCallback(self.mviFileCB, MessageBox, _("Show '%s' as picture%s?\nThe current service must interrupted!") % (longname, savetext), simple=True, list=choice)
		elif filetype in TEXT_EXTENSIONS or config.plugins.filecommander.unknown_extension_as_text.value:
			try:
				xfile = osstat(longname)
			except OSError as oe:
				self.session.open(MessageBox, _("%s: %s") % (longname, oe.strerror), type=MessageBox.TYPE_ERROR)
				return
			if longname:
				if xfile.st_size < 1000000:
					self.session.open(FileCommanderEditor, longname)
					self.onFileActionCB(True)
				else:
					self.session.open(FileCommanderViewer, longname, 2)
		elif filetype == ".hex":
			try:
				xfile = osstat(longname)
			except OSError as oe:
				self.session.open(MessageBox, _("%s: %s") % (longname, oe.strerror), type=MessageBox.TYPE_ERROR)
				return
			if longname:
				self.session.open(FileCommanderViewer, longname)
				self.onFileActionCB(True)
		else:
			try:
				found_viewer = openFile(self.session, guess_type(longname)[0], longname)
			except TypeError:
				found_viewer = False
			if not found_viewer:
				self.session.open(MessageBox, _("No viewer installed for this file type: %s") % filename, type=MessageBox.TYPE_ERROR, timeout=5, close_on_any_key=True)

	def run_script(self, source, target):
		self.commando = source
		filename = basename(self.commando)
		self.parameter = target or ""
		stxt = _("shell") if self.commando.endswith(".sh") else _("python")
		askList = [(_("Cancel"), "NO"), (_("View or edit this %s script") % stxt, "VIEW"), (_("Run script"), "YES"), (_("Run script in background"), "YES_BG")]
		if self.parameter:
			askList.append((_("Run script with optional parameter"), "PAR"))
			askList.append((_("Run script with optional parameter in background"), "PAR_BG"))
			filename += _("\noptional parameter:\n%s") % self.parameter
		self.session.openWithCallback(self.do_run_script, ChoiceBox, title=_("Do you want to view or run the script?\n") + filename, list=askList)

	def do_run_script(self, answer):
		answer = answer and answer[1]
		if answer in ("YES", "PAR", "YES_BG", "PAR_BG"):
			if not access(self.commando, R_OK):
				self.session.open(MessageBox, _("Script '%s' must have read permission to be able to run it") % self.commando, type=MessageBox.TYPE_ERROR, close_on_any_key=True)
				return
			nice = config.plugins.filecommander.script_priority_nice.value or ""
			ionice = config.plugins.filecommander.script_priority_ionice.value or ""
			if nice:
				nice = "nice -n %d " % nice
			if ionice:
				ionice = "ionice -c %d " % ionice
			priority = "%s%s" % (nice, ionice)
			if self.commando.endswith(".sh"):
				if access(self.commando, X_OK):
					cmdline = "%s%s" % (priority, self.commando)
				else:
					cmdline = "%s/bin/sh %s" % (priority, self.commando)
			else:
				cmdline = "%s/usr/bin/python %s" % (priority, self.commando)
			if "PAR" in answer:
				cmdline = "%s '%s'" % (cmdline, self.parameter)
		elif answer == "VIEW":
			try:
				yfile = osstat(self.commando)
			except OSError as oe:
				self.session.open(MessageBox, _("%s: %s") % (self.commando, oe.strerror), type=MessageBox.TYPE_ERROR)
				return
			if self.commando:
				if yfile.st_size < 1000000:
					self.session.open(FileCommanderEditor, self.commando)
				else:
					self.session.open(FileCommanderViewer, self.commando, 2)

		if answer and answer not in ("NO", "VIEW"):
			if answer.endswith("_BG"):
				global task_Stout, task_Sterr
				task_Stout = []
				task_Sterr = []
				if "PAR" in answer:
					name = "%s%s %s" % (priority, self.commando, self.parameter)
				else:
					name = "%s%s" % (priority, self.commando)
				job = Job(_("Run script") + " ('%s')" % name)
				task = Task(job, name)
				task.postconditions.append(task_postconditions())
				task.processStdout = task_processStdout
				task.processStderr = task_processSterr
				task.setCmdline(cmdline)
				job_manager.AddJob(job, onSuccess=self.finishedCB, onFail=self.failCB)
				self.jobs += 1
				self.onLayout()
			else:
				self.session.open(Console, cmdlist=(cmdline,))

	def play_music(self, dirsource):
		self.sourceDir = dirsource
		askList = [(_("Play title"), "SINGLE"), (_("Play folder"), "LIST"), (_("Cancel"), "NO")]
		self.session.openWithCallback(self.do_play_music, ChoiceBox, title=_("What do you want to play?\n") + basename(self.sourceDir.getPath()), list=askList)

	def do_play_music(self, answer):
		longname = self.sourceDir.getPath()
		answer = answer and answer[1]
		if answer == "SINGLE":
			fileRef = eServiceReference(eServiceReference.idServiceMP3, eServiceReference.noFlags, longname)
			self.session.open(FileCommanderMoviePlayer, fileRef)
		elif answer == "LIST":
			self.music_playlist()

	def music_playlist(self):
		fileList = []
		from Plugins.Extensions.MediaPlayer.plugin import MediaPlayer
		self.beforeService = self.session.nav.getCurrentlyPlayingServiceReference()
		path = self.sourceDir.getCurrentDirectory()
		mp = self.session.open(MediaPlayer)
		mp.callback = self.cbmusic_playlist
		mp.playlist.clear()
		mp.savePlaylistOnExit = False
		i = 0
		start_song = -1
		filename = self.sourceDir.getPath()
		fileList = self.sourceDir.getFileList()
		for x in fileList:
			l = len(x)
			if x[0][0] is not None:
				testFileName = x[0][0].lower()
				_, filetype = splitext(testFileName)
			else:
				testFileName = x[0][0]  # "empty"
				filetype = None
			if l == 3 or l == 2:
				if not x[0][1]:
					if filetype in AUDIO_EXTENSIONS:
						if filename == x[0][0]:
							start_song = i
						i += 1
						mp.playlist.addFile(eServiceReference(4097, 0, path + x[0][0]))
			elif l >= 5:
				testFileName = x[4].lower()
				_, filetype = splitext(testFileName)
				if filetype in AUDIO_EXTENSIONS:
					if filename == x[0][0]:
						start_song = i
					i += 1
					mp.playlist.addFile(eServiceReference(4097, 0, path + x[4]))
		if start_song < 0:
			start_song = 0
		mp.changeEntry(start_song)
		mp.switchToPlayList()

	def cbmusic_playlist(self, data=None):
		if self.beforeService is not None:
			self.session.nav.playService(self.beforeService)
			self.beforeService = None

	def mviFileCB(self, ret=None):
		if ret and ret == "show":
			self.last_service = self.session.nav.getCurrentlyPlayingServiceReference()
			cmd = "/usr/bin/showiframe '%s'" % self.file_name
			self.session.nav.stopService()
			self.hide()
			eActionMap.getInstance().bindAction("", -maxsize - 1, self.showCB)
			console().ePopen(cmd)
		elif ret == "save":
			if isfile(self.tmp_file):
				remove(self.tmp_file)
			cmd = ["/usr/bin/ffmpeg -hide_banner -f mpegvideo -i %s -frames:v 1 -r 1/1 %s" % (self.file_name, self.tmp_file)]
			console().eBatch(cmd, self.saveCB)

	def showCB(self, key=None, flag=1):
		self.show()
		self.session.nav.playService(self.last_service)
		eActionMap.getInstance().unbindAction("", self.showCB)

	def saveCB(self, extra_args):
		if isfile(self.tmp_file):
			filename = self.tmp_file.split("/")[-1]
			self.session.open(FileCommanderImageViewer, [((filename, ""), "")], 0, self.tmp_file.replace(filename, ""), filename)  # DEBUG: path is not needed!
		else:
			self.session.open(MessageBox, _("File not found: %s") % self.tmp_file, type=MessageBox.TYPE_ERROR)

	def cbShowPicture(self, idx=0):
		if idx > 0:
			self.SOURCELIST.moveToIndex(idx)

	def goContext(self):
		dummy_to_translate_in_skin = _("File Commander menu")
		buttons = ("menu", "info") + tuple(digits) + ("red", "green", "yellow", "blue")
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
		dirName = self.SOURCELIST.getPath()
		if dirName and isdir(dirName):
			dirName = pathjoin(dirName, "")
			menu += [("bullet", dirName in config.plugins.filecommander.bookmarks.value
								and _("Remove selected folder from bookmarks")
								or _("Add selected folder to bookmarks"), "bookmark+selected")]
		dirName = self.SOURCELIST.getCurrentDirectory()
		if dirName:
			dirName = pathjoin(dirName, "")
			menu += [("bullet", dirName in config.plugins.filecommander.bookmarks.value
								and _("Remove current folder from bookmarks")
								or _("Add current folder to bookmarks"), "bookmark+current")]
		self.session.openWithCallback(self.goContextCB, FileCommanderContextMenu, contexts, menu)

	def goContextCB(self, action):
		if action:
			if action == "menu":
				self.goMenu()
			elif action.startswith("bookmark"):
				self.goBookmark(action.endswith("current"))
			else:
				actions = self["actions"].actions
				if action in actions:
					actions[action]()

	def goMenu(self):
		self.oldFilterSettings = self.filterSettings()
		self.session.openWithCallback(self.goRestart, FileCommanderSetup)

	def goBookmark(self, current):
		dirName = current and self.SOURCELIST.getCurrentDirectory() or self.SOURCELIST.getPath()
		bookmarks = config.plugins.filecommander.bookmarks.value
		if dirName in bookmarks:
			bookmarks.remove(dirName)
		else:
			bookmarks.insert(0, dirName)
			order = config.misc.pluginlist.fc_bookmarks_order.value
			if dirName not in order:
				order = "%s,%s" % (dirName, order)
				config.misc.pluginlist.fc_bookmarks_order.value = order
				config.misc.pluginlist.fc_bookmarks_order.save()
		config.plugins.filecommander.bookmarks.value = bookmarks
		config.plugins.filecommander.bookmarks.save()

	def goDefaultfolder(self):
		bookmarks = config.plugins.filecommander.bookmarks.value
		if not bookmarks:
			if config.plugins.filecommander.pathDefault.value:
				bookmarks.append(config.plugins.filecommander.pathDefault.value)
			bookmarks.append("/home/root/")
			bookmarks.append(defaultMoviePath())
			config.plugins.filecommander.bookmarks.value = bookmarks
			config.plugins.filecommander.bookmarks.save()
		bookmarks = [(x, x) for x in bookmarks]
		bookmarks.append((_("Storage Devices"), None))
		self.session.openWithCallback(self.locationCB, ChoiceBox, title=_("Select a path"), list=bookmarks, reorderConfig="fc_bookmarks_order")

	def locationCB(self, answer):
		if answer:
			self.SOURCELIST.changeDir(answer[1])

	def goRestart(self, *answer):
		if hasattr(self, "oldFilterSettings"):
			if self.oldFilterSettings != self.filterSettings():
				filefilter = compile(self.fileFilter())
				self["list_left"].matchingPattern = filefilter
				self["list_right"].matchingPattern = filefilter
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

	def listSelect(self):  # Multiselect.
		if not self.SOURCELIST.getCurrentDirectory():
			return
		selectedid = self.SOURCELIST.getSelectionID()
		config.plugins.filecommander.pathLeft_tmp.value = self["list_left"].getCurrentDirectory() or ""
		config.plugins.filecommander.pathRight_tmp.value = self["list_right"].getCurrentDirectory() or ""
		config.plugins.filecommander.sortingLeft_tmp.value = self["list_left"].getSortBy()
		config.plugins.filecommander.sortingRight_tmp.value = self["list_right"].getSortBy()
		leftactive = self.SOURCELIST == self["list_left"]
		self.session.openWithCallback(self.doRefreshDir, FileCommanderFileSelect, leftactive, selectedid)

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
		message = "%s\n%s: %s" % (job.name, _("Error"), problems[0].getErrorMessage(task))
		messageboxtyp = MessageBox.TYPE_ERROR
		timeout = 0
		if InfoBar.instance and not inStandby:
			InfoBar.instance.openInfoBarMessage(message, messageboxtyp, timeout)
		else:
			Tools.Notifications.AddNotification(MessageBox, message, type=messageboxtyp, timeout=timeout)
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
		if not self.running and config.plugins.filecommander.showTaskCompleted_message.value:
			for job in job_manager.getPendingJobs():
				if (job.name.startswith(_("Copy file")) or job.name.startswith(_("Copy folder")) or job.name.startswith(_("move file")) or job.name.startswith(_("move folder")) or job.name.startswith(_("Run script"))):
					return
			from Screens.Standby import inStandby
			message = _("File Commander - all Task's are completed!")
			messageboxtyp = MessageBox.TYPE_INFO
			timeout = 30
			if InfoBar.instance and not inStandby:
				InfoBar.instance.openInfoBarMessage(message, messageboxtyp, timeout)
			else:
				Tools.Notifications.AddNotification(MessageBox, message, type=messageboxtyp, timeout=timeout)

	def setSort(self, liste, setDirs=False):
		sortDirs, sortFiles = liste.getSortBy().split(",")
		if setDirs:
			sort, reverse = [int(x) for x in sortDirs.split(".")]
			sort += 1
			if sort > 1:
				sort = 0
		else:
			sort, reverse = [int(x) for x in sortFiles.split(".")]
			sort += 1
			if sort > 2:
				sort = 0
		return "%d.%d" % (sort, reverse)

	def setReverse(self, liste, setDirs=False):
		sortDirs, sortFiles = liste.getSortBy().split(",")
		if setDirs:
			sort, reverse = [int(x) for x in sortDirs.split(".")]
		else:
			sort, reverse = [int(x) for x in sortFiles.split(".")]
		reverse += 1
		if reverse > 1:
			reverse = 0
		return "%d.%d" % (sort, reverse)

	def goRedLong(self):  # Sorting files left.
		self["list_left"].setSortBy(self.setSort(self["list_left"]))
		self.doRefresh()

	def goGreenLong(self):  # Reverse sorting files left.
		self["list_left"].setSortBy(self.setReverse(self["list_left"]))
		self.doRefresh()

	def goYellowLong(self):  # Reverse sorting files right.
		self["list_right"].setSortBy(self.setReverse(self["list_right"]))
		self.doRefresh()

	def goBlueLong(self):  # Sorting files right.
		self["list_right"].setSortBy(self.setSort(self["list_right"]))
		self.doRefresh()

	def getCurrentSelectionFileInfo(self):
		sourcePath = normpath(self.SOURCELIST.getPath())
		sourceDir = normpath(self.SOURCELIST.getCurrentDirectory())
		targetDir = self.TARGETLIST.getCurrentDirectory()
		if targetDir:
			targetDir = normpath(targetDir)
		sourceName = basename(sourcePath)
		isFile = isfile(sourcePath)
		return (sourcePath, sourceName, isFile, sourceDir, targetDir)

	def goYellow(self):  # Copy.
		if InfoBar.instance and InfoBar.instance.LongButtonPressed:
			return
		(sourcePath, sourceName, isFile, sourceDir, targetDir) = self.getCurrentSelectionFileInfo()
		warntxt = ""
		if exists(pathjoin(targetDir, sourceName)):
			warntxt = _(" - file exist! Overwrite") if isFile else _(" - folder exist! Overwrite")
		copytext = "%s%s" % (_("Copy file"), warntxt) if isFile else "%s%s" % (_("Copy folder"), warntxt)
		self.session.openWithCallback(self.doCopy, MessageBox, text="%s?\n%s\n%s\n%s\n%s\n%s" % (copytext, sourceName, _("from dir"), sourceDir, _("to dir"), targetDir))

	def doCopy(self, answer):
		if answer:
			(sourcePath, sourceName, isFile, sourceDir, targetDir) = self.getCurrentSelectionFileInfo()
			updateDirs = [targetDir]
			if isFile:
				self.addJob(FileTransferJob(sourcePath, targetDir, False, True, "%s : %s" % (_("Copy file"), sourceName)), updateDirs)
			else:
				self.addJob(FileTransferJob(sourcePath, targetDir, True, True, "%s : %s" % (_("Copy folder"), sourceName)), updateDirs)

	def goRed(self):  # Delete.
		if InfoBar.instance and InfoBar.instance.LongButtonPressed:
			return
		filename = normpath(self.SOURCELIST.getPath())
		sourceDir = normpath(self.SOURCELIST.getCurrentDirectory())
		deltext = _("Delete file") if isfile(filename) else _("Delete folder")
		filename = basename(normpath(filename))
		self.session.openWithCallback(self.doDelete, MessageBox, text="%s?\n%s\n%s\n%s" % (deltext, filename, _("from dir"), sourceDir))

	def doDelete(self, answer):
		if answer:
			filename = normpath(self.SOURCELIST.getPath())
			sourceDir = normpath(self.SOURCELIST.getCurrentDirectory())
			if isfile(filename):
				remove(filename)
				self.doRefresh()
			else:
				self.addJob([filename], [sourceDir])

	def goGreen(self):  # Move.
		if InfoBar.instance and InfoBar.instance.LongButtonPressed:
			return
		(sourcePath, sourceName, isFile, sourceDir, targetDir) = self.getCurrentSelectionFileInfo()
		warntxt = ""
		if exists(pathjoin(targetDir, sourceName)):
			warntxt = _(" - file exist! Overwrite") if isFile else _(" - folder exist! Overwrite")
		movetext = "%s%s" % (_("Move file"), warntxt) if isFile else "%s%s" % (_("Move folder"), warntxt)
		self.session.openWithCallback(self.doMove, MessageBox, text="%s?\n%s\n%s\n%s\n%s\n%s" % (movetext, sourceName, _("from dir"), sourceDir, _("to dir"), targetDir))

	def doMove(self, answer):
		if answer:
			(sourcePath, sourceName, isFile, sourceDir, targetDir) = self.getCurrentSelectionFileInfo()
			updateDirs = [sourceDir, targetDir]
			if isFile:
				self.addJob(FileTransferJob(sourcePath, targetDir, False, False, "%s : %s" % (_("move file"), sourceName)), updateDirs)
			else:
				self.addJob(FileTransferJob(sourcePath, targetDir, True, False, "%s : %s" % (_("move folder"), sourceName)), updateDirs)

	def goBlue(self):  # Rename.
		if InfoBar.instance and InfoBar.instance.LongButtonPressed:
			return
		filename = normpath(self.SOURCELIST.getPath())
		filename = basename(filename)
		if not filename:
			self.session.open(MessageBox, _("It's not possible to rename the file system root."), type=MessageBox.TYPE_ERROR)
			return
		fname = _("Please enter the new file name") if isfile(filename) else _("Please enter the new directory name")
		self.session.openWithCallback(self.doRename, VirtualKeyBoard, title=fname, text=filename)

	def doRename(self, newname):
		if newname:
			filename = normpath(self.SOURCELIST.getPath())
			sourceDir = normpath(self.SOURCELIST.getCurrentDirectory())
			try:
				if isfile(filename):
					rename(filename, pathjoin(sourceDir, newname))
				else:
					rename(filename, pathjoin(sourceDir, newname))
					movie, ext = splitext(filename)
					newmovie, newext = splitext(newname)
					if ext in ALL_MOVIE_EXTENSIONS and newext in ALL_MOVIE_EXTENSIONS:
						for ext in RECORDING_EXTENSIONS:
							try:
								if ext == ".eit":
									rename(pathjoin(sourceDir, movie) + ".eit", pathjoin(sourceDir, newmovie) + ".eit")
								else:
									rename(pathjoin(sourceDir, filename) + ext, pathjoin(sourceDir, newname) + ext)
							except OSError:
								pass
			except OSError as err:
				self.session.open(MessageBox, _("Error %d: Unable to rename '%s' to '%s':\n%s") % (err.errno, filename, newname, err.strerror), type=MessageBox.TYPE_ERROR)
			self.doRefresh()

	def gomakeSym(self):  # Symlink by name.
		filename = self.SOURCELIST.getPath()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		targetDir = self.TARGETLIST.getCurrentDirectory()
		if sourceDir and targetDir and filename and self.SOURCELIST.getSelectionID():
			filename = basename(normpath(filename))
			self.session.openWithCallback(self.doMakesym, VirtualKeyBoard, title=_("Please enter name of the new symlink"), text=filename)

	def doMakesym(self, newname):  # FIXME
		if newname:
			oldname = self.SOURCELIST.getPath()
			sourceDir = self.SOURCELIST.getCurrentDirectory()
			targetDir = self.TARGETLIST.getCurrentDirectory()
			if targetDir and oldname:
				if oldname.startswith("/"):
					oldpath = oldname
				elif sourceDir is not None:
					oldpath = pathjoin(sourceDir, oldname)
				else:
					return
				newpath = pathjoin(targetDir, newname)
				try:
					symlink(oldpath, newpath)
				except OSError as err:
					self.session.open(MessageBox, _("Error linking %s to %s:\n%s") % (oldpath, newpath, err.strerror), type=MessageBox.TYPE_ERROR)
				self.doRefresh()

	def gofileStatInfo(self):  # File/directory information.
		path = self.SOURCELIST.getPath()
		if path:
			self.session.open(FileCommanderInformation, path, self.SOURCELIST.getCurrentDirectory())

	def gomakeSymlink(self):  # Symlink by folder.
		filename = self.SOURCELIST.getPath()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		targetDir = self.TARGETLIST.getCurrentDirectory()
		if filename and sourceDir and targetDir:
			filename = normpath(filename)
			if islink(filename):
				return
			movetext = _("Symlink to ") if isdir(filename) else _("Create symlink to file")
			self.session.openWithCallback(self.domakeSymlink, MessageBox, text="%s %s in %s" % (movetext, filename, targetDir))

	def domakeSymlink(self, answer):
		if answer:
			filename = self.SOURCELIST.getPath()
			sourceDir = self.SOURCELIST.getCurrentDirectory()
			targetDir = self.TARGETLIST.getCurrentDirectory()
			if filename and sourceDir and targetDir:
				if sourceDir in filename:  # FIXME ????
					self.session.openWithCallback(self.doRefresh, Console, title=_("create symlink ..."), cmdlist=(("ln", "-s", filename, targetDir),))

	def gomakeDir(self):  # New folder.
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		if sourceDir:
			self.session.openWithCallback(self.doMakedir, VirtualKeyBoard, title=_("Please enter a name for the new directory:"), text=_("New folder"))

	def doMakedir(self, newname):
		if newname:
			sourceDir = self.SOURCELIST.getCurrentDirectory()
			if sourceDir:
				try:
					mkdir(pathjoin(sourceDir, newname))
				except OSError as err:
					self.session.open(MessageBox, _("Error creating directory %s:\n%s") % (pathjoin(sourceDir, newname), err.strerror), type=MessageBox.TYPE_ERROR)
				self.doRefresh()

	def downloadSubtitles(self):  # Download subtitles.
		testFileName = self.SOURCELIST.getPath()
		if testFileName:
			movie, extension = splitext(testFileName)
			if extension in ("mpg", "mpeg", "mkv", "m2ts", "vob", "mod", "avi", "mp4", "divx", "mkv", "wmv", "mov", "flv", "3gp"):
				print("[FileCommander] Downloading subtitle for '%s'." % testFileName)
				# For Future USE

	def subCallback(self, answer=False):
		self.doRefresh()

	def updateButtons(self):
		self["VKeyIcon"].boolean = self.viewable_file() is not None
		valid = self.SOURCELIST and self.SOURCELIST.count() and self.SOURCELIST.getPath() and self.SOURCELIST.getCurrentIndex()
		self["ColorActions"].setEnabled = valid
		self["key_green"].setText(_("Move") if valid else "")
		self["key_yellow"].setText(_("Copy") if valid else "")
		self["key_blue"].setText(_("Rename") if valid else "")
		self["key_red"].setText(_("Delete") if valid else "")

	def doRefreshDir(self, jobs, updateDirs):
		if jobs:
			for job in jobs:
				self.addJob(job, updateDirs)
		self["list_left"].changeDir(config.plugins.filecommander.pathLeft_tmp.value or None)
		self["list_right"].changeDir(config.plugins.filecommander.pathRight_tmp.value or None)
		if self.SOURCELIST == self["list_left"]:
			self["list_left"].selectionEnabled(1)
			self["list_right"].selectionEnabled(0)
		else:
			self["list_left"].selectionEnabled(0)
			self["list_right"].selectionEnabled(1)

	def doRefresh(self):
		sortDirsLeft, sortFilesLeft = self["list_left"].getSortBy().split(",")
		sortDirsRight, sortFilesRight = self["list_right"].getSortBy().split(",")
		sortLeft = formatSortingTyp(sortDirsLeft, sortFilesLeft)
		sortRight = formatSortingTyp(sortDirsRight, sortFilesRight)
		self["sort_left"].setText(sortLeft)
		self["sort_right"].setText(sortRight)
		self.SOURCELIST.refresh()
		self.TARGETLIST.refresh()

	def call_change_mode(self):
		self.change_mod(self.SOURCELIST)

	def change_mod(self, dirsource):
		filename = dirsource.getPath()
		sourceDir = dirsource.getCurrentDirectory()

		if filename is None or sourceDir is None:
			self.session.open(MessageBox, _("It is not possible to change the file mode of <List of Storage Devices>"), type=MessageBox.TYPE_ERROR)
			return

		self.longname = filename
		if not dirsource.canDescent():
			askList = [(_("Set archive mode (644)"), "CHMOD644"), (_("Set executable mode (755)"), "CHMOD755"), (_("Cancel"), "NO")]
			self.session.openWithCallback(self.do_change_mod, ChoiceBox, title=(_("Do you want change rights?\n") + filename), list=askList)
		else:
			self.session.open(MessageBox, _("Not allowed with folders"), type=MessageBox.TYPE_INFO, close_on_any_key=True)

	def do_change_mod(self, answer):
		answer = answer and answer[1]
		if answer == "CHMOD644":
			chmod(self.longname, 0o644)
		elif answer == "CHMOD755":
			chmod(self.longname, 0o755)
		self.doRefresh()


class FileCommanderFileSelect(FileCommanderBase):
	def __init__(self, session, leftactive, selectedid):
		FileCommanderBase.__init__(self, session)
		self.multiselect = True
		self.selectedFiles = []
		self.selectedid = selectedid
		pathLeft = config.plugins.filecommander.pathLeft_tmp.value or None
		pathRight = config.plugins.filecommander.pathRight_tmp.value or None
		sortDirsLeft, sortFilesLeft = config.plugins.filecommander.sortingLeft_tmp.value.split(",")  # Set sorting.
		sortDirsRight, sortFilesRight = config.plugins.filecommander.sortingRight_tmp.value.split(",")
		firstDirs = config.plugins.filecommander.firstDirs.value
		sortLeft = formatSortingTyp(sortDirsLeft, sortFilesLeft)
		sortRight = formatSortingTyp(sortDirsRight, sortFilesRight)
		self["sort_left"] = Label(sortLeft)
		self["sort_right"] = Label(sortRight)
		filefilter = self.fileFilter()  # Set filter.
		self["list_left_head1"] = Label(pathLeft)  # Set current folder.
		self["list_left_head2"] = List()
		self["list_right_head1"] = Label(pathRight)
		self["list_right_head2"] = List()
		if leftactive:
			self["list_left"] = FileListMultiSelect(self.selectedFiles, pathLeft, matchingPattern=filefilter, sortDirs=sortDirsLeft, sortFiles=sortFilesLeft, firstDirs=firstDirs)
			self["list_right"] = FileList(pathRight, matchingPattern=filefilter, sortDirs=sortDirsRight, sortFiles=sortFilesRight, firstDirs=firstDirs)
			self.SOURCELIST = self["list_left"]
			self.TARGETLIST = self["list_right"]
			self.onLayoutFinish.append(self.listLeft)
		else:
			self["list_left"] = FileList(pathLeft, matchingPattern=filefilter, sortDirs=sortDirsLeft, sortFiles=sortFilesLeft, firstDirs=firstDirs)
			self["list_right"] = FileListMultiSelect(self.selectedFiles, pathRight, matchingPattern=filefilter, sortDirs=sortDirsRight, sortFiles=sortFilesRight, firstDirs=firstDirs)
			self.SOURCELIST = self["list_right"]
			self.TARGETLIST = self["list_left"]
			self.onLayoutFinish.append(self.listRight)
		self["key_blue"].setText(_("Skip selection"))
		self["actions"] = HelpableActionMap(self, ["DirectionActions", "OkCancelActions", "NumberActions", "ColorActions"], {
			"ok": (self.ok, _("Select (source list) or enter directory (target list)")),
			"cancel": (self.exit, _("Leave multi-select mode")),
			"moveDown": (self.listRight, _("Activate right-hand file list as multi-select source")),
			"moveUp": (self.listLeft, _("Activate left-hand file list as multi-select source")),
			"chplus": (self.listRightB, _("Activate right-hand file list as multi-select source")),
			"chminus": (self.listLeftB, _("Activate left-hand file list as multi-select source")),
			"blue": (self.goBlue, _("Leave multi-select mode")),
			"0": (self.doRefresh, _("Refresh screen")),
		}, prio=-1, description=_("File Commander Selection Actions"))
		self["ColorActions"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.goGreen, _("Move file/directory to target directory")),
			"yellow": (self.goYellow, _("Copy file/directory to target directory")),
		}, prio=-1, description=_("File Commander Selection Actions"))
		self["DeleteAction"] = HelpableActionMap(self, ["ColorActions"], {
			"red": (self.goRed, _("Delete the selected files or directories")),
		}, prio=-1, description=_("File Commander Selection Actions"))
		self.onLayoutFinish.append(self.onLayout)

	def onLayout(self):
		filtered = "" if config.plugins.filecommander.extension.value == "^.*" else "(*)"
		self.setTitle("%s %s %s" % (PNAME, filtered, _("(Selectmode)")))
		self.SOURCELIST.moveToIndex(self.selectedid)

	def changeSelectionState(self):
		if self.ACTIVELIST == self.SOURCELIST:
			self.ACTIVELIST.changeSelectionState()
			self.selectedFiles = self.ACTIVELIST.getSelectedList()
			print("[FileCommander] selectedFiles %s." % self.selectedFiles)
			self.goDown()

	def exit(self, jobs=None, updateDirs=None):
		config.plugins.filecommander.pathLeft_tmp.value = self["list_left"].getCurrentDirectory() or ""
		config.plugins.filecommander.pathRight_tmp.value = self["list_right"].getCurrentDirectory() or ""
		self.close(jobs, updateDirs)

	def ok(self):
		if self.ACTIVELIST == self.SOURCELIST:
			self.changeSelectionState()
		else:
			if self.ACTIVELIST.canDescent():  # isDir
				self.ACTIVELIST.descent()

	def goRed(self):  # Delete selected.
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		cnt = 0
		filename = ""
		self.delete_dirs = []
		self.delete_files = []
		self.delete_updateDirs = [sourceDir]
		for file in self.selectedFiles:
			print("[FileCommander] Delete '%s'." % file)
			if not cnt:
				filename += "%s" % file
			elif cnt < 5:
				filename += ", %s" % file
			elif cnt < 6:
				filename += ", ..."
			cnt += 1
			if isdir(file):
				self.delete_dirs.append(file)
			else:
				self.delete_files.append(file)
		if cnt > 1:
			deltext = _("Delete %d elements") % len(self.selectedFiles)
		else:
			deltext = _("Delete 1 element")
		self.session.openWithCallback(self.doDelete, MessageBox, text="%s?\n%s\n%s\n%s" % (deltext, filename, _("from dir"), sourceDir))

	def doDelete(self, answer):
		if answer:
			for file in self.delete_files:
				print("[FileCommander] Delete '%s'." % file)
				remove(file)
			self.exit([self.delete_dirs], self.delete_updateDirs)

	def goGreen(self):  # Move selected.
		cnt = 0
		warncnt = 0
		warntxt = ""
		filename = ""
		self.cleanList()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		targetDir = self.TARGETLIST.getCurrentDirectory()
		self.move_updateDirs = [targetDir, sourceDir]
		self.move_jobs = []
		for file in self.selectedFiles:
			if not cnt:
				filename += "%s" % file
			elif cnt < 3:
				filename += ", %s" % file
			elif cnt < 4:
				filename += ", ..."
			cnt += 1
			if exists(pathjoin(targetDir, file.rstrip("/").split("/")[-1])):
				warncnt += 1
				if warncnt > 1:
					warntxt = _(" - %d elements exist! Overwrite") % warncnt
				else:
					warntxt = _(" - 1 element exist! Overwrite")
			dst_file = targetDir
			if dst_file.endswith("/") and dst_file != "/":
				targetDir = dst_file[:-1]
			self.move_jobs.append(FileTransferJob(file, targetDir, False, False, "%s : %s" % (_("move file"), file)))
		if cnt > 1:
			movetext = (_("Move %d elements") % len(self.selectedFiles)) + warntxt
		else:
			movetext = _("Move 1 element") + warntxt
		self.session.openWithCallback(self.doMove, MessageBox, text="%s?\n%s\n%s\n%s\n%s\n%s" % (movetext, filename, _("from dir"), sourceDir, _("to dir"), targetDir))

	def doMove(self, answer):
		if answer:
			self.exit(self.move_jobs, self.move_updateDirs)

	def goYellow(self):  # Copy selected.
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		targetDir = self.TARGETLIST.getCurrentDirectory()
		cnt = 0
		warncnt = 0
		warntxt = ""
		filename = ""
		self.cleanList()
		self.copy_updateDirs = [targetDir]
		self.copy_jobs = []
		for file in self.selectedFiles:
			if not cnt:
				filename += "%s" % file
			elif cnt < 3:
				filename += ", %s" % file
			elif cnt < 4:
				filename += ", ..."
			cnt += 1
			if exists(pathjoin(targetDir, file.rstrip("/").split("/")[-1])):
				warncnt += 1
				if warncnt > 1:
					warntxt = _(" - %d elements exist! Overwrite") % warncnt
				else:
					warntxt = _(" - 1 element exist! Overwrite")
			dst_file = targetDir
			if dst_file.endswith("/") and dst_file != "/":
				targetDir = dst_file[:-1]
			if file.endswith("/"):
				self.copy_jobs.append(FileTransferJob(file, targetDir, True, True, "%s : %s" % (_("Copy folder"), file)))
			else:
				self.copy_jobs.append(FileTransferJob(file, targetDir, False, True, "%s : %s" % (_("Copy file"), file)))
		if cnt > 1:
			copytext = (_("Copy %d elements") % len(self.selectedFiles)) + warntxt
		else:
			copytext = _("Copy 1 element") + warntxt
		self.session.openWithCallback(self.doCopy, MessageBox, text="%s?\n%s\n%s\n%s\n%s\n%s" % (copytext, filename, _("from dir"), sourceDir, _("to dir"), targetDir))

	def doCopy(self, answer):
		if answer:
			self.exit(self.copy_jobs, self.copy_updateDirs)

	def goBlue(self):
		self.exit()

	def updateButtons(self):
		targetDir = self.TARGETLIST.getCurrentDirectory()
		selected = len(self.selectedFiles)
		valid = targetDir and selected
		self["ColorActions"].setEnabled = valid
		self["key_green"].setText(_("Move") if valid else "")
		self["key_yellow"].setText(_("Copy") if valid else "")
		self["DeleteAction"].setEnabled = selected
		self["key_red"].setText(_("Delete") if selected else "")

	def doRefresh(self):
		print("[FileCommander] selectedFiles %s." % self.selectedFiles)
		self.SOURCELIST.refresh()
		self.TARGETLIST.refresh()

	def cleanList(self):  # Remove movie parts if the movie is present.
		for file in self.selectedFiles[:]:
			movie, extension = splitext(file)
			if extension in RECORDING_EXTENSIONS:
				if extension == ".eit":
					extension = ".ts"
					movie = "%s%s" % (movie, extension)
				else:
					extension = splitext(movie)[1]
				if extension in ALL_MOVIE_EXTENSIONS and movie in self.selectedFiles:
					self.selectedFiles.remove(file)


class FileCommanderContextMenu(Screen):
	skin = """
	<screen name="FileCommanderContextMenu" title="File Commander Context Menu" position="center,center" size="560,570" resolution="1280,720">
		<widget name="menu" position="fill" itemHeight="35" />
	</screen>"""

	def __init__(self, session, contexts, menuList):
		Screen.__init__(self, session, mandatoryWidgets=["Test"])
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

	def keyCancel(self):
		self.close(False)

	def keyOk(self):
		self.close(self["menu"].getCurrent()[0][1])


class FileCommanderSetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "FileCommander", plugin="Extensions/FileCommander")

	def keySelect(self):
		if self.getCurrentItem() == config.plugins.filecommander.pathDefault:
			currDir = config.plugins.filecommander.pathDefault.value if config.plugins.filecommander.pathDefault.value else None
			self.session.openWithCallback(self.keySelectCallback, LocationBox, text=_("Select default File Commander directory:"), currDir=currDir, minFree=100)
		else:
			Setup.keySelect(self)

	def keySelectCallback(self, path):
		if path:
			config.plugins.filecommander.pathDefault.value = path


class FileCommanderInformation(Screen, HelpableScreen, StatInfo):
	skin = ["""
	<screen name="FileCommanderInformation" title="File/Directory Status Information" position="center,center" size="800,410" resolution="1280,720">
		<widget name="path" position="0,0" size="800,50" font="Regular;20" valign="center" />
		<widget source="data" render="Listbox" position="0,60" size="800,300">
			<convert type="TemplatedMultiContent">
				{
				"template":
					[
					# 0   100 200 300 400 500
					# |   |   |   |   |   |
					# 00000000 1111111111111
					MultiContentEntryText(pos=(%d, 0), size=(%d, %d), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=0), # Index 0 is a label.
					MultiContentEntryText(pos=(%d, 0), size=(%d, %d), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=1)  # Index 1 is the information.
					],
				"fonts": [parseFont("Regular;%d")],
				"itemHeight": %d,
				"selectionEnabled": False
				}
			</convert>
		</widget>
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>""",
		15, 200, 25,  # label
		245, 555, 25,  # information
		20,  # fonts
		25  # itenHeight
	]

	def __init__(self, session, path, target):
		Screen.__init__(self, session, mandatoryWidgets=["path", "data", "Test"])
		HelpableScreen.__init__(self)
		StatInfo.__init__(self)
		self.skinname = ["FileCommanderInformation", "FileCommanderFileStatInfo"]
		if not self.getTitle():
			self.setTitle(_("File/Directory Status Information"))
		self.path = normpath(path) if path.endswith(sep) else path
		self.target = target
		self.data = []
		self["path"] = Label(self.path)
		self["data"] = List(self.data)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText("")
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"cancel": (self.close, _("Close this screen")),
			"ok": (self.close, _("Close this screen")),
			"red": (self.close, _("Close this screen"))
		}, prio=0, description=_("File/Directory Status Actions"))
		self["detailAction"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyDetails, _("Display more information about this file"))
		}, prio=0, description=_("File/Directory Status Actions"))
		self["navigationActions"] = HelpableActionMap(self, ["NavigationActions"], {
			"top": (self["data"].goTop, _("Move to first line / screen")),
			"pageUp": (self["data"].goPageUp, _("Move up a screen")),
			"up": (self["data"].goLineUp, _("Move up a line")),
			# "left": (self["data"].goPageUp, _("Move up a screen")),
			# "right": (self["data"].goPageDown, _("Move down a screen")),
			"down": (self["data"].goLineDown, _("Move down a line")),
			"pageDown": (self["data"].goPageDown, _("Move down a screen")),
			"bottom": (self["data"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("File/Directory Status Actions"))
		self.onShown.append(self.layoutFinished)

	def layoutFinished(self):
		self["data"].downstream_elements[0].downstream_elements[0].instance.enableAutoNavigation(False)
		self.height = self["data"].downstream_elements[0].downstream_elements[0].instance.size().height()
		self.itemHeight = self["data"].downstream_elements[0].template.get("itemHeight", 25)
		self.getStatus()

	def getStatus(self):
		extension = splitext(self.path)[1][1:].lower()
		if extension in MEDIA_FILES:
			self["key_green"].setText(_("MediaInfo"))
			self["detailAction"].setEnabled(True)
		elif extension in TEXT_FILES:
			self["key_green"].setText(_("Edit File"))
			self["detailAction"].setEnabled(True)
		elif extension in ARCHIVE_FILES:
			self["key_green"].setText(_("Unpack File"))
			self["detailAction"].setEnabled(True)
		else:
			self["key_green"].setText("")
			self["detailAction"].setEnabled(False)
		self.data = []
		try:
			lines = 10
			status = lstat(self.path)
			mode = status.st_mode
			self.data.append((_("Type:"), self.fileTypeStr(mode)))
			if stat.S_ISLNK(mode):
				try:
					link = readlink(self.path)
				except OSError as err:
					link = _("Error %d: %s") % (err.errno, err.strerror)
				lines += 1
				self.data.append((_("Link target:"), link))
			self.data.append((_("Owner:"), "%s (%d)" % (self.username(status.st_uid), status.st_uid)))
			self.data.append((_("Group:"), "%s (%d)" % (self.groupname(status.st_gid), status.st_gid)))
			permissions = stat.S_IMODE(mode)
			self.data.append((_("Permissions:"), _("%s (%04o)") % (stat.filemode(mode), permissions)))
			if not (stat.S_ISCHR(mode) or stat.S_ISBLK(mode)):
				lines += 1
				self.data.append(("%s:" % _("Size"), "%s (%sB)" % ("{:n}".format(status.st_size), " ".join(self.SIZESCALER.scale(status.st_size)))))
			self.data.append((_("Modified:"), self.formatTime(status.st_mtime)))
			self.data.append((_("Accessed:"), self.formatTime(status.st_atime)))
			self.data.append((_("Metadata changed:"), self.formatTime(status.st_ctime)))
			self.data.append((_("Links:"), "%d" % status.st_nlink))
			self.data.append((_("Inode:"), "%d" % status.st_ino))
			self.data.append((_("Device number:"), "%d, %d" % ((status.st_dev >> 8) & 0xff, status.st_dev & 0xff)))
			self["data"].updateList(self.data)
			self["navigationActions"].setEnabled(self.height < self.itemHeight * lines)
		except OSError as err:
			self.session.open(MessageBox, _("Error %s: Unable to get information for '%s'!  (%s)") % (err.errno, path, err.strerror), type=MessageBox.TYPE_ERROR)
			self.close()

	def keyDetails(self):
		extension = splitext(self.path)[1][1:].lower()
		if extension in MEDIA_FILES:
			# self.session.open(FileCommanderMediaInfo, self.path)
			pass
		elif extension in TEXT_FILES:
			self.session.open(FileCommanderEditor, self.path)
		elif extension == "hex":
			self.session.open(FileCommanderViewer, self.path)
		elif extension in ARCHIVE_FILES:
			self.session.open(FileCommanderArchive, self.path, self.target)
			pass


# Play media with MoviePlayer.
#
class FileCommanderMoviePlayer(MoviePlayer):
	def __init__(self, session, service):
		self.WithoutStopClose = False
		MoviePlayer.__init__(self, session, service)

	def leavePlayer(self):
		self.is_closing = True
		self.close()

	def leavePlayerConfirmed(self, answer):  # Overwrite InfoBar method!
		pass

	def doEofInternal(self, playing):
		if not self.execing:
			return
		if not playing:
			return
		self.leavePlayer()

	def showMovies(self):
		self.WithoutStopClose = True
		self.close()

	def movieSelected(self, service):
		self.leavePlayer()

	def __onClose(self):
		if not(self.WithoutStopClose):
			self.session.nav.playService(self.lastservice)


class FileCommanderImageViewer(Screen, HelpableScreen):
	width = getDesktop(0).size().width()
	height = getDesktop(0).size().height()
	skin = ["""
	<screen name="FileCommanderImageViewer" title="File Commander Image Viewer" position="fill" flags="wfNoBorder">
		<eLabel position="fill" backgroundColor="#00000000" />
		<widget name="image" position="0,0" size="%d,%d" alphatest="on" zPosition="+1" />
		<widget source="message" render="Label" position="10,%d-35" size="%d,25" borderColor="#00000000" borderWidth="2" font="Regular;20" foregroundColor="#0038FF48" noWrap="1" transparent="1" valign="bottom" zPosition="+2" />
		<widget name="icon" position="%d,%d" size="20,20" pixmap="icons/ico_mp_play.png" alphatest="blend" scale="1" zPosition="+2" />
		<widget name="status" position="%d,%d" size="20,20" pixmap="icons/record.png" alphatest="blend" scale="1" zPosition="+2" />
		<widget name="infolabels" position="10,10" size="250,600" borderColor="#00000000" borderWidth="2" font="Regular;20" foregroundColor="#0038FF48" halign="right" transparent="1" zPosition="+3" />
		<widget name="infodata" position="270,10" size="%d,600" borderColor="#00000000" borderWidth="2" font="Regular;20" foregroundColor="#0038FF48" halign="left" transparent="1" zPosition="+3" />
	</screen>
	""",
		width, height,  # image
		height, width - 70,  # message
		width - 30, height - 30,  # icon
		width - 60, height - 30,  # status
		width - 280  # infodata
	]
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
		Screen.__init__(self, session, mandatoryWidgets=["infolabels", "Test"])
		HelpableScreen.__init__(self)
		self.skinName = ["FileCommanderImageViewer", "ImageViewer"]
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
		self["message"] = StaticText(_("Please wait, loading image."))
		self["infolabels"] = Label()
		self.infoLabelsText = "%s:" % ":\n".join(self.exifDesc)
		self["infodata"] = Label()
		self.currentIndex = 0
		self.fileList = self.makeFileList(fileList, filename)
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
			scale = AVSwitch().getFramebufferScale()
			self.imageLoad.setPara([self["image"].instance.size().width(), self["image"].instance.size().height(), scale[0], scale[1], 0, 1, "#00000000"])
			self["icon"].hide()
			self["message"].setText("")
			self["infolabels"].setText("")
			self["infodata"].setText("")
			self.startDecode()

	def makeFileList(self, fileList, filename):
		elements = len(fileList[0])
		imageExtensions = (".bmp", ".gif", ".jpg", ".jpe", ".jpeg", ".png")
		# imageExtensions = tuple([".%s" % x for x in IMAGE_EXTENSIONS])
		imageList = []
		index = 0
		for fileData in fileList:
			imagePath = fileData[0][FILE_PATH] if elements > 1 else fileData[4]
			extension = splitext(imagePath)[1].lower() if imagePath and not fileData[0][FILE_IS_DIR] else None
			if extension and extension in imageExtensions:
				imageList.append(imagePath)
				if imagePath.endswith(filename):
					self.currentIndex = index
				index += 1
		return imageList

	def slideshowCallback(self):
		if not config.plugins.filecommander.slideshowLoop.value and self.lastIndex == self.fileListLen:
			self["icon"].hide()
			return
		self.displayNow = True
		self.showPicture()

	def startDecode(self):
		if len(self.fileList) == 0:
			self.currentIndex = 0
		self.imageLoad.startDecode(self.fileList[self.currentIndex])
		if self.displayOverlay:
			self["status"].show()

	def finishDecode(self, picInfo=""):
		if self.displayOverlay:
			self["status"].hide()
		data = self.imageLoad.getData()
		if data:
			try:
				text = "(%d / %d)  %s" % (self.currentIndex + 1, self.fileListLen + 1, picInfo.split("\n", 1)[0].split("/")[-1])
			except Exception:
				text = "(%d / %d)" % (self.currentIndex + 1, self.fileListLen + 1)
			exifList = self.imageLoad.getInfo(self.fileList[self.currentIndex])
			information = []
			for index in range(len(exifList)):
				information.append("%s" % exifList[index])
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
			self.slideshowTimer.start(config.plugins.filecommander.slideshowDelay.value * 1000)
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


# Hex file viewer.
#
class FileCommanderViewer(Screen, HelpableScreen):
	skin = """
	<screen name="FileCommanderViewer" title="File Commander Hex Viewer" position="40,80" size="1200,610" resolution="1280,720">
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

	def __init__(self, session, path, mode=0):
		Screen.__init__(self, session, mandatoryWidgets=["path", "location", "data", "Test"])
		HelpableScreen.__init__(self)
		self.skinName = ["FileCommanderViewer"]
		if not self.getTitle():
			self.setTitle(_("File Commander Viewer"))
		self.path = normpath(path) if path.endswith(sep) else path
		self["path"] = Label(self.path)
		self["data"] = ScrollLabel()
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"cancel": (self.close, _("Close viewer")),
			"ok": (self.close, _("Close viewer")),
			"red": (self.close, _("Close viewer")),
			"top": (self["data"].goTop, _("Move to first line / screen")),
			"pageUp": (self["data"].goPageUp, _("Move up a screen")),
			"up": (self["data"].goLineUp, _("Move up a line")),
			"down": (self["data"].goLineDown, _("Move down a line")),
			"pageDown": (self["data"].goPageDown, _("Move down a screen")),
			"bottom": (self["data"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("File Commander Viewer Actions"))
		self["hexAction"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyHex, _("Display file as hexadecimal"))
		}, prio=0, description=_("File Commander Viewer Actions"))
		self["octAction"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyOct, _("Display file as octal"))
		}, prio=0, description=_("File Commander Viewer Actions"))
		self["textAction"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.keyText, _("Display file as text"))
		}, prio=0, description=_("File Commander Viewer Actions"))
		if mode == 0:
			self.keyHex()
		elif mode == 1:
			self.keyOct()
		elif mode == 2:
			self.keyText()

	def keyHex(self):
		data = []
		try:
			with open(self.path, "rb") as fd:
				buffer = fd.read(1048576)
				for position, rowData in [(x, buffer[x:x + 16]) for x in range(0, len(buffer), 16)]:
					hexChars = " ".join(["%02X" % x for x in rowData])
					textChars = " ".join([chr(x) if 0x20 <= x < 0x7F else "?" for x in rowData])
					count = len(rowData)
					while count < 16:
						hexChars = "%s   " % hexChars
						count += 1
					data.append("%06X: %s  -  %s" % (position, hexChars, textChars))
		except OSError as err:
			data = ["Error %d: Unable to read '%s'!  (%s)" % (err.errno, self.path, err.strerror)]
		self["data"].setText("\n".join(data))
		self["key_green"].setText("")
		self["key_yellow"].setText(_("Octal"))
		self["key_blue"].setText(_("Text"))
		self["hexAction"].setEnabled(False)
		self["octAction"].setEnabled(True)
		self["textAction"].setEnabled(True)

	def keyOct(self):
		data = []
		try:
			with open(self.path, "rb") as fd:
				buffer = fd.read(1048576)
				for position, rowData in [(x, buffer[x:x + 8]) for x in range(0, len(buffer), 8)]:
					octChars = " ".join(["%03o" % x for x in rowData])
					textChars = " ".join([chr(x) if 0x20 <= x < 0x7F else "?" for x in rowData])
					count = len(rowData)
					while count < 8:
						octChars = "%s    " % octChars
						count += 1
					data.append("%08o: %s  -  %s" % (position, octChars, textChars))
		except OSError:
			data = ["Error %d: Unable to read '%s'!  (%s)" % (err.errno, self.path, err.strerror)]
		self["data"].setText("\n".join(data))
		self["key_green"].setText(_("Hexadecimal"))
		self["key_yellow"].setText("")
		self["key_blue"].setText(_("Text"))
		self["hexAction"].setEnabled(True)
		self["octAction"].setEnabled(False)
		self["textAction"].setEnabled(True)

	def keyText(self):
		data = []
		try:
			with open(self.path, "r") as fd:
				data = fd.read(1048576).splitlines()
		except OSError:
			data = ["Error %d: Unable to read '%s'!  (%s)" % (err.errno, self.path, err.strerror)]
		self["data"].setText("\n".join(data))
		self["key_green"].setText(_("Hexadecimal"))
		self["key_yellow"].setText(_("Octal"))
		self["key_blue"].setText("")
		self["hexAction"].setEnabled(True)
		self["octAction"].setEnabled(True)
		self["textAction"].setEnabled(False)


# File viewer/line editor.
#
class FileCommanderEditor(Screen, HelpableScreen):
	skin = """
	<screen name="FileCommanderEditor" title="File Commander Text Editor" position="40,80" size="1200,610" resolution="1280,720">
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
		Screen.__init__(self, session, mandatoryWidgets=["path", "location", "data", "Test"])
		HelpableScreen.__init__(self)
		self.skinName = ["FileCommanderEditor", "vEditorScreen"]
		if not self.getTitle():
			self.setTitle(_("File Commander Text Editor"))
		self.path = normpath(path) if path.endswith(sep) else path
		self.data = []
		self["path"] = Label(self.path)
		self["location"] = Label()
		self["data"] = MenuList(self.data)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Delete Line"))
		self["key_blue"] = StaticText(_("Insert Line"))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Exit editor and discard any changes")),
			"ok": (self.keyEdit, _("Edit current line")),
			"red": (self.keyCancel, _("Exit editor and discard any changes")),
			"green": (self.keySave, _("Exit editor and save any changes")),
			"yellow": (self.keyDelete, _("Delete current line")),
			"blue": (self.keyInsert, _("Insert line before current line")),
			"top": (self["data"].goTop, _("Move to first line / screen")),
			"pageUp": (self["data"].goPageUp, _("Move up a screen")),
			"up": (self["data"].goLineUp, _("Move up a line")),
			"down": (self["data"].goLineDown, _("Move down a line")),
			"pageDown": (self["data"].goPageDown, _("Move down a screen")),
			"bottom": (self["data"].goBottom, _("Move to last line / screen"))
			# Add command to sort the file.
		}, prio=0, description=_("File Commander Text Editor Actions"))
		self["moveUpAction"] = HelpableActionMap(self, ["NavigationActions"], {
			"left": (self.keyMoveLineUp, _("Move the current line up")),
		}, prio=0, description=_("File Commander Text Editor Actions"))
		self["moveDownAction"] = HelpableActionMap(self, ["NavigationActions"], {
			"right": (self.keyMoveLineDown, _("Move the current line down")),
		}, prio=0, description=_("File Commander Text Editor Actions"))
		self.isChanged = False
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["data"].instance.enableAutoNavigation(False)  # Override listbox navigation.
		self.data = fileReadLines(self.path, default=[], source=MODULE_NAME)
		self["data"].setList(self.data)
		self["data"].onSelectionChanged.append(self.updateLine)
		self.updateLine()

	def updateLine(self):
		count = self["data"].count()
		index = self["data"].getCurrentIndex()
		if count:
			self["location"].setText(_("Line %d / %d") % (index + 1, count))
		else:
			self["location"].setText(_("Empty file"))
		self["moveUpAction"].setEnabled(index > 0)
		self["moveDownAction"].setEnabled(index < count - 1)

	def keyCancel(self):
		if self.isChanged:
			msg = _("The file '%s' has been changed. Do you discard the changes?" % self.path)
			self.session.openWithCallback(self.keyCancelCallback, MessageBox, msg, MessageBox.TYPE_YESNO, default=False, windowTitle=self.getTitle())
		else:
			self.close()

	def keyCancelCallback(self, answer):
		if answer:
			self.close()

	def keySave(self):
		if self.isChanged:
			msg = [_("The file '%s' has been changed. Do you want to save it?") % self.path]
			msg.append("")
			msg.append(_("WARNING:"))
			msg.append(_("The authors are NOT RESPONSIBLE for DATA LOSS OR DAMAGE!"))
			self.session.openWithCallback(self.keyExitCallback, MessageBox, "\n".join(msg), MessageBox.TYPE_YESNO, windowTitle=self.getTitle())
		else:
			self.close()

	def keyExitCallback(self, answer):
		if answer:
			if isfile(self.path):
				copyFile(self.path, "%s.bak" % self.path)
			result = fileWriteLines(self.path, "\n".join(self.data), source=MODULE_NAME)
		self.close()

	def keyEdit(self):
		line = self["data"].getCurrent()
		# Find and replace TABs with a special single character.  This could also be helpful for NEWLINE as well.
		currPos = None if config.plugins.filecommander.editposition_lineend.value == True else 0
		self.session.openWithCallback(self.editLineCallback, VirtualKeyBoard, title="%s: %s" % (_("Original"), line), text=line, currPos=currPos, allMarked=False, windowTitle=self.getTitle())

	def editLineCallback(self, line):
		if line is not None:
			# Find and resetore TABs from a special single character.  This could also be helpful for NEWLINE as well.
			self.data[self["data"].getCurrentIndex()] = line
			self["data"].setList(self.data)
			self.isChanged = True

	def keyDelete(self):
		if self.data:
			del self.data[self["data"].getCurrentIndex()]
			self["data"].setList(self.data)
			self.isChanged = True

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


class FileCommanderArchive(Screen, HelpableScreen):
	skin = """
	<screen name="FileCommanderArchive" title="File Commander Archive" position="50,50" size="1180,600" resolution="1280,720">
		<widget name="path" position="0,0" size="1180,55" font="Regular;20" foregroundColor="#00fff000" valign="center" />
		<widget name="data" position="0,65" size="1180,485" font="Console;20" />
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

	def __init__(self, session, path, target=None):
		Screen.__init__(self, session, mandatoryWidgets=["Test"])
		HelpableScreen.__init__(self)
		self.skinName = ["FileCommanderArchive"]
		if not self.getTitle():
			self.setTitle(_("File Commander Archive"))
		self.path = normpath(path) if path.endswith(sep) else path
		self.extension = splitext(self.path)[1][1:].lower()
		if self.path[-8:].lower() == ".tar.bz2" or self.path[-7:].lower() in (".tar.gz", ".tar.xz"):
			self.extension = "tar"
		self.target = target
		self["path"] = Label(self.path)
		self["data"] = ScrollLabel(_("Please select an action from the color buttons to proceed."))
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("View"))
		self["key_yellow"] = StaticText(_("Extract"))
		self["key_blue"] = StaticText(_("Install") if self.extension == "ipk" else "")
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Close the screen")),
			"ok": (self.keyCancel, _("Close the screen")),
			"red": (self.keyCancel, _("Close the screen")),
			"green": (self.keyView, _("View the contents of the archive/package")),
			"yellow": (self.keyExtract, _("Extract the contents of the archive/package")),
			"top": (self["data"].goTop, _("Move to first line / screen")),
			"pageUp": (self["data"].goPageUp, _("Move up a screen")),
			"up": (self["data"].goLineUp, _("Move up a line")),
			"down": (self["data"].goLineDown, _("Move down a line")),
			"pageDown": (self["data"].goPageDown, _("Move down a screen")),
			"bottom": (self["data"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("File Commander Archiver Content Actions"))
		self["installAction"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"blue": (self.keyInstall, _("Install the package"))
		}, prio=0, description=_("File Commander Archiver Content Actions"))
		self["installAction"].setEnabled(self.extension == "ipk")

	def keyCancel(self):
		self.close()

	def keyView(self):
		self.textBuffer = ""
		if self.extension == "tar":
			def displayData(data):
				self["data"].setText(data)

			self.processArguments(None, ["/bin/busybox", "tar", "-tf", self.path], displayData, None)
		elif self.extension == "ipk":
			def displayData(data):
				self["data"].setText(data)

			def processControl(retVal):
				path = pathjoin(tempDir, "control.tar.gz")
				if isfile(path):
					self.textBuffer = "%s%s\n" % (self.textBuffer, _("Control files:"))
					self.processArguments(tempDir, ["/bin/busybox", "tar", "-tf", path], displayData, processArchive)

			def processArchive(retVal):
				for file in ("data.tar.gz", "data.tar.xz"):
					path = pathjoin(tempDir, file)
					if isfile(path):
						self.textBuffer = "%s\n%s\n" % (self.textBuffer, _("Package files:"))
						self.processArguments(tempDir, ["/bin/busybox", "tar", "-tf", path], displayData, processCleanup)
						break

			def processCleanup(retVal):
				for file in ("debian-binary", "control.tar.gz", "data.tar.gz", "data.tar.xz"):
					path = pathjoin(tempDir, file)
					if isfile(path):
						try:
							remove(path)
						except OSError:
							pass
				try:
					rmdir(tempDir)
				except OSError:
					pass

			tempDir = mkdtemp()
			self.processArguments(tempDir, ["/usr/bin/ar", "/usr/bin/ar", "x", self.path], None, processControl)
		elif self.extension == "rar":
			def displayData(data):
				self["data"].setText(data)

			self.processArguments(None, ["/usr/bin/unrar", "/usr/bin/unrar", "lb", self.path], displayData, None)
		else:
			def displayData(data):
				self["data"].setText("\n".join([x[53:] for x in [x for x in data.split("\n") if x]]))

			self.processArguments(None, ["/usr/bin/7za", "/usr/bin/7za", "l", "-ba", self.path], displayData, None)

	def keyExtract(self):
		choices = [
			(_("Cancel extraction"), 0),
			(_("Current directory (%s)") % pathjoin(dirname(self.path), ""), 1),
			(_("Default movie location (%s)") % config.usage.default_path.value, 3),
			(_("Temp directory (%s)") % pathjoin(gettempdir(), ""), 4),
			(_("Select a directory"), 5)
		]
		if self.target:
			choices.insert(2, (_("Other panel directory (%s)") % pathjoin(self.target, ""), 2))
		self.session.openWithCallback(self.keyExtractCallbackA, MessageBox, _("To where would you like to extract '%s'?") % self.path, type=MessageBox.TYPE_YESNO, list=choices, default=0, windowTitle=self.getTitle())

	def keyExtractCallbackA(self, answer):
		if answer == 1:
			self.keyExtractCallbackC(pathjoin(dirname(self.path), ""))
		elif answer == 2:
			self.keyExtractCallbackB(pathjoin(self.target, ""))
		elif answer == 3:
			self.keyExtractCallbackC(config.usage.default_path.value)
		elif answer == 4:
			self.keyExtractCallbackC(pathjoin(gettempdir(), ""))
		elif answer == 5:
			minFree = 100  # Get the size of the archive?
			self.session.openWithCallback(self.keyExtractCallbackB, LocationBox, text=_("Select a location into which to extract '%s':") % self.path, currDir=tempDir, minFree=minFree)

	def keyExtractCallbackB(self, target):
		if target:
			self.keyExtractCallbackC(target)

	def keyExtractCallbackC(self, target):
		self.textBuffer = ""
		if self.extension == "tar":
			def displayData(data):
				self["data"].setText(data)

			self.processArguments(target, ["/bin/busybox", "tar", "-xvf", self.path], displayData, None)
		elif self.extension == "ipk":
			def displayData(data):
				self["data"].setText(data)

			def processControl(retVal):
				path = pathjoin(target, "control.tar.gz")
				if isfile(path):
					self.textBuffer = "%s%s\n" % (self.textBuffer, _("Control files:"))
					self.processArguments(target, ["/bin/busybox", "tar", "-xvf", path], displayData, processArchive)

			def processArchive(retVal):
				for file in ("data.tar.gz", "data.tar.xz"):
					path = pathjoin(target, file)
					if isfile(path):
						self.textBuffer = "%s\n%s\n" % (self.textBuffer, _("Package files:"))
						self.processArguments(target, ["/bin/busybox", "tar", "-xvf", path], displayData, processCleanup)
						break

			def processCleanup(retVal):
				for file in ("debian-binary", "control.tar.gz", "data.tar.gz", "data.tar.xz"):
					path = pathjoin(target, file)
					if isfile(path):
						try:
							remove(path)
						except OSError:
							pass

			target = pathjoin(target, splitext(basename(self.path))[0])
			try:
				mkdir(target)
			except OSError as err:
				if err.errno != EEXIST:
					self["data"].setText("Error %d: Unable to create package directory '%s'!  (%s)" % (err.errno, target, err.strerror))
					print("[FileCommander] Error %d: Unable to create package directory '%s'!  (%s)" % (err.errno, target, err.strerror))
					return
			self.processArguments(target, ["/usr/bin/ar", "/usr/bin/ar", "x", self.path], None, processControl)
		elif self.extension == "rar":
			def displayData(data):
				self["data"].setText(data)

			self.processArguments(target, ["/usr/bin/unrar", "/usr/bin/unrar", "x", self.path], displayData, None)
		else:
			def displayData(data):
				self["data"].setText("\n".join([x[53:] for x in [x for x in data.split("\n") if x]]))

			self.processArguments(target, ["/usr/bin/7za", "/usr/bin/7za", "x", "-ba", self.path], displayData, None)

	def keyInstall(self):
		def displayData(data):
			self["data"].setText(data)

		def processInstall(retVal):
			self.processArguments(None, ["/usr/bin/opkg", "/usr/bin/opkg", "install", self.path], displayData, processPlugin)

		def processPlugin(retVal):
			if basename(self.path).startswith("enigma2-plugin-"):
				plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))

		self.textBuffer = ""
		self.processArguments(None, ["/usr/bin/opkg", "/usr/bin/opkg", "update"], displayData, processInstall)

	def processArguments(self, directory, arguments, display, finished):
		def dataAvail(data):
			if isinstance(data, bytes):
				data = data.decode()
			self.textBuffer = "%s%s" % (self.textBuffer, data)
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
		self["data"].setText(_("Please wait while the data is extracted."))


class task_postconditions(Condition):
	def check(self, task):
		global task_Stout, task_Sterr
		message = ""
		lines = config.plugins.filecommander.script_messagelen.value * -1
		if task_Stout:
			msg_out = "\n\n" + _("script 'stout':") + "\n" + "\n".join(task_Stout[lines:])
		if task_Sterr:
			msg_err = "\n\n" + _("script 'sterr':") + "\n" + "\n".join(task_Sterr[lines:])
		if task.returncode != 0:
			messageboxtyp = MessageBox.TYPE_ERROR
			msg_msg = _("Run script") + _(" ('%s') ends with error number [%d].") % (task.name, task.returncode)
		else:
			messageboxtyp = MessageBox.TYPE_INFO
			msg_msg = _("Run script") + _(" ('%s') ends with error messages.") % task.name
		if task_Stout and (task.returncode != 0 or task_Sterr):
			message += msg_msg + msg_out
		if task_Sterr:
			if message:
				message += msg_err
			else:
				message += msg_msg + msg_err
		timeout = 0
		if not message and task.returncode == 0 and config.plugins.filecommander.showScriptCompleted_message.value:
			timeout = 30
			msg_out = ""
			if task_Stout:
				msg_out = "\n\n" + "\n".join(task_Stout[lines:])
			message += _("Run script") + _(" ('%s') ends successfully.") % task.name + msg_out

		task_Stout = []
		task_Sterr = []

		if message:
			self.showMessage(message, messageboxtyp, timeout)
			return True
		return task.returncode == 0

	def showMessage(self, message, messageboxtyp, timeout):
		from Screens.Standby import inStandby
		if InfoBar.instance and not inStandby:
			InfoBar.instance.openInfoBarMessage(message, messageboxtyp, timeout)
		else:
			Tools.Notifications.AddNotification(MessageBox, message, type=messageboxtyp, timeout=timeout)


def task_processStdout(data):
	global task_Stout
	for line in data.split("\n"):
		if line:
			task_Stout.append(line)
	while len(task_Stout) > 10:
		task_Stout.pop(0)


def task_processSterr(data):
	global task_Sterr
	for line in data.split("\n"):
		if line:
			task_Sterr.append(line)
	while len(task_Sterr) > 10:
		task_Sterr.pop(0)


def formatSortingTyp(sortDirs, sortFiles):
	sortDirs, reverseDirs = [int(x) for x in sortDirs.split(".")]
	sortFiles, reverseFiles = [int(x) for x in sortFiles.split(".")]
	sD = ("n", "d", "s")[sortDirs]  # name, date, size
	sF = ("n", "d", "s")[sortFiles]
	rD = ("+", "-")[reverseDirs]  # normal, reverse
	rF = ("+", "-")[reverseFiles]
	return "[D]%s%s[F]%s%s" % (sD, rD, sF, rF)


# Start Routines
#
def filescan_open(list, session, **kwargs):
	path = "/".join(list[0].path.split("/")[:-1]) + "/"
	session.open(FileCommander, pathLeft=path)


def start_from_filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	return Scanner(
		mimetypes=None,
		paths_to_scan=[
			ScanPath(path="", with_subdirs=False),
		],
		name=PNAME,
		description=_("Open with File Commander"),
		openfnc=filescan_open,
	)


def start_from_mainmenu(menuid, **kwargs):
	if menuid == "mainmenu":  # Starting from main menu.
		return [(PNAME, start_from_pluginmenu, "filecommand", 1)]
	return []


def start_from_pluginmenu(session, **kwargs):
	session.openWithCallback(exit, FileCommander)


def exit(session, result):
	if not result:
		session.openWithCallback(exit, FileCommander)


def Plugins(path, **kwargs):
	plugin = [
		PluginDescriptor(name=PNAME, description=PDESC, where=PluginDescriptor.WHERE_PLUGINMENU, icon="FileCommander.png", fnc=start_from_pluginmenu),
		# PluginDescriptor(name=PNAME, where=PluginDescriptor.WHERE_FILESCAN, fnc=start_from_filescan)  # Buggy!!!
	]
	if config.plugins.filecommander.add_extensionmenu_entry.value:
		plugin.append(PluginDescriptor(name=PNAME, description=PDESC, where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=start_from_pluginmenu))
	if config.plugins.filecommander.add_mainmenu_entry.value:
		plugin.append(PluginDescriptor(name=PNAME, description=PDESC, where=PluginDescriptor.WHERE_MENU, fnc=start_from_mainmenu))
	return plugin
