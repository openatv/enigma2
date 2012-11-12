# -*- coding: utf-8 -*-
from enigma import *
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.GUIComponent import GUIComponent
from Components.HTMLComponent import HTMLComponent
from Tools.Directories import fileExists, SCOPE_SKIN_IMAGE, SCOPE_CURRENT_SKIN, resolveFilename
from Components.Label import Label
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Pixmap import Pixmap
from Tools.LoadPixmap import LoadPixmap

class ExtraActionBox(Screen):
	skin = """
		<screen name="ExtraActionBox" position="360,325" size="560,70" title=" ">
		<widget alphatest="on" name="logo" position="10,10" size="48,48" transparent="1" zPosition="2"/>
		<widget font="Regular;20" halign="center" name="message" position="60,10" size="490,48" valign="center"/>
	</screen>"""
	def __init__(self, session, message, title, action):
		Screen.__init__(self, session)
		self.session = session
		self.ctitle = title
		self.caction = action

		self["message"] = Label(message)
		self["logo"] = Pixmap()
		self.timer = eTimer()
		self.timer.callback.append(self.__setTitle)
		self.timer.start(200, 1)
		
	def __setTitle(self):
		if self["logo"].instance is not None:
			self["logo"].instance.setPixmapFromFile("/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/icons/run.png")
		self.setTitle(self.ctitle)
		self.timer = eTimer()
		self.timer.callback.append(self.__start)
		self.timer.start(200, 1)
		
	def __start(self):
		self.close(self.caction())
