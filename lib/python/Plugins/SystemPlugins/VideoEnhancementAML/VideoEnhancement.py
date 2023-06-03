from os.path import exists
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSlider, ConfigSelection, ConfigNothing, NoSave

# The "VideoEnhancement" is the interface to /sys/class/amvecm.


class VideoEnhancement:
	firstRun = True

	def __init__(self):
		self.last_modes_preferred = []
		self.createConfig()

	def createConfig(self):
		config.amvecm = ConfigSubsection()
		config.amvecm.configsteps = NoSave(ConfigSelection(choices=[1, 5, 10, 25], default=1))

		if exists("/sys/class/amvecm/contrast1"):
			def setContrast1(configItem):
				myval = str(configItem.value)
				try:
					print("--> setting video contrast to:%s" % myval)
					f = open("/sys/class/amvecm/contrast1", "w")
					f.write(myval)
					f.close()
				except OSError:
					print("couldn't write video contrast.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.amvecm.contrast1 = ConfigSlider(default=0, limits=(-1022, 1022))
			config.amvecm.contrast1.addNotifier(setContrast1)
		else:
			config.amvecm.contrast1 = NoSave(ConfigNothing())

		if exists("/sys/class/amvecm/contrast2"):
			def setContrast2(configItem):
				myval = str(configItem.value)
				try:
					print("--> setting video & OSD contrast to:%s" % myval)
					f = open("/sys/class/amvecm/contrast2", "w")
					f.write(myval)
					f.close()
				except OSError:
					print("couldn't write video & OSD contrast.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.amvecm.contrast2 = ConfigSlider(default=0, limits=(-1022, 1022))
			config.amvecm.contrast2.addNotifier(setContrast2)
		else:
			config.amvecm.contrast2 = NoSave(ConfigNothing())

		if exists("/sys/class/amvecm/saturation_hue_post"):
			def setSaturation(configItem):
				myval = str(configItem.value)
				try:
					print("--> setting saturation to: %s" % myval)
					f = open("/sys/class/amvecm/saturation_hue_post", "w")
					f.write("%s 0" % myval)
					f.close()
				except OSError:
					print("couldn't write saturaion.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.amvecm.saturation = ConfigSlider(default=0, limits=(-127, 127))
			config.amvecm.saturation.addNotifier(setSaturation)
		else:
			config.amvecm.saturation = NoSave(ConfigNothing())

		if exists("/sys/class/amvecm/saturation_hue"):
			def setHue(configItem):
				myval = int(configItem.value)
				try:
					print("--> setting hue to: %s" % myval)
					f = open("/sys/class/amvecm/saturation_hue", "w")
					f.write("%s0000" % hex(myval))
					f.close()
				except OSError:
					print("couldn't write hue.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.amvecm.hue = ConfigSlider(default=256, limits=(-1022, 1022))
			config.amvecm.hue.addNotifier(setHue)
		else:
			config.amvecm.hue = NoSave(ConfigNothing())

		if exists("/sys/class/amvecm/brightness1"):
			def setBrightness1(configItem):
				myval = str(configItem.value)
				try:
					print("--> setting brightness Video to: %s" % myval)
					f = open("/sys/class/amvecm/brightness1", "w")
					f.write(myval)
					f.close()
				except OSError:
					print("couldn't write brightness1.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()
			config.amvecm.brightness1 = ConfigSlider(default=0, limits=(-1022, 1022))
			config.amvecm.brightness1.addNotifier(setBrightness1)
		else:
			config.amvecm.brightness1 = NoSave(ConfigNothing())

		if exists("/sys/class/amvecm/brightness2"):
			def setBrightness2(configItem):
				myval = str(configItem.value)
				try:
					print("--> setting brightness Video & OSD to: %s" % myval)
					f = open("/sys/class/amvecm/brightness2", "w")
					f.write(myval)
					f.close()
				except OSError:
					print("couldn't write brightness2.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()
			config.amvecm.brightness2 = ConfigSlider(default=0, limits=(-1022, 1022))
			config.amvecm.brightness2.addNotifier(setBrightness2)
		else:
			config.amvecm.brightness2 = NoSave(ConfigNothing())

		if exists("/sys/class/amvecm/color_bottom"):
			def setColor_bottom(configItem):
				myval = int(configItem.value)
				try:
					print("--> setting color button to: %s" % myval)
					f = open("/sys/class/amvecm/color_bottom", "w")
					f.write("%s" % hex(myval))
					f.close()
				except OSError:
					print("couldn't write color button.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.amvecm.color_bottom = ConfigInteger(default=0, limits=(0, 268435454))
			config.amvecm.color_bottom.addNotifier(setColor_bottom)
		else:
			config.amvecm.color_bottom = NoSave(ConfigNothing())

		if exists("/sys/class/amvecm/color_top"):
			def setColor_top(configItem):
				myval = int(configItem.value)
				try:
					print("--> setting color top to: %s" % myval)
					f = open("/sys/class/amvecm/color_top", "w")
					f.write("%s" % hex(myval))
					f.close()
				except OSError:
					print("couldn't write color top.")

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.amvecm.color_top = ConfigInteger(default=1073741823, limits=(0, 268435454))
			config.amvecm.color_top.addNotifier(setColor_top)
		else:
			config.amvecm.color_top = NoSave(ConfigNothing())

		if VideoEnhancement.firstRun:
			self.setConfiguredValues()

		VideoEnhancement.firstRun = False

	def setConfiguredValues(self):
		# TODO is there something missing?
		pass


VideoEnhancement()
