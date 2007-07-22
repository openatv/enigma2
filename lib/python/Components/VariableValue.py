class VariableValue(object):
	"""VariableValue can be used for components which have a variable value (like eSlider), based on any widget with setValue call"""
	
	def __init__(self):
		self.__value = 0

	def setValue(self, value):
		self.__value = value
		if self.instance:
			self.instance.setValue(self.__value)

	def getValue(self):
		return self.__value

	def postWidgetCreate(self, instance):
		print self
		print self.GUI_WIDGET
		self.instance.setValue(self.__value)

	value = property(getValue, setValue)
