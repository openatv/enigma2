from Wizard import wizardManager
from Screens.WizardLanguage import WizardLanguage
from Screens.ScanSetup import DefaultSatLists
from Screens.DefaultWizard import DefaultWizard
from Screens.Rc import Rc

from Components.Pixmap import Pixmap, MovingPixmap, MultiPixmap
from Components.config import config, ConfigBoolean, configfile, ConfigSubsection

from LanguageSelection import LanguageWizard

config.misc.firstrun = ConfigBoolean(default = True)
config.misc.startwizard = ConfigSubsection()
config.misc.startwizard.shownimconfig = ConfigBoolean(default = True)
config.misc.startwizard.doservicescan = ConfigBoolean(default = True)
config.misc.languageselected = ConfigBoolean(default = True)

class StartWizard(DefaultSatLists, Rc):
	def __init__(self, session, silent = True, showSteps = False, neededTag = None):
		self.xmlfile = ["startwizard.xml", "defaultsatlists.xml"]
		WizardLanguage.__init__(self, session, showSteps = False)
		DefaultWizard.__init__(self, session, silent, showSteps, neededTag = "services")
		Rc.__init__(self)
		self["wizard"] = Pixmap()
				
	def markDone(self):
		config.misc.firstrun.value = 0
		config.misc.firstrun.save()
		configfile.save()
		
wizardManager.registerWizard(LanguageWizard, config.misc.languageselected.value, priority = 5)
wizardManager.registerWizard(StartWizard, config.misc.firstrun.value, priority = 20)
