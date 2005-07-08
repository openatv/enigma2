from HTMLComponent import *
from GUIComponent import *

from enigma import eListboxPythonStringContent, eListbox

class MenuList(HTMLComponent, GUIComponent):
	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonStringContent()
		self.l.setList(list)
	
	def getCurrent(self):
		return self.l.getCurrentSelection()
	
	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
	
	def GUIdelete(self):
		self.instance.setContent(None)
		self.instance = None


