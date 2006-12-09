from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Button import Button
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from enigma import eSize, ePoint, eTimer

class MessageBox(Screen):
	TYPE_YESNO = 0
	TYPE_INFO = 1
	TYPE_WARNING = 2
	TYPE_ERROR = 3
	
	def __init__(self, session, text, type = TYPE_YESNO, timeout = -1, close_on_any_key = False):
		self.type = type
		Screen.__init__(self, session)
		
		self["text"] = Label(text)
		
		self.text = text
		self.close_on_any_key = close_on_any_key
		
		self["ErrorPixmap"] = Pixmap()
		self["QuestionPixmap"] = Pixmap()
		self["InfoPixmap"] = Pixmap()
		self.timerRunning = False
		if timeout > 0:
			self.timer = eTimer()
			self.timer.timeout.get().append(self.timerTick)
			self.timer.start(1000)
			self.origTitle = None
			self.onShown.append(self.timerTick)
			self.timerRunning = True
		self.timeout = timeout
		
		self.list = []
		if type != self.TYPE_ERROR:
			self["ErrorPixmap"].hide()
		if type != self.TYPE_YESNO:
			self["QuestionPixmap"].hide()
		if type != self.TYPE_INFO:
			self["InfoPixmap"].hide()
			
		if type == self.TYPE_YESNO:
			self.list = [ (_("yes"), 0), (_("no"), 1) ]


		self["list"] = MenuList(self.list)
		
		self["actions"] = ActionMap(["MsgBoxActions", "DirectionActions"], 
			{
				"cancel": self.cancel,
				"ok": self.ok,
				"alwaysOK": self.alwaysOK,
				"up": self.up,
				"down": self.down,
				"left": self.left,
				"right": self.right,
				"upRepeated": self.up,
				"downRepeated": self.down,
				"leftRepeated": self.left,
				"rightRepeated": self.right
			}, -1)
			
	
	def timerTick(self):
		self.timeout -= 1
		if self.origTitle is None:
			self.origTitle = self.instance.getTitle()
		self.setTitle(self.origTitle + " (" + str(self.timeout) + ")")
		if self.timeout == 0:
			self.timer.stop()
			self.timerRunning = False
			self.timeoutCallback()
			
	def timeoutCallback(self):
		print "Timeout!"
		self.ok()
	
	def cancel(self):
		self.close(False)
	
	def ok(self):
		if self.type == self.TYPE_YESNO:
			self.close(self["list"].getCurrent()[1] == 0)
		else:
			self.close(True)

	def alwaysOK(self):
		self.close(True)

	def up(self):
		self.move(self["list"].instance.moveUp)
		
	def down(self):
		self.move(self["list"].instance.moveDown)

	def left(self):
		self.move(self["list"].instance.pageUp)
		
	def right(self):
		self.move(self["list"].instance.pageDown)

	def move(self, direction):
		if self.close_on_any_key:
			self.close(True)

		self["list"].instance.moveSelection(direction)
		if self.timerRunning:
			self.timer.stop()
			self.setTitle(self.origTitle)
			self.timerRunning = False

	def __repr__(self):
		return str(type(self)) + "(" + self.text + ")"
