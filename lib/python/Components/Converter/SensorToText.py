from Components.Converter.Converter import Converter


class SensorToText(Converter):
	def __init__(self, arguments):
		Converter.__init__(self, arguments)

	def getText(self):
		if self.source.getValue() is None:
			return ""
		unit = self.source.getUnit()
		if unit in ('C', 'F'):
			return "%d%s%s" % (self.source.getValue(), u"\u00B0", unit)

	text = property(getText)
