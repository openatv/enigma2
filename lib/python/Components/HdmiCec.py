import struct
import os
from fcntl import ioctl
from sys import maxint
from enigma import eTimer, eHdmiCEC, eActionMap
from config import config, ConfigSelection, ConfigYesNo, ConfigSubsection, ConfigText, NoSave, ConfigInteger
from Components.Console import Console
from Tools.StbHardware import getFPWasTimerWakeup
from Tools.Directories import fileExists
import Screens.Standby

config.hdmicec = ConfigSubsection()
config.hdmicec.enabled = ConfigYesNo(default = False)
config.hdmicec.control_tv_standby = ConfigYesNo(default = True)
config.hdmicec.control_tv_wakeup = ConfigYesNo(default = True)
config.hdmicec.report_active_source = ConfigYesNo(default = True)
config.hdmicec.report_active_menu = ConfigYesNo(default = True)
choicelist = [
	("disabled", _("Disabled")),
	("standby", _("Standby")),
	("deepstandby", _("Deep standby")),
	]
config.hdmicec.handle_tv_standby = ConfigSelection(default = "standby", choices = choicelist)
config.hdmicec.handle_tv_input = ConfigSelection(default = "standby", choices = choicelist)
config.hdmicec.handle_tv_wakeup = ConfigSelection(
	choices = {
	"disabled": _("Disabled"),
	"wakeup": _("Wakeup"),
	"tvreportphysicaladdress": _("TV physical address report"),
	"routingrequest": _("Routing request"),
	"sourcerequest": _("Source request"),
	"streamrequest": _("Stream request"),
	"osdnamerequest": _("OSD name request"),
	"activity": _("Any activity"),
	},
	default = "streamrequest")
config.hdmicec.fixed_physical_address = ConfigText(default = "0.0.0.0")
config.hdmicec.volume_forwarding = ConfigYesNo(default = False)
config.hdmicec.control_receiver_wakeup = ConfigYesNo(default = False)
config.hdmicec.control_receiver_standby = ConfigYesNo(default = False)
config.hdmicec.handle_deepstandby_events = ConfigYesNo(default = False)
config.hdmicec.preemphasis = ConfigYesNo(default = False)
choicelist = []
for i in (10, 50, 100, 150, 250, 500, 750, 1000, 1500, 2000):
	choicelist.append(("%d" % i, "%d ms" % i))
config.hdmicec.minimum_send_interval = ConfigSelection(default = "0", choices = [("0", _("Disabled"))] + choicelist)
choicelist = []
for i in range(1,11):
	choicelist.append(("%d" % i, _("%d times") % i))
config.hdmicec.messages_repeat = ConfigSelection(default = "0", choices = [("0", _("Disabled"))] + choicelist)
choicelist = []
for i in (10,30,60,120,300,600,900,1800,3600):
	if i/60<1:
		choicelist.append(("%d" % i, _("%d sec") % i))
	else:
		choicelist.append(("%d" % i, _("%d min") % (i/60)))
config.hdmicec.handle_tv_delaytime = ConfigSelection(default = "300", choices = choicelist)
config.hdmicec.handle_tv_standby_to_deepstandby = ConfigYesNo(default = True)
config.hdmicec.check_tv_powerstate = ConfigYesNo(default = False)
config.hdmicec.deepstandby_waitfortimesync = ConfigYesNo(default = True)
config.hdmicec.tv_standby_notinstandby = ConfigYesNo(default = True)
config.hdmicec.tv_standby_notinputactive = ConfigYesNo(default = False)
config.hdmicec.tv_wakeup_zaptimer = ConfigYesNo(default = True)
config.hdmicec.tv_wakeup_zapandrecordtimer = ConfigYesNo(default = False)
config.hdmicec.tv_wakeup_wakeuppowertimer = ConfigYesNo(default = False)
config.hdmicec.active_source_alreadyon = ConfigYesNo(default = False)
config.hdmicec.active_source_zaptimer = ConfigYesNo(default = True)
config.hdmicec.active_source_zapandrecordtimer = ConfigYesNo(default = False)
config.hdmicec.active_source_wakeuppowertimer = ConfigYesNo(default = False)

#nice cec info site: http://www.cec-o-matic.com/

class HdmiCec:
	instance = None

	def __init__(self):
		if config.hdmicec.enabled.value:
			assert not HdmiCec.instance, "only one HdmiCec instance is allowed!"
			HdmiCec.instance = self

			self.wait = eTimer()
			self.wait.timeout.get().append(self.sendCmd)
			self.queue = []
			self.messages = []

			eHdmiCEC.getInstance().messageReceived.get().append(self.messageReceived)
			config.misc.standbyCounter.addNotifier(self.onEnterStandby, initial_call = False)
			config.misc.DeepStandby.addNotifier(self.onEnterDeepStandby, initial_call = False)
			self.setFixedPhysicalAddress(config.hdmicec.fixed_physical_address.value)

			self.volumeForwardingEnabled = False
			self.volumeForwardingDestination = 0
			eActionMap.getInstance().bindAction('', -maxint - 1, self.keyEvent)
			config.hdmicec.volume_forwarding.addNotifier(self.configVolumeForwarding)
			config.hdmicec.enabled.addNotifier(self.configVolumeForwarding)

			self.handleTimer = eTimer()
			self.stateTimer = eTimer()
			self.stateTimer.callback.append(self.checkTVPowerState)
			self.repeatTimer = eTimer()
			self.repeatTimer.callback.append(self.repeatMessages)
			self.stateCounter = 0
			self.repeatCounter = 0
			self.what = ''
			self.recall = None
			self.firststart =  True
			self.skipreceived = False
			self.activesource = False
			self.tv_lastrequest = False, False
			self.tv_powerstate = ''
			self.tv_powerstate_on_wakeup = ''
			self.tv_skip_setinput = False
			self.tv_skip_messages = False
			self.sethdmipreemphasis()
			self.checkTVPowerState()
			dummy = self.checkifPowerupWithoutWakingTv() # initially write 'False' to file, see below

	def getPhysicalAddress(self):
		physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
		hexstring = '%04x' % physicaladdress
		return hexstring[0] + '.' + hexstring[1] + '.' + hexstring[2] + '.' + hexstring[3]

	def setFixedPhysicalAddress(self, address):
		if address != config.hdmicec.fixed_physical_address.value:
			config.hdmicec.fixed_physical_address.value = address
			config.hdmicec.fixed_physical_address.save()
		hexstring = address[0] + address[2] + address[4] + address[6]
		eHdmiCEC.getInstance().setFixedPhysicalAddress(int(float.fromhex(hexstring)))

	def sendMessage(self, address, message):
		if config.hdmicec.enabled.value:
			cmd = 0
			data = ''
			if message == "wakeup":
				cmd = 0x04
			elif message == "sourceactive":
				address = 0x0f # use broadcast for active source command
				cmd = 0x82
				physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
				data = str(struct.pack('BB', int(physicaladdress/256), int(physicaladdress%256)))
			elif message == "routinginfo":
				address = 0x0f # use broadcast address
				cmd = 0x81
				physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
				data = str(struct.pack('BB', int(physicaladdress/256), int(physicaladdress%256)))
			elif message == "standby":
				cmd = 0x36
			elif message == "sourceinactive":
				physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
				cmd = 0x9d
				data = str(struct.pack('BB', int(physicaladdress/256), int(physicaladdress%256)))
			elif message == "menuactive":
				cmd = 0x8e
				data = str(struct.pack('B', 0x00))
			elif message == "menuinactive":
				cmd = 0x8e
				data = str(struct.pack('B', 0x01))
			elif message == "givesystemaudiostatus":
				cmd = 0x7d
				address = 0x05
			elif message == "setsystemaudiomode":
				cmd = 0x70
				address = 0x05
				physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
				data = str(struct.pack('BB', int(physicaladdress/256), int(physicaladdress%256)))
			elif message == "osdname":
				cmd = 0x47
				data = os.uname()[1]
				data = data[:14]
			elif message == "poweractive":
				cmd = 0x90
				data = str(struct.pack('B', 0x00))
			elif message == "powerinactive":
				cmd = 0x90
				data = str(struct.pack('B', 0x01))
			elif message == "reportaddress":
				address = 0x0f # use broadcast address
				cmd = 0x84
				physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
				devicetype = eHdmiCEC.getInstance().getDeviceType()
				data = str(struct.pack('BBB', int(physicaladdress/256), int(physicaladdress%256), devicetype))
			elif message == "vendorid":
				cmd = 0x87
				data = '\x00\x00\x00'
			elif message == "keypoweron":
				cmd = 0x44
				data = str(struct.pack('B', 0x6d))
			elif message == "keypoweroff":
				cmd = 0x44
				data = str(struct.pack('B', 0x6c))
			elif message == "powerstate":
				cmd = 0x8f
			if cmd:
				if config.hdmicec.minimum_send_interval.value != "0" and message != "standby": # Use no interval time when message is standby. usefull for Panasonic TV
					self.queue.append((address, cmd, data))
					if not self.wait.isActive():
						self.wait.start(int(config.hdmicec.minimum_send_interval.value), True)
				else:
					eHdmiCEC.getInstance().sendMessage(address, cmd, data, len(data))

	def sendCmd(self):
		if len(self.queue):
			(address, cmd, data) = self.queue.pop(0)
			eHdmiCEC.getInstance().sendMessage(address, cmd, data, len(data))
			self.wait.start(int(config.hdmicec.minimum_send_interval.value), True)

	def repeatMessages(self):
		if len(self.queue):
			self.repeatTimer.start(1000, True)
		elif not int(config.hdmicec.messages_repeat.value):
			self.setAdditionalMessages()
		else:
			if (self.repeatCounter < int(config.hdmicec.messages_repeat.value) and not (config.hdmicec.check_tv_powerstate.value and self.what == self.tv_powerstate) and
				(config.hdmicec.control_tv_wakeup.value and self.what == 'on' or config.hdmicec.control_tv_standby.value and self.what == 'standby')):
				self.sendMessages(self.messages)
				self.repeatCounter += 1
			else:
				if config.hdmicec.control_tv_wakeup.value and self.what == 'on' and not 'on' in self.tv_powerstate:
					self.tv_powerstate = 'unknown'
					print '[HdmiCec] wakeup TV failed !!!'
				elif config.hdmicec.control_tv_standby.value and self.what == 'standby' and not 'standby' in self.tv_powerstate:
					self.tv_powerstate = 'unknown'
					print '[HdmiCec] standby TV failed !!!'
				self.setAdditionalMessages()

	def setAdditionalMessages(self):
		self.skipreceived = False
		if 'on' in self.what and config.hdmicec.report_active_source.value and not self.activesource and not self.tv_skip_setinput:
			self.sendMessage(0, "sourceactive")
		if not Screens.Standby.inStandby and 'on' in self.tv_powerstate:
			self.skipreceived = True
			self.sendMessage(0, 'routinginfo')
		self.tv_skip_setinput = False

	def sendMessages(self, messages):
		self.queue = []
		if self.wait.isActive():
			self.wait.stop()
		if self.repeatTimer.isActive():
			self.repeatTimer.stop()
		for send in messages:
			address = send[0]
			message = send[1]
			self.skipreceived = True
			self.sendMessage(address, message)
		self.repeatTimer.start(int(config.hdmicec.minimum_send_interval.value)*len(messages)+1000, True)

	def wakeupMessages(self, powerCheck = True, powerCheckOK = False):
		self.handleTimerStop()
		if self.tv_skip_messages:
			self.tv_skip_messages = False
			self.tv_skip_setinput = False
			print "[HdmiCec] Skip turning on TV"
			return
		elif powerCheck:
			self.checkTVPowerState(True, self.wakeupMessages)
			return

		if config.hdmicec.report_active_source.value and not config.hdmicec.active_source_alreadyon.value and 'on' in self.tv_powerstate:
			print "[HdmiCec] Skip turning on TV - config: tv was already on"
		elif self.checkifPowerupWithoutWakingTv() == 'True':
			print "[HdmiCec] Skip waking TV, found 'True' in '/tmp/powerup_without_waking_tv.txt' (usually written by openWebif)"
		else:
			if config.hdmicec.enabled.value:
				self.messages = []
				self.what = 'on'
				self.repeatCounter = 0
				powerswitch = False
				if config.hdmicec.control_tv_wakeup.value and not (self.what == self.tv_powerstate and config.hdmicec.check_tv_powerstate.value):
					powerswitch = True
					self.messages.append((0,"wakeup"))
				if config.hdmicec.report_active_source.value and not (self.tv_skip_setinput or self.activesource):
					self.messages.append((0,"sourceactive"))
				if config.hdmicec.report_active_menu.value:
					self.messages.append((0,"menuactive"))

				if powerswitch or not powerCheckOK:
					self.tv_powerstate = ''
					self.messages.append((0,"powerstate"))

				if config.hdmicec.control_receiver_wakeup.value:
					self.messages.append((5, "keypoweron"))
					self.messages.append((5, "setsystemaudiomode"))

				if self.messages:
					self.sendMessages(self.messages)

			if os.path.exists("/usr/script/TvOn.sh"):
				Console().ePopen("/usr/script/TvOn.sh &")

	def standbyMessages(self, powerCheck = True, powerCheckOK = False):
		self.handleTimerStop()
		if self.tv_skip_messages:
			self.tv_skip_messages = False
			self.tv_skip_setinput = False
			print "[HdmiCec] Skip turning off TV"
			return
		elif powerCheck:
			self.checkTVPowerState(True, self.standbyMessages)
			return

		if config.hdmicec.control_tv_standby.value and not config.hdmicec.tv_standby_notinstandby.value and 'on' in self.tv_powerstate_on_wakeup:
			print "[HdmiCec] Skip turning off TV - config: tv was not in standby"
		elif config.hdmicec.control_tv_standby.value and not config.hdmicec.tv_standby_notinputactive.value and not self.activesource and 'on' in self.tv_powerstate:
			print "[HdmiCec] Skip turning off TV - config: another input active"
		else: 
			if config.hdmicec.enabled.value:
				self.messages = []
				self.what = 'standby'
				self.repeatCounter = 0
				powerswitch = False
				if config.hdmicec.control_tv_standby.value and not (self.what == self.tv_powerstate and config.hdmicec.check_tv_powerstate.value):
					powerswitch = True
					self.messages.append((0,"standby"))
				else:
					if config.hdmicec.report_active_source.value and self.activesource:
						self.messages.append((0,"sourceinactive"))
					if config.hdmicec.report_active_menu.value:
						self.messages.append((0,"menuinactive"))

				if powerswitch or not powerCheckOK:
					self.tv_powerstate = ''
					self.messages.append((0,"powerstate"))

				if config.hdmicec.control_receiver_standby.value:
					self.messages.append((5, "keypoweroff"))
					self.messages.append((5, "standby"))

				if self.messages:
					self.sendMessages(self.messages)

			if os.path.exists("/usr/script/TvOff.sh"):
				Console().ePopen("/usr/script/TvOff.sh &")

	def onLeaveStandby(self):
		self.wakeupMessages()

	def onEnterStandby(self, configElement):
		Screens.Standby.inStandby.onClose.append(self.onLeaveStandby)
		self.standbyMessages()

	def onEnterDeepStandby(self, configElement):
		if config.hdmicec.handle_deepstandby_events.value:
			self.standbyMessages(False)

	def deepstandby(self):
		import NavigationInstance
		from time import time
		now = time()
		recording = NavigationInstance.instance.getRecordingsCheckBeforeActivateDeepStandby(config.hdmicec.handle_tv_standby_to_deepstandby.value)
		rectimer = abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - now) <= 900 or NavigationInstance.instance.RecordTimer.getStillRecording() or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - now) <= 900
		pwrtimer = abs(NavigationInstance.instance.PowerTimer.getNextPowerManagerTime() - now) <= 900 or NavigationInstance.instance.PowerTimer.isProcessing(exceptTimer = 0) or not NavigationInstance.instance.PowerTimer.isAutoDeepstandbyEnabled()

		print '[HdmiCec] deepstandby dependencies: config=%s, no recording=%s, no rectimer=%s, no pwrtimer=%s' %((not Screens.Standby.inStandby or config.hdmicec.handle_tv_standby_to_deepstandby.value), (not recording), (not rectimer), (not pwrtimer))

		if recording or rectimer or pwrtimer:
			self.standby()
		elif not Screens.Standby.inStandby or config.hdmicec.handle_tv_standby_to_deepstandby.value:
			from Screens.InfoBar import InfoBar
			if InfoBar and InfoBar.instance:
				print '[HdmiCec] go in deepstandby...'
				InfoBar.instance.openInfoBarSession(Screens.Standby.TryQuitMainloop, 1)

	def standby(self):
		if not Screens.Standby.inStandby:
			from Screens.InfoBar import InfoBar
			if InfoBar and InfoBar.instance:
				InfoBar.instance.openInfoBarSession(Screens.Standby.Standby)

	def wakeup(self):
		self.handleTimerStop()
		if Screens.Standby.inStandby:
			Screens.Standby.inStandby.Power()

	def messageReceived(self, message):
		if config.hdmicec.enabled.value:
			cmd = message.getCommand()
			data = 16 * '\x00'
			length = message.getData(data, len(data))
			if cmd == 0x00: # feature abort
				if data[0] == '\x44':
					print 'eHdmiCec: volume forwarding not supported by device %02x'%(message.getAddress())
					self.volumeForwardingEnabled = False
			elif cmd == 0x46: # request name
				self.sendMessage(message.getAddress(), 'osdname')
			elif cmd == 0x7e or cmd == 0x72: # system audio mode status
				if data[0] == '\x01':
					self.volumeForwardingDestination = 5 # on: send volume keys to receiver
				else:
					self.volumeForwardingDestination = 0 # off: send volume keys to tv
				if config.hdmicec.volume_forwarding.value:
					print 'eHdmiCec: volume forwarding to device %02x enabled'% self.volumeForwardingDestination
					self.volumeForwardingEnabled = True
			elif cmd == 0x8f: # request power status
				if Screens.Standby.inStandby:
					self.sendMessage(message.getAddress(), 'powerinactive')
				else:
					self.sendMessage(message.getAddress(), 'poweractive')
			elif cmd == 0x83: # request address
				self.sendMessage(message.getAddress(), 'reportaddress')
			elif cmd == 0x85: # request active source
				if not (self.skipreceived or Screens.Standby.inStandby):
					if config.hdmicec.report_active_source.value:
						self.sendMessage(message.getAddress(), 'sourceactive')
			elif cmd == 0x8c: # request vendor id
				self.sendMessage(message.getAddress(), 'vendorid')
			elif cmd == 0x8d: # menu request
				requesttype = ord(data[0])
				if requesttype == 2: # query
					if Screens.Standby.inStandby:
						self.sendMessage(message.getAddress(), 'menuinactive')
					else:
						self.sendMessage(message.getAddress(), 'menuactive')
			elif cmd == 0x90: # report power state
				if data[0] == '\x00':
					self.tv_powerstate = "on"
				elif data[0] == '\x01':
					self.tv_powerstate = "standby"
				elif data[0] == '\x02':
					self.tv_powerstate = "get_on"
				elif data[0] == '\x03':
					self.tv_powerstate = "get_standby"
			elif cmd == 0x36: # handle standby request from the tv
				self.checkTVPowerState(True)
				self.handleTVRequest(tvstandby = True)
			elif cmd == 0x80: # routing changed
				pass
			elif cmd == 0x86 or cmd == 0x82: # set streaming path, active source changed
				newaddress = ord(data[0]) * 256 + ord(data[1])
				ouraddress = eHdmiCEC.getInstance().getPhysicalAddress()
				if self.activesource != (newaddress == ouraddress):
					self.activesource = (newaddress == ouraddress)
					if not (self.skipreceived or Screens.Standby.inStandby) and self.activesource and config.hdmicec.report_active_source.value:
						self.sendMessage(message.getAddress(), 'sourceactive')
					txt = 'active source'
					if cmd == 0x86: txt = 'streaming path'
					print '[HdmiCec] %s has changed... to our address: %s' %(txt, self.activesource)
				self.handleTVRequest(self.activesource)

			# handle wakeup requests from the tv
			if not (self.skipreceived or config.hdmicec.handle_tv_wakeup.value == 'disabled'):
				if cmd == 0x04 and config.hdmicec.handle_tv_wakeup.value == "wakeup":
					self.wakeup()
				elif cmd == 0x80 and config.hdmicec.handle_tv_wakeup.value == "routingrequest":
					oldaddress = ord(data[0]) * 256 + ord(data[1])
					newaddress = ord(data[2]) * 256 + ord(data[3])
					ouraddress = eHdmiCEC.getInstance().getPhysicalAddress()
					print '[HdmiCec] routing has changed... from %s to %s (to our address: %s)' %(oldaddress, newaddress, (newaddress == ouraddress))
					if newaddress == ouraddress:
						self.wakeup()
				elif cmd == 0x84 and config.hdmicec.handle_tv_wakeup.value == "tvreportphysicaladdress":
					if (ord(data[0]) * 256 + ord(data[1])) == 0 and ord(data[2]) == 0:
						self.wakeup()
				elif cmd == 0x85 and config.hdmicec.handle_tv_wakeup.value == "sourcerequest":
					self.wakeup()
				elif cmd == 0x86 and config.hdmicec.handle_tv_wakeup.value == "streamrequest":
					if self.activesource:
						self.wakeup()
				elif cmd == 0x46 and config.hdmicec.handle_tv_wakeup.value == "osdnamerequest":
					self.wakeup()
				elif cmd != 0x36 and config.hdmicec.handle_tv_wakeup.value == "activity":
					self.wakeup()

			if not (self.wait.isActive() or self.repeatTimer.isActive() or self.stateTimer.isActive()):
				self.skipreceived = False

	def handleTimerStop(self):
		if self.handleTimer.isActive():
			self.handleTimer.stop()
			if len(self.handleTimer.callback):
				target = 'standby'
				if 'deep' in str(self.handleTimer.callback[0]):
					target = 'deep ' + target
				print '[HdmiCec] stopping Timer to %s' %target

	def handleTVRequest(self, reset = False, tvstandby = False):
		if not reset and self.tv_lastrequest == (reset,tvstandby) and self.handleTimer.isActive():
			return

		if reset or (not self.tv_lastrequest[1] and tvstandby):
			self.tv_skip_messages = False
			self.handleTimerStop()

		standby = deepstandby = False
		if not self.activesource or tvstandby:
			if tvstandby and config.hdmicec.handle_tv_standby.value == 'standby':
				self.tv_skip_messages = False
				standby = True
			elif tvstandby and config.hdmicec.handle_tv_standby.value == 'deepstandby':
				self.tv_skip_messages = False
				deepstandby = True
			elif not Screens.Standby.inStandby and not self.activesource and config.hdmicec.handle_tv_input.value == 'standby':
				self.tv_skip_messages = True
				standby = True
			elif not self.activesource and config.hdmicec.handle_tv_input.value == 'deepstandby':
				self.tv_skip_messages = True
				deepstandby = True

		if standby or deepstandby:
			self.tv_lastrequest = reset, tvstandby
			while len(self.handleTimer.callback):
				self.handleTimer.callback.pop()
		if standby:
			self.handleTimer.callback.append(self.standby)
			self.handleTimer.startLongTimer(int(config.hdmicec.handle_tv_delaytime.value))
			print '[HdmiCec] starting Timer to standby in %s s' %config.hdmicec.handle_tv_delaytime.value
		elif deepstandby:
			self.handleTimer.callback.append(self.deepstandby)
			self.handleTimer.startLongTimer(int(config.hdmicec.handle_tv_delaytime.value))
			print '[HdmiCec] starting Timer to deep standby in %s s' %config.hdmicec.handle_tv_delaytime.value

	def checkTVPowerState(self, reset = False, recall = None):
		if reset:
			self.recall = recall
			self.tv_powerstate = ''
			self.stateCounter = 0
			if self.stateTimer.isActive():
				self.stateTimer.stop()

		if not config.hdmicec.check_tv_powerstate.value:
			self.firststart = False
			self.activesource = False
			self.tv_powerstate_on_wakeup = 'standby'
			if self.recall:
				self.recall(False)
				self.recall = None
			return

		if self.stateCounter < 11:
			if self.tv_powerstate not in ('on','standby'):
				self.stateCounter += 1
				self.sendMessage(0, "powerstate")
				self.stateTimer.start(1000, True)
		else:
			self.tv_powerstate = 'unknown'
			print '[HdmiCec] TV power state failed !!!'

		if not self.stateTimer.isActive():
			self.stateCounter = 0
			if 'on' in self.tv_powerstate and (not Screens.Standby.inStandby or self.firststart):
				self.skipreceived = True
				self.sendMessage(0, 'routinginfo')
			elif 'standby' in self.tv_powerstate and not self.firststart:
				self.activesource = False
				self.tv_powerstate_on_wakeup = self.tv_powerstate
			if self.firststart:
				self.firststart = False
				self.tv_powerstate_on_wakeup = self.tv_powerstate
				print '[HdmiCec] TV power state at startup: %s' %self.tv_powerstate_on_wakeup
			if self.recall:
				self.recall(False, self.tv_powerstate != 'unknown')
				self.recall = None
			else:
				if self.tv_powerstate != 'unknown':
					print '[HdmiCec] TV power state: %s' %self.tv_powerstate

	def configVolumeForwarding(self, configElement):
		if config.hdmicec.enabled.value and config.hdmicec.volume_forwarding.value:
			self.volumeForwardingEnabled = True
			self.sendMessage(0x05, 'givesystemaudiostatus')
		else:
			self.volumeForwardingEnabled = False

	def keyEvent(self, keyCode, keyEvent):
		if not self.volumeForwardingEnabled: return
		cmd = 0
		data = ''
		if keyEvent == 0:
			if keyCode == 115:
				cmd = 0x44
				data = str(struct.pack('B', 0x41))
			if keyCode == 114:
				cmd = 0x44
				data = str(struct.pack('B', 0x42))
			if keyCode == 113:
				cmd = 0x44
				data = str(struct.pack('B', 0x43))
		if keyEvent == 2:
			if keyCode == 115:
				cmd = 0x44
				data = str(struct.pack('B', 0x41))
			if keyCode == 114:
				cmd = 0x44
				data = str(struct.pack('B', 0x42))
			if keyCode == 113:
				cmd = 0x44
				data = str(struct.pack('B', 0x43))
		if keyEvent == 1:
			if keyCode == 115 or keyCode == 114 or keyCode == 113:
				cmd = 0x45
		if cmd:
			eHdmiCEC.getInstance().sendMessage(self.volumeForwardingDestination, cmd, data, len(data))
			return 1
		else:
			return 0

	def sethdmipreemphasis(self):
		try:
			if fileExists("/proc/stb/hdmi/preemphasis"):
				if config.hdmicec.preemphasis.value == True:
					file = open("/proc/stb/hdmi/preemphasis", "w")
					file.write('on')
					file.close()
				else:
					file = open("/proc/stb/hdmi/preemphasis", "w")
					file.write('off')
					file.close()
		except:
			return

	def checkifPowerupWithoutWakingTv(self):
		try:
			#returns 'True' if openWebif function "Power on without TV" has written 'True' to this file:
			f = open("/tmp/powerup_without_waking_tv.txt", "r")
			powerupWithoutWakingTv = f.read()
			f.close()
		except:
			powerupWithoutWakingTv = 'False'

		try:
			#write 'False' to the file so that turning on the TV is only suppressed once
			#(and initially, so that openWebif knows that the image supports this feature)
			f = open("/tmp/powerup_without_waking_tv.txt", "w")
			f.write('False')
			f.close()
		except:
			print "[HdmiCec] failed writing /tmp/powerup_without_waking_tv.txt"

		return powerupWithoutWakingTv

hdmi_cec = HdmiCec()
