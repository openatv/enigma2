from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from skin import parseColor

from enigma import loadPNG, eListboxServiceContent, eListbox, eServiceCenter, eServiceReference, gFont, eRect

from string import upper

from Tools.Directories import resolveFilename, SCOPE_SKIN_IMAGE

class ServiceList(HTMLComponent, GUIComponent):
	MODE_NORMAL = 0
	MODE_FAVOURITES = 1

	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxServiceContent()

		pic = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "folder.png"))
		if pic:
			self.l.setPixmap(self.l.picFolder, pic)

		pic = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "marker-fs8.png"))
		if pic:
			self.l.setPixmap(self.l.picMarker, pic)

		pic = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "ico_dvb_s-fs8.png"))
		if pic:
			self.l.setPixmap(self.l.picDVB_S, pic)

		pic = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "ico_dvb_c-fs8.png"))
		if pic:
			self.l.setPixmap(self.l.picDVB_C, pic)

		pic = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "ico_dvb_t-fs8.png"))
		if pic:
			self.l.setPixmap(self.l.picDVB_T, pic)

		pic = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "ico_service_group-fs8.png"))
		if pic:
			self.l.setPixmap(self.l.picServiceGroup, pic)

		self.root = None
		self.mode = self.MODE_NORMAL
		self.onSelectionChanged = [ ]

	def applySkin(self, desktop):
		attribs = [ ]
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "foregroundColorMarked":
					self.l.setColor(eListboxServiceContent.markedForeground, parseColor(value))
				elif attrib == "foregroundColorMarkedSelected":
					self.l.setColor(eListboxServiceContent.markedForegroundSelected, parseColor(value))
				elif attrib == "backgroundColorMarked":
					self.l.setColor(eListboxServiceContent.markedBackground, parseColor(value))
				elif attrib == "backgroundColorMarkedSelected":
					self.l.setColor(eListboxServiceContent.markedBackgroundSelected, parseColor(value))
				elif attrib == "foregroundColorServiceNotAvail":
					self.l.setColor(eListboxServiceContent.serviceNotAvail, parseColor(value))
				else:
					attribs.append((attrib, value))
		self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop)

	def connectSelChanged(self, fnc):
		if not fnc in self.onSelectionChanged:
			self.onSelectionChanged.append(fnc)

	def disconnectSelChanged(self, fnc):
		if fnc in self.onSelectionChanged:
			self.onSelectionChanged.remove(fnc)

	def selectionChanged(self):
		for x in self.onSelectionChanged:
			x()

	def setCurrent(self, ref):
		self.l.setCurrent(ref)

	def getCurrent(self):
		r = eServiceReference()
		self.l.getCurrent(r)
		return r

	def atBegin(self):
		return self.instance.atBegin()

	def atEnd(self):
		return self.instance.atEnd()

	def moveUp(self):
		self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)

	def moveToChar(self, char):
		# TODO fill with life
		print "Next char: "
		index = self.l.getNextBeginningWithChar(char)
		indexup = self.l.getNextBeginningWithChar(upper(char))
		if indexup != 0:
			if (index > indexup or index == 0):
				index = indexup

		self.instance.moveSelectionTo(index)
		print "Moving to character " + str(char)

	def moveToNextMarker(self):
		idx = self.l.getNextMarkerPos()
		self.instance.moveSelectionTo(idx)

	def moveToPrevMarker(self):
		idx = self.l.getPrevMarkerPos()
		self.instance.moveSelectionTo(idx)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	GUI_WIDGET = eListbox
	
	def postWidgetCreate(self, instance):
		instance.setWrapAround(True)
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
		self.setMode(self.mode)

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

	def setNumberOffset(self, offset):
		self.l.setNumberOffset(offset)

	def setPlayableIgnoreService(self, ref):
		self.l.setIgnoreService(ref)

	def setRoot(self, root, justSet=False):
		self.root = root
		self.l.setRoot(root, justSet)
		if not justSet:
			self.l.sort()
		self.selectionChanged()

	def removeCurrent(self):
		self.l.removeCurrent()

	def addService(self, service, beforeCurrent=False):
		self.l.addService(service, beforeCurrent)

	def finishFill(self):
		self.l.FillFinished()
		self.l.sort()

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
		self.mode = mode

		if mode == self.MODE_NORMAL:
			self.l.setItemHeight(28)
			self.l.setVisualMode(eListboxServiceContent.visModeComplex)
			self.l.setElementFont(self.l.celServiceName, gFont("Regular", 22))
			self.l.setElementPosition(self.l.celServiceName, eRect(0, 0, self.instance.size().width(), 28))
			self.l.setElementFont(self.l.celServiceInfo, gFont("Regular", 18))
		else:
			self.l.setItemHeight(28)
			self.l.setVisualMode(eListboxServiceContent.visModeComplex)
			self.l.setElementFont(self.l.celServiceNumber, gFont("Regular", 20))
			self.l.setElementPosition(self.l.celServiceNumber, eRect(0, 0, 50, 28))
			self.l.setElementFont(self.l.celServiceName, gFont("Regular", 22))
			self.l.setElementPosition(self.l.celServiceName, eRect(60, 0, self.instance.size().width()-60, 28))
			self.l.setElementFont(self.l.celServiceInfo, gFont("Regular", 18))
