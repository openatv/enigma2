from Wizard import Wizard, wizardManager

from Components.config import ConfigBoolean, config
from Components.Pixmap import MovingPixmap

config.misc.firstruntutorial = ConfigBoolean(default = True)

class TutorialWizard(Wizard):
	skin = """
		<screen position="0,0" size="720,576" title="Welcome..." flags="wfNoBorder">
			<widget name="text" position="50,100" size="440,200" font="Regular;23" />
			<widget name="list" position="50,300" zPosition="1" size="440,200" />
			<widget name="rc" pixmap="skin_default/rc.png" position="500,600" zPosition="10" size="154,475" transparent="1" alphatest="on"/>
			<widget name="arrowdown" pixmap="skin_default/arrowdown.png" position="0,0" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
			<widget name="arrowup" pixmap="skin_default/arrowup.png" position="-100,-100" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
			<widget name="arrowup2" pixmap="skin_default/arrowup.png" position="-100,-100" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
		</screen>"""
	
	def __init__(self, session):
		self.skin = TutorialWizard.skin
		self.xmlfile = "tutorialwizard.xml"
		
		Wizard.__init__(self, session, showSteps=False, showStepSlider=False, showList=True, showConfig=False)
		self["rc"] = MovingPixmap()
		self["arrowdown"] = MovingPixmap()
		self["arrowup"] = MovingPixmap()
		self["arrowup2"] = MovingPixmap()
		
	def markDone(self):
		config.misc.firstruntutorial.value = False
		config.misc.firstruntutorial.save()

#wizardManager.registerWizard(TutorialWizard, config.misc.firstruntutorial.value, priority = 30)
