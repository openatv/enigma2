from config import config, ConfigSlider, ConfigSelection, ConfigYesNo, \
	ConfigEnableDisable, ConfigSubsection, ConfigBoolean, ConfigSelectionNumber, ConfigNothing, NoSave
from enigma import eAVSwitch, getDesktop
from SystemInfo import SystemInfo
import os

class AVSwitch:
	def setInput(self, input):
		INPUT = { "ENCODER": 0, "SCART": 1, "AUX": 2 }
		eAVSwitch.getInstance().setInput(INPUT[input])

	def setColorFormat(self, value):
		eAVSwitch.getInstance().setColorFormat(value)

	def setAspectRatio(self, value):
		eAVSwitch.getInstance().setAspectRatio(value)

	def setSystem(self, value):
		eAVSwitch.getInstance().setVideomode(value)

	def getOutputAspect(self):
		valstr = config.av.aspectratio.value
		if valstr in ("4_3_letterbox", "4_3_panscan"): # 4:3
			return (4,3)
		elif valstr == "16_9": # auto ... 4:3 or 16:9
			try:
				aspect_str = open("/proc/stb/vmpeg/0/aspect", "r").read()
				if aspect_str == "1": # 4:3
					return (4,3)
			except IOError:
				pass
		elif valstr in ("16_9_always", "16_9_letterbox"): # 16:9
			pass
		elif valstr in ("16_10_letterbox", "16_10_panscan"): # 16:10
			return (16,10)
		return (16,9)

	def getFramebufferScale(self):
		aspect = self.getOutputAspect()
		fb_size = getDesktop(0).size()
		return (aspect[0] * fb_size.height(), aspect[1] * fb_size.width())

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
		elif valstr == "16_9_letterbox":
			val = 6
		return val

	def setAspectWSS(self, aspect=None):
		if not config.av.wss.value:
			value = 2 # auto(4:3_off)
		else:
			value = 1 # auto
		eAVSwitch.getInstance().setWSS(value)

def InitAVSwitch():
	config.av = ConfigSubsection()
	config.av.yuvenabled = ConfigBoolean(default=True)
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
			"16_10_panscan": _("16:10 PanScan"), 
			"16_9_letterbox": _("16:9 Letterbox")}, 
			default = "16_9")
	config.av.aspect = ConfigSelection(choices={
			"4_3": _("4:3"),
			"16_9": _("16:9"), 
			"16_10": _("16:10"),
			"auto": _("Automatic")},
			default = "auto")
	policy2_choices = {
	# TRANSLATORS: (aspect ratio policy: black bars on top/bottom) in doubt, keep english term.
	"letterbox": _("Letterbox"),
	# TRANSLATORS: (aspect ratio policy: cropped content on left/right) in doubt, keep english term
	"panscan": _("Pan&Scan"),
	# TRANSLATORS: (aspect ratio policy: display as fullscreen, even if this breaks the aspect)
	"scale": _("Just Scale")}
	if os.path.exists("/proc/stb/video/policy2_choices") and "auto" in open("/proc/stb/video/policy2_choices").readline():
		# TRANSLATORS: (aspect ratio policy: always try to display as fullscreen, when there is no content (black bars) on left/right, even if this breaks the aspect.
		policy2_choices.update({"auto": _("Auto")})
	config.av.policy_169 = ConfigSelection(choices=policy2_choices, default = "letterbox")
	policy_choices = {
	# TRANSLATORS: (aspect ratio policy: black bars on left/right) in doubt, keep english term.
	"pillarbox": _("Pillarbox"),
	# TRANSLATORS: (aspect ratio policy: cropped content on left/right) in doubt, keep english term
	"panscan": _("Pan&Scan"),
	# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching the left/right)
	"nonlinear": _("Nonlinear"),
	# TRANSLATORS: (aspect ratio policy: display as fullscreen, even if this breaks the aspect)
	"scale": _("Just Scale")}
	if os.path.exists("/proc/stb/video/policy_choices") and "auto" in open("/proc/stb/video/policy_choices").readline():
		# TRANSLATORS: (aspect ratio policy: always try to display as fullscreen, when there is no content (black bars) on left/right, even if this breaks the aspect.
		policy_choices.update({"auto": _("Auto")})
	config.av.policy_43 = ConfigSelection(choices=policy_choices, default = "pillarbox")
	config.av.tvsystem = ConfigSelection(choices = {"pal": _("PAL"), "ntsc": _("NTSC"), "multinorm": _("multinorm")}, default="pal")
	config.av.wss = ConfigEnableDisable(default = True)
	config.av.generalAC3delay = ConfigSelectionNumber(-1000, 1000, 5, default = 0)
	config.av.generalPCMdelay = ConfigSelectionNumber(-1000, 1000, 5, default = 0)
	config.av.vcrswitch = ConfigEnableDisable(default = False)

	iAVSwitch = AVSwitch()

	def setColorFormat(configElement):
		map = {"cvbs": 0, "rgb": 1, "svideo": 2, "yuv": 3}
		iAVSwitch.setColorFormat(map[configElement.value])

	def setAspectRatio(configElement):
		map = {"4_3_letterbox": 0, "4_3_panscan": 1, "16_9": 2, "16_9_always": 3, "16_10_letterbox": 4, "16_10_panscan": 5, "16_9_letterbox" : 6}
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
	SystemInfo["ScartSwitch"] = eAVSwitch.getInstance().haveScartSwitch()

	try:
		can_downmix = open("/proc/stb/audio/ac3_choices", "r").read()[:-1].find("downmix") != -1
	except:
		can_downmix = False

	SystemInfo["CanDownmixAC3"] = can_downmix
	if can_downmix:
		def setAC3Downmix(configElement):
			open("/proc/stb/audio/ac3", "w").write(configElement.value and "downmix" or "passthrough")
		config.av.downmix_ac3 = ConfigYesNo(default = True)
		config.av.downmix_ac3.addNotifier(setAC3Downmix)

	try:
		can_osd_alpha = open("/proc/stb/video/alpha", "r") and True or False
	except:
		can_osd_alpha = False

	SystemInfo["CanChangeOsdAlpha"] = can_osd_alpha

	def setAlpha(config):
		open("/proc/stb/video/alpha", "w").write(str(config.value))

	if can_osd_alpha:
		config.av.osd_alpha = ConfigSlider(default=255, limits=(0,255))
		config.av.osd_alpha.addNotifier(setAlpha)

	if os.path.exists("/proc/stb/vmpeg/0/pep_scaler_sharpness"):
		def setScaler_sharpness(config):
			myval = int(config.value)
			try:
				print "--> setting scaler_sharpness to: %0.8X" % myval
				open("/proc/stb/vmpeg/0/pep_scaler_sharpness", "w").write("%0.8X" % myval)
				open("/proc/stb/vmpeg/0/pep_apply", "w").write("1")
			except IOError:
				print "couldn't write pep_scaler_sharpness"

		config.av.scaler_sharpness = ConfigSlider(default=13, limits=(0,26))
		config.av.scaler_sharpness.addNotifier(setScaler_sharpness)
	else:
		config.av.scaler_sharpness = NoSave(ConfigNothing())

