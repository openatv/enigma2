from Components.Converter.Converter import Converter
from Components.Element import cached

class RadioText(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)

	@cached
	def getText(self):
		rt = self.source.radiotext
		if rt is None:
			return "N/A"
		return rt

	text = property(getText)
