from Screens.Screen import Screen
from Components.MovieList import AUDIO_EXTENSIONS
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Pixmap import Pixmap
from enigma import ePoint, eTimer, iPlayableService
import os, random

class Screensaver(Screen):
	def __init__(self, session):

		self.skin = """
			<screen name="Screensaver" position="fill" flags="wfNoBorder">
				<eLabel position="fill" backgroundColor="#54000000" zPosition="0"/>
				<widget name="picture" pixmap="skin_default/screensaverpicture.png" position="0,0" size="119,139" alphatest="blend" transparent="1" zPosition="1"/>
			</screen>"""

		Screen.__init__(self, session)

		self.moveLogoTimer = eTimer()
		self.moveLogoTimer.callback.append(self.doMovePicture)
		self.onShow.append(self.__onShow)
		self.onHide.append(self.__onHide)

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evStart: self.serviceStarted
			})

		self["picture"] = Pixmap()

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		picturesize = self["picture"].getSize()
		self.maxx = self.instance.size().width() - picturesize[0]
		self.maxy = self.instance.size().height() - picturesize[1]
		self.doMovePicture()

	def __onHide(self):
		self.moveLogoTimer.stop()

	def __onShow(self):
		self.moveLogoTimer.startLongTimer(5)

	def serviceStarted(self):
		if self.shown:
			ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if ref:
				ref = ref.toString().split(":")
				if not os.path.splitext(ref[10])[1].lower() in AUDIO_EXTENSIONS:
					self.hide()

	def doMovePicture(self):
		self.posx = random.randint(1,self.maxx)
		self.posy = random.randint(1,self.maxy)
		self["picture"].instance.move(ePoint(self.posx, self.posy))
		self.moveLogoTimer.startLongTimer(5)
