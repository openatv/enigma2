# -*- coding: utf-8 -*-
# by digiteng...12-2019
# v1.1a 01-2020
from os.path import exists

from enigma import ePixmap, loadJPG

from Components.Renderer.Renderer import Renderer


class pstrRndr(Renderer):
	GUI_WIDGET = ePixmap
	POSTER = "/tmp/poster/poster.jpg"

	def changed(self, what):
		if self.instance:
			if self.source.text and exists(self.POSTER):
				self.instance.setPixmap(loadJPG(self.POSTER))
				self.instance.show()
			else:
				self.instance.hide()
