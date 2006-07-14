from Converter import Converter

class ValueRange(Converter, object):
	def __init__(self, arg, *args, **kwargs):
		Converter.__init__(self)
		(self.lower, self.upper) = [int(x) for x in arg.split(',')]

	def getBoolean(self):
		if self.lower < self.upper:
			return self.lower < self.source.value < self.upper
		else:
			return not (self.upper < self.source.value < self.lower)

	boolean = property(getBoolean)
