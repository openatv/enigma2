# Movie Selection:
# <widget source="Service" render="Picon" position="1120,95" zPosition="14" size="100,60" transparent="12" alphatest="blend">
# 	<convert type="MovieReference"/>
# </widget>
# Movie Player Infobar:
# <widget source="session.CurrentService" render="Picon" position="1120,95" zPosition="14" size="100,60" transparent="12" alphatest="blend">
# 	<convert type="MovieReference"/>
# </widget>

from enigma import eServiceReference, iPlayableServicePtr, iServiceInformation

from Components.Converter.Converter import Converter
from Components.Element import cached


class MovieReference(Converter):
	def __init__(self, tokens):
		Converter.__init__(self, tokens)

	@cached
	def getText(self):
		text = ""
		service = self.source.service
		if isinstance(service, eServiceReference):
			info = self.source.info
		elif isinstance(service, iPlayableServicePtr):
			info = service.info()
			service = None
		else:
			info = None
		if info is not None:
			if service is None:
				text = info.getInfoString(iServiceInformation.sServiceref)
				path = text and eServiceReference(text).getPath()
				if path:
					try:
						with open(f"{path}.meta") as fd:
							text = fd.readline().strip()
					except OSError:
						pass
			else:
				text = info.getInfoString(service, iServiceInformation.sServiceref)
		return text

	text = property(getText)
