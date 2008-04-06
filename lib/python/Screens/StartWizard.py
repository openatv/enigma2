from Wizard import wizardManager
from Screens.WizardLanguage import WizardLanguage

from Components.Pixmap import Pixmap, MovingPixmap
from Components.config import config, ConfigBoolean, configfile

from LanguageSelection import LanguageSelection
#from DefaultWizard import DefaultWizard

config.misc.firstrun = ConfigBoolean(default = True)
config.misc.languageselected = ConfigBoolean(default = True)

class StartWizard(WizardLanguage):
	skin = """
		<screen position="0,0" size="720,576" title="Welcome..." flags="wfNoBorder" >
			<widget name="text" position="153,50" size="340,270" font="Regular;23" />
			<widget source="list" render="Listbox" position="50,300" size="440,200" scrollbarMode="showOnDemand" >
				<convert type="StringList" />
			</widget>
			<widget name="config" position="50,300" zPosition="1" size="440,200" transparent="1" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/button_red.png" position="40,225" zPosition="0" size="15,16" transparent="1" alphatest="on" />
			<widget name="languagetext" position="55,225" size="95,30" font="Regular;18" />			
			<widget name="stepslider" position="50,500" zPosition="1" borderWidth="2" size="440,20" backgroundColor="dark" />
			<widget name="wizard" pixmap="wizard.png" position="40,50" zPosition="10" size="110,174" transparent="1" alphatest="on"/>
			<widget name="rc" pixmap="rc.png" position="500,600" zPosition="10" size="154,475" transparent="1" alphatest="on"/>
			<widget name="arrowdown" pixmap="arrowdown.png" position="0,0" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
			<widget name="arrowup" pixmap="arrowup.png" position="-100,-100" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
			<widget name="arrowup2" pixmap="arrowup.png" position="-100,-100" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
		</screen>"""
	
	def __init__(self, session):
		self.skin = StartWizard.skin
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
#wizardManager.registerWizard(DefaultWizard, config.misc.defaultchosen.value)
wizardManager.registerWizard(StartWizard, config.misc.firstrun.value, priority = 20)
