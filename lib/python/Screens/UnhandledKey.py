from enigma import eTimer

from Components.config import config
from Components.Pixmap import Pixmap
from Screens.Screen import Screen


class UnhandledKey(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["UnhandledKeyPixmap"] = Pixmap()
		self.unhandledKeyTimer = eTimer()
		self.unhandledKeyTimer.callback.append(self.hide)
		self.setAnimationMode(0)
		self.hide()
		self.onShow.append(self.startAutoHide)

	def startAutoHide(self):
		self.unhandledKeyTimer.start(config.usage.unhandledKeyTimeout.value * 1000, True)
