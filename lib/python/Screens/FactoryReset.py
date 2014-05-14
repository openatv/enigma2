from Screens.MessageBox import MessageBox
from boxbranding import getMachineBrand, getMachineName

class FactoryReset(MessageBox):
	def __init__(self, session):
		MessageBox.__init__(self, session, default = False,
			 text = _("When you do a factory reset, you will lose ALL your configuration data, "
					"including timers, but not the contents of your hard disk.\n\n"
					"You can use the Backup Settings option in the Software Manager section "
					"of the Setup menu and then the Restore Settings option later.\n\n"
					"Your %s %s will reboot automatically after a factory reset.\n\n"
					"Do you really want to perform a factory reset now?") % (getMachineBrand(), getMachineName()))
		self.setTitle(_("Factory reset"))
