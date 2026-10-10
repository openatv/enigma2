from Components.Element import cached
from Components.Converter.Converter import Converter


class HbbtvApplicationInfo(Converter):
	NAME = 0

	def __init__(self, token):
		Converter.__init__(self, token)
		self.type = self.NAME if token == "Name" else ""

	@cached
	def getText(self):
		return self.source.name if self.type == self.NAME else ""

	text = property(getText)
