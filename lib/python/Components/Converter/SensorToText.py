from Components.Converter.Converter import Converter

class SensorToText(Converter, object):
	def __init__(self, arguments):
		Converter.__init__(self, arguments)

	def getText(self):
		if self.source.getValue() is None:
			return ""
		mark = " "
		unit = self.source.getUnit()
		if unit in ('C','F'):
			mark = str('\xc2\xb0')
		return "%d%s%s" % (self.source.getValue(), mark, unit)

	text = property(getText)
