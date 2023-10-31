from os import sync
from os.path import join

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
	CMD_INSTALL = 0
	CMD_REFRESH_INSTALL = 1
	CMD_LIST = 2
	CMD_REMOVE = 3
	CMD_UPDATE = 4
	CMD_REFRESH_UPDATE = 5
	CMD_UPGRADE = 6
	CMD_UPGRADE_LIST = 7
	CMD_LIST_INSTALLED = 8
	CMD_INFO = 9
	CMD_REFRESH = 10
	CMD_REFRESH_LIST = 11
	CMD_REFRESH_UPDATES = 12
	CMD_REFRESH_INFO = 13
	CMD_LIST_UPDATES = 14
	CMD_REFRESH_INSTALLABLE = 15
	CMD_LIST_INSTALLABLE = 16
	CMD_REPLACE = 17
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
		CMD_REFRESH_INSTALL: "CMD_REFRESH_INSTALL",
		CMD_REPLACE: "CMD_REPLACE",
		CMD_UPDATE: "CMD_UPDATE",
		CMD_REFRESH_UPDATE: "CMD_REFRESH_UPDATE",
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
		# CMD_LIST_INSTALLABLE: ["list", "list-installed"],
		CMD_LIST_INSTALLABLE: ["list-installed"],
		CMD_REFRESH_INFO: ["update", "info"],
		CMD_INFO: ["info"],
		CMD_REMOVE: ["remove"],
		CMD_INSTALL: ["install"],
		CMD_REFRESH_INSTALL: ["update", "install"],
		CMD_REPLACE: ["remove", "install"],
		CMD_UPDATE: ["install"],
		CMD_REFRESH_UPDATE: ["update", "install"],
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

	def __init__(self, opkg=PACKAGER):
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
		print(f"[Opkg] The command '{self.getCommandText(cmd)}' has {self.steps} step{'s' if self.steps > 1 else ''} {self.commands}.")
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
		print(f"[Opkg] Step {self.step} of {self.steps}: Executing '{opkgArgs[0]}' with command line arguments '{' '.join(opkgArgs[1:])}'{msg}.")
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
				# elif line.startswith("Removing "):
				elif line.startswith("Removing ") and not line.startswith("Removing obsolete file "):
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
				print(f"[Opkg] Error: Failed to parse line '{line}'!  ({str(err)})")

		data = data.decode("UTF-8", "ignore") if isinstance(data, bytes) else data
		self.dataCache = f"{self.dataCache}{data}"
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
				print(f"[Opkg] Opkg command '{self.opkgCmd}' output:")
				for line in self.dataCache.splitlines():
					print(f"[Opkg]    {line}")
				if self.opkgCmd in self.logCommands:
					self.callCallbacks(self.EVENT_LOG, self.dataCache)
			else:
				print(f"[Opkg] Opkg command '{self.opkgCmd}' resulted in no output.")
		elif self.opkgCmd in self.listCommands:
			print(f"[Opkg] Opkg command '{self.opkgCmd}' output suppressed to not flood the log file.")
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
				print(f"[Opkg] Warning: The command '{self.opkgCmd}' completed with no callback defined.")
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
					print(f"[Opkg] Warning: Not selecting '{line[14:]}'.")
			args = None
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
		for callback in self.callbackList:
			callback(event, parameter)

	def addCallback(self, callback):
		if callback not in self.callbackList:
			self.callbackList.append(callback)
		else:
			print(f"[Opkg] Error: Callback '{str(callback)}' already exists!")

	def removeCallback(self, callback):
		if callback in self.callbackList:
			self.callbackList.remove(callback)
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
		extra = []
		consoleBuffer = 2048
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
		if self.currentCommand == self.CMD_INFO:
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
			print(f"[Opkg] Error: Failed to parse line '{line}'!  ({str(err)})")

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
		elif item.find(f"{BoxInfo.getItem('distro')}-spinner") > -1 and not config.plugins.softwaremanager.overwriteSpinnerFiles.value:
			exclude = True
		else:
			exclude = False
		return exclude

	def cmdFinished(self, retVal):
		self.console.dataAvail.remove(self.cmdData)
		self.console.appClosed.remove(self.cmdFinished)
		if config.crash.debugOpkg.value and self.currentCommand != self.CMD_INFO:
			print(f"[Opkg] Opkg command '{self.getCommandText(self.currentCommand)}' output:\n{self.cache}")
		if self.nextCommand:
			cmd, args = self.nextCommand
			self.nextCommand = None
			self.startCmd(cmd, args)
		else:
			self.callCallbacks(self.EVENT_DONE if retVal == 0 else self.EVENT_ERROR)

	def getFetchedList(self):
		return self.fetchedList

	def getExcludeList(self):
		return self.excludeList
