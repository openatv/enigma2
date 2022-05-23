from enigma import eTimer

from Components.Pixmap import Pixmap
from Screens.Screen import Screen


class UnhandledKey(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["UnhandledKeyPixmap"] = Pixmap()
		self.unhandledKeyTimer = eTimer()
		self.unhandledKeyTimer.callback.append(self.hide)
		# if BoxInfo.getItem("OSDAnimation"):
		# 	self.unhandledKeyDialog.setAnimationMode(0)

	def displayUnhandledKey(self):
		self.show()
		self.unhandledKeyTimer.start(2000, True)
