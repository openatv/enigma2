from re import sub
from os.path import exists, isfile, splitext
from time import localtime

from enigma import eConsoleAppContainer, eTimer

from skin import parseColor
from Components.ActionMap import HelpableActionMap
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Directories import fileReadLines, fileWriteLines

MODULE_NAME = __name__.split(".")[-1]


# The cmdList must be a mixed list or tuple of strings or lists/tuples.
# Strings are executed by sh -c string, lists/tuples are executed by execvp(list[0], list).
#
class Console(Screen):
	def __init__(self, session, title=_("Console"), cmdlist=None, finishedCallback=None, closeOnSuccess=False, cmdList=None, showScripts=True, windowTitle=None):
		Screen.__init__(self, session, enableHelp=True)
		if windowTitle:
			title = windowTitle
		self.setTitle(title)
		if finishedCallback:
			print("[Console] Warning: The argument 'finishedCallback' is deprecated! Use 'openWithCallback' rather than 'open'.")
		if cmdList:
			cmdlist = cmdList
		self.cmdList = cmdlist
		self.finishedCallback = finishedCallback
		self.closeOnSuccess = closeOnSuccess
		self.showScripts = showScripts
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Hide"))
		self["key_yellow"] = StaticText()
		self["text"] = ConsoleScrollLabel()
		self["summary_description"] = StaticText()
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"ok": (self.keyCancel, _("Close the screen")),
			"cancel": (self.keyCancel, _("Close the screen")),
			"close": (self.keyCloseRecursive, _("Close the screen and exit all menus")),
			"red": (self.keyCancel, _("Close this screen")),
			"top": (self.keyTop, _("Move to first line / screen")),
			"pageUp": (self.keyPageUp, _("Move up a screen")),
			"up": (self.keyLineUp, _("Move up a line")),
			"down": (self.keyLineDown, _("Move down a line")),
			"pageDown": (self.keyPageDown, _("Move down a screen")),
			"bottom": (self.keyBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Console Actions"))
		self["hideAction"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyToggleHideShow, _("Hide/Show the console screen"), _("NOTE: While the console screen is hidden from view the buttons are still active. Pressing any enabled button will cause the screen to reappear but the button will not be actioned.")),
		}, prio=0, description=_("Console Actions"))
		self["saveAction"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keySaveLog, _("Save the log of the console messages to a file")),
		}, prio=0, description=_("Console Actions"))
		self["saveAction"].setEnabled(False)
		self.container = eConsoleAppContainer()  # We use this as the Console component does not produce command output in real time.
		self.container.dataAvail.append(self.dataAvail)
		self.container.appClosed.append(self.runFinished)
		self.timer = eTimer()
		self.timer.callback.append(self.timeout)
		self.baseTitle = self.getTitle()
		self.screenHidden = False
		self.cancelMessageBox = None
		self.errorOcurred = False
		self.run = 0
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.commandColorStart, self.commandColorEnd, self.scriptColorStart, self.scriptColorEnd = self["text"].getColors()
		if self.runCommand(self.cmdList[self.run]):  # Start of container application failed so we must call runFinished manually.
			self.runFinished(-1)

	def keyCancel(self, recursive=False):
		def cancelCallback(answer):
			if answer:
				self.container.kill()
				processCancel()

		def processCancel():
			# self.container.dataAvail.remove(self.dataAvail)  # This doesn't currently work at the C++ layer!
			# self.container.appClosed.remove(self.runFinished)  # This doesn't currently work at the C++ layer!
			del self.container.dataAvail[:]
			del self.container.appClosed[:]
			del self.container
			if recursive:
				self.close(True)
			else:
				self.close()

		self.stopTimer()
		if self.screenHidden:
			self.keyToggleHideShow()
		elif self.run == len(self.cmdList):
			processCancel()
		else:
			self.cancelMessageBox = self.session.openWithCallback(cancelCallback, MessageBox, _("Cancel execution?"), type=MessageBox.TYPE_YESNO, default=False, windowTitle=self.getTitle())

	def keyCloseRecursive(self):
		self.keyCancel(recursive=True)

	def keyToggleHideShow(self, forceShow=False):
		if forceShow or self.screenHidden:
			self.show()
		else:
			self.hide()
		self.screenHidden = not (self.screenHidden or forceShow)

	def keySaveLog(self):
		def saveLogCallback(answer=None):
			if answer:
				text = sub(r"\\c[0-9A-F]{8}", "", self["text"].getText())
				if not fileWriteLines(self.outputFile, text, source=MODULE_NAME):
					self.session.open(MessageBox, _("Error: Unable to write log file '%s'!") % self.outputFile, type=MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
				self["key_yellow"].setText("")

		self.stopTimer()
		localTime = localtime()
		self.outputFile = f"/tmp/{localTime[3]:02d}{localTime[4]:02d}{localTime[5]:02d}_console.txt"
		self.session.openWithCallback(saveLogCallback, MessageBox, f"{_("Save the commands and output to the log file?")}\n('{self.outputFile}')", type=MessageBox.TYPE_YESNO, default=True, windowTitle=self.getTitle())

	def keyTop(self):
		if self.screenHidden:
			self.keyToggleHideShow()
		else:
			self.stopTimer()
			self["text"].goTop()

	def keyPageUp(self):
		if self.screenHidden:
			self.keyToggleHideShow()
		else:
			self.stopTimer()
			self["text"].goPageUp()

	def keyLineUp(self):
		if self.screenHidden:
			self.keyToggleHideShow()
		else:
			self.stopTimer()
			self["text"].goLineUp()

	def keyLineDown(self):
		if self.screenHidden:
			self.keyToggleHideShow()
		else:
			self.stopTimer()
			self["text"].goLineDown()

	def keyPageDown(self):
		if self.screenHidden:
			self.keyToggleHideShow()
		else:
			self.stopTimer()
			self["text"].goPageDown()

	def keyBottom(self):
		if self.screenHidden:
			self.keyToggleHideShow()
		else:
			self.stopTimer()
			self["text"].goBottom()

	def runCommand(self, cmd):
		print(f"[Console] Running command {self.run + 1}: '{self.cmdList[self.run]}'.")
		self["text"].appendText(f"{self.commandColorStart}>>> {_("Running command %d: '%s'.") % (self.run + 1, self.cmdList[self.run])}{self.commandColorEnd}\n")
		if self.showScripts:
			cmdLine = cmd[0] if isinstance(cmd, (list, tuple)) else cmd.split()[0]
			if cmdLine.endswith((".sh", ".py")) and isfile(cmdLine):
				lines = fileReadLines(cmdLine, default=None, source=MODULE_NAME)
				if lines:
					self["text"].appendText(f"{self.scriptColorStart}>>> Command script '{cmdLine}' contents:\n{"\n".join(lines)}\n>>> End of script.{self.scriptColorEnd}\n")
		self["text"].appendText("\n")
		return self.container.execute(cmd[0], *cmd) if isinstance(cmd, (list, tuple)) else self.container.execute(cmd)

	def startRun(self, cmd):  # For compatibility with the current FSBLUpdater.  This code needs to be updated anyway as it uses the deprecated callback syntax!
		return self.runCommand(cmd)

	def dataAvail(self, data):
		if isinstance(data, bytes):
			data = data.decode()
		self["text"].appendText(data)

	def runFinished(self, retVal):
		if retVal:
			print(f"[Console] Running command {self.run + 1} finsihed with '{retVal}'.")
			self.errorOcurred = True
			self.keyToggleHideShow(True)
		self.run += 1
		if self.run != len(self.cmdList):
			if self.runCommand(self.cmdList[self.run]):  # Start of container application failed so we must call runFinished manually.
				self.runFinished(-1)
		else:
			self["key_red"].setText(_("Close"))
			self["key_green"].setText("")
			self["hideAction"].setEnabled(False)
			self["key_yellow"].setText(_("Save Log"))
			self["saveAction"].setEnabled(True)
			self.keyToggleHideShow(True)
			if self.cancelMessageBox:
				self.cancelMessageBox.close(None)
			text = ngettext("Command finished.", "Commands finished.", len(self.cmdList))
			self["text"].appendText(f"\n{self.commandColorStart}>>> {text}{self.commandColorEnd}\n")
			if not self.errorOcurred and not isinstance(self.closeOnSuccess, bool) and self.closeOnSuccess:
				self["text"].appendText(f"\n{self.commandColorStart}>>> {_("This window will automatically close in %d seconds.") % self.closeOnSuccess}{self.commandColorEnd}\n")
			self["summary_description"].setText(text)
			if self.finishedCallback and callable(self.finishedCallback):
				self.finishedCallback()
			if not self.errorOcurred and self.closeOnSuccess:
				if not isinstance(self.closeOnSuccess, bool):
					self.setTitle(f"{self.baseTitle} ({self.closeOnSuccess})")
					self.timer.start(1000)
				else:
					self.keyCancel()

	def timeout(self):
		self.timer.stop()
		self.closeOnSuccess -= 1
		if self.closeOnSuccess:
			self.timer.start(1000)
			self.setTitle(f"{self.baseTitle} ({self.closeOnSuccess})")
		else:
			self.keyCancel()

	def stopTimer(self):
		if self.closeOnSuccess:
			self.timer.stop()
			self.setTitle(self.baseTitle)


class ConsoleScrollLabel(ScrollLabel):
	def applySkin(self, desktop, parent):
		for attribute, value in self.skinAttributes[:]:
			match attribute:
				case "commandColor":
					self.skinAttributes.remove((attribute, value))
					self.commandColor = rf"\c{parseColor(value, 0x00FFFF00).argb():08X}"
				case "scriptColor":
					self.skinAttributes.remove((attribute, value))
					self.scriptColor = rf"\c{parseColor(value, 0x0000FFFF).argb():08X}"
		return ScrollLabel.applySkin(self, desktop, parent)

	def getColors(self):
		defaultColor = rf"\c{self.getForegroundColor():08X}"
		commandColorStart = self.commandColor if hasattr(self, "commandColor") else ""
		commandColorEnd = defaultColor if commandColorStart else ""
		scriptColorStart = self.scriptColor if hasattr(self, "scriptColor") else ""
		scriptColorEnd = defaultColor if scriptColorStart else ""
		return commandColorStart, commandColorEnd, scriptColorStart, scriptColorEnd
