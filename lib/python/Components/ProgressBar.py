from HTMLComponent import *
from GUIComponent import *
from VariableValue import *

from enigma import eSlider

# a general purpose progress bar
class ProgressBar(HTMLComponent, GUIComponent, VariableValue):
	def __init__(self):
		GUIComponent.__init__(self)
		VariableValue.__init__(self)

	def createWidget(self, parent):
		g = eSlider(parent)
		g.setRange(0, 100)
		return g
	
