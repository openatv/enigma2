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

	def changed(self, what):
		if what[0] == self.CHANGED_CLEAR:
			(self.range, self.value) = ((0, 1), 0)
			return

		range = self.source.range or 100
		value = self.source.value
		if value is None:
			value = 0
		(self.range, self.value) = ((0, range), value)

	def postWidgetCreate(self, instance):
		instance.setRange(self.__start, self.__end)

	def setRange(self, range):
		(self.__start, self.__end) = range
		if self.instance is not None:
			self.instance.setRange(self.__start, self.__end)

	def getRange(self):
		return (self.__start, self.__end)

	range = property(getRange, setRange)
