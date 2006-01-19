import skin

class VariableText:
	"""VariableText can be used for components which have a variable text, based on any widget with setText call"""
	
	def __init__(self):
		self.message = ""
		self.instance = None
	
	def setText(self, text):
		self.message = text
		if self.instance:
			self.instance.setText(self.message)

	def setMarkedPos(self, pos):
		if self.instance:
			self.instance.setMarkedPos(int(pos))

	def getText(self):
		return self.message
	
	def GUIcreate(self, parent):
		self.instance = self.createWidget(parent)
		self.instance.setText(self.message)
	
	def GUIdelete(self):
		self.removeWidget(self.instance)
		self.instance = None
	
	def removeWidget(self, instance):
		pass

