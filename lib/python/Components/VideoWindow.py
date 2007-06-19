from GUIComponent import GUIComponent
from enigma import eVideoWidget

class VideoWindow(GUIComponent):
	def __init__(self, decoder = 1):
		GUIComponent.__init__(self)
		self.decoder = decoder

	GUI_WIDGET = eVideoWidget

	def postWidgetCreate(self, instance):
		instance.setDecoder(self.decoder)
