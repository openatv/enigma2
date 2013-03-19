import Screens.InfoBar
from Screens import Standby
from Screens.Screen import Screen
from Components.config import config
from Components.ServiceEventTracker import ServiceEventTracker
from Components.MovieList import AUDIO_EXTENSIONS
from Components.Pixmap import Pixmap
from enigma import ePoint, eTimer, eActionMap, iPlayableService
import os

inScreenSaver = False

def screensaverTimeout():
	if not inScreenSaver and not Standby.inStandby and not Standby.inTryQuitMainloop:
		InfoBarInstance = Screens.InfoBar.InfoBar.instance
		if InfoBarInstance:
			InfoBarInstance.session.open(Screensaver)

ScreenSaverTimer = eTimer()
ScreenSaverTimer.callback.append(screensaverTimeout)

def TimerStart(flag):
	time = int(config.usage.screen_saver.value)
	if not flag:
		InfoBarInstance = Screens.InfoBar.InfoBar.instance
		if InfoBarInstance:
			ref = InfoBarInstance.session.nav.getCurrentlyPlayingServiceOrGroup()
			if ref:
				ref = ref.toString().split(":")
				flag = ref[2] == "2" or os.path.splitext(ref[10])[1].lower() in AUDIO_EXTENSIONS
	if time and flag:
		ScreenSaverTimer.startLongTimer(time)
	else:
		ScreenSaverTimer.stop()

class Screensaver(Screen):
	def __init__(self, session):
		
		self.skin = """
			<screen name="Screensaver" position="fill" flags="wfNoBorder">
				<eLabel position="fill" backgroundColor="#54111112" zPosition="0"/>
				<widget name="picture" pixmap="PLi-HD/logos/pli.png" position="0,0" size="120,34" alphatest="on" zPosition="1"/>
			</screen>"""	

		Screen.__init__(self, session)
		
		global inScreenSaver
		inScreenSaver = True

		self.moveLogoTimer = eTimer()
		self.moveLogoTimer.callback.append(self.doMovePicture)
		self.onClose.append(self.__onClose)

		#Do use any key to get quit from the Screensaver
		eActionMap.getInstance().bindAction('', 0, self.keypress)
		
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evStart: self.close,
			})

		self["picture"] = Pixmap()
		
		self.onLayoutFinish.append(self.LayoutFinished)

	def LayoutFinished(self):
		picturesize = self["picture"].getSize()
		self.maxx = self.instance.size().width() - picturesize[0]
		self.maxy = self.instance.size().height() - picturesize[1]
		import random
		self.posx = random.randint(1,self.maxx)
		self.posy = random.randint(1,self.maxy)
		self.movex = self.movey = 1
		self.moveLogoTimer.start(50)

	def __onClose(self):
		eActionMap.getInstance().unbindAction('', self.keypress)
		global inScreenSaver
		inScreenSaver = False

	def keypress(self, key, flag):
		if flag == 1:
			TimerStart(True)
			self.close()

	def doMovePicture(self):
			if self.posx > self.maxx or self.posx < 0:
				self.movex = -self.movex
			self.posx += self.movex
			if self.posy > self.maxy or self.posy < 0:
				self.movey = -self.movey
			self.posy += self.movey		
			self["picture"].instance.move(ePoint(self.posx, self.posy))
			self.moveLogoTimer.start(50)