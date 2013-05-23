# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.InfoBar import MoviePlayer
from Screens.Console import Console
from Screens.ChoiceBox import ChoiceBox
from Screens.InputBox import InputBox
from Screens.MessageBox import MessageBox

from Components.ActionMap import ActionMap
from Components.config import config, ConfigSubList, ConfigSubsection, ConfigInteger, ConfigYesNo, ConfigText, getConfigListEntry, ConfigSelection
from Components.ConfigList import *
from Components.FileList import FileList
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.Pixmap import Pixmap
from Components.AVSwitch import AVSwitch
from Components.Scanner import openFile
from Components.ServiceEventTracker import ServiceEventTracker
from enigma import eConsoleAppContainer, eServiceReference, eTimer, ePicLoad, getDesktop, iPlayableService

from Tools.Directories import fileExists, pathExists
from Tools.HardwareInfo import HardwareInfo
from ServiceReference import ServiceReference

from os import system as os_system
from os import stat as os_stat
from os import walk as os_walk
from os.path import isdir as os_path_isdir
from mimetypes import guess_type
from random import randint

if fileExists("/usr/lib/enigma2/python/Plugins/Extensions/PicturePlayer/plugin.pyo") or fileExists("/usr/lib/enigma2/python/Plugins/Extensions/PicturePlayer/plugin.pyc"):
	from Plugins.Extensions.PicturePlayer.plugin import Pic_Thumb, picshow
	PicPlayerAviable = True
else:
	PicPlayerAviable = False
if fileExists("/usr/lib/enigma2/python/Plugins/Extensions/DVDPlayer/plugin.pyo") or fileExists("/usr/lib/enigma2/python/Plugins/Extensions/DVDPlayer/plugin.pyc"):
	from Plugins.Extensions.DVDPlayer.plugin import DVDPlayer
	DVDPlayerAviable = True
else:
	DVDPlayerAviable = False
	
pname = _("File Manager")
pdesc = _("manage local Files")

config.plugins.filemanager = ConfigSubsection()
config.plugins.filemanager.savedirs = ConfigYesNo(default = True)
config.plugins.filemanager.media_filter = ConfigYesNo(default=False)
config.plugins.filemanager.hidden_filter = ConfigYesNo(default = True)
config.plugins.filemanager.pic_filter = ConfigYesNo(default=False)
config.plugins.filemanager.path_left = ConfigText(default = "/")
config.plugins.filemanager.path_right = ConfigText(default = "/")
config.plugins.filemanager.symlink_name = ConfigText(default = "/")
config.plugins.filemanager.symlink_path = ConfigText(default = "/")
config.plugins.filemanager.sort_by = ConfigSelection(choices={ 'date': _('Date'), 'name': _('Name')}, default='name')
config.plugins.filemanager.exit_eop = ConfigSelection(choices={ 'Yes': _('Yes'), 'No': _('No'), 'Ask': _('Ask User')}, default='Yes')
config.plugins.filemanager.sub_lang = ConfigSelection(choices={ 'PL': _('Polish'), 'ENG': _('English')}, default='PL')

FileManagerConfig_Skin ="""
        		<screen name="FileManagerConfig" position="center,center" size="650,400" title="File Manager - Configuration" >
            			<widget name="config" position="0,0" size="640,360" scrollbarMode="showOnDemand" />
            			<widget name="key_red" position="120,360" size="100,40" zPosition="1"  transparent="1" foregroundColor="white" font="Regular;18"/>
            			<widget name="key_green" position="380,360" size="100,40" zPosition="1"  transparent="1" foregroundColor="white" font="Regular;18"/>
            			<ePixmap position="100,358" size="100,40" zPosition="0" pixmap="skin_default/buttons/button_red.png" transparent="1" alphatest="on"/>
            			<ePixmap position="360,358" size="100,40" zPosition="0" pixmap="skin_default/buttons/button_green.png" transparent="1" alphatest="on"/>
        		</screen>"""

FileManager_Skin = """
        		<screen name="FileManager" position="center,center" size="935,590" title="File Manager">
				<widget name="list_left_text" font="Regular;20" position="60,0" size="150,30"/>
				<widget name="list_right_text" font="Regular;20" position="575,0" size="150,30"/>
            			<widget name="list_left" position="0,30" size="460,480" scrollbarMode="showOnDemand" />
            			<widget name="list_right" position="465,30" size="460,480" scrollbarMode="showOnDemand" />
            			<ePixmap position="20,545" size="80,80" zPosition="1" pixmap="skin_default/buttons/button_red.png" transparent="1" alphatest="blend" />
            			<widget name="key_red" zPosition="4" position="50,545" size="140,40" halign="left" valign="top" font="Regular;22" transparent="1" />
            			<ePixmap position="160,545" size="80,80" zPosition="1" pixmap="skin_default/buttons/button_green.png" transparent="1" alphatest="blend" />
				<widget name="key_green" zPosition="4" position="190,545" size="140,40" halign="left" valign="top" font="Regular;22" transparent="1" />
				<ePixmap position="320,545" size="80,80" zPosition="1" pixmap="skin_default/buttons/button_yellow.png" transparent="1" alphatest="blend" />
				<widget name="key_yellow" zPosition="4" position="350,545" size="140,40" halign="left" valign="top" font="Regular;22" transparent="1" />
				<ePixmap position="470,545" size="80,80" zPosition="1" pixmap="skin_default/buttons/button_blue.png" transparent="1" alphatest="blend" />
				<widget name="key_blue" zPosition="4" position="500,545" size="240,40" halign="left" valign="top" font="Regular;22" transparent="1"  />
				<ePixmap position="740,545" size="80,80" zPosition="1" pixmap="skin_default/buttons/key_menu.png" transparent="1" alphatest="blend" />
				<widget name="settings_text" zPosition="4" position="790,545" size="240,40" halign="left" valign="top" font="Regular;22" transparent="1" />
        		</screen>"""

FileManager_InfoMenu_Skin = """
           		<screen name="FileManager_InfoMenu" position="center,center" size="450,260" title="File Manager - More Options" >
           			<widget name="menu" position="10,10" size="440,250" scrollbarMode="showOnDemand" />
           		</screen>"""
           		
FileViewer_Skin = """
        		<screen position="center,center" size="650,500" title="File Manager - Viewer" >
            			<widget name="filedata" position="0,0" size="650,460" font="Regular;16" zPosition="9" transparent="1" />
            			<widget name="status" position="10,360" size="600,40" valign="center" halign="center" zPosition="1"  transparent="1" foregroundColor="white" font="Regular;18"/>
        		</screen>"""

ConsoleView_Skin = """
			<screen name="ConsoleView" position="center,center" size="620,476" title="File Manager - Console" >
            			<widget name="text" position="0,0" size="650,460" font="Regular;16" zPosition="9" transparent="1" />
            			<widget name="status" position="10,460" size="600,40" valign="center" halign="center" zPosition="1"  transparent="1" foregroundColor="white" font="Regular;18"/>
       		  	</screen>"""

PicViewer_Skin="""
			<screen name="PicViewer" flags="wfNoBorder" position="0,0" size="1280,720" title="PicViewer" backgroundColor="#00121214">
					<widget name="Picture" position="0,0" size="1280,720" zPosition="1" alphatest="on" />
			</screen>"""
			
FileManager_symlink_create_Skin = """
        		<screen name="FileManager_symlink_create" position="center,center" size="550,400" title="File Manager - New Symlink" >
            			<widget name="config" position="0,0" size="550,360" scrollbarMode="showOnDemand" />
            			<widget name="key_green" position="120,360" size="100,40" valign="center" halign="center" zPosition="1"  transparent="1" foregroundColor="white" font="Regular;18"/>
            			<ePixmap position="120,360" size="100,40" zPosition="0" pixmap="skin_default/buttons/button_green.png" transparent="1" alphatest="on"/>
        		</screen>"""
			
FileManager_file_permision_Skin = """
        		<screen name="FileManager_file_permision" position="center,center" size="550,400" title="File Manager - File permission settings" >
            			<widget name="config" position="0,0" size="550,360" scrollbarMode="showOnDemand" />
            			<widget name="key_green" position="120,360" size="100,40" valign="center" halign="center" zPosition="1"  transparent="1" foregroundColor="white" font="Regular;18"/>
            			<ePixmap position="120,360" size="100,40" zPosition="0" pixmap="skin_default/buttons/button_green.png" transparent="1" alphatest="on"/>
        		</screen>"""
        		
        		
##################################
class FileManagerConfig(ConfigListScreen,Screen):
    def __init__(self, session):
        self.session = session
        Screen.__init__(self, session)
        self.skinName = ["Setup"]
        self.list = []
        self.list.append(getConfigListEntry(_("Save Filesystemposition on exit"), config.plugins.filemanager.savedirs))
        self.list.append(getConfigListEntry(_("Filesystemposition list left"), config.plugins.filemanager.path_left))
        self.list.append(getConfigListEntry(_("Filesystemposition list right"), config.plugins.filemanager.path_right))
	self.list.append(getConfigListEntry(_("Enable only media filter ?"), config.plugins.filemanager.media_filter))
	self.list.append(getConfigListEntry(_("Show table with all pictures ?"), config.plugins.filemanager.pic_filter))
	self.list.append(getConfigListEntry(_("Show hidden files ?"), config.plugins.filemanager.hidden_filter))
	self.list.append(getConfigListEntry(_("Sort files by"), config.plugins.filemanager.sort_by))
	self.list.append(getConfigListEntry(_("Exit mediaplayer on the end of file ?"), config.plugins.filemanager.exit_eop))
	self.list.append(getConfigListEntry(_("Subtitles downloader language"), config.plugins.filemanager.sub_lang))

        ConfigListScreen.__init__(self, self.list)
        self["key_red"] = Label(_("Save"))
        self["key_green"] = Label(_("Cancel"))
        self["setupActions"] = ActionMap(["SetupActions", "OkCancelActions","WizardActions"],
        {
            "green": self.cancel,
            "red": self.save,
            "save": self.save,
            "cancel": self.cancel,
            "ok": self.save,
        }, -2)
        self.onLayoutFinish.append(self.onLayout)

    def onLayout(self):
        self.setTitle(_("File Manager - Settings"))

    def save(self):
	sub_file = open('/etc/egami/.sub_lang', 'w')
	sub_file.write(config.plugins.filemanager.sub_lang.value)
	sub_file.close()
        for x in self["config"].list:
            x[1].save()
        self.close(True)

    def cancel(self):
        for x in self["config"].list:
            x[1].cancel()
        self.close(False)

##################################################################################################################################################################################

from re import compile as re_compile
from os import path as os_path, listdir
from Components.MenuList import MenuList
from Components.Harddisk import harddiskmanager
from Components.config import config
from enigma import RT_HALIGN_LEFT, eListboxPythonMultiContent, eServiceReference, eServiceCenter, gFont, iServiceInformation
from Tools.LoadPixmap import LoadPixmap



EXTENSIONS = {
		"m4a": "ext_music",
		"mp2": "ext_music",
		"mp3": "ext_music",
		"wav": "ext_music",
		"ogg": "ext_music",
		"flac": "ext_music",
		"jpg": "ext_picture",
		"jpeg": "ext_picture",
		"jpe": "ext_picture",
		"png": "ext_picture",
		"bmp": "ext_picture",
		"mvi": "ext_picture",
		"ts": "ext_movie",
		"m2ts": "ext_movie",
		"avi": "ext_movie",
		"divx": "ext_movie",
		"mpg": "ext_movie",
		"mpeg": "ext_movie",
		"mkv": "ext_movie",
		"mp4": "ext_movie",
		"mov": "ext_movie",
		"mts": "ext_movie",
		"vob": "ext_movie",
		"ifo": "ext_movie",
		"iso": "ext_iso",
		"ipk": "ext_package",
		"gz": "ext_package",
		"bz2": "ext_package",
		"sh": "ext_shellscript",
		"py" : "ext_pythonscript",
		"txt" : "ext_text",
		"log" : "ext_text",
		"img" : "ext_iso",
		"ird" : "ext_iso"
	}



def FileEntryComponent(name, absolute = None, isDir = False):
	res = [ (absolute, isDir) ]
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 40, 2, 1000, 22, 0, RT_HALIGN_LEFT, name))
	if isDir:
		png = LoadPixmap("/usr/share/enigma2/easy-skin-hd/extensions/ext_dir.png")
	else:
		extension = name.split('.')
		extension = extension[-1].lower()
		if EXTENSIONS.has_key(extension):
			png = LoadPixmap("/usr/share/enigma2/easy-skin-hd/extensions/" + EXTENSIONS[extension] + ".png")
		else:
			png = LoadPixmap("/usr/share/enigma2/easy-skin-hd/extensions/ext_unknown.png")
	if png is not None:
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 12, 3, 20, 20, png))
	return res



class FileList(MenuList):
	def __init__(self, directory, showDirectories = True, showFiles = True, showMountpoints = True, matchingPattern = None, useServiceRef = False, inhibitDirs = False, inhibitMounts = False, isTop = False, enableWrapAround = True, additionalExtensions = None):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.additional_extensions = additionalExtensions
		self.mountpoints = []
		self.current_directory = None
		self.current_mountpoint = None
		self.useServiceRef = useServiceRef
		self.showDirectories = showDirectories
		self.showMountpoints = showMountpoints
		self.showFiles = showFiles
		self.isTop = isTop
		self.matchingPattern = matchingPattern
		self.inhibitDirs = inhibitDirs or []
		self.inhibitMounts = inhibitMounts or []
		self.refreshMountpoints()
		self.changeDir(directory)
		self.l.setFont(0, gFont("Regular", 18))
		self.l.setItemHeight(26)
		self.serviceHandler = eServiceCenter.getInstance()

	def refreshMountpoints(self):
		self.mountpoints = [os_path.join(p.mountpoint, "") for p in harddiskmanager.getMountedPartitions()]
		self.mountpoints.sort(reverse = True)

	def getMountpoint(self, file):
		file = os_path.join(os_path.realpath(file), "")
		for m in self.mountpoints:
			if file.startswith(m):
				return m
		return False

	def getMountpointLink(self, file):
		if os_path.realpath(file) == file:
			return self.getMountpoint(file)
		else:
			if file[-1] == "/":
				file = file[:-1]
			mp = self.getMountpoint(file)
			last = file
			file = os_path.dirname(file)
			while last != "/" and mp == self.getMountpoint(file):
				last = file
				file = os_path.dirname(file)
			return os_path.join(last, "")

	def getSelection(self):
		if self.l.getCurrentSelection() is None:
			return None
		return self.l.getCurrentSelection()[0]

	def getCurrentEvent(self):
		l = self.l.getCurrentSelection()
		if not l or l[0][1] == True:
			return None
		else:
			return self.serviceHandler.info(l[0][0]).getEvent(l[0][0])

	def getFileList(self):
		return self.list

	def inParentDirs(self, dir, parents):
		dir = os_path.realpath(dir)
		for p in parents:
			if dir.startswith(p):
				return True
		return False

	def changeDir(self, directory, select = None):
		self.list = []
		if self.current_directory is None:
			if directory and self.showMountpoints:
				self.current_mountpoint = self.getMountpointLink(directory)
			else:
				self.current_mountpoint = None
		self.current_directory = directory
		directories = []
		files = []
		if directory is None and self.showMountpoints:
			for p in harddiskmanager.getMountedPartitions():
				path = os_path.join(p.mountpoint, "")
				if path not in self.inhibitMounts and not self.inParentDirs(path, self.inhibitDirs):
					self.list.append(FileEntryComponent(name = p.description, absolute = path, isDir = True))
			files = [ ]
			directories = [ ]
		elif directory is None:
			files = [ ]
			directories = [ ]
		elif self.useServiceRef:
			root = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + directory)
			if self.additional_extensions:
				root.setName(self.additional_extensions)
			serviceHandler = eServiceCenter.getInstance()
			list = serviceHandler.list(root)
			while 1:
				s = list.getNext()
				if not s.valid():
					del list
					break
				if s.flags & s.mustDescent:
					directories.append(s.getPath())
				else:
					files.append(s)
			directories.sort()
			files.sort()
		else:
			if os_path.exists(directory):
				files = listdir(directory)
				files.sort()
				tmpfiles = files[:]
				for x in tmpfiles:
					if os_path.isdir(directory + x):
						directories.append(directory + x + "/")
						files.remove(x)
		if directory is not None and self.showDirectories and not self.isTop:
			if directory == self.current_mountpoint and self.showMountpoints:
				self.list.append(FileEntryComponent(name = "<" +_("List of Storage Devices") + ">", absolute = None, isDir = True))
			elif (directory != "/") and not (self.inhibitMounts and self.getMountpoint(directory) in self.inhibitMounts):
				self.list.append(FileEntryComponent(name = "<" +_("Root Directory ") + ">", absolute = '/', isDir = True))
				self.list.append(FileEntryComponent(name = "<" +_("Parent Directory") + ">", absolute = '/'.join(directory.split('/')[:-2]) + '/', isDir = True))
		if self.showDirectories:
			for x in directories:
				if not (self.inhibitMounts and self.getMountpoint(x) in self.inhibitMounts) and not self.inParentDirs(x, self.inhibitDirs):
					name = x.split('/')[-2]
					self.list.append(FileEntryComponent(name = name, absolute = x, isDir = True))
		if self.showFiles:
			for x in files:
				if self.useServiceRef:
					path = x.getPath()
					name = path.split('/')[-1]
				else:
					path = directory + x
					name = x
					nx = None
					if (config.plugins.filemanager.media_filter.value == True):
						nx = self.getTSInfo(path)
						if nx is not None:
							name = nx
				EXext = os_path.splitext(path)[1]
				EXext = EXext.replace(".", "")
				EXext = EXext.lower()
				if (EXext == ""):
					EXext = "nothing"
				if (self.matchingPattern is None) or (EXext in self.matchingPattern):
					if nx is None:
						self.list.append(FileEntryComponent(name = name, absolute = x , isDir = False))
					else:
						res = [ (x, False) ]
						res.append((eListboxPythonMultiContent.TYPE_TEXT, 40, 2, 1000, 22, 0, RT_HALIGN_LEFT, name + " [" + self.getTSLength(path) + "]"))
						png = LoadPixmap("/usr/share/enigma2/easy-skin-hd/extensions/ext_movie.png")
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 12, 3, 20, 20, png))
						self.list.append(res)
		self.l.setList(self.list)
		if select is not None:
			i = 0
			self.moveToIndex(0)
			for x in self.list:
				p = x[0][0]
				if isinstance(p, eServiceReference):
					p = p.getPath()
				if p == select:
					self.moveToIndex(i)
				i += 1

	def getCurrentDirectory(self):
		return self.current_directory

	def canDescent(self):
		if self.getSelection() is None:
			return False
		return self.getSelection()[1]

	def descent(self):
		if self.getSelection() is None:
			return
		self.changeDir(self.getSelection()[0], select = self.current_directory)

	def getFilename(self):
		if self.getSelection() is None:
			return None
		x = self.getSelection()[0]
		if isinstance(x, eServiceReference):
			x = x.getPath()
		return x

	def getServiceRef(self):
		if self.getSelection() is None:
			return None
		x = self.getSelection()[0]
		if isinstance(x, eServiceReference):
			return x
		return None

	def execBegin(self):
		harddiskmanager.on_partition_list_change.append(self.partitionListChanged)

	def execEnd(self):
		harddiskmanager.on_partition_list_change.remove(self.partitionListChanged)

	def refresh(self):
		self.changeDir(self.current_directory, self.getFilename())

	def partitionListChanged(self, action, device):
		self.refreshMountpoints()
		if self.current_directory is None:
			self.refresh()

	def getTSInfo(self, path):
		if path.endswith(".ts"):
			serviceref = eServiceReference("1:0:0:0:0:0:0:0:0:0:" + path)
			if not serviceref.valid():
				return None
			serviceHandler = eServiceCenter.getInstance()
			info = serviceHandler.info(serviceref)
			if info is not None:
				txt = info.getName(serviceref)
				description = info.getInfoString(serviceref, iServiceInformation.sDescription)
				if not txt.endswith(".ts"):
					if description is not "":
						return txt + ' - ' + description
					else:
						return txt
				else:
					evt = info.getEvent(serviceref)
					if evt:
						return evt.getEventName() + ' - ' + evt.getShortDescription()
					else:
						return None

	def getTSLength(self, path):
		tslen = ""
		if path.endswith(".ts"):
			serviceref = eServiceReference("1:0:0:0:0:0:0:0:0:0:" + path)
			serviceHandler = eServiceCenter.getInstance()
			info = serviceHandler.info(serviceref)
			tslen = info.getLength(serviceref)
			if tslen > 0:
				tslen = "%d:%02d" % (tslen / 60, tslen % 60)
			else:
				tslen = ""
		return tslen

	def byNameFunc(self, a, b):
		return cmp(b[0][1], a[0][1]) or cmp(a[1][7], b[1][7])

	def sortName(self):
		self.list.sort(self.byNameFunc)
		#self.l.invalidate()
		self.l.setList(self.list)
		self.moveToIndex(0)

	def byDateFunc(self, a, b):
		try:
			stat1 = os_stat(self.current_directory + a[0][0])
			stat2 = os_stat(self.current_directory + b[0][0])
		except:
			return 0
		return cmp(b[0][1], a[0][1]) or cmp(stat2.st_ctime, stat1.st_ctime)

	def sortDate(self):
		self.list.sort(self.byDateFunc)
		#self.l.invalidate()
		self.l.setList(self.list)
		self.moveToIndex(0)



#######################################################################################################################################################################################
class FileManager(Screen):
    def __init__(self, session,path_left):
	path_right = "/"
        if path_left is None:
	    try:
	      if os_path_isdir(config.plugins.filemanager.path_left.value) and config.plugins.filemanager.savedirs.value:
		  path_left = config.plugins.filemanager.path_left.value
	      else:
		  path_left = "/"
	    except:
	      path_left = "/"
	    
	    try:
	      if os_path_isdir(config.plugins.filemanager.path_right.value) and config.plugins.filemanager.savedirs.value:
		  path_right = config.plugins.filemanager.path_right.value
	      else:
		  path_right = "/"
	    except:
	      path_right = "/"

	self.skin = FileManager_Skin
        Screen.__init__(self, session)

	self.sesion = session
	self.MyBox = HardwareInfo().get_device_name()
	self.commando = [ "ls" ]
	self.selectedDir = "/tmp/"
	self.booklines = []
	self.altservice = self.session.nav.getCurrentlyPlayingServiceReference()
	self.RightList = False
	self.LeftList = True
	self.ReloadPlugins = False
	  
	if config.plugins.filemanager.media_filter.value == False:
		self.MediaFilter = False
	else:
		self.MediaFilter = True
		
	if config.plugins.filemanager.hidden_filter.value == True:
		self.MediaPattern = "^.*\.(ts|m2ts|mts|mp3|wav|ogg|jpg|jpeg|jpe|png|bmp|mpg|mpeg|mkv|mp4|mov|divx|avi|mp2|m4a|flac|ifo|vob|iso)"
	else:
		self.MediaPattern = "(?i)^.*\.(ts|m2ts|mts|mp3|wav|ogg|jpg|jpeg|jpe|png|bmp|mpg|mpeg|mkv|mp4|mov|divx|avi|mp2|m4a|flac|ifo|vob|iso)"

		
	if (config.plugins.filemanager.media_filter.value == True):
		self["list_left"] = FileList(path_left, showDirectories = True, showFiles = True, matchingPattern = self.MediaPattern, useServiceRef = False)
		self["list_right"] = FileList(path_right, showDirectories = True, showFiles = True, matchingPattern = self.MediaPattern, useServiceRef = False)
	else:
		self["list_left"] = FileList(path_left, showDirectories = True, showFiles = True, matchingPattern = None, useServiceRef = False)
		self["list_right"] = FileList(path_right, showDirectories = True, showFiles = True, matchingPattern = None, useServiceRef = False)
			

	self["list_left_text"] = Label(_("Source"))
	self["list_right_text"] = Label(_("Target"))
	self["key_red"] = Label(_("Copy"))
	self["key_green"] = Label(_("Remove"))
	self["key_yellow"] = Label(_("Move"))
	self["key_blue"] = Label(_("More Options"))
	self["settings_text"] = Label(_("Settings"))
	
        self["actions"] = ActionMap(["ChannelSelectBaseActions","WizardActions", "DirectionActions","MenuActions","NumberActions","ColorActions"],
            {
             "ok":      self.ok,
             "back":    self.exit,
             "menu":    self.goSettings,
             "nextMarker": self.listRight,
             "prevMarker": self.listLeft,
             "up": self.goUp,
             "down": self.goDown,
             "left": self.goLeft,
             "right": self.goRight,
             "0": self.doRefresh,
             "red" : self.goCopy,
             "green" : self.goRemove,
	     "yellow" : self.goMove,
	     "blue" : self.goMenu,
             }, -1)
        self.onLayoutFinish.append(self.listLeft)

    def exit(self):
        if self["list_left"].getCurrentDirectory() and config.plugins.filemanager.savedirs.value:
            config.plugins.filemanager.path_left.value = self["list_left"].getCurrentDirectory()
            config.plugins.filemanager.path_left.save()

        if self["list_right"].getCurrentDirectory() and config.plugins.filemanager.savedirs.value:
            config.plugins.filemanager.path_right.value = self["list_right"].getCurrentDirectory()
            config.plugins.filemanager.path_right.save()
			
	if self.ReloadPlugins:
		from Components.PluginComponent import plugins
		from Tools.Directories import resolveFilename, SCOPE_PLUGINS
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
		self.ReloadPlugins = False
		
        self.close()

    def ok(self):
        if self.SOURCELIST.canDescent(): # isDir
            self.SOURCELIST.descent()
            if self.SOURCELIST.getCurrentDirectory(): #??? when is it none
                self.setTitle(self.SOURCELIST.getCurrentDirectory())
		print self.SOURCELIST.getCurrentDirectory()
        else:
            self.onFileAction()

    def goMenu(self):
	if(self.LeftList == True):
		try:
			filename = self["list_left"].getCurrentDirectory() + self["list_left"].getFilename()
			testFileName = self["list_left"].getFilename()
			self.SOURCELIST = self["list_left"]
        		self.TARGETLIST = self["list_right"]
			sourcedir = self["list_left"].getCurrentDirectory()
			targetdir = self.TARGETLIST.getCurrentDirectory()
			self.session.openWithCallback(self.doRefresh, FileManager_InfoMenu, testFileName, filename, targetdir, sourcedir)
		except:
			print 'none'
	else:
		try:
			filename = self["list_right"].getCurrentDirectory() + self["list_right"].getFilename()
			testFileName = self["list_right"].getFilename()
			self.SOURCELIST = self["list_right"]
        		self.TARGETLIST = self["list_left"]
			sourcedir = self["list_right"].getCurrentDirectory()
			targetdir = self.TARGETLIST.getCurrentDirectory()
			self.session.openWithCallback(self.doRefresh, FileManager_InfoMenu, testFileName, filename, targetdir, sourcedir)
		except:
			print 'none'		

    def goLeft(self):
        self.SOURCELIST.pageUp()

    def goRight(self):
        self.SOURCELIST.pageDown()

    def goUp(self):
        self.SOURCELIST.up()

    def goDown(self):
        self.SOURCELIST.down()

    def doRefresh(self):
		if config.plugins.filemanager.hidden_filter.value == True:
			self.MediaPattern = "^.*\.(ts|m2ts|mts|mp3|wav|ogg|jpg|jpeg|jpe|png|bmp|mpg|mpeg|mkv|mp4|mov|divx|avi|mp2|m4a|flac|ifo|vob|iso)"
		else:
			self.MediaPattern = "(?i)^.*\.(ts|m2ts|mts|mp3|wav|ogg|jpg|jpeg|jpe|png|bmp|mpg|mpeg|mkv|mp4|mov|divx|avi|mp2|m4a|flac|ifo|vob|iso)"
			
		if config.plugins.filemanager.media_filter.value == False:
			self.MediaFilter=False
			config.plugins.filemanager.media_filter.value == False
			config.plugins.filemanager.media_filter.save()
			self["list_left"].matchingPattern = None
			self["list_left"].refresh()
			self["list_right"].matchingPattern = None
			self["list_right"].refresh()
		else:
			self.MediaFilter=True
			config.plugins.filemanager.media_filter.value == True
			config.plugins.filemanager.media_filter.save()
			self["list_left"].matchingPattern = self.MediaPattern
			self["list_left"].refresh()
			self["list_right"].matchingPattern = self.MediaPattern
			self["list_right"].refresh()

		if config.plugins.filemanager.sort_by.value == 'name':
			print "[FileManager] Sorting Lists by Name"
			self["list_left"].sortName()
			self["list_right"].sortName()
		else:
			print "[FileManager] Sorting Lists by Date"
			self["list_left"].sortDate()
			self["list_right"].sortDate()


    def listRight(self):
	self.doRefresh()
	self.RightList = True
	self.LeftList = False
        self["list_left"].selectionEnabled(0)
        self["list_right"].selectionEnabled(1)
        self.SOURCELIST = self["list_right"]
        self.TARGETLIST = self["list_left"]
        self.setTitle(self.SOURCELIST.getCurrentDirectory())

    def listLeft(self):
	self.doRefresh()
	self.RightList = False
	self.LeftList = True
        self["list_left"].selectionEnabled(1)
        self["list_right"].selectionEnabled(0)
        self.SOURCELIST = self["list_left"]
        self.TARGETLIST = self["list_right"]
        self.setTitle(self.SOURCELIST.getCurrentDirectory())

    def SysExecution(self, answer):
	answer = answer and answer[1]
	if answer == "YES":
		self.session.open(ConsoleView, self.commando[0])
	elif answer == "VIEW":
		yfile=os_stat(self.commando[0])
		if (yfile.st_size < 100000):
			self.session.open(FileViewer, self.commando[0])
				
    def onFileAction(self):
	    	global DVDPlayerAviable
		if self.SOURCELIST.canDescent():
			self.SOURCELIST.descent()
			self.doRefresh()
		else:
			filename = self.SOURCELIST.getCurrentDirectory() + self.SOURCELIST.getFilename()
			testFileName = self.SOURCELIST.getFilename()
			testFileName = testFileName.lower()
			if filename != None:
				if testFileName.endswith(".ts"):
					m_dir = self.SOURCELIST.getCurrentDirectory()
					fileRef = eServiceReference("1:0:0:0:0:0:0:0:0:0:" + filename)
					self.session.open(ExtMoviePlayer, fileRef, m_dir, testFileName)
				elif (testFileName.endswith(".mpg")) or (testFileName.endswith(".mpeg")) or (testFileName.endswith(".mkv")) or (testFileName.endswith(".m2ts")) or (testFileName.endswith(".vob")):
						m_dir = self.SOURCELIST.getCurrentDirectory()
						fileRef = eServiceReference("4097:0:0:0:0:0:0:0:0:0:" + filename)
						self.session.open(ExtMoviePlayer, fileRef, m_dir, testFileName)
				elif (testFileName.endswith(".avi")) or (testFileName.endswith(".mp4")) or (testFileName.endswith(".divx")) or (testFileName.endswith(".mov")) or (testFileName.endswith(".mts")):
					if not(self.MyBox=="dm7025"):	
						m_dir = self.SOURCELIST.getCurrentDirectory()
						fileRef = eServiceReference("4097:0:0:0:0:0:0:0:0:0:" + filename)
						self.session.open(ExtMoviePlayer, fileRef, m_dir, testFileName)
				elif (testFileName.endswith(".mp3")) or (testFileName.endswith(".wav")) or (testFileName.endswith(".ogg")):
					m_dir = self.SOURCELIST.getCurrentDirectory()
					fileRef = eServiceReference("4097:0:0:0:0:0:0:0:0:0:" + filename)
					self.session.open(ExtMusicPlayer, fileRef, m_dir, testFileName)
				elif (testFileName.endswith(".m4a")) or (testFileName.endswith(".mp2")) or (testFileName.endswith(".flac")):
					if not(self.MyBox=="dm7025"):	
						m_dir = self.SOURCELIST.getCurrentDirectory()
						fileRef = eServiceReference("4097:0:0:0:0:0:0:0:0:0:" + filename)
						self.session.open(ExtMusicPlayer, fileRef, m_dir, testFileName)
				elif (testFileName.endswith(".jpg")) or (testFileName.endswith(".jpeg")) or (testFileName.endswith(".jpe")) or (testFileName.endswith(".png")) or (testFileName.endswith(".bmp")):
					m_dir = self.SOURCELIST.getCurrentDirectory()
					self.session.open(PicViewer, filename, m_dir)
				elif (testFileName.endswith(".mvi")):
					self.session.nav.stopService()
					self.session.open(EGMviViewer, filename)
				elif (testFileName == "video_ts.ifo"):
					if DVDPlayerAviable:
						if (self["filelist"].getCurrentDirectory()).lower().endswith("video_ts/"):
							self.session.nav.stopService()
							self.session.open(DVDPlayer, dvd_filelist=[self["filelist"].getCurrentDirectory()])
				elif testFileName.endswith(".iso"):
					if DVDPlayerAviable:
						self.session.nav.stopService()
						self.session.open(DVDPlayer, dvd_filelist=[filename])
				elif testFileName.endswith(".tar.gz"):
					self.commando = [ "tar -xzvf " + filename + " -C /;chmod 755 /tmp/egami_e2_installer.sh; /tmp/egami_e2_installer.sh; rm /tmp/egami_e2_installer.sh" ]
					askList = [(_("Cancel"), "NO"),(_("Install this package"), "YES")]
					dei = self.session.openWithCallback(self.SysExecution, ChoiceBox, title=_("GZ-package:\\n"+filename), list=askList)
					dei.setTitle(_("File Manager Install..."))
				elif testFileName.endswith(".tar.bz2"):
					self.commando = [ "tar -xjvf " + filename + " -C /;chmod 755 /tmp/egami_e2_installer.sh; /tmp/egami_e2_installer.sh; rm /tmp/egami_e2_installer.sh" ]
					askList = [(_("Cancel"), "NO"),(_("Install this package"), "YES")]
					dei = self.session.openWithCallback(self.SysExecution, ChoiceBox, title=_("BZ2-package:\\n"+filename), list=askList)
					dei.setTitle(_("File Manager Install..."))
				elif testFileName.endswith(".ipk"):
					self.ReloadPlugins = True
					self.commando = [ "ipkg install -force-overwrite " + filename ]
					askList = [(_("Cancel"), "NO"),(_("Install this package"), "YES")]
					dei = self.session.openWithCallback(self.SysExecution, ChoiceBox, title=_("IPKG-package:\\n"+filename), list=askList)
					dei.setTitle(_("File Manager Install..."))
				elif testFileName.endswith(".sh"):
					self.commando = [ filename ]
					askList = [(_("Cancel"), "NO"),(_("View this shell-script"), "VIEW"),(_("Start execution"), "YES")]
					self.session.openWithCallback(self.SysExecution, ChoiceBox, title=_("Do you want to execute?\\n"+filename), list=askList)
				else:
					xfile=os_stat(filename)
					if (xfile.st_size < 100000):
						self.session.open(FileViewer, filename)

#### REMOVE FILE		
    def goRemove(self):
	if(self.LeftList == True):
		try:
			filename = self["list_left"].getCurrentDirectory() + self["list_left"].getFilename()
			testFileName = self["list_left"].getFilename()
			self.SOURCELIST = self["list_left"]
        		self.TARGETLIST = self["list_right"]
			sourcedir = self["list_left"].getCurrentDirectory()
			targetdir = self.TARGETLIST.getCurrentDirectory()
			self.filename = filename
			self.dir = dir
			self.targetdir = targetdir
			self.sourcedir = sourcedir
			self.dirfile = sourcedir+filename
			self.usunHDD = sourcedir + testFileName
			self.usunFlash = testFileName
# HDD
#print filename        /media/hdd/enigma2-plugin-extensions-multiquickbutton_2.7_mipsel.ipk
#print testFileName    enigma2-plugin-extensions-multiquickbutton_2.7_mipsel.ipk
#print sourcedir       /media/hdd/                             OK


# FLASH
#/usr/lib/enigma2/python/Plugins/Extensions//usr/lib/enigma2/python/Plugins/Extensions/LiveFootBall/
#/usr/lib/enigma2/python/Plugins/Extensions/LiveFootBall/
#/usr/lib/enigma2/python/Plugins/Extensions/                 OK

			self.movie = self.sourcedir+self.filename
			self.session.openWithCallback(self.doDelete,ChoiceBox, title = _("delete file")+"?\n%s\nfrom dir\n%s"%(self.filename,self.sourcedir),list=[(_("yes"), True ),(_("no"), False )])
		except:
			print 'none'
	else:
		try:
			filename = self["list_right"].getCurrentDirectory() + self["list_right"].getFilename()
			testFileName = self["list_right"].getFilename()
			self.SOURCELIST = self["list_right"]
        		self.TARGETLIST = self["list_left"]
			sourcedir = self["list_right"].getCurrentDirectory()
			targetdir = self.TARGETLIST.getCurrentDirectory()
			self.filename = filename
			self.dir = dir
			self.targetdir = targetdir
			self.sourcedir = sourcedir
			self.dirfile = sourcedir+filename
			self.movie = self.sourcedir+self.filename
			self.usunHDD = sourcedir + testFileName
			self.usunFlash = testFileName
			self.session.openWithCallback(self.doDelete,ChoiceBox, title = _("delete file")+"?\n%s\nfrom dir\n%s"%(self.filename,self.sourcedir),list=[(_("yes"), True ),(_("no"), False )])
		except:
			print 'none'		
			
        

    def doDelete(self,result):
        if result is not None:
            if result[1]:
                self.session.open(Console, title = _("deleting file ..."), cmdlist = ["rm -rf \""+self.usunHDD+"\";rm -rf \""+self.usunFlash+"\""])
                self.doRefresh()
### COPY FILE
    def goCopy(self):
	if(self.LeftList == True):
		try:
			filename = self["list_left"].getCurrentDirectory() + self["list_left"].getFilename()
			testFileName = self["list_left"].getFilename()
			self.SOURCELIST = self["list_left"]
        		self.TARGETLIST = self["list_right"]
			sourcedir = self["list_left"].getCurrentDirectory()
			targetdir = self.TARGETLIST.getCurrentDirectory()
			self.filename = filename
			self.dir = filename
			self.targetdir = targetdir
			self.sourcedir = sourcedir
			self.dirfile = sourcedir+filename
			self.movie = self.sourcedir+self.filename
			self.session.openWithCallback(self.doCopy,ChoiceBox, title = _("copy file")+"?\n%s\nfrom\n%s\n%s"%(self.filename,self.dir,self.targetdir),list=[(_("yes"), True ),(_("no"), False )])
		except:
			print 'none'
	else:
		try:
			filename = self["list_right"].getCurrentDirectory() + self["list_right"].getFilename()
			testFileName = self["list_right"].getFilename()
			self.SOURCELIST = self["list_right"]
        		self.TARGETLIST = self["list_left"]
			sourcedir = self["list_right"].getCurrentDirectory()
			targetdir = self.TARGETLIST.getCurrentDirectory()
			self.filename = filename
			self.dir = filename
			self.targetdir = targetdir
			self.sourcedir = sourcedir
			self.dirfile = sourcedir+filename
			self.movie = self.sourcedir+self.filename
			self.session.openWithCallback(self.doCopy,ChoiceBox, title = _("copy file")+"?\n%s\nfrom\n%s\n%s"%(self.filename,self.dir,self.targetdir),list=[(_("yes"), True ),(_("no"), False )])
		except:
			print 'none'	

    def doCopy(self,result):
        if result is not None:
            if result[1]:
                 self.session.open(Console, title = _("copying file ..."), cmdlist = ["cp \""+self.dir+"\" \""+self.targetdir+"\""])
                 self.doRefresh()
		
### MOVE FILE
    def goMove(self):
	if(self.LeftList == True):
		try:
			filename = self["list_left"].getCurrentDirectory() + self["list_left"].getFilename()
			testFileName = self["list_left"].getFilename()
			self.SOURCELIST = self["list_left"]
        		self.TARGETLIST = self["list_right"]
			sourcedir = self["list_left"].getCurrentDirectory()
			targetdir = self.TARGETLIST.getCurrentDirectory()
			self.filename = filename
			self.dir = filename
			self.targetdir = targetdir
			self.sourcedir = sourcedir
			self.dirfile = sourcedir+filename
			self.movie = self.sourcedir+self.filename
			self.session.openWithCallback(self.doMove,ChoiceBox, title = _("move file")+"?\n%s\nfrom dir\n%s\nto dir\n%s"%(self.filename,self.dir,self.targetdir),list=[(_("yes"), True ),(_("no"), False )])
		except:
			print 'none'
	else:
		try:
			filename = self["list_right"].getCurrentDirectory() + self["list_right"].getFilename()
			testFileName = self["list_right"].getFilename()
			self.SOURCELIST = self["list_right"]
        		self.TARGETLIST = self["list_left"]
			sourcedir = self["list_right"].getCurrentDirectory()
			targetdir = self.TARGETLIST.getCurrentDirectory()
			self.filename = filename
			self.dir = filename
			self.targetdir = targetdir
			self.sourcedir = sourcedir
			self.dirfile = sourcedir+filename
			self.movie = self.sourcedir+self.filename
			self.session.openWithCallback(self.doMove,ChoiceBox, title = _("move file")+"?\n%s\nfrom dir\n%s\nto dir\n%s"%(self.filename,self.dir,self.targetdir),list=[(_("yes"), True ),(_("no"), False )])
		except:
			print 'none'	

    def doMove(self,result):
        if result is not None:
            if result[1]:
                 self.session.open(Console, title = _("moving file ..."), cmdlist = ["mv \""+self.dir+"\" \""+self.targetdir+"\""])
                 self.doRefresh()
                 
    def goSettings(self):
      self.session.open(FileManagerConfig)
                
class FileManager_symlink_create(Screen, ConfigListScreen):
	def __init__(self, session, file, path):
		self.skin = FileManager_symlink_create_Skin
		Screen.__init__(self, session)
	 
		list = []

		config.plugins.filemanager.symlink_name = ConfigText(default = file, fixed_size = False)
		config.plugins.filemanager.symlink_path = ConfigText(default = path, fixed_size = False)
			
		list.append(getConfigListEntry(_("Source:"), config.plugins.filemanager.symlink_name))
		list.append(getConfigListEntry(_("Symlink:"), config.plugins.filemanager.symlink_path))

		ConfigListScreen.__init__(self, list)
		
		self["key_green"] = Label(_("Create"))
		
        	self['actions'] = ActionMap(['OkCancelActions', 'ColorActions'], 
		{
	 		'green': self.KeyGreen,
         		'cancel': self.Exit
		}, -1)

	def KeyGreen(self):
		os_system((("ln -s " + config.plugins.filemanager.symlink_name.value) + " ") + config.plugins.filemanager.symlink_path.value)
		self.session.open(MessageBox, _("Symlink created sucesfully"), MessageBox.TYPE_INFO)
		self.close(True)
	
	def Exit(self):
		self.close()
		
import stat, sys, os, string


class FileManager_file_permission(Screen, ConfigListScreen):
	def __init__(self, session, file, path):
		self.skin = FileManager_file_permision_Skin
		Screen.__init__(self, session)
			 
		self.file = file
		self.path = path
		
		self.load_perm()
		
		list = []

		config.plugins.filemanager.user_read = ConfigSelection(default = self.user_r, choices = [("4", _("Yes")), ("0", _("No"))])
		config.plugins.filemanager.user_write = ConfigSelection(default = self.user_w, choices = [("2", _("Yes")), ("0", _("No"))])
		config.plugins.filemanager.user_execute = ConfigSelection(default = self.user_x, choices = [("1", _("Yes")), ("0", _("No"))])

		config.plugins.filemanager.group_read = ConfigSelection(default = self.group_r, choices = [("4", _("Yes")), ("0", _("No"))])
		config.plugins.filemanager.group_write = ConfigSelection(default = self.group_w, choices = [("2", _("Yes")), ("0", _("No"))])
		config.plugins.filemanager.group_execute = ConfigSelection(default = self.group_x, choices = [("1", _("Yes")), ("0", _("No"))])

		config.plugins.filemanager.other_read = ConfigSelection(default = self.other_r, choices = [("4", _("Yes")), ("0", _("No"))])
		config.plugins.filemanager.other_write = ConfigSelection(default = self.other_w, choices = [("2", _("Yes")), ("0", _("No"))])
		config.plugins.filemanager.other_execute = ConfigSelection(default = self.other_x, choices = [("1", _("Yes")), ("0", _("No"))])

		list.append(getConfigListEntry(_("user-read"), config.plugins.filemanager.user_read))
		list.append(getConfigListEntry(_("user-write"), config.plugins.filemanager.user_write))
		list.append(getConfigListEntry(_("user-execute"), config.plugins.filemanager.user_execute))
		#list.append("--------------------------")
		list.append(getConfigListEntry(_("group-read"), config.plugins.filemanager.group_read))
		list.append(getConfigListEntry(_("group-write"), config.plugins.filemanager.group_write))
		list.append(getConfigListEntry(_("group-execute"), config.plugins.filemanager.group_execute))
		#list.append("--------------------------")
		list.append(getConfigListEntry(_("other-read"), config.plugins.filemanager.other_read))
		list.append(getConfigListEntry(_("other-write"), config.plugins.filemanager.other_write))
		list.append(getConfigListEntry(_("other-execute"), config.plugins.filemanager.other_execute))

		ConfigListScreen.__init__(self, list)
		
		self["key_green"] = Label(_("Save"))
		
        	self['actions'] = ActionMap(['OkCancelActions', 'ColorActions'], 
		{
	 		'green': self.KeyGreen,
         		'cancel': self.Exit
		}, -1)

	def load_perm(self):
		file = self.file
		mode=stat.S_IMODE(os.lstat(file)[stat.ST_MODE])
		level = "USR"
		for perm in "R", "W", "X":
				if mode & getattr(stat,"S_I"+perm+level):
					if(perm == 'R'):
						self.user_r = '4'
					if(perm == 'W'):
						self.user_w = '2'
					if(perm == 'X'):
						self.user_x = '1'
				else:
					if(perm == 'R'):
						self.user_r = '0'
					if(perm == 'W'):
						self.user_w = '0'
					if(perm == 'X'):
						self.user_x = '0'
		
		level = "GRP"
		for perm in "R", "W", "X":
				if mode & getattr(stat,"S_I"+perm+level):
					if(perm == 'R'):
						self.group_r = '4'
					if(perm == 'W'):
						self.group_w = '2'
					if(perm == 'X'):
						self.group_x = '1'
				else:
					if(perm == 'R'):
						self.group_r = '0'
					if(perm == 'W'):						
						self.group_w = '0'
					if(perm == 'X'):
						self.group_x = '0'
		level = "OTH"
		for perm in "R", "W", "X":
				if mode & getattr(stat,"S_I"+perm+level):
					if(perm == 'R'):
						self.other_r = '4'
					if(perm == 'W'):
						self.other_w = '2'
					if(perm == 'X'):
						self.other_x = '1'
				else:
					if(perm == 'R'):
						self.other_r = '0'
					if(perm == 'W'):
						self.other_w = '0'
					if(perm == 'X'):
						self.other_x = '0'
								
	def KeyGreen(self):
		user = int(config.plugins.filemanager.user_read.value) + int(config.plugins.filemanager.user_write.value) + int(config.plugins.filemanager.user_execute.value)
		group = int(config.plugins.filemanager.group_read.value) + int(config.plugins.filemanager.group_write.value) + int(config.plugins.filemanager.group_execute.value)
		other = int(config.plugins.filemanager.other_read.value) + int(config.plugins.filemanager.other_write.value) + int(config.plugins.filemanager.other_execute.value)
		os_system("chmod "+str(user)+str(group)+str(other) + " " + self.file)
		#print "chmod "+str(user)+str(group)+str(other) + " " + self.file
		self.session.open(MessageBox, _("Permission for file has been changed sucesfully!"), MessageBox.TYPE_INFO)
		self.close(True)
	
	def Exit(self):
		self.close()

dmnapi_py = "python /usr/lib/enigma2/python/EGAMI/EGAMI_dmnapi.pyo"

class FileManager_InfoMenu(Screen):
    def __init__(self, session, filename, dir, targetdir, sourcedir, args = 0):
        self.session = session
        Screen.__init__(self, session)
	self.skin = FileManager_InfoMenu_Skin
	self.filename = filename
	self.dir = dir
        self.targetdir = targetdir
	self.sourcedir = sourcedir
	self.dirfile = sourcedir+filename
	self.movie = self.sourcedir+self.filename
	self.menu = args
        list = []
        #list.append((_("Remove"), "remove"))
	#list.append((_("Copy"), "copy"))
	#list.append((_("Move"), "move"))
	list.append((_("Rename"), "rename"))
	list.append((_("Permission"), "rights"))
	list.append((_("----------------------------------"), " "))
	list.append((_("New directory"), "new_directory"))
	list.append((_("New file"), "new_file"))
	list.append((_("New symlink"), "new_link"))
	list.append((_("----------------------------------"), " "))
	if (self.movie.endswith(".avi")) or (self.movie.endswith(".mp4")) or (self.movie.endswith(".divx")) or (self.movie.endswith(".mov")) or (self.movie.endswith(".mpg")) or (self.movie.endswith(".mpeg")) or (self.movie.endswith(".mkv")) or (self.movie.endswith(".m2ts")) or (self.movie.endswith(".vob")) or (self.movie.endswith(".rmvb")):
		list.append((_("Get Subtitle"), "get_sub"))
	#list.append((_("----------------------------------"), " "))
	#list.append((_("Settings"), "settings"))
        self["menu"] = MenuList(list)
        self["actions"] = ActionMap(["WizardActions"],{"ok": self.go,"exit": self.exit,}, -1)

### MENU
    def go(self):
        returnValue = self["menu"].l.getCurrentSelection()[1]
        if returnValue is not None:
           if returnValue is "remove":
		self.goRemove()
           elif returnValue is "copy":
		self.goCopy()
           elif returnValue is "move":
		self.goMove()
           elif returnValue is "rename":
		self.goRename()
           elif returnValue is "new_directory":
		self.goNewDirectory()
           elif returnValue is "new_file":
		self.goNewFile()
	   elif returnValue is "settings":
		self.session.open(FileManagerConfig)
           elif returnValue is "new_link":
		self.session.open(FileManager_symlink_create, self.dirfile, self.sourcedir)
	   elif returnValue is "rights":
		self.session.open(FileManager_file_permission, self.dirfile, self.sourcedir)
	   elif returnValue is "get_sub":
		os.system("chmod 755 /usr/lib/enigma2/python/EGAMI/EGAMI_dmnapi.pyo")
		self.session.open(Console,_("Download subtitle:"),['%s get "%s"' % (dmnapi_py, self.movie )])
		
    def exit(self):
        self.close()
	
#### REMOVE FILE		
    def goRemove(self):
        self.session.openWithCallback(self.doDelete,ChoiceBox, title = _("delete file")+"?\n%s\nfrom dir\n%s"%(self.filename,self.sourcedir),list=[(_("yes"), True ),(_("no"), False )])

    def doDelete(self,result):
        if result is not None:
            if result[1]:
                self.session.openWithCallback(self.exit,Console, title = _("deleting file ..."), cmdlist = ["rm -rf \""+self.sourcedir+self.filename+"\";rm -rf \""+self.filename+"\""])
### COPY FILE
    def goCopy(self):
        self.session.openWithCallback(self.doCopy,ChoiceBox, title = _("copy file")+"?\n%s\nfrom\n%s\n%s"%(self.filename,self.dir,self.targetdir),list=[(_("yes"), True ),(_("no"), False )])

    def doCopy(self,result):
        if result is not None:
            if result[1]:
                self.session.openWithCallback(self.exit,Console, title = _("copying file ..."), cmdlist = ["cp \""+self.dir+"\" \""+self.targetdir+"\""])
		
### MOVE FILE
    def goMove(self):
        self.session.openWithCallback(self.doMove,ChoiceBox, title = _("move file")+"?\n%s\nfrom dir\n%s\nto dir\n%s"%(self.filename,self.dir,self.targetdir),list=[(_("yes"), True ),(_("no"), False )])

    def doMove(self,result):
        if result is not None:
            if result[1]:
                self.session.openWithCallback(self.exit,Console, title = _("moving file ..."), cmdlist = ["mv \""+self.dir+"\" \""+self.targetdir+"\""])
		
### RENAME FILE
    def goRename(self):
        self.session.openWithCallback(self.doRename,InputBox,text=self.filename, title = self.filename, windowTitle=_("rename file"))

	
    def doRename(self,newname):
    	if newname:
            self.session.openWithCallback(self.exit,Console, title = _("renaming file ..."), cmdlist = ["mv \""+self.dir+"\" \""+self.sourcedir+newname+"\""])
	    
### NEW DIRECTORY
    def goNewDirectory(self):
		self.session.openWithCallback(self.doNewDirectory,InputBox,text=_("NewFolder"), title = _("new directory name"), windowTitle=_("creating new directory"))
	
    def doNewDirectory(self,newdict):
	    try:
            	self.session.openWithCallback(self.exit,Console, title = _("creating new directory ..."), cmdlist = ["mkdir \""+self.sourcedir+newdict+"\""])
	    except:
		    self.exit()
### NEW FILE
    def goNewFile(self):
        	self.session.openWithCallback(self.doNewFile,InputBox,text=_("NewFile"),title = _("new file name"), windowTitle=_("creating new file"))
	
    def doNewFile(self,newfile):
	    try:
		self.session.openWithCallback(self.exit,Console, title = _("creating new file ..."), cmdlist = [(("touch " + self.sourcedir) + newfile)])
	    except:
		self.exit()
				
class FileViewer(Screen):
	def __init__(self, session, file):
		self.skin = FileViewer_Skin
		Screen.__init__(self, session)
		self.file_name = file
		self["status"] = Label(_(file))
		self["filedata"] = ScrollLabel(_("Reading file. Please wait..."))
		self.filetext = ""
		self["actions"] = ActionMap(["WizardActions"],
		{
			"ok": self.close,
			"back": self.close,
			"left": self["filedata"].pageUp,
			"right": self["filedata"].pageDown,
			"up": self["filedata"].pageUp,
			"down": self["filedata"].pageDown
		}, -1)
		self.onLayoutFinish.append(self.ViewFileLines)

	def GetFileData(self, fx):
		xxflines = []
		try:
			flines = open(fx, "r")
			for line in flines:
				xxflines.append(line)
			flines.close()
			self.filetext = ''.join(xxflines)
		except:
			return 'Read Error.'

	def ViewFileLines(self):
		self.GetFileData(self.file_name)
		self["filedata"].setText(self.filetext)



class ConsoleView(Console):
	def __init__(self, session, os_commando):
		Console.skin = ConsoleView_Skin
		Console.__init__(self, session, title = "File Manager - Console", cmdlist = [ os_commando ])
		self["status"] = Label(_(os_commando))


class PicViewer(Screen):
	def __init__(self, session, whatPic = None, whatDir = None):
		self.skin = PicViewer_Skin
		Screen.__init__(self, session)
		self.session = session
		self.whatPic = whatPic
		self.whatDir = whatDir
		self.picList = []
		self.Pindex = 0
		self.EXscale = (AVSwitch().getFramebufferScale())
		self.EXpicload = ePicLoad()
		self["Picture"] = Pixmap()
		self["State"] = Label(_("LOADING..."))
		self["actions"] = ActionMap(["WizardActions", "DirectionActions"],
		{
			"ok": self.close,
			"back": self.close,
			"left": self.Pleft,
			"right": self.Pright
		}, -1)
		self.EXpicload.PictureData.get().append(self.DecodeAction)
		self.onLayoutFinish.append(self.Show_Picture)

	def Show_Picture(self):
		if self.whatPic is not None:
			self.EXpicload.setPara([self["Picture"].instance.size().width(), self["Picture"].instance.size().height(), self.EXscale[0], self.EXscale[1], 0, 1, "#002C2C39"])
			self.EXpicload.startDecode(self.whatPic)
		if self.whatDir is not None:
			pidx = 0
			for root, dirs, files in os_walk(self.whatDir ):
				for name in files:
					if name.endswith(".jpg") or name.endswith(".jpeg") or name.endswith(".Jpg") or name.endswith(".Jpeg") or name.endswith(".JPG") or name.endswith(".JPEG"):
						self.picList.append(name)
						if name in self.whatPic:
							self.Pindex = pidx
						pidx = pidx + 1

	def DecodeAction(self, pictureInfo=""):
		if self.whatPic is not None:
			self["State"].visible = False
			ptr = self.EXpicload.getData()
			self["Picture"].instance.setPixmap(ptr)

	def Pright(self):
		if len(self.picList)>2:
			self["State"].visible = True
			if self.Pindex<(len(self.picList)-1):
				self.Pindex = self.Pindex + 1
				self.whatPic = self.whatDir + str(self.picList[self.Pindex])
				self.EXpicload.startDecode(self.whatPic)
			else:
				self["State"].visible = False
				self.session.open(MessageBox,_('No more picture-files.'), MessageBox.TYPE_INFO)

	def Pleft(self):
		if len(self.picList)>2:
			self["State"].visible = True
			if self.Pindex>0:
				self.Pindex = self.Pindex - 1
				self.whatPic = self.whatDir + str(self.picList[self.Pindex])
				self.EXpicload.startDecode(self.whatPic)
			else:
				self["State"].visible = False
				self.session.open(MessageBox,_('No more picture-files.'), MessageBox.TYPE_INFO)

class MviViewer(Screen):
	skin = """
		<screen position="-300,-300" size="10,10" title="mvi-Explorer">
		</screen>"""
	def __init__(self, session, file):
		self.skin = EGMviViewer.skin
		Screen.__init__(self, session)
		self.file_name = file
		self["actions"] = ActionMap(["WizardActions"],
		{
			"ok": self.close,
			"back": self.close
		}, -1)
		self.onLayoutFinish.append(self.showMvi)
	def showMvi(self):
		os_system("/usr/bin/showiframe " + self.file_name)

class ExtMoviePlayer(MoviePlayer):
	def __init__(self, session, service, MusicDir, theFile):
		self.session = session
		MoviePlayer.__init__(self, session, service)
		self.skinName = "MoviePlayer"
		self.exitmodus = config.plugins.filemanager.exit_eop.value
		self.MusicDir = MusicDir
		self.musicList = []
		self.Mindex = 0
		self.curFile = theFile
		self.searchMusic()
		MoviePlayer.WithoutStopClose = False

	def searchMusic(self):
		midx = 0
		lista = os.listdir(self.MusicDir)
		lista.sort()
		for name in lista:
				name = name.lower()
				if name.endswith(".mpg") or name.endswith(".mpeg") or name.endswith(".mkv") or name.endswith(".m2ts") or name.endswith(".vob") or name.endswith(".avi") or name.endswith(".mts") or name.endswith(".mp4") or name.endswith(".divix") or name.endswith(".mov"):
					self.musicList.append(name)
					self.musicList.sort()
					if self.curFile in name:
						self.Mindex = midx
					midx = midx + 1
					

	def seekFwd(self):
		if len(self.musicList)>2:
			if self.Mindex<(len(self.musicList)-1):
				self.Mindex = self.Mindex + 1
				nextfile = self.MusicDir + str(self.musicList[self.Mindex])
				nextRef = eServiceReference("4097:0:0:0:0:0:0:0:0:0:" + nextfile)
				self.session.nav.playService(nextRef)
			else:
				self.nowhide()

	def seekBack(self):
		if len(self.musicList)>2:
			if self.Mindex>0:
				self.Mindex = self.Mindex - 1
				nextfile = self.MusicDir + str(self.musicList[self.Mindex])
				nextRef = eServiceReference("4097:0:0:0:0:0:0:0:0:0:" + nextfile)
				self.session.nav.playService(nextRef)
			else:
				self.nowhide()

	def leavePlayer(self):
		self.is_closing = True
		self.close()
		
	def doEofInternal(self, playing):
		if not self.execing:
			return
		if not playing :
			return
		self.seekFwd()
		
	def nowhide(self):
		if self.exitmodus == "Ask":
			print "ask"
			self.handleLeave("ask")
		elif self.exitmodus == "Yes":
			print "yes"
			self.leavePlayer()
		else:
			print "no"
			self.hide()
			
			
class ExtMusicPlayer(MoviePlayer):
	def __init__(self, session, service, MusicDir, theFile):
		self.session = session
		MoviePlayer.__init__(self, session, service)
		self.skinName = "MoviePlayer"
		self.exitmodus = config.plugins.filemanager.exit_eop.value
		self.MusicDir = MusicDir
		self.musicList = []
		self.Mindex = 0
		self.curFile = theFile
		self.searchMusic()
		self.onLayoutFinish.append(self.showMMI)
		MoviePlayer.WithoutStopClose = False

	def showMMI(self):
		os_system("/usr/bin/showiframe /usr/share/enigma2/radio.mvi")

	def searchMusic(self):
		#midx = 0
		#for root, dirs, files in os_walk(self.MusicDir ):
		#	for name in files:
		midx = 0
		lista = os.listdir(self.MusicDir)
		lista.sort()
		for name in lista:
				name = name.lower()
				if name.endswith(".mp3") or name.endswith(".mp2") or name.endswith(".ogg") or name.endswith(".wav") or name.endswith(".flac") or name.endswith(".m4a"):
					self.musicList.append(name)
					if self.curFile in name:
						self.Mindex = midx
					midx = midx + 1

	def seekFwd(self):
		if len(self.musicList)>2:
			if self.Mindex<(len(self.musicList)-1):
				self.Mindex = self.Mindex + 1
				nextfile = self.MusicDir + str(self.musicList[self.Mindex])
				nextRef = eServiceReference("4097:0:0:0:0:0:0:0:0:0:" + nextfile)
				self.session.nav.playService(nextRef)
			else:
				self.nowhide()

	def seekBack(self):
		if len(self.musicList)>2:
			if self.Mindex>0:
				self.Mindex = self.Mindex - 1
				nextfile = self.MusicDir + str(self.musicList[self.Mindex])
				nextRef = eServiceReference("4097:0:0:0:0:0:0:0:0:0:" + nextfile)
				self.session.nav.playService(nextRef)
			else:
				self.nowhide()

	def leavePlayer(self):
		self.is_closing = True
		self.close()
		
	def doEofInternal(self, playing):
		if not self.execing:
			return
		if not playing :
			return
		self.seekFwd()
		
	def nowhide(self):
		if self.exitmodus == "Ask":
			print "ask"
			self.handleLeave("ask")
		elif self.exitmodus == "Yes":
			print "yes"
			self.leavePlayer()
		else:
			print "no"
			self.session.open(MessageBox,_('No more playable files.'), MessageBox.TYPE_INFO)