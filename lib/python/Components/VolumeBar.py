from enigma import eSlider

from Components.GUIComponent import GUIComponent
from Components.VariableValue import VariableValue


class VolumeBar(VariableValue, GUIComponent):
	def __init__(self):
		VariableValue.__init__(self)
		GUIComponent.__init__(self)

	GUI_WIDGET = eSlider

	def postWidgetCreate(self, instance):
		instance.setRange(0, 100)
