from enigma import ePicLoad

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection, ConfigSlider, getConfigListEntry
from Components.Pixmap import Pixmap
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN

from os import path as os_path, chmod as os_chmod, unlink as os_unlink, system as os_system

modelist = {"0": _("Auto"), 
	    "1": _("INI3000"), 
	    "2": _("INI7000"), 
	    "3": _("HDx"), 
	    "4": _("MIRACLEBOX"), 
	    "5": _("XPEED LX"), 
	    "6": _("DUIA5200I"), 
	    "7": _("DUIA5200I_1"), 
	    "8": _("DUIA5200I_2")}

config.plugins.RCSetup = ConfigSubsection()
from os import system as os_system
file = open("/proc/stb/ir/rc/type", "r")
text=file.read()
file.close()
temp = int(text)

if temp == 8:
	config.plugins.RCSetup.mode = ConfigSelection(choices = modelist, default = "8")
elif temp == 7:
	config.plugins.RCSetup.mode = ConfigSelection(choices = modelist, default = "7")
elif temp == 6:
	config.plugins.RCSetup.mode = ConfigSelection(choices = modelist, default = "6")
elif temp == 5:
	config.plugins.RCSetup.mode = ConfigSelection(choices = modelist, default = "5")
elif temp == 4:
	config.plugins.RCSetup.mode = ConfigSelection(choices = modelist, default = "4")
elif temp == 3:
	config.plugins.RCSetup.mode = ConfigSelection(choices = modelist, default = "3")
elif temp == 2:
	config.plugins.RCSetup.mode = ConfigSelection(choices = modelist, default = "2")
elif temp == 1:
	config.plugins.RCSetup.mode = ConfigSelection(choices = modelist, default = "1")
elif temp == 0:
	config.plugins.RCSetup.mode = ConfigSelection(choices = modelist, default = "0")
	
	
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

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"ok": self.keyGo,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"green": self.keyGo,
			"red": self.keyCancel,
		}, -2)

		self.mode = ConfigSelection(choices = modelist, default = config.plugins.RCSetup.mode.value)
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
		self.picload.setPara((self["Preview"].instance.size().width(), self["Preview"].instance.size().height(), 0, 0, 1, 1, "#00000000"))
		self.loadPreview()
		
	def grabLastGoodMode(self):
		self.last_good = config.plugins.RCSetup.mode.value

	def keyGo(self):
		config.plugins.RCSetup.mode.value = self.mode.value
		self.applySettings()

		RC = config.plugins.RCSetup.mode.value
		if (RC) != self.last_good:
			from Screens.MessageBox import MessageBox
			self.session.openWithCallback(self.confirm, MessageBox, _("Is this remote ok?"), MessageBox.TYPE_YESNO, timeout = 10, default = False)
		else:
			config.plugins.RCSetup.save()
			self.close()

	def confirm(self, confirmed):
		if not confirmed:
			config.plugins.RCSetup.mode.value = self.last_good[0]
			self.applySettings()
		else:
			self.installHelper()
			self.applySettings()
			self.keySave()

	def installHelper(self):
		tmp = int(config.plugins.RCSetup.mode.value)
		if tmp == 0:
			self.createFile()
		elif tmp == 1:
			self.createFile()
		elif tmp == 2:
			self.createFile()
		elif tmp == 3:
			self.createFile()
		elif tmp == 4:
			self.createFile()
		elif tmp == 5:
			self.createFile()
		elif tmp == 6:
			self.createFile()
		elif tmp == 7:
			self.createFile()
		elif tmp == 8:
			self.createFile()

	def createFile(self):
		file = open("/etc/rc3.d/S30rcsetup", "w")
		m = 'echo ' + config.plugins.RCSetup.mode.value + ' > /proc/stb/ir/rc/type'
		file.write(m)
		file.close()
		os_chmod("/etc/rc3.d/S30rcsetup", 0755)

	def removeFile(self):
		if os_path.exists("/etc/rc3.d/S30rcsetup"):
			os_unlink("/etc/rc3.d/S30rcsetup")

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.current_sel = self["config"].getCurrent()[1]
		self.loadPreview()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.current_sel = self["config"].getCurrent()[1]
		self.loadPreview()

	def keyCancel(self):
		self.applySettings()
		self.close()

	def loadPreview(self):
		root = "/usr/lib/enigma2/python/Plugins/SystemPlugins/RemoteControlCode/img/ini"
		pngpath = root +  self.current_sel.value + "/rc.png"

		if not os_path.exists(pngpath):
			pngpath = resolveFilename(SCOPE_ACTIVE_SKIN, "noprev.png")

		if self.previewPath != pngpath:
			self.previewPath = pngpath

		self.picload.startDecode(self.previewPath)
		
	def applySettings(self):
		file = open("/proc/stb/ir/rc/type", "r")
		lines = file.readlines()
		file.close()
		if int(lines[0]) != int(config.plugins.RCSetup.mode.value):
			try:
				cmd = 'echo ' + config.plugins.RCSetup.mode.value + ' > /proc/stb/ir/rc/type'
				os_system(cmd)
			except:
				return

def main(session, **kwargs):
	session.open(RCSetupScreen)

def RemoteControlSetup(menuid, **kwargs):
	if menuid == "system":
		return [(_("Remote Control Code"), main, "remotecontrolcode", 50)]
	else:
		return []

def Plugins(**kwargs):
	if os_path.exists("/proc/stb/ir/rc/type"):
		from Plugins.Plugin import PluginDescriptor
		return [PluginDescriptor(name=_("Remote Control Code"), where=PluginDescriptor.WHERE_MENU, needsRestart = False, fnc=RemoteControlSetup)]
	return []
