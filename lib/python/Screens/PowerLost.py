from Screen import Screen
from MessageBox import MessageBox
from Components.config import config
import Screens.Standby
from boxbranding import getMachineBrand, getMachineName

class PowerLost(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.showMessageBox()

	def showMessageBox(self):
		if config.usage.boot_action.value == 'normal':
			message = _("Your %s %s was not shutdown properly.\n\n"
					"Do you want to put it in %s?") % (getMachineBrand(), getMachineName(), config.usage.shutdownNOK_action.value)
			self.session.openWithCallback(self.MsgBoxClosed, MessageBox, message, MessageBox.TYPE_YESNO, timeout = 60, default = True)
		else:
			self.MsgBoxClosed(True)

	def MsgBoxClosed(self, ret):
		if ret:
			if config.usage.shutdownNOK_action.value == 'deepstandby' and not config.usage.shutdownOK.value:
				self.session.open(Screens.Standby.TryQuitMainloop, 1)
			elif not Screens.Standby.inStandby:
				self.session.open(Screens.Standby.Standby)

		self.close()
