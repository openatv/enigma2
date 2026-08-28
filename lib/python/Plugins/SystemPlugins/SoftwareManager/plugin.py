from os import F_OK, R_OK, W_OK, access, makedirs, mkdir, stat  # noqa F401
from os.path import dirname, isdir, isfile, join as pathjoin
from stat import ST_MTIME
from pickle import dump, load
from time import time

from Components.config import config
from Components.SystemInfo import BoxInfo
from Screens.MessageBox import MessageBox
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
	return []
