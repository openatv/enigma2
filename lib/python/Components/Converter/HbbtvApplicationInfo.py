from Components.Converter.Converter import Converter
from Components.Element import cached


class HbbtvApplicationInfo(Converter):
	NAME = 0

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = ""
		if type == "Name":
			self.type = self.NAME

	@cached
	def getText(self):
		return self.source.name if self.type == self.NAME else ""

	text = property(getText)
