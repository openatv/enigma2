from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Button import Button
from enigma import eSize, ePoint

class MessageBox(Screen):
	def __init__(self, session, text):
		Screen.__init__(self, session)
		
		self["text"] = Label(text)
		
		self["key_green"] = Button("OK")
		self["key_red"] = Button("Exit")

		self["actions"] = ActionMap(["MsgBoxActions"], 
			{
				"cancel": self.cancel,
				"ok": self.ok
			})
			
	
	def cancel(self):
		self.close(False)
	
	def ok(self):
		self.close(True)
