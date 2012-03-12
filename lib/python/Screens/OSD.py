from Screens.Screen import Screen
from Components.config import configfile , config, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.SystemInfo import SystemInfo
from Components.Sources.StaticText import StaticText
from os import path
from enigma import getDesktop

class OSDSetup(Screen, ConfigListScreen):
	skin = """
	<screen name="OSDSetup" position="c-250,c-200" size="500,400">
		<widget name="config" position="c-175,30" size="350,150" foregroundColor="white" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="c-230,e-50" zPosition="0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="c-70,e-50" zPosition="0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="c+90,e-50" zPosition="0" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="c-230,e-50" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="red" />
		<widget source="key_green" render="Label" position="c-70,e-50" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="green" />
		<widget source="key_yellow" render="Label" position="c+90,e-50" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="yellow" />
		<ePixmap pixmap="skin_default/div-h.png" position="c-250,e-100" zPosition="1" size="500,2" />
		<widget source="status" render="Label" position="c-200,e-90" size="400,30" zPosition="10" font="Regular;21" halign="center" valign="center" foregroundColor="white" transparent="1" />
	</screen>"""

	def __init__(self, session):
		self.skin = OSDSetup.skin
		Screen.__init__(self, session)
		self.setup_title = _("OSD Setup")

		from Components.ActionMap import ActionMap
		from Components.Sources.StaticText import StaticText

<<<<<<< HEAD
		self["status"] = StaticText()
=======
		self["satus"] = StaticText()
>>>>>>> parent of e788576... OSD: allow cancel to revert OSD to state before you messed with settings.
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText(_("Default"))

		self["actions"] = ActionMap(["ColorActions","SetupActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
				"yellow": self.keydefaults,
			}, -2)

		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		if SystemInfo["CanChangeOsdAlpha"] == True:
			self.list.append(getConfigListEntry(_("OSD visibility"), config.osd.alpha))
		if SystemInfo["CanChangeOsdPosition"] == True:
			self.list.append(getConfigListEntry(_("Move Left/Right"), config.osd.dst_left))
			self.list.append(getConfigListEntry(_("Width"), config.osd.dst_width))
			self.list.append(getConfigListEntry(_("Move Up/Down"), config.osd.dst_top))
			self.list.append(getConfigListEntry(_("Height"), config.osd.dst_height))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self.onLayoutFinish.append(self.layoutFinished)
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		self["status"].setText(_("Current value: ") + self.getCurrentValue())

	def layoutFinished(self):
		self.setTitle(_(self.setup_title))

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
		self.selectionChanged()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.setPreviewPosition()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setPreviewPosition()

	def keydefaults(self):
		setDefaults()
		self.setPreviewPosition()
		self["config"].l.setList(self.list)

	def setPreviewPosition(self):
		open("/proc/stb/video/alpha", "w").write(str(config.osd.alpha.value))
		size_w = getDesktop(0).size().width()
		size_h = getDesktop(0).size().height()
		dsk_w = int(float(size_w)) / float(720)
		dsk_h = int(float(size_h)) / float(576)
		while config.osd.dst_width.value + (int(config.osd.dst_left.value) / float(dsk_w)) >= 720.5 or config.osd.dst_width.value + config.osd.dst_left.value > 720:
			config.osd.dst_width.value = int(config.osd.dst_width.value) - 1
			config.osd.dst_width.save()
			configfile.save()
		while config.osd.dst_height.value + (int(config.osd.dst_top.value) / float(dsk_h)) >= 576.5 or config.osd.dst_height.value + config.osd.dst_top.value > 576:
			config.osd.dst_height.value = int(config.osd.dst_height.value) - 1
			config.osd.dst_height.save()
			configfile.save()
<<<<<<< HEAD

		setPosition(int(config.osd.dst_left.value), int(config.osd.dst_width.value), int(config.osd.dst_top.value), int(config.osd.dst_height.value))
=======
	
		setPosition(int(config.osd.dst_left.value), int(config.osd.dst_width.value), int(config.osd.dst_top.value), int(config.osd.dst_height.value))
		setAlpha(int(config.osd.alpha.value))
>>>>>>> parent of e788576... OSD: allow cancel to revert OSD to state before you messed with settings.

	def saveAll(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()

	# keySave and keyCancel are just provided in case you need them.
	# you have to call them by yourself.
	def keySave(self):
		self.saveAll()
		self.close()

	def cancelConfirm(self, result):
		if not result:
			return

		for x in self["config"].list:
			x[1].cancel()
		setConfiguredPosition()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			from Screens.MessageBox import MessageBox
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

def setPosition(dst_left, dst_width, dst_top, dst_height):
	try:
		file = open("/proc/stb/fb/dst_left", "w")
		file.write('%X' % dst_left)
		file.close()
		file = open("/proc/stb/fb/dst_top", "w")
		file.write('%X' % dst_top)
		file.close()
		file = open("/proc/stb/fb/dst_width", "w")
		file.write('%X' % dst_width)
		file.close()
		file = open("/proc/stb/fb/dst_height", "w")
		file.write('%X' % dst_height)
		file.close()
	except:
		return

<<<<<<< HEAD
def setDefaults():
	print'[OSD Setup] Set Defaults'
	config.osd.dst_left.value = 0
	config.osd.dst_width.value = 720
	config.osd.dst_top.value = 0
	config.osd.dst_height.value = 576
	config.osd.alpha.value = 255
=======
def setAlpha(alpha_value):
		open("/proc/stb/video/alpha", "w").write(str(alpha_value))
>>>>>>> parent of e788576... OSD: allow cancel to revert OSD to state before you messed with settings.

class OSD3DSetupScreen(Screen, ConfigListScreen):
	skin = """
	<screen position="c-200,c-100" size="400,200" title="OSD 3D setup">
		<widget name="config" position="c-175,c-75" size="350,150" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="c-145,e-45" zPosition="0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="c+5,e-45" zPosition="0" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="c-145,e-45" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="red" />
		<widget source="key_green" render="Label" position="c+5,e-45" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="green" />
	</screen>"""

	def __init__(self, session):
		self.skin = OSD3DSetupScreen.skin
		Screen.__init__(self, session)
		self.setup_title = _("OSD 3D Setup")

		from Components.ActionMap import ActionMap
		from Components.Sources.StaticText import StaticText

<<<<<<< HEAD
		self["status"] = StaticText()
=======
		self["satus"] = StaticText()
>>>>>>> parent of e788576... OSD: allow cancel to revert OSD to state before you messed with settings.
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))

		self["actions"] = ActionMap(["SetupActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
			}, -2)

		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		self.list.append(getConfigListEntry(_("3D Mode"), config.osd.threeDmode))
		self.list.append(getConfigListEntry(_("Depth"), config.osd.threeDznorm))
		if config.misc.boxtype.value == 'gb800se' or config.misc.boxtype.value == 'gb800solo':
			self.list.append(getConfigListEntry(_("Set Mode"), config.osd.threeDsetmode))
		self.list.append(getConfigListEntry(_("Show in extensions list ?"), config.osd.show3dextensions))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_(self.setup_title))

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.setPreviewSettings()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setPreviewSettings()

	def setPreviewSettings(self):
		applySettings(config.osd.threeDmode.value, int(config.osd.threeDznorm.value) - 50)

	def saveAll(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()

	# keySave and keyCancel are just provided in case you need them.
	# you have to call them by yourself.
	def keySave(self):
		self.saveAll()
		self.close()

	def cancelConfirm(self, result):
		if not result:
			return

		for x in self["config"].list:
			x[1].cancel()
		setConfiguredPosition()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			from Screens.MessageBox import MessageBox
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()


def applySettings(mode, znorm):
	try:
		file = open("/proc/stb/fb/3dmode", "w")
		file.write(mode)
		file.close()
		file = open("/proc/stb/fb/znorm", "w")
		file.write('%d' % znorm)
		file.close()
	except:
		return
<<<<<<< HEAD
		
def applySettings2(mode, znorm, setmode):
	try:
		if setmode == "mode1":
			file = open("/proc/stb/fb/3dmode", "w")
			file.write(mode)
			file.close()
			file = open("/proc/stb/fb/znorm", "w")
			file.write('%d' % znorm)
			file.close()
		elif setmode == "mode2":
			file = open("/proc/stb/fb/primary/3d","w")
			if mode == "sidebyside" :
				mode = "sbs"
			elif mode == "topandbottom":
				mode = "tab"
			file.write(mode)
			file.close()
			file = open("/proc/stb/fb/primary/zoffset","w")
			file.write('%d' % znorm)
			file.close()
	except:
		return		
=======
>>>>>>> parent of e788576... OSD: allow cancel to revert OSD to state before you messed with settings.

def setConfiguredPosition():
	setPosition(int(config.osd.dst_left.value), int(config.osd.dst_width.value), int(config.osd.dst_top.value), int(config.osd.dst_height.value))

def setConfiguredSettings():
	if config.misc.boxtype.value == 'gb800se' or config.misc.boxtype.value == 'gb800solo':
		applySettings2(config.osd.threeDmode.value, int(config.osd.threeDznorm.value), config.osd.threeDsetmode.value)
	else:
		applySettings(config.osd.threeDmode.value, int(config.osd.threeDznorm.value))

def isCanChangeOsdPositionSupported():
	if path.exists("/proc/stb/fb/dst_left"):
		return True
	return False

def isCanChangeOsdAlphaSupported():
<<<<<<< HEAD
	if path.exists("/proc/stb/video/alpha"):
		return True
	return False
=======
	try:
		can_osd_alpha = open("/proc/stb/video/alpha", "r") and True or False
	except:
		can_osd_alpha = False
	return can_osd_alpha
>>>>>>> parent of e788576... OSD: allow cancel to revert OSD to state before you messed with settings.

def isCanChange3DOsdSupported():
	if path.exists("/proc/stb/fb/3dmode"):
		return True
	return False

def isOsdSetupSupported():
	if SystemInfo["CanChangeOsdAlpha"] == True or SystemInfo["CanChangeOsdPosition"] == True:
		return True
	return False

def isOsdMenuSupported():
	if SystemInfo["CanChangeOsdAlpha"] == True or SystemInfo["CanChangeOsdPosition"] == True:
		return True
	return False

SystemInfo["CanChange3DOsd"] = isCanChange3DOsdSupported()
SystemInfo["CanChangeOsdAlpha"] = isCanChangeOsdAlphaSupported()
SystemInfo["CanChangeOsdPosition"] = isCanChangeOsdPositionSupported()
SystemInfo["OsdSetup"] = isOsdSetupSupported()
SystemInfo["OsdMenu"] = isOsdMenuSupported()
