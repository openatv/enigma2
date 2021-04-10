from Converter import Converter
from Components.Element import cached


class TextCase(Converter):
	"""Converts a StaticText into upper/lower case."""
	UPPER = 0
	LOWER = 1

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = self.UPPER
		if type == "ToLower":
			self.type = self.LOWER
		elif type == "ToUpper":
			self.type = self.UPPER

	@cached
	def getText(self):
		originaltext = self.source.getText()
		if self.type == self.UPPER:
			return originaltext.decode('utf-8').upper().encode('utf-8')
		elif self.type == self.LOWER:
			return originaltext.decode('utf-8').lower().encode('utf-8')
		else:
			return originaltext

	text = property(getText)
