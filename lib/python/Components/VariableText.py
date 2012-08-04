class VariableText(object):
	"""VariableText can be used for components which have a variable text, based on any widget with setText call"""

	def __init__(self):
		object.__init__(self)
		self.message = ""
		self.instance = None

	def setText(self, text):
		self.message = text
		if self.instance:
			self.instance.setText(self.message or "")

	def setMarkedPos(self, pos):
		if self.instance:
			self.instance.setMarkedPos(int(pos))

	def getText(self):
		return self.message

	text = property(getText, setText)

	def postWidgetCreate(self, instance):
		instance.setText(self.message or "")
