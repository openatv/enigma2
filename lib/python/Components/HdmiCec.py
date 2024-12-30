from datetime import datetime
from os import remove, statvfs, uname
from os.path import isfile, join as pathjoin
from struct import pack
from sys import maxsize
from time import time

from enigma import eActionMap, eHdmiCEC, eTimer

from Components.config import config, ConfigSelection, ConfigYesNo, ConfigSubsection, ConfigText, NoSave
from Components.Console import Console
import Screens.Standby
from Tools.Directories import fileExists, pathExists

config.hdmicec = ConfigSubsection()
config.hdmicec.enabled = ConfigYesNo(default=False)  # Query from this value in hdmi_cec.cpp
config.hdmicec.control_tv_standby = ConfigYesNo(default=True)
config.hdmicec.control_tv_wakeup = ConfigYesNo(default=True)
config.hdmicec.report_active_source = ConfigYesNo(default=True)
config.hdmicec.report_active_menu = ConfigYesNo(default=True)  # Query from this value in hdmi_cec.cpp
choicelist = [
	("disabled", _("Disabled")),
	("standby", _("Standby")),
	("deepstandby", _("Deep Standby"))
]
config.hdmicec.handle_tv_standby = ConfigSelection(default="standby", choices=choicelist)
config.hdmicec.handle_tv_input = ConfigSelection(default="disabled", choices=choicelist)
config.hdmicec.handle_tv_wakeup = ConfigSelection(default="streamrequest", choices={
	"disabled": _("Disabled"),
	"wakeup": _("Wake up"),
	"tvreportphysicaladdress": _("TV physical address report"),
	"routingrequest": _("Routing request"),
	"sourcerequest": _("Source request"),
	"streamrequest": _("Stream request"),
	"osdnamerequest": _("OSD name request"),
	"activity": _("Any activity"),
})
config.hdmicec.fixed_physical_address = ConfigText(default="0.0.0.0")
config.hdmicec.volume_forwarding = ConfigYesNo(default=False)
config.hdmicec.control_receiver_wakeup = ConfigYesNo(default=False)
config.hdmicec.control_receiver_standby = ConfigYesNo(default=False)
config.hdmicec.handle_deepstandby_events = ConfigYesNo(default=True)
config.hdmicec.preemphasis = ConfigYesNo(default=False)
choicelist = []
for i in (10, 50, 100, 150, 250, 500, 750, 1000):
	choicelist.append((i, _("%d ms") % i))
config.hdmicec.minimum_send_interval = ConfigSelection(default=250, choices=[(0, _("Disabled"))] + choicelist)
choicelist = []
for i in list(range(1, 6)):
	choicelist.append((i, _("%d times") % i))
config.hdmicec.messages_repeat = ConfigSelection(default=0, choices=[(0, _("Disabled"))] + choicelist)
config.hdmicec.messages_repeat_standby = ConfigYesNo(default=False)
choicelist = []
for i in (500, 1000, 2000, 3000, 4000, 5000):
	choicelist.append((i, _("%d ms") % i))
config.hdmicec.messages_repeat_slowdown = ConfigSelection(default=1000, choices=[(0, _("None"))] + choicelist)
choicelist = []
for i in (5, 10, 30, 60, 120, 300, 600, 900, 1800, 3600):
	if i / 60 < 1:
		choicelist.append((i, _("%d sec") % i))
	else:
		choicelist.append((i, _("%d min") % (i / 60)))
config.hdmicec.handle_tv_delaytime = ConfigSelection(default=0, choices=[(0, _("None"))] + choicelist)
config.hdmicec.deepstandby_waitfortimesync = ConfigYesNo(default=True)
config.hdmicec.tv_wakeup_zaptimer = ConfigYesNo(default=True)
config.hdmicec.tv_wakeup_zapandrecordtimer = ConfigYesNo(default=True)
config.hdmicec.tv_wakeup_wakeuppowertimer = ConfigYesNo(default=True)
config.hdmicec.tv_standby_notinputactive = ConfigYesNo(default=True)
config.hdmicec.check_tv_state = ConfigYesNo(default=False)
config.hdmicec.workaround_activesource = ConfigYesNo(default=False)
choicelist = []
for i in (5, 10, 15, 30, 45, 60):
	choicelist.append((i, _("%d sec") % i))
config.hdmicec.workaround_turnbackon = ConfigSelection(default=0, choices=[(0, _("Disabled"))] + choicelist)
config.hdmicec.advanced_settings = ConfigYesNo(default=False)
config.hdmicec.default_settings = NoSave(ConfigYesNo(default=False))
config.hdmicec.debug = ConfigYesNo(default=False)
config.hdmicec.commandline = ConfigYesNo(default=False)

cmdfile = "/tmp/hdmicec_cmd"
msgfile = "/tmp/hdmicec_msg"
errfile = "/tmp/hdmicec_cmd_err.log"
hlpfile = "/tmp/hdmicec_cmd_hlp.txt"
cecinfo = "http://www.cec-o-matic.com"

WRONG_DATA_LENGTH = "<wrong data length>"
UNKNOWN = "<unknown>"

CEC = ["1.1", "1.2", "1.2a", "1.3", "1.3a", "1.4", "2.0?", "unknown"]  # CEC Version's table.  CmdList from http://www.cec-o-matic.com

CECintcmd = {
	"Active Source": "sourceactive",
	"Device Vendor ID": "vendorid",
	"Give Device Power Status": "powerstate",
	"Give System Audio Mode Status": "givesystemaudiostatus",
	"Image View On": "wakeup",
	"Inactive Source": "sourceinactive",
	"Menu Status Activated": "menuactive",
	"Menu Status Deactivated": "menuinactive",
	"Report Physical Address": "reportaddress",
	"Report Power Status On": "poweractive",
	"Report Power Status Standby": "powerinactive",
	"Routing Information": "routinginfo",
	"Set OSD Name": "osdname",
	"Set System Audio Mode Off": "deactivatesystemaudiomode",
	"Set System Audio Mode On": "activatesystemaudiomode",
	"Standby": "standby",
	"System Audio Mode Request": "setsystemaudiomode",
	"User Control Pressed Power Off": "keypoweroff",
	"User Control Pressed Power On": "keypoweron"
}

CECaddr = {
	0x00: "<TV>",
	0x01: "<Recording 1>",
	0x02: "<Recording 2>",
	0x03: "<Tuner 1>",
	0x04: "<Playback 1>",
	0x05: "<Audio System>",
	0x06: "<Tuner 2>",
	0x07: "<Tuner 3>",
	0x08: "<Playback 2>",
	0x09: "<Playback 3>",
	0x0A: "<Tuner 4>",
	0x0B: "<Playback 2>",
	0x0C: "<Reserved>",
	0x0D: "<Reserved>",
	0x0E: "<Specific>",
	0x0F: "<Broadcast>"
}

CECcmd = {
	0x00: "<Feature Abort>",
	0x04: "<Image View On>",
	0x05: "<Tuner Step Increment>",
	0x06: "<Tuner Step Decrement>",
	0x07: "<Tuner Device Status>",
	0x08: "<Give Tuner Device Status>",
	0x09: "<Record On>",
	0x0A: "<Record Status>",
	0x0B: "<Record Off>",
	0x0D: "<Text View On>",
	0x0F: "<Record TV Screen>",
	0x1A: "<Give Deck Status>",
	0x1B: "<Deck Status>",
	0x32: "<Set Menu Language>",
	0x33: "<Clear Analogue Timer>",
	0x34: "<Set Analogue Timer>",
	0x35: "<Timer Status>",
	0x36: "<Standby>",
	0x41: "<Play>",
	0x42: "<Deck Control>",
	0x43: "<Timer Cleared Status>",
	0x44: "<User Control Pressed>",
	0x45: "<User Control Released>",
	0x46: "<Give OSD Name>",
	0x47: "<Set OSD Name>",
	0x64: "<Set OSD String>",
	0x67: "<Set Timer Program Title>",
	0x70: "<System Audio Mode Request>",
	0x71: "<Give Audio Status>",
	0x72: "<Set System Audio Mode>",
	0x7A: "<Report Audio Status>",
	0x7D: "<Give System Audio Mode Status>",
	0x7E: "<System Audio Mode Status>",
	0x80: "<Routing Change>",
	0x81: "<Routing Information>",
	0x82: "<Active Source>",
	0x83: "<Give Physical Address>",
	0x84: "<Report Physical Address>",
	0x85: "<Request Active Source>",
	0x86: "<Set Stream Path>",
	0x87: "<Reporting Device Vendor ID>",  # Device (TV, AV receiver, audio device) returns its vendor ID (3 bytes).
	0x89: "<Vendor Command><Vendor Specific Data>",
	0x8A: "<Vendor Remote Button Down><Vendor Specific RC Code>",
	0x8B: "<Vendor Remote Button Up>",
	0x8C: "<Request Device Vendor ID>",  # Request vendor ID from device(TV, AV receiver, audio device).
	0x8D: "<Menu Request>",
	0x8E: "<Menu Status>",
	0x8F: "<Give Device Power Status>",
	0x90: "<Report Power Status>",
	0x91: "<Get Menu Language>",
	0x92: "<Select Analogue Service>",
	0x93: "<Select Digital Service>",
	0x97: "<Set Digital Timer>",
	0x99: "<Clear Digital Timer>",
	0x9A: "<Set Audio Rate>",
	0x9D: "<Inactive Source>",
	0x9E: "<CEC Version>",
	0x9F: "<Get CEC Version>",
	0xA0: "<Vendor Command With ID>",
	0xA1: "<Clear External Timer>",
	0xA2: "<Set External Timer>",
	0xFF: "<Abort>"
}

CECdat = {
	0x00: {
		0x00: "<Unrecognized opcode>",
		0x01: "<Not in correct mode to respond>",
		0x02: "<Cannot provide source>",
		0x03: "<Invalid operand>",
		0x04: "<Refused>"
	},
	0x08: {
		0x01: "<On>",
		0x02: "<Off>",
		0x03: "<Once>"
	},
	0x0A: {
		0x01: "<Recording currently selected source>",
		0x02: "<Recording Digital Service>",
		0x03: "<Recording Analogue Service>",
		0x04: "<Recording External Input>",
		0x05: "<No recording - unable to record Digital Service>",
		0x06: "<No recording - unable to record Analogue Service>",
		0x07: "<No recording - unable to select required Service>",
		0x09: "<No recording - unable External plug number>",
		0x0A: "<No recording - unable External plug number>",
		0x0B: "<No recording - CA system not supported>",
		0x0C: "<No recording - No or Insufficent CA Entitlements>",
		0x0D: "<No recording - No allowed to copy source>",
		0x0E: "<No recording - No futher copies allowed>",
		0x10: "<No recording - no media>",
		0x11: "<No recording - playing>",
		0x12: "<No recording - already recording>",
		0x13: "<No recording - media protected>",
		0x14: "<No recording - no source signa>",
		0x15: "<No recording - media problem>",
		0x16: "<No recording - no enough space available>",
		0x17: "<No recording - Parental Lock On>",
		0x1A: "<Recording terminated normally>",
		0x1B: "<Recording has already terminated>",
		0x1F: "<No recording - other reason>"
	},
	0x1B: {
		0x11: "<Play>",
		0x12: "<Record",
		0x13: "<Play Reverse>",
		0x14: "<Still>",
		0x15: "<Slow>",
		0x16: "<Slow Reverse>",
		0x17: "<Fast Forward>",
		0x18: "<Fast Reverse>",
		0x19: "<No Media>",
		0x1A: "<Stop>",
		0x1B: "<Skip Forward / Wind>",
		0x1C: "<Skip Reverse / Rewind>",
		0x1D: "<Index Search Forward>",
		0x1E: "<Index Search Reverse>",
		0x1F: "<Other Status>"
	},
	0x1A: {
		0x01: "<On>",
		0x02: "<Off>",
		0x03: "<Once>"
	},
	0x41: {
		0x05: "<Play Forward Min Speed>",
		0x06: "<Play Forward Medium Speed>",
		0x07: "<Play Forward Max Speed>",
		0x09: "<Play Reverse Min Speed>",
		0x0A: "<Play Reverse Medium Speed>",
		0x0B: "<Play Reverse Max Speed>",
		0x15: "<Slow Forward Min Speed>",
		0x16: "<Slow Forward Medium Speed>",
		0x17: "<Slow Forward Max Speed>",
		0x19: "<Slow Reverse Min Speed>",
		0x1A: "<Slow Reverse Medium Speed>",
		0x1B: "<Slow Reverse Max Speed>",
		0x20: "<Play Reverse>",
		0x24: "<Play Forward>",
		0x25: "<Play Still>"
	},
	0x42: {
		0x01: "<Skip Forward / Wind>",
		0x02: "<Skip Reverse / Rewind",
		0x03: "<Stop>",
		0x04: "<Eject>"
	},
	0x43: {
		0x00: "<Timer not cleared - recording>",
		0x01: "<Timer not cleared - no matching>",
		0x02: "<Timer not cleared - no info available>",
		0x80: "<Timer cleared>"
	},
	0x44: {
		0x00: "<Select>",
		0x01: "<Up>",
		0x02: "<Down>",
		0x03: "<Left>",
		0x04: "<Right>",
		0x05: "<Right-Up>",
		0x06: "<Right-Down>",
		0x07: "<Left-Up>",
		0x08: "<Left-Down>",
		0x09: "<Root Menu>",
		0x0A: "<Setup Menu>",
		0x0B: "<Contents Menu>",
		0x0C: "<Favorite Menu>",
		0x0D: "<Exit>",
		0x0E: "<Reserved 0x0E>",
		0x0F: "<Reserved 0x0F>",
		0x10: "<Media Top Menu>",
		0x11: "<Media Context-sensitive Menu>",
		0x12: "<Reserved 0x12>",
		0x13: "<Reserved 0x13>",
		0x14: "<Reserved 0x14>",
		0x15: "<Reserved 0x15>",
		0x16: "<Reserved 0x16>",
		0x17: "<Reserved 0x17>",
		0x18: "<Reserved 0x18>",
		0x19: "<Reserved 0x19>",
		0x1A: "<Reserved 0x1A>",
		0x1B: "<Reserved 0x1B>",
		0x1C: "<Reserved 0x1C>",
		0x1D: "<Number Entry Mode>",
		0x1E: "<Number 11>",
		0x1F: "<Number 12>",
		0x20: "<Number 0 or Number 10>",
		0x21: "<Number 1>",
		0x22: "<Number 2>",
		0x23: "<Number 3>",
		0x24: "<Number 4>",
		0x25: "<Number 5>",
		0x26: "<Number 6>",
		0x27: "<Number 7>",
		0x28: "<Number 8>",
		0x29: "<Number 9>",
		0x2A: "<Dot>",
		0x2B: "<Enter>",
		0x2C: "<Clear>",
		0x2D: "<Reserved 0x2D>",
		0x2E: "<Reserved 0x2E>",
		0x2F: "<Next Favorite>",
		0x30: "<Channel Up>",
		0x31: "<Channel Down>",
		0x32: "<Previous Channel>",
		0x33: "<Sound Select>",
		0x34: "<Input Select>",
		0x35: "<Display Informationen>",
		0x36: "<Help>",
		0x37: "<Page Up>",
		0x38: "<Page Down>",
		0x39: "<Reserved 0x39>",
		0x3A: "<Reserved 0x3A>",
		0x3B: "<Reserved 0x3B>",
		0x3C: "<Reserved 0x3C>",
		0x3D: "<Reserved 0x3D>",
		0x3E: "<Reserved 0x3E>",
		0x3F: "<Reserved 0x3F>",
		0x40: "<Power>",
		0x41: "<Volume Up>",
		0x42: "<Volume Down>",
		0x43: "<Mute>",
		0x44: "<Play>",
		0x45: "<Stop>",
		0x46: "<Pause>",
		0x47: "<Record>",
		0x48: "<Rewind>",
		0x49: "<Fast Forward>",
		0x4A: "<Eject>",
		0x4B: "<Forward>",
		0x4C: "<Backward>",
		0x4D: "<Stop-Record>",
		0x4E: "<Pause-Record>",
		0x4F: "<Reserved 0x4F>",
		0x50: "<Angle>",
		0x51: "<Sub Picture>",
		0x52: "<Video On Demand>",
		0x53: "<Electronic Program Guide>",
		0x54: "<Timer programming>",
		0x55: "<Initial Configuration>",
		0x56: "<Reserved 0x56>",
		0x57: "<Reserved 0x57>",
		0x58: "<Reserved 0x58>",
		0x59: "<Reserved 0x59>",
		0x5A: "<Reserved 0x5A>",
		0x5B: "<Reserved 0x5B>",
		0x5C: "<Reserved 0x5C>",
		0x5D: "<Reserved 0x5D>",
		0x5E: "<Reserved 0x5E>",
		0x5F: "<Reserved 0x5F>",
		0x60: "<Play Function>",
		0x61: "<Pause-Play Function>",
		0x62: "<Record Function>",
		0x63: "<Pause-Record Function>",
		0x64: "<Stop Function>",
		0x65: "<Mute Function>",
		0x66: "<Restore Volume Function>",
		0x67: "<Tune Function>",
		0x68: "<Select Media Function>",
		0x69: "<Select A/V Input Function>",
		0x6A: "<Select Audio Input Function>",
		0x6B: "<Power Toggle Function>",
		0x6C: "<Power Off Function>",
		0x6D: "<Power On Function>",
		0x6E: "<Reserved 0x6E>",
		0x6F: "<Reserved 0x6E>",
		0x70: "<Reserved 0x70>",
		0x71: "<F1 (Blue)>",
		0x72: "<F2 (Red)>",
		0x73: "<F3 (Green)>",
		0x74: "<F4 (Yellow)>",
		0x75: "<F5>",
		0x76: "<Data>",
		0x77: "<Reserved 0x77>",
		0x78: "<Reserved 0x78>",
		0x79: "<Reserved 0x79>",
		0x7A: "<Reserved 0x7A>",
		0x7B: "<Reserved 0x7B>",
		0x7C: "<Reserved 0x7C>",
		0x7D: "<Reserved 0x7D>",
		0x7E: "<Reserved 0x7E>",
		0x7F: "<Reserved 0x7F>"
	},
	0x64: {
		0x00: "<Display for default time>",
		0x40: "<Display until cleared>",
		0x80: "<Clear previous message>",
		0xC0: "<Reserved for future use>"
	},
	0x72: {
		0x00: "<Off>",
		0x01: "<On>"
	},
	0x7E: {
		0x00: "<Off>",
		0x01: "<On>"
	},
	0x84: {
		0x00: "<TV>",
		0x01: "<Recording Device>",
		0x02: "<Reserved>",
		0x03: "<Tuner>",
		0x04: "<Playback Devive>",
		0x05: "<Audio System>",
		0x06: "<Pure CEC Switch>",
		0x07: "<Video Processor>"
	},
	0x8D: {
		0x00: "<Activate>",
		0x01: "<Deactivate>",
		0x02: "<Query>"
	},
	0x8E: {
		0x00: "<Activated>",
		0x01: "<Deactivated>"
	},
	0x90: {
		0x00: "<On>",
		0x01: "<Standby>",
		0x02: "<In transition Standby to On>",
		0x03: "<In transition On to Standby>"
	},
	0x9A: {
		0x00: "<Rate Control Off>",
		0x01: "<WRC Standard Rate: 100% rate>",
		0x02: "<WRC Fast Rate: Max 101% rate>",
		0x03: "<WRC Slow Rate: Min 99% rate",
		0x04: "<NRC Standard Rate: 100% rate>",
		0x05: "<NRC Fast Rate: Max 100.1% rate>",
		0x06: "<NRC Slow Rate: Min 99.9% rate"
	},
	0x9E: {
		0x00: "<1.1>",
		0x01: "<1.2>",
		0x02: "<1.2a>",
		0x03: "<1.3>",
		0x04: "<1.3a>",
		0x05: "<1.4>",
		0x06: "<2.0>"
	},
}


class HdmiCec:
	instance = None
	KEY_VOLUP = 115
	KEY_VOLDOWN = 114
	KEY_VOLMUTE = 113

	def __init__(self):
		if config.hdmicec.enabled.value:
			try:
				if HdmiCec.instance:
					raise AssertionError("only one HdmiCec instance is allowed!")
			except:
				pass
			HdmiCec.instance = self

			self.wait = eTimer()
			self.wait.timeout.get().append(self.sendCmd)
			self.queue = []
			self.messages = []

			self.handleTimer = eTimer()
			self.stateTimer = eTimer()
			self.stateTimer.callback.append(self.stateTimeout)
			self.repeatTimer = eTimer()
			self.repeatTimer.callback.append(self.repeatMessages)
			self.cmdPollTimer = eTimer()
			self.cmdPollTimer.callback.append(self.CECcmdline)
			self.cmdWaitTimer = eTimer()
			self.repeatCounter = 0
			self.what = ""
			self.tv_lastrequest = ""
			self.tv_powerstate = "unknown"
			self.tv_skip_messages = False
			self.activesource = False
			self.firstrun = True
			self.standbytime = 0
			self.disk_full = False
			self.start_log = True

			self.sethdmipreemphasis()
			self.checkifPowerupWithoutWakingTv()  # Initially write "False" to file, see below.

			eHdmiCEC.getInstance().messageReceived.get().append(self.messageReceived)
			config.misc.standbyCounter.addNotifier(self.onEnterStandby, initial_call=False)
			config.misc.DeepStandby.addNotifier(self.onEnterDeepStandby, initial_call=False)
			self.setFixedPhysicalAddress(config.hdmicec.fixed_physical_address.value)

			self.volumeForwardingEnabled = False
			self.volumeForwardingDestination = 0
			eActionMap.getInstance().bindAction("", -maxsize - 1, self.keyEvent)
			config.hdmicec.volume_forwarding.addNotifier(self.configVolumeForwarding, initial_call=False)
			config.hdmicec.enabled.addNotifier(self.configVolumeForwarding)

			# Workaround for needless messages after cancel settings.
			self.old_configReportActiveMenu = config.hdmicec.report_active_menu.value
			self.old_configTVstate = config.hdmicec.check_tv_state.value or (config.hdmicec.tv_standby_notinputactive.value and config.hdmicec.control_tv_standby.value)
			#
			config.hdmicec.report_active_menu.addNotifier(self.configReportActiveMenu, initial_call=False)
			config.hdmicec.check_tv_state.addNotifier(self.configTVstate, initial_call=False)
			config.hdmicec.tv_standby_notinputactive.addNotifier(self.configTVstate, initial_call=False)
			config.hdmicec.control_tv_standby.addNotifier(self.configTVstate, initial_call=False)

			config.hdmicec.commandline.addNotifier(self.CECcmdstart)

			self.checkTVstate("firstrun")

	def getPhysicalAddress(self):
		physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
		hexstring = f"{physicaladdress:04x}"
		return hexstring[0] + "." + hexstring[1] + "." + hexstring[2] + "." + hexstring[3]

	def setFixedPhysicalAddress(self, address):
		if address != config.hdmicec.fixed_physical_address.value:
			config.hdmicec.fixed_physical_address.value = address
			config.hdmicec.fixed_physical_address.save()
		hexstring = address[0] + address[2] + address[4] + address[6]
		eHdmiCEC.getInstance().setFixedPhysicalAddress(int(float.fromhex(hexstring)))

	def messageReceived(self, message):
		if config.hdmicec.enabled.value:
			checkstate = self.stateTimer.isActive()
			data = 16 * "\x00"
			cmd = message.getCommand()
			_CECcmd = CECcmd.get(cmd, "<Polling Message>")
			length = message.getData(data, len(data))
			ctrl0 = message.getControl0()
			ctrl1 = message.getControl1()
			ctrl2 = message.getControl2()
			address = message.getAddress()
			print(f"[hdmiCEC][messageReceived]1: address={address}  CECcmd={_CECcmd}, cmd = {cmd}, ctrl0={ctrl0}, length={length} \n")
			cmdReceived = (config.hdmicec.commandline.value and self.cmdWaitTimer.isActive())
			if config.hdmicec.debug.value:
				if cmdReceived:
					# FIXME : improve debug for commandline
					self.CECdebug("Rx", address, cmd, data, length - 1, cmdReceived)
				else:
					self.debugRx(length, cmd, ctrl0)

			# // workaround for wrong address vom driver (e.g. hd51, message comes from tv -> address is only sometimes 0, dm920, same tv -> address is always 0)
			if address > 15:
				self.CECwritedebug("[HdmiCec] workaround for wrong address active", True)
				address = 0
			# //

			if cmd == 0x00:  # feature abort
				if length == 0:  # only polling message ( it's same as ping )
					print("eHdmiCec: received polling message")
				else:
					if ctrl0 == 68:  # feature abort
						print(f"[hdmiCEC][messageReceived]: volume forwarding not supported by device {address:02x}")
					# self.CECwritedebug("[HdmiCec] volume forwarding not supported by device %02x" % (address), True)
						self.volumeForwardingEnabled = False
			elif cmd == 0x46:  # request name
				self.sendMessage(address, "osdname")
			elif cmd in (0x7e, 0x72):  # system audio mode status
				if ctrl0 == 1:
					self.volumeForwardingDestination = 5  # on: send volume keys to receiver
				else:
					self.volumeForwardingDestination = 0  # off: send volume keys to tv
				print(f"[hdmiCEC][messageReceived]: volume forwarding={self.volumeForwardingDestination}, address={address} \n")
				if config.hdmicec.volume_forwarding.value:
					self.CECwritedebug(f"[HdmiCec] volume forwarding to device {self.volumeForwardingDestination:02x} enabled", True)
					self.volumeForwardingEnabled = True
			elif cmd == 0x8f:  # request power status
				if Screens.Standby.inStandby:
					self.sendMessage(address, "powerinactive")
				else:
					self.sendMessage(address, "poweractive")
			elif cmd == 0x83:  # request address
				self.sendMessage(address, "reportaddress")
			elif cmd == 0x85:  # request active source
				if not Screens.Standby.inStandby and config.hdmicec.report_active_source.value:
					self.sendMessage(address, "sourceactive")
			elif cmd == 0x8c:  # request vendor id
				self.sendMessage(address, "vendorid")
			elif cmd == 0x8d:  # menu request
				if ctrl0 == 1:  # query
					if Screens.Standby.inStandby:
						self.sendMessage(address, "menuinactive")
					else:
						self.sendMessage(address, "menuactive")
			elif cmd == 0x90:  # report power state from the tv
				if ctrl0 == 0:
					self.tv_powerstate = "on"
				elif ctrl0 == 1:
					self.tv_powerstate = "standby"
				elif ctrl0 == 2:
					self.tv_powerstate = "get_on"
				elif ctrl0 == 3:
					self.tv_powerstate = "get_standby"
				if checkstate and not self.firstrun:
					self.checkTVstate("powerstate")
				elif self.firstrun and not config.hdmicec.handle_deepstandby_events.value:
					self.firstrun = False
				else:
					self.checkTVstate()
			elif address == 0 and cmd == 0x36:  # handle standby request from the tv
				if config.hdmicec.handle_tv_standby.value != "disabled":
					self.handleTVRequest("tvstandby")
				self.checkTVstate("tvstandby")
			elif cmd == 0x80:  # routing changed
				ctrl3 = message.getControl3()
				oldaddress = ctrl0 * 256 + ctrl1
				newaddress = ctrl2 * 256 + ctrl3
				ouraddress = eHdmiCEC.getInstance().getPhysicalAddress()
				active = (newaddress == ouraddress)
				hexstring = f"{oldaddress:04x}"
				oldaddress = hexstring[0] + "." + hexstring[1] + "." + hexstring[2] + "." + hexstring[3]
				hexstring = f"{newaddress:04x}"
				newaddress = hexstring[0] + "." + hexstring[1] + "." + hexstring[2] + "." + hexstring[3]
				self.CECwritedebug(f"[HdmiCec] routing has changed... from '{oldaddress}' to '{newaddress}' (to our address: {active})", True)
			elif cmd in (0x86, 0x82):  # set streaming path, active source changed
				newaddress = ctrl0 * 256 + ctrl1
				ouraddress = eHdmiCEC.getInstance().getPhysicalAddress()
				active = (newaddress == ouraddress)
				if checkstate or self.activesource != active:
					if checkstate:
						txt = "our receiver is active source"
					else:
						txt = "active source"
						if cmd == 0x86:
							txt = "streaming path"
						txt += " has changed... to our address"
					self.CECwritedebug(f"[HdmiCec] {txt}: {active}", True)
				self.activesource = active
				if not checkstate:
					if cmd == 0x86 and not Screens.Standby.inStandby and self.activesource:
						self.sendMessage(address, "sourceactive")
						if config.hdmicec.report_active_menu.value:
							self.sendMessage(0, "menuactive")
					if config.hdmicec.handle_tv_input.value != "disabled":
						self.handleTVRequest("activesource")
					self.checkTVstate("changesource")
				else:
					self.checkTVstate("activesource")

			# handle wakeup requests from the tv
			wakeup = False
			if address == 0 and cmd == 0x44 and ctrl0 in (64, 109):  # handle wakeup from tv hdmi-cec menu (e.g. panasonic tv apps, viera link)
				wakeup = True
			elif not checkstate and config.hdmicec.handle_tv_wakeup.value != "disabled":
				if address == 0:
					if ((cmd == 0x04 and config.hdmicec.handle_tv_wakeup.value == "wakeup") or
						(cmd == 0x85 and config.hdmicec.handle_tv_wakeup.value == "sourcerequest") or
						(cmd == 0x46 and config.hdmicec.handle_tv_wakeup.value == "osdnamerequest") or
						(cmd != 0x36 and config.hdmicec.handle_tv_wakeup.value == "activity")):
						wakeup = True
					elif cmd == 0x84 and config.hdmicec.handle_tv_wakeup.value == "tvreportphysicaladdress":
						if (ctrl0 * 256 + ctrl1) == 0 and ctrl2 == 0:
							wakeup = True
				if (cmd == 0x80 and config.hdmicec.handle_tv_wakeup.value == "routingrequest") or (cmd == 0x86 and config.hdmicec.handle_tv_wakeup.value == "streamrequest"):
					if active:
						wakeup = True
			if wakeup:
				self.wakeup()

	def sendMessage(self, address, message):
		if config.hdmicec.enabled.value:
			cmd = 0
			data = b""
			if message == "wakeup":
				cmd = 0x04
			elif message == "sourceactive":
				address = 0x0f  # use broadcast address
				cmd = 0x82
				physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
				data = pack("BB", int(physicaladdress / 256), int(physicaladdress % 256))
			elif message == "routinginfo":
				address = 0x0f  # use broadcast address
				cmd = 0x81
				physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
				data = pack("BB", int(physicaladdress / 256), int(physicaladdress % 256))
			elif message == "standby":
				cmd = 0x36
			elif message == "sourceinactive":
				physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
				cmd = 0x9d
				data = pack("BB", int(physicaladdress / 256), int(physicaladdress % 256))
			elif message == "menuactive":
				cmd = 0x8e
				data = pack("B", 0x00)
			elif message == "menuinactive":
				cmd = 0x8e
				data = pack("B", 0x01)
			elif message == "givesystemaudiostatus":
				cmd = 0x7d
			elif message == "setsystemaudiomode":
				cmd = 0x70
				physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
				data = pack("BB", int(physicaladdress / 256), int(physicaladdress % 256))
			elif message == "activatesystemaudiomode":
				cmd = 0x72
				data = pack("B", 0x01)
			elif message == "deactivatesystemaudiomode":
				cmd = 0x72
				data = pack("B", 0x00)
			elif message == "osdname":
				cmd = 0x47
				data = uname()[1]
				data = data[:14]
				if not isinstance(data, bytes):
					data = data.encode(encoding='utf-8', errors='strict')
			elif message == "poweractive":
				cmd = 0x90
				data = pack("B", 0x00)
			elif message == "powerinactive":
				cmd = 0x90
				data = pack("B", 0x01)
			elif message == "reportaddress":
				address = 0x0f  # use broadcast address
				cmd = 0x84
				physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
				devicetype = eHdmiCEC.getInstance().getDeviceType()
				data = pack("BBB", int(physicaladdress / 256), int(physicaladdress % 256), devicetype)
			elif message == "vendorid":
				cmd = 0x87
				data = b"\x00\x00\x00"
			elif message == "keypoweron":
				cmd = 0x44
				data = pack("B", 0x6d)
			elif message == "keypoweroff":
				cmd = 0x44
				data = pack("B", 0x6c)
			elif message == "powerstate":
				cmd = 0x8f
			if cmd:
				try:
					data = data.decode("UTF-8")
				except:
					data = data.decode("ISO-8859-1")
				if config.misc.DeepStandby.value:  # no delay for messages before go in to deep-standby
					if config.hdmicec.debug.value:
						self.debugTx(address, cmd, data)
					eHdmiCEC.getInstance().sendMessage(address, cmd, data, len(data))
				else:
					self.queue.append((address, cmd, data))
					if not self.wait.isActive():
						self.wait.start(config.hdmicec.minimum_send_interval.value, True)

	def sendCmd(self):
		if len(self.queue):
			(address, cmd, data) = self.queue.pop(0)
			if config.hdmicec.debug.value:
				self.debugTx(address, cmd, data)
			eHdmiCEC.getInstance().sendMessage(address, cmd, data, len(data))
			self.wait.start(config.hdmicec.minimum_send_interval.value, True)

	def sendMessages(self, messages):
		self.firstrun = False
		self.queue = []
		self.sendMessagesIsActive(True)
		sendCnt = 0
		for send in messages:
			address = send[0]
			message = send[1]
			if self.what == "on" and ((self.repeatCounter > 0 or self.activesource) and (message == "standby" or (message == "wakeup" and not config.hdmicec.control_tv_wakeup.value))):  # skip active source workaround messages
				continue
			self.sendMessage(address, message)
			sendCnt += 1
		if sendCnt:
			self.repeatTimer.start((config.hdmicec.minimum_send_interval.value * (len(messages) + 1) + self.sendSlower()), True)

	def repeatMessages(self):
		if len(self.queue):
			self.repeatTimer.start(1000, True)
		elif self.firstrun:
			if self.stateTimer.isActive():
				self.repeatTimer.start(1000, True)
			else:
				self.sendMessages(self.messages)
		elif self.repeatCounter < config.hdmicec.messages_repeat.value and (self.what == "on" or (config.hdmicec.messages_repeat_standby.value and self.what == "standby")):
			self.repeatCounter += 1
			self.sendMessages(self.messages)
		else:
			self.repeatCounter = 0
			self.checkTVstate(self.what)

	def sendSlower(self):
		if config.hdmicec.messages_repeat.value and self.repeatCounter != config.hdmicec.messages_repeat.value:
			return config.hdmicec.messages_repeat_slowdown.value * (self.repeatCounter or 1)
		return 0

	def wakeupMessages(self):
		self.handleTimerStop()
		if self.tv_skip_messages:
			self.tv_skip_messages = False
			self.CECwritedebug("[HdmiCec] Skip turning on TV", True)
		elif self.checkifPowerupWithoutWakingTv() == "True":
			self.CECwritedebug("[HdmiCec] Skip waking TV, found 'True' in '/tmp/powerup_without_waking_tv.txt' (usually written by openWebif)", True)
		else:
			if config.hdmicec.enabled.value:
				self.messages = []
				self.what = "on"
				self.repeatCounter = 0
				if config.hdmicec.workaround_activesource.value and config.hdmicec.report_active_source.value and not self.activesource and "standby" not in self.tv_powerstate:
					# Some tv devices don't switch to the correct hdmi port if a another hdmi port active.  The workaround is to switch the tv off and on.
					self.messages.append((0, "standby"))
					if not config.hdmicec.control_tv_wakeup.value:
						self.messages.append((0, "wakeup"))
					#
				if config.hdmicec.control_tv_wakeup.value:
					self.messages.append((0, "wakeup"))
				if config.hdmicec.report_active_source.value:
					self.messages.append((0, "sourceactive"))
				if config.hdmicec.report_active_menu.value:
					if not config.hdmicec.report_active_source.value and self.activesource:
						self.messages.append((0, "sourceactive"))
					self.messages.append((0, "menuactive"))

				if config.hdmicec.control_receiver_wakeup.value:
					self.messages.append((5, "keypoweron"))
					self.messages.append((5, "setsystemaudiomode"))

				if self.firstrun:  # Wait for tv state and another messages on first start.
					self.repeatTimer.start(1000, True)
				else:
					self.sendMessages(self.messages)

			if isfile("/usr/script/TvOn.sh"):
				Console().ePopen("/usr/script/TvOn.sh &")

	def standbyMessages(self):
		self.handleTimerStop()
		if self.tv_skip_messages:
			self.tv_skip_messages = False
			self.CECwritedebug("[HdmiCec] Skip turning off TV", True)
		elif config.hdmicec.control_tv_standby.value and not config.hdmicec.tv_standby_notinputactive.value and not self.sendMessagesIsActive() and not self.activesource and "on" in self.tv_powerstate:
			self.CECwritedebug("[HdmiCec] Skip turning off TV - config: tv has another input active", True)
		else:
			if config.hdmicec.enabled.value:
				self.messages = []
				self.what = "standby"
				self.repeatCounter = 0
				if config.hdmicec.control_tv_standby.value:
					self.messages.append((0, "standby"))
				else:
					if config.hdmicec.report_active_source.value:
						self.messages.append((0, "sourceinactive"))
					if config.hdmicec.report_active_menu.value:
						self.messages.append((0, "menuinactive"))

				if config.hdmicec.control_receiver_standby.value:
					self.messages.append((5, "keypoweroff"))
					# self.messages.append((5, "standby"))

				self.sendMessages(self.messages)

			if isfile("/usr/script/TvOff.sh"):
				Console().ePopen("/usr/script/TvOff.sh &")

	def sendMessagesIsActive(self, stopMessages=False):
		if stopMessages:
			active = False
			if self.wait.isActive():
				self.wait.stop()
				active = True
			if self.repeatTimer.isActive():
				self.repeatTimer.stop()
				active = True
			if self.stateTimer.isActive():
				self.stateTimer.stop()
				active = True
			return active
		else:
			return self.repeatTimer.isActive() or self.stateTimer.isActive()

	def stateTimeout(self):
		self.CECwritedebug("[HdmiCec] timeout for check TV state!", True)
		if "on" in self.tv_powerstate:
			self.checkTVstate("activesource")
		elif self.tv_powerstate == "unknown":  # No response from tv - another input active? -> check if powered on.
			self.checkTVstate("getpowerstate")
		elif self.firstrun and not config.hdmicec.handle_deepstandby_events.value:
			self.firstrun = False

	def checkTVstate(self, state=""):
		if self.stateTimer.isActive():
			self.stateTimer.stop()

		timeout = 3000
		need_routinginfo = config.hdmicec.control_tv_standby.value and not config.hdmicec.tv_standby_notinputactive.value
		if "source" in state:
			self.tv_powerstate = "on"
			if state == "activesource" and self.what == "on" and config.hdmicec.report_active_source.value and not self.activesource and not self.firstrun:  # last try for switch to correct input
				self.sendMessage(0, "sourceactive")
				if need_routinginfo or config.hdmicec.check_tv_state.value:
					self.sendMessage(0, "routinginfo")
			if self.firstrun and not config.hdmicec.handle_deepstandby_events.value:
				self.firstrun = False
		elif state == "tvstandby":
			self.activesource = False
			self.tv_powerstate = "standby"
		elif state == "firstrun" and ((not config.hdmicec.handle_deepstandby_events.value and (need_routinginfo or config.hdmicec.report_active_menu.value)) or config.hdmicec.check_tv_state.value or config.hdmicec.workaround_activesource.value):
			self.stateTimer.start(timeout, True)
			self.sendMessage(0, "routinginfo")
		elif state == "firstrun" and not config.hdmicec.handle_deepstandby_events.value:
			self.firstrun = False
		elif config.hdmicec.check_tv_state.value or "powerstate" in state:
			if state == "getpowerstate" or state in ("on", "standby"):
				self.activesource = False
				if state in ("on", "standby"):
					self.tv_powerstate = "unknown"
				else:
					self.tv_powerstate = "getpowerstate"
				self.stateTimer.start(timeout, True)
				self.sendMessage(0, "powerstate")
			elif state == "powerstate" and "on" in self.tv_powerstate:
				self.stateTimer.start(timeout, True)
				self.sendMessage(0, "routinginfo")
		else:
			if state == "on" and need_routinginfo:
				self.activesource = False
				self.tv_powerstate = "unknown"
				self.stateTimer.start(timeout, True)
				self.sendMessage(0, "routinginfo")
			elif state == "standby" and config.hdmicec.control_tv_standby.value:
				self.activesource = False
				self.tv_powerstate = "standby"

	def handleTimerStop(self, reset=False):
		if reset:
			self.tv_skip_messages = False
		if self.handleTimer.isActive():
			self.handleTimer.stop()
			if len(self.handleTimer.callback):
				target = "standby"
				if "deep" in str(self.handleTimer.callback[0]):
					target = "deep " + target
				self.CECwritedebug(f"[HdmiCec] stopping Timer to {target}", True)

	def handleTVRequest(self, request):
		if (request == "activesource" and self.activesource) or (self.tv_lastrequest == "tvstandby" and request == "activesource" and self.handleTimer.isActive()):
			self.handleTimerStop(True)
		elif ((request == self.tv_lastrequest or self.tv_lastrequest == "tvstandby") and self.handleTimer.isActive()) or (request == "activesource" and not self.activesource and self.sendMessagesIsActive()):
			return
		else:
			self.handleTimerStop(True)
			self.tv_lastrequest = request

			standby = deepstandby = False
			if config.hdmicec.handle_tv_standby.value != "disabled" and request == "tvstandby":
				self.tv_skip_messages = False
				if config.hdmicec.handle_tv_standby.value == "standby":
					standby = True
				elif config.hdmicec.handle_tv_standby.value == "deepstandby":
					deepstandby = True
			elif config.hdmicec.handle_tv_input.value != "disabled" and request == "activesource":
				self.tv_skip_messages = True
				if config.hdmicec.handle_tv_input.value == "standby":
					standby = True
				elif config.hdmicec.handle_tv_input.value == "deepstandby":
					deepstandby = True

			if standby and Screens.Standby.inStandby:
				self.tv_skip_messages = False
				return
			elif standby or deepstandby:
				while len(self.handleTimer.callback):
					self.handleTimer.callback.pop()

			if standby:
				if config.hdmicec.handle_tv_delaytime.value:
					self.handleTimer.callback.append(self.standby)
					self.handleTimer.startLongTimer(config.hdmicec.handle_tv_delaytime.value)
					self.CECwritedebug(f"[HdmiCec] starting Timer to standby in {config.hdmicec.handle_tv_delaytime.value} s", True)
				else:
					self.standby()
			elif deepstandby:
				if config.hdmicec.handle_tv_delaytime.value:
					self.handleTimer.callback.append(self.deepstandby)
					self.handleTimer.startLongTimer(config.hdmicec.handle_tv_delaytime.value)
					self.CECwritedebug(f"[HdmiCec] starting Timer to deep standby in {config.hdmicec.handle_tv_delaytime.value} s", True)
				else:
					self.deepstandby()

	def deepstandby(self):
		import NavigationInstance
		now = time()
		recording = NavigationInstance.instance.getRecordingsCheckBeforeActivateDeepStandby()
		rectimer = abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - now) <= 900 or NavigationInstance.instance.RecordTimer.getStillRecording() or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - now) <= 900
		scheduler = abs(NavigationInstance.instance.Scheduler.getNextPowerManagerTime() - now) <= 900 or NavigationInstance.instance.Scheduler.isProcessing(exceptTimer=0) or not NavigationInstance.instance.Scheduler.isAutoDeepstandbyEnabled()
		if recording or rectimer or scheduler:
			self.CECwritedebug(f"[HdmiCec] go not into deepstandby... recording={recording}, rectimer={rectimer}, scheduler={scheduler}", True)
			self.standby()
		else:
			from Screens.InfoBar import InfoBar
			if InfoBar and InfoBar.instance:
				self.CECwritedebug("[HdmiCec] go into deepstandby...", True)
				InfoBar.instance.openInfoBarSession(Screens.Standby.TryQuitMainloop, 1)

	def standby(self):
		if not Screens.Standby.inStandby:
			import NavigationInstance
			NavigationInstance.instance.skipWakeup = True
			from Screens.InfoBar import InfoBar
			if InfoBar and InfoBar.instance:
				self.CECwritedebug("[HdmiCec] go into standby...", True)
				InfoBar.instance.openInfoBarSession(Screens.Standby.Standby)

	def wakeup(self):
		if config.hdmicec.workaround_turnbackon.value and self.standbytime > time():
			self.CECwritedebug(f"[HdmiCec] ignore wakeup for {int(self.standbytime - time())} seconds ...", True)
			return
		self.standbytime = 0
		self.handleTimerStop(True)
		if Screens.Standby.inStandby:
			self.CECwritedebug("[HdmiCec] wake up...", True)
			Screens.Standby.inStandby.Power()

	def onLeaveStandby(self):
		self.wakeupMessages()

	def onEnterStandby(self, configElement):
		self.standbytime = time() + config.hdmicec.workaround_turnbackon.value
		Screens.Standby.inStandby.onClose.append(self.onLeaveStandby)
		self.standbyMessages()

	def onEnterDeepStandby(self, configElement):
		if config.hdmicec.handle_deepstandby_events.value:
			self.standbyMessages()

	def configVolumeForwarding(self, configElement):
		if config.hdmicec.enabled.value and config.hdmicec.volume_forwarding.value:
			self.volumeForwardingEnabled = True
			self.sendMessage(5, "givesystemaudiostatus")
		else:
			self.volumeForwardingEnabled = False

	def configReportActiveMenu(self, configElement):
		if self.old_configReportActiveMenu == config.hdmicec.report_active_menu.value:
			return
		self.old_configReportActiveMenu = config.hdmicec.report_active_menu.value
		if config.hdmicec.report_active_menu.value:
			self.sendMessage(0, "sourceactive")
			self.sendMessage(0, "menuactive")
		else:
			self.sendMessage(0, "menuinactive")

	def configTVstate(self, configElement):
		if self.old_configTVstate == (config.hdmicec.check_tv_state.value or (config.hdmicec.tv_standby_notinputactive.value and config.hdmicec.control_tv_standby.value)):
			return
		self.old_configTVstate = config.hdmicec.check_tv_state.value or (config.hdmicec.tv_standby_notinputactive.value and config.hdmicec.control_tv_standby.value)
		if not self.sendMessagesIsActive() and self.old_configTVstate:
			self.sendMessage(0, "powerstate")
			self.sendMessage(0, "routinginfo")

	def keyEvent(self, keyCode, keyEvent):
		if not self.volumeForwardingEnabled:
			return
		cmd = 0
		address = keyEvent
		data = b""
		if keyEvent in (0, 2):
			if keyCode == self.KEY_VOLUP:
				cmd = 0x44
				data = pack("B", 0x41)
			elif keyCode == self.KEY_VOLDOWN:
				cmd = 0x44
				data = pack("B", 0x42)
			elif keyCode == self.KEY_VOLMUTE:
				cmd = 0x44
				data = pack("B", 0x43)
		elif keyEvent == 1 and keyCode in (self.KEY_VOLMUTE, self.KEY_VOLDOWN, self.KEY_VOLUP):
			cmd = 0x45
		if cmd:
			try:
				data = data.decode("UTF-8")
			except:
				data = data.decode("ISO-8859-1")

			if config.hdmicec.debug.value:
				self.debugTx(address, cmd, data)
			eHdmiCEC.getInstance().sendMessage(self.volumeForwardingDestination, cmd, data, len(data))
			return 1
		else:
			return 0

	def debugTx(self, address, cmd, data):
		txt = self.now(True) + self.opCode(cmd, True) + " " + f"{cmd:02X}" + " "
		tmp = ""
		if len(data):
			if cmd in [0x32, 0x47]:
				for item in data:
					tmp += f"{item}"
			else:
				for item in data:
					tmp += f"{ord(item):02X}" + " "
		tmp += 48 * " "
		self.CECwritedebug(txt + tmp[:48] + f"[0x{address:02X}]")

	def debugRx(self, length, cmd, ctrl):
		txt = self.now()
		if cmd == 0 and length == 0:
			txt += self.opCode(cmd) + " - "
		else:
			if cmd == 0:
				txt += "<Feature Abort>" + 13 * " " + "<  " + f"{cmd:02X}" + " "
			else:
				txt += self.opCode(cmd) + " " + f"{cmd:02X}" + " "
			if cmd == 0x9e:
				txt += f"{ctrl:02X}" + 3 * " " + f"[version: {CEC[ctrl]}]"
			else:
				txt += f"{ctrl:02X}" + " "
		self.CECwritedebug(txt)

	def opCode(self, cmd, out=False):
		send = ">" if out else "<"
		opCode = ""
		if cmd in CECcmd:
			opCode += f"{CECcmd[cmd]}"
		opCode += 30 * " "
		return opCode[:28] + send + " "

	def now(self, out=False, fulldate=False):
		send = "Tx: " if out else "Rx: "
		now = datetime.now()
		if fulldate:
			return send + now.strftime("%d-%m-%Y %H:%M:%S") + 2 * " "
		return send + now.strftime("%H:%M:%S") + 2 * " "

	def sethdmipreemphasis(self):
		f = "/proc/stb/hdmi/preemphasis"
		if fileExists(f):
			if config.hdmicec.preemphasis.value:
				self.CECwritefile(f, "w", "on")
			else:
				self.CECwritefile(f, "w", "off")

	def checkifPowerupWithoutWakingTv(self):
		f = "/tmp/powerup_without_waking_tv.txt"
		# Returns "True" if openWebif function "Power on without TV" has written "True" to this file:
		powerupWithoutWakingTv = (self.CECreadfile(f) or "False") if fileExists(f) else "False"
		# Write "False" to the file so that turning on the TV is only suppressed once
		# (and initially, so that openWebif knows that the image supports this feature).
		self.CECwritefile(f, "w", "False")
		return powerupWithoutWakingTv

	def CECdebug(self, type, address, cmd, data, length, cmdmsg=False):
		txt = f"<{type}:> "
		tmp = f"{address:02X} "
		tmp += f"{cmd:02X} "
		for idx in range(length):
			tmp += f"{ord(data[idx]):02X} "
		if cmdmsg:
			self.CECcmdline(tmp)
			if not config.hdmicec.debug.value:
				return
		txt += f"{tmp.rstrip() + (47 - len(tmp.rstrip())) * ' '} "
		txt += CECaddr.get(address, UNKNOWN)
		if not cmd and not length:
			txt += "<Polling Message>"
		else:
			txt += CECcmd.get(cmd, "<Polling Message>")
			if cmd in (0x07, 0x09, 0x33, 0x34, 0x35, 0x92, 0x93, 0x97, 0x99, 0xA1, 0xA2):
				txt += "<unknown (not implemented yet)>"
			elif cmd == 0x00:
				if length == 2:
					txt += CECcmd.get(ord(data[0]), UNKNOWN)
					txt += CECdat.get(cmd, "").get(ord(data[1]), UNKNOWN)
				else:
					txt += WRONG_DATA_LENGTH
			elif cmd in (0x70, 0x80, 0x81, 0x82, 0x84, 0x86, 0x9D):
				if (cmd == 0x80 and length == 4) or (cmd == 0x84 and length == 3) or (cmd not in (0x80, 0x84) and length == 2):
					hexstring = f"{ord(data[0]) * 256 + ord(data[1]):04x}"
					txt += f"<{hexstring[0]}.{hexstring[1]}.{hexstring[2]}.{hexstring[3]}>"
					if cmd == 0x80:
						hexstring = f"{ord(data[2]) * 256 + ord(data[3]):04x}"
						txt += f"<{hexstring[0]}.{hexstring[1]}.{hexstring[2]}.{hexstring[3]}>"
					elif cmd == 0x84:
						txt += CECdat.get(cmd, "").get(ord(data[2]), UNKNOWN)
				else:
					txt += WRONG_DATA_LENGTH
			elif cmd in (0x87, 0xA0):
				if length > 2:
					txt += "<%d>" % (ord(data[0]) * 256 * 256 + ord(data[1]) * 256 + ord(data[2]))
					if cmd == 0xA0:
						txt += "<Vendor Specific Data>"
				else:
					txt += WRONG_DATA_LENGTH
			elif cmd in (0x32, 0x47, 0x64, 0x67):
				if length:
					s = 0
					if cmd == 0x64:
						s = 1
						txt += CECdat.get(cmd, "").get(ord(data[0]), UNKNOWN)
					txt += "<"
					for idx in range(s, length):
						txt += f"{data[idx]}"
					txt += ">"
				else:
					txt += WRONG_DATA_LENGTH
			elif cmd == 0x7A:
				if length == 1:
					val = ord(data[0])
					txt += "<Audio Mute On>" if val >= 0x80 else "<Audio Mute Off>"
					txt += "<Volume %d>" % (val - 0x80) if val >= 0x80 else "<Volume %d>" % val
				else:
					txt += WRONG_DATA_LENGTH
			elif length:
				txt += CECdat.get(cmd, "").get(ord(data[0]), UNKNOWN) if cmd in CECdat else ""
			else:
				txt += CECdat.get(cmd, "")
		self.CECwritedebug(txt)

	def CECwritedebug(self, debugtext, debugprint=False):
		if debugprint and not config.hdmicec.debug.value:
			print(debugtext)
			return
		log_path = config.crash.debug_path.value
		if pathExists(log_path):
			stat = statvfs(log_path)
			disk_free = stat.f_bavail * stat.f_bsize / 1024
			if self.disk_full:
				self.start_log = True
			if not self.disk_full and disk_free < 500:
				print("[HdmiCec] write debug file failed - disk full!")
				self.disk_full = True
				return
			elif not self.disk_full and disk_free < 1000:
				self.disk_full = True
			elif disk_free >= 1000:
				self.disk_full = False
			else:
				return
			now = datetime.now()
			debugfile = pathjoin(log_path, now.strftime("Enigma2-hdmicec-%Y%m%d.log"))
			timestamp = now.strftime("%H:%M:%S.%f")[:-2]
			debugtext = f"{timestamp} {'[   ] ' if debugprint else ''}{debugtext.replace('[HdmiCec] ', '')}\n"
			if self.start_log:
				self.start_log = False
				la = eHdmiCEC.getInstance().getLogicalAddress()
				debugtext = f"{timestamp}  +++  start logging  +++  physical address: {self.getPhysicalAddress()}  -  logical address: {la}  -  device type: {CECaddr.get(la, UNKNOWN)}\n{debugtext}"
			if self.disk_full:
				debugtext += f"{timestamp}  +++  stop logging  +++  disk full!\n"
			self.CECwritefile(debugfile, "a", debugtext)
		else:
			print(f"[HdmiCec] write debug file failed - log path ({log_path}) not found!")

	def CECcmdstart(self, configElement):
		if config.hdmicec.commandline.value:
			self.CECcmdline("start")
		else:
			self.CECcmdline("stop")

	def CECcmdline(self, received=None):
		polltime = 1
		waittime = 3
		if self.cmdPollTimer.isActive():
			self.cmdPollTimer.stop()
		if not config.hdmicec.enabled.value or received in ("start", "stop"):
			self.CECremovefiles((cmdfile, msgfile, errfile))
			if received == "start":
				self.cmdPollTimer.startLongTimer(polltime)
			return
		if received:
			self.CECwritefile(msgfile, "w", received.rstrip().replace(" ", ":") + "\n")
			if self.cmdWaitTimer.isActive():
				self.cmdWaitTimer.stop()
		if self.firstrun or self.sendMessagesIsActive():
			self.cmdPollTimer.startLongTimer(polltime)
			return
		if fileExists(cmdfile):
			files = [cmdfile, errfile]
			if received is None and not self.cmdWaitTimer.isActive():
				files.append(msgfile)
			ceccmd = self.CECreadfile(cmdfile).strip().split(":")
			self.CECremovefiles(files)
			if len(ceccmd) == 1 and not ceccmd[0]:
				e = "Empty input file!"
				self.CECwritedebug(f"[HdmiCec] CECcmdline - error: {e}", True)
				txt = f"{e}\n"
				self.CECwritefile(errfile, "w", txt)
			elif ceccmd[0] in ("help", "?"):
				internaltxt = "  Available internal commands: "
				space = len(internaltxt) * " "
				addspace = False
				for key in sorted(CECintcmd.keys()):
					internaltxt += f"{space if addspace else ''}'{key}' or '{CECintcmd[key]}'\n"
					addspace = True
				txt = "Help for the hdmi-cec command line function\n"
				txt += "-------------------------------------------\n\n"
				txt += "Files:\n"
				txt += f"- Input file to send the hdmi-cec command line: '{cmdfile}'\n"
				txt += f"- Output file for received hdmi-cec messages:   '{msgfile}'\n"
				txt += f"- Error file for hdmi-cec command line errors:  '{errfile}'\n"
				txt += f"- This help file:                               '{hlpfile}'\n\n"
				txt += "Functions:\n"
				txt += f"- Help: Type 'echo help > {cmdfile}' to create this file.\n\n"
				txt += f"- Send internal commands: address:command (e.g. Type 'echo 00:wakeup > {cmdfile}' for wakeup the TV device.)\n"
				txt += f"{internaltxt}\n"
				txt += f"- Send individual commands: address:command:data (e.g. Type 'echo 00:04 > {cmdfile}' for wakeup the TV device.)\n"
				txt += f"  Available individual commands: {cecinfo}\n\n"
				txt += "Info:\n"
				txt += "- Input and error file will removed with send a new command line. Output file will removed if not waiting for a message.\n"
				txt += "  (If the command was accepted successfully, the input file is deleted and no error file exist.)\n"
				txt += f"- Poll time for new command line is {polltime} second. Maximum wait time for one received message is {waittime} seconds after send the hdmi-cec command.\n"
				txt += f"  (After the first incoming message and outside this waiting time no more received messages will be write to '{msgfile}'.)\n"
				txt += "- Address, command and optional data must write as hex values and text for internal command must write exactly!\n\n"
				txt += "End\n"
				self.CECwritefile(hlpfile, "w", txt)
			else:
				try:
					if not ceccmd[0] or (ceccmd[0] and len(ceccmd[0].strip()) > 2):
						raise Exception(f"Wrong address detected - '{ceccmd[0]}'")
					address = int(ceccmd[0] or "0", 16)
					if len(ceccmd) > 1:
						if ceccmd[1] in CECintcmd:
							self.sendMessage(address, CECintcmd[ceccmd[1]])
						elif ceccmd[1] in list(CECintcmd.values()):
							self.sendMessage(address, ceccmd[1])
						else:
							for x in ceccmd[1:]:
								if len(x.strip()) > 2:
									raise Exception(f"Wrong command or incorrect data detected - '{x}'")
							data = b""
							cmd = int(ceccmd[1] or "0", 16)
							if len(ceccmd) > 2:
								for d in ceccmd[2:]:
									data += pack("B", int(d or "0", 16))

							try:
								data = data.decode("UTF-8")
							except:
								data = data.decode("ISO-8859-1")

							if config.hdmicec.debug.value:
								self.debugTx(address, cmd, data)

							eHdmiCEC.getInstance().sendMessage(address, cmd, data, len(data))
						self.cmdWaitTimer.startLongTimer(waittime)
				except Exception as e:
					self.CECwritedebug(f"[HdmiCec] CECcmdline - error: {e}", True)
					txt = f"{e}\n"
					self.CECwritefile(errfile, "w", txt)
		self.cmdPollTimer.startLongTimer(polltime)

	def CECreadfile(self, FILE):
		try:
			with open(FILE) as f:
				return f.read()
		except Exception as e:
			self.CECwritedebug(f"[HdmiCec] read file '{FILE}' failed - error: {e}", True)
		return ""

	def CECwritefile(self, FILE, MODE, INPUT):
		try:
			with open(FILE, MODE) as f:
				f.write(INPUT)
		except Exception as e:
			txt = f"[HdmiCec] write file '{FILE}' failed - error: {e}"
			print(txt if "Enigma2-hdmicec-" in FILE else self.CECwritedebug(txt, True))

	def CECremovefiles(self, FILES):
		for f in FILES:
			if fileExists(f):
				try:
					remove(f)
				except Exception as e:
					self.CECwritedebug(f"[HdmiCec] remove file '{f}' failed - error: {e}", True)

	def keyVolUp(self):  # keyVolUp for hbbtv
		if self.volumeForwardingEnabled:
			self.keyEvent(self.KEY_VOLUP, 0)
			self.keyEvent(self.KEY_VOLUP, 1)
			return 1
		else:
			return 0

	def keyVolDown(self):  # keyVolDown for hbbtv
		if self.volumeForwardingEnabled:
			self.keyEvent(self.KEY_VOLDOWN, 0)
			self.keyEvent(self.KEY_VOLDOWN, 1)
			return 1
		else:
			return 0

	def keyVolMute(self):  # keyVolMute for hbbtv
		if self.volumeForwardingEnabled:
			self.keyEvent(self.KEY_VOLMUTE, 0)
			self.keyEvent(self.KEY_VOLMUTE, 1)
			return 1
		else:
			return 0


hdmi_cec = HdmiCec()
