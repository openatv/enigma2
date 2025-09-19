from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.AVSwitch import AVSwitch
import Tools.Notifications


class Scart(Screen):
	def __init__(self, session, start_visible=True):
		Screen.__init__(self, session)
		self.msgBox = None
		self.notificationVisible = None

		self.avswitch = AVSwitch()

		if start_visible:
			self.onExecBegin.append(self.showMessageBox)
			self.msgVisible = None
		else:
			self.msgVisible = False

	def showMessageBox(self):
		if self.msgVisible is None:
			self.onExecBegin.remove(self.showMessageBox)
			self.msgVisible = False

		if not self.msgVisible:
			self.msgVisible = True
			self.avswitch.setInput("scart")
			if not self.session.in_exec:
				self.notificationVisible = True
				Tools.Notifications.AddNotificationWithCallback(self.MsgBoxClosed, MessageBox, _("If you see this, something is wrong with\nyour SCART connection. Press OK to return."), MessageBox.TYPE_ERROR, msgBoxID="scart_msgbox")
			else:
				self.msgBox = self.session.openWithCallback(self.MsgBoxClosed, MessageBox, _("If you see this, something is wrong with\nyour SCART connection. Press OK to return."), MessageBox.TYPE_ERROR)

	def MsgBoxClosed(self, *val):
		self.msgBox = None
		self.switchToTV()

	def switchToTV(self, *val):
		if self.msgVisible:
			if self.msgBox:
				self.msgBox.close()  # ... MsgBoxClosed -> switchToTV again..
				return
			self.avswitch.setInput("encoder")
			self.msgVisible = False
		if self.notificationVisible:
			self.avswitch.setInput("encoder")
			self.notificationVisible = False
			for notification in Tools.Notifications.current_notifications:
				try:
					if notification[1].msgBoxID == "scart_msgbox":
						notification[1].close()
				except Exception:
					print("other notification is open. try another one.")
