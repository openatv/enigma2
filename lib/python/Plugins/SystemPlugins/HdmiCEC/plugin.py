from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry
from Components.Sources.StaticText import StaticText

class HdmiCECSetupScreen(Screen, ConfigListScreen):
	skin = """
	<screen position="c-300,c-250" size="600,500" title="HDMI CEC setup">
		<widget name="config" position="25,25" size="550,350" />
		<widget source="current_address" render="Label" position="25,375" size="550,30" zPosition="10" font="Regular;21" halign="left" valign="center" />
		<widget source="fixed_address" render="Label" position="25,405" size="550,30" zPosition="10" font="Regular;21" halign="left" valign="center" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="20,e-45" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="160,e-45" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="300,e-45" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="440,e-45" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="20,e-45" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="160,e-45" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_yellow" render="Label" position="300,e-45" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		<widget source="key_blue" render="Label" position="440,e-45" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
	</screen>"""

	def __init__(self, session):
		self.skin = HdmiCECSetupScreen.skin
		Screen.__init__(self, session)

		from Components.ActionMap import ActionMap
		from Components.Button import Button

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText(_("Set fixed"))
		self["key_blue"] = StaticText(_("Clear fixed"))
		self["current_address"] = StaticText()
		self["fixed_address"] = StaticText()

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
			"ok": self.keyGo,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"green": self.keyGo,
			"red": self.keyCancel,
			"yellow": self.setFixedAddress,
			"blue": self.clearFixedAddress,
			"menu": self.closeRecursive,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)

		self.list.append(getConfigListEntry(_("Enabled"), config.hdmicec.enabled))
		self.list.append(getConfigListEntry(_("Put TV in standby"), config.hdmicec.control_tv_standby))
		self.list.append(getConfigListEntry(_("Wakeup TV from standby"), config.hdmicec.control_tv_wakeup))
		self.list.append(getConfigListEntry(_("Regard deep standby as standby"), config.hdmicec.handle_deepstandby_events))
		self.list.append(getConfigListEntry(_("Switch TV to correct input"), config.hdmicec.report_active_source))
		self.list.append(getConfigListEntry(_("Use TV remote control"), config.hdmicec.report_active_menu))
		self.list.append(getConfigListEntry(_("Handle standby from TV"), config.hdmicec.handle_tv_standby))
		self.list.append(getConfigListEntry(_("Handle wakeup from TV"), config.hdmicec.handle_tv_wakeup))
		self.list.append(getConfigListEntry(_("Wakeup signal from TV"), config.hdmicec.tv_wakeup_detection))
		self.list.append(getConfigListEntry(_("Forward volume keys"), config.hdmicec.volume_forwarding))
		self.list.append(getConfigListEntry(_("Put receiver in standby"), config.hdmicec.control_receiver_standby))
		self.list.append(getConfigListEntry(_("Wakeup receiver from standby"), config.hdmicec.control_receiver_wakeup))
		self.list.append(getConfigListEntry(_("Minimum send interval"), config.hdmicec.minimum_send_interval))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self.updateAddress()

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

	def setFixedAddress(self):
		import Components.HdmiCec
		Components.HdmiCec.hdmi_cec.setFixedPhysicalAddress(Components.HdmiCec.hdmi_cec.getPhysicalAddress())
		self.updateAddress()

	def clearFixedAddress(self):
		import Components.HdmiCec
		Components.HdmiCec.hdmi_cec.setFixedPhysicalAddress("0.0.0.0")
		self.updateAddress()

	def updateAddress(self):
		import Components.HdmiCec
		self["current_address"].setText(_("Current CEC address") + ": " + Components.HdmiCec.hdmi_cec.getPhysicalAddress())
		if config.hdmicec.fixed_physical_address.value == "0.0.0.0":
			fixedaddresslabel = ""
		else:
			fixedaddresslabel = _("Using fixed address") + ": " + config.hdmicec.fixed_physical_address.value
		self["fixed_address"].setText(fixedaddresslabel)

def main(session, **kwargs):
	session.open(HdmiCECSetupScreen)

def startSetup(menuid):
	if menuid == "system":
		return [(_("HDMI-CEC setup"), main, "hdmi_cec_setup", 0)]
	return []

def Plugins(**kwargs):
	from os import path
	if path.exists("/dev/hdmi_cec") or path.exists("/dev/misc/hdmi_cec0"):
		import Components.HdmiCec
		from Plugins.Plugin import PluginDescriptor
		return [PluginDescriptor(where = PluginDescriptor.WHERE_MENU, fnc = startSetup)]
	return []
