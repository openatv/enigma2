from random import randrange
from os.path import splitext

from enigma import ePoint, eTimer, iPlayableService

from Components.MovieList import AUDIO_EXTENSIONS
from Components.Pixmap import Pixmap
from Components.ServiceEventTracker import ServiceEventTracker
from Screens.Screen import Screen


class ScreenSaver(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["ScreenSaver", "Screensaver"]
		self["picture"] = Pixmap()
		self.onShow.append(self.showScreenSaver)
		self.onHide.append(self.hideScreenSaver)
		self.onLayoutFinish.append(self.layoutFinished)
		self.moveLogoTimer = eTimer()
		self.moveLogoTimer.callback.append(self.doMovePicture)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evStart: self.serviceStarted
		})

	def showScreenSaver(self):
		self.moveLogoTimer.startLongTimer(5)

	def hideScreenSaver(self):
		self.moveLogoTimer.stop()

	def layoutFinished(self):
		pictureSize = self["picture"].getSize()
		self.maxX = self.instance.size().width() - pictureSize[0]
		self.maxY = self.instance.size().height() - pictureSize[1]
		self.doMovePicture()

	def doMovePicture(self):
		self.posX = randrange(self.maxX)
		self.posY = randrange(self.maxY)
		self["picture"].instance.move(ePoint(self.posX, self.posY))
		self.moveLogoTimer.startLongTimer(9)

	def serviceStarted(self):
		if self.shown:
			ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if ref:
				ref = ref.toString().split(":")
				flag = ref[2] == "2" or ref[2] == "A" or splitext(ref[10])[1].lower() in AUDIO_EXTENSIONS
				if not flag:
					self.hide()
