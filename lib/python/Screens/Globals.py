from Screens.Screen import Screen
from Components.Sources.Clock import Clock

class Globals(Screen):
	def __init__(self):
		Screen.__init__(self, None)
		self["CurrentTime"] = Clock()
