from enigma import eSlider
from Components.Renderer.Renderer import Renderer
from Components.VariableValue import VariableValue


class Progress(VariableValue, Renderer):
	GUI_WIDGET = eSlider

	def __init__(self):
		Renderer.__init__(self)
		VariableValue.__init__(self)
		self.__range = (0, 100)

	def changed(self, what):
		if what[0] == self.CHANGED_CLEAR:
			(self.range, self.value) = ((0, 1), 0)
			return

		range = self.source.range or 100
		value = self.source.value
		if value is None:
			value = 0
		if range > 2**31 - 1:
			range = 2**31 - 1
		if value > range:
			value = range
		if value < 0:
			value = 0
		(self.range, self.value) = ((0, range), value)

	def postWidgetCreate(self, instance):
		instance.setRange(*self.__range)

	def setRange(self, range):
		self.__range = range
		if self.instance is not None:
			self.instance.setRange(*self.__range)

	def getRange(self):
		return self.__range

	range = property(getRange, setRange)
