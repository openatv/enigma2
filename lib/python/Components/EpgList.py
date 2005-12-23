from HTMLComponent import *
from GUIComponent import *

from enigma import *

class EPGList(HTMLComponent, GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxEPGContent()

	def getCurrent(self):
		evt = self.l.getCurrent()
		return evt

	def moveUp(self):
		self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)

	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)

	def GUIdelete(self):
		self.instance = None

	def setRoot(self, root):
		self.l.setRoot(root)
		self.l.sort()

#	def setMode(self, mode):
#		if mode == self.MODE_NORMAL:
#			self.instance.setItemHeight(20)
#			self.l.setVisualMode(eListboxServiceContent.visModeSimple)
#		else:
#			self.instance.setItemHeight(40)
#			self.l.setElementFont(self.l.celServiceName, gFont("Regular", 30))
#			self.l.setElementPosition(self.l.celServiceName, eRect(40, 0, self.instance.size().width(), 40))
#			self.l.setElementFont(self.l.celServiceNumber, gFont("Regular", 20))
#			self.l.setElementPosition(self.l.celServiceNumber, eRect(0, 10, 40, 30))
#
#			self.l.setVisualMode(eListboxServiceContent.visModeComplex)
