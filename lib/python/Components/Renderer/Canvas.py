from Renderer import Renderer

from enigma import eCanvas, eRect, gRGB

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
			print "drawing ..", l
			self.instance.fillRect(eRect(l[1], l[2], l[3], l[4]), gRGB(l[5]))

	def changed(self, what):
		self.pull_updates()

	def postWidgetCreate(self, instance):
		self.sequence = None
		self.pull_updates()
