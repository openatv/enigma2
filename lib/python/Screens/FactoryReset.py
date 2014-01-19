from Screens.MessageBox import MessageBox
from boxbranding import getMachineBrand, getMachineName

class FactoryReset(MessageBox):
	def __init__(self, session):
		MessageBox.__init__(self, session, _("When you do a factory reset, you will lose ALL your configuration data\n"
			"(including bouquets, services, satellite data ...)\n"
			"After completion of factory reset, your %s %s will restart automatically!\n\n"
			"Really do a factory reset?") % (getMachineBrand(), getMachineName()), MessageBox.TYPE_YESNO, default = False)
		self.setTitle(_("Factory reset"))
		self.skinName = "MessageBox"
