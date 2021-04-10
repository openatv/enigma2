#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from Screens.MessageBox import MessageBox
from Components.Label import Label
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Tools.BoundFunction import boundFunction
from Components.MultiContent import MultiContentEntryText, MultiContentEntryProgress
from enigma import eConsoleAppContainer, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_HALIGN_CENTER, RT_VALIGN_CENTER
import subprocess
import skin

pname = _("File Commander - generalised archive handler")
pdesc = _("unpack archives")
pversion = "0.0-r1"

class ArchiverMenuScreen(Screen):
	skin = """
		<screen position="40,80" size="1200,600" title="" >
			<widget name="list_left_head" position="10,10" size="1180,60" font="Regular;20" foregroundColor="#00fff000"/>
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

		self.pname = pname
		self.pdesc = pdesc
		self.pversion = pversion

		self.SOURCELIST = sourcelist
		self.TARGETLIST = targetlist
		Screen.__init__(self, session)
		self.filename = self.SOURCELIST.getFilename()
		self.sourceDir = self.SOURCELIST.getCurrentDirectory()
		self.targetDir = self.TARGETLIST.getCurrentDirectory() or '/tmp/'
		self.list = []

		self.commands = {}

		self.errlog = ""

		self.chooseMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		font = skin.fonts.get("FileList", ("Regular", 20, 25))
		self.chooseMenuList.l.setFont(0, gFont(font[0], font[1]))
		self.chooseMenuList.l.setItemHeight(font[2])
		self['list_left'] = self.chooseMenuList

		self.chooseMenuList2 = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList2.l.setFont(0, gFont(font[0], font[1]))
		self.chooseMenuList2.l.setItemHeight(font[2])
		self['unpacking'] = self.chooseMenuList2
		self['unpacking'].selectionEnabled(0)

		self["list_left_head"] = Label("%s%s" % (self.sourceDir, self.filename))

		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("OK"))
		self["key_yellow"] = Label("")
		self["key_blue"] = Label("")

		self["setupActions"] = ActionMap(["SetupActions"], {
			"cancel": self.cancel,
			"save": self.ok,
			"ok": self.ok,
		}, -2)

		self.onLayoutFinish.append(self.onLayout)

	def onLayout(self):
		self.setTitle(self.pname)
		self.chooseMenuList.setList(map(self.ListEntry, self.list))

	def ListEntry(self, entry):
		x, y, w, h = skin.parameters.get("FileListName",(10, 0, 1180, 25))
		x = 10
		w = self['list_left'].l.getItemSize().width()
		return [
			entry,
			MultiContentEntryText(pos=(x, y), size=(w - x, h), font=0, flags=RT_HALIGN_LEFT, text=entry[0])
		]

	def UnpackListEntry(self, entry):
		# print "[ArchiverMenuScreen] UnpackListEntry", entry
		currentProgress = int(float(100) / float(int(100)) * int(entry))
		progpercent = str(currentProgress) + "%"
		x, y, w, h = skin.parameters.get("FileListMultiName",(60, 0, 1180, 25))
		x2 = x
		x = 10
		w = self['list_left'].l.getItemSize().width()
		return [
			entry,
			MultiContentEntryProgress(pos=(x + x2, y + int(h / 3)), size=(w - (x + x2), int(h / 3)), percent=int(currentProgress), borderWidth=1),
			MultiContentEntryText(pos=(x, y), size=(x2, h), font=0, flags=RT_HALIGN_LEFT, text=str(progpercent))
		]

	def ok(self):
		selectName = self['list_left'].getCurrent()[0][0]
		self.selectId = self['list_left'].getCurrent()[0][1]
		print "[ArchiverMenuScreen] Select:", selectName, self.selectId
		self.unpackModus(self.selectId)

	def unpackModus(self, id):
		return

	# unpackPopen and unpackEConsoleApp run unpack and info
	# commands for the specific archive unpackers.

	def unpackPopen(self, cmd, infoScreen):

		# cmd is either a string or a list/tuple
		# containing the command name and arguments.
		# It it's a string, it's passed to the shell
		# for interpretation. If it's a tuple/list,
		# it's effectively run by execvp().
		# infoScreen is used by to display the output
		# of the command. It must have an API compatible
		# with ArchiverInfoScreen.

		print "[ArchiverMenuScreen] unpackPopen", cmd
		try:
			shellcmd = type(cmd) not in (tuple, list)
			p = subprocess.Popen(cmd, shell=shellcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		except OSError as ex:
			cmdname = cmd.split()[0] if shellcmd else cmd[0]
			msg = _("Can not run %s: %s.\n%s may be in a plugin that is not installed.") % (cmdname, ex.strerror, cmdname)
			print "[ArchiverMenuScreen]", msg
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR)
			return
		output = map(str.splitlines, p.communicate())
		if output[0] and output[1]:
			output[1].append("----------")
		self.extractlist = [(l,) for l in output[1] + output[0]]
		if not self.extractlist:
			self.extractlist = [(_("No files found."),)]
		self.session.open(infoScreen, self.extractlist, self.sourceDir, self.filename)

	def unpackEConsoleApp(self, cmd, exePath=None, logCallback=None):

		# cmd is either a string or a list/tuple
		# containing the command name and arguments.
		# It it's a string, it's passed to the shell
		# for interpretation. If it's a tuple/list,
		# it's effectively run by execvp().
		# exePath is the optional full pathname of the
		# command, otherwise a search of $PATH is used
		# to find the command. Only used if cmd is a
		# list/tuple
		# logCallback is used to update the command
		# progress indicator using the command output
		# (see unrar.py)

		print "[ArchiverMenuScreen] unpackEConsoleApp", cmd
		self.errlog = ""
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(boundFunction(self.extractDone, self.filename))
		if logCallback is not None:
			self.container.stdoutAvail.append(self.log)
		self.container.stderrAvail.append(self.logerrs)
		self.ulist = []
		if type(cmd) in (tuple, list):
			exe = exePath or cmd[0]
			self.container.execute(exe, *cmd)
		else:
			self.container.execute(cmd)

	def extractDone(self, filename, data):
		print "[ArchiverMenuScreen] extractDone", data
		if data:
			type = MessageBox.TYPE_ERROR
			timeout = 15
			message = _("%s - extraction errors.") % filename
			if data == -1:
				self.errlog = self.errlog.rstrip()
				self.errlog += "\nTerminated by a signal"
			if self.errlog:
				self.errlog = self.errlog.strip()
				message += "\n----------\n" + self.errlog
			self.errlog = ""
		else:
			type = MessageBox.TYPE_INFO
			timeout = 8
			message = _("%s successfully extracted.") % filename
		self.session.open(MessageBox, message, type, timeout=timeout)

	def logerrs(self, data):
		self.errlog += data

	def cancel(self):
		self.close(False)

class ArchiverInfoScreen(Screen):
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

		self.pname = pname
		self.pdesc = pdesc
		self.pversion = pversion

		self.list = list
		self.sourceDir = sourceDir
		self.filename = filename
		Screen.__init__(self, session)

		self.chooseMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		font = skin.fonts.get("FileList", ("Regular", 20, 25))
		self.chooseMenuList.l.setFont(0, gFont(font[0], font[1]))
		self.chooseMenuList.l.setItemHeight(font[2])
		self['list_left'] = self.chooseMenuList

		self["list_left_head"] = Label("%s%s" % (self.sourceDir, self.filename))

		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("OK"))
		self["key_yellow"] = Label("")
		self["key_blue"] = Label("")

		self["setupActions"] = ActionMap(["SetupActions"], {
			"cancel": self.cancel,
			"save": self.cancel,
			"ok": self.cancel,
		}, -2)

		self.onLayoutFinish.append(self.onLayout)

	def onLayout(self):
		self.setTitle(self.pname)
		if len(self.list) != 0:
			self.chooseMenuList.setList(map(self.ListEntry, self.list))

	def ListEntry(self, entry):
		x, y, w, h = skin.parameters.get("FileListName",(10, 0, 1180, 25))
		x = 10
		w = self['list_left'].l.getItemSize().width()
		flags = RT_HALIGN_LEFT
		if 'Plugins.Extensions.FileCommander.addons.unzip.UnpackInfoScreen' in `self`:
			flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER
			y *= 2
		return [
			entry,
			MultiContentEntryText(pos=(x, int(y)), size=(w - x, h), font=0, flags=flags, text=entry[0])
		]

	def cancel(self):
		self.close()
