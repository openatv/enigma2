from Converter import Converter
from Components.Element import cached

class Combine(Converter, object):
	SINGLE_SOURCE = False

	def __init__(self, arg=None, func=None):
		Converter.__init__(self, arg)
		assert func is not None
		self.func = func

	@cached
	def getValue(self):
		return self.func(self.sources)

	value = property(getValue)
