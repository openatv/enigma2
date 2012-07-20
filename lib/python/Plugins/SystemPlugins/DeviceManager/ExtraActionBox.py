# -*- coding: utf-8 -*-
from enigma import *
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.GUIComponent import GUIComponent
from Components.HTMLComponent import HTMLComponent
from Tools.Directories import fileExists, SCOPE_SKIN_IMAGE, SCOPE_CURRENT_PLUGIN, resolveFilename
from Components.Label import Label
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Pixmap import Pixmap
from Tools.LoadPixmap import LoadPixmap

class ExtraActionBox(Screen):
	skin = """
	<screen name="ExtraActionBox" position="center,center" size="560,70" title=" ">
		<widget alphatest="on" name="logo" position="10,10" size="48,48" transparent="1" zPosition="2"/>
		<widget font="Regular;20" halign="center" name="message" position="10,10" size="538,48" valign="center" />
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
			self["logo"].instance.setPixmapFromFile(resolveFilename(SCOPE_CURRENT_PLUGIN, 'SystemPlugins/DeviceManager/icons/run.png'))
		self.setTitle(self.ctitle)
		self.timer = eTimer()
		self.timer.callback.append(self.__start)
		self.timer.start(200, 1)

	def __start(self):
		self.close(self.caction())
