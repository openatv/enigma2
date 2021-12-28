from Components.Converter.Converter import Converter
from Components.Element import cached


class ValueRange(Converter):
	def __init__(self, arg):
		Converter.__init__(self, arg)
		(self.lower, self.upper) = [int(x) for x in arg.split(',')]

	@cached
	def getBoolean(self):
		try:
			sourcevalue = int(self.source.value)
		except:
			sourcevalue = self.source.value
		if self.lower <= self.upper:
			return self.lower <= sourcevalue <= self.upper
		else:
			return not (self.upper < sourcevalue < self.lower)

	boolean = property(getBoolean)
