from Components.config import config, ConfigSubsection, ConfigSlider, ConfigSelection, ConfigNothing, NoSave
from Tools.CList import CList
from os import path as os_path
# The "VideoEnhancement" is the interface to /proc/stb/vmpeg/0.

class VideoEnhancement:
	firstRun = True

	def __init__(self):
		self.last_modes_preferred =  [ ]
		self.createConfig()

	def createConfig(self, *args):
		config.pep = ConfigSubsection()
		config.pep.configsteps = NoSave(ConfigSelection(choices=[1, 5, 10, 25], default = 1))

		if os_path.exists("/proc/stb/vmpeg/0/pep_contrast"):
			def setContrast(config):
				myval = int(config.value*256)
				try:
					print "--> setting contrast to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_contrast", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_contrast."

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.pep.contrast = ConfigSlider(default=128, limits=(0,256))
			config.pep.contrast.addNotifier(setContrast)
		else:
			config.pep.contrast = NoSave(ConfigNothing())

		if os_path.exists("/proc/stb/vmpeg/0/pep_saturation"):
			def setSaturation(config):
				myval = int(config.value*256)
				try:
					print "--> setting saturation to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_saturation", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_saturaion."

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.pep.saturation = ConfigSlider(default=128, limits=(0,256))
			config.pep.saturation.addNotifier(setSaturation)
		else:
			config.pep.saturation = NoSave(ConfigNothing())

		if os_path.exists("/proc/stb/vmpeg/0/pep_hue"):
			def setHue(config):
				myval = int(config.value*256)
				try:
					print "--> setting hue to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_hue", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_hue."

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.pep.hue = ConfigSlider(default=128, limits=(0,256))
			config.pep.hue.addNotifier(setHue)
		else:
			config.pep.hue = NoSave(ConfigNothing())

		if os_path.exists("/proc/stb/vmpeg/0/pep_brightness"):
			def setBrightness(config):
				myval = int(config.value*256)
				try:
					print "--> setting brightness to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_brightness", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_brightness."

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.pep.brightness = ConfigSlider(default=128, limits=(0,256))
			config.pep.brightness.addNotifier(setBrightness)
		else:
			config.pep.brightness = NoSave(ConfigNothing())

		if os_path.exists("/proc/stb/vmpeg/0/pep_block_noise_reduction"):
			def setBlock_noise_reduction(config):
				myval = int(config.value)
				try:
					print "--> setting block_noise_reduction to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_block_noise_reduction", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_block_noise_reduction."

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.pep.block_noise_reduction = ConfigSlider(default=0, limits=(0,5))
			config.pep.block_noise_reduction.addNotifier(setBlock_noise_reduction)
		else:
			config.pep.block_noise_reduction = NoSave(ConfigNothing())

		if os_path.exists("/proc/stb/vmpeg/0/pep_mosquito_noise_reduction"):
			def setMosquito_noise_reduction(config):
				myval = int(config.value)
				try:
					print "--> setting mosquito_noise_reduction to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_mosquito_noise_reduction", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_mosquito_noise_reduction."

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.pep.mosquito_noise_reduction = ConfigSlider(default=0, limits=(0,5))
			config.pep.mosquito_noise_reduction.addNotifier(setMosquito_noise_reduction)
		else:
			config.pep.mosquito_noise_reduction = NoSave(ConfigNothing())

		if os_path.exists("/proc/stb/vmpeg/0/pep_digital_contour_removal"):
			def setDigital_contour_removal(config):
				myval = int(config.value)
				try:
					print "--> setting digital_contour_removal to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_digital_contour_removal", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_digital_contour_removal."

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.pep.digital_contour_removal = ConfigSlider(default=0, limits=(0,5))
			config.pep.digital_contour_removal.addNotifier(setDigital_contour_removal)
		else:
			config.pep.digital_contour_removal = NoSave(ConfigNothing())

		if os_path.exists("/proc/stb/vmpeg/0/pep_split"):
			def setSplitMode(config):
				try:
					print "--> setting splitmode to:",str(config.value)
					open("/proc/stb/vmpeg/0/pep_split", "w").write(str(config.value))
				except IOError:
					print "couldn't write pep_split."

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.pep.split = ConfigSelection(choices={
					"off": _("Off"),
					"left": _("Left"),
					"right": _("Right")},
					default = "off")
			config.pep.split.addNotifier(setSplitMode)
		else:
			config.pep.split = NoSave(ConfigNothing())

		if os_path.exists("/proc/stb/vmpeg/0/pep_sharpness"):
			def setSharpness(config):
				myval = int(config.value*256)
				try:
					print "--> setting sharpness to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_sharpness", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_sharpness."

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.pep.sharpness = ConfigSlider(default=0, limits=(0,256))
			config.pep.sharpness.addNotifier(setSharpness)
		else:
			config.pep.sharpness = NoSave(ConfigNothing())

		if os_path.exists("/proc/stb/vmpeg/0/pep_auto_flesh"):
			def setAutoflesh(config):
				myval = int(config.value)
				try:
					print "--> setting auto_flesh to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_auto_flesh", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_auto_flesh."

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.pep.auto_flesh = ConfigSlider(default=0, limits=(0,4))
			config.pep.auto_flesh.addNotifier(setAutoflesh)
		else:
			config.pep.auto_flesh = NoSave(ConfigNothing())

		if os_path.exists("/proc/stb/vmpeg/0/pep_green_boost"):
			def setGreenboost(config):
				myval = int(config.value)
				try:
					print "--> setting green_boost to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_green_boost", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_green_boost."

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.pep.green_boost = ConfigSlider(default=0, limits=(0,4))
			config.pep.green_boost.addNotifier(setGreenboost)
		else:
			config.pep.green_boost = NoSave(ConfigNothing())

		if os_path.exists("/proc/stb/vmpeg/0/pep_blue_boost"):
			def setBlueboost(config):
				myval = int(config.value)
				try:
					print "--> setting blue_boost to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_blue_boost", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_blue_boost."

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.pep.blue_boost = ConfigSlider(default=0, limits=(0,4))
			config.pep.blue_boost.addNotifier(setBlueboost)
		else:
			config.pep.blue_boost = NoSave(ConfigNothing())

		if os_path.exists("/proc/stb/vmpeg/0/pep_dynamic_contrast"):
			def setDynamic_contrast(config):
				myval = int(config.value)
				try:
					print "--> setting dynamic_contrast to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_dynamic_contrast", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_dynamic_contrast."

				if not VideoEnhancement.firstRun:
					self.setConfiguredValues()

			config.pep.dynamic_contrast = ConfigSlider(default=0, limits=(0,256))
			config.pep.dynamic_contrast.addNotifier(setDynamic_contrast)
		else:
			config.pep.dynamic_contrast = NoSave(ConfigNothing())

		try:
			x = config.av.scaler_sharpness.value
		except KeyError:
			if os_path.exists("/proc/stb/vmpeg/0/pep_scaler_sharpness"):
				def setScaler_sharpness(config):
					myval = int(config.value)
					try:
						print "--> setting scaler_sharpness to: %0.8X" % myval
						open("/proc/stb/vmpeg/0/pep_scaler_sharpness", "w").write("%0.8X" % myval)
					except IOError:
						print "couldn't write pep_scaler_sharpness."

					if not VideoEnhancement.firstRun:
						self.setConfiguredValues()

				config.av.scaler_sharpness = ConfigSlider(default=13, limits=(0,26))
				config.av.scaler_sharpness.addNotifier(setScaler_sharpness)
			else:
				config.av.scaler_sharpness = NoSave(ConfigNothing())

		if VideoEnhancement.firstRun:
			self.setConfiguredValues()

		VideoEnhancement.firstRun = False

	def setConfiguredValues(self):
		try:
			print "--> applying pep values"
			open("/proc/stb/vmpeg/0/pep_apply", "w").write("1")
		except IOError:
			print "couldn't apply pep values."

VideoEnhancement()
