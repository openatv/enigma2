from boxbranding import getMachineBrand, getMachineName
from Screens.MessageBox import MessageBox
from Screens.ParentalControlSetup import ProtectedScreen
from Components.config import config

class FactoryReset(MessageBox, ProtectedScreen):
	def __init__(self, session):
		MessageBox.__init__(self, session, default = False,
			 text = _("When you do a factory reset, you will lose ALL your configuration data, "
					"including timers, but not the contents of your hard disk.\n\n"
					"You can use the Backup Settings option in the Software Manager section "
					"of the Setup menu and then the Restore Settings option later.\n\n"
					"Your %s %s will reboot automatically after a factory reset.\n\n"
					"Do you really want to perform a factory reset now?") % (getMachineBrand(), getMachineName()))
		self.setTitle(_("Factory reset"))
		ProtectedScreen.__init__(self)

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and\
			(not config.ParentalControl.config_sections.main_menu.value and not config.ParentalControl.config_sections.configuration.value  or hasattr(self.session, 'infobar') and self.session.infobar is None) and\
			config.ParentalControl.config_sections.manufacturer_reset.value
