# Movie Selection:
#<widget source="Service" render="Picon" position="1120,95" zPosition="14" size="100,60" transparent="12" alphatest="blend">
#	<convert type="MovieReference"/>
#</widget>
# Movie Player Infobar:
#<widget source="session.CurrentService" render="Picon" position="1120,95" zPosition="14" size="100,60" transparent="12" alphatest="blend">
#	<convert type="MovieReference"/>
#</widget>


from Components.Converter.Converter import Converter
from Components.Element import cached
from enigma import iServiceInformation, eServiceReference, iPlayableServicePtr


class MovieReference(Converter, object):

	def __init__(self, type):
		Converter.__init__(self, type)

	@cached
	def getText(self):
		service = self.source.service
		if isinstance(service, eServiceReference):
			info = self.source.info
		elif isinstance(service, iPlayableServicePtr):
			info = service.info()
			service = None
		else:
			info = None
		if info is None:
			return ""

		if service is None:
			refstr = info.getInfoString(iServiceInformation.sServiceref)
			path = refstr and eServiceReference(refstr).getPath()
			if path:
				try:
					fd = open("%s.meta" % (path), "r")
					refstr = fd.readline().strip()
					fd.close()
				except:
					pass
			return refstr
		else:
			return info.getInfoString(service, iServiceInformation.sServiceref)

	text = property(getText)
