from Components.Converter.Converter import Converter
from Components.Element import cached

class RemainingToText(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)

	@cached
	def getText(self):
		r = self.source.time
		if r is None:
			return ""

		(duration, remaining) = self.source.time
		if remaining is not None:
			return "+%d min" % (remaining / 60)
		else:
			return "%d min" % (duration / 60)

	text = property(getText)
