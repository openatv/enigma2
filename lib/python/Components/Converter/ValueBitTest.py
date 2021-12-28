from Components.Converter.Converter import Converter
from Components.Element import cached


class ValueBitTest(Converter):
	def __init__(self, arg):
		Converter.__init__(self, arg)
		self.value = int(arg)

	@cached
	def getBoolean(self):
		return self.source.value & self.value and True or False

	boolean = property(getBoolean)
