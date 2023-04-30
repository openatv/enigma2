from re import search, sub
from os.path import exists, realpath, isdir
from skin import getSkinFactor
from time import sleep

from enigma import eListboxPythonMultiContent, gFont, eEnv, pNavigation, BT_SCALE

from Components.ActionMap import ActionMap
from Components.Console import Console
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend
from Components.Network import iNetwork
from Components.NimManager import nimmanager
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import BoxInfo, getBoxDisplayName

import NavigationInstance

from Plugins.SystemPlugins.SoftwareManager.BackupRestore import BackupScreen, RestoreScreen, BackupSelection, getBackupPath, getOldBackupPath, getBackupFilename
from Plugins.SystemPlugins.SoftwareManager.plugin import SoftwareManagerSetup

from Screens.HarddiskSetup import HarddiskSelection, HarddiskFsckSelection, HarddiskConvertExt4Selection
from Screens.MountManager import HddMount
from Screens.NetworkSetup import *
from Screens.OScamInfo import OscamInfoMenu
from Screens.CCcamInfo import CCcamInfoMain
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.PluginBrowser import PluginDownloadBrowser, PluginFilter, PluginBrowser
from Screens.RestartNetwork import RestartNetwork
from Screens.Satconfig import NimSelection
from Screens.ScanSetup import ScanSimple, ScanSetup
from Screens.Screen import Screen
from Screens.ShowSoftcamPackages import ShowSoftcamPackages
from Screens.Setup import Setup
from Screens.SkinSelector import LcdSkinSelector, SkinSelector
from Screens.SoftcamSetup import SoftcamSetup
from Screens.VideoMode import VideoSetup

from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import isPluginInstalled


NETWORKBROWSER = isPluginInstalled("NetworkBrowser")
AUDIOSYNC = isPluginInstalled("AudioSync")
VIDEOENH = isPluginInstalled("VideoEnhancement") and exists("/proc/stb/vmpeg/0/pep_apply")
DFLASH = isPluginInstalled("dFlash")
DBACKUP = isPluginInstalled("dBackup")
POSSETUP = isPluginInstalled("PositionerSetup")
SATFINDER = isPluginInstalled("Satfinder")


def isFileSystemSupported(filesystem):
	try:
		for fs in open('/proc/filesystems', 'r'):
			if fs.strip().endswith(filesystem):
				return True
		return False
	except Exception as ex:
		print("[Harddisk] Failed to read /proc/filesystems: %s" % str(ex))


class QuickMenu(Screen, ProtectedScreen):
	skin = """
		<screen name="QuickMenu" position="center,center" size="1180,600" backgroundColor="black" flags="wfBorder">
		<widget name="list" position="21,32" size="370,400" backgroundColor="black" itemHeight="50" transparent="1" />
		<widget name="sublist" position="410,32" size="300,400" backgroundColor="black" itemHeight="50" />
		<eLabel position="400,30" size="2,400" backgroundColor="darkgrey" zPosition="3" />
		<widget source="session.VideoPicture" render="Pig" position="720,30" size="450,300" backgroundColor="transparent" zPosition="1" />
		<widget name="description" position="22,445" size="1150,110" zPosition="1" font="Regular;22" halign="center" backgroundColor="black" transparent="1" />
		<widget name="key_red" position="20,571" size="300,26" zPosition="1" font="Regular;22" halign="center" foregroundColor="white" backgroundColor="black" transparent="1" />
		<widget name="key_green" position="325,571" size="300,26" zPosition="1" font="Regular;22" halign="center" foregroundColor="white" backgroundColor="black" transparent="1" />
		<widget name="key_yellow" position="630,571" size="300,26" zPosition="1" font="Regular;22" halign="center" foregroundColor="white" backgroundColor="black" transparent="1" valign="center" />
		<widget name="key_blue" position="935,571" size="234,26" zPosition="1" font="Regular;22" halign="center" foregroundColor="white" backgroundColor="black" transparent="1" />
		<eLabel name="new eLabel" position="21,567" size="300,3" zPosition="3" backgroundColor="red" />
		<eLabel name="new eLabel" position="325,567" size="300,3" zPosition="3" backgroundColor="green" />
		<eLabel name="new eLabel" position="630,567" size="300,3" zPosition="3" backgroundColor="yellow" />
		<eLabel name="new eLabel" position="935,567" size="234,3" zPosition="3" backgroundColor="blue" />
		</screen> """

	def __init__(self, session):
		Screen.__init__(self, session)
		if config.ParentalControl.configured.value:
			ProtectedScreen.__init__(self)
		Screen.setTitle(self, _("Quick Launch Menu"))
		ProtectedScreen.__init__(self)

		self["key_red"] = Label(_("Exit"))
		self["key_green"] = Label(_("System Info"))
		self["key_yellow"] = Label(_("Devices"))
		self["key_blue"] = Label()
		self["description"] = Label()
		self["summary_description"] = StaticText("")

		self.menu = 0
		self.list = []
		self["list"] = QuickMenuList(self.list)
		self.sublist = []
		self["sublist"] = QuickMenuSubList(self.sublist)
		self.selectedList = []
		self.onChangedEntry = []
		self["list"].onSelectionChanged.append(self.selectionChanged)
		self["sublist"].onSelectionChanged.append(self.selectionSubChanged)

		self["NavigationActions"] = ActionMap(["OkCancelActions", "NavigationActions"],
		{
			"ok": self.ok,
			"cancel": self.keyred,
			"left": self.goLeft,
			"right": self.goRight,
			"up": self.goUp,
			"down": self.goDown,
		}, -1)

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
			"red": self.keyred,
			"green": self.keygreen,
			"yellow": self.keyyellow,
			})

		self.MainQmenu()
		self.selectedList = self["list"]
		self.selectionChanged()
		self.onLayoutFinish.append(self.layoutFinished)

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and not config.ParentalControl.config_sections.main_menu.value and config.ParentalControl.config_sections.quickmenu.value

	def createSummary(self):
		pass

	def layoutFinished(self):
		self["sublist"].selectionEnabled(0)

	def selectionChanged(self):
		if self.selectedList == self["list"]:
			item = self["list"].getCurrent()
			if item:
				self["description"].text = item[4][7]
				self["summary_description"].text = item[0]
				self.okList()

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

	def keyred(self):
		self.close()

	def keygreen(self):
		from Screens.Information import DistributionInformation
		self.session.open(DistributionInformation)

	def keyyellow(self):
		self.session.open(QuickMenuDevices)

######## Main Menu ##############################
	def MainQmenu(self):
		self.menu = 0
		self.list = []
		self.oldlist = []
		self.list.append(QuickMenuEntryComponent("Software Manager", _("Update/Backup/Restore your box"), _("Update/Backup your firmware, Backup/Restore settings")))
		if BoxInfo.getItem("SoftCam"):
			self.list.append(QuickMenuEntryComponent("Softcam", _("Start/stop/select cam"), _("Start/stop/select your cam, You need to install first a softcam")))
		self.list.append(QuickMenuEntryComponent("System", _("System Setup"), _("Setup your System")))
		self.list.append(QuickMenuEntryComponent("Mounts", _("Mount Setup"), _("Setup your mounts for network")))
		self.list.append(QuickMenuEntryComponent("Network", _("Setup your local network"), _("Setup your local network. For Wlan you need to boot with a USB-Wlan stick")))
		self.list.append(QuickMenuEntryComponent("AV Setup", _("Setup Video/Audio"), _("Setup your Video Mode, Video Output and other Video Settings")))
		self.list.append(QuickMenuEntryComponent("Tuner Setup", _("Setup Tuner"), _("Setup your Tuner and search for channels")))
		self.list.append(QuickMenuEntryComponent("Plugins", _("Setup Plugins"), _("Shows available plugins. Here you can download and install them")))
		self.list.append(QuickMenuEntryComponent("Harddisk", _("Harddisk Setup"), _("Setup your Harddisk")))
		self["list"].l.setList(self.list)

######## System Setup Menu ##############################
	def Qsystem(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Customize", _("Setup Enigma2"), _("Customize enigma2 personal settings")))
		self.sublist.append(QuickSubMenuEntryComponent("OSD Settings", _("OSD Setup"), _("Setup your OSD")))
		self.sublist.append(QuickSubMenuEntryComponent("Button Setup", _("Button Setup"), _("Setup your remote buttons")))
		if BoxInfo.getItem("FrontpanelDisplay") and BoxInfo.getItem("Display"):
			self.sublist.append(QuickSubMenuEntryComponent("Display Settings", _("Setup your LCD"), _("Setup your display")))
		if BoxInfo.getItem("LCDSKINSetup"):
			self.sublist.append(QuickSubMenuEntryComponent("LCD Skin Settings", _("Select LCD Skin"), _("Setup your LCD Skin")))
		self.sublist.append(QuickSubMenuEntryComponent("Skin Settings", _("Select Enigma2 Skin"), _("Setup your Skin")))
		self.sublist.append(QuickSubMenuEntryComponent("Channel selection", _("Channel selection configuration"), _("Setup your Channel selection configuration")))
		self.sublist.append(QuickSubMenuEntryComponent("Recording Settings", _("Recording Setup"), _("Setup your recording config")))
		self.sublist.append(QuickSubMenuEntryComponent("EPG Settings", _("EPG Setup"), _("Setup your EPG config")))
		self["sublist"].l.setList(self.sublist)

######## Network Menu ##############################
	def Qnetwork(self):
		self.sublist = []
		if isPluginInstalled("NetworkWizard"):
			self.sublist.append(QuickSubMenuEntryComponent("Network Wizard", _("Configure your Network"), _("Use the Networkwizard to configure your Network. The wizard will help you to setup your network")))
		if len(self.adapters) > 1:  # show only adapter selection if more as 1 adapter is installed
			self.sublist.append(QuickSubMenuEntryComponent("Network Adapter Selection", _("Select Lan/Wlan"), _("Setup your network interface. If no Wlan stick is used, you only can select Lan")))
		if not self.activeInterface == None:  # show only if there is already a adapter up
			self.sublist.append(QuickSubMenuEntryComponent("Network Interface", _("Setup interface"), _("Setup network. Here you can setup DHCP, IP, DNS")))
		self.sublist.append(QuickSubMenuEntryComponent("Network Restart", _("Restart network to with current setup"), _("Restart network and remount connections")))
		self.sublist.append(QuickSubMenuEntryComponent("Network Services", _("Setup Network Services"), _("Setup Network Services (Samba, Ftp, NFS, ...)")))
		self["sublist"].l.setList(self.sublist)

#### Network Services Menu ##############################
	def Qnetworkservices(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Samba", _("Setup Samba"), _("Setup Samba")))
		self.sublist.append(QuickSubMenuEntryComponent("NFS", _("Setup NFS"), _("Setup NFS")))
		self.sublist.append(QuickSubMenuEntryComponent("FTP", _("Setup FTP"), _("Setup FTP")))
		self.sublist.append(QuickSubMenuEntryComponent("SATPI", _("Setup SATPI"), _("Setup SATPI")))
		self.sublist.append(QuickSubMenuEntryComponent("OpenVPN", _("Setup OpenVPN"), _("Setup OpenVPN")))
		self.sublist.append(QuickSubMenuEntryComponent("MiniDLNA", _("Setup MiniDLNA"), _("Setup MiniDLNA")))
		self.sublist.append(QuickSubMenuEntryComponent("Inadyn", _("Setup Inadyn"), _("Setup Inadyn")))
		self.sublist.append(QuickSubMenuEntryComponent("SABnzbd", _("Setup SABnzbd"), _("Setup SABnzbd")))
		self.sublist.append(QuickSubMenuEntryComponent("uShare", _("Setup uShare"), _("Setup uShare")))
		self.sublist.append(QuickSubMenuEntryComponent("Telnet", _("Setup Telnet"), _("Setup Telnet")))
		self.sublist.append(QuickSubMenuEntryComponent("AFP", _("Setup AFP"), _("Setup AFP")))
		self["sublist"].l.setList(self.sublist)

######## Mount Settings Menu ##############################
	def Qmount(self):
		self.sublist = []
		if NETWORKBROWSER:
			self.sublist.append(QuickSubMenuEntryComponent("Mount Manager", _("Manage network mounts"), _("Setup your network mounts")))
			self.sublist.append(QuickSubMenuEntryComponent("Network Browser", _("Search for network shares"), _("Search for network shares")))
		self.sublist.append(QuickSubMenuEntryComponent("Device Manager", _("Mounts Devices"), _("Setup your Device mounts (USB, HDD, others...)")))
		self["sublist"].l.setList(self.sublist)

######## Softcam Menu ##############################
	def Qsoftcam(self):
		self.sublist = []
		if BoxInfo.getItem("SoftCam"):  # show only when there is a softcam installed
			self.sublist.append(QuickSubMenuEntryComponent("Softcam Settings", _("Control your Softcams"), _("Use the Softcam Panel to control your Cam. This let you start/stop/select a cam")))
			if BoxInfo.getItem("ShowOscamInfo"):  # show only when oscam or ncam is active
				self.sublist.append(QuickSubMenuEntryComponent("OScam Information", _("Show OScam Info"), _("Show the OScamInfo Screen")))
			if BoxInfo.getItem("ShowCCCamInfo"):  # show only when CCcam is active
				self.sublist.append(QuickSubMenuEntryComponent("CCcam Information", _("Show CCcam Info"), _("Show the CCcam Info Screen")))
		self.sublist.append(QuickSubMenuEntryComponent("Download Softcams", _("Download and install cam"), _("Shows available softcams. Here you can download and install them")))
		self["sublist"].l.setList(self.sublist)

######## A/V Settings Menu ##############################
	def Qavsetup(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Video Settings", _("Setup Videomode"), _("Setup your Video Mode, Video Output and other Video Settings")))
		self.sublist.append(QuickSubMenuEntryComponent("Audio Settings", _("Setup Audiomode"), _("Setup your Audio Mode")))
		if AUDIOSYNC:
			self.sublist.append(QuickSubMenuEntryComponent("Audio Sync", _("Setup Audio Sync"), _("Setup Audio Sync settings")))
		self.sublist.append(QuickSubMenuEntryComponent("Auto Language", _("Auto Language Selection"), _("Select your Language for Audio/Subtitles")))
		if VIDEOENH:
			self.sublist.append(QuickSubMenuEntryComponent("VideoEnhancement", _("VideoEnhancement Setup"), _("VideoEnhancement Setup")))

		self["sublist"].l.setList(self.sublist)

######## Tuner Menu ##############################
	def Qtuner(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Tuner Configuration", _("Setup tuner(s)"), _("Setup each tuner for your satellite system")))
		if POSSETUP:
			self.sublist.append(QuickSubMenuEntryComponent("Positioner Setup", _("Setup rotor"), _("Setup your positioner for your satellite system")))
		self.sublist.append(QuickSubMenuEntryComponent("Automatic Scan", _("Automatic Service Searching"), _("Automatic scan for services")))
		self.sublist.append(QuickSubMenuEntryComponent("Manual Scan", _("Manual Service Searching"), _("Manual scan for services")))
		if SATFINDER:
			self.sublist.append(QuickSubMenuEntryComponent("Sat Finder", _("Search Sats"), _("Search Sats, check signal and lock")))
		self["sublist"].l.setList(self.sublist)

######## Software Manager Menu ##############################
	def Qsoftware(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Software Update", _("Online software update"), _("Check/Install online updates (you must have a working Internet connection)")))
		self.sublist.append(QuickSubMenuEntryComponent("Flash Online", _("Flash Online a new image"), _("Flash on the fly your your Receiver software.")))
		self.sublist.append(QuickSubMenuEntryComponent("Complete Backup", _("Backup your current image"), _("Backup your current image to HDD or USB. This will make a 1:1 copy of your box")))
		self.sublist.append(QuickSubMenuEntryComponent("Backup Settings", _("Backup your current settings"), _("Backup your current settings. This includes E2-setup, channels, network and all selected files")))
		self.sublist.append(QuickSubMenuEntryComponent("Restore Settings", _("Restore settings from a backup"), _("Restore your settings back from a backup. After restore the box will restart to activated the new settings")))
		self.sublist.append(QuickSubMenuEntryComponent("Show Default Backup Files", _("Show files backed up by default"), _("Here you can browse (but not modify) the files that are added to the backupfile by default (E2-setup, channels, network).")))
		self.sublist.append(QuickSubMenuEntryComponent("Select Additional Backup Files", _("Select additional files to backup"), _("Here you can specify additional files that should be added to the backup file.")))
		self.sublist.append(QuickSubMenuEntryComponent("Select Excluded Backup Files", _("Select files to exclude from backup"), _("Here you can select which files should be excluded from the backup.")))
		self.sublist.append(QuickSubMenuEntryComponent("Software Manager Settings", _("Manage your online update files"), _("Here you can select which files should be updated with a online update")))
		self["sublist"].l.setList(self.sublist)

######## Plugins Menu ##############################
	def Qplugin(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Plugin Browser", _("Open the Plugin Browser"), _("Shows Plugins Browser. Here you can setup installed Plugin")))
		self.sublist.append(QuickSubMenuEntryComponent("Download Plugins", _("Download and install Plugins"), _("Shows available plugins. Here you can download and install them")))
		self.sublist.append(QuickSubMenuEntryComponent("Remove Plugins", _("Delete Plugins"), _("Delete and uninstall Plugins. This will remove the Plugin from your box")))
		self.sublist.append(QuickSubMenuEntryComponent("Plugin Filter Settings", _("Setup Plugin filter"), _("Setup Plugin filter. Here you can select which Plugins are showed in the PluginBrowser")))
		self.sublist.append(QuickSubMenuEntryComponent("IPK Installer", _("Install Local Extension"), _("Scan for local extensions and install them")))
		self["sublist"].l.setList(self.sublist)

######## Harddisk Menu ##############################
	def Qharddisk(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Harddisk Setup", _("Harddisk Setup"), _("Setup your Harddisk")))
		self.sublist.append(QuickSubMenuEntryComponent("Initialization", _("Format HDD"), _("Format your hard drive")))
		self.sublist.append(QuickSubMenuEntryComponent("File System Check", _("Check HDD"), _("Filesystem check your hard drive")))
		if isFileSystemSupported("ext4"):
			self.sublist.append(QuickSubMenuEntryComponent("Convert ext3 to ext4", _("Convert file system ext3 to ext4"), _("Convert file system ext3 to ext4")))
		self["sublist"].l.setList(self.sublist)

	def ok(self):
		if self.menu > 0:
			self.okSubList()
		else:
			self.goRight()


#####################################################################
######## Make Selection MAIN MENU LIST ##############################
#####################################################################

	def okList(self):
		item = self["list"].getCurrent()

######## Select Network Menu ##############################
		if item[0] == _("Network"):
			self.GetNetworkInterfaces()
			self.Qnetwork()
######## Select System Setup Menu ##############################
		elif item[0] == _("System"):
			self.Qsystem()
######## Select Mount Menu ##############################
		elif item[0] == _("Mounts"):
			self.Qmount()
######## Select Softcam Menu ##############################
		elif item[0] == _("Softcam"):
			self.Qsoftcam()
######## Select AV Setup Menu ##############################
		elif item[0] == _("AV Setup"):
			self.Qavsetup()
######## Select Tuner Setup Menu ##############################
		elif item[0] == _("Tuner Setup"):
			self.Qtuner()
######## Select Software Manager Menu ##############################
		elif item[0] == _("Software Manager"):
			self.Qsoftware()
######## Select PluginDownloadBrowser Menu ##############################
		elif item[0] == _("Plugins"):
			self.Qplugin()
######## Select Tuner Setup Menu ##############################
		elif item[0] == _("Harddisk"):
			self.Qharddisk()

		self["sublist"].selectionEnabled(0)

#####################################################################
######## Make Selection SUB MENU LIST ##############################
#####################################################################

	def okSubList(self):
		item = self["sublist"].getCurrent()

######## Select Network Menu ##############################
		if item[0] == _("Network Wizard"):
			from Plugins.SystemPlugins.NetworkWizard.NetworkWizard import NetworkWizard
			self.session.open(NetworkWizard)
		elif item[0] == _("Network Adapter Selection"):
			self.session.open(NetworkAdapterSelection)
		elif item[0] == _("Network Interface"):
			self.session.open(AdapterSetup, self.activeInterface)
		elif item[0] == _("Network Restart"):
			self.session.open(RestartNetwork)
		elif item[0] == _("Network Services"):
			self.Qnetworkservices()
			self["sublist"].moveToIndex(0)
		elif item[0] == _("Samba"):
			self.session.open(NetworkSamba)
		elif item[0] == _("NFS"):
			self.session.open(NetworkNfs)
		elif item[0] == _("FTP"):
			self.session.open(NetworkFtp)
		elif item[0] == _("AFP"):
			self.session.open(NetworkAfp)
		elif item[0] == _("OpenVPN"):
			self.session.open(NetworkOpenvpn)
		elif item[0] == _("MiniDLNA"):
			self.session.open(NetworkMiniDLNA)
		elif item[0] == _("Inadyn"):
			self.session.open(NetworkInadyn)
		elif item[0] == _("SABnzbd"):
			self.session.open(NetworkSABnzbd)
		elif item[0] == _("SATPI"):
			self.session.open(NetworkSATPI)
		elif item[0] == _("uShare"):
			self.session.open(NetworkuShare)
		elif item[0] == _("Telnet"):
			self.session.open(NetworkTelnet)
######## Select System Setup Menu ##############################
		elif item[0] == _("Customize"):
			self.openSetup("Usage")
		elif item[0] == _("Button Setup"):
			self.openSetup("RemoteButton")
		elif item[0] == _("Display Settings"):
			self.openSetup("Display")
		elif item[0] == _("LCD Skin Settings"):
			self.session.open(LcdSkinSelector)
		elif item[0] == _("Skin Settings"):
			self.session.open(SkinSelector)
		elif item[0] == _("OSD Settings"):
			self.openSetup("UserInterface")
		elif item[0] == _("Channel selection"):
			self.openSetup("ChannelSelection")
		elif item[0] == _("Recording Settings"):
			self.openSetup("Recording")
		elif item[0] == _("EPG Settings"):
			self.openSetup("EPG")
######## Select Mounts Menu ##############################
		elif item[0] == _("Mount Manager"):
			from Plugins.SystemPlugins.NetworkBrowser.MountManager import AutoMountManager
			plugin_path_networkbrowser = eEnv.resolve("${libdir}/enigma2/python/Plugins/SystemPlugins/NetworkBrowser")
			self.session.open(AutoMountManager, None, plugin_path_networkbrowser)
		elif item[0] == _("Network Browser"):
			from Plugins.SystemPlugins.NetworkBrowser.NetworkBrowser import NetworkBrowser
			plugin_path_networkbrowser = eEnv.resolve("${libdir}/enigma2/python/Plugins/SystemPlugins/NetworkBrowser")
			self.session.open(NetworkBrowser, None, plugin_path_networkbrowser)
		elif item[0] == _("Device Manager"):
			self.session.open(HddMount)
######## Select Softcam Menu ##############################
		elif item[0] == _("Softcam Settings"):
			self.session.open(SoftcamSetup)
		elif item[0] == _("OScam Information"):
			self.session.open(OscamInfoMenu)
		elif item[0] == _("CCcam Information"):
			self.session.open(CCcamInfoMain)
		elif item[0] == _("Download Softcams"):
			self.session.open(ShowSoftcamPackages)
######## Select AV Setup Menu ##############################
		elif item[0] == _("Video Settings"):
			self.session.open(VideoSetup)
		elif item[0] == _("Audio Settings"):
			self.openSetup("Audio")
		elif item[0] == _("Auto Language"):
			self.openSetup("AutoLanguage")
		elif item[0] == _("Audio Sync"):
			from Plugins.Extensions.AudioSync.AC3setup import AC3LipSyncSetup
			plugin_path_audiosync = eEnv.resolve("${libdir}/enigma2/python/Plugins/Extensions/AudioSync")
			self.session.open(AC3LipSyncSetup, plugin_path_audiosync)
		elif item[0] == _("VideoEnhancement"):
			from Plugins.SystemPlugins.VideoEnhancement.plugin import VideoEnhancementSetup
			self.session.open(VideoEnhancementSetup)
######## Select TUNER Setup Menu ##############################
		elif item[0] == _("Tuner Configuration"):
			self.session.open(NimSelection)
		elif item[0] == _("Positioner Setup"):
			self.PositionerMain()
		elif item[0] == _("Automatic Scan"):
			self.session.open(ScanSimple)
		elif item[0] == _("Manual Scan"):
			self.session.open(ScanSetup)
		elif item[0] == _("Sat Finder"):
			self.SatfinderMain()
######## Select Software Manager Menu ##############################
		elif item[0] == _("Software Update"):
			from Screens.SoftwareUpdate import SoftwareUpdate
			self.session.open(SoftwareUpdate)
		elif item[0] == _("Flash Online"):
			from Screens.FlashManager import FlashManager
			self.session.open(FlashManager)
		elif item[0] == _("Complete Backup"):
			self.CompleteBackup()
		elif item[0] == _("Backup Settings"):
			self.session.openWithCallback(self.backupDone, BackupScreen, runBackup=True)
		elif item[0] == _("Restore Settings"):
			self.backuppath = getBackupPath()
			if not isdir(self.backuppath):
				self.backuppath = getOldBackupPath()
			self.backupfile = getBackupFilename()
			self.fullbackupfilename = self.backuppath + "/" + self.backupfile
			if exists(self.fullbackupfilename):
				self.session.openWithCallback(self.startRestore, MessageBox, _("Are you sure you want to restore your %s %s backup?\nSTB will restart after the restore") % getBoxDisplayName(), default=False)
			else:
				self.session.open(MessageBox, _("Sorry no backups found!"), MessageBox.TYPE_INFO, timeout=10)
		elif item[0] == _("Show Default Backup Files"):
			self.session.open(BackupSelection, title=_("Default files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs_default, readOnly=True, mode="backupfiles")
		elif item[0] == _("Select Additional Backup Files"):
			self.session.open(BackupSelection, title=_("Additional files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs, readOnly=False, mode="backupfiles_addon")
		elif item[0] == _("Select Excluded Backup Files"):
			self.session.open(BackupSelection, title=_("Files/folders to exclude from backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs_exclude, readOnly=False, mode="backupfiles_exclude")
		elif item[0] == _("Software Manager Settings"):
			self.session.open(SoftwareManagerSetup)
######## Select PluginDownloadBrowser Menu ##############################
		elif item[0] == _("Plugin Browser"):
			self.session.open(PluginBrowser)
		elif item[0] == _("Download Plugins"):
			self.session.open(PluginDownloadBrowser, 0)
		elif item[0] == _("Remove Plugins"):
			self.session.open(PluginDownloadBrowser, 1)
		elif item[0] == _("Plugin Filter Settings"):
			self.session.open(PluginFilter)
		elif item[0] == _("IPK Installer"):
			try:
				from Plugins.Extensions.MediaScanner.plugin import main
				main(self.session)
			except:
				self.session.open(MessageBox, _("Sorry MediaScanner is not installed!"), MessageBox.TYPE_INFO, timeout=10)
######## Select Harddisk Menu ############################################
		elif item[0] == _("Harddisk Setup"):
			self.openSetup("HardDisk")
		elif item[0] == _("Initialization"):
			self.session.open(HarddiskSelection)
		elif item[0] == _("File System Check"):
			self.session.open(HarddiskFsckSelection)
		elif item[0] == _("Convert ext3 to ext4"):
			self.session.open(HarddiskConvertExt4Selection)

######## OPEN SETUP MENUS ####################
	def openSetup(self, dialog):
		self.session.openWithCallback(self.menuClosed, Setup, dialog)

	def menuClosed(self, *res):
		pass

######## NETWORK TOOLS #######################
	def GetNetworkInterfaces(self):
		self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getAdapterList()]

		if not self.adapters:
			self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getConfiguredAdapters()]

		if len(self.adapters) == 0:
			self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getInstalledAdapters()]

		self.activeInterface = None

		for x in self.adapters:
			if iNetwork.getAdapterAttribute(x[1], 'up') is True:
				self.activeInterface = x[1]
				return

######## TUNER TOOLS #######################
	def PositionerMain(self):
		nimList = nimmanager.getNimListOfType("DVB-S")
		if len(nimList) == 0:
			self.session.open(MessageBox, _("No positioner capable frontend found."), MessageBox.TYPE_ERROR)
		else:
			if len(NavigationInstance.instance.getRecordings(False, pNavigation.isAnyRecording)) > 0:
				self.session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to configure the positioner."), MessageBox.TYPE_ERROR)
			else:
				usableNims = []
				for x in nimList:
					configured_rotor_sats = nimmanager.getRotorSatListForNim(x)
					if len(configured_rotor_sats) != 0:
						usableNims.append(x)
				if len(usableNims) == 1:
					from Plugins.SystemPlugins.PositionerSetup.plugin import PositionerSetup
					self.session.open(PositionerSetup, usableNims[0])
				elif len(usableNims) > 1:
					from Plugins.SystemPlugins.PositionerSetup.plugin import RotorNimSelection
					self.session.open(RotorNimSelection)
				else:
					self.session.open(MessageBox, _("No tuner is configured for use with a DiSEqC positioner!"), MessageBox.TYPE_ERROR)

	def SatfinderMain(self):
		if len(NavigationInstance.instance.getRecordings(False, pNavigation.isAnyRecording)) > 0:
			self.session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to start the satellite finder."), MessageBox.TYPE_ERROR)
		else:
			from Plugins.SystemPlugins.Satfinder.plugin import Satfinder
			self.session.open(Satfinder)

######## SOFTWARE MANAGER TOOLS #######################
	def backupDone(self, retval=None):
		if retval is True:
			self.session.open(MessageBox, _("Backup done."), MessageBox.TYPE_INFO, timeout=10)
		else:
			self.session.open(MessageBox, _("Backup failed."), MessageBox.TYPE_INFO, timeout=10)

	def startRestore(self, ret=False):
		if (ret == True):
			self.exe = True
			self.session.open(RestoreScreen, runRestore=True)

	def CompleteBackup(self):
		if DFLASH:
			from Plugins.Extensions.dFlash.plugin import dFlash
			self.session.open(dFlash)
		elif DBACKUP:
			from Plugins.Extensions.dBackup.plugin import dBackup
			self.session.open(dBackup)
		else:
			from Plugins.SystemPlugins.SoftwareManager.ImageBackup import ImageBackup
			self.session.open(ImageBackup)


######## Create MENULIST format #######################
def QuickMenuEntryComponent(name, description, long_description=None, width=540):
	pngname = name.replace(" ", "_")
	png = LoadPixmap("/usr/share/enigma2/icons/" + pngname + ".png")
	if png is None:
		png = LoadPixmap("/usr/share/enigma2/icons/default.png")

	sf = getSkinFactor()
	return [
		_(name),
		MultiContentEntryText(pos=(60 * sf, 2 * sf), size=((width - 60) * sf, 28 * sf), font=0, text=_(name)),
		MultiContentEntryText(pos=(60 * sf, 25 * sf), size=((width - 60) * sf, 22 * sf), font=1, text=_(description)),
		MultiContentEntryPixmapAlphaBlend(pos=(10 * sf, 5 * sf), size=(40 * sf, 40 * sf), flags=BT_SCALE, png=png),
		MultiContentEntryText(pos=(0, 0), size=(0, 0), font=0, text=_(long_description))
	]


def QuickSubMenuEntryComponent(name, description, long_description=None, width=540):
	sf = getSkinFactor()
	return [
		_(name),
		MultiContentEntryText(pos=(10 * sf, 2 * sf), size=((width - 10) * sf, 28 * sf), font=0, text=_(name)),
		MultiContentEntryText(pos=(10 * sf, 25 * sf), size=((width - 10) * sf, 22 * sf), font=1, text=_(description)),
		MultiContentEntryText(pos=(0, 0), size=(0, 0), font=0, text=_(long_description))
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
		<screen name="QuickMenuDevices" position="center,center" size="840,525" title="Devices" flags="wfBorder">
		<widget source="devicelist" render="Listbox" position="30,46" size="780,450" font="Regular;16" scrollbarMode="showOnDemand" transparent="1" backgroundColorSelected="grey" foregroundColorSelected="black">
		<convert type="TemplatedMultiContent">
				{"template": [
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
	</screen> """

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Devices"))
		self['lab1'] = Label()
		self.devicelist = []
		self['devicelist'] = List(self.devicelist)

		self['actions'] = ActionMap(['WizardActions'],
		{
			'back': self.close,
		})
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.updateList2)
		self.updateList()

	def updateList(self, result=None, retval=None, extra_args=None):
		scanning = _("Wait please while scanning for devices...")
		self['lab1'].setText(scanning)
		self.activityTimer.start(10)

	def updateList2(self):
		self.activityTimer.stop()
		self.devicelist = []

		def swapCallback(data, retVal, extraArgs):
			list2 = []
			swapdevices = data.replace('\n', '').split('/')
			f = open('/proc/partitions', 'r')
			for line in f.readlines():
				parts = line.strip().split()
				if not parts:
					continue
				device = parts[3]
				if not search(r'^sd[a-z][1-9][\d]*$', device):
					continue
				if device in list2:
					continue
				self.buildMy_rec(device, swapdevices)
				list2.append(device)

			f.close()
			self['devicelist'].list = self.devicelist
			if len(self.devicelist) == 0:
				self['lab1'].setText(_("No Devices Found !!"))
			else:
				self['lab1'].hide()

		self.Console = Console()
		self.Console.ePopen("sfdisk -l /dev/sd? | grep swap | awk '{print $(NF-9)}'", swapCallback)

	def buildMy_rec(self, device, swapdevices):
		device2 = sub(r'[\d]', '', device)  # strip device number
		devicetype = realpath('/sys/block/' + device2 + '/device')
		name = 'USB: '
		mypixmap = '/usr/share/enigma2/icons/dev_usbstick.png'
		model = open('/sys/block/' + device2 + '/device/model').read()
		model = str(model).replace('\n', '')
		des = ''
		if devicetype.find('/devices/pci') != -1:
			name = _("HARD DISK: ")
			mypixmap = '/usr/share/enigma2/icons/dev_hdd.png'
		name = name + model

		f = open('/proc/mounts', 'r')
		for line in f.readlines():
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
					dtype = 'swap'
					rw = _("None")
					break
				else:
					d1 = _("None")
					dtype = _("unavailable")
					rw = _("None")
		f.close()
		f = open('/proc/partitions', 'r')
		for line in f.readlines():
			if line.find(device) != -1:
				parts = line.strip().split()
				size = int(parts[2])
			else:
				try:
					size = open('/sys/block/' + device2 + '/' + device + '/size').read()
					size = str(size).replace('\n', '')
					size = int(size)
					size = size // 2
				except:
					size = 0

			if ((size / 1024) / 1024) > 1:
				des = "%s: %s %s" % (_("Size"), str((size // 1024) // 1024), _("GB"))
			else:
				des = "%s: %s %s" % (_("Size"), str(size // 1024), _("MB"))

		f.close()
		if des != '':
			if rw.startswith('rw'):
				rw = ' R/W'
			elif rw.startswith('ro'):
				rw = ' R/O'
			else:
				rw = ""
			des += '\t' + _("Mount: ") + d1 + '\n' + _("Device: ") + ' /dev/' + device + '\t' + _("Type: ") + dtype + rw
			png = LoadPixmap(mypixmap)
			res = (name, des, png)
			self.devicelist.append(res)
