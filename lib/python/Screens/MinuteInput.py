from Screens.Screen import Screen
from Components.ActionMap import NumberActionMap
from Components.Input import Input

class MinuteInput(Screen):
	def __init__(self, session, basemins = 5):
		Screen.__init__(self, session)

		self["minutes"] = Input(str(basemins), type=Input.NUMBER)

		self["actions"] = NumberActionMap([ "InputActions" , "MinuteInputActions", "TextEntryActions", "KeyboardInputActions" ],
		{
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal,
			"left": self.left,
			"right": self.right,
			"home": self.home,
			"end": self.end,
			"deleteForward": self.deleteForward,
			"deleteBackward": self.deleteBackward,
			"up": self.up,
			"down": self.down,
			"ok": self.ok,
			"cancel": self.cancel
		})

	def keyNumberGlobal(self, number):
		self["minutes"].number(number)
		pass

	def left(self):
		self["minutes"].left()

	def right(self):
		self["minutes"].right()

	def home(self):
		self["minutes"].home()

	def end(self):
		self["minutes"].end()

	def deleteForward(self):
		self["minutes"].delete()

	def deleteBackward(self):
		self["minutes"].deleteBackward()

	def up(self):
		self["minutes"].up()

	def down(self):
		self["minutes"].down()

	def ok(self):
		self.close(int(self["minutes"].getText()))

	def cancel(self):
		self.close(0)
