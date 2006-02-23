from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Button import Button
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from enigma import eSize, ePoint

class MessageBox(Screen):
	TYPE_YESNO = 0
	TYPE_INFO = 1
	TYPE_WARNING = 2
	TYPE_ERROR = 3
	
	def __init__(self, session, text, type = TYPE_YESNO):
		self.type = type
		Screen.__init__(self, session)
		
		self["text"] = Label(text)
		
		self["ErrorPixmap"] = Pixmap()
		self["QuestionPixmap"] = Pixmap()
		self["InfoPixmap"] = Pixmap()
		
		self.list = []
		if type != self.TYPE_ERROR:
			self.onShown.append(self["ErrorPixmap"].hideWidget)
		elif type != self.TYPE_YESNO:
			self.onShown.append(self["QuestionPixmap"].hideWidget)
		elif type != self.TYPE_INFO:
			self.onShown.append(self["InfoPixmap"].hideWidget)
			
		if type == self.TYPE_YESNO:
			self.list = [ (_("yes"), 0), (_("no"), 1) ]


		self["list"] = MenuList(self.list)
		
		self["actions"] = ActionMap(["MsgBoxActions"], 
			{
				"cancel": self.cancel,
				"ok": self.ok,
				"alwaysOK": self.alwaysOK
			})
			
	
	def cancel(self):
		self.close(False)
	
	def ok(self):
		if self.type == self.TYPE_YESNO:
			self.close(self["list"].getCurrent()[1] == 0)
		else:
			self.close(True)

	def alwaysOK(self):
		self.close(True)
