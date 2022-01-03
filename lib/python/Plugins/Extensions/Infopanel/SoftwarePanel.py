from os.path import exists
from socket import getdefaulttimeout, setdefaulttimeout
try:
	from urllib.request import URLError, urlopen
except ImportError:
	from urllib2 import urlopen
	URLError = Exception

from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.Opkg import OpkgComponent
from Components.Pixmap import Pixmap
from Components.SystemInfo import BoxInfo
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Directories import SCOPE_PLUGINS, SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap

STATUS_URL = "http://ampel.mynonpublic.com/Ampel/index.php"
UPDATE_LIMIT = 200


class SoftwarePanel(Screen, HelpableScreen):
	skin = """
	<screen name="SoftwarePanel" position="center,center" size="650,605" title="Software Panel">
		<widget name="a_off" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/icons/aoff.png" position="10,10" zPosition="1" size="36,97" alphatest="on" />
		<widget name="a_red" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/icons/ared.png" position="10,10" zPosition="1" size="36,97" alphatest="on" />
		<widget name="a_yellow" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/icons/ayellow.png" position="10,10" zPosition="1" size="36,97" alphatest="on" />
		<widget name="a_green" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/icons/agreen.png" position="10,10" zPosition="1" size="36,97" alphatest="on" />
		<widget name="feedstatusOFF" position="60,46" size="200,30" zPosition="1" font="Regular;25" halign="left" transparent="1" />
		<widget name="feedstatusRED" position="60,14" size="200,30" zPosition="1" font="Regular;25" halign="left" transparent="1" />
		<widget name="feedstatusYELLOW" position="60,46" size="200,30" zPosition="1" font="Regular;25" halign="left" transparent="1" />
		<widget name="feedstatusGREEN" position="60,78" size="200,30" zPosition="1" font="Regular;25" halign="left" transparent="1" />
		<widget name="packagetext" position="180,50" size="350,30" zPosition="1" font="Regular;25" halign="right" transparent="1" />
		<widget name="packagenr" position="511,50" size="50,30" zPosition="1" font="Regular;25" halign="right" transparent="1" />
		<widget source="list" render="Listbox" position="10,120" size="630,365" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{
				"template":
					[
					MultiContentEntryText(pos = (5, 1), size = (540, 28), font=0, flags = RT_HALIGN_LEFT, text = 0), # Index 0 is the name.
					MultiContentEntryText(pos = (5, 26), size = (540, 20), font=1, flags = RT_HALIGN_LEFT, text = 2), # Index 2 is the description.
					MultiContentEntryPixmapAlphaBlend(pos = (545, 2), size = (48, 48), png = 4), # Index 4 is the status pixmap.
					MultiContentEntryPixmapAlphaBlend(pos = (5, 50), size = (610, 2), png = 5), # Index 5 is the div pixmap
					],
				"fonts": [gFont("Regular", 22),gFont("Regular", 14)],
				"itemHeight": 52
				}
			</convert>
		</widget>
		<widget source="key_red" render="Label" position=" 80,573" size="200,26" zPosition="1" font="Regular;22" halign="left" transparent="1" />
		<widget source="key_green" render="Label" position="340,573" size="200,26" zPosition="1" font="Regular;22" halign="left" transparent="1">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, *args):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		Screen.setTitle(self, _("Software Panel"))
		self.updateList = []
		self["list"] = List(self.updateList)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText("")
		self["a_off"] = Pixmap()
		self["a_red"] = Pixmap()
		self["a_yellow"] = Pixmap()
		self["a_green"] = Pixmap()
		self["feedstatusOFF"] = Label(_("Status unavailable!"))
		self["feedstatusRED"] = Label("<  %s" % _("Feed disabled!"))
		self["feedstatusYELLOW"] = Label("<  %s" % _("Feed unstable!"))
		self["feedstatusGREEN"] = Label("<  %s" % _("Feed stable."))
		self["packagetext"] = Label(_("Updates available:"))
		self["packagenr"] = Label("?")
		cancelMsg = _("Cancel the software update")
		updateMsg = _("Proceed with the update")
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"cancel": (self.keyCancel, cancelMsg),
			"red": (self.keyCancel, cancelMsg)
		}, prio=0, description=_("Software Update Actions"))
		self["updateActions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"ok": (self.keyUpdate, updateMsg),
			"green": (self.keyUpdate, updateMsg)
		}, prio=0, description=_("Software Update Actions"))
		self["updateActions"].setEnabled(False)
		self.update = False
		self.packages = 0
		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.checkTrafficLight()
		self.rebuildList()

	def keyCancel(self):
		self.opkg.stop()
		self.close()

	def keyUpdate(self):
		if self.packages <= UPDATE_LIMIT:
			from Plugins.SystemPlugins.SoftwareManager.plugin import UpdatePlugin  # This must be here to ensure the plugin is initialized.
			self.session.open(UpdatePlugin)
			self.close()
		else:
			print("[SoftwarePanel] Warning: There are more packages than the %d maximum recommended for an update!" % UPDATE_LIMIT)
			message = [
				_("Warning: There are %d update packages!") % self.packages,
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

	def checkPackagesCallback(self, answer):
		if answer == 1:
			from Plugins.SystemPlugins.SoftwareManager.Flash_online import FlashOnline  # This must be here to ensure the plugin is initialized.
			self.session.open(FlashOnline)
		elif answer == 2:
			from Plugins.SystemPlugins.SoftwareManager.plugin import UpdatePlugin  # This must be here to ensure the plugin is initialized.
			self.session.open(UpdatePlugin)
		self.close()

	def checkTrafficLight(self):
		self["a_off"].hide()
		self["a_red"].hide()
		self["a_yellow"].hide()
		self["a_green"].hide()
		self["feedstatusOFF"].hide()
		self["feedstatusRED"].hide()
		self["feedstatusYELLOW"].hide()
		self["feedstatusGREEN"].hide()
		currentTimeoutDefault = getdefaulttimeout()
		setdefaulttimeout(3)
		try:
			with urlopen(STATUS_URL) as fd:
				tmpStatus = fd.read()
			if b"rot.png" in tmpStatus:
				self["a_red"].show()
				self["feedstatusRED"].show()
			elif b"gelb.png" in tmpStatus:
				self["a_yellow"].show()
				self["feedstatusYELLOW"].show()
			elif b"gruen.png" in tmpStatus:
				self["a_green"].show()
				self["feedstatusGREEN"].show()
		except URLError as err:
			print("[SoftwarePanel] Error: Unable to get server status!  (%s!)" % err)
			self["a_off"].show()
			self["feedstatusOFF"].show()
		except (IOError, OSError) as err:
			print("[SoftwarePanel] Error %s: Unable to get server status!  (%d)" % (err.errno, err.strerror))
			self["a_off"].show()
			self["feedstatusOFF"].show()
		setdefaulttimeout(currentTimeoutDefault)

	def rebuildList(self):
		self.setStatus("update")
		self.opkg.startCmd(OpkgComponent.CMD_UPDATE)

	def opkgCallback(self, event, param):
		if event == OpkgComponent.EVENT_ERROR:
			self.setStatus("error")
		elif event == OpkgComponent.EVENT_DONE:
			if self.update == False:
				self.update = True
				self.opkg.startCmd(OpkgComponent.CMD_UPGRADE_LIST)
			else:
				self.buildPacketList()

	def setStatus(self, status=None):
		if status:
			if status == "update":
				imagePath = resolveFilename(SCOPE_GUISKIN, "icons/upgrade.png")
				if not exists(imagePath):
					imagePath = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/upgrade.png")
				name = _("Package list update")
				description = _("Downloading latest update list.  Please wait...")
			elif status == "error":
				imagePath = resolveFilename(SCOPE_GUISKIN, "icons/remove.png")
				if not exists(imagePath):
					imagePath = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/remove.png")
				name = _("Download error")
				description = _("There was an error downloading the update list.  Please try again.")
			elif status == "noupdate":
				imagePath = resolveFilename(SCOPE_GUISKIN, "icons/installed.png")
				if not exists(imagePath):
					imagePath = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/installed.png")
				name = _("Nothing to upgrade")
				description = _("There are no updates available.")
			statusPng = LoadPixmap(cached=True, path=imagePath)
			divPng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
			self["list"].setList([(name, "", description, "", statusPng, divPng)])

	def buildPacketList(self):
		self.updateList = []
		fetchedList = self.opkg.getFetchedList()
		# excludeList = self.opkg.getExcludeList()
		count = len(fetchedList)
		if count > 0:
			for fetched in fetchedList:
				try:
					self.updateList.append(self.buildEntryComponent(fetched[0], fetched[1], fetched[2], "upgradeable"))
				except:
					print("[SoftwarePanel] Error: Ignoring '%s' as it has an invalid architecture!" % fetched[0])
					# self.updateList.append(self.buildEntryComponent(fetched[0], "", "Invalid architecture ignored!", "installable"))
			# if len(excludeList) > 0:
			# 	for exclude in excludeList:
			# 		try:
			# 			self.updateList.append(self.buildEntryComponent(exclude[0], exclude[1], exclude[2], "installable"))
			# 		except:
			# 			self.updateList.append(self.buildEntryComponent(exclude[0], "", "Invalid architecture ignored!", "installable"))
			if self.updateList:
				self["list"].setList(self.updateList)
			else:
				self.setStatus("noupdate")
		elif count == 0:
			self.setStatus("noupdate")
		else:
			self.setStatus("error")
		self.packages = len(self.updateList)
		print("[SoftwareUpdate] %d packages available for update." % self.packages)
		self["packagenr"].setText(str(self.packages))
		if self.packages == 0:
			self["key_green"].setText("")
			self["updateActions"].setEnabled(False)
		else:
			self["key_green"].setText(_("Update"))
			self["updateActions"].setEnabled(True)

	def buildEntryComponent(self, name, version, description, state):
		if not description:
			description = _("No description available.")
		if state == "installed":
			imagePath = resolveFilename(SCOPE_GUISKIN, "icons/installed.png")
			if not exists(imagePath):
				imagePath = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/installed.png")
		elif state == "upgradeable":
			imagePath = resolveFilename(SCOPE_GUISKIN, "icons/upgradeable.png")
			if not exists(imagePath):
				imagePath = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/upgradeable.png")
		else:
			imagePath = resolveFilename(SCOPE_GUISKIN, "icons/installable.png")
			if not exists(imagePath):
				imagePath = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/installable.png")
		statusPng = LoadPixmap(cached=True, path=imagePath)
		divPng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
		return (name, version, description, state, statusPng, divPng)
