from enigma import ePixmap

from Components.Renderer.Renderer import Renderer


class Pixmap(Renderer):
	def __init__(self):
		Renderer.__init__(self)

	GUI_WIDGET = ePixmap

	def postWidgetCreate(self, instance):
		self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		if what[0] != self.CHANGED_CLEAR:
			if self.source and hasattr(self.source, "pixmap"):
				if self.instance:
					self.instance.setPixmap(self.source.pixmap)
