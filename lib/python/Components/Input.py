from HTMLComponent import *
from GUIComponent import *
from VariableText import *

from enigma import eLabel, isUTF8, convertUTF8DVB, convertDVBUTF8

from Tools.NumericalTextInput import NumericalTextInput

class Input(VariableText, HTMLComponent, GUIComponent):
	TEXT = 0
	PIN = 1
	NUMBER = 2	

	def __init__(self, text="", maxSize = False, type = TEXT):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.table = 0
		self.numericalTextInput = NumericalTextInput(self.right)
		self.type = type
		self.maxSize = maxSize
		self.currPos = 0
		self.Text = text
		self.overwrite = 0
		self.update()

	def update(self):
		self.setMarkedPos(self.currPos)
		if self.type == self.PIN:
			self.message = "*" * len(self.Text)
		else:
			self.message = convertDVBUTF8(self.Text, self.table)
		if self.instance:
			self.instance.setText(self.message)

	def setText(self, text):
		if not len(text):
			self.currPos = 0
			self.Text = ""
		elif isUTF8(text):
			self.Text = convertUTF8DVB(text, self.table)
		else:
			self.Text = text
		self.update()

	def getText(self):
		return convertDVBUTF8(self.Text, self.table)

	def createWidget(self, parent):
		return eLabel(parent, self.currPos)

	def getSize(self):
		s = self.instance.calculateSize()
		return (s.width(), s.height())
	
	def right(self):
		self.currPos += 1
		if self.currPos == len(self.Text):
			if self.maxSize:
				self.currPos -= 1
			else:
				self.Text = self.Text + " "
		self.update()

	def left(self):
		if self.currPos > 0:
			self.currPos -= 1
			self.update()

	def up(self):
		if self.Text[self.currPos] == "9" or self.Text[self.currPos] == " ":
			newNumber = "0"
		else:
			newNumber = str(int(self.Text[self.currPos]) + 1)
		self.Text = self.Text[0:self.currPos] + newNumber + self.Text[self.currPos + 1:]
		self.update()

	def down(self):
		if self.Text[self.currPos] == "0" or self.Text[self.currPos] == " ":
			newNumber = "9"
		else:
			newNumber = str(int(self.Text[self.currPos]) - 1)
		self.Text = self.Text[0:self.currPos] + newNumber + self.Text[self.currPos + 1:]
		self.update()
		
	def home(self):
		self.currPos = 0
		self.update()
	
	def end(self):
		self.currPos = len(self.Text) - 1
		self.update()

	def tab(self):
		if self.currPos == len(self.Text) - 1:
			self.Text=self.Text+ " "
			self.end()
		else:
			self.Text = self.Text[0:self.currPos] + " " + self.Text[self.currPos:]
		self.update()

	def delete(self):
		self.Text = self.Text[:self.currPos] + self.Text[self.currPos + 1:]
		self.update()

	def toggleOverwrite(self):
		if self.overwrite==1:
			self.overwrite=0
		else:
			self.overwrite=1
		self.update()

	def deleteBackward(self):
		self.Text = self.Text[:self.currPos - 1] + self.Text[self.currPos:]
		self.left()
		self.update()

	def handleAscii(self, code):
		newChar = chr(code)
		if self.overwrite==1:
			self.Text = self.Text[0:self.currPos] + newChar + self.Text[self.currPos + 1:]
		else:
			self.Text = self.Text[0:self.currPos] + newChar + self.Text[self.currPos:]
		self.right()

	def number(self, number):
		if self.type == self.TEXT:
			newChar = self.numericalTextInput.getKey(number)
		elif self.type == self.PIN or self.type == self.NUMBER:
			newChar = str(number)
		self.Text = self.Text[0:self.currPos] + newChar + self.Text[self.currPos + 1:]
		if self.type == self.PIN or self.type == self.NUMBER:
			self.right()
		self.update()
