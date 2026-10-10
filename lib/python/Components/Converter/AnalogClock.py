# Original code is from openmips gb Team: [OMaclock] Converter.
# Thx to arn354.

from time import localtime
from Components.Converter.Converter import Converter
from Components.Element import cached


class AnalogClock(Converter):
	DEFAULT = 0
	OMA_SEC = 1
	OMA_MIN = 2
	OMA_HOUR = 3

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.type = {
			"Hours": self.OMA_HOUR,
			"Minutes": self.OMA_MIN,
			"Seconds": self.OMA_SEC
		}.get(tokens, self.DEFAULT)

	@cached
	def getText(self):
		text = ""
		sourceTime = self.source.time
		if sourceTime is not None:
			timeStruct = localtime(sourceTime)
			match self.type:
				case self.OMA_HOUR:
					hour = (timeStruct.tm_hour * 5) + int((timeStruct.tm_min / 12))
					text = f"{hour:02d},hour"
				case self.OMA_MIN:
					text = f"{timeStruct.tm_min:02d},min"
				case self.OMA_SEC:
					text = f"{timeStruct.tm_sec:02d},sec"
				case _:
					text = "???"
		return text

	text = property(getText)
