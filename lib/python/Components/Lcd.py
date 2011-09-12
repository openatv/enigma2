from config import config, ConfigSubsection, ConfigSelection, ConfigSlider, ConfigYesNo, ConfigNothing
from enigma import eDBoxLCD, eTimer
from Components.SystemInfo import SystemInfo
from os import path

def NetworkLinkCheck(session=None, **kwargs):
	if path.exists("/proc/stb/lcd/symbol_network"):
		global networklinkpoller
		networklinkpoller = NetworkLinkCheckPoller()
		networklinkpoller.start()

class NetworkLinkCheckPoller:
	def __init__(self):
		self.timer = eTimer()

	def start(self):
		if self.networklink_check not in self.timer.callback:
			self.timer.callback.append(self.networklink_check)
		self.timer.startLongTimer(0)

	def stop(self):
		if self.version_check in self.timer.callback:
			self.timer.callback.remove(self.networklinkcheck)
		self.timer.stop()

	def networklink_check(self):
		if path.exists('/sys/class/net/wlan0/carrier'):
			LinkState = open('/sys/class/net/wlan0/carrier').read()
		elif path.exists('/sys/class/net/eth0/carrier'):
			LinkState = open('/sys/class/net/eth0/carrier').read()
		LinkState = LinkState[:1]
		file = open("/proc/stb/lcd/symbol_network", "w")
		file.write('%d' % int(LinkState))
		file.close()
		self.timer.startLongTimer(30)

class LCD:
	def __init__(self):
		pass

	def setBright(self, value):
		value *= 255
		value /= 10
		if value > 255:
			value = 255
		eDBoxLCD.getInstance().setLCDBrightness(value)

	def setContrast(self, value):
		value *= 63
		value /= 20
		if value > 63:
			value = 63
		eDBoxLCD.getInstance().setLCDContrast(value)

	def setInverted(self, value):
		if value:
			value = 255
		eDBoxLCD.getInstance().setInverted(value)

	def isOled(self):
		return eDBoxLCD.getInstance().isOled()

	def setMode(self, value):
		file = open("/proc/stb/lcd/show_symbols", "w")
		file.write('%d' % int(value))
		file.close()
		print "[LCD] set mode to %d" % int(value)

	def setRepeat(self, value):
		file = open("/proc/stb/lcd/scroll_repeats", "w")
		file.write('%d' % int(value))
		file.close()
		print "[LCD] set repeat to %d" % int(value)

	def setScrollspeed(self, value):
		file = open("/proc/stb/lcd/scroll_delay", "w")
		file.write('%d' % int(value))
		file.close()
		print "[LCD] set scrollspeed to %d" % int(value)

	def setHdd(self, value):
		file = open("/proc/stb/lcd/symbol_hdd", "w")
		file.write('%d' % int(value))
		file.close()
		print "[LCD] set Hdd to %d" % int(value)

	def setHddProgress(self, value):
		file = open("/proc/stb/lcd/symbol_hddprogress", "w")
		file.write('%d' % int(value))
		file.close()
		print "[LCD] set HDD Progress to %d" % int(value)

	def setSignal(self, value):
		file = open("/proc/stb/lcd/symbol_signal", "w")
		file.write('%d' % int(value))
		file.close()
		print "[LCD] set Signal to %d" % int(value)

	def setTv(self, value):
		file = open("/proc/stb/lcd/symbol_tv", "w")
		file.write('%d' % int(value))
		file.close()
		print "[LCD] set TV to %d" % int(value)

	def setUsb(self, value):
		file = open("/proc/stb/lcd/symbol_usb", "w")
		file.write('%d' % int(value))
		file.close()
		print "[LCD] set USB to %d" % int(value)

def leaveStandby():
	config.lcd.bright.apply()

def standbyCounterChanged(configElement):
	from Screens.Standby import inStandby
	inStandby.onClose.append(leaveStandby)
	config.lcd.standby.apply()

def InitLcd():
	detected = eDBoxLCD.getInstance().detected()
	SystemInfo["Display"] = detected
	config.lcd = ConfigSubsection();
	if detected:
		def setLCDbright(configElement):
			ilcd.setBright(configElement.value);

		def setLCDcontrast(configElement):
			ilcd.setContrast(configElement.value);

		def setLCDinverted(configElement):
			ilcd.setInverted(configElement.value);

		def setLCDmode(configElement):
			ilcd.setMode(configElement.value);

		def setLCDrepeat(configElement):
			ilcd.setRepeat(configElement.value);

		def setLCDscrollspeed(configElement):
			ilcd.setScrollspeed(configElement.value);

		def setLCDhdd(configElement):
			ilcd.setHdd(configElement.value);

		def setLCDhddprogress(configElement):
			ilcd.setHddProgress(configElement.value);

		def setLCDsignal(configElement):
			ilcd.setSignal(configElement.value);

		def setLCDtv(configElement):
			ilcd.setTv(configElement.value);

		def setLCDusb(configElement):
			ilcd.setUsb(configElement.value);

		standby_default = 0

		ilcd = LCD()

		if not ilcd.isOled():
			config.lcd.contrast = ConfigSlider(default=5, limits=(0, 20))
			config.lcd.contrast.addNotifier(setLCDcontrast);
		else:
			config.lcd.contrast = ConfigNothing()
			standby_default = 1

		config.lcd.standby = ConfigSlider(default=standby_default, limits=(0, 10))
		config.lcd.standby.addNotifier(setLCDbright);
		config.lcd.standby.apply = lambda : setLCDbright(config.lcd.standby)

		config.lcd.bright = ConfigSlider(default=5, limits=(0, 10))
		config.lcd.bright.addNotifier(setLCDbright);
		config.lcd.bright.apply = lambda : setLCDbright(config.lcd.bright)
		config.lcd.bright.callNotifiersOnSaveAndCancel = True

		config.lcd.invert = ConfigYesNo(default=False)
		config.lcd.invert.addNotifier(setLCDinverted);

		if path.exists("/proc/stb/lcd/scroll_delay"):
			config.lcd.mode = ConfigSelection([("0", _("No")), ("1", _("Yes"))], "1")
			config.lcd.mode.addNotifier(setLCDmode);
			config.lcd.repeat = ConfigSelection([("0", _("None")), ("1", _("1X")), ("2", _("2X")), ("3", _("3X")), ("4", _("4X")), ("500", _("Continues"))], "3")
			config.lcd.repeat.addNotifier(setLCDrepeat);
			config.lcd.scrollspeed = ConfigSlider(default = 150, increment = 10, limits = (0, 500))
			config.lcd.scrollspeed.addNotifier(setLCDscrollspeed);
			config.lcd.hddprogress = ConfigSlider(default = 150, increment = 16.6, limits = (0, 100))
			config.lcd.hddprogress.addNotifier(setLCDhddprogress);
			config.lcd.tv = ConfigSelection([("0", _("No")), ("1", _("Yes"))], "1")
			config.lcd.tv.addNotifier(setLCDtv);
			config.lcd.usb = ConfigSelection([("0", _("No")), ("1", _("Yes"))], "1")
			config.lcd.usb.addNotifier(setLCDusb);
		else:
			config.lcd.mode = ConfigNothing()
			config.lcd.repeat = ConfigNothing()
			config.lcd.scrollspeed = ConfigNothing()

	else:
		def doNothing():
			pass
		config.lcd.contrast = ConfigNothing()
		config.lcd.bright = ConfigNothing()
		config.lcd.standby = ConfigNothing()
		config.lcd.bright.apply = lambda : doNothing()
		config.lcd.standby.apply = lambda : doNothing()
		config.lcd.mode = ConfigNothing()
		config.lcd.repeat = ConfigNothing()
		config.lcd.scrollspeed = ConfigNothing()

	config.misc.standbyCounter.addNotifier(standbyCounterChanged, initial_call = False)

