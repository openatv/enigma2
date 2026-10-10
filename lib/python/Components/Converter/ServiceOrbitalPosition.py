from enigma import eServiceCenter, iPlayableService, iPlayableServicePtr, iServiceInformation

from Components.Converter.Converter import Converter
from Components.Element import cached
from ServiceReference import resolveAlternate


class ServiceOrbitalPosition(Converter):
	FULL = 0
	SHORT = 1

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.type = self.SHORT if tokens == "Short" else self.FULL

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart, iPlayableService.evEnd, iPlayableService.evUpdatedInfo):
			Converter.changed(self, what)

	@cached
	def getText(self):
		text = ""
		info = None
		ref = None
		service = self.source.service
		if isinstance(service, iPlayableServicePtr):
			if getattr(self.source, "isDVBI", False):
				text = "DVB-I"
			else:
				info = service and service.info()
		else:  # Reference.
			info = service and self.source.info
			ref = service
		if info:
			if ref:
				alternativeRef = resolveAlternate(ref)
				if alternativeRef:
					ref = alternativeRef
					info = eServiceCenter.getInstance().info(ref)
				transponderInfo = info.getInfoObject(ref, iServiceInformation.sTransponderData)
			else:
				transponderInfo = info.getInfoObject(iServiceInformation.sTransponderData)
			if transponderInfo:
				tunerType = transponderInfo["tuner_type"]
				if tunerType == "DVB-S":
					position = int(transponderInfo["orbital_position"])
					direction = "E"
					if position > 1800:
						position = 3600 - position
						direction = "W"
					text = f"{position // 10}.{position % 10}{direction}" if self.type == self.SHORT else f"{position // 10}.{position % 10}° {direction}"
				else:
					text = tunerType
			elif ref:
				refString = ref.toString().lower()
				if "%3a//" in refString:
					text = _("Stream")
				elif refString.startswith("1:134:"):
					text = _("Alternative")
		return text

	text = property(getText)
