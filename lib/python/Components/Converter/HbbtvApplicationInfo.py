from Components.Converter.Converter import Converter
from Components.Element import cached

class HbbtvApplicationInfo(Converter, object):
	NAME = 0

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = ""
		if type == "Name":
			self.type = self.NAME

	@cached
	def getText(self):
		if self.type == self.NAME:
			return self.source.name
		else:
			return ""

	text = property(getText)