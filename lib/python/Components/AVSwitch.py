from config import config, ConfigSlider, ConfigSelection, ConfigSubDict, ConfigYesNo, ConfigEnableDisable, ConfigSubsection, ConfigBoolean, ConfigSelectionNumber, ConfigNothing, NoSave
from Components.About import about
from Tools.CList import CList
from Tools.HardwareInfo import HardwareInfo
from enigma import eAVSwitch, getDesktop
from boxbranding import getBoxType, getBrandOEM
from SystemInfo import SystemInfo
import os

config.av = ConfigSubsection()

class AVSwitch:
	rates = { } # high-level, use selectable modes.
	modes = { }  # a list of (high-level) modes for a certain port.

	rates["PAL"]  = { "50Hz":  { 50: "pal" },
					  "60Hz":  { 60: "pal60" },
					  "multi": { 50: "pal", 60: "pal60" } }

	rates["NTSC"]  = { "60Hz": { 60: "ntsc" } }

	rates["Multi"] = { "multi": { 50: "pal", 60: "ntsc" } }

	rates["480i"] = { "60Hz": { 60: "480i" } }

	rates["576i"] = { "50Hz": { 50: "576i" } }

	rates["480p"] = { "60Hz": { 60: "480p" } }

	rates["576p"] = { "50Hz": { 50: "576p" } }

	rates["720p"] = { "50Hz": { 50: "720p50" },
					  "60Hz": { 60: "720p" },
					  "multi": { 50: "720p50", 60: "720p" } }

	rates["1080i"] = { "50Hz":  { 50: "1080i50" },
					   "60Hz":  { 60: "1080i" },
					   "multi": { 50: "1080i50", 60: "1080i" } }

	rates["1080p"] = { "50Hz":  { 50: "1080p50" },
					   "60Hz":  { 60: "1080p" },
					   "multi": { 50: "1080p50", 60: "1080p" } }

	rates["2160p"] = { "50Hz":  { 50: "2160p50" },
					   "60Hz":  { 60: "2160p" },
					   "multi": { 50: "2160p50", 60: "2160p" } }

	rates["PC"] = {
		"1024x768": { 60: "1024x768" }, # not possible on DM7025
		"800x600" : { 60: "800x600" },  # also not possible
		"720x480" : { 60: "720x480" },
		"720x576" : { 60: "720x576" },
		"1280x720": { 60: "1280x720" },
		"1280x720 multi": { 50: "1280x720_50", 60: "1280x720" },
		"1920x1080": { 60: "1920x1080"},
		"1920x1080 multi": { 50: "1920x1080", 60: "1920x1080_50" },
		"1280x1024" : { 60: "1280x1024"},
		"1366x768" : { 60: "1366x768"},
		"1366x768 multi" : { 50: "1366x768", 60: "1366x768_50" },
		"1280x768": { 60: "1280x768" },
		"640x480" : { 60: "640x480" }
	}

	modes["Scart"] = ["PAL", "NTSC", "Multi"]
	# modes["DVI-PC"] = ["PC"]

	if about.getChipSetString() in ('5272s', '7251', '7251s', '7252', '7252s', '7366', '7376', '7444s'):
		modes["HDMI"] = ["720p", "1080p", "2160p", "1080i", "576p", "576i", "480p", "480i"]
		widescreen_modes = {"720p", "1080p", "2160p", "1080i"}
	elif about.getChipSetString() in ('7241', '7356', '73565', '7358', '7362', '73625', '7424', '7425', '7552'):
		modes["HDMI"] = ["720p", "1080p", "1080i", "576p", "576i", "480p", "480i"]
		widescreen_modes = {"720p", "1080p", "1080i"}
	else:
		modes["HDMI"] = ["720p", "1080i", "576p", "576i", "480p", "480i"]
		widescreen_modes = {"720p", "1080i"}

	modes["YPbPr"] = modes["HDMI"]
	if getBrandOEM() == 'vuplus' and getBoxType() not in ('vusolo4k', 'vuultimo4k', 'vuuno4k'):
		modes["Scart-YPbPr"] = modes["HDMI"]

	# if "DVI-PC" in modes and not getModeList("DVI-PC"):
	# 	print "[VideoHardware] remove DVI-PC because of not existing modes"
	# 	del modes["DVI-PC"]

	# Machines that do not have component video (red, green and blue RCA sockets).
	no_YPbPr = (
		'dm500hd',
		'dm500hdv2',
		'dm800',
		'e3hd',
		'ebox7358',
		'eboxlumi',
		'ebox5100',
		'enfinity',
		'et4x00',
		'gbx1',
		'gbx3',
		'iqonios300hd',
		'ixusszero',
		'mbmicro',
		'mbtwinplus',
		'mutant11',
		'mutant51',
		'mutant500c',
		'mutant1200',
		'mutant1500',
		'odimm7',
		'optimussos1',
		'osmega',
		'osmini',
		'osminiplus',
		'sf128',
		'sf138',
		'sf4008',
		'tm2t',
		'tmnano',
		'tmnano2super',
		'tmnano3t',
		'tmnanose',
		'tmnanosecombo',
		'tmnanoseplus',
		'tmnanosem2',
		'tmnanosem2plus',
		'tmnanom3',
		'tmsingle',
		'tmtwin4k',
		'uniboxhd1',
		'vusolo2',
		'vusolo4k',
		'vuuno4k',
		'vuultimo4k',
		'xp1000'
	)

	# Machines that have composite video (yellow RCA socket) but do not have Scart.
	yellow_RCA_no_scart = (
		'gb800ueplus',
		'gbultraue',
		'mbmicro',
		'mbtwinplus',
		'mutant11',
		'mutant500c',
		'osmega',
		'osmini',
		'osminiplus',
		'sf138',
		'tmnano',
		'tmnanose',
		'tmnanosecombo',
		'tmnanosem2',
		'tmnanoseplus',
		'tmnanosem2plus',
		'tmnano2super',
		'tmnano3t',
		'xpeedlx3'
	)

	# Machines that have neither yellow RCA nor Scart sockets
	no_yellow_RCA__no_scart = (
		'et5x00',
		'et6x00',
		'gbquad',
		'gbx1',
		'gbx3',
		'ixussone',
		'mutant51',
		'mutant1500',
		'sf4008',
		'tmnano2t',
		'tmnanom3',
		'tmtwin4k',
		'vusolo4k',
		'vuuno4k',
		'vuultimo4k'
	)

	if "YPbPr" in modes and getBoxType() in no_YPbPr:
		del modes["YPbPr"]

	if "Scart" in modes and getBoxType() in yellow_RCA_no_scart:
		modes["RCA"] = modes["Scart"]
		del modes["Scart"]

	if "Scart" in modes and getBoxType() in no_yellow_RCA__no_scart:
		del modes["Scart"]

	def __init__(self):
		self.last_modes_preferred =  [ ]
		self.on_hotplug = CList()
		self.current_mode = None
		self.current_port = None

		self.readAvailableModes()

		self.createConfig()
		self.readPreferredModes()

	def readAvailableModes(self):
		try:
			f = open("/proc/stb/video/videomode_choices")
			modes = f.read()[:-1]
			f.close()
		except IOError:
			print "[VideoHardware] couldn't read available videomodes."
			modes = [ ]
			return modes
		return modes.split(' ')

	def readPreferredModes(self):
		try:
			f = open("/proc/stb/video/videomode_preferred")
			modes = f.read()[:-1]
			f.close()
			self.modes_preferred = modes.split(' ')
		except IOError:
			print "[VideoHardware] reading preferred modes failed, using all modes"
			self.modes_preferred = self.readAvailableModes()

		if self.modes_preferred != self.last_modes_preferred:
			self.last_modes_preferred = self.modes_preferred
			self.on_hotplug("HDMI") # must be HDMI

	# check if a high-level mode with a given rate is available.
	def isModeAvailable(self, port, mode, rate):
		rate = self.rates[mode][rate]
		for mode in rate.values():
			if mode not in self.readAvailableModes():
				return False
		return True

	def isWidescreenMode(self, port, mode):
		return mode in self.widescreen_modes

	def setMode(self, port, mode, rate, force = None):
		print "[VideoHardware] setMode - port: %s, mode: %s, rate: %s" % (port, mode, rate)

		# config.av.videoport.setValue(port)
		# we can ignore "port"
		self.current_mode = mode
		self.current_port = port
		modes = self.rates[mode][rate]

		mode_50 = modes.get(50)
		mode_60 = modes.get(60)
		if mode_50 is None or force == 60:
			mode_50 = mode_60
		if mode_60 is None or force == 50:
			mode_60 = mode_50

		if os.path.exists('/proc/stb/video/videomode_50hz') and getBoxType() not in ('gbquadplus', 'gb800solo', 'gb800se', 'gb800ue', 'gb800ueplus'):
			f = open("/proc/stb/video/videomode_50hz", "w")
			f.write(mode_50)
			f.close()
		if os.path.exists('/proc/stb/video/videomode_60hz') and getBoxType() not in ('gbquadplus', 'gb800solo', 'gb800se', 'gb800ue', 'gb800ueplus'):
			f = open("/proc/stb/video/videomode_60hz", "w")
			f.write(mode_60)
			f.close()
		try:
			set_mode = modes.get(int(rate[:2]))
		except: # not support 50Hz, 60Hz for 1080p
			set_mode = mode_50
		f = open("/proc/stb/video/videomode", "w")
		f.write(set_mode)
		f.close()
		map = {"cvbs": 0, "rgb": 1, "svideo": 2, "yuv": 3}
		self.setColorFormat(map[config.av.colorformat.value])

	def saveMode(self, port, mode, rate):
		config.av.videoport.setValue(port)
		config.av.videoport.save()
		if port in config.av.videomode:
			config.av.videomode[port].setValue(mode)
			config.av.videomode[port].save()
		if mode in config.av.videorate:
			config.av.videorate[mode].setValue(rate)
			config.av.videorate[mode].save()

	def isPortAvailable(self, port):
		# fixme
		return True

	def isPortUsed(self, port):
		if port == "HDMI":
			self.readPreferredModes()
			return len(self.modes_preferred) != 0
		else:
			return True

	def getPortList(self):
		return [port for port in self.modes if self.isPortAvailable(port)]

	# get a list with all modes, with all rates, for a given port.
	def getModeList(self, port):
		res = [ ]
		for mode in self.modes[port]:
			# list all rates which are completely valid
			rates = [rate for rate in self.rates[mode] if self.isModeAvailable(port, mode, rate)]

			# if at least one rate is ok, add this mode
			if len(rates):
				res.append( (mode, rates) )
		return res

	def createConfig(self, *args):
		hw_type = HardwareInfo().get_device_name()
		has_hdmi = HardwareInfo().has_hdmi()
		lst = []

		config.av.videomode = ConfigSubDict()
		config.av.videorate = ConfigSubDict()

		# create list of output ports
		portlist = self.getPortList()
		for port in portlist:
			descr = port
			if 'HDMI' in port:
				lst.insert(0, (port, descr))
			else:
				lst.append((port, descr))

			modes = self.getModeList(port)
			if len(modes):
				config.av.videomode[port] = ConfigSelection(choices = [mode for (mode, rates) in modes])
			for (mode, rates) in modes:
				config.av.videorate[mode] = ConfigSelection(choices = rates)
		config.av.videoport = ConfigSelection(choices = lst)

	def setInput(self, input):
		INPUT = { "ENCODER": 0, "SCART": 1, "AUX": 2 }
		eAVSwitch.getInstance().setInput(INPUT[input])

	def setColorFormat(self, value):
		if not self.current_port:
			self.current_port = config.av.videoport.value
		if self.current_port in ("YPbPr", "Scart-YPbPr"):
			eAVSwitch.getInstance().setColorFormat(3)
		elif self.current_port in ("RCA"):
			eAVSwitch.getInstance().setColorFormat(0)
		else:
			eAVSwitch.getInstance().setColorFormat(value)

	def setConfiguredMode(self):
		port = config.av.videoport.value
		if port not in config.av.videomode:
			print "[VideoHardware] current port not available, not setting videomode"
			return

		mode = config.av.videomode[port].value

		if mode not in config.av.videorate:
			print "[VideoHardware] current mode not available, not setting videomode"
			return

		rate = config.av.videorate[mode].value
		self.setMode(port, mode, rate)

	def setAspect(self, cfgelement):
		print "[VideoHardware] setting aspect: %s" % cfgelement.value
		f = open("/proc/stb/video/aspect", "w")
		f.write(cfgelement.value)
		f.close()

	def setWss(self, cfgelement):
		if not cfgelement.value:
			wss = "auto(4:3_off)"
		else:
			wss = "auto"
		print "[VideoHardware] setting wss: %s" % wss
		f = open("/proc/stb/denc/0/wss", "w")
		f.write(wss)
		f.close()

	def setPolicy43(self, cfgelement):
		print "[VideoHardware] setting policy: %s" % cfgelement.value
		f = open("/proc/stb/video/policy", "w")
		f.write(cfgelement.value)
		f.close()

	def setPolicy169(self, cfgelement):
		if os.path.exists("/proc/stb/video/policy2"):
			print "[VideoHardware] setting policy2: %s" % cfgelement.value
			f = open("/proc/stb/video/policy2", "w")
			f.write(cfgelement.value)
			f.close()

	def getOutputAspect(self):
		ret = (16,9)
		port = config.av.videoport.value
		if port not in config.av.videomode:
			print "[VideoHardware] current port not available in getOutputAspect!!! force 16:9"
		else:
			mode = config.av.videomode[port].value
			force_widescreen = self.isWidescreenMode(port, mode)
			is_widescreen = force_widescreen or config.av.aspect.value in ("16:9", "16:10")
			is_auto = config.av.aspect.value == "auto"
			if is_widescreen:
				if force_widescreen:
					pass
				else:
					aspect = {"16:9": "16:9", "16:10": "16:10"}[config.av.aspect.value]
					if aspect == "16:10":
						ret = (16,10)
			elif is_auto:
				try:
					aspect_str = open("/proc/stb/vmpeg/0/aspect", "r").read()
					if aspect_str == "1": # 4:3
						ret = (4,3)
				except IOError:
					pass
			else:  # 4:3
				ret = (4,3)
		return ret

	def getFramebufferScale(self):
		aspect = self.getOutputAspect()
		fb_size = getDesktop(0).size()
		return aspect[0] * fb_size.height(), aspect[1] * fb_size.width()

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

iAVSwitch = AVSwitch()

def InitAVSwitch():
	config.av.yuvenabled = ConfigBoolean(default=True)
	colorformat_choices = {"cvbs": _("CVBS"), "rgb": _("RGB"), "svideo": _("S-Video")}
	# when YUV is not enabled, don't let the user select it
	if config.av.yuvenabled.value:
		colorformat_choices["yuv"] = _("YPbPr")

	config.av.autores = ConfigSelection(choices={"disabled": _("Disabled"), "all": _("All resolutions"), "hd": _("only HD")}, default="disabled")
	choicelist = []
	for i in range(5, 16):
		choicelist.append(("%d" % i, ngettext("%d second", "%d seconds", i) % i))
	config.av.autores_label_timeout = ConfigSelection(default = "5", choices = [("0", _("Not Shown"))] + choicelist)
	config.av.autores_delay = ConfigSelectionNumber(min = 0, max = 15000, stepwidth = 500, default = 500, wraparound = True)
	config.av.autores_deinterlace = ConfigYesNo(default=False)
	config.av.autores_sd = ConfigSelection(choices={"720p": _("720p"), "1080i": _("1080i")}, default="720p")
	config.av.autores_480p24 = ConfigSelection(choices={"480p24": _("480p 24Hz"), "720p24": _("720p 24Hz"), "1080p24": _("1080p 24Hz")}, default="1080p24")
	config.av.autores_720p24 = ConfigSelection(choices={"720p24": _("720p 24Hz"), "1080p24": _("1080p 24Hz")}, default="1080p24")
	config.av.autores_1080p24 = ConfigSelection(choices={"1080p24": _("1080p 24Hz"), "1080p25": _("1080p 25Hz")}, default="1080p24")
	config.av.autores_1080p25 = ConfigSelection(choices={"1080p25": _("1080p 25Hz"), "1080p50": _("1080p 50Hz")}, default="1080p25")
	config.av.autores_1080p30 = ConfigSelection(choices={"1080p30": _("1080p 30Hz"), "1080p60": _("1080p 60Hz")}, default="1080p30")
	config.av.autores_2160p24 = ConfigSelection(choices={"2160p24": _("2160p 24Hz"), "2160p25": _("2160p 25Hz")}, default="2160p24")
	config.av.autores_2160p25 = ConfigSelection(choices={"2160p25": _("2160p 25Hz"), "2160p50": _("2160p 50Hz")}, default="2160p25")
	config.av.autores_2160p30 = ConfigSelection(choices={"2160p30": _("2160p 30Hz"), "2160p60": _("2160p 60Hz")}, default="2160p30")
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
			"4:3": _("4:3"),
			"16:9": _("16:9"),
			"16:10": _("16:10"),
			"auto": _("Automatic")},
			default = "16:9")
	policy2_choices = {
	# TRANSLATORS: (aspect ratio policy: black bars on top/bottom) in doubt, keep english term.
	"letterbox": _("Letterbox"),
	# TRANSLATORS: (aspect ratio policy: cropped content on left/right) in doubt, keep english term
	"panscan": _("Pan&scan"),
	# TRANSLATORS: (aspect ratio policy: display as fullscreen, even if this breaks the aspect)
	"scale": _("Just scale")}
	if os.path.exists("/proc/stb/video/policy2_choices"):
		f = open("/proc/stb/video/policy2_choices")
		if "auto" in f.readline():
			# TRANSLATORS: (aspect ratio policy: always try to display as fullscreen, when there is no content (black bars) on left/right, even if this breaks the aspect.
			policy2_choices.update({"auto": _("Auto")})
		f.close()
	config.av.policy_169 = ConfigSelection(choices=policy2_choices, default = "letterbox")
	policy_choices = {
	# TRANSLATORS: (aspect ratio policy: black bars on left/right) in doubt, keep english term.
	"panscan": _("Pillarbox"),
	# TRANSLATORS: (aspect ratio policy: cropped content on left/right) in doubt, keep english term
	"letterbox": _("Pan&scan"),
	# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching the left/right)
	# "nonlinear": _("Nonlinear"),
	# TRANSLATORS: (aspect ratio policy: display as fullscreen, even if this breaks the aspect)
	"bestfit": _("Just scale")}
	if os.path.exists("/proc/stb/video/policy_choices"):
		f = open("/proc/stb/video/policy_choices")
		if "auto" in f.readline():
			# TRANSLATORS: (aspect ratio policy: always try to display as fullscreen, when there is no content (black bars) on left/right, even if this breaks the aspect.
			policy_choices.update({"auto": _("Auto")})
		f.close()
	config.av.policy_43 = ConfigSelection(choices=policy_choices, default = "panscan")
	config.av.tvsystem = ConfigSelection(choices = {"pal": _("PAL"), "ntsc": _("NTSC"), "multinorm": _("multinorm")}, default="pal")
	config.av.wss = ConfigEnableDisable(default = True)
	config.av.generalAC3delay = ConfigSelectionNumber(-1000, 1000, 5, default = 0)
	config.av.generalPCMdelay = ConfigSelectionNumber(-1000, 1000, 5, default = 0)
	config.av.vcrswitch = ConfigEnableDisable(default = False)

	config.av.aspect.setValue('16:9')
	config.av.aspect.addNotifier(iAVSwitch.setAspect)
	config.av.wss.addNotifier(iAVSwitch.setWss)
	config.av.policy_43.addNotifier(iAVSwitch.setPolicy43)
	config.av.policy_169.addNotifier(iAVSwitch.setPolicy169)

	def setColorFormat(configElement):
		if config.av.videoport and config.av.videoport.value in ("YPbPr", "Scart-YPbPr"):
			iAVSwitch.setColorFormat(3)
		elif config.av.videoport and config.av.videoport.value in ("RCA"):
			iAVSwitch.setColorFormat(0)
		else:
			map = {"cvbs": 0, "rgb": 1, "svideo": 2, "yuv": 3}
			iAVSwitch.setColorFormat(map[configElement.value])
	config.av.colorformat.addNotifier(setColorFormat)

	def setAspectRatio(configElement):
		map = {"4_3_letterbox": 0, "4_3_panscan": 1, "16_9": 2, "16_9_always": 3, "16_10_letterbox": 4, "16_10_panscan": 5, "16_9_letterbox" : 6}
		iAVSwitch.setAspectRatio(map[configElement.value])

	iAVSwitch.setInput("ENCODER") # init on startup
	SystemInfo["ScartSwitch"] = eAVSwitch.getInstance().haveScartSwitch()

	if os.path.exists("/proc/stb/hdmi/bypass_edid_checking"):
		f = open("/proc/stb/hdmi/bypass_edid_checking", "r")
		can_edidchecking = f.read().strip().split(" ")
		f.close()
	else:
		can_edidchecking = False

	SystemInfo["Canedidchecking"] = can_edidchecking

	if can_edidchecking:
		def setEDIDBypass(configElement):
			try:
				f = open("/proc/stb/hdmi/bypass_edid_checking", "w")
				f.write(configElement.value)
				f.close()
			except:
				pass
		config.av.bypass_edid_checking = ConfigSelection(choices={
				"00000000": _("off"),
				"00000001": _("on")},
				default = "00000000")
		config.av.bypass_edid_checking.addNotifier(setEDIDBypass)
	else:
		config.av.bypass_edid_checking = ConfigNothing()

	if os.path.exists("/proc/stb/video/hdmi_colorspace"):
		f = open("/proc/stb/video/hdmi_colorspace", "r")
		have_colorspace = f.read().strip().split(" ")
		f.close()
	else:
		have_colorspace = False

	SystemInfo["havecolorspace"] = have_colorspace

	if have_colorspace:
		def setHDMIColorspace(configElement):
			try:
				f = open("/proc/stb/video/hdmi_colorspace", "w")
				f.write(configElement.value)
				f.close()
			except:
				pass
		if getBoxType() in ('vusolo4k','vuuno4k','vuultimo4k'):
			config.av.hdmicolorspace = ConfigSelection(choices={
					"Edid(Auto)": _("Auto"),
					"Hdmi_Rgb": _("RGB"),
					"444": _("YCbCr444"),
					"422": _("YCbCr422"),
					"420": _("YCbCr420")},
					default = "Edid(Auto)")
		else:
			config.av.hdmicolorspace = ConfigSelection(choices={
					"auto": _("auto"),
					"rgb": _("rgb"),
					"420": _("420"),
					"422": _("422"),
					"444": _("444")},
					default = "auto")
		config.av.hdmicolorspace.addNotifier(setHDMIColorspace)
	else:
		config.av.hdmicolorspace = ConfigNothing()

	if os.path.exists("/proc/stb/video/hdmi_colorimetry"):
		f = open("/proc/stb/video/hdmi_colorimetry", "r")
		have_colorimetry = f.read().strip().split(" ")
		f.close()
	else:
		have_colorimetry = False

	SystemInfo["havecolorimetry"] = have_colorimetry

	if have_colorimetry:
		def setHDMIColorimetry(configElement):
			try:
				f = open("/proc/stb/video/hdmi_colorimetry", "w")
				f.write(configElement.value)
				f.close()
			except:
				pass
		config.av.hdmicolorimetry = ConfigSelection(choices={
				"Auto": _("Auto"),
				"bt2020ncl": _("BT 2020 NCL"),
				"bt2020cl": _("BT 2020 CL"),
				"bt709": _("BT 709")},
				default = "Auto")
		config.av.hdmicolorimetry.addNotifier(setHDMIColorimetry)
	else:
		config.av.hdmicolorimetry = ConfigNothing()

	if os.path.exists("/proc/stb/info/boxmode"):
		f = open("/proc/stb/info/boxmode", "r")
		have_boxmode = f.read().strip().split(" ")
		f.close()
	else:
		have_boxmode = False

	SystemInfo["haveboxmode"] = have_boxmode

	if have_boxmode:
		def setBoxmode(configElement):
			try:
				f = open("/proc/stb/info/boxmode", "w")
				f.write(configElement.value)
				f.close()
			except:
				pass
		config.av.boxmode = ConfigSelection(choices={
				"12": _("PIP enabled, no HDR"),
				"1": _("HDR, 12bit 4:2:0/4:2:2, no PIP")},
				default = "12")
		config.av.boxmode.addNotifier(setBoxmode)
	else:
		config.av.boxmode = ConfigNothing()

	if os.path.exists("/proc/stb/video/hdmi_colordepth"):
		f = open("/proc/stb/video/hdmi_colordepth", "r")
		have_HdmiColordepth = f.read().strip().split(" ")
		f.close()
	else:
		have_HdmiColordepth = False

	SystemInfo["havehdmicolordepth"] = have_HdmiColordepth

	if have_HdmiColordepth:
		def setHdmiColordepth(configElement):
			try:
				f = open("/proc/stb/video/hdmi_colordepth", "w")
				f.write(configElement.value)
				f.close()
			except:
				pass
		config.av.hdmicolordepth = ConfigSelection(choices={
				"auto": _("Auto"),
				"8bit": _("8bit"),
				"10bit": _("10bit"),
				"12bit": _("12bit")},
				default = "auto")
		config.av.hdmicolordepth.addNotifier(setHdmiColordepth)
	else:
		config.av.hdmicolordepth = ConfigNothing()

	if os.path.exists("/proc/stb/hdmi/audio_source"):
		f = open("/proc/stb/hdmi/audio_source", "r")
		can_audiosource = f.read().strip().split(" ")
		f.close()
	else:
		can_audiosource = False

	SystemInfo["Canaudiosource"] = can_audiosource

	if can_audiosource:
		def setAudioSource(configElement):
			try:
				f = open("/proc/stb/hdmi/audio_source", "w")
				f.write(configElement.value)
				f.close()
			except:
				pass
		config.av.audio_source = ConfigSelection(choices={
				"pcm": _("PCM"),
				"spdif": _("SPDIF")},
				default="pcm")
		config.av.audio_source.addNotifier(setAudioSource)
	else:
		config.av.audio_source = ConfigNothing()

	if os.path.exists("/proc/stb/audio/3d_surround_choices"):
		f = open("/proc/stb/audio/3d_surround_choices", "r")
		can_3dsurround = f.read().strip().split(" ")
		f.close()
	else:
		can_3dsurround = False

	SystemInfo["Can3DSurround"] = can_3dsurround

	if can_3dsurround:
		def set3DSurround(configElement):
			f = open("/proc/stb/audio/3d_surround", "w")
			f.write(configElement.value)
			f.close()
		choice_list = [("none", _("off")), ("hdmi", _("HDMI")), ("spdif", _("SPDIF")), ("dac", _("DAC"))]
		config.av.surround_3d = ConfigSelection(choices = choice_list, default = "none")
		config.av.surround_3d.addNotifier(set3DSurround)
	else:
		config.av.surround_3d = ConfigNothing()

	if os.path.exists("/proc/stb/audio/3d_surround_speaker_position_choices"):
		f = open("/proc/stb/audio/3d_surround_speaker_position_choices", "r")
		can_3dsurround_speaker = f.read().strip().split(" ")
		f.close()
	else:
		can_3dsurround_speaker = False

	SystemInfo["Can3DSpeaker"] = can_3dsurround_speaker

	if can_3dsurround_speaker:
		def set3DSurroundSpeaker(configElement):
			f = open("/proc/stb/audio/3d_surround_speaker_position", "w")
			f.write(configElement.value)
			f.close()
		choice_list = [("center", _("center")), ("wide", _("wide")), ("extrawide", _("extra wide"))]
		config.av.surround_3d_speaker = ConfigSelection(choices = choice_list, default = "center")
		config.av.surround_3d_speaker.addNotifier(set3DSurroundSpeaker)
	else:
		config.av.surround_3d_speaker = ConfigNothing()

	if os.path.exists("/proc/stb/audio/avl_choices"):
		f = open("/proc/stb/audio/avl_choices", "r")
		can_autovolume = f.read().strip().split(" ")
		f.close()
	else:
		can_autovolume = False

	SystemInfo["CanAutoVolume"] = can_autovolume

	if can_autovolume:
		def setAutoVolume(configElement):
			f = open("/proc/stb/audio/avl", "w")
			f.write(configElement.value)
			f.close()
		choice_list = [("none", _("off")), ("hdmi", _("HDMI")), ("spdif", _("SPDIF")), ("dac", _("DAC"))]
		config.av.autovolume = ConfigSelection(choices = choice_list, default = "none")
		config.av.autovolume.addNotifier(setAutoVolume)
	else:
		config.av.autovolume = ConfigNothing()

	try:
		can_pcm_multichannel = os.access("/proc/stb/audio/multichannel_pcm", os.W_OK)
	except:
		can_pcm_multichannel = False

	SystemInfo["supportPcmMultichannel"] = can_pcm_multichannel
	if can_pcm_multichannel:
		def setPCMMultichannel(configElement):
			open("/proc/stb/audio/multichannel_pcm", "w").write(configElement.value and "enable" or "disable")
		config.av.pcm_multichannel = ConfigYesNo(default = False)
		config.av.pcm_multichannel.addNotifier(setPCMMultichannel)

	try:
		f = open("/proc/stb/audio/ac3_choices", "r")
		file = f.read()[:-1]
		f.close()
		can_downmix_ac3 = "downmix" in file
	except:
		can_downmix_ac3 = False

	SystemInfo["CanDownmixAC3"] = can_downmix_ac3
	if can_downmix_ac3:
		def setAC3Downmix(configElement):
			f = open("/proc/stb/audio/ac3", "w")
			f.write(configElement.value and "downmix" or "passthrough")
			f.close()
			if SystemInfo.get("supportPcmMultichannel", False) and not configElement.value:
				SystemInfo["CanPcmMultichannel"] = True
			else:
				SystemInfo["CanPcmMultichannel"] = False
				if can_pcm_multichannel:
					config.av.pcm_multichannel.setValue(False)
		config.av.downmix_ac3 = ConfigYesNo(default = True)
		config.av.downmix_ac3.addNotifier(setAC3Downmix)

	try:
		f = open("/proc/stb/audio/dts_choices", "r")
		file = f.read()[:-1]
		f.close()
		can_downmix_dts = "downmix" in file
	except:
		can_downmix_dts = False

	SystemInfo["CanDownmixDTS"] = can_downmix_dts
	if can_downmix_dts:
		def setDTSDownmix(configElement):
			f = open("/proc/stb/audio/dts", "w")
			f.write(configElement.value and "downmix" or "passthrough")
			f.close()
		config.av.downmix_dts = ConfigYesNo(default = True)
		config.av.downmix_dts.addNotifier(setDTSDownmix)

	try:
		f = open("/proc/stb/audio/aac_choices", "r")
		file = f.read()[:-1]
		f.close()
		can_downmix_aac = "downmix" in file
	except:
		can_downmix_aac = False

	SystemInfo["CanDownmixAAC"] = can_downmix_aac
	if can_downmix_aac:
		def setAACDownmix(configElement):
			f = open("/proc/stb/audio/aac", "w")
			f.write(configElement.value and "downmix" or "passthrough")
			f.close()
		config.av.downmix_aac = ConfigYesNo(default = True)
		config.av.downmix_aac.addNotifier(setAACDownmix)

	if os.path.exists("/proc/stb/audio/aac_transcode_choices"):
		f = open("/proc/stb/audio/aac_transcode_choices", "r")
		can_aactranscode = f.read().strip().split(" ")
		f.close()
	else:
		can_aactranscode = False

	SystemInfo["CanAACTranscode"] = can_aactranscode

	if can_aactranscode:
		def setAACTranscode(configElement):
			f = open("/proc/stb/audio/aac_transcode", "w")
			f.write(configElement.value)
			f.close()
		choice_list = [("off", _("off")), ("ac3", _("AC3")), ("dts", _("DTS"))]
		config.av.transcodeaac = ConfigSelection(choices = choice_list, default = "off")
		config.av.transcodeaac.addNotifier(setAACTranscode)
	else:
		config.av.transcodeaac = ConfigNothing()

	if os.path.exists("/proc/stb/vmpeg/0/pep_scaler_sharpness"):
		def setScaler_sharpness(config):
			myval = int(config.value)
			try:
				print "[VideoHardware] setting scaler_sharpness to: %0.8X" % myval
				f = open("/proc/stb/vmpeg/0/pep_scaler_sharpness", "w")
				f.write("%0.8X" % myval)
				f.close()
				f = open("/proc/stb/vmpeg/0/pep_apply", "w")
				f.write("1")
				f.close()
			except IOError:
				print "[VideoHardware] couldn't write pep_scaler_sharpness"

		if getBoxType() in ('gbquad', 'gbquadplus'):
			config.av.scaler_sharpness = ConfigSlider(default=5, limits=(0,26))
		else:
			config.av.scaler_sharpness = ConfigSlider(default=13, limits=(0,26))
		config.av.scaler_sharpness.addNotifier(setScaler_sharpness)
	else:
		config.av.scaler_sharpness = NoSave(ConfigNothing())

	config.av.edid_override = ConfigYesNo(default = False)

	iAVSwitch.setConfiguredMode()

class VideomodeHotplug:
	def __init__(self):
		pass

	def start(self):
		iAVSwitch.on_hotplug.append(self.hotplug)

	def stop(self):
		iAVSwitch.on_hotplug.remove(self.hotplug)

	def hotplug(self, what):
		print "[VideoHardware] hotplug detected on port '%s'" % what
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value

		if not iAVSwitch.isModeAvailable(port, mode, rate):
			print "[VideoHardware] mode %s/%s/%s went away!" % (port, mode, rate)
			modelist = iAVSwitch.getModeList(port)
			if not len(modelist):
				print "[VideoHardware] sorry, no other mode is available (unplug?). Doing nothing."
				return
			mode = modelist[0][0]
			rate = modelist[0][1]
			print "[VideoHardware] setting %s/%s/%s" % (port, mode, rate)
			iAVSwitch.setMode(port, mode, rate)

hotplug = None

def startHotplug():
	global hotplug
	hotplug = VideomodeHotplug()
	hotplug.start()

def stopHotplug():
	global hotplug
	hotplug.stop()

def InitiVideomodeHotplug(**kwargs):
	startHotplug()
