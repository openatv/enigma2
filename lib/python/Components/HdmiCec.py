import struct
from config import config, ConfigSelection, ConfigYesNo, ConfigSubsection
from enigma import eHdmiCEC

class HdmiCec:
	def __init__(self):
		config.hdmicec = ConfigSubsection()
		config.hdmicec.enabled = ConfigYesNo(default = True)
		config.hdmicec.active_source_reply = ConfigYesNo(default = True)
		config.hdmicec.standby_message = ConfigSelection(
			choices = {
			"inactive,standby": _("TV standby"),
			"inactive": _("Source inactive"),
			"nothing": _("Nothing"),
			},
			default = "inactive,standby")
		config.hdmicec.wakeup_message = ConfigSelection(
			choices = {
			"wakeup,active": _("TV wakeup"),
			"active": _("Source active"),
			"nothing": _("Nothing"),
			},
			default = "wakeup,active")

		eHdmiCEC.getInstance().messageReceived.get().append(self.messageReceived)
		config.misc.standbyCounter.addNotifier(self.enterStandby, initial_call = False)

	def sendMessages(self, address, messages):
		for message in messages.split(','):
			cmd = None
			if message == "wakeup":
				cmd = struct.pack('B', 0x04)
			elif message == "active":
				cmd = struct.pack('B', 0x82)
			elif message == "standby":
				cmd = struct.pack('B', 0x36)
			elif message == "inactive":
				cmd = struct.pack('B', 0x9e)
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
		print "received cec message %x from %x" % (message, address)
		if config.hdmicec.enabled.value:
			if message == 0x85 and config.hdmicec.active_source_reply.value:
				# tv is requesting active sources
				if not inStandby:
					# we are active
					self.sendMessages(address, "active")

hdmi_cec = HdmiCec()
