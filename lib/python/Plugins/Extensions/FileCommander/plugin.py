from Components.config import ConfigDirectory, ConfigLocations, ConfigSelection, ConfigSelectionNumber, ConfigSubsection, ConfigText, ConfigYesNo, config
from Components.FileList import EXTENSIONS, RECORDING_EXTENSIONS
from Plugins.Plugin import PluginDescriptor
from Screens.MovieSelection import defaultMoviePath

PROGRAM_NAME = _("File Commander")
PROGRAM_DESCRIPTION = _("Manage and explore directories and files.")
PROGRAM_VERSION = f"{_("Version")} 4.12"

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


def filescanOpen(list, session, **kwargs):
	from .ui import FileCommander  # Load the file manager only when opened.
	path = "/".join(list[0].path.split("/")[:-1]) + "/"
	session.open(FileCommander, pathLeft=path)


def startFromFilescan(**kwargs):
	from Components.Scanner import ScanPath, Scanner  # File scanning is optional.
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
		return [(PROGRAM_NAME, startFromPluginMenu, "filecommand", 1)]
	return []


def startFromPluginMenu(session, **kwargs):
	from .ui import FileCommander  # Load the file manager only when opened.
	session.openWithCallback(exit, FileCommander)


def exit(session, result):
	if not result:
		startFromPluginMenu(session)


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


def __getattr__(name):
	if name in ('StatInfo', 'FileCommander', 'FileCommanderContextMenu', 'FileCommanderSetup', 'FileCommanderData', 'FileCommanderArchiveBase', 'FileCommanderArchiveExtract', 'FileCommanderArchiveInstall', 'FileCommanderArchiveView', 'FileCommanderFileViewer', 'FileCommanderPictureViewer', 'FileCommanderInformation', 'FileCommanderMediaInfo', 'FileCommanderTextEditor', 'FileCopyTask', 'FileMoveTask', 'FileDeleteTask', 'FileTestTask', 'FileTransferTask', 'TaskPostConditions', 'taskProcessStdout', 'taskProcessStderr', 'running', 'taskSTDOut', 'taskSTDErr', 'MODULE_NAME', 'STORAGE_DEVICES_NAME', 'PROTECTED_DIRECTORIES', 'HASH_CHECK_SIZE', 'MAX_EDIT_SIZE', 'MAX_HEXVIEW_SIZE', 'BLOCK_CHUNK_SIZE', 'FILE_CHUNK_SIZE', 'FILES_TO_LIST', 'ARCHIVE_FILES', 'MEDIA_FILES', 'TEXT_FILES'):
		from . import ui  # Preserve existing screen imports and live task state.
		return getattr(ui, name)
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
