from os import F_OK, R_OK, W_OK, access, listdir, makedirs, mkdir, stat  # noqa F401
from os.path import dirname, isdir, isfile, join as pathjoin
from stat import ST_MTIME
from pickle import dump, load
from time import time

from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.Harddisk import harddiskmanager  # noqa F401
from Components.Opkg import OpkgComponent
from Components.PluginComponent import plugins  # noqa F401
from Components.SelectionList import SelectionList
from Components.SystemInfo import BoxInfo
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Opkg import Opkg
from Screens.Screen import Screen

from .BackupRestore import InitConfig as BackupRestore_InitConfig, BackupSelection, BackupScreen, RestoreScreen, getBackupPath, getOldBackupPath, getBackupFilename, RestoreMenu
from .ImageWizard import ImageWizard

boxType = BoxInfo.getItem("machinebuild")
config.plugins.configurationbackup = BackupRestore_InitConfig()


def write_cache(cache_file, cache_data):  # Does a cPickle dump.
	if not isdir(dirname(cache_file)):
		try:
			mkdir(dirname(cache_file))
		except OSError:
			print("%s is a file" % dirname(cache_file))
	with open(cache_file, "wb") as fd:
		dump(cache_data, fd, protocol=5)


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


class RestoreMenu(RestoreMenu):
	pass


class IpkgInstaller(Screen):
	skin = """
		<screen name="IpkgInstaller" position="center,center" size="550,450" title="Install extensions" resolution="1280,720">
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
			self.session.openWithCallback(self.backupDone, BackupScreen, runBackup=True, closeOnSuccess=5)
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
			except ImportError:
				self.session.open(MessageBox, _("Sorry, %s has not been installed!") % ("MediaScanner"), MessageBox.TYPE_INFO, timeout=10)
		elif self.args == 5:
			self.session.open(BackupSelection, title=_("Default files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs_default, readOnly=True, mode="backupfiles")
		elif self.args == 6:
			self.session.open(BackupSelection, title=_("Additional files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs, readOnly=False, mode="backupfiles_addon")
		elif self.args == 7:
			self.session.open(BackupSelection, title=_("Files/folders to exclude from backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs_exclude, readOnly=False, mode="backupfiles_exclude")
		if doClose:
			self.close()

	def startRestore(self, ret=False):
		if (ret is True):
			self.exe = True
			self.session.open(RestoreScreen, runRestore=True)
		self.close()

	def backupDone(self, retval=None):
		#message = _("Backup completed.") if retval else _("Backup failed.")
		#self.session.open(MessageBox, message, MessageBox.TYPE_INFO, timeout=10)
		self.close()


def Plugins(path, **kwargs):
	return [PluginDescriptor(name=_("Ipkg"), where=PluginDescriptor.WHERE_FILESCAN, needsRestart=False, fnc=filescan)]
