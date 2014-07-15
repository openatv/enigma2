#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from Plugins.Plugin import PluginDescriptor
from Components.config import config, ConfigSubList, ConfigSubsection, ConfigInteger, ConfigYesNo, ConfigText, getConfigListEntry, ConfigSelection, NoSave, ConfigNothing
from Components.ConfigList import ConfigListScreen
from Screens.Console import Console
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.LocationBox import MovieLocationBox
from Screens.HelpMenu import HelpableScreen
from Screens.TaskList import TaskListScreen
from Components.Label import Label
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Scanner import openFile
from Components.MenuList import MenuList
from os.path import isdir as os_path_isdir
from mimetypes import guess_type
from Components.FileTransfer import FileTransferJob
from Components.Task import job_manager
from Screens.InfoBar import MoviePlayer as Movie_Audio_Player
from Tools.Directories import *
from Tools.BoundFunction import boundFunction
from enigma import eServiceReference, eServiceCenter, eTimer, eSize, eConsoleAppContainer, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER
from os import listdir, remove, rename, system, path, symlink, chdir
import os, re, subprocess
from Plugins.Extensions.FileCommander.InputBoxmod import InputBox

pname = _("File Commander - Unrar Addon")
pdesc = _("unpack Rar Files")
pversion = "0.2-r1"

class RarMenuScreen(Screen):
	skin = """
		<screen position="40,80" size="1200,600" title="" >
			<widget name="list_left_head" position="10,10" size="570,60" font="Regular;20" foregroundColor="#00fff000"/>
			<widget name="list_left" position="10,85" size="570,470" scrollbarMode="showOnDemand"/>
			<widget name="unpacking" position="10,250" size="570,30" scrollbarMode="showOnDemand" foregroundColor="#00ffffff"/>
			<widget name="key_red" position="100,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_green" position="395,570" size="260,25"  transparent="1" font="Regular;20"/>
			<widget name="key_yellow" position="690,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_blue" position="985,570" size="260,25" transparent="1" font="Regular;20"/>
			<ePixmap position="70,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_red.png" transparent="1" alphatest="on"/>
			<ePixmap position="365,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_green.png" transparent="1" alphatest="on"/>
			<ePixmap position="660,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_yellow.png" transparent="1" alphatest="on"/>
			<ePixmap position="955,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_blue.png" transparent="1" alphatest="on"/>
		</screen>"""

	def __init__(self, session, sourcelist, targetlist):
		self.session = session
		self.SOURCELIST = sourcelist
		self.TARGETLIST = targetlist
		Screen.__init__(self, session)
		self.unrar = "/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/addons/unrar"
		self.defaultPW = "2D1U3MP!"
		self.filename = self.SOURCELIST.getFilename()
		self.sourceDir = self.SOURCELIST.getCurrentDirectory()
		self.targetDir = self.TARGETLIST.getCurrentDirectory()
		self.list = []
		self.list.append((_("Show content of Rar File"), 1))
		self.list.append((_("Unpack to current folder"), 2))
		self.list.append((_("Unpack to %s") % (self.targetDir), 3))
		self.list.append((_("Unpack to /media/hdd/movie/"), 4))
		#self.list.append((_("Unpack with Password"), 5))

		self.chooseMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList.l.setFont(0, gFont('Regular', 20))
		self.chooseMenuList.l.setItemHeight(25)
		self['list_left'] = self.chooseMenuList
		
		self.chooseMenuList2 = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList2.l.setFont(0, gFont('Regular', 25))
		self.chooseMenuList2.l.setItemHeight(30)
		self['unpacking'] = self.chooseMenuList2
		self['unpacking'].selectionEnabled(0)

		self["list_left_head"] = Label("%s%s" % (self.sourceDir, self.filename))

		self["key_red"] = Label(_("cancel"))
		self["key_green"] = Label(_("ok"))
		self["key_yellow"] = Label("")
		self["key_blue"] = Label("")

		self["setupActions"] = ActionMap(["SetupActions"],
		{
			"red": self.cancel,
			"green": self.ok,
			"cancel": self.cancel,
			"ok": self.ok,
		}, -2)

		self.onLayoutFinish.append(self.onLayout)

	def onLayout(self):
		self.setTitle(pname)
		self.chooseMenuList.setList(map(self.ListEntry, self.list))

	def ListEntry(self, entry):
		return [entry,
			(eListboxPythonMultiContent.TYPE_TEXT, 10, 0, 1180, 25, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, entry[0])
			]
			
	def UnpackListEntry(self, entry):
		print entry
		currentProgress = int(float(100) / float(int(100)) * int(entry))
		proanzeige = str(currentProgress)+"%"
#		color2 = 0x00ffffff #Weiss
		return [entry,
			(eListboxPythonMultiContent.TYPE_PROGRESS, 10, 0, 560, 30, int(currentProgress), None, None, None, None),
			(eListboxPythonMultiContent.TYPE_TEXT, 10, 3, 560, 30, 0, RT_HALIGN_CENTER | RT_VALIGN_CENTER, str(proanzeige))
			]

	def ok(self):
		selectName = self['list_left'].getCurrent()[0][0]
		self.selectId = self['list_left'].getCurrent()[0][1]
		print "Select:", selectName, self.selectId
		self.checkPW(self.defaultPW)

	def checkPW(self, pwd):
		self.defaultPW = pwd
		print "Current pw:", self.defaultPW
		self.container = eConsoleAppContainer()
		cmd = "%s p -p%s %s%s -o+ %s" % (self.unrar, self.defaultPW, self.sourceDir, self.filename, self.sourceDir)
		p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		stdlog = p.stdout.read()
		if stdlog:
			print stdlog
			if re.search('Corrupt file or wrong password.', stdlog, re.S):
				print "pw falsch..!"
				length = config.plugins.filecommander.input_length.value
				self.session.openWithCallback(self.setPW,InputBox,text="", visible_width=length, overwrite=False, firstpos_end=True, allmarked=False, title = _("Please enter password"), windowTitle=_("%s is password protected.") % self.filename)
			else:
				print "pw richtig !"
				self.unpackModus(self.selectId)

	def setPW(self, pwd):
		if pwd == None:
			self.defaultPW = "2D1U3MP!"
		elif pwd == "":
			self.defaultPW = "2D1U3MP!"
		elif pwd == " ":
			self.defaultPW = "2D1U3MP!"
		elif pwd == "  ":
			self.defaultPW = "2D1U3MP!"
		elif pwd == "   ":
			self.defaultPW = "2D1U3MP!"
		else:
			self.checkPW(pwd)

	def unpackModus(self, id):
		if id == 1:
			cmd = "%s lb -p%s %s%s" % (self.unrar, self.defaultPW, self.sourceDir, self.filename)
			print cmd
			p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			output = p.stdout.readlines()
			if output:
				self.extractlist = []
				#self.extractlist.append(("<" +_("List of Storage Devices") + ">"))
				for line in output:
					#print line.split('\n')
					self.extractlist.append((line.split('\n')))
				
				if len(self.extractlist) != 0:
					self.session.open(UnpackInfoScreen, self.extractlist, self.sourceDir, self.filename)
				else:
					self.extractlist.append((_("no files found.")))
					self.session.open(UnpackInfoScreen, self.extractlist, self.sourceDir, self.filename)

		elif id == 2:
			self.container = eConsoleAppContainer()
			self.container.appClosed.append(boundFunction(self.extractDone, self.filename))
			self.container.dataAvail.append(self.log)
			self.ulist = []
			cmd = "%s x -p%s %s%s -o+ %s" % (self.unrar, self.defaultPW, self.sourceDir, self.filename, self.sourceDir)
			self.container.execute(cmd)

		elif id == 3:
			self.container = eConsoleAppContainer()
			self.container.appClosed.append(boundFunction(self.extractDone, self.filename))
			self.container.dataAvail.append(self.log)
			self.ulist = []
			cmd = "%s x -p%s %s%s -o+ %s" % (self.unrar, self.defaultPW, self.sourceDir, self.filename, self.targetDir)
			self.container.execute(cmd)

		elif id == 4:
			self.container = eConsoleAppContainer()
			self.container.appClosed.append(boundFunction(self.extractDone, self.filename))
			self.container.dataAvail.append(self.log)
			self.ulist = []
			cmd = "%s x -p%s %s%s -o+ /media/hdd/movie/" % (self.unrar, self.defaultPW, self.sourceDir, self.filename)
			self.container.execute(cmd)
			
	def log(self, data):
		print data			
		status = re.findall('(\d+)%', data, re.S)
		if status:
			if not status[0] in self.ulist:
				self.ulist.append((status[0]))
				self.chooseMenuList2.setList(map(self.UnpackListEntry, status))
				self['unpacking'].selectionEnabled(0)

		if re.search('All OK', data):
			self.chooseMenuList2.setList(map(self.UnpackListEntry, ['100']))
			self['unpacking'].selectionEnabled(0)

	def extractDone(self, filename, data):
		message = self.session.open(MessageBox, (_("%s successful extracted.") % filename), MessageBox.TYPE_INFO, timeout=8)

	def cancel(self):
		self.close(False)

class UnpackInfoScreen(Screen):
	skin = """
		<screen position="40,80" size="1200,600" title="" >
			<widget name="list_left_head" position="10,10" size="1180,60" font="Regular;20" foregroundColor="#00fff000"/>
			<widget name="list_left" position="10,85" size="1180,470" scrollbarMode="showOnDemand"/>
			<widget name="key_red" position="100,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_green" position="395,570" size="260,25"  transparent="1" font="Regular;20"/>
			<widget name="key_yellow" position="690,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_blue" position="985,570" size="260,25" transparent="1" font="Regular;20"/>
			<ePixmap position="70,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_red.png" transparent="1" alphatest="on"/>
			<ePixmap position="365,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_green.png" transparent="1" alphatest="on"/>
			<ePixmap position="660,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_yellow.png" transparent="1" alphatest="on"/>
			<ePixmap position="955,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FileCommander/pic/button_blue.png" transparent="1" alphatest="on"/>
		</screen>"""

	def __init__(self, session, list, sourceDir, filename):
		self.session = session
		self.list = list
		self.sourceDir = sourceDir
		self.filename = filename
		Screen.__init__(self, session)

		self.chooseMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList.l.setFont(0, gFont('Regular', 20))
		self.chooseMenuList.l.setItemHeight(25)
		self['list_left'] = self.chooseMenuList
		
		self["list_left_head"] = Label("%s%s" % (self.sourceDir, self.filename))
		
		self["key_red"] = Label(_("cancel"))
		self["key_green"] = Label(_("ok"))
		self["key_yellow"] = Label("")
		self["key_blue"] = Label("")

		self["setupActions"] = ActionMap(["SetupActions"],
		{
			"red": self.cancel,
			"green": self.cancel,
			"cancel": self.cancel,
			"ok": self.cancel,
		}, -2)

		self.onLayoutFinish.append(self.onLayout)

	def onLayout(self):
		self.setTitle(pname)
		if len(self.list) != 0:
			self.chooseMenuList.setList(map(self.ListEntry, self.list))

	def ListEntry(self, entry):
		return [entry,
			(eListboxPythonMultiContent.TYPE_TEXT, 10, 0, 1180, 25, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, entry[0])
			]

	def cancel(self):
		self.close()