from os import system, unlink
from os.path import exists, normpath
from re import compile
from enigma import eConsoleAppContainer, eDVBDB
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Components.config import config, ConfigSubsection, ConfigYesNo, ConfigText
from Components.Harddisk import harddiskmanager
from Components.Opkg import opkgAddDestination, opkgExtraDestinations, opkgDestinations, OpkgComponent
from Components.Label import Label
from Components.PluginComponent import plugins
from Components.PluginList import PluginList, PluginCategoryComponent, PluginDownloadComponent, PluginEntryComponentSelected, PluginEntryComponent
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.Screen import Screen
from Screens.Setup import Setup
from Tools.BoundFunction import boundFunction
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap

config.pluginfilter = ConfigSubsection()
config.pluginfilter.kernel = ConfigYesNo(default=False)
config.pluginfilter.drivers = ConfigYesNo(default=True)
config.pluginfilter.extensions = ConfigYesNo(default=True)
config.pluginfilter.m2k = ConfigYesNo(default=True)
config.pluginfilter.picons = ConfigYesNo(default=True)
config.pluginfilter.pli = ConfigYesNo(default=False)
config.pluginfilter.security = ConfigYesNo(default=True)
config.pluginfilter.settings = ConfigYesNo(default=True)
config.pluginfilter.skin = ConfigYesNo(default=True)
config.pluginfilter.display = ConfigYesNo(default=True)
config.pluginfilter.softcams = ConfigYesNo(default=True)
config.pluginfilter.systemplugins = ConfigYesNo(default=True)
config.pluginfilter.vix = ConfigYesNo(default=False)
config.pluginfilter.weblinks = ConfigYesNo(default=True)
config.pluginfilter.userfeed = ConfigText(default="http://", fixed_size=False)


def CreateFeedConfig():
	fileconf = "/etc/opkg/user-feed.conf"
	feedurl = "src/gz user-feeds %s\n" % config.pluginfilter.userfeed.value
	with open(fileconf, "w") as fd:
		fd.write(feedurl)
	system("ipkg update")


class PluginBrowserSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["entry"] = StaticText("")
		self["desc"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent.selectionChanged()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self, name, desc):
		self["entry"].text = name
		self["desc"].text = desc


class PluginBrowser(Screen, ProtectedScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		if config.ParentalControl.configured.value:
			ProtectedScreen.__init__(self)
		Screen.setTitle(self, _("Plugin Browser"))
		ProtectedScreen.__init__(self)

		self.firsttime = True

		self.sort_mode = False
		self.selected_plugin = None

		self["key_red"] = StaticText(_("Remove Plugins"))
		self["key_green"] = StaticText(_("Download Plugins"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")

		self.list = []
		self["list"] = PluginList(self.list)

		self["actions"] = ActionMap(["SetupActions", "WizardActions"],
		{
			"ok": self.keyOk,
			"back": self.keyCancel,
			"menu": self.menu,
		})
		self["PluginDownloadActions"] = ActionMap(["ColorActions"],
		{
			"red": self.delete,
			"green": self.download,
			"blue": self.keyBlue,
		})
		self["SoftwareActions"] = ActionMap(["ColorActions"],
		{
			"red": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"blue": self.keyBlue,
		})
		self["MoveActions"] = ActionMap(["WizardActions"],
			{
				"left": self.keyLeft,
				"right": self.keyRight,
				"up": self.keyUp,
				"down": self.keyDown,
			}, -1
		)

		self["NumberAction"] = NumberActionMap(["NumberActions"],
			{
				"0": self.resetSortOrder,
			}, -1
		)

		self["PluginDownloadActions"].setEnabled(True)
		self["SoftwareActions"].setEnabled(False)
		self.onFirstExecBegin.append(self.checkWarnings)
		self.onShown.append(self.updateList)
		self.onChangedEntry = []
		self["list"].onSelectionChanged.append(self.selectionChanged)
		self.onLayoutFinish.append(self.saveListsize)
		if config.pluginfilter.userfeed.value != "http://":
			if not exists("/etc/opkg/user-feed.conf"):
				CreateFeedConfig()

	def openSetup(self):
		self.session.open(Setup, "PluginBrowser")

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and not config.ParentalControl.config_sections.main_menu.value and config.ParentalControl.config_sections.plugin_browser.value

	def menu(self):
		self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginFilter)

	def saveListsize(self):
		listsize = self["list"].instance.size()
		self.listWidth = listsize.width()
		self.listHeight = listsize.height()

	def createSummary(self):
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["list"].getCurrent()
		if item:
			p = item[0]
			name = p.name
			desc = p.description
			if self.sort_mode:
				if config.usage.plugin_sort_weight.getConfigValue(name.lower(), "hidden"):
					self["key_yellow"].setText(_("Show"))
				else:
					self["key_yellow"].setText(_("Hide"))
		else:
			name = "-"
			desc = ""
			if self.sort_mode:
				self["key_yellow"].setText("")
		for cb in self.onChangedEntry:
			cb(name, desc)

	def checkWarnings(self):
		if len(plugins.warnings):
			text = _("Some plugins are not available:\n")
			for (pluginname, error) in plugins.warnings:
				text += _("%s (%s)\n") % (pluginname, error)
			plugins.resetWarnings()
			self.session.open(MessageBox, text=text, type=MessageBox.TYPE_WARNING)

	def save(self):
		self.run()

	def run(self):
		plugin = self["list"].l.getCurrentSelection()[0]
		plugin(session=self.session)

	def keyLeft(self):
		self.cur_idx = self["list"].getSelectedIndex()
		self["list"].pageUp()
		if self.sort_mode and self.selected_plugin is not None:
			self.moveAction()

	def keyRight(self):
		self.cur_idx = self["list"].getSelectedIndex()
		self["list"].pageDown()
		if self.sort_mode and self.selected_plugin is not None:
			self.moveAction()

	def keyDown(self):
		self.cur_idx = self["list"].getSelectedIndex()
		self["list"].down()
		if self.sort_mode and self.selected_plugin is not None:
			self.moveAction()

	def keyUp(self):
		self.cur_idx = self["list"].getSelectedIndex()
		self["list"].up()
		if self.sort_mode and self.selected_plugin is not None:
			self.moveAction()

	def moveAction(self):
		entry = self.list.pop(self.cur_idx)
		newpos = self["list"].getSelectedIndex()
		self.list.insert(newpos, entry)
		self["list"].l.setList(self.list)

	def keyYellow(self):
		if self.sort_mode:
			plugin = self["list"].l.getCurrentSelection()[0]
			hidden = config.usage.plugin_sort_weight.getConfigValue(plugin.name.lower(), "hidden") or 0
			if hidden:
				config.usage.plugin_sort_weight.removeConfigValue(plugin.name.lower(), "hidden")
				self["key_yellow"].setText(_("Hide"))
			else:
				config.usage.plugin_sort_weight.changeConfigValue(plugin.name.lower(), "hidden", 1)
				self["key_yellow"].setText(_("Show"))

	def keyBlue(self):
		if config.usage.plugins_sort_mode.value == "user":
			self.toggleSortMode()

	def keyRed(self):
		pass

	def keyCancel(self):
		if self.sort_mode:
			self.toggleSortMode()
		self.close()

	def keyGreen(self):
		if config.usage.plugins_sort_mode.value == "user" and self.sort_mode:
			self.keyOk()

	def keyOk(self):
		if self.sort_mode and len(self.list):
			plugin = self["list"].l.getCurrentSelection()[0]
			select = False
			if self.selected_plugin is None:
				select = True
			elif self.selected_plugin != plugin:
				select = True
			if not select:
				self.selected_plugin = None
			idx = 0
			for x in self.list:
				if plugin == x[0] and select == True:
					self.list.pop(idx)
					self.list.insert(idx, PluginEntryComponentSelected(x[0], self.listWidth))
					self.selected_plugin = plugin
					break
				elif plugin == x[0] and select == False:
					self.list.pop(idx)
					self.list.insert(idx, PluginEntryComponent(x[0], self.listWidth))
					self.selected_plugin = None
					break
				idx += 1
			if self.selected_plugin is not None:
				self["key_green"].setText(_("Move Mode Off"))
			else:
				self["key_green"].setText(_("Move Mode On"))
			self["list"].l.setList(self.list)
		elif len(self.list):
			self.save()

	def resetSortOrder(self, key=None):
		config.usage.plugin_sort_weight.value = {}
		config.usage.plugin_sort_weight.save()
		self.updateList()

	def toggleSortMode(self):
		if self.sort_mode:
			self.sort_mode = False
			i = 10
			idx = 0
			for x in self.list:
				config.usage.plugin_sort_weight.changeConfigValue(x[0].name.lower(), "sort", i)
				if self.selected_plugin is not None:
					if x[0] == self.selected_plugin:
						self.list.pop(idx)
						self.list.insert(idx, PluginEntryComponent(x[0], self.listWidth))
						self.selected_plugin = None
				i += 10
				idx += 1
			config.usage.plugin_sort_weight.save()
			self.updateList()
		else:
			self.sort_mode = True
			self.updateList()

	def updateList(self):
		self.pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_PLUGINMENU)
		empty_sort_order = len(config.usage.plugin_sort_weight.value) or False
		self.list = []
		i = 10
		for plugin in self.pluginlist:
			plugin.listweight = config.usage.plugin_sort_weight.getConfigValue(plugin.name.lower(), "sort") or i
			if self.sort_mode or not config.usage.plugin_sort_weight.getConfigValue(plugin.name.lower(), "hidden"):
				self.list.append(PluginEntryComponent(plugin, self.listWidth))
			i += 10
		if config.usage.plugins_sort_mode.value == "a_z" or (not empty_sort_order and config.usage.plugins_sort_mode.value == "user"):
			self.list.sort(key=lambda p_name: p_name[0].name.lower())
		elif config.usage.plugins_sort_mode.value == "user":
			self.list.sort(key=lambda listweight: listweight[0].listweight)
		self["list"].l.setList(self.list)
		if self.sort_mode:
			self["key_blue"].setText(_("Edit Mode Off"))
			self["key_green"].setText(_("Move Mode Off"))
			self["key_red"].setText("")
			self["SoftwareActions"].setEnabled(True)
			self["PluginDownloadActions"].setEnabled(False)
			if self.selected_plugin:
				self["key_green"].setText(_("Move Mode Off"))
			else:
				self["key_green"].setText(_("Move Mode On"))
		else:
			if config.usage.plugins_sort_mode.value == "user":
				self["key_blue"].setText(_("Edit Mode On"))
			else:
				self["key_blue"].setText("")
			self["SoftwareActions"].setEnabled(False)
			self["PluginDownloadActions"].setEnabled(True)
			self["key_yellow"].setText("")
			self["key_red"].setText(_("Remove Plugins"))
			self["key_green"].setText(_("Download Plugins"))

	def delete(self):
		self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginDownloadBrowser, PluginDownloadBrowser.REMOVE)

	def download(self):
		self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginDownloadBrowser, PluginDownloadBrowser.DOWNLOAD, self.firsttime)
		self.firsttime = False

	def PluginDownloadBrowserClosed(self):
		self.updateList()
		self.checkWarnings()


class PluginDownloadBrowser(Screen):
	DOWNLOAD = 0
	REMOVE = 1
	UPDATE = 2
	MANAGE = 3
	PLUGIN_PREFIX = "enigma2-plugin-"
	PLUGIN_PREFIX2 = []
	lastDownloadDate = None

	def __init__(self, session, type=0, needupdate=True):
		Screen.__init__(self, session)
		self.setTitle(_("Download Plugins"))
		self.type = type
		self.needupdate = needupdate
		self.createPluginFilter()

		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.runFinished)
		self.container.dataAvail.append(self.dataAvail)
		self.onLayoutFinish.append(self.startRun)
		self.onShown.append(self.setWindowTitle)

		self.list = []
		self["list"] = PluginList(self.list)
		self.pluginlist = []
		self.expanded = []
		self.installedplugins = []
		self.plugins_changed = False
		self.reload_settings = False
		self.check_settings = False
		self.check_bootlogo = False
		self.install_settings_name = ""
		self.remove_settings_name = ""
		self.onChangedEntry = []
		self["list"].onSelectionChanged.append(self.selectionChanged)

		if self.type in (self.DOWNLOAD, self.MANAGE):
			self["text"] = Label(_("Downloading plugin information. Please wait..."))
		elif self.type == self.REMOVE:
			self["text"] = Label(_("Getting plugin information. Please wait..."))

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText(_("Refresh"))

		self.run = 0
		self.remainingdata = ""

		self["actions"] = HelpableActionMap(self, ["ColorActions", "OkCancelActions"], {
			"blue": (self.keyRefresh, _("Refresh the update-able package list")),
			"cancel": (self.requestClose, _("Cancel / Close the screen")),
			"ok": (self.go, _("Perform install/remove of the selected item"))
		}, prio=0, description=_("Plugin Manager Actions"))

		self.opkg = "/usr/bin/opkg"
		self.opkg_install = self.opkg + " install --force-overwrite"
		self.opkg_remove = self.opkg + " remove --autoremove --force-depends"

		self.opkgObj = OpkgComponent()
		self.opkgObj.addCallback(self.opkgCallback)

	def keyRefresh(self):
		if self.type == self.MANAGE:
			self.startRun()

	def opkgCallback(self, event, param):
		if event == OpkgComponent.EVENT_DONE:
			if self.opkgObj.currentCommand == OpkgComponent.CMD_UPDATE:
				self.opkgObj.startCmd(OpkgComponent.CMD_INFO)
			elif self.opkgObj.currentCommand == OpkgComponent.CMD_INFO:
				pluginlist = param
				self.fillPluginList(pluginlist)
		elif event == OpkgComponent.EVENT_ERROR:
			return

	def fillPluginList(self, packages):
		self.pluginlist = []
		self.installedplugins = []
		allcount, installcount, updatecount = (0, 0, 0)
		for package in packages:
			packagename = package["name"]
			version = package["version"]
			description = package["description"]
			exclude = compile(r"(-dev$|-staticdev$|-dbg$|-doc$|-src$|-meta$)")
			if exclude.search(packagename) is None:
				# Plugin filter
				for s in self.PLUGIN_PREFIX2:
					if packagename.startswith(s):
						plugin = [packagename, version]
						plugin.append(description)
						plugin.append(plugin[0][15:])
						if package["installed"] == "1":
							self.installedplugins.append(packagename)
							plugin.append("1")
							installcount += 1
						else:
							plugin.append("0")
						if package["update"] != "0":
							updatecount += 1
						plugin.append(package["update"])
						allcount += 1
						self.pluginlist.append(plugin)
		if self.pluginlist:
			self.updateList()
			self["list"].instance.show()
			self["text"].setText(_("%d packages found, %d packages installed and %d packages has updates.") % (allcount, installcount, updatecount))
		else:
			self["text"].setText(_("No packages found."))

	def createSummary(self):
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["list"].getCurrent()
		try:
			if isinstance(item[0], str):  # category
				name = item[0]
				desc = ""
			else:
				p = item[0]
				name = item[1][0:8][7]
				desc = p.description
		except:
			name = ""
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def createPluginFilter(self):
		#Create Plugin Filter
		self.PLUGIN_PREFIX2 = []
		for filtername in ("display", "drivers", "extensions", "m2k", "picons", "pli", "softcams", "security", "settings", "skin", "systemplugins", "vix", "weblinks"):
			if getattr(config.pluginfilter, filtername).value:
				self.PLUGIN_PREFIX2.append("%s%s" % (self.PLUGIN_PREFIX, filtername))
		if config.pluginfilter.kernel.value:
			self.PLUGIN_PREFIX2.append("kernel-module-")

	def go(self):
		sel = self["list"].l.getCurrentSelection()
		if sel is None:
			return
		plugin = sel[0]
		if isinstance(plugin, str):  # category
			if plugin in self.expanded:
				self.expanded.remove(plugin)
			else:
				self.expanded.append(plugin)
			self.updateList()
		else:
			installed = self.type == self.REMOVE
			if self.type == self.MANAGE:
				installed = self.pluginstatus[plugin.name][0] == "1"
			if installed:
				mbox = self.session.openWithCallback(boundFunction(self.runInstall, installed), MessageBox, _("Do you really want to remove the plugin \"%s\"?") % plugin.name, default=False)
				mbox.setTitle(_("Remove Plugins"))
			else:
				mbox = self.session.openWithCallback(boundFunction(self.runInstall, installed), MessageBox, _("Do you really want to download the plugin \"%s\"?") % plugin.name)
				mbox.setTitle(_("Download Plugins"))

	def requestClose(self):
		if self.plugins_changed:
			plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
		if self.reload_settings:
			self["text"].setText(_("Reloading bouquets and services..."))
			eDVBDB.getInstance().reloadBouquets()
			eDVBDB.getInstance().reloadServicelist()
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
		self.container.appClosed.remove(self.runFinished)
		self.container.dataAvail.remove(self.dataAvail)
		self.close()

	def resetPostInstall(self):
		try:
			del self.postInstallCall
		except:
			pass

	def installDestinationCallback(self, result):
		if result is not None:
			dest = result[1]
			if dest.startswith("/"):
				# Custom install path, add it to the list too
				dest = normpath(dest)
				extra = " --add-dest %s:%s -d %s" % (dest, dest, dest)
				opkgAddDestination(dest)
			else:
				extra = " -d " + dest
			self.doInstall(self.installFinished, self["list"].l.getCurrentSelection()[0].name + " " + extra)
		else:
			self.resetPostInstall()

	def runInstall(self, installed=False, val=None):
		if val:
			if installed:
				if self["list"].l.getCurrentSelection()[0].name.startswith("bootlogo-"):
					self.doRemove(self.installFinished, self["list"].l.getCurrentSelection()[0].name + " --force-remove --force-depends")
				else:
					self.doRemove(self.installFinished, self["list"].l.getCurrentSelection()[0].name)
			else:
				if self["list"].l.getCurrentSelection()[0].name.startswith("picons-"):
					supported_filesystems = frozenset(("vfat", "ext4", "ext3", "ext2", "reiser", "reiser4", "jffs2", "ubifs", "rootfs"))
					candidates = []
					import Components.Harddisk
					mounts = Components.Harddisk.getProcMounts()
					for partition in harddiskmanager.getMountedPartitions(False, mounts):
						if partition.filesystem(mounts) in supported_filesystems:
							candidates.append((partition.description, partition.mountpoint))
					if candidates:
						from Components.Renderer import Picon
						self.postInstallCall = Picon.initPiconPaths
						self.session.openWithCallback(self.installDestinationCallback, ChoiceBox, title=_("Install picons on"), list=candidates)
					return
				elif self["list"].l.getCurrentSelection()[0].name.startswith("display-picon"):
					supported_filesystems = frozenset(("vfat", "ext4", "ext3", "ext2", "reiser", "reiser4", "jffs2", "ubifs", "rootfs"))
					candidates = []
					import Components.Harddisk
					mounts = Components.Harddisk.getProcMounts()
					for partition in harddiskmanager.getMountedPartitions(False, mounts):
						if partition.filesystem(mounts) in supported_filesystems:
							candidates.append((partition.description, partition.mountpoint))
					if candidates:
						from Components.Renderer import LcdPicon
						self.postInstallCall = LcdPicon.initLcdPiconPaths
						self.session.openWithCallback(self.installDestinationCallback, ChoiceBox, title=_("Install lcd picons on"), list=candidates)
					return
				self.install_settings_name = self["list"].l.getCurrentSelection()[0].name
				self.install_bootlogo_name = self["list"].l.getCurrentSelection()[0].name
				if self["list"].l.getCurrentSelection()[0].name.startswith("settings-"):
					self.check_settings = True
					self.startOpkgListInstalled(self.PLUGIN_PREFIX + "settings-*")
				elif self["list"].l.getCurrentSelection()[0].name.startswith("bootlogo-"):
					self.check_bootlogo = True
					self.startOpkgListInstalled(self.PLUGIN_PREFIX + "bootlogo-*")
				else:
					self.runSettingsInstall()

	def doRemove(self, callback, pkgname):
		prefix = "" if pkgname.startswith("kernel-module-") else self.PLUGIN_PREFIX
		pkgname = "%s%s %s%s" % (self.opkg_remove, opkgExtraDestinations(), prefix, pkgname)
		self.session.openWithCallback(callback, Console, cmdlist=[pkgname, "sync"], closeOnSuccess=True)

	def doInstall(self, callback, pkgname):
		prefix = "" if pkgname.startswith("kernel-module-") else self.PLUGIN_PREFIX
		pkgname = "%s %s%s" % (self.opkg_install, prefix, pkgname)
		self.session.openWithCallback(callback, Console, cmdlist=[pkgname, "sync"], closeOnSuccess=True)

	def runSettingsRemove(self, val):
		if val:
			self.doRemove(self.runSettingsInstall, self.remove_settings_name)

	def runBootlogoRemove(self, val):
		if val:
			self.doRemove(self.runSettingsInstall, self.remove_bootlogo_name + " --force-remove --force-depends")

	def runSettingsInstall(self):
		self.doInstall(self.installFinished, self.install_settings_name)

	def setWindowTitle(self):
		if self.type == self.DOWNLOAD:
			self.setTitle(_("Install Plugins"))
		elif self.type == self.REMOVE:
			self.setTitle(_("Remove Plugins"))
		elif self.type == self.MANAGE:
			self.setTitle(_("Manage Plugins"))

	def startOpkg(self, command):
		extra = []
		for destination in opkgDestinations:
			extra.append("--add-dest")
			extra.append("%s:%s" % (destination, destination))
		argv = extra + [command]
		argv.insert(0, self.opkg)
		self.container.execute(self.opkg, *argv)

	def startOpkgListInstalled(self, pkgname=PLUGIN_PREFIX + "*"):
		self.startOpkg("list-installed")

	def startOpkgListAvailable(self):
		self.startOpkg("list")

	def startRun(self):
		listsize = self["list"].instance.size()
		self["list"].instance.hide()
		self.listWidth = listsize.width()
		self.listHeight = listsize.height()
		if self.type == self.DOWNLOAD:
			self.type = self.UPDATE
			self.startOpkg("update")
		elif self.type == self.REMOVE:
			self.run = 1
			self.startOpkgListInstalled()
		elif self.type == self.MANAGE:
			self.run = 4
			self.opkgObj.startCmd(OpkgComponent.CMD_UPDATE)

	def installFinished(self):
		if hasattr(self, "postInstallCall"):
			try:
				self.postInstallCall()
			except Exception as ex:
				print("[PluginBrowser] postInstallCall failed: %s" % str(ex))
			self.resetPostInstall()
		try:
			unlink("/tmp/opkg.conf")
		except:
			pass
		newplugin = None
		idx = -1
		for idx, plugin in enumerate(self.pluginlist):
			if plugin[3] == self["list"].l.getCurrentSelection()[0].name or plugin[0] == self["list"].l.getCurrentSelection()[0].name:
				if self.type == self.MANAGE:
					newplugin = plugin
				else:
					self.pluginlist.remove(plugin)
				break
		if newplugin and idx != -1:
			if newplugin[4] == "1":
				newplugin[4] = "0"
			else:
				newplugin[4] = "1"
			newplugin[5] = "0"
			self.pluginlist[idx] = newplugin
		self.plugins_changed = True
		if self["list"].l.getCurrentSelection()[0].name.startswith("settings-"):
			self.reload_settings = True
		self.expanded = []
		self.updateList()
		self["list"].moveToIndex(0)

	def runFinished(self, retval):
		if self.check_settings:
			self.check_settings = False
			self.runSettingsInstall()
			return
		if self.check_bootlogo:
			self.check_bootlogo = False
			self.runSettingsInstall()
			return
		self.remainingdata = ""
		if self.run == 0:
			self.run = 1
			if self.type == self.UPDATE:
				self.type = self.DOWNLOAD
				self.startOpkgListInstalled()
		elif self.run == 1 and self.type == self.DOWNLOAD:
			self.run = 2
			self.startOpkgListAvailable()
		else:
			if len(self.pluginlist) > 0:
				self["text"].setText(_("%s Packages found") % len(self.pluginlist))
				self.updateList()
				self["list"].instance.show()
			else:
				if self.type == self.DOWNLOAD:
					self["text"].setText(_("Sorry feeds are down for maintenance."))

	def dataAvail(self, data):
		if isinstance(data, bytes):
			data = data.decode()
		if self.type == self.DOWNLOAD and data.find("404 Not Found") >= 0:
			self["text"].setText(_("Sorry feeds are down for maintenance."))
			self.run = 3
			return
		#prepend any remaining data from the previous call
		data = "%s%s" % (self.remainingdata, data)
		#split in lines
		lines = data.split("\n")
		#"str" should end with "\n", so when splitting, the last line should be empty. If this is not the case, we received an incomplete line
		if len(lines[-1]):
			#remember this data for next time
			self.remainingdata = lines[-1]
			lines = lines[0:-1]
		else:
			self.remainingdata = ""

		if self.check_settings:
			self.check_settings = False
			self.remove_settings_name = data.split(" - ")[0].replace(self.PLUGIN_PREFIX, "")
			self.session.openWithCallback(self.runSettingsRemove, MessageBox, _('You already have a channel list installed,\nwould you like to remove\n"%s"?') % self.remove_settings_name)
			return

		if self.check_bootlogo:
			self.check_bootlogo = False
			self.remove_bootlogo_name = data.split(" - ")[0].replace(self.PLUGIN_PREFIX, "")
			self.session.openWithCallback(self.runBootlogoRemove, MessageBox, _('You already have a bootlogo installed,\nwould you like to remove\n"%s"?') % self.remove_bootlogo_name)
			return

		exclude = compile(r"(-dev$|-staticdev$|-dbg$|-doc$|-src$|-meta$)")

		for x in lines:
			plugin = x.split(" - ", 2)
			# "opkg list_installed" only returns name + version, no description field
			if len(plugin) >= 1:
				if exclude.search(plugin[0]) is None:
					# Plugin filter
					for s in self.PLUGIN_PREFIX2:
						if plugin[0].startswith(s):
							if self.run == 1 and self.type == self.DOWNLOAD:
								if plugin[0] not in self.installedplugins:
									self.installedplugins.append(plugin[0])
							else:
								if plugin[0] not in self.installedplugins:
									if len(plugin) == 2:
										plugin.append("")
									plugin.append(plugin[0][15:])
									plugin.append("")  # installed dummy
									plugin.append("")  # update dummy
									self.pluginlist.append(plugin)

	def updateList(self):
		_list = []
		expandableIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/expandable-plugins.png"))
		expandedIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/expanded-plugins.png"))
		verticallineIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/verticalline-plugins.png"))
		self.plugins = {}
		self.pluginstatus = {}

		if self.type == self.UPDATE:
			self.list = _list
			self["list"].l.setList(_list)
			return

		for x in self.pluginlist:
			split = x[3].split("-", 1)
			if x[0][0:14] == "kernel-module-":
				split[0] = "kernel modules"

			if split[0] not in self.plugins:
				self.plugins[split[0]] = []

			if split[0] == "kernel modules":
				self.plugins[split[0]].append((PluginDescriptor(name=x[0], description=x[2], icon=verticallineIcon), x[0][14:], x[1], x[4], x[5]))
			else:
				if len(split) < 2:
					continue
				self.plugins[split[0]].append((PluginDescriptor(name=x[3], description=x[2], icon=verticallineIcon), split[1], x[1], x[4], x[5]))

		temp = list(self.plugins.keys())

		if config.usage.sort_pluginlist.value:
			temp.sort()

		for x in temp:
			if x in self.expanded:
				_list.append(PluginCategoryComponent(x, expandedIcon, self.listWidth))
				for plugin in self.plugins[x]:
					self.pluginstatus[plugin[0].name] = (plugin[3], plugin[4])
				_list.extend([PluginDownloadComponent(plugin[0], plugin[1], plugin[2], self.listWidth, plugin[3], plugin[4]) for plugin in self.plugins[x]])
			else:
				_list.append(PluginCategoryComponent(x, expandableIcon, self.listWidth))
		self.list = _list
		self["list"].l.setList(_list)


class PluginFilter(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "PluginFilter")
		self.setTitle(_("Plugin Filter Settings"))

	def saveAll(self):
		Setup.saveAll(self)
		if config.pluginfilter.userfeed.value != "http://":
			CreateFeedConfig()


class PluginDownloadManager(PluginDownloadBrowser):
	def __init__(self, session):
		PluginDownloadBrowser.__init__(self, session=session, type=self.MANAGE)
		self.skinName = ["PluginDownloadBrowser"]
