from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection, getConfigListEntry
from Components.FanControl import fancontrol

modelist = {"0": _("Off"), "1": _("On")}
standbylist = [("false", _("no")), ("true", _("yes")), ("trueRec", _("yes, Except for Recording or HDD"))]

config.plugins.FanControl = ConfigSubsection()
config.plugins.FanControl.mode = ConfigSelection(choices = modelist, default = "0")
config.plugins.FanControl.StandbyOff = ConfigSelection(choices = standbylist, default="false")

class FanSetupScreen(ConfigListScreen, Screen):

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.skinName = "Setup"
		Screen.setTitle(self, _("Fan setup") + "...")

		from Components.ActionMap import ActionMap
		from Components.Sources.StaticText import StaticText

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))

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

		mode = config.plugins.FanControl.mode.value
		modestandby = config.plugins.FanControl.StandbyOff.value

		self.mode = ConfigSelection(choices = modelist, default = mode)
		self.list.append(getConfigListEntry(_("Fan mode"), self.mode))
		self.modestandby = ConfigSelection(choices = standbylist, default = modestandby)
		self.list.append(getConfigListEntry(_("Fan control in Standby off"), self.modestandby))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.setPreviewSettings()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setPreviewSettings()

	def setPreviewSettings(self):
		applySettings(int(self.mode.value), False, self.modestandby.value)

	def keyGo(self):
		config.plugins.FanControl.mode.value = self.mode.value
		config.plugins.FanControl.StandbyOff.value = self.modestandby.value
		config.plugins.FanControl.save()
		self.close()

	def keyCancel(self):
		setConfiguredSettings()
		self.close()

def applySettings(mode, firststart = None, modestandby = None):
	if mode == 1:
		fancontrol.getConfig(0).pwm.value = 255
	else:
		fancontrol.getConfig(0).pwm.value = 0

	if firststart:
		if config.plugins.FanControl.StandbyOff.value == "false":
			fancontrol.getConfig(0).pwm_standby.value = 255
		else:
			fancontrol.getConfig(0).pwm_standby.value = 0
	else:
		if modestandby == "false":
			fancontrol.getConfig(0).pwm_standby.value = 255
		else:
			fancontrol.getConfig(0).pwm_standby.value = 0

	fancontrol.getConfig(0).pwm.save()
	fancontrol.getConfig(0).pwm_standby.save()

def setConfiguredSettings():
	applySettings(int(config.plugins.FanControl.mode.value), True)

def main(session, **kwargs):
	session.open(FanSetupScreen)

def startup(reason, **kwargs):
	setConfiguredSettings()

def Plugins(**kwargs):
	from os import path
	from Plugins.Plugin import PluginDescriptor
	return [PluginDescriptor(name = _("Fan Control"), description = _("switch Fan On/Off"), where = PluginDescriptor.WHERE_PLUGINMENU, fnc = main),
	PluginDescriptor(name = "Fan Control", description = "", where = PluginDescriptor.WHERE_SESSIONSTART, fnc = startup)]