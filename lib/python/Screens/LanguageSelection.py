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
		self["list"] = LanguageList(self.list)
		self.updateList()
		
		self["actions"] = ActionMap(["ListboxActions", "OkCancelActions"], 
		{
			"ok": self.save,
			"cancel": self.close,
			"moveUp": self.up,
			"moveDown": self.down
		})
		
	def save(self):
		self.run()
		self.close()
	
	def run(self):
		language.activateLanguage(self["list"].l.getCurrentSelectionIndex())
		config.osd.language.value = self["list"].l.getCurrentSelectionIndex()
		config.osd.language.save()

	def updateList(self):
		self.list = []
		if len(language.lang) == 0: # no language available => display only english
			self.list.append(LanguageEntryComponent("en", _("English")))
		else:
			for x in language.lang:
				self.list.append(LanguageEntryComponent(x[2], _(x[0])))
		
		self["list"].l.setList(self.list)
		
	def up(self):
		print "up"
		
	def down(self):
		print "down"