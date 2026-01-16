from os.path import isfile
from random import randrange

from enigma import ePoint, eServiceReference, eSize, eTimer, iPlayableServicePtr, iServiceInformation

from Components.config import config
from Components.Pixmap import Pixmap
from Components.Renderer.Picon import getPiconName
from Screens.Screen import Screen


class ScreenSaver(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["ScreenSaver", "Screensaver"]
		self["picture"] = Pixmap()
		self.padding = 20  # Allow 20 pixels of edge padding to allow for screen over-scan.
		self.picturePath = None
		self.movePictureTimer = eTimer()
		self.movePictureTimer.callback.append(self.movePicture)
		self.onLayoutFinish.append(self.layoutFinished)
		self.onShow.append(self.showScreenSaver)
		self.onHide.append(self.hideScreenSaver)

	def movePicture(self, timerActive=True):
		self["picture"].instance.move(ePoint(self.padding + randrange(self.maxX), self.padding + randrange(self.maxY)))
		if timerActive:
			self.movePictureTimer.startLongTimer(config.usage.screenSaverMoveTimer.value)

	def layoutFinished(self):
		self.screenW = self.instance.size().width()
		self.screenH = self.instance.size().height()
		self.logoPath = [x[1] for x in self["picture"].skinAttributes if x[0] == "pixmap"]
		self.logoPath = self.logoPath[0] if self.logoPath and isfile(self.logoPath[0]) else None
		self.picturePath = self.logoPath
		self.logoW = self["picture"].instance.size().width()
		self.logoH = self["picture"].instance.size().height()
		self.logoMaxX = self.screenW - self.logoW - (self.padding * 2)
		self.logoMaxY = self.screenH - self.logoH - (self.padding * 2)
		self.maxX = self.logoMaxX
		self.maxY = self.logoMaxY
		self.movePicture(timerActive=False)

	def showScreenSaver(self):
		def showLogo():
			if self.logoPath and isfile(self.logoPath):
				if self.logoPath != self.picturePath:
					self["picture"].instance.setPixmapFromFile(self.logoPath)
					self.picturePath = self.logoPath
					self["picture"].instance.resize(eSize(self.logoW, self.logoH))
					self.maxX = self.logoMaxX
					self.maxY = self.logoMaxY
				move = True
			else:
				move = False
			return move

		match config.usage.screenSaverMode.value:
			case 0:  # Show blank screen saver.
				self["picture"].instance.resize(eSize(0, 0))
				move = False
			case 1:  # Show logo screen saver.
				move = showLogo()
			case 2:  # Show picon screen saver.
				try:
					service = self.session.screen["CurrentService"].service
					if isinstance(service, eServiceReference):
						serviceReference = service.toString()
					elif isinstance(service, iPlayableServicePtr):
						info = service and service.info()
						serviceReference = info.getInfoString(iServiceInformation.sServiceref)
					else:
						serviceReference = None
					if serviceReference:
						piconPath = getPiconName(serviceReference)
						if isfile(piconPath):
							if piconPath != self.picturePath:
								self["picture"].instance.setPixmapFromFile(piconPath)
								self.picturePath = piconPath
								piconW = self["picture"].instance.getPixmapSize().width()
								piconH = self["picture"].instance.getPixmapSize().height()
								self["picture"].instance.resize(eSize(piconW, piconH))
								self.maxX = self.screenW - piconW - (self.padding * 2)
								self.maxY = self.screenH - piconH - (self.padding * 2)
							move = True
						else:
							raise NameError("Picon not found")
				except Exception as err:  # Picon is not available so show the logo.
					print(f"[ScreenSaver] Error: Unable to display picon!  ({err})")
					move = showLogo()
		if move:
			self.movePicture(timerActive=True)

	def hideScreenSaver(self):
		self.movePictureTimer.stop()
