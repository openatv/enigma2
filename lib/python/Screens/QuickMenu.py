from os.path import exists, isdir, join

from enigma import pNavigation

import NavigationInstance
from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import config
from Components.Label import Label
from Components.Network import iNetwork
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Plugins.SystemPlugins.SoftwareManager.BackupRestore import BackupScreen, BackupSelection, RestoreScreen, getBackupFilename, getBackupPath, getOldBackupPath
from Screens.MessageBox import MessageBox
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.PluginBrowser import PackageAction
from Screens.Screen import Screen
from Screens.Setup import Setup
from Tools.Directories import SCOPE_PLUGINS, SCOPE_SKIN, fileReadLines, isPluginInstalled, resolveFilename
from Tools.LoadPixmap import LoadPixmap

MODULE_NAME = __name__.split(".")[-1]

AUDIOSYNC = isPluginInstalled("AudioSync")
NETWORKBROWSER = isPluginInstalled("NetworkBrowser")
POSSETUP = isPluginInstalled("PositionerSetup")
SATFINDER = isPluginInstalled("Satfinder")
VIDEOENH = isPluginInstalled("VideoEnhancement") and exists("/proc/stb/vmpeg/0/pep_apply")


class QuickMenu(Screen, ProtectedScreen):
	skin = """
	<screen name="QuickMenu" title="Quick Launch Menu" position="center,center" size="1150,500" backgroundColor="#00000000" resolution="1280,720">
		<widget source="mainlist" render="Listbox" position="0,0" size="360,450" backgroundColor="#00000000" itemHeight="50">
			<templates>
				<template name="Default" fonts="Regular;20,Regular;15" itemWidth="360" itemHeight="50">
					<mode name="default">
						<pixmap index="2" position="10,5" size="40,40" alpha="blend" scale="centerScaled"/>
						<text index="0" position="60,0" size="e-70,30" font="0" verticalAlignment="center" />
						<text index="1" position="80,30" size="e-90,20" font="1" verticalAlignment="center" />
					</mode>
				</template>
			</templates>
		</widget>
		<eLabel position="369,0" size="2,450" backgroundColor="#00666666" />
		<widget source="sublist" render="Listbox" position="380,0" size="360,450" backgroundColor="#00000000" itemHeight="50">
			<templates>
				<template name="Default" fonts="Regular;20,Regular;15" itemWidth="380" itemHeight="50">
					<mode name="default">
						<text index="0" position="10,0" size="e-20,30" font="0" verticalAlignment="center" />
						<text index="1" position="30,30" size="e-40,20" font="1" verticalAlignment="center" />
					</mode>
				</template>
			</templates>
		</widget>
		<widget source="session.VideoPicture" render="Pig" position="750,0" size="400,225" backgroundColor="#ff000000" />
		<widget name="description" position="750,245" size="400,205" backgroundColor="#00000000" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="380,e-40" size="180,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True, mandatoryWidgets=["mainlist"])
		ProtectedScreen.__init__(self)
		self.setTitle(_("Quick Launch Menu"))
		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("System Info"))
		self["key_yellow"] = StaticText(_("Devices"))
		self["description"] = Label()
		self["summary_description"] = StaticText("")
		self["mainlist"] = List()
		self["sublist"] = List()
		self["mainlist"].onSelectionChanged.append(self.selectionMainChanged)
		self["sublist"].onSelectionChanged.append(self.selectionSubChanged)
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "NavigationActions", "ColorActions"], {
			"ok": (self.keyOk, _("Select the current menu item")),
			"cancel": (self.close, _("Close this screen")),
			"red": (self.close, _("Close this screen")),
			"green": (self.keyDistributionInformation, _("Open the Image information")),
			"yellow": (self.keyStorageInformation, _("Open the Storage Device information")),
			"top": (self.keyTop, _("Move to first line / screen")),
			"pageUp": (self.keyPageUp, _("Move up a screen")),
			"up": (self.keyLineUp, _("Move up a line")),
			"left": (self.keyLeft, _("Switch to the left column")),
			"right": (self.keyRight, _("Switch to the right column")),
			"down": (self.keyLineDown, _("Move down a line")),
			"pageDown": (self.keyPageDown, _("Move down a screen")),
			"bottom": (self.keyBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Quick Menu Actions"))
		helpStr = _("Direct menu item selection")
		self["numberActions"] = HelpableNumberActionMap(self, ["NumberActions"], {
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
		}, prio=0, description=_("Quick Menu Actions"))
		self.onChangedEntry = []
		self.menu = 0
		self.mainList = []
		self.subList = []
		self.selectedList = self["mainlist"]
		self.showMainMenu()
		self.selectionMainChanged()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["mainlist"].enableAutoNavigation(False)
		self["sublist"].enableAutoNavigation(False)
		self["sublist"].selectionEnabled(False)

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and not config.ParentalControl.config_sections.main_menu.value and config.ParentalControl.config_sections.quickmenu.value

	def selectionMainChanged(self):
		if self.selectedList == self["mainlist"]:
			item = self.mainList[self["mainlist"].getCurrentIndex()]
			self["description"].text = item[4]
			self["summary_description"].text = item[0]
			self.selectMainItem()

	def selectionSubChanged(self):
		if self.selectedList == self["sublist"]:
			item = self.subList[self["sublist"].getCurrentIndex()]
			self["description"].text = item[2]
			self["summary_description"].text = item[0]

	def keyOk(self):
		if self.menu > 0:
			self.selectSubItem()
		else:
			self.keyRight()

	def keyDistributionInformation(self):
		self.openScreen("Information", screenName="DistributionInformation")

	def keyStorageInformation(self):
		self.openScreen("Information", screenName="StorageInformation")

	def keyTop(self):
		self.selectedList.goTop()

	def keyPageUp(self):
		self.selectedList.goPageUp()

	def keyLineUp(self):
		self.selectedList.goLineUp()

	def keyLeft(self):
		if self.menu != 0:
			self.menu = 0
			self.selectedList = self["mainlist"]
			self["mainlist"].selectionEnabled(1)
			self["sublist"].selectionEnabled(0)
			self.selectionMainChanged()

	def keyRight(self):
		if self.menu == 0:
			self.menu = 1
			self.selectedList = self["sublist"]
			self["sublist"].setCurrentIndex(0)
			self["mainlist"].selectionEnabled(0)
			self["sublist"].selectionEnabled(1)
			self.selectionSubChanged()

	def keyLineDown(self):
		self.selectedList.goLineDown()

	def keyPageDown(self):
		self.selectedList.goPageDown()

	def keyBottom(self):
		self.selectedList.goBottom()

	def keyNumberGlobal(self, number):  # Run a numbered shortcut.
		if number and number <= self.selectedList.count():
			self.selectedList.setCurrentIndex(number - 1)
			self.keyOk()

	def showMainMenu(self):  # Main Menu.
		def quickMenuEntryComponent(itemIndex, pngname, name, description, longDescription=None, width=540):
			icon = LoadPixmap(resolveFilename(SCOPE_SKIN, f"icons/{pngname}.png"))
			if icon is None:
				icon = LoadPixmap(resolveFilename(SCOPE_SKIN, "icons/default.png"))
			return (name, description, icon, itemIndex, longDescription)

		self.menu = 0
		self.mainList = []
		self.mainList.append(quickMenuEntryComponent(0, "Software_Manager", _("Software Manager"), _("Update/Backup/Restore your box"), _("Update/Backup your firmware, Backup/Restore settings")))
		if BoxInfo.getItem("SoftCam"):
			self.mainList.append(quickMenuEntryComponent(1, "Softcam", _("Softcam"), _("Start/stop/select cam"), _("Start/stop/select your cam, You need to install first a softcam")))
		self.mainList.append(quickMenuEntryComponent(2, "System", _("System"), _("System Setup"), _("Setup your System")))
		self.mainList.append(quickMenuEntryComponent(3, "Mounts", _("Mounts"), _("Mount Setup"), _("Setup your mounts for network")))
		self.mainList.append(quickMenuEntryComponent(4, "Network", _("Network"), _("Setup your local network"), _("Setup your local network. For Wlan you need to boot with a USB-Wlan stick")))
		self.mainList.append(quickMenuEntryComponent(5, "AV_Setup", _("AV Setup"), _("Setup Video/Audio"), _("Setup your Video Mode, Video Output and other Video Settings")))
		self.mainList.append(quickMenuEntryComponent(6, "Tuner_Setup", _("Tuner Setup"), _("Setup Tuner"), _("Setup your Tuner and search for channels")))
		self.mainList.append(quickMenuEntryComponent(7, "Plugins", _("Plugins"), _("Setup Plugins"), _("Shows available plugins. Here you can download and install them")))
		self.mainList.append(quickMenuEntryComponent(8, "Harddisk", _("Harddisk"), _("Harddisk Setup"), _("Setup your Harddisk")))
		self["mainlist"].setList([(x[0], x[1], x[2]) for x in self.mainList])

	def selectMainItem(self):
		match self.mainList[self["mainlist"].getCurrentIndex()][3]:
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
				self.subMenuAVSetup()
			case 6:
				self.subMenuTuner()
			case 7:
				self.subMenuPlugin()
			case 8:
				self.subMenuHarddisk()
		self["sublist"].selectionEnabled(0)

	def subMenuSoftware(self):  # Software Manager Menu.
		def completeBackupCallback():
			if BoxInfo.getItem("dFlash"):
				from Plugins.Extensions.dFlash.plugin import dFlash
				self.session.open(dFlash)
			elif BoxInfo.getItem("dBackup"):
				from Plugins.Extensions.dBackup.plugin import dBackup
				self.session.open(dBackup)
			else:
				from Screens.ImageBackup import ImageBackup
				self.session.open(ImageBackup)

		def backupSettingsCallback():
			# self.session.openWithCallback(backupDoneCallback, BackupScreen, runBackup=True)
			self.session.open(BackupScreen, runBackup=True, closeOnSuccess=5)

		# def backupDoneCallback(retval=None):
		# 	self.session.open(MessageBox, _("Backup done.") if retval else _("Backup failed!"), MessageBox.TYPE_INFO if retval else MessageBox.TYPE_ERROR, timeout=10, windowTitle=self.getTitle())

		def restoreSettingsCallback():
			backupPath = getBackupPath()
			if not isdir(backupPath):
				backupPath = getOldBackupPath()
			if exists(join(backupPath, getBackupFilename())):
				self.session.openWithCallback(startRestoreCallback, MessageBox, _("Are you sure you want to restore your %s %s backup?\nSTB will restart after the restore") % getBoxDisplayName(), default=False, windowTitle=self.getTitle())
			else:
				self.session.open(MessageBox, _("Sorry no backups found!"), MessageBox.TYPE_INFO, timeout=10, windowTitle=self.getTitle())

		def startRestoreCallback(answer=False):
			if (answer is True):
				self.exe = True
				self.session.open(RestoreScreen, runRestore=True)

		def defaultBackupFilesCallback():
			self.session.open(BackupSelection, title=_("Default files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs_default, readOnly=True, mode="backupfiles")

		def additionalBackupFilesCallback():
			self.session.open(BackupSelection, title=_("Additional files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs, readOnly=False, mode="backupfiles_addon")

		def excludedBackupFilesCallback():
			self.session.open(BackupSelection, title=_("Files/folders to exclude from backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs_exclude, readOnly=False, mode="backupfiles_exclude")

		self.subList = []
		self.subList.append(self.quickSubMenuEntryComponent(_("Software Update"), _("Online software update"), _("Check/Install online updates (you must have a working Internet connection)"), screen="SoftwareUpdate"))
		self.subList.append(self.quickSubMenuEntryComponent(_("Flash Online"), _("Flash Online a new image"), _("Flash on the fly your your Receiver software."), screen="FlashManager"))
		self.subList.append(self.quickSubMenuEntryComponent(_("Complete Backup"), _("Backup your current image"), _("Backup your current image to HDD or USB. This will make a 1:1 copy of your box"), callback=completeBackupCallback))
		self.subList.append(self.quickSubMenuEntryComponent(_("Backup Settings"), _("Backup your current settings"), _("Backup your current settings. This includes E2-setup, channels, network and all selected files"), callback=backupSettingsCallback))
		self.subList.append(self.quickSubMenuEntryComponent(_("Restore Settings"), _("Restore settings from a backup"), _("Restore your settings back from a backup. After restore the box will restart to activated the new settings"), callback=restoreSettingsCallback))
		self.subList.append(self.quickSubMenuEntryComponent(_("Show Default Backup Files"), _("Show files backed up by default"), _("Here you can browse (but not modify) the files that are added to the backupfile by default (E2-setup, channels, network)."), callback=defaultBackupFilesCallback))
		self.subList.append(self.quickSubMenuEntryComponent(_("Select Additional Backup Files"), _("Select additional files to backup"), _("Here you can specify additional files that should be added to the backup file."), callback=additionalBackupFilesCallback))
		self.subList.append(self.quickSubMenuEntryComponent(_("Select Excluded Backup Files"), _("Select files to exclude from backup"), _("Here you can select which files should be excluded from the backup."), callback=excludedBackupFilesCallback))
		self.subList.append(self.quickSubMenuEntryComponent(_("Software Manager Settings"), _("Manage your online update files"), _("Here you can select which files should be updated with a online update"), setup="SoftwareManager"))
		self.setSubList()

	def subMenuSoftcam(self):  # Softcam Menu.
		def downloadSoftcams():
			self.session.open(PackageAction, PackageAction.MODE_SOFTCAM)

		self.subList = []
		if BoxInfo.getItem("SoftCam"):  # Show only when there is a softcam installed.
			self.subList.append(self.quickSubMenuEntryComponent(_("Softcam Settings"), _("Control your Softcams"), _("Use the Softcam Panel to control your Cam. This let you start/stop/select a cam"), screen="SoftcamSetup"))
			if BoxInfo.getItem("ShowOscamInfo"):  # Show only when oscam or ncam is active.
				self.subList.append(self.quickSubMenuEntryComponent(_("OSCam Information"), _("Show OSCam Information"), _("Show the OSCam information screen"), screen="OScamInfo", screenName="OSCamInfo"))
			if BoxInfo.getItem("ShowCCCamInfo"):  # Show only when CCcam is active.
				self.subList.append(self.quickSubMenuEntryComponent(_("CCcam Information"), _("Show CCcam Info"), _("Show the CCcam Info Screen"), screen="CCcamInfo", screenName="CCcamInfoMain"))
		self.subList.append(self.quickSubMenuEntryComponent(_("Download Softcams"), _("Download and install cam"), _("Shows available softcams. Here you can download and install them"), callback=downloadSoftcams))
		self.setSubList()

	def subMenuSystem(self):  # System Setup Menu.
		self.subList = []
		self.subList.append(self.quickSubMenuEntryComponent(_("Customize"), _("Setup Enigma2"), _("Customize enigma2 personal settings"), setup="Usage"))
		self.subList.append(self.quickSubMenuEntryComponent(_("OSD Settings"), _("OSD Setup"), _("Setup your OSD"), setup="UserInterface"))
		self.subList.append(self.quickSubMenuEntryComponent(_("Button Setup"), _("Button Setup"), _("Setup your remote buttons"), setup="RemoteButton"))
		if BoxInfo.getItem("FrontpanelDisplay") and BoxInfo.getItem("Display"):
			self.subList.append(self.quickSubMenuEntryComponent(_("Display Settings"), _("Setup your LCD"), _("Setup your display"), setup="Display"))
		self.subList.append(self.quickSubMenuEntryComponent(_("Skin Settings"), _("Select Enigma2 Skin"), _("Setup your Skin"), screen="SkinSelection"))
		self.subList.append(self.quickSubMenuEntryComponent(_("Channel Selection"), _("Channel selection configuration"), _("Setup your Channel selection configuration"), setup="ChannelSelection"))
		self.subList.append(self.quickSubMenuEntryComponent(_("Recording Settings"), _("Recording Setup"), _("Setup your recording config"), setup="Recording"))
		self.subList.append(self.quickSubMenuEntryComponent(_("EPG Settings"), _("EPG Setup"), _("Setup your EPG config"), setup="EPG"))
		self.setSubList()

	def subMenuMount(self):  # Mount Settings Menu.
		def mountManager():
			from Plugins.SystemPlugins.NetworkBrowser.MountManager import AutoMountManager
			self.session.open(AutoMountManager, None, resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkBrowser"))

		def networkBrowser():
			from Plugins.SystemPlugins.NetworkBrowser.NetworkBrowser import NetworkBrowser
			self.session.open(NetworkBrowser, None, resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkBrowser"))

		self.subList = []
		if NETWORKBROWSER:
			self.subList.append(self.quickSubMenuEntryComponent(_("Mount Manager"), _("Manage network mounts"), _("Setup your network mounts"), callback=mountManager))
			self.subList.append(self.quickSubMenuEntryComponent(_("Network Browser"), _("Search for network shares"), _("Search for network shares"), callback=networkBrowser))
		self.setSubList()

	def subMenuNetwork(self):  # Network Menu.
		def getNetworkInterfaces():
			adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getAdapterList()]
			if not adapters:
				adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getConfiguredAdapters()]
			if not adapters:
				adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getInstalledAdapters()]
			activeInterface = None
			for adapter in adapters:
				if iNetwork.getAdapterAttribute(adapter[1], "up") is True:
					activeInterface = adapter[1]
					break
			return adapters, activeInterface

		def networkInterface():
			self.openScreen("NetworkSetup", screenName="AdapterSetup", networkinfo=activeInterface)

		def networkWizard():
			from Plugins.SystemPlugins.NetworkWizard.NetworkWizard import NetworkWizard
			self.session.open(NetworkWizard)

		adapters, activeInterface = getNetworkInterfaces()
		self.subList = []
		if isPluginInstalled("NetworkWizard"):
			self.subList.append(self.quickSubMenuEntryComponent(_("Network Wizard"), _("Configure your Network"), _("Use the Networkwizard to configure your Network. The wizard will help you to setup your network"), callback=networkWizard))
		if len(adapters) > 1:  # Show only adapter selection if more as 1 adapter is installed.
			self.subList.append(self.quickSubMenuEntryComponent(_("Network Adapter Selection"), _("Select Lan/Wlan"), _("Setup your network interface. If no Wlan stick is used, you only can select Lan"), screen="NetworkSetup", screenName="NetworkAdapterSelection"))
		if activeInterface is not None:  # Show only if there is already a adapter up.
			self.subList.append(self.quickSubMenuEntryComponent(_("Network Interface"), _("Setup interface"), _("Setup network. Here you can setup DHCP, IP, DNS"), callback=networkInterface))
		self.subList.append(self.quickSubMenuEntryComponent(_("Network Restart"), _("Restart network to with current setup"), _("Restart network and remount connections"), screen="RestartNetwork"))
		self.subList.append(self.quickSubMenuEntryComponent(_("Network Services"), _("Setup Network Services"), _("Setup Network Services (Samba, Ftp, NFS, ...)"), screen="NetworkSetup", screenName="NetworkServicesSetup"))
		self.subList.append(self.quickSubMenuEntryComponent(_("MiniDLNA"), _("Setup MiniDLNA"), _("Setup MiniDLNA"), screen="NetworkSetup", screenName="NetworkMiniDLNASetup"))
		self.subList.append(self.quickSubMenuEntryComponent(_("Inadyn"), _("Setup Inadyn"), _("Setup Inadyn"), screen="NetworkSetup", screenName="NetworkInadynSetup"))
		self.subList.append(self.quickSubMenuEntryComponent(_("uShare"), _("Setup uShare"), _("Setup uShare"), screen="NetworkSetup", screenName="NetworkuShareSetup"))
		self.setSubList()

	def subMenuAVSetup(self):  # A/V Settings Menu.
		def audioSync():
			from Plugins.Extensions.AudioSync.AC3setup import AC3LipSyncSetup
			self.session.open(AC3LipSyncSetup, resolveFilename(SCOPE_PLUGINS, "Extensions/AudioSync"))

		def videoEnhancement():
			from Plugins.SystemPlugins.VideoEnhancement.plugin import VideoEnhancementSetup
			self.session.open(VideoEnhancementSetup)

		self.subList = []
		self.subList.append(self.quickSubMenuEntryComponent(_("Video Settings"), _("Setup Videomode"), _("Setup your Video Mode, Video Output and other Video Settings"), screen="VideoMode", screenName="VideoSetup"))
		self.subList.append(self.quickSubMenuEntryComponent(_("Audio Settings"), _("Setup Audiomode"), _("Setup your Audio Mode"), setup="Audio"))
		if AUDIOSYNC:
			self.subList.append(self.quickSubMenuEntryComponent(_("Audio Sync"), _("Setup Audio Sync"), _("Setup Audio Sync settings"), callback=audioSync))
		self.subList.append(self.quickSubMenuEntryComponent(_("Auto Language"), _("Auto Language Selection"), _("Select your Language for Audio/Subtitles"), setup="AutoLanguage"))
		if VIDEOENH:
			self.subList.append(self.quickSubMenuEntryComponent(_("VideoEnhancement"), _("VideoEnhancement Setup"), _("VideoEnhancement Setup"), callback=videoEnhancement))
		self.setSubList()

	def subMenuTuner(self):  # Tuner Menu.
		def positionerSetup():
			from Plugins.SystemPlugins.PositionerSetup.plugin import PositionerMain
			PositionerMain(self.session)

		def satfinderMain():
			if len(NavigationInstance.instance.getRecordings(False, pNavigation.isAnyRecording)) > 0:
				self.session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to start the satellite finder."), MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
			else:
				from Plugins.SystemPlugins.Satfinder.plugin import Satfinder
				self.session.open(Satfinder)

		self.subList = []
		self.subList.append(self.quickSubMenuEntryComponent(_("Tuner Configuration"), _("Setup tuner(s)"), _("Setup each tuner for your satellite system"), screen="Satconfig", screenName="NimSelection"))
		if POSSETUP:
			self.subList.append(self.quickSubMenuEntryComponent(_("Positioner Setup"), _("Setup rotor"), _("Setup your positioner for your satellite system"), callback=positionerSetup))
		self.subList.append(self.quickSubMenuEntryComponent(_("Automatic Scan"), _("Automatic Service Searching"), _("Automatic scan for services"), screen="ScanSetup", screenName="ScanSimple"))
		self.subList.append(self.quickSubMenuEntryComponent(_("Manual Scan"), _("Manual Service Searching"), _("Manual scan for services"), screen="ScanSetup"))
		if SATFINDER:
			self.subList.append(self.quickSubMenuEntryComponent(_("Sat Finder"), _("Search Sats"), _("Search Sats, check signal and lock"), callback=satfinderMain))
		self.setSubList()

	def subMenuPlugin(self):  # Plugin Menu.
		def ipkInstaller():
			try:
				from Plugins.Extensions.MediaScanner.plugin import main
				main(self.session)
			except Exception:
				self.session.open(MessageBox, _("Sorry MediaScanner is not installed!"), MessageBox.TYPE_INFO, timeout=10, windowTitle=self.getTitle())

		def downloadPlugins():
			self.session.open(PackageAction, PackageAction.MODE_INSTALL)

		def removePlugins():
			self.session.open(PackageAction, PackageAction.MODE_REMOVE)

		def managePlugins():
			self.session.open(PackageAction, PackageAction.MODE_MANAGE)

		self.subList = []
		self.subList.append(self.quickSubMenuEntryComponent(_("Plugin Browser"), _("Open the Plugin Browser"), _("Shows Plugins Browser. Here you can setup installed Plugin"), screen="PluginBrowser"))
		self.subList.append(self.quickSubMenuEntryComponent(_("Download Plugins"), _("Download and install Plugins"), _("Shows available plugins. Here you can download and install them"), callback=downloadPlugins))
		self.subList.append(self.quickSubMenuEntryComponent(_("Remove Plugins"), _("Delete Plugins"), _("Delete and uninstall Plugins. This will remove the Plugin from your box"), callback=removePlugins))
		self.subList.append(self.quickSubMenuEntryComponent(_("Manage Plugins"), _("Manage Plugins"), _("Manage Plugins. This will remove/install Plugins on your box"), callback=managePlugins))
		self.subList.append(self.quickSubMenuEntryComponent(_("Plugin Browser Settings"), _("Setup Plugin Browser"), _("Setup PluginBrowser. Here you can select which Plugins are showed in the PluginBrowser"), setup="PluginBrowser"))
		self.subList.append(self.quickSubMenuEntryComponent(_("IPK Installer"), _("Install Local Extension"), _("Scan for local extensions and install them"), callback=ipkInstaller))
		self.setSubList()

	def subMenuHarddisk(self):  # Harddisk Menu.
		self.subList = []
		self.subList.append(self.quickSubMenuEntryComponent(_("Device Manager"), _("Device Manager"), _("Setup your Device mounts (USB, HDD, others...)"), screen="DeviceManager", screenName="DeviceManager"))
		self.setSubList()

	def quickSubMenuEntryComponent(self, name, description, longDescription=None, width=540, setup=None, screen=None, screenName=None, callback=None):
		return (name, description, longDescription, setup, screen, screenName, callback)

	def setSubList(self):
		self["sublist"].setList([(x[0], x[1]) for x in self.subList])

	def selectSubItem(self):
		(name, description, longDescription, setup, screen, screenName, callback) = self.subList[self["sublist"].getCurrentIndex()]
		if setup:
			self.openSetup(setup)
		elif screen:
			self.openScreen(screen, screenName=screenName)
		elif callback and callable(callback):
			callback()

	def openSetup(self, key):
		self.session.open(Setup, key)

	def openScreen(self, screenModule, screenName=None, **kwargs):
		try:
			screenobj = __import__(f"Screens.{screenModule}", None, None, [screenName or screenModule], 0)
			self.session.open(getattr(screenobj, screenName or screenModule), **kwargs)
		except (ModuleNotFoundError, AttributeError) as err:
			print(f"[QuickMenu] Error openScreen: {err}")

	def createSummary(self):
		pass
