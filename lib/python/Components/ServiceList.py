from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from skin import parseColor, parseFont

from enigma import eListboxServiceContent, eListbox, eServiceCenter, eServiceReference, gFont, eRect
from Tools.LoadPixmap import LoadPixmap

from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN

from Components.config import config

class ServiceList(HTMLComponent, GUIComponent):
	MODE_NORMAL = 0
	MODE_FAVOURITES = 1

	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxServiceContent()

		pic = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/folder.png"))
		if pic:
			self.l.setPixmap(self.l.picFolder, pic)

		pic = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/marker.png"))
		if pic:
			self.l.setPixmap(self.l.picMarker, pic)

		pic = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "ico_dvb_s-fs8.png"))
		if pic:
			self.l.setPixmap(self.l.picDVB_S, pic)

		pic = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "ico_dvb_c-fs8.png"))
		if pic:
			self.l.setPixmap(self.l.picDVB_C, pic)

		pic = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "ico_dvb_t-fs8.png"))
		if pic:
			self.l.setPixmap(self.l.picDVB_T, pic)

		pic = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "ico_service_group-fs8.png"))
		if pic:
			self.l.setPixmap(self.l.picServiceGroup, pic)

		self.root = None
		self.mode = self.MODE_NORMAL
		self.ItemHeight = 28
		self.ServiceNameFont = parseFont("Regular;22", ((1,1),(1,1)))
		self.ServiceInfoFont = parseFont("Regular;18", ((1,1),(1,1)))
		self.ServiceNumberFont = parseFont("Regular;20", ((1,1),(1,1)))
		self.onSelectionChanged = [ ]

	def applySkin(self, desktop, parent):
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
				elif attrib == "colorEventProgressbar":
					self.l.setColor(eListboxServiceContent.serviceEventProgressbarColor, parseColor(value))
				elif attrib == "colorEventProgressbarSelected":
					self.l.setColor(eListboxServiceContent.serviceEventProgressbarColorSelected, parseColor(value))
				elif attrib == "colorEventProgressbarBorder":
					self.l.setColor(eListboxServiceContent.serviceEventProgressbarBorderColor, parseColor(value))
				elif attrib == "colorEventProgressbarBorderSelected":
					self.l.setColor(eListboxServiceContent.serviceEventProgressbarBorderColorSelected, parseColor(value))
				elif attrib == "colorServiceDescription":
					self.l.setColor(eListboxServiceContent.serviceDescriptionColor, parseColor(value))
				elif attrib == "colorServiceDescriptionSelected":
					self.l.setColor(eListboxServiceContent.serviceDescriptionColorSelected, parseColor(value))
				elif attrib == "picServiceEventProgressbar":
					pic = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, value))
					if pic:
						self.l.setPixmap(self.l.picServiceEventProgressbar, pic)
				elif attrib == "serviceItemHeight":
					self.ItemHeight = int(value)
				elif attrib == "serviceNameFont":
					self.ServiceNameFont = parseFont(value, ((1,1),(1,1)))
				elif attrib == "serviceInfoFont":
					self.ServiceInfoFont = parseFont(value, ((1,1),(1,1)))
				elif attrib == "serviceNumberFont":
					self.ServiceNumberFont = parseFont(value, ((1,1),(1,1)))
				else:
					attribs.append((attrib, value))
		self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop, parent)

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
		indexup = self.l.getNextBeginningWithChar(char.upper())
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

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

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
		self.l.setItemHeight(self.ItemHeight)
		self.l.setVisualMode(eListboxServiceContent.visModeComplex)
		if mode == self.MODE_NORMAL:
			if config.usage.show_event_progress_in_servicelist.value:
				self.l.setElementPosition(self.l.celServiceEventProgressbar, eRect(0, 0, 52, self.ItemHeight))
			else:
				self.l.setElementPosition(self.l.celServiceEventProgressbar, eRect(0, 0, 0, 0))
			self.l.setElementFont(self.l.celServiceName, self.ServiceNameFont)
			self.l.setElementPosition(self.l.celServiceName, eRect(0, 0, self.instance.size().width(), self.ItemHeight))
			self.l.setElementFont(self.l.celServiceInfo, self.ServiceInfoFont)
		else:
			if config.usage.show_event_progress_in_servicelist.value:
				self.l.setElementPosition(self.l.celServiceEventProgressbar, eRect(60, 0, 52, self.ItemHeight))
			else:
				self.l.setElementPosition(self.l.celServiceEventProgressbar, eRect(60, 0, 0, 0))
			self.l.setElementFont(self.l.celServiceNumber, self.ServiceNumberFont)
			self.l.setElementPosition(self.l.celServiceNumber, eRect(0, 0, 50, self.ItemHeight))
			self.l.setElementFont(self.l.celServiceName, self.ServiceNameFont)
			self.l.setElementPosition(self.l.celServiceName, eRect(60, 0, self.instance.size().width()-60, self.ItemHeight))
			self.l.setElementFont(self.l.celServiceInfo, self.ServiceInfoFont)

