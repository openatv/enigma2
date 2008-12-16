from Screens.Screen import Screen

from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.ScrollLabel import ScrollLabel

class TextBox(Screen):
	def __init__(self, session, text = ""):
		Screen.__init__(self, session)
		
		self.text = text
		self["text"] = ScrollLabel(self.text)
		
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], 
				{
					"cancel": self.cancel,
					"ok": self.ok,
					"up": self["text"].pageUp,
					"down": self["text"].pageDown,
				}, -1)
		
	def ok(self):
		self.close()
	
	def cancel(self):
		self.close()
