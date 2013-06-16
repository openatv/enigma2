from Wizard import wizardManager
from Screens.WizardLanguage import WizardLanguage
from Screens.WizardUserInterfacePositioner import UserInterfacePositionerWizard
from Screens.Rc import Rc

from Components.Pixmap import Pixmap
from Components.config import config, ConfigBoolean, configfile

from LanguageSelection import LanguageWizard

config.misc.firstrun = ConfigBoolean(default = True)
config.misc.languageselected = ConfigBoolean(default = True)

class StartWizard(WizardLanguage, Rc):
	def __init__(self, session, silent = True, showSteps = False, neededTag = None):
		self.xmlfile = ["startwizard.xml"]
		WizardLanguage.__init__(self, session, showSteps = False)
		Rc.__init__(self)
		self["wizard"] = Pixmap()

	def markDone(self):
		# setup remote control, all stb have same settings except dm8000 which uses a different settings
		import os
		boxType = ''
		if os.path.isfile("/proc/stb/info/model"):
			boxType = open("/proc/stb/info/model").read().strip().lower()

		if 'dm8000' in boxType:
			config.misc.rcused.value = 0
		else:
			config.misc.rcused.value = 1
		config.misc.rcused.save()

		config.misc.firstrun.value = 0
		config.misc.firstrun.save()
		configfile.save()

wizardManager.registerWizard(LanguageWizard, config.misc.languageselected.getValue(), priority = 2)
wizardManager.registerWizard(UserInterfacePositionerWizard, config.misc.firstrun.getValue(), priority = 4)
wizardManager.registerWizard(StartWizard, config.misc.firstrun.getValue(), priority = 20)
