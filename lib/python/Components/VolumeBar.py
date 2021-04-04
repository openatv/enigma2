from __future__ import absolute_import
from Components.HTMLComponent import HTMLComponent
from Components.GUIComponent import GUIComponent
from Components.VariableValue import VariableValue

from enigma import eSlider


class VolumeBar(VariableValue, HTMLComponent, GUIComponent):
	def __init__(self):
		VariableValue.__init__(self)
		GUIComponent.__init__(self)

	GUI_WIDGET = eSlider

	def postWidgetCreate(self, instance):
		instance.setRange(0, 100)
