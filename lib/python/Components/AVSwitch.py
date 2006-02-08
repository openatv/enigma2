from config import *
import os
from enigma import *

class AVSwitch:
	INPUT = { "ENCODER": (0, 4), "SCART": (1, 3), "AUX": (2, 4) }

	def setInput(self, input):
		eAVSwitch.getInstance().setInput(self.INPUT[input][0])
		if self.INPUT[input][1] == 4:
			aspect = self.getAspectRatioSetting()
			self.setWSS(aspect)
			self.setSlowBlank(aspect)
		else:
			eAVSwitch.getInstance().setSlowblank(self.INPUT[input][1])
		# FIXME why do we have to reset the colorformat? bug in avs-driver?
		eAVSwitch.getInstance().setColorFormat(config.av.colorformat.value)

	def setColorFormat(self, value):
		eAVSwitch.getInstance().setColorFormat(value)

	def setAspectRatio(self, value):
		eAVSwitch.getInstance().setAspectRatio(value)
		self.setWSS(value)
		self.setSlowBlank(value)

	def setSystem(self, value):
		eAVSwitch.getInstance().setVideomode(value)

	def getAspectRatioSetting(self):
		valstr = currentConfigSelectionElement(config.av.aspectratio)
		if valstr == "4_3_letterbox":
			val = 0
		elif valstr == "4_3_panscan":
			val = 1
		elif valstr == "16_9":
			val = 2
		elif valstr == "16_9_always":
			val = 3
		return val

	def setWSS(self, aspect=None):
		if aspect is None:
			aspect = self.getAspectRatioSetting()
		if aspect == 0 or aspect == 1: # letterbox or panscan
			value = 3 # 4:3_full_format
		elif aspect == 2: # 16:9
			if currentConfigSelectionElement(config.av.wss) == "off":
				value = 2 # auto(4:3_off)
			else:
				value = 1 # auto
		elif aspect == 3: # always 16:9
			value = 4 # 16:9_full_format
		eAVSwitch.getInstance().setWSS(value)

	def setSlowBlank(self, aspect=None):
		if aspect is None:
			aspect = self.getAspectRatioSetting()
		if aspect == 0 or aspect == 1: # letterbox or panscan
			value = 2 # 12 V
		elif aspect == 2: # 16:9
			value = 4 # auto
		elif aspect == 3: # always 16:9
			value = 1 # 6V
		eAVSwitch.getInstance().setSlowblank(value)

def InitAVSwitch():
	config.av = ConfigSubsection();
	config.av.colorformat = configElement("config.av.colorformat", configSelection, 1, (("cvbs", _("CVBS")), ("rgb", _("RGB")), ("svideo", _("S-Video")) ))
	config.av.aspectratio = configElement("config.av.aspectratio", configSelection, 0, (("4_3_letterbox", _("4:3 Letterbox")), ("4_3_panscan", _("4:3 PanScan")), ("16_9", _("16:9")), ("16_9_always", _("16:9 always"))) )
	#config.av.tvsystem = configElement("config.av.tvsystem", configSelection, 0, ("PAL", "PAL + PAL60", "Multi", "NTSC") )
	config.av.tvsystem = configElement("config.av.tvsystem", configSelection, 0, (("pal", _("PAL")), ("ntsc", _("NTSC"))) )
	config.av.wss = configElement("config.av.wss", configSelection, 0, (("off", _("Off")), ("on", _("On"))) )
	config.av.defaultac3 = configElement("config.av.defaultac3", configSelection, 1, (("enable", _("Enable")), ("disable", _("Disable"))))
	config.av.vcrswitch = configElement("config.av.vcrswitch", configSelection, 1, (("enable", _("Enable")), ("disable", _("Disable"))))

	iAVSwitch = AVSwitch()

	def setColorFormat(configElement):
		iAVSwitch.setColorFormat(configElement.value)

	def setAspectRatio(configElement):
		iAVSwitch.setAspectRatio(configElement.value)

	def setSystem(configElement):
		iAVSwitch.setSystem(configElement.value)

	def setWSS(configElement):
		iAVSwitch.setWSS(configElement.value)

	# this will call the "setup-val" initial
	config.av.colorformat.addNotifier(setColorFormat)
	config.av.aspectratio.addNotifier(setAspectRatio)
	config.av.tvsystem.addNotifier(setSystem)
	config.av.wss.addNotifier(setWSS)

	iAVSwitch.setInput("ENCODER") # init on startup