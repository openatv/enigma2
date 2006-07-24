from Converter import Converter

class ValueRange(Converter, object):
	def __init__(self, arg):
		Converter.__init__(self, arg)
		(self.lower, self.upper) = [int(x) for x in arg.split(',')]

	def getBoolean(self):
		if self.lower < self.upper:
			return self.lower < self.source.value < self.upper
		else:
			return not (self.upper < self.source.value < self.lower)

	boolean = property(getBoolean)
