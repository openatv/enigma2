import skin
from GUIComponent import *

from enigma import *

class Pixmap(GUIComponent):
	"""Pixmap can be used for components which diplay a pixmap"""
	
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
	
	def getePixmap(self, parent):
		#pixmap = ePixmap(parent)
		#pixmap.setPixmapFromFile(self.filename)
		return ePixmap(parent)
	
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
	
	def removeWidget(self, instance):
		pass

class PixmapConditional(Pixmap):
	def __init__(self, withTimer = True):
		Pixmap.__init__(self)
		
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
				self.showPixmap()
		else:
			if (self.state == self.SHOWN):
				self.hidePixmap()

	def update(self):
		if (self.conditionalFunction != None):
			try:
				self.conditionalFunction() # check, if the conditionalfunction is still valid
			except:
				self.conditionalFunction = None
				self.activateCondition(False)
			
			self.activateCondition(self.conditionalFunction())
