from Plugins.Plugin import PluginDescriptor
from Screens.Console import Console
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Ipkg import Ipkg
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Input import Input
from Components.Ipkg import IpkgComponent
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Sources.List import List
from Components.Slider import Slider
from Components.Harddisk import harddiskmanager
from Components.config import config,getConfigListEntry, ConfigSubsection, ConfigText, ConfigLocations
from Components.Console import Console
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.SelectionList import SelectionList
from Components.PluginComponent import plugins
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS, SCOPE_SKIN_IMAGE
from Tools.LoadPixmap import LoadPixmap
from enigma import eTimer, quitMainloop, RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, eListbox, gFont, getDesktop
from cPickle import dump, load

from os import path as os_path, system as os_system, unlink, stat, mkdir, popen, makedirs, listdir, access, rename, remove, W_OK, R_OK, F_OK
from time import time, gmtime, strftime, localtime
from stat import ST_MTIME
from datetime import date

from ImageWizard import ImageWizard
from BackupRestore import BackupSelection, RestoreMenu, BackupScreen, RestoreScreen, getBackupPath, getBackupFilename

config.plugins.configurationbackup = ConfigSubsection()
config.plugins.configurationbackup.backuplocation = ConfigText(default = '/media/hdd/', visible_width = 50, fixed_size = False)
config.plugins.configurationbackup.backupdirs = ConfigLocations(default=['/etc/enigma2/', '/etc/network/interfaces', '/etc/wpa_supplicant.conf'])

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


class UpdatePluginMenu(Screen):
	skin = """
		<screen name="UpdatePluginMenu" position="90,130" size="550,330" title="Softwaremanager..." >
			<ePixmap pixmap="skin_default/border_menu.png" position="10,10" zPosition="1" size="250,300" transparent="1" alphatest="on" />
			<widget source="menu" render="Listbox" position="20,20" size="230,260" scrollbarMode="showOnDemand">
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (2, 2), size = (230, 22), flags = RT_HALIGN_LEFT, text = 1), # index 0 is the MenuText,
						],
					"fonts": [gFont("Regular", 20)],
					"itemHeight": 25
					}
				</convert>
			</widget>
			<widget source="menu" render="Listbox" position="280,10" size="230,300" scrollbarMode="showNever" selectionDisabled="1">
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (2, 2), size = (230, 300), flags = RT_HALIGN_CENTER|RT_VALIGN_CENTER|RT_WRAP, text = 2), # index 2 is the Description,
						],
					"fonts": [gFont("Regular", 20)],
					"itemHeight": 230
					}
				</convert>
			</widget>
		</screen>"""
		
	def __init__(self, session, args = 0):
		Screen.__init__(self, session)
		self.skin_path = plugin_path
		self.menu = args
		self.list = []
		self.oktext = _("\nPress OK on your remote control to continue.")
		self.backupdirs = ' '.join( config.plugins.configurationbackup.backupdirs.value )
		if self.menu == 0:
			self.list.append(("software-update", _("Software update"), _("\nOnline update of your Dreambox software." ) + self.oktext) )
			self.list.append(("software-restore", _("Software restore"), _("\nRestore your Dreambox with a new firmware." ) + self.oktext))
			self.list.append(("system-backup", _("Backup system settings"), _("\nBackup your Dreambox settings." ) + self.oktext))
			self.list.append(("system-restore",_("Restore system settings"), _("\nRestore your Dreambox settings." ) + self.oktext))
			if config.usage.setup_level.index >= 2: # expert+
				self.list.append(("advanced", _("Advanced Options"), _("\nAdvanced options and settings." ) + self.oktext))
		elif self.menu == 1:
			self.list.append(("ipkg-manager", _("Packet management"),  _("\nView, install and remove available or installed packages." ) + self.oktext))
			self.list.append(("ipkg-install", _("Install local IPKG"),  _("\nScan for local packages and install them." ) + self.oktext))
			self.list.append(("advancedrestore", _("Advanced restore"), _("\nRestore your backups by date." ) + self.oktext))
			self.list.append(("backuplocation", _("Choose backup location"),  _("\nSelect your backup device.\nCurrent device: " ) + config.plugins.configurationbackup.backuplocation.value + self.oktext ))
			self.list.append(("backupfiles", _("Choose backup files"),  _("Select files for backup. Currently selected:\n" ) + self.backupdirs + self.oktext))
			self.list.append(("ipkg-source",_("Choose upgrade source"), _("\nEdit the upgrade source address." ) + self.oktext))

		self["menu"] = List(self.list)
				
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"ok": self.go,
			"back": self.close,
			"red": self.close,
		}, -1)

		self.onLayoutFinish.append(self.layoutFinished)
		self.backuppath = getBackupPath()
		self.backupfile = getBackupFilename()
		self.fullbackupfilename = self.backuppath + "/" + self.backupfile
		self.onShown.append(self.setWindowTitle)
		
	def layoutFinished(self):
		idx = 0
		self["menu"].index = idx
		
	def setWindowTitle(self):
		self.setTitle(_("Software manager..."))
		
	def go(self):
		current = self["menu"].getCurrent()
		if current:
			current = current[0]
			if self.menu == 0:
				if (current == "software-restore"):
					self.session.open(ImageWizard)
				elif (current == "software-update"):
					self.session.openWithCallback(self.runUpgrade, MessageBox, _("Do you want to update your Dreambox?")+"\n"+_("\nAfter pressing OK, please wait!"))
				elif (current == "advanced"):
					self.session.open(UpdatePluginMenu, 1)
				elif (current == "system-backup"):
					self.session.openWithCallback(self.backupDone,BackupScreen, runBackup = True)
				elif (current == "system-restore"):
					if os_path.exists(self.fullbackupfilename):
						self.session.openWithCallback(self.startRestore, MessageBox, _("Are you sure you want to restore your Enigma2 backup?\nEnigma2 will restart after the restore"))
					else:	
						self.session.open(MessageBox, _("Sorry no backups found!"), MessageBox.TYPE_INFO)
			elif self.menu == 1:
				if (current == "ipkg-manager"):
					self.session.open(PacketManager, self.skin_path)
				elif (current == "ipkg-source"):
					self.session.open(IPKGMenu, self.skin_path)
					#self.session.open(IPKGSource)
				elif (current == "ipkg-install"):
					try:
						from Plugins.Extensions.MediaScanner.plugin import main
						main(self.session)
					except:
						self.session.open(MessageBox, _("Sorry MediaScanner is not installed!"), MessageBox.TYPE_INFO)
				elif (current == "backuplocation"):
					parts = [ (r.description, r.mountpoint, self.session) for r in harddiskmanager.getMountedPartitions(onlyhotplug = False)]
					for x in parts:
						if not access(x[1], F_OK|R_OK|W_OK) or x[1] == '/':
							parts.remove(x)
					for x in parts:
						if x[1].startswith('/autofs/'):
							parts.remove(x)
					if len(parts):
						self.session.openWithCallback(self.backuplocation_choosen, ChoiceBox, title = _("Please select medium to use as backup location"), list = parts)
				elif (current == "backupfiles"):
					self.session.openWithCallback(self.backupfiles_choosen,BackupSelection)
				elif (current == "advancedrestore"):
					self.session.open(RestoreMenu, self.skin_path)

	def backupfiles_choosen(self, ret):
		self.backupdirs = ' '.join( config.plugins.configurationbackup.backupdirs.value )

	def backuplocation_choosen(self, option):
		if option is not None:
			config.plugins.configurationbackup.backuplocation.value = str(option[1])
		config.plugins.configurationbackup.backuplocation.save()
		config.plugins.configurationbackup.save()
		config.save()
		self.createBackupfolders()
	
	def runUpgrade(self, result):
		if result:
			self.session.open(UpdatePlugin, self.skin_path)

	"""def runFinished(self):
		self.session.openWithCallback(self.reboot, MessageBox, _("Upgrade finished.") +" "+_("Do you want to reboot your Dreambox?"), MessageBox.TYPE_YESNO)
		
	def reboot(self, result):
		if result is None:
			return
		if result:
			quitMainloop(3)"""

	def createBackupfolders(self):
		print "Creating backup folder if not already there..."
		self.backuppath = getBackupPath()
		try:
			if (os_path.exists(self.backuppath) == False):
				makedirs(self.backuppath)
		except OSError:
			self.session.open(MessageBox, _("Sorry, your backup destination is not writeable.\n\nPlease choose another one."), MessageBox.TYPE_INFO)

	def backupDone(self,retval = None):
		if retval is True:
			self.session.open(MessageBox, _("Backup done."), MessageBox.TYPE_INFO)
		else:
			self.session.open(MessageBox, _("Backup failed."), MessageBox.TYPE_INFO)

	def startRestore(self, ret = False):
		if (ret == True):
			self.exe = True
			self.session.open(RestoreScreen, runRestore = True)

class IPKGMenu(Screen):
	skin = """
		<screen name="IPKGMenu" position="135,144" size="450,320" title="Select IPKG source......" >
			<widget name="filelist" position="10,10" size="430,240" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,280" zPosition="2" size="140,40" transparent="1" alphatest="on" />
			<widget name="closetext" position="20,290" size="140,21" zPosition="10" font="Regular;21" transparent="1" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="160,280" zPosition="2" size="140,40" transparent="1" alphatest="on" />
			<widget name="edittext" position="170,290" size="300,21" zPosition="10" font="Regular;21" transparent="1" />
		</screen>"""

	def __init__(self, session, plugin_path):
		Screen.__init__(self, session)
		self.skin_path = plugin_path
		
		self["closetext"] = Label(_("Close"))
		self["edittext"] = Label(_("Edit"))

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
		self.flist = []
		self["filelist"] = MenuList(self.flist)
		self.fill_list()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setWindowTitle()

	def setWindowTitle(self):
		self.setTitle(_("Select IPKG source to edit..."))


	def fill_list(self):
		self.flist = []
		self.path = '/etc/ipkg/'
		if (os_path.exists(self.path) == False):
			self.entry = False
			return
		for file in listdir(self.path):
			if (file.endswith(".conf")):
				if file != 'arch.conf':
					self.flist.append((file))
					self.entry = True
					self["filelist"].l.setList(self.flist)

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
		<screen name="IPKGSource" position="100,100" size="550,80" title="IPKG source" >
			<widget name="text" position="10,10" size="530,25" font="Regular;20" backgroundColor="background" foregroundColor="#cccccc" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,40" zPosition="2" size="140,40" transparent="1" alphatest="on" />
			<widget name="closetext" position="20,50" size="140,21" zPosition="10" font="Regular;21" transparent="1" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="160,40" zPosition="2" size="140,40" transparent="1" alphatest="on" />
			<widget name="edittext" position="170,50" size="300,21" zPosition="10" font="Regular;21" transparent="1" />
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
		#print "[IPKGSource] mainscreen: current desktop size: %dx%d" % (x,y)

		self["closetext"] = Label(_("Cancel"))
		self["edittext"] = Label(_("Save"))
		
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
		self.setTitle(_("Edit IPKG source URL..."))
		
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
		print "pressed", number
		self["text"].number(number)


class PacketManager(Screen):
	skin = """
		<screen position="90,80" size="530,420" title="IPKG upgrade..." >
			<widget source="list" render="Listbox" position="5,10" size="520,365" scrollbarMode="showOnDemand">
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
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,380" zPosition="2" size="140,40" transparent="1" alphatest="on" />
			<widget name="closetext" position="20,390" size="140,21" zPosition="10" font="Regular;21" transparent="1" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="160,380" zPosition="2" size="140,40" transparent="1" alphatest="on" />
			<widget name="reloadtext" position="170,390" size="300,21" zPosition="10" font="Regular;21" transparent="1" />
		</screen>"""
		
	def __init__(self, session, plugin_path, args = None):
		Screen.__init__(self, session)
		self.session = session
		self.skin_path = plugin_path

		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"], 
		{
			"ok": self.go,
			"back": self.exit,
			"red": self.exit,
			"green": self.reload,
		}, -1)
		
		self.list = []
		self.statuslist = []
		self["list"] = List(self.list)
		self["closetext"] = Label(_("Close"))
		self["reloadtext"] = Label(_("Reload"))

		self.list_updating = True
		self.packetlist = []
		self.installed_packetlist = {}
		self.Console = Console()
		self.cmdList = []
		self.cachelist = []
		self.cache_ttl = 86400  #600 is default, 0 disables, Seconds cache is considered valid (24h should be ok for caching ipkgs)
		self.cache_file = '/usr/lib/enigma2/python/Plugins/SystemPlugins/SoftwareManager/packetmanager.cache' #Path to cache directory	 
		self.oktext = _("\nAfter pressing OK, please wait!")

		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)
		self.onShown.append(self.setWindowTitle)
		self.onLayoutFinish.append(self.rebuildList)

	def exit(self):
		self.ipkg.stop()
		if self.Console is not None:
			if len(self.Console.appContainers):
				for name in self.Console.appContainers.keys():
					self.Console.kill(name)
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
			divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/div-h.png"))
			if status == 'update':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/installable.png"))
				self.statuslist.append(( _("Package list update"), '', _("Trying to download a new packetlist. Please wait..." ),'',statuspng, divpng ))
				self['list'].setList(self.statuslist)	
			elif status == 'error':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/installed.png"))
				self.statuslist.append(( _("Error"), '', _("There was an error downloading the packetlist. Please try again." ),'',statuspng, divpng ))
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
					self.session.openWithCallback(self.runRemove, MessageBox, _("Do you want to remove the package:\n" + package + "\n" + self.oktext))
			elif status == 'upgradeable':
				self.cmdList.append((IpkgComponent.CMD_INSTALL, { "package": package }))
				if len(self.cmdList):
					self.session.openWithCallback(self.runUpgrade, MessageBox, _("Do you want to upgrade the package:\n" + package + "\n" + self.oktext))
			elif status == "installable":
				self.cmdList.append((IpkgComponent.CMD_INSTALL, { "package": package }))
				if len(self.cmdList):
					self.session.openWithCallback(self.runUpgrade, MessageBox, _("Do you want to install the package:\n" + package + "\n" + self.oktext))

	def runRemove(self, result):
		if result:
			self.session.openWithCallback(self.runRemoveFinished, Ipkg, cmdList = self.cmdList)

	def runRemoveFinished(self):
		self.session.openWithCallback(self.RemoveReboot, MessageBox, _("Remove finished.") +" "+_("Do you want to reboot your Dreambox?"), MessageBox.TYPE_YESNO)

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
			quitMainloop(3)

	def runUpgrade(self, result):
		if result:
			self.session.openWithCallback(self.runUpgradeFinished, Ipkg, cmdList = self.cmdList)

	def runUpgradeFinished(self):
		self.session.openWithCallback(self.UpgradeReboot, MessageBox, _("Upgrade finished.") +" "+_("Do you want to reboot your Dreambox?"), MessageBox.TYPE_YESNO)
		
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
			quitMainloop(3)

	def ipkgCallback(self, event, param):
		if event == IpkgComponent.EVENT_ERROR:
			self.list_updating = False
			self.setStatus('error')
		elif event == IpkgComponent.EVENT_DONE:
			if self.list_updating:
				self.list_updating = False
				if not self.Console:
					self.Console = Console()
				cmd = "ipkg list"
				self.Console.ePopen(cmd, self.IpkgList_Finished)
		#print event, "-", param
		pass

	def IpkgList_Finished(self, result, retval, extra_args = None):
		if len(result):
			self.packetlist = []
			for x in result.splitlines():
				split = x.split(' - ')
				if not (split[0].strip().endswith('-dbg') or split[0].strip().endswith('-dev')):
					self.packetlist.append([split[0].strip(), split[1].strip(),split[2].strip()])
		if not self.Console:
			self.Console = Console()
		cmd = "ipkg list_installed"
		self.Console.ePopen(cmd, self.IpkgListInstalled_Finished)

	def IpkgListInstalled_Finished(self, result, retval, extra_args = None):
		if len(result):
			self.installed_packetlist = {}
			for x in result.splitlines():
				split = x.split(' - ')
				if not (split[0].strip().endswith('-dbg') or split[0].strip().endswith('-dev')):
					self.installed_packetlist[split[0].strip()] = split[1].strip()
		self.buildPacketList()

	def buildEntryComponent(self, name, version, description, state):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/div-h.png"))
		if state == 'installed':
			installedpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/installed.png"))
			return((name, version, description, state, installedpng, divpng))	
		elif state == 'upgradeable':
			upgradeablepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/upgradeable.png"))
			return((name, version, description, state, upgradeablepng, divpng))	
		else:
			installablepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/installable.png"))
			return((name, version, description, state, installablepng, divpng))

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
				if self.installed_packetlist.has_key(x[0].strip()):
					if self.installed_packetlist[x[0].strip()] == x[1].strip():
						status = "installed"
						self.list.append(self.buildEntryComponent(x[0].strip(), x[1].strip(), x[2].strip(), status))
					else:
						status = "upgradeable"
						self.list.append(self.buildEntryComponent(x[0].strip(), x[1].strip(), x[2].strip(), status))
				else:
					status = "installable"
					self.list.append(self.buildEntryComponent(x[0].strip(), x[1].strip(), x[2].strip(), status))
				if not (x[0].strip().endswith('-dbg') or x[0].strip().endswith('-dev')):
					self.cachelist.append([x[0].strip(), x[1].strip(), x[2].strip(), status])	
			write_cache(self.cache_file, self.cachelist)
			self['list'].setList(self.list)

	def reloadPluginlist(self):
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))

class UpdatePlugin(Screen):
	skin = """
		<screen position="100,100" size="550,200" title="Software Update..." >
			<widget name="activityslider" position="0,0" size="550,5"  />
			<widget name="slider" position="0,100" size="550,30"  />
			<widget name="package" position="10,30" size="540,20" font="Regular;18"/>
			<widget name="status" position="10,60" size="540,45" font="Regular;18"/>
		</screen>"""
		
	def __init__(self, session, args = None):
		self.skin = UpdatePlugin.skin
		Screen.__init__(self, session)
		
		self.sliderPackages = { "dreambox-dvb-modules": 1, "enigma2": 2, "tuxbox-image-info": 3 }
		
		self.slider = Slider(0, 4)
		self["slider"] = self.slider
		self.activityslider = Slider(0, 100)
		self["activityslider"] = self.activityslider
		self.status = Label(_("Upgrading Dreambox... Please wait"))
		self["status"] = self.status
		self.package = Label()
		self["package"] = self.package
		
		self.packages = 0
		self.error = 0
		
		self.activity = 0
		self.activityTimer = eTimer()
		self.activityTimer.callback.append(self.doActivityTimer)
		self.activityTimer.start(100, False)
				
		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)
		
		self.updating = True
		self.package.setText(_("Package list update"))
		self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)
			
		self["actions"] = ActionMap(["WizardActions"], 
		{
			"ok": self.exit,
			"back": self.exit
		}, -1)
		
	def doActivityTimer(self):
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
			self.status.setText(_("Upgrading"))
			self.packages += 1
		elif event == IpkgComponent.EVENT_INSTALL:
			self.package.setText(param)
			self.status.setText(_("Installing"))
			self.packages += 1
		elif event == IpkgComponent.EVENT_CONFIGURING:
			self.package.setText(param)
			self.status.setText(_("Configuring"))
		elif event == IpkgComponent.EVENT_MODIFIED:
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
				self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE, args = {'test_only': False})
			elif self.error == 0:
				self.slider.setValue(4)
				
				self.activityTimer.stop()
				self.activityslider.setValue(0)
				
				self.package.setText("")
				self.status.setText(_("Done - Installed or upgraded %d packages") % self.packages)
			else:
				self.activityTimer.stop()
				self.activityslider.setValue(0)
				error = _("your dreambox might be unusable now. Please consult the manual for further assistance before rebooting your dreambox.")
				if self.packages == 0:
					error = _("No packages were upgraded yet. So you can check your network and try again.")
				if self.updating:
					error = _("Your dreambox isn't connected to the internet properly. Please check it and try again.")
				self.status.setText(_("Error") +  " - " + error)
		#print event, "-", param
		pass

	def modificationCallback(self, res):
		self.ipkg.write(res and "N" or "Y")

	def exit(self):
		if not self.ipkg.isRunning():
			if self.packages != 0 and self.error == 0:
				self.session.openWithCallback(self.exitAnswer, MessageBox, _("Upgrade finished.") +" "+_("Do you want to reboot your Dreambox?"))
			else:
				self.close()
			
	def exitAnswer(self, result):
		if result is not None and result:
			quitMainloop(2)
		self.close()



class IpkgInstaller(Screen):
	skin = """
		<screen position="100,100" size="550,400" title="..." >
			<widget name="red" halign="center" valign="center" position="0,0" size="140,60" backgroundColor="red" font="Regular;21" />
			<widget name="green" halign="center" valign="center" position="140,0" text="Install selected" size="140,60" backgroundColor="green" font="Regular;21" />
			<widget name="yellow" halign="center" valign="center" position="280,0" size="140,60" backgroundColor="yellow" font="Regular;21" />
			<widget name="blue" halign="center" valign="center" position="420,0" size="140,60" backgroundColor="blue" font="Regular;21" />
			<widget name="list" position="0,60" size="550,360" />
		</screen>
		"""
	
	def __init__(self, session, list):
		self.skin = IpkgInstaller.skin
		Screen.__init__(self, session)

		self.list = SelectionList()
		self["list"] = self.list
		for listindex in range(len(list)):
			self.list.addSelection(list[listindex], list[listindex], listindex, True)

		self["red"] = Label()
		self["green"] = Label()
		self["yellow"] = Label()
		self["blue"] = Label()
		
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], 
		{
			"ok": self.list.toggleSelection, 
			"cancel": self.close, 
			"green": self.install
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
			description = _("Install software updates..."), 
			openfnc = filescan_open, )

def UpgradeMain(session, **kwargs):
	session.open(UpdatePluginMenu)

def startSetup(menuid):
	if menuid != "setup": 
		return [ ]
	return [(_("Software manager") + "...", UpgradeMain, "software_manager", 50)]

def Plugins(path, **kwargs):
	global plugin_path
	plugin_path = path
	list = [
		PluginDescriptor(name=_("Software manager"), description=_("Manage your receiver's software"), where = PluginDescriptor.WHERE_MENU, fnc=startSetup), 
		PluginDescriptor(name=_("Ipkg"), where = PluginDescriptor.WHERE_FILESCAN, fnc = filescan)
	]
	if config.usage.setup_level.index >= 2: # expert+	
		list.append(PluginDescriptor(name=_("Software manager"), description=_("Manage your receiver's software"), where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=UpgradeMain))	
	return list
