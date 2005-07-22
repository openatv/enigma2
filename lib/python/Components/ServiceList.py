from HTMLComponent import *
from GUIComponent import *

from enigma import *

class ServiceList(HTMLComponent, GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxServiceContent()
		
	def getCurrent(self):
		r = eServiceReference()
		self.l.getCurrent(r)
		return r
		
	def moveUp(self):
		self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)

	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
	
	def GUIdelete(self):
		self.instance = None

	def setRoot(self, root):
		self.l.setRoot(root)
		
		# mark stuff
	def clearMarked(self):
		self.l.clearMarked()
		
	def clearMarks(self):
		self.l.initMarked()
	
	def isMarked(self, ref):
		return self.l.isMarked(ref)

	def addMarked(self, ref):
		self.l.addMarked(ref)
	
	def removeMarked(self, ref):
		self.l.removeMarked(ref)

	def getMarked(self):
		i = self.l
		i.markedQueryStart()
		ref = eServiceReference()
		marked = [ ]
		while i.markedQueryNext(ref) == 0:
			marked.append(ref)
			ref = eServiceReference()

		return marked
