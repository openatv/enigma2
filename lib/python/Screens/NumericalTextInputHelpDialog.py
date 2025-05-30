from Screens.Screen import Screen
from Components.Label import Label


class NumericalTextInputHelpDialog(Screen):
	def __init__(self, session, textinput):
		Screen.__init__(self, session)
		self["help1"] = Label(text="<")
		self["help2"] = Label(text=">")

		def ensure_str(result):
			if isinstance(result, bytes):
				result = result.decode(encoding='utf-8', errors='strict')
			return result

		for x in (1, 2, 3, 4, 5, 6, 7, 8, 9, 0):
			self["key%d" % x] = Label(text=ensure_str(textinput.mapping[x]))
		self.last_marked = 0

	def update(self, textinput):
		if 0 <= self.last_marked <= 9:
			self["key%d" % self.last_marked].setMarkedPos(-1)
		if 0 <= textinput.lastKey <= 9:
			self["key%d" % textinput.lastKey].setMarkedPos(textinput.pos)
			self.last_marked = textinput.lastKey
