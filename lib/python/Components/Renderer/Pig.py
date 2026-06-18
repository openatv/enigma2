# -*- coding: utf-8 -*-
from enigma import eVideoWidget, getDesktop

from Components.Renderer.Renderer import Renderer
from Screens.PictureInPicture import PipPigMode


class Pig(Renderer):
	GUI_WIDGET = eVideoWidget

	def __init__(self):
		Renderer.__init__(self)
		self.Position = None
		self.Size = None
		self.hidePip = True

	def postWidgetCreate(self, instance):
		instance.setDecoder(0)
		instance.setFBSize(getDesktop(0).size())

	def preWidgetRemove(self, instance):
		pass

	def applySkin(self, desktop, parent):
		attribs = list(self.skinAttributes or [])
		for attrib, value in list(attribs):
			if attrib == "hidePip":
				self.hidePip = str(value).strip().lower() in ("1", "true", "yes", "on")
				attribs.remove((attrib, value))
		self.skinAttributes = attribs

		ret = Renderer.applySkin(self, desktop, parent)
		if ret and self.instance:
			self.Position = self.instance.position()
			self.Size = self.instance.size()
		return ret

	def _applyPosition(self):
		if not self.instance:
			return
		if self.Size:
			self.instance.resize(self.Size)
		if self.Position:
			self.instance.move(self.Position)

	def onShow(self):
		if self.instance:
			self._applyPosition()
			if self.hidePip:
				PipPigMode(True)

	def onHide(self):
		if self.instance:
			self.instance.restoreFullsize()
			self.preWidgetRemove(self.instance)
			if self.hidePip:
				PipPigMode(False)
