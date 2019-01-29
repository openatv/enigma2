import struct
import os
from fcntl import ioctl
from enigma import eTimer, eHdmiCEC, eActionMap
from config import config, ConfigSelection, ConfigYesNo, ConfigSubsection, ConfigText, NoSave
from Components.Console import Console
from Tools.Directories import fileExists
from time import time
import Screens.Standby

from sys import maxint


config.hdmicec = ConfigSubsection()
config.hdmicec.enabled = ConfigYesNo(default = False) # query from this value in hdmi_cec.cpp
config.hdmicec.control_tv_standby = ConfigYesNo(default = True)
config.hdmicec.control_tv_wakeup = ConfigYesNo(default = True)
config.hdmicec.report_active_source = ConfigYesNo(default = True)
config.hdmicec.report_active_menu = ConfigYesNo(default = True) # query from this value in hdmi_cec.cpp
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
config.hdmicec.handle_deepstandby_events = ConfigYesNo(default = True)
config.hdmicec.preemphasis = ConfigYesNo(default = False)
choicelist = []
for i in (10, 50, 100, 150, 250, 500, 750, 1000):
	choicelist.append(("%d" % i, "%d ms" % i))
config.hdmicec.minimum_send_interval = ConfigSelection(default = "250", choices = [("0", _("Disabled"))] + choicelist)
choicelist = []
for i in range(1,6):
	choicelist.append(("%d" % i, _("%d times") % i))
config.hdmicec.messages_repeat = ConfigSelection(default = "0", choices = [("0", _("Disabled"))] + choicelist)
config.hdmicec.messages_repeat_standby = ConfigYesNo(default = False)
choicelist = []
for i in (500, 1000, 2000, 3000, 4000, 5000):
	choicelist.append(("%d" % i, "%d ms" % i))
config.hdmicec.messages_repeat_slowdown = ConfigSelection(default = "1000", choices = [("0", _("None"))] + choicelist)
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
config.hdmicec.workaround_activesource = ConfigYesNo(default = False)
choicelist = []
for i in (5,10,15,30,45,60):
	choicelist.append(("%d" % i, _("%d sec") % i))
config.hdmicec.workaround_turnbackon = ConfigSelection(default = "0", choices = [("0", _("Disabled"))] + choicelist)
config.hdmicec.advanced_settings = NoSave(ConfigYesNo(default = False))
config.hdmicec.default_settings = NoSave(ConfigYesNo(default = False))

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
			self.stateTimer = eTimer()
			self.stateTimer.callback.append(self.stateTimeout)
			self.repeatTimer = eTimer()
			self.repeatTimer.callback.append(self.repeatMessages)
			self.repeatCounter = 0
			self.what = ''
			self.tv_lastrequest = ''
			self.tv_powerstate = 'unknown'
			self.tv_skip_messages = False
			self.activesource = False
			self.firstrun = True
			self.standbytime = 0

			self.sethdmipreemphasis()
			self.checkifPowerupWithoutWakingTv() # initially write 'False' to file, see below

			eHdmiCEC.getInstance().messageReceived.get().append(self.messageReceived)
			config.misc.standbyCounter.addNotifier(self.onEnterStandby, initial_call = False)
			config.misc.DeepStandby.addNotifier(self.onEnterDeepStandby, initial_call = False)
			self.setFixedPhysicalAddress(config.hdmicec.fixed_physical_address.value)

			self.volumeForwardingEnabled = False
			self.volumeForwardingDestination = 0
			eActionMap.getInstance().bindAction('', -maxint - 1, self.keyEvent)
			config.hdmicec.volume_forwarding.addNotifier(self.configVolumeForwarding, initial_call = False)
			config.hdmicec.enabled.addNotifier(self.configVolumeForwarding)

			#workaround for needless messages after cancel settings
			self.old_configReportActiveMenu = config.hdmicec.report_active_menu.value
			self.old_configTVstate = config.hdmicec.check_tv_state.value or (config.hdmicec.tv_standby_notinputactive.value and config.hdmicec.control_tv_standby.value)
			#
			config.hdmicec.report_active_menu.addNotifier(self.configReportActiveMenu, initial_call = False)
			config.hdmicec.check_tv_state.addNotifier(self.configTVstate, initial_call = False)
			config.hdmicec.tv_standby_notinputactive.addNotifier(self.configTVstate, initial_call = False)
			config.hdmicec.control_tv_standby.addNotifier(self.configTVstate, initial_call = False)

			self.checkTVstate('firstrun')

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
			checkstate = self.stateTimer.isActive()
			data = 16 * '\x00'
			cmd = message.getCommand()
			length = message.getData(data, len(data))
			address = message.getAddress()

			#// workaround for wrong address vom driver (e.g. hd51, message comes from tv -> address is only sometimes 0, dm920, same tv -> address is always 0)
			if address > 15:
				address = 0
				print "[HdmiCec] workaround for wrong received address data enabled"
			#//

			if cmd == 0x00: # feature abort
				if data[0] == '\x44':
					print 'eHdmiCec: volume forwarding not supported by device %02x'%(address)
					self.volumeForwardingEnabled = False
			elif cmd == 0x46: # request name
				self.sendMessage(address, 'osdname')
			elif cmd in (0x7e, 0x72): # system audio mode status
				if data[0] == '\x01':
					self.volumeForwardingDestination = 5 # on: send volume keys to receiver
				else:
					self.volumeForwardingDestination = 0 # off: send volume keys to tv
				if config.hdmicec.volume_forwarding.value:
					print 'eHdmiCec: volume forwarding to device %02x enabled'% self.volumeForwardingDestination
					self.volumeForwardingEnabled = True
			elif cmd == 0x8f: # request power status
				if Screens.Standby.inStandby:
					self.sendMessage(address, 'powerinactive')
				else:
					self.sendMessage(address, 'poweractive')
			elif cmd == 0x83: # request address
				self.sendMessage(address, 'reportaddress')
			elif cmd == 0x85: # request active source
				if not Screens.Standby.inStandby and config.hdmicec.report_active_source.value:
					self.sendMessage(address, 'sourceactive')
			elif cmd == 0x8c: # request vendor id
				self.sendMessage(address, 'vendorid')
			elif cmd == 0x8d: # menu request
				requesttype = ord(data[0])
				if requesttype == 2: # query
					if Screens.Standby.inStandby:
						self.sendMessage(address, 'menuinactive')
					else:
						self.sendMessage(address, 'menuactive')
			elif address == 0 and cmd == 0x90: # report power state from the tv
				if data[0] == '\x00':
					self.tv_powerstate = "on"
				elif data[0] == '\x01':
					self.tv_powerstate = "standby"
				elif data[0] == '\x02':
					self.tv_powerstate = "get_on"
				elif data[0] == '\x03':
					self.tv_powerstate = "get_standby"
				if checkstate and not self.firstrun:
					self.checkTVstate('powerstate')
				elif self.firstrun and not config.hdmicec.handle_deepstandby_events.value:
					self.firstrun = False
				else:
					self.checkTVstate()
			elif address == 0 and cmd == 0x36: # handle standby request from the tv
				if config.hdmicec.handle_tv_standby.value != 'disabled':
					self.handleTVRequest('tvstandby')
				self.checkTVstate('tvstandby')
			elif cmd == 0x80: # routing changed
				oldaddress = ord(data[0]) * 256 + ord(data[1])
				newaddress = ord(data[2]) * 256 + ord(data[3])
				ouraddress = eHdmiCEC.getInstance().getPhysicalAddress()
				active = (newaddress == ouraddress)
				hexstring = '%04x' % oldaddress
				oldaddress = hexstring[0] + '.' + hexstring[1] + '.' + hexstring[2] + '.' + hexstring[3]
				hexstring = '%04x' % newaddress
				newaddress = hexstring[0] + '.' + hexstring[1] + '.' + hexstring[2] + '.' + hexstring[3]
				print "[HdmiCec] routing has changed... from '%s' to '%s' (to our address: %s)" %(oldaddress, newaddress, active)
			elif cmd in (0x86, 0x82): # set streaming path, active source changed
				newaddress = ord(data[0]) * 256 + ord(data[1])
				ouraddress = eHdmiCEC.getInstance().getPhysicalAddress()
				active = (newaddress == ouraddress)
				if checkstate or self.activesource != active:
					if checkstate:
						txt = 'our receiver is active source'
					else:
						txt = 'active source'
						if cmd == 0x86: txt = 'streaming path'
						txt += ' has changed... to our address'
					print '[HdmiCec] %s: %s' %(txt, active)
				self.activesource = active
				if not checkstate:
					if cmd == 0x86 and not Screens.Standby.inStandby and self.activesource:
						self.sendMessage(address, 'sourceactive')
						if config.hdmicec.report_active_menu.value:
							self.sendMessage(0, 'menuactive')
					if config.hdmicec.handle_tv_input.value != 'disabled':
						self.handleTVRequest('activesource')
					self.checkTVstate('changesource')
				else:
					self.checkTVstate('activesource')

			# handle wakeup requests from the tv
			wakeup = False
			if address == 0 and cmd == 0x44 and data[0] in ('\x40', '\x6D'): # handle wakeup from tv hdmi-cec menu (e.g. panasonic tv apps, viera link)
				wakeup = True
			elif not checkstate and config.hdmicec.handle_tv_wakeup.value != 'disabled':
				if address == 0:
					if ((cmd == 0x04 and config.hdmicec.handle_tv_wakeup.value == "wakeup") or 
						(cmd == 0x85 and config.hdmicec.handle_tv_wakeup.value == "sourcerequest") or
						(cmd == 0x46 and config.hdmicec.handle_tv_wakeup.value == "osdnamerequest") or 
						(cmd != 0x36 and config.hdmicec.handle_tv_wakeup.value == "activity")):
						wakeup = True
					elif cmd == 0x84 and config.hdmicec.handle_tv_wakeup.value == "tvreportphysicaladdress":
						if (ord(data[0]) * 256 + ord(data[1])) == 0 and ord(data[2]) == 0:
							wakeup = True
				if (cmd == 0x80 and config.hdmicec.handle_tv_wakeup.value == "routingrequest") or (cmd == 0x86 and config.hdmicec.handle_tv_wakeup.value == "streamrequest"):
					if active:
						wakeup = True
			if wakeup:
				self.wakeup()

	def sendMessage(self, address, message):
		if config.hdmicec.enabled.value:
			cmd = 0
			data = ''
			if message == "wakeup":
				cmd = 0x04
			elif message == "sourceactive":
				address = 0x0f # use broadcast address
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
			elif message == "setsystemaudiomode":
				cmd = 0x70
				physicaladdress = eHdmiCEC.getInstance().getPhysicalAddress()
				data = str(struct.pack('BB', int(physicaladdress/256), int(physicaladdress%256)))
			elif message == "activatesystemaudiomode":
				cmd = 0x72
				data = str(struct.pack('B', 0x01))
			elif message == "deactivatesystemaudiomode":
				cmd = 0x72
				data = str(struct.pack('B', 0x00))
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
				if config.misc.DeepStandby.value: # no delay for messages before go in to deep-standby
					eHdmiCEC.getInstance().sendMessage(address, cmd, data, len(data))
				else:
					self.queue.append((address, cmd, data))
					if not self.wait.isActive():
						self.wait.start(int(config.hdmicec.minimum_send_interval.value), True)

	def sendCmd(self):
		if len(self.queue):
			(address, cmd, data) = self.queue.pop(0)
			eHdmiCEC.getInstance().sendMessage(address, cmd, data, len(data))
			self.wait.start(int(config.hdmicec.minimum_send_interval.value), True)

	def sendMessages(self, messages):
		self.firstrun = False
		self.queue = []
		self.sendMessagesIsActive(True)
		sendCnt = 0
		for send in messages:
			address = send[0]
			message = send[1]
			if self.what == 'on' and ((self.repeatCounter > 0 or self.activesource) and (message == 'standby' or (message == 'wakeup' and not config.hdmicec.control_tv_wakeup.value))): # skip active source workaround messages
				continue
			self.sendMessage(address, message)
			sendCnt += 1
		if sendCnt:
			self.repeatTimer.start((int(config.hdmicec.minimum_send_interval.value)*(len(messages)+1)+self.sendSlower()), True)

	def repeatMessages(self):
		if len(self.queue):
			self.repeatTimer.start(1000, True)
		elif self.firstrun:
			if self.stateTimer.isActive():
				self.repeatTimer.start(1000, True)
			else:
				self.sendMessages(self.messages)
		elif self.repeatCounter < int(config.hdmicec.messages_repeat.value) and (self.what == 'on' or (config.hdmicec.messages_repeat_standby.value and self.what == 'standby')):
			self.repeatCounter += 1
			self.sendMessages(self.messages)
		else:
			self.repeatCounter = 0
			self.checkTVstate(self.what)

	def sendSlower(self):
		if int(config.hdmicec.messages_repeat.value) and self.repeatCounter != int(config.hdmicec.messages_repeat.value):
			return int(config.hdmicec.messages_repeat_slowdown.value) * (self.repeatCounter or 1)
		return 0

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
				if config.hdmicec.workaround_activesource.value and config.hdmicec.report_active_source.value and not self.activesource and not 'standby' in self.tv_powerstate:
					#// some tv devices switched not to correct hdmi port if a another hdmi port active - the workaround switch the tv off and on
					self.messages.append((0, "standby"))
					if not config.hdmicec.control_tv_wakeup.value:
						self.messages.append((0, "wakeup"))
					#//
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

				if self.firstrun: # wait for tv state and another messages on first start
					self.repeatTimer.start(1000, True)
				else:
					self.sendMessages(self.messages)

			if os.path.exists("/usr/script/TvOn.sh"):
				Console().ePopen("/usr/script/TvOn.sh &")

	def standbyMessages(self):
		self.handleTimerStop()
		if self.tv_skip_messages:
			self.tv_skip_messages = False
			print "[HdmiCec] Skip turning off TV"
		elif config.hdmicec.control_tv_standby.value and not config.hdmicec.tv_standby_notinputactive.value and not self.sendMessagesIsActive() and not self.activesource and 'on' in self.tv_powerstate:
			print "[HdmiCec] Skip turning off TV - config: tv has another input active"
		else: 
			if config.hdmicec.enabled.value:
				self.messages = []
				self.what = 'standby'
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
					#self.messages.append((5, "standby"))

				self.sendMessages(self.messages)

			if os.path.exists("/usr/script/TvOff.sh"):
				Console().ePopen("/usr/script/TvOff.sh &")

	def sendMessagesIsActive(self, stopMessages = False):
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
		print '[HdmiCec] timeout for check TV state!'
		if 'on' in self.tv_powerstate:
			self.checkTVstate('activesource')
		elif self.tv_powerstate == 'unknown': # no response from tv - another input active ? -> check if powered on
			self.checkTVstate('getpowerstate')
		elif self.firstrun and not config.hdmicec.handle_deepstandby_events.value:
			self.firstrun = False

	def checkTVstate(self, state = ''):
		if self.stateTimer.isActive():
			self.stateTimer.stop()

		timeout = 3000
		need_routinginfo = config.hdmicec.control_tv_standby.value and not config.hdmicec.tv_standby_notinputactive.value
		if 'source' in state:
			self.tv_powerstate = 'on'
			if state == 'activesource' and self.what == 'on' and config.hdmicec.report_active_source.value and not self.activesource and not self.firstrun: # last try for switch to correct input
				self.sendMessage(0, 'sourceactive')
				if need_routinginfo or config.hdmicec.check_tv_state.value:
					self.sendMessage(0, 'routinginfo')
			if self.firstrun and not config.hdmicec.handle_deepstandby_events.value:
				self.firstrun = False
		elif state == 'tvstandby':
			self.activesource = False
			self.tv_powerstate = 'standby'
		elif state == 'firstrun' and ((not config.hdmicec.handle_deepstandby_events.value and (need_routinginfo or config.hdmicec.report_active_menu.value)) or config.hdmicec.check_tv_state.value or config.hdmicec.workaround_activesource.value):
			self.stateTimer.start(timeout,True)
			self.sendMessage(0, 'routinginfo')
		elif state == 'firstrun' and not config.hdmicec.handle_deepstandby_events.value:
			self.firstrun = False
		elif config.hdmicec.check_tv_state.value or 'powerstate' in state:
			if state == 'getpowerstate' or state in ('on', 'standby'):
				self.activesource = False
				if state in ('on', 'standby'):
					self.tv_powerstate = 'unknown'
				else:
					self.tv_powerstate = 'getpowerstate'
				self.stateTimer.start(timeout,True)
				self.sendMessage(0, 'powerstate')
			elif state == 'powerstate' and 'on' in self.tv_powerstate:
				self.stateTimer.start(timeout,True)
				self.sendMessage(0, 'routinginfo')
		else:
			if state == 'on' and need_routinginfo:
				self.activesource = False
				self.tv_powerstate = 'unknown'
				self.stateTimer.start(timeout,True)
				self.sendMessage(0, 'routinginfo')
			elif state == 'standby' and config.hdmicec.control_tv_standby.value:
				self.activesource = False
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
		elif ((request == self.tv_lastrequest or self.tv_lastrequest == 'tvstandby') and self.handleTimer.isActive()) or (request == 'activesource' and not self.activesource and self.sendMessagesIsActive()):
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
			elif standby or deepstandby:
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
				print '[HdmiCec] go into standby...'
				InfoBar.instance.openInfoBarSession(Screens.Standby.Standby)

	def wakeup(self):
		if int(config.hdmicec.workaround_turnbackon.value) and self.standbytime > time():
			print '[HdmiCec] ignore wakeup for %d seconds ...' %int(self.standbytime - time())
			return
		self.standbytime = 0
		self.handleTimerStop(True)
		if Screens.Standby.inStandby:
			print '[HdmiCec] wake up...'
			Screens.Standby.inStandby.Power()

	def onLeaveStandby(self):
		self.wakeupMessages()

	def onEnterStandby(self, configElement):
		self.standbytime = time() + int(config.hdmicec.workaround_turnbackon.value)
		Screens.Standby.inStandby.onClose.append(self.onLeaveStandby)
		self.standbyMessages()

	def onEnterDeepStandby(self, configElement):
		if config.hdmicec.handle_deepstandby_events.value:
			self.standbyMessages()

	def configVolumeForwarding(self, configElement):
		if config.hdmicec.enabled.value and config.hdmicec.volume_forwarding.value:
			self.volumeForwardingEnabled = True
			self.sendMessage(5, 'givesystemaudiostatus')
		else:
			self.volumeForwardingEnabled = False

	def configReportActiveMenu(self, configElement):
		if self.old_configReportActiveMenu == config.hdmicec.report_active_menu.value: return
		self.old_configReportActiveMenu = config.hdmicec.report_active_menu.value
		if config.hdmicec.report_active_menu.value:
			self.sendMessage(0, 'sourceactive')
			self.sendMessage(0, 'menuactive')
		else:
			self.sendMessage(0, 'menuinactive')

	def configTVstate(self, configElement):
		if self.old_configTVstate == (config.hdmicec.check_tv_state.value or config.hdmicec.check_tv_state.value or (config.hdmicec.tv_standby_notinputactive.value and config.hdmicec.control_tv_standby.value)): return
		self.old_configTVstate = config.hdmicec.check_tv_state.value or config.hdmicec.check_tv_state.value or (config.hdmicec.tv_standby_notinputactive.value and config.hdmicec.control_tv_standby.value)
		if not self.sendMessagesIsActive() and self.old_configTVstate:
			self.sendMessage(0, 'powerstate')
			self.sendMessage(0, 'routinginfo')

	def keyEvent(self, keyCode, keyEvent):
		if not self.volumeForwardingEnabled: return
		cmd = 0
		data = ''
		if keyEvent in (0, 2):
			if keyCode == 115:
				cmd = 0x44
				data = str(struct.pack('B', 0x41))
			elif keyCode == 114:
				cmd = 0x44
				data = str(struct.pack('B', 0x42))
			elif keyCode == 113:
				cmd = 0x44
				data = str(struct.pack('B', 0x43))
		elif keyEvent == 1 and keyCode in (113, 114, 115):
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
