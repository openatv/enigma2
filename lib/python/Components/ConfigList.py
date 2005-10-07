from HTMLComponent import *
from GUIComponent import *
from config import *

from enigma import eListbox, eListboxPythonConfigContent

class ConfigList(HTMLComponent, GUIComponent):
	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonConfigContent()
		self.l.setList(list)
		self.l.setSeperation(100)
		self.list = list
	
	def toggle(self):
		selection = self.getCurrent()
		selection[1].toggle()
		self.invalidateCurrent()

	def handleKey(self, key):
		selection = self.getCurrent()
		selection[1].handleKey(key)
		self.invalidateCurrent()

	def getCurrent(self):
		return self.l.getCurrentSelection()
	
	def invalidateCurrent(self):
		self.l.invalidateEntry(self.l.getCurrentSelectionIndex())

	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
	
	def GUIdelete(self):
		self.instance.setContent(None)
		self.instance = None

