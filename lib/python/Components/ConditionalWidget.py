import skin
from GUIComponent import *

from enigma import *

class Widget(GUIComponent):
	
	SHOWN = 0
	HIDDEN = 1
	
	def __init__(self):
		GUIComponent.__init__(self)
		self.instance = None
		self.state = self.SHOWN
	
	def GUIcreate(self, parent):
		self.instance = self.createWidget(parent)
	
	def GUIdelete(self):
		self.removeWidget(self.instance)
		self.instance = None
	
	def removeWidget(self, w):
		pass
	
	def showWidget(self):
		self.state = self.SHOWN
		self.instance.show()

	def hideWidget(self):
		self.state = self.HIDDEN
		self.instance.hide()
		
	def move(self, x, y):
		self.instance.move(ePoint(int(x), int(y)))
	
class ConditionalWidget(Widget):
	def __init__(self, withTimer = True):
		Widget.__init__(self)
		
		self.setConnect(None)
		
		if (withTimer):
			self.conditionCheckTimer = eTimer()
			self.conditionCheckTimer.timeout.get().append(self.update)
			self.conditionCheckTimer.start(1000)
		
	def setConnect(self, conditionalFunction):
		self.conditionalFunction = conditionalFunction
		
	def activateCondition(self, condition):
		if (condition):
			if (self.state == self.HIDDEN):
				self.showWidget()
		else:
			if (self.state == self.SHOWN):
				self.hideWidget()

	def update(self):
		if (self.conditionalFunction != None):
			try:
				self.conditionalFunction() # check, if the conditionalfunction is still valid
				self.activateCondition(self.conditionalFunction())
			except:
				self.conditionalFunction = None
				self.activateCondition(False)
			


			
			
import time

class BlinkingWidget(Widget):
	def __init__(self):
		Widget.__init__(self)
		
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
		
class BlinkingWidgetConditional(BlinkingWidget, ConditionalWidget):
	def __init__(self):
		BlinkingWidget.__init__(self)
		ConditionalWidget.__init__(self)
		
	def activateCondition(self, condition):
		if (condition):
			if not self.blinking: # we are already blinking
				self.startBlinking()
		else:
			if self.blinking: # we are blinking
				self.stopBlinking()			