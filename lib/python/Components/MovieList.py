from GUIComponent import GUIComponent
from Tools.FuzzyDate import FuzzyTime
from ServiceReference import ServiceReference
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.config import config
import os
import struct
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import SCOPE_HDD, SCOPE_SKIN_IMAGE, resolveFilename

from enigma import eListboxPythonMultiContent, eListbox, gFont, iServiceInformation, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, eServiceReference, eServiceCenter

cutsParser = struct.Struct('>QI') # big-endian, 64-bit PTS and 32-bit type

def moviePlayState(cutsFileName):
	'''Returns None, 0..4 for percentage'''
	try:
		lastCut = None
		cutPTS = None
		f = open(cutsFileName, 'rb')
		while 1:
			data = f.read(cutsParser.size)
			if len(data) < cutsParser.size:
				break
			cut, cutType = cutsParser.unpack(data)
			if cutType == 3: # undocumented, but 3 appears to be the stop
				cutPTS = cut
			else:
				lastCut = cut
		f.close()
		if not cutPTS:
			# Was not played (or played till the end)
			return None
		if not lastCut:
			# dunno, just say 50% then
			return 2
		if cutPTS >= lastCut:
			return 4
		return (4 * cutPTS) // lastCut
	except:
		import sys
		print "Exception in moviePlayState: %s: %s" % sys.exc_info()[:2]
        
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
		self.firstFileEntry = 0
		self.fontName = "Regular"
		self.fontSizesOriginal = (22,18,16)
		self.fontSizesCompact = (20,14)
		self.fontSizesMinimal = (20,16)

		self.l = eListboxPythonMultiContent()
		self.tags = set()
		
		if root is not None:
			self.reload(root)
		
		self.l.setBuildFunc(self.buildMovieListEntry)
		
		self.onSelectionChanged = [ ]
		self.iconPart = []
		for part in range(5):
			self.iconPart.append(LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/part_%d_4.png" % part)))
		self.iconMovieNew = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/part_new.png"))
		self.iconMovieUnknown = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/part_unk.png"))
		self.iconFolder = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/folder.png"))

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

	def applySkin(self, desktop, parent):
		attribs = [ ]
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				try:
					if attrib == "fontName":
						self.fontName = value
					elif attrib == "fontSizesOriginal":
						self.fontSizesOriginal = map(int, value.split(","))
					elif attrib == "fontSizesCompact":
						self.fontSizesCompact = map(int, value.split(","))
					elif attrib == "fontSizesMinimal":
						self.fontSizesMinimal = map(int, value.split(","))
					else:
						attribs.append((attrib, value))
				except Exception, e:
					print '[MovieList] Error "%s" parsing attribute: %s="%s"' % (str(e), attrib,value)					
		self.skinAttributes = attribs
		self.redrawList()
		return GUIComponent.applySkin(self, desktop, parent)

	def redrawList(self):
		if self.list_type == MovieList.LISTTYPE_ORIGINAL:
			for i in range(3):
				self.l.setFont(i, gFont(self.fontName, self.fontSizesOriginal[i]))
			self.itemHeight = 75
		elif self.list_type == MovieList.LISTTYPE_COMPACT_DESCRIPTION or self.list_type == MovieList.LISTTYPE_COMPACT:
			for i in range(2):
				self.l.setFont(i, gFont(self.fontName, self.fontSizesCompact[i]))
			self.itemHeight = 37
		else:
			for i in range(2):
				self.l.setFont(i, gFont(self.fontName, self.fontSizesMinimal[i]))
			self.itemHeight = 25
		self.l.setItemHeight(self.itemHeight)

	def buildMovieListEntry(self, serviceref, info, begin, len):
		width = self.l.getItemSize().width()
		pathName = serviceref.getPath()

		if serviceref.flags & eServiceReference.mustDescent:
			# Directory
			res = [ None ]
			iconSize = 22
			# Name is full path name
			if info is None:
				# Special case: "parent"
				txt = ".."
			else:
				p = os.path.split(pathName)
				if not p[1]:
					# if path ends in '/', p is blank.
					p = os.path.split(p[0])
				txt = p[1]
			res.append(MultiContentEntryPixmapAlphaTest(pos=(0,1), size=(iconSize,iconSize), png=self.iconFolder))
			res.append(MultiContentEntryText(pos=(iconSize+2, 0), size=(width-166, self.itemHeight), font = 0, flags = RT_HALIGN_LEFT, text = txt))
			res.append(MultiContentEntryText(pos=(width-145, 4), size=(145, self.itemHeight), font=1, flags=RT_HALIGN_RIGHT, text=_("Directory")))
			return res

		if len <= 0: #recalc len when not already done
			cur_idx = self.l.getCurrentSelectionIndex()
			x = self.list[cur_idx] # x = ref,info,begin,...
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
		cutsPathName = pathName + '.cuts'
		
		if config.usage.show_icons_in_movielist.value:
			iconSize = 22
			icon = self.iconMovieNew
			if os.path.exists(cutsPathName):
				part = moviePlayState(cutsPathName)
				if part is not None:
					# There's a stop point in the movie, we're watching it
					icon = self.iconPart[part]
				elif os.stat(cutsPathName).st_mtime - os.stat(pathName).st_mtime > 600:  
					# mtime of cuts file is much newer, we've seen it
					icon = self.iconMovieUnknown
			if self.list_type in (MovieList.LISTTYPE_COMPACT_DESCRIPTION,MovieList.LISTTYPE_COMPACT):
				pos = (0,0)
			else:
				pos = (0,1) 
			res.append(MultiContentEntryPixmapAlphaTest(pos=pos, size=(iconSize,20), png=icon))
		else:
			icon = None
			iconSize = 0		

		service = ServiceReference(info.getInfoString(serviceref, iServiceInformation.sServiceref))
		description = info.getInfoString(serviceref, iServiceInformation.sDescription)

		begin_string = ""
		if begin > 0:
			t = FuzzyTime(begin, inPast = True)
			begin_string = t[0] + ", " + t[1]

		if self.list_type == MovieList.LISTTYPE_ORIGINAL:
			res.append(MultiContentEntryText(pos=(iconSize, 0), size=(width-182, 30), font = 0, flags = RT_HALIGN_LEFT, text=txt))
			if self.tags:
				res.append(MultiContentEntryText(pos=(width-180, 0), size=(180, 30), font = 2, flags = RT_HALIGN_RIGHT, text = info.getInfoString(serviceref, iServiceInformation.sTags)))
				if service is not None:
					res.append(MultiContentEntryText(pos=(200, 50), size=(200, 20), font = 1, flags = RT_HALIGN_LEFT, text = service.getServiceName()))
			else:
				if service is not None:
					res.append(MultiContentEntryText(pos=(width-180, 0), size=(180, 30), font = 2, flags = RT_HALIGN_RIGHT, text = service.getServiceName()))
			res.append(MultiContentEntryText(pos=(0, 30), size=(width, 20), font=1, flags=RT_HALIGN_LEFT, text=description))
			res.append(MultiContentEntryText(pos=(0, 50), size=(200, 20), font=1, flags=RT_HALIGN_LEFT, text=begin_string))
			if len:
			     res.append(MultiContentEntryText(pos=(width-200, 50), size=(198, 20), font=1, flags=RT_HALIGN_RIGHT, text=len))
		elif self.list_type == MovieList.LISTTYPE_COMPACT_DESCRIPTION:
			if len:
			     lenSize = 58
			else:
			     lenSize = 0
			res.append(MultiContentEntryText(pos=(iconSize, 0), size=(width-140, 20), font = 0, flags = RT_HALIGN_LEFT, text = txt))
			res.append(MultiContentEntryText(pos=(0, 20), size=(width-154-lenSize, 17), font=1, flags=RT_HALIGN_LEFT, text=description))
			res.append(MultiContentEntryText(pos=(width-120, 6), size=(120, 20), font=1, flags=RT_HALIGN_RIGHT, text=begin_string))
			if service is not None:
				res.append(MultiContentEntryText(pos=(width-154-lenSize, 20), size=(154, 17), font = 1, flags = RT_HALIGN_RIGHT, text = service.getServiceName()))
			if lenSize:
			     res.append(MultiContentEntryText(pos=(width-lenSize, 20), size=(lenSize, 20), font=1, flags=RT_HALIGN_RIGHT, text=len))
		elif self.list_type == MovieList.LISTTYPE_COMPACT:
			if len:
			     lenSize = 75
			else:
			     lenSize = 0
			res.append(MultiContentEntryText(pos=(iconSize, 0), size=(width-lenSize-22, 20), font = 0, flags = RT_HALIGN_LEFT, text = txt))
			if self.tags:
				res.append(MultiContentEntryText(pos=(width-200, 20), size=(200, 17), font = 1, flags = RT_HALIGN_RIGHT, text = info.getInfoString(serviceref, iServiceInformation.sTags)))
				if service is not None:
					res.append(MultiContentEntryText(pos=(200, 20), size=(200, 17), font = 1, flags = RT_HALIGN_LEFT, text = service.getServiceName()))
			else:
				if service is not None:
					res.append(MultiContentEntryText(pos=(width-200, 20), size=(200, 17), font = 1, flags = RT_HALIGN_RIGHT, text = service.getServiceName()))
			res.append(MultiContentEntryText(pos=(0, 20), size=(200, 17), font=1, flags=RT_HALIGN_LEFT, text=begin_string))
			if lenSize:
			     res.append(MultiContentEntryText(pos=(width-lenSize, 0), size=(lenSize, 20), font=0, flags=RT_HALIGN_RIGHT, text=len))
		else:
			assert(self.list_type == MovieList.LISTTYPE_MINIMAL)
			if not len:
				res.append(MultiContentEntryText(pos=(iconSize, 0), size=(width-166, 25), font = 0, flags = RT_HALIGN_LEFT, text = txt))
				res.append(MultiContentEntryText(pos=(width-145, 4), size=(145, 25), font=1, flags=RT_HALIGN_RIGHT, text=begin_string))
			else:
				res.append(MultiContentEntryText(pos=(iconSize, 0), size=(width-97, 25), font = 0, flags = RT_HALIGN_LEFT, text = txt))
				res.append(MultiContentEntryText(pos=(width-75, 0), size=(75, 25), font=0, flags=RT_HALIGN_RIGHT, text=len))
		
		return res

	def moveToFirstMovie(self):
		if self.firstFileEntry < len(self.list):
			self.instance.moveSelectionTo(self.firstFileEntry)
		else:
			# there are no movies, just directories...
			self.instance.moveSelectionTo(0)

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
		numberOfDirs = 0
		
		self.root = root
		reflist = self.serviceHandler.list(root)
		if reflist is None:
			print "listing of movies failed"
			return
		realtags = set()
		tags = {}
		rootPath = os.path.normpath(root.getPath());
		moviePath = os.path.normpath(resolveFilename(SCOPE_HDD))
		if (len(rootPath) > 1) and (rootPath != moviePath):
			parent = os.path.split(os.path.normpath(rootPath))[0]
			ref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + parent + '/')
			ref.flags = eServiceReference.flagDirectory
			self.list.append((ref, None, 0, -1))
			numberOfDirs += 1
		 
		while 1:
			serviceref = reflist.getNext()
			if not serviceref.valid():
				break
			info = self.serviceHandler.info(serviceref)
			if info is None:
				continue
			begin = info.getInfo(serviceref, iServiceInformation.sTimeCreate)
			if serviceref.flags & eServiceReference.mustDescent:
				self.list.append((serviceref, info, begin, -1))
				numberOfDirs += 1
				continue
		
		
			# convert space-seperated list of tags into a set
			this_tags = info.getInfoString(serviceref, iServiceInformation.sTags).split(' ')
			name = info.getName(serviceref)
			if this_tags == ['']:
				# No tags? Auto tag!
				this_tags = [x for x in name.replace(',',' ').replace('.',' ').split() if len(x)>1]
			else:
				realtags.update(this_tags)
			for tag in this_tags:
				if tags.has_key(tag):
					tags[tag].append(name)
				else:
					tags[tag] = [name]
			this_tags = set(this_tags)
		
			# filter_tags is either None (which means no filter at all), or 
			# a set. In this case, all elements of filter_tags must be present,
			# otherwise the entry will be dropped.			
			if filter_tags is not None and not this_tags.issuperset(filter_tags):
				print "Skipping", name, "tags=", this_tags, " filter=", filter_tags
				continue
		
			self.list.append((serviceref, info, begin, -1))
		
		self.firstFileEntry = numberOfDirs
		if self.sort_type == MovieList.SORT_ALPHANUMERIC:
			self.list.sort(key=self.buildAlphaNumericSortKey)
		else:
			# sort: key is 'begin'
			self.list.sort(key=self.buildBeginTimeSortKey)
		
		# finally, store a list of all tags which were found. these can be presented
		# to the user to filter the list
		# ML: Only use the tags that occur more than once in the list OR that were
		# really in the tag set of some file.
		
		# reverse the dictionary to see which unique movie each tag now references
		rtags = {}
		for tag, movies in tags.items():
			if (len(movies) > 1) or (tag in realtags):
				movies = tuple(movies) # a tuple can be hashed, but a list not
				item = rtags.get(movies, [])
				if not item: rtags[movies] = item
				item.append(tag)
		# format the tag lists so that they are in 'original' order
		self.tags = {}
		for movies, tags in rtags.items():
			movie = movies[0]
			tags.sort(key = movie.find)
			self.tags[' '.join(tags)] = set(tags)

	def buildAlphaNumericSortKey(self, x):
		# x = ref,info,begin,...
		ref = x[0]
		name = x[1] and x[1].getName(ref)
		if ref.flags & eServiceReference.mustDescent:
			return (0, name, -x[2])
		return (1, name and name.lower() or "", -x[2])
		
	def buildBeginTimeSortKey(self, x):
		ref = x[0]
		if ref.flags & eServiceReference.mustDescent:
			return (0, x[1] and x[1].getName(ref))
		return (1, -x[2])

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
