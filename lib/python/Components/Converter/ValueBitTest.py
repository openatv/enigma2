from Components.Element import cached
from Components.Converter.Converter import Converter


class ValueBitTest(Converter):
	def __init__(self, token):
		Converter.__init__(self, token)
		self.value = int(token)

	@cached
	def getBoolean(self):
		return bool(self.source.value & self.value)

	boolean = property(getBoolean)
