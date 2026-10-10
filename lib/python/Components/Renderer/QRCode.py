from enigma import eQRCode

from Components.Renderer.Renderer import Renderer
from Components.VariableText import VariableText


class QRCode(VariableText, Renderer):
	GUI_WIDGET = eQRCode

	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)

	def changed(self, what):
		if what[0] == self.CHANGED_CLEAR or not self.source:
			self.text = ""
		else:
			self.text = getattr(self.source, "text", "") or ""
		if self.instance:
			self.updateVisibility(self.instance)

	def postWidgetCreate(self, instance):
		VariableText.postWidgetCreate(self, instance)
		self.updateVisibility(instance)

	def updateVisibility(self, instance):
		if self.text:
			instance.show()
		else:
			instance.hide()
