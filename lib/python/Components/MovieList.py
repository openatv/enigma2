from GUIComponent import GUIComponent
from Tools.FuzzyDate import FuzzyTime
from ServiceReference import ServiceReference
from Components.MultiContent import MultiContentEntryText
from Components.config import config

from enigma import eListboxPythonMultiContent, eListbox, gFont, iServiceInformation, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, eServiceReference, eServiceCenter

class MovieList(GUIComponent):
	SORT_ALPHANUMERIC = 1
	SORT_RECORDED = 2

	LISTTYPE_ORIGINAL = 1
	LISTTYPE_COMPACT_DESCRIPTION = 2
	LISTTYPE_COMPACT = 3
	LISTTYPE_MINIMAL = 4

	HIDE_DESCRIPTION = 1
	SHOW_DESCRIPTION = 2

	def __init__(self, root, list_type=None, sort_type=None, descr_state=None):
		GUIComponent.__init__(self)
		self.list_type = list_type or self.LISTTYPE_ORIGINAL
		self.descr_state = descr_state or self.HIDE_DESCRIPTION
		self.sort_type = sort_type or self.SORT_RECORDED

		self.l = eListboxPythonMultiContent()
		self.tags = set()
		
		if root is not None:
			self.reload(root)
		
		self.redrawList()
		self.l.setBuildFunc(self.buildMovieListEntry)
		
		self.onSelectionChanged = [ ]

	def connectSelChanged(self, fnc):
		if not fnc in self.onSelectionChanged:
			self.onSelectionChanged.append(fnc)

	def disconnectSelChanged(self, fnc):
		if fnc in self.onSelectionChanged:
			self.onSelectionChanged.remove(fnc)

	def selectionChanged(self):
		for x in self.onSelectionChanged:
			x()

	def setListType(self, type):
		self.list_type = type

	def setDescriptionState(self, val):
		self.descr_state = val

	def setSortType(self, type):
		self.sort_type = type

	def redrawList(self):
		if self.list_type == MovieList.LISTTYPE_ORIGINAL:
			self.l.setFont(0, gFont("Regular", 22))
			self.l.setFont(1, gFont("Regular", 18))
			self.l.setFont(2, gFont("Regular", 16))
			self.l.setItemHeight(75)
		elif self.list_type == MovieList.LISTTYPE_COMPACT_DESCRIPTION or self.list_type == MovieList.LISTTYPE_COMPACT:
			self.l.setFont(0, gFont("Regular", 20))
			self.l.setFont(1, gFont("Regular", 14))
			self.l.setItemHeight(37)
		else:
			self.l.setFont(0, gFont("Regular", 20))
			self.l.setFont(1, gFont("Regular", 16))
			self.l.setItemHeight(25)

	#
	# | name of movie              |
	#
	def buildMovieListEntry(self, serviceref, info, begin, len):
		if serviceref.flags & eServiceReference.mustDescent:
			return None

		width = self.l.getItemSize().width()

		if len <= 0: #recalc len when not already done
			cur_idx = self.l.getCurrentSelectionIndex()
			x = self.list[cur_idx]
			if config.usage.load_length_of_movies_in_moviellist.value:
				len = x[1].getLength(x[0]) #recalc the movie length...
			else:
				len = 0 #dont recalc movielist to speedup loading the list
			self.list[cur_idx] = (x[0], x[1], x[2], len) #update entry in list... so next time we don't need to recalc
		
		if len > 0:
			len = "%d:%02d" % (len / 60, len % 60)
		else:
			len = ""
		
		res = [ None ]
		
		txt = info.getName(serviceref)
		service = ServiceReference(info.getInfoString(serviceref, iServiceInformation.sServiceref))
		description = info.getInfoString(serviceref, iServiceInformation.sDescription)
		tags = info.getInfoString(serviceref, iServiceInformation.sTags)

		begin_string = ""
		if begin > 0:
			t = FuzzyTime(begin)
			begin_string = t[0] + ", " + t[1]
		
		if self.list_type == MovieList.LISTTYPE_ORIGINAL:
			res.append(MultiContentEntryText(pos=(0, 0), size=(width-182, 30), font = 0, flags = RT_HALIGN_LEFT, text=txt))
			if self.tags:
				res.append(MultiContentEntryText(pos=(width-180, 0), size=(180, 30), font = 2, flags = RT_HALIGN_RIGHT, text = tags))
				if service is not None:
					res.append(MultiContentEntryText(pos=(200, 50), size=(200, 20), font = 1, flags = RT_HALIGN_LEFT, text = service.getServiceName()))
			else:
				if service is not None:
					res.append(MultiContentEntryText(pos=(width-180, 0), size=(180, 30), font = 2, flags = RT_HALIGN_RIGHT, text = service.getServiceName()))
			res.append(MultiContentEntryText(pos=(0, 30), size=(width, 20), font=1, flags=RT_HALIGN_LEFT, text=description))
			res.append(MultiContentEntryText(pos=(0, 50), size=(200, 20), font=1, flags=RT_HALIGN_LEFT, text=begin_string))
			res.append(MultiContentEntryText(pos=(width-200, 50), size=(198, 20), font=1, flags=RT_HALIGN_RIGHT, text=len))
		elif self.list_type == MovieList.LISTTYPE_COMPACT_DESCRIPTION:
			res.append(MultiContentEntryText(pos=(0, 0), size=(width-120, 20), font = 0, flags = RT_HALIGN_LEFT, text = txt))
			res.append(MultiContentEntryText(pos=(0, 20), size=(width-212, 17), font=1, flags=RT_HALIGN_LEFT, text=description))
			res.append(MultiContentEntryText(pos=(width-120, 6), size=(120, 20), font=1, flags=RT_HALIGN_RIGHT, text=begin_string))
			if service is not None:
				res.append(MultiContentEntryText(pos=(width-212, 20), size=(154, 17), font = 1, flags = RT_HALIGN_RIGHT, text = service.getServiceName()))
			res.append(MultiContentEntryText(pos=(width-58, 20), size=(58, 20), font=1, flags=RT_HALIGN_RIGHT, text=len))
		elif self.list_type == MovieList.LISTTYPE_COMPACT:
			res.append(MultiContentEntryText(pos=(0, 0), size=(width-77, 20), font = 0, flags = RT_HALIGN_LEFT, text = txt))
			if self.tags:
				res.append(MultiContentEntryText(pos=(width-200, 20), size=(200, 17), font = 1, flags = RT_HALIGN_RIGHT, text = tags))
				if service is not None:
					res.append(MultiContentEntryText(pos=(200, 20), size=(200, 17), font = 1, flags = RT_HALIGN_LEFT, text = service.getServiceName()))
			else:
				if service is not None:
					res.append(MultiContentEntryText(pos=(width-200, 20), size=(200, 17), font = 1, flags = RT_HALIGN_RIGHT, text = service.getServiceName()))
			res.append(MultiContentEntryText(pos=(0, 20), size=(200, 17), font=1, flags=RT_HALIGN_LEFT, text=begin_string))
			res.append(MultiContentEntryText(pos=(width-75, 0), size=(75, 20), font=0, flags=RT_HALIGN_RIGHT, text=len))
		else:
			assert(self.list_type == MovieList.LISTTYPE_MINIMAL)
			if self.descr_state == MovieList.SHOW_DESCRIPTION:
				res.append(MultiContentEntryText(pos=(0, 0), size=(width-146, 20), font = 0, flags = RT_HALIGN_LEFT, text = txt))
				res.append(MultiContentEntryText(pos=(width-145, 4), size=(145, 20), font=1, flags=RT_HALIGN_RIGHT, text=begin_string))
			else:
				res.append(MultiContentEntryText(pos=(0, 0), size=(width-77, 20), font = 0, flags = RT_HALIGN_LEFT, text = txt))
				res.append(MultiContentEntryText(pos=(width-75, 0), size=(75, 20), font=0, flags=RT_HALIGN_RIGHT, text=len))
		
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
		instance.selectionChanged.get().append(self.selectionChanged)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

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

	def load(self, root, filter_tags):
		# this lists our root service, then building a 
		# nice list
		
		self.list = [ ]
		self.serviceHandler = eServiceCenter.getInstance()
		
		self.root = root
		list = self.serviceHandler.list(root)
		if list is None:
			print "listing of movies failed"
			list = [ ]	
			return
		tags = set()
		
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
			tags |= this_tags
		
			# filter_tags is either None (which means no filter at all), or 
			# a set. In this case, all elements of filter_tags must be present,
			# otherwise the entry will be dropped.			
			if filter_tags is not None and not this_tags.issuperset(filter_tags):
				continue
		
			self.list.append((serviceref, info, begin, -1))
		
		if self.sort_type == MovieList.SORT_ALPHANUMERIC:
			self.list.sort(key=self.buildAlphaNumericSortKey)
		else:
			# sort: key is 'begin'
			self.list.sort(key=lambda x: -x[2])
		
		# finally, store a list of all tags which were found. these can be presented
		# to the user to filter the list
		self.tags = tags

	def buildAlphaNumericSortKey(self, x):
		ref = x[0]
		info = self.serviceHandler.info(ref)
		name = info and info.getName(ref)
		return (name and name.lower() or "", -x[2])

	def moveTo(self, serviceref):
		count = 0
		for x in self.list:
			if x[0] == serviceref:
				self.instance.moveSelectionTo(count)
				return True
			count += 1
		return False
	
	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)
