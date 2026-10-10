from Components.Converter.Converter import Converter
from Components.Element import cached


class ValueBitTest(Converter):
	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.value = int(tokens)

	@cached
	def getBoolean(self):
		return bool(self.source.value & self.value)

	boolean = property(getBoolean)
