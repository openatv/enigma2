# -*- coding: utf-8 -*-
# by digiteng...12-2019
# v1.1a 01-2020
from os.path import exists
from enigma import ePixmap, loadJPG
from Components.Renderer.Renderer import Renderer


class pstrRndr(Renderer):
	GUI_WIDGET = ePixmap

	def __init__(self):
		Renderer.__init__(self)

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value,) in self.skinAttributes:
			attribs.append((attrib, value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def changed(self, what):
		try:
			eventName = self.source.text
			if eventName:
				poster = "/tmp/poster/poster.jpg"
				if exists(poster):
					self.instance.setPixmap(loadJPG(poster))
					self.instance.show()
				else:
					self.instance.hide()
			else:
				self.instance.hide()
		except Exception:
			pass
