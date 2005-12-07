from Screen import Screen

from Screens.HelpMenu import HelpableScreen
from Components.Label import Label
from Components.Slider import Slider
from Components.ActionMap import HelpableActionMap
from Components.config import config, configElementBoolean
from Components.Pixmap import Pixmap

config.misc.firstrun = configElementBoolean("config.misc.firstrun", 1);

class WelcomeWizard(Screen, HelpableScreen):

	skin = """
		<screen position="0,0" size="720,560" title="Welcome..." flags="wfNoBorder">
			<widget name="text" position="50,100" size="440,300" font="Arial;23" />
			<widget name="step" position="50,50" size="440,25" font="Arial;23" />
			<widget name="stepslider" position="50,500" zPosition="1" size="440,20" backgroundColor="dark" />
			<widget name="rc" pixmap="/usr/share/enigma2/rc.png" position="500,50" size="154,475" alphatest="on" />
			<widget name="arrowdown" pixmap="/usr/share/enigma2/arrowdown.png" position="557,232" zPosition="1" size="37,70" alphatest="on" />
		</screen>"""
		
	text = [_("Hello User.\n\nThis start-wizard will guide you through the basic setup of your Dreambox."), 
			_("Bla"),
			_("Blub")]

	def __init__(self, session):
		self.skin = WelcomeWizard.skin
		self.numSteps = 3
		self.currStep = 1

		Screen.__init__(self, session)
		HelpableScreen.__init__(self)


		self["text"] = Label()
		self["rc"] = Pixmap()
		self["arrowdown"] = Pixmap()

		self["step"] = Label()
				
		self["stepslider"] = Slider(1, self.numSteps)

		self.updateValues()
		
		self["actions"] = HelpableActionMap(self, "OkCancelActions",
			{
				"ok": (self.ok, _("Close this Screen...")),
			})

	def updateValues(self):
		self["text"].setText(self.text[self.currStep - 1])
		self["step"].setText(_("Step ") + str(self.currStep) + "/" + str(self.numSteps))
		self["stepslider"].setValue(self.currStep)
		
	def ok(self):
		if (self.currStep == self.numSteps): # wizard finished
			config.misc.firstrun.value = 0;
			config.misc.firstrun.save()
			self.session.close()
		else:
			self.currStep += 1
			self.updateValues()

def listActiveWizards():
	wizards = [ ]

	if config.misc.firstrun.value:
		wizards.append(WelcomeWizard)
	
	return wizards
