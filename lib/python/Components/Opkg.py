from os import sync
from os.path import join
from time import sleep

from enigma import eConsoleAppContainer

from Components.config import config
from Components.SystemInfo import BoxInfo
from Tools.Directories import SCOPE_LIBDIR, fileReadLines, fileWriteLine, resolveFilename

MODULE_NAME = __name__.split(".")[-1]

PACKAGER = "/usr/bin/opkg"
PACKAGER_CONFIG_DIR = "/etc/opkg/"
PACKAGER_CONFIG_FILE = join(PACKAGER_CONFIG_DIR, "opkg.conf")
PACKAGER_LISTS_DIR = "/var/lib/opkg/lists/"
PACKAGER_STATUS_FILE = "/var/lib/opkg/status"


class OpkgComponent:
	CMD_CLEAN_REFRESH = 0
	CMD_REFRESH = 1
	CMD_REFRESH_LIST = 2
	CMD_LIST = 3
	CMD_REFRESH_INSTALLED = 4
	CMD_LIST_INSTALLED = 5
	CMD_REFRESH_INSTALLABLE = 6
	CMD_LIST_INSTALLABLE = 7
	CMD_REFRESH_UPDATES = 8
	CMD_LIST_UPDATES = 9
	CMD_REFRESH_INFO = 10
	CMD_INFO = 11
	CMD_REFRESH_REMOVE = 12  # This command currently has no functional value but the option code is reserved for potential future use.
	CMD_REMOVE = 13
	CMD_REFRESH_INSTALL = 14
	CMD_INSTALL = 15
	CMD_REFRESH_UPDATE = 16
	CMD_UPDATE = 17
	CMD_REFRESH_REPLACE = 18
	CMD_REPLACE = 19
	CMD_UPGRADE = 20
	CMD_SET_FLAG = 21
	CMD_RESET_FLAG = 22
	# NOTE: The following commands are defunct and were for internal use only and should NOT be used by external modules!
	CMD_UPGRADE_EXCLUDE = 100
	CMD_UPGRADE_LIST = 101
	CMD_CLEAN = 102
	CMD_CLEAN_UPDATE = 103

	CMD_NAMES = {
		CMD_CLEAN_REFRESH: "CMD_CLEAN_REFRESH",
		CMD_REFRESH: "CMD_REFRESH",
		CMD_REFRESH_LIST: "CMD_REFRESH_LIST",
		CMD_LIST: "CMD_LIST",
		CMD_REFRESH_INSTALLED: "CMD_REFRESH_INSTALLED",
		CMD_LIST_INSTALLED: "CMD_LIST_INSTALLED",
		CMD_REFRESH_INSTALLABLE: "CMD_REFRESH_INSTALLABLE",
		CMD_LIST_INSTALLABLE: "CMD_LIST_INSTALLABLE",
		CMD_REFRESH_UPDATES: "CMD_REFRESH_UPDATES",
		CMD_LIST_UPDATES: "CMD_LIST_UPDATES",
		CMD_REFRESH_INFO: "CMD_REFRESH_INFO",
		CMD_INFO: "CMD_INFO",
		CMD_REFRESH_REMOVE: "CMD_REFRESH_REMOVE",
		CMD_REMOVE: "CMD_REMOVE",
		CMD_REFRESH_INSTALL: "CMD_REFRESH_INSTALL",
		CMD_INSTALL: "CMD_INSTALL",
		CMD_REFRESH_UPDATE: "CMD_REFRESH_UPDATE",
		CMD_UPDATE: "CMD_UPDATE",
		CMD_REFRESH_REPLACE: "CMD_REFRESH_REPLACE",
		CMD_REPLACE: "CMD_REPLACE",
		CMD_UPGRADE: "CMD_UPGRADE",
		CMD_SET_FLAG: "CMD_SET_FLAG",
		CMD_RESET_FLAG: "CMD_RESET_FLAG",
		# Defunct...
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
		CMD_REFRESH_INSTALLED: ["update", "list-installed"],  # JB: This is used in PluginBrowser Line 1085 .. I don't understand this part of the code because it's confusing me.
		CMD_LIST_INSTALLED: ["list-installed"],  # JB: This is used in PluginBrowser Line 1085 .. I don't understand this part of the code because it's confusing me.
		CMD_REFRESH_UPDATES: ["update", "list-upgradable"],
		CMD_LIST_UPDATES: ["list-upgradable"],
		CMD_REFRESH_INSTALLABLE: ["update", "list", "list-installed"],
		CMD_LIST_INSTALLABLE: ["list", "list-installed"],
		CMD_REFRESH_INFO: ["update", "info"],
		CMD_INFO: ["info"],
		CMD_REMOVE: ["remove"],
		CMD_REFRESH_INSTALL: ["update", "install"],
		CMD_INSTALL: ["install"],
		CMD_REFRESH_UPDATE: ["update", "install"],
		CMD_UPDATE: ["install"],
		CMD_REFRESH_REPLACE: ["update", "remove", "install"],
		CMD_REPLACE: ["remove", "install"],
		CMD_UPGRADE: ["upgrade"],
		CMD_SET_FLAG: ["flag", "hold"],  # JB: This syntax is wrong as this is not two commands, upgrade command is not implemented in runCommand.
		CMD_RESET_FLAG: ["flag", "ok"]  # JB: This syntax is wrong as this is not two commands, upgrade command is not implemented in runCommand.
	}

	EVENT_COMMAND_ERROR = 0
	EVENT_SYNTAX_ERROR = 1
	EVENT_NETWORK_ERROR = 2
	EVENT_OPKG_IN_USE = 3
	EVENT_CANT_INSTALL = 4
	EVENT_OPKG_MISMATCH = 5
	EVENT_LOG = 6
	EVENT_CLEAN_ERROR = 7
	EVENT_CLEAN_DONE = 8
	EVENT_DOWNLOAD = 9
	EVENT_FEED_UPDATED = 10
	EVENT_REFRESH_DONE = 11
	EVENT_LIST_DONE = 12
	EVENT_LIST_INSTALLED_DONE = 13
	EVENT_LIST_INSTALLABLE_DONE = 14
	EVENT_LIST_UPDATES_DONE = 15
	EVENT_BOOTLOGO_FOUND = 16
	EVENT_SETTINGS_FOUND = 17
	EVENT_INFO_DONE = 18
	EVENT_REMOVE = 19
	EVENT_REMOVE_DONE = 20
	EVENT_INSTALL = 21
	EVENT_CONFIGURING = 22
	EVENT_INSTALL_DONE = 23
	EVENT_UPDATE = 24
	EVENT_UPDATE_DONE = 25
	EVENT_REMOVE_OBSOLETE = 26
	EVENT_DESELECTED = 27
	EVENT_MODIFIED = 28
	EVENT_ERROR = 29
	EVENT_DONE = 30
	# Defunct...
	EVENT_INFLATING = 31
	EVENT_UPVERSION = 32
	EVENT_UPGRADE = 33
	EVENT_UPDATED = 34
	EVENT_LISTITEM = 35
	EVENT_DOWNLOAD_DONE = 36

	EVENT_NAMES = {
		EVENT_COMMAND_ERROR: "EVENT_COMMAND_ERROR",
		EVENT_SYNTAX_ERROR: "EVENT_SYNTAX_ERROR",
		EVENT_NETWORK_ERROR: "EVENT_NETWORK_ERROR",
		EVENT_OPKG_IN_USE: "EVENT_OPKG_IN_USE",
		EVENT_CANT_INSTALL: "EVENT_CANT_INSTALL",
		EVENT_OPKG_MISMATCH: "EVENT_OPKG_MISMATCH",
		EVENT_LOG: "EVENT_LOG",
		EVENT_CLEAN_ERROR: "EVENT_CLEAN_ERROR",
		EVENT_CLEAN_DONE: "EVENT_CLEAN_DONE",
		EVENT_DOWNLOAD: "EVENT_DOWNLOAD",
		EVENT_FEED_UPDATED: "EVENT_FEED_UPDATED",
		EVENT_REFRESH_DONE: "EVENT_REFRESH_DONE",
		EVENT_LIST_DONE: "EVENT_LIST_DONE",
		EVENT_LIST_INSTALLED_DONE: "EVENT_LIST_INSTALLED_DONE",
		EVENT_LIST_INSTALLABLE_DONE: "EVENT_LIST_INSTALLABLE_DONE",
		EVENT_LIST_UPDATES_DONE: "EVENT_LIST_UPDATES_DONE",
		EVENT_BOOTLOGO_FOUND: "EVENT_BOOTLOGO_FOUND",
		EVENT_SETTINGS_FOUND: "EVENT_SETTINGS_FOUND",
		EVENT_INFO_DONE: "EVENT_INFO_DONE",
		EVENT_REMOVE: "EVENT_REMOVE",
		EVENT_REMOVE_DONE: "EVENT_REMOVE_DONE",
		EVENT_INSTALL: "EVENT_INSTALL",
		EVENT_CONFIGURING: "EVENT_CONFIGURING",
		EVENT_INSTALL_DONE: "EVENT_INSTALL_DONE",
		EVENT_UPDATE: "EVENT_UPDATE",
		EVENT_UPDATE_DONE: "EVENT_UPDATE_DONE",
		EVENT_REMOVE_OBSOLETE: "EVENT_REMOVE_OBSOLETE",
		EVENT_DESELECTED: "EVENT_DESELECTED",
		EVENT_MODIFIED: "EVENT_MODIFIED",
		EVENT_ERROR: "EVENT_ERROR",
		EVENT_DONE: "EVENT_DONE",
		# Defunct...
		EVENT_INFLATING: "EVENT_INFLATING",
		EVENT_UPVERSION: "EVENT_UPVERSION",
		EVENT_UPGRADE: "EVENT_UPGRADE",
		EVENT_UPDATED: "EVENT_UPDATED",
		EVENT_LISTITEM: "EVENT_LISTITEM",
		EVENT_DOWNLOAD_DONE: "EVENT_DOWNLOAD_DONE"
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

	def __init__(self, opkg=PACKAGER):
		self.opkg = opkg
		self.console = eConsoleAppContainer()
		self.listCommands = ("list", "list-installed", "list-upgradable", "info")
		self.logCommands = ("install", "remove")
		self.command = None
		self.debugMode = None
		self.callbacks = []
		self.installable = []  # Note this list is NOT reset between runs and steps.  It is filled and updated on every list command and used to calculate upgradeable packages.
		self.checklist = []  # List of packages in the argument list.
		self.removed = []  # List of packages in the argument list that were removed.
		self.installed = []  # List of packages in the argument list that were installed.
		self.updated = []  # List of packages in the argument list that were updated.
		self.configuring = []  # List of packages in the argument list that were configured.
		self.opkgRemoved = []  # List of packages removed during the run.
		self.opkgInstalled = []  # List of packages installed during the run.
		self.fetchedList = []
		self.excludeList = []
		self.opkgCommands = []
		self.opkgCommand = None
		self.opkgCacheEmpty = False

	def runCommand(self, command, args=None):
		self.command = command
		if args is None:
			args = {}
		self.opkgCommands = self.CMD_TABLE.get(command)[:]  # Copy the command list so it can be manipulated.
		if self.opkgCommands:
			self.args = args
			self.step = 0
			self.steps = len(self.opkgCommands)
			print(f"[Opkg] The command '{self.getCommandText(command)}' has {self.steps} step{'s' if self.steps > 1 else ''} {self.opkgCommands}.")
			self.runStep()
		else:
			self.callCallbacks(self.EVENT_COMMAND_ERROR, command)

	def runStep(self):
		self.step += 1
		opkgCommand = self.opkgCommands.pop(0)
		self.opkgCommand = opkgCommand
		complexCommand = opkgCommand not in ("clean", "update")
		opkgArgs = [self.opkg, self.opkg]
		if "testMode" in self.args and self.args["testMode"]:
			opkgArgs.append("--noaction")
		if "options" in self.args and complexCommand:
			if isinstance(self.args["options"], dict):
				if opkgCommand in self.args["options"]:
					opkgArgs.extend(self.args["options"][opkgCommand])
			elif isinstance(self.args["options"], list):
				opkgArgs.extend(self.args["options"])
			else:
				opkgArgs.append(self.args["options"])
		opkgArgs.append(opkgCommand)
		if "arguments" in self.args:
			self.checklist = self.args["arguments"]
			if complexCommand:
				if self.command == self.CMD_REPLACE:  # CMD_REPLACE is special in that there are two arguments, the first is to be removed and the second is to be installed.
					opkgArgs.extend([self.args["arguments"][0]] if opkgCommand == "remove" else [self.args["arguments"][1]])
				else:
					opkgArgs.extend(self.args["arguments"])
		else:
			self.checklist = []
		dataBuffer = 131072 if opkgCommand in ("list", "list-installed", "list-upgradable", "info") else 2048  # 128 * 1024 = 128 KB data buffer for lists and 2 KB for other commands.
		self.debugMode = "debugMode" in self.args and self.args["debugMode"]
		msg = " in debug mode" if self.debugMode else ""
		print(f"[Opkg] Step {self.step} of {self.steps}: Executing '{opkgArgs[0]}' with command line arguments '{' '.join(opkgArgs[1:])}'{msg}.")
		self.removed = []
		self.installed = []
		self.updated = []
		self.configuring = []
		self.dataCache = ""
		self.dataCachePtr = -1
		self.console.setBufferSize(dataBuffer)
		self.console.dataAvail.append(self.consoleDataAvail)
		self.console.appClosed.append(self.consoleAppClosed)
		status = self.console.execute(*opkgArgs)
		if status:
			print(f"[Opkg] Note: Opkg execute returned a value of {status}.")
			# self.consoleAppClosed(-1)

	def consoleDataAvail(self, data):
		def consoleDataParse(line):
			if line:  # Skip empty lines. (Continuation lines should only occur in list commands.)
				try:
					argv = line.split()
					argc = len(argv)
					if line.startswith(f"{self.opkg}: unknown sub-command ") or line.startswith(f"{self.opkg}: the \""):
						self.callCallbacks(self.EVENT_SYNTAX_ERROR, line)
					elif line.startswith(" * opkg_download_backend: Failed to download"):
						self.callCallbacks(self.EVENT_NETWORK_ERROR, (self.opkgCommand, argv[5][:-1], argv[8][:-1]))
					elif line.startswith(" * opkg_lock: Could not lock"):
						self.callCallbacks(self.EVENT_OPKG_IN_USE, (self.command, self.opkgCommand))
					elif line.startswith(" * opkg_cmd_exec: Command failed to capture privilege lock:"):
						self.callCallbacks(self.EVENT_OPKG_IN_USE, (self.command, self.opkgCommand))
					elif line.startswith(" * opkg_solver_install: Cannot install package "):
						self.callCallbacks(self.EVENT_CANT_INSTALL, (self.opkgCommand, argv[5][:-1]))
					elif line.startswith(" * pkg_verify: File size mismatch:"):
						self.callCallbacks(self.EVENT_OPKG_MISMATCH, (self.opkgCommand, argv[5], argv[7], argv[10]))
					elif line == " * rm_r: Failed to open dir /var/cache/opkg: No such file or directory.":
						self.opkgCacheEmpty = True
					elif line.startswith("opkg_download: ERROR:"):
						self.callCallbacks(self.EVENT_ERROR, (self.command, self.opkgCommand))
					elif line.startswith("An error occurred"):
						self.callCallbacks(self.EVENT_ERROR, (self.command, self.opkgCommand))
					elif line.startswith("Configuring "):
						arg = argv[1][:-1]
						if arg in self.checklist:
							self.configuring.append(arg)
						self.callCallbacks(self.EVENT_CONFIGURING, arg)
					elif line.startswith("Downloading "):
						self.callCallbacks(self.EVENT_DOWNLOAD, argv[1][:-1])
					elif line.startswith("Failed to download"):
						self.callCallbacks(self.EVENT_ERROR, (self.command, self.opkgCommand))
					elif line.startswith("Installing "):
						if argc == 5 and argv[1] in self.checklist:
							self.installed.append(argv[1])
						self.callCallbacks(self.EVENT_INSTALL, argv[1])
					elif line.startswith("Not selecting "):
						self.callCallbacks(self.EVENT_DESELECTED, argv[2])
					elif line.startswith("Removing obsolete file "):
						self.callCallbacks(self.EVENT_REMOVE_OBSOLETE, argv[1])
					elif line.startswith("Removing "):
						if argv[1] in self.checklist:
							self.removed.append(argv[1])
						self.callCallbacks(self.EVENT_REMOVE, argv[1])
					elif line.startswith("Updated source "):
						self.callCallbacks(self.EVENT_FEED_UPDATED, argv[2][1:-2])
					elif line.startswith("Upgrading "):
						if argc == 8:
							self.updated.append(argv[1])
							self.callCallbacks(self.EVENT_UPDATE, (argv[1], argv[3], argv[5]))
						elif argc == 5:
							self.callCallbacks(self.EVENT_UPGRADE, argv[1])  # NOTE: This is not currently used.
					elif line.find("Configuration file '") >= 0:
						# Note: the config file update question doesn't end with a newline, so
						# if we get multiple config file update questions, the next ones
						# don't necessarily start at the beginning of a line.
						self.callCallbacks(self.EVENT_MODIFIED, line.split(" '", 3)[1][:-1])
				except IndexError as err:
					print(f"[Opkg] Error: Failed to parse line '{line}'!  ({str(err)})")

		data = data.decode("UTF-8", "ignore") if isinstance(data, bytes) else data
		self.dataCache = f"{self.dataCache}{data}"
		if self.opkgCommand not in self.listCommands:
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
		# sleep(0.5)  # Pause for 500ms to allow the synchronize of the file system to complete.
		if self.debugMode or config.crash.debugOpkg.value or self.opkgCommand not in self.listCommands:
			if self.dataCache:
				print(f"[Opkg] Opkg command '{self.opkgCommand}' output:")
				for line in self.dataCache.splitlines():
					print(f"[Opkg]    {line}")
				if self.opkgCommand in self.logCommands:
					self.callCallbacks(self.EVENT_LOG, self.dataCache)
			else:
				print(f"[Opkg] Opkg command '{self.opkgCommand}' resulted in no output.")
		elif self.opkgCommand in self.listCommands:
			print(f"[Opkg] Opkg command '{self.opkgCommand}' output suppressed to not flood the log file.")
		if self.opkgCommand == "clean":
			sync()
			sleep(0.5)  # Pause for 500ms to allow the synchronization of the files changed by clean to complete.
			if retVal == 255:
				if self.opkgCacheEmpty:
					self.callCallbacks(self.EVENT_CLEAN_DONE, 0)
					print("[Opkg] Opkg cache directory does not exist! Running 'update' to rebuild the cache.")
				else:
					self.callCallbacks(self.EVENT_CLEAN_ERROR, 0)
					self.opkgCommands = []  # The clean failed so abort any further steps!
					print("[Opkg] Opkg cache clean has failed! Running a file system check is STRONGLY recommended.")
			else:
				self.callCallbacks(self.EVENT_CLEAN_DONE, 0)
		elif self.opkgCommand == "update":
			self.callCallbacks(self.EVENT_REFRESH_DONE, retVal)
		elif self.opkgCommand == "list":
			packages = self.parseListData(self.dataCache, self.LIST_KEYS, False)
			self.installable = packages[:]
			if self.command in (self.CMD_REFRESH_LIST, self.CMD_LIST):
				self.callCallbacks(self.EVENT_LIST_DONE, packages)
		elif self.opkgCommand == "list-installed":
			packages = self.parseListData(self.dataCache, self.LIST_KEYS, True)
			if self.command in (self.CMD_REFRESH_INSTALLED, self.CMD_LIST_INSTALLED):
				self.callCallbacks(self.EVENT_LIST_INSTALLED_DONE, packages)
			elif self.command in (self.CMD_REFRESH_INSTALLABLE, self.CMD_LIST_INSTALLABLE):
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
		elif self.opkgCommand == "list-upgradable":
			packages = self.parseListData(self.dataCache, self.UPDATE_KEYS, True)
			self.callCallbacks(self.EVENT_LIST_UPDATES_DONE, packages)
		elif self.opkgCommand == "info":
			packages = self.parseInfoData(self.dataCache)
			for package in packages:
				if package["Installed"]:
					packageFile = package["Package"]
					if packageFile.startswith("enigma2-plugin-bootlogo-"):
						self.callCallbacks(self.EVENT_BOOTLOGO_FOUND, packageFile)
					elif packageFile.startswith("enigma2-plugin-settings-"):
						self.callCallbacks(self.EVENT_SETTINGS_FOUND, packageFile)
			self.callCallbacks(self.EVENT_INFO_DONE, packages)
		elif self.opkgCommand == "remove" and self.command == self.CMD_REPLACE:
			pass  # We are half way through a CMD_REPLACE command so do nothing.
		elif self.command == self.CMD_REMOVE and self.opkgCommand == "remove":
			self.callCallbacks(self.EVENT_REMOVE_DONE, self.removed)
		elif self.command in (self.CMD_REFRESH_INSTALL, self.CMD_INSTALL) and self.opkgCommand == "install":
			self.callCallbacks(self.EVENT_INSTALL_DONE, self.installed)
		elif self.command in (self.CMD_REFRESH_UPDATE, self.CMD_UPDATE) and self.opkgCommand == "install":
			self.callCallbacks(self.EVENT_UPDATE_DONE, self.updated)
		if self.opkgCommands:
			self.runStep()
		else:
			self.callCallbacks(self.EVENT_DONE, self.command)

	def parseListData(self, listData, listKeys, installed):
		data = {}
		if listData:
			lines = listData.splitlines()
			for line in lines:
				if line.startswith("Not selecting "):
					print(f"[Opkg] Warning: Not selecting '{line[14:]}'.")
			args = []
			for line in lines:
				if args:
					if line[:1] == " ":
						args[-1] = f"{args[-1]} {line.strip()}"
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
								print(f"[Opkg] Warning: Package '{entry['Package']}' has an invalid size of '{entry['Size']}'.")
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
					value = f"{value} {line.strip()}"
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

	def callCallbacks(self, event, parameter=None):
		for callback in self.callbacks:
			callback(event, parameter)

	def addCallback(self, callback):
		if callback not in self.callbacks:
			self.callbacks.append(callback)
		else:
			print(f"[Opkg] Error: Callback '{str(callback)}' already exists!")

	def removeCallback(self, callback):
		if callback in self.callbacks:
			self.callbacks.remove(callback)
		else:
			print(f"[Opkg] Error: Callback '{str(callback)}' does not exist!")

	def stop(self):
		self.console.kill()

	def isRunning(self):
		return self.console.running()

	def write(self, what):
		if what:
			if not what.endswith("\n"):  # We except unterminated commands.
				what = f"{what}\n"
			self.console.write(what, len(what))

	def getCommandText(self, command):
		return self.CMD_NAMES.get(command, "None")

	def getEventText(self, event):
		return self.EVENT_NAMES.get(event, "None")


# The following code is a deprecated and due to be removed soon.

	def startCmd(self, cmd, args=None):
		self.nextCommand = None
		extra = []
		consoleBuffer = 2048
		if cmd == self.CMD_UPGRADE and self.excludeList:
			cmd = self.CMD_SET_FLAG
		self.command = cmd
		self.currentCommand = cmd  # Support legacy code until it is refactored to the new runCommand() method.
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
		print(f"[Opkg] Executing '{self.opkg}' with '{' '.join(argv)}'.")
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
		self.cache = f"{self.cache}{data}"
		if self.command == self.CMD_INFO:
			return
		while True:
			linePtr = self.cache.find("\n", self.cachePtr + 1)
			if linePtr == -1:
				break
			self.parseLine(self.cache[self.cachePtr + 1:linePtr])
			self.cachePtr = linePtr

	def parseLine(self, line):
		# print(f"[Opkg] DEBUG: Line='{line}'.")
		if not line or line.startswith(" "):  # Skip empty or continuation lines.
			return
		if self.command in (self.CMD_LIST, self.CMD_LIST_INSTALLED, self.CMD_UPGRADE_LIST):
			argv = line.split(" - ", 2)
			argc = len(argv)
			if not line.startswith("Not selecting ") and not line.startswith("error: "):
				if self.command == self.CMD_UPGRADE_LIST and self.isExcluded(argv[0]):
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
			print(f"[Opkg] Error: Failed to parse line '{line}'!  ({str(err)})")

	def isExcluded(self, item):  # NOTE: These filters are for SoftwareUpdate.
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
		elif item.find(f"{BoxInfo.getItem('distro')}-spinner") > -1 and not config.plugins.softwaremanager.overwriteSpinnerFiles.value:
			exclude = True
		else:
			exclude = False
		return exclude

	def cmdFinished(self, retVal):
		self.console.dataAvail.remove(self.cmdData)
		self.console.appClosed.remove(self.cmdFinished)
		if config.crash.debugOpkg.value and self.command != self.CMD_INFO:
			print(f"[Opkg] Opkg command '{self.getCommandText(self.command)}' output:\n{self.cache}")
		if self.nextCommand:
			cmd, args = self.nextCommand
			self.nextCommand = None
			self.startCmd(cmd, args)
		else:
			self.callCallbacks(self.EVENT_DONE if retVal == 0 else self.EVENT_ERROR)

	def getFetchedList(self):  # NOTE: This is used in SoftwareUpdate.
		return self.fetchedList
