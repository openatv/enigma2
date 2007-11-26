from Screens.Ci import MMIDialog
from enigma import eSocket_UI

class SocketMMIMessageHandler:
	def __init__(self):
		self.session = None
		self.dlgs = { }
		self.handler = eSocket_UI.getInstance()
		self.handler.socketStateChanged.get().append(self.socketStateChanged)

	def setSession(self, session):
		self.session = session

	def connected(self):
		return self.handler.getState(0)

	def getName(self):
		return self.handler.getName(0)

	def startMMI(self):
		slot = 0
		self.dlgs[slot] = self.session.openWithCallback(self.dlgClosed, MMIDialog, slot, 2, self.handler, _("wait for mmi..."))

	def socketStateChanged(self, slot):
		if slot in self.dlgs:
			self.dlgs[slot].ciStateChanged()
		elif self.handler.availableMMI(slot) == 1:
			if self.session:
				self.dlgs[slot] = self.session.openWithCallback(self.dlgClosed, MMIDialog, slot, 3, self.handler, _("wait for mmi..."))

	def dlgClosed(self, slot):
		if slot in self.dlgs:
			del self.dlgs[slot]

