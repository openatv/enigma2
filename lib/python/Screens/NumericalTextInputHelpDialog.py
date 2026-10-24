from Components.Label import Label
from Screens.Screen import Screen


class NumericalTextInputHelpDialog(Screen):
	def __init__(self, session, textInput):
		Screen.__init__(self, session)
		self["help1"] = Label(text="<")
		self["help2"] = Label(text=">")
		for x in (1, 2, 3, 4, 5, 6, 7, 8, 9, 0):
			text = textInput.mapping[x]
			self[f"key{x}"] = Label(text.decode(encoding="utf-8", errors="strict") if isinstance(text, bytes) else text)
		self.lastMarked = 0

	def update(self, textInput):
		if 0 <= self.lastMarked <= 9:
			self[f"key{self.lastMarked}"].setMarkedPos(-1)
		if 0 <= textInput.lastKey <= 9:
			self[f"key{textInput.lastKey}"].setMarkedPos(textInput.pos)
			self.lastMarked = textInput.lastKey
