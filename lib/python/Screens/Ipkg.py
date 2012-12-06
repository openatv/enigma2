from Components.ActionMap import ActionMap
from Components.Ipkg import IpkgComponent
from Components.Label import Label
from Components.Slider import Slider
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from enigma import eTimer

class Ipkg(Screen):
	def __init__(self, session, cmdList = []):
		Screen.__init__(self, session)

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

		self.packages = 0
		self.error = 0
		self.processed_packages = []

		self.activity = 0
		self.activityTimer = eTimer()
		self.activityTimer.callback.append(self.doActivityTimer)
		#self.activityTimer.start(100, False)

		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)

		self.runningCmd = None
		self.runNextCmd()

		self["actions"] = ActionMap(["WizardActions"],
		{
			"ok": self.exit,
			"back": self.exit
		}, -1)

	def runNextCmd(self):
		if self.runningCmd is None:
			self.runningCmd = 0
		else:
			self.runningCmd += 1
		print len(self.cmdList), self.runningCmd
		if len(self.cmdList) - 1 < self.runningCmd:
			self.activityslider.setValue(0)
			self.slider.setValue(len(self.cmdList))

			self.package.setText("")
			self.status.setText(ngettext("Done - Installed, upgraded or removed %d package (%s)", "Done - Installed, upgraded or removed %d packages (%s)", self.packages) % (self.packages, ngettext("with %d error", "with %d errors", self.error) % self.error))
			return False
		else:
			cmd = self.cmdList[self.runningCmd]
			self.slider.setValue(self.runningCmd)
			self.ipkg.startCmd(cmd[0], args = cmd[1])
			self.startActivityTimer()

	def doActivityTimer(self):
		if not self.ipkg.isRunning():
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

	def ipkgCallback(self, event, param):
		if event == IpkgComponent.EVENT_DOWNLOAD:
			self.status.setText(_("Downloading"))
		elif event == IpkgComponent.EVENT_UPGRADE:
			if self.sliderPackages.has_key(param):
				self.slider.setValue(self.sliderPackages[param])
			self.package.setText(param)
			self.status.setText(_("Upgrading"))
			if not param in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == IpkgComponent.EVENT_INSTALL:
			self.package.setText(param)
			self.status.setText(_("Installing"))
			if not param in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == IpkgComponent.EVENT_REMOVE:
			self.package.setText(param)
			self.status.setText(_("Removing"))
			if not param in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == IpkgComponent.EVENT_CONFIGURING:
			self.package.setText(param)
			self.status.setText(_("Configuring"))
		elif event == IpkgComponent.EVENT_ERROR:
			self.error += 1
		elif event == IpkgComponent.EVENT_DONE:
			self.runNextCmd()
		elif event == IpkgComponent.EVENT_MODIFIED:
			self.session.openWithCallback(
				self.modificationCallback,
				MessageBox,
				_("A configuration file (%s) was modified since Installation.\nDo you want to keep your version?") % (param)
			)

	def modificationCallback(self, res):
		self.ipkg.write(res and "N" or "Y")

	def exit(self):
		if not self.ipkg.isRunning():
			self.close()
