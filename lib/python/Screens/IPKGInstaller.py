from os import listdir
from os.path import exists

from enigma import getDesktop

from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.Input import Input
from Components.MenuList import MenuList
from Components.Opkg import OpkgComponent
from Components.SelectionList import SelectionList
from Components.Sources.StaticText import StaticText
from Screens.Opkg import Opkg
from Screens.Screen import Screen


class IPKGMenu(Screen):
	skin = """
		<screen name="IPKGMenu" position="center,center" size="560,400" resolution="1280,720">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="filelist" position="5,50" size="550,340" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Select Upgrade Source To Edit"))
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Edit"))
		self.sel = []
		self.val = []
		self.entry = False
		self.exe = False
		self.path = ""
		self["actions"] = HelpableActionMap(self, ["OkCancelActions"], {
			"ok": self.KeyOk,
			"cancel": self.keyCancel
		}, prio=-1)
		self["shortcuts"] = HelpableActionMap(self, ["ColorActions"], {
			"red": self.keyCancel,
			"green": self.KeyOk,
		})
		self["filelist"] = MenuList([])
		self.fill_list()

	def fill_list(self):
		flist = []
		self.path = "/etc/opkg/"
		if (exists(self.path) is False):
			self.entry = False
			return
		for file in listdir(self.path):
			if file.endswith(".conf"):
				if file not in ("arch.conf", "opkg.conf"):
					flist.append((file))
					self.entry = True
		self["filelist"].l.setList(flist)

	def KeyOk(self):
		if (self.exe is False) and (self.entry is True):
			self.sel = self["filelist"].getCurrent()
			self.val = self.path + self.sel
			self.session.open(IPKGSource, self.val)

	def keyCancel(self):
		self.close()

	def Exit(self):
		self.close()


class IPKGSource(Screen):
	skin = """
		<screen name="IPKGSource" position="center,center" size="560,80" title="Edit upgrade source url." resolution="1280,720">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="text" position="5,50" size="550,25" font="Regular;20" backgroundColor="background" foregroundColor="#cccccc" />
		</screen>"""

	def __init__(self, session, configfile=None):
		Screen.__init__(self, session)
		self.setTitle(_("Edit Upgrade Source URL"))
		self.configfile = configfile
		text = ""
		if self.configfile:
			try:
				fp = open(configfile)
				sources = fp.readlines()
				if sources:
					text = sources[0]
				fp.close()
			except OSError:
				pass
		desk = getDesktop(0)
		x = int(desk.size().width())  # noqa F841
		y = int(desk.size().height())
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		if (y >= 720):
			self["text"] = Input(text, maxSize=False, type=Input.TEXT)
		else:
			self["text"] = Input(text, maxSize=False, visible_width=55, type=Input.TEXT)
		self["actions"] = HelpableNumberActionMap(self, ["WizardActions", "InputActions", "TextEntryActions", "KeyboardInputActions", "ShortcutActions"], {
			"ok": self.go,
			"back": self.close,
			"red": self.close,
			"green": self.go,
			"left": self.keyLeft,
			"right": self.keyRight,
			"home": self.keyHome,
			"end": self.keyEnd,
			"deleteForward": self.keyDeleteForward,
			"deleteBackward": self.keyDeleteBackward,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, prio=-1)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["text"].right()

	def go(self):
		text = self["text"].getText()
		if text:
			fp = open(self.configfile, "w")
			fp.write(text)
			fp.write("\n")
			fp.close()
		self.close()

	def keyLeft(self):
		self["text"].left()

	def keyRight(self):
		self["text"].right()

	def keyHome(self):
		self["text"].home()

	def keyEnd(self):
		self["text"].end()

	def keyDeleteForward(self):
		self["text"].delete()

	def keyDeleteBackward(self):
		self["text"].deleteBackward()

	def keyNumberGlobal(self, number):
		self["text"].number(number)


class IPKGInstaller(Screen):
	skin = """
		<screen name="IPKGInstaller" position="center,center" size="550,450" title="Install extensions" resolution="1280,720">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget name="list" position="5,50" size="540,360" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,410" zPosition="10" size="560,2" transparent="1" alphatest="on" />
			<widget source="introduction" render="Label" position="5,420" zPosition="10" size="550,30" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""

	def __init__(self, session, list):
		Screen.__init__(self, session)
		self.skinName = ["IpkgInstaller", self.skinName]
		self.selectionList = SelectionList()
		self["list"] = self.selectionList
		p = 0
		if len(list):
			p = list[0].rfind("/")
			title = list[0][:p]
			self.title = ("%s %s %s") % (_("Install extensions"), _("from"), title)
		for listindex in range(len(list)):
			self.selectionList.addSelection(list[listindex][p + 1:], list[listindex], listindex, False)
		self.selectionList.sort()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Install"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText(_("Invert"))
		self["introduction"] = StaticText(_("Press OK to toggle the selection."))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"ok": self.selectionList.toggleSelection,
			"cancel": self.close,
			"red": self.close,
			"green": self.install,
			"blue": self.selectionList.toggleAllSelection
		}, prio=-1)

	def install(self):
		packages = self.selectionList.getSelectionsList()
		cmdList = [(OpkgComponent.CMD_UPDATE, None)]
		for item in packages:
			cmdList.append((OpkgComponent.CMD_INSTALL, {"package": item[1]}))
		self.session.open(Opkg, cmdList=cmdList)
