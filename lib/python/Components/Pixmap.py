from ConditionalWidget import *

from enigma import *

class Pixmap(Widget):
	def __init__(self):
		Widget.__init__(self)

	def getePixmap(self, parent):
		#pixmap = ePixmap(parent)
		#pixmap.setPixmapFromFile(self.filename)
		return ePixmap(parent)
	
	def createWidget(self, parent):
		return self.getePixmap(parent)

	def removeWidget(self, w):
		pass

class PixmapConditional(ConditionalWidget, Pixmap):
	def __init__(self, withTimer = True):
		ConditionalWidget.__init__(self)

