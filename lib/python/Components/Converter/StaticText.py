from Components.Converter.Converter import Converter

class StaticText(Converter, object):
	def __init__(self, text, *args, **kwargs):
		Converter.__init__(self)
		self.text = str(text)

