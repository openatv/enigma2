from Components.VariableValue import VariableValue
from Renderer import Renderer

from enigma import eSlider

class Progress(VariableValue, Renderer):
	def __init__(self):
		Renderer.__init__(self)
		VariableValue.__init__(self)
		self.__start = 0
		self.__end = 100

	GUI_WIDGET = eSlider

	def changed(self):
		range = self.source.range or 100
		value = self.source.value
		if value is None:
			value = 0
		(self.range, self.value) = ((0, range), value)

	GUI_WIDGET = eSlider

	def postWidgetCreate(self, instance):
		instance.setRange(self.__start, self.__end)

	def setRange(self, range):
		(__start, __end) = range
		if self.instance is not None:
			self.instance.setRange(__start, __end)

	def getRange(self):
		return (self.__start, self.__end)

	range = property(getRange, setRange)
