# keep it for compatibility, please note this renderer is deprecated --> remove it from your skins
from Components.Renderer.Renderer import Renderer
from enigma import eLabel


class VWeatherUpdater(Renderer):

	def __init__(self):
		Renderer.__init__(self)

	GUI_WIDGET = eLabel
