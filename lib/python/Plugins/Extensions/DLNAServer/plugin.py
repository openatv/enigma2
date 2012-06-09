from Plugins.Plugin import PluginDescriptor

import os
from enigma import eTimer

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox

from Components.Button import Button
from Components.Label import Label
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.ActionMap import NumberActionMap, ActionMap
from Components.config import config, ConfigSelection, getConfigListEntry, ConfigText, ConfigDirectory, ConfigYesNo, ConfigSelection
from Components.FileList import FileList

from Tools.Directories import resolveFilename, SCOPE_PLUGINS

class SelectDirectoryWindow(Screen):
	skin = 	"""
		<screen name="SelectDirectoryWindow" position="center,center" size="560,320" title="Select Directory">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<widget name="currentDir" position="10,60" size="530,22" valign="center" font="Regular;22" />
			<widget name="filelist" position="0,100" zPosition="1" size="560,220" scrollbarMode="showOnDemand"/>
			<widget render="Label" source="key_red" position="0,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;20" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget render="Label" source="key_green" position="140,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;20" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		</screen>
		"""
	def __init__(self, session, currentDir):
		Screen.__init__(self, session)
		inhibitDirs = ["/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sbin", "/sys", "/usr", "/var"]
		self["filelist"] = FileList(currentDir, showDirectories = True, showFiles = False, inhibitMounts=[], inhibitDirs=inhibitDirs)
		self["actions"]  = ActionMap(["WizardActions", "DirectionActions", "ColorActions", "EPGSelectActions"], {
			"back"  : self.cancel,
			"left"  : self.left,
			"right" : self.right,
			"up"    : self.up,
			"down"  : self.down,
			"ok"    : self.ok,
			"green" : self.green,
			"red"   : self.cancel
		}, -1)

		self["currentDir"] = Label()
		self["key_green"]  = StaticText(_("OK"))
		self["key_red"]    = StaticText(_("Cancel"))

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.updateCurrentDirectory()

	def cancel(self):
		self.close(None)

	def green(self):
		self.close(self["filelist"].getSelection()[0])

	def up(self):
		self["filelist"].up()
		self.updateCurrentDirectory()

	def down(self):
		self["filelist"].down()
		self.updateCurrentDirectory()

	def left(self):
		self["filelist"].pageUp()
		self.updateCurrentDirectory()

	def right(self):
		self["filelist"].pageDown()
		self.updateCurrentDirectory()

	def ok(self):
		if self["filelist"].canDescent():
			self["filelist"].descent()
			self.updateCurrentDirectory()

	def updateCurrentDirectory(self):
		currentDir = self["filelist"].getSelection()[0]
		if currentDir is None or currentDir.strip() == '':
			currentDir = "Invalid Location"
		self["currentDir"].setText(currentDir)

class DLNAServer(ConfigListScreen, Screen):
	skin=   """
		<screen position="center,center" size="600,350" title="DLNA Server">
			<ePixmap pixmap="skin_default/buttons/red.png" position="5,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="155,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="305,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="455,0" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="5,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="155,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_yellow" render="Label" position="305,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_blue" render="Label" position="455,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="#ffffff" transparent="1" />

			<widget name="config" position="0,50" size="600,200" scrollbarMode="showOnDemand" />
			<widget name="information" position="0,250" size="600,100" valign="center" font="Regular;20" />
		</screen>
		"""
	def __init__(self, session): 
                self.session = session
		Screen.__init__(self, session)

		self.oldConfig = {}
		self.menulist = []
		ConfigListScreen.__init__(self, self.menulist)

		self.configFileName = "/etc/minidlna.conf"
		self.runcherBin     = resolveFilename(SCOPE_PLUGINS, "Extensions/DLNAServer/dlnaserver")
		self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "WizardActions", "ColorActions", "SetupActions", ], {
			"red"    : self.keyExit,
			"green"  : self.keyGreen,
			"blue"   : self.keyBlue,
			"yellow" : self.keyYellow,
			"cancel" : self.keyExit,
			"ok"     : self.keyOK
                }, -2)
		self["key_red"]     = StaticText(_("Exit"))
		self["key_green"]   = StaticText(_("Start"))
		self["key_yellow"]  = StaticText(_("Save"))
		self["key_blue"]    = StaticText(_("Reset"))
		self["information"] = Label()

		self.makeMenuEntry()
		self.onLayoutFinish.append(self.layoutFinished)

		self.updateGreenTimer = eTimer()
		self.updateGreenTimer.timeout.get().append(self.cbGreenTimer)

	def layoutFinished(self):
		green_btm_str = 'Start'
		if self.isRunning():
			green_btm_str = 'Stop'
		self["key_green"].setText(green_btm_str)
		#self["information"].setText(' ')

	def cbGreenTimer(self):
		self.updateGreenTimer.stop()
		self.layoutFinished()

	def keyExit(self):
		self.close()
	
	def keyOK(self):
		currentItem  = self.getCurrentItem()
		if currentItem is not None:
			self.session.openWithCallback(self.cbChangeDirectory, SelectDirectoryWindow, currentItem.value)

	def keyGreen(self):
		args = '-e'
		if self["key_green"].getText().strip() == 'Start':
			args = '-s'
			self.saveConfigFile()
		rc = os.popen('%s %s'%(self.runcherBin, args)).read()
		self["information"].setText(rc)
		self.updateGreenTimer.start(1000)

	def keyYellow(self):
		self.saveConfigFile()
		self["information"].setText('finished saving!!')

	def keyBlue(self):
		self.menuItemServerName.value = self.oldConfig.get('friendly_name')
		self.menuItemVideoDir.value   = self.oldConfig.get('media_dirV')
		self.menuItemMusicDir.value   = self.oldConfig.get('media_dirA')
		self.menuItemPictureDir.value = self.oldConfig.get('media_dirP')

		log_level_list = self.oldConfig.get('log_level').split('=')
		enable_log = False
		log_level  = log_level_list[1]
		if log_level != 'off':
			enable_log = True
		if log_level not in ('off', 'error', 'warn', 'debug'):
			log_level = 'error'
		self.menuItemEnableLog.value = enable_log
		self.menuItemLogLevel.value  = log_level
		self.menuItemLogDir.value    = self.oldConfig.get('log_dir')
		self.resetMenuList()

	def keyRed(self):
		self.keyExit()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.resetMenuList()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.resetMenuList()

	def saveConfigFile(self):
		serverName = self.menuItemServerName.value
		videoDir   = self.menuItemVideoDir.value
		auditDir   = self.menuItemMusicDir.value
		pictureDir = self.menuItemPictureDir.value
		logDir     = self.menuItemLogDir.value
		logLevel   = self.menuItemLogLevel.value
		if not self.menuItemEnableLog.value:
			logDir,logLevel = None, None
		self.writeConfigFile(serverName=serverName, videoDir=videoDir, auditDir=auditDir, pictureDir=pictureDir, logDir=logDir, logLevel=logLevel)

	def isRunning(self):
		ps_str = os.popen('ps -ef | grep minidlna | grep -v grep').read()
		if ps_str.strip() != '':
			return True
		return False

	def getCurrentItem(self):
		currentEntry = self["config"].getCurrent()
		if currentEntry == self.menuEntryVideoDir:
			return self.menuItemVideoDir
		elif currentEntry == self.menuEntryMusicDir:
			return self.menuItemMusicDir
		elif currentEntry == self.menuEntryPictureDir:
			return self.menuItemPictureDir
		elif currentEntry == self.menuEntryLogDir:
			return self.menuItemLogDir
		return None

        def cbChangeDirectory(self, pathStr):
		if pathStr is None or pathStr.strip() == '':
			return

		currentItem  = self.getCurrentItem()
		if currentItem is not None:
			currentItem.value = pathStr

	def makeMenuEntry(self):
		self.readConfigFile()
		if not os.path.exists('/media/dlna'):
			os.system('mkdir -p /media/dlna/.minidlna/')
			os.system('mkdir -p /media/dlna/Videos/')
			os.system('mkdir -p /media/dlna/Musics/')
			os.system('mkdir -p /media/dlna/Pictures/')
		self.menuItemServerName = ConfigText(default=self.oldConfig.get('friendly_name'))
		self.menuItemVideoDir   = ConfigDirectory(default = self.oldConfig.get('media_dirV'))
		self.menuItemMusicDir   = ConfigDirectory(default = self.oldConfig.get('media_dirA'))
		self.menuItemPictureDir = ConfigDirectory(default = self.oldConfig.get('media_dirP'))

		log_level_list = self.oldConfig.get('log_level').split('=')
		enable_log = False
		log_level  = log_level_list[1]
		if log_level != 'off':
			enable_log = True
		if log_level not in ('off', 'error', 'warn', 'debug'):
			log_level = 'error'
		self.menuItemEnableLog = ConfigYesNo(default = enable_log)
		self.menuItemLogLevel  = ConfigSelection(default = log_level, choices = [("off", _("off")), ("error", _("error")), ("warn", _("warn")), ("debug", _("debug"))])
		self.menuItemLogDir    = ConfigDirectory(default = self.oldConfig.get('log_dir'))

		self.menuEntryServerName = getConfigListEntry(_("Server Name"), self.menuItemServerName)
		self.menuEntryVideoDir   = getConfigListEntry(_("Video Directory"), self.menuItemVideoDir)
		self.menuEntryMusicDir   = getConfigListEntry(_("Music Directory"), self.menuItemMusicDir)
		self.menuEntryPictureDir = getConfigListEntry(_("Picture Directory"), self.menuItemPictureDir)
		self.menuEntryEnableLog  = getConfigListEntry(_("Enable Logging"), self.menuItemEnableLog)
		self.menuEntryLogLevel   = getConfigListEntry(_("    - Log Level"), self.menuItemLogLevel)
		self.menuEntryLogDir     = getConfigListEntry(_("    - Log Directory"), self.menuItemLogDir)
		self.resetMenuList()

	def resetMenuList(self):
		self.menulist = []
		self.menulist.append(self.menuEntryServerName)
		self.menulist.append(self.menuEntryVideoDir)
		self.menulist.append(self.menuEntryMusicDir)
		self.menulist.append(self.menuEntryPictureDir)
		self.menulist.append(self.menuEntryEnableLog)
		if self.menuItemEnableLog.value:
			self.menulist.append(self.menuEntryLogLevel)
			self.menulist.append(self.menuEntryLogDir)
		self["config"].list = self.menulist
		self["config"].l.setList(self.menulist)

	def writeConfigFile(self, serverName=None, videoDir=None, auditDir=None, pictureDir=None, logDir=None, logLevel='error'):
		configString = ""
		def configDataAppend(origin, key, value):
			if key.strip() != '' and value.strip() != '':
				origin += "%s=%s\n" % (key,value)
			return origin
		configString = configDataAppend(configString, "friendly_name", serverName)
		if videoDir is not None and videoDir.strip() != '':
			configString = configDataAppend(configString, "media_dir", "V,%s"%(videoDir))
		if auditDir is not None and auditDir.strip() != '':
			configString = configDataAppend(configString, "media_dir", "A,%s"%(auditDir))
		if pictureDir is not None and pictureDir.strip() != '':
			configString = configDataAppend(configString, "media_dir", "P,%s"%(pictureDir))
		if logDir is not None and logDir.strip() != '':
			configString = configDataAppend(configString, "log_dir", logDir)
			configString = configDataAppend(configString, "log_level", "general,artwork,database,inotify,scanner,metadata,http,ssdp,tivo=%s"%(logLevel))
		configString = configDataAppend(configString, "port", self.oldConfig.get('port'))
		configString = configDataAppend(configString, "db_dir", self.oldConfig.get('db_dir'))
		configString = configDataAppend(configString, "album_art_names", self.oldConfig.get('album_art_names'))
		configString = configDataAppend(configString, "inotify", self.oldConfig.get('inotify'))
		configString = configDataAppend(configString, "enable_tivo", self.oldConfig.get('enable_tivo'))
		configString = configDataAppend(configString, "strict_dlna", self.oldConfig.get('strict_dlna'))
		configString = configDataAppend(configString, "notify_interval", self.oldConfig.get('notify_interval'))
		configString = configDataAppend(configString, "serial", self.oldConfig.get('serial'))
		configString = configDataAppend(configString, "model_number", self.oldConfig.get('model_number'))
		print configString
		confFile = file(self.configFileName, 'w')
		confFile.write(configString)
		confFile.close()

	def readConfigFile(self):
		if not os.path.exists(self.configFileName):
			return
		self.oldConfig = {}
		for line in file(self.configFileName).readlines():
			line = line.strip()
			if line == '' or line[0] == '#':
				continue
			try:
				i   = line.find('=')
				k,v = line[:i],line[i+1:]
				if k == 'media_dir':
					k += v[0]
					v  = v[2:]
				self.oldConfig[k] = v
			except : pass
		def setDefault(key, default):
			try:
				value = self.oldConfig.get(key)
				if value == None or value.strip() == '':
					self.oldConfig[key] = default
			except: self.oldConfig[key] = default
			
		setDefault('friendly_name', '%s DLNA Server'%(config.misc.boxtype.value.upper()))
		setDefault('media_dirV', '/media/dlna/Videos')
		setDefault('media_dirA', '/media/dlna/Musics')
		setDefault('media_dirP', '/media/dlna/Pictures')
		setDefault('log_dir', '/media/dlna/.minidlnalog')
		setDefault('log_level', 'general,artwork,database,inotify,scanner,metadata,http,ssdp,tivo=error')
		setDefault('port', '8200')
		setDefault('db_dir', '/var/cache/minidlna')
		setDefault('album_art_names', 'Cover.jpg/cover.jpg/AlbumArtSmall.jpg/albumartsmall.jpg/AlbumArt.jpg/albumart.jpg/Album.jpg/album.jpg/Folder.jpg/folder.jpg/Thumb.jpg/thumb.jpg')
		setDefault('inotify', 'yes')
		setDefault('enable_tivo', 'no')
		setDefault('strict_dlna', 'no')
		setDefault('notify_interval', '900')
		setDefault('serial', '12345678')
		setDefault('model_number', '1')
		print "Current Config : ", self.oldConfig

def main(session, **kwargs):
	session.open(DLNAServer)

def Plugins(**kwargs):
 	return PluginDescriptor(name="DLNA Server", description="This is dlna server using minidlna.", where = PluginDescriptor.WHERE_PLUGINMENU, needsRestart = False, fnc=main)
