from six import PY2

from enigma import eLabel

from Components.GUIComponent import GUIComponent
from Components.VariableText import VariableText
from Tools.NumericalTextInput import NumericalTextInput

pyunichr = unichr if PY2 else chr


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

	def __len__(self):
		return len(self.text)  #NOSONAR

	def getText(self):
		return self.textU.encode("UTF-8", "ignore") if PY2 else self.textU

	def setText(self, text):
		if len(text):
			self.textU = text.decode("UTF-8", "ignore") if isinstance(text, bytes) else text
		else:
			self.currPos = 0
			self.textU = u""
		self.update()

	def update(self):
		if self.visibleWidth:
			if self.currPos < self.offset:
				self.offset = self.currPos
			if self.currPos >= self.offset + self.visibleWidth:
				self.offset = self.currPos - self.visibleWidth
				if self.currPos != len(self.textU):
					self.offset += 1
			if self.offset > 0 and self.offset + self.visibleWidth > len(self.textU):
				self.offset = max(0, len(self.textU) - self.visibleWidth)
		if self.allMarked:
			self.setMarkedPos(-2)
		else:
			self.setMarkedPos(self.currPos - self.offset)
		# Use non-breaking spaces, as right alignment removes trailing spaces,
		# causing the cursor to disappear at the end.
		if self.visibleWidth:
			if self.type == self.PIN:
				self.text = ""
				for x in self.textU[self.offset:self.offset + self.visibleWidth]:
					self.text += (x == " " and u"\u00A0" or "*")
			else:
				self.text = self.textU[self.offset:self.offset + self.visibleWidth].encode("UTF-8", "ignore") + u"\u00A0" if PY2 else self.textU[self.offset:self.offset + self.visibleWidth] + u"\u00A0"
		else:
			if self.type == self.PIN:
				self.text = ""
				for x in self.textU:
					self.text += (x == " " and u"\u00A0" or "*")
			else:
				self.text = self.textU.encode("UTF-8", "ignore") + u"\u00A0" if PY2 else self.textU + u"\u00A0"

	def createWidget(self, parent):
		if self.allMarked:
			return eLabel(parent, -2)
		return eLabel(parent, self.currPos - self.offset)

	def getSize(self):
		size = self.instance.calculateSize()
		return (size.width(), size.height())

	def markAll(self):
		self.allMarked = True
		self.update()

	def innerRight(self):
		if self.allMarked:
			self.currPos = 0
			self.allMarked = False
		elif self.maxSize:
			if self.currPos < len(self.textU) - 1:
				self.currPos += 1
		else:
			if self.currPos < len(self.textU):
				self.currPos += 1

	def up(self):
		self.allMarked = False
		if self.type == self.TEXT:
			self.timeout()
		if self.currPos == len(self.textU) or self.textU[self.currPos] == "9" or self.textU[self.currPos] == " ":
			newNumber = "0"
		else:
			newNumber = str(int(self.textU[self.currPos]) + 1)
		self.textU = self.textU[0:self.currPos] + newNumber + self.textU[self.currPos + 1:]
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
			self.currPos = len(self.textU) - 1 if self.maxSize else len(self.textU)
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
		self.currPos = len(self.text) - 1 if self.maxSize else len(self.text)
		self.update()

	def down(self):
		self.allMarked = False
		if self.type == self.TEXT:
			self.timeout()
		if self.currPos == len(self.textU) or self.textU[self.currPos] == "0" or self.textU[self.currPos] == " ":
			newNumber = "9"
		else:
			newNumber = str(int(self.textU[self.currPos]) - 1)
		self.textU = self.textU[0:self.currPos] + newNumber + self.textU[self.currPos + 1:]
		self.update()

	def insertChar(self, ch, pos=False, owr=False, ins=False):
		if isinstance(ch, bytes):
			ch = ch.decode("UTF-8", "ignore")
		n = len(ch)
		if not pos:
			pos = self.currPos
		if ins and not self.maxSize:
			self.textU = self.textU[0:pos] + ch + self.textU[pos:]
		elif owr or self.overwrite:
			self.textU = self.textU[0:pos] + ch + self.textU[pos + n:]
		elif self.maxSize:
			self.textU = self.textU[0:pos] + ch + self.textU[pos:-n]
		else:
			self.textU = self.textU[0:pos] + ch + self.textU[pos:]
		self.currPos += n - 1

	def deleteChar(self, pos):
		if not self.maxSize:
			self.textU = self.textU[0:pos] + self.textU[pos + 1:]
		elif self.overwrite:
			self.textU = self.textU[0:pos] + u" " + self.textU[pos + 1:]
		else:
			self.textU = self.textU[0:pos] + self.textU[pos + 1:] + u" "

	def deleteAllChars(self):
		self.textU = u" " * len(self.textU) if self.maxSize else u""
		self.currPos = 0

	def tab(self):
		if self.type == self.TEXT:
			self.timeout()
		if self.allMarked:
			self.deleteAllChars()
			self.allMarked = False
		else:
			self.insertChar(u" ", self.currPos, False, True)
			self.innerRight()
		self.update()

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
		else:
			if self.currPos > 0:
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

	def toggleOverwrite(self):
		if self.type == self.TEXT:
			self.timeout()
		self.overwrite = not self.overwrite
		self.update()

	def handleAscii(self, code):
		if self.type == self.TEXT:
			self.timeout()
		if self.allMarked:
			self.deleteAllChars()
			self.allMarked = False
		self.insertChar(pyunichr(code), self.currPos, False, False)
		self.innerRight()
		self.update()

	def number(self, number):  #NOSONAR
		if self.type == self.TEXT:
			owr = self.lastKey == number
			newChar = self.getKey(number)
		elif self.type == self.PIN or self.type == self.NUMBER:
			owr = False
			newChar = str(number)
		if self.allMarked:
			self.deleteAllChars()
			self.allMarked = False
		self.insertChar(newChar, self.currPos, owr, False)
		if self.type == self.PIN or self.type == self.NUMBER:
			self.innerRight()
		self.update()

	def char(self, char):
		if self.allMarked:
			self.deleteAllChars()
			self.allMarked = False
		self.insertChar(char)
		self.innerRight()
		self.update()
