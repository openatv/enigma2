# flake8: noqa: F401

from os import stat
from os.path import islink, join, normpath, realpath, split, splitext
from random import shuffle
from struct import Struct

from enigma import BT_KEEP_ASPECT_RATIO, BT_SCALE, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER, eListbox, eListboxPythonMultiContent, eServiceCenter, eServiceReference, eServiceReferenceFS, eSize, eTimer, gFont, iServiceInformation, loadPNG

import NavigationInstance
from ServiceReference import ServiceReference
from skin import fonts, getSkinFactor, parameters, parseFont
from Components.config import config
from Components.FileList import AUDIO_EXTENSIONS, DVD_EXTENSIONS, IMAGE_EXTENSIONS, KNOWN_EXTENSIONS, MOVIE_EXTENSIONS
from Components.GUIComponent import GUIComponent
from Components.MovieListSettings import movieListSettings
from Components.MovieListStyle import movieListStyles
from Components.MultiContent import MultiContentEntryPixmapAlphaBlend, MultiContentEntryPixmapAlphaTest, MultiContentEntryProgress, MultiContentEntryText
from Components.SkinIcon import SkinIcon, loadSkinIcon
from Components.Renderer.Picon import getChannelSelectionPiconName
from Screens.LocationBox import defaultInhibitDirs
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap
from Tools.MovieFileOperations import writeMovieStatus
from Tools.MovieMaintenance import MovieStructure, movieMaintenanceState
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


class MovieListServiceInfo(StubInfo):
	def __init__(self, item):
		self.item = item

	def getName(self, serviceRef):
		return self.item.get("title") or split(serviceRef.getPath())[1]

	def getLength(self, serviceRef):
		return self.item.get("duration") or -1

	def getInfo(self, serviceRef, field):
		return self.item.get({iServiceInformation.sTimeCreate: "recordedAt", iServiceInformation.sFileSize: "fileSize"}.get(field), 0) or 0

	def getInfoObject(self, serviceRef, field):
		return self.getInfo(serviceRef, field)

	def getInfoString(self, serviceRef, field):
		return self.item.get({iServiceInformation.sDescription: "description", iServiceInformation.sServiceref: "serviceReference", iServiceInformation.sTags: "tags"}.get(field), "") or ""


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
				elif cutType == 5:
					lastCut = cut
		last = lastPlayPosFromCache(ref)  # See what we have in RAM (it might help).
		if last:
			if not lastCut:  # Get the length from the cache.
				lastCut = last[2]
			if cutPTS is None:  # Zero is an explicit start position.
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
			length = cutPTS[2] or (max(0, length or 0) * 90000)
			if length:
				if cutPTS[1] >= length:
					return 100
				return (100 * cutPTS[1]) // length
			else:
				return 0
		return None


def resetMoviePlayState(cutsFileName, ref=None):
	try:
		if not cutsFileName.endswith(".cuts"):
			return
		writeMovieStatus(cutsFileName[:-5])
		if ref is not None:
			# InfoBarGenerics imports MovieList; resolve this entry point after startup.
			from Screens.InfoBarGenerics import delResumePoint
			delResumePoint(ref)
	except (OSError, ValueError) as error:
		print(f"[MovieList] Unable to reset playback position: {error}")


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
		self.listStyle = None
		self.styleOverride = None
		self.styleMode = "default"
		self.isGrid = False
		self.styleScale = ((1, 1), (1, 1))
		self.movieMetadata = {}
		self.cached = False
		self.moviePosters = {}
		self.moviePreviews = {}
		self.markedPaths = set()
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
			self.iconPart.append(loadSkinIcon("MovieList", f"part_{part}_4", f"icons/part_{part}_4.png"))
		self.iconMovieRec = loadSkinIcon("MovieList", "record", "icons/part_new.png")
		self.iconMoviePlay = loadSkinIcon("MovieList", "play", "icons/movie_play.png")
		self.iconMoviePlayRec = loadSkinIcon("MovieList", "play_record", "icons/movie_play_rec.png")
		self.iconUnwatched = loadSkinIcon("MovieList", "unwatched", "icons/part_unwatched.png")
		self.iconFolder = loadSkinIcon("MovieList", "folder", "icons/folder.png")
		self.iconTrash = loadSkinIcon("MovieList", "trash", "icons/trashcan.png")
		self.runningTimers = {}
		self.updateRecordings()
		self.updatePlayPosCache()

	def applySkin(self, desktop, parent):
		self.styleScale = parent.scale
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
		if self._playInForeground is not value:
			previous = self._playInForeground
			self._playInForeground = value
			if self.listStyle is not None:
				for serviceRef in (previous, value):
					index = self.findService(serviceRef)
					if index is not None:
						self.invalidateItem(index)
						self.l.invalidateEntry(index)

	playInForeground = property(get_playInForeground, set_playInForeground)

	def updatePlayPosCache(self):
		from Screens.InfoBarGenerics import updateresumePointCache
		updateresumePointCache()

	def updateRecordings(self, timer=None):
		if timer is not None and timer.justplay:
			return
		result = {}
		for recording in NavigationInstance.instance.RecordTimer.timer_list:
			if recording.isRunning() and not recording.justplay:
				result[f"{split(recording.Filename)[1]}.ts"] = recording
		if self.runningTimers == result:
			return
		self.runningTimers = result
		if timer is not None:
			movieMaintenanceState.invalidate((f"{timer.Filename}.ts",))
			if self.reloadDelayTimer is not None:
				self.reloadDelayTimer.stop()
			self.reloadDelayTimer = eTimer()
			self.reloadDelayTimer.callback.append(self.reload)
			self.reloadDelayTimer.start(5000, 1)

	def updateRecordingLengths(self):
		if config.movielist.showRecordingLength.value and not self.cached:
			for service, info, begin, data in self.list:
				path = service.getPath()
				if (timer := self.runningTimers.get(split(path)[1])) is not None and path == f"{timer.Filename}.ts":
					info = eServiceCenter.getInstance().info(service)
					length = info.getLength(service) if info else 0
					self.movieMetadata.setdefault(path, {})["duration"] = max(0, length)
					self.invalidateMoviePaths((path,))

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
		if self.descr_state != val:
			self.descr_state = val
			self.list = [(x[0], x[1], x[2], None) for x in self.list]
			self.l.setList(self.list)

	def setSortType(self, type):
		self.sort_type = type

	def setItemsPerPage(self):
		styleSetting = getattr(config.movielist, "widgetStyle", None)
		styleName = self.styleOverride if self.styleOverride is not None else styleSetting.value if styleSetting is not None else ""
		self.listStyle = None
		self.isGrid = False
		self.l.setTemplate(None)
		if self.instance is not None and styleName:
			width = self.instance.size().width() - self.instance.getScrollbarWidth() - self.instance.getScrollbarOffset()
			height = self.instance.size().height()
			if width > 0 and height > 0:
				self.listStyle = movieListStyles.createTemplate(styleName, width, height, self.styleScale, self.styleMode)
		if self.listStyle is not None:
			self.listStyle.apply(self.l)
			self.itemHeight = self.listStyle.itemHeight
			self.isGrid = self.listStyle.isGrid
			self.instance.resize(eSize(self.listWidth, height // self.itemHeight * self.itemHeight))
			return
		self.l.setOrientation(eListbox.orVertical)
		listHeight = self.instance.size().height() if styleName else self.listHeight
		if listHeight > 0:
			ext = config.movielist.useextlist.value
			minimumHeight = max(34 if getSkinFactor() == 1.5 else 28, self.fontSize + config.movielist.fontsize.value + 8)
			itemHeight = max(minimumHeight, listHeight // config.movielist.itemsperpage.value) * (2 if ext != "0" else 1)
		else:
			itemHeight = 30  # Some default (270/5).
		self.itemHeight = itemHeight
		self.l.setItemHeight(itemHeight)
		self.setFontsize()
		self.instance.resize(eSize(self.listWidth, listHeight // itemHeight * itemHeight))

	def setStyleMode(self, mode):
		if self.styleMode != mode:
			self.styleMode = mode
			if self.instance is not None:
				self.instance.resize(eSize(self.listWidth, self.listHeight))
				self.setItemsPerPage()
				self.invalidateMoviePaths(self.movieMetadata)

	def setFontsize(self):
		if self.listStyle is not None:
			for index, font in enumerate(self.listStyle.template["fonts"]):
				self.l.setFont(index, font)
			return
		self.l.setFont(0, gFont(self.fontName, self.fontSize + config.movielist.fontsize.value))
		self.dateFont = gFont(self.fontName, (self.fontSize - 3) + config.movielist.fontsize.value)
		self.l.setFont(1, self.dateFont)
		self.setIconFont()

	def setIconFont(self):
		if parameters.get("MovieListNativeIcons", 0):
			font = fonts.get("MovieListIcons", ("enigma2icons", self.fontSize))
			height = getattr(self, "itemHeight", font[1] + 4)
			if config.movielist.useextlist.value != "0":
				height //= 2
			self.iconFontSize = max(1, min(font[1], height - 4))
			self.l.setFont(2, gFont(font[0], self.iconFontSize))

	def iconEntry(self, icon, pos, size):
		if isinstance(icon, SkinIcon):
			return icon.entry(pos, size, 2)
		return MultiContentEntryPixmapAlphaBlend(pos=pos, size=size, png=icon, flags=BT_SCALE | BT_KEEP_ASPECT_RATIO)

	def invalidateItem(self, index):
		x = self.list[index]
		self.list[index] = (x[0], x[1], x[2], None)

	def invalidateCurrentItem(self):
		self.invalidateItem(self.getCurrentIndex())

	def buildMovieListEntry(self, serviceref, info, begin, data):
		if self.listStyle is not None:
			return self.buildStyledMovieListEntry(serviceref, info, begin, data)
		if data is not None and data != -1 and hasattr(data, "styleValues"):
			data = None
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
		if parameters.get("MovieListNativeIcons", 0):
			pathIconSize = dataIconSize = progressIconSize = min(ih, self.iconFontSize + 4)
		else:
			maximumIconSize = max(1, ih - 2 * listBeginX)
			pathIconSize = min(pathIconSize, maximumIconSize)
			dataIconSize = min(dataIconSize, maximumIconSize)
			progressIconSize = min(progressIconSize, maximumIconSize)
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
				if isinstance(info, MovieListServiceInfo):
					txt = info.getName(serviceref)
				if txt == TRASHCAN:
					dateSize = getTextBoundarySize(self.instance, self.dateFont, self.l.getItemSize(), _("Trashcan")).width()
					res.append(self.iconEntry(self.iconTrash, (iconPosX, iconPosY), (iconSize, iconSize)))
					res.append(MultiContentEntryText(pos=(textPosX, 0), size=(width - textPosX - dateSize - listMarginX - listEndX, ih), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=_("Deleted items")))
					res.append(MultiContentEntryText(pos=(width - dateSize - listEndX, textPosY), size=(dateSize, self.itemHeight), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=_("Trashcan")))
					return res
			if not config.movielist.show_underscores.value:
				txt = txt.replace("_", " ").strip()
			directoryText = movieListSettings.directoryText(pathName) if info is not None else _("Directory")
			directoryText = self.movieMetadata.get(pathName, {}).get("mediaStructure") or directoryText
			dateSize = getTextBoundarySize(self.instance, self.dateFont, self.l.getItemSize(), directoryText).width()
			res.append(self.iconEntry(self.iconFolder, (iconPosX, iconPosY), (iconSize, iconSize)))
			res.append(MultiContentEntryText(pos=(textPosX, 0), size=(width - textPosX - dateSize - listMarginX - listEndX, ih), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=txt))
			res.append(MultiContentEntryText(pos=(width - dateSize - listEndX, textPosY), size=(dateSize, self.itemHeight), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=directoryText))
			return res
		if (data == -1) or (data is None):
			data = MovieListData()
			cur_idx = self.l.getCurrentSelectionIndex()
			x = self.list[cur_idx]  # x = ref, info, begin, ...
			data.len = 0  # Don't recalculate movie list to speedup loading the list.
			self.list[cur_idx] = (x[0], x[1], x[2], data)  # Update entry in list... so next time we don't need to recalculate.
			metadata = self.movieMetadata.get(pathName, {})
			recordingTitle = info.item.get("recordingTitle", "") if isinstance(info, MovieListServiceInfo) else info.getName(serviceref)
			data.txt = movieListSettings.title(pathName, recordingTitle, metadata)
			fileInfo = movieListSettings.fileInfo(pathName, metadata, split(pathName)[1] in self.runningTimers)
			if fileInfo:
				data.txt = f"{data.txt} · {fileInfo}"
			data.icon = None
			data.part = None
			data.partcol = None
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
			elif switch in ("i", "p", "s"):
				data.part = info.item.get("progress") if isinstance(info, MovieListServiceInfo) else moviePlayState(f"{pathName}.cuts", serviceref, data.len)
				if pathName in getattr(self, "fileSnapshots", {}):
					self.fileSnapshots[pathName]["progress"] = data.part
				watchState = movieListSettings.watchState(data.part)
				if switch == "i":
					if watchState == "watched":
						data.icon = self.iconPart[4]
					elif watchState == "watching":
						data.icon = self.iconPart[max(1, min(3, data.part // 25))]
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
			if movieListSettings.isNew(begin, data.part if data.part is not None else metadata.get("progress")):
				data.txt = f"{_('New')} · {data.txt}"
		len = data.len
		len = f"{len // 60}:{len % 60:02d}" if len > 0 else ""
		iconSize = 0
		if switch == "i":
			iconSize = dataIconSize
			iconPosX = listBeginX
			iconPosY = ih // 2 - iconSize // 2
			if iconPosY < iconPosX:
				iconPosY = iconPosX
			res.append(self.iconEntry(data.icon, (iconPosX, iconPosY), (iconSize, iconSize)))
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
				res.append(self.iconEntry(data.icon, (iconPosX, iconPosY), (iconSize, iconSize)))
		elif switch == "s":
			iconSize = progressIconSize
			iconPosX = listBeginX
			iconPosY = ih // 2 - iconSize // 2
			if iconPosY < iconPosX:
				iconPosY = iconPosX
			if data.part is not None and data.part > 0:
				res.append(MultiContentEntryProgress(pos=(iconPosX, iconPosY), size=(iconSize, iconSize), percent=data.part, borderWidth=2, foreColor=data.partcol, foreColorSelected=None, backColor=None, backColorSelected=None))
			else:
				res.append(self.iconEntry(data.icon, (iconPosX, iconPosY), (iconSize, iconSize)))
		begin_string = ""
		if begin > 0:
			begin_string = movieListSettings.dateText(begin)
		dateSize = serviceSize = getTextBoundarySize(self.instance, self.dateFont, self.l.getItemSize(), begin_string).width()
		textPosX = listBeginX + iconSize + listMarginX if iconSize else listBeginX
		displayTitle = f"✓ {data.txt}" if pathName in self.markedPaths else data.txt
		if ext != "0":
			getrec = info.getName(serviceref)
			fileName, fileExtension = splitext(getrec)
			desc = None
			picon = None
			service = None
			try:
				desc = info.getInfoString(serviceref, iServiceInformation.sDescription) if self.descr_state == self.SHOW_DESCRIPTION else ""
				ref = info.getInfoString(serviceref, iServiceInformation.sServiceref)  # Get reference.
				service = ServiceReference(ref).getServiceName()  # Get service name.
				serviceSize = getTextBoundarySize(self.instance, self.dateFont, self.l.getItemSize(), service).width()
			except Exception as err:
				print(f"[MovieList] Load extended info get failed: '{str(err)}'!")
			if ext == "2":
				try:
					picon = getChannelSelectionPiconName(ref)
					picon = loadPNG(picon)
				except Exception as err:
					print(f"[MovieList] Load picon get failed: '{str(err)}'!")
			if fileExtension in (".ts", ".stream"):
				if ext == "1":
					res.append(MultiContentEntryText(pos=(textPosX, 0), size=(width - textPosX - serviceSize - listMarginX - listEndX, ih), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=displayTitle))
					res.append(MultiContentEntryText(pos=(width - serviceSize - listEndX, textPosY), size=(serviceSize, ih), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=service))
				if ext == "2":
					piconSize = ih * 1.667
					res.append(MultiContentEntryText(pos=(textPosX, 0), size=(width - textPosX - dateSize - listMarginX - listEndX, ih), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=displayTitle))
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(width - piconSize - listEndX, listEndX), size=(piconSize, ih), png=picon, flags=BT_SCALE | BT_KEEP_ASPECT_RATIO))
				res.append(MultiContentEntryText(pos=(listBeginX, ih + textPosY), size=(width - listBeginX - dateSize - listMarginX - listEndX, ih), font=1, flags=RT_HALIGN_LEFT, text=desc))
				res.append(MultiContentEntryText(pos=(width - dateSize - listEndX, ih + textPosY), size=(dateSize, ih), font=1, flags=RT_HALIGN_RIGHT, text=begin_string))
				return res
			else:
				res.append(MultiContentEntryText(pos=(textPosX, 0), size=(width - textPosX - dateSize - listMarginX - listEndX, ih), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=displayTitle))
				res.append(MultiContentEntryText(pos=(width - dateSize - listEndX, ih), size=(dateSize, ih), font=1, flags=RT_HALIGN_RIGHT, text=begin_string))
				return res
		else:
			res.append(MultiContentEntryText(pos=(textPosX, 0), size=(width - textPosX - dateSize - listMarginX - listEndX, ih), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=displayTitle))
			res.append(MultiContentEntryText(pos=(width - dateSize - listEndX, textPosY), size=(dateSize, ih), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=begin_string))
			return res

	def buildStyledMovieListEntry(self, serviceRef, info, begin, data):
		if data is not None and data != -1 and getattr(data, "styleFields", None) == self.listStyle.fields:
			return data.styleValues
		path = serviceRef.getPath()
		isDirectory = bool(serviceRef.flags & eServiceReference.mustDescent)
		metadata = self.movieMetadata.get(path, {})
		fields = self.listStyle.fields
		title = ""
		date = ""
		description = ""
		serviceName = ""
		status = ""
		progress = -1  # Native progress skips values outside 0..100.
		if isDirectory:
			title = split(normpath(path))[1] if info is not None else ".."
			if isinstance(info, MovieListServiceInfo):
				title = info.getName(serviceRef)
			kind = movieListSettings.directoryText(path) if info is not None else _("Directory")
			kind = metadata.get("mediaStructure") or kind
			if title == TRASHCAN:
				title = _("Deleted items")
				kind = _("Trashcan")
			date = kind
		else:
			recordingTitle = info.item.get("recordingTitle", "") if isinstance(info, MovieListServiceInfo) else info.getName(serviceRef) if info is not None else ""
			title = movieListSettings.title(path, recordingTitle, metadata)
			kind = splitext(path)[1][1:].upper() if config.movielist.showFormat.value else ""
			if "Date" in fields and begin > 0:
				date = movieListSettings.dateText(begin)
			if info is not None:
				try:
					if "Description" in fields and "description" not in metadata:
						description = info.getInfoString(serviceRef, iServiceInformation.sDescription)
					if "ServiceName" in fields:
						reference = info.getInfoString(serviceRef, iServiceInformation.sServiceref)
						serviceName = ServiceReference(reference).getServiceName() if reference else ""
				except (OSError, RuntimeError) as error:
					print(f"[MovieList] Unable to read movie details: {error}")
			if fields.intersection(("Status", "Progress")):
				if split(path)[1] in self.runningTimers:
					status = _("Recording")
				elif serviceRef == (self.playInBackground or self.playInForeground):
					status = _("Playing")
				elif config.usage.show_icons_in_movielist.value != "o":
					progress = metadata.get("progress")
					if progress is not None:
						progress = max(0, min(100, progress))
					if "progress" in metadata and (movieListSettings.watchState(progress) != "unwatched" or config.usage.movielist_unseen.value):
						status = movieListSettings.watchText(progress)
			if movieListSettings.isNew(begin, metadata.get("progress")):
				status = f"{_('New')} · {status}" if status else _("New")
		if isDirectory and not config.movielist.show_underscores.value:
			title = title.replace("_", " ").strip()
		data = MovieListData()
		description = metadata.get("description", description) if self.descr_state == self.SHOW_DESCRIPTION else ""
		data.txt = title  # Front-panel summaries and existing plugins use the legacy title field.
		if path in self.markedPaths:
			title = f"✓ {title}"
		data.styleFields = fields
		if progress is None:
			progress = -1
		fileInfo = movieListSettings.fileInfo(path, metadata, split(path)[1] in self.runningTimers) if not isDirectory else kind
		if not isDirectory and fileInfo and "FileInfo" not in fields:
			title = f"{title} · {fileInfo}"
		data.styleValues = (title, date, description, serviceName, status, progress, kind, self.moviePosters.get(path), str(metadata.get("year", "")), str(metadata.get("rating", "")), fileInfo, self.moviePreviews.get(path))
		index = self.l.getCurrentSelectionIndex()
		self.list[index] = (serviceRef, info, begin, data)
		return data.styleValues

	def invalidateMoviePaths(self, paths):
		for index, item in enumerate(self.list):
			if item[0].getPath() in paths:
				self.invalidateItem(index)
				self.l.invalidateEntry(index)

	def setMovieMetadata(self, items):
		items = {x: dict(items[x]) for x in items}
		for path, item in items.items():
			if path in getattr(self, "fileSnapshots", {}):
				self.fileSnapshots[path].update(item)
		for path, item in self.movieMetadata.items():
			if item.get("mediaStructure") or split(path)[1] in self.runningTimers:
				items[path] = dict(items.get(path, {}), **{x: item[x] for x in ("mediaStructure", "playPath", "duration") if x in item})
		paths = {path for path in self.movieMetadata.keys() | items.keys() if self.movieMetadata.get(path) != items.get(path)}
		self.movieMetadata = dict(items)
		self.moviePosters = {path: pixmap for path, pixmap in self.moviePosters.items() if path in items}
		self.moviePreviews = {path: pixmap for path, pixmap in self.moviePreviews.items() if path in items}
		self.invalidateMoviePaths(paths)

	def setMoviePoster(self, path, pixmap):
		if path in self.movieMetadata and self.moviePosters.get(path) is not pixmap:
			self.moviePosters[path] = pixmap
			self.invalidateMoviePaths((path,))

	def setMoviePreview(self, path, pixmap):
		if path in self.movieMetadata and self.moviePreviews.get(path) is not pixmap:
			self.moviePreviews[path] = pixmap
			self.invalidateMoviePaths((path,))

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
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)

	def reload(self, root=None, filter_tags=None):
		if self.reloadDelayTimer is not None:
			self.reloadDelayTimer.stop()
			self.reloadDelayTimer = None
		self.load(self.root if root is None else root, filter_tags)
		self.l.setBuildFunc(self.buildMovieListEntry)  # Don't move that to __init__ as this will create memory leak when calling MovieList from OpenWebIf.
		self.l.setList(self.list)

	def removeService(self, service):
		movieMaintenanceState.invalidate((service.getPath(),))
		if service.flags & eServiceReference.mustDescent:
			movieMaintenanceState.catalogueReady = False
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
		self.setStyleMode("default")
		del self.list[:]  # This lists our root service, then building a nice list.
		self.movieMetadata.clear()
		self.moviePosters.clear()
		self.moviePreviews.clear()
		serviceHandler = eServiceCenter.getInstance()
		numberOfDirs = 0
		rootPath = normpath(root.getPath()) if root else ""
		lifetime = int(config.movielist.fileListCache.value) if config.movielist.fileListCache.value != "off" else 0
		cached = movieMaintenanceState.getDirectory(rootPath, lifetime)
		self.cached = cached is not None
		reflist = root and serviceHandler.list(root) if cached is None else None
		if cached is None and reflist is None:
			print("[MovieList] Listing of movies failed!")
			return
		realtags = set()
		tags = {}
		hiddenFolders = set(config.movielist.hiddenFolders.value)
		parent = None
		if len(rootPath) > 1 and (rootPath if cached is not None else realpath(rootPath)) != config.movielist.root.value:  # Don't navigate above the "root".
			parent = split(normpath(rootPath))[0]
			currentfolder = join(normpath(rootPath), "")
			if parent and (parent not in defaultInhibitDirs) and not currentfolder.endswith(config.usage.default_path.value):
				parent = join(parent, "")  # Enigma wants an extra "/" appended.
			ref = eServiceReference(eServiceReference.idFile, eServiceReference.flagDirectory, eServiceReferenceFS.directory)
			ref.setPath(parent)
			ref.flags = eServiceReference.flagDirectory
			self.list.append((ref, None, 0, -1))
			numberOfDirs += 1
		records = []
		iterator = iter(cached) if cached is not None else None
		while True:
			if iterator is not None:
				entry = next(iterator, None)
				if entry is None:
					break
				serviceref, item = entry
				info = MovieListServiceInfo(item)
				self.movieMetadata[serviceref.getPath()] = dict(item)
			else:
				serviceref = reflist.getNext()
				if not serviceref.valid():
					break
				if normpath(serviceref.getPath()) in hiddenFolders:
					continue
				info = serviceHandler.info(serviceref) or justStubInfo
				path = serviceref.getPath()
				item = {"path": path, "title": info.getName(serviceref), "recordedAt": info.getInfo(serviceref, iServiceInformation.sTimeCreate), "symlink": islink(normpath(path)) if lifetime or not config.movielist.showSymlinks.value else False}
				item["recordingTitle"] = item["title"]
				if serviceref.flags & eServiceReference.mustDescent:
					item["title"] = split(normpath(path))[1]
					try:
						item["recordedAt"] = int(stat(path).st_mtime)
					except OSError:
						continue
					if not item["symlink"] or config.movielist.showSymlinks.value:
						item.update(MovieStructure.detect(path, config.movielist.recognizeDVD.value, config.movielist.recognizeBluray.value, config.movielist.recognizeMovieFolders.value))
				elif lifetime:
					item.update(description=info.getInfoString(serviceref, iServiceInformation.sDescription), serviceReference=info.getInfoString(serviceref, iServiceInformation.sServiceref), tags=info.getInfoString(serviceref, iServiceInformation.sTags))
				records.append((serviceref, item))
			if normpath(serviceref.getPath()) in hiddenFolders:
				continue
			if item.get("symlink") and not config.movielist.showSymlinks.value:
				continue
			begin = item["recordedAt"]
			if serviceref.flags & eServiceReference.mustDescent:
				if item.get("mediaStructure"):
					self.movieMetadata[serviceref.getPath()] = dict(item)
					info = MovieListServiceInfo(dict(item, title=split(normpath(serviceref.getPath()))[1]))
				elif not config.movielist.showDirectories.value and split(normpath(serviceref.getPath()))[1] != TRASHCAN:
					continue
				if split(normpath(serviceref.getPath()))[1] not in (".AppleDouble", ".AppleDesktop", ".AppleDB", "Network Trash Folder", "Temporary Items"):
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
		if cached is None and lifetime:
			movieMaintenanceState.cacheDirectory(rootPath, records)
		self.fileSnapshots = {x[0].getPath(): x[1] for x in (records if cached is None else cached)} if lifetime else {}
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
		order = config.movielist.directoryOrder.value
		if order == "mixed":
			if self.sort_type == self.SHUFFLE:
				shuffle(self.list)
			else:
				key = self.buildBeginTimeSortKey if self.sort_type in (self.SORT_RECORDED, self.SORT_RECORDED_REVERSE) else self.buildGroupwiseSortkey if self.sort_type == self.SORT_GROUPWISE else self.buildAlphaNumericFlatSortKey
				if self.sort_type in (self.SORT_ALPHA_DATE_OLDEST_FIRST, self.SORT_ALPHAREV_DATE_NEWEST_FIRST):
					self.list.sort(key=lambda row: (self.buildAlphaNumericFlatSortKey(row)[1], row[2]), reverse=self.sort_type == self.SORT_ALPHAREV_DATE_NEWEST_FIRST)
				else:
					self.list.sort(key=lambda row: key(row)[1:], reverse=self.sort_type in (self.SORT_RECORDED_REVERSE, self.SORT_ALPHANUMERIC_REVERSE, self.SORT_ALPHANUMERIC_FLAT_REVERSE))
		elif order == "first":
			self.list.sort(key=lambda row: not bool(row[0].flags & eServiceReference.mustDescent))
		parents = [x for x in self.list if x[1] is None]
		self.list = parents + [x for x in self.list if x[1] is not None]
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
		self.firstFileEntry = next((index for index, row in enumerate(self.list) if not row[0].flags & eServiceReference.mustDescent), len(self.list))
		self.updateRecordingLengths()
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
			return 0, "", -x[2]
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
		if self.isGrid:
			if self.list:
				self.moveToIndex(min(len(self.list) - 1, self.getCurrentIndex() + 1))
		else:
			self.instance.moveSelection(self.instance.moveDown)

	def moveUp(self):
		if self.isGrid:
			self.moveToIndex(max(0, self.getCurrentIndex() - 1))
		else:
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
