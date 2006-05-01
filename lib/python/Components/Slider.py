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

	GUI_WIDGET = eSlider
	
	def postWidgetCreate(self, instance):
		instance.setRange(self.min, self.max)
