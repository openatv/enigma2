from os import listdir
from os.path import exists, isdir, isfile, join, split

from enigma import addFont, ePicLoad

from Components.config import ConfigSelection, NoSave, config, configfile
from Components.PluginComponent import plugins
from Components.Pixmap import Pixmap
from Plugins.Plugin import PluginDescriptor
from Screens.Processing import Processing
from Screens.Setup import Setup
from Screens.Standby import TryQuitMainloop, QUIT_RESTART
from Tools.Directories import SCOPE_GUISKIN, SCOPE_FONTS, SCOPE_SKINS, resolveFilename


class SkinSelection(Setup):
	DISPLAY_SKINS = {
		"skin_display.xml": _("< Default >"),
		"skin_display_picon.xml": _("< Default with Picon >"),
		"skin_display_usr.xml": _("< User Skin >"),
		"skin_display_alternate.xml": _("< Alternate Skin >")
	}
	PREVIEW = {
		"skin_display_picon.xml": "piconprev.png",
		"skin_display_usr.xml": "userskin.png",
		"skin_display_alternate.xml": "alternate.png"
	}

	def __init__(self, session):
		self.guiRoot = resolveFilename(SCOPE_SKINS)
		self.lcdRoot = join(self.guiRoot, "display")
		self.noPreview = join(resolveFilename(SCOPE_GUISKIN), "noprev.png")
		self.createItems()
		Setup.__init__(self, session, "Skin")
		self["preview"] = Pixmap()
		self["preview"].hide()
		self.picLoad = None

	def createItems(self):
		guiDirectory, guiSkin = split(config.skin.primary_skin.value)
		guiSkin = guiSkin if guiSkin else "skin.xml"
		choices = []
		for directory in [x for x in listdir(self.guiRoot) if isdir(join(self.guiRoot, x))]:
			path = join(directory, "skin.xml")
			if exists(join(self.guiRoot, path)):
				label = _("< Default >") if directory == "skin_default" else directory
				if directory == "MetrixHD":
					if isfile(join(self.guiRoot, directory, "skin.MySkin.xml")):
						guiSkin = "skin.MySkin.xml"
					path = join(directory, guiSkin)
				choices.append((path, label))
		config.skin.guiSkin = NoSave(ConfigSelection(default=config.skin.primary_skin.value, choices=choices))
		lcdDirectory, lcdSkin = split(config.skin.display_skin.value)
		lcdSkin = lcdSkin if lcdSkin else "skin_display.xml"
		choices = []
		if exists(self.lcdRoot):
			for skin in self.DISPLAY_SKINS.keys():
				path = join(self.lcdRoot, skin)
				if exists(path):
					choices.append((skin, self.DISPLAY_SKINS[skin]))
			for directory in [x for x in listdir(self.lcdRoot) if isdir(join(self.lcdRoot, x))]:
				path = join(directory, "skin_display.xml")
				if exists(join(self.lcdRoot, path)):
					choices.append((path, directory))
		else:
			choices.append((config.skin.display_skin.value, ""))
		config.skin.lcdSkin = NoSave(ConfigSelection(default=config.skin.display_skin.value, choices=choices))

	def layoutFinished(self):
		def showPicture(picInfo=""):
			ptr = self.picLoad.getData()
			if ptr is not None:
				self["preview"].instance.setPixmap(ptr.__deref__())
				self["preview"].show()

		self.picLoad = ePicLoad()
		self.picLoad.PictureData.get().append(showPicture)
		self.picLoad.setPara((self["preview"].instance.size().width(), self["preview"].instance.size().height(), 1, 1, False, 1, "#00000000"))
		Setup.layoutFinished(self)
		self.loadPreview()

	def changedEntry(self):
		Setup.changedEntry(self)
		self.loadPreview()

	def selectionChanged(self):
		Setup.selectionChanged(self)
		self.loadPreview()

	def keySave(self):
		guiSkinChanged = config.skin.guiSkin.value != config.skin.primary_skin.value
		if guiSkinChanged:
			if config.skin.primary_skin.value == "MetrixHD/skin.MySkin.xml":
				try:
					if config.plugins.MyMetrixLiteOther.EHDenabled.value != "0":
						from Plugins.Extensions.MyMetrixLite.ActivateSkinSettings import ActivateSkinSettings
						ActivateSkinSettings().RefreshIcons(True)  # Restore default icons if old skin is Metrix.
				except Exception:
					pass
			config.skin.primary_skin.value = config.skin.guiSkin.value
			config.skin.primary_skin.save()
		if config.skin.lcdSkin.value != config.skin.display_skin.value:
			config.skin.display_skin.value = config.skin.lcdSkin.value
			config.skin.display_skin.save()

		if not guiSkinChanged and (config.channelSelection.screenStyle.isChanged() or config.channelSelection.widgetStyle.isChanged()):
			from Screens.ChannelSelection import ChannelSelectionSetup
			ChannelSelectionSetup.updateSettings(self.session)

		if guiSkinChanged and config.usage.fastSkinReload.value:
			Processing.instance.setDescription(_("Loading skin..."))
			Processing.instance.showProgress(endless=True)
			self.saveAll()
			open("/etc/.restore_skins", "w").close()
			from skin import reloadSkins
			reloadSkins()
			for plugin in plugins.getPlugins(PluginDescriptor.WHERE_SKINCHANGE):
				plugin(session=self.session)
			self.session.reloadDialogs()
			Processing.instance.hideProgress()
			self.close(True)
			return
		elif not guiSkinChanged and config.skin.FallbackFont.isChanged():
			fallbackFont = resolveFilename(SCOPE_FONTS, config.skin.FallbackFont.value)
			if isfile(fallbackFont):
				addFont(fallbackFont, "Fallback", 100, -1, 0)
		Setup.keySave(self)

	def restartGUICallback(self, answer):
		if answer:
			self.session.open(TryQuitMainloop, QUIT_RESTART)
		else:
			self.close(True)

	def loadPreview(self):
		def loadImage(root):
			directory, file = split(current.value)
			path = join(root, directory, self.PREVIEW.get(file, "prev.png"))
			if not isfile(path):
				path = self.noPreview
			if isfile(path):
				self.picLoad.startDecode(path)
				self["preview"].show()
			else:
				self["preview"].hide()

		if self.picLoad:
			current = self.getCurrentItem()
			match current:
				case config.skin.guiSkin:
					loadImage(self.guiRoot)
				case config.skin.lcdSkin:
					loadImage(self.lcdRoot)
				case _:
					self["preview"].hide()
