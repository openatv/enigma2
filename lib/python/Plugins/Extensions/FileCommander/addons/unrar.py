#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from Screens.MessageBox import MessageBox
from Components.config import config
from Plugins.Extensions.FileCommander.addons.unarchiver import ArchiverMenuScreen, ArchiverInfoScreen
import re
import subprocess
from Plugins.Extensions.FileCommander.InputBox import InputBox
from Screens.VirtualKeyBoard import VirtualKeyBoard

pname = _("File Commander - unrar Addon")
pdesc = _("unpack Rar Files")
pversion = "0.2-r1"


class RarMenuScreen(ArchiverMenuScreen):

	DEFAULT_PW = "2D1U3MP!"

	def __init__(self, session, sourcelist, targetlist):
		super(RarMenuScreen, self).__init__(session, sourcelist, targetlist)

		self.unrar = "unrar"
		self.defaultPW = self.DEFAULT_PW

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
		print "[RarMenuScreen] Select:", selectName, self.selectId
		self.checkPW(self.defaultPW)

	def checkPW(self, pwd):
		self.defaultPW = pwd
		print "[RarMenuScreen] Current pw:", self.defaultPW
		cmd = (self.unrar, "t", "-p" + self.defaultPW, self.sourceDir + self.filename)
		try:
			p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		except OSError as ex:
			msg = _("Can not run %s: %s.\n%s may be in a plugin that is not installed.") % (cmd[0], ex.strerror, cmd[0])
			print "[RarMenuScreen]", msg
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR)
			return
		stdlog = p.stdout.read()
		if stdlog:
			print "[RarMenuScreen] checkPW stdout", len(stdlog)
			print stdlog
			if 'Corrupt file or wrong password.' in stdlog:
				print "[RarMenuScreen] pw incorrect!"
				#length = config.plugins.filecommander.input_length.value
				#self.session.openWithCallback(self.setPW, InputBox, text="", visible_width=length, overwrite=False, firstpos_end=True, allmarked=False, title=_("Please enter password"), windowTitle=_("%s is password protected.") % self.filename)
				self.session.openWithCallback(self.setPW, VirtualKeyBoard, title=_("%s is password protected.") % self.filename + " " + _("Please enter password"), text="")
			else:
				print "[RarMenuScreen] pw correct!"
				self.unpackModus(self.selectId)

	def setPW(self, pwd):
		if pwd is None or pwd.strip() == "":
			self.defaultPW = self.DEFAULT_PW
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
		# print "[RarMenuScreen] log", data
		status = re.findall('(\d+)%', data)
		if status:
			if not status[0] in self.ulist:
				self.ulist.append((status[0]))
				self.chooseMenuList2.setList(map(self.UnpackListEntry, status))
				self['unpacking'].selectionEnabled(0)

		if 'All OK' in data:
			self.chooseMenuList2.setList(map(self.UnpackListEntry, ['100']))
			self['unpacking'].selectionEnabled(0)

	def extractDone(self, filename, data):
		if data:
			if self.errlog and not self.errlog.endswith("\n"):
				self.errlog += "\n"
			self.errlog += {
				1: "Non fatal error(s) occurred.",
				2: "A fatal error occurred.",
				3: "Invalid checksum. Data is damaged.",
				4: "Attempt to modify an archive locked by 'k' command.",
				5: "Write error.",
				6: "File open error.",
				7: "Wrong command line option.",
				8: "Not enough memory.",
				9: "File create error",
				10: "No files matching the specified mask and options were found.",
				11: "Wrong password.",
				255: "User stopped the process.",
			}.get(data, "Unknown error")
		super(RarMenuScreen, self).extractDone(filename, data)


class UnpackInfoScreen(ArchiverInfoScreen):

	def __init__(self, session, list, sourceDir, filename):
		super(UnpackInfoScreen, self).__init__(session, list, sourceDir, filename)
		self.pname = pname
		self.pdesc = pdesc
		self.pversion = pversion
