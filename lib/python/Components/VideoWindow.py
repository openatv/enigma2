from GUIComponent import GUIComponent
from enigma import eVideoWidget

class VideoWindow(GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)

	GUI_WIDGET = eVideoWidget
