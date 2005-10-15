from HTMLComponent import *
from GUIComponent import *

from enigma import *

class ServiceList(HTMLComponent, GUIComponent):

	MODE_NORMAL = 0
	MODE_FAVOURITES = 1
	
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
		self.l.sort()
		
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

	def setCurrentMarked(self, state):
		self.l.setCurrentMarked(state)

	def setMode(self, mode):
		if mode == self.MODE_NORMAL:
			self.instance.setItemHeight(20)
			self.l.setVisualMode(eListboxServiceContent.visModeSimple)
		else:
			self.instance.setItemHeight(40)
			self.l.setElementFont(self.l.celServiceName, gFont("Arial", 30))
			self.l.setElementPosition(self.l.celServiceName, eRect(40, 0, self.instance.size().width(), 40))
			self.l.setElementFont(self.l.celServiceNumber, gFont("Arial", 20))
			self.l.setElementPosition(self.l.celServiceNumber, eRect(0, 10, 40, 30))

			self.l.setVisualMode(eListboxServiceContent.visModeComplex)
