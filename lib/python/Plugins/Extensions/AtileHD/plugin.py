from os import listdir, makedirs, mkdir, remove, symlink
from os.path import basename, exists, isdir, islink, join, realpath
from shutil import rmtree

from enigma import eTimer

from Components.ActionMap import ActionMap, HelpableActionMap
from Components.config import ConfigNothing, ConfigNumber, ConfigSelection, ConfigSubsection, ConfigYesNo, NoSave, config
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.SkinSelection import SkinSelection
from Screens.Standby import QUIT_RESTART, TryQuitMainloop
from Tools.Directories import SCOPE_GUISKIN, SCOPE_SKINS, resolveFilename
from Tools.LoadPixmap import LoadPixmap

config.plugins.AtileHD = ConfigSubsection()
config.plugins.AtileHD.refreshInterval = ConfigNumber(default=10)
config.plugins.AtileHD.woeid = ConfigNumber(default=638242)
config.plugins.AtileHD.tempUnit = ConfigSelection(default="Celsius", choices=[("Celsius", _("Celsius")), ("Fahrenheit", _("Fahrenheit"))])


class AtileHelper:
	EXCLUDED_SKINS = {
		"KravenVB/skin.xml",
		"MetrixHD/skin.MySkin.xml",
		"MetrixHD/skin.xml",
		"OverlayHD/skin.xml",
		"SevenHD/skin.xml",
		"Umbra/FHD/skin.xml",
		"Umbra/HD/skin.xml",
		"Umbra/WQHD/skin.xml",
		"Umbra/skin.xml"
	}

	def getSkinName(self):
		return config.skin.primary_skin.value.replace("/skin.xml", "")

	def showPreview(self, widget, skinDir, fileName):
		preview = join(skinDir, "preview", f"preview_{fileName.replace('.xml', '.png')}") if fileName else ""
		if widget.instance and exists(preview):
			widget.instance.setPixmapFromFile(preview)
			widget.show()
		else:
			widget.hide()


atileHelper = AtileHelper()


class AtileHD_Config(Setup):
	skin = """
	<screen name="AtileHD_Config" position="center,center" size="1180,570" resolution="1280,720">
		<widget name="config" position="10,10" size="700,350" enableWrapAround="1" font="Regular;25" itemHeight="35" scrollbarMode="showOnDemand" />
		<widget name="Picture" position="730,10" size="440,248" alphatest="blend" scale="centerScaled" />
		<widget name="footnote" position="10,e-185" size="e-20,25" font="Regular;20" valign="center" />
		<widget name="description" position="10,e-160" size="e-20,100" font="Regular;20" valign="center" />
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="390,e-50" size="180,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="580,e-50" size="180,40" backgroundColor="key_blue" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_menu" render="Label" position="e-200,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-100,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	ATILE_DEFAULT_FILES = {
		"colors": "colors_atile_Grey_transparent.xml",
		"font": "font_atile_Roboto.xml"
	}

	def __init__(self, session):
		self.parts = (  # File prefix, user file and label of each skin part.
			("colors", "skin_user_colors.xml", _("Style:")),
			("font", "skin_user_header.xml", _("Font:")),
			("background", "skin_user_background.xml", _("Background:")),
			("sb", "skin_user_sb.xml", _("Background selected:")),
			("infobar", "skin_user_infobar.xml", "%s:" % _("InfoBar")),
			("sib", "skin_user_sib.xml", "%s:" % _("2nd InfoBar")),
			("ch_se", "skin_user_ch_se.xml", _("Channel selection:")),
			("ev", "skin_user_ev.xml", _("Event view:")),
			("clock", "skin_user_clock.xml", _("Clock:")),
			("ul", "skin_user_ul.xml", _("User logo:"))
		)
		self.startSkin = config.skin.primary_skin.value
		self.changedScreens = False
		self.changeSkinItem = ConfigNothing()
		self.weatherItem = ConfigNothing()
		self.initSettings()
		Setup.__init__(self, session, setup=None)
		self.mandatoryWidgets = ["config"]  # Accept older skin screens without footnote and description.
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText(_("About"))
		self["Picture"] = Pixmap()
		self["colorActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyYellow, _("Open the additional screens")),
			"blue": (self.keyBlue, _("Show the about screen"))
		}, prio=0, description=_("Skin Setup Actions"))
		if self.startSkin == "skin.xml":
			self.onLayoutFinish.append(self.openSkinSelectionDelayed)

	def initSettings(self):
		self.currentSkin = atileHelper.getSkinName()
		self.skinDir = resolveFilename(SCOPE_SKINS, self.currentSkin)
		self.partSettings = []
		self.mySkinActive = None
		if self.currentSkin != "skin.xml":
			isAtile = self.currentSkin == "AtileHD"
			files = listdir(self.skinDir)
			for prefix, userFile, label in self.parts:
				searchText = f"{prefix}_atile_" if isAtile else f"{prefix}_"
				defaultFile = self.ATILE_DEFAULT_FILES.get(prefix, f"{prefix}_Original.xml") if isAtile else f"{prefix}_Original.xml"
				screensDir = join(self.skinDir, "allScreens", prefix)
				partFiles = files + listdir(screensDir) if isdir(screensDir) else files
				choices = [(join(screensDir, x) if exists(join(screensDir, x)) else join(self.skinDir, x), x.replace(searchText, "").replace(".xml", "").replace("_", " ")) for x in sorted(partFiles, key=str.lower) if x.startswith(searchText) and x.endswith(".xml")]
				choices.append(("default", _("Default")))
				userPath = join(self.skinDir, userFile)
				if not exists(userPath):  # Link the default file if the user file is missing.
					defaultPath = join(self.skinDir, defaultFile)
					if not exists(defaultPath):
						defaultPath = join(screensDir, defaultFile)
					if exists(defaultPath):
						if islink(userPath):
							remove(userPath)
						symlink(defaultPath, userPath)
				current = realpath(userPath) if exists(userPath) else "default"
				self.partSettings.append((label, NoSave(ConfigSelection(default=current, choices=choices)), userFile))
			self.mySkinActive = NoSave(ConfigYesNo(default=exists(join(self.skinDir, "mySkin"))))

	def createSetup(self):
		self.list = []
		if self.mySkinActive:
			self.list.append((_("Enable %s pro:") % self.currentSkin, self.mySkinActive))
			self.list.extend([x[:2] for x in self.partSettings if len(x[1].choices) > 1])
		self.list.append((_("Change skin"), self.changeSkinItem))
		self.list.append((_("Weather settings"), self.weatherItem))
		self["config"].setList(self.list)
		self.setTitle(_("%s - Setup") % self.currentSkin)

	def changedEntry(self):
		Setup.changedEntry(self)
		self.selectionChanged()

	def selectionChanged(self):
		Setup.selectionChanged(self)
		self["key_yellow"].setText(f"{self.currentSkin} pro" if self.mySkinActive and self.mySkinActive.value else "")
		currentItem = self.getCurrentItem()
		fileName = next((basename(x[1].value) for x in self.partSettings if x[1] is currentItem), None)
		atileHelper.showPreview(self["Picture"], self.skinDir, fileName)

	def keySelect(self):
		currentItem = self.getCurrentItem()
		if currentItem is self.changeSkinItem:
			self.openSkinSelection()
		elif currentItem is self.weatherItem:
			try:
				from Plugins.Extensions.WeatherPlugin.setup import MSNWeatherPluginEntriesListConfigScreen  # The WeatherPlugin is optional.
				self.session.open(MSNWeatherPluginEntriesListConfigScreen)
			except ImportError:
				self.session.open(MessageBox, _("'WeatherPlugin' is not installed!"), MessageBox.TYPE_INFO)
		else:
			Setup.keySelect(self)

	def keySave(self):
		if self["config"].isChanged():
			for label, configElement, userFile in self.partSettings:
				userPath = join(self.skinDir, userFile)
				if exists(userPath) or islink(userPath):
					remove(userPath)
				if configElement.value != "default":
					symlink(configElement.value, userPath)
			mySkinOff = join(self.skinDir, "mySkin_off")
			mySkin = join(self.skinDir, "mySkin")
			if not exists(mySkinOff):
				mkdir(mySkinOff)
			if self.mySkinActive.value:
				if not exists(mySkin):
					symlink("mySkin_off", mySkin)
			elif islink(mySkin):
				remove(mySkin)
			elif exists(mySkin):
				rmtree(mySkin)
			self.restartGUI()
		elif self.changedScreens or config.skin.primary_skin.value != self.startSkin:
			self.restartGUI()
		else:
			self.close()

	def keyCancel(self):
		if self.changedScreens and not self["config"].isChanged():
			self.restartGUI()
		else:
			Setup.keyCancel(self)

	def keyYellow(self):
		def keyYellowCallback():
			self.changedScreens = True
			self["config"].setCurrentIndex(0)

		if self.mySkinActive and self.mySkinActive.value:
			self.session.openWithCallback(keyYellowCallback, AtileHDScreens)
		else:
			self["config"].setCurrentIndex(0)

	def keyBlue(self):
		self.session.open(MessageBox, "%s\n\n%s" % (_("%s Setup") % self.currentSkin, _("Personalize your Skin")), MessageBox.TYPE_INFO, windowTitle=_("About"))

	def openSkinSelection(self):
		self.session.openWithCallback(self.skinChanged, SkinSelection)

	def openSkinSelectionDelayed(self):
		self.delayTimer = eTimer()
		self.delayTimer.callback.append(self.openSkinSelection)
		self.delayTimer.start(200, True)

	def skinChanged(self, result=None):
		if atileHelper.getSkinName() == "skin.xml":
			self.restartGUI()
		else:
			self.initSettings()
			self.createSetup()

	def restartGUI(self):
		def restartGUICallback(answer):
			if answer:
				self.session.open(TryQuitMainloop, QUIT_RESTART)
			else:
				self.close()

		self.session.openWithCallback(restartGUICallback, MessageBox, _("Restart necessary, restart GUI now?"), MessageBox.TYPE_YESNO, windowTitle=_("Message"))


class AtileHDScreens(Screen):
	skin = """
	<screen name="AtileHDScreens" title="Additional screens" position="center,center" size="1180,570" resolution="1280,720">
		<widget source="menu" render="Listbox" position="10,10" size="700,e-80">
			<template name="Default" fonts="Regular;25" itemHeight="35">
				<mode name="default">
					<pixmap index="Image" position="5,5" size="25,25" alpha="blend" scale="centerScaled" />
					<text index="Text" position="40,0" size="650,35" font="0" horizontalAlignment="left" verticalAlignment="center" />
				</mode>
			</template>
		</widget>
		<widget name="Picture" position="730,10" size="440,248" alphatest="blend" scale="centerScaled" />
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		currentSkin = atileHelper.getSkinName()
		self.setTitle(_("%s additional screens") % currentSkin)
		self["title"] = StaticText(self.getTitle())
		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("On"))
		self["Picture"] = Pixmap()
		self["menu"] = List([], indexNames={"File": 0, "Text": 1, "Image": 2})
		self["shortcuts"] = ActionMap(["OkCancelActions", "ColorActions"], {
			"ok": self.toggleScreen,
			"cancel": self.close,
			"red": self.close,
			"green": self.toggleScreen
		}, prio=-2)
		self.skinDir = resolveFilename(SCOPE_SKINS, currentSkin)
		self.screensDir = join(self.skinDir, "allScreens")
		self.skinPartsDir = join(self.skinDir, "skinparts")
		self.mySkinDir = join(self.skinDir, "mySkin_off")
		self.enabledPic = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/lock_on.png"))
		self.disabledPic = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/lock_off.png"))
		self["menu"].onSelectionChanged.append(self.selectionChanged)
		self.onLayoutFinish.append(self.createMenuList)

	def selectionChanged(self):
		current = self["menu"].getCurrent()
		if current:
			atileHelper.showPreview(self["Picture"], self.skinDir, current[0])
			self["key_green"].setText(_("Off") if current[2] == self.enabledPic else _("On"))

	def createMenuList(self):
		for directory in (self.screensDir, self.skinPartsDir, self.mySkinDir):
			if not exists(directory):
				makedirs(directory)
		globalSkinPartsDir = resolveFilename(SCOPE_SKINS, "skinparts")
		if isdir(globalSkinPartsDir):
			for pack in listdir(globalSkinPartsDir):
				packDir = join(globalSkinPartsDir, pack)
				if isdir(packDir):
					for part in listdir(packDir):
						partFile = join(packDir, part, f"{part}_Atile.xml")
						if exists(partFile):
							screenFile = join(self.screensDir, f"skin_{part}.xml")
							if not exists(screenFile):
								symlink(partFile, screenFile)
							partLink = join(self.skinPartsDir, part)
							if not exists(partLink):
								symlink(join(packDir, part), partLink)
		menuList = []
		for fileName in sorted(listdir(self.screensDir), key=str.lower):
			if fileName.startswith("skin_") and fileName.endswith(".xml"):
				screenFile = join(self.screensDir, fileName)
				if exists(screenFile):
					linkedFile = join(self.mySkinDir, fileName)
					if exists(linkedFile) and not islink(linkedFile):  # Replace a copied file by a link.
						remove(linkedFile)
						symlink(screenFile, linkedFile)
					menuList.append((fileName, fileName.replace("skin_", "").replace(".xml", "").replace("_", " "), self.enabledPic if exists(linkedFile) else self.disabledPic))
				elif islink(screenFile):  # Remove a broken link.
					remove(screenFile)
		self["menu"].updateList(menuList)
		self.selectionChanged()

	def toggleScreen(self):
		current = self["menu"].getCurrent()
		if current:
			linkedFile = join(self.mySkinDir, current[0])
			if current[2] == self.enabledPic:
				remove(linkedFile)
			else:
				symlink(join(self.screensDir, current[0]), linkedFile)
			self.createMenuList()


def main(session, **kwargs):
	session.open(AtileHD_Config)


def menu(menuid, **kwargs):
	return [(_("Setup - %s") % atileHelper.getSkinName(), main, "atilehd_setup", None)] if menuid == "system" and config.skin.primary_skin.value not in atileHelper.EXCLUDED_SKINS else []


def Plugins(**kwargs):
	return [PluginDescriptor(name=_("%s Setup") % atileHelper.getSkinName(), description=_("Personalize your Skin"), where=PluginDescriptor.WHERE_MENU, icon="plugin.png", fnc=menu)]
