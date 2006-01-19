from HTMLComponent import *
from GUIComponent import *
from VariableText import *

from enigma import eLabel

from Tools.NumericalTextInput import NumericalTextInput

class Input(HTMLComponent, GUIComponent, VariableText):
	def __init__(self, text=""):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.numericalTextInput = NumericalTextInput(self.right)
		self.currPos = 0
		self.text = text
		self.update()

	def update(self):
		self.setMarkedPos(self.currPos)
		self.setText(self.text)
		#self.setText(self.text[0:self.currPos] + "_" + self.text[self.currPos] + "_" + self.text[self.currPos + 1:])

	
	def createWidget(self, parent):
		return eLabel(parent, self.currPos)
	
	def getSize(self):
		s = self.instance.calculateSize()
		return (s.width(), s.height())
	
	def right(self):
		self.currPos += 1
		if self.currPos == len(self.text):
			self.text = self.text + " "
		self.update()
		
	def left(self):
		self.currPos -= 1
		self.update()
		
	def number(self, number):
		self.text = self.text[0:self.currPos] + self.numericalTextInput.getKey(number) + self.text[self.currPos + 1:]
		self.update()

	def show(self):
		self.instance.show()

	def hide(self):
		self.instance.hide()