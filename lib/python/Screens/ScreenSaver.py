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
				service = self.session.screen["CurrentService"].service
				sref = None
				if isinstance(service, eServiceReference):
					sref = service.toString()
				elif isinstance(service, iPlayableServicePtr):
					info = service and service.info()
					sref = info.getInfoString(iServiceInformation.sServiceref)
				if sref:
					picon = getPiconName(sref)
					if exists(picon):
						self["picture"].instance.setPixmapFromFile(picon)
						pictureSize = (220, 132)
			except Exception:
				pass
			pictureSize = pictureSize or self["picture"].getSize()
			scaleFactor = 1.5 if self.instance.size().width() > 1300 else 1.0
			self.maxX = int(self.instance.size().width() - pictureSize[0] * scaleFactor)
			self.maxY = int(self.instance.size().height() - pictureSize[1] * scaleFactor)
			self.movePicture()
		else:
			self["picture"].hide()

	def hideScreenSaver(self):
		self.moveTimer.stop()

	def movePicture(self):
		self["picture"].instance.move(ePoint(randrange(self.maxX), randrange(self.maxY)))
		self.moveTimer.startLongTimer(self.moveTiming)

	def serviceStarted(self):
		if self.shown:
			ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if ref:
				ref = ref.toString().split(":")
				flag = ref[2] == "2" or ref[2] == "A" or splitext(ref[10])[1].lower() in AUDIO_EXTENSIONS
				if not flag:
					self.hide()
