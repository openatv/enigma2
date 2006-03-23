from HTMLComponent import *
from GUIComponent import *

from enigma import eListboxPythonStringContent, eListbox

class MenuList(HTMLComponent, GUIComponent):
	def __init__(self, list):
		GUIComponent.__init__(self)
		self.list = list
		self.l = eListboxPythonStringContent()
		self.l.setList(self.list)
		self.onSelectionChanged = [ ]
	
	def getCurrent(self):
		return self.l.getCurrentSelection()
	
	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
		self.instance.selectionChanged.get().append(self.selectionChanged)
	
	def GUIdelete(self):
		self.instance.setContent(None)
		self.instance = None

	def selectionChanged(self):
		for f in self.onSelectionChanged:
			f()

	def setList(self, list):
		self.list = list
		self.l.setList(self.list)

	def moveToIndex(self, idx):
		self.instance.moveSelectionTo(idx)

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)
		
	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)
			
	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)
		
	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)
			
	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)