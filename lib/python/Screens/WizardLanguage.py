from Wizard import Wizard
from Components.Label import Label
from Components.Language import language

class WizardLanguage(Wizard):
	def __init__(self, session, showSteps = True, showStepSlider = True, showList = True, showConfig = True):
		Wizard.__init__(self, session, showSteps, showStepSlider, showList, showConfig)
		self["languagetext"] = Label()
		self.updateLanguageDescription()

	def red(self):
		self.resetCounter()
		self.languageSelect()

	def languageSelect(self):
		print "languageSelect"
		newlanguage = language.getActiveLanguageIndex() + 1
		if newlanguage >= len(language.getLanguageList()):
			newlanguage = 0
		language.activateLanguageIndex(newlanguage)
		self.updateTexts()

	def updateLanguageDescription(self):
		print language.getLanguageList()[language.getActiveLanguageIndex()]
		self["languagetext"].setText(self.getTranslation(language.getLanguageList()[language.getActiveLanguageIndex()][1][0]))

	def updateTexts(self):
		print "updateTexts"
		self.updateText(firstset = True)
		self.updateValues()
		self.updateLanguageDescription()
