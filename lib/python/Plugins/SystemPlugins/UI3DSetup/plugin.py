from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection, ConfigSlider, getConfigListEntry
from Components.Sources.StaticText import StaticText

modelist = {"off": _("Off"), "auto": _("Auto"), "sidebyside": _("Side by Side"), "topandbottom": _("Top and Bottom")}
setmodelist = {"mode1": _("Mode 1"), "mode2": _("Mode 2")}

config.plugins.UI3DSetup = ConfigSubsection()
config.plugins.UI3DSetup.mode = ConfigSelection(choices = modelist, default = "auto")
config.plugins.UI3DSetup.znorm = ConfigInteger(default = 0)
config.plugins.UI3DSetup.setmode = ConfigSelection(choices = setmodelist, default = "mode1")

class UI3DSetupScreen(Screen, ConfigListScreen):
	skin = """
		<screen position="center,center" size="440,300" title="UI 3D setup" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,10" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="290,10" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="10,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" transparent="1" />
			<widget source="key_green" render="Label" position="290,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" transparent="1" />
			<widget name="config" zPosition="2" position="10,70" size="410,200" scrollbarMode="showOnDemand" transparent="1" />
		</screen>"""

	def __init__(self, session):
		self.skin = UI3DSetupScreen.skin
		Screen.__init__(self, session)

		from Components.ActionMap import ActionMap
		from Components.Button import Button
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))

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

		mode = config.plugins.UI3DSetup.mode.value
		znorm = config.plugins.UI3DSetup.znorm.value
		setmode = config.plugins.UI3DSetup.setmode.value

		self.mode = ConfigSelection(choices = modelist, default = mode)
		self.znorm = ConfigSlider(default = znorm + 50, increment = 1, limits = (0, 100))
		self.setmode = ConfigSelection(choices = setmodelist, default = setmode)
		self.list.append(getConfigListEntry(_("Setup mode"), self.setmode))
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
		applySettings(self.mode.value, self.znorm.value - 50, self.setmode.value)

	def keyGo(self):
		config.plugins.UI3DSetup.mode.setValue(self.mode.value)
		config.plugins.UI3DSetup.znorm.setValue(self.znorm.value - 50)
		config.plugins.UI3DSetup.setmode.setValue(self.setmode.value)
		config.plugins.UI3DSetup.save()
		self.close()

	def keyCancel(self):
		setConfiguredSettings()
		self.close()

def applySettings(mode, znorm, setmode):
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

def setConfiguredSettings():
	applySettings(config.plugins.UI3DSetup.mode.value,
		int(config.plugins.UI3DSetup.znorm.value), config.plugins.UI3DSetup.setmode.value)

def main(session, **kwargs):
	session.open(UI3DSetupScreen)

def startup(reason, **kwargs):
	setConfiguredSettings()

def Plugins(**kwargs):
	from os import path
	if path.exists("/proc/stb/fb/3dmode") or path.exists("/proc/stb/fb/primary/3d"):
		from Plugins.Plugin import PluginDescriptor
		return [PluginDescriptor(name = "UI 3D setup", description = _("Adjust 3D settings"), where = PluginDescriptor.WHERE_PLUGINMENU, fnc = main),
					PluginDescriptor(name = "UI 3D setup", description = "", where = PluginDescriptor.WHERE_SESSIONSTART, fnc = startup)]
	return []
