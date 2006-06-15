from Components.VariableValue import VariableValue
from Components.GUIComponent import GUIComponent

from enigma import eSlider

class Progress(VariableValue, GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		VariableValue.__init__(self)
		self.__start = 0
		self.__end = 100

	GUI_WIDGET = eSlider

	def connect(self, source):
		source.changed.listen(self.changed)
		self.source = source
		self.changed()

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
