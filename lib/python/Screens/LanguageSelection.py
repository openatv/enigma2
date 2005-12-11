from Screen import Screen

from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Language import language
from Components.LanguageList import *
from Components.config import config


class LanguageSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self.list = []
		list = language.getLanguageList()
		for x in language.lang:
			print x
			self.list.append(LanguageEntryComponent(x[2], x[0]))

		self["list"] = LanguageList(self.list)
		
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
		config.osd.language.value = self["list"].l.getCurrentSelectionIndex()
		config.osd.language.save()
