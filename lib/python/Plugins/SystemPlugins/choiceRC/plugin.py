#  ET-View RCSetup version 1.2
#  Remote Controller Setup (RCSetup) 
# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection, ConfigSlider, getConfigListEntry
from os import path as os_path, chmod as os_chmod, unlink as os_unlink, system as os_system

modelist = {"5": _("ET9000/ET9100"), "4": _("DMM/DMM ADV"), "7": _("ET5000/ET6000"), "11": _("ET9200/ET9500") }

config.plugins.RCSetup = ConfigSubsection()
from os import system as os_system
file = open("/proc/stb/ir/rc/type", "r")
text=file.read()
file.close()
temp = int(text)
if temp == 11:
	config.plugins.RCSetup.mode = ConfigSelection(choices = modelist, default = "11")
elif temp == 7:
	config.plugins.RCSetup.mode = ConfigSelection(choices = modelist, default = "7")
elif temp == 5:
	config.plugins.RCSetup.mode = ConfigSelection(choices = modelist, default = "5")
elif temp == 4:
	config.plugins.RCSetup.mode = ConfigSelection(choices = modelist, default = "4")

class RCSetupScreen(Screen, ConfigListScreen):
	skin = """
	<screen position="c-200,c-100" size="400,200" title="Remote setup">
		<widget name="config" position="c-175,c-75" size="350,150" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="c-145,e-45" zPosition="0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="c+5,e-45" zPosition="0" size="140,40" alphatest="on" />
		<widget name="ok" position="c-145,e-45" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="green" />
		<widget name="cancel" position="c+5,e-45" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="red" />
	</screen>"""

	def __init__(self, session):
		self.skin = RCSetupScreen.skin
		Screen.__init__(self, session)

		from Components.ActionMap import ActionMap
		from Components.Button import Button

		self["ok"] = Button(_("OK"))
		self["cancel"] = Button(_("Cancel"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"ok": self.keyGo,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"green": self.keyGo,
			"red": self.keyCancel,
		}, -2)
		self.createSetup()
		self.grabLastGoodMode()


	def grabLastGoodMode(self):
		mode = config.plugins.RCSetup.mode.value
		self.last_good = (mode)

	def createSetup(self):
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)
		mode = config.plugins.RCSetup.mode.value
		self.mode = ConfigSelection(choices = modelist, default = mode)
		self.list.append(getConfigListEntry(_("Remote"), self.mode))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

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
		if tmp == 5:
			self.removeFile()
		elif tmp == 4:
			self.createFile()
		elif tmp == 6:
			self.createFile()
		elif tmp == 7:
			self.createFile()
		elif tmp == 11:
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

	def keyRight(self):
		ConfigListScreen.keyRight(self)

	def keyCancel(self):
		self.applySettings()
		self.close()

	def applySettings(self):
		file = open("/proc/stb/ir/rc/type", "r")
		lines = file.readlines()
		file.close()
		if int(lines[0]) != int(config.plugins.RCSetup.mode.value):
			try:
				file = open("/proc/stb/ir/rc/type", "w")
				file.write('%d' % int(config.plugins.RCSetup.mode.value))
				file.close()
			except:
				return

def main(session, **kwargs):
	session.open(RCSetupScreen)

def startup(reason, **kwargs):
	return

def Plugins(**kwargs):
	if os_path.exists("/proc/stb/ir/rc/type"):
		from Plugins.Plugin import PluginDescriptor
		return [PluginDescriptor(name = "Remote Setup", description = _("Choice remote"), where = PluginDescriptor.WHERE_PLUGINMENU, fnc = main),
					PluginDescriptor(name = "Remote Setup", description = "", where = PluginDescriptor.WHERE_SESSIONSTART, fnc = startup)]
	return []