from Components.Converter.Converter import Converter
from Components.Element import cached


class TextCase(Converter):
	"""Converts a StaticText into upper/lower case."""
	UPPER = 0
	LOWER = 1

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.type = self.LOWER if tokens == "ToLower" else self.UPPER

	@cached
	def getText(self):
		text = self.source.getText()
		match self.type:
			case self.LOWER:
				text = text.lower()
			case self.UPPER:
				text = text.upper()
		return text

	text = property(getText)
