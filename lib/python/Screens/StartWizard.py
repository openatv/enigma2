from Wizard import wizardManager
from Screens.WizardLanguage import WizardLanguage

from Components.Pixmap import Pixmap, MovingPixmap
from Components.config import config, ConfigBoolean, configfile

from LanguageSelection import LanguageSelection
from DefaultWizard import DefaultWizard

config.misc.firstrun = ConfigBoolean(default = True)
config.misc.languageselected = ConfigBoolean(default = True)

class StartWizard(WizardLanguage):
	def __init__(self, session):
		self.xmlfile = "startwizard.xml"
		WizardLanguage.__init__(self, session, showSteps = False)
		self["wizard"] = Pixmap()
		self["rc"] = MovingPixmap()
		self["arrowdown"] = MovingPixmap()
		self["arrowup"] = MovingPixmap()
		self["arrowup2"] = MovingPixmap()
		
	def markDone(self):
		config.misc.firstrun.value = 0
		config.misc.firstrun.save()
		configfile.save()
		
wizardManager.registerWizard(LanguageSelection, config.misc.languageselected.value, priority = 5)
wizardManager.registerWizard(DefaultWizard, config.misc.defaultchosen.value, priority = 1)
wizardManager.registerWizard(StartWizard, config.misc.firstrun.value, priority = 20)
