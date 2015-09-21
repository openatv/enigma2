from Screens.Screen import Screen
from Components.ActionMap import NumberActionMap, ActionMap
from Components.config import config, ConfigNothing, ConfigYesNo, ConfigSelection, ConfigText, ConfigPassword
from Tools.Directories import resolveFilename, SCOPE_CURRENT_PLUGIN
from Components.SystemInfo import SystemInfo
from Components.ConfigList import ConfigListScreen
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.Sources.Boolean import Boolean

from enigma import eEnv
from boxbranding import getMachineBrand, getMachineName

import xml.etree.cElementTree

def setupdom(plugin=None):
	# read the setupmenu
	try:
		# first we search in the current path
		setupfile = file(resolveFilename(SCOPE_CURRENT_PLUGIN, plugin + '/setup.xml'), 'r')
	except:
		# if not found in the current path, we use the global datadir-path
		setupfile = file(eEnv.resolve('${datadir}/enigma2/setup.xml'), 'r')
	setupfiledom = xml.etree.cElementTree.parse(setupfile)
	setupfile.close()
	return setupfiledom

def getConfigMenuItem(configElement):
	for item in setupdom().getroot().findall('./setup/item/.'):
		if item.text == configElement:
			return _(item.attrib["text"]), eval(configElement)
	return "", None

class SetupError(Exception):
	def __init__(self, message):
		self.msg = message

	def __str__(self):
		return self.msg

class SetupSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
		self["SetupTitle"] = StaticText(_(parent.setup_title))
		self["SetupEntry"] = StaticText("")
		self["SetupValue"] = StaticText("")
		if hasattr(self.parent,"onChangedEntry"):
			self.onShow.append(self.addWatcher)
			self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if hasattr(self.parent,"onChangedEntry"):
			self.parent.onChangedEntry.append(self.selectionChanged)
			self.parent["config"].onSelectionChanged.append(self.selectionChanged)
			self.selectionChanged()

	def removeWatcher(self):
		if hasattr(self.parent,"onChangedEntry"):
			self.parent.onChangedEntry.remove(self.selectionChanged)
			self.parent["config"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self["SetupEntry"].text = self.parent.getCurrentEntry()
		self["SetupValue"].text = self.parent.getCurrentValue()
		if hasattr(self.parent,"getCurrentDescription") and self.parent.has_key("description"):
			self.parent["description"].text = self.parent.getCurrentDescription()

class Setup(ConfigListScreen, Screen):

	ALLOW_SUSPEND = True

	def removeNotifier(self):
		self.onNotifiers.remove(self.levelChanged)

	def levelChanged(self, configElement):
		list = []
		self.refill(list)
		self["config"].setList(list)

	def refill(self, list):
		xmldata = setupdom(self.plugin).getroot()
		for x in xmldata.findall("setup"):
			if x.get("key") != self.setup:
				continue
			self.addItems(list, x)
			self.setup_title = x.get("title", "").encode("UTF-8")
			self.seperation = int(x.get('separation', '0'))

	def __init__(self, session, setup, plugin=None):
		Screen.__init__(self, session)
		# for the skin: first try a setup_<setupID>, then Setup
		self.skinName = ["setup_" + setup, "Setup" ]

		self['footnote'] = Label(_("* = Restart Required"))
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)
		self["status"] = StaticText()
		self.onChangedEntry = [ ]
		self.item = None
		self.setup = setup
		self.plugin = plugin
		list = []
		self.onNotifiers = [ ]
		self.refill(list)
		ConfigListScreen.__init__(self, list, session = session, on_change = self.changedEntry)
		self.createSetup()

		#check for list.entries > 0 else self.close
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["description"] = Label("")

		self["actions"] = NumberActionMap(["SetupActions", "MenuActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
				"menu": self.closeRecursive,
			}, -2)

		self["VirtualKB"] = ActionMap(["VirtualKeyboardActions"],
		{
			"showVirtualKeyboard": self.KeyText,
		}, -2)
		self["VirtualKB"].setEnabled(False)

		if not self.handleInputHelpers in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.handleInputHelpers)
		self.changedEntry()
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.HideHelp)

	def createSetup(self):
		list = []
		self.refill(list)
		self["config"].setList(list)
		if config.usage.sort_settings.value:
			self["config"].list.sort()
		self.moveToItem(self.item)

	def getIndexFromItem(self, item):
		if item is not None:
			for x in range(len(self["config"].list)):
				if self["config"].list[x][0] == item[0]:
					return x
		return None

	def moveToItem(self, item):
		newIdx = self.getIndexFromItem(item)
		if newIdx is None:
			newIdx = 0
		self["config"].setCurrentIndex(newIdx)

	def handleInputHelpers(self):
		self["status"].setText(self["config"].getCurrent()[2])
		if self["config"].getCurrent() is not None:
			try:
				if isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
					if self.has_key("VKeyIcon"):
						self["VirtualKB"].setEnabled(True)
						self["VKeyIcon"].boolean = True
					if self.has_key("HelpWindow"):
						if self["config"].getCurrent()[1].help_window.instance is not None:
							helpwindowpos = self["HelpWindow"].getPosition()
							from enigma import ePoint
							self["config"].getCurrent()[1].help_window.instance.move(ePoint(helpwindowpos[0],helpwindowpos[1]))
				else:
					if self.has_key("VKeyIcon"):
						self["VirtualKB"].setEnabled(False)
						self["VKeyIcon"].boolean = False
			except:
				if self.has_key("VKeyIcon"):
					self["VirtualKB"].setEnabled(False)
					self["VKeyIcon"].boolean = False
		else:
			if self.has_key("VKeyIcon"):
				self["VirtualKB"].setEnabled(False)
				self["VKeyIcon"].boolean = False

	def HideHelp(self):
		self.help_window_was_shown = False
		try:
			if isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
				if self["config"].getCurrent()[1].help_window.instance is not None:
					self["config"].getCurrent()[1].help_window.hide()
					self.help_window_was_shown = True
		except:
			pass

	def KeyText(self):
		if isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
			if self["config"].getCurrent()[1].help_window.instance is not None:
				self["config"].getCurrent()[1].help_window.hide()
		from Screens.VirtualKeyBoard import VirtualKeyBoard
		self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title = self["config"].getCurrent()[0], text = self["config"].getCurrent()[1].value)

	def VirtualKeyBoardCallback(self, callback = None):
		if callback is not None and len(callback):
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidate(self["config"].getCurrent())

	def layoutFinished(self):
		self.setTitle(_(self.setup_title))

	# for summary:
	def changedEntry(self):
		self.item = self["config"].getCurrent()
		try:
			#FIXME This code prevents an LCD refresh for this ConfigElement(s)
			if not isinstance(self["config"].getCurrent()[1], ConfigText):
				self.createSetup()
		except:
			pass

	def addItems(self, list, parentNode):
		for x in parentNode:
			if not x.tag:
				continue
			if x.tag == 'item':
				item_level = int(x.get("level", 0))

				if not self.onNotifiers:
					self.onNotifiers.append(self.levelChanged)
					self.onClose.append(self.removeNotifier)

				if item_level > config.usage.setup_level.index:
					continue

				requires = x.get("requires")
				if requires and requires.startswith('config.'):
					item = eval(requires or "")
					if item.value and not item.value == "0":
						SystemInfo[requires] = True
					else:
						SystemInfo[requires] = False

				if requires and not SystemInfo.get(requires, False):
					continue

				item_text = _(x.get("text", "??").encode("UTF-8"))
				item_text = item_text.replace("%s %s","%s %s" % (getMachineBrand(), getMachineName()))
				item_description = _(x.get("description", " ").encode("UTF-8"))
				item_description = item_description.replace("%s %s","%s %s" % (getMachineBrand(), getMachineName()))
				b = eval(x.text or "")
				if b == "":
					continue
				#add to configlist
				item = b
				# the first b is the item itself, ignored by the configList.
				# the second one is converted to string.
				if not isinstance(item, ConfigNothing):
					list.append((item_text, item, item_description))

def getSetupTitle(id):
	xmldata = setupdom().getroot()
	for x in xmldata.findall("setup"):
		if x.get("key") == id:
			if _(x.get("title", "").encode("UTF-8")) == _("OSD Settings") or _(x.get("title", "").encode("UTF-8")) == _("Softcam Setup") or _(x.get("title", "").encode("UTF-8")) == _("EPG settings"):
				return _("Settings...")
			return x.get("title", "").encode("UTF-8")
	raise SetupError("unknown setup id '%s'!" % repr(id))

def getSetupTitleLevel(id):
	xmldata = setupdom().getroot()
	for x in xmldata.findall("setup"):
		if x.get("key") == id:
			return int(x.get("level", 0))
	return 0
