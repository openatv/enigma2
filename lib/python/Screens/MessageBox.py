import enigma

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList


class MessageBox(Screen):
	TYPE_YESNO = 0
	TYPE_INFO = 1
	TYPE_WARNING = 2
	TYPE_ERROR = 3

	def __init__(self, session, text, type=TYPE_YESNO, timeout=-1, close_on_any_key=False, default=True, enable_input=True, msgBoxID=None, picon=True, simple=False, wizard=False, list=None, skin_name=None, timeout_default=None):
		if not list: list = []
		if not skin_name: skin_name = []
		self.type = type
		Screen.__init__(self, session)
		self.skinName = ["MessageBox"]
		if wizard:
			from Components.config import config
			from Components.Pixmap import MultiPixmap
			self["rc"] = MultiPixmap()
			self["rc"].setPixmapNum(config.misc.rcused.value)		
			self.skinName = ["MessageBoxWizard"]

		if simple:
			self.skinName = ["MessageBoxSimple"]

		if isinstance(skin_name, str):
			self.skinName = [skin_name] + self.skinName

		self.msgBoxID = msgBoxID

		self["text"] = Label(_(text))
		self["Text"] = StaticText(_(text))
		self["selectedChoice"] = StaticText()

		self.text = _(text)
		self.close_on_any_key = close_on_any_key
		self.timeout_default = timeout_default

		self["ErrorPixmap"] = Pixmap()
		self["ErrorPixmap"].hide()
		self["QuestionPixmap"] = Pixmap()
		self["QuestionPixmap"].hide()
		self["InfoPixmap"] = Pixmap()
		self["InfoPixmap"].hide()

		self.timerRunning = False
		self.initTimeout(timeout)

		if picon:
			picon = type
			if picon == self.TYPE_ERROR:
				self["ErrorPixmap"].show()
			elif picon == self.TYPE_YESNO:
				self["QuestionPixmap"].show()
			elif picon == self.TYPE_INFO:
				self["InfoPixmap"].show()

		self.messtype = type
		if type == self.TYPE_YESNO:
			if list:
				self.list = list
			elif default:
				self.list = [ (_("yes"), True), (_("no"), False) ]
			else:
				self.list = [ (_("no"), False), (_("yes"), True) ]
		else:
			self.list = []

		self["list"] = MenuList(self.list)
		if self.list:
			self["selectedChoice"].setText(self.list[0][0])
		else:
			self["list"].hide()

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

	def autoResize(self):
		desktop_w = enigma.getDesktop(0).size().width()
		desktop_h = enigma.getDesktop(0).size().height()
		count = len(self.list)

		if not self["text"].text:
			textsize = (520, 0)
			listsize = (520, 25*count)
			if self["ErrorPixmap"].visible or self["QuestionPixmap"].visible or self["InfoPixmap"].visible:
				self["list"].instance.move(enigma.ePoint(65, 0))
			else:
				self["list"].instance.move(enigma.ePoint(0, 0))
			self["list"].instance.resize(enigma.eSize(*listsize))

		else:
			textsize = self["text"].getSize()
			if textsize[0] < textsize[1]:
				textsize = (textsize[1],textsize[0]+10)
			if textsize[0] > 520:
				textsize = (textsize[0], textsize[1]+25)
			else:
				textsize = (520, textsize[1]+25)
			listsize = (textsize[0], 25*count)

			self["text"].instance.resize(enigma.eSize(*textsize))
			if self["ErrorPixmap"].visible or self["QuestionPixmap"].visible or self["InfoPixmap"].visible:
				self["text"].instance.move(enigma.ePoint(65, 0))
			else:
				self["text"].instance.move(enigma.ePoint(10, 10))

			if self["ErrorPixmap"].visible or self["QuestionPixmap"].visible or self["InfoPixmap"].visible:
				self["list"].instance.move(enigma.ePoint(65, textsize[1]))
				wsizex = textsize[0]+65
			else:
				self["list"].instance.move(enigma.ePoint(0, textsize[1]))
				wsizex = textsize[0]
			self["list"].instance.resize(enigma.eSize(*listsize))

		wsizey = textsize[1]+listsize[1]
		wsize = (wsizex, wsizey)
		self.instance.resize(enigma.eSize(*wsize))
		self.instance.move(enigma.ePoint((desktop_w-wsizex)/2, (desktop_h-wsizey)/2))

	def initTimeout(self, timeout):
		self.timeout = timeout
		if timeout > 0:
			self.timer = enigma.eTimer()
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
			if self.origTitle:
				self.setTitle(_(self.origTitle))
			else:
				self.setTitle(self.origTitle)
			self.timerRunning = False

	def timerTick(self):
		if self.execing:
			self.timeout -= 1
			if self.origTitle is None:
				self.origTitle = self.instance.getTitle()
			if self.origTitle:
				self.setTitle(_(self.origTitle) + " (" + str(self.timeout) + ")")
			else:
				self.setTitle(self.origTitle + " (" + str(self.timeout) + ")")
			if self.timeout == 0:
				self.timer.stop()
				self.timerRunning = False
				self.timeoutCallback()

	def timeoutCallback(self):
		print "Timeout!"
		if self.timeout_default is not None:
			self.close(self.timeout_default)
		else:
			self.ok()

	def cancel(self):
		if self["list"].list:
			for l in self["list"].list:
				if l[0].lower() == _('no') or l[0].lower() == _('false'):
					if len(l) > 2:
						l[2](None)
					else:
						self.close(False)
					break
		else:
			self.close(False)

	def ok(self):
		if self["list"].getCurrent():
			self.goEntry(self["list"].getCurrent())
		else:
			self.close(True)

	def goEntry(self, entry=None):
		if not entry: entry = []
		if entry and len(entry) > 3 and isinstance(entry[1], str) and entry[1] == "CALLFUNC":
			arg = entry[3]
			entry[2](arg)
		elif entry and len(entry) > 2 and isinstance(entry[1], str) and entry[1] == "CALLFUNC":
			entry[2](None)
		elif entry:
			self.close(entry[1])
		else:
			self.close(False)

	def alwaysOK(self):
		if self["list"].list:
			for l in self["list"].list:
				if l[0].lower() == _('yes') or l[0].lower() == _('true'):
					if len(l) > 2:
						self.goEntry(l)
					else:
						self.close(True)
					break
		else:
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
