from enigma import eTimer

from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.Opkg import OpkgComponent
from Components.ScrollLabel import ScrollLabel
from Components.Slider import Slider
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen


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
