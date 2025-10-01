from enigma import eListbox, eListboxPythonConfigContent, ePoint, eRCInput, eTimer

from skin import parameters
from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import ACTIONKEY_0, ACTIONKEY_ASCII, ACTIONKEY_BACKSPACE, ACTIONKEY_DELETE, ACTIONKEY_ERASE, ACTIONKEY_FIRST, ACTIONKEY_LAST, ACTIONKEY_LEFT, ACTIONKEY_NUMBERS, ACTIONKEY_RIGHT, ACTIONKEY_SELECT, ACTIONKEY_TIMEOUT, ACTIONKEY_TOGGLE, ConfigBoolean, ConfigElement, ConfigInteger, ConfigMACText, ConfigNumber, ConfigSelection, ConfigSequence, ConfigText, config, configfile
from Components.GUIComponent import GUIComponent
from Components.Pixmap import Pixmap
from Components.Sources.Boolean import Boolean
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import getBoxDisplayName
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Standby import QUIT_REBOOT, QUIT_RESTART, TryQuitMainloop
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.BoundFunction import boundFunction


class ConfigList(GUIComponent):
	GUI_WIDGET = eListbox

	def __init__(self, list, session=None):
		GUIComponent.__init__(self)
		self.session = session
		self.l = eListboxPythonConfigContent()
		seperation = parameters.get("ConfigListSeperator", 200)
		self.l.setSeperation(seperation)
		height, borderWidth = parameters.get("ConfigListSlider", (17, 0))
		self.l.setSlider(height, borderWidth)
		self.list = list
		self.timer = eTimer()
		self.onSelectionChanged = []
		self.current = None

	def execBegin(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmAscii if not config.misc.remotecontrol_text_support.value else rcinput.kmNone)
		self.timer.callback.append(self.timeout)

	def execEnd(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)
		self.timer.stop()
		self.timer.callback.remove(self.timeout)

	def timeout(self):
		self.handleKey(ACTIONKEY_TIMEOUT)

	def postWidgetCreate(self, instance):
		instance.selectionChanged.get().append(self.selectionChanged)
		instance.setContent(self.l)

	def preWidgetRemove(self, instance):
		if isinstance(self.current, tuple) and len(self.current) >= 2:
			self.current[1].onDeselect(self.session)
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)

	def selectionChanged(self):
		if isinstance(self.current, tuple) and len(self.current) >= 2:
			self.current[1].onDeselect(self.session)
		self.current = self.getCurrent(full=False)
		if isinstance(self.current, tuple) and len(self.current) >= 2:
			self.current[1].onSelect(self.session)
		else:
			return
		for callback in self.onSelectionChanged:
			callback()

	def getCurrent(self, full=True):
		item = self.l.getCurrentSelection()
		if full and item and len(item) > 1 and isinstance(item[0], tuple):
			item = (item[0][0],) + item[1:]
		return item

	def handleKey(self, key, callback=None):
		selection = self.getCurrent(full=False)
		if selection and selection[1].enabled:
			changed = selection[1].handleKey(key, callback)
			self.invalidateCurrent()
			if key in ACTIONKEY_NUMBERS:
				self.timer.start(1000, 1)
			return changed
		return False

	def toggle(self):
		self.getCurrent(full=False)[1].toggle()
		self.invalidateCurrent()

	def getCurrentIndex(self):
		return self.l.getCurrentSelectionIndex()

	def setCurrentIndex(self, index):
		if self.instance:
			self.instance.moveSelectionTo(index)

	def invalidateCurrent(self):
		self.l.invalidateEntry(self.l.getCurrentSelectionIndex())

	def invalidate(self, entry):
		# When the entry to invalidate does not exist, just ignore the request.
		# This eases up conditional setup screens a lot.
		if entry in self.__list:
			self.l.invalidateEntry(self.__list.index(entry))

	def isChanged(self):
		for item in self.list:
			if len(item) > 1 and item[1].isChanged():
				return True
		return False

	def selectionEnabled(self, enabled):
		if self.instance:
			self.instance.setSelectionEnable(enabled)

	def enableAutoNavigation(self, enabled):
		if self.instance:
			self.instance.enableAutoNavigation(enabled)

	def getList(self):
		return self.__list

	def setList(self, newList):
		self.__list = newList
		self.l.setList(self.__list)
		if newList is not None:
			for x in newList:
				assert len(x) < 2 or isinstance(x[1], ConfigElement), "[ConfigList] Error: Entry in ConfigList '%s' must be a ConfigElement!" % str(x[1])

	list = property(getList, setList)

	def goTop(self):
		if self.instance:
			self.instance.goTop()

	def goPageUp(self):
		if self.instance:
			self.instance.goPageUp()

	def goLineUp(self):
		if self.instance:
			self.instance.goLineUp()

	def goLineDown(self):
		if self.instance:
			self.instance.goLineDown()

	def goPageDown(self):
		if self.instance:
			self.instance.goPageDown()

	def goBottom(self):
		if self.instance:
			self.instance.goBottom()

	# Old navigation method names.
	#
	def moveTop(self):
		self.goTop()

	def pageUp(self):
		self.goPageUp()

	def moveUp(self):
		self.goLineUp()

	def moveDown(self):
		self.goLineDown()

	def pageDown(self):
		self.goPageDown()

	def moveBottom(self):
		self.goBottom()


class ConfigListScreen:
	def __init__(self, list, session=None, on_change=None, fullUI=False, allowDefault=False):
		self.entryChanged = on_change if on_change is not None else lambda: None
		if fullUI:
			if "key_red" not in self:
				self["key_red"] = StaticText(_("Cancel"))
			if "key_green" not in self:
				self["key_green"] = StaticText(_("Save"))
			self["fullUIActions"] = HelpableActionMap(self, ["ConfigListActions"], {
				"cancel": (self.keyCancel, _("Cancel any changed settings and exit")),
				"close": (self.closeRecursive, _("Cancel any changed settings and exit all menus")),
				"save": (self.keySave, _("Save all changed settings and exit"))
			}, prio=1, description=_("Common Setup Actions"))
			self.actionMaps = ["fullUIActions"]
			if allowDefault:
				if "key_yellow" not in self:
					self["key_yellow"] = StaticText(_("Default"))
				self["defaultAction"] = HelpableActionMap(self, ["ConfigListActions", "ColorActions"], {
					"default": (self.keyDefault, _("Reset entries to their default values")),
					"yellow": (self.keyDefault, _("Reset entries to their default values"))
				}, prio=1, description=_("Common Setup Actions"))
				self.actionMaps.append("defaultAction")
		else:
			self.actionMaps = []
		if "key_menu" not in self:
			self["key_menu"] = StaticText(_("MENU"))
		if "key_text" not in self:
			self["key_text"] = StaticText(_("TEXT"))
		if "VKeyIcon" not in self:
			self["VKeyIcon"] = Boolean(False)
		if "HelpWindow" not in self:
			self["HelpWindow"] = Pixmap()
			self["HelpWindow"].hide()
		self["configActions"] = HelpableActionMap(self, ["ConfigListActions"], {
			"select": (self.keySelect, _("Select, toggle, process or edit the current entry"))
		}, prio=1, description=_("Common Setup Actions"))
		self["navigationActions"] = HelpableActionMap(self, ["NavigationActions"], {
			"top": (self.keyTop, _("Move to the first line / screen")),
			"pageUp": (self.keyPageUp, _("Move up a screen")),
			"up": (self.keyUp, _("Move up a line")),
			"first": (self.keyFirst, _("Select the first item in list or move to the start of text")),
			"left": (self.keyLeft, _("Select the previous item in list or move the cursor left")),
			"right": (self.keyRight, _("Select the next item in list or move the cursor right")),
			"last": (self.keyLast, _("Select the last item in list or move to the end of text")),
			"down": (self.keyDown, _("Move down a line")),
			"pageDown": (self.keyPageDown, _("Move down a screen")),
			"bottom": (self.keyBottom, _("Move to the last line / screen"))
		}, prio=1, description=_("Common Setup Actions"))
		self["menuConfigActions"] = HelpableActionMap(self, "ConfigListActions", {
			"menu": (self.keyMenu, _("Display selection list as a selection menu")),
		}, prio=1, description=_("Common Setup Actions"))
		self["menuConfigActions"].setEnabled(False if fullUI else True)
		self["charConfigActions"] = HelpableNumberActionMap(self, ["NumberActions", "InputAsciiActions"], {
			"1": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"2": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"3": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"4": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"5": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"6": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"7": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"8": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"9": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"0": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"gotAsciiCode": (self.keyGotAscii, _("Keyboard data entry"))
		}, prio=1, description=_("Common Setup Actions"))
		self["charConfigActions"].setEnabled(False if fullUI else True)
		self["editConfigActions"] = HelpableActionMap(self, ["TextEditActions"], {
			"backspace": (self.keyBackspace, _("Delete character to left of cursor or select AM times")),
			"delete": (self.keyDelete, _("Delete character under cursor or select PM times")),
			"erase": (self.keyErase, _("Delete all the text")),
			"toggleOverwrite": (self.keyToggle, _("Toggle if new text inserts before or overwrites existing text")),
		}, prio=1, description=_("Common Setup Actions"))
		self["editConfigActions"].setEnabled(False if fullUI else True)
		self["virtualKeyBoardActions"] = HelpableActionMap(self, "VirtualKeyboardActions", {
			"showVirtualKeyboard": (self.keyText, _("Display the virtual keyboard for data entry"))
		}, prio=1, description=_("Common Setup Actions"))
		self["virtualKeyBoardActions"].setEnabled(False)
		self.actionMaps.extend([
			"configActions",
			"navigationActions",
			"menuConfigActions",
			"charConfigActions",
			"editConfigActions",
			"virtualKeyBoardActions"
		])
		# Temporary support for legacy code and plugins that hasn't yet been updated (next 4 lines).
		# All code should be updated to allow a better UI experience for users.  This patch code
		# forces course control over the edit buttons instead of individual button control that is
		# now available.
		self["config_actions"] = DummyActions()
		self["config_actions"].setEnabled = self.dummyConfigActions
		self["VirtualKB"] = DummyActions()
		self["VirtualKB"].setEnabled = self.dummyVKBActions
		self["config"] = ConfigList(list, session=session)
		self.setCancelMessage(None)
		self.setRestartMessage(None)
		self.onChangedEntry = []
		self.onSave = []
		self.onExecBegin.append(self.showHelpWindow)
		self.onExecEnd.append(self.hideHelpWindow)
		self.onLayoutFinish.append(self.disableNativeActionMaps)  # self.layoutFinished is already in use!
		self["config"].onSelectionChanged.append(self.handleInputHelpers)

	def setCancelMessage(self, msg):
		self.cancelMsg = _("Really close without saving settings?") if msg is None else msg

	def setRestartMessage(self, msg):
		self.restartMsg = _("Restart GUI now?") if msg is None else msg

	def getCurrentItem(self):
		return self["config"].getCurrent(full=False) and self["config"].getCurrent()[1] or None

	def getCurrentEntry(self):
		return self["config"].getCurrent() and self["config"].getCurrent()[0] or ""

	def getCurrentValue(self):
		return self["config"].getCurrent(full=False) and str(self["config"].getCurrent()[1].getText()) or ""

	def getCurrentDescription(self):
		return self["config"].getCurrent(full=False) and len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2] or ""

	def changedEntry(self):
		for callback in self.onChangedEntry:
			callback()

	def disableNativeActionMaps(self):
		self["config"].enableAutoNavigation(False)

	def suspendAllActionMaps(self):
		self.actionMapStates = []
		for actionMap in self.actionMaps:
			self.actionMapStates.append(self[actionMap].getEnabled())
			self[actionMap].setEnabled(False)

	def resumeAllActionMaps(self):
		if hasattr(self, "actionMapStates"):
			for index, actionMap in enumerate(self.actionMaps):
				self[actionMap].setEnabled(self.actionMapStates[index])

	def handleInputHelpers(self):
		currConfig = self["config"].getCurrent(full=False)
		if currConfig is not None:
			if isinstance(currConfig[1], (ConfigInteger, ConfigSequence, ConfigText)):
				self["charConfigActions"].setEnabled(True)
				self["editConfigActions"].setEnabled(True)
			else:
				self["charConfigActions"].setEnabled(False)
				self["editConfigActions"].setEnabled(False)
			if isinstance(currConfig[1], ConfigSelection):
				self["menuConfigActions"].setEnabled(True)
				self["key_menu"].setText(_("MENU"))
			else:
				self["menuConfigActions"].setEnabled(False)
				self["key_menu"].setText("")
			if isinstance(currConfig[1], ConfigText):
				self.showVirtualKeyBoard(True)
				if "HelpWindow" in self and currConfig[1].help_window and currConfig[1].help_window.instance is not None:
					helpwindowpos = self["HelpWindow"].getPosition()
					currConfig[1].help_window.instance.move(ePoint(helpwindowpos[0], helpwindowpos[1]))
			else:
				self.showVirtualKeyBoard(False)
			if isinstance(currConfig[1], ConfigMACText):
				self["editConfigActions"].setEnabled(False)
				self.showVirtualKeyBoard(False)
			if isinstance(currConfig[1], ConfigNumber):
				self.showVirtualKeyBoard(False)

	def showVirtualKeyBoard(self, state):
		if "key_text" in self or "VKeyIcon" in self:
			self["key_text"].setText(_("TEXT") if state else "")
			self["VKeyIcon"].boolean = state
			self["virtualKeyBoardActions"].setEnabled(state)

	def showHelpWindow(self):
		self.displayHelp(True)

	def hideHelpWindow(self):
		self.displayHelp(False)

	def displayHelp(self, state):
		if "config" in self and "HelpWindow" in self and self["config"].getCurrent() is not None and len(self["config"].getCurrent()) > 1:
			currConf = self["config"].getCurrent(full=False)[1]
			if isinstance(currConf, ConfigText) and currConf.help_window is not None and currConf.help_window.instance is not None:
				if state:
					currConf.help_window.show()
				else:
					currConf.help_window.hide()

	def keySelect(self):
		if isinstance(self.getCurrentItem(), ConfigBoolean):
			self.keyToggle()
		elif isinstance(self.getCurrentItem(), ConfigSelection):
			self.keyMenu()
		elif isinstance(self.getCurrentItem(), ConfigText) and not isinstance(self.getCurrentItem(), (ConfigMACText, ConfigNumber)):
			self.keyText()
		else:
			self["config"].handleKey(ACTIONKEY_SELECT, self.entryChanged)

	def keyOK(self):  # This is the deprecated version of keySelect!
		self.keySelect()

	def keyDefault(self):  # This method should be replaced in sub-classes that need help to reset the defaults.
		for item in self["config"].getList():
			item[1].setValue(item[1].default)
			self["config"].invalidate(item)

	def keyText(self):
		def keyTextCallback(callback=None):
			if callback is not None:
				prev = str(self.getCurrentValue())
				self["config"].getCurrent(full=False)[1].setValue(callback)
				self["config"].invalidateCurrent()
				if callback != prev:
					self.entryChanged()

		self.session.openWithCallback(keyTextCallback, VirtualKeyBoard, title=self.getCurrentEntry(), text=str(self.getCurrentValue()))

	def keyMenu(self):
		def keyMenuCallback(answer):
			if answer:
				prev = str(self.getCurrentValue())
				self["config"].getCurrent(full=False)[1].setValue(answer[1])
				self["config"].invalidateCurrent()
				if answer[1] != prev:
					self.entryChanged()

		currConfig = self["config"].getCurrent()
		if currConfig and currConfig[1].enabled and hasattr(currConfig[1], "description"):
			self.session.openWithCallback(keyMenuCallback, ChoiceBox, text=self.getCurrentDescription(), choiceList=list(zip(currConfig[1].description, currConfig[1].choices)), selection=currConfig[1].getIndex(), buttonList=[], windowTitle=currConfig[0])

	def keyTop(self):
		self["config"].goTop()

	def keyPageUp(self):
		self["config"].goPageUp()

	def keyUp(self):
		self["config"].goLineUp()

	def keyFirst(self):
		self["config"].handleKey(ACTIONKEY_FIRST, self.entryChanged)

	def keyLeft(self):
		self["config"].handleKey(ACTIONKEY_LEFT, self.entryChanged)

	def keyRight(self):
		self["config"].handleKey(ACTIONKEY_RIGHT, self.entryChanged)

	def keyLast(self):
		self["config"].handleKey(ACTIONKEY_LAST, self.entryChanged)

	def keyDown(self):
		self["config"].goLineDown()

	def keyPageDown(self):
		self["config"].goPageDown()

	def keyBottom(self):
		self["config"].goBottom()

	def keyBackspace(self):
		self["config"].handleKey(ACTIONKEY_BACKSPACE, self.entryChanged)

	def keyDelete(self):
		self["config"].handleKey(ACTIONKEY_DELETE, self.entryChanged)

	def keyErase(self):
		self["config"].handleKey(ACTIONKEY_ERASE, self.entryChanged)

	def keyToggle(self):
		self["config"].handleKey(ACTIONKEY_TOGGLE, self.entryChanged)

	def keyGotAscii(self):
		self["config"].handleKey(ACTIONKEY_ASCII, self.entryChanged)

	def keyNumberGlobal(self, number):
		self["config"].handleKey(ACTIONKEY_0 + number, self.entryChanged)

	def keySave(self):
		for notifier in self.onSave:
			notifier()
		quitData = self.saveAll()
		if quitData:
			self.session.openWithCallback(boundFunction(self.restartConfirm, quitData[0]), MessageBox, quitData[1], default=True, type=MessageBox.TYPE_YESNO)
		else:
			self.close()

	def restartConfirm(self, quitValue, result):
		if result:
			self.session.open(TryQuitMainloop, retvalue=quitValue)
			self.close()

	def saveAll(self):
		quitData = ()
		for item in self["config"].list:
			if len(item) > 1:
				if item[1].isChanged():
					itemText = item[0][0] if isinstance(item[0], tuple) else item[0]
					if itemText.endswith("*"):
						quitData = (QUIT_RESTART, _("Restart GUI now?"))
					elif itemText.endswith("#"):
						quitData = (QUIT_REBOOT, _("Reboot %s %s now?") % getBoxDisplayName())
				item[1].save()
		configfile.save()
		return quitData

	def addSaveNotifier(self, notifier):
		if callable(notifier):
			self.onSave.append(notifier)
		else:
			raise TypeError("[ConfigList] Error: Notifier must be callable!")

	def removeSaveNotifier(self, notifier):
		while notifier in self.onSave:
			self.onSave.remove(notifier)

	def clearSaveNotifiers(self):
		self.onSave = []

	def keyCancel(self):
		self.closeConfigList(())

	def closeRecursive(self):
		self.closeConfigList((True,))

	def closeConfigList(self, closeParameters=()):
		if self["config"].isChanged():
			self.closeParameters = closeParameters
			self.session.openWithCallback(self.cancelConfirm, MessageBox, self.cancelMsg, default=False, type=MessageBox.TYPE_YESNO)
		else:
			self.close(*closeParameters)

	def cancelConfirm(self, result):
		if not result:
			return
		for item in self["config"].list:
			if len(item) > 1:
				item[1].cancel()
		if not hasattr(self, "closeParameters"):
			self.closeParameters = ()
		self.close(*self.closeParameters)

	def createSummary(self):  # This should not be required if ConfigList is invoked via Setup (as it should).
		from Screens.Setup import SetupSummary
		return SetupSummary

	def run(self):  # Allow ConfigList based screens to be processed from the Wizard.
		self.keySave()

	def dummyConfigActions(self, value):  # Temporary support for legacy code and plugins that hasn't yet been updated.
		self["configActions"].setEnabled(value)
		self["navigationActions"].setEnabled(value)
		self["menuConfigActions"].setEnabled(value)
		self["charConfigActions"].setEnabled(value)
		self["editConfigActions"].setEnabled(value)

	def dummyVKBActions(self, value):  # Temporary support for legacy code and plugins that hasn't yet been updated.
		self["virtualKeyBoardActions"].setEnabled(value)


class DummyActions:  # Temporary support for legacy code and plugins that hasn't yet been updated.
	def setEnabled(self, enabled):
		pass

	def destroy(self):
		pass

	def execBegin(self):
		pass

	def execEnd(self):
		pass
