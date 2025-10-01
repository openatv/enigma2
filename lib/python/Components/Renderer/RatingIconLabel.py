from enigma import eLabel, gRGB

from skin import parseColor
from Components.Renderer.Renderer import Renderer


class RatingIconLabel(Renderer):
	GUI_WIDGET = eLabel

	def __init__(self):
		Renderer.__init__(self)
		self.colors = {}
		self.extendDirection = "right"
		self.sidesMargin = 20

	def postWidgetCreate(self, instance):
		instance.setNoWrap(True)
		self.changed((self.CHANGED_DEFAULT,))

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes:
			match attrib:
				case "colors":
					self.colors = {int(k): parseColor(v) for k, v in (item.split(":") for item in value.split(","))}
				case "extendDirection":
					self.extendDirection = value
				case "sidesMargin":
					self.sidesMargin = int(value)
				case _:
					attribs.append((attrib, value))
		self.skinAttributes = attribs
		result = Renderer.applySkin(self, desktop, parent)
		self.changed((self.CHANGED_DEFAULT,))
		return result

	def hideLabel(self):
		if self.instance:
			self.instance.setText("")
			self.instance.hide()

	def changed(self, what):
		self.hideLabel()  # initially hide the label
		if self.source and hasattr(self.source, "text") and self.instance:
			if what[0] == self.CHANGED_CLEAR:
				self.hideLabel()
			else:
				if self.source.text:
					color = 0x00000000
					ageText = ""
					if ";" in self.source.text:
						splitText = self.source.text.split(";")
						if splitText and len(splitText) == 2 and splitText[0]:
							ageText = splitText[0]
							color = parseColor(splitText[1])
						else:
							self.hideLabel()
							return
					else:
						age = int(self.source.text.replace("+", ""))
						if age <= 15:
							age += 3
						ageText = str(age)
						color = self.colors.get(age, 0x10000000)
					size = self.instance.size()
					pos = self.instance.position()
					self.instance.setText(ageText)
					textSize = self.instance.calculateSize()
					newWidth = textSize.width() + self.sidesMargin
					if newWidth < size.width():
						newWidth = size.width()
					if self.extendDirection == "left":
						rightEdgePos = pos.x() + size.width()
						self.move(rightEdgePos - newWidth, pos.y())
					if self.extendDirection != "none":
						self.resize(newWidth, size.height())
					self.instance.setBackgroundColor(gRGB(color))
					self.instance.show()
				else:
					self.hideLabel()
