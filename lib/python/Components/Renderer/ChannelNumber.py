from Components.VariableText import VariableText
from enigma import eLabel, iServiceInformation, eServiceReference, eServiceCenter
from Renderer import Renderer

#
# borrowed from vali, adapted for openpli
#
class ChannelNumber(Renderer, VariableText):
	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)
		self.list = []
		self.getList()

	GUI_WIDGET = eLabel

	def changed(self, what):
		service = self.source.service
		info = service and service.info()
		if info is None:
			self.text = ""
			return

		serviceref = info.getInfoString(iServiceInformation.sServiceref)
		if serviceref in self.list:
			for idx in range(1, len(self.list)):
				if serviceref == self.list[idx-1]:
					self.text = str(idx)
					break
		else:
			self.text = '---'

	def getList(self):
		serviceHandler = eServiceCenter.getInstance()
		services = serviceHandler.list(eServiceReference('1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 195) || (type == 25) FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
		bouquets = services and services.getContent("SN", True)
		for bouquet in bouquets:
			services = serviceHandler.list(eServiceReference(bouquet[0]))
			channels = services and services.getContent("SN", True)
			for channel in channels:
				if not channel[0].startswith("1:64:"):
					self.list.append(channel[0])
