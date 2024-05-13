from Components.FileList import FileList
from Components.Sources.StaticText import StaticText
from Components.config import config, ConfigSubsection, ConfigText, ConfigYesNo, ConfigDirectory, NoSave
from Components.ActionMap import ActionMap
from Screens.Screen import Screen
from Screens.Setup import Setup


def Load_defaults():
	config.mediaplayer = ConfigSubsection()
	config.mediaplayer.repeat = ConfigYesNo(default=False)
	config.mediaplayer.savePlaylistOnExit = ConfigYesNo(default=True)
	config.mediaplayer.saveDirOnExit = ConfigYesNo(default=False)
	config.mediaplayer.defaultDir = ConfigDirectory()
	config.mediaplayer.sortPlaylists = ConfigYesNo(default=False)
	config.mediaplayer.alwaysHideInfoBar = ConfigYesNo(default=True)
	config.mediaplayer.onMainMenu = ConfigYesNo(default=False)

	config.mediaplayer.useAlternateUserAgent = NoSave(ConfigYesNo(default=False))
	config.mediaplayer.alternateUserAgent = NoSave(ConfigText(default="HbbTV/1.1.1 (+PVR+RTSP+DL; Sonic; TV44; 1.32.455; 2.002) Bee/3.5"))


Load_defaults()


class DirectoryBrowser(Screen):

	def __init__(self, session, currDir):
		Screen.__init__(self, session, enableHelp=True)
		# for the skin: first try MediaPlayerDirectoryBrowser, then FileBrowser, this allows individual skinning
		self.skinName = ["MediaPlayerDirectoryBrowser", "FileBrowser"]

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
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("Directory browser"))

	def ok(self):
		if self.filelist.canDescent():
			self.filelist.descent()

	def use(self):
		if self["filelist"].getCurrentDirectory() is not None:
			if self.filelist.canDescent() and self["filelist"].getFilename() and len(self["filelist"].getFilename()) > len(self["filelist"].getCurrentDirectory()):
				self.filelist.descent()
				self.close(self["filelist"].getCurrentDirectory())
		else:
			self.close(self["filelist"].getFilename())

	def exit(self):
		self.close(False)


class MediaPlayerSetup(Setup):
	def __init__(self, session, parent):
		Setup.__init__(self, session, setup="MediaPlayer", plugin="Extensions/MediaPlayer")
		self.parent = parent

	def keySelect(self):
		if self["config"].getCurrent()[1] == config.mediaplayer.defaultDir:
			self.session.openWithCallback(self.DirectoryBrowserClosed, DirectoryBrowser, self.parent.filelist.getCurrentDirectory())
			return
		Setup.keySelect(self)

	def keySave(self):
		if config.mediaplayer.defaultDir.value == "None":
			config.mediaplayer.defaultDir.value = ""
		Setup.keySave(self)

	def DirectoryBrowserClosed(self, path):
		print("PathBrowserClosed:" + str(path))
		if path:
			config.mediaplayer.defaultDir.setValue(path)
