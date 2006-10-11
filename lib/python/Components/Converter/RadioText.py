from Components.Converter.Converter import Converter
from Components.Element import cached

class RadioText(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = type

	@cached
	def getText(self):
		rt = self.source.radiotext
		if rt is None:
			return ""
		text = rt.getRadioText()
		if self.type == "RadioText-UTF8":
			return text.decode("latin-1").encode("utf-8")
		else:
			return text
	text = property(getText)
