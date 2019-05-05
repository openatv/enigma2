from os import mkdir, path
from shutil import copyfile
from boxbranding import getMachineBuild, getMachineMtdRoot
from Components.Sources.StaticText import StaticText
from Components.ActionMap import ActionMap
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.Console import Console
from Components.Label import Label
from Components.SystemInfo import SystemInfo
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
from Tools.Directories import fileExists, fileCheck, pathExists, fileHas
from Tools.BoundFunction import boundFunction
from Tools.Multiboot import GetImagelist, GetCurrentImage, GetCurrentImageMode, ReadSTARTUP, GetSTARTUPFile

class MultiBootSelector(Screen):

	skin = """
	<screen name="Multiboot Image Selector" position="center,center" size="750,900" flags="wfNoBorder" backgroundColor="transparent">
		<eLabel name="b" position="0,0" size="750,700" backgroundColor="#00ffffff" zPosition="-2" />
		<eLabel name="a" position="1,1" size="748,698" backgroundColor="#00000000" zPosition="-1" />
		<widget source="Title" render="Label" position="60,10" foregroundColor="#00ffffff" size="480,50" halign="left" font="Regular; 28" backgroundColor="#00000000" />
		<eLabel name="line" position="1,60" size="748,1" backgroundColor="#00ffffff" zPosition="1" />
		<eLabel name="line2" position="1,250" size="748,4" backgroundColor="#00ffffff" zPosition="1" />
		<widget name="config" position="2,280" size="730,380" halign="center" font="Regular; 22" backgroundColor="#00000000" foregroundColor="#00e5b243" />
		<widget source="description" render="Label" position="2,80" size="730,30" halign="center" font="Regular; 22" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="options" render="Label" position="2,130" size="730,60" halign="center" font="Regular; 22" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="key_red" render="Label" position="30,200" size="150,30" noWrap="1" zPosition="1" valign="center" font="Regular; 20" halign="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="key_green" render="Label" position="200,200" size="150,30" noWrap="1" zPosition="1" valign="center" font="Regular; 20" halign="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<eLabel position="20,200" size="6,40" backgroundColor="#00e61700" /> <!-- Should be a pixmap -->
		<eLabel position="190,200" size="6,40" backgroundColor="#0061e500" /> <!-- Should be a pixmap -->
	</screen>
	"""

	def __init__(self, session, *args):
		Screen.__init__(self, session)
		screentitle = _("Multiboot Image Selector")
		self["key_red"] = StaticText(_("Cancel"))
		if not SystemInfo["HasSDmmc"] or SystemInfo["HasSDmmc"] and pathExists('/dev/%s4' %(SystemInfo["canMultiBoot"][2])):
			self["description"] = StaticText(_("Use the cursor keys to select an installed image and then Reboot button."))
		else:
			self["description"] = StaticText(_("SDcard is not initialised for multiboot - Exit and use MultiBoot Image Manager to initialise"))
		self["options"] = StaticText(_(" "))
		self["key_green"] = StaticText(_("Reboot"))
		if SystemInfo["canMode12"]:
			self["options"] = StaticText(_("Mode 1 suppports Kodi, PiP may not work.\nMode 12 supports PiP, Kodi may not work."))
		self["config"] = ChoiceList(list=[ChoiceEntryComponent('',((_("Retrieving image slots - Please wait...")), "Queued"))])
		imagedict = []
		self.mtdboot = "%s1" % SystemInfo["canMultiBoot"][2]
 		if SystemInfo["canMultiBoot"][2] == "sda":
			self.mtdboot = "%s3" %getMachineMtdRoot()[0:8]
		self.getImageList = None
		self.title = screentitle
		if not SystemInfo["HasSDmmc"] or SystemInfo["HasSDmmc"] and pathExists('/dev/%s4' %(SystemInfo["canMultiBoot"][2])):
			self.startit()

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "KeyboardInputActions", "MenuActions"],
		{
			"red": boundFunction(self.close, None),
			"green": self.reboot,
			"ok": self.reboot,
			"cancel": boundFunction(self.close, None),
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"upRepeated": self.keyUp,
			"downRepeated": self.keyDown,
			"leftRepeated": self.keyLeft,
			"rightRepeated": self.keyRight,
			"menu": boundFunction(self.close, True),
		}, -1)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(self.title)

	def startit(self):
		self.getImageList = GetImagelist(self.ImageList)

	def ImageList(self, imagedict):
		list = []
		mode = GetCurrentImageMode() or 0
		currentimageslot = GetCurrentImage() or 1
		if imagedict:
			if not SystemInfo["canMode12"]:
				for x in sorted(imagedict.keys()):
					if imagedict[x]["imagename"] != _("Empty slot"):
						list.append(ChoiceEntryComponent('',((_("slot%s -%s - %s (current image)") if x == currentimageslot else _("slot%s -%s- %s ")) % (x, imagedict[x]['part'][0:3], imagedict[x]['imagename']), x)))
			else:
				for x in range(1, SystemInfo["canMultiBoot"][1] + 1):
					if imagedict[x]["imagename"] != _("Empty slot"):
						list.append(ChoiceEntryComponent('',((_("slot%s - %s mode 1 (current image)") if x == currentimageslot and mode != 12 else _("slot%s - %s mode 1")) % (x, imagedict[x]['imagename']), x)))
				list.append("                                 ")
				list.append("                                 ")
				for x in range(1, SystemInfo["canMultiBoot"][1] + 1):
						if SystemInfo["canMode12"] and imagedict[x]["imagename"] != _("Empty slot"):
							list.append(ChoiceEntryComponent('',((_("slot%s - %s mode 12 (current image)") if x == currentimageslot and mode == 12 else _("slot%s - %s mode 12")) % (x, imagedict[x]['imagename']), x)))
		else:
			list.append(ChoiceEntryComponent('',((_("No images found")), "Waiter")))
		self["config"].setList(list)

	def reboot(self):
		self.currentSelected = self["config"].l.getCurrentSelection()
		if self.currentSelected[0][1] != "Queued":
			self.container = Console()
			if pathExists('/tmp/startupmount'):
				self.ContainterFallback()
			else:
				mkdir('/tmp/startupmount')
				if SystemInfo["HasRootSubdir"]:
					if fileExists("/dev/block/by-name/bootoptions"):
						self.container.ePopen('mount /dev/block/by-name/bootoptions /tmp/startupmount', self.ContainterFallback)
					elif fileExists("/dev/block/by-name/boot"):
						self.container.ePopen('mount /dev/block/by-name/boot /tmp/startupmount', self.ContainterFallback)
				else:
					self.container.ePopen('mount /dev/%s /tmp/startupmount' % self.mtdboot, self.ContainterFallback)

	def ContainterFallback(self, data=None, retval=None, extra_args=None):
		self.container.killAll()
		slot = self.currentSelected[0][1]
		mode = GetCurrentImageMode() or 0
		currentimageslot = GetCurrentImage() or 1
		if pathExists("/tmp/startupmount/%s" %GetSTARTUPFile()):
			if currentimageslot == slot and SystemInfo["canMode12"]:
				if mode == 12:
					startupFileContents = ReadSTARTUP().replace("boxmode=12'","boxmode=1'").replace(SystemInfo["canMode12"][1],SystemInfo["canMode12"][0])
					open('/tmp/startupmount/%s'%GetSTARTUPFile(), 'w').write(startupFileContents)
				else:
					startupFileContents = ReadSTARTUP().replace("boxmode=1'","boxmode=12'").replace(SystemInfo["canMode12"][0],SystemInfo["canMode12"][1])
					open('/tmp/startupmount/%s'%GetSTARTUPFile(), 'w').write(startupFileContents)
			elif  fileExists("/tmp/startupmount/STARTUP_1"):
				copyfile("/tmp/startupmount/STARTUP_%s" % slot, "/tmp/startupmount/%s" %GetSTARTUPFile())
			elif fileExists("/tmp/startupmount/STARTUP_LINUX_4_BOXMODE_12"):
				if mode == 1:
					copyfile("/tmp/startupmount/STARTUP_LINUX_%s_BOXMODE_1" % slot, "/tmp/startupmount/%s" %GetSTARTUPFile())
				else:
					copyfile("/tmp/startupmount/STARTUP_LINUX_%s_BOXMODE_12" % slot, "/tmp/startupmount/%s" %GetSTARTUPFile())
			elif fileExists("/tmp/startupmount/STARTUP_LINUX_4"):
				copyfile("/tmp/startupmount/STARTUP_LINUX_%s" % slot, "/tmp/startupmount/%s" %GetSTARTUPFile())

			message = _("Do you want to reboot now the image in slot %s?") %slot
			self.session.openWithCallback(self.restartImage,MessageBox, message, MessageBox.TYPE_YESNO, timeout=20)
		else:
			self.session.open(MessageBox, _("Multiboot ERROR! - no %s in boot partition.") %GetSTARTUPFile(), MessageBox.TYPE_INFO, timeout=20)

	def restartImage(self, answer):
		if answer is True:
			self.session.open(TryQuitMainloop, 2)
		else:
			self.close()

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
