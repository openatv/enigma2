from Components.Converter.Converter import Converter


class StaticText(Converter):
	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.text = str(tokens)
