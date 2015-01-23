# -*- coding: iso-8859-1 -*-
# (c) 2006 Stephan Reichholf
# This Software is Free, use it where you want, when you want for whatever you want and modify it if you want but don't remove my copyright!
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList
from Plugins.Plugin import PluginDescriptor
from Components.config import config
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from enigma import eEnv
import os

SKINXML = "skin.xml"
DEFAULTSKIN = "<Default Skin>"

class SkinSelector(Screen):
	# for i18n:
	# _("Choose your Skin")
	skinlist = []
	root = os.path.join(eEnv.resolve("${datadir}"),"enigma2")

	def __init__(self, session, args = None):

		Screen.__init__(self, session)

		self.skinlist = []
		self.previewPath = ""
		if os.path.exists(os.path.join(self.root, SKINXML)):
			self.skinlist.append(DEFAULTSKIN)
		for root, dirs, files in os.walk(self.root, followlinks=True):
			for subdir in dirs:
				dir = os.path.join(root,subdir)
				if os.path.exists(os.path.join(dir,SKINXML)):
					self.skinlist.append(subdir)
			dirs = []

		self["key_red"] = StaticText(_("Close"))
		self["introduction"] = StaticText(_("Press OK to activate the selected skin."))
		self.skinlist.sort()
		self["SkinList"] = MenuList(self.skinlist)
		self["Preview"] = Pixmap()

		self["actions"] = NumberActionMap(["WizardActions", "InputActions", "EPGSelectActions"],
		{
			"ok": self.ok,
			"back": self.close,
			"red": self.close,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right,
			"info": self.info,
		}, -1)

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		tmp = config.skin.primary_skin.value.find("/"+SKINXML)
		if tmp != -1:
			tmp = config.skin.primary_skin.value[:tmp]
			idx = 0
			for skin in self.skinlist:
				if skin == tmp:
					break
				idx += 1
			if idx < len(self.skinlist):
				self["SkinList"].moveToIndex(idx)
		self.loadPreview()

	def up(self):
		self["SkinList"].up()
		self.loadPreview()

	def down(self):
		self["SkinList"].down()
		self.loadPreview()

	def left(self):
		self["SkinList"].pageUp()
		self.loadPreview()

	def right(self):
		self["SkinList"].pageDown()
		self.loadPreview()

	def info(self):
		aboutbox = self.session.open(MessageBox,_("Enigma2 skin selector"), MessageBox.TYPE_INFO)
		aboutbox.setTitle(_("About..."))

	def ok(self):
		if self["SkinList"].getCurrent() == DEFAULTSKIN:
			self.skinfile = "."
		else:
			self.skinfile = self["SkinList"].getCurrent()
		self.skinfile = os.path.join(self.skinfile, SKINXML)

		print "Skinselector: Selected Skin: "+self.root+self.skinfile
		restartbox = self.session.openWithCallback(self.restartGUI,MessageBox,_("GUI needs a restart to apply a new skin\nDo you want to restart the GUI now?"), MessageBox.TYPE_YESNO)
		restartbox.setTitle(_("Restart GUI now?"))

	def loadPreview(self):
		if self["SkinList"].getCurrent() == DEFAULTSKIN:
			pngpath = "."
		else:
			pngpath = self["SkinList"].getCurrent()
		pngpath = os.path.join(os.path.join(self.root, pngpath), "prev.png")

		if not os.path.exists(pngpath):
			pngpath = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SkinSelector/noprev.png")

		if self.previewPath != pngpath:
			self.previewPath = pngpath

		self["Preview"].instance.setPixmapFromFile(self.previewPath)

	def restartGUI(self, answer):
		if answer is True:
			config.skin.primary_skin.value = self.skinfile
			config.skin.primary_skin.save()
			self.session.open(TryQuitMainloop, 3)

def SkinSelMain(session, **kwargs):
	session.open(SkinSelector)

def SkinSelSetup(menuid, **kwargs):
	if menuid == "system":
		return [(_("Skin"), SkinSelMain, "skin_selector", None)]
	else:
		return []

def Plugins(**kwargs):
	return PluginDescriptor(name="Skinselector", description="Select Your Skin", where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc=SkinSelSetup)
