from Screens.HelpMenu import ShowRemoteControl
from Screens.Screen import Screen
from Screens.Wizard import Wizard
from Components.Pixmap import Pixmap
from Components.Sources.Boolean import Boolean
from Tools.Directories import resolveFilename, SCOPE_SKINS
from Components.Console import Console


class WizardOSDCalibration(Wizard, ShowRemoteControl):
	def __init__(self, session, interface=None):
		self.xmlfile = resolveFilename(SCOPE_SKINS, "wizardosdcalibration.xml")
		Wizard.__init__(self, session, showSteps=False, showStepSlider=False)
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

	def exitWizardQuestion(self, ret=False):
		if ret:
			self.markDone()
			self.close()

	def markDone(self):
		pass

	def back(self):
		Wizard.back(self)
