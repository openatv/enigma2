from json import load
try:
	from urllib.request import urlopen
except ImportError:
	from urllib2 import urlopen

from enigma import eTimer

from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.Opkg import OpkgComponent
from Components.Pixmap import Pixmap
from Components.Slider import Slider
from Components.SystemInfo import BoxInfo
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen, ScreenSummary
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap

UPDATE_LIMIT = 200


class SoftwareUpdate(Screen, HelpableScreen):
	FEED_UNKNOWN = 0
	FEED_DISABLED = 1
	FEED_UNSTABLE = 2
	FEED_STABLE = 3

	skin = """
	<screen name="SoftwareUpdate" title="Software Update" position="center,center" size="650,580">
		<widget name="traffic_off" position="10,10" size="36,97" alphatest="blend" pixmap="icons/traffic_off.png" />
		<widget name="traffic_red" position="10,10" size="36,97" alphatest="blend" pixmap="icons/traffic_red.png" />
		<widget name="traffic_yellow" position="10,10" size="36,97" alphatest="blend" pixmap="icons/traffic_yellow.png" />
		<widget name="traffic_green" position="10,10" size="36,97" alphatest="blend" pixmap="icons/traffic_green.png" />
		<widget name="feedstatus_off" position="60,46" size="200,30" font="Regular;20" transparent="1" valign="center" />
		<widget name="feedstatus_red" position="60,14" size="200,30" font="Regular;20" transparent="1" valign="center" />
		<widget name="feedstatus_yellow" position="60,46" size="200,30" font="Regular;20" transparent="1" valign="center" />
		<widget name="feedstatus_green" position="60,78" size="200,30" font="Regular;20" transparent="1" valign="center" />
		<widget name="package_text" position="330,10" size="250,30" font="Regular;25" transparent="1" valign="center" />
		<widget name="package_count" position="590,10" size="50,30" font="Regular;25" halign="right" transparent="1" valign="center" />
		<widget name="feedmessage" position="330,50" size="310,50" font="Regular;20" transparent="1" />
		<widget name="activity" position="330,102" size="310,5" />
		<widget source="list" render="Listbox" position="10,120" size="630,400" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{
				"template":
					[
					MultiContentEntryText(pos = (10, 0), size = (535, 30), font=0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER, text = 0),  # Index 0 is the name.
					MultiContentEntryText(pos = (20, 30), size = (515, 20), font=1, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER, text = 2),  # Index 2 is the description.
					MultiContentEntryPixmapAlphaBlend(pos = (560, 0), size = (48, 48), flags = BT_SCALE, png = 4),  # Index 4 is the status pixmap.
					MultiContentEntryPixmapAlphaBlend(pos = (5, 48), size = (630, 2), png = 5),  # Index 5 is the div pixmap
					],
				"fonts": [gFont("Regular", 22), gFont("Regular", 15)],
				"itemHeight": 50
				}
			</convert>
		</widget>
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, *args):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		Screen.setTitle(self, _("Software Update"))
		self.onCheckTrafficLight = []
		self.updateList = []
		self["list"] = List(self.updateList, enableWrapAround=True)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText("")
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
		cancelMsg = _("Cancel the software update")
		updateMsg = _("Proceed with the update")
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"cancel": (self.keyCancel, cancelMsg),
			"red": (self.keyCancel, cancelMsg),
			"top": (self.top, _("Move to first line")),
			"pageUp": (self.pageUp, _("Move up a page")),
			"up": (self.up, _("Move up a line")),
			# "first": (self.top, _("Move to first line")),
			# "left": (self.pageUp, _("Move up a page")),
			# "right": (self.pageDown, _("Move down a page")),
			# "last": (self.bottom, _("Move to last line")),
			"down": (self.down, _("Move down a line")),
			"pageDown": (self.pageDown, _("Move down a page")),
			"bottom": (self.bottom, _("Move to last line"))
		}, prio=0, description=_("Software Update Actions"))
		self["updateActions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"ok": (self.keyUpdate, updateMsg),
			"green": (self.keyUpdate, updateMsg)
		}, prio=0, description=_("Software Update Actions"))
		self["updateActions"].setEnabled(False)
		self.activity = 0
		self.feedState = self.FEED_UNKNOWN
		self.updateFlag = True
		self.packageCount = 0
		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)
		self.timer = eTimer()
		self.timer.callback.append(self.timeout)
		self.timer.callback.append(self.checkTrafficLight)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["list"].master.master.instance.allowNativeKeys(False)
		self.timer.start(25, True)
		self.rebuildList()

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

	def keyCancel(self):
		self.opkg.stop()
		self.close()

	def keyUpdate(self):
		if self.packageCount <= UPDATE_LIMIT:
			from Plugins.SystemPlugins.SoftwareManager.plugin import UpdatePlugin  # This must be here to ensure the plugin is initialized.
			self.session.open(UpdatePlugin)
			self.close()
		else:
			print("[SoftwarePanel] Warning: There are more packages than the %d maximum recommended for an update!" % UPDATE_LIMIT)
			message = [
				_("Warning: There are %d update packages!") % self.packageCount,
				_("There is a risk that your %s %s will not boot or may malfunction after such a large on-line update.") % (BoxInfo.getItem("displaybrand"), BoxInfo.getItem("displaymodel")),
				_("You should flash a new image!"),
				_("What would you like to do?")
			]
			message = "\n\n".join(message)
			optionList = [
				(_("Cancel the update"), 0),
				(_("Perform an on-line flash instead"), 1),
				(_("Continue with the on-line update"), 2)
			]
			self.session.openWithCallback(self.checkPackagesCallback, MessageBox, message, list=optionList, default=0)

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

	def checkPackagesCallback(self, answer):
		if answer == 1:
			from Plugins.SystemPlugins.SoftwareManager.Flash_online import FlashOnline  # This must be here to ensure the plugin is initialized.
			self.session.open(FlashOnline)
		elif answer == 2:
			from Plugins.SystemPlugins.SoftwareManager.plugin import UpdatePlugin  # This must be here to ensure the plugin is initialized.
			self.session.open(UpdatePlugin)
		self.close()

	def checkTrafficLight(self):
		self.timer.callback.remove(self.checkTrafficLight)
		try:
#			status = dict(load(urlopen("%s/%s.php" % (BoxInfo.getItem("feedsurl"), BoxInfo.getItem("model")), timeout=5)))
#			message = status.get("message")
#			status = status.get("status")
			status = ""
			message = ""
			with urlopen("http://ampel.mynonpublic.com/Ampel/index.php") as fd:
				tmpStatus = fd.read()
				if b"rot.png" in tmpStatus:
					status = "RED"
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
		for method in self.onCheckTrafficLight:
			method()

	def rebuildList(self):
		self.setStatus("update")
		self.opkg.startCmd(OpkgComponent.CMD_UPDATE)

	def opkgCallback(self, event, param):
		if event == OpkgComponent.EVENT_ERROR:
			self.activity = -1
			self.setStatus("error")
		elif event == OpkgComponent.EVENT_DONE:
			if self.updateFlag:
				self.updateFlag = False
				self.opkg.startCmd(OpkgComponent.CMD_UPGRADE_LIST)
			else:
				self.buildPacketList()

	def setStatus(self, status=None):
		if status:
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

	def buildPacketList(self):
		self.updateList = []
		fetchedList = self.opkg.getFetchedList()
		count = len(fetchedList)
		if count > 0:
			for fetched in fetchedList:
				try:
					self.updateList.append(self.buildEntryComponent(fetched[0], fetched[1], fetched[2], "upgradeable"))
				except:
					print("[SoftwarePanel] Error: Ignoring '%s' as it has an invalid architecture!" % fetched[0])
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
		if self.packageCount == 0 or self.feedState == self.FEED_DISABLED:
			self["key_green"].setText("")
			self["updateActions"].setEnabled(False)
		else:
			self["key_green"].setText(_("Update"))
			self["updateActions"].setEnabled(True)
		for method in self.onCheckTrafficLight:
			method()
		self.activity = -1

	def buildEntryComponent(self, name, version, description, state):
		if not description:
			description = _("No description available.")
		if state == "installed":
			imagePath = resolveFilename(SCOPE_GUISKIN, "icons/installed.png")
		elif state == "upgradeable":
			imagePath = resolveFilename(SCOPE_GUISKIN, "icons/upgradeable.png")
		else:
			imagePath = resolveFilename(SCOPE_GUISKIN, "icons/installable.png")
		statusPng = LoadPixmap(cached=True, path=imagePath)
		divPng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
		return (name, version, description, state, statusPng, divPng)

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
