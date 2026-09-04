from datetime import datetime
from glob import glob
from json import loads
from locale import format_string
from os import listdir, remove, statvfs
from os.path import basename, getmtime, isdir, isfile, join
from re import search
from subprocess import PIPE, Popen
from urllib.request import urlopen

from enigma import eAVControl, eDVBCSAEngine, eDVBFrontendParametersSatellite, eDVBResourceManager, eGetEnigmaDebugLvl, eRTSPStreamServer, eServiceCenter, eServiceReference, eStreamServer, eTimer, getDesktop, getE2Rev, getGStreamerVersionString, iFrontendInformation, iPlayableService, iServiceInformation

from ServiceReference import ServiceReference
from Components.About import about
from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.Console import Console
from Components.Harddisk import harddiskmanager
from Components.InputDevice import remoteControl
from Components.Label import Label
from Components.NetworkManager import encryptionLabels, networkManager
from Components.NimManager import nimmanager
from Components.Pixmap import Pixmap
from Components.RTLSDR import getRTLSDRChannelFrequency
from Components.ScrollLabel import ScrollLabel
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Sources.StaticText import StaticText
# from Components.Storage import storageManager
from Components.SystemInfo import BoxInfo, getBoxDisplayName, getDemodVersion
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen, ScreenSummary
from Screens.Setup import Setup
from Tools.Conversions import formatDate, scaleNumber
from Tools.Directories import SCOPE_SKINS, fileReadLine, fileReadLines, fileWriteLine, resolveFilename
from Tools.Geolocation import geolocation
from Tools.LoadPixmap import LoadPixmap
from Tools.MultiBoot import MultiBoot
from Tools.StbHardware import getBoxProc, getBoxProcType, getBoxRCType, getFPVersion, getHWSerial
from Tools.Transponder import ConvertToHumanReadable

MODULE_NAME = __name__.split(".")[-1]

DISPLAY_BRAND = BoxInfo.getItem("displaybrand")
DISPLAY_MODEL = BoxInfo.getItem("displaymodel")
MACHINE_BUILD = BoxInfo.getItem("machinebuild")
MODEL = BoxInfo.getItem("model")
BoxInfo.setItem("InformationDistributionWelcome", [_("Welcome to %s") % BoxInfo.getItem("displaydistro", "Enigma2")])

LOG_MAX_LINES = 10000  # Maximum number of log lines to be displayed on screen.
AUTO_REFRESH_TIME = 5000  # Streaming auto refresh timer (in milliseconds).


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
			"cancel": (self.keyClose, _("Close the screen")),
			"close": (self.keyCloseRecursive, _("Close the screen and exit all menus")),
			"save": (self.refreshInformation, _("Refresh the screen")),
			"ok": (self.refreshInformation, _("Refresh the screen")),
			"top": (self["information"].goTop, _("Move to first line / screen")),
			"pageUp": (self["information"].goPageUp, _("Move up a screen")),
			"up": (self["information"].goLineUp, _("Move up a line")),
			"down": (self["information"].goLineDown, _("Move down a line")),
			"pageDown": (self["information"].goPageDown, _("Move down a screen")),
			"bottom": (self["information"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Common Information Actions"))
		self.informationColors = ["H", "S", "P", "V", "M", "F"]
		self.informationColor = {
			"B": None,
			"H": 0x00FFFFFF,  # Headings.
			"S": 0x00FFFFFF,  # Subheadings.
			"P": 0x00CCCCCC,  # Prompts.
			"V": 0x00CCCCCC,  # Values.
			"M": 0x00FFFF00,  # Messages.
			"F": 0x0000FFFF  # Features.
		}
		self["information"].setText(_("Loading information, please wait..."))
		self.console = Console()
		self.extraSpacing = config.usage.informationExtraSpacing.value
		self.onInformationUpdated = [self.displayInformation]
		self.onLayoutFinish.append(self.layoutFinished)
		self.informationTimer = eTimer()
		self.informationTimer.callback.append(self.fetchInformation)
		self.informationTimer.start(25)

	def layoutFinished(self):
		colors = self["information"].getColors()
		if len(colors) == len(self.informationColors):
			for index, color in enumerate(colors):
				if colors[index]:
					self.informationColor[self.informationColors[index]] = color.argb()
		else:
			print(f"[Information] Warning: {len(colors)} colors are defined in the skin when {len(self.informationColors)} were expected!")
		self.displayInformation()

	def keyClose(self):
		self.console.killAll()
		self.close()

	def keyCloseRecursive(self):
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

	def formatLine(self, style, left, right=None):
		styleLen = len(style)
		leftStartColor = "" if styleLen > 0 and style[0] == "B" else r"\c%08X" % (self.informationColor.get(style[0], "P") if styleLen > 0 else self.informationColor["P"])
		leftEndColor = "" if leftStartColor == "" else r"\C"
		leftIndent = "    " * int(style[1]) if styleLen > 1 and style[1].isdigit() else ""
		rightStartColor = "" if styleLen > 2 and style[2] == "B" else r"\c%08X" % (self.informationColor.get(style[2], "V") if styleLen > 2 else self.informationColor["V"])
		rightEndColor = "" if rightStartColor == "" else r"\C"
		rightIndent = "    " * int(style[3]) if styleLen > 3 and style[3].isdigit() else ""
		if right is None:
			colon = "" if styleLen > 0 and style[0] in ("M", "P", "V") else ":"
			line = f"{leftIndent}{leftStartColor}{left}{colon}{leftEndColor}"
		else:
			line = f"{leftIndent}{leftStartColor}{left}:{leftEndColor}|{rightIndent}{rightStartColor}{right}{rightEndColor}"
		return line

	def displayInformation(self):
		pass

	def getSummaryInformation(self):
		pass

	def createSummary(self):
		return InformationSummary


class InformationBenchmark(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Benchmark Information"))
		self.skinName.insert(0, "InformationBenchmark")
		self.skinName.insert(1, "BenchmarkInformation")
		self.cpuTypes = []
		self.cpuMemoryClock = None
		self.cpuBenchmark = None
		self.cpuRating = None
		self.ramBenchmark = None

	def fetchInformation(self):
		def cpuBenchmarkCallback(result, retVal, extraArgs):
			def ramBenchmarkCallback(result, retVal, extraArgs):
				for line in result.split("\n"):
					if line.startswith("Copy rate:"):
						self.ramBenchmark = float([x.strip() for x in line.split(":")][1])
				for callback in self.onInformationUpdated:
					if callable(callback):
						callback()

			for line in result.split("\n"):
				if line.startswith("Memory clock speed (HZ):"):
					self.cpuMemoryClock = int([x.strip() for x in line.split(":")][1])
				if line.startswith("DMIPS:"):
					self.cpuBenchmark = int([x.strip() for x in line.split(":")][1])
				if line.startswith("CPU status:"):
					self.cpuRating = [x.strip() for x in line.split(":")][1]
			# Serialize the tests for better accuracy.
			self.console.ePopen(("/usr/bin/streambench", "/usr/bin/streambench"), ramBenchmarkCallback)
			for callback in self.onInformationUpdated:
				if callable(callback):
					callback()

		self.informationTimer.stop()
		self.cpuTypes = []
		lines = []
		lines = fileReadLines("/proc/cpuinfo", lines, source=MODULE_NAME)
		for line in lines:
			if line.startswith("model name") or line.startswith("Processor"):  # HiSilicon use the label "Processor"!
				self.cpuTypes.append([x.strip() for x in line.split(":")][1])
		# Serialize the tests for better accuracy.
		self.console.ePopen(("/usr/bin/dhry", "/usr/bin/dhry"), callback=cpuBenchmarkCallback)
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
		info.append(self.formatLine("H", _("Benchmark information for %s %s") % getBoxDisplayName()))
		info.append("")
		for index, cpu in enumerate(self.cpuTypes):
			info.append(self.formatLine("P1", _("CPU / Core %d type") % index, cpu))
		info.append("")
		info.append(self.formatLine("P1", _("CPU memory clock"), _("%d Hz") % self.cpuMemoryClock if self.cpuMemoryClock else _("Calculating clock...")))
		info.append(self.formatLine("P1", _("CPU benchmark"), _("%s DMIPS per core") % self.cpuBenchmark if self.cpuBenchmark else _("Calculating benchmark...")))
		count = len(self.cpuTypes)
		if count > 1:
			info.append(self.formatLine("P1", _("Total CPU benchmark"), _("%d DMIPS with %d cores") % (self.cpuBenchmark * count, count) if self.cpuBenchmark else _("Calculating benchmark...")))
		info.append(self.formatLine("P1", _("CPU rating"), self.cpuRating if self.cpuRating else _("Calculating rating...")))
		info.append("")
		info.append(self.formatLine("P1", _("RAM benchmark"), f"{self.ramBenchmark:.2f} MB/s copy rate" if self.ramBenchmark else _("Calculating benchmark...")))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Benchmark Information"


class InformationBuild(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Build Information"))
		self.skinName.insert(0, "InformationBuild")
		self.skinName.insert(1, "BuildInformation")

	def displayInformation(self):
		info = []
		info.append(self.formatLine("H", _("Build information for %s %s") % getBoxDisplayName()))
		info.append("")
		checksum = BoxInfo.getItem("checksumerror", False)
		if checksum:
			info.append(self.formatLine("M1", _("Error: Checksum is invalid!")))
		override = BoxInfo.getItem("overrideactive", False)
		if override:
			info.append(self.formatLine("M1", _("Warning: Overrides are currently active!")))
		if checksum or override:
			info.append("")
		for item in BoxInfo.getEnigmaInfoList():
			info.append(self.formatLine("P1", item, BoxInfo.getItem(item)))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Build Information"


class InformationCommit(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Commit Log Information"))
		self.baseTitle = _("Commit Log")
		self.skinName.insert(0, "InformationCommit")
		self.skinName.insert(1, "CommitInformation")
		self["key_menu"] = StaticText(_("MENU"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["commitActions"] = HelpableActionMap(self, ["MenuActions", "ColorActions", "NavigationActions"], {
			"menu": (self.keyShowCommitMenu, _("Show selection menu for commit logs")),
			"yellow": (self.keyPreviousCommitLog, _("Show previous commit log")),
			"blue": (self.keyNextCommitLog, _("Show next commit log")),
			"left": (self.keyPreviousCommitLog, _("Show previous commit log")),
			"right": (self.keyNextCommitLog, _("Show next commit log"))
		}, prio=0, description=_("Commit Information Actions"))
		self.commitLogs = BoxInfo.getItem("InformationCommitLogs", [("Unavailable", None)])
		self.commitLogIndex = 0
		self.commitLogMax = len(self.commitLogs)
		self.cachedCommitInfo = {}

	def keyShowCommitMenu(self):
		def keyShowCommitMenuCallBack(selectedIndex):
			if isinstance(selectedIndex, int):
				self.commitLogIndex = selectedIndex
				self.displayInformation()
				self.informationTimer.start(25)

		choices = [(commitLog[0], index) for index, commitLog in enumerate(self.commitLogs)]
		self.session.openWithCallback(keyShowCommitMenuCallBack, MessageBox, text=_("Select a repository commit log to view:"), list=choices, windowTitle=self.baseTitle)

	def keyPreviousCommitLog(self):
		self.commitLogIndex = (self.commitLogIndex - 1) % self.commitLogMax
		self.displayInformation()
		self.informationTimer.start(25)

	def keyNextCommitLog(self):
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


class InformationDebug(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Debug Log Information"))
		self.baseTitle = _("Log")
		self.skinName.insert(0, "InformationDebug")
		self.skinName.insert(1, "DebugInformation")
		self["key_menu"] = StaticText()
		self["key_info"] = StaticText(_("INFO"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["debugActions"] = HelpableActionMap(self, ["MenuActions", "InfoActions", "ColorActions", "NavigationActions"], {
			"menu": (self.keyShowLogMenu, _("Show selection menu for debug log files")),
			"info": (self.keyShowLogSettings, _("Show the Logs Settings screen")),
			"yellow": (self.keyDeleteLog, _("Delete the currently displayed log file")),
			"blue": (self.keyDeleteAllLogs, _("Delete all log files")),
			"left": (self.keyPreviousDebugLog, _("Show previous debug log file")),
			"right": (self.keyNextDebugLog, _("Show next debug log file"))
		}, prio=0, description=_("Debug Log Information Actions"))
		self["debugActions"].setEnabled(False)
		self.debugLogs = []
		self.debugLogIndex = 0
		self.debugLogMax = 0
		self.cachedDebugInfo = {}

	def keyShowLogMenu(self):
		def keyShowLogMenuCallBack(selectedIndex):
			if isinstance(selectedIndex, int):
				self.debugLogIndex = selectedIndex
				self.displayInformation()
				self.informationTimer.start(25)

		choices = [(_("Log file: '%s'  (%s)") % (debugLog[0], debugLog[1]), index) for index, debugLog in enumerate(self.debugLogs)]
		self.session.openWithCallback(keyShowLogMenuCallBack, MessageBox, text=_("Select a debug log file to view:"), list=choices, default=self.debugLogIndex, windowTitle=self.baseTitle)

	def keyShowLogSettings(self):
		self.setTitle(_("Debug Log Information"))
		self.session.openWithCallback(self.showLogSettingsCallback, Setup, "Logs")

	def showLogSettingsCallback(self, *retVal):
		if retVal and retVal[0]:
			self.close(True)

	def keyDeleteLog(self):
		def keyDeleteLogCallback(answer):
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

		name, sequence, path = self.debugLogs[self.debugLogIndex]
		self.session.openWithCallback(keyDeleteLogCallback, MessageBox, "%s\n\n%s" % (_("Log file: '%s'  (%s)") % (name, sequence), _("Do you want to delete this log file?")), default=False)

	def keyDeleteAllLogs(self):
		def keyDeleteAllLogsCallback(answer):
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

		self.session.openWithCallback(keyDeleteAllLogsCallback, MessageBox, _("Do you want to delete all the log files?"), default=False)

	def keyPreviousDebugLog(self):
		self.debugLogIndex = (self.debugLogIndex - 1) % self.debugLogMax
		self.displayInformation()
		self.informationTimer.start(25)

	def keyNextDebugLog(self):
		self.debugLogIndex = (self.debugLogIndex + 1) % self.debugLogMax
		self.displayInformation()
		self.informationTimer.start(25)

	def fetchInformation(self):
		def findLogFiles():
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

		self.informationTimer.stop()
		if not self.debugLogs:
			self.debugLogs = findLogFiles()
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
			self.cachedDebugInfo[name] = f"0,{_("No log files found so debug logs are unavailable!")}"
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

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


class InformationDistribution(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.displayDistro = BoxInfo.getItem("displaydistro", "Enigma2")
		self.setTitle(_("%s Information") % self.displayDistro)
		self.skinName.insert(0, "InformationDistribution")
		self.skinName.insert(1, "DistributionInformation")
		self["key_info"] = StaticText(_("INFO"))
		self["key_yellow"] = StaticText(_("Commit Logs"))
		self["key_blue"] = StaticText(_("Translation"))
		self["receiverActions"] = HelpableActionMap(self, ["InfoActions", "ColorActions"], {
			"info": (self.keyShowBuild, _("Show build information")),
			"yellow": (self.keyShowCommitLogs, _("Show commit log information")),
			"blue": (self.keyShowTranslation, _("Show translation information"))
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

	def keyShowBuild(self):
		self.session.openWithCallback(self.informationWindowClosed, InformationBuild)

	def keyShowCommitLogs(self):
		self.session.openWithCallback(self.informationWindowClosed, InformationCommit)

	def keyShowTranslation(self):
		self.session.openWithCallback(self.informationWindowClosed, InformationTranslation)

	def displayInformation(self):
		info = []
		info.append(self.formatLine("H", _("Distribution '%s' information for %s %s") % (self.displayDistro, DISPLAY_BRAND, DISPLAY_MODEL)))
		info.append("")
		if self.imageMessage:
			for line in self.imageMessage:
				info.append(self.formatLine("M", line))
			info.append("")
		info.append(self.formatLine("S", _("System information")))
		if self.extraSpacing:
			info.append("")
		info.append(self.formatLine("P1", _("Info file checksum"), _("Invalid") if BoxInfo.getItem("checksumerror", False) else _("Valid")))
		override = BoxInfo.getItem("overrideactive", False)
		if override:
			info.append(self.formatLine("P1", _("Info file override"), _("Defined / Active")))
		info.append(self.formatLine("P1", _("Distribution version"), BoxInfo.getItem("imgversion")))
		info.append(self.formatLine("P1", _("Distribution revision"), formatDate(BoxInfo.getItem("imgrevision"))))
		info.append(self.formatLine("P1", _("Distribution language"), BoxInfo.getItem("imglanguage")))
		info.append(self.formatLine("P1", _("OEM model"), BoxInfo.getItem("platform", _("Unknown"))))
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
			info.append(self.formatLine("P1", _("Hardware MultiBoot device"), device))
			info.append(self.formatLine("P1", _("MultiBoot startup file"), MultiBoot.getStartupFile()))
		if bootCode:
			info.append(self.formatLine("P1", _("MultiBoot boot mode"), MultiBoot.getBootCodeDescription(bootCode)))
		info.append(self.formatLine("P1", _("Software MultiBoot"), _("Yes") if BoxInfo.getItem("multiboot", False) else _("No")))
		if BoxInfo.getItem("HasKexecMultiboot"):
			info.append(self.formatLine("P1", _("Vu+ MultiBoot"), _("Yes")))
		info.append(self.formatLine("P1", _("Flash type"), about.getFlashType()))
		xResolution = getDesktop(0).size().width()
		yResolution = getDesktop(0).size().height()
		info.append(self.formatLine("P1", _("Skin & Resolution"), f"{config.skin.primary_skin.value.split("/")[0]}  ({self.resolutions.get(yResolution, "Unknown")}  -  {xResolution} x {yResolution})"))
		info.append("")
		info.append(self.formatLine("S", _("Enigma2 information")))
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
		info.append(self.formatLine("P1", _("%s version") % "Enigma2", enigmaVersion))
		info.append(self.formatLine("P1", _("Enigma2 revision"), getE2Rev()))
		compileDate = str(BoxInfo.getItem("compiledate"))
		info.append(self.formatLine("P1", _("Last update"), formatDate(f"{compileDate[:4]}{compileDate[4:6]}{compileDate[6:]}")))
		info.append(self.formatLine("P1", _("Last flash"), formatDate(about.getFlashDateString())))
		info.append(self.formatLine("P1", _("Enigma2 (re)starts"), config.misc.startCounter.value))
		info.append(self.formatLine("P1", _("Enigma2 debug level"), eGetEnigmaDebugLvl()))
		mediaService = BoxInfo.getItem("mediaservice")
		if mediaService:
			info.append(self.formatLine("P1", _("Media service"), mediaService.replace("enigma2-plugin-systemplugins-", "")))
		if eDVBCSAEngine.isAvailable():
			info.append(self.formatLine("P1", _("Software descrambling"), _("Available")))
		info.append("")
		info.append(self.formatLine("S", _("Build information")))
		if self.extraSpacing:
			info.append("")
		info.append(self.formatLine("P1", _("Distribution"), BoxInfo.getItem("displaydistro")))
		info.append(self.formatLine("P1", _("Distribution build"), formatDate(BoxInfo.getItem("imagebuild"))))
		info.append(self.formatLine("P1", _("Distribution build date"), formatDate(about.getBuildDateString())))
		info.append(self.formatLine("P1", _("Distribution architecture"), BoxInfo.getItem("architecture")))
		if BoxInfo.getItem("imagedir"):
			info.append(self.formatLine("P1", _("Distribution folder"), BoxInfo.getItem("imagedir")))
		if BoxInfo.getItem("imagefs"):
			info.append(self.formatLine("P1", _("Distribution file system"), BoxInfo.getItem("imagefs").strip()))
		upxVersion = BoxInfo.getItem("upx")
		info.append(self.formatLine("P1", _("File compression"), f"{_("Enabled")} / {_("%s version") % "UPX"} {upxVersion}" if upxVersion else _("Disabled")))
		info.append(self.formatLine("P1", _("Feed URL"), BoxInfo.getItem("feedsurl")))
		info.append(self.formatLine("P1", _("Compiled by"), BoxInfo.getItem("developername")))
		info.append("")
		info.append(self.formatLine("S", _("Software information")))
		if self.extraSpacing:
			info.append("")
		versions = [
			("GCC", about.getGccVersion()),
			("Glibc", about.getGlibcVersion()),
			("OpenSSL", about.getVersionFromOpkg("openssl")),
			("Python", about.getPythonVersionString()),
			("Rust", BoxInfo.getItem("rust")),
			("Samba", about.getVersionFromOpkg("samba")),
			("GStreamer", getGStreamerVersionString().replace("GStreamer ", "")),
			("FFmpeg", about.getVersionFromOpkg("ffmpeg"))
		]
		if eDVBCSAEngine.isAvailable():
			libName = eDVBCSAEngine.getLibraryName()
			libVersion = eDVBCSAEngine.getLibraryVersion()
			if libName and libVersion:
				libName = libName.capitalize()
				versions.append((libName, libVersion))
		for version in versions:
			info.append(self.formatLine("P1", _("%s version") % version[0], version[1]))
		bootId = fileReadLine("/proc/sys/kernel/random/boot_id", source=MODULE_NAME)
		if bootId:
			info.append(self.formatLine("P1", _("Boot ID"), bootId))
		uuId = fileReadLine("/proc/sys/kernel/random/uuid", source=MODULE_NAME)
		if uuId:
			info.append(self.formatLine("P1", _("UUID"), uuId))
		info.append("")
		info.append(self.formatLine("S", _("Boot information")))
		if self.extraSpacing:
			info.append("")
		if BoxInfo.getItem("mtdbootfs"):
			info.append(self.formatLine("P1", _("MTD boot"), BoxInfo.getItem("mtdbootfs")))
		if BoxInfo.getItem("mtdkernel"):
			info.append(self.formatLine("P1", _("MTD kernel"), BoxInfo.getItem("mtdkernel")))
		if BoxInfo.getItem("mtdrootfs"):
			info.append(self.formatLine("P1", _("MTD root"), BoxInfo.getItem("mtdrootfs")))
		if BoxInfo.getItem("kernelfile"):
			info.append(self.formatLine("P1", _("Kernel file"), BoxInfo.getItem("kernelfile")))
		if BoxInfo.getItem("rootfile"):
			info.append(self.formatLine("P1", _("Root file"), BoxInfo.getItem("rootfile")))
		if BoxInfo.getItem("mkubifs"):
			info.append(self.formatLine("P1", _("MKUBIFS"), BoxInfo.getItem("mkubifs")))
		if BoxInfo.getItem("ubinize"):
			info.append(self.formatLine("P1", _("UBINIZE"), BoxInfo.getItem("ubinize")))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return f"{self.displayDistro} Information"


class InformationGeolocation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Geolocation Information"))
		self.skinName.insert(0, "InformationGeolocation")
		self.skinName.insert(1, "GeolocationInformation")

	def displayInformation(self):
		info = []
		info.append(self.formatLine("H", _("Geolocation information for %s %s") % getBoxDisplayName()))
		info.append("")
		geolocationData = geolocation.getGeolocationData(fields="continent,country,regionName,city,lat,lon,timezone,currency,isp,org,mobile,proxy,query", useCache=False)
		if geolocationData.get("status", None) == "success":
			info.append(self.formatLine("S", _("Location information")))
			if self.extraSpacing:
				info.append("")
			continent = geolocationData.get("continent", None)
			if continent:
				info.append(self.formatLine("P1", _("Continent"), continent))
			country = geolocationData.get("country", None)
			if country:
				info.append(self.formatLine("P1", _("Country"), country))
			state = geolocationData.get("regionName", None)
			if state:
				# TRANSLATORS: "State" is location information and not condition based information.
				info.append(self.formatLine("P1", _("State"), state))
			city = geolocationData.get("city", None)
			if city:
				info.append(self.formatLine("P1", _("City"), city))
			latitude = geolocationData.get("lat", None)
			if latitude:
				info.append(self.formatLine("P1", _("Latitude"), latitude))
			longitude = geolocationData.get("lon", None)
			if longitude:
				info.append(self.formatLine("P1", _("Longitude"), longitude))
			info.append("")
			info.append(self.formatLine("S", _("Local information")))
			if self.extraSpacing:
				info.append("")
			timezone = geolocationData.get("timezone", None)
			if timezone:
				info.append(self.formatLine("P1", _("Timezone"), timezone))
			currency = geolocationData.get("currency", None)
			if currency:
				info.append(self.formatLine("P1", _("Currency"), currency))
			info.append("")
			info.append(self.formatLine("S", _("Connection information")))
			if self.extraSpacing:
				info.append("")
			isp = geolocationData.get("isp", None)
			if isp:
				ispOrg = geolocationData.get("org", None)
				if ispOrg:
					info.append(self.formatLine("P1", _("ISP"), f"{isp}  ({ispOrg})"))
				else:
					info.append(self.formatLine("P1", _("ISP"), isp))
			mobile = geolocationData.get("mobile", None)
			info.append(self.formatLine("P1", _("Mobile connection"), (_("Yes") if mobile else _("No"))))
			proxy = geolocationData.get("proxy", False)
			info.append(self.formatLine("P1", _("Proxy detected"), (_("Yes") if proxy else _("No"))))
			publicIp = geolocationData.get("query", None)
			if publicIp:
				info.append(self.formatLine("P1", _("Public IP"), publicIp))
		else:
			info.append(_("Geolocation information cannot be retrieved, please try again later."))
			info.append("")
			info.append(_("Access to geolocation information requires an Internet connection."))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Geolocation Information"


class InformationMemory(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Memory Information"))
		self.skinName.insert(0, "InformationMemory")
		self.skinName.insert(1, "MemoryInformation")
		self["clearActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyClearMemoryInformation, _("Clear the virtual memory caches"))
		}, prio=0, description=_("Memory Information Actions"))
		self["key_yellow"] = StaticText(_("Clear"))

	def keyClearMemoryInformation(self):
		self.console.ePopen(("/bin/sync", "/bin/sync"))
		fileWriteLine("/proc/sys/vm/drop_caches", "3")
		self.informationTimer.start(25)
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

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
		info.append(self.formatLine("H", _("Memory information for %s %s") % getBoxDisplayName()))
		info.append("")
		memInfo = fileReadLines("/proc/meminfo", source=MODULE_NAME)
		info.append(self.formatLine("S", _("RAM (Summary)")))
		if self.extraSpacing:
			info.append("")
		for line in memInfo:
			key, value = (x for x in line.split(maxsplit=1))
			if key == "MemTotal:":
				info.append(self.formatLine("P1", _("Total memory"), formatNumber(value)))
			elif key == "MemFree:":
				info.append(self.formatLine("P1", _("Free memory"), formatNumber(value)))
			elif key == "Buffers:":
				info.append(self.formatLine("P1", _("Buffers"), formatNumber(value)))
			elif key == "Cached:":
				info.append(self.formatLine("P1", _("Cached"), formatNumber(value)))
			elif key == "SwapTotal:":
				info.append(self.formatLine("P1", _("Total swap"), formatNumber(value)))
			elif key == "SwapFree:":
				info.append(self.formatLine("P1", _("Free swap"), formatNumber(value)))
		info.append("")
		info.append(self.formatLine("S", _("FLASH")))
		if self.extraSpacing:
			info.append("")
		stat = statvfs("/")
		diskSize = stat.f_blocks * stat.f_frsize
		diskFree = stat.f_bfree * stat.f_frsize
		diskUsed = diskSize - diskFree
		info.append(self.formatLine("P1", _("Total flash"), f"{scaleNumber(diskSize)}  ({scaleNumber(diskSize, "Iec")})"))
		info.append(self.formatLine("P1", _("Used flash"), f"{scaleNumber(diskUsed)}  ({scaleNumber(diskUsed, "Iec")})"))
		info.append(self.formatLine("P1", _("Free flash"), f"{scaleNumber(diskFree)}  ({scaleNumber(diskFree, "Iec")})"))
		for line in fileReadLines("/proc/mtd", [], source=MODULE_NAME):
			if "\"kernel" in line:
				data = line.split()
				name = data[3].strip("\"")
				size = int(data[1], 16)
				label = _("Kernel partition") if name == "kernel" else _("Kernel%s partition") % name.replace("kernel", "")
				info.append(self.formatLine("P1", label, f"{scaleNumber(size)} ({scaleNumber(size, "Iec")})"))
		info.append("")
		info.append(self.formatLine("S", _("RAM (Details)")))
		if self.extraSpacing:
			info.append("")
		for line in memInfo:
			key, value = (x for x in line.split(maxsplit=1))
			info.append(self.formatLine("P1", key[:-1], formatNumber(value)))
		info.append("")
		info.append(self.formatLine("M1", _("The detailed information is intended for developers only.")))
		info.append(self.formatLine("M1", _("Please don't panic if you see values that look suspicious.")))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Memory Information Data"


class InformationMultiBoot(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("MultiBoot Information"))
		self.skinName.insert(0, "InformationMultiBoot")
		self.skinName.insert(1, "MultiBootInformation")
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
		info.append(self.formatLine("H", _("Boot slot information for %s %s") % getBoxDisplayName()))
		info.append("")
		if self.slotImages:
			slotCode, bootCode = MultiBoot.getCurrentSlotAndBootCodes()
			slotImageList = sorted(self.slotImages.keys(), key=lambda x: (not x.isnumeric(), int(x) if x.isnumeric() else x))
			currentMsg = f"  -  {_("Active")}"
			imageLists = {}
			for slot in slotImageList:
				for boot in self.slotImages[slot]["bootCodes"]:
					if imageLists.get(boot) is None:
						imageLists[boot] = []
					active = currentMsg if boot == bootCode and slot == slotCode else ""
					indent = "P0V" if boot == "" else "P1V"
					if active:
						indent = indent.replace("P", "F").replace("V", "F")
					device = self.slotImages[slot]["device"]
					slotType = "eMMC" if "mmcblk" in device else "MTD" if "mtd" in device else "UBI" if "ubi" in device else "USB"
					imageLists[boot].append(self.formatLine(indent, _("Slot '%s' %s") % (slot, slotType), f"{self.slotImages[slot]["imagename"]}{active}"))
			count = 0
			for bootCode in sorted(imageLists.keys()):
				if bootCode == "":
					continue
				if count:
					info.append("")
				info.append(self.formatLine("S", MultiBoot.getBootCodeDescription(bootCode), None))
				if self.extraSpacing:
					info.append("")
				info.extend(imageLists[bootCode])
				count += 1
			if count:
				info.append("")
			if "" in imageLists:
				info.extend(imageLists[""])
		else:
			info.append(self.formatLine("P1", _("Retrieving boot slot information...")))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "MultiBoot Information Data"


class InformationNetwork(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Network Information"))
		self.skinName.insert(0, "InformationNetwork")
		self.skinName.insert(1, "NetworkInformation")
		self["key_yellow"] = StaticText(_("WAN Geolocation"))
		self["geolocationActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyUseGeolocation, _("Use geolocation to get WAN information")),
		}, prio=0, description=_("Network Information Actions"))
		self.geolocationData = []

	def keyUseGeolocation(self):
		geolocationData = geolocation.getGeolocationData(fields="isp,org,mobile,proxy,query", useCache=False)
		info = []
		if geolocationData.get("status", None) == "success":
			info.append("")
			info.append(self.formatLine("S", _("WAN connection information")))
			isp = geolocationData.get("isp", None)
			if isp:
				ispOrg = geolocationData.get("org", None)
				if ispOrg:
					info.append(self.formatLine("P1", _("ISP"), f"{isp}  ({ispOrg})"))
				else:
					info.append(self.formatLine("P1", _("ISP"), isp))
			mobile = geolocationData.get("mobile", None)
			info.append(self.formatLine("P1", _("Mobile connection"), (_("Yes") if mobile else _("No"))))
			proxy = geolocationData.get("proxy", False)
			info.append(self.formatLine("P1", _("Proxy detected"), (_("Yes") if proxy else _("No"))))
			publicIp = geolocationData.get("query", None)
			if publicIp:
				info.append(self.formatLine("P1", _("Public IP"), publicIp))
		else:
			info.append(_("Geolocation information cannot be retrieved, please try again later."))
			info.append("")
			info.append(_("Access to geolocation information requires an Internet connection."))
		self.geolocationData = info
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def displayInformation(self, selectedAdapter=None):
		info = []
		info.append(self.formatLine("H", _("Network information for %s %s") % getBoxDisplayName()))
		info.append("")
		hostname = fileReadLine("/proc/sys/kernel/hostname", source=MODULE_NAME)
		info.append(self.formatLine("S0S", _("Hostname"), hostname))
		for interface in sorted(networkManager.adapters.keys()):
			adapter = networkManager.adapters[interface]
			if selectedAdapter and selectedAdapter != adapter:
				continue
			net = adapter.netInfo
			info.append("")
			info.append(self.formatLine("S", _("Interface '%s'") % interface, _("Wi-Fi") if adapter.isWiFi else _("LAN")))
			info.append(self.formatLine("P1", _("Status"), (_("Up / Active") if net.up else _("Down / Inactive"))))
			if net.up:
				if net.ip != [0, 0, 0, 0]:
					info.append(self.formatLine("P1", _("IP address"), ".".join(str(x) for x in net.ip)))
				if net.netmask != [0, 0, 0, 0]:
					info.append(self.formatLine("P1", _("Netmask"), ".".join(str(x) for x in net.netmask)))
				if net.gateway != [0, 0, 0, 0]:
					info.append(self.formatLine("P1", _("Gateway"), ".".join(str(x) for x in net.gateway)))
				if net.bcast != [0, 0, 0, 0]:
					info.append(self.formatLine("P1", _("Broadcast address"), ".".join(str(x) for x in net.bcast)))
				for ip6 in net.ip6:
					info.append(self.formatLine("P1", _("IPv6 address"), ip6.get("addr", "")))
					info.append(self.formatLine("P3V2", _("Scope"), ip6.get("scope", "").capitalize()))
				if adapter.mac:
					info.append(self.formatLine("P1", _("MAC address"), adapter.mac))
				if net.mtu:
					info.append(self.formatLine("P1", _("MTU"), net.mtu))
				if adapter.isWiFi:
					if net.ssid:
						info.append(self.formatLine("P1", _("SSID"), net.ssid))
						connection = next((x for x in networkManager.getConnections(interface) if x.wifi and x.wifi.ssid == net.ssid), None)
						if connection:
							label = encryptionLabels.get(connection.wifi.encryption)
							info.append(self.formatLine("P1", _("Encryption"), label() if label else connection.wifi.encryption))
					if net.bssid:
						info.append(self.formatLine("P1", _("Access point"), net.bssid))
					if net.freqMhz:
						info.append(self.formatLine("P1", _("Frequency"), f"{net.freqMhz} MHz"))
					if net.channel:
						info.append(self.formatLine("P1", _("Channel"), net.channel))
					if net.bitrateBps:
						info.append(self.formatLine("P1", _("Bitrate"), f"{net.bitrateBps // 1000000} Mbps"))
					if net.signal:
						info.append(self.formatLine("P1", _("Signal strength"), f"{net.signal} dBm"))
				else:
					if net.speed > 0:
						info.append(self.formatLine("P1", _("Speed"), f"{net.speed} Mbps"))
					if net.duplex:
						info.append(self.formatLine("P1", _("Duplex"), _(net.duplex.capitalize())))
					if net.transceiver:
						info.append(self.formatLine("P1", _("Transceiver"), _(net.transceiver.capitalize())))
					info.append(self.formatLine("P1", _("Link detected"), (_("Yes") if net.link else _("No"))))
				if net.bus:
					info.append(self.formatLine("P1", _("Bus"), net.bus.upper()))
				if net.driver:
					info.append(self.formatLine("P1", _("Driver"), net.driver))
			if net.rxBytes or net.txBytes:
				info.append("")
				info.append(self.formatLine("P1", _("Bytes received"), "%d (%s)" % (net.rxBytes, scaleNumber(net.rxBytes, style="Iec", format="%.1f"))))
				info.append(self.formatLine("P1", _("Bytes sent"), "%d (%s)" % (net.txBytes, scaleNumber(net.txBytes, style="Iec", format="%.1f"))))
		info += self.geolocationData
		self["information"].setText("\n".join(info))


class InformationPicture(Screen):
	skin = """
	<screen name="InformationPicture" title="Picture Information" position="center,center" size="950,560" resolution="1280,720">
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
		self.skinName = ["InformationPicture"]
		self.skinName.append("PictureInformation")
		self["name"] = Label()
		self["picture"] = Pixmap()
		self["key_red"] = StaticText(_("Close"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"cancel": (self.keyClose, _("Close the screen")),
			"close": (self.keyCloseRecursive, _("Close the screen and exit all menus")),
			"red": (self.keyClose, _("Close the screen")),
		}, prio=0, description=_("Picture Information Actions"))
		self["pictureActions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"ok": (self.keyNextPicture, _("Show next picture")),
			"yellow": (self.keyPrevPicture, _("Show previous picture")),
			"blue": (self.keyNextPicture, _("Show next picture")),
			"up": (self.keyPrevPicture, _("Show previous picture")),
			"left": (self.keyPrevPicture, _("Show previous picture")),
			"right": (self.keyNextPicture, _("Show next picture")),
			"down": (self.keyNextPicture, _("Show next picture"))
		}, prio=0, description=_("Picture Information Actions"))
		self["pictureActions"].setEnabled(False)
		self.definedPictures = (
			(_("Remote Control"), f"hardware/{BoxInfo.getItem("rcname")}.png"),
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

	def keyClose(self):
		self.close()

	def keyCloseRecursive(self):
		self.close(True)

	def keyPrevPicture(self):
		self.pictureIndex = (self.pictureIndex - 1) % self.pictureMax
		self.layoutFinished()

	def keyNextPicture(self):
		self.pictureIndex = (self.pictureIndex + 1) % self.pictureMax
		self.layoutFinished()

	def layoutFinished(self):
		self["name"].setText(f"{DISPLAY_BRAND} {DISPLAY_MODEL}  -  {_("%s View") % self.pictures[self.pictureIndex][0]}")
		if self.pictureMax > 1:
			self["key_yellow"].setText(self.pictures[(self.pictureIndex - 1) % self.pictureMax][0])
			self["key_blue"].setText(self.pictures[(self.pictureIndex + 1) % self.pictureMax][0])
			self["pictureActions"].setEnabled(True)
		else:
			self["key_yellow"].setText("")
			self["key_blue"].setText("")
			self["pictureActions"].setEnabled(False)
		picture = self.pictures[self.pictureIndex][1]
		if picture:
			self["picture"].instance.setPixmap(self.pictures[self.pictureIndex][1])


class InformationReceiver(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Receiver Information"))
		self.skinName.insert(0, "InformationReceiver")
		self.skinName.insert(1, "ReceiverInformation")
		self["key_info"] = StaticText(_("INFO"))
		self["key_yellow"] = StaticText(_("System Information"))
		self["key_blue"] = StaticText(_("Debug Information"))
		self["receiverActions"] = HelpableActionMap(self, ["InfoActions", "ColorActions"], {
			"info": (self.keyShowPictureInformation, _("Show picture information")),
			"yellow": (self.keyShowSystemInformation, _("Show system information")),
			"blue": (self.keyShowDebugInformation, _("Show debug log information"))
		}, prio=0, description=_("Receiver Information Actions"))

	def keyShowPictureInformation(self):
		self.session.openWithCallback(self.informationWindowClosed, InformationPicture)

	def keyShowSystemInformation(self):
		self.session.openWithCallback(self.informationWindowClosed, InformationSystem)

	def keyShowDebugInformation(self):
		self.session.openWithCallback(self.informationWindowClosed, InformationDebug)

	def displayInformation(self):
		def getBoxProcTypeName():  # This code is all to move into SystemInfo.py when it can handle translated text.
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
			return f"{procType}  -  {boxProcTypes.get(procType, _("Unknown"))}"

		def findPackageRevision(package, packageList):
			revision = None
			data = [x for x in packageList if f"-{package}" in x]
			if data:
				data = data[0].split("-")
				if len(data) >= 4:
					revision = data[3]
			return revision

		info = []
		info.append(self.formatLine("H", _("Receiver information for %s %s") % getBoxDisplayName()))
		info.append("")
		info.append(self.formatLine("S", _("Hardware information")))
		if self.extraSpacing:
			info.append("")
		info.append(self.formatLine("P1", _("Receiver name"), "%s %s" % getBoxDisplayName()))
		info.append(self.formatLine("P1", _("Build Brand"), BoxInfo.getItem("brand")))
		platform = BoxInfo.getItem("platform")
		info.append(self.formatLine("P1", _("Build Model"), MODEL))
		if platform != MODEL:
			info.append(self.formatLine("P1", _("Platform"), platform))
		procModel = getBoxProc()
		if procModel != MODEL:
			info.append(self.formatLine("P1", _("Proc model"), procModel))
		procModelType = getBoxProcTypeName()
		if procModelType and procModelType != _("Unknown"):
			info.append(self.formatLine("P1", _("Hardware type"), procModelType))
		hwSerial = getHWSerial()
		if hwSerial:
			info.append(self.formatLine("P1", _("Hardware serial"), (hwSerial if hwSerial != "unknown" else about.getCPUSerial())))
		hwRelease = fileReadLine("/proc/stb/info/release", source=MODULE_NAME)
		if hwRelease:
			info.append(self.formatLine("P1", _("Factory release"), hwRelease))
		hwVersion = fileReadLine("/proc/stb/info/version", source=MODULE_NAME)
		if hwVersion:
			match = search(r"\brev[0-9]+\b", hwVersion)
			if match:
				hwVersion = match.group(0)
			info.append(self.formatLine("P1", _("Hardware revision"), hwVersion))
		displayType = BoxInfo.getItem("displaytype")
		if displayType and not displayType.startswith(" "):
			info.append(self.formatLine("P1", _("Display type"), displayType))
		fpVersion = getFPVersion()
		if fpVersion and fpVersion != "unknown":
			info.append(self.formatLine("P1", _("Front processor version"), fpVersion))
		demodVersion = getDemodVersion()
		if demodVersion and demodVersion != "unknown":
			info.append(self.formatLine("P1", _("Demod firmware version"), demodVersion))
		transcoding = _("Yes") if BoxInfo.getItem("transcoding") else _("MultiTranscoding") if BoxInfo.getItem("multitranscoding") else _("No")
		info.append(self.formatLine("P1", _("Transcoding"), transcoding))
		temp = about.getSystemTemperature()
		if temp:
			info.append(self.formatLine("P1", _("System temperature"), temp))
		info.append("")
		info.append(self.formatLine("S", _("Processor information")))
		if self.extraSpacing:
			info.append("")
		cpu = about.getCPUInfoString()
		info.append(self.formatLine("P1", _("CPU"), cpu[0]))
		info.append(self.formatLine("P1", _("CPU speed/cores"), f"{cpu[1]} {cpu[2]}"))
		if cpu[3]:
			info.append(self.formatLine("P1", _("CPU temperature"), cpu[3]))
		info.append(self.formatLine("P1", _("CPU brand"), about.getCPUBrand()))
		socFamily = BoxInfo.getItem("socfamily")
		if socFamily:
			info.append(self.formatLine("P1", _("SoC family"), socFamily))
		info.append(self.formatLine("P1", _("CPU architecture"), about.getCPUArch()))
		if BoxInfo.getItem("fpu"):
			info.append(self.formatLine("P1", _("FPU"), BoxInfo.getItem("fpu")))
		if BoxInfo.getItem("architecture") == "aarch64":
			info.append(self.formatLine("P1", _("MultiLib"), (_("Yes") if BoxInfo.getItem("multilib") else _("No"))))
		info.append("")
		info.append(self.formatLine("S", _("Remote control information")))
		if self.extraSpacing:
			info.append("")
		rcIndex = int(config.inputDevices.remotesIndex.value)
		info.append(self.formatLine("P1", _("RC identification"), f"{remoteControl.remotes[rcIndex][remoteControl.REMOTE_DISPLAY_NAME]}  (Index: {rcIndex})"))
		rcName = remoteControl.remotes[rcIndex][remoteControl.REMOTE_NAME]
		info.append(self.formatLine("P1", _("RC selected name"), rcName))
		boxName = BoxInfo.getItem("rcname")
		if boxName != rcName:
			info.append(self.formatLine("P1", _("RC default name"), boxName))
		rcType = remoteControl.remotes[rcIndex][remoteControl.REMOTE_RCTYPE]
		info.append(self.formatLine("P1", _("RC selected type"), rcType))
		boxType = BoxInfo.getItem("rctype")
		if boxType != rcType:
			info.append(self.formatLine("P1", _("RC default type"), boxType))
		boxRcType = getBoxRCType()
		if boxRcType:
			if boxRcType == "unknown":
				if isfile("/usr/bin/remotecfg"):
					boxRcType = _("Amlogic remote")
				elif isfile("/usr/sbin/lircd"):
					boxRcType = _("LIRC remote")
			if boxRcType != rcType and boxRcType != "unknown":
				info.append(self.formatLine("P1", _("RC detected type"), boxRcType))
		customCode = fileReadLine("/proc/stb/ir/rc/customcode", source=MODULE_NAME)
		if customCode:
			info.append(self.formatLine("P1", _("RC custom code"), customCode))
		if BoxInfo.getItem("HasHDMI-CEC") and config.hdmicec.enabled.value:
			info.append("")
			address = config.hdmicec.fixed_physical_address.value if config.hdmicec.fixed_physical_address.value != "0.0.0.0" else _("N/A")
			info.append(self.formatLine("P1", _("HDMI-CEC address"), address))
		info.append("")
		info.append(self.formatLine("S", _("Driver and kernel information")))
		if self.extraSpacing:
			info.append("")
		info.append(self.formatLine("P1", _("Drivers version"), formatDate(BoxInfo.getItem("driversdate"))))
		info.append(self.formatLine("P1", _("Kernel version"), BoxInfo.getItem("kernel")))
		deviceId = fileReadLine("/proc/device-tree/amlogic-dt-id", source=MODULE_NAME)
		if deviceId:
			info.append(self.formatLine("P1", _("Device id"), deviceId))
		givenId = fileReadLine("/proc/device-tree/le-dt-id", source=MODULE_NAME)
		if givenId:
			info.append(self.formatLine("P1", _("Given device id"), givenId))
		if BoxInfo.getItem("HiSilicon"):
			info.append("")
			info.append(self.formatLine("S", _("HiSilicon specific information")))
			if self.extraSpacing:
				info.append("")
			process = Popen(("/usr/bin/opkg", "list-installed"), stdout=PIPE, stderr=PIPE, universal_newlines=True)
			stdout, stderr = process.communicate()
			if process.returncode == 0:
				missing = True
				packageList = stdout.split("\n")
				revision = findPackageRevision("grab", packageList)
				if revision and revision != "r0":
					info.append(self.formatLine("P1", _("Grab"), revision))
					missing = False
				revision = findPackageRevision("hihalt", packageList)
				if revision:
					info.append(self.formatLine("P1", _("Halt"), revision))
					missing = False
				revision = findPackageRevision("libs", packageList)
				if revision:
					info.append(self.formatLine("P1", _("Libs"), revision))
					missing = False
				revision = findPackageRevision("partitions", packageList)
				if revision:
					info.append(self.formatLine("P1", _("Partitions"), revision))
					missing = False
				revision = findPackageRevision("reader", packageList)
				if revision:
					info.append(self.formatLine("P1", _("Reader"), revision))
					missing = False
				revision = findPackageRevision("showiframe", packageList)
				if revision:
					info.append(self.formatLine("P1", _("Showiframe"), revision))
					missing = False
				if missing:
					info.append(self.formatLine("P1", _("HiSilicon specific information not found.")))
			else:
				info.append(self.formatLine("P1", _("Package information currently not available!")))
		info.append("")
		info.append(self.formatLine("S", _("Tuner information")))
		if self.extraSpacing:
			info.append("")
		for count, nim in enumerate(nimmanager.nimListCompressed()):
			tuner, type = (x.strip() for x in nim.split(":", 1))
			info.append(self.formatLine("P1", tuner, type))
		info.append("")
		info.append(self.formatLine("S", _("Storage / Drive information")))
		if self.extraSpacing:
			info.append("")
		stat = statvfs("/")
		diskSize = stat.f_blocks * stat.f_frsize
		info.append(self.formatLine("P1", _("Internal flash"), f"{scaleNumber(diskSize)}  ({scaleNumber(diskSize, "Iec")})"))
		# hddList = storageManager.HDDList()
		hddList = harddiskmanager.HDDList()
		if hddList:
			for hdd in hddList:
				hdd = hdd[1]
				diskSize = hdd.diskSize() * 1000000
				info.append(self.formatLine("P1", hdd.model(), f"{scaleNumber(diskSize)}  ({scaleNumber(diskSize, "Iec")})"))
		else:
			info.append(self.formatLine("H", _("No hard disks detected.")))
		info.append("")
		info.append(self.formatLine("S", _("Network information")))
		if self.extraSpacing:
			info.append("")
		for x in about.GetIPsFromNetworkInterfaces():
			info.append(self.formatLine("P1", x[0], x[1]))
		info.append("")
		info.append(self.formatLine("S", _("Uptime"), about.getBoxUptime()))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Receiver Information"


class InformationService(InformationBase):
	def __init__(self, session, serviceRef=None):
		InformationBase.__init__(self, session)
		self.baseTitle = _("Service Information")
		self.setTitle(self.baseTitle)
		self.skinName.insert(0, "InformationService")
		self.skinName.insert(1, "ServiceInformation")
		self.serviceRef = serviceRef
		self["key_menu"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["serviceActions"] = HelpableActionMap(self, ["MenuActions", "ColorActions", "NavigationActions"], {
			"menu": (self.keyShowServiceMenu, _("Show selection for service information screen")),
			"yellow": (self.keyPreviousService, _("Show previous service information screen")),
			"blue": (self.keyNextService, _("Show next service information screen")),
			"left": (self.keyPreviousService, _("Show previous service information screen")),
			"right": (self.keyNextService, _("Show next service information screen"))
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

	def fetchInformationDelayed(self):  # This allows the newly selected service to stabilize before updating the service data.
		self.informationTimer.startLongTimer(3)

	def keyShowServiceMenu(self):
		def keyShowServiceMenuCallBack(selectedIndex):
			if isinstance(selectedIndex, int):
				self.serviceCommandsIndex = selectedIndex
				self.displayInformation()
				self.informationTimer.start(25)

		choices = [(serviceCommand[0], index) for index, serviceCommand in enumerate(self.serviceCommands)]
		self.session.openWithCallback(keyShowServiceMenuCallBack, MessageBox, text=_("Select service information to view:"), list=choices, windowTitle=self.baseTitle)

	def keyPreviousService(self):
		self.serviceCommandsIndex = (self.serviceCommandsIndex - 1) % self.serviceCommandsMax
		self.displayInformation()
		self.informationTimer.start(25)

	def keyNextService(self):
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
		def addIfAvailable(info, label, value):
			if value not in (None, "", -1, _("N/A")):
				info.append(self.formatLine("P1", label, value))

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
				namespace = f"{_("N/A")}  -  {_("N/A")}"
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
				indent = "P1F0" if subtitle[:3] == subtitleSelected else "P1"
				subtitleLang = subtitle[4]
				if subtitle[0] == 0:  # DVB PID.
					info.append(self.formatLine(indent, _("DVB Subtitles PID & Language"), f"{formatHex(subtitle[1])}  -  {subtitleLang}"))
				elif subtitle[0] == 1:  # Teletext.
					info.append(self.formatLine(indent, _("TXT Subtitles page & Language"), f"0x0{subtitle[3] or 8:X}{subtitle[2]:02X}  -  {subtitleLang}"))
				elif subtitle[0] == 2:  # File.
					subtitleDesc = subtitleTypes.get(subtitle[2], f"{_("Unknown")}: {subtitle[2]}")
					info.append(self.formatLine(indent, _("Other Subtitles & Language"), f"{subtitle[1] + 1}  -  {subtitleDesc}  -  {subtitleLang}"))

		info = []
		if self.serviceReferenceType == eServiceReference.idServiceDAB and self.serviceInfo:
			info.append(self.formatLine("H", _("DAB+ service information for '%s'") % self.serviceName))
			info.append("")
			addIfAvailable(info, _("Station"), self.serviceName)
			addIfAvailable(info, _("Reception source"), getServiceInfoValue(iServiceInformation.sProvider))
			addIfAvailable(info, _("Ensemble"), getServiceInfoValue(iServiceInformation.sDABEnsembleLabel))
			ensembleId = getServiceInfoValue(iServiceInformation.sDABEnsembleId)
			addIfAvailable(info, _("Ensemble ID (EID)"), formatHex(ensembleId))
			addIfAvailable(info, _("Service ID (SID)"), formatHex(getServiceInfoValue(iServiceInformation.sSID)))
			channel = getServiceInfoValue(iServiceInformation.sDABChannel)
			serviceRef = self.session.nav.getCurrentlyPlayingServiceReference()
			if channel:
				frequency = getRTLSDRChannelFrequency(channel)
				channelText = _("Block %s") % channel
				if frequency:
					channelText = _("Block %s - %.3f MHz") % (channel, frequency / 1000.0)
				addIfAvailable(info, _("DAB+ channel"), channelText)
			elif serviceRef:
				addIfAvailable(info, _("DVB payload PID"), formatHex(serviceRef.getUnsignedData(5) & 0x1FFF))
			addIfAvailable(info, _("Program type"), getServiceInfoValue(iServiceInformation.sTagGenre))
			addIfAvailable(info, _("Language"), getServiceInfoValue(iServiceInformation.sTagLanguageCode))
			addIfAvailable(info, _("Codec"), getServiceInfoValue(iServiceInformation.sTagCodec))
			addIfAvailable(info, _("Audio bit rate"), getServiceInfoValue(iServiceInformation.sTagBitrate))
			addIfAvailable(info, _("Protection"), getServiceInfoValue(iServiceInformation.sDABProtection))
			addIfAvailable(info, _("Dynamic label"), getServiceInfoValue(iServiceInformation.sDABDynamicLabel))
			addIfAvailable(info, _("RTL-SDR tuner"), getServiceInfoValue(iServiceInformation.sDABReceiverName))
			frontendInfo = self.service and self.service.frontendInfo()
			if frontendInfo and channel:
				locked = frontendInfo.getFrontendInfo(iFrontendInformation.lockState)
				info.append("")
				addIfAvailable(info, _("Receiver lock"), _("Locked") if locked else _("Tuning"))
				snr = frontendInfo.getFrontendInfo(iFrontendInformation.signalQualitydB)
				if snr >= 0:
					addIfAvailable(info, _("RF SNR"), "%.2f dB" % (snr / 100.0))
				ficQuality = getServiceInfoValue(iServiceInformation.sDABFICQuality)
				mscQuality = getServiceInfoValue(iServiceInformation.sDABMSCQuality)
				if isinstance(ficQuality, int) and ficQuality >= 0:
					addIfAvailable(info, _("FIC quality"), "%d %%" % ficQuality)
				if isinstance(mscQuality, int) and mscQuality >= 0:
					addIfAvailable(info, _("MSC audio frame quality"), "%d %%" % mscQuality)
		else:
			info.append(self.formatLine("H", _("Service and PID information for '%s'") % self.serviceName))
			info.append("")
			if self.serviceInfo:
				from Components.Converter.PliExtraInfo import codec_data  # This should be in SystemInfo maybe as a BoxInfo variable.
				videoData = []
				videoData.append(codec_data.get(self.serviceInfo.getInfo(iServiceInformation.sVideoType), _("N/A")))
				width = self.serviceInfo.getInfo(iServiceInformation.sVideoWidth)
				height = self.serviceInfo.getInfo(iServiceInformation.sVideoHeight)
				if width > 0 and height > 0:
					videoData.append(f"{width}x{height}")
					videoData.append(f"{(self.serviceInfo.getInfo(iServiceInformation.sFrameRate) + 500) // 1000}{("i", "p", "")[self.serviceInfo.getInfo(iServiceInformation.sProgressive)]}")
					videoData.append(f"[{"4:3" if getServiceInfoValue(iServiceInformation.sAspect) in (1, 2, 5, 6, 9, 0xA, 0xD, 0xE) else "16:9"}]")  # This should be in SystemInfo maybe as a BoxInfo variable.
				gamma = ("SDR", "HDR", "HDR10", "HLG", "")[self.serviceInfo.getInfo(iServiceInformation.sGamma)]  # This should be in SystemInfo maybe as a BoxInfo variable.
				if gamma:
					videoData.append(gamma)
				videoData = "  -  ".join(videoData)
			else:
				videoData = _("Unknown")
			if "%3a//" in self.serviceReference and self.serviceReferenceType not in (1, 257, 4098, 4114):  # IPTV 4097 5001, no PIDs shown.
				info.append(self.formatLine("P1", _("Video Codec, Size & Format"), videoData))
				info.append(self.formatLine("P1", _("Service reference"), ":".join(self.serviceReference.split(":")[:9])))
				info.append(self.formatLine("P1", _("URL"), self.serviceReference.split(":")[10].replace("%3a", ":")))
				getSubtitleList()  # IanSav: This wasn't activated to be used!
			else:
				if ":/" in self.serviceReference:  # mp4 videos, DVB-S-T recording.
					info.append(self.formatLine("P1", _("Video Codec, Size & Format"), videoData))
					info.append(self.formatLine("P1", _("Service reference"), ":".join(self.serviceReference.split(":")[:9])))
					info.append(self.formatLine("P1", _("Filename"), self.serviceReference.split(":")[10]))
				else:  # fallback, movistartv, live DVB-S-T.
					info.append(self.formatLine("P1", _("Provider"), getServiceInfoValue(iServiceInformation.sProvider)))
					info.append(self.formatLine("P1", _("Video Codec, Size & Format"), videoData))
					if "%3a//" in self.serviceReference:  # fallback, movistartv.
						info.append(self.formatLine("P1", _("Service reference"), ":".join(self.serviceReference.split(":")[:9])))
						info.append(self.formatLine("P1", _("URL"), self.serviceReference.split(":")[10].replace("%3a", ":")))
					else:  # Live DVB-S-T
						info.append(self.formatLine("P1", _("Service reference"), self.serviceReference))
				info.append(self.formatLine("P1", _("Namespace & Orbital position"), getNamespace(getServiceInfoValue(iServiceInformation.sNamespace))))
				info.append(self.formatLine("P1", _("Service ID (SID)"), formatHex(getServiceInfoValue(iServiceInformation.sSID))))
				info.append(self.formatLine("P1", _("Transport Stream ID (TSID)"), formatHex(getServiceInfoValue(iServiceInformation.sTSID))))
				info.append(self.formatLine("P1", _("Original Network ID (ONID)"), formatHex(getServiceInfoValue(iServiceInformation.sONID))))
				info.append(self.formatLine("P1", _("Video PID"), formatHex(getServiceInfoValue(iServiceInformation.sVideoPID))))
				audio = self.service and self.service.audioTracks()
				numberOfTracks = audio and audio.getNumberOfTracks()
				if numberOfTracks:
					for index in range(numberOfTracks):
						audioPID = audio.getTrackInfo(index).getPID()
						audioDesc = audio.getTrackInfo(index).getDescription()
						audioLang = audio.getTrackInfo(index).getLanguage() or _("Undefined")
						audioPIDValue = _("N/A") if getServiceInfoValue(iServiceInformation.sAudioPID) == "N/A" else formatHex(audioPID)
						indent = "P1F0" if numberOfTracks > 1 and audio.getCurrentTrack() == index else "P1"
						info.append(self.formatLine(indent, _("Audio PID%s, Codec & Language") % (f" {index + 1}" if numberOfTracks > 1 else ""), f"{audioPIDValue}  -  {audioDesc}  -  {audioLang}"))
				else:
					info.append(self.formatLine("P1", _("Audio PID"), _("N/A")))
				info.append(self.formatLine("P1", _("PCR PID"), formatHex(getServiceInfoValue(iServiceInformation.sPCRPID))))
				info.append(self.formatLine("P1", _("PMT PID"), formatHex(getServiceInfoValue(iServiceInformation.sPMTPID))))
				info.append(self.formatLine("P1", _("TXT PID"), formatHex(getServiceInfoValue(iServiceInformation.sTXTPID))))
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
			return f"{valueLive} {_("KSymb/s")}" if valueLive == valueConfig else f"{valueLive} {_("KSymb/s")}  ({valueConfig} {_("KSymb/s")})"

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
		info.append(self.formatLine("H", _("Transponder information for '%s'") % self.serviceName))
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
				info.append(self.formatLine("P1", _("NIM"), f"{chr(ord("A") + frontendLive.get("tuner_number", 0))}"))
			info.append(self.formatLine("P1", _("Type"), f"{frontendLive.get("tuner_type", na)}  [{tunerType}]"))
			if tunerType == "DVB-C":
				info.append(self.formatLine("P1", _("Modulation"), getValue("modulation", na)))
				info.append(self.formatLine("P1", _("Frequency"), getDVBCFrequencyValue()))
				info.append(self.formatLine("P1", _("Symbol rate"), getSymbolRateValue()))
				info.append(self.formatLine("P1", _("Forward Error Correction (FEC)"), getValue("fec_inner", na)))
				info.append(self.formatLine("P1", _("Inversion"), getValue("inversion", na)))
			elif tunerType == "DVB-S":
				info.append(self.formatLine("P1", _("System"), getValue("system", na)))
				info.append(self.formatLine("P1", _("Modulation"), getValue("modulation", na)))
				info.append(self.formatLine("P1", _("Orbital position"), getValue("orbital_position", na)))
				info.append(self.formatLine("P1", _("Frequency"), getDVBSFrequencyValue()))
				info.append(self.formatLine("P1", _("Polarization"), getValue("polarization", na)))
				info.append(self.formatLine("P1", _("Symbol rate"), getSymbolRateValue()))
				info.append(self.formatLine("P1", _("Forward Error Correction (FEC)"), getValue("fec_inner", na)))
				info.append(self.formatLine("P1", _("Inversion"), getValue("inversion", na)))
				info.append(self.formatLine("P1", _("Pilot"), getValue("pilot", na)))
				info.append(self.formatLine("P1", _("Roll-off"), getValue("rolloff", na)))
				info.append(self.formatLine("P1", _("Input Stream ID"), getInputStreamID()))
				info.append(self.formatLine("P1", _("PLS Mode"), getValue("pls_mode", na)))
				info.append(self.formatLine("P1", _("PLS Code"), getValue("pls_code", 0)))
				valueLive = frontendLive.get("t2mi_plp_id", -1)
				valueConfig = frontendConfig.get("t2mi_plp_id", -1)
				if valueLive != -1 or valueConfig != -1:
					info.append(self.formatLine("P1", _("T2MI PLP ID"), f"{valueLive}" if valueLive == valueConfig else f"{valueLive}  ({valueConfig})"))
				valueLive = None if frontendLive.get("t2mi_plp_id", -1) == -1 else frontendLive.get("t2mi_pid", eDVBFrontendParametersSatellite.T2MI_Default_Pid)
				valueConfig = None if frontendConfig.get("t2mi_plp_id", -1) == -1 else frontendConfig.get("t2mi_pid", eDVBFrontendParametersSatellite.T2MI_Default_Pid)
				if valueLive or valueConfig:
					info.append(self.formatLine("P1", _("T2MI PID"), f"{valueLive or "None"}" if valueLive == valueConfig else f"{valueLive or "None"}  ({valueConfig or "None"})"))
			elif tunerType == "DVB-T":
				info.append(self.formatLine("P1", _("Frequency"), getFrequencyValue()))
				info.append(self.formatLine("P1", _("Channel"), getValue("channel", na)))
				info.append(self.formatLine("P1", _("Inversion"), getValue("inversion", na)))
				info.append(self.formatLine("P1", _("Bandwidth"), getValue("bandwidth", na)))
				info.append(self.formatLine("P1", _("Code rate LP"), getValue("code_rate_lp", na)))
				info.append(self.formatLine("P1", _("Code rate HP"), getValue("code_rate_hp", na)))
				info.append(self.formatLine("P1", _("Guard Interval"), getValue("guard_interval", na)))
				info.append(self.formatLine("P1", _("Constellation"), getValue("constellation", na)))
				info.append(self.formatLine("P1", _("Transmission mode"), getValue("transmission_mode", na)))
				info.append(self.formatLine("P1", _("Hierarchy info"), getValue("hierarchy_information", na)))
			elif tunerType == "ATSC":
				info.append(self.formatLine("P1", _("System"), getValue("system", na)))
				info.append(self.formatLine("P1", _("Modulation"), getValue("modulation", na)))
				info.append(self.formatLine("P1", _("Frequency"), getFrequencyValue()))
				info.append(self.formatLine("P1", _("Inversion"), getValue("inversion", na)))
		else:
			info.append(self.formatLine("M0", _("Tuner data is not available!")))
		return info

	def showECMInformation(self):
		info = []
		info.append(self.formatLine("H", _("ECM information for '%s'") % self.serviceName))
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
				active = f" ({_("Active")})" if caID[0] == int(ecmData[1], 16) and (caID[1] == int(ecmData[3], 16) or str(int(ecmData[2], 16)) in provid) else ""
				info.append(self.formatLine("P1", f"ECMPid {caID[1]:04X} ({caID[1]})", f"{caID[0]:04X}-{description}{extraInfo}{active}"))
			if len(info) == 2:
				info.append(self.formatLine("P1", _("No ECM PIDs available"), _("Free to Air (FTA) Service")))
		return info

	def getSummaryInformation(self):
		return "Service Information"


class InformationStorage(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Storage / Disk Information"))
		self.skinName.insert(0, "InformationStorage")
		self.skinName.insert(1, "StorageDiskInformation")
		self["information"].setText(_("Retrieving network server information, please wait..."))
		self.mountInfo = []

	def fetchInformation(self):
		def fetchCallback(result, retVal, extraArgs=None):
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

		self.informationTimer.stop()
		self.console.ePopen("/bin/df -mh | /bin/grep -v '^Filesystem'", callback=fetchCallback)
		for callback in self.onInformationUpdated:
			if callable(callback):
				callback()

	def displayInformation(self):
		info = []
		info.append(self.formatLine("H", _("Storage / Disk information for %s %s") % getBoxDisplayName()))
		info.append("")
		partitions = sorted(harddiskmanager.getMountedPartitions(), key=lambda partitions: partitions.device or "")
		for partition in partitions:
			if partition.mountpoint == "/":
				info.append(self.formatLine("S1", "/dev/root", partition.description))
				stat = statvfs("/")
				diskSize = stat.f_blocks * stat.f_frsize
				diskFree = stat.f_bfree * stat.f_frsize
				diskUsed = diskSize - diskFree
				info.append(self.formatLine("P2", _("Mount point"), partition.mountpoint))
				info.append(self.formatLine("P2", _("Size"), f"{scaleNumber(diskSize)}  ({scaleNumber(diskSize, "Iec")})"))
				info.append(self.formatLine("P2", _("Used"), f"{scaleNumber(diskUsed)}  ({scaleNumber(diskUsed, "Iec")})"))
				info.append(self.formatLine("P2", _("Free"), f"{scaleNumber(diskFree)}  ({scaleNumber(diskFree, "Iec")})"))
				break
		# hddList = storageManager.HDDList()
		hddList = harddiskmanager.HDDList()
		if hddList:
			for hdd in hddList:
				hdd = hdd[1]
				info.append("")
				info.append(self.formatLine("S1", hdd.getDeviceName(), hdd.bus()))
				info.append(self.formatLine("P2", _("Model"), hdd.model()))
				diskSize = hdd.diskSize() * 1000000
				info.append(self.formatLine("P2", _("Size"), f"{scaleNumber(diskSize)}  ({scaleNumber(diskSize, "Iec")})"))
				info.append(self.formatLine("P2", _("Sleeping"), (_("Yes") if hdd.isSleeping() else _("No"))))
				for partition in partitions:
					if partition.device and join("/dev", partition.device).startswith(hdd.getDeviceName()):
						info.append(self.formatLine("P2", _("Partition"), partition.device))
						stat = statvfs(partition.mountpoint)
						diskSize = stat.f_blocks * stat.f_frsize
						diskFree = stat.f_bfree * stat.f_frsize
						diskUsed = diskSize - diskFree
						info.append(self.formatLine("P3", _("Mount point"), partition.mountpoint))
						info.append(self.formatLine("P3", _("Size"), f"{scaleNumber(diskSize)}  ({scaleNumber(diskSize, "Iec")})"))
						info.append(self.formatLine("P3", _("Used"), f"{scaleNumber(diskUsed)}  ({scaleNumber(diskUsed, "Iec")})"))
						info.append(self.formatLine("P3", _("Free"), f"{scaleNumber(diskFree)}  ({scaleNumber(diskFree, "Iec")})"))
		else:
			info.append("")
			info.append(self.formatLine("S1", _("No storage or hard disks detected.")))
		info.append("")
		info.append(self.formatLine("H", f"{_("Network storage on")} {DISPLAY_BRAND} {DISPLAY_MODEL}"))
		info.append("")
		if self.mountInfo:
			count = 0
			for data in self.mountInfo:
				if count:
					info.append("")
				info.append(self.formatLine("S1", data[5]))
				if data[0]:
					info.append(self.formatLine("P2", _("Network address"), data[0]))
					info.append(self.formatLine("P2", _("Size"), data[1]))
					info.append(self.formatLine("P2", _("Used"), f"{data[2]}  ({data[4]})"))
					info.append(self.formatLine("P2", _("Free"), data[3]))
				else:
					info.append(self.formatLine("P2", _("Not currently mounted.")))
				count += 1
		else:
			info.append(self.formatLine("S1", _("No network storage detected.")))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Storage / Disk Information"


class InformationStreaming(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Streaming Tuner Information"))
		self.skinName.insert(0, "InformationStreaming")
		self.skinName.insert(1, "StreamingInformation")
		self["key_yellow"] = StaticText(_("Stop Auto Refresh"))
		self["key_blue"] = StaticText()
		self["refreshActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyToggleAutoRefresh, _("Toggle auto refresh On/Off"))
		}, prio=0, description=_("Streaming Information Actions"))
		self["streamActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.keyStopStreams, _("Stop streams"))
		}, prio=0, description=_("Streaming Information Actions"))
		self["streamActions"].setEnabled(False)
		self.autoRefresh = True

	def keyToggleAutoRefresh(self):
		self.autoRefresh = not self.autoRefresh
		self["key_yellow"].setText(_("Stop Auto Refresh") if self.autoRefresh else _("Start Auto Refresh"))

	def keyStopStreams(self):
		if eStreamServer.getInstance().getConnectedClients():
			eStreamServer.getInstance().stopStream()
		if eRTSPStreamServer.getInstance().getConnectedClients():
			eRTSPStreamServer.getInstance().stopStream()

	def displayInformation(self):
		info = []
		info.append(self.formatLine("H", _("Streaming tuner information for %s %s") % getBoxDisplayName()))
		info.append("")
		clientList = eStreamServer.getInstance().getConnectedClients() + eRTSPStreamServer.getInstance().getConnectedClients()
		if clientList:
			self["key_blue"].setText(_("Stop Streams"))
			self["streamActions"].setEnabled(True)
			for count, client in enumerate(clientList):
				# print("[Information] DEBUG: Client data '%s'." % str(client))
				if count:
					info.append("")
				info.append(self.formatLine("S", f"{_("Client")}  -  {count + 1}"))
				info.append(self.formatLine("P1", _("Service reference"), client[1]))
				info.append(self.formatLine("P1", _("Service name"), ServiceReference(client[1]).getServiceName() or _("Unknown service!")))
				info.append(self.formatLine("P1", _("IP address"), client[0][7:] if client[0].startswith("::ffff:") else client[0]))
				info.append(self.formatLine("P1", _("Transcoding"), _("Yes") if client[2] else _("No")))
		else:
			self["key_blue"].setText("")
			self["streamActions"].setEnabled(False)
			info.append(self.formatLine("P1", _("No tuners are currently streaming.")))
		self["information"].setText("\n".join(info))
		if self.autoRefresh:
			self.informationTimer.start(AUTO_REFRESH_TIME)

	def getSummaryInformation(self):
		return "Streaming Tuner Information"


class InformationSystem(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.baseTitle = _("System Information")
		self.setTitle(self.baseTitle)
		self.skinName.insert(0, "InformationSystem")
		self.skinName.insert(1, "SystemInformation")
		self["key_menu"] = StaticText(_("MENU"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["systemActions"] = HelpableActionMap(self, ["MenuActions", "ColorActions", "NavigationActions"], {
			"menu": (self.keyShowSystemMenu, _("Show selection for system information screen")),
			"yellow": (self.keyPreviousSystem, _("Show previous system information screen")),
			"blue": (self.keyNextSystem, _("Show next system information screen")),
			"left": (self.keyPreviousSystem, _("Show previous system information screen")),
			"right": (self.keyNextSystem, _("Show next system information screen"))
		}, prio=0, description=_("System Information Actions"))
		self.systemCommands = [
			("CPU", None, "/proc/cpuinfo"),
			("Top Processes", ("/usr/bin/top", "/usr/bin/top", "-b", "-n", "1"), None),
			("Current Processes", ("/bin/ps", "/bin/ps", "-l"), None),
			("Kernel Modules", None, "/proc/modules"),
			("Kernel Messages", ("/bin/dmesg", "/bin/dmesg"), None),
			("System Messages", None, "/home/root/logs/messages"),
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

	def keyShowSystemMenu(self):
		def keyShowSystemMenuCallBack(selectedIndex):
			if isinstance(selectedIndex, int):
				self.systemCommandsIndex = selectedIndex
				self.displayInformation()
				self.informationTimer.start(25)

		choices = [(systemCommand[0], index) for index, systemCommand in enumerate(self.systemCommands)]
		self.session.openWithCallback(keyShowSystemMenuCallBack, MessageBox, text=_("Select system information to view:"), list=choices, windowTitle=self.baseTitle)

	def keyPreviousSystem(self):
		self.systemCommandsIndex = (self.systemCommandsIndex - 1) % self.systemCommandsMax
		self.displayInformation()
		self.informationTimer.start(25)

	def keyNextSystem(self):
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
				if self.systemCommandsIndex == 0:  # CPU option needs to be parsed.
					info = []
					for line in self.info:
						if line:
							data = [x.strip() for x in line.split(":")]
							info.append(f"{data[0]}:|{data[1]}")
						else:
							info.append("")
					self.info = info
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


class InformationTranslation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Translation Information"))
		self.skinName.insert(0, "InformationTranslation")
		self.skinName.insert(1, "TranslationInformation")

	def displayInformation(self):
		info = []
		info.append(self.formatLine("H", _("Translation information for %s %s") % getBoxDisplayName()))
		info.append("")
		translateInfo = _("TRANSLATOR_INFO")
		if translateInfo != "TRANSLATOR_INFO":
			info.append(self.formatLine("H", _("Translation information")))
			info.append("")
			translateInfo = translateInfo.split("\n")
			for translate in translateInfo:
				info.append(self.formatLine("P1", translate))
			info.append("")
		translateInfo = _("").split("\n")  # This is deliberate to dump the translation information.
		for translate in translateInfo:
			if not translate:
				continue
			translate = [x.strip() for x in translate.split(":", 1)]
			if len(translate) == 1:
				translate.append("")
			info.append(self.formatLine("P1", translate[0], translate[1]))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Translation Information"


class InformationTuner(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Tuner Information"))
		self.skinName.insert(0, "InformationTuner")
		self.skinName.insert(1, "TunerInformation")
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
		info.append(self.formatLine("H", _("Tuner information for %s %s") % getBoxDisplayName()))
		info.append("")
		for count, tunerData in enumerate(self.tunerList):
			if count:
				info.append("")
			tuner = tunerData["start"] if tunerData["start"] == tunerData["end"] else f"{tunerData["start"]} - {tunerData["end"]}"
			info.append(self.formatLine("S", f"Tuner {tuner}"))
			if self.extraSpacing:
				info.append("")
			name = tunerData.get("name")
			if name:
				info.append(self.formatLine("P1", _("Name"), name))
			model = tunerData.get("model")
			if model:
				info.append(self.formatLine("P1", _("Type / Model"), model))
			broadcast = tunerData.get("broadcast")
			if broadcast:
				info.append(self.formatLine("P1", _("Broadcast systems"), broadcast))
			capabilities = tunerData.get("capabilities")
			if capabilities:
				info.append(self.formatLine("P1", _("Multistream"), (_("Yes") if "MULTISTREAM" in capabilities else _("No"))))
			frequency = tunerData.get("frequency")
			if frequency:
				data = parseValues(frequency)
				info.append(self.formatLine("P1", _("Frequency range"), f"{data["min"]}  -  {data["max"]}  (Step {data["stepsize"]})"))
			symbolrate = tunerData.get("symbolrate")
			if symbolrate:
				data = parseValues(symbolrate)
				info.append(self.formatLine("P1", _("Symbol rate"), f"{data["min"]}  -  {data["max"]}"))
			FEC = extractModes(capabilities, "FEC")
			if FEC:
				info.append(self.formatLine("P1", _("FEC modes"), ", ".join(FEC)))
			QAM = sortQAM(extractModes(capabilities, "QAM"))
			if QAM:
				info.append(self.formatLine("P1", _("Modulation modes"), ", ".join(QAM)))
			api = tunerData.get("api")
			if api:
				info.append(self.formatLine("P1", _("%s version") % "DVB API", api))
		if info:
			info.append("")
		info.append(self.formatLine("S", _("Transcoding"), (_("Yes") if BoxInfo.getItem("transcoding") else _("No"))))
		info.append(self.formatLine("S", _("MultiTranscoding"), (_("Yes") if BoxInfo.getItem("multitranscoding") else _("No"))))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Tuner Information"


class InformationTesting(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Testing Information"))
		self.skinName.insert(0, "InformationTesting")
		self.skinName.insert(1, "TestingInformation")
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
