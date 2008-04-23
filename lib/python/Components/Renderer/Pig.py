##
## P(icture)i(n)g(raphics) renderer
##
from Renderer import Renderer
from enigma import eVideoWidget, eSize, ePoint

class Pig(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.Position = self.Size = None

	GUI_WIDGET = eVideoWidget

	def postWidgetCreate(self, instance):
		instance.setDecoder(0)

	def applySkin(self, desktop, parent):
		ret = Renderer.applySkin(self, desktop, parent)
		if ret:
			self.Position = self.instance.position() # fixme, scaling!
			self.Size = self.instance.size()
		return ret

	def preWidgetRemove(self, instance):
		instance.resize(eSize(720,576))
		instance.move(ePoint(0,0))

	def onShow(self):
		if self.instance:
			if self.Size:
				self.instance.resize(self.Size)
			if self.Position:
				self.instance.move(self.Position)

	def onHide(self):
		if self.instance:
			self.preWidgetRemove(self.instance)
