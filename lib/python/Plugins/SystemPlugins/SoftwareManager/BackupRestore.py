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
from Components.config import getConfigListEntry, configfile, ConfigSelection, ConfigSubsection, ConfigText, ConfigLocations
from Components.config import config
from Components.ConfigList import ConfigList,ConfigListScreen
from Components.FileList import MultiFileSelectList
from Components.Network import iNetwork
from Plugins.Plugin import PluginDescriptor
from enigma import eTimer, eEnv, eConsoleAppContainer
from Tools.Directories import *
from os import system, popen, path, makedirs, listdir, access, stat, rename, remove, W_OK, R_OK
from time import gmtime, strftime, localtime, sleep
from datetime import date
from boxbranding import getBoxType, getMachineBrand, getMachineName

boxtype = getBoxType()

config.plugins.configurationbackup = ConfigSubsection()
if boxtype in ('maram9', 'classm', 'axodin', 'axodinc', 'starsatlx', 'genius', 'evo', 'galaxym6') and not path.exists("/media/hdd/backup_%s" %boxtype):
	config.plugins.configurationbackup.backuplocation = ConfigText(default = '/media/backup/', visible_width = 50, fixed_size = False)
else:	
	config.plugins.configurationbackup.backuplocation = ConfigText(default = '/media/hdd/', visible_width = 50, fixed_size = False)
config.plugins.configurationbackup.backupdirs = ConfigLocations(default=[eEnv.resolve('${sysconfdir}/enigma2/'), '/etc/CCcam.cfg', '/usr/keys/',
																		 '/etc/network/interfaces', '/etc/wpa_supplicant.conf', '/etc/wpa_supplicant.ath0.conf',
																		 '/etc/wpa_supplicant.wlan0.conf', '/etc/resolv.conf', '/etc/default_gw', '/etc/hostname',
																		 eEnv.resolve("${datadir}/enigma2/keymap.usr")])

def getBackupPath():
	backuppath = config.plugins.configurationbackup.backuplocation.value
	if backuppath.endswith('/'):
		return backuppath + 'backup_' + boxtype
	else:
		return backuppath + '/backup_' + boxtype

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
		configfile.save()
		try:
			if path.exists(self.backuppath) == False:
				makedirs(self.backuppath)
			self.backupdirs = ' '.join( config.plugins.configurationbackup.backupdirs.value )
			if not "/tmp/installed-list.txt" in self.backupdirs:
				self.backupdirs = self.backupdirs + " /tmp/installed-list.txt"
			if not "/tmp/changed-configfiles.txt" in self.backupdirs:
				self.backupdirs = self.backupdirs + " /tmp/changed-configfiles.txt"

			cmd1 = "opkg list-installed | egrep 'enigma2-plugin-|task-base|packagegroup-base' > /tmp/installed-list.txt"
			cmd2 = "opkg list-changed-conffiles > /tmp/changed-configfiles.txt"
			cmd3 = "tar -czvf " + self.fullbackupfilename + " " + self.backupdirs
			cmd = [cmd1, cmd2, cmd3]
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
		self.close(True)

	def backupErrorCB(self,retval = None):
		self.close(False)

	def runAsync(self, finished_cb):
		self.finished_cb = finished_cb
		self.doBackup()


class BackupSelection(Screen):
	skin = """
		<screen name="BackupSelection" position="center,center" size="560,400" title="Select files/folders to backup">
			<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget name="checkList" position="5,50" size="550,250" transparent="1" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText()
		self["summary_description"] = StaticText("")

		self.selectedFiles = config.plugins.configurationbackup.backupdirs.value
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
		self["summary_description"].text = current[3]
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
		self["checkList"].changeSelectionState()
		self.selectedFiles = self["checkList"].getSelectedList()

	def saveSelection(self):
		self.selectedFiles = self["checkList"].getSelectedList()
		config.plugins.configurationbackup.backupdirs.setValue(self.selectedFiles)
		config.plugins.configurationbackup.backupdirs.save()
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
			self.exe = True
			self.session.open(Console, title = _("Restoring..."), cmdlist = ["rm -R /etc/enigma2", "tar -xzvf " + self.path + "/" + self.sel + " -C /", "killall -9 enigma2"])

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
		if path.exists("/proc/stb/vmpeg/0/dst_width"):
			restorecmdlist = ["rm -R /etc/enigma2", "tar -xzvf " + self.fullbackupfilename + " -C /", "echo 0 > /proc/stb/vmpeg/0/dst_height", "echo 0 > /proc/stb/vmpeg/0/dst_left", "echo 0 > /proc/stb/vmpeg/0/dst_top", "echo 0 > /proc/stb/vmpeg/0/dst_width"]
		else:
			restorecmdlist = ["rm -R /etc/enigma2", "tar -xzvf " + self.fullbackupfilename + " -C /"]
		print"[SOFTWARE MANAGER] Restore Settings !!!!"

		self.session.open(Console, title = _("Restoring..."), cmdlist = restorecmdlist, finishedCallback = self.restoreFinishedCB)

	def restoreFinishedCB(self,retval = None):
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
		self.session.open(Console, title = _("Your %s %s will Reboot...")% (getMachineBrand(), getMachineName()), cmdlist = ["init 4;reboot"])

	def restoreMetrixSkin(self, ret = None):
		try:
			from Plugins.Extensions.MyMetrixLite.MainSettingsView import MainSettingsView
			print"Restoring MyMetrixLite..."
			MainSettingsView(None,True)
		except:
			pass
		self.restartGUI()

	def runAsync(self, finished_cb):
		self.doRestore()

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
		self.PluginList = []
		f = open("/tmp/installed-list.txt", "r")
		lines = f.readlines()
		for x in lines:
			self.PluginList.append(x[:x.find(' - ')])
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
