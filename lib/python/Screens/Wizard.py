from Screen import Screen

from Screens.HelpMenu import HelpableScreen
from Components.Label import Label
from Components.ActionMap import HelpableActionMap
from Components.config import config, configElementBoolean
from Components.Pixmap import Pixmap

config.misc.firstrun = configElementBoolean("config.misc.firstrun", 1);

class WelcomeWizard(Screen, HelpableScreen):

	skin = """
		<screen position="0,0" size="720,560" title="Welcome..." flags="wfNoBorder">
			<widget name="text" position="50,50" size="440,300" font="Arial;20" />
			<widget name="rc" pixmap="/usr/share/enigma2/rc.png" position="500,50" size="154,475" alphatest="on" />
			<widget name="circle" pixmap="/usr/share/enigma2/mute-fs8.png" position="520,200" zPosition="1" size="100,100" alphatest="on" />
		</screen>"""

	def __init__(self, session):
		self.skin = WelcomeWizard.skin

		Screen.__init__(self, session)
		HelpableScreen.__init__(self)


		self["text"] = Label(_("Hello User.\n\nThis start-wizard will guide you through the basic setup of your Dreambox."));
		self["rc"] = Pixmap()
		self["circle"] = Pixmap()
		
		self["actions"] = HelpableActionMap(self, "OkCancelActions",
			{
				"ok": (self.ok, _("Close this Screen...")),
			})

	def ok(self):
		config.misc.firstrun.value = 0;
		config.misc.firstrun.save()
		self.session.close()

def listActiveWizards():
	wizards = [ ]

	if config.misc.firstrun.value:
		wizards.append(WelcomeWizard)
	
	return wizards
