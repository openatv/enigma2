##
## Picon renderer by Gruffy .. some speedups by Ghost
##
from Renderer import Renderer
from enigma import ePixmap
from Tools.Directories import pathExists, fileExists, SCOPE_SKIN_IMAGE, resolveFilename

class Picon(Renderer):
	pngname = ""
	nameCache = { }
	searchPaths = ['/etc/picon/',
				'/media/cf/picon/',
				'/media/usb/picon/',
				'/media/hdd/picon/']

	def __init__(self):
		Renderer.__init__(self)

	GUI_WIDGET = ePixmap

	def changed(self, what):
		if self.instance:
			pngname = ""
			if what[0] != self.CHANGED_CLEAR:
				sname = self.source.text
				pngname = self.nameCache.get(sname, "")
				if pngname == "":
					pngname = self.findPicon(self.source.text)
					if pngname == "":
						self.nameCache[sname] = pngname
					else:
						self.nameCache[sname] = pngname
			if pngname == "": # no picon for service found
				pngname = self.nameCache.get("default", "")
				if pngname == "": # no default yet in cache..
					pngname = self.findPicon("picon_default")
					self.nameCache[sname] = pngname
					if pngname == "": # Fallback to enigma2 logo
						pngname = resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/enigma2.png")
					self.nameCache["default"] = pngname
			if self.pngname != pngname:
				self.instance.setPixmapFromFile(pngname)
				self.pngname = pngname

	def findPicon(self, serviceName):
		for path in self.searchPaths:
			if pathExists(path):
				png = self.findFile(path, serviceName)
				if png != "":
					return png
		return ""

	def findFile(self, path, serviceName):
		pngname = path + serviceName + ".png"
		if fileExists(pngname):
			return pngname
		else:
			for i in range(len(serviceName), 1, -1):
				if fileExists(path + serviceName[0:i] + ".png"):
					return path + serviceName[0:i] + ".png"
			return ""
