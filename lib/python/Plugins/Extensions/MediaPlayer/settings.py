from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Components.Label import Label
from Components.FileList import FileList
from Components.MediaPlayer import PlayList
from Components.config import config, getConfigListEntry, ConfigSubsection, configfile, ConfigText, ConfigYesNo, ConfigDirectory
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap

config.mediaplayer = ConfigSubsection()
config.mediaplayer.repeat = ConfigYesNo(default=False)
config.mediaplayer.savePlaylistOnExit = ConfigYesNo(default=True)
config.mediaplayer.saveDirOnExit = ConfigYesNo(default=False)
config.mediaplayer.defaultDir = ConfigDirectory()

class DirectoryBrowser(Screen, HelpableScreen):
	skin = """
		<screen name="DirectoryBrowser" position="center,center" size="560,400" title="Directory browser" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="filelist" position="5,50" size="550,350" scrollbarMode="showOnDemand" />
		</screen>"""
	def __init__(self, session, currDir):
		from Components.Sources.StaticText import StaticText
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Use"))

		self.filelist = FileList(currDir, matchingPattern="")
		self["filelist"] = self.filelist

		self["FilelistActions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"green": self.use,
				"red": self.exit,
				"ok": self.ok,
				"cancel": self.exit
			})

	def ok(self):
		if self.filelist.canDescent():
			self.filelist.descent()

	def use(self):
		if self.filelist.canDescent() and self["filelist"].getFilename() and len(self["filelist"].getFilename()) > len(self["filelist"].getCurrentDirectory()):
			self.filelist.descent()
		self.close(self["filelist"].getCurrentDirectory())

	def exit(self):
		self.close(False)

class MediaPlayerSettings(Screen,ConfigListScreen):
	skin = """
		<screen name="MediaPlayerSettings" position="center,center" size="560,300" title="Edit settings">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" position="5,50" size="550,250" />
		</screen>"""

	def __init__(self, session, parent):
		from Components.Sources.StaticText import StaticText
		Screen.__init__(self, session)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))

		ConfigListScreen.__init__(self, [])
		self.parent = parent
		self.initConfigList()
		config.mediaplayer.saveDirOnExit.addNotifier(self.initConfigList)

		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
		    "green": self.save,
		    "red": self.cancel,
		    "cancel": self.cancel,
		    "ok": self.ok,
		}, -2)

	def initConfigList(self, element=None):
		print "[initConfigList]", element
		try:
			self.list = []
			self.list.append(getConfigListEntry(_("repeat playlist"), config.mediaplayer.repeat))
			self.list.append(getConfigListEntry(_("save playlist on exit"), config.mediaplayer.savePlaylistOnExit))
			self.list.append(getConfigListEntry(_("save last directory on exit"), config.mediaplayer.saveDirOnExit))
			if not config.mediaplayer.saveDirOnExit.getValue():
				self.list.append(getConfigListEntry(_("start directory"), config.mediaplayer.defaultDir))
			self["config"].setList(self.list)
		except KeyError:
			print "keyError"

	def changedConfigList(self):
		self.initConfigList()

	def ok(self):
		if self["config"].getCurrent()[1] == config.mediaplayer.defaultDir:
			self.session.openWithCallback(self.DirectoryBrowserClosed, DirectoryBrowser, self.parent.filelist.getCurrentDirectory())

	def DirectoryBrowserClosed(self, path):
		print "PathBrowserClosed:" + str(path)
		if path != False:
			config.mediaplayer.defaultDir.setValue(path)

	def save(self):
		for x in self["config"].list:
			x[1].save()
		self.close()

	def cancel(self):
		self.close()

