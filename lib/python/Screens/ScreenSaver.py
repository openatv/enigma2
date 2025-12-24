from os.path import exists, splitext
from random import randrange

from enigma import ePoint, eServiceReference, eTimer, iPlayableService, iPlayableServicePtr, iServiceInformation

from Components.config import config
from Components.MovieList import AUDIO_EXTENSIONS
from Components.Pixmap import Pixmap
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Renderer.Picon import getPiconName
from Screens.Screen import Screen


class ScreenSaver(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["ScreenSaver", "Screensaver"]
		self["picture"] = Pixmap()
		self.moveTimer = eTimer()
		self.moveTimer.callback.append(self.movePicture)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evStart: self.serviceStarted
		})
		self.onShow.append(self.showScreenSaver)
		self.onHide.append(self.hideScreenSaver)

	def showScreenSaver(self):
		if config.usage.screenSaverMode.value > 0:  # Show logo or picon
			self.moveTiming = config.usage.screenSaverMoveTimer.value
			if config.usage.screenSaverMode.value == 2:  # Show picon
				pictureSize = ()
				try:
					sref = None
					service = self.session.screen["CurrentService"].service
					if isinstance(service, eServiceReference):
						sref = service.toString()
					elif isinstance(service, iPlayableServicePtr):
						info = service and service.info()
						sref = info.getInfoString(iServiceInformation.sServiceref)
					if sref:
						picon = getPiconName(sref)
						if exists(picon):
							self["picture"].instance.setPixmapFromFile(picon)
				except Exception:
					pass
			pictureSize = (self["picture"].instance.getPixmapSize().width(), self["picture"].instance.getPixmapSize().height())
			self.maxX = int(self.instance.size().width() - pictureSize[0])
			self.maxY = int(self.instance.size().height() - pictureSize[1])
			self.movePicture()
		else:
			self["picture"].hide()

	def hideScreenSaver(self):
		self.moveTimer.stop()

	def movePicture(self):
		posX, posY = 20 + randrange(self.maxX - 40), 20 + randrange(self.maxY - 40)  # Leave space 20 pixels around the edges
		self["picture"].instance.move(ePoint(posX, posY))
		self.moveTimer.startLongTimer(self.moveTiming)

	def serviceStarted(self):
		if self.shown:
			ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if ref:
				ref = ref.toString().split(":")
				flag = ref[2] == "2" or ref[2] == "A" or splitext(ref[10])[1].lower() in AUDIO_EXTENSIONS
				if not flag:
					self.hide()
