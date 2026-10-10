from Components.Converter.Converter import Converter
from Components.Element import cached


class ValueRange(Converter):
	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		(self.lower, self.upper) = (int(x) for x in tokens.split(","))

	@cached
	def getBoolean(self):
		try:
			sourceValue = int(self.source.value)
		except Exception:
			sourceValue = self.source.value
		return self.lower <= sourceValue <= self.upper if self.lower <= self.upper else not (self.upper < sourceValue < self.lower)

	boolean = property(getBoolean)
