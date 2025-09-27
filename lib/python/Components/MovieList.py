# flake8: noqa: F401

from os import stat
from os.path import join, normpath, realpath, split, splitext
from random import shuffle
from struct import Struct

from enigma import BT_KEEP_ASPECT_RATIO, BT_SCALE, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER, eListbox, eListboxPythonMultiContent, eServiceCenter, eServiceReference, eServiceReferenceFS, eSize, eTimer, gFont, iServiceInformation, loadPNG

import NavigationInstance
from ServiceReference import ServiceReference
from skin import getSkinFactor, parseFont
from Components.config import config
from Components.FileList import AUDIO_EXTENSIONS, DVD_EXTENSIONS, IMAGE_EXTENSIONS, MOVIE_EXTENSIONS, KNOWN_EXTENSIONS
from Components.GUIComponent import GUIComponent
from Components.MultiContent import MultiContentEntryPixmapAlphaBlend, MultiContentEntryPixmapAlphaTest, MultiContentEntryProgress, MultiContentEntryText
from Components.Renderer.Picon import getPiconName
from Screens.LocationBox import defaultInhibitDirs
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.FuzzyDate import FuzzyTime
from Tools.LoadPixmap import LoadPixmap
from Tools.TextBoundary import getTextBoundarySize
from Tools.Trashcan import TRASHCAN

cutsParser = Struct(">QI")  # Big-endian, 64-bit PTS and 32-bit type.


class MovieListData:
	def __init__(self):
		pass

# iStaticServiceInformation


class StubInfo:
	def __init__(self):
		pass

	def getName(self, serviceref):
		return split(serviceref.getPath())[1]

	def getLength(self, serviceref):
		return -1

	def getEvent(self, serviceref, *args):
		return None

	def isPlayable(self):
		return True

	def getInfo(self, serviceref, w):
		try:
			if w == iServiceInformation.sTimeCreate:
				result = stat(serviceref.getPath()).st_ctime
			elif w == iServiceInformation.sFileSize:
				result = stat(serviceref.getPath()).st_size
			elif w == iServiceInformation.sDescription:
				result = serviceref.getPath()
			else:
				result = 0
		except Exception:
			result = 0
		return result

	def getInfoString(self, serviceref, w):
		return ""


justStubInfo = StubInfo()


def lastPlayPosFromCache(ref):
	from Screens.InfoBarGenerics import resumePointCache
	return resumePointCache.get(ref.toString(), None)


def moviePlayState(cutsFileName, ref, length):
	"""Returns None, 0..100 for percentage"""
	try:
		with open(cutsFileName, "rb") as fd:  # Read the cuts file first.
			lastCut = None
			cutPTS = None
			while True:
				data = fd.read(cutsParser.size)
				if len(data) < cutsParser.size:
					break
				cut, cutType = cutsParser.unpack(data)
				if cutType == 3:  # Undocumented, but 3 appears to be the stop.
					cutPTS = cut
				else:
					lastCut = cut
		last = lastPlayPosFromCache(ref)  # See what we have in RAM (it might help).
		if last:
			if not lastCut:  # Get the length from the cache.
				lastCut = last[2]
			if not cutPTS:  # Get the cut point from the cache if not in the file.
				cutPTS = last[1]
		if cutPTS is None:
			return None  # Unseen movie.
		if not lastCut:
			if length and (length > 0):
				lastCut = length * 90000
			else:
				return 0  # Unknown.
		if cutPTS >= lastCut:
			return 100
		return (100 * cutPTS) // lastCut
	except Exception:
		cutPTS = lastPlayPosFromCache(ref)
		if cutPTS:
			if not length or (length < 0):
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
		with open(cutsFileName, "rb") as fd:
			cutlist = []
			while True:
				data = fd.read(cutsParser.size)
				if len(data) < cutsParser.size:
					break
				cut, cutType = cutsParser.unpack(data)
				if cutType != 3:
					cutlist.append(data)
		with open(cutsFileName, "wb") as fd:
			fd.write("".join(cutlist))
	except Exception:
		pass
		# import sys
		# print(f"[MovieList] Exception in resetMoviePlayState: {sys.exc_info()[0]} - {sys.exc_info()[1]}!")


class MovieList(GUIComponent):
	GUI_WIDGET = eListbox

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
		self.descr_state = descr_state or self.HIDE_DESCRIPTION
		self.sort_type = sort_type or self.SORT_GROUPWISE
		self.firstFileEntry = 0
		self.parentDirectory = 0
		self.fontName = "Regular"
		self.fontSize = 28 if getSkinFactor() == 1.5 else 20
		self.listHeight = None
		self.listWidth = None
		self.reloadDelayTimer = None
		self.l = eListboxPythonMultiContent()
		self.tags = set()
		self.root = None
		self._playInBackground = None
		self._playInForeground = None
		self._char = ""
		if root is not None:
			self.reload(root)
		self.onSelectionChanged = []
		self.iconPart = []
		for part in list(range(5)):
			self.iconPart.append(LoadPixmap(resolveFilename(SCOPE_GUISKIN, f"icons/part_{part}_4.png")))
		self.iconMovieRec = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/part_new.png"))
		self.iconMoviePlay = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/movie_play.png"))
		self.iconMoviePlayRec = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/movie_play_rec.png"))
		self.iconUnwatched = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/part_unwatched.png"))
		self.iconFolder = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/folder.png"))
		self.iconTrash = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/trashcan.png"))
		self.runningTimers = {}
		self.updateRecordings()
		self.updatePlayPosCache()

	def applySkin(self, desktop, parent):
		if self.skinAttributes is not None:
			attribs = []
			for (attrib, value) in self.skinAttributes:
				if attrib == "font":
					font = parseFont(value, ((1, 1), (1, 1)))
					self.fontName = font.family
					self.fontSize = font.pointSize
				else:
					attribs.append((attrib, value))
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
		if timer is not None and timer.justplay:
			return
		result = {}
		for timer in NavigationInstance.instance.RecordTimer.timer_list:
			if timer.isRunning() and not timer.justplay:
				result[f"{split(timer.Filename)[1]}.ts"] = timer
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
		for callback in self.onSelectionChanged:
			if callback and callable(callback):
				callback()

	def setDescriptionState(self, val):
		self.descr_state = val

	def setSortType(self, type):
		self.sort_type = type

	def setItemsPerPage(self):
		if self.listHeight > 0:
			ext = config.movielist.useextlist.value
			itemHeight = (self.listHeight // config.movielist.itemsperpage.value) * 2 if ext != "0" else self.listHeight // config.movielist.itemsperpage.value
		else:
			itemHeight = 30  # Some default (270/5).
		self.itemHeight = itemHeight
		self.l.setItemHeight(itemHeight)
		self.instance.resize(eSize(self.listWidth, self.listHeight // itemHeight * itemHeight))

	def setFontsize(self):
		self.l.setFont(0, gFont(self.fontName, self.fontSize + config.movielist.fontsize.value))
		self.dateFont = gFont(self.fontName, (self.fontSize - 3) + config.movielist.fontsize.value)
		self.l.setFont(1, self.dateFont)

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
		res = [None]
		ih = self.itemHeight // 2 if ext != "0" else self.itemHeight
		if getSkinFactor() == 1.5:
			listBeginX = 3
			listEndX = 3
			listMarginX = 12
			pathIconSize = 29
			dataIconSize = 25
			progressIconSize = 25
			progressBarSize = 72
			textPosY = 2
		else:
			listBeginX = 2
			listEndX = 2
			listMarginX = 8
			pathIconSize = 25
			dataIconSize = 21
			progressIconSize = 21
			progressBarSize = 48
			textPosY = 1
		textPosX = listBeginX + dataIconSize + listMarginX
		if serviceref.flags & eServiceReference.mustDescent:
			iconSize = pathIconSize  # Directory.
			iconPosX = listBeginX - 1
			iconPosY = int(ih / 2) - int(iconSize / 2)
			if iconPosY < iconPosX:
				iconPosY = iconPosX
			if info is None:  # Name is full path name.
				txt = ".."  # Special case: "parent".
			else:
				p = split(pathName)
				if not p[1]:
					p = split(p[0])  # If path ends in "/", p is blank.
				txt = p[1]
				if txt == TRASHCAN:
					dateSize = getTextBoundarySize(self.instance, self.dateFont, self.l.getItemSize(), _("Trashcan")).width()
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(iconPosX, iconPosY), size=(iconSize, iconSize), png=self.iconTrash, flags=BT_SCALE | BT_KEEP_ASPECT_RATIO))
					res.append(MultiContentEntryText(pos=(textPosX, 0), size=(width - textPosX - dateSize - listMarginX - listEndX, ih), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=_("Deleted items")))
					res.append(MultiContentEntryText(pos=(width - dateSize - listEndX, textPosY), size=(dateSize, self.itemHeight), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=_("Trashcan")))
					return res
			if not config.movielist.show_underscores.value:
				txt = txt.replace("_", " ").strip()
			dateSize = getTextBoundarySize(self.instance, self.dateFont, self.l.getItemSize(), _("Directory")).width()
			res.append(MultiContentEntryPixmapAlphaBlend(pos=(iconPosX, iconPosY), size=(iconSize, iconSize), png=self.iconFolder, flags=BT_SCALE | BT_KEEP_ASPECT_RATIO))
			res.append(MultiContentEntryText(pos=(textPosX, 0), size=(width - textPosX - dateSize - listMarginX - listEndX, ih), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=txt))
			res.append(MultiContentEntryText(pos=(width - dateSize - listEndX, textPosY), size=(dateSize, self.itemHeight), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=_("Directory")))
			return res
		if (data == -1) or (data is None):
			data = MovieListData()
			cur_idx = self.l.getCurrentSelectionIndex()
			x = self.list[cur_idx]  # x = ref, info, begin, ...
			data.len = 0  # Don't recalculate movie list to speedup loading the list.
			self.list[cur_idx] = (x[0], x[1], x[2], data)  # Update entry in list... so next time we don't need to recalculate.
			if config.movielist.show_underscores.value:
				data.txt = info.getName(serviceref)
			else:
				data.txt = info.getName(serviceref).replace("_", " ").strip()
			if config.movielist.hide_extensions.value:
				fileName, fileExtension = splitext(data.txt)
				if fileExtension in KNOWN_EXTENSIONS:
					data.txt = fileName
			data.icon = None
			data.part = None
			if split(pathName)[1] in self.runningTimers:
				if switch == "i":
					if (self.playInBackground or self.playInForeground) and serviceref == (self.playInBackground or self.playInForeground):
						data.icon = self.iconMoviePlayRec
					else:
						data.icon = self.iconMovieRec
				elif switch == "p" or switch == "s":
					data.part = 100
					if (self.playInBackground or self.playInForeground) and serviceref == (self.playInBackground or self.playInForeground):
						data.partcol = 0xffc71d
					else:
						data.partcol = 0xff001d
			elif (self.playInBackground or self.playInForeground) and serviceref == (self.playInBackground or self.playInForeground):
				data.icon = self.iconMoviePlay
			else:
				data.part = moviePlayState(f"{pathName}.cuts", serviceref, data.len)
				if switch == "i":
					if data.part is not None and data.part > 0:
						data.icon = self.iconPart[data.part // 25]
					else:
						if config.usage.movielist_unseen.value:
							data.icon = self.iconUnwatched
				elif switch == "p" or switch == "s":
					if data.part is not None and data.part > 0:
						data.partcol = 0xffc71d
					else:
						if config.usage.movielist_unseen.value:
							data.part = 100
							data.partcol = 0x206333
		len = data.len
		len = f"{len // 60}:{len % 60:02d}" if len > 0 else ""
		iconSize = 0
		if switch == "i":
			iconSize = dataIconSize
			iconPosX = listBeginX
			iconPosY = ih // 2 - iconSize // 2
			if iconPosY < iconPosX:
				iconPosY = iconPosX
			res.append(MultiContentEntryPixmapAlphaBlend(pos=(iconPosX, iconPosY), size=(iconSize, iconSize), png=data.icon, flags=BT_SCALE | BT_KEEP_ASPECT_RATIO))
		elif switch == "p":
			if data.part is not None and data.part > 0:
				iconSize = progressBarSize
				iconPosX = listBeginX
				iconPosY = ih // 2 - iconSize // 8
				if iconPosY < iconPosX:
					iconPosY = iconPosX
				res.append(MultiContentEntryProgress(pos=(iconPosX, iconPosY), size=(iconSize, iconSize // 4), percent=data.part, borderWidth=2, foreColor=data.partcol, foreColorSelected=None, backColor=None, backColorSelected=None))
			else:
				iconSize = dataIconSize
				iconPosX = listBeginX
				iconPosY = ih // 2 - iconSize // 2
				if iconPosY < iconPosX:
					iconPosY = iconPosX
				res.append(MultiContentEntryPixmapAlphaBlend(pos=(iconPosX, iconPosY), size=(iconSize, iconSize), png=data.icon, flags=BT_SCALE | BT_KEEP_ASPECT_RATIO))
		elif switch == "s":
			iconSize = progressIconSize
			iconPosX = listBeginX
			iconPosY = ih // 2 - iconSize // 2
			if iconPosY < iconPosX:
				iconPosY = iconPosX
			if data.part is not None and data.part > 0:
				res.append(MultiContentEntryProgress(pos=(iconPosX, iconPosY), size=(iconSize, iconSize), percent=data.part, borderWidth=2, foreColor=data.partcol, foreColorSelected=None, backColor=None, backColorSelected=None))
			else:
				res.append(MultiContentEntryPixmapAlphaBlend(pos=(iconPosX, iconPosY), size=(iconSize, iconSize), png=data.icon, flags=BT_SCALE | BT_KEEP_ASPECT_RATIO))
		begin_string = ""
		if begin > 0:
			begin_string = ", ".join(FuzzyTime(begin, inPast=True))
		dateSize = serviceSize = getTextBoundarySize(self.instance, self.dateFont, self.l.getItemSize(), begin_string).width()
		textPosX = listBeginX + iconSize + listMarginX if iconSize else listBeginX
		if ext != "0":
			getrec = info.getName(serviceref)
			fileName, fileExtension = splitext(getrec)
			desc = None
			picon = None
			service = None
			try:
				serviceHandler = eServiceCenter.getInstance()
				info = serviceHandler.info(serviceref)
				desc = info.getInfoString(serviceref, iServiceInformation.sDescription)  # Get description.
				ref = info.getInfoString(serviceref, iServiceInformation.sServiceref)  # Get reference.
				service = ServiceReference(ref).getServiceName()  # Get service name.
				serviceSize = getTextBoundarySize(self.instance, self.dateFont, self.l.getItemSize(), service).width()
			except Exception as err:
				print(f"[MovieList] Load extended info get failed: '{str(err)}'!")
			if ext == "2":
				try:
					picon = getPiconName(ref)
					picon = loadPNG(picon)
				except Exception as err:
					print(f"[MovieList] Load picon get failed: '{str(err)}'!")
			if fileExtension in (".ts", ".stream"):
				if ext == "1":
					res.append(MultiContentEntryText(pos=(textPosX, 0), size=(width - textPosX - serviceSize - listMarginX - listEndX, ih), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=data.txt))
					res.append(MultiContentEntryText(pos=(width - serviceSize - listEndX, textPosY), size=(serviceSize, ih), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=service))
				if ext == "2":
					piconSize = ih * 1.667
					res.append(MultiContentEntryText(pos=(textPosX, 0), size=(width - textPosX - dateSize - listMarginX - listEndX, ih), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=data.txt))
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(width - piconSize - listEndX, listEndX), size=(piconSize, ih), png=picon, flags=BT_SCALE | BT_KEEP_ASPECT_RATIO))
				res.append(MultiContentEntryText(pos=(listBeginX, ih + textPosY), size=(width - listBeginX - dateSize - listMarginX - listEndX, ih), font=1, flags=RT_HALIGN_LEFT, text=desc))
				res.append(MultiContentEntryText(pos=(width - dateSize - listEndX, ih + textPosY), size=(dateSize, ih), font=1, flags=RT_HALIGN_RIGHT, text=begin_string))
				return res
			else:
				res.append(MultiContentEntryText(pos=(textPosX, 0), size=(width - textPosX - dateSize - listMarginX - listEndX, ih), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=data.txt))
				res.append(MultiContentEntryText(pos=(width - dateSize - listEndX, ih), size=(dateSize, ih), font=1, flags=RT_HALIGN_RIGHT, text=begin_string))
				return res
		else:
			res.append(MultiContentEntryText(pos=(textPosX, 0), size=(width - textPosX - dateSize - listMarginX - listEndX, ih), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=data.txt))
			res.append(MultiContentEntryText(pos=(width - dateSize - listEndX, textPosY), size=(dateSize, ih), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=begin_string))
			return res

	def moveToFirstMovie(self):
		if self.firstFileEntry < len(self.list):
			self.instance.moveSelectionTo(self.firstFileEntry)
		else:
			self.moveToFirst()  # There are no movies, just directories.

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
		movieList = self.l.getCurrentSelection()
		return movieList and movieList[0] and movieList[1] and movieList[1].getEvent(movieList[0])

	def getCurrent(self):
		movieList = self.l.getCurrentSelection()
		return movieList and movieList[0]

	def getItem(self, index):
		if self.list:
			if len(self.list) > index:
				return self.list[index] and self.list[index][0]

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
		self.load(self.root if root is None else root, filter_tags)
		self.l.setBuildFunc(self.buildMovieListEntry)  # Don't move that to __init__ as this will create memory leak when calling MovieList from OpenWebIf.
		self.l.setList(self.list)

	def removeService(self, service):
		index = self.findService(service)
		if index is not None:
			del self.list[index]
			self.l.setList(self.list)

	def findService(self, service):
		if service is None:
			return None
		for index, item in enumerate(self.list):
			if item[0] == service:
				return index
		return None

	def __len__(self):
		return len(self.list)

	def __getitem__(self, index):
		return self.list[index]

	def __iter__(self):
		return self.list.__iter__()

	def load(self, root, filter_tags):
		del self.list[:]  # This lists our root service, then building a nice list.
		serviceHandler = eServiceCenter.getInstance()
		numberOfDirs = 0
		reflist = root and serviceHandler.list(root)
		if reflist is None:
			print("[MovieList] Listing of movies failed!")
			return
		realtags = set()
		tags = {}
		rootPath = normpath(root.getPath())
		parent = None
		if len(rootPath) > 1 and (realpath(rootPath) != config.movielist.root.value):  # Don't navigate above the "root".
			parent = split(normpath(rootPath))[0]
			currentfolder = join(normpath(rootPath), "")
			if parent and (parent not in defaultInhibitDirs) and not currentfolder.endswith(config.usage.default_path.value):
				parent = join(parent, "")  # Enigma wants an extra "/" appended.
			ref = eServiceReference(eServiceReference.idFile, eServiceReference.flagDirectory, eServiceReferenceFS.directory)
			ref.setPath(parent)
			ref.flags = eServiceReference.flagDirectory
			self.list.append((ref, None, 0, -1))
			numberOfDirs += 1
		while True:
			serviceref = reflist.getNext()
			if not serviceref.valid():
				break
			info = serviceHandler.info(serviceref)
			if info is None:
				info = justStubInfo
			begin = info.getInfo(serviceref, iServiceInformation.sTimeCreate)
			if serviceref.flags & eServiceReference.mustDescent:
				dirname = info.getName(serviceref)
				if not dirname.endswith(".AppleDouble/") and not dirname.endswith(".AppleDesktop/") and not dirname.endswith(".AppleDB/") and not dirname.endswith("Network Trash Folder/") and not dirname.endswith("Temporary Items/"):
					self.list.append((serviceref, info, begin, -1))
					numberOfDirs += 1
				continue
			if serviceref.getPath().endswith(".jpg"):  # Ignore all JPEG files as they are often added as movie posters but should not be listed as extra media.
				continue
			# Convert space-separated list of tags into a set.
			this_tags = info.getInfoString(serviceref, iServiceInformation.sTags).split(" ")
			name = info.getName(serviceref)
			# OSX puts a lot of "._*: everywhere, we need to skip them.
			if name[:2] == "._":
				continue
			if this_tags == [""]:  # No tags? Auto tag.
				this_tags = name.replace(",", " ").replace(".", " ").replace("_", " ").replace(":", " ").split()
			else:
				realtags.update(this_tags)
			for tag in this_tags:
				if len(tag) >= 4:
					if tag in tags:
						tags[tag].append(name)
					else:
						tags[tag] = [name]
			# Filter_tags is either None (which means no filter at all), or a set. In this case,
			# all elements of filter_tags must be present, otherwise the entry will be dropped.
			if filter_tags is not None:
				this_tags_fullname = [" ".join(this_tags)]
				this_tags_fullname = set(this_tags_fullname)
				this_tags = set(this_tags)
				if not this_tags.issuperset(filter_tags) and not this_tags_fullname.issuperset(filter_tags):
					# print(f"[MovieList] Skipping '{name}' tags='{this_tags}' filter='{filter_tags}'.")
					continue
			self.list.append((serviceref, info, begin, -1))
		self.firstFileEntry = numberOfDirs
		self.parentDirectory = 0
		self.list.sort(key=self.buildGroupwiseSortkey)
		if self.sort_type == MovieList.SORT_ALPHANUMERIC:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildAlphaNumericSortKey) + sorted(self.list[numberOfDirs:], key=self.buildAlphaNumericSortKey)
		elif self.sort_type == MovieList.SORT_ALPHANUMERIC_REVERSE:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildAlphaNumericSortKey, reverse=True) + sorted(self.list[numberOfDirs:], key=self.buildAlphaNumericSortKey, reverse=True)
		elif self.sort_type == MovieList.SORT_ALPHANUMERIC_FLAT:
			self.list.sort(key=self.buildAlphaNumericFlatSortKey)
		elif self.sort_type == MovieList.SORT_ALPHANUMERIC_FLAT_REVERSE:
			self.list.sort(key=self.buildAlphaNumericFlatSortKey, reverse=True)
		elif self.sort_type == MovieList.SORT_RECORDED:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildBeginTimeSortKey) + sorted(self.list[numberOfDirs:], key=self.buildBeginTimeSortKey)
		elif self.sort_type == MovieList.SORT_RECORDED_REVERSE:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildBeginTimeSortKey, reverse=True) + sorted(self.list[numberOfDirs:], key=self.buildBeginTimeSortKey, reverse=True)
		elif self.sort_type == MovieList.SHUFFLE:
			dirlist = self.list[:numberOfDirs]
			shufflelist = self.list[numberOfDirs:]
			shuffle(shufflelist)
			self.list = dirlist + shufflelist
		elif self.sort_type == MovieList.SORT_ALPHA_DATE_OLDEST_FIRST:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildAlphaDateSortKey) + sorted(self.list[numberOfDirs:], key=self.buildAlphaDateSortKey)
		elif self.sort_type == MovieList.SORT_ALPHAREV_DATE_NEWEST_FIRST:
			self.list = sorted(self.list[:numberOfDirs], key=self.buildAlphaDateSortKey, reverse=True) + sorted(self.list[numberOfDirs:], key=self.buildAlphaDateSortKey, reverse=True)
		for x in self.list:
			if x[1]:
				tmppath = x[1].getName(x[0])[:-1] if x[1].getName(x[0]).endswith("/") else x[1].getName(x[0])
				if tmppath.endswith(".Trash"):
					self.list.insert(0, self.list.pop(self.list.index(x)))
					break
		if self.root and numberOfDirs > 0:
			rootPath = normpath(self.root.getPath())
			if not rootPath.endswith("/"):
				rootPath += "/"
			if rootPath != parent:
				# With new sort types directories may be in-between files, so scan whole
				# list for parentDirectory index. Usually it is the first one anyway.
				for index, item in enumerate(self.list):
					if item[0].flags & eServiceReference.mustDescent:
						itempath = normpath(item[0].getPath())
						if not itempath.endswith("/"):
							itempath += "/"
						if itempath == rootPath:
							self.parentDirectory = index
							break
		self.root = root
		# Finally, store a list of all tags which were found. these can be presented to the user to filter the list.
		# ML: Only use the tags that occur more than once in the list OR that were really in the tag set of some file.
		rtags = {}  # Reverse the dictionary to see which unique movie each tag now references.
		for tag, movies in list(tags.items()):
			if (len(movies) > 1) or (tag in realtags):
				movies = tuple(movies)  # A tuple can be hashed, but a list not.
				item = rtags.get(movies, [])
				if not item:
					rtags[movies] = item
				item.append(tag)
		self.tags = {}
		for movies, tags in list(rtags.items()):
			movie = movies[0]
			tags.sort(key=movie.find)  # Format the tag lists so that they are in "original" order.
			first = movie.find(tags[0])
			last = movie.find(tags[-1]) + len(tags[-1])
			match = movie
			start = 0
			end = len(movie)
			for m in movies[1:]:  # Check if the set has a complete sentence in common, and how far.
				if m[start:end] != match:
					if not m.startswith(movie[:last]):
						start = first
					if not m.endswith(movie[first:]):
						end = last
					match = movie[start:end]
					if m[start:end] != match:
						match = ""
						break
			if match:
				self.tags[match] = set(tags)
				continue
			else:
				match = " ".join(tags)
				if len(match) > 2:  # Omit small words.
					self.tags[match] = set(tags)

	def buildAlphaNumericSortKey(self, x):
		ref = x[0]  # x = ref, info, begin, ...
		name = x[1] and x[1].getName(ref)
		if ref.flags & eServiceReference.mustDescent:
			return 0, name and name.lower() or "", -x[2]
		return 1, name and name.lower() or "", -x[2]

	def buildAlphaDateSortKey(self, x):  # As for buildAlphaNumericSortKey, but without negating dates.
		ref = x[0]  # x = ref, info, begin, ...
		name = x[1] and x[1].getName(ref)
		if ref.flags & eServiceReference.mustDescent:
			return 0, name and name.lower() or "", x[2]
		return 1, name and name.lower() or "", x[2]

	def buildAlphaNumericFlatSortKey(self, x):
		ref = x[0]
		name = x[1] and x[1].getName(ref)
		if name and ref.flags & eServiceReference.mustDescent:
			p = split(name)  # Only use directory base name for sorting.
			if not p[1]:  # if path ends in "/", p is blank.
				p = split(p[0])
			name = p[1]
		# print(f"[MovieList] Sorting for '{name}'.")
		return 1, name and name.lower() or "", -x[2]

	def buildBeginTimeSortKey(self, x):
		ref = x[0]  # x = ref, info, begin, ...
		if ref.flags & eServiceReference.mustDescent:
			return 0, "", x[1] and -stat(ref.getPath()).st_mtime or 0
		return 1, "", -x[2]

	def buildGroupwiseSortkey(self, x):  # Sort recordings by date, sort MP3 and stuff by name.
		ref = x[0]  # x = ref, info, begin, ...
		return self.buildAlphaNumericSortKey(x) if ref.type >= eServiceReference.idUser else self.buildBeginTimeSortKey(x)

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
		self.moveToCharTimer.start(1000, True)  # Time to wait for next key press to decide which letter to use.

	def moveToString(self, char, lbl=None):
		self._char = f"{self._char}{char.upper()}"
		self._lbl = lbl
		if lbl:
			lbl.setText(self._char)
			lbl.visible = True
		self.moveToCharTimer = eTimer()
		self.moveToCharTimer.callback.append(self._moveToChrStr)
		self.moveToCharTimer.start(1000, True)  # Time to wait for next key press to decide which letter to use.

	def _moveToChrStr(self):
		currentIndex = self.instance.getCurrentIndex()
		found = False
		if currentIndex < (len(self.list) - 1):
			itemsBelow = self.list[currentIndex + 1:]
			for index, item in enumerate(itemsBelow):  # First search the items below the selection.
				if item[1] is None:
					continue
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
		if found is False and currentIndex > 0:
			itemsAbove = self.list[1:currentIndex]  # First item (0) points parent folder - no point in including it.
			for index, item in enumerate(itemsAbove):
				if item[1] is None:
					continue
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
		self._char = ""
		if self._lbl:
			self._lbl.visible = False


def getShortName(name, serviceref):
	if serviceref.flags & eServiceReference.mustDescent:  # Directory.
		pathName = serviceref.getPath()
		p = split(pathName)
		if not p[1]:  # If path ends in "/", p is blank.
			p = split(p[0])
		return p[1].upper()
	else:
		return name
