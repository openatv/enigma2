from Screen import Screen

from Components.ActionMap import ActionMap
from Components.Language import language
from Components.config import config
from Components.Sources.List import List

from Tools.Directories import *

from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT
from Tools.LoadPixmap import LoadPixmap

def LanguageEntryComponent(file, name, index):
	res = [ index ]
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 80, 10, 200, 50, 0, RT_HALIGN_LEFT ,name))
	png = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "countries/" + file + ".png"))
	if png == None:
		png = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "countries/missing.png"))
	res.append((eListboxPythonMultiContent.TYPE_PIXMAP, 10, 5, 60, 40, png))
	
	return res

class LanguageSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self.oldActiveLanguage = language.getActiveLanguage()

		self.list = []
		self["languages"] = List(self.list, item_height=50, fonts = [gFont("Regular", 20)])
		self["languages"].onSelectionChanged.append(self.changed)

		self.updateList()
		self.onLayoutFinish.append(self.selectActiveLanguage)

		self["actions"] = ActionMap(["OkCancelActions"], 
		{
			"ok": self.save,
			"cancel": self.cancel,
		}, -1)

	def selectActiveLanguage(self):
		activeLanguage = language.getActiveLanguage()
		pos = 0
		for x in self.list:
			if x[0] == activeLanguage:
				self["languages"].index = pos
				break
			pos += 1

	def save(self):
		self.run()
		self.close()

	def cancel(self):
		language.activateLanguage(self.oldActiveLanguage)
		self.close()

	def run(self):
		print "updating language..."
		lang = self["languages"].getCurrent()[0]
		language.activateLanguage(lang)
		config.osd.language.value = lang
		config.osd.language.save()
		config.misc.languageselected.value = 0
		config.misc.languageselected.save()
		self.setTitle(_("Language selection"))
		print "ok"

	def updateList(self):
		print "update list"
		first_time = len(self.list) == 0

		self.list = []
		if len(language.getLanguageList()) == 0: # no language available => display only english
			self.list.append(LanguageEntryComponent("en", _("English"), "en_EN"))
		else:
			for x in language.getLanguageList():
				self.list.append(LanguageEntryComponent(file = x[1][3].lower(), name = _(x[1][0]), index = x[0]))
		#self.list.sort(key=lambda x: x[1][7])
		
		print "updateList"
		if first_time:
			self["languages"].list = self.list
		else:
			self["languages"].updateList(self.list)
		print "done"

	def changed(self):
		self.run()
		self.updateList()
