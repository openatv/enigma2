from Components.Sources.Clock import Clock
from Screens.Screen import Screen


class Globals(Screen):
	def __init__(self):
		Screen.__init__(self, None)
		self["CurrentTime"] = Clock()
