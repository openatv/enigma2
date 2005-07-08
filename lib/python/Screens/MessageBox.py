from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label

class MessageBox(Screen):
	def __init__(self, session, text):
		Screen.__init__(self, session)
		
		self["text"] = Label(text)

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"cancel": self.close
			})

