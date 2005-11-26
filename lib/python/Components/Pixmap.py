import skin

from enigma import *

class Pixmap:
	"""Pixmap can be used for components which diplay a pixmap"""
	
	def __init__(self):
		self.instance = None
	
	def GUIcreate(self, parent):
		self.instance = self.createWidget(parent)
	
	def GUIdelete(self):
		self.removeWidget(self.instance)
		self.instance = None
	
	def getePixmap(self, parent):
		#pixmap = ePixmap(parent)
		#pixmap.setPixmapFromFile(self.filename)
		return ePixmap(parent)
	
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
			self.instance.show()
		else:
			self.instance.hide()

	def update(self):
		if (self.setConnect != None):
			try:
				self.conditionalFunction() # check, if the conditionalfunction is still valid
			except:
				self.conditionalFunction = None
				self.activateCondition(False)
			
			self.activateCondition(self.conditionalFunction())
