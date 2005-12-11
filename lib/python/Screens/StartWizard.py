from Wizard import Wizard, wizardManager

from Components.Pixmap import *
from LanguageSelection import LanguageSelection

class StartWizard(Wizard):
	skin = """
		<screen position="0,0" size="720,560" title="Welcome..." flags="wfNoBorder" >
			<widget name="text" position="50,100" size="440,200" font="Arial;23" />
			<widget name="list" position="50,300" zPosition="1" size="440,200" />
			<widget name="config" position="50,300" zPosition="1" size="440,200" transparent="1" />			
			<widget name="step" position="50,50" size="440,25" font="Arial;23" />
			<widget name="stepslider" position="50,500" zPosition="1" size="440,20" backgroundColor="dark" />
			<widget name="rc" pixmap="/usr/share/enigma2/rc.png" position="500,600" zPosition="10" size="154,475" transparent="1" alphatest="on"/>
			<widget name="arrowdown" pixmap="/usr/share/enigma2/arrowdown.png" position="0,0" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
			<widget name="arrowup" pixmap="/usr/share/enigma2/arrowup.png" position="-100,-100" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
		</screen>"""
	
	def __init__(self, session):
		self.skin = StartWizard.skin
		self.xmlfile = "startwizard.xml"
		
		Wizard.__init__(self, session)
		self["rc"] = MovingPixmap()
		self["arrowdown"] = MovingPixmap()
		self["arrowup"] = MovingPixmap()
		
wizardManager.registerWizard(LanguageSelection)
wizardManager.registerWizard(StartWizard)