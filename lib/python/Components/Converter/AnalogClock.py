# original code is from openmips gb Team: [OMaclock] Converter #
# Thx to arn354 #

from time import localtime
from Components.Converter.Converter import Converter
from Components.Element import cached


class AnalogClock(Converter):
	DEFAULT = 0
	OMA_SEC = 1
	OMA_MIN = 2
	OMA_HOUR = 3

	def __init__(self, type):
		Converter.__init__(self, type)

		self.type = {
			"Seconds": self.OMA_SEC,
			"Minutes": self.OMA_MIN,
			"Hours": self.OMA_HOUR
		}.get(type, self.DEFAULT)

	@cached
	def getText(self):
		time = self.source.time
		if time is None:
			return ""

		t = localtime(time)

		if self.type == self.OMA_SEC:
			return f"{t.tm_sec:02d},sec"
		elif self.type == self.OMA_MIN:
			return f"{t.tm_min:02d},min"
		elif self.type == self.OMA_HOUR:
			hour = (t.tm_hour * 5) + int((t.tm_min / 12))
			return f"{hour:02d},hour"
		else:
			return "???"

	text = property(getText)
