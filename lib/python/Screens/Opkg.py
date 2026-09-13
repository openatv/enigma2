from os import listdir
from os.path import isdir, join

from enigma import eTimer

from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Opkg import OpkgComponent
from Components.ScrollLabel import ScrollLabel
from Components.SelectionList import SelectionList
from Components.Slider import Slider
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyboard
from Tools.Directories import fileReadLines, fileWriteLines

MODULE_NAME = __name__.split(".")[-1]


class IpkgInstaller(Screen):
	skin = """
		<screen name="IpkgInstaller" position="center,center" size="550,450" title="Install extensions" resolution="1280,720">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget name="list" position="5,50" size="540,360" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,410" zPosition="10" size="560,2" transparent="1" alphatest="on" />
			<widget source="introduction" render="Label" position="5,420" zPosition="10" size="550,30" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""

	def __init__(self, session, list):
		Screen.__init__(self, session)
		self.selectionList = SelectionList()
		self["list"] = self.selectionList
		p = 0
		if len(list):
			p = list[0].rfind("/")
			title = list[0][:p]
			self.title = ("%s %s %s") % (_("Install extensions"), _("from"), title)
		for listindex in range(len(list)):
			self.selectionList.addSelection(list[listindex][p + 1:], list[listindex], listindex, False)
		self.selectionList.sort()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Install"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText(_("Invert"))
		self["introduction"] = StaticText(_("Press OK to toggle the selection."))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"ok": self.selectionList.toggleSelection,
			"cancel": self.close,
			"red": self.close,
			"green": self.install,
			"blue": self.selectionList.toggleAllSelection
		}, prio=-1)

	def install(self):
		packages = self.selectionList.getSelectionsList()
		cmdList = [(OpkgComponent.CMD_UPDATE, None)]
		for item in packages:
			cmdList.append((OpkgComponent.CMD_INSTALL, {"package": item[1]}))
		self.session.open(Opkg, cmdList=cmdList)


class Opkg(Screen):
	def __init__(self, session, cmdList=None):
		if not cmdList:
			cmdList = []
		Screen.__init__(self, session)
		self.setTitle(_("Installing Software..."))

		self.cmdList = cmdList

		self.sliderPackages = {}

		self.slider = Slider(0, len(cmdList))
		self["slider"] = self.slider
		self.activityslider = Slider(0, 100)
		self["activityslider"] = self.activityslider
		self.status = Label(_("Preparing... Please wait"))
		self["status"] = self.status
		self.package = Label()
		self["package"] = self.package

		self["log"] = ScrollLabel()
		self["key_red"] = StaticText()
		self["key_blue"] = StaticText()

		self.packages = 0
		self.error = 0
		self.processed_packages = []

		self.activity = 0
		self.activityTimer = eTimer()
		self.activityTimer.callback.append(self.doActivityTimer)
		#self.activityTimer.start(100, False)

		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)

		self.runningCmd = None
		self.commandOutput = ""
		self.showStatus = True
		self.runNextCmd()

		self["logactions"] = HelpableActionMap(self, ["NavigationActions"], {
			"top": (self["log"].moveTop, _("Move to first line / screen")),
			"pageUp": (self["log"].pageUp, _("Move up a screen")),
			"up": (self["log"].moveUp, _("Move up a line")),
			"down": (self["log"].moveDown, _("Move down a line")),
			"pageDown": (self["log"].pageDown, _("Move down a screen")),
			"bottom": (self["log"].moveBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Opkg Log Actions"))
		self["logactions"].setEnabled(False)

		self["actions"] = HelpableActionMap(self, ["CancelSaveActions", "OkActions", "ColorActions"], {
			"cancel": (self.keyCancel, _("Close the screen")),
			"close": (self.closeRecursive, _("Close the screen and exit all menus")),
			"ok": (self.keyCancel, _("Close the screen")),
			"red": (self.keyCancel, _("Close the screen")),
			"blue": (self.keyLog, _("Toggle Log and Status")),
		}, prio=0, description=_("Opkg Actions"))

	def runNextCmd(self):
		if self.runningCmd is None:
			self.runningCmd = 0
		else:
			self.runningCmd += 1
		#print(len(self.cmdList), self.runningCmd)
		if len(self.cmdList) - 1 < self.runningCmd:
			self.activityslider.setValue(0)
			self.slider.setValue(len(self.cmdList))

			self.package.setText("")
			self.status.setText(ngettext("Done - Installed, upgraded or removed %d package (%s)", "Done - Installed, upgraded or removed %d packages (%s)", self.packages) % (self.packages, ngettext("with %d error", "with %d errors", self.error) % self.error))
			self["key_red"].setText(_("Close"))
			self["key_blue"].setText(_("Log"))
			return False
		else:
			cmd = self.cmdList[self.runningCmd]
			self.slider.setValue(self.runningCmd)
			self.opkg.startCmd(cmd[0], args=cmd[1])
			self.startActivityTimer()

	def doActivityTimer(self):
		if not self.opkg.isRunning():
			self.stopActivityTimer()
		else:
			self.activity += 1
			if self.activity == 100:
				self.activity = 0
			self.activityslider.setValue(self.activity)

	def startActivityTimer(self):
		self.activityTimer.start(100, False)

	def stopActivityTimer(self):
		self.activityTimer.stop()

	def opkgCallback(self, event, param):
		if event == OpkgComponent.EVENT_DOWNLOAD:
			self.status.setText(_("Downloading"))
		elif event == OpkgComponent.EVENT_UPGRADE:
			if param in self.sliderPackages:
				self.slider.setValue(self.sliderPackages[param])
			self.package.setText(param)
			self.status.setText(_("Updating"))
			if param not in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == OpkgComponent.EVENT_INSTALL:
			self.package.setText(param)
			self.status.setText(_("Installing"))
			if param not in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == OpkgComponent.EVENT_REMOVE:
			self.package.setText(param)
			self.status.setText(_("Removing"))
			if param not in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == OpkgComponent.EVENT_CONFIGURING:
			self.package.setText(param)
			self.status.setText(_("Configuring"))
		elif event == OpkgComponent.EVENT_ERROR:
			self.error += 1
			self.commandOutput += self.opkg.cache
			self.runNextCmd()
		elif event == OpkgComponent.EVENT_DONE:
			self.commandOutput += self.opkg.cache
			self.runNextCmd()
		elif event == OpkgComponent.EVENT_MODIFIED:
			self.session.openWithCallback(
				self.modificationCallback,
				MessageBox,
				_("Configuration file '%s' has been modified since it was installed, would you like to keep the modified version?") % param
			)

	def modificationCallback(self, res):
		self.opkg.write(res and "N" or "Y")

	def closeRecursive(self):
		if not self.opkg.isRunning():
			self.close(True)

	def keyCancel(self):
		if not self.opkg.isRunning():
			self.close()

	def keyLog(self):
		if self.showStatus:
			self["logactions"].setEnabled(True)
			self["key_blue"].setText(_("Status"))
			self["log"].show()
			self["log"].setText(self.commandOutput)
			self["package"].hide()
			self["slider"].hide()
			self["activityslider"].hide()
			self["status"].hide()
			self.showStatus = False
		else:
			self["logactions"].setEnabled(False)
			self["key_blue"].setText(_("Log"))
			self["log"].hide()
			self["package"].show()
			self["slider"].show()
			self["activityslider"].show()
			self["status"].show()


class PackageFeedSelection(Screen):
	PACKAGE_PATH = "/etc/opkg/"
	skin = """
	<screen name="PackageFeedSelection" title="Package Feed Selection" position="center,center" size="700,400" resolution="1280,720">
		<widget name="feeds" position="10,10" size="e-20,e-70" font="Regular;20" itemHeight="25" />
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-100,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True, mandatoryWidgets=["feeds"])
		self.setTitle(_("Select Upgrade Source To Edit"))
		feedList = []
		if isdir(self.PACKAGE_PATH):
			for file in sorted(listdir(self.PACKAGE_PATH)):
				if file.endswith(".conf") and file not in ("arch.conf", "opkg.conf"):
					feedList.append(file)
		self["feeds"] = MenuList(feedList)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Edit") if feedList else "")
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"ok": (self.keyOk, _("Edit the currently highlighted feed")),
			"cancel": (self.close, _("Close the screen")),
			"red": (self.close, _("Close the screen")),
			"green": (self.keyOk, _("Edit the currently highlighted feed"))
		}, prio=0, description=_("Package Feed Editor Actions"))
		self["actions"].setEnabledAction("ok", feedList != [])
		self["actions"].setEnabledAction("green", feedList != [])

	def keyOk(self):
		self.session.open(PackageFeedEditor, join(self.PACKAGE_PATH, self["feeds"].getCurrent()))


class PackageFeedEditor(VirtualKeyboard):
	def __init__(self, session, configFile=None):
		self.configFile = configFile
		self.lines = fileReadLines(configFile, default=[], source=MODULE_NAME) if configFile else []
		VirtualKeyboard.__init__(self, session, title=_("Edit the feed URL:"), text=self.lines[0] if self.lines else "", style=VirtualKeyboard.VKB_SAVE_ICON, windowTitle=_("Package Feed Editor"))

	def save(self):  # This is a redefinition of the method in VirtualKeyboard.
		self.smsGotChar()  # Commit any pending SMS character before the text is read.
		text = self["text"].getText().replace(self.TAB_GLYPH, "\t")
		if text and self.configFile:
			if fileWriteLines(self.configFile, [text] + self.lines[1:], source=MODULE_NAME) == 0:  # Only the first line is edited, keep the others.
				self.session.open(MessageBox, _("Error: There was a problem writing '%s'!") % self.configFile, MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
				return  # Keep the screen open so the edit is not lost.
		VirtualKeyboard.save(self)
