from os import listdir, sync
from os.path import exists, join as pathjoin, normpath

from enigma import eConsoleAppContainer

from Components.config import ConfigSubsection, ConfigYesNo, config
# from Components.Harddisk import harddiskmanager
from Components.SystemInfo import BoxInfo
from Tools.Directories import SCOPE_LIBDIR, fileReadLines, fileWriteLine, resolveFilename

MODULE_NAME = __name__.split(".")[-1]

opkgDestinations = []
opkgStatusPath = ""


def opkgExtraDestinations():
	return " ".join(["--add-dest %s:%s" % (x, x) for x in opkgDestinations])


def opkgAddDestination(mountpoint):
	global opkgDestinations
	if mountpoint not in opkgDestinations:
		opkgDestinations.append(mountpoint)
		print("[Opkg] Added to OPKG destinations: '%s'." % mountpoint)


def onPartitionChange(why, part):
	global opkgDestinations
	global opkgStatusPath
	mountpoint = normpath(part.mountpoint)
	if mountpoint and mountpoint != "/":
		if why == "add":
			if opkgStatusPath == "":
				opkgStatusPath = "var/lib/opkg/status"  # Recent opkg versions.
				if not exists(pathjoin("/", opkgStatusPath)):
					opkgStatusPath = resolveFilename(SCOPE_LIBDIR, "opkg/status")  # Older opkg versions.
			if exists(pathjoin(mountpoint, opkgStatusPath)):
				opkgAddDestination(mountpoint)
		elif why == "remove":
			if mountpoint in opkgDestinations:
				opkgDestinations.remove(mountpoint)
				print("[Opkg] Removed from OPKG destinations: '%s'." % mountpoint)


def listsDirPath():
	for line in fileReadLines("/etc/opkg/opkg.conf", default=[], source=MODULE_NAME):
		if line.startswith("option"):
			line = line.strip().split()
			if len(line) == 3 and line[1] == "lists_dir":
				return line[2]
	return "/var/lib/opkg/lists"


def enumFeeds():
	for file in listdir("/etc/opkg"):
		if file.endswith("-feed.conf"):
			for line in fileReadLines(pathjoin("/etc/opkg", file), default=[], source=MODULE_NAME):
				line = line.strip().split()
				if len(line) >= 2:
					yield line[1]


def enumPlugins(filterStart=""):
	listsDir = listsDirPath()
	for feed in enumFeeds():
		package = None
		for line in fileReadLines(pathjoin(listsDir, feed), default=[], source=MODULE_NAME):
			if line.startswith("Package: "):
				package = line.split(":", 1)[1].strip()
				version = ""
				description = ""
				if config.misc.extraopkgpackages.value:
					if package.startswith(filterStart) and not package.endswith("--pycache--"):
						continue
				else:
					if package.startswith(filterStart) and not (package.endswith("-dbg") or package.endswith("-dev") or package.endswith("-doc") or package.endswith("-meta") or package.endswith("-po") or package.endswith("-src") or package.endswith("-staticdev") or package.endswith("--pycache--")):
						continue
				package = None
			if package is None:
				continue
			if line.startswith("Version: "):
				version = line.split(":", 1)[1].strip()
			elif line.startswith("Description: "):
				description = line.split(":", 1)[1].strip()
			elif description and line.startswith(" "):
				description = "%s%s" % (description, line)
			elif len(line) <= 1:
				yield package, version, description
				package = None


if __name__ == "__main__":
	for plugin in enumPlugins("enigma"):
		print(plugin)

# harddiskmanager.on_partition_list_change.append(onPartitionChange)
# for part in harddiskmanager.getMountedPartitions():
# 	onPartitionChange("add", part)


class OpkgComponent:
	CMD_INSTALL = 0
	CMD_LIST = 1
	CMD_REMOVE = 2
	CMD_UPDATE = 3
	CMD_UPGRADE = 4
	CMD_UPGRADE_LIST = 5
	CMD_LIST_INSTALLED = 6
	CMD_INFO = 7
	CMD_REFRESH = 8
	CMD_REFRESH_LIST = 9
	CMD_REFRESH_UPDATES = 10
	CMD_REFRESH_INFO = 11
	CMD_LIST_UPDATES = 12
	CMD_REFRESH_INSTALLABLE = 13
	CMD_LIST_INSTALLABLE = 14
	CMD_REPLACE = 15
	# NOTE: The following commands are internal use only and should NOT be used by external modules!
	CMD_CLEAN = 100
	CMD_CLEAN_UPDATE = 101
	CMD_SET_FLAG = 102
	CMD_UPGRADE_EXCLUDE = 103
	CMD_RESET_FLAG = 104
	CMD_CLEAN_REFRESH = 105

	CMD_NAMES = {
		CMD_CLEAN_REFRESH: "CMD_CLEAN_REFRESH",
		CMD_REFRESH: "CMD_REFRESH",
		CMD_REFRESH_LIST: "CMD_REFRESH_LIST",
		CMD_LIST: "CMD_LIST",
		CMD_LIST_INSTALLED: "CMD_LIST_INSTALLED",
		CMD_REFRESH_UPDATES: "CMD_REFRESH_UPDATES",
		CMD_LIST_UPDATES: "CMD_LIST_UPDATES",
		CMD_REFRESH_INSTALLABLE: "CMD_REFRESH_INSTALLABLE",
		CMD_LIST_INSTALLABLE: "CMD_LIST_INSTALLABLE",
		CMD_REFRESH_INFO: "CMD_REFRESH_INFO",
		CMD_INFO: "CMD_INFO",
		CMD_REMOVE: "CMD_REMOVE",
		CMD_INSTALL: "CMD_INSTALL",
		CMD_REPLACE: "CMD_REPLACE",
		CMD_UPDATE: "CMD_UPDATE",
		CMD_UPGRADE: "CMD_UPGRADE",
		CMD_SET_FLAG: "CMD_SET_FLAG",
		CMD_RESET_FLAG: "CMD_RESET_FLAG",
		CMD_UPGRADE_EXCLUDE: "CMD_UPGRADE_EXCLUDE",  # This should now be controllable via the new "options" dictionary item.
		CMD_UPGRADE_LIST: "CMD_UPGRADE_LIST",  # Should this now be CMD_LIST_UPDATES?
		CMD_CLEAN: "CMD_CLEAN",  # This should be removed.
		CMD_CLEAN_UPDATE: "CMD_CLEAN_UPDATE"  # This should now be CMD_CLEAN_REFRESH.
	}

	CMD_TABLE = {
		CMD_CLEAN_REFRESH: ["clean", "update"],
		CMD_REFRESH: ["update"],
		CMD_REFRESH_LIST: ["update", "list"],
		CMD_LIST: ["list"],
		CMD_LIST_INSTALLED: ["list-installed"],
		CMD_REFRESH_UPDATES: ["update", "list-upgradable"],
		CMD_LIST_UPDATES: ["list-upgradable"],
		CMD_REFRESH_INSTALLABLE: ["update", "list", "list-installed"],
		CMD_LIST_INSTALLABLE: ["list-installed"],
		CMD_REFRESH_INFO: ["update", "info"],
		CMD_INFO: ["info"],
		CMD_REMOVE: ["remove"],
		CMD_INSTALL: ["install"],
		CMD_REPLACE: ["remove", "install"],
		CMD_UPDATE: ["install"],
		CMD_UPGRADE: ["upgrade"],
		CMD_SET_FLAG: ["flag", "hold"],
		CMD_RESET_FLAG: ["flag", "ok"]
	}

	EVENT_INSTALL = 0
	EVENT_DOWNLOAD = 1
	EVENT_INFLATING = 2
	EVENT_CONFIGURING = 3
	EVENT_REMOVE = 4
	EVENT_UPVERSION = 5
	EVENT_UPGRADE = 6
	EVENT_UPDATED = 7
	EVENT_DESELECTED = 8
	EVENT_LISTITEM = 9
	EVENT_DONE = 10
	EVENT_ERROR = 11
	EVENT_MODIFIED = 12
	EVENT_LIST_DONE = 13
	EVENT_LIST_INSTALLED_DONE = 14
	EVENT_LIST_UPDATES_DONE = 15
	EVENT_LIST_INSTALLABLE_DONE = 16
	EVENT_INFO_DONE = 17
	EVENT_REMOVE_DONE = 18
	EVENT_DOWNLOAD_DONE = 19
	EVENT_UPDATE_DONE = 20
	EVENT_BOOTLOGO_FOUND = 21
	EVENT_SETTINGS_FOUND = 22
	EVENT_LOG = 23
	EVENT_OPKG_MISMATCH = 24
	EVENT_CANT_INSTALL = 25
	EVENT_NETWORK_ERROR = 26
	EVENT_REFRESH_DONE = 27

	EVENT_NAMES = {
		EVENT_INSTALL: "EVENT_INSTALL",
		EVENT_DOWNLOAD: "EVENT_DOWNLOAD",
		EVENT_INFLATING: "EVENT_INFLATING",
		EVENT_CONFIGURING: "EVENT_CONFIGURING",
		EVENT_REMOVE: "EVENT_REMOVE",
		EVENT_UPVERSION: "EVENT_UPVERSION",
		EVENT_UPGRADE: "EVENT_UPGRADE",
		EVENT_UPDATED: "EVENT_UPDATED",
		EVENT_DESELECTED: "EVENT_DESELECTED",
		EVENT_LISTITEM: "EVENT_LISTITEM",
		EVENT_DONE: "EVENT_DONE",
		EVENT_ERROR: "EVENT_ERROR",
		EVENT_MODIFIED: "EVENT_MODIFIED",
		EVENT_LIST_DONE: "EVENT_LIST_DONE",
		EVENT_LIST_INSTALLED_DONE: "EVENT_LIST_INSTALLED_DONE",
		EVENT_LIST_UPDATES_DONE: "EVENT_LIST_UPDATES_DONE",
		EVENT_LIST_INSTALLABLE_DONE: "EVENT_LIST_INSTALLABLE_DONE",
		EVENT_INFO_DONE: "EVENT_INFO_DONE",
		EVENT_REMOVE_DONE: "EVENT_REMOVE_DONE",
		EVENT_DOWNLOAD_DONE: "EVENT_DOWNLOAD_DONE",
		EVENT_UPDATE_DONE: "EVENT_UPDATE_DONE",
		EVENT_BOOTLOGO_FOUND: "EVENT_BOOTLOGO_FOUND",
		EVENT_SETTINGS_FOUND: "EVENT_SETTINGS_FOUND",
		EVENT_LOG: "EVENT_LOG",
		EVENT_OPKG_MISMATCH: "EVENT_OPKG_MISMATCH",
		EVENT_CANT_INSTALL: "EVENT_CANT_INSTALL",
		EVENT_NETWORK_ERROR: "EVENT_NETWORK_ERROR",
		EVENT_REFRESH_DONE: "EVENT_REFRESH_DONE"
	}

	LIST_KEYS = [
		"Package",
		"Version",
		"Description"
	]
	UPDATE_KEYS = [
		"Package",
		"Version",
		"Update"
	]

	def __init__(self, opkg="/usr/bin/opkg"):
		self.opkg = opkg
		self.console = eConsoleAppContainer()
		self.listCommands = ("list", "list-installed", "list-upgradable", "info")
		self.logCommands = ("install", "remove")
		self.callbackList = []
		self.removed = []
		self.installable = []  # Note this list is NOT reset between runs and steps.  It is filled and updated on every list command and used to calculate upgradeable packages.
		self.downloaded = []
		self.updated = []
		self.fetchedList = []
		self.excludeList = []
		self.currentCommand = None
		self.nextCommand = None
		self.debugMode = None

	def startCmd(self, cmd, args=None):
		extra = []
		consoleBuffer = 2048
		for destination in opkgDestinations:
			extra.append("--add-dest")
			extra.append("%s:%s" % (destination, destination))
		if cmd == self.CMD_UPDATE and config.misc.opkgcleanmode.value:
			cmd = self.CMD_CLEAN
		elif cmd == self.CMD_UPGRADE and self.excludeList:
			cmd = self.CMD_SET_FLAG
		self.currentCommand = cmd
		if cmd == self.CMD_CLEAN:
			argv = ["clean"]
			self.nextCommand = (self.CMD_CLEAN_UPDATE, args)
		elif cmd in (self.CMD_UPDATE, self.CMD_CLEAN_UPDATE):
			argv = extra + ["update"]
		elif cmd == self.CMD_UPGRADE:
			command = extra + ["upgrade"]
			if "testMode" in args and args["testMode"]:
				command.insert(0, "--noaction")
			argv = command
		elif cmd == self.CMD_SET_FLAG:
			argv = ["flag", "hold"] + [x[0] for x in self.excludeList]
			self.nextCommand = (self.CMD_UPGRADE_EXCLUDE, args)
		elif cmd == self.CMD_UPGRADE_EXCLUDE:
			command = extra + ["upgrade"]
			if "testMode" in args and args["testMode"]:
				command.insert(0, "--noaction")
			argv = command
			self.nextCommand = (self.CMD_RESET_FLAG, args)
		elif cmd == self.CMD_RESET_FLAG:
			packages = [x[0] for x in self.excludeList]
			argv = ["flag", "ok"] + packages
			deferred = []
			for package in packages:
				if package.startswith("busybox"):
					deferred.append(package)
			if deferred:
				deferred = [self.opkg, "install", "--force-reinstall"] + deferred
				fileWriteLine("/etc/enigma2/.busybox_update_required", " ".join(deferred), source=MODULE_NAME)
		elif cmd == self.CMD_LIST:
			self.fetchedList = []
			self.excludeList = []
			packages = args["package"].split() if args and "package" in args else []
			argv = extra + ["list"] + packages
		elif cmd == self.CMD_INSTALL:
			argv = ["--force-overwrite", "install"] + args["package"].split()
		elif cmd == self.CMD_REMOVE:
			argv = ["remove"] + args["package"].split()
		elif cmd == self.CMD_UPGRADE_LIST:
			self.fetchedList = []
			self.excludeList = []
			argv = extra + ["list-upgradable"]
		elif cmd == self.CMD_LIST_INSTALLED:
			self.fetchedList = []
			self.excludeList = []
			packages = args["package"].split() if args and "package" in args else []
			argv = extra + ["list-installed"] + packages
		if cmd == self.CMD_INFO:
			argv = ["info"]
			consoleBuffer = 131072
			self.console.setBufferSize(128 * 1024)
		print("[Opkg] Executing '%s' with '%s'." % (self.opkg, " ".join(argv)))
		self.cache = ""
		self.cachePtr = -1
		self.console.setBufferSize(consoleBuffer)
		self.console.dataAvail.append(self.cmdData)
		self.console.appClosed.append(self.cmdFinished)
		argv.insert(0, self.opkg)
		if self.console.execute(self.opkg, *argv):
			self.cmdFinished(-1)

	def cmdData(self, data):
		data = data.decode("UTF-8", "ignore") if isinstance(data, bytes) else data
		self.cache = "%s%s" % (self.cache, data)
		if self.currentCommand == self.CMD_INFO:
			return
		while True:
			linePtr = self.cache.find("\n", self.cachePtr + 1)
			if linePtr == -1:
				break
			self.parseLine(self.cache[self.cachePtr + 1:linePtr])
			self.cachePtr = linePtr

	def parseLine(self, line):
		# print("[Opkg] DEBUG: Line='%s'." % line)
		if not line or line.startswith(" "):  # Skip empty or continuation lines.
			return
		if self.currentCommand in (self.CMD_LIST, self.CMD_LIST_INSTALLED, self.CMD_UPGRADE_LIST):
			argv = line.split(" - ", 2)
			argc = len(argv)
			if not line.startswith("Not selecting "):
				if self.currentCommand == self.CMD_UPGRADE_LIST and self.isExcluded(argv[0]):
					self.excludeList.append(argv)
				else:
					self.fetchedList.append(argv)
					self.callCallbacks(self.EVENT_LISTITEM, argv)
			return
		try:
			argv = line.split()
			argc = len(argv)
			if line.startswith("Not selecting "):
				self.callCallbacks(self.EVENT_DESELECTED, argv[2])
			elif line.startswith("Downloading "):
				self.callCallbacks(self.EVENT_DOWNLOAD, argv[1])
			elif line.startswith("Updated source "):
				self.callCallbacks(self.EVENT_UPDATED, argv[2])
			elif line.startswith("Upgrading ") and argc == 8:
				self.callCallbacks(self.EVENT_UPVERSION, argv[1])
			elif line.startswith("Upgrading ") and argc == 5:
				self.callCallbacks(self.EVENT_UPGRADE, argv[1])
			elif line.startswith("Installing "):
				self.callCallbacks(self.EVENT_INSTALL, argv[1])
			elif line.startswith("Removing ") and not line.startswith("Removing obsolete file "):
				self.callCallbacks(self.EVENT_REMOVE, argv[1])
			elif line.startswith("Configuring "):
				self.callCallbacks(self.EVENT_CONFIGURING, argv[1])
			elif line.startswith("An error occurred"):
				self.callCallbacks(self.EVENT_ERROR, None)
			elif line.startswith("Failed to download"):
				self.callCallbacks(self.EVENT_ERROR, None)
			elif line.startswith("opkg_download: ERROR:"):
				self.callCallbacks(self.EVENT_ERROR, None)
			elif line.find("Configuration file '") >= 0:
				# Note: the config file update question doesn't end with a newline, so
				# if we get multiple config file update questions, the next ones
				# don't necessarily start at the beginning of a line.
				self.callCallbacks(self.EVENT_MODIFIED, line.split(" '", 3)[1][:-1])
		except IndexError as err:
			print("[Opkg] Error: Failed to parse line '%s'!  (%s)" % (line, str(err)))

	def isExcluded(self, item):
		if item.find("busybox") > -1:
			exclude = True
		elif item.find("-settings-") > -1 and not config.plugins.softwaremanager.overwriteSettingsFiles.value:
			exclude = True
		elif item.find("kernel-module-") > -1 and not config.plugins.softwaremanager.overwriteDriversFiles.value:
			exclude = True
		elif item.find("-softcams-") > -1 and not config.plugins.softwaremanager.overwriteEmusFiles.value:
			exclude = True
		elif item.find("-picons-") > -1 and not config.plugins.softwaremanager.overwritePiconsFiles.value:
			exclude = True
		elif item.find("-bootlogo") > -1 and not config.plugins.softwaremanager.overwriteBootlogoFiles.value:
			exclude = True
		elif item.find("%s-spinner" % BoxInfo.getItem("distro")) > -1 and not config.plugins.softwaremanager.overwriteSpinnerFiles.value:
			exclude = True
		else:
			exclude = False
		return exclude

	def cmdFinished(self, retVal):
		self.console.dataAvail.remove(self.cmdData)
		self.console.appClosed.remove(self.cmdFinished)
		if config.crash.debugOpkg.value and self.currentCommand != self.CMD_INFO:
			print("[Opkg] Opkg command '%s' output:\n%s" % (self.getCommandText(self.currentCommand), self.cache))
		if self.nextCommand:
			cmd, args = self.nextCommand
			self.nextCommand = None
			self.startCmd(cmd, args)
		else:
			if self.currentCommand == self.CMD_INFO and retVal == 0:
				self.parseInfo(self.cache)
				return
			self.callCallbacks(self.EVENT_DONE if retVal == 0 else self.EVENT_ERROR)

	def callCallbacks(self, event, parameter=None):
		for callback in self.callbackList:
			callback(event, parameter)

	def addCallback(self, callback):
		if callback not in self.callbackList:
			self.callbackList.append(callback)
		else:
			print("[Opkg] Error: Callback '%s' already exists!" % str(callback))

	def removeCallback(self, callback):
		if callback in self.callbackList:
			self.callbackList.remove(callback)
		else:
			print("[Opkg] Error: Callback '%s' does not exist!" % str(callback))

	def getFetchedList(self):
		return self.fetchedList

	def getExcludeList(self):
		return self.excludeList

	def stop(self):
		self.console.kill()

	def isRunning(self):
		return self.console.running()

	def write(self, what):
		if what:
			if not what.endswith("\n"):  # We except unterminated commands.
				what = "%s\n" % what
			self.console.write(what, len(what))

	def getCommandText(self, command):
		return self.CMD_NAMES.get(command, "None")

	def getEventText(self, event):
		return self.EVENT_NAMES.get(event, "None")

	def parseInfo(self, data=None):
		ret = []
		try:
			packageInfo = {}
			if data:
				lines = data.splitlines()
			for line in lines:
				if line.startswith("Package:"):
					package = line.split(":", 1)[1].strip()
					description = ""
					depends = ""
					status = ""
					section = ""
					installed = "0"
					architecture = ""
					size = ""
					maintainer = ""
					version = ""
					continue
				if package is None:
					continue
				if line.startswith("Status:"):
					status = line.split(":", 1)[1].strip()
					if " installed" in status.lower():
						installed = "1"
				elif line.startswith("Section:"):
					section = line.split(":", 1)[1].strip()
				elif line.startswith("Architecture:"):
					architecture = line.split(":", 1)[1].strip()
				elif line.startswith("Size:"):
					size = line.split(":", 1)[1].strip()
				elif line.startswith("Maintainer:"):
					maintainer = line.split(":", 1)[1].strip()
				elif line.startswith("Depends:"):
					depends = line.split(":", 1)[1].strip()
				elif line.startswith("Version:"):
					version = line.split(":", 1)[1].strip()
				# TDOD : check description
				elif line.startswith("Description:"):
					description = line.split(":", 1)[1].strip()
				elif description and line.startswith(" "):
					description += line[:-1]
				elif len(line) <= 1:
					d = description.split(" ", 3)
					if len(d) > 3:
						if d[1] == "version":
							description = d[3]
						# TDOD : check this
						if description.startswith("gitAUTOINC"):
							description = description.split(" ", 1)[1]
					if package in packageInfo:
						v = packageInfo[package][0]
						packageInfo[package][3] = v
						packageInfo[package][2] = "1"
						packageInfo[package][0] = version
					else:
						packageInfo.update({package: [version, description.strip(), installed, "0", section, architecture, size, maintainer, depends]})
					package = None
			keys = sorted(packageInfo.keys())
			for name in keys:
				ret.append({
					"name": name,
					"version": packageInfo[name][0],
					"description": packageInfo[name][1],
					"installed": packageInfo[name][2],
					"update": packageInfo[name][3],
					"section": packageInfo[name][4],
					"architecture": packageInfo[name][5],
					"size": packageInfo[name][6],
					"maintainer": packageInfo[name][7],
					"depends": packageInfo[name][8]
				})
		except IndexError as err:
			print("[Opkg] parseInfo error: '%s'." % str(err))
		self.callCallbacks(self.EVENT_LIST_DONE if ret else self.EVENT_ERROR, ret)


# The following code is a proposal for an updated opkg interface.


	def runCmd(self, cmd, args=None):
		self.currentCommand = cmd
		if args is None:
			args = {}
		self.commands = self.CMD_TABLE.get(cmd, ["help"])[:]  # Copy the command list so it can be manipulated.
		if config.misc.opkgcleanmode.value and self.commands[0] == "update":
			self.commands.insert(0, "clean")
		self.args = args
		self.step = 0
		self.steps = len(self.commands)
		plural = "s" if self.steps > 1 else ""
		print("[Opkg] The command '%s' has %d step%s %s." % (self.getCommandText(cmd), self.steps, plural, self.commands))
		self.runStep()

	def runStep(self):
		self.step += 1
		opkgCmd = self.commands.pop(0)
		self.opkgCmd = opkgCmd
		opkgArgs = [self.opkg, self.opkg, opkgCmd]
		self.debugMode = "debugMode" in self.args and self.args["debugMode"]
		if "testMode" in self.args and self.args["testMode"]:
			opkgArgs += ["--noaction"]
		if "options" in self.args:
			if self.currentCommand != self.CMD_REPLACE and opkgCmd == "remove":
				opkgArgs += self.args["options"]
		for destination in opkgDestinations:
			opkgArgs += ["--add-dest", "%s:%s" % (destination, destination)]
		if "arguments" in self.args and opkgCmd not in ("clean", "update"):
			if self.currentCommand == self.CMD_REPLACE:
				opkgArgs += [self.args["arguments"][0]] if opkgCmd == "remove" else [self.args["arguments"][1]]
			else:
				opkgArgs += self.args["arguments"]
		if opkgCmd in ("list", "list-installed", "list-upgradable", "info"):
			dataBuffer = 131072  # 128 * 1024 = 128 KB data buffer.
		else:
			dataBuffer = 2048  # 2 KB data buffer.
		msg = " in debug mode" if self.debugMode else ""
		print("[Opkg] Step %d of %d: Executing '%s' with command line arguments '%s'%s." % (self.step, self.steps, opkgArgs[0], " ".join(opkgArgs[1:]), msg))
		self.removed = []
		self.downloaded = []
		self.updated = []
		self.dataCache = ""
		self.dataCachePtr = -1
		self.console.setBufferSize(dataBuffer)
		self.console.dataAvail.append(self.consoleDataAvail)
		self.console.appClosed.append(self.consoleAppClosed)
		if self.console.execute(*opkgArgs):
			self.consoleAppClosed(-1)

	def consoleDataAvail(self, data):
		def consoleDataParse(line):
			if not line:  # Skip empty lines. (Continuation lines should only occur in list commands.)
				return
			try:
				argv = line.split()
				argc = len(argv)
				if line.startswith("Not selecting "):
					self.callCallbacks(self.EVENT_DESELECTED, argv[2])
				elif line.startswith("Downloading "):
					self.callCallbacks(self.EVENT_DOWNLOAD, argv[1][:-1])
				elif line.startswith("Updated source "):
					self.callCallbacks(self.EVENT_UPDATED, argv[2][1:-2])
				elif line.startswith("Upgrading ") and argc == 8:
					self.updated.append(argv[2])
					self.callCallbacks(self.EVENT_UPVERSION, argv[1])
				elif line.startswith("Upgrading ") and argc == 5:
					self.callCallbacks(self.EVENT_UPGRADE, argv[1])
				elif line.startswith("Installing "):
					self.downloaded.append(argv[1])
					self.callCallbacks(self.EVENT_INSTALL, argv[1])
				# elif line.startswith("Removing ") and not line.startswith("Removing obsolete file "):
				elif line.startswith("Removing "):
					self.removed.append(argv[1])
					self.callCallbacks(self.EVENT_REMOVE, argv[1])
				elif line.startswith("Configuring "):
					self.callCallbacks(self.EVENT_CONFIGURING, argv[1][:-1])
				elif line.startswith("An error occurred"):
					self.callCallbacks(self.EVENT_ERROR, (self.currentCommand, self.opkgCmd))
				elif line.startswith("Failed to download"):
					self.callCallbacks(self.EVENT_ERROR, (self.currentCommand, self.opkgCmd))
				elif line.startswith("opkg_download: ERROR:"):
					self.callCallbacks(self.EVENT_ERROR, (self.currentCommand, self.opkgCmd))
				elif line.startswith(" * pkg_verify: File size mismatch:"):
					self.callCallbacks(self.EVENT_OPKG_MISMATCH, (self.opkgCmd, argv[5], argv[7], argv[10]))
				elif line.startswith(" * opkg_solver_install: Cannot install package "):
					self.callCallbacks(self.EVENT_CANT_INSTALL, (self.opkgCmd, argv[5][:-1]))
				elif line.startswith(" * opkg_download_backend: Failed to download"):
					self.callCallbacks(self.EVENT_NETWORK_ERROR, (self.opkgCmd, argv[5][:-1], argv[8][:-1]))
				elif line.find("Configuration file '") >= 0:
					# Note: the config file update question doesn't end with a newline, so
					# if we get multiple config file update questions, the next ones
					# don't necessarily start at the beginning of a line.
					self.callCallbacks(self.EVENT_MODIFIED, line.split(" '", 3)[1][:-1])
			except IndexError as err:
				print("[Opkg] Error: Failed to parse line '%s'!  (%s)" % (line, str(err)))

		data = data.decode("UTF-8", "ignore") if isinstance(data, bytes) else data
		self.dataCache = "%s%s" % (self.dataCache, data)
		if self.opkgCmd not in self.listCommands:
			while True:
				linePtr = self.dataCache.find("\n", self.dataCachePtr + 1)
				if linePtr == -1:
					break
				consoleDataParse(self.dataCache[self.dataCachePtr + 1:linePtr])
				self.dataCachePtr = linePtr

	def consoleAppClosed(self, retVal):
		self.console.dataAvail.remove(self.consoleDataAvail)
		self.console.appClosed.remove(self.consoleAppClosed)
		sync()
		if self.debugMode or config.crash.debugOpkg.value or self.opkgCmd not in self.listCommands:
			if self.dataCache:
				print("[Opkg] Opkg command '%s' output:" % self.opkgCmd)
				for line in self.dataCache.splitlines():
					print("[Opkg]    %s" % line)
				if self.opkgCmd in self.logCommands:
					self.callCallbacks(self.EVENT_LOG, self.dataCache)
			else:
				print("[Opkg] Opkg command '%s' resulted in no output." % self.opkgCmd)
		elif self.opkgCmd in self.listCommands:
			print("[Opkg] Opkg command '%s' output suppressed to not flood the log file." % self.opkgCmd)
		if retVal == 0:
			if self.opkgCmd == "update":
				self.callCallbacks(self.EVENT_REFRESH_DONE, retVal)
			elif self.opkgCmd == "list":
				packages = self.parseListData(self.dataCache, self.LIST_KEYS, False)
				self.installable = packages[:]
				if self.currentCommand in (self.CMD_REFRESH_LIST, self.CMD_LIST):
					self.callCallbacks(self.EVENT_LIST_DONE, packages)
			elif self.opkgCmd == "list-installed":
				packages = self.parseListData(self.dataCache, self.LIST_KEYS, True)
				if self.currentCommand == self.CMD_LIST_INSTALLED:
					self.callCallbacks(self.EVENT_LIST_INSTALLED_DONE, packages)
				elif self.currentCommand in (self.CMD_REFRESH_INSTALLABLE, self.CMD_LIST_INSTALLABLE):
					installed = []
					for package in packages:
						packageFile = package["Package"]
						if packageFile.startswith("enigma2-plugin-bootlogo-"):
							self.callCallbacks(self.EVENT_BOOTLOGO_FOUND, packageFile)
						elif packageFile.startswith("enigma2-plugin-settings-"):
							self.callCallbacks(self.EVENT_SETTINGS_FOUND, packageFile)
						installed.append(packageFile)
					packages = []
					for package in self.installable:
						if package["Package"] not in installed:
							packages.append(package)
					self.callCallbacks(self.EVENT_LIST_INSTALLABLE_DONE, packages)
			elif self.opkgCmd == "list-upgradable":
				packages = self.parseListData(self.dataCache, self.UPDATE_KEYS, True)
				self.callCallbacks(self.EVENT_LIST_UPDATES_DONE, packages)
			elif self.opkgCmd == "info":
				packages = self.parseInfoData(self.dataCache)
				for package in packages:
					if package["Installed"]:
						packageFile = package["Package"]
						if packageFile.startswith("enigma2-plugin-bootlogo-"):
							self.callCallbacks(self.EVENT_BOOTLOGO_FOUND, packageFile)
						elif packageFile.startswith("enigma2-plugin-settings-"):
							self.callCallbacks(self.EVENT_SETTINGS_FOUND, packageFile)
				self.callCallbacks(self.EVENT_INFO_DONE, packages)
			elif self.opkgCmd == "remove" and self.currentCommand == self.CMD_REPLACE:
				pass  # We are half way through a CMD_REPLACE command so do nothing.
			elif self.opkgCmd == "remove":  # This is used if the auto-dependencies are also removed.
				self.callCallbacks(self.EVENT_REMOVE_DONE, self.removed)
			elif self.opkgCmd == "install" and self.updated:
				self.callCallbacks(self.EVENT_UPDATE_DONE, self.updated)
			elif self.opkgCmd == "install" and self.downloaded:
				self.callCallbacks(self.EVENT_DOWNLOAD_DONE, self.downloaded)
			else:
				print("[Opkg] Warning: The command '%s' completed with no callback defined." % self.opkgCmd)
		elif retVal == 255:
			if self.opkgCmd == "clean":
				print("[Opkg] Opkg cache directory does not exist! Running 'update' to rebuild the cache.")
				self.runCmd(self.CMD_REFRESH)
			elif self.opkgCmd == "remove" and self.currentCommand == self.CMD_REPLACE:
				pass  # We are half way through a CMD_REPLACE command so do nothing.
			elif self.opkgCmd == "remove":  # This is used if the auto-dependencies were not able to be removed.
				self.callCallbacks(self.EVENT_REMOVE_DONE, self.removed)
		elif retVal:
			if self.opkgCmd == "update":
				self.callCallbacks(self.EVENT_REFRESH_DONE, retVal)
			else:
				self.callCallbacks(self.EVENT_ERROR, (self.currentCommand, self.opkgCmd))
		if self.commands:
			self.runStep()
		else:
			self.callCallbacks(self.EVENT_DONE, self.currentCommand)

	def parseListData(self, listData, listKeys, installed):
		data = {}
		if listData:
			lines = listData.splitlines()
			for line in lines:
				if line.startswith("Not selecting "):
					print("[Opkg] Warning: Not selecting '%s'." % line[14:])
			args = None
			for line in lines:
				if args:
					if line[:1] == " ":
						args[-1] = "%s %s" % (args[-1], line.strip())
						continue
					entry = {}
					for index, arg in enumerate(args):
						entry[listKeys[index]] = arg
					package = args[0]
					entry["Installed"] = installed
					if package in data:
						data[package].append(entry)
					else:
						data[package] = [entry]
				args = line.split(" - ", 2)
				args = [x.strip() for x in args]
		packages = []
		for package in sorted(data.keys()):
			select = 0
			if len(data[package]) > 1:
				latest = ""
				for index, entry in enumerate(data[package]):
					if entry["Version"] > latest:
						latest = entry["Version"]
						select = index
			packages.append(data[package][select])
		return packages

	def parseInfoData(self, infoData):
		data = {}
		if infoData:
			lines = infoData.splitlines()
			token = None
			entry = {}
			for line in lines:
				if line == "":
					if "Package" in entry:
						if "Size" in entry and isinstance(entry["Size"], str):
							if entry["Size"].isdigit():
								entry["Size"] = int(entry["Size"])
							else:
								print("[Opkg] Warning: Package '%s' has an invalid size of '%s'." % (entry["Package"], entry["Size"]))
								entry["Size"] = 0
						entry["Installed"] = " installed" in entry["Status"].lower()
						package = entry["Package"]
						if package in data:
							data[package].append(entry)
						else:
							data[package] = [entry]
					token = None
					entry = {}
					continue
				if token and line[:1] == " ":
					value = "%s %s" % (value, line.strip())
					entry[token] = value
					continue
				args = line.split(":", 1)
				token = args[0]
				if len(args) > 1:
					value = args[1]
					entry[token] = value.strip()
		packages = []
		for package in sorted(data.keys()):
			select = 0
			if len(data[package]) > 1:
				installed = 0
				latest = ""
				for index, entry in enumerate(data[package]):
					if entry["Installed"]:
						installed = index
					if entry["Version"] > latest:
						latest = entry["Version"]
						select = index
				if installed != select:
					data[package][select]["Update"] = data[package][select]["Version"]
				for item in data[package][installed]:
					data[package][select][item] = data[package][installed][item]
			packages.append(data[package][select])
		return packages
