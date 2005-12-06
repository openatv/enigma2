from HTMLComponent import *
from GUIComponent import *
from VariableText import *

from ConditionalWidget import *

from enigma import eLabel

class Label(HTMLComponent, GUIComponent, VariableText):
	def __init__(self, text=""):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.setText(text)
	
# html:	
	def produceHTML(self):
		return self.getText()

# GUI:
	def createWidget(self, parent):
		return eLabel(parent)
	
	def getSize(self):
		s = self.instance.calculateSize()
		return (s.width(), s.height())

	def show(self):
		self.instance.show()

	def hide(self):
		self.instance.hide()

class LabelConditional(Label, ConditionalWidget):
	def __init__(self, text = "", withTimer = True):
		ConditionalWidget.__init__(self, withTimer = withTimer)
		Label.__init__(self, text = text)