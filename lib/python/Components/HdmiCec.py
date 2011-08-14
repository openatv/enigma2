import struct
from config import config, ConfigSelection, ConfigYesNo, ConfigSubsection
from enigma import eHdmiCEC

config.hdmicec = ConfigSubsection()
config.hdmicec.enabled = ConfigYesNo(default = True)
config.hdmicec.standby_message = ConfigSelection(
	choices = {
	"standby": _("TV off"),
	"inactive": _("Source inactive"),
	"menuinactive": _("Menu inactive"),
	"menuinactive,standby": _("Menu inactive, TV off"),
	"menuinactive,inactive": _("Menu inactive, source inactive"),
	"nothing": _("Nothing"),
	},
	default = "standby")
config.hdmicec.wakeup_message = ConfigSelection(
	choices = {
	"wakeup": _("TV on"),
	"active": _("Source active"),
	"menuactive": _("Menu active"),
	"wakeup,menuactive": _("TV on, menu active"),
	"active,menuactive": _("Source active, menu active"),
	"nothing": _("Nothing"),
	},
	default = "wakeup")

class HdmiCec:
	def __init__(self):
		eHdmiCEC.getInstance().messageReceived.get().append(self.messageReceived)
		config.misc.standbyCounter.addNotifier(self.enterStandby, initial_call = False)

	def sendMessages(self, address, messages):
		for message in messages.split(','):
			cmd = None
			if message == "wakeup":
				cmd = struct.pack('B', 0x04)
			elif message == "active":
				physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
				cmd = struct.pack('BBB', 0x82, int(physicaladdress/256), int(physicaladdress%256))
			elif message == "standby":
				cmd = struct.pack('B', 0x36)
			elif message == "inactive":
				physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
				cmd = struct.pack('BBB', 0x9d, int(physicaladdress/256), int(physicaladdress%256))
			elif message == "menuactive":
				cmd = struct.pack('BB', 0x8e, 0x00)
			elif message == "menuinactive":
				cmd = struct.pack('BB', 0x8e, 0x01)
			if cmd:
				eHdmiCEC.getInstance().sendMessage(address, len(cmd), str(cmd))

	def leaveStandby(self):
		if config.hdmicec.enabled.value:
			self.sendMessages(0, config.hdmicec.wakeup_message.value)

	def enterStandby(self, configElement):
		from Screens.Standby import inStandby
		inStandby.onClose.append(self.leaveStandby)
		if config.hdmicec.enabled.value:
			self.sendMessages(0, config.hdmicec.standby_message.value)

	def messageReceived(self, address, message):
		if config.hdmicec.enabled.value:
			if message == 0x36:
				from Screens.Standby import Standby, inStandby
				if not inStandby:
					from Tools import Notifications
					Notifications.AddNotification(Standby)

hdmi_cec = HdmiCec()
