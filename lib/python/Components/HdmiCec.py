import struct
from config import config, ConfigSelection, ConfigYesNo, ConfigSubsection
from enigma import eHdmiCEC, eTimer

config.hdmicec = ConfigSubsection()
config.hdmicec.enabled = ConfigYesNo(default = True)
config.hdmicec.standby_message = ConfigSelection(
	choices = {
	"standby": _("TV off"),
	"sourceinactive": _("Source inactive"),
	"menuinactive": _("Menu inactive"),
	"nothing": _("Nothing"),
	},
	default = "standby")
config.hdmicec.wakeup_message = ConfigSelection(
	choices = {
	"wakeup": _("TV on"),
	"sourceactive": _("Source active"),
	"menuactive": _("Menu active"),
	"wakeup,menuactive": _("TV on, menu active"),
	"sourceactive,menuactive": _("Source active, menu active"),
	"wakeup,sourceactive,menuactive": _("TV on, source active, menu active"),
	"nothing": _("Nothing"),
	},
	default = "wakeup,sourceactive,menuactive")
config.hdmicec.wakeup_handling = ConfigSelection(
	choices = {
		"": _("Wakeup"),
		"delay": _("Wakeup, wait 3s"),
		"delay,delay": _("Wakeup, wait 6s"),
		"waitforactivity,delay": _("Wakeup, wait for activity, wait 3s"),
		"waitforstreamrequest,delay": _("Wakeup, wait for stream request, wait 3s"),
	},
	default = "waitforstreamrequest,delay")

class HdmiCec:
	def __init__(self):
		eHdmiCEC.getInstance().messageReceived.get().append(self.messageReceived)
		eHdmiCEC.getInstance().streamRequestReceived.get().append(self.streamRequestReceived)
		config.misc.standbyCounter.addNotifier(self.enterStandby, initial_call = False)
		self.timer = eTimer()
		self.timer.callback.append(self.timeout)
		self.messages = []
		self.destinationaddress = 0
		self.waitforactivity = False
		self.waitforstreamrequest = False

	def timeout(self):
		print "HdmiCec: continue after delay"
		self.sendMessages(self.destinationaddress, self.messages)

	def sendMessages(self, address, messages):
		self.messages = messages
		self.destinationaddress = address
		for message in self.messages:
			cmd = None
			self.messages = self.messages[1:]
			address = self.destinationaddress
			if message == "delay":
				print "HdmiCec: delay"
				self.timer.start(3000, True)
				break
			elif message == "waitforactivity":
				print "HdmiCec: wait for activity..."
				self.waitforactivity = True
				break
			elif message == "waitforstreamrequest":
				print "HdmiCec: wait for streaming path request..."
				self.waitforstreamrequest = True
				break
			elif message == "wakeup":
				cmd = struct.pack('B', 0x04)
			elif message == "sourceactive":
				address = 0x0f # use broadcast for active source command
				physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
				cmd = struct.pack('BBB', 0x82, int(physicaladdress/256), int(physicaladdress%256))
			elif message == "standby":
				cmd = struct.pack('B', 0x36)
			elif message == "sourceinactive":
				address = 0x0f # use broadcast for inactive source command
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
			messages = config.hdmicec.wakeup_message.value
			if config.hdmicec.wakeup_handling.value:
				messages = messages.replace("wakeup", "wakeup," + config.hdmicec.wakeup_handling.value)
			self.sendMessages(0, messages.split(','))

	def enterStandby(self, configElement):
		from Screens.Standby import inStandby
		inStandby.onClose.append(self.leaveStandby)
		if config.hdmicec.enabled.value:
			self.sendMessages(0, config.hdmicec.standby_message.value.split(','))

	def messageReceived(self, address, message):
		if config.hdmicec.enabled.value:
			if self.waitforactivity:
				print "HdmiCec: activity detected, continue"
				self.waitforactivity = False
				self.sendMessages(self.destinationaddress, self.messages)
			if message == 0x36:
				from Screens.Standby import Standby, inStandby
				if not inStandby:
					from Tools import Notifications
					Notifications.AddNotification(Standby)

	def streamRequestReceived(self, address):
		if config.hdmicec.enabled.value:
			if self.waitforstreamrequest:
				print "HdmiCec: streaming path request received, continue"
				self.waitforstreamrequest = False
				self.sendMessages(self.destinationaddress, self.messages)
			from Screens.Standby import Standby, inStandby
			if inStandby:
				inStandby.Power()

hdmi_cec = HdmiCec()
