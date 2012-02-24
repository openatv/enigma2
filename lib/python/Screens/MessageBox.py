from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList
from enigma import eTimer

class MessageBox(Screen):
	TYPE_YESNO = 0
	TYPE_INFO = 1
	TYPE_WARNING = 2
	TYPE_ERROR = 3

	def __init__(self, session, text, type = TYPE_YESNO, timeout = -1, close_on_any_key = False, default = True, enable_input = True, msgBoxID = None, picon = None, simple = False):
		self.type = type
		Screen.__init__(self, session)

		if simple:
			self.skinName="MessageBoxSimple"
		
		self.msgBoxID = msgBoxID

 		self["text"] = Label(text)
		self["Text"] = StaticText(text)
		self["selectedChoice"] = StaticText()

		self.text = text
		self.close_on_any_key = close_on_any_key

		self["ErrorPixmap"] = Pixmap()
		self["QuestionPixmap"] = Pixmap()
		self["InfoPixmap"] = Pixmap()
		self.timerRunning = False
		self.initTimeout(timeout)

		self.list = []
		picon = picon or type
		if picon != self.TYPE_ERROR:
			self["ErrorPixmap"].hide()
		if picon != self.TYPE_YESNO:
			self["QuestionPixmap"].hide()
		if picon != self.TYPE_INFO:
			self["InfoPixmap"].hide()

		if type == self.TYPE_YESNO:
			if default == True:
				self.list = [ (_("yes"), 0), (_("no"), 1) ]
			else:
				self.list = [ (_("no"), 1), (_("yes"), 0) ]
		
		if self.list:
			self["selectedChoice"].setText(self.list[0][0])
		self["list"] = MenuList(self.list)

		if enable_input:
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

	def initTimeout(self, timeout):
		self.timeout = timeout
		if timeout > 0:
			self.timer = eTimer()
			self.timer.callback.append(self.timerTick)
			self.onExecBegin.append(self.startTimer)
			self.origTitle = None
			if self.execing:
				self.timerTick()
			else:
				self.onShown.append(self.__onShown)
			self.timerRunning = True
		else:
			self.timerRunning = False

	def __onShown(self):
		self.onShown.remove(self.__onShown)
		self.timerTick()

	def startTimer(self):
		self.timer.start(1000)

	def stopTimer(self):
		if self.timerRunning:
			del self.timer
			self.onExecBegin.remove(self.startTimer)
			self.setTitle(self.origTitle)
			self.timerRunning = False

	def timerTick(self):
		if self.execing:
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
		if self.list:
			self["selectedChoice"].setText(self["list"].getCurrent()[0])
		self.stopTimer()

	def __repr__(self):
		return str(type(self)) + "(" + self.text + ")"
