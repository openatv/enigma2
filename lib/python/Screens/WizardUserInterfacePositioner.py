from Screens.Wizard import wizardManager, WizardSummary
from Screens.WizardLanguage import WizardLanguage
from Screens.Rc import Rc
from Screens.MessageBox import MessageBox
from Components.Pixmap import Pixmap, MovingPixmap, MultiPixmap
from Components.Sources.Boolean import Boolean
from Tools.Directories import resolveFilename, SCOPE_SKIN
from Components.config import config, configfile

class WizardUserInterfacePositioner(WizardLanguage, Rc):
	skin = """
		<screen position="0,0" size="e,e" backgroundColor="blue">
			<widget name="config" position="c-175,c-75" size="350,150" foregroundColor="black" backgroundColor="blue" />
			<widget source="status" render="Label" position="c-300,e-170" size="600,60" zPosition="10" font="Regular;21" halign="center" valign="center" foregroundColor="black" backgroundColor="blue" transparent="1" />
			<widget name="text" position="153,40" size="340,300" font="Regular;22"  foregroundColor="black" backgroundColor="blue" />
			<widget source="list" render="Listbox" position="53,340" size="440,180"  foregroundColor="black" backgroundColor="blue" scrollbarMode="showOnDemand" >
				<convert type="StringList" />
			</widget>
			<widget name="config" position="53,340" zPosition="1" size="440,180"  foregroundColor="black" backgroundColor="blue" transparent="1" scrollbarMode="showOnDemand" />
			<widget name="wizard" pixmap="skin_default/wizard.png" position="40,50" zPosition="10" size="110,174" alphatest="on" />
			<widget name="rc" pixmaps="skin_default/rc.png,skin_default/rcold.png" position="e-300,c-250" zPosition="10" size="154,500" alphatest="on" />
			<widget name="arrowdown" pixmap="skin_default/arrowdown.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
			<widget name="arrowup" pixmap="skin_default/arrowup.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
		</screen>"""
	def __init__(self, session, interface = None):
		self.xmlfile = resolveFilename(SCOPE_SKIN, "userinterfacepositionerwizard.xml")
		WizardLanguage.__init__(self, session, showSteps = False, showStepSlider = False)
		Rc.__init__(self)
		self.session = session
		self["wizard"] = Pixmap()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		self.NextStep = None
		self.Text = None

	def exitWizardQuestion(self, ret = False):
		if (ret):
			self.markDone()
			self.close()

	def markDone(self):
		pass

	def back(self):
		WizardLanguage.back(self)

