import struct
import os
from fcntl import ioctl
from sys import maxint
from enigma import eTimer, eHdmiCEC, eActionMap
from config import config, ConfigSelection, ConfigYesNo, ConfigSubsection, ConfigText
from Components.Console import Console
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
config.hdmicec.handle_tv_input = ConfigSelection(default = "disabled", choices = choicelist)
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
for i in (10, 50, 100, 150, 250, 500, 750, 1000, 1500, 2000, 3000):
	choicelist.append(("%d" % i, "%d ms" % i))
config.hdmicec.minimum_send_interval = ConfigSelection(default = "0", choices = [("0", _("Disabled"))] + choicelist)
choicelist = []
for i in range(1,4):
	choicelist.append(("%d" % i, _("%d times") % i))
config.hdmicec.messages_repeat = ConfigSelection(default = "0", choices = [("0", _("Disabled"))] + choicelist)
choicelist = []
for i in (10,30,60,120,300,600,900,1800,3600):
	if i/60<1:
		choicelist.append(("%d" % i, _("%d sec") % i))
	else:
		choicelist.append(("%d" % i, _("%d min") % (i/60)))
config.hdmicec.handle_tv_delaytime = ConfigSelection(default = "0", choices = [("0", _("None"))] + choicelist)
config.hdmicec.deepstandby_waitfortimesync = ConfigYesNo(default = True)
config.hdmicec.tv_wakeup_zaptimer = ConfigYesNo(default = True)
config.hdmicec.tv_wakeup_zapandrecordtimer = ConfigYesNo(default = True)
config.hdmicec.tv_wakeup_wakeuppowertimer = ConfigYesNo(default = True)
config.hdmicec.tv_standby_notinputactive = ConfigYesNo(default = True)
config.hdmicec.check_tv_state = ConfigYesNo(default = False)

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

			self.handleTimer = eTimer()
			self.repeatTimer = eTimer()
			self.repeatTimer.callback.append(self.repeatMessages)
			self.repeatCounter = 0
			self.what = ''
			self.tv_lastrequest = ''
			self.tv_powerstate = ''
			self.tv_skip_messages = False
			self.activesource = False

			eHdmiCEC.getInstance().messageReceived.get().append(self.messageReceived)
			config.misc.standbyCounter.addNotifier(self.onEnterStandby, initial_call = False)
			config.misc.DeepStandby.addNotifier(self.onEnterDeepStandby, initial_call = False)
			self.setFixedPhysicalAddress(config.hdmicec.fixed_physical_address.value)

			self.volumeForwardingEnabled = False
			self.volumeForwardingDestination = 0
			eActionMap.getInstance().bindAction('', -maxint - 1, self.keyEvent)
			config.hdmicec.volume_forwarding.addNotifier(self.configVolumeForwarding)
			config.hdmicec.enabled.addNotifier(self.configVolumeForwarding)

			self.sethdmipreemphasis()
			self.checkTVstate('standby')
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
				if not Screens.Standby.inStandby and config.hdmicec.report_active_source.value:
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
				self.checkTVstate('powerstate')
			elif cmd == 0x36: # handle standby request from the tv
				if config.hdmicec.handle_tv_standby.value != 'disabled':
					self.handleTVRequest('tvstandby')
				self.checkTVstate('tvstandby')
			elif cmd == 0x80: # routing changed
				pass
			elif cmd == 0x86 or cmd == 0x82: # set streaming path, active source changed
				newaddress = ord(data[0]) * 256 + ord(data[1])
				ouraddress = eHdmiCEC.getInstance().getPhysicalAddress()
				if self.activesource != (newaddress == ouraddress):
					txt = 'active source'
					if cmd == 0x86: txt = 'streaming path'
					print '[HdmiCec] %s has changed... to our address: %s' %(txt, (newaddress == ouraddress))
				self.activesource = (newaddress == ouraddress)
				if not Screens.Standby.inStandby and self.activesource and config.hdmicec.report_active_source.value:
					self.sendMessage(message.getAddress(), 'sourceactive')
				if config.hdmicec.handle_tv_input.value != 'disabled':
					self.handleTVRequest('activesource')
				self.checkTVstate('activesource')

			# handle wakeup requests from the tv
			if config.hdmicec.handle_tv_wakeup.value != 'disabled':
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
				sendSlower = self.sendSlower()
				if int(config.hdmicec.minimum_send_interval.value) + sendSlower != 0 and message != "standby": # Use no interval time when message is standby. usefull for Panasonic TV
					self.queue.append((address, cmd, data))
					if not self.wait.isActive():
						self.wait.start(int(config.hdmicec.minimum_send_interval.value) + sendSlower, True)
				else:
					eHdmiCEC.getInstance().sendMessage(address, cmd, data, len(data))

	def sendCmd(self):
		if len(self.queue):
			(address, cmd, data) = self.queue.pop(0)
			eHdmiCEC.getInstance().sendMessage(address, cmd, data, len(data))
			self.wait.start(int(config.hdmicec.minimum_send_interval.value) + self.sendSlower(), True)

	def sendMessages(self, messages):
		self.queue = []
		if self.wait.isActive():
			self.wait.stop()
		if self.repeatTimer.isActive():
			self.repeatTimer.stop()
		for send in messages:
			address = send[0]
			message = send[1]
			self.sendMessage(address, message)
		self.repeatTimer.start((int(config.hdmicec.minimum_send_interval.value)+self.sendSlower())*len(messages)+1000, True)

	def repeatMessages(self):
		if len(self.queue):
			self.repeatTimer.start(1000, True)
		elif self.repeatCounter < int(config.hdmicec.messages_repeat.value):
			self.repeatCounter += 1
			self.sendMessages(self.messages)
		else:
			self.repeatCounter = 0
			self.checkTVstate(self.what)

	def sendSlower(self):
		return 100 * self.repeatCounter

	def wakeupMessages(self):
		self.handleTimerStop()
		if self.tv_skip_messages:
			self.tv_skip_messages = False
			print "[HdmiCec] Skip turning on TV"
		elif self.checkifPowerupWithoutWakingTv() == 'True':
			print "[HdmiCec] Skip waking TV, found 'True' in '/tmp/powerup_without_waking_tv.txt' (usually written by openWebif)"
		else:
			if config.hdmicec.enabled.value:
				self.messages = []
				self.what = 'on'
				self.repeatCounter = 0
				if config.hdmicec.control_tv_wakeup.value:
					self.messages.append((0,"wakeup"))
				if config.hdmicec.report_active_source.value:
					self.messages.append((0,"sourceactive"))
				if config.hdmicec.report_active_menu.value:
					self.messages.append((0,"menuactive"))

				if config.hdmicec.control_receiver_wakeup.value:
					self.messages.append((5, "keypoweron"))
					self.messages.append((5, "setsystemaudiomode"))

				if self.messages:
					self.sendMessages(self.messages)

			if os.path.exists("/usr/script/TvOn.sh"):
				Console().ePopen("/usr/script/TvOn.sh &")

	def standbyMessages(self):
		self.handleTimerStop()
		if self.tv_skip_messages:
			self.tv_skip_messages = False
			print "[HdmiCec] Skip turning off TV"
		elif config.hdmicec.control_tv_standby.value and not config.hdmicec.tv_standby_notinputactive.value and not self.activesource and 'on' in self.tv_powerstate:
			print "[HdmiCec] Skip turning off TV - config: tv has another input active"
		else: 
			if config.hdmicec.enabled.value:
				self.messages = []
				self.what = 'standby'
				self.repeatCounter = 0
				if config.hdmicec.control_tv_standby.value:
					self.messages.append((0,"standby"))
				else:
					if config.hdmicec.report_active_source.value:
						self.messages.append((0,"sourceinactive"))
					if config.hdmicec.report_active_menu.value:
						self.messages.append((0,"menuinactive"))

				if config.hdmicec.control_receiver_standby.value:
					self.messages.append((5, "keypoweroff"))
					self.messages.append((5, "standby"))

				if self.messages:
					self.sendMessages(self.messages)

			if os.path.exists("/usr/script/TvOff.sh"):
				Console().ePopen("/usr/script/TvOff.sh &")

	def checkTVstate(self, state = ''):
		if config.hdmicec.check_tv_state.value:
			if state in ('on', 'standby'):
				self.sendMessage(0, 'powerstate')
			elif state == 'powerstate' and 'on' in self.tv_powerstate:
				self.activesource = False
				self.sendMessage(0, 'routinginfo')
			elif state == 'tvstandby':
				self.tv_powerstate = 'standby'
		else:
			if state == 'on' and config.hdmicec.control_tv_wakeup.value:
				self.activesource = False
				self.tv_powerstate = 'standby'
				self.sendMessage(0, 'routinginfo')
			elif state == 'activesource':
				self.tv_powerstate = 'on'
			elif state == 'tvstandby' or (state == 'standby' and config.hdmicec.control_tv_standby.value):
				self.tv_powerstate = 'standby'

	def handleTimerStop(self, reset = False):
		if reset:
			self.tv_skip_messages = False
		if self.handleTimer.isActive():
			self.handleTimer.stop()
			if len(self.handleTimer.callback):
				target = 'standby'
				if 'deep' in str(self.handleTimer.callback[0]):
					target = 'deep ' + target
				print '[HdmiCec] stopping Timer to %s' %target

	def handleTVRequest(self, request):
		if (request == 'activesource' and self.activesource) or (self.tv_lastrequest == 'tvstandby' and request == 'activesource' and self.handleTimer.isActive()):
			self.handleTimerStop(True)
		elif (request == self.tv_lastrequest or self.tv_lastrequest == 'tvstandby') and self.handleTimer.isActive():
			return
		else:
			self.handleTimerStop(True)
			self.tv_lastrequest = request

			standby = deepstandby = False
			if config.hdmicec.handle_tv_standby.value != 'disabled' and request == 'tvstandby':
				self.tv_skip_messages = False
				if config.hdmicec.handle_tv_standby.value == 'standby':
					standby = True
				elif config.hdmicec.handle_tv_standby.value == 'deepstandby':
					deepstandby = True
			elif config.hdmicec.handle_tv_input.value != 'disabled' and request == 'activesource':
				self.tv_skip_messages = True
				if config.hdmicec.handle_tv_input.value == 'standby':
					standby = True
				elif config.hdmicec.handle_tv_input.value == 'deepstandby':
					deepstandby = True

			if standby and Screens.Standby.inStandby:
				self.tv_skip_messages = False
				return

			if standby or deepstandby:
				while len(self.handleTimer.callback):
					self.handleTimer.callback.pop()
			if standby:
				if int(config.hdmicec.handle_tv_delaytime.value):
					self.handleTimer.callback.append(self.standby)
					self.handleTimer.startLongTimer(int(config.hdmicec.handle_tv_delaytime.value))
					print '[HdmiCec] starting Timer to standby in %s s' %config.hdmicec.handle_tv_delaytime.value
				else:
					self.standby()
			elif deepstandby:
				if int(config.hdmicec.handle_tv_delaytime.value):
					self.handleTimer.callback.append(self.deepstandby)
					self.handleTimer.startLongTimer(int(config.hdmicec.handle_tv_delaytime.value))
					print '[HdmiCec] starting Timer to deep standby in %s s' %config.hdmicec.handle_tv_delaytime.value
				else:
					self.deepstandby()

	def deepstandby(self):
		import NavigationInstance
		from time import time
		now = time()
		recording = NavigationInstance.instance.getRecordingsCheckBeforeActivateDeepStandby()
		rectimer = abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - now) <= 900 or NavigationInstance.instance.RecordTimer.getStillRecording() or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - now) <= 900
		pwrtimer = abs(NavigationInstance.instance.PowerTimer.getNextPowerManagerTime() - now) <= 900 or NavigationInstance.instance.PowerTimer.isProcessing(exceptTimer = 0) or not NavigationInstance.instance.PowerTimer.isAutoDeepstandbyEnabled()
		if recording or rectimer or pwrtimer:
			print '[HdmiCec] go not into deepstandby... recording=%s, rectimer=%s, pwrtimer=%s' %(recording, rectimer, pwrtimer)
			self.standby()
		else:
			from Screens.InfoBar import InfoBar
			if InfoBar and InfoBar.instance:
				print '[HdmiCec] go into deepstandby...'
				InfoBar.instance.openInfoBarSession(Screens.Standby.TryQuitMainloop, 1)

	def standby(self):
		if not Screens.Standby.inStandby:
			import NavigationInstance
			NavigationInstance.instance.skipWakeup = True
			from Screens.InfoBar import InfoBar
			if InfoBar and InfoBar.instance:
				InfoBar.instance.openInfoBarSession(Screens.Standby.Standby)

	def wakeup(self):
		self.handleTimerStop(True)
		if Screens.Standby.inStandby:
			Screens.Standby.inStandby.Power()

	def onLeaveStandby(self):
		self.wakeupMessages()

	def onEnterStandby(self, configElement):
		Screens.Standby.inStandby.onClose.append(self.onLeaveStandby)
		self.standbyMessages()

	def onEnterDeepStandby(self, configElement):
		if config.hdmicec.handle_deepstandby_events.value:
			self.standbyMessages()

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
		if fileExists("/proc/stb/hdmi/preemphasis"):
			try:
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
