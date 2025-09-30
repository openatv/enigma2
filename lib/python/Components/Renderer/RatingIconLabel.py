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
		attribs = self.skinAttributes[:]
		for (attrib, value) in self.skinAttributes:
			if attrib == "colors":
				self.colors = {int(k): parseColor(v) for k, v in (item.split(":") for item in value.split(","))}
		self.skinAttributes = attribs
		rc = Renderer.applySkin(self, desktop, parent)
		self.changed((self.CHANGED_DEFAULT,))
		return rc

	def changed(self, what):
		if self.source and hasattr(self.source, "text") and self.instance:
			if what[0] == self.CHANGED_CLEAR:
				self.instance.setText("")
				self.instance.setPixmap(None)
			else:
				if self.source.text:
					age = int(self.source.text.replace("+", ""))
					if age == 0:
						self.instance.setText("")
						self.instance.hide()
						return
					if age <= 15:
						age += 3

					self.instance.setText(str(age))
					self.instance.setBackgroundColor(gRGB(self.colors.get(age, 0x10000000)))
					self.instance.show()
				else:
					self.instance.setText("")
					self.instance.hide()
