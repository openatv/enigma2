from enigma import eTimer

from Screens.Screen import Screen
from Components.Pixmap import Pixmap
from Components.config import config


class UnhandledKey(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["UnhandledKeyPixmap"] = Pixmap()
		self.unhandledKeyTimer = eTimer()
		self.unhandledKeyTimer.callback.append(self.hide)
		self.timeout = int(config.usage.unhandledkey_timeout.value) * 1000

	def displayUnhandledKey(self):
		self.show()
		self.unhandledKeyTimer.start(self.timeout, True)
