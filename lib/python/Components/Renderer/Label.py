from Components.VariableText import VariableText
from Renderer import Renderer

from enigma import eLabel

class Label(VariableText, Renderer):
	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)

	GUI_WIDGET = eLabel

	def connect(self, source):
		if(source):
			Renderer.connect(self, source)
			self.changed((self.CHANGED_DEFAULT,))
		else:
			print "SKINERROR: render label has no source"

	def changed(self, what):
		if what[0] == self.CHANGED_CLEAR:
			self.text = ""
		elif self.source:
			self.text = self.source.text
		else:
			self.text = "<no-source>"
			print "SKINERROR: render label has no source"

