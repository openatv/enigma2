from Converter import Converter
from Components.Element import cached

class ValueRange(Converter, object):
	def __init__(self, arg):
		Converter.__init__(self, arg)
		(self.lower, self.upper) = [int(x) for x in arg.split(',')]

	@cached
	def getBoolean(self):
		val = int(self.source.value)
		if self.lower <= self.upper:
			return self.lower <= val <= self.upper
		else:
			return not (self.upper < val < self.lower)

	boolean = property(getBoolean)
