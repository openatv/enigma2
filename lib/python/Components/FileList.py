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
		"jpg": "picture",
		"jpeg": "picture",
		"png": "picture",
		"ts": "movie",
		"avi": "movie",
		"mpg": "movie",
		"mpeg": "movie",
	}

def FileEntryComponent(name, absolute, isDir = False):
	res = [ (absolute, isDir) ]
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 35, 1, 200, 20, 0, RT_HALIGN_LEFT ,name))
	if isDir:
		png = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "/extensions/directory.png"))
	else:
		extension = name.split('.')
		extension = extension[len(extension) - 1]
		if EXTENSIONS.has_key(extension):
			png = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "/extensions/" + EXTENSIONS[extension] + ".png"))
	if png is not None:
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 10, 2, 20, 20, png))
	
	return res

class FileList(HTMLComponent, GUIComponent, MenuList):
	def __init__(self, directory, showDirectories = True, showFiles = True, matchingPattern = None):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()

		self.showDirectories = showDirectories
		self.showFiles = showFiles
		# example: matching .nfi and .ts files: "^.*\.(nfi|ts)"
		self.matchingPattern = matchingPattern
		self.changeDir(directory)

		self.l.setFont(0, gFont("Regular", 18))
		
	def getSelection(self):
		return self.l.getCurrentSelection()[0]
	
	def changeDir(self, directory):
		self.list = []
		
		directories = os.listdir(directory)
		
		if directory != "/" and self.showDirectories:
			self.list.append(FileEntryComponent(name = "..", absolute = '/'.join(directory.split('/')[:-2]) + '/', isDir = True))
		for x in directories:
			if os.path.isdir(directory + x):
				if self.showDirectories:
					self.list.append(FileEntryComponent(name = x, absolute = directory + x + "/" , isDir = True))
			elif self.showFiles:
				if self.matchingPattern is not None:
					if re.compile(self.matchingPattern).search(x):
						self.list.append(FileEntryComponent(name = x, absolute = directory + x , isDir = False))
				else:
					self.list.append(FileEntryComponent(name = x, absolute = directory + x , isDir = False))
				
		self.l.setList(self.list)
				
	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
		self.instance.setItemHeight(23)