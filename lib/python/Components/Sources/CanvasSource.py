from Source import Source

class CanvasSource(Source):
	def __init__(self):
		Source.__init__(self)
		self.sequence = 0
		self.clear()

	def clear(self):
		self.sequence += 1
		self._drawlist = (self.sequence, [ ])

	def get_drawlist(self):
		return self._drawlist

	drawlist = property(get_drawlist)

	def fill(self, x, y, width, height, color):
		self.drawlist[1].append((1, x, y, width, height, color))

	def writeText(self, x, y, width, height, fg, bg, font, text, flags = 0):
		self.drawlist[1].append((2, x, y, width, height, fg, bg, font, text, flags))

	def flush(self):
		self.changed((self.CHANGED_DEFAULT,))
