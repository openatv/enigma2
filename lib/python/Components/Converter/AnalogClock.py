# original code is from openmips gb Team: [OMaclock] Converter #
# Thx to arn354 #

from Converter import Converter
from time import localtime, strftime
from Components.Element import cached


class AnalogClock(Converter, object):
	DEFAULT = 0
	OMA_SEC = 1
	OMA_MIN = 2
	OMA_HOUR = 3

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "Seconds":
			self.type = self.OMA_SEC
		elif type == "Minutes":
			self.type = self.OMA_MIN
		elif type == "Hours":
			self.type = self.OMA_HOUR
		else:
			self.type = self.DEFAULT

	@cached
	def getText(self):
		time = self.source.time
		if time is None:
			return ""

		t = localtime(time)

		if self.type == self.OMA_SEC:
			return "%02d,sec" % t.tm_sec
		elif self.type == self.OMA_MIN:
			return "%02d,min" % t.tm_min
		elif self.type == self.OMA_HOUR:
			ret = (t.tm_hour * 5) + (t.tm_min / 12)
			return "%02d,hour" % ret
		else:
			return "???"

	text = property(getText)
