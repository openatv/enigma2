from Screen import Screen

from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Language import language

class LanguageSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self.list = []
		list = language.getLanguageList()
		for x in list:
			self.list.append((x, None))

		self["list"] = MenuList(self.list)
		
		self["actions"] = ActionMap(["OkCancelActions"], 
		{
			"ok": self.save,
			"cancel": self.close
		})
		
	def save(self):
		self.run()
		self.close()
	
	def run(self):
		language.activateLanguage(self["list"].l.getCurrentSelectionIndex())
