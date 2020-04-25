from enigma import getDesktop
from os import mkdir, path

from Components.ActionMap import HelpableActionMap
from Components.ChoiceList import ChoiceEntryComponent, ChoiceList
from Components.Console import Console
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import SystemInfo
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen
from Screens.Standby import QUIT_REBOOT, TryQuitMainloop
from Tools.BoundFunction import boundFunction
from Tools.Directories import copyfile, pathExists
from Tools.Multiboot import GetCurrentImage, GetCurrentImageMode, GetImagelist


class MultiBootSelector(Screen, HelpableScreen):
	skinTemplate = """
	<screen title="MultiBoot Image Selector" position="center,center" size="%d,%d">
		<widget name="config" position="%d,%d" size="%d,%d" font="Regular;%d" itemHeight="%d" scrollbarMode="showOnDemand" />
		<widget source="options" render="Label" position="%d,e-160" size="%d,%d" font="Regular;%d" halign="center" valign="center" />
		<widget source="description" render="Label" position="%d,e-90" size="%d,%d" font="Regular;%d" />
		<widget source="key_red" render="Label" position="%d,e-50" size="%d,%d" backgroundColor="key_red" font="Regular;%d" foregroundColor="key_text" halign="center" noWrap="1" valign="center" />
		<widget source="key_green" render="Label" position="%d,e-50" size="%d,%d" backgroundColor="key_green" font="Regular;%d" foregroundColor="key_text" halign="center" noWrap="1" valign="center" />
	</screen>"""
	scaleData = [
		800, 485,
		10, 10, 780, 306, 24, 34,
		10, 780, 60, 20,
		10, 780, 30, 22,
		10, 140, 40, 20,
		160, 140, 40, 20
	]
	skin = None

	def __init__(self, session, *args):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		if MultiBootSelector.skin is None:
			# The skin template is designed for a HD screen so the scaling factor is 720.
			MultiBootSelector.skin = MultiBootSelector.skinTemplate % tuple([x * getDesktop(0).size().height() / 720 for x in MultiBootSelector.scaleData])
		Screen.setTitle(self, _("MultiBoot Image Selector"))
		self["config"] = ChoiceList(list=[ChoiceEntryComponent("", ((_("Retrieving image slots - Please wait...")), "Queued"))])
		self["options"] = StaticText(_("Mode 1 suppports Kodi, PiP may not work.\nMode 12 supports PiP, Kodi may not work.") if SystemInfo["canMode12"] else "")
		self["description"] = StaticText(_("Use the cursor keys to select an installed image and then Reboot button."))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Reboot"))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "DirectionActions", "KeyboardInputActions", "MenuActions"], {
			"red": (boundFunction(self.close, None), _("Cancel the image selection and exit")),
			"green": (self.reboot, _("Select the highlighted image and reboot")),
			"ok": (self.reboot, _("Select the highlighted image and reboot")),
			"cancel": (boundFunction(self.close, None), _("Cancel the image selection and exit")),
			"up": (self.keyUp, _("Move up a line")),
			"down": (self.keyDown, _("Move down a line")),
			"left": (self.keyLeft, _("Move up a line")),
			"right": (self.keyRight, _("Move down a line")),
			"upRepeated": (self.keyUp, _("Move up a line")),
			"downRepeated": (self.keyDown, _("Move down a line")),
			"leftRepeated": (self.keyLeft, _("Move up a line")),
			"rightRepeated": (self.keyRight, _("Move down a line")),
			"menu": (boundFunction(self.close, True), _("Cancel the image selection and exit all menus"))
		}, -1, description=_("MultiBootSelector Actions"))
		imagedict = []
		self.getImageList = None
		self.mountDir = "/tmp/startupmount"
		self.callLater(self.getBootOptions)

	def cancel(self, value=None):
		self.container = Console()
		self.container.ePopen("umount %s" % self.mountDir, boundFunction(self.unmountCallback, value))

	def unmountCallback(self, value, data=None, retval=None, extra_args=None):
		self.container.killAll()
		if not path.ismount(self.mountDir):
			rmdir(self.mountDir)
		self.close(value)

	def getBootOptions(self, value=None):
		self.container = Console()
		if path.isdir(self.mountDir) and path.ismount(self.mountDir):
			self.getImagesList()
		else:
			if not path.isdir(self.mountDir):
				mkdir(self.mountDir)
			self.container.ePopen("mount %s %s" % (SystemInfo["MBbootdevice"], self.mountDir), self.getImagesList)

	def getImagesList(self, data=None, retval=None, extra_args=None):
		self.container.killAll()
		self.getImageList = GetImagelist(self.getImagelistCallback)

	def getImagelistCallback(self, imagedict):
		list = []
		mode = GetCurrentImageMode() or 0
		currentimageslot = GetCurrentImage()
		print "[MultiBootSelector] reboot1 slot:", currentimageslot
		current = "  %s" % _("(current image)")
		slotSingle = _("Slot %s: %s%s")
		slotMulti = _("Slot %s: %s - Mode %d%s")
		if imagedict:
			indextot = 0
			for index, x in enumerate(sorted(imagedict.keys())):
				if imagedict[x]["imagename"] != _("Empty slot"):
					if SystemInfo["canMode12"]:
						list.insert(index, ChoiceEntryComponent("", (slotMulti % (x, imagedict[x]["imagename"], 1, current if x == currentimageslot and mode != 12 else ""), x)))
						list.append(ChoiceEntryComponent("", (slotMulti % (x, imagedict[x]["imagename"], 12, current if x == currentimageslot and mode == 12 else ""), x + 12)))
						indextot = index + 1
					else:
						list.append(ChoiceEntryComponent("", (slotSingle % (x, imagedict[x]["imagename"], current if x == currentimageslot else ""), x)))
			if SystemInfo["canMode12"]:
				list.insert(indextot, " ")
		else:
			list.append(ChoiceEntryComponent("", ((_("No images found")), "Waiter")))
		self["config"].setList(list)

	def reboot(self):
		self.currentSelected = self["config"].l.getCurrentSelection()
		self.slot = self.currentSelected[0][1]
		if self.currentSelected[0][1] != "Queued":
			print "[MultiBootSelector] reboot2 rebootslot = %s, " % self.slot
			print "[MultiBootSelector] reboot3 slotinfo = %s" % SystemInfo["canMultiBoot"]
			if self.slot < 12:
				copyfile(path.join(self.mountDir, SystemInfo["canMultiBoot"][self.slot]["startupfile"]), path.join(self.mountDir, "STARTUP"))
			else:
				self.slot -= 12
				startupfile = path.join(self.mountDir, SystemInfo["canMultiBoot"][self.slot]["startupfile"].replace("BOXMODE_1", "BOXMODE_12"))
				print "[MultiBootSelector] reboot5 startupfile = %s" % startupfile
				if "BOXMODE" in startupfile:
					copyfile(startupfile, path.join(self.mountDir, "STARTUP"))
				else:
					f = open(startupfile, "r").read().replace("boxmode=1'", "boxmode=12'").replace("%s" % SystemInfo["canMode12"][0], "%s" % SystemInfo["canMode12"][1])
					open(path.join(self.mountDir, "STARTUP"), "w").write(f)
					self.session.open(TryQuitMainloop, QUIT_REBOOT)
			self.session.open(TryQuitMainloop, QUIT_REBOOT)

	def selectionChanged(self):
		currentSelected = self["config"].l.getCurrentSelection()

	def keyLeft(self):
		self["config"].instance.moveSelection(self["config"].instance.moveUp)
		self.selectionChanged()

	def keyRight(self):
		self["config"].instance.moveSelection(self["config"].instance.moveDown)
		self.selectionChanged()

	def keyUp(self):
		self["config"].instance.moveSelection(self["config"].instance.moveUp)
		self.selectionChanged()

	def keyDown(self):
		self["config"].instance.moveSelection(self["config"].instance.moveDown)
		self.selectionChanged()
