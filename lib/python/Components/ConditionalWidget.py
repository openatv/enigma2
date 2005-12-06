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
	
class ConditionalWidget(Widget):
	def __init__(self, withTimer = True):
		Widget.__init__(self)
		
		self.setConnect(None)
		
		if (withTimer):
			self.conditionCheckTimer = eTimer()
			self.conditionCheckTimer.timeout.get().append(self.update)
			self.conditionCheckTimer.start(500)
		
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
			except:
				self.conditionalFunction = None
				self.activateCondition(False)
			
			self.activateCondition(self.conditionalFunction())
