from Screens.Screen import Screen
from Components.config import configfile , config, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.SystemInfo import SystemInfo
from os import path

class OSDSetup(Screen, ConfigListScreen):
	skin = """
	<screen position="0,0" size="e,e" backgroundColor="blue">
		<widget name="config" position="c-175,c-75" size="350,150" foregroundColor="black" backgroundColor="blue" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="c-145,e-100" zPosition="0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="c+5,e-100" zPosition="0" size="140,40" alphatest="on" />
		<widget name="ok" position="c-145,e-100" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="green" />
		<widget name="cancel" position="c+5,e-100" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="red" />
	</screen>"""

	def __init__(self, session):
		self.skin = OSDSetup.skin
		Screen.__init__(self, session)
		Screen.setTitle(self, _("OSD Setup"))

		from Components.ActionMap import ActionMap
		from Components.Button import Button

		self["ok"] = Button(_("OK"))
		self["cancel"] = Button(_("Cancel"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"ok": self.keySave,
			"save": self.keySave,
			"cancel": self.keyCancel,
			"green": self.keySave,
			"red": self.keyCancel,
		}, -2)

		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		if SystemInfo["CanChangeOsdAlpha"] == True:
			self.list.append(getConfigListEntry(_("OSD visibility"), config.osd.alpha))
		if SystemInfo["CanChangeOsdPosition"] == True:
			self.list.append(getConfigListEntry(_("left"), config.osd.dst_left))
			self.list.append(getConfigListEntry(_("width"), config.osd.dst_width))
			self.list.append(getConfigListEntry(_("top"), config.osd.dst_top))
			self.list.append(getConfigListEntry(_("height"), config.osd.dst_height))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

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
		self.setPreviewPosition()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setPreviewPosition()

	def setPreviewPosition(self):
		setPosition(int(config.osd.dst_left.value), int(config.osd.dst_width.value), int(config.osd.dst_top.value), int(config.osd.dst_height.value))

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
	if dst_left + dst_width > 720:
		dst_width = 720 - dst_left
	if dst_top + dst_height > 576:
		dst_height = 576 - dst_top
	try:
		file = open("/proc/stb/fb/dst_left", "w")
		file.write('%X' % dst_left)
		file.close()
		file = open("/proc/stb/fb/dst_width", "w")
		file.write('%X' % dst_width)
		file.close()
		file = open("/proc/stb/fb/dst_top", "w")
		file.write('%X' % dst_top)
		file.close()
		file = open("/proc/stb/fb/dst_height", "w")
		file.write('%X' % dst_height)
		file.close()
	except:
		return

class OSD3DSetupScreen(Screen, ConfigListScreen):
	skin = """
	<screen position="c-200,c-100" size="400,200" title="OSD 3D setup">
		<widget name="config" position="c-175,c-75" size="350,150" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="c-145,e-45" zPosition="0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="c+5,e-45" zPosition="0" size="140,40" alphatest="on" />
		<widget name="ok" position="c-145,e-45" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="green" />
		<widget name="cancel" position="c+5,e-45" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="red" />
	</screen>"""

	def __init__(self, session):
		self.skin = OSD3DSetupScreen.skin
		Screen.__init__(self, session)

		from Components.ActionMap import ActionMap
		from Components.Button import Button

		self["ok"] = Button(_("OK"))
		self["cancel"] = Button(_("Cancel"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"ok": self.keySave,
			"save": self.keySave,
			"cancel": self.keyCancel,
			"green": self.keySave,
			"red": self.keyCancel,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)
		self.list.append(getConfigListEntry(_("3d mode"), config.osd.threeDmode))
		self.list.append(getConfigListEntry(_("Depth"), config.osd.threeDznorm))
		self.list.append(getConfigListEntry(_("Show in extensions list ?"), config.osd.show3dextensions))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

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

def setConfiguredPosition():
	setPosition(int(config.osd.dst_left.value), int(config.osd.dst_width.value), int(config.osd.dst_top.value), int(config.osd.dst_height.value))

def setConfiguredSettings():
	applySettings(config.osd.threeDmode.value, int(config.osd.threeDznorm.value))

def isCanChangeOsdPositionSupported():
	if path.exists("/proc/stb/fb/dst_left"):
		return True
	return False

def isCanChangeOsdAlphaSupported():
	if path.exists("/proc/stb/video/alpha"):
		return True
	return False

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
