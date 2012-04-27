from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection, getConfigListEntry

modelist = {"0": _("Off"), "2": _("On"), "1": _("Auto")}

config.plugins.FanSetup = ConfigSubsection()
config.plugins.FanSetup.mode = ConfigSelection(choices = modelist, default = "0")

class FanSetupScreen(Screen, ConfigListScreen):
	skin = """
	<screen position="c-200,c-100" size="400,200" title="Fan setup">
		<widget name="config" position="c-175,c-75" size="350,150" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="c-145,e-45" zPosition="0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="c+5,e-45" zPosition="0" size="140,40" alphatest="on" />
		<widget name="ok" position="c-145,e-45" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="green" />
		<widget name="cancel" position="c+5,e-45" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="red" />
	</screen>"""

	def __init__(self, session):
		self.skin = FanSetupScreen.skin
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

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)

		mode = config.plugins.FanSetup.mode.value

		self.mode = ConfigSelection(choices = modelist, default = mode)
		self.list.append(getConfigListEntry(_("Fan mode"), self.mode))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.setPreviewSettings()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setPreviewSettings()

	def setPreviewSettings(self):
		applySettings(int(self.mode.value))

	def keyGo(self):
		config.plugins.FanSetup.mode.value = self.mode.value
		config.plugins.FanSetup.save()
		self.close()

	def keyCancel(self):
		setConfiguredSettings()
		self.close()

def applySettings(mode):
	setMode = ""
	if mode == 1:
		setMode = "auto"

	elif mode == 2:
		setMode = "on"

	else:
		setMode = "off"

	try:
		file = open("/proc/stb/fp/fan", "w")
		file.write('%s' % setMode)
		file.close()
	except:
		return

def setConfiguredSettings():
	applySettings(int(config.plugins.FanSetup.mode.value))

def main(session, **kwargs):
	session.open(FanSetupScreen)

def startup(reason, **kwargs):
	setConfiguredSettings()

def selSetup(menuid, **kwargs):
	if menuid != "system":
		return [ ]
	return [(_("Fan Control"), main, "fansetup_config", 70)]

def Plugins(**kwargs):
	from os import path
	if not path.exists("/usr/lib/enigma2/python/Plugins/Extensions/FanControl2/plugin.pyo") and path.exists("/proc/stb/fp/fan"):
		from Plugins.Plugin import PluginDescriptor
		return [PluginDescriptor(name=_("Fan Control"), description=_("switch Fan On/Off"), where = PluginDescriptor.WHERE_MENU, needsRestart = True, fnc=selSetup)
				PluginDescriptor(name = "Fan Control", description = "", where = PluginDescriptor.WHERE_SESSIONSTART, needsRestart = True, fnc = startup)]
	return []
