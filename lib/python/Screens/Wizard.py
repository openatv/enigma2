from Screen import Screen

from Screens.HelpMenu import HelpableScreen
from Components.Label import Label
from Components.Slider import Slider
from Components.ActionMap import HelpableActionMap
from Components.config import config, configElementBoolean
from Components.Pixmap import *
from Components.MenuList import MenuList

config.misc.firstrun = configElementBoolean("config.misc.firstrun", 1);

class WelcomeWizard(Screen, HelpableScreen):

	skin = """
		<screen position="0,0" size="720,560" title="Welcome..." flags="wfNoBorder" >
			<widget name="text" position="50,100" size="440,200" font="Arial;23" />
			<widget name="list" position="50,300" size="440,200" />
			<widget name="step" position="50,50" size="440,25" font="Arial;23" />
			<widget name="stepslider" position="50,500" zPosition="1" size="440,20" backgroundColor="dark" />
			<widget name="rc" pixmap="/usr/share/enigma2/rc.png" position="500,50" size="154,475" transparent="1" alphatest="on"/>
			<widget name="arrowdown" pixmap="/usr/share/enigma2/arrowdown.png" position="0,0" zPosition="1" size="37,70" transparent="1" alphatest="on"/>
			<widget name="arrowup" pixmap="/usr/share/enigma2/arrowup.png" position="-100,-100" zPosition="1" size="37,70" transparent="1" alphatest="on"/>
		</screen>"""
		
	text = [_("Hello User.\n\nThis start-wizard will guide you through the basic setup of your Dreambox.\n\nPress the OK button on your remote control to move to the next step."), 
			_("You can use the Up and Down buttons on your remote control to select your choice.\n\nWhat do you want to do?"),
			_("Blub")]
			
	listEntries = [[],
				    ["Use wizard to set up basic features", "Exit wizard"],
					[]]

	def __init__(self, session):
		self.skin = WelcomeWizard.skin
		self.numSteps = 3
		self.currStep = 1

		Screen.__init__(self, session)
		HelpableScreen.__init__(self)


		self["text"] = Label()
		self["rc"] = Pixmap()
		self["arrowdown"] = MovingPixmap()
		self["arrowdown"].moveTo(557, 232, 100)
		self["arrowup"] = MovingPixmap()
		
		self.onShown.append(self["arrowdown"].startMoving)

		self["step"] = Label()
				
		self["stepslider"] = Slider(1, self.numSteps)
		
		self.list = []
		#list.append(("Use wizard to set up basic features", None))
		#list.append(("Exit wizard", None))
		self["list"] = MenuList(self.list)

		self.updateValues()
		
		self["actions"] = HelpableActionMap(self, "OkCancelActions",
			{
				"ok": (self.ok, _("Close this Screen...")),
			})

	def updateValues(self):
		self["text"].setText(self.text[self.currStep - 1])
		self["step"].setText(_("Step ") + str(self.currStep) + "/" + str(self.numSteps))
		self["stepslider"].setValue(self.currStep)
		self.list = []
		
		if (len(self.listEntries[self.currStep - 1]) > 0):
			for x in self.listEntries[self.currStep - 1]:
				self.list.append((x, None))
		self["list"].l.setList(self.list)
		
	def ok(self):
		if (self.currStep == self.numSteps): # wizard finished
			config.misc.firstrun.value = 0;
			config.misc.firstrun.save()
			self.session.close()
		else:
			self.currStep += 1
			self.updateValues()
			
			if (self.currStep == 2):
				self["arrowdown"].moveTo(557, 200, 100)
				self["arrowup"].moveTo(557, 355, 100)
				self["arrowdown"].startMoving()
				self["arrowup"].startMoving()
				

def listActiveWizards():
	wizards = [ ]

	if config.misc.firstrun.value:
		wizards.append(WelcomeWizard)
	
	return wizards
