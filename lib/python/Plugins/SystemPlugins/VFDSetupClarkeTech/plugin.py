from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection, ConfigSlider, getConfigListEntry

modelist = {"0": _("No"), "1": _("Yes")}
repeatlist = {"0": _("Continues"), "1": _("NOT"), "2": _("1X"), "3": _("2X"), "4": _("3X")}

config.plugins.VFDSetup = ConfigSubsection()
config.plugins.VFDSetup.mode = ConfigSelection(choices = modelist, default = "1")
config.plugins.VFDSetup.repeat = ConfigSelection(choices = repeatlist, default = "3")
config.plugins.VFDSetup.scrollspeed = ConfigInteger(default = 150)

class VFDSetupScreen(Screen, ConfigListScreen):
	skin = """
	<screen name="VFDSetupScreen" position="c-200,c-100" size="400,200" title="Display Setup">
		<widget name="config" position="c-175,c-75" size="350,150" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="c-145,e-45" zPosition="0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="c+5,e-45" zPosition="0" size="140,40" alphatest="on" />
		<widget name="ok" position="c-145,e-45" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="green" />
		<widget name="cancel" position="c+5,e-45" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="red" />
	</screen>"""

	def __init__(self, session):
		self.skin = VFDSetupScreen.skin
		Screen.__init__(self, session)

		from Components.ActionMap import ActionMap
		from Components.Button import Button

		self.setTitle(_("VFD Setup"))
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

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)

		mode = config.plugins.VFDSetup.mode.value
		repeat = config.plugins.VFDSetup.repeat.value
		scrollspeed = config.plugins.VFDSetup.scrollspeed.value

		self.mode = ConfigSelection(choices = modelist, default = mode)
		self.repeat = ConfigSelection(choices = repeatlist, default = repeat)
		self.scrollspeed = ConfigSlider(default = scrollspeed, increment = 10, limits = (0, 500))
		self.list.append(getConfigListEntry(_("Show Display Icons"), self.mode))
		self.list.append(getConfigListEntry(_("Repeat Display Message"), self.repeat))
		self.list.append(getConfigListEntry(_("scrolling Speed"), self.scrollspeed))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.setPreviewSettings()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setPreviewSettings()

	def setPreviewSettings(self):
		applySettings(int(self.mode.value), int(self.repeat.value), int(self.scrollspeed.value))

	def keyGo(self):
		config.plugins.VFDSetup.mode.value = self.mode.value
		config.plugins.VFDSetup.repeat.value = self.repeat.value
		config.plugins.VFDSetup.scrollspeed.value = int(self.scrollspeed.value)
		config.plugins.VFDSetup.save()
		self.close()

	def keyCancel(self):
		setConfiguredSettings()
		self.close()

def applySettings(mode, repeat, scrollspeed):
	try:
		file = open("/proc/stb/lcd/show_symbols", "w")
		file.write('%d' % mode)
		file.close()
		file = open("/proc/stb/lcd/scroll_repeats", "w")
		file.write('%d' % repeat)
		file.close()
		file = open("/proc/stb/lcd/scroll_delay", "w")
		file.write('%d' % scrollspeed)
		file.close()
	except:
		return

def setConfiguredSettings():
	applySettings(int(config.plugins.VFDSetup.mode.value), int(config.plugins.VFDSetup.repeat.value), int(config.plugins.VFDSetup.scrollspeed.value))

def main(menuid):
	if menuid != "system": 
		return [ ]

	return [(_("VFD Setup"), showVFDMenu, "vfd_setup",None)]

def showVFDMenu(session, **kwargs):
	session.open(VFDSetupScreen)

def startup(reason, **kwargs):
	setConfiguredSettings()

def Plugins(**kwargs):
	from os import path
	if path.exists("/proc/stb/lcd/scroll_delay"):
		from Plugins.Plugin import PluginDescriptor
		return [PluginDescriptor(name = "VFD setup", description = _("Adjust display scrolling and symbols"), where = PluginDescriptor.WHERE_MENU, fnc = main),
					PluginDescriptor(name = "VFD setup", description = "", where = PluginDescriptor.WHERE_SESSIONSTART, fnc = startup)]
	return []
