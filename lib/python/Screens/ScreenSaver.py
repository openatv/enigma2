import Screens.InfoBar
from Screens.Screen import Screen
from Components.config import config
from Components.Pixmap import Pixmap
from enigma import ePoint, eTimer, eActionMap

def screensaverTimeout():
	InfoBarInstance = Screens.InfoBar.InfoBar.instance
	if InfoBarInstance:
		InfoBarInstance.session.open(Screensaver)

Timer = eTimer()
Timer.callback.append(screensaverTimeout)

def TimerStart():
	time = int(config.usage.screen_saver.value)
	print "[Screensaver] Timer start", time
	if time:
		Timer.startLongTimer(time)
	else:
		Timer.stop()
	
def TimerStop():
	print "[Screensaver] Timer stop"
	Timer.stop()
	
class Screensaver(Screen):
	def __init__(self, session):
		
		self.skin = """
			<screen name="Screensaver" position="fill" flags="wfNoBorder">
				<eLabel position="fill" backgroundColor="transpBlack" zPosition="0"/>
				<widget name="picture" pixmap="PLi-HD/logos/pli.png" position="0,0" size="120,34" alphatest="on" zPosition="1"/>
			</screen>"""	

		Screen.__init__(self, session)
		
		self.moveLogoTimer = eTimer()
		self.moveLogoTimer.callback.append(self.doMovePicture)

		#Do use any key to get quit from the Screensaver
		eActionMap.getInstance().bindAction('', 0, self.keypress)
		
		self["picture"] = Pixmap()
		
		self.onLayoutFinish.append(self.LayoutFinished)

	def LayoutFinished(self):
		picturesize = self["picture"].getSize()
		self.posx = self.posy = 0
		self.movex = self.movey = 1
		self.maxx = self.instance.size().width() - picturesize[0]
		self.maxy = self.instance.size().height() - picturesize[1]
		self.moveLogoTimer.start(50)
				
	def keypress(self, key, flag):
		if flag == 1:
			eActionMap.getInstance().unbindAction('', self.keypress)
			TimerStart()
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