from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry

class HdmiCECSetupScreen(Screen, ConfigListScreen):
	skin = """
	<screen position="c-250,c-150" size="500,300" title="HDMI CEC setup">
		<widget name="config" position="c-225,c-125" size="450,250" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="c-145,e-45" zPosition="0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="c+5,e-45" zPosition="0" size="140,40" alphatest="on" />
		<widget name="ok" position="c-145,e-45" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="green" />
		<widget name="cancel" position="c+5,e-45" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="red" />
	</screen>"""

	def __init__(self, session):
		self.skin = HdmiCECSetupScreen.skin
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
		self.list.append(getConfigListEntry(_("Enabled"), config.hdmicec.enabled))
		self.list.append(getConfigListEntry(_("Standby message"), config.hdmicec.standby_message))
		self.list.append(getConfigListEntry(_("Wakeup message"), config.hdmicec.wakeup_message))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		ConfigListScreen.keyRight(self)

	def keyGo(self):
		for x in self["config"].list:
			x[1].save()
		self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

def main(session, **kwargs):
	session.open(HdmiCECSetupScreen)

def Plugins(**kwargs):
	from os import path
	if path.exists("/dev/hdmi_cec"):
		import Components.HdmiCec
		from Plugins.Plugin import PluginDescriptor
		return [PluginDescriptor(name = "HDMI CEC setup", description = _("Adjust HDMI CEC settings"), where = PluginDescriptor.WHERE_PLUGINMENU, fnc = main)]
	return []
