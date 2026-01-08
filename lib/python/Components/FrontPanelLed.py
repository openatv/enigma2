from os.path import exists

from enigma import iRecordableService

from Components.config import ConfigSelection, ConfigSlider, ConfigSubsection, config
from Components.SystemInfo import BoxInfo
from Tools.Directories import fileWriteLine

MODULE_NAME = __name__.split(".")[-1]
BLINK_DEFAULT = 0x0710FF
BRIGHTNESS_DEFAULT = 0xFF
COLOR_DEFAULT = 0xFFFFFF
FADE_DEFAULT = 0x07


class FrontPanelLed:
	def __init__(self):
		if BoxInfo.getItem("LEDColorControl"):
			ledBlinkPath = "/proc/stb/fp/led_blink"
			ledBrightnessPath = "/proc/stb/fp/led_brightness"
			ledColorPath = "/proc/stb/fp/led_color"
			ledFadePath = "/proc/stb/fp/led_fade"
			self.ledBlinkPath = ledBlinkPath if exists(ledBlinkPath) else None
			self.ledBrightnessPath = ledBrightnessPath if exists(ledBrightnessPath) else None
			self.ledColorPath = ledColorPath if exists(ledColorPath) else None
			self.ledFadePath = ledFadePath if exists(ledFadePath) else None
			ledColors = [
				(0x00FF99, _("Aqua")),
				(0x6666FF, _("Azure")),
				(0x0000FF, _("Blue")),
				(0x00FF00, _("Green")),
				(0x99DD00, _("Lime")),
				(0x00BBFF, _("Olympic blue")),
				(0xFF5500, _("Orange")),
				(0xFF0066, _("Pink")),
				(0x9900FF, _("Purple")),
				(0xFF0000, _("Red")),
				(0xFF3333, _("Rose")),
				(0xFFFFFF, _("White")),
				(0xDD9900, _("Yellow"))
			]
			config.fp = ConfigSubsection()
			config.fp.led = ConfigSubsection()
			config.fp.led.default_brightness = ConfigSlider(default=0xFF, increment=25, limits=(0, 0xFF))
			config.fp.led.default_color = ConfigSelection(default=0xFFFFFF, choices=ledColors)
			config.fp.led.shutdown_color = ConfigSelection(default=0xFF5500, choices=ledColors)
			config.fp.led.standby_brightness = ConfigSlider(default=0x08, increment=8, limits=(0, 0xFF))
			config.fp.led.standby_color = ConfigSelection(default=0xFFFFFF, choices=ledColors)
			config.fp.led.default_brightness.addNotifier(self.onDefaultChanged, initial_call=False)
			config.fp.led.default_color.addNotifier(self.onDefaultChanged, initial_call=False)
			config.misc.standbyCounter.addNotifier(self.onStandby, initial_call=False)
			self.session = None

	def setSession(self, session):
		if BoxInfo.getItem("LEDColorControl"):
			self.session = session
			session.nav.record_event.append(self.checkRecordings)
			self.checkRecordings()

	def checkRecordings(self, service=None, event=iRecordableService.evEnd):
		def recordingActive():
			self.setFade()
			self.setBlink()

		def recordingInactive():
			from Screens.Standby import inStandby
			if inStandby:
				self.standby(checkRec=False)
			else:
				self.default(checkRec=False)

		if event == iRecordableService.evEnd:
			if self.session.nav.getAnyRecordingsCount():
				recordingActive()
			else:
				recordingInactive()
		elif event == iRecordableService.evStart:
			recordingActive()

	def default(self, checkRec=True):
		self.setBrightness(config.fp.led.default_brightness.value)
		self.setColor(config.fp.led.default_color.value)
		if checkRec and self.session:
			self.checkRecordings()

	def onStandby(self, *args):
		self.standby(checkRec=True)
		from Screens.Standby import inStandby
		if inStandby:
			inStandby.onClose.append(self.default)

	def onDefaultChanged(self, *args):
		from Screens.Standby import inStandby
		if not inStandby:
			self.default(checkRec=True)

	def standby(self, checkRec=True):
		self.setBrightness(config.fp.led.standby_brightness.value)
		self.setColor(config.fp.led.standby_color.value)
		if checkRec and self.session:
			self.checkRecordings()

	def shutdown(self):
		if BoxInfo.getItem("LEDColorControl"):
			self.setFade(0x00)
			self.setBrightness()
			self.setColor(config.fp.led.shutdown_color.value)
			self.setBlink()

	def setBlink(self, value=BLINK_DEFAULT):  # 8 bit on-time (* 31ms), 8 bit total time (* 31ms), 8 bit number of repeats (FF == unlimited).
		if not 0x0 <= value <= 0xFFFFFF:
			print(f"[FrontPanelLed] LED blink must be between 0x000000 and 0xFFFFFF (on, total, repeats) not '{value:06X}'!  Using default of {BLINK_DEFAULT:06X}.")
			value = BLINK_DEFAULT
		self.procWrite(self.ledBlinkPath, value)

	def setBrightness(self, value=BRIGHTNESS_DEFAULT):  # 8 bit brightness.
		if not 0x0 <= value <= 0xFF:
			print(f"[FrontPanelLed] LED brightness must be between 0x00 and 0xFF not '{value:02X}'!  Using default of {BRIGHTNESS_DEFAULT:02X}.")
			value = BRIGHTNESS_DEFAULT
		self.procWrite(self.ledBrightnessPath, value)

	def setColor(self, value=COLOR_DEFAULT):  # 24 bit RGB.
		if not 0x0 <= value <= 0xFFFFFF:
			print(f"[FrontPanelLed] LED color must be between 0x000000 and 0xFFFFFF (R, G B) not '{value:06X}'!  Using default of {COLOR_DEFAULT:06X}.")
			value = COLOR_DEFAULT
		self.procWrite(self.ledColorPath, value)

	def setFade(self, value=FADE_DEFAULT):  # 8 bit fade time (* 51ms).
		if not 0x0 <= value <= 0xFF:
			print(f"[FrontPanelLed] LED fade must be between 0x00 and 0xFF not '{value:02X}'!  Using default of {FADE_DEFAULT:02X}.")
			value = FADE_DEFAULT
		self.procWrite(self.ledFadePath, value)

	def procWrite(self, ledPath, value):
		if ledPath:
			fileWriteLine(ledPath, f"{value:X}", source=MODULE_NAME)


frontPanelLed = FrontPanelLed()
