from Components.Converter.Converter import Converter
from Components.Element import cached


class HbbtvApplicationInfo(Converter):
	NAME = 0

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.type = self.NAME if tokens == "Name" else ""

	@cached
	def getText(self):
		return self.source.name if self.type == self.NAME else ""

	text = property(getText)
