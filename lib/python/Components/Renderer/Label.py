from Components.VariableText import VariableText
from Components.GUIComponent import GUIComponent

from enigma import eLabel

class Label(VariableText, GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		VariableText.__init__(self)

	GUI_WIDGET = eLabel

	def connect(self, source):
		source.changed.listen(self.changed)
		self.source = source
		self.changed()

	def changed(self):
		self.text = self.source.text
