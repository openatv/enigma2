from enigma import iPlayableService, iPlayableServicePtr, iServiceInformation

from Components.Converter.Converter import Converter
from Components.Element import cached


class VServiceOrbitalPosition(Converter):
	FULL = 0
	SHORT = 1

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.type = self.SHORT if tokens == "Short" else self.FULL

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] == iPlayableService.evStart:
			Converter.changed(self, what)

	@cached
	def getText(self):
		text = ""
		service = self.source.service
		if isinstance(service, iPlayableServicePtr):
			info = service and service.info()
			ref = None
		else:  # Reference.
			info = service and self.source.info
			ref = service
		if info is not None:
			transponderInfo = info.getInfoObject(ref, iServiceInformation.sTransponderData) if ref else info.getInfoObject(iServiceInformation.sTransponderData)
			if transponderInfo and "orbital_position" in transponderInfo:
				position = int(transponderInfo["orbital_position"])
				direction = "E"
				if position > 1800:
					position = 3600 - position
					direction = "W"
				text = f"{position // 10}.{position % 10}{direction}" if self.type == self.SHORT else f"{position // 10}.{position % 10} ° {direction}"
		return text

	text = property(getText)
