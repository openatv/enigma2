from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.config import config, configfile, ConfigSubsection, ConfigSelectionNumber, ConfigSelection, ConfigSlider, ConfigYesNo, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.SystemInfo import SystemInfo
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.Label import Label
from os import path
from enigma import getDesktop, getBoxType

class UserInterfacePositioner(Screen, ConfigListScreen):
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
		self.setup_title = _("OSD Position Setup")
		self["status"] = StaticText()
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText(_("Defaults"))
		self["info1"] = Label(_("Use arrows Up/Down to select"))
		self["info2"] = Label(_("Use arrows Left/Right to adjust"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
				"left": self.keyLeft,
				"right": self.keyRight,
				"yellow": self.keyDefault,
			}, -2)

		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		if SystemInfo["CanChangeOsdAlpha"] == True:
			self.list.append(getConfigListEntry(_("OSD visibility"), config.osd.alpha, _("This option lets you adjust the transparency of the OSD")))
		if SystemInfo["CanChangeOsdPosition"] == True:
			self.list.append(getConfigListEntry(_("Move Left/Right"), config.osd.dst_left, _("Use the Left/Right buttons on your remote to move the OSD left/right")))
			self.list.append(getConfigListEntry(_("Width"), config.osd.dst_width, _("Use the Left/Right buttons on your remote to adjust the size of the OSD. Left button decreases the size, Right increases the size.")))
			self.list.append(getConfigListEntry(_("Move Up/Down"), config.osd.dst_top, _("Use the Left/Right buttons on your remote to move the OSD up/down")))
			self.list.append(getConfigListEntry(_("Height"), config.osd.dst_height, _("Use the Left/Right buttons on your remote to adjust the size of the OSD. Left button decreases the size, Right increases the size.")))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self.onLayoutFinish.append(self.layoutFinished)
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		self["status"].setText(self["config"].getCurrent()[2])

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
		self.setPreviewPosition()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setPreviewPosition()

	def keyDefault(self):
		config.osd.alpha.setValue(255)

		config.osd.dst_left.setValue(0)
		config.osd.dst_width.setValue(720)
		config.osd.dst_top.setValue(0)
		config.osd.dst_height.setValue(576)

		self.keyLeft()

	def setPreviewPosition(self):
		size_w = getDesktop(0).size().width()
		size_h = getDesktop(0).size().height()
		dsk_w = int(float(size_w)) / float(720)
		dsk_h = int(float(size_h)) / float(576)
		dst_left = int(config.osd.dst_left.getValue())
		dst_width = int(config.osd.dst_width.getValue())
		dst_top = int(config.osd.dst_top.getValue())
		dst_height = int(config.osd.dst_height.getValue())
		while dst_width + (dst_left / float(dsk_w)) >= 720.5 or dst_width + dst_left > 720:
			dst_width = int(dst_width) - 1
		while dst_height + (dst_top / float(dsk_h)) >= 576.5 or dst_height + dst_top > 576:
			dst_height = int(dst_height) - 1

		config.osd.dst_left.setValue(dst_left)
		config.osd.dst_width.setValue(dst_width)
		config.osd.dst_top.setValue(dst_top)
		config.osd.dst_height.setValue(dst_height)

		setPosition(config.osd.dst_left.getValue(), config.osd.dst_width.getValue(), config.osd.dst_top.getValue(), config.osd.dst_height.getValue())
		setAlpha(config.osd.alpha.getValue())

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
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), default = False)
		else:
			self.close()

	def run(self):
		config.osd.dst_left.save()
		config.osd.dst_width.save()
		config.osd.dst_top.save()
		config.osd.dst_height.save()
		configfile.save()
		self.close()

def setPosition(dst_left, dst_width, dst_top, dst_height):
	try:
		print 'Setting OSD position:' + str(dst_left) + " " + str(dst_width) + " " + str(dst_top) + " " + str(dst_height)
		open("/proc/stb/fb/dst_left", "w").write('%X' % int(dst_left))
		open("/proc/stb/fb/dst_width", "w").write('%X' % int(dst_width))
		open("/proc/stb/fb/dst_top", "w").write('%X' % int(dst_top))
		open("/proc/stb/fb/dst_height", "w").write('%X' % int(dst_height))
	except:
		return

def setAlpha(alpha_value):
	try:
		print 'Setting OSD alpha:', str(alpha_value)
		open("/proc/stb/video/alpha", "w").write(str(alpha_value))
	except:
		return

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
		self["status"] = StaticText()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["info1"] = Label(_("Use arrows Up/Down to select"))
		self["info2"] = Label(_("Use arrows Left/Right to adjust"))

		self["actions"] = ActionMap(["SetupActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
			}, -2)

		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		self.list.append(getConfigListEntry(_("3D Mode"), config.osd.threeDmode, _("This option lets you choose the 3D mode")))
		self.list.append(getConfigListEntry(_("Depth"), config.osd.threeDznorm, _("This option lets you adjust the 3D depth")))
		if getBoxType() == 'gb800se' or getBoxType() == 'gb800solo' or getBoxType() == 'gb800ue':
			self.list.append(getConfigListEntry(_("Set Mode"), config.osd.threeDsetmode, _("This option lets you adjust the 3D mode")))
		self.list.append(getConfigListEntry(_("Show in extensions list ?"), config.osd.show3dextensions, _("This option lets you show the option in the extension screen")))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self.onLayoutFinish.append(self.layoutFinished)
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
 		self["status"].setText(self["config"].getCurrent()[2])

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
		applySettings(config.osd.threeDmode.getValue(), int(config.osd.threeDznorm.getValue()) - 50)

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
		print 'Setting 3D mode:',mode
		open("/proc/stb/fb/3dmode", "w").write(mode)
		print 'Setting 3D depth:',znorm
		open("/proc/stb/fb/znorm", "w").write('%d' % znorm)
	except:
		return		

def applySettings2(mode, znorm, setmode):
	try:
		if setmode == "mode1":
			print 'Setting 3D mode:',mode
			open("/proc/stb/fb/3dmode", "w").write(mode)
			print 'Setting 3D depth:',znorm
			open("/proc/stb/fb/znorm", "w").write('%d' % znorm)
		elif setmode == "mode2":
			if mode == "sidebyside" :
				mode = "sbs"
			elif mode == "topandbottom":
				mode = "tab"
			print 'Setting primary 3D mode:',mode	
			open("/proc/stb/fb/primary/3d", "w").write(mode)
			print 'Setting zoffset 3D mode:',znorm
			open("/proc/stb/fb/primary/zoffset", "w").write('%d' % znorm)
	except:
		return			

def setConfiguredPosition():
	if SystemInfo["CanChangeOsdPosition"]:
		setPosition(int(config.osd.dst_left.getValue()), int(config.osd.dst_width.getValue()), int(config.osd.dst_top.getValue()), int(config.osd.dst_height.getValue()))

def setConfiguredAplha():
	if SystemInfo["CanChangeOsdAlpha"]:
		setAlpha(int(config.osd.alpha.getValue()))

def setConfiguredSettings():
	if SystemInfo["CanChange3DOsd"]:
		if getBoxType() == 'gb800se' or getBoxType() == 'gb800solo' or getBoxType() == 'gb800ue':
			applySettings2(config.osd.threeDmode.getValue(), int(config.osd.threeDznorm.getValue()), config.osd.threeDsetmode.getValue())
		else:
			applySettings(config.osd.threeDmode.getValue(), int(config.osd.threeDznorm.getValue()))

def InitOsd():
	try:
		SystemInfo["CanChange3DOsd"] = (open("/proc/stb/fb/3dmode", "r") or open("/proc/stb/fb/primary/3d", "r")) and True or False
	except:
		SystemInfo["CanChange3DOsd"] = False
	try:
		SystemInfo["CanChangeOsdAlpha"] = open("/proc/stb/video/alpha", "r") and True or False
	except:
		SystemInfo["CanChangeOsdAlpha"] = False
	try:	
		SystemInfo["CanChangeOsdPosition"] = open("/proc/stb/fb/dst_left", "r") and True or False
	except:
		SystemInfo["CanChangeOsdPosition"] = False
	SystemInfo["OsdSetup"] = SystemInfo["CanChangeOsdPosition"]
	if SystemInfo["CanChangeOsdAlpha"] == True or SystemInfo["CanChangeOsdPosition"] == True:
		SystemInfo["OsdMenu"] = True
	else:
		SystemInfo["OsdMenu"] = False
