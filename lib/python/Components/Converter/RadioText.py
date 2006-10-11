from Components.Converter.Converter import Converter
from Components.Element import cached

class RadioText(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = type

	@cached
	def getText(self):
		rt = self.source.radiotext
		text = ""
		if rt:
			if self.type == "RadioText":
				text = rt.getRadioText()
		return text.decode("latin-1").encode("utf-8")
	text = property(getText)
