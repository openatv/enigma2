from os import R_OK, access, listdir, lstat, sep
from os.path import basename, dirname, exists, isdir, islink, join, normpath, realpath, splitext
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
FILE_DIR_ICON = 5

SELECT_DIRECTORIES = 0
SELECT_FILES = 1
SELECT_ALL = 2

ICON_STORAGE = 0
ICON_PARENT = 1
ICON_CURRENT = 2

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
	".stream": "movie",
	".ts": "movie",
	".vob": "movie",
	".webm": "movie",
	".wmv": "movie",
	".wtv": "movie",
	# DVD image file types.
	".img": "iso",
	".iso": "iso",
	".nrg": "iso",
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
AUDIO_EXTENSIONS = frozenset((".mp3", ".mp2", ".m4a", ".m2a", ".mka", ".flac", ".ogg", ".oga", ".dts", ".wav", ".wave", ".wma", ".wv", ".ac3", ".aac", ".ape", ".alac", ".amr", ".au", ".mid"))
DVD_EXTENSIONS = frozenset((".iso", ".img", ".nrg"))
IMAGE_EXTENSIONS = frozenset((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".jpe", ".svg"))
MOVIE_EXTENSIONS = frozenset((".ts", ".stream", ".mp4", ".mkv", ".mpg", ".mpeg", ".mpe", ".avi", ".vob", ".ogv", ".ogm", ".asf", ".dat", ".divx", ".flv", ".m2ts", ".m4v", ".mov", ".mts", ".trp", ".webm", ".wmv", ".wtv", ".pva", ".rm", ".rmvb", ".3gp", ".3g2"))
PLAYLIST_EXTENSIONS = frozenset((".m3u", ".m3u8", ".e2pls", ".pls"))
RECORDING_EXTENSIONS = frozenset((".ap", ".cuts", ".eit", ".meta", ".sc"))
KNOWN_EXTENSIONS = MOVIE_EXTENSIONS.union(AUDIO_EXTENSIONS, DVD_EXTENSIONS, IMAGE_EXTENSIONS)


class FileListBase(MenuList):
	def __init__(self, selectedItems, directory, showDirectories=True, showFiles=True, showMountPoints=True, matchingPattern=None, useServiceRef=False, inhibitDirs=False, inhibitMounts=False, isTop=False, additionalExtensions=None, sortDirectories="0.0", sortFiles="0.0", directoriesFirst=True, showCurrentDirectory=False):
		self.extensionIcons = {}
		self.extensionIcons["lock_off"] = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/lock_off.png"))
		self.extensionIcons["lock_on"] = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/lock_on.png"))
		self.extensionIcons["link_arrow"] = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "extensions/link_arrow.png"))
		self.extensionIcons["link_error"] = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "extensions/link_error.png"))
		self.extensionIcons["storage"] = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "extensions/storage.png"))
		self.extensionIcons["parent"] = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "extensions/parent.png"))
		self.extensionIcons["current"] = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "extensions/current.png"))
		self.extensionIcons["directory"] = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "extensions/directory.png"))
		self.extensionIcons["file"] = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "extensions/file.png"))
		for icon in set(EXTENSIONS.values()):
			self.extensionIcons[icon] = LoadPixmap(resolveFilename(SCOPE_GUISKIN, f"extensions/{icon}.png"))
		if self.extensionIcons["storage"] is None:
			self.extensionIcons["storage"] = self.extensionIcons["directory"]
		if self.extensionIcons["parent"] is None:
			self.extensionIcons["parent"] = self.extensionIcons["directory"]
		if self.extensionIcons["current"] is None:
			self.extensionIcons["current"] = self.extensionIcons["directory"]
		self.fileList = []
		MenuList.__init__(self, self.fileList, content=eListboxPythonMultiContent)
		self.selectedItems = selectedItems
		self.showDirectories = showDirectories
		self.showFiles = showFiles
		self.showMountPoints = showMountPoints
		self.matchingPattern = compile(matchingPattern) if matchingPattern else None  # Example: To match .nfi and .ts files use "^.*\.(nfi|ts)$".
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
		self.previousDirectory = None
		self.serviceHandler = eServiceCenter.getInstance()
		if self.multiSelect:
			self.setMultiSelectMode()
		else:
			self.setSingleSelectMode()
		self.refreshMountPoints()
		self.changeDir(directory, directory)

	def execBegin(self):
		harddiskmanager.on_partition_list_change.append(self.partitionListChanged)

	def execEnd(self):
		harddiskmanager.on_partition_list_change.remove(self.partitionListChanged)

	def partitionListChanged(self, action, device):
		self.refreshMountPoints()
		if self.currentDirectory is None:
			self.refresh()

	def refreshMountPoints(self):
		self.mountPoints = [join(x.mountpoint, "") for x in harddiskmanager.getMountedPartitions()]
		self.mountPoints.sort(reverse=True)

	def setSingleSelectMode(self):
		self.multiSelect = False
		font = fonts.get("FileList", ("Regular", 20, 25))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])
		self.itemHeight = font[2]
		self.lockX, self.lockY, self.lockW, self.lockH = (0, 0, 0, 0)
		self.iconX, self.iconY, self.iconW, self.iconH = parameters.get("FileListIcon", (15, 0, self.itemHeight, self.itemHeight - 4))
		self.nameX, self.nameY, self.nameW, self.nameH = parameters.get("FileListName", (25 + self.iconW, 0, 900, self.itemHeight))
		self.refresh()

	def setMultiSelectMode(self):
		self.multiSelect = True
		font = fonts.get("FileListMulti", ("Regular", 20, 25))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])
		self.itemHeight = font[2]
		self.lockX, self.lockY, self.lockW, self.lockH = parameters.get("FileListMultiLock", (15, 0, self.itemHeight, self.itemHeight - 4))
		self.iconX, self.iconY, self.iconW, self.iconH = parameters.get("FileListMultiIcon", (25 + self.lockW, 0, self.itemHeight, self.itemHeight - 4))
		self.nameX, self.nameY, self.nameW, self.nameH = parameters.get("FileListMultiName", (35 + self.lockW + self.iconW, 0, 900, self.itemHeight))
		self.refresh()

	def changeDir(self, directory, select=None):
		def buildDirectoryList():
			if directory and not self.isTop:
				mountPoint = normpath(self.getMountPoint(directory)) if islink(directory) else normpath(self.getMountPointLink(directory))
				if self.showMountPoints and directory == mountPoint:
					self.fileList.append(self.fileListComponent(name=f"<{_("List of Storage Devices")}>", path=None, isDir=True, isLink=False, selected=None, dirIcon=ICON_STORAGE))
				if self.showCurrentDirectory:
					self.fileList.append(self.fileListComponent(name=f"<{_("Current Directory")}>", path=join(directory, ""), isDir=True, isLink=islink(directory), selected=None, dirIcon=ICON_CURRENT))
				parent = dirname(directory)
				inside = mountPoint != directory if islink(directory) else parent.startswith(mountPoint)
				if directory != parent and inside and not (self.inhibitMounts and self.getMountPoint(directory) in self.inhibitMounts):
					self.fileList.append(self.fileListComponent(name=f"<{_("Parent Directory")}>", path=join(parent, ""), isDir=True, isLink=islink(parent), selected=None, dirIcon=ICON_PARENT))
				# print(f"[FileList] changeDir DEBUG: mountPointLink='{normpath(self.getMountPointLink(directory))}', mountPoint='{normpath(self.getMountPoint(directory))}', directory='{directory}', parent='{parent}'.")
			for name, path, isDir, isLink in directories:
				if not (self.inhibitMounts and self.getMountPoint(path) in self.inhibitMounts) and not self.inParentDirs(path, self.inhibitDirs):
					selected = (path in self.selectedItems or normpath(path) in self.selectedItems) if self.multiSelect else None
					self.fileList.append(self.fileListComponent(name=name, path=path, isDir=isDir, isLink=isLink, selected=selected, dirIcon=None))

		self.fileList = []
		directories = []
		files = []
		self.currentDirectory = join(directory, "") if directory else directory
		if directory:
			directory = normpath(directory)
		if directory is None and self.showMountPoints:  # Present available mount points.
			seenMountPoints = []  # TO DO: Fix Hardisk.py to remove duplicated mount points!
			for partition in harddiskmanager.getMountedPartitions():
				path = normpath(partition.mountpoint)
				if path in seenMountPoints:  # TO DO: Fix Hardisk.py to remove duplicated mount points!
					continue
				seenMountPoints.append(path)
				if path not in self.inhibitMounts and not self.inParentDirs(path, self.inhibitDirs):
					selected = False if self.multiSelect else None
					self.fileList.append(self.fileListComponent(name=partition.description, path=join(path, ""), isDir=True, isLink=False, selected=selected, dirIcon=None))
		elif self.useServiceRef and directory:
			# Don't use "eServiceReference(string)" constructor as it doesn't allow ":" in the directory name.
			root = eServiceReference(eServiceReference.idFile, eServiceReference.noFlags, eServiceReferenceFS.directory)
			root.setPath(join(directory, ""))
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
			if directory and isdir(directory):
				try:
					items = listdir(directory)
					for item in items:
						path = join(directory, item)
						if isdir(path):
							directories.append((item, join(path, ""), True, islink(path)))
						else:
							files.append((item, path, False, islink(path)))
					directories = self.sortList(directories, self.sortDirectories)
					files = self.sortList(files, self.sortFiles)
				except OSError as err:
					print(f"FileList] Error {err.errno}: Unable to list directory contents of '{directory}'!  ({err.strerror})")
		if self.showDirectories and self.directoriesFirst:
			buildDirectoryList()
		if self.showFiles:
			for name, path, isDir, isLink in files:
				if (self.matchingPattern is None) or self.matchingPattern.search(path):
					selected = path in self.selectedItems if self.multiSelect else None
					if isinstance(name, eServiceReference):
						self.fileList.append(self.fileListComponent(name=basename(path), path=name, isDir=isDir, isLink=isLink, selected=selected, dirIcon=None))
					else:
						self.fileList.append(self.fileListComponent(name=name, path=path, isDir=isDir, isLink=isLink, selected=selected, dirIcon=None))
		if self.showDirectories and not self.directoriesFirst:
			buildDirectoryList()
		if self.showMountPoints and len(self.fileList) == 0:
			self.fileList.append(self.fileListComponent(name=_("Nothing connected and/or no files available!"), path=None, isDir=False, isLink=False, selected=None, dirIcon=None))
		self.setList(self.fileList)
		start = self.getCurrentIndex() if self.previousDirectory == self.currentDirectory else 0
		self.previousDirectory = self.currentDirectory
		if start and start > self.count():
			start = self.count() - 1
		if select:
			for index, entry in enumerate(self.fileList):
				path = entry[0][FILE_PATH]
				path = path.getPath() if isinstance(path, eServiceReference) else path
				if path == select:
					start = index
					break
		# We may need to reset the top of the viewport before setting the index.
		self.setCurrentIndex(start)

	def refresh(self, path=None):
		if path is None:
			path = self.getPath()
		self.changeDir(self.currentDirectory, path)

	def fileListComponent(self, name, path, isDir, isLink, selected, dirIcon):
		# print(f"[FileList] fileListComponent DEBUG: Name='{name}', Path='{path}', isDir={isDir}, isLink={isLink}, selected={selected}, dirIcon={dirIcon}.")
		res = [(path, isDir, isLink, selected, name, dirIcon)]
		if selected is not None and not self.getIsSpecialFolder(res[0]):
			icon = self.extensionIcons[f"lock_{'on' if selected else 'off'}"]
			if icon:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.lockX, self.lockY, self.lockW, self.lockH, icon, None, None, BT_SCALE | BT_VALIGN_CENTER))
		if isDir:
			icon = self.extensionIcons[{
				ICON_STORAGE: "storage",
				ICON_PARENT: "parent",
				ICON_CURRENT: "current"
			}.get(dirIcon, "directory")]
		else:
			if path is None:
				path = ""
			extension = splitext(path.getPath())[1].lower() if isinstance(path, eServiceReference) else splitext(path)[1].lower()
			icon = self.extensionIcons[EXTENSIONS.get(extension, "file")]
		if icon:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.iconX, self.iconY, self.iconW, self.iconH, icon, None, None, BT_SCALE | BT_VALIGN_CENTER))
			if isLink:
				icon = self.extensionIcons["link_arrow"] if exists(path) else self.extensionIcons["link_error"]
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.iconX, self.iconY, self.iconW, self.iconH, icon, None, None, BT_SCALE | BT_VALIGN_CENTER))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, self.nameX, self.nameY, self.nameW, self.nameH, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, name))
		return res

	def assignSelection(self, entry, type, selected):
		path = entry[0][FILE_PATH]
		isDir = entry[0][FILE_IS_DIR]
		dirIcon = entry[0][FILE_DIR_ICON]
		if (isDir is False and type == SELECT_DIRECTORIES) or (isDir is True and type == SELECT_FILES):
			selected = entry[0][FILE_SELECTED]
		if path and not self.getIsSpecialFolder(entry[0]):
			path = path if isDir else join(self.currentDirectory, path)
			if selected and path not in self.selectedItems:
				self.selectedItems.append(path)
			elif not selected and path in self.selectedItems:
				self.selectedItems.remove(path)
			entry = self.fileListComponent(name=entry[0][FILE_NAME], path=path, isDir=isDir, isLink=entry[0][FILE_IS_LINK], selected=selected, dirIcon=dirIcon)
		else:
			entry = self.fileListComponent(name=entry[0][FILE_NAME], path=path, isDir=isDir, isLink=entry[0][FILE_IS_LINK], selected=None, dirIcon=dirIcon)
		return entry

	def setSelection(self):
		if self.fileList:
			index = self.getCurrentIndex()
			self.fileList[index] = self.assignSelection(self.fileList[index], SELECT_ALL, True)
			self.setList(self.fileList)

	def setAllSelections(self, type=SELECT_ALL):
		newFileList = []
		for entry in self.fileList:
			newFileList.append(self.assignSelection(entry, type, True))
		self.fileList = newFileList
		self.setList(self.fileList)

	def clearSelection(self):
		if self.fileList:
			index = self.getCurrentIndex()
			self.fileList[index] = self.assignSelection(self.fileList[index], SELECT_ALL, False)
			self.setList(self.fileList)

	def clearAllSelections(self, type=SELECT_ALL):
		newFileList = []
		for entry in self.fileList:
			newFileList.append(self.assignSelection(entry, type, False))
		self.fileList = newFileList
		self.setList(self.fileList)

	def toggleSelection(self):
		if self.fileList:
			index = self.getCurrentIndex()
			entry = self.fileList[index]
			selected = not entry[0][FILE_SELECTED]
			self.fileList[index] = self.assignSelection(entry, SELECT_ALL, selected)
			self.setList(self.fileList)

	def toggleAllSelections(self, type=SELECT_ALL):
		newFileList = []
		for entry in self.fileList:
			selected = not entry[0][FILE_SELECTED]
			newFileList.append(self.assignSelection(entry, type, selected))
		self.fileList = newFileList
		self.setList(self.fileList)

	# Marker!
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

	def getIsSpecialFolder(self, selection=None):
		if not selection:
			selection = self.getSelection()
		return selection[FILE_DIR_ICON] in (ICON_STORAGE, ICON_PARENT, ICON_CURRENT) if selection else False

	def getFilename(self):  # Legacy method name for external code.
		return self.getPath()

	def getSelection(self):
		selection = self.getCurrent()
		return selection[0] if selection else None

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
		return join(last, "")

	def getMountpointLink(self, path):  # Legacy method name for external code.
		self.getMountPointLink(path)

	def getMountPoint(self, path):
		path = join(realpath(path), "")
		for mountPoint in self.mountPoints:
			if path.startswith(mountPoint):
				return mountPoint
		return "/"  # Return root if path not in mountPoints to prevent crashes with software MultiBoot.

	def getMountpoint(self, path):  # Legacy method name for external code.
		self.getMountPoint(path)

	def inParentDirs(self, path, parents):
		path = realpath(path)
		for parent in parents:
			if path.startswith(parent):
				return True
		return False

	def setSortBy(self, sortBy):
		# directory,files -> "0.0,0.0"
		# 0.0
		# | 0 - normal
		# | 1 - reverse
		# 0 - name
		# 1 - date
		# 2 - size (files only)
		self.sortDirectories, self.sortFiles = sortBy.split(",")

	def getSortBy(self):
		return f"{self.sortDirectories},{self.sortFiles}"

	def sortList(self, items, sortBy):
		sort, reverse = (int(x) for x in sortBy.split("."))
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

	def getCurrentDirectory(self):
		return self.currentDirectory

	def setCurrentDirectory(self, directory):
		self.currentDirectory = join(directory, "")

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

	def changeSelectionState(self):
		self.toggleSelection()

	def getSelectedItems(self):
		selectedItems = []
		for item in self.selectedItems:
			if exists(item):
				selectedItems.append(item)
		return selectedItems

	def getSelectedList(self):  # This method name is deprecated, please use getSelectedItems() instead.
		return self.getSelectedItems()


class FileList(FileListBase):
	def __init__(self, directory, showDirectories=True, showFiles=True, showMountpoints=True, matchingPattern=None, useServiceRef=False, inhibitDirs=False, inhibitMounts=False, isTop=False, additionalExtensions=None, sortDirs='0.0', sortFiles='0.0', firstDirs=True, showCurrentDirectory=False, enableWrapAround=False):
		self.multiSelect = False
		selectedItems = []
		FileListBase.__init__(self, selectedItems, directory, showMountPoints=showMountpoints, matchingPattern=matchingPattern, showDirectories=showDirectories, showFiles=showFiles, useServiceRef=useServiceRef, inhibitDirs=inhibitDirs, inhibitMounts=inhibitMounts, isTop=isTop, additionalExtensions=additionalExtensions, sortDirectories=sortDirs, sortFiles=sortFiles, directoriesFirst=firstDirs, showCurrentDirectory=showCurrentDirectory)


class FileListMultiSelect(FileListBase):
	def __init__(self, selectedItems, directory, showDirectories=True, showFiles=True, showMountpoints=True, matchingPattern=None, useServiceRef=False, inhibitDirs=False, inhibitMounts=False, isTop=False, additionalExtensions=None, sortDirs='0.0', sortFiles='0.0', firstDirs=True, showCurrentDirectory=False, enableWrapAround=False):
		self.multiSelect = True
		FileListBase.__init__(self, selectedItems, directory, showMountPoints=showMountpoints, matchingPattern=matchingPattern, showDirectories=showDirectories, showFiles=showFiles, useServiceRef=useServiceRef, inhibitDirs=inhibitDirs, inhibitMounts=inhibitMounts, isTop=isTop, additionalExtensions=additionalExtensions, sortDirectories=sortDirs, sortFiles=sortFiles, directoriesFirst=firstDirs, showCurrentDirectory=showCurrentDirectory)


class MultiFileSelectList(FileListMultiSelect):
	pass


def FileEntryComponent(name, absolute=None, isDir=False):  # This method is deprecated but currently in use by the FTPBrowser plugin.
	res = [(absolute, isDir)]
	x, y, w, h = parameters.get("FileListName", (35, 1, 470, 20))
	res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT, name))
	if isDir:
		png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "extensions/directory.png"))
	else:
		png = EXTENSIONS.get(splitext(name)[1].lower())
		if png:
			png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, f"extensions/{png}.png"))
	if png is not None:
		x, y, w, h = parameters.get("FileListIcon", (10, 2, 20, 20))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, x, y, w, h, png))
	return res
