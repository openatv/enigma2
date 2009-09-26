from enigma import eTimer
from Components.config import config, ConfigSubsection, ConfigSlider, ConfigSelection, ConfigYesNo, NoSave
from Tools.CList import CList
from Tools.HardwareInfo import HardwareInfo
import os
# The "VideoEnhancement" is the interface to /proc/stb/vmpeg/0.

class VideoEnhancement:

	firstRun = None

	def __init__(self):
		self.last_modes_preferred =  [ ]
		self.on_hotplug = CList()
		self.createConfig()

	def createConfig(self, *args):
		hw_type = HardwareInfo().get_device_name()
		config.pep = ConfigSubsection()

		config.pep.configsteps = NoSave(ConfigSelection(choices=[1, 5, 10, 25], default = 1))

		def setContrast(config):
			myval = int(config.value*256)
			try:
				print "--> setting contrast to: %0.8X" % myval
				open("/proc/stb/vmpeg/0/pep_contrast", "w").write("%0.8X" % myval)
			except IOError:
				print "couldn't write pep_contrast."

			if VideoEnhancement.firstRun is False:
				self.setConfiguredValues()

		config.pep.contrast = ConfigSlider(default=128, limits=(0,256))
		config.pep.contrast.addNotifier(setContrast)

		def setSaturation(config):
			myval = int(config.value*256)
			try:
				print "--> setting saturation to: %0.8X" % myval
				open("/proc/stb/vmpeg/0/pep_saturation", "w").write("%0.8X" % myval)
			except IOError:
				print "couldn't write pep_saturaion."

			if VideoEnhancement.firstRun is False:
				self.setConfiguredValues()

		config.pep.saturation = ConfigSlider(default=128, limits=(0,256))
		config.pep.saturation.addNotifier(setSaturation)

		def setHue(config):
			myval = int(config.value*256)
			try:
				print "--> setting hue to: %0.8X" % myval
				open("/proc/stb/vmpeg/0/pep_hue", "w").write("%0.8X" % myval)
			except IOError:
				print "couldn't write pep_hue."

			if VideoEnhancement.firstRun is False:
				self.setConfiguredValues()

		config.pep.hue = ConfigSlider(default=128, limits=(0,256))
		config.pep.hue.addNotifier(setHue)

		def setBrightness(config):
			myval = int(config.value*256)
			try:
				print "--> setting brightness to: %0.8X" % myval
				open("/proc/stb/vmpeg/0/pep_brightness", "w").write("%0.8X" % myval)
			except IOError:
				print "couldn't write pep_brightness."

			if VideoEnhancement.firstRun is False:
				self.setConfiguredValues()

		config.pep.brightness = ConfigSlider(default=128, limits=(0,256))
		config.pep.brightness.addNotifier(setBrightness)

		def setBlock_noise_reduction(config):
			myval = int(config.value)
			try:
				print "--> setting block_noise_reduction to: %0.8X" % myval
				open("/proc/stb/vmpeg/0/pep_block_noise_reduction", "w").write("%0.8X" % myval)
			except IOError:
				print "couldn't write pep_block_noise_reduction."

			if VideoEnhancement.firstRun is False:
				self.setConfiguredValues()

		config.pep.block_noise_reduction = ConfigSlider(default=0, limits=(0,5))
		config.pep.block_noise_reduction.addNotifier(setBlock_noise_reduction)

		def setMosquito_noise_reduction(config):
			myval = int(config.value)
			try:
				print "--> setting mosquito_noise_reduction to: %0.8X" % myval
				open("/proc/stb/vmpeg/0/pep_mosquito_noise_reduction", "w").write("%0.8X" % myval)
			except IOError:
				print "couldn't write pep_mosquito_noise_reduction."

			if VideoEnhancement.firstRun is False:
				self.setConfiguredValues()

		config.pep.mosquito_noise_reduction = ConfigSlider(default=0, limits=(0,5))
		config.pep.mosquito_noise_reduction.addNotifier(setMosquito_noise_reduction)

		def setDigital_contour_removal(config):
			myval = int(config.value)
			try:
				print "--> setting digital_contour_removal to: %0.8X" % myval
				open("/proc/stb/vmpeg/0/pep_digital_contour_removal", "w").write("%0.8X" % myval)
			except IOError:
				print "couldn't write pep_digital_contour_removal."

			if VideoEnhancement.firstRun is False:
				self.setConfiguredValues()

		config.pep.digital_contour_removal = ConfigSlider(default=0, limits=(0,5))
		config.pep.digital_contour_removal.addNotifier(setDigital_contour_removal)

		if hw_type in ( 'dm8000', 'dm500hd' ):
			def setSplitMode(config):
				try:
					print "--> setting splitmode to:",str(config.value)
					open("/proc/stb/vmpeg/0/pep_split", "w").write(str(config.value))
				except IOError:
					print "couldn't write pep_split."

				if VideoEnhancement.firstRun is False:
					self.setConfiguredValues()

			config.pep.split = ConfigSelection(choices={
					"off": _("Off"),
					"left": _("Left"),
					"right": _("Right")},
					default = "off")
			config.pep.split.addNotifier(setSplitMode)

			def setSharpness(config):
				myval = int(config.value*256)
				try:
					print "--> setting sharpness to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_sharpness", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_sharpness."

				if VideoEnhancement.firstRun is False:
					self.setConfiguredValues()

			config.pep.sharpness = ConfigSlider(default=0, limits=(0,256))
			config.pep.sharpness.addNotifier(setSharpness)

			def setAutoflesh(config):
				myval = int(config.value)
				try:
					print "--> setting auto_flesh to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_auto_flesh", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_auto_flesh."

				if VideoEnhancement.firstRun is False:
					self.setConfiguredValues()

			config.pep.auto_flesh = ConfigSlider(default=0, limits=(0,4))
			config.pep.auto_flesh.addNotifier(setAutoflesh)

			def setGreenboost(config):
				myval = int(config.value)
				try:
					print "--> setting green_boost to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_green_boost", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_green_boost."

				if VideoEnhancement.firstRun is False:
					self.setConfiguredValues()

			config.pep.green_boost = ConfigSlider(default=0, limits=(0,4))
			config.pep.green_boost.addNotifier(setGreenboost)

			def setBlueboost(config):
				myval = int(config.value)
				try:
					print "--> setting blue_boost to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_blue_boost", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_blue_boost."

				if VideoEnhancement.firstRun is False:
					self.setConfiguredValues()

			config.pep.blue_boost = ConfigSlider(default=0, limits=(0,4))
			config.pep.blue_boost.addNotifier(setBlueboost)

			def setDynamic_contrast(config):
				myval = int(config.value)
				try:
					print "--> setting dynamic_contrast to: %0.8X" % myval
					open("/proc/stb/vmpeg/0/pep_dynamic_contrast", "w").write("%0.8X" % myval)
				except IOError:
					print "couldn't write pep_dynamic_contrast."

				if VideoEnhancement.firstRun is False:
					self.setConfiguredValues()

			config.pep.dynamic_contrast = ConfigSlider(default=0, limits=(0,256))
			config.pep.dynamic_contrast.addNotifier(setDynamic_contrast)

		VideoEnhancement.firstRun = True

	def setConfiguredValues(self):
		try:
			print "--> applying pep values"
			open("/proc/stb/vmpeg/0/pep_apply", "w").write("1")
			VideoEnhancement.firstRun = False
		except IOError:
			print "couldn't apply pep values."


if config.usage.setup_level.index >= 2: # expert+
	hw_type = HardwareInfo().get_device_name()
	if hw_type in ( 'dm8000', 'dm800', 'dm500hd' ):
		video_enhancement = VideoEnhancement()
		if video_enhancement.firstRun == True:
			video_enhancement.setConfiguredValues()
