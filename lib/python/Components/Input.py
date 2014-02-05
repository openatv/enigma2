from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from VariableText import VariableText

from enigma import eLabel

from Tools.NumericalTextInput import NumericalTextInput

class Input(VariableText, HTMLComponent, GUIComponent, NumericalTextInput):
	TEXT = 0
	PIN = 1
	NUMBER = 2

	def __init__(self, text="", maxSize=False, visible_width=False, type=TEXT, currPos=0, allMarked=True):
		NumericalTextInput.__init__(self, self.right)
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.type = type
		self.allmarked = allMarked and (text != "") and (type != self.PIN)
		self.maxSize = maxSize
		self.currPos = currPos
		self.visible_width = visible_width
		self.offset = 0
		self.overwrite = maxSize
		self.setText(text)

	def __len__(self):
		return len(self.text)

	def update(self):
		if self.visible_width:
			if self.currPos < self.offset:
				self.offset = self.currPos
			if self.currPos >= self.offset + self.visible_width:
				if self.currPos == len(self.Text):
					self.offset = self.currPos - self.visible_width
				else:
					self.offset = self.currPos - self.visible_width + 1
			if self.offset > 0 and self.offset + self.visible_width > len(self.Text):
				self.offset = max(0, len(self.Text) - self.visible_width)
		if self.allmarked:
			self.setMarkedPos(-2)
		else:
			self.setMarkedPos(self.currPos-self.offset)
		if self.visible_width:
			if self.type == self.PIN:
				self.text = ""
				for x in self.Text[self.offset:self.offset+self.visible_width]:
					self.text += (x==" " and " " or "*")
			else:
				self.text = self.Text[self.offset:self.offset+self.visible_width].encode("utf-8") + " "
		else:
			if self.type == self.PIN:
				self.text = ""
				for x in self.Text:
					self.text += (x==" " and " " or "*")
			else:
				self.text = self.Text.encode("utf-8") + " "

	def setText(self, text):
		if not len(text):
			self.currPos = 0
			self.Text = u""
		else:
			self.Text = text.decode("utf-8", "ignore").decode("utf-8")
		self.update()

	def getText(self):
		return self.Text.encode("utf-8")

	def createWidget(self, parent):
		if self.allmarked:
			return eLabel(parent, -2)
		else:
			return eLabel(parent, self.currPos-self.offset)

	def getSize(self):
		s = self.instance.calculateSize()
		return s.width(), s.height()

	def markAll(self):
		self.allmarked = True
		self.update()

	def innerright(self):
		if self.allmarked:
			self.currPos = 0
			self.allmarked = False
		elif self.maxSize:
			if self.currPos < len(self.Text)-1:
				self.currPos += 1
		else:
			if self.currPos < len(self.Text):
				self.currPos += 1

	def right(self):
		if self.type == self.TEXT:
			self.timeout()
		self.innerright()
		self.update()

	def left(self):
		if self.type == self.TEXT:
			self.timeout()
		if self.allmarked:
			if self.maxSize:
				self.currPos = len(self.Text) - 1
			else:
				self.currPos = len(self.Text)
			self.allmarked = False
		elif self.currPos > 0:
			self.currPos -= 1
		self.update()

	def up(self):
		self.allmarked = False
		if self.type == self.TEXT:
			self.timeout()
		if self.currPos == len(self.Text) or self.Text[self.currPos] == "9" or self.Text[self.currPos] == " ":
			newNumber = "0"
		else:
			newNumber = str(int(self.Text[self.currPos]) + 1)
		self.Text = self.Text[0:self.currPos] + newNumber + self.Text[self.currPos + 1:]
		self.update()

	def down(self):
		self.allmarked = False
		if self.type == self.TEXT:
			self.timeout()
		if self.currPos == len(self.Text) or self.Text[self.currPos] == "0" or self.Text[self.currPos] == " ":
			newNumber = "9"
		else:
			newNumber = str(int(self.Text[self.currPos]) - 1)
		self.Text = self.Text[0:self.currPos] + newNumber + self.Text[self.currPos + 1:]
		self.update()

	def home(self):
		self.allmarked = False
		if self.type == self.TEXT:
			self.timeout()
		self.currPos = 0
		self.update()

	def end(self):
		self.allmarked = False
		if self.type == self.TEXT:
			self.timeout()
		if self.maxSize:
			self.currPos = len(self.Text) - 1
		else:
			self.currPos = len(self.Text)
		self.update()

	def insertChar(self, ch, pos=False, owr=False, ins=False):
		self.Text = self.Text.decode("utf-8", "ignore").decode("utf-8")
		if not pos:
			pos = self.currPos
		if ins and not self.maxSize:
			self.Text = self.Text[0:pos] + ch + self.Text[pos:]
		elif owr or self.overwrite:
			self.Text = self.Text[0:pos] + ch + self.Text[pos + 1:]
		elif self.maxSize:
			self.Text = self.Text[0:pos] + ch + self.Text[pos:-1]
		else:
			self.Text = self.Text[0:pos] + ch + self.Text[pos:]

	def deleteChar(self, pos):
		if not self.maxSize:
			self.Text = self.Text[0:pos] + self.Text[pos + 1:]
		elif self.overwrite:
			self.Text = self.Text[0:pos] + " " + self.Text[pos + 1:]
		else:
			self.Text = self.Text[0:pos] + self.Text[pos + 1:] + " "

	def deleteAllChars(self):
		if self.maxSize:
			self.Text = " " * len(self.Text)
		else:
			self.Text = ""
		self.currPos = 0

	def tab(self):
		if self.type == self.TEXT:
			self.timeout()
		if self.allmarked:
			self.deleteAllChars()
			self.allmarked = False
		else:
			self.insertChar(" ", self.currPos, False, True)
			self.innerright()
		self.update()

	def delete(self):
		if self.type == self.TEXT:
			self.timeout()
		if self.allmarked:
			self.deleteAllChars()
			self.allmarked = False
		else:
			self.deleteChar(self.currPos)
			if self.maxSize and self.overwrite:
				self.innerright()
		self.update()

	def deleteBackward(self):
		if self.type == self.TEXT:
			self.timeout()
		if self.allmarked:
			self.deleteAllChars()
			self.allmarked = False
		else:
			if self.currPos > 0:
				self.deleteChar(self.currPos-1)
				if not self.maxSize and self.offset > 0:
					self.offset -= 1
				self.currPos -= 1
		self.update()

	def deleteForward(self):
		if self.type == self.TEXT:
			self.timeout()
		if self.allmarked:
			self.deleteAllChars()
			self.allmarked = False
		else:
			self.deleteChar(self.currPos)
		self.update()

	def toggleOverwrite(self):
		if self.type == self.TEXT:
			self.timeout()
		self.overwrite = not self.overwrite
		self.update()

	def handleAscii(self, code):
		if self.type == self.TEXT:
			self.timeout()
		if self.allmarked:
			self.deleteAllChars()
			self.allmarked = False
		self.insertChar(unichr(code), self.currPos, False, False)
		self.innerright()
		self.update()

	def number(self, number):
		if self.type == self.TEXT:
			owr = self.lastKey == number
			newChar = self.getKey(number)
		elif self.type == self.PIN or self.type == self.NUMBER:
			owr = False
			newChar = str(number)
		if self.allmarked:
			self.deleteAllChars()
			self.allmarked = False
		self.insertChar(newChar, self.currPos, owr, False)
		if self.type == self.PIN or self.type == self.NUMBER:
			self.innerright()
		self.update()

	def char(self, char):
		if self.allmarked:
			self.deleteAllChars()
			self.allmarked = False
		self.insertChar(char)
		self.innerright()
		self.update()
