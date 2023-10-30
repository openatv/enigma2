from enigma import eLabel
from Components.Renderer.Renderer import Renderer
from Components.VariableText import VariableText


class Label(VariableText, Renderer):
	GUI_WIDGET = eLabel

	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)

	def connect(self, source):
		if (source):
			Renderer.connect(self, source)
			self.changed((self.CHANGED_DEFAULT,))
		else:
			print("SKINERROR: render label has no source")

	def changed(self, what):
		if what[0] == self.CHANGED_CLEAR:
			self.text = ""
		elif self.source:
			if hasattr(self.source, "text"):
				self.text = self.source.text
		else:
			self.text = "<no-source>"
			print("SKINERROR: render label has no source")
