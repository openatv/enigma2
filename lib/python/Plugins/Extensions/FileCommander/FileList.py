import os
import re
from Components.FileList import FileList as FileListBase, EXTENSIONS as BASE_EXTENSIONS
from Components.Harddisk import harddiskmanager

from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS, SCOPE_CURRENT_SKIN

from enigma import RT_HALIGN_LEFT, BT_SCALE, eListboxPythonMultiContent, \
	eServiceReference, eServiceReferenceFS, eServiceCenter
from Tools.LoadPixmap import LoadPixmap
from addons.key_actions import TEXT_EXTENSIONS
import skin

LOCAL_EXTENSIONS = {
	"py": "py",
	"pyo": "py",
	"sh": "sh",
	"html": "html",
	"xml": "xml",
	"cfg": "cfg",
	"lst": "lst",
	"ipk": "ipk",
	"zip": "zip",
	"tar": "tar",
	"tgz": "tar",
	"gz": "gz",
	"rar": "rar",
	"mvi": "picture",
}

LOCAL_EXTENSIONS.update(((ext[1:], "txt") for ext in TEXT_EXTENSIONS if ext[1:] not in LOCAL_EXTENSIONS))

EXTENSIONS = BASE_EXTENSIONS.copy()
EXTENSIONS.update(LOCAL_EXTENSIONS)

imagePath = resolveFilename(SCOPE_CURRENT_SKIN, 'FCimages')
if not os.path.isdir(imagePath):
	imagePath = resolveFilename(SCOPE_PLUGINS, base="Extensions/FileCommander/images/")

def getPNGByExt(name):
	basename, ext = os.path.splitext(name)
	if ext.startswith('.'):
		ext = ext[1:]
	if ext == "gz":
		_, ex = os.path.splitext(basename)
		if ex == ".tar":
			ext = "tgz"
	elif re.match("^r\d+$", ext):
		ext = "rar"

	if ext in EXTENSIONS:
		return LoadPixmap(path=os.path.join(imagePath, EXTENSIONS[ext]) + ".png")
	else:
		return LoadPixmap(path=os.path.join(imagePath, "file.png"))

def FileEntryComponent(name, absolute=None, isDir=False, isLink=False):
	res = [(absolute, isDir, isLink)]
	x, y, w, h = skin.parameters.get("FileListName",(55, 1, 1175, 25))
	res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w-x, h, 0, RT_HALIGN_LEFT, name))
	if isLink:
		link_png = LoadPixmap(path=os.path.join(imagePath, "link-arrow.png"))
	else:
		link_png = None
	if isDir:
		if isLink and link_png is None:
			png = LoadPixmap(path=os.path.join(imagePath, "link.png"))
		else:
			png = LoadPixmap(path=os.path.join(imagePath, "directory.png"))
	else:
		png = getPNGByExt(name)
	if png is not None:
		x, y, w, h = skin.parameters.get("FileListIcon",(10, 4, 20, 20))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, x, y, w, h, png, None, None, BT_SCALE))
		if link_png is not None:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, x, y, w, h, link_png, None ,None, BT_SCALE))

	return res

def getSortedList(list, sortBy, dir=''):
	sort, reverse = [int(x) for x in sortBy.split('.')]
	tmplist = []
	for x in list:
		dx = dir + x
		date = size = 0
		if os.access(dx, os.R_OK):
			stat = os.lstat(dx)
			date, size = stat.st_ctime, stat.st_size
		tmplist.append((x, date, size))
	tmplist = sorted(tmplist, key=lambda x: x[sort], reverse=reverse)
	list = []
	for x in tmplist:
		list.append(x[0])
	return list

class FileList(FileListBase):
	def __init__(self, directory, showDirectories=True, showFiles=True, showMountpoints=True, matchingPattern=None, useServiceRef=False, inhibitDirs=False, inhibitMounts=False, isTop=False, enableWrapAround=True, additionalExtensions=None, sortDirs='0.0', sortFiles='0.0', firstDirs=True):
		self.parent_directory = None
		self.sortDirs = sortDirs
		self.sortFiles = sortFiles
		self.firstDirs = firstDirs

		FileListBase.__init__(self, directory, showDirectories=showDirectories, showFiles=showFiles, showMountpoints=showMountpoints, matchingPattern=matchingPattern, useServiceRef=useServiceRef, inhibitDirs=inhibitDirs, inhibitMounts=inhibitMounts, isTop=isTop, enableWrapAround=enableWrapAround, additionalExtensions=additionalExtensions)

	def setSortBy(self, sortBy, setDir=False):
		#0.0
		#| 0 - normal
		#| 1 - reverse
		#0 - name
		#1 - date
		#2 - size (files only)
		if setDir:
			self.sortDirs = sortBy
		else:
			self.sortFiles = sortBy

	def getSortBy(self):
		return '%s,%s' %(self.sortDirs, self.sortFiles)

	def changeDir(self, directory, select=None):
		self.list = []

		# if we are just entering from the list of mount points:
		if self.current_directory is None:
			if directory and self.showMountpoints:
				self.current_mountpoint = self.getMountpointLink(directory)
			else:
				self.current_mountpoint = None
		self.current_directory = directory
		self.parent_directory = False
		directories = []
		files = []

		if directory is None and self.showMountpoints:  # present available mountpoints
			for p in harddiskmanager.getMountedPartitions():
				path = os.path.join(p.mountpoint, "")
				if path not in self.inhibitMounts and not self.inParentDirs(path, self.inhibitDirs):
					self.list.append(FileEntryComponent(name=p.description, absolute=path, isDir=True, isLink=False))
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
			list = serviceHandler.list(root)
			while 1:
				s = list.getNext()
				if not s.valid():
					del list
					break
				if s.flags & s.mustDescent:
					directories.append(s.getPath())
				else:
					files.append(s)
			#directories.sort()
			#files.sort()
		else:
			if fileExists(directory):
				try:
					files = os.listdir(directory)
				except:
					files = []
				#files.sort()
				tmpfiles = files[:]
				for x in tmpfiles:
					if os.path.isdir(directory + x):
						directories.append(directory + x + "/")
						files.remove(x)

		directories = getSortedList(directories, self.sortDirs)
		files = getSortedList(files, self.sortFiles, directory or '')

		if directory is not None and self.showDirectories and not self.isTop:
			if directory == self.current_mountpoint and self.showMountpoints:
				self.list.append(FileEntryComponent(name="<" + _("List of Storage Devices") + ">", absolute=None, isDir=True, isLink=False))
				self.parent_directory = None
			elif (directory != "/") and not (self.inhibitMounts and self.getMountpoint(directory) in self.inhibitMounts):
				self.parent_directory = '/'.join(directory.split('/')[:-2]) + '/'
				self.list.append(FileEntryComponent(name="<" + _("Parent Directory") + ">", absolute=self.parent_directory, isDir=True, isLink=False))

		if self.firstDirs:
			if self.showDirectories:
				for x in directories:
					if not (self.inhibitMounts and self.getMountpoint(x) in self.inhibitMounts) and not self.inParentDirs(x, self.inhibitDirs):
						name = x.split('/')[-2]
						testname = x[:-1]
						self.list.append(FileEntryComponent(name=name, absolute=x, isDir=True, isLink=os.path.islink(testname)))

			if self.showFiles:
				for x in files:
					if self.useServiceRef:
						path = x.getPath()
						name = path.split('/')[-1]
					else:
						path = directory + x
						name = x

					if (self.matchingPattern is None) or self.matchingPattern.search(path):
						self.list.append(FileEntryComponent(name=name, absolute=x, isDir=False, isLink=os.path.islink(path)))
		else:
			if self.showFiles:
				for x in files:
					if self.useServiceRef:
						path = x.getPath()
						name = path.split('/')[-1]
					else:
						path = directory + x
						name = x

					if (self.matchingPattern is None) or self.matchingPattern.search(path):
						self.list.append(FileEntryComponent(name=name, absolute=x, isDir=False, isLink=os.path.islink(path)))

			if self.showDirectories:
				for x in directories:
					if not (self.inhibitMounts and self.getMountpoint(x) in self.inhibitMounts) and not self.inParentDirs(x, self.inhibitDirs):
						name = x.split('/')[-2]
						testname = x[:-1]
						self.list.append(FileEntryComponent(name=name, absolute=x, isDir=True, isLink=os.path.islink(testname)))

		if self.showMountpoints and len(self.list) == 0:
			self.list.append(FileEntryComponent(name=_("nothing connected"), absolute=None, isDir=False, isLink=False))

		self.l.setList(self.list)

		if select is not None:
			i = 0
			#self.moveToIndex(0)
			for x in self.list:
				p = x[0][0]

				if isinstance(p, eServiceReference):
					p = p.getPath()

				if p == select:
					self.moveToIndex(i)
				i += 1

	def getParentDirectory(self):
		return self.parent_directory

	def getSelectionID(self):
		idx = self.l.getCurrentSelectionIndex()
		return idx

def MultiFileSelectEntryComponent(name, absolute=None, isDir=False, isLink=False, selected=False):
	res = [(absolute, isDir, isLink, selected, name)]
	x, y, w, h = skin.parameters.get("FileListMultiName",(55, 1, 1175, 25))
	res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT, name))

	if isLink:
		link_png = LoadPixmap(path=os.path.join(imagePath, "link-arrow.png"))
	else:
		link_png = None
	if isDir:
		if isLink and link_png is None:
			png = LoadPixmap(path=os.path.join(imagePath, "link.png"))
		else:
			png = LoadPixmap(path=os.path.join(imagePath, "directory.png"))
	else:
		png = getPNGByExt(name)
	if png is not None:
		x, y, w, h = skin.parameters.get("FileListMultiIcon",(30, 4, 20, 20))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, x, y, w, h, png, None ,None, BT_SCALE))
		if link_png is not None:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, x, y, w, h, link_png, None ,None, BT_SCALE))

	if not name.startswith('<'):
		x, y, w, h = skin.parameters.get("FileListMultiLock",(4, 0, 25, 25))
		if selected is False:
			icon = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/lock_off.png"))
			if not icon:
				icon = LoadPixmap(path=os.path.join(imagePath, "lock_off.png"))
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, x, y, w, h, icon, None ,None, BT_SCALE))
		else:
			icon = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/lock_on.png"))
			if not icon:
				icon = LoadPixmap(path=os.path.join(imagePath, "lock_on.png"))
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, x, y, w, h, icon, None ,None, BT_SCALE))
	return res

class MultiFileSelectList(FileList):
	def __init__(self, preselectedFiles, directory, showMountpoints=False, matchingPattern=None, showDirectories=True, showFiles=True, useServiceRef=False, inhibitDirs=False, inhibitMounts=False, isTop=False, enableWrapAround=True, additionalExtensions=None, sortDirs='0.0', sortFiles='0.0', firstDirs=True):
		self.selectedFiles = preselectedFiles
		if self.selectedFiles is None:
			self.selectedFiles = []

		FileList.__init__(self, directory, showMountpoints=showMountpoints, matchingPattern=matchingPattern, showDirectories=showDirectories, showFiles=showFiles, useServiceRef=useServiceRef, inhibitDirs=inhibitDirs, inhibitMounts=inhibitMounts, isTop=isTop, enableWrapAround=enableWrapAround, additionalExtensions=additionalExtensions, sortDirs=sortDirs, sortFiles=sortFiles, firstDirs=firstDirs)
		self.changeDir(directory)
		self.onSelectionChanged = []

	def selectionChanged(self):
		for f in self.onSelectionChanged:
			f()

	def changeSelectionState(self):
		idx = self.l.getCurrentSelectionIndex()
		# os.system('echo %s >> /tmp/test1.log' % ("- xxx - "))
		count = 0
		newList = []
		for x in self.list:
			# os.system('echo %s >> /tmp/test1.log' % ("- state0 - "))
			if idx == count:
				if x[0][4].startswith('<'):
					newList.append(x)
				else:
					if x[0][1] is True:
						realPathname = x[0][0]
					else:
						realPathname = self.current_directory + x[0][0]
					SelectState = not x[0][3]
					if SelectState:
						if realPathname not in self.selectedFiles:
							self.selectedFiles.append(realPathname)
					else:
						if realPathname in self.selectedFiles:
							self.selectedFiles.remove(realPathname)
					newList.append(MultiFileSelectEntryComponent(name=x[0][4], absolute=x[0][0], isDir=x[0][1], isLink=x[0][2], selected=SelectState))
			else:
				newList.append(x)

			count += 1

		self.list = newList
		self.l.setList(self.list)

	def getSelectedList(self):
		return self.selectedFiles

	def changeDir(self, directory, select=None):
		self.list = []

		# if we are just entering from the list of mount points:
		if self.current_directory is None:
			if directory and self.showMountpoints:
				self.current_mountpoint = self.getMountpointLink(directory)
			else:
				self.current_mountpoint = None
		self.current_directory = directory
		directories = []
		files = []

		if directory is None and self.showMountpoints:  # present available mountpoints
			for p in harddiskmanager.getMountedPartitions():
				path = os.path.join(p.mountpoint, "")
				if path not in self.inhibitMounts and not self.inParentDirs(path, self.inhibitDirs):
					self.list.append(MultiFileSelectEntryComponent(name=p.description, absolute=path, isDir=True))
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
			list = serviceHandler.list(root)

			while 1:
				s = list.getNext()
				if not s.valid():
					del list
					break
				if s.flags & s.mustDescent:
					directories.append(s.getPath())
				else:
					files.append(s)
			#directories.sort()
			#files.sort()
		else:
			if fileExists(directory):
				try:
					files = os.listdir(directory)
				except:
					files = []
				#files.sort()
				tmpfiles = files[:]
				for x in tmpfiles:
					if os.path.isdir(directory + x):
						directories.append(directory + x + "/")
						files.remove(x)

		directories = getSortedList(directories, self.sortDirs)
		files = getSortedList(files, self.sortFiles, directory or '')

		if directory is not None and self.showDirectories and not self.isTop:
			if directory == self.current_mountpoint and self.showMountpoints:
				self.list.append(MultiFileSelectEntryComponent(name="<" + _("List of Storage Devices") + ">", absolute=None, isDir=True))
				self.parent_directory = None
			elif (directory != "/") and not (self.inhibitMounts and self.getMountpoint(directory) in self.inhibitMounts):
				self.parent_directory = '/'.join(directory.split('/')[:-2]) + '/'
				self.list.append(MultiFileSelectEntryComponent(name="<" + _("Parent Directory") + ">", absolute=self.parent_directory, isDir=True))

		if self.firstDirs:
			if self.showDirectories:
				for x in directories:
					if not (self.inhibitMounts and self.getMountpoint(x) in self.inhibitMounts) and not self.inParentDirs(x, self.inhibitDirs):
						name = x.split('/')[-2]
						testname = x[:-1]
						alreadySelected = x in self.selectedFiles
						self.list.append(MultiFileSelectEntryComponent(name=name, absolute=x, isDir=True, isLink=os.path.islink(testname), selected=alreadySelected))

			if self.showFiles:
				for x in files:
					if self.useServiceRef:
						path = x.getPath()
						name = path.split('/')[-1]
					else:
						path = directory + x
						name = x

					if (self.matchingPattern is None) or self.matchingPattern.search(path):
						alreadySelected = path in self.selectedFiles
						self.list.append(MultiFileSelectEntryComponent(name=name, absolute=x, isDir=False, isLink=os.path.islink(path), selected=alreadySelected))
		else:
			if self.showFiles:
				for x in files:
					if self.useServiceRef:
						path = x.getPath()
						name = path.split('/')[-1]
					else:
						path = directory + x
						name = x

					if (self.matchingPattern is None) or self.matchingPattern.search(path):
						alreadySelected = path in self.selectedFiles
						self.list.append(MultiFileSelectEntryComponent(name=name, absolute=x, isDir=False, isLink=os.path.islink(path), selected=alreadySelected))

			if self.showDirectories:
				for x in directories:
					if not (self.inhibitMounts and self.getMountpoint(x) in self.inhibitMounts) and not self.inParentDirs(x, self.inhibitDirs):
						name = x.split('/')[-2]
						testname = x[:-1]
						alreadySelected = x in self.selectedFiles
						self.list.append(MultiFileSelectEntryComponent(name=name, absolute=x, isDir=True, isLink=os.path.islink(testname), selected=alreadySelected))

		self.l.setList(self.list)

		if select is not None:
			i = 0
			#self.moveToIndex(0)
			for x in self.list:
				p = x[0][0]

				if isinstance(p, eServiceReference):
					p = p.getPath()

				if p == select:
					self.moveToIndex(i)
				i += 1
