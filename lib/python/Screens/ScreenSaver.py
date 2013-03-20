from Screens.Screen import Screen
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Pixmap import Pixmap
from enigma import ePoint, eTimer, iPlayableService

class Screensaver(Screen):
	def __init__(self, session):

		self.skin = """
			<screen name="Screensaver" position="fill" flags="wfNoBorder">
				<eLabel position="fill" backgroundColor="#54111112" zPosition="0"/>
				<widget name="picture" pixmap="PLi-HD/logos/pli.png" position="0,0" size="120,34" alphatest="on" zPosition="1"/>
			</screen>"""	

		Screen.__init__(self, session)
		
		self.moveLogoTimer = eTimer()
		self.moveLogoTimer.callback.append(self.doMovePicture)
		self.onShow.append(self.__onShow)
		self.onHide.append(self.__onHide)

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evStart: self.hide
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

	def __onHide(self):
		self.moveLogoTimer.stop()

	def __onShow(self):
		self.moveLogoTimer.start(50)

	def doMovePicture(self):
			if self.posx > self.maxx or self.posx < 0:
				self.movex = -self.movex
			self.posx += self.movex
			if self.posy > self.maxy or self.posy < 0:
				self.movey = -self.movey
			self.posy += self.movey		
			self["picture"].instance.move(ePoint(self.posx, self.posy))
			self.moveLogoTimer.start(50)