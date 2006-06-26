from Converter import Converter

class ConditionalShowHide(Converter, object):

	def __init__(self, type, *args, **kwargs):
		Converter.__init__(self)
		self.invert = type == "Invert"

	def changed(self):
		for x in self.downstream_elements:
			x.visible = self.source.boolean
