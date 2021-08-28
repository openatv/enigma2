from gettext import dgettext
from os.path import getmtime, join as pathjoin
from six import PY2
from xml.etree.cElementTree import ParseError, fromstring, parse

from skin import setups
from Components.config import ConfigBoolean, ConfigNothing, ConfigSelection, config
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.SystemInfo import BoxInfo
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen, ScreenSummary
from Tools.Directories import SCOPE_CURRENT_SKIN, SCOPE_PLUGINS, SCOPE_SKIN, fileReadXML, resolveFilename
from Tools.LoadPixmap import LoadPixmap

MODULE_NAME = __name__.split(".")[-1]

domSetups = {}
setupModTimes = {}


class Setup(ConfigListScreen, Screen, HelpableScreen):
	skin = """
	<screen name="Setup" position="center,center" size="980,570" resolution="1280,720">
		<widget name="config" position="10,10" size="e-20,350" enableWrapAround="1" font="Regular;25" itemHeight="35" scrollbarMode="showOnDemand" />
		<widget name="footnote" position="10,e-185" size="e-20,25" font="Regular;20" valign="center" />
		<widget name="description" position="10,e-160" size="e-20,100" font="Regular;20" valign="center" />
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="390,e-50" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="580,e-50" size="180,40" backgroundColor="key_blue" conditional="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_menu" render="Label" position="e-400,e-50" size="90,40" backgroundColor="key_back" conditional="key_menu" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_info" render="Label" position="e-300,e-50" size="90,40" backgroundColor="key_back" conditional="key_info" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="VKeyIcon" text="TEXT" render="Label" position="e-200,e-50" size="90,40" backgroundColor="key_back" conditional="VKeyIcon" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-100,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" conditional="key_help" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget name="setupimage" position="0,0" size="0,0" alphatest="blend" conditional="setupimage" transparent="1" />
		<widget name="HelpWindow" position="0,0" size="0,0" alphatest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
	</screen>"""

	def __init__(self, session, setup, plugin=None, PluginLanguageDomain=None):
		Screen.__init__(self, session, mandatoryWidgets=["config", "footnote", "description"])
		HelpableScreen.__init__(self)
		self.setup = setup
		self.plugin = plugin
		self.pluginLanguageDomain = PluginLanguageDomain
		if not isinstance(self.skinName, list):
			self.skinName = [self.skinName]
		self.skinName.append("setup_%s" % setup)
		self.skinName.append("Setup%s" % setup)
		self.skinName.append("Setup")
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry, fullUI=True)
		self["footnote"] = Label()
		self["footnote"].hide()
		self["description"] = Label()
		self.createSetup()
		defaultSetupImage = setups.get("default", "")
		setupImage = setups.get(setup, defaultSetupImage)
		if setupImage:
			print("[Setup] %s image '%s'." % ("Default" if setupImage is defaultSetupImage else "Setup", setupImage))
			setupImage = resolveFilename(SCOPE_CURRENT_SKIN, setupImage)
			self.setupImage = LoadPixmap(setupImage)
			if self.setupImage:
				self["setupimage"] = Pixmap()
			else:
				print("[Setup] Error: Unable to load image '%s'!" % setupImage)
		else:
			self.setupImage = None
		self["config"].onSelectionChanged.append(self.selectionChanged)
		self.onLayoutFinish.append(self.layoutFinished)

	def changedEntry(self):
		if isinstance(self["config"].getCurrent()[1], (ConfigBoolean, ConfigSelection)):
			self.createSetup()

	def createSetup(self):
		oldList = self.list
		self.showDefaultChanged = False
		self.graphicSwitchChanged = False
		self.list = []
		title = None
		xmlData = setupDom(self.setup, self.plugin)
		for setup in xmlData.findall("setup"):
			if setup.get("key") == self.setup:
				self.addItems(setup)
				skin = setup.get("skin", None)
				if skin and skin != "":
					self.skinName.insert(0, skin)
				title = setup.get("title", None).encode("UTF-8", errors="ignore") if PY2 else setup.get("title", None)
				# If this break is executed then there can only be one setup tag with this key.
				# This may not be appropriate if conditional setup blocks become available.
				break
		self.setTitle(_(title) if title and title != "" else _("Setup"))
		if self.list != oldList or self.showDefaultChanged or self.graphicSwitchChanged:
			currentItem = self["config"].getCurrent()
			self["config"].setList(self.list)
			if config.usage.sort_settings.value:
				self["config"].list.sort()
			self.moveToItem(currentItem)

	def addItems(self, parentNode, including=True):
		for element in parentNode:
			if not element.tag:
				continue
			if element.tag in ("elif", "else") and including:
				break  # End of succesful if/elif branch - short-circuit rest of children.
			include = self.includeElement(element)
			if element.tag == "item":
				if including and include:
					self.addItem(element)
			elif element.tag == "if":
				if including:
					self.addItems(element, including=include)
			elif element.tag == "elif":
				including = include
			elif element.tag == "else":
				including = True

	def addItem(self, element):
		if self.pluginLanguageDomain:
			itemText = dgettext(self.pluginLanguageDomain, element.get("text", "??").encode("UTF-8", errors="ignore")) if PY2 else dgettext(self.pluginLanguageDomain, element.get("text", "??"))
			itemDescription = dgettext(self.pluginLanguageDomain, element.get("description", " ").encode("UTF-8", errors="ignore")) if PY2 else dgettext(self.pluginLanguageDomain, element.get("description", " "))
		else:
			itemText = _(element.get("text", "??").encode("UTF-8", errors="ignore")) if PY2 else _(element.get("text", "??"))
			itemDescription = _(element.get("description", " ").encode("UTF-8", errors="ignore")) if PY2 else _(element.get("description", " "))
		item = eval(element.text or "")
		if item != "" and not isinstance(item, ConfigNothing):
			self.list.append((self.formatItemText(itemText), item, self.formatItemDescription(item, itemDescription)))  # Add the item to the config list.
		if item is config.usage.setupShowDefault:
			self.showDefaultChanged = True
		if item is config.usage.boolean_graphic:
			self.graphicSwitchChanged = True

	def formatItemText(self, itemText):
		return itemText.replace("%s %s", "%s %s" % (BoxInfo.getItem("displaybrand"), BoxInfo.getItem("displaymodel")))

	def formatItemDescription(self, item, itemDescription):
		itemDescription = itemDescription.replace("%s %s", "%s %s" % (BoxInfo.getItem("displaybrand"), BoxInfo.getItem("displaymodel")))
		if config.usage.setupShowDefault.value:
			spacer = "\n" if config.usage.setupShowDefault.value == "newline" else "  "
			itemDefault = item.toDisplayString(item.default)
			itemDescription = _("%s%s(Default: %s)") % (itemDescription, spacer, itemDefault) if itemDescription and itemDescription != " " else _("Default: '%s'.") % itemDefault
		return itemDescription

	def includeElement(self, element):
		itemLevel = int(element.get("level", 0))
		if itemLevel > config.usage.setup_level.index:  # The item is higher than the current setup level.
			return False
		requires = element.get("requires")
		if requires:
			for require in [x.strip() for x in requires.split(";")]:
				negate = require.startswith("!")
				if negate:
					require = require[1:]
				if require.startswith("config."):
					try:
						result = eval(require)
						result = bool(result.value and str(result.value).lower() not in ("0", "disable", "false", "no", "off"))
					except Exception:
						return self.logIncludeElementError(element, "requires", require)
				else:
					result = bool(BoxInfo.getItem(require, False))
				if require and negate == result:  # The item requirements are not met.
					return False
		conditional = element.get("conditional")
		if conditional:
			try:
				if not bool(eval(conditional)):
					return False
			except Exception:
				return self.logIncludeElementError(element, "conditional", conditional)
		return True

	def logIncludeElementError(self, element, type, token):
		item = "title" if element.tag == "screen" else "text"
		text = element.get(item)
		print("[Setup]")
		print("[Setup] Error: Tag '%s' with %s of '%s' has a %s '%s' that can't be evaluated!" % (element.tag, item, text, type, token))
		print("[Setup] NOTE: Ignoring this error may have consequences like unexpected operation or system failures!")
		print("[Setup]")
		return False

	def selectionChanged(self):
		if self["config"]:
			self.setFootnote(None)
			self["description"].text = self.getCurrentDescription()
		else:
			self["description"].text = _("There are no items currently available for this screen.")

	def layoutFinished(self):
		if self.setupImage:
			self["setupimage"].instance.setPixmap(self.setupImage)
		if not self["config"]:
			print("[Setup] No setup items available!")

	def setFootnote(self, footnote):
		if footnote is None:
			if self.getCurrentEntry().endswith("*"):
				self["footnote"].text = _("* = Restart Required")
				self["footnote"].show()
			else:
				self["footnote"].text = ""
				self["footnote"].hide()
		else:
			self["footnote"].text = footnote
			self["footnote"].show()

	def getFootnote(self):
		return self["footnote"].text

	def moveToItem(self, item):
		if item != self["config"].getCurrent():
			self["config"].setCurrentIndex(self.getIndexFromItem(item))

	def getIndexFromItem(self, item):
		if item is None:  # If there is no item position at the top of the config list.
			return 0
		if item in self["config"].list:  # If the item is in the config list position to that item.
			return self["config"].list.index(item)
		for pos, data in enumerate(self["config"].list):
			if data[0] == item[0] and data[1] == item[1]:  # If the label and config class match then position to that item.
				return pos
		return 0  # We can't match the item to the config list then position to the top of the list.

	def createSummary(self):
		return SetupSummary


class SetupSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self["entry"] = StaticText("")  # DEBUG: Proposed for new summary screens.
		self["value"] = StaticText("")  # DEBUG: Proposed for new summary screens.
		self["SetupTitle"] = StaticText(parent.getTitle())
		self["SetupEntry"] = StaticText("")
		self["SetupValue"] = StaticText("")
		if self.addWatcher not in self.onShow:
			self.onShow.append(self.addWatcher)
		if self.removeWatcher not in self.onHide:
			self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if self.selectionChanged not in self.parent.onChangedEntry:
			self.parent.onChangedEntry.append(self.selectionChanged)
		if self.selectionChanged not in self.parent["config"].onSelectionChanged:
			self.parent["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def removeWatcher(self):
		if self.selectionChanged in self.parent.onChangedEntry:
			self.parent.onChangedEntry.remove(self.selectionChanged)
		if self.selectionChanged in self.parent["config"].onSelectionChanged:
			self.parent["config"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self["entry"].text = self.parent.getCurrentEntry()  # DEBUG: Proposed for new summary screens.
		self["value"].text = self.parent.getCurrentValue()  # DEBUG: Proposed for new summary screens.
		self["SetupEntry"].text = self.parent.getCurrentEntry()
		self["SetupValue"].text = self.parent.getCurrentValue()
		# FIXME This part is a fallback for old Setup based Screens
		if hasattr(self.parent, "getCurrentDescription") and "description" in self.parent:
			self.parent["description"].text = self.parent.getCurrentDescription()
		if 'footnote' in self.parent:
			if self.parent.getCurrentEntry().endswith('*'):
				self.parent['footnote'].text = (_("* = Restart Required"))
			else:
				self.parent['footnote'].text = (_(" "))


# Read the setup XML file.
#
def setupDom(setup=None, plugin=None):
	# Constants for checkItems()
	ROOT_ALLOWED = ("setup", )  # Tags allowed in top level of setupxml entry.
	ELEMENT_ALLOWED = ("item", "if")  # Tags allowed in top level of setup entry.
	IF_ALLOWED = ("item", "if", "elif", "else")  # Tags allowed inside <if />.
	AFTER_ELSE_ALLOWED = ("item", "if")  # Tags allowed after <elif /> or <else />.
	CHILDREN_ALLOWED = ("setup", "if", )  # Tags that may have children.
	TEXT_ALLOWED = ("item", )  # Tags that may have non-whitespace text (or tail).
	KEY_ATTRIBUTES = {  # Tags that have a reference key mandatory attribute.
		"setup": "key",
		"item": "text"
	}
	MANDATORY_ATTRIBUTES = {  # Tags that have a list of mandatory attributes.
		"setup": ("key", "title"),
		"item": ("text", )
	}

	def checkItems(parentNode, key, allowed=ROOT_ALLOWED, mandatory=MANDATORY_ATTRIBUTES, reference=KEY_ATTRIBUTES):
		keyText = " in '%s'" % key if key else ""
		for element in parentNode:
			if element.tag not in allowed:
				print("[Setup] Error: Tag '%s' not permitted%s!  (Permitted: '%s')" % (element.tag, keyText, ", ".join(allowed)))
				continue
			if mandatory and element.tag in mandatory:
				valid = True
				for attrib in mandatory[element.tag]:
					if element.get(attrib) is None:
						print("[Setup] Error: Tag '%s'%s does not contain the mandatory '%s' attribute!" % (element.tag, keyText, attrib))
						valid = False
				if not valid:
					continue
			if element.tag not in TEXT_ALLOWED:
				if element.text and not element.text.isspace():
					print("[Setup] Tag '%s'%s contains text '%s'." % (element.tag, keyText, element.text.strip()))
				if element.tail and not element.tail.isspace():
					print("[Setup] Tag '%s'%s has trailing text '%s'." % (element.tag, keyText, element.text.strip()))
			if element.tag not in CHILDREN_ALLOWED and len(element):
				itemKey = ""
				if element.tag in reference:
					itemKey = " (%s)" % element.get(reference[element.tag])
				print("[Setup] Tag '%s'%s%s contains children where none expected." % (element.tag, itemKey, keyText))
			if element.tag in CHILDREN_ALLOWED:
				if element.tag in reference:
					key = element.get(reference[element.tag])
				checkItems(element, key, allowed=IF_ALLOWED)
			elif element.tag == "else":
				allowed = AFTER_ELSE_ALLOWED  # Another else and elif not permitted after else.
			elif element.tag == "elif":
				pass

	setupFileDom = fromstring("<setupxml></setupxml>")
	setupFile = resolveFilename(SCOPE_PLUGINS, pathjoin(plugin, "setup.xml")) if plugin else resolveFilename(SCOPE_SKIN, "setup.xml")
	global domSetups, setupModTimes
	try:
		modTime = getmtime(setupFile)
	except (IOError, OSError) as err:
		print("[Setup] Error: Unable to get '%s' modified time - Error (%d): %s!" % (setupFile, err.errno, err.strerror))
		if setupFile in domSetups:
			del domSetups[setupFile]
		if setupFile in setupModTimes:
			del setupModTimes[setupFile]
		return setupFileDom
	cached = setupFile in domSetups and setupFile in setupModTimes and setupModTimes[setupFile] == modTime
	print("[Setup] XML%s setup file '%s', using element '%s'%s." % (" cached" if cached else "", setupFile, setup, " from plugin '%s'" % plugin if plugin else ""))
	if cached:
		return domSetups[setupFile]
	if setupFile in domSetups:
		del domSetups[setupFile]
	if setupFile in setupModTimes:
		del setupModTimes[setupFile]
	fileDom = fileReadXML(setupFile, source=MODULE_NAME)
	if fileDom:
		checkItems(fileDom, None)
		setupFileDom = fileDom
		domSetups[setupFile] = setupFileDom
		setupModTimes[setupFile] = modTime
		for setup in setupFileDom.findall("setup"):
			key = setup.get("key")
			if key:  # If there is no key then this element is useless and can be skipped!
				title = setup.get("title", "").encode("UTF-8", errors="ignore") if PY2 else setup.get("title", "")
				if title == "":
					print("[Setup] Error: Setup key '%s' title is missing or blank!" % key)
					title = "** Setup error: '%s' title is missing or blank!" % key
				# print("[Setup] DEBUG: XML setup load: key='%s', title='%s'." % (key, setup.get("title", "").encode("UTF-8", errors="ignore")))
	return setupFileDom


# Temporary legacy interface.  Known to be used by the Heinz plugin and possibly others.
#
def setupdom(setup=None, plugin=None):
	return setupDom(setup, plugin)


# Only used in AudioSelection screen...
#
def getConfigMenuItem(configElement):
	for item in setupDom().findall("./setup/item/."):
		if item.text == configElement:
			return _(item.attrib["text"]), eval(configElement)
	return "", None


# Temporary legacy interfaces.  Only used in Menu screen.
#
def getSetupTitle(id):
	xmlData = setupDom()
	for x in xmlData.findall("setup"):
		if x.get("key") == id:
			return x.get("title", "").encode("UTF-8", errors="ignore") if PY2 else x.get("title", "")
	print("[Setup] Error: Unknown setup id '%s'!" % repr(id))
	return "Unknown setup id '%s'!" % repr(id)


def getSetupTitleLevel(setupId):
	xmlData = setupDom()
	for x in xmlData.findall("setup"):
		if x.get("key") == setupId:
			return int(x.get("level", 0))
	return 0
