from HTMLComponent import *
from GUIComponent import *
from config import *

from enigma import eListbox, eListboxPythonConfigContent

class ConfigList(HTMLComponent, GUIComponent, object):
	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonConfigContent()
		self.l.setSeperation(100)
		self.list = list
		self.onSelectionChanged = [ ]
	
	def toggle(self):
		selection = self.getCurrent()
		selection[1].toggle()
		self.invalidateCurrent()

	def handleKey(self, key):
		selection = self.getCurrent()
		if selection[1].parent.enabled:
			selection[1].handleKey(key)
			self.invalidateCurrent()

	def getCurrent(self):
		return self.l.getCurrentSelection()
	
	def invalidateCurrent(self):
		self.l.invalidateEntry(self.l.getCurrentSelectionIndex())
		
	def invalidate(self, entry):
		i = 0
		for x in self.__list:
			if (entry.getConfigPath() == x[1].parent.getConfigPath()):
				self.l.invalidateEntry(i)
			i += 1

	GUI_WIDGET = eListbox
	
	def selectionChanged(self):
		for x in self.onSelectionChanged:
			x()

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
	
	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.selectionChanged)
	
	def setList(self, list):
		self.__list = list
		self.l.setList(self.__list)

	def getList(self):
		return self.__list

	list = property(getList, setList)
