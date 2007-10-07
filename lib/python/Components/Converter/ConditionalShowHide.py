from Converter import Converter

class ConditionalShowHide(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.invert = type == "Invert"

	def calcVisibility(self):
		b = self.source.boolean
		if b is None:
			return True
		b ^= self.invert
		return b

	def changed(self, what):
		vis = self.calcVisibility()
		for x in self.downstream_elements:
			x.visible = vis

	def connectDownstream(self, downstream):
		Converter.connectDownstream(self, downstream)
		downstream.visible = self.calcVisibility()
