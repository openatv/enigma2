from enigma import ePicLoad
from boxbranding import getBoxType
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ConfigList import ConfigListScreen
from Components.config import config, configfile, ConfigSubsection, ConfigSelection, getConfigListEntry
from Components.Pixmap import Pixmap
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN

from os import path as os_path

if getBoxType() == "beyonwizu4":
	modelist = [
		("507", _("Beyonwiz U4 (0xAE97)")),
		("509", _("Beyonwiz U4/T4/T2 (0x02F3)")),
		("508", _("Beyonwiz T2/T4 (0x02F2)")),
		("510", _("Beyonwiz T2/T4 (0x02F4)")),
		("506", _("Beyonwiz T3 (0xABCD)")),
		# ("16", _("Generic (0x00FF)")),
		]
	imagemap = {
		"506" : "ini5.png",
		"507" : "BeyonwizU4.png",
		"508" : "ini6.png",
		"509" : "BeyonwizU4.png",
		"510" : "ini6.png",
		}
else:
	modelist = [
		("0", _("All supported")),
		("5", _("Beyonwiz T3 (0xABCD)")),
		("6", _("Beyonwiz (0x02F2)")),
		("7", _("Beyonwiz (0x02F3)")),
		("8", _("Beyonwiz (0x02F4)")),
		("10", _("Beyonwiz U4 (0xAE97)")),
		# ("1", _("INI3000 (0x0932)")),
		# ("2", _("INI7000 (0x0831")),
		("3", _("HDx (0x0933)")),
		# ("4", _("MIRACLEBOX (0x02F9)")),
		# ("9", _("YHGD2580 (0x08F7)")),
	]
	imagemap = {
		"1" : "ini1.png",
		"2" : "ini2.png",
		"3" : "ini3.png",
		"4" : "ini4.png",
		"5" : "ini5.png",
		"6" : "ini6.png",
		"7" : "ini6.png",
		"8" : "ini6.png",
		"10" : "BeyonwizU4.png",
		}

config.plugins.RCSetup = ConfigSubsection()
config.plugins.RCSetup.mode = ConfigSelection(choices=modelist)

def applySettings():
	f = open("/proc/stb/ir/rc/type", "w")
	f.write("%d" % int(config.plugins.RCSetup.mode.value))
	f.close()

class RCSetupScreen(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Remote control code settings"))
		self.previewPath = ""

		self.list = []
		ConfigListScreen.__init__(self, self.list)

		self["key_red"] = Label(_("Exit"))
		self["key_green"] = Label(_("Save"))
		self["Preview"] = Pixmap()

		self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
			"ok": self.keyGo,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"green": self.keyGo,
			"red": self.keyCancel,
		}, -2)

		self.mode = ConfigSelection(choices=modelist, default=config.plugins.RCSetup.mode.value)
		self.list.append(getConfigListEntry(_("Remote"), self.mode))

		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self.grabLastGoodMode()

		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.showPic)
		self.current_sel = self["config"].getCurrent()[1]

		self.onLayoutFinish.append(self.layoutFinished)

	def showPic(self, picInfo=""):
		ptr = self.picload.getData()
		if ptr is not None:
			self["Preview"].instance.setPixmap(ptr.__deref__())
			self["Preview"].show()

	def layoutFinished(self):
		self.picload.setPara((self["Preview"].instance.size().width(), self["Preview"].instance.size().height(), 1.0, 1, 1, 1, "#FF000000"))
		self.loadPreview()

	def grabLastGoodMode(self):
		self.last_good = config.plugins.RCSetup.mode.value

	def keyGo(self):
		config.plugins.RCSetup.mode.value = self.mode.value
		applySettings()

		RC = config.plugins.RCSetup.mode.value
		if (RC) != self.last_good:
			from Screens.MessageBox import MessageBox
			self.session.openWithCallback(self.confirm, MessageBox, _("Is this remote OK?"), MessageBox.TYPE_YESNO, timeout=30, default=False)
		else:
			config.plugins.RCSetup.save()
			self.close()

	def confirm(self, confirmed):
		if not confirmed:
			config.plugins.RCSetup.mode.value = self.last_good
			applySettings()
		else:
			applySettings()
			config.plugins.RCSetup.mode.save()
			configfile.save()
			self.keySave()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.current_sel = self["config"].getCurrent()[1]
		self.loadPreview()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.current_sel = self["config"].getCurrent()[1]
		self.loadPreview()

	def keyCancel(self):
		applySettings()
		self.close()

	def loadPreview(self):
		root = "/usr/lib/enigma2/python/Plugins/SystemPlugins/RemoteControlCode/img/"
		pngpath = root + imagemap.get(self.current_sel.value, "other.png")

		if not os_path.exists(pngpath):
			pngpath = resolveFilename(SCOPE_ACTIVE_SKIN, "noprev.png")

		if self.previewPath != pngpath:
			self.previewPath = pngpath

		self.picload.startDecode(self.previewPath)

def main(session, **kwargs):
	session.open(RCSetupScreen)

def RemoteControlSetup(menuid, **kwargs):
	if menuid == "system":
		return [(_("Remote Control Code"), main, "remotecontrolcode", 50)]
	else:
		return []

def Plugins(**kwargs):
	if os_path.exists("/proc/stb/ir/rc/type"):
		applySettings()
		from Plugins.Plugin import PluginDescriptor
		return [PluginDescriptor(name=_("Remote Control Code"), where=PluginDescriptor.WHERE_MENU, needsRestart=False, fnc=RemoteControlSetup)]
	return []
