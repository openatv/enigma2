from os import F_OK, R_OK, W_OK, access, listdir, makedirs, mkdir, remove, stat
from os.path import dirname, exists, isdir, isfile, join as pathjoin
from stat import ST_MTIME
from pickle import dump, load
from time import time

from enigma import getDesktop, eRCInput, getPrevAsciiCode, eEnv

from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import config
from Components.Console import Console
from Components.Harddisk import harddiskmanager
from Components.Input import Input
from Components.MenuList import MenuList
from Components.Opkg import OpkgComponent
from Components.PluginComponent import plugins
from Components.SelectionList import SelectionList
from Components.SystemInfo import BoxInfo
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Opkg import Opkg
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.Standby import TryQuitMainloop
from Tools.Directories import SCOPE_CURRENT_PLUGIN, SCOPE_GUISKIN, SCOPE_PLUGINS, resolveFilename
from Tools.LoadPixmap import LoadPixmap
from Tools.NumericalTextInput import NumericalTextInput

from .BackupRestore import InitConfig as BackupRestore_InitConfig, BackupSelection, BackupScreen, RestoreScreen, getBackupPath, getOldBackupPath, getBackupFilename, RestoreMenu
from .ImageWizard import ImageWizard
from .ImageBackup import ImageBackup

boxType = BoxInfo.getItem("machinebuild")
config.plugins.configurationbackup = BackupRestore_InitConfig()


def write_cache(cache_file, cache_data):  # Does a cPickle dump.
	if not isdir(dirname(cache_file)):
		try:
			mkdir(dirname(cache_file))
		except OSError:
			print("%s is a file" % dirname(cache_file))
	with open(cache_file, "wb") as fd:
		dump(cache_data, fd, -1)


def valid_cache(cache_file, cache_ttl):  # See if the cache file exists and is still living.
	try:
		mtime = stat(cache_file)[ST_MTIME]
	except OSError:
		return 0
	curr_time = time()
	if (curr_time - mtime) > cache_ttl:
		return 0
	else:
		return 1


def load_cache(cache_file):  # Does a cPickle load.
	cache_data = None
	with open(cache_file, "rb") as fd:
		cache_data = load(fd)
	return cache_data


# Helper for menu.xml
class ImageWizard(ImageWizard):
    pass


class ImageBackup(ImageBackup):
    pass


class RestoreMenu(RestoreMenu):
    pass


class SoftwareManagerSetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "SoftwareManager", plugin="SystemPlugins/SoftwareManager")


class IPKGMenu(Screen):
	skin = """
		<screen name="IPKGMenu" position="center,center" size="560,400" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="filelist" position="5,50" size="550,340" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Select Upgrade Source To Edit"))
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Edit"))
		self.sel = []
		self.val = []
		self.entry = False
		self.exe = False
		self.path = ""
		self["actions"] = HelpableActionMap(self, ["OkCancelActions"], {
			"ok": self.KeyOk,
			"cancel": self.keyCancel
		}, prio=-1)
		self["shortcuts"] = HelpableActionMap(self, ["ColorActions"], {
			"red": self.keyCancel,
			"green": self.KeyOk,
		})
		self["filelist"] = MenuList([])
		self.fill_list()

	def fill_list(self):
		flist = []
		self.path = "/etc/opkg/"
		if (exists(self.path) == False):
			self.entry = False
			return
		for file in listdir(self.path):
			if file.endswith(".conf"):
				if file not in ("arch.conf", "opkg.conf"):
					flist.append((file))
					self.entry = True
		self["filelist"].l.setList(flist)

	def KeyOk(self):
		if (self.exe == False) and (self.entry == True):
			self.sel = self["filelist"].getCurrent()
			self.val = self.path + self.sel
			self.session.open(IPKGSource, self.val)

	def keyCancel(self):
		self.close()

	def Exit(self):
		self.close()


class IPKGSource(Screen):
	skin = """
		<screen name="IPKGSource" position="center,center" size="560,80" title="Edit upgrade source url." >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="text" position="5,50" size="550,25" font="Regular;20" backgroundColor="background" foregroundColor="#cccccc" />
		</screen>"""

	def __init__(self, session, configfile=None):
		Screen.__init__(self, session)
		self.setTitle(_("Edit Upgrade Source URL"))
		self.configfile = configfile
		text = ""
		if self.configfile:
			try:
				fp = open(configfile, "r")
				sources = fp.readlines()
				if sources:
					text = sources[0]
				fp.close()
			except OSError:
				pass
		desk = getDesktop(0)
		x = int(desk.size().width())
		y = int(desk.size().height())
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		if (y >= 720):
			self["text"] = Input(text, maxSize=False, type=Input.TEXT)
		else:
			self["text"] = Input(text, maxSize=False, visible_width=55, type=Input.TEXT)
		self["actions"] = HelpableNumberActionMap(self, ["WizardActions", "InputActions", "TextEntryActions", "KeyboardInputActions", "ShortcutActions"], {
			"ok": self.go,
			"back": self.close,
			"red": self.close,
			"green": self.go,
			"left": self.keyLeft,
			"right": self.keyRight,
			"home": self.keyHome,
			"end": self.keyEnd,
			"deleteForward": self.keyDeleteForward,
			"deleteBackward": self.keyDeleteBackward,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, prio=-1)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["text"].right()

	def go(self):
		text = self["text"].getText()
		if text:
			fp = open(self.configfile, "w")
			fp.write(text)
			fp.write("\n")
			fp.close()
		self.close()

	def keyLeft(self):
		self["text"].left()

	def keyRight(self):
		self["text"].right()

	def keyHome(self):
		self["text"].home()

	def keyEnd(self):
		self["text"].end()

	def keyDeleteForward(self):
		self["text"].delete()

	def keyDeleteBackward(self):
		self["text"].deleteBackward()

	def keyNumberGlobal(self, number):
		self["text"].number(number)


class PacketManager(Screen, NumericalTextInput):
	skin = """
		<screen name="PacketManager" position="center,center" size="530,420" title="Packet Manager" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="list" render="Listbox" position="5,50" size="520,365" scrollbarMode="showOnDemand">
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (5, 1), size = (440, 28), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the name
							MultiContentEntryText(pos = (5, 26), size = (440, 20), font=1, flags = RT_HALIGN_LEFT, text = 2), # index 2 is the description
							MultiContentEntryPixmapAlphaTest(pos = (445, 2), size = (48, 48), png = 4), # index 4 is the status pixmap
							MultiContentEntryPixmapAlphaTest(pos = (5, 50), size = (510, 2), png = 5), # index 4 is the div pixmap
						],
					"fonts": [gFont("Regular", 22),gFont("Regular", 14)],
					"itemHeight": 52
					}
				</convert>
			</widget>
		</screen>"""

	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		NumericalTextInput.__init__(self)
		self.setTitle(_("Packet Manager"))
		self.setUseableChars(u"1234567890abcdefghijklmnopqrstuvwxyz")
		self["shortcuts"] = HelpableNumberActionMap(self, ["ShortcutActions", "WizardActions", "NumberActions", "InputActions", "InputAsciiActions", "KeyboardInputActions"], {
			"ok": self.go,
			"back": self.exit,
			"red": self.exit,
			"green": self.reload,
			"gotAsciiCode": self.keyGotAscii,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, prio=-1)
		self.packageList = []
		self.statuslist = []
		self["list"] = List(self.packageList)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Reload"))
		self.packageList_updating = True
		self.packetlist = []
		self.installed_packetlist = {}
		self.upgradeable_packages = {}
		self.Console = Console()
		self.cmdList = []
		self.cachelist = []
		self.cache_ttl = 86400  # 600 is default, 0 disables, Seconds cache is considered valid (24h should be okay for caching ipkgs).
		self.cache_file = eEnv.resolve("${libdir}/enigma2/python/Plugins/SystemPlugins/SoftwareManager/packetmanager.cache")  # Path to cache directory.
		self.okText = _("After pressing OK, please wait!")
		self.unwanted_extensions = ("-dbg", "-dev", "-doc", "-staticdev", "-src", "busybox")
		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)
		self.onLayoutFinish.append(self.rebuildList)
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmAscii)

	def keyNumberGlobal(self, val):
		key = self.getKey(val)
		if key is not None:
			keyvalue = key.encode("utf-8")
			if len(keyvalue) == 1:
				self.setNextIdx(keyvalue[0])

	def keyGotAscii(self):
		keyvalue = chr(getPrevAsciiCode())
		if len(keyvalue) == 1:
			self.setNextIdx(keyvalue[0])

	def setNextIdx(self, char):
		if char in ("0", "1", "a"):
			self["list"].setIndex(0)
		else:
			idx = self.getNextIdx(char)
			if idx and idx <= self["list"].count:
				self["list"].setIndex(idx)

	def getNextIdx(self, char):
		for idx, i in enumerate(self["list"].list):
			if i[0] and (i[0][0] == char):
				return idx

	def exit(self):
		self.opkg.stop()
		if self.Console is not None:
			if len(self.Console.appContainers):
				for name in list(self.Console.appContainers.keys()):
					self.Console.kill(name)
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)
		self.close()

	def reload(self):
		if (exists(self.cache_file) == True):
			remove(self.cache_file)
			self.packageList_updating = True
			self.rebuildList()

	def setStatus(self, status=None):
		if status:
			self.statuslist = []
			divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
			if status == "update":
				if isfile(resolveFilename(SCOPE_GUISKIN, "icons/upgrade.png")):
					statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/upgrade.png"))
				else:
					statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/upgrade.png"))
				self.statuslist.append((_("Package list update"), "", _("Trying to download a new packet list. Please wait..."), "", statuspng, divpng))
				self["list"].setList(self.statuslist)
			elif status == "error":
				if isfile(resolveFilename(SCOPE_GUISKIN, "icons/remove.png")):
					statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/remove.png"))
				else:
					statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/remove.png"))
				self.statuslist.append((_("Error"), "", _("An error occurred while downloading the packet list. Please try again."), "", statuspng, divpng))
				self["list"].setList(self.statuslist)

	def rebuildList(self):
		self.setStatus("update")
		self.inv_cache = 0
		self.vc = valid_cache(self.cache_file, self.cache_ttl)
		if self.cache_ttl > 0 and self.vc != 0:
			try:
				self.buildPacketList()
			except:
				self.inv_cache = 1
		if self.cache_ttl == 0 or self.inv_cache == 1 or self.vc == 0:
			self.run = 0
			self.opkg.startCmd(OpkgComponent.CMD_UPDATE)

	def go(self, returnValue=None):
		cur = self["list"].getCurrent()
		if cur:
			status = cur[3]
			package = cur[0]
			self.cmdList = []
			if status == "installed":
				self.cmdList.append((OpkgComponent.CMD_REMOVE, {"package": package}))
				if len(self.cmdList):
					self.session.openWithCallback(self.runRemove, MessageBox, _("Do you want to remove the package:\n") + package + "\n" + self.okText)
			elif status == "upgradeable":
				self.cmdList.append((OpkgComponent.CMD_INSTALL, {"package": package}))
				if len(self.cmdList):
					self.session.openWithCallback(self.runUpgrade, MessageBox, _("Do you want to upgrade the package:\n") + package + "\n" + self.okText)
			elif status == "installable":
				self.cmdList.append((OpkgComponent.CMD_INSTALL, {"package": package}))
				if len(self.cmdList):
					self.session.openWithCallback(self.runUpgrade, MessageBox, _("Do you want to install the package:\n") + package + "\n" + self.okText)

	def runRemove(self, result):
		if result:
			self.session.openWithCallback(self.runRemoveFinished, Opkg, cmdList=self.cmdList)

	def runRemoveFinished(self):
		self.session.openWithCallback(self.RemoveReboot, MessageBox, _("Remove Finished.") + " " + _("Do you want to reboot your receiver?"), MessageBox.TYPE_YESNO)

	def RemoveReboot(self, result):
		if result is None:
			return
		if result is False:
			cur = self["list"].getCurrent()
			if cur:
				item = self["list"].getIndex()
				self.packageList[item] = self.buildEntryComponent(cur[0], cur[1], cur[2], "installable")
				self.cachelist[item] = [cur[0], cur[1], cur[2], "installable"]
				self["list"].setList(self.packageList)
				write_cache(self.cache_file, self.cachelist)
				self.reloadPluginlist()
		if result:
			self.session.open(TryQuitMainloop, retvalue=3)

	def runUpgrade(self, result):
		if result:
			self.session.openWithCallback(self.runUpgradeFinished, Opkg, cmdList=self.cmdList)

	def runUpgradeFinished(self):
		self.session.openWithCallback(self.UpgradeReboot, MessageBox, _("Upgrade finished.") + " " + _("Do you want to reboot your receiver?"), MessageBox.TYPE_YESNO)

	def UpgradeReboot(self, result):
		if result is None:
			return
		if result is False:
			cur = self["list"].getCurrent()
			if cur:
				item = self["list"].getIndex()
				self.packageList[item] = self.buildEntryComponent(cur[0], cur[1], cur[2], "installed")
				self.cachelist[item] = [cur[0], cur[1], cur[2], "installed"]
				self["list"].setList(self.packageList)
				write_cache(self.cache_file, self.cachelist)
				self.reloadPluginlist()
		if result:
			self.session.open(TryQuitMainloop, retvalue=3)

	def opkgCallback(self, event, param):
		if event == OpkgComponent.EVENT_ERROR:
			self.packageList_updating = False
			self.setStatus("error")
		elif event == OpkgComponent.EVENT_DONE:
			if self.packageList_updating:
				self.packageList_updating = False
				if not self.Console:
					self.Console = Console()
				cmd = self.opkg.opkg + " list"
				self.Console.ePopen(cmd, self.OpkgList_Finished)

	def OpkgList_Finished(self, result, retval, extra_args=None):
		if result:
			result = result.replace("\n ", " - ")
			self.packetlist = []
			last_name = ""
			for x in result.splitlines():
				tokens = x.split(" - ")
				name = tokens[0].strip()
				if not any((name.endswith(x) or name.find("locale") != -1) for x in self.unwanted_extensions):
					l = len(tokens)
					version = l > 1 and tokens[1].strip() or ""
					descr = l > 3 and tokens[3].strip() or l > 2 and tokens[2].strip() or ""
					if name == last_name:
						continue
					last_name = name
					self.packetlist.append([name, version, descr])
		if not self.Console:
			self.Console = Console()
		cmd = self.opkg.opkg + " list_installed"
		self.Console.ePopen(cmd, self.OpkgListInstalled_Finished)

	def OpkgListInstalled_Finished(self, result, retval, extra_args=None):
		if result:
			self.installed_packetlist = {}
			for x in result.splitlines():
				tokens = x.split(" - ")
				name = tokens[0].strip()
				if not any(name.endswith(x) for x in self.unwanted_extensions):
					l = len(tokens)
					version = l > 1 and tokens[1].strip() or ""
					self.installed_packetlist[name] = version
		if not self.Console:
			self.Console = Console()
		cmd = "opkg list-upgradable"
		self.Console.ePopen(cmd, self.OpkgListUpgradeable_Finished)

	def OpkgListUpgradeable_Finished(self, result, retval, extra_args=None):
		if result:
			self.upgradeable_packages = {}
			for x in result.splitlines():
				tokens = x.split(" - ")
				name = tokens[0].strip()
				if not any(name.endswith(x) for x in self.unwanted_extensions):
					l = len(tokens)
					version = l > 2 and tokens[2].strip() or ""
					self.upgradeable_packages[name] = version
		self.buildPacketList()

	def buildEntryComponent(self, name, version, description, state):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
		if not description:
			description = "No description available."
		imagePath = resolveFilename(SCOPE_GUISKIN, "icons/%s.png" % state)
		statusPng = LoadPixmap(cached=True, path=imagePath)
		return ((name, version, _(description), state, statusPng, divpng))

	def buildPacketList(self):
		self.packageList = []
		self.cachelist = []
		if self.cache_ttl > 0 and self.vc != 0:
			print("Loading packagelist cache from %s" % self.cache_file)
			try:
				self.cachelist = load_cache(self.cache_file)
				if len(self.cachelist) > 0:
					for x in self.cachelist:
						self.packageList.append(self.buildEntryComponent(x[0], x[1], x[2], x[3]))
					self["list"].setList(self.packageList)
			except:
				self.inv_cache = 1
		if self.cache_ttl == 0 or self.inv_cache == 1 or self.vc == 0:
			print("rebuilding fresh package list")
			for x in self.packetlist:
				status = "installable"
				if x[0] in self.installed_packetlist:
					status = "upgradeable" if x[0] in self.upgradeable_packages else "installed"
				self.packageList.append(self.buildEntryComponent(x[0], x[1], x[2], status))
				self.cachelist.append([x[0], x[1], x[2], status])
			write_cache(self.cache_file, self.cachelist)
			self["list"].setList(self.packageList)

	def reloadPluginlist(self):
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))


class IpkgInstaller(Screen):
	skin = """
		<screen name="IpkgInstaller" position="center,center" size="550,450" title="Install extensions" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget name="list" position="5,50" size="540,360" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,410" zPosition="10" size="560,2" transparent="1" alphatest="on" />
			<widget source="introduction" render="Label" position="5,420" zPosition="10" size="550,30" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""

	def __init__(self, session, list):
		Screen.__init__(self, session)
		self.selectionList = SelectionList()
		self["list"] = self.selectionList
		p = 0
		if len(list):
			p = list[0].rfind("/")
			title = list[0][:p]
			self.title = ("%s %s %s") % (_("Install extensions"), _("from"), title)
		for listindex in range(len(list)):
			self.selectionList.addSelection(list[listindex][p + 1:], list[listindex], listindex, False)
		self.selectionList.sort()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Install"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText(_("Invert"))
		self["introduction"] = StaticText(_("Press OK to toggle the selection."))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"ok": self.selectionList.toggleSelection,
			"cancel": self.close,
			"red": self.close,
			"green": self.install,
			"blue": self.selectionList.toggleAllSelection
		}, prio=-1)

	def install(self):
		packages = self.selectionList.getSelectionsList()
		cmdList = [(OpkgComponent.CMD_UPDATE, None)]
		for item in packages:
			cmdList.append((OpkgComponent.CMD_INSTALL, {"package": item[1]}))
		self.session.open(Opkg, cmdList=cmdList)


def filescan_open(list, session, **kwargs):
	filelist = [x.path for x in list]
	session.open(IpkgInstaller, filelist)  # List.


def filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	return Scanner(mimetypes=["application/x-debian-package"], paths_to_scan=[
		ScanPath(path="ipk", with_subdirs=True),
		ScanPath(path="", with_subdirs=False),
	], name="Ipkg", description=_("Install extensions."), openfnc=filescan_open)


class BackupHelper(Screen):
	skin = """
		<screen name="BackupHelper" position="0,0" size="1,1" title="SoftwareManager">
		</screen>"""

	def __init__(self, session, args=0):
		Screen.__init__(self, session)
		self.args = args
		self.backuppath = getBackupPath()
		if not isdir(self.backuppath):
			self.backuppath = getOldBackupPath()
		self.backupfile = getBackupFilename()
		self.fullbackupfilename = pathjoin(self.backuppath, self.backupfile)
		self.callLater(self.doAction)

	def doAction(self):
		doClose = True
		if self.args == 1:
			self.session.openWithCallback(self.backupDone, BackupScreen, runBackup=True)
			doClose = False
		elif self.args == 2:
			if isfile(self.fullbackupfilename):
				self.session.openWithCallback(self.startRestore, MessageBox, _("Are you sure you want to restore the backup?\nYour receiver will restart after the backup has been restored!"), default=False)
				doClose = False
			else:
				self.session.open(MessageBox, _("Sorry, no backups found!"), MessageBox.TYPE_INFO, timeout=10)
		elif self.args == 3:
			try:
				from Plugins.Extensions.MediaScanner.plugin import scan
				scan(self.session, self)
				doClose = False
			except:
				self.session.open(MessageBox, _("Sorry, %s has not been installed!") % ("MediaScanner"), MessageBox.TYPE_INFO, timeout=10)
		elif self.args == 4:
			seenMountPoints = []  # DEBUG: Fix Hardisk.py to remove duplicated mount points!
			choices = []
			oldpath = config.plugins.configurationbackup.backuplocation.value
			index = 0
			for partition in harddiskmanager.getMountedPartitions(onlyhotplug=False):
				path = pathjoin(partition.mountpoint, "")
				if path in seenMountPoints:  # TODO: Fix Hardisk.py to remove duplicated mount points!
					continue
				if access(path, F_OK | R_OK | W_OK) and path != "/":
					seenMountPoints.append(path)
					choices.append(("%s (%s)" % (path, partition.description), path))
					if oldpath and oldpath == path:
						index = len(choices) - 1

			def backuplocationCB(path):
				if path:
					oldpath = config.plugins.configurationbackup.backuplocation.value
					config.plugins.configurationbackup.backuplocation.setValue(path)
					config.plugins.configurationbackup.backuplocation.save()
					config.plugins.configurationbackup.save()
					config.save()
					if path != oldpath:
						print("Creating backup folder if not already there...")
						self.backuppath = getBackupPath()
						try:
							if not exists(self.backuppath):
								makedirs(self.backuppath)
						except OSError:
							self.session.open(MessageBox, _("Sorry, your backup destination is not writeable.\nPlease select a different one."), MessageBox.TYPE_INFO, timeout=10)
				self.close()

			if len(choices):
				self.session.openWithCallback(backuplocationCB, MessageBox, _("Please select medium to use as backup location"), list=choices, default=index, windowTitle=_("Backup Location"))
				doClose = False
			else:
				self.session.open(MessageBox, _("No suitable backup locations found!"), MessageBox.TYPE_ERROR, timeout=5)
		elif self.args == 5:
			self.session.open(BackupSelection, title=_("Default files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs_default, readOnly=True, mode="backupfiles")
		elif self.args == 6:
			self.session.open(BackupSelection, title=_("Additional files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs, readOnly=False, mode="backupfiles_addon")
		elif self.args == 7:
			self.session.open(BackupSelection, title=_("Files/folders to exclude from backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs_exclude, readOnly=False, mode="backupfiles_exclude")
		if doClose:
			self.close()

	def startRestore(self, ret=False):
		if (ret == True):
			self.exe = True
			self.session.open(RestoreScreen, runRestore=True)
		self.close()

	def backupDone(self, retval=None):
		message = _("Backup completed.") if retval else _("Backup failed.")
		self.session.open(MessageBox, message, MessageBox.TYPE_INFO, timeout=10)
		self.close()


def Plugins(path, **kwargs):
	return [PluginDescriptor(name=_("Ipkg"), where=PluginDescriptor.WHERE_FILESCAN, needsRestart=False, fnc=filescan)]
