from HTMLComponent import *
from GUIComponent import *
from Tools.FuzzyDate import FuzzyTime
from ServiceReference import ServiceReference
from Components.MultiContent import MultiContentEntryText, RT_HALIGN_LEFT, RT_HALIGN_RIGHT

from enigma import eListboxPythonMultiContent, eListbox, gFont, iServiceInformation

from enigma import eServiceReference, eServiceCenter, \
	eServiceCenterPtr, iListableServicePtr, \
	iStaticServiceInformationPtr

class MovieList(HTMLComponent, GUIComponent):
	def __init__(self, root):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		if root is not None:
			self.reload(root)
		self.l.setFont(0, gFont("Regular", 22))
		self.l.setFont(1, gFont("Regular", 18))
		self.l.setFont(2, gFont("Regular", 16))
		self.l.setBuildFunc(self.buildMovieListEntry)

	#
	# | name of movie              |
	#
	def buildMovieListEntry(self, serviceref, info, begin, len):
		if serviceref.flags & eServiceReference.mustDescent:
			return None

		if len > 0:
			len = "%d:%02d" % (len / 60, len % 60)
		else:
			len = "?:??"

		res = [ None ]

		res.append(MultiContentEntryText(pos=(0, 0), size=(420, 30), font = 0, flags = RT_HALIGN_LEFT, text = info.getName(serviceref)))
		service = ServiceReference(info.getInfoString(serviceref, iServiceInformation.sServiceref))
		if service is not None:
			res.append(MultiContentEntryText(pos=(420, 0), size=(140, 30), font = 2, flags = RT_HALIGN_RIGHT, text = service.getServiceName()))

		description = info.getInfoString(serviceref, iServiceInformation.sDescription)

		begin_string = ""
		if begin > 0:
			t = FuzzyTime(begin)
			begin_string = t[0] + ", " + t[1]

		res.append(MultiContentEntryText(pos=(0, 30), size=(560, 20), font=1, flags=RT_HALIGN_LEFT, text=description))
		res.append(MultiContentEntryText(pos=(0, 50), size=(270, 20), font=1, flags=RT_HALIGN_LEFT, text=begin_string))
		res.append(MultiContentEntryText(pos=(290, 50), size=(270, 20), font=1, flags=RT_HALIGN_RIGHT, text=len))

		return res

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def getCurrentEvent(self):
		l = self.l.getCurrentSelection()
		return l and l[0] and l[1] and l[1].getEvent(l[0])

	def getCurrent(self):
		l = self.l.getCurrentSelection()
		return l and l[0]

	GUI_WIDGET = eListbox
	
	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.setItemHeight(75)
	
	def reload(self, root = None):
		if root is not None:
			self.load(root)
		else:
			self.load(self.root)
		self.l.setList(self.list)

	def removeService(self, service):
		for l in self.list[:]:
			if l[0] == service:
				self.list.remove(l)
		self.l.setList(self.list)

	def __len__(self):
		return len(self.list)

	def updateLengthOfIndex(self, index):
		if len(self.list) > index:
			x = self.list[index]
			self.list[index] = (x[0], x[1], x[2], x[1].getLength(x[0]))
			self.l.invalidateEntry(index)

	def load(self, root):
		# this lists our root service, then building a 
		# nice list
		
		self.list = [ ]
		self.root = root
		
		self.serviceHandler = eServiceCenter.getInstance()
		list = self.serviceHandler.list(root)
		
		if list is None:
			raise "listing of movies failed"

		while 1:
			serviceref = list.getNext()
			if not serviceref.valid():
				break
			if serviceref.flags & eServiceReference.mustDescent:
				continue
			info = self.serviceHandler.info(serviceref)
			if info is None:
				continue
			begin = info.getInfo(serviceref, iServiceInformation.sTimeCreate)
			self.list.append((serviceref, info, begin, -1))
		
		self.list.sort(key=lambda x: -x[2])

	def moveTo(self, serviceref):
		found = 0
		count = 0
		for x in self.list:
			if x[0] == serviceref:
				found = count
			count += 1
		self.instance.moveSelectionTo(found)

	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)
