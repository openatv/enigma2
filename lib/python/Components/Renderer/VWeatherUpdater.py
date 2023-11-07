# keep it for compatibility, please note this renderer is deprecated --> remove it from your skins
from enigma import eLabel
from Components.Renderer.Renderer import Renderer


class VWeatherUpdater(Renderer):
	GUI_WIDGET = eLabel

	def __init__(self):
		Renderer.__init__(self)
