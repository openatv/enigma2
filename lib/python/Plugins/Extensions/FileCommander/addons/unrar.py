#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from Plugins.Plugin import PluginDescriptor
from Components.config import config
from Plugins.Extensions.FileCommander.addons.unarchiver import ArchiverMenuScreen, ArchiverInfoScreen
from enigma import eServiceReference, eServiceCenter, eTimer, eSize, eConsoleAppContainer, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER
from Tools.Directories import resolveFilename, SCOPE_CURRENT_PLUGIN
from os.path import basename
import re
import subprocess
from Plugins.Extensions.FileCommander.InputBoxmod import InputBox

pname = _("File Commander - Unrar Addon")
pdesc = _("unpack Rar Files")
pversion = "0.2-r1"

class RarMenuScreen(ArchiverMenuScreen):

	def __init__(self, session, sourcelist, targetlist):
		super(RarMenuScreen, self).__init__(session, sourcelist, targetlist)

		self.unrar = "unrar"
		self.defaultPW = "2D1U3MP!"

		self.list.append((_("Show contents of rar file"), 1))
		self.list.append((_("Unpack to current folder"), 2))
		self.list.append((_("Unpack to %s") % self.targetDir, 3))
		self.list.append((_("Unpack to %s") % config.usage.default_path.value, 4))

		self.pname = pname
		self.pdesc = pdesc
		self.pversion = pversion

	def ok(self):
		selectName = self['list_left'].getCurrent()[0][0]
		self.selectId = self['list_left'].getCurrent()[0][1]
		print "Select:", selectName, self.selectId
		self.checkPW(self.defaultPW)

	def checkPW(self, pwd):
		self.defaultPW = pwd
		print "Current pw:", self.defaultPW
		cmd = (self.unrar, "p", "-p" + self.defaultPW, self.sourceDir + self.filename, "-o+", self.sourceDir)
		p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		stdlog = p.stdout.read()
		if stdlog:
			print stdlog
			if re.search('Corrupt file or wrong password.', stdlog, re.S):
				print "pw incorrect!"
				length = config.plugins.filecommander.input_length.value
				self.session.openWithCallback(self.setPW, InputBox, text="", visible_width=length, overwrite=False, firstpos_end=True, allmarked=False, title=_("Please enter password"), windowTitle=_("%s is password protected.") % self.filename)
			else:
				print "pw correct!"
				self.unpackModus(self.selectId)

	def setPW(self, pwd):
		if pwd is None:
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
		print "[RarMenuScreen] unpackModus", id
		if id == 1:
			cmd = (self.unrar, "lb", "-p" + self.defaultPW, self.sourceDir + self.filename)
			self.unpackPopen(cmd, UnpackInfoScreen)
		elif 2 <= id <= 4:
			cmd = [self.unrar, "x", "-p" + self.defaultPW, self.sourceDir + self.filename, "-o+"]
			if id == 2:
				cmd.append(self.sourceDir)
			elif id == 3:
				cmd.append(self.targetDir)
			elif id == 4:
				cmd.append(config.usage.default_path.value)
			self.unpackEConsoleApp(cmd, exePath=self.unrar, logCallback=self.log)

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

class UnpackInfoScreen(ArchiverInfoScreen):

	def __init__(self, session, list, sourceDir, filename):
		super(UnpackInfoScreen, self).__init__(session, list, sourceDir, filename)
		self.pname = pname
		self.pdesc = pdesc
		self.pversion = pversion
