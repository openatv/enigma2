#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

# Components
from __future__ import print_function
from __future__ import absolute_import
from Components.config import config
from Components.Scanner import openFile
from Components.MovieList import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, MOVIE_EXTENSIONS, DVD_EXTENSIONS
from Components.Task import Task, Job, job_manager, Condition
from Components.Console import Console as console

# Screens
from Screens.Console import Console
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.InfoBar import InfoBar

# Tools
from Tools.Directories import fileExists
from Tools.UnitConversions import UnitScaler, UnitMultipliers
import Tools.Notifications

# Various
from mimetypes import guess_type
from enigma import eServiceReference, eActionMap
from sys import maxsize

import stat
import pwd
import grp
import time
import re

import os

# Addons
from .unrar import RarMenuScreen
from .tar import TarMenuScreen
from .unzip import UnzipMenuScreen
from .gz import GunzipMenuScreen
from .ipk import ipkMenuScreen
from .type_utils import ImageViewer, MoviePlayer, vEditor

TEXT_EXTENSIONS = frozenset((".txt", ".log", ".py", ".xml", ".html", ".meta", ".bak", ".lst", ".cfg", ".conf", ".srt"))

try:
	from Screens import DVD
	DVDPlayerAvailable = True
except Exception as e:
	DVDPlayerAvailable = False

##################################

pname = _("File Commander - Addon Movieplayer")
pdesc = _("play Files")
last_service = None


class stat_info:
	def __init__(self):
		pass

	@staticmethod
	def filetypeStr(mode):
		return {
			stat.S_IFSOCK: _("Socket"),
			stat.S_IFLNK: _("Symbolic link"),
			stat.S_IFREG: _("Regular file"),
			stat.S_IFBLK: _("Block device"),
			stat.S_IFDIR: _("Directory"),
			stat.S_IFCHR: _("Character device"),
			stat.S_IFIFO: _("FIFO"),
		}.get(stat.S_IFMT(mode), _("Unknown"))

	@staticmethod
	def filetypeChr(mode):
		return {
			stat.S_IFSOCK: 's',
			stat.S_IFLNK: 'l',
			stat.S_IFREG: '-',
			stat.S_IFBLK: 'b',
			stat.S_IFDIR: 'd',
			stat.S_IFCHR: 'c',
			stat.S_IFIFO: 'p',
		}.get(stat.S_IFMT(mode), _('?'))

	@staticmethod
	def fileModeStr(mode):
		modestr = stat.S_IFMT(mode) and stat_info.filetypeChr(mode) or ''
		modestr += stat_info.permissionGroupStr((mode >> 6) & stat.S_IRWXO, mode & stat.S_ISUID, 's')
		modestr += stat_info.permissionGroupStr((mode >> 3) & stat.S_IRWXO, mode & stat.S_ISGID, 's')
		modestr += stat_info.permissionGroupStr(mode & stat.S_IRWXO, mode & stat.S_ISVTX, 't')
		return modestr

	@staticmethod
	def permissionGroupStr(mode, bit4, bit4chr):
		permstr = mode & stat.S_IROTH and 'r' or "-"
		permstr += mode & stat.S_IWOTH and 'w' or "-"
		if bit4:
			permstr += mode & stat.S_IXOTH and bit4chr or bit4chr.upper()
		else:
			permstr += mode & stat.S_IXOTH and "x" or "-"
		return permstr

	@staticmethod
	def username(uid):
		try:
			pwent = pwd.getpwuid(uid)
			return pwent.pw_name
		except KeyError as ke:
			return _("Unknown user: %d") % uid

	@staticmethod
	def groupname(gid):
		try:
			grent = grp.getgrgid(gid)
			return grent.gr_name
		except KeyError as ke:
			return _("Unknown group: %d") % gid

	@staticmethod
	def formatTime(t):
		return time.strftime(config.usage.date.daylong.value + " " + config.usage.time.long.value, time.localtime(t))


task_Stout = []
task_Sterr = []


class task_postconditions(Condition):
	def check(self, task):
		global task_Stout, task_Sterr
		message = ''
		lines = config.plugins.filecommander.script_messagelen.value * -1
		if task_Stout:
			msg_out = '\n\n' + _("script 'stout':") + '\n' + '\n'.join(task_Stout[lines:])
		if task_Sterr:
			msg_err = '\n\n' + _("script 'sterr':") + '\n' + '\n'.join(task_Sterr[lines:])
		if task.returncode != 0:
			messageboxtyp = MessageBox.TYPE_ERROR
			msg_msg = _("Run script") + _(" ('%s') ends with error number [%d].") % (task.name, task.returncode)
		else:
			messageboxtyp = MessageBox.TYPE_INFO
			msg_msg = _("Run script") + _(" ('%s') ends with error messages.") % task.name
		if task_Stout and (task.returncode != 0 or task_Sterr):
			message += msg_msg + msg_out
		if task_Sterr:
			if message:
				message += msg_err
			else:
				message += msg_msg + msg_err
		timeout = 0
		if not message and task.returncode == 0 and config.plugins.filecommander.showScriptCompleted_message.value:
			timeout = 30
			msg_out = ''
			if task_Stout:
				msg_out = '\n\n' + '\n'.join(task_Stout[lines:])
			message += _("Run script") + _(" ('%s') ends successfully.") % task.name + msg_out

		task_Stout = []
		task_Sterr = []

		if message:
			self.showMessage(message, messageboxtyp, timeout)
			return True
		return task.returncode == 0

	def showMessage(self, message, messageboxtyp, timeout):
		from Screens.Standby import inStandby
		if InfoBar.instance and not inStandby:
			InfoBar.instance.openInfoBarMessage(message, messageboxtyp, timeout)
		else:
			Tools.Notifications.AddNotification(MessageBox, message, type=messageboxtyp, timeout=timeout)


def task_processStdout(data):
	global task_Stout
	for line in data.split('\n'):
		if line:
			task_Stout.append(line)
	while len(task_Stout) > 10:
		task_Stout.pop(0)


def task_processSterr(data):
	global task_Sterr
	for line in data.split('\n'):
		if line:
			task_Sterr.append(line)
	while len(task_Sterr) > 10:
		task_Sterr.pop(0)


class key_actions(stat_info):
	hashes = {
		"MD5": "md5sum",
		"SHA1": "sha1sum",
		"SHA3": "sha3sum",
		"SHA256": "sha256sum",
		"SHA512": "sha512sum",
	}

	progPackages = {
		"file": "file",
		"ffprobe": "ffmpeg",
		#  "mediainfo": "mediainfo",
	}

	SIZESCALER = UnitScaler(scaleTable=UnitMultipliers.Jedec, maxNumLen=3, decimals=1)

	def __init__(self):
		stat_info.__init__(self)

	@staticmethod
	def have_program(prog):
		path = os.environ.get('PATH')
		if '/' in prog or not path:
			return os.access(prog, os.X_OK)
		for dir in path.split(':'):
			if os.access(os.path.join(dir, prog), os.X_OK):
				return True
		return False

	def change_mod(self, dirsource):
		filename = dirsource.getFilename()
		sourceDir = dirsource.getCurrentDirectory()  # self.SOURCELIST.getCurrentDirectory()

		if filename is None or sourceDir is None:
			self.session.open(MessageBox, _("It is not possible to change the file mode of <List of Storage Devices>"), type=MessageBox.TYPE_ERROR)
			return

		self.longname = sourceDir + filename
		if not dirsource.canDescent():
			askList = [(_("Set archive mode (644)"), "CHMOD644"), (_("Set executable mode (755)"), "CHMOD755"), (_("Cancel"), "NO")]
			self.session.openWithCallback(self.do_change_mod, ChoiceBox, title=(_("Do you want change rights?\n") + filename), list=askList)
		else:
			self.session.open(MessageBox, _("Not allowed with folders"), type=MessageBox.TYPE_INFO, close_on_any_key=True)

	def do_change_mod(self, answer):
		answer = answer and answer[1]
		# sourceDir = dirsource.getCurrentDirectory() #self.SOURCELIST.getCurrentDirectory()
		if answer == "CHMOD644":
			os.system("chmod 644 " + self.longname)
		elif answer == "CHMOD755":
			os.system("chmod 755 " + self.longname)
		self.doRefresh()

	def Humanizer(self, size):
		if (size < 1024):
			humansize = str(size) + " B"
		elif (size < 1048576):
			humansize = str(size / 1024) + " KB"
		else:
			humansize = str(round(float(size) / 1048576, 2)) + " MB"
		return humansize

	def Info(self, dirsource):
		filename = dirsource.getFilename()
		sourceDir = dirsource.getCurrentDirectory()
		if dirsource.canDescent():
			if dirsource.getSelectionIndex() != 0:
				if (not sourceDir) and (not filename):
					return pname
				else:
					pathname = filename
		else:
			pathname = sourceDir + filename
		try:
			st = os.lstat(os.path.normpath(pathname))
		except:
			return ""
		info = ' '.join(self.SIZESCALER.scale(st.st_size)) + "B    "
		info += self.formatTime(st.st_mtime) + "    "
		info += _("Mode %s (%04o)") % (self.fileModeStr(st.st_mode), stat.S_IMODE(st.st_mode))
		return info

	def statInfo(self, dirsource):
		filename = dirsource.getFilename()
		sourceDir = dirsource.getCurrentDirectory()
		if dirsource.canDescent():
			if dirsource.getSelectionIndex() != 0:
				if (not sourceDir) and (not filename):
					return pname
				else:
					pathname = filename
		else:
			pathname = sourceDir + filename
		try:
			st = os.lstat(os.path.normpath(pathname))
		except:
			return ()

		# Numbers in trailing comments are the template text indexes
		symbolicmode = self.fileModeStr(st.st_mode)
		octalmode = "%04o" % stat.S_IMODE(st.st_mode)
		modes = (
			octalmode,  # 0
			symbolicmode,  # 1
			_("%s (%s)") % (octalmode, symbolicmode)  # 2
		)

		if stat.S_ISCHR(st.st_mode) or stat.S_ISBLK(st.st_mode):
			sizes = ("", "", "")
		else:
			bytesize = "%s" % "{:n}".format(st.st_size)
			scaledsize = ' '.join(self.SIZESCALER.scale(st.st_size)) + 'B'
			sizes = (
				bytesize,  # 10
				_("%s") % scaledsize,  # 11
				_("%s (%s") % (bytesize, scaledsize)  # 12
			)

		return [modes + (
			"%d" % st.st_ino,  # 3
			"%d, %d" % ((st.st_dev >> 8) & 0xff, st.st_dev & 0xff),   # 4
			"%d" % st.st_nlink,  # 5
			"%d" % st.st_uid,  # 6
			"%s" % self.username(st.st_uid),  # 7
			"%d" % st.st_gid,  # 8
			"%s" % self.groupname(st.st_gid)  # 9
		) + sizes + (
			self.formatTime(st.st_mtime),  # 13
			self.formatTime(st.st_atime),  # 14
			self.formatTime(st.st_ctime)  # 15
		)]

	@staticmethod
	def fileFilter():
		if config.plugins.filecommander.extension.value == "myfilter":
			return "^.*\.%s" % config.plugins.filecommander.my_extension.value
		else:
			return config.plugins.filecommander.extension.value

	@staticmethod
	def filterSettings():
		return(
			config.plugins.filecommander.extension.value,
			config.plugins.filecommander.my_extension.value
		)

	def run_script(self, dirsource, dirtarget):
		filename = dirsource.getFilename()
		sourceDir = dirsource.getCurrentDirectory()
		self.commando = sourceDir + filename
		self.parameter = ''
		targetdir = dirtarget.getCurrentDirectory()
		if targetdir is not None:
			file = dirtarget.getFilename() or ''
			if file.startswith(targetdir):
				self.parameter = file
			elif not targetdir.startswith(file):
				self.parameter = targetdir + file
			else:
				self.parameter = targetdir
		stxt = _('python')
		if self.commando.endswith('.sh'):
			stxt = _('shell')
		askList = [(_("Cancel"), "NO"), (_("View or edit this %s script") % stxt, "VIEW"), (_("Run script"), "YES"), (_("Run script in background"), "YES_BG")]
		if self.parameter:
			askList.append((_("Run script with optional parameter"), "PAR"))
			askList.append((_("Run script with optional parameter in background"), "PAR_BG"))
			filename += _('\noptional parameter:\n%s') % self.parameter
		self.session.openWithCallback(self.do_run_script, ChoiceBox, title=_("Do you want to view or run the script?\n") + filename, list=askList)

	def do_run_script(self, answer):
		answer = answer and answer[1]
		if answer in ("YES", "PAR", "YES_BG", "PAR_BG"):
			if not os.access(self.commando, os.R_OK):
				self.session.open(MessageBox, _("Script '%s' must have read permission to be able to run it") % self.commando, type=MessageBox.TYPE_ERROR, close_on_any_key=True)
				return
			nice = config.plugins.filecommander.script_priority_nice.value or ''
			ionice = config.plugins.filecommander.script_priority_ionice.value or ''
			if nice:
				nice = 'nice -n %d ' % nice
			if ionice:
				ionice = 'ionice -c %d ' % ionice
			priority = '%s%s' % (nice, ionice)
			if self.commando.endswith('.sh'):
				if os.access(self.commando, os.X_OK):
					if 'PAR' in answer:
						cmdline = "%s%s '%s'" % (priority, self.commando, self.parameter)
					else:
						cmdline = "%s%s" % (priority, self.commando)
				else:
					if 'PAR' in answer:
						cmdline = "%s/bin/sh %s '%s'" % (priority, self.commando, self.parameter)
					else:
						cmdline = "%s/bin/sh %s" % (priority, self.commando)
			else:
				if 'PAR' in answer:
					cmdline = "%s/usr/bin/python %s '%s'" % (priority, self.commando, self.parameter)
				else:
					cmdline = "%s/usr/bin/python %s" % (priority, self.commando)
		elif answer == "VIEW":
			try:
				yfile = os.stat(self.commando)
			except OSError as oe:
				self.session.open(MessageBox, _("%s: %s") % (self.commando, oe.strerror), type=MessageBox.TYPE_ERROR)
				return
			if (yfile.st_size < 1000000):
				self.session.open(vEditor, self.commando)

		if answer and answer not in ("NO", "VIEW"):
			if answer.endswith('_BG'):
				global task_Stout, task_Sterr
				task_Stout = []
				task_Sterr = []
				if 'PAR' in answer:
					name = '%s%s %s' % (priority, self.commando, self.parameter)
				else:
					name = '%s%s' % (priority, self.commando)
				job = Job(_("Run script") + " ('%s')" % name)
				task = Task(job, name)
				task.postconditions.append(task_postconditions())
				task.processStdout = task_processStdout
				task.processStderr = task_processSterr
				task.setCmdline(cmdline)
				job_manager.AddJob(job, onSuccess=self.finishedCB, onFail=self.failCB)
				self.jobs += 1
				self.onLayout()
			else:
				self.session.open(Console, cmdlist=(cmdline,))

	def run_file(self):
		if self.disableActions_Timer.isActive():
			return
		self.run_prog("file")

	def run_ffprobe(self):
		if self.disableActions_Timer.isActive():
			return
		self.run_prog("ffprobe", "-hide_banner")

	def run_mediainfo(self):
		if self.disableActions_Timer.isActive():
			return
		self.run_prog("mediainfo")

	def run_prog(self, prog, args=None):
		if not self.have_program(prog):
			pkg = self.progPackages.get(prog)
			if pkg:
				self._opkgArgs = ("install", pkg)
				self.session.openWithCallback(self.doOpkgCB, MessageBox, _("Program '%s' needs to be installed to run this action.\nInstall the '%s' package to install the program?") % (prog, pkg), type=MessageBox.TYPE_YESNO, default=True)
			else:
				self.session.open(MessageBox, _("Program '%s' not installed.\nThe package containing this program isn't known.") % (prog, how_to), type=MessageBox.TYPE_ERROR, close_on_any_key=True)
			return

		filename = self.SOURCELIST.getFilename()

		if filename is None:
			self.session.open(MessageBox, _("It is not possible to run '%s' on <List of Storage Devices>") % prog, type=MessageBox.TYPE_ERROR)
			return

		if filename.startswith("/"):
			if prog != "file":
				self.session.open(MessageBox, _("You can't usefully run '%s' on a directory.") % prog, type=MessageBox.TYPE_ERROR, close_on_any_key=True)
				return
			filepath = filename
			filename = os.path.basename(os.path.normpath(filepath)) or '/'
			filetype = "directory"
		else:
			sourceDir = self.SOURCELIST.getCurrentDirectory()
			__, filetype = os.path.splitext(filename.lower())
			filepath = os.path.join(sourceDir, filename)
		if prog == "file" or filetype == ".ts" or filetype in MOVIE_EXTENSIONS:
			if args is None:
				args = ()
			elif not isinstance(args, (tuple, list)):
				args = (args,)
			toRun = (prog,) + tuple(args) + (filepath,)
			self._progConsole = self.session.open(Console, cmdlist=(toRun,), finishedCallback=self.progConsoleCB)
		else:
			self.session.open(MessageBox, _("You can't usefully run '%s' on '%s'.") % (prog, filename), type=MessageBox.TYPE_ERROR, close_on_any_key=True)

	def progConsoleCB(self):
		if hasattr(self, "_progConsole") and "text" in self._progConsole:
			self._progConsole["text"].setPos(0)
			self._progConsole["text"].updateScrollbar()

	def help_run_file(self):
		if self.disableActions_Timer.isActive():
			return
		return self.help_run_prog("file")

	def help_run_ffprobe(self):
		if self.disableActions_Timer.isActive():
			return
		return self.help_run_prog("ffprobe")

	def help_run_mediainfo(self):
		if self.disableActions_Timer.isActive():
			return
		return self.help_run_prog("mediainfo")

	def help_run_prog(self, prog):
		if self.have_program(prog):
			return _("Run '%s' command") % prog
		else:
			if prog in self.progPackages:
				return _("Install '%s' and enable this operation") % prog
			else:
				return _("'%s' not installed and no known package") % prog

	def uninstall_file(self):
		self.uninstall_prog("file")

	def uninstall_ffprobe(self):
		self.uninstall_prog("ffprobe")

	def uninstall_mediainfo(self):
		self.uninstall_prog("mediainfo")

	def uninstall_prog(self, prog):
		if self.have_program(prog):
			pkg = self.progPackages.get(prog)
			if pkg:
				self._opkgArgs = ("remove", pkg)
				self.session.openWithCallback(self.doOpkgCB, MessageBox, _("Program '%s' needs to be installed to run the '%s' action.\nUninstall the '%s' package to uninstall the program?") % (prog, prog, pkg), type=MessageBox.TYPE_YESNO, default=True)
				return True
			else:
				self.session.open(MessageBox, _("Program '%s' is installed.\nThe package containing this program isn't known, so it can't be uninstalled.") % (prog, how_to), type=MessageBox.TYPE_ERROR, close_on_any_key=True)
		return False

	def doOpkgCB(self, ans):
		if ans and hasattr(self, "_opkgArgs"):
			self.session.open(Console, cmdlist=((("opkg",) + self._opkgArgs),))
			del self._opkgArgs

	def help_uninstall_file(self):
		return self.help_uninstall_prog("file")

	def help_uninstall_ffprobe(self):
		return self.help_uninstall_prog("ffprobe")

	def help_uninstall_mediainfo(self):
		return self.help_uninstall_prog("mediainfo")

	def help_uninstall_prog(self, prog):
		if self.have_program(prog):
			pkg = self.progPackages.get(prog)
			if pkg:
				return _("Uninstall '%s' package and disable '%s'") % (pkg, prog)
		return None

	def run_hashes(self):
		if not config.plugins.filecommander.hashes.value:
			self.session.open(MessageBox, _("No hash calculations configured"), type=MessageBox.TYPE_ERROR, close_on_any_key=True)
			return
		progs = tuple((h, self.hashes[h]) for h in config.plugins.filecommander.hashes.value if h in self.hashes and self.have_program(self.hashes[h]))
		if not progs:
			self.session.open(MessageBox, _("None of the hash programs for the hashes %s are available") % ''.join(config.plugins.filecommander.hashes.value), type=MessageBox.TYPE_ERROR, close_on_any_key=True)
			return
		filename = self.SOURCELIST.getFilename()

		if filename is None:
			self.session.open(MessageBox, _("It is not possible to calculate hashes on <List of Storage Devices>"), type=MessageBox.TYPE_ERROR)
			return

		if filename.startswith("/"):
			self.session.open(MessageBox, _("The hash of a directory can't be calculated."), type=MessageBox.TYPE_ERROR, close_on_any_key=True)
			return
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		filepath = os.path.join(sourceDir, filename)
		toRun = []
		for prog in progs:
			toRun += [("echo", "-n", prog[0] + ": "), (prog[1], filepath)]
		self.session.open(Console, cmdlist=toRun)

	def play_music(self, dirsource):
		self.sourceDir = dirsource
		askList = [(_("Play title"), "SINGLE"), (_("Play folder"), "LIST"), (_("Cancel"), "NO")]
		self.session.openWithCallback(self.do_play_music, ChoiceBox, title=_("What do you want to play?\n") + self.sourceDir.getFilename(), list=askList)

	def do_play_music(self, answer):
		longname = self.sourceDir.getCurrentDirectory() + self.sourceDir.getFilename()
		answer = answer and answer[1]
		if answer == "SINGLE":
			fileRef = eServiceReference(eServiceReference.idServiceMP3, eServiceReference.noFlags, longname)
			self.session.open(MoviePlayer, fileRef)
		elif answer == "LIST":
			self.music_playlist()

	def music_playlist(self):
		fileList = []
		from Plugins.Extensions.MediaPlayer.plugin import MediaPlayer
		self.beforeService = self.session.nav.getCurrentlyPlayingServiceReference()
		path = self.sourceDir.getCurrentDirectory()
		mp = self.session.open(MediaPlayer)
		mp.callback = self.cbmusic_playlist
		mp.playlist.clear()
		mp.savePlaylistOnExit = False
		i = 0
		start_song = -1
		filename = self.sourceDir.getFilename()
		fileList = self.sourceDir.getFileList()
		for x in fileList:
			l = len(x)
			if x[0][0] is not None:
				testFileName = x[0][0].lower()
				_, filetype = os.path.splitext(testFileName)
			else:
				testFileName = x[0][0]  # "empty"
				filetype = None
			if l == 3 or l == 2:
				if not x[0][1]:
					if filetype in AUDIO_EXTENSIONS:
						if filename == x[0][0]:
							start_song = i
						i += 1
						mp.playlist.addFile(eServiceReference(4097, 0, path + x[0][0]))
			elif l >= 5:
				testFileName = x[4].lower()
				_, filetype = os.path.splitext(testFileName)
				if filetype in AUDIO_EXTENSIONS:
					if filename == x[0][0]:
						start_song = i
					i += 1
					mp.playlist.addFile(eServiceReference(4097, 0, path + x[4]))
		if start_song < 0:
			start_song = 0
		mp.changeEntry(start_song)
		mp.switchToPlayList()

	def cbmusic_playlist(self, data=None):
		if self.beforeService is not None:
			self.session.nav.playService(self.beforeService)
			self.beforeService = None

	def cbShowPicture(self, idx=0):
		if idx > 0:
			self.SOURCELIST.moveToIndex(idx)

	def onFileAction(self, dirsource, dirtarget):
		filename = dirsource.getFilename()
		self.SOURCELIST = dirsource
		self.TARGETLIST = dirtarget
		sourceDir = dirsource.getCurrentDirectory()
		if not sourceDir.endswith("/"):
			sourceDir = sourceDir + "/"
		testFileName = filename.lower()
		filetype = os.path.splitext(testFileName)[1]
		longname = sourceDir + filename
		print("[Filebrowser]:", filename, sourceDir, testFileName)
		if not fileExists(longname):
			self.session.open(MessageBox, _("File not found: %s") % longname, type=MessageBox.TYPE_ERROR)
			return
		if filetype == ".ipk":
			self.session.openWithCallback(self.onFileActionCB, ipkMenuScreen, self.SOURCELIST, self.TARGETLIST)
		elif filetype == ".ts":
			fileRef = eServiceReference(eServiceReference.idDVB, eServiceReference.noFlags, longname)
			self.session.open(MoviePlayer, fileRef)
		elif filetype in MOVIE_EXTENSIONS:
			fileRef = eServiceReference(eServiceReference.idServiceMP3, eServiceReference.noFlags, longname)
			self.session.open(MoviePlayer, fileRef)
		elif filetype in DVD_EXTENSIONS:
			if DVDPlayerAvailable:
				self.session.open(DVD.DVDPlayer, dvd_filelist=[longname])
		elif filetype in AUDIO_EXTENSIONS:
			self.play_music(self.SOURCELIST)
		elif filetype == ".rar" or re.search('\.r\d+$', filetype):
			self.session.openWithCallback(self.onFileActionCB, RarMenuScreen, self.SOURCELIST, self.TARGETLIST)
		elif testFileName.endswith(".tar.gz") or filetype in (".tgz", ".tar"):
			self.session.openWithCallback(self.onFileActionCB, TarMenuScreen, self.SOURCELIST, self.TARGETLIST)
		elif filetype == ".gz":  # Must follow test for .tar.gz
			self.session.openWithCallback(self.onFileActionCB, GunzipMenuScreen, self.SOURCELIST, self.TARGETLIST)
		elif filetype == ".zip":
			self.session.openWithCallback(self.onFileActionCB, UnzipMenuScreen, self.SOURCELIST, self.TARGETLIST)
		elif filetype in IMAGE_EXTENSIONS:
			if self.SOURCELIST.getSelectionIndex() != 0:
				self.session.openWithCallback(
					self.cbShowPicture,
					ImageViewer,
					self.SOURCELIST.getFileList(),
					self.SOURCELIST.getSelectionIndex(),
					self.SOURCELIST.getCurrentDirectory(),
					filename
				)
		elif filetype in (".sh", ".py", ".pyo"):
			self.run_script(self.SOURCELIST, self.TARGETLIST)
		elif filetype == ".mvi":
			self.file_name = longname
			self.tmp_file = '/tmp/grab_%s_mvi.png' % filename[:-4]
			choice = [(_("No"), "no"),
					(_("Show as Picture (press any key to close)"), "show")]
			savetext = ''
			stat = os.statvfs('/tmp/')
			if stat.f_bavail * stat.f_bsize > 1000000:
				choice.append((_("Show as Picture and save as file ('%s')") % self.tmp_file, "save"))
				savetext = _(" or save additional the picture to a file")
			self.session.openWithCallback(self.mviFileCB, MessageBox, _("Show '%s' as picture%s?\nThe current service must interrupted!") % (longname, savetext), simple=True, list=choice)
		elif filetype in TEXT_EXTENSIONS or config.plugins.filecommander.unknown_extension_as_text.value:
			try:
				xfile = os.stat(longname)
			except OSError as oe:
				self.session.open(MessageBox, _("%s: %s") % (longname, oe.strerror), type=MessageBox.TYPE_ERROR)
				return
			if (xfile.st_size < 1000000):
				self.session.open(vEditor, longname)
				self.onFileActionCB(True)
		else:
			try:
				found_viewer = openFile(self.session, guess_type(longname)[0], longname)
			except TypeError as e:
				found_viewer = False
			if not found_viewer:
				self.session.open(MessageBox, _("No viewer installed for this file type: %s") % filename, type=MessageBox.TYPE_ERROR, timeout=5, close_on_any_key=True)

	def mviFileCB(self, ret=None):
		if ret and ret != 'no':
			global last_service
			last_service = self.session.nav.getCurrentlyPlayingServiceReference()
			cmd = "/usr/bin/showiframe '%s'" % self.file_name
			self.session.nav.stopService()
			self.hide()
		if ret == 'show':
			eActionMap.getInstance().bindAction('', -maxsize - 1, self.showCB)
			console().ePopen(cmd)
		elif ret == 'save':
			if os.path.isfile(self.tmp_file):
				os.remove(self.tmp_file)
			cmd = [cmd, "/usr/bin/grab -v -p %s" % self.tmp_file]
			console().eBatch(cmd, self.saveCB)
			self.disableActions_Timer.startLongTimer(10)

	def showCB(self, key=None, flag=1):
		self.show()
		self.session.nav.playService(last_service)
		eActionMap.getInstance().unbindAction('', self.showCB)
		self.disableActions_Timer.start(100, True)

	def saveCB(self, extra_args):
		global last_service
		if hasattr(self, 'session'):
			self.disableActions_Timer.startLongTimer(1)
			self.session.nav.playService(last_service)
			self.show()
			if os.path.isfile(self.tmp_file):
				filename = self.tmp_file.split('/')[-1]
				self.session.open(ImageViewer, [((filename, ''), '')], 0, self.tmp_file.replace(filename, ''), filename)
			else:
				self.session.open(MessageBox, _("File not found: %s") % self.tmp_file, type=MessageBox.TYPE_ERROR)
		else:
			import NavigationInstance
			if last_service and NavigationInstance.instance:
				NavigationInstance.instance.playService(last_service)
				last_service = None
			Tools.Notifications.AddNotification(MessageBox, _("The function has interrupted.\nDon't press in the next time any key until the picture from mvi-file is displayed!"), type=MessageBox.TYPE_ERROR, timeout=10)

	def onFileActionCB(self, result):
		# os.system('echo %s > /tmp/test.log' % (result))
		# print result
		self.SOURCELIST.refresh()
		self.TARGETLIST.refresh()
