from os.path import exists
from Components.config import config, ConfigSubsection, ConfigSlider, ConfigSelection, ConfigNothing, NoSave

# The "VideoEnhancement" is the interface to /sys/class/amvecm.
#
# UX convention (matches the non-AML VideoEnhancement plugin):
#   Every slider is unsigned 0..255 with 128 = neutral. The notifier maps
#   that to the kernel-native signed range before writing to sysfs.
#
# Kernel-accepted ranges on Amlogic S922X amvecm (probed live):
#   contrast1/2:      -127..127
#   brightness1/2:    -1024..1023
#   saturation (saturation_hue_post, first field):  -128..127
#   saturation_hue (packed 32-bit, hi half 0..0x200, default 0x100 = neutral)
#   color_top / color_bottom: 0..0x3fffffff (per-channel 10-bit RGB clamp)

AMVECM = "/sys/class/amvecm"
SLIDER_MAX = 255
SLIDER_NEUTRAL = 128


def _readRawText(p):
	try:
		with open(p, "r") as f:
			return f.read().strip()
	except OSError:
		return None


def _readInt(p, fallback):
	v = _readRawText(p)
	if v is None:
		return fallback
	try:
		return int(v, 0)
	except ValueError:
		return fallback


def _readPair(p, fallback):
	# saturation_hue_post returns "<sat> <hue>"
	v = _readRawText(p)
	if v is None:
		return fallback
	parts = v.split()
	try:
		return (int(parts[0], 0), int(parts[1], 0))
	except (ValueError, IndexError):
		return fallback


def _clamp(v, lo, hi):
	return max(lo, min(hi, v))


def _kernelToSlider(kval, scale):
	# kval is signed, neutral at 0 in kernel space. slider neutral = 128.
	return _clamp(SLIDER_NEUTRAL + int(round(kval / scale)), 0, SLIDER_MAX)


def _sliderToKernel(sval, scale, lo, hi):
	return _clamp(int(round((sval - SLIDER_NEUTRAL) * scale)), lo, hi)


class VideoEnhancement:
	firstRun = True

	def __init__(self):
		self.last_modes_preferred = []
		self.createConfig()

	def createConfig(self):
		config.amvecm = ConfigSubsection()
		config.amvecm.configsteps = NoSave(ConfigSelection(choices=[1, 5, 10, 25], default=1))

		# --- contrast1: kernel -127..127, slider 0..255 (scale 1.0) ---
		if exists("%s/contrast1" % AMVECM):
			initial = _kernelToSlider(_readInt("%s/contrast1" % AMVECM, 0), 1.0)

			def setContrast1(configItem):
				kval = _sliderToKernel(int(configItem.value), 1.0, -127, 127)
				try:
					print("--> setting contrast1 (video) to: %d" % kval)
					with open("%s/contrast1" % AMVECM, "w") as f:
						f.write(str(kval))
				except OSError:
					print("couldn't write contrast1.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.amvecm.contrast1 = ConfigSlider(default=initial, limits=(0, SLIDER_MAX))
			config.amvecm.contrast1.addNotifier(setContrast1)
		else:
			config.amvecm.contrast1 = NoSave(ConfigNothing())

		# --- contrast2: kernel -127..127, slider 0..255 (scale 1.0) ---
		if exists("%s/contrast2" % AMVECM):
			initial = _kernelToSlider(_readInt("%s/contrast2" % AMVECM, 0), 1.0)

			def setContrast2(configItem):
				kval = _sliderToKernel(int(configItem.value), 1.0, -127, 127)
				try:
					print("--> setting contrast2 (video+OSD) to: %d" % kval)
					with open("%s/contrast2" % AMVECM, "w") as f:
						f.write(str(kval))
				except OSError:
					print("couldn't write contrast2.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.amvecm.contrast2 = ConfigSlider(default=initial, limits=(0, SLIDER_MAX))
			config.amvecm.contrast2.addNotifier(setContrast2)
		else:
			config.amvecm.contrast2 = NoSave(ConfigNothing())

		# --- saturation: kernel -127..127, slider 0..255 (scale 1.0) ---
		if exists("%s/saturation_hue_post" % AMVECM):
			initialSat, _initialHuePost = _readPair("%s/saturation_hue_post" % AMVECM, (0, 0))
			initial = _kernelToSlider(initialSat, 1.0)

			def setSaturation(configItem):
				kval = _sliderToKernel(int(configItem.value), 1.0, -127, 127)
				# preserve current hue_post so we don't clobber it with a hard 0
				_curSat, curHuePost = _readPair("%s/saturation_hue_post" % AMVECM, (0, 0))
				try:
					print("--> setting saturation to: %d (hue_post preserved: %d)" % (kval, curHuePost))
					with open("%s/saturation_hue_post" % AMVECM, "w") as f:
						f.write("%d %d" % (kval, curHuePost))
				except OSError:
					print("couldn't write saturation.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.amvecm.saturation = ConfigSlider(default=initial, limits=(0, SLIDER_MAX))
			config.amvecm.saturation.addNotifier(setSaturation)
		else:
			config.amvecm.saturation = NoSave(ConfigNothing())

		# --- hue: kernel saturation_hue packed 32-bit, hi half 0..0x200, neutral 0x100.
		# Map slider 0..255 to hi half 0..510 (slider 128 -> 256 = 0x100 neutral). ---
		if exists("%s/saturation_hue" % AMVECM):
			rawInitial = _readInt("%s/saturation_hue" % AMVECM, 0x1000000)
			hiInitial = (rawInitial >> 16) & 0xffff
			initial = _clamp(hiInitial // 2, 0, SLIDER_MAX)

			def setHue(configItem):
				hi = _clamp(int(configItem.value) * 2, 0, 0x1ff)
				packed = (hi << 16) & 0xffffffff
				try:
					print("--> setting saturation_hue hi to: 0x%x (raw=0x%x)" % (hi, packed))
					with open("%s/saturation_hue" % AMVECM, "w") as f:
						f.write("0x%x" % packed)
				except OSError:
					print("couldn't write saturation_hue.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.amvecm.hue = ConfigSlider(default=initial, limits=(0, SLIDER_MAX))
			config.amvecm.hue.addNotifier(setHue)
		else:
			config.amvecm.hue = NoSave(ConfigNothing())

		# --- brightness1: kernel -1024..1023, slider 0..255 (scale ~8) ---
		if exists("%s/brightness1" % AMVECM):
			initial = _kernelToSlider(_readInt("%s/brightness1" % AMVECM, 0), 8.0)

			def setBrightness1(configItem):
				kval = _sliderToKernel(int(configItem.value), 8.0, -1024, 1023)
				try:
					print("--> setting brightness1 (video) to: %d" % kval)
					with open("%s/brightness1" % AMVECM, "w") as f:
						f.write(str(kval))
				except OSError:
					print("couldn't write brightness1.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.amvecm.brightness1 = ConfigSlider(default=initial, limits=(0, SLIDER_MAX))
			config.amvecm.brightness1.addNotifier(setBrightness1)
		else:
			config.amvecm.brightness1 = NoSave(ConfigNothing())

		# --- brightness2: kernel -1024..1023, slider 0..255 (scale ~8) ---
		if exists("%s/brightness2" % AMVECM):
			initial = _kernelToSlider(_readInt("%s/brightness2" % AMVECM, 0), 8.0)

			def setBrightness2(configItem):
				kval = _sliderToKernel(int(configItem.value), 8.0, -1024, 1023)
				try:
					print("--> setting brightness2 (video+OSD) to: %d" % kval)
					with open("%s/brightness2" % AMVECM, "w") as f:
						f.write(str(kval))
				except OSError:
					print("couldn't write brightness2.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.amvecm.brightness2 = ConfigSlider(default=initial, limits=(0, SLIDER_MAX))
			config.amvecm.brightness2.addNotifier(setBrightness2)
		else:
			config.amvecm.brightness2 = NoSave(ConfigNothing())

		# --- color_top / color_bottom: 30-bit RGB clamp presets ---
		# (R << 20) | (G << 10) | B, each channel 10-bit (0..1023).
		# Full range (no clipping): top=0x3fffffff, bottom=0x0
		# Limited broadcast-safe (64..940): top=0x3aceb3ac, bottom=0x04010040
		COLOR_TOP_PRESETS = {
			"full": 0x3fffffff,
			"limited": 0x3aceb3ac,
		}
		COLOR_BOTTOM_PRESETS = {
			"full": 0x00000000,
			"limited": 0x04010040,
		}

		def _detectMode(raw, presets):
			for name, val in presets.items():
				if raw == val:
					return name
			return "full"

		COLOR_MODE_CHOICES = [
			("full", _("Full range (no clipping)")),
			("limited", _("Limited range (64..940)")),
		]

		if exists("%s/color_bottom" % AMVECM):
			initialRaw = _readInt("%s/color_bottom" % AMVECM, 0)
			initialMode = _detectMode(initialRaw, COLOR_BOTTOM_PRESETS)

			def setColor_bottom(configItem):
				mode = configItem.value
				val = COLOR_BOTTOM_PRESETS.get(mode)
				if val is None:
					return
				try:
					print("--> setting color_bottom to: 0x%08x (%s)" % (val, mode))
					with open("%s/color_bottom" % AMVECM, "w") as f:
						f.write("0x%x" % val)
				except OSError:
					print("couldn't write color_bottom.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.amvecm.color_bottom = ConfigSelection(choices=COLOR_MODE_CHOICES, default=initialMode)
			config.amvecm.color_bottom.addNotifier(setColor_bottom)
		else:
			config.amvecm.color_bottom = NoSave(ConfigNothing())

		if exists("%s/color_top" % AMVECM):
			initialRaw = _readInt("%s/color_top" % AMVECM, 0x3fffffff)
			initialMode = _detectMode(initialRaw, COLOR_TOP_PRESETS)

			def setColor_top(configItem):
				mode = configItem.value
				val = COLOR_TOP_PRESETS.get(mode)
				if val is None:
					return
				try:
					print("--> setting color_top to: 0x%08x (%s)" % (val, mode))
					with open("%s/color_top" % AMVECM, "w") as f:
						f.write("0x%x" % val)
				except OSError:
					print("couldn't write color_top.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.amvecm.color_top = ConfigSelection(choices=COLOR_MODE_CHOICES, default=initialMode)
			config.amvecm.color_top.addNotifier(setColor_top)
		else:
			config.amvecm.color_top = NoSave(ConfigNothing())

		if VideoEnhancement.firstRun:
			self.setConfiguredValues()

		VideoEnhancement.firstRun = False

	def setConfiguredValues(self):
		# amvecm has no global "apply" trigger; per-attribute writes take effect immediately.
		pass


VideoEnhancement()
