from Components.config import config
from Components.SystemInfo import BoxInfo
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
import Screens.Standby


class PowerLost(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.showMessageBox()

	def showMessageBox(self):
		if config.usage.boot_action.value == 'normal':
			message = _("Your %s %s was not shutdown properly.\n\n"
					"Do you want to put it in %s?") % (BoxInfo.getItem("displaybrand"), BoxInfo.getItem("displaymodel"), config.usage.shutdownNOK_action.value)
			self.session.openWithCallback(self.MsgBoxClosed, MessageBox, message, MessageBox.TYPE_YESNO, timeout=int(config.usage.shutdown_msgbox_timeout.value), default=True)
		else:
			self.MsgBoxClosed(True)

	def MsgBoxClosed(self, ret):
		if ret:
			if config.usage.shutdownNOK_action.value == 'deepstandby' and not config.usage.shutdownOK.value:
				self.session.open(Screens.Standby.TryQuitMainloop, 1)
			elif not Screens.Standby.inStandby:
				self.session.open(Screens.Standby.Standby)

		self.close()
