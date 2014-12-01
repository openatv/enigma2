from Components.VariableText import VariableText
from enigma import eLabel, iPlayableService
from Renderer import Renderer

class ChannelNumber(Renderer, VariableText):
	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)
		self.text = "---"
	GUI_WIDGET = eLabel

	def changed(self, what):
		if what == True or what[0] == self.CHANGED_SPECIFIC and what[1] == iPlayableService.evStart:
			service = self.source.serviceref
			num = service and service.getChannelNum() or None
			if num:
				self.text = str(num)
			else:
				self.text = '---'

