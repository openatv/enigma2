from Plugins.Plugin import PluginDescriptor
from Screens.Console import Console
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.Ipkg import Ipkg
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Input import Input
from Components.Ipkg import IpkgComponent
from Components.Sources.StaticText import StaticText
from Components.ScrollLabel import ScrollLabel
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from Components.Sources.List import List
from Components.Slider import Slider
from Components.Harddisk import harddiskmanager
from Components.config import config,getConfigListEntry, ConfigSubsection, ConfigText, ConfigLocations, ConfigYesNo, ConfigSelection
from Components.ConfigList import ConfigListScreen
from Components.Console import Console
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.SelectionList import SelectionList
from Components.PluginComponent import plugins
from Plugins.Extensions.Infopanel.SoftwarePanel import SoftwarePanel
from Components.PackageInfo import PackageInfoHandler
from Components.Language import language
from Components.AVSwitch import AVSwitch
from Components.Task import job_manager
from Tools.Directories import pathExists, fileExists, resolveFilename, SCOPE_PLUGINS, SCOPE_CURRENT_PLUGIN, SCOPE_ACTIVE_SKIN, SCOPE_METADIR, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap
from Tools.NumericalTextInput import NumericalTextInput
from enigma import eTimer, RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, eListbox, gFont, getDesktop, ePicLoad, eRCInput, getPrevAsciiCode, eEnv, iRecordableService, getEnigmaVersionString
from cPickle import dump, load
from os import path as os_path, system as os_system, unlink, stat, mkdir, popen, makedirs, listdir, access, rename, remove, W_OK, R_OK, F_OK
from time import time, gmtime, strftime, localtime
from stat import ST_MTIME
from datetime import date, timedelta
from twisted.web import client
from twisted.internet import reactor

from ImageBackup import ImageBackup
from Flash_online import FlashOnline
from ImageWizard import ImageWizard
from BackupRestore import BackupSelection, RestoreMenu, BackupScreen, RestoreScreen, getBackupPath, getOldBackupPath, getBackupFilename, RestoreMyMetrixHD
from BackupRestore import InitConfig as BackupRestore_InitConfig
from SoftwareTools import iSoftwareTools
import os
from boxbranding import getBoxType, getMachineBrand, getMachineName, getBrandOEM

boxtype = getBoxType()
brandoem = getBrandOEM()

if os.path.exists("/usr/lib/enigma2/python/Plugins/Extensions/dFlash"):
	from Plugins.Extensions.dFlash.plugin import dFlash
	DFLASH = True
else:
	DFLASH = False

if os.path.exists("/usr/lib/enigma2/python/Plugins/Extensions/dBackup"):
	from Plugins.Extensions.dBackup.plugin import dBackup
	DBACKUP = True
else:
	DBACKUP = False

config.plugins.configurationbackup = BackupRestore_InitConfig()

config.plugins.softwaremanager = ConfigSubsection()
config.plugins.softwaremanager.overwriteSettingsFiles = ConfigYesNo(default=False)
config.plugins.softwaremanager.overwriteDriversFiles = ConfigYesNo(default=True)
config.plugins.softwaremanager.overwriteEmusFiles = ConfigYesNo(default=True)
config.plugins.softwaremanager.overwritePiconsFiles = ConfigYesNo(default=True)
config.plugins.softwaremanager.overwriteBootlogoFiles = ConfigYesNo(default=True)
config.plugins.softwaremanager.overwriteSpinnerFiles = ConfigYesNo(default=True)
config.plugins.softwaremanager.overwriteConfigFiles = ConfigSelection(
				[
				 ("Y", _("Yes, always")),
				 ("N", _("No, never")),
				 ("ask", _("Always ask"))
				], "Y")

config.plugins.softwaremanager.updatetype = ConfigSelection(
				[
					("hot", _("Upgrade with GUI")),
					("cold", _("Unattended upgrade without GUI")),
				], "hot")
config.plugins.softwaremanager.epgcache = ConfigYesNo(default=False)

def write_cache(cache_file, cache_data):
	#Does a cPickle dump
	if not os_path.isdir( os_path.dirname(cache_file) ):
		try:
			mkdir( os_path.dirname(cache_file) )
		except OSError:
			    print os_path.dirname(cache_file), 'is a file'
	fd = open(cache_file, 'w')
	dump(cache_data, fd, -1)
	fd.close()

def valid_cache(cache_file, cache_ttl):
	#See if the cache file exists and is still living
	try:
		mtime = stat(cache_file)[ST_MTIME]
	except:
		return 0
	curr_time = time()
	if (curr_time - mtime) > cache_ttl:
		return 0
	else:
		return 1

def load_cache(cache_file):
	#Does a cPickle load
	fd = open(cache_file)
	cache_data = load(fd)
	fd.close()
	return cache_data

def Check_Softcam():
	found = False
	for x in os.listdir('/etc'):
		if x.find('.emu') > -1:
			found = True
			break;
	return found

class UpdatePluginMenu(Screen):
	skin = """
		<screen name="UpdatePluginMenu" position="center,center" size="610,410" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<ePixmap pixmap="skin_default/border_menu_350.png" position="5,50" zPosition="1" size="350,300" transparent="1" alphatest="on" />
			<widget source="menu" render="Listbox" position="15,60" size="330,290" scrollbarMode="showOnDemand">
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (2, 2), size = (330, 24), flags = RT_HALIGN_LEFT, text = 1), # index 0 is the MenuText,
						],
					"fonts": [gFont("Regular", 22)],
					"itemHeight": 25
					}
				</convert>
			</widget>
			<widget source="menu" render="Listbox" position="360,50" size="240,300" scrollbarMode="showNever" selectionDisabled="1">
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (2, 2), size = (240, 300), flags = RT_HALIGN_CENTER|RT_VALIGN_CENTER|RT_WRAP, text = 2), # index 2 is the Description,
						],
					"fonts": [gFont("Regular", 22)],
					"itemHeight": 300
					}
				</convert>
			</widget>
			<widget source="status" render="Label" position="5,360" zPosition="10" size="600,50" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""

	def __init__(self, session, args = 0):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Software management"))
		self.skin_path = plugin_path
		self.menu = args
		self.list = []
		self.oktext = _("\nPress OK on your remote control to continue.")
		self.menutext = _("Press MENU on your remote control for additional options.")
		self.infotext = _("Press INFO on your remote control for additional information.")
		self.text = ""
		if self.menu == 0:
			print "building menu entries"
			self.list.append(("install-extensions", _("Manage extensions"), _("\nManage extensions or plugins for your %s %s") % (getMachineBrand(), getMachineName()) + self.oktext, None))
			self.list.append(("software-update", _("Software update"), _("\nOnline update of your %s %s software.") % (getMachineBrand(), getMachineName()) + self.oktext, None))
			self.list.append(("software-restore", _("Software restore"), _("\nRestore your %s %s with a new firmware.") % (getMachineBrand(), getMachineName()) + self.oktext, None))
			if not boxtype.startswith('az') and not boxtype.startswith('dm') and not brandoem.startswith('cube'):
				self.list.append(("flash-online", _("Flash Online"), _("\nFlash on the fly your %s %s.") % (getMachineBrand(), getMachineName()) + self.oktext, None))
			if not boxtype.startswith('az') and not brandoem.startswith('cube'):
				self.list.append(("backup-image", _("Backup Image"), _("\nBackup your running %s %s image to HDD or USB.") % (getMachineBrand(), getMachineName()) + self.oktext, None))
			self.list.append(("system-backup", _("Backup system settings"), _("\nBackup your %s %s settings.") % (getMachineBrand(), getMachineName()) + self.oktext + "\n\n" + self.infotext, None))
			self.list.append(("system-restore",_("Restore system settings"), _("\nRestore your %s %s settings.") % (getMachineBrand(), getMachineName()) + self.oktext, None))
			self.list.append(("ipkg-install", _("Install local extension"),  _("\nScan for local extensions and install them.") + self.oktext, None))
			for p in plugins.getPlugins(PluginDescriptor.WHERE_SOFTWAREMANAGER):
				if p.__call__.has_key("SoftwareSupported"):
					callFnc = p.__call__["SoftwareSupported"](None)
					if callFnc is not None:
						if p.__call__.has_key("menuEntryName"):
							menuEntryName = p.__call__["menuEntryName"](None)
						else:
							menuEntryName = _('Extended Software')
						if p.__call__.has_key("menuEntryDescription"):
							menuEntryDescription = p.__call__["menuEntryDescription"](None)
						else:
							menuEntryDescription = _('Extended Software Plugin')
						self.list.append(('default-plugin', menuEntryName, menuEntryDescription + self.oktext, callFnc))
			if config.usage.setup_level.index >= 2: # expert+
				self.list.append(("advanced", _("Advanced options"), _("\nAdvanced options and settings." ) + self.oktext, None))
		elif self.menu == 1:
			self.list.append(("advancedrestore", _("Advanced restore"), _("\nRestore your backups by date." ) + self.oktext, None))
			self.list.append(("backuplocation", _("Select backup location"),  _("\nSelect your backup device.\nCurrent device: " ) + config.plugins.configurationbackup.backuplocation.value + self.oktext, None))
			self.list.append(("backupfiles", _("Show default backup files"),  _("Here you can browse (but not modify) the files that are added to the backupfile by default (E2-setup, channels, network).") + self.oktext + "\n\n" + self.infotext, None))
			self.list.append(("backupfiles_addon", _("Select additional backup files"),  _("Here you can specify additional files that should be added to the backup file.") + self.oktext + "\n\n" + self.infotext, None))
			self.list.append(("backupfiles_exclude", _("Select excluded backup files"),  _("Here you can select which files should be excluded from the backup.") + self.oktext + "\n\n" + self.infotext, None))
			if config.usage.setup_level.index >= 2: # expert+
				self.list.append(("ipkg-manager", _("Packet management"),  _("\nView, install and remove available or installed packages." ) + self.oktext, None))
			self.list.append(("ipkg-source",_("Select upgrade source"), _("\nEdit the upgrade source address." ) + self.oktext, None))
			for p in plugins.getPlugins(PluginDescriptor.WHERE_SOFTWAREMANAGER):
				if p.__call__.has_key("AdvancedSoftwareSupported"):
					callFnc = p.__call__["AdvancedSoftwareSupported"](None)
					if callFnc is not None:
						if p.__call__.has_key("menuEntryName"):
							menuEntryName = p.__call__["menuEntryName"](None)
						else:
							menuEntryName = _('Advanced software')
						if p.__call__.has_key("menuEntryDescription"):
							menuEntryDescription = p.__call__["menuEntryDescription"](None)
						else:
							menuEntryDescription = _('Advanced software plugin')
						self.list.append(('advanced-plugin', menuEntryName, menuEntryDescription + self.oktext, callFnc))

		self["menu"] = List(self.list)
		self["key_red"] = StaticText(_("Close"))
		self["status"] = StaticText(self.menutext)

		self["shortcuts"] = NumberActionMap(["ShortcutActions", "WizardActions", "InfobarEPGActions", "MenuActions", "NumberActions"],
		{
			"ok": self.go,
			"back": self.close,
			"red": self.close,
			"menu": self.handleMenu,
			"info": self.handleInfo,
			"1": self.go,
			"2": self.go,
			"3": self.go,
			"4": self.go,
			"5": self.go,
			"6": self.go,
			"7": self.go,
			"8": self.go,
			"9": self.go,
		}, -1)
		self.onLayoutFinish.append(self.layoutFinished)
		self.backuppath = getBackupPath()
		if not os.path.isdir(self.backuppath):
			self.backuppath = getOldBackupPath()
		self.backupfile = getBackupFilename()
		self.fullbackupfilename = self.backuppath + "/" + self.backupfile
		self.onShown.append(self.setWindowTitle)
		self.onChangedEntry = []
		self["menu"].onSelectionChanged.append(self.selectionChanged)

	def createSummary(self):
		from Screens.PluginBrowser import PluginBrowserSummary
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["menu"].getCurrent()
		if item:
			name = item[1]
			desc = item[2]
		else:
			name = "-"
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def layoutFinished(self):
		idx = 0
		self["menu"].index = idx

	def setWindowTitle(self):
		self.setTitle(_("Software management"))

	def cleanup(self):
		iSoftwareTools.cleanupSoftwareTools()

	def getUpdateInfos(self):
		if iSoftwareTools.NetworkConnectionAvailable is True:
			if iSoftwareTools.available_updates is not 0:
				self.text = _("There are at least %s updates available.") % (str(iSoftwareTools.available_updates))
			else:
				self.text = "" #_("There are no updates available.")
			if iSoftwareTools.list_updating is True:
				self.text += "\n" + _("A search for available updates is currently in progress.")
		else:
			self.text = _("No network connection available.")
		self["status"].setText(self.text)

	def handleMenu(self):
		self.session.open(SoftwareManagerSetup)

	def handleInfo(self):
		current = self["menu"].getCurrent()
		if current:
			currentEntry = current[0]
			if currentEntry in ("system-backup","backupfiles","backupfiles_exclude","backupfiles_addon"):
				self.session.open(SoftwareManagerInfo, mode = "backupinfo", submode = currentEntry)

	def go(self, num = None):
		if num is not None:
			num -= 1
			if not num < self["menu"].count():
				return
			self["menu"].setIndex(num)
		current = self["menu"].getCurrent()
		if current:
			currentEntry = current[0]
			if self.menu == 0:
				if (currentEntry == "software-update"):
					self.session.open(SoftwarePanel, self.skin_path)
				elif (currentEntry == "software-restore"):
					self.session.open(ImageWizard)
				elif (currentEntry == "install-extensions"):
					self.session.open(PluginManager, self.skin_path)
				elif (currentEntry == "flash-online"):
					self.session.open(FlashOnline)
				elif (currentEntry == "backup-image"):
					if DFLASH == True:
						self.session.open(dFlash)
					elif DBACKUP == True:
						self.session.open(dBackup)
					else:
						self.session.open(ImageBackup)
				elif (currentEntry == "system-backup"):
					self.session.openWithCallback(self.backupDone,BackupScreen, runBackup = True)
				elif (currentEntry == "system-restore"):
					if os_path.exists(self.fullbackupfilename):
						self.session.openWithCallback(self.startRestore, MessageBox, _("Are you sure you want to restore the backup?\nYour receiver will restart after the backup has been restored!"), default = False)
					else:
						self.session.open(MessageBox, _("Sorry, no backups found!"), MessageBox.TYPE_INFO, timeout = 10)
				elif (currentEntry == "ipkg-install"):
					try:
						from Plugins.Extensions.MediaScanner.plugin import main
						main(self.session)
					except:
						self.session.open(MessageBox, _("Sorry, %s has not been installed!") % ("MediaScanner"), MessageBox.TYPE_INFO, timeout = 10)
				elif (currentEntry == "default-plugin"):
					self.extended = current[3]
					self.extended(self.session, None)
				elif (currentEntry == "advanced"):
					self.session.open(UpdatePluginMenu, 1)
			elif self.menu == 1:
				if (currentEntry == "ipkg-manager"):
					self.session.open(PacketManager, self.skin_path)
				elif (currentEntry == "backuplocation"):
					parts = [ (r.description, r.mountpoint, self.session) for r in harddiskmanager.getMountedPartitions(onlyhotplug = False)]
					for x in parts:
						if not access(x[1], F_OK|R_OK|W_OK) or x[1] == '/':
							parts.remove(x)
					if len(parts):
						self.session.openWithCallback(self.backuplocation_choosen, ChoiceBox, title = _("Please select medium to use as backup location"), list = parts)
				elif (currentEntry == "backupfiles"):
					self.session.open(BackupSelection,title=_("Default files/folders to backup"),configBackupDirs=config.plugins.configurationbackup.backupdirs_default,readOnly=True)
				elif (currentEntry == "backupfiles_addon"):
					self.session.open(BackupSelection,title=_("Additional files/folders to backup"),configBackupDirs=config.plugins.configurationbackup.backupdirs,readOnly=False)
				elif (currentEntry == "backupfiles_exclude"):
					self.session.open(BackupSelection,title=_("Files/folders to exclude from backup"),configBackupDirs=config.plugins.configurationbackup.backupdirs_exclude,readOnly=False)
				elif (currentEntry == "advancedrestore"):
					self.session.open(RestoreMenu, self.skin_path)
				elif (currentEntry == "ipkg-source"):
					self.session.open(IPKGMenu, self.skin_path)
				elif (currentEntry == "advanced-plugin"):
					self.extended = current[3]
					self.extended(self.session, None)

	def backuplocation_choosen(self, option):
		oldpath = config.plugins.configurationbackup.backuplocation.value
		if option is not None:
			config.plugins.configurationbackup.backuplocation.setValue(str(option[1]))
		config.plugins.configurationbackup.backuplocation.save()
		config.plugins.configurationbackup.save()
		config.save()
		newpath = config.plugins.configurationbackup.backuplocation.value
		if newpath != oldpath:
			self.createBackupfolders()

	def createBackupfolders(self):
		print "Creating backup folder if not already there..."
		self.backuppath = getBackupPath()
		try:
			if (os_path.exists(self.backuppath) == False):
				makedirs(self.backuppath)
		except OSError:
			self.session.open(MessageBox, _("Sorry, your backup destination is not writeable.\nPlease select a different one."), MessageBox.TYPE_INFO, timeout = 10)

	def backupDone(self,retval = None):
		if retval is True:
			self.session.open(MessageBox, _("Backup completed."), MessageBox.TYPE_INFO, timeout = 10)
		else:
			self.session.open(MessageBox, _("Backup failed."), MessageBox.TYPE_INFO, timeout = 10)

	def startRestore(self, ret = False):
		if (ret == True):
			self.exe = True
			self.session.open(RestoreScreen, runRestore = True)

class SoftwareManagerSetup(Screen, ConfigListScreen):

	skin = """
		<screen name="SoftwareManagerSetup" position="center,center" size="560,440" title="SoftwareManager setup">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget name="config" position="5,50" size="550,290" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,300" zPosition="1" size="560,2" />
			<widget source="introduction" render="Label" position="5,310" size="550,80" zPosition="10" font="Regular;21" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
		</screen>"""

	def __init__(self, session, skin_path = None):
		Screen.__init__(self, session)
		self.session = session
		self.skin_path = skin_path
		if self.skin_path == None:
			self.skin_path = resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager")

		self.onChangedEntry = [ ]
		self.setup_title = _("Software manager setup")
		self.overwriteConfigfilesEntry = None
		self.overwriteSettingsfilesEntry = None
		self.overwriteDriversfilesEntry = None
		self.overwriteEmusfilesEntry = None
		self.overwritePiconsfilesEntry = None
		self.overwriteBootlogofilesEntry = None
		self.overwriteSpinnerfilesEntry = None
		self.updatetypeEntry = None

		self.list = [ ]
		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changedEntry)

		self["actions"] = ActionMap(["SetupActions", "MenuActions"],
			{
				"cancel": self.keyCancel,
				"save": self.apply,
				"menu": self.closeRecursive,
			}, -2)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["introduction"] = StaticText()

		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(self.setup_title)

	def createSetup(self):
		self.list = [ ]
		self.overwriteConfigfilesEntry = getConfigListEntry(_("Overwrite configuration files?"), config.plugins.softwaremanager.overwriteConfigFiles)
		self.overwriteSettingsfilesEntry = getConfigListEntry(_("Overwrite Setting Files ?"), config.plugins.softwaremanager.overwriteSettingsFiles)
		self.overwriteDriversfilesEntry = getConfigListEntry(_("Overwrite Driver Files ?"), config.plugins.softwaremanager.overwriteDriversFiles)
		self.overwriteEmusfilesEntry = getConfigListEntry(_("Overwrite Emu Files ?"), config.plugins.softwaremanager.overwriteEmusFiles)
		self.overwritePiconsfilesEntry = getConfigListEntry(_("Overwrite Picon Files ?"), config.plugins.softwaremanager.overwritePiconsFiles)
		self.overwriteBootlogofilesEntry = getConfigListEntry(_("Overwrite Bootlogo Files ?"), config.plugins.softwaremanager.overwriteBootlogoFiles)
		self.overwriteSpinnerfilesEntry = getConfigListEntry(_("Overwrite Spinner Files ?"), config.plugins.softwaremanager.overwriteSpinnerFiles)
		self.updatetypeEntry  = getConfigListEntry(_("Select Software Update"), config.plugins.softwaremanager.updatetype)
		if boxtype.startswith('et'): 
			self.list.append(self.updatetypeEntry)
		self.list.append(self.overwriteConfigfilesEntry)
		self.list.append(self.overwriteSettingsfilesEntry)
		self.list.append(self.overwriteDriversfilesEntry)
		if Check_Softcam():
			self.list.append(self.overwriteEmusfilesEntry)
		self.list.append(self.overwritePiconsfilesEntry)
		self.list.append(self.overwriteBootlogofilesEntry)
		self.list.append(self.overwriteSpinnerfilesEntry)
		self["config"].list = self.list
		self["config"].l.setSeperation(400)
		self["config"].l.setList(self.list)
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		if self["config"].getCurrent() == self.overwriteConfigfilesEntry:
			self["introduction"].setText(_("Overwrite configuration files during software upgrade?"))
		elif self["config"].getCurrent() == self.overwriteSettingsfilesEntry:
			self["introduction"].setText(_("Overwrite setting files (channellist) during software upgrade?"))
		elif self["config"].getCurrent() == self.overwriteDriversfilesEntry:
			self["introduction"].setText(_("Overwrite driver files during software upgrade?"))
		elif self["config"].getCurrent() == self.overwriteEmusfilesEntry:
			self["introduction"].setText(_("Overwrite softcam files during software upgrade?"))
		elif self["config"].getCurrent() == self.overwritePiconsfilesEntry:
			self["introduction"].setText(_("Overwrite picon files during software upgrade?"))
		elif self["config"].getCurrent() == self.overwriteBootlogofilesEntry:
			self["introduction"].setText(_("Overwrite bootlogo files during software upgrade?"))
		elif self["config"].getCurrent() == self.overwriteSpinnerfilesEntry:
			self["introduction"].setText(_("Overwrite spinner files during software upgrade?"))
		elif self["config"].getCurrent() == self.updatetypeEntry:
			self["introduction"].setText(_("Select how your box will upgrade."))
		else:
			self["introduction"].setText("")

	def newConfig(self):
		pass

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		ConfigListScreen.keyRight(self)

	def confirm(self, confirmed):
		if not confirmed:
			print "not confirmed"
			return
		else:
			self.keySave()

	def apply(self):
		self.session.openWithCallback(self.confirm, MessageBox, _("Use these settings?"), MessageBox.TYPE_YESNO, timeout = 20, default = True)

	def cancelConfirm(self, result):
		if not result:
			return
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), MessageBox.TYPE_YESNO, timeout = 20, default = False)
		else:
			self.close()

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
		self.selectionChanged()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].value)

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary


class SoftwareManagerInfo(Screen):
	skin = """
		<screen name="SoftwareManagerInfo" position="center,center" size="560,440" title="SoftwareManager information">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget source="list" render="Listbox" position="5,50" size="550,340" scrollbarMode="showOnDemand" selectionDisabled="0">
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (5, 0), size = (540, 26), font=0, flags = RT_HALIGN_LEFT | RT_HALIGN_CENTER, text = 0), # index 0 is the name
						],
					"fonts": [gFont("Regular", 24),gFont("Regular", 22)],
					"itemHeight": 26
					}
				</convert>
			</widget>
			<ePixmap pixmap="skin_default/div-h.png" position="0,400" zPosition="1" size="560,2" />
			<widget source="introduction" render="Label" position="5,410" size="550,30" zPosition="10" font="Regular;21" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
		</screen>"""

	def __init__(self, session, skin_path = None, mode = None, submode = None):
		Screen.__init__(self, session)
		self.session = session
		self.mode = mode
		self.submode = submode
		self.skin_path = skin_path
		if self.skin_path == None:
			self.skin_path = resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager")

		self["actions"] = ActionMap(["ShortcutActions", "WizardActions"],
			{
				"back": self.close,
				"red": self.close,
			}, -2)

		self.list = []
		self["list"] = List(self.list)

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["introduction"] = StaticText()

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("Softwaremanager information"))
		if self.mode is not None:
			self.showInfos()

	def showInfos(self):
		if self.mode == "backupinfo":
			self.list = []
			if self.submode == "backupfiles_exclude":
				backupfiles = config.plugins.configurationbackup.backupdirs_exclude.value
			elif self.submode == "backupfiles_addon":
				backupfiles = config.plugins.configurationbackup.backupdirs.value
			else:
				backupfiles = config.plugins.configurationbackup.backupdirs_default.value
			for entry in backupfiles:
				self.list.append((entry,))
			self['list'].setList(self.list)


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

	def __init__(self, session, plugin_path = None, args = None):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Extensions management"))
		self.session = session
		self.skin_path = plugin_path
		if self.skin_path == None:
			self.skin_path = resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager")

		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions", "InfobarEPGActions", "HelpActions" ],
		{
			"ok": self.handleCurrent,
			"back": self.exit,
			"red": self.exit,
			"green": self.handleCurrent,
			"yellow": self.handleSelected,
			"showEventInfo": self.handleSelected,
			"displayHelp": self.handleHelp,
		}, -1)

		self.list = []
		self.statuslist = []
		self.selectedFiles = []
		self.categoryList = []
		self.packetlist = []
		self["list"] = List(self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["status"] = StaticText("")

		self.cmdList = []
		self.oktext = _("\nAfter pressing OK, please wait!")
		if not self.selectionChanged in self["list"].onSelectionChanged:
			self["list"].onSelectionChanged.append(self.selectionChanged)

		self.currList = ""
		self.currentSelectedTag = None
		self.currentSelectedIndex = None
		self.currentSelectedPackage = None
		self.saved_currentSelectedPackage = None
		self.restartRequired = False

		self.onShown.append(self.setWindowTitle)
		self.onLayoutFinish.append(self.getUpdateInfos)

	def setWindowTitle(self):
		self.setTitle(_("Extensions management"))

	def exit(self):
		if self.currList == "packages":
			self.currList = "category"
			self.currentSelectedTag = None
			self["list"].style = "category"
			self['list'].setList(self.categoryList)
			self["list"].setIndex(self.currentSelectedIndex)
			self["list"].updateList(self.categoryList)
			self.selectionChanged()
		else:
			iSoftwareTools.cleanupSoftwareTools()
			self.prepareInstall()
			if len(self.cmdList):
				self.session.openWithCallback(self.runExecute, PluginManagerInfo, self.skin_path, self.cmdList)
			else:
				self.close()

	def handleHelp(self):
		if self.currList != "status":
			self.session.open(PluginManagerHelp, self.skin_path)

	def setState(self,status = None):
		if status:
			self.currList = "status"
			self.statuslist = []
			self["key_green"].setText("")
			self["key_blue"].setText("")
			self["key_yellow"].setText("")
			divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, "div-h.png"))
			if status == 'update':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/upgrade.png"))
				self.statuslist.append(( _("Updating software catalog"), '', _("Searching for available updates. Please wait..." ),'', '', statuspng, divpng, None, '' ))
			elif status == 'sync':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/upgrade.png"))
				self.statuslist.append(( _("Package list update"), '', _("Searching for new installed or removed packages. Please wait..." ),'', '', statuspng, divpng, None, '' ))
			elif status == 'error':
				self["key_green"].setText(_("Continue"))
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/remove.png"))
				self.statuslist.append(( _("Error"), '', _("An error occurred while downloading the packetlist. Please try again." ),'', '', statuspng, divpng, None, '' ))
			self["list"].style = "default"
			self['list'].setList(self.statuslist)


	def getUpdateInfos(self):
		if (iSoftwareTools.lastDownloadDate is not None and iSoftwareTools.NetworkConnectionAvailable is False):
			self.rebuildList()
		else:
			self.setState('update')
			iSoftwareTools.startSoftwareTools(self.getUpdateInfosCB)

	def getUpdateInfosCB(self, retval = None):
		if retval is not None:
			if retval is True:
				if iSoftwareTools.available_updates is not 0:
					self["status"].setText(_("There are at least ") + str(iSoftwareTools.available_updates) + ' ' + _("updates available."))
				else:
					self["status"].setText(_("There are no updates available."))
				self.rebuildList()
			elif retval is False:
				if iSoftwareTools.lastDownloadDate is None:
					self.setState('error')
					if iSoftwareTools.NetworkConnectionAvailable:
						self["status"].setText(_("Updatefeed not available."))
					else:
						self["status"].setText(_("No network connection available."))
				else:
					iSoftwareTools.lastDownloadDate = time()
					iSoftwareTools.list_updating = True
					self.setState('update')
					iSoftwareTools.getUpdates(self.getUpdateInfosCB)

	def rebuildList(self, retval = None):
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
				if current[4] == 'installed':
					self["key_green"].setText(_("Uninstall"))
				elif current[4] == 'installable':
					self["key_green"].setText(_("Install"))
					if iSoftwareTools.NetworkConnectionAvailable is False:
						self["key_green"].setText("")
				elif current[4] == 'remove':
					self["key_green"].setText(_("Undo uninstall"))
				elif current[4] == 'install':
					self["key_green"].setText(_("Undo install"))
					if iSoftwareTools.NetworkConnectionAvailable is False:
						self["key_green"].setText("")
				self["key_yellow"].setText(_("View details"))
				self["key_blue"].setText("")
				if len(self.selectedFiles) == 0 and iSoftwareTools.available_updates is not 0:
					self["status"].setText(_("There are at least ") + str(iSoftwareTools.available_updates) + ' ' + _("updates available."))
				elif len(self.selectedFiles) is not 0:
					self["status"].setText(str(len(self.selectedFiles)) + ' ' + _("packages selected."))
				else:
					self["status"].setText(_("There are currently no outstanding actions."))
			elif self.currList == "category":
				self["key_red"].setText(_("Close"))
				self["key_green"].setText("")
				self["key_yellow"].setText("")
				self["key_blue"].setText("")
				if len(self.selectedFiles) == 0 and iSoftwareTools.available_updates is not 0:
					self["status"].setText(_("There are at least ") + str(iSoftwareTools.available_updates) + ' ' + _("updates available."))
					self["key_yellow"].setText(_("Update"))
				elif len(self.selectedFiles) is not 0:
					self["status"].setText(str(len(self.selectedFiles)) + ' ' + _("packages selected."))
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
				if current[7] is not '':
					idx = self["list"].getIndex()
					detailsFile = self.list[idx][1]
					if self.list[idx][7] == True:
						for entry in self.selectedFiles:
							if entry[0] == detailsFile:
								self.selectedFiles.remove(entry)
					else:
						alreadyinList = False
						for entry in self.selectedFiles:
							if entry[0] == detailsFile:
								alreadyinList = True
						if not alreadyinList:
							if (iSoftwareTools.NetworkConnectionAvailable is False and current[4] in ('installable','install')):
								pass
							else:
								self.selectedFiles.append((detailsFile,current[4],current[3]))
								self.currentSelectedPackage = ((detailsFile,current[4],current[3]))
					if current[4] == 'installed':
						self.list[idx] = self.buildEntryComponent(current[0], current[1], current[2], current[3], 'remove', True)
					elif current[4] == 'installable':
						if iSoftwareTools.NetworkConnectionAvailable:
							self.list[idx] = self.buildEntryComponent(current[0], current[1], current[2], current[3], 'install', True)
					elif current[4] == 'remove':
						self.list[idx] = self.buildEntryComponent(current[0], current[1], current[2], current[3], 'installed', False)
					elif current[4] == 'install':
						if iSoftwareTools.NetworkConnectionAvailable:
							self.list[idx] = self.buildEntryComponent(current[0], current[1], current[2], current[3], 'installable',False)
					self["list"].setList(self.list)
					self["list"].setIndex(idx)
					self["list"].updateList(self.list)
					self.selectionChanged()
			elif self.currList == "status":
				iSoftwareTools.lastDownloadDate = time()
				iSoftwareTools.list_updating = True
				self.setState('update')
				iSoftwareTools.getUpdates(self.getUpdateInfosCB)

	def handleSelected(self):
		current = self["list"].getCurrent()
		if current:
			if self.currList == "packages":
				if current[7] is not '':
					detailsfile = iSoftwareTools.directory[0] + "/" + current[1]
					if (os_path.exists(detailsfile) == True):
						self.saved_currentSelectedPackage = self.currentSelectedPackage
						self.session.openWithCallback(self.detailsClosed, PluginDetails, self.skin_path, current)
					else:
						self.session.open(MessageBox, _("Sorry, no details available!"), MessageBox.TYPE_INFO, timeout = 10)
			elif self.currList == "category":
				self.prepareInstall()
				if len(self.cmdList):
					self.session.openWithCallback(self.runExecute, PluginManagerInfo, self.skin_path, self.cmdList)

	def detailsClosed(self, result = None):
		if result is not None:
			if result is not False:
				self.setState('sync')
				iSoftwareTools.lastDownloadDate = time()
				for entry in self.selectedFiles:
					if entry == self.saved_currentSelectedPackage:
						self.selectedFiles.remove(entry)
				iSoftwareTools.startIpkgListInstalled(self.rebuildList)

	def buildEntryComponent(self, name, details, description, packagename, state, selected = False):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, "div-h.png"))
		installedpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/installed.png"))
		installablepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/installable.png"))
		removepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/remove.png"))
		installpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/install.png"))
		if state == 'installed':
			return((name, details, description, packagename, state, installedpng, divpng, selected))
		elif state == 'installable':
			return((name, details, description, packagename, state, installablepng, divpng, selected))
		elif state == 'remove':
			return((name, details, description, packagename, state, removepng, divpng, selected))
		elif state == 'install':
			return((name, details, description, packagename, state, installpng, divpng, selected))

	def buildPacketList(self, categorytag = None):
		if categorytag is not None:
			self.currList = "packages"
			self.currentSelectedTag = categorytag
			self.packetlist = []
			for package in iSoftwareTools.packagesIndexlist[:]:
				prerequisites = package[0]["prerequisites"]
				if prerequisites.has_key("tag"):
					for foundtag in prerequisites["tag"]:
						if categorytag == foundtag:
							attributes = package[0]["attributes"]
							if attributes.has_key("packagetype"):
								if attributes["packagetype"] == "internal":
									continue
								self.packetlist.append([attributes["name"], attributes["details"], attributes["shortdescription"], attributes["packagename"]])
							else:
								self.packetlist.append([attributes["name"], attributes["details"], attributes["shortdescription"], attributes["packagename"]])
			self.list = []
			for x in self.packetlist:
				status = ""
				name = x[0].strip()
				details = x[1].strip()
				description = x[2].strip()
				if not description:
					description = "No description available."
				packagename = x[3].strip()
				selectState = self.getSelectionState(details)
				if iSoftwareTools.installed_packetlist.has_key(packagename):
					if selectState == True:
						status = "remove"
					else:
						status = "installed"
					self.list.append(self.buildEntryComponent(name, _(details), _(description), packagename, status, selected = selectState))
				else:
					if selectState == True:
						status = "install"
					else:
						status = "installable"
					self.list.append(self.buildEntryComponent(name, _(details), _(description), packagename, status, selected = selectState))
			if len(self.list):
				self.list.sort(key=lambda x: x[0])
			self["list"].style = "default"
			self['list'].setList(self.list)
			self["list"].updateList(self.list)
			self.selectionChanged()

	def buildCategoryList(self):
		self.currList = "category"
		self.categories = []
		self.categoryList = []
		for package in iSoftwareTools.packagesIndexlist[:]:
			prerequisites = package[0]["prerequisites"]
			if prerequisites.has_key("tag"):
				for foundtag in prerequisites["tag"]:
					attributes = package[0]["attributes"]
					if foundtag not in self.categories:
						self.categories.append(foundtag)
						self.categoryList.append(self.buildCategoryComponent(foundtag))
		self.categoryList.sort(key=lambda x: x[0])
		self["list"].style = "category"
		self['list'].setList(self.categoryList)
		self["list"].updateList(self.categoryList)
		self.selectionChanged()

	def buildCategoryComponent(self, tag = None):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, "div-h.png"))
		if tag is not None:
			if tag == 'System':
				return(( _("System"), _("View list of available system extensions" ), tag, divpng ))
			elif tag == 'Skin':
				return(( _("Skins"), _("View list of available skins" ), tag, divpng ))
			elif tag == 'Recording':
				return(( _("Recordings"), _("View list of available recording extensions" ), tag, divpng ))
			elif tag == 'Network':
				return(( _("Network"), _("View list of available networking extensions" ), tag, divpng ))
			elif tag == 'CI':
				return(( _("Common Interface"), _("View list of available CommonInterface extensions" ), tag, divpng ))
			elif tag == 'Default':
				return(( _("Default settings"), _("View list of available default settings" ), tag, divpng ))
			elif tag == 'SAT':
				return(( _("Satellite equipment"), _("View list of available Satellite equipment extensions." ), tag, divpng ))
			elif tag == 'Software':
				return(( _("Software"), _("View list of available software extensions" ), tag, divpng ))
			elif tag == 'Multimedia':
				return(( _("Multimedia"), _("View list of available multimedia extensions." ), tag, divpng ))
			elif tag == 'Display':
				return(( _("Display and user interface"), _("View list of available display and userinterface extensions." ), tag, divpng ))
			elif tag == 'EPG':
				return(( _("Electronic Program Guide"), _("View list of available EPG extensions." ), tag, divpng ))
			elif tag == 'Communication':
				return(( _("Communication"), _("View list of available communication extensions." ), tag, divpng ))
			else: # dynamically generate non existent tags
				return(( str(tag), _("View list of available ") + str(tag) + ' ' + _("extensions." ), tag, divpng ))

	def prepareInstall(self):
		self.cmdList = []
		if iSoftwareTools.available_updates > 0:
			self.cmdList.append((IpkgComponent.CMD_UPGRADE, { "test_only": False }))
		if self.selectedFiles and len(self.selectedFiles):
			for plugin in self.selectedFiles:
				detailsfile = iSoftwareTools.directory[0] + "/" + plugin[0]
				if (os_path.exists(detailsfile) == True):
					iSoftwareTools.fillPackageDetails(plugin[0])
					self.package = iSoftwareTools.packageDetails[0]
					if self.package[0].has_key("attributes"):
						self.attributes = self.package[0]["attributes"]
						if self.attributes.has_key("needsRestart"):
							self.restartRequired = True
					if self.attributes.has_key("package"):
						self.packagefiles = self.attributes["package"]
					if plugin[1] == 'installed':
						if self.packagefiles:
							for package in self.packagefiles[:]:
								self.cmdList.append((IpkgComponent.CMD_REMOVE, { "package": package["name"] }))
						else:
							self.cmdList.append((IpkgComponent.CMD_REMOVE, { "package": plugin[2] }))
					else:
						if self.packagefiles:
							for package in self.packagefiles[:]:
								self.cmdList.append((IpkgComponent.CMD_INSTALL, { "package": package["name"] }))
						else:
							self.cmdList.append((IpkgComponent.CMD_INSTALL, { "package": plugin[2] }))
				else:
					if plugin[1] == 'installed':
						self.cmdList.append((IpkgComponent.CMD_REMOVE, { "package": plugin[2] }))
					else:
						self.cmdList.append((IpkgComponent.CMD_INSTALL, { "package": plugin[2] }))

	def runExecute(self, result = None):
		if result is not None:
			if result[0] is True:
				self.session.openWithCallback(self.runExecuteFinished, Ipkg, cmdList = self.cmdList)
			elif result[0] is False:
				self.cmdList = result[1]
				self.session.openWithCallback(self.runExecuteFinished, Ipkg, cmdList = self.cmdList)
		else:
			self.close()

	def runExecuteFinished(self):
		self.reloadPluginlist()
		if plugins.restartRequired or self.restartRequired:
			self.session.openWithCallback(self.ExecuteReboot, MessageBox, _("Install or remove finished.") +" "+_("Do you want to reboot your receiver?"), MessageBox.TYPE_YESNO)
		else:
			self.selectedFiles = []
			self.restartRequired = False
			self.detailsClosed(True)

	def ExecuteReboot(self, result):
		if result:
			self.session.open(TryQuitMainloop,retvalue=3)
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

	def __init__(self, session, plugin_path, cmdlist = None):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Plugin manager activity information"))
		self.session = session
		self.skin_path = plugin_path
		self.cmdlist = cmdlist

		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"ok": self.process_all,
			"back": self.exit,
			"red": self.exit,
			"green": self.process_extensions,
		}, -1)

		self.list = []
		self["list"] = List(self.list)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Only extensions."))
		self["status"] = StaticText(_("Following tasks will be done after you press OK!"))

		self.onShown.append(self.setWindowTitle)
		self.onLayoutFinish.append(self.rebuildList)

	def setWindowTitle(self):
		self.setTitle(_("Plugin manager activity information"))

	def rebuildList(self):
		self.list = []
		if self.cmdlist is not None:
			for entry in self.cmdlist:
				action = ""
				info = ""
				cmd = entry[0]
				if cmd == 0:
					action = 'install'
				elif cmd == 2:
					action = 'remove'
				else:
					action = 'upgrade'
				args = entry[1]
				if cmd == 0:
					info = args['package']
				elif cmd == 2:
					info = args['package']
				else:
					info = _("%s %s software because updates are available.") % (getMachineBrand(), getMachineName())

				self.list.append(self.buildEntryComponent(action,info))
			self['list'].setList(self.list)
			self['list'].updateList(self.list)

	def buildEntryComponent(self, action,info):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, "div-h.png"))
		upgradepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/upgrade.png"))
		installpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/install.png"))
		removepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/remove.png"))
		if action == 'install':
			return(( _('Installing'), info, installpng, divpng))
		elif action == 'remove':
			return(( _('Removing'), info, removepng, divpng))
		else:
			return(( _('Upgrading'), info, upgradepng, divpng))

	def exit(self):
		self.close()

	def process_all(self):
		self.close((True,None))

	def process_extensions(self):
		self.list = []
		if self.cmdlist is not None:
			for entry in self.cmdlist:
				cmd = entry[0]
				if entry[0] in (0,2):
					self.list.append((entry))
		self.close((False,self.list))


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

	def __init__(self, session, plugin_path):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Plugin manager help"))
		self.session = session
		self.skin_path = plugin_path

		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"back": self.exit,
			"red": self.exit,
		}, -1)

		self.list = []
		self["list"] = List(self.list)
		self["key_red"] = StaticText(_("Close"))
		self["status"] = StaticText(_("A small overview of the available icon states and actions."))

		self.onShown.append(self.setWindowTitle)
		self.onLayoutFinish.append(self.rebuildList)

	def setWindowTitle(self):
		self.setTitle(_("Plugin manager help"))

	def rebuildList(self):
		self.list = []
		self.list.append(self.buildEntryComponent('install'))
		self.list.append(self.buildEntryComponent('installable'))
		self.list.append(self.buildEntryComponent('installed'))
		self.list.append(self.buildEntryComponent('remove'))
		self['list'].setList(self.list)
		self['list'].updateList(self.list)

	def buildEntryComponent(self, state):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, "div-h.png"))
		installedpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/installed.png"))
		installablepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/installable.png"))
		removepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/remove.png"))
		installpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/install.png"))

		if state == 'installed':
			return(( _('This plugin is installed.'), _('You can remove this plugin.'), installedpng, divpng))
		elif state == 'installable':
			return(( _('This plugin is not installed.'), _('You can install this plugin.'), installablepng, divpng))
		elif state == 'install':
			return(( _('This plugin will be installed.'), _('You can cancel the installation.'), installpng, divpng))
		elif state == 'remove':
			return(( _('This plugin will be removed.'), _('You can cancel the removal.'), removepng, divpng))

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
	def __init__(self, session, plugin_path, packagedata = None):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Plugin details"))
		self.skin_path = plugin_path
		self.language = language.getLanguage()[:2] # getLanguage returns e.g. "fi_FI" for "language_country"
		self.attributes = None
		PackageInfoHandler.__init__(self, self.statusCallback, blocking = False)
		self.directory = resolveFilename(SCOPE_METADIR)
		if packagedata:
			self.pluginname = packagedata[0]
			self.details = packagedata[1]
			self.pluginstate = packagedata[4]
			self.statuspicinstance = packagedata[5]
			self.divpicinstance = packagedata[6]
			self.fillPackageDetails(self.details)

		self.thumbnail = ""

		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"back": self.exit,
			"red": self.exit,
			"green": self.go,
			"up": self.pageUp,
			"down":	self.pageDown,
			"left":	self.pageUp,
			"right": self.pageDown,
		}, -1)

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
		if self.package[0].has_key("attributes"):
			self.attributes = self.package[0]["attributes"]
		self.restartRequired = False
		self.cmdList = []
		self.oktext = _("\nAfter pressing OK, please wait!")
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.paintScreenshotPixmapCB)
		self.onShown.append(self.setWindowTitle)
		self.onLayoutFinish.append(self.setInfos)

	def setWindowTitle(self):
		self.setTitle(_("Details for plugin: ") + self.pluginname )

	def exit(self):
		self.close(False)

	def pageUp(self):
		self["detailtext"].pageUp()

	def pageDown(self):
		self["detailtext"].pageDown()

	def statusCallback(self, status, progress):
		pass

	def setInfos(self):
		if self.attributes.has_key("screenshot"):
			self.loadThumbnail(self.attributes)

		if self.attributes.has_key("name"):
			self.pluginname = self.attributes["name"]
		else:
			self.pluginname = _("unknown")

		if self.attributes.has_key("author"):
			self.author = self.attributes["author"]
		else:
			self.author = _("unknown")

		if self.attributes.has_key("description"):
			self.description = _(self.attributes["description"].replace("\\n", "\n"))
		else:
			self.description = _("No description available.")

		self["author"].setText(_("Author: ") + self.author)
		self["detailtext"].setText(_(self.description))
		if self.pluginstate in ('installable', 'install'):
			if iSoftwareTools.NetworkConnectionAvailable:
				self["key_green"].setText(_("Install"))
			else:
				self["key_green"].setText("")
		else:
			self["key_green"].setText(_("Remove"))

	def loadThumbnail(self, entry):
		thumbnailUrl = None
		if entry.has_key("screenshot"):
			thumbnailUrl = entry["screenshot"]
			if self.language == "de":
				if thumbnailUrl[-7:] == "_en.jpg":
					thumbnailUrl = thumbnailUrl[:-7] + "_de.jpg"

		if thumbnailUrl is not None:
			self.thumbnail = "/tmp/" + thumbnailUrl.split('/')[-1]
			print "[PluginDetails] downloading screenshot " + thumbnailUrl + " to " + self.thumbnail
			if iSoftwareTools.NetworkConnectionAvailable:
				client.downloadPage(thumbnailUrl,self.thumbnail).addCallback(self.setThumbnail).addErrback(self.fetchFailed)
			else:
				self.setThumbnail(noScreenshot = True)
		else:
			self.setThumbnail(noScreenshot = True)

	def setThumbnail(self, noScreenshot = False):
		if not noScreenshot:
			filename = self.thumbnail
		else:
			filename = resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/noprev.png")

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
			self.setThumbnail(noScreenshot = True)

	def go(self):
		if self.attributes.has_key("package"):
			self.packagefiles = self.attributes["package"]
		if self.attributes.has_key("needsRestart"):
			self.restartRequired = True
		self.cmdList = []
		if self.pluginstate in ('installed', 'remove'):
			if self.packagefiles:
				for package in self.packagefiles[:]:
					self.cmdList.append((IpkgComponent.CMD_REMOVE, { "package": package["name"] }))
					if len(self.cmdList):
						self.session.openWithCallback(self.runRemove, MessageBox, _("Do you want to remove the package:\n") + self.pluginname + "\n" + self.oktext)
		else:
			if iSoftwareTools.NetworkConnectionAvailable:
				if self.packagefiles:
					for package in self.packagefiles[:]:
						self.cmdList.append((IpkgComponent.CMD_INSTALL, { "package": package["name"] }))
						if len(self.cmdList):
							self.session.openWithCallback(self.runUpgrade, MessageBox, _("Do you want to install the package:\n") + self.pluginname + "\n" + self.oktext)

	def runUpgrade(self, result):
		if result:
			self.session.openWithCallback(self.runUpgradeFinished, Ipkg, cmdList = self.cmdList)

	def runUpgradeFinished(self):
		self.reloadPluginlist()
		if plugins.restartRequired or self.restartRequired:
			self.session.openWithCallback(self.UpgradeReboot, MessageBox, _("Installation finished.") +" "+_("Do you want to reboot your receiver?"), MessageBox.TYPE_YESNO)
		else:
			self.close(True)
	def UpgradeReboot(self, result):
		if result:
			self.session.open(TryQuitMainloop,retvalue=3)
		self.close(True)

	def runRemove(self, result):
		if result:
			self.session.openWithCallback(self.runRemoveFinished, Ipkg, cmdList = self.cmdList)

	def runRemoveFinished(self):
		self.close(True)

	def reloadPluginlist(self):
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))

	def fetchFailed(self,string):
		self.setThumbnail(noScreenshot = True)
		print "[PluginDetails] fetch failed " + string.getErrorMessage()


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
		Screen.setTitle(self, _("Software update"))
		
		self.sliderPackages = { "dreambox-dvb-modules": 1, "enigma2": 2, "tuxbox-image-info": 3 }

		self.slider = Slider(0, 4)
		self["slider"] = self.slider
		self.activityslider = Slider(0, 100)
		self["activityslider"] = self.activityslider
		self.status = StaticText(_("Please wait..."))
		self["status"] = self.status
		self.package = StaticText(_("Package list update"))
		self["package"] = self.package
		self.oktext = _("Press OK on your remote control to continue.")

		self.packages = 0
		self.error = 0
		self.processed_packages = []
		self.total_packages = None
		self.skin_path = plugin_path
		self.TraficCheck = False
		self.TraficResult = False
		self.CheckDateDone = False

		self.activity = 0
		self.activityTimer = eTimer()
		self.activityTimer.callback.append(self.doActivityTimer)

		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)

		self.updating = False

		self["actions"] = ActionMap(["WizardActions"],
		{
			"ok": self.exit,
			"back": self.exit
		}, -1)

		self.activityTimer.start(100, False)

	def CheckDate(self):
		# Check if image is not to old for update (max 30days)
		self.CheckDateDone = True
		tmpdate = getEnigmaVersionString()
		imageDate = date(int(tmpdate[0:4]), int(tmpdate[5:7]), int(tmpdate[8:10]))
		datedelay = imageDate +  timedelta(days=30)
		message = _("Your image is out of date!\n\n"
				"After such a long time, there is a risk that your %s %s will not\n"
				"boot after online-update, or will show disfunction in running Image.\n\n"
				"A new flash will increase the stability\n\n"
				"An online update is done at your own risk !!\n\n\n"
				"Do you still want to update?") % (getMachineBrand(), getMachineName())

		if datedelay > date.today():
			self.updating = True
			self.activityTimer.start(100, False)
			self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE_LIST)
		else:
			print"[SOFTWAREMANAGER] Your image is to old (%s), you need to flash new !!" %getEnigmaVersionString()
			self.session.openWithCallback(self.checkDateCallback, MessageBox, message, default = False)
			return

	def checkDateCallback(self, ret):
		print ret
		if ret:
			self.activityTimer.start(100, False)
			self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE_LIST)
		else:
			self.close()
			return

	def checkTraficLight(self):
		from urllib import urlopen
		import socket
		currentTimeoutDefault = socket.getdefaulttimeout()
		socket.setdefaulttimeout(3)
		message = ""
		picon = None
		default = True
		doUpdate = True
		# TODO: Use Twisted's URL fetcher, urlopen is evil. And it can
		# run in parallel to the package update.
		try:
			urlopenATV = "http://ampel.mynonpublic.com/Ampel/index.php"
			d = urlopen(urlopenATV)
			tmpStatus = d.read()
			if (os.path.exists("/etc/.beta") and 'rot.png' in tmpStatus) or 'gelb.png' in tmpStatus:
				message = _("Caution update not yet tested !!") + "\n" + _("Update at your own risk") + "\n\n" + _("For more information see http://www.opena.tv") + "\n\n"# + _("Last Status Date") + ": "  + statusDate + "\n\n"
				picon = MessageBox.TYPE_ERROR
				default = False
			elif 'rot.png' in tmpStatus:
				message = _("Update is reported as faulty !!") + "\n" + _("Aborting updateprogress") + "\n\n" + _("For more information see http://www.opena.tv")# + "\n\n" + _("Last Status Date") + ": " + statusDate
				picon = MessageBox.TYPE_ERROR
				default = False
				doUpdate = False
		except:
			message = _("The status of the current update could not be checked because http://www.opena.tv could not be reached for some reason") + "\n"
			picon = MessageBox.TYPE_ERROR
			default = False
		socket.setdefaulttimeout(currentTimeoutDefault)

		if default:
		        # We'll ask later
		        self.runUpgrade(True)
		else:
			if doUpdate:
				# Ask for Update, 
				message += _("Do you want to update your box?")+"\n"+_("After pressing OK, please wait!")
				self.session.openWithCallback(self.runUpgrade, MessageBox, message, default = default, picon = picon)
			else:
				# Don't Update RED LIGHT !!
				self.session.open(MessageBox, message, picon, timeout = 20)
				self.runUpgrade(False)

	def runUpgrade(self, result):
		self.TraficResult = result
		if result:
			self.TraficCheck = True
			self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE_LIST)
		else:
			self.TraficCheck = False
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

	def ipkgCallback(self, event, param):
		if event == IpkgComponent.EVENT_DOWNLOAD:
			self.status.setText(_("Downloading"))
		elif event == IpkgComponent.EVENT_UPGRADE:
			if self.sliderPackages.has_key(param):
				self.slider.setValue(self.sliderPackages[param])
			self.package.setText(param)
			self.status.setText(_("Upgrading") + ": %s/%s" % (self.packages, self.total_packages))
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

		elif event == IpkgComponent.EVENT_MODIFIED:
			if config.plugins.softwaremanager.overwriteConfigFiles.value in ("N", "Y"):
				self.ipkg.write(True and config.plugins.softwaremanager.overwriteConfigFiles.value)
			else:
				self.session.openWithCallback(
					self.modificationCallback,
					MessageBox,
					_("A configuration file (%s) was modified since Installation.\nDo you want to keep your version?") % (param)
				)
		elif event == IpkgComponent.EVENT_ERROR:
			self.error += 1
		elif event == IpkgComponent.EVENT_DONE:
			if self.updating:
				self.updating = False
				self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE_LIST)
			elif self.ipkg.currentCommand == IpkgComponent.CMD_UPGRADE_LIST:
				self.total_packages = len(self.ipkg.getFetchedList())
				if self.total_packages and not self.TraficCheck:
					self.checkTraficLight()
					return
				if self.total_packages and self.TraficCheck and self.TraficResult:
					#message = _("Do you want to update your %s %s?") % (getMachineBrand(), getMachineName()) + "                 \n(%s " % self.total_packages + _("Packages") + ")"
					try:
						if config.plugins.softwaremanager.updatetype.value == "cold":
							self.startActualUpgrade("cold")
						#	choices = [(_("Show new Packages"), "show"), (_("Unattended upgrade without GUI and reboot system"), "cold"), (_("Cancel"), "")]
						else:
							self.startActualUpgrade("hot")
					except:
						self.startActualUpgrade("hot")
					#	choices = [(_("Show new Packages"), "show"), (_("Upgrade and ask to reboot"), "hot"), (_("Cancel"), "")]
					#self.session.openWithCallback(self.startActualUpgrade, ChoiceBox, title=message, list=choices)
				else:
					self.session.openWithCallback(self.close, MessageBox, _("Nothing to upgrade"), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
			elif self.error == 0:
				self.slider.setValue(4)
				self.activityTimer.stop()
				self.activityslider.setValue(0)
				self.package.setText(_("Done - Installed or upgraded %d packages") % self.packages)
				self.status.setText(self.oktext)
			else:
				self.activityTimer.stop()
				self.activityslider.setValue(0)
				error = _("your %s %s might be unusable now. Please consult the manual for further assistance before rebooting your %s %s.") % (getMachineBrand(), getMachineName())
				if self.packages == 0:
					error = _("No packages were upgraded yet. So you can check your network and try again.")
				if self.updating:
					error = _("Your %s %s isn't connected to the internet properly. Please check it and try again.") % (getMachineBrand(), getMachineName())
				self.status.setText(_("Error") +  " - " + error)
		#print event, "-", param
		pass

	def startActualUpgrade(self, answer):
		if not answer or not answer[1]:
			self.close()
			return
		if answer[1] == "cold":
			self.session.open(TryQuitMainloop,retvalue=42)
			self.close()
		elif answer[1] == "show":
			global plugin_path
			self.session.openWithCallback(self.ipkgCallback(IpkgComponent.EVENT_DONE, None), ShowUpdatePackages, plugin_path)
		else:
			self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE, args = {'test_only': False})

	def modificationCallback(self, res):
		self.ipkg.write(res and "N" or "Y")

	def exit(self):
		if not self.ipkg.isRunning():
			if self.packages != 0 and self.error == 0:
				if fileExists("/etc/enigma2/.removelang"):
					language.delLanguage()
				#self.session.openWithCallback(self.exitAnswer, MessageBox, _("Upgrade finished.") +" "+_("Do you want to reboot your %s %s?") % (getMachineBrand(), getMachineName()))
				self.restoreMetrixHD()
			else:
				self.close()
		else:
			if not self.updating:
				self.ipkg.stop()
				self.close()

	def exitAnswer(self, result):
		if result is not None and result:
			self.session.open(TryQuitMainloop,retvalue=2)
		self.close()

	def restoreMetrixHD(self):
		try:
			if config.skin.primary_skin.value == "MetrixHD/skin.MySkin.xml" and not os.path.exists("/usr/share/enigma2/MetrixHD/skin.MySkin.xml"):
				self.session.openWithCallback(self.restoreMetrixHDCallback, RestoreMyMetrixHD)
			elif config.skin.primary_skin.value == "MetrixHD/skin.MySkin.xml" and config.plugins.MyMetrixLiteOther.EHDenabled.value != '0':
				from Plugins.Extensions.MyMetrixLite.MainSettingsView import MainSettingsView
				MainSettingsView(None).getEHDiconRefresh()
				self.restoreMetrixHDCallback()
			else:
				self.restoreMetrixHDCallback()
		except:
			self.restoreMetrixHDCallback()

	def restoreMetrixHDCallback(self, ret = None):
		self.session.openWithCallback(self.exitAnswer, MessageBox, _("Upgrade finished.") +" "+_("Do you want to reboot your %s %s?") % (getMachineBrand(), getMachineName()))

class IPKGMenu(Screen):
	skin = """
		<screen name="IPKGMenu" position="center,center" size="560,400" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="filelist" position="5,50" size="550,340" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, plugin_path):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Select upgrade source to edit."))
		self.skin_path = plugin_path

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Edit"))

		self.sel = []
		self.val = []
		self.entry = False
		self.exe = False

		self.path = ""

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.KeyOk,
			"cancel": self.keyCancel
		}, -1)

		self["shortcuts"] = ActionMap(["ShortcutActions"],
		{
			"red": self.keyCancel,
			"green": self.KeyOk,
		})
		self["filelist"] = MenuList([])
		self.fill_list()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setWindowTitle()

	def setWindowTitle(self):
		self.setTitle(_("Select upgrade source to edit."))

	def fill_list(self):
		flist = []
		self.path = '/etc/opkg/'
		if (os_path.exists(self.path) == False):
			self.entry = False
			return
		for file in listdir(self.path):
			if file.endswith(".conf"):
				if file not in ('arch.conf', 'opkg.conf'):
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

	def __init__(self, session, configfile = None):
		Screen.__init__(self, session)
		self.session = session
		self.configfile = configfile
		text = ""
		if self.configfile:
			try:
				fp = file(configfile, 'r')
				sources = fp.readlines()
				if sources:
					text = sources[0]
				fp.close()
			except IOError:
				pass

		desk = getDesktop(0)
		x= int(desk.size().width())
		y= int(desk.size().height())

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))

		if (y>=720):
			self["text"] = Input(text, maxSize=False, type=Input.TEXT)
		else:
			self["text"] = Input(text, maxSize=False, visible_width = 55, type=Input.TEXT)

		self["actions"] = NumberActionMap(["WizardActions", "InputActions", "TextEntryActions", "KeyboardInputActions","ShortcutActions"],
		{
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
		}, -1)

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setWindowTitle()
		self["text"].right()

	def setWindowTitle(self):
		self.setTitle(_("Edit upgrade source url."))

	def go(self):
		text = self["text"].getText()
		if text:
			fp = file(self.configfile, 'w')
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
		<screen name="PacketManager" position="center,center" size="530,420" title="Packet manager" >
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

	def __init__(self, session, plugin_path, args = None):
		Screen.__init__(self, session)
		NumericalTextInput.__init__(self)
		self.session = session
		self.skin_path = plugin_path

		self.setUseableChars(u'1234567890abcdefghijklmnopqrstuvwxyz')

		self["shortcuts"] = NumberActionMap(["ShortcutActions", "WizardActions", "NumberActions", "InputActions", "InputAsciiActions", "KeyboardInputActions" ],
		{
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
		}, -1)

		self.list = []
		self.statuslist = []
		self["list"] = List(self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Reload"))

		self.list_updating = True
		self.packetlist = []
		self.installed_packetlist = {}
		self.upgradeable_packages = {}
		self.Console = Console()
		self.cmdList = []
		self.cachelist = []
		self.cache_ttl = 86400  #600 is default, 0 disables, Seconds cache is considered valid (24h should be ok for caching ipkgs)
		self.cache_file = eEnv.resolve('${libdir}/enigma2/python/Plugins/SystemPlugins/SoftwareManager/packetmanager.cache') #Path to cache directory
		self.oktext = _("\nAfter pressing OK, please wait!")
		self.unwanted_extensions = ('-dbg', '-dev', '-doc', '-staticdev', '-src', 'busybox')

		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)
		self.onShown.append(self.setWindowTitle)
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
		keyvalue = unichr(getPrevAsciiCode()).encode("utf-8")
		if len(keyvalue) == 1:
			self.setNextIdx(keyvalue[0])

	def setNextIdx(self,char):
		if char in ("0", "1", "a"):
			self["list"].setIndex(0)
		else:
			idx = self.getNextIdx(char)
			if idx and idx <= self["list"].count:
				self["list"].setIndex(idx)

	def getNextIdx(self,char):
		for idx, i in enumerate(self["list"].list):
			if i[0] and (i[0][0] == char):
				return idx

	def exit(self):
		self.ipkg.stop()
		if self.Console is not None:
			if len(self.Console.appContainers):
				for name in self.Console.appContainers.keys():
					self.Console.kill(name)
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)
		self.close()

	def reload(self):
		if (os_path.exists(self.cache_file) == True):
			remove(self.cache_file)
			self.list_updating = True
			self.rebuildList()

	def setWindowTitle(self):
		self.setTitle(_("Packet manager"))

	def setStatus(self,status = None):
		if status:
			self.statuslist = []
			divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, "div-h.png"))
			if status == 'update':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/upgrade.png"))
				self.statuslist.append(( _("Package list update"), '', _("Trying to download a new packetlist. Please wait..." ),'',statuspng, divpng ))
				self['list'].setList(self.statuslist)
			elif status == 'error':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/remove.png"))
				self.statuslist.append(( _("Error"), '', _("An error occurred while downloading the packetlist. Please try again." ),'',statuspng, divpng ))
				self['list'].setList(self.statuslist)

	def rebuildList(self):
		self.setStatus('update')
		self.inv_cache = 0
		self.vc = valid_cache(self.cache_file, self.cache_ttl)
		if self.cache_ttl > 0 and self.vc != 0:
			try:
				self.buildPacketList()
			except:
				self.inv_cache = 1
		if self.cache_ttl == 0 or self.inv_cache == 1 or self.vc == 0:
			self.run = 0
			self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)

	def go(self, returnValue = None):
		cur = self["list"].getCurrent()
		if cur:
			status = cur[3]
			package = cur[0]
			self.cmdList = []
			if status == 'installed':
				self.cmdList.append((IpkgComponent.CMD_REMOVE, { "package": package }))
				if len(self.cmdList):
					self.session.openWithCallback(self.runRemove, MessageBox, _("Do you want to remove the package:\n") + package + "\n" + self.oktext)
			elif status == 'upgradeable':
				self.cmdList.append((IpkgComponent.CMD_INSTALL, { "package": package }))
				if len(self.cmdList):
					self.session.openWithCallback(self.runUpgrade, MessageBox, _("Do you want to upgrade the package:\n") + package + "\n" + self.oktext)
			elif status == "installable":
				self.cmdList.append((IpkgComponent.CMD_INSTALL, { "package": package }))
				if len(self.cmdList):
					self.session.openWithCallback(self.runUpgrade, MessageBox, _("Do you want to install the package:\n") + package + "\n" + self.oktext)

	def runRemove(self, result):
		if result:
			self.session.openWithCallback(self.runRemoveFinished, Ipkg, cmdList = self.cmdList)

	def runRemoveFinished(self):
		self.session.openWithCallback(self.RemoveReboot, MessageBox, _("Remove finished.") +" "+_("Do you want to reboot your receiver?"), MessageBox.TYPE_YESNO)

	def RemoveReboot(self, result):
		if result is None:
			return
		if result is False:
			cur = self["list"].getCurrent()
			if cur:
				item = self['list'].getIndex()
				self.list[item] = self.buildEntryComponent(cur[0], cur[1], cur[2], 'installable')
				self.cachelist[item] = [cur[0], cur[1], cur[2], 'installable']
				self['list'].setList(self.list)
				write_cache(self.cache_file, self.cachelist)
				self.reloadPluginlist()
		if result:
			self.session.open(TryQuitMainloop,retvalue=3)

	def runUpgrade(self, result):
		if result:
			self.session.openWithCallback(self.runUpgradeFinished, Ipkg, cmdList = self.cmdList)

	def runUpgradeFinished(self):
		self.session.openWithCallback(self.UpgradeReboot, MessageBox, _("Upgrade finished.") +" "+_("Do you want to reboot your receiver?"), MessageBox.TYPE_YESNO)

	def UpgradeReboot(self, result):
		if result is None:
			return
		if result is False:
			cur = self["list"].getCurrent()
			if cur:
				item = self['list'].getIndex()
				self.list[item] = self.buildEntryComponent(cur[0], cur[1], cur[2], 'installed')
				self.cachelist[item] = [cur[0], cur[1], cur[2], 'installed']
				self['list'].setList(self.list)
				write_cache(self.cache_file, self.cachelist)
				self.reloadPluginlist()
		if result:
			self.session.open(TryQuitMainloop,retvalue=3)

	def ipkgCallback(self, event, param):
		if event == IpkgComponent.EVENT_ERROR:
			self.list_updating = False
			self.setStatus('error')
		elif event == IpkgComponent.EVENT_DONE:
			if self.list_updating:
				self.list_updating = False
				if not self.Console:
					self.Console = Console()
				cmd = self.ipkg.ipkg + " list"
				self.Console.ePopen(cmd, self.IpkgList_Finished)
		#print event, "-", param
		pass

	def IpkgList_Finished(self, result, retval, extra_args = None):
		result = result.replace('\n ',' - ')
		if result:
			self.packetlist = []
			last_name = ""
			for x in result.splitlines():
				tokens = x.split(' - ')
				name = tokens[0].strip()
				if not any((name.endswith(x) or name.find('locale') != -1) for x in self.unwanted_extensions):
					l = len(tokens)
					version = l > 1 and tokens[1].strip() or ""
					descr = l > 3 and tokens[3].strip() or l > 2 and tokens[2].strip() or ""
					if name == last_name:
						continue
					last_name = name
					self.packetlist.append([name, version, descr])

		if not self.Console:
			self.Console = Console()
		cmd = self.ipkg.ipkg + " list_installed"
		self.Console.ePopen(cmd, self.IpkgListInstalled_Finished)

	def IpkgListInstalled_Finished(self, result, retval, extra_args = None):
		if result:
			self.installed_packetlist = {}
			for x in result.splitlines():
				tokens = x.split(' - ')
				name = tokens[0].strip()
				if not any(name.endswith(x) for x in self.unwanted_extensions):
					l = len(tokens)
					version = l > 1 and tokens[1].strip() or ""
					self.installed_packetlist[name] = version
		if not self.Console:
			self.Console = Console()
		cmd = "opkg list-upgradable"
		self.Console.ePopen(cmd, self.OpkgListUpgradeable_Finished)

	def OpkgListUpgradeable_Finished(self, result, retval, extra_args = None):
		if result:
			self.upgradeable_packages = {}
			for x in result.splitlines():
				tokens = x.split(' - ')
				name = tokens[0].strip()
				if not any(name.endswith(x) for x in self.unwanted_extensions):
					l = len(tokens)
					version = l > 2 and tokens[2].strip() or ""
					self.upgradeable_packages[name] = version
		self.buildPacketList()

	def buildEntryComponent(self, name, version, description, state):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, "div-h.png"))
		if not description:
			description = "No description available."
		if state == 'installed':
			installedpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/installed.png"))
			return((name, version, _(description), state, installedpng, divpng))
		elif state == 'upgradeable':
			upgradeablepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/upgradeable.png"))
			return((name, version, _(description), state, upgradeablepng, divpng))
		else:
			installablepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/installable.png"))
			return((name, version, _(description), state, installablepng, divpng))

	def buildPacketList(self):
		self.list = []
		self.cachelist = []
		if self.cache_ttl > 0 and self.vc != 0:
			print 'Loading packagelist cache from ',self.cache_file
			try:
				self.cachelist = load_cache(self.cache_file)
				if len(self.cachelist) > 0:
					for x in self.cachelist:
						self.list.append(self.buildEntryComponent(x[0], x[1], x[2], x[3]))
					self['list'].setList(self.list)
			except:
				self.inv_cache = 1

		if self.cache_ttl == 0 or self.inv_cache == 1 or self.vc == 0:
			print 'rebuilding fresh package list'
			for x in self.packetlist:
				status = ""
				if self.installed_packetlist.has_key(x[0]):
					if self.upgradeable_packages.has_key(x[0]):
						status = "upgradeable"
					else:
						status = "installed"
				else:
					status = "installable"
				self.list.append(self.buildEntryComponent(x[0], x[1], x[2], status))
				self.cachelist.append([x[0], x[1], x[2], status])
			write_cache(self.cache_file, self.cachelist)
			self['list'].setList(self.list)

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

		self.list = SelectionList()
		self["list"] = self.list

		p = 0
		if len(list):
			p = list[0].rfind("/")
			title = list[0][:p]
			self.title = ("%s %s %s") % (_("Install extensions"), _("from"), title)

		for listindex in range(len(list)):
			self.list.addSelection(list[listindex][p+1:], list[listindex], listindex, False)
		self.list.sort()

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Install"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText(_("Invert"))
		self["introduction"] = StaticText(_("Press OK to toggle the selection."))

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"ok": self.list.toggleSelection,
			"cancel": self.close,
			"red": self.close,
			"green": self.install,
			"blue": self.list.toggleAllSelection
		}, -1)

	def install(self):
		list = self.list.getSelectionsList()
		cmdList = []
		for item in list:
			cmdList.append((IpkgComponent.CMD_INSTALL, { "package": item[1] }))
		self.session.open(Ipkg, cmdList = cmdList)


def filescan_open(list, session, **kwargs):
	filelist = [x.path for x in list]
	session.open(IpkgInstaller, filelist) # list

def filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	return \
		Scanner(mimetypes = ["application/x-debian-package"],
			paths_to_scan =
				[
					ScanPath(path = "ipk", with_subdirs = True),
					ScanPath(path = "", with_subdirs = False), 
				], 
			name = "Ipkg",
			description = _("Install extensions."),
			openfnc = filescan_open, )

class ShowUpdatePackages(Screen, NumericalTextInput):
	skin = """
		<screen name="ShowUpdatePackages" position="center,center" size="530,420" title="New Packages" >
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
		
	def __init__(self, session, plugin_path, args = None):
		Screen.__init__(self, session)
		NumericalTextInput.__init__(self)
		self.session = session
		self.skin_path = plugin_path

		self.setUseableChars(u'1234567890abcdefghijklmnopqrstuvwxyz')

		self["shortcuts"] = NumberActionMap(["ShortcutActions", "WizardActions", "NumberActions", "InputActions", "InputAsciiActions", "KeyboardInputActions"],
		{
			"back": self.exit,
			"red": self.exit,
			"ok": self.exit,
			"green": self.rebuildList,
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
		}, -1)
		
		self.list = []
		self.statuslist = []
		self["list"] = List(self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Reload"))

		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)
		self.onShown.append(self.setWindowTitle)
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
		keyvalue = unichr(getPrevAsciiCode()).encode("utf-8")
		if len(keyvalue) == 1:
			self.setNextIdx(keyvalue[0])
		
	def setNextIdx(self,char):
		if char in ("0", "1", "a"):
			self["list"].setIndex(0)
		else:
			idx = self.getNextIdx(char)
			if idx and idx <= self["list"].count:
				self["list"].setIndex(idx)

	def getNextIdx(self,char):
		for idx, i in enumerate(self["list"].list):
			if i[0] and (i[0][0] == char):
				return idx

	def exit(self):
		self.ipkg.stop()
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)
		self.close()
			
	def setWindowTitle(self):
		self.setTitle(_("New Packages"))

	def setStatus(self,status = None):
		if status:
			self.statuslist = []
			divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/div-h.png"))
			if status == 'update':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/upgrade.png"))
				self.statuslist.append(( _("Package list update"), '', _("Trying to download a new updatelist. Please wait..." ),'',statuspng, divpng ))
				self['list'].setList(self.statuslist)	
			elif status == 'error':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/remove.png"))
				self.statuslist.append(( _("Error"), '', _("There was an error downloading the updatelist. Please try again." ),'',statuspng, divpng ))
				self['list'].setList(self.statuslist)				

	def rebuildList(self):
		self.setStatus('update')
		self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE_LIST)

	def ipkgCallback(self, event, param):
		if event == IpkgComponent.EVENT_ERROR:
			self.setStatus('error')
		elif event == IpkgComponent.EVENT_DONE:
			self.buildPacketList()

		pass
	
	def buildEntryComponent(self, name, version, description, state):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/div-h.png"))
		if not description:
			description = "No description available."
		if state == 'installed':
			installedpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/installed.png"))
			return((name, version, _(description), state, installedpng, divpng))	
		elif state == 'upgradeable':
			upgradeablepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/upgradeable.png"))
			return((name, version, _(description), state, upgradeablepng, divpng))	
		else:
			installablepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/installable.png"))
			return((name, version, _(description), state, installablepng, divpng))

	def buildPacketList(self):
		self.list = []
		fetchedList = self.ipkg.getFetchedList()
		excludeList = self.ipkg.getExcludeList()

		if len(fetchedList) > 0:
			for x in fetchedList:
				try:
					self.list.append(self.buildEntryComponent(x[0], x[1], x[2], "upgradeable"))
				except:
					self.list.append(self.buildEntryComponent(x[0], '', 'no valid architecture, ignoring !!', "installable"))
			if len(excludeList) > 0:
				for x in excludeList:
					try:
						self.list.append(self.buildEntryComponent(x[0], x[1], x[2], "installable"))
					except:
						self.list.append(self.buildEntryComponent(x[0], '', 'no valid architecture, ignoring !!', "installable"))

			self['list'].setList(self.list)
	
		else:
			self.setStatus('error')

def UpgradeMain(session, **kwargs):
	session.open(UpdatePluginMenu)

def startSetup(menuid):
	if menuid != "setup":
		return [ ]
	return [(_("Software management"), UpgradeMain, "software_manager", 50)]


def Plugins(path, **kwargs):
	global plugin_path
	plugin_path = path
	list = [
		PluginDescriptor(name=_("Software management"), description=_("Manage your %s %s's software") % (getMachineBrand(), getMachineName()), where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc=startSetup),
		PluginDescriptor(name=_("Ipkg"), where = PluginDescriptor.WHERE_FILESCAN, needsRestart = False, fnc = filescan)
	]
	if config.usage.setup_level.index >= 2: # expert+
		list.append(PluginDescriptor(name=_("Software management"), description=_("Manage your %s %s's software") % (getMachineBrand(), getMachineName()), where = PluginDescriptor.WHERE_EXTENSIONSMENU, needsRestart = False, fnc=UpgradeMain))
	return list
