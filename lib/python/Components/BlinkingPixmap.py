from Pixmap import *

from enigma import *

import time

class BlinkingPixmap(Pixmap):
	def __init__(self):
		Pixmap.__init__(self)
		
		self.blinking = True
		
		self.setBlinkTime(500)

		self.timer = eTimer()
		self.timer.timeout.get().append(self.blink)
	
	def setBlinkTime(self, time):
		self.blinktime = time
		
	def blink(self):
		if self.blinking == True:
			if (self.state == self.SHOWN):
				self.hideWidget()
			elif (self.state == self.HIDDEN):
				self.showWidget()
			
	def startBlinking(self):
		self.blinking = True
		self.timer.start(self.blinktime)
		
	def stopBlinking(self):
		self.blinking = False
		if (self.state == self.SHOWN):
			self.hideWidget()
		self.timer.stop()
		
class BlinkingPixmapConditional(BlinkingPixmap, PixmapConditional):
	def __init__(self):
		BlinkingPixmap.__init__(self)
		PixmapConditional.__init__(self)
		
	def activateCondition(self, condition):
		if (condition):
			if not self.blinking: # we are already blinking
				self.startBlinking()
		else:
			if self.blinking: # we are blinking
				self.stopBlinking()
