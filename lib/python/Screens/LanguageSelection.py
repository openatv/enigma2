from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop
from Components.ActionMap import ActionMap
from Components.Language import language
from Components.config import config
from Components.Sources.List import List
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.Language_cache import LANG_TEXT
from enigma import eTimer

from Screens.Rc import Rc

from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
from Tools.LoadPixmap import LoadPixmap
import gettext

inWizzard = False

def LanguageEntryComponent(file, name, index):
	png = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "countries/" + index + ".png"))
	if png is None:
		png = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "countries/" + file + ".png"))
		if png is None:
			png = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "countries/missing.png"))
	res = (index, name, png)
	return res

def _cached(x):
	return LANG_TEXT.get(config.osd.language.value, {}).get(x, "")

class LanguageSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Setup Language"))

		language.InitLang()
		self.oldActiveLanguage = language.getActiveLanguage()
		self.catalog = language.getActiveCatalog()

		self.list = []
# 		self["flag"] = Pixmap()
		self["summarylangname"] = StaticText()
		self["summarylangsel"] = StaticText()
		self["languages"] = List(self.list)
		self["languages"].onSelectionChanged.append(self.changed)

		self.updateList()
		self.onLayoutFinish.append(self.selectActiveLanguage)

		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Save"))
		self["key_yellow"] = Label(_("Update Cache"))
		self["key_blue"] = Label(_("Delete Language"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"ok": self.save,
			"cancel": self.cancel,
			"red": self.cancel,
			"green": self.save,
			"yellow": self.updateCache,
			"blue": self.delLang,
		}, -1)

	def updateCache(self):
		print"updateCache"
		self["languages"].setList([('update cache',_('Updating cache, please wait...'),None)])
		self.updateTimer = eTimer()
		self.updateTimer.callback.append(self.startupdateCache)
		self.updateTimer.start(100)

	def startupdateCache(self):
		self.updateTimer.stop()
		language.updateLanguageCache()
		self["languages"].setList(self.list)
		self.selectActiveLanguage()
		
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
		global inWizzard
		if inWizzard:
			inWizzard = False
			#self.session.openWithCallback(self.deletelanguagesCB, MessageBox, _("Do you want to delete all other languages?"), default = False)
			if self.oldActiveLanguage != config.osd.language.value:
				self.session.open(TryQuitMainloop, 3)
			self.close()
		else:
			if self.oldActiveLanguage != config.osd.language.value:
				self.session.openWithCallback(self.restartGUI, MessageBox,_("GUI needs a restart to apply a new language\nDo you want to restart the GUI now?"), MessageBox.TYPE_YESNO)
			else:
				self.close()

	def restartGUI(self, answer=True):
		if answer is True:
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close()

	#def deletelanguagesCB(self, anwser):
		#if anwser:
			#language.delLanguage()
		#self.close()

	def cancel(self):
		language.activateLanguage(self.oldActiveLanguage)
		config.osd.language.setValue(self.oldActiveLanguage)
		config.osd.language.save()
		self.close()

	def delLang(self):
		curlang = config.osd.language.value
		lang = curlang
		languageList = language.getLanguageListSelection()
		for t in languageList:
			if curlang == t[0]:
				lang = t[1]
				break
		self.session.openWithCallback(self.delLangCB, MessageBox, _("Do you want to delete all other languages?") + _(" Except %s") %(lang), default = False)

	def delLangCB(self, anwser):
		if anwser:
			language.delLanguage()
			language.activateLanguage(self.oldActiveLanguage)
			self.updateList()
			self.selectActiveLanguage()

	def run(self, justlocal = False):
		print "updating language..."
		lang = self["languages"].getCurrent()[0]

		if lang == 'update cache':
			self.setTitle("Updating cache")
			self["summarylangname"].setText("Updating cache")
			return

		if lang != config.osd.language.value:
			config.osd.language.setValue(lang)
			config.osd.language.save()

		self.setTitle(_cached("T2"))
		self["summarylangname"].setText(_cached("T2"))
		self["summarylangsel"].setText(self["languages"].getCurrent()[1])
		self["key_red"].setText(_cached("T3"))
		self["key_green"].setText(_cached("T4"))
# 		index = self["languages"].getCurrent()[2]
# 		print 'INDEX:',index
# 		self["flag"].instance.setPixmap(self["languages"].getCurrent()[2])

		if justlocal:
			return

		language.activateLanguage(lang)
		config.misc.languageselected.value = 0
		config.misc.languageselected.save()
		print "ok"

	def updateList(self):
		languageList = language.getLanguageList()
		if not languageList: # no language available => display only english
			list = [ LanguageEntryComponent("en", "English (US)", "en_US") ]
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
		global inWizzard
		inWizzard = True
		self.onLayoutFinish.append(self.selectKeys)

		self["wizard"] = Pixmap()
		self["summarytext"] = StaticText()
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
		self["text"].setText(_cached("T1"))
		self["summarytext"].setText(_cached("T1"))

	def createSummary(self):
		return LanguageWizardSummary

class LanguageWizardSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent)
