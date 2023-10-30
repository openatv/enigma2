from enigma import eLabel, iPlayableService
from Components.Renderer.Renderer import Renderer
from Components.VariableText import VariableText


class ChannelNumber(Renderer, VariableText):
	GUI_WIDGET = eLabel

	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)
		self.text = "---"

	def changed(self, what):
		if what is True or what[0] == self.CHANGED_SPECIFIC and what[1] == iPlayableService.evStart:
			service = self.source.serviceref
			num = service and service.getChannelNum() or None
			self.text = str(num) if num else "---"
