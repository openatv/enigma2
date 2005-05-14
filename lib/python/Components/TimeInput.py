from HTMLComponent import *
from GUIComponent import *
from VariableText import *

from enigma import eInput, eInputContentNumber

class TimeInput(HTMLComponent, GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.content = eInputContentNumber(12, 0, 15)
	
	def GUIcreate(self, parent, skindata):
		self.instance = eInput(parent)
		self.instance.setContent(self.content)
	
	def GUIdelete(self):
		self.instance.setContent(None)
		self.instance = None
