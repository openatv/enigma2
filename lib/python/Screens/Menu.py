from os.path import exists
from six import PY2
from xml.etree.cElementTree import parse

from enigma import eTimer
from skin import findSkinScreen, menus
from Components.ActionMap import HelpableNumberActionMap, ActionMap, HelpableActionMap
from Components.Button import Button
from Components.config import ConfigDictionarySet, NoSave, config, configfile
from Components.Pixmap import Pixmap
from Components.PluginComponent import plugins
from Components.SystemInfo import BoxInfo
from Components.Label import Label
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.HelpMenu import HelpableScreen
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.Screen import Screen, ScreenSummary
from Screens.Setup import Setup, getSetupTitle, getSetupTitleLevel
from Tools.BoundFunction import boundFunction
from Tools.Directories import SCOPE_GUISKIN, SCOPE_SKINS, resolveFilename
from Tools.LoadPixmap import LoadPixmap

MODULE_NAME = __name__.split(".")[-1]


# Read the menu
file = open(resolveFilename(SCOPE_SKINS, "menu.xml"), "r")
mdom = parse(file)
file.close()

mainmenu = _("Main Menu")
lastMenuID = None

nomainmenupath = False if exists(resolveFilename(SCOPE_GUISKIN, "mainmenu")) else True

def MenuEntryPixmap(entryID, png_cache, lastMenuID):
	if nomainmenupath:
		return None
	png = png_cache.get(entryID, None)
	if png is None:
		pngPath = resolveFilename(SCOPE_GUISKIN, "mainmenu/" + entryID + ".png")
		pos = config.skin.primary_skin.value.rfind("/")
		if pos > -1:
			current_skin = config.skin.primary_skin.value[:pos + 1]
		else:
			current_skin = ""
		if current_skin in pngPath and current_skin or not current_skin:
			png = LoadPixmap(pngPath, cached=True)
		if png is None:
			if lastMenuID is not None:
				png = png_cache.get(lastMenuID, None)
			png_cache[entryID] = png
	if png is None:
		png = png_cache.get("missing", None)
		if png is None:
			png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "mainmenu/missing.png"), cached=True)
			png_cache["missing"] = png
	return png


def MenuEntryName(name):
	def splitUpperCase(name, maxlen):
		for c in range(len(name), 0, -1):
			if name[c - 1].isupper() and c - 1 and c - 1 <= maxlen:
				return name[:c - 1] + "-:-" + name[c - 1:]
		return name

	def splitLowerCase(name, maxlen):
		for c in range(len(name), 0, -1):
			if name[c - 1].islower() and c - 1 and c - 1 <= maxlen:
				return name[:c - 1] + "-:-" + name[c - 1:]
		return name

	def splitName(name, maxlen):
		for s in (" ", "-", "/"):
			pos = name.rfind(s, 0, maxlen + 1)
			if pos > 1:
				return [name[:pos + 1] if pos + 1 <= maxlen and s != " " else name[:pos], name[pos + 1:]]
		return splitUpperCase(name, maxlen).split("-:-", 1)

	maxrow = 3
	maxlen = 18
	namesplit = []
	if len(name) > maxlen and maxrow > 1:
		namesplit = splitName(name, maxlen)
		if len(namesplit) == 1 or (len(namesplit) == 2 and len(namesplit[1]) > maxlen * (maxrow - 1)):
			tmp = splitLowerCase(name, maxlen).split("-:-", 1)
			if len(tmp[0]) > len(namesplit[0]) or len(namesplit) < 2:
				namesplit = tmp
		for x in range(1, maxrow):
			if len(namesplit) > x and len(namesplit) < maxrow and len(namesplit[x]) > maxlen:
				tmp = splitName(namesplit[x], maxlen)
				if len(tmp) == 1 or (len(tmp) == 2 and len(tmp[1]) > maxlen * (maxrow - x)):
					tmp = splitLowerCase(namesplit[x], maxlen).split("-:-", 1)
				if len(tmp) == 2:
					namesplit.pop(x)
					namesplit.extend(tmp)
			else:
				break
	return name if len(namesplit) < 2 else "\n".join(namesplit)


class title_History:
	def __init__(self):
		self.thistory = ""

	def reset(self):
		self.thistory = ""

	def reducehistory(self):
		history_len = len(self.thistory.split(">"))
		if history_len < 3:
			self.reset()
			return
		if self.thistory == "":
			return
		result = self.thistory.rsplit(">", 2)
		if result[0] == "":
			self.reset()
			return
		self.thistory = result[0] + "> "


t_history = title_History()

class Menu(Screen, HelpableScreen, ProtectedScreen):
	ALLOW_SUSPEND = True
	png_cache = {}

	def __init__(self, session, parent):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.parentMenu = parent
		self.menuList = []
		self["menu"] = List(self.menuList)
		self["menu"].enableWrapAround = True
		self["menu"].onSelectionChanged.append(self.selectionChanged)
		self.showNumericHelp = False
		self["green"] = Label()
		self["yellow"] = Label()
		self["blue"] = Label()
		self.sort_mode = False
		self.selected_entry = None
		self.sub_menu_sort = None
		self.createMenuList()
		ProtectedScreen.__init__(self)
		# for the skin: first try a menu_<menuID>, then Menu
		self.skinName = []
		if self.menuID is not None:
			if config.usage.menutype.value == "horzanim" and findSkinScreen("Animmain"):
				self.skinName.append("Animmain")
			elif config.usage.menutype.value == "horzicon" and findSkinScreen("Iconmain"):
				self.skinName.append("Iconmain")
			else:
				self.skinName.append("menu_" + self.menuID)
		self.skinName.append("Menu")
		
		if config.usage.menu_sort_mode.value == "user":
			
			self["MoveActions"] = ActionMap(["WizardActions"],
				{
					"left": self.keyLeft,
					"right": self.keyRight,
					"up": self.keyUp,
					"down": self.keyDown,
				}, -1
			)
			self["EditActions"] = ActionMap(["ColorActions"],
			{
				"green": self.keyGreen,
				"yellow": self.keyYellow,
				"blue": self.keyBlue,
			})
		
		
		self["menuActions"] = HelpableNumberActionMap(self, ["OkCancelActions", "NumberActions", "MenuActions"], {
			"ok": (self.okbuttonClick, _("Select the current menu item")),
			"cancel": (self.closeNonRecursive, _("Exit menu")),
			"close": (self.closeRecursive, _("Exit all menus")),
			"menu": (self.closeRecursive, _("Exit all menus")),
			"1": (self.keyNumberGlobal, _("Direct menu item selection")),
			"2": (self.keyNumberGlobal, _("Direct menu item selection")),
			"3": (self.keyNumberGlobal, _("Direct menu item selection")),
			"4": (self.keyNumberGlobal, _("Direct menu item selection")),
			"5": (self.keyNumberGlobal, _("Direct menu item selection")),
			"6": (self.keyNumberGlobal, _("Direct menu item selection")),
			"7": (self.keyNumberGlobal, _("Direct menu item selection")),
			"8": (self.keyNumberGlobal, _("Direct menu item selection")),
			"9": (self.keyNumberGlobal, _("Direct menu item selection")),
			"0": (self.keyNumberGlobal, _("Direct menu item selection"))

		}, prio=0, description=_("Common Menu Actions"))
		title = parent.get("title", "").encode("UTF-8") if PY2 else parent.get("title", "") or None
		title = title and _(title)
		if title is None:
			title = _(parent.get("text", "").encode("UTF-8", "ignore")) if PY2 else _(parent.get("text", ""))
		else:
			t_history.reset()
		self["title"] = StaticText(title)
		self.setTitle(title)
		self.menu_title = title
		self["thistory"] = StaticText(t_history.thistory)
		history_len = len(t_history.thistory)
		self["title0"] = StaticText("")
		self["title1"] = StaticText("")
		self["title2"] = StaticText("")
		if history_len < 13:
			self["title0"] = StaticText(title)
		elif history_len < 21:
			self["title0"] = StaticText("")
			self["title1"] = StaticText(title)
		else:
			self["title0"] = StaticText("")
			self["title1"] = StaticText("")
			self["title2"] = StaticText(title)
		if t_history.thistory == "":
			t_history.thistory = str(title) + " > "
		else:
			t_history.thistory = t_history.thistory + str(title) + " > "
		if config.usage.menutype.value == "horzanim" and findSkinScreen("Animmain"):
			self["label1"] = StaticText()
			self["label2"] = StaticText()
			self["label3"] = StaticText()
			self["label4"] = StaticText()
			self["label5"] = StaticText()
			self.onShown.append(self.openTestA)
		elif config.usage.menutype.value == "horzicon" and findSkinScreen("Iconmain"):
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
			self.onShown.append(self.openTestB)
		self.number = 0
		self.nextNumberTimer = eTimer()
		self.nextNumberTimer.callback.append(self.okbuttonClick)
		if len(self.menuList) == 1:
			self.onExecBegin.append(self.__onExecBegin)
		self.onLayoutFinish.append(self.layoutFinished)

	def createMenuList(self, showNumericHelp=False):
		self.menuList = []
		self.menuID = None
		for x in self.parentMenu:  # walk through the actual nodelist
			if not x.tag:
				continue
			if x.tag == "item":
				itemLevel = int(x.get("level", 0))
				if itemLevel <= config.usage.setup_level.index:
					self.addItem(self.menuList, x)
					count += 1
			elif x.tag == "menu":
				itemLevel = int(x.get("level", 0))
				if itemLevel <= config.usage.setup_level.index:
					self.addMenu(self.menuList, x)
					count += 1
			elif x.tag == "id":
				self.menuID = x.get("val")
				count = 0

			if self.menuID:
				# menuupdater?
				if menuUpdater.updatedMenuAvailable(self.menuID):
					for x in menuUpdater.getUpdatedMenu(self.menuID):
						if x[1] == count:
							description = _(x.get("description", "").encode("UTF-8", "ignore")) if PY2 else _(x.get("description", ""))
							menupng = MenuEntryPixmap(self.menuID, self.png_cache, lastMenuID)
							self.menuList.append((x[0], boundFunction(self.runScreen, (x[2], x[3] + ", ")), x[4], description, menupng))
							count += 1


		if self.menuID:
			# plugins
			for l in plugins.getPluginsForMenu(self.menuID):
				# check if a plugin overrides an existing menu
				plugin_menuid = l[2]
				for x in self.menuList:
					if x[2] == plugin_menuid:
						self.menuList.remove(x)
						break
				description = plugins.getDescriptionForMenuEntryID(self.menuID, plugin_menuid)
				menupng = MenuEntryPixmap(l[2], self.png_cache, lastMenuID)
				if len(l) > 4 and l[4]:
					self.menuList.append((l[0], boundFunction(l[1], self.session, self.close), l[2], l[3] or 50, description, menupng))
				else:
					self.menuList.append((l[0], boundFunction(l[1], self.session), l[2], l[3] or 50, description, menupng))


		if config.usage.menu_sort_mode.value == "user" and self.menuID == "mainmenu":
			plugin_list = []
			id_list = []
			for l in plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_EVENTINFO]):
				l.id = (l.name.lower()).replace(" ", "_")
				if l.id not in id_list:
					id_list.append(l.id)
					plugin_list.append((l.name, boundFunction(l.__call__, self.session), l.id, 200))

		if self.menuID is not None and config.usage.menu_sort_mode.value == "user":
			self.sub_menu_sort = NoSave(ConfigDictionarySet())
			self.sub_menu_sort.value = config.usage.menu_sort_weight.getConfigValue(self.menuID, "submenu") or {}
			idx = 0
			for x in self.menuList:
				entry = list(self.menuList.pop(idx))
				m_weight = self.sub_menu_sort.getConfigValue(entry[2], "sort") or entry[3]
				entry.append(m_weight)
				self.menuList.insert(idx, tuple(entry))
				self.sub_menu_sort.changeConfigValue(entry[2], "sort", m_weight)
				idx += 1
			self.full_list = list(self.menuList)

		if config.usage.menu_sort_mode.value == "a_z":
			# Sort by Name
			self.menuList.sort(key=self.sortByName)
		elif config.usage.menu_sort_mode.value == "user":
			self["blue"].setText(_("Edit Mode On"))
			self.hide_show_entries()
		else:
			# Sort by Weight
			self.menuList.sort(key=lambda x: int(x[3]))

		if config.usage.menu_show_numbers.value:
			self.menuList = [(str(x[0] + 1) + " " + x[1][0], x[1][1], x[1][2]) for x in enumerate(self.menuList)]

		self["menu"].setList(self.menuList)

	def layoutFinished(self):
		self.selectionChanged()

	def selectionChanged(self):
		if self.sort_mode:
			selection = self["menu"].getCurrent()[2]
			if self.sub_menu_sort.getConfigValue(selection, "hidden"):
				self["yellow"].setText(_("Show"))
			else:
				self["yellow"].setText(_("Hide"))
		else:
			self["yellow"].setText("")

	def okbuttonClick(self):
		global lastMenuID
		# print "okbuttonClick"
		self.resetNumberKey()
		selection = self["menu"].getCurrent()
		if selection is not None and selection[1] is not None:
			lastMenuID = selection[2]
			selection[1]()

	def execText(self, text):
		exec(text)

	def runScreen(self, arg):
		# arg[0] is the module (as string)
		# arg[1] is Screen inside this module
		#	plus possible arguments, as
		#	string (as we want to reference
		#	stuff which is just imported)
		if arg[0] != "":
			exec("from %s import %s" % (arg[0], arg[1].split(",")[0]))
			self.openDialog(*eval(arg[1]))

	def nothing(self):  # dummy
		pass

	def gotoStandby(self, *res):
		from Screens.Standby import Standby2
		self.session.open(Standby2)
		self.close(True)

	def openDialog(self, *dialog):  # in every layer needed
		self.session.openWithCallback(self.menuClosed, *dialog)

	def openSetup(self, dialog):
		self.session.openWithCallback(self.menuClosed, Setup, dialog)

	def addMenu(self, destList, node):
		requires = node.get("requires")
		if requires:
			if requires[0] == "!":
				if BoxInfo.getItem(requires[1:], False):
					return
			elif not BoxInfo.getItem(requires, False):
				return

		MenuTitle = _(node.get("text", "??").encode("UTF-8", "ignore")) if PY2 else _(node.get("text", "??"))
		entryID = node.get("entryID", "undefined")
		weight = node.get("weight", 50)
		description = _(node.get("description", "").encode("UTF-8", "ignore")) if PY2 else _(node.get("description", ""))
		menupng = MenuEntryPixmap(entryID, self.png_cache, lastMenuID)
		x = node.get("flushConfigOnClose")
		if x:
			a = boundFunction(self.session.openWithCallback, self.menuClosedWithConfigFlush, Menu, node)
		else:
			a = boundFunction(self.session.openWithCallback, self.menuClosed, Menu, node)
		# TODO add check if !empty(node.childNodes)
		destList.append((MenuTitle, a, entryID, weight, description, menupng))

	def menuClosedWithConfigFlush(self, *res):
		configfile.save()
		self.menuClosed(*res)

	def menuClosed(self, *res):
		global lastMenuID
		if res and res[0]:
			lastMenuID = None
			self.close(True)

	def addItem(self, destList, node):
		requires = node.get("requires")
		if requires:
			if requires[0] == "!":
				if BoxInfo.getItem(requires[1:], False):
					return
			elif not BoxInfo.getItem(requires, False):
				return
		conditional = node.get("conditional")
		if conditional and not eval(conditional):
			return
		item_text = node.get("text", "").encode("UTF-8", "ignore") if PY2 else node.get("text", "")
		entryID = node.get("entryID", "undefined")
		weight = node.get("weight", 50)
		description = _(node.get("description", "").encode("UTF-8", "ignore")) if PY2 else _(node.get("description", ""))
		menupng = MenuEntryPixmap(entryID, self.png_cache, lastMenuID)
		for x in node:
			if x.tag == "screen":
				module = x.get("module")
				screen = x.get("screen")

				if screen is None:
					screen = module

				# print(module, screen)
				if module:
					module = "Screens." + module
				else:
					module = ""

				# check for arguments. they will be appended to the
				# openDialog call
				args = x.text or ""
				screen += ", " + args

				destList.append((_(item_text or "??"), boundFunction(self.runScreen, (module, screen)), entryID, weight, description, menupng))
				return
			elif x.tag == 'plugin':
				extensions = x.get("extensions")
				system = x.get("system")
				screen = x.get("screen")

				if extensions:
					module = extensions
				elif system:
					module = system

				if screen is None:
					screen = module

				if extensions:
					module = "Plugins.Extensions." + extensions + '.plugin'
				elif system:
					module = "Plugins.SystemPlugins." + system + '.plugin'
				else:
					module = ""

				# check for arguments. they will be appended to the
				# openDialog call
				args = x.text or ""
				screen += ", " + args

				destList.append((_(item_text or "??"), boundFunction(self.runScreen, (module, screen)), entryID, weight, description, menupng))
				return
			elif x.tag == "code":
				destList.append((_(item_text or "??"), boundFunction(self.execText, x.text), entryID, weight, description, menupng))
				return
			elif x.tag == "setup":
				id = x.get("id")
				if item_text == "":
					if getSetupTitleLevel(id) > config.usage.setup_level.index:
						return
					item_text = _(getSetupTitle(id))
				else:
					item_text = _(item_text)
				destList.append((item_text, boundFunction(self.openSetup, id), entryID, weight, description, menupng))
				return
		destList.append((item_text, self.nothing, entryID, weight, description, menupng))

	def sortByName(self, listentry):
		return listentry[0].lower()

	def openTestA(self):
		self.session.open(AnimMain, self.menuList, self.menu_title)
		self.close()

	def openTestB(self):
		self.session.open(IconMain, self.menuList, self.menu_title)
		self.close()

	def __onExecBegin(self):
		self.onExecBegin.remove(self.__onExecBegin)
		if config.usage.menutype.value == "horzanim" and findSkinScreen("Animmain"):
			return
		elif config.usage.menutype.value == "horzicon" and findSkinScreen("Iconmain"):
			return
		else:
			self.okbuttonClick()

	def keyNumberGlobal(self, number):
		self.number = self.number * 10 + number
		if self.number and self.number <= len(self["menu"].list):
			self["menu"].setIndex(self.number - 1)
			if len(self["menu"].list) < 10 or self.number >= 10:
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
		t_history.reducehistory()
		self.close(False)

	def closeRecursive(self):
		self.resetNumberKey()
		t_history.reset()
		self.close(True)

	def createSummary(self):
		if config.usage.menutype.value == "standard":
			return MenuSummary

	def isProtected(self):
		if config.ParentalControl.setuppinactive.value:
			if config.ParentalControl.config_sections.main_menu.value and not(hasattr(self.session, "infobar") and self.session.infobar is None):
				return self.menuID == "mainmenu"
			elif config.ParentalControl.config_sections.configuration.value and self.menuID == "setup":
				return True
			elif config.ParentalControl.config_sections.timer_menu.value and self.menuID == "timermenu":
				return True
			elif config.ParentalControl.config_sections.standby_menu.value and self.menuID == "shutdown":
				return True

	def keyBlue(self):
		if config.usage.menu_sort_mode.value == "user":
			self.toggleSortMode()

	def updateList(self):
		self.sub_menu_sort = NoSave(ConfigDictionarySet())
		self.sub_menu_sort.value = config.usage.menu_sort_weight.getConfigValue(self.menuID, "submenu") or None
		idx = 0
		for x in self.menuList:
			entry = list(self.menuList.pop(idx))
			m_weight = self.sub_menu_sort.getConfigValue(entry[2], "sort") or entry[3]
			entry.append(m_weight)
			self.menuList.insert(idx, tuple(entry))
			self.sub_menu_sort.changeConfigValue(entry[2], "sort", m_weight)
			if not self.sort_mode and self.sub_menu_sort.getConfigValue(entry[2], "hidden"):
				self.menuList.remove(x)
			idx += 1

	def keyLeft(self):
		self.cur_idx = self["menu"].getSelectedIndex()
		self["menu"].pageUp()
		if self.sort_mode and self.selected_entry is not None:
			self.moveAction()

	def keyRight(self):
		self.cur_idx = self["menu"].getSelectedIndex()
		self["menu"].pageDown()
		if self.sort_mode and self.selected_entry is not None:
			self.moveAction()

	def keyDown(self):
		self.cur_idx = self["menu"].getSelectedIndex()
		self["menu"].down()
		if self.sort_mode and self.selected_entry is not None:
			self.moveAction()

	def keyUp(self):
		self.cur_idx = self["menu"].getSelectedIndex()
		self["menu"].up()
		if self.sort_mode and self.selected_entry is not None:
			self.moveAction()

	def keyOk(self):
		if self.sort_mode and len(self.menuList):
			m_entry = selection = self["menu"].getCurrent()
			select = False
			if self.selected_entry is None:
				select = True
			elif self.selected_entry != m_entry[2]:
				select = True
			if not select:
				self["green"].setText(_("Move Mode On"))
				self.selected_entry = None
			else:
				self["green"].setText(_("Move Mode Off"))
			idx = 0
			for x in self.menuList:
				if m_entry[2] == x[2] and select == True:
					self.selected_entry = m_entry[2]
					break
				elif m_entry[2] == x[2] and select == False:
					self.selected_entry = None
					break
				idx += 1
		elif not self.sort_mode:
			self.okbuttonClick()

	def moveAction(self):
		tmp_list = list(self.menuList)
		entry = tmp_list.pop(self.cur_idx)
		newpos = self["menu"].getSelectedIndex()
		tmp_list.insert(newpos, entry)
		self.menuList = list(tmp_list)
		self["menu"].updateList(self.menuList)

	def keyYellow(self):
		if self.sort_mode:
			m_entry = selection = self["menu"].getCurrent()[2]
			hidden = self.sub_menu_sort.getConfigValue(m_entry, "hidden") or 0
			if hidden:
				self.sub_menu_sort.removeConfigValue(m_entry, "hidden")
				self["yellow"].setText(_("Hide"))
			else:
				self.sub_menu_sort.changeConfigValue(m_entry, "hidden", 1)
				self["yellow"].setText(_("Show"))

	def keyGreen(self):
		if self.sort_mode:
			self.keyOk()

	def keyCancel(self):
		if self.sort_mode:
			self.toggleSortMode()
		else:
			self.closeNonRecursive()

	def resetSortOrder(self, key=None):
		config.usage.menu_sort_weight.value = {"mainmenu": {"submenu": {}}}
		config.usage.menu_sort_weight.save()
		self.closeRecursive()

	def toggleSortMode(self):
		if self.sort_mode:
			self["green"].setText("")
			self["yellow"].setText("")
			self["blue"].setText(_("Edit Mode On"))
			self.sort_mode = False
			i = 10
			idx = 0
			for x in self.menuList:
				self.sub_menu_sort.changeConfigValue(x[2], "sort", i)
				if len(x) >= 7:
					entry = list(x)
					entry[6] = i
					entry = tuple(entry)
					self.menuList.pop(idx)
					self.menuList.insert(idx, entry)
				if self.selected_entry is not None:
					if x[2] == self.selected_entry:
						self.selected_entry = None
				i += 10
				idx += 1
			self.full_list = list(self.menuList)
			config.usage.menu_sort_weight.changeConfigValue(self.menuID, "submenu", self.sub_menu_sort.value)
			config.usage.menu_sort_weight.save()
			self.hide_show_entries()
			self["menu"].setList(self.menuList)
		else:
			self["green"].setText(_("Move Mode On"))
			self["blue"].setText(_("Edit Mode Off"))
			self.sort_mode = True
			self.hide_show_entries()
			self["menu"].updateList(self.menuList)
			self.selectionChanged()

	def hide_show_entries(self):
		m_list = list(self.full_list)
		if not self.sort_mode:
			rm_list = []
			for entry in m_list:
				if self.sub_menu_sort.getConfigValue(entry[2], "hidden"):
					rm_list.append(entry)
			for entry in rm_list:
				if entry in m_list:
					m_list.remove(entry)
		if not len(m_list):
			m_list.append(('', None, 'dummy', '10', '', None, 10))
		m_list.sort(key=lambda listweight: int(listweight[6]))
		self.menuList = list(m_list)

class MenuUpdater:
	def __init__(self):
		self.updatedMenuItems = {}

	def addMenuItem(self, id, pos, text, module, screen, weight, description):
		if not self.updatedMenuAvailable(id):
			self.updatedMenuItems[id] = []
		self.updatedMenuItems[id].append([text, pos, module, screen, weight, description])

	def delMenuItem(self, id, pos, text, module, screen, weight, description):
		self.updatedMenuItems[id].remove([text, pos, module, screen, weight, description])

	def updatedMenuAvailable(self, id):
		return id in self.updatedMenuItems

	def getUpdatedMenu(self, id):
		return self.updatedMenuItems[id]




class AnimMain(Screen):
	def __init__(self, session, tlist, menuTitle):
		Screen.__init__(self, session)
		self.skinName = "Animmain"
		self.tlist = tlist
		ipage = 1
		list = []
		nopic = len(tlist)
		self.pos = []
		self.index = 0
		title = menuTitle
		self["title"] = Button(title)
		list = []
		tlist = []
		self["label1"] = StaticText()
		self["label2"] = StaticText()
		self["label3"] = StaticText()
		self["label4"] = StaticText()
		self["label5"] = StaticText()
		self["red"] = StaticText(_("Exit"))
		self["green"] = StaticText(_("Select"))
		self["yellow"] = StaticText(_("Config"))
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
		})
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

	def paintFrame(self):
		pass

	def openTest(self):
		i = self.index
		if i - 3 > -1:
			name1 = MenuEntryName(self.tlist[i - 3][0])
		else:
			name1 = " "
		if i - 2 > -1:
			name2 = MenuEntryName(self.tlist[i - 2][0])
		else:
			name2 = " "
		name3 = MenuEntryName(self.tlist[i - 1][0])
		if i < self.nop:
			name4 = MenuEntryName(self.tlist[i][0])
		else:
			name4 = " "
		if i + 1 < self.nop:
			name5 = MenuEntryName(self.tlist[i + 1][0])
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
		self.skinName = "Iconmain"
		self.tlist = tlist
		ipage = 1
		list = []
		nopic = len(self.tlist)
		self.pos = []
		self.ipage = 1
		self.index = 0
		title = menuTitle
		self["title"] = Button(title)
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
		self["red"] = StaticText(_("Exit"))
		self["green"] = StaticText(_("Select"))
		self["yellow"] = StaticText(_("Config"))
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
		})
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
				icon = dskin[0] + "/blank.png"
				name = ""
			else:
				name = self.tlist[i][0]
			name = MenuEntryName(name)
			if j == self.index + 1:
				self["label" + str(j)].setText(" ")
				self["label" + str(j) + "s"].setText(name)
			else:
				self["label" + str(j)].setText(name)
				self["label" + str(j) + "s"].setText(" ")
			i = i + 1
		j = 0
		i = ii
		while j < 6:
			j = j + 1
			itot = (self.ipage - 1) * 6 + j
			if itot > self.picnum:
				icon = '/usr/share/enigma2/' + dskin[0] + '/blank.png'
			else:
				icon = '/usr/share/enigma2/' + dskin[0] + '/buttons/icon1.png'
			pic = icon
			self["pixmap" + str(j)].instance.setPixmapFromFile(pic)
			i = i + 1
		if self.picnum > 6:
			try:
				dpointer = "/usr/share/enigma2/" + dskin[0] + "/pointer.png"
				self["pointer"].instance.setPixmapFromFile(dpointer)
			except:
				dpointer = "/usr/share/enigma2/skin_default/pointer.png"
				self["pointer"].instance.setPixmapFromFile(dpointer)
		else:
			try:
				dpointer = "/usr/share/enigma2/" + dskin[0] + "/blank.png"
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


class MainMenu(Menu):
	def __init__(self, *args):
		self.skinName = ["Menu"]
		Menu.__init__(self, *args)


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
		self["entry"].text = self.parent["menu"].getCurrent()[0]


menuUpdater = MenuUpdater()
