from __future__ import absolute_import
from Screens.HelpMenu import ShowRemoteControl
from Screens.Wizard import wizardManager
from Screens.WizardLanguage import WizardLanguage
from Screens.VideoWizard import VideoWizard
from Screens.Screen import Screen

from boxbranding import getBoxType

from Components.Pixmap import Pixmap
from Components.config import config, ConfigBoolean, configfile

from Screens.LocaleSelection import LocaleWizard

config.misc.firstrun = ConfigBoolean(default=True)
config.misc.videowizardenabled = ConfigBoolean(default=True)


class StartWizard(WizardLanguage, ShowRemoteControl):
	def __init__(self, session, silent=True, showSteps=False, neededTag=None):
		self.xmlfile = ["startwizard.xml"]
		WizardLanguage.__init__(self, session, showSteps=False)
		ShowRemoteControl.__init__(self)
		self["wizard"] = Pixmap()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		#Screen.setTitle(self, _("Welcome..."))
		Screen.setTitle(self, _("StartWizard"))

	def markDone(self):
		# setup remote control, all stb have same settings except dm8000 which uses a different settings
		if getBoxType() == 'dm8000':
			config.misc.rcused.value = 0
		else:
			config.misc.rcused.value = 1
		config.misc.rcused.save()

		config.misc.firstrun.value = 0
		config.misc.firstrun.save()
		configfile.save()


# StartEnigma.py#L528ff - RestoreSettings
wizardManager.registerWizard(VideoWizard, config.misc.videowizardenabled.value, priority=0)
#wizardManager.registerWizard(LocaleWizard, config.misc.languageselected.value, priority=2)
# FrontprocessorUpgrade FPUpgrade priority = 8
# FrontprocessorUpgrade SystemMessage priority = 9
wizardManager.registerWizard(StartWizard, config.misc.firstrun.value, priority=20)
# StartWizard calls InstallWizard
# NetworkWizard priority = 25
