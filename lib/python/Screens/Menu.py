from Screens.Screen import Screen
from Screens.ParentalControlSetup import ProtectedScreen
from Components.Sources.List import List
from Components.ActionMap import NumberActionMap, ActionMap
from Components.Sources.StaticText import StaticText
from Components.config import configfile
from Components.PluginComponent import plugins
from Components.config import config, ConfigDictionarySet, NoSave
from Components.SystemInfo import SystemInfo
from Components.Label import Label
from Tools.BoundFunction import boundFunction
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, SCOPE_SKIN
from enigma import eTimer

import xml.etree.cElementTree

from Screens.Setup import Setup, getSetupTitle, getSetupTitleLevel

mainmenu = _("Main menu")

# read the menu
file = open(resolveFilename(SCOPE_SKIN, 'menu.xml'), 'r')
mdom = xml.etree.cElementTree.parse(file)
file.close()
class title_History:
	def __init__(self):
		self.thistory = ''
	def reset(self):
		self.thistory = ''
	def reducehistory(self):
		history_len = len(self.thistory.split('>'))
		if(history_len < 3):
			self.reset()
			return
		if(self.thistory == ''):
			return
		result = self.thistory.rsplit('>',2)
		if(result[0] == ''):
			self.reset()
			return
		self.thistory = result[0] + '> '

t_history = title_History()

class MenuUpdater:
	def __init__(self):
		self.updatedMenuItems = {}

	def addMenuItem(self, id, pos, text, module, screen, weight):
		if not self.updatedMenuAvailable(id):
			self.updatedMenuItems[id] = []
		self.updatedMenuItems[id].append([text, pos, module, screen, weight])

	def delMenuItem(self, id, pos, text, module, screen, weight):
		self.updatedMenuItems[id].remove([text, pos, module, screen, weight])

	def updatedMenuAvailable(self, id):
		return self.updatedMenuItems.has_key(id)

	def getUpdatedMenu(self, id):
		return self.updatedMenuItems[id]

menuupdater = MenuUpdater()

class MenuSummary(Screen):
	pass

class Menu(Screen, ProtectedScreen):
	ALLOW_SUSPEND = True

	def okbuttonClick(self):
		# print "okbuttonClick"
		self.resetNumberKey()
		selection = self["menu"].getCurrent()
		if selection is not None and selection[1] is not None:
			selection[1]()

	def execText(self, text):
		exec text

	def runScreen(self, arg):
		# arg[0] is the module (as string)
		# arg[1] is Screen inside this module
		#        plus possible arguments, as
		#        string (as we want to reference
		#        stuff which is just imported)
		# FIXME. somehow
		if arg[0] != "":
			exec "from " + arg[0] + " import *"

		self.openDialog(*eval(arg[1]))

	def nothing(self): #dummy
		pass

	def gotoStandby(self, *res):
		from Screens.Standby import Standby2
		self.session.open(Standby2)
		self.close(True)

	def openDialog(self, *dialog):				# in every layer needed
		self.session.openWithCallback(self.menuClosed, *dialog)

	def openSetup(self, dialog):
		self.session.openWithCallback(self.menuClosed, Setup, dialog)

	def addMenu(self, destList, node):
		requires = node.get("requires")
		if requires:
			if requires[0] == '!':
				if SystemInfo.get(requires[1:], False):
					return
			elif not SystemInfo.get(requires, False):
				return
		MenuTitle = _(node.get("text", "??").encode("UTF-8"))
		entryID = node.get("entryID", "undefined")
		weight = node.get("weight", 50)
		x = node.get("flushConfigOnClose")
		if x:
			a = boundFunction(self.session.openWithCallback, self.menuClosedWithConfigFlush, Menu, node)
		else:
			a = boundFunction(self.session.openWithCallback, self.menuClosed, Menu, node)
		#TODO add check if !empty(node.childNodes)
		destList.append((MenuTitle, a, entryID, weight))

	def menuClosedWithConfigFlush(self, *res):
		configfile.save()
		self.menuClosed(*res)

	def menuClosed(self, *res):
		if res and res[0]:
			self.close(True)

	def addItem(self, destList, node):
		requires = node.get("requires")
		if requires:
			if requires[0] == '!':
				if SystemInfo.get(requires[1:], False):
					return
			elif not SystemInfo.get(requires, False):
				return
		configCondition = node.get("configcondition")
		if configCondition and not eval(configCondition + ".value"):
			return
		item_text = node.get("text", "").encode("UTF-8")
		entryID = node.get("entryID", "undefined")
		weight = node.get("weight", 50)
		for x in node:
			if x.tag == 'screen':
				module = x.get("module")
				screen = x.get("screen")

				if screen is None:
					screen = module

				# print module, screen
				if module:
					module = "Screens." + module
				else:
					module = ""

				# check for arguments. they will be appended to the
				# openDialog call
				args = x.text or ""
				screen += ", " + args

				destList.append((_(item_text or "??"), boundFunction(self.runScreen, (module, screen)), entryID, weight))
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

				destList.append((_(item_text or "??"), boundFunction(self.runScreen, (module, screen)), entryID, weight))
				return
			elif x.tag == 'code':
				destList.append((_(item_text or "??"), boundFunction(self.execText, x.text), entryID, weight))
				return
			elif x.tag == 'setup':
				id = x.get("id")
				if item_text == "":
					if getSetupTitleLevel(id) > config.usage.setup_level.index:
						return
					item_text = _(getSetupTitle(id))
				else:
					item_text = _(item_text)
				destList.append((item_text, boundFunction(self.openSetup, id), entryID, weight))
				return
		destList.append((item_text, self.nothing, entryID, weight))

	def sortByName(self, listentry):
		return listentry[0].lower()

	def __init__(self, session, parent):
		Screen.__init__(self, session)

		self.sort_mode = False
		self.selected_entry = None
		self.sub_menu_sort = None

		self["green"] = Label()
		self["yellow"] = Label()
		self["blue"] = Label()

		m_list = []

		menuID = None
		for x in parent:						#walk through the actual nodelist
			if not x.tag:
				continue
			if x.tag == 'item':
				item_level = int(x.get("level", 0))
				if item_level <= config.usage.setup_level.index:
					self.addItem(m_list, x)
					count += 1
			elif x.tag == 'menu':
				item_level = int(x.get("level", 0))
				if item_level <= config.usage.setup_level.index:
					self.addMenu(m_list, x)
					count += 1
			elif x.tag == "id":
				menuID = x.get("val")
				count = 0

			if menuID is not None:
				# menuupdater?
				if menuupdater.updatedMenuAvailable(menuID):
					for x in menuupdater.getUpdatedMenu(menuID):
						if x[1] == count:
							m_list.append((x[0], boundFunction(self.runScreen, (x[2], x[3] + ", ")), x[4]))
							count += 1

		self.menuID = menuID
		if config.ParentalControl.configured.value:
			ProtectedScreen.__init__(self)

		if menuID is not None:
			# plugins
			for l in plugins.getPluginsForMenu(menuID):
				# check if a plugin overrides an existing menu
				plugin_menuid = l[2]
				for x in m_list:
					if x[2] == plugin_menuid:
						m_list.remove(x)
						break
				if len(l) > 4 and l[4]:
					m_list.append((l[0], boundFunction(l[1], self.session, self.close), l[2], l[3] or 50))
				else:
					m_list.append((l[0], boundFunction(l[1], self.session), l[2], l[3] or 50))

		# for the skin: first try a menu_<menuID>, then Menu
		self.skinName = [ ]
		if menuID is not None:
			self.skinName.append("menu_" + menuID)
		self.skinName.append("Menu")
		self.menuID = menuID
		ProtectedScreen.__init__(self)

		if config.usage.menu_sort_mode.value == "user" and menuID == "mainmenu":
			plugin_list = []
			id_list = []
			for l in plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU ,PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_EVENTINFO]):
				l.id = (l.name.lower()).replace(' ','_')
				if l.id not in id_list:
					id_list.append(l.id)
					plugin_list.append((l.name, boundFunction(l.__call__, session), l.id, 200))

		self.list = m_list

		if menuID is not None and config.usage.menu_sort_mode.value == "user":
			self.sub_menu_sort = NoSave(ConfigDictionarySet())
			self.sub_menu_sort.value = config.usage.menu_sort_weight.getConfigValue(self.menuID, "submenu") or {}
			idx = 0
			for x in self.list:
				entry = list(self.list.pop(idx))
				m_weight = self.sub_menu_sort.getConfigValue(entry[2], "sort") or entry[3]
				entry.append(m_weight)
				self.list.insert(idx, tuple(entry))
				self.sub_menu_sort.changeConfigValue(entry[2], "sort", m_weight)
				idx += 1
			self.full_list = list(m_list)

		if config.usage.menu_sort_mode.value == "a_z":
			# Sort by Name
			m_list.sort(key=self.sortByName)
		elif config.usage.menu_sort_mode.value == "user":
			self["blue"].setText(_("Edit mode on"))
			self.hide_show_entries()
			m_list = self.list
		else:
			# Sort by Weight
			m_list.sort(key=lambda x: int(x[3]))
		
		if config.usage.menu_show_numbers.value:
			m_list = [(str(x[0] + 1) + " " +x[1][0], x[1][1], x[1][2]) for x in enumerate(m_list)]

		self["menu"] = List(m_list)
		self["menu"].enableWrapAround = True
		if config.usage.menu_sort_mode.value == "user":
			self["menu"].onSelectionChanged.append(self.selectionChanged)

		self["actions"] = NumberActionMap(["OkCancelActions", "MenuActions", "NumberActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.closeNonRecursive,
				"menu": self.closeRecursive,
				#"0": self.resetSortOrder,
				"0": self.keyNumberGlobal,
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

		a = parent.get("title", "").encode("UTF-8") or None
		a = a and _(a)
		if a is None:
			a = _(parent.get("text", "").encode("UTF-8"))
		else:
			t_history.reset()
		self["title"] = StaticText(a)
		Screen.setTitle(self, a)
		self.menu_title = a

		self["thistory"] = StaticText(t_history.thistory)
		history_len = len(t_history.thistory)
		self["title0"] = StaticText('')
		self["title1"] = StaticText('')
		self["title2"] = StaticText('')
		if history_len < 13 :
			self["title0"] = StaticText(a)
		elif history_len < 21 :
			self["title0"] = StaticText('')
			self["title1"] = StaticText(a)
		else:
			self["title0"] = StaticText('')
			self["title1"] = StaticText('')
			self["title2"] = StaticText(a)

		if(t_history.thistory ==''):
			t_history.thistory = str(a) + ' > '
		else:
			t_history.thistory = t_history.thistory + str(a) + ' > '

		self.number = 0
		self.nextNumberTimer = eTimer()
		self.nextNumberTimer.callback.append(self.okbuttonClick)

	def isProtected(self):
		if config.ParentalControl.setuppinactive.value:
			if config.ParentalControl.config_sections.main_menu.value and self.menuID == "mainmenu":
				return True
			elif config.ParentalControl.config_sections.configuration.value and self.menuID == "setup":
				return True
			elif config.ParentalControl.config_sections.timer_menu.value and self.menuID == "timermenu":
				return True
			elif config.ParentalControl.config_sections.standby_menu.value and self.menuID == "shutdown":
				return True

	def keyNumberGlobal(self, number):
		self.number = self.number * 10 + number
		if self.number and self.number <= len(self["menu"].list):
			self["menu"].setIndex(self.number - 1)
			if len(self["menu"].list) < 10 or self.number >= 10:
				self.okbuttonClick()
			else:
				self.nextNumberTimer.start(1500, True)
		else:
			self.number = 0

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
		return MenuSummary

	def isProtected(self):
		if config.ParentalControl.setuppinactive.value:
			if config.ParentalControl.config_sections.main_menu.value:
				return self.menuID == "mainmenu"
			elif config.ParentalControl.config_sections.configuration.value and self.menuID == "setup":
				return True
			elif config.ParentalControl.config_sections.timer_menu.value and self.menuID == "timermenu":
				return True
			elif config.ParentalControl.config_sections.standby_menu.value and self.menuID == "shutdown":
				return True

	def updateList(self):
		self.sub_menu_sort = NoSave(ConfigDictionarySet())
		self.sub_menu_sort.value = config.usage.menu_sort_weight.getConfigValue(self.menuID, "submenu") or None
		idx = 0
		for x in self.list:
			entry = list(self.list.pop(idx))
			m_weight = self.sub_menu_sort.getConfigValue(entry[2], "sort") or entry[3]
			entry.append(m_weight)
			self.list.insert(idx, tuple(entry))
			self.sub_menu_sort.changeConfigValue(entry[2], "sort", m_weight)
			if not self.sort_mode and self.sub_menu_sort.getConfigValue(entry[2], "hidden"):
				self.list.remove(x)
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
		if self.sort_mode and len(self.list):
			m_entry = selection = self["menu"].getCurrent()
			select = False
			if self.selected_entry is None:
				select = True
			elif  self.selected_entry != m_entry[2]:
				select = True
			if not select:
				self["green"].setText(_("Move mode on"))
				self.selected_entry = None
			else:
				self["green"].setText(_("Move mode off"))
			idx = 0
			for x in self.list:
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
		tmp_list = list(self.list)
		entry = tmp_list.pop(self.cur_idx)
		newpos = self["menu"].getSelectedIndex()
		tmp_list.insert(newpos, entry)
		self.list = list(tmp_list)
		self["menu"].updateList(self.list)

	def keyBlue(self):
		if config.usage.menu_sort_mode.value == "user":
			self.toggleSortMode()

	def keyYellow(self):
		if self.sort_mode:
			m_entry = selection = self["menu"].getCurrent()[2]
			hidden = self.sub_menu_sort.getConfigValue(m_entry, "hidden") or 0
			if hidden:
				self.sub_menu_sort.removeConfigValue(m_entry, "hidden")
				self["yellow"].setText(_("hide"))
			else:
				self.sub_menu_sort.changeConfigValue(m_entry, "hidden", 1)
				self["yellow"].setText(_("show"))

	def keyGreen(self):
		if self.sort_mode:
			self.keyOk()

	def keyCancel(self):
		if self.sort_mode:
			self.toggleSortMode()
		else:
			self.closeNonRecursive()

	def resetSortOrder(self, key = None):
		config.usage.menu_sort_weight.value = { "mainmenu" : {"submenu" : {} }}
		config.usage.menu_sort_weight.save()
		self.closeRecursive()

	def toggleSortMode(self):
		if self.sort_mode:
			self["green"].setText("")
			self["yellow"].setText("")
			self["blue"].setText(_("Edit mode on"))
			self.sort_mode = False
			i = 10
			idx = 0
			for x in self.list:
				self.sub_menu_sort.changeConfigValue(x[2], "sort", i)
				if len(x) >= 5:
					entry = list(x)
					entry[4] = i
					entry = tuple(entry)
					self.list.pop(idx)
					self.list.insert(idx, entry)
				if self.selected_entry is not None:
					if x[2] == self.selected_entry:
						self.selected_entry = None
				i += 10
				idx += 1
			self.full_list = list(self.list)
			config.usage.menu_sort_weight.changeConfigValue(self.menuID, "submenu", self.sub_menu_sort.value)
			config.usage.menu_sort_weight.save()
			self.hide_show_entries()
			self["menu"].setList(self.list)
		else:
			self["green"].setText(_("Move mode on"))
			self["blue"].setText(_("Edit mode off"))
			self.sort_mode = True
			self.hide_show_entries()
			self["menu"].updateList(self.list)
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
			m_list.append(('',None,'dummy','10',10))
		m_list.sort(key=lambda listweight : int(listweight[4]))
		self.list = list(m_list)

	def selectionChanged(self):
		if self.sort_mode:
			selection = self["menu"].getCurrent()[2]
			if self.sub_menu_sort.getConfigValue(selection, "hidden"):
				self["yellow"].setText(_("show"))
			else:
				self["yellow"].setText(_("hide"))
		else:
			self["yellow"].setText("")

class MainMenu(Menu):
	#add file load functions for the xml-file

	def __init__(self, *x):
		self.skinName = "Menu"
		Menu.__init__(self, *x)
