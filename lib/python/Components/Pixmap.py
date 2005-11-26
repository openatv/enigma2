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
