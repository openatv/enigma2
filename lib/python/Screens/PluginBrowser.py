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
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.Processing import Processing
from Screens.Screen import Screen, ScreenSummary
from Screens.Setup import Setup
from Tools.Directories import SCOPE_GUISKIN, SCOPE_PLUGINS, fileAccess, fileReadLines, fileWriteLine, fileWriteLines, resolveFilename
from Tools.LoadPixmap import LoadPixmap
from Tools.NumericalTextInput import NumericalTextInput

MODULE_NAME = __name__.split(".")[-1]

INTERNET_TIMEOUT = 2
FEED_SERVER = "feeds2.mynonpublic.com"
ENIGMA_PREFIX = "enigma2-plugin-%s"
PACKAGE_PREFIX = "%s"
SOFTCAM_PREFIX = "enigma2-plugin-softcams-%s"
KERNEL_PREFIX = "kernel-module-%s"

PLUGIN_CATEGORIES = {
	"": _("Other Packages"),
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
	"subscription": _("Subscription Packages"),
	"systemplugins": _("System Plugin Packages"),
	"vix": _("OpenViX Packages"),
	"weblinks": _("Web Link Packages")
}
PACKAGE_CATEGORIES = {
	"": _("Other Packages"),
	"base": _("Base Packages"),
	# "base/utils": _("Base Utility Packages"),
	"base/shell": _("Base Shell Packages"),
	"console": _("Console Packages"),
	# "console/admin": _("Console Administrative Packages"),  # Now bundled into the "Other Packages" category.
	# "console/multimedia": _("Console Multimedia Packages"),  # Now bundled into the "Other Packages" category.
	"console/network": _("Console Network Packages"),
	"console/utils": _("Console Utility Packages"),
	"devel": _("Development Packages"),
	"devel/python": _("Python Development Packages"),
	# "doc": _("Documentation Packages"),  # Now bundled into the "Other Packages" category.
	# "enigma2": _("Enigma2 Packages"),  # Now bundled into the "Other Packages" category.
	# "font": _("Font Packages"),  # Now bundled into the "Other Packages" category.
	"kernel": _("Kernel Packages"),
	"libs": _("Library Packages"),
	"multimedia": _("Multimedia Packages"),
	"network": _("Network Packages"),
	"plugin": _("Plugin Packages"),
	"universe/otherosfs": _("File System Packages"),
	"utils": _("Utility Packages"),
	"x11": _("X11 Packages")
}
PACKAGE_CATEGORY_MAPPINGS = {
	"console/tools": "console/utils",
	"python-devel": "devel/python",
	"net": "network",
	"kernel/modules": "kernel",
	"libs/multimedia": "libs",
	"libs/network": "libs",
	"x11/base": "x11",
	"x11/fonts": "x11",
	"x11/gnome": "x11",
	"x11/gnome/libs": "x11",
	"x11/libs": "x11",
	"x11/utils": "x11"
}

PLUGIN_LIST = 0
PLUGIN_GRID = 1

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
config.pluginfilter.subscription = ConfigYesNo(default=True)
config.pluginfilter.systemplugins = ConfigYesNo(default=True)
config.pluginfilter.vix = ConfigYesNo(default=False)
config.pluginfilter.weblinks = ConfigYesNo(default=True)
config.pluginfilter.userfeed = ConfigText(default="http://", fixed_size=False)


class PluginBrowser(Screen, NumericalTextInput, ProtectedScreen):
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
		Screen.__init__(self, session, mandatoryWidgets=[self.layout], enableHelp=True)
		NumericalTextInput.__init__(self, handleTimeout=False, mode="SearchUpper")
		self.skinName = ["PluginBrowserList" if config.usage.pluginListLayout.value == PLUGIN_LIST else "PluginBrowserGrid", "PluginBrowser"]
		self.setTitle(_("Plugin Browser"))
		ProtectedScreen.__init__(self)
		self["key_menu"] = StaticText(_("MENU"))
		self["key_red"] = StaticText()
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
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
			"blue": (self.keyEditMode, _("Start edit mode")),
		}, prio=0, description=_("Plugin Browser Select Actions"))
		self["pluginDownloadActions"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyGreen, _("Install Plugins")),
			"yellow": (self.keyYellow, _("Update Plugins"))
		}, prio=0, description=_("Plugin Browser Select Actions"))
		self["pluginEditActions"] = HelpableActionMap(self, ["ColorActions"], {
			"red": (self.keyRed, _("Reset sort order")),
			"green": (self.keyGreen, _("Toggle move mode")),
			"yellow": (self.keyYellow, _("Toggle the visibility of the highlighted plugin")),
			"blue": (self.keyEditMode, _("Stop edit mode"))
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
		self.internetAccess = 0  # 0=Site reachable, 1=DNS error, 2=Other network error, 3=No link, 4=No active adapter.
		if config.pluginfilter.userfeed.value != "http://" and not exists("/etc/opkg/user-feed.conf"):
			self.createFeedConfig()
		self.onFirstExecBegin.append(self.checkWarnings)  # This is needed to avoid a modal screen issue.
		self.onLayoutFinish.append(self.layoutFinished)

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
		def createFeedConfigCallback(event, eventData):
			if event == opkgComponent.EVENT_CLEAN_ERROR:
				print("[PluginBrowser] Error: There was an issue in the feed update! Please reboot and check the file system for any errors.")
			elif event in (opkgComponent.EVENT_DOWNLOAD, opkgComponent.EVENT_UPDATED):
				print(f"[PluginBrowser] Feed '{eventData}' {'downloaded' if event == opkgComponent.EVENT_DOWNLOAD else 'updated'}.")
			elif event == opkgComponent.EVENT_REFRESH_DONE:
				if eventData:
					print(f"[PluginBrowser] Warning: {eventData} feed(s) were unable to be reloaded!")
					self["pluginDownloadActions"].setEnabled(False)
				else:
					print("[PluginBrowser] Feed update completed successfully.")
					self["pluginDownloadActions"].setEnabled(True)
			elif event == opkgComponent.EVENT_DONE:
				Processing.instance.hideProgress()
				self["actions"].setEnabled(True)
				self["pluginRemoveActions"].setEnabled(True)
				self["navigationActions"].setEnabled(True)
				self["quickSelectActions"].setEnabled(True)

		fileWriteLine("/etc/opkg/user-feed.conf", f"src/gz user-feeds {config.pluginfilter.userfeed.value}\n", source=MODULE_NAME)
		opkgComponent = OpkgComponent()
		opkgComponent.addCallback(createFeedConfigCallback)
		opkgComponent.runCommand(opkgComponent.CMD_CLEAN_REFRESH)
		Processing.instance.setDescription(_("Please wait while feeds are updated..."))
		Processing.instance.showProgress(endless=True)
		self["actions"].setEnabled(False)
		self["pluginRemoveActions"].setEnabled(False)
		self["pluginDownloadActions"].setEnabled(False)
		self["navigationActions"].setEnabled(False)
		self["quickSelectActions"].setEnabled(False)

	def checkWarnings(self):
		def checkWarningsCallback(answer):
			if answer:
				pluginComponent.resetWarnings()

		warnings = pluginComponent.getWarnings()
		if warnings:
			count = len(warnings)
			text = [ngettext("%d plugin is not available:", "%d plugins are not available:", count) % count, ""]
			for pluginName, error in warnings:
				text.append(f"- {pluginName}\n    {error}")
			options = [
				(ngettext("Keep warning", "Keep warnings", count), False),
				(ngettext("Clear warning", "Clear warnings", count), True)
			]
			self.session.openWithCallback(checkWarningsCallback, MessageBox, text="\n".join(text), type=MessageBox.TYPE_YESNO, list=options, default=0, typeIcon=MessageBox.TYPE_WARNING, windowTitle=self.getTitle())

	def layoutFinished(self):
		self[self.layout].enableAutoNavigation(False)  # Override list box self navigation.
		self.callLater(self.checkInternet)
		self.updatePluginList()

	def checkInternet(self):
		self.internetAccess = checkInternetAccess(FEED_SERVER, INTERNET_TIMEOUT)
		self.updateButtons()

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
		self[self.layout].updateList(self.pluginList)
		self.updateButtons()

	def updateButtons(self):
		if self.sortMode:
			self["key_red"].setText(_("Reset Order"))
			self["key_green"].setText(_("Move Mode Off") if self.selectedPlugin else _("Move Mode On"))
			self["key_blue"].setText(_("Edit Mode Off"))
			self["pluginRemoveActions"].setEnabled(False)
			self["pluginDownloadActions"].setEnabled(False)
			self["pluginEditActions"].setEnabled(True)
		else:
			self["key_red"].setText(_("Remove Plugins"))
			if self.internetAccess == 0:  # 0=Site reachable, 1=DNS error, 2=Other network error, 3=No link, 4=No active adapter.
				self["key_green"].setText(_("Install Plugins"))
				self["key_yellow"].setText(_("Update Plugins"))
				self["pluginDownloadActions"].setEnabled(True)
			else:
				self["key_green"].setText("")
				self["key_yellow"].setText("")
				self["pluginDownloadActions"].setEnabled(False)
			self["key_blue"].setText(_("Edit Mode On") if config.usage.plugins_sort_mode.value == "user" else "")
			self["pluginRemoveActions"].setEnabled(True)
			self["pluginEditActions"].setEnabled(False)

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
			self.session.openWithCallback(self.childScreenClosedCallback, PackageAction, PackageAction.MODE_REMOVE)

	def keyGreen(self):
		if self.sortMode:
			if config.usage.plugins_sort_mode.value == "user" and self.sortMode:
				self.keySelect()
		else:
			self.session.openWithCallback(self.childScreenClosedCallback, PackageAction, PackageAction.MODE_INSTALL)
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
			self.session.openWithCallback(self.childScreenClosedCallback, PackageAction, PackageAction.MODE_UPDATE)

	def childScreenClosedCallback(self):
		self.checkWarnings()
		self.updatePluginList()

	def keyEditMode(self):
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
		newPos = self.currentList.getSelectedIndex()
		self.pluginList.insert(newPos, entry)
		self.currentList.updateList(self.pluginList)

	def keyNumberGlobal(self, digit):
		self.quickSelectTimer.stop()
		if self.lastKey != digit:  # Is this a different digit?
			self.nextKey()  # Reset lastKey again so NumericalTextInput triggers its key change.
			self.selectByStart()
			self.quickSelectPos += 1
		char = self.getKey(digit)  # Get char and append to text.
		self.quickSelect = f"{self.quickSelect[:self.quickSelectPos]}{str(char)}"
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
		self["key_yellow"] = StaticText(_("Reset Feeds"))
		self["actions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyResetFeeds, _("Reset (clear and reload) the feeds"))
		}, prio=0, description=_("Plugin Browser Actions"))
		self["resetFeedsAction"] = HelpableActionMap(self, ["CancelActions"], {
			"cancel": (self.keyResetFeedsCancel, _("Cancel the Reset Feeds command currently being processed"))
		}, prio=0, description=_("Plugin Browser Actions"))
		self["resetFeedsAction"].setEnabled(False)
		choiceList = [("/", _("Internal flash"))]
		oldLocation = config.usage.piconInstallLocation.savedValue
		for partition in harddiskmanager.getMountedPartitions():
			if partition.device and fileAccess(partition.mountpoint, "w") and partition.fileSystem() in ("ext3", "ext4"):  # Limit to physical drives with ext3 and ext4
				choiceList.append((partition.mountpoint, f"{partition.description} ({partition.mountpoint})"))
		if oldLocation and oldLocation not in [location[0] for location in choiceList]:  # Add old location if not in calculated list of locations to prevent a setting change.
			choiceList.append((oldLocation, oldLocation))
		config.usage.piconInstallLocation.setSelectionList(default="/", choices=sorted(choiceList))
		config.usage.piconInstallLocation.value = oldLocation
		self.opkgComponent = OpkgComponent()
		self.opkgComponent.addCallback(self.keyResetFeedsCallback)
		self.cleanError = False
		self.refreshIncomplete = 0
		self.addSaveNotifier(self.onUpdateSettings)
		self.onClose.append(self.clearSaveNotifiers)

	def keyResetFeeds(self):
		self.suspendAllActionMaps()
		Processing.instance.setDescription(f"{_('Please wait while the feeds are reset (cleared and reloaded)...')}\n\n{_('Warning: Canceling this process will leave the feeds in an incomplete and unusable state!')}")
		Processing.instance.showProgress(endless=True)
		self["actions"].setEnabled(False)
		self["resetFeedsAction"].setEnabled(True)
		self.opkgComponent.runCommand(self.opkgComponent.CMD_CLEAN_REFRESH)

	def keyResetFeedsCallback(self, event, eventData):
		match event:
			case self.opkgComponent.EVENT_CLEAN_ERROR:
				self.cleanError = True
			case self.opkgComponent.EVENT_CLEAN_DONE:
				pass  # Ignore the clean successful message.
			case self.opkgComponent.EVENT_DOWNLOAD | self.opkgComponent.EVENT_FEED_UPDATED:
				pass  # Ignore the feed download and updated messages.
			case self.opkgComponent.EVENT_REFRESH_DONE:
				if eventData:
					self.refreshIncomplete = eventData
			case self.opkgComponent.EVENT_DONE:
				Processing.instance.hideProgress()
				self["resetFeedsAction"].setEnabled(False)
				self["actions"].setEnabled(True)
				self.resumeAllActionMaps()
				if self.cleanError:
					self.session.open(MessageBox, _("Error: There was an issue in the reset of the feeds! Please reboot the %s %s and check the file system for any errors before trying this command again.") % getBoxDisplayName(), type=MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
				if self.refreshIncomplete:
					self.session.open(MessageBox, _("Warning: %d feeds were unable to be reloaded!") % self.refreshIncomplete, type=MessageBox.TYPE_WARNING, windowTitle=self.getTitle())
			case _:
				print(f"[PluginBrowser] Setup Error: Unexpected opkg event '{self.opkgComponent.getEventText(event)}'!")

	def keyResetFeedsCancel(self):
		self.opkgComponent.stop()
		Processing.instance.hideProgress()
		self["resetFeedsAction"].setEnabled(False)
		self["actions"].setEnabled(True)
		self.resumeAllActionMaps()

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
					print(f"[PluginBrowser] Setup Error {err.errno}: Unable to create picon links!  ({err.strerror})")
					self.session.open(MessageBox, _("Error: Creating picon target directory: (%s)") % err.strerror, type=MessageBox.TYPE_ERROR)
					config.usage.piconInstallLocation.cancel()
			else:
				config.usage.piconInstallLocation.cancel()
			Setup.keySave(self)
		self.swapGitHubDNS()
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
			errorDir = ""
			try:
				for dir in ("/picon", "/piconlcd"):
					errorDir = dir
					if islink(dir):
						unlink(dir)
			except OSError as err:
				print(f"[PluginBrowser] Setup Error {err.errno}: Unable to remove picon link '{errorDir}'!  ({err.strerror})")
			Setup.keySave(self)
		else:
			Setup.keySave(self)

	def swapGitHubDNS(self):
		if config.usage.alternateGitHubDNS.isChanged():
			lines = fileReadLines("/etc/hosts", source=MODULE_NAME)
			lines = [line for line in lines if "raw.githubusercontent.com" not in line]
			if config.usage.alternateGitHubDNS.value:
				lines += ["%s raw.githubusercontent.com" % ip for ip in ("185.199.108.133", "185.199.109.133", "185.199.110.133", "185.199.111.133", "2606:50c0:8000::154", "2606:50c0:8001::154", "2606:50c0:8002::154", "2606:50c0:8003::154")]
			fileWriteLines("/etc/hosts", lines, source=MODULE_NAME)

	def onUpdateSettings(self):
		if config.usage.pluginListLayout.isChanged():
			oldDialogIndex = None
			oldSummarys = (-1, None)
			for index, dialog in enumerate(self.session.dialog_stack):
				if isinstance(dialog[0], PluginBrowser):
					oldDialogIndex = (index, dialog[1])
					oldSummarys = dialog[0].summaries[:]
					break
			if oldDialogIndex[0] != -1:
				newDialog = self.session.instantiateDialog(PluginBrowser)
				newDialog.summaries = oldSummarys
				newDialog.isTmp = False
				newDialog.callback = None
				self.session.dialog_stack[oldDialogIndex[0]] = (newDialog, oldDialogIndex[1])


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


class PackageAction(Screen, NumericalTextInput):
	skin = """
	<screen name="PackageAction" title="Plugin Browser Action" position="center,center" size="900,585" resolution="1280,720">
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

	MODE_REMOVE = 0
	MODE_INSTALL = 1
	MODE_UPDATE = 2
	MODE_MANAGE = 3
	MODE_PACKAGE = 4
	MODE_SOFTCAM = 5
	MODE_NAMES = {
		0: "MODE_REMOVE",
		1: "MODE_INSTALL",
		2: "MODE_UPDATE",
		3: "MODE_MANAGE",
		4: "MODE_PACKAGE",
		5: "MODE_SOFTCAM"
	}

	MANAGE_OPTIONS = {
		MODE_MANAGE: (MODE_MANAGE, _("Plugin"), _("Plugins"), _("plugin"), _("plugins"), ENIGMA_PREFIX, PLUGIN_CATEGORIES),
		MODE_PACKAGE: (MODE_PACKAGE, _("Package"), _("Packages"), _("package"), _("packages"), PACKAGE_PREFIX, PLUGIN_CATEGORIES | PACKAGE_CATEGORIES),
		MODE_SOFTCAM: (MODE_SOFTCAM, _("Softcam"), _("Softcams"), _("softcam"), _("softcams"), SOFTCAM_PREFIX, PLUGIN_CATEGORIES),
	}
	DATA_MODE = 0
	DATA_UPPER_SINGULAR = 1
	DATA_UPPER_PLURAL = 2
	DATA_LOWER_SINGULAR = 3
	DATA_LOWER_PLURAL = 4
	DATA_FILTER = 5
	DATA_CATEGORIES = 6

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

	def __init__(self, session, mode=MODE_REMOVE):
		Screen.__init__(self, session, enableHelp=True)
		NumericalTextInput.__init__(self, handleTimeout=False, mode="SearchUpper")
		self.skinName = ["PackageAction", "PluginAction"]
		self.modeData = self.MANAGE_OPTIONS.get(mode, self.MANAGE_OPTIONS[self.MODE_MANAGE])
		self.mode = min(mode, self.MODE_MANAGE)
		self.setTitle({
			self.MODE_REMOVE: _("Remove Plugins"),
			self.MODE_INSTALL: _("Install Plugins"),
			self.MODE_UPDATE: _("Update Plugins"),
			self.MODE_MANAGE: _("Manage %s") % self.modeData[self.DATA_UPPER_PLURAL]
		}.get(self.mode, _("Unknown")))
		self["plugins"] = List([])
		self["plugins"].onSelectionChanged.append(self.selectionChanged)
		self["quickselect"] = Label()
		self["quickselect"].hide()
		text = _("Getting plugin information. Please wait...") if self.mode == self.MODE_REMOVE else _("Downloading plugin information. Please wait...")
		self["description"] = Label(text)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		description = {
			self.MODE_REMOVE: _("Plugin Browser Remove Actions"),
			self.MODE_INSTALL: _("Plugin Browser Install Actions"),
			self.MODE_UPDATE: _("Plugin Browser Update Actions"),
			self.MODE_MANAGE: _("%s Browser Manage Actions") % self.modeData[self.DATA_UPPER_SINGULAR]
		}.get(self.mode, _("Unknown"))
		self["actions"] = HelpableActionMap(self, ["SelectCancelActions"], {
			"cancel": (self.keyCancel, _("Close the screen"))
		}, prio=0, description=description)
		buttonHelp = {
			self.MODE_REMOVE: _("Add/Remove highlighted plugin to/from remove list"),
			self.MODE_INSTALL: _("Add/Remove highlighted plugin to/from install list"),
			self.MODE_UPDATE: _("Add/Remove highlighted plugin to/from update list"),
			self.MODE_MANAGE: _("Manage the highlighted %s") % self.modeData[self.DATA_LOWER_SINGULAR]
		}.get(self.mode, _("Unknown"))
		self["selectAction"] = HelpableActionMap(self, ["OkCancelActions"], {
			"ok": (self.keySelect, buttonHelp)
		}, prio=0, description=description)
		buttonHelp = {
			self.MODE_REMOVE: _("Remove the selected plugin / list of plugins"),
			self.MODE_INSTALL: _("Install the selected plugin / list of plugins"),
			self.MODE_UPDATE: _("Update the selected plugin / list of plugins"),
			self.MODE_MANAGE: _("Manage the highlighted %s / list of %s") % (self.modeData[self.DATA_LOWER_SINGULAR], self.modeData[self.DATA_LOWER_PLURAL])
		}.get(self.mode, _("Unknown"))
		self["performAction"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyGreen, buttonHelp)
		}, prio=0, description=description)
		self["performAction"].setEnabled(False)
		self["logAction"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyShowLog, _("Show the last opkg command's output"))
		}, prio=0, description=description)
		self["logAction"].setEnabled(False)
		self["navigationActions"] = HelpableActionMap(self, ["NavigationActions", "PreviousNextActions"], {
			"top": (self["plugins"].goTop, _("Move to the first item on the first screen")),
			"pageUp": (self["plugins"].goPageUp, _("Move up a screen")),
			"up": (self["plugins"].goLineUp, _("Move up a line")),
			"first": (self.keyPreviousCategory, _("Move to the previous category in the list")),
			"previous": (self.keyPreviousCategory, _("Move to the previous category in the list")),
			"last": (self.keyNextCategory, _("Move to the next category in the list")),
			"next": (self.keyNextCategory, _("Move to the next category in the list")),
			"down": (self["plugins"].goLineDown, _("Move down a line")),
			"pageDown": (self["plugins"].goPageDown, _("Move down a screen")),
			"bottom": (self["plugins"].goBottom, _("Move to the last item on the last screen"))
		}, prio=0, description=description)
		self["legacyNavigationActions"] = HelpableActionMap(self, ["NavigationActions"], {
			"left": (self.keyPreviousCategory, _("Move to the previous category in the list")),
			"right": (self.keyNextCategory, _("Move to the next category in the list")),
		}, prio=0, description=description)
		self["legacyNavigationActions"].setEnabled(not config.misc.actionLeftRightToPageUpPageDown.value)
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
		self.kernelVersion = f"-{BoxInfo.getItem('kernel', '')}"
		self.quickSelectTimer = eTimer()  # Initialize QuickSelect timer.
		self.quickSelectTimer.callback.append(self.quickSelectTimeout)
		self.quickSelectTimerType = 0
		self.quickSelectCategory = ""
		self.quickSelect = ""
		self.quickSelectPos = -1
		self.onChangedEntry = []
		self.processing = False
		self.pluginList = []
		self.currentCategory = None
		self.expanded = []
		self.selectedRemoveItems = []
		self.selectedInstallItems = []
		self.selectedUpdateItems = []
		self.pluginsChanged = False
		self.reloadSettings = False
		self.currentBootLogo = None
		self.currentSettings = None
		self.logData = ""
		self.opkgComponent = OpkgComponent()
		self.opkgComponent.addCallback(self.fetchOpkgDataCallback)
		opkgFilterArguments = [self.modeData[self.DATA_FILTER] % "*"]
		displayExclude = []
		if mode <= self.MODE_MANAGE:
			if config.pluginfilter.kernel.value:
				opkgFilterArguments.append(KERNEL_PREFIX % "*")
			displayFilter = []
			for filter in sorted(PLUGIN_CATEGORIES.keys()):
				if filter in ("", "extraopkgpackages", "src"):
					continue
				if getattr(config.pluginfilter, filter).value:
					displayFilter.append((KERNEL_PREFIX % "")[:-1] if filter == "kernel" else self.modeData[self.DATA_FILTER] % filter)
			self.displayFilter = compile(r"^(%s-)" % "-|".join(displayFilter)) if displayFilter else None
			if not config.pluginfilter.extraopkgpackages.value:
				displayExclude.extend(["-dev", "-dbg", "-doc", "-meta", "-staticdev"])
			if not config.pluginfilter.src.value:
				displayExclude.append("-src")
		else:
			self.displayFilter = compile(r"^(%s-)" % (SOFTCAM_PREFIX % "*")) if mode == self.MODE_SOFTCAM else None
			displayExclude = ["-dev", "-dbg", "-doc", "-meta", "-staticdev", "-src"]
		self.opkgFilterArguments = {"arguments": opkgFilterArguments}
		self.displayExclude = compile(r"(%s)$" % "|".join(displayExclude) if displayExclude else r"^$")
		# print(f"[PluginBrowser] DEBUG: Opkg filter is '{self.opkgFilterArguments}'.")
		# for count, filter in enumerate(displayFilter, start=1):
		# 	print(f"[PluginBrowser] DEBUG: Plugin display filter {count} is '{filter}'.")
		# print("[PluginBrowser] DEBUG: Display filter is '%s'." % (r"^(%s-)" % "-|".join(displayFilter) if displayFilter else r"^$"))
		# for count, exclude in enumerate(displayExclude, start=1):
		# 	print(f"[PluginBrowser] DEBUG: Plugin exclude filter {count} is '{exclude}'.")
		# print("[PluginBrowser] DEBUG: Exclude filter is '%s'." % (r"(%s)$" % "|".join(displayExclude) if displayExclude else r"^$"))
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["plugins"].enableAutoNavigation(False)
		self.setWaiting(self["description"].getText())
		match self.mode:
			case self.MODE_REMOVE:
				self.opkgComponent.runCommand(self.opkgComponent.CMD_LIST_INSTALLED, self.opkgFilterArguments)
			case self.MODE_INSTALL:
				self.opkgComponent.runCommand(self.opkgComponent.CMD_REFRESH_INSTALLABLE, self.opkgFilterArguments)
			case self.MODE_UPDATE:
				self.opkgComponent.runCommand(self.opkgComponent.CMD_REFRESH_UPDATES, self.opkgFilterArguments)
			case self.MODE_MANAGE:
				match checkInternetAccess(FEED_SERVER, INTERNET_TIMEOUT):  # 0=Site reachable, 1=DNS error, 2=Other network error, 3=No link, 4=No active adapter.
					case 0:
						self.opkgComponent.runCommand(self.opkgComponent.CMD_REFRESH_INFO, self.opkgFilterArguments)
					case 1:
						self["description"].setText(_("Feed server DNS error!"))
						print("[PluginBrowser] PackageAction Error: Feed server DNS error!")
						self.setWaiting(None)
					case 2:
						self["description"].setText(_("Feed server access error!"))
						print("[PluginBrowser] PackageAction Error: Feed server access error!")
						self.setWaiting(None)
					case 3:
						self["description"].setText(_("Network adapter not connected to a network!"))
						print("[PluginBrowser] PackageAction Error: Network adapter not connected to a network!")
						self.setWaiting(None)
					case 4:
						self["description"].setText(_("No network adapters enabled/available!"))
						print("[PluginBrowser] PackageAction Error: No network adapters enabled/available!")
						self.setWaiting(None)

	def selectionChanged(self):
		label = ""
		current = self["plugins"].getCurrent()
		if current:
			category = current[self.PLUGIN_CATEGORY]
			if not isinstance(category, str) or self.selectedRemoveItems or self.selectedInstallItems or self.selectedUpdateItems:
				label = {
					self.MODE_REMOVE: _("Remove Plugins") if len(self.selectedRemoveItems) > 1 else _("Remove Plugin"),
					self.MODE_INSTALL: _("Install Plugins") if len(self.selectedInstallItems) > 1 else _("Install Plugin"),
					self.MODE_UPDATE: _("Update Plugins") if len(self.selectedUpdateItems) > 1 else _("Update Plugin"),
					self.MODE_MANAGE: (_("Remove %s") if current[self.PLUGIN_INSTALLED] else _("Install %s")) % self.modeData[self.DATA_UPPER_PLURAL]
				}.get(self.mode, _("Unknown"))
			self.quickSelectCategory = current[self.PLUGIN_DISPLAY_CATEGORY] if category is None or category in self.expanded else ""  # Allows QuickSelect to start searching the current category from the category heading. QuickSelect disabled on closed categories.
			self["quickSelectActions"].setEnabled(self.quickSelectCategory != "")
		self["key_green"].setText(label)
		self["performAction"].setEnabled(label != "")
		for callback in self.onChangedEntry:
			callback()

	def keyCancel(self):
		if self.processing:
			self.opkgComponent.stop()
			self.setWaiting(None)
			print("[PluginBrowser] PackageAction Note: User aborted the 'opkg' plugin refresh!")
		else:
			if self.pluginsChanged:
				plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
			if self.reloadSettings:
				self["description"].setText(_("Reloading bouquets and services."))
				eDVBDB.getInstance().reloadServicelist()
				eDVBDB.getInstance().reloadBouquets()
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
				if package.startswith("enigma2-plugin-bootlogo-") or package.startswith("enigma2-plugin-settings-") or package.startswith("enigma2-plugin-picons-"):  # Don't use MultiSelect for bootlogo, settings or picons.
					self.selectedRemoveItems = []
					self.selectedInstallItems = []
					self.selectedUpdateItems = []
					self.keyGreen()
					return
				match self.mode:
					case self.MODE_MANAGE:  # Install and remove actions can't be mixed, only support install or remove actions at any one time.
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
					case self.MODE_REMOVE:
						if package in self.selectedRemoveItems:
							self.selectedRemoveItems.remove(package)
						else:
							self.selectedRemoveItems.append(package)
					case self.MODE_INSTALL:
						if package in self.selectedInstallItems:
							self.selectedInstallItems.remove(package)
						else:
							self.selectedInstallItems.append(package)
					case self.MODE_UPDATE:
						if package in self.selectedUpdateItems:
							self.selectedUpdateItems.remove(package)
						else:
							self.selectedUpdateItems.append(package)
			self.displayPluginList(self.pluginList, False)
			removeText = ngettext("%d package marked for remove.", "%d packages marked for remove.", len(self.selectedRemoveItems)) % len(self.selectedRemoveItems) if self.selectedRemoveItems else ""
			installText = ngettext("%d package marked for install.", "%d packages marked for install.", len(self.selectedInstallItems)) % len(self.selectedInstallItems) if self.selectedInstallItems else ""
			updateText = ngettext("%d package marked for update.", "%d packages marked for update.", len(self.selectedUpdateItems)) % len(self.selectedUpdateItems) if self.selectedUpdateItems else ""
			markedText = installText or removeText or updateText
			markedText = f"\n{markedText}" if markedText else ""
			self["description"].setText(f"{self.descriptionText}{markedText}")

	def keyGreen(self):
		def confirmSelection(prompt, items, default):
			if len(items) > 15:
				items = "'\n    '".join(items[0:15])
				items = f"'{items}'\n    ..."
			else:
				items = "'\n    '".join(items)
				items = f"'{items}'"
			self.session.openWithCallback(keyGreenCallback, MessageBox, text=f"{prompt}\n    {items}", default=default, windowTitle=self.getTitle())

		def keyGreenCallback(answer):
			if answer:
				args = {}
				if self.selectedRemoveItems:
					args["arguments"] = self.selectedRemoveItems
					args["options"] = {"remove": ["--autoremove", "--force-depends"]}
					if self.selectedRemoveItems[0].startswith("bootlogo-"):
						args["options"]["remove"].append("--force-remove")
					# args["debugMode"] = True
					# args["testMode"] = True
					self.opkgComponent.runCommand(self.opkgComponent.CMD_REMOVE, args)
					text = ngettext("Please wait while the plugin is removed.", "Please wait while the plugins are removed.", len(args["arguments"]))
				elif self.selectedInstallItems:
					package = self.selectedInstallItems[0]
					replace = False
					if package.startswith("enigma2-plugin-bootlogo-") and self.currentBootLogo:
						replace = True
						args["options"] = {"remove": ["--autoremove", "--force-depends", "--force-remove"]}
					elif package.startswith("enigma2-plugin-settings-") and self.currentSettings:
						replace = True
						args["options"] = {"remove": ["--autoremove", "--force-depends"]}
					elif package.startswith("enigma2-plugin-picons-") and config.usage.piconInstallLocation.value:
						location = config.usage.piconInstallLocation.value
						try:
							for dir in ("picon", "piconlcd"):
								srcDir = join(location, dir)
								if not exists(srcDir):
									makedirs(srcDir, mode=0o755, exist_ok=True)
						except OSError as err:
							print(f"[PluginBrowser] PackageAction Error {err.errno}: Unable to create picon location!  ({err.strerror})")
					args["arguments"] = self.selectedInstallItems
					# args["debugMode"] = True
					# args["testMode"] = True
					if replace:
						self.opkgComponent.runCommand(self.opkgComponent.CMD_REPLACE, args)
						text = _("Please wait while the plugin is replaced.")
					else:
						self.opkgComponent.runCommand(self.opkgComponent.CMD_INSTALL, args)
						text = ngettext("Please wait while the plugin is installed.", "Please wait while the plugins are installed.", len(args["arguments"]))
					if package.startswith("enigma2-plugin-settings-"):
						self.reloadSettings = True
				elif self.selectedUpdateItems:
					args["arguments"] = self.selectedUpdateItems
					args["options"] = {"install": ["--force-overwrite"]}
					# args["debugMode"] = True
					# args["testMode"] = True
					self.opkgComponent.runCommand(self.opkgComponent.CMD_UPDATE, args)
					text = _("Please wait while the plugin is updated.")
				self.setWaiting(text)
				self.logData = ""
				self.selectedInstallItems = []
				self.selectedRemoveItems = []
				self.selectedUpdateItems = []

		current = self["plugins"].getCurrent()
		if self.selectedRemoveItems and self.selectedInstallItems and self.selectedUpdateItems:  # Mixing install, remove and update is currently not possible.
			pass
		elif self.selectedRemoveItems:
			confirmSelection(_("Do you want to remove:"), self.selectedRemoveItems, False)
		elif self.selectedInstallItems:
			confirmSelection(_("Do you want to install:"), self.selectedInstallItems, True)
		elif self.selectedUpdateItems:
			confirmSelection(_("Do you want to update:"), self.selectedUpdateItems, True)
		elif current:
			package = current[self.PLUGIN_PACKAGE]
			if self.mode in (self.MODE_REMOVE, self.MODE_MANAGE) and current[self.PLUGIN_INSTALLED]:
				self.selectedRemoveItems = [package]
				text = f"{_('Do you want to remove:')}\n   '{package}'"
				default = False
			elif self.mode in (self.MODE_INSTALL, self.MODE_MANAGE) and not current[self.PLUGIN_INSTALLED]:
				oldPackage = None
				if package.startswith("enigma2-plugin-bootlogo-") and self.currentBootLogo:
					oldPackage = self.currentBootLogo
				elif package.startswith("enigma2-plugin-settings-") and self.currentSettings:
					oldPackage = self.currentSettings
				if oldPackage:
					self.selectedInstallItems = [oldPackage, package]
					text = f"{_('Do you want to replace:')}\n    '{oldPackage}'\nwith:\n    '{package}'"
					default = False
				else:
					self.selectedInstallItems = [package]
					text = f"{_('Do you want to install:')}\n    '{package}'"
					default = True
			elif self.mode == self.MODE_UPDATE and current[self.PLUGIN_UPGRADABLE]:
				self.selectedUpdateItems = [package]
				text = f"{_('Do you want to update:')}\n    '{package}'"
				default = False
			self.session.openWithCallback(keyGreenCallback, MessageBox, text=text, default=default, windowTitle=self.getTitle())

	def keyShowLog(self):
		self.session.open(PackageActionLog, self.logData)

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

	def fetchOpkgDataCallback(self, event, eventData):
		match event:
			case self.opkgComponent.EVENT_LIST_INSTALLED_DONE | self.opkgComponent.EVENT_LIST_INSTALLABLE_DONE | self.opkgComponent.EVENT_LIST_UPDATES_DONE | self.opkgComponent.EVENT_INFO_DONE:
				# print(f"[PluginBrowser] PackageAction DEBUG: '{self.opkgComponent.getCommandText(self.opkgComponent.command)}' returned event '{self.opkgComponent.getEventText(event)}' with {len(eventData)} parameters.")
				self.processListCallback(eventData)  # The eventData is a list of dictionary items for each package processed.
			case self.opkgComponent.EVENT_LOG:
				print("[PluginBrowser] PackageAction: Command log data added to log screen.")
				self.logData = f"{self.logData}{eventData}"
			# case self.opkgComponent.EVENT_DOWNLOAD:
			# 	print(f"[PluginBrowser] PackageAction: Downloading package '{eventData}'.")
			# case self.opkgComponent.EVENT_FEED_UPDATED:
			# 	print(f"[PluginBrowser] PackageAction: Updated feed package '{eventData}'.")
			case self.opkgComponent.EVENT_DOWNLOAD | self.opkgComponent.EVENT_FEED_UPDATED | self.opkgComponent.EVENT_REFRESH_DONE:
				pass  # Ignore the feed download and updated messages.
			case self.opkgComponent.EVENT_BOOTLOGO_FOUND:
				print(f"[PluginBrowser] PackageAction: Bootlogo package '{eventData}' found.")
				self.currentBootLogo = eventData
			case self.opkgComponent.EVENT_SETTINGS_FOUND:
				print(f"[PluginBrowser] PackageAction: Settings package '{eventData}' found.")
				self.currentSettings = eventData
			case self.opkgComponent.EVENT_REMOVE:
				# print(f"[PluginBrowser] PackageAction: Removing package '{eventData}'.")
				pass  # Ignore the removed items as they will be in the log.
			case self.opkgComponent.EVENT_INSTALL:
				# print(f"[PluginBrowser] PackageAction: Installing package '{eventData}'.")
				pass  # Ignore the installing items as they will be in the log.
			case self.opkgComponent.EVENT_CONFIGURING:
				# print(f"[PluginBrowser] PackageAction: Configuring package '{eventData}'.")
				pass  # Ignore the configuring items as they will be in the log.
			case self.opkgComponent.EVENT_UPDATE:
				print(f"[PluginBrowser] PackageAction: Updating package '{eventData[0]}' from version {eventData[1]} to version {eventData[2]}.")
			case self.opkgComponent.EVENT_REMOVE_DONE:
				print("[PluginBrowser] PackageAction: Package(s) '%s' removed." % "', '".join(eventData))
				self.nextCommand = self.opkgComponent.CMD_INFO if self.mode == self.MODE_MANAGE else self.opkgComponent.CMD_LIST_INSTALLED
			case self.opkgComponent.EVENT_INSTALL_DONE:
				print("[PluginBrowser] PackageAction: Package(s) '%s' installed." % "', '".join(eventData))
				self.nextCommand = self.opkgComponent.CMD_INFO if self.mode == self.MODE_MANAGE else self.opkgComponent.CMD_LIST_INSTALLABLE
			case self.opkgComponent.EVENT_UPDATE_DONE:
				print("[PluginBrowser] PackageAction: Package(s) '%s' updated." % "', '".join(eventData))
				self.nextCommand = self.opkgComponent.CMD_INFO if self.mode == self.MODE_MANAGE else self.opkgComponent.CMD_LIST_UPDATES
			case self.opkgComponent.EVENT_OPKG_MISMATCH:
				print(f"[PluginBrowser] PackageAction: Command '{eventData[0]}' downloading '{eventData[1]}' returned a mismatch error!  (Got {eventData[2]} bytes, expected {eventData[3]} bytes)")
			case self.opkgComponent.EVENT_CANT_INSTALL:
				print(f"[PluginBrowser] PackageAction: Command '{eventData[0]}' downloading '{eventData[1]}' returned a installation error!")
			case self.opkgComponent.EVENT_NETWORK_ERROR:
				print(f"[PluginBrowser] PackageAction: Command '{eventData[0]}' downloading '{eventData[1]}' returned a network error!  (Wget error {eventData[2]})")
			case self.opkgComponent.EVENT_OPKG_IN_USE:
				print(f"[PluginBrowser] PackageAction Error: Opkg is already running when trying to run command '{eventData[1]}'!  ({self.opkgComponent.getCommandText(eventData[0])})")
			case self.opkgComponent.EVENT_DONE:
				# print(f"[PluginBrowser] PackageAction: Opkg command '{self.opkgComponent.getCommandText(eventData)}' completed.")
				if hasattr(self, "nextCommand"):
					self.opkgComponent.runCommand(self.nextCommand, self.opkgFilterArguments)
					del self.nextCommand
				else:
					self.setWaiting(None)
					haveLogs = self.logData != ""
					self["logAction"].setEnabled(haveLogs)
					self["key_yellow"].setText(_("Show Log") if haveLogs else "")
			case self.opkgComponent.EVENT_ERROR:
				print(f"[PluginBrowser] PackageAction: Opkg command '{eventData[1]}' error!  ({self.opkgComponent.getCommandText(eventData[0])})")
			case _:
				print(f"[PluginBrowser] PackageAction: Opkg command '{self.opkgComponent.getCommandText(self.opkgComponent.command)}' returned event '{self.opkgComponent.getEventText(event)}'.")

	# Opkg info returns data with any of the possible keys:
	# 	"Package",  "Version",  "Depends",  "Pre-Depends",  "Recommends",  "Suggests",  "Provides",  "Replaces",  "Conflicts",
	# 	"Status",  "Section",  "Essential",  "Architecture",  "Maintainer", "MD5sum",  "Size",  "Filename",  "Conffiles", "Source",
	# 	"Description",  "Installed-Size",  "Installed-Time",  "Tags".  The keys "Installed" and "Update" are added by Opkg.py.
	# Only "Package" is guaranteed to be always be present.
	#
	def processListCallback(self, packages):
		allCount = 0
		installCount = 0
		updateCount = 0
		pluginList = []
		for package in packages:
			packageFile = package["Package"]
			if (self.displayFilter is None or self.displayFilter.search(packageFile)) and self.displayExclude.search(packageFile) is None:
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
					if self.modeData[self.DATA_MODE] == self.MODE_PACKAGE:
						packageCategory = package.get("Section", "")
						packageCategory = PACKAGE_CATEGORY_MAPPINGS.get(packageCategory, packageCategory)
						packageName = packageFile
					else:
						print(f"[PluginBrowser] PackageAction Error: Plugin package '{packageFile}' has no name!")
						continue
				if packageCategory not in PLUGIN_CATEGORIES and packageCategory not in PACKAGE_CATEGORIES:
					packageCategory = ""
				# print(f"[PluginBrowser] PackageAction DEBUG: Package='{packageFile}', Name='{packageName}', Category='{packageCategory}'.")
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
		print(f"[PluginBrowser] PackageAction Packages: {len(packages)} returned from opkg, {allCount} matched, {installCount} installed, {updateCount} have updates.")
		installedText = ngettext("%d package installed.", "%d packages installed.", installCount) % installCount
		updateText = ngettext("%d package has an update", "%d packages have updates.", updateCount) % updateCount
		match self.mode:
			case self.MODE_REMOVE:
				self.descriptionText = installedText
			case self.MODE_INSTALL:
				self.descriptionText = ngettext("%d package installable.", "%d packages installable.", allCount) % allCount
			case self.MODE_UPDATE:
				self.descriptionText = updateText
			case _:
				self.descriptionText = f"{ngettext('%d package found.', '%d packages found.', allCount) % allCount} {installedText} {updateText}"
		self["description"].setText(self.descriptionText)
		self.displayPluginList(pluginList, True)
		self.pluginList = pluginList

	def displayPluginList(self, pluginList, initialLoad):
		categories = {}
		for info in pluginList:
			category = info[self.INFO_CATEGORY]
			if category in categories:
				categories[category].append(info)
			else:
				categories[category] = [info]
		# categoryList = sorted(categories.keys())  # This sorts the categories by their key.
		categoryList = [y[1] for y in sorted([(self.modeData[self.DATA_CATEGORIES].get(x, _("Unknown Packages")), x) for x in categories.keys()])]  # This sorts the categories by their label.
		count = len(categoryList)
		if initialLoad:
			autoExpand = 1
			match autoExpand:  # config.pluginBrowser.autoExpand.value
				case 1:
					if count == 1:
						self.expanded.append(categoryList[0])
				case 2:
					self.expanded.append(categoryList[0])
				case 3:
					for category in categoryList:
						self.expanded.append(category)
		plugins = []
		for category in categoryList:
			if category in self.expanded:
				plugins.append((category, category, self.modeData[self.DATA_CATEGORIES].get(category, category), None, None, None, self.expandedIcon, None, self.modeData[self.DATA_CATEGORIES].get(category, category), None, None, None))
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
						version = f"exp-{version[13:]}"
					version = version.replace("devel", "dev")
					version = version.replace("-git", "+git")
					parts = version.split("+")
					for part in parts[:]:
						if part.startswith("git"):
							parts.remove(part)
					version = "+".join(parts)
					plugins.append((info[self.INFO_PACKAGE], None, None, info[self.INFO_NAME], info[self.INFO_DESCRIPTION], version, self.verticalIcon, icon, self.modeData[self.DATA_CATEGORIES].get(category, category), info[self.INFO_INSTALLED], info[self.INFO_UPGRADE], f"{info[self.INFO_NAME]} ({version})"))
			else:
				plugins.append((category, category, self.modeData[self.DATA_CATEGORIES].get(category, category), None, None, None, self.expandableIcon, None, self.modeData[self.DATA_CATEGORIES].get(category, category), None, None, None))
		self["plugins"].setList(plugins)

	def setWaiting(self, text):
		if text:
			self.actionMaps = (self["selectAction"].getEnabled(), self["performAction"].getEnabled(), self["logAction"].getEnabled(), self["navigationActions"].getEnabled(), self["quickSelectActions"].getEnabled())
			self["selectAction"].setEnabled(False)
			self["performAction"].setEnabled(False)
			self["logAction"].setEnabled(False)
			self["navigationActions"].setEnabled(False)
			self["quickSelectActions"].setEnabled(False)
			self.processing = True
			Processing.instance.setDescription(text)
			Processing.instance.showProgress(endless=True)
		else:
			Processing.instance.hideProgress()
			self.processing = False
			self["selectAction"].setEnabled(self.actionMaps[0])
			self["performAction"].setEnabled(self.actionMaps[1])
			self["logAction"].setEnabled(self.actionMaps[2])
			self["navigationActions"].setEnabled(self.actionMaps[3])
			self["quickSelectActions"].setEnabled(self.actionMaps[4])

	def keyNumberGlobal(self, digit):
		self.quickSelectTimer.stop()
		if self.lastKey != digit:  # Is this a different digit?
			self.nextKey()  # Reset lastKey again so NumericalTextInput triggers its key change.
			self.selectByStart()
			self.quickSelectPos += 1
		char = self.getKey(digit)  # Get char and append to text.
		self.quickSelect = f"{self.quickSelect[:self.quickSelectPos]}{str(char)}"
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
		return PackageActionSummary


class PluginAction(PackageAction):
	def __init__(self, session, mode=PackageAction.MODE_REMOVE):
		PackageAction.__init__(self, session, mode=mode)


class PackageActionSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self.skinName = ["PackageActionSummary"]
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


class PackageActionLog(Screen):
	skin = """
	<screen name="PackageActionLog" title="Plugin Action Log" position="center,center" size="950,590" resolution="1280,720">
		<widget name="log" position="0,0" size="e,e-50" font="Regular;20" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, logData):
		Screen.__init__(self, session, enableHelp=True)
		self.skinName = ["PackageActionLog", "PluginActionLog"]
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
