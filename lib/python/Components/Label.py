from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from VariableText import VariableText

from ConditionalWidget import ConditionalWidget, BlinkingWidget, BlinkingWidgetConditional

from enigma import eLabel

class Label(VariableText, HTMLComponent, GUIComponent):
	def __init__(self, text=""):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.setText(text)
	
# html:	
	def produceHTML(self):
		return self.getText()

# GUI:
	GUI_WIDGET = eLabel

	def getSize(self):
		s = self.instance.calculateSize()
		return (s.width(), s.height())

class LabelConditional(Label, ConditionalWidget):
	def __init__(self, text = "", withTimer = True):
		ConditionalWidget.__init__(self, withTimer = withTimer)
		Label.__init__(self, text = text)
		
class BlinkingLabel(Label, BlinkingWidget):
	def __init__(self, text = ""):
		Label.__init__(text = text)
		BlinkingWidget.__init__()

class BlinkingLabelConditional(BlinkingWidgetConditional, LabelConditional):
	def __init__(self, text = ""):
		LabelConditional.__init__(self, text = text)
		BlinkingWidgetConditional.__init__(self)
