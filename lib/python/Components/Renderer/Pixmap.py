from enigma import ePixmap
from Components.Renderer.Renderer import Renderer
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import SCOPE_GUISKIN, resolveFilename


class Pixmap(Renderer):
	GUI_WIDGET = ePixmap

	def __init__(self):
		self.pixmaps = []
		Renderer.__init__(self)

	def applySkin(self, desktop, parent):
		attributes = []
		for (attrib, value) in self.skinAttributes:
			if attrib == "pixmaps":
				pixmaps = value.split(",")
				for pixmap in pixmaps:
					self.pixmaps.append(LoadPixmap(resolveFilename(SCOPE_GUISKIN, pixmap.strip())))
			else:
				attributes.append((attrib, value))
		self.skinAttributes = attributes
		return Renderer.applySkin(self, desktop, parent)

	def postWidgetCreate(self, instance):
		self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		if what[0] != self.CHANGED_CLEAR:
			if what[0] == self.CHANGED_SPECIFIC and self.source and hasattr(self.source, "text") and self.pixmaps:
				text = self.source.text
				index = int(text) if text and text.isnumeric() else 0
				if 0 <= index < len(self.pixmaps):
					self.instance.setPixmap(self.pixmaps[index])
				else:
					self.instance.setPixmap(None)
			if self.source and hasattr(self.source, "pixmap"):
				if self.instance:
					self.instance.setPixmap(self.source.pixmap)
