from HTMLComponent import *
from GUIComponent import *
from VariableValue import *
from VariableText import *

from enigma import eSlider

class Slider(VariableValue, HTMLComponent, GUIComponent):
	def __init__(self, min, max):
		VariableValue.__init__(self)
		GUIComponent.__init__(self)
		
		self.min = min
		self.max = max

	def createWidget(self, parent):
		g = eSlider(parent)
		g.setRange(self.min, self.max)
		return g
