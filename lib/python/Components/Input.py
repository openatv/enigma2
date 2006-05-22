from HTMLComponent import *
from GUIComponent import *
from VariableText import *

from enigma import eLabel

from Tools.NumericalTextInput import NumericalTextInput

class Input(VariableText, HTMLComponent, GUIComponent):
	TEXT = 0
	PIN = 1
	NUMBER = 2	
	
	def __init__(self, text="", maxSize = False, type = TEXT):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.numericalTextInput = NumericalTextInput(self.right)
		self.type = type
		self.maxSize = maxSize
		self.currPos = 0
		self.text = text
		self.update()

	def update(self):
		self.setMarkedPos(self.currPos)
		text = self.text
		if self.type == self.PIN:
			text = "*" * len(self.text)
		self.setText(text)
		#self.setText(self.text[0:self.currPos] + "_" + self.text[self.currPos] + "_" + self.text[self.currPos + 1:])

	def getText(self):
		return self.text
	
	def createWidget(self, parent):
		return eLabel(parent, self.currPos)
	
	def getSize(self):
		s = self.instance.calculateSize()
		return (s.width(), s.height())
	
	def right(self):
		self.currPos += 1
		if self.currPos == len(self.text):
			if self.maxSize:
				self.currPos -= 1
			else:
				self.text = self.text + " "
			
		self.update()
		
	def left(self):
		self.currPos -= 1
		self.update()
		
	def up(self):
		if self.text[self.currPos] == "9" or self.text[self.currPos] == " ":
			newNumber = "0"
		else:
			newNumber = str(int(self.text[self.currPos]) + 1)
		self.text = self.text[0:self.currPos] + newNumber + self.text[self.currPos + 1:]
		self.update()
		
	def down(self):
		if self.text[self.currPos] == "0" or self.text[self.currPos] == " ":
			newNumber = "9"
		else:
			newNumber = str(int(self.text[self.currPos]) - 1)

		self.text = self.text[0:self.currPos] + newNumber + self.text[self.currPos + 1:]
		self.update()
		
	def delete(self):
		self.text = self.text[:self.currPos] + self.text[self.currPos + 1:]
		self.update()
		
	def number(self, number):
		if self.type == self.TEXT:
			newChar = self.numericalTextInput.getKey(number)
		elif self.type == self.PIN or self.type == self.NUMBER:
			newChar = str(number)
		self.text = self.text[0:self.currPos] + newChar + self.text[self.currPos + 1:]
		if self.type == self.PIN or self.type == self.NUMBER:
			self.right()
		self.update()
