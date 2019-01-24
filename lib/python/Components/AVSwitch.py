from config import config, ConfigSlider, ConfigSelection, ConfigSubDict, ConfigYesNo, ConfigEnableDisable, ConfigSubsection, ConfigBoolean, ConfigSelectionNumber, ConfigNothing, NoSave
from Components.About import about
from Tools.CList import CList
from Tools.HardwareInfo import HardwareInfo
from enigma import eAVSwitch, eDVBVolumecontrol, getDesktop
from boxbranding import getBoxType, getMachineBuild, getBrandOEM
from SystemInfo import SystemInfo
import os
from time import sleep

has_scart = False
has_scartyuv = False
has_yuv = False
has_dvi = False
has_hdmi = False
has_rca = False
has_avjack = False

has_scart = SystemInfo["HAVESCART"]
has_scartyuv = SystemInfo["HAVESCARTYUV"]
has_yuv = SystemInfo["HAVEYUV"]
has_dvi = SystemInfo["HaveDVI"]
has_hdmi = SystemInfo["HAVEHDMI"]
has_rca = SystemInfo["HaveRCA"]
has_avjack = SystemInfo["HaveAVJACK"]

config.av = ConfigSubsection()
if getBrandOEM() in ('azbox'):
	config.av.edid_override = ConfigYesNo(default = True)
else:
	config.av.edid_override = ConfigYesNo(default = False)

class AVSwitch:
	hw_type = HardwareInfo().get_device_name()
	rates = { } # high-level, use selectable modes.
	modes = { }  # a list of (high-level) modes for a certain port.

	rates["PAL"] =		{	"50Hz":		{ 50: "pal" },
							"60Hz":		{ 60: "pal60" },
							"multi":	{ 50: "pal", 60: "pal60" } }

	rates["NTSC"] =		{	"60Hz":		{ 60: "ntsc" } }

	rates["Multi"] =	{	"multi":	{ 50: "pal", 60: "ntsc" } }

	rates["480i"] =		{	"60Hz":		{ 60: "480i" } }

	rates["576i"] =		{	"50Hz":		{ 50: "576i" } }

	rates["480p"] =		{	"60Hz":		{ 60: "480p" } }

	rates["576p"] =		{	"50Hz":		{ 50: "576p" } }

	rates["720p"] =		{	"50Hz":		{ 50: "720p50" },
							"60Hz":		{ 60: "720p" },
							"multi":	{ 50: "720p50", 60: "720p" },
							"auto":		{ 50: "720p50", 60: "720p", 24: "720p24" } }

	rates["1080i"] =	{	"50Hz":		{ 50: "1080i50" },
							"60Hz":		{ 60: "1080i" },
							"multi":	{ 50: "1080i50", 60: "1080i" },
							"auto":		{ 50: "1080i50", 60: "1080i", 24: "1080p24" } }

	rates["1080p"] =	{ 	"50Hz":		{ 50: "1080p50" },
							"60Hz":		{ 60: "1080p" },
							"multi":	{ 50: "1080p50", 60: "1080p" },
							"auto":		{ 50: "1080p50", 60: "1080p", 24: "1080p24" } }

	if getBoxType().startswith('dm9'):
		rates["2160p"] =	{ 	"50Hz":		{ 50: "2160p50" },
								"60Hz":		{ 60: "2160p60" },
								"multi":	{ 50: "2160p50", 60: "2160p60" },
								"auto":		{ 50: "2160p50", 60: "2160p60", 24: "2160p24" } }
	else:
		rates["2160p"] =	{ 	"50Hz":		{ 50: "2160p50" },
								"60Hz":		{ 60: "2160p" },
								"multi":	{ 50: "2160p50", 60: "2160p" },
								"auto":		{ 50: "2160p50", 60: "2160p", 24: "2160p24" } }

	rates["2160p30"] =	{ 	"25Hz":		{ 50: "2160p25" },
							"30Hz":		{ 60: "2160p30"} ,
							"multi":	{ 50: "2160p25", 60: "2160p30" },
							"auto":		{ 50: "2160p25", 60: "2160p30", 24: "2160p24" } }

	rates["PC"] = {
		"1024x768":						{ 60: "1024x768" }, # not possible on DM7025
		"800x600" :						{ 60: "800x600" },  # also not possible
		"720x480" :						{ 60: "720x480" },
		"720x576" :						{ 60: "720x576" },
		"1280x720":						{ 60: "1280x720" },
		"1280x720 multi":				{ 50: "1280x720_50", 60: "1280x720" },
		"1920x1080":					{ 60: "1920x1080"},
		"1920x1080 multi":				{ 50: "1920x1080", 60: "1920x1080_50" },
		"1280x1024":					{ 60: "1280x1024"},
		"1366x768" :					{ 60: "1366x768"},
		"1366x768 multi":				{ 50: "1366x768", 60: "1366x768_50" },
		"1280x768":						{ 60: "1280x768" },
		"640x480" :						{ 60: "640x480" }
	}

	modes["Scart"] = ["PAL", "NTSC", "Multi"]
	# modes["DVI-PC"] = ["PC"]

	if (about.getChipSetString() in ('7366', '7376', '5272s', '7444', '7445', '7445s')):
		modes["HDMI"] = ["720p", "1080p", "2160p", "1080i", "576p", "576i", "480p", "480i"]
		widescreen_modes = {"720p", "1080p", "1080i", "2160p"}
	elif (about.getChipSetString() in ('7252', '7251', '7251S', '7252S', '7251s', '7252s', '72604', '7278', '7444s', '3798mv200', '3798cv200', 'hi3798mv200', 'hi3798cv200')):
		modes["HDMI"] = ["720p", "1080p", "2160p", "2160p30", "1080i", "576p", "576i", "480p", "480i"]
		widescreen_modes = {"720p", "1080p", "1080i", "2160p", "2160p30"}
	elif (about.getChipSetString() in ('7241', '7358', '7362', '73625', '7346', '7356', '73565', '7424', '7425', '7435', '7552', '7581', '7584', '75845', '7585', 'pnx8493', '7162', '7111', '3716mv410', 'hi3716mv410')) or (getBrandOEM() in ('azbox')):
		modes["HDMI"] = ["720p", "1080p", "1080i", "576p", "576i", "480p", "480i"]
		widescreen_modes = {"720p", "1080p", "1080i"}
	elif about.getChipSetString() in ('meson-6'):
		modes["HDMI"] = ["720p", "1080p", "1080i"]
		widescreen_modes = {"720p", "1080p", "1080i"}
	elif about.getChipSetString() in ('meson-64','S905D'):
		modes["HDMI"] = ["720p", "1080p", "2160p", "2160p30", "1080i"]
		widescreen_modes = {"720p", "1080p", "1080i", "2160p", "2160p30"}
	else:
		modes["HDMI"] = ["720p", "1080i", "576p", "576i", "480p", "480i"]
		widescreen_modes = {"720p", "1080i"}

	modes["YPbPr"] = modes["HDMI"]
	if has_scartyuv:
		modes["Scart-YPbPr"] = modes["HDMI"]

	# if modes.has_key("DVI-PC") and not getModeList("DVI-PC"):
	# 	print "[AVSwitch] remove DVI-PC because of not existing modes"
	# 	del modes["DVI-PC"]
	if modes.has_key("YPbPr") and not has_yuv:
		del modes["YPbPr"]
	if modes.has_key("Scart") and not has_scart and not has_rca and not has_avjack:
			del modes["Scart"]
		
	if getBoxType() in ('mutant2400'):
		f = open("/proc/stb/info/board_revision", "r").read()
		if f >= "2":
			del modes["YPbPr"]

	def __init__(self):
		self.last_modes_preferred =  [ ]
		self.on_hotplug = CList()
		self.current_mode = None
		self.current_port = None

		self.readAvailableModes()
		self.is24hzAvailable()

		self.readPreferredModes()
		self.createConfig()


	def readAvailableModes(self):
		try:
			f = open("/proc/stb/video/videomode_choices")
			modes = f.read()[:-1]
			f.close()
		except IOError:
			print "[AVSwitch] couldn't read available videomodes."
			self.modes_available = [ ]
			return
		self.modes_available = modes.split(' ')

	def readPreferredModes(self):
		if config.av.edid_override.value == False:
			try:
				f = open("/proc/stb/video/videomode_edid")
				modes = f.read()[:-1]
				f.close()
				self.modes_preferred = modes.split(' ')
				print "[AVSwitch] reading edid modes: ", self.modes_preferred
			except IOError:
				print "[AVSwitch] reading edid modes failed, using all modes"
				try:
					f = open("/proc/stb/video/videomode_preferred")
					modes = f.read()[:-1]
					f.close()
					self.modes_preferred = modes.split(' ')
					print "[AVSwitch] reading _preferred modes: ", self.modes_preferred
				except IOError:
					print "[AVSwitch] reading preferred modes failed, using all modes"
					self.modes_preferred = self.modes_available
		else:
			self.modes_preferred = self.modes_available
			print "[AVSwitch] used default modes: ", self.modes_preferred
			
		if len(self.modes_preferred) <= 2:
			print "[AVSwitch] preferend modes not ok, possible driver failer, len=", len(self.modes_preferred)
			self.modes_preferred = self.modes_available

		if self.modes_preferred != self.last_modes_preferred:
			self.last_modes_preferred = self.modes_preferred
			self.on_hotplug("HDMI") # must be HDMI

	def is24hzAvailable(self):
		try:
			self.has24pAvailable = os.access("/proc/stb/video/videomode_24hz", os.W_OK) and True or False
		except IOError:
			print "[AVSwitch] failed to read video choices 24hz ."
			self.has24pAvailable = False
		SystemInfo["have24hz"] = self.has24pAvailable

	# check if a high-level mode with a given rate is available.
	def isModeAvailable(self, port, mode, rate):
		rate = self.rates[mode][rate]
		for mode in rate.values():
			if port == "DVI":
				if getBrandOEM() in ('azbox'):
					if mode not in self.modes_preferred and not config.av.edid_override.value:
						print "[AVSwitch] no, not preferred"
						return False
			if port != "HDMI":
				if mode not in self.modes_available:
					return False
			elif mode not in self.modes_preferred:
				return False
		return True

	def isWidescreenMode(self, port, mode):
		return mode in self.widescreen_modes

	def setMode(self, port, mode, rate, force = None):
		print "[AVSwitch] setMode - port: %s, mode: %s, rate: %s" % (port, mode, rate)

		# config.av.videoport.setValue(port)
		# we can ignore "port"
		self.current_mode = mode
		self.current_port = port
		modes = self.rates[mode][rate]


		mode_50 = modes.get(50)
		mode_60 = modes.get(60)
		mode_24 = modes.get(24)

		if mode_50 is None or force == 60:
			mode_50 = mode_60
		if mode_60 is None or force == 50:
			mode_60 = mode_50
		if mode_24 is None or force:
			mode_24 = mode_60
			if force == 50:
				mode_24 = mode_50

		try:
			f = open("/proc/stb/video/videomode_50hz", "w")
			f.write(mode_50)
			f.close()
			f = open("/proc/stb/video/videomode_60hz", "w")
			f.write(mode_60)
			f.close()
		except IOError:
			try:
				# fallback if no possibility to setup 50/60 hz mode
				f = open("/proc/stb/video/videomode", "w")
				f.write(mode_50)
				f.close()
			except IOError:
				print "[AVSwitch] setting videomode failed."

		if SystemInfo["have24hz"]:
			try:
				open("/proc/stb/video/videomode_24hz", "w").write(mode_24)
			except IOError:
				print "[VideoHardware] cannot open /proc/stb/video/videomode_24hz"

		if getBrandOEM() in ('gigablue'):
			try:
				# use 50Hz mode (if available) for booting
				f = open("/etc/videomode", "w")
				f.write(mode_50)
				f.close()
			except IOError:
				print "[AVSwitch] writing initial videomode to /etc/videomode failed."

		map = {"cvbs": 0, "rgb": 1, "svideo": 2, "yuv": 3}
		self.setColorFormat(map[config.av.colorformat.value])

		if about.getCPUString().startswith('STx'):
			#call setResolution() with -1,-1 to read the new scrren dimensions without changing the framebuffer resolution
			from enigma import gMainDC
			gMainDC.getInstance().setResolution(-1, -1)

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
		config.av.autores_mode_sd = ConfigSubDict()
		config.av.autores_mode_hd = ConfigSubDict()
		config.av.autores_mode_fhd = ConfigSubDict()
		config.av.autores_mode_uhd = ConfigSubDict()
		config.av.videorate = ConfigSubDict()
		config.av.autores_rate_sd = ConfigSubDict()
		config.av.autores_rate_hd = ConfigSubDict()
		config.av.autores_rate_fhd = ConfigSubDict()
		config.av.autores_rate_uhd = ConfigSubDict()

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
				config.av.autores_mode_sd[port] = ConfigSelection(choices = [mode for (mode, rates) in modes])
				config.av.autores_mode_hd[port] = ConfigSelection(choices = [mode for (mode, rates) in modes])
				config.av.autores_mode_fhd[port] = ConfigSelection(choices = [mode for (mode, rates) in modes])
				config.av.autores_mode_uhd[port] = ConfigSelection(choices = [mode for (mode, rates) in modes])
			for (mode, rates) in modes:
				ratelist = []
				for rate in rates:
					if rate in ("auto") and not SystemInfo["have24hz"]:
						continue
					ratelist.append((rate, rate))
				config.av.videorate[mode] = ConfigSelection(choices = ratelist)
				config.av.autores_rate_sd[mode] = ConfigSelection(choices = ratelist)
				config.av.autores_rate_hd[mode] = ConfigSelection(choices = ratelist)
				config.av.autores_rate_fhd[mode] = ConfigSelection(choices = ratelist)
				config.av.autores_rate_uhd[mode] = ConfigSelection(choices = ratelist)
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
			print "[AVSwitch] current port not available, not setting videomode"
			return

		mode = config.av.videomode[port].value

		if mode not in config.av.videorate:
			print "[AVSwitch] current mode not available, not setting videomode"
			return

		rate = config.av.videorate[mode].value
		self.setMode(port, mode, rate)

	def setAspect(self, cfgelement):
		print "[AVSwitch] setting aspect: %s" % cfgelement.value
		try:
			f = open("/proc/stb/video/aspect", "w")
			f.write(cfgelement.value)
			f.close()
		except IOError:
			print "[AVSwitch] setting aspect failed."

	def setWss(self, cfgelement):
		if not cfgelement.value:
			wss = "auto(4:3_off)"
		else:
			wss = "auto"
		if os.path.exists("/proc/stb/denc/0/wss"):
			print "[AVSwitch] setting wss: %s" % wss
			f = open("/proc/stb/denc/0/wss", "w")
			f.write(wss)
			f.close()

	def setPolicy43(self, cfgelement):
		print "[AVSwitch] setting policy: %s" % cfgelement.value
		arw = "0"
		try:
			if about.getChipSetString() in ('meson-6', 'meson-64'):
				if cfgelement.value == "panscan" : arw = "11"
				if cfgelement.value == "letterbox" : arw = "12"
				if cfgelement.value == "bestfit" : arw = "10"
				open("/sys/class/video/screen_mode", "w").write(arw)
			else:
				f = open("/proc/stb/video/policy", "w")
				f.write(cfgelement.value)
				f.close()
		except IOError:
			print "[AVSwitch] setting policy43 failed."

	def setPolicy169(self, cfgelement):
		if os.path.exists("/proc/stb/video/policy2"):
			print "[AVSwitch] setting policy2: %s" % cfgelement.value
			f = open("/proc/stb/video/policy2", "w")
			f.write(cfgelement.value)
			f.close()

	def getOutputAspect(self):
		ret = (16,9)
		port = config.av.videoport.value
		if port not in config.av.videomode:
			print "current port not available in getOutputAspect!!! force 16:9"
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

	def setAspectRatio(self, value):
		eAVSwitch.getInstance().setAspectRatio(value)

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
	if getBoxType() == 'vuduo' or getBoxType().startswith('ixuss'):
		config.av.yuvenabled = ConfigBoolean(default=False)
	else:
		config.av.yuvenabled = ConfigBoolean(default=True)
	config.av.osd_alpha = ConfigSlider(default=255, increment = 5, limits=(20,255)) # Make openATV compatible with some plugins who still use config.av.osd_alpha
	colorformat_choices = {"cvbs": _("CVBS"), "rgb": _("RGB"), "svideo": _("S-Video")}
	# when YUV is not enabled, don't let the user select it
	if config.av.yuvenabled.value:
		colorformat_choices["yuv"] = _("YPbPr")

	config.av.autores = ConfigSelection(choices={"disabled": _("Disabled"), "simple": _("Simple"), "native": _("Native"), "all": _("All resolutions"), "hd": _("only HD")}, default="disabled")
	config.av.autores_preview = NoSave(ConfigYesNo(default=False))
	config.av.autores_1080i_deinterlace = ConfigYesNo(default=False)
	choicelist = {
			"24,24": _("24p/24p"),
			"24,25": _("24p/25p"),
			"24,30": _("24p/30p"),
			"24,50": _("24p/50p"),
			"24,60": _("24p/60p"),
			"25,24": _("25p/24p"),
			"30,24": _("30p/24p"),
			"50,24": _("50p/24p"),
			"60,24": _("60p/24p"),
			"25,25": _("25p/25p"),
			"25,30": _("25p/30p"),
			"25,50": _("25p/50p"),
			"25,60": _("25p/60p"),
			"30,25": _("30p/25p"),
			"50,25": _("50p/25p"),
			"60,25": _("60p/25p"),
			"30,30": _("30p/30p"),
			"30,50": _("30p/50p"),
			"30,60": _("30p/60p"),
			"50,30": _("50p/30p"),
			"60,30": _("60p/30p"),
			"50,50": _("50p/50p"),
			"50,60": _("50p/60p"),
			"60,50": _("60p/50p"),
			"60,60": _("60p/60p")
				}  # first value <=720p , second value > 720p
	config.av.autores_24p =  ConfigSelection(choices=choicelist, default="50,24")
	config.av.autores_25p =  ConfigSelection(choices=choicelist, default="50,25")
	config.av.autores_30p =  ConfigSelection(choices=choicelist, default="60,30")
	config.av.autores_unknownres =  ConfigSelection(choices={"next": _("next higher Resolution"), "highest": _("highest Resolution")}, default="next")
	choicelist = []
	for i in range(5, 16):
		choicelist.append(("%d" % i, ngettext("%d second", "%d seconds", i) % i))
	config.av.autores_label_timeout = ConfigSelection(default = "5", choices = [("0", _("Not Shown"))] + choicelist)
	config.av.autores_delay = ConfigSelectionNumber(min = 0, max = 3000, stepwidth = 50, default = 400, wraparound = True)
	config.av.autores_deinterlace = ConfigYesNo(default=False)
	config.av.autores_sd = ConfigSelection(choices={"720p50": _("720p50"), "720p": _("720p"), "1080i50": _("1080i50"), "1080i": _("1080i")}, default="720p50")
	config.av.autores_480p24 = ConfigSelection(choices={"480p24": _("480p 24Hz"), "720p24": _("720p 24Hz"), "1080p24": _("1080p 24Hz")}, default="1080p24")
	config.av.autores_720p24 = ConfigSelection(choices={"720p24": _("720p 24Hz"), "1080p24": _("1080p 24Hz"), "1080i50": _("1080i 50Hz"), "1080i": _("1080i 60Hz")}, default="720p24")
	config.av.autores_1080p24 = ConfigSelection(choices={"1080p24": _("1080p 24Hz"), "1080p25": _("1080p 25Hz"), "1080i50": _("1080p 50Hz"), "1080i": _("1080i 60Hz")}, default="1080p24")
	config.av.autores_1080p25 = ConfigSelection(choices={"1080p25": _("1080p 25Hz"), "1080p50": _("1080p 50Hz"), "1080i50": _("1080i 50Hz")}, default="1080p25")
	config.av.autores_1080p30 = ConfigSelection(choices={"1080p30": _("1080p 30Hz"), "1080p60": _("1080p 60Hz"), "1080i": _("1080i 60Hz")}, default="1080p30")
	config.av.smart1080p = ConfigSelection(choices={"false": _("off"), "true": _("1080p50: 24p/50p/60p"), "2160p50": _("2160p50: 24p/50p/60p"), "1080i50": _("1080i50: 24p/50i/60i"), "720p50": _("720p50: 24p/50p/60p")}, default="false")
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

	# Some boxes have a redundant proc entry for policy2 choices, but some don't (The choices are from a 16:9 point of view anyways)
	if os.path.exists("/proc/stb/video/policy2_choices"):
		policy2_choices_proc="/proc/stb/video/policy2_choices"
	else:
		policy2_choices_proc="/proc/stb/video/policy_choices"

	try:
		policy2_choices_raw=open(policy2_choices_proc, "r").read()
	except:
		policy2_choices_raw="letterbox"
	
	policy2_choices = {}

	if "letterbox" in policy2_choices_raw:
		# TRANSLATORS: (aspect ratio policy: black bars on top/bottom) in doubt, keep english term.
		policy2_choices.update({"letterbox": _("Letterbox")})

	if "panscan" in policy2_choices_raw:
		# TRANSLATORS: (aspect ratio policy: cropped content on left/right) in doubt, keep english term
		policy2_choices.update({"panscan": _("Pan&scan")})

	if "nonliner" in policy2_choices_raw and not "nonlinear" in policy2_choices_raw:
		# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching the top/bottom (Center of picture maintains aspect, top/bottom lose aspect heaver than on linear stretch))
		policy2_choices.update({"nonliner": _("Stretch nonlinear")})
	if "nonlinear" in policy2_choices_raw:
		# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching the top/bottom (Center of picture maintains aspect, top/bottom lose aspect heaver than on linear stretch))
		policy2_choices.update({"nonlinear": _("Stretch nonlinear")})

	if "scale" in policy2_choices_raw and not "auto" in policy2_choices_raw and not "bestfit" in policy2_choices_raw:
		# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching all parts of the picture with the same factor (All parts lose aspect))
		policy2_choices.update({"scale": _("Stretch linear")})
	if "full" in policy2_choices_raw:
		# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching all parts of the picture with the same factor (force aspect))
		policy2_choices.update({"full": _("Stretch full")})
	if "auto" in policy2_choices_raw and not "bestfit" in policy2_choices_raw:
		# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching all parts of the picture with the same factor (All parts lose aspect))
		policy2_choices.update({"auto": _("Stretch linear")})
	if "bestfit" in policy2_choices_raw:
		# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching all parts of the picture with the same factor (All parts lose aspect))
		policy2_choices.update({"bestfit": _("Stretch linear")})

	config.av.policy_169 = ConfigSelection(choices=policy2_choices, default =	"letterbox")

	policy_choices_proc="/proc/stb/video/policy_choices"
	try:
		policy_choices_raw=open(policy_choices_proc, "r").read()
	except:
		policy_choices_raw="panscan"
	
	policy_choices = {}

	if "pillarbox" in policy_choices_raw and not "panscan" in policy_choices_raw:
		# Very few boxes support "pillarbox" as an alias for "panscan" (Which in fact does pillarbox)
		# So only add "pillarbox" if "panscan" is not listed in choices
		
		# TRANSLATORS: (aspect ratio policy: black bars on left/right) in doubt, keep english term.
		policy_choices.update({"pillarbox": _("Pillarbox")})

	if "panscan" in policy_choices_raw:
		# DRIVER BUG:	"panscan" in /proc actually does "pillarbox" (That's probably why an alias to it named "pillarbox" existed)!
		#		Interpret "panscan" setting with a "Pillarbox" text in order to show the correct value in GUI

		# TRANSLATORS: (aspect ratio policy: black bars on left/right) in doubt, keep english term.
		policy_choices.update({"panscan": _("Pillarbox")})

	if "letterbox" in policy_choices_raw:
		# DRIVER BUG:	"letterbox" in /proc actually does pan&scan
		#		"letterbox" and 4:3 content on 16:9 TVs is mutually exclusive, as "letterbox" is the method to show wide content on narrow TVs
		#		Probably the bug arose as the driver actually does the same here as it would for wide content on narrow TVs (It stretches the picture to fit width)
		
		# TRANSLATORS: (aspect ratio policy: Fit width, cut/crop top and bottom (Maintain aspect ratio))
		policy_choices.update({"letterbox": _("Pan&scan")})

	if "nonliner" in policy_choices_raw and not "nonlinear" in policy_choices_raw:
		# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching the left/right (Center 50% of picture maintain aspect, left/right 25% lose aspect heaver than on linear stretch))
		policy_choices.update({"nonliner": _("Stretch nonlinear")})
	if "nonlinear" in policy_choices_raw:
		# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching the left/right (Center 50% of picture maintain aspect, left/right 25% lose aspect heaver than on linear stretch))
		policy_choices.update({"nonlinear": _("Stretch nonlinear")})

	# "auto", "bestfit" and "scale" are aliasses for the same: Stretch linear
	if "scale" in policy_choices_raw and not "auto" in policy_choices_raw and not "bestfit" in policy_choices_raw:
		# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching all parts of the picture with the same factor (All parts lose aspect))
		policy_choices.update({"scale": _("Stretch linear")})
	if "full" in policy_choices_raw:
		# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching all parts of the picture with the same factor (force aspect))
		policy_choices.update({"full": _("Stretch full")})
	if "auto" in policy_choices_raw and not "bestfit" in policy_choices_raw:
		# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching all parts of the picture with the same factor (All parts lose aspect))
		policy_choices.update({"auto": _("Stretch linear")})
	if "bestfit" in policy_choices_raw:
		# TRANSLATORS: (aspect ratio policy: display as fullscreen, with stretching all parts of the picture with the same factor (All parts lose aspect))
		policy_choices.update({"bestfit": _("Stretch linear")})

	config.av.policy_43 = ConfigSelection(choices=policy_choices, default = "panscan")
	config.av.tvsystem = ConfigSelection(choices = {"pal": _("PAL"), "ntsc": _("NTSC"), "multinorm": _("multinorm")}, default="pal")
	config.av.wss = ConfigEnableDisable(default = True)
	config.av.generalAC3delay = ConfigSelectionNumber(-1000, 1000, 5, default = 0)
	config.av.generalPCMdelay = ConfigSelectionNumber(-1000, 1000, 5, default = 0)
	config.av.vcrswitch = ConfigEnableDisable(default = False)

	#config.av.aspect.setValue('16:9')
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
			if getBoxType() == 'et6x00':
				map = {"cvbs": 3, "rgb": 3, "svideo": 2, "yuv": 3}	
			elif getBoxType() == 'gbquad' or getBoxType() == 'gbquadplus' or getBoxType().startswith('et'):
				map = {"cvbs": 0, "rgb": 3, "svideo": 2, "yuv": 3}
			else:
				map = {"cvbs": 0, "rgb": 1, "svideo": 2, "yuv": 3}
			iAVSwitch.setColorFormat(map[configElement.value])
	config.av.colorformat.addNotifier(setColorFormat)

	def setAspectRatio(configElement):
		map = {"4_3_letterbox": 0, "4_3_panscan": 1, "16_9": 2, "16_9_always": 3, "16_10_letterbox": 4, "16_10_panscan": 5, "16_9_letterbox" : 6}
		iAVSwitch.setAspectRatio(map[configElement.value])

	iAVSwitch.setInput("ENCODER") # init on startup
	if (getBoxType() in ('gbquad', 'gbquadplus', 'et5x00', 'ixussone', 'ixusszero', 'axodin', 'axodinc', 'starsatlx', 'galaxym6', 'geniuse3hd', 'evoe3hd', 'axase3', 'axase3c', 'omtimussos1', 'omtimussos2', 'gb800seplus', 'gb800ueplus', 'gbultrase', 'gbultraue', 'gbultraueh' , 'twinboxlcd' )) or about.getModelString() == 'et6000':
		detected = False
	else:
		detected = eAVSwitch.getInstance().haveScartSwitch()

	SystemInfo["ScartSwitch"] = detected

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
				default = "00000001")
		config.av.bypass_edid_checking.addNotifier(setEDIDBypass)
	else:
		config.av.bypass_edid_checking = ConfigNothing()
		
		
	def setUnsupportModes(configElement):
		iAVSwitch.readPreferredModes()
		iAVSwitch.createConfig()

	config.av.edid_override.addNotifier(setUnsupportModes)

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
		if getBoxType() in ('vusolo4k','vuuno4k','vuuno4kse','vuultimo4k','vuduo4k'):
			config.av.hdmicolorspace = ConfigSelection(choices={
					"Edid(Auto)": _("Auto"),
					"Hdmi_Rgb": _("RGB"),
					"444": _("YCbCr444"),
					"422": _("YCbCr422"),
					"420": _("YCbCr420")},
					default = "Edid(Auto)")
		elif getBoxType() in ('dm900','dm920','vuzero4k'):
			config.av.hdmicolorspace = ConfigSelection(choices={
					"Edid(Auto)": _("Auto"),
					"Hdmi_Rgb": _("RGB"),
					"Itu_R_BT_709": _("BT709"),
					"DVI_Full_Range_RGB": _("Full Range RGB"),
					"FCC": _("FCC 1953"),
					"Itu_R_BT_470_2_BG": _("BT470 BG"),
					"Smpte_170M": _("Smpte 170M"),
					"Smpte_240M": _("Smpte 240M"),
					"Itu_R_BT_2020_NCL": _("BT2020 NCL"),
					"Itu_R_BT_2020_CL": _("BT2020 CL"),
					"XvYCC_709": _("BT709 XvYCC"),
					"XvYCC_601": _("BT601 XvYCC")},
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
			sleep(0.1)
			try:
				f = open("/proc/stb/video/hdmi_colorimetry", "w")
				f.write(configElement.value)
				f.close()
			except:
				pass
		config.av.hdmicolorimetry = ConfigSelection(choices={
				"auto": _("auto"),
				"bt2020ncl": _("BT 2020 NCL"),
				"bt2020cl": _("BT 2020 CL"),
				"bt709": _("BT 709")},
				default = "auto")
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
				"12": _("enable PIP no HDR"),
				"1": _("12bit 4:2:0/4:2:2 no PIP")},
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
		
		
	if os.path.exists("/proc/stb/video/hdmi_hdrtype"):
		f = open("/proc/stb/video/hdmi_hdrtype", "r")
		have_HdmiHdrType = f.read().strip().split(" ")
		f.close()
	else:
		have_HdmiHdrType = False

	SystemInfo["havehdmihdrtype"] = have_HdmiHdrType

	if have_HdmiHdrType:
		def setHdmiHdrType(configElement):
			try:
				f = open("/proc/stb/video/hdmi_hdrtype", "w")
				f.write(configElement.value)
				f.close()
			except:
				pass
		config.av.hdmihdrtype = ConfigSelection(choices={
				"auto": _("Auto"),
				"dolby": _("dolby"),
				"none": _("sdr"),
				"hdr10": _("hdr10"),
				"hlg": _("hlg")},
				default = "auto")
		config.av.hdmihdrtype.addNotifier(setHdmiHdrType)
	else:
		config.av.hdmihdrtype = ConfigNothing()

	if os.path.exists("/proc/stb/hdmi/hlg_support_choices"):
		f = open("/proc/stb/hdmi/hlg_support_choices", "r")
		have_HDRSupport = f.read().strip().split(" ")
		f.close()
	else:
		have_HDRSupport = False

	SystemInfo["HDRSupport"] = have_HDRSupport

	if have_HDRSupport:
		def setHlgSupport(configElement):
			open("/proc/stb/hdmi/hlg_support", "w").write(configElement.value)
		config.av.hlg_support = ConfigSelection(default = "auto(EDID)", 
			choices = [ ("auto(EDID)", _("controlled by HDMI")), ("yes", _("force enabled")), ("no", _("force disabled")) ])
		config.av.hlg_support.addNotifier(setHlgSupport)

		def setHdr10Support(configElement):
			open("/proc/stb/hdmi/hdr10_support", "w").write(configElement.value)
		config.av.hdr10_support = ConfigSelection(default = "auto(EDID)", 
			choices = [ ("auto(EDID)", _("controlled by HDMI")), ("yes", _("force enabled")), ("no", _("force disabled")) ])
		config.av.hdr10_support.addNotifier(setHdr10Support)

		def setDisable12Bit(configElement):
			open("/proc/stb/video/disable_12bit", "w").write(configElement.value)
		config.av.allow_12bit = ConfigSelection(default = "0", choices = [ ("0", _("yes")), ("1", _("no")) ]);
		config.av.allow_12bit.addNotifier(setDisable12Bit)

		def setDisable10Bit(configElement):
			open("/proc/stb/video/disable_10bit", "w").write(configElement.value)
		config.av.allow_10bit = ConfigSelection(default = "0", choices = [ ("0", _("yes")), ("1", _("no")) ]);
		config.av.allow_10bit.addNotifier(setDisable10Bit)


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
			try:
				f = open("/proc/stb/audio/3d_surround_speaker_position", "w")
				f.write(configElement.value)
				f.close()
			except:
				pass
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

	def setVolumeStepsize(configElement):
		eDVBVolumecontrol.getInstance().setVolumeSteps(int(configElement.value))
	config.av.volume_stepsize = ConfigSelectionNumber(1, 10, 1, default = 5)
	config.av.volume_stepsize_fastmode = ConfigSelectionNumber(1, 10, 1, default = 5)
	config.av.volume_hide_mute = ConfigYesNo(default = True)
	config.av.volume_stepsize.addNotifier(setVolumeStepsize)

	try:
		f = open("/proc/stb/audio/ac3_choices", "r")
		file = f.read()[:-1]
		f.close()
		can_downmix_ac3 = "downmix" in file
	except:
		can_downmix_ac3 = False
		SystemInfo["CanPcmMultichannel"] = False

	SystemInfo["CanDownmixAC3"] = can_downmix_ac3
	if can_downmix_ac3:
		def setAC3Downmix(configElement):
			f = open("/proc/stb/audio/ac3", "w")
			if getBoxType() in ('dm900', 'dm920', 'dm7080', 'dm800'):
				f.write(configElement.value)
			else:
				f.write(configElement.value and "downmix" or "passthrough")
			f.close()
			if SystemInfo.get("supportPcmMultichannel", False) and not configElement.value:
				SystemInfo["CanPcmMultichannel"] = True
			else:
				SystemInfo["CanPcmMultichannel"] = False
				if can_pcm_multichannel:
					config.av.pcm_multichannel.setValue(False)
		if getBoxType() in ('dm900', 'dm920', 'dm7080', 'dm800'):
			choice_list = [("downmix",  _("Downmix")), ("passthrough", _("Passthrough")), ("multichannel",  _("convert to multi-channel PCM")), ("hdmi_best",  _("use best / controlled by HDMI"))]
			config.av.downmix_ac3 = ConfigSelection(choices = choice_list, default = "downmix")
		else:
			config.av.downmix_ac3 = ConfigYesNo(default = True)
		config.av.downmix_ac3.addNotifier(setAC3Downmix)

	if os.path.exists("/proc/stb/audio/ac3plus_choices"):
		f = open("/proc/stb/audio/ac3plus_choices", "r")
		can_ac3plustranscode = f.read().strip().split(" ")
		f.close()
	else:
		can_ac3plustranscode = False

	SystemInfo["CanAC3plusTranscode"] = can_ac3plustranscode

	if can_ac3plustranscode:
		def setAC3plusTranscode(configElement):
			f = open("/proc/stb/audio/ac3plus", "w")
			f.write(configElement.value)
			f.close()
		if getBoxType() in ('dm900', 'dm920', 'dm7080', 'dm800'):
			choice_list = [("use_hdmi_caps", _("controlled by HDMI")), ("force_ac3", _("convert to AC3")), ("multichannel",  _("convert to multi-channel PCM")), ("hdmi_best",  _("use best / controlled by HDMI")), ("force_ddp",  _("force AC3plus"))]
			config.av.transcodeac3plus = ConfigSelection(choices = choice_list, default = "force_ac3")
		elif getBoxType() in ('gbquad4k', 'gbue4k'):
			choice_list = [("downmix", _("Downmix")), ("passthrough", _("Passthrough")), ("force_ac3", _("convert to AC3")), ("multichannel",  _("convert to multi-channel PCM")), ("force_dts",  _("convert to DTS"))]
			config.av.transcodeac3plus = ConfigSelection(choices = choice_list, default = "force_ac3")
		else:
			choice_list = [("use_hdmi_caps", _("controlled by HDMI")), ("force_ac3", _("convert to AC3"))]
			config.av.transcodeac3plus = ConfigSelection(choices = choice_list, default = "force_ac3")
		config.av.transcodeac3plus.addNotifier(setAC3plusTranscode)

	try:
		f = open("/proc/stb/audio/dtshd_choices", "r")
		file = f.read()[:-1]
		can_dtshd = f.read().strip().split(" ")
		f.close()
	except:
		can_dtshd = False

	SystemInfo["CanDTSHD"] = can_dtshd
	if can_dtshd:
		def setDTSHD(configElement):
			f = open("/proc/stb/audio/dtshd", "w")
			f.write(configElement.value)
			f.close()
		if getBoxType() in ("dm7080" , "dm820"):
			choice_list = [("use_hdmi_caps",  _("controlled by HDMI")), ("force_dts", _("convert to DTS"))]
			config.av.dtshd = ConfigSelection(choices = choice_list, default = "use_hdmi_caps")
		else:
			choice_list = [("downmix",  _("Downmix")), ("force_dts", _("convert to DTS")), ("use_hdmi_caps",  _("controlled by HDMI")), ("multichannel",  _("convert to multi-channel PCM")), ("hdmi_best",  _("use best / controlled by HDMI"))]
			config.av.dtshd = ConfigSelection(choices = choice_list, default = "downmix")
		config.av.dtshd.addNotifier(setDTSHD)

	try:
		f = open("/proc/stb/audio/wmapro_choices", "r")
		file = f.read()[:-1]
		can_wmapro = f.read().strip().split(" ")
		f.close()
	except:
		can_wmapro = False

	SystemInfo["CanWMAPRO"] = can_wmapro
	if can_wmapro:
		def setWMAPRO(configElement):
			f = open("/proc/stb/audio/wmapro", "w")
			f.write(configElement.value)
			f.close()
		choice_list = [("downmix",  _("Downmix")), ("passthrough", _("Passthrough")), ("multichannel",  _("convert to multi-channel PCM")), ("hdmi_best",  _("use best / controlled by HDMI"))]
		config.av.wmapro = ConfigSelection(choices = choice_list, default = "downmix")
		config.av.wmapro.addNotifier(setWMAPRO)

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
			if getBoxType() in ('dm900', 'dm920', 'dm7080', 'dm800', 'gbquad4k', 'gbue4k'):
				f.write(configElement.value)
			else:
				f.write(configElement.value and "downmix" or "passthrough")
			f.close()
		if getBoxType() in ('dm900', 'dm920', 'dm7080', 'dm800'):
			choice_list = [("downmix",  _("Downmix")), ("passthrough", _("Passthrough")), ("multichannel",  _("convert to multi-channel PCM")), ("hdmi_best",  _("use best / controlled by HDMI"))]
			config.av.downmix_aac = ConfigSelection(choices = choice_list, default = "downmix")
		elif getBoxType() in ('gbquad4k', 'gbue4k'):
			choice_list = [("downmix",  _("Downmix")), ("passthrough", _("Passthrough")), ("multichannel",  _("convert to multi-channel PCM")), ("force_ac3", _("convert to AC3")), ("force_dts",  _("convert to DTS")), ("use_hdmi_cacenter",  _("use_hdmi_cacenter")), ("wide",  _("wide")), ("extrawide",  _("extrawide"))]
			config.av.downmix_aac = ConfigSelection(choices = choice_list, default = "downmix")
		else:
			config.av.downmix_aac = ConfigYesNo(default = True)
		config.av.downmix_aac.addNotifier(setAACDownmix)

	try:
		f = open("/proc/stb/audio/aacplus_choices", "r")
		file = f.read()[:-1]
		f.close()
		can_downmix_aacplus = "downmix" in file
	except:
		can_downmix_aacplus = False

	SystemInfo["CanDownmixAACPlus"] = can_downmix_aacplus
	if can_downmix_aacplus:
		def setAACDownmixPlus(configElement):
			f = open("/proc/stb/audio/aacplus", "w")
			f.write(configElement.value)
			f.close()

		choice_list = [("downmix",  _("Downmix")), ("passthrough", _("Passthrough")), ("multichannel",  _("convert to multi-channel PCM")), ("force_ac3", _("convert to AC3")), ("force_dts",  _("convert to DTS")), ("use_hdmi_cacenter",  _("use_hdmi_cacenter")), ("wide",  _("wide")), ("extrawide",  _("extrawide"))]
		config.av.downmix_aacplus = ConfigSelection(choices = choice_list, default = "downmix")
		config.av.downmix_aacplus.addNotifier(setAACDownmixPlus)

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
				print "[AVSwitch] setting scaler_sharpness to: %0.8X" % myval
				f = open("/proc/stb/vmpeg/0/pep_scaler_sharpness", "w")
				f.write("%0.8X\n" % myval)
				f.close()
				f = open("/proc/stb/vmpeg/0/pep_apply", "w")
				f.write("1")
				f.close()
			except IOError:
				print "[AVSwitch] couldn't write pep_scaler_sharpness"

		if getBoxType() in ('gbquad', 'gbquadplus'):
			config.av.scaler_sharpness = ConfigSlider(default=5, limits=(0,26))
		else:
			config.av.scaler_sharpness = ConfigSlider(default=13, limits=(0,26))
		config.av.scaler_sharpness.addNotifier(setScaler_sharpness)
	else:
		config.av.scaler_sharpness = NoSave(ConfigNothing())

	iAVSwitch.setConfiguredMode()

class VideomodeHotplug:
	def __init__(self):
		pass

	def start(self):
		iAVSwitch.on_hotplug.append(self.hotplug)

	def stop(self):
		iAVSwitch.on_hotplug.remove(self.hotplug)

	def hotplug(self, what):
		print "[AVSwitch] hotplug detected on port '%s'" % what
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value

		if not iAVSwitch.isModeAvailable(port, mode, rate):
			print "[AVSwitch] mode %s/%s/%s went away!" % (port, mode, rate)
			modelist = iAVSwitch.getModeList(port)
			if not len(modelist):
				print "[AVSwitch] sorry, no other mode is available (unplug?). Doing nothing."
				return
			mode = modelist[0][0]
			rate = modelist[0][1]
			print "[AVSwitch] setting %s/%s/%s" % (port, mode, rate)
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

