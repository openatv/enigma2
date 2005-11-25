from HTMLComponent import *
from GUIComponent import *

from Pixmap import Pixmap

from enigma import *

import time

class BlinkingPoint(GUIComponent, Pixmap):
	SHOWN = 0
	HIDDEN = 1
	
	def __init__(self):
		Pixmap.__init__(self)
		GUIComponent.__init__(self)
		
		self.state = self.SHOWN
		self.blinking = False

		self.timer = eTimer()
		self.timer.timeout.get().append(self.blink)
		
	def createWidget(self, parent):
		return self.getePixmap(parent, "/usr/share/enigma2/record.png")

	def removeWidget(self, w):
		pass
	
	def showPoint(self):
		print "Show point"
		self.state = self.SHOWN
		self.instance.show()

	def hidePoint(self):
		print "Hide point"
		self.state = self.HIDDEN
		self.instance.hide()
		
	def blink(self):
		if self.blinking == True:
			if (self.state == self.SHOWN):
				self.hidePoint()
			elif (self.state == self.HIDDEN):
				self.showPoint()
			
	def startBlinking(self):
		self.blinking = True
		self.timer.start(500)
		
	def stopBlinking(self):
		self.blinking = False
		if (self.state == self.SHOWN):
			self.hidePoint()
		self.timer.stop()