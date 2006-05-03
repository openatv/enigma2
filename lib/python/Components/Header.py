from HTMLComponent import *
from GUIComponent import *
from VariableText import *

from enigma import eLabel

class Header(VariableText, HTMLComponent, GUIComponent):

	def __init__(self, message):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.setText(message)
	
	def produceHTML(self):
		return "<h2>" + self.getText() + "</h2>\n"

	GUI_WIDGET = eLabel
