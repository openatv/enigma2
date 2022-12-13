from os import R_OK, access, listdir, lstat, sep
from os.path import basename, dirname, exists, isdir, isfile, islink, join as pathjoin, normpath, realpath, splitext
from re import compile

from enigma import BT_SCALE, BT_VALIGN_CENTER, RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, eServiceCenter, eServiceReference, eServiceReferenceFS, gFont

from skin import fonts, parameters
from Components.Harddisk import harddiskmanager
from Components.MenuList import MenuList
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap

FILE_PATH = 0
FILE_IS_DIR = 1
FILE_IS_LINK = 2
FILE_SELECTED = 3
FILE_NAME = 4

EXTENSIONS = {
	# Music file types.
	".aac": "music",
	".ac3": "music",
	".alac": "music",
	".amr": "music",
	".ape": "music",
	".au": "music",
	".dts": "music",
	".flac": "music",
	".m2a": "music",
	".m4a": "music",
	".mid": "music",
	".mka": "music",
	".mp2": "music",
	".mp3": "music",
	".oga": "music",
	".ogg": "music",
	".wav": "music",
	".wave": "music",
	".wma": "music",
	".wv": "music",
	# Picture file types.
	".bmp": "picture",
	".gif": "picture",
	".jpe": "picture",
	".jpeg": "picture",
	".jpg": "picture",
	".mvi": "picture",
	".png": "picture",
	".svg": "picture",
	# Movie File types.
	".3g2": "movie",
	".3gp": "movie",
	".asf": "movie",
	".avi": "movie",
	".dat": "movie",
	".divx": "movie",
	".flv": "movie",
	".m2ts": "movie",
	".m4v": "movie",
	".mkv": "movie",
	".mov": "movie",
	".mp4": "movie",
	".mpe": "movie",
	".mpeg": "movie",
	".mpg": "movie",
	".mts": "movie",
	".ogm": "movie",
	".ogv": "movie",
	".pva": "movie",
	".rm": "movie",
	".rmvb": "movie",
	".ts": "movie",
	".vob": "movie",
	".webm": "movie",
	".wmv": "movie",
	".wtv": "movie",
	# DVD image file types.
	".img": "iso",
	".iso": "iso",
	# Playlist file types.
	".e2pls": "playlist",
	".m3u": "playlist",
	".m3u8": "playlist",
	".pls": "playlist",
	# Other file types.
	".7z": "7z",
	".bak": "txt",
	".bat": "txt",
	".bz2": "tar",
	".cfg": "cfg",
	".cmd": "txt",
	".conf": "cfg",
	".gz": "tar",
	".htm": "html",
	".html": "html",
	".ipk": "ipk",
	".log": "log",
	".lst": "lst",
	".meta": "txt",
	".nfo": "txt",
	".py": "py",
	".pyc": "pyc",
	".pyo": "pyc",
	".rar": "rar",
	".sh": "sh",
	".srt": "txt",
	".tar": "tar",
	".text": "txt",
	".tgz": "tar",
	".txt": "txt",
	".xml": "xml",
	".xz": "tar",
	".zip": "zip"
}

# Playable file extensions.
AUDIO_EXTENSIONS = frozenset((".mp3", ".mp2", ".m4a", ".m2a", ".flac", ".ogg", ".dts", ".wav", ".3g2", ".3gp", ".wave", ".wma"))
DVD_EXTENSIONS = frozenset((".iso", ".img"))
IMAGE_EXTENSIONS = frozenset((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".jpe"))
MOVIE_EXTENSIONS = frozenset((".ts", ".mp4", ".mkv", ".mpg", ".avi", ".vob", ".asf", ".dat", ".divx", ".flv", ".m2ts", ".m4v", ".mov", ".mts", ".trp", ".webm", ".wmv"))
PLAYLIST_EXTENSIONS = frozenset((".m3u", ".m3u8", ".e2pls", ".pls"))
RECORDING_EXTENSIONS = frozenset((".ap", ".cuts", ".eit", ".meta", ".sc"))
KNOWN_EXTENSIONS = MOVIE_EXTENSIONS.union(AUDIO_EXTENSIONS, DVD_EXTENSIONS, IMAGE_EXTENSIONS)

# RECORDING_EXTENSIONS = {  # DEBUG: Is this version of the definition used?
# 	"cuts": "movieparts",
# 	"meta": "movieparts",
# 	"ap": "movieparts",
# 	"sc": "movieparts",
# 	"eit": "movieparts"
# }


class FileListBase(MenuList):
	def __init__(self, selectedFiles, directory, showDirectories=True, showFiles=True, showMountPoints=True, matchingPattern=None, useServiceRef=False, inhibitDirs=False, inhibitMounts=False, isTop=False, additionalExtensions=None, sortDirectories="0.0", sortFiles="0.0", directoriesFirst=True, showCurrentDirectory=False):
		self.fileList = []
		MenuList.__init__(self, self.fileList, content=eListboxPythonMultiContent)
		self.selectedFiles = selectedFiles
		self.showDirectories = showDirectories
		self.showFiles = showFiles
		self.showMountPoints = showMountPoints
		self.matchingPattern = compile(matchingPattern) if matchingPattern else None  # Example: To match .nfi and .ts files use "^.*\.(nfi|ts)".
		self.useServiceRef = useServiceRef
		self.inhibitDirs = inhibitDirs or []
		self.inhibitMounts = inhibitMounts or []
		self.isTop = isTop
		self.additionalExtensions = additionalExtensions
		self.sortDirectories = sortDirectories
		self.sortFiles = sortFiles
		self.directoriesFirst = directoriesFirst
		self.showCurrentDirectory = showCurrentDirectory
		self.mountPoints = []
		self.currentDirectory = None
		# self.currentMountPoint = None
		self.serviceHandler = eServiceCenter.getInstance()
		self.refreshMountPoints()

	def execBegin(self):
		harddiskmanager.on_partition_list_change.append(self.partitionListChanged)

	def execEnd(self):
		harddiskmanager.on_partition_list_change.remove(self.partitionListChanged)

	def partitionListChanged(self, action, device):
		self.refreshMountPoints()
		if self.currentDirectory is None:
			self.refresh()

	def refreshMountPoints(self):
		self.mountPoints = [pathjoin(x.mountpoint, "") for x in harddiskmanager.getMountedPartitions()]
		self.mountPoints.sort(reverse=True)

	def refresh(self):
		self.changeDir(self.currentDirectory, self.getPath())

	def getServiceRef(self):
		selection = self.getSelection()
		return selection[FILE_PATH] if selection and isinstance(selection[FILE_PATH], eServiceReference) else None

	def getPath(self):
		selection = self.getSelection()
		if selection:
			return selection[FILE_PATH].getPath() if isinstance(selection[FILE_PATH], eServiceReference) else selection[FILE_PATH]
		return None

	def getName(self):
		selection = self.getSelection()
		return selection[FILE_NAME] if selection else None

	def getIsDir(self):
		selection = self.getSelection()
		return selection[FILE_IS_DIR] if selection else None

	def getIsLink(self):
		selection = self.getSelection()
		return selection[FILE_IS_LINK] if selection else None

	def getIsSelected(self):
		selection = self.getSelection()
		return selection[FILE_SELECTED] if selection else None

	def getFilename(self):  # Legacy method name for external code.
		return self.getPath()

	def getSelection(self):
		selection = self.getCurrent()
		return selection[0] if selection else None

	def changeDir(self, directory, select=None):
		def buildDirectoryList():
			if directory and not self.isTop:
				# if self.showMountPoints and pathjoin(directory, "") == self.currentMountPoint:
				# 	self.fileList.append(self.fileListComponent(name="<%s>" % _("List of Storage Devices"), path=None, isDir=True, isLink=False, selected=None))
				# elif (directory != sep) and not (self.inhibitMounts and self.getMountPoint(directory) in self.inhibitMounts):
				# 	if self.showCurrentDirectory:
				# 		self.fileList.append(self.fileListComponent(name="<%s>" % _("Current Directory"), path=pathjoin(directory, ""), isDir=True, isLink=islink(directory), selected=None))
				# 	parent = dirname(directory)
				# 	self.fileList.append(self.fileListComponent(name="<%s>" % _("Parent Directory"), path=pathjoin(parent, ""), isDir=True, isLink=islink(parent), selected=None))
				mountPoint = normpath(self.getMountPointLink(directory))
				if self.showMountPoints and directory == mountPoint:
					self.fileList.append(self.fileListComponent(name="<%s>" % _("List of Storage Devices"), path=None, isDir=True, isLink=False, selected=None))
				if self.showCurrentDirectory:
					self.fileList.append(self.fileListComponent(name="<%s>" % _("Current Directory"), path=pathjoin(directory, ""), isDir=True, isLink=islink(directory), selected=None))
				parent = dirname(directory)
				if directory != parent and parent.startswith(mountPoint) and not (self.inhibitMounts and self.getMountPoint(directory) in self.inhibitMounts):
					self.fileList.append(self.fileListComponent(name="<%s>" % _("Parent Directory"), path=pathjoin(parent, ""), isDir=True, isLink=islink(parent), selected=None))
				# print("[FileList] changeDir DEBUG: mountPoint='%s', mountPointLink='%s', directory='%s', parent='%s'." % (normpath(self.getMountPointLink(directory)), mountPoint, directory, parent))
			for name, path, isDir, isLink in directories:
				if not (self.inhibitMounts and self.getMountPoint(path) in self.inhibitMounts) and not self.inParentDirs(path, self.inhibitDirs):
					selected = (path in self.selectedFiles or normpath(path) in self.selectedFiles) if self.multiSelect else None
					self.fileList.append(self.fileListComponent(name=name, path=path, isDir=isDir, isLink=isLink, selected=selected))

		self.fileList = []
		directories = []
		files = []
		# if self.currentDirectory is None:  # If we are just entering from the list of mount points.
		# 	self.currentMountPoint = self.getMountPointLink(directory) if directory and self.showMountPoints else None
		# 	print("[FileList] changeDir DEBUG: The current mount point is '%s'." % self.currentMountPoint)
		self.currentDirectory = pathjoin(directory, "") if directory else directory
		if directory:
			directory = normpath(directory)
		if directory is None and self.showMountPoints:  # Present available mount points.
			seenMountPoints = []  # TO DO: Fix Hardisk.py to remove duplicated mount points!
			for partition in harddiskmanager.getMountedPartitions():
				# print("[FileList] DEBUG: Partition='%s'." % partition)
				path = normpath(partition.mountpoint)
				if path in seenMountPoints:  # TO DO: Fix Hardisk.py to remove duplicated mount points!
					continue
				seenMountPoints.append(path)
				if path not in self.inhibitMounts and not self.inParentDirs(path, self.inhibitDirs):
					# print("[FileList] DEBUG: Path='%s'." % path)
					selected = False if self.multiSelect else None
					self.fileList.append(self.fileListComponent(name=partition.description, path=pathjoin(path, ""), isDir=True, isLink=False, selected=selected))
		elif self.useServiceRef:
			# Don't use "eServiceReference(string)" constructor as it doesn't allow ":" in the directory name.
			root = eServiceReference(eServiceReference.idFile, eServiceReference.noFlags, eServiceReferenceFS.directory)
			root.setPath(pathjoin(directory, ""))
			if self.additionalExtensions:
				root.setName(self.additionalExtensions)
			serviceList = self.serviceHandler.list(root)
			while True:
				service = serviceList.getNext()
				if not service.valid():
					del serviceList
					break
				path = normpath(service.getPath())
				if service.flags & service.mustDescent:
					directories.append((basename(path), service.getPath(), True, islink(path)))
				else:
					files.append((service, service.getPath(), False, islink(path)))
			directories = self.sortList(directories, self.sortDirectories)
			files = self.sortList(files, self.sortFiles)
		else:
			if isdir(directory):
				try:
					items = listdir(directory)
					for item in items:
						path = pathjoin(directory, item)
						if isdir(path):
							directories.append((item, pathjoin(path, ""), True, islink(path)))
						else:
							files.append((item, path, False, islink(path)))
					directories = self.sortList(directories, self.sortDirectories)
					files = self.sortList(files, self.sortFiles)
				except OSError as err:
					print("FileList] Error %d: Unable to list directory contents of '%s'!  (%s)" % (err.errno, directory, err.strerror))
		if self.showDirectories and self.directoriesFirst:
			buildDirectoryList()
		if self.showFiles:
			for name, path, isDir, isLink in files:
				if (self.matchingPattern is None) or self.matchingPattern.search(path):
					selected = path in self.selectedFiles if self.multiSelect else None
					if isinstance(name, eServiceReference):
						self.fileList.append(self.fileListComponent(name=basename(path), path=name, isDir=isDir, isLink=isLink, selected=selected))
					else:
						self.fileList.append(self.fileListComponent(name=name, path=path, isDir=isDir, isLink=isLink, selected=selected))
		if self.showDirectories and not self.directoriesFirst:
			buildDirectoryList()
		if self.showMountPoints and len(self.fileList) == 0:
			self.fileList.append(self.fileListComponent(name=_("Nothing connected"), path=None, isDir=False, isLink=False, selected=None))
		self.setList(self.fileList)
		start = 0
		if select:
			# print("[FileList] changeDir DEBUG: Selecting '%s'." % select)
			for index, entry in enumerate(self.fileList):
				path = entry[0][FILE_PATH]
				path = path.getPath() if isinstance(path, eServiceReference) else path
				# print("[FileList] changeDir DEBUG: Trying '%s'." % path)
				if path == select:
					# print("[FileList] changeDir DEBUG: Found select='%s' as index %d." % (select, index))
					start = index
					break
		self.moveToIndex(start)

	def getMountPointLink(self, path):
		if realpath(path) == path:
			return self.getMountPoint(path)
		path = normpath(path)
		mountPoint = self.getMountPoint(path)
		last = path
		path = dirname(path)
		while last != sep and mountPoint == self.getMountPoint(path):
			last = path
			path = dirname(path)
		return pathjoin(last, "")

	def getMountpointLink(self, path):  # Legacy method name for external code.
		self.getMountPointLink(path)

	def getMountPoint(self, path):
		path = pathjoin(realpath(path), "")
		for mountPoint in self.mountPoints:
			if path.startswith(mountPoint):
				return mountPoint
		return "/"  # Return root if path not in mountPoints to prevent crashes

	def getMountpoint(self, path):  # Legacy method name for external code.
		self.getMountPoint(path)

	def inParentDirs(self, path, parents):
		path = realpath(path)
		for parent in parents:
			if path.startswith(parent):
				return True
		return False

	def sortList(self, items, sortBy):
		sort, reverse = [int(x) for x in sortBy.split(".")]
		itemList = []
		for name, path, isDir, isLink in items:
			if access(path, R_OK):
				status = lstat(path)
				date = status.st_ctime
				size = status.st_size
			else:
				date = 0
				size = 0
			itemList.append((name, date, size, path, isDir, isLink))
		itemList = sorted(itemList, key=lambda x: x[sort], reverse=reverse)
		items = []
		for name, date, size, path, isDir, isLink in itemList:
			items.append((name, path, isDir, isLink))
		return items

	def fileListComponent(self, name, path, isDir, isLink, selected):
		# print("[FileList] fileListComponent DEBUG: Name='%s', Path='%s', isDir=%s, isLink=%s, selected=%s." % (name, path, isDir, isLink, selected))
		if selected is None:
			res = [(path, isDir, isLink, None, name)]
		else:
			res = [(path, isDir, isLink, selected, name)]
			if not name.startswith("<"):
				icon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/lock_%s.png" % ("on" if selected else "off")), cached=True)
				if icon:
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.lockX, self.lockY, self.lockW, self.lockH, icon, None, None, BT_SCALE | BT_VALIGN_CENTER))
		linkIcon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "extensions/link-arrow.png"), cached=True) if isLink else None
		if isDir:
			if isLink and linkIcon is None:
				icon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "extensions/link.png"), cached=True)
			else:
				icon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "extensions/%s.png" % ("back" if name == ".." else "directory")), cached=True)
		else:
			extension = splitext(path.getPath())[1].lower() if isinstance(path, eServiceReference) else splitext(path)[1].lower()
			icon = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "extensions/%s.png" % EXTENSIONS.get(extension, "file")), cached=True)
		if icon:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.iconX, self.iconY, self.iconW, self.iconH, icon, None, None, BT_SCALE | BT_VALIGN_CENTER))
			if linkIcon:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.iconX, self.iconY, self.iconW, self.iconH, linkIcon, None, None, BT_SCALE | BT_VALIGN_CENTER))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, self.nameX, self.nameY, self.nameW, self.nameH, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, name))
		return res

	def getCurrentDirectory(self):
		return self.currentDirectory

	def setCurrentDirectory(self, directory):
		self.currentDirectory = pathjoin(directory, "")

	current_directory = property(getCurrentDirectory, setCurrentDirectory)  # This variable is deprecated but currently in use by the FTPBrowser plugin.

	def getFileList(self):
		return self.fileList

	def getCurrentEvent(self):
		selection = self.getSelection()
		return None if not selection or selection[FILE_IS_DIR] else self.serviceHandler.info(selection[FILE_PATH]).getEvent(selection[FILE_PATH])

	def canDescend(self):
		selection = self.getSelection()
		return selection and selection[FILE_IS_DIR]

	def canDescent(self):  # Legacy method name for external code.
		return self.canDescend()

	def descend(self):
		selection = self.getSelection()
		if selection:
			self.changeDir(selection[FILE_PATH], select=self.currentDirectory)

	def descent(self):  # Legacy method name for external code.
		return self.descend()

	def setSortBy(self, sortBy, setDir=False):
		# 0.0
		# | 0 - normal
		# | 1 - reverse
		# 0 - name
		# 1 - date
		# 2 - size (files only)
		if setDir:
			self.sortDirectories = sortBy
		else:
			self.sortFiles = sortBy

	def getSortBy(self):
		return "%s,%s" % (self.sortDirectories, self.sortFiles)


class FileList(FileListBase):
	def __init__(self, directory, showDirectories=True, showFiles=True, showMountpoints=True, matchingPattern=None, useServiceRef=False, inhibitDirs=False, inhibitMounts=False, isTop=False, additionalExtensions=None, sortDirs='0.0', sortFiles='0.0', firstDirs=True, showCurrentDirectory=False, enableWrapAround=False):
		# print("[FileList] FileList DEBUG: Initial directory='%s'." % directory)
		self.multiSelect = False
		selectedFiles = []
		FileListBase.__init__(self, selectedFiles, directory, showMountPoints=showMountpoints, matchingPattern=matchingPattern, showDirectories=showDirectories, showFiles=showFiles, useServiceRef=useServiceRef, inhibitDirs=inhibitDirs, inhibitMounts=inhibitMounts, isTop=isTop, additionalExtensions=additionalExtensions, sortDirectories=sortDirs, sortFiles=sortFiles, directoriesFirst=firstDirs, showCurrentDirectory=showCurrentDirectory)
		font = fonts.get("FileList", ("Regular", 20, 25))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])
		self.itemHeight = font[2]
		self.lockX, self.lockY, self.lockW, self.lockH = (0, 0, 0, 0)
		self.iconX, self.iconY, self.iconW, self.iconH = parameters.get("FileListIcon", (15, 0, self.itemHeight, self.itemHeight - 4))
		self.nameX, self.nameY, self.nameW, self.nameH = parameters.get("FileListName", (25 + self.iconW, 0, 900, self.itemHeight))
		self.changeDir(directory, directory)


class FileListMultiSelect(FileListBase):
	def __init__(self, selectedFiles, directory, showDirectories=True, showFiles=True, showMountpoints=True, matchingPattern=None, useServiceRef=False, inhibitDirs=False, inhibitMounts=False, isTop=False, additionalExtensions=None, sortDirs='0.0', sortFiles='0.0', firstDirs=True, showCurrentDirectory=False, enableWrapAround=False):
		# print("[FileList] FileListMultiSelect DEBUG: Initial directory='%s'." % directory)
		self.multiSelect = True
		# self.onSelectionChanged = []
		FileListBase.__init__(self, selectedFiles, directory, showMountPoints=showMountpoints, matchingPattern=matchingPattern, showDirectories=showDirectories, showFiles=showFiles, useServiceRef=useServiceRef, inhibitDirs=inhibitDirs, inhibitMounts=inhibitMounts, isTop=isTop, additionalExtensions=additionalExtensions, sortDirectories=sortDirs, sortFiles=sortFiles, directoriesFirst=firstDirs, showCurrentDirectory=showCurrentDirectory)
		font = fonts.get("FileListMulti", ("Regular", 20, 25))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])
		self.itemHeight = font[2]
		self.lockX, self.lockY, self.lockW, self.lockH = parameters.get("FileListMultiLock", (15, 0, self.itemHeight, self.itemHeight - 4))
		self.iconX, self.iconY, self.iconW, self.iconH = parameters.get("FileListMultiIcon", (25 + self.lockW, 0, self.itemHeight, self.itemHeight - 4))
		self.nameX, self.nameY, self.nameW, self.nameH = parameters.get("FileListMultiName", (35 + self.lockW + self.iconW, 0, 900, self.itemHeight))
		self.changeDir(directory, directory)

	# def selectionChanged(self):
	# 	for callback in self.onSelectionChanged:
	# 		callback()

	def setSelection(self):
		if self.fileList:
			index = self.getSelectionIndex()
			entry = self.fileList[index]
			if not entry[0][FILE_NAME].startswith("<"):
				path = entry[0][FILE_PATH] if entry[0][FILE_IS_DIR] else pathjoin(self.currentDirectory, entry[0][FILE_PATH])
				# normPath = normpath(path)
				if not entry[0][FILE_SELECTED]:
					# if (path not in self.selectedFiles) and (normPath not in self.selectedFiles):
					if path not in self.selectedFiles:
						self.selectedFiles.append(path)
					self.fileList[index] = self.fileListComponent(name=entry[0][FILE_NAME], path=entry[0][FILE_PATH], isDir=entry[0][FILE_IS_DIR], isLink=entry[0][FILE_IS_LINK], selected=True)
					self.setList(self.fileList)

	def clearSelection(self):
		if self.fileList:
			index = self.getSelectionIndex()
			entry = self.fileList[index]
			if not entry[0][FILE_NAME].startswith("<"):
				path = entry[0][FILE_PATH] if entry[0][FILE_IS_DIR] else pathjoin(self.currentDirectory, entry[0][FILE_PATH])
				# normPath = normpath(path)
				if entry[0][FILE_SELECTED]:
					if path in self.selectedFiles:
						self.selectedFiles.remove(path)
					# elif normPath in self.selectedFiles:
					# 	self.selectedFiles.remove(normPath)
					else:
						print("[FileList] Error: Can't remove '%s'!" % path)
					self.fileList[index] = self.fileListComponent(name=entry[0][FILE_NAME], path=entry[0][FILE_PATH], isDir=entry[0][FILE_IS_DIR], isLink=entry[0][FILE_IS_LINK], selected=False)
					self.setList(self.fileList)

	def toggleSelection(self):
		if self.fileList:
			index = self.getSelectionIndex()
			entry = self.fileList[index]
			if not entry[0][FILE_NAME].startswith("<"):
				path = entry[0][FILE_PATH] if entry[0][FILE_IS_DIR] else pathjoin(self.currentDirectory, entry[0][FILE_PATH])
				# normPath = normpath(path)
				if entry[0][FILE_SELECTED]:
					selectState = False
					if path in self.selectedFiles:
						self.selectedFiles.remove(path)
					# elif normPath in self.selectedFiles:
					# 	self.selectedFiles.remove(normPath)
					else:
						print("[FileList] Error: Can't remove '%s'!" % path)
				else:
					selectState = True
					# if (path not in self.selectedFiles) and (normPath not in self.selectedFiles):
					if path not in self.selectedFiles:
						self.selectedFiles.append(path)
				self.fileList[index] = self.fileListComponent(name=entry[0][FILE_NAME], path=entry[0][FILE_PATH], isDir=entry[0][FILE_IS_DIR], isLink=entry[0][FILE_IS_LINK], selected=selectState)
				self.setList(self.fileList)

	def changeSelectionState(self):
		self.toggleSelection()

	def getSelectedList(self):
		selectedList = []
		for file in self.selectedFiles:
			if exists(file):
				selectedList.append(file)
		return selectedList


class MultiFileSelectList(FileListMultiSelect):
	pass


def FileEntryComponent(name, absolute=None, isDir=False):  # This method is deprecated but currently in use by the FTPBrowser plugin.
	res = [(absolute, isDir)]
	x, y, w, h = parameters.get("FileListName", (35, 1, 470, 20))
	res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT, name))
	if isDir:
		png = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "extensions/directory.png"))
	else:
		extension = splitext(name)[1].lower()
		png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "extensions/%s.png" % EXTENSIONS[extension])) if extension in EXTENSIONS else None
	if png is not None:
		x, y, w, h = parameters.get("FileListIcon", (10, 2, 20, 20))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, x, y, w, h, png))
	return res
