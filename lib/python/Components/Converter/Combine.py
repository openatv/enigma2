from Components.Converter.Converter import Converter
from Components.Element import cached


class Combine(Converter):
	SINGLE_SOURCE = False

	def __init__(self, tokens=None, func=None):
		Converter.__init__(self, tokens)
		assert func is not None
		self.func = func

	@cached
	def getValue(self):
		return self.func(self.sources)

	value = property(getValue)
