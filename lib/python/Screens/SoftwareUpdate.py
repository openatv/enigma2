from json import load
from os.path import exists
from urllib.request import urlopen

from enigma import eTimer

from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.Label import Label
from Components.Opkg import OpkgComponent
from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel
from Components.Slider import Slider
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.Screen import Screen, ScreenSummary
from Screens.Standby import QUIT_REBOOT, TryQuitMainloop
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap


class SoftwareUpdate(Screen, ProtectedScreen):
	FEED_UNKNOWN = 0
	FEED_DISABLED = 1
	FEED_UNSTABLE = 2
	FEED_STABLE = 3

	skin = """
	<screen name="SoftwareUpdate" title="Software Update" position="center,center" size="750,560" resolution="1280,720">
		<widget name="traffic_off" position="0,0" size="36,97" alphatest="blend" pixmap="icons/traffic_off.png" scale="1" />
		<widget name="traffic_red" position="0,0" size="36,97" alphatest="blend" pixmap="icons/traffic_red.png" scale="1" />
		<widget name="traffic_yellow" position="0,0" size="36,97" alphatest="blend" pixmap="icons/traffic_yellow.png" scale="1" />
		<widget name="traffic_green" position="0,0" size="36,97" alphatest="blend" pixmap="icons/traffic_green.png" scale="1" />
		<widget name="feedstatus_off" position="50,36" size="250,30" font="Regular;20" transparent="1" verticalAlignment="center" />
		<widget name="feedstatus_red" position="50,4" size="250,30" font="Regular;20" transparent="1" verticalAlignment="center" />
		<widget name="feedstatus_yellow" position="50,36" size="250,30" font="Regular;20" transparent="1" verticalAlignment="center" />
		<widget name="feedstatus_green" position="50,68" size="250,30" font="Regular;20" transparent="1" verticalAlignment="center" />
		<widget name="package_text" position="330,0" size="320,30" font="Regular;25" transparent="1" verticalAlignment="center" />
		<widget name="package_count" position="660,0" size="90,30" font="Regular;25" horizontalAlignment="right" transparent="1" verticalAlignment="center" />
		<widget name="feedmessage" position="330,40" size="420,40" font="Regular;20" transparent="1" verticalAlignment="center" />
		<widget name="activity" position="330,92" size="420,5" />
		<widget source="list" render="Listbox" position="0,110" size="750,400" scrollbarMode="showOnDemand">
			<templates>
				<template name="Default" fonts="Regular;22,Regular;15" itemHeight="50" itemWidth="750">
					<mode name="default">
						<text index="Package" position="10,0" size="660,30" font="0" horizontalAlignment="left" verticalAlignment="center" />
						<text index="Versions" position="30,30" size="640,20" font="1" horizontalAlignment="left" verticalAlignment="center" />
						<pixmap index="UpgradeIcon" position="680,0" size="48,48" alpha="blend" scale="centerScaled" />
						<pixmap index="Divider" position="0,48" size="750,2" alpha="blend" scale="centerScaled" />
					</mode>
				</template>
			</templates>
		</widget>
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="380,e-40" size="180,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-90,e-40" size="90,40" backgroundColor="key_back" font="Regular;20" conditional="key_help" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, *args):
		Screen.__init__(self, session, enableHelp=True)
		ProtectedScreen.__init__(self)
		self.setTitle(_("Software Update"))
		self.onCheckTrafficLight = []
		self.updateList = []
		indexNames = {
			"Package": 0,
			"OldVersion": 1,
			"NewVersion": 6,
			"Versions": 2,
			"UpgradeText": 3,
			"UpgradeIcon": 4,
			"Divider": 5
		}
		self["list"] = List(self.updateList, enableWrapAround=True, indexNames=indexNames)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["traffic_off"] = Pixmap()
		self["traffic_red"] = Pixmap()
		self["traffic_red"].hide()
		self["traffic_yellow"] = Pixmap()
		self["traffic_yellow"].hide()
		self["traffic_green"] = Pixmap()
		self["traffic_green"].hide()
		self["feedstatus_off"] = Label(_("Status unavailable!"))
		self["feedstatus_off"].hide()
		self["feedstatus_red"] = Label(f"< {_("Feed disabled!")}")
		self["feedstatus_red"].hide()
		self["feedstatus_yellow"] = Label(f"< {_("Feed unstable!")}")
		self["feedstatus_yellow"].hide()
		self["feedstatus_green"] = Label(f"< {_("Feed stable.")}")
		self["feedstatus_green"].hide()
		self["feedmessage"] = Label()
		self["package_text"] = Label(_("Updates available:"))
		self["package_count"] = Label("?")
		self["activity"] = Slider(0, 100)
		cancelMsg = _("Cancel / Close the software update screen")
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"cancel": (self.keyCancel, cancelMsg),
			"red": (self.keyCancel, cancelMsg),
			"top": (self["list"].goTop, _("Move to first line / screen")),
			"pageUp": (self["list"].goPageUp, _("Move up a page / screen")),
			"up": (self["list"].goLineUp, _("Move up a line")),
			"down": (self["list"].goLineDown, _("Move down a line")),
			"pageDown": (self["list"].goPageDown, _("Move down a page / screen")),
			"bottom": (self["list"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Software Update Actions"))
		updateMsg = _("Proceed with the update")
		self["updateActions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"ok": (self.keyUpdate, updateMsg),
			"green": (self.keyUpdate, updateMsg)
		}, prio=0, description=_("Software Update Actions"))
		self["updateActions"].setEnabled(False)
		self["refreshActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyRefresh, _("Refresh the update-able package list"))
		}, prio=0, description=_("Software Update Actions"))
		self["refreshActions"].setEnabled(False)
		self.activity = 0
		self.feedState = self.FEED_UNKNOWN
		self.updateFlag = True
		self.packageCount = 0
		self.feedOnline = False
		self.timer = eTimer()
		self.timer.callback.append(self.timeout)
		self.timer.callback.append(self.checkTrafficLight)
		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)
		self.onLayoutFinish.append(self.layoutFinished)

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and \
			(not config.ParentalControl.config_sections.main_menu.value and not config.ParentalControl.config_sections.configuration.value or hasattr(self.session, "infobar") and self.session.infobar is None) and \
			config.ParentalControl.config_sections.software_update.value

	def timeout(self):
		if self.activity < 0:
			self.timer.stop()
			self["activity"].hide()
		else:
			self.activity += 1
			if self.activity == 100:
				self.activity = 0
			self["activity"].setValue(self.activity)
			self.timer.start(100, True)

	def checkTrafficLight(self):
		self.timer.callback.remove(self.checkTrafficLight)
		try:
			# status = dict(load(urlopen(f"{BoxInfo.getItem("feedsurl")}/{BoxInfo.getItem("model")}.php", timeout=5)))
			# message = status.get("message")
			# status = status.get("status")
			status = ""
			message = ""
			boxName = BoxInfo.getItem("BoxName")
			with urlopen(f"https://ampel.mynonpublic.com/status/index.php?boxname={boxName}", timeout=10) as fd:
				tmpStatus = fd.read()
				if b"rot.png" in tmpStatus:
					status = "YELLOW" if exists("/etc/.beta") else "RED"
				elif b"gelb.png" in tmpStatus:
					status = "YELLOW"
				elif b"gruen.png" in tmpStatus:
					status = "GREEN"
			self["traffic_off"].hide()
			if status == "RED":
				self["traffic_red"].show()
				self["feedstatus_red"].show()
				self.feedState = self.FEED_DISABLED
			elif status == "YELLOW":
				self["traffic_yellow"].show()
				self["feedstatus_yellow"].show()
				self.feedState = self.FEED_UNSTABLE
			elif status == "GREEN":
				self["traffic_green"].show()
				self["feedstatus_green"].show()
				self.feedState = self.FEED_STABLE
			if message:
				self["feedmessage"].setText(_(message))
		except Exception as err:
			print(f"[SoftwareUpdate] Error: Unable to get server status!  ({str(err)})")
			self["feedstatus_off"].show()
		for callback in self.onCheckTrafficLight:
			callback()

	def opkgCallback(self, event, parameter):
		if self.updateFlag:
			if event == OpkgComponent.EVENT_UPDATED and "openatv-all" in parameter:
				self.feedOnline = True
			if event == OpkgComponent.EVENT_ERROR and self.feedOnline:  # Suppress error if openatv-all feed is online.
				event = OpkgComponent.EVENT_DONE
		if event == OpkgComponent.EVENT_ERROR:
			self.setStatus("error")
			self.activity = -1
		elif event == OpkgComponent.EVENT_DONE:
			if self.updateFlag:
				self.updateFlag = False
				self.opkg.startCmd(OpkgComponent.CMD_UPGRADE_LIST)
			else:
				self.updateList = []
				fetchedList = self.opkg.getFetchedList()
				count = len(fetchedList)
				if count > 0:
					upgradeablePng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/upgradeable.png"))
					divPng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
					for fetched in fetchedList:
						oldVer = fetched[1] if fetched[1] else _("Current version unknown")
						newVer = fetched[2] if fetched[2] else _("Updated version unknown")
						self.updateList.append((fetched[0], fetched[1], f"{oldVer}  ->  {newVer}", "upgradeable", upgradeablePng, divPng, fetched[2]))
					if self.updateList:
						self.updateList.sort(key=lambda x: x[0])  # Sort by package name.
						self["list"].setList(self.updateList)
					else:
						self.setStatus("noupdate")
				elif count == 0:
					self.setStatus("noupdate")
				else:
					self.setStatus("error")
				self.packageCount = len(self.updateList)
				print(f"[SoftwareUpdate] {self.packageCount} packages available for update.")
				self["package_count"].setText(str(self.packageCount))
				for callback in self.onCheckTrafficLight:
					callback()
				if self.packageCount:
					if self.feedState == self.FEED_DISABLED:
						self["key_red"].setText(_("Close"))
						self["key_green"].setText("")
						self["updateActions"].setEnabled(False)
					else:
						self["key_red"].setText(_("Cancel"))
						self["key_green"].setText(_("Update"))
						self["updateActions"].setEnabled(True)
				else:
					self["key_red"].setText(_("Close"))
				self["key_yellow"].setText(_("Refresh"))
				self["refreshActions"].setEnabled(True)
				self.activity = -1

	def layoutFinished(self):
		self["list"].enableAutoNavigation(False)
		self.setStatus("update")
		self.opkg.startCmd(OpkgComponent.CMD_UPDATE)
		self.timer.start(25, True)

	def setStatus(self, status):
		if status == "update":
			imagePath = resolveFilename(SCOPE_GUISKIN, "icons/upgrade.png")
			name = _("Package list update")
			description = _("Downloading latest update list. Please wait...")
		elif status == "error":
			imagePath = resolveFilename(SCOPE_GUISKIN, "icons/remove.png")
			name = _("Download error")
			description = _("There was an error downloading the update list. Please try again.")
		elif status == "noupdate":
			imagePath = resolveFilename(SCOPE_GUISKIN, "icons/installed.png")
			name = _("Nothing to upgrade")
			description = _("There are no updates available.")
		statusPng = LoadPixmap(cached=True, path=imagePath)
		divPng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
		self["list"].setList([(name, "", description, "", statusPng, divPng)])

	def keyCancel(self):
		if self.opkg.isRunning():
			self.opkg.stop()
		self.opkg.removeCallback(self.opkgCallback)
		self.close()

	def keyUpdate(self):
		def keyUpdateCallback(answer):
			match answer:
				case 1:
					from Screens.FlashManager import FlashManager  # This must be here to ensure the plugin is initialized.
					self.session.open(FlashManager)
				case 2:
					self.session.open(RunSoftwareUpdate)
			self.close()

		self.opkg.removeCallback(self.opkgCallback)
		updateLimit = BoxInfo.getItem("UpdateLimit", 200)
		if self.packageCount <= updateLimit:
			keyUpdateCallback(2)
		else:
			print(f"[SoftwareUpdate] Warning: There are {self.packageCount} packages available, more than the {updateLimit} maximum recommended, for an update!")
			message = [
				_("Warning: There are %d update packages!") % self.packageCount,
				_("There is a risk that your %s %s will not boot or may malfunction after such a large on-line update.") % getBoxDisplayName(),
				_("You should flash a new image!"),
				_("What would you like to do?")
			]
			message = "\n\n".join(message)
			optionList = [
				(_("Cancel the update"), 0),
				(_("Perform an on-line flash instead"), 1),
				(_("Continue with the on-line update"), 2)
			]
			self.session.openWithCallback(keyUpdateCallback, MessageBox, message, list=optionList, default=0)

	def keyRefresh(self):
		self.timer.callback.append(self.checkTrafficLight)
		self["key_red"].setText(_("Cancel"))
		self["key_green"].setText("")
		self["key_yellow"].setText("")
		self["updateActions"].setEnabled(False)
		self["refreshActions"].setEnabled(False)
		self["package_count"].setText("?")
		self["traffic_off"].show()
		self["traffic_red"].hide()
		self["traffic_yellow"].hide()
		self["traffic_green"].hide()
		self["feedstatus_off"].hide()
		self["feedstatus_red"].hide()
		self["feedstatus_yellow"].hide()
		self["feedstatus_green"].hide()
		self["feedmessage"].setText("")
		self.activity = 0
		self.feedOnline = False
		self.updateFlag = True
		self["activity"].setValue(self.activity)
		self["activity"].show()
		self.setStatus("update")
		self.opkg.startCmd(OpkgComponent.CMD_UPDATE)
		self.timer.start(25, True)

	def createSummary(self):
		return SoftwareUpdateSummary


class SoftwareUpdateSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self["entry"] = StaticText()  # Use the same widget as the Setup Summary screen so the screens can be shared.
		self["value"] = StaticText()  # Use the same widget as the Setup Summary screen so the screens can be shared.
		self.statusText = [
			parent["feedstatus_off"].getText(),
			parent["feedstatus_red"].getText(),
			parent["feedstatus_yellow"].getText(),
			parent["feedstatus_green"].getText()
		]
		if self.addWatcher not in self.onShow:
			self.onShow.append(self.addWatcher)
		if self.removeWatcher not in self.onHide:
			self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if self.feedStatusChanged not in self.parent.onCheckTrafficLight:
			self.parent.onCheckTrafficLight.append(self.feedStatusChanged)
		self.feedStatusChanged()

	def removeWatcher(self):
		if self.feedStatusChanged in self.parent.onCheckTrafficLight:
			self.parent.onCheckTrafficLight.remove(self.feedStatusChanged)

	def feedStatusChanged(self):
		self["entry"].setText(self.statusText[self.parent.feedState])
		self["value"].setText(f"{self.parent["package_text"].getText()} {self.parent["package_count"].getText()}")


class RunSoftwareUpdate(Screen):
	skin = """
	<screen name="RunSoftwareUpdate" position="center,center" size="720,435" resolution="1280,720">
		<widget name="update" position="10,10" size="700,400" font="Regular;20" halign="center" transparent="1" valign="center" />
		<widget name="activity" position="10,420" size="700,5" />
	</screen>"""

	def __init__(self, session, *args):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Software Update"))
		self.onTimerTick = []
		self["update"] = ScrollLabel(_("Software update starting, please wait.\n\n"))
		self["activity"] = Slider(0, 100)
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Stop the update, if running, then exit")),
			"ok": (self.keyCancel, _("Stop the update, if running, then exit")),
			"top": (self["update"].goTop, _("Move to first line / screen")),
			"pageUp": (self["update"].goPageUp, _("Move up a page / screen")),
			"up": (self["update"].goLineUp, _("Move up a page / screen")),
			"down": (self["update"].goLineDown, _("Move down a page / screen")),
			"pageDown": (self["update"].goPageDown, _("Move down a page / screen")),
			"bottom": (self["update"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Software Update Actions"))
		self.activity = 0
		self.packageTotal = 0
		self.downloadCount = 0
		self.updateCount = 0
		self.installCount = 0
		self.removeCount = 0
		self.deselectCount = 0
		self.upgradeCount = 0
		self.configureCount = 0
		self.metrixUpdated = False
		self.timer = eTimer()
		self.timer.callback.append(self.timeout)
		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)
		self.onLayoutFinish.append(self.layoutFinished)

	def timeout(self):
		if self.activity < 0:
			self.timer.stop()
			self["activity"].hide()
		else:
			if self.packageTotal and self.upgradeCount:
				self["activity"].setValue(int(self.upgradeCount / self.packageTotal * 100))
			else:
				self.activity += 1
				if self.activity == 100:
					self.activity = 0
				self["activity"].setValue(self.activity)
			self.timer.start(100, True)
		for callback in self.onTimerTick:
			callback()

	def opkgCallback(self, event, parameter):
		def modificationCallback(answer):
			self.opkg.write("N" if answer else "Y")

		if event == OpkgComponent.EVENT_DOWNLOAD:
			self.downloadCount += 1
			if parameter.find("_") == -1:  # Only display the downloading of the feed packages.
				self["update"].appendText(f"{_("Downloading")}: '{parameter}'.\n")
		elif event == OpkgComponent.EVENT_UPDATED:
			self.updateCount += 1
			self["update"].appendText(f"{_("Updated")}: {parameter}\n")
		elif event == OpkgComponent.EVENT_UPVERSION:
			self.upgradeCount += 1
			self["update"].appendText(f"{_("Updating")} {self.upgradeCount}/{self.packageTotal}: '{parameter}'.\n")
			if "enigma2-plugin-skins-metrix-atv" in parameter:
				self.metrixUpdated = True
		elif event == OpkgComponent.EVENT_INSTALL:
			self.installCount += 1
			self["update"].appendText(f"{_("Installing")}: '{parameter}'.\n")
		elif event == OpkgComponent.EVENT_REMOVE:
			self.removeCount += 1
			self["update"].appendText(f"{_("Removing")}: '{parameter}'.\n")
		elif event == OpkgComponent.EVENT_CONFIGURING:
			self.configureCount += 1
			self["update"].appendText(f"{_("Configuring")}: '{parameter}'.\n")
		elif event == OpkgComponent.EVENT_MODIFIED:
			if config.plugins.softwaremanager.overwriteConfigFiles.value in ("N", "Y"):
				self.opkg.write(True and config.plugins.softwaremanager.overwriteConfigFiles.value)
			else:
				self.session.openWithCallback(modificationCallback, MessageBox, _("Configuration file '%s' has been modified since it was installed, would you like to keep the modified version?") % parameter)
		elif event in (OpkgComponent.EVENT_DONE, OpkgComponent.EVENT_ERROR):
			if self.opkg.currentCommand == OpkgComponent.CMD_UPGRADE_LIST:
				self.packageTotal = len(self.opkg.getFetchedList())
				if self.packageTotal:
					self.opkg.startCmd(OpkgComponent.CMD_UPGRADE, args={"testMode": False})
				else:
					self.activity = -1
					self["update"].appendText(f"{_("No updates available.")}\n\n{_("Press OK on your remote control to continue.")}")
			else:
				self["update"].appendText(f"\n{_("Update completed.")}\n\n")
				self["update"].appendText(f"{ngettext("%d package was identified for upgrade.", "%d packages were identified for upgrade.", self.packageTotal) % self.packageTotal}\n")
				self["update"].appendText(f"{ngettext("%d package was downloaded.", "%d packages were downloaded.", self.downloadCount) % self.downloadCount}\n")
				self["update"].appendText(f"{ngettext("%d feed catalog package was updated.", "%d feed catalog packages were updated.", self.updateCount) % self.updateCount}\n")
				self["update"].appendText(f"{ngettext("%d package was installed.", "%d packages were installed.", self.installCount) % self.installCount}\n")
				self["update"].appendText(f"{ngettext("%d package was removed.", "%d packages were removed.", self.removeCount) % self.removeCount}\n")
				self["update"].appendText(f"{ngettext("%d package was upgraded.", "%d packages were upgraded.", self.upgradeCount) % self.upgradeCount}\n")
				self["update"].appendText(f"{ngettext("%d package was configured.", "%d packages were configured.", self.configureCount) % self.configureCount}\n")
				if self.deselectCount:
					self["update"].appendText(f"{ngettext("%d package was deselected.", "%d packages were deselected.", self.deselectCount) % self.deselectCount}\n")
					self["update"].appendText(f"\n{_("Deselected packages usually occur because those packaged are incompatible with existing packages. While this is mostly harmless it is possible that your %s %s may experience issues.") % getBoxDisplayName()}\n")
				if event == OpkgComponent.EVENT_ERROR:
					self["update"].appendText(f"\n\n{_("Error")}:\n{_("Your receiver might be now be unstable. Please consult the manual for further assistance before rebooting your %s %s.") % getBoxDisplayName()}\n")
				self.activity = -1
				self["update"].appendText(f"\n{_("Press OK on your remote control to continue.")}")

	def layoutFinished(self):
		self.opkg.startCmd(OpkgComponent.CMD_UPGRADE_LIST)
		self.timer.start(25, True)

	# def keyCancel(self):
	# 	def keyCancelCallback(answer):
	# 		if answer:
	# 			self.session.open(TryQuitMainloop, retvalue=QUIT_REBOOT)
	# 		self.close()

	# 	if self.opkg.isRunning():
	# 		self.opkg.stop()
	# 	self.opkg.removeCallback(self.opkgCallback)
	# 	if self.upgradeCount != 0:
	# 		self.session.openWithCallback(keyCancelCallback, MessageBox, f"{_("Upgrade finished.")} {_("Do you want to reboot your %s %s?") % getBoxDisplayName()}")
	# 	else:
	# 		self.close()

	def keyCancel(self):
		def keyCancelCallback(result=None):
			def rebootCallback(answer):
				if answer:
					self.session.open(TryQuitMainloop, retvalue=QUIT_REBOOT)
				self.close()

			self.session.openWithCallback(rebootCallback, MessageBox, f"{_("Upgrade finished.")} {_("Do you want to reboot your %s %s?") % getBoxDisplayName()}")

		if self.opkg.isRunning():
			self.opkg.stop()
		self.opkg.removeCallback(self.opkgCallback)
		if config.skin.primary_skin.value == "MetrixHD/skin.MySkin.xml" and self.metrixUpdated:   # TODO: move this to Metrix Plugin.
			try:
				if not exists("/usr/share/enigma2/MetrixHD/skin.MySkin.xml"):
					from Plugins.SystemPlugins.SoftwareManager.BackupRestore import RestoreMyMetrixHD
					self.session.openWithCallback(keyCancelCallback, RestoreMyMetrixHD)
					return
				elif config.plugins.MyMetrixLiteOther.EHDenabled.value != "0":
					from Plugins.Extensions.MyMetrixLite.ActivateSkinSettings import ActivateSkinSettings
					ActivateSkinSettings().RefreshIcons()
			except Exception:
				pass
		if self.upgradeCount != 0:
			keyCancelCallback()
		else:
			self.close()

	def createSummary(self):
		return RunSoftwareUpdateSummary


class RunSoftwareUpdateSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self["entry"] = StaticText()  # Use the same widget as the Setup Summary screen so the screens can be shared.
		self["value"] = StaticText()  # Use the same widget as the Setup Summary screen so the screens can be shared.
		self["activity"] = Slider(0, 100)
		if self.addWatcher not in self.onShow:
			self.onShow.append(self.addWatcher)
		if self.removeWatcher not in self.onHide:
			self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if self.update not in self.parent.onTimerTick:
			self.parent.onTimerTick.append(self.update)
		self.update()

	def removeWatcher(self):
		if self.update in self.parent.onTimerTick:
			self.parent.onTimerTick.remove(self.update)

	def update(self):
		self["entry"].setText(ngettext("%d package upgraded.", "%d packages upgraded.", self.parent.upgradeCount) % self.parent.upgradeCount)
		if self.parent.activity < 0:
			self["value"].setText(_("Press OK to continue."))
			self["activity"].hide()
		else:
			self["activity"].setValue(self.parent.activity)
