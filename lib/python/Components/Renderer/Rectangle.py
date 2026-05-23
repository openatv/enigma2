from enigma import eRectangle
from Components.Renderer.Renderer import Renderer


class Rectangle(Renderer):
	GUI_WIDGET = eRectangle

	def __init__(self):
		Renderer.__init__(self)

	def connect(self, source):
		if (source):
			Renderer.connect(self, source)
