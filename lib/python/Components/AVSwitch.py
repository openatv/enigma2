from config import config, ConfigSelection, ConfigYesNo, ConfigEnableDisable, ConfigSubsection, ConfigBoolean
import os
from enigma import *

class AVSwitch:
	INPUT = { "ENCODER": (0, 4), "SCART": (1, 3), "AUX": (2, 4) }

	def setInput(self, input):
		eAVSwitch.getInstance().setInput(self.INPUT[input][0])
		if self.INPUT[input][1] == 4:
			aspect = self.getAspectRatioSetting()
			self.setAspectWSS(aspect)
			self.setAspectSlowBlank(aspect)
		else:
			eAVSwitch.getInstance().setSlowblank(self.INPUT[input][1])
		# FIXME why do we have to reset the colorformat? bug in avs-driver?
		map = {"cvbs": 0, "rgb": 1, "svideo": 2, "yuv": 3}
		eAVSwitch.getInstance().setColorFormat(map[config.av.colorformat.value])

	def setColorFormat(self, value):
		eAVSwitch.getInstance().setColorFormat(value)

	def setAspectRatio(self, value):
		eAVSwitch.getInstance().setAspectRatio(value)
		self.setAspectWSS(value)
		self.setAspectSlowBlank(value)

	def setSystem(self, value):
		eAVSwitch.getInstance().setVideomode(value)

	def getAspectRatioSetting(self):
		valstr = config.av.aspectratio.value
		if valstr == "4_3_letterbox":
			val = 0
		elif valstr == "4_3_panscan":
			val = 1
		elif valstr == "16_9":
			val = 2
		elif valstr == "16_9_always":
			val = 3
		elif valstr == "16_10_letterbox":
			val = 4
		elif valstr == "16_10_panscan":
			val = 5
		return val

	def setAspectWSS(self, aspect=None):
		if aspect is None:
			aspect = self.getAspectRatioSetting()
		if aspect == 0 or aspect == 1: # letterbox or panscan
			value = 3 # 4:3_full_format
		elif aspect == 2: # 16:9
			if not config.av.wss.value:
				value = 2 # auto(4:3_off)
			else:
				value = 1 # auto
		elif aspect == 3: # always 16:9
			value = 4 # 16:9_full_format
		elif aspect == 4 or aspect == 5: # 16:10
			value = 10 # 14:9_full_format
		eAVSwitch.getInstance().setWSS(value)

	def setAspectSlowBlank(self, aspect=None):
		if aspect is None:
			aspect = self.getAspectRatioSetting()
		if aspect == 0 or aspect == 1: # letterbox or panscan
			value = 2 # 12 V
		elif aspect == 2: # 16:9
			value = 4 # auto
		elif aspect == 3 or aspect == 4 or aspect == 5: # always 16:9
			value = 1 # 6V
		eAVSwitch.getInstance().setSlowblank(value)

def InitAVSwitch():
	config.av = ConfigSubsection()
	config.av.yuvenabled = ConfigBoolean(default=False)
	colorformat_choices = {"cvbs": _("CVBS"), "rgb": _("RGB"), "svideo": _("S-Video")}
	
	# when YUV is not enabled, don't let the user select it
	if config.av.yuvenabled.value:
		colorformat_choices["yuv"] = _("YPbPr")

	config.av.colorformat = ConfigSelection(choices=colorformat_choices, default="rgb")
	config.av.aspectratio = ConfigSelection(choices={
			"4_3_letterbox": _("4:3 Letterbox"),
			"4_3_panscan": _("4:3 PanScan"), 
			"16_9": _("16:9"), 
			"16_9_always": _("16:9 always"),
			"16_10_letterbox": _("16:10 Letterbox"),
			"16_10_panscan": _("16:10 PanScan")}, 
			default = "4_3_letterbox")
	config.av.tvsystem = ConfigSelection(choices = {"pal": _("PAL"), "ntsc": _("NTSC"), "multinorm": _("multinorm")}, default="pal")
	config.av.wss = ConfigEnableDisable(default = True)
	config.av.defaultac3 = ConfigYesNo(default = False)
	config.av.vcrswitch = ConfigEnableDisable(default = False)

	iAVSwitch = AVSwitch()

	def setColorFormat(configElement):
		map = {"cvbs": 0, "rgb": 1, "svideo": 2, "yuv": 3}
		iAVSwitch.setColorFormat(map[configElement.value])

	def setAspectRatio(configElement):
		map = {"4_3_letterbox": 0, "4_3_panscan": 1, "16_9": 2, "16_9_always": 3, "16_10_letterbox": 4, "16_10_panscan": 5}
		iAVSwitch.setAspectRatio(map[configElement.value])

	def setSystem(configElement):
		map = {"pal": 0, "ntsc": 1, "multinorm" : 2}
		iAVSwitch.setSystem(map[configElement.value])

	def setWSS(configElement):
		iAVSwitch.setAspectWSS()

	# this will call the "setup-val" initial
	config.av.colorformat.addNotifier(setColorFormat)
	config.av.aspectratio.addNotifier(setAspectRatio)
	config.av.tvsystem.addNotifier(setSystem)
	config.av.wss.addNotifier(setWSS)

	iAVSwitch.setInput("ENCODER") # init on startup
