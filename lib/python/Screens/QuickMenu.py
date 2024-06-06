from re import search, sub
from os.path import exists, isdir, join, realpath

from enigma import BT_SCALE, eEnv, eListboxPythonMultiContent, eTimer, gFont, pNavigation

import NavigationInstance
from skin import getSkinFactor
from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import config
from Components.Console import Console
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryPixmapAlphaBlend, MultiContentEntryText
from Components.Network import iNetwork
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Plugins.SystemPlugins.SoftwareManager.BackupRestore import BackupScreen, BackupSelection, RestoreScreen, getBackupFilename, getBackupPath, getOldBackupPath
from Screens.MessageBox import MessageBox
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.PluginBrowser import PackageAction
from Screens.Screen import Screen
from Screens.Setup import Setup
from Tools.Directories import isPluginInstalled, fileReadLines
from Tools.LoadPixmap import LoadPixmap

MODULE_NAME = __name__.split(".")[-1]

NETWORKBROWSER = isPluginInstalled("NetworkBrowser")
AUDIOSYNC = isPluginInstalled("AudioSync")
VIDEOENH = isPluginInstalled("VideoEnhancement") and exists("/proc/stb/vmpeg/0/pep_apply")
POSSETUP = isPluginInstalled("PositionerSetup")
SATFINDER = isPluginInstalled("Satfinder")


def isFileSystemSupported(filesystem):
	try:
		for fs in open("/proc/filesystems"):
			if fs.strip().endswith(filesystem):
				return True
		return False
	except OSError as err:
		print(f"[Harddisk] Failed to read /proc/filesystems: {str(err)}")


class QuickMenu(Screen, ProtectedScreen):
	skin = """
	<screen name="QuickMenu" position="center,center" size="1180,600" backgroundColor="black" flags="wfBorder" resolution="1280,720">
		<widget name="list" position="21,32" size="370,400" backgroundColor="black" itemHeight="50" transparent="1" />
		<widget name="sublist" position="410,32" size="300,400" backgroundColor="black" itemHeight="50" />
		<eLabel position="400,30" size="2,400" backgroundColor="darkgrey" zPosition="3" />
		<widget source="session.VideoPicture" render="Pig" position="720,30" size="450,300" backgroundColor="transparent" zPosition="1" />
		<widget name="description" position="22,445" size="1150,110" zPosition="1" font="Regular;22" halign="center" backgroundColor="black" transparent="1" />
		<widget name="key_red" position="20,571" size="300,26" zPosition="1" font="Regular;22" halign="center" foregroundColor="white" backgroundColor="black" transparent="1" />
		<widget name="key_green" position="325,571" size="300,26" zPosition="1" font="Regular;22" halign="center" foregroundColor="white" backgroundColor="black" transparent="1" />
		<widget name="key_yellow" position="630,571" size="300,26" zPosition="1" font="Regular;22" halign="center" foregroundColor="white" backgroundColor="black" transparent="1" valign="center" />
		<eLabel name="new eLabel" position="21,567" size="300,3" zPosition="3" backgroundColor="red" />
		<eLabel name="new eLabel" position="325,567" size="300,3" zPosition="3" backgroundColor="green" />
		<eLabel name="new eLabel" position="630,567" size="300,3" zPosition="3" backgroundColor="yellow" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Quick Launch Menu"))
		ProtectedScreen.__init__(self)
		self["key_red"] = Label(_("Exit"))
		self["key_green"] = Label(_("System Info"))
		self["key_yellow"] = Label(_("Devices"))
		self["description"] = Label()
		self["summary_description"] = StaticText("")
		self.menu = 0
		self.mainList = []
		self["list"] = QuickMenuList(self.mainList)
		self.subList = []
		self["sublist"] = QuickMenuSubList(self.subList)
		self.selectedList = []
		self.onChangedEntry = []
		self["list"].onSelectionChanged.append(self.selectionChanged)
		self["sublist"].onSelectionChanged.append(self.selectionSubChanged)
		helpStr = _("Direct menu item selection")
		self["NavigationActions"] = HelpableNumberActionMap(self, ["OkCancelActions", "NavigationActions", "NumberActions"], {
			"ok": self.ok,
			"cancel": self.close,
			"left": self.goLeft,
			"right": self.goRight,
			"up": self.goUp,
			"down": self.goDown,
			"1": (self.keyNumberGlobal, helpStr),
			"2": (self.keyNumberGlobal, helpStr),
			"3": (self.keyNumberGlobal, helpStr),
			"4": (self.keyNumberGlobal, helpStr),
			"5": (self.keyNumberGlobal, helpStr),
			"6": (self.keyNumberGlobal, helpStr),
			"7": (self.keyNumberGlobal, helpStr),
			"8": (self.keyNumberGlobal, helpStr),
			"9": (self.keyNumberGlobal, helpStr),
			"0": (self.keyNumberGlobal, helpStr)
		}, prio=-1, description=_("Menu Common Actions"))
		self["ColorActions"] = HelpableActionMap(self, "ColorActions", {
			"red": self.close,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
		}, prio=0)
		self.skinFactor = getSkinFactor()
		self.showMainMenu()
		self.selectedList = self["list"]
		self.selectionChanged()
		self.onLayoutFinish.append(self.layoutFinished)

	def keyNumberGlobal(self, number):  # Run a numbered shortcut.
		count = self.selectedList.count()
		if number and number <= count:
			self.selectedList.setCurrentIndex(number - 1)
			self.ok()

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and not config.ParentalControl.config_sections.main_menu.value and config.ParentalControl.config_sections.quickmenu.value

	def createSummary(self):
		pass

	def layoutFinished(self):
		self["sublist"].selectionEnabled(False)

	def selectionChanged(self):
		if self.selectedList == self["list"]:
			item = self["list"].getCurrent()
			if item:
				self["description"].text = item[4][7]
				self["summary_description"].text = item[0]
				self.selectMainItem()

	def selectionSubChanged(self):
		if self.selectedList == self["sublist"]:
			item = self["sublist"].getCurrent()
			if item:
				self["description"].text = item[3][7]
				self["summary_description"].text = item[0]

	def goLeft(self):
		if self.menu != 0:
			self.menu = 0
			self.selectedList = self["list"]
			self["list"].selectionEnabled(1)
			self["sublist"].selectionEnabled(0)
			self.selectionChanged()

	def goRight(self):
		if self.menu == 0:
			self.menu = 1
			self.selectedList = self["sublist"]
			self["sublist"].moveToIndex(0)
			self["list"].selectionEnabled(0)
			self["sublist"].selectionEnabled(1)
			self.selectionSubChanged()

	def goUp(self):
		self.selectedList.up()

	def goDown(self):
		self.selectedList.down()

	def keyGreen(self):
		from Screens.Information import DistributionInformation
		self.session.open(DistributionInformation)

	def keyYellow(self):
		self.session.open(QuickMenuDevices)

# ####### Main Menu ##############################
	def showMainMenu(self):
		self.menu = 0
		self.mainList = []
		self.mainList.append(self.QuickMenuEntryComponent(0, "Software_Manager", _("Software Manager"), _("Update/Backup/Restore your box"), _("Update/Backup your firmware, Backup/Restore settings")))
		if BoxInfo.getItem("SoftCam"):
			self.mainList.append(self.QuickMenuEntryComponent(1, "Softcam", _("Softcam"), _("Start/stop/select cam"), _("Start/stop/select your cam, You need to install first a softcam")))
		self.mainList.append(self.QuickMenuEntryComponent(2, "System", _("System"), _("System Setup"), _("Setup your System")))
		self.mainList.append(self.QuickMenuEntryComponent(3, "Mounts", _("Mounts"), _("Mount Setup"), _("Setup your mounts for network")))
		self.mainList.append(self.QuickMenuEntryComponent(4, "Network", _("Network"), _("Setup your local network"), _("Setup your local network. For Wlan you need to boot with a USB-Wlan stick")))
		self.mainList.append(self.QuickMenuEntryComponent(5, "AV_Setup", _("AV Setup"), _("Setup Video/Audio"), _("Setup your Video Mode, Video Output and other Video Settings")))
		self.mainList.append(self.QuickMenuEntryComponent(6, "Tuner_Setup", _("Tuner Setup"), _("Setup Tuner"), _("Setup your Tuner and search for channels")))
		self.mainList.append(self.QuickMenuEntryComponent(7, "Plugins", _("Plugins"), _("Setup Plugins"), _("Shows available plugins. Here you can download and install them")))
		self.mainList.append(self.QuickMenuEntryComponent(8, "Harddisk", _("Harddisk"), _("Harddisk Setup"), _("Setup your Harddisk")))
		self["list"].setList(self.mainList)

# ####### System Setup Menu ##############################
	def subMenuSystem(self):
		self.subList = []
		self.subList.append(self.QuickSubMenuEntryComponent(_("Customize"), _("Setup Enigma2"), _("Customize enigma2 personal settings"), setup="Usage"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("OSD Settings"), _("OSD Setup"), _("Setup your OSD"), setup="UserInterface"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Button Setup"), _("Button Setup"), _("Setup your remote buttons"), setup="RemoteButton"))
		if BoxInfo.getItem("FrontpanelDisplay") and BoxInfo.getItem("Display"):
			self.subList.append(self.QuickSubMenuEntryComponent(_("Display Settings"), _("Setup your LCD"), _("Setup your display"), setup="Display"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Skin Settings"), _("Select Enigma2 Skin"), _("Setup your Skin"), setup="SkinSelection"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Channel Selection"), _("Channel selection configuration"), _("Setup your Channel selection configuration"), setup="ChannelSelection"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Recording Settings"), _("Recording Setup"), _("Setup your recording config"), setup="Recording"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("EPG Settings"), _("EPG Setup"), _("Setup your EPG config"), setup="EPG"))
		self["sublist"].setList(self.subList)

# ####### Network Menu ##############################
	def subMenuNetwork(self):
		def networkInterface():
			self.openScreen("NetworkSetup", screenName="AdapterSetup", networkinfo=self.activeInterface)

		def networkWizard():
			from Plugins.SystemPlugins.NetworkWizard.NetworkWizard import NetworkWizard
			self.session.open(NetworkWizard)

		self.getNetworkInterfaces()
		self.subList = []
		if isPluginInstalled("NetworkWizard"):
			self.subList.append(self.QuickSubMenuEntryComponent(_("Network Wizard"), _("Configure your Network"), _("Use the Networkwizard to configure your Network. The wizard will help you to setup your network"), callback=networkWizard))
		if len(self.adapters) > 1:  # show only adapter selection if more as 1 adapter is installed
			self.subList.append(self.QuickSubMenuEntryComponent(_("Network Adapter Selection"), _("Select Lan/Wlan"), _("Setup your network interface. If no Wlan stick is used, you only can select Lan"), screen="NetworkSetup", screenName="NetworkAdapterSelection"))
		if self.activeInterface is not None:  # show only if there is already a adapter up
			self.subList.append(self.QuickSubMenuEntryComponent(_("Network Interface"), _("Setup interface"), _("Setup network. Here you can setup DHCP, IP, DNS"), callback=networkInterface))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Network Restart"), _("Restart network to with current setup"), _("Restart network and remount connections"), screen="RestartNetwork"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Network Services"), _("Setup Network Services"), _("Setup Network Services (Samba, Ftp, NFS, ...)"), screen="NetworkSetup", screenName="NetworkServicesSetup"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("MiniDLNA"), _("Setup MiniDLNA"), _("Setup MiniDLNA"), screen="NetworkSetup", screenName="NetworkMiniDLNASetup"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Inadyn"), _("Setup Inadyn"), _("Setup Inadyn"), screen="NetworkSetup", screenName="NetworkInadynSetup"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("uShare"), _("Setup uShare"), _("Setup uShare"), screen="NetworkSetup", screenName="NetworkuShareSetup"))
		self["sublist"].setList(self.subList)

# ####### Mount Settings Menu ##############################
	def subMenuMount(self):
		def mountManager():
			from Plugins.SystemPlugins.NetworkBrowser.MountManager import AutoMountManager
			plugin_path_networkbrowser = eEnv.resolve("${libdir}/enigma2/python/Plugins/SystemPlugins/NetworkBrowser")
			self.session.open(AutoMountManager, None, plugin_path_networkbrowser)

		def networkBrowser():
			from Plugins.SystemPlugins.NetworkBrowser.NetworkBrowser import NetworkBrowser
			plugin_path_networkbrowser = eEnv.resolve("${libdir}/enigma2/python/Plugins/SystemPlugins/NetworkBrowser")
			self.session.open(NetworkBrowser, None, plugin_path_networkbrowser)

		self.subList = []
		if NETWORKBROWSER:
			self.subList.append(self.QuickSubMenuEntryComponent(_("Mount Manager"), _("Manage network mounts"), _("Setup your network mounts"), callback=mountManager))
			self.subList.append(self.QuickSubMenuEntryComponent(_("Network Browser"), _("Search for network shares"), _("Search for network shares"), callback=networkBrowser))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Device Manager"), _("Mounts Devices"), _("Setup your Device mounts (USB, HDD, others...)"), screen="MountManager", screenName="HddMount"))
		self["sublist"].setList(self.subList)

# ####### Softcam Menu ##############################
	def subMenuSoftcam(self):

		def downloadSoftcams():
			self.session.open(PackageAction, PackageAction.MODE_SOFTCAM)

		self.subList = []
		if BoxInfo.getItem("SoftCam"):  # show only when there is a softcam installed
			self.subList.append(self.QuickSubMenuEntryComponent(_("Softcam Settings"), _("Control your Softcams"), _("Use the Softcam Panel to control your Cam. This let you start/stop/select a cam"), screen="SoftcamSetup"))
			if BoxInfo.getItem("ShowOscamInfo"):  # show only when oscam or ncam is active
				self.subList.append(self.QuickSubMenuEntryComponent(_("OSCam Information"), _("Show OSCam Information"), _("Show the OSCam information screen"), screen="OSCamInfo"))
			if BoxInfo.getItem("ShowCCCamInfo"):  # show only when CCcam is active
				self.subList.append(self.QuickSubMenuEntryComponent(_("CCcam Information"), _("Show CCcam Info"), _("Show the CCcam Info Screen"), screen="CCcamInfo", screenName="CCcamInfoMain"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Download Softcams"), _("Download and install cam"), _("Shows available softcams. Here you can download and install them"), callback=downloadSoftcams))
		self["sublist"].setList(self.subList)

# ####### A/V Settings Menu ##############################
	def subMenuAvsetup(self):
		def audioSync():
			from Plugins.Extensions.AudioSync.AC3setup import AC3LipSyncSetup
			plugin_path_audiosync = eEnv.resolve("${libdir}/enigma2/python/Plugins/Extensions/AudioSync")
			self.session.open(AC3LipSyncSetup, plugin_path_audiosync)

		def videoEnhancement():
			from Plugins.SystemPlugins.VideoEnhancement.plugin import VideoEnhancementSetup
			self.session.open(VideoEnhancementSetup)

		self.subList = []
		self.subList.append(self.QuickSubMenuEntryComponent(_("Video Settings"), _("Setup Videomode"), _("Setup your Video Mode, Video Output and other Video Settings"), screen="VideoMode", screenName="VideoSetup"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Audio Settings"), _("Setup Audiomode"), _("Setup your Audio Mode"), setup="Audio"))
		if AUDIOSYNC:
			self.subList.append(self.QuickSubMenuEntryComponent(_("Audio Sync"), _("Setup Audio Sync"), _("Setup Audio Sync settings"), callback=audioSync))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Auto Language"), _("Auto Language Selection"), _("Select your Language for Audio/Subtitles"), setup="AutoLanguage"))
		if VIDEOENH:
			self.subList.append(self.QuickSubMenuEntryComponent(_("VideoEnhancement"), _("VideoEnhancement Setup"), _("VideoEnhancement Setup"), callback=videoEnhancement))

		self["sublist"].setList(self.subList)

# ####### Tuner Menu ##############################
	def subMenuTuner(self):
		def positionerSetup():
			from Plugins.SystemPlugins.PositionerSetup.plugin import PositionerMain
			PositionerMain(self.session)

		self.subList = []
		self.subList.append(self.QuickSubMenuEntryComponent(_("Tuner Configuration"), _("Setup tuner(s)"), _("Setup each tuner for your satellite system"), screen="SatConfig", screenName="NimSelection"))
		if POSSETUP:
			self.subList.append(self.QuickSubMenuEntryComponent(_("Positioner Setup"), _("Setup rotor"), _("Setup your positioner for your satellite system"), callback=positionerSetup))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Automatic Scan"), _("Automatic Service Searching"), _("Automatic scan for services"), screen="ScanSetup", screenName="ScanSimple"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Manual Scan"), _("Manual Service Searching"), _("Manual scan for services"), screen="ScanSetup"))
		if SATFINDER:
			self.subList.append(self.QuickSubMenuEntryComponent(_("Sat Finder"), _("Search Sats"), _("Search Sats, check signal and lock"), callback=self.satfinderMain))
		self["sublist"].setList(self.subList)

# ####### Software Manager Menu ##############################
	def subMenuSoftware(self):
		def backupSettings():
			#self.session.openWithCallback(self.backupDone, BackupScreen, runBackup=True)
			self.session.open(BackupScreen, runBackup=True, closeOnSuccess=False)

		def restoreSettings():
			self.backuppath = getBackupPath()
			if not isdir(self.backuppath):
				self.backuppath = getOldBackupPath()
			self.backupfile = getBackupFilename()
			self.fullbackupfilename = join(self.backuppath, self.backupfile)
			if exists(self.fullbackupfilename):
				self.session.openWithCallback(self.startRestore, MessageBox, _("Are you sure you want to restore your %s %s backup?\nSTB will restart after the restore") % getBoxDisplayName(), default=False)
			else:
				self.session.open(MessageBox, _("Sorry no backups found!"), MessageBox.TYPE_INFO, timeout=10)

		def defaultBackupFiles():
			self.session.open(BackupSelection, title=_("Default files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs_default, readOnly=True, mode="backupfiles")

		def additionalBackupFiles():
			self.session.open(BackupSelection, title=_("Additional files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs, readOnly=False, mode="backupfiles_addon")

		def excludedBackupFiles():
			self.session.open(BackupSelection, title=_("Files/folders to exclude from backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs_exclude, readOnly=False, mode="backupfiles_exclude")

		self.subList = []
		self.subList.append(self.QuickSubMenuEntryComponent(_("Software Update"), _("Online software update"), _("Check/Install online updates (you must have a working Internet connection)"), screen="SoftwareUpdate"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Flash Online"), _("Flash Online a new image"), _("Flash on the fly your your Receiver software."), screen="FlashManager"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Complete Backup"), _("Backup your current image"), _("Backup your current image to HDD or USB. This will make a 1:1 copy of your box"), callback=self.completeBackup))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Backup Settings"), _("Backup your current settings"), _("Backup your current settings. This includes E2-setup, channels, network and all selected files"), callback=backupSettings))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Restore Settings"), _("Restore settings from a backup"), _("Restore your settings back from a backup. After restore the box will restart to activated the new settings"), callback=restoreSettings))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Show Default Backup Files"), _("Show files backed up by default"), _("Here you can browse (but not modify) the files that are added to the backupfile by default (E2-setup, channels, network)."), callback=defaultBackupFiles))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Select Additional Backup Files"), _("Select additional files to backup"), _("Here you can specify additional files that should be added to the backup file."), callback=additionalBackupFiles))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Select Excluded Backup Files"), _("Select files to exclude from backup"), _("Here you can select which files should be excluded from the backup."), callback=excludedBackupFiles))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Software Manager Settings"), _("Manage your online update files"), _("Here you can select which files should be updated with a online update"), setup="SoftwareManager"))
		self["sublist"].setList(self.subList)

# ####### Plugins Menu ##############################
	def subMenuPlugin(self):
		def ipkInstaller():
			try:
				from Plugins.Extensions.MediaScanner.plugin import main
				main(self.session)
			except Exception:
				self.session.open(MessageBox, _("Sorry MediaScanner is not installed!"), MessageBox.TYPE_INFO, timeout=10)

		def downloadPlugins():
			self.session.open(PackageAction, PackageAction.MODE_INSTALL)

		def removePlugins():
			self.session.open(PackageAction, PackageAction.MODE_REMOVE)

		def managePlugins():
			self.session.open(PackageAction, PackageAction.MODE_MANAGE)

		self.subList = []
		self.subList.append(self.QuickSubMenuEntryComponent(_("Plugin Browser"), _("Open the Plugin Browser"), _("Shows Plugins Browser. Here you can setup installed Plugin"), screen="PluginBrowser"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Download Plugins"), _("Download and install Plugins"), _("Shows available plugins. Here you can download and install them"), callback=downloadPlugins))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Remove Plugins"), _("Delete Plugins"), _("Delete and uninstall Plugins. This will remove the Plugin from your box"), callback=removePlugins))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Manage Plugins"), _("Manage Plugins"), _("Manage Plugins. This will remove/install Plugins on your box"), callback=managePlugins))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Plugin Browser Settings"), _("Setup Plugin Browser"), _("Setup PluginBrowser. Here you can select which Plugins are showed in the PluginBrowser"), setup="PluginBrowser"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("IPK Installer"), _("Install Local Extension"), _("Scan for local extensions and install them"), callback=ipkInstaller))
		self["sublist"].setList(self.subList)

# ####### Harddisk Menu ##############################
	def subMenuHarddisk(self):
		self.subList = []
		self.subList.append(self.QuickSubMenuEntryComponent(_("Harddisk Setup"), _("Harddisk Setup"), _("Setup your Harddisk"), setup="HardDisk"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("Initialization"), _("Format HDD"), _("Format your hard drive"), screen="HarddiskSetup", screenName="HarddiskSelection"))
		self.subList.append(self.QuickSubMenuEntryComponent(_("File System Check"), _("Check HDD"), _("Filesystem check your hard drive"), screen="HarddiskSetup", screenName="HarddiskFsckSelection"))
		if isFileSystemSupported("ext4"):
			self.subList.append(self.QuickSubMenuEntryComponent(_("Convert ext3 to ext4"), _("Convert file system ext3 to ext4"), _("Convert file system ext3 to ext4"), screen="HarddiskSetup", screenName="HarddiskConvertExt4Selection"))
		self["sublist"].setList(self.subList)

	def ok(self):
		if self.menu > 0:
			self.selectSubItem()
		else:
			self.goRight()


# ####################################################################
# ####### Make Selection MAIN MENU LIST ##############################
# ####################################################################


	def selectMainItem(self):
		item = self["list"].getCurrent()[0]
		match item:
			case 0:
				self.subMenuSoftware()
			case 1:
				self.subMenuSoftcam()
			case 2:
				self.subMenuSystem()
			case 3:
				self.subMenuMount()
			case 4:
				self.subMenuNetwork()
			case 5:
				self.subMenuAvsetup()
			case 6:
				self.subMenuTuner()
			case 7:
				self.subMenuPlugin()
			case 8:
				self.subMenuHarddisk()

		self["sublist"].selectionEnabled(0)

# ####################################################################
# ####### Make Selection SUB MENU LIST ##############################
# ####################################################################

	def selectSubItem(self):
		(setup, screen, screenName, callback) = self["sublist"].getCurrent()[0]
		if setup:
			self.openSetup(setup)
		elif screen:
			self.openScreen(screen, screenName=screenName)
		elif callback and callable(callback):
			callback()

	def openSetup(self, dialog):
		self.session.openWithCallback(self.menuClosed, Setup, dialog)

	def openScreen(self, screenModule, screenName=None, **kwargs):
		try:
			screenobj = __import__(f"Screens.{screenModule}", None, None, [screenName or screenModule], 0)
			self.session.open(getattr(screenobj, screenName or screenModule), **kwargs)
		except (ModuleNotFoundError, AttributeError) as err:
			print(f"[QuickMenu] Error openScreen: {err}")

	def menuClosed(self, *res):
		pass

# ####### NETWORK TOOLS #######################
	def getNetworkInterfaces(self):
		self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getAdapterList()]
		if not self.adapters:
			self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getConfiguredAdapters()]
		if len(self.adapters) == 0:
			self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getInstalledAdapters()]
		self.activeInterface = None
		for x in self.adapters:
			if iNetwork.getAdapterAttribute(x[1], "up") is True:
				self.activeInterface = x[1]
				return

# ####### TUNER TOOLS #######################
	def satfinderMain(self):
		if len(NavigationInstance.instance.getRecordings(False, pNavigation.isAnyRecording)) > 0:
			self.session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to start the satellite finder."), MessageBox.TYPE_ERROR)
		else:
			from Plugins.SystemPlugins.Satfinder.plugin import Satfinder
			self.session.open(Satfinder)

# ####### SOFTWARE MANAGER TOOLS #######################
	def backupDone(self, retval=None):
		self.session.open(MessageBox, _("Backup done.") if retval else _("Backup failed!"), MessageBox.TYPE_INFO if retval else MessageBox.TYPE_ERROR, timeout=10)

	def startRestore(self, ret=False):
		if (ret is True):
			self.exe = True
			self.session.open(RestoreScreen, runRestore=True)

	def completeBackup(self):
		if BoxInfo.getItem("dFlash"):
			from Plugins.Extensions.dFlash.plugin import dFlash
			self.session.open(dFlash)
		elif BoxInfo.getItem("dBackup"):
			from Plugins.Extensions.dBackup.plugin import dBackup
			self.session.open(dBackup)
		else:
			from Plugins.SystemPlugins.SoftwareManager.ImageBackup import ImageBackup
			self.session.open(ImageBackup)

	def QuickSubMenuEntryComponent(self, name, description, longDescription=None, width=540, setup=None, screen=None, screenName=None, callback=None):
		sf = self.skinFactor
		return [
			(setup, screen, screenName, callback),
			MultiContentEntryText(pos=(10 * sf, 2 * sf), size=((width - 10) * sf, 28 * sf), font=0, text=name),
			MultiContentEntryText(pos=(10 * sf, 25 * sf), size=((width - 10) * sf, 22 * sf), font=1, text=description),
			MultiContentEntryText(pos=(0, 0), size=(0, 0), font=0, text=longDescription)
		]

	def QuickMenuEntryComponent(self, itemIndex, pngname, name, description, longDescription=None, width=540):
		png = LoadPixmap(f"/usr/share/enigma2/icons/{pngname}.png")
		if png is None:
			png = LoadPixmap("/usr/share/enigma2/icons/default.png")
		sf = self.skinFactor
		return [
			itemIndex,
			MultiContentEntryText(pos=(60 * sf, 2 * sf), size=((width - 60) * sf, 28 * sf), font=0, text=name),
			MultiContentEntryText(pos=(60 * sf, 25 * sf), size=((width - 60) * sf, 22 * sf), font=1, text=description),
			MultiContentEntryPixmapAlphaBlend(pos=(10 * sf, 5 * sf), size=(40 * sf, 40 * sf), flags=BT_SCALE, png=png),
			MultiContentEntryText(pos=(0, 0), size=(0, 0), font=0, text=longDescription)
		]


class QuickMenuList(MenuList):
	def __init__(self, list, enableWrapAround=True):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		sf = getSkinFactor()
		self.l.setFont(0, gFont("Regular", int(19 * sf)))
		self.l.setFont(1, gFont("Regular", int(16 * sf)))
		self.l.setItemHeight(int(50 * sf))


class QuickMenuSubList(QuickMenuList):
	pass


class QuickMenuDevices(Screen):
	skin = """
	<screen name="QuickMenuDevices" position="center,center" size="840,525" title="Devices" flags="wfBorder" resolution="1280,720">
		<widget source="devicelist" render="Listbox" position="30,46" size="780,450" font="Regular;16" scrollbarMode="showOnDemand" transparent="1" backgroundColorSelected="grey" foregroundColorSelected="black">
			<convert type="TemplatedMultiContent">
				{"template":
					[
					MultiContentEntryText(pos = (90, 0), size = (600, 30), font=0, text = 0),
					MultiContentEntryText(pos = (110, 30), size = (600, 50), font=1, flags = RT_VALIGN_TOP, text = 1),
					MultiContentEntryPixmapAlphaBlend(pos = (0, 0), size = (80, 80), png = 2),
					],
				"fonts": [gFont("Regular", 24),gFont("Regular", 20)],
				"itemHeight": 85
				}
			</convert>
		</widget>
		<widget name="lab1" zPosition="2" position="126,92" size="600,40" font="Regular;22" halign="center" backgroundColor="black" transparent="1" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Devices"))
		self["lab1"] = Label()
		self.devicelist = []
		self["devicelist"] = List(self.devicelist)
		self["actions"] = HelpableActionMap(self, ["CancelActions"], {
			"cancel": self.close,
		}, prio=0)
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.updateList2)
		self.updateList()

	def updateList(self, result=None, retval=None, extra_args=None):
		scanning = _("Wait please while scanning for devices...")
		self["lab1"].setText(scanning)
		self.activityTimer.start(10)

	def updateList2(self):
		def buildMy_rec(device, swapdevices, partitions):
			device2 = sub(r"[\d]", "", device)  # Strip device number.
			deviceType = realpath(f"/sys/block/{device2}/device")
			name = "USB: "
			pixmapName = "dev_usbstick.png"
			with open(f"/sys/block/{device2}/device/model") as fd:
				model = fd.read()
				model = str(model).replace("\n", "")
			des = ""
			if deviceType.find("/devices/pci") != -1:
				name = _("HARD DISK: ")
				pixmapName = "dev_hdd.png"
			name = f"{name}{model}"
			mounts = fileReadLines("/proc/mounts", [], source=MODULE_NAME)
			if mounts:
				for line in mounts:
					if line.find(device) != -1:
						parts = line.strip().split()
						d1 = parts[1]
						dtype = parts[2]
						rw = parts[3]
						break
					else:
						if device in swapdevices:
							parts = line.strip().split()
							d1 = _("None")
							dtype = "swap"
							rw = _("None")
							break
						else:
							d1 = _("None")
							dtype = _("unavailable")
							rw = _("None")
			if partitions:
				for line in partitions:
					if line.find(device) != -1:
						parts = line.strip().split()
						size = int(parts[2])
					else:
						try:
							with open(f"/sys/block/{device2}/{device}/size") as fd:
								size = fd.read()
							size = str(size).replace("\n", "")
							size = int(size)
							size = size // 2
						except Exception:
							size = 0
					if ((size / 1024) / 1024) > 1:
						des = f"{_("Size")}: {str(size // 1024 // 1024)} {_("GB")}"
					else:
						des = f"{_("Size")}: {str(size // 1024)} {_("MB")}"
			if des != "":
				if rw.startswith("rw"):
					rw = " R/W"
				elif rw.startswith("ro"):
					rw = " R/O"
				else:
					rw = ""
				des = f"{des}\t{_("Mount: ")}{d1}\n{_("Device: ")} /dev/{device}\t{_("Type: ")}{dtype}{rw}"
				png = LoadPixmap(join("/usr/share/enigma2/icons", pixmapName))
				self.devicelist.append((name, des, png))

		def swapCallback(data, retVal, extraArgs):
			list2 = []
			swapdevices = data.replace("\n", "").split("/")
			partitions = fileReadLines("/proc/partitions", [], source=MODULE_NAME)
			for partition in partitions:
				parts = partition.split()
				if parts:
					device = parts[3]
					if device not in list2 and search(r"^sd[a-z][1-9][\d]*$", device):
						buildMy_rec(device, swapdevices, partitions)
						list2.append(device)
			self["devicelist"].list = self.devicelist
			if len(self.devicelist) == 0:
				self["lab1"].setText(_("No Devices Found !!"))
			else:
				self["lab1"].hide()
		self.activityTimer.stop()
		self.devicelist = []
		Console().ePopen("sfdisk -l /dev/sd? | grep swap | awk '{print $(NF-9)}'", swapCallback)
