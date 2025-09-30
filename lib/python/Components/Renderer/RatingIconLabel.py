# This Renderer is used in E2-DarkOS-skin and it's temporary.
from Components.Converter.EventInfo import COUNTRIES, OPENTV_COUNTRIES, EventInfo

from Components.Renderer.Renderer import Renderer
from enigma import eLabel, gRGB
from skin import parseColor


class RatingIconLabel(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.colors = {}
		self.extendDirection = "right"

	GUI_WIDGET = eLabel

	def postWidgetCreate(self, instance):
		instance.setNoWrap(1)
		self.changed((self.CHANGED_DEFAULT,))

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes:
			if attrib == "colors":
				self.colors = {int(k): parseColor(v) for k, v in (item.split(":") for item in value.split(","))}
			elif attrib == "extendDirection":
				self.extendDirection = value
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
					color = 0x00000000
					ageText = ""
					if ";" in self.source.text:
						split_text = self.source.text.split(";")
						age = int(split_text[0])
						if age == 0:
							self.hideLabel()
							return
						country = split_text[1]
						if country in OPENTV_COUNTRIES:
							country = OPENTV_COUNTRIES[country]
						if country in COUNTRIES:
							c = COUNTRIES[country]
						else:
							c = COUNTRIES["ETSI"]
						rating = c[EventInfo.RATING_NORMAL].get(age, c[EventInfo.RATING_DEFAULT](age))
						ageText = rating[EventInfo.RATING_SHORT].strip().replace("+", "")
						color = rating[EventInfo.RATING_COLOR]
					else:
						age = int(self.source.text.replace("+", ""))
						if age == 0:
							self.hideLabel()
							return
						if age <= 15:
							age += 3
						ageText = str(age)
						color = self.colors.get(age, 0x10000000)

					size = self.instance.size()
					pos = self.instance.position()
					self.instance.setText(ageText)
					textSize = self.instance.calculateSize()
					newWidth = textSize.width() + 20
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
