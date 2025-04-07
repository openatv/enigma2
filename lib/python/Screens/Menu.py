from gettext import dgettext
from os.path import isdir, isfile
from xml.etree.ElementTree import parse

from enigma import eTimer

from skin import findSkinScreen, menus
from Components.ActionMap import HelpableNumberActionMap, HelpableActionMap
from Components.AVSwitch import avSwitch
from Components.config import ConfigDictionarySet, NoSave, config, configfile
from Components.Pixmap import Pixmap
from Components.PluginComponent import plugins
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.Screen import Screen, ScreenSummary
from Screens.Setup import Setup
from Tools.BoundFunction import boundFunction
from Tools.Directories import SCOPE_GUISKIN, SCOPE_SKINS, resolveFilename
from Tools.LoadPixmap import LoadPixmap

MENU_TEXT = 0
MENU_MODULE = 1
MENU_KEY = 2
MENU_WEIGHT = 3
MENU_DESCRIPTION = 4
MENU_IMAGE = 5
MENU_SORT = 6
MAX_MENU = 7

PLUGIN_TEXT = 0
PLUGIN_MODULE = 1
PLUGIN_KEY = 2
PLUGIN_WEIGHT = 3
PLUGIN_CLOSEALL = 4

WIDGET_NUMBER_TEXT = 0
WIDGET_IMAGE = 1
WIDGET_NUMBER = 2
WIDGET_TEXT = 3
WIDGET_DESCRIPTION = 4
WIDGET_KEY = 5
WIDGET_WEIGHT = 6
WIDGET_MODULE = 7

imageCache = {}
lastKey = None

# Read the menu.
file = open(resolveFilename(SCOPE_SKINS, "menu.xml"))
mdom = parse(file)
file.close()


def findMenu(key):
	menuList = mdom.getroot().findall(f".//menu[@key='{key}']")
	count = len(menuList)
	if menuList:
		for index, menu in enumerate(menuList):
			print(f"[Menu] Found menu entry '{menu.get('text', '* Unknown *')}' ({index + 1} of {count}).")
		menu = menuList[0]
	else:
		print(f"[Menu] Error: Menu '{key}' not found!")
		menu = None
	return menu


def menuEntryName(name):
	def splitUpperCase(name, maxLen):
		for character in range(len(name), 0, -1):
			if name[character - 1].isupper() and character - 1 and character - 1 <= maxLen:
				return name[:character - 1] + "-:-" + name[character - 1:]
		return name

	def splitLowerCase(name, maxLen):
		for character in range(len(name), 0, -1):
			if name[character - 1].islower() and character - 1 and character - 1 <= maxLen:
				return name[:character - 1] + "-:-" + name[character - 1:]
		return name

	def splitName(name, maxLen):
		for separator in (" ", "-", "/"):
			pos = name.rfind(separator, 0, maxLen + 1)
			if pos > 1:
				return [name[:pos + 1] if pos + 1 <= maxLen and separator != " " else name[:pos], name[pos + 1:]]
		return splitUpperCase(name, maxLen).split("-:-", 1)

	maxRow = 3
	maxLen = 18
	nameSplit = []
	if len(name) > maxLen and maxRow > 1:
		nameSplit = splitName(name, maxLen)
		if len(nameSplit) == 1 or (len(nameSplit) == 2 and len(nameSplit[1]) > maxLen * (maxRow - 1)):
			tmp = splitLowerCase(name, maxLen).split("-:-", 1)
			if len(tmp[0]) > len(nameSplit[0]) or len(nameSplit) < 2:
				nameSplit = tmp
		for row in range(1, maxRow):
			if len(nameSplit) > row and len(nameSplit) < maxRow and len(nameSplit[row]) > maxLen:
				tmp = splitName(nameSplit[row], maxLen)
				if len(tmp) == 1 or (len(tmp) == 2 and len(tmp[1]) > maxLen * (maxRow - row)):
					tmp = splitLowerCase(nameSplit[row], maxLen).split("-:-", 1)
				if len(tmp) == 2:
					nameSplit.pop(row)
					nameSplit.extend(tmp)
			else:
				break
	return name if len(nameSplit) < 2 else "\n".join(nameSplit)


class Menu(Screen, ProtectedScreen):
	skin = """
	<screen name="Menu" title="Menu"  position="center,center" size="980,600" resolution="1280,720">
		<widget source="menu" render="Listbox" position="0,0" size="730,490">
			<convert type="TemplatedMultiContent">
				{
				"templates":
					{
					"default": (35,
						[
						MultiContentEntryText(pos=(15, 0), size=(710, 35), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=0)
						]),
					"text": (35,
						[
						MultiContentEntryText(pos=(20, 0), size=(660, 35), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=3),
						]),
					"number": (35,
						[
						MultiContentEntryText(pos=(15, 0), size=(30, 35), font=0, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=2),
						MultiContentEntryText(pos=(65, 0), size=(610, 35), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=3),
						]),
					"image": (35,
						[
						MultiContentEntryPixmapAlphaBlend(pos=(15, 2), size=(31, 31), png=1, flags=BT_SCALE | BT_KEEP_ASPECT_RATIO),
						MultiContentEntryText(pos=(65, 0), size=(610, 35), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=3),
						]),
					"both": (35,
						[
						MultiContentEntryPixmapAlphaBlend(pos=(15, 2), size=(31, 31), png=1, flags=BT_SCALE | BT_KEEP_ASPECT_RATIO),
						MultiContentEntryText(pos=(65, 0), size=(40, 35), font=0, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=2),
						MultiContentEntryText(pos=(125, 0), size=(550, 35), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=3),
						])
					},
				"fonts": [parseFont("Regular;25")]
				}
			</convert>
		</widget>
		<widget name="menuimage" position="780,0" size="200,200" alphatest="blend" conditional="menuimage" scaleFlags="scaleCenter" transparent="1" />
		<widget source="description" render="Label" position="0,e-110" size="e,50" conditional="description" font="Regular;20" valign="center" />
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="390,e-50" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="580,e-50" size="180,40" backgroundColor="key_blue" conditional="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_menu" render="Label" position="e-300,e-50" size="90,40" backgroundColor="key_back" conditional="key_menu" font="Regular;20" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_info" render="Label" position="e-200,e-50" size="90,40" backgroundColor="key_back" conditional="key_info" font="Regular;20" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-100,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" conditional="key_help" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, parentMenu, PluginLanguageDomain=None):
		self.session = session
		self.parentMenu = parentMenu
		self.pluginLanguageDomain = PluginLanguageDomain
		Screen.__init__(self, session, enableHelp=True)
		self.menuList = []
		self["menu"] = List(self.menuList)
		self["menu"].onSelectionChanged.append(self.selectionChanged)
		self["menuimage"] = Pixmap()
		self["description"] = StaticText()
		self["key_menu"] = StaticText(_("MENU"))
		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		menuImageLibrary = resolveFilename(SCOPE_GUISKIN, "mainmenu")
		self.menuImageLibrary = menuImageLibrary if isdir(menuImageLibrary) else None
		self.showNumericHelp = False
		self.sortMode = False
		self.selectedEntry = None
		self.subMenuSort = None
		self.createMenuList()
		ProtectedScreen.__init__(self)  # ProtectedScreen needs self.menuID
		# For the skin: first try a menu_<menuID>, then Menu.
		self.skinName = []
		if self.menuID is not None:
			if config.usage.menuType.value == "horzanim" and findSkinScreen("Animmain"):
				self.skinName.append("Animmain")
			elif config.usage.menuType.value == "horzicon" and findSkinScreen("Iconmain"):
				self.skinName.append("Iconmain")
			else:
				self.skinName.append(f"Menu{self.menuID}")
				self.skinName.append(f"menu_{self.menuID}")
		self.skinName.append("Menu")
		if config.usage.menuType.value == "horzanim" and findSkinScreen("Animmain"):
			self.onShown.append(self.openTestA)
		elif config.usage.menuType.value == "horzicon" and findSkinScreen("Iconmain"):
			self.onShown.append(self.openTestB)
		self["menuActions"] = HelpableNumberActionMap(self, ["OkCancelActions", "MenuActions", "ColorActions", "NumberActions", "TextActions"], {
			"ok": (self.okbuttonClick, _("Select the current menu item")),
			"cancel": (self.closeNonRecursive, _("Exit menu")),
			"close": (self.closeRecursive, _("Exit all menus")),
			"menu": (self.keySetupMenu, _("Change OSD Settings")),
			"red": (self.closeNonRecursive, _("Exit menu")),
			"1": (self.keyNumberGlobal, _("Direct menu item selection")),
			"2": (self.keyNumberGlobal, _("Direct menu item selection")),
			"3": (self.keyNumberGlobal, _("Direct menu item selection")),
			"4": (self.keyNumberGlobal, _("Direct menu item selection")),
			"5": (self.keyNumberGlobal, _("Direct menu item selection")),
			"6": (self.keyNumberGlobal, _("Direct menu item selection")),
			"7": (self.keyNumberGlobal, _("Direct menu item selection")),
			"8": (self.keyNumberGlobal, _("Direct menu item selection")),
			"9": (self.keyNumberGlobal, _("Direct menu item selection")),
			"0": (self.keyNumberGlobal, _("Direct menu item selection")),
			"textlong": (self.keyText, _("Switch to 720p video"))
		}, prio=0, description=_("Menu Common Actions"))
		self["navigationActions"] = HelpableActionMap(self, ["NavigationActions"], {
			"top": (self.keyTop, _("Move to first line / screen")),
			"pageUp": (self.keyPageUp, _("Move up a screen")),
			"up": (self.keyUp, _("Move up a line")),
			# "first": (self.keyFirst, _("Jump to first item in list or the start of text")),
			# "last": (self.keyLast, _("Jump to last item in list or the end of text")),
			"down": (self.keyDown, _("Move down a line")),
			"pageDown": (self.keyPageDown, _("Move down a screen")),
			"bottom": (self.keyBottom, _("Move to last line / screen"))
		}, prio=-1, description=_("Menu Navigation Actions"))
		if config.usage.menuSortOrder.value == "user":
			self["editActions"] = HelpableActionMap(self, ["ColorActions"], {
				"green": (self.keyGreen, _("Toggle item move mode on/off")),
				"yellow": (self.keyYellow, _("Toggle hide/show of the current item")),
				"blue": (self.toggleSortMode, _("Toggle item edit mode on/off"))
			}, prio=0, description=_("Menu Edit Actions"))
		title = parentMenu.get("title", "") or None
		title = title and (dgettext(self.pluginLanguageDomain, title) if self.pluginLanguageDomain else _(title))
		if title is None:
			title = _(parentMenu.get("text", ""))
		self.setTitle(title)
		self.number = 0
		self.nextNumberTimer = eTimer()
		self.nextNumberTimer.callback.append(self.okbuttonClick)
		if len(self.menuList) == 1:  # Does this menu have only one item, if so just run that item.
			self.onExecBegin.append(self.singleItemMenu)
		self.onLayoutFinish.append(self.layoutFinished)

	def createMenuList(self, showNumericHelp=False):
		self.menuID = self.parentMenu.get("key")
		self.menuList = []
		for menu in self.parentMenu:  # Walk through the menu node list.
			if not menu.tag:
				continue
			if menu.tag == "item":
				itemLevel = int(menu.get("level", 0))
				if itemLevel <= config.usage.setup_level.index:
					data = self.addItem(menu)
					if data:
						self.menuList.append(data)
			elif menu.tag == "menu":
				itemLevel = int(menu.get("level", 0))
				if itemLevel <= config.usage.setup_level.index:
					data = self.addMenu(menu)
					if data:
						self.menuList.append(data)
		if self.menuID:
			for plugin in plugins.getPluginsForMenu(self.menuID):  # Plugins.
				# print(f"[Menu] DEBUG 1: Plugin data={str(plugin)}.")
				pluginKey = plugin[PLUGIN_KEY]  # Check if a plugin overrides an existing menu.
				for entry in self.menuList:
					if entry[PLUGIN_KEY] == pluginKey:
						self.menuList.remove(entry)
						break
				description = plugins.getDescriptionForMenuEntryID(self.menuID, pluginKey)  # It is assumed that description is already translated by the plugin!
				if "%s %s" in description:
					description = description % getBoxDisplayName()
				image = self.getMenuEntryImage(plugin[PLUGIN_KEY], lastKey)
				if len(plugin) > PLUGIN_CLOSEALL and plugin[PLUGIN_CLOSEALL]:  # Was "len(plugin) > 4".
					self.menuList.append((plugin[PLUGIN_TEXT], boundFunction(plugin[PLUGIN_MODULE], self.session, self.close), plugin[PLUGIN_KEY], plugin[PLUGIN_WEIGHT] or 50, description, image))
				else:
					self.menuList.append((plugin[PLUGIN_TEXT], boundFunction(plugin[PLUGIN_MODULE], self.session), plugin[PLUGIN_KEY], plugin[PLUGIN_WEIGHT] or 50, description, image))
		if config.usage.menuSortOrder.value == "user" and self.menuID == "mainmenu":
			idList = []
			for plugin in plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_EVENTINFO]):
				# print(f"[Menu] DEBUG 2: Plugin data={str(plugin)}.")
				plugin.id = (plugin.name.lower()).replace(" ", "_")
				if plugin.id not in idList:
					idList.append(plugin.id)
		if self.menuID is not None and config.usage.menuSortOrder.value == "user":
			self.subMenuSort = NoSave(ConfigDictionarySet())
			self.subMenuSort.value = config.usage.menu_sort_weight.getConfigValue(self.menuID, "submenu") or {}
			for index, entry in enumerate(self.menuList):
				data = list(self.menuList.pop(index))
				sort = self.subMenuSort.getConfigValue(data[MENU_KEY], "sort") or data[MENU_WEIGHT]
				data.append(sort)
				self.menuList.insert(index, tuple(data))
				self.subMenuSort.changeConfigValue(data[MENU_KEY], "sort", sort)
			self.fullMenuList = list(self.menuList)
		if config.usage.menuSortOrder.value == "alpha":  # Sort by menu item text.
			self.menuList.sort(key=lambda x: x[MENU_TEXT].lower())
		elif config.usage.menuSortOrder.value == "user":  # Sort by user defined sequence.
			self["key_blue"].setText(_("Edit Mode On"))
			self.hideShowEntries()
		else:  # Sort by menu item weight.
			self.menuList.sort(key=lambda x: int(x[MENU_WEIGHT]))
		self.setMenuList(self.menuList)

	def addItem(self, menu):
		requires = menu.get("requires")
		if requires:
			if requires[0] == "!":
				if BoxInfo.getItem(requires[1:], False):
					return None
			elif not BoxInfo.getItem(requires, False):
				return None
		conditional = menu.get("conditional")
		if conditional and not eval(conditional):
			return None
		text = self.processDisplayedText(menu.get("text"))
		key = menu.get("key", "undefined")
		weight = menu.get("weight", 50)
		description = self.processDisplayedText(menu.get("description"))
		image = self.getMenuEntryImage(key, lastKey)
		for menuItem in menu:
			if menuItem.tag == "screen":
				module = menuItem.get("module")
				screen = menuItem.get("screen")
				if screen is None:
					screen = module
				module = f"Screens.{module}" if module else ""
				screen = f"{screen}, {menuItem.text or ''}"  # Check for arguments, they will be appended to the openDialog call.
				return (text, boundFunction(self.runScreen, (module, screen)), key, weight, description, image)
			elif menuItem.tag == "plugin":
				extensions = menuItem.get("extensions")
				system = menuItem.get("system")
				screen = menuItem.get("screen")
				if extensions:
					module = extensions
				elif system:
					module = system
				if screen is None:
					screen = module
				if extensions:
					module = f"Plugins.Extensions.{extensions}.plugin"
				elif system:
					module = f"Plugins.SystemPlugins.{system}.plugin"
				else:
					module = ""
				screen = f"{screen}, {menuItem.text or ''}"  # Check for arguments, they will be appended to the openDialog call.
				return (text, boundFunction(self.runScreen, (module, screen)), key, weight, description, image)
			elif menuItem.tag == "code":
				return (text, boundFunction(self.execText, menuItem.text), key, weight, description, image)
			elif menuItem.tag == "setup":
				setupKey = menuItem.get("setupKey", "Undefined")
				return (text, boundFunction(self.openSetup, setupKey), key, weight, description, image)
		return (text, self.nothing, key, weight, description, image)

	def addMenu(self, menu):
		requires = menu.get("requires")
		if requires:
			if requires[0] == "!":
				if BoxInfo.getItem(requires[1:], False):
					return
			elif not BoxInfo.getItem(requires, False):
				return
		text = self.processDisplayedText(menu.get("text"))
		key = menu.get("key", "undefined")
		weight = menu.get("weight", 50)
		description = self.processDisplayedText(menu.get("description"))
		image = self.getMenuEntryImage(key, lastKey)
		if menu.get("flushConfigOnClose"):
			module = boundFunction(self.session.openWithCallback, self.menuClosedWithConfigFlush, Menu, menu)
		else:
			module = boundFunction(self.session.openWithCallback, self.menuClosed, Menu, menu)
		# TODO: Add check if !empty(menu.childNodes).
		return (text, module, key, weight, description, image)

	def processDisplayedText(self, text):
		text = dgettext(self.pluginLanguageDomain, text) if self.pluginLanguageDomain else _(text) if text else ""
		if "%s %s" in text:
			text = text % getBoxDisplayName()
		return text

	def getMenuEntryImage(self, key, lastKey):
		global imageCache
		image = imageCache.get(key)
		if image is None:
			imageFile = resolveFilename(SCOPE_GUISKIN, f"mainmenu/{key}.png" if self.menuImageLibrary else menus.get(key, ""))
			if imageFile and isfile(imageFile):
				image = LoadPixmap(imageFile, cached=True)
				if image:
					print(f"[Menu] Menu image for menu ID '{key}' is '{imageFile}'.")
					imageCache[key] = image
				else:
					print(f"[Menu] Error: Unable to load image '{imageFile}'!")
					if lastKey:
						image = imageCache.get(lastKey)
		if image is None:
			image = imageCache.get("default")
			if image is None:
				imageFile = resolveFilename(SCOPE_GUISKIN, "mainmenu/missing.png" if self.menuImageLibrary else menus.get("default", ""))
				if imageFile and isfile(imageFile):
					image = LoadPixmap(imageFile, cached=True)
					if image:
						print(f"[Menu] Default menu image is '{imageFile}'.")
						imageCache["default"] = image
					else:
						print(f"[Menu] Error: Unable to load default image '{imageFile}'!")
						imageCache["default"] = "N/A"
				else:
					print(f"[Menu] Error: Default image '{imageFile}' is not a file!")
					imageCache["default"] = "N/A"
			elif image == "N/A":
				image = None
		return image

	def setMenuList(self, menuList):
		menu = []
		for number, entry in enumerate(menuList):
			number += 1
			numberText = f"{number}  {entry[MENU_TEXT]}" if config.usage.menuEntryStyle.value in ("number", "both") else entry[MENU_TEXT]  # This is for compatibility with older skins.
			menu.append((numberText, entry[MENU_IMAGE], str(number), entry[MENU_TEXT], entry[MENU_DESCRIPTION], entry[MENU_KEY], entry[MENU_WEIGHT], entry[MENU_MODULE]))
		self["menu"].setList(menu)

	def layoutFinished(self):
		self["menu"].enableAutoNavigation(False)
		self["menu"].setStyle(config.usage.menuEntryStyle.value)
		self.selectionChanged()

	def selectionChanged(self):
		current = self["menu"].getCurrent()
		if current:
			self["menuimage"].instance.setPixmap(current[WIDGET_IMAGE])
			self["description"].setText(current[WIDGET_DESCRIPTION])
			if self.sortMode:
				self["key_yellow"].setText(_("Show") if self.subMenuSort.getConfigValue(current[WIDGET_KEY], "hidden") else _("Hide"))
			else:
				self["key_yellow"].setText("")

	def okbuttonClick(self):
		global lastKey
		self.resetNumberKey()
		current = self["menu"].getCurrent()
		if current and current[WIDGET_MODULE]:
			lastKey = current[WIDGET_KEY]
			current[WIDGET_MODULE]()

	def menuClosedWithConfigFlush(self, *result):
		configfile.save()
		self.menuClosed(*result)

	def menuClosed(self, *result):
		global lastKey
		if result and result[0]:
			lastKey = None
			self.close(True)

	def execText(self, text):
		exec(text)

	def runScreen(self, arg):
		# arg[0] is the module (as string)
		# arg[1] is Screen inside this module
		#	plus possible arguments, as
		#	string (as we want to reference
		#	stuff which is just imported)
		if arg[0] != "":
			exec(f"from {arg[0]} import {arg[1].split(',')[0]}", globals())
			self.openDialog(*eval(arg[1]))

	def nothing(self):  # Dummy.
		pass

	def openDialog(self, *dialog):  # In every layer needed.
		self.session.openWithCallback(self.menuClosed, *dialog)

	def openSetup(self, dialog):
		self.session.openWithCallback(self.menuClosed, Setup, dialog)

	def openTestA(self):
		self.session.open(AnimMain, self.menuList, self.getTitle())
		self.close()

	def openTestB(self):
		self.session.open(IconMain, self.menuList, self.getTitle())
		self.close()

	def singleItemMenu(self):
		self.onExecBegin.remove(self.singleItemMenu)
		if config.usage.menuType.value == "horzanim" and findSkinScreen("Animmain"):
			return
		elif config.usage.menuType.value == "horzicon" and findSkinScreen("Iconmain"):
			return
		else:
			self.okbuttonClick()

	def closeRecursive(self):
		self.resetNumberKey()
		self.close(True)

	def createSummary(self):
		if config.usage.menuType.value == "standard":
			return MenuSummary

	def isProtected(self):
		if config.ParentalControl.setuppinactive.value:
			if config.ParentalControl.config_sections.main_menu.value and not (hasattr(self.session, "infobar") and self.session.infobar is None):
				return self.menuID == "mainmenu"
			elif config.ParentalControl.config_sections.configuration.value and self.menuID == "setup":
				return True
			elif config.ParentalControl.config_sections.timer_menu.value and self.menuID == "timermenu":
				return True
			elif config.ParentalControl.config_sections.standby_menu.value and self.menuID == "shutdown":
				return True

	def keyOk(self):
		if self.sortMode and len(self.menuList):
			current = self["menu"].getCurrent()
			select = False
			if self.selectedEntry is None:
				select = True
			elif self.selectedEntry != current[WIDGET_KEY]:
				select = True
			if not select:
				self["key_green"].setText(_("Move Mode On"))
				self.selectedEntry = None
			else:
				self["key_green"].setText(_("Move Mode Off"))
			for entry in self.menuList:
				if current[WIDGET_KEY] == entry[MENU_KEY] and select is True:
					self.selectedEntry = current[WIDGET_KEY]
					break
				elif current[WIDGET_KEY] == entry[MENU_KEY] and select is False:
					self.selectedEntry = None
					break
		elif not self.sortMode:
			self.okbuttonClick()

	def keySetupMenu(self):
		self.openSetup("UserInterface")

	def keyYellow(self):
		if self.sortMode:
			key = self["menu"].getCurrent()[WIDGET_KEY]
			hidden = self.subMenuSort.getConfigValue(key, "hidden") or False
			if hidden:
				self.subMenuSort.removeConfigValue(key, "hidden")
				self["key_yellow"].setText(_("Hide"))
			else:
				self.subMenuSort.changeConfigValue(key, "hidden", True)
				self["key_yellow"].setText(_("Show"))

	def keyGreen(self):
		if self.sortMode:
			self.keyOk()

	def keyCancel(self):
		if self.sortMode:
			self.toggleSortMode()
		else:
			self.closeNonRecursive()

	def keyNumberGlobal(self, number):
		self.number = self.number * 10 + number
		count = self["menu"].count()
		if self.number and self.number <= count:
			self["menu"].setIndex(self.number - 1)
			if count < 10 or self.number >= 10:
				self.okbuttonClick()
			else:
				self.nextNumberTimer.start(1500, True)
		else:
			self.resetNumberKey()

	def resetNumberKey(self):
		self.nextNumberTimer.stop()
		self.number = 0

	def closeNonRecursive(self):
		self.resetNumberKey()
		self.close(False)

	def keyTop(self):
		self.currentIndex = self["menu"].getSelectedIndex()
		self["menu"].top()
		if self.sortMode and self.selectedEntry is not None:
			self.moveAction()

	def keyPageUp(self):
		self.currentIndex = self["menu"].getSelectedIndex()
		self["menu"].pageUp()
		if self.sortMode and self.selectedEntry is not None:
			self.moveAction()

	def keyUp(self):
		self.currentIndex = self["menu"].getSelectedIndex()
		self["menu"].up()
		if self.sortMode and self.selectedEntry is not None:
			self.moveAction()

	def keyDown(self):
		self.currentIndex = self["menu"].getSelectedIndex()
		self["menu"].down()
		if self.sortMode and self.selectedEntry is not None:
			self.moveAction()

	def keyPageDown(self):
		self.currentIndex = self["menu"].getSelectedIndex()
		self["menu"].pageDown()
		if self.sortMode and self.selectedEntry is not None:
			self.moveAction()

	def keyBottom(self):
		self.currentIndex = self["menu"].getSelectedIndex()
		self["menu"].bottom()
		if self.sortMode and self.selectedEntry is not None:
			self.moveAction()

	def keyText(self):
		avSwitch.setMode("HDMI", "720p", "50Hz")

	def moveAction(self):
		menuListCopy = list(self.menuList)
		entry = menuListCopy.pop(self.currentIndex)
		newPos = self["menu"].getSelectedIndex()
		menuListCopy.insert(newPos, entry)
		self.menuList = menuListCopy
		self.setMenuList(self.menuList)

	def resetSortOrder(self, key=None):
		config.usage.menu_sort_weight.value = {"mainmenu": {"submenu": {}}}
		config.usage.menu_sort_weight.save()
		self.closeRecursive()

	def toggleSortMode(self):
		if self.sortMode:
			self["key_green"].setText("")
			self["key_yellow"].setText("")
			self["key_blue"].setText(_("Edit Mode On"))
			self.sortMode = False
			for index, entry in enumerate(self.menuList):
				sort = (index + 1) * 10
				self.subMenuSort.changeConfigValue(entry[MENU_KEY], "sort", sort)
				if len(entry) >= MAX_MENU:
					data = list(entry)
					data[MENU_SORT] = sort
					data = tuple(data)
					self.menuList.pop(index)
					self.menuList.insert(index, data)
				if self.selectedEntry is not None:
					if entry[MENU_KEY] == self.selectedEntry:
						self.selectedEntry = None
			self.fullMenuList = list(self.menuList)
			config.usage.menu_sort_weight.changeConfigValue(self.menuID, "submenu", self.subMenuSort.value)
			config.usage.menu_sort_weight.save()
			self.hideShowEntries()
			self.setMenuList(self.menuList)
		else:
			self["key_green"].setText(_("Move Mode On"))
			self["key_blue"].setText(_("Edit Mode Off"))
			self.sortMode = True
			self.hideShowEntries()
			self.setMenuList(self.menuList)

	def hideShowEntries(self):
		menuList = list(self.fullMenuList)
		if not self.sortMode:
			removeList = []
			for entry in menuList:
				if self.subMenuSort.getConfigValue(entry[MENU_KEY], "hidden"):
					removeList.append(entry)
			for entry in removeList:
				if entry in menuList:
					menuList.remove(entry)
		if not len(menuList):
			menuList.append(("", None, "dummy", 10, "", None, 10))
		menuList.sort(key=lambda x: int(x[MENU_SORT]))
		self.menuList = list(menuList)

	def gotoStandby(self, *res):
		from Screens.Standby import Standby2
		self.session.open(Standby2)
		self.close(True)


class AnimMain(Screen):
	def __init__(self, session, tlist, menuTitle):
		Screen.__init__(self, session)
		self.tlist = tlist
		self.setTitle(menuTitle)
		self.skinName = "Animmain"
		ipage = 1
		list = []
		nopic = len(tlist)
		self.pos = []
		self.index = 0
		list = []
		tlist = []
		self["label1"] = StaticText()
		self["label2"] = StaticText()
		self["label3"] = StaticText()
		self["label4"] = StaticText()
		self["label5"] = StaticText()
		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Select"))
		self["actions"] = HelpableNumberActionMap(self, ["OkCancelActions", "MenuActions", "DirectionActions", "NumberActions", "ColorActions"], {
			"ok": self.okbuttonClick,
			"cancel": self.closeNonRecursive,
			"left": self.key_left,
			"right": self.key_right,
			"up": self.key_up,
			"down": self.key_down,
			"red": self.cancel,
			"green": self.okbuttonClick,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal
		}, prio=0)
		nop = len(self.tlist)
		self.nop = nop
		nh = 1
		if nop == 1:
			nh = 1
		elif nop == 2:
			nh = 2
		elif nop == 3:
			nh = 2
		elif nop == 4:
			nh = 3
		elif nop == 5:
			nh = 3
		else:
			nh = int(float(nop) / 2)
		self.index = nh
		i = 0
		self.onShown.append(self.openTest)

	def key_menu(self):
		pass

	def cancel(self):
		self.close()

	def openTest(self):
		i = self.index
		if i - 3 > -1:
			name1 = menuEntryName(self.tlist[i - 3][0])
		else:
			name1 = " "
		if i - 2 > -1:
			name2 = menuEntryName(self.tlist[i - 2][0])
		else:
			name2 = " "
		name3 = menuEntryName(self.tlist[i - 1][0])
		if i < self.nop:
			name4 = menuEntryName(self.tlist[i][0])
		else:
			name4 = " "
		if i + 1 < self.nop:
			name5 = menuEntryName(self.tlist[i + 1][0])
		else:
			name5 = " "
		self["label1"].setText(name1)
		self["label2"].setText(name2)
		self["label3"].setText(name3)
		self["label4"].setText(name4)
		self["label5"].setText(name5)

	def key_left(self):
		self.index -= 1
		if self.index < 1:
			self.index = self.nop
		self.openTest()

	def key_right(self):
		self.index += 1
		if self.index > self.nop:
			self.index = 1
		self.openTest()

	def key_up(self):
		self.index = 1 if self.index > 1 else self.nop
		self.openTest()

	def key_down(self):
		self.index = self.nop if self.index < self.nop else 1
		self.openTest()

	def keyNumberGlobal(self, number):
		if number <= self.nop:
			self.index = number
			self.openTest()
			self.okbuttonClick()

	def closeNonRecursive(self):
		self.close(False)

	def closeRecursive(self):
		self.close(True)

	def createSummary(self):
		pass

	def okbuttonClick(self):
		idx = self.index - 1
		selection = self.tlist[idx]
		if selection is not None:
			selection[1]()


class IconMain(Screen):
	def __init__(self, session, tlist, menuTitle):
		Screen.__init__(self, session)
		self.tlist = tlist
		self.setTitle(menuTitle)
		self.skinName = "Iconmain"
		ipage = 1
		list = []
		nopic = len(self.tlist)
		self.pos = []
		self.ipage = 1
		self.index = 0
		self.icons = []
		self.indx = []
		n1 = len(tlist)
		self.picnum = n1
		list = []
		tlist = []
		self["label1"] = StaticText()
		self["label2"] = StaticText()
		self["label3"] = StaticText()
		self["label4"] = StaticText()
		self["label5"] = StaticText()
		self["label6"] = StaticText()
		self["label1s"] = StaticText()
		self["label2s"] = StaticText()
		self["label3s"] = StaticText()
		self["label4s"] = StaticText()
		self["label5s"] = StaticText()
		self["label6s"] = StaticText()
		self["pointer"] = Pixmap()
		self["pixmap1"] = Pixmap()
		self["pixmap2"] = Pixmap()
		self["pixmap3"] = Pixmap()
		self["pixmap4"] = Pixmap()
		self["pixmap5"] = Pixmap()
		self["pixmap6"] = Pixmap()
		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Select"))
		self["key_yellow"] = StaticText(_("Config"))
		self["actions"] = HelpableNumberActionMap(self, ["OkCancelActions", "MenuActions", "DirectionActions", "NumberActions", "ColorActions"], {
			"ok": self.okbuttonClick,
			"cancel": self.closeNonRecursive,
			"left": self.key_left,
			"right": self.key_right,
			"up": self.key_up,
			"down": self.key_down,
			"red": self.cancel,
			"green": self.okbuttonClick,
			"yellow": self.key_menu,
			"menu": self.closeRecursive,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal
		}, prio=0)
		self.index = 0
		i = 0
		self.maxentry = 29
		self.istart = 0
		i = 0
		self.onShown.append(self.openTest)

	def key_menu(self):
		pass

	def cancel(self):
		self.close()

	def paintFrame(self):
		pass

	def openTest(self):
		if self.ipage == 1:
			ii = 0
		elif self.ipage == 2:
			ii = 6
		elif self.ipage == 3:
			ii = 12
		elif self.ipage == 4:
			ii = 18
		elif self.ipage == 5:
			ii = 24
		dxml = config.skin.primary_skin.value
		dskin = dxml.split("/")
		j = 0
		i = ii
		while j < 6:
			j = j + 1
			if i > self.picnum - 1:
				icon = f"{dskin[0]}/blank.png"
				name = ""
			else:
				name = self.tlist[i][0]
			name = menuEntryName(name)
			if j == self.index + 1:
				self[f"label{j}"].setText(" ")
				self[f"label{j}s"].setText(name)
			else:
				self[f"label{j}"].setText(name)
				self[f"label{j}s"].setText(" ")
			i = i + 1
		j = 0
		i = ii
		while j < 6:
			j = j + 1
			itot = (self.ipage - 1) * 6 + j
			if itot > self.picnum:
				icon = f"/usr/share/enigma2/{dskin[0]}/blank.png"
			else:
				icon = f"/usr/share/enigma2/{dskin[0]}/buttons/icon1.png"
			pic = icon
			self[f"pixmap{j}"].instance.setPixmapFromFile(pic)
			i = i + 1
		if self.picnum > 6:
			try:
				dpointer = f"/usr/share/enigma2/{dskin[0]}/pointer.png"
				self["pointer"].instance.setPixmapFromFile(dpointer)
			except:
				dpointer = "/usr/share/enigma2/skin_default/pointer.png"
				self["pointer"].instance.setPixmapFromFile(dpointer)
		else:
			try:
				dpointer = f"/usr/share/enigma2/{dskin[0]}/blank.png"
				self["pointer"].instance.setPixmapFromFile(dpointer)
			except:
				dpointer = "/usr/share/enigma2/skin_default/blank.png"
				self["pointer"].instance.setPixmapFromFile(dpointer)

	def key_left(self):
		self.index -= 1
		if self.index < 0:
			self.key_up(True)
		else:
			self.openTest()

	def key_right(self):
		self.index += 1
		inum = self.picnum - 1 - (self.ipage - 1) * 6
		if self.index > inum or self.index > 5:
			self.key_down()
		else:
			self.openTest()

	def key_up(self, focusLastPic=False):
		self.ipage = self.ipage - 1
		if self.ipage < 1 and 7 > self.picnum > 0:
			self.ipage = 1
			focusLastPic = focusLastPic or self.index == 0
		elif self.ipage < 1 and 13 > self.picnum > 6:
			self.ipage = 2
		elif self.ipage < 1 and 19 > self.picnum > 12:
			self.ipage = 3
		elif self.ipage < 1 and 25 > self.picnum > 18:
			self.ipage = 4
		elif self.ipage < 1 and 31 > self.picnum > 24:
			self.ipage = 5
		if focusLastPic:
			inum = self.picnum - 1 - (self.ipage - 1) * 6
			self.index = inum if inum < 5 else 5
		else:
			self.index = 0
		self.openTest()

	def key_down(self, focusLastPic=False):
		self.ipage = self.ipage + 1
		if self.ipage == 2 and 7 > self.picnum > 0:
			self.ipage = 1
			focusLastPic = focusLastPic or self.index < self.picnum - 1 - (self.ipage - 1) * 6
		elif self.ipage == 3 and 13 > self.picnum > 6:
			self.ipage = 1
		elif self.ipage == 4 and 19 > self.picnum > 12:
			self.ipage = 1
		elif self.ipage == 5 and 25 > self.picnum > 18:
			self.ipage = 1
		elif self.ipage == 6 and 31 > self.picnum > 24:
			self.ipage = 1
		if focusLastPic:
			inum = self.picnum - 1 - (self.ipage - 1) * 6
			self.index = inum if inum < 5 else 5
		else:
			self.index = 0
		self.openTest()

	def keyNumberGlobal(self, number):
		if number == 7:
			self.key_up()
		elif number == 8:
			self.closeNonRecursive()
		elif number == 9:
			self.key_down()
		else:
			number -= 1
			if number <= self.picnum - 1 - (self.ipage - 1) * 6:
				self.index = number
				self.openTest()
				self.okbuttonClick()

	def closeNonRecursive(self):
		self.close(False)

	def closeRecursive(self):
		self.close(True)

	def createSummary(self):
		pass

	def okbuttonClick(self):
		if self.ipage == 1:
			idx = self.index
		elif self.ipage == 2:
			idx = self.index + 6
		elif self.ipage == 3:
			idx = self.index + 12
		elif self.ipage == 4:
			idx = self.index + 18
		elif self.ipage == 5:
			idx = self.index + 24
		if idx > self.picnum - 1:
			return
		if idx is None:
			return
		selection = self.tlist[idx]
		if selection is not None:
			selection[1]()


class MenuSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self["entry"] = StaticText("")
		if self.addWatcher not in self.onShow:
			self.onShow.append(self.addWatcher)
		if self.removeWatcher not in self.onHide:
			self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if self.selectionChanged not in self.parent["menu"].onSelectionChanged:
			self.parent["menu"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def removeWatcher(self):
		if self.selectionChanged in self.parent["menu"].onSelectionChanged:
			self.parent["menu"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self["entry"].setText(self.parent["menu"].getCurrent()[WIDGET_NUMBER_TEXT])
