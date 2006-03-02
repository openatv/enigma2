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
		self.onLayoutFinish.append(self.selectActiveLanguage)
				
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], 
		{
			"ok": self.save,
			"cancel": self.close,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right
		}, -1)
		
	def selectActiveLanguage(self):
		self["list"].instance.moveSelectionTo(language.activeLanguage)
		
	def save(self):
		self.run()
		self.close()
	
	def run(self):
		language.activateLanguage(self["list"].l.getCurrentSelectionIndex())
		config.osd.language.value = self["list"].l.getCurrentSelectionIndex()
		config.osd.language.save()
		self.setTitle(_("Language selection"))

	def updateList(self):
		self.list = []
		if len(language.lang) == 0: # no language available => display only english
			self.list.append(LanguageEntryComponent("en", _("English")))
		else:
			for x in language.lang:
				self.list.append(LanguageEntryComponent(x[3].lower(), _(x[0])))
		
		self["list"].l.setList(self.list)

	def up(self):
		self["list"].instance.moveSelection(self["list"].instance.moveUp)
		self.run()
		self.updateList()
		
	def down(self):
		self["list"].instance.moveSelection(self["list"].instance.moveDown)
		self.run()
		self.updateList()

	def left(self):
		self["list"].instance.moveSelection(self["list"].instance.pageUp)
		self.run()
		self.updateList()
		
	def right(self):
		self["list"].instance.moveSelection(self["list"].instance.pageDown)
		self.run()
		self.updateList()