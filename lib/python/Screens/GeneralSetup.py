from enigma import eListboxPythonMultiContent, gFont, eEnv, RT_HALIGN_CENTER, RT_HALIGN_RIGHT, RT_WRAP

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Network import iNetwork
from Components.NimManager import nimmanager
from Components.SystemInfo import SystemInfo

from Screens.Screen import Screen
from Screens.NetworkSetup import *
from Screens.About import About
from Screens.PluginBrowser import PluginDownloadBrowser, PluginBrowser
from Screens.LanguageSelection import LanguageSelection
from Screens.Satconfig import NimSelection
from Screens.ScanSetup import ScanSimple, ScanSetup
from Screens.Setup import Setup, getSetupTitle
from Screens.HarddiskSetup import HarddiskSelection, HarddiskFsckSelection, HarddiskConvertExt4Selection
from Screens.SkinSelector import LcdSkinSelector

from Plugins.Plugin import PluginDescriptor
from Plugins.SystemPlugins.PositionerSetup.plugin import PositionerSetup, RotorNimSelection
from Plugins.SystemPlugins.Satfinder.plugin import Satfinder, SatNimSelection
from Plugins.SystemPlugins.NetworkBrowser.MountManager import AutoMountManager
from Plugins.SystemPlugins.NetworkBrowser.NetworkBrowser import NetworkBrowser
from Plugins.SystemPlugins.NetworkWizard.NetworkWizard import NetworkWizard
from Plugins.SystemPlugins.Videomode.plugin import VideoSetup
from Plugins.SystemPlugins.Videomode.VideoHardware import video_hw

from Plugins.SystemPlugins.SoftwareManager.plugin import UpdatePlugin, SoftwareManagerSetup
from Plugins.SystemPlugins.SoftwareManager.BackupRestore import BackupScreen, RestoreScreen, BackupSelection, getBackupPath, getBackupFilename

from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_SKIN_IMAGE, SCOPE_SKIN
from Tools.LoadPixmap import LoadPixmap

from os import path
from time import sleep
from re import search

import NavigationInstance

plugin_path_networkbrowser = eEnv.resolve("${libdir}/enigma2/python/Plugins/SystemPlugins/NetworkBrowser")

if path.exists("/usr/lib/enigma2/python/Plugins/Extensions/AudioSync"):
	from Plugins.Extensions.AudioSync.AC3setup import AC3LipSyncSetup
	plugin_path_audiosync = eEnv.resolve("${libdir}/enigma2/python/Plugins/Extensions/AudioSync")
	AUDIOSYNC = True
else:
	AUDIOSYNC = False

if path.exists("/usr/lib/enigma2/python/Plugins/SystemPlugins/VideoEnhancement/plugin.pyo"):
	from Plugins.SystemPlugins.VideoEnhancement.plugin import VideoEnhancementSetup
	VIDEOENH = True
else:
	VIDEOENH = False

if path.exists("/usr/lib/enigma2/python/Plugins/SystemPlugins/AutoResolution/plugin.pyo"):
	from Plugins.SystemPlugins.AutoResolution.plugin import AutoResSetupMenu
	AUTORES = True
else:
	AUTORES = False

if path.exists("/usr/lib/enigma2/python/Plugins/Extensions/dFlash"):
	from Plugins.Extensions.dFlash.plugin import dFlash
	DFLASH = True
else:
	DFLASH = False

def isFileSystemSupported(filesystem):
	try:
		for fs in open('/proc/filesystems', 'r'):
			if fs.strip().endswith(filesystem):
				return True
		return False
	except Exception, ex:
		print "[Harddisk] Failed to read /proc/filesystems:", ex

class GeneralSetup(Screen):
	skin = """
		<screen name="GeneralSetup" position="center,center" size="1180,600" backgroundColor="black" flags="wfBorder">
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
		Screen.setTitle(self, _("Setup"))

		self["key_red"] = Label(_("Exit"))
		#self["key_green"] = Label(_("System Info"))
		#self["key_yellow"] = Label(_("Service Info"))
		#self["key_blue"] = Label(_("Memory Info"))
		self["description"] = Label()

		self.menu = 0
		self.list = []
		self["list"] = GeneralSetupList(self.list)
		self.sublist = []
		self["sublist"] = GeneralSetupSubList(self.sublist)
		self.selectedList = []
		self.onChangedEntry = []
		self["list"].onSelectionChanged.append(self.selectionChanged)
		self["sublist"].onSelectionChanged.append(self.selectionSubChanged)

		self["actions"] = ActionMap(["SetupActions","WizardActions","MenuActions","MoviePlayerActions"],
		{
			"ok": self.ok,
			"back": self.keyred,
			"cancel": self.keyred,
			"left": self.goLeft,
			"right": self.goRight,
			"up": self.goUp,
			"down": self.goDown,
		}, -1)


		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
			"red": self.keyred,
			#"green": self.keygreen,
			#"yellow": self.keyyellow,
			#"blue": self.keyblue,
			})

		self.MainQmenu()
		self.selectedList = self["list"]
		self.selectionChanged()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["sublist"].selectionEnabled(0)

	def selectionChanged(self):
		if self.selectedList == self["list"]:
			item = self["list"].getCurrent()
			if item:
				self["description"].setText(_(item[4]))
				self.okList()

	def selectionSubChanged(self):
		if self.selectedList == self["sublist"]:
			item = self["sublist"].getCurrent()
			if item:
				self["description"].setText(_(item[3]))

	def goLeft(self):
		if self.menu <> 0:
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
		self.session.open(About)

	def keyyellow(self):
		from Screens.ServiceInfo import ServiceInfo
		self.session.open(ServiceInfo)

	def keyblue(self):
		from Screens.About import Devices
		self.session.open(Devices)
		
######## Main Menu ##############################
	def MainQmenu(self):
		self.menu = 0
		self.list = []
		self.oldlist = []
		self.list.append(GeneralSetupEntryComponent("System",_("System Setup"),_("Setup your System"), ">"))
		#self.list.append(GeneralSetupEntryComponent("Mounts",_("Mount Setup"),_("Setup your mounts for network")))
		self.list.append(GeneralSetupEntryComponent("Network",_("Setup your local network"),_("Setup your local network. For Wlan you need to boot with a USB-Wlan stick"), ">"))
		self.list.append(GeneralSetupEntryComponent("Antena Setup",_("Setup Tuner"),_("Setup your Tuner and search for channels"), ">"))
		self.list.append(GeneralSetupEntryComponent("TV",_("Setup basic TV options"),_("Setup Your TV options"), ">"))
		self.list.append(GeneralSetupEntryComponent("Media",_("Setup Pictures / music / movies"),_("Setup picture, music and movie player"), ">"))
		self.list.append(GeneralSetupEntryComponent("Plugins",_("Download plugins"),_("Shows available pluigns. Here you can download and install them"), ">"))
		self.list.append(GeneralSetupEntryComponent("Storage",_("Harddisk Setup"),_("Setup your Harddisk"), ">"))
		self.list.append(GeneralSetupEntryComponent("Software Manager",_("Update/Backup/Restore your box"),_("Update/Backup your firmware, Backup/Restore settings"), ">"))		
		self["list"].l.setList(self.list)

######## TV Setup Menu ##############################
	def Qtv(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Channel selection",_("Channel selection configuration"),_("Setup your Channel selection configuration")))
		self.sublist.append(QuickSubMenuEntryComponent("Recording settings",_("Recording Setup"),_("Setup your recording config")))
		self.sublist.append(QuickSubMenuEntryComponent("Timeshift settings",_("Timeshift Setup"),_("Setup your timeshift config")))
		self.sublist.append(QuickSubMenuEntryComponent("Subtitles settings",_("Subtitles Setup"),_("Setup subtitles behaviour")))
		self.sublist.append(QuickSubMenuEntryComponent("EPG settings",_("EPG Setup"),_("Setup your EPG config")))
		self.sublist.append(QuickSubMenuEntryComponent("Common Interface",_("Common Interface configuration"),_("Active/reset and manage your CI")))
		self.sublist.append(QuickSubMenuEntryComponent("Parental Control",_("Lock/unlock channels"),_("Setup parental control lock")))
		self.sublist.append(QuickSubMenuEntryComponent("Zap History",_("List of last zapped channels"),_("Setup zap history")))
		self["sublist"].l.setList(self.sublist)
		
######## System Setup Menu ##############################
	def Qsystem(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("AV Setup",_("Setup Videomode"),_("Setup your Video Mode, Video Output and other Video Settings")))
		self.sublist.append(QuickSubMenuEntryComponent("GUI Setup",_("Setup GUI"),_("Customize UI personal settings")))
		self.sublist.append(QuickSubMenuEntryComponent("OSD settings",_("Settings..."),_("Setup your OSD")))
		self.sublist.append(QuickSubMenuEntryComponent("Language Settings",_("Setup Your language"),_("Setup menu language")))
		self.sublist.append(QuickSubMenuEntryComponent("Time Settings",_("Time Settings"),_("Setup date and time")))
		if SystemInfo["FrontpanelDisplay"] and SystemInfo["Display"]:
			self.sublist.append(QuickSubMenuEntryComponent("Display Settings",_("Display Setup"),_("Setup your display")))
		if SystemInfo["LcdDisplay"]:
			self.sublist.append(QuickSubMenuEntryComponent("LCD Skin Setup",_("Skin Setup"),_("Setup your LCD")))
		self.sublist.append(QuickSubMenuEntryComponent("HDMI-CEC",_("Consumer Electronics Control"),_("Control up to ten CEC-enabled devices connected through HDMI")))
		self.sublist.append(QuickSubMenuEntryComponent("Factory Reset",_("Load default"),_("Reset all settings to defaults one")))
		self["sublist"].l.setList(self.sublist)

######## Network Menu ##############################
	def Qnetwork(self):
		self.sublist = []
		#self.sublist.append(QuickSubMenuEntryComponent("Network Wizard",_("Configure your Network"),_("Use the Networkwizard to configure your Network. The wizard will help you to setup your network")))
		if len(self.adapters) > 1: # show only adapter selection if more as 1 adapter is installed
			self.sublist.append(QuickSubMenuEntryComponent("Network Adapter Selection",_("Select Lan/Wlan"),_("Setup your network interface. If no Wlan stick is used, you only can select Lan")))
		if not self.activeInterface == None: # show only if there is already a adapter up
			self.sublist.append(QuickSubMenuEntryComponent("Network Interface",_("Setup interface"),_("Setup network. Here you can setup DHCP, IP, DNS")))
		self.sublist.append(QuickSubMenuEntryComponent("Network Restart",_("Restart network to with current setup"),_("Restart network and remount connections")))
		self.sublist.append(QuickSubMenuEntryComponent("Network Services",_("Setup Network Services"),_("Setup Network Services (Samba, Ftp, NFS, ...)")))
		# test
		self.sublist.append(QuickSubMenuEntryComponent("Mount Manager",_("Manage network mounts"),_("Setup your network mounts")))
		self.sublist.append(QuickSubMenuEntryComponent("Network Browser",_("Search for network shares"),_("Search for network shares")))
		self["sublist"].l.setList(self.sublist)

#### Network Services Menu ##############################
	def Qnetworkservices(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Samba",_("Setup Samba"),_("Setup Samba")))
		self.sublist.append(QuickSubMenuEntryComponent("NFS",_("Setup NFS"),_("Setup NFS")))
		self.sublist.append(QuickSubMenuEntryComponent("FTP",_("Setup FTP"),_("Setup FTP")))
		#self.sublist.append(QuickSubMenuEntryComponent("AFP",_("Setup AFP"),_("Setup AFP")))
		#self.sublist.append(QuickSubMenuEntryComponent("OpenVPN",_("Setup OpenVPN"),_("Setup OpenVPN")))
		self.sublist.append(QuickSubMenuEntryComponent("DLNA Server",_("Setup MiniDLNA"),_("Setup MiniDLNA")))
		self.sublist.append(QuickSubMenuEntryComponent("DYN-DNS",_("Setup Inadyn"),_("Setup Inadyn")))
		#self.sublist.append(QuickSubMenuEntryComponent("SABnzbd",_("Setup SABnzbd"),_("Setup SABnzbd")))
		#self.sublist.append(QuickSubMenuEntryComponent("uShare",_("Setup uShare"),_("Setup uShare")))
		#self.sublist.append(QuickSubMenuEntryComponent("Telnet",_("Setup Telnet"),_("Setup Telnet")))
		self["sublist"].l.setList(self.sublist)

######## Mount Settings Menu ##############################
	def Qmount(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Mount Manager",_("Manage network mounts"),_("Setup your network mounts")))
		self.sublist.append(QuickSubMenuEntryComponent("Network Browser",_("Search for network shares"),_("Search for network shares")))
		#self.sublist.append(QuickSubMenuEntryComponent("Device Manager",_("Mounts Devices"),_("Setup your Device mounts (USB, HDD, others...)")))
		self["sublist"].l.setList(self.sublist)

######## Media Menu ##############################
	def Qmedia(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Picture Player",_("Setup picture player"),_("Configure timeout, thumbnails for picture slideshow")))
		self.sublist.append(QuickSubMenuEntryComponent("Media Player",_("Setup media player"),_("Here You can manage playlists, sorting, repeat")))
		self.sublist.append(QuickSubMenuEntryComponent("Movie Browser",_("Setup movie player"),_("Setup database, covers, and style of Movie Browser")))
		self.sublist.append(QuickSubMenuEntryComponent("Music Browser",_("Setup music player"),_("Setup database, covers, and style of MP3 Browser")))
		self["sublist"].l.setList(self.sublist)

######## A/V Settings Menu ##############################
	def Qavsetup(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("AV Settings",_("Setup Videomode"),_("Setup your Video Mode, Video Output and other Video Settings")))
		if AUDIOSYNC == True:
			self.sublist.append(QuickSubMenuEntryComponent("Audio Sync",_("Setup Audio Sync"),_("Setup Audio Sync settings")))
		self.sublist.append(QuickSubMenuEntryComponent("Auto Language",_("Auto Language Selection"),_("Select your Language for Audio/Subtitles")))
		if os_path.exists("/proc/stb/vmpeg/0/pep_apply") and VIDEOENH == True:
			self.sublist.append(QuickSubMenuEntryComponent("VideoEnhancement",_("VideoEnhancement Setup"),_("VideoEnhancement Setup")))
		if AUTORES == True:
			self.sublist.append(QuickSubMenuEntryComponent("AutoResolution",_("AutoResolution Setup"),_("Automatically change resolution")))

		self["sublist"].l.setList(self.sublist)

######## Tuner Menu ##############################
	def Qtuner(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Tuner Configuration",_("Setup tuner(s)"),_("Setup each tuner for your satellite system")))
		self.sublist.append(QuickSubMenuEntryComponent("Positioner Setup",_("Setup rotor"),_("Setup your positioner for your satellite system")))
		self.sublist.append(QuickSubMenuEntryComponent("Automatic Scan",_("Service Searching"),_("Automatic scan for services")))
		self.sublist.append(QuickSubMenuEntryComponent("Manual Scan",_("Service Searching"),_("Manual scan for services")))
		self.sublist.append(QuickSubMenuEntryComponent("Sat Finder",_("Search Sats"),_("Search Sats, check signal and lock")))
		self["sublist"].l.setList(self.sublist)

######## Software Manager Menu ##############################
	def Qsoftware(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Software Update",_("Online software update"),_("Check/Install online updates (you must have a working internet connection)")))
		#self.sublist.append(QuickSubMenuEntryComponent("Complete Backup",_("Backup your current image"),_("Backup your current image to HDD or USB. This will make a 1:1 copy of your box")))
		self.sublist.append(QuickSubMenuEntryComponent("Backup Settings",_("Backup your current settings"),_("Backup your current settings. This includes E2-setup, channels, network and all selected files")))
		self.sublist.append(QuickSubMenuEntryComponent("Restore Settings",_("Restore settings from a backup"),_("Restore your settings back from a backup. After restore the box will restart to activated the new settings")))
		self.sublist.append(QuickSubMenuEntryComponent("Select Backup files",_("Choose the files to backup"),_("Here you can select which files should be added to backupfile. (default: E2-setup, channels, network")))
		#self.sublist.append(QuickSubMenuEntryComponent("Software Manager Setup",_("Manage your online update files"),_("Here you can select which files should be updated with a online update")))
		self["sublist"].l.setList(self.sublist)

######## Plugins Menu ##############################
	def Qplugin(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Browser Plugin",_("Open the Plugin Browser"),_("Shows Plugins Browser. Here you can setup installed Plugin")))
		self.sublist.append(QuickSubMenuEntryComponent("Download Plugins",_("Download and install Plugins"),_("Shows available plugins. Here you can download and install them")))
		self.sublist.append(QuickSubMenuEntryComponent("Remove Plugins",_("Delete Plugins"),_("Delete and unstall Plugins. This will remove the Plugin from your box")))
		#self.sublist.append(QuickSubMenuEntryComponent("Plugin Filter",_("Setup Plugin filter"),_("Setup Plugin filter. Here you can select which Plugins are showed in the PluginBrowser")))
		self.sublist.append(QuickSubMenuEntryComponent("Package Installer",_("Install local extension"),_("Scan for local extensions and install them")))
		self["sublist"].l.setList(self.sublist)

######## Harddisk Menu ##############################
	def Qharddisk(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Harddisk Setup",_("Harddisk Setup"),_("Setup your Harddisk")))
		self.sublist.append(QuickSubMenuEntryComponent("Format and Initialize",_("Format HDD"),_("Format your Harddisk")))
		self.sublist.append(QuickSubMenuEntryComponent("Filesystem Check",_("Check HDD"),_("Filesystem check your Harddisk")))
		if isFileSystemSupported("ext4"):
			self.sublist.append(QuickSubMenuEntryComponent("Convert ext3 to ext4",_("Convert filesystem ext3 to ext4"),_("Convert filesystem ext3 to ext4")))
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
######## Select TV Setup Menu ##############################
		elif item[0] == _("TV"):
			self.Qtv()
######## Select Mount Menu ##############################
		elif item[0] == _("Mounts"):
			self.Qmount()
######## Select Media Menu ##############################
		elif item[0] == _("Media"):
			self.Qmedia()
######## Select AV Setup Menu ##############################
		elif item[0] == _("AV Setup"):
			self.Qavsetup()
######## Select Tuner Setup Menu ##############################
		elif item[0] == _("Antena Setup"):
			self.Qtuner()
######## Select Software Manager Menu ##############################
		elif item[0] == _("Software Manager"):
			self.Qsoftware()
######## Select PluginDownloadBrowser Menu ##############################
		elif item[0] == _("Plugins"):
			self.Qplugin()
######## Select Tuner Setup Menu ##############################
		elif item[0] == _("Storage"):
			self.Qharddisk()
		self["sublist"].selectionEnabled(0)

#####################################################################
######## Make Selection SUB MENU LIST ##############################
#####################################################################
			
	def okSubList(self):
		item = self["sublist"].getCurrent()

######## Select Network Menu ##############################
		if item[0] == _("Network Wizard"):
			self.session.open(NetworkWizard)
		elif item[0] == _("Network Adapter Selection"):
			self.session.open(NetworkAdapterSelection)
		elif item[0] == _("Network Interface"):
			self.session.open(AdapterSetup,self.activeInterface)
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
		elif item[0] == _("DLNA Server"):
			self.session.open(NetworkMiniDLNA)
		elif item[0] == _("DYN-DNS"):
			self.session.open(NetworkInadyn)
		elif item[0] == _("SABnzbd"):
			self.session.open(NetworkSABnzbd)
		elif item[0] == _("uShare"):
			self.session.open(NetworkuShare)
		elif item[0] == _("Telnet"):
			self.session.open(NetworkTelnet)
######## Select AV Setup Menu ##############################
		elif item[0] == _("AV Setup"):
			self.Qavsetup()
######## Select System Setup Menu ##############################
		elif item[0] == _("GUI Setup"):
			self.openSetup("usage")
		elif item[0] == _("Time Settings"):
			self.openSetup("time")
		elif item[0] == _("Language Settings"):
			from Screens.LanguageSelection import LanguageSelection
			self.session.open(LanguageSelection)
		elif item[0] == _("Display Settings"):
			self.openSetup("display")
		elif item[0] == _("LCD Skin Setup"):
			self.session.open(LcdSkinSelector)
		elif item[0] == _("OSD settings"):
			self.openSetup("userinterface")
		elif item[0] == _("HDMI-CEC"):
			from Plugins.SystemPlugins.HdmiCEC.plugin import HdmiCECSetupScreen
			self.session.open(HdmiCECSetupScreen)  
		elif item[0] == _("Factory Reset"):
			from Screens.FactoryReset import FactoryReset
			def msgClosed(ret):
				if ret:
					from os import system, _exit
					system("rm -R /etc/enigma2")
					system("cp -R /usr/share/enigma2/defaults /etc/enigma2")
					system("/usr/bin/showiframe /usr/share/backdrop.mvi")
					_exit(0)
			self.session.openWithCallback(msgClosed, FactoryReset)  
######## Select TV Setup Menu ##############################
		elif item[0] == _("Channel selection"):
			self.openSetup("channelselection")
		elif item[0] == _("Recording settings"):
			self.openSetup("recording")
		elif item[0] == _("Timeshift settings"):
			self.openSetup("timeshift")
		elif item[0] == _("Subtitles settings"):
			self.openSetup("subtitlesetup")
		elif item[0] == _("EPG settings"):
			self.openSetup("epgsettings")
		elif item[0] == _("Common Interface"):
			from Screens.Ci import CiSelection
			self.session.open(CiSelection)
		elif item[0] == _("Parental Control"):
			from Screens.ParentalControlSetup import ParentalControlSetup
			self.session.open(ParentalControlSetup)
		elif item[0] == _("Zap History"):
			from Plugins.Extensions.IniZapHistoryBrowser.plugin import ZapHistoryConfigurator
			self.session.open(ZapHistoryConfigurator)
######## Select Mounts Menu ##############################
		elif item[0] == _("Mount Manager"):
			self.session.open(AutoMountManager, None, plugin_path_networkbrowser)
		elif item[0] == _("Network Browser"):
			self.session.open(NetworkBrowser, None, plugin_path_networkbrowser)
		#elif item[0] == _("Device Manager"):
		#	self.session.open(HddMount)
######## Select Media Menu ##############################
		elif item[0] == _("Picture Player"):
			from Plugins.Extensions.PicturePlayer.ui import Pic_Setup
			self.session.open(Pic_Setup)
		elif item[0] == _("Media Player"):
			from Plugins.Extensions.MediaPlayer.settings import MediaPlayerSettings
			self.session.open(MediaPlayerSettings, self)
		elif item[0] == _("Movie Browser"):
			from Plugins.Extensions.MovieBrowser.plugin import movieBrowserConfig
			self.session.open(movieBrowserConfig)  
		elif item[0] == _("Music Browser"):
			from Plugins.Extensions.MP3Browser.plugin import mp3BrowserConfig
			self.session.open(mp3BrowserConfig)  
		#elif item[0] == _("Download Softcams"):
		#	self.session.open(ShowSoftcamPackages)
######## Select AV Setup Menu ##############################
		elif item[0] == _("AV Settings"):
			self.session.open(VideoSetup, video_hw)
		elif item[0] == _("Auto Language"):
			self.openSetup("autolanguagesetup")
		elif item[0] == _("Audio Sync"):
			self.session.open(AC3LipSyncSetup, plugin_path_audiosync)
		elif item[0] == _("VideoEnhancement"):
			self.session.open(VideoEnhancementSetup)
		elif item[0] == _("AutoResolution"):
			self.session.open(AutoResSetupMenu)
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
			self.session.open(UpdatePlugin)
			#self.session.open(SoftwarePanel)
		#elif item[0] == _("Complete Backup"):
		#	if DFLASH == True:
		#		self.session.open(dFlash)
		#	else:
		#		self.session.open(ImageBackup)
		elif item[0] == _("Backup Settings"):
			self.session.openWithCallback(self.backupDone,BackupScreen, runBackup = True)
		elif item[0] == _("Restore Settings"):
			self.backuppath = getBackupPath()
			if not path.isdir(self.backuppath):
				self.backuppath = getOldBackupPath()
			self.backupfile = getBackupFilename()
			self.fullbackupfilename = self.backuppath + "/" + self.backupfile
			if os_path.exists(self.fullbackupfilename):
				self.session.openWithCallback(self.startRestore, MessageBox, _("Are you sure you want to restore your STB_BOX backup?\nSTB will restart after the restore"))
			else:
				self.session.open(MessageBox, _("Sorry no backups found!"), MessageBox.TYPE_INFO, timeout = 10)
		elif item[0] == _("Select Backup files"):
			self.session.openWithCallback(self.backupfiles_choosen,BackupSelection)
		#elif item[0] == _("Software Manager Setup"):
		#	self.session.open(SoftwareManagerSetup)
######## Select PluginDownloadBrowser Menu ##############################
		elif item[0] == _("Browser Plugin"):
			self.session.open(PluginBrowser)
		elif item[0] == _("Download Plugins"):
			self.session.open(PluginDownloadBrowser, 0)
		elif item[0] == _("Remove Plugins"):
			self.session.open(PluginDownloadBrowser, 1)
		elif item[0] == _("Plugin Filter"):
			self.session.open(PluginFilter)
		elif item[0] == _("Package Installer"):
			try:
				from Plugins.Extensions.MediaScanner.plugin import main
				main(self.session)
			except:
				self.session.open(MessageBox, _("Sorry MediaScanner is not installed!"), MessageBox.TYPE_INFO, timeout = 10)
######## Select Harddisk Menu ############################################
		elif item[0] == _("Harddisk Setup"):
			self.openSetup("harddisk")
		elif item[0] == _("Format and Initialize"):
			self.session.open(HarddiskSelection)
		elif item[0] == _("Filesystem Check"):
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
		self.adapters = [(iNetwork.getFriendlyAdapterName(x),x) for x in iNetwork.getAdapterList()]

		if not self.adapters:
			self.adapters = [(iNetwork.getFriendlyAdapterName(x),x) for x in iNetwork.getConfiguredAdapters()]

		if len(self.adapters) == 0:
			self.adapters = [(iNetwork.getFriendlyAdapterName(x),x) for x in iNetwork.getInstalledAdapters()]

		self.activeInterface = None
	
		for x in self.adapters:
			if iNetwork.getAdapterAttribute(x[1], 'up') is True:
				self.activeInterface = x[1]
				return

from Components.Network import iNetwork
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Components.Label import Label

class RestartNetwork(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        skin = """
            <screen name="RestartNetwork" position="center,center" size="600,100" title="Restart Network Adapter">
            <widget name="label" position="10,30" size="500,50" halign="center" font="Regular;20" transparent="1" foregroundColor="white" />
            </screen> """
        self.skin = skin
        self["label"] = Label(_("Please wait while your network is restarting..."))
        self.onShown.append(self.setWindowTitle)
        self.onLayoutFinish.append(self.restartLan)

    def setWindowTitle(self):
        self.setTitle(_("Restart Network Adapter"))

    def restartLan(self):
        iNetwork.restartNetwork(self.restartLanDataAvail)
  
    def restartLanDataAvail(self, data):
        if data is True:
            iNetwork.getInterfaces(self.getInterfacesDataAvail)

    def getInterfacesDataAvail(self, data):
        self.close()
        
        
######## TUNER TOOLS #######################
	def PositionerMain(self):
		nimList = nimmanager.getNimListOfType("DVB-S")
		if len(nimList) == 0:
			self.session.open(MessageBox, _("No positioner capable frontend found."), MessageBox.TYPE_ERROR)
		else:
			if len(NavigationInstance.instance.getRecordings()) > 0:
				self.session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to configure the positioner."), MessageBox.TYPE_ERROR)
			else:
				usableNims = []
				for x in nimList:
					configured_rotor_sats = nimmanager.getRotorSatListForNim(x)
					if len(configured_rotor_sats) != 0:
						usableNims.append(x)
				if len(usableNims) == 1:
					self.session.open(PositionerSetup, usableNims[0])
				elif len(usableNims) > 1:
					self.session.open(RotorNimSelection)
				else:
					self.session.open(MessageBox, _("No tuner is configured for use with a diseqc positioner!"), MessageBox.TYPE_ERROR)

	def SatfinderMain(self):
		nims = nimmanager.getNimListOfType("DVB-S")

		nimList = []
		for x in nims:
			if not nimmanager.getNimConfig(x).configMode.getValue() in ("loopthrough", "satposdepends", "nothing"):
				nimList.append(x)

		if len(nimList) == 0:
			self.session.open(MessageBox, _("No satellite frontend found!!"), MessageBox.TYPE_ERROR)
		else:
			if len(NavigationInstance.instance.getRecordings()) > 0:
				self.session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to start the satfinder."), MessageBox.TYPE_ERROR)
			else:
				if len(nimList) == 1:
					self.session.open(Satfinder, nimList[0])
				else:
					self.session.open(SatNimSelection)

		
######## SOFTWARE MANAGER TOOLS #######################
	def backupfiles_choosen(self, ret):
		config.plugins.configurationbackup.backupdirs.save()
		config.plugins.configurationbackup.save()
		config.save()

	def backupDone(self,retval = None):
		if retval is True:
			self.session.open(MessageBox, _("Backup done."), MessageBox.TYPE_INFO, timeout = 10)
		else:
			self.session.open(MessageBox, _("Backup failed."), MessageBox.TYPE_INFO, timeout = 10)

	def startRestore(self, ret = False):
		if (ret == True):
			self.exe = True
			self.session.open(RestoreScreen, runRestore = True)


######## Create MENULIST format #######################
def GeneralSetupEntryComponent(name, description, long_description = None, endtext=">", width=540):
	return [
		_(name),
		MultiContentEntryText(pos=(20, 10), size=(width-120, 35), font=0, text = _(name)),
		#MultiContentEntryText(pos=(20, 26), size=(width-120, 17), font=1, text = _(description)),
		MultiContentEntryText(pos=(20, 26), size=(0,0), font=1, text = _(description)),
		MultiContentEntryText(pos=(350, 10), size=(35, 35), text = ">"),
		_(long_description),
	]

def QuickSubMenuEntryComponent(name, description, long_description = None, width=540):
	return [
		_(name),
		#MultiContentEntryText(pos=(20, 5), size=(width-10, 25), font=0, text = _(name)),
		MultiContentEntryText(pos=(20, 15), size=(width-10, 25), font=0, text = _(name)),		
		#MultiContentEntryText(pos=(20, 26), size=(width-10, 17), font=1, text = _(description)),
		MultiContentEntryText(pos=(20, 26), size=(0, 0), font=1, text = _(description)),
		_(long_description),
	]

class GeneralSetupList(MenuList):
	def __init__(self, list, enableWrapAround=True):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 28))
		self.l.setFont(1, gFont("Regular", 14))
		self.l.setItemHeight(50)

class GeneralSetupSubList(MenuList):
	def __init__(self, sublist, enableWrapAround=True):
		MenuList.__init__(self, sublist, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setFont(1, gFont("Regular", 14))
		self.l.setItemHeight(50)

		