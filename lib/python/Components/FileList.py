from HTMLComponent import *
from GUIComponent import *
import re

from MenuList import MenuList

from Tools.Directories import *

from enigma import *

RT_HALIGN_LEFT = 0
RT_HALIGN_RIGHT = 1
RT_HALIGN_CENTER = 2
RT_HALIGN_BLOCK = 4

RT_VALIGN_TOP = 0
RT_VALIGN_CENTER = 8
RT_VALIGN_BOTTOM = 16

EXTENSIONS = {
		"mp3": "music",
		"wav": "music",
		"ogg": "music",
		"jpg": "picture",
		"jpeg": "picture",
		"png": "picture",
		"ts": "movie",
		"avi": "movie",
		"mpg": "movie",
		"mpeg": "movie",
	}

def FileEntryComponent(name, absolute = None, isDir = False):
	res = [ (absolute, isDir) ]
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 35, 1, 470, 20, 0, RT_HALIGN_LEFT, name))
	if isDir:
		png = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "extensions/directory.png"))
	else:
		extension = name.split('.')
		extension = extension[-1].lower()
		if EXTENSIONS.has_key(extension):
			png = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "extensions/" + EXTENSIONS[extension] + ".png"))
		else:
			png = None
	if png is not None:
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 10, 2, 20, 20, png))
	
	return res

class FileList(MenuList, HTMLComponent, GUIComponent):
	def __init__(self, directory, showDirectories = True, showFiles = True, matchingPattern = None, useServiceRef = False, isTop = False):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		
		self.current_directory = None
		self.useServiceRef = useServiceRef
		self.showDirectories = showDirectories
		self.showFiles = showFiles
		self.isTop = isTop
		# example: matching .nfi and .ts files: "^.*\.(nfi|ts)"
		self.matchingPattern = matchingPattern
		self.changeDir(directory)

		self.l.setFont(0, gFont("Regular", 18))
		
	def getSelection(self):
		return self.l.getCurrentSelection()[0]
	
	def getFileList(self):
		return self.list
	
	def changeDir(self, directory, select = None):
		self.list = []
		
		self.current_directory = directory
		directories = []
		files = []
		
		if self.useServiceRef:
			root = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + directory)
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
				print s.getName(), s.flags
			directories.sort()
			files.sort()
		else:
			files = os.listdir(directory)
			files.sort()
			tmpfiles = files[:]
			for x in tmpfiles:
				if os.path.isdir(directory + x):
					directories.append(directory + x + "/")
					files.remove(x)
		
		if directory != "/" and self.showDirectories and not self.isTop:
			self.list.append(FileEntryComponent(name = "..", absolute = '/'.join(directory.split('/')[:-2]) + '/', isDir = True))

		if self.showDirectories:
			for x in directories:
				name = x.split('/')[-2]
				self.list.append(FileEntryComponent(name = name, absolute = x, isDir = True))

		if self.showFiles:
			for x in files:
				if self.useServiceRef:
					path = x.getPath()
					name = path.split('/')[-1]
				else:
					path = directory + x
					name = x
				
				if self.matchingPattern is not None:
					if re.compile(self.matchingPattern).search(path):
						self.list.append(FileEntryComponent(name = name, absolute = x , isDir = False))
				else:
					self.list.append(FileEntryComponent(name = name, absolute = x , isDir = False))

		self.l.setList(self.list)
		
		if select is not None:
			i = 0
			self.moveToIndex(0)
			for x in self.list:
				p = x[0][0]
				
				if isinstance(p, eServiceReference):
					p = p.getPath()
				
				if p == select:
					self.moveToIndex(i)
				i += 1

	def getCurrentDirectory(self):
		return self.current_directory

	def canDescent(self):
		return self.getSelection()[1]
	
	def descent(self):
		self.changeDir(self.getSelection()[0], select = self.current_directory)
		
	def getFilename(self):
		x = self.getSelection()[0]
		if isinstance(x, eServiceReference):
			x = x.getPath()
		return x

	def getServiceRef(self):
		x = self.getSelection()[0]
		if isinstance(x, eServiceReference):
			return x
		return None

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.setItemHeight(23)
