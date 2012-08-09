from Components.VariableText import VariableText
from enigma import eLabel, iPlayableService
from Renderer import Renderer
from Screens.InfoBar import InfoBar

class ChannelNumber(Renderer, VariableText):
	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)
		self.text = "---"
	GUI_WIDGET = eLabel

	def changed(self, what):
		global text
		if what[0] != self.CHANGED_SPECIFIC:
			return
		if what[1] != iPlayableService.evStart:
			return
		self.text = "---"
		service = self.source.serviceref
		num = service and service.getChannelNum() or -1
		if (num == -1):
 			self.text = '---'
		else:
			self.text = str(num)

