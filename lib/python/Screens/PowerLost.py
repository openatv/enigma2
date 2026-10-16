from enigma import eTimer

from Components.config import config
from Components.SystemInfo import BoxInfo
from Screens.MessageBox import MessageBox
import Screens.Standby
from Tools.Notifications import AddNotification, AddNotificationWithCallback


class PowerLost():
	def __init__(self, session):
		self.session = session
		# StartEnigma marks the new session as unclean before entering the main loop.
		self.shutdownOK = config.usage.shutdownOK.value
		self.bootAction = config.usage.boot_action.value
		self.shutdownAction = config.usage.shutdownNOK_action.value
		self.timer = eTimer()
		self.timer.callback.append(self.showMessageBox)
		self.timer.start(0, True)

	def showMessageBox(self):
		if self.session.shutdown:
			return
		# Queue only once the main loop is running; notifications wait for the
		# InfoBar, so an active wizard or another startup dialog keeps its focus.
		if self.bootAction == 'normal':
			message = _("Your %s %s was not shutdown properly.\n\n"
					"Do you want to put it in %s?") % (BoxInfo.getItem("displaybrand"), BoxInfo.getItem("displaymodel"), self.shutdownAction)
			AddNotificationWithCallback(self.msgBoxClosed, MessageBox, message, MessageBox.TYPE_YESNO, timeout=int(config.usage.shutdown_msgbox_timeout.value), default=True)
		else:
			self.msgBoxClosed(True)

	def msgBoxClosed(self, ret):
		if ret and not self.session.shutdown:
			if self.shutdownAction == 'deepstandby' and not self.shutdownOK:
				AddNotification(Screens.Standby.TryQuitMainloop, 1)
			elif not Screens.Standby.inStandby:
				AddNotification(Screens.Standby.Standby)
