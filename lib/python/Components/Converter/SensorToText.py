from Components.Converter.Converter import Converter


class SensorToText(Converter):
	def __init__(self, tokens):
		Converter.__init__(self, tokens)

	def getText(self):
		text = None
		value = self.source.getValue()
		if value is None:
			text = ""
		else:
			unit = self.source.getUnit()
			if unit in ("C", "F"):
				text = f"{int(value)}°{unit}"
		return text

	text = property(getText)
