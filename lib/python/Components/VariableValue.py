class VariableValue:
	"""VariableValue can be used for components which have a variable value (like eSlider), based on any widget with setValue call"""
	
	def __init__(self):
		self.value = 0
		self.instance = None
	
	def setValue(self, value):
		self.value = value
		if self.instance:
			self.instance.setValue(self.value)

	def getValue(self):
		return self.value
		
	def GUIcreate(self, parent, skindata):
		self.instance = self.createWidget(parent, skindata)
		self.instance.setValue(self.value)
	
	def GUIdelete(self):
		self.removeWidget(self.instance)
		self.instance = None
	
	def removeWidget(self, instance):
		pass
