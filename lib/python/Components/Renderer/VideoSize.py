from enigma import eLabel, iServiceInformation
from Components.Renderer.Renderer import Renderer
from Components.VariableText import VariableText

#
# borrowed from vali, addapter for openpli
#


class VideoSize(Renderer, VariableText):
	GUI_WIDGET = eLabel

	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)

	def changed(self, what):
		service = self.source.service
		info = service and service.info()
		if info is not None:
			xresol = info.getInfo(iServiceInformation.sVideoWidth)
			yresol = info.getInfo(iServiceInformation.sVideoHeight)
			self.text = f"{xresol}x{yresol}" if xresol > 0 else ""
		else:
			self.text = ""
