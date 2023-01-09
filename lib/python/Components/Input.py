from enigma import eLabel

from Components.GUIComponent import GUIComponent
from Components.VariableText import VariableText
from Tools.NumericalTextInput import NumericalTextInput


class Input(VariableText, GUIComponent, NumericalTextInput):
	TEXT = 0
	PIN = 1
	NUMBER = 2

	def __init__(self, text="", maxSize=False, visible_width=False, type=TEXT, currPos=0, allMarked=True):
		VariableText.__init__(self)
		GUIComponent.__init__(self)
		NumericalTextInput.__init__(self, self.right)
		self.maxSize = maxSize
		self.visibleWidth = visible_width
		self.type = type
		self.currPos = currPos
		self.allMarked = allMarked and (text != "") and (type != self.PIN)
		self.offset = 0
		self.overwrite = maxSize
		self.setText(text)

	def __len__(self):  # NOTE: self.text is a property of VariableText!!!
		return len(self.text)  #NOSONAR

	def createWidget(self, parent):
		if self.allMarked:
			return eLabel(parent, -2)
		return eLabel(parent, self.currPos - self.offset)

	def getSize(self):
		size = self.instance.calculateSize()
		return (size.width(), size.height())

	def getText(self):
		return self.textBuffer

	def setText(self, text):
		if text:
			self.textBuffer = text.decode("UTF-8", "ignore") if isinstance(text, bytes) else text
		else:
			self.currPos = 0
			self.textBuffer = ""
		self.update()

	def update(self):  # NOTE: self.text is a property of VariableText!!!
		if self.visibleWidth:
			if self.currPos < self.offset:
				self.offset = self.currPos
			if self.currPos >= self.offset + self.visibleWidth:
				self.offset = self.currPos - self.visibleWidth
				if self.currPos != len(self.textBuffer):
					self.offset += 1
			if self.offset > 0 and self.offset + self.visibleWidth > len(self.textBuffer):
				self.offset = max(0, len(self.textBuffer) - self.visibleWidth)
		if self.allMarked:
			self.setMarkedPos(-2)
		else:
			self.setMarkedPos(self.currPos - self.offset)
		# Use non-breaking spaces, as right alignment removes trailing spaces,
		# causing the cursor to disappear at the end.
		visibleText = self.textBuffer[self.offset:self.offset + self.visibleWidth] if self.visibleWidth else self.textBuffer
		if self.type == self.PIN:
			text = []
			for character in visibleText:
				text.append(character == " " and "\u00A0" or "*")
			self.text = "".join(text)
		else:
			self.text = "%s\u00A0" % visibleText

	def markAll(self):
		self.allMarked = True
		self.update()

	def up(self):
		self.allMarked = False
		if self.type == self.TEXT:
			self.timeout()
		if self.currPos == len(self.textBuffer) or self.textBuffer[self.currPos] == "9" or self.textBuffer[self.currPos] == " ":
			newNumber = "0"
		else:
			newNumber = str(int(self.textBuffer[self.currPos]) + 1)
		self.textBuffer = self.textBuffer[0:self.currPos] + newNumber + self.textBuffer[self.currPos + 1:]
		self.update()

	def home(self):
		self.allMarked = False
		if self.type == self.TEXT:
			self.timeout()
		self.currPos = 0
		self.update()

	def left(self):
		if self.type == self.TEXT:
			self.timeout()
		if self.allMarked:
			self.currPos = len(self.textBuffer) - 1 if self.maxSize else len(self.textBuffer)
			self.allMarked = False
		elif self.currPos > 0:
			self.currPos -= 1
		self.update()

	def right(self):
		if self.type == self.TEXT:
			self.timeout()
		self.innerRight()
		self.update()

	def end(self):
		self.allMarked = False
		if self.type == self.TEXT:
			self.timeout()
		self.currPos = len(self.textBuffer) - 1 if self.maxSize else len(self.textBuffer)
		self.update()

	def down(self):
		self.allMarked = False
		if self.type == self.TEXT:
			self.timeout()
		if self.currPos == len(self.textBuffer) or self.textBuffer[self.currPos] == "0" or self.textBuffer[self.currPos] == " ":
			newNumber = "9"
		else:
			newNumber = str(int(self.textBuffer[self.currPos]) - 1)
		self.textBuffer = "%s%s%s" % (self.textBuffer[0:self.currPos], newNumber, self.textBuffer[self.currPos + 1:])
		self.update()

	def innerRight(self):
		if self.allMarked:
			self.currPos = 0
			self.allMarked = False
		elif self.maxSize:
			if self.currPos < len(self.textBuffer) - 1:
				self.currPos += 1
		elif self.currPos < len(self.textBuffer):
			self.currPos += 1

	def tab(self):
		if self.type == self.TEXT:
			self.timeout()
		if self.allMarked:
			self.deleteAllChars()
			self.allMarked = False
		else:
			self.insertChar(" ", self.currPos, False, True)
			self.innerRight()
		self.update()

	def insertChar(self, character, pos=False, overwrite=False, ins=False):
		if isinstance(character, bytes):
			character = character.decode("UTF-8", "ignore")
		length = len(character)
		if not pos:
			pos = self.currPos
		if ins and not self.maxSize:
			endText = self.textBuffer[pos:]
		elif overwrite or self.overwrite:
			endText = self.textBuffer[pos + length:]
		elif self.maxSize:
			endText = self.textBuffer[pos:-length]
		else:
			endText = self.textBuffer[pos:]
		self.textBuffer = "%s%s%s" % (self.textBuffer[0:pos], character, endText)
		self.currPos += length - 1

	def delete(self):
		if self.type == self.TEXT:
			self.timeout()
		if self.allMarked:
			self.deleteAllChars()
			self.allMarked = False
		else:
			self.deleteChar(self.currPos)
			if self.maxSize and self.overwrite:
				self.innerRight()
		self.update()

	def deleteBackward(self):
		if self.type == self.TEXT:
			self.timeout()
		if self.allMarked:
			self.deleteAllChars()
			self.allMarked = False
		elif self.currPos > 0:
			self.deleteChar(self.currPos - 1)
			if not self.maxSize and self.offset > 0:
				self.offset -= 1
			self.currPos -= 1
		self.update()

	def deleteForward(self):
		if self.type == self.TEXT:
			self.timeout()
		if self.allMarked:
			self.deleteAllChars()
			self.allMarked = False
		else:
			self.deleteChar(self.currPos)
		self.update()

	def deleteAllChars(self):
		self.textBuffer = " " * len(self.textBuffer) if self.maxSize else ""
		self.currPos = 0

	def deleteChar(self, pos):
		if not self.maxSize:
			layout = "%s%s"
		elif self.overwrite:
			layout = "%s %s"
		else:
			layout = "%s%s "
		self.textBuffer = layout % (self.textBuffer[0:pos], self.textBuffer[pos + 1:])

	def toggleOverwrite(self):
		if self.type == self.TEXT:
			self.timeout()
		self.overwrite = not self.overwrite
		self.update()

	def handleAscii(self, asciiCode):
		if self.type == self.TEXT:
			self.timeout()
		if self.allMarked:
			self.deleteAllChars()
			self.allMarked = False
		self.insertChar(chr(asciiCode), self.currPos, False, False)
		self.innerRight()
		self.update()

	def char(self, character):
		if self.allMarked:
			self.deleteAllChars()
			self.allMarked = False
		self.insertChar(character)
		self.innerRight()
		self.update()

	def number(self, digit):
		if self.type == self.TEXT:
			overwrite = self.lastKey == digit
			character = self.getKey(digit)
		elif self.type == self.PIN or self.type == self.NUMBER:
			overwrite = False
			character = str(digit)
		if self.allMarked:
			self.deleteAllChars()
			self.allMarked = False
		self.insertChar(character, self.currPos, overwrite, False)
		if self.type == self.PIN or self.type == self.NUMBER:
			self.innerRight()
		self.update()
