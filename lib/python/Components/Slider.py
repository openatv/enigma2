from enigma import eSlider

from Components.GUIComponent import GUIComponent
from Components.VariableValue import VariableValue


class Slider(VariableValue, GUIComponent):
	def __init__(self, min, max):
		VariableValue.__init__(self)
		GUIComponent.__init__(self)

		self.min = min
		self.max = max

	GUI_WIDGET = eSlider

	def postWidgetCreate(self, instance):
		instance.setRange(self.min, self.max)
