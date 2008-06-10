from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from VariableText import VariableText
from skin import parseColor
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

class MultiColorLabel(Label):
	def __init__(self, text=""):
		Label.__init__(self,text)
		self.foreColors = []
		self.backColors = []

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			foregroundColor = None
			backgroundColor = None
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "foregroundColors":
					colors = value.split(',')
					for color in colors:
						self.foreColors.append(parseColor(color))
					if not foregroundColor:
						foregroundColor = colors[0]
				elif attrib == "backgroundColors":
					colors = value.split(',')
					for color in colors:
						self.backColors.append(parseColor(color))
					if not backgroundColor:
						backgroundColor = colors[0]
				elif attrib == "backgroundColor":
					backgroundColor = value
				elif attrib == "foregroundColor":
					foregroundColor = value
				else:
					attribs.append((attrib,value))
			if foregroundColor:
				attribs.append(("foregroundColor",foregroundColor))
			if backgroundColor:
				attribs.append(("backgroundColor",backgroundColor))
			self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop, screen)
	
	def setForegroundColorNum(self, x):
		if self.instance:
			if len(self.foreColors) > x:
				self.instance.setForegroundColor(self.foreColors[x])
			else:
				print "setForegroundColorNum(%d) failed! defined colors:" %(x), self.foreColors

	def setBackgroundColorNum(self, x):
		if self.instance:
			if len(self.backColors) > x:
				self.instance.setBackgroundColor(self.backColors[x])
			else:
				print "setBackgroundColorNum(%d) failed! defined colors:" %(x), self.backColors

