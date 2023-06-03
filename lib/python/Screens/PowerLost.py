from Components.config import config
from Components.SystemInfo import BoxInfo
from Screens.MessageBox import MessageBox
import Screens.Standby


class PowerLost():
	def __init__(self, session):
		self.session = session
		if config.usage.boot_action.value == 'normal':
			message = _("Your %s %s was not shutdown properly.\n\n"
					"Do you want to put it in %s?") % (BoxInfo.getItem("displaybrand"), BoxInfo.getItem("displaymodel"), config.usage.shutdownNOK_action.value)
			self.session.openWithCallback(self.msgBoxClosed, MessageBox, message, MessageBox.TYPE_YESNO, timeout=int(config.usage.shutdown_msgbox_timeout.value), default=True)
		else:
			self.msgBoxClosed(True)

	def msgBoxClosed(self, ret):
		if ret:
			if config.usage.shutdownNOK_action.value == 'deepstandby' and not config.usage.shutdownOK.value:
				self.session.open(Screens.Standby.TryQuitMainloop, 1)
			elif not Screens.Standby.inStandby:
				self.session.open(Screens.Standby.Standby)
