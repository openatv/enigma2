from GUIComponent import GUIComponent
from enigma import eVideoWidget, eSize

class VideoWindow(GUIComponent):
	def __init__(self, decoder = 1, fb_width = 720, fb_height = 576):
		GUIComponent.__init__(self)
		self.decoder = decoder
		self.fb_width = fb_width
		self.fb_height = fb_height

	GUI_WIDGET = eVideoWidget

	def postWidgetCreate(self, instance):
		instance.setDecoder(self.decoder)
		instance.setFBSize(eSize(self.fb_width, self.fb_height))
