from HTMLComponent import *
from GUIComponent import *
from VariableValue import *
from VariableText import *

from enigma import eSlider
from enigma import eLabel

class VolumeBar(VariableValue, HTMLComponent, GUIComponent):
	def __init__(self):
		VariableValue.__init__(self)
		GUIComponent.__init__(self)

	GUI_WIDGET = eSlider

	def postWidgetCreate(self, instance):
		instance.setRange(0, 100)
