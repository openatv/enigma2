from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from VariableText import VariableText
from skin import parseColor
from ConditionalWidget import ConditionalWidget, BlinkingWidget, BlinkingWidgetConditional

from enigma import eLabel

# Fake Source mixin
# Allows a getText()/setText() Component widget to
# be referenced in a <widget source= /> screen skin element
# without crashing and without displaying anything.

# To do that it must save the widget text value and set the widget text to ""
# when the connection to a downstream is Converter or Renderer is made
# so that the initial displayed text in the Renderer when it
# connects is "".

class DummySource(object):
	def connectDownstream(self, downstream):
		# intercept the connection to the downstream and save
		# and clear the widget text
		# hasattr(self, "_DummySource__initText") tests for self.__initText.
		if not hasattr(self, "_DummySource__initText"):
			self.__initText = self.text
			self.text = ""

	def checkSuspend(self):
		pass

	def disconnectDownstream(self, downstream):
		pass

	# This applySkin intercepts any <widget ... text= .../> assignment
	# so that it's properly applied and restores the correct text value
	# after any Converter or Renderer connections have been made.

	def applySkin(self, desktop, screen):
		# catch any "text" attribute setting so that it's properly applied
		if self.skinAttributes is not None and "text" in self.skinAttributes:
			self.__initText = _(self.skinAttributes["text"])
			del self.skinAttributes["text"]
		retval = GUIComponent.applySkin(self, desktop, screen)

		# Test for whether self.__initText exists with a saved
		# initial ot skin text value. If it does, now use it to set
		# the instance's text value back to its intended value.

		# hasattr(self, "_DummySource__initText") tests
		# for self.__initText.

		if hasattr(self, "_DummySource__initText"):
			self.text = self.__initText
			del self.__initText

		return retval

class Label(DummySource, VariableText, HTMLComponent, GUIComponent):
	def __init__(self, text=""):
		GUIComponent.__init__(self)
		VariableText.__init__(self)

		# Use DummySource to allow Label to be used in a
		# <widget source= ... /> screen skin element, but
		# without displaying anything through that element

		DummySource.__init__(self)
		self.text = text

# html:
	def produceHTML(self):
		return self.getText()

# GUI:
	GUI_WIDGET = eLabel

	def getSize(self):
		s = self.instance.calculateSize()
		return s.width(), s.height()

class LabelConditional(Label, ConditionalWidget):
	def __init__(self, text="", withTimer=True):
		ConditionalWidget.__init__(self, withTimer=withTimer)
		Label.__init__(self, text=text)

class BlinkingLabel(Label, BlinkingWidget):
	def __init__(self, text=""):
		Label.__init__(text=text)
		BlinkingWidget.__init__()

class BlinkingLabelConditional(BlinkingWidgetConditional, LabelConditional):
	def __init__(self, text=""):
		LabelConditional.__init__(self, text=text)
		BlinkingWidgetConditional.__init__(self)

class MultiColorLabel(Label):
	def __init__(self, text=""):
		Label.__init__(self, text)
		self.foreColors = []
		self.backColors = []

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			foregroundColor = None
			backgroundColor = None
			attribs = []
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
					attribs.append((attrib, value))
			if foregroundColor:
				attribs.append(("foregroundColor", foregroundColor))
			if backgroundColor:
				attribs.append(("backgroundColor", backgroundColor))
			self.skinAttributes = attribs
		return Label.applySkin(self, desktop, screen)

	def setForegroundColorNum(self, x):
		if self.instance:
			if len(self.foreColors) > x:
				self.instance.setForegroundColor(self.foreColors[x])
			else:
				print "setForegroundColorNum(%d) failed! defined colors:" % x, self.foreColors

	def setBackgroundColorNum(self, x):
		if self.instance:
			if len(self.backColors) > x:
				self.instance.setBackgroundColor(self.backColors[x])
			else:
				print "setBackgroundColorNum(%d) failed! defined colors:" % x, self.backColors
