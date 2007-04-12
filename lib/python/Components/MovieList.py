from GUIComponent import *
from Tools.FuzzyDate import FuzzyTime
from ServiceReference import ServiceReference
from Components.MultiContent import MultiContentEntryText

from enigma import eListboxPythonMultiContent, eListbox, gFont, iServiceInformation, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, eServiceReference, eServiceCenter

class MovieList(GUIComponent):
	def __init__(self, root):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.tags = set()
		if root is not None:
			self.reload(root)
		self.l.setFont(0, gFont("Regular", 22))
		self.l.setFont(1, gFont("Regular", 18))
		self.l.setFont(2, gFont("Regular", 16))
		self.l.setBuildFunc(self.buildMovieListEntry)
		self.l.setItemHeight(75)

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
	
	def reload(self, root = None, filter_tags = None):
		if root is not None:
			self.load(root, filter_tags)
		else:
			self.load(self.root, filter_tags)
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

	def load(self, root, filter_tags):
		# this lists our root service, then building a 
		# nice list
		
		self.list = [ ]
		self.root = root
		
		self.serviceHandler = eServiceCenter.getInstance()
		list = self.serviceHandler.list(root)
		
		tags = set()
		
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
			
			# convert space-seperated list of tags into a set
			this_tags = info.getInfoString(serviceref, iServiceInformation.sTags).split(' ')
			if this_tags == ['']:
				this_tags = []
			this_tags = set(this_tags)
			
			# filter_tags is either None (which means no filter at all), or 
			# a set. In this case, all elements of filter_tags must be present,
			# otherwise the entry will be dropped.			
			if filter_tags is not None and not this_tags.issuperset(filter_tags):
				continue
			
			tags |= this_tags
			self.list.append((serviceref, info, begin, -1))
		
		# sort: key is 'begin'
		self.list.sort(key=lambda x: -x[2])
		
		# finally, store a list of all tags which were found. these can be presented
		# to the user to filter the list
		self.tags = tags

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
