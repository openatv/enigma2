from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.config import config, configfile, ConfigSubsection, getConfigListEntry, ConfigSelectionNumber, ConfigSelection, ConfigSlider, ConfigYesNo, NoSave, ConfigNumber, ConfigText
from Components.ConfigList import ConfigListScreen
from Components.SystemInfo import SystemInfo
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.Console import Console
from Components.Language import language
from Tools.Directories import fileCheck, fileExists
from enigma import getDesktop
from os import access, R_OK

from boxbranding import getBoxType

def getFilePath(setting):
	return "/proc/stb/fb/dst_%s" % (setting)

def setPositionParameter(parameter, configElement):
	f = open(getFilePath(parameter), "w")
	f.write('%08X\n' % configElement.value)
	f.close()
	if fileExists(getFilePath("apply")):
		f = open(getFilePath("apply"), "w")
		f.write('1')
		f.close()

	#	InitOsd is now the 2nd Initialisation routine and is called after LCD iniialisation
	#	by mytest.py .. this was historically the case before the 3D modification
	#	It is important that this call remains in mytest.py at this position!

def InitOsd():
	SystemInfo["CanChangeOsdAlpha"] = access('/proc/stb/video/alpha', R_OK) and True or False
	SystemInfo["CanChangeOsdPosition"] = access('/proc/stb/fb/dst_left', R_OK) and True or False
	SystemInfo["OsdSetup"] = SystemInfo["CanChangeOsdPosition"]

	if SystemInfo["CanChangeOsdAlpha"] == True or SystemInfo["CanChangeOsdPosition"] == True:
		SystemInfo["OsdMenu"] = True
	else:
		SystemInfo["OsdMenu"] = False

	def setOSDLeft(configElement):
		if SystemInfo["CanChangeOsdPosition"]:
			setPositionParameter("left", configElement)
	config.osd.dst_left.addNotifier(setOSDLeft)

	def setOSDWidth(configElement):
		if SystemInfo["CanChangeOsdPosition"]:
			setPositionParameter("width", configElement)
	config.osd.dst_width.addNotifier(setOSDWidth)

	def setOSDTop(configElement):
		if SystemInfo["CanChangeOsdPosition"]:
			setPositionParameter("top", configElement)
	config.osd.dst_top.addNotifier(setOSDTop)

	def setOSDHeight(configElement):
		if SystemInfo["CanChangeOsdPosition"]:
			setPositionParameter("height", configElement)
	config.osd.dst_height.addNotifier(setOSDHeight)
	print '[UserInterfacePositioner] Setting OSD position: %s %s %s %s' %  (config.osd.dst_left.value, config.osd.dst_width.value, config.osd.dst_top.value, config.osd.dst_height.value)

	def setOSDAlpha(configElement):
		if SystemInfo["CanChangeOsdAlpha"]:
			print '[UserInterfacePositioner] Setting OSD alpha:', str(configElement.value)
			config.av.osd_alpha.setValue(configElement.value)
			f = open("/proc/stb/video/alpha", "w")
			f.write(str(configElement.value))
			f.close()
	config.osd.alpha.addNotifier(setOSDAlpha)


	#	InitOsd3D is the 1st Initialisation routine and is called by mytest.py to enable 3D setup by Videomode.py
	#	It is important that this call remains in mytest.py at this position! 

def InitOsd3D():
	SystemInfo["CanChange3DOsd"] = (access('/proc/stb/fb/3dmode', R_OK) or access('/proc/stb/fb/primary/3d', R_OK)) and True or False

	def languageNotifier(configElement):
		language.activateLanguage(configElement.value)

	config.osd = ConfigSubsection()
	config.osd.language = ConfigText(default = "en_GB")
	config.osd.language.addNotifier(languageNotifier)
	config.osd.dst_left = ConfigSelectionNumber(default = 0, stepwidth = 1, min = 0, max = 720, wraparound = False)
	config.osd.dst_width = ConfigSelectionNumber(default = 720, stepwidth = 1, min = 0, max = 720, wraparound = False)
	config.osd.dst_top = ConfigSelectionNumber(default = 0, stepwidth = 1, min = 0, max = 576, wraparound = False)
	config.osd.dst_height = ConfigSelectionNumber(default = 576, stepwidth = 1, min = 0, max = 576, wraparound = False)
	config.osd.alpha = ConfigSelectionNumber(default = 255, stepwidth = 1, min = 0, max = 255, wraparound = False)
	config.av.osd_alpha = NoSave(ConfigNumber(default = 255))
	config.osd.threeDmode = ConfigSelection([("off", _("Off")), ("auto", _("Auto")), ("sidebyside", _("Side by Side")),("topandbottom", _("Top and Bottom"))], "auto")
	config.osd.threeDznorm = ConfigSlider(default = 50, increment = 1, limits = (0, 100))
	config.osd.show3dextensions = ConfigYesNo(default = False)

	def set3DMode(configElement):
		if SystemInfo["CanChange3DOsd"] and getBoxType() not in ('spycat'):
			print '[UserInterfacePositioner] Setting 3D mode:',configElement.value
			file3d = fileCheck('/proc/stb/fb/3dmode') or fileCheck('/proc/stb/fb/primary/3d')
			f = open(file3d, "w")
			f.write(configElement.value)
			f.close()
	config.osd.threeDmode.addNotifier(set3DMode)

	def set3DZnorm(configElement):
		if SystemInfo["CanChange3DOsd"] and getBoxType() not in ('spycat'):
			print '[UserInterfacePositioner] Setting 3D depth:',configElement.value
			f = open("/proc/stb/fb/znorm", "w")
			f.write('%d' % int(configElement.value))
			f.close()
	config.osd.threeDznorm.addNotifier(set3DZnorm)

class UserInterfacePositioner(Screen, ConfigListScreen):
	def __init__(self, session, menu_path=""):
		Screen.__init__(self, session)
		screentitle = _("Position Setup")
		if config.usage.show_menupath.value == 'large':
			menu_path += screentitle
			title = menu_path
			self.setup_title = title
			self["menu_path_compressed"] = StaticText("")
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			self.setup_title = screentitle
			self["menu_path_compressed"] = StaticText(menu_path + " >" if not menu_path.endswith(' / ') else menu_path[:-3] + " >" or "")
		else:
			title = screentitle
			self.setup_title = title
			self["menu_path_compressed"] = StaticText("")
		self.Console = Console()
		self["status"] = StaticText()
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText(_("Defaults"))

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
		if SystemInfo["CanChangeOsdAlpha"]:
			self.list.append(getConfigListEntry(_("User interface visibility"), config.osd.alpha, _("This option lets you adjust the transparency of the user interface")))
		if SystemInfo["CanChangeOsdPosition"]:
			self.list.append(getConfigListEntry(_("Move Left/Right"), config.osd.dst_left, _("Use the Left/Right buttons on your remote to move the user interface left/right")))
			self.list.append(getConfigListEntry(_("Width"), config.osd.dst_width, _("Use the Left/Right buttons on your remote to adjust the size of the user interface. Left button decreases the size, Right increases the size.")))
			self.list.append(getConfigListEntry(_("Move Up/Down"), config.osd.dst_top, _("Use the Left/Right buttons on your remote to move the user interface up/down")))
			self.list.append(getConfigListEntry(_("Height"), config.osd.dst_height, _("Use the Left/Right buttons on your remote to adjust the size of the user interface. Left button decreases the size, Right increases the size.")))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self.onLayoutFinish.append(self.layoutFinished)
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		if self.restoreService not in self.onClose:
			self.onClose.append(self.restoreService)
		self.selectionChanged()

	def selectionChanged(self):
		self["status"].setText(self["config"].getCurrent()[2])

	def layoutFinished(self):
		self.setTitle(_(self.setup_title))
		self.Console.ePopen('/usr/bin/showiframe /usr/share/enigma2/hd-testcard.mvi')

	def restoreService(self):
		try:
			serviceRef = self.session.nav.getCurrentlyPlayingServiceReference()
			self.session.nav.stopService()
			self.session.nav.playService(serviceRef)
		except:
			pass

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

	def setPreviewPosition(self):
		size_w = getDesktop(0).size().width()
		size_h = getDesktop(0).size().height()
		dsk_w = int(float(size_w)) / float(720)
		dsk_h = int(float(size_h)) / float(576)
		dst_left = int(config.osd.dst_left.value)
		dst_width = int(config.osd.dst_width.value)
		dst_top = int(config.osd.dst_top.value)
		dst_height = int(config.osd.dst_height.value)
		while dst_width + (dst_left / float(dsk_w)) >= 720.5 or dst_width + dst_left > 720:
			dst_width = int(dst_width) - 1
		while dst_height + (dst_top / float(dsk_h)) >= 576.5 or dst_height + dst_top > 576:
			dst_height = int(dst_height) - 1

		config.osd.dst_left.setValue(dst_left)
		config.osd.dst_width.setValue(dst_width)
		config.osd.dst_top.setValue(dst_top)
		config.osd.dst_height.setValue(dst_height)
		print '[UserInterfacePositioner] Setting OSD position: %s %s %s %s' %  (config.osd.dst_left.value, config.osd.dst_width.value, config.osd.dst_top.value, config.osd.dst_height.value)

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

class OSD3DSetupScreen(Screen, ConfigListScreen):
	def __init__(self, session, menu_path=""):
		Screen.__init__(self, session)
		screentitle = _("OSD 3D Setup")
		if config.usage.show_menupath.value == 'large':
			menu_path += screentitle
			title = menu_path
			self.setup_title = title
			self["menu_path_compressed"] = StaticText("")
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			self.setup_title = screentitle
			self["menu_path_compressed"] = StaticText(menu_path + " >" if not menu_path.endswith(' / ') else menu_path[:-3] + " >" or "")
		else:
			title = screentitle
			self.setup_title = title
			self["menu_path_compressed"] = StaticText("")
		self.skinName = "Setup"
		self["status"] = StaticText()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()

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
		self.list.append(getConfigListEntry(_("3D Mode"), config.osd.threeDmode, _("This option lets you choose the 3D mode")))
		self.list.append(getConfigListEntry(_("Depth"), config.osd.threeDznorm, _("This option lets you adjust the 3D depth")))
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
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			from Screens.MessageBox import MessageBox
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()
