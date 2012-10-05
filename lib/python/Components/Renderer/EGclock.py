from Components.VariableValue import VariableValue
from Renderer import Renderer

from enigma import eGauge

class EGclock(VariableValue, Renderer):
	def __init__(self):
		Renderer.__init__(self)
		VariableValue.__init__(self)

	GUI_WIDGET = eGauge

	def changed(self, what):
		if what[0] == self.CHANGED_CLEAR:
			return

		value = self.source.value
		if value is None:
			value = 0
		self.setValue(value)
		
	GUI_WIDGET = eGauge
	
	def postWidgetCreate(self, instance):
		instance.setValue(0)

	
	def setValue(self, value):
		#self.instance.setValue(5)
		if self.instance is not None:
			self.instance.setValue(value)


	#value = property(setValue)
