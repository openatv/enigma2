from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from VariableText import VariableText
from skin import parseColor
from ConditionalWidget import ConditionalWidget, BlinkingWidget, BlinkingWidgetConditional

from enigma import eLabel

# Fake Source mixin
# Allows a getText()/setText() Component widget to
# be references in a <widget source= /> screen skin element
# without crashing and without displaying anything.

# To do that it must defer setting any constructor text argument
# or any <widget ... text= .../> text assignment until after applySkin()
# has attached any Converters or Renderers, because they call back
# to getText() when they attach, so at that time getText() must
# return an empty string.

class DummySource(object):
	def __init__(self, text=""):
		# defer setting text until applySkin() has connected any Elements
		self.__initText = text

	def connectDownstream(self, downstream):
		pass

	def checkSuspend(self):
		pass

	def disconnectDownstream(self, downstream):
		pass

	# This applySkin intercepts any <widget ... text= .../> assignment
	# and defers calls of the main object's setText() until the underlying
	# GUIComponent.applySkin() has been called.

	def applySkin(self, desktop, screen):
		# defer any "text" attribute setting until any Elements have been connected
		if self.skinAttributes is not None and "text" in self.skinAttributes:
			self.__initText = _(self.skinAttributes["text"])
			del self.skinAttributes["text"]
		retval = GUIComponent.applySkin(self, desktop, screen)

		# Test for whether self.__initText exists with a deferred
		# initial text value. If it does, now use it to set
		# the instance's text value.
		# hasattr(self, "_DummySource__initText") tests for self.__initText.

		if hasattr(self, "_DummySource__initText"):
			self.setText(self.__initText)
			del self.__initText

		return retval

class Label(DummySource, VariableText, HTMLComponent, GUIComponent):
	def __init__(self, text=""):
		GUIComponent.__init__(self)
		VariableText.__init__(self)

		# Use DummySource to allow Label to be used in a
		# <widget source= ... /> screen skin element, but
		# without displaying anything through that element

		DummySource.__init__(self, text)

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
