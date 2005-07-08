from HTMLComponent import *
from GUIComponent import *
from VariableText import *

from enigma import eButton

class Button(HTMLComponent, GUIComponent, VariableText):
	def __init__(self, text="", onClick = [ ]):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.setText(text)
		self.onClick = onClick
	
	def push(self):
		for x in self.onClick:
			x()
		return 0
	
	def disable(self):
#		self.instance.hide()
		pass
	
	def enable(self):
#		self.instance.show()
		pass

# html:
	def produceHTML(self):
		return "<input type=\"submit\" text=\"" + self.getText() + "\">\n"

# GUI:
	def createWidget(self, parent):
		g = eButton(parent)
		g.selected.get().append(self.push)
		return g

	def removeWidget(self, w):
		w.selected.get().remove(self.push)

