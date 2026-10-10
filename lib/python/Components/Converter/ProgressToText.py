from Components.Converter.Converter import Converter
from Components.Element import cached


class ProgressToText(Converter):
	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.in_percent = "InPercent" in tokens.split(",")

	@cached
	def getText(self):
		sourceRange = self.source.range
		sourceValue = self.source.value
		if self.in_percent:
			text = f"{int(sourceValue * 100 / sourceRange)} %" if sourceRange else None
		else:
			text = f"{int(sourceValue)} / {int(sourceRange)}"
		return text

	text = property(getText)
