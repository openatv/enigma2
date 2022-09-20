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
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.Screen import Screen, ScreenSummary
from Screens.Standby import QUIT_REBOOT, TryQuitMainloop
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap


class SoftwareUpdate(Screen, HelpableScreen, ProtectedScreen):
	FEED_UNKNOWN = 0
	FEED_DISABLED = 1
	FEED_UNSTABLE = 2
	FEED_STABLE = 3

	skin = ["""
	<screen name="SoftwareUpdate" title="Software Update" position="center,center" size="%d,%d" >
		<widget name="traffic_off" position="%d,%d" size="%d,%d" alphatest="blend" pixmap="icons/traffic_off.png" scale="1" />
		<widget name="traffic_red" position="%d,%d" size="%d,%d" alphatest="blend" pixmap="icons/traffic_red.png" scale="1" />
		<widget name="traffic_yellow" position="%d,%d" size="%d,%d" alphatest="blend" pixmap="icons/traffic_yellow.png" scale="1" />
		<widget name="traffic_green" position="%d,%d" size="%d,%d" alphatest="blend" pixmap="icons/traffic_green.png" scale="1" />
		<widget name="feedstatus_off" position="%d,%d" size="%d,%d" font="Regular;%d" transparent="1" valign="center" />
		<widget name="feedstatus_red" position="%d,%d" size="%d,%d" font="Regular;%d" transparent="1" valign="center" />
		<widget name="feedstatus_yellow" position="%d,%d" size="%d,%d" font="Regular;%d" transparent="1" valign="center" />
		<widget name="feedstatus_green" position="%d,%d" size="%d,%d" font="Regular;%d" transparent="1" valign="center" />
		<widget name="package_text" position="%d,%d" size="%d,%d" font="Regular;%d" transparent="1" valign="center" />
		<widget name="package_count" position="%d,%d" size="%d,%d" font="Regular;%d" halign="right" transparent="1" valign="center" />
		<widget name="feedmessage" position="%d,%d" size="%d,%d" font="Regular;%d" transparent="1" />
		<widget name="activity" position="%d,%d" size="%d,%d" />
		<widget source="list" render="Listbox" position="%d,%d" size="%d,%d" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{
				"template":
					[
					MultiContentEntryText(pos = (%d, %d), size = (%d, %d), font=0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER, text = 0),  # Index 0 is the name.
					MultiContentEntryText(pos = (%d, %d), size = (%d, %d), font=1, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER, text = 2),  # Index 2 is the description.
					MultiContentEntryPixmapAlphaBlend(pos = (%d, %d), size = (%d, %d), flags = BT_SCALE, png = 4),  # Index 4 is the status pixmap.
					MultiContentEntryPixmapAlphaBlend(pos = (%d, %d), size = (%d, %d), png = 5),  # Index 5 is the div pixmap
					],
				"fonts": [gFont("Regular", %d), gFont("Regular", %d)],
				"itemHeight": %d
				}
			</convert>
		</widget>
		<widget source="key_red" render="Label" position="%d,e-%d" size="%d,%d" backgroundColor="key_red" font="Regular;%d" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="%d,e-%d" size="%d,%d" backgroundColor="key_green" font="Regular;%d" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="%d,e-%d" size="%d,%d" backgroundColor="key_yellow" font="Regular;%d" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>""",
		650, 580,  # SoftwareUpdate
		10, 10, 36, 97,  # traffic_off
		10, 10, 36, 97,  # traffic_red
		10, 10, 36, 97,  # traffic_yellow
		10, 10, 36, 97,  # traffic_green
		60, 46, 200, 30, 20,  # feedstatus_off
		60, 14, 200, 30, 20,  # feedstatus_red
		60, 46, 200, 30, 20,  # feedstatus_yellow
		60, 78, 200, 30, 20,  # feedstatus_green
		330, 10, 250, 30, 25,  # package_text
		590, 10, 50, 30, 25,  # package_count
		330, 50, 310, 50, 20,  # feedmessage
		330, 102, 310, 5,  # activity
		10, 120, 630, 400,  # list
		10, 0, 535, 30,  # Index 0 - name
		20, 30, 515, 20,  # Index 2 - description
		560, 0, 48, 48,  # Index 4 - status pixmap
		5, 48, 630, 2,  # Index 5 - div pixmap
		22, 15,  # fonts
		50,  # itemHeight
		10, 50, 180, 40, 20,  # key_red
		200, 50, 180, 40, 20,  # key_green
		390, 50, 180, 40, 20  # key_yellow
	]

	def __init__(self, session, *args):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		ProtectedScreen.__init__(self)
		Screen.setTitle(self, _("Software Update"))
		self.onCheckTrafficLight = []
		self.updateList = []
		self["list"] = List(self.updateList, enableWrapAround=True)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["traffic_off"] = Pixmap()
		self["traffic_red"] = Pixmap()
		self["traffic_red"].hide()
		self["traffic_yellow"] = Pixmap()
		self["traffic_yellow"].hide()
		self["traffic_green"] = Pixmap()
		self["traffic_green"].hide()
		self["feedstatus_off"] = Label(_("Status unavailable!"))
		self["feedstatus_off"].hide()
		self["feedstatus_red"] = Label("< %s" % _("Feed disabled!"))
		self["feedstatus_red"].hide()
		self["feedstatus_yellow"] = Label("< %s" % _("Feed unstable!"))
		self["feedstatus_yellow"].hide()
		self["feedstatus_green"] = Label("< %s" % _("Feed stable."))
		self["feedstatus_green"].hide()
		self["feedmessage"] = Label()
		self["package_text"] = Label(_("Updates available:"))
		self["package_count"] = Label("?")
		self["activity"] = Slider(0, 100)
		cancelMsg = _("Cancel / Close the software update screen")
		updateMsg = _("Proceed with the update")
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"cancel": (self.keyCancel, cancelMsg),
			"red": (self.keyCancel, cancelMsg),
			"top": (self.top, _("Move to first line / screen")),
			"pageUp": (self.pageUp, _("Move up a page / screen")),
			"up": (self.up, _("Move up a line")),
			# "first": (self.top, _("Move to first line / screen")),
			"left": (self.pageUp, _("Move up a page / screen")),
			"right": (self.pageDown, _("Move down a page / screen")),
			# "last": (self.bottom, _("Move to last line / screen")),
			"down": (self.down, _("Move down a line")),
			"pageDown": (self.pageDown, _("Move down a page / screen")),
			"bottom": (self.bottom, _("Move to last line / screen"))
		}, prio=0, description=_("Software Update Actions"))
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

	def layoutFinished(self):
		self["list"].master.master.instance.enableAutoNavigation(False)
		self.setStatus("update")
		self.opkg.startCmd(OpkgComponent.CMD_UPDATE)
		self.timer.start(25, True)

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
#			status = dict(load(urlopen("%s/%s.php" % (BoxInfo.getItem("feedsurl"), BoxInfo.getItem("model")), timeout=5)))
#			message = status.get("message")
#			status = status.get("status")
			status = ""
			message = ""
			with urlopen("https://ampel.mynonpublic.com/Ampel/index.php") as fd:
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
			print("[SoftwareUpdate] Error: Unable to get server status!  (%s)" % str(err))
			self["feedstatus_off"].show()
		for callback in self.onCheckTrafficLight:
			callback()

	def opkgCallback(self, event, parameter):
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
						self.updateList.append((fetched[0], fetched[1], "%s  ->  %s" % (oldVer, newVer), "upgradeable", upgradeablePng, divPng))
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
				print("[SoftwareUpdate] %d packages available for update." % self.packageCount)
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

	def setStatus(self, status):
		if status == "update":
			imagePath = resolveFilename(SCOPE_GUISKIN, "icons/upgrade.png")
			name = _("Package list update")
			description = _("Downloading latest update list.  Please wait...")
		elif status == "error":
			imagePath = resolveFilename(SCOPE_GUISKIN, "icons/remove.png")
			name = _("Download error")
			description = _("There was an error downloading the update list.  Please try again.")
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
		self.opkg.removeCallback(self.opkgCallback)
		updateLimit = BoxInfo.getItem("UpdateLimit", 200)
		if self.packageCount <= updateLimit:
			self.keyUpdateCallback(2)
		else:
			print("[SoftwareUpdate] Warning: There are %d packages available, more than the %d maximum recommended, for an update!" % (self.packageCount, updateLimit))
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
			self.session.openWithCallback(self.keyUpdateCallback, MessageBox, message, list=optionList, default=0)

	def keyUpdateCallback(self, answer):
		if answer == 1:
			from Screens.FlashManager import FlashManager  # This must be here to ensure the plugin is initialized.
			self.session.open(FlashManager)
		elif answer == 2:
			self.session.open(RunSoftwareUpdate)
		self.close()

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
		self["activity"].setValue(self.activity)
		self["activity"].show()
		self.setStatus("update")
		self.opkg.startCmd(OpkgComponent.CMD_UPDATE)
		self.timer.start(25, True)

	def top(self):
		self["list"].top()

	def pageUp(self):
		self["list"].pageUp()

	def up(self):
		self["list"].up()

	def down(self):
		self["list"].down()

	def pageDown(self):
		self["list"].pageDown()

	def bottom(self):
		self["list"].bottom()

	def createSummary(self):
		return SoftwareUpdateSummary


class SoftwareUpdateSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self["entry"] = StaticText("")  # Use the same widget as the Setup Summary screen so the screens can be shared.
		self["value"] = StaticText("")  # Use the same widget as the Setup Summary screen so the screens can be shared.
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
		self["value"].setText("%s %s" % (self.parent["package_text"].getText(), self.parent["package_count"].getText()))


class RunSoftwareUpdate(Screen, HelpableScreen):
	skin = """
	<screen name="RunSoftwareUpdate" position="center,center" size="720,435" resolution="1280,720">
		<widget name="update" position="10,10" size="700,400" font="Regular;20" halign="center" transparent="1" valign="center" />
		<widget name="activity" position="10,420" size="700,5" />
	</screen>"""

	def __init__(self, session, *args):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setTitle(_("Software Update"))
		self.onTimerTick = []
		self["update"] = ScrollLabel(_("Software update starting, please wait.\n\n"))
		self["activity"] = Slider(0, 100)
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Stop the update, if running, then exit")),
			"ok": (self.keyCancel, _("Stop the update, if running, then exit")),
			"top": (self.top, _("Move to first line / screen")),
			"pageUp": (self.pageUp, _("Move up a page / screen")),
			"up": (self.pageUp, _("Move up a page / screen")),
			# "first": (self.top, _("Move to first line / screen")),
			"left": (self.pageUp, _("Move up a page / screen")),
			"right": (self.pageDown, _("Move down a page / screen")),
			# "last": (self.bottom, _("Move to last line / screen")),
			"down": (self.pageDown, _("Move down a page / screen")),
			"pageDown": (self.pageDown, _("Move down a page / screen")),
			"bottom": (self.bottom, _("Move to last line / screen"))
		}, prio=0, description=_("Software Update Actions"))
		self.activity = 0
		self.timer = eTimer()
		self.timer.callback.append(self.timeout)
		self.packageTotal = 0
		self.downloadCount = 0
		self.updateCount = 0
		self.installCount = 0
		self.removeCount = 0
		self.deselectCount = 0
		self.upgradeCount = 0
		self.configureCount = 0
		self.errorCount = 0
		self.updateFlag = True
		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.opkg.startCmd(OpkgComponent.CMD_UPDATE)
		self.timer.start(25, True)

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
		for callback in self.onTimerTick:
			callback()

	def opkgCallback(self, event, parameter):
		if event == OpkgComponent.EVENT_DOWNLOAD:
			self.downloadCount += 1
			if parameter.find("_") == -1:  # Only display the downloading of the feed packages.
				self["update"].appendText("%s: '%s'.\n" % (_("Downloading"), parameter))
		elif event == OpkgComponent.EVENT_UPDATED:
			self.updateCount += 1
			self["update"].appendText("%s: %s\n" % (_("Updated"), parameter))
		elif event == OpkgComponent.EVENT_UPVERSION:
			self.upgradeCount += 1
			self["update"].appendText("%s %s/%s: '%s'.\n" % (_("Updating"), self.upgradeCount, self.packageTotal, parameter))
		elif event == OpkgComponent.EVENT_INSTALL:
			self.installCount += 1
			self["update"].appendText("%s: '%s'.\n" % (_("Installing"), parameter))
		elif event == OpkgComponent.EVENT_REMOVE:
			self.removeCount += 1
			self["update"].appendText("%s: '%s'.\n" % (_("Removing"), parameter))
		elif event == OpkgComponent.EVENT_CONFIGURING:
			self.configureCount += 1
			self["update"].appendText("%s: '%s'.\n" % (_("Configuring"), parameter))
		elif event == OpkgComponent.EVENT_MODIFIED:
			if config.plugins.softwaremanager.overwriteConfigFiles.value in ("N", "Y"):
				self.opkg.write(True and config.plugins.softwaremanager.overwriteConfigFiles.value)
			else:
				self.session.openWithCallback(
					self.modificationCallback,
					MessageBox,
					_("Configuration file '%s' has been modified since it was installed, would you like to keep the modified version?") % parameter
				)
		elif event == OpkgComponent.EVENT_ERROR:
			self.errorCount += 1
		elif event == OpkgComponent.EVENT_DONE:
			if self.updateFlag:
				self.updateFlag = False
				self.opkg.startCmd(OpkgComponent.CMD_UPGRADE_LIST)
			elif self.opkg.currentCommand == OpkgComponent.CMD_UPGRADE_LIST:
				self.packageTotal = len(self.opkg.getFetchedList())
				if self.packageTotal:
					self.opkg.startCmd(OpkgComponent.CMD_UPGRADE, args={"testMode": False})
				else:
					self.activity = -1
					self["update"].appendText("%s\n\n%s" % (_("No updates available."), _("Press OK on your remote control to continue.")))
			else:
				if self.errorCount == 0:
					self["update"].appendText("\n%s\n\n" % _("Update completed."))
					self["update"].appendText("%s\n" % ngettext("%d package was identified for upgrade.", "%d packages were identified for upgrade.", self.packageTotal) % self.packageTotal)
					self["update"].appendText("%s\n" % ngettext("%d package was downloaded.", "%d packages were downloaded.", self.downloadCount) % self.downloadCount)
					self["update"].appendText("%s\n" % ngettext("%d feed catalog package was updated.", "%d feed catalog packages were updated.", self.updateCount) % self.updateCount)
					self["update"].appendText("%s\n" % ngettext("%d package was installed.", "%d packages were installed.", self.installCount) % self.installCount)
					self["update"].appendText("%s\n" % ngettext("%d package was removed.", "%d packages were removed.", self.removeCount) % self.removeCount)
					self["update"].appendText("%s\n" % ngettext("%d package was upgraded.", "%d packages were upgraded.", self.upgradeCount) % self.upgradeCount)
					self["update"].appendText("%s\n" % ngettext("%d package was configured.", "%d packages were configured.", self.configureCount) % self.configureCount)
					if self.deselectCount:
						self["update"].appendText("%s\n" % ngettext("%d package was deselected.", "%d packages were deselected.", self.deselectCount) % self.deselectCount)
						self["update"].appendText("\n%s\n" % _("Deselected packages usually occur because those packaged are incompatible with existing packages.  While this is mostly harmless it is possible that your %s %s may experience issues.") % getBoxDisplayName())
				else:
					error = _("Your receiver might be unusable now.  Please consult the manual for further assistance before rebooting your %s %s.") % getBoxDisplayName()
					if self.upgradeCount == 0:
						error = _("No updates were available.  Please try again later.")
					self["update"].appendText("%s: %s\n" % (_("Error"), error))
				self.activity = -1
				self["update"].appendText("\n%s" % _("Press OK on your remote control to continue."))

	def modificationCallback(self, answer):
		self.opkg.write("N" if answer else "Y")

	def keyCancel(self):
		if self.opkg.isRunning():
			self.opkg.stop()
		self.opkg.removeCallback(self.opkgCallback)
		if self.upgradeCount != 0 and self.errorCount == 0:
			self.restoreMetrixHD()
		else:
			self.close()

	def keyCancelCallback(self, answer):
		if answer:
			self.session.open(TryQuitMainloop, retvalue=QUIT_REBOOT)
		self.close()

	def top(self):
		self["update"].moveTop()

	def pageUp(self):
		self["update"].pageUp()

	def pageDown(self):
		self["update"].pageDown()

	def bottom(self):
		self["update"].moveBottom()

	def createSummary(self):
		return RunSoftwareUpdateSummary

	def restoreMetrixHD(self):  # TODO: call this only after metrix update / move this to Metrix Plugin
		try:
			if config.skin.primary_skin.value == "MetrixHD/skin.MySkin.xml":
				if not exists("/usr/share/enigma2/MetrixHD/skin.MySkin.xml"):
					from Plugins.SystemPlugins.SoftwareManager.BackupRestore import RestoreMyMetrixHD
					self.session.openWithCallback(self.restoreMetrixHDCallback, RestoreMyMetrixHD)
					return
				elif config.plugins.MyMetrixLiteOther.EHDenabled.value != '0':
					from Plugins.Extensions.MyMetrixLite.ActivateSkinSettings import ActivateSkinSettings
					ActivateSkinSettings().RefreshIcons()
		except:
			pass
		self.restoreMetrixHDCallback()

	def restoreMetrixHDCallback(self, ret=None):
		self.session.openWithCallback(self.keyCancelCallback, MessageBox, _("Upgrade finished.") + " " + _("Do you want to reboot your %s %s?") % getBoxDisplayName())


class RunSoftwareUpdateSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self["entry"] = StaticText("")  # Use the same widget as the Setup Summary screen so the screens can be shared.
		self["value"] = StaticText("")  # Use the same widget as the Setup Summary screen so the screens can be shared.
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
