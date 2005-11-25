import skin

from enigma import *

class Pixmap:
	"""Pixmap can be used for components which use a pixmap"""
	
	def __init__(self):
		self.instance = None
	
	def GUIcreate(self, parent):
		self.instance = self.createWidget(parent)
		#self.instance.setText(self.message)
	
	def GUIdelete(self):
		self.removeWidget(self.instance)
		self.instance = None
	
	def getePixmap(self, parent, filename):
		pixmap = ePixmap(parent)
		pixmap.setPixmapFromFile(filename)
		return pixmap
	
	def removeWidget(self, instance):
		pass
