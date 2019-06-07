from boxbranding import getBoxType, getMachineBuild
from sys import maxint

from twisted.internet import threads
from enigma import eDBoxLCD, eTimer, eActionMap

from config import config, ConfigSubsection, ConfigSelection, ConfigSlider, ConfigYesNo, ConfigNothing
from Components.SystemInfo import SystemInfo
from Tools.Directories import fileExists
from Screens.Screen import Screen
import Screens.Standby
from Components.Network import iNetwork
from Components.About import about
import usb


class dummyScreen(Screen):
	skin = """<screen position="0,0" size="0,0" transparent="1">
	<widget source="session.VideoPicture" render="Pig" position="0,0" size="0,0" backgroundColor="transparent" zPosition="1"/>
	</screen>"""

	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.close()

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

		eActionMap.getInstance().bindAction('', -maxint - 1, self.DimUpEvent)
		self.autoDimDownLCDTimer = eTimer()
		self.autoDimDownLCDTimer.callback.append(self.autoDimDownLCD)
		self.autoDimUpLCDTimer = eTimer()
		self.autoDimUpLCDTimer.callback.append(self.autoDimUpLCD)
		self.currBrightness = self.dimBrightness = self.Brightness = None
		self.dimDelay = 0
		config.misc.standbyCounter.addNotifier(self.standbyCounterChanged, initial_call=False)

	def standbyCounterChanged(self, configElement):
		Screens.Standby.inStandby.onClose.append(self.leaveStandby)
		self.autoDimDownLCDTimer.stop()
		self.autoDimUpLCDTimer.stop()
		eActionMap.getInstance().unbindAction('', self.DimUpEvent)

	def leaveStandby(self):
		eActionMap.getInstance().bindAction('', -maxint - 1, self.DimUpEvent)

	def DimUpEvent(self, key, flag):
		self.autoDimDownLCDTimer.stop()
		if not Screens.Standby.inTryQuitMainloop:
			if self.Brightness is not None and not self.autoDimUpLCDTimer.isActive():
				self.autoDimUpLCDTimer.start(25, True)

	def autoDimDownLCD(self):
		if not Screens.Standby.inTryQuitMainloop:
			if self.dimBrightness is not None and self.currBrightness > self.dimBrightness:
				self.currBrightness = self.currBrightness - 256 / self.oled_brightness_scale
				if self.currBrightness < self.dimBrightness:
					self.currBrightness = self.dimBrightness
				eDBoxLCD.getInstance().setLCDBrightness(self.currBrightness)
				self.autoDimDownLCDTimer.start(25, True)

	def autoDimUpLCD(self):
		if not Screens.Standby.inTryQuitMainloop:
			self.autoDimDownLCDTimer.stop()
			if self.currBrightness < self.Brightness:
				self.currBrightness = self.currBrightness + 2 * 256 / self.oled_brightness_scale
				if self.currBrightness > self.Brightness:
					self.currBrightness = self.Brightness
				eDBoxLCD.getInstance().setLCDBrightness(self.currBrightness)
				self.autoDimUpLCDTimer.start(25, True)
			else:
				if self.dimBrightness is not None and self.currBrightness > self.dimBrightness and self.dimDelay is not None and self.dimDelay > 0:
					self.autoDimDownLCDTimer.startLongTimer(self.dimDelay)

	def setBright(self, value):
		value *= 255
		value /= self.oled_brightness_scale
		if value > 255:
			value = 255
		self.autoDimDownLCDTimer.stop()
		self.autoDimUpLCDTimer.stop()
		self.currBrightness = self.Brightness = value
		eDBoxLCD.getInstance().setLCDBrightness(self.currBrightness)
		if self.dimBrightness is not None and self.currBrightness > self.dimBrightness:
			if self.dimDelay is not None and self.dimDelay > 0:
				self.autoDimDownLCDTimer.startLongTimer(self.dimDelay)

	def setStandbyBright(self, value):
		value *= 255
		value /= self.oled_brightness_scale
		if value > 255:
			value = 255
		self.autoDimDownLCDTimer.stop()
		self.autoDimUpLCDTimer.stop()
		self.Brightness = value
		if self.dimBrightness is None:
			self.dimBrightness = value
		if self.currBrightness is None:
			self.currBrightness = value
		eDBoxLCD.getInstance().setLCDBrightness(self.Brightness)

	def setDimBright(self, value):
		value *= 255
		value /= self.oled_brightness_scale
		if value > 255:
			value = 255
		self.dimBrightness = value

	def setDimDelay(self, value):
		self.dimDelay = int(value)

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

	def setPower(self, value):
		print 'setLCDPower', value
		f = open("/proc/stb/power/vfd", "w")
		f.write(value)
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
		print '[LCD] setLCDMiniTVFPS', value
		f = open('/proc/stb/lcd/fps', "w")
		f.write("%d \n" % value)
		f.close()

def leaveStandby():
	config.lcd.bright.apply()
	if SystemInfo["LEDButtons"]:
		config.lcd.ledbrightness.apply()
		config.lcd.ledbrightnessdeepstandby.apply()

def standbyCounterChanged(dummy):
	from Screens.Standby import inStandby
	inStandby.onClose.append(leaveStandby)
	config.lcd.standby.apply()
	if SystemInfo["LEDButtons"]:
		config.lcd.ledbrightnessstandby.apply()
		config.lcd.ledbrightnessdeepstandby.apply()

def InitLcd():
	if getBoxType() in ('et4x00', 'et5x00', 'et6x00', 'gb800se', 'gb800solo', 'inihde2', 'iqonios300hd', 'mbmicro', 'sf128', 'sf138', 'tmsingle', 'tmnano2super', 'tmnanose', 'tmnanoseplus', 'tmnanosem2', 'tmnanosem2plus', 'tmnanosecombo', 'vusolo') or getMachineBuild() in ('inihde2', ):
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

		config.lcd.ledblinkingtime = ConfigSlider(default=5, increment=1, limits=(0, 15))
		config.lcd.ledblinkingtime.addNotifier(setLEDblinkingtime)
		config.lcd.ledbrightnessdeepstandby = ConfigSlider(default=1, increment=1, limits=(0, 15))
		config.lcd.ledbrightnessdeepstandby.addNotifier(setLEDnormalstate)
		config.lcd.ledbrightnessdeepstandby.addNotifier(setLEDdeepstandby)
		config.lcd.ledbrightnessdeepstandby.apply = lambda: setLEDdeepstandby(config.lcd.ledbrightnessdeepstandby)
		config.lcd.ledbrightnessstandby = ConfigSlider(default=1, increment=1, limits=(0, 15))
		config.lcd.ledbrightnessstandby.addNotifier(setLEDnormalstate)
		config.lcd.ledbrightnessstandby.apply = lambda: setLEDnormalstate(config.lcd.ledbrightnessstandby)
		config.lcd.ledbrightness = ConfigSlider(default=3, increment=1, limits=(0, 15))
		config.lcd.ledbrightness.addNotifier(setLEDnormalstate)
		config.lcd.ledbrightness.apply = lambda: setLEDnormalstate(config.lcd.ledbrightness)
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

		def setLCDstandbybright(configElement):
			ilcd.setStandbyBright(configElement.value)

		def setLCDdimbright(configElement):
			ilcd.setDimBright(configElement.value)

		def setLCDdimdelay(configElement):
			ilcd.setDimDelay(configElement.value)

		def setLCDcontrast(configElement):
			ilcd.setContrast(configElement.value)

		def setLCDinverted(configElement):
			ilcd.setInverted(configElement.value)

		def setLCDflipped(configElement):
			ilcd.setFlipped(configElement.value)

		def setLCDmode(configElement):
			ilcd.setMode(configElement.value)

		def setLCDpower(configElement):
			ilcd.setPower(configElement.value)

		def setfblcddisplay(configElement):
			ilcd.setfblcddisplay(configElement.value)

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

		def writeFp(fp, configElement):
			fp = "/proc/stb/fp/" + fp
			if fileExists(fp):
				f = open(fp, "w")
				f.write(configElement.value)
				f.close()

		def setLedPowerColor(configElement):
			writeFp("ledpowercolor", configElement)

		def setLedStandbyColor(configElement):
			writeFp("ledstandbycolor", configElement)

		def setLedSuspendColor(configElement):
			writeFp("ledsuspendledcolor", configElement)

		def setPower4x7On(configElement):
			writeFp("power4x7on", configElement)

		def setPower4x7Standby(configElement):
			writeFp("power4x7standby", configElement)

		def setPower4x7Suspend(configElement):
			writeFp("power4x7suspend", configElement)

		ledchoices = [("0", _("off")), ("1", _("blue")), ("2", _("red")), ("3", _("violet"))]
		config.usage.lcd_ledpowercolor = ConfigSelection(default="1", choices=ledchoices[:])
		config.usage.lcd_ledpowercolor.addNotifier(setLedPowerColor)

		config.usage.lcd_ledstandbycolor = ConfigSelection(default="3", choices=ledchoices[:])
		config.usage.lcd_ledstandbycolor.addNotifier(setLedStandbyColor)

		config.usage.lcd_ledsuspendcolor = ConfigSelection(default="2", choices=ledchoices[:])
		config.usage.lcd_ledsuspendcolor.addNotifier(setLedSuspendColor)

		config.usage.lcd_power4x7on = ConfigSelection(default="on", choices=[("off", _("off")), ("on", _("on"))])
		config.usage.lcd_power4x7on.addNotifier(setPower4x7On)

		config.usage.lcd_power4x7standby = ConfigSelection(default="off", choices=[("off", _("off")), ("on", _("on"))])
		config.usage.lcd_power4x7standby.addNotifier(setPower4x7Standby)

		config.usage.lcd_power4x7suspend = ConfigSelection(default="off", choices=[("off", _("off")), ("on", _("on"))])
		config.usage.lcd_power4x7suspend.addNotifier(setPower4x7Suspend)

		brightness_default = ilcd.oled_brightness_scale
		standby_default = ilcd.oled_brightness_scale * 2 / 3

		if not ilcd.isOled():
			config.lcd.contrast = ConfigSlider(default=5, limits=(0, 20))
			config.lcd.contrast.addNotifier(setLCDcontrast)
		else:
			config.lcd.contrast = ConfigNothing()
			standby_default = 1

		if getMachineBuild() in ('beyonwizv2', ):
			brightness_default = 1
			standby_default = 1

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

		config.lcd.bright = BrightnessSlider(default=brightness_default, limits=(0, ilcd.oled_brightness_scale))
		config.lcd.bright.addNotifier(setLCDbright)
		config.lcd.bright.apply = lambda: setLCDbright(config.lcd.bright)
		config.lcd.bright.callNotifiersOnSaveAndCancel = True

		config.lcd.dimbright = ConfigSlider(default=standby_default, limits=(0, ilcd.oled_brightness_scale))
		config.lcd.dimbright.addNotifier(setLCDdimbright)
		config.lcd.dimbright.apply = lambda: setLCDdimbright(config.lcd.dimbright)
		config.lcd.dimdelay = ConfigSelection(default="0", choices=[
			("5", "5 " + _("seconds")),
			("10", "10 " + _("seconds")),
			("15", "15 " + _("seconds")),
			("20", "20 " + _("seconds")),
			("30", "30 " + _("seconds")),
			("60", "1 " + _("minute")),
			("120", "2 " + _("minutes")),
			("300", "5 " + _("minutes")),
			("0", _("off"))])
		config.lcd.dimdelay.addNotifier(setLCDdimdelay)

		config.lcd.invert = ConfigYesNo(default=False)
		config.lcd.invert.addNotifier(setLCDinverted)

		def PiconPackChanged(configElement):
			configElement.save()
		config.lcd.picon_pack = ConfigYesNo(default=False)
		config.lcd.picon_pack.addNotifier(PiconPackChanged)

		config.lcd.flip = ConfigYesNo(default=False)
		config.lcd.flip.addNotifier(setLCDflipped)

		if SystemInfo["LcdLiveTV"]:
			def lcdLiveTvChanged(configElement):
				setLCDLiveTv(configElement.value)
				configElement.save()
			config.lcd.showTv = ConfigYesNo(default=False)
			config.lcd.showTv.addNotifier(lcdLiveTvChanged)

			if "live_enable" in SystemInfo["LcdLiveTV"]:
				config.misc.standbyCounter.addNotifier(standbyCounterChangedLCDLiveTV, initial_call=False)

		if SystemInfo["LCDMiniTV"]:
			config.lcd.minitvmode = ConfigSelection([("0", _("normal")), ("1", _("MiniTV")), ("2", _("OSD")), ("3", _("MiniTV with OSD"))], "0")
			config.lcd.minitvmode.addNotifier(setLCDminitvmode)
			config.lcd.minitvpipmode = ConfigSelection([("0", _("off")), ("5", _("PIP")), ("7", _("PIP with OSD"))], "0")
			config.lcd.minitvpipmode.addNotifier(setLCDminitvpipmode)
			config.lcd.minitvfps = ConfigSlider(default=30, limits=(0, 30))
			config.lcd.minitvfps.addNotifier(setLCDminitvfps)

		if SystemInfo["VFD_scroll_delay"]:
			config.lcd.scrollspeed = ConfigSlider(default=150, increment=1, limits=(0, 500))
			config.lcd.scrollspeed.addNotifier(setLCDscrollspeed)
		else:
			config.lcd.scrollspeed = ConfigNothing()

		if SystemInfo["VFD_initial_scroll_delay"]:
			def initial_scroll_delay(el):
				open(SystemInfo["VFD_initial_scroll_delay"], "w").write(el.value)
			choicelist = [
				("10000", "10 " + _("seconds")),
				("20000", "20 " + _("seconds")),
				("30000", "30 " + _("seconds")),
				("0", _("no delay"))
			]
			config.usage.vfd_initial_scroll_delay = ConfigSelection(default="1000", choices=choicelist)
			config.usage.vfd_initial_scroll_delay.addNotifier(initial_scroll_delay, immediate_feedback=False)

		if SystemInfo["VFD_final_scroll_delay"]:
			def final_scroll_delay(el):
				open(SystemInfo["VFD_final_scroll_delay"], "w").write(el.value)
			choicelist = [
				("10000", "10 " + _("seconds")),
				("20000", "20 " + _("seconds")),
				("30000", "30 " + _("seconds")),
				("0", _("no delay"))
			]
			config.usage.vfd_final_scroll_delay = ConfigSelection(default="1000", choices=choicelist)
			config.usage.vfd_final_scroll_delay.addNotifier(final_scroll_delay, immediate_feedback=False)

		if SystemInfo["VFD_scroll_repeats"]:
			config.lcd.repeat = ConfigSelection([("0", _("None")), ("1", _("1x")), ("2", _("2x")), ("3", _("3x")), ("4", _("4x")), ("5", _("5x")), ("10", _("10x")), ("255", _("Continuous"))], "3")
			config.lcd.repeat.addNotifier(setLCDrepeat)
		else:
			config.lcd.repeat = ConfigNothing()

		if fileExists("/proc/stb/lcd/show_symbols"):
			config.lcd.mode = ConfigSelection([("0", _("No")), ("1", _("Yes"))], "1")
			config.lcd.mode.addNotifier(setLCDmode)
		else:
			config.lcd.mode = ConfigNothing()

		if fileExists("/proc/stb/power/vfd"):
			config.lcd.power = ConfigSelection([("0", _("off")), ("1", _("on"))], "1")
			config.lcd.power.addNotifier(setLCDpower)
		else:
			config.lcd.power = ConfigNothing()
	else:
		def doNothing():
			pass
		config.lcd.contrast = ConfigNothing()
		config.lcd.bright = ConfigNothing()
		config.lcd.standby = ConfigNothing()
		config.lcd.bright.apply = lambda: doNothing()
		config.lcd.standby.apply = lambda: doNothing()
		config.lcd.fblcddisplay = ConfigNothing()
		config.lcd.mode = ConfigNothing()
		config.lcd.repeat = ConfigNothing()
		config.lcd.scrollspeed = ConfigNothing()
		config.lcd.power = ConfigNothing()
		config.lcd.ledbrightness = ConfigNothing()
		config.lcd.ledbrightness.apply = lambda: doNothing()
		config.lcd.ledbrightnessstandby = ConfigNothing()
		config.lcd.ledbrightnessstandby.apply = lambda: doNothing()
		config.lcd.ledbrightnessdeepstandby = ConfigNothing()
		config.lcd.ledbrightnessdeepstandby.apply = lambda: doNothing()
		config.lcd.ledblinkingtime = ConfigNothing()
		config.lcd.picon_pack = ConfigNothing()

	config.misc.standbyCounter.addNotifier(standbyCounterChanged, initial_call=False)

def setLCDLiveTv(value):
	if "live_enable" in SystemInfo["LcdLiveTV"]:
		open(SystemInfo["LcdLiveTV"], "w").write(value and "enable" or "disable")
	else:
		open(SystemInfo["LcdLiveTV"], "w").write(value and "0" or "1")
	if not value:
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		InfoBarInstance and InfoBarInstance.session.open(dummyScreen)

def leaveStandbyLCDLiveTV():
	if config.lcd.showTv.value:
		setLCDLiveTv(True)

def standbyCounterChangedLCDLiveTV(dummy):
	if config.lcd.showTv.value:
		from Screens.Standby import inStandby
		if leaveStandbyLCDLiveTV not in inStandby.onClose:
			inStandby.onClose.append(leaveStandbyLCDLiveTV)
		setLCDLiveTv(False)
