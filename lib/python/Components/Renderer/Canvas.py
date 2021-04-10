from enigma import eCanvas, eRect, gRGB

from Renderer import Renderer


class Canvas(Renderer):
	GUI_WIDGET = eCanvas

	def __init__(self):
		Renderer.__init__(self)
		self.sequence = None
		self.draw_count = 0

	def pull_updates(self):
		if self.instance is None:
			return

		# do an incremental update
		list = self.source.drawlist
		if list is None:
			return

		# if the lists sequence count changed, re-start from begin
		if list[0] != self.sequence:
			self.sequence = list[0]
			self.draw_count = 0

		self.draw(list[1][self.draw_count:])
		self.draw_count = len(list[1])

	def draw(self, list):
		for l in list:
			if l[0] == 1:
				self.instance.fillRect(eRect(l[1], l[2], l[3], l[4]), gRGB(l[5]))
			elif l[0] == 2:
				self.instance.writeText(eRect(l[1], l[2], l[3], l[4]), gRGB(l[5]), gRGB(l[6]), l[7], l[8], l[9])
			elif l[0] == 3:
				self.instance.drawLine(l[1], l[2], l[3], l[4], gRGB(l[5]))
			elif l[0] == 4:
				self.instance.drawRotatedLine(l[1], l[2], l[3], l[4], l[5], l[6], l[7], l[8], gRGB(l[9]))
			else:
				print "drawlist entry:", l
				raise RuntimeError("invalid drawlist entry")

	def changed(self, what):
		self.pull_updates()

	def postWidgetCreate(self, instance):
		self.sequence = None

		from enigma import eSize

		def parseSize(str):
			x, y = str.split(',')
			return eSize(int(x), int(y))

		for (attrib, value) in self.skinAttributes:
			if attrib == "size":
				self.instance.setSize(parseSize(value))

		self.pull_updates()
