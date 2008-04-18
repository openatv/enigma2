from Wizard import Wizard, wizardManager

from Components.config import ConfigBoolean, config
from Components.Pixmap import MovingPixmap

config.misc.firstruntutorial = ConfigBoolean(default = True)

class TutorialWizard(Wizard):
	def __init__(self, session):
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
