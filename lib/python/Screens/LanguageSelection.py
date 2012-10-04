import gettext

from Screen import Screen

from Components.ActionMap import ActionMap
from Components.Language import language
from Components.config import config
from Components.Sources.List import List
from Components.Label import Label
from Components.Pixmap import Pixmap

from Screens.Rc import Rc

from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN, SCOPE_LANGUAGE

from Tools.LoadPixmap import LoadPixmap

def LanguageEntryComponent(file, name, index):
	png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/" + index + ".png"))
	if png == None:
		png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/" + file + ".png"))
		if png == None:
			png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/missing.png"))
	res = (index, name, png)
	return res

class LanguageSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self.oldActiveLanguage = language.getActiveLanguage()
		self.catalog = language.getActiveCatalog()

		self.list = []
		self["languages"] = List(self.list)
		self["languages"].onSelectionChanged.append(self.changed)

		self.updateList()
		self.onLayoutFinish.append(self.selectActiveLanguage)

		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Save"))

		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.save,
			"cancel": self.cancel,
			"red": self.cancel,
			"green": self.save,
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

	def run(self, justlocal = False):
		print "updating language..."
		lang = self["languages"].getCurrent()[0]
		if lang != config.osd.language.setValue():
			config.osd.language.setValue(lang)
			config.osd.language.save()
			self.catalog = gettext.translation('enigma2', resolveFilename(SCOPE_LANGUAGE, ""), languages=[config.osd.language.value])
		self.setTitle(self.catalog.gettext("Language selection"))

		if justlocal:
			return

		language.activateLanguage(lang)
		config.misc.languageselected.value = 0
		config.misc.languageselected.save()
		print "ok"

	def updateList(self):
		languageList = language.getLanguageList()
		if not languageList: # no language available => display only english
			list = [ LanguageEntryComponent("en_GB", "English (UK)", "en_GB_GB") ]
		else:
			list = [ LanguageEntryComponent(file = x[1][2].lower(), name = x[1][0], index = x[0]) for x in languageList]
		self.list = list
		self["languages"].list = list

	def changed(self):
		self.run(justlocal = True)

class LanguageWizard(LanguageSelection, Rc):
	def __init__(self, session):
		LanguageSelection.__init__(self, session)
		Rc.__init__(self)
		self.onLayoutFinish.append(self.selectKeys)

		self["wizard"] = Pixmap()
		self["text"] = Label()
		self.setText()

	def selectKeys(self):
		self.clearSelectedKeys()
		self.selectKey("UP")
		self.selectKey("DOWN")

	def changed(self):
		self.run(justlocal = True)
		self.setText()

	def setText(self):
		self["text"].setText(self.catalog.gettext("Please use the UP and DOWN keys to select your language. Afterwards press the OK button."))
