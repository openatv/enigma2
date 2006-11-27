from HTMLComponent import *
from GUIComponent import *
from config import KEY_LEFT, KEY_RIGHT, KEY_0, KEY_DELETE, KEY_OK, KEY_TIMEOUT, ConfigElement
from Components.ActionMap import NumberActionMap
from enigma import eListbox, eListboxPythonConfigContent, eTimer
from Screens.MessageBox import MessageBox

class ConfigList(HTMLComponent, GUIComponent, object):
	def __init__(self, list, session = None):
		GUIComponent.__init__(self)
		self.l = eListboxPythonConfigContent()
		self.l.setSeperation(100)
		self.timer = eTimer()
		self.list = list
		self.onSelectionChanged = [ ]
		self.current = None
		self.help_window = None
		self.setHelpWindowSession(session)

	def execBegin(self):
		self.timer.timeout.get().append(self.timeout)

	def execEnd(self):
		self.timer.timeout.get().remove(self.timeout)

	def setHelpWindowSession(self, session):
		assert self.help_window is None, "you can't move a help window to another session"
		self.session = session

	def toggle(self):
		selection = self.getCurrent()
		selection[1].toggle()
		self.invalidateCurrent()

	def handleKey(self, key):
		selection = self.getCurrent()
		if selection and selection[1].enabled:
			selection[1].handleKey(key)
			self.invalidateCurrent()
			if self.help_window:
				self.help_window.update(selection[1])
			if key not in [KEY_TIMEOUT, KEY_LEFT, KEY_RIGHT, KEY_DELETE, KEY_OK]:
				self.timer.start(1000, 1)

	def getCurrent(self):
		return self.l.getCurrentSelection()
	
	def invalidateCurrent(self):
		self.l.invalidateEntry(self.l.getCurrentSelectionIndex())

	def invalidate(self, entry):
		# when the entry to invalidate does not exist, just ignore the request.
		# this eases up conditional setup screens a lot.
		if entry in self.__list:
			self.l.invalidateEntry(self.__list.index(entry))

	GUI_WIDGET = eListbox
	
	def selectionChanged(self):
		n = self.getCurrent()
		
		if self.help_window:
			self.session.deleteDialog(self.help_window)
		
		nh = n and n[1].helpWindow()
		if nh is not None and self.session is not None:
			self.help_window = self.session.instantiateDialog(*nh)
			self.help_window.show()

		self.current = n
		for x in self.onSelectionChanged:
			x()

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
	
	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.selectionChanged)
	
	def setList(self, l):
		self.timer.stop()
		self.__list = l
		self.l.setList(self.__list)

		if l is not None:
			for x in l:
				assert isinstance(x[1], ConfigElement), "entry in ConfigList " + str(x[1]) + " must be a ConfigElement"

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

class ConfigListScreen:
	def __init__(self, list, session = None, on_change = None):
		self["config_actions"] = NumberActionMap(["SetupActions", "TextInputActions"],
		{
			"ok": self.keyOK,
			"left": self.keyLeft,
			"right": self.keyRight,
			"delete": self.keyDelete,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, -1) # to prevent left/right overriding the listbox
		
		self["config"] = ConfigList(list, session = session)
		if on_change is not None:
			self.__changed = on_change
		else:
			self.__changed = lambda: None

	def keyOK(self):
		self["config"].handleKey(KEY_OK)

	def keyLeft(self):
		self["config"].handleKey(KEY_LEFT)
		self.__changed()

	def keyRight(self):
		self["config"].handleKey(KEY_RIGHT)
		self.__changed()

	def keyDelete(self):
		self["config"].handleKey(KEY_DELETE)
		self.__changed()

	def keyNumberGlobal(self, number):
		self["config"].handleKey(KEY_0 + number)
		self.__changed()

	# keySave and keyCancel are just provided in case you need them.
	# you have to call them by yourself.
	def keySave(self):
		for x in self["config"].list:
			x[1].save()
		self.close()
	
	def cancelConfirm(self, result):
		if not result:
			return

		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()
