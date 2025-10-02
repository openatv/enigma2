class VariableText:
	"""VariableText can be used for components which have a variable text, based on any widget with setText call"""

	def __init__(self):
		object.__init__(self)
		self.message = ""
		self.instance = None
		self.onChanged = []

	def setText(self, text):
		try:
			self.message = text
			if self.instance:
				self.instance.setText(self.message or "")
		except Exception:
			self.message = ""
			self.instance.setText(self.message or "")
		for method in self.onChanged:
			method()

	def setMarkedPos(self, pos):
		if self.instance:
			self.instance.setMarkedPos(int(pos))

	def getText(self):
		return self.message

	text = property(getText, setText)

	def postWidgetCreate(self, instance):
		try:
			instance.setText(self.message or "")
		except Exception:
			pass
