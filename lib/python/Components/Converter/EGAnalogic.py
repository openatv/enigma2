# Shamelessly copied from BP Project.

from time import localtime
from Components.Converter.Converter import Converter
from Components.Element import cached


class EGAnalogic(Converter):
	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.type = {
			"Hours": 3,
			"Minutes": 2,
			"Seconds": 1
		}.get(tokens, -1)

	@cached
	def getValue(self):
		value = 0
		sourceTime = self.source.time
		if sourceTime is not None:
			timeStruct = localtime(sourceTime)
			match self.type:
				case 1:
					value = int((timeStruct.tm_sec * 100) / 60)
				case 2:
					value = int((timeStruct.tm_min * 100) / 60)
				case 3:
					value = int(((timeStruct.tm_hour * 100) / 12) + (timeStruct.tm_min / 8))
				case _:
					value = None
		return value

	value = property(getValue)
