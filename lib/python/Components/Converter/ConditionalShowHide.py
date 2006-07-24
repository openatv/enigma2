from Converter import Converter

class ConditionalShowHide(Converter, object):

	def __init__(self, type):
		Converter.__init__(self, type)
		self.invert = type == "Invert"

	def changed(self):
		for x in self.downstream_elements:
			x.visible = self.source.boolean
