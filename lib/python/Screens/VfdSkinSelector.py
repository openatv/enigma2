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
from os import path, walk
from enigma import eEnv

class VFDSkinSelector(Screen):
	skinlist = []
	root = eEnv.resolve("${datadir}/enigma2/vfd_skin/")

	def __init__(self, session, args = None):

		Screen.__init__(self, session)

		self.skinlist = []
		self.previewPath = ""
		path.walk(self.root, self.find, "")

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
		}, -1)

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		tmp = config.skin.vfdskin.value
		if tmp in self.skinlist:
			tmp = config.skin.vfdskin.value
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
			if x.startswith("skinvfd") and x.endswith(".xml"):
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
		print "VFDSkinselector: Selected Skin: ", skinfile
		config.skin.vfdskin.value = skinfile
		config.skin.vfdskin.save()
		restartbox = self.session.openWithCallback(self.restartGUI,MessageBox,_("GUI needs a restart to apply a new skin\nDo you want to Restart the GUI now?"), MessageBox.TYPE_YESNO)
		restartbox.setTitle(_("Restart GUI now?"))

	def loadPreview(self):
		pngpath = self["SkinList"].getCurrent()
		try:
			pngpath = pngpath.replace(".xml", "_prev.png")
			pngpath = self.root+pngpath
		except AttributeError:
			pngpath = eEnv.resolve("${datadir}/enigma2/vfd_skin/noprev.png")
		if self.previewPath != pngpath:
			self.previewPath = pngpath

		self["Preview"].instance.setPixmapFromFile(self.previewPath)

	def restartGUI(self, answer):
		if answer is True:
			self.session.open(TryQuitMainloop, 3)
