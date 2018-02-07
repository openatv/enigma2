import os
import struct
import random
from time import localtime, strftime

from enigma import eListboxPythonMultiContent, eListbox, gFont, iServiceInformation, eSize, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER, eServiceReference, eServiceReferenceFS, eServiceCenter, eTimer, getDesktop
from GUIComponent import GUIComponent
from Tools.FuzzyDate import FuzzyTime
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest, MultiContentEntryPixmapAlphaBlend, MultiContentEntryProgress
from Components.config import config
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import SCOPE_ACTIVE_SKIN, resolveFilename
from Tools.UnitConversions import UnitScaler
from Screens.LocationBox import defaultInhibitDirs
# GML:1
from Tools.Trashcan import getTrashFolder
import NavigationInstance
import skin


AUDIO_EXTENSIONS = frozenset((".dts", ".mp3", ".wav", ".wave", ".oga", ".ogg", ".flac", ".m4a", ".mp2", ".m2a", ".wma", ".ac3", ".mka", ".aac", ".ape", ".alac"))
DVD_EXTENSIONS = frozenset((".iso", ".img", ".nrg"))
IMAGE_EXTENSIONS = frozenset((".jpg", ".png", ".gif", ".bmp", ".jpeg"))
MOVIE_EXTENSIONS = frozenset((".mpg", ".vob", ".m4v", ".mkv", ".avi", ".divx", ".dat", ".flv", ".mp4", ".mov", ".wmv", ".asf", ".3gp", ".3g2", ".mpeg", ".mpe", ".rm", ".rmvb", ".ogm", ".ogv", ".m2ts", ".mts", ".webm"))
KNOWN_EXTENSIONS = MOVIE_EXTENSIONS.union(IMAGE_EXTENSIONS, DVD_EXTENSIONS, AUDIO_EXTENSIONS)

cutsParser = struct.Struct('>QI')  # big-endian, 64-bit PTS and 32-bit type

class MovieListData:
	def __init__(self):
		pass

# iStaticServiceInformation
class StubInfo:
	def __init__(self):
		pass

	def getName(self, serviceref):
		if serviceref.getPath().endswith('/'):
			return serviceref.getPath()
		else:
			return os.path.basename(serviceref.getPath())

	def getLength(self, serviceref):
		return -1

	def getFileSize(self, serviceref):
		try:
			return os.stat(serviceref.getPath()).st_size
		except:
			return -1

	def getEvent(self, serviceref, *args):
		return None

	def isPlayable(self):
		return True

	def getInfo(self, serviceref, w):
		try:
			if w == iServiceInformation.sTimeCreate:
				return os.stat(serviceref.getPath()).st_ctime
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
	# .cuts file - bookmarks, edit points and resume, kept with a recording
	resume = _getCutsResumeInfo(cutsFileName)

	# There was enough info in the .cuts file
	if resume and length and length > 0:
		if resume >= length:
			return 100
		return int(100.0 * resume / length + 0.5)

	# Need to gather more info
	# Resume position and end pts, stored in non-volatile memory, cached in RAM
	cache = lastPlayPosFromCache(ref)
	if cache:
		_, cache_resume, cache_end = cache

		if length is None or (length <= 0):
			length = cache_end

		if resume is None or (resume <= 0):
			resume = cache_resume

		if length and resume:
			if resume >= length:
				return 100
			return int(100.0 * resume / length + 0.5)

		return 0
	return None

def _getCutsResumeInfo(filename):
	resume_pts = None
	try:
		with open(filename, 'rb') as f:
			while True:
				data = f.read(cutsParser.size)
				if len(data) < cutsParser.size:
					break
				cut, cutType = cutsParser.unpack(data)
				if cutType == 3:  # Resume point
					resume_pts = cut
	except:
		pass
	return resume_pts

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
		# import sys
		# print "[MovieList] Exception in resetMoviePlayState: %s: %s" % sys.exc_info()[:2]

class MovieList(GUIComponent):
	SORT_ALPHANUMERIC = SORT_ALPHA_DATE_NEWEST_FIRST = 1
	SORT_RECORDED = SORT_DATE_NEWEST_FIRST_ALPHA = 2
	SHUFFLE = 3
	SORT_ALPHANUMERIC_REVERSE = SORT_ALPHAREV_DATE_OLDEST_FIRST = 4
	SORT_RECORDED_REVERSE = SORT_DATE_OLDEST_FIRST_ALPHAREV = 5
	SORT_ALPHANUMERIC_FLAT = SORT_ALPHA_DATE_NEWEST_FIRST_FLAT = 6
	SORT_ALPHANUMERIC_FLAT_REVERSE = SORT_ALPHAREV_DATE_OLDEST_FIRST_FLAT = 7
	SORT_GROUPWISE = 8
	SORT_ALPHA_DATE_OLDEST_FIRST = 9
	SORT_ALPHAREV_DATE_NEWEST_FIRST = 10
	SORT_DURATION_ALPHA = 11
	SORT_DURATIONREV_ALPHA = 12
	SORT_SIZE_ALPHA = 13
	SORT_SIZEREV_ALPHA = 14

	HIDE_DESCRIPTION = 1
	SHOW_DESCRIPTION = 2

	COL_NAME = 1
	COL_BEGIN = 2
	COL_LENGTH = 3
	COL_SIZE = 4

	staticCols = frozenset([COL_NAME, COL_BEGIN])
	sortCols = {
		SORT_DURATION_ALPHA: staticCols | frozenset([COL_LENGTH]),
		SORT_DURATIONREV_ALPHA: staticCols | frozenset([COL_LENGTH]),
		SORT_SIZE_ALPHA: staticCols | frozenset([COL_SIZE]),
		SORT_SIZEREV_ALPHA: staticCols | frozenset([COL_SIZE]),
	}

	dirNameExclusions = [
		'.AppleDouble', '.AppleDesktop', '.AppleDB',
		'Network Trash Folder', 'Temporary Items',
		'.TemporaryItems'
	]

# GML:1
# So MovieSelection.selectSortby() can find out whether we are
# in a Trash folder and, if so, what the last sort was
# The numbering starts after SORT_* values above.
# in MovieSelection.py (that has no SORT_GROUPWISE)
#
	TRASHSORT_SHOWRECORD = 15
	TRASHSORT_SHOWDELETE = 16
	UsingTrashSort = False
	InTrashFolder = False

	def __init__(self, root, sort_type=None, descr_state=None):
		GUIComponent.__init__(self)
		self.list = []
		self.descr_state = descr_state or self.HIDE_DESCRIPTION
		self.sort_type = sort_type or self.SORT_GROUPWISE
		self.firstFileEntry = 0
		self.parentDirectory = 0
		self.numUserDirs = 0  # does not include parent or Trashcan
		self.numUserFiles = 0
		self.fontName, self.fontSize, height, width = skin.fonts.get("MovieSelectionFont", ("Regular", 20, 25, 18))
		self.listHeight = None
		self.listWidth = None
		# pbarShift, trashShift, dirShift, dateWidth, lenWidth
		# and sizeWidth are properties that return their
		# calculated size if set to None
		self.pbarShift = None  # Defaults to being calculated from bar height
		self.pbarHeight = 16
		self.pbarLargeWidth = 48
		self.pbarColour = 0x206333
		self.pbarColourSeen = 0xffc71d
		self.pbarColourRec = 0xff001d
		self.pbarColourSel = 0x20a333
		self.pbarColourSeenSel = 0xffc71d
		self.pbarColourRecSel = 0xff001d
		# Unlike pbarShift and trashShift, etc below,
		# partIconeShift is an ordinary attribute, because
		# its "None" value is calculated per row in the list
		self.partIconeShift = None  # Defaults to being calculated from icon height
		self.spaceRight = 2
		self.spaceIconeText = 2
		self.iconsWidth = 22

		self.trashShift = None  # Defaults to being calculated from trash icon height
		self.dirShift = None  # Defaults to being calculated from directory icon height
		self.dateWidth = None  # Defaults to being calculated from font size
		self.dateWidthScale = 9.0  # Over-ridden by self.dateWidth if set
		self.lenWidth = None  # Defaults to being calculated from font size
		self.lenWidthScale = 4.0  # Over-ridden by self.lenWidth if set
		self.sizeWidth = None  # Defaults to being calculated from font size
		self.sizeWidthScale = 5.0  # Over-ridden by self.sizeWidth if set
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

		self.onSelectionChanged = []
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

	@property
	def dateWidth(self):
		if self._dateWidth is None:
			return int(((self.fontSize - 3) + config.movielist.fontsize.value) * self.dateWidthScale)
		else:
			return self._dateWidth

	@dateWidth.setter
	def dateWidth(self, val):
		self._dateWidth = val

	@property
	def lenWidth(self):
		if self._lenWidth is None:
			return int(((self.fontSize - 3) + config.movielist.fontsize.value) * self.lenWidthScale)
		else:
			return self._lenWidth

	@lenWidth.setter
	def lenWidth(self, val):
		self._lenWidth = val

	@property
	def sizeWidth(self):
		if self._sizeWidth is None:
			return int(((self.fontSize - 3) + config.movielist.fontsize.value) * self.sizeWidthScale)
		else:
			return self._sizeWidth

	@sizeWidth.setter
	def sizeWidth(self, val):
		self._sizeWidth = val

	@property
	def trashShift(self):
		if self._trashShift is None:
			return max(0, int((self.itemHeight - self.iconTrash.size().height() + 1.0) / 2))
		else:
			return self._trashShift

	@trashShift.setter
	def trashShift(self, val):
		self._trashShift = val

	@property
	def dirShift(self):
		if self._dirShift is None:
			return max(0, int((self.itemHeight - self.iconFolder.size().height() + 1.0) / 2))
		else:
			return self._dirShift

	@dirShift.setter
	def dirShift(self, val):
		self._dirShift = val

	@property
	def pbarShift(self):
		if self._pbarShift is None:
			return max(0, int((self.itemHeight - self.pbarHeight) / 2))
		else:
			return self._pbarShift

	@pbarShift.setter
	def pbarShift(self, val):
		self._pbarShift = val

	def get_playInBackground(self):
		return self._playInBackground

	def set_playInBackground(self, value):
		if self._playInBackground is not value:
			index = self.findService(self._playInBackground)
			if index is not None:
				self.invalidateItem(index)
			index = self.findService(value)
			if index is not None:
				self.invalidateItem(index)
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
			if timer.isRunning() and not timer.justplay and not timer.failed:
				result[os.path.basename(timer.Filename) + '.ts'] = timer
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
		if fnc not in self.onSelectionChanged:
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

	def applySkin(self, desktop, parent):
		def warningWrongSkinParameter(string):
			print "[MovieList] wrong '%s' skin parameters" % string

		def font(value):
			font = skin.parseFont(value, ((1, 1), (1, 1)))
			self.fontName = font.family
			self.fontSize = font.pointSize

		def pbarShift(value):
			self.pbarShift = int(value)

		def pbarHeight(value):
			self.pbarHeight = int(value)

		def pbarLargeWidth(value):
			self.pbarLargeWidth = int(value)

		def pbarColour(value):
			self.pbarColour = skin.parseColor(value).argb()

		def pbarColourSeen(value):
			self.pbarColourSeen = skin.parseColor(value).argb()

		def pbarColourRec(value):
			self.pbarColourRec = skin.parseColor(value).argb()

		def pbarColourSel(value):
			self.pbarColourSel = skin.parseColor(value).argb()

		def pbarColourSeenSel(value):
			self.pbarColourSeenSel = skin.parseColor(value).argb()

		def pbarColourRecSel(value):
			self.pbarColourRecSel = skin.parseColor(value).argb()

		def partIconeShift(value):
			self.partIconeShift = int(value)

		def spaceIconeText(value):
			self.spaceIconeText = int(value)

		def iconsWidth(value):
			self.iconsWidth = int(value)

		def trashShift(value):
			self.trashShift = int(value)

		def dirShift(value):
			self.dirShift = int(value)

		def spaceRight(value):
			self.spaceRight = int(value)

		def dateWidth(value):
			self.dateWidth = int(value)

		def dateWidthScale(value):
			self.dateWidthScale = float(value)

		def lenWidth(value):
			self.lenWidth = int(value)

		def lenWidthScale(value):
			self.lenWidthScale = float(value)

		def sizeWidth(value):
			self.sizeWidth = int(value)

		def sizeWidthScale(value):
			self.sizeWidthScale = float(value)

		for (attrib, value) in self.skinAttributes[:]:
			try:
				locals().get(attrib)(value)
				self.skinAttributes.remove((attrib, value))
			except:
				pass
		rc = GUIComponent.applySkin(self, desktop, parent)
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.setFontsize()
		self.setItemsPerPage()
		return rc

	def setItemsPerPage(self):
		if self.listHeight > 0:
			itemHeight = self.listHeight / config.movielist.itemsperpage.value
		else:
			itemHeight = 25  # some default (270/5)
		self.itemHeight = itemHeight
		self.l.setItemHeight(itemHeight)
		self.instance.resize(eSize(self.listWidth, self.listHeight / itemHeight * itemHeight))

	def setFontsize(self):
		self.l.setFont(0, gFont(self.fontName, self.fontSize + config.movielist.fontsize.value))
		self.l.setFont(1, gFont(self.fontName, (self.fontSize - 3) + config.movielist.fontsize.value))

	def invalidateItem(self, index):
		x = self.list[index]
		self.list[index] = (x[0], x[1], x[2], None)
		self.l.invalidateEntry(index)

	def invalidateCurrentItem(self):
		self.invalidateItem(self.getCurrentIndex())

	def userItemCount(self):
		return (self.numUserDirs, self.numUserFiles)

	def showCol(self, conf, col):
		return conf.value == "yes" or conf.value == "auto" and col in self.sortCols.get(self.sort_type, self.staticCols)

	def buildMovieListEntry(self, serviceref, info, begin, data):
		switch = config.usage.show_icons_in_movielist.value
		width = self.l.getItemSize().width()
		dateWidth = self.dateWidth
		if config.usage.time.wide.value:
			dateWidth = int(dateWidth * 1.15)
		if not config.movielist.use_fuzzy_dates.value:
			dateWidth += 35
		showLen = self.showCol(config.movielist.showlengths, self.COL_LENGTH)
		lenWidth = self.lenWidth if showLen else 0
		showSize = self.showCol(config.movielist.showsizes, self.COL_SIZE)
		sizeWidth = self.sizeWidth if showSize else 0
		iconSize = self.iconsWidth
		space = self.spaceIconeText
		r = self.spaceRight
		ih = self.itemHeight
		pathName = serviceref.getPath()
		res = [None]

		if serviceref.flags & eServiceReference.mustDescent:
			# Directory
			# Name is full path name
			if info is None:
				# Special case: "parent"
				txt = ".."
			else:
				txt = os.path.basename(os.path.normpath(pathName))
			if txt == ".Trash":
				res.append(MultiContentEntryPixmapAlphaBlend(pos=(0, self.trashShift), size=(iconSize, self.iconTrash.size().height()), png=self.iconTrash))
				res.append(MultiContentEntryText(pos=(iconSize + space, 0), size=(width - iconSize - space - dateWidth - r, ih), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text = _("Trash")))
				res.append(MultiContentEntryText(pos=(width - dateWidth - r, 0), size=(dateWidth, ih), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=_("Trash")))
				return res
			res.append(MultiContentEntryPixmapAlphaBlend(pos=(0, self.dirShift), size=(iconSize, iconSize), png=self.iconFolder))
			res.append(MultiContentEntryText(pos=(iconSize + space, 0), size=(width - iconSize - space - dateWidth - r, ih), font=0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=txt))
			res.append(MultiContentEntryText(pos=(width - dateWidth - r, 0), size=(dateWidth, ih), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=_("Directory")))
			return res
		if data == -1 or data is None:
			data = MovieListData()
			cur_idx = self.l.getCurrentSelectionIndex()
			x = self.list[cur_idx]  # x = ref,info,begin,...
			data.len = info.getLength(serviceref)
			if showSize:
				data.size = info.getFileSize(serviceref)
			self.list[cur_idx] = (x[0], x[1], x[2], data)  # update entry in list... so next time we don't need to recalc
			data.txt = info.getName(serviceref)
			if config.movielist.hide_extensions.value:
				fileName, fileExtension = os.path.splitext(data.txt)
				if fileExtension in KNOWN_EXTENSIONS:
					data.txt = fileName
			data.icon = None
			data.part = None
			if os.path.basename(pathName) in self.runningTimers:
				if switch == 'i':
					if (self.playInBackground or self.playInForeground) and serviceref == (self.playInBackground or self.playInForeground):
						data.icon = self.iconMoviePlayRec
					else:
						data.icon = self.iconMovieRec
				elif switch in ('p', 's'):
					data.part = 100
					if (self.playInBackground or self.playInForeground) and serviceref == (self.playInBackground or self.playInForeground):
						data.partcol = self.pbarColourSeen
						data.partcolsel = self.pbarColourSeenSel
					else:
						data.partcol = self.pbarColourRec
						data.partcolsel = self.pbarColourRecSel
			elif (self.playInBackground or self.playInForeground) and serviceref == (self.playInBackground or self.playInForeground):
				data.icon = self.iconMoviePlay
			else:
				data.part = moviePlayState(pathName + '.cuts', serviceref, data.len * 90000)
				if switch == 'i':
					if data.part is not None and data.part >= 0:
						data.icon = self.iconPart[data.part // 25]
					else:
						if config.usage.movielist_unseen.value:
							data.icon = self.iconUnwatched
				elif switch in ('p', 's'):
					if data.part is not None and data.part > 0:
						data.partcol = self.pbarColourSeen
						data.partcolsel = self.pbarColourSeenSel
					else:
						if config.usage.movielist_unseen.value:
							data.part = 100
							data.partcol = self.pbarColour
							data.partcolsel = self.pbarColourSel
		if showLen:
			len = data.len
			len = "%d:%02d" % (len / 60, len % 60) if len > 0 else ""
		if showSize:
			size = _("%s %sB") % UnitScaler()(data.size) if data.size > 0 else ""

		if data:
			if switch == 'i' and hasattr(data, 'icon') and data.icon is not None:
				if self.partIconeShift is None:
					partIconeShift = max(0, int((ih - data.icon.size().height()) / 2))
				else:
					partIconeShift = self.partIconeShift
				pos = (0, partIconeShift)
				res.append(MultiContentEntryPixmapAlphaBlend(pos=pos, size=(iconSize, data.icon.size().height()), png=data.icon))
			elif switch in ('p', 's'):
				if switch == 'p':
					iconSize = self.pbarLargeWidth
				if hasattr(data, 'part') and data.part > 0:
					res.append(MultiContentEntryProgress(pos=(0, self.pbarShift), size=(iconSize, self.pbarHeight), percent=data.part, borderWidth=2, foreColor=data.partcol, foreColorSelected=data.partcolsel, backColor=None, backColorSelected=None))
				elif hasattr(data, 'icon') and data.icon is not None:
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(0, self.pbarShift), size=(iconSize, self.pbarHeight), png=data.icon))

		begin_string = ""
		if begin > 0:
			if config.movielist.use_fuzzy_dates.value:
				begin_string = ' '.join(FuzzyTime(begin, inPast = True))
			else:
				begin_string = strftime("%s %s" % (config.usage.date.daylong.value, config.usage.time.short.value), localtime(begin))

		textItems = []
		xPos = width

		if showSize:
			xPos -= sizeWidth + r
			textItems.insert(0, MultiContentEntryText(pos=(xPos, 0), size=(sizeWidth, ih), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=size))
		if showLen:
			xPos -= lenWidth + r
			textItems.insert(0, MultiContentEntryText(pos=(xPos, 0), size=(lenWidth, ih), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=len))
		xPos -= dateWidth + r
		textItems.insert(0, MultiContentEntryText(pos=(xPos, 0), size=(dateWidth, ih), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=begin_string))
		textItems.insert(0, MultiContentEntryText(pos=(iconSize + space, 0), size=(xPos - (iconSize + space), ih), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=data.txt))

		res += textItems
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

	def reload(self, root=None, filter_tags=None):
		if self.reloadDelayTimer is not None:
			self.reloadDelayTimer.stop()
			self.reloadDelayTimer = None
		if root is not None:
			self.load(root, filter_tags)
		else:
			self.load(self.root, filter_tags)
		self.refreshDisplay()

	def refreshDisplay(self):
		self.l.setList(self.list)

	def removeService(self, service):
		index = self.findService(service)
		if index is not None:
			(serviceref, info, _, _) = self.list[index]
			pathName = serviceref.getPath()
			if serviceref.flags & eServiceReference.mustDescent:
				name = os.path.basename(os.path.normpath(pathName))
				if info is not None and name != ".Trash" and self.numUserDirs > 0:
					self.numUserDirs -= 1
			elif self.numUserFiles > 0:
				self.numUserFiles -= 1
			del self.list[index]
			self.refreshDisplay()

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
		self.list = []
		serviceHandler = eServiceCenter.getInstance()
		numberOfDirs = 0
		self.numUserDirs = 0  # does not include parent or Trashcan
		self.numUserFiles = 0

		reflist = root and serviceHandler.list(root)
		if reflist is None:
			print "[MovieList] listing of movies failed"
			return
		realtags = set()
		autotags = {}
		rootPath = os.path.normpath(root.getPath())
		parent = None
		# Don't navigate above the "root"
		if len(rootPath) > 1 and (os.path.realpath(rootPath) != os.path.realpath(config.movielist.root.value)):
			parent = os.path.dirname(rootPath)
			# enigma wants an extra '/' appended
			if not parent.endswith('/'):
				parent += '/'
			ref = eServiceReference(eServiceReference.idFile, eServiceReference.flagDirectory, eServiceReferenceFS.directory)
			ref.setPath(parent)
			self.list.append((ref, None, 0, -1))
			numberOfDirs += 1

# GML:1
		if config.usage.movielist_trashcan.value:
			here = os.path.realpath(rootPath)
			MovieList.InTrashFolder = here.startswith(getTrashFolder(here))
		else:
			MovieList.InTrashFolder = False
		MovieList.UsingTrashSort = False
		if MovieList.InTrashFolder:
			if (config.usage.trashsort_deltime.value == "show record time"):
				MovieList.UsingTrashSort = MovieList.TRASHSORT_SHOWRECORD
			elif (config.usage.trashsort_deltime.value == "show delete time"):
				MovieList.UsingTrashSort = MovieList.TRASHSORT_SHOWDELETE

		while 1:
			serviceref = reflist.getNext()
			if not serviceref.valid():
				break
			if config.ParentalControl.servicepinactive.value and config.ParentalControl.storeservicepin.value != "never":
				from Components.ParentalControl import parentalControl
				if not parentalControl.sessionPinCached and parentalControl.isProtected(serviceref):
					continue
			info = serviceHandler.info(serviceref)
			if info is None:
				info = justStubInfo
			begin = info.getInfo(serviceref, iServiceInformation.sTimeCreate)

# GML:1
			begin2 = 0
			if MovieList.UsingTrashSort:
				f_path = serviceref.getPath()
				if os.path.exists(f_path):  # Override with deltime for sorting
					if MovieList.UsingTrashSort == MovieList.TRASHSORT_SHOWRECORD:
						begin2 = begin      # Save for later re-instatement
					begin = os.stat(f_path).st_ctime

			if serviceref.flags & eServiceReference.mustDescent:
				dirname = info.getName(serviceref)
				normdirname = os.path.normpath(dirname)
				normname = os.path.basename(normdirname)
				if normname not in MovieList.dirNameExclusions and normdirname not in defaultInhibitDirs:
					self.list.insert(0, (serviceref, info, begin, -1))
					numberOfDirs += 1
					if normname != ".Trash":
						self.numUserDirs += 1
				continue
			# convert space-separated list of tags into a set
			this_tags = info.getInfoString(serviceref, iServiceInformation.sTags).split(' ')
			name = info.getName(serviceref)

			# OSX put a lot of stupid files ._* everywhere... we need to skip them
			if name[:2] == "._":
				continue

			if this_tags == ['']:
				# No tags? Auto tag!
				this_tags = name.replace(',', ' ').replace('.', ' ').replace('_', ' ').replace(':', ' ').split()
				# For auto tags, we are keeping a (tag, movies) dictionary.
				# It will be used later to check if movies have a complete sentence in common.
				for tag in this_tags:
					if tag in autotags:
						autotags[tag].append(name)
					else:
						autotags[tag] = [name]
			else:
				realtags.update(this_tags)
			# filter_tags is either None (which means no filter at all), or
			# a set. In this case, all elements of filter_tags must be present,
			# otherwise the entry will be dropped.
			if filter_tags is not None:
				this_tags_fullname = [" ".join(this_tags)]
				this_tags_fullname = set(this_tags_fullname)
				this_tags = set(this_tags)
				if not this_tags.issuperset(filter_tags) and not this_tags_fullname.issuperset(filter_tags):
					# print "[MovieList] Skipping", name, "tags=", this_tags, " filter=", filter_tags
					continue

# GML:1
			if begin2 != 0:
				self.list.append((serviceref, info, begin, -1, begin2))
			else:
				self.list.append((serviceref, info, begin, -1))
			self.numUserFiles += 1

		self.parentDirectory = 0

# GML:1
		if MovieList.UsingTrashSort:      # Same as SORT_RECORDED (SORT_DATE_NEWEST_FIRST_ALPHA), but must come first...
			self.list = sorted(self.list[:numberOfDirs], key=self.buildBeginTimeSortKey) + sorted(self.list[numberOfDirs:], key=self.buildBeginTimeSortKey)
# Having sorted on deletion times, re-instate any record times for display.
# self.list is a list of tuples, so we can't just assign to elements...
#
			if config.usage.trashsort_deltime.value == "show record time":
				for i in range(len(self.list)):
					if len(self.list[i]) == 5:
						x = self.list[i]
						self.list[i] = (x[0], x[1], x[4], x[3])
		elif self.sort_type == MovieList.SORT_ALPHA_DATE_NEWEST_FIRST:
			self.list.sort(key=self.buildAlphaNumericSortKey)
		elif self.sort_type == MovieList.SORT_ALPHAREV_DATE_OLDEST_FIRST:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildAlphaNumericSortKey, reverse=True) \
				+ sorted(self.list[numberOfDirs:], key=self.buildAlphaNumericSortKey, reverse=True)
		elif self.sort_type == MovieList.SORT_ALPHA_DATE_NEWEST_FIRST_FLAT:
			self.list.sort(key=self.buildAlphaNumericFlatSortKey)
		elif self.sort_type == MovieList.SORT_ALPHAREV_DATE_OLDEST_FIRST_FLAT:
			self.list.sort(key=self.buildAlphaNumericFlatSortKey, reverse=True)
		elif self.sort_type == MovieList.SORT_DATE_NEWEST_FIRST_ALPHA:
			self.list.sort(key=self.buildBeginTimeSortKey)
		elif self.sort_type == MovieList.SORT_DATE_OLDEST_FIRST_ALPHAREV:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildBeginTimeSortKey, reverse=True) \
				+ sorted(self.list[numberOfDirs:], key=self.buildBeginTimeSortKey, reverse=True)
		elif self.sort_type == MovieList.SHUFFLE:
			shufflelist = self.list[numberOfDirs:]
			random.shuffle(shufflelist)
			self.list = self.list[:numberOfDirs] + shufflelist
		elif self.sort_type == MovieList.SORT_ALPHA_DATE_OLDEST_FIRST:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildAlphaDateSortKey) \
				+ sorted(self.list[numberOfDirs:], key=self.buildAlphaDateSortKey)
		elif self.sort_type == MovieList.SORT_ALPHAREV_DATE_NEWEST_FIRST:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildAlphaDateSortKey, reverse=True) \
				+ sorted(self.list[numberOfDirs:], key=self.buildAlphaDateSortKey, reverse=True)
		elif self.sort_type == MovieList.SORT_SIZE_ALPHA:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildAlphaDateSortKey) \
				+ sorted(self.list[numberOfDirs:], key=self.buildSizeAlphaSortKey)
		elif self.sort_type == MovieList.SORT_SIZEREV_ALPHA:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildAlphaDateSortKey) \
				+ sorted(self.list[numberOfDirs:], key=self.buildSizeRevAlphaSortKey)
		elif self.sort_type == MovieList.SORT_DURATION_ALPHA:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildAlphaDateSortKey) \
				+ sorted(self.list[numberOfDirs:], key=self.buildLengthAlphaSortKey)
		elif self.sort_type == MovieList.SORT_DURATIONREV_ALPHA:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildAlphaDateSortKey) \
				+ sorted(self.list[numberOfDirs:], key=self.buildLengthRevAlphaSortKey)
		else:
			self.list.sort(key=self.buildGroupwiseSortkey)

		for x in self.list[:]:
			if x[1]:
				tmppath = x[1].getName(x[0])[:-1] if x[1].getName(x[0]).endswith('/') else x[1].getName(x[0])
				if tmppath.endswith('.Trash'):
					self.list.append(self.list.pop(self.list.index(x)))
			else:
					self.list.insert(0, self.list.pop(self.list.index(x)))

		# Find first recording/file. Must be done after self.list has stopped changing
		self.firstFileEntry = 0
		for index, item in enumerate(self.list):
			if not item[0].flags & eServiceReference.mustDescent:
				self.firstFileEntry = index
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
		rautotags = {}
		for tag, movies in autotags.items():
			if (len(movies) > 1):
				movies = tuple(movies)  # a tuple can be hashed, but a list not
				item = rautotags.get(movies, [])
				if not item:
					rautotags[movies] = item
				item.append(tag)
		self.tags = {}
		for movies, tags in rautotags.items():
			movie = movies[0]
			# format the tag lists so that they are in 'original' order
			tags.sort(key=movie.find)
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
			# Adding the longest common sentence to the tag list
			if match:
				self.tags[match] = set(tags)
			else:
				match = ' '.join(tags)
				if (len(match) > 2) or (match in realtags):  # Omit small words, only for auto tags
					self.tags[match] = set(tags)
		# Adding the realtags to the tag list
		for tag in realtags:
			self.tags[tag] = set([tag])

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
		name = x[1] and x[1].getName(ref) or ".."
		if name and ref.flags & eServiceReference.mustDescent:
			# only use directory basename for sorting
			try:
				name = os.path.basename(os.path.normpath(name))
			except:
				pass
		if name.endswith(".Trash"):
			name = "Trash"
		# print "[MovieList] Sorting for -%s-" % name

		return 1, name and name.lower() or "", -x[2]

	def buildBeginTimeSortKey(self, x):
		ref = x[0]
		name = x[1] and x[1].getName(ref)
		if ref.flags & eServiceReference.mustDescent and os.path.exists(ref.getPath()):
			try:
				mtime = -os.stat(ref.getPath()).st_mtime
			except:
				mtime = 0
			return 0, x[1] and mtime, name and name.lower() or ""
		return 1, -x[2], name and name.lower() or ""

	def buildGroupwiseSortkey(self, x):
		# Sort recordings by date, sort MP3 and stuff by name
		ref = x[0]
		if ref.type >= eServiceReference.idUser:
			return self.buildAlphaNumericSortKey(x)
		else:
			return self.buildBeginTimeSortKey(x)

	def buildSizeAlphaSortKey(self, x):
		ref = x[0]
		info = x[1]
		name = info and info.getName(ref)
		size = info and info.getFileSize(ref)
		return 1, size, name and name.lower() or "", -x[2]

	def buildSizeRevAlphaSortKey(self, x):
		x = self.buildSizeAlphaSortKey(x)
		return (x[0], -x[1], x[2], x[3])

	def buildLengthAlphaSortKey(self, x):
		ref = x[0]
		info = x[1]
		name = info and info.getName(ref)
		len = info and info.getLength(ref)
		return 1, len, name and name.lower() or "", -x[2]

	def buildLengthRevAlphaSortKey(self, x):
		x = self.buildLengthAlphaSortKey(x)
		return (x[0], -x[1], x[2], x[3])

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
		self.moveToCharTimer.start(1000, True)  # time to wait for next key press to decide which letter to use...

	def moveToString(self, char, lbl=None):
		self._char = self._char + char.upper()
		self._lbl = lbl
		if lbl:
			lbl.setText(self._char)
			lbl.visible = True
		self.moveToCharTimer = eTimer()
		self.moveToCharTimer.callback.append(self._moveToChrStr)
		self.moveToCharTimer.start(1000, True)  # time to wait for next key press to decide which letter to use...

	def _moveToChrStr(self):
		currentIndex = self.instance.getCurrentIndex()
		index = currentIndex + 1
		if index >= len(self.list):
			index = 0
		while index != currentIndex:
			item = self.list[index]
			if item[1] is not None:
				ref = item[0]
				itemName = getShortName(item[1].getName(ref), ref)
				strlen = len(self._char)
				if (
					strlen == 1 and itemName.startswith(self._char)
					or strlen > 1 and itemName.find(self._char) >= 0
				):
					self.instance.moveSelectionTo(index)
					break
			index += 1
			if index >= len(self.list):
				index = 0
		self._char = ''
		if self._lbl:
			self._lbl.visible = False

def getShortName(name, serviceref):
	if serviceref.flags & eServiceReference.mustDescent:  # Directory
		pathName = serviceref.getPath()
		name = os.path.basename(os.path.normpath(pathName))
		if name == '.Trash':
			name = _("Trash")
	return name.upper()
