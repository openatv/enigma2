from Screen import Screen

from Components.MenuList import MenuList
from Components.ActionMap import ActionMap

class LanguageSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self.list = []
		self.list.append(("English", None))
		self.list.append(("German", None))
		self["list"] = MenuList(self.list)
		
		self["actions"] = ActionMap(["OkCancelActions"], 
		{
			"ok": self.save,
			"cancel": self.close
		})
		
	def save(self):
		pass
	
	def run(self):
		print "select the language here"