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
from InputBoxmod import InputBox
from FileListmod import FileList, MultiFileSelectList
# Addons
from Plugins.Extensions.FileCommander.addons.key_actions import *
from Plugins.Extensions.FileCommander.addons.type_utils import *
from Plugins.Extensions.PicturePlayer.ui import config

MOVIEEXTENSIONS = {"cuts": "movieparts", "meta": "movieparts", "ap": "movieparts", "sc": "movieparts", "eit": "movieparts"}

movie = "(?i)^.*\.(ts|iso|avi|divx|m4v|mpg|mpeg|mkv|mp4|mov|flv|m2ts|mts|3gp|3g2|wmv)"
music = "(?i)^.*\.(m4a|mp2|mp3|wav|ogg|flac|wma)"
pictures = "(?i)^.*\.(jpg|jpeg|jpe|bmp|png|gif)"
records = "(?i)^.*\.(ts)"

dmnapi_py = "/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/addons/dmnapi.py"
##################################

pname = _("File Commander")
pdesc = _("manage local Files")

config.plugins.filecommander = ConfigSubsection()
config.plugins.filecommander.savedir_left = ConfigYesNo(default=True)
config.plugins.filecommander.savedir_right = ConfigYesNo(default=True)
config.plugins.filecommander.add_mainmenu_entry = ConfigYesNo(default=False)
config.plugins.filecommander.add_extensionmenu_entry = ConfigYesNo(default=False)
config.plugins.filecommander.path_default = ConfigText(default="/")
config.plugins.filecommander.path_left = ConfigText(default="/")
config.plugins.filecommander.path_right = ConfigText(default="/")
config.plugins.filecommander.my_extension = ConfigText(default="", visible_width=15, fixed_size=False)
config.plugins.filecommander.extension = ConfigSelection(default="^.*", choices=[("^.*", _("without")), ("myfilter", _("My Extension")), (records, _("Records")), (movie, _("Movie")), (music, _("Music")), (pictures, _("Pictures"))])
config.plugins.filecommander.input_length = ConfigInteger(default=40, limits=(1, 100))
config.plugins.filecommander.diashow = ConfigInteger(default=5000, limits=(1000, 10000))
config.plugins.filecommander.fake_entry = NoSave(ConfigNothing())

config.plugins.filecommander.path_left_tmp = ConfigText(default=config.plugins.filecommander.path_left.value)
config.plugins.filecommander.path_right_tmp = ConfigText(default=config.plugins.filecommander.path_right.value)
config.plugins.filecommander.path_left_selected = ConfigYesNo(default=True)

# ####################
# ## Config Screen ###
# ####################
class FileCommanderConfigScreen(Screen, ConfigListScreen):
	skin = """
		<screen position="40,80" size="1200,600" title="" >
			<widget name="config" position="10,10" size="700,300" scrollbarMode="showOnDemand"/>
			<widget name="help" position="10,310" size="700,280" font="Regular;20" foregroundColor="#00fff000"/>
			<widget name="key_red" position="100,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_green" position="395,570" size="260,25"  transparent="1" font="Regular;20"/>
			<ePixmap position="70,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_red.png" transparent="1" alphatest="on"/>
			<ePixmap position="365,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_green.png" transparent="1" alphatest="on"/>
			<ePixmap position="660,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_yellow.png" transparent="1" alphatest="on"/>
			<ePixmap position="955,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_blue.png" transparent="1" alphatest="on"/>
		</screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.list = []
		# self.list.append(getConfigListEntry(_("Add plugin to Mainmenu"), config.plugins.filecommander.add_mainmenu_entry))
		# self.list.append(getConfigListEntry(_("Add plugin to Extensionmenu"), config.plugins.filecommander.add_extensionmenu_entry))
		self.list.append(getConfigListEntry(_("Save left folder on exit (%s)") % config.plugins.filecommander.path_left_tmp.value, config.plugins.filecommander.savedir_left))
		self.list.append(getConfigListEntry(_("Save right folder on exit (%s)") % config.plugins.filecommander.path_right_tmp.value, config.plugins.filecommander.savedir_right))
		self.get_folder = getConfigListEntry(_("Default folder"), config.plugins.filecommander.path_default)
		self.list.append(self.get_folder)
		self.list.append(getConfigListEntry(_("My extension"), config.plugins.filecommander.my_extension))
		self.list.append(getConfigListEntry(_("Filter extension, (*) appears in title"), config.plugins.filecommander.extension))
		self.list.append(getConfigListEntry(_("Input length - Filename"), config.plugins.filecommander.input_length))
		self.list.append(getConfigListEntry(_("Time for Slideshow"), config.plugins.filecommander.diashow))

		ConfigListScreen.__init__(self, self.list)
		# self["help"] = Label(_("Help:\nKey [0] refresh screen. Key [1] new folder.\nKey [2] new symlink with name. Key [3] new symlink with foldername.\nKey [4] CHMOD 644/755.\nKey [5] Change to default folder. Key [EPG] shows tasklist. Check copy/move progress in extensions menu.\nKey [R] Select multiple files."))
		self["help"] = Label(_("Help:\nKey [0] Refresh screen.\nKey [1] New folder.\nKey [2] New symlink with file name.\nKey [3] New symlink with foldername.\nKey [4] Change permissions: chmod 644/755.\nKey [5] Change to default folder.\nKey [INFO] Shows tasklist. Check progress of copy/move operations.\nKey [MEDIA] Select multiple files.\nKey [OK] Play movie and music, show pictures, view/edit files, install/extract files, run scripts."))
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Save"))
		self["setupActions"] = ActionMap(["SetupActions"], {
			"green": self.save,
			"red": self.cancel,
			"save": self.save,
			"cancel": self.cancel,
			"ok": self.ok,
		}, -2)
		self.onLayoutFinish.append(self.onLayout)

	def onLayout(self):
		self.setTitle(pname + " " + _("Settings"))

	def ok(self):
		if self["config"].getCurrent() == self.get_folder:
			self.session.openWithCallback(self.pathSelected, MovieLocationBox, _("Default Folder"), config.plugins.filecommander.path_default.value, minFree=100)

	def pathSelected(self, res):
		if res is not None:
			config.plugins.filecommander.path_default.value = res

	def save(self):
		print "[FileCommander] Settings saved"
		for x in self["config"].list:
			x[1].save()
		self.close(True)

	def cancel(self):
		print "[FileCommander] Settings canceled"
		for x in self["config"].list:
			x[1].cancel()
		self.close(False)

###################
# ## Main Screen ###
###################
class FileCommanderScreen(Screen, key_actions):
	skin = """
		<screen position="40,80" size="1200,600" title="" >
			<widget name="list_left_head" position="10,10" size="570,65" font="Regular;20" foregroundColor="#00fff000"/>
			<widget name="list_right_head" position="595,10" size="570,65" font="Regular;20" foregroundColor="#00fff000"/>
			<widget name="list_left" position="10,85" size="570,470" scrollbarMode="showOnDemand"/>
			<widget name="list_right" position="595,85" size="570,470" scrollbarMode="showOnDemand"/>
			<widget name="key_red" position="100,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_green" position="395,570" size="260,25"  transparent="1" font="Regular;20"/>
			<widget name="key_yellow" position="690,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_blue" position="985,570" size="260,25" transparent="1" font="Regular;20"/>
			<ePixmap position="70,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_red.png" transparent="1" alphatest="on"/>
			<ePixmap position="365,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_green.png" transparent="1" alphatest="on"/>
			<ePixmap position="660,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_yellow.png" transparent="1" alphatest="on"/>
			<ePixmap position="955,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_blue.png" transparent="1" alphatest="on"/>
		</screen>"""

	def __init__(self, session, path_left=None):
		if path_left is None:
			if os_path_isdir(config.plugins.filecommander.path_left.value) and config.plugins.filecommander.savedir_left:
				path_left = config.plugins.filecommander.path_left.value
			else:
				path_left = config.plugins.filecommander.path_default.value

		if os_path_isdir(config.plugins.filecommander.path_right.value) and config.plugins.filecommander.savedir_right:
			path_right = config.plugins.filecommander.path_right.value
		else:
			path_right = config.plugins.filecommander.path_default.value

		if os_path_isdir(path_left) and path_left[-1] != "/":
			path_left += "/"

		if os_path_isdir(path_right) and path_right[-1] != "/":
			path_right += "/"

		self.session = session
		Screen.__init__(self, session)

		# set filter
		if config.plugins.filecommander.extension.value == "myfilter":
			filter = "^.*\.%s" % config.plugins.filecommander.my_extension.value
		else:
			filter = config.plugins.filecommander.extension.value

		# set current folder
		self["list_left_head"] = Label(path_left)
		self["list_right_head"] = Label(path_right)
		self["list_left"] = FileList(path_left, matchingPattern=filter)
		self["list_right"] = FileList(path_right, matchingPattern=filter)

		self["key_red"] = Label(_("Delete"))
		self["key_green"] = Label(_("Move"))
		self["key_yellow"] = Label(_("Copy"))
		self["key_blue"] = Label(_("Rename"))
		self["VKeyIcon"] = Pixmap()
		self["VKeyIcon"].hide()

		self["actions"] = ActionMap(["ChannelSelectBaseActions", "WizardActions", "DirectionActions", "MenuActions", "NumberActions", "ColorActions", "TimerEditActions", "InfobarActions", "InfobarTeletextActions", "InfobarSubtitleSelectionActions"], {
			"ok": self.ok,
			"back": self.exit,
			"menu": self.goMenu,
			"nextMarker": self.listRight,
			"prevMarker": self.listLeft,
			"nextBouquet": self.listRight,
			"prevBouquet": self.listLeft,
			"1": self.gomakeDir,
			"2": self.gomakeSym,
			"3": self.gomakeSymlink,
			"4": self.call_change_mode,
			"5": self.goDefaultfolder,
			# "8": self.test,
			"startTeletext": self.file_viewer,
			"info": self.openTasklist,
			"up": self.goUp,
			"down": self.goDown,
			"left": self.goLeft,
			"right": self.goRight,
			"red": self.goRed,
			"green": self.goGreen,
			"yellow": self.goYellow,
			"blue": self.goBlue,
			"0": self.doRefresh,
			"showMovies": self.listSelect,
			"subtitleSelection": self.downloadSubtitles,
		}, -1)

		if config.plugins.filecommander.path_left_selected:
			self.onLayoutFinish.append(self.listLeft)
		else:
			self.onLayoutFinish.append(self.listRight)

		self.onLayoutFinish.append(self.onLayout)

	def onLayout(self):
		if config.plugins.filecommander.extension.value == "^.*":
			filtered = ""
		else:
			filtered = "(*)"
		self.setTitle(pname + filtered)

	def viewable_file(self):
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		if (filename is None) or (sourceDir is None):
			return None
		longname = sourceDir + filename
		try:
			xfile = os_stat(longname)
			if (xfile.st_size < 1000000):
				return longname
		except:
			pass
		return None

	def file_viewer(self):
		longname = self.viewable_file()
		if longname is not None:
			self.session.open(vEditor, longname)
			self.onFileActionCB(True)

	def exit(self):
		if self["list_left"].getCurrentDirectory() and config.plugins.filecommander.savedir_left.value:
			config.plugins.filecommander.path_left.value = self["list_left"].getCurrentDirectory()
			config.plugins.filecommander.path_left.save()
		else:
			config.plugins.filecommander.path_left.value = config.plugins.filecommander.path_default.value

		if self["list_right"].getCurrentDirectory() and config.plugins.filecommander.savedir_right.value:
			config.plugins.filecommander.path_right.value = self["list_right"].getCurrentDirectory()
			config.plugins.filecommander.path_right.save()
		else:
			config.plugins.filecommander.path_right.value = config.plugins.filecommander.path_default.value

		self.close(self.session, True)

	def ok(self):
		if self.SOURCELIST.canDescent():  # isDir
			self.SOURCELIST.descent()
			if self.SOURCELIST == self["list_right"]:
				self["list_left_head"].setText(self.TARGETLIST.getCurrentDirectory())
				self["list_right_head"].setText(self.SOURCELIST.getCurrentDirectory())
			else:
				self["list_left_head"].setText(self.SOURCELIST.getCurrentDirectory())
				self["list_right_head"].setText(self.TARGETLIST.getCurrentDirectory())
			self.updateHead()
		else:
			self.onFileAction(self.SOURCELIST, self.TARGETLIST)
			# self.updateHead()
			self.doRefresh()

	def goMenu(self):
		if self["list_left"].getCurrentDirectory():
			config.plugins.filecommander.path_left_tmp.value = self["list_left"].getCurrentDirectory()
		if self["list_right"].getCurrentDirectory():
			config.plugins.filecommander.path_right_tmp.value = self["list_right"].getCurrentDirectory()
		self.session.openWithCallback(self.goRestart, FileCommanderConfigScreen)

	def goDefaultfolder(self):
		self.SOURCELIST.changeDir(config.plugins.filecommander.path_default.value)
		self["list_left_head"].setText(self["list_left"].getCurrentDirectory())
		self["list_right_head"].setText(self["list_right"].getCurrentDirectory())

	def goRestart(self, answer):
		config.plugins.filecommander.path_left.value = config.plugins.filecommander.path_left_tmp.value
		config.plugins.filecommander.path_right.value = config.plugins.filecommander.path_right_tmp.value
		# self.close(self.session, False)
		self.doRefresh()

	def goLeft(self):
		self.SOURCELIST.pageUp()
		self.updateHead()

	def goRight(self):
		self.SOURCELIST.pageDown()
		self.updateHead()

	def goUp(self):
		self.SOURCELIST.up()
		self.updateHead()

	def goDown(self):
		self.SOURCELIST.down()
		self.updateHead()

# ## Multiselect ###
	def listSelect(self):
		selectedid = self.SOURCELIST.getSelectionID()
		config.plugins.filecommander.path_left_tmp.value = self["list_left"].getCurrentDirectory()
		config.plugins.filecommander.path_right_tmp.value = self["list_right"].getCurrentDirectory()
		if self.SOURCELIST == self["list_left"]:
			leftactive = True
		else:
			leftactive = False

		self.session.openWithCallback(self.doRefreshDir, FileCommanderScreenFileSelect, leftactive, selectedid)
		self.updateHead()

	def openTasklist(self):
		self.tasklist = []
		for job in job_manager.getPendingJobs():
			self.tasklist.append((job, job.name, job.getStatustext(), int(100 * job.progress / float(job.end)), str(100 * job.progress / float(job.end)) + "%"))
		self.session.open(TaskListScreen, self.tasklist)

# ## copy ###
	def goYellow(self):
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		targetDir = self.TARGETLIST.getCurrentDirectory()
		if (filename is None) or (sourceDir is None) or (targetDir is None):
			return
		if sourceDir not in filename:
			copytext = _("Copy file - existing file will be overwritten !")
		else:
			copytext = _("Copy folder - existing folders/files will be overwritten !")
		self.session.openWithCallback(self.doCopy, ChoiceBox, title=copytext + "?\n%s\nfrom\n%s\n%s" % (filename, sourceDir, targetDir), list=[(_("Yes"), True), (_("No"), False)])

	def doCopy(self, result):
		if result is not None:
			if result[1]:
				filename = self.SOURCELIST.getFilename()
				sourceDir = self.SOURCELIST.getCurrentDirectory()
				targetDir = self.TARGETLIST.getCurrentDirectory()
				dst_file = targetDir
				if dst_file.endswith("/"):
					targetDir = dst_file[:-1]
				if sourceDir not in filename:
					job_manager.AddJob(FileTransferJob(sourceDir + filename, targetDir, False, True, "%s : %s" % (_("copy file"), sourceDir + filename)))
					self.doCopyCB()
				else:
					job_manager.AddJob(FileTransferJob(filename, targetDir, True, True, "%s : %s" % (_("copy folder"), filename)))
					self.doCopyCB()

	def doCopyCB(self):
		self.doRefresh()

# ## delete ###
	def goRed(self):
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		if (filename is None) or (sourceDir is None):
			return
		if sourceDir not in filename:
			deltext = _("Delete file")
		else:
			deltext = _("Delete folder")
		self.session.openWithCallback(self.doDelete, ChoiceBox, title=deltext + "?\n%s\nfrom dir\n%s" % (filename, sourceDir), list=[(_("Yes"), True), (_("No"), False)])

	def doDelete(self, result):
		if result is not None:
			if result[1]:
				filename = self.SOURCELIST.getFilename()
				sourceDir = self.SOURCELIST.getCurrentDirectory()
				if sourceDir not in filename:
					self.session.openWithCallback(self.doDeleteCB, Console, title=_("deleting file ..."), cmdlist=["rm \"" + sourceDir + filename + "\""])
				else:
					self.session.openWithCallback(self.doDeleteCB, Console, title=_("deleting folder ..."), cmdlist=["rm -rf \"" + filename + "\""])

	def doDeleteCB(self):
		self.doRefresh()

# ## move ###
	def goGreen(self):
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		targetDir = self.TARGETLIST.getCurrentDirectory()
		if (filename is None) or (sourceDir is None) or (targetDir is None):
			return
		if sourceDir not in filename:
			movetext = _("Move file")
		else:
			movetext = _("Move folder")
		self.session.openWithCallback(self.doMove, ChoiceBox, title=movetext + "?\n%s\nfrom dir\n%s\nto dir\n%s" % (filename, sourceDir, targetDir), list=[(_("Yes"), True), (_("No"), False)])

	def doMove(self, result):
		if result is not None:
			if result[1]:
				filename = self.SOURCELIST.getFilename()
				sourceDir = self.SOURCELIST.getCurrentDirectory()
				targetDir = self.TARGETLIST.getCurrentDirectory()
				dst_file = targetDir
				if dst_file.endswith("/"):
					targetDir = dst_file[:-1]
				if sourceDir not in filename:
					job_manager.AddJob(FileTransferJob(sourceDir + filename, targetDir, False, False, "%s : %s" % (_("move file"), sourceDir + filename)))
					self.doMoveCB()
				else:
					job_manager.AddJob(FileTransferJob(filename, targetDir, True, False, "%s : %s" % (_("move folder"), filename)))
					self.doMoveCB()

	def doMoveCB(self):
		# os.system('echo %s > /tmp/test.log' % ("refresh move"))
		self.doRefresh()

# ## rename ###
	def goBlue(self):
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		length = config.plugins.filecommander.input_length.value
		if (filename is None) or (sourceDir is None):
			return
		self.session.openWithCallback(self.doRename, InputBox, text=filename, visible_width=length, overwrite=False, firstpos_end=True, allmarked=False, title=_("Please enter file/folder name"), windowTitle=_("Rename file"))
		# overwrite : False = insert mode (not overwrite) when InputBox is created
		# firstpos_end : True = cursor at end of text on InputBox creation - False = cursor at start of text on InputBox creation
		# visible_width : if this width is smaller than the skin width, the text will be scrolled if it is too long
		# allmarked : text all selected at InputBox creation or not

	def doRename(self, newname):
		if newname:
			filename = self.SOURCELIST.getFilename()
			sourceDir = self.SOURCELIST.getCurrentDirectory()
			if sourceDir not in filename:
				self.session.openWithCallback(self.doRenameCB, Console, title=_("renaming file ..."), cmdlist=["mv \"" + sourceDir + filename + "\" \"" + sourceDir + newname + "\""])
			else:
				self.session.openWithCallback(self.doRenameCB, Console, title=_("renaming folder ..."), cmdlist=["mv \"" + filename + "\" \"" + newname + "\""])

	def doRenameCB(self):
		self.doRefresh()

# ## symlink by name ###
	def gomakeSym(self):
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		if (filename is None) or (sourceDir is None):
			return
		self.session.openWithCallback(self.doMakesym, InputBox, text="", title=_("Please enter name of the new symlink"), windowTitle=_("New symlink"))

	def doMakesym(self, newname):
		if newname:
			filename = self.SOURCELIST.getFilename()
			sourceDir = self.SOURCELIST.getCurrentDirectory()
			targetDir = self.TARGETLIST.getCurrentDirectory()
			# self.session.openWithCallback(self.doMakesymCB, Console, title=_("create symlink"), cmdlist=["ln -s \"" + sourceDir + "\" \"" + targetDir + newname + "\""])
			symlink(sourceDir, targetDir + newname)
			self.doRefresh()

	def doMakesymCB(self):
		self.doRefresh()

# ## symlink by folder ###
	def gomakeSymlink(self):
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		targetDir = self.TARGETLIST.getCurrentDirectory()
		if sourceDir not in filename:
			movetext = _("Create symlink to file")
		else:
			movetext = _("Symlink to ")
		testfile = filename[:-1]
		test = path.islink(testfile)
		if (filename is None) or (sourceDir is None):
			return
		if path.islink(testfile):
			return
		self.session.openWithCallback(self.domakeSymlink, ChoiceBox, title=movetext + " %s in %s" % (filename, targetDir), list=[(_("Yes"), True), (_("No"), False)])

	def domakeSymlink(self, result):
		if result is not None:
			if result[1]:
				filename = self.SOURCELIST.getFilename()
				sourceDir = self.SOURCELIST.getCurrentDirectory()
				targetDir = self.TARGETLIST.getCurrentDirectory()
				if sourceDir not in filename:
					return
					self.session.openWithCallback(self.doRenameCB, Console, title=_("renaming file ..."), cmdlist=["mv \"" + sourceDir + filename + "\" \"" + sourceDir + newname + "\""])
					symlink(sourceDir, targetDir + newname)
				else:
					self.session.openWithCallback(self.doRenameCB, Console, title=_("renaming folder ..."), cmdlist=["ln -s \"" + filename + "\" \"" + targetDir + "\""])

		self.doRefresh()

# ## new folder ###
	def gomakeDir(self):
		filename = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		if (filename is None) or (sourceDir is None):
			return
		self.session.openWithCallback(self.doMakedir, InputBox, text="", title=_("Please enter name of the new directory"), windowTitle=_("New folder"))

	def doMakedir(self, newname):
		if newname:
			filename = self.SOURCELIST.getFilename()
			sourceDir = self.SOURCELIST.getCurrentDirectory()
			# self.session.openWithCallback(self.doMakedirCB, Console, title = _("create folder"), cmdlist=["mkdir \"" + sourceDir + newname + "\""])
			os.mkdir(sourceDir + newname)
			self.doRefresh()

	def doMakedirCB(self):
		self.doRefresh()

# ## download subtitles ###
	def downloadSubtitles(self):
		testFileName = self.SOURCELIST.getFilename()
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		subFile = sourceDir + testFileName
		fps = 0
		if (testFileName.endswith(".mpg")) or (testFileName.endswith(".mpeg")) or (testFileName.endswith(".mkv")) or (testFileName.endswith(".m2ts")) or (testFileName.endswith(".vob")) or (testFileName.endswith(".mod")) or (testFileName.endswith(".avi")) or (testFileName.endswith(".mp4")) or (testFileName.endswith(".divx")) or (testFileName.endswith(".mkv")) or (testFileName.endswith(".wmv")) or (testFileName.endswith(".mov")) or (testFileName.endswith(".flv")) or (testFileName.endswith(".3gp")):
			print "[FileCommander] Downloading subtitle for: ", subFile
			# For Future USE

	def subCallback(self, answer=False):
		self.doRefresh()

# ## basic functions ###
	def updateHead(self):
		text_target = self.Info(self.TARGETLIST)
		text_source = self.Info(self.SOURCELIST)
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		targetDir = self.TARGETLIST.getCurrentDirectory()
		if self.SOURCELIST == self["list_right"]:
			if targetDir is not None:
				self["list_left_head"].setText(self.TARGETLIST.getCurrentDirectory() + text_target)
			if sourceDir is not None:
				self["list_right_head"].setText(self.SOURCELIST.getCurrentDirectory() + text_source)
		else:
			if sourceDir is not None:
				self["list_left_head"].setText(self.SOURCELIST.getCurrentDirectory() + text_source)
			if targetDir is not None:
				self["list_right_head"].setText(self.TARGETLIST.getCurrentDirectory() + text_target)
		self["VKeyIcon"].setVisible(self.viewable_file() is not None)

	def doRefreshDir(self):
		self["list_left"].changeDir(config.plugins.filecommander.path_left_tmp.value)
		self["list_right"].changeDir(config.plugins.filecommander.path_right_tmp.value)
		if self.SOURCELIST == self["list_left"]:
			self["list_left"].selectionEnabled(1)
			self["list_right"].selectionEnabled(0)
		else:
			self["list_left"].selectionEnabled(0)
			self["list_right"].selectionEnabled(1)
		self.updateHead()

	def doRefresh(self):
		self.SOURCELIST.refresh()
		self.TARGETLIST.refresh()
		self.updateHead()

	def listRight(self):
		self["list_left"].selectionEnabled(0)
		self["list_right"].selectionEnabled(1)
		self.SOURCELIST = self["list_right"]
		self.TARGETLIST = self["list_left"]
		self.updateHead()

	def listLeft(self):
		self["list_left"].selectionEnabled(1)
		self["list_right"].selectionEnabled(0)
		self.SOURCELIST = self["list_left"]
		self.TARGETLIST = self["list_right"]
		self.updateHead()

	def call_change_mode(self):
		self.change_mod(self.SOURCELIST)

# 	def call_onFileAction(self):
# 		self.onFileAction(self.SOURCELIST, self.TARGETLIST)

#####################
# ## Select Screen ###
#####################
class FileCommanderScreenFileSelect(Screen, key_actions):
	skin = """
		<screen position="40,80" size="1200,600" title="" >
			<widget name="list_left_head" position="10,10" size="570,65" font="Regular;20" foregroundColor="#00fff000"/>
			<widget name="list_right_head" position="595,10" size="570,65" font="Regular;20" foregroundColor="#00fff000"/>
			<widget name="list_left" position="10,85" size="570,470" scrollbarMode="showOnDemand"/>
			<widget name="list_right" position="595,85" size="570,470" scrollbarMode="showOnDemand"/>
			<widget name="key_red" position="100,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_green" position="395,570" size="260,25"  transparent="1" font="Regular;20"/>
			<widget name="key_yellow" position="690,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_blue" position="985,570" size="260,25" transparent="1" font="Regular;20"/>
			<ePixmap position="70,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_red.png" transparent="1" alphatest="on"/>
			<ePixmap position="365,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_green.png" transparent="1" alphatest="on"/>
			<ePixmap position="660,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_yellow.png" transparent="1" alphatest="on"/>
			<ePixmap position="955,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_blue.png" transparent="1" alphatest="on"/>
		</screen>"""

	def __init__(self, session, leftactive, selectedid):
		Screen.__init__(self, session)

		self.selectedFiles = []
		self.selectedid = selectedid

		path_left = config.plugins.filecommander.path_left_tmp.value
		path_right = config.plugins.filecommander.path_right_tmp.value

		# set filter
		if config.plugins.filecommander.extension.value == "myfilter":
			filter = "^.*\.%s" % config.plugins.filecommander.my_extension.value
		else:
			filter = config.plugins.filecommander.extension.value

		# set current folder
		self["list_left_head"] = Label(path_left)
		self["list_right_head"] = Label(path_right)

		if leftactive:
			self["list_left"] = MultiFileSelectList(self.selectedFiles, path_left, matchingPattern=filter)
			self["list_right"] = FileList(path_right, matchingPattern=filter)
			self.SOURCELIST = self["list_left"]
			self.TARGETLIST = self["list_right"]
			self.listLeft()
		else:
			self["list_left"] = FileList(path_left, matchingPattern=filter)
			self["list_right"] = MultiFileSelectList(self.selectedFiles, path_right, matchingPattern=filter)
			self.SOURCELIST = self["list_right"]
			self.TARGETLIST = self["list_left"]
			self.listRight()

		self["key_red"] = Label(_("Delete"))
		self["key_green"] = Label(_("Move"))
		self["key_yellow"] = Label(_("Copy"))
		self["key_blue"] = Label(_("Skip selection"))

		self["actions"] = ActionMap(["ChannelSelectBaseActions", "WizardActions", "DirectionActions", "MenuActions", "NumberActions", "ColorActions", "TimerEditActions", "InfobarActions"], {
			"ok": self.ok,
			"back": self.exit,
			# "menu": self.goMenu,
			"nextMarker": self.listRight,
			"prevMarker": self.listLeft,
			"nextBouquet": self.listRight,
			"prevBouquet": self.listLeft,
			"info": self.openTasklist,
			"up": self.goUp,
			"down": self.goDown,
			"left": self.goLeft,
			"right": self.goRight,
			"red": self.goRed,
			"green": self.goGreen,
			"yellow": self.goYellow,
			"blue": self.goBlue,
			"0": self.doRefresh,
			"showMovies": self.changeSelectionState,
		}, -1)
		self.onLayoutFinish.append(self.onLayout)

	def onLayout(self):
		if config.plugins.filecommander.extension.value == "^.*":
			filtered = ""
		else:
			filtered = "(*)"
		self.setTitle(pname + filtered + _("(Selectmode)"))
		self.SOURCELIST.moveToIndex(self.selectedid)
		self.updateHead()

	def changeSelectionState(self):
		if self.ACTIVELIST == self.SOURCELIST:
			self.ACTIVELIST.changeSelectionState()
			self.selectedFiles = self.ACTIVELIST.getSelectedList()
			print "[FileCommander] selectedFiles:", self.selectedFiles
			self.goDown()

	def exit(self):
		config.plugins.filecommander.path_left_tmp.value = self["list_left"].getCurrentDirectory()
		config.plugins.filecommander.path_right_tmp.value = self["list_right"].getCurrentDirectory()
		self.close()

	def ok(self):

		if self.ACTIVELIST == self.SOURCELIST:
			self.changeSelectionState()
		else:
			if self.ACTIVELIST.canDescent():  # isDir
				self.ACTIVELIST.descent()
			if self.ACTIVELIST == self["list_right"]:
				self["list_left_head"].setText(self.TARGETLIST.getCurrentDirectory())
				self["list_right_head"].setText(self.SOURCELIST.getCurrentDirectory())
			else:
				self["list_left_head"].setText(self.SOURCELIST.getCurrentDirectory())
				self["list_right_head"].setText(self.TARGETLIST.getCurrentDirectory())

	def goMenu(self):
		self.session.open(FileCommanderConfigScreen)

	def goLeft(self):
		self.ACTIVELIST.pageUp()
		self.updateHead()

	def goRight(self):
		self.ACTIVELIST.pageDown()
		self.updateHead()

	def goUp(self):
		self.ACTIVELIST.up()
		self.updateHead()

	def goDown(self):
		self.ACTIVELIST.down()
		self.updateHead()

	def openTasklist(self):
		self.tasklist = []
		for job in job_manager.getPendingJobs():
			self.tasklist.append((job, job.name, job.getStatustext(), int(100 * job.progress / float(job.end)), str(100 * job.progress / float(job.end)) + "%"))
		self.session.open(TaskListScreen, self.tasklist)

# ## delete select ###
	def goRed(self):
		for file in self.selectedFiles:
			if os_path_isdir(file):
				container = eConsoleAppContainer()
				container.execute("rm -rf '%s'" % file)
			else:
				remove(file)
		self.exit()

# ## move select ###
	def goGreen(self):
		targetDir = self.TARGETLIST.getCurrentDirectory()

		for file in self.selectedFiles:
			extension = file.split('.')
			extension = extension[-1].lower()
			if extension in MOVIEEXTENSIONS:
				print "[FileCommander] skip " + extension
			else:
				print "[FileCommander] copy " + extension
				dst_file = targetDir
				if dst_file.endswith("/"):
					targetDir = dst_file[:-1]
				job_manager.AddJob(FileTransferJob(file, targetDir, False, False, "%s : %s" % (_("move file"), file)))
		self.exit()

# ## copy select ###
	def goYellow(self):
		targetDir = self.TARGETLIST.getCurrentDirectory()

		for file in self.selectedFiles:
			extension = file.split('.')
			extension = extension[-1].lower()
			if extension in MOVIEEXTENSIONS:
				print "[FileCommander] skip " + extension
			else:
				print "[FileCommander] copy " + extension
				dst_file = targetDir
				if dst_file.endswith("/"):
					targetDir = dst_file[:-1]
				if file.endswith("/"):
					job_manager.AddJob(FileTransferJob(file, targetDir, True, True, "%s : %s" % (_("copy folder"), file)))
				else:
					job_manager.AddJob(FileTransferJob(file, targetDir, False, True, "%s : %s" % (_("copy file"), file)))
		self.exit()

	def goBlue(self):
		self.exit()

# ## basic functions ###
	def updateHead(self):
		text_target = self.Info(self.TARGETLIST)
		text_source = self.Info(self.SOURCELIST)
		sourceDir = self.SOURCELIST.getCurrentDirectory()
		targetDir = self.TARGETLIST.getCurrentDirectory()
		if self.SOURCELIST == self["list_right"]:
			if targetDir is not None:
				self["list_left_head"].setText(self.TARGETLIST.getCurrentDirectory() + text_target)
			if sourceDir is not None:
				self["list_right_head"].setText(self.SOURCELIST.getCurrentDirectory() + text_source)
		else:
			if sourceDir is not None:
				self["list_left_head"].setText(self.SOURCELIST.getCurrentDirectory() + text_source)
			if targetDir is not None:
				self["list_right_head"].setText(self.TARGETLIST.getCurrentDirectory() + text_target)

	def doRefresh(self):
		print "[FileCommander] selectedFiles:", self.selectedFiles
		self.SOURCELIST.refresh()
		self.TARGETLIST.refresh()
		self.updateHead()

	def listRight(self):
		self["list_left"].selectionEnabled(0)
		self["list_right"].selectionEnabled(1)
		self.ACTIVELIST = self["list_right"]
		self.updateHead()

	def listLeft(self):
		self["list_left"].selectionEnabled(1)
		self["list_right"].selectionEnabled(0)
		self.ACTIVELIST = self["list_left"]
		self.updateHead()

# #####################
# ## Start routines ###
# #####################
def filescan_open(list, session, **kwargs):
	path = "/".join(list[0].path.split("/")[:-1]) + "/"
	session.open(FileCommanderScreen, path_left=path)

def start_from_filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	return \
		Scanner(
			mimetypes=None,
			paths_to_scan=[
				ScanPath(path="", with_subdirs=False),
			],
			name=pname,
			description=_("Open with File Commander"),
			openfnc=filescan_open,
		)

def start_from_mainmenu(menuid, **kwargs):
	# starting from main menu
	if menuid == "mainmenu":
		return [(pname, start_from_pluginmenu, "filecommand", 1)]
	return []

def start_from_pluginmenu(session, **kwargs):
	session.openWithCallback(exit, FileCommanderScreen)

def exit(session, result):
	if not result:
		session.openWithCallback(exit, FileCommanderScreen)

def Plugins(path, **kwargs):
	desc_mainmenu = PluginDescriptor(name=pname, description=pdesc, where=PluginDescriptor.WHERE_MENU, fnc=start_from_mainmenu)
	# desc_pluginmenu = PluginDescriptor(name=pname, description=pdesc,  where=PluginDescriptor.WHERE_PLUGINMENU, fnc=start_from_pluginmenu)
	desc_extensionmenu = PluginDescriptor(name=pname, description=pdesc, where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=start_from_pluginmenu)
	desc_filescan = PluginDescriptor(name=pname, where=PluginDescriptor.WHERE_FILESCAN, fnc=start_from_filescan)
	list = []
	# list.append(desc_pluginmenu)
####
# 	buggy
# 	list.append(desc_filescan)
####
	if config.plugins.filecommander.add_extensionmenu_entry.value:
		list.append(desc_extensionmenu)
	if config.plugins.filecommander.add_mainmenu_entry.value:
		list.append(desc_mainmenu)
	return list
