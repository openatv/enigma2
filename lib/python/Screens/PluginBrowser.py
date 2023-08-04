from os import makedirs, symlink, unlink
from os.path import exists, join, islink
from re import compile
from shutil import rmtree

from enigma import checkInternetAccess, eDVBDB, eTimer, gRGB

from skin import parseColor
from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import ConfigDictionarySet, ConfigSelection, ConfigSubsection, ConfigText, ConfigYesNo, config
from Components.GUIComponent import GUIComponent
from Components.Harddisk import harddiskmanager
from Components.Label import Label
from Components.Opkg import OpkgComponent
from Components.PluginComponent import pluginComponent
from Components.ScrollLabel import ScrollLabel
from Components.SystemInfo import BoxInfo
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.Processing import Processing
from Screens.Screen import Screen, ScreenSummary
from Screens.Setup import Setup
from Tools.Directories import SCOPE_GUISKIN, SCOPE_PLUGINS, fileAccess, fileWriteLine, resolveFilename
from Tools.LoadPixmap import LoadPixmap
from Tools.NumericalTextInput import NumericalTextInput

MODULE_NAME = __name__.split(".")[-1]

INTERNET_TIMEOUT = 2
FEED_SERVER = "feeds2.mynonpublic.com"
ENIGMA_PREFIX = "enigma2-plugin-%s"
KERNEL_PREFIX = "kernel-module-%s"

PLUGIN_LIST = 0
PLUGIN_GRID = 1

PACKAGE_CATEGORIES = {
	"display": _("Display Skin Packages"),
	"drivers": _("Driver Packages"),
	"extensions": _("Extension Packages"),
	"extraopkgpackages": _("Development Packages"),
	"kernel": _("Kernel Packages"),
	"m2k": _("M2k Packages"),
	"picons": _("Picon Packages"),
	"pli": _("OpenPLi Packages"),
	"security": _("Security Packages"),
	"settings": _("Setting Packages"),
	"skincomponents": _("Skin Component Packages"),
	"skinpacks": _("Plugin Skin Packages"),
	"skins": _("Skin Packages"),
	"softcams": _("Softcam Packages"),
	"src": _("Source Packages"),
	"systemplugins": _("System Plugin Packages"),
	"vix": _("OpenViX Packages"),
	"weblinks": _("Web Link Packages")
}

config.pluginfilter = ConfigSubsection()
config.usage.pluginListLayout = ConfigSelection(default=PLUGIN_GRID, choices=[
	(PLUGIN_LIST, _("View as list")),
	(PLUGIN_GRID, _("View as grid"))
])
config.usage.plugins_sort_mode = ConfigSelection(default="user", choices=[
	("a_z", _("Alphabetical")),
	("default", _("Default")),
	("user", _("User defined"))
])
config.usage.plugin_sort_weight = ConfigDictionarySet()
config.usage.piconInstallLocation = ConfigSelection(default="/", choices=[("/", _("Internal flash"))])
config.pluginfilter.display = ConfigYesNo(default=True)
config.pluginfilter.drivers = ConfigYesNo(default=True)
config.pluginfilter.extensions = ConfigYesNo(default=True)
config.pluginfilter.extraopkgpackages = ConfigYesNo(default=False)
config.pluginfilter.kernel = ConfigYesNo(default=False)  # This uses the KERNEL_PREFIX rather than the standard ENIGMA_PREFIX!
config.pluginfilter.m2k = ConfigYesNo(default=True)
config.pluginfilter.picons = ConfigYesNo(default=True)
config.pluginfilter.pli = ConfigYesNo(default=False)
config.pluginfilter.security = ConfigYesNo(default=True)
config.pluginfilter.settings = ConfigYesNo(default=True)
config.pluginfilter.skincomponents = ConfigYesNo(default=True)
config.pluginfilter.skinpacks = ConfigYesNo(default=True)
config.pluginfilter.skins = ConfigYesNo(default=True)
config.pluginfilter.softcams = ConfigYesNo(default=True)
config.pluginfilter.src = ConfigYesNo(default=False)
config.pluginfilter.systemplugins = ConfigYesNo(default=True)
config.pluginfilter.vix = ConfigYesNo(default=False)
config.pluginfilter.weblinks = ConfigYesNo(default=True)
config.pluginfilter.userfeed = ConfigText(default="http://", fixed_size=False)


class PluginBrowser(Screen, HelpableScreen, NumericalTextInput, ProtectedScreen):
	skin = """
	<screen name="PluginBrowser" title="Plugin Browser" position="center,center" size="1000,535" resolution="1280,720">
		<widget source="pluginList" render="Listbox" position="0,0" size="e,450" conditional="pluginList" listOrientation="vertical" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{
				"template":
					[
					MultiContentEntryPixmapAlphaBlend(pos=(10, 5), size=(100, 40), png=3, flags=BT_SCALE),
					MultiContentEntryText(pos=(125, 3), size=(865, 24), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, text=1),
					MultiContentEntryText(pos=(145, 30), size=(845, 19), font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_BOTTOM, text=2)
					],
				"fonts": [parseFont("Regular;20"), parseFont("Regular;15")],
				"itemHeight": 50
				}
			</convert>
		</widget>
		<widget source="pluginGrid" render="Listbox" position="0,0" size="e,448" conditional="pluginGrid" listOrientation="grid" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{
				"template":
					[
					MultiContentEntryText(pos=(0, 0), size=(195, 110), font=0),
					MultiContentEntryText(pos=(4, 4), size=(187, 102), font=0, backcolor=0x00404040),
					MultiContentEntryPixmapAlphaBlend(pos=(45, 14), size=(100, 40), png=3, flags=BT_SCALE),
					MultiContentEntryText(pos=(5, 58), size=(185, 45), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER | RT_WRAP, text=1)
					],
				"fonts": [parseFont("Regular;18")],
				"itemWidth": 195,
				"itemHeight": 112
				}
			</convert>
		</widget>
		<widget name="quickselect" position="0,0" size="e,450" font="Regular;100" foregroundColor="#00fff000" halign="center" transparent="1" valign="center" zPosition="+1" />
		<widget name="description" position="0,e-75" size="e,25" font="Regular;20" valign="center" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="380,e-40" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="570,e-40" size="180,40" backgroundColor="key_blue" conditional="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_menu" render="Label" position="e-190,e-40" size="90,40" backgroundColor="key_back" conditional="key_menu" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-90,e-40" size="90,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""
	moveBackgroundColor = gRGB(0x00DC143C)
	moveFontColor = None

	def __init__(self, session):
		self.layout = "pluginList" if config.usage.pluginListLayout.value == PLUGIN_LIST else "pluginGrid"
		Screen.__init__(self, session, mandatoryWidgets=[self.layout])
		HelpableScreen.__init__(self)
		NumericalTextInput.__init__(self, handleTimeout=False, mode="SearchUpper")
		self.skinName = ["PluginBrowserList" if config.usage.pluginListLayout.value == PLUGIN_LIST else "PluginBrowserGrid", "PluginBrowser"]
		self.setTitle(_("Plugin Browser"))
		ProtectedScreen.__init__(self)
		self["key_menu"] = StaticText(_("MENU"))
		self["key_red"] = StaticText(_("Remove Plugins"))
		self["key_green"] = StaticText(_("Download Plugins"))
		self["key_yellow"] = StaticText(_("Update Plugins"))
		self["key_blue"] = StaticText("")
		self[self.layout] = List([])
		self[self.layout].onSelectionChanged.append(self.selectionChanged)
		self.currentList = self[self.layout]
		self["quickselect"] = Label()
		self["quickselect"].hide()
		self["description"] = Label()
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "MenuActions"], {
			"ok": (self.keySelect, _("Start the highlighted plugin")),
			"cancel": (self.keyCancel, _("Close the Plugin Browser screen")),
			"menu": (self.keyMenu, _("Open the Plugin Browser settings screen"))
		}, prio=0, description=_("Plugin Browser Actions"))
		self["pluginRemoveActions"] = HelpableActionMap(self, ["ColorActions"], {
			"red": (self.keyRed, _("Remove Plugins")),
			"blue": (self.keyBlue, _("Start edit mode")),
		}, prio=0, description=_("Plugin Browser Select Actions"))
		self["pluginDownloadActions"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyGreen, _("Download Plugins")),
			"yellow": (self.keyYellow, _("Update Plugins"))
		}, prio=0, description=_("Plugin Browser Select Actions"))
		self["pluginEditActions"] = HelpableActionMap(self, ["ColorActions"], {
			"red": (self.keyRed, _("Reset sort order")),
			"green": (self.keyGreen, _("Toggle move mode")),
			"yellow": (self.keyYellow, _("Toggle the visibility of the highlighted plugin")),
			"blue": (self.keyBlue, _("Stop edit mode"))
		}, prio=0, description=_("Plugin Browser Edit Actions"))
		if config.usage.pluginListLayout.value == PLUGIN_LIST:
			self["navigationActions"] = HelpableActionMap(self, ["NavigationActions"], {
				"top": (self.keyTop, _("Move to the first line / screen")),
				"pageUp": (self.keyPageUp, _("Move up a screen")),
				"up": (self.keyUp, _("Move up a line")),
				"down": (self.keyDown, _("Move down a line")),
				"pageDown": (self.keyPageDown, _("Move down a screen")),
				"bottom": (self.keyBottom, _("Move to the last line / screen"))
			}, prio=0, description=_("Plugin Browser Navigation Actions"))
		else:
			self["navigationActions"] = HelpableActionMap(self, ["NavigationActions"], {
				"top": (self.keyTop, _("Move to the first item on the first screen")),
				"pageUp": (self.keyPageUp, _("Move up a screen")),
				"up": (self.keyUp, _("Move up a line")),
				"first": (self.keyFirst, _("Move to the first item on the current line")),
				"left": (self.keyLeft, _("Move to the previous item in list")),
				"right": (self.keyRight, _("Move to the next item in the list")),
				"last": (self.keyLast, _("Move to the last item on the current line")),
				"down": (self.keyDown, _("Move down a line")),
				"pageDown": (self.keyPageDown, _("Move down a screen")),
				"bottom": (self.keyBottom, _("Move to the last item on the last screen"))
			}, prio=0, description=_("Plugin Browser Navigation Actions"))
		smsMsg = _("SMS style QuickSelect entry selection")
		self["quickSelectActions"] = HelpableNumberActionMap(self, "NumberActions", {  # Action used by QuickSelect.
			"1": (self.keyNumberGlobal, smsMsg),
			"2": (self.keyNumberGlobal, smsMsg),
			"3": (self.keyNumberGlobal, smsMsg),
			"4": (self.keyNumberGlobal, smsMsg),
			"5": (self.keyNumberGlobal, smsMsg),
			"6": (self.keyNumberGlobal, smsMsg),
			"7": (self.keyNumberGlobal, smsMsg),
			"8": (self.keyNumberGlobal, smsMsg),
			"9": (self.keyNumberGlobal, smsMsg),
			"0": (self.keyNumberGlobal, smsMsg)
		}, prio=0, description=_("QuickSelect Actions"))
		self.pluginIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/plugin.png"))
		self.quickSelectTimer = eTimer()  # Initialize QuickSelect timer.
		self.quickSelectTimer.callback.append(self.quickSelectTimeout)
		self.quickSelectTimerType = 0
		self.quickSelect = ""
		self.quickSelectPos = -1
		self.onChangedEntry = []
		self.pluginList = []
		self.firstTime = True
		self.sortMode = False
		self.selectedPlugin = None
		self.opkgComponent = OpkgComponent()
		self.opkgComponent.addCallback(self.createFeedConfigCallback)
		if config.pluginfilter.userfeed.value != "http://" and not exists("/etc/opkg/user-feed.conf"):
			self.createFeedConfig()
		self.onLayoutFinish.append(self.layoutFinished)
		self.onFirstExecBegin.append(self.checkWarnings)
		self.onShown.append(self.updatePluginList)

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and not config.ParentalControl.config_sections.main_menu.value and config.ParentalControl.config_sections.plugin_browser.value

	def createGUIScreen(self, parent, desktop, updateonly=False):
		for item in self.renderer:
			if isinstance(item, GUIComponent) and item.__class__.__name__ == "Listbox":  # Is the listbox name "pluginGrid" available so this test can be more specific?
				for attribute, value in item.skinAttributes[:]:
					if attribute == "moveBackgroundColor":
						PluginBrowser.moveBackgroundColor = parseColor(value)
						item.skinAttributes.remove((attribute, value))
					elif attribute == "moveFontColor":
						PluginBrowser.moveFontColor = parseColor(value)
						item.skinAttributes.remove((attribute, value))
		Screen.createGUIScreen(self, parent, desktop, updateonly)

	def layoutFinished(self):
		self[self.layout].enableAutoNavigation(False)  # Override list box self navigation.

	def selectionChanged(self):
		if self.pluginList:
			item = self.pluginList[self.currentList.getSelectedIndex()]
			if item:
				package = item[0]
				name = package.name
				description = package.description
				self["description"].setText(description)
				if self.sortMode:
					self["key_yellow"].setText(_("Show") if config.usage.plugin_sort_weight.getConfigValue(name.lower(), "hidden") else _("Hide"))
			else:
				name = "-"
				description = ""
				if self.sortMode:
					self["key_yellow"].setText("")
			for callback in self.onChangedEntry:
				callback(name, description)

	def createFeedConfig(self):
		fileWriteLine("/etc/opkg/user-feed.conf", "src/gz user-feeds %s\n" % config.pluginfilter.userfeed.value, source=MODULE_NAME)
		self.opkgComponent.runCmd(OpkgComponent.CMD_CLEAN_REFRESH)
		Processing.instance.setDescription(_("Please wait while feeds are updated..."))
		Processing.instance.showProgress(endless=True)
		self["actions"].setEnabled(False)
		self["pluginRemoveActions"].setEnabled(False)
		self["pluginDownloadActions"].setEnabled(False)
		self["navigationActions"].setEnabled(False)
		self["quickSelectActions"].setEnabled(False)

	def createFeedConfigCallback(self, event, parameter):
		if event in (OpkgComponent.EVENT_DOWNLOAD, OpkgComponent.EVENT_UPDATED):
			print("[PluginBrowser] Feed '%s' %s." % (parameter, "downloaded" if event == OpkgComponent.EVENT_DOWNLOAD else "updated"))
		else:
			if event == OpkgComponent.EVENT_DONE:
				print("[PluginBrowser] Feed update completed successfully.")
				self["pluginDownloadActions"].setEnabled(True)
			else:
				print("[PluginBrowser] Error: Feed update error!  (%s: %s)" % (OpkgComponent.getEventText(self, event), parameter))
				self["pluginDownloadActions"].setEnabled(False)
			Processing.instance.hideProgress()
			self["actions"].setEnabled(True)
			self["pluginRemoveActions"].setEnabled(True)
			self["navigationActions"].setEnabled(True)
			self["quickSelectActions"].setEnabled(True)

	def checkWarnings(self):
		warnings = pluginComponent.getWarnings()
		if warnings:
			text = [_("Some plugins are not available:"), ""]
			for pluginName, error in warnings:
				text.append(_("%s  (%s)") % (pluginName, error))
			pluginComponent.resetWarnings()
			self.session.open(MessageBox, text="\n".join(text), type=MessageBox.TYPE_WARNING, windowTitle=self.getTitle())

	def updatePluginList(self):
		pluginList = pluginComponent.getPlugins(PluginDescriptor.WHERE_PLUGINMENU)
		emptySortOrder = config.usage.plugin_sort_weight.value or False
		self.pluginList = []
		for weight, plugin in enumerate(pluginList, start=1):
			plugin.listWeight = config.usage.plugin_sort_weight.getConfigValue(plugin.name.lower(), "sort") or weight * 10
			if self.sortMode or not config.usage.plugin_sort_weight.getConfigValue(plugin.name.lower(), "hidden"):
				self.pluginList.append((plugin, plugin.name, plugin.description, plugin.icon or self.pluginIcon))
		if config.usage.plugins_sort_mode.value == "a_z" or (not emptySortOrder and config.usage.plugins_sort_mode.value == "user"):
			self.pluginList.sort(key=lambda x: x[0].name.lower())
		elif config.usage.plugins_sort_mode.value == "user":
			self.pluginList.sort(key=lambda x: x[0].listWeight)
		if self.sortMode:
			self["key_red"].setText(_("Reset Order"))
			self["key_green"].setText(_("Move Mode Off") if self.selectedPlugin else _("Move Mode On"))
			self["key_blue"].setText(_("Edit Mode Off"))
			self["pluginRemoveActions"].setEnabled(False)
			self["pluginDownloadActions"].setEnabled(False)
			self["pluginEditActions"].setEnabled(True)
		else:
			self["key_red"].setText(_("Remove Plugins"))
			self["key_blue"].setText(_("Edit Mode On") if config.usage.plugins_sort_mode.value == "user" else "")
			self["pluginRemoveActions"].setEnabled(True)
			internetAccess = checkInternetAccess(FEED_SERVER, INTERNET_TIMEOUT)
			if internetAccess == 0:  # 0=Site reachable, 1=DNS error, 2=Other network error, 3=No link, 4=No active adapter.
				self["key_green"].setText(_("Download Plugins"))
				self["key_yellow"].setText(_("Update Plugins"))
				self["pluginDownloadActions"].setEnabled(True)
			else:
				self["key_green"].setText("")
				self["key_yellow"].setText("")
				self["pluginDownloadActions"].setEnabled(False)
			self["pluginEditActions"].setEnabled(False)
		self[self.layout].updateList(self.pluginList)

	def keyCancel(self):
		if self.sortMode:
			self.toggleSortMode()
		self.close()

	def toggleSortMode(self):
		if self.sortMode:
			self.sortMode = False
			for index, plugin in enumerate(self.pluginList):
				config.usage.plugin_sort_weight.changeConfigValue(plugin[0].name.lower(), "sort", (index + 1) * 10)
				if self.selectedPlugin and plugin[0] == self.selectedPlugin:
					self.pluginList.pop(index)
					self.pluginList.insert(index, (plugin[0], plugin[0].name, plugin[0].description, plugin[0].icon or self.pluginIcon))
					self.selectedPlugin = None
			config.usage.plugin_sort_weight.save()
			self.currentList.master.master.instance.clearBackgroundColorSelected()
			if self.moveFontColor:
				self.currentList.master.master.instance.clearForegroundColorSelected()
		else:
			self.sortMode = True
		self.updatePluginList()

	def keySelect(self):
		if self.pluginList:
			currentPlugin = self.pluginList[self.currentList.getSelectedIndex()][0]
			if self.sortMode:
				select = (self.selectedPlugin is None or self.selectedPlugin != currentPlugin)
				if not select:
					self.selectedPlugin = None
				for index, plugin in enumerate(self.pluginList):
					if currentPlugin == plugin[0]:
						self.pluginList.pop(index)
						self.pluginList.insert(index, (plugin[0], plugin[0].name, plugin[0].description, plugin[0].icon or self.pluginIcon))
						self.selectedPlugin = currentPlugin if select else None
						break
				if self.selectedPlugin:
					self["key_green"].setText(_("Move Mode Off"))
					self.currentList.master.master.instance.setBackgroundColorSelected(self.moveBackgroundColor)
					if self.moveFontColor:
						self.currentList.master.master.instance.setForegroundColorSelected(self.moveFontColor)
				else:
					self["key_green"].setText(_("Move Mode On"))
					self.currentList.master.master.instance.clearBackgroundColorSelected()
					if self.moveFontColor:
						self.currentList.master.master.instance.clearForegroundColorSelected()
				self.currentList.updateList(self.pluginList)
			else:
				currentPlugin(session=self.session)

	def keyMenu(self):
		def keyMenuCallback():
			if config.pluginfilter.userfeed.value != "http://":
				self.createFeedConfig()
			self.checkWarnings()
			self.updatePluginList()

		self.session.openWithCallback(keyMenuCallback, PluginBrowserSetup)

	def keyRed(self):
		if self.sortMode:
			config.usage.plugin_sort_weight.value = {}
			config.usage.plugin_sort_weight.save()
			self.updatePluginList()
		else:
			self.session.openWithCallback(self.childScreenClosedCallback, PluginAction, PluginAction.REMOVE)

	def keyGreen(self):
		if self.sortMode:
			if config.usage.plugins_sort_mode.value == "user" and self.sortMode:
				self.keySelect()
		else:
			self.session.openWithCallback(self.childScreenClosedCallback, PluginAction, PluginAction.DOWNLOAD)
			self.firstTime = False

	def keyYellow(self):
		if self.sortMode:
			plugin = self.pluginList[self.currentList.getSelectedIndex()][0]
			hidden = config.usage.plugin_sort_weight.getConfigValue(plugin.name.lower(), "hidden") or 0
			if hidden:
				config.usage.plugin_sort_weight.removeConfigValue(plugin.name.lower(), "hidden")
				self["key_yellow"].setText(_("Hide"))
			else:
				config.usage.plugin_sort_weight.changeConfigValue(plugin.name.lower(), "hidden", 1)
				self["key_yellow"].setText(_("Show"))
		else:
			self.session.openWithCallback(self.childScreenClosedCallback, PluginAction, PluginAction.UPDATE)

	def childScreenClosedCallback(self):
		self.checkWarnings()
		self.updatePluginList()

	def keyBlue(self):
		if config.usage.plugins_sort_mode.value == "user":
			self.toggleSortMode()
			self.selectionChanged()

	def keyTop(self):
		self.currentIndex = self.currentList.getSelectedIndex()
		self.currentList.goTop()
		if self.sortMode and self.selectedPlugin:
			self.moveAction()

	def keyPageUp(self):
		self.currentIndex = self.currentList.getSelectedIndex()
		self.currentList.goPageUp()
		if self.sortMode and self.selectedPlugin:
			self.moveAction()

	def keyUp(self):
		self.currentIndex = self.currentList.getSelectedIndex()
		self.currentList.goLineUp()
		if self.sortMode and self.selectedPlugin:
			self.moveAction()

	def keyFirst(self):
		self.currentIndex = self.currentList.getSelectedIndex()
		self.currentList.goFirst()
		if self.sortMode and self.selectedPlugin:
			self.moveAction()

	def keyLeft(self):
		self.currentIndex = self.currentList.getSelectedIndex()
		self.currentList.goLeft()
		if self.sortMode and self.selectedPlugin:
			self.moveAction()

	def keyRight(self):
		self.currentIndex = self.currentList.getSelectedIndex()
		self.currentList.goRight()
		if self.sortMode and self.selectedPlugin:
			self.moveAction()

	def keyLast(self):
		self.currentIndex = self.currentList.getSelectedIndex()
		self.currentList.goLast()
		if self.sortMode and self.selectedPlugin:
			self.moveAction()

	def keyDown(self):
		self.currentIndex = self.currentList.getSelectedIndex()
		self.currentList.goLineDown()
		if self.sortMode and self.selectedPlugin:
			self.moveAction()

	def keyPageDown(self):
		self.currentIndex = self.currentList.getSelectedIndex()
		self.currentList.goPageDown()
		if self.sortMode and self.selectedPlugin:
			self.moveAction()

	def keyBottom(self):
		self.currentIndex = self.currentList.getSelectedIndex()
		self.currentList.goBottom()
		if self.sortMode and self.selectedPlugin:
			self.moveAction()

	def moveAction(self):
		entry = self.pluginList.pop(self.currentIndex)
		newpos = self.currentList.getSelectedIndex()
		self.pluginList.insert(newpos, entry)
		self.currentList.updateList(self.pluginList)

	def keyNumberGlobal(self, digit):
		self.quickSelectTimer.stop()
		if self.lastKey != digit:  # Is this a different digit?
			self.nextKey()  # Reset lastKey again so NumericalTextInput triggers its key change.
			self.selectByStart()
			self.quickSelectPos += 1
		char = self.getKey(digit)  # Get char and append to text.
		self.quickSelect = "%s%s" % (self.quickSelect[:self.quickSelectPos], str(char))
		self["quickselect"].setText(self.quickSelect)
		self["quickselect"].show()
		self.quickSelectTimerType = 0
		self.quickSelectTimer.start(1000, True)  # Allow 1 second to select the desired character for the QuickSelect text.

	def quickSelectTimeout(self, force=False):
		if not force and self.quickSelectTimerType == 0:
			self.selectByStart()
			self.quickSelectTimerType = 1
			self.quickSelectTimer.start(1500, True)  # Allow 1.5 seconds before reseting the QuickSelect text.
		else:  # Timeout QuickSelect
			self.quickSelectTimer.stop()
			self.quickSelect = ""
			self.quickSelectPos = -1
		self.lastKey = -1  # Finalize current character.

	def selectByStart(self):  # Try to select what was typed so far.
		if self.pluginList and self.quickSelect:
			self["quickselect"].hide()
			self["quickselect"].setText("")
			pattern = self.quickSelect.lower()
			for index, item in enumerate(self.pluginList):
				package = item[0]
				if package.name.lower().startswith(pattern):  # Select first file starting with case insensitive QuickSelect text.
					self.currentList.setCurrentIndex(index)
					break

	def createSummary(self):
		return PluginBrowserSummary


class PluginBrowserSetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "PluginBrowser")
		choiceList = [("/", _("Internal flash"))]
		oldLocation = config.usage.piconInstallLocation.savedValue
		for partition in harddiskmanager.getMountedPartitions():
			if partition.device and fileAccess(partition.mountpoint, "w") and partition.filesystem() in ("ext3", "ext4"):  # Limit to physical drives with ext3 and ext4
				choiceList.append((partition.mountpoint, "%s (%s)" % (partition.description, partition.mountpoint)))
		if oldLocation and oldLocation not in [location[0] for location in choiceList]:  # Add old location if not in calculated list of locations to prevent a setting change.
			choiceList.append((oldLocation, oldLocation))
		config.usage.piconInstallLocation.setSelectionList(default="/", choices=sorted(choiceList))
		config.usage.piconInstallLocation.value = oldLocation

	def keySave(self):
		def keySaveCallback(answer):
			if answer:
				try:
					for dir in ("picon", "piconlcd"):
						destDir = join("/", dir)
						if exists(destDir):
							if islink(destDir):
								unlink(destDir)
							else:
								rmtree(destDir)
						srcDir = join(location, dir)
						makedirs(srcDir, mode=0o755, exist_ok=True)
						symlink(srcDir, destDir)
				except OSError as err:
					print("[PluginBrowserSetup] Error %d: Unable to create picon links!  (%s)" % (err.errno, err.strerror))
					self.session.open(MessageBox, _("Error: Creating picon target directory: (%s)") % err.strerror, type=MessageBox.TYPE_ERROR)
					config.usage.piconInstallLocation.cancel()
			else:
				config.usage.piconInstallLocation.cancel()
			Setup.keySave(self)

		location = config.usage.piconInstallLocation.value

		if location != "/" and location != config.usage.piconInstallLocation.savedValue:
			srcExists = False
			for dir in ("picon", "piconlcd"):
				destDir = join("/", dir)
				if exists(destDir) and not islink(destDir):
					srcExists = True
					break
			if srcExists:
				self.session.openWithCallback(keySaveCallback, MessageBox, _("The picon directory already exists and must be removed. Do you want to proceed?"), default=False, type=MessageBox.TYPE_YESNO, windowTitle=self.getTitle())
			else:
				keySaveCallback(True)
		elif location == "/" and config.usage.piconInstallLocation.savedValue != "/":  # remove link if the setting has been changed to flash
			errordir = ""
			try:
				for dir in ("/picon", "/piconlcd"):
					errordir = dir
					if islink(dir):
						unlink(dir)
			except OSError as err:
				print("[PluginBrowser] Error %d: Unable to remove picon link '%s'!  (%s)" % (err.errno, errordir, err.strerror))
			Setup.keySave(self)
		else:
			Setup.keySave(self)


class PluginBrowserSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self.skinName = ["PluginBrowserSummary"]
		self["entry"] = StaticText("")
		self["value"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent.selectionChanged()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self, name, description):
		self["entry"].setText(name)
		self["value"].setText(description)


class PluginAction(Screen, HelpableScreen, NumericalTextInput):
	skin = """
	<screen name="PluginAction" title="Plugin Browser Download" position="center,center" size="900,585" resolution="1280,720">
		<widget source="plugins" render="Listbox" position="0,0" size="e,500" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{
				"template":
					[
					MultiContentEntryPixmapAlphaBlend(pos=(5, 0), size=(60, 50), png=6, flags=BT_SCALE),
					MultiContentEntryText(pos=(70, 0), size=(810, 50), font=0, flags=RT_VALIGN_CENTER, text=2),
					MultiContentEntryText(pos=(70, 2), size=(530, 25), font=1, flags=RT_VALIGN_CENTER, text=3),
					MultiContentEntryText(pos=(610, 2), size=(220, 25), font=1, flags=RT_VALIGN_CENTER, text=5),
					MultiContentEntryText(pos=(70, 28), size=(760, 20), font=2, flags=RT_VALIGN_CENTER, text=4, color=0x00b0b0b0),
					MultiContentEntryPixmapAlphaBlend(pos=(840, 1), size=(48, 48), png=7, flags=BT_SCALE)
					],
				"fonts": [parseFont("Regular;25"), parseFont("Regular;20"), parseFont("Regular;16")],
				"itemHeight": 50
				}
			</convert>
		</widget>
		<widget name="quickselect" position="0,0" size="e,500" font="Regular;100" foregroundColor="#00fff000" halign="center" transparent="1" valign="center" zPosition="+1" />
		<widget name="description" position="0,e-75" size="e,25" font="Regular;20" valign="center" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="380,e-40" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-90,e-40" size="90,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	REMOVE = 0
	DOWNLOAD = 1
	UPDATE = 2
	MANAGE = 3

	# Skin template indexes:
	PLUGIN_PACKAGE = 0  # This is the full package name as used in opkg.
	PLUGIN_CATEGORY = 1  # This is only defined for category headings.
	PLUGIN_FORMATTED_CATEGORY = 2  # This is only defined for category headings.
	PLUGIN_NAME = 3  # This is only defined for plugin details and management.
	PLUGIN_DESCRIPTION = 4  # This is only defined for plugin details and management.
	PLUGIN_VERSION = 5  # This is only defined for plugin details and management.
	PLUGIN_LIST_ICON = 6  # This is always defined.
	PLUGIN_STATUS_ICON = 7  # This is only defined for management screens.
	PLUGIN_DISPLAY_CATEGORY = 8  # This is the same as PLUGIN_FORMATTED_CATEGORY but is always available for the summary screen.
	PLUGIN_INSTALLED = 9  # This is only defined for management screens and is not intended for display.
	PLUGIN_UPGRADABLE = 10  # This is only defined for management screens and is not intended for display.
	PLUGIN_NAME_VERSION = 11  # This is the name and the version and only defined for plugin details and management.

	INFO_PACKAGE = 0
	INFO_CATEGORY = 1
	INFO_NAME = 2
	INFO_DESCRIPTION = 3
	INFO_VERSION = 4
	INFO_INSTALLED = 5
	INFO_UPGRADE = 6

	def __init__(self, session, type=0):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		NumericalTextInput.__init__(self, handleTimeout=False, mode="SearchUpper")
		self.type = type
		self.setTitle({
			self.REMOVE: _("Remove Plugins"),
			self.DOWNLOAD: _("Download Plugins"),
			self.UPDATE: _("Update Plugins"),
			self.MANAGE: _("Manage Plugins")
		}.get(type, _("Unknown")))
		self["plugins"] = List([])
		self["plugins"].onSelectionChanged.append(self.selectionChanged)
		self["quickselect"] = Label()
		self["quickselect"].hide()
		text = _("Downloading plugin information. Please wait...") if type in (self.DOWNLOAD, self.UPDATE, self.MANAGE) else _("Getting plugin information. Please wait...")
		self["description"] = Label(text)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		description = {
			self.REMOVE: _("Plugin Browser Remove Actions"),
			self.DOWNLOAD: _("Plugin Browser Download Actions"),
			self.UPDATE: _("Plugin Browser Update Actions"),
			self.MANAGE: _("Plugin Browser Manage Actions")
		}.get(type, _("Unknown"))
		self["actions"] = HelpableActionMap(self, ["SelectCancelActions"], {
			"cancel": (self.keyCancel, _("Close the screen"))
		}, prio=0, description=description)
		buttonHelp = {
			self.REMOVE: _("Add/Remove highlighted plugin to/from remove list"),
			self.DOWNLOAD: _("Add/Remove highlighted plugin to/from download list"),
			self.UPDATE: _("Add/Remove highlighted plugin to/from update list"),
			self.MANAGE: _("Manage the highlighted plugin")
		}.get(type, _("Unknown"))
		self["selectAction"] = HelpableActionMap(self, ["OkCancelActions"], {
			"ok": (self.keySelect, buttonHelp),
		}, prio=0, description=description)
		buttonHelp = {
			self.REMOVE: _("Remove the selected list of plugins"),
			self.DOWNLOAD: _("Download the selected list of plugins"),
			self.UPDATE: _("Update the selected list of plugins"),
			self.MANAGE: _("Manage the highlighted plugin")
		}.get(type, _("Unknown"))
		self["performAction"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyGreen, buttonHelp),
		}, prio=0, description=description)
		self["logAction"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyYellow, _("Show the last opkg command's output"))
		}, prio=0, description=description)
		self["logAction"].setEnabled(False)
		self["navigationActions"] = HelpableActionMap(self, ["NavigationActions"], {
			"top": (self["plugins"].goTop, _("Move to the first item on the first screen")),
			"pageUp": (self["plugins"].goPageUp, _("Move up a screen")),
			"up": (self["plugins"].goLineUp, _("Move up a line")),
			# "first": (self.keyTop, _("Move to the first item on the current line")),
			"left": (self.keyPreviousCategory, _("Move to the previous category in the list")),
			"right": (self.keyNextCategory, _("Move to the next category in the list")),
			# "last": (self.keyBottom, _("Move to the last item on the current line")),
			"down": (self["plugins"].goLineDown, _("Move down a line")),
			"pageDown": (self["plugins"].goPageDown, _("Move down a screen")),
			"bottom": (self["plugins"].goBottom, _("Move to the last item on the last screen"))
		}, prio=0, description=description)
		smsMsg = _("SMS style QuickSelect entry selection")
		self["quickSelectActions"] = HelpableNumberActionMap(self, "NumberActions", {  # Action used by QuickSelect.
			"1": (self.keyNumberGlobal, smsMsg),
			"2": (self.keyNumberGlobal, smsMsg),
			"3": (self.keyNumberGlobal, smsMsg),
			"4": (self.keyNumberGlobal, smsMsg),
			"5": (self.keyNumberGlobal, smsMsg),
			"6": (self.keyNumberGlobal, smsMsg),
			"7": (self.keyNumberGlobal, smsMsg),
			"8": (self.keyNumberGlobal, smsMsg),
			"9": (self.keyNumberGlobal, smsMsg),
			"0": (self.keyNumberGlobal, smsMsg)
		}, prio=0, description=_("QuickSelect Actions"))
		self["quickSelectActions"].setEnabled(False)
		self.expandableIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/plugin_expandable.png"))
		self.expandedIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/plugin_expanded.png"))
		self.verticalIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/plugin_vertical.png"))
		self.installableIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/installable.png"))
		self.installIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/install.png"))
		self.installedIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/installed.png"))
		self.upgradableIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/upgradeable.png"))
		self.removeIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/remove.png"))
		self.kernelVersion = "-%s" % BoxInfo.getItem("kernel", "")
		self.quickSelectTimer = eTimer()  # Initialize QuickSelect timer.
		self.quickSelectTimer.callback.append(self.quickSelectTimeout)
		self.quickSelectTimerType = 0
		self.quickSelectCategory = ""
		self.quickSelect = ""
		self.quickSelectPos = -1
		self.onChangedEntry = []
		self.pluginList = []
		self.currentCategory = None
		self.expanded = []
		self.selectedInstallItems = []
		self.selectedRemoveItems = []
		self.pluginsChanged = False
		self.reloadSettings = False
		self.currentBootLogo = None
		self.currentSettings = None
		self.logData = ""
		self.opkgComponent = OpkgComponent()
		self.opkgComponent.addCallback(self.fetchOpkgDataCallback)
		opkgFilterArguments = [ENIGMA_PREFIX % "*"]
		if config.pluginfilter.kernel.value:
			opkgFilterArguments.append(KERNEL_PREFIX % "*")
		self.opkgFilterArguments = {"arguments": opkgFilterArguments}
		# print("[PluginBrowser] DEBUG: Opkg filter is '%s'." % self.opkgFilterArguments)
		displayFilter = []
		for filter in sorted(PACKAGE_CATEGORIES.keys()):
			if filter in ("extraopkgpackages", "src"):
				continue
			if getattr(config.pluginfilter, filter).value:
				displayFilter.append((KERNEL_PREFIX % "")[:-1] if filter == "kernel" else ENIGMA_PREFIX % filter)
		# for count, filter in enumerate(displayFilter, start=1):
		# 	print("[PluginBrowser] DEBUG: Plugin display filter %d is '%s'." % (count, filter))
		# print("[PluginBrowser] DEBUG: Display filter is '%s'." % (r"^(%s-)" % "-|".join(displayFilter) if displayFilter else r"^$"))
		self.displayFilter = compile(r"^(%s-)" % "-|".join(displayFilter) if displayFilter else r"^$")
		displayExclude = []
		if not config.pluginfilter.extraopkgpackages.value:
			displayExclude.extend(["-dev", "-dbg", "-doc", "-meta", "-staticdev"])
		if not config.pluginfilter.src.value:
			displayExclude.append("-src")
		# for count, exclude in enumerate(displayExclude, start=1):
		# 	print("[PluginBrowser] DEBUG: Plugin exclude filter %d is '%s'." % (count, exclude))
		# print("[PluginBrowser] DEBUG: Exclude filter is '%s'." % (r"(%s)$" % "|".join(displayExclude) if displayExclude else r"^$"))
		self.displayExclude = compile(r"(%s)$" % "|".join(displayExclude) if displayExclude else r"^$")
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["plugins"].enableAutoNavigation(False)
		text = _("Downloading plugin information. Please wait...") if self.type in (self.DOWNLOAD, self.UPDATE, self.MANAGE) else _("Getting plugin information. Please wait...")
		self.setWaiting(text)
		if self.type == self.REMOVE:
			self.opkgComponent.runCmd(OpkgComponent.CMD_LIST_INSTALLED, self.opkgFilterArguments)
		elif self.type == self.DOWNLOAD:
			self.opkgComponent.runCmd(OpkgComponent.CMD_REFRESH_INSTALLABLE, self.opkgFilterArguments)
		elif self.type == self.UPDATE:
			self.opkgComponent.runCmd(OpkgComponent.CMD_REFRESH_UPDATES, self.opkgFilterArguments)
		elif self.type == self.MANAGE:
			internetAccess = checkInternetAccess(FEED_SERVER, INTERNET_TIMEOUT)
			if internetAccess == 0:  # 0=Site reachable, 1=DNS error, 2=Other network error, 3=No link, 4=No active adapter.
				self.opkgComponent.runCmd(OpkgComponent.CMD_REFRESH_INFO, self.opkgFilterArguments)
			elif internetAccess == 1:
				self["description"].setText(_("Feed server DNS error!"))
				print("[PluginBrowser] Error: Feed server DNS error!")
				self.setWaiting(None)
			elif internetAccess == 2:
				self["description"].setText(_("Feed server access error!"))
				print("[PluginBrowser] Error: Feed server access error!")
				self.setWaiting(None)
			elif internetAccess == 3:
				self["description"].setText(_("Network adapter not connected to a network!"))
				print("[PluginBrowser] Error: Network adapter not connected to a network!")
				self.setWaiting(None)
			elif internetAccess == 4:
				self["description"].setText(_("No network adapters enabled/available!"))
				print("[PluginBrowser] Error: No network adapters enabled/available!")
				self.setWaiting(None)

	def selectionChanged(self):
		current = self["plugins"].getCurrent()
		if current:
			category = current[self.PLUGIN_CATEGORY]
			if isinstance(category, str):  # Entry is a category.
				if category in self.expanded:  # This allows QuickSelect to start searching the current category from the category heading.
					self["key_green"].setText(_("Collapse"))
					self.quickSelectCategory = current[self.PLUGIN_DISPLAY_CATEGORY]
				else:  # QuickSelect disabled on closed categories.
					self["key_green"].setText(_("Expand"))
					self.quickSelectCategory = ""
			else:
				label = {
					self.REMOVE: _("Remove Plugin"),
					self.DOWNLOAD: _("Download Plugin"),
					self.UPDATE: _("Update Plugin"),
					self.MANAGE: _("Remove Plugin") if current[self.PLUGIN_INSTALLED] else _("Download Plugin")
				}.get(self.type, _("Unknown"))
				self["key_green"].setText(label)
				self.quickSelectCategory = current[self.PLUGIN_DISPLAY_CATEGORY]  # This allows QuickSelect to search the current category.
			self["quickSelectActions"].setEnabled(self.quickSelectCategory != "")
		for callback in self.onChangedEntry:
			callback()

	def keyCancel(self):
		if self.pluginsChanged:
			plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
		if self.reloadSettings:
			self["description"].setText(_("Reloading bouquets and services."))
			eDVBDB.getInstance().reloadBouquets()
			eDVBDB.getInstance().reloadServicelist()
		pluginComponent.readPluginList(resolveFilename(SCOPE_PLUGINS))
		self.close()

	def keySelect(self):
		current = self["plugins"].getCurrent()
		if current:
			category = current[self.PLUGIN_CATEGORY]
			if isinstance(category, str):  # Entry is a category.
				if category in self.expanded:
					self.expanded.remove(category)
				else:
					self.expanded.append(category)
			else:
				package = current[self.PLUGIN_PACKAGE]
				# Don't use multiselect for bootlogo , settings or picons
				if package.startswith("enigma2-plugin-bootlogo-") or package.startswith("enigma2-plugin-settings-") or package.startswith("enigma2-plugin-picons-"):
					self.selectedRemoveItems = []
					self.selectedInstallItems = []
					self.keyGreen()
					return
				if self.type == self.MANAGE:  # support only remove or install and not mixing
					if current[self.PLUGIN_INSTALLED]:
						if package in self.selectedRemoveItems:
							self.selectedRemoveItems.remove(package)
						else:
							self.selectedRemoveItems.append(package)
						self.selectedInstallItems = []
					else:
						if package in self.selectedInstallItems:
							self.selectedInstallItems.remove(package)
						else:
							self.selectedInstallItems.append(package)
						self.selectedRemoveItems = []
				elif self.type == self.REMOVE:
					if package in self.selectedRemoveItems:
						self.selectedRemoveItems.remove(package)
					else:
						self.selectedRemoveItems.append(package)
				else:
					if package in self.selectedInstallItems:
						self.selectedInstallItems.remove(package)
					else:
						self.selectedInstallItems.append(package)
			self.displayPluginList(self.pluginList)
			installText = ngettext("%d package marked for install.", "%d packages marked for install.", len(self.selectedInstallItems)) % len(self.selectedInstallItems) if self.selectedInstallItems else ""
			removeText = ngettext("%d package marked for remove.", "%d packages marked for remove.", len(self.selectedRemoveItems)) % len(self.selectedRemoveItems) if self.selectedRemoveItems else ""
			markedText = installText if installText else removeText
			markedText = "\n%s" % markedText if markedText else ""
			self["description"].setText("%s%s" % (self.descriptionText, markedText))

	def keyGreen(self):
		def keyGreenCallback(answer):
			if answer:
				args = {}
				if self.type in (self.REMOVE, self.MANAGE) and (self.selectedRemoveItems or current[self.PLUGIN_INSTALLED]):
					args["arguments"] = self.selectedRemoveItems or [package]
					args["options"] = ["--autoremove", "--force-depends"]
					if package.startswith("bootlogo-"):
						args["options"].append("--force-remove")
					# args["testMode"] = True
					self.opkgComponent.runCmd(OpkgComponent.CMD_REMOVE, args)
					text = _("Please wait while the plugin is removed.")
				elif self.type in (self.DOWNLOAD, self.MANAGE) and (self.selectedInstallItems or not current[self.PLUGIN_INSTALLED]):
					oldPackage = None
					if package.startswith("enigma2-plugin-bootlogo-") and self.currentBootLogo:
						oldPackage = self.currentBootLogo
						args["options"] = ["--autoremove", "--force-depends", "--force-remove"]
					elif package.startswith("enigma2-plugin-settings-") and self.currentSettings:
						oldPackage = self.currentSettings
						args["options"] = ["--autoremove", "--force-depends"]
						self.reloadSettings = True
					elif package.startswith("enigma2-plugin-picons-") and config.usage.piconInstallLocation.value:
						location = config.usage.piconInstallLocation.value
						try:
							for dir in ("picon", "piconlcd"):
								srcDir = join(location, dir)
								if not exists(srcDir):
									makedirs(srcDir, mode=0o755, exist_ok=True)
						except OSError as err:
							print("[PluginAction] Error %d: Unable to create picon location!  (%s)" % (err.errno, err.strerror))
					if oldPackage:
						args["arguments"] = [oldPackage, package]
						# args["testMode"] = True
						self.opkgComponent.runCmd(OpkgComponent.CMD_REPLACE, args)
						text = _("Please wait while the plugin is replaced.")
					else:
						args["arguments"] = self.selectedInstallItems or [package]
						# args["testMode"] = True
						self.opkgComponent.runCmd(OpkgComponent.CMD_INSTALL, args)
						text = _("Please wait while the plugin is downloaded.")
						if package.startswith("enigma2-plugin-settings-"):
							self.reloadSettings = True
				elif self.type == self.UPDATE and (self.selectedInstallItems or current[self.PLUGIN_UPGRADABLE]):
					args["arguments"] = self.selectedInstallItems or [package]
					args["options"] = ["--force-overwrite"]
					# args["testMode"] = True
					self.opkgComponent.runCmd(OpkgComponent.CMD_UPDATE, args)
					text = _("Please wait while the plugin is updated.")
				self.setWaiting(text)
				self.logData = ""

		current = None
		if self.selectedRemoveItems and self.selectedInstallItems:  # mixing install and remove is currently not possible
			pass
		elif self.selectedInstallItems:
			text = _("Do you want to download '%s'?") % ", ".join(self.selectedInstallItems)
			default = True
			package = " ".join(self.selectedInstallItems)
			self.session.openWithCallback(keyGreenCallback, MessageBox, text=text, default=default, windowTitle=self.getTitle())
		elif self.selectedRemoveItems:
			text = _("Do you want to remove '%s'?") % ", ".join(self.selectedRemoveItems)
			default = False
			package = " ".join(self.selectedRemoveItems)
			self.session.openWithCallback(keyGreenCallback, MessageBox, text=text, default=default, windowTitle=self.getTitle())
		else:
			current = self["plugins"].getCurrent()
			package = current[self.PLUGIN_PACKAGE]
			if self.type in (self.REMOVE, self.MANAGE) and current[self.PLUGIN_INSTALLED]:
				text = _("Do you want to remove '%s'?") % package
				default = False
			elif self.type in (self.DOWNLOAD, self.MANAGE) and not current[self.PLUGIN_INSTALLED]:
				oldPackage = None
				if package.startswith("enigma2-plugin-bootlogo-") and self.currentBootLogo:
					oldPackage = self.currentBootLogo
				elif package.startswith("enigma2-plugin-settings-") and self.currentSettings:
					oldPackage = self.currentSettings
				if oldPackage:
					text = _("Do you want to replace '%s' with '%s?") % (oldPackage, package)
					default = False
				else:
					text = _("Do you want to download '%s'?") % package
					default = True
			elif self.type == self.UPDATE and current[self.PLUGIN_UPGRADABLE]:
				text = _("Do you want to update '%s'?") % package
				default = False
			self.session.openWithCallback(keyGreenCallback, MessageBox, text=text, default=default, windowTitle=self.getTitle())

	def keyYellow(self):
		self.session.open(PluginActionLog, self.logData)

	def keyPreviousCategory(self):
		current = self["plugins"].getCurrent()
		if current:
			self["plugins"].goLineUp()
			current = self["plugins"].getCurrent()
			while current[1] is None:
				self["plugins"].goLineUp()
				current = self["plugins"].getCurrent()

	def keyNextCategory(self):
		current = self["plugins"].getCurrent()
		if current:
			self["plugins"].goLineDown()
			current = self["plugins"].getCurrent()
			while current[1] is None:
				self["plugins"].goLineDown()
				current = self["plugins"].getCurrent()

	def fetchOpkgDataCallback(self, event, parameter):
		match event:
			case OpkgComponent.EVENT_BOOTLOGO_FOUND:
				print("[PluginBrowser] Bootlogo package '%s' found." % parameter)
				self.currentBootLogo = parameter
			case OpkgComponent.EVENT_SETTINGS_FOUND:
				print("[PluginBrowser] Settings package '%s' found." % parameter)
				self.currentSettings = parameter
			case OpkgComponent.EVENT_LOG:
				print("[PluginBrowser] Command log data added to log screen.")
				self.logData = "%s%s" % (self.logData, parameter)
			case OpkgComponent.EVENT_LIST_INSTALLED_DONE | OpkgComponent.EVENT_LIST_INSTALLABLE_DONE | OpkgComponent.EVENT_LIST_UPDATES_DONE | OpkgComponent.EVENT_INFO_DONE:
				self.processListCallback(parameter)  # The parameter is a list of dictionary items for each package processed.
			case OpkgComponent.EVENT_REMOVE_DONE:
				print("[PluginBrowser] Package(s) '%s' removed." % "', '".join(parameter))
				self.opkgComponent.runCmd(OpkgComponent.CMD_INFO if self.type == self.MANAGE else OpkgComponent.CMD_LIST_INSTALLED, self.opkgFilterArguments)
			case OpkgComponent.EVENT_DOWNLOAD_DONE:
				print("[PluginBrowser] Package(s) '%s' downloaded." % "', '".join(parameter))
				self.opkgComponent.runCmd(OpkgComponent.CMD_INFO if self.type == self.MANAGE else OpkgComponent.CMD_LIST_INSTALLABLE, self.opkgFilterArguments)
			case OpkgComponent.EVENT_UPDATE_DONE:
				print("[PluginBrowser] Package(s) '%s' updated." % "', '".join(parameter))
				self.opkgComponent.runCmd(OpkgComponent.CMD_INFO if self.type == self.MANAGE else OpkgComponent.CMD_LIST_UPDATES, self.opkgFilterArguments)
			case OpkgComponent.EVENT_OPKG_MISMATCH:
				print("[PluginBrowser] Command '%s' downloading '%s' returned a mismatch error!  (Got %s bytes, expected %s bytes)" % parameter)
			case OpkgComponent.EVENT_CANT_INSTALL:
				print("[PluginBrowser] Command '%s' downloading '%s' returned a installation error!" % parameter)
			case OpkgComponent.EVENT_NETWORK_ERROR:
				print("[PluginBrowser] Command '%s' downloading '%s' returned a network error!  (Wget error %s)" % parameter)
			case OpkgComponent.EVENT_DONE:
				print("[PluginBrowser] Opkg command '%s' completed." % self.opkgComponent.getCommandText(parameter))
				self.setWaiting(None)
			case OpkgComponent.EVENT_ERROR:
				print("[PluginBrowser] Opkg command '%s' error!  (%s)" % (parameter[1], self.opkgComponent.getCommandText(parameter[0])))
			case _:
				print("[PluginBrowser] Opkg command '%s' returned event '%s'." % (self.opkgComponent.getCommandText(self.opkgComponent.currentCommand), self.opkgComponent.getEventText(event)))

		haveLogs = self.logData != ""
		self["logAction"].setEnabled(haveLogs)
		self["key_yellow"].setText(_("Show Log") if haveLogs else "")

	# Opkg info returns data with any of the possible keys:
	# 	"Package",  "Version",  "Depends",  "Pre-Depends",  "Recommends",  "Suggests",  "Provides",  "Replaces",  "Conflicts",
	# 	"Status",  "Section",  "Essential",  "Architecture",  "Maintainer", "MD5sum",  "Size",  "Filename",  "Conffiles", "Source",
	# 	"Description",  "Installed-Size",  "Installed-Time",  "Tags".  The keys "Installed" and "Update" are added by Opkg.py.
	# Only "Package" is guaranteed to be always be present.
	#
	def processListCallback(self, packages):
		pluginList = []
		allCount = 0
		installCount = 0
		updateCount = 0
		for package in packages:
			packageFile = package["Package"]
			if self.displayFilter.search(packageFile) and self.displayExclude.search(packageFile) is None:
				allCount += 1
				parts = packageFile.split("-")
				count = len(parts)
				if count > 2:
					if parts[0] == "enigma2" and parts[1] == "plugin":
						packageCategory = parts[2]
						packageName = "-".join(parts[3:])
					elif parts[0] == "kernel" and parts[1] == "module":
						packageCategory = "kernel"
						packageName = ("-".join(parts[2:])).replace(self.kernelVersion, "")
				else:
					print("[PluginBrowser] Error: Plugin package '%s' has no name!" % packageFile)
					continue
				packageDescription = package["Description"] if "Description" in package else ""
				packageVersion = package["Version"] if "Version" in package else ""
				packageInstalled = package["Installed"] if "Installed" in package else False
				packageUpdate = "Update" in package
				if packageInstalled:
					installCount += 1
				if packageUpdate:
					updateCount += 1
				data = (packageFile, packageCategory, packageName, packageDescription, packageVersion, packageInstalled, packageUpdate)
				pluginList.append(data)
		# self.setWaiting(None)
		print("[PluginBrowser] Packages: %d returned from opkg, %d matched, %d installed, %d have updates." % (len(packages), allCount, installCount, updateCount))
		installedText = ngettext("%d package installed.", "%d packages installed.", installCount) % installCount
		updateText = ngettext("%d package has an update", "%d packages have updates.", updateCount) % updateCount
		if self.type == self.REMOVE:
			self.descriptionText = installedText
		elif self.type == self.DOWNLOAD:
			self.descriptionText = ngettext("%d package installable.", "%d packages installable.", allCount) % allCount
		elif self.type == self.UPDATE:
			self.descriptionText = updateText
		else:
			self.descriptionText = "%s %s %s" % (ngettext("%d package found.", "%d packages found.", allCount) % allCount, installedText, updateText)
		self["description"].setText(self.descriptionText)
		self.displayPluginList(pluginList)
		self.pluginList = pluginList

	def displayPluginList(self, pluginList):
		categories = {}
		for info in pluginList:
			category = info[self.INFO_CATEGORY]
			if category in categories:
				categories[category].append(info)
			else:
				categories[category] = [info]
		plugins = []
		for category in sorted(categories.keys()):
			if category in self.expanded:
				plugins.append((category, category, PACKAGE_CATEGORIES.get(category, category), None, None, None, self.expandedIcon, None, PACKAGE_CATEGORIES.get(category, category), None, None, None))
				for info in sorted(categories[category], key=lambda x: x[self.INFO_PACKAGE]):
					installed = info[self.INFO_INSTALLED]
					icon = self.installedIcon if installed else self.installableIcon
					if installed and info[self.INFO_UPGRADE]:
						icon = self.upgradableIcon
					if info[self.INFO_PACKAGE] in self.selectedInstallItems:
						icon = self.installIcon
					if info[self.INFO_PACKAGE] in self.selectedRemoveItems:
						icon = self.removeIcon
					version = info[self.INFO_VERSION]
					if version.startswith("experimental-"):
						version = "exp-%s" % version[13:]
					version = version.replace("devel", "dev")
					version = version.replace("-git", "+git")
					parts = version.split("+")
					for part in parts[:]:
						if part.startswith("git"):
							parts.remove(part)
					version = "+".join(parts)
					plugins.append((info[self.INFO_PACKAGE], None, None, info[self.INFO_NAME], info[self.INFO_DESCRIPTION], version, self.verticalIcon, icon, PACKAGE_CATEGORIES.get(category, category), info[self.INFO_INSTALLED], info[self.INFO_UPGRADE], "%s (%s)" % (info[self.INFO_NAME], version)))
			else:
				plugins.append((category, category, PACKAGE_CATEGORIES.get(category, category), None, None, None, self.expandableIcon, None, PACKAGE_CATEGORIES.get(category, category), None, None, None))
		self["plugins"].setList(plugins)

	def setWaiting(self, text):
		if text:
			self.actionMaps = (self["actions"].getEnabled(), self["selectAction"].getEnabled(), self["performAction"].getEnabled(), self["logAction"].getEnabled(), self["navigationActions"].getEnabled(), self["quickSelectActions"].getEnabled())
			self["actions"].setEnabled(False)
			self["selectAction"].setEnabled(False)
			self["performAction"].setEnabled(False)
			self["logAction"].setEnabled(False)
			self["navigationActions"].setEnabled(False)
			self["quickSelectActions"].setEnabled(False)
			Processing.instance.setDescription(text)
			Processing.instance.showProgress(endless=True)
		else:
			Processing.instance.hideProgress()
			self["actions"].setEnabled(self.actionMaps[0])
			self["selectAction"].setEnabled(self.actionMaps[1])
			self["performAction"].setEnabled(self.actionMaps[2])
			self["logAction"].setEnabled(self.actionMaps[3])
			self["navigationActions"].setEnabled(self.actionMaps[4])
			self["quickSelectActions"].setEnabled(self.actionMaps[5])

	def keyNumberGlobal(self, digit):
		self.quickSelectTimer.stop()
		if self.lastKey != digit:  # Is this a different digit?
			self.nextKey()  # Reset lastKey again so NumericalTextInput triggers its key change.
			self.selectByStart()
			self.quickSelectPos += 1
		char = self.getKey(digit)  # Get char and append to text.
		self.quickSelect = "%s%s" % (self.quickSelect[:self.quickSelectPos], str(char))
		self["quickselect"].setText(self.quickSelect)
		self["quickselect"].show()
		self.quickSelectTimerType = 0
		self.quickSelectTimer.start(1000, True)  # Allow 1 second to select the desired character for the QuickSelect text.

	def quickSelectTimeout(self, force=False):
		if not force and self.quickSelectTimerType == 0:
			self.selectByStart()
			self.quickSelectTimerType = 1
			self.quickSelectTimer.start(1500, True)  # Allow 1.5 seconds before reseting the QuickSelect text.
		else:  # Timeout QuickSelect
			self.quickSelectTimer.stop()
			self.quickSelect = ""
			self.quickSelectPos = -1
		self.lastKey = -1  # Finalize current character.

	def selectByStart(self):  # Try to select what was typed so far.
		pluginList = self["plugins"].getList()
		if pluginList and self.quickSelect and self.quickSelectCategory:
			self["quickselect"].hide()
			self["quickselect"].setText("")
			pattern = self.quickSelect.lower()
			for index, item in enumerate(pluginList):
				if item[self.PLUGIN_DISPLAY_CATEGORY] != self.quickSelectCategory:
					continue
				name = item[self.PLUGIN_NAME]
				if name and name.lower().startswith(pattern):  # Select first package name starting with case insensitive QuickSelect text.
					self["plugins"].setCurrentIndex(index)
					break

	def createSummary(self):
		return PluginActionSummary


class PluginActionSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self.skinName = ["PluginActionSummary"]
		self["category"] = StaticText("")
		self["name"] = StaticText("")
		self["description"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent.selectionChanged()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self):
		current = self.parent["plugins"].getCurrent()
		if current:
			self["category"].setText(current[self.parent.PLUGIN_DISPLAY_CATEGORY])
			self["name"].setText(current[self.parent.PLUGIN_NAME])
			self["description"].setText(current[self.parent.PLUGIN_DESCRIPTION])
		else:
			self["category"].setText("")
			self["name"].setText("")
			self["description"].setText("")


class PluginActionLog(Screen, HelpableScreen):
	skin = """
	<screen name="PluginActionLog" title="Plugin Action Log" position="center,center" size="950,590" resolution="1280,720">
		<widget name="log" position="0,0" size="e,e-50" font="Regular;20" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, logData):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setTitle(_("Plugin Action Log"))
		self["log"] = ScrollLabel()
		self["log"].setText(logData)
		self["key_red"] = StaticText(_("Close"))
		self["actions"] = HelpableActionMap(self, ["CancelActions", "NavigationActions"], {
			"cancel": (self.close, _("Close the screen")),
			"top": (self["log"].moveTop, _("Move to first line / screen")),
			"pageUp": (self["log"].pageUp, _("Move up a screen")),
			"up": (self["log"].moveUp, _("Move up a line")),
			"down": (self["log"].moveDown, _("Move down a line")),
			"pageDown": (self["log"].pageDown, _("Move down a screen")),
			"bottom": (self["log"].moveBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Plugin Action Log Actions"))
