from datetime import date
from glob import glob
from os import access, makedirs, listdir, stat, rename, remove, F_OK, R_OK, W_OK
from os.path import exists, isdir, join

from enigma import eTimer, eEnv, eConsoleAppContainer, eEPGCache
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Components.Button import Button
from Components.config import NoSave, configfile, ConfigSubsection, ConfigText, ConfigLocations
from Components.config import config
from Components.ConfigList import ConfigListScreen
from Components.FileList import MultiFileSelectList
from Components.Harddisk import harddiskmanager
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Screens.RestartNetwork import RestartNetwork
from Screens.Screen import Screen
from Tools.Directories import fileWriteLines, resolveFilename, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap
from . import ShellCompatibleFunctions


MACHINEBUILD = BoxInfo.getItem("machinebuild")


def eEnv_resolve_multi(path):
	resolve = eEnv.resolve(path)
	return [] if resolve == path else resolve.split()


# MANDATORY_RIGHTS contains commands to ensure correct rights for certain files, shared with ShellCompatibleFunctions for FastRestore
MANDATORY_RIGHTS = ShellCompatibleFunctions.MANDATORY_RIGHTS + " ; exit 0"

# BLACKLISTED lists all files/folders that MUST NOT be backed up or restored in order for the image to work properly, shared with ShellCompatibleFunctions for FastRestore
BLACKLISTED = ShellCompatibleFunctions.BLACKLISTED


def InitConfig():
	# BACKUPFILES contains all files and folders to back up, for wildcard entries ALWAYS use eEnv_resolve_multi!
	BACKUPFILES = ["/etc/enigma2/", "/etc/CCcam.cfg", "/usr/keys/",
		"/etc/davfs2/", "/etc/tuxbox/config/", "/etc/auto.network", "/etc/feeds.xml", "/etc/machine-id", "/etc/rc.local",
		"/etc/openvpn/", "/etc/ipsec.conf", "/etc/ipsec.secrets", "/etc/ipsec.user", "/etc/strongswan.conf", "/etc/vtuner.conf",
		"/etc/default/crond", "/etc/dropbear/", "/etc/default/dropbear", "/home/", "/etc/samba/", "/etc/fstab", "/etc/inadyn.conf",
		"/etc/network/interfaces", "/etc/wpa_supplicant.conf", "/etc/wpa_supplicant.ath0.conf", "/etc/ciplus/", "/etc/udev/known_devices",
		"/etc/wpa_supplicant.wlan0.conf", "/etc/wpa_supplicant.wlan1.conf", "/etc/resolv.conf", "/etc/enigma2/nameserversdns.conf", "/etc/default_gw", "/etc/hostname", "/etc/hosts", "/etc/epgimport/", "/etc/exports",
		"/etc/enigmalight.conf", "/etc/enigma2/volume.xml", "/etc/enigma2/ci_auth_slot_0.bin", "/etc/enigma2/ci_auth_slot_1.bin", "/etc/PrivateKey.key",
		"/usr/lib/enigma2/python/Plugins/Extensions/VMC/DB/",
		"/usr/lib/enigma2/python/Plugins/Extensions/VMC/youtv.pwd",
		"/usr/lib/enigma2/python/Plugins/Extensions/VMC/vod.config",
		"/usr/share/enigma2/MetrixHD/skinparts/",
		"/usr/share/enigma2/display/skin_display_usr.xml",
		"/usr/share/enigma2/display/userskin.png",
		"/usr/lib/enigma2/python/Plugins/Extensions/SpecialJump/keymap_user.xml",
		"/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db",
		"/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db",
		"/usr/lib/enigma2/python/Plugins/Extensions/TVSpielfilm/db", "/etc/ConfFS",
		"/etc/rc3.d/S99tuner.sh",
		"/usr/bin/enigma2_pre_start.sh",
		eEnv.resolve("${datadir}/enigma2/keymap.usr"),
		eEnv.resolve("${datadir}/enigma2/keymap_usermod.xml")]\
		+ eEnv_resolve_multi("${sysconfdir}/opkg/*-secret-feed.conf")\
		+ eEnv_resolve_multi("${datadir}/enigma2/*/mySkin_off")\
		+ eEnv_resolve_multi("${datadir}/enigma2/*/mySkin")\
		+ eEnv_resolve_multi("${datadir}/enigma2/*/skin_user_*.xml")\
		+ eEnv_resolve_multi("/etc/*.emu")\
		+ eEnv_resolve_multi("${sysconfdir}/cron*")\
		+ eEnv_resolve_multi("${sysconfdir}/init.d/softcam*")\
		+ eEnv_resolve_multi("${sysconfdir}/init.d/cardserver*")\
		+ eEnv_resolve_multi("${sysconfdir}/sundtek.*")\
		+ eEnv_resolve_multi("/usr/sundtek/*")\
		+ eEnv_resolve_multi("/opt/bin/*")\
		+ eEnv_resolve_multi("/usr/script/*")

	# Drop non existant paths from list
	backupset = [f for f in BACKUPFILES if exists(f)]

	config.plugins.configurationbackup = ConfigSubsection()
	defaultlocation = "/media/hdd/"
	if MACHINEBUILD in ("maram9", "classm", "axodin", "axodinc", "starsatlx", "genius", "evo", "galaxym6") and not exists(f"/media/hdd/backup_{MACHINEBUILD}"):
		defaultlocation = "/media/backup/"
	config.plugins.configurationbackup.backuplocation = ConfigText(default=defaultlocation, visible_width=50, fixed_size=False)
	config.plugins.configurationbackup.backupdirs_default = NoSave(ConfigLocations(default=backupset))
	config.plugins.configurationbackup.backupdirs = ConfigLocations(default=[])  # "backupdirs_addon" is called "backupdirs" for backwards compatibility, holding the user"s old selection, duplicates are removed during backup
	config.plugins.configurationbackup.backupdirs_exclude = ConfigLocations(default=[])
	return config.plugins.configurationbackup


config.plugins.configurationbackup = InitConfig()


def getBackupPath():
	backuppath = config.plugins.configurationbackup.backuplocation.value
	return join(backuppath, f"backup_{BoxInfo.getItem('distro')}_{MACHINEBUILD}")


def getOldBackupPath():
	backuppath = config.plugins.configurationbackup.backuplocation.value
	return join(backuppath, "backup")


def getBackupFilename():
	return "enigma2settingsbackup.tar.gz"


def SettingsEntry(name, checked):
	picture = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, f"skin_default/icons/lock_{'on' if checked else 'off'}.png"))
	return (name, picture, checked)


class BackupScreen(ConfigListScreen, Screen):
	skin = """
		<screen position="0,0" size="0,0" title="" >
		<widget name="config" position="10,10" size="330,250" transparent="1" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, runBackup=False, closeOnSuccess=True):
		Screen.__init__(self, session)
		self.setTitle(_("Backup is running..."))
		self["actions"] = ActionMap(["WizardActions", "DirectionActions"],
		{
			"ok": self.close,
			"back": self.close,
			"cancel": self.close,
		}, -1)
		self.finishedCallback = None
		self.closeOnSuccess = closeOnSuccess
		self.list = []
		self.backuppath = getBackupPath()  # Used in ImageWizard
		ConfigListScreen.__init__(self, self.list)  # Used in ImageWizard
		if runBackup:
			self.callLater(self.doBackup)

	def doBackup(self):
		def backuplocationCB(path):
			if path:
				config.plugins.configurationbackup.backuplocation.value = path
				config.plugins.configurationbackup.backuplocation.save()
				config.plugins.configurationbackup.save()
				config.save()
				self.shutdownOKOld = config.usage.shutdownOK.value
				config.usage.shutdownOK.setValue(True)
				config.usage.shutdownOK.save()
				configfile.save()
				self.backuppath = getBackupPath()
				try:
					if config.plugins.softwaremanager.epgcache.value:
						eEPGCache.getInstance().save()
				except Exception:
					pass
				try:
					backupFile = getBackupFilename()
					if exists(self.backuppath) is False:
						makedirs(self.backuppath)
					fullbackupFilename = join(self.backuppath, backupFile)
					if not hasattr(config.plugins, "configurationbackup"):
						InitConfig()
					backupDirs = " ".join(f.strip("/") for f in config.plugins.configurationbackup.backupdirs_default.value)
					for f in config.plugins.configurationbackup.backupdirs.value:
						if f.strip("/") not in backupDirs:
							backupDirs += f" {f.strip('/')}"
					for file in ("installed-list.txt", "changed-configfiles.txt", "passwd.txt", "groups.txt"):
						if f"tmp/{file}" not in backupDirs:
							backupDirs += f" tmp/{file}"

					ShellCompatibleFunctions.backupUserDB()
					pkgs = ShellCompatibleFunctions.listpkg(type="user")
					fileWriteLines("/tmp/installed-list.txt", pkgs)
					if exists("/usr/lib/package.lst"):
						pkgs = ShellCompatibleFunctions.listpkg(type="installed")
						with open("/usr/lib/package.lst") as fd:
							installed = set(line.split()[0] for line in pkgs)
							preinstalled = set(line.split()[0] for line in fd)
							removed = preinstalled - installed
							removed = [package for package in removed if package.startswith("enigma2-plugin-") or package.startswith("enigma2-locale-")]
							if removed:
								fileWriteLines("/tmp/removed-list.txt", removed)
								backupDirs += " tmp/removed-list.txt"
					tarCmd = f"tar -C / -czvf {fullbackupFilename}"
					for f in config.plugins.configurationbackup.backupdirs_exclude.value:
						tarCmd += f" --exclude {f.strip('/')}"
					for f in BLACKLISTED:
						tarCmd += f" --exclude {f.strip('/')}"
					tarCmd += f" {backupDirs}"
					cmdList = ["opkg list-changed-conffiles > /tmp/changed-configfiles.txt", tarCmd]
					if exists(fullbackupFilename):
						dt = str(date.fromtimestamp(stat(fullbackupFilename).st_ctime))
						newFilename = join(self.backuppath, f"{dt}-{backupFile}")
						if exists(newFilename):
							remove(newFilename)
						rename(fullbackupFilename, newFilename)
					self.session.openWithCallback(self.backupFinishedCB, Console, title=self.screenTitle, cmdlist=cmdList, closeOnSuccess=self.closeOnSuccess, showScripts=False)
				except OSError:
					self.session.openWithCallback(self.backupErrorCB, MessageBox, _("Sorry, your backup destination is not writeable.\nPlease select a different one."), MessageBox.TYPE_INFO, timeout=10)
			else:
				self.close(True)

		seenMountPoints = []  # DEBUG: Fix Hardisk.py to remove duplicated mount points!
		choices = []
		oldpath = config.plugins.configurationbackup.backuplocation.value
		index = 0
		for partition in harddiskmanager.getMountedPartitions(onlyhotplug=False):
			path = join(partition.mountpoint, "")
			if path in seenMountPoints:  # TODO: Fix Hardisk.py to remove duplicated mount points!
				continue
			if access(path, F_OK | R_OK | W_OK) and path != "/":
				seenMountPoints.append(path)
				choices.append(("%s (%s)" % (path, partition.description), path))
				if oldpath and oldpath == path:
					index = len(choices) - 1

		if len(choices):
			if len(choices) > 1:
				self.session.openWithCallback(backuplocationCB, MessageBox, _("Please select medium to use as backup location"), list=choices, default=index, windowTitle=_("Backup Location"))
			else:
				backuplocationCB(choices[0][1])
		else:
			self.session.open(MessageBox, _("No suitable backup locations found!"), MessageBox.TYPE_ERROR, timeout=5)

	def backupFinishedCB(self, retval=None):
		print("[BackupScreen] DEBUG backupFinishedCB")
		if self.finishedCallback:
			self.finishedCallback()
		else:
			config.usage.shutdownOK.setValue(self.shutdownOKOld)
			config.usage.shutdownOK.save()
			configfile.save()
			self.close(True)

	def backupErrorCB(self, retval=None):
		if self.finishedCallback:
			self.finishedCallback()
		else:
			self.close(False)

	def runAsync(self, finished_cb):  # Called from ImageWizard
		self.finishedCallback = finished_cb
		self.doBackup()


class BackupSelection(Screen):
	skin = """
		<screen name="BackupSelection" position="center,center" size="560,400" title="Select files/folders to backup" resolution="1280,720">
			<ePixmap pixmap="buttons/red.png" position="0,340" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/green.png" position="140,340" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/yellow.png" position="280,340" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="Title" render="Label" position="10,0" size="540,30" font="Regular;24" halign="left" foregroundColor="white" backgroundColor="black" transparent="1" />
			<widget source="summary_description" render="Label" position="5,300" size="550,30" foregroundColor="white" backgroundColor="black" font="Regular; 24" halign="left" transparent="1" />
			<widget name="checkList" position="5,50" size="550,250" transparent="1" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, title=_("Select files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs, readOnly=False, mode=""):
		Screen.__init__(self, session)
		self.setTitle(title)
		self.mode = mode
		self.readOnly = readOnly
		self.configBackupDirs = configBackupDirs
		self["key_red"] = StaticText(_("Exit") if self.readOnly else _("Cancel"))
		self["key_green"] = StaticText("" if self.readOnly else _("Save"))
		self["key_yellow"] = StaticText(_("Info") if self.readOnly else "")
		self["summary_description"] = StaticText(_("default"))

		self.selectedFiles = self.configBackupDirs.value
		defaultDir = "/"
		inhibitDirs = ["/bin", "/boot", "/dev", "/autofs", "/lib", "/proc", "/sbin", "/sys", "/hdd", "/tmp", "/mnt", "/media"]
		self.filelist = MultiFileSelectList(self.selectedFiles, defaultDir, inhibitDirs=inhibitDirs)
		self["checkList"] = self.filelist

		self["actions"] = ActionMap(["DirectionActions", "OkCancelActions", "ColorActions", "InfoActions"],
		{
			"cancel": self.exit,
			"red": self.exit,
			"yellow": self.changeSelectionState,
			"green": self.saveSelection,
			"ok": self.okClicked,
			"left": self.left,
			"right": self.right,
			"down": self.down,
			"up": self.up,
			"info": self.keyInfo
		}, -1)
		if self.selectionChanged not in self["checkList"].onSelectionChanged:
			self["checkList"].onSelectionChanged.append(self.selectionChanged)
		self.onLayoutFinish.append(self.layoutFinished)

	def keyInfo(self):
		if self.mode in ("backupfiles", "backupfiles_exclude", "backupfiles_addon"):
			self.session.open(SoftwareManagerInfo, mode="backupinfo", submode=self.mode)

	def layoutFinished(self):
		idx = 0
		self["checkList"].moveToIndex(idx)
		self.selectionChanged()

	def selectionChanged(self):
		current = self["checkList"].getCurrent()[0]
		self["summary_description"].text = self["checkList"].getName()
		if self.readOnly:
			return
		self["key_yellow"].setText(_("Deselect") if current[2] else _("Select"))

	def up(self):
		self["checkList"].up()

	def down(self):
		self["checkList"].down()

	def left(self):
		self["checkList"].pageUp()

	def right(self):
		self["checkList"].pageDown()

	def changeSelectionState(self):
		if self.readOnly:
			self.session.open(MessageBox, _("The default backup selection cannot be changed.\nPlease use the 'additional' and 'excluded' backup selection."), type=MessageBox.TYPE_INFO, timeout=10)
		else:
			self["checkList"].changeSelectionState()
			self.selectedFiles = self["checkList"].getSelectedList()

	def saveSelection(self):
		if self.readOnly:
			pass
			#self.close(None)
		else:
			self.selectedFiles = self["checkList"].getSelectedList()
			self.configBackupDirs.setValue(self.selectedFiles)
			self.configBackupDirs.save()
			config.plugins.configurationbackup.save()
			config.save()
			self.close(None)

	def exit(self):
		self.close(None)

	def okClicked(self):
		if self.filelist.canDescent():
			self.filelist.descent()


class RestoreMenu(Screen):
	skin = """
		<screen name="RestoreMenu" position="center,center" size="560,400" title="Restore backups" resolution="1280,720">
			<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget name="filelist" position="5,50" size="550,230" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Restore backups"))

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Restore"))
		self["key_yellow"] = StaticText(_("Delete"))
		self["summary_description"] = StaticText("")

		self.sel = []
		self.val = []
		self.entry = False
		self.exe = False

		self.path = ""

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.KeyOk,
			"cancel": self.keyCancel,
			"up": self.keyUp,
			"down": self.keyDown
		}, -1)

		self["shortcuts"] = ActionMap(["ColorActions"],
		{
			"red": self.keyCancel,
			"green": self.KeyOk,
			"yellow": self.deleteFile,
		})
		self.flist = []
		self["filelist"] = MenuList(self.flist)
		self.fill_list()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.checkSummary()

	def fill_list(self):
		self.flist = []
		self.path = getBackupPath()
		if not exists(self.path):
			makedirs(self.path)
		for file in listdir(self.path):
			if file.endswith(".tar.gz"):
				self.flist.append(file)
				self.entry = True
		self.flist.sort(reverse=True)
		self["filelist"].l.setList(self.flist)

	def KeyOk(self):
		if (self.exe is False) and (self.entry is True):
			self.sel = self["filelist"].getCurrent()
			if self.sel:
				self.val = join(self.path, self.sel)
				self.session.openWithCallback(self.startRestore, MessageBox, _("Are you sure you want to restore\nthe following backup:\n%s\nYour receiver will restart after the backup has been restored!") % self.sel)

	def keyCancel(self):
		self.close()

	def keyUp(self):
		self["filelist"].up()
		self.checkSummary()

	def keyDown(self):
		self["filelist"].down()
		self.checkSummary()

	def startRestore(self, ret=False):
		if ret:
			self.session.openWithCallback(self.CB_startRestore, MessageBox, _("Do you want to delete the old settings in /etc/enigma2 first?"))

	def CB_startRestore(self, ret=False):
		self.exe = True
		tarcmd = f"tar -C / -xzvf {join(self.path, self.sel)}"
		for f in BLACKLISTED:
			tarcmd += f" --exclude {f.strip('/')}"

		cmds = [tarcmd, MANDATORY_RIGHTS, "/etc/init.d/autofs restart", "killall -9 enigma2"]
		if ret:
			cmds.insert(0, "rm -R /etc/enigma2")
		self.session.open(Console, title=_("Restoring..."), cmdlist=cmds, showScripts=False)

	def deleteFile(self):
		if (self.exe is False) and (self.entry is True):
			self.sel = self["filelist"].getCurrent()
			if self.sel:
				self.val = join(self.path, self.sel)
				self.session.openWithCallback(self.startDelete, MessageBox, _("Are you sure you want to delete\nthe following backup:\n") + self.sel)

	def startDelete(self, ret=False):
		if ret:
			self.exe = True
			print(f"removing: {self.val}")
			if exists(self.val):
				remove(self.val)
			self.exe = False
			self.fill_list()

	def checkSummary(self):
		cur = self["filelist"].getCurrent()
		self["summary_description"].text = cur


class RestoreScreen(ConfigListScreen, Screen):
	skin = """
		<screen position="0,0" size="0,0" title="" >
		<widget name="config" position="10,10" size="330,250" transparent="1" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, runRestore=False):
		Screen.__init__(self, session)
		self.setTitle(_("Restoring..."))
		self.runRestore = runRestore
		self["actions"] = ActionMap(["WizardActions", "DirectionActions"],
		{
			"ok": self.close,
			"back": self.close,
			"cancel": self.close,
		}, -1)
		self.backuppath = getBackupPath()  # Used in ImageWizard
		if not isdir(self.backuppath):
			self.backuppath = getOldBackupPath()
		self.backupfile = getBackupFilename()
		self.list = []
		ConfigListScreen.__init__(self, self.list)  # Used in ImageWizard
		if runRestore:
			self.callLater(self.doRestore)

	def doRestore(self):
		fullbackupfilename = join(self.backuppath, self.backupfile)
		tarcmd = f"tar -C / -xzvf {fullbackupfilename}"
		for f in BLACKLISTED:
			tarcmd = tarcmd + f" --exclude {f.strip('/')}"
		restorecmdlist = ["rm -R /etc/enigma2", tarcmd, MANDATORY_RIGHTS]
		if exists("/proc/stb/vmpeg/0/dst_width"):
			restorecmdlist += ["echo 0 > /proc/stb/vmpeg/0/dst_height", "echo 0 > /proc/stb/vmpeg/0/dst_left", "echo 0 > /proc/stb/vmpeg/0/dst_top", "echo 0 > /proc/stb/vmpeg/0/dst_width"]
		restorecmdlist.append("/etc/init.d/autofs restart")
		print("[SOFTWARE MANAGER] Restore Settings !!!!")
		self.session.openWithCallback(self.restoreFinishedCB, Console, title=self.screenTitle, cmdlist=restorecmdlist, closeOnSuccess=True, showScripts=False)

	def restoreFinishedCB(self, retval=None):
		ShellCompatibleFunctions.restoreUserDB()
		self.session.openWithCallback(self.checkPlugins, RestartNetwork)

	def checkPlugins(self):
		if exists("/tmp/installed-list.txt"):
			if exists("/media/hdd/images/config/noplugins") and config.misc.firstrun.value:
				self.userRestoreScript()
			else:
				self.session.openWithCallback(self.userRestoreScript, installedPlugins)
		else:
			self.userRestoreScript()

	def userRestoreScript(self, ret=None):
		scriptPath = None
		for directory in listdir("/media"):
			if directory not in ("audiocd", "autofs"):
				configPath = join("/media", directory, "images/config/myrestore.sh")
				if exists(configPath):
					scriptPath = configPath
					break

		if scriptPath:
			self.session.openWithCallback(self.restoreMetrixSkin, Console, title=_("Running Myrestore script, Please wait ..."), cmdlist=[scriptPath], closeOnSuccess=True, showScripts=False)
		else:
			self.restoreMetrixSkin()

	def restartGUI(self, ret=None):
		self.session.open(Console, title=_("Your %s %s will Restart...") % getBoxDisplayName(), cmdlist=["killall -9 enigma2"], showScripts=False)

	def rebootSYS(self, ret=None):
		try:
			with open("/tmp/rebootSYS.sh", "w") as fd:
				fd.write("#!/bin/bash\n\nkillall -9 enigma2\nreboot\n")
			self.session.open(Console, title=_("Your %s %s will Reboot...") % getBoxDisplayName(), cmdlist=["chmod +x /tmp/rebootSYS.sh", "/tmp/rebootSYS.sh"], showScripts=False)
		except Exception:
			self.restartGUI()

	def restoreMetrixSkin(self, ret=None):
		configfile.load()
		configfile.save()
		try:
			s = ""
			with open("/etc/enigma2/settings") as fd:
				s = fd.read()
			restore = "config.skin.primary_skin=MetrixHD/skin.MySkin.xml" in s
		except Exception:
			restore = False
		if restore:
			self.session.openWithCallback(self.rebootSYS, RestoreMyMetrixHD)
		else:
			self.rebootSYS()

	def runAsync(self, finished_cb):  # Used in ImageWizard
		self.doRestore()


class RestoreMyMetrixHD(Screen):

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Restore MetrixHD Settings"))
		skin = """
			<screen name="RestoreMetrixHD" position="center,center" size="600,100" title="Restore MetrixHD Settings" resolution="1280,720">
			<widget name="label" position="10,30" size="500,50" halign="center" font="Regular;20" transparent="1" foregroundColor="white" />
			</screen> """
		self.skin = skin
		self["label"] = Label(_("Please wait while your skin setting is restoring..."))
		self["summary_description"] = StaticText(_("Please wait while your skin setting is restoring..."))

		# if not waiting is bsod possible (RuntimeError: modal open are allowed only from a screen which is modal!)
		self.restoreSkinTimer = eTimer()
		self.restoreSkinTimer.callback.append(self.restoreSkin)
		self.restoreSkinTimer.start(1000, True)

	def restoreSkin(self):
		try:
			from Plugins.Extensions.MyMetrixLite.ActivateSkinSettings import ActivateSkinSettings
			result = ActivateSkinSettings().WriteSkin(True)
			if result:
				infotext = ({1: _("Unknown Error creating Skin.\nPlease check after reboot MyMetrixLite-Plugin and apply your settings."),
							2: _("Error creating HD-Skin. Not enough flash memory free."),
							3: _("Error creating EHD-Skin. Not enough flash memory free.\nUsing HD-Skin!"),
							4: _("Error creating EHD-Skin. Icon package download not available.\nUsing HD-Skin!"),
							5: _("Error creating EHD-Skin.\nUsing HD-Skin!"),
							6: _("Error creating EHD-Skin. Some EHD-Icons are missing.\nUsing HD-Skin!"),
							7: _("Error, unknown Result!"),
							}[result])
				self.session.openWithCallback(self.checkSkinCallback, MessageBox, infotext, MessageBox.TYPE_ERROR, timeout=30)
			else:
				self.close()
		except Exception:
			self.session.openWithCallback(self.checkSkinCallback, MessageBox, _("Error creating MetrixHD-Skin.\nPlease check after reboot MyMetrixLite-Plugin and apply your settings."), MessageBox.TYPE_ERROR, timeout=30)

	def checkSkinCallback(self, ret=None):
		self.close()


class installedPlugins(Screen):
	UPDATE = 0
	LIST = 1

	skin = """
		<screen position="center,center" size="600,100" title="Install Plugins" >
		<widget name="label" position="10,30" size="500,50" halign="center" font="Regular;20" transparent="1" foregroundColor="white" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Install Plugins"))
		self["label"] = Label(_("Please wait while we check your installed plugins..."))
		self["summary_description"] = StaticText(_("Please wait while we check your installed plugins..."))
		self.type = self.UPDATE
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.runFinished)
		self.container.dataAvail.append(self.dataAvail)
		self.remainingdata = ""
		self.pluginsInstalled = []
		self.doUpdate()

	def doUpdate(self):
		print("[SOFTWARE MANAGER] update package list")
		self.container.execute("opkg update")

	def doList(self):
		print("[SOFTWARE MANAGER] read installed package list")
		self.container.execute("opkg list-installed | egrep 'enigma2-plugin-|task-base|packagegroup-base'")

	def dataAvail(self, strData):
		if isinstance(strData, bytes):
			strData = strData.decode("UTF-8", "ignore")
		if self.type == self.LIST:
			strData = self.remainingdata + strData
			lines = strData.split("\n")
			if len(lines[-1]):
				self.remainingdata = lines[-1]
				lines = lines[0:-1]
			else:
				self.remainingdata = ""
			for x in lines:
				self.pluginsInstalled.append(x[:x.find(" - ")])

	def runFinished(self, retval):
		if self.type == self.UPDATE:
			self.type = self.LIST
			self.doList()
		elif self.type == self.LIST:
			self.readPluginList()

	def readPluginList(self):
		installedpkgs = ShellCompatibleFunctions.listpkg(type="installed")
		self.PluginList = []
		if exists("/tmp/installed-list.txt"):
			with open("/tmp/installed-list.txt") as f:
				for line in f:
					if line.strip() not in installedpkgs:
						self.PluginList.append(line.strip())
		self.PluginRemoveList = []
		if exists("/tmp/removed-list.txt"):
			with open("/tmp/removed-list.txt") as f:
				for line in f:
					if line.strip() in installedpkgs:
						self.PluginRemoveList.append(line.strip())
		self.createMenuList()

	def createMenuList(self):
		self.Menulist = []
		for x in self.PluginList:
			if x not in self.pluginsInstalled:
				self.Menulist.append(SettingsEntry(x, True))
		if len(self.Menulist) == 0 and len(self.PluginRemoveList) == 0:
			self.close()
		else:
			if exists("/media/hdd/images/config/plugins") and config.misc.firstrun.value:
				self.startInstall(True)
			else:
				self.session.openWithCallback(self.startInstall, MessageBox, _("Backup plugins found\ndo you want to install now?"))

	def startInstall(self, ret=None):
		if ret:
			self.session.openWithCallback(self.restoreCB, RestorePlugins, self.Menulist, self.PluginRemoveList)
		else:
			self.close()

	def restoreCB(self, ret=None):
		self.close()


class RestorePlugins(Screen):
	def __init__(self, session, menulist, removelist=None):
		Screen.__init__(self, session)
		self.setTitle(_("Restore Plugins"))
		self.index = 0
		self.list = menulist
		self.removelist = removelist or []
		for r in menulist:
			print(f"[SOFTWARE MANAGER] Plugin to restore: {r[0]}")
		for r in self.removelist:
			print(f"[SOFTWARE MANAGER] Plugin to remove: {r}")
		self.container = eConsoleAppContainer()
		self["menu"] = List([])
		self["menu"].onSelectionChanged.append(self.selectionChanged)
		self["key_green"] = Button(_("Install"))
		self["key_red"] = Button(_("Cancel"))
		self["summary_description"] = StaticText("")

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"red": self.close,
			"green": self.green,
			"cancel": self.close,
			"ok": self.ok
		}, -2)

		self["menu"].setList(menulist)
		self["menu"].setIndex(self.index)
		self.onShown.append(self.runOnce)

	def runOnce(self):
		self.onShown.remove(self.runOnce)
		self.selectionChanged()
		if (exists("/media/hdd/images/config/plugins") and config.misc.firstrun.value) or len(self.list) == 0:
			self.green()

	def green(self):
		def searchIPKs():
			fileNames = []
			for searchDir in (x for x in ("/media/hdd/images/ipk", "/media/usb/images/ipk", "/media/mmc/images/ipk", "/media/cf/images/ipk") if isdir(x)):
				fileNames.extend([x for x in glob(join(searchDir, "*.ipk"), recursive=True) if "./open-multiboot/" not in x])
			return fileNames

		pluginlist = []
		pluginlistfirst = []
		myipklist = []
		myipklistfirst = []
		ipkFileNames = searchIPKs()
		for x in self.list:
			if x[2]:
				myipk = [i for i in ipkFileNames if x[0] in i]
				if myipk:
					myipk = myipk[0]
					if "-feed-" in myipk:
						myipklistfirst.append(myipk)
					else:
						myipklist.append(myipk)
				else:
					if "-feed-" in x[0]:
						pluginlistfirst.append(x[0])
					else:
						pluginlist.append(x[0])

		cmdList = []
		if pluginlistfirst:
			cmdList.append("opkg install " + " ".join(pluginlistfirst) + " ; opkg update")
		if myipklistfirst:
			cmdList.append("opkg install " + " ".join(myipklistfirst) + " ; opkg update")
		if myipklist:
			cmdList.append("opkg install " + " ".join(myipklist))
		if pluginlist:
			cmdList.append("opkg install " + " ".join(pluginlist))
		if self.removelist:
			cmdList.append("opkg --autoremove --force-depends remove " + " ".join(self.removelist))
		if cmdList:
			self.session.openWithCallback(self.close, Console, title=self.getTitle(), cmdlist=cmdList, closeOnSuccess=True, showScripts=False)
		else:
			self.close()

	def ok(self):
		if self["menu"].count():
			index = self["menu"].getIndex()
			item = self["menu"].getCurrent()[0]
			state = self["menu"].getCurrent()[2]
			self.list[index] = SettingsEntry(item, False if state else True)
			self["menu"].setList(self.list)
			self["menu"].setIndex(index)

	def selectionChanged(self):
		if self["menu"].count():
			index = self["menu"].getIndex()
			if index is None:
				index = 0
			else:
				self["summary_description"].text = self["menu"].getCurrent()[0]
			self.index = index

	#def exitNoPlugin(self, ret):
	#	self.close()


class SoftwareManagerInfo(Screen):
	skin = """
		<screen name="SoftwareManagerInfo" position="center,center" size="560,440" title="Software Manager Information" resolution="1280,720">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget source="list" render="Listbox" position="5,50" size="550,340" scrollbarMode="showOnDemand" selectionDisabled="0">
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (5, 0), size = (540, 26), font=0, flags = RT_HALIGN_LEFT | RT_HALIGN_CENTER, text = 0), # index 0 is the name
						],
					"fonts": [gFont("Regular", 24),gFont("Regular", 22)],
					"itemHeight": 26
					}
				</convert>
			</widget>
			<ePixmap pixmap="skin_default/div-h.png" position="0,400" zPosition="1" size="560,2" />
			<widget source="introduction" render="Label" position="5,410" size="550,30" zPosition="10" font="Regular;21" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
		</screen>"""

	def __init__(self, session, mode=None, submode=None):
		Screen.__init__(self, session)
		self.mode = mode
		self.submode = submode
		self["actions"] = HelpableActionMap(self, ["ShortcutActions", "WizardActions"], {
			"back": self.close,
			"red": self.close,
		}, prio=-2)
		self.infoList = []
		self["list"] = List(self.infoList)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["introduction"] = StaticText()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("Software Manager Information"))
		if self.mode is not None:
			self.showInfos()

	def showInfos(self):
		if self.mode == "backupinfo":
			self.infoList = []
			if self.submode == "backupfiles_exclude":
				backupfiles = config.plugins.configurationbackup.backupdirs_exclude.value
			elif self.submode == "backupfiles_addon":
				backupfiles = config.plugins.configurationbackup.backupdirs.value
			else:
				backupfiles = config.plugins.configurationbackup.backupdirs_default.value
			for entry in backupfiles:
				self.infoList.append((entry,))
			self["list"].setList(self.infoList)
