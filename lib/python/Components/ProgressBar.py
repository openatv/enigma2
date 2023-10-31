from enigma import eSlider
from Components.GUIComponent import GUIComponent
from Components.VariableValue import VariableValue


class ProgressBar(VariableValue, GUIComponent):  # A general purpose progress bar

	def __init__(self):
		GUIComponent.__init__(self)
		VariableValue.__init__(self)
		self.__range = (0, 100)

	GUI_WIDGET = eSlider

	def postWidgetCreate(self, instance):
		instance.setRange(*self.__range)

	def setRange(self, range):
		self.__range = range
		if self.instance is not None:
			self.instance.setRange(*self.__range)

	def getRange(self):
		return self.__range

	range = property(getRange, setRange)
