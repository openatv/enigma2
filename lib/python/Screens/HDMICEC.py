from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.HdmiCec import hdmi_cec as hdmiCec
from Components.Sources.StaticText import StaticText
from Screens.Setup import Setup


class HDMICECSetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session=session, setup="HDMICEC")
		self.setTitle(_("HDMI-CEC Settings"))
		self["addressActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.updateFixedAddress, _("Set current CEC address as fixed address"))
		}, prio=0, description=_("HDMI-CEC Setup Actions"))
		self["defaultActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.setDefaults, _("Reset HDMI-CEC settings to default"))
		}, prio=0, description=_("HDMI-CEC Setup Actions"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["current_address"] = StaticText()
		self["fixed_address"] = StaticText()

	def updateFixedAddress(self):
		config.hdmicec.fixed_physical_address.value = hdmiCec.getPhysicalAddress() if config.hdmicec.fixed_physical_address.value == "0.0.0.0" else "0.0.0.0"
		hdmiCec.setFixedPhysicalAddress(config.hdmicec.fixed_physical_address.value)
		self.updateAddress()

	def updateAddress(self):
		self["current_address"].setText("%s: %s" % (_("Current CEC address"), hdmiCec.getPhysicalAddress()))
		value = config.hdmicec.fixed_physical_address.value
		if value == "0.0.0.0":
			self["fixed_address"].setText(_("Using automatic address"))
			if hdmiCec.getPhysicalAddress() != "0.0.0.0":
				self["addressActions"].setEnabled(True)
				self["key_yellow"].setText(_("Set fixed"))
			else:
				self["addressActions"].setEnabled(False)
				self["key_yellow"].setText("")
		else:
			self["fixed_address"].setText("%s: %s" % (_("Using fixed address"), value))
			self["addressActions"].setEnabled(True)
			self["key_yellow"].setText(_("Clear fixed"))

	def setDefaults(self):
		for item in config.hdmicec.dict():
			if item in ("enabled", "advanced_settings"):
				continue
			configItem = getattr(config.hdmicec, item)
			configItem.value = configItem.default
		self.createSetup()

	def selectionChanged(self):
		if self.getCurrentItem() == config.hdmicec.enabled:
			if config.hdmicec.enabled.value:
				self.updateAddress()
			else:
				self["key_yellow"].setText("")
				self["current_address"].setText("")
				self["fixed_address"].setText("")
			self["addressActions"].setEnabled(config.hdmicec.enabled.value)
			self["key_blue"].setText(_("Use defaults") if config.hdmicec.enabled.value else "")
			self["defaultActions"].setEnabled(config.hdmicec.enabled.value)
		Setup.selectionChanged(self)

	def keySave(self):
		config.hdmicec.save()
		Setup.keySave(self)
