from re import findall
from os.path import splitext
from subprocess import Popen, PIPE, STDOUT

from enigma import eConsoleAppContainer, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_HALIGN_CENTER, RT_VALIGN_CENTER
from Components.ActionMap import ActionMap
from Components.config import config
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryProgress
from Components.PluginComponent import plugins
from Components.Sources.StaticText import StaticText
from skin import fonts, parameters
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.BoundFunction import boundFunction
from Tools.Directories import shellquote, fileExists, resolveFilename, SCOPE_PLUGINS


COMMONINFO = (
	_("File Commander - generalised archive handler"),
	_("unpack archives"),
	"0.0-r1"
)


class ArchiverMenuScreen(Screen):
	ID_SHOW = 0
	ID_CURRENTDIR = 1
	ID_TARGETDIR = 2
	ID_DEFAULTDIR = 3
	ID_INSTALL = 4

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

	def __init__(self, session, sourcelist, targetlist, addoninfo=None):

		addoninfo = addoninfo or COMMONINFO
		self.pname = addoninfo[0]
		self.pdesc = addoninfo[1]
		self.pversion = addoninfo[2]

		self.SOURCELIST = sourcelist
		self.TARGETLIST = targetlist
		Screen.__init__(self, session)
		self.filename = self.SOURCELIST.getFilename()
		self.sourceDir = self.SOURCELIST.getCurrentDirectory()
		self.targetDir = self.TARGETLIST.getCurrentDirectory() or "/tmp/"
		self.list = []
		self.commands = {}
		self.errlog = ""

		self.chooseMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		font = fonts.get("FileList", ("Regular", 20, 25))
		self.chooseMenuList.l.setFont(0, gFont(font[0], font[1]))
		self.chooseMenuList.l.setItemHeight(font[2])
		self["list_left"] = self.chooseMenuList

		self.chooseMenuList2 = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList2.l.setFont(0, gFont(font[0], font[1]))
		self.chooseMenuList2.l.setItemHeight(font[2])
		self["unpacking"] = self.chooseMenuList2
		self["unpacking"].selectionEnabled(0)

		self["list_left_head"] = Label("%s%s" % (self.sourceDir, self.filename))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")

		self["setupActions"] = ActionMap(["SetupActions"], {
			"cancel": self.cancel,
			"save": self.ok,
			"ok": self.ok,
		}, -2)

		self.onLayoutFinish.append(self.onLayout)

	def onLayout(self):
		self.setTitle(self.pname)
		self.chooseMenuList.setList(list(map(self.ListEntry, self.list)))

	def getPathBySelectId(self, selectId):
		if selectId == self.ID_CURRENTDIR:
			return self.sourceDir
		elif selectId == self.ID_TARGETDIR:
			return self.targetDir
		elif selectId == self.ID_DEFAULTDIR:
			return config.usage.default_path.value

	def initList(self, firstElement=None):
		if firstElement:
			self.list.append((firstElement, self.ID_SHOW))
		self.list.append((_("Unpack to current folder"), self.ID_CURRENTDIR))
		self.list.append((_("Unpack to %s") % self.targetDir, self.ID_TARGETDIR))
		self.list.append((_("Unpack to %s") % config.usage.default_path.value, self.ID_DEFAULTDIR))

	def ListEntry(self, entry):
		x, y, w, h = parameters.get("FileListName", (10, 0, 1180, 25))
		x = 10
		w = self["list_left"].l.getItemSize().width()
		return [
			entry,
			MultiContentEntryText(pos=(x, y), size=(w - x, h), font=0, flags=RT_HALIGN_LEFT, text=entry[0])
		]

	def UnpackListEntry(self, entry):
		# print "[ArchiverMenuScreen] UnpackListEntry", entry
		currentProgress = int(float(100) / float(int(100)) * int(entry))
		progpercent = str(currentProgress) + "%"
		x, y, w, h = parameters.get("FileListMultiName", (60, 0, 1180, 25))
		x2 = x
		x = 10
		w = self["list_left"].l.getItemSize().width()
		return [
			entry,
			MultiContentEntryProgress(pos=(x + x2, y + int(h / 3)), size=(w - (x + x2), int(h / 3)), percent=int(currentProgress), borderWidth=1),
			MultiContentEntryText(pos=(x, y), size=(x2, h), font=0, flags=RT_HALIGN_LEFT, text=str(progpercent))
		]

	def ok(self):
		selectName = self["list_left"].getCurrent()[0][0]
		self.selectId = self["list_left"].getCurrent()[0][1]
		print("[ArchiverMenuScreen] Select: %s %s" % (selectName, self.selectId))
		self.unpackModus(self.selectId)

	def unpackModus(self, selectid):
		return

	# unpackPopen and unpackEConsoleApp run unpack and info
	# commands for the specific archive unpackers.

	def unpackPopen(self, cmd, infoScreen, addoninfo):

		# cmd is either a string or a list/tuple
		# containing the command name and arguments.
		# It it's a string, it's passed to the shell
		# for interpretation. If it's a tuple/list,
		# it's effectively run by execvp().
		# infoScreen is used by to display the output
		# of the command. It must have an API compatible
		# with ArchiverInfoScreen.

		print("[ArchiverMenuScreen] unpackPopen %s" % cmd)
		try:
			shellcmd = type(cmd) not in (tuple, list)
			p = Popen(cmd, shell=shellcmd, stdout=PIPE, stderr=PIPE, text=True)
		except OSError as ex:
			cmdname = cmd.split()[0] if shellcmd else cmd[0]
			msg = _("Can not run %s: %s.\n%s may be in a plugin that is not installed.") % (cmdname, ex.strerror, cmdname)
			print("[ArchiverMenuScreen] %s" % msg)
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR)
			return
		stdout, stderr = p.communicate()
		output = []
		output.append(stdout.split("\n"))
		output.append(stderr.split("\n"))
		if stdout and stderr:
			output[1].append("----------")
		self.extractlist = [(l,) for l in output[1] + output[0]]
		if not self.extractlist:
			self.extractlist = [(_("No files found."),)]
		self.session.open(infoScreen, self.extractlist, self.sourceDir, self.filename, addoninfo)

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

		print("[ArchiverMenuScreen] unpackEConsoleApp %s" % cmd)
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
		print("[ArchiverMenuScreen] extractDone %s" % data)
		if data:
			messagetype = MessageBox.TYPE_ERROR
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
			messagetype = MessageBox.TYPE_INFO
			timeout = 8
			message = _("%s successfully extracted.") % filename
		self.session.open(MessageBox, message, messagetype, timeout=timeout)

	def logerrs(self, data):
		if isinstance(data, bytes):
			data = data.decode()
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

	def __init__(self, session, liste, sourceDir, filename, addoninfo=None):

		addoninfo = addoninfo or COMMONINFO
		self.pname = addoninfo[0]
		self.pdesc = addoninfo[1]
		self.pversion = addoninfo[2]

		self.list = liste
		self.sourceDir = sourceDir
		self.filename = filename
		Screen.__init__(self, session)

		self.chooseMenuList = MenuList([], content=eListboxPythonMultiContent)
		font = fonts.get("FileList", ("Regular", 20, 25))
		self.chooseMenuList.l.setFont(0, gFont(font[0], font[1]))
		self.chooseMenuList.l.setItemHeight(font[2])
		self["list_left"] = self.chooseMenuList

		self["list_left_head"] = Label("%s%s" % (self.sourceDir, self.filename))

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")

		self["setupActions"] = ActionMap(["SetupActions"], {
			"cancel": self.cancel,
			"save": self.cancel,
			"ok": self.cancel,
		}, -2)

		self.onLayoutFinish.append(self.onLayout)

	def onLayout(self):
		self.setTitle(self.pname)
		if len(self.list) != 0:
			self.chooseMenuList.setList(list(map(self.ListEntry, self.list)))

	def ListEntry(self, entry):
		x, y, w, h = parameters.get("FileListName", (10, 0, 1180, 25))
		x = 10
		w = self["list_left"].l.getItemSize().width()
		flags = RT_HALIGN_LEFT
		if "Plugins.Extensions.FileCommander.unarchiver.UnpackInfoScreen" in repr(self):
			flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER
			y *= 2
		return [
			entry,
			MultiContentEntryText(pos=(x, int(y)), size=(w - x, h), font=0, flags=flags, text=entry[0])
		]

	def cancel(self):
		self.close()


class UnzipMenuScreen(ArchiverMenuScreen):
	ADDONINFO = (
		_("File Commander - unzip Addon"),
		_("unpack zip Files"),
		"0.3"
	)

	def __init__(self, session, sourcelist, targetlist):
		ArchiverMenuScreen.__init__(self, session, sourcelist, targetlist, addoninfo=self.ADDONINFO)
		self.skinname = ["UnzipMenuScreen", "ArchiverMenuScreen"]
		self.initList(_("Show contents of zip file"))

	def unpackModus(self, selectid):
		print("[UnzipMenuScreen] unpackModus %s" % selectid)
		if selectid == self.ID_SHOW:
			cmd = ("unzip", "-l", self.sourceDir + self.filename)
			self.unpackPopen(cmd, UnpackInfoScreen, self.ADDONINFO)
		else:
			cmd = ["unzip", "-o", self.sourceDir + self.filename, "-d"]
			cmd.append(self.getPathBySelectId(selectid))
			self.unpackEConsoleApp(cmd)


class UnpackInfoScreen(ArchiverInfoScreen):
	def __init__(self, session, liste, sourceDir, filename, addoninfo=None):
		ArchiverInfoScreen.__init__(self, session, liste, sourceDir, filename, addoninfo)
		self.skinname = ["UnpackInfoScreen", "ArchiverInfoScreen"]
		font = fonts.get("FileList", ("Console", 20, 30))
		self.chooseMenuList.l.setFont(0, gFont("Console", int(font[1] * 0.85)))


class RarMenuScreen(ArchiverMenuScreen):

	DEFAULT_PW = "2D1U3MP!"

	ADDONINFO = (
		_("File Commander - unrar Addon"),
		_("unpack Rar Files"),
		"0.3"
	)

	def __init__(self, session, sourcelist, targetlist):
		ArchiverMenuScreen.__init__(self, session, sourcelist, targetlist, addoninfo=self.ADDONINFO)
		self.skinname = ["RarMenuScreen", "ArchiverMenuScreen"]

		self.unrar = "unrar"
		self.defaultPW = self.DEFAULT_PW

		self.initList(_("Show contents of rar file"))

	def ok(self):
		selectName = self["list_left"].getCurrent()[0][0]
		self.selectId = self["list_left"].getCurrent()[0][1]
		print("[RarMenuScreen] Select: %s %s" % (selectName, self.selectId))
		self.checkPW(self.defaultPW)

	def checkPW(self, pwd):
		self.defaultPW = pwd
		print("[RarMenuScreen] Current pw: %s" % self.defaultPW)
		cmd = (self.unrar, "t", "-p" + self.defaultPW, self.sourceDir + self.filename)
		try:
			p = Popen(cmd, shell=False, stdout=PIPE, stderr=STDOUT, text=True)
		except OSError as ex:
			msg = _("Can not run %s: %s.\n%s may be in a plugin that is not installed.") % (cmd[0], ex.strerror, cmd[0])
			print("[RarMenuScreen] %s" % msg)
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR)
			return
		stdlog = p.stdout.read()
		if stdlog:
			print("[RarMenuScreen] checkPW stdout %s" % len(stdlog))
			print(stdlog)
			if "Corrupt file or wrong password." in stdlog:
				print("[RarMenuScreen] pw incorrect!")
				self.session.openWithCallback(self.setPW, VirtualKeyBoard, title=_("%s is password protected.") % self.filename + " " + _("Please enter password"), text="")
			else:
				print("[RarMenuScreen] pw correct!")
				self.unpackModus(self.selectId)

	def setPW(self, pwd):
		if pwd is None or pwd.strip() == "":
			self.defaultPW = self.DEFAULT_PW
		else:
			self.checkPW(pwd)

	def unpackModus(self, selectid):
		print("[RarMenuScreen] unpackModus %s" % selectid)
		if selectid == self.ID_SHOW:
			cmd = (self.unrar, "lb", "-p" + self.defaultPW, self.sourceDir + self.filename)
			self.unpackPopen(cmd, ArchiverInfoScreen, self.ADDONINFO)
		else:
			cmd = [self.unrar, "x", "-p" + self.defaultPW, self.sourceDir + self.filename, "-o+"]
			cmd.append(self.getPathBySelectId(selectid))
			self.unpackEConsoleApp(cmd, exePath=self.unrar, logCallback=self.log)

	def log(self, data):
		# print "[RarMenuScreen] log", data
		status = findall("(\d+)%", data)
		if status and status[0] not in self.ulist:
			self.ulist.append((status[0]))
			self.chooseMenuList2.setList(list(map(self.UnpackListEntry, status)))
			self["unpacking"].selectionEnabled(0)

		if "All OK" in data:
			self.chooseMenuList2.setList(list(map(self.UnpackListEntry, ["100"])))
			self["unpacking"].selectionEnabled(0)

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


class GunzipMenuScreen(ArchiverMenuScreen):
	ADDONINFO = (
		_("File Commander - gzip Addon"),
		_("unpack gzip Files"),
		"0.3"
	)

	def __init__(self, session, sourcelist, targetlist):
		ArchiverMenuScreen.__init__(self, session, sourcelist, targetlist, addoninfo=self.ADDONINFO)
		self.skinname = ["GunzipMenuScreen", "ArchiverMenuScreen"]
		self.initList()

	def unpackModus(self, selectid):
		print("[GunzipMenuScreen] unpackModus %s" % selectid)
		pathName = self.sourceDir + self.filename
		if selectid == self.ID_CURRENTDIR:
			cmd = ("gunzip", pathName)
		elif selectid in (self.ID_TARGETDIR, self.ID_DEFAULTDIR):
			baseName, ext = splitext(self.filename)
			if ext != ".gz":
				return
			dest = "%s%s" % (self.getPathBySelectId(id), baseName)
			cmd = "gunzip -c %s > %s && rm %s" % (shellquote(pathName), shellquote(dest), shellquote(pathName))
		self.unpackEConsoleApp(cmd)


class ipkMenuScreen(ArchiverMenuScreen):

	ADDONINFO = (
		_("File Commander - ipk Addon"),
		_("install/unpack ipk Files"),
		"0.3"
	)

	def __init__(self, session, sourcelist, targetlist):
		ArchiverMenuScreen.__init__(self, session, sourcelist, targetlist, addoninfo=self.ADDONINFO)
		self.skinname = ["ipkMenuScreen", "ArchiverMenuScreen"]
		self.list.append((_("Show contents of ipk file"), self.ID_SHOW))
		self.list.append((_("Install"), self.ID_INSTALL))

	def unpackModus(self, selectid):
		if selectid == self.ID_SHOW:
			# This is done in a subshell because using two
			# communicating Popen commands can deadlock on the
			# pipe output. Using communicate() avoids deadlock
			# on reading stdout and stderr from the pipe.
			fname = shellquote(self.sourceDir + self.filename)
			p = Popen("ar -t %s > /dev/null 2>&1" % fname, shell=True)
			if p.wait():
				cmd = "tar -xOf %s ./data.tar.gz | tar -tzf -" % fname
			else:
				cmd = "ar -p %s data.tar.gz | tar -tzf -" % fname
			self.unpackPopen(cmd, ArchiverInfoScreen, self.ADDONINFO)
		elif selectid == self.ID_INSTALL:
			self.ulist = []
			if fileExists("/usr/bin/opkg"):
				self.session.openWithCallback(self.doCallBack, Console, title=_("Installing Plugin ..."), cmdlist=(("opkg", "install", self.sourceDir + self.filename),))

	def doCallBack(self):
		if self.filename.startswith("enigma2-plugin-"):
			plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))


class TarMenuScreen(ArchiverMenuScreen):
	ADDONINFO = (
		_("File Commander - tar Addon"),
		_("unpack tar/compressed tar Files"),
		"0.3"
	)

	def __init__(self, session, sourcelist, targetlist):
		ArchiverMenuScreen.__init__(self, session, sourcelist, targetlist, addoninfo=self.ADDONINFO)
		self.skinname = ["TarMenuScreen", "ArchiverMenuScreen"]
		self.initList(_("Show contents of tar or compressed tar file"))

	def unpackModus(self, selectid):
		print("[TarMenuScreen] unpackModus %s" % selectid)
		if selectid == self.ID_SHOW:
			cmd = ("tar", "-tf", self.sourceDir + self.filename)
			self.unpackPopen(cmd, ArchiverInfoScreen, self.ADDONINFO)
		else:
			cmd = ["tar", "-xvf", self.sourceDir + self.filename, "-C"]
			cmd.append(self.getPathBySelectId(selectid))
			self.unpackEConsoleApp(cmd)
