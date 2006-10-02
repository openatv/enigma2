from Screen import Screen
from Components.Label import Label

class NumericalTextInputHelpDialog(Screen):
	def __init__(self, session, textinput):
		Screen.__init__(self, session)
		for x in range(1, 10):
			self["key%d" % x] = Label(text=textinput.mapping[x].encode("utf-8"))
		self.last_marked = 0

	def update(self, textinput):
		if 1 <= self.last_marked <= 9:
			self["key%d" % self.last_marked].setMarkedPos(-1)
		if 1 <= textinput.lastKey <= 9:
			self["key%d" % textinput.lastKey].setMarkedPos(textinput.pos)
			self.last_marked = textinput.lastKey
