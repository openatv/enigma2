import struct
from config import config, ConfigSelection, ConfigYesNo, ConfigSubsection
from enigma import eHdmiCEC

config.hdmicec = ConfigSubsection()
config.hdmicec.enabled = ConfigYesNo(default = True)
config.hdmicec.standby_message = ConfigSelection(
	choices = {
	"standby": _("TV standby"),
	"inactive": _("Source inactive"),
	"nothing": _("Nothing"),
	},
	default = "standby")
config.hdmicec.wakeup_message = ConfigSelection(
	choices = {
	"wakeup": _("TV wakeup"),
	"active": _("Source active"),
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
