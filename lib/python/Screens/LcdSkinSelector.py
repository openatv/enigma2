from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.MenuList import MenuList
from Plugins.Plugin import PluginDescriptor
from Components.config import config
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from os import path, walk
from enigma import eEnv
from skin import *
import os

class LCDSkinSelector(Screen):
	skin = """
		<screen name="LCDSkinSelector" position="center,center" size="700,400" title="LCD Skin-Selector" transparent="0">
			<widget name="lab1" position="50,30" size="250,26" zPosition="1" foregroundColor="#FFE500" font="Regular;22" halign="left" />
			<widget name="lab2" position="380,30" size="250,26" zPosition="1" foregroundColor="#FFE500" font="Regular;22" halign="left" />
			<widget name="SkinList" render="Listbox" position="50,60" size="270,200" zPosition="1" enableWrapAround="1" scrollbarMode="showOnDemand" />
			<widget name="Preview" position="380,65" size="280,210" zPosition="1" backgroundColor="background" transparent="0" alphatest="on" />
			<widget name="lab3" position="0,307" halign="center" size="700,26" zPosition="1" foregroundColor="#FFE500" font="Regular;22" />
		</screen>"""

	skinlist = []
	root = eEnv.resolve("${datadir}/enigma2/lcd_skin/")

	def __init__(self, session, args = None):

		Screen.__init__(self, session)

		self.skinlist = []
		self.previewPath = ""
		path.walk(self.root, self.find, "")

		self.skinlist.sort()
		self["SkinList"] = MenuList(self.skinlist)
		self["Preview"] = Pixmap()
		self["lab1"] = Label(_("Select skin:"))
		self["lab2"] = Label(_("Preview:"))
		self["lab3"] = Label(_("Select your skin and press OK to activate the selected skin."))

		self["actions"] = NumberActionMap(["WizardActions", "InputActions", "EPGSelectActions"],
		{
			"ok": self.ok,
			"back": self.close,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right,
		}, -1)

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		tmp = config.skin.lcdskin.value
		if tmp in self.skinlist:
			tmp = config.skin.lcdskin.value
			idx = 0
			for skin in self.skinlist:
				if skin == tmp:
					break
				idx += 1
			if idx < len(self.skinlist):
				self["SkinList"].moveToIndex(idx)
		else:
			idx = 0
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

	def find(self, arg, dirname, names):
		for x in names:
			if x.startswith("skin_lcd") and x.endswith(".xml"):
				if dirname <> self.root:
					subdir = dirname[19:]
					skinname = x
					skinname = subdir + "/" + skinname
					self.skinlist.append(skinname)
				else:
					skinname = x
					self.skinlist.append(skinname)

	def ok(self):
		skinfile = self["SkinList"].getCurrent()
		print "LCDSkinselector: Selected Skin: ", skinfile
		config.skin.lcdskin.value = skinfile
		config.skin.lcdskin.save()
		restartbox = self.session.openWithCallback(self.restartGUI,MessageBox,_("GUI needs a restart to apply a new skin\nDo you want to Restart the GUI now?"), MessageBox.TYPE_YESNO)
		restartbox.setTitle(_("Restart GUI now?"))

	def loadPreview(self):
		pngpath = self["SkinList"].getCurrent()
		try:
			pngpath = pngpath.replace(".xml", "_prev.png")
			pngpath = self.root+pngpath
		except AttributeError:
			pngpath = resolveFilename("${datadir}/enigma2/lcd_skin/noprev.png")
		
		if not path.exists(pngpath):
			pngpath = eEnv.resolve("${datadir}/enigma2/lcd_skin/noprev.png")		
		if self.previewPath != pngpath:
			self.previewPath = pngpath

		self["Preview"].instance.setPixmapFromFile(self.previewPath)

	def restartGUI(self, answer):
		if answer is True:
			self.session.open(TryQuitMainloop, 3)
