from enigma import eGauge
from Components.Renderer.Renderer import Renderer
from Components.VariableValue import VariableValue


class EGclock(VariableValue, Renderer):
	GUI_WIDGET = eGauge

	def __init__(self):
		Renderer.__init__(self)
		VariableValue.__init__(self)

	def changed(self, what):
		if what[0] != self.CHANGED_CLEAR:
			value = self.source.value
			if value is None:
				value = 0
			self.setValue(value)

	GUI_WIDGET = eGauge

	def postWidgetCreate(self, instance):
		instance.setValue(0)

	def setValue(self, value):
		if self.instance is not None:
			self.instance.setValue(value)
