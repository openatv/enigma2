from Renderer import Renderer
from enigma import ePixmap
from Tools.Directories import pathExists, SCOPE_SKIN_IMAGE, SCOPE_CURRENT_SKIN, resolveFilename
from os import listdir

class Picon(Renderer):
	searchPaths = ['/usr/share/enigma2/picon/','/picon/']
	if pathExists("/media"):
		for f in listdir("/media"):
			if pathExists('/media/' + f + '/picon'):
				searchPaths.append('/media/' + f + '/picon/')
	if pathExists("/media/net"):
		for f in listdir("/media/net"):
			if pathExists('/media/net/' + f + '/picon'):
				searchPaths.append('/media/net/' + f + '/picon/')
	if pathExists("/autofs"):
		for f in listdir("/autofs"):
			if pathExists('/autofs/' + f + '/picon'):
				searchPaths.append('/autofs/' + f + '/picon/')

	def __init__(self):
		Renderer.__init__(self)
		self.pngname = ""
		self.lastPath = None
		pngname = self.findPicon("picon_default")
		if not pngname:
			tmp = resolveFilename(SCOPE_CURRENT_SKIN, "picon_default.png")
			if pathExists(tmp):
				pngname = tmp
			else:
				pngname = resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/picon_default.png")
		self.defaultpngname = pngname

	def addPath(self, value):
		if pathExists(value):
			if not value.endswith('/'):
				value += '/'
			if value not in self.searchPaths:
				self.searchPaths = self.searchPaths + (value,)

	def applySkin(self, desktop, parent):
		attribs = self.skinAttributes[:]
		for (attrib, value) in self.skinAttributes:
			if attrib == "path":
				self.addPath(value)
				attribs.remove((attrib,value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	GUI_WIDGET = ePixmap

	def changed(self, what):
		if self.instance:
			pngname = ""
			if what[0] != self.CHANGED_CLEAR:
				sname = self.source.text
				# strip all after last :
				pos = sname.rfind(':')
				if pos != -1:
					sname = sname[:pos].rstrip(':').replace(':','_')
				pngname = self.findPicon(sname)
				if not pngname:
					fields = sname.split('_', 3)
					if len(fields) > 2 and fields[2] != '2':
						#fallback to 1 for tv services with nonstandard servicetypes
						fields[2] = '1'
						pngname = self.findPicon('_'.join(fields))
			if not pngname: # no picon for service found
				pngname = self.defaultpngname
			if self.pngname != pngname:
				self.instance.setScale(1)
				self.instance.setPixmapFromFile(pngname)
				self.pngname = pngname

	def findPicon(self, serviceName):
		if self.lastPath:
			pngname = self.lastPath + serviceName + ".png"
			if fileExists(pngname):
				return pngname
			else:
				pngname = self.lastPath + serviceName + "_0.png"
				if fileExists(pngname):
					return pngname
		for path in self.searchPaths:
			if pathExists(path):
				pngname = path + serviceName + ".png"
				if pathExists(pngname):
					self.lastPath = path
					return pngname
				else:
					pngname = path + serviceName + "_0.png"
					if pathExists(pngname):
						return pngname
		return ""
