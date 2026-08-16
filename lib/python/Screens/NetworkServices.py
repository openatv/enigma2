from errno import ETIMEDOUT
from json import dumps, loads
from glob import glob
from os import listdir, rename, strerror
from os.path import exists
from process import ProcessList
from random import Random
from urllib.request import Request, urlopen

from enigma import eConsoleAppContainer, eTimer

from Components.ActionMap import HelpableActionMap
from Components.config import ConfigNumber, ConfigPassword, ConfigSelection, ConfigText, ConfigYesNo, NoSave, ReadOnly, config, getConfigListEntry
from Components.Console import Console

from Components.ScrollLabel import ScrollLabel
from Components.SystemInfo import BoxInfo
from Components.FileList import MultiFileSelectList
from Components.Opkg import OpkgComponent
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Processing import Processing
from Screens.Screen import Screen
from Screens.Setup import Setup
from Tools.Directories import SCOPE_SKINS, fileReadLines, fileReadXML, fileWriteLines, resolveFilename

MODULE_NAME = __name__.split(".")[-1]
BASE_GROUP = "packagegroup-base"


class NetworkDaemons:
	def __init__(self):
		fileDom = fileReadXML(resolveFilename(SCOPE_SKINS, "networkdaemons.xml"), source=MODULE_NAME)
		self.__daemons = []
		for daemon in fileDom.findall("daemon"):
			daemondict = {}
			for key in ("key", "title", "installcheck", "package", "autostart", "autostartservice", "autostartprio", "running", "startservice", "logpath"):
				daemondict[key] = daemon.get(key, "")
			if daemondict["key"] and daemondict["title"]:
				daemondict["isinstalled"] = daemondict["installcheck"] == "" or exists(daemondict["installcheck"])
				daemondict["isservice"] = daemondict["startservice"] != ""
				self.__daemons.append(daemondict)

	def getDaemons(self):
		return self.__daemons


class NetworkServicesSetup(Setup, NetworkDaemons):
	def __init__(self, session):
		NetworkDaemons.__init__(self)
		self.serviceItems = []
		self.serviceIsRunning = {}
		Setup.__init__(self, session, "NetworkServicesSetup")
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["startStopActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.toggleStartStop, _("Start or Stop service"))
		}, prio=0, description=_("Network Setup Actions"))
		self["showLogActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.showLog, _("Show Log"))
		}, prio=0, description=_("Network Setup Actions"))
		self.console = Console()
		self.opkgComponent = OpkgComponent()
		self.opkgComponent.addCallback(self.opkgCallback)

	def getRunningStatus(self):
		self.serviceIsRunning = {}
		processlist = ProcessList()
		for daemon in self.getDaemons():
			if daemon["isservice"]:
				self.serviceIsRunning[daemon["key"]] = False
				for runningService in daemon["running"].split(","):
					if str(processlist.named(runningService)).strip("[]"):
						self.serviceIsRunning[daemon["key"]] = True
						break

	def getService(self, daemon):
		choices = []
		checkFile = daemon["installcheck"]
		autoStartCheck = daemon["autostart"]
		title = daemon["title"]
		if checkFile:
			if exists(checkFile):
				choices.append((2, _("Uninstall")))
				if not autoStartCheck:
					choices.append((3, _("Installed")))
					default = 3
			else:
				choices.append((2, _("Not Installed")))
				choices.append((3, _("Install")))
				default = 2
				autoStartCheck = False
		if autoStartCheck:
			default = 0 if glob(autoStartCheck) else 1
			if default == 0:
				choices.append((0, _("Enabled")))
				choices.append((1, _("Disable")))
			else:
				choices.append((0, _("Enable")))
				choices.append((1, _("Disabled")))

		cfg = ConfigSelection(default=default, choices=choices)
		return (title, cfg, _("Select the action for '%s'") % title, daemon)

	def createSetup(self):  # NOSONAR silence S2638
		if not self.serviceItems:
			for daemon in self.getDaemons():
				self.serviceItems.append(self.getService(daemon))
			self.getRunningStatus()
		Setup.createSetup(self, appendItems=self.serviceItems)

	def selectionChanged(self):
		current = self["config"].getCurrent()
		if current:
			daemon = current[3]
			isInstalled = daemon["isinstalled"]
			isRunning = self.serviceIsRunning.get(daemon["key"], None)
			if isInstalled and isRunning is not None:
				cmd = _("Stop") if isRunning else _("Start")
				self["key_yellow"].setText(cmd)
				self["startStopActions"].setEnabled(True)
			else:
				self["key_yellow"].setText("")
				self["startStopActions"].setEnabled(False)
			logPath = daemon["logpath"] and isInstalled
			self["key_blue"].setText(_("Show Log") if logPath else "")
			self["showLogActions"].setEnabled(logPath != "")

			Setup.selectionChanged(self)
			installed = _("Installed") if isInstalled else _("Not Installed")
			if isRunning is not None:
				running = _("Running") if isRunning else _("Not running")
				footnote = f"{_('Current Status:')} {installed} / {running}"
			else:
				footnote = f"{_('Current Status:')} {installed}"
			self.setFootnote(footnote)

	def toggleStartStop(self):
		def toggleStartStopCallback(result=None, retval=None, extra_args=None):
			self.getRunningStatus()
			self.selectionChanged()
			Processing.instance.hideProgress()

		current = self["config"].getCurrent()
		if current:
			daemon = current[3]
			if daemon["isservice"]:
				isRunning = self.serviceIsRunning.get(daemon["key"], None)
				service = daemon["startservice"]
				cmd = "stop" if isRunning else "start"
				self.showProgress()
				commands = [f"/etc/init.d/{service} {cmd}"]
				if daemon["key"] == "sambas":
					commands = [f"/etc/init.d/wsdd {cmd}"]
					if isRunning:
						commands.append("killall nmbd")
						commands.append("killall smbd")
				self.console.eBatch(commands, toggleStartStopCallback, debug=True)

	def showLog(self):
		current = self["config"].getCurrent()
		if current:
			self.session.open(NetworkLogScreen, title=_("Log"), logPath=current[3]["logpath"])

	def showProgress(self, text=""):
		Processing.instance.setDescription(text or _("Please wait..."))
		Processing.instance.showProgress(endless=True)

	def opkgCallback(self, event, parameter):
		def configureCallback(result=None, retval=None, extra_args=None):
			Processing.instance.hideProgress()
			Setup.keySave(self)
		if event == self.opkgComponent.EVENT_REMOVE_DONE and self.installPackages:
			self.showProgress(_("Installing Service"))
			self.opkgComponent.runCommand(self.opkgComponent.CMD_REFRESH_INSTALL, {"arguments": self.installPackages})
		elif event in (self.opkgComponent.EVENT_REMOVE_DONE, self.opkgComponent.EVENT_INSTALL_DONE):
			if self.cmdList:
				self.showProgress(_("Configuring Service"))
				self.console.eBatch(self.cmdList, configureCallback, debug=True)
			else:
				configureCallback()

	def keySave(self):
		self.installPackages = []
		self.removePackages = []
		self.cmdList = []
		for item in self["config"].list:
			if len(item) > 1 and item[1].isChanged():
				daemon = item[3]
				if item[1].value == 2:  # remove
					self.removePackages.append(daemon["package"])
				elif item[1].value == 3:  # install
					self.installPackages.append(daemon["package"])
				elif item[1].value == 0:  # autostart on
					autostartprio = daemon["autostartprio"]
					cmd = f"defaults {autostartprio}" if autostartprio else "defaults"
					autostartservice = daemon["autostartservice"]
					self.cmdList.append(f"update-rc.d -f {autostartservice} {cmd}")
				elif item[1].value == 1:  # autostart off
					autostartservice = daemon["autostartservice"]
					self.cmdList.append(f"update-rc.d -f {autostartservice} remove")
			item[1].cancel()

		if self.removePackages:
			self.showProgress(_("Removing Service"))
			args = {
				"arguments": self.removePackages,
				"options": {"remove": ["--force-remove", "--autoremove"]}
			}
			self.opkgComponent.runCommand(self.opkgComponent.CMD_REMOVE, args)
		elif self.installPackages:
			self.opkgCallback(self.opkgComponent.EVENT_REMOVE_DONE, "")
		elif self.cmdList:
			self.opkgCallback(self.opkgComponent.EVENT_INSTALL_DONE, "")
		else:
			Setup.keySave(self)


class NetworkInadynSetup(Setup):
	def __init__(self, session):
		self.ina_user = NoSave(ConfigText(fixed_size=False))
		self.ina_pass = NoSave(ConfigText(fixed_size=False))
		self.ina_alias = NoSave(ConfigText(fixed_size=False))
		self.ina_period = NoSave(ConfigNumber())
		self.ina_sysactive = NoSave(ConfigYesNo(default=False))
		choices = [(x, x) for x in ("dyndns@dyndns.org", "statdns@dyndns.org", "custom@dyndns.org", "default@no-ip.com")]
		self.ina_system = NoSave(ConfigSelection(default="dyndns@dyndns.org", choices=choices))
		Setup.__init__(self, session, "NetworkInadynSetup")

	def changedEntry(self):
		pass  # No actions needed

	def createSetup(self):  # NOSONAR silence S2638
		inadynItems = []
		lines = fileReadLines("/etc/inadyn.conf", source=MODULE_NAME)
		if lines:
			for line in lines:
				if line.startswith("username "):
					line = line[9:]
					self.ina_user.value = line
					ina_user1 = getConfigListEntry("%s:" % _("Username"), self.ina_user)
					inadynItems.append(ina_user1)
				elif line.startswith("password "):
					line = line[9:]
					self.ina_pass.value = line
					ina_pass1 = getConfigListEntry("%s:" % _("Password"), self.ina_pass)
					inadynItems.append(ina_pass1)
				elif line.startswith("alias "):
					line = line[6:]
					self.ina_alias.value = line
					ina_alias1 = getConfigListEntry("%s:" % _("Alias"), self.ina_alias)
					inadynItems.append(ina_alias1)
				elif line.startswith("update_period_sec "):
					line = line[18:]
					line = (int(line) // 60)
					self.ina_period.value = line
					ina_period1 = getConfigListEntry("%s:" % _("Time update in minutes"), self.ina_period)
					inadynItems.append(ina_period1)
				elif line.startswith("dyndns_system ") or line.startswith("#dyndns_system "):
					if not line.startswith("#"):
						self.ina_sysactive.value = True
						line = line[14:]
					else:
						self.ina_sysactive.value = False
						line = line[15:]
					ina_sysactive1 = getConfigListEntry("%s:" % _("Set system"), self.ina_sysactive)
					inadynItems.append(ina_sysactive1)
					self.ina_value = line
					ina_system1 = getConfigListEntry("%s:" % _("System"), self.ina_system)
					inadynItems.append(ina_system1)
		Setup.createSetup(self, appendItems=inadynItems)
		self.setTitle(_("Inadyn Settings"))

	def keySave(self):
		oldLines = fileReadLines("/etc/inadyn.conf", source=MODULE_NAME)
		if oldLines:
			newLines = []
			for line in oldLines:
				if line.startswith("username "):
					line = f"username {self.ina_user.value.strip()}"
				elif line.startswith("password "):
					line = f"password {self.ina_pass.value.strip()}"
				elif line.startswith("alias "):
					line = f"alias {self.ina_alias.value.strip()}"
				elif line.startswith("update_period_sec "):
					strview = self.ina_period.value * 60
					line = f"update_period_sec {str(strview)}"
				elif line.startswith("dyndns_system ") or line.startswith("#dyndns_system "):
					line = f"{'' if self.ina_sysactive.value else '#'}dyndns_system {self.ina_system.value.strip()}"
				newLines.append(line)
			fileWriteLines("/etc/inadyn.conf.tmp", newLines)
		else:
			self.session.open(MessageBox, _("Sorry Inadyn Config is Missing"), MessageBox.TYPE_INFO)
			self.close()
		if exists("/etc/inadyn.conf.tmp"):
			rename("/etc/inadyn.conf.tmp", "/etc/inadyn.conf")
		self.close()


class NetworkuShareSetup(Setup):
	def __init__(self, session):
		self.ushare_user = NoSave(ConfigText(default=BoxInfo.getItem("machinebuild"), fixed_size=False))
		self.ushare_iface = NoSave(ConfigText(fixed_size=False))
		self.ushare_port = NoSave(ConfigNumber())
		self.ushare_telnetport = NoSave(ConfigNumber())
		self.ushare_web = NoSave(ConfigYesNo(default=True))
		self.ushare_telnet = NoSave(ConfigYesNo(default=True))
		self.ushare_xbox = NoSave(ConfigYesNo(default=True))
		self.ushare_ps3 = NoSave(ConfigYesNo(default=True))
		choices = [(x, x) for x in ("dyndns@dyndns.org", "statdns@dyndns.org", "custom@dyndns.org", "default@no-ip.com")]
		self.ushare_system = NoSave(ConfigSelection(default="dyndns@dyndns.org", choices=choices))
		self.selectedFiles = []
		Setup.__init__(self, session, "NetworkuShareSetup")
		self["key_yellow"] = StaticText(_("Shares"))
		self["selectSharesActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.selectShares, _("Select Shares"))
		}, prio=0, description=_("Network Setup Actions"))

	def changedEntry(self):
		pass  # No actions needed

	def createSetup(self):  # NOSONAR silence S2638
		ushareItems = []
		lines = fileReadLines("/etc/ushare.conf", source=MODULE_NAME)
		if lines:
			for line in lines:
				line = line.strip()
				if line.startswith("USHARE_NAME="):
					line = line[12:]
					self.ushare_user.value = line
					ushare_user1 = getConfigListEntry("%s:" % _("uShare Name"), self.ushare_user)
					ushareItems.append(ushare_user1)
				elif line.startswith("USHARE_IFACE="):
					line = line[13:]
					self.ushare_iface.value = line
					ushare_iface1 = getConfigListEntry("%s:" % _("Interface"), self.ushare_iface)
					ushareItems.append(ushare_iface1)
				elif line.startswith("USHARE_PORT="):
					line = line[12:]
					self.ushare_port.value = line
					ushare_port1 = getConfigListEntry("%s:" % _("uShare Port"), self.ushare_port)
					ushareItems.append(ushare_port1)
				elif line.startswith("USHARE_TELNET_PORT="):
					line = line[19:]
					self.ushare_telnetport.value = line
					ushare_telnetport1 = getConfigListEntry("%s:" % _("Telnet Port"), self.ushare_telnetport)
					ushareItems.append(ushare_telnetport1)
				elif line.startswith("ENABLE_WEB="):
					self.ushare_web.value = line.endswith("yes")
					ushare_web1 = getConfigListEntry("%s:" % _("Web Interface"), self.ushare_web)
					ushareItems.append(ushare_web1)
				elif line.startswith("ENABLE_TELNET="):
					self.ushare_telnet.value = line.endswith("yes")
					ushare_telnet1 = getConfigListEntry("%s:" % _("Telnet Interface"), self.ushare_telnet)
					ushareItems.append(ushare_telnet1)
				elif line.startswith("ENABLE_XBOX="):
					self.ushare_xbox.value = line.endswith("yes")
					ushare_xbox1 = getConfigListEntry("%s:" % _("XBox 360 support"), self.ushare_xbox)
					ushareItems.append(ushare_xbox1)
				elif line.startswith("ENABLE_DLNA="):
					self.ushare_ps3.value = line.endswith("yes")
					ushare_ps31 = getConfigListEntry("%s:" % _("DLNA support"), self.ushare_ps3)
					ushareItems.append(ushare_ps31)
				elif line.startswith("USHARE_DIR="):
					line = line[11:]
					self.selectedFiles = [str(n) for n in line.split(", ")]
		Setup.createSetup(self, appendItems=ushareItems)
		self.setTitle(_("uShare Settings"))

	def keySave(self):
		def getYesNo(configItem):
			return "yes" if configItem.value else "no"
		oldLines = fileReadLines("/etc/ushare.conf", source=MODULE_NAME)
		if oldLines:
			newLines = []
			for line in oldLines:
				if line.startswith("USHARE_NAME="):
					line = f"USHARE_NAME={self.ushare_user.value.strip()}"
				elif line.startswith("USHARE_IFACE="):
					line = f"USHARE_IFACE={self.ushare_iface.value.strip()}"
				elif line.startswith("USHARE_PORT="):
					line = f"USHARE_PORT={str(self.ushare_port.value)}"
				elif line.startswith("USHARE_TELNET_PORT="):
					line = f"USHARE_TELNET_PORT={str(self.ushare_telnetport.value)}"
				elif line.startswith("USHARE_DIR="):
					line = ("USHARE_DIR=%s" % ", ".join(self.selectedFiles))
				elif line.startswith("ENABLE_WEB="):
					line = f"ENABLE_WEB={getYesNo(self.ushare_web)}"
				elif line.startswith("ENABLE_TELNET="):
					line = f"ENABLE_TELNET={getYesNo(self.ushare_telnet)}"
				elif line.startswith("ENABLE_XBOX="):
					line = f"ENABLE_XBOX={getYesNo(self.ushare_xbox)}"
				elif line.startswith("ENABLE_DLNA="):
					line = f"ENABLE_DLNA={getYesNo(self.ushare_ps3)}"
				newLines.append(line)
			fileWriteLines("/etc/ushare.conf.tmp", newLines)
		else:
			self.session.open(MessageBox, _("Sorry uShare Config is Missing"), MessageBox.TYPE_INFO)
			self.close()
		if exists("/etc/ushare.conf.tmp"):
			rename("/etc/ushare.conf.tmp", "/etc/ushare.conf")
		self.close()

	def selectShares(self):
		def selectSharesCallBack(selectedFiles):
			if selectedFiles:
				self.selectedFiles = selectedFiles
		self.session.openWithCallback(selectSharesCallBack, uShareSelection, self.selectedFiles)


class uShareSelection(Screen):
	def __init__(self, session, selectedFiles):
		Screen.__init__(self, session)
		self.setTitle(_("Select Folders"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText()
		self.selectedFiles = selectedFiles
		defaultDir = "/media/"
		self.filelist = MultiFileSelectList(self.selectedFiles, defaultDir, showFiles=False)
		self["checkList"] = self.filelist
		self["actions"] = HelpableActionMap(self, ["NavigationActions", "OkCancelActions", "ColorActions"], {
			"ok": self.keyOk,
			"cancel": self.exit,
			"red": self.exit,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"top": (self["checkList"].goTop, _("Move to first line / screen")),
			"pageUp": (self["checkList"].goPageUp, _("Move up a screen")),
			"up": (self["checkList"].goLineUp, _("Move up a line")),
			# "left": (self.left, _("Move up to first entry")),
			# "right": (self.right, _("Move down to last entry")),
			"down": (self["checkList"].goLineDown, _("Move down a line")),
			"pageDown": (self["checkList"].goPageDown, _("Move down a screen")),
			"bottom": (self["checkList"].goBottom, _("Move to last line / screen"))
		}, prio=-1, description=_("uShare Selection Actions"))
		if self.selectionChanged not in self["checkList"].onSelectionChanged:
			self["checkList"].onSelectionChanged.append(self.selectionChanged)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		idx = 0
		self["checkList"].moveToIndex(idx)
		self.selectionChanged()

	def selectionChanged(self):
		current = self["checkList"].getCurrent()[0]
		self["key_yellow"].setText(_("Deselect") if current[2] is True else _("Select"))

	def keyYellow(self):
		self["checkList"].changeSelectionState()
		self.selectedFiles = self["checkList"].getSelectedList()

	def keyGreen(self):
		self.selectedFiles = self["checkList"].getSelectedList()
		self.close(self.selectedFiles)

	def exit(self):
		self.close(None)

	def keyOk(self):
		if self.filelist.canDescent():
			self.filelist.descent()


class NetworkMiniDLNASetup(Setup):
	def __init__(self, session):
		self.selectedFiles = []
		self.minidlna_name = NoSave(ConfigText(default=BoxInfo.getItem("machinebuild"), fixed_size=False))
		self.minidlna_iface = NoSave(ConfigText(fixed_size=False))
		self.minidlna_port = NoSave(ConfigNumber())
		self.minidlna_serialno = NoSave(ConfigNumber())
		self.minidlna_web = NoSave(ConfigYesNo(default=True))
		self.minidlna_inotify = NoSave(ConfigYesNo(default=True))
		self.minidlna_tivo = NoSave(ConfigYesNo(default=True))
		self.minidlna_strictdlna = NoSave(ConfigYesNo(default=True))
		Setup.__init__(self, session, "NetworkMiniDLNASetup")
		self["key_yellow"] = StaticText(_("Shares"))
		self["selectSharesActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.selectShares, _("Select Shares"))
		}, prio=0, description=_("Network Setup Actions"))

	def changedEntry(self):
		pass  # No actions needed

	def createSetup(self):  # NOSONAR silence S2638
		minidlnaItems = []
		lines = fileReadLines("/etc/minidlna.conf", source=MODULE_NAME)
		if lines:
			for line in lines:
				line = line.strip()
				if line.startswith("friendly_name="):
					line = line[14:]
					self.minidlna_name.value = line
					minidlna_name1 = getConfigListEntry("%s:" % _("Name"), self.minidlna_name)
					minidlnaItems.append(minidlna_name1)
				elif line.startswith("network_interface="):
					line = line[18:]
					self.minidlna_iface.value = line
					minidlna_iface1 = getConfigListEntry("%s:" % _("Interface"), self.minidlna_iface)
					minidlnaItems.append(minidlna_iface1)
				elif line.startswith("port="):
					line = line[5:]
					self.minidlna_port.value = line
					minidlna_port1 = getConfigListEntry("%s:" % _("Port"), self.minidlna_port)
					minidlnaItems.append(minidlna_port1)
				elif line.startswith("serial="):
					line = line[7:]
					self.minidlna_serialno.value = line
					minidlna_serialno1 = getConfigListEntry("%s:" % _("Serial No"), self.minidlna_serialno)
					minidlnaItems.append(minidlna_serialno1)
				elif line.startswith("inotify="):
					self.minidlna_inotify.value = line[8:] != "no"
					minidlna_inotify1 = getConfigListEntry("%s:" % _("Inotify Monitoring"), self.minidlna_inotify)
					minidlnaItems.append(minidlna_inotify1)
				elif line.startswith("enable_tivo="):
					self.minidlna_tivo.value = line[12:] != "no"
					minidlna_tivo1 = getConfigListEntry("%s:" % _("TiVo support"), self.minidlna_tivo)
					minidlnaItems.append(minidlna_tivo1)
				elif line.startswith("strict_dlna="):
					self.minidlna_strictdlna.value = line[12:] != "no"
					minidlna_strictdlna1 = getConfigListEntry("%s:" % _("Strict DLNA"), self.minidlna_strictdlna)
					minidlnaItems.append(minidlna_strictdlna1)
				elif line.startswith("media_dir="):
					line = line[10:]
					self.selectedFiles = [str(n) for n in line.split(", ")]

		Setup.createSetup(self, appendItems=minidlnaItems)
		self.setTitle(_("MiniDLNA Settings"))

	def keySave(self):
		def getYesNo(configItem):
			return "yes" if configItem.value else "no"
		oldLines = fileReadLines("/etc/minidlna.conf", [], source=MODULE_NAME)
		if oldLines:
			newLines = []
			for line in oldLines:
				line = line.replace("\n", "")
				if line.startswith("friendly_name="):
					line = f"friendly_name={self.minidlna_name.value.strip()}"
				elif line.startswith("network_interface="):
					line = f"network_interface={self.minidlna_iface.value.strip()}"
				elif line.startswith("port="):
					line = f"port={str(self.minidlna_port.value)}"
				elif line.startswith("serial="):
					line = f"serial={str(self.minidlna_serialno.value)}"
				elif line.startswith("media_dir="):
					line = "media_dir=%s" % ", ".join(self.selectedFiles)
				elif line.startswith("inotify="):
					line = f"inotify={getYesNo(self.minidlna_inotify)}"
				elif line.startswith("enable_tivo="):
					line = f"enable_tivo={getYesNo(self.minidlna_tivo)}"
				elif line.startswith("strict_dlna="):
					line = f"strict_dlna={getYesNo(self.minidlna_strictdlna)}"
				newLines.append(line)
			fileWriteLines("/etc/minidlna.conf.tmp", newLines, source=MODULE_NAME)
		else:
			self.session.open(MessageBox, _("Sorry MiniDLNA Config is Missing"), MessageBox.TYPE_INFO)
			self.close()
		if exists("/etc/minidlna.conf.tmp"):
			rename("/etc/minidlna.conf.tmp", "/etc/minidlna.conf")
		self.close()

	def selectShares(self):
		def selectSharesCallBack(selectedFiles):
			if selectedFiles:
				self.selectedFiles = selectedFiles
		self.session.openWithCallback(selectSharesCallBack, uShareSelection, self.selectedFiles)


class NetworkNFSSetup(Setup):
	NFSCONF = "/etc/nfs.conf"
	EXPORTSFILE = "/etc/exports"
	_MARKER = "# OpenATV managed exports"

	def __init__(self, session):
		self.nfsThreads = NoSave(ConfigNumber(default=8))
		self.nfsVers3 = NoSave(ConfigYesNo(default=True))
		self.nfsVers4 = NoSave(ConfigYesNo(default=True))
		self.nfsAccessMode = NoSave(ConfigSelection(default="rw", choices=[
			("rw", _("Read/Write")),
			("ro", _("Read Only")),
		]))
		self.nfsClients = NoSave(ConfigText(default="*", fixed_size=False))
		self.nfsRootSquash = NoSave(ConfigYesNo(default=False))
		self.selectedPaths = []
		self._readConf()
		Setup.__init__(self, session=session, setup="NetworkNFS")
		self["key_yellow"] = StaticText(_("Exports"))
		self["exportsActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.selectExports, _("Select exported directories")),
		}, prio=0, description=_("NFS Setup Actions"))

	def _readConf(self):
		inNfsd = False
		for line in (fileReadLines(self.NFSCONF, source=MODULE_NAME) or []):
			ls = line.lstrip()
			if ls.startswith("[") and ls.rstrip().endswith("]"):
				inNfsd = ls.strip()[1:-1].strip().lower() == "nfsd"
				continue
			if not inNfsd or ls.startswith("#") or "=" not in ls:
				continue
			key, _, val = ls.partition("=")
			key = key.strip().lower()
			val = val.strip()
			if key == "threads":
				try:
					self.nfsThreads.value = int(val)
				except ValueError:
					pass
			elif key == "vers3":
				self.nfsVers3.value = val.lower() in ("y", "yes", "1", "true")
			elif key == "vers4":
				self.nfsVers4.value = val.lower() in ("y", "yes", "1", "true")
		inManaged = False
		parsedOpts = False
		for line in (fileReadLines(self.EXPORTSFILE, source=MODULE_NAME) or []):
			if line.strip() == self._MARKER:
				inManaged = True
				continue
			if not inManaged or not line.strip() or line.strip().startswith("#"):
				continue
			parts = line.split()
			if parts and parts[0] not in self.selectedPaths:
				self.selectedPaths.append(parts[0])
			if not parsedOpts and len(parts) >= 2 and "(" in parts[1]:
				client, _, rest = parts[1].partition("(")
				if client:
					self.nfsClients.value = client
				opts = [o.strip() for o in rest.rstrip(")").split(",")]
				if "ro" in opts:
					self.nfsAccessMode.value = "ro"
				if "root_squash" in opts and "no_root_squash" not in opts:
					self.nfsRootSquash.value = True
				parsedOpts = True

	def keySave(self):
		self._writeNfsConf()
		self._writeExports()
		Setup.keySave(self)

	def _writeNfsConf(self):
		updates = {
			"threads": str(self.nfsThreads.value),
			"vers3": "y" if self.nfsVers3.value else "n",
			"vers4": "y" if self.nfsVers4.value else "n",
		}
		lines = fileReadLines(self.NFSCONF, source=MODULE_NAME) or []
		inNfsd = False
		found = set()
		newLines = []
		for line in lines:
			ls = line.lstrip()
			if ls.startswith("[") and ls.rstrip().endswith("]"):
				if inNfsd:
					for key, val in updates.items():
						if key not in found:
							newLines.append(f"{key} = {val}")
				inNfsd = ls.strip()[1:-1].strip().lower() == "nfsd"
				newLines.append(line)
				continue
			if not inNfsd:
				newLines.append(line)
				continue
			content = ls.lstrip("#").strip()
			if "=" in content:
				key, _, _ = content.partition("=")
				key = key.strip().lower()
				if key in updates and key not in found:
					newLines.append(f"{key} = {updates[key]}")
					found.add(key)
					continue
			newLines.append(line)
		if inNfsd:
			for key, val in updates.items():
				if key not in found:
					newLines.append(f"{key} = {val}")
		tmpPath = f"{self.NFSCONF}.tmp"
		fileWriteLines(tmpPath, newLines, source=MODULE_NAME)
		if exists(tmpPath):
			rename(tmpPath, self.NFSCONF)

	def _writeExports(self):
		squash = "root_squash" if self.nfsRootSquash.value else "no_root_squash"
		opts = f"{self.nfsAccessMode.value},sync,no_subtree_check,{squash}"
		client = self.nfsClients.value.strip() or "*"
		oldLines = fileReadLines(self.EXPORTSFILE, source=MODULE_NAME) or []
		baseLines = []
		for line in oldLines:
			if line.strip() == self._MARKER:
				break
			baseLines.append(line)
		while baseLines and not baseLines[-1].strip():
			baseLines.pop()
		newLines = baseLines + ([""] if baseLines else [])
		newLines.append(self._MARKER)
		for path in self.selectedPaths:
			newLines.append(f"{path}\t{client}({opts})")
		tmpPath = f"{self.EXPORTSFILE}.tmp"
		fileWriteLines(tmpPath, newLines, source=MODULE_NAME)
		if exists(tmpPath):
			rename(tmpPath, self.EXPORTSFILE)

	def selectExports(self):
		def callback(selectedFiles):
			if selectedFiles is not None:
				self.selectedPaths = selectedFiles
		self.session.openWithCallback(callback, uShareSelection, self.selectedPaths)


class NetworkSambaSetup(Setup):
	SMBCONF = "/etc/samba/smb-local.conf"

	def __init__(self, session):
		self.workgroup = NoSave(ConfigText(default="WORKGROUP", fixed_size=False))
		self.guest = NoSave(ConfigYesNo(default=True))
		self.globalLine = 0
		self.workgroupLine = 0
		self.guestLine = 0
		self.smbConf = fileReadLines(self.SMBCONF, default=[], source=MODULE_NAME)
		inGlobal = False
		for index, line in enumerate(self.smbConf):
			line = line.strip()
			if line.startswith("[") and line.endswith("]"):
				inGlobal = line[1:-1].lower() == "global"
				continue
			if inGlobal and "=" in line:
				if self.globalLine == 0:
					self.globalLine = index
				key, value = [x.strip() for x in line.split("=", 1)]
				comment = key.startswith(("#", ";"))
				match key.lstrip("#;").lstrip().lower():
					case "workgroup":
						self.workgroupLine = index
						if not comment:
							self.workgroup.value = value
							self.workgroup.savedValue = value
					case "guest ok":
						self.guestLine = index
						if not comment:
							self.guest.value = value.lower() in ("yes", "true", "1")
							self.guest.savedValue = value
		Setup.__init__(self, session=session, setup="NetworkSamba")

	def keySave(self):
		if self.workgroupLine:
			if self.workgroup.isChanged():
				self.smbConf[self.workgroupLine] = f"\tworkgroup = {self.workgroup.value}"
		elif self.globalLine and self.workgroup.value != self.workgroup.default:
			self.smbConf.insert(self.globalLine, f"\tworkgroup = {self.workgroup.value}")
			self.globalLine += 1
		value = "yes" if self.guest.value else "no"
		if self.guestLine:
			if self.guest.isChanged():
				self.smbConf[self.guestLine] = f"\tguest ok = {value}"
		elif self.globalLine and self.guest.value != self.guest.default:
			self.smbConf.insert(self.globalLine, f"\tguest ok = {value}")
		if fileWriteLines(self.SMBCONF, self.smbConf, source=MODULE_NAME):
			print("Error")
		Setup.keySave(self)


class NetworkPassword(Setup):
	def __init__(self, session):
		config.network.password = NoSave(ConfigPassword(default=""))
		Setup.__init__(self, session=session, setup="Password")
		self["key_yellow"] = StaticText(_("Random Password"))
		self["passwordActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.randomPassword, _("Create a randomly generated password"))
		}, prio=0, description=_("Password Actions"))
		self.user = "root"
		self.counter = 0
		self.timer = eTimer()
		self.timer.callback.append(self.appClosed)
		self.language = "C.UTF-8"  # This is a complete hack to negate all the plugins that inappropriately change the language!

	def appClosed(self, retVal=ETIMEDOUT):
		self.timer.stop()
		if retVal:
			if retVal == ETIMEDOUT:
				self.container.kill()
			print(f"[NetworkSetup] NetworkPassword: Error {retVal}: Unable to change password!  ({strerror(retVal)})")
			self.session.open(MessageBox, _("Error %d: Unable to change password!  (%s)") % (retVal, strerror(retVal)), MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
		elif self.counter == 2:
			print("[NetworkSetup] NetworkPassword: Password changed.")
			self.session.open(MessageBox, _("Password changed."), MessageBox.TYPE_INFO, timeout=5, windowTitle=self.getTitle())
			Setup.keySave(self)
		else:
			print("[NetworkSetup] NetworkPassword: Error: Unexpected program interaction!")
			self.session.open(MessageBox, _("Error: Interaction failure, unable to change password!"), MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
		del self.container.dataAvail[:]
		del self.container.appClosed[:]
		del self.container

	def keySave(self):
		def dataAvail(data):
			data = data.decode("UTF-8", "ignore")
			if data.endswith("password: "):
				self.container.write(f"{config.network.password.value}\n")
				self.counter += 1

		password = config.network.password.value
		if not password:
			print("[NetworkSetup] NetworkPassword: Error: The new password may not be blank!")
			self.session.open(MessageBox, _("Error: The new password may not be blank!"), MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
			return
		# print(f"[NetworkSetup] NetworkPassword: Changing the password for '{self.user}' to '{password}'.")
		print(f"[NetworkSetup] NetworkPassword: Changing the password for '{self.user}'.")
		self.container = eConsoleAppContainer()
		self.container.dataAvail.append(dataAvail)
		self.container.appClosed.append(self.appClosed)
		status = self.container.execute(*("/usr/bin/passwd", "/usr/bin/passwd", self.user))
		if status:  # If status is -1 code is already/still running, is status is -3 code can not be started!
			self.session.open(MessageBox, _("Error %d: Unable to start 'passwd' command!") % status, MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
			Setup.keySave(self)
		else:
			self.timer.start(3000)

	def randomPassword(self):
		from string import ascii_letters, digits
		passwdChars = ascii_letters + digits
		passwdLength = 10
		config.network.password.value = "".join(Random().sample(passwdChars, passwdLength))
		self["config"].invalidateCurrent()


# TODO "NetworkInadynLog" skin?
#
class NetworkLogScreen(Screen):
	def __init__(self, session, title=None, skinName="NetworkInadynLog", logPath="", tailLog=True):
		Screen.__init__(self, session)
		self.setTitle(title if title else _("Network Log"))
		self.skinName = [skinName, "NetworkLogScreen"]
		self.logPath = logPath
		self.tailLog = tailLog
		# self["log"] = ScrollLabel()  # This would make a better widget name.
		self["infotext"] = ScrollLabel()
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Close the screen")),
			"close": (self.closeRecursive, _("Close the screen and exit all menus")),
			"ok": (self.keyCancel, _("Close the screen")),
			"top": (self["infotext"].goTop, _("Move to first line / screen")),
			"pageUp": (self["infotext"].goPageUp, _("Move up a screen")),
			"up": (self["infotext"].goLineUp, _("Move up a line")),
			"down": (self["infotext"].goLineDown, _("Move down a line")),
			"pageDown": (self["infotext"].goPageDown, _("Move down a screen")),
			"bottom": (self["infotext"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Network Log Actions"))
		self.console = Console()
		if self.tailLog:
			self.console.ePopen(["/usr/bin/tail", "/usr/bin/tail", logPath], self.showLog)  # Should the number of lines be specified?  10 lines is probably less than one screen worth!
		else:
			self.showLog()

	def keyCancel(self):
		self.console.killAll()
		self.close()

	def closeRecursive(self):
		self.console.killAll()
		self.close(True)

	def showLog(self, data=None, retVal=None, extraArgs=None):
		lines = []
		if self.tailLog:
			lines = [x.rstrip() for x in data.split("\n")]
		elif self.logPath and exists(self.logPath):
			lines = fileReadLines(self.logPath, [], source=MODULE_NAME)
		self["infotext"].setText("\n".join(lines))


class NetworkZeroTierSetup(Setup):
	ZEROTIERCLI = "/usr/sbin/zerotier-cli"
	ZEROTIERSECRET = "/var/lib/zerotier-one/authtoken.secret"
	ZEROTIERAPI = "http://127.0.0.1:9993"

	def __init__(self, session):
		self.cachedToken = None
		self.lastInfo = None
		self.joined = False
		Setup.__init__(self, session=session, setup="NetworkZeroTier")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText(_("Refresh"))
		self["zerotierActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.toggleJoinLeave, _("Join or leave the configured ZeroTier network")),
			"blue": (self.refreshInfo, _("Refresh ZeroTier status information"))
		}, prio=0, description=_("ZeroTier Actions"))
		self.setJoinLeaveButton()

	def changedEntry(self):
		current = self["config"].getCurrent()
		if current and len(current) > 1 and current[1] is config.network.ZeroTierNetworkId:
			self.createSetup()
			self.setJoinLeaveButton()
		return Setup.changedEntry(self)

	def refreshInfo(self):
		self.createSetup()
		self["config"].invalidateCurrent()
		self.setJoinLeaveButton()

	def readAuthToken(self):
		if self.cachedToken:
			return self.cachedToken
		with open(self.ZEROTIERSECRET, encoding="utf-8", errors="ignore") as fd:
			token = fd.read().strip()
			self.cachedToken = token if token else None
			return self.cachedToken

	def apiRequest(self, method, path, payload=None, timeout=2):
		token = self.readAuthToken()
		url = f"{self.ZEROTIERAPI}{path}"
		headers = {"X-ZT1-Auth": token}

		data = None
		if payload is not None:
			data = dumps(payload).encode("utf-8")
			headers["Content-Type"] = "application/json"

		req = Request(url, data=data, headers=headers, method=method)
		try:
			with urlopen(req, timeout=timeout) as resp:
				body = resp.read().decode("utf-8", "ignore").strip()
				return loads(body) if body else None
		except Exception:
			pass

	def getserviceStatus(self):
		data = self.apiRequest("GET", "/status")
		return {
			"online": bool(data.get("online", False)) if isinstance(data, dict) else False,
			"version": str(data.get("version", "")) if isinstance(data, dict) else "",
			"address": str(data.get("address", "")) if isinstance(data, dict) else ""
		}

	def getMemberships(self):
		data = self.apiRequest("GET", "/network")
		return data if isinstance(data, list) else []

	def isJoined(self, nwid, memberships=None):
		memberships = memberships if memberships is not None else self.getMemberships()
		for m in memberships:
			if isinstance(m, dict) and str(m.get("id", "")).lower() == nwid.lower():
				return True
		return False

	def setJoinLeaveButton(self):
		nwid = str(config.network.ZeroTierNetworkId.value or "").strip()
		if not nwid:
			self["key_yellow"].setText("")
			self["zerotierActions"].setEnabled(False)
			return

		self["zerotierActions"].setEnabled(True)
		self["key_yellow"].setText(_("Leave") if self.joined else _("Join"))

	def toggleJoinLeave(self):
		nwid = str(config.network.ZeroTierNetworkId.value or "").strip()
		if not nwid:
			return

		memberships = self.getMemberships()
		self.joined = self.isJoined(nwid, memberships)

		if self.joined:
			self.zerotierCli(nwid, "leave")
		else:
			self.zerotierCli(nwid, "join")
		self.refreshInfo()

	def createSetup(self):  # NOSONAR silence S2638
		nwid = str(config.network.ZeroTierNetworkId.value or "").strip()
		if not nwid:
			self.lastInfo = None
			Setup.createSetup(self, appendItems=[])
			return

		items = []
		serviceOnline = False
		serviceVersion = ""
		name = ""
		status = ""
		ipv4 = ""
		ipv6 = ""
		serviceStatus = self.getserviceStatus()
		serviceOnline = serviceStatus.get("online", False)
		serviceVersion = serviceStatus.get("version", "")
		memberships = self.getMemberships()
		entry = next((n for n in memberships if str(n.get("nwid") or n.get("id") or "").lower() == nwid.lower()), None)
		self.joined = entry is not None

		if self.joined:
			name = str(entry.get("name", "") or "")
			status = str(entry.get("status", "") or "")
			ips = entry.get("assignedAddresses", []) or []
			ipv4 = next((ip.split("/", 1)[0] for ip in ips if "." in ip), "")
			ipv6 = next((ip.split("/", 1)[0] for ip in ips if ":" in ip), "")
		self.lastInfo = {
			"serviceOnline": serviceOnline,
			"serviceVersion": serviceVersion,
			"joined": self.joined,
			"name": name,
			"status": status,
			"ipv4": ipv4,
			"ipv6": ipv6
		}

		items.append(getConfigListEntry((_("Joined"), 0), ReadOnly(NoSave(ConfigText(default=_("Yes") if self.joined else _("No"), fixed_size=False)))))
		items.append(getConfigListEntry((_("Service online"), 0), ReadOnly(NoSave(ConfigText(default=_("Yes") if serviceOnline else _("No"), fixed_size=False)))))
		if serviceVersion:
			items.append(getConfigListEntry((_("Version"), 0), ReadOnly(NoSave(ConfigText(default=serviceVersion, fixed_size=False)))))

		if self.joined:
			if name:
				items.append(getConfigListEntry((_("Name"), 0), ReadOnly(NoSave(ConfigText(default=name, fixed_size=False)))))
			if status:
				items.append(getConfigListEntry((_("Status"), 0), ReadOnly(NoSave(ConfigText(default=status, fixed_size=False)))))
			items.append(getConfigListEntry((_("Tunnel IPv4"), 0), ReadOnly(NoSave(ConfigText(default=ipv4 or _("N/A"), fixed_size=False)))))
			items.append(getConfigListEntry((_("Tunnel IPv6"), 0), ReadOnly(NoSave(ConfigText(default=ipv6 or _("N/A"), fixed_size=False)))))
		else:
			items.append(getConfigListEntry((_("Info"), 0), ReadOnly(NoSave(ConfigText(default=_("Not joined. Press Yellow to join."), fixed_size=False)))))
		Setup.createSetup(self, appendItems=items)

	def zerotierCli(self, nwid, option):
		if not nwid:
			return False
		background = " "
		if option == "leave":
			background = "&"
			ztIface = next((a for a in listdir("/sys/class/net/") if a.startswith("zt")), "")
			if ztIface:
				Console().ePopen(f"ip link del dev {ztIface}")
		Console().ePopen([self.ZEROTIERCLI, self.ZEROTIERCLI, option, nwid, background])
