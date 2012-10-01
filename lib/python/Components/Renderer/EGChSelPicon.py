# -*- coding: utf-8 -*-
import os
from Renderer import Renderer
from enigma import ePixmap
from Tools.Directories import fileExists, SCOPE_SKIN_IMAGE, SCOPE_CURRENT_SKIN, resolveFilename

class EGChSelPicon(Renderer):
	searchPaths = ('/%s/', '/media/usb/%s/', '/media/usb2/%s/', '/media/usb3/%s/', '/media/card/%s/', '/media/cf/%s/', '/etc/%s/', '/usr/share/enigma2/%s/')
		
	def __init__(self):
		Renderer.__init__(self)
		self.path = "picon"
		self.nameCache = { }
		self.pngname = ""

	def applySkin(self, desktop, parent):
		attribs = [ ]
		for (attrib, value) in self.skinAttributes:
			if attrib == "path":
				self.path = value
			else:
				attribs.append((attrib,value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	GUI_WIDGET = ePixmap

	def changed(self, what):
		if self.instance:
		      pngname = ""
		      if what[0] != self.CHANGED_CLEAR:
			      service = self.source.service
			      sname = service.toString()
			      # strip all after last :
			      pos = sname.rfind(':')
			      if pos != -1:
				      sname = sname[:pos].rstrip(':').replace(':','_')
			      pngname = self.nameCache.get(sname, "")
			      if pngname == "":
				      pngname = self.findPicon(sname)
				      if pngname != "":
					      self.nameCache[sname] = pngname
		      if pngname == "": # no picon for service found
			      pngname = self.nameCache.get("default", "")
			      if pngname == "": # no default yet in cache..
				      pngname = self.findPicon("picon_default")
				      if pngname == "":
					      tmp = resolveFilename(SCOPE_CURRENT_SKIN, "picon_default.png")
					      if fileExists(tmp):
						      pngname = tmp
					      else:
						      pngname = resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/picon_default.png")
				      self.nameCache["default"] = pngname
		      if self.pngname != pngname:
			      self.instance.setPixmapFromFile(pngname)
			      self.pngname = pngname


	def findPicon(self, serviceName):
		for path in self.searchPaths:
			pngname = (path % self.path) + serviceName + ".png"
			if fileExists(pngname):
				return pngname
		return ""
