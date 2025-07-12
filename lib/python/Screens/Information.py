from datetime import datetime
from glob import glob
from json import loads
from locale import format_string
from os import listdir, remove, statvfs
from os.path import basename, getmtime, isdir, isfile, join
from select import select
from subprocess import PIPE, Popen
from time import localtime, strftime, strptime
from urllib.request import urlopen

from enigma import eAVControl, eDVBFrontendParametersSatellite, eDVBResourceManager, eGetEnigmaDebugLvl, eRTSPStreamServer, eServiceCenter, eStreamServer, eTimer, getDesktop, getE2Rev, getGStreamerVersionString, iPlayableService, iServiceInformation

from ServiceReference import ServiceReference
from skin import parameters
from Components.About import about
from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import config
from Components.Console import Console
from Components.Harddisk import Harddisk, harddiskmanager
from Components.InputDevice import remoteControl
from Components.Label import Label
from Components.Network import iNetwork
from Components.NimManager import nimmanager
from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel
from Components.ServiceEventTracker import ServiceEventTracker
# from Components.Storage import Harddisk, storageManager
from Components.SystemInfo import BoxInfo, getBoxDisplayName, getDemodVersion
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.Screen import Screen, ScreenSummary
from Screens.Setup import Setup
from Tools.Conversions import scaleNumber, formatDate
from Tools.Directories import SCOPE_GUISKIN, SCOPE_SKINS, fileReadLine, fileReadLines, fileWriteLine, resolveFilename
from Tools.Geolocation import geolocation
from Tools.LoadPixmap import LoadPixmap
from Tools.MultiBoot import MultiBoot
from Tools.StbHardware import getFPVersion, getBoxProc, getHWSerial, getBoxRCType, getBoxProcType
from Tools.Transponder import ConvertToHumanReadable

MODULE_NAME = __name__.split(".")[-1]

DISPLAY_BRAND = BoxInfo.getItem("displaybrand")
DISPLAY_MODEL = BoxInfo.getItem("displaymodel")
MACHINE_BUILD = BoxInfo.getItem("machinebuild")
MODEL = BoxInfo.getItem("model")

INFO_COLORS = ["N", "H", "S", "P", "V", "M", "F"]
INFO_COLOR = {
	"B": None,
	"N": 0x00ffffff,  # Normal.
	"H": 0x00ffffff,  # Headings.
	"S": 0x00ffffff,  # Subheadings.
	"P": 0x00cccccc,  # Prompts.
	"V": 0x00cccccc,  # Values.
	"M": 0x00ffff00,  # Messages.
	"F": 0x0000ffff  # Features.
}
LOG_MAX_LINES = 10000  # Maximum number of log lines to be displayed on screen.
AUTO_REFRESH_TIME = 5000  # Streaming auto refresh timer (in milliseconds).


# This code is all to move into SystemInfo.py when it can handle translated text...
#
def getBoxProcTypeName():
	boxProcTypes = {
		"00": _("OTT Model"),
		"10": _("Single Tuner"),
		"11": _("Twin Tuner"),
		"12": _("Combo Tuner"),
		"21": _("Twin Hybrid"),
		"22": _("Hybrid Tuner")
	}
	procType = getBoxProcType()
	if procType == "unknown":
		return _("Unknown")
	return f"{procType}  -  {boxProcTypes.get(procType, _('Unknown'))}"


welcome = [
	_("Welcome to %s") % BoxInfo.getItem("displaydistro", "Enigma2")
]
BoxInfo.setItem("InformationDistributionWelcome", welcome)
#
# End of marked code.


class InformationBase(Screen):
	skin = """
	<screen name="Information" title="Information" position="center,center" size="1020,600" resolution="1280,720">
		<widget name="Image" position="0,0" size="0,0" conditional="Image" />
		<widget name="information" position="0,0" size="e,e-50" font="Regular;20" splitPosition="400" />
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

	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		self.skinName = ["Information"]
		self["information"] = ScrollLabel()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Refresh"))
		self["actions"] = HelpableActionMap(self, ["CancelSaveActions", "OkActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Close the screen")),
			"close": (self.closeRecursive, _("Close the screen and exit all menus")),
			"save": (self.refreshInformation, _("Refresh the screen")),
			"ok": (self.refreshInformation, _("Refresh the screen")),
			"top": (self["information"].goTop, _("Move to first line / screen")),
			"pageUp": (self["information"].goPageUp, _("Move up a screen")),
			"up": (self["information"].goLineUp, _("Move up a line")),
			"down": (self["information"].goLineDown, _("Move down a line")),
			"pageDown": (self["information"].goPageDown, _("Move down a screen")),
			"bottom": (self["information"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Common Information Actions"))
		colors = parameters.get("InformationColors", (0x00ffffff, 0x00ffffff, 0x00ffffff, 0x00cccccc, 0x00cccccc, 0x00ffff00, 0x0000ffff))
		if len(colors) == len(INFO_COLORS):
			for index in range(len(colors)):
				INFO_COLOR[INFO_COLORS[index]] = colors[index]
		else:
			print(f"[Information] Warning: {len(colors)} colors are defined in the skin when {len(INFO_COLORS)} were expected!")
		self["information"].setText(_("Loading information, please wait..."))
		self.extraSpacing = config.usage.informationExtraSpacing.value
		self.onInformationUpdated = [self.displayInformation]
		self.onLayoutFinish.append(self.displayInformation)
		self.console = Console()
		self.informationTimer = eTimer()
		self.informationTimer.callback.append(self.fetchInformation)
		self.informationTimer.start(25)

	def keyCancel(self):
		self.console.killAll()
		self.close()

	def closeRecursive(self):
		self.console.killAll()
		self.close(True)

	def informationWindowClosed(self, *retVal):
		if retVal and retVal[0]:
			self.close(True)

	def fetchInformation(self):
		self.informationTimer.stop()
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def refreshInformation(self):
		self.informationTimer.start(25)
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def displayInformation(self):
		pass

	def getSummaryInformation(self):
		pass

	def createSummary(self):
		return InformationSummary


def formatLine(style, left, right=None):
	styleLen = len(style)
	leftStartColor = "" if styleLen > 0 and style[0] == "B" else r"\c%08x" % (INFO_COLOR.get(style[0], "P") if styleLen > 0 else INFO_COLOR["P"])
	leftEndColor = "" if leftStartColor == "" else r"\c%08x" % INFO_COLOR["N"]
	leftIndent = "    " * int(style[1]) if styleLen > 1 and style[1].isdigit() else ""
	rightStartColor = "" if styleLen > 2 and style[2] == "B" else r"\c%08x" % (INFO_COLOR.get(style[2], "V") if styleLen > 2 else INFO_COLOR["V"])
	rightEndColor = "" if rightStartColor == "" else r"\c%08x" % INFO_COLOR["N"]
	rightIndent = "    " * int(style[3]) if styleLen > 3 and style[3].isdigit() else ""
	if right is None:
		colon = "" if styleLen > 0 and style[0] in ("M", "P", "V") else ":"
		return f"{leftIndent}{leftStartColor}{left}{colon}{leftEndColor}"
	return f"{leftIndent}{leftStartColor}{left}:{leftEndColor}|{rightIndent}{rightStartColor}{right}{rightEndColor}"


class BenchmarkInformation(InformationBase):  # This code can't be used until we find open source test code!
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Benchmark Information"))
		self.skinName.insert(0, "BenchmarkInformation")
		self.cpuTypes = []
		self.cpuBenchmark = None
		self.cpuRating = None
		self.ramBenchmark = None

	def fetchInformation(self):
		self.informationTimer.stop()
		self.cpuTypes = []
		lines = []
		lines = fileReadLines("/proc/cpuinfo", lines, source=MODULE_NAME)
		for line in lines:
			if line.startswith("model name") or line.startswith("Processor"):  # HiSilicon use the label "Processor"!
				self.cpuTypes.append([x.strip() for x in line.split(":")][1])
		self.console.ePopen(("/usr/bin/dhry", "/usr/bin/dhry"), self.cpuBenchmarkFinished)
		# Serialize the tests for better accuracy.
		# self.console.ePopen(("/usr/bin/streambench", "/usr/bin/streambench"), self.ramBenchmarkFinished)
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def cpuBenchmarkFinished(self, result, retVal, extraArgs):
		for line in result.split("\n"):
			if line.startswith("Open Vision DMIPS"):
				self.cpuBenchmark = int([x.strip() for x in line.split(":")][1])
			if line.startswith("Open Vision CPU status"):
				self.cpuRating = [x.strip() for x in line.split(":")][1]
		# Serialize the tests for better accuracy.
		self.console.ePopen(("/usr/bin/streambench", "/usr/bin/streambench"), self.ramBenchmarkFinished)
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def ramBenchmarkFinished(self, result, retVal, extraArgs):
		for line in result.split("\n"):
			if line.startswith("Open Vision copy rate"):
				self.ramBenchmark = float([x.strip() for x in line.split(":")][1])
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def refreshInformation(self):
		self.cpuBenchmark = None
		self.cpuRating = None
		self.ramBenchmark = None
		InformationBase.refreshInformation(self)

	def displayInformation(self):
		info = []
		info.append(formatLine("H", _("Benchmark information for %s %s") % getBoxDisplayName()))
		info.append("")
		for index, cpu in enumerate(self.cpuTypes):
			info.append(formatLine("P1", _("CPU / Core %d type") % index, cpu))
		info.append("")
		info.append(formatLine("P1", _("CPU benchmark"), _("%d DMIPS per core") % (self.cpuBenchmark if self.cpuBenchmark else _("Calculating benchmark..."))))
		count = len(self.cpuTypes)
		if count > 1:
			info.append(formatLine("P1", _("Total CPU benchmark"), _("%d DMIPS with %d cores") % (self.cpuBenchmark * count, count) if self.cpuBenchmark else _("Calculating benchmark...")))
		info.append(formatLine("P1", _("CPU rating"), self.cpuRating if self.cpuRating else _("Calculating rating...")))
		info.append("")
		info.append(formatLine("P1", _("RAM benchmark"), f"{self.ramBenchmark:.2f} MB/s copy rate" if self.ramBenchmark else _("Calculating benchmark...")))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Benchmark Information"


class BuildInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Build Information"))
		self.skinName.insert(0, "BuildInformation")

	def displayInformation(self):
		info = []
		info.append(formatLine("H", _("Build information for %s %s") % getBoxDisplayName()))
		info.append("")
		checksum = BoxInfo.getItem("checksumerror", False)
		if checksum:
			info.append(formatLine("M1", _("Error: Checksum is invalid!")))
		override = BoxInfo.getItem("overrideactive", False)
		if override:
			info.append(formatLine("M1", _("Warning: Overrides are currently active!")))
		if checksum or override:
			info.append("")
		for item in BoxInfo.getEnigmaInfoList():
			info.append(formatLine("P1", item, BoxInfo.getItem(item)))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Build Information"


class CommitInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Commit Log Information"))
		self.baseTitle = _("Commit Log")
		self.skinName.insert(0, "CommitInformation")
		self["key_menu"] = StaticText(_("MENU"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["commitActions"] = HelpableActionMap(self, ["MenuActions", "ColorActions", "NavigationActions"], {
			"menu": (self.showCommitMenu, _("Show selection menu for commit logs")),
			"yellow": (self.previousCommitLog, _("Show previous commit log")),
			"blue": (self.nextCommitLog, _("Show next commit log")),
			"left": (self.previousCommitLog, _("Show previous commit log")),
			"right": (self.nextCommitLog, _("Show next commit log"))
		}, prio=0, description=_("Commit Information Actions"))
		self.commitLogs = BoxInfo.getItem("InformationCommitLogs", [("Unavailable", None)])
		self.commitLogIndex = 0
		self.commitLogMax = len(self.commitLogs)
		self.cachedCommitInfo = {}

	def showCommitMenu(self):
		choices = [(commitLog[0], index) for index, commitLog in enumerate(self.commitLogs)]
		self.session.openWithCallback(self.showCommitMenuCallBack, MessageBox, text=_("Select a repository commit log to view:"), list=choices, windowTitle=self.baseTitle)

	def showCommitMenuCallBack(self, selectedIndex):
		if isinstance(selectedIndex, int):
			self.commitLogIndex = selectedIndex
			self.displayInformation()
			self.informationTimer.start(25)

	def previousCommitLog(self):
		self.commitLogIndex = (self.commitLogIndex - 1) % self.commitLogMax
		self.displayInformation()
		self.informationTimer.start(25)

	def nextCommitLog(self):
		self.commitLogIndex = (self.commitLogIndex + 1) % self.commitLogMax
		self.displayInformation()
		self.informationTimer.start(25)

	def fetchInformation(self):  # Should we limit the number of fetches per minute?
		self.informationTimer.stop()
		name = self.commitLogs[self.commitLogIndex][0]
		url = self.commitLogs[self.commitLogIndex][1]
		if url is None:
			info = [_("There are no repositories defined so commit logs are unavailable!")]
		else:
			try:
				log = []
				with urlopen(url, timeout=10) as fd:
					log = loads(fd.read())
				info = []
				for data in log:
					date = datetime.strptime(data["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ").strftime(f"{config.usage.date.daylong.value} {config.usage.time.long.value}")
					author = data["commit"]["author"]["name"]
					# committer = data["commit"]["committer"]["name"]
					message = [x.rstrip() for x in data["commit"]["message"].split("\n")]
					if info:
						info.append("")
					# info.append(_("Date: %s   Author: %s   Commit by: %s") % (date, author, committer))
					info.append(_("Date: %s   Author: %s") % (date, author))
					info.extend(message)
				if not info:
					info = [_("The '%s' commit log contains no information.") % name]
			except Exception as err:
				info = str(err)
		self.cachedCommitInfo[name] = info
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def refreshInformation(self):  # Should we limit the number of fetches per minute?
		self.cachedCommitInfo = {}
		InformationBase.refreshInformation(self)

	def displayInformation(self):
		name = self.commitLogs[self.commitLogIndex][0]
		self.setTitle(f"{self.baseTitle}: {name}")
		self["key_yellow"].setText(self.commitLogs[(self.commitLogIndex - 1) % self.commitLogMax][0])
		self["key_blue"].setText(self.commitLogs[(self.commitLogIndex + 1) % self.commitLogMax][0])
		if name in self.cachedCommitInfo:
			info = self.cachedCommitInfo[name]
			if isinstance(info, str):
				err = info
				info = []
				info.append(_("Error '%s' encountered retrieving the '%s' commit log!") % (err, name))
				info.append("")
				info.append(_("The '%s' commit log can't be retrieved, please try again later.") % name)
				info.append("")
				info.append(_("(Access to the '%s' commit log requires an Internet connection.)") % name)
		else:
			info = [_("Retrieving '%s' commit log, please wait...") % name]
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Commit Log Information"


class DebugInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Debug Log Information"))
		self.baseTitle = _("Log")
		self.skinName.insert(0, "DebugInformation")
		self["key_menu"] = StaticText()
		self["key_info"] = StaticText(_("INFO"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["debugActions"] = HelpableActionMap(self, ["MenuActions", "InfoActions", "ColorActions", "NavigationActions"], {
			"menu": (self.showLogMenu, _("Show selection menu for debug log files")),
			"info": (self.showLogSettings, _("Show the Logs Settings screen")),
			"yellow": (self.deleteLog, _("Delete the currently displayed log file")),
			"blue": (self.deleteAllLogs, _("Delete all log files")),
			"left": (self.previousDebugLog, _("Show previous debug log file")),
			"right": (self.nextDebugLog, _("Show next debug log file"))
		}, prio=0, description=_("Debug Log Information Actions"))
		self["debugActions"].setEnabled(False)
		self.debugLogs = []
		self.debugLogIndex = 0
		self.debugLogMax = 0
		self.cachedDebugInfo = {}

	def showLogMenu(self):
		choices = [(_("Log file: '%s'  (%s)") % (debugLog[0], debugLog[1]), index) for index, debugLog in enumerate(self.debugLogs)]
		self.session.openWithCallback(self.showLogMenuCallBack, MessageBox, text=_("Select a debug log file to view:"), list=choices, default=self.debugLogIndex, windowTitle=self.baseTitle)

	def showLogMenuCallBack(self, selectedIndex):
		if isinstance(selectedIndex, int):
			self.debugLogIndex = selectedIndex
			self.displayInformation()
			self.informationTimer.start(25)

	def showLogSettings(self):
		self.setTitle(_("Debug Log Information"))
		self.session.openWithCallback(self.showLogSettingsCallback, Setup, "Logs")

	def showLogSettingsCallback(self, *retVal):
		if retVal and retVal[0]:
			self.close(True)

	def deleteLog(self):
		name, sequence, path = self.debugLogs[self.debugLogIndex]
		self.session.openWithCallback(self.deleteLogCallback, MessageBox, "%s\n\n%s" % (_("Log file: '%s'  (%s)") % (name, sequence), _("Do you want to delete this log file?")), default=False)

	def deleteLogCallback(self, answer):
		if answer:
			name, sequence, path = self.debugLogs[self.debugLogIndex]
			try:
				remove(path)
				del self.cachedDebugInfo[path]
				self.session.open(MessageBox, _("Log file '%s' deleted.") % name, type=MessageBox.TYPE_INFO, timeout=5, close_on_any_key=True, windowTitle=self.baseTitle)
				self.debugLogs = []
			except OSError as err:
				self.session.open(MessageBox, _("Error %d: Log file '%s' not deleted!  (%s)") % (err.errno, name, err.strerror), type=MessageBox.TYPE_ERROR, timeout=5, windowTitle=self.baseTitle)
			self.informationTimer.start(25)

	def deleteAllLogs(self):
		self.session.openWithCallback(self.deleteAllLogsCallback, MessageBox, _("Do you want to delete all the log files?"), default=False)

	def deleteAllLogsCallback(self, answer):
		if answer:
			log = []
			type = MessageBox.TYPE_INFO
			close = True
			for name, sequence, path in self.debugLogs:
				try:
					remove(path)
					log.append(((_("Log file '%s' deleted.") % name), None))
				except OSError as err:
					type = MessageBox.TYPE_ERROR
					close = False
					log.append(((_("Error %d: Log file '%s' not deleted!  (%s)") % (err.errno, name, err.strerror)), None))
			self.session.open(MessageBox, _("Results of the delete all logs:"), type=type, list=log, timeout=5, close_on_any_key=close, windowTitle=self.baseTitle)
			self.debugLogs = []
			self.cachedDebugInfo = {}
			self.informationTimer.start(25)

	def previousDebugLog(self):
		self.debugLogIndex = (self.debugLogIndex - 1) % self.debugLogMax
		self.displayInformation()
		self.informationTimer.start(25)

	def nextDebugLog(self):
		self.debugLogIndex = (self.debugLogIndex + 1) % self.debugLogMax
		self.displayInformation()
		self.informationTimer.start(25)

	def fetchInformation(self):
		self.informationTimer.stop()
		if not self.debugLogs:
			self.debugLogs = self.findLogFiles()
			self.debugLogIndex = 0
			self.debugLogMax = len(self.debugLogs)
		if self.debugLogs:
			self["key_menu"].setText(_("MENU"))
			self["key_yellow"].setText(_("Delete log"))
			self["key_blue"].setText(_("Delete all logs"))
			self["debugActions"].setEnabled(True)
			name, sequence, path = self.debugLogs[self.debugLogIndex]
			if path in self.cachedDebugInfo:
				info = self.cachedDebugInfo[path]
			else:
				try:
					with open(path) as fd:
						info = [x.strip() for x in fd.readlines()][-LOG_MAX_LINES:]
				except OSError as err:
					info = f"{err.errno},{err.strerror}"
			self.cachedDebugInfo[path] = info
		else:
			self["key_menu"].setText("")
			self["key_yellow"].setText("")
			self["key_blue"].setText("")
			self["debugActions"].setEnabled(False)
			name = "Unavailable"
			self.debugLogs = [(name, name, name)]
			self.cachedDebugInfo[name] = f"0,{_('No log files found so debug logs are unavailable!')}"
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def findLogFiles(self):
		debugLogs = []
		installLog = "/home/root/autoinstall.log"
		if isfile(installLog):
			debugLogs.append((_("Auto install log"), _("Install 1/1"), installLog))
		crashLog = "/tmp/enigma2_crash.log"
		if isfile(crashLog):
			debugLogs.append((_("Current crash log"), _("Current 1/1"), crashLog))
		paths = [x for x in sorted(glob("/mnt/hdd/*.log"), key=lambda x: isfile(x) and getmtime(x))]
		if paths:
			countLogs = len(paths)
			for index, path in enumerate(reversed(paths)):
				debugLogs.append((basename(path), _("Log %d/%d") % (index + 1, countLogs), path))
		logPath = config.crash.debug_path.value
		paths = [x for x in sorted(glob(join(logPath, "*-enigma2-crash.log")), key=lambda x: isfile(x) and getmtime(x))]
		paths += [x for x in sorted(glob(join(logPath, "enigma2_crash*.log")), key=lambda x: isfile(x) and getmtime(x))]
		if paths:
			countLogs = len(paths)
			for index, path in enumerate(reversed(paths)):
				debugLogs.append((basename(path), _("Crash %d/%d") % (index + 1, countLogs), path))
		paths = [x for x in sorted(glob(join(logPath, "*-enigma2-debug.log")), key=lambda x: isfile(x) and getmtime(x))]
		paths += [x for x in sorted(glob(join(logPath, "Enigma2-debug*.log")), key=lambda x: isfile(x) and getmtime(x))]
		if paths:
			countLogs = len(paths)
			for index, path in enumerate(reversed(paths)):
				debugLogs.append((basename(path), _("Debug %d/%d") % (index + 1, countLogs), path))
		return debugLogs

	def refreshInformation(self):  # Should we limit the number of fetches per minute?
		self.debugLogs = []
		self.debugLogIndex = 0
		self.cachedDebugInfo = {}
		InformationBase.refreshInformation(self)

	def displayInformation(self):
		if self.debugLogs:
			name, sequence, path = self.debugLogs[self.debugLogIndex]
			self.setTitle(_("Debug Log Information") if sequence == "Unavailable" else f"{self.baseTitle}: '{name}' ({sequence})")
			if path in self.cachedDebugInfo:
				info = self.cachedDebugInfo[path]
				if isinstance(info, str):
					errno, strerror = info.split(",", 1)
					info = []
					if errno == "0":
						info.append(strerror)
					else:
						info.append(_("Error %s: Unable to retrieve the '%s' file!  (%s)") % (errno, path, strerror))
						info.append("")
						info.append(_("The '%s' file can't be retrieved, please try again later.") % path)
			else:
				info = [_("Retrieving '%s' log, please wait...") % name]
		else:
			info = [_("Finding available log files, please wait...")]
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Debug Log Information"


class DistributionInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.displayDistro = BoxInfo.getItem("displaydistro", "Enigma2")
		self.setTitle(_("%s Information") % self.displayDistro)
		self.skinName.insert(0, "DistributionInformation")
		self["key_info"] = StaticText(_("INFO"))
		self["key_yellow"] = StaticText(_("Commit Logs"))
		self["key_blue"] = StaticText(_("Translation"))
		self["receiverActions"] = HelpableActionMap(self, ["InfoActions", "ColorActions"], {
			"info": (self.showBuild, _("Show build information")),
			"yellow": (self.showCommitLogs, _("Show commit log information")),
			"blue": (self.showTranslation, _("Show translation information"))
		}, prio=0, description=_("%s Information Actions") % self.displayDistro)
		self.resolutions = {
			480: "NTSC",
			576: "PAL",
			720: "HD",
			1080: "FHD",
			2160: "4K",
			4320: "8K",
			8640: "16K"
		}
		self.imageMessage = BoxInfo.getItem("InformationDistributionWelcome", "")

	def showBuild(self):
		self.session.openWithCallback(self.informationWindowClosed, BuildInformation)

	def showCommitLogs(self):
		self.session.openWithCallback(self.informationWindowClosed, CommitInformation)

	def showTranslation(self):
		self.session.openWithCallback(self.informationWindowClosed, TranslationInformation)

	def displayInformation(self):
		info = []
		info.append(formatLine("H", _("Distribution '%s' information for %s %s") % (self.displayDistro, DISPLAY_BRAND, DISPLAY_MODEL)))
		info.append("")
		if self.imageMessage:
			for line in self.imageMessage:
				info.append(formatLine("M", line))
			info.append("")
		info.append(formatLine("S", _("System information")))
		if self.extraSpacing:
			info.append("")
		info.append(formatLine("P1", _("Info file checksum"), _("Invalid") if BoxInfo.getItem("checksumerror", False) else _("Valid")))
		override = BoxInfo.getItem("overrideactive", False)
		if override:
			info.append(formatLine("P1", _("Info file override"), _("Defined / Active")))
		info.append(formatLine("P1", _("Distribution version"), BoxInfo.getItem("imgversion")))
		info.append(formatLine("P1", _("Distribution revision"), formatDate(BoxInfo.getItem("imgrevision"))))
		info.append(formatLine("P1", _("Distribution language"), BoxInfo.getItem("imglanguage")))
		info.append(formatLine("P1", _("OEM model"), BoxInfo.getItem("platform", _("Unknown"))))
		slotCode, bootCode = MultiBoot.getCurrentSlotAndBootCodes()
		if MultiBoot.canMultiBoot():
			device = MultiBoot.getBootDevice()
			if BoxInfo.getItem("HasHiSi") and "sda" in device and slotCode != "F":
				slotCode = int(slotCode)
				image = slotCode - 4 if slotCode > 4 else slotCode - 1
				device = _("SDcard slot %s%s") % (image, f"  -  {device}" if device else "")
			else:
				if BoxInfo.getItem("HasKexecMultiboot"):
					device = MultiBoot.bootSlots[slotCode]["device"]
				elif BoxInfo.getItem("HasChkrootMultiboot"):
					device = MultiBoot.bootSlots[slotCode]["device"]
				if "mmcblk" in device:
					device = _("eMMC slot %s%s") % (slotCode, f"  -  {device}" if device else "")
				elif "mtd" in device:
					device = _("MTD slot %s%s") % (slotCode, f"  -  {device}" if device else "")
				elif "ubi" in device:
					device = _("UBI slot %s%s") % (slotCode, f"  -  {device}" if device else "")
				else:
					device = _("USB slot %s%s") % (slotCode, f"  -  {device}" if device else "")
			info.append(formatLine("P1", _("Hardware MultiBoot device"), device))
			info.append(formatLine("P1", _("MultiBoot startup file"), MultiBoot.getStartupFile()))
		if bootCode:
			info.append(formatLine("P1", _("MultiBoot boot mode"), MultiBoot.getBootCodeDescription(bootCode)))
		info.append(formatLine("P1", _("Software MultiBoot"), _("Yes") if BoxInfo.getItem("multiboot", False) else _("No")))
		if BoxInfo.getItem("HasKexecMultiboot"):
			info.append(formatLine("P1", _("Vu+ MultiBoot"), _("Yes")))
		info.append(formatLine("P1", _("Flash type"), about.getFlashType()))
		xResolution = getDesktop(0).size().width()
		yResolution = getDesktop(0).size().height()
		info.append(formatLine("P1", _("Skin & Resolution"), f"{config.skin.primary_skin.value.split('/')[0]}  ({self.resolutions.get(yResolution, 'Unknown')}  -  {xResolution} x {yResolution})"))
		info.append("")
		info.append(formatLine("S", _("Enigma2 information")))
		if self.extraSpacing:
			info.append("")
		enigmaVersion = str(BoxInfo.getItem("imageversion"))
		enigmaVersion = enigmaVersion.rsplit("-", enigmaVersion.count("-") - 2)
		if len(enigmaVersion) == 3:
			enigmaVersion = f"{enigmaVersion[0]} ({enigmaVersion[2]}-{enigmaVersion[1].capitalize()})"
		elif len(enigmaVersion) == 1:
			enigmaVersion = f"{enigmaVersion[0]}"
		else:
			enigmaVersion = f"{enigmaVersion[0]} ({enigmaVersion[1].capitalize()})"
		info.append(formatLine("P1", _("Enigma2 version"), enigmaVersion))
		info.append(formatLine("P1", _("Enigma2 revision"), getE2Rev()))
		compileDate = str(BoxInfo.getItem("compiledate"))
		info.append(formatLine("P1", _("Last update"), formatDate(f"{compileDate[:4]}{compileDate[4:6]}{compileDate[6:]}")))
		info.append(formatLine("P1", _("Last flash"), formatDate(about.getFlashDateString())))
		info.append(formatLine("P1", _("Enigma2 (re)starts"), config.misc.startCounter.value))
		info.append(formatLine("P1", _("Enigma2 debug level"), eGetEnigmaDebugLvl()))
		mediaService = BoxInfo.getItem("mediaservice")
		if mediaService:
			info.append(formatLine("P1", _("Media service"), mediaService.replace("enigma2-plugin-systemplugins-", "")))
		info.append("")
		info.append(formatLine("S", _("Build information")))
		if self.extraSpacing:
			info.append("")
		info.append(formatLine("P1", _("Distribution"), BoxInfo.getItem("displaydistro")))
		info.append(formatLine("P1", _("Distribution build"), formatDate(BoxInfo.getItem("imagebuild"))))
		info.append(formatLine("P1", _("Distribution build date"), formatDate(about.getBuildDateString())))
		info.append(formatLine("P1", _("Distribution architecture"), BoxInfo.getItem("architecture")))
		if BoxInfo.getItem("imagedir"):
			info.append(formatLine("P1", _("Distribution folder"), BoxInfo.getItem("imagedir")))
		if BoxInfo.getItem("imagefs"):
			info.append(formatLine("P1", _("Distribution file system"), BoxInfo.getItem("imagefs").strip()))
		info.append(formatLine("P1", _("File compression"), about.getFileCompressionInfo()))
		info.append(formatLine("P1", _("Feed URL"), BoxInfo.getItem("feedsurl")))
		info.append(formatLine("P1", _("Compiled by"), BoxInfo.getItem("developername")))
		info.append("")
		info.append(formatLine("S", _("Software information")))
		if self.extraSpacing:
			info.append("")
		info.append(formatLine("P1", _("GCC version"), about.getGccVersion()))
		info.append(formatLine("P1", _("Glibc version"), about.getGlibcVersion()))
		info.append(formatLine("P1", _("OpenSSL version"), about.getVersionFromOpkg("openssl")))
		info.append(formatLine("P1", _("Python version"), about.getPythonVersionString()))
		info.append(formatLine("P1", _("Rust version"), about.getRustVersion()))
		info.append(formatLine("P1", _("Samba version"), about.getVersionFromOpkg("samba")))
		info.append(formatLine("P1", _("GStreamer version"), getGStreamerVersionString().replace("GStreamer ", "")))
		info.append(formatLine("P1", _("FFmpeg version"), about.getVersionFromOpkg("ffmpeg")))
		bootId = fileReadLine("/proc/sys/kernel/random/boot_id", source=MODULE_NAME)
		if bootId:
			info.append(formatLine("P1", _("Boot ID"), bootId))
		uuId = fileReadLine("/proc/sys/kernel/random/uuid", source=MODULE_NAME)
		if uuId:
			info.append(formatLine("P1", _("UUID"), uuId))
		info.append("")
		info.append(formatLine("S", _("Boot information")))
		if self.extraSpacing:
			info.append("")
		if BoxInfo.getItem("mtdbootfs"):
			info.append(formatLine("P1", _("MTD boot"), BoxInfo.getItem("mtdbootfs")))
		if BoxInfo.getItem("mtdkernel"):
			info.append(formatLine("P1", _("MTD kernel"), BoxInfo.getItem("mtdkernel")))
		if BoxInfo.getItem("mtdrootfs"):
			info.append(formatLine("P1", _("MTD root"), BoxInfo.getItem("mtdrootfs")))
		if BoxInfo.getItem("kernelfile"):
			info.append(formatLine("P1", _("Kernel file"), BoxInfo.getItem("kernelfile")))
		if BoxInfo.getItem("rootfile"):
			info.append(formatLine("P1", _("Root file"), BoxInfo.getItem("rootfile")))
		if BoxInfo.getItem("mkubifs"):
			info.append(formatLine("P1", _("MKUBIFS"), BoxInfo.getItem("mkubifs")))
		if BoxInfo.getItem("ubinize"):
			info.append(formatLine("P1", _("UBINIZE"), BoxInfo.getItem("ubinize")))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return f"{self.displayDistro} Information"


class GeolocationInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Geolocation Information"))
		self.skinName.insert(0, "GeolocationInformation")

	def displayInformation(self):
		info = []
		info.append(formatLine("H", _("Geolocation information for %s %s") % getBoxDisplayName()))
		info.append("")
		geolocationData = geolocation.getGeolocationData(fields="continent,country,regionName,city,lat,lon,timezone,currency,isp,org,mobile,proxy,query", useCache=False)
		if geolocationData.get("status", None) == "success":
			info.append(formatLine("S", _("Location information")))
			if self.extraSpacing:
				info.append("")
			continent = geolocationData.get("continent", None)
			if continent:
				info.append(formatLine("P1", _("Continent"), continent))
			country = geolocationData.get("country", None)
			if country:
				info.append(formatLine("P1", _("Country"), country))
			state = geolocationData.get("regionName", None)
			if state:
				# TRANSLATORS: "State" is location information and not condition based information.
				info.append(formatLine("P1", _("State"), state))
			city = geolocationData.get("city", None)
			if city:
				info.append(formatLine("P1", _("City"), city))
			latitude = geolocationData.get("lat", None)
			if latitude:
				info.append(formatLine("P1", _("Latitude"), latitude))
			longitude = geolocationData.get("lon", None)
			if longitude:
				info.append(formatLine("P1", _("Longitude"), longitude))
			info.append("")
			info.append(formatLine("S", _("Local information")))
			if self.extraSpacing:
				info.append("")
			timezone = geolocationData.get("timezone", None)
			if timezone:
				info.append(formatLine("P1", _("Timezone"), timezone))
			currency = geolocationData.get("currency", None)
			if currency:
				info.append(formatLine("P1", _("Currency"), currency))
			info.append("")
			info.append(formatLine("S", _("Connection information")))
			if self.extraSpacing:
				info.append("")
			isp = geolocationData.get("isp", None)
			if isp:
				ispOrg = geolocationData.get("org", None)
				if ispOrg:
					info.append(formatLine("P1", _("ISP"), f"{isp}  ({ispOrg})"))
				else:
					info.append(formatLine("P1", _("ISP"), isp))
			mobile = geolocationData.get("mobile", None)
			info.append(formatLine("P1", _("Mobile connection"), (_("Yes") if mobile else _("No"))))
			proxy = geolocationData.get("proxy", False)
			info.append(formatLine("P1", _("Proxy detected"), (_("Yes") if proxy else _("No"))))
			publicIp = geolocationData.get("query", None)
			if publicIp:
				info.append(formatLine("P1", _("Public IP"), publicIp))
		else:
			info.append(_("Geolocation information cannot be retrieved, please try again later."))
			info.append("")
			info.append(_("Access to geolocation information requires an Internet connection."))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Geolocation Information"


class MemoryInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Memory Information"))
		self.skinName.insert(0, "MemoryInformation")
		self["clearActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.clearMemoryInformation, _("Clear the virtual memory caches"))
		}, prio=0, description=_("Memory Information Actions"))
		self["key_yellow"] = StaticText(_("Clear"))

	def displayInformation(self):
		def formatNumber(number):
			number = number.strip()
			value, units = number.split(maxsplit=1) if " " in number else (number, None)
			if "." in value:
				format = "%.3f"
				value = float(value)
			else:
				format = "%d"
				value = int(value)
			return f"{format_string(format, value, grouping=True)} {units}" if units else format_string(format, value, grouping=True)

		info = []
		info.append(formatLine("H", _("Memory information for %s %s") % getBoxDisplayName()))
		info.append("")
		memInfo = fileReadLines("/proc/meminfo", source=MODULE_NAME)
		info.append(formatLine("S", _("RAM (Summary)")))
		if self.extraSpacing:
			info.append("")
		for line in memInfo:
			key, value = (x for x in line.split(maxsplit=1))
			if key == "MemTotal:":
				info.append(formatLine("P1", _("Total memory"), formatNumber(value)))
			elif key == "MemFree:":
				info.append(formatLine("P1", _("Free memory"), formatNumber(value)))
			elif key == "Buffers:":
				info.append(formatLine("P1", _("Buffers"), formatNumber(value)))
			elif key == "Cached:":
				info.append(formatLine("P1", _("Cached"), formatNumber(value)))
			elif key == "SwapTotal:":
				info.append(formatLine("P1", _("Total swap"), formatNumber(value)))
			elif key == "SwapFree:":
				info.append(formatLine("P1", _("Free swap"), formatNumber(value)))
		info.append("")
		info.append(formatLine("S", _("FLASH")))
		if self.extraSpacing:
			info.append("")
		stat = statvfs("/")
		diskSize = stat.f_blocks * stat.f_frsize
		diskFree = stat.f_bfree * stat.f_frsize
		diskUsed = diskSize - diskFree
		info.append(formatLine("P1", _("Total flash"), f"{scaleNumber(diskSize)}  ({scaleNumber(diskSize, 'Iec')})"))
		info.append(formatLine("P1", _("Used flash"), f"{scaleNumber(diskUsed)}  ({scaleNumber(diskUsed, 'Iec')})"))
		info.append(formatLine("P1", _("Free flash"), f"{scaleNumber(diskFree)}  ({scaleNumber(diskFree, 'Iec')})"))
		for line in fileReadLines("/proc/mtd", [], source=MODULE_NAME):
			if "\"kernel" in line:
				data = line.split()
				name = data[3].strip("\"")
				size = int(data[1], 16)
				label = _("Kernel partition") if name == "kernel" else _("Kernel%s partition") % name.replace("kernel", "")
				info.append(formatLine("P1", label, f"{scaleNumber(size)} ({scaleNumber(size, "Iec")})"))
		info.append("")
		info.append(formatLine("S", _("RAM (Details)")))
		if self.extraSpacing:
			info.append("")
		for line in memInfo:
			key, value = (x for x in line.split(maxsplit=1))
			info.append(formatLine("P1", key[:-1], formatNumber(value)))
		info.append("")
		info.append(formatLine("M1", _("The detailed information is intended for developers only.")))
		info.append(formatLine("M1", _("Please don't panic if you see values that look suspicious.")))
		self["information"].setText("\n".join(info))

	def clearMemoryInformation(self):
		self.console.ePopen(("/bin/sync", "/bin/sync"))
		fileWriteLine("/proc/sys/vm/drop_caches", "3")
		self.informationTimer.start(25)
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def getSummaryInformation(self):
		return "Memory Information Data"


class MultiBootInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("MultiBoot Information"))
		self.skinName.insert(0, "MultiBootInformation")
		self.slotImages = None

	def fetchInformation(self):
		def fetchInformationCallback(slotImages):
			self.slotImages = slotImages
			for callback in self.onInformationUpdated:
				if callable(callback):
					callback()

		self.informationTimer.stop()
		MultiBoot.getSlotImageList(fetchInformationCallback)

	def refreshInformation(self):
		self.slotImages = None
		MultiBoot.loadMultiBoot()
		InformationBase.refreshInformation(self)

	def displayInformation(self):
		info = []
		info.append(formatLine("H", _("Boot slot information for %s %s") % getBoxDisplayName()))
		info.append("")
		if self.slotImages:
			slotCode, bootCode = MultiBoot.getCurrentSlotAndBootCodes()
			slotImageList = sorted(self.slotImages.keys(), key=lambda x: (not x.isnumeric(), int(x) if x.isnumeric() else x))
			currentMsg = f"  -  {_('Current')}"
			imageLists = {}
			for slot in slotImageList:
				for boot in self.slotImages[slot]["bootCodes"]:
					if imageLists.get(boot) is None:
						imageLists[boot] = []
					current = currentMsg if boot == bootCode and slot == slotCode else ""
					indent = "P0V" if boot == "" else "P1V"
					if current:
						indent = indent.replace("P", "F").replace("V", "F")
					device = self.slotImages[slot]["device"]
					slotType = "eMMC" if "mmcblk" in device else "MTD" if "mtd" in device else "UBI" if "ubi" in device else "USB"
					imageLists[boot].append(formatLine(indent, _("Slot '%s' %s") % (slot, slotType), f"{self.slotImages[slot]['imagename']}{current}"))
			count = 0
			for bootCode in sorted(imageLists.keys()):
				if bootCode == "":
					continue
				if count:
					info.append("")
				info.append(formatLine("S", MultiBoot.getBootCodeDescription(bootCode), None))
				if self.extraSpacing:
					info.append("")
				info.extend(imageLists[bootCode])
				count += 1
			if count:
				info.append("")
			if "" in imageLists:
				info.extend(imageLists[""])
		else:
			info.append(formatLine("P1", _("Retrieving boot slot information...")))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "MultiBoot Information Data"


class NetworkInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Network Information"))
		self.skinName.insert(0, "NetworkInformation")
		self["key_yellow"] = StaticText(_("WAN Geolocation"))
		self["geolocationActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.useGeolocation, _("Use geolocation to get WAN information")),
		}, prio=0, description=_("Network Information Actions"))
		self.interfaceData = {}
		self.geolocationData = []
		self.ifconfigAttributes = {
			"Link encap": "encapsulation",
			"HWaddr": "mac",
			"inet addr": "addr",
			"Bcast": "brdaddr",
			"Mask": "nmask",
			"inet6 addr": "addr6",
			"Scope": "scope",
			"MTU": "mtu",
			"Metric": "metric",
			"RX packets": "rxPackets",
			"rxerrors": "rxErrors",
			"rxdropped": "rxDropped",
			"rxoverruns": "rxOverruns",
			"rxframe": "rxFrame",
			"TX packets": "txPackets",
			"txerrors": "txErrors",
			"txdropped": "txDropped",
			"txoverruns": "txOverruns",
			"collisions": "txCollisions",
			"txqueuelen": "txQueueLen",
			"RX bytes": "rxBytes",
			"TX bytes": "txBytes"
		}
		self.iwconfigAttributes = {
			"interface": "interface",
			"standard": "standard",
			"ESSID": "ssid",
			"Mode": "mode",
			"Frequency": "frequency",
			"Access Point": "accessPoint",
			"Bit Rate": "bitrate",
			"Tx-Power": "transmitPower",
			"Retry short limit": "retryLimit",
			"RTS thr": "rtsThrottle",
			"Fragment thr": "fragThrottle",
			"Encryption key": "encryption",
			"Power Management": "powerManagement",
			"Link Quality": "signalQuality",
			"Signal level": "signalStrength",
			"Rx invalid nwid": "rxInvalidNwid",
			"Rx invalid crypt": "rxInvalidCrypt",
			"Rx invalid frag": "rxInvalidFrag",
			"Tx excessive retries": "txExcessiveReties",
			"Invalid misc": "invalidMisc",
			"Missed beacon": "missedBeacon"
		}
		self.ethtoolAttributes = {
			"Speed": "speed",
			"Duplex": "duplex",
			"Transceiver": "transceiver",
			"Auto-negotiation": "autoNegotiation",
			"Link detected": "link"
		}

	def useGeolocation(self):
		geolocationData = geolocation.getGeolocationData(fields="isp,org,mobile,proxy,query", useCache=False)
		info = []
		if geolocationData.get("status", None) == "success":
			info.append("")
			info.append(formatLine("S", _("WAN connection information")))
			isp = geolocationData.get("isp", None)
			if isp:
				ispOrg = geolocationData.get("org", None)
				if ispOrg:
					info.append(formatLine("P1", _("ISP"), f"{isp}  ({ispOrg})"))
				else:
					info.append(formatLine("P1", _("ISP"), isp))
			mobile = geolocationData.get("mobile", None)
			info.append(formatLine("P1", _("Mobile connection"), (_("Yes") if mobile else _("No"))))
			proxy = geolocationData.get("proxy", False)
			info.append(formatLine("P1", _("Proxy detected"), (_("Yes") if proxy else _("No"))))
			publicIp = geolocationData.get("query", None)
			if publicIp:
				info.append(formatLine("P1", _("Public IP"), publicIp))
		else:
			info.append(_("Geolocation information cannot be retrieved, please try again later."))
			info.append("")
			info.append(_("Access to geolocation information requires an Internet connection."))
		self.geolocationData = info
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def fetchInformation(self):
		self.informationTimer.stop()
		for interface in sorted([x for x in listdir("/sys/class/net") if not self.isBlacklisted(x)]):
			self.interfaceData[interface] = {}
			self.console.ePopen(("/sbin/ifconfig", "/sbin/ifconfig", interface), self.ifconfigInfoFinished, extra_args=interface)
			if iNetwork.isWirelessInterface(interface):
				self.console.ePopen(("/sbin/iwconfig", "/sbin/iwconfig", interface), self.iwconfigInfoFinished, extra_args=interface)
			else:
				self.console.ePopen(("/usr/sbin/ethtool", "/usr/sbin/ethtool", interface), self.ethtoolInfoFinished, extra_args=interface)
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def isBlacklisted(self, interface):
		for type in ("lo", "wifi", "wmaster", "sit", "tun", "sys", "p2p", "ip6_vti", "ip_vti", "ip6tn", "wg", "tap"):
			if interface.startswith(type):
				return True
		return False

	def ifconfigInfoFinished(self, result, retVal, extraArgs):  # This temporary code borrowed and adapted from the new but unreleased Network.py!
		if retVal == 0:
			capture = False
			data = ""
			if isinstance(result, bytes):
				result = result.decode("UTF-8", "ignore")
			for line in result.split("\n"):
				if line.startswith(f"{extraArgs} "):
					capture = True
					if "HWaddr " in line:
						line = line.replace("HWaddr ", "HWaddr:")
					data += line
					continue
				if capture and line.startswith(" "):
					if " Scope:" in line:
						line = line.replace(" Scope:", " ")
					elif "X packets:" in line:
						pos = line.index("X packets:")
						direction = line[pos - 1:pos].lower()
						line = "%s%s" % (line[0:pos + 10], line[pos + 10:].replace(" ", "  %sx" % direction))
						# line = f"{line[0:pos + 10]}{line[pos + 10:].replace(" ", f"  {direction}x")}"  # Python 3.12
					elif " txqueuelen" in line:
						line = line.replace(" txqueuelen:", "  txqueuelen:")
					data += line
					continue
				if line == "":
					break
			data = list(filter(None, [x.strip().replace("=", ":", 1) for x in data.split("  ")]))
			data[0] = f"interface:{data[0]}"
			# print("[Network] DEBUG: Raw network data %s." % data)
			for item in data:
				if ":" not in item:
					flags = item.split()
					self.interfaceData[extraArgs]["up"] = True if "UP" in flags else False
					self.interfaceData[extraArgs]["status"] = "up" if "UP" in flags else "down"  # Legacy status flag.
					self.interfaceData[extraArgs]["running"] = True if "RUNNING" in flags else False
					self.interfaceData[extraArgs]["broadcast"] = True if "BROADCAST" in flags else False
					self.interfaceData[extraArgs]["multicast"] = True if "MULTICAST" in flags else False
					continue
				key, value = item.split(":", 1)
				key = self.ifconfigAttributes.get(key, None)
				if key:
					value = value.strip()
					if value.startswith("\""):
						value = value[1:-1]
					if key == "addr6":
						if key not in self.interfaceData[extraArgs]:
							self.interfaceData[extraArgs][key] = []
						self.interfaceData[extraArgs][key].append(value)
					else:
						self.interfaceData[extraArgs][key] = value
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def iwconfigInfoFinished(self, result, retVal, extraArgs):  # This temporary code borrowed and adapted from the new but unreleased Network.py!
		if retVal == 0:
			capture = False
			data = ""
			if isinstance(result, bytes):
				result = result.decode("UTF-8", "ignore")
			for line in result.split("\n"):
				if line.startswith(f"{extraArgs} "):
					capture = True
					data += line
					continue
				if capture and line.startswith(" "):
					data += line
					continue
				if line == "":
					break
			data = list(filter(None, [x.strip().replace("=", ":", 1) for x in data.split("  ")]))
			data[0] = f"interface:{data[0]}"
			data[1] = f"standard:{data[1]}"
			for item in data:
				if ":" not in item:
					continue
				key, value = item.split(":", 1)
				key = self.iwconfigAttributes.get(key, None)
				if key:
					value = value.strip()
					if value.startswith("\""):
						value = value[1:-1]
					self.interfaceData[extraArgs][key] = value
			if "encryption" in self.interfaceData[extraArgs]:
				self.interfaceData[extraArgs]["encryption"] = _("Disabled or WPA/WPA2") if self.interfaceData[extraArgs]["encryption"] == "off" else _("Enabled")
			if "standard" in self.interfaceData[extraArgs] and "no wireless extensions" in self.interfaceData[extraArgs]["standard"]:
				del self.interfaceData[extraArgs]["standard"]
				self.interfaceData[extraArgs]["wireless"] = False
			else:
				self.interfaceData[extraArgs]["wireless"] = True
			if "ssid" in self.interfaceData[extraArgs]:
				self.interfaceData[extraArgs]["SSID"] = self.interfaceData[extraArgs]["ssid"]
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def ethtoolInfoFinished(self, result, retVal, extraArgs):  # This temporary code borrowed and adapted from the new but unreleased Network.py!
		if retVal == 0:
			if isinstance(result, bytes):
				result = result.decode("UTF-8", "ignore")
			for line in result.split("\n"):
				if "Speed:" in line:
					self.interfaceData[extraArgs]["speed"] = line.split(":")[1][:-4].strip()
				if "Duplex:" in line:
					self.interfaceData[extraArgs]["duplex"] = _(line.split(":")[1].strip().capitalize())
				if "Transceiver:" in line:
					self.interfaceData[extraArgs]["transeiver"] = _(line.split(":")[1].strip().capitalize())
				if "Auto-negotiation:" in line:
					self.interfaceData[extraArgs]["autoNegotiation"] = line.split(":")[1].strip().lower() == "on"
				if "Link detected:" in line:
					self.interfaceData[extraArgs]["link"] = line.split(":")[1].strip().lower() == "yes"
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def displayInformation(self):
		info = []
		info.append(formatLine("H", _("Network information for %s %s") % getBoxDisplayName()))
		info.append("")
		hostname = fileReadLine("/proc/sys/kernel/hostname", source=MODULE_NAME)
		info.append(formatLine("S0S", _("Hostname"), hostname))
		for interface in sorted(self.interfaceData.keys()):
			info.append("")
			info.append(formatLine("S", _("Interface '%s'") % interface, iNetwork.getFriendlyAdapterName(interface)))
			if "up" in self.interfaceData[interface]:
				info.append(formatLine("P1", _("Status"), (_("Up / Active") if self.interfaceData[interface]["up"] else _("Down / Inactive"))))
				if self.interfaceData[interface]["up"]:
					if "addr" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("IP address"), self.interfaceData[interface]["addr"]))
					if "nmask" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Netmask"), self.interfaceData[interface]["nmask"]))
					if "brdaddr" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Broadcast address"), self.interfaceData[interface]["brdaddr"]))
					if "addr6" in self.interfaceData[interface]:
						for addr6 in self.interfaceData[interface]["addr6"]:
							addr, scope = addr6.split()
							info.append(formatLine("P1", _("IPv6 address"), addr))
							info.append(formatLine("P3V2", _("Scope"), scope))
						info.append(formatLine("P1", _("IPv6 address"), "2003:0000:4021:4700:4270:0000:0000:8250/64"))
						info.append(formatLine("P3V2", _("Scope"), "Global"))
					if "mac" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("MAC address"), self.interfaceData[interface]["mac"]))
					if "speed" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Speed"), f"{self.interfaceData[interface]['speed']} Mbps"))
					if "duplex" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Duplex"), self.interfaceData[interface]["duplex"]))
					if "mtu" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("MTU"), self.interfaceData[interface]["mtu"]))
					if "link" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Link detected"), (_("Yes") if self.interfaceData[interface]["link"] else _("No"))))
					if "ssid" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("SSID"), self.interfaceData[interface]["ssid"]))
					if "standard" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Standard"), self.interfaceData[interface]["standard"]))
					if "encryption" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Encryption"), self.interfaceData[interface]["encryption"]))
					if "frequency" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Frequency"), self.interfaceData[interface]["frequency"]))
					if "accessPoint" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Access point"), self.interfaceData[interface]["accessPoint"]))
					if "bitrate" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Bitrate"), self.interfaceData[interface]["bitrate"]))
					if "signalQuality" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Signal quality"), self.interfaceData[interface]["signalQuality"]))
					if "signalStrength" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Signal strength"), self.interfaceData[interface]["signalStrength"]))
			if "rxBytes" in self.interfaceData[interface] or "txBytes" in self.interfaceData[interface]:
				info.append("")
				rxBytes = int(self.interfaceData[interface]["rxBytes"].split(" ")[0])
				txBytes = int(self.interfaceData[interface]["txBytes"].split(" ")[0])
				info.append(formatLine("P1", _("Bytes received"), "%d (%s)" % (rxBytes, scaleNumber(rxBytes, style="Iec", format="%.1f"))))
				info.append(formatLine("P1", _("Bytes sent"), "%d (%s)" % (txBytes, scaleNumber(txBytes, style="Iec", format="%.1f"))))
		info += self.geolocationData
		self["information"].setText("\n".join(info))


class PictureInformation(Screen):
	skin = """
	<screen name="PictureInformation" title="Picture Information" position="center,center" size="950,560" resolution="1280,720">
		<widget name="Image" position="0,0" size="0,0" conditional="Image" />
		<widget name="name" position="0,0" size="e,25" font="Regular;20" halign="center" transparent="1" valign="center" />
		<widget name="picture" position="0,35" size="e,e-85" alphatest="blend" scaleFlags="scaleCenter" transparent="1" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="380,e-40" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="570,e-40" size="180,40" backgroundColor="key_blue" conditional="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Picture Information"))
		self["name"] = Label()
		self["picture"] = Pixmap()
		self["key_red"] = StaticText(_("Close"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"cancel": (self.keyCancel, _("Close the screen")),
			"close": (self.closeRecursive, _("Close the screen and exit all menus")),
			"red": (self.keyCancel, _("Close the screen")),
		}, prio=0, description=_("Picture Information Actions"))
		self["pictureActions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"ok": (self.nextPicture, _("Show next picture")),
			"yellow": (self.prevPicture, _("Show previous picture")),
			"blue": (self.nextPicture, _("Show next picture")),
			"up": (self.prevPicture, _("Show previous picture")),
			"left": (self.prevPicture, _("Show previous picture")),
			"right": (self.nextPicture, _("Show next picture")),
			"down": (self.nextPicture, _("Show next picture"))
		}, prio=0, description=_("Picture Information Actions"))
		self["pictureActions"].setEnabled(False)
		self.definedPictures = (
			(_("Remote Control"), f"hardware/{BoxInfo.getItem('rcname')}.png"),
			(_("Front"), f"hardware/{MACHINE_BUILD}_front.png"),
			(_("Rear"), f"hardware/{MACHINE_BUILD}_rear.png"),
			(_("Internal"), f"hardware/{MACHINE_BUILD}_internal.png")
		)
		self.pictures = []
		for item in self.definedPictures:
			picture = resolveFilename(SCOPE_SKINS, item[1])
			if isfile(picture):
				picture = LoadPixmap(picture)
				if picture:
					self.pictures.append((item[0], picture))
		if not self.pictures:
			self.pictures.append((_("No pictures available"), None))
		self.pictureIndex = 0
		self.pictureMax = len(self.pictures)
		self.onLayoutFinish.append(self.layoutFinished)

	def keyCancel(self):
		self.close()

	def closeRecursive(self):
		self.close(True)

	def layoutFinished(self):
		self["name"].setText(f"{DISPLAY_BRAND} {DISPLAY_MODEL}  -  {self.pictures[self.pictureIndex][0]} View")
		if self.pictureMax > 1:
			self["key_yellow"].setText(_("%s View") % self.pictures[(self.pictureIndex - 1) % self.pictureMax][0])
			self["key_blue"].setText(_("%s View") % self.pictures[(self.pictureIndex + 1) % self.pictureMax][0])
			self["pictureActions"].setEnabled(True)
		else:
			self["key_yellow"].setText("")
			self["key_blue"].setText("")
			self["pictureActions"].setEnabled(False)
		picture = self.pictures[self.pictureIndex][1]
		if picture:
			self["picture"].instance.setPixmap(self.pictures[self.pictureIndex][1])

	def prevPicture(self):
		self.pictureIndex = (self.pictureIndex - 1) % self.pictureMax
		self.layoutFinished()

	def nextPicture(self):
		self.pictureIndex = (self.pictureIndex + 1) % self.pictureMax
		self.layoutFinished()


class ReceiverInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Receiver Information"))
		self.skinName.insert(0, "ReceiverInformation")
		self["key_info"] = StaticText(_("INFO"))
		self["key_yellow"] = StaticText(_("System Information"))
		self["key_blue"] = StaticText(_("Debug Information"))
		self["receiverActions"] = HelpableActionMap(self, ["InfoActions", "ColorActions"], {
			"info": (self.showPictureInformation, _("Show picture information")),
			"yellow": (self.showSystemInformation, _("Show system information")),
			"blue": (self.showDebugInformation, _("Show debug log information"))
		}, prio=0, description=_("Receiver Information Actions"))

	def showPictureInformation(self):
		self.session.openWithCallback(self.informationWindowClosed, PictureInformation)

	def showSystemInformation(self):
		self.session.openWithCallback(self.informationWindowClosed, SystemInformation)

	def showDebugInformation(self):
		self.session.openWithCallback(self.informationWindowClosed, DebugInformation)

	def displayInformation(self):
		def findPackageRevision(package, packageList):
			revision = None
			data = [x for x in packageList if f"-{package}" in x]
			if data:
				data = data[0].split("-")
				if len(data) >= 4:
					revision = data[3]
			return revision

		info = []
		info.append(formatLine("H", _("Receiver information for %s %s") % getBoxDisplayName()))
		info.append("")
		info.append(formatLine("S", _("Hardware information")))
		if self.extraSpacing:
			info.append("")
		info.append(formatLine("P1", _("Receiver name"), "%s %s" % getBoxDisplayName()))
		info.append(formatLine("P1", _("Build Brand"), BoxInfo.getItem("brand")))
		platform = BoxInfo.getItem("platform")
		info.append(formatLine("P1", _("Build Model"), MODEL))
		if platform != MODEL:
			info.append(formatLine("P1", _("Platform"), platform))
		procModel = getBoxProc()
		if procModel != MODEL:
			info.append(formatLine("P1", _("Proc model"), procModel))
		procModelType = getBoxProcTypeName()
		if procModelType and procModelType != "unknown":
			info.append(formatLine("P1", _("Hardware type"), procModelType))
		hwSerial = getHWSerial()
		if hwSerial:
			info.append(formatLine("P1", _("Hardware serial"), (hwSerial if hwSerial != "unknown" else about.getCPUSerial())))
		hwRelease = fileReadLine("/proc/stb/info/release", source=MODULE_NAME)
		if hwRelease:
			info.append(formatLine("P1", _("Factory release"), hwRelease))
		displayType = BoxInfo.getItem("displaytype")
		if displayType and not displayType.startswith(" "):
			info.append(formatLine("P1", _("Display type"), displayType))
		fpVersion = getFPVersion()
		if fpVersion and fpVersion != "unknown":
			info.append(formatLine("P1", _("Front processor version"), fpVersion))
		demodVersion = getDemodVersion()
		if demodVersion and demodVersion != "unknown":
			info.append(formatLine("P1", _("Demod firmware version"), demodVersion))
		transcoding = _("Yes") if BoxInfo.getItem("transcoding") else _("MultiTranscoding") if BoxInfo.getItem("multitranscoding") else _("No")
		info.append(formatLine("P1", _("Transcoding"), transcoding))
		temp = about.getSystemTemperature()
		if temp:
			info.append(formatLine("P1", _("System temperature"), temp))
		info.append("")
		info.append(formatLine("S", _("Processor information")))
		if self.extraSpacing:
			info.append("")
		cpu = about.getCPUInfoString()
		info.append(formatLine("P1", _("CPU"), cpu[0]))
		info.append(formatLine("P1", _("CPU speed/cores"), f"{cpu[1]} {cpu[2]}"))
		if cpu[3]:
			info.append(formatLine("P1", _("CPU temperature"), cpu[3]))
		info.append(formatLine("P1", _("CPU brand"), about.getCPUBrand()))
		socFamily = BoxInfo.getItem("socfamily")
		if socFamily:
			info.append(formatLine("P1", _("SoC family"), socFamily))
		info.append(formatLine("P1", _("CPU architecture"), about.getCPUArch()))
		if BoxInfo.getItem("fpu"):
			info.append(formatLine("P1", _("FPU"), BoxInfo.getItem("fpu")))
		if BoxInfo.getItem("architecture") == "aarch64":
			info.append(formatLine("P1", _("MultiLib"), (_("Yes") if BoxInfo.getItem("multilib") else _("No"))))
		info.append("")
		info.append(formatLine("S", _("Remote control information")))
		if self.extraSpacing:
			info.append("")
		rcIndex = int(config.inputDevices.remotesIndex.value)
		info.append(formatLine("P1", _("RC identification"), f"{remoteControl.remotes[rcIndex][remoteControl.REMOTE_DISPLAY_NAME]}  (Index: {rcIndex})"))
		rcName = remoteControl.remotes[rcIndex][remoteControl.REMOTE_NAME]
		info.append(formatLine("P1", _("RC selected name"), rcName))
		boxName = BoxInfo.getItem("rcname")
		if boxName != rcName:
			info.append(formatLine("P1", _("RC default name"), boxName))
		rcType = remoteControl.remotes[rcIndex][remoteControl.REMOTE_RCTYPE]
		info.append(formatLine("P1", _("RC selected type"), rcType))
		boxType = BoxInfo.getItem("rctype")
		if boxType != rcType:
			info.append(formatLine("P1", _("RC default type"), boxType))
		boxRcType = getBoxRCType()
		if boxRcType:
			if boxRcType == "unknown":
				if isfile("/usr/bin/remotecfg"):
					boxRcType = _("Amlogic remote")
				elif isfile("/usr/sbin/lircd"):
					boxRcType = _("LIRC remote")
			if boxRcType != rcType and boxRcType != "unknown":
				info.append(formatLine("P1", _("RC detected type"), boxRcType))
		customCode = fileReadLine("/proc/stb/ir/rc/customcode", source=MODULE_NAME)
		if customCode:
			info.append(formatLine("P1", _("RC custom code"), customCode))
		if BoxInfo.getItem("HasHDMI-CEC") and config.hdmicec.enabled.value:
			info.append("")
			address = config.hdmicec.fixed_physical_address.value if config.hdmicec.fixed_physical_address.value != "0.0.0.0" else _("N/A")
			info.append(formatLine("P1", _("HDMI-CEC address"), address))
		info.append("")
		info.append(formatLine("S", _("Driver and kernel information")))
		if self.extraSpacing:
			info.append("")
		info.append(formatLine("P1", _("Drivers version"), formatDate(BoxInfo.getItem("driversdate"))))
		info.append(formatLine("P1", _("Kernel version"), BoxInfo.getItem("kernel")))
		deviceId = fileReadLine("/proc/device-tree/amlogic-dt-id", source=MODULE_NAME)
		if deviceId:
			info.append(formatLine("P1", _("Device id"), deviceId))
		givenId = fileReadLine("/proc/device-tree/le-dt-id", source=MODULE_NAME)
		if givenId:
			info.append(formatLine("P1", _("Given device id"), givenId))
		if BoxInfo.getItem("HiSilicon"):
			info.append("")
			info.append(formatLine("S", _("HiSilicon specific information")))
			if self.extraSpacing:
				info.append("")
			process = Popen(("/usr/bin/opkg", "list-installed"), stdout=PIPE, stderr=PIPE, universal_newlines=True)
			stdout, stderr = process.communicate()
			if process.returncode == 0:
				missing = True
				packageList = stdout.split("\n")
				revision = findPackageRevision("grab", packageList)
				if revision and revision != "r0":
					info.append(formatLine("P1", _("Grab"), revision))
					missing = False
				revision = findPackageRevision("hihalt", packageList)
				if revision:
					info.append(formatLine("P1", _("Halt"), revision))
					missing = False
				revision = findPackageRevision("libs", packageList)
				if revision:
					info.append(formatLine("P1", _("Libs"), revision))
					missing = False
				revision = findPackageRevision("partitions", packageList)
				if revision:
					info.append(formatLine("P1", _("Partitions"), revision))
					missing = False
				revision = findPackageRevision("reader", packageList)
				if revision:
					info.append(formatLine("P1", _("Reader"), revision))
					missing = False
				revision = findPackageRevision("showiframe", packageList)
				if revision:
					info.append(formatLine("P1", _("Showiframe"), revision))
					missing = False
				if missing:
					info.append(formatLine("P1", _("HiSilicon specific information not found.")))
			else:
				info.append(formatLine("P1", _("Package information currently not available!")))
		info.append("")
		info.append(formatLine("S", _("Tuner information")))
		if self.extraSpacing:
			info.append("")
		for count, nim in enumerate(nimmanager.nimListCompressed()):
			tuner, type = (x.strip() for x in nim.split(":", 1))
			info.append(formatLine("P1", tuner, type))
		info.append("")
		info.append(formatLine("S", _("Storage / Drive information")))
		if self.extraSpacing:
			info.append("")
		stat = statvfs("/")
		diskSize = stat.f_blocks * stat.f_frsize
		info.append(formatLine("P1", _("Internal flash"), f"{scaleNumber(diskSize)}  ({scaleNumber(diskSize, 'Iec')})"))
		# hddList = storageManager.HDDList()
		hddList = harddiskmanager.HDDList()
		if hddList:
			for hdd in hddList:
				hdd = hdd[1]
				diskSize = hdd.diskSize() * 1000000
				info.append(formatLine("P1", hdd.model(), f"{scaleNumber(diskSize)}  ({scaleNumber(diskSize, 'Iec')})"))
		else:
			info.append(formatLine("H", _("No hard disks detected.")))
		info.append("")
		info.append(formatLine("S", _("Network information")))
		if self.extraSpacing:
			info.append("")
		for x in about.GetIPsFromNetworkInterfaces():
			info.append(formatLine("P1", x[0], x[1]))
		info.append("")
		info.append(formatLine("S", _("Uptime"), about.getBoxUptime()))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Receiver Information"


class ServiceInformation(InformationBase):
	def __init__(self, session, serviceRef=None):
		InformationBase.__init__(self, session)
		self.baseTitle = _("Service Information")
		self.setTitle(self.baseTitle)
		self.skinName.insert(0, "ServiceInformation")
		self.serviceRef = serviceRef
		self["key_menu"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["serviceActions"] = HelpableActionMap(self, ["MenuActions", "ColorActions", "NavigationActions"], {
			"menu": (self.showServiceMenu, _("Show selection for service information screen")),
			"yellow": (self.previousService, _("Show previous service information screen")),
			"blue": (self.nextService, _("Show next service information screen")),
			"left": (self.previousService, _("Show previous service information screen")),
			"right": (self.nextService, _("Show next service information screen"))
		}, prio=0, description=_("Service Information Actions"))
		self.serviceCommands = [
			(_("Service and PID information"), _("Service & PID"), self.showServiceInformation),
			(_("Transponder information"), _("Transponder"), self.showTransponderInformation),
			(_("ECM information"), _("ECM"), self.showECMInformation)
		]
		self.serviceCommandsMax = len(self.serviceCommands)
		self.info = None
		if serviceRef:
			self.serviceCommandsIndex = 1
		else:
			self.eventTracker = ServiceEventTracker(screen=self, eventmap={iPlayableService.evEnd: self.fetchInformationDelayed})
			self.serviceCommandsIndex = 0

	def getServiceTransponderData(self):
		self.frontendInfo = None
		self.serviceInfo = None
		self.transponderInfo = None
		self.service = None
		playServiceRef = self.session.nav.getCurrentlyPlayingServiceReference()
		if playServiceRef:
			self.serviceName = ServiceReference(playServiceRef).getServiceName()
			self.serviceReference = playServiceRef.toString()
			self.serviceReferenceType = playServiceRef.type
		else:
			self.serviceName = _("N/A")
			self.serviceReference = _("N/A")
			self.serviceReferenceType = 0
		if self.serviceRef:  # and not (playServiceRef and playServiceRef == self.serviceRef):
			self.serviceName = ServiceReference(self.serviceRef).getServiceName()
			self.transponderInfo = eServiceCenter.getInstance().info(self.serviceRef).getInfoObject(self.serviceRef, iServiceInformation.sTransponderData)  # Note that info is a iStaticServiceInformation not a iServiceInformation.
			self["key_menu"].setText("")
			self["serviceActions"].setEnabled(False)
			self.serviceCommandsIndex = 1
		else:
			self.service = self.session.nav.getCurrentService()
			if self.service:
				self.serviceInfo = self.service.info()
				self.frontendInfo = self.service.frontendInfo()
				if self.frontendInfo and not self.frontendInfo.getAll(True):
					self.frontendInfo = None
					serviceRef = playServiceRef
					self.transponderInfo = serviceRef and eServiceCenter.getInstance().info(serviceRef).getInfoObject(serviceRef, iServiceInformation.sTransponderData)
			self["key_menu"].setText(_("MENU"))
			self["serviceActions"].setEnabled(True)

	def showServiceMenu(self):
		def showServiceMenuCallBack(selectedIndex):
			if isinstance(selectedIndex, int):
				self.serviceCommandsIndex = selectedIndex
				self.displayInformation()
				self.informationTimer.start(25)

		choices = [(serviceCommand[0], index) for index, serviceCommand in enumerate(self.serviceCommands)]
		self.session.openWithCallback(showServiceMenuCallBack, MessageBox, text=_("Select service information to view:"), list=choices, windowTitle=self.baseTitle)

	def previousService(self):
		self.serviceCommandsIndex = (self.serviceCommandsIndex - 1) % self.serviceCommandsMax
		self.displayInformation()
		self.informationTimer.start(25)

	def nextService(self):
		self.serviceCommandsIndex = (self.serviceCommandsIndex + 1) % self.serviceCommandsMax
		self.displayInformation()
		self.informationTimer.start(25)

	def fetchInformation(self):
		self.informationTimer.stop()
		self.getServiceTransponderData()
		name, label, method = self.serviceCommands[self.serviceCommandsIndex]
		self.info = method()
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def fetchInformationDelayed(self):  # This allows the newly selected service to stabilize before updating the service data.
		self.informationTimer.startLongTimer(3)

	def refreshInformation(self):
		self.getServiceTransponderData()
		InformationBase.refreshInformation(self)

	def displayInformation(self):
		name, label, method = self.serviceCommands[self.serviceCommandsIndex]
		self.setTitle(f"{self.baseTitle}: {label}")
		if self["key_menu"].getText():
			self["key_yellow"].setText(self.serviceCommands[(self.serviceCommandsIndex - 1) % self.serviceCommandsMax][1])
			self["key_blue"].setText(self.serviceCommands[(self.serviceCommandsIndex + 1) % self.serviceCommandsMax][1])
		else:
			self["key_yellow"].setText("")
			self["key_blue"].setText("")
		info = [_("Retrieving '%s' information, please wait...") % name] if self.info is None else self.info
		if info == [""]:
			info = [_("There is no information to show for '%s'.") % name]
		self["information"].setText("\n".join(info))
		self.frontendInfo = None
		self.serviceInfo = None
		self.transponderInfo = None
		self.service = None

	def showServiceInformation(self):
		def formatHex(value):
			return f"0x{value:04X}  ({value})" if value and isinstance(value, int) else ""

		def getServiceInfoValue(item):
			if self.serviceInfo:
				value = self.serviceInfo.getInfo(item)
				if value == -2:
					value = self.serviceInfo.getInfoString(item)
				elif value == -1:
					value = _("N/A")
			else:
				value = ""
			return value

		def getNamespace(value):
			if isinstance(value, str):
				namespace = f"{_('N/A')}  -  {_('N/A')}"
			else:
				namespace = f"{value & 0xFFFFFFFF:08X}"
				if namespace.startswith("EEEE"):
					namespace = f"{namespace}  -  DVB-T"
				elif namespace.startswith("FFFF"):
					namespace = f"{namespace}  -  DVB-C"
				else:
					position = int(namespace[:4], 16)
					if position > 1800:
						position = 3600 - position
						alignment = _("W")
					else:
						alignment = _("E")
					namespace = f"{namespace}  -  {float(position) / 10.0}\u00B0{alignment}"
			return namespace

		def getSubtitleList():  # IanSav: If we know the current subtitle then we should flag it as "(Current)".
			subtitleTypes = {  # This should be in SystemInfo maybe as a BoxInfo variable.
				0: _("Unknown"),
				1: _("Embedded"),
				2: _("SSA file"),
				3: _("ASS file"),
				4: _("SRT file"),
				5: _("VOB file"),
				6: _("PGS file"),
				7: "WebVTT",
			}
			subtitleSelected = self.service and self.service.subtitle().getCachedSubtitle()
			if subtitleSelected:
				subtitleSelected = subtitleSelected[:3]
			subtitle = self.service and self.service.subtitle()
			subList = subtitle and subtitle.getSubtitleList() or []
			for subtitle in subList:
				print(subtitle)
				indent = "P1F0" if subtitle[:3] == subtitleSelected else "P1"
				subtitleLang = subtitle[4]
				if subtitle[0] == 0:  # DVB PID.
					info.append(formatLine(indent, _("DVB Subtitles PID & Language"), f"{formatHex(subtitle[1])}  -  {subtitleLang}"))
				elif subtitle[0] == 1:  # Teletext.
					info.append(formatLine(indent, _("TXT Subtitles page & Language"), f"0x0{subtitle[3] or 8:X}{subtitle[2]:02X}  -  {subtitleLang}"))
				elif subtitle[0] == 2:  # File.
					subtitleDesc = subtitleTypes.get(subtitle[2], f"{_('Unknown')}: {subtitle[2]}")
					info.append(formatLine(indent, _("Other Subtitles & Language"), f"{subtitle[1] + 1}  -  {subtitleDesc}  -  {subtitleLang}"))

		info = []
		info.append(formatLine("H", _("Service and PID information for '%s'") % self.serviceName))
		info.append("")
		if self.serviceInfo:
			from Components.Converter.PliExtraInfo import codec_data  # This should be in SystemInfo maybe as a BoxInfo variable.
			videoData = []
			videoData.append(codec_data.get(self.serviceInfo.getInfo(iServiceInformation.sVideoType), _("N/A")))
			width = self.serviceInfo.getInfo(iServiceInformation.sVideoWidth)
			height = self.serviceInfo.getInfo(iServiceInformation.sVideoHeight)
			if width > 0 and height > 0:
				videoData.append(f"{width}x{height}")
				videoData.append(f"{(self.serviceInfo.getInfo(iServiceInformation.sFrameRate) + 500) // 1000}{('i', 'p', '')[self.serviceInfo.getInfo(iServiceInformation.sProgressive)]}")
				videoData.append(f"[{'4:3' if getServiceInfoValue(iServiceInformation.sAspect) in (1, 2, 5, 6, 9, 0xA, 0xD, 0xE) else '16:9'}]")  # This should be in SystemInfo maybe as a BoxInfo variable.
			gamma = ("SDR", "HDR", "HDR10", "HLG", "")[self.serviceInfo.getInfo(iServiceInformation.sGamma)]  # This should be in SystemInfo maybe as a BoxInfo variable.
			if gamma:
				videoData.append(gamma)
			videoData = "  -  ".join(videoData)
		else:
			videoData = _("Unknown")
		if "%3a//" in self.serviceReference and self.serviceReferenceType not in (1, 257, 4098, 4114):  # IPTV 4097 5001, no PIDs shown.
			info.append(formatLine("P1", _("Video Codec, Size & Format"), videoData))
			info.append(formatLine("P1", _("Service reference"), ":".join(self.serviceReference.split(":")[:9])))
			info.append(formatLine("P1", _("URL"), self.serviceReference.split(":")[10].replace("%3a", ":")))
			getSubtitleList()  # IanSav: This wasn't activated to be used!
		else:
			if ":/" in self.serviceReference:  # mp4 videos, DVB-S-T recording.
				info.append(formatLine("P1", _("Video Codec, Size & Format"), videoData))
				info.append(formatLine("P1", _("Service reference"), ":".join(self.serviceReference.split(":")[:9])))
				info.append(formatLine("P1", _("Filename"), self.serviceReference.split(":")[10]))
			else:  # fallback, movistartv, live DVB-S-T.
				info.append(formatLine("P1", _("Provider"), getServiceInfoValue(iServiceInformation.sProvider)))
				info.append(formatLine("P1", _("Video Codec, Size & Format"), videoData))
				if "%3a//" in self.serviceReference:  # fallback, movistartv.
					info.append(formatLine("P1", _("Service reference"), ":".join(self.serviceReference.split(":")[:9])))
					info.append(formatLine("P1", _("URL"), self.serviceReference.split(":")[10].replace("%3a", ":")))
				else:  # Live DVB-S-T
					info.append(formatLine("P1", _("Service reference"), self.serviceReference))
			info.append(formatLine("P1", _("Namespace & Orbital position"), getNamespace(getServiceInfoValue(iServiceInformation.sNamespace))))
			info.append(formatLine("P1", _("Service ID (SID)"), formatHex(getServiceInfoValue(iServiceInformation.sSID))))
			info.append(formatLine("P1", _("Transport Stream ID (TSID)"), formatHex(getServiceInfoValue(iServiceInformation.sTSID))))
			info.append(formatLine("P1", _("Original Network ID (ONID)"), formatHex(getServiceInfoValue(iServiceInformation.sONID))))
			info.append(formatLine("P1", _("Video PID"), formatHex(getServiceInfoValue(iServiceInformation.sVideoPID))))
			audio = self.service and self.service.audioTracks()
			numberOfTracks = audio and audio.getNumberOfTracks()
			if numberOfTracks:
				for index in range(numberOfTracks):
					audioPID = audio.getTrackInfo(index).getPID()
					audioDesc = audio.getTrackInfo(index).getDescription()
					audioLang = audio.getTrackInfo(index).getLanguage() or _("Undefined")
					audioPIDValue = _("N/A") if getServiceInfoValue(iServiceInformation.sAudioPID) == "N/A" else formatHex(audioPID)
					indent = "P1F0" if numberOfTracks > 1 and audio.getCurrentTrack() == index else "P1"
					info.append(formatLine(indent, _("Audio PID%s, Codec & Language") % (f" {index + 1}" if numberOfTracks > 1 else ""), f"{audioPIDValue}  -  {audioDesc}  -  {audioLang}"))
			else:
				info.append(formatLine("P1", _("Audio PID"), _("N/A")))
			info.append(formatLine("P1", _("PCR PID"), formatHex(getServiceInfoValue(iServiceInformation.sPCRPID))))
			info.append(formatLine("P1", _("PMT PID"), formatHex(getServiceInfoValue(iServiceInformation.sPMTPID))))
			info.append(formatLine("P1", _("TXT PID"), formatHex(getServiceInfoValue(iServiceInformation.sTXTPID))))
			getSubtitleList()
		return info

	def showTransponderInformation(self):
		def getValue(key, default):
			valueLive = frontendLive.get(key, default)
			valueConfig = frontendConfig.get(key, default)
			return valueLive if valueLive == valueConfig else f"{valueLive}  ({valueConfig})"

		def getDVBCFrequencyValue():
			valueLive = frontendLive.get("frequency", 0) / 1000.0
			valueConfig = frontendConfig.get("frequency", 0) / 1000.0
			return f"{valueLive:.3f} {mhz}" if valueLive == valueConfig else f"{valueLive:.3f} {mhz}  ({valueConfig:.3f} {mhz})"

		def getSymbolRateValue():
			valueLive = frontendLive.get("symbol_rate", 0) // 1000
			valueConfig = frontendConfig.get("symbol_rate", 0) // 1000
			return f"{valueLive} {_('KSymb/s')}" if valueLive == valueConfig else f"{valueLive} {_('KSymb/s')}  ({valueConfig} {_('KSymb/s')})"

		def getDVBSFrequencyValue():
			valueLive = frontendLive.get("frequency", 0) // 1000
			valueConfig = frontendConfig.get("frequency", 0) // 1000
			return f"{valueLive} {mhz}" if valueLive == valueConfig else f"{valueLive} {mhz}  ({valueConfig} {mhz})"

		def getInputStreamID():
			valueLive = frontendLive.get("is_id", -1)
			if valueLive == -1:
				valueLive = na
			valueConfig = frontendConfig.get("is_id", -1)
			if valueConfig == -1:
				valueConfig = na
			return valueLive if valueLive == valueConfig else f"{valueLive}  ({valueConfig})"

		def getFrequencyValue():
			valueLive = frontendLive.get("frequency", 0) / 1000000.0
			valueConfig = frontendConfig.get("frequency", 0) / 1000000.0
			return f"{valueLive:.3f} {mhz}" if valueLive == valueConfig else f"{valueLive:.3f} {mhz}  ({valueConfig:.3f} {mhz})"

		info = []
		info.append(formatLine("H", _("Transponder information for '%s'") % self.serviceName))
		info.append("")
		if self.frontendInfo:
			frontendLive = self.frontendInfo and self.frontendInfo.getAll(False)
			frontendConfig = self.frontendInfo and self.frontendInfo.getAll(True)
		else:
			frontendLive = self.transponderInfo
			frontendConfig = self.transponderInfo
		if frontendLive and len(frontendLive) and frontendConfig and len(frontendConfig):
			tunerType = frontendLive["tuner_type"]
			frontendLive = ConvertToHumanReadable(frontendLive)
			frontendConfig = ConvertToHumanReadable(frontendConfig)
			na = _("N/A")
			mhz = _("MHz")
			if not self.transponderInfo:
				info.append(formatLine("P1", _("NIM"), f"{chr(ord('A') + frontendLive.get('tuner_number', 0))}"))
			info.append(formatLine("P1", _("Type"), f"{frontendLive.get('tuner_type', na)}  [{tunerType}]"))
			if tunerType == "DVB-C":
				info.append(formatLine("P1", _("Modulation"), getValue("modulation", na)))
				info.append(formatLine("P1", _("Frequency"), getDVBCFrequencyValue()))
				info.append(formatLine("P1", _("Symbol rate"), getSymbolRateValue()))
				info.append(formatLine("P1", _("Forward Error Correction (FEC)"), getValue("fec_inner", na)))
				info.append(formatLine("P1", _("Inversion"), getValue("inversion", na)))
			elif tunerType == "DVB-S":
				info.append(formatLine("P1", _("System"), getValue("system", na)))
				info.append(formatLine("P1", _("Modulation"), getValue("modulation", na)))
				info.append(formatLine("P1", _("Orbital position"), getValue("orbital_position", na)))
				info.append(formatLine("P1", _("Frequency"), getDVBSFrequencyValue()))
				info.append(formatLine("P1", _("Polarization"), getValue("polarization", na)))
				info.append(formatLine("P1", _("Symbol rate"), getSymbolRateValue()))
				info.append(formatLine("P1", _("Forward Error Correction (FEC)"), getValue("fec_inner", na)))
				info.append(formatLine("P1", _("Inversion"), getValue("inversion", na)))
				info.append(formatLine("P1", _("Pilot"), getValue("pilot", na)))
				info.append(formatLine("P1", _("Roll-off"), getValue("rolloff", na)))
				info.append(formatLine("P1", _("Input Stream ID"), getInputStreamID()))
				info.append(formatLine("P1", _("PLS Mode"), getValue("pls_mode", na)))
				info.append(formatLine("P1", _("PLS Code"), getValue("pls_code", 0)))
				valueLive = frontendLive.get("t2mi_plp_id", -1)
				valueConfig = frontendConfig.get("t2mi_plp_id", -1)
				if valueLive != -1 or valueConfig != -1:
					info.append(formatLine("P1", _("T2MI PLP ID"), f"{valueLive}" if valueLive == valueConfig else f"{valueLive}  ({valueConfig})"))
				valueLive = None if frontendLive.get("t2mi_plp_id", -1) == -1 else frontendLive.get("t2mi_pid", eDVBFrontendParametersSatellite.T2MI_Default_Pid)
				valueConfig = None if frontendConfig.get("t2mi_plp_id", -1) == -1 else frontendConfig.get("t2mi_pid", eDVBFrontendParametersSatellite.T2MI_Default_Pid)
				if valueLive or valueConfig:
					info.append(formatLine("P1", _("T2MI PID"), f"{valueLive or 'None'}" if valueLive == valueConfig else f"{valueLive or 'None'}  ({valueConfig or 'None'})"))
			elif tunerType == "DVB-T":
				info.append(formatLine("P1", _("Frequency"), getFrequencyValue()))
				info.append(formatLine("P1", _("Channel"), getValue("channel", na)))
				info.append(formatLine("P1", _("Inversion"), getValue("inversion", na)))
				info.append(formatLine("P1", _("Bandwidth"), getValue("bandwidth", na)))
				info.append(formatLine("P1", _("Code rate LP"), getValue("code_rate_lp", na)))
				info.append(formatLine("P1", _("Code rate HP"), getValue("code_rate_hp", na)))
				info.append(formatLine("P1", _("Guard Interval"), getValue("guard_interval", na)))
				info.append(formatLine("P1", _("Constellation"), getValue("constellation", na)))
				info.append(formatLine("P1", _("Transmission mode"), getValue("transmission_mode", na)))
				info.append(formatLine("P1", _("Hierarchy info"), getValue("hierarchy_information", na)))
			elif tunerType == "ATSC":
				info.append(formatLine("P1", _("System"), getValue("system", na)))
				info.append(formatLine("P1", _("Modulation"), getValue("modulation", na)))
				info.append(formatLine("P1", _("Frequency"), getFrequencyValue()))
				info.append(formatLine("P1", _("Inversion"), getValue("inversion", na)))
		else:
			info.append(formatLine("M0", _("Tuner data is not available!")))
		return info

	def showECMInformation(self):
		info = []
		info.append(formatLine("H", _("ECM information for '%s'") % self.serviceName))
		info.append("")
		if self.serviceInfo:
			from Tools.GetEcmInfo import getCaidData, GetEcmInfo
			ecmData = GetEcmInfo().getEcmData()
			for caID in sorted(set(self.serviceInfo.getInfoObject(iServiceInformation.sCAIDPIDs)), key=lambda x: (x[0], x[1])):
				description = _("Undefined")
				extraInfo = ""
				provid = ""
				for caidEntry in getCaidData():
					if int(caidEntry[0], 16) <= caID[0] <= int(caidEntry[1], 16):
						description = caidEntry[2]
						break
				if caID[2]:
					if description == "Seca":
						provid = ",".join([caID[2][y:y + 4] for y in range(len(caID[2]), 30)])
					elif description == "Nagra":
						provid = caID[2][-4:]
					elif description == "Via":
						provid = caID[2][-6:]
					if provid:
						extraInfo = f" provid={provid}"
					else:
						extraInfo = f" extra={caID[2]}"
				active = f" ({_('Active')})" if caID[0] == int(ecmData[1], 16) and (caID[1] == int(ecmData[3], 16) or str(int(ecmData[2], 16)) in provid) else ""
				info.append(formatLine("P1", f"ECMPid {caID[1]:04X} ({caID[1]})", f"{caID[0]:04X}-{description}{extraInfo}{active}"))
			if len(info) == 2:
				info.append(formatLine("P1", _("No ECM PIDs available"), _("Free to Air (FTA) Service")))
		return info

	def getSummaryInformation(self):
		return "Service Information"


class StorageInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Storage / Disk Information"))
		self.skinName.insert(0, "StorageDiskInformation")
		self["information"].setText(_("Retrieving network server information, please wait..."))
		self.mountInfo = []

	def fetchInformation(self):
		self.informationTimer.stop()
		self.console.ePopen("df -mh | grep -v '^Filesystem'", self.fetchComplete)
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def fetchComplete(self, result, retVal, extraArgs=None):
		self.mountInfo = []
		previousLine = None
		for line in [x.strip() for x in result.split("\n")]:
			if "%" in line:
				if previousLine:
					line = f"{previousLine} {line}"
					previousLine = None
				if line.startswith("//"):
					line = line[::-1]
					mount, other = line.split(" %")
					percent, free, used, total, device = other.split(None, 4)
					self.mountInfo.append([device[::-1], total[::-1], used[::-1], free[::-1], f"{percent[::-1]}%", mount[::-1]])
			else:
				previousLine = line
		if isdir("/media/autofs"):
			for entry in sorted(listdir("/media/autofs")):
				path = join("/media/autofs", entry)
				keep = True
				for data in self.mountInfo:
					if data[5] == path:
						keep = False
						break
				if keep:
					self.mountInfo.append(["", 0, 0, 0, "N/A", path])
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def displayInformation(self):
		info = []
		info.append(formatLine("H", _("Storage / Disk information for %s %s") % getBoxDisplayName()))
		info.append("")
		partitions = sorted(harddiskmanager.getMountedPartitions(), key=lambda partitions: partitions.device or "")
		for partition in partitions:
			if partition.mountpoint == "/":
				info.append(formatLine("S1", "/dev/root", partition.description))
				stat = statvfs("/")
				diskSize = stat.f_blocks * stat.f_frsize
				diskFree = stat.f_bfree * stat.f_frsize
				diskUsed = diskSize - diskFree
				info.append(formatLine("P2", _("Mount point"), partition.mountpoint))
				info.append(formatLine("P2", _("Size"), f"{scaleNumber(diskSize)}  ({scaleNumber(diskSize, 'Iec')})"))
				info.append(formatLine("P2", _("Used"), f"{scaleNumber(diskUsed)}  ({scaleNumber(diskUsed, 'Iec')})"))
				info.append(formatLine("P2", _("Free"), f"{scaleNumber(diskFree)}  ({scaleNumber(diskFree, 'Iec')})"))
				break
		# hddList = storageManager.HDDList()
		hddList = harddiskmanager.HDDList()
		if hddList:
			for hdd in hddList:
				hdd = hdd[1]
				info.append("")
				info.append(formatLine("S1", hdd.getDeviceName(), hdd.bus()))
				info.append(formatLine("P2", _("Model"), hdd.model()))
				diskSize = hdd.diskSize() * 1000000
				info.append(formatLine("P2", _("Size"), f"{scaleNumber(diskSize)}  ({scaleNumber(diskSize, 'Iec')})"))
				info.append(formatLine("P2", _("Sleeping"), (_("Yes") if hdd.isSleeping() else _("No"))))
				for partition in partitions:
					if partition.device and join("/dev", partition.device).startswith(hdd.getDeviceName()):
						info.append(formatLine("P2", _("Partition"), partition.device))
						stat = statvfs(partition.mountpoint)
						diskSize = stat.f_blocks * stat.f_frsize
						diskFree = stat.f_bfree * stat.f_frsize
						diskUsed = diskSize - diskFree
						info.append(formatLine("P3", _("Mount point"), partition.mountpoint))
						info.append(formatLine("P3", _("Size"), f"{scaleNumber(diskSize)}  ({scaleNumber(diskSize, 'Iec')})"))
						info.append(formatLine("P3", _("Used"), f"{scaleNumber(diskUsed)}  ({scaleNumber(diskUsed, 'Iec')})"))
						info.append(formatLine("P3", _("Free"), f"{scaleNumber(diskFree)}  ({scaleNumber(diskFree, 'Iec')})"))
		else:
			info.append("")
			info.append(formatLine("S1", _("No storage or hard disks detected.")))
		info.append("")
		info.append(formatLine("H", f"{_('Network storage on')} {DISPLAY_BRAND} {DISPLAY_MODEL}"))
		info.append("")
		if self.mountInfo:
			count = 0
			for data in self.mountInfo:
				if count:
					info.append("")
				info.append(formatLine("S1", data[5]))
				if data[0]:
					info.append(formatLine("P2", _("Network address"), data[0]))
					info.append(formatLine("P2", _("Size"), data[1]))
					info.append(formatLine("P2", _("Used"), f"{data[2]}  ({data[4]})"))
					info.append(formatLine("P2", _("Free"), data[3]))
				else:
					info.append(formatLine("P2", _("Not currently mounted.")))
				count += 1
		else:
			info.append(formatLine("S1", _("No network storage detected.")))
		self["information"].setText("\n".join(info))


class StreamingInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Streaming Tuner Information"))
		self.skinName.insert(0, "StreamingInformation")
		self["key_yellow"] = StaticText(_("Stop Auto Refresh"))
		self["key_blue"] = StaticText()
		self["refreshActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.toggleAutoRefresh, _("Toggle auto refresh On/Off"))
		}, prio=0, description=_("Streaming Information Actions"))
		self["streamActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.stopStreams, _("Stop streams"))
		}, prio=0, description=_("Streaming Information Actions"))
		self["streamActions"].setEnabled(False)
		self.autoRefresh = True

	def toggleAutoRefresh(self):
		self.autoRefresh = not self.autoRefresh
		self["key_yellow"].setText(_("Stop Auto Refresh") if self.autoRefresh else _("Start Auto Refresh"))

	def stopStreams(self):
		if eStreamServer.getInstance().getConnectedClients():
			eStreamServer.getInstance().stopStream()
		if eRTSPStreamServer.getInstance().getConnectedClients():
			eRTSPStreamServer.getInstance().stopStream()

	def displayInformation(self):
		info = []
		info.append(formatLine("H", _("Streaming tuner information for %s %s") % getBoxDisplayName()))
		info.append("")
		clientList = eStreamServer.getInstance().getConnectedClients() + eRTSPStreamServer.getInstance().getConnectedClients()
		if clientList:
			self["key_blue"].setText(_("Stop Streams"))
			self["streamActions"].setEnabled(True)
			for count, client in enumerate(clientList):
				# print("[Information] DEBUG: Client data '%s'." % str(client))
				if count:
					info.append("")
				info.append(formatLine("S", f"{_('Client')}  -  {count + 1}"))
				info.append(formatLine("P1", _("Service reference"), client[1]))
				info.append(formatLine("P1", _("Service name"), ServiceReference(client[1]).getServiceName() or _("Unknown service!")))
				info.append(formatLine("P1", _("IP address"), client[0][7:] if client[0].startswith("::ffff:") else client[0]))
				info.append(formatLine("P1", _("Transcoding"), _("Yes") if client[2] else _("No")))
		else:
			self["key_blue"].setText("")
			self["streamActions"].setEnabled(False)
			info.append(formatLine("P1", _("No tuners are currently streaming.")))
		self["information"].setText("\n".join(info))
		if self.autoRefresh:
			self.informationTimer.start(AUTO_REFRESH_TIME)

	def getSummaryInformation(self):
		return "Streaming Tuner Information"


class SystemInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.baseTitle = _("System Information")
		self.setTitle(self.baseTitle)
		self.skinName.insert(0, "SystemInformation")
		self["key_menu"] = StaticText(_("MENU"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["systemActions"] = HelpableActionMap(self, ["MenuActions", "ColorActions", "NavigationActions"], {
			"menu": (self.showSystemMenu, _("Show selection for system information screen")),
			"yellow": (self.previousSystem, _("Show previous system information screen")),
			"blue": (self.nextSystem, _("Show next system information screen")),
			"left": (self.previousSystem, _("Show previous system information screen")),
			"right": (self.nextSystem, _("Show next system information screen"))
		}, prio=0, description=_("System Information Actions"))
		self.systemCommands = [
			("CPU", None, "/proc/cpuinfo"),
			("Top Processes", ("/usr/bin/top", "/usr/bin/top", "-b", "-n", "1"), None),
			("Current Processes", ("/bin/ps", "/bin/ps", "-l"), None),
			("Kernel Modules", None, "/proc/modules"),
			("Kernel Messages", ("/bin/dmesg", "/bin/dmesg"), None),
			("System Messages", None, "/var/volatile/log/messages"),
			("Network Interfaces", ("/sbin/ifconfig", "/sbin/ifconfig"), None),
			("Disk Usage", ("/bin/df", "/bin/df", "-h"), None),
			("Mounted Volumes", ("/bin/mount", "/bin/mount"), None),
			("Partition Table", None, "/proc/partitions")
		]

		edidPath = eAVControl.getInstance().getEDIDPath()
		if edidPath:
			self.systemCommands.append(("EDID", ("/usr/bin/edid-decode", "/usr/bin/edid-decode", edidPath), None))
		self.systemCommandsIndex = 0
		self.systemCommandsMax = len(self.systemCommands)
		self.info = None

	def showSystemMenu(self):
		def showSystemMenuCallBack(selectedIndex):
			if isinstance(selectedIndex, int):
				self.systemCommandsIndex = selectedIndex
				self.displayInformation()
				self.informationTimer.start(25)

		choices = [(systemCommand[0], index) for index, systemCommand in enumerate(self.systemCommands)]
		self.session.openWithCallback(showSystemMenuCallBack, MessageBox, text=_("Select system information to view:"), list=choices, windowTitle=self.baseTitle)

	def previousSystem(self):
		self.systemCommandsIndex = (self.systemCommandsIndex - 1) % self.systemCommandsMax
		self.displayInformation()
		self.informationTimer.start(25)

	def nextSystem(self):
		self.systemCommandsIndex = (self.systemCommandsIndex + 1) % self.systemCommandsMax
		self.displayInformation()
		self.informationTimer.start(25)

	def fetchInformation(self):
		def fetchInformationCallback(result, retVal, extraArgs):
			self.info = [x.rstrip() for x in result.split("\n")]
			for callback in self.onInformationUpdated:
				if callable(callback):
					callback()

		self.informationTimer.stop()
		name, command, path = self.systemCommands[self.systemCommandsIndex]
		self.info = None
		if command:
			self.console.ePopen(command, fetchInformationCallback)
		elif path:
			try:
				with open(path) as fd:
					self.info = [x.strip() for x in fd.readlines()]
			except OSError as err:
				self.info = [_("Error %d: System information file '%s' can't be read!  (%s)") % (err.errno, path, err.strerror)]
			for callback in self.onInformationUpdated:
				if callable(callback):
					callback()

	def displayInformation(self):
		name, command, path = self.systemCommands[self.systemCommandsIndex]
		self.setTitle(f"{self.baseTitle}: {name}")
		self["key_yellow"].setText(self.systemCommands[(self.systemCommandsIndex - 1) % self.systemCommandsMax][0])
		self["key_blue"].setText(self.systemCommands[(self.systemCommandsIndex + 1) % self.systemCommandsMax][0])
		info = [_("Retrieving '%s' information, please wait...") % name] if self.info is None else self.info
		if info == [""]:
			info = [_("There is no information to show for '%s'.") % name]
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "System Information"


class TranslationInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Translation Information"))
		self.skinName.insert(0, "TranslationInformation")

	def displayInformation(self):
		info = []
		info.append(formatLine("H", _("Translation information for %s %s") % getBoxDisplayName()))
		info.append("")
		translateInfo = _("TRANSLATOR_INFO")
		if translateInfo != "TRANSLATOR_INFO":
			info.append(formatLine("H", _("Translation information")))
			info.append("")
			translateInfo = translateInfo.split("\n")
			for translate in translateInfo:
				info.append(formatLine("P1", translate))
			info.append("")
		translateInfo = _("").split("\n")  # This is deliberate to dump the translation information.
		for translate in translateInfo:
			if not translate:
				continue
			translate = [x.strip() for x in translate.split(":", 1)]
			if len(translate) == 1:
				translate.append("")
			info.append(formatLine("P1", translate[0], translate[1]))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Translation Information"


class TunerInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Tuner Information"))
		self.skinName.insert(0, "TunerInformation")
		self.frontEndFields = {
			"DVB API version": "api",
			"Name": "name",
			"Frequency": "frequency",
			"Symbolrate": "symbolrate",
			"Capabilities": "capabilities",
			"Delivery Systems": "delivery"
		}
		self.broadcasts = ("DVB-S", "DVB-S2", "DVB-C", "DVB-T", "DVB-T2", "ATSC", "ISDB-T", "DTMB")
		self.tunerList = []

	def fetchInformation(self):
		self.informationTimer.stop()
		self.tunerList = []
		curIndex = -1
		for count, nim in enumerate(nimmanager.nimList()):
			tunerData = {}
			tuner, model = (x.strip() for x in nim.split(":", 1))
			tuner = tuner.strip("Tuner").strip()
			if self.tunerList and self.tunerList[curIndex]["model"] == model:
				self.tunerList[curIndex]["end"] = tuner
				continue
			curIndex += 1
			tunerData["start"] = tuner
			tunerData["end"] = tuner
			tunerData["model"] = model
			for key, value in [(x.strip(), y.strip()) for x, y in [x.split(":", 1) for x in eDVBResourceManager.getInstance().getFrontendCapabilities(count).splitlines()]]:
				if key in self.frontEndFields:
					tunerData[self.frontEndFields[key]] = value
				else:
					print(f"[Information] Note: Unexpected field '{key}' in front-end with data '{value}'!")
			if tunerData.get("delivery"):
				broadcasts = []
				for broadcast in self.broadcasts:
					if broadcast.replace("-", "") in tunerData["delivery"]:
						broadcasts.append(broadcast)
				if broadcasts:
					tunerData["broadcast"] = ", ".join(broadcasts)
			self.tunerList.append(tunerData)
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def displayInformation(self):
		def parseValues(data):
			values = {}
			for item in data.split(","):
				key, value = item.split("=", 1)
				values[key] = formatNumber(value)
			return values

		def formatNumber(number):
			number = number.strip()
			value, units = number.split(maxsplit=1) if " " in number else (number, None)
			if "." in value:
				format = "%.3f"
				value = float(value)
			else:
				format = "%d"
				value = int(value)
			return f"{format_string(format, value, grouping=True)} {units}" if units else format_string(format, value, grouping=True)

		def extractModes(data, mode):
			values = []
			if data:
				mode = f"{mode} "
				length = len(mode)
				for item in data.split(","):
					if item.startswith(mode):
						values.append(item[length:].capitalize())
			return sorted(values)

		def sortQAM(values):
			if "Auto" in values:
				values.remove("Auto")
				addAuto = True
			else:
				addAuto = False
			values = [str(x) for x in sorted([int(x) for x in values])]
			if addAuto:
				values.append("Auto")
			return values

		info = []
		info.append(formatLine("H", _("Tuner information for %s %s") % getBoxDisplayName()))
		info.append("")
		for count, tunerData in enumerate(self.tunerList):
			if count:
				info.append("")
			tuner = tunerData["start"] if tunerData["start"] == tunerData["end"] else f"{tunerData['start']} - {tunerData['end']}"
			info.append(formatLine("S", f"Tuner {tuner}"))
			if self.extraSpacing:
				info.append("")
			name = tunerData.get("name")
			if name:
				info.append(formatLine("P1", _("Name"), name))
			model = tunerData.get("model")
			if model:
				info.append(formatLine("P1", _("Type / Model"), model))
			broadcast = tunerData.get("broadcast")
			if broadcast:
				info.append(formatLine("P1", _("Broadcast systems"), broadcast))
			capabilities = tunerData.get("capabilities")
			if capabilities:
				info.append(formatLine("P1", _("Multistream"), (_("Yes") if "MULTISTREAM" in capabilities else _("No"))))
			frequency = tunerData.get("frequency")
			if frequency:
				data = parseValues(frequency)
				info.append(formatLine("P1", _("Frequency range"), f"{data['min']}  -  {data['max']}  (Step {data['stepsize']})"))
			symbolrate = tunerData.get("symbolrate")
			if symbolrate:
				data = parseValues(symbolrate)
				info.append(formatLine("P1", _("Symbol rate"), f"{data['min']}  -  {data['max']}"))
			FEC = extractModes(capabilities, "FEC")
			if FEC:
				info.append(formatLine("P1", _("FEC modes"), ", ".join(FEC)))
			QAM = sortQAM(extractModes(capabilities, "QAM"))
			if QAM:
				info.append(formatLine("P1", _("Modulation modes"), ", ".join(QAM)))
			api = tunerData.get("api")
			if api:
				info.append(formatLine("P1", _("DVB API version"), api))
		if info:
			info.append("")
		info.append(formatLine("S", _("Transcoding"), (_("Yes") if BoxInfo.getItem("transcoding") else _("No"))))
		info.append(formatLine("S", _("MultiTranscoding"), (_("Yes") if BoxInfo.getItem("multitranscoding") else _("No"))))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Tuner Information"


class TestingInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Testing Information"))
		self.skinName.insert(0, "TestingInformation")
		self.slotImages = None

	def displayInformation(self):
		html = remoteControl.getOpenWebifHTML()
		if html is None:
			html = "OpenWebif HTML file isn't available."
		self["information"].setText(html)
		# info = []
		# for index in range(1, 24):
		# 	info.append("This is test line %d." % index)
		# self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Testing Information Data"


class InformationSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self.parent = parent
		self["information"] = StaticText()
		parent.onInformationUpdated.append(self.updateSummary)
		# self.updateSummary()

	def updateSummary(self):
		self["information"].setText(self.parent.getSummaryInformation())
