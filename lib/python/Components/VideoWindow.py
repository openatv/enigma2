from GUIComponent import GUIComponent
from enigma import eVideoWidget

class VideoWindow(GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
	
	def GUIcreate(self, parent):
		self.instance = eVideoWidget(parent)

	def GUIdelete(self):
		self.instance = None
