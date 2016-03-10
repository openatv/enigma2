from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from VariableText import VariableText
from Label import DummySource

from enigma import eButton

class Button(DummySource, VariableText, HTMLComponent, GUIComponent):
	def __init__(self, text="", onClick=None):
		if not onClick: onClick = []
		GUIComponent.__init__(self)
		VariableText.__init__(self)

		# Use DummySource to allow Label to be used in a
		# <widget source= ... /> screen skin element, but
		# without displaying anything through that element

		DummySource.__init__(self, text)
		self.onClick = onClick

	def push(self):
		for x in self.onClick:
			x()
		return 0

	def disable(self):
		pass

	def enable(self):
		pass

# html:
	def produceHTML(self):
		return "<input type=\"submit\" text=\"" + self.getText() + "\">\n"

	GUI_WIDGET = eButton

	def postWidgetCreate(self, instance):
		instance.setText(self.text)
		instance.selected.get().append(self.push)

	def preWidgetRemove(self, instance):
		instance.selected.get().remove(self.push)
