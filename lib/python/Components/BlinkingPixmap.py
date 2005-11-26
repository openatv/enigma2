from HTMLComponent import *
from GUIComponent import *

from Pixmap import Pixmap

from enigma import *

import time

class BlinkingPixmap(GUIComponent, Pixmap):
	SHOWN = 0
	HIDDEN = 1
	
	def __init__(self):
		Pixmap.__init__(self)
		GUIComponent.__init__(self)
		
		self.state = self.SHOWN
		self.blinking = False
		
		self.setBlinkTime(500)

		self.timer = eTimer()
		self.timer.timeout.get().append(self.blink)
	
		
	def createWidget(self, parent):
		return self.getePixmap(parent)

	def removeWidget(self, w):
		pass
	
	def showPixmap(self):
		print "Show pixmap"
		self.state = self.SHOWN
		self.instance.show()

	def hidePixmap(self):
		print "Hide pixmap"
		self.state = self.HIDDEN
		self.instance.hide()
		
	def setBlinkTime(self, time):
		self.blinktime = time
		
	def blink(self):
		if self.blinking == True:
			if (self.state == self.SHOWN):
				self.hidePixmap()
			elif (self.state == self.HIDDEN):
				self.showPixmap()
			
	def startBlinking(self):
		self.blinking = True
		self.timer.start(self.blinktime)
		
	def stopBlinking(self):
		self.blinking = False
		if (self.state == self.SHOWN):
			self.hidePixmap()
		self.timer.stop()
		
class BlinkingPixmapConditional(BlinkingPixmap):
	def __init__(self):
		BlinkingPixmap.__init__(self)
		
		self.setConnect(None)
		
		self.conditionCheckTimer = eTimer()
		self.conditionCheckTimer.timeout.get().append(self.conditionallyBlink)
		self.conditionCheckTimer.start(1000)
		
	def setConnect(self, conditionalFunction):
		self.conditionalFunction = conditionalFunction
		
	def conditionallyBlink(self):
		try:
			self.conditionalFunction() # check, if the conditionalfunction is still valid
		except:
			self.conditionalFunction = None
			self.stopBlinking()
			
		if self.conditionalFunction != None:
			if self.conditionalFunction(): # we shall blink
				if self.blinking: # we are already blinking
					pass
				else: # we don't blink
					self.startBlinking()
			else: # we shall not blink
				if self.blinking: # we are blinking
					self.stopBlinking()
				else: # we don't blink
					pass