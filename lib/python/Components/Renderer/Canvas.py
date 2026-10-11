from enigma import eCanvas, eRect, eSize, gRGB

from Components.Renderer.Renderer import Renderer


class Canvas(Renderer):
	GUI_WIDGET = eCanvas

	def __init__(self):
		Renderer.__init__(self)
		self.sequence = None
		self.drawCount = 0

	def postWidgetCreate(self, instance):
		self.sequence = None

		def parseSize(val):
			x, y = val.split(',')
			return eSize(int(x), int(y))

		for (attrib, value) in self.skinAttributes:
			if attrib == "size":
				self.instance.setSize(parseSize(value))

		self.pullUpdates()

	def changed(self, what):
		self.pullUpdates()

	def pullUpdates(self):
		if self.instance is not None:  # do an incremental update
			items = self.source.drawlist
			if items is not None:
				if items[0] != self.sequence:  # if the lists sequence count changed, re-start from begin
					self.sequence = items[0]
					self.drawCount = 0
				self.draw(items[1][self.drawCount:])
				self.drawCount = len(items[1])

	def draw(self, items):
		for item in items:
			match item[0]:
				case 1:
					self.instance.fillRect(eRect(item[1], item[2], item[3], item[4]), gRGB(item[5]))
				case 2:
					self.instance.writeText(eRect(item[1], item[2], item[3], item[4]), gRGB(item[5]), gRGB(item[6]), item[7], item[8], item[9])
				case 3:
					self.instance.drawLine(item[1], item[2], item[3], item[4], gRGB(item[5]))
				case 4:
					self.instance.drawRotatedLine(item[1], item[2], item[3], item[4], item[5], item[6], item[7], item[8], gRGB(item[9]))
				case _:
					print(f"[Canvas] drawlist entry: {item}")
					raise RuntimeError("invalid drawlist entry")
