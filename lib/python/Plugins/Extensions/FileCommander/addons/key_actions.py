#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from Plugins.Plugin import PluginDescriptor
# Components
from Components.config import config, ConfigSubList, ConfigSubsection, ConfigInteger, ConfigYesNo, ConfigText, getConfigListEntry, ConfigSelection, NoSave, ConfigNothing
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Task import job_manager
from Components.Scanner import openFile
from Components.MenuList import MenuList
from Components.MovieList import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, MOVIE_EXTENSIONS, DVD_EXTENSIONS, KNOWN_EXTENSIONS
# Screens
from Screens.Screen import Screen
from Screens.Console import Console
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.LocationBox import MovieLocationBox
from Screens.HelpMenu import HelpableScreen
from Screens.TaskList import TaskListScreen
from Screens.InfoBar import MoviePlayer as Movie_Audio_Player
# Tools
from Tools.Directories import *
from Tools.BoundFunction import boundFunction
# from Tools.HardwareInfo import HardwareInfo
# Various
from os.path import isdir as os_path_isdir
from os.path import splitext as os_path_splitext
from mimetypes import guess_type
from enigma import eServiceReference, eServiceCenter, eTimer, eSize, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER
from os import listdir, remove, rename, system, path, symlink, chdir
from os import system as os_system
from os import stat as os_stat
from os import walk as os_walk
from os import popen as os_popen
from os import path as os_path
from os import listdir as os_listdir
from time import strftime as time_strftime
from time import localtime as time_localtime
import stat
import pwd
import grp
import time

import os

# Addons
# from unrar import *
from Plugins.Extensions.FileCommander.addons.unrar import *
from Plugins.Extensions.FileCommander.addons.tar import *
from Plugins.Extensions.FileCommander.addons.unzip import *
from Plugins.Extensions.FileCommander.addons.gz import *
from Plugins.Extensions.FileCommander.addons.ipk import *
from Plugins.Extensions.FileCommander.addons.type_utils import *

TEXT_EXTENSIONS = frozenset((".txt", ".log", ".py", ".xml", ".html", ".meta", ".bak", ".lst", ".cfg", ".conf", ".srt"))

try:
	from Screens import DVD
	DVDPlayerAvailable = True
except Exception, e:
	DVDPlayerAvailable = False

##################################

pname = _("File Commander - Addon Movieplayer")
pdesc = _("play Files")

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

class key_actions():
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

	def __init__(self):
		pass

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
		self.longname = sourceDir + filename
		if not dirsource.canDescent():
			askList = [(_("Set archive mode (644)"), "CHMOD644"), (_("Set executable mode (755)"), "CHMOD755"), (_("Cancel"), "NO")]
			self.session.openWithCallback(self.do_change_mod, ChoiceBox, title=_("Do you want change rights?\\n" + filename), list=askList)
		else:
			self.session.open(MessageBox, _("Not allowed with folders"), type=MessageBox.TYPE_INFO, close_on_any_key=True)

	def do_change_mod(self, answer):
		answer = answer and answer[1]
		# sourceDir = dirsource.getCurrentDirectory() #self.SOURCELIST.getCurrentDirectory()
		if answer == "CHMOD644":
			os_system("chmod 644 " + self.longname)
		elif answer == "CHMOD755":
			os_system("chmod 755 " + self.longname)
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
		sourceDir = dirsource.getCurrentDirectory()  # self.SOURCELIST.getCurrentDirectory()
		mytest = dirsource.canDescent()
		if dirsource.canDescent():
			if dirsource.getSelectionIndex() != 0:
				if (not sourceDir) and (not filename):
					return pname
				else:
					sourceDir = filename
				if os_path_isdir(sourceDir):
					mode = os.stat(sourceDir).st_mode
				else:
					return ("")
				mode = oct(mode)
				curSelDir = sourceDir
				dir_stats = os_stat(curSelDir)
				dir_infos = "   " + str(self.Humanizer(dir_stats.st_size)) + "    "
				dir_infos = dir_infos + time_strftime(config.usage.date.daylong.value + " " + config.usage.time.long.value, time_localtime(dir_stats.st_mtime)) + "    "
				dir_infos = dir_infos + _("Mode") + " " + str(mode[-3:])
				return (dir_infos)
			else:
				return ("")
		else:
			longname = sourceDir + filename
			if fileExists(longname):
				mode = os.stat(longname).st_mode
			else:
				return ("")
			mode = oct(mode)
			file_stats = os_stat(longname)
			file_infos = filename + "   " + str(self.Humanizer(file_stats.st_size)) + "    "
			file_infos = file_infos + time_strftime(config.usage.date.daylong.value + " " + config.usage.time.long.value, time_localtime(file_stats.st_mtime)) + "    "
			file_infos = file_infos + _("Mode") + " " + str(mode[-3:])
			return (file_infos)

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

	def run_script(self, dirsource):
		filename = dirsource.getFilename()
		sourceDir = dirsource.getCurrentDirectory()
		longname = sourceDir + filename
		self.commando = (longname,)
		askList = [(_("Cancel"), "NO"), (_("View or edit this shell script"), "VIEW"), (_("Run script"), "YES")]
		self.session.openWithCallback(self.do_run_script, ChoiceBox, title=_("Do you want to view or run the script?\n" + filename), list=askList)

	def do_run_script(self, answer):
		answer = answer and answer[1]
		if answer == "YES":
			if not os.access(self.commando[0], os.R_OK):
				self.session.open(MessageBox, _("Script '%s' must have read permission to be able to run it") % self.commando[0], type=MessageBox.TYPE_ERROR, close_on_any_key=True)
				return

			if os.access(self.commando[0], os.X_OK):
				self.session.open(Console, cmdlist=(self.commando,))
			else:
				self.session.open(Console, cmdlist=((("/bin/sh",) + self.commando),))
		elif answer == "VIEW":
			try:
				yfile = os_stat(self.commando[0])
			except OSError as oe:
				self.session.open(MessageBox, _("%s: %s") % (self.commando[0], oe.strerror), type=MessageBox.TYPE_ERROR)
				return
			if (yfile.st_size < 61440):
				self.session.open(vEditor, self.commando[0])

	def run_file(self):
		self.run_prog("file")

	def run_ffprobe(self):
		self.run_prog("ffprobe", "-hide_banner")

	def run_mediainfo(self):
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
		return self.help_run_prog("file")

	def help_run_ffprobe(self):
		return self.help_run_prog("ffprobe")

	def help_run_mediainfo(self):
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
		self.session.openWithCallback(self.do_play_music, ChoiceBox, title=_("What do you want to play?\n" + self.sourceDir.getFilename()), list=askList)

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
				_, filetype = os_path_splitext(testFileName)
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
				_, filetype = os_path_splitext(testFileName)
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
		self.SOURCELIST = dirsource
		self.TARGETLIST = dirtarget
		filename = dirsource.getFilename()
		self.SOURCELIST = dirsource
		self.TARGETLIST = dirtarget
		sourceDir = dirsource.getCurrentDirectory()
		if not sourceDir.endswith("/"):
			sourceDir = sourceDir + "/"
		testFileName = filename.lower()
		filetype = os_path_splitext(testFileName)[1]
		longname = sourceDir + filename
		print "[Filebrowser]:", filename, sourceDir, testFileName
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
		elif filetype == ".sh":
			self.run_script(self.SOURCELIST)
		elif filetype in TEXT_EXTENSIONS:
			try:
				xfile = os_stat(longname)
			except OSError as oe:
				self.session.open(MessageBox, _("%s: %s") % (longname, oe.strerror), type=MessageBox.TYPE_ERROR)
				return
			# if (xfile.st_size < 61440):
			if (xfile.st_size < 1000000):
				self.session.open(vEditor, longname)
				self.onFileActionCB(True)
		else:
			try:
				found_viewer = openFile(self.session, guess_type(longname)[0], longname)
			except TypeError, e:
				found_viewer = False
			if not found_viewer:
				self.session.open(MessageBox, _("No viewer installed for this file type: %s") % filename, type=MessageBox.TYPE_ERROR, timeout=5, close_on_any_key=True)

	def onFileActionCB(self, result):
		# os.system('echo %s > /tmp/test.log' % (result))
		# print result
		self.SOURCELIST.refresh()
		self.TARGETLIST.refresh()
