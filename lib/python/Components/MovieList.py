import os
import struct
import random

from enigma import eListboxPythonMultiContent, eListbox, gFont, iServiceInformation, eSize, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER, eServiceReference, eServiceCenter, eTimer, getDesktop, loadPNG, BT_SCALE, BT_KEEP_ASPECT_RATIO

from GUIComponent import GUIComponent
from Tools.FuzzyDate import FuzzyTime
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest, MultiContentEntryPixmapAlphaBlend, MultiContentEntryProgress
from Components.config import config
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import SCOPE_ACTIVE_SKIN, resolveFilename
from Screens.LocationBox import defaultInhibitDirs
from ServiceReference import ServiceReference
from Components.Renderer.Picon import getPiconName
import NavigationInstance
import skin


AUDIO_EXTENSIONS = frozenset((".dts", ".mp3", ".wav", ".wave", ".ogg", ".flac", ".m4a", ".mp2", ".m2a", ".3gp", ".3g2", ".asf", ".wma"))
DVD_EXTENSIONS = ('.iso', '.img')
IMAGE_EXTENSIONS = frozenset((".jpg", ".png", ".gif", ".bmp"))
MOVIE_EXTENSIONS = frozenset((".mpg", ".vob", ".wav", ".m4v", ".mkv", ".avi", ".divx", ".dat", ".flv", ".mp4", ".mov", ".wmv", ".m2ts"))
KNOWN_EXTENSIONS = MOVIE_EXTENSIONS.union(IMAGE_EXTENSIONS, DVD_EXTENSIONS, AUDIO_EXTENSIONS)
RECORD_EXTENSIONS = (".ts")

cutsParser = struct.Struct('>QI') # big-endian, 64-bit PTS and 32-bit type

class MovieListData:
	def __init__(self):
		pass

# iStaticServiceInformation
class StubInfo:
	def __init__(self):
		pass

	def getName(self, serviceref):
		return os.path.split(serviceref.getPath())[1]
	def getLength(self, serviceref):
		return -1
	def getEvent(self, serviceref, *args):
		return None
	def isPlayable(self):
		return True
	def getInfo(self, serviceref, w):
		try:
			if w == iServiceInformation.sTimeCreate:
				return os.stat(serviceref.getPath()).st_ctime
			if w == iServiceInformation.sFileSize:
				return os.stat(serviceref.getPath()).st_size
			if w == iServiceInformation.sDescription:
				return serviceref.getPath()
		except:
			pass
		return 0
	def getInfoString(self, serviceref, w):
		return ''
justStubInfo = StubInfo()

def lastPlayPosFromCache(ref):
	from Screens.InfoBarGenerics import resumePointCache
	return resumePointCache.get(ref.toString(), None)

def moviePlayState(cutsFileName, ref, length):
	"""Returns None, 0..100 for percentage"""
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
		if cutPTS is None:
			# Unseen movie
			return None
		if not lastCut:
			if length and (length > 0):
				lastCut = length * 90000
			else:
				# dunno
				return 0
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
				return 0
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
	SORT_ALPHANUMERIC_FLAT = 6
	SORT_ALPHANUMERIC_FLAT_REVERSE = 7
	SORT_GROUPWISE = 8
	SORT_ALPHA_DATE_OLDEST_FIRST = 9
	SORT_ALPHAREV_DATE_NEWEST_FIRST = 10

	HIDE_DESCRIPTION = 1
	SHOW_DESCRIPTION = 2

	def __init__(self, root, sort_type=None, descr_state=None):
		GUIComponent.__init__(self)
		self.list = []
		self.screenwidth = getDesktop(0).size().width()
		self.descr_state = descr_state or self.HIDE_DESCRIPTION
		self.sort_type = sort_type or self.SORT_GROUPWISE
		self.firstFileEntry = 0
		self.parentDirectory = 0
		self.fontName = "Regular"
		if self.screenwidth and self.screenwidth == 1920:
			self.fontSize = 28
		else:
			self.fontSize = 20
		self.listHeight = None
		self.listWidth = None
		self.reloadDelayTimer = None
		self.l = eListboxPythonMultiContent()
		self.tags = set()
		self.root = None
		self._playInBackground = None
		self._playInForeground = None
		self._char = ''

		if root is not None:
			self.reload(root)

		self.l.setBuildFunc(self.buildMovieListEntry)

		self.onSelectionChanged = [ ]
		self.iconPart = []
		for part in range(5):
			self.iconPart.append(LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/part_%d_4.png" % part)))
		self.iconMovieRec = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/part_new.png"))
		self.iconMoviePlay = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/movie_play.png"))
		self.iconMoviePlayRec = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/movie_play_rec.png"))
		self.iconUnwatched = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/part_unwatched.png"))
		self.iconFolder = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/folder.png"))
		self.iconTrash = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/trashcan.png"))
		self.runningTimers = {}
		self.updateRecordings()
		self.updatePlayPosCache()

	def applySkin(self, desktop, parent):
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "font":
					font = skin.parseFont(value, ((1,1),(1,1)))
					self.fontName = font.family
					self.fontSize = font.pointSize
				else:
					attribs.append((attrib,value))
			self.skinAttributes = attribs
			self.setFontsize()
		rc = GUIComponent.applySkin(self, desktop, parent)
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.setItemsPerPage()
		return rc

	def get_playInBackground(self):
		return self._playInBackground

	def set_playInBackground(self, value):
		if self._playInBackground is not value:
			index = self.findService(self._playInBackground)
			if index is not None:
				self.invalidateItem(index)
				self.l.invalidateEntry(index)
			index = self.findService(value)
			if index is not None:
				self.invalidateItem(index)
				self.l.invalidateEntry(index)
			self._playInBackground = value

	playInBackground = property(get_playInBackground, set_playInBackground)

	def get_playInForeground(self):
		return self._playInForeground

	def set_playInForeground(self, value):
		self._playInForeground = value

	playInForeground = property(get_playInForeground, set_playInForeground)

	def updatePlayPosCache(self):
		from Screens.InfoBarGenerics import updateresumePointCache
		updateresumePointCache()

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

	def setDescriptionState(self, val):
		self.descr_state = val

	def setSortType(self, type):
		self.sort_type = type

	def setItemsPerPage(self):
		if self.listHeight > 0:
			ext = config.movielist.useextlist.value
			if ext != '0':
				itemHeight = (self.listHeight / config.movielist.itemsperpage.value) *2
			else:
				itemHeight = self.listHeight / config.movielist.itemsperpage.value
		else:
			itemHeight = 30 # some default (270/5)
		self.itemHeight = itemHeight
		self.l.setItemHeight(itemHeight)
		self.instance.resize(eSize(self.listWidth, self.listHeight / itemHeight * itemHeight))

	def setFontsize(self):
		self.l.setFont(0, gFont(self.fontName, self.fontSize + config.movielist.fontsize.value))
		self.l.setFont(1, gFont(self.fontName, (self.fontSize - 3) + config.movielist.fontsize.value))

	def invalidateItem(self, index):
		x = self.list[index]
		self.list[index] = (x[0], x[1], x[2], None)

	def invalidateCurrentItem(self):
		self.invalidateItem(self.getCurrentIndex())

	def buildMovieListEntry(self, serviceref, info, begin, data):
		switch = config.usage.show_icons_in_movielist.value
		ext = config.movielist.useextlist.value
		width = self.l.getItemSize().width()
		pathName = serviceref.getPath()
		res = [ None ]

		if serviceref.flags & eServiceReference.mustDescent:
			if self.screenwidth and self.screenwidth == 1920:
				# Directory
				iconSize = 37
			else:
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
					if self.screenwidth and self.screenwidth == 1920:
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(3,5), size=(iconSize,37), png=self.iconTrash))
						res.append(MultiContentEntryText(pos=(40+20, 5), size=(width-166, self.itemHeight), font = 0, flags = RT_HALIGN_LEFT, text = _("Deleted items")))
						res.append(MultiContentEntryText(pos=(width-145, 0), size=(145, self.itemHeight), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=_("Trashcan")))
						return res
					else:
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(0,2), size=(iconSize,24), png=self.iconTrash))
						res.append(MultiContentEntryText(pos=(iconSize+10, 0), size=(width-166, self.itemHeight), font = 0, flags = RT_HALIGN_LEFT, text = _("Deleted items")))
						res.append(MultiContentEntryText(pos=(width-150, 0), size=(145, self.itemHeight), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=_("Trashcan")))
						return res
			if self.screenwidth and self.screenwidth == 1920:
				res.append(MultiContentEntryPixmapAlphaBlend(pos=(3,5), size=(iconSize,iconSize), png=self.iconFolder))
				res.append(MultiContentEntryText(pos=(40+20, 5), size=(width-166, self.itemHeight), font = 0, flags = RT_HALIGN_LEFT, text = txt))
				res.append(MultiContentEntryText(pos=(width-145, 0), size=(145, self.itemHeight), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=_("Directory")))
				return res
			else:
				res.append(MultiContentEntryPixmapAlphaBlend(pos=(0,2), size=(iconSize,iconSize), png=self.iconFolder))
				res.append(MultiContentEntryText(pos=(iconSize+10, 0), size=(width-166, self.itemHeight), font = 0, flags = RT_HALIGN_LEFT, text = txt))
				res.append(MultiContentEntryText(pos=(width-150, 0), size=(145, self.itemHeight), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=_("Directory")))
				return res
		if (data == -1) or (data is None):
			data = MovieListData()
			cur_idx = self.l.getCurrentSelectionIndex()
			x = self.list[cur_idx] # x = ref,info,begin,...
			data.len = 0 #dont recalc movielist to speedup loading the list
			self.list[cur_idx] = (x[0], x[1], x[2], data) #update entry in list... so next time we don't need to recalc
			data.txt = info.getName(serviceref)
			if config.movielist.hide_extensions.value:
				fileName, fileExtension = os.path.splitext(data.txt)
				if fileExtension in KNOWN_EXTENSIONS:
					data.txt = fileName
			data.icon = None
			data.part = None
			if os.path.split(pathName)[1] in self.runningTimers:
				if switch == 'i':
					if (self.playInBackground or self.playInForeground) and serviceref == (self.playInBackground or self.playInForeground):
						data.icon = self.iconMoviePlayRec
					else:
						data.icon = self.iconMovieRec
				elif switch == 'p' or switch == 's':
					data.part = 100
					if (self.playInBackground or self.playInForeground) and serviceref == (self.playInBackground or self.playInForeground):
						data.partcol = 0xffc71d
					else:
						data.partcol = 0xff001d
			elif (self.playInBackground or self.playInForeground) and serviceref == (self.playInBackground or self.playInForeground):
				data.icon = self.iconMoviePlay
			else:
				data.part = moviePlayState(pathName + '.cuts', serviceref, data.len)
				if switch == 'i':
					if data.part is not None and data.part > 0:
						data.icon = self.iconPart[data.part // 25]
					else:
						if config.usage.movielist_unseen.value:
							data.icon = self.iconUnwatched
				elif switch == 'p' or switch == 's':
					if data.part is not None and data.part > 0:
						data.partcol = 0xffc71d
					else:
						if config.usage.movielist_unseen.value:
							data.part = 100
							data.partcol = 0x206333
		len = data.len
		if len > 0:
			len = "%d:%02d" % (len / 60, len % 60)
		else:
			len = ""

		iconSize = 0
		if switch == 'i':
			if self.screenwidth and self.screenwidth == 1920:
				iconSize = 42
				res.append(MultiContentEntryPixmapAlphaBlend(pos=(2,3), size=(iconSize,iconSize), png=data.icon))
			else:
				iconSize = 22
				res.append(MultiContentEntryPixmapAlphaBlend(pos=(0,1), size=(iconSize,20), png=data.icon))
		elif switch == 'p':
			if self.screenwidth and self.screenwidth == 1920:
				iconSize = 42
			else:
				iconSize = 48
			if data.part is not None and data.part > 0:
				if self.screenwidth and self.screenwidth == 1920:
					res.append(MultiContentEntryProgress(pos=(0,10), size=(iconSize+5,16), percent=data.part, borderWidth=2, foreColor=data.partcol, foreColorSelected=None, backColor=None, backColorSelected=None))
				else:
					res.append(MultiContentEntryProgress(pos=(0,5), size=(iconSize-2,16), percent=data.part, borderWidth=2, foreColor=data.partcol, foreColorSelected=None, backColor=None, backColorSelected=None))
			else:
				if self.screenwidth and self.screenwidth == 1920:
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(0,1), size=(iconSize,iconSize), png=data.icon))
				else:
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(0,1), size=(iconSize,20), png=data.icon))
		elif switch == 's':
			if self.screenwidth and self.screenwidth == 1920:
				iconSize = 42
			else:
				iconSize = 22
			if data.part is not None and data.part > 0:
				if self.screenwidth and self.screenwidth == 1920:
					res.append(MultiContentEntryProgress(pos=(0,10), size=(iconSize+5,16), percent=data.part, borderWidth=2, foreColor=data.partcol, foreColorSelected=None, backColor=None, backColorSelected=None))
				else:
					res.append(MultiContentEntryProgress(pos=(0,5), size=(iconSize-2,16), percent=data.part, borderWidth=2, foreColor=data.partcol, foreColorSelected=None, backColor=None, backColorSelected=None))
			else:
				if self.screenwidth and self.screenwidth == 1920:
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(0,1), size=(iconSize,iconSize), png=data.icon))
				else:
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(0,1), size=(iconSize,20), png=data.icon))

		begin_string = ""
		if begin > 0:
			begin_string = ', '.join(FuzzyTime(begin, inPast = True))

		if ext != '0':
			ih = self.itemHeight / 2
		else:
			ih = self.itemHeight
		lenSize = ih * 3 # 25 -> 75
		dateSize = ih * 145 / 25   # 25 -> 145
		if ext != '0':
			getrec = info.getName(serviceref)
			fileName, fileExtension = os.path.splitext(getrec)
			desc = None
			picon = None
			service = None
			try:
				serviceHandler = eServiceCenter.getInstance()
				info = serviceHandler.info(serviceref)
				desc = info.getInfoString(serviceref, iServiceInformation.sDescription)		# get description
				ref = info.getInfoString(serviceref, iServiceInformation.sServiceref)		# get reference
				service = ServiceReference(ref).getServiceName()				# get service name
			except Exception, e:
				print('[MovieList] load extended infos get failed: ', e)
			if ext == '2':
				try:
					picon = getPiconName(ref)
					picon = loadPNG(picon)
				except Exception, e:
					print('[MovieList] load picon get failed: ', e)

			# TODO: make it shorter in future, this is the first way to get the extendedList
			if fileExtension in RECORD_EXTENSIONS:
				if self.screenwidth and self.screenwidth == 1920:
					if ext == '1':
						res.append(MultiContentEntryText(pos=(iconSize+20, 5), size=(width - iconSize - dateSize - dateSize / 2 - 15, ih), font=0, flags=RT_HALIGN_LEFT, text=data.txt))
						res.append(MultiContentEntryText(pos=(width - dateSize - dateSize / 2 - 5, 1), size=(dateSize + dateSize / 2, ih), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=service))
					if ext == '2':
						piconSize = ih * 2
						res.append(MultiContentEntryText(pos=(iconSize+20, 5), size=(width - iconSize - dateSize - 15, ih+2), font=0, flags=RT_HALIGN_LEFT, text=data.txt))
						res.append(MultiContentEntryPixmapAlphaTest(pos=(width - 48 - 5, 1), size=(piconSize, ih-2), png=picon, flags = BT_SCALE | BT_KEEP_ASPECT_RATIO))
					res.append(MultiContentEntryText(pos=(iconSize+20, ih), size=(width - iconSize - dateSize - 15, ih), font=1, flags=RT_HALIGN_LEFT, text=desc))
					res.append(MultiContentEntryText(pos=(width-dateSize, 0), size=(dateSize, ih), font=1, flags=RT_HALIGN_RIGHT, text=begin_string))
					return res
				else:
					if ext == '1':
						res.append(MultiContentEntryText(pos=(iconSize + 8, 0), size=(width - iconSize - dateSize - dateSize / 2 - 15, ih), font=0, flags=RT_HALIGN_LEFT, text=data.txt))
						res.append(MultiContentEntryText(pos=(width - dateSize - dateSize / 2 - 5, 1), size=(dateSize + dateSize / 2, ih), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=service))
					if ext == '2':
						piconSize = ih * 2
						res.append(MultiContentEntryText(pos=(iconSize + 8, 0), size=(width - iconSize - dateSize - 15, ih+2), font=0, flags=RT_HALIGN_LEFT, text=data.txt))
						res.append(MultiContentEntryPixmapAlphaTest(pos=(width - 48 - 5, 1), size=(piconSize, ih-2), png=picon, flags = BT_SCALE | BT_KEEP_ASPECT_RATIO))
					res.append(MultiContentEntryText(pos=(iconSize + 8, ih), size=(width - iconSize - dateSize - 15, ih), font=1, flags=RT_HALIGN_LEFT, text=desc))
					res.append(MultiContentEntryText(pos=(width - dateSize - 5, ih), size=(dateSize, ih), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=begin_string))
					return res
			else:
				if self.screenwidth and self.screenwidth == 1920:
					res.append(MultiContentEntryText(pos=(iconSize+20, 5), size=(width-iconSize-dateSize-15, ih), font = 0, flags = RT_HALIGN_LEFT, text = data.txt))
					res.append(MultiContentEntryText(pos=(width-dateSize, ih), size=(dateSize, ih), font=1, flags=RT_HALIGN_RIGHT, text=begin_string))
					return res
				else:
					res.append(MultiContentEntryText(pos=(iconSize+8, 0), size=(width-iconSize-dateSize-15, ih), font = 0, flags = RT_HALIGN_LEFT, text = data.txt))
					res.append(MultiContentEntryText(pos=(width-dateSize-5, ih), size=(dateSize, ih), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=begin_string))
					return res
		else:
			if self.screenwidth and self.screenwidth == 1920:
				res.append(MultiContentEntryText(pos=(iconSize+20, 5), size=(width-iconSize-dateSize-15, ih), font = 0, flags = RT_HALIGN_LEFT, text = data.txt))
				res.append(MultiContentEntryText(pos=(width-dateSize, 0), size=(dateSize, ih), font=1, flags=RT_HALIGN_RIGHT, text=begin_string))
				return res
			else:
				res.append(MultiContentEntryText(pos=(iconSize+8, 0), size=(width-iconSize-dateSize-15, ih), font = 0, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = data.txt))
				res.append(MultiContentEntryText(pos=(width-dateSize-5, 0), size=(dateSize, ih), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=begin_string))
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
		self.setFontsize()

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
		index = self.findService(service)
		if index is not None:
			del self.list[index]
			self.l.setList(self.list)

	def findService(self, service):
		if service is None:
			return None
		for index, l in enumerate(self.list):
			if l[0] == service:
				return index
		return None

	def __len__(self):
		return len(self.list)

	def __getitem__(self, index):
		return self.list[index]

	def __iter__(self):
		return self.list.__iter__()

	def load(self, root, filter_tags):
		# this lists our root service, then building a
		# nice list
		del self.list[:]
		serviceHandler = eServiceCenter.getInstance()
		numberOfDirs = 0

		reflist = root and serviceHandler.list(root)
		if reflist is None:
			print "listing of movies failed"
			return
		realtags = set()
		tags = {}
		rootPath = os.path.normpath(root.getPath())
		parent = None
		# Don't navigate above the "root"
		if len(rootPath) > 1 and (os.path.realpath(rootPath) != config.movielist.root.value):
			parent = os.path.split(os.path.normpath(rootPath))[0]
			currentfolder = os.path.normpath(rootPath) + '/'
			if parent and (parent not in defaultInhibitDirs) and not currentfolder.endswith(config.usage.default_path.value):
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
				dirname = info.getName(serviceref)
				if not dirname.endswith('.AppleDouble/') and not dirname.endswith('.AppleDesktop/') and not dirname.endswith('.AppleDB/') and not dirname.endswith('Network Trash Folder/') and not dirname.endswith('Temporary Items/'):
					self.list.append((serviceref, info, begin, -1))
					numberOfDirs += 1
				continue
			# convert space-seperated list of tags into a set
			this_tags = info.getInfoString(serviceref, iServiceInformation.sTags).split(' ')
			name = info.getName(serviceref)

			# OSX put a lot of stupid files ._* everywhere... we need to skip them
			if name[:2] == "._":
				continue

			if this_tags == ['']:
				# No tags? Auto tag!
				this_tags = name.replace(',',' ').replace('.',' ').replace('_',' ').replace(':',' ').split()
			else:
				realtags.update(this_tags)
			for tag in this_tags:
				if len(tag) >= 4:
					if tags.has_key(tag):
						tags[tag].append(name)
					else:
						tags[tag] = [name]
			# filter_tags is either None (which means no filter at all), or
			# a set. In this case, all elements of filter_tags must be present,
			# otherwise the entry will be dropped.
			if filter_tags is not None:
				this_tags_fullname = [" ".join(this_tags)]
				this_tags_fullname = set(this_tags_fullname)
				this_tags = set(this_tags)
				if not this_tags.issuperset(filter_tags) and not this_tags_fullname.issuperset(filter_tags):
# 					print "Skipping", name, "tags=", this_tags, " filter=", filter_tags
					continue

			self.list.append((serviceref, info, begin, -1))

		self.firstFileEntry = numberOfDirs
		self.parentDirectory = 0

		self.list.sort(key=self.buildGroupwiseSortkey)
		if self.sort_type == MovieList.SORT_ALPHANUMERIC:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildAlphaNumericSortKey) + sorted(self.list[numberOfDirs:], key=self.buildAlphaNumericSortKey)
		elif self.sort_type == MovieList.SORT_ALPHANUMERIC_REVERSE:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildAlphaNumericSortKey, reverse = True) + sorted(self.list[numberOfDirs:], key=self.buildAlphaNumericSortKey, reverse = True)
		elif self.sort_type == MovieList.SORT_ALPHANUMERIC_FLAT:
			self.list.sort(key=self.buildAlphaNumericFlatSortKey)
		elif self.sort_type == MovieList.SORT_ALPHANUMERIC_FLAT_REVERSE:
			self.list.sort(key=self.buildAlphaNumericFlatSortKey, reverse = True)
		elif self.sort_type == MovieList.SORT_RECORDED:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildBeginTimeSortKey) + sorted(self.list[numberOfDirs:], key=self.buildBeginTimeSortKey)
		elif self.sort_type == MovieList.SORT_RECORDED_REVERSE:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildBeginTimeSortKey, reverse = True) + sorted(self.list[numberOfDirs:], key=self.buildBeginTimeSortKey, reverse = True)
		elif self.sort_type == MovieList.SHUFFLE:
			dirlist = self.list[:numberOfDirs]
			shufflelist = self.list[numberOfDirs:]
			random.shuffle(shufflelist)
			self.list = dirlist + shufflelist
		elif self.sort_type == MovieList.SORT_ALPHA_DATE_OLDEST_FIRST:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildAlphaDateSortKey) + sorted(self.list[numberOfDirs:], key=self.buildAlphaDateSortKey)
		elif self.sort_type == MovieList.SORT_ALPHAREV_DATE_NEWEST_FIRST:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildAlphaDateSortKey, reverse = True) + sorted(self.list[numberOfDirs:], key=self.buildAlphaDateSortKey, reverse = True)
		
		for x in self.list:
			if x[1]:
				tmppath = x[1].getName(x[0])[:-1] if x[1].getName(x[0]).endswith('/') else x[1].getName(x[0])
				if tmppath.endswith('.Trash'):
					self.list.insert(0, self.list.pop(self.list.index(x)))
					break

		if self.root and numberOfDirs > 0:
			rootPath = os.path.normpath(self.root.getPath())
			if not rootPath.endswith('/'):
				rootPath += '/'
			if rootPath != parent:
				# with new sort types directories may be in between files, so scan whole
				# list for parentDirectory index. Usually it is the first one anyway
				for index, item in enumerate(self.list):
					if item[0].flags & eServiceReference.mustDescent:
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
		self.tags = {}
		for movies, tags in rtags.items():
			movie = movies[0]
			# format the tag lists so that they are in 'original' order
			tags.sort(key = movie.find)
			first = movie.find(tags[0])
			last = movie.find(tags[-1]) + len(tags[-1])
			match = movie
			start = 0
			end = len(movie)
			# Check if the set has a complete sentence in common, and how far
			for m in movies[1:]:
				if m[start:end] != match:
					if not m.startswith(movie[:last]):
						start = first
					if not m.endswith(movie[first:]):
						end = last
					match = movie[start:end]
					if m[start:end] != match:
						match = ''
						break
			if match:
				self.tags[match] = set(tags)
				continue
			else:
				match = ' '.join(tags)
				if len(match) > 2: #Omit small words
					self.tags[match] = set(tags)

	def buildAlphaNumericSortKey(self, x):
		# x = ref,info,begin,...
		ref = x[0]
		name = x[1] and x[1].getName(ref)
		if ref.flags & eServiceReference.mustDescent:
			return 0, name and name.lower() or "", -x[2]
		return 1, name and name.lower() or "", -x[2]

# as for buildAlphaNumericSortKey, but without negating dates
	def buildAlphaDateSortKey(self, x):
		# x = ref,info,begin,...
		ref = x[0]
		name = x[1] and x[1].getName(ref)
		if ref.flags & eServiceReference.mustDescent:
			return 0, name and name.lower() or "", x[2]
		return 1, name and name.lower() or "", x[2]

	def buildAlphaNumericFlatSortKey(self, x):
		# x = ref,info,begin,...
		ref = x[0]
		name = x[1] and x[1].getName(ref)
		if name and ref.flags & eServiceReference.mustDescent:
			# only use directory basename for sorting
			p = os.path.split(name)
			if not p[1]:
				# if path ends in '/', p is blank.
				p = os.path.split(p[0])
			name = p[1]
		# print "Sorting for -%s-" % name

		return 1, name and name.lower() or "", -x[2]

	def buildBeginTimeSortKey(self, x):
		ref = x[0]
		if ref.flags & eServiceReference.mustDescent:
			return 0, x[1] and -os.stat(ref.getPath()).st_mtime
		return 1, -x[2]

	def buildGroupwiseSortkey(self, x):
		# Sort recordings by date, sort MP3 and stuff by name
		ref = x[0]
		if ref.type >= eServiceReference.idUser:
			return self.buildAlphaNumericSortKey(x)
		else:
			return self.buildBeginTimeSortKey(x)

	def moveTo(self, serviceref):
		index = self.findService(serviceref)
		if index is not None:
			self.instance.moveSelectionTo(index)
			return True
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
