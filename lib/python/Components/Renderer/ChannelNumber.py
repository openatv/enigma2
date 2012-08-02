from Components.VariableText import VariableText
from enigma import eLabel, eServiceCenter, iPlayableService
from Renderer import Renderer
from Screens.InfoBar import InfoBar

firstChannelNumberClass = True
text = ""

class ChannelNumber(Renderer, VariableText):
	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)
		self.text = "---"
		global firstChannelNumberClass
		self.firstChannelNumberClass  = firstChannelNumberClass
		firstChannelNumberClass  = False

	GUI_WIDGET = eLabel

	def changed(self, what):
		global text
		if what[0] != self.CHANGED_SPECIFIC:
			return
		if what[1] != iPlayableService.evStart:
			return
		if not self.firstChannelNumberClass:
			self.text = text
			return
		self.text = "---"
		service = self.source.service
		if service and service.info():
			CurrentServiceList = InfoBar.instance.servicelist
			root = CurrentServiceList.servicelist.getRoot()
			if 'userbouquet.' in root.toCompareString():
				services = eServiceCenter.getInstance().list(root)
				channels = services and services.getContent("SN", True)
				channelIndex = CurrentServiceList.servicelist.getCurrentIndex()
				markersCounter = 0
				for i in range(channelIndex):
					if channels[i][0].startswith("1:64:"):
						markersCounter = markersCounter + 1
				self.text = str(CurrentServiceList.getBouquetNumOffset(root)+channelIndex+1-markersCounter)
		text = self.text