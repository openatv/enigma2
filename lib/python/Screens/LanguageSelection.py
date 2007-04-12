from Screen import Screen

from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Language import language
from Components.LanguageList import *
from Components.config import config


class LanguageSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self.oldActiveLanguage = language.getActiveLanguage()

		self.list = []
		self["list"] = LanguageList(self.list)
		self.updateList()
		self.onLayoutFinish.append(self.selectActiveLanguage)

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], 
		{
			"ok": self.save,
			"cancel": self.cancel,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right
		}, -1)

	def selectActiveLanguage(self):
		activeLanguage = language.getActiveLanguage()
		pos = 0
		for x in self.list:
			if x[0] == activeLanguage:
				self["list"].instance.moveSelectionTo(pos)
				break
			pos += 1

	def save(self):
		self.run()
		self.close()

	def cancel(self):
		language.activateLanguage(self.oldActiveLanguage)
		self.close()

	def run(self):
		language.activateLanguage(self["list"].l.getCurrentSelection()[0])
		config.osd.language.value = self["list"].l.getCurrentSelection()[0]
		config.osd.language.save()
		config.misc.languageselected.value = 0
		config.misc.languageselected.save()
		self.setTitle(_("Language selection"))

	def updateList(self):
		self.list = []
		if len(language.getLanguageList()) == 0: # no language available => display only english
			self.list.append(LanguageEntryComponent("en", _("English"), "en_EN"))
		else:
			for x in language.getLanguageList():
				self.list.append(LanguageEntryComponent(file = x[1][3].lower(), name = _(x[1][0]), index = x[0]))
		#self.list.sort(key=lambda x: x[1][7])
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
