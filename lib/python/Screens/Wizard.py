from Screen import Screen

from Screens.HelpMenu import HelpableScreen
from Components.Label import Label
from Components.ActionMap import HelpableActionMap
from Components.config import config, configElementBoolean

config.misc.firstrun = configElementBoolean("config.misc.firstrun", 1);

class WelcomeWizard(Screen, HelpableScreen):

	skin = """
		<screen position="140,125" size="460,350" title="Welcome...">
			<widget name="text" position="20,20" size="440,300" font="Arial;30" />
		</screen>"""

	def __init__(self, session):
		self.skin = WelcomeWizard.skin

		Screen.__init__(self, session)
		HelpableScreen.__init__(self)


		self["text"] = Label(_("Welcome!\n\nYou can always press the help key!\n\nPlease Note: Make a service search first!"));
		
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
