from HTMLComponent import *
from GUIComponent import *

from enigma import *

class ServiceList(HTMLComponent, GUIComponent):

	MODE_NORMAL = 0
	MODE_FAVOURITES = 1

	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxServiceContent()
		self.root = None

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

	def getRoot(self):
		return self.root

	def getRootServices(self):
		serviceHandler = eServiceCenter.getInstance()
		list = serviceHandler.list(self.root)
		dest = [ ]
		if list is not None:
			while 1:
				s = list.getNext()
				if s.valid():
					dest.append(s.toString())
				else:
					break
		return dest

	def setRoot(self, root):
		self.root = root
		self.l.setRoot(root)
		self.l.sort()

	def cursorGet(self):
		return self.l.cursorGet()

	def cursorSet(self, val):
		self.l.cursorSet(val)

# stuff for multiple marks (edit mode / later multiepg)
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
			marked.append(ref.toString())
			ref = eServiceReference()
		return marked

#just for movemode.. only one marked entry..
	def setCurrentMarked(self, state):
		self.l.setCurrentMarked(state)

	def setMode(self, mode):
		if mode == self.MODE_NORMAL:
			self.instance.setItemHeight(25)
			self.l.setVisualMode(eListboxServiceContent.visModeSimple)
		else:
			self.instance.setItemHeight(40)
			self.l.setElementFont(self.l.celServiceName, gFont("Arial", 30))
			self.l.setElementPosition(self.l.celServiceName, eRect(40, 0, self.instance.size().width(), 40))
			self.l.setElementFont(self.l.celServiceNumber, gFont("Arial", 20))
			self.l.setElementPosition(self.l.celServiceNumber, eRect(0, 10, 40, 30))
			self.l.setVisualMode(eListboxServiceContent.visModeComplex)
