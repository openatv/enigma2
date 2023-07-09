from Screens.HelpMenu import ShowRemoteControl
from Screens.Screen import Screen
from Screens.WizardLanguage import WizardLanguage
from Components.Pixmap import Pixmap
from Components.Sources.Boolean import Boolean
from Tools.Directories import resolveFilename, SCOPE_SKINS
from Components.Console import Console


class UserInterfacePositionerWizard(WizardLanguage, ShowRemoteControl):
	def __init__(self, session, interface=None):
		self.xmlfile = resolveFilename(SCOPE_SKINS, "userinterfacepositionerwizard.xml")
		WizardLanguage.__init__(self, session, showSteps=False, showStepSlider=False)
		ShowRemoteControl.__init__(self)
		self.skinName = "StartWizard"
		self.session = session
		Screen.setTitle(self, _("Welcome..."))
		self.Console = Console()
		self["wizard"] = Pixmap()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		self.NextStep = None
		self.Text = None

		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.__onClose)

	def layoutFinished(self):
		self.Console.ePopen('/usr/bin/showiframe /usr/share/enigma2/hd-testcard.mvi')

	def exitWizardQuestion(self, ret=False):
		if ret:
			self.markDone()
			self.close()

	def markDone(self):
		pass

	def back(self):
		WizardLanguage.back(self)

	def __onClose(self):
		self.Console.ePopen('/usr/bin/showiframe /usr/share/backdrop.mvi')
