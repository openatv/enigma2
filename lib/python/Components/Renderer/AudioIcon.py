from Renderer import Renderer
from enigma import ePixmap
from Tools.Directories import fileExists, SCOPE_CURRENT_SKIN, resolveFilename
import os

class AudioIcon(Renderer):
	searchPaths = (resolveFilename(SCOPE_CURRENT_SKIN), '/usr/share/enigma2/skin_default/')

	def __init__(self):
		Renderer.__init__(self)
		self.size = None
		self.nameAudioCache = { }
		self.pngname = ""
		self.path = ""

	def applySkin(self, desktop, parent):
		attribs = [ ]
		for (attrib, value) in self.skinAttributes:
			if attrib == "path":
				self.path = value
				if value.endswith("/"):
					self.path = value
				else:
					self.path = value + "/"
			else:
				attribs.append((attrib,value))
			if attrib == "size":
				value = value.split(',')
				if len(value) == 2:
					self.size = value[0] + "x" + value[1]
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	GUI_WIDGET = ePixmap

	def changed(self, what):
		if self.instance:
			pngname = ""
			if what[0] != self.CHANGED_CLEAR:
				sname = self.source.text
				pngname = self.nameAudioCache.get(sname, "")
				if pngname == "":
					pngname = self.findAudioIcon(sname)
					if pngname != "":
						self.nameAudioCache[sname] = pngname
			if pngname == "":
				self.instance.hide()
			else:
				self.instance.show()
			if pngname != "" and self.pngname != pngname:
				self.instance.setPixmapFromFile(pngname)
				self.pngname = pngname

	def findAudioIcon(self, audioName):
		if self.path.startswith("/"):
			pngname = self.path + audioName + ".png"
			if os.path.exists(pngname):
				return pngname
		for path in self.searchPaths:
			pngname = path + self.path + audioName + ".png"
			if os.path.exists(pngname):
				return pngname
		return ""

