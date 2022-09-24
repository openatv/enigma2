from os import listdir, sep
from os.path import basename, dirname, isdir, join as pathjoin, normpath, realpath, exists
from re import compile

from enigma import RT_HALIGN_LEFT, eListboxPythonMultiContent, eServiceCenter, eServiceReference, eServiceReferenceFS, gFont

from skin import fonts, parameters
from Components.Harddisk import harddiskmanager
from Components.MenuList import MenuList
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap

EXTENSIONS = {
	# Music file types.
	"aac": "music",
	"ac3": "music",
	"alac": "music",
	"amr": "music",
	"ape": "music",
	"au": "music",
	"dts": "music",
	"flac": "music",
	"m2a": "music",
	"m4a": "music",
	"mid": "music",
	"mka": "music",
	"mp2": "music",
	"mp3": "music",
	"oga": "music",
	"ogg": "music",
	"wav": "music",
	"wave": "music",
	"wma": "music",
	"wv": "music",
	# Picture file types.
	"bmp": "picture",
	"gif": "picture",
	"jpe": "picture",
	"jpeg": "picture",
	"jpg": "picture",
	"mvi": "picture",
	"png": "picture",
	"svg": "picture",
	# Movie File types.
	"3g2": "movie",
	"3gp": "movie",
	"asf": "movie",
	"avi": "movie",
	"dat": "movie",
	"divx": "movie",
	"flv": "movie",
	"m2ts": "movie",
	"m4v": "movie",
	"mkv": "movie",
	"mov": "movie",
	"mp4": "movie",
	"mpe": "movie",
	"mpeg": "movie",
	"mpg": "movie",
	"mts": "movie",
	"ogm": "movie",
	"ogv": "movie",
	"pva": "movie",
	"rm": "movie",
	"rmvb": "movie",
	"ts": "movie",
	"vob": "movie",
	"webm": "movie",
	"wmv": "movie",
	"wtv": "movie",
	# Other file types.
	"cfg": "cfg",
	"conf": "cfg",
	"gz": "gz",
	"htm": "html",
	"html": "html",
	"ipk": "ipk",
	"iso": "iso",
	"log": "log",
	"lst": "lst",
	"py": "py",
	"pyc": "pyc",
	"pyo": "pyc",
	"rar": "rar",
	"sh": "sh",
	"tar": "tar",
	"text": "txt",
	"tgz": "tar",
	"txt": "txt",
	"xml": "xml",
	"zip": "zip"
}


def FileEntryComponent(name, absolute=None, isDir=False):
	res = [(absolute, isDir)]
	x, y, w, h = parameters.get("FileListName", (35, 1, 470, 20))
	res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT, name))
	if isDir:
		png = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "extensions/directory.png"))
	else:
		extension = name.split(".")
		extension = extension[-1].lower()
		png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "extensions/%s.png" % EXTENSIONS[extension])) if extension in EXTENSIONS else None
	if png is not None:
		x, y, w, h = parameters.get("FileListIcon", (10, 2, 20, 20))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, x, y, w, h, png))
	return res


class FileList(MenuList):
	def __init__(self, directory, showDirectories=True, showFiles=True, showMountpoints=True, matchingPattern=None, useServiceRef=False, inhibitDirs=False, inhibitMounts=False, isTop=False, enableWrapAround=False, additionalExtensions=None, showCurrentDirectory=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.additional_extensions = additionalExtensions
		self.mountpoints = []
		self.current_directory = None
		self.current_mountpoint = None
		self.useServiceRef = useServiceRef
		self.showDirectories = showDirectories
		self.showMountpoints = showMountpoints
		self.showFiles = showFiles
		self.isTop = isTop
		self.matchingPattern = compile(matchingPattern) if matchingPattern else None  # Example: Matching .nfi and .ts files: "^.*\.(nfi|ts)".
		self.inhibitDirs = inhibitDirs or []
		self.inhibitMounts = inhibitMounts or []
		self.showCurrentDirectory = showCurrentDirectory
		self.refreshMountpoints()
		self.changeDir(directory)
		font = fonts.get("FileList", ("Regular", 18, 23))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])
		self.serviceHandler = eServiceCenter.getInstance()

	def refreshMountpoints(self):
		self.mountpoints = [pathjoin(p.mountpoint, "") for p in harddiskmanager.getMountedPartitions()]
		self.mountpoints.sort(reverse=True)

	def getMountpoint(self, file):
		file = pathjoin(realpath(file), "")
		for mount in self.mountpoints:
			if file.startswith(mount):
				return mount
		return False

	def getMountpointLink(self, file):
		if realpath(file) == file:
			return self.getMountpoint(file)
		else:
			if file[-1] == sep:
				file = file[:-1]
			mp = self.getMountpoint(file)
			last = file
			file = dirname(file)
			while last != sep and mp == self.getMountpoint(file):
				last = file
				file = dirname(file)
			return pathjoin(last, "")

	def getSelection(self):
		if self.l.getCurrentSelection() is None:
			return None
		return self.l.getCurrentSelection()[0]

	def getCurrentEvent(self):
		event = self.l.getCurrentSelection()
		return None if not event or event[0][1] else self.serviceHandler.info(event[0][0]).getEvent(event[0][0])

	def getFileList(self):
		return self.list

	def inParentDirs(self, dir, parents):
		dir = realpath(dir)
		for parent in parents:
			if dir.startswith(parent):
				return True
		return False

	def changeDir(self, directory, select=None):
		self.list = []
		if self.current_directory is None:  # If we are just entering from the list of mount points.
			self.current_mountpoint = self.getMountpointLink(directory) if directory and self.showMountpoints else None
		self.current_directory = directory
		directories = []
		files = []
		if directory is None and self.showMountpoints:  # Present available mount points.
			for p in harddiskmanager.getMountedPartitions():
				path = pathjoin(p.mountpoint, "")
				if path not in self.inhibitMounts and not self.inParentDirs(path, self.inhibitDirs):
					self.list.append(FileEntryComponent(name=p.description, absolute=path, isDir=True))
			files = []
			directories = []
		elif directory is None:
			files = []
			directories = []
		elif self.useServiceRef:
			# We should not use the 'eServiceReference(string)' constructor because it doesn't allow ':' in the directory name.
			root = eServiceReference(eServiceReference.idFile, eServiceReference.noFlags, eServiceReferenceFS.directory)
			root.setPath(directory)
			if self.additional_extensions:
				root.setName(self.additional_extensions)
			serviceHandler = eServiceCenter.getInstance()
			_list = serviceHandler.list(root)
			while True:
				service = _list.getNext()
				if not service.valid():
					del _list
					break
				if service.flags & service.mustDescent:
					directories.append(service.getPath())
				else:
					files.append(service)
			directories.sort()
			files.sort()
		else:
			if isdir(directory):
				try:
					files = listdir(directory)
				except OSError:
					files = []
				files.sort()
				tmpfiles = files[:]
				for file in tmpfiles:
					if isdir(pathjoin(directory, file)):
						directories.append(pathjoin(directory, file, ""))
						files.remove(file)
		if self.showDirectories:
			if directory is not None and not self.isTop:
				if directory == self.current_mountpoint and self.showMountpoints:
					self.list.append(FileEntryComponent(name="<%s>" % _("List of storage devices"), absolute=None, isDir=True))
				elif (directory != sep) and not (self.inhibitMounts and self.getMountpoint(directory) in self.inhibitMounts):
					self.list.append(FileEntryComponent(name="<%s>" % _("Parent directory"), absolute=pathjoin(sep.join(directory.split(sep)[:-2]), ""), isDir=True))
				if self.showCurrentDirectory:
					self.list.append(FileEntryComponent(name="<%s>" % _("Current directory"), absolute=directory, isDir=True))
			for dir in directories:
				if not (self.inhibitMounts and self.getMountpoint(dir) in self.inhibitMounts) and not self.inParentDirs(dir, self.inhibitDirs):
					name = dir.split(sep)[-2]
					self.list.append(FileEntryComponent(name=name, absolute=dir, isDir=True))
		if self.showFiles:
			for file in files:
				if self.useServiceRef:
					path = file.getPath()
					name = path.split(sep)[-1]
				else:
					path = pathjoin(directory, file)
					name = file
				if (self.matchingPattern is None) or self.matchingPattern.search(path):
					self.list.append(FileEntryComponent(name=name, absolute=file, isDir=False))
		if self.showMountpoints and len(self.list) == 0:
			self.list.append(FileEntryComponent(name=_("Nothing connected"), absolute=None, isDir=False))
		self.l.setList(self.list)
		if select is not None:
			self.moveToIndex(0)
			for index, item in enumerate(self.list):
				path = item[0][0]
				if isinstance(path, eServiceReference):
					path = path.getPath()
				if path == select:
					self.moveToIndex(index)

	def getCurrentDirectory(self):
		return self.current_directory

	def canDescent(self):
		if self.getSelection() is None:
			return False
		return self.getSelection()[1]

	def descent(self):
		if self.getSelection() is None:
			return
		self.changeDir(self.getSelection()[0], select=self.current_directory)

	def getFilename(self):
		if self.getSelection() is None:
			return None
		item = self.getSelection()[0]
		if isinstance(item, eServiceReference):
			item = item.getPath()
		return item

	def getServiceRef(self):
		if self.getSelection() is None:
			return None
		item = self.getSelection()[0]
		if isinstance(item, eServiceReference):
			return item
		return None

	def execBegin(self):
		harddiskmanager.on_partition_list_change.append(self.partitionListChanged)

	def execEnd(self):
		harddiskmanager.on_partition_list_change.remove(self.partitionListChanged)

	def refresh(self):
		self.changeDir(self.current_directory, self.getFilename())

	def partitionListChanged(self, action, device):
		self.refreshMountpoints()
		if self.current_directory is None:
			self.refresh()


def MultiFileSelectEntryComponent(name, absolute=None, isDir=False, selected=False):
	res = [(absolute, isDir, selected, name)]
	x, y, w, h = parameters.get("FileListMultiName", (55, 0, 470, 25))
	res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT, name))
	if isDir:
		png = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "extensions/directory.png"))
	else:
		extension = name.split(".")
		extension = extension[-1].lower()
		png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "extensions/%s.png" % EXTENSIONS[extension])) if extension in EXTENSIONS else None
	if png is not None:
		x, y, w, h = parameters.get("FileListMultiIcon", (30, 2, 20, 20))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, x, y, w, h, png))
	if not name.startswith("<"):
		icon = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/lock_on.png" if selected else "icons/lock_off.png"))
		x, y, w, h = parameters.get("FileListMultiLock", (2, 0, 25, 25))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, x, y, w, h, icon))
	return res


class MultiFileSelectList(FileList):
	def __init__(self, preselectedFiles, directory, showMountpoints=False, matchingPattern=None, showDirectories=True, showFiles=True, useServiceRef=False, inhibitDirs=False, inhibitMounts=False, isTop=False, enableWrapAround=False, additionalExtensions=None):
		self.selectedFiles = [] if preselectedFiles is None else preselectedFiles
		FileList.__init__(self, directory, showMountpoints=showMountpoints, matchingPattern=matchingPattern, showDirectories=showDirectories, showFiles=showFiles, useServiceRef=useServiceRef, inhibitDirs=inhibitDirs, inhibitMounts=inhibitMounts, isTop=isTop, enableWrapAround=enableWrapAround, additionalExtensions=additionalExtensions)
		self.changeDir(directory)
		font = fonts.get("FileListMulti", ("Regular", 20, 25))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])
		self.onSelectionChanged = []

	def selectionChanged(self):
		for callback in self.onSelectionChanged:
			callback()

	def changeSelectionState(self):
		if len(self.list):
			index = self.l.getCurrentSelectionIndex()
			newList = self.list[:]
			item = self.list[index]
			if not item[0][3].startswith("<"):
				realPathname = item[0][0] if item[0][1] else pathjoin(self.current_directory, item[0][0])
				if item[0][2]:
					selectState = False
					try:
						self.selectedFiles.remove(realPathname)
					except ValueError:
						try:
							self.selectedFiles.remove(normpath(realPathname))
						except OSError as err:
							print("[FileList] Error %d: Can't remove '%s'!  (%s)" % (err.errno, realPathname, err.strerror))
				else:
					selectState = True
					if (realPathname not in self.selectedFiles) and (normpath(realPathname) not in self.selectedFiles):
						self.selectedFiles.append(realPathname)
				newList[index] = MultiFileSelectEntryComponent(name=item[0][3], absolute=item[0][0], isDir=item[0][1], selected=selectState)
			self.list = newList
			self.l.setList(self.list)

	def getSelectedList(self):
		selectedFilesExist = []
		for file in self.selectedFiles:
			if exists(file):
				selectedFilesExist.append(file)
		return selectedFilesExist

	def changeDir(self, directory, select=None):
		self.list = []
		if self.current_directory is None:  # If we are just entering from the list of mount points.
			self.current_mountpoint = self.getMountpointLink(directory) if directory and self.showMountpoints else None
		self.current_directory = directory
		directories = []
		files = []
		if directory is None and self.showMountpoints:  # Present available mount points.
			for partition in harddiskmanager.getMountedPartitions():
				path = pathjoin(partition.mountpoint, "")
				if path not in self.inhibitMounts and not self.inParentDirs(path, self.inhibitDirs):
					self.list.append(MultiFileSelectEntryComponent(name=partition.description, absolute=path, isDir=True))
			files = []
			directories = []
		elif directory is None:
			files = []
			directories = []
		elif self.useServiceRef:
			root = eServiceReference(eServiceReference.idFile, eServiceReference.noFlags, eServiceReferenceFS.directory)
			root.setPath(directory)
			if self.additional_extensions:
				root.setName(self.additional_extensions)
			serviceHandler = eServiceCenter.getInstance()
			_list = serviceHandler.list(root)
			while True:
				service = _list.getNext()
				if not service.valid():
					del _list
					break
				if service.flags & service.mustDescent:
					directories.append(service.getPath())
				else:
					files.append(service)
			directories.sort()
			files.sort()
		else:
			if isdir(directory):
				try:
					files = listdir(directory)
				except OSError:
					files = []
				files.sort()
				tmpfiles = files[:]
				for file in tmpfiles:
					if isdir(pathjoin(directory, file)):
						directories.append(pathjoin(directory, file, ""))
						files.remove(file)
		if self.showDirectories:
			if directory is not None and not self.isTop:
				if directory == self.current_mountpoint and self.showMountpoints:
					self.list.append(MultiFileSelectEntryComponent(name="<%s>" % _("List of storage devices"), absolute=None, isDir=True))
				elif (directory != sep) and not (self.inhibitMounts and self.getMountpoint(directory) in self.inhibitMounts):
					self.list.append(MultiFileSelectEntryComponent(name="<%s>" % _("Parent directory"), absolute=pathjoin(sep.join(directory.split(sep)[:-2]), ""), isDir=True))
			for dir in directories:
				if not (self.inhibitMounts and self.getMountpoint(dir) in self.inhibitMounts) and not self.inParentDirs(dir, self.inhibitDirs):
					name = dir.split(sep)[-2]
					alreadySelected = (dir in self.selectedFiles) or (normpath(dir) in self.selectedFiles)
					self.list.append(MultiFileSelectEntryComponent(name=name, absolute=dir, isDir=True, selected=alreadySelected))
		if self.showFiles:
			for file in files:
				if self.useServiceRef:
					path = file.getPath()
					name = path.split(sep)[-1]
				else:
					path = pathjoin(directory, file)
					name = file
				if (self.matchingPattern is None) or self.matchingPattern.search(path):
					alreadySelected = False
					for entry in self.selectedFiles:
						# if basename(entry) == file:
						if entry == path:
							alreadySelected = True
					self.list.append(MultiFileSelectEntryComponent(name=name, absolute=file, isDir=False, selected=alreadySelected))
		self.l.setList(self.list)
		if select is not None:
			self.moveToIndex(0)
			for index, item in enumerate(self.list):
				path = item[0][0]
				if isinstance(path, eServiceReference):
					path = path.getPath()
				if path == select:
					self.moveToIndex(index)
