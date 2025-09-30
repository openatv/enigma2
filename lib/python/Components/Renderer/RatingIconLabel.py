# This Renderer is used in E2-DarkOS-skin and it's temporary.
# The Renderer can changed or removed.
# We need to find a better solution for the ratings.

from Components.Renderer.Renderer import Renderer
from enigma import eLabel, gRGB
from skin import parseColor


class RatingIconLabel(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.colors = {}

	GUI_WIDGET = eLabel

	def postWidgetCreate(self, instance):
		self.changed((self.CHANGED_DEFAULT,))

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes:
			if attrib == "colors":
				self.colors = {int(k): parseColor(v) for k, v in (item.split(":") for item in value.split(","))}
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		rc = Renderer.applySkin(self, desktop, parent)
		self.changed((self.CHANGED_DEFAULT,))
		return rc

	def hideLabel(self):
		self.instance.setText("")
		self.instance.hide()

	def changed(self, what):
		if self.source and hasattr(self.source, "text") and self.instance:
			if what[0] == self.CHANGED_CLEAR:
				self.hideLabel()
			else:
				if self.source.text:
					age = int(self.source.text.replace("+", ""))
					if age == 0:
						self.hideLabel()
						return
					if age <= 15:
						age += 3

					self.instance.setText(str(age))
					self.instance.setBackgroundColor(gRGB(self.colors.get(age, 0x10000000)))
					self.instance.show()
				else:
					self.hideLabel()
