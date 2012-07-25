from Components.VariableText import VariableText
from enigma import eLabel, eServiceCenter
from Renderer import Renderer
from Screens.InfoBar import InfoBar

class ChannelNumber(Renderer, VariableText):
	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)

	GUI_WIDGET = eLabel

	def changed(self, what):
		self.text=""
		service = self.source.service
		if service and service.info():
			serviceHandler = eServiceCenter.getInstance()
			CurrentServiceList = InfoBar.instance.servicelist
			root = CurrentServiceList.servicelist.getRoot()
			services = serviceHandler.list(root)
			channels = services and services.getContent("SN", True)
			channelIndex = CurrentServiceList.servicelist.l.lookupService(CurrentServiceList.servicelist.getCurrent())
			markersCounter = 0
			for i in range(channelIndex):
				if channels[i][0].startswith("1:64:"):
					markersCounter = markersCounter + 1
			self.text = str(CurrentServiceList.getBouquetNumOffset(root)+channelIndex+1-markersCounter)
			CurrentServiceList = None