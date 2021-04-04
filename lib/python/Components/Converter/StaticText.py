from Components.Converter.Converter import Converter


class StaticText(Converter, object):
	def __init__(self, text):
		Converter.__init__(self, type)
		self.text = str(text)
