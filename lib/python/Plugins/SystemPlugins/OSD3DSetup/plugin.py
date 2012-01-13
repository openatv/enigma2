from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection, ConfigSlider, getConfigListEntry

modelist = {"off": _("Off"), "auto": _("Auto"), "sidebyside": _("Side by Side"), "topandbottom": _("Top and Bottom")}

config.plugins.OSD3DSetup = ConfigSubsection()
config.plugins.OSD3DSetup.mode = ConfigSelection(choices = modelist, default = "auto")
config.plugins.OSD3DSetup.znorm = ConfigInteger(default = 0)

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

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
			"ok": self.keyGo,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"green": self.keyGo,
			"red": self.keyCancel,
			"menu": self.closeRecursive,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)

		mode = config.plugins.OSD3DSetup.mode.value
		znorm = config.plugins.OSD3DSetup.znorm.value

		self.mode = ConfigSelection(choices = modelist, default = mode)
		self.znorm = ConfigSlider(default = znorm + 50, increment = 1, limits = (0, 100))
		self.list.append(getConfigListEntry(_("3d mode"), self.mode))
		self.list.append(getConfigListEntry(_("Depth"), self.znorm))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.setPreviewSettings()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setPreviewSettings()

	def setPreviewSettings(self):
		applySettings(self.mode.value, int(self.znorm.value) - 50)

	def keyGo(self):
		config.plugins.OSD3DSetup.mode.value = self.mode.value
		config.plugins.OSD3DSetup.znorm.value = int(self.znorm.value) - 50
		config.plugins.OSD3DSetup.save()
		self.close()

	def keyCancel(self):
		setConfiguredSettings()
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

def setConfiguredSettings():
	applySettings(config.plugins.OSD3DSetup.mode.value, int(config.plugins.OSD3DSetup.znorm.value))

def main(session, **kwargs):
	session.open(OSD3DSetupScreen)

def startup(reason, **kwargs):
	setConfiguredSettings()

def Plugins(**kwargs):
	from os import path
	if path.exists("/proc/stb/fb/3dmode"):
		from Plugins.Plugin import PluginDescriptor
		return [PluginDescriptor(name = "OSD 3D setup", description = _("Adjust 3D settings"), where = PluginDescriptor.WHERE_PLUGINMENU, fnc = main),
					PluginDescriptor(name = "OSD 3D setup", description = "", where = PluginDescriptor.WHERE_SESSIONSTART, fnc = startup)]
	return []
