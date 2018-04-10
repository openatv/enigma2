from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from config import KEY_LEFT, KEY_RIGHT, KEY_HOME, KEY_END, KEY_0, KEY_DELETE, KEY_BACKSPACE, KEY_OK, KEY_TOGGLEOW, KEY_ASCII, KEY_TIMEOUT, KEY_NUMBERS, config, configfile, ConfigElement, ConfigText, ConfigPassword
from Components.ActionMap import NumberActionMap, ActionMap
from enigma import eListbox, eListboxPythonConfigContent, eRCInput, eTimer, quitMainloop
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
import skin

class ConfigList(HTMLComponent, GUIComponent, object):
	def __init__(self, list, session = None):
		GUIComponent.__init__(self)
		self.l = eListboxPythonConfigContent()
		seperation, = skin.parameters.get("ConfigListSeperator", (350, ))
		self.l.setSeperation(seperation)
		height, space = skin.parameters.get("ConfigListSlider",(17, 0))
		self.l.setSlider(height, space)
		self.timer = eTimer()
		self.list = list
		self.onSelectionChanged = [ ]
		self.current = None
		self.session = session

	def execBegin(self):
		rcinput = eRCInput.getInstance()
		if not config.misc.remotecontrol_text_support.value:
			rcinput.setKeyboardMode(rcinput.kmAscii)
		else:
			rcinput.setKeyboardMode(rcinput.kmNone)
		self.timer.callback.append(self.timeout)

	def execEnd(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)
		self.timer.callback.remove(self.timeout)

	def toggle(self):
		selection = self.getCurrent()
		selection[1].toggle()
		self.invalidateCurrent()

	def handleKey(self, key):
		selection = self.getCurrent()
		if selection and selection[1].enabled:
			selection[1].handleKey(key)
			self.invalidateCurrent()
			if key in KEY_NUMBERS:
				self.timer.start(1000, 1)

	def getCurrent(self):
		return self.l.getCurrentSelection()

	def getCurrentIndex(self):
		return self.l.getCurrentSelectionIndex()

	def setCurrentIndex(self, index):
		if self.instance is not None:
			self.instance.moveSelectionTo(index)

	def invalidateCurrent(self):
		self.l.invalidateEntry(self.l.getCurrentSelectionIndex())

	def invalidate(self, entry):
		# when the entry to invalidate does not exist, just ignore the request.
		# this eases up conditional setup screens a lot.
		if entry in self.__list:
			self.l.invalidateEntry(self.__list.index(entry))

	GUI_WIDGET = eListbox

	def selectionChanged(self):
		if isinstance(self.current,tuple) and len(self.current) >= 2:
			self.current[1].onDeselect(self.session)
		self.current = self.getCurrent()
		if isinstance(self.current,tuple) and len(self.current) >= 2:
			self.current[1].onSelect(self.session)
		else:
			return
		for x in self.onSelectionChanged:
			x()

	def postWidgetCreate(self, instance):
		instance.selectionChanged.get().append(self.selectionChanged)
		instance.setContent(self.l)
		self.instance.setWrapAround(True)

	def preWidgetRemove(self, instance):
		if isinstance(self.current,tuple) and len(self.current) >= 2:
			self.current[1].onDeselect(self.session)
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)

	def setList(self, l):
		self.timer.stop()
		self.__list = l
		self.l.setList(self.__list)

		if l is not None:
			for x in l:
				assert len(x) < 2 or isinstance(x[1], ConfigElement), "entry in ConfigList " + str(x[1]) + " must be a ConfigElement"

	def getList(self):
		return self.__list

	list = property(getList, setList)

	def timeout(self):
		self.handleKey(KEY_TIMEOUT)

	def isChanged(self):
		is_changed = False
		for x in self.list:
			is_changed |= x[1].isChanged()

		return is_changed

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)

	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)

	def moveUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)

	def refresh(self):
		for x in self.onSelectionChanged:
			if x.__func__.__name__ == "selectionChanged":
				x()

class ConfigListScreen:
	def __init__(self, list, session = None, on_change = None):
		self["config_actions"] = NumberActionMap(["SetupActions", "InputAsciiActions", "KeyboardInputActions"],
		{
			"gotAsciiCode": self.keyGotAscii,
			"ok": self.keyOK,
			"left": self.keyLeft,
			"right": self.keyRight,
			"home": self.keyHome,
			"end": self.keyEnd,
			"deleteForward": self.keyDelete,
			"deleteBackward": self.keyBackspace,
			"toggleOverwrite": self.keyToggleOW,
			"pageUp": self.keyPageUp,
			"pageDown": self.keyPageDown,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal,
			"file" : self.keyFile
		}, -1) # to prevent left/right overriding the listbox

		self.onChangedEntry = []

		self["VirtualKB"] = ActionMap(["VirtualKeyboardActions"],
		{
			"showVirtualKeyboard": self.KeyText,
		}, -2)
		self["VirtualKB"].setEnabled(False)

		self["config"] = ConfigList(list, session = session)

		if on_change is not None:
			self.__changed = on_change
		else:
			self.__changed = lambda: None

		if not self.handleInputHelpers in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.handleInputHelpers)

	def createSummary(self):
		self.setup_title = self.getTitle()
		from Screens.Setup import SetupSummary
		return SetupSummary

	def getCurrentEntry(self):
		return self["config"].getCurrent() and self["config"].getCurrent()[0] or ""

	def getCurrentValue(self):
		return self["config"].getCurrent() and str(self["config"].getCurrent()[1].getText()) or ""

	def getCurrentDescription(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2] or ""

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def handleInputHelpers(self):
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

	def KeyText(self):
		from Screens.VirtualKeyBoard import VirtualKeyBoard
		self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title = self["config"].getCurrent()[0], text = self["config"].getCurrent()[1].value)

	def VirtualKeyBoardCallback(self, callback = None):
		if callback is not None and len(callback):
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidate(self["config"].getCurrent())

	def keyOK(self):
		self["config"].handleKey(KEY_OK)

	def keyLeft(self):
		self["config"].handleKey(KEY_LEFT)
		self.__changed()
		self["config"].refresh()

	def keyRight(self):
		self["config"].handleKey(KEY_RIGHT)
		self.__changed()
		self["config"].refresh()

	def keyHome(self):
		self["config"].handleKey(KEY_HOME)
		self.__changed()

	def keyEnd(self):
		self["config"].handleKey(KEY_END)
		self.__changed()

	def keyDelete(self):
		self["config"].handleKey(KEY_DELETE)
		self.__changed()

	def keyBackspace(self):
		self["config"].handleKey(KEY_BACKSPACE)
		self.__changed()

	def keyToggleOW(self):
		self["config"].handleKey(KEY_TOGGLEOW)
		self.__changed()

	def keyGotAscii(self):
		self["config"].handleKey(KEY_ASCII)
		self.__changed()

	def keyNumberGlobal(self, number):
		self["config"].handleKey(KEY_0 + number)
		self.__changed()

	def keyPageDown(self):
		self["config"].pageDown()

	def keyPageUp(self):
		self["config"].pageUp()

	def keyFile(self):
		selection = self["config"].getCurrent()
		if selection and selection[1].enabled and hasattr(selection[1], "description"):
			self.session.openWithCallback(self.handleKeyFileCallback, ChoiceBox, selection[0],
				list=zip(selection[1].description, selection[1].choices),
				selection=selection[1].choices.index(selection[1].value),
				keys=[])

	def handleKeyFileCallback(self, answer):
		if answer:
			self["config"].getCurrent()[1].value = answer[1]
			self["config"].invalidateCurrent()
			self.__changed()

	def saveAll(self):
		restartgui = False
		for x in self["config"].list:
			if x[1].isChanged():
				if x[0] == _('Show on Display'): 
					restartgui = True
			x[1].save()
		configfile.save()	
		self.doRestartGui(restartgui)
			
	def doRestartGui(self, restart):
		if restart:
			self.session.openWithCallback(self.ExecuteRestart, MessageBox, _("Restart GUI now?"), MessageBox.TYPE_YESNO)

	def ExecuteRestart(self, result):
		if result:
			quitMainloop(3)

	# keySave and keyCancel are just provided in case you need them.
	# you have to call them by yourself.
	def keySave(self):
		self.saveAll()
		self.close()

	def cancelConfirm(self, result):
		if not result:
			if self.help_window_was_shown:
				self["config"].getCurrent()[1].help_window.show()
			return

		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def closeMenuList(self, recursive = False):
		self.help_window_was_shown = False
		try:
			self.HideHelp()
		except:
			pass
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), default = False)
		else:
			try:
				self.close(recursive)
			except:
				self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))

	def keyCancel(self):
		self.closeMenuList()
	
	def closeRecursive(self):
		self.closeMenuList(True)
