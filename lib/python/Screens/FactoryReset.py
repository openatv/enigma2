from Screens.MessageBox import MessageBox
from Screens.ParentalControlSetup import ProtectedScreen
from Components.config import config

class FactoryReset(MessageBox, ProtectedScreen):
	def __init__(self, session):
		MessageBox.__init__(self, session, _("When you do a factory reset, you will lose ALL your configuration data\n"
			"(including bouquets, services, satellite data ...)\n"
			"After completion of factory reset, your receiver will restart automatically!\n\n"
			"Really do a factory reset?"), MessageBox.TYPE_YESNO)
		self.skinName = "MessageBox"
		ProtectedScreen.__init__(self)

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and\
			(not config.ParentalControl.config_sections.main_menu.value and not config.ParentalControl.config_sections.configuration.value  or hasattr(self.session, 'infobar') and self.session.infobar is None) and\
			config.ParentalControl.config_sections.manufacturer_reset.value
