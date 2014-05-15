from enigma import eListboxPythonMultiContent, gFont, eEnv, RT_HALIGN_CENTER, RT_HALIGN_RIGHT, RT_WRAP
from boxbranding import getMachineBrand, getMachineName, getBoxType

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
from Screens.ScanSetup import ScanSimple, ScanSetup
from Screens.Satconfig import NimSelection
from Screens.Setup import Setup, getSetupTitle
from Screens.HarddiskSetup import HarddiskSelection, HarddiskFsckSelection, HarddiskConvertExt4Selection
from Screens.SkinSelector import SkinSelector, LcdSkinSelector

from Plugins.Plugin import PluginDescriptor
from Plugins.SystemPlugins.NetworkBrowser.MountManager import AutoMountManager
from Plugins.SystemPlugins.NetworkBrowser.NetworkBrowser import NetworkBrowser
from Plugins.SystemPlugins.NetworkWizard.NetworkWizard import NetworkWizard
from Screens.VideoMode import VideoSetup

from Plugins.SystemPlugins.SoftwareManager.plugin import UpdatePlugin, SoftwareManagerSetup
from Plugins.SystemPlugins.SoftwareManager.BackupRestore import BackupScreen, RestoreScreen, BackupSelection, getBackupPath, getBackupFilename

from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_SKIN_IMAGE, SCOPE_SKIN
from Tools.LoadPixmap import LoadPixmap

from os import path
from time import sleep
from re import search

import NavigationInstance

plugin_path_networkbrowser = eEnv.resolve("${libdir}/enigma2/python/Plugins/SystemPlugins/NetworkBrowser")

if path.exists("/usr/lib/enigma2/python/Plugins/SystemPlugins/PositionerSetup"):
	from Plugins.SystemPlugins.PositionerSetup.plugin import PositionerSetup, RotorNimSelection
	HAVE_POSITIONERSETUP = True
else:
	HAVE_POSITIONERSETUP = False

if path.exists("/usr/lib/enigma2/python/Plugins/SystemPlugins/SatFinder"):
	from Plugins.SystemPlugins.Satfinder.plugin import Satfinder
	HAVE_SATFINDER = True
else:
	HAVE_SATFINDER = False

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

if path.exists("/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/plugin.pyo"):
	from Plugins.SystemPlugins.Blindscan.plugin import Blindscan
	BLINDSCAN = True
else:
	BLINDSCAN = False
	
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
		<eLabel position="21,567" size="300,3" zPosition="3" backgroundColor="red" />
		<eLabel position="325,567" size="300,3" zPosition="3" backgroundColor="green" />
		<eLabel position="630,567" size="300,3" zPosition="3" backgroundColor="yellow" />
		<eLabel position="935,567" size="234,3" zPosition="3" backgroundColor="blue" />
		</screen> """
	
	ALLOW_SUSPEND = True
	
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Setup"))

		self["key_red"] = Label(_("Exit"))
		self["key_green"] = Label()
		self["key_yellow"] = Label()
		self["key_blue"] = Label()
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
				self["description"].setText(_(item[0][1]))
				self.okList()

	def selectionSubChanged(self):
		if self.selectedList == self["sublist"]:
			item = self["sublist"].getCurrent()
			if item:
				self["description"].setText(_(item[0][1]))

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
		if self.menu <> 0:
			self.goLeft()
		else:
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
		self.list.append(GeneralSetupEntryComponent("System",_("System setup"),_("Set up your system"), ">"))
		self.list.append(GeneralSetupEntryComponent("Antenna",_("Set up tuner"),_("Set up your tuner and search for channels"), ">"))
		self.list.append(GeneralSetupEntryComponent("TV",_("Set up basic TV options"),_("Set up your TV options"), ">"))
		self.list.append(GeneralSetupEntryComponent("Media",_("Set up pictures, music and movies"),_("Set up picture, music and movie player"), ">"))
		#self.list.append(GeneralSetupEntryComponent("Mounts",_("Mount Setup"),_("Set up your mounts for network")))
		self.list.append(GeneralSetupEntryComponent("Network",_("Set up your local network"),_("Set up your local network. For WLAN you need to boot with a USB-WLAN stick"), ">"))
		self.list.append(GeneralSetupEntryComponent("Storage",_("Hard disk setup"),_("Set up your hard disk"), ">"))
		self.list.append(GeneralSetupEntryComponent("Plugins",_("Download plugins"),_("Show download and install available plugins"), ">"))
		self.list.append(GeneralSetupEntryComponent("Software Manager",_("Update/Backup/Restore"),_("Update firmware. Backup / restore settings"), ">"))
		self["list"].l.setList(self.list)

######## TV Setup Menu ##############################
	def Qtv(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Channel selection",_("Channel selection configuration"),_("Set up your channel selection configuration")))
		self.sublist.append(QuickSubMenuEntryComponent("Recording settings",_("Recording Setup"),_("Set up your recording configuration")))
		self.sublist.append(QuickSubMenuEntryComponent("Timeshift settings",_("Timeshift Setup"),_("Set up your timeshift configuration")))
		self.sublist.append(QuickSubMenuEntryComponent("Subtitle settings",_("Subtitle Setup"),_("Set up subtitle behaviour")))
		self.sublist.append(QuickSubMenuEntryComponent("EPG settings",_("EPG Setup"),_("Set up your EPG configuration")))
		if getMachineBrand() == "GI":
			self.sublist.append(QuickSubMenuEntryComponent("Common Interface",_("Common Interface configuration"),_("Active/reset and manage your CI")))
		self.sublist.append(QuickSubMenuEntryComponent("Parental control",_("Lock/unlock channels"),_("Set up parental controls")))
		self.sublist.append(QuickSubMenuEntryComponent("Zap history",_("List of last zapped channels"),_("Set up zap (channel change) history")))
		self["sublist"].l.setList(self.sublist)
		
######## System Setup Menu ##############################
	def Qsystem(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("AV setup",_("Set up video mode"),_("Set up your video mode, video output and other video settings")))
		self.sublist.append(QuickSubMenuEntryComponent("GUI setup",_("Set up GUI"),_("Customize UI personal settings")))
		self.sublist.append(QuickSubMenuEntryComponent("OSD settings",_("On screen display"),_("Configure your OSD (on screen display) settings")))
		self.sublist.append(QuickSubMenuEntryComponent("Button settings",_("Button assignment"),_("Set up your buttons")))
		if getMachineBrand() == "GI":
			self.sublist.append(QuickSubMenuEntryComponent("Language settings",_("Setup your language"),_("Set up menu language")))
		self.sublist.append(QuickSubMenuEntryComponent("Time settings",_("Time settings"),_("Set up date and time")))
		if SystemInfo["FrontpanelDisplay"] and SystemInfo["Display"]:
			self.sublist.append(QuickSubMenuEntryComponent("Front panel settings",_("Front panel setup"),_("Set up your front panel")))
		if SystemInfo["GraphicLCD"]: 
			self.sublist.append(QuickSubMenuEntryComponent("Display skin",_("Skin setup"),_("Set up your display skin")))
		if SystemInfo["Fan"]: 
			self.sublist.append(QuickSubMenuEntryComponent("Fan settings",_("Fan setup"),_("Set up your fan")))
		self.sublist.append(QuickSubMenuEntryComponent("Factory reset",_("Load default"),_("Reset all settings to defaults")))
		self["sublist"].l.setList(self.sublist)

######## Network Menu ##############################
	def Qnetwork(self):
		self.sublist = []
		#self.sublist.append(QuickSubMenuEntryComponent("Network Wizard",_("Configure your Network"),_("Use the Networkwizard to configure your Network. The wizard will help you to setup your network")))
		#if len(self.adapters) > 1: # show only adapter selection if more as 1 adapter is installed, no need as eth0 is always present
		self.sublist.append(QuickSubMenuEntryComponent("Network Adapter Selection",_("Select LAN/WLAN"),_("Set up your network interface. If no USB WLAN stick is present, you can only select LAN")))
		if not self.activeInterface == None: # show only if there is already an adapter up
			self.sublist.append(QuickSubMenuEntryComponent("Network Interface",_("Setup interface"),_("Setup network. Here you can setup DHCP, IP, DNS")))
		self.sublist.append(QuickSubMenuEntryComponent("Network Restart",_("Restart network with current setup"),_("Restart network and remount connections")))
		self.sublist.append(QuickSubMenuEntryComponent("Network Services",_("Setup Network Services"),_("Set up network services (Samba, FTP, NFS, ...)")))
		# test
		self.sublist.append(QuickSubMenuEntryComponent("Mount Manager",_("Manage network mounts"),_("Set up your network mounts")))
		self.sublist.append(QuickSubMenuEntryComponent("Network Browser",_("Search for network shares"),_("Search for network shares")))
		self["sublist"].l.setList(self.sublist)

#### Network Services Menu ##############################
	def Qnetworkservices(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Samba",_("Set up Samba"),_("Set up Samba")))
		self.sublist.append(QuickSubMenuEntryComponent("NFS",_("Set up NFS"),_("Set up NFS")))
		self.sublist.append(QuickSubMenuEntryComponent("FTP",_("Set up FTP"),_("Set up FTP")))
		#self.sublist.append(QuickSubMenuEntryComponent("AFP",_("Set up AFP"),_("Set up AFP")))
		#self.sublist.append(QuickSubMenuEntryComponent("OpenVPN",_("Set up OpenVPN"),_("Set up OpenVPN")))
		self.sublist.append(QuickSubMenuEntryComponent("DLNA Server",_("Set up MiniDLNA"),_("Set up MiniDLNA")))
		self.sublist.append(QuickSubMenuEntryComponent("DYN-DNS",_("Set up Inadyn"),_("Set up Inadyn")))
		#self.sublist.append(QuickSubMenuEntryComponent("SABnzbd",_("Set up SABnzbd"),_("Set up SABnzbd")))
		#self.sublist.append(QuickSubMenuEntryComponent("uShare",_("Set up uShare"),_("Set up uShare")))
		self.sublist.append(QuickSubMenuEntryComponent("Telnet",_("Set up Telnet"),_("Set up Telnet")))
		self["sublist"].l.setList(self.sublist)

######## Mount Settings Menu ##############################
	def Qmount(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Mount Manager",_("Manage network mounts"),_("Set up your network mounts")))
		self.sublist.append(QuickSubMenuEntryComponent("Network Browser",_("Search for network shares"),_("Search for network shares")))
		#self.sublist.append(QuickSubMenuEntryComponent("Device Manager",_("Mounts devices"),_("Set up your device mounts (USB, HDD, others...)")))
		self["sublist"].l.setList(self.sublist)

######## Media Menu ##############################
	def Qmedia(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Picture Player",_("Set up picture player"),_("Configure timeout, thumbnails, etc. for picture slide show")))
		self.sublist.append(QuickSubMenuEntryComponent("Media Player",_("Set up media player"),_("Manage play lists, sorting, repeat")))
		self["sublist"].l.setList(self.sublist)

######## A/V Settings Menu ##############################
	def Qavsetup(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("AV Settings",_("Set up video mode"),_("Set up your video mode, video output and other video settings")))
		if AUDIOSYNC == True:
			self.sublist.append(QuickSubMenuEntryComponent("Audio Sync",_("Set up Audio Sync"),_("Set up audio sync settings")))
		self.sublist.append(QuickSubMenuEntryComponent("Auto Language",_("Auto Language Selection"),_("Select your Language for audio/subtitles")))
		if os_path.exists("/proc/stb/vmpeg/0/pep_apply") and VIDEOENH == True:
			self.sublist.append(QuickSubMenuEntryComponent("VideoEnhancement",_("Video enhancement setup"),_("Video enhancement setup")))
		if AUTORES == True:
			self.sublist.append(QuickSubMenuEntryComponent("AutoResolution",_("Auto resolution setup"),_("Automatically change resolution")))
		if config.usage.setup_level.getValue() == "expert":
			self.sublist.append(QuickSubMenuEntryComponent("OSD Position",_("Adjust OSD Size"),_("Adjust OSD (on screen display) size")))
		if SystemInfo["CanChange3DOsd"]:
			self.sublist.append(QuickSubMenuEntryComponent("OSD 3D Setup",_("OSD 3D mode and depth"),_("Adjust 3D OSD (on screen display) mode and depth")))
		self.sublist.append(QuickSubMenuEntryComponent("Skin Setup",_("Choose menu skin"),_("Choose user interface skin")))
		self.sublist.append(QuickSubMenuEntryComponent("HDMI-CEC",_("Consumer Electronics Control"),_("Control up to ten CEC-enabled devices connected through HDMI")))

		self["sublist"].l.setList(self.sublist)

######## Tuner Menu ##############################
	def Qtuner(self):
		dvbs_nimList = nimmanager.getNimListOfType("DVB-S")
		dvbt_nimList = nimmanager.getNimListOfType("DVB-T")
		self.sublist = []
		if len(dvbs_nimList) != 0:
			self.sublist.append(QuickSubMenuEntryComponent("Tuner Configuration",_("Setup tuner(s)"),_("Setup each tuner for your satellite system")))
			self.sublist.append(QuickSubMenuEntryComponent("Automatic Scan",_("Service Searching"),_("Automatic scan for services")))
		if len(dvbt_nimList) != 0:
			self.sublist.append(QuickSubMenuEntryComponent("Location Scan",_("Automatic Location Scan"),_("Automatic scan for services based on your location")))
		self.sublist.append(QuickSubMenuEntryComponent("Manual Scan",_("Service Searching"),_("Manual scan for services")))
		if HAVE_POSITIONERSETUP and len(dvbs_nimList) != 0:
			self.sublist.append(QuickSubMenuEntryComponent("Positioner Setup",_("Set up rotor"),_("Set up positioner for your satellite system")))
		if BLINDSCAN == True and len(dvbs_nimList) != 0:
			self.sublist.append(QuickSubMenuEntryComponent("Blind Scan",_("Blind Searching"),_("Blind scan for services")))
		if HAVE_SATFINDER and len(dvbs_nimList) != 0:
			self.sublist.append(QuickSubMenuEntryComponent("Sat Finder",_("Search Sats"),_("Search Sats, check signal and lock")))
		self["sublist"].l.setList(self.sublist)

######## Software Manager Menu ##############################
	def Qsoftware(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Software Update",_("Online software update"),_("Check/install online updates (you must have a working Internet connection)")))
		#self.sublist.append(QuickSubMenuEntryComponent("Complete Backup",_("Backup your current image"),_("Backup your current image to HDD or USB. This will make a 1:1 copy of your box")))
		self.sublist.append(QuickSubMenuEntryComponent("Backup Settings",_("Backup your current settings"),_("Backup your current settings. This includes setup, channels, network and all files selected using the settings below")))
		self.sublist.append(QuickSubMenuEntryComponent("Select Backup files",_("Choose the files to backup"),_("Here you can select which files should be added to the backup option above. (default: setup, channels, network")))
		self.sublist.append(QuickSubMenuEntryComponent("Restore Settings",_("Restore settings from a backup"),_("Restore your settings from a backup. After restore the box will reboot in order to activate the new settings")))
		self["sublist"].l.setList(self.sublist)

######## Plugins Menu ##############################
	def Qplugin(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Plugin Browser",_("Open the plugin browser"),_("Shows plugins browser, where you can configure installed plugins")))
		self.sublist.append(QuickSubMenuEntryComponent("Download Plugins",_("Download and install plugins"),_("Shows available plugins or download and install new ones")))
		self.sublist.append(QuickSubMenuEntryComponent("Remove Plugins",_("Delete plugins"),_("Delete and uninstall plugins.")))
		self.sublist.append(QuickSubMenuEntryComponent("Package Installer",_("Install local extension"),_("Scan HDD and USB media for local extensions and install them")))
		self["sublist"].l.setList(self.sublist)

######## Harddisk Menu ##############################
	def Qharddisk(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Hard disk setup",_("Hard disk setup"),_("Configure hard disk options, such as standby timeout")))
		self.sublist.append(QuickSubMenuEntryComponent("Format hard disk",_("Format HDD"),_("Format your hard disk")))
		self.sublist.append(QuickSubMenuEntryComponent("File system check",_("Check HDD"),_("Check the integrity of the file system on your hard disk")))
# 		if isFileSystemSupported("ext4"):
# 			self.sublist.append(QuickSubMenuEntryComponent("Convert ext3 to ext4",_("Convert file system from ext3 to ext4"),_("Convert file system from ext3 to ext4")))
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
		selected = item[0][0]

######## Select Network Menu ##############################
		if selected == _("Network"):
			self.GetNetworkInterfaces()
			self.Qnetwork()
######## Select System Setup Menu ##############################
		elif selected == _("System"):
			self.Qsystem()
######## Select TV Setup Menu ##############################
		elif selected == _("TV"):
			self.Qtv()
######## Select Mount Menu ##############################
		elif selected == _("Mounts"):
			self.Qmount()
######## Select Media Menu ##############################
		elif selected == _("Media"):
			self.Qmedia()
######## Select AV Setup Menu ##############################
		elif selected == _("AV setup"):
			self.Qavsetup()
######## Select Tuner Setup Menu ##############################
		elif selected == _("Antenna"):
			self.Qtuner()
######## Select Software Manager Menu ##############################
		elif selected == _("Software Manager"):
			self.Qsoftware()
######## Select Plugins Menu ##############################
		elif selected == _("Plugins"):
			self.Qplugin()
######## Select Storage Setup Menu ##############################
		elif selected == _("Storage"):
			self.Qharddisk()
		self["sublist"].selectionEnabled(0)

#####################################################################
######## Make Selection SUB MENU LIST ##############################
#####################################################################
			
	def okSubList(self):
		item = self["sublist"].getCurrent()
		selected = item[0][0]

######## Select Network Menu ##############################
		if selected == _("Network Wizard"):
			self.session.open(NetworkWizard)
		elif selected == _("Network Adapter Selection"):
			self.session.open(NetworkAdapterSelection)
		elif selected == _("Network Interface"):
			self.session.open(AdapterSetup,self.activeInterface)
		elif selected == _("Network Restart"):
			self.session.open(RestartNetwork)
		elif selected == _("Network Services"):
			self.Qnetworkservices()
			self["sublist"].moveToIndex(0)
		elif selected == _("Samba"):
			self.session.open(NetworkSamba)
		elif selected == _("NFS"):
			self.session.open(NetworkNfs)
		elif selected == _("FTP"):
			self.session.open(NetworkFtp)
		elif selected == _("AFP"):
			self.session.open(NetworkAfp)
		elif selected == _("OpenVPN"):
			self.session.open(NetworkOpenvpn)
		elif selected == _("DLNA Server"):
			self.session.open(NetworkMiniDLNA)
		elif selected == _("DYN-DNS"):
			self.session.open(NetworkInadyn)
# 		elif selected == _("SABnzbd"):
# 			self.session.open(NetworkSABnzbd)
		elif selected == _("uShare"):
			self.session.open(NetworkuShare)
		elif selected == _("Telnet"):
			self.session.open(NetworkTelnet)
######## Select AV Setup Menu ##############################
		elif selected == _("AV setup"):
			self.Qavsetup()
######## Select System Setup Menu ##############################
		elif selected == _("GUI setup"):
			self.openSetup("usage")
		elif selected == _("Time settings"):
			self.openSetup("time")
		elif selected == _("Language settings"):
			self.session.open(LanguageSelection)
		elif selected == _("Front panel settings"):
			self.openSetup("display")
		elif selected == _("Skin Setup"):
			self.session.open(SkinSelector)
		elif selected == _("Display skin"):
			self.session.open(LcdSkinSelector)
		elif selected == _("OSD settings"):
			self.openSetup("userinterface")
		elif selected == _("Button settings"):
			self.openSetup("remotesetup")
		elif selected == _("HDMI-CEC"):
			from Plugins.SystemPlugins.HdmiCEC.plugin import HdmiCECSetupScreen
			self.session.open(HdmiCECSetupScreen)  
		elif selected == _("Fan settings"):
			from Plugins.SystemPlugins.FanControl.plugin import FanSetupScreen
			self.session.open(FanSetupScreen)
		elif selected == _("Factory reset"):
			from Screens.FactoryReset import FactoryReset

			def deactivateInterfaceCB(data):
				if data is True:
					applyConfigDataAvail(True)

			def activateInterfaceCB(self, data):
				if data is True:
					iNetwork.activateInterface("eth0", applyConfigDataAvail)

			def applyConfigDataAvail(data):
				if data is True:
					iNetwork.getInterfaces(getInterfacesDataAvail)

			def getInterfacesDataAvail(data):
				if data is True:
					pass
		
			def msgClosed(ret):
				if ret:
					from os import system, _exit
					system("rm -rf /etc/enigma2")
					system("rm -rf /etc/network/interfaces")
					system("rm -rf /etc/wpa_supplicant.ath0.conf")
					system("rm -rf /etc/wpa_supplicant.wlan0.conf")
					system("rm -rf /etc/wpa_supplicant.conf")
					system("cp -a /usr/share/enigma2/defaults /etc/enigma2")
					system("/usr/bin/showiframe /usr/share/backdrop.mvi")
					iNetwork.setAdapterAttribute("eth0", "up", True)
					iNetwork.setAdapterAttribute("eth0", "dhcp", True)
					iNetwork.activateInterface("eth0", deactivateInterfaceCB)
					iNetwork.writeNetworkConfig()
					_exit(2)	# We want a full reboot to ensure new hostname is picked up 
			self.session.openWithCallback(msgClosed, FactoryReset)  
######## Select TV Setup Menu ##############################
		elif selected == _("Channel selection"):
			self.openSetup("channelselection")
		elif selected == _("Recording settings"):
			from Screens.Recordings import RecordingSettings
			self.session.open(RecordingSettings)
		elif selected == _("Timeshift settings"):
			from Screens.Timershift import TimeshiftSettings
			self.session.open(TimeshiftSettings)
		elif selected == _("Subtitle settings"):
			self.openSetup("subtitlesetup")
		elif selected == _("EPG settings"):
			self.openSetup("epgsettings")
		elif selected == _("Common Interface"):
			from Screens.Ci import CiSelection
			self.session.open(CiSelection)
		elif selected == _("Parental control"):
			from Screens.ParentalControlSetup import ParentalControlSetup
			self.session.open(ParentalControlSetup)
		elif selected == _("Zap history"):
			from Plugins.Extensions.IniZapHistoryBrowser.plugin import ZapHistoryConfigurator
			self.session.open(ZapHistoryConfigurator)
######## Select Mounts Menu ##############################
		elif selected == _("Mount Manager"):
			self.session.open(AutoMountManager, None, plugin_path_networkbrowser)
		elif selected == _("Network Browser"):
			self.session.open(NetworkBrowser, None, plugin_path_networkbrowser)
		#elif selected == _("Device Manager"):
		#	self.session.open(HddMount)
######## Select Media Menu ##############################
		elif selected == _("Picture Player"):
			from Plugins.Extensions.PicturePlayer.ui import Pic_Setup
			self.session.open(Pic_Setup)
		elif selected == _("Media Player"):
			from Plugins.Extensions.MediaPlayer.settings import MediaPlayerSettings
			self.session.open(MediaPlayerSettings, self)
######## Select AV Setup Menu ##############################
		elif selected == _("AV Settings"):
			self.session.open(VideoSetup)
		elif selected == _("Auto Language"):
			self.openSetup("autolanguagesetup")
		elif selected == _("Audio Sync"):
			self.session.open(AC3LipSyncSetup, plugin_path_audiosync)
		elif selected == _("VideoEnhancement"):
			self.session.open(VideoEnhancementSetup)
		elif selected == _("AutoResolution"):
			self.session.open(AutoResSetupMenu)
		elif selected == _("OSD Position"):
			from Screens.UserInterfacePositioner import UserInterfacePositioner
			self.session.open(UserInterfacePositioner)
		elif selected == _("OSD 3D Setup"):
			from Screens.UserInterfacePositioner import OSD3DSetupScreen
			self.session.open(OSD3DSetupScreen)
######## Select TUNER Setup Menu ##############################
		elif selected == _("Location Scan"):
			from Screens.IniTerrestrialLocation import IniTerrestrialLocation
			self.session.open(IniTerrestrialLocation)
		elif selected == _("Tuner Configuration"):
			self.session.open(NimSelection)
		elif HAVE_POSITIONERSETUP and selected == _("Positioner Setup"):
			self.PositionerMain()
		elif selected == _("Automatic Scan"):
			self.session.open(ScanSimple)
		elif selected == _("Manual Scan"):
			self.session.open(ScanSetup)
		elif selected == _("Blind Scan"):
			self.session.open(Blindscan)
		elif HAVE_SATFINDER and selected == _("Sat Finder"):
			self.SatfinderMain()
######## Select Software Manager Menu ##############################
		elif selected == _("Software Update"):
			self.session.open(UpdatePlugin)
		elif selected == _("Backup Settings"):
			self.session.openWithCallback(self.backupDone,BackupScreen, runBackup = True)
		elif selected == _("Restore Settings"):
			self.backuppath = getBackupPath()
			if not path.isdir(self.backuppath):
				self.backuppath = getBackupPath()
			self.backupfile = getBackupFilename()
			self.fullbackupfilename = self.backuppath + "/" + self.backupfile
			if os_path.exists(self.fullbackupfilename):
				self.session.openWithCallback(self.startRestore, MessageBox, _("Are you sure you want to restore your %s %s backup?\n"
					"Your %s %s will reboot after the restore") % (getMachineBrand(), getMachineName(), getMachineBrand(), getMachineName()))
			else:
				self.session.open(MessageBox, _("Sorry no backups found!"), MessageBox.TYPE_INFO, timeout = 10)
		elif selected == _("Select Backup files"):
			self.session.openWithCallback(self.backupfiles_choosen,BackupSelection)
		#elif selected == _("Software Manager Setup"):
		#	self.session.open(SoftwareManagerSetup)
######## Select PluginDownloadBrowser Menu ##############################
		elif selected == _("Plugin Browser"):
			self.session.open(PluginBrowser)
		elif selected == _("Download Plugins"):
			self.session.open(PluginDownloadBrowser, 0)
		elif selected == _("Remove Plugins"):
			self.session.open(PluginDownloadBrowser, 1)
		elif selected == _("Package Installer"):
			try:
				from Plugins.Extensions.MediaScanner.plugin import main
				main(self.session)
			except:
				self.session.open(MessageBox, _("Sorry MediaScanner is not installed!"), MessageBox.TYPE_INFO, timeout = 10)
######## Select Harddisk Menu ############################################
		elif selected == _("Hard disk setup"):
			self.openSetup("harddisk")
		elif selected == _("Format hard disk"):
			self.session.open(HarddiskSelection)
		elif selected == _("File system check"):
			self.session.open(HarddiskFsckSelection)
		elif selected == _("Convert ext3 to ext4"):
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


######## TUNER TOOLS #######################
	if HAVE_POSITIONERSETUP:
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

	if HAVE_SATFINDER:
		def SatfinderMain(self):
			nims = nimmanager.getNimListOfType("DVB-S")
	
			nimList = []
			for x in nims:
				if nimmanager.getNimConfig(x).configMode.value in ("loopthrough", "satposdepends", "nothing"):
					continue
				if nimmanager.getNimConfig(x).configMode.value == "advanced" and len(nimmanager.getSatListForNim(x)) < 1:
					continue
				nimList.append(x)
	
			if len(nimList) == 0:
				self.session.open(MessageBox, _("No satellites configured. Plese check your tuner setup."), MessageBox.TYPE_ERROR)
			else:
				if self.session.nav.RecordTimer.isRecording():
					self.session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to start the satfinder."), MessageBox.TYPE_ERROR)
				else:
					self.session.open(Satfinder)


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
		
######## Create MENULIST format #######################
def GeneralSetupEntryComponent(name, description, long_description = None, endtext=">", width=540):
	return [
		(_(name), _(long_description)),
		MultiContentEntryText(pos=(20, 10), size=(width-120, 35), font=0, text = _(name)),
		#MultiContentEntryText(pos=(20, 26), size=(width-120, 17), font=1, text = _(description)),
		MultiContentEntryText(pos=(20, 26), size=(0,0), font=1, text = _(description)),
		MultiContentEntryText(pos=(350, 10), size=(35, 35), text = ">")
	]

def QuickSubMenuEntryComponent(name, description, long_description = None, width=540):
	return [
		(_(name), _(long_description)),
		#MultiContentEntryText(pos=(20, 5), size=(width-10, 25), font=0, text = _(name)),
		MultiContentEntryText(pos=(20, 15), size=(width-10, 25), font=0, text = _(name)),		
		#MultiContentEntryText(pos=(20, 26), size=(width-10, 17), font=1, text = _(description)),
		MultiContentEntryText(pos=(20, 26), size=(0, 0), font=1, text = _(description))
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
