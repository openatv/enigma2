from boxbranding import getBoxType

from twisted.internet import threads
from enigma import eDBoxLCD, eTimer

from config import config, ConfigSubsection, ConfigSelection, ConfigSlider, ConfigYesNo, ConfigNothing
from Components.SystemInfo import SystemInfo
from Tools.Directories import fileExists
from Components.Network import iNetwork
from Components.About import about
import usb


def IconCheck(session=None, **kwargs):
	if fileExists("/proc/stb/lcd/symbol_network") or fileExists("/proc/stb/lcd/symbol_usb"):
		global networklinkpoller
		networklinkpoller = IconCheckPoller()
		networklinkpoller.start()

class IconCheckPoller:
	def __init__(self):
		self.timer = eTimer()

	def start(self):
		if self.iconcheck not in self.timer.callback:
			self.timer.callback.append(self.iconcheck)
		self.timer.startLongTimer(0)

	def stop(self):
		if self.iconcheck in self.timer.callback:
			self.timer.callback.remove(self.iconcheck)
		self.timer.stop()

	def iconcheck(self):
		threads.deferToThread(self.JobTask)
		self.timer.startLongTimer(30)

	def JobTask(self):
		# Network state symbol
		netSymbol = "/proc/stb/lcd/symbol_network"
		if fileExists(netSymbol):
			linkUp = 0
			if config.lcd.mode.value == '1':
				for ifName in iNetwork.getInstalledAdapters():
					ifState = about.getIfConfig(ifName)
					if (
						'flags' in ifState and
						ifState['flags'].get('up') and
						ifState['flags'].get('running')
					):
						linkUp = 1
						break
			open(netSymbol, "w").write(str(linkUp))

		# USB devices connected symbol
		usbSymbol = "/proc/stb/lcd/symbol_usb"
		if fileExists(usbSymbol):
			USBState = 0
			busses = usb.busses()
			if config.lcd.mode.value == '1':
				for bus in busses:
					devices = bus.devices
					for dev in devices:
						if dev.deviceClass != 9 and dev.deviceClass != 2 and dev.idVendor > 0:
							# print ' '
							# print "Device:", dev.filename
							# print "  Number:", dev.deviceClass
							# print "  idVendor: %d (0x%04x)" % (dev.idVendor, dev.idVendor)
							# print "  idProduct: %d (0x%04x)" % (dev.idProduct, dev.idProduct)
							USBState = 1
							break
			open(usbSymbol, "w").write(str(USBState))

		self.timer.startLongTimer(30)

class LCD:
	def __init__(self):
		self.oled_type = eDBoxLCD.getInstance().isOled()
		if self.oled_type == 3:
			# Bitmapped OLED has 16 level of brightness
			self.oled_brightness_scale = 15
		else:
			# LCD display has 10 levels of brightness
			self.oled_brightness_scale = 10
		print "[LCD] oled_type=%d, oled_brightness_scale=%d" % (self.oled_type, self.oled_brightness_scale)

	def setBright(self, value):
		value *= 255
		value /= self.oled_brightness_scale
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

	def setFlipped(self, value):
		eDBoxLCD.getInstance().setFlipped(value)

	def isOled(self):
		return self.oled_type

	def setMode(self, value):
		print '[LCD] setMode', value
		f = open("/proc/stb/lcd/show_symbols", "w")
		f.write(value)
		f.close()

	def setRepeat(self, value):
		print '[LCD] setRepeat', value
		f = open("/proc/stb/lcd/scroll_repeats", "w")
		f.write(value)
		f.close()

	def setScrollspeed(self, value):
		print '[LCD] setScrollspeed', value
		f = open("/proc/stb/lcd/scroll_delay", "w")
		f.write(str(value))
		f.close()

	def setLEDNormalState(self, value):
		eDBoxLCD.getInstance().setLED(value, 0)

	def setLEDDeepStandbyState(self, value):
		eDBoxLCD.getInstance().setLED(value, 1)

	def setLEDBlinkingTime(self, value):
		eDBoxLCD.getInstance().setLED(value, 2)

	def setLEDStandby(self, value):
		file = open("/proc/stb/power/standbyled", "w")
		file.write(value and "on" or "off")
		file.close()

	def setLCDMiniTVMode(self, value):
		print '[LCD] setLCDMiniTVMode', value
		f = open('/proc/stb/lcd/mode', "w")
		f.write(value)
		f.close()

	def setLCDMiniTVPIPMode(self, value):
		print '[LCD] setLCDMiniTVPIPMode', value

	def setLCDMiniTVFPS(self, value):
		print '[LCD] setLCDMiniTVFPS',value
		f = open('/proc/stb/lcd/fps', "w")
		f.write("%d \n" % value)
		f.close()

def leaveStandby():
	config.lcd.bright.apply()
	if SystemInfo["LEDButtons"]:
		config.lcd.ledbrightness.apply()
		config.lcd.ledbrightnessdeepstandby.apply()

def standbyCounterChanged(configElement):
	from Screens.Standby import inStandby
	inStandby.onClose.append(leaveStandby)
	config.lcd.standby.apply()
	if SystemInfo["LEDButtons"]:
		config.lcd.ledbrightnessstandby.apply()
		config.lcd.ledbrightnessdeepstandby.apply()

def InitLcd():
	if getBoxType() in ('gb800se', 'gb800solo', 'iqonios300hd', 'tmsingle', 'tmnano2super', 'vusolo', 'et4x00', 'et5x00', 'et6x00'):
		detected = False
	else:
		detected = eDBoxLCD.getInstance().detected()

	ilcd = LCD()

	SystemInfo["Display"] = detected
	config.lcd = ConfigSubsection()

	if SystemInfo["StandbyLED"]:
		def setLEDstandby(configElement):
			ilcd.setLEDStandby(configElement.value)
		config.usage.standbyLED = ConfigYesNo(default=True)
		config.usage.standbyLED.addNotifier(setLEDstandby)

	if SystemInfo["LEDButtons"]:
		def setLEDnormalstate(configElement):
			ilcd.setLEDNormalState(configElement.value)

		def setLEDdeepstandby(configElement):
			ilcd.setLEDDeepStandbyState(configElement.value)

		def setLEDblinkingtime(configElement):
			ilcd.setLEDBlinkingTime(configElement.value)

		config.lcd.ledblinkingtime = ConfigSlider(default = 5, increment = 1, limits = (0,15))
		config.lcd.ledblinkingtime.addNotifier(setLEDblinkingtime)
		config.lcd.ledbrightnessdeepstandby = ConfigSlider(default = 1, increment = 1, limits = (0,15))
		config.lcd.ledbrightnessdeepstandby.addNotifier(setLEDnormalstate)
		config.lcd.ledbrightnessdeepstandby.addNotifier(setLEDdeepstandby)
		config.lcd.ledbrightnessdeepstandby.apply = lambda : setLEDdeepstandby(config.lcd.ledbrightnessdeepstandby)
		config.lcd.ledbrightnessstandby = ConfigSlider(default = 1, increment = 1, limits = (0,15))
		config.lcd.ledbrightnessstandby.addNotifier(setLEDnormalstate)
		config.lcd.ledbrightnessstandby.apply = lambda : setLEDnormalstate(config.lcd.ledbrightnessstandby)
		config.lcd.ledbrightness = ConfigSlider(default = 3, increment = 1, limits = (0,15))
		config.lcd.ledbrightness.addNotifier(setLEDnormalstate)
		config.lcd.ledbrightness.apply = lambda : setLEDnormalstate(config.lcd.ledbrightness)
		config.lcd.ledbrightness.callNotifiersOnSaveAndCancel = True

	if detected:
		config.lcd.scroll_speed = ConfigSelection(default="300", choices=[
			("500", _("slow")),
			("300", _("normal")),
			("100", _("fast"))])
		config.lcd.scroll_delay = ConfigSelection(default="10000", choices=[
			("10000", "10 " + _("seconds")),
			("20000", "20 " + _("seconds")),
			("30000", "30 " + _("seconds")),
			("60000", "1 " + _("minute")),
			("300000", "5 " + _("minutes")),
			("noscrolling", _("off"))])

		def setLCDbright(configElement):
			ilcd.setBright(configElement.value)

		def setLCDcontrast(configElement):
			ilcd.setContrast(configElement.value)

		def setLCDinverted(configElement):
			ilcd.setInverted(configElement.value)

		def setLCDflipped(configElement):
			ilcd.setFlipped(configElement.value)

		def setLCDmode(configElement):
			ilcd.setMode(configElement.value)

		def setLCDrepeat(configElement):
			ilcd.setRepeat(configElement.value)

		def setLCDscrollspeed(configElement):
			ilcd.setScrollspeed(configElement.value)

		def setLCDminitvmode(configElement):
			ilcd.setLCDMiniTVMode(configElement.value)

		def setLCDminitvpipmode(configElement):
			ilcd.setLCDMiniTVPIPMode(configElement.value)

		def setLCDminitvfps(configElement):
			ilcd.setLCDMiniTVFPS(configElement.value)

		standby_default = ilcd.oled_brightness_scale * 2 / 3

		if not ilcd.isOled():
			config.lcd.contrast = ConfigSlider(default=5, limits=(0, 20))
			config.lcd.contrast.addNotifier(setLCDcontrast)
		else:
			config.lcd.contrast = ConfigNothing()

		class BrightnessSlider(ConfigSlider):
			def __init__(self, **kwargs):
				self._value = None
				ConfigSlider.__init__(self, **kwargs)

			def setValue(self, value):
				if self._value != value:
					self._value = value
					self.changed()

			value = property(ConfigSlider.getValue, setValue)

			def onSelect(self, session):
				self.changed()

			def onDeselect(self, session):
				ConfigSlider.onDeselect(self, session)
				b = config.lcd.bright.saved_value
				if not b:
					b = config.lcd.bright.default
				ilcd.setBright(int(b))

		config.lcd.standby = BrightnessSlider(default=standby_default, limits=(0, ilcd.oled_brightness_scale))
		config.lcd.standby.addNotifier(setLCDbright)
		config.lcd.standby.apply = lambda: setLCDbright(config.lcd.standby)
		config.lcd.standby.callNotifiersOnSaveAndCancel = True

		config.lcd.bright = BrightnessSlider(default=ilcd.oled_brightness_scale, limits=(0, ilcd.oled_brightness_scale))
		config.lcd.bright.addNotifier(setLCDbright)
		config.lcd.bright.apply = lambda: setLCDbright(config.lcd.bright)
		config.lcd.bright.callNotifiersOnSaveAndCancel = True

		config.lcd.invert = ConfigYesNo(default=False)
		config.lcd.invert.addNotifier(setLCDinverted)

		config.lcd.flip = ConfigYesNo(default=False)
		config.lcd.flip.addNotifier(setLCDflipped)

		if SystemInfo["LCDMiniTV"]:
			config.lcd.minitvmode = ConfigSelection([("0", _("normal")), ("1", _("MiniTV")), ("2", _("OSD")), ("3", _("MiniTV with OSD"))], "0")
			config.lcd.minitvmode.addNotifier(setLCDminitvmode)
			config.lcd.minitvpipmode = ConfigSelection([("0", _("off")), ("5", _("PIP")), ("7", _("PIP with OSD"))], "0")
			config.lcd.minitvpipmode.addNotifier(setLCDminitvpipmode)
			config.lcd.minitvfps = ConfigSlider(default=30, limits=(0, 30))
			config.lcd.minitvfps.addNotifier(setLCDminitvfps)

		if fileExists("/proc/stb/lcd/scroll_delay"):
			config.lcd.scrollspeed = ConfigSlider(default=150, increment=10, limits=(0, 500))
			config.lcd.scrollspeed.addNotifier(setLCDscrollspeed)
		else:
			config.lcd.scrollspeed = ConfigNothing()
		if fileExists("/proc/stb/lcd/scroll_repeats"):
			config.lcd.repeat = ConfigSelection([("0", _("None")), ("1", _("1x")), ("2", _("2x")), ("3", _("3x")), ("4", _("4x")), ("5", _("5x")), ("10", _("10x")), ("255", _("Continuous"))], "3")
			config.lcd.repeat.addNotifier(setLCDrepeat)
		else:
			config.lcd.repeat = ConfigNothing()
		if fileExists("/proc/stb/lcd/show_symbols"):
			config.lcd.mode = ConfigSelection([("0", _("No")), ("1", _("Yes"))], "1")
			config.lcd.mode.addNotifier(setLCDmode)
		else:
			config.lcd.mode = ConfigNothing()

	else:
		def doNothing():
			pass
		config.lcd.contrast = ConfigNothing()
		config.lcd.bright = ConfigNothing()
		config.lcd.standby = ConfigNothing()
		config.lcd.bright.apply = lambda: doNothing()
		config.lcd.standby.apply = lambda: doNothing()
		config.lcd.mode = ConfigNothing()
		config.lcd.repeat = ConfigNothing()
		config.lcd.scrollspeed = ConfigNothing()
		config.lcd.ledbrightness = ConfigNothing()
		config.lcd.ledbrightness.apply = lambda: doNothing()
		config.lcd.ledbrightnessstandby = ConfigNothing()
		config.lcd.ledbrightnessstandby.apply = lambda: doNothing()
		config.lcd.ledbrightnessdeepstandby = ConfigNothing()
		config.lcd.ledbrightnessdeepstandby.apply = lambda: doNothing()
		config.lcd.ledblinkingtime = ConfigNothing()

	config.misc.standbyCounter.addNotifier(standbyCounterChanged, initial_call=False)
