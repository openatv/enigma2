# (c) 2006 Stephan Reichholf
# This Software is Free, use it where you want, when you want for whatever you want and modify it if you want but don't remove my copyright!

from enigma import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.Pixmap import Pixmap
from Components.GUIComponent import *
from Components.MenuList import MenuList
from Plugins.Plugin import PluginDescriptor

from Components.config import config
from Tools.Directories import SCOPE_SKIN

from Components.config import config

import os, sys

class SkinSelector(Screen):
	skin = """
		<screen position="75,138" size="600,320" title="Choose your Skin" >
			<widget name="SkinList" position="10,10" size="275,300" scrollbarMode="showOnDemand" />
			<widget name="Preview" position="305,45" size="280,210" alphatest="on"/>
		</screen>
		"""

	skinlist = []
	root = "/usr/share/enigma2/"

	def __init__(self, session, args = None):

		self.skin = SkinSelector.skin
		Screen.__init__(self, session)

		self.skinlist = []
		self.session = session
		self.previewPath = ""

		os.path.walk(self.root, self.find, "")

		self.skinlist.sort()
		self["SkinList"] = MenuList(self.skinlist)
		self["Preview"] = Pixmap()

		self["actions"] = NumberActionMap(["WizardActions", "InputActions", "EPGSelectActions"],
		{
			"ok": self.ok,
			"back": self.close,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right,
			"info": self.info,
		}, -1)
		
		self.onLayoutFinish.append(self.loadPreview)

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
		aboutbox = self.session.open(MessageBox,_("Enigma2 Skinselector v0.5 BETA\n\nIf you experience any problems please contact\nstephan@reichholf.net\n\n\xA9 2006 - Stephan Reichholf"), MessageBox.TYPE_INFO)
		aboutbox.setTitle(_("About..."))

	def find(self, arg, dirname, names):
		for x in names:
			if x == "skin.xml":
				if dirname <> self.root:
					subdir = dirname[19:]
					self.skinlist.append(subdir)
				else:
					subdir = "Default Skin"
					self.skinlist.append(subdir)

	def ok(self):
		if self["SkinList"].getCurrent() == "Default Skin":
			skinfile = "skin.xml"
		else:
			skinfile = self["SkinList"].getCurrent()+"/skin.xml"

		print "Skinselector: Selected Skin: "+self.root+skinfile
		config.skin.primary_skin.value = skinfile
		config.skin.primary_skin.save()
		restartbox = self.session.openWithCallback(self.restartGUI,MessageBox,_("GUI needs a restart to apply a new skin\nDo you want to Restart the GUI now?"), MessageBox.TYPE_YESNO)
		restartbox.setTitle(_("Restart GUI now?"))

	def loadPreview(self):
		if self["SkinList"].getCurrent() == "Default Skin":
			pngpath = self.root+"/prev.png"
		else:
			pngpath = self.root+self["SkinList"].getCurrent()+"/prev.png"

		if not os.path.exists(pngpath):
			# FIXME: don't use hardcoded path
			pngpath = "/usr/lib/enigma2/python/Plugins/SystemPlugins/SkinSelector/noprev.png"

		if self.previewPath != pngpath:
			self.previewPath = pngpath

		self["Preview"].instance.setPixmapFromFile(self.previewPath)

	def restartGUI(self, answer):
		if answer is True:
			quitMainloop(3)

def SkinSelMain(session, **kwargs):
	session.open(SkinSelector)

def SkinSelSetup(menuid):
	if menuid == "system":
		return [("Skin...", SkinSelMain)]
	else:
		return []

def Plugins(**kwargs):
	return PluginDescriptor(name="Skinselector", description="Select Your Skin", where = PluginDescriptor.WHERE_SETUP, fnc=SkinSelSetup)
