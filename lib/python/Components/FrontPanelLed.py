from enigma import iRecordableService
from Components.config import config, ConfigSlider, ConfigSelection, ConfigSubsection
from Tools.Directories import fileExists


config.fp = ConfigSubsection()
config.fp.led = ConfigSubsection()
colors = [
	("0xFF0000", _("red")),
	("0xFF3333", _("rose")),
	("0xFF5500", _("orange")),
	("0xDD9900", _("yellow")),
	("0x99DD00", _("lime")),
	("0x00FF00", _("green")),
	("0x00FF99", _("aqua")),
	("0x00BBFF", _("olympic blue")),
	("0x0000FF", _("blue")),
	("0x6666FF", _("azure")),
	("0x9900FF", _("purple")),
	("0xFF0066", _("pink")),
	("0xFFFFFF", _("white")),
]
# running
config.fp.led.default_color = ConfigSelection(colors, default="0xFFFFFF")
config.fp.led.default_brightness = ConfigSlider(default=0xff, increment=25, limits=(0, 0xff))
# standby
config.fp.led.standby_color = ConfigSelection(colors, default="0xFFFFFF")
config.fp.led.standby_brightness = ConfigSlider(default=0x08, increment=8, limits=(0, 0xff))
# shutdown
config.fp.led.shutdown_color = ConfigSelection(colors, default="0xFF5500")

frontPanelLed = None


class FrontPanelLed:
	BLINK_PATH = "/proc/stb/fp/led_blink"
	BLINK_DEFAULT = 0x0710ff

	BRIGHTNESS_PATH = "/proc/stb/fp/led_brightness"
	BRIGHTNESS_DEFAULT = 0xFF

	COLOR_PATH = "/proc/stb/fp/led_color"
	COLOR_DEFAULT = 0xFFFFFF

	FADE_PATH = "/proc/stb/fp/led_fade"
	FADE_DEFAULT = 0x7

	instance = None

	def __init__(self):
		assert (not FrontPanelLed.instance)
		FrontPanelLed.instance = self
		self._session = None
		self.default()
		config.misc.standbyCounter.addNotifier(self._onStandby, initial_call=False)
		config.fp.led.default_color.addNotifier(self._onDefaultChanged, initial_call=False)
		config.fp.led.default_brightness.addNotifier(self._onDefaultChanged, initial_call=False)

	def init(self, session):
		self._session = session
		session.nav.record_event.append(self.checkRecordings)

	def _onDefaultChanged(self, *args):
		from Screens.Standby import inStandby
		if not inStandby:
			FrontPanelLed.default()

	def _onStandby(self, *args):
		FrontPanelLed.standby()
		from Screens.Standby import inStandby
		if inStandby:
			inStandby.onClose.append(self._onLeaveStandby)

	def _onLeaveStandby(self):
		FrontPanelLed.default()

	def checkRecordings(self, service=None, event=iRecordableService.evEnd):
		if not self._session:
			return
		if event == iRecordableService.evEnd:
			if self._session.nav.getAnyRecordingsCount():
				FrontPanelLed.recording()
			else:
				FrontPanelLed.stopRecording()
		elif event == iRecordableService.evStart:
			FrontPanelLed.recording()

	@staticmethod
	def _write(path, value):
		if not fileExists(path):
			print("[FrontPanelLed] %s does not exist!" % (path))
			return
		with open(path, 'w') as f:
			value = "%x" % (value)
			print("[FrontPanelLed] : %s" % (value))
			f.write(value)

	# 8 bit brightness
	@staticmethod
	def setBrightness(value=BRIGHTNESS_DEFAULT):
		if value > 0xff or value < 0:
			print("[FrontPanelLed]  LED brightness has to be between 0x0 and 0xff! Using default value (%x)" % (FrontPanelLed.BRIGHTNESS_DEFAULT))
			value = FrontPanelLed.BRIGHTNESS_DEFAULT
		FrontPanelLed._write(FrontPanelLed.BRIGHTNESS_PATH, value)

	# 24 bit RGB
	@staticmethod
	def setColor(value=COLOR_DEFAULT):
		if value > 0xffffff or value < 0:
			print("[FrontPanelLed]  LED color has to be between 0x0 and 0xffffff (r, g b)! Using default value (%x)" % (FrontPanelLed.COLOR_DEFAULT))
			value = FrontPanelLed.COLOR_DEFAULT
		FrontPanelLed._write(FrontPanelLed.COLOR_PATH, value)

	# 8 bit on-time (* 31ms), 8 bit total time (* 31ms), 8 bit number of repeats (ff == unlimited)
	@staticmethod
	def setBlink(value=BLINK_DEFAULT):
		if value > 0xffffff or value < 0:
			print("[FrontPanelLed]  LED blink has to be between 0x0 and 0xffffff (on, total, repeats)! Using default value (%x)" % (FrontPanelLed.BLINK_DEFAULT))
			value = FrontPanelLed.BLINK_DEFAULT
		FrontPanelLed._write(FrontPanelLed.BLINK_PATH, value)

	# 8 bit fade time (* 51ms)
	@staticmethod
	def setFade(value=FADE_DEFAULT):
		if value > 0xff or value < 0:
			value = FrontPanelLed.FADE_DEFAULT
			print("[FrontPanelLed] LED fade has to be between 0x0 and 0xff! Using default value (%x)" % (FrontPanelLed.FADE_DEFAULT))
		FrontPanelLed._write(FrontPanelLed.FADE_PATH, value)

	@staticmethod
	def default(checkRec=True):
		FrontPanelLed.setBrightness(config.fp.led.default_brightness.value)
		FrontPanelLed.setColor(int(config.fp.led.default_color.value, 0))
		if checkRec:
			FrontPanelLed.instance.checkRecordings()

	@staticmethod
	def recording():
		FrontPanelLed.setFade()
		FrontPanelLed.setBlink()

	@staticmethod
	def stopRecording():
		from Screens.Standby import inStandby
		if inStandby:
			FrontPanelLed.standby(False)
		else:
			FrontPanelLed.default(False)

	@staticmethod
	def standby(checkRec=True):
		FrontPanelLed.setBrightness(config.fp.led.standby_brightness.value)
		FrontPanelLed.setColor(int(config.fp.led.standby_color.value, 0))
		if checkRec:
			FrontPanelLed.instance.checkRecordings()

	@staticmethod
	def shutdown():
		FrontPanelLed.setFade(0)
		FrontPanelLed.setBrightness(0xFF)
		FrontPanelLed.setColor(int(config.fp.led.shutdown_color.value, 0))
		FrontPanelLed.setBlink()


frontPanelLed = FrontPanelLed()
