from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Sources.TunerInfo import TunerInfo as TunerInfoSource


class TunerInfo(Converter):
	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.type = {
			"TunerAvailable": TunerInfoSource.TUNER_AVAILABLE,
			"TunerUseMask": TunerInfoSource.FE_USE_MASK
		}[tokens]

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] == self.type:
			Converter.changed(self, what)

	@cached
	def getBoolean(self):
		return bool(self.source.getTunerUseMask()) if self.type == TunerInfoSource.FE_USE_MASK else None

	boolean = property(getBoolean)

	@cached
	def getText(self):
		return str(self.source.getTunerUseMask()) if self.type == TunerInfoSource.FE_USE_MASK else ""

	text = property(getText)

	@cached
	def getValue(self):
		match self.type:
			case TunerInfoSource.FE_USE_MASK:
				value = self.source.getTunerUseMask()
			case TunerInfoSource.TUNER_AVAILABLE:
				value = self.source.getTunerAmount()
			case _:
				value = -1
		return value

	value = property(getValue)
