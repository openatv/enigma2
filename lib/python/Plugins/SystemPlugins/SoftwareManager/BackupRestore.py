from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.Console import Console
from Screens.Standby import TryQuitMainloop
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Pixmap import Pixmap
from Tools.LoadPixmap import LoadPixmap
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList
from Components.Sources.List import List
from Components.Button import Button
from Components.config import NoSave, getConfigListEntry, configfile, ConfigSelection, ConfigSubsection, ConfigText, ConfigLocations
from Components.config import config
from Components.ConfigList import ConfigList,ConfigListScreen
from Components.FileList import MultiFileSelectList
from Components.Network import iNetwork
from Plugins.Plugin import PluginDescriptor
from enigma import eTimer, eEnv, eConsoleAppContainer, eEPGCache
from Tools.Directories import *
from os import system, popen, path, makedirs, listdir, access, stat, rename, remove, W_OK, R_OK
from time import gmtime, strftime, localtime, sleep
from datetime import date
from boxbranding import getBoxType, getMachineBrand, getMachineName, getImageDistro
import ShellCompatibleFunctions

boxtype = getBoxType()
distro = getImageDistro()

def eEnv_resolve_multi(path):
	resolve = eEnv.resolve(path)
	if resolve == path:
		return []
	else:
		return resolve.split()

# MANDATORY_RIGHTS contains commands to ensure correct rights for certain files, shared with ShellCompatibleFunctions for FastRestore
MANDATORY_RIGHTS = ShellCompatibleFunctions.MANDATORY_RIGHTS

# BLACKLISTED lists all files/folders that MUST NOT be backed up or restored in order for the image to work properly, shared with ShellCompatibleFunctions for FastRestore
BLACKLISTED = ShellCompatibleFunctions.BLACKLISTED

def InitConfig():
	# BACKUPFILES contains all files and folders to back up, for wildcard entries ALWAYS use eEnv_resolve_multi!
	BACKUPFILES = ['/etc/enigma2/', '/etc/CCcam.cfg', '/usr/keys/',
		'/etc/davfs2/', '/etc/tuxbox/config/', '/etc/auto.network', '/etc/feeds.xml', '/etc/machine-id', '/etc/rc.local', 
		'/etc/openvpn/', '/etc/ipsec.conf', '/etc/ipsec.secrets', '/etc/ipsec.user', '/etc/strongswan.conf', '/etc/vtuner.conf',
		'/etc/default/crond', '/etc/dropbear/', '/etc/default/dropbear', '/home/', '/etc/samba/', '/etc/fstab', '/etc/inadyn.conf', 
		'/etc/network/interfaces', '/etc/wpa_supplicant.conf', '/etc/wpa_supplicant.ath0.conf', '/etc/opkg/secret-feed.conf',
		'/etc/wpa_supplicant.wlan0.conf', '/etc/wpa_supplicant.wlan1.conf', '/etc/resolv.conf', '/etc/default_gw', '/etc/hostname', '/etc/epgimport/', '/etc/exports',
		'/etc/enigmalight.conf', '/etc/volume.xml', '/etc/enigma2/ci_auth_slot_0.bin', '/etc/enigma2/ci_auth_slot_1.bin',
		'/usr/lib/enigma2/python/Plugins/Extensions/VMC/DB/',
		'/usr/lib/enigma2/python/Plugins/Extensions/VMC/youtv.pwd',
		'/usr/lib/enigma2/python/Plugins/Extensions/VMC/vod.config',
		'/usr/share/enigma2/MetrixHD/skinparts/',
		'/usr/share/enigma2/display/skin_display_usr.xml',
		'/usr/share/enigma2/display/userskin.png',
		'/usr/lib/enigma2/python/Plugins/Extensions/SpecialJump/keymap_user.xml',
		'/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db',
		'/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db',
		'/usr/lib/enigma2/python/Plugins/Extensions/TVSpielfilm/db', '/etc/ConfFS',
		'/etc/rc3.d/S99tuner.sh',
		'/usr/bin/enigma2_pre_start.sh',
		eEnv.resolve("${datadir}/enigma2/keymap.usr"),
		eEnv.resolve("${datadir}/enigma2/keymap_usermod.xml")]\
		+eEnv_resolve_multi("${datadir}/enigma2/*/mySkin_off/*.xml")\
		+eEnv_resolve_multi("${datadir}/enigma2/*/mySkin/*.xml")\
		+eEnv_resolve_multi('/usr/bin/*cam*')\
		+eEnv_resolve_multi('/etc/*.emu')\
		+eEnv_resolve_multi('/etc/cron*')\
		+eEnv_resolve_multi('/etc/init.d/softcam*')\
		+eEnv_resolve_multi('/etc/init.d/cardserver*')\
		+eEnv_resolve_multi('/etc/sundtek.*')\
		+eEnv_resolve_multi('/usr/sundtek/*')\
		+eEnv_resolve_multi('/opt/bin/*')\
		+eEnv_resolve_multi('/usr/script/*')

	# Drop non existant paths from list
	tmpfiles=[]
	for f in BACKUPFILES:
		if path.exists(f):
			tmpfiles.append(f)
	backupset=tmpfiles

	config.plugins.configurationbackup = ConfigSubsection()
	if boxtype in ('maram9', 'classm', 'axodin', 'axodinc', 'starsatlx', 'genius', 'evo', 'galaxym6') and not path.exists("/media/hdd/backup_%s" %boxtype):
		config.plugins.configurationbackup.backuplocation = ConfigText(default = '/media/backup/', visible_width = 50, fixed_size = False)
	else:
		config.plugins.configurationbackup.backuplocation = ConfigText(default = '/media/hdd/', visible_width = 50, fixed_size = False)
	config.plugins.configurationbackup.backupdirs_default = NoSave(ConfigLocations(default=backupset))
	config.plugins.configurationbackup.backupdirs         = ConfigLocations(default=[]) # 'backupdirs_addon' is called 'backupdirs' for backwards compatibility, holding the user's old selection, duplicates are removed during backup
	config.plugins.configurationbackup.backupdirs_exclude = ConfigLocations(default=[])
	return config.plugins.configurationbackup

config.plugins.configurationbackup=InitConfig()

def getBackupPath():
	backuppath = config.plugins.configurationbackup.backuplocation.value
	if backuppath.endswith('/'):
		return backuppath + 'backup_' + distro + '_'+ boxtype
	else:
		return backuppath + '/backup_' + distro + '_'+ boxtype

def getOldBackupPath():
	backuppath = config.plugins.configurationbackup.backuplocation.value
	if backuppath.endswith('/'):
		return backuppath + 'backup'
	else:
		return backuppath + '/backup'

def getBackupFilename():
	return "enigma2settingsbackup.tar.gz"

def SettingsEntry(name, checked):
	if checked:
		picture = LoadPixmap(cached = True, path = resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/lock_on.png"));
	else:
		picture = LoadPixmap(cached = True, path = resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/lock_off.png"));
		
	return (name, picture, checked)

class BackupScreen(Screen, ConfigListScreen):
	skin = """
		<screen position="135,144" size="350,310" title="Backup is running" >
		<widget name="config" position="10,10" size="330,250" transparent="1" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, runBackup = False):
		Screen.__init__(self, session)
		self.session = session
		self.runBackup = runBackup
		self["actions"] = ActionMap(["WizardActions", "DirectionActions"],
		{
			"ok": self.close,
			"back": self.close,
			"cancel": self.close,
		}, -1)
		self.finished_cb = None
		self.backuppath = getBackupPath()
		self.backupfile = getBackupFilename()
		self.fullbackupfilename = self.backuppath + "/" + self.backupfile
		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.onLayoutFinish.append(self.layoutFinished)
		if self.runBackup:
			self.onShown.append(self.doBackup)

	def layoutFinished(self):
		self.setWindowTitle()

	def setWindowTitle(self):
		self.setTitle(_("Backup is running..."))

	def doBackup(self):
		self.save_shutdownOK = config.usage.shutdownOK.value
		config.usage.shutdownOK.setValue(True)
		config.usage.shutdownOK.save()
		configfile.save()
		try:
			if config.plugins.softwaremanager.epgcache.value:
				eEPGCache.getInstance().save()
		except:
			pass
		try:
			if path.exists(self.backuppath) == False:
				makedirs(self.backuppath)
			InitConfig()
			self.backupdirs=" ".join(f.strip("/") for f in config.plugins.configurationbackup.backupdirs_default.value)
			for f in config.plugins.configurationbackup.backupdirs.value:
				if not f.strip("/") in self.backupdirs:
					self.backupdirs += " " + f.strip("/")
			if not "tmp/installed-list.txt" in self.backupdirs:
				self.backupdirs += " tmp/installed-list.txt"
			if not "tmp/changed-configfiles.txt" in self.backupdirs:
				self.backupdirs += " tmp/changed-configfiles.txt"
			if not "tmp/passwd.txt" in self.backupdirs:
				self.backupdirs += " tmp/passwd.txt"
			if not "tmp/groups.txt" in self.backupdirs:
				self.backupdirs += " tmp/groups.txt"

			ShellCompatibleFunctions.backupUserDB()
			pkgs=ShellCompatibleFunctions.listpkg(type="user")
			installed = open("/tmp/installed-list.txt", "w")
			installed.write('\n'.join(pkgs))
			installed.close()
			cmd2 = "opkg list-changed-conffiles > /tmp/changed-configfiles.txt"
			cmd3 = "tar -C / -czvf " + self.fullbackupfilename + " " + self.backupdirs
			for f in config.plugins.configurationbackup.backupdirs_exclude.value:
				cmd3 = cmd3 + " --exclude " + f.strip("/")
			for f in BLACKLISTED:
				cmd3 = cmd3 + " --exclude " + f.strip("/")
			cmd = [cmd2, cmd3]
			if path.exists(self.fullbackupfilename):
				dt = str(date.fromtimestamp(stat(self.fullbackupfilename).st_ctime))
				self.newfilename = self.backuppath + "/" + dt + '-' + self.backupfile
				if path.exists(self.newfilename):
					remove(self.newfilename)
				rename(self.fullbackupfilename,self.newfilename)
			if self.finished_cb:
				self.session.openWithCallback(self.finished_cb, Console, title = _("Backup is running..."), cmdlist = cmd,finishedCallback = self.backupFinishedCB,closeOnSuccess = True)
			else:
				self.session.open(Console, title = _("Backup is running..."), cmdlist = cmd,finishedCallback = self.backupFinishedCB, closeOnSuccess = True)
		except OSError:
			if self.finished_cb:
				self.session.openWithCallback(self.finished_cb, MessageBox, _("Sorry, your backup destination is not writeable.\nPlease select a different one."), MessageBox.TYPE_INFO, timeout = 10 )
			else:
				self.session.openWithCallback(self.backupErrorCB,MessageBox, _("Sorry, your backup destination is not writeable.\nPlease select a different one."), MessageBox.TYPE_INFO, timeout = 10 )

	def backupFinishedCB(self,retval = None):
		config.usage.shutdownOK.setValue(self.save_shutdownOK)
		config.usage.shutdownOK.save()
		configfile.save()
		self.close(True)

	def backupErrorCB(self,retval = None):
		self.close(False)

	def runAsync(self, finished_cb):
		self.finished_cb = finished_cb
		self.doBackup()


class BackupSelection(Screen):
	skin = """
		<screen name="BackupSelection" position="center,center" size="560,400" title="Select files/folders to backup">
			<ePixmap pixmap="buttons/red.png" position="0,340" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/green.png" position="140,340" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/yellow.png" position="280,340" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="title_text" render="Label" position="10,0" size="540,30" font="Regular;24" halign="left" foregroundColor="white" backgroundColor="black" transparent="1" />
			<widget source="summary_description" render="Label" position="5,300" size="550,30" foregroundColor="white" backgroundColor="black" font="Regular; 24" halign="left" transparent="1" />
			<widget name="checkList" position="5,50" size="550,250" transparent="1" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, title=_("Select files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs, readOnly=False):
		Screen.__init__(self, session)
		self.readOnly = readOnly
		self.configBackupDirs = configBackupDirs
		if self.readOnly:
			self["key_red"] = StaticText(_("Exit"))
			self["key_green"] = StaticText(_("Exit"))
		else:
			self["key_red"] = StaticText(_("Cancel"))
			self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText()
		self["summary_description"] = StaticText(_("default"))
		self["title_text"] = StaticText(title)

		self.selectedFiles = self.configBackupDirs.value
		defaultDir = '/'
		inhibitDirs = ["/bin", "/boot", "/dev", "/autofs", "/lib", "/proc", "/sbin", "/sys", "/hdd", "/tmp", "/mnt", "/media"]
		self.filelist = MultiFileSelectList(self.selectedFiles, defaultDir, inhibitDirs = inhibitDirs )
		self["checkList"] = self.filelist

		self["actions"] = ActionMap(["DirectionActions", "OkCancelActions", "ShortcutActions"],
		{
			"cancel": self.exit,
			"red": self.exit,
			"yellow": self.changeSelectionState,
			"green": self.saveSelection,
			"ok": self.okClicked,
			"left": self.left,
			"right": self.right,
			"down": self.down,
			"up": self.up
		}, -1)
		if not self.selectionChanged in self["checkList"].onSelectionChanged:
			self["checkList"].onSelectionChanged.append(self.selectionChanged)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		idx = 0
		self["checkList"].moveToIndex(idx)
		self.setWindowTitle()
		self.selectionChanged()

	def setWindowTitle(self):
		self.setTitle(_("Select files/folders to backup"))

	def selectionChanged(self):
		current = self["checkList"].getCurrent()[0]
		if current[3] == "<Parent directory>":
			self["summary_description"].text =self["checkList"].getCurrentDirectory()+".."
		else:
			self["summary_description"].text =self["checkList"].getCurrentDirectory()+current[3]
		if current[2] is True:
			self["key_yellow"].setText(_("Deselect"))
		else:
			self["key_yellow"].setText(_("Select"))

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
			self.session.open(MessageBox,_("The default backup selection cannot be changed.\nPlease use the 'additional' and 'excluded' backup selection."), type = MessageBox.TYPE_INFO,timeout = 10)
		else:
			self["checkList"].changeSelectionState()
			self.selectedFiles = self["checkList"].getSelectedList()

	def saveSelection(self):
		if self.readOnly:
			self.close(None)
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
		<screen name="RestoreMenu" position="center,center" size="560,400" title="Restore backups" >
			<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget name="filelist" position="5,50" size="550,230" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, plugin_path):
		Screen.__init__(self, session)
		self.skin_path = plugin_path

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

		self["shortcuts"] = ActionMap(["ShortcutActions"],
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
		self.setWindowTitle()
		self.checkSummary()

	def setWindowTitle(self):
		self.setTitle(_("Restore backups"))


	def fill_list(self):
		self.flist = []
		self.path = getBackupPath()
		if path.exists(self.path) == False:
			makedirs(self.path)
		for file in listdir(self.path):
			if file.endswith(".tar.gz"):
				self.flist.append(file)
				self.entry = True
		self.flist.sort(reverse=True)
		self["filelist"].l.setList(self.flist)

	def KeyOk(self):
		if (self.exe == False) and (self.entry == True):
			self.sel = self["filelist"].getCurrent()
			if self.sel:
				self.val = self.path + "/" + self.sel
				self.session.openWithCallback(self.startRestore, MessageBox, _("Are you sure you want to restore\nthe following backup:\n%s\nYour receiver will restart after the backup has been restored!") % self.sel)

	def keyCancel(self):
		self.close()

	def keyUp(self):
		self["filelist"].up()
		self.checkSummary()

	def keyDown(self):
		self["filelist"].down()
		self.checkSummary()

	def startRestore(self, ret = False):
		if ret == True:
			self.session.openWithCallback(self.CB_startRestore, MessageBox, _("Do you want to delete the old settings in /etc/enigma2 first?"))

	def CB_startRestore(self, ret = False):
		self.exe = True
		tarcmd = "tar -C / -xzvf " + self.path + "/" + self.sel
		for f in BLACKLISTED:
			tarcmd = tarcmd + " --exclude " + f.strip("/")

		cmds = [ tarcmd, MANDATORY_RIGHTS, "/etc/init.d/autofs restart", "killall -9 enigma2" ]
		if ret == True:
			cmds.insert(0, "rm -R /etc/enigma2")
			self.session.open(Console, title = _("Restoring..."), cmdlist = cmds)
		else:
			self.session.open(Console, title = _("Restoring..."), cmdlist = cmds)

	def deleteFile(self):
		if (self.exe == False) and (self.entry == True):
			self.sel = self["filelist"].getCurrent()
			if self.sel:
				self.val = self.path + "/" + self.sel
				self.session.openWithCallback(self.startDelete, MessageBox, _("Are you sure you want to delete\nthe following backup:\n") + self.sel)

	def startDelete(self, ret = False):
		if ret == True:
			self.exe = True
			print "removing:",self.val
			if path.exists(self.val) == True:
				remove(self.val)
			self.exe = False
			self.fill_list()

	def checkSummary(self):
		cur = self["filelist"].getCurrent()
		self["summary_description"].text = cur

class RestoreScreen(Screen, ConfigListScreen):
	skin = """
		<screen position="135,144" size="350,310" title="Restore is running..." >
		<widget name="config" position="10,10" size="330,250" transparent="1" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, runRestore = False):
		Screen.__init__(self, session)
		self.session = session
		self.runRestore = runRestore
		self["actions"] = ActionMap(["WizardActions", "DirectionActions"],
		{
			"ok": self.close,
			"back": self.close,
			"cancel": self.close,
		}, -1)
		self.backuppath = getBackupPath()
		if not path.isdir(self.backuppath):
			self.backuppath = getOldBackupPath()
		self.backupfile = getBackupFilename()
		self.fullbackupfilename = self.backuppath + "/" + self.backupfile
		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.onLayoutFinish.append(self.layoutFinished)
		if self.runRestore:
			self.onShown.append(self.doRestore)

	def layoutFinished(self):
		self.setWindowTitle()

	def setWindowTitle(self):
		self.setTitle(_("Restoring..."))

	def doRestore(self):
		tarcmd = "tar -C / -xzvf " + self.fullbackupfilename
		for f in BLACKLISTED:
				tarcmd = tarcmd + " --exclude " + f.strip("/")
		restorecmdlist = ["rm -R /etc/enigma2", tarcmd, MANDATORY_RIGHTS]
		if path.exists("/proc/stb/vmpeg/0/dst_width"):
			restorecmdlist += ["echo 0 > /proc/stb/vmpeg/0/dst_height", "echo 0 > /proc/stb/vmpeg/0/dst_left", "echo 0 > /proc/stb/vmpeg/0/dst_top", "echo 0 > /proc/stb/vmpeg/0/dst_width"]
		restorecmdlist.append("/etc/init.d/autofs restart")
		print"[SOFTWARE MANAGER] Restore Settings !!!!"

		self.session.open(Console, title = _("Restoring..."), cmdlist = restorecmdlist, finishedCallback = self.restoreFinishedCB)

	def restoreFinishedCB(self,retval = None):
		ShellCompatibleFunctions.restoreUserDB()
		self.session.openWithCallback(self.checkPlugins, RestartNetwork)

	def checkPlugins(self):
		if path.exists("/tmp/installed-list.txt"):
			if os.path.exists("/media/hdd/images/config/noplugins") and config.misc.firstrun.value:
				self.userRestoreScript()
			else:
				self.session.openWithCallback(self.userRestoreScript, installedPlugins)
		else:
			self.userRestoreScript()

	def userRestoreScript(self, ret = None):
		
		SH_List = []
		SH_List.append('/media/hdd/images/config/myrestore.sh')
		SH_List.append('/media/usb/images/config/myrestore.sh')
		SH_List.append('/media/cf/images/config/myrestore.sh')
		
		startSH = None
		for SH in SH_List:
			if path.exists(SH):
				startSH = SH
				break

		if startSH:
			self.session.openWithCallback(self.restoreMetrixSkin, Console, title = _("Running Myrestore script, Please wait ..."), cmdlist = [startSH], closeOnSuccess = True)
		else:
			self.restoreMetrixSkin()

	def restartGUI(self, ret = None):
		self.session.open(Console, title = _("Your %s %s will Restart...")% (getMachineBrand(), getMachineName()), cmdlist = ["killall -9 enigma2"])

	def rebootSYS(self, ret = None):
		try:
			f = open("/tmp/rebootSYS.sh","w")
			f.write("#!/bin/bash\n\nkillall -9 enigma2\nreboot\n")
			f.close()
			self.session.open(Console, title = _("Your %s %s will Reboot...")% (getMachineBrand(), getMachineName()), cmdlist = ["chmod +x /tmp/rebootSYS.sh", "/tmp/rebootSYS.sh"])
		except:
			self.restartGUI()

	def restoreMetrixSkin(self, ret = None):
		configfile.load()
		configfile.save()
		try:
			f=open("/etc/enigma2/settings", "r")
			s=f.read()
			f.close()
			restore = "config.skin.primary_skin=MetrixHD/skin.MySkin.xml" in s
		except:
			restore = False
		if restore:
			self.session.openWithCallback(self.rebootSYS, RestoreMyMetrixHD)
		else:
			self.rebootSYS()

	def runAsync(self, finished_cb):
		self.doRestore()

class RestoreMyMetrixHD(Screen):

	def __init__(self, session):
		Screen.__init__(self, session)
		skin = """
			<screen name="RestoreMetrixHD" position="center,center" size="600,100" title="Restore MetrixHD Settings">
			<widget name="label" position="10,30" size="500,50" halign="center" font="Regular;20" transparent="1" foregroundColor="white" />
			</screen> """
		self.skin = skin
		self.session = session
		self["label"] = Label(_("Please wait while your skin setting is restoring..."))
		self["summary_description"] = StaticText(_("Please wait while your skin setting is restoring..."))
		self.onShown.append(self.setWindowTitle) 

		# if not waiting is bsod possible (RuntimeError: modal open are allowed only from a screen which is modal!)
		self.restoreSkinTimer = eTimer()
		self.restoreSkinTimer.callback.append(self.restoreSkin)
		self.restoreSkinTimer.start(1000, True)

	def setWindowTitle(self): 
		self.setTitle(_("Restore MetrixHD Settings"))

	def restoreSkin(self):
		try:
			from Plugins.Extensions.MyMetrixLite.ActivateSkinSettings import ActivateSkinSettings
			result = ActivateSkinSettings().WriteSkin(True)
			if result:
				infotext = ({1:_("Unknown Error creating Skin.\nPlease check after reboot MyMetrixLite-Plugin and apply your settings."),
							2:_("Error creating HD-Skin. Not enough flash memory free."),
							3:_("Error creating FullHD-Skin. Not enough flash memory free.\nUsing HD-Skin!"),
							4:_("Error creating FullHD-Skin. Icon package download not available.\nUsing HD-Skin!"),
							5:_("Error creating FullHD-Skin.\nUsing HD-Skin!"),
							6:_("Some FullHD-Icons are missing.\nUsing HD-Icons!"),
							7:_("Error, unknown Result!"),
							}[result])
				self.session.openWithCallback(self.checkSkinCallback, MessageBox, infotext, MessageBox.TYPE_ERROR, timeout = 30)
			else:
				self.close()
		except:
			self.session.openWithCallback(self.checkSkinCallback, MessageBox, _("Error creating MetrixHD-Skin.\nPlease check after reboot MyMetrixLite-Plugin and apply your settings."), MessageBox.TYPE_ERROR, timeout = 30)

	def checkSkinCallback(self, ret = None):
		self.close()

class RestartNetwork(Screen):

	def __init__(self, session):
		Screen.__init__(self, session)
		skin = """
			<screen name="RestartNetwork" position="center,center" size="600,100" title="Restart Network Adapter">
			<widget name="label" position="10,30" size="500,50" halign="center" font="Regular;20" transparent="1" foregroundColor="white" />
			</screen> """
		self.skin = skin
		self["label"] = Label(_("Please wait while your network is restarting..."))
		self["summary_description"] = StaticText(_("Please wait while your network is restarting..."))
		self.onShown.append(self.setWindowTitle)
		self.onLayoutFinish.append(self.restartLan)

	def setWindowTitle(self):
		self.setTitle(_("Restart Network Adapter"))

	def restartLan(self):
		print"[SOFTWARE MANAGER] Restart Network"
		iNetwork.restartNetwork(self.restartLanDataAvail)
		
	def restartLanDataAvail(self, data):
		if data is True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
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
		Screen.setTitle(self, _("Install Plugins"))
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
		print"[SOFTWARE MANAGER] update package list"
		self.container.execute("opkg update")

	def doList(self):
		print"[SOFTWARE MANAGER] read installed package list"
		self.container.execute("opkg list-installed | egrep 'enigma2-plugin-|task-base|packagegroup-base'")

	def dataAvail(self, strData):
		if self.type == self.LIST:
			strData = self.remainingdata + strData
			lines = strData.split('\n')
			if len(lines[-1]):
				self.remainingdata = lines[-1]
				lines = lines[0:-1]
			else:
				self.remainingdata = ""
			for x in lines:
				self.pluginsInstalled.append(x[:x.find(' - ')])

	def runFinished(self, retval):
		if self.type == self.UPDATE:
			self.type = self.LIST
			self.doList()
		elif self.type == self.LIST:
			self.readPluginList()

	def readPluginList(self):
		installedpkgs=ShellCompatibleFunctions.listpkg(type="installed")
		self.PluginList = []
		with open('/tmp/installed-list.txt') as f:
			for line in f:
				if line.strip() not in installedpkgs:
					self.PluginList.append(line.strip())
		f.close()
		self.createMenuList()

	def createMenuList(self):
		self.Menulist = []
		for x in self.PluginList:
			if x not in self.pluginsInstalled:
				self.Menulist.append(SettingsEntry(x , True))
		if len(self.Menulist) == 0:
			self.close()
		else:
			if os.path.exists("/media/hdd/images/config/plugins") and config.misc.firstrun.value:
				self.startInstall(True)
			else:
				self.session.openWithCallback(self.startInstall, MessageBox, _("Backup plugins found\ndo you want to install now?"))

	def startInstall(self, ret = None):
		if ret:
			self.session.openWithCallback(self.restoreCB, RestorePlugins, self.Menulist)
		else:
			self.close()

	def restoreCB(self, ret = None):
		self.close()

class RestorePlugins(Screen):

	def __init__(self, session, menulist):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Restore Plugins"))
		self.index = 0
		self.list = menulist
		for r in menulist:
			print "[SOFTWARE MANAGER] Plugin to restore: %s" % r[0]
		self.container = eConsoleAppContainer()
		self["menu"] = List(list())
		self["menu"].onSelectionChanged.append(self.selectionChanged)
		self["key_green"] = Button(_("Install"))
		self["key_red"] = Button(_("Cancel"))
		self["summary_description"] = StaticText("")
				
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
				{
					"red": self.exit,
					"green": self.green,
					"cancel": self.exit,
					"ok": self.ok
				}, -2)

		self["menu"].setList(menulist)
		self["menu"].setIndex(self.index)
		self.selectionChanged()
		self.onShown.append(self.setWindowTitle)

	def setWindowTitle(self):
		self.setTitle(_("Restore Plugins"))
		if os.path.exists("/media/hdd/images/config/plugins") and config.misc.firstrun.value:
			self.green()

	def exit(self):
		self.close()

	def green(self):
		pluginlist = []
		self.myipklist = []
		for x in self.list:
			if x[2]:
				myipk = self.SearchIPK(x[0])
				if myipk:
					self.myipklist.append(myipk)
				else:
					pluginlist.append(x[0])
		if len(pluginlist) > 0:
			if len(self.myipklist) > 0:
				self.session.open(Console, title = _("Installing plugins..."), cmdlist = ['opkg --force-overwrite install ' + ' '.join(pluginlist)], finishedCallback = self.installLocalIPK, closeOnSuccess = True)
			else:
				self.session.open(Console, title = _("Installing plugins..."), cmdlist = ['opkg --force-overwrite install ' + ' '.join(pluginlist)], finishedCallback = self.exit, closeOnSuccess = True)
		elif len(self.myipklist) > 0:
			self.installLocalIPK()

	def installLocalIPK(self):
		self.session.open(Console, title = _("Installing plugins..."), cmdlist = ['opkg --force-overwrite install ' + ' '.join(self.myipklist)], finishedCallback = self.exit, closeOnSuccess = True)
	
	def ok(self):
		index = self["menu"].getIndex()
		item = self["menu"].getCurrent()[0]
		state = self["menu"].getCurrent()[2]
		if state:
			self.list[index] = SettingsEntry(item , False)
		else:
			self.list[index] = SettingsEntry(item, True)

		self["menu"].setList(self.list)
		self["menu"].setIndex(index)

	def selectionChanged(self):
		index = self["menu"].getIndex()
		if index == None:
			index = 0
		else:
			self["summary_description"].text = self["menu"].getCurrent()[0]
		self.index = index
			
	def drawList(self):
		self["menu"].setList(self.Menulist)
		self["menu"].setIndex(self.index)

	def exitNoPlugin(self, ret):
		self.close()

	def SearchIPK(self, ipkname):
		ipkname = ipkname + "*"
		search_dirs = [ "/media/hdd", "/media/usb" ]
		sdirs = " ".join(search_dirs)
		cmd = 'find %s -name "%s" | grep -iv "./open-multiboot/*" | head -n 1' % (sdirs, ipkname)
		res = popen(cmd).read()
		if res == "":
			return None
		else:
			return res.replace("\n", "")
