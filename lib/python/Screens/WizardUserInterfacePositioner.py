from Screens.MessageBox import MessageBox
from Screens.WizardLanguage import WizardLanguage
from Screens.Rc import Rc
from Components.Pixmap import Pixmap
from Components.Sources.Boolean import Boolean
from Tools.Directories import resolveFilename, SCOPE_SKIN
from Components.Console import Console

class UserInterfacePositionerWizard(WizardLanguage, Rc):
	def __init__(self, session, interface = None):
		self.xmlfile = resolveFilename(SCOPE_SKIN, "userinterfacepositionerwizard.xml")
		WizardLanguage.__init__(self, session, showSteps = False, showStepSlider = False)
		Rc.__init__(self)
		self.skinName = "StartWizard"
		self.session = session
		self.Console = Console()
		self["wizard"] = Pixmap()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		self.NextStep = None
		self.Text = None

		self.onClose.append(self.__onClose)
		if self.welcomeWarning not in self.onShow:
			self.onShow.append(self.welcomeWarning)

	def welcomeWarning(self):
		if self.welcomeWarning in self.onShow:
			self.onShow.remove(self.welcomeWarning)
		popup = self.session.openWithCallback(self.welcomeAction, MessageBox, _("Welcome to OpenViX!\n\n"
			"NOTE: This section of the wizard is intended for people who cannot disable overscan "
			"on their television / display.  Please first try to disable overscan before using this feature.\n\n"
			"USAGE: If you continue adjust the screen size and position settings so that the shaded user interface layer *just* "
			"covers the test pattern in the background.\n\n"
			"Select Yes to change these settings or No to skip this step."), type=MessageBox.TYPE_YESNO, timeout=-1, default=False)
		popup.setTitle("Start Wizard - Screen Alignment")

	def welcomeAction(self, answer):
		if answer:
			self.Console.ePopen('/usr/bin/showiframe /usr/share/enigma2/hd-testcard.mvi')
		else:
			self.close()

	def exitWizardQuestion(self, ret = False):
		if ret:
			self.markDone()
			self.close()

	def markDone(self):
		pass

	def back(self):
		WizardLanguage.back(self)

	def __onClose(self):
		self.Console.ePopen('/usr/bin/showiframe /usr/share/backdrop.mvi')
