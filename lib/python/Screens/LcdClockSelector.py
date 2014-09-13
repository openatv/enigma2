from Screens.Screen import Screen
from Components.ActionMap import NumberActionMap
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.config import config
from Tools.Directories import resolveFilename
from os import path, walk
from enigma import eEnv

class LCDClockSelector(Screen):
	clocklist = []
	root = eEnv.resolve("${datadir}/enigma2/lcd_skin/")

	def __init__(self, session, args = None):

		Screen.__init__(self, session)

		self.clocklist = []
		self.previewPath = ""
		path.walk(self.root, self.find, "")

		self.clocklist.sort()
		self["ClockList"] = MenuList(self.clocklist)
		self["Preview"] = Pixmap()
		self["lab1"] = Label(_("Select LCD clock:"))
		self["lab2"] = Label(_("Preview:"))
		self["lab3"] = Label(_("Select your LCD clock and press OK to activate the selected clock."))

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
		try:
			what = open(self.root+'active','r').read()
		except:
			what = "clock_lcd_analog.xml"
		tmp = what
		if tmp in self.clocklist:
			idx = 0
			for skin in self.clocklist:
				if skin == tmp:
					break
				idx += 1
			if idx < len(self.clocklist):
				self["ClockList"].moveToIndex(idx)
		else:
			idx = 0
			self["ClockList"].moveToIndex(idx)
		self.loadPreview()

	def up(self):
		self["ClockList"].up()
		self.loadPreview()

	def down(self):
		self["ClockList"].down()
		self.loadPreview()

	def left(self):
		self["ClockList"].pageUp()
		self.loadPreview()

	def right(self):
		self["ClockList"].pageDown()
		self.loadPreview()

	def find(self, arg, dirname, names):
		for x in names:
			if x.startswith("clock_lcd") and x.endswith(".xml"):
				if dirname <> self.root:
					subdir = dirname[19:]
					skinname = x
					skinname = subdir + "/" + skinname
					self.clocklist.append(skinname)
				else:
					skinname = x
					self.clocklist.append(skinname)

	def ok(self):
		clockfile = self["ClockList"].getCurrent()
		fp = open(self.root+'active','w')
		fp.write(clockfile)
		fp.close()
		self.close()

	def loadPreview(self):
		pngpath = self["ClockList"].getCurrent()
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
