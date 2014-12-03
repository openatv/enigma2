#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from Plugins.Plugin import PluginDescriptor
# Components
from Components.config import config, ConfigSubList, ConfigSubsection, ConfigInteger, ConfigYesNo, ConfigText, getConfigListEntry, ConfigSelection, NoSave, ConfigNothing
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.FileTransfer import FileTransferJob
from Components.Task import job_manager
from Components.ActionMap import ActionMap
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
#from Tools.HardwareInfo import HardwareInfo
# Various
from os.path import isdir as os_path_isdir
from mimetypes import guess_type
from enigma import eServiceReference, eServiceCenter, eTimer, eSize, eConsoleAppContainer, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER
from os import listdir, remove, rename, system, path, symlink, chdir
from os import system as os_system
from os import stat as os_stat
from os import walk as os_walk
from os import popen as os_popen
from os import path as os_path
from os import listdir as os_listdir
from time import strftime as time_strftime
from time import localtime as time_localtime

import os
# System mods
#from InputBoxmod import InputBox
#from FileListmod import FileList, MultiFileSelectList
# Addons
#from unrar import *
from Plugins.Extensions.FileCommander.addons.unrar import *
from Plugins.Extensions.FileCommander.addons.tar import *
from Plugins.Extensions.FileCommander.addons.unzip import *
from Plugins.Extensions.FileCommander.addons.ipk import *
from Plugins.Extensions.FileCommander.addons.type_utils import *

try:
	from Screens import DVD
	DVDPlayerAvailable = True
except Exception, e:
	DVDPlayerAvailable = False

##################################

pname = _("File Commander - Addon Movieplayer")
pdesc = _("play Files")

class key_actions():
	def __init__(self):
		pass


	def change_mod(self, dirsource):
		filename = dirsource.getFilename()
		sourceDir = dirsource.getCurrentDirectory() #self.SOURCELIST.getCurrentDirectory()
		self.longname = sourceDir + filename
		if not dirsource.canDescent():
			askList = [(_("Set archive mode (644)"), "CHMOD644"),(_("Set executable mode (755)"), "CHMOD755"),(_("Cancel"), "NO")]	
			self.session.openWithCallback(self.do_change_mod, ChoiceBox, title=_("Do you want change rights?\\n" + filename), list=askList)
		else:
			self.session.open(MessageBox,_("Not allowed with folders"), type = MessageBox.TYPE_INFO, close_on_any_key = True)

		
	def do_change_mod(self, answer):
		answer = answer and answer[1]
	#	sourceDir = dirsource.getCurrentDirectory() #self.SOURCELIST.getCurrentDirectory()
		if answer == "CHMOD644":
			os_system("chmod 644 " + self.longname)
		elif answer == "CHMOD755":
			os_system("chmod 755 " + self.longname)
		self.doRefresh()
	
	def Humanizer(self, size):
		if (size < 1024):
			humansize = str(size)+" B"
		elif (size < 1048576):
			humansize = str(size/1024)+" KB"
		else:
			humansize = str(round(float(size)/1048576,2))+" MB"
		return humansize
	
	def Info(self, dirsource):
		filename = dirsource.getFilename()
		sourceDir = dirsource.getCurrentDirectory() #self.SOURCELIST.getCurrentDirectory()
		mytest = dirsource.canDescent()
		if dirsource.canDescent():
			if dirsource.getSelectionIndex()!=0:
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
				dir_infos = "   " + _("Size") + str(self.Humanizer(dir_stats.st_size))+"    "
				dir_infos = dir_infos + _("Date") + " " + time_strftime("%d.%m.%Y - %H:%M:%S",time_localtime(dir_stats.st_mtime))+"    "
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
			file_infos = filename + "   " + _("Size") + " " + str(self.Humanizer(file_stats.st_size))+"    "
			file_infos = file_infos + _("Date") + " " + time_strftime("%d.%m.%Y - %H:%M:%S",time_localtime(file_stats.st_mtime))+"    "
			file_infos = file_infos + _("Mode") + " " + str(mode[-3:])
			return (file_infos)

	def run_script(self, dirsource):
		filename = dirsource.getFilename()
		sourceDir = dirsource.getCurrentDirectory()
		longname = sourceDir + filename
		self.commando = [ longname ]
		askList = [(_("Cancel"), "NO"),(_("View this shell-script"), "VIEW"),(_("Start execution"), "YES")]
		self.session.openWithCallback(self.do_run_script, ChoiceBox, title=_("Do you want to execute?\\n"+filename), list=askList)

	def do_run_script(self, answer):
		answer = answer and answer[1]
		if answer == "YES":
			self.session.open(Console, cmdlist = [ self.commando[0] ])
		elif answer == "VIEW":
			yfile=os_stat(self.commando[0])
			if (yfile.st_size < 61440):
				self.session.open(vEditor, self.commando[0])

	def play_music(self, dirsource):
		self.sourceDir = dirsource
		askList = [(_("Play title"), "SINGLE"),(_("Play folder"), "LIST"),(_("Cancel"), "NO")]
		self.session.openWithCallback(self.do_play_music, ChoiceBox, title=_("What do you want to play?\\n"+self.sourceDir.getFilename()), list=askList)

	def do_play_music(self, answer):
		longname = self.sourceDir.getCurrentDirectory() + self.sourceDir.getFilename()
		answer = answer and answer[1]
		if answer == "SINGLE":
			fileRef = eServiceReference("4097:0:0:0:0:0:0:0:0:0:" + longname)
			self.session.open(MoviePlayer, fileRef)
		elif answer == "LIST":
			self.music_playlist()

	def music_playlist(self):
		fileList     = []
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
			l = len(fileList[0])
			if x[0][0] is not None:
				testFileName = x[0][0].lower()
			else:
				testFileName = x[0][0] #"empty"
			if l == 3 or l == 2:
				if x[0][1] == False:
					if testFileName.endswith(tuple(AUDIO_EXTENSIONS)):
						if filename == x[0][0]:
							start_song = i
						i += 1
						mp.playlist.addFile(eServiceReference(4097, 0, path + x[0][0]))
			else:
				testfilename = x[4].lower()
				if testFileName.endswith(tuple(AUDIO_EXTENSIONS)):
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
		if idx > 0: self.SOURCELIST.moveToIndex(idx)

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
		filetype = testFileName.split('.')
		filetype = "." + filetype[-1]
		longname = sourceDir + filename
		print "[Filebrowser]: " + filename, sourceDir, testFileName
		if testFileName.endswith(".ipk"):
			self.session.openWithCallback(self.onFileActionCB, ipkMenuScreen, self.SOURCELIST, self.TARGETLIST)
		elif testFileName.endswith(".ts"):
			fileRef = eServiceReference("1:0:0:0:0:0:0:0:0:0:" + longname)
			self.session.open(MoviePlayer, fileRef)
		elif testFileName.endswith(tuple(MOVIE_EXTENSIONS)):
			fileRef = eServiceReference("4097:0:0:0:0:0:0:0:0:0:" + longname)
			self.session.open(MoviePlayer, fileRef)
		elif testFileName.endswith(tuple(DVD_EXTENSIONS)):
			if DVDPlayerAvailable:
				self.session.open(DVD.DVDPlayer, dvd_filelist=[longname])
		elif testFileName.endswith(tuple(AUDIO_EXTENSIONS)):
			self.play_music(self.SOURCELIST)
		elif (testFileName.endswith(".rar")) or (re.search('\.r\d+$', filetype)):
			self.session.openWithCallback(self.onFileActionCB, RarMenuScreen, self.SOURCELIST, self.TARGETLIST)
		elif (testFileName.endswith(".gz")) or (testFileName.endswith(".tar")):
			self.session.openWithCallback(self.onFileActionCB, TarMenuScreen, self.SOURCELIST, self.TARGETLIST)
		elif (testFileName.endswith(".zip")):
			self.session.openWithCallback(self.onFileActionCB, UnzipMenuScreen, self.SOURCELIST, self.TARGETLIST)
		elif testFileName.endswith(tuple(IMAGE_EXTENSIONS)):
			if self.SOURCELIST.getSelectionIndex()!=0:
				self.session.openWithCallback(self.cbShowPicture, 
							      ImageViewer, 
							      self.SOURCELIST.getFileList(), 
					  		    self.SOURCELIST.getSelectionIndex(), 
					      		self.SOURCELIST.getCurrentDirectory(),
					      		filename)
		elif testFileName.endswith(".sh"):
			self.run_script(self.SOURCELIST)
		elif testFileName.endswith(".txt") or testFileName.endswith(".log") or testFileName.endswith(".py") or testFileName.endswith(".xml") or testFileName.endswith(".html") or testFileName.endswith(".meta") or testFileName.endswith(".bak") or testFileName.endswith(".lst") or testFileName.endswith(".cfg"):
			xfile=os_stat(longname)
#			if (xfile.st_size < 61440):
			if (xfile.st_size < 1000000):
				self.session.open(vEditor, longname)
				self.onFileActionCB(True)
		else:
			try:
				x = openFile(self.session,guess_type(self.SOURCELIST.getFilename())[0],self.SOURCELIST.getCurrentDirectory()+self.SOURCELIST.getFilename())
			except TypeError,e:
				self.session.open(MessageBox,_("no Viewer installed for this mimetype!"), type = MessageBox.TYPE_ERROR, timeout = 5, close_on_any_key = True)
#			try:
#				xfile=os_stat(longname)
##				if (xfile.st_size < 61440):
#				self.session.open(vEditor, longname)

	def onFileActionCB(self,result):
#		os.system('echo %s > /tmp/test.log' % (result))
		#print result
		self.SOURCELIST.refresh()
		self.TARGETLIST.refresh()
