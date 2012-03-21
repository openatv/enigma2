from GUIComponent import GUIComponent
from Tools.FuzzyDate import FuzzyTime
from ServiceReference import ServiceReference
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest, MultiContentEntryProgress
from Components.config import config
import os
import struct
import random
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import SCOPE_HDD, SCOPE_SKIN_IMAGE, resolveFilename
from Screens.LocationBox import defaultInhibitDirs
import NavigationInstance
import skin

from enigma import eListboxPythonMultiContent, eListbox, gFont, iServiceInformation, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, eServiceReference, eServiceCenter, eTimer

cutsParser = struct.Struct('>QI') # big-endian, 64-bit PTS and 32-bit type

class MovieListData:
	pass

# iStaticServiceInformation
class StubInfo:
	def getName(self, serviceref):
		return os.path.split(serviceref.getPath())[1]
	def getLength(self, serviceref):
		return -1
	def getEvent(self, serviceref, *args):
		return None
	def isPlayable(self):
		return True
	def getInfo(self, serviceref, w):
		if w == iServiceInformation.sTimeCreate:
			return os.stat(serviceref.getPath()).st_ctime
		if w == iServiceInformation.sFileSize:
			return os.stat(serviceref.getPath()).st_size
		if w == iServiceInformation.sDescription:
			return serviceref.getPath()
		return 0
	def getInfoString(self, serviceref, w):
		return ''
justStubInfo = StubInfo()

def lastPlayPosFromCache(ref):
	from Screens.InfoBarGenerics import resumePointCache
	return resumePointCache.get(ref.toString(), None)

def moviePlayState(cutsFileName, ref, length):
	'''Returns None, 0..100 for percentage'''
	try:
		# read the cuts file first
		f = open(cutsFileName, 'rb')
		lastCut = None
		cutPTS = None
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
		# See what we have in RAM (it might help)
		last = lastPlayPosFromCache(ref)
		if last:
			# Get the length from the cache
			if not lastCut:
				lastCut = last[2]
			# Get the cut point from the cache if not in the file
			if not cutPTS:
				cutPTS = last[1]
		if not lastCut:
			if length and (length > 0):
				lastCut = length * 90000
			else:
				# dunno
				return 50
		if cutPTS >= lastCut:
			return 100
		return (100 * cutPTS) // lastCut
	except:
		cutPTS = lastPlayPosFromCache(ref)
		if cutPTS:
			if not length or (length<0):
				length = cutPTS[2]
			if length:
			        if cutPTS[1] >= length:
			                return 100
				return (100 * cutPTS[1]) // length
			else:
				return 50
		return None

def resetMoviePlayState(cutsFileName, ref=None):
	try:
		if ref is not None:
			from Screens.InfoBarGenerics import delResumePoint
			delResumePoint(ref)
		f = open(cutsFileName, 'rb')
		cutlist = []
		while 1:
			data = f.read(cutsParser.size)
			if len(data) < cutsParser.size:
				break
			cut, cutType = cutsParser.unpack(data)
			if cutType != 3:
				cutlist.append(data)
		f.close()
		f = open(cutsFileName, 'wb')
		f.write(''.join(cutlist))
		f.close()
	except:
		pass
		#import sys
		#print "Exception in resetMoviePlayState: %s: %s" % sys.exc_info()[:2]

        
class MovieList(GUIComponent):
	SORT_ALPHANUMERIC = 1
	SORT_RECORDED = 2
	SHUFFLE = 3
	SORT_ALPHANUMERIC_REVERSE = 4
	SORT_RECORDED_REVERSE = 5

	LISTTYPE_ORIGINAL = 1
	LISTTYPE_COMPACT_DESCRIPTION = 2
	LISTTYPE_COMPACT = 3
	LISTTYPE_MINIMAL = 4

	HIDE_DESCRIPTION = 1
	SHOW_DESCRIPTION = 2

	def __init__(self, root, list_type=None, sort_type=None, descr_state=None):
		GUIComponent.__init__(self)
		self.list = []
		self.list_type = list_type or self.LISTTYPE_MINIMAL
		self.descr_state = descr_state or self.HIDE_DESCRIPTION
		self.sort_type = sort_type or self.SORT_RECORDED
		self.firstFileEntry = 0
		self.parentDirectory = 0
		self.fontName = "Regular"
		self.fontSizesOriginal = (22,18,16)
		self.fontSizesCompact = (20,14)
		self.fontSizesMinimal = (20,16)
		self.itemHeights = (75,37,25)
		self.reloadDelayTimer = None
		self.l = eListboxPythonMultiContent()
		self.tags = set()
		self.root = None
		self._playInBackground = None
		self._char = ''
		
		if root is not None:
			self.reload(root)
		
		self.l.setBuildFunc(self.buildMovieListEntry)
		
		self.onSelectionChanged = [ ]
		self.iconPart = []
		for part in range(5):
			self.iconPart.append(LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/part_%d_4.png" % part)))
		self.iconMovieRec = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/part_new.png"))
		self.iconMoviePlay = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/movie_play.png"))
		self.iconMoviePlayRec = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/movie_play_rec.png"))
		self.iconUnwatched = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/part_unwatched.png"))
		self.iconFolder = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/folder.png"))
		self.iconTrash = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/trashcan.png"))
		self.runningTimers = {}
		self.updateRecordings()

	def get_playInBackground(self):
		return self._playInBackground

	def set_playInBackground(self, value):
		self._playInBackground = value
		self.reload()

	playInBackground = property(get_playInBackground, set_playInBackground)

	def updateRecordings(self, timer=None):
		if timer is not None:
			if timer.justplay:
				return
		result = {}
		for timer in NavigationInstance.instance.RecordTimer.timer_list:
			if timer.isRunning() and not timer.justplay:
				result[os.path.split(timer.Filename)[1]+'.ts'] = timer
		if self.runningTimers == result:
			return 
		self.runningTimers = result
		if timer is not None:
			if self.reloadDelayTimer is not None:
				self.reloadDelayTimer.stop()
			self.reloadDelayTimer = eTimer()
			self.reloadDelayTimer.callback.append(self.reload)
			self.reloadDelayTimer.start(5000, 1)

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
		if type != self.list_type:
			self.list_type = type
			self.redrawList()

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
					elif attrib == "itemHeights":
						self.itemHeights = map(int, value.split(","))
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
			self.itemHeight = self.itemHeights[0]
		elif self.list_type == MovieList.LISTTYPE_COMPACT_DESCRIPTION or self.list_type == MovieList.LISTTYPE_COMPACT:
			for i in range(2):
				self.l.setFont(i, gFont(self.fontName, self.fontSizesCompact[i]))
			self.itemHeight = self.itemHeights[1]
		else:
			for i in range(2):
				self.l.setFont(i, gFont(self.fontName, self.fontSizesMinimal[i]))
			self.itemHeight = self.itemHeights[2]
		self.l.setItemHeight(self.itemHeight)

	def invalidateItem(self, index):
		x = self.list[index]
		self.list[index] = (x[0], x[1], x[2], None)
		
	def invalidateCurrentItem(self):
		self.invalidateItem(self.getCurrentIndex())

	def buildMovieListEntry(self, serviceref, info, begin, data):
		width = self.l.getItemSize().width()
		pathName = serviceref.getPath()
		res = [ None ]

		if serviceref.flags & eServiceReference.mustDescent:
			# Directory
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
				if txt == ".Trash":
					res.append(MultiContentEntryPixmapAlphaTest(pos=(0,1), size=(iconSize,24), png=self.iconTrash))
					res.append(MultiContentEntryText(pos=(iconSize+2, 0), size=(width-166, self.itemHeight), font = 0, flags = RT_HALIGN_LEFT, text = _("Deleted items")))
					res.append(MultiContentEntryText(pos=(width-145, 4), size=(145, self.itemHeight), font=1, flags=RT_HALIGN_RIGHT, text=_("Trashcan")))
					return res
			res.append(MultiContentEntryPixmapAlphaTest(pos=(0,1), size=(iconSize,iconSize), png=self.iconFolder))
			res.append(MultiContentEntryText(pos=(iconSize+2, 0), size=(width-166, self.itemHeight), font = 0, flags = RT_HALIGN_LEFT, text = txt))
			res.append(MultiContentEntryText(pos=(width-145, 4), size=(145, self.itemHeight), font=1, flags=RT_HALIGN_RIGHT, text=_("Directory")))
			return res
		if (data == -1) or (data is None):
			data = MovieListData()
			cur_idx = self.l.getCurrentSelectionIndex()
			x = self.list[cur_idx] # x = ref,info,begin,...
			if config.usage.load_length_of_movies_in_moviellist.value:
				data.len = x[1].getLength(x[0]) #recalc the movie length...
			else:
				data.len = 0 #dont recalc movielist to speedup loading the list
			self.list[cur_idx] = (x[0], x[1], x[2], data) #update entry in list... so next time we don't need to recalc
			data.txt = info.getName(serviceref)
			data.icon = None
			data.part = None
			if os.path.split(pathName)[1] in self.runningTimers:
				if self.playInBackground and serviceref == self.playInBackground:
					data.icon = self.iconMoviePlayRec
				else:
					data.icon = self.iconMovieRec
			elif self.playInBackground and serviceref == self.playInBackground:
				data.icon = self.iconMoviePlay
			else:
				switch = config.usage.show_icons_in_movielist.value
				data.part = moviePlayState(pathName + '.cuts', serviceref, data.len)
				if switch == 'i':
					if data.part is None:
						if config.usage.movielist_unseen.value:
							data.icon = self.iconUnwatched
					else:
						data.icon = self.iconPart[data.part // 25]
				elif switch == 'p' or switch == 's':
					if data.part is None:
						if config.usage.movielist_unseen.value:
							data.part = 0
						data.partcol = 0x808080
					else:
						data.partcol = 0xf0f0f0
			service = ServiceReference(info.getInfoString(serviceref, iServiceInformation.sServiceref))
			if service is None:
				data.serviceName = None
			else:
				data.serviceName = service.getServiceName()
			data.description = info.getInfoString(serviceref, iServiceInformation.sDescription)

		len = data.len		
		if len > 0:
			len = "%d:%02d" % (len / 60, len % 60)
		else:
			len = ""

		if data.icon is not None: 
			iconSize = 22
			if self.list_type in (MovieList.LISTTYPE_COMPACT_DESCRIPTION,MovieList.LISTTYPE_COMPACT):
				pos = (0,0)
			else:
				pos = (0,1)
			res.append(MultiContentEntryPixmapAlphaTest(pos=pos, size=(iconSize,20), png=data.icon))
		switch = config.usage.show_icons_in_movielist.value
		if switch == 'p' or switch == 's':
			if switch == 'p':
				iconSize = 48
			else:
				iconSize = 22
			if data.part is not None:
				res.append(MultiContentEntryProgress(pos=(0,5), size=(iconSize-2,16), percent=data.part, borderWidth=2, foreColor=data.partcol, foreColorSelected=None, backColor=None, backColorSelected=None))
		elif switch == 'i':
			iconSize = 22
		else:
			iconSize = 0		

		begin_string = ""
		if begin > 0:
			begin_string = ', '.join(FuzzyTime(begin, inPast = True))

		ih = self.itemHeight
		if self.list_type == MovieList.LISTTYPE_ORIGINAL:
			ih1 = (ih * 2) / 5 # 75 -> 30
			ih2 = (ih * 2) / 3 # 75 -> 50 
			res.append(MultiContentEntryText(pos=(iconSize, 0), size=(width-182, ih1), font = 0, flags = RT_HALIGN_LEFT, text=data.txt))
			if self.tags:
				res.append(MultiContentEntryText(pos=(width-180, 0), size=(180, ih1), font = 2, flags = RT_HALIGN_RIGHT, text = info.getInfoString(serviceref, iServiceInformation.sTags)))
				if data.serviceName:
					res.append(MultiContentEntryText(pos=(200, ih2), size=(200, ih2-ih1), font = 1, flags = RT_HALIGN_LEFT, text = data.serviceName))
			else:
				if data.serviceName:
					res.append(MultiContentEntryText(pos=(width-180, 0), size=(180, ih1), font = 2, flags = RT_HALIGN_RIGHT, text = data.serviceName))
			res.append(MultiContentEntryText(pos=(0, ih1), size=(width, ih2-ih1), font=1, flags=RT_HALIGN_LEFT, text=data.description))
			res.append(MultiContentEntryText(pos=(0, ih2), size=(200, ih-ih2), font=1, flags=RT_HALIGN_LEFT, text=begin_string))
			if len:
			     res.append(MultiContentEntryText(pos=(width-200, ih2), size=(198, ih-ih2), font=1, flags=RT_HALIGN_RIGHT, text=len))
		elif self.list_type == MovieList.LISTTYPE_COMPACT_DESCRIPTION:
			ih1 = ((ih * 8) + 14) / 15 # 37 -> 20, round up
			if len:
			     lenSize = 58 * ih / 37
			else:
			     lenSize = 0
			res.append(MultiContentEntryText(pos=(iconSize, 0), size=(width-140, ih1), font = 0, flags = RT_HALIGN_LEFT, text = data.txt))
			res.append(MultiContentEntryText(pos=(0, ih1), size=(width-154-lenSize, ih-ih1), font=1, flags=RT_HALIGN_LEFT, text=data.description))
			res.append(MultiContentEntryText(pos=(width-120, 6), size=(120, ih1), font=1, flags=RT_HALIGN_RIGHT, text=begin_string))
			if data.serviceName:
				res.append(MultiContentEntryText(pos=(width-154-lenSize, ih1), size=(154, ih-ih1), font = 1, flags = RT_HALIGN_RIGHT, text = data.serviceName))
			if lenSize:
			     res.append(MultiContentEntryText(pos=(width-lenSize, ih1), size=(lenSize, ih-ih1), font=1, flags=RT_HALIGN_RIGHT, text=len))
		elif self.list_type == MovieList.LISTTYPE_COMPACT:
			ih1 = ((ih * 8) + 14) / 15 # 37 -> 20, round up
			if len:
			     lenSize = 2 * ih
			else:
			     lenSize = 0
			res.append(MultiContentEntryText(pos=(iconSize, 0), size=(width-lenSize-iconSize, ih1), font = 0, flags = RT_HALIGN_LEFT, text = data.txt))
			if self.tags:
				res.append(MultiContentEntryText(pos=(width-200, ih1), size=(200, ih-ih1), font = 1, flags = RT_HALIGN_RIGHT, text = info.getInfoString(serviceref, iServiceInformation.sTags)))
				if data.serviceName:
					res.append(MultiContentEntryText(pos=(200, ih1), size=(200, ih-ih1), font = 1, flags = RT_HALIGN_LEFT, text = data.serviceName))
			else:
				if data.serviceName:
					res.append(MultiContentEntryText(pos=(width-200, ih1), size=(200, ih-ih1), font = 1, flags = RT_HALIGN_RIGHT, text = data.serviceName))
			res.append(MultiContentEntryText(pos=(0, ih1), size=(200, ih-ih1), font=1, flags=RT_HALIGN_LEFT, text=begin_string))
			if lenSize:
			     res.append(MultiContentEntryText(pos=(width-lenSize, 0), size=(lenSize, ih1), font=0, flags=RT_HALIGN_RIGHT, text=len))
		else:
			if (self.descr_state == MovieList.SHOW_DESCRIPTION) or not len:
				dateSize = ih * 145 / 25   # 25 -> 145
				res.append(MultiContentEntryText(pos=(iconSize, 0), size=(width-iconSize-dateSize, ih), font = 0, flags = RT_HALIGN_LEFT, text = data.txt))
				res.append(MultiContentEntryText(pos=(width-dateSize, 4), size=(dateSize, ih), font=1, flags=RT_HALIGN_RIGHT, text=begin_string))
			else:
				lenSize = ih * 3 # 25 -> 75
				res.append(MultiContentEntryText(pos=(iconSize, 0), size=(width-lenSize-iconSize, ih), font = 0, flags = RT_HALIGN_LEFT, text = data.txt))
				res.append(MultiContentEntryText(pos=(width-lenSize, 0), size=(lenSize, ih), font=0, flags=RT_HALIGN_RIGHT, text=len))
		return res

	def moveToFirstMovie(self):
		if self.firstFileEntry < len(self.list):
			self.instance.moveSelectionTo(self.firstFileEntry)
		else:
			# there are no movies, just directories...
			self.moveToFirst()
	
	def moveToParentDirectory(self):
		if self.parentDirectory < len(self.list):
			self.instance.moveSelectionTo(self.parentDirectory)
		else:
			self.moveToFirst()
	
	def moveToLast(self):
		if self.list:
			self.instance.moveSelectionTo(len(self.list) - 1)

	def moveToFirst(self):
		if self.list:
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
		
	def getItem(self, index):
		if self.list:
			if len(self.list) > index:
				return self.list[index] and self.list[index][0]
					
	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

	def reload(self, root = None, filter_tags = None):
		if self.reloadDelayTimer is not None:
			self.reloadDelayTimer.stop()
			self.reloadDelayTimer = None
		if root is not None:
			self.load(root, filter_tags)
		else:
			self.load(self.root, filter_tags)
		self.l.setList(self.list)

	def removeService(self, service):
		for index, l in enumerate(self.list):
			if l[0] == service:
				del self.list[index]
				break
		self.l.setList(self.list)

	def __len__(self):
		return len(self.list)

	def load(self, root, filter_tags):
		# this lists our root service, then building a 
		# nice list
		
		self.list = [ ]
		serviceHandler = eServiceCenter.getInstance()
		numberOfDirs = 0
		
		reflist = serviceHandler.list(root)
		if reflist is None:
			print "listing of movies failed"
			return
		realtags = set()
		tags = {}
		rootPath = os.path.normpath(root.getPath());
		parent = None
		# Don't navigate above the "root"
		if len(rootPath) > 1 and (os.path.realpath(rootPath) != config.movielist.root.value):
			parent = os.path.split(os.path.normpath(rootPath))[0]
			if parent and (parent not in defaultInhibitDirs):
				# enigma wants an extra '/' appended
				if not parent.endswith('/'):
					parent += '/'
				ref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + parent)
				ref.flags = eServiceReference.flagDirectory
				self.list.append((ref, None, 0, -1))
				numberOfDirs += 1
		while 1:
			serviceref = reflist.getNext()
			if not serviceref.valid():
				break
			info = serviceHandler.info(serviceref)
			if info is None:
				info = justStubInfo 
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
		self.parentDirectory = 0
		if self.sort_type == MovieList.SORT_ALPHANUMERIC:
			self.list.sort(key=self.buildAlphaNumericSortKey)
		else:
			#always sort first this way to avoid shuffle and reverse-sort directories
			self.list.sort(key=self.buildBeginTimeSortKey)
		if self.sort_type == MovieList.SHUFFLE:
			dirlist = self.list[:numberOfDirs]
			shufflelist = self.list[numberOfDirs:]
			random.shuffle(shufflelist)
			self.list = dirlist + shufflelist
		elif self.sort_type == MovieList.SORT_ALPHANUMERIC_REVERSE:
			self.list = self.list[:numberOfDirs] + sorted(self.list[numberOfDirs:], key=self.buildAlphaNumericSortKey, reverse = True)
		elif self.sort_type == MovieList.SORT_RECORDED_REVERSE:
			self.list = self.list[:numberOfDirs] + sorted(self.list[numberOfDirs:], key=self.buildBeginTimeSortKey, reverse = True)
	
		if self.root and numberOfDirs > 0:
			rootPath = os.path.normpath(self.root.getPath())
			if not rootPath.endswith('/'):
				rootPath += '/'
			if rootPath != parent:
				dirlist = self.list[:numberOfDirs]
				for index, item in enumerate(dirlist):
					itempath = os.path.normpath(item[0].getPath())
					if not itempath.endswith('/'):
						itempath += '/'
					if itempath == rootPath: 
						self.parentDirectory = index
						break
		self.root = root
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
			return (0, name and name.lower() or "", -x[2])
		return (1, name and name.lower() or "", -x[2])
		
	def buildBeginTimeSortKey(self, x):
		ref = x[0]
		if ref.flags & eServiceReference.mustDescent:
			return (0, x[1] and x[1].getName(ref).lower() or "")
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

	def moveUp(self):
		self.instance.moveSelection(self.instance.moveUp)
		
	def moveToChar(self, char, lbl=None):
		self._char = char
		self._lbl = lbl
		if lbl:			
			lbl.setText(self._char)
			lbl.visible = True
		self.moveToCharTimer = eTimer()
		self.moveToCharTimer.callback.append(self._moveToChrStr)
		self.moveToCharTimer.start(1000, True) #time to wait for next key press to decide which letter to use...

	def moveToString(self, char, lbl=None):
		self._char = self._char + char.upper()
		self._lbl = lbl
		if lbl:			
			lbl.setText(self._char)
			lbl.visible = True
		self.moveToCharTimer = eTimer()
		self.moveToCharTimer.callback.append(self._moveToChrStr)
		self.moveToCharTimer.start(1000, True) #time to wait for next key press to decide which letter to use...

	def _moveToChrStr(self):
		currentIndex = self.instance.getCurrentIndex()
		found = False
		if currentIndex < (len(self.list) - 1):
			itemsBelow = self.list[currentIndex + 1:]
			#first search the items below the selection
			for index, item in enumerate(itemsBelow):
				ref = item[0]
				itemName = getShortName(item[1].getName(ref).upper(), ref)
				if len(self._char) == 1 and itemName.startswith(self._char):
					found = True
					self.instance.moveSelectionTo(index + currentIndex + 1)
					break
				elif len(self._char) > 1 and itemName.find(self._char) >= 0:
					found = True
					self.instance.moveSelectionTo(index + currentIndex + 1)
					break
		if found == False and currentIndex > 0:
			itemsAbove = self.list[1:currentIndex] #first item (0) points parent folder - no point to include
			for index, item in enumerate(itemsAbove):
				ref = item[0]
				itemName = getShortName(item[1].getName(ref).upper(), ref)
				if len(self._char) == 1 and itemName.startswith(self._char):
					found = True
					self.instance.moveSelectionTo(index + 1)
					break
				elif len(self._char) > 1 and itemName.find(self._char) >= 0:
					found = True
					self.instance.moveSelectionTo(index + 1)
					break

		self._char = ''
		if self._lbl:
			self._lbl.visible = False			

def getShortName(name, serviceref):
	if serviceref.flags & eServiceReference.mustDescent: #Directory			
		pathName = serviceref.getPath()
		p = os.path.split(pathName)
		if not p[1]: #if path ends in '/', p is blank.
			p = os.path.split(p[0])
		return p[1].upper()
	else:
		return name
