# -*- coding: utf-8 -*-
from datetime import timedelta, date
from os import F_OK, R_OK, W_OK, access, listdir, makedirs, mkdir, remove, stat, system
from os.path import dirname, exists, isdir, isfile, join as pathjoin
import requests
from stat import ST_MTIME
from pickle import dump, load
from urllib.request import urlopen
from socket import getdefaulttimeout, setdefaulttimeout
from time import time

from twisted.internet import reactor

from enigma import eTimer, getDesktop, ePicLoad, eRCInput, getPrevAsciiCode, eEnv, getEnigmaVersionString

from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.AVSwitch import AVSwitch
from Components.config import config
from Components.Console import Console
from Components.Harddisk import harddiskmanager
from Components.Input import Input
from Components.International import international
from Components.MenuList import MenuList
from Components.Opkg import OpkgComponent
from Components.PackageInfo import PackageInfoHandler
from Components.Pixmap import Pixmap
from Components.PluginComponent import plugins
from Components.ScrollLabel import ScrollLabel
from Components.SelectionList import SelectionList
from Components.Slider import Slider
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Opkg import Opkg
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.Standby import TryQuitMainloop
from Tools.Directories import SCOPE_CURRENT_PLUGIN, SCOPE_GUISKIN, SCOPE_METADIR, SCOPE_PLUGINS, fileExists, resolveFilename
from Tools.LoadPixmap import LoadPixmap
from Tools.NumericalTextInput import NumericalTextInput

from .BackupRestore import InitConfig as BackupRestore_InitConfig, BackupSelection, BackupScreen, RestoreScreen, getBackupPath, getOldBackupPath, getBackupFilename, RestoreMyMetrixHD, RestoreMenu
from .SoftwareTools import iSoftwareTools
from .ImageWizard import ImageWizard
from .ImageBackup import ImageBackup

boxType = BoxInfo.getItem("machinebuild")
config.plugins.configurationbackup = BackupRestore_InitConfig()


def write_cache(cache_file, cache_data):  # Does a cPickle dump.
	if not isdir(dirname(cache_file)):
		try:
			mkdir(dirname(cache_file))
		except OSError:
			print("%s is a file" % dirname(cache_file))
	with open(cache_file, "wb") as fd:
		dump(cache_data, fd, -1)


def valid_cache(cache_file, cache_ttl):  # See if the cache file exists and is still living.
	try:
		mtime = stat(cache_file)[ST_MTIME]
	except OSError:
		return 0
	curr_time = time()
	if (curr_time - mtime) > cache_ttl:
		return 0
	else:
		return 1


def load_cache(cache_file):  # Does a cPickle load.
	cache_data = None
	with open(cache_file, "rb") as fd:
		cache_data = load(fd)
	return cache_data


def Check_Softcam_Emu():
	found = False
	if not isfile("/etc/enigma2/noemu"):
		for x in listdir("/etc"):
			if x.find(".emu") > -1:
				found = True
				break
	return found


# Helper for menu.xml
class ImageWizard(ImageWizard):
    pass


class ImageBackup(ImageBackup):
    pass


class RestoreMenu(RestoreMenu):
    pass


class SoftwareManagerSetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "SoftwareManager", plugin="SystemPlugins/SoftwareManager")


class PluginManager(Screen, PackageInfoHandler):

	skin = """
		<screen name="PluginManager" position="center,center" size="560,440" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget source="list" render="Listbox" position="5,50" size="550,360" scrollbarMode="showOnDemand">
				<convert type="TemplatedMultiContent">
				{"templates":
					{"default": (51,[
							MultiContentEntryText(pos = (0, 1), size = (470, 24), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the name
							MultiContentEntryText(pos = (0, 25), size = (470, 24), font=1, flags = RT_HALIGN_LEFT, text = 2), # index 2 is the description
							MultiContentEntryPixmapAlphaTest(pos = (475, 0), size = (48, 48), png = 5), # index 5 is the status pixmap
							MultiContentEntryPixmapAlphaTest(pos = (0, 49), size = (550, 2), png = 6), # index 6 is the div pixmap
						]),
					"category": (40,[
							MultiContentEntryText(pos = (30, 0), size = (500, 22), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the name
							MultiContentEntryText(pos = (30, 22), size = (500, 16), font=2, flags = RT_HALIGN_LEFT, text = 1), # index 1 is the description
							MultiContentEntryPixmapAlphaTest(pos = (0, 38), size = (550, 2), png = 3), # index 3 is the div pixmap
						])
					},
					"fonts": [gFont("Regular", 22),gFont("Regular", 20),gFont("Regular", 16)],
					"itemHeight": 52
				}
				</convert>
			</widget>
			<widget source="status" render="Label" position="5,410" zPosition="10" size="540,30" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""

	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.setTitle(_("Extensions Management"))
		self["shortcuts"] = HelpableActionMap(self, ["ColorActions", "InfoActions", "OkCancelActions"], {
			"ok": self.handleCurrent,
			"cancel": self.exit,
			"red": self.exit,
			"green": self.handleCurrent,
			"yellow": self.handleSelected,
			"info": self.handleSelected,
		}, prio=-1)
		self["helpaction"] = HelpableActionMap(self, ["HelpActions"], {
			"displayHelp": self.handleHelp,
		}, prio=0)
		self.statuslist = []
		self.selectedFiles = []
		self.categoryList = []
		self.packageList = []
		self["list"] = List(self.packageList)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["status"] = StaticText("")
		self.cmdList = []
		self.okText = _("After pressing OK, please wait!")
		if self.selectionChanged not in self["list"].onSelectionChanged:
			self["list"].onSelectionChanged.append(self.selectionChanged)
		self.currList = ""
		self.currentSelectedTag = None
		self.currentSelectedIndex = None
		self.currentSelectedPackage = None
		self.saved_currentSelectedPackage = None
		self.restartRequired = False
		self.onLayoutFinish.append(self.getUpdateInfos)

	def exit(self):
		if self.currList == "packages":
			self.currList = "category"
			self.currentSelectedTag = None
			self["list"].style = "category"
			self["list"].setList(self.categoryList)
			self["list"].setIndex(self.currentSelectedIndex)
			self["list"].updateList(self.categoryList)
			self.selectionChanged()
		else:
			iSoftwareTools.cleanupSoftwareTools()
			self.prepareInstall()
			if len(self.cmdList):
				self.session.openWithCallback(self.runExecute, PluginManagerInfo, self.cmdList)
			else:
				self.close()

	def handleHelp(self):
		if self.currList != "status":
			self.session.open(PluginManagerHelp)

	def setState(self, status=None):
		if status:
			self.currList = "status"
			self.statuslist = []
			self["key_green"].setText("")
			self["key_blue"].setText("")
			self["key_yellow"].setText("")
			divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
			if status == "update":
				if isfile(resolveFilename(SCOPE_GUISKIN, "icons/upgrade.png")):
					statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/upgrade.png"))
				else:
					statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/upgrade.png"))
				self.statuslist.append((_("Updating software catalog"), "", _("Searching for available updates. Please wait..."), "", "", statuspng, divpng, None, ""))
			elif status == "sync":
				if isfile(resolveFilename(SCOPE_GUISKIN, "icons/upgrade.png")):
					statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/upgrade.png"))
				else:
					statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/upgrade.png"))
				self.statuslist.append((_("Package list update"), "", _("Searching for new installed or removed packages. Please wait..."), "", "", statuspng, divpng, None, ""))
			elif status == "error":
				self["key_green"].setText(_("Continue"))
				if isfile(resolveFilename(SCOPE_GUISKIN, "icons/remove.png")):
					statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/remove.png"))
				else:
					statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/remove.png"))
				self.statuslist.append((_("Error"), "", _("An error occurred while downloading the packet list. Please try again."), "", "", statuspng, divpng, None, ""))
			self["list"].style = "default"
			self["list"].setList(self.statuslist)

	def getUpdateInfos(self):
		if (iSoftwareTools.lastDownloadDate is not None and iSoftwareTools.NetworkConnectionAvailable is False):
			self.rebuildList()
		else:
			self.setState("update")
			iSoftwareTools.startSoftwareTools(self.getUpdateInfosCB)

	def getUpdateInfosCB(self, retval=None):
		if retval is not None:
			if retval is True:
				if iSoftwareTools.available_updates != 0:
					self["status"].setText(_("There are at least ") + str(iSoftwareTools.available_updates) + " " + _("updates available."))
				else:
					self["status"].setText(_("There are no updates available."))
				self.rebuildList()
			elif retval is False:
				if iSoftwareTools.lastDownloadDate is None:
					self.setState("error")
					if iSoftwareTools.NetworkConnectionAvailable:
						self["status"].setText(_("Update feed not available."))
					else:
						self["status"].setText(_("No network connection available."))
				else:
					iSoftwareTools.lastDownloadDate = time()
					iSoftwareTools.list_updating = True
					self.setState("update")
					iSoftwareTools.getUpdates(self.getUpdateInfosCB)

	def rebuildList(self, retval=None):
		if self.currentSelectedTag is None:
			self.buildCategoryList()
		else:
			self.buildPacketList(self.currentSelectedTag)

	def selectionChanged(self):
		current = self["list"].getCurrent()
		self["status"].setText("")
		if current:
			if self.currList == "packages":
				self["key_red"].setText(_("Back"))
				if current[4] == "installed":
					self["key_green"].setText(_("Uninstall"))
				elif current[4] == "installable":
					self["key_green"].setText(_("Install"))
					if iSoftwareTools.NetworkConnectionAvailable is False:
						self["key_green"].setText("")
				elif current[4] == "remove":
					self["key_green"].setText(_("Undo uninstall"))
				elif current[4] == "install":
					self["key_green"].setText(_("Undo install"))
					if iSoftwareTools.NetworkConnectionAvailable is False:
						self["key_green"].setText("")
				self["key_yellow"].setText(_("View details"))
				self["key_blue"].setText("")
				if len(self.selectedFiles) == 0 and iSoftwareTools.available_updates != 0:
					self["status"].setText(_("There are at least ") + str(iSoftwareTools.available_updates) + " " + _("updates available."))
				elif len(self.selectedFiles) != 0:
					self["status"].setText(str(len(self.selectedFiles)) + " " + _("packages selected."))
				else:
					self["status"].setText(_("There are currently no outstanding actions."))
			elif self.currList == "category":
				self["key_red"].setText(_("Close"))
				self["key_green"].setText("")
				self["key_yellow"].setText("")
				self["key_blue"].setText("")
				if len(self.selectedFiles) == 0 and iSoftwareTools.available_updates != 0:
					self["status"].setText(_("There are at least ") + str(iSoftwareTools.available_updates) + " " + _("updates available."))
					self["key_yellow"].setText(_("Update"))
				elif len(self.selectedFiles) != 0:
					self["status"].setText(str(len(self.selectedFiles)) + " " + _("packages selected."))
					self["key_yellow"].setText(_("Process"))
				else:
					self["status"].setText(_("There are currently no outstanding actions."))

	def getSelectionState(self, detailsFile):
		for entry in self.selectedFiles:
			if entry[0] == detailsFile:
				return True
		return False

	def handleCurrent(self):
		current = self["list"].getCurrent()
		if current:
			if self.currList == "category":
				self.currentSelectedIndex = self["list"].index
				selectedTag = current[2]
				self.buildPacketList(selectedTag)
			elif self.currList == "packages":
				if current[7] != "":
					idx = self["list"].getIndex()
					detailsFile = self.packageList[idx][1]
					if self.packageList[idx][7] == True:
						for entry in self.selectedFiles:
							if entry[0] == detailsFile:
								self.selectedFiles.remove(entry)
					else:
						alreadyinList = False
						for entry in self.selectedFiles:
							if entry[0] == detailsFile:
								alreadyinList = True
						if not alreadyinList:
							if (iSoftwareTools.NetworkConnectionAvailable is False and current[4] in ("installable", "install")):
								pass
							else:
								self.selectedFiles.append((detailsFile, current[4], current[3]))
								self.currentSelectedPackage = ((detailsFile, current[4], current[3]))
					if current[4] == "installed":
						self.packageList[idx] = self.buildEntryComponent(current[0], current[1], current[2], current[3], "remove", True)
					elif current[4] == "installable":
						if iSoftwareTools.NetworkConnectionAvailable:
							self.packageList[idx] = self.buildEntryComponent(current[0], current[1], current[2], current[3], "install", True)
					elif current[4] == "remove":
						self.packageList[idx] = self.buildEntryComponent(current[0], current[1], current[2], current[3], "installed", False)
					elif current[4] == "install":
						if iSoftwareTools.NetworkConnectionAvailable:
							self.packageList[idx] = self.buildEntryComponent(current[0], current[1], current[2], current[3], "installable", False)
					self["list"].setList(self.packageList)
					self["list"].setIndex(idx)
					self["list"].updateList(self.packageList)
					self.selectionChanged()
			elif self.currList == "status":
				iSoftwareTools.lastDownloadDate = time()
				iSoftwareTools.list_updating = True
				self.setState("update")
				iSoftwareTools.getUpdates(self.getUpdateInfosCB)

	def handleSelected(self):
		current = self["list"].getCurrent()
		if current:
			if self.currList == "packages":
				if current[7] != "":
					detailsfile = pathjoin(iSoftwareTools.directory[0], current[1])
					if exists(detailsfile):
						self.saved_currentSelectedPackage = self.currentSelectedPackage
						self.session.openWithCallback(self.detailsClosed, PluginDetails, current)
					else:
						self.session.open(MessageBox, _("Sorry, no details available!"), MessageBox.TYPE_INFO, timeout=10)
			elif self.currList == "category":
				self.prepareInstall()
				if len(self.cmdList):
					self.session.openWithCallback(self.runExecute, PluginManagerInfo, self.cmdList)

	def detailsClosed(self, result=None):
		if result is not None:
			if result is not False:
				self.setState("sync")
				iSoftwareTools.lastDownloadDate = time()
				for entry in self.selectedFiles:
					if entry == self.saved_currentSelectedPackage:
						self.selectedFiles.remove(entry)
				iSoftwareTools.startOpkgListInstalled(self.rebuildList)

	def buildEntryComponent(self, name, details, description, packagename, state, selected=False):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
		imagePath = resolveFilename(SCOPE_GUISKIN, "icons/%s.png" % state)
		statusPng = LoadPixmap(cached=True, path=imagePath)
		if state == "installed":
			return((name, details, description, packagename, state, statusPng, divpng, selected))
		elif state == "installable":
			return((name, details, description, packagename, state, statusPng, divpng, selected))
		elif state == "remove":
			return((name, details, description, packagename, state, statusPng, divpng, selected))
		elif state == "install":
			return((name, details, description, packagename, state, statusPng, divpng, selected))

	def buildPacketList(self, categorytag=None):
		if categorytag is not None:
			self.currList = "packages"
			self.currentSelectedTag = categorytag
			packetlist = []
			for package in iSoftwareTools.packagesIndexlist[:]:
				prerequisites = package[0]["prerequisites"]
				if "tag" in prerequisites:
					for foundtag in prerequisites["tag"]:
						if categorytag == foundtag:
							attributes = package[0]["attributes"]
							if "packagetype" in attributes:
								if attributes["packagetype"] == "internal":
									continue
							packetlist.append([attributes["name"], attributes["details"], attributes["shortdescription"], attributes["packagename"]])
			self.packageList = []
			for x in packetlist:
				status = ""
				name = x[0].strip()
				details = x[1].strip()
				description = x[2].strip()
				if not description:
					description = "No description available."
				packagename = x[3].strip()
				selectState = self.getSelectionState(details)
				if packagename in iSoftwareTools.installed_packetlist:
					status = "remove" if selectState == True else "installed"
					self.packageList.append(self.buildEntryComponent(name, _(details), _(description), packagename, status, selected=selectState))
				else:
					status = "install" if selectState == True else "installable"
					self.packageList.append(self.buildEntryComponent(name, _(details), _(description), packagename, status, selected=selectState))
			if len(self.packageList):
				self.packageList.sort(key=lambda x: x[0])
			self["list"].style = "default"
			self["list"].setList(self.packageList)
			self["list"].updateList(self.packageList)
			self.selectionChanged()

	def buildCategoryList(self):
		self.currList = "category"
		self.categories = []
		self.categoryList = []
		for package in iSoftwareTools.packagesIndexlist[:]:
			prerequisites = package[0]["prerequisites"]
			if "tag" in prerequisites:
				for foundtag in prerequisites["tag"]:
					attributes = package[0]["attributes"]
					if foundtag not in self.categories:
						self.categories.append(foundtag)
						self.categoryList.append(self.buildCategoryComponent(foundtag))
		self.categoryList.sort(key=lambda x: x[0])
		self["list"].style = "category"
		self["list"].setList(self.categoryList)
		self["list"].updateList(self.categoryList)
		self.selectionChanged()

	def buildCategoryComponent(self, tag=None):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
		if tag is not None:
			if tag == "System":
				return((_("System"), _("View list of available system extensions"), tag, divpng))
			elif tag == "Skin":
				return((_("Skins"), _("View list of available skins"), tag, divpng))
			elif tag == "Recording":
				return((_("Recordings"), _("View list of available recording extensions"), tag, divpng))
			elif tag == "Network":
				return((_("Network"), _("View list of available networking extensions"), tag, divpng))
			elif tag == "CI":
				return((_("Common Interface"), _("View list of available CommonInterface extensions"), tag, divpng))
			elif tag == "Default":
				return((_("Default settings"), _("View list of available default settings"), tag, divpng))
			elif tag == "SAT":
				return((_("Satellite equipment"), _("View list of available Satellite equipment extensions."), tag, divpng))
			elif tag == "Software":
				return((_("Software"), _("View list of available software extensions"), tag, divpng))
			elif tag == "Multimedia":
				return((_("Multimedia"), _("View list of available multimedia extensions."), tag, divpng))
			elif tag == "Display":
				return((_("Display and user interface"), _("View list of available display and user interface extensions."), tag, divpng))
			elif tag == "EPG":
				return((_("Electronic Program Guide"), _("View list of available EPG extensions."), tag, divpng))
			elif tag == "Communication":
				return((_("Communication"), _("View list of available communication extensions."), tag, divpng))
			else:  # Dynamically generate non existent tags.
				return((str(tag), _("View list of available ") + str(tag) + " " + _("extensions."), tag, divpng))

	def prepareInstall(self):
		self.cmdList = []
		if iSoftwareTools.available_updates > 0:
			self.cmdList.append((OpkgComponent.CMD_UPGRADE, {"test_only": False}))
		if self.selectedFiles and len(self.selectedFiles):
			for plugin in self.selectedFiles:
				detailsfile = pathjoin(iSoftwareTools.directory[0], plugin[0])
				if exists(detailsfile):
					iSoftwareTools.fillPackageDetails(plugin[0])
					self.package = iSoftwareTools.packageDetails[0]
					if "attributes" in self.package[0]:
						self.attributes = self.package[0]["attributes"]
						if "needsRestart" in self.attributes:
							self.restartRequired = True
					if "package" in self.attributes:
						self.packagefiles = self.attributes["package"]
					if plugin[1] == "installed":
						if self.packagefiles:
							for package in self.packagefiles[:]:
								self.cmdList.append((OpkgComponent.CMD_REMOVE, {"package": package["name"]}))
						else:
							self.cmdList.append((OpkgComponent.CMD_REMOVE, {"package": plugin[2]}))
					else:
						if self.packagefiles:
							for package in self.packagefiles[:]:
								self.cmdList.append((OpkgComponent.CMD_INSTALL, {"package": package["name"]}))
						else:
							self.cmdList.append((OpkgComponent.CMD_INSTALL, {"package": plugin[2]}))
				else:
					if plugin[1] == "installed":
						self.cmdList.append((OpkgComponent.CMD_REMOVE, {"package": plugin[2]}))
					else:
						self.cmdList.append((OpkgComponent.CMD_INSTALL, {"package": plugin[2]}))

	def runExecute(self, result=None):
		if result is not None:
			if result[0] is True:
				self.session.openWithCallback(self.runExecuteFinished, Opkg, cmdList=self.cmdList)
			elif result[0] is False:
				self.cmdList = result[1]
				self.session.openWithCallback(self.runExecuteFinished, Opkg, cmdList=self.cmdList)
		else:
			self.close()

	def runExecuteFinished(self):
		self.reloadPluginlist()
		if plugins.restartRequired or self.restartRequired:
			self.session.openWithCallback(self.ExecuteReboot, MessageBox, _("Install or remove finished.") + " " + _("Do you want to reboot your receiver?"), MessageBox.TYPE_YESNO)
		else:
			self.selectedFiles = []
			self.restartRequired = False
			self.detailsClosed(True)

	def ExecuteReboot(self, result):
		if result:
			self.session.open(TryQuitMainloop, retvalue=3)
		else:
			self.selectedFiles = []
			self.restartRequired = False
			self.detailsClosed(True)

	def reloadPluginlist(self):
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))


class PluginManagerInfo(Screen):
	skin = """
		<screen name="PluginManagerInfo" position="center,center" size="560,450" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="list" render="Listbox" position="5,50" size="550,350" scrollbarMode="showOnDemand" selectionDisabled="1">
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (50, 0), size = (150, 26), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the name
							MultiContentEntryText(pos = (50, 27), size = (540, 23), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 1 is the state
							MultiContentEntryPixmapAlphaTest(pos = (0, 1), size = (48, 48), png = 2), # index 2 is the status pixmap
							MultiContentEntryPixmapAlphaTest(pos = (0, 48), size = (550, 2), png = 3), # index 3 is the div pixmap
						],
					"fonts": [gFont("Regular", 24),gFont("Regular", 22)],
					"itemHeight": 50
					}
				</convert>
			</widget>
			<ePixmap pixmap="skin_default/div-h.png" position="0,404" zPosition="10" size="560,2" transparent="1" alphatest="on" />
			<widget source="status" render="Label" position="5,408" zPosition="10" size="550,44" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""

	def __init__(self, session, cmdlist=None):
		Screen.__init__(self, session)
		self.setTitle(_("Plugin Manager Activity Information"))
		self.cmdlist = cmdlist
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"ok": self.process_all,
			"cancel": self.exit,
			"red": self.exit,
			"green": self.process_extensions,
		}, prio=-1)
		self.infoList = []
		self["list"] = List(self.infoList)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Only extensions."))
		self["status"] = StaticText(_("Following tasks will be done after you press OK!"))
		self.onLayoutFinish.append(self.rebuildList)

	def rebuildList(self):
		self.infoList = []
		if self.cmdlist is not None:
			for entry in self.cmdlist:
				action = "upgrade"
				info = ""
				cmd = entry[0]
				if cmd == 0:
					action = "install"
				elif cmd == 2:
					action = "remove"
				args = entry[1]
				if cmd == 0:
					info = args["package"]
				elif cmd == 2:
					info = args["package"]
				else:
					info = _("%s %s software because updates are available.") % getBoxDisplayName()
				self.infoList.append(self.buildEntryComponent(action, info))
			self["list"].setList(self.infoList)
			self["list"].updateList(self.infoList)

	def buildEntryComponent(self, action, info):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
		imagePath = resolveFilename(SCOPE_GUISKIN, "icons/%s.png" % action)
		statusPng = LoadPixmap(cached=True, path=imagePath)
		if action == "install":
			return((_("Installing"), info, statusPng, divpng))
		elif action == "remove":
			return((_("Removing"), info, statusPng, divpng))
		else:
			return((_("Upgrading"), info, statusPng, divpng))

	def exit(self):
		self.close()

	def process_all(self):
		self.close((True, None))

	def process_extensions(self):
		self.infoList = []
		if self.cmdlist is not None:
			for entry in self.cmdlist:
				cmd = entry[0]
				if entry[0] in (0, 2):
					self.infoList.append((entry))
		self.close((False, self.infoList))


class PluginManagerHelp(Screen):
	skin = """
		<screen name="PluginManagerHelp" position="center,center" size="560,450" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="list" render="Listbox" position="5,50" size="550,350" scrollbarMode="showOnDemand" selectionDisabled="1">
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (50, 0), size = (540, 26), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the name
							MultiContentEntryText(pos = (50, 27), size = (540, 23), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 1 is the state
							MultiContentEntryPixmapAlphaTest(pos = (0, 1), size = (48, 48), png = 2), # index 2 is the status pixmap
							MultiContentEntryPixmapAlphaTest(pos = (0, 48), size = (550, 2), png = 3), # index 3 is the div pixmap
						],
					"fonts": [gFont("Regular", 24),gFont("Regular", 22)],
					"itemHeight": 50
					}
				</convert>
			</widget>
			<ePixmap pixmap="skin_default/div-h.png" position="0,404" zPosition="10" size="560,2" transparent="1" alphatest="on" />
			<widget source="status" render="Label" position="5,408" zPosition="10" size="550,44" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Plugin Manager Help"))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"cancel": self.exit,
			"red": self.exit,
		}, prio=-1)
		self.helpList = []
		self["list"] = List(self.helpList)
		self["key_red"] = StaticText(_("Close"))
		self["status"] = StaticText(_("A small overview of the available icon states and actions."))
		self.onLayoutFinish.append(self.rebuildList)

	def rebuildList(self):
		self.helpList = []
		self.helpList.append(self.buildEntryComponent("install"))
		self.helpList.append(self.buildEntryComponent("installable"))
		self.helpList.append(self.buildEntryComponent("installed"))
		self.helpList.append(self.buildEntryComponent("remove"))
		self["list"].setList(self.helpList)
		self["list"].updateList(self.helpList)

	def buildEntryComponent(self, state):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
		imagePath = resolveFilename(SCOPE_GUISKIN, "icons/%s.png" % state)
		statusPng = LoadPixmap(cached=True, path=imagePath)
		if state == "installed":
			return((_("This plugin is installed."), _("You can remove this plugin."), statusPng, divpng))
		elif state == "installable":
			return((_("This plugin is not installed."), _("You can install this plugin."), statusPng, divpng))
		elif state == "install":
			return((_("This plugin will be installed."), _("You can cancel the installation."), statusPng, divpng))
		elif state == "remove":
			return((_("This plugin will be removed."), _("You can cancel the removal."), statusPng, divpng))

	def exit(self):
		self.close()


class PluginDetails(Screen, PackageInfoHandler):
	skin = """
		<screen name="PluginDetails" position="center,center" size="600,440" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="author" render="Label" position="10,50" size="500,25" zPosition="10" font="Regular;21" transparent="1" />
			<widget name="statuspic" position="550,40" size="48,48" alphatest="on"/>
			<widget name="divpic" position="0,80" size="600,2" alphatest="on"/>
			<widget name="detailtext" position="10,90" size="270,330" zPosition="10" font="Regular;21" transparent="1" halign="left" valign="top"/>
			<widget name="screenshot" position="290,90" size="300,330" alphatest="on"/>
		</screen>"""

	def __init__(self, session, packagedata=None):
		Screen.__init__(self, session)
		self.language = international.getLanguage()
		self.attributes = None
		PackageInfoHandler.__init__(self, self.statusCallback, blocking=False)
		self.directory = resolveFilename(SCOPE_METADIR)
		if packagedata:
			self.pluginname = packagedata[0]
			self.details = packagedata[1]
			self.pluginstate = packagedata[4]
			self.statuspicinstance = packagedata[5]
			self.divpicinstance = packagedata[6]
			self.fillPackageDetails(self.details)
			self.setTitle(_("Plugin Details: %s") % self.pluginname)
		else:
			self.setTitle(_("Plugin Details"))
		self.thumbnail = ""
		self["actions"] = HelpableActionMap(self, ["CancelActions", "ColorActions", "DirectionActions"], {
			"cancel": self.exit,
			"red": self.exit,
			"green": self.go,
			"up": self.pageUp,
			"down": self.pageDown,
			"left": self.pageUp,
			"right": self.pageDown,
		}, prio=-1)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText("")
		self["author"] = StaticText()
		self["statuspic"] = Pixmap()
		self["divpic"] = Pixmap()
		self["screenshot"] = Pixmap()
		self["detailtext"] = ScrollLabel()
		self["statuspic"].hide()
		self["screenshot"].hide()
		self["divpic"].hide()
		self.package = self.packageDetails[0]
		if "attributes" in self.package[0]:
			self.attributes = self.package[0]["attributes"]
		self.restartRequired = False
		self.cmdList = []
		self.okText = _("After pressing OK, please wait!")
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.paintScreenshotPixmapCB)
		self.onLayoutFinish.append(self.setInfos)

	def exit(self):
		self.close(False)

	def pageUp(self):
		self["detailtext"].pageUp()

	def pageDown(self):
		self["detailtext"].pageDown()

	def statusCallback(self, status, progress):
		pass

	def setInfos(self):
		if "screenshot" in self.attributes:
			self.loadThumbnail(self.attributes)

		if "name" in self.attributes:
			self.pluginname = self.attributes["name"]
		else:
			self.pluginname = _("unknown")
		if "author" in self.attributes:
			self.author = self.attributes["author"]
		else:
			self.author = _("unknown")
		if "description" in self.attributes:
			self.description = _(self.attributes["description"].replace("\\n", "\n"))
		else:
			self.description = _("No description available.")
		self["author"].setText(_("Author: ") + self.author)
		self["detailtext"].setText(_(self.description))
		if self.pluginstate in ("installable", "install"):
			if iSoftwareTools.NetworkConnectionAvailable:
				self["key_green"].setText(_("Install"))
			else:
				self["key_green"].setText("")
		else:
			self["key_green"].setText(_("Remove"))

	def loadThumbnail(self, entry):
		thumbnailUrl = None
		if "screenshot" in entry:
			thumbnailUrl = entry["screenshot"]
			if self.language == "de":
				if thumbnailUrl[-7:] == "_en.jpg":
					thumbnailUrl = thumbnailUrl[:-7] + "_de.jpg"
		if thumbnailUrl is not None:
			self.thumbnail = "/tmp/" + thumbnailUrl.split("/")[-1]
			print("[PluginDetails] downloading screenshot %s to %s" % (thumbnailUrl, self.thumbnail))
			if iSoftwareTools.NetworkConnectionAvailable:
				reactor.callInThread(self.downloadThumbnail, thumbnailUrl)
			else:
				self.setThumbnail(noScreenshot=True)
		else:
			self.setThumbnail(noScreenshot=True)

	def downloadThumbnail(self, thumbnailUrl=None):
		try:
			response = requests.get(thumbnailUrl, headers={"User-agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en; rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5"})
			with open(self.thumbnail, "wb") as f:
				f.write(response.content)
			self.setThumbnail()
		except OSError as err:
			self.fetchFailed(err)

	def setThumbnail(self, noScreenshot=False):
		if not noScreenshot:
			filename = self.thumbnail
		else:
			if isfile(resolveFilename(SCOPE_GUISKIN, "noprev.png")):
				filename = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "noprev.png"))
			else:
				filename = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/noprev.png"))
		sc = AVSwitch().getFramebufferScale()
		self.picload.setPara((self["screenshot"].instance.size().width(), self["screenshot"].instance.size().height(), sc[0], sc[1], False, 1, "#00000000"))
		self.picload.startDecode(filename)
		if self.statuspicinstance != None:
			self["statuspic"].instance.setPixmap(self.statuspicinstance.__deref__())
			self["statuspic"].show()
		if self.divpicinstance != None:
			self["divpic"].instance.setPixmap(self.divpicinstance.__deref__())
			self["divpic"].show()

	def paintScreenshotPixmapCB(self, picInfo=None):
		ptr = self.picload.getData()
		if ptr != None:
			self["screenshot"].instance.setPixmap(ptr.__deref__())
			self["screenshot"].show()
		else:
			self.setThumbnail(noScreenshot=True)

	def go(self):
		if "package" in self.attributes:
			self.packagefiles = self.attributes["package"]
		if "needsRestart" in self.attributes:
			self.restartRequired = True
		self.cmdList = []
		if self.pluginstate in ("installed", "remove"):
			if self.packagefiles:
				for package in self.packagefiles[:]:
					self.cmdList.append((OpkgComponent.CMD_REMOVE, {"package": package["name"]}))
					if len(self.cmdList):
						self.session.openWithCallback(self.runRemove, MessageBox, _("Do you want to remove the package:\n") + self.pluginname + "\n" + self.okText)
		else:
			if iSoftwareTools.NetworkConnectionAvailable:
				if self.packagefiles:
					for package in self.packagefiles[:]:
						self.cmdList.append((OpkgComponent.CMD_INSTALL, {"package": package["name"]}))
						if len(self.cmdList):
							self.session.openWithCallback(self.runUpgrade, MessageBox, _("Do you want to install the package:\n") + self.pluginname + "\n" + self.okText)

	def runUpgrade(self, result):
		if result:
			self.session.openWithCallback(self.runUpgradeFinished, Opkg, cmdList=self.cmdList)

	def runUpgradeFinished(self):
		self.reloadPluginlist()
		if plugins.restartRequired or self.restartRequired:
			self.session.openWithCallback(self.UpgradeReboot, MessageBox, _("Installation finished.") + " " + _("Do you want to reboot your receiver?"), MessageBox.TYPE_YESNO)
		else:
			self.close(True)

	def UpgradeReboot(self, result):
		if result:
			self.session.open(TryQuitMainloop, retvalue=3)
		self.close(True)

	def runRemove(self, result):
		if result:
			self.session.openWithCallback(self.runRemoveFinished, Opkg, cmdList=self.cmdList)

	def runRemoveFinished(self):
		self.close(True)

	def reloadPluginlist(self):
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))

	def fetchFailed(self, string):
		self.setThumbnail(noScreenshot=True)
		print("[PluginDetails] fetch failed %s " % string.getErrorMessage())


class UpdatePlugin(Screen):
	skin = """
		<screen name="UpdatePlugin" position="center,center" size="550,300" >
			<widget name="activityslider" position="0,0" size="550,5"  />
			<widget name="slider" position="0,150" size="550,30"  />
			<widget source="package" render="Label" position="10,30" size="540,20" font="Regular;18" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
			<widget source="status" render="Label" position="10,180" size="540,100" font="Regular;20" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
		</screen>"""

	def __init__(self, session, *args):
		Screen.__init__(self, session)
		self.setTitle(_("Software Update"))
		self.sliderPackages = {"dreambox-dvb-modules": 1, "enigma2": 2, "tuxbox-image-info": 3}
		self.slider = Slider(0, 4)
		self["slider"] = self.slider
		self.activityslider = Slider(0, 100)
		self["activityslider"] = self.activityslider
		self.status = StaticText(_("Please wait..."))
		self["status"] = self.status
		self.package = StaticText(_("Package list update"))
		self["package"] = self.package
		self.okText = _("Press OK on your remote control to continue.")
		self.packages = 0
		self.error = 0
		self.processed_packages = []
		self.total_packages = None
		self.TrafficCheck = False
		self.TrafficResult = False
		self.CheckDateDone = False
		self.activity = 0
		self.activityTimer = eTimer()
		self.activityTimer.callback.append(self.doActivityTimer)
		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)
		self.updating = False
		self["actions"] = HelpableActionMap(self, ["OkCancelActions"], {
			"ok": self.exit,
			"cancel": self.exit
		}, prio=-1)
		self.activityTimer.start(100, False)

	def CheckDate(self):  # Check if image is not to old for update (max 30days).
		self.CheckDateDone = True
		tmpdate = getEnigmaVersionString()
		imageDate = date(int(tmpdate[0:4]), int(tmpdate[5:7]), int(tmpdate[8:10]))
		datedelay = imageDate + timedelta(days=30)
		message = _("Your image is out of date!\n\n"
			"After such a long time, there is a risk that your %s %s will not\n"
			"boot after online-update, or will show disfunction in running Image.\n\n"
			"A new flash will increase the stability\n\n"
			"An online update is done at your own risk !!\n\n\n"
			"Do you still want to update?"
		) % getBoxDisplayName()
		if datedelay > date.today():
			self.updating = True
			self.activityTimer.start(100, False)
			self.opkg.startCmd(OpkgComponent.CMD_UPGRADE_LIST)
		else:
			print("[SOFTWAREMANAGER] Your image is to old (%s), you need to flash new !!" % getEnigmaVersionString())
			self.session.openWithCallback(self.checkDateCallback, MessageBox, message, default=False)
			return

	def checkDateCallback(self, ret):
		print(ret)
		if ret:
			self.activityTimer.start(100, False)
			self.opkg.startCmd(OpkgComponent.CMD_UPGRADE_LIST)
		else:
			self.close()
			return

	def checkTrafficLight(self):
		currentTimeoutDefault = getdefaulttimeout()
		setdefaulttimeout(3)
		message = ""
		default = True
		doUpdate = True
		# TODO: Use Twisted's URL fetcher, urlopen is evil. And it can run in parallel to the package update.
		try:
			urlopenATV = "https://ampel.mynonpublic.com/Ampel/index.php"
			d = urlopen(urlopenATV)
			tmpStatus = d.read().decode("UTF-8")
			if (exists("/etc/.beta") and "rot.png" in tmpStatus) or "gelb.png" in tmpStatus:
				message = _("Caution update not yet tested !!") + "\n" + _("Update at your own risk") + "\n" + _("For more information see https://www.opena.tv")  # + "\n\n" + _("Last Status Date") + ": "  + statusDate + "\n\n"
				default = False
			elif "rot.png" in tmpStatus:
				message = _("Update is reported as faulty !!") + "\n" + _("Aborting update progress") + "\n" + _("For more information see https://www.opena.tv")  # + "\n\n" + _("Last Status Date") + ": " + statusDate
				default = False
				doUpdate = False
		except:
			message = _("The status of the current update could not be checked because https://www.opena.tv could not be reached for some reason") + "\n"
			default = False
		setdefaulttimeout(currentTimeoutDefault)
		if default:
			self.runUpgrade(True)  # We'll ask later.
		else:
			if doUpdate:  # Ask for Update,
				message += _("Do you want to update your box?") + "\n" + _("After pressing OK, please wait!")
				self.session.openWithCallback(self.runUpgrade, MessageBox, message, default=default)
			else:  # Don't Update RED LIGHT!
				self.session.open(MessageBox, message, MessageBox.TYPE_ERROR, timeout=20)
				self.runUpgrade(False)

	def runUpgrade(self, result):
		self.TrafficResult = result
		if result:
			self.TrafficCheck = True
			self.opkg.startCmd(OpkgComponent.CMD_UPGRADE_LIST)
		else:
			self.TrafficCheck = False
			self.activityTimer.stop()
			self.activityslider.setValue(0)
			self.exit()

	def doActivityTimer(self):
		if not self.CheckDateDone:
			self.activityTimer.stop()
			self.CheckDate()
			return
		self.activity += 1
		if self.activity == 100:
			self.activity = 0
		self.activityslider.setValue(self.activity)

	def opkgCallback(self, event, param):
		if event == OpkgComponent.EVENT_DOWNLOAD:
			self.status.setText(_("Downloading"))
		elif event == OpkgComponent.EVENT_UPGRADE:
			if param in self.sliderPackages:
				self.slider.setValue(self.sliderPackages[param])
			self.package.setText(param)
			self.status.setText(_("Updating") + ": %s/%s" % (self.packages, self.total_packages))
			if not param in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == OpkgComponent.EVENT_INSTALL:
			self.package.setText(param)
			self.status.setText(_("Installing"))
			if not param in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == OpkgComponent.EVENT_REMOVE:
			self.package.setText(param)
			self.status.setText(_("Removing"))
			if not param in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == OpkgComponent.EVENT_CONFIGURING:
			self.package.setText(param)
			self.status.setText(_("Configuring"))

		elif event == OpkgComponent.EVENT_MODIFIED:
			if config.plugins.softwaremanager.overwriteConfigFiles.value in ("N", "Y"):
				self.opkg.write(True and config.plugins.softwaremanager.overwriteConfigFiles.value)
			else:
				self.session.openWithCallback(
					self.modificationCallback,
					MessageBox,
					_("Configuration file '%s' has been modified since it was installed, would you like to keep the modified version?") % (param)
				)
		elif event == OpkgComponent.EVENT_ERROR:
			self.error += 1
		elif event == OpkgComponent.EVENT_DONE:
			if self.updating:
				self.updating = False
				self.opkg.startCmd(OpkgComponent.CMD_UPGRADE_LIST)
			elif self.opkg.currentCommand == OpkgComponent.CMD_UPGRADE_LIST:
				self.total_packages = len(self.opkg.getFetchedList())
				if self.total_packages and not self.TrafficCheck:
					self.checkTrafficLight()
					return
				if self.total_packages and self.TrafficCheck and self.TrafficResult:
					try:
						if config.plugins.softwaremanager.updatetype.value == "cold":
							self.startActualUpgrade("cold")
						else:
							self.startActualUpgrade("hot")
					except:
						self.startActualUpgrade("hot")
				else:
					self.session.openWithCallback(self.close, MessageBox, _("Nothing to upgrade"), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
			elif self.error == 0:
				self.slider.setValue(4)
				self.activityTimer.stop()
				self.activityslider.setValue(0)
				self.package.setText(_("Done - Installed or upgraded %d packages") % self.packages)
				self.status.setText(self.okText)
			else:
				self.activityTimer.stop()
				self.activityslider.setValue(0)
				error = _("your %s %s might be unusable now. Please consult the manual for further assistance before rebooting your %s %s.") % getBoxDisplayName()
				if self.packages == 0:
					error = _("No packages were upgraded yet. So you can check your network and try again.")
				if self.updating:
					error = _("Your %s %s isn't connected to the Internet properly. Please check it and try again.") % getBoxDisplayName()
				self.status.setText(_("Error") + " - " + error)

	def startActualUpgrade(self, answer):
		if not answer or not answer[1]:
			self.close()
			return
		if answer[1] == "cold":
			self.session.open(TryQuitMainloop, retvalue=42)
			self.close()
		else:
			self.opkg.startCmd(OpkgComponent.CMD_UPGRADE, args={"test_only": False})

	def modificationCallback(self, res):
		self.opkg.write(res and "N" or "Y")

	def exit(self):
		if not self.opkg.isRunning():
			if self.packages != 0 and self.error == 0:  # Check and remove previously removed/deleted languages get re-installed on updating enigma2.
				if fileExists("/etc/enigma2/.removelang"):
					packages = international.getPurgablePackages(config.osd.language.value)
					if packages:
						international.deleteLanguagePackages(packages)
					system("touch /etc/enigma2/.removelang")
				self.restoreMetrixHD()
			else:
				self.close()
		else:
			if not self.updating:
				self.opkg.stop()
				self.close()

	def exitAnswer(self, result):
		if result is not None and result:
			self.session.open(TryQuitMainloop, retvalue=2)
		self.close()

	def restoreMetrixHD(self):
		try:
			if config.skin.primary_skin.value == "MetrixHD/skin.MySkin.xml" and not isfile("/usr/share/enigma2/MetrixHD/skin.MySkin.xml"):
				self.session.openWithCallback(self.restoreMetrixHDCallback, RestoreMyMetrixHD)
			elif config.skin.primary_skin.value == "MetrixHD/skin.MySkin.xml" and config.plugins.MyMetrixLiteOther.EHDenabled.value != "0":
				from Plugins.Extensions.MyMetrixLite.ActivateSkinSettings import ActivateSkinSettings
				ActivateSkinSettings().RefreshIcons()
				self.restoreMetrixHDCallback()
			else:
				self.restoreMetrixHDCallback()
		except:
			self.restoreMetrixHDCallback()

	def restoreMetrixHDCallback(self, ret=None):
		self.session.openWithCallback(self.exitAnswer, MessageBox, _("Upgrade finished.") + " " + _("Do you want to reboot your %s %s?") % getBoxDisplayName())


class IPKGMenu(Screen):
	skin = """
		<screen name="IPKGMenu" position="center,center" size="560,400" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="filelist" position="5,50" size="550,340" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Select Upgrade Source To Edit"))
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Edit"))
		self.sel = []
		self.val = []
		self.entry = False
		self.exe = False
		self.path = ""
		self["actions"] = HelpableActionMap(self, ["OkCancelActions"], {
			"ok": self.KeyOk,
			"cancel": self.keyCancel
		}, prio=-1)
		self["shortcuts"] = HelpableActionMap(self, ["ColorActions"], {
			"red": self.keyCancel,
			"green": self.KeyOk,
		})
		self["filelist"] = MenuList([])
		self.fill_list()

	def fill_list(self):
		flist = []
		self.path = "/etc/opkg/"
		if (exists(self.path) == False):
			self.entry = False
			return
		for file in listdir(self.path):
			if file.endswith(".conf"):
				if file not in ("arch.conf", "opkg.conf"):
					flist.append((file))
					self.entry = True
		self["filelist"].l.setList(flist)

	def KeyOk(self):
		if (self.exe == False) and (self.entry == True):
			self.sel = self["filelist"].getCurrent()
			self.val = self.path + self.sel
			self.session.open(IPKGSource, self.val)

	def keyCancel(self):
		self.close()

	def Exit(self):
		self.close()


class IPKGSource(Screen):
	skin = """
		<screen name="IPKGSource" position="center,center" size="560,80" title="Edit upgrade source url." >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="text" position="5,50" size="550,25" font="Regular;20" backgroundColor="background" foregroundColor="#cccccc" />
		</screen>"""

	def __init__(self, session, configfile=None):
		Screen.__init__(self, session)
		self.setTitle(_("Edit Upgrade Source URL"))
		self.configfile = configfile
		text = ""
		if self.configfile:
			try:
				fp = open(configfile, "r")
				sources = fp.readlines()
				if sources:
					text = sources[0]
				fp.close()
			except OSError:
				pass
		desk = getDesktop(0)
		x = int(desk.size().width())
		y = int(desk.size().height())
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		if (y >= 720):
			self["text"] = Input(text, maxSize=False, type=Input.TEXT)
		else:
			self["text"] = Input(text, maxSize=False, visible_width=55, type=Input.TEXT)
		self["actions"] = HelpableNumberActionMap(self, ["WizardActions", "InputActions", "TextEntryActions", "KeyboardInputActions", "ShortcutActions"], {
			"ok": self.go,
			"back": self.close,
			"red": self.close,
			"green": self.go,
			"left": self.keyLeft,
			"right": self.keyRight,
			"home": self.keyHome,
			"end": self.keyEnd,
			"deleteForward": self.keyDeleteForward,
			"deleteBackward": self.keyDeleteBackward,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, prio=-1)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["text"].right()

	def go(self):
		text = self["text"].getText()
		if text:
			fp = open(self.configfile, "w")
			fp.write(text)
			fp.write("\n")
			fp.close()
		self.close()

	def keyLeft(self):
		self["text"].left()

	def keyRight(self):
		self["text"].right()

	def keyHome(self):
		self["text"].home()

	def keyEnd(self):
		self["text"].end()

	def keyDeleteForward(self):
		self["text"].delete()

	def keyDeleteBackward(self):
		self["text"].deleteBackward()

	def keyNumberGlobal(self, number):
		self["text"].number(number)


class PacketManager(Screen, NumericalTextInput):
	skin = """
		<screen name="PacketManager" position="center,center" size="530,420" title="Packet Manager" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="list" render="Listbox" position="5,50" size="520,365" scrollbarMode="showOnDemand">
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (5, 1), size = (440, 28), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the name
							MultiContentEntryText(pos = (5, 26), size = (440, 20), font=1, flags = RT_HALIGN_LEFT, text = 2), # index 2 is the description
							MultiContentEntryPixmapAlphaTest(pos = (445, 2), size = (48, 48), png = 4), # index 4 is the status pixmap
							MultiContentEntryPixmapAlphaTest(pos = (5, 50), size = (510, 2), png = 5), # index 4 is the div pixmap
						],
					"fonts": [gFont("Regular", 22),gFont("Regular", 14)],
					"itemHeight": 52
					}
				</convert>
			</widget>
		</screen>"""

	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		NumericalTextInput.__init__(self)
		self.setTitle(_("Packet Manager"))
		self.setUseableChars(u"1234567890abcdefghijklmnopqrstuvwxyz")
		self["shortcuts"] = HelpableNumberActionMap(self, ["ShortcutActions", "WizardActions", "NumberActions", "InputActions", "InputAsciiActions", "KeyboardInputActions"], {
			"ok": self.go,
			"back": self.exit,
			"red": self.exit,
			"green": self.reload,
			"gotAsciiCode": self.keyGotAscii,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, prio=-1)
		self.packageList = []
		self.statuslist = []
		self["list"] = List(self.packageList)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Reload"))
		self.packageList_updating = True
		self.packetlist = []
		self.installed_packetlist = {}
		self.upgradeable_packages = {}
		self.Console = Console()
		self.cmdList = []
		self.cachelist = []
		self.cache_ttl = 86400  # 600 is default, 0 disables, Seconds cache is considered valid (24h should be okay for caching ipkgs).
		self.cache_file = eEnv.resolve("${libdir}/enigma2/python/Plugins/SystemPlugins/SoftwareManager/packetmanager.cache")  # Path to cache directory.
		self.okText = _("After pressing OK, please wait!")
		self.unwanted_extensions = ("-dbg", "-dev", "-doc", "-staticdev", "-src", "busybox")
		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)
		self.onLayoutFinish.append(self.rebuildList)
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmAscii)

	def keyNumberGlobal(self, val):
		key = self.getKey(val)
		if key is not None:
			keyvalue = key.encode("utf-8")
			if len(keyvalue) == 1:
				self.setNextIdx(keyvalue[0])

	def keyGotAscii(self):
		keyvalue = chr(getPrevAsciiCode())
		if len(keyvalue) == 1:
			self.setNextIdx(keyvalue[0])

	def setNextIdx(self, char):
		if char in ("0", "1", "a"):
			self["list"].setIndex(0)
		else:
			idx = self.getNextIdx(char)
			if idx and idx <= self["list"].count:
				self["list"].setIndex(idx)

	def getNextIdx(self, char):
		for idx, i in enumerate(self["list"].list):
			if i[0] and (i[0][0] == char):
				return idx

	def exit(self):
		self.opkg.stop()
		if self.Console is not None:
			if len(self.Console.appContainers):
				for name in list(self.Console.appContainers.keys()):
					self.Console.kill(name)
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)
		self.close()

	def reload(self):
		if (exists(self.cache_file) == True):
			remove(self.cache_file)
			self.packageList_updating = True
			self.rebuildList()

	def setStatus(self, status=None):
		if status:
			self.statuslist = []
			divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
			if status == "update":
				if isfile(resolveFilename(SCOPE_GUISKIN, "icons/upgrade.png")):
					statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/upgrade.png"))
				else:
					statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/upgrade.png"))
				self.statuslist.append((_("Package list update"), "", _("Trying to download a new packet list. Please wait..."), "", statuspng, divpng))
				self["list"].setList(self.statuslist)
			elif status == "error":
				if isfile(resolveFilename(SCOPE_GUISKIN, "icons/remove.png")):
					statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/remove.png"))
				else:
					statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/remove.png"))
				self.statuslist.append((_("Error"), "", _("An error occurred while downloading the packet list. Please try again."), "", statuspng, divpng))
				self["list"].setList(self.statuslist)

	def rebuildList(self):
		self.setStatus("update")
		self.inv_cache = 0
		self.vc = valid_cache(self.cache_file, self.cache_ttl)
		if self.cache_ttl > 0 and self.vc != 0:
			try:
				self.buildPacketList()
			except:
				self.inv_cache = 1
		if self.cache_ttl == 0 or self.inv_cache == 1 or self.vc == 0:
			self.run = 0
			self.opkg.startCmd(OpkgComponent.CMD_UPDATE)

	def go(self, returnValue=None):
		cur = self["list"].getCurrent()
		if cur:
			status = cur[3]
			package = cur[0]
			self.cmdList = []
			if status == "installed":
				self.cmdList.append((OpkgComponent.CMD_REMOVE, {"package": package}))
				if len(self.cmdList):
					self.session.openWithCallback(self.runRemove, MessageBox, _("Do you want to remove the package:\n") + package + "\n" + self.okText)
			elif status == "upgradeable":
				self.cmdList.append((OpkgComponent.CMD_INSTALL, {"package": package}))
				if len(self.cmdList):
					self.session.openWithCallback(self.runUpgrade, MessageBox, _("Do you want to upgrade the package:\n") + package + "\n" + self.okText)
			elif status == "installable":
				self.cmdList.append((OpkgComponent.CMD_INSTALL, {"package": package}))
				if len(self.cmdList):
					self.session.openWithCallback(self.runUpgrade, MessageBox, _("Do you want to install the package:\n") + package + "\n" + self.okText)

	def runRemove(self, result):
		if result:
			self.session.openWithCallback(self.runRemoveFinished, Opkg, cmdList=self.cmdList)

	def runRemoveFinished(self):
		self.session.openWithCallback(self.RemoveReboot, MessageBox, _("Remove Finished.") + " " + _("Do you want to reboot your receiver?"), MessageBox.TYPE_YESNO)

	def RemoveReboot(self, result):
		if result is None:
			return
		if result is False:
			cur = self["list"].getCurrent()
			if cur:
				item = self["list"].getIndex()
				self.packageList[item] = self.buildEntryComponent(cur[0], cur[1], cur[2], "installable")
				self.cachelist[item] = [cur[0], cur[1], cur[2], "installable"]
				self["list"].setList(self.packageList)
				write_cache(self.cache_file, self.cachelist)
				self.reloadPluginlist()
		if result:
			self.session.open(TryQuitMainloop, retvalue=3)

	def runUpgrade(self, result):
		if result:
			self.session.openWithCallback(self.runUpgradeFinished, Opkg, cmdList=self.cmdList)

	def runUpgradeFinished(self):
		self.session.openWithCallback(self.UpgradeReboot, MessageBox, _("Upgrade finished.") + " " + _("Do you want to reboot your receiver?"), MessageBox.TYPE_YESNO)

	def UpgradeReboot(self, result):
		if result is None:
			return
		if result is False:
			cur = self["list"].getCurrent()
			if cur:
				item = self["list"].getIndex()
				self.packageList[item] = self.buildEntryComponent(cur[0], cur[1], cur[2], "installed")
				self.cachelist[item] = [cur[0], cur[1], cur[2], "installed"]
				self["list"].setList(self.packageList)
				write_cache(self.cache_file, self.cachelist)
				self.reloadPluginlist()
		if result:
			self.session.open(TryQuitMainloop, retvalue=3)

	def opkgCallback(self, event, param):
		if event == OpkgComponent.EVENT_ERROR:
			self.packageList_updating = False
			self.setStatus("error")
		elif event == OpkgComponent.EVENT_DONE:
			if self.packageList_updating:
				self.packageList_updating = False
				if not self.Console:
					self.Console = Console()
				cmd = self.opkg.opkg + " list"
				self.Console.ePopen(cmd, self.OpkgList_Finished)

	def OpkgList_Finished(self, result, retval, extra_args=None):
		if result:
			result = result.replace("\n ", " - ")
			self.packetlist = []
			last_name = ""
			for x in result.splitlines():
				tokens = x.split(" - ")
				name = tokens[0].strip()
				if not any((name.endswith(x) or name.find("locale") != -1) for x in self.unwanted_extensions):
					l = len(tokens)
					version = l > 1 and tokens[1].strip() or ""
					descr = l > 3 and tokens[3].strip() or l > 2 and tokens[2].strip() or ""
					if name == last_name:
						continue
					last_name = name
					self.packetlist.append([name, version, descr])
		if not self.Console:
			self.Console = Console()
		cmd = self.opkg.opkg + " list_installed"
		self.Console.ePopen(cmd, self.OpkgListInstalled_Finished)

	def OpkgListInstalled_Finished(self, result, retval, extra_args=None):
		if result:
			self.installed_packetlist = {}
			for x in result.splitlines():
				tokens = x.split(" - ")
				name = tokens[0].strip()
				if not any(name.endswith(x) for x in self.unwanted_extensions):
					l = len(tokens)
					version = l > 1 and tokens[1].strip() or ""
					self.installed_packetlist[name] = version
		if not self.Console:
			self.Console = Console()
		cmd = "opkg list-upgradable"
		self.Console.ePopen(cmd, self.OpkgListUpgradeable_Finished)

	def OpkgListUpgradeable_Finished(self, result, retval, extra_args=None):
		if result:
			self.upgradeable_packages = {}
			for x in result.splitlines():
				tokens = x.split(" - ")
				name = tokens[0].strip()
				if not any(name.endswith(x) for x in self.unwanted_extensions):
					l = len(tokens)
					version = l > 2 and tokens[2].strip() or ""
					self.upgradeable_packages[name] = version
		self.buildPacketList()

	def buildEntryComponent(self, name, version, description, state):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
		if not description:
			description = "No description available."
		imagePath = resolveFilename(SCOPE_GUISKIN, "icons/%s.png" % state)
		statusPng = LoadPixmap(cached=True, path=imagePath)
		return((name, version, _(description), state, statusPng, divpng))

	def buildPacketList(self):
		self.packageList = []
		self.cachelist = []
		if self.cache_ttl > 0 and self.vc != 0:
			print("Loading packagelist cache from %s" % self.cache_file)
			try:
				self.cachelist = load_cache(self.cache_file)
				if len(self.cachelist) > 0:
					for x in self.cachelist:
						self.packageList.append(self.buildEntryComponent(x[0], x[1], x[2], x[3]))
					self["list"].setList(self.packageList)
			except:
				self.inv_cache = 1
		if self.cache_ttl == 0 or self.inv_cache == 1 or self.vc == 0:
			print("rebuilding fresh package list")
			for x in self.packetlist:
				status = "installable"
				if x[0] in self.installed_packetlist:
					status = "upgradeable" if x[0] in self.upgradeable_packages else "installed"
				self.packageList.append(self.buildEntryComponent(x[0], x[1], x[2], status))
				self.cachelist.append([x[0], x[1], x[2], status])
			write_cache(self.cache_file, self.cachelist)
			self["list"].setList(self.packageList)

	def reloadPluginlist(self):
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))


class IpkgInstaller(Screen):
	skin = """
		<screen name="IpkgInstaller" position="center,center" size="550,450" title="Install extensions" >
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


def filescan_open(list, session, **kwargs):
	filelist = [x.path for x in list]
	session.open(IpkgInstaller, filelist)  # List.


def filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	return Scanner(mimetypes=["application/x-debian-package"], paths_to_scan=[
		ScanPath(path="ipk", with_subdirs=True),
		ScanPath(path="", with_subdirs=False),
	], name="Ipkg", description=_("Install extensions."), openfnc=filescan_open)


class BackupHelper(Screen):
	skin = """
		<screen name="BackupHelper" position="0,0" size="1,1" title="SoftwareManager">
		</screen>"""

	def __init__(self, session, args=0):
		Screen.__init__(self, session)
		self.args = args
		self.backuppath = getBackupPath()
		if not isdir(self.backuppath):
			self.backuppath = getOldBackupPath()
		self.backupfile = getBackupFilename()
		self.fullbackupfilename = pathjoin(self.backuppath, self.backupfile)
		self.callLater(self.doAction)

	def doAction(self):
		doClose = True
		if self.args == 1:
			self.session.openWithCallback(self.backupDone, BackupScreen, runBackup=True)
			doClose = False
		elif self.args == 2:
			if isfile(self.fullbackupfilename):
				self.session.openWithCallback(self.startRestore, MessageBox, _("Are you sure you want to restore the backup?\nYour receiver will restart after the backup has been restored!"), default=False)
				doClose = False
			else:
				self.session.open(MessageBox, _("Sorry, no backups found!"), MessageBox.TYPE_INFO, timeout=10)
		elif self.args == 3:
			try:
				from Plugins.Extensions.MediaScanner.plugin import scan
				scan(self.session, self)
				doClose = False
			except:
				self.session.open(MessageBox, _("Sorry, %s has not been installed!") % ("MediaScanner"), MessageBox.TYPE_INFO, timeout=10)
		elif self.args == 4:
			seenMountPoints = []  # DEBUG: Fix Hardisk.py to remove duplicated mount points!
			choices = []
			oldpath = config.plugins.configurationbackup.backuplocation.value
			index = 0
			for partition in harddiskmanager.getMountedPartitions(onlyhotplug=False):
				path = pathjoin(partition.mountpoint, "")
				if path in seenMountPoints:  # TODO: Fix Hardisk.py to remove duplicated mount points!
					continue
				if access(path, F_OK | R_OK | W_OK) and path != "/":
					seenMountPoints.append(path)
					choices.append(("%s (%s)" % (path, partition.description), path))
					if oldpath and oldpath == path:
						index = len(choices) - 1

			def backuplocationCB(path):
				if path:
					oldpath = config.plugins.configurationbackup.backuplocation.value
					config.plugins.configurationbackup.backuplocation.setValue(path)
					config.plugins.configurationbackup.backuplocation.save()
					config.plugins.configurationbackup.save()
					config.save()
					if path != oldpath:
						print("Creating backup folder if not already there...")
						self.backuppath = getBackupPath()
						try:
							if not exists(self.backuppath):
								makedirs(self.backuppath)
						except OSError:
							self.session.open(MessageBox, _("Sorry, your backup destination is not writeable.\nPlease select a different one."), MessageBox.TYPE_INFO, timeout=10)
				self.close()

			if len(choices):
				self.session.openWithCallback(backuplocationCB, MessageBox, _("Please select medium to use as backup location"), list=choices, default=index, windowTitle=_("Backup Location"))
				doClose = False
			else:
				self.session.open(MessageBox, _("No suitable backup locations found!"), MessageBox.TYPE_ERROR, timeout=5)
		elif self.args == 5:
			self.session.open(BackupSelection, title=_("Default files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs_default, readOnly=True, mode="backupfiles")
		elif self.args == 6:
			self.session.open(BackupSelection, title=_("Additional files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs, readOnly=False, mode="backupfiles_addon")
		elif self.args == 7:
			self.session.open(BackupSelection, title=_("Files/folders to exclude from backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs_exclude, readOnly=False, mode="backupfiles_exclude")
		if doClose:
			self.close()

	def startRestore(self, ret=False):
		if (ret == True):
			self.exe = True
			self.session.open(RestoreScreen, runRestore=True)
		self.close()

	def backupDone(self, retval=None):
		message = _("Backup completed.") if retval else _("Backup failed.")
		self.session.open(MessageBox, message, MessageBox.TYPE_INFO, timeout=10)
		self.close()


def Plugins(path, **kwargs):
	return [PluginDescriptor(name=_("Ipkg"), where=PluginDescriptor.WHERE_FILESCAN, needsRestart=False, fnc=filescan)]
